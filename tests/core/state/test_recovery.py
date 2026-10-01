"""Recovery-before-scheduling (docs/STATE_MACHINE.md section 15) - the acceptance-bar scenarios:
a killed-mid-transaction process recovers cleanly without double-processing or losing the accepted
portion, and a stale lease is reclaimed after its own recorded timeout.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from repository_presenter.core.errors import IllegalTransitionError
from repository_presenter.core.state.cas import (
    acquire_lease,
    lease_is_current,
    record_transition,
    save_state_patch,
)
from repository_presenter.core.state.recovery import recovery_sweep, resume_recoverable
from repository_presenter.core.state.schema import DependencyHashes, SourceObservation
from support import InMemoryStateBackend

REPO = "aspose-3d-foss/example"
PROVIDER_ID = 42
LEASE_SECONDS = 900


def _start_transaction_at(backend: InMemoryStateBackend, *, state: str, now: datetime):
    """Simulate a transaction that has made real, durable progress: a lease, an active
    transaction id, a couple of accepted-looking dependency hashes, sitting in ``state``."""
    lease = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=LEASE_SECONDS,
        now=now,
    )
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(
            update={
                "active_transaction_id": "tx-1",
                "state": "SNAPSHOTTING",
                "source": SourceObservation(default_branch="main", revision="rev-1"),
            }
        ),
        provider_repository_id=PROVIDER_ID,
    )
    # One real, receipted transition commits dependency/evidence-shaped progress - exactly the
    # "accepted portion" recovery must not lose.
    record, _ = record_transition(
        backend,
        REPO,
        lease,
        to_state="EXTRACTING",
        event="immutable_snapshot_captured",
        input_manifest="sha256:source",
        output_manifest="sha256:tree",
        policy_version="sha256:policy",
        provider_repository_id=PROVIDER_ID,
        patch=lambda r: r.model_copy(
            update={"dependencies": DependencyHashes(facts="sha256:facts")}
        ),
    )
    if state == "EXTRACTING":
        return lease, record
    # The remaining hops to ``state`` are simulated directly (save_state_patch, not
    # record_transition) purely as test setup - transition-registry legality for every hop is
    # already covered by test_schema.py/test_cas.py; this fixture only needs a transaction
    # genuinely sitting in ``state`` with its dependencies intact and a lease held.
    record = save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"state": state}),
        provider_repository_id=PROVIDER_ID,
    )
    return lease, record


def test_a_killed_mid_transaction_process_recovers_without_losing_accepted_progress() -> None:
    """The acceptance bar, verbatim: a killed-mid-transaction process recovers cleanly on the
    next run without double-processing or losing the accepted portion."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    dead_lease, _ = _start_transaction_at(backend, state="VALIDATING", now=now)

    # The worker is killed here: it never releases the lease, never advances the transaction
    # further. No new trigger fires yet - the lease is simply left to expire.
    after_lease_expiry = now + timedelta(seconds=LEASE_SECONDS + 1)

    outcomes = recovery_sweep(backend, {REPO: PROVIDER_ID}, now=after_lease_expiry)
    assert len(outcomes) == 1
    assert outcomes[0].transaction_id == "tx-1"
    assert outcomes[0].prior_state == "VALIDATING"
    assert outcomes[0].reason == "stale_or_missing_lease"

    swept = backend.load(REPO)
    assert swept is not None
    assert swept.state == "RETRYABLE"
    # The expired lease is left on the record, not nulled: resume_recoverable's own acquire_lease
    # needs the dead worker's real fencing token to issue a strictly higher one later.
    assert swept.lease is not None
    assert swept.lease.holder_id == dead_lease.holder_id
    assert swept.active_transaction_id == "tx-1"  # same transaction, not a new one
    assert swept.failure is not None
    assert swept.failure.resume_state == "VALIDATING"  # never skips ahead or falls back
    assert swept.dependencies.facts == "sha256:facts"  # the accepted portion is not lost

    # A second sweep run (as the next scheduled pass would do) must not double-process: it is a
    # no-op once the transaction is no longer in an active state with a stale lease.
    again = recovery_sweep(
        backend, {REPO: PROVIDER_ID}, now=after_lease_expiry + timedelta(hours=1)
    )
    assert again == []

    # The next run resumes - not from OBSERVED, not from a guessed later stage - exactly where the
    # killed worker left off, under a fresh fencing token.
    resumed = resume_recoverable(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        now=after_lease_expiry,
    )
    assert resumed is not None
    resumed_record, new_lease = resumed
    assert resumed_record.state == "VALIDATING"
    assert resumed_record.active_transaction_id == "tx-1"
    assert resumed_record.dependencies.facts == "sha256:facts"
    assert new_lease.fencing_token > 1
    assert lease_is_current(backend, REPO, new_lease)

    # Negative control: the dead worker's own stale lease/fencing token can never commit again,
    # even after resumption - this is the literal "without double-processing" guarantee.
    with pytest.raises(IllegalTransitionError):
        record_transition(
            backend,
            REPO,
            dead_lease,
            to_state="REVIEWING",
            event="late-write-from-the-dead-worker",
            input_manifest="sha256:x",
            output_manifest="sha256:y",
            policy_version="sha256:policy",
            provider_repository_id=PROVIDER_ID,
        )


def test_an_actively_held_lease_is_never_swept() -> None:
    """Negative control: recovery must not interfere with genuinely in-flight work."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    _start_transaction_at(backend, state="COMPOSING", now=now)

    still_within_lease = now + timedelta(seconds=LEASE_SECONDS - 1)
    outcomes = recovery_sweep(backend, {REPO: PROVIDER_ID}, now=still_within_lease)
    assert outcomes == []
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "COMPOSING"
    assert record.lease is not None


def test_a_stale_lease_is_reclaimed_after_its_own_recorded_timeout() -> None:
    """Acceptance bar, verbatim: a stale lease is reclaimed after its own recorded timeout."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    original_lease, _ = _start_transaction_at(backend, state="COMPOSING", now=now)

    just_before_timeout = now + timedelta(seconds=LEASE_SECONDS - 1)
    assert recovery_sweep(backend, {REPO: PROVIDER_ID}, now=just_before_timeout) == []

    just_after_timeout = now + timedelta(seconds=LEASE_SECONDS + 1)
    outcomes = recovery_sweep(backend, {REPO: PROVIDER_ID}, now=just_after_timeout)
    assert len(outcomes) == 1

    resumed = resume_recoverable(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        now=just_after_timeout,
    )
    assert resumed is not None
    _, reclaimed_lease = resumed
    assert reclaimed_lease.fencing_token == original_lease.fencing_token + 1
    assert reclaimed_lease.holder_id == "worker-b"


def test_recovery_marks_a_transaction_superseded_when_source_revision_has_moved_on() -> None:
    """Section 15 point 7: a newer source revision supersedes stale in-flight work rather than
    resuming it into a world its own inputs no longer describe."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    _start_transaction_at(backend, state="PLANNING", now=now)

    after_lease_expiry = now + timedelta(seconds=LEASE_SECONDS + 1)
    outcomes = recovery_sweep(
        backend,
        {REPO: PROVIDER_ID},
        current_source_revisions={REPO: "rev-2"},  # the registry has since moved past rev-1
        now=after_lease_expiry,
    )
    assert len(outcomes) == 1
    assert outcomes[0].reason == "source_revision_superseded"
    record = backend.load(REPO)
    assert record is not None
    assert record.state == "SUPERSEDED"
    assert record.lease is not None  # the expired lease is preserved, not nulled (recovery.py)

    # A superseded transaction is never "resumable" - resume_recoverable only acts on RETRYABLE.
    assert (
        resume_recoverable(
            backend,
            REPO,
            holder_id="worker-b",
            provider_repository_id=PROVIDER_ID,
            now=after_lease_expiry,
        )
        is None
    )


def test_recovery_ignores_a_repository_with_no_active_transaction() -> None:
    backend = InMemoryStateBackend()
    save_state_patch(backend, REPO, lambda r: r, provider_repository_id=PROVIDER_ID)
    assert recovery_sweep(backend, {REPO: PROVIDER_ID}) == []


def test_resume_recoverable_is_none_for_a_repository_that_is_not_retryable() -> None:
    backend = InMemoryStateBackend()
    assert (
        resume_recoverable(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
        is None
    )


def test_resume_recoverable_only_ever_resumes_once() -> None:
    """Negative control: two resume attempts for the same retryable transaction must not both
    succeed - only one worker may pick up the recovered work."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    _start_transaction_at(backend, state="COMPOSING", now=now)
    after_lease_expiry = now + timedelta(seconds=LEASE_SECONDS + 1)
    recovery_sweep(backend, {REPO: PROVIDER_ID}, now=after_lease_expiry)

    first = resume_recoverable(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        now=after_lease_expiry,
    )
    assert first is not None

    second = resume_recoverable(
        backend,
        REPO,
        holder_id="worker-c",
        provider_repository_id=PROVIDER_ID,
        now=after_lease_expiry,
    )
    assert second is None
