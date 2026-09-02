"""Shared example-verification types: what a platform plugin receives and what it returns."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

ExampleOutcome = Literal["EXECUTED", "FAILED", "TIMED_OUT", "NEEDS_INPUT", "NOT_VERIFIED"]
FormatDirection = Literal["input", "output"]
RECEIPTS_FILENAME = "examples.json"


@dataclass(frozen=True)
class FormatClaim:
    """A file extension one example statement loads (input) or saves (output), by code line."""

    extension: str
    direction: FormatDirection
    line: int


@dataclass(frozen=True)
class ExampleCandidate:
    """One code block of the existing README that claims to be a runnable example."""

    ordinal: int
    language: str
    code: str
    source_path: str
    start_line: int
    end_line: int
    unit_id: str


@dataclass(frozen=True)
class FixtureBinding:
    """A repository-owned input file staged under the name the example opens."""

    literal: str
    source_path: str


@dataclass(frozen=True)
class ExampleReceipt:
    """The verification outcome of one candidate, with redacted output."""

    ordinal: int
    outcome: ExampleOutcome
    return_code: int | None
    stdout: str
    stderr: str
    detail: str
    fixtures: tuple[FixtureBinding, ...] = ()


def write_receipts(receipts: list[ExampleReceipt], path: Path) -> None:
    """Write the receipts as one deterministic JSON document."""
    payload = [asdict(receipt) for receipt in sorted(receipts, key=lambda r: r.ordinal)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
