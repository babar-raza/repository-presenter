"""An unpublished package is a verified state, not a failure (BC-02, wave 6).

The rows are recorded from the wave-6 reseal (cut 8fbf2166): the install fact, the build-command
fact, the README's Installation section and the checkout's root files exactly as the facts stage
saw them for the Aspose.JMAP libraries and Aspose.Cells for Rust (the packages the maintainers say
are unpublished and the registries answer 404 or an empty list for), and for the rows that must
stay refused (a name another project holds, a README that says it is published, no README at all,
a registry that could not be read).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.extract import extract_facts
from repository_presenter.components.readme.evidence.facts.unpublished import (
    DOCUMENTED_BUILD_PHRASE,
    README_STATEMENT_PHRASE,
    documented_source_install,
    documented_steps,
    unpublished_statement,
)
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.extractors.surface.registry import observe
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import (
    DOCUMENTED_COMMAND_ATTRIBUTE,
    NOT_PUBLISHED,
    REGISTRY_COMMAND_ATTRIBUTE,
    REGISTRY_STATE_ATTRIBUTE,
    SOURCE_BASIS_ATTRIBUTE,
    Evidence,
    Fact,
)
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.package_registry import fact_registry_reading
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths
from support import REPO_ROOT, commit_all, init_git_repository

ROWS: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "unpublished_rows.json").read_text("utf-8")
)


@pytest.fixture(autouse=True)
def _no_live_product_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "fetch_status", lambda url: (404, url))


def _fact(raw: dict[str, Any]) -> Fact:
    return Fact(
        raw["id"],
        raw["kind"],
        raw["value"],
        tuple(Evidence(e["path"], e["detail"]) for e in raw["evidence"]),
        polarity=raw["polarity"],
        confidence=raw["confidence"],
        attributes=raw["attributes"],
    )


# The five aspose-jmap-foss rows this module's fixture was recorded from (wave-6 reseal,
# cut 8fbf2166) were removed from data/registry.json 2026-10-17 (owner ruling,
# docs/DECISION_LOG.md, this date; aspose-jmap-foss excluded from scope). This module tests the
# unpublished-package install logic, not the live registry's current membership, so the exact
# entries are frozen here (captured from data/registry.json immediately before removal) rather
# than made to depend on a registry admission that no longer exists.
_RETIRED_JMAP_ENTRIES: dict[str, dict[str, Any]] = {
    "aspose-email-foss/Aspose.JMAP-FOSS-for-Cpp": {
        "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Cpp",
        "family": "jmap",
        "platform": "cpp",
        "ecosystem": "cpp",
        "mode": "dry_run",
        "policy_profile": "aspose-email-foss-jmap-cpp",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1389233504,
            "node_id": "R_kgDOUs4FYA",
        },
    },
    "aspose-email-foss/Aspose.JMAP-FOSS-for-Go": {
        "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Go",
        "family": "jmap",
        "platform": "go",
        "ecosystem": "go",
        "mode": "dry_run",
        "policy_profile": "aspose-email-foss-jmap-go",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1389233108,
            "node_id": "R_kgDOUs4D1A",
        },
    },
    "aspose-email-foss/Aspose.JMAP-FOSS-for-Java": {
        "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Java",
        "family": "jmap",
        "platform": "java",
        "ecosystem": "java",
        "mode": "dry_run",
        "policy_profile": "aspose-email-foss-jmap-java",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1389233642,
            "node_id": "R_kgDOUs4F6g",
        },
    },
    "aspose-email-foss/Aspose.JMAP-FOSS-for-Python": {
        "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Python",
        "family": "jmap",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "aspose-email-foss-jmap-python",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1389232730,
            "node_id": "R_kgDOUs4CWg",
        },
    },
    "aspose-email-foss/Aspose.JMAP-FOSS-for-Rust": {
        "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Rust",
        "family": "jmap",
        "platform": "rust",
        "ecosystem": "rust",
        "mode": "dry_run",
        "policy_profile": "aspose-email-foss-jmap-rust",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1389233264,
            "node_id": "R_kgDOUs4EcA",
        },
    },
}


def _entry(name: str) -> RegistryEntry:
    """The admitted registry entry of the recorded repository (``data/registry.json``), or the
    frozen snapshot above for a repository retired from the registry since this row was recorded."""
    repository = ROWS[name]["repository"]
    registry = json.loads((REPO_ROOT / "data" / "registry.json").read_text("utf-8"))
    raw = next((e for e in registry["entries"] if e["repository"] == repository), None)
    if raw is None:
        raw = _RETIRED_JMAP_ENTRIES[repository]
    return RegistryEntry.model_validate(raw)


def _siblings(name: str) -> list[Fact]:
    row = ROWS[name]
    return [_fact(raw) for raw in (row["package_name_fact"], row["build_command_fact"]) if raw]


def _admit(name: str, install: Fact | None = None, **overrides: Any) -> Fact:
    row = ROWS[name]
    plugin_for(row["ecosystem"])  # registers the ecosystem's spec, as extraction always has
    arguments: dict[str, Any] = {
        "facts": _siblings(name),
        "tree_paths": row["root_paths"],
        "readme_path": "README.md",
        "readme_text": row["readme_installation"],
        "registry_less": row["ecosystem"] == "cpp",
    }
    arguments.update(overrides)
    return documented_source_install(
        install if install is not None else _fact(row["install_fact"]), _entry(name), **arguments
    )


def _go_install_after_the_proxy_answered() -> Fact:
    """JMAP-Go as the facts stage now builds it: the proxy's recorded answer for the module (200,
    an empty version list) read through the façade, then the install verdict it yields."""
    row = ROWS["jmap-go"]
    recorded = _fact(row["install_fact"])
    module = row["package_name_fact"]["value"]

    class _Answer:
        status_code = 200
        body = b""

    reading = observe("go", module, fetch=lambda url, **_: _Answer(), sleep=lambda _s: None)
    polarity, confidence, detail = reading.install_verdict()
    return replace(
        recorded,
        polarity=polarity,
        confidence=confidence,
        evidence=(recorded.evidence[0], Evidence(reading.evidence_url or "", detail)),
    )


# What each recorded repository's own build is, after the clone.
STEPS = {
    "jmap-java": "mvn package",
    "jmap-go": "go build ./...",
    "jmap-cpp": (
        "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release\ncmake --build build --config Release"
    ),
    "jmap-rust": "cargo build",
    "jmap-python": "pip install .",
    "cells-rust": "cargo check --all-targets",
}


@pytest.mark.parametrize("name", sorted(STEPS))
def test_a_package_its_registry_and_its_readme_both_call_unpublished_is_a_documented_checkout(
    name: str,
) -> None:
    """The wave-6 BC-02 rows: the registry reads 404 / not found / no registry, the maintainers'
    README says "not published", and the repository documents its build. The install is the
    clone plus that build - SUPPORTED as a source checkout, and never a registry command."""
    install = _go_install_after_the_proxy_answered() if name == "jmap-go" else None
    admitted = _admit(name, install)
    row = ROWS[name]
    repository = row["repository"]
    prefix = f"git clone https://github.com/{repository}.git\ncd {repository.split('/')[1]}\n"
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == prefix + STEPS[name]
    attributes = admitted.attributes or {}
    assert attributes["install_kind"] == "source_checkout"
    assert attributes[REGISTRY_STATE_ATTRIBUTE] == NOT_PUBLISHED
    assert attributes[SOURCE_BASIS_ATTRIBUTE] == "documented"
    assert attributes[DOCUMENTED_COMMAND_ATTRIBUTE] == STEPS[name]
    # The optional "work from a checkout" record belonged to the registry-kind fact it replaced.
    assert "source_checkout_unverified" not in attributes
    assert "source_checkout_command" not in attributes
    details = [e.detail or "" for e in admitted.evidence]
    assert any(d.startswith(README_STATEMENT_PHRASE) for d in details)
    assert any(d.startswith(DOCUMENTED_BUILD_PHRASE) for d in details)
    # The registry reading stays on the fact: unpublished is two sources agreeing, not a guess.
    assert fact_registry_reading(replace(admitted, evidence=admitted.evidence[:-2])) in (
        "not_published",
        "no_registry",
    )
    command = _fact(row["install_fact"]).value
    if row["ecosystem"] == "cpp":
        # C++ has no registry: the original value already was a source build, nothing to forbid.
        assert REGISTRY_COMMAND_ATTRIBUTE not in attributes
    else:
        assert attributes[REGISTRY_COMMAND_ATTRIBUTE] == command
        assert command not in admitted.value


def test_the_go_proxys_empty_version_list_is_the_registrys_answer_not_a_failed_read() -> None:
    """JMAP-Go: proxy.golang.org answers `@v/list` 200 with an empty body (no tag). As recorded
    the fact read "go_modules could not be read" - a transient class that sent a retry at a
    question already answered. Corrected, it is CONTRADICTED (not published), which the README's
    own "No versioned tag has been published yet" corroborates."""
    recorded = _fact(ROWS["jmap-go"]["install_fact"])
    assert fact_registry_reading(recorded) == "unreadable"
    assert _admit("jmap-go", recorded) is recorded, "an unreadable registry admits nothing"
    corrected = _go_install_after_the_proxy_answered()
    assert corrected.polarity == "CONTRADICTED"
    assert fact_registry_reading(corrected) == "not_published"
    assert _admit("jmap-go", corrected).polarity == "SUPPORTED"


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("3d-python", "the name is held by another project; the README says it is published"),
        ("page-python", "the registry lists no source repository to compare; README: published"),
        (
            "pdf-cpp",
            "no registry, but the README documents a NuGet package, not an unpublished one",
        ),
        ("gis-net", "the repository has no README to corroborate the registry's 404"),
    ],
)
def test_a_row_the_registry_or_the_readme_does_not_show_unpublished_stays_refused(
    name: str, why: str
) -> None:
    row = ROWS[name]
    install = _fact(row["install_fact"])
    assert _admit(name) == install, why
    assert install.polarity != "SUPPORTED"


def test_a_registry_that_could_not_be_read_never_becomes_an_unpublished_package() -> None:
    """A network or TLS failure says nothing about the package: even with a README that says
    "not published" and a documented build, the fact stays UNRESOLVED so the extraction is read
    again, and it is classified as a retry, never as an absent package."""
    install = _fact(ROWS["jmap-java"]["install_fact"])
    for detail in (
        "package registry: maven could not be read",
        "package registry: maven answered ambiguously",
        "package registry unreachable: ConnectError",
    ):
        unread = replace(
            install,
            polarity="UNRESOLVED",
            evidence=(install.evidence[0], Evidence("https://repo1.maven.org/x", detail)),
        )
        assert fact_registry_reading(unread) in ("unreadable", "ambiguous")
        assert _admit("jmap-java", unread) is unread


def test_the_registry_must_say_not_published_for_a_registry_having_ecosystem() -> None:
    """A registry-having ecosystem's UNRESOLVED (e.g. the registry-less sentence) and a found
    package are not "not published": only the registry's own "distribution not found" admits."""
    install = _fact(ROWS["jmap-java"]["install_fact"])
    found = replace(
        install,
        polarity="SUPPORTED",
        evidence=(install.evidence[0], Evidence("https://x", "package registry: found on maven")),
    )
    assert _admit("jmap-java", found) is found
    # "package registry: none could not be read" is the registry-LESS reading; a registry-having
    # ecosystem reporting it is a defect upstream of this tier, never an admission.
    odd = replace(
        install,
        polarity="UNRESOLVED",
        evidence=(
            install.evidence[0],
            Evidence("no package registry", "package registry: none could not be read"),
        ),
    )
    assert _admit("jmap-java", odd, registry_less=False) is odd


def test_a_repository_that_documents_no_build_admits_nothing() -> None:
    """The command is the repository's own: its build-command fact, else the ecosystem's standard
    command where the checkout root holds the manifest it starts from. With neither, the install
    stays refused rather than inventing a step."""
    install = _fact(ROWS["jmap-python"]["install_fact"])
    assert _admit("jmap-python", install, tree_paths=[".gitignore", "README.md"]) is install
    # With the manifest at the root the ecosystem's standard command is stated, and says so.
    admitted = _admit("jmap-python", install)
    assert (admitted.attributes or {})[DOCUMENTED_COMMAND_ATTRIBUTE] == "pip install ."
    assert any("standard command" in (e.detail or "") for e in admitted.evidence)
    # A SUPPORTED build-command fact outranks the template; a refused (CONTRADICTED) one does not.
    spec = spec_for("python")
    build = Fact(
        "build_test_asset:build-command",
        "build_test_asset",
        "python -m build",
        (Evidence(".github/workflows/ci.yml", "build command; job build runs `python -m build`"),),
        attributes={
            "role": "build command",
            "source": "ci workflow",
            "precondition": "pip install build",
        },
    )
    steps = documented_steps(spec, [build], ["pyproject.toml"])
    assert steps is not None and steps[0] == "pip install build\npython -m build"
    refused = replace(build, polarity="CONTRADICTED")
    fallback = documented_steps(spec, [refused], ["pyproject.toml"])
    assert fallback is not None and fallback[0] == "pip install ."


def test_an_npm_build_read_from_package_json_is_preceded_by_the_dependency_install() -> None:
    """`npm run build` fails on a fresh clone until `npm install` has run, and the build-command
    fact is read from the repository's own files, not measured: the documented checkout states the
    step the toolchain needs first. Cargo, Go and Maven fetch inside their build and add nothing."""
    build = Fact(
        "build_test_asset:build-command",
        "build_test_asset",
        "npm run build",
        (Evidence("package.json", "build command; script build is declared"),),
        attributes={"role": "build command", "source": "package.json script"},
    )
    for ecosystem in ("typescript", "nodejs"):
        plugin_for(ecosystem)
        steps = documented_steps(spec_for(ecosystem), [build], ["package.json"])
        assert steps is not None and steps[0] == "npm install\nnpm run build", ecosystem
    # A command that already is the install step is not doubled.
    steps = documented_steps(spec_for("typescript"), [replace(build, value="npm install")], [])
    assert steps is not None and steps[0] == "npm install"
    plugin_for("rust")
    cargo = replace(build, value="cargo build")
    steps = documented_steps(spec_for("rust"), [cargo], ["Cargo.toml"])
    assert steps is not None and steps[0] == "cargo build"


def test_a_fact_that_is_already_a_source_install_is_left_alone() -> None:
    """A measured or receipt-proven build (extract._source_build_fact) is the stronger proof and
    was admitted first; this tier never rewrites it."""
    install = _fact(ROWS["jmap-rust"]["install_fact"])
    measured = replace(
        install,
        polarity="SUPPORTED",
        attributes={"install_kind": "source", "build_command": "cargo build"},
    )
    assert _admit("jmap-rust", measured) is measured


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("jmap-java", "No artifact has been published to Maven Central yet"),
        ("jmap-go", "No versioned tag has been published yet"),
        ("jmap-cpp", "No package has been published to a registry."),
        ("jmap-rust", "No version has been published to crates.io yet"),
        ("jmap-python", "No package has been published to PyPI yet"),
        ("cells-rust", "Aspose.Cells FOSS for Rust is not yet published to crates.io"),
    ],
)
def test_the_maintainers_statements_are_recognised_as_the_recorded_readmes_spell_them(
    name: str, expected: str
) -> None:
    statement = unpublished_statement(ROWS[name]["readme_installation"])
    assert statement is not None and expected in statement


@pytest.mark.parametrize(
    "readme",
    [
        "Install the published package from PyPI (`aspose-3d-foss`, version 26.1.0).",
        "```text\nNo package has been published to PyPI yet.\n```",
        "The release process is documented in docs/releasing.md and a feature is not yet released.",
        "",
    ],
)
def test_a_readme_that_does_not_say_the_package_is_unpublished_has_no_statement(
    readme: str,
) -> None:
    assert unpublished_statement(readme) is None


def test_a_statement_wrapped_over_two_lines_is_one_sentence() -> None:
    assert (
        unpublished_statement("No package has been\npublished to PyPI yet; build from source.")
        == "No package has been published to PyPI yet; build from source."
    )


# --- end to end through extract_facts, on a real local clone -----------------------------------


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


def _unpublished_source(tmp_path: Path, readme: str) -> Path:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text(readme, encoding="utf-8")
    (source / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    (source / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="aspose-example", version="0.1.0",'
        ' python_requires=">=3.8")\n',
        encoding="utf-8",
    )
    (source / "aspose" / "example").mkdir(parents=True)
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (source / "aspose" / "example" / "__init__.py").write_text("VERSION = '0.1.0'\n", "utf-8")
    commit_all(source, "seed")
    return source


def _extracted_install(tmp_path: Path, readme: str) -> Fact:
    source = _unpublished_source(tmp_path, readme)
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    plugin = plugin_for(ENTRY.ecosystem)
    document, _ = extract_facts(
        ENTRY,
        snapshot,
        clone.path,
        list_tree_paths(clone.path),
        plugin,
        plugin.detect_manifest(clone.path),
    )
    return next(f for f in document.facts if f.id == "install_command:pip")


def test_extraction_states_a_404_package_the_readme_calls_unpublished_as_a_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={"message": "Not Found"}),
    )
    install = _extracted_install(
        tmp_path,
        "# Example\n\n## Installation\n\nNo package has been published to PyPI yet; until it is, "
        "build the library from source.\n\n```bash\npip install aspose-example\n```\n",
    )
    assert install.polarity == "SUPPORTED"
    assert (install.attributes or {})["install_kind"] == "source_checkout"
    assert (install.attributes or {})[REGISTRY_COMMAND_ATTRIBUTE] == "pip install aspose-example"
    assert install.value.endswith("\npip install .")
    assert "pip install aspose-example" not in install.value


def test_extraction_keeps_a_package_the_readme_calls_published_refused_when_the_registry_404s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The registry and the maintainers disagree: nothing is decided, BC-02 keeps refusing."""
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={"message": "Not Found"}),
    )
    install = _extracted_install(
        tmp_path,
        "# Example\n\n## Installation\n\nInstall the package from PyPI:\n\n```bash\n"
        "pip install aspose-example\n```\n",
    )
    assert install.polarity == "CONTRADICTED"
    assert "install_kind" not in (install.attributes or {})


def test_extraction_never_turns_a_registry_outage_into_an_unpublished_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A TLS or connection failure beside a README that says "not published": the fact stays
    UNRESOLVED (a retry), and is not rewritten as a source install on the strength of a network
    error."""

    def _down(url: str, transport: Any = None) -> httpx.Response:
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED]")

    monkeypatch.setattr(python_registry, "fetch_project_json", _down)
    monkeypatch.setattr(python_registry.time, "sleep", lambda _s: None)
    install = _extracted_install(
        tmp_path,
        "# Example\n\n## Installation\n\nNo package has been published to PyPI yet.\n",
    )
    assert install.polarity == "UNRESOLVED"
    assert fact_registry_reading(install) == "unreadable"
    assert "install_kind" not in (install.attributes or {})
