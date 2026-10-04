"""The unattended sealing run's plan: DRIFTED-only selection, the per-run cap, deterministic order,
the qwen3-next-only model guard, and the drift monitor's file contract (core/sealing_plan.py)."""

from __future__ import annotations

import json
import random
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
    SEALING_MODEL,
    DriftRecord,
    github_output_lines,
    parse_drift_contract,
    plan_sealing_run,
    read_drift_contract,
    require_sealing_model,
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
