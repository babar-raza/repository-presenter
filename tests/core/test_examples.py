"""Receipts are written as one deterministic JSON document, sorted by ordinal."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.core.examples import (
    ExampleReceipt,
    FixtureBinding,
    collapse_blank_runs,
    write_receipts,
)


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
