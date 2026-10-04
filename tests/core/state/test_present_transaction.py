"""G5-W05: wiring G5-W04's durable-state backend around one ``present`` invocation.

``classify_present_outcome`` is tested against the exact artifacts a real sealed bundle leaves on
disk (``CANDIDATES_DIRNAME/<owner>__<name>/CURRENT`` plus ``manifest.json``), never a mock of
``verify_bundle``. ``run_present_transaction`` is tested against the real cas.py/trigger.py/
recovery.py primitives with ``InMemoryStateBackend`` (the same test double G5-W04's own suite
uses) standing in for the git-ref backend - the CAS/lease/dedup contract is identical either way,
and ``test_git_backend.py`` separately proves the real ref mechanism.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, get_args

import pytest

from repository_presenter.components.readme.evidence.processability import (
    NO_IMPLEMENTATION_EVIDENCE,
    NonProcessableDisposition,
    write_disposition,
)
from repository_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME
from repository_presenter.core.errors import IllegalTransitionError, StateBackendError
from repository_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repository_presenter.core.state.cas import acquire_lease, record_transition, save_state_patch
from repository_presenter.core.state.present_transaction import (
    PresentOutcome,
    _commit_outcome,
    classify_present_outcome,
    run_present_transaction,
)
from repository_presenter.core.state.schema import TransactionState
from repository_presenter.core.state.trigger import admit_trigger, normalize_trigger
from support import InMemoryStateBackend

REPO = "example/Aspose.Widget-FOSS-for-Python"
PROVIDER_ID = 777


def _entry(repository: str = REPO) -> RegistryEntry:
    return RegistryEntry(
        repository=repository,
        family="widget",
        platform="python",
        ecosystem="python",
        mode="disabled",
        policy_profile="example-widget",
        active=True,
        provider_identity=ProviderIdentity(repository_id=PROVIDER_ID, node_id="R_777"),
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bundle(
    root: Path, entry: RegistryEntry, revision: str, manifest_extra: dict[str, Any]
) -> None:
    """A minimal real sealed bundle: one artifact file plus a manifest whose own inventory
    checks out against it, exactly what ``verify_bundle`` requires."""
    bundle_dir = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / revision
    bundle_dir.mkdir(parents=True)
    artifact = b"README content\n"
    (bundle_dir / "README.md").write_bytes(artifact)
    manifest = {
        "schema_version": 1,
        "repository": entry.repository,
        "revision": revision,
        "files": {"README.md": {"sha256": _sha256(artifact), "bytes": len(artifact)}},
        **manifest_extra,
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    current_dir = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}"
    (current_dir / CURRENT_FILENAME).write_text(f"{revision}\n", encoding="utf-8")


# --- classify_present_outcome -----------------------------------------------------------------


def test_classify_nonzero_exit_code_is_failed(tmp_path: Path) -> None:
    outcome = classify_present_outcome(tmp_path, _entry(), exit_code=1)
    assert outcome.kind == "failed"
    assert outcome.detail is not None


def test_classify_no_bundle_at_all_lands_at_snapshotting(tmp_path: Path) -> None:
    outcome = classify_present_outcome(tmp_path, _entry(), exit_code=0)
    assert outcome == PresentOutcome(kind="success", target_state="SNAPSHOTTING")


def test_classify_zero_call_byte_identical_reproduction_is_ready_for_proposal(
    tmp_path: Path,
) -> None:
    entry = _entry()
    _write_bundle(
        tmp_path,
        entry,
        "rev-1",
        {
            "state": "READY_FOR_PROPOSAL",
            "provider_calls": 0,
            "no_op_proof": {"fresh_process": True, "byte_identical": True, "provider_calls": 0},
        },
    )
    outcome = classify_present_outcome(tmp_path, entry, exit_code=0)
    assert outcome == PresentOutcome(kind="success", target_state="READY_FOR_PROPOSAL")


def test_classify_real_new_unproven_work_is_accepted(tmp_path: Path) -> None:
    entry = _entry()
    _write_bundle(
        tmp_path,
        entry,
        "rev-2",
        {"state": "ACCEPTED", "provider_calls": 12, "no_op_proof": None},
    )
    outcome = classify_present_outcome(tmp_path, entry, exit_code=0)
    assert outcome == PresentOutcome(kind="success", target_state="ACCEPTED")


def test_classify_a_waiting_update_never_counts_as_ready_for_proposal(tmp_path: Path) -> None:
    """A proven bundle with a factual update waiting adoption (TB-06) is real new information
    this run surfaced - never silently folded into the proven-unchanged outcome."""
    entry = _entry()
    _write_bundle(
        tmp_path,
        entry,
        "rev-3",
        {
            "state": "VALID_UPDATE_AVAILABLE",
            "provider_calls": 0,
            "no_op_proof": {"fresh_process": True, "byte_identical": True, "provider_calls": 0},
            "update": {"available": True, "classification": "factual"},
        },
    )
    outcome = classify_present_outcome(tmp_path, entry, exit_code=0)
    assert outcome == PresentOutcome(kind="success", target_state="ACCEPTED")


# --- run_present_transaction -------------------------------------------------------------------


def _classify_always(outcome: PresentOutcome):
    def classify(exit_code: int) -> PresentOutcome:
        return outcome

    return classify


_READY = PresentOutcome(kind="success", target_state="READY_FOR_PROPOSAL")
_ACCEPTED = PresentOutcome(kind="success", target_state="ACCEPTED")
_FAILED = PresentOutcome(kind="failed", detail="synthetic failure")


def test_a_first_trigger_runs_once_and_walks_the_full_spine_to_ready_for_proposal() -> None:
    """The acceptance-bar scenario: a brand new durable record (no prior state at all - exactly
    what every repository's first-ever hosted run looks like), a zero-call reproduction of an
    already-sealed candidate. The whole success spine is walked in one call, since the existing
    local pipeline already performed every one of those stages before returning."""
    backend = InMemoryStateBackend()
    calls = {"count": 0}

    def run() -> int:
        calls["count"] += 1
        return 0

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=run,
        classify=_classify_always(_READY),
        workflow_run_id="run-1",
    )
    assert exit_code == 0
    assert calls["count"] == 1
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "READY_FOR_PROPOSAL"
    assert record.lease is None  # released
    assert record.last_transition is not None
    assert record.last_transition.from_state == "PROVING_NO_OP"
    assert record.last_transition.to_state == "READY_FOR_PROPOSAL"


def test_a_repeat_no_op_run_already_at_ready_for_proposal_commits_nothing_new() -> None:
    """The registry has no self-loop; once a repository's durable record already sits at
    READY_FOR_PROPOSAL, a second, equally-unchanged run must not try to re-walk the spine (which
    would be illegal) - it correctly commits no new transition at all."""
    backend = InMemoryStateBackend()
    run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(_READY),
        workflow_run_id="run-1",
    )
    first = backend.load(REPO)
    assert first is not None
    first_transition_id = first.last_transition.transition_id  # type: ignore[union-attr]

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(_READY),
        workflow_run_id="run-2",
    )
    assert exit_code == 0
    second = backend.load(REPO)
    assert second is not None
    assert second.state == "READY_FOR_PROPOSAL"
    # No new transition receipt was minted - the state genuinely did not change.
    assert second.last_transition.transition_id == first_transition_id  # type: ignore[union-attr]


def test_a_regression_from_ready_for_proposal_to_real_new_work_closes_the_cycle_first() -> None:
    """A repository previously fully proven (READY_FOR_PROPOSAL) now has a genuinely changed
    upstream revision: the only registered way back toward the top of the spine is
    READY_FOR_PROPOSAL -> MONITORING -> OBSERVED, then forward again to ACCEPTED."""
    backend = InMemoryStateBackend()
    run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(_READY),
        workflow_run_id="run-1",
    )
    assert backend.load(REPO).state == "READY_FOR_PROPOSAL"  # type: ignore[union-attr]

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(_ACCEPTED),
        workflow_run_id="run-2",
    )
    assert exit_code == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "ACCEPTED"
    assert record.last_transition is not None
    assert record.last_transition.from_state == "REVIEWING"
    assert record.last_transition.to_state == "ACCEPTED"


def test_a_duplicate_trigger_while_one_is_in_flight_never_runs_twice() -> None:
    backend = InMemoryStateBackend()
    # Simulate an already in-flight transaction for this repository (the lease is held).
    envelope = normalize_trigger(REPO, event_type="workflow_dispatch", workflow_run_id="run-A")
    admission = admit_trigger(
        backend, envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert admission.outcome == "accepted"

    calls = {"count": 0}

    def run() -> int:
        calls["count"] += 1
        return 0

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-b",
        run=run,
        classify=_classify_always(_READY),
        workflow_run_id="run-B",
    )
    assert exit_code == 0
    assert calls["count"] == 0  # deduplicated: the in-flight transaction owns this trigger


def test_a_stale_lease_resumes_via_recovery_rather_than_minting_a_fresh_transaction() -> None:
    backend = InMemoryStateBackend()
    # A worker acquires a lease, starts real work, then is killed (never releases, never commits
    # a terminal transition) - exactly recovery_sweep's own target scenario.
    then = datetime.now(UTC) - timedelta(hours=1)
    lease = acquire_lease(
        backend,
        REPO,
        holder_id="dead-worker",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,  # already expired relative to "now" used by the sweep below
        now=then,
    )
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(
            update={"active_transaction_id": "tx-dead", "state": "SNAPSHOTTING"}
        ),
        provider_repository_id=PROVIDER_ID,
    )
    before = backend.load(REPO)
    assert before is not None and before.lease is not None
    dead_token = before.lease.fencing_token

    calls = {"count": 0}

    def run() -> int:
        calls["count"] += 1
        return 0

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="new-worker",
        run=run,
        classify=_classify_always(_READY),
        workflow_run_id="run-C",
    )
    assert exit_code == 0
    assert calls["count"] == 1  # resumed and actually ran, not silently deduplicated away
    record = backend.load(REPO)
    assert record is not None
    assert record.active_transaction_id == "tx-dead"  # the same transaction, truly resumed
    assert record.state == "READY_FOR_PROPOSAL"
    assert record.lease is None
    # And whatever lease eventually committed carried a strictly higher fencing token than the
    # dead worker's - section 14's own guarantee.
    assert record.last_transition is not None
    assert record.last_transition.fencing_token > dead_token


def test_a_failing_run_commits_failed_internal_and_still_releases_the_lease() -> None:
    backend = InMemoryStateBackend()

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 1,
        classify=_classify_always(_FAILED),
        workflow_run_id="run-D",
    )
    assert exit_code == 1
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "FAILED_INTERNAL"
    assert record.failure is not None
    assert record.lease is None


def test_two_consecutive_failing_runs_never_attempt_an_illegal_self_transition() -> None:
    """Reproduces a real defect caught live in G5-W05's first hosted run (present.yml run
    36846738278): a second trigger whose own run also fails, resuming from a record this same
    module already left at FAILED_INTERNAL, tried FAILED_INTERNAL -> FAILED_INTERNAL -
    unregistered (no self-loop exists) - raising IllegalTransitionError instead of this test's own
    exit code. The second run must commit no new transition (the record already correctly reads
    "failed, not yet resolved"), exactly like a repeat no-op success commits nothing new."""
    backend = InMemoryStateBackend()

    first = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 1,
        classify=_classify_always(_FAILED),
        workflow_run_id="run-E1",
    )
    assert first == 1
    after_first = backend.load(REPO)
    assert after_first is not None and after_first.state == "FAILED_INTERNAL"
    first_transition_id = after_first.last_transition.transition_id  # type: ignore[union-attr]

    second = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-b",
        run=lambda: 1,
        classify=_classify_always(_FAILED),
        workflow_run_id="run-E2",
    )
    assert second == 1
    after_second = backend.load(REPO)
    assert after_second is not None
    assert after_second.state == "FAILED_INTERNAL"
    assert after_second.lease is None
    # No new transition receipt was minted - record_transition was never even called the second
    # time, since there was no registered hop to commit.
    assert after_second.last_transition.transition_id == first_transition_id  # type: ignore[union-attr]


def test_a_failing_run_from_an_already_accepted_resume_invalidates_instead() -> None:
    """ACCEPTED has no registered edge to FAILED_INTERNAL (only PROVING_NO_OP and INVALIDATED) -
    a failure discovered while resuming an ACCEPTED transaction must land on INVALIDATED, never
    raise an IllegalTransitionError from trying an unregistered hop."""
    backend = InMemoryStateBackend()
    lease = acquire_lease(
        backend, REPO, holder_id="dead-worker", provider_repository_id=PROVIDER_ID
    )
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"active_transaction_id": "tx-1"}),
        provider_repository_id=PROVIDER_ID,
    )
    record_transition(
        backend,
        REPO,
        lease,
        to_state="SNAPSHOTTING",
        event="seed",
        input_manifest="x",
        output_manifest="x",
        policy_version="v1",
        provider_repository_id=PROVIDER_ID,
    )
    for step in (
        "EXTRACTING",
        "INVESTIGATING",
        "RECONCILING",
        "PLANNING",
        "COMPOSING",
        "VALIDATING",
        "REVIEWING",
        "ACCEPTED",
    ):
        record_transition(
            backend,
            REPO,
            lease,
            to_state=step,
            event="seed",
            input_manifest="x",
            output_manifest="x",
            policy_version="v1",
            provider_repository_id=PROVIDER_ID,
        )
    # Expire the lease without releasing it (simulating a crash right after reaching ACCEPTED).
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(
            update={"lease": r.lease.model_copy(update={"expires_at": then_past()})}
        ),
        provider_repository_id=PROVIDER_ID,
    )

    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="new-worker",
        run=lambda: 1,
        classify=_classify_always(_FAILED),
        workflow_run_id="run-E",
    )
    assert exit_code == 1
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "INVALIDATED"
    assert record.failure is not None


def then_past() -> str:
    return (datetime.now(UTC) - timedelta(hours=1)).isoformat()


# --- durable outcome table (defect: present_transaction.wrapper_outcome_no_registered_path) ------
#
# The wrapper's real production sequence: a sealed ACCEPTED candidate, a later run's pipeline fails
# (ACCEPTED -> INVALIDATED is the one registered failure exit from ACCEPTED), and the next run
# succeeds with a VALID_UPDATE_AVAILABLE bundle (a changed consumed presentation input whose update
# waits; the durable outcome is ACCEPTED - the candidate stays valid and is never invalidated by a
# non-critical update, docs/STATE_MACHINE.md section 9). That next run crashed with
# "'INVALIDATED' has no registered path toward a committed outcome" because admission never resets
# a record's state, so the wrapper started its success hops from INVALIDATED.


def _bundle_state(state: str, *, update: bool = False) -> dict[str, Any]:
    extra: dict[str, Any] = {"state": state, "provider_calls": 0}
    if state == "READY_FOR_PROPOSAL":
        extra["no_op_proof"] = {"fresh_process": True, "byte_identical": True, "provider_calls": 0}
    else:
        extra["no_op_proof"] = None
    if update:
        extra["update"] = {"available": True, "classification": "presentation"}
    return extra


def test_a_changed_consumed_input_after_a_sealed_candidate_was_invalidated_commits_without_raising(
    tmp_path: Path,
) -> None:
    entry = _entry()
    backend = InMemoryStateBackend()

    def classify(exit_code: int) -> PresentOutcome:
        return classify_present_outcome(tmp_path, entry, exit_code)

    # 1. A sealed candidate lands ACCEPTED.
    _write_bundle(tmp_path, entry, "rev-1", _bundle_state("ACCEPTED"))
    run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=classify,
        workflow_run_id="run-1",
    )
    assert backend.load(REPO).state == "ACCEPTED"  # type: ignore[union-attr]

    # 2. A later run's pipeline fails: the registered ACCEPTED -> INVALIDATED exit.
    run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 1,
        classify=classify,
        workflow_run_id="run-2",
    )
    assert backend.load(REPO).state == "INVALIDATED"  # type: ignore[union-attr]

    # 3. The next run succeeds; its bundle is VALID_UPDATE_AVAILABLE. Must commit, never raise.
    _write_bundle(tmp_path, entry, "rev-2", _bundle_state("VALID_UPDATE_AVAILABLE", update=True))
    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=classify,
        workflow_run_id="run-3",
    )
    assert exit_code == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "ACCEPTED"
    assert record.last_transition is not None
    assert record.last_transition.to_state == "ACCEPTED"
    assert record.lease is None


@pytest.mark.parametrize("start", ["ACCEPTED", "READY_FOR_PROPOSAL"])
def test_a_genuinely_invalid_candidate_still_commits_invalidated(
    tmp_path: Path, start: str
) -> None:
    """Negative control: a failed factual check (the bundle itself is written INVALIDATED on
    disk, exit 1) must still land INVALIDATED - the fix never softens a real invalidation.
    READY_FOR_PROPOSAL previously had no registered failure exit at all and crashed with
    IllegalTransitionError."""
    entry = _entry()
    backend = InMemoryStateBackend()
    seed = _ACCEPTED if start == "ACCEPTED" else _READY
    run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(seed),
        workflow_run_id="run-seed",
    )
    assert backend.load(REPO).state == start  # type: ignore[union-attr]

    _write_bundle(
        tmp_path,
        entry,
        "rev-bad",
        {"state": "INVALIDATED", "invalidated": {"check": "BC-08", "classification": "factual"}},
    )
    exit_code = run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 1,
        classify=lambda code: classify_present_outcome(tmp_path, entry, code),
        workflow_run_id="run-bad",
    )
    assert exit_code == 1
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "INVALIDATED"
    assert record.last_transition is not None
    assert record.last_transition.to_state == "INVALIDATED"
    assert record.failure is not None


_MID_SPINE = (
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
    "VALIDATING",
    "REVIEWING",
)
_SNAPSHOT_ONLY = PresentOutcome(kind="success", target_state="SNAPSHOTTING")
_NON_OUTCOME = PresentOutcome(
    kind="non_processable", target_state="NON_PROCESSABLE", detail="synthetic placeholder"
)
_OUTCOMES: dict[str, PresentOutcome] = {
    "ACCEPTED": _ACCEPTED,
    "READY_FOR_PROPOSAL": _READY,
    "SNAPSHOTTING": _SNAPSHOT_ONLY,
    "failed": _FAILED,
    "non_processable": _NON_OUTCOME,
}

# Every state the durable wrapper itself can leave a record in (its own commits, its failure exits,
# and the one intermediate hop of a READY_FOR_PROPOSAL regression), mapped to the record state each
# outcome must commit. ``None`` is the one declared refusal: a facts-only (SNAPSHOTTING) outcome
# behind a mid-spine record has no registered route back to SNAPSHOTTING, so the wrapper refuses
# before writing anything (fail closed, never an attempted unregistered hop).
_EXPECTED_FINAL: dict[str, dict[str, str | None]] = {
    "OBSERVED": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "FAILED_INTERNAL",
        "non_processable": "NON_PROCESSABLE",
    },
    "SNAPSHOTTING": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "FAILED_INTERNAL",
        "non_processable": None,
    },
    **{
        state: {
            "ACCEPTED": "ACCEPTED",
            "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
            "SNAPSHOTTING": None,
            "failed": "FAILED_INTERNAL",
            "non_processable": None,
        }
        for state in _MID_SPINE
    },
    "PROVING_NO_OP": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "INVALIDATED",
        "failed": "FAILED_INTERNAL",
        "non_processable": None,
    },
    "ACCEPTED": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "INVALIDATED",
        "failed": "INVALIDATED",
        "non_processable": None,
    },
    "READY_FOR_PROPOSAL": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "INVALIDATED",
        "non_processable": "NON_PROCESSABLE",
    },
    "MONITORING": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "FAILED_INTERNAL",
        "non_processable": "NON_PROCESSABLE",
    },
    "FAILED_INTERNAL": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "FAILED_INTERNAL",
        "non_processable": None,
    },
    "INVALIDATED": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "INVALIDATED",
        "failed": "INVALIDATED",
        "non_processable": None,
    },
    # A placeholder disposition is written by the wrapper now (see the non-processable tests
    # below); NON_PROCESSABLE is terminal, re-entered through OBSERVED on a processable run.
    "NON_PROCESSABLE": {
        "ACCEPTED": "ACCEPTED",
        "READY_FOR_PROPOSAL": "READY_FOR_PROPOSAL",
        "SNAPSHOTTING": "SNAPSHOTTING",
        "failed": "FAILED_INTERNAL",
        "non_processable": "NON_PROCESSABLE",
    },
}

# States no wrapper commit or recovery step ever writes today: a later stage (processability,
# authorization, proposal, repair) owns them, so the wrapper must refuse them cleanly, never
# attempt an unregistered hop.
_NOT_WRITTEN_BY_WRAPPER: frozenset[str] = frozenset(
    {
        "UNCHANGED",
        "REPAIRING",
        "AWAITING_AUTHORIZATION",
        "PROPOSING",
        "RETRYABLE",
        "BLOCKED_EXTERNAL",
        "SUPERSEDED",
    }
)


def _seed_record(backend: InMemoryStateBackend, state: str) -> Any:
    """A real lease on a real record already sitting at ``state`` (no faked transition history)."""
    lease = acquire_lease(
        backend, REPO, holder_id="worker-enum", provider_repository_id=PROVIDER_ID
    )
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"state": state, "active_transaction_id": "tx-enum"}),
        provider_repository_id=PROVIDER_ID,
    )
    return lease


def test_the_outcome_table_classifies_every_transaction_state() -> None:
    """A state added to the schema must be classified here, never silently left without a path."""
    classified = set(_EXPECTED_FINAL) | _NOT_WRITTEN_BY_WRAPPER
    assert classified == set(get_args(TransactionState))
    assert not (set(_EXPECTED_FINAL) & _NOT_WRITTEN_BY_WRAPPER)


@pytest.mark.parametrize(
    ("state", "outcome_name"),
    [(s, o) for s in _EXPECTED_FINAL for o in _OUTCOMES],
)
def test_every_reachable_state_and_outcome_pair_has_a_registered_path(
    state: str, outcome_name: str
) -> None:
    backend = InMemoryStateBackend()
    lease = _seed_record(backend, state)
    expected = _EXPECTED_FINAL[state][outcome_name]
    outcome = _OUTCOMES[outcome_name]

    if expected is None:
        with pytest.raises(StateBackendError) as info:
            _commit_outcome(backend, REPO, lease, PROVIDER_ID, state, outcome)  # type: ignore[arg-type]
        assert not isinstance(info.value, IllegalTransitionError)
        record = backend.load(REPO)
        assert record is not None and record.state == state  # refused before any write
        return

    _commit_outcome(backend, REPO, lease, PROVIDER_ID, state, outcome)  # type: ignore[arg-type]
    record = backend.load(REPO)
    assert record is not None
    assert record.state == expected


@pytest.mark.parametrize(
    ("state", "outcome_name"),
    [(s, o) for s in sorted(_NOT_WRITTEN_BY_WRAPPER) for o in _OUTCOMES],
)
def test_states_the_wrapper_never_writes_are_refused_cleanly_never_by_an_illegal_hop(
    state: str, outcome_name: str
) -> None:
    backend = InMemoryStateBackend()
    lease = _seed_record(backend, state)
    try:
        _commit_outcome(backend, REPO, lease, PROVIDER_ID, state, _OUTCOMES[outcome_name])  # type: ignore[arg-type]
    except IllegalTransitionError as error:  # pragma: no cover - the failure this guards against
        pytest.fail(f"unregistered hop attempted from {state!r}: {error}")
    except StateBackendError:
        record = backend.load(REPO)
        assert record is not None and record.state == state  # refused before any write


def _write_disposition(path: Path, repository: str = REPO) -> Path:
    """The real disposition artifact ``cli.py::run_present`` writes for a placeholder."""
    write_disposition(
        NonProcessableDisposition(
            reason_code=NO_IMPLEMENTATION_EVIDENCE,
            repository=repository,
            source_revision="b" * 40,
            tree_sha256="c" * 64,
            ecosystem="python",
            evidence_paths_inspected=("LICENSE", "README.md"),
            resume_predicate="a later default-branch revision adds a python manifest",
        ),
        path,
    )
    return path


def test_classify_a_written_disposition_is_non_processable_with_its_reason(tmp_path: Path) -> None:
    disposition = _write_disposition(tmp_path / "disposition.json")
    outcome = classify_present_outcome(
        tmp_path, _entry(), exit_code=0, disposition_path=disposition
    )
    assert outcome.kind == "non_processable"
    assert outcome.target_state == "NON_PROCESSABLE"
    assert outcome.detail is not None
    assert NO_IMPLEMENTATION_EVIDENCE in outcome.detail


def test_classify_an_unreadable_disposition_fails_closed_never_non_processable(
    tmp_path: Path,
) -> None:
    outcome = classify_present_outcome(
        tmp_path, _entry(), exit_code=0, disposition_path=tmp_path / "missing.json"
    )
    assert outcome.kind == "failed"


def test_classify_a_disposition_for_another_repository_fails_closed(tmp_path: Path) -> None:
    disposition = _write_disposition(
        tmp_path / "disposition.json", repository="example/Other-FOSS-for-Python"
    )
    outcome = classify_present_outcome(
        tmp_path, _entry(), exit_code=0, disposition_path=disposition
    )
    assert outcome.kind == "failed"


def test_a_nonzero_exit_with_a_disposition_is_still_failed(tmp_path: Path) -> None:
    disposition = _write_disposition(tmp_path / "disposition.json")
    outcome = classify_present_outcome(
        tmp_path, _entry(), exit_code=1, disposition_path=disposition
    )
    assert outcome.kind == "failed"


_NON_PROCESSABLE = PresentOutcome(
    kind="non_processable", target_state="NON_PROCESSABLE", detail="synthetic placeholder"
)


def _present(backend: InMemoryStateBackend, outcome: PresentOutcome, run_id: str) -> int:
    return run_present_transaction(
        backend=backend,
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        holder_id="worker-a",
        run=lambda: 0,
        classify=_classify_always(outcome),
        workflow_run_id=run_id,
    )


def test_a_placeholder_from_a_first_trigger_commits_non_processable_not_failed() -> None:
    backend = InMemoryStateBackend()
    assert _present(backend, _NON_PROCESSABLE, "run-1") == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "NON_PROCESSABLE"
    assert record.failure is None
    assert record.lease is None
    assert record.last_transition is not None
    assert record.last_transition.from_state == "OBSERVED"
    assert record.last_transition.to_state == "NON_PROCESSABLE"


def test_a_repeat_placeholder_run_commits_nothing_new() -> None:
    backend = InMemoryStateBackend()
    _present(backend, _NON_PROCESSABLE, "run-1")
    first = backend.load(REPO)
    assert first is not None
    first_transition_id = first.last_transition.transition_id  # type: ignore[union-attr]

    assert _present(backend, _NON_PROCESSABLE, "run-2") == 0
    second = backend.load(REPO)
    assert second is not None
    assert second.state == "NON_PROCESSABLE"
    assert second.last_transition.transition_id == first_transition_id  # type: ignore[union-attr]


def test_a_placeholder_that_gains_implementation_reobserves_before_the_spine() -> None:
    """NON_PROCESSABLE is terminal for its revision; its only registered exit is OBSERVED."""
    backend = InMemoryStateBackend()
    _present(backend, _NON_PROCESSABLE, "run-1")
    assert _present(backend, _READY, "run-2") == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "READY_FOR_PROPOSAL"
    assert record.last_transition is not None
    assert record.last_transition.from_state == "PROVING_NO_OP"


def test_a_processable_repository_that_becomes_a_placeholder_walks_back_to_observed() -> None:
    backend = InMemoryStateBackend()
    _present(backend, _READY, "run-1")
    assert _present(backend, _NON_PROCESSABLE, "run-2") == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "NON_PROCESSABLE"
    assert record.last_transition is not None
    assert record.last_transition.from_state == "OBSERVED"


def test_a_failure_after_a_placeholder_reobserves_then_fails() -> None:
    backend = InMemoryStateBackend()
    _present(backend, _NON_PROCESSABLE, "run-1")
    assert _present(backend, _FAILED, "run-2") == 0
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "FAILED_INTERNAL"
    assert record.failure is not None
    assert record.last_transition is not None
    assert record.last_transition.from_state == "OBSERVED"


def test_a_placeholder_from_an_accepted_record_has_no_registered_path_and_fails_closed() -> None:
    backend = InMemoryStateBackend()
    _present(backend, _ACCEPTED, "run-1")
    with pytest.raises(StateBackendError):
        _present(backend, _NON_PROCESSABLE, "run-2")
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "ACCEPTED"
