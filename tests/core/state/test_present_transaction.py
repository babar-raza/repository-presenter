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
from typing import Any

from repository_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME
from repository_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repository_presenter.core.state.cas import acquire_lease, record_transition, save_state_patch
from repository_presenter.core.state.present_transaction import (
    PresentOutcome,
    classify_present_outcome,
    run_present_transaction,
)
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
