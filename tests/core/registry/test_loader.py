"""The registry allow-list on disk: fail-closed loading and the admission gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.core.errors import ConfigError, NotAllowlistedError
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    enabled_entries,
    find_entry,
    is_permitted,
    load_registry,
    require_listed,
)
from support import REPO_ROOT

REGISTRY = REPO_ROOT / REGISTRY_RELATIVE_PATH
CANARY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
LISTED = "example/Aspose.Widget-FOSS-for-Java"


def write_registry(path: Path, entries: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8")
    return path


def disabled_widget() -> dict[str, Any]:
    return {
        "repository": LISTED,
        "family": "widget",
        "platform": "java",
        "ecosystem": "java",
        "mode": "disabled",
        "policy_profile": "example-widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 10, "node_id": "R_10"},
    }


def test_real_registry_validates_against_its_schema() -> None:
    schema = json.loads((REPO_ROOT / "schemas" / "registry.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(json.loads(REGISTRY.read_text("utf-8"))))
    assert errors == []


def test_real_registry_is_the_frozen_portfolio() -> None:
    registry = load_registry(REGISTRY)
    assert len(registry.entries) == 34
    assert [e.repository for e in registry.entries] == sorted(
        (e.repository for e in registry.entries), key=str.casefold
    )
    assert all(e.active for e in registry.entries)
    assert {e.mode for e in registry.entries} == {"full", "dry_run", "disabled"}
    assert len(enabled_entries(registry)) == 31


def test_real_registry_admits_the_canary_read_only() -> None:
    registry = load_registry(REGISTRY)
    canary = require_listed(registry, CANARY)
    assert canary.mode == "dry_run"
    assert canary.ecosystem == "python"
    assert (canary.family, canary.platform) == ("3d", "python")
    assert canary.clone_url == f"https://github.com/{CANARY}.git"
    assert canary.provider_identity.repository_id == 1138357893
    assert is_permitted(registry, CANARY) is canary


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="registry not found"):
        load_registry(tmp_path / "nope.json")


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_registry(bad)


@pytest.mark.parametrize(
    "document",
    [[], {"schema_version": 2, "entries": []}, {"schema_version": 1, "entries": [{"family": "x"}]}],
)
def test_malformed_documents_fail_closed(tmp_path: Path, document: Any) -> None:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ConfigError, match="malformed"):
        load_registry(path)


def test_nonconforming_repository_name_fails_closed(tmp_path: Path) -> None:
    widget = disabled_widget()
    widget.update(
        repository="aspose-html-foss/CSSForge", family="html", platform="python", ecosystem="python"
    )
    path = write_registry(tmp_path / "registry.json", [widget])
    with pytest.raises(ConfigError, match="repository name must match"):
        load_registry(path)


def test_gates_distinguish_presence_from_permission(tmp_path: Path) -> None:
    registry = load_registry(write_registry(tmp_path / "registry.json", [disabled_widget()]))

    assert find_entry(registry, LISTED) is registry.entries[0]
    assert require_listed(registry, LISTED).mode == "disabled"
    assert is_permitted(registry, LISTED) is None
    assert enabled_entries(registry) == ()

    assert find_entry(registry, "some-org/not-listed") is None
    assert is_permitted(registry, "some-org/not-listed") is None
    with pytest.raises(NotAllowlistedError, match="not in the registry allow-list") as info:
        require_listed(registry, "some-org/not-listed")
    assert info.value.exit_code == 3
