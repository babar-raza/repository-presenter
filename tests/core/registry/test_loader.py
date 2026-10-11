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
    assert len(registry.entries) == 44
    assert [e.repository for e in registry.entries] == sorted(
        (e.repository for e in registry.entries), key=str.casefold
    )
    assert all(e.active for e in registry.entries)
    # G4-W17 arrival item 31: aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript's `disabled` mode
    # was a stale flag, not a content defect - no clone had ever been attempted
    # (evidence/build/lanes/lane-b/G4-W14.json). Flipped to dry_run; the reachable ceiling moved
    # 31 to 32. 2026-09-25 (owner ruling, docs/DECISION_LOG.md): aspose-imaging-foss's .NET repo
    # (OWNER-08, admitted 2026-09-23 at mode disabled) flipped to dry_run, and a new entry,
    # aspose-gis-foss/Aspose.GIS.FOSS-for-.Net (the org's only repository, added 2026-09-22,
    # confirmed via live `gh api orgs/aspose-gis-foss/repos`), admitted directly at mode dry_run
    # - both by explicit owner instruction, not auto-admission. Ceiling moves 32 to 34.
    # 2026-09-30 (owner ruling, docs/DECISION_LOG.md, this date): project/state.yaml's
    # `progress.denominator` no longer freezes at the 2026-09-01 legacy baseline - it now tracks
    # `len(registry.entries)` live (36, not this function's own `enabled_entries` count, then 34;
    # see test_governance_consistency.py::test_the_cursor_denominator_matches_the_live_registry).
    # 2026-10-07 (owner ruling, docs/DECISION_LOG.md, this date): aspose-psd-foss's .NET and
    # Python repositories - disabled since admission with no reason ever recorded (flagged as an
    # open question by the 2026-09-30 retry-list entry above) - flipped `disabled` to `dry_run` on
    # explicit owner instruction, matching the majority mode rather than the two `full` entries.
    # No registry entry is now `disabled`; the mode set and the reachable ceiling both move to
    # the full 36.
    # 2026-10-11 (owner decision via the interactive box, docs/DECISION_LOG.md): seven of the
    # eight aspose-email-foss/Aspose.JMAP-FOSS-for-* libraries (a new `jmap` family inside the
    # Email organization) admitted at mode dry_run - nothing is ever pushed. The eighth, Node.js,
    # followed once its ecosystem had a platform plugin (platforms/nodejs.py; the guard in
    # tests/components/readme/extractors/platforms/test_registry.py keeps an entry from landing
    # without one). The registry and the reachable ceiling both move 36 to 43, then 44.
    assert {e.mode for e in registry.entries} == {"full", "dry_run"}
    assert len(enabled_entries(registry)) == 44


def test_the_jmap_family_is_admitted_at_dry_run_in_the_email_organization() -> None:
    registry = load_registry(REGISTRY)
    jmap = [e for e in registry.entries if e.family == "jmap"]
    assert {e.platform for e in jmap} == {
        "python",
        "typescript",
        "go",
        "rust",
        "net",
        "cpp",
        "java",
        "nodejs",
    }
    assert all(e.platform == e.ecosystem for e in jmap)
    assert {e.mode for e in jmap} == {"dry_run"}
    assert {e.owner for e in jmap} == {"aspose-email-foss"}
    assert all(e.active and e.issues_mode is None for e in jmap)
    # Two organization-level entries the owner did not choose stay unregistered (not allow-listed,
    # so never touched): the Go MCP server and the Slides organization's `.github` repository.
    for repository in (
        "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP",
        "aspose-slides-foss/.github",
    ):
        assert find_entry(registry, repository) is None


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


def _schema_errors(entries: list[dict[str, Any]]) -> list[Any]:
    schema = json.loads((REPO_ROOT / "schemas" / "registry.schema.json").read_text("utf-8"))
    document = {"schema_version": 1, "entries": entries}
    return list(Draft202012Validator(schema).iter_errors(document))


@pytest.mark.parametrize("value", ["off", "dry_run", "file"])
def test_loader_and_schema_accept_each_issues_mode(tmp_path: Path, value: str) -> None:
    entries = [{**disabled_widget(), "issues_mode": value}]
    assert _schema_errors(entries) == []
    loaded = load_registry(write_registry(tmp_path / "data" / "registry.json", entries))
    assert loaded.entries[0].issues_mode == value


@pytest.mark.parametrize("value", ["full", "on", 1])
def test_loader_and_schema_reject_a_bad_issues_mode(tmp_path: Path, value: Any) -> None:
    entries = [{**disabled_widget(), "issues_mode": value}]
    assert _schema_errors(entries) != []
    with pytest.raises(ConfigError):
        load_registry(write_registry(tmp_path / "data" / "registry.json", entries))


def test_a_null_issues_mode_from_a_model_dump_loads_as_absent(tmp_path: Path) -> None:
    """``RegistryEntry.model_dump()`` emits ``issues_mode: null``; the loader treats it as unset
    (the schema file shape omits the key)."""
    entries = [{**disabled_widget(), "issues_mode": None}]
    loaded = load_registry(write_registry(tmp_path / "data" / "registry.json", entries))
    assert loaded.entries[0].issues_mode is None
    assert loaded.entries[0].effective_issues_mode == "dry_run"
