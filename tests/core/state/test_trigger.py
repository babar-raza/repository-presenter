"""Trigger normalization and dedup (docs/STATE_MACHINE.md section 3.2)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from repository_presenter.core.errors import StateBackendError
from repository_presenter.core.state.cas import lease_is_current, release_lease
from repository_presenter.core.state.trigger import (
    MAX_TRIGGER_DEDUP_ENTRIES,
    admit_trigger,
    normalize_trigger,
)
from support import InMemoryStateBackend

REPO = "aspose-3d-foss/example"
PROVIDER_ID = 42


def test_schedule_dedup_key_is_stable_per_window() -> None:
    first = normalize_trigger(REPO, event_type="schedule", schedule_window="2026-10-01-daily")
    second = normalize_trigger(REPO, event_type="schedule", schedule_window="2026-10-01-daily")
    assert first.dedup_key == second.dedup_key


def test_schedule_requires_a_window() -> None:
    with pytest.raises(StateBackendError):
        normalize_trigger(REPO, event_type="schedule")


def test_repository_dispatch_requires_a_delivery_or_provider_id() -> None:
    with pytest.raises(StateBackendError):
        normalize_trigger(REPO, event_type="repository_dispatch")


def test_workflow_dispatch_dedup_key_is_scoped_per_repository() -> None:
    envelope = normalize_trigger(REPO, event_type="workflow_dispatch", workflow_run_id="run-1")
    other_repo = normalize_trigger(
        "aspose-3d-foss/other", event_type="workflow_dispatch", workflow_run_id="run-1"
    )
    assert envelope.dedup_key != other_repo.dedup_key


def test_admit_trigger_accepts_the_first_trigger_for_a_repository() -> None:
    backend = InMemoryStateBackend()
    envelope = normalize_trigger(REPO, event_type="schedule", schedule_window="w1")
    admission = admit_trigger(
        backend, envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert admission.outcome == "accepted"
    assert admission.lease is not None
    assert admission.record.active_transaction_id == admission.transaction_id
    assert lease_is_current(backend, REPO, admission.lease)


def test_admit_trigger_deduplicates_a_concurrent_trigger_for_the_same_revision() -> None:
    """Acceptance bar: two concurrent triggers for the same repository/revision deduplicate to
    one transaction."""
    backend = InMemoryStateBackend()
    envelope = normalize_trigger(
        REPO, event_type="workflow_dispatch", workflow_run_id="run-1", source_revision="abc123"
    )
    first = admit_trigger(
        backend, envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert first.outcome == "accepted"

    # A second, concurrent trigger for the same repository/revision (e.g. a retried workflow
    # dispatch, or an overlapping scheduled run) must fold into the same transaction, never spawn
    # a second one.
    second = admit_trigger(
        backend, envelope, holder_id="worker-b", provider_repository_id=PROVIDER_ID
    )
    assert second.outcome == "deduplicated"
    assert second.transaction_id == first.transaction_id
    assert second.lease is None  # the second caller never gets its own exclusive lease

    # worker-a's lease remains the sole active one; worker-b never acquired a competing lease.
    assert first.lease is not None
    assert lease_is_current(backend, REPO, first.lease)


def test_admit_trigger_deduplicates_a_genuinely_different_trigger_while_one_is_in_flight() -> None:
    """Even a *different* dedup_key folds into the already-active transaction - only one
    transaction may be active per repository at a time (section 14)."""
    backend = InMemoryStateBackend()
    first_envelope = normalize_trigger(REPO, event_type="schedule", schedule_window="w1")
    first = admit_trigger(
        backend, first_envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert first.outcome == "accepted"

    different_envelope = normalize_trigger(
        REPO, event_type="repository_dispatch", delivery_id="delivery-xyz"
    )
    second = admit_trigger(
        backend, different_envelope, holder_id="worker-b", provider_repository_id=PROVIDER_ID
    )
    assert second.outcome == "deduplicated"
    assert second.transaction_id == first.transaction_id


def test_admit_trigger_recognizes_a_replay_after_the_transaction_has_finished() -> None:
    """A late, exact-duplicate delivery of an already-folded-in trigger must still be recognized
    once the lease that was active at the time has since been released - never silently starting
    a second transaction for the same logical event."""
    backend = InMemoryStateBackend()
    envelope = normalize_trigger(REPO, event_type="repository_dispatch", delivery_id="delivery-1")
    first = admit_trigger(
        backend, envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert first.lease is not None

    release_lease(backend, REPO, first.lease, provider_repository_id=PROVIDER_ID)

    replay = admit_trigger(
        backend, envelope, holder_id="worker-c", provider_repository_id=PROVIDER_ID
    )
    assert replay.outcome == "deduplicated"
    assert replay.transaction_id == first.transaction_id
    assert replay.lease is None


def test_admit_trigger_issues_a_new_transaction_once_the_lease_is_genuinely_free() -> None:
    """A different, later trigger (new dedup_key, no lease held) legitimately starts the next
    transaction - deduplication must never become a permanent block."""
    backend = InMemoryStateBackend()
    first_envelope = normalize_trigger(REPO, event_type="schedule", schedule_window="w1")
    first = admit_trigger(
        backend, first_envelope, holder_id="worker-a", provider_repository_id=PROVIDER_ID
    )
    assert first.lease is not None

    release_lease(backend, REPO, first.lease, provider_repository_id=PROVIDER_ID)

    second_envelope = normalize_trigger(REPO, event_type="schedule", schedule_window="w2")
    second = admit_trigger(
        backend, second_envelope, holder_id="worker-b", provider_repository_id=PROVIDER_ID
    )
    assert second.outcome == "accepted"
    assert second.transaction_id != first.transaction_id


def test_admit_trigger_dedup_ledger_is_bounded() -> None:
    backend = InMemoryStateBackend()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(MAX_TRIGGER_DEDUP_ENTRIES + 10):
        envelope = normalize_trigger(
            REPO, event_type="workflow_dispatch", workflow_run_id=f"run-{index}"
        )
        admission = admit_trigger(
            backend,
            envelope,
            holder_id=f"worker-{index}",
            provider_repository_id=PROVIDER_ID,
            now=now,
        )
        assert admission.lease is not None
        release_lease(backend, REPO, admission.lease, provider_repository_id=PROVIDER_ID)
    record = backend.load(REPO)
    assert record is not None
    assert len(record.recent_trigger_dedup_keys) <= MAX_TRIGGER_DEDUP_ENTRIES
