"""Typed invalidation scopes: the table, the routing, and the read-only portfolio dry run."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.bundle.dry_run import (
    held_updates,
    portfolio_routing,
)
from repository_presenter.components.readme.bundle.evaluation import evaluate
from repository_presenter.components.readme.bundle.invalidation import (
    COMPONENT_SCOPES,
    DEPENDENCY_SCOPES,
    PROMPT_SCOPES,
    SCOPE_BY_NAME,
    SCOPES,
    STAGE_OVERRIDES,
    STATE_INVALIDATED,
    STATE_ORDER,
    STATE_UPDATE_AVAILABLE,
    ScopeError,
    reopening_stage,
    route,
    scope_of,
    scope_of_artifact,
)
from repository_presenter.components.readme.bundle.seal import (
    DEPENDENCIES_FILENAME,
    OPTIONAL_ARTIFACTS,
    REQUIRED_ARTIFACTS,
    code_dependencies,
    upstream_dependencies,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

PROMPTS = load_manifests(REPO_ROOT / "prompts")


# --- the table -----------------------------------------------------------------------------


def test_the_scope_table_maps_each_scope_to_a_stage_and_a_state() -> None:
    assert [scope.name for scope in SCOPES] == [
        "facts",
        "evidence",
        "reconciliation",
        "presentation",
        "planning",
        "authoring",
        "validator",
        "reviewer",
    ]
    stages = [STATE_ORDER.index(scope.stage) for scope in SCOPES]
    assert stages == sorted(stages)  # written in stage order; ties keep table order
    assert {scope.state for scope in SCOPES} <= {STATE_INVALIDATED, STATE_UPDATE_AVAILABLE}


def test_only_the_facts_scope_invalidates() -> None:
    """Negative control: a prompt, template, validator or reviewer input is never itself a factual
    input, so none of those scopes may be mapped to an invalidation (AGENTS.md)."""
    invalidating = [scope.name for scope in SCOPES if scope.state == STATE_INVALIDATED]
    assert invalidating == ["facts"]
    assert all(
        scope.state == STATE_UPDATE_AVAILABLE
        for scope in SCOPES
        if scope.name in {"validator", "reviewer", "presentation", "authoring", "planning"}
    )


def test_every_dependency_class_the_seal_records_has_a_scope() -> None:
    facts = FactsDocument(
        "owner/repo",
        "r" * 40,
        (Fact("identity:repository", "identity", "owner/repo", (Evidence("x"),)),),
    )
    record = upstream_dependencies("r" * 40, "t" * 64, facts, PROMPTS)
    classes = ["source", "facts", "contract_version", "validators", "acceptance_profile_version"]
    classes += ["policy"]
    classes += [f"environment.{name}" for name in record["environment"]]
    classes += [f"prompts.{name}" for name in record["prompts"]]
    classes += [f"components.{name}" for name in record["components"]]
    assert {scope_of(dependency).name for dependency in classes} <= {s.name for s in SCOPES}
    # ... and the tables have no row for a class the record does not carry.
    assert set(DEPENDENCY_SCOPES) <= set(classes)
    assert set(PROMPT_SCOPES) == set(record["prompts"])
    assert set(COMPONENT_SCOPES) == set(record["components"])


def test_every_sealed_artifact_has_a_scope() -> None:
    for name in (*REQUIRED_ARTIFACTS, *OPTIONAL_ARTIFACTS, DEPENDENCIES_FILENAME):
        if name in {"calls.jsonl", "probes.json"}:  # the clock-bearing files are never compared
            continue
        assert scope_of_artifact(name).name in SCOPE_BY_NAME, name


def test_a_class_or_artifact_with_no_row_raises_rather_than_guessing() -> None:
    with pytest.raises(ScopeError, match="no invalidation scope for the dependency 'surprise'"):
        scope_of("surprise")
    with pytest.raises(ScopeError, match="no invalidation scope for the sealed artifact"):
        scope_of_artifact("surprise.json")
    # An unknown prompt or component falls to its family's row, as evaluation always defaulted.
    assert scope_of("prompts.a_new_job").name == "evidence"
    assert scope_of("components.a_new_component").name == "presentation"


def test_a_class_reopens_its_scope_stage_except_the_one_documented_override() -> None:
    assert STAGE_OVERRIDES == {"components.reviewer_logic": "COMPOSING"}
    concrete = [
        *DEPENDENCY_SCOPES,
        *(f"prompts.{name}" for name in PROMPT_SCOPES),
        *(f"components.{name}" for name in COMPONENT_SCOPES),
        "environment.python_version",
    ]
    for dependency in concrete:
        expected = STAGE_OVERRIDES.get(dependency) or scope_of(dependency).stage
        assert reopening_stage(dependency) == expected
    # The override only ever reopens earlier than its scope, so nothing under-reopens.
    reviewer = scope_of("components.reviewer_logic")
    assert STATE_ORDER.index(reopening_stage("components.reviewer_logic")) <= STATE_ORDER.index(
        reviewer.stage
    )


# --- the routing ---------------------------------------------------------------------------


def test_nothing_changed_routes_nowhere() -> None:
    routing = route([], [])
    assert routing.state is None and routing.scopes == () and not routing.invalidates


@pytest.mark.parametrize(
    ("dependency", "scope", "state", "stage"),
    [
        ("source", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("environment.extractor_version", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("facts", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("prompts.repository_investigation", "evidence", STATE_UPDATE_AVAILABLE, "INVESTIGATING"),
        ("prompts.source_reconciliation", "reconciliation", STATE_UPDATE_AVAILABLE, "RECONCILING"),
        ("components.shell", "presentation", STATE_UPDATE_AVAILABLE, "RECONCILING"),
        ("prompts.presentation_planning", "planning", STATE_UPDATE_AVAILABLE, "PLANNING"),
        ("policy", "planning", STATE_UPDATE_AVAILABLE, "PLANNING"),
        ("prompts.section_authoring", "authoring", STATE_UPDATE_AVAILABLE, "COMPOSING"),
        ("components.normalisation", "authoring", STATE_UPDATE_AVAILABLE, "COMPOSING"),
        ("validators", "validator", STATE_UPDATE_AVAILABLE, "VALIDATING"),
        ("contract_version", "validator", STATE_UPDATE_AVAILABLE, "VALIDATING"),
        ("prompts.independent_review", "reviewer", STATE_UPDATE_AVAILABLE, "REVIEWING"),
        ("acceptance_profile_version", "reviewer", STATE_UPDATE_AVAILABLE, "REVIEWING"),
        ("components.reviewer_logic", "reviewer", STATE_UPDATE_AVAILABLE, "COMPOSING"),
    ],
)
def test_each_changed_class_routes_to_its_scope_state_and_stage(
    dependency: str, scope: str, state: str, stage: str
) -> None:
    routing = route([dependency])
    assert (routing.triggering_scope, routing.state, routing.stage) == (scope, state, stage)
    assert routing.scopes == (scope,) and routing.basis == "inputs"
    assert routing.invalidates == (state == STATE_INVALIDATED)


def test_an_invalidating_scope_decides_over_earlier_and_later_scopes() -> None:
    routing = route(["validators", "prompts.independent_review", "facts", "components.shell"])
    assert routing.triggering_scope == "facts" and routing.invalidates
    assert routing.scopes == ("facts", "presentation", "validator", "reviewer")
    assert routing.stage == "EXTRACTING"


def test_without_a_facts_change_the_earliest_scope_decides_and_nothing_invalidates() -> None:
    routing = route(["validators", "prompts.independent_review", "prompts.section_authoring"])
    assert routing.triggering_scope == "authoring"
    assert routing.state == STATE_UPDATE_AVAILABLE and not routing.invalidates
    assert routing.stage == "COMPOSING"


def test_changed_inputs_win_over_the_artifacts_they_rewrote() -> None:
    routing = route(["components.renderer"], ["README.md", "facts.json"])
    assert routing.scopes == ("presentation",) and routing.basis == "inputs"
    assert not routing.invalidates


def test_artifact_drift_with_no_changed_input_is_scoped_by_the_stage_that_wrote_it() -> None:
    routing = route([], ["README.md", "review.json"])
    assert routing.scopes == ("authoring", "reviewer") and routing.basis == "artifacts"
    assert routing.state == STATE_UPDATE_AVAILABLE and routing.stage == "COMPOSING"
    assert route([], ["facts.json"]).invalidates


# --- the portfolio dry run -----------------------------------------------------------------


def _record(**overrides: Any) -> dict[str, Any]:
    record = {
        "schema_version": 1,
        "source": {"revision": "a" * 40, "tree_sha256": "t" * 64},
        "facts": {"identity:repository": "1" * 64},
        "protected_content_fingerprint": "f" * 64,
        **copy.deepcopy(code_dependencies(PROMPTS)),
    }
    record["environment"] = {**record["environment"], "python_version": "3.13.2", "os": "Windows"}
    for dotted, value in overrides.items():
        target = record
        parts = dotted.split("__")
        for part in parts[:-1]:
            target = target[part]
        if value is None:
            target.pop(parts[-1], None)
        else:
            target[parts[-1]] = value
    return record


def _bundle(root: Path, name: str, state: str, sealed: dict[str, Any], **extra: Any) -> None:
    revision = hashlib.sha1(name.encode()).hexdigest()
    directory = root / "candidates" / name
    (directory / revision).mkdir(parents=True)
    (directory / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    (directory / revision / DEPENDENCIES_FILENAME).write_text(json.dumps(sealed), encoding="utf-8")
    manifest = {"state": state, "repository": name, "revision": revision, **extra}
    (directory / revision / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_the_dry_run_routes_each_bundle_by_the_scopes_of_its_own_stale_inputs(
    tmp_path: Path,
) -> None:
    current = code_dependencies(PROMPTS)
    _bundle(tmp_path, "same", "READY_FOR_PROPOSAL", _record())
    _bundle(tmp_path, "old-renderer", "READY_FOR_PROPOSAL", _record(components__renderer="0"))
    _bundle(tmp_path, "old-check", "READY_FOR_PROPOSAL", _record(validator_version="0"))
    _bundle(
        tmp_path,
        "old-prompt-and-review",
        "READY_FOR_PROPOSAL",
        _record(
            prompts__section_authoring__sha256="0" * 64,
            prompts__independent_review__sha256="0" * 64,
        ),
    )
    before = _snapshot(tmp_path)

    rows = {row.repository_dir: row for row in portfolio_routing(tmp_path, current)}

    assert _snapshot(tmp_path) == before  # a dry run writes nothing
    assert rows["same"].routing.state is None
    assert rows["same"].would_become == "READY_FOR_PROPOSAL"
    assert rows["old-renderer"].would_become == STATE_UPDATE_AVAILABLE
    assert rows["old-renderer"].routing.triggering_scope == "presentation"
    assert rows["old-check"].routing.scopes == ("validator",)
    assert rows["old-prompt-and-review"].routing.scopes == ("authoring", "reviewer")
    # Negative control: the dry run cannot observe the source, the facts or the host, so it can
    # never route to INVALIDATED.
    assert all(not row.routing.invalidates for row in rows.values())


def test_a_component_the_candidate_never_consumed_cannot_reopen_it(tmp_path: Path) -> None:
    """Negative control: the running code has a component, check and prompt this older sealed
    record never named; none of them reopens it (docs/STATE_MACHINE.md section 9)."""
    _bundle(
        tmp_path,
        "older-record",
        "READY_FOR_PROPOSAL",
        _record(
            **{
                "components__reviewer_logic": None,
                "validators__BC-01": None,
                "prompts__targeted_repair": None,
            }
        ),
    )

    (row,) = portfolio_routing(tmp_path, code_dependencies(PROMPTS))

    assert row.changed == () and row.routing.state is None
    assert row.would_become == "READY_FOR_PROPOSAL"


def test_a_bundle_already_holding_an_update_keeps_it_in_the_dry_run(tmp_path: Path) -> None:
    _bundle(tmp_path, "held", STATE_UPDATE_AVAILABLE, _record(components__renderer="0"), update={})

    (row,) = portfolio_routing(tmp_path, code_dependencies(PROMPTS))

    assert row.state == STATE_UPDATE_AVAILABLE and row.would_become == STATE_UPDATE_AVAILABLE


def test_the_dry_run_sees_the_same_changes_a_real_run_would(tmp_path: Path) -> None:
    sealed = _record(components__renderer="0", validator_version="0")
    _bundle(tmp_path, "one", "READY_FOR_PROPOSAL", sealed)
    (row,) = portfolio_routing(tmp_path, code_dependencies(PROMPTS))
    code = {k: v for k, v in code_dependencies(PROMPTS).items() if k != "environment"}
    real = evaluate(sealed, {**sealed, **code})
    assert row.changed == tuple(change.dependency for change in real.changes)


def test_held_updates_name_the_scope_the_manifest_recorded(tmp_path: Path) -> None:
    _bundle(
        tmp_path,
        "update-held",
        STATE_UPDATE_AVAILABLE,
        _record(),
        update={"triggering_scope": "authoring", "earliest_affected_stage": "COMPOSING"},
    )
    _bundle(
        tmp_path,
        "invalidated",
        STATE_INVALIDATED,
        _record(),
        invalidated={"scope": "facts", "causal_stage": "EXTRACTING"},
    )
    _bundle(tmp_path, "old-record", STATE_UPDATE_AVAILABLE, _record(), update={})
    _bundle(tmp_path, "ready", "READY_FOR_PROPOSAL", _record())

    held = {item.repository_dir: item for item in held_updates(tmp_path)}

    assert set(held) == {"update-held", "invalidated", "old-record"}
    assert (held["update-held"].scope, held["update-held"].stage) == ("authoring", "COMPOSING")
    assert (held["invalidated"].scope, held["invalidated"].stage) == ("facts", "EXTRACTING")
    assert held["old-record"].scope is None  # recorded before scopes existed
