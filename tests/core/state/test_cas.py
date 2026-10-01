"""The generic CAS, lease/fencing, and transition-commit mechanism (STATE_MACHINE.md 13-15, 17).

Uses ``support.InMemoryStateBackend`` - a real compare-and-swap contract with no git subprocess -
so these tests stay fast; ``test_git_backend.py`` separately proves the real ref-based backend.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from repository_presenter.core.errors import IllegalTransitionError, StateBackendError
from repository_presenter.core.state.cas import (
    acquire_lease,
    lease_is_current,
    record_transition,
    release_lease,
    renew_lease,
    save_state_patch,
)
from support import InMemoryStateBackend

REPO = "aspose-3d-foss/example"
PROVIDER_ID = 42


def test_save_state_patch_creates_a_fresh_record_on_first_write() -> None:
    backend = InMemoryStateBackend()
    record = save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"state": "SNAPSHOTTING"}),
        provider_repository_id=PROVIDER_ID,
    )
    assert record.state == "SNAPSHOTTING"
    assert record.state_version == 1
    assert backend.load(REPO) == record


def test_save_state_patch_no_op_patch_never_writes() -> None:
    """A patch that returns its input unchanged must not bump state_version - cheap no-op proof."""
    backend = InMemoryStateBackend()
    save_state_patch(backend, REPO, lambda r: r, provider_repository_id=PROVIDER_ID)
    first = backend.load(REPO)
    assert first is not None
    save_state_patch(backend, REPO, lambda r: r, provider_repository_id=PROVIDER_ID)
    assert backend.load(REPO) == first


def test_save_state_patch_retries_through_a_concurrent_writer() -> None:
    """Two independent patches racing the same CAS must both converge, never lose an update."""
    backend = InMemoryStateBackend()
    save_state_patch(backend, REPO, lambda r: r, provider_repository_id=PROVIDER_ID)

    real_save = backend.save
    calls = {"n": 0}

    def interleaved_save(repository: str, record: object, expected_version: int | None) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            # Simulate a second writer winning the race between this attempt's read and its write.
            other = save_state_patch(
                InMemoryStateBackendProxy(backend),
                repository,
                lambda r: r.model_copy(update={"recovery_count": r.recovery_count + 1}),
                provider_repository_id=PROVIDER_ID,
            )
            assert other.recovery_count == 1
        return real_save(repository, record, expected_version)

    backend.save = interleaved_save  # type: ignore[method-assign]
    result = save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"state": "EXTRACTING"}),
        provider_repository_id=PROVIDER_ID,
    )
    assert result.state == "EXTRACTING"
    assert result.recovery_count == 1  # the interleaved writer's update was not lost
    assert result.state_version == 3  # v1 create, v2 interleaved writer, v3 this attempt's retry


class InMemoryStateBackendProxy:
    """Delegates to a shared backend without creating a second independent store."""

    def __init__(self, backend: InMemoryStateBackend) -> None:
        self._backend = backend

    def load(self, repository: str):
        return self._backend.load(repository)

    def save(self, repository: str, record: object, expected_version: int | None):
        return InMemoryStateBackend.save(self._backend, repository, record, expected_version)


def test_acquire_lease_grants_an_unheld_lease_with_fencing_token_one() -> None:
    backend = InMemoryStateBackend()
    lease = acquire_lease(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
    assert lease is not None
    assert lease.fencing_token == 1
    assert lease_is_current(backend, REPO, lease)


def test_acquire_lease_refuses_while_another_holder_is_unexpired() -> None:
    backend = InMemoryStateBackend()
    first = acquire_lease(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
    assert first is not None
    second = acquire_lease(backend, REPO, holder_id="worker-b", provider_repository_id=PROVIDER_ID)
    assert second is None  # negative control: concurrent acquire must not silently double-grant


def test_acquire_lease_reclaims_an_expired_lease_with_a_strictly_higher_fencing_token() -> None:
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,
        now=now,
    )
    assert first is not None and first.fencing_token == 1
    later = now + timedelta(seconds=61)
    second = acquire_lease(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=900,
        now=later,
    )
    assert second is not None
    assert second.holder_id == "worker-b"
    assert second.fencing_token == 2  # strictly higher than the reclaimed worker-a's token


def test_renew_lease_extends_without_changing_the_fencing_token() -> None:
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    lease = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,
        now=now,
    )
    assert lease is not None
    renewed = renew_lease(
        backend,
        REPO,
        lease,
        provider_repository_id=PROVIDER_ID,
        lease_seconds=900,
        now=now + timedelta(seconds=30),
    )
    assert renewed is not None
    assert renewed.fencing_token == lease.fencing_token
    assert renewed.expires_at != lease.expires_at


def test_renew_lease_fails_once_the_fencing_token_has_been_superseded() -> None:
    """Negative control: a worker whose lease was reclaimed cannot resurrect it by renewing."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    stale = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,
        now=now,
    )
    assert stale is not None
    acquire_lease(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=900,
        now=now + timedelta(seconds=61),
    )
    renewed = renew_lease(
        backend,
        REPO,
        stale,
        provider_repository_id=PROVIDER_ID,
        now=now + timedelta(seconds=62),
    )
    assert renewed is None


def test_release_lease_only_removes_its_own_holder_and_fencing_token() -> None:
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    stale = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,
        now=now,
    )
    assert stale is not None
    reclaimed = acquire_lease(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=900,
        now=now + timedelta(seconds=61),
    )
    assert reclaimed is not None
    # worker-a's belated release must not destroy worker-b's legitimate, currently-held lease.
    release_lease(backend, REPO, stale, provider_repository_id=PROVIDER_ID)
    assert lease_is_current(backend, REPO, reclaimed)


def test_record_transition_commits_state_and_receipt_together() -> None:
    backend = InMemoryStateBackend()
    lease = acquire_lease(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"active_transaction_id": "tx-1", "state": "SNAPSHOTTING"}),
        provider_repository_id=PROVIDER_ID,
    )
    record, receipt = record_transition(
        backend,
        REPO,
        lease,
        to_state="EXTRACTING",
        event="immutable_snapshot_captured",
        input_manifest="sha256:in",
        output_manifest="sha256:out",
        policy_version="sha256:policy",
        provider_repository_id=PROVIDER_ID,
    )
    assert record.state == "EXTRACTING"
    assert record.last_transition == receipt
    assert receipt.from_state == "SNAPSHOTTING"
    assert receipt.to_state == "EXTRACTING"
    assert receipt.transaction_id == "tx-1"
    assert receipt.fencing_token == lease.fencing_token


def test_record_transition_rejects_an_unregistered_transition() -> None:
    """Negative control: an illegal state transition must never be silently accepted."""
    backend = InMemoryStateBackend()
    lease = acquire_lease(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
    assert lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"active_transaction_id": "tx-1", "state": "OBSERVED"}),
        provider_repository_id=PROVIDER_ID,
    )
    with pytest.raises(IllegalTransitionError):
        record_transition(
            backend,
            REPO,
            lease,
            to_state="ACCEPTED",
            event="skip-ahead",
            input_manifest="sha256:in",
            output_manifest="sha256:out",
            policy_version="sha256:policy",
            provider_repository_id=PROVIDER_ID,
        )


def test_record_transition_rejects_a_stale_fencing_token() -> None:
    """Negative control: a worker whose lease was reclaimed cannot commit a transition afterward
    (docs/STATE_MACHINE.md section 14: "An expired worker cannot commit state after a new fencing
    token is issued")."""
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    stale_lease = acquire_lease(
        backend,
        REPO,
        holder_id="worker-a",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=60,
        now=now,
    )
    assert stale_lease is not None
    save_state_patch(
        backend,
        REPO,
        lambda r: r.model_copy(update={"active_transaction_id": "tx-1", "state": "OBSERVED"}),
        provider_repository_id=PROVIDER_ID,
    )
    acquire_lease(
        backend,
        REPO,
        holder_id="worker-b",
        provider_repository_id=PROVIDER_ID,
        lease_seconds=900,
        now=now + timedelta(seconds=61),
    )
    with pytest.raises(IllegalTransitionError):
        record_transition(
            backend,
            REPO,
            stale_lease,
            to_state="SNAPSHOTTING",
            event="late-write-from-dead-worker",
            input_manifest="sha256:in",
            output_manifest="sha256:out",
            policy_version="sha256:policy",
            provider_repository_id=PROVIDER_ID,
        )


def test_record_transition_requires_an_active_transaction() -> None:
    backend = InMemoryStateBackend()
    lease = acquire_lease(backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID)
    assert lease is not None
    with pytest.raises(IllegalTransitionError):
        record_transition(
            backend,
            REPO,
            lease,
            to_state="SNAPSHOTTING",
            event="no-transaction",
            input_manifest="sha256:in",
            output_manifest="sha256:out",
            policy_version="sha256:policy",
            provider_repository_id=PROVIDER_ID,
        )


def test_save_state_patch_raises_state_backend_error_when_retries_are_exhausted() -> None:
    backend = InMemoryStateBackend()
    save_state_patch(backend, REPO, lambda r: r, provider_repository_id=PROVIDER_ID)
    real_save = backend.save
    backend.save = lambda repository, record, expected_version: real_save(  # type: ignore[method-assign]
        repository, record, -1
    )
    with pytest.raises(StateBackendError):
        save_state_patch(
            backend,
            REPO,
            lambda r: r.model_copy(update={"state": "SNAPSHOTTING"}),
            provider_repository_id=PROVIDER_ID,
            max_retries=2,
        )
