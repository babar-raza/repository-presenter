"""Receipts are written as one deterministic JSON document, sorted by ordinal."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.core.examples import ExampleReceipt, FixtureBinding, write_receipts


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
