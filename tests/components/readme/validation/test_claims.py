"""BC-14 (TC-CLM-01, G3-W08): version, install-package, and publication statements are held to
the facts. The failing fixtures are the strings four reviewers found in sealed READMEs."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from repository_presenter.components.readme.validation.claims import claim_findings, claim_notes
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    _check_claims,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REVISION = "a" * 40


def _fact(
    fact_id: str,
    kind: str,
    value: str,
    *details: str,
    polarity: str = "SUPPORTED",
    attributes: dict[str, str] | None = None,
) -> Fact:
    evidence = tuple(Evidence("pom.xml", detail) for detail in details) or (Evidence("pom.xml"),)
    return Fact(fact_id, kind, value, evidence, polarity=polarity, attributes=attributes)  # type: ignore[arg-type]


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument("org/repo", REVISION, facts)


# --- Slides-Java: the install version Maven Central does not list -----------------------------
JAVA_INSTALL = "mvn dependency:get -Dartifact=org.aspose:aspose-slides-foss:26.8.0"
JAVA = (
    _fact("package:name", "package", "org.aspose:aspose-slides-foss"),
    _fact("package:version", "package", "26.8.0"),
    _fact(
        "install_command:maven",
        "install_command",
        JAVA_INSTALL,
        "install command for the coordinate the `pom.xml` manifest declares",
        "package registry: found on maven",
    ),
)
PUBLISHED_267 = _fact("package:published_version", "package", "26.7.0", "current stable release")
SLIDES_JAVA_README = f"""# Aspose.Slides FOSS for Java

The library is published as `org.aspose:aspose-slides-foss` version 26.8.0, targets Java 21.

## Installation

Install the published package from Maven Central:

```bash
{JAVA_INSTALL}
```
"""


def test_slides_java_version_the_registry_does_not_list_fails() -> None:
    findings = claim_findings(SLIDES_JAVA_README, _facts(*JAVA, PUBLISHED_267))
    assert len(findings) == 2
    prose, command = sorted(findings, key=lambda f: f.line)
    assert "26.8.0" in prose.detail and "26.7.0" in prose.detail
    # The prose repeats a version the install fact itself carries, so the defect is extraction's.
    assert prose.stage == command.stage == "EXTRACTING"
    assert command.line == SLIDES_JAVA_README.splitlines().index(JAVA_INSTALL)


def test_the_published_release_passes_and_so_does_the_manifest_without_a_registry_reading() -> None:
    fixed = SLIDES_JAVA_README.replace("26.8.0", "26.7.0")
    assert claim_findings(fixed, _facts(*JAVA, PUBLISHED_267)) == []
    # Registry unreachable: no published fact, the manifest version stands, a pending note says so.
    unread = _facts(*JAVA)
    assert claim_findings(SLIDES_JAVA_README, unread) == []
    [note] = claim_notes(SLIDES_JAVA_README, unread)
    assert "BC-14 pending" in note and "package:published_version" in note
    assert claim_notes(SLIDES_JAVA_README, _facts(*JAVA, PUBLISHED_267)) == []


def test_a_readme_stating_no_version_has_nothing_to_judge_and_no_note() -> None:
    bare = (
        "## Installation\n\n```bash\n"
        "mvn dependency:get -Dartifact=org.aspose:aspose-slides-foss\n```\n"
    )
    assert claim_findings(bare, _facts(*JAVA, PUBLISHED_267)) == []
    assert claim_notes(bare, _facts(*JAVA)) == []


# --- PDF-.NET: a stale version ----------------------------------------------------------------
NET = (
    _fact("package:name", "package", "Aspose.PDF.FOSS"),
    _fact("package:version", "package", "26.9.0"),
    _fact("package:published_version", "package", "26.10.0", "current stable release"),
)


@pytest.mark.parametrize(
    "line",
    [
        "dotnet add package Aspose.PDF.FOSS --version 26.9.0",
        '<PackageReference Include="Aspose.PDF.FOSS" Version="26.9.0" />',
        "The package `Aspose.PDF.FOSS` version 26.9.0 targets net10.0.",
    ],
)
def test_pdf_dotnet_stale_version_fails_in_every_shape(line: str) -> None:
    [finding] = claim_findings(f"## Installation\n\n```bash\n{line}\n```\n", _facts(*NET))
    assert "26.10.0" in finding.detail and finding.stage == "COMPOSING"


def test_pdf_dotnet_current_version_and_unrelated_numbers_pass() -> None:
    readme = (
        "## Installation\n\n```bash\ndotnet add package Aspose.PDF.FOSS --version 26.10.0\n```\n\n"
        "Requires .NET 10.0 and PDF 1.7. Aspose.PDF.FOSS reads files from 2024.\n"
    )
    assert claim_findings(readme, _facts(*NET)) == []


def test_other_version_syntaxes_are_held_to_the_same_release() -> None:
    facts = _facts(
        _fact("package:name", "package", "aspose-pdf-foss"),
        _fact("package:published_version", "package", "26.9.0", "current stable release"),
    )
    stale = [
        "pip install aspose-pdf-foss==26.8.0",
        "npm install aspose-pdf-foss@26.8.0",
        'aspose-pdf-foss = "26.8.0"',
        "<artifactId>aspose-pdf-foss</artifactId>\n<version>26.8.0</version>",
    ]
    for snippet in stale:
        assert len(claim_findings(f"```text\n{snippet}\n```\n", facts)) == 1, snippet
    assert claim_findings("```bash\npip install aspose-pdf-foss==26.9.0\n```\n", facts) == []
    assert claim_findings("```bash\npip install aspose-pdf-foss==v26.9.0\n```\n", facts) == []


# --- Note-Python: a renamed package ----------------------------------------------------------
NOTE = (
    _fact("package:name", "package", "aspose-note-foss"),
    _fact("package:version", "package", "26.1.0"),
    _fact("dependency:requests", "dependency", "requests>=2.0"),
)


def test_note_python_old_package_name_in_an_install_command_fails() -> None:
    readme = "## Installation\n\n```bash\npip install aspose-note\n```\n"
    [finding] = claim_findings(readme, _facts(*NOTE))
    assert "aspose-note" in finding.detail and "aspose-note-foss" in finding.detail
    assert finding.stage == "COMPOSING" and finding.line == 3


def test_the_identity_unrelated_packages_dependencies_and_local_installs_pass() -> None:
    readme = """## Installation

```bash
pip install aspose-note-foss
pip install Aspose_Note.FOSS==26.1.0
pip install requests
pip install pytest pytest-cov
pip install -r requirements.txt
pip install -e .[dev]
pip install --index-url https://example.com/simple aspose-note-foss
```
"""
    assert claim_findings(readme, _facts(*NOTE)) == []


def test_an_install_line_in_prose_rather_than_a_fence_is_not_an_install_command() -> None:
    assert claim_findings("Older docs said pip install aspose-note.\n", _facts(*NOTE)) == []


# --- Cells-Cpp: "not published" against a registry that lists the package ---------------------
CPP_README = (
    "## Installation\n\n"
    "`aspose_cells_foss_cpp` is not yet published on any package registry; build it from a "
    "source checkout instead.\n"
)


def _cpp(*install_details: str, attributes: dict[str, str] | None = None) -> FactsDocument:
    return _facts(
        _fact("package:name", "package", "aspose_cells_foss_cpp"),
        _fact(
            "install_command:nuget",
            "install_command",
            "dotnet add package Aspose.Cells.Cpp.FOSS",
            *install_details,
            attributes=attributes,
        ),
    )


def test_cells_cpp_not_published_fails_when_a_registry_reading_lists_the_package() -> None:
    [finding] = claim_findings(CPP_README, _cpp("package registry: found on nuget"))
    assert finding.stage == "COMPOSING" and finding.line == 2
    assert "not published" in finding.detail
    # The core observer's wording is read the same way.
    assert claim_findings(CPP_README, _cpp("package registry: found; manifest version published"))


def test_not_published_passes_when_the_observation_agrees_or_there_is_none() -> None:
    assert claim_findings(CPP_README, _cpp("package registry: distribution not found")) == []
    # No registry for the ecosystem (C++ today): nothing contradicts the statement.
    assert claim_findings(CPP_README, _cpp("package registry: none could not be read")) == []
    source = _cpp("package registry: found on nuget", attributes={"install_kind": "source"})
    assert claim_findings(CPP_README, source) == []
    # The manifest's own version is unreleased although the distribution exists: not contradicted.
    unreleased = _cpp("package registry: found; manifest version not published")
    assert claim_findings(CPP_README, unreleased) == []


def test_a_not_published_sentence_about_something_else_is_left_alone() -> None:
    readme = "ARM64 wheels are not published for Linux yet.\n"
    assert claim_findings(readme, _cpp("package registry: found on nuget")) == []


# --- the check as the validator runs it -------------------------------------------------------
def test_bc14_is_a_registered_blocking_check_judged_at_s9() -> None:
    check = next(c for c in BLOCKING_CHECKS if c.id == "BC-14")
    assert (check.version, check.judged_at) == ("1", "S9")


def test_the_registry_judge_routes_each_finding_to_its_section_and_stage() -> None:
    candidate: Any = SimpleNamespace(readme=SLIDES_JAVA_README, facts=_facts(*JAVA, PUBLISHED_267))
    failures = _check_claims(candidate)
    assert {f.stage for f in failures} == {"EXTRACTING"}
    assert [f.section for f in failures] == [None, "installation"]  # the opening has no heading
    clean: Any = SimpleNamespace(
        readme=SLIDES_JAVA_README.replace("26.8.0", "26.7.0"), facts=_facts(*JAVA, PUBLISHED_267)
    )
    assert _check_claims(clean) == []


def test_a_readme_with_no_package_identity_fact_is_not_judged() -> None:
    assert claim_findings(SLIDES_JAVA_README, _facts()) == []
