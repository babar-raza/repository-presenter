"""The durable repository record (``docs/STATE_MACHINE.md`` section 13.1) and the transition
registry it is updated through (section 17).

Ported in spirit from the legacy ``readme_agent.state.schema``/``lifecycle_schema`` modules
(``migration/reuse-manifest.yaml``), but the shape itself is written fresh against this project's
own 23-state repository transaction machine (``docs/STATE_MACHINE.md`` section 4.1) rather than
carrying over the legacy ``RunStateV1``/``RunStateV2`` lifecycle fields, which encode a different,
retired mission/capability model (``AGENTS.md``: "a legacy module is not exempt for having run in
production").

``docs/STATE_MACHINE.md`` section 13.1's YAML is illustrative, not exhaustive: it has no field for
the CAS version a compare-and-swap backend needs, nor for the trigger-dedup ledger section 3.2
requires ("Duplicate trigger identities are acknowledged without creating duplicate repository
transactions"). Both are added here as implementation-necessary fields (``state_version``,
``recent_trigger_dedup_keys``), called out individually below.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

REPOSITORY_PATTERN = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"

# The full repository-transaction vocabulary, docs/STATE_MACHINE.md section 4.1's table, column 1,
# read top to bottom.
TransactionState = Literal[
    "OBSERVED",
    "NON_PROCESSABLE",
    "UNCHANGED",
    "SNAPSHOTTING",
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
    "VALIDATING",
    "REVIEWING",
    "REPAIRING",
    "ACCEPTED",
    "PROVING_NO_OP",
    "READY_FOR_PROPOSAL",
    "AWAITING_AUTHORIZATION",
    "PROPOSING",
    "MONITORING",
    "INVALIDATED",
    "RETRYABLE",
    "BLOCKED_EXTERNAL",
    "FAILED_INTERNAL",
    "SUPERSEDED",
]

# Section 4.1's "Active"/"Agentic"/"Deterministic"/"Mixed"/"Write-capable"/"Routing" rows: a
# transaction sitting in one of these has real in-flight work a crashed worker could have
# abandoned, so recovery (section 15) must consider it. Every other row is "Terminal",
# "Quiescent", or a temporary/honest/unacceptable terminal that a worker reaches only after
# durably recording why - nothing further to recover there until a new trigger or predicate fires.
ACTIVE_STATES: frozenset[TransactionState] = frozenset(
    {
        "OBSERVED",
        "SNAPSHOTTING",
        "EXTRACTING",
        "INVESTIGATING",
        "RECONCILING",
        "PLANNING",
        "COMPOSING",
        "VALIDATING",
        "REVIEWING",
        "REPAIRING",
        "ACCEPTED",
        "PROVING_NO_OP",
        "AWAITING_AUTHORIZATION",
        "PROPOSING",
        "INVALIDATED",
    }
)

QUIESCENT_OR_TERMINAL_STATES: frozenset[TransactionState] = frozenset(
    {
        "NON_PROCESSABLE",
        "UNCHANGED",
        "READY_FOR_PROPOSAL",
        "SUPERSEDED",
        "RETRYABLE",
        "BLOCKED_EXTERNAL",
        "FAILED_INTERNAL",
        "MONITORING",
    }
)

assert frozenset(get_args(TransactionState)) == ACTIVE_STATES | QUIESCENT_OR_TERMINAL_STATES
assert not (ACTIVE_STATES & QUIESCENT_OR_TERMINAL_STATES)

# The three "previous active state" rows (RETRYABLE, BLOCKED_EXTERNAL, FAILED_INTERNAL) resume
# into whichever active state they recorded as their own resume target, not a single fixed one -
# represented at runtime by ``FailureRecord.resume_state`` and checked precisely there
# (``recovery.py``). Membership in the registry below is therefore the wildcard "any active
# state"; the exact resume target is re-validated against the recorded value, which is strictly
# tighter than mere registry membership.
_RECOVERY_WILDCARD_SOURCES: tuple[TransactionState, ...] = (
    "RETRYABLE",
    "BLOCKED_EXTERNAL",
    "FAILED_INTERNAL",
)

# docs/STATE_MACHINE.md section 4's mermaid diagram plus every additional edge named in section
# 4.1's "Permitted next states" column that the simplified diagram omits (terminal-failure exits,
# and the repair/invalidation fan-in/fan-out). Kept as one explicit, readable edge list rather than
# derived cleverly, so a reviewer can check it against the doc line by line.
_DIAGRAM_EDGES: tuple[tuple[TransactionState, TransactionState], ...] = (
    ("OBSERVED", "NON_PROCESSABLE"),
    ("OBSERVED", "UNCHANGED"),
    ("OBSERVED", "SNAPSHOTTING"),
    ("SNAPSHOTTING", "EXTRACTING"),
    ("EXTRACTING", "INVESTIGATING"),
    ("INVESTIGATING", "RECONCILING"),
    ("RECONCILING", "PLANNING"),
    ("PLANNING", "COMPOSING"),
    ("COMPOSING", "VALIDATING"),
    ("VALIDATING", "REVIEWING"),
    ("VALIDATING", "REPAIRING"),
    ("REVIEWING", "REPAIRING"),
    ("REVIEWING", "ACCEPTED"),
    ("REPAIRING", "EXTRACTING"),
    ("REPAIRING", "INVESTIGATING"),
    ("REPAIRING", "PLANNING"),
    ("REPAIRING", "COMPOSING"),
    ("ACCEPTED", "PROVING_NO_OP"),
    ("PROVING_NO_OP", "READY_FOR_PROPOSAL"),
    ("PROVING_NO_OP", "INVALIDATED"),
    ("READY_FOR_PROPOSAL", "MONITORING"),
    ("READY_FOR_PROPOSAL", "AWAITING_AUTHORIZATION"),
    ("AWAITING_AUTHORIZATION", "PROPOSING"),
    ("PROPOSING", "MONITORING"),
    ("MONITORING", "OBSERVED"),
    # Section 4.1's terminal-failure exits, every row that names "terminal failure states":
    ("OBSERVED", "BLOCKED_EXTERNAL"),
    ("OBSERVED", "FAILED_INTERNAL"),
    ("SNAPSHOTTING", "RETRYABLE"),
    ("SNAPSHOTTING", "BLOCKED_EXTERNAL"),
    ("SNAPSHOTTING", "FAILED_INTERNAL"),
    ("EXTRACTING", "RETRYABLE"),
    ("EXTRACTING", "BLOCKED_EXTERNAL"),
    ("EXTRACTING", "FAILED_INTERNAL"),
    ("INVESTIGATING", "RETRYABLE"),
    ("INVESTIGATING", "BLOCKED_EXTERNAL"),
    ("INVESTIGATING", "FAILED_INTERNAL"),
    ("RECONCILING", "RETRYABLE"),
    ("RECONCILING", "BLOCKED_EXTERNAL"),
    ("RECONCILING", "FAILED_INTERNAL"),
    ("PLANNING", "RETRYABLE"),
    ("PLANNING", "BLOCKED_EXTERNAL"),
    ("PLANNING", "FAILED_INTERNAL"),
    ("COMPOSING", "RETRYABLE"),
    ("COMPOSING", "BLOCKED_EXTERNAL"),
    ("COMPOSING", "FAILED_INTERNAL"),
    ("VALIDATING", "RETRYABLE"),
    ("VALIDATING", "BLOCKED_EXTERNAL"),
    ("VALIDATING", "FAILED_INTERNAL"),
    ("REVIEWING", "RETRYABLE"),
    ("REVIEWING", "BLOCKED_EXTERNAL"),
    ("REVIEWING", "FAILED_INTERNAL"),
    ("REPAIRING", "RETRYABLE"),
    ("REPAIRING", "BLOCKED_EXTERNAL"),
    ("REPAIRING", "FAILED_INTERNAL"),
    ("PROVING_NO_OP", "RETRYABLE"),
    ("PROVING_NO_OP", "BLOCKED_EXTERNAL"),
    ("PROVING_NO_OP", "FAILED_INTERNAL"),
    ("ACCEPTED", "INVALIDATED"),
    ("READY_FOR_PROPOSAL", "INVALIDATED"),
    ("AWAITING_AUTHORIZATION", "BLOCKED_EXTERNAL"),
    ("PROPOSING", "RETRYABLE"),
    ("PROPOSING", "BLOCKED_EXTERNAL"),
    ("PROPOSING", "FAILED_INTERNAL"),
    # INVALIDATED routes to "the earliest affected active state" (sections 8/9's reopen tables).
    ("INVALIDATED", "EXTRACTING"),
    ("INVALIDATED", "INVESTIGATING"),
    ("INVALIDATED", "RECONCILING"),
    ("INVALIDATED", "PLANNING"),
    ("INVALIDATED", "COMPOSING"),
    ("INVALIDATED", "VALIDATING"),
    ("INVALIDATED", "REVIEWING"),
    ("INVALIDATED", "AWAITING_AUTHORIZATION"),
    # Terminal-for-revision/invocation states resume observation on the next trigger.
    ("NON_PROCESSABLE", "OBSERVED"),
    ("UNCHANGED", "OBSERVED"),
)

TRANSITION_REGISTRY: frozenset[tuple[TransactionState, TransactionState]] = frozenset(
    _DIAGRAM_EDGES
) | frozenset((source, target) for source in _RECOVERY_WILDCARD_SOURCES for target in ACTIVE_STATES)


def is_registered_transition(from_state: TransactionState, to_state: TransactionState) -> bool:
    """Section 17's first rejection rule: "it is not present in the transition registry"."""
    return (from_state, to_state) in TRANSITION_REGISTRY


class SourceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_branch: str
    revision: str
    readme_blob: str | None = None
    relevant_tree: str | None = None


class SurfaceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_hash: str | None = None
    checked_at: str | None = None
    due_at: str | None = None


class DependencyHashes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: str | None = None
    prompts: str | None = None
    models: str | None = None
    presentation: str | None = None
    validation: str | None = None


class AcceptedArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: str
    candidate: str
    accepted_at: str
    no_op_proven_at: str | None = None


class ProposalRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=REPOSITORY_PATTERN)
    branch: str
    number: int | None = None
    head_sha: str | None = None


FailureClassification = Literal[
    "transient",
    "permanent",
    "authorization_blocked",
    "validation_failed",
    "unknown",
]


class FailureRecord(BaseModel):
    """``docs/STATE_MACHINE.md`` section 4.1's ``RETRYABLE``/``BLOCKED_EXTERNAL``/
    ``FAILED_INTERNAL`` rows each require "original trigger identity"/"resume predicate"/
    "recovery task" alongside the failure class. ``resume_state`` is this record's own precise
    answer to "previous active state": recovery (section 15 point 3) re-enters exactly this
    state, never guesses or skips ahead of it.
    """

    model_config = ConfigDict(extra="forbid")

    classification: FailureClassification
    detail: str
    resume_state: TransactionState
    occurred_at: str
    resume_predicate: str | None = None
    recovery_count: int = Field(default=0, ge=0)


class LeaseRecord(BaseModel):
    """``docs/STATE_MACHINE.md`` section 14: "owner, acquired time, heartbeat, expiry and fencing
    token". ``fencing_token`` increments only when a lease is newly acquired (first acquire, or a
    reclaim after a prior holder's lease expired) - a same-holder renewal keeps the same token and
    only extends ``expires_at``, matching section 14's "An expired worker cannot commit state
    after a new fencing token is issued": a renewal is not a new issuance.
    """

    model_config = ConfigDict(extra="forbid")

    holder_id: str = Field(min_length=1)
    acquired_at: str
    heartbeat_at: str
    expires_at: str
    fencing_token: int = Field(ge=1)


class TransitionReceipt(BaseModel):
    """``docs/STATE_MACHINE.md`` section 17, verbatim field set (``from``/``to`` are Python
    keywords, so the model exposes ``from_state``/``to_state`` and aliases them for the wire
    shape)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    transition_id: str
    transaction_id: str
    repository: str = Field(pattern=REPOSITORY_PATTERN)
    from_state: TransactionState = Field(alias="from")
    to_state: TransactionState = Field(alias="to")
    event: str
    occurred_at: str
    actor: Literal["runtime"] = "runtime"
    input_manifest: str
    output_manifest: str
    policy_version: str
    fencing_token: int = Field(ge=1)


class RepositoryRecord(BaseModel):
    """``docs/STATE_MACHINE.md`` section 13.1's repository record.

    Two fields are implementation-necessary additions beyond the doc's illustrative YAML, each
    documented at its own definition: ``state_version`` (the CAS backend's own optimistic-
    concurrency counter; section 13.2 requires "compare-and-swap update" without naming the
    counter it compares) and ``recent_trigger_dedup_keys`` (section 3.2's trigger-deduplication
    requirement, which the illustrative record has no field for at all).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    repository: str = Field(pattern=REPOSITORY_PATTERN)
    provider_repository_id: int = Field(gt=0)
    registry_revision: str | None = None
    active_transaction_id: str | None = None
    state: TransactionState = "OBSERVED"
    source: SourceObservation | None = None
    surfaces: dict[str, SurfaceObservation] = Field(default_factory=dict)
    dependencies: DependencyHashes = Field(default_factory=DependencyHashes)
    accepted_artifact: AcceptedArtifact | None = None
    proposal: ProposalRef | None = None
    failure: FailureRecord | None = None
    lease: LeaseRecord | None = None
    last_transition: TransitionReceipt | None = None

    # CAS version: incremented by the backend on every successful save (``cas.py``).
    state_version: int = Field(default=0, ge=0)

    # Trigger-dedup ledger: dedup_key -> the transaction_id it was folded into, bounded to the
    # most recent ``MAX_TRIGGER_DEDUP_ENTRIES`` entries (``trigger.py``) so a long-lived repository
    # record cannot grow this map without bound across its lifetime.
    recent_trigger_dedup_keys: dict[str, str] = Field(default_factory=dict)

    recovery_count: int = Field(default=0, ge=0)
