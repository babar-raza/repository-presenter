"""README examples the repository refutes are findings, never edits."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.detectors.examples import failing_example


def test_a_failing_example_is_reported_with_its_lines_and_never_edited(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    failing = make_fact(
        "example:003",
        "using Aspose.ThreeD;\nvar scene = Scene.FromFile(1);\n",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "lines 165-173; csharp fence; unit inherited_unit:032.code_block"),
            ("examples.json", "example 3: FAILED; Program.cs(3,41): error CS1503: Argument 2"),
        ),
    )
    result = failing_example(make_context("text\n", make_facts(failing)))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.line == 165 and "lines 165-173" in finding.reason and "CS1503" in finding.reason
    assert finding.fact_ids == ("example:003",)


def test_a_verified_or_unresolved_example_is_not_reported(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ok = make_fact(
        "example:001",
        "x",
        evidence=(("README.md", "lines 1-3; java fence; unit u"), ("examples.json", "EXECUTED")),
    )
    needs_input = make_fact(
        "example:002",
        "y",
        polarity="UNRESOLVED",
        evidence=(("README.md", "lines 5-9; python fence"), ("examples.json", "NEEDS_INPUT")),
    )
    assert failing_example(make_context("t\n", make_facts(ok, needs_input))).findings == ()
