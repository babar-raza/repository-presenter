"""Receipt outcomes map to fact polarities; an unverified example is never called supported."""

from __future__ import annotations

from repository_presenter.components.readme.extractors.examples.verify import example_facts
from repository_presenter.core.examples import (
    PRELUDE_ATTRIBUTE,
    ExampleCandidate,
    ExampleReceipt,
    FixtureBinding,
    printed_example,
)


def _candidate(ordinal: int) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal,
        "python",
        f"print({ordinal})\n",
        "README.md",
        10 * ordinal,
        10 * ordinal + 2,
        f"inherited_unit:{ordinal:03d}.code_block",
    )


def test_outcomes_become_polarities_with_receipt_evidence() -> None:
    candidates = [_candidate(n) for n in range(1, 6)]
    receipts = [
        ExampleReceipt(
            1, "EXECUTED", 0, "ok", "", "exit 0", (FixtureBinding("a.obj", "tests/a.obj"),)
        ),
        ExampleReceipt(2, "FAILED", 1, "", "Traceback\nAttributeError: nope", "AttributeError"),
        ExampleReceipt(3, "TIMED_OUT", 124, "", "", "no exit within 120s"),
        ExampleReceipt(4, "NEEDS_INPUT", 1, "", "FileNotFoundError", "FileNotFoundError: input"),
    ]
    facts = example_facts(candidates, receipts, "examples.json")
    assert [(f.id, f.polarity, f.confidence) for f in facts] == [
        ("example:001", "SUPPORTED", 1.0),
        ("example:002", "CONTRADICTED", 1.0),
        ("example:003", "CONTRADICTED", 1.0),
        ("example:004", "UNRESOLVED", 0.5),
        ("example:005", "UNRESOLVED", 0.5),
    ]
    assert facts[0].value == "print(1)\n"
    assert facts[0].evidence[0].path == "README.md"
    assert (
        facts[0].evidence[0].detail
        == "lines 10-12; python fence; unit inherited_unit:001.code_block"
    )
    assert facts[0].evidence[1].detail == "example 1: EXECUTED; exit 0"
    assert facts[0].evidence[2].path == "tests/a.obj"
    assert facts[4].evidence[1].detail == "example 5: NOT_VERIFIED; no verification receipt"


def test_a_verified_programs_prelude_travels_on_the_example_fact() -> None:
    """The lines the verifier compiled in front of the snippet reach the fact as an attribute the
    renderer prints; a failed or unprepared example carries none."""
    candidates = [_candidate(1), _candidate(2), _candidate(3)]
    receipts = [
        ExampleReceipt(1, "EXECUTED", 0, "", "", "exit 0", prelude="using System;"),
        ExampleReceipt(2, "FAILED", 1, "", "", "CS0246", prelude="using System;"),
        ExampleReceipt(3, "EXECUTED", 0, "", "", "exit 0"),
    ]
    facts = example_facts(candidates, receipts, "examples.json")
    assert facts[0].attributes == {PRELUDE_ATTRIBUTE: "using System;"}
    assert printed_example(facts[0]) == "using System;\nprint(1)\n"
    assert facts[1].attributes is None
    assert facts[2].attributes is None
    assert printed_example(facts[2]) == "print(3)\n"
