"""The facts document for a real local clone: identity, manifest, license, and assets."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.extract import (
    _source_build_fact,
    extract_facts,
)
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.core.examples import ExampleReceipt
from repository_presenter.core.facts import Evidence, Fact
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

    document, probes = extract_facts(
        ENTRY, snapshot, clone.path, tree_paths, plugin, plugin.detect_manifest(clone.path)
    )

    # Every live read is recorded beside the facts, never inside them: a probe carries the
    # duration and the registry's current version, which no fact may hash (section 27.2 RC7).
    assert {probe.kind for probe in probes} <= {"link", "package_registry"}
    assert all(probe.elapsed_ms is not None for probe in probes)
    hashed = " ".join(
        evidence.detail or "" for fact in document.facts for evidence in fact.evidence
    )
    assert "latest " not in hashed
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

    again, _ = extract_facts(
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

    document, _ = extract_facts(
        ENTRY, snapshot, clone.path, list_tree_paths(clone.path), plugin, None
    )

    assert {fact.kind for fact in document.facts} == {
        "identity",
        "inherited_unit",
        "link_target",  # the product-page lookup, unresolved offline
        "public_symbol",
    }
    assert [f.value for f in document.by_kind("inherited_unit")] == ["# Example"]
    assert [f.value for f in document.by_kind("public_symbol")] == ["pkg"]


def _install(polarity: str = "CONTRADICTED") -> Fact:
    return Fact(
        "install_command:dotnet",
        "install_command",
        "dotnet add package Aspose.Widget",
        (Evidence("Widget.csproj", "install command for the package id declared by the manifest"),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _receipt(outcome: str) -> ExampleReceipt:
    return ExampleReceipt(1, outcome, 0, "", "", "d")  # type: ignore[arg-type]


NET_ENTRY = RegistryEntry.model_validate(
    {
        **ENTRY.model_dump(mode="json"),
        "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-.NET",
        "family": "widget",
        "platform": "net",
        "ecosystem": "net",
    }
)
CPP_ENTRY = RegistryEntry.model_validate(
    {
        **ENTRY.model_dump(mode="json"),
        "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-Cpp",
        "family": "widget",
        "platform": "cpp",
        "ecosystem": "cpp",
    }
)


def test_a_verified_source_build_is_admitted_when_the_registry_says_not_yet_published() -> None:
    """G4-W17 arrival item 0. A registry's CONTRADICTED reading means the package is not there,
    not that the repository cannot be used - an EXECUTED example already proves the source
    compiles at this revision, using the exact command the ecosystem's own spec names."""
    admitted = _source_build_fact(_install(), NET_ENTRY, [_receipt("FAILED"), _receipt("EXECUTED")])
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
        "cd Aspose.Widget-FOSS-for-.NET\ndotnet build"
    )
    assert admitted.attributes == {"install_kind": "source"}
    assert "verified source build" in admitted.evidence[-1].detail
    # The manifest's own evidence is kept, not replaced - both facts justify the value now.
    assert (
        admitted.evidence[0].detail == "install command for the package id declared by the manifest"
    )


def test_a_verified_source_build_is_not_admitted_without_reason() -> None:
    # No executed example: nothing proves the source compiles.
    assert (
        _source_build_fact(_install(), NET_ENTRY, [_receipt("FAILED")]).polarity == "CONTRADICTED"
    )
    # Already SUPPORTED: nothing to admit.
    assert _source_build_fact(
        _install("SUPPORTED"), NET_ENTRY, [_receipt("EXECUTED")]
    ).polarity == ("SUPPORTED")
    # Not an install_command fact at all: nothing to admit.
    not_install = replace(_install(), kind="package", id="package:name")
    assert _source_build_fact(not_install, NET_ENTRY, [_receipt("EXECUTED")]) is not_install


def test_a_registry_less_ecosystems_unresolved_install_is_admitted_too() -> None:
    """G4-W17 arrival item 24. With no registry to read as "not there", a registry-less
    ecosystem's install fact can never become CONTRADICTED - it starts and stays UNRESOLVED
    forever, so item 0's gate never opened for it. Measured 2026-09-06 on the whole C++ cohort:
    `cpp` has no `REGISTRY_TYPES` entry, and PDF and Cells C++ had no other blocker."""
    plugin_for("cpp")  # imports platforms/cpp.py, which registers its own EcosystemSpec
    admitted = _source_build_fact(_install("UNRESOLVED"), CPP_ENTRY, [_receipt("EXECUTED")])
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Cpp.git\n"
        "cd Aspose.Widget-FOSS-for-Cpp\ncmake -S . -B build"
    )
    assert admitted.attributes == {"install_kind": "source"}


def test_a_registry_having_ecosystems_unresolved_install_stays_unresolved() -> None:
    """G4-W17 arrival item 24's own mutation test. UNRESOLVED for a registry-having ecosystem
    means the probe could not be read this time - a transient reading, never "not published" -
    so it must keep failing closed even with an EXECUTED receipt, exactly as it did before this
    item; only a registry-less ecosystem's UNRESOLVED is admitted."""
    assert (
        _source_build_fact(_install("UNRESOLVED"), NET_ENTRY, [_receipt("EXECUTED")]).polarity
        == "UNRESOLVED"
    )
