"""Edits that tip a validation check are dropped and reported; the rest are kept."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.composition.renderer import line_counts
from repository_presenter.components.readme_correction.settle import correct_settled


def readme(filler: int) -> str:
    lines = ["# Aspose.3D FOSS for Java", "", "## Installation", "", "```bash"]
    lines += ["mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0", "```", ""]
    lines += ["## Notes", ""] + [f"Maintainer line {n}." for n in range(filler)]
    lines += ["", "## Development and Testing", "", "Run it the usual way.", "", "## License", ""]
    return "\n".join([*lines, "MIT.", ""])


def commands(make_fact: Any) -> list[Any]:
    return [
        make_fact("build_test_asset:build-command", "mvn -B verify", evidence=(("pom.xml", "x"),)),
        make_fact("build_test_asset:test-command", "mvn test", evidence=(("pom.xml", "x"),)),
    ]


@pytest.mark.usefixtures("reenabled")
def test_an_addition_that_would_push_the_readme_over_a_budget_is_dropped_and_reported(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    text = readme(300 - line_counts(readme(0))[0])  # exactly at the 300 visible-line budget
    ctx = make_context(text, make_facts(*commands(make_fact)))
    result, delta = correct_settled(ctx, text.encode())
    detectors = {e.detector for e in result.edits}
    assert detectors == {"claim_version"}  # every insertion would pass the budget; the fix stays
    assert delta["introduced"] == []
    reasons = [f.reason for f in result.findings if f.detector == "add_dev_commands"]
    assert reasons and "visible" in reasons[0] and "BC-07" in reasons[0]


@pytest.mark.usefixtures("reenabled")
def test_the_same_addition_is_kept_when_there_is_room(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    text = readme(40)
    ctx = make_context(text, make_facts(*commands(make_fact)))
    result, delta = correct_settled(ctx, text.encode())
    assert {e.detector for e in result.edits} >= {"claim_version", "add_dev_commands"}
    assert delta["introduced"] == []


def test_the_settled_result_is_deterministic(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    text = readme(300 - line_counts(readme(0))[0])
    ctx = make_context(text, make_facts(*commands(make_fact)))
    first, _ = correct_settled(ctx, text.encode())
    second, _ = correct_settled(ctx, text.encode())
    assert first.corrected == second.corrected and first.edits == second.edits
