"""G7-W03: dead-man monitoring and alerting over the durable repository record.

Two layers, matching this project's own established split between a backend-agnostic unit layer
and a real-mechanism proof (``test_git_backend.py``'s own precedent):

1. ``evaluate_repository_health`` against hand-built ``RepositoryRecord``s - every named rule in
   isolation, plus the negative controls this item's own acceptance bar names: "a genuinely healthy
   run produces no alert."
2. The acceptance bar's own literal scenario, driven end to end through the real
   ``run_present_transaction`` + real ``GitStateBackend`` against a disposable local git remote (not
   ``InMemoryStateBackend``) - a synthetic failure produces a named, specific alert; a genuinely
   healthy run produces none.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from repository_presenter.core.state.git_backend import GitStateBackend
from repository_presenter.core.state.health import (
    Budgets,
    evaluate_repository_health,
)
from repository_presenter.core.state.present_transaction import (
    PresentOutcome,
    run_present_transaction,
)
from repository_presenter.core.state.schema import (
    FailureRecord,
    RepositoryRecord,
    TransitionReceipt,
)
from support import init_git_repository

REPO = "example/Aspose.Widget-FOSS-for-Python"
PROVIDER_ID = 777
NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)


def _receipt(*, to_state: str, occurred_at: str) -> TransitionReceipt:
    return TransitionReceipt(
        transition_id="t-1",
        transaction_id="tx-1",
        repository=REPO,
        from_state="PROVING_NO_OP",
        to_state=to_state,  # type: ignore[arg-type]
        event="seed",
        occurred_at=occurred_at,
        input_manifest="x",
        output_manifest="x",
        policy_version="v1",
        fencing_token=1,
    )


def _healthy_record(occurred_at: str = "2026-10-01T11:55:00+00:00") -> RepositoryRecord:
    return RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="READY_FOR_PROPOSAL",
        last_transition=_receipt(to_state="READY_FOR_PROPOSAL", occurred_at=occurred_at),
    )


# --- evaluate_repository_health: the named rules, in isolation --------------------------------


def test_a_genuinely_healthy_record_produces_no_alert() -> None:
    """The acceptance bar's own negative control, at the unit layer."""
    alerts = evaluate_repository_health(REPO, _healthy_record(), now=NOW)
    assert alerts == []


def test_no_durable_record_at_all_is_its_own_named_alert() -> None:
    alerts = evaluate_repository_health(REPO, None, now=NOW)
    assert len(alerts) == 1
    assert alerts[0].kind == "no_durable_record"
    assert alerts[0].repository == REPO


def test_a_failed_internal_record_names_the_repository_and_the_failing_stage() -> None:
    record = RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="FAILED_INTERNAL",
        last_transition=_receipt(
            to_state="FAILED_INTERNAL", occurred_at="2026-10-01T11:59:00+00:00"
        ),
        failure=FailureRecord(
            classification="validation_failed",
            detail="present exited 3 (NotAllowlistedError)",
            resume_state="SNAPSHOTTING",
            occurred_at="2026-10-01T11:59:00+00:00",
        ),
    )
    alerts = evaluate_repository_health(REPO, record, now=NOW)
    failed = [a for a in alerts if a.kind == "transaction_failed"]
    assert len(failed) == 1
    assert failed[0].repository == REPO
    assert failed[0].stage == "SNAPSHOTTING"  # the stage the failure names, not just the terminal
    assert "NotAllowlistedError" in failed[0].detail
    assert "repository=" + REPO in failed[0].annotation()
    assert "stage=SNAPSHOTTING" in failed[0].annotation()


def test_blocked_external_and_invalidated_are_both_named_failures() -> None:
    for state, resume in (("BLOCKED_EXTERNAL", "EXTRACTING"), ("INVALIDATED", "REVIEWING")):
        record = RepositoryRecord(
            repository=REPO,
            provider_repository_id=PROVIDER_ID,
            state=state,  # type: ignore[arg-type]
            last_transition=_receipt(to_state=state, occurred_at="2026-10-01T11:59:00+00:00"),
            failure=FailureRecord(
                classification="transient" if state == "BLOCKED_EXTERNAL" else "validation_failed",
                detail=f"synthetic {state}",
                resume_state=resume,  # type: ignore[arg-type]
                occurred_at="2026-10-01T11:59:00+00:00",
            ),
        )
        alerts = evaluate_repository_health(REPO, record, now=NOW)
        assert any(a.kind == "transaction_failed" and a.stage == resume for a in alerts)


def test_retryable_is_not_treated_as_a_stuck_failure() -> None:
    """RETRYABLE is recovery_sweep's own expected, self-healing resume target - alerting on it
    would be noise, not signal (core/state/health.py's own documented exclusion)."""
    record = RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="RETRYABLE",
        last_transition=_receipt(to_state="RETRYABLE", occurred_at="2026-10-01T11:59:00+00:00"),
        failure=FailureRecord(
            classification="transient",
            detail="transient gateway error",
            resume_state="COMPOSING",
            occurred_at="2026-10-01T11:59:00+00:00",
        ),
    )
    alerts = evaluate_repository_health(REPO, record, now=NOW)
    assert all(a.kind != "transaction_failed" for a in alerts)


def test_a_stale_record_is_named_separately_from_a_failure() -> None:
    old = (NOW - timedelta(hours=48)).isoformat()
    record = RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="MONITORING",
        last_transition=_receipt(to_state="MONITORING", occurred_at=old),
    )
    alerts = evaluate_repository_health(REPO, record, now=NOW, stale_after=timedelta(hours=24))
    assert len(alerts) == 1
    assert alerts[0].kind == "stale"
    assert alerts[0].repository == REPO


def test_a_record_within_the_staleness_budget_is_not_stale() -> None:
    recent = (NOW - timedelta(hours=1)).isoformat()
    record = RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="MONITORING",
        last_transition=_receipt(to_state="MONITORING", occurred_at=recent),
    )
    alerts = evaluate_repository_health(REPO, record, now=NOW, stale_after=timedelta(hours=24))
    assert alerts == []


def test_wall_clock_budget_exceeded_names_the_measured_and_budgeted_values() -> None:
    alerts = evaluate_repository_health(
        REPO,
        _healthy_record(),
        now=NOW,
        budgets=Budgets(max_wall_clock_seconds=60.0, max_provider_calls=None),
        wall_clock_seconds=120.0,
    )
    assert len(alerts) == 1
    assert alerts[0].kind == "wall_clock_budget_exceeded"
    assert "120.0" in alerts[0].detail
    assert "60.0" in alerts[0].detail


def test_wall_clock_within_budget_produces_no_alert() -> None:
    alerts = evaluate_repository_health(
        REPO,
        _healthy_record(),
        now=NOW,
        budgets=Budgets(max_wall_clock_seconds=600.0, max_provider_calls=None),
        wall_clock_seconds=59.0,
    )
    assert alerts == []


def test_provider_call_budget_exceeded_names_the_measured_and_budgeted_values() -> None:
    alerts = evaluate_repository_health(
        REPO,
        _healthy_record(),
        now=NOW,
        budgets=Budgets(max_wall_clock_seconds=None, max_provider_calls=10),
        provider_calls=11,
    )
    assert len(alerts) == 1
    assert alerts[0].kind == "provider_call_budget_exceeded"
    assert "11" in alerts[0].detail
    assert "10" in alerts[0].detail


def test_a_disabled_budget_is_never_evaluated() -> None:
    """``None`` disables a budget outright - never a silent zero-as-disabled that would alert on
    every run."""
    alerts = evaluate_repository_health(
        REPO,
        _healthy_record(),
        now=NOW,
        budgets=Budgets(max_wall_clock_seconds=None, max_provider_calls=None),
        wall_clock_seconds=999999.0,
        provider_calls=999999,
    )
    assert alerts == []


def test_multiple_independent_conditions_each_produce_their_own_named_alert() -> None:
    old = (NOW - timedelta(hours=48)).isoformat()
    record = RepositoryRecord(
        repository=REPO,
        provider_repository_id=PROVIDER_ID,
        state="FAILED_INTERNAL",
        last_transition=_receipt(to_state="FAILED_INTERNAL", occurred_at=old),
        failure=FailureRecord(
            classification="validation_failed",
            detail="synthetic",
            resume_state="PLANNING",
            occurred_at=old,
        ),
    )
    alerts = evaluate_repository_health(
        REPO,
        record,
        now=NOW,
        budgets=Budgets(max_wall_clock_seconds=10.0, max_provider_calls=5),
        stale_after=timedelta(hours=24),
        wall_clock_seconds=20.0,
        provider_calls=6,
    )
    kinds = {a.kind for a in alerts}
    assert kinds == {
        "transaction_failed",
        "stale",
        "wall_clock_budget_exceeded",
        "provider_call_budget_exceeded",
    }


# --- the acceptance bar's own scenario, end to end against the real backend -------------------


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "remote")


def test_synthetic_failure_produces_a_named_specific_alert_against_the_real_backend(
    remote: Path,
) -> None:
    """This item's own acceptance bar, verbatim: "a synthetic failure (a repository whose
    transaction is forced to fail) produces a named, specific alert" - driven through the real
    ``run_present_transaction`` + real git-ref ``GitStateBackend`` (not a mock), exactly the
    mechanism ``present.yml`` uses in production, against a disposable local remote instead of
    this control repository's own origin (the same isolation ``test_git_backend.py`` already
    establishes as this project's proof pattern for the real mechanism)."""
    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present_transaction(
            backend=backend,
            repository=REPO,
            provider_repository_id=PROVIDER_ID,
            holder_id="worker-synthetic-failure",
            run=lambda: 1,  # forced failure
            classify=lambda exit_code: PresentOutcome(
                kind="failed", detail="synthetic forced failure (G7-W03 exercise)"
            ),
            workflow_run_id="exercise-failure-1",
        )
        assert exit_code == 1
        record = backend.load(REPO)

    alerts = evaluate_repository_health(REPO, record)
    failed = [a for a in alerts if a.kind == "transaction_failed"]
    assert len(failed) == 1
    assert failed[0].repository == REPO
    assert failed[0].stage == "SNAPSHOTTING"  # classify_present_outcome's own failure resume_state
    assert "synthetic forced failure" in failed[0].detail
    # Within a bounded time: the alert is available the instant the record is read back - no
    # polling window, no separate scheduled sweep required for this to fire.


def test_a_genuinely_healthy_run_produces_no_alert_against_the_real_backend(remote: Path) -> None:
    """This item's own acceptance bar, verbatim: "a genuinely healthy run produces no alert" -
    same real backend, a first-ever zero-call reproduction reaching READY_FOR_PROPOSAL."""
    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present_transaction(
            backend=backend,
            repository=REPO,
            provider_repository_id=PROVIDER_ID,
            holder_id="worker-healthy",
            run=lambda: 0,
            classify=lambda exit_code: PresentOutcome(
                kind="success", target_state="READY_FOR_PROPOSAL"
            ),
            workflow_run_id="exercise-healthy-1",
        )
        assert exit_code == 0
        record = backend.load(REPO)

    alerts = evaluate_repository_health(
        REPO,
        record,
        budgets=Budgets(max_wall_clock_seconds=3600.0, max_provider_calls=500),
        wall_clock_seconds=12.0,
        provider_calls=0,
    )
    assert alerts == []
