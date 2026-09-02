"""Schemas under schemas/ validate the cursor, the reuse manifest, and sealed bundle manifests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from repository_presenter.core.candidates import COUNTED_STATES
from support import REPO_ROOT

SCHEMAS = REPO_ROOT / "schemas"
CURSOR = REPO_ROOT / "project" / "state.yaml"
MANIFEST = REPO_ROOT / "migration" / "reuse-manifest.yaml"
BUNDLE_FILES = (
    "README.md",
    "README.patch",
    "facts.json",
    "dispositions.json",
    "plan.json",
    "validation.json",
    "review.json",
    "calls.jsonl",
    "dependencies.json",
)


class _TextTimestampLoader(yaml.SafeLoader):
    """Keep dates and timestamps as text so the schemas constrain their written form."""


_TextTimestampLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_TextTimestampLoader)


def load_schema(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def errors(validator: Draft202012Validator, instance: Any) -> list[str]:
    found = sorted(validator.iter_errors(instance), key=lambda error: error.json_path)
    return [f"{error.json_path}: {error.message}" for error in found]


def sealed_manifest(state: str = "READY_FOR_PROPOSAL") -> dict[str, Any]:
    proven = state == "READY_FOR_PROPOSAL"
    return {
        "schema_version": 1,
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "revision": "0" * 40,
        "state": state,
        "sealed_at": "2026-09-02T12:00:00+05:00",
        "files": {name: {"sha256": "a" * 64, "bytes": 1} for name in BUNDLE_FILES},
        "provider_calls": 6,
        "no_op_proof": (
            {
                "proven_at": "2026-09-02T12:05:00+05:00",
                "fresh_process": True,
                "byte_identical": True,
                "provider_calls": 0,
            }
            if proven
            else None
        ),
    }


@pytest.mark.parametrize(
    ("schema", "instance"),
    [("state.schema.json", CURSOR), ("reuse-manifest.schema.json", MANIFEST)],
    ids=["cursor", "reuse-manifest"],
)
def test_governance_file_validates_against_its_schema(schema: str, instance: Path) -> None:
    assert errors(load_schema(schema), load_yaml(instance)) == []


def test_cursor_schema_rejects_drift() -> None:
    validator = load_schema("state.schema.json")
    cursor = load_yaml(CURSOR)

    unknown_status = copy.deepcopy(cursor)
    unknown_status["active_work_item"]["status"] = "DONE"
    assert errors(validator, unknown_status)

    extra_field = copy.deepcopy(cursor)
    extra_field["roadmap"] = []
    assert errors(validator, extra_field)

    direct_push = copy.deepcopy(cursor)
    direct_push["publication"]["direct_default_branch_push_allowed"] = True
    assert errors(validator, direct_push)


def test_cursor_schema_ties_blockers_to_blocked_statuses() -> None:
    validator = load_schema("state.schema.json")
    cursor = load_yaml(CURSOR)
    item = cursor["active_work_item"]

    item["status"] = "BLOCKED_EXTERNAL"
    item["blocker"] = None
    assert errors(validator, cursor)

    item["blocker"] = {
        "class": "BLOCKED_EXTERNAL",
        "summary": "Branch protection requires an owner.",
        "resume_predicate": "main requires the CI status check before merge.",
        "recorded_at": "2026-09-02T12:00:00+05:00",
    }
    assert errors(validator, cursor) == []

    item["status"] = "IN_PROGRESS"
    assert errors(validator, cursor)


def test_cursor_schema_keeps_owner_predicates_in_owner_items() -> None:
    validator = load_schema("state.schema.json")
    cursor = load_yaml(CURSOR)
    assert cursor["owner_items"], "owner-only predicates live in owner_items, never in a gate"
    assert all(item["consumed_by"] for item in cursor["owner_items"])

    unconsumed = copy.deepcopy(cursor)
    del unconsumed["owner_items"][0]["consumed_by"]
    assert errors(validator, unconsumed)

    unknown_status = copy.deepcopy(cursor)
    unknown_status["owner_items"][0]["status"] = "WAITING"
    assert errors(validator, unknown_status)

    force_push = copy.deepcopy(cursor)
    force_push["publication"]["control_repository"]["push"] = "FORCE"
    assert errors(validator, force_push)

    product_push = copy.deepcopy(cursor)
    product_push["publication"]["direct_default_branch_push_allowed"] = True
    assert errors(validator, product_push)


def test_manifest_schema_requires_complete_file_records() -> None:
    validator = load_schema("reuse-manifest.schema.json")
    manifest = load_yaml(MANIFEST)
    record = {
        "source_path": "src/readme_agent/retry.py",
        "sha256": "b" * 64,
        "disposition": "PORT_NEARLY_INTACT",
        "destination": "src/repository_presenter/core/retry.py",
        "retained_behavior": ["Bounded retry with typed failure classes."],
        "removed_behavior": [],
        "tests_ported": ["tests/core/test_retry.py"],
        "acceptance": "Official entry point exercises retry on the canary.",
        "import_closure": ["src/readme_agent/errors.py"],
        "pulled_at": "2026-09-03",
        "work_item": "G1-W01",
    }
    manifest["file_records"] = [record]
    assert errors(validator, manifest) == []

    without_hash = copy.deepcopy(manifest)
    del without_hash["file_records"][0]["sha256"]
    assert errors(validator, without_hash)

    short_hash = copy.deepcopy(manifest)
    short_hash["file_records"][0]["sha256"] = "b" * 40
    assert errors(validator, short_hash)

    unknown_disposition = copy.deepcopy(manifest)
    unknown_disposition["file_records"][0]["disposition"] = "COPY"
    assert errors(validator, unknown_disposition)


def test_manifest_schema_records_owner_exclusions() -> None:
    validator = load_schema("reuse-manifest.schema.json")
    manifest = load_yaml(MANIFEST)
    manifest["source"]["working_tree_at_freeze"]["exclusions"] = [
        {
            "path": "src/readme_agent/supervisor/mission_execution_guard.py",
            "kind": "MODIFIED",
            "disposition": "EXCLUDED_BY_DEFAULT_PENDING_OWNER_OVERRIDE",
            "reason": "Uncommitted at the frozen revision; the supervisor package is RETIRE.",
        }
    ]
    assert errors(validator, manifest) == []
    manifest["source"]["working_tree_at_freeze"]["exclusions"][0]["disposition"] = "KEEP"
    assert errors(validator, manifest)


def test_bundle_schema_accepts_sealed_bundles() -> None:
    validator = load_schema("candidate-bundle.schema.json")
    assert errors(validator, sealed_manifest("READY_FOR_PROPOSAL")) == []
    assert errors(validator, sealed_manifest("ACCEPTED")) == []


def test_bundle_schema_requires_no_op_proof_before_ready_for_proposal() -> None:
    validator = load_schema("candidate-bundle.schema.json")
    unproven = sealed_manifest("READY_FOR_PROPOSAL")
    unproven["no_op_proof"] = None
    assert errors(validator, unproven)

    with_calls = sealed_manifest("READY_FOR_PROPOSAL")
    with_calls["no_op_proof"]["provider_calls"] = 1
    assert errors(validator, with_calls)

    differing = sealed_manifest("READY_FOR_PROPOSAL")
    differing["no_op_proof"]["byte_identical"] = False
    assert errors(validator, differing)


def test_bundle_schema_rejects_incomplete_or_unknown_bundles() -> None:
    validator = load_schema("candidate-bundle.schema.json")
    missing_file = sealed_manifest()
    del missing_file["files"]["dependencies.json"]
    assert errors(validator, missing_file)

    unknown_state = sealed_manifest()
    unknown_state["state"] = "PUBLISHED"
    assert errors(validator, unknown_state)

    bad_digest = sealed_manifest()
    bad_digest["files"]["README.md"]["sha256"] = "not-a-hash"
    assert errors(validator, bad_digest)


def test_counted_states_are_sealed_bundle_states() -> None:
    schema = json.loads((SCHEMAS / "candidate-bundle.schema.json").read_text(encoding="utf-8"))
    assert set(schema["properties"]["state"]["enum"]) >= COUNTED_STATES
