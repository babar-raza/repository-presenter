"""Dependency evaluation: each changed class names the state it reopens; nothing changed is NONE."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.bundle.evaluation import (
    Change,
    evaluate,
    evaluation_document,
    summarize_evaluation,
    write_evaluation,
)

SEALED: dict[str, Any] = {
    "schema_version": 1,
    "source": {"revision": "a" * 40, "tree_sha256": "t" * 64},
    "facts": {"identity:repository": "1" * 64, "format:output.glb": "2" * 64},
    "prompts": {
        "repository_investigation": {
            "sha256": "i" * 64,
            "version": "1",
            "model_route": "qwen3-next",
        },
        "source_reconciliation": {"sha256": "r" * 64, "version": "1", "model_route": "qwen3-next"},
        "presentation_planning": {"sha256": "p" * 64, "version": "1", "model_route": "qwen3-next"},
        "section_authoring": {"sha256": "s" * 64, "version": "1", "model_route": "qwen3-next"},
        "independent_review": {"sha256": "v" * 64, "version": "2", "model_route": "qwen3-next"},
        "targeted_repair": {"sha256": "x" * 64, "version": "2", "model_route": "qwen3-next"},
    },
    "contract_version": "readme-contract-v1-draft",
    "components": {"shell": "1", "renderer": "1", "normalisation": "1"},
    "validators": {"BC-01": "1", "BC-02": "1"},
    "validator_version": "1",
    "acceptance_profile_version": None,
    "policy": {"version": "1", "sha256": "y" * 64},
    "protected_content_fingerprint": "f" * 64,
}


def _current(**overrides: Any) -> dict[str, Any]:
    current = copy.deepcopy(SEALED)
    del current["protected_content_fingerprint"]
    for path, value in overrides.items():
        target = current
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return current


def test_an_unchanged_input_set_is_none() -> None:
    evaluation = evaluate(SEALED, _current())
    assert evaluation.changes == () and evaluation.earliest == "NONE"
    document = evaluation_document("a" * 40, evaluation)
    assert document["earliest_affected_stage"] == "NONE" and document["changes"] == []
    assert summarize_evaluation(document) == "earliest affected stage NONE; 0 changes"


def test_each_dependency_class_names_the_state_it_reopens() -> None:
    cases = {
        "source__revision": ("source", "EXTRACTING"),
        "facts__format:output.glb": ("facts", "EXTRACTING"),
        "prompts__repository_investigation__sha256": (
            "prompts.repository_investigation",
            "INVESTIGATING",
        ),
        "prompts__source_reconciliation__version": ("prompts.source_reconciliation", "RECONCILING"),
        "prompts__presentation_planning__model_route": (
            "prompts.presentation_planning",
            "PLANNING",
        ),
        "prompts__section_authoring__sha256": ("prompts.section_authoring", "COMPOSING"),
        "prompts__independent_review__sha256": ("prompts.independent_review", "REVIEWING"),
        "prompts__targeted_repair__sha256": ("prompts.targeted_repair", "REVIEWING"),
        "contract_version": ("contract_version", "VALIDATING"),
        "components__renderer": ("components.renderer", "COMPOSING"),
        # The normalisation the composition package owns decides rendered bytes, so a change
        # to it reopens COMPOSING like any other component (the gap recorded at d147b4a).
        "components__normalisation": ("components.normalisation", "COMPOSING"),
        "validators__BC-02": ("validators", "VALIDATING"),
        "validator_version": ("validators", "VALIDATING"),
        "acceptance_profile_version": ("acceptance_profile_version", "REVIEWING"),
        "policy__sha256": ("policy", "PLANNING"),
    }
    for path, (dependency, state) in cases.items():
        evaluation = evaluate(SEALED, _current(**{path: "changed"}))
        assert [c.dependency for c in evaluation.changes] == [dependency], path
        assert evaluation.earliest == state, path
    added = _current()
    added["facts"]["format:input.obj"] = "3" * 64
    del added["facts"]["identity:repository"]
    evaluation = evaluate(SEALED, added)
    assert evaluation.changes == (
        Change("facts", "1 fact records added, 1 removed, 0 altered", "EXTRACTING"),
    )
    new_prompt = _current()
    new_prompt["prompts"]["extra_job"] = {"sha256": "z" * 64, "version": "1", "model_route": "m"}
    assert evaluate(SEALED, new_prompt).changes == (
        Change("prompts.extra_job", "prompt added", "INVESTIGATING"),
    )


def test_changes_order_by_state_and_the_earliest_wins(tmp_path: Path) -> None:
    current = _current(**{"prompts__section_authoring__sha256": "c", "policy__sha256": "d"})
    current["validators"]["BC-01"] = "2"
    evaluation = evaluate(SEALED, current)
    assert [(c.dependency, c.reopens) for c in evaluation.changes] == [
        ("policy", "PLANNING"),
        ("prompts.section_authoring", "COMPOSING"),
        ("validators", "VALIDATING"),
    ]
    assert evaluation.earliest == "PLANNING"
    document = evaluation_document("a" * 40, evaluation)
    assert summarize_evaluation(document) == (
        "earliest affected stage PLANNING; 3 changes (policy -> PLANNING, "
        "prompts.section_authoring -> COMPOSING, validators -> VALIDATING)"
    )
    digest = write_evaluation(document, tmp_path / "evaluation.json")
    assert write_evaluation(document, tmp_path / "evaluation.json") == digest
    assert json.loads((tmp_path / "evaluation.json").read_text("utf-8")) == document
    unsealed = evaluation_document(None, None)
    assert unsealed["sealed_bundle"] is None and unsealed["earliest_affected_stage"] == "EXTRACTING"
    assert summarize_evaluation(unsealed) == "no sealed bundle for this revision; every stage runs"


# The invalidation matrix (docs/STATE_MACHINE.md section 9, G2-W05) against the sealed canary
# bundle's own dependency record: one case per dependency class, as a path into the record and
# the state its change reopens.
SEALED_CANARY = (
    Path(__file__).resolve().parents[4]
    / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "65b1f577c0f16d0d9112bb6c1153d3024543ac02/dependencies.json"
)
DEPENDENCY_CLASSES: dict[str, tuple[list[str], str]] = {
    "source revision": (["source", "revision"], "EXTRACTING"),
    "fact extractor (a fact record's digest)": (["facts", "identity:repository"], "EXTRACTING"),
    "investigation prompt": (["prompts", "repository_investigation", "sha256"], "INVESTIGATING"),
    "reconciliation prompt": (["prompts", "source_reconciliation", "sha256"], "RECONCILING"),
    "planning prompt": (["prompts", "presentation_planning", "sha256"], "PLANNING"),
    "model route": (["prompts", "section_authoring", "model_route"], "COMPOSING"),
    "template component": (["components", "renderer"], "COMPOSING"),
    "normalisation component": (["components", "normalisation"], "COMPOSING"),
    "validator": (["validators", "BC-07"], "VALIDATING"),
    "reviewer rubric": (["prompts", "independent_review", "sha256"], "REVIEWING"),
    "link policy": (["policy", "sha256"], "PLANNING"),
}


def _sealed_canary() -> dict[str, Any]:
    return json.loads(SEALED_CANARY.read_text("utf-8"))


def _changed(document: dict[str, Any], path: list[str]) -> dict[str, Any]:
    current = copy.deepcopy(document)
    target: Any = current
    for part in path[:-1]:
        target = target[part]
    assert path[-1] in target, path
    target[path[-1]] = "changed"
    return current


def test_the_sealed_canary_reopens_nothing_when_nothing_changed() -> None:
    sealed = _sealed_canary()
    assert evaluate(sealed, copy.deepcopy(sealed)).earliest == "NONE"
    # The record lists only what the candidate consumed: no global control-plane hash.
    assert set(sealed) == {
        "schema_version",
        "source",
        "facts",
        "prompts",
        "contract_version",
        "components",
        "validators",
        "validator_version",
        "acceptance_profile_version",
        "policy",
        "protected_content_fingerprint",
    }


@pytest.mark.parametrize(("label", "case"), sorted(DEPENDENCY_CLASSES.items()))
def test_each_dependency_class_of_the_sealed_canary_reopens_its_own_state(
    label: str, case: tuple[list[str], str]
) -> None:
    path, state = case
    sealed = _sealed_canary()
    evaluation = evaluate(sealed, _changed(sealed, path))
    assert evaluation.earliest == state, label
    assert len(evaluation.changes) == 1, (label, evaluation.changes)
    assert evaluation.changes[0].dependency.startswith(path[0]), label
