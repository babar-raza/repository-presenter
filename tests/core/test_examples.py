"""Receipts are written as one deterministic JSON document, sorted by ordinal."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.core.examples import (
    PRELUDE_ATTRIBUTE,
    ExampleReceipt,
    FixtureBinding,
    collapse_blank_runs,
    printed_example,
    with_prelude,
    write_receipts,
)
from repository_presenter.core.facts import Evidence, Fact


def test_receipts_are_sorted_and_deterministic(tmp_path: Path) -> None:
    receipts = [
        ExampleReceipt(2, "FAILED", 1, "", "AttributeError: x", "AttributeError"),
        ExampleReceipt(
            1, "EXECUTED", 0, "ok\n", "", "exit 0", (FixtureBinding("model.obj", "tests/a.obj"),)
        ),
    ]
    write_receipts(receipts, tmp_path / "examples.json")
    first = (tmp_path / "examples.json").read_bytes()
    document = json.loads(first)
    assert [r["ordinal"] for r in document] == [1, 2]
    assert document[0]["fixtures"] == [
        {"literal": "model.obj", "source_path": "tests/a.obj", "produced_by": None}
    ]
    write_receipts(list(reversed(receipts)), tmp_path / "examples.json")
    assert (tmp_path / "examples.json").read_bytes() == first
    assert b"\r\n" not in first


def test_blank_line_runs_collapse_to_one_and_nothing_else_changes() -> None:
    """plans/idea.md: "visitor examples use normalized, language-valid spacing without repeated
    empty-line runs" - the example's one-blank-line paragraphs stay, its runs do not."""
    assert collapse_blank_runs("a\n\n\n\nb\n") == "a\n\nb\n"
    assert collapse_blank_runs("a\n  \n\t\nb\n") == "a\n  \nb\n"
    assert collapse_blank_runs("a\n\nb\n") == "a\n\nb\n"
    assert collapse_blank_runs("a\nb") == "a\nb"
    assert collapse_blank_runs("") == ""


def _example(code: str, prelude: str | None = None) -> Fact:
    return Fact(
        "example:001",
        "example",
        code,
        (Evidence("README.md", None),),
        attributes={PRELUDE_ATTRIBUTE: prelude} if prelude else None,
    )


def test_a_printed_example_is_the_program_its_receipt_compiled() -> None:
    """Wave-3 acceptance review, Slides-.NET: the harness supplied `using Aspose.Slides.Foss.
    Drawing;` for the receipt, the README printed none, and three of seven examples then failed
    CS0103/CS0246. The printed example carries the supplied lines in front of the snippet."""
    code = "using Aspose.Slides.Foss;\n\nvar c = Color.Red;\n"
    printed = printed_example(_example(code, "using Aspose.Slides.Foss.Drawing;"))
    assert (
        printed
        == "using Aspose.Slides.Foss.Drawing;\nusing Aspose.Slides.Foss;\n\nvar c = Color.Red;\n"
    )
    assert printed.endswith(code)


def test_an_example_that_needed_nothing_is_printed_as_written() -> None:
    assert printed_example(_example("print(1)\n")) == "print(1)\n"
    assert printed_example(_example("print(1)\n", "  \n")) == "print(1)\n"


def test_a_java_package_declaration_stays_the_first_statement() -> None:
    """`package` must open a compilation unit, so the supplied imports follow it."""
    code = "package org.x;\n\npublic class Demo {}\n"
    assert with_prelude(code, "import java.util.*;\nimport java.io.*;") == (
        "package org.x;\n\nimport java.util.*;\nimport java.io.*;\npublic class Demo {}\n"
    )
    assert with_prelude("var x = 1;", "using System;") == "using System;\nvar x = 1;"
