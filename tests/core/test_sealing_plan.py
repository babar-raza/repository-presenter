"""The unattended sealing run's plan: DRIFTED-only selection, the per-run cap, deterministic order,
the qwen3-next-only model guard, and the drift monitor's file contract (core/sealing_plan.py)."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.config import MODEL_VARIABLE
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.loader import load_registry
from repository_presenter.core.registry.models import Registry
from repository_presenter.core.sealing_plan import (
    DRIFTED,
    MAX_REPOSITORIES_PER_RUN,
    OUTCOME_FAILED,
    OUTCOME_SEALED,
    SEALING_FAILURE_COOLDOWN,
    SEALING_HISTORY_CONTRACT_VERSION,
    SEALING_MODEL,
    SEALING_PAUSED_VARIABLE,
    DriftRecord,
    SealingAttempt,
    empty_plan,
    github_output_lines,
    parse_drift_contract,
    parse_sealing_history_contract,
    plan_sealing_run,
    read_drift_contract,
    read_sealing_history_contract,
    require_sealing_model,
    sealing_paused,
)
from support import REPO_ROOT


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
        _entry("charlie", repository_id=3),
        _entry("delta", repository_id=4),
        _entry("echo", repository_id=5),
        _entry("foxtrot", mode="disabled", repository_id=6),
    ]
    return Registry.model_validate({"schema_version": 1, "entries": entries})


def _drifted(*names: str) -> list[DriftRecord]:
    return [
        DriftRecord(f"example/Aspose.{name.capitalize()}-FOSS-for-Java", DRIFTED) for name in names
    ]


def _repo(family: str) -> str:
    return f"example/Aspose.{family.capitalize()}-FOSS-for-Java"


def test_only_drifted_repositories_are_selected() -> None:
    records = [
        DriftRecord(_repo("alpha"), DRIFTED),
        DriftRecord(_repo("bravo"), "CURRENT"),
        DriftRecord(_repo("charlie"), "UNKNOWN"),
        DriftRecord(_repo("delta"), DRIFTED),
    ]
    plan = plan_sealing_run(records, _registry())
    assert plan.selected == (_repo("alpha"), _repo("delta"))
    assert plan.deferred == () and plan.not_admitted == () and plan.disabled == ()


def test_the_per_run_cap_holds_and_the_rest_are_deferred_in_sorted_order() -> None:
    assert MAX_REPOSITORIES_PER_RUN == 3
    plan = plan_sealing_run(_drifted("echo", "delta", "bravo", "charlie", "alpha"), _registry())
    assert plan.selected == (_repo("alpha"), _repo("bravo"), _repo("charlie"))
    assert plan.deferred == (_repo("delta"), _repo("echo"))


def test_the_selection_does_not_depend_on_the_order_the_contract_lists_repositories() -> None:
    records = _drifted("alpha", "bravo", "charlie", "delta", "echo")
    expected = plan_sealing_run(records, _registry())
    for seed in range(5):
        shuffled = records[:]
        random.Random(seed).shuffle(shuffled)
        assert plan_sealing_run(shuffled, _registry()) == expected


def test_an_explicit_cap_is_honoured_and_zero_is_refused() -> None:
    records = _drifted("alpha", "bravo")
    assert plan_sealing_run(records, _registry(), cap=1).selected == (_repo("alpha"),)
    with pytest.raises(ConfigError, match="cap of at least 1"):
        plan_sealing_run(records, _registry(), cap=0)


def test_a_disabled_drifted_repository_is_never_selected_and_is_reported() -> None:
    plan = plan_sealing_run(_drifted("foxtrot", "alpha"), _registry())
    assert plan.selected == (_repo("alpha"),)
    assert plan.disabled == (_repo("foxtrot"),)


def test_a_drifted_repository_outside_the_registry_is_never_selected() -> None:
    records = [DriftRecord("example/Aspose.Ghost-FOSS-for-Java", DRIFTED)]
    plan = plan_sealing_run(records, _registry())
    assert plan.selected == ()
    assert plan.not_admitted == ("example/Aspose.Ghost-FOSS-for-Java",)


def test_no_drift_means_no_work_and_false_outputs_for_both_matrices() -> None:
    plan = plan_sealing_run([DriftRecord(_repo("alpha"), "CURRENT")], _registry())
    assert plan.selected == ()
    assert github_output_lines(plan) == [
        "repositories=[]",
        "has_work=false",
        "publishable=[]",
        "has_publishable=false",
        "skipped=[]",
    ]


def test_the_matrix_output_names_each_repository_and_its_candidates_slug() -> None:
    plan = plan_sealing_run(_drifted("bravo"), _registry())
    bravo = (
        '[{"repository":"example/Aspose.Bravo-FOSS-for-Java",'
        '"slug":"example__Aspose.Bravo-FOSS-for-Java"}]'
    )
    assert github_output_lines(plan) == [
        f"repositories={bravo}",
        "has_work=true",
        f"publishable={bravo}",
        "has_publishable=true",
        "skipped=[]",
    ]


def test_only_full_mode_repositories_are_publishable_but_every_selected_one_is_sealed() -> None:
    # Mode governs publication readiness (core/registry/models.py): a dry_run repository is still
    # sealed - analysis is not publication - but never reaches the proposal matrix.
    records = _drifted("golf", "alpha")
    registry = _registry_with(_entry("golf", mode="dry_run", repository_id=7))
    plan = plan_sealing_run(records, registry)
    assert plan.selected == (_repo("alpha"), _repo("golf"))
    assert plan.publishable == (_repo("alpha"),)
    dry_only = plan_sealing_run(_drifted("golf"), registry)
    assert dry_only.selected == (_repo("golf"),) and dry_only.publishable == ()
    assert github_output_lines(dry_only)[3] == "has_publishable=false"


def _registry_with(*extra: dict[str, Any]) -> Registry:
    entries = [
        _entry("alpha", repository_id=1),
        _entry("bravo", repository_id=2),
        _entry("charlie", repository_id=3),
        _entry("delta", repository_id=4),
        _entry("echo", repository_id=5),
        _entry("foxtrot", mode="disabled", repository_id=6),
        *extra,
    ]
    return Registry.model_validate({"schema_version": 1, "entries": entries})


def _contract(*repositories: Any, version: Any = 1) -> dict[str, Any]:
    return {"schema_version": version, "repositories": list(repositories)}


def test_the_drift_contract_accepts_exactly_its_documented_shape() -> None:
    records = parse_drift_contract(
        _contract(
            {"repository": "owner/name", "status": DRIFTED},
            {"repository": "o/n2", "status": "CURRENT"},
        )
    )
    assert records == (DriftRecord("owner/name", DRIFTED), DriftRecord("o/n2", "CURRENT"))


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([], "not a JSON object"),
        (_contract(version=2), "schema_version"),
        ({"schema_version": 1}, "no repositories list"),
        (_contract("owner/name"), "not an object"),
        (_contract({"repository": "no-slash", "status": DRIFTED}), "owner/name"),
        (_contract({"repository": "o/n", "status": "STALE"}), "unknown status"),
        (
            _contract(
                {"repository": "o/n", "status": DRIFTED}, {"repository": "o/n", "status": DRIFTED}
            ),
            "more than once",
        ),
    ],
)
def test_a_malformed_drift_contract_fails_closed(raw: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_drift_contract(raw)


def test_a_missing_drift_contract_is_a_named_failure_never_zero_work(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="drift monitor output not found"):
        read_drift_contract(tmp_path / "drift" / "drift.json")


def test_an_unparseable_drift_contract_is_a_named_failure(tmp_path: Path) -> None:
    path = tmp_path / "drift.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        read_drift_contract(path)


def test_a_drift_contract_file_round_trips_through_the_reader(tmp_path: Path) -> None:
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(_contract({"repository": _repo("alpha"), "status": DRIFTED})))
    assert read_drift_contract(path) == (DriftRecord(_repo("alpha"), DRIFTED),)


def test_the_real_prompt_manifests_all_route_to_the_sealing_model() -> None:
    routes = load_manifests(REPO_ROOT / "prompts").routes()
    assert routes and set(routes.values()) == {SEALING_MODEL}
    require_sealing_model(routes, {})


def test_a_prompt_routed_to_another_model_is_refused() -> None:
    with pytest.raises(ConfigError, match="route elsewhere: section_authoring=gpt-oss"):
        require_sealing_model({"section_authoring": "gpt-oss", "coherence": SEALING_MODEL}, {})


def test_a_model_override_to_another_model_is_refused() -> None:
    with pytest.raises(ConfigError, match="would switch the sealing model"):
        require_sealing_model({"coherence": SEALING_MODEL}, {MODEL_VARIABLE: "gpt-oss"})


def test_a_model_override_naming_the_sealing_model_is_allowed() -> None:
    require_sealing_model({"coherence": SEALING_MODEL}, {MODEL_VARIABLE: f" {SEALING_MODEL} "})


def test_the_real_registry_loads_and_drifted_entries_resolve_against_it() -> None:
    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    listed = [entry.repository for entry in registry.entries if entry.mode != "disabled"]
    assert listed, "the registry must list at least one enabled repository"
    plan = plan_sealing_run([DriftRecord(repo, DRIFTED) for repo in listed], registry)
    assert plan.selected == tuple(sorted(listed)[:MAX_REPOSITORIES_PER_RUN])


# --- the owner pause switch: REPOSITORY_PRESENTER_SEALING_PAUSED, exactly "1" ------------------


def test_the_pause_variable_pauses_sealing_only_when_exactly_one() -> None:
    assert SEALING_PAUSED_VARIABLE == "REPOSITORY_PRESENTER_SEALING_PAUSED"
    assert sealing_paused({SEALING_PAUSED_VARIABLE: "1"}) is True


@pytest.mark.parametrize("value", ["", "0", "true", "TRUE", "yes", "on", " 1", "1 ", "11", "2"])
def test_any_other_value_leaves_sealing_enabled(value: str) -> None:
    """Negative controls: truthy-looking values, whitespace and case variants never pause."""
    assert sealing_paused({SEALING_PAUSED_VARIABLE: value}) is False


def test_an_unset_pause_variable_leaves_sealing_enabled() -> None:
    assert sealing_paused({}) is False
    assert sealing_paused({"GH_TOKEN": "x"}) is False


def test_a_paused_run_reports_no_work_and_nothing_publishable() -> None:
    assert github_output_lines(empty_plan()) == [
        "repositories=[]",
        "has_work=false",
        "publishable=[]",
        "has_publishable=false",
        "skipped=[]",
    ]


# --- failure memory: a FAILED repository is skipped for a cooldown, never abandoned (#1009) ----

_NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)
_REV_A = "a" * 40
_REV_B = "b" * 40


def _attempt(
    family: str, outcome: str, *, ago: timedelta, revision: str | None = _REV_A
) -> SealingAttempt:
    return SealingAttempt(_repo(family), outcome, _NOW - ago, revision)


def test_a_repository_that_failed_last_cycle_is_skipped_this_cycle() -> None:
    records = _drifted("alpha", "bravo")
    history = [_attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=1))]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("bravo"),)
    assert [item.repository for item in plan.skipped] == [_repo("alpha")]


def test_a_repository_with_fresh_drift_after_a_failure_is_not_skipped() -> None:
    # The same repository failed recently (within the cooldown), but the drift record now names a
    # different source_revision than the one the failure was recorded against: a new commit
    # landed, so the old failure cannot be assumed to still apply, and the cooldown is bypassed.
    records = [DriftRecord(_repo("alpha"), DRIFTED, source_revision=_REV_B)]
    history = [_attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=1), revision=_REV_A)]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("alpha"),)
    assert plan.skipped == ()


def test_the_same_revision_after_a_failure_is_still_skipped() -> None:
    # Negative control for the above: an unchanged source_revision is the stuck-drift case the
    # cooldown exists for, not a new commit, so it is skipped exactly as the base case is.
    records = [DriftRecord(_repo("alpha"), DRIFTED, source_revision=_REV_A)]
    history = [_attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=1), revision=_REV_A)]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == ()
    assert [item.repository for item in plan.skipped] == [_repo("alpha")]


def test_the_skip_reason_is_recorded_and_typed_never_silent() -> None:
    records = _drifted("alpha")
    history = [_attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=2), revision=_REV_A)]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert len(plan.skipped) == 1
    reason = plan.skipped[0].reason
    assert "cooldown" in reason and _REV_A in reason and "eligible again at" in reason
    # The reason also reaches the workflow's own GITHUB_OUTPUT, never only an in-memory field.
    lines = github_output_lines(plan)
    skipped_line = next(line for line in lines if line.startswith("skipped="))
    payload = json.loads(skipped_line.removeprefix("skipped="))
    assert payload == [{"repository": _repo("alpha"), "reason": reason}]


def test_an_always_failing_repository_is_retried_once_the_cooldown_elapses() -> None:
    """Negative control: failure memory must not starve a repeatedly-failing repository forever.
    The same repository, same unchanged revision, is skipped right up to the cooldown boundary and
    selected again the moment it elapses - with no separate unlock step and no dependency on how
    many runs happened in between, so a permanently broken repository is retried roughly once per
    cooldown window forever, never parked for good."""
    records = [DriftRecord(_repo("alpha"), DRIFTED, source_revision=_REV_A)]
    just_inside = [
        _attempt(
            "alpha",
            OUTCOME_FAILED,
            ago=SEALING_FAILURE_COOLDOWN - timedelta(seconds=1),
            revision=_REV_A,
        )
    ]
    assert plan_sealing_run(records, _registry(), just_inside, now=_NOW).selected == ()
    at_boundary = [_attempt("alpha", OUTCOME_FAILED, ago=SEALING_FAILURE_COOLDOWN, revision=_REV_A)]
    assert plan_sealing_run(records, _registry(), at_boundary, now=_NOW).selected == (
        _repo("alpha"),
    )
    long_past = [
        _attempt("alpha", OUTCOME_FAILED, ago=SEALING_FAILURE_COOLDOWN * 10, revision=_REV_A)
    ]
    assert plan_sealing_run(records, _registry(), long_past, now=_NOW).selected == (_repo("alpha"),)


def test_a_sealed_outcome_is_never_skipped() -> None:
    records = _drifted("alpha")
    history = [_attempt("alpha", OUTCOME_SEALED, ago=timedelta(minutes=5))]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("alpha"),)
    assert plan.skipped == ()


def test_only_the_latest_attempt_per_repository_governs_the_skip() -> None:
    # An older FAILED attempt followed by a newer SEALED one (a retry that then succeeded, or a
    # history file that concatenates several past runs) must not keep skipping forever.
    records = _drifted("alpha")
    history = [
        _attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=10)),
        _attempt("alpha", OUTCOME_SEALED, ago=timedelta(hours=1)),
    ]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("alpha"),)


def test_the_cap_still_applies_to_what_remains_after_skipping() -> None:
    # Five drifted repositories, one skipped by failure memory, cap 3: the cap counts only the
    # repositories failure memory left eligible, never the skipped one.
    records = _drifted("echo", "delta", "bravo", "charlie", "alpha")
    history = [_attempt("alpha", OUTCOME_FAILED, ago=timedelta(hours=1))]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("bravo"), _repo("charlie"), _repo("delta"))
    assert plan.deferred == (_repo("echo"),)
    assert [item.repository for item in plan.skipped] == [_repo("alpha")]


def test_a_history_record_for_a_non_drifted_or_unlisted_repository_has_no_effect() -> None:
    records = _drifted("alpha")
    history = [_attempt("ghost", OUTCOME_FAILED, ago=timedelta(hours=1))]
    plan = plan_sealing_run(records, _registry(), history, now=_NOW)
    assert plan.selected == (_repo("alpha"),)
    assert plan.skipped == ()


# --- the sealing history contract: read-leniently, parsed strictly -----------------------------


def _history_contract(
    *repositories: Any, version: Any = SEALING_HISTORY_CONTRACT_VERSION
) -> dict[str, Any]:
    return {"schema_version": version, "repositories": list(repositories)}


def test_the_sealing_history_contract_accepts_exactly_its_documented_shape() -> None:
    attempts = parse_sealing_history_contract(
        _history_contract(
            {
                "repository": "owner/name",
                "outcome": OUTCOME_FAILED,
                "observed_at": "2026-10-06T12:34:19+00:00",
                "source_revision": _REV_A,
            },
            {
                "repository": "o/n2",
                "outcome": OUTCOME_SEALED,
                "observed_at": "2026-10-06T12:00:00+00:00",
            },
        )
    )
    assert attempts == (
        SealingAttempt(
            "owner/name",
            OUTCOME_FAILED,
            datetime.fromisoformat("2026-10-06T12:34:19+00:00"),
            _REV_A,
        ),
        SealingAttempt(
            "o/n2", OUTCOME_SEALED, datetime.fromisoformat("2026-10-06T12:00:00+00:00"), None
        ),
    )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([], "not a JSON object"),
        (_history_contract(version=2), "schema_version"),
        ({"schema_version": SEALING_HISTORY_CONTRACT_VERSION}, "no repositories list"),
        (_history_contract("owner/name"), "not an object"),
        (
            _history_contract(
                {
                    "repository": "no-slash",
                    "outcome": OUTCOME_FAILED,
                    "observed_at": "2026-10-06T12:00:00+00:00",
                }
            ),
            "owner/name",
        ),
        (
            _history_contract(
                {
                    "repository": "o/n",
                    "outcome": "STUCK",
                    "observed_at": "2026-10-06T12:00:00+00:00",
                }
            ),
            "unknown outcome",
        ),
        (
            _history_contract(
                {"repository": "o/n", "outcome": OUTCOME_FAILED, "observed_at": "not-a-date"}
            ),
            "no valid observed_at",
        ),
        (
            _history_contract(
                {
                    "repository": "o/n",
                    "outcome": OUTCOME_FAILED,
                    "observed_at": "2026-10-06T12:00:00",
                }
            ),
            "no timezone",
        ),
    ],
)
def test_a_malformed_sealing_history_contract_fails_closed_when_parsed_directly(
    raw: Any, message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_sealing_history_contract(raw)


def test_a_missing_sealing_history_file_reads_as_empty_never_a_failure(tmp_path: Path) -> None:
    # Unlike the drift contract: no history is the ordinary first-run state, and failing closed
    # here would trade "a stuck repository burns its budget every run" for "sealing stops running
    # entirely" - strictly worse. read_sealing_history_contract is lenient; parse_sealing_history_
    # contract (above) stays strict, so a real shape defect is still caught where it is produced.
    assert read_sealing_history_contract(tmp_path / "sealing" / "history.json") == ()


def test_a_malformed_sealing_history_file_also_reads_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_sealing_history_contract(path) == ()
    path.write_text(json.dumps(_history_contract(version=99)), encoding="utf-8")
    assert read_sealing_history_contract(path) == ()


def test_a_sealing_history_file_round_trips_through_the_lenient_reader(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            _history_contract(
                {
                    "repository": _repo("alpha"),
                    "outcome": OUTCOME_FAILED,
                    "observed_at": "2026-10-06T12:00:00+00:00",
                    "source_revision": _REV_A,
                }
            )
        )
    )
    assert read_sealing_history_contract(path) == (
        SealingAttempt(
            _repo("alpha"),
            OUTCOME_FAILED,
            datetime.fromisoformat("2026-10-06T12:00:00+00:00"),
            _REV_A,
        ),
    )


def test_the_drift_contract_still_accepts_an_absent_source_revision() -> None:
    # source_revision is additive and optional: existing evidence with no such field must keep
    # parsing exactly as before.
    records = parse_drift_contract(_contract({"repository": "owner/name", "status": DRIFTED}))
    assert records == (DriftRecord("owner/name", DRIFTED, None),)


def test_the_drift_contract_carries_a_source_revision_when_the_evidence_has_one() -> None:
    records = parse_drift_contract(
        _contract({"repository": "owner/name", "status": DRIFTED, "source_revision": _REV_A})
    )
    assert records == (DriftRecord("owner/name", DRIFTED, _REV_A),)


def test_a_non_string_source_revision_fails_closed() -> None:
    with pytest.raises(ConfigError, match="non-string source_revision"):
        parse_drift_contract(
            _contract({"repository": "owner/name", "status": DRIFTED, "source_revision": 1})
        )
