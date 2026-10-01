"""Recover stale, unfinished work before new scheduling (docs/STATE_MACHINE.md section 15).

Ported in concept from legacy ``readme_agent.state.recovery`` (``migration/reuse-manifest.yaml``):
sweep every repository's durable record, find nonterminal work whose lease is missing or expired,
and mark it cleanly resumable rather than silently abandoned, re-run from scratch, or allowed to
skip ahead. Written fresh against this project's own ``RepositoryRecord``/``FailureRecord`` shape
(``schema.py``) - legacy's ``TriggerLifecycleV2``-keyed sweep over a separate lifecycle map has no
equivalent here, since trigger-dedup, lease, and transaction state all live on the one embedded
record this project's schema uses.

Only two of section 15's seven recovery steps need their own code here; the rest are properties
this module's own restraint already satisfies, documented at :func:`recovery_sweep`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from repository_presenter.core.state.cas import (
    DEFAULT_LEASE_SECONDS,
    StateBackend,
    acquire_lease,
    lease_is_active,
    save_state_patch,
)
from repository_presenter.core.state.schema import (
    ACTIVE_STATES,
    FailureRecord,
    LeaseRecord,
    RepositoryRecord,
    TransactionState,
)

RecoveryReason = str  # "stale_or_missing_lease" | "source_revision_superseded"


@dataclass(frozen=True)
class RecoveryOutcome:
    """One repository's transaction that this sweep found and acted on."""

    repository: str
    transaction_id: str
    prior_state: TransactionState
    reason: RecoveryReason


def recovery_sweep(
    backend: StateBackend,
    repositories: dict[str, int],
    *,
    current_source_revisions: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[RecoveryOutcome]:
    """Run before every new scheduling pass (section 15's own opening line).

    ``repositories`` maps each repository to admit to its ``provider_repository_id`` (needed only
    to create a fresh default record if one somehow does not exist yet; an already-existing record
    is never touched for this reason).

    docs/STATE_MACHINE.md section 15's seven points, and where each one lives:

    1. "Finds nonterminal transactions without a valid lease" - exactly this function's main loop:
       an active-transaction record whose state is in :data:`~...schema.ACTIVE_STATES` and whose
       lease is missing or expired.
    2/3. "Verifies the last durable artifact and transition receipt" / "Re-enters the last state
       whose entry conditions are fully proven" - every write that ever advanced ``state`` went
       through :func:`~repository_presenter.core.state.cas.record_transition`, which never commits
       a state change without first writing its own :class:`~...schema.TransitionReceipt`
       (``record.last_transition``). The record's own ``state`` field *is* that last proven state
       by construction, so recovery trusts it directly rather than re-deriving it - there is
       nothing else durable to re-verify against.
    4. "Never skips a stage merely because a later partial artifact exists" - this sweep only ever
       relabels the record ``RETRYABLE``, recording the exact state to resume into
       (``FailureRecord.resume_state``); it never advances ``state`` itself. The next scheduling
       pass's call to :func:`resume_recoverable` is what actually resumes work, and it reads that
       recorded value verbatim.
    5. "Reconciles uncertain GitHub effects before retrying them" - not yet applicable: no stage
       that performs a GitHub effect exists yet (G6's own scope). Nothing for this sweep to
       reconcile today; it cannot invent a reconciliation step for a mechanism that is not built.
    6. "Preserves accepted agentic outputs whose dependency hashes still match" - satisfied by
       restraint: this function only ever changes ``state``/``lease``/``failure``/
       ``recovery_count``. It never touches ``accepted_artifact``, ``dependencies``, or
       ``proposal``, so nothing it does can lose or invalidate already-accepted work.
    7. "Marks a transaction SUPERSEDED if a newer source revision owns the active work" -
       ``current_source_revisions`` (repository -> the registry's current observed revision);
       when it differs from the record's own ``source.revision``, the transaction is marked
       ``SUPERSEDED`` instead of ``RETRYABLE`` - its own inputs no longer describe the world this
       sweep would otherwise resume it into.
    """
    now = now or datetime.now(UTC)
    revisions = current_source_revisions or {}
    outcomes: list[RecoveryOutcome] = []

    for repository, provider_repository_id in repositories.items():
        record = backend.load(repository)
        if record is None or record.active_transaction_id is None:
            continue
        if record.state not in ACTIVE_STATES:
            continue  # terminal or quiescent: nothing in flight for this sweep to recover
        if lease_is_active(record.lease, now):
            continue  # a worker genuinely still owns this; not recovery's business

        outcome = _sweep_one(
            backend,
            repository,
            provider_repository_id,
            superseding_revision=revisions.get(repository),
            now=now,
        )
        if outcome is not None:
            outcomes.append(outcome)
    return outcomes


def _sweep_one(
    backend: StateBackend,
    repository: str,
    provider_repository_id: int,
    *,
    superseding_revision: str | None,
    now: datetime,
) -> RecoveryOutcome | None:
    captured: dict[str, str] = {}

    def patch(current: RepositoryRecord) -> RepositoryRecord:
        # Re-check everything inside the patch too: another writer may have raced this sweep
        # (reclaimed the lease, or completed the transaction) between the read above and this CAS
        # attempt - a decision made from stale data must never be committed blindly.
        if current.active_transaction_id is None or current.state not in ACTIVE_STATES:
            return current
        if lease_is_active(current.lease, now):
            return current

        is_superseded = (
            superseding_revision is not None
            and current.source is not None
            and current.source.revision != superseding_revision
        )
        captured["transaction_id"] = current.active_transaction_id
        captured["prior_state"] = current.state

        if is_superseded:
            captured["reason"] = "source_revision_superseded"
            # The lease field is deliberately left as-is, not nulled: it is already expired (the
            # guard above returned early otherwise), and leaving the real prior fencing token in
            # place - rather than resetting the record to "no lease ever existed" - is what lets a
            # future acquire issue a strictly higher token than the dead worker's, never token 1
            # again. Harmless here (SUPERSEDED has no "resume" path to protect), and kept
            # consistent with the RETRYABLE case below rather than special-cased.
            return current.model_copy(update={"state": "SUPERSEDED"})

        captured["reason"] = "stale_or_missing_lease"
        failure = FailureRecord(
            classification="transient",
            detail="recovery_sweep: nonterminal transaction had no valid lease",
            resume_state=current.state,
            occurred_at=now.isoformat(),
            recovery_count=current.recovery_count + 1,
        )
        # Same reasoning: the expired lease is left on the record (not nulled) so
        # resume_recoverable's own acquire_lease call later issues a strictly higher fencing token
        # than the dead worker's, satisfying section 14's "An expired worker cannot commit state
        # after a new fencing token is issued" even across this intermediate RETRYABLE state.
        return current.model_copy(
            update={
                "state": "RETRYABLE",
                "failure": failure,
                "recovery_count": current.recovery_count + 1,
            }
        )

    save_state_patch(backend, repository, patch, provider_repository_id=provider_repository_id)
    if "transaction_id" not in captured:
        return None
    return RecoveryOutcome(
        repository=repository,
        transaction_id=captured["transaction_id"],
        prior_state=captured["prior_state"],  # type: ignore[arg-type]
        reason=captured["reason"],
    )


def resume_recoverable(
    backend: StateBackend,
    repository: str,
    *,
    holder_id: str,
    provider_repository_id: int,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> tuple[RepositoryRecord, LeaseRecord] | None:
    """The next scheduling pass's own resume step (section 4.1's ``RETRYABLE`` row: "Previous
    active state through recovery").

    Acquires a fresh lease - a strictly higher fencing token than whatever the dead worker held, so
    it can never commit again even if it somehow wakes back up - and re-enters exactly the state
    :func:`recovery_sweep` recorded as this transaction's own resume point. Never ``OBSERVED``,
    never a guessed later stage: the same continuity guarantee section 15 requires.

    Returns ``None`` when ``repository`` is not currently ``RETRYABLE`` with a recorded resume
    state, or when another caller has already won the lease to resume it - this is not a
    speculative probe, and a caller should not treat ``None`` as an error.
    """
    now = now or datetime.now(UTC)
    record = backend.load(repository)
    if record is None or record.state != "RETRYABLE" or record.failure is None:
        return None
    resume_state = record.failure.resume_state

    lease = acquire_lease(
        backend,
        repository,
        holder_id=holder_id,
        provider_repository_id=provider_repository_id,
        lease_seconds=lease_seconds,
        now=now,
    )
    if lease is None:
        return None  # someone else is already resuming this transaction

    def patch(current: RepositoryRecord) -> RepositoryRecord:
        if current.state != "RETRYABLE" or current.failure is None:
            return current
        return current.model_copy(update={"state": resume_state, "failure": None})

    saved = save_state_patch(
        backend, repository, patch, provider_repository_id=provider_repository_id
    )
    return saved, lease
