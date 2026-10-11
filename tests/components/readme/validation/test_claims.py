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
    assert (check.version, check.judged_at) == ("2", "S9")


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


# --- a distribution the repository's own README names, confirmed by a registry (CUT-2) ---------
CELLS_CPP_INSTALL = (
    "## Installation\n\n```bash\nnuget install Aspose.Cells.Cpp.FOSS\n```\n\n"
    "Or build from source with CMake.\n"
)


def _cells_cpp(polarity: str) -> FactsDocument:
    """Aspose.Cells for C++: the CMake `project()` is `aspose_cells_foss_cpp`; the README names
    the NuGet package `Aspose.Cells.Cpp.FOSS`, which NuGet lists with this repository's URL."""
    return _facts(
        _fact("package:name", "package", "aspose_cells_foss_cpp"),
        _fact(
            "package:distribution.aspose-cells-cpp-foss",
            "package",
            "Aspose.Cells.Cpp.FOSS",
            "NuGet package the repository's own README names",
            polarity=polarity,
            attributes={"registry": "nuget"},
        ),
    )


def test_an_install_naming_a_registry_confirmed_distribution_is_not_a_near_miss() -> None:
    """The BC-14 failure `the install command names 'Aspose.Cells.Cpp.FOSS', but the package
    identity is 'aspose_cells_foss_cpp'`: both names are facts, from the same README, and the
    second was confirmed by NuGet - so the install command is consistent with the facts."""
    assert claim_findings(CELLS_CPP_INSTALL, _cells_cpp("SUPPORTED")) == []


def test_an_unconfirmed_distribution_does_not_excuse_the_near_miss() -> None:
    """Negative control: BC-14 is not loosened. A name NuGet did not confirm as this
    repository's (UNRESOLVED) or said does not exist (CONTRADICTED) is still a near-miss."""
    for polarity in ("UNRESOLVED", "CONTRADICTED"):
        [finding] = claim_findings(CELLS_CPP_INSTALL, _cells_cpp(polarity))
        assert "Aspose.Cells.Cpp.FOSS" in finding.detail
        assert "aspose_cells_foss_cpp" in finding.detail
    # And a different package that merely resembles the project is still refused.
    other = CELLS_CPP_INSTALL.replace("Aspose.Cells.Cpp.FOSS", "Aspose.Cells.Cpp")
    assert claim_findings(other, _cells_cpp("SUPPORTED"))


SLIDES_CPP_NOT_PUBLISHED = (
    "## Installation\n\n`AsposeSlidesFoss` is not yet published on any package registry; build it "
    "from a source checkout instead, verified against this revision:\n"
)
CPP_PUBLISHED = "## Installation\n\nThe library is published on NuGet as `Aspose.Cells.Cpp.FOSS`.\n"


def test_a_confirmed_distribution_is_a_positive_registry_reading() -> None:
    """Slides-Cpp, wave 3: the Installation section said "not yet published on any package
    registry" beside a NuGet package NuGet lists (the independent review's F01). A distribution a
    registry confirmed as this repository's own is a reading that the package is published, so a
    sentence denying it is flagged exactly as one beside `package:published_version` is."""
    [finding] = claim_findings(SLIDES_CPP_NOT_PUBLISHED, _cells_cpp("SUPPORTED"))
    assert finding.stage == "COMPOSING" and "not published" in finding.detail
    # What the renderer now writes of such a library is not a denial.
    assert claim_findings(CPP_PUBLISHED, _cells_cpp("SUPPORTED")) == []


def test_an_unconfirmed_distribution_is_no_reading_so_the_denial_is_not_judged() -> None:
    """Negative control: the check flags only against a reading. A name NuGet did not confirm
    (UNRESOLVED) or said does not exist (CONTRADICTED) leaves nothing to hold the sentence to."""
    for polarity in ("UNRESOLVED", "CONTRADICTED"):
        assert claim_findings(SLIDES_CPP_NOT_PUBLISHED, _cells_cpp(polarity)) == []


# --- Cells-Java: "the sole published version" while the registry lists two ---------------------
CELLS_JAVA_README = (
    "# Aspose.Cells FOSS for Java\n\n## API Reference\n\n"
    "Aspose.Cells FOSS for Java provides a public API under the `org.aspose.cells_foss` package. "
    "The package `org.aspose:aspose-cells-foss` version 26.7.0 targets Java 17 and is the sole "
    "published version.\n"
)
CELLS_JAVA = (_fact("package:name", "package", "org.aspose:aspose-cells-foss"),)


def _published(count: str | None) -> Fact:
    return _fact(
        "package:published_version",
        "package",
        "26.7.0",
        "current stable release",
        attributes={"registry": "maven", **({"version_count": count} if count else {})},
    )


def test_sole_published_version_fails_when_the_registry_lists_more_than_one() -> None:
    [finding] = claim_findings(CELLS_JAVA_README, _facts(*CELLS_JAVA, _published("2")))
    assert finding.stage == "COMPOSING"
    assert "sole published version" in finding.detail
    assert "the registry lists 2 versions" in finding.detail
    assert finding.line == 4


def test_sole_published_version_is_unverifiable_without_a_version_count() -> None:
    [finding] = claim_findings(CELLS_JAVA_README, _facts(*CELLS_JAVA, _published(None)))
    assert "no registry reading lists every published version" in finding.detail


def test_sole_published_version_passes_when_the_registry_lists_exactly_one() -> None:
    assert claim_findings(CELLS_JAVA_README, _facts(*CELLS_JAVA, _published("1"))) == []


def test_exclusivity_is_judged_only_against_a_registry_reading() -> None:
    # Unpublished or unreadable: there is no reading to contradict, as for rule (b).
    assert claim_findings(CELLS_JAVA_README, _facts(*CELLS_JAVA)) == []


@pytest.mark.parametrize(
    "sentence",
    [
        "This is the only published version of the package.",
        "Version 26.5.0 was the first published release on Maven Central.",
        "The initial release on PyPI is 26.5.0.",
        "There are no other versions of the package on NuGet.",
        "26.7.0 is the only version available in the registry.",
    ],
)
def test_every_phrasing_of_exclusivity_about_the_published_version_is_held_to_the_count(
    sentence: str,
) -> None:
    facts = _facts(*CELLS_JAVA, _published("2"))
    assert len(claim_findings(f"{sentence}\n", facts)) == 1


@pytest.mark.parametrize(
    "sentence",
    [
        "Java 17 is the only supported version of the runtime.",
        "Only the latest published version receives fixes.",
        "The first release of the roadmap adds charts.",
        "Install the published version from Maven Central.",
        "This is the only package published by the project.",
    ],
)
def test_ordinary_sentences_that_merely_use_the_words_are_left_alone(sentence: str) -> None:
    assert claim_findings(f"{sentence}\n", _facts(*CELLS_JAVA, _published("2"))) == []


def test_the_registry_judge_routes_the_exclusivity_finding_to_its_section() -> None:
    candidate: Any = SimpleNamespace(
        readme=CELLS_JAVA_README, facts=_facts(*CELLS_JAVA, _published("2"))
    )
    [failure] = _check_claims(candidate)
    assert failure.stage == "COMPOSING" and failure.section == "api_reference"


# --- rule (e): the licence is stated once, by the licence fact (wave-3 acceptance, Note-Python) ---
LICENSE_FACTS = (
    _fact("package:name", "package", "aspose-note-foss"),
    _fact("license:spdx", "license", "MIT", "license text states this license"),
)


def test_a_scope_sentence_naming_a_license_reference_beside_an_mit_license_is_flagged() -> None:
    readme = (
        "# Aspose.Note FOSS\n\nIt supports Python 3.10 and later, and is distributed under the "
        "LicenseRef-Aspose-Split license.\n\n## License\n\n"
        "This project is licensed under the [MIT License](LICENSE).\n"
    )
    [finding] = claim_findings(readme, _facts(*LICENSE_FACTS))
    assert finding.stage == "COMPOSING" and finding.line == 2
    assert "LicenseRef-Aspose-Split" in finding.detail and "states MIT" in finding.detail


def test_a_different_recognised_license_is_flagged_and_the_facts_own_is_not() -> None:
    other = "The package is released under the Apache License 2.0 terms.\n"
    assert claim_findings(other, _facts(*LICENSE_FACTS)) == []  # not classifiable: left alone
    different = "The project is licensed under the BSD 3-Clause license.\n"
    [finding] = claim_findings(different, _facts(*LICENSE_FACTS))
    assert "BSD-3-Clause" in finding.detail
    same = "The project is distributed under the MIT license.\n"
    assert claim_findings(same, _facts(*LICENSE_FACTS)) == []


def test_the_license_rule_is_silent_without_a_supported_license_fact_or_inside_a_fence() -> None:
    readme = "Distributed under the LicenseRef-Aspose-Split license.\n"
    assert claim_findings(readme, _facts(LICENSE_FACTS[0])) == []
    unclassified = _fact("license:spdx", "license", "UNCLASSIFIED", polarity="UNRESOLVED")
    assert claim_findings(readme, _facts(LICENSE_FACTS[0], unclassified)) == []
    fenced = "```text\nLicenseRef-Aspose-Split\n```\n"
    assert claim_findings(fenced, _facts(*LICENSE_FACTS)) == []


def test_a_sentence_about_a_dependencys_or_fonts_license_is_not_the_projects_statement() -> None:
    readme = "The optional PDF dependency is distributed under the BSD 3-Clause license.\n"
    assert claim_findings(readme, _facts(*LICENSE_FACTS)) == []
