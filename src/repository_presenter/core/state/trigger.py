"""Normalize provider trigger events into immutable envelopes and deduplicate them against
durable state before a transaction starts (docs/STATE_MACHINE.md section 3.2).

Ported in shape from legacy ``readme_agent.state.trigger_v2`` (``migration/reuse-manifest.yaml``):
the ``dedup_key`` construction rules per event type carry over the same durable idea - derive a
stable identity from whatever each trigger source actually guarantees is unique, never the whole
event payload - adapted to this project's own trigger vocabulary (section 3.2's table) rather than
legacy's own event-type list. ``admit_trigger`` is written fresh: it folds deduplication and the
repository-scoped lease into one CAS operation against this project's single-record
``RepositoryRecord`` (``schema.py``), where legacy tracked trigger lifecycles in a separate,
larger structure this project does not carry over.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import uuid4

from repository_presenter.core.errors import StateBackendError
from repository_presenter.core.state.cas import (
    DEFAULT_LEASE_SECONDS,
    StateBackend,
    lease_is_active,
    save_state_patch,
)
from repository_presenter.core.state.schema import LeaseRecord, RepositoryRecord

# docs/STATE_MACHINE.md section 3.2's trigger table, one event type per row (the three "Scheduled
# ..." rows share one "schedule" type, disambiguated by schedule_window).
TriggerEventType = Literal[
    "schedule",
    "repository_dispatch",
    "workflow_dispatch",
    "workflow_call",
    "manual_dispatch",
    "recovery",
]

# Bounds RepositoryRecord.recent_trigger_dedup_keys so a long-lived repository record's dedup
# ledger cannot grow without bound across its lifetime - see schema.py's own field docstring.
MAX_TRIGGER_DEDUP_ENTRIES = 50


@dataclass(frozen=True)
class TriggerEnvelope:
    """Normalized identity for one trigger event, independent of its original transport shape."""

    repository: str
    event_type: TriggerEventType
    dedup_key: str
    provider_event_id: str | None = None
    delivery_id: str | None = None
    workflow_run_id: str | None = None
    source_revision: str | None = None
    schedule_window: str | None = None
    occurred_at: str = ""


def normalize_trigger(
    repository: str,
    *,
    event_type: TriggerEventType,
    provider_event_id: str | None = None,
    delivery_id: str | None = None,
    workflow_run_id: str | None = None,
    source_revision: str | None = None,
    schedule_window: str | None = None,
    occurred_at: str | None = None,
) -> TriggerEnvelope:
    """docs/STATE_MACHINE.md section 3.2: "Duplicate trigger identities are acknowledged without
    creating duplicate repository transactions or provider calls" - ``dedup_key`` is the one
    stable identity each event type actually guarantees is unique, never a hash of the whole
    envelope (two genuinely distinct deliveries of the very same logical event must collapse to
    the same key).

    Raises :class:`~repository_presenter.core.errors.StateBackendError` when the event type's own
    required identity is missing - fails closed rather than guessing a dedup key that could
    collide with, or fail to recognize, a genuinely different trigger.
    """
    if event_type == "schedule":
        if not schedule_window:
            raise StateBackendError("a schedule trigger requires a stable schedule_window")
        dedup_key = f"schedule:{repository}:{schedule_window}"
    elif event_type == "repository_dispatch":
        identity = delivery_id or provider_event_id
        if not identity:
            raise StateBackendError(
                "a repository_dispatch trigger requires a delivery or provider event id"
            )
        dedup_key = f"delivery:{identity}"
    elif event_type in ("workflow_dispatch", "workflow_call"):
        identity = workflow_run_id or provider_event_id
        if not identity:
            raise StateBackendError(f"a {event_type} trigger requires a workflow run identity")
        dedup_key = f"run:{identity}:{repository}"
    elif event_type == "recovery":
        identity = provider_event_id
        if not identity:
            raise StateBackendError(
                "a recovery trigger requires the original trigger's own identity"
            )
        dedup_key = f"recovery:{identity}:{repository}"
    else:
        identity = provider_event_id or workflow_run_id
        if not identity:
            raise StateBackendError(f"a {event_type} trigger requires a provider identity")
        dedup_key = f"manual:{identity}:{repository}"

    provider_id = provider_event_id or delivery_id or workflow_run_id or schedule_window
    assert provider_id is not None  # one of the branches above already required it
    return TriggerEnvelope(
        repository=repository,
        event_type=event_type,
        dedup_key=dedup_key,
        provider_event_id=provider_id,
        delivery_id=delivery_id,
        workflow_run_id=workflow_run_id,
        source_revision=source_revision,
        schedule_window=schedule_window,
        occurred_at=occurred_at or datetime.now(UTC).isoformat(),
    )


TriggerOutcome = Literal["accepted", "deduplicated"]


@dataclass(frozen=True)
class TriggerAdmission:
    """``lease`` is set only when ``outcome == "accepted"`` - a deduplicated trigger never gets
    its own lease; it is folded into whichever transaction already owns ``transaction_id``."""

    outcome: TriggerOutcome
    transaction_id: str
    record: RepositoryRecord
    lease: LeaseRecord | None


def _bounded_put(mapping: dict[str, str], key: str, value: str, *, limit: int) -> dict[str, str]:
    if mapping.get(key) == value:
        return mapping
    updated = dict(mapping)
    updated[key] = value
    if len(updated) > limit:
        for stale_key in list(updated)[: len(updated) - limit]:
            del updated[stale_key]
    return updated


def admit_trigger(
    backend: StateBackend,
    envelope: TriggerEnvelope,
    *,
    holder_id: str,
    provider_repository_id: int,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> TriggerAdmission:
    """One CAS operation: fold a duplicate trigger into whatever transaction already owns its
    ``dedup_key`` or the repository's current in-flight transaction, or mint a fresh transaction
    when the repository's lease is free.

    A trigger arriving while *any* lease is held folds into ``"deduplicated"`` regardless of
    whether its own ``dedup_key`` was ever seen before: docs/STATE_MACHINE.md section 14 permits
    only one active transaction per repository at a time, so from the caller's perspective "a
    second, distinct trigger arrived mid-transaction" and "an exact duplicate delivery arrived"
    are the same outcome - both reduce to the one transaction already running, which section 3.2
    requires regardless of which specific trigger happens to be the one in flight. The folded-in
    trigger's own ``dedup_key`` is still recorded against that transaction, so a later exact
    replay of it (after the transaction has already finished and released its lease) is
    recognized too, rather than starting a second transaction for the same logical event.
    """
    now = now or datetime.now(UTC)
    outcome_box: dict[str, str | LeaseRecord] = {}

    def patch(record: RepositoryRecord) -> RepositoryRecord:
        known_transaction = record.recent_trigger_dedup_keys.get(envelope.dedup_key)
        if known_transaction is not None:
            outcome_box["outcome"] = "deduplicated"
            outcome_box["transaction_id"] = known_transaction
            return record

        if lease_is_active(record.lease, now):
            assert record.active_transaction_id is not None
            outcome_box["outcome"] = "deduplicated"
            outcome_box["transaction_id"] = record.active_transaction_id
            updated_keys = _bounded_put(
                record.recent_trigger_dedup_keys,
                envelope.dedup_key,
                record.active_transaction_id,
                limit=MAX_TRIGGER_DEDUP_ENTRIES,
            )
            return record.model_copy(update={"recent_trigger_dedup_keys": updated_keys})

        transaction_id = uuid4().hex
        new_token = record.lease.fencing_token + 1 if record.lease is not None else 1
        lease = LeaseRecord(
            holder_id=holder_id,
            acquired_at=now.isoformat(),
            heartbeat_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=lease_seconds)).isoformat(),
            fencing_token=new_token,
        )
        outcome_box["outcome"] = "accepted"
        outcome_box["transaction_id"] = transaction_id
        outcome_box["lease"] = lease
        updated_keys = _bounded_put(
            record.recent_trigger_dedup_keys,
            envelope.dedup_key,
            transaction_id,
            limit=MAX_TRIGGER_DEDUP_ENTRIES,
        )
        return record.model_copy(
            update={
                "active_transaction_id": transaction_id,
                "lease": lease,
                "recent_trigger_dedup_keys": updated_keys,
            }
        )

    saved = save_state_patch(
        backend, envelope.repository, patch, provider_repository_id=provider_repository_id
    )
    outcome = outcome_box["outcome"]
    transaction_id = outcome_box["transaction_id"]
    lease_value = outcome_box.get("lease")
    assert outcome in ("accepted", "deduplicated")
    assert isinstance(transaction_id, str)
    assert lease_value is None or isinstance(lease_value, LeaseRecord)
    return TriggerAdmission(
        outcome=cast(TriggerOutcome, outcome),
        transaction_id=transaction_id,
        record=saved,
        lease=lease_value,
    )
