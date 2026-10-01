"""Backend-independent durable-state interface and the shared compare-and-swap retry helpers.

Ported in shape from the legacy ``readme_agent.state.backend``/``state.cas`` modules
(``MEM-003``'s "interface + at least one real backend" bar; ``migration/reuse-manifest.yaml``): a
``Protocol`` so the real git-ref backend (``git_backend.py``) and a fast in-memory test double
implement the same contract, and one shared bounded-retry CAS patch helper every caller reuses
instead of hand-rolling its own retry loop. The lease/fencing and transition-commit helpers below
are written fresh against this project's single-record-per-repository shape (``schema.py``), not
legacy's three separate lock-ref families.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from uuid import uuid4

from repository_presenter.core.errors import IllegalTransitionError, StateBackendError
from repository_presenter.core.retry import RETRY_POLICIES, RetryableOperationError, run_with_retry
from repository_presenter.core.state.schema import (
    LeaseRecord,
    RepositoryRecord,
    TransactionState,
    TransitionReceipt,
    is_registered_transition,
)

SaveOutcome = Literal["saved", "stale"]

# Long enough for one real present transaction (clone + LLM calls + validate); short enough a
# genuine crash does not block the next scheduled run for long. Matches legacy's own
# LOCK_LEASE_SECONDS starting value (docs/STATE_MACHINE.md section 14).
DEFAULT_LEASE_SECONDS = 900


@dataclass(frozen=True)
class SaveResult:
    """``record`` is the record actually persisted on ``"saved"``, or the backend's current record
    on ``"stale"`` (so a caller can inspect what won without a second read)."""

    outcome: SaveOutcome
    record: RepositoryRecord | None


class StateBackend(Protocol):
    """One independently updateable CAS record per repository (STATE_MACHINE.md section 13.2)."""

    def load(self, repository: str) -> RepositoryRecord | None: ...

    def save(
        self, repository: str, record: RepositoryRecord, expected_version: int | None
    ) -> SaveResult:
        """Compare-and-swap: rejected with ``outcome="stale"`` if the backend's current
        ``state_version`` no longer matches ``expected_version``. ``expected_version=None`` is only
        valid for a repository with no durable record yet."""
        ...


RepositoryPatch = Callable[[RepositoryRecord], RepositoryRecord]


def _default_record(repository: str, provider_repository_id: int) -> RepositoryRecord:
    return RepositoryRecord(repository=repository, provider_repository_id=provider_repository_id)


def save_state_patch(
    backend: StateBackend,
    repository: str,
    patch: RepositoryPatch,
    *,
    provider_repository_id: int,
    max_retries: int = RETRY_POLICIES["state_cas"].max_attempts,
) -> RepositoryRecord:
    """Apply one fresh-state patch under the shared bounded CAS policy.

    ``patch`` must be pure and idempotent: it may be called more than once (once per CAS retry)
    against a freshly reloaded base record each time. A patch that returns its input unchanged
    short-circuits to a plain read - no write, no version bump.
    """

    def attempt() -> RepositoryRecord:
        current = backend.load(repository)
        expected_version = current.state_version if current is not None else None
        base = current or _default_record(repository, provider_repository_id)
        updated = patch(base)
        if current is not None and updated == current:
            return current
        result = backend.save(repository, updated, expected_version)
        if result.outcome == "saved":
            if result.record is None:  # pragma: no cover - defensive, contract violation
                raise StateBackendError(
                    f"backend reported 'saved' with no record for {repository!r}"
                )
            return result.record
        raise RetryableOperationError(
            f"durable-state CAS for {repository!r} observed a stale version"
        )

    try:
        return run_with_retry("state_cas", attempt, max_attempts=max_retries)
    except RetryableOperationError as exc:
        raise StateBackendError(
            f"durable-state save for {repository!r} did not converge after {max_retries} attempts"
        ) from exc


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _lease_is_active(lease: LeaseRecord | None, now: datetime) -> bool:
    return lease is not None and _parse_iso(lease.expires_at) > now


def _lease_matches(current: LeaseRecord | None, lease: LeaseRecord) -> bool:
    """Same holder, same fencing token - the only two facts that identify "this exact lease"."""
    return (
        current is not None
        and current.holder_id == lease.holder_id
        and current.fencing_token == lease.fencing_token
    )


def acquire_lease(
    backend: StateBackend,
    repository: str,
    *,
    holder_id: str,
    provider_repository_id: int,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> LeaseRecord | None:
    """Non-blocking optimistic acquire. ``None`` means another holder has an unexpired lease.

    A reclaim (the prior lease, if any, has expired) issues a strictly higher ``fencing_token`` -
    docs/STATE_MACHINE.md section 14: "An expired worker cannot commit state after a new fencing
    token is issued".
    """
    now = now or datetime.now(UTC)
    won: dict[str, LeaseRecord | None] = {"lease": None}

    def patch(record: RepositoryRecord) -> RepositoryRecord:
        if _lease_is_active(record.lease, now):
            won["lease"] = None
            return record
        new_token = record.lease.fencing_token + 1 if record.lease is not None else 1
        lease = LeaseRecord(
            holder_id=holder_id,
            acquired_at=now.isoformat(),
            heartbeat_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=lease_seconds)).isoformat(),
            fencing_token=new_token,
        )
        won["lease"] = lease
        return record.model_copy(update={"lease": lease})

    save_state_patch(backend, repository, patch, provider_repository_id=provider_repository_id)
    return won["lease"]


def renew_lease(
    backend: StateBackend,
    repository: str,
    lease: LeaseRecord,
    *,
    provider_repository_id: int,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> LeaseRecord | None:
    """Extend ``lease`` without changing its fencing token. ``None`` means ownership was lost -
    someone else's holder/fencing token is now on record, which can only happen after this
    holder's own lease already expired and was reclaimed."""
    now = now or datetime.now(UTC)
    won: dict[str, LeaseRecord | None] = {"lease": None}

    def patch(record: RepositoryRecord) -> RepositoryRecord:
        current = record.lease
        if not _lease_matches(current, lease):
            won["lease"] = None
            return record
        assert current is not None
        renewed = current.model_copy(
            update={
                "heartbeat_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=lease_seconds)).isoformat(),
            }
        )
        won["lease"] = renewed
        return record.model_copy(update={"lease": renewed})

    save_state_patch(backend, repository, patch, provider_repository_id=provider_repository_id)
    return won["lease"]


def release_lease(
    backend: StateBackend, repository: str, lease: LeaseRecord, *, provider_repository_id: int
) -> None:
    """Best-effort compare-and-swap release: only ever clears the lease this exact holder+fencing
    token put there. A failure is swallowed - the lease self-heals via expiry either way (the same
    "released but the push itself failed is not a new risk" reasoning as legacy's
    ``safe_release_lock``), so a transient release failure must never mask an already-successful
    transition result in a caller's ``finally:`` block."""

    def patch(record: RepositoryRecord) -> RepositoryRecord:
        if not _lease_matches(record.lease, lease):
            return record  # already reclaimed by someone else; nothing of ours to remove
        return record.model_copy(update={"lease": None})

    with contextlib.suppress(StateBackendError):
        save_state_patch(backend, repository, patch, provider_repository_id=provider_repository_id)


def lease_is_current(backend: StateBackend, repository: str, lease: LeaseRecord) -> bool:
    """Fresh read: is ``lease`` still the exclusive, un-reclaimed lease on ``repository`` right now?

    Checked by holder identity *and* fencing token, not wall-clock alone - the same reasoning as
    legacy's ``lock_still_held``: a lease that has technically ticked past its nominal duration but
    was never actually reclaimed is still genuinely exclusive.
    """
    record = backend.load(repository)
    return (
        record is not None
        and record.lease is not None
        and record.lease.holder_id == lease.holder_id
        and record.lease.fencing_token == lease.fencing_token
    )


def record_transition(
    backend: StateBackend,
    repository: str,
    lease: LeaseRecord,
    *,
    to_state: TransactionState,
    event: str,
    input_manifest: str,
    output_manifest: str,
    policy_version: str,
    provider_repository_id: int,
    patch: RepositoryPatch | None = None,
    now: datetime | None = None,
) -> tuple[RepositoryRecord, TransitionReceipt]:
    """Commit one validated state transition under a held lease, with its receipt.

    This is the one generic, deterministic "advance durable state" primitive every future stage
    implementation calls (``AGENTS.md``'s agentic/deterministic boundary: an LLM proposes typed
    outputs, deterministic code is what "advances durable state ... asserts a deterministic gate
    result"). It enforces every one of docs/STATE_MACHINE.md section 17's rejection rules before
    writing: transition-registry membership, the record's current state matching ``from``, and the
    caller's lease/fencing token still being current - raising
    :class:`~repository_presenter.core.errors.IllegalTransitionError` otherwise, never silently
    coercing an illegal request into a legal one.

    ``patch`` may additionally update other record fields (dependencies, accepted_artifact, ...) as
    part of the same atomic write; it runs before the state/receipt fields are set, so it cannot
    override them.
    """
    now = now or datetime.now(UTC)
    minted: dict[str, TransitionReceipt] = {}

    def do_patch(record: RepositoryRecord) -> RepositoryRecord:
        if not _lease_matches(record.lease, lease):
            raise IllegalTransitionError(
                f"transition for {repository!r} rejected: lease/fencing token is stale"
            )
        if record.active_transaction_id is None:
            raise IllegalTransitionError(
                f"transition for {repository!r} rejected: no active transaction"
            )
        if not is_registered_transition(record.state, to_state):
            raise IllegalTransitionError(
                f"transition {record.state!r} -> {to_state!r} is not in the transition registry"
            )
        # Constructed via model_validate(), not keyword arguments: "from"/"to" are the model's
        # real (aliased) field names per section 17's verbatim wire shape, and "from" is a Python
        # keyword, so it can never be passed as a keyword argument at all.
        receipt = TransitionReceipt.model_validate(
            {
                "transition_id": uuid4().hex,
                "transaction_id": record.active_transaction_id,
                "repository": repository,
                "from": record.state,
                "to": to_state,
                "event": event,
                "occurred_at": now.isoformat(),
                "input_manifest": input_manifest,
                "output_manifest": output_manifest,
                "policy_version": policy_version,
                "fencing_token": lease.fencing_token,
            }
        )
        minted["receipt"] = receipt
        base = patch(record) if patch is not None else record
        return base.model_copy(update={"state": to_state, "last_transition": receipt})

    saved = save_state_patch(
        backend, repository, do_patch, provider_repository_id=provider_repository_id
    )
    return saved, minted["receipt"]
