"""TC-ISS-10: a repository whose candidate was blocked by an upstream defect is planned for sealing
again once the issue lifecycle proves the defect resolved - whatever the drift monitor says.

The producer is ``components/issues/lifecycle.py`` (a redetect that says the handoff's check no
longer fires); the consumer is ``core/sealing_plan.py``, which reads only the JSON contract below,
exactly as it reads the drift contract."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.errors import ConfigError
from repository_presenter.core.registry.models import Registry
from repository_presenter.core.sealing_plan import (
    DRIFTED,
    OUTCOME_FAILED,
    OUTCOME_SEALED,
    RESUME_CONTRACT_VERSION,
    DriftRecord,
    ResumeRecord,
    SealingAttempt,
    parse_resume_contract,
    plan_sealing_run,
    read_resume_contract,
)

NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
REV_A = "a" * 40
REV_B = "b" * 40


def _entry(family: str, mode: str = "full", repository_id: int = 1) -> dict[str, Any]:
    name = f"Aspose.{family.capitalize()}-FOSS-for-Java"
    return {
        "repository": f"example/{name}",
        "family": family,
        "platform": "java",
        "ecosystem": "java",
        "mode": mode,
        "policy_profile": f"example-{family}",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_{repository_id}",
        },
    }


def _registry() -> Registry:
    entries = [
        _entry("alpha", repository_id=1),
        _entry("bravo", repository_id=2),
        _entry("charlie", mode="disabled", repository_id=3),
    ]
    return Registry.model_validate({"schema_version": 1, "entries": entries})


def _repo(family: str) -> str:
    return f"example/Aspose.{family.capitalize()}-FOSS-for-Java"


def _resume(family: str, revision: str | None = REV_A) -> ResumeRecord:
    return ResumeRecord(_repo(family), revision, f"handoff-{family}")


def test_a_resolved_blocker_selects_a_repository_the_drift_monitor_calls_current() -> None:
    records = [DriftRecord(_repo("alpha"), "CURRENT")]
    plan = plan_sealing_run(records, _registry(), resumed=[_resume("alpha")], now=NOW)
    assert plan.selected == (_repo("alpha"),)
    assert plan.resumed == (_repo("alpha"),)


def test_a_resolved_blocker_selects_a_repository_the_monitor_has_no_record_of() -> None:
    plan = plan_sealing_run([], _registry(), resumed=[_resume("bravo")], now=NOW)
    assert plan.selected == (_repo("bravo"),)


def test_without_a_resume_record_nothing_changes() -> None:
    records = [DriftRecord(_repo("alpha"), "CURRENT")]
    plan = plan_sealing_run(records, _registry(), now=NOW)
    assert plan.selected == () and plan.resumed == ()


def test_a_repository_both_drifted_and_resumed_is_selected_once() -> None:
    records = [DriftRecord(_repo("alpha"), DRIFTED, REV_A)]
    plan = plan_sealing_run(records, _registry(), resumed=[_resume("alpha")], now=NOW)
    assert plan.selected == (_repo("alpha"),)


def test_resume_never_overrides_the_registry_allow_list_or_a_disabled_entry() -> None:
    plan = plan_sealing_run(
        [], _registry(), resumed=[_resume("charlie"), _resume("delta")], now=NOW
    )
    assert plan.selected == ()
    assert plan.disabled == (_repo("charlie"),)
    assert plan.not_admitted == (_repo("delta"),)


def test_the_failure_cooldown_is_respected_for_a_resumed_repository() -> None:
    history = [SealingAttempt(_repo("alpha"), OUTCOME_FAILED, NOW - timedelta(hours=1), REV_A)]
    plan = plan_sealing_run([], _registry(), history, resumed=[_resume("alpha", REV_A)], now=NOW)
    assert plan.selected == ()
    assert [item.repository for item in plan.skipped] == [_repo("alpha")]
    assert "cooldown" in plan.skipped[0].reason


def test_a_resolution_at_a_newer_revision_than_the_failure_is_not_held_by_the_cooldown() -> None:
    history = [SealingAttempt(_repo("alpha"), OUTCOME_FAILED, NOW - timedelta(hours=1), REV_A)]
    plan = plan_sealing_run([], _registry(), history, resumed=[_resume("alpha", REV_B)], now=NOW)
    assert plan.selected == (_repo("alpha"),)


def test_the_cooldown_lapses_for_a_resumed_repository_like_any_other() -> None:
    history = [SealingAttempt(_repo("alpha"), OUTCOME_FAILED, NOW - timedelta(hours=25), REV_A)]
    plan = plan_sealing_run([], _registry(), history, resumed=[_resume("alpha")], now=NOW)
    assert plan.selected == (_repo("alpha"),)


def test_a_resume_is_one_shot_once_the_repository_sealed_at_the_resolved_revision() -> None:
    history = [SealingAttempt(_repo("alpha"), OUTCOME_SEALED, NOW - timedelta(hours=1), REV_A)]
    plan = plan_sealing_run([], _registry(), history, resumed=[_resume("alpha", REV_A)], now=NOW)
    assert plan.selected == ()
    assert "already satisfied" in plan.skipped[0].reason


def test_a_resume_at_a_newer_revision_than_the_last_seal_still_selects() -> None:
    history = [SealingAttempt(_repo("alpha"), OUTCOME_SEALED, NOW - timedelta(hours=1), REV_A)]
    plan = plan_sealing_run([], _registry(), history, resumed=[_resume("alpha", REV_B)], now=NOW)
    assert plan.selected == (_repo("alpha"),)


def test_the_per_run_cap_still_bounds_drifted_and_resumed_work_together() -> None:
    records = [DriftRecord(_repo("alpha"), DRIFTED)]
    plan = plan_sealing_run(records, _registry(), resumed=[_resume("bravo")], cap=1, now=NOW)
    assert plan.selected == (_repo("alpha"),)
    assert plan.deferred == (_repo("bravo"),)


# --- the contract -----------------------------------------------------------------------------


def _contract(*rows: Any, version: Any = RESUME_CONTRACT_VERSION) -> dict[str, Any]:
    return {"schema_version": version, "repositories": list(rows)}


def test_the_resume_contract_accepts_exactly_its_documented_shape() -> None:
    raw = _contract(
        {"repository": "o/a", "resolved_revision": REV_A, "handoff_id": "o__a__f"},
        {"repository": "o/b", "resolved_revision": None, "handoff_id": None},
    )
    assert parse_resume_contract(raw) == (
        ResumeRecord("o/a", REV_A, "o__a__f"),
        ResumeRecord("o/b", None, None),
    )


@pytest.mark.parametrize(
    "raw",
    [
        [],
        _contract(version=2),
        {"schema_version": 1},
        _contract({"repository": "no-slash"}),
        _contract({"repository": "o/a", "resolved_revision": 5}),
        _contract({"repository": "o/a"}, {"repository": "o/a"}),
        _contract("not-an-object"),
    ],
)
def test_a_malformed_resume_contract_fails_closed(raw: Any) -> None:
    with pytest.raises(ConfigError):
        parse_resume_contract(raw)


def test_a_missing_or_malformed_resume_file_reads_as_no_resume_never_a_failure(
    tmp_path: Path,
) -> None:
    """Resuming is an acceleration, never a gate: sealing must keep running without it."""
    assert read_resume_contract(tmp_path / "absent.json") == ()
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_resume_contract(broken) == ()


def test_a_resume_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "resume.json"
    path.write_text(
        json.dumps(_contract({"repository": "o/a", "resolved_revision": REV_A})), encoding="utf-8"
    )
    assert read_resume_contract(path) == (ResumeRecord("o/a", REV_A, None),)
