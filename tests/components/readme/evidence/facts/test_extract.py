"""The facts document for a real local clone: identity, manifest, license, and assets."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.extract import extract_facts
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths
from support import REPO_ROOT, commit_all, init_git_repository


@pytest.fixture(autouse=True)
def _no_live_product_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "fetch_status", lambda url: (404, url))


ENTRY = RegistryEntry.model_validate(
    {
        "repository": "example-org/Aspose.Example-FOSS-for-Python",
        "family": "example",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "example",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 7, "node_id": "R_7"},
    }
)


def _canary_like_source(tmp_path: Path) -> Path:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    (source / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="aspose-example", version="1.0.0",'
        ' python_requires=">=3.8")\n',
        encoding="utf-8",
    )
    (source / "aspose" / "example").mkdir(parents=True)
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (source / "aspose" / "example" / "__init__.py").write_text("VERSION = '1.0.0'\n", "utf-8")
    (source / "tests").mkdir()
    (source / "tests" / "test_example.py").write_text("def test_ok():\n    pass\n", "utf-8")
    commit_all(source, "seed")
    return source


def test_facts_document_for_a_local_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={"message": "Not Found"}),
    )
    source = _canary_like_source(tmp_path)
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    plugin = plugin_for(ENTRY.ecosystem)
    tree_paths = list_tree_paths(clone.path)

    document = extract_facts(
        ENTRY, snapshot, clone.path, tree_paths, plugin, plugin.detect_manifest(clone.path)
    )

    ids = sorted(fact.id for fact in document.facts)
    assert ids == [
        "build_test_asset:tests",
        "dependency:none",
        "identity:ecosystem",
        "identity:family",
        "identity:platform",
        "identity:repository",
        "identity:revision",
        "import_path:aspose",
        "import_path:aspose.example",
        "inherited_unit:001.heading",
        "install_command:pip",
        "license:file",
        "license:spdx",
        "link_target:product.banner",
        "link_target:product.enterprise",
        "link_target:product.homepage",
        "package:name",
        "package:python_requires",
        "package:version",
        "public_symbol:aspose",
        "public_symbol:aspose.example",
    ]
    by_id = {fact.id: fact for fact in document.facts}
    assert by_id["identity:revision"].value == clone.revision
    assert by_id["license:spdx"].value == "MIT"
    assert by_id["package:name"].value == "aspose-example"
    assert by_id["install_command:pip"].polarity == "CONTRADICTED"
    assert by_id["install_command:pip"].evidence[1].detail == (
        "package registry: distribution not found"
    )
    assert all(fact.evidence for fact in document.facts)

    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []

    again = extract_facts(
        ENTRY, snapshot, clone.path, tree_paths, plugin, plugin.detect_manifest(clone.path)
    )
    assert again.to_json() == document.to_json()


def test_without_a_manifest_only_identity_license_and_assets_remain(tmp_path: Path) -> None:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "pkg").mkdir()
    (source / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    commit_all(source, "seed")
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    plugin = plugin_for("python")

    document = extract_facts(ENTRY, snapshot, clone.path, list_tree_paths(clone.path), plugin, None)

    assert {fact.kind for fact in document.facts} == {
        "identity",
        "inherited_unit",
        "link_target",  # the product-page lookup, unresolved offline
        "public_symbol",
    }
    assert [f.value for f in document.by_kind("inherited_unit")] == ["# Example"]
    assert [f.value for f in document.by_kind("public_symbol")] == ["pkg"]
