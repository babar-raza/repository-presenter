"""Missing template sections: rendered from facts, inserted additively, never duplicated."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
)
from repository_presenter.components.readme_correction.detectors.sections import missing_sections

README = """# Product

Opening paragraph the maintainers wrote.

## Key Capabilities

- Reads files.

## Scope and Limitations

Only STL works.
"""


def inserted(make_context: Any, readme: str, **kwargs: Any) -> tuple[str, Any]:
    result = missing_sections(make_context(readme, **kwargs))
    corrected, _spans = apply_edits(readme, sorted(result.edits, key=lambda e: (e.start, e.order)))
    return corrected, result


@pytest.mark.usefixtures("reenabled")
def test_missing_sections_are_rendered_from_facts_and_placed_in_template_order(
    make_context: Any,
) -> None:
    ctx = make_context(README)
    result = missing_sections(ctx)
    edits = sorted(result.edits, key=lambda e: (e.start, e.order))
    corrected, spans = apply_edits(README, edits)
    assert confinement_violations(README, corrected, edits, spans) == []  # maintainer bytes kept
    headings = [line for line in corrected.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Key Capabilities",
        "## Installation",
        "## Dependencies",
        "## Scope and Limitations",
        "## Development and Testing",
        "## License",
    ]
    assert "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0" in corrected
    assert "licensed under the [MIT License](LICENSE)" in corrected
    assert "\n\n\n" not in corrected
    assert {e.kind for e in result.edits} == {"MISSING_SECTION"}
    assert all(e.fact_ids for e in result.edits)


def test_a_section_goes_before_the_first_heading_the_template_orders_after_it(
    make_context: Any,
) -> None:
    readme = "# P\n\n## Key Capabilities\n\n- x\n\n## Quick Start\n\nrun it\n\n## License\n\nMIT.\n"
    corrected, _ = inserted(make_context, readme)
    order = [line for line in corrected.splitlines() if line.startswith("## ")]
    assert order[:4] == [
        "## Key Capabilities",
        "## Installation",
        "## Dependencies",
        "## Quick Start",
    ]
    assert corrected.count("## License") == 1  # present under its own heading: not duplicated


@pytest.mark.usefixtures("reenabled")
def test_a_section_present_under_another_name_is_not_duplicated(make_context: Any) -> None:
    readme = (
        "# P\n\n## Getting Started\n\nmvn dependency:get -Dartifact=x\n\n"
        "## Requirements\n\nJava 21\n\n## Legal\n\nMIT\n"
    )
    result = missing_sections(make_context(readme))
    assert {e.rationale.split(" section")[0] for e in result.edits} == {
        "the README has no Development and Testing"
    }


def test_an_installation_that_already_spells_the_verified_command_is_not_added(
    make_context: Any,
) -> None:
    command = "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0"
    readme = f"# P\n\n## Usage\n\n{command}\n\n## Notes\n\nx\n"
    names = [e.rationale for e in missing_sections(make_context(readme)).edits]
    assert not any("Installation" in name for name in names)


def test_a_readme_without_structure_gets_no_insertion(make_context: Any) -> None:
    result = missing_sections(make_context("# P\n\nJust one paragraph.\n"))
    assert result.edits == () and "fewer than two H2 sections" in result.findings[0].reason


def test_a_section_with_no_verified_fact_is_reported_not_invented(
    make_context: Any, make_facts: Any
) -> None:
    facts = make_facts(drop=["license:spdx", "license:file", "install_command:maven"])
    result = missing_sections(make_context(README, facts))
    names = {e.rationale for e in result.edits}
    assert not any("License" in n or "Installation" in n for n in names)
    assert any("license is absent and no verified fact" in f.reason for f in result.findings)


def test_sections_that_need_prose_are_listed_as_gaps_when_absent(make_context: Any) -> None:
    result = missing_sections(make_context(README))
    reasons = " ".join(f.reason for f in result.findings)
    assert "Quick Start is absent" in reasons and "At a Glance is absent" in reasons
    assert "Key Capabilities is absent" not in reasons  # the README has it


def test_an_h2_inside_a_fence_is_not_a_heading(make_context: Any) -> None:
    readme = "# P\n\n## Key Capabilities\n\n```md\n## License\n```\n\n## Scope\n\ntext\n"
    corrected, _ = inserted(make_context, readme)
    assert corrected.count("licensed under") == 1  # License was missing in prose: added once


def test_third_party_notices_are_not_one_of_the_ten_and_are_never_added(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    notices = make_fact("third_party_notices:file", "THIRD_PARTY_NOTICES.md")
    result = missing_sections(make_context(README, make_facts(notices)))
    assert not any("Third" in e.rationale for e in result.edits)
