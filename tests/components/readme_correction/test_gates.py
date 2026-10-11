"""The review's universal defects as gates: contents list, narration, redundancy, contradiction."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.apply import apply_edits
from repository_presenter.components.readme_correction.detectors.examples import failing_example
from repository_presenter.components.readme_correction.detectors.links import broken_link
from repository_presenter.components.readme_correction.detectors.sections import missing_sections
from repository_presenter.components.readme_correction.detectors.stale import (
    stale_phrase,
    unpublished_install_command,
)
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.text_gate import clean, narration

WORDS = "aspose-words-foss/Aspose.Words-FOSS-for-Python"
NAV_README = (
    "# P\n\n## Navigation\n\n- [Installation](#installation)\n- [Scope and Limitations]"
    "(#scope-and-limitations)\n- [License](#license)\n\n## Installation\n\n```bash\n"
    "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n\n"
    "## Scope and Limitations\n\nOnly the happy path.\n\n## License\n\nMIT.\n"
)


def corrected(readme: str, edits: Any) -> str:
    ordered = sorted(edits, key=lambda e: (e.start, e.order))
    return apply_edits(readme, ordered)[0]


# ------------------------------------------------------------------------------- contents list
def test_an_inserted_section_gets_its_contents_item_in_document_order(make_context: Any) -> None:
    ctx = make_context(NAV_README)
    result = missing_sections(ctx)
    text = corrected(NAV_README, result.edits)
    nav = text.split("## Installation")[0]
    assert "- [Installation](#installation)\n- [Dependencies](#dependencies)\n- [Scope" in nav
    assert text.index("## Dependencies") < text.index("## Scope and Limitations")
    items = [e for e in result.edits if e.kind == "MISSING_INFO"]
    assert items and all(e.locators[0].startswith("README.md:") for e in items)


def test_a_section_appended_at_the_end_gets_its_item_after_the_last_preceding_one(
    make_context: Any,
) -> None:
    readme = (
        "# P\n\n## Navigation\n\n- [Installation](#installation)\n- [Quick Start](#quick-start)\n"
        "- [Scope and Limitations](#scope-and-limitations)\n\n## Installation\n\n```bash\n"
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n\n"
        "## Quick Start\n\nRun it.\n\n## Scope and Limitations\n\nOnly the happy path.\n"
    )
    result = missing_sections(make_context(readme))
    text = corrected(readme, result.edits)
    nav = text.split("## Installation")[0]
    tail = "(#scope-and-limitations)\n- [Development and Testing](#development-and-testing)\n"
    assert tail + "- [License](#license)\n" in nav
    assert text.rstrip().endswith("The software is provided without warranty.")


def test_a_navigation_this_path_cannot_extend_blocks_the_insertion_and_says_so(
    make_context: Any,
) -> None:
    readme = "# P\n\n## Navigation\n\nSee below.\n\n## Installation\n\nx\n\n## License\n\nMIT.\n"
    result = missing_sections(make_context(readme))
    assert not any("Dependencies" in e.replacement for e in result.edits)
    assert any("contents list cannot be extended safely" in f.reason for f in result.findings)


def test_a_readme_without_a_contents_list_gets_no_contents_item(make_context: Any) -> None:
    readme = "# P\n\n## Installation\n\nx\n\n## License\n\nMIT.\n"
    edits = missing_sections(make_context(readme)).edits
    assert edits and all(e.kind == "MISSING_SECTION" for e in edits)


# -------------------------------------------------------------------------------- narration
def test_renderer_evidence_phrasing_is_cleaned_and_assurance_vocabulary_is_blocked() -> None:
    assert clean("build it from a source checkout instead, verified against this revision:") == (
        "build it from a source checkout instead:"
    )
    assert (
        clean(
            "No required third-party package dependencies; in `pyproject.toml`, no "
            "`project.dependencies` is declared."
        )
        == "No required third-party package dependencies."
    )
    floor = '- Requires Python 3.10 or later (`python_requires=">=3.10"` in `pyproject.toml`).'
    assert clean(floor) == "- Requires Python 3.10 or later."
    assert "this revision" in narration("verified against this revision")
    assert narration("Install it with `pip install x`.") == []


def test_an_edit_whose_text_still_narrates_is_dropped_with_its_contents_item(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("dependency:odd", "network policy 1.0", evidence=(("pom.xml", None),)),
        drop=["dependency:none"],
    )
    result = correct(make_context(NAV_README, facts))
    assert "## Dependencies" not in result.corrected
    assert "(#dependencies)" not in result.corrected  # the contents item went with its section
    assert any("internal narration" in f.reason for f in result.findings)


def test_words_the_replaced_text_already_held_are_the_maintainers_own_not_narration(
    make_context: Any,
) -> None:
    from repository_presenter.components.readme_correction.engine import _without_narration
    from repository_presenter.components.readme_correction.model import DIAGRAM_FIX, Edit

    nl = chr(10)
    label = "Checks run against this revision"
    readme = nl.join(["# P", "", "```mermaid", "flowchart TD", f"  a['{label}']", "```", ""])
    start = readme.index("flowchart")
    end = readme.index("```" + nl, start)
    body = readme[start:end]
    kept = Edit(
        kind=DIAGRAM_FIX,
        detector="at_a_glance_diagram",
        start=start,
        end=end,
        original=body,
        replacement=body.replace("flowchart TD", "flowchart LR"),
        fact_ids=(),
        locators=("README.md:4",),
        rationale="redrawn",
    )
    assert narration(kept.replacement)  # the maintainers' label does match a narration pattern
    findings: list[Any] = []
    assert _without_narration(make_context(readme), [kept], findings) == [kept]
    assert findings == []
    fresh = Edit(
        kind=DIAGRAM_FIX,
        detector="at_a_glance_diagram",
        start=start,
        end=end,
        original=body,
        replacement=body.replace(label, label + " and evidence"),
        fact_ids=(),
        locators=("README.md:4",),
        rationale="redrawn",
    )
    assert _without_narration(make_context(readme), [fresh], findings) == []
    assert findings and "internal narration" in findings[0].reason


# --------------------------------------------------------------------------------- redundancy
def test_dependencies_the_readme_already_names_elsewhere_are_not_repeated(
    make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact("package:name", "aspose-words-foss", evidence=(("pyproject.toml", None),)),
        make_fact("dependency:olefile-0.46", "olefile>=0.46", evidence=(("pyproject.toml", None),)),
    ]
    readme = (
        "# P\n\n## Installation\n\nInstall with pip; needs olefile>=0.46.\n\n## License\n\nMIT.\n"
    )
    result = missing_sections(make_context(readme, facts, repository=WORDS))
    assert not any("## Dependencies" in e.replacement for e in result.edits)
    assert any("already names 'olefile'" in f.reason for f in result.findings)


# --------------------------------------------------------------------------- contradictions
def unpublished_facts(make_fact: Any) -> list[Any]:
    return [
        make_fact("package:name", "aspose-font", evidence=(("pyproject.toml", None),)),
        make_fact(
            "install_command:pip",
            "git clone https://example/x.git\ncd x\npip install .",
            attributes={"install_kind": "source"},
            evidence=(
                ("pyproject.toml", "distribution name declared by the manifest"),
                (
                    "https://pypi.org/pypi/aspose-font/json",
                    "package registry: distribution not found",
                ),
            ),
        ),
    ]


UNPUBLISHED_README = (
    '# P\n\n## Usage\n\n```bash\npip install "aspose-font[mcp]"\n```\n\n## License\n\nMIT.\n'
)


def test_an_install_command_for_a_package_the_registry_lacks_is_reported_with_its_evidence(
    make_context: Any, make_fact: Any
) -> None:
    ctx = make_context(UNPUBLISHED_README, unpublished_facts(make_fact), repository=WORDS)
    result = unpublished_install_command(ctx)
    (finding,) = result.findings
    assert result.edits == () and finding.line == 6
    assert "distribution not found" in finding.reason and "aspose-font" in finding.reason


def test_no_not_yet_published_installation_is_inserted_beside_the_command_it_contradicts(
    make_context: Any, make_fact: Any
) -> None:
    ctx = make_context(UNPUBLISHED_README, unpublished_facts(make_fact), repository=WORDS)
    result = missing_sections(ctx)
    assert not any("## Installation" in e.replacement for e in result.edits)
    assert any("does not list it" in f.reason for f in result.findings)


def test_a_future_tense_release_claim_is_reported_and_corrected_only_as_a_whole_line(
    make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact("package:name", "Aspose.Words.FOSS", evidence=(("x.csproj", None),)),
        make_fact("package:published_version", "26.3.0", evidence=(("https://nuget", None),)),
        make_fact(
            "install_command:dotnet",
            "dotnet add package Aspose.Words.FOSS",
            attributes={"install_kind": "registry"},
            evidence=(("x.csproj", None), ("https://nuget", "package registry: found")),
        ),
    ]
    readme = (
        "# P\n\nThe NuGet package and new formats are landing soon.\n\n"
        "NuGet package landing soon.\n"
    )
    ctx = make_context(readme, facts, repository="aspose-words-foss/Aspose.Words-FOSS-for-.NET")
    result = stale_phrase(ctx)
    assert [f.line for f in result.findings] == [3]  # other claims in the sentence: reported
    (edit,) = result.edits  # nothing but the promise: replaced by the verified install command
    assert edit.original == "NuGet package landing soon."
    assert edit.replacement == "Install it with `dotnet add package Aspose.Words.FOSS`."


def test_a_future_tense_claim_about_an_unpublished_package_is_only_reported(
    make_context: Any, make_fact: Any
) -> None:
    readme = "# P\n\nOnce the repository is live at its real location, add it as a dependency.\n"
    result = stale_phrase(make_context(readme, unpublished_facts(make_fact), repository=WORDS))
    assert result.edits == () and len(result.findings) == 1


# ----------------------------------------------------------------------- other false positives
def test_a_github_relative_issues_link_is_not_a_dead_link(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    link = make_fact(
        "link_target:001",
        "../../issues",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "line 1; relative; text 'issues'"),
            ("README.md", "MISSING: tree does not contain ../../issues"),
        ),
    )
    result = broken_link(make_context("[issues](../../issues)\n", make_facts(link)))
    assert result.edits == () and result.findings == ()


def test_examples_failing_to_parse_are_reported_as_one_upstream_defect(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    def failing(number: int) -> Any:
        return make_fact(
            f"example:00{number}",
            "x",
            polarity="CONTRADICTED",
            evidence=(
                ("README.md", f"lines {number}-{number + 2}; python fence"),
                ("examples.json", f"example {number}: FAILED; IndentationError"),
            ),
        )

    result = failing_example(make_context("t\n", make_facts(failing(1), failing(2), failing(3))))
    assert any("library source itself may not parse" in f.reason for f in result.findings)
