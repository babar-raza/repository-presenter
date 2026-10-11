"""Receipts are written as one deterministic JSON document, sorted by ordinal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.core.examples import (
    PRELUDE_ATTRIBUTE,
    ExampleReceipt,
    FixtureBinding,
    collapse_blank_runs,
    printed_example,
    stable_output,
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


# --- wave 6 (cut 5): a receipt is the same bytes in every process --------------------------------
# PDF-Python was held at BC-11 PENDING for three waves in a row: 14 of its 20 receipts carried the
# library's own wall-clock log line, so a fresh process could never reproduce examples.json and
# the zero-call no-op proof was withdrawn ("examples.json changed since the last seal").
VOLATILE = [
    "2026-10-12 00:43:01,981 [INFO] aspose_pdf: Document resources released.",
    "2026-10-12T00:43:01.981234Z [info] done",
    "2026-10-12 00:43:01+02:00 started",
    "[00:43:01.981] request finished",
    "Mon Oct 12 00:43:01 2026",
    "Ran 3 tests in 0.001s",
    "== 3 passed in 0.02s ==",
    "Done in 2.45s.",
    "took 12ms",
    "Elapsed: 00:00:01.25 total",
    "--- PASS: TestSave (0.00s)",
    "<widget.Document object at 0x000001F4A3B2C4D0>",
    "worker pid=18244 ready",
    "request 3f2504e0-4f89-11d3-9a0c-0305e82c3301 sent",
    "wrote /var/tmp/tmp9xk2_ab3/out.pdf",
]


@pytest.mark.parametrize("line", VOLATILE)
def test_a_receipt_carries_nothing_that_depends_on_when_or_where_it_ran(line: str) -> None:
    once = stable_output(line)
    assert once != line
    assert stable_output(once) == once  # idempotent: sealing a sealed receipt moves nothing
    receipt = ExampleReceipt(1, "EXECUTED", 0, line + "\n", line, "exit 0")
    assert receipt.stdout == once + "\n" and receipt.stderr == once


@pytest.mark.parametrize(
    "line",
    [
        "hello world",
        "Saved 3 pages to out.pdf",
        "version 26.9.0",
        "page 1 of 12 (landscape)",
        "values: [1, 2, 3]",
        "converted 2024-01-15 to a date",  # a date with no time of day is the example's own output
        "no exit within 60s",
        "retry in 5 seconds",  # a configured whole-second wait is not a measurement
        "0xFF is 255",
        "within 3.5 of the target",
    ],
)
def test_the_examples_own_deterministic_output_is_left_alone(line: str) -> None:
    assert stable_output(line) == line
    assert ExampleReceipt(1, "EXECUTED", 0, line, line, line).stdout == line


def test_two_runs_of_the_same_logging_example_write_the_same_examples_json(tmp_path: Path) -> None:
    clock = iter(["2026-10-12 00:43:01,981", "2026-10-12 00:43:09,114"])
    runs = []
    for name in ("first", "second"):
        stderr = f"{next(clock)} [INFO] aspose_pdf: Document resources released.\n"
        receipt = ExampleReceipt(1, "EXECUTED", 0, "done in 0.31s\n", stderr, "exit 0")
        write_receipts([receipt], tmp_path / f"{name}.json")
        runs.append((tmp_path / f"{name}.json").read_bytes())
    assert runs[0] == runs[1]
