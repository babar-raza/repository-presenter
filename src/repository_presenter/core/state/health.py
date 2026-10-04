"""Dead-man monitoring and alerting over the durable repository record (G7-W03;
``docs/EXECUTION_STATE_MACHINE.md`` G7 Work item 1/4).

``.github/workflows/liveness.yml`` already supervises this control repository's own development
process (stranded branches, stuck PRs, a silent cron) - this module is its product-portfolio
equivalent: one repository's own durable ``RepositoryRecord`` (``core/state/schema.py``), built by
G5-W05's real hosted ``present.yml``, read and evaluated for a named, specific alert rather than a
generic "a run failed". Budgets (wall-clock, provider-call count) extend
``components/readme/bundle/seal.py``'s own ``call_variance`` mechanism's precedent - "make it
observable" logging - into actual alerting, the same way ``liveness.yml`` turned raw git/API state
into ``::error::`` annotations instead of leaving it to be noticed by chance.

Deliberately deterministic only (``AGENTS.md``'s agentic/deterministic boundary): every rule here
reads already-committed, already-typed state and compares it against a fixed threshold - no LLM
judgment, no state mutation. A caller (``cli.py::run_health_check``) wires this against the real
``GitStateBackend``; this module itself never touches a backend, matching ``cas.py``'s own
backend-agnostic design.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from repository_presenter.core.state.schema import RepositoryRecord, TransactionState

# docs/STATE_MACHINE.md section 4.1's own three "previous active state" rows name
# FAILED_INTERNAL/BLOCKED_EXTERNAL/RETRYABLE as the terminal-failure landings - RETRYABLE is
# deliberately excluded here: it is recovery_sweep's own expected, self-healing resume target
# (core/state/recovery.py), not yet a stuck condition worth paging on. INVALIDATED is added: it is
# the honest substitute a resumed-ACCEPTED failure lands on
# (core/state/present_transaction.py::_failure_target) and carries the same FailureRecord shape -
# routing defects to their earliest causal stage (AGENTS.md) means this alert, not a silent
# "INVALIDATED just means re-review", names it too.
FAILED_STATES: frozenset[TransactionState] = frozenset(
    {"FAILED_INTERNAL", "BLOCKED_EXTERNAL", "INVALIDATED"}
)

# Deliberately generous starting budgets, named honestly as a ceiling meant to catch a genuine
# runaway (an infinite retry loop, a stuck gateway) rather than flag ordinary variance - not a
# measured distribution. G3-W04's own cohort timebox was 3 hours for ten repositories (~18
# minutes/repository average, facts cache cold); G5-W03's own per-repository call-rate discovery
# (RESEARCH_AND_GUIDELINES.md section 18.4) is still open. Tune down once G7-W05's failure-mode
# exercises and more real hosted runs establish a real distribution - never asserted as measured
# fact today.
DEFAULT_MAX_WALL_CLOCK_SECONDS = 3600.0
DEFAULT_MAX_PROVIDER_CALLS = 500
DEFAULT_STALE_AFTER = timedelta(hours=24)


@dataclass(frozen=True)
class Budgets:
    """``None`` disables that one budget's check entirely - never a silent zero-as-disabled."""

    max_wall_clock_seconds: float | None = DEFAULT_MAX_WALL_CLOCK_SECONDS
    max_provider_calls: int | None = DEFAULT_MAX_PROVIDER_CALLS


@dataclass(frozen=True)
class Alert:
    """One named, specific alert - repository and stage always named, never a generic "a run
    failed" (this item's own acceptance bar, verbatim)."""

    repository: str
    kind: str
    stage: str
    detail: str
    occurred_at: str

    def annotation(self) -> str:
        """A GitHub Actions ``::error::`` line - ``liveness.yml``'s own established alerting
        contract (a red job, visible in Actions history, natively notification-capable) reused
        rather than a bespoke channel this project would have to build and operate itself
        (``AGENTS.md``'s prefer-battle-tested-solutions rule)."""
        return (
            f"::error::repository={self.repository} stage={self.stage} kind={self.kind} - "
            f"{self.detail}"
        )


def evaluate_repository_health(
    repository: str,
    record: RepositoryRecord | None,
    *,
    now: datetime | None = None,
    budgets: Budgets | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
    wall_clock_seconds: float | None = None,
    provider_calls: int | None = None,
) -> list[Alert]:
    """Every rule this item's own acceptance bar names, evaluated independently - a genuinely
    healthy record (a non-failed state, a recent transition, within every supplied budget)
    produces an empty list, never a suppressed or merged partial alert."""
    now = now or datetime.now(UTC)
    budgets = Budgets() if budgets is None else budgets
    alerts: list[Alert] = []

    if record is None:
        # present --durable-state ran (or should have) and left no record at all - a distinct,
        # named condition from a record that exists and failed.
        return [
            Alert(
                repository=repository,
                kind="no_durable_record",
                stage="unknown",
                detail=(
                    "no durable-state record exists for this repository - present --durable-state "
                    "either never ran or failed before its first committed transition"
                ),
                occurred_at=now.isoformat(),
            )
        ]

    if record.state in FAILED_STATES:
        failure = record.failure
        stage = failure.resume_state if failure is not None else record.state
        detail = (
            failure.detail
            if failure is not None
            else f"record left at {record.state} with no FailureRecord attached"
        )
        occurred_at = failure.occurred_at if failure is not None else now.isoformat()
        alerts.append(
            Alert(
                repository=repository,
                kind="transaction_failed",
                stage=stage,
                detail=detail,
                occurred_at=occurred_at,
            )
        )

    last_seen = _last_seen_at(record)
    if last_seen is not None:
        age = now - last_seen
        if age > stale_after:
            alerts.append(
                Alert(
                    repository=repository,
                    kind="stale",
                    stage=record.state,
                    detail=(
                        f"no transition observed in {age} (staleness budget {stale_after}); "
                        f"last transition to {record.last_transition.to_state!r}"  # type: ignore[union-attr]
                    ),
                    occurred_at=last_seen.isoformat(),
                )
            )

    if (
        budgets.max_wall_clock_seconds is not None
        and wall_clock_seconds is not None
        and wall_clock_seconds > budgets.max_wall_clock_seconds
    ):
        alerts.append(
            Alert(
                repository=repository,
                kind="wall_clock_budget_exceeded",
                stage=record.state,
                detail=(
                    f"{wall_clock_seconds:.1f}s observed, budget "
                    f"{budgets.max_wall_clock_seconds:.1f}s"
                ),
                occurred_at=now.isoformat(),
            )
        )

    if (
        budgets.max_provider_calls is not None
        and provider_calls is not None
        and provider_calls > budgets.max_provider_calls
    ):
        alerts.append(
            Alert(
                repository=repository,
                kind="provider_call_budget_exceeded",
                stage=record.state,
                detail=(
                    f"{provider_calls} provider calls observed, budget {budgets.max_provider_calls}"
                ),
                occurred_at=now.isoformat(),
            )
        )

    return alerts


def _last_seen_at(record: RepositoryRecord) -> datetime | None:
    """Section 13.1's own "last successful run" reading: the most recent committed transition,
    success or failure alike - a failed record's own recency is exactly what tells recovery or a
    human whether it is a fresh failure or a long-stuck one; a separate, narrower "healthy only"
    staleness reading is left to a caller that wants it (not needed by this item's own acceptance
    bar, which asks for staleness alongside, not instead of, the failure alert above)."""
    if record.last_transition is None:
        return None
    return datetime.fromisoformat(record.last_transition.occurred_at)
