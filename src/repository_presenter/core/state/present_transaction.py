"""Wire G5-W04's durable-state backend into a real hosted ``present`` run (G5-W05).

G5-W04 built the durable-state backend (``cas.py``, ``git_backend.py``, ``trigger.py``,
``recovery.py``) deliberately unwired into any caller - its own item record names wiring it into
the real hosted ``present.yml`` as "G5-W05's own explicit scope". This module is that wiring,
reused by the ``present --durable-state`` CLI path (``cli.py::run_present_hosted``) that
``.github/workflows/present.yml`` invokes:

1. :func:`~repository_presenter.core.state.recovery.recovery_sweep` first, so a worker killed
   mid-transaction by a prior hosted run is found before any new work starts (section 15: "run
   before every new scheduling pass") - never silently abandoned, never double-processed.
2. :func:`~repository_presenter.core.state.recovery.resume_recoverable` resumes exactly what
   recovery found, under a strictly higher fencing token than the dead worker's - never a fresh
   :func:`~repository_presenter.core.state.trigger.admit_trigger` that would mint a second,
   unrelated transaction for the same repository while an abandoned one is still unresolved.
3. ``admit_trigger`` otherwise - the normal path for a first or routine run, deduplicating a
   second concurrent trigger into whichever transaction is already in flight (section 3.2).
4. the caller's own ``run()`` callable - the existing, unmodified local pipeline
   (``cli.py::run_present``), which this module never reimplements or reaches into.
5. one or more :func:`~repository_presenter.core.state.cas.record_transition` calls committing the
   registered hops :func:`classify_present_outcome` derives from the pipeline's exit code and the
   sealed bundle it left on disk - never a second, independent guess at what happened.
6. :func:`~repository_presenter.core.state.cas.release_lease`, always, best-effort, in a
   ``finally`` - a transient release failure must never mask an already-committed transition
   (``cas.py``'s own ``release_lease`` docstring).

Why more than one hop: this schema's transition registry (``schema.py``) has no self-loops and no
shortcut from deep in the active chain back to a quiescent state - ``UNCHANGED``/``NON_PROCESSABLE``
are reachable only directly from ``OBSERVED``, and a proven candidate's own terminal,
``READY_FOR_PROPOSAL``, is reachable only by walking every stage after it
(``ACCEPTED`` -> ``PROVING_NO_OP`` -> ``READY_FOR_PROPOSAL``). The existing local pipeline
(``cli.py::run_present``) already performs every one of those stages synchronously before this
module ever sees its exit code, so walking the matching span of registered edges in one call is an
honest receipt of what already happened - never a claim this module invented. What it deliberately
does **not** attempt is attaching distinct, stage-specific evidence to each intermediate hop (every
hop in one call cites the same coarse ``input_manifest``/``output_manifest``): that would need the
local pipeline itself to expose per-stage artifacts across this module boundary, a materially larger
change than this item's own acceptance bar asks for (matching G5-W04's own item record, which named
exactly this kind of scope growth and left it to a later item). The real, fine-grained evidence for
every stage still exists, under ``runs/transactions/...`` and the sealed bundle itself - this module
only adds the durable-state *receipt* that a transaction ran, not a replacement for that evidence.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from repository_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME, verify_bundle
from repository_presenter.core.errors import StateBackendError
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.state.cas import StateBackend, record_transition, release_lease
from repository_presenter.core.state.recovery import recovery_sweep, resume_recoverable
from repository_presenter.core.state.schema import (
    FailureRecord,
    LeaseRecord,
    RepositoryRecord,
    TransactionState,
)
from repository_presenter.core.state.trigger import (
    TriggerEventType,
    admit_trigger,
    normalize_trigger,
)

# The control repository's own write token for its internal state-ref namespace only - never the
# read-only analysis token the hosted job mints for the *target* repository being presented
# (AGENTS.md "Security and Effects": credentials stay distinct and scope-separated). Named
# deliberately unlike GH_TOKEN/GITHUB_TOKEN so a workflow author can never confuse "the control
# repo's own write token" with "the ambient token the fail-closed App-auth path must ignore".
STATE_TOKEN_VARIABLE = "REPOSITORY_PRESENTER_STATE_TOKEN"

# components/readme/bundle/seal.py's own CONTRACT_VERSION - the one existing "policy version"
# concept this project has. Duplicated rather than imported: core/ may not import a
# components/readme/ module (core/candidates.py's own DEPENDENCIES_FILENAME docstring names this
# same constraint and the same remedy).
POLICY_VERSION = "readme-contract-v1-draft"

EXIT_OK = 0

# docs/STATE_MACHINE.md section 4's diagram, the one straight-through "real work succeeded" path,
# read start to end. Every adjacent pair here is a registered edge in schema.py's own
# TRANSITION_REGISTRY (checked directly against _DIAGRAM_EDGES, not assumed).
SUCCESS_SPINE: tuple[TransactionState, ...] = (
    "OBSERVED",
    "SNAPSHOTTING",
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
    "VALIDATING",
    "REVIEWING",
    "ACCEPTED",
    "PROVING_NO_OP",
    "READY_FOR_PROPOSAL",
)

# schema.py's own wildcard sources: RETRYABLE/BLOCKED_EXTERNAL/FAILED_INTERNAL may each resume into
# any ACTIVE_STATE, SNAPSHOTTING included - resume_recoverable already converts RETRYABLE into its
# own recorded resume_state before this module ever sees it, so only the other two appear here in
# practice (a record this module itself left at FAILED_INTERNAL after a prior failed run).
_WILDCARD_RESUME_SOURCES: frozenset[TransactionState] = frozenset(
    {"BLOCKED_EXTERNAL", "FAILED_INTERNAL"}
)

# docs/STATE_MACHINE.md section 6: a README-only placeholder is NON_PROCESSABLE, terminal for its
# revision. Its only registered exit is OBSERVED (schema.py), so every path in is spelled out here
# rather than searched for. A current state absent from both this table and NON_PROCESSABLE itself
# has no registered path, and the transition fails closed (see _non_processable_hops).
_NON_PROCESSABLE_HOPS: dict[TransactionState, tuple[TransactionState, ...]] = {
    "OBSERVED": ("NON_PROCESSABLE",),
    # A repository proven READY_FOR_PROPOSAL whose source is now empty: close the cycle first.
    "READY_FOR_PROPOSAL": ("MONITORING", "OBSERVED", "NON_PROCESSABLE"),
}


@dataclass(frozen=True)
class PresentOutcome:
    """What one local-pipeline invocation actually did, typed so
    :func:`run_present_transaction` never has to re-derive it."""

    kind: Literal["success", "failed", "non_processable"]
    # "success": the success-spine position this run reached (ACCEPTED or READY_FOR_PROPOSAL,
    # or SNAPSHOTTING for an EXIT_OK run that sealed no bundle at all, e.g. --facts-only).
    # "non_processable": always NON_PROCESSABLE.
    target_state: TransactionState | None = None
    # "failed": attached to the committed failure state as FailureRecord.
    # "non_processable": the disposition's reason code and resume predicate, for the run output.
    detail: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _classify_disposition(entry: RegistryEntry, path: Path) -> PresentOutcome:
    """Map a written processability disposition onto NON_PROCESSABLE, reading it back rather than
    trusting the success exit code alone.

    The artifact (``components/readme/evidence/processability.py``'s ``disposition.json``) must
    parse, name this repository, and carry its reason code; anything else fails closed as a
    failure, never as a quiet non-processable record. Only the reason is read here - this module
    stays free of ``components/`` imports (``core/`` may not depend on them).
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PresentOutcome(
            kind="failed", detail=f"processability disposition {path.name} is unreadable"
        )
    if not isinstance(document, dict):
        return PresentOutcome(
            kind="failed", detail=f"processability disposition {path.name} is not an object"
        )
    reason = document.get("reason_code")
    if document.get("repository") != entry.repository or not isinstance(reason, str) or not reason:
        return PresentOutcome(
            kind="failed",
            detail=f"processability disposition {path.name} does not name {entry.repository}",
        )
    predicate = document.get("resume_predicate")
    resume = predicate if isinstance(predicate, str) and predicate else "unspecified"
    return PresentOutcome(
        kind="non_processable",
        target_state="NON_PROCESSABLE",
        detail=f"NON_PROCESSABLE: insufficient_evidence ({reason}); resume when {resume}",
    )


def classify_present_outcome(
    root: Path, entry: RegistryEntry, exit_code: int, *, disposition_path: Path | None = None
) -> PresentOutcome:
    """Map one local-pipeline invocation's outcome onto this module's typed result.

    ``exit_code != 0`` (a blocking validation failure or any other typed failure
    ``cli.py::run_present`` already converts into an exit code) always classifies ``"failed"``,
    even when a disposition was also written.

    ``exit_code == 0`` with ``disposition_path`` set means ``run_present`` decided the repository is
    a README-only placeholder and wrote that disposition instead of candidate work: the outcome is
    ``"non_processable"`` (see :func:`_classify_disposition`). The caller passes the path only from
    the run it just performed, so this never guesses which transaction's artifact to read.

    Otherwise ``exit_code == 0`` reads the sealed bundle this run just left on disk (``CURRENT``
    plus its manifest - the exact mechanism ``core/candidates.py``'s own stale/count helpers already
    use) to report which success-spine state it actually reached: ``READY_FOR_PROPOSAL`` for a
    byte-identical, zero-provider-call reproduction of an already-sealed candidate (the hosted
    no-op-proof scenario G5-W05 exists to prove, or an equally real fresh no-op proof this very
    run), ``ACCEPTED`` for real new or changed composition work not yet proven in this run.
    """
    if exit_code != EXIT_OK:
        return PresentOutcome(
            kind="failed",
            detail=(
                f"present exited {exit_code} (a blocking validation failure or another typed "
                "failure - see this transaction's own runs/ output for which)"
            ),
        )
    if disposition_path is not None:
        return _classify_disposition(entry, disposition_path)

    candidates_dir = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}"
    current = candidates_dir / CURRENT_FILENAME
    if not current.is_file():
        # --facts-only, or any other EXIT_OK path that never seals a bundle: real work (at least a
        # snapshot) happened, but nothing conclusive to report beyond that.
        return PresentOutcome(kind="success", target_state="SNAPSHOTTING")
    revision = current.read_text(encoding="utf-8").strip()
    manifest = verify_bundle(candidates_dir / revision)
    if manifest is None:
        return PresentOutcome(kind="success", target_state="SNAPSHOTTING")
    state = manifest.get("state")
    if state == "READY_FOR_PROPOSAL":
        return PresentOutcome(kind="success", target_state="READY_FOR_PROPOSAL")
    # ACCEPTED, VALID_UPDATE_AVAILABLE, SUPERSEDED, or anything else: real work happened and this
    # run did not end with a freshly proven no-op. VALID_UPDATE_AVAILABLE/SUPERSEDED do not have
    # their own durable-state terminal yet (out of this item's scope); ACCEPTED is the honest,
    # conservative "real work, not proven this run" landing for all of them.
    return PresentOutcome(kind="success", target_state="ACCEPTED")


def _failure_target(current_state: TransactionState) -> TransactionState:
    """``ACCEPTED``'s only two registered edges are ``PROVING_NO_OP`` and ``INVALIDATED`` - it has
    no direct edge to ``FAILED_INTERNAL``, unlike every other active state this wrapper can resume
    into. ``INVALIDATED`` is the honest substitute: a failure discovered while resuming an
    ``ACCEPTED`` transaction means the previously accepted candidate no longer stands."""
    return "INVALIDATED" if current_state == "ACCEPTED" else "FAILED_INTERNAL"


def _success_hops(
    current_state: TransactionState, target_state: TransactionState
) -> list[TransactionState]:
    """The registered hops from ``current_state`` to ``target_state`` along :data:`SUCCESS_SPINE`,
    or the explicit bridge onto it from a quiescent/wildcard state - never a hop this module cannot
    name a real registered edge for (fail closed on anything else: ``run_present_transaction`` is
    the only writer of this record's ``state`` field today, so an unreachable combination here is a
    genuine defect in this module, not a state another caller could legitimately have produced).
    """
    if current_state == target_state:
        return []  # nothing changed; the registry has no self-loop and none is needed
    if current_state == "NON_PROCESSABLE":
        # The placeholder gained implementation evidence: its only registered exit is OBSERVED.
        end = SUCCESS_SPINE.index(target_state)
        return ["OBSERVED", *SUCCESS_SPINE[1 : end + 1]]
    if current_state in _WILDCARD_RESUME_SOURCES:
        # FAILED_INTERNAL/BLOCKED_EXTERNAL -> any ACTIVE_STATE is registered (schema.py's own
        # wildcard); SNAPSHOTTING is this module's one re-entry point onto the spine.
        bridge: list[TransactionState] = ["SNAPSHOTTING"]
        start = SUCCESS_SPINE.index("SNAPSHOTTING")
        end = SUCCESS_SPINE.index(target_state)
        return bridge + list(SUCCESS_SPINE[start + 1 : end + 1])
    if current_state in SUCCESS_SPINE:
        start = SUCCESS_SPINE.index(current_state)
        end = SUCCESS_SPINE.index(target_state)
        if end > start:
            return list(SUCCESS_SPINE[start + 1 : end + 1])
        if current_state == "READY_FOR_PROPOSAL":
            # A real regression: the repository was previously fully sealed and proven, and this
            # run found genuine new, unproven work. READY_FOR_PROPOSAL -> MONITORING -> OBSERVED
            # is the only registered way back toward the top of the spine from a quiescent
            # READY_FOR_PROPOSAL; restart from there.
            return ["MONITORING", "OBSERVED", *SUCCESS_SPINE[1 : end + 1]]
        raise StateBackendError(
            f"present_transaction: no registered path from {current_state!r} back to "
            f"{target_state!r} (the only known regression is READY_FOR_PROPOSAL -> ACCEPTED)"
        )
    raise StateBackendError(
        f"present_transaction: {current_state!r} has no registered path toward a committed "
        "outcome - this wiring's own scope only ever produces OBSERVED, a success-spine state, "
        "FAILED_INTERNAL, or INVALIDATED (see module docstring)"
    )


def _non_processable_hops(current_state: TransactionState) -> list[TransactionState]:
    """The registered hops from ``current_state`` into NON_PROCESSABLE, or fail closed.

    Recording a placeholder from a state with no registered path would either skip the registry or
    misstate the repository's history, so an unreachable state raises instead (the lease is still
    released by the caller's ``finally``, and the durable record is left exactly as it was).
    """
    if current_state == "NON_PROCESSABLE":
        return []  # already recorded for this revision; the registry has no self-loop
    hops = _NON_PROCESSABLE_HOPS.get(current_state)
    if hops is None:
        raise StateBackendError(
            f"present_transaction: {current_state!r} has no registered path to NON_PROCESSABLE "
            "(only OBSERVED and READY_FOR_PROPOSAL do); the placeholder disposition is left on "
            "disk and the durable record is unchanged"
        )
    return list(hops)


def _record_hops(
    backend: StateBackend,
    repository: str,
    lease: LeaseRecord,
    provider_repository_id: int,
    hops: list[TransactionState],
    event: str,
    input_manifest: str,
    output_manifest: str,
) -> None:
    for to_state in hops:
        record_transition(
            backend,
            repository,
            lease,
            to_state=to_state,
            event=event,
            input_manifest=input_manifest,
            output_manifest=output_manifest,
            policy_version=POLICY_VERSION,
            provider_repository_id=provider_repository_id,
        )


def _commit_outcome(
    backend: StateBackend,
    repository: str,
    lease: LeaseRecord,
    provider_repository_id: int,
    current_state: TransactionState,
    outcome: PresentOutcome,
) -> None:
    output_manifest = f"candidates/{repository.replace('/', '__', 1)}/CURRENT"
    input_manifest = f"registry:{repository}"
    if outcome.kind == "non_processable":
        _record_hops(
            backend,
            repository,
            lease,
            provider_repository_id,
            _non_processable_hops(current_state),
            event=(
                "present.yml hosted transaction classified NON_PROCESSABLE (processability "
                "disposition written; no candidate sealed)"
            ),
            input_manifest=input_manifest,
            output_manifest=output_manifest,
        )
        return
    if outcome.kind == "failed":
        if current_state == "NON_PROCESSABLE":
            # The one registered exit from the terminal placeholder state: re-observe the revision,
            # then record the failure from OBSERVED like any other observed run.
            _record_hops(
                backend,
                repository,
                lease,
                provider_repository_id,
                ["OBSERVED"],
                event="present.yml hosted transaction re-observed a non-processable repository",
                input_manifest=input_manifest,
                output_manifest=output_manifest,
            )
            current_state = "OBSERVED"
        target = _failure_target(current_state)
        if current_state == target:
            # The registry has no self-loop (same reasoning as _success_hops's own early return):
            # a repeat failure that lands on the same already-committed terminal state - e.g. two
            # consecutive hosted runs both failing at FAILED_INTERNAL - has no registered hop to
            # commit. The record already correctly reflects "failed, not yet resolved"; a later
            # trigger re-enters through admit_trigger regardless, so nothing is lost by not
            # re-writing the same state a second time.
            return

        def mark_failed(record: RepositoryRecord) -> RepositoryRecord:
            return record.model_copy(
                update={
                    "failure": FailureRecord(
                        classification="validation_failed",
                        detail=outcome.detail or "present reported a failure",
                        # Informational only: neither FAILED_INTERNAL nor INVALIDATED is
                        # auto-resumed by recovery_sweep; a later trigger re-enters through this
                        # module's own admit_trigger path regardless of what resume_state names.
                        resume_state="SNAPSHOTTING",
                        occurred_at=_now_iso(),
                    )
                }
            )

        record_transition(
            backend,
            repository,
            lease,
            to_state=target,
            event="present.yml hosted transaction failed",
            input_manifest=input_manifest,
            output_manifest=output_manifest,
            policy_version=POLICY_VERSION,
            provider_repository_id=provider_repository_id,
            patch=mark_failed,
        )
        return

    assert outcome.target_state is not None
    event = (
        "present.yml hosted transaction completed (one coarse receipt spanning the local "
        "pipeline's own stages - see core/state/present_transaction.py's module docstring)"
    )
    _record_hops(
        backend,
        repository,
        lease,
        provider_repository_id,
        _success_hops(current_state, outcome.target_state),
        event=event,
        input_manifest=input_manifest,
        output_manifest=output_manifest,
    )


def run_present_transaction(
    *,
    backend: StateBackend,
    repository: str,
    provider_repository_id: int,
    holder_id: str,
    run: Callable[[], int],
    classify: Callable[[int], PresentOutcome],
    trigger_event_type: TriggerEventType = "workflow_dispatch",
    workflow_run_id: str | None = None,
) -> int:
    """Run ``run()`` under the durable-state backend's recovery, dedup, and transition-receipt
    discipline. Returns ``run()``'s own exit code, or ``0`` when this trigger deduplicated into an
    already in-flight transaction without running anything (section 3.2).
    """
    recovery_sweep(backend, {repository: provider_repository_id})

    resumed = resume_recoverable(
        backend, repository, holder_id=holder_id, provider_repository_id=provider_repository_id
    )
    if resumed is not None:
        record, lease = resumed
        current_state = record.state
    else:
        envelope = normalize_trigger(
            repository,
            event_type=trigger_event_type,
            workflow_run_id=workflow_run_id,
            provider_event_id=None if workflow_run_id else uuid4().hex,
        )
        admission = admit_trigger(
            backend, envelope, holder_id=holder_id, provider_repository_id=provider_repository_id
        )
        if admission.outcome == "deduplicated":
            print(
                f"trigger deduplicated: {repository} already has transaction "
                f"{admission.transaction_id} in flight; not starting a duplicate run"
            )
            return EXIT_OK
        assert admission.lease is not None  # "accepted" always carries a fresh lease
        lease = admission.lease
        current_state = admission.record.state

    try:
        exit_code = run()
        outcome = classify(exit_code)
        _commit_outcome(backend, repository, lease, provider_repository_id, current_state, outcome)
        return exit_code
    finally:
        release_lease(backend, repository, lease, provider_repository_id=provider_repository_id)
