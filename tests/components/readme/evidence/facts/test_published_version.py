"""TC-CLM-01: `package:published_version` exists only on a conclusive registry reading, and its
evidence is deterministic (no timestamp, status, or duration)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts import links, published_version
from repository_presenter.components.readme.evidence.facts.extract import extract_facts
from repository_presenter.components.readme.evidence.facts.published_version import (
    PUBLISHED_VERSION_FACT_ID,
    published_version_fact,
)
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.extractors.surface.registry import RegistryObservation
from repository_presenter.core.facts import Evidence, Fact
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths
from support import REPO_ROOT, commit_all, init_git_repository

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "family": "slides",
        "platform": "java",
        "ecosystem": "java",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
NAME = Fact(
    "package:name",
    "package",
    "org.aspose:aspose-slides-foss",
    (Evidence("pom.xml", "`groupId` and `artifactId` declared by the POM"),),
)
URL = "https://repo1.maven.org/maven2/org/aspose/aspose-slides-foss/maven-metadata.xml"


def _reading(**overrides: object) -> RegistryObservation:
    values: dict[str, object] = {
        "registry": "maven",
        "name": NAME.value,
        "published": True,
        "ambiguous": False,
        "evidence_url": URL,
        "method": "maven-metadata-xml",
        "source": "live_probe",
        "latest_version": "26.7.0",
    }
    return RegistryObservation(**{**values, **overrides})  # type: ignore[arg-type]


def test_a_conclusive_published_reading_becomes_the_published_version_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(published_version, "_observe", lambda ecosystem, name: _reading())
    fact = published_version_fact(ENTRY, NAME)
    assert fact is not None
    assert (fact.id, fact.kind, fact.value, fact.polarity) == (
        PUBLISHED_VERSION_FACT_ID,
        "package",
        "26.7.0",
        "SUPPORTED",
    )
    assert fact.evidence[0].path == URL
    detail = fact.evidence[0].detail or ""
    assert "latest " not in detail and "26.7.0" not in detail
    assert fact.attributes == {"registry": "maven"}
    # Two reads of the same registry state give identical bytes (no timestamp, no status).
    assert published_version_fact(ENTRY, NAME) == fact


@pytest.mark.parametrize(
    "reading",
    [
        _reading(published=None, ambiguous=True, latest_version=None),  # registry unreachable
        _reading(ambiguous=True),  # answered ambiguously
        _reading(published=False, latest_version=None),  # 404
        _reading(latest_version=None),  # published, no stable release listed
    ],
    ids=["unreachable", "ambiguous", "not-found", "no-stable-release"],
)
def test_nothing_conclusive_yields_no_fact_never_an_invented_version(
    monkeypatch: pytest.MonkeyPatch, reading: RegistryObservation
) -> None:
    monkeypatch.setattr(published_version, "_observe", lambda ecosystem, name: reading)
    assert published_version_fact(ENTRY, NAME) is None


def test_without_a_supported_package_name_nothing_is_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(ecosystem: str, name: str) -> RegistryObservation:
        raise AssertionError("the registry must not be asked without a package identity")

    monkeypatch.setattr(published_version, "_observe", refuse)
    assert published_version_fact(ENTRY, None) is None


def test_extract_facts_emits_the_fact_beside_the_manifest_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(links, "fetch_status", lambda url: (404, url))
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={}),
    )
    entry = ENTRY.model_copy(update={"platform": "python", "ecosystem": "python"})
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="aspose-example", version="1.0.0")\n',
        encoding="utf-8",
    )
    (source / "aspose").mkdir()
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    commit_all(source, "seed")
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(entry.repository, clone)
    plugin = plugin_for("python")
    paths = list_tree_paths(clone.path)
    manifest = plugin.detect_manifest(clone.path)

    asked: list[tuple[str, str]] = []

    def observed(ecosystem: str, name: str) -> RegistryObservation:
        asked.append((ecosystem, name))
        return _reading(registry="pypi", name=name, latest_version="1.2.0")

    monkeypatch.setattr(published_version, "_observe", observed)
    document, _ = extract_facts(entry, snapshot, clone.path, paths, plugin, manifest)
    by_id = {fact.id: fact for fact in document.facts}
    assert asked == [("python", "aspose-example")]
    assert by_id["package:version"].value == "1.0.0"
    assert by_id[PUBLISHED_VERSION_FACT_ID].value == "1.2.0"
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []

    # An unreachable registry: the fact is simply absent and nothing else changes.
    monkeypatch.setattr(
        published_version,
        "_observe",
        lambda ecosystem, name: _reading(published=None, ambiguous=True, latest_version=None),
    )
    unreadable, _ = extract_facts(entry, snapshot, clone.path, paths, plugin, manifest)
    assert PUBLISHED_VERSION_FACT_ID not in {fact.id for fact in unreadable.facts}
    assert {f.id for f in unreadable.facts} == set(by_id) - {PUBLISHED_VERSION_FACT_ID}


def test_the_fact_id_core_names_is_the_one_a_package_fact_slugs_to() -> None:
    from repository_presenter.core.facts import fact_id
    from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID as named

    assert named == fact_id("package", "published_version")
