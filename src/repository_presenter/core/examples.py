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


FormatDeclarationKind = Literal["declaration", "registration"]


@dataclass(frozen=True)
class FormatDeclaration:
    """A static statement about a format, read from the product's own source without importing
    it: a ``declaration`` states an extension the product provides (direction None), and a
    ``registration`` implements one direction of it with a non-stub importer or exporter."""

    extension: str
    direction: FormatDirection | None
    kind: FormatDeclarationKind
    source_path: str
    line: int
    detail: str


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
    """An input file staged under the name the example opens.

    ``source_path`` is the repository path the file came from, or the file name an earlier
    example wrote; ``produced_by`` names that example's ordinal when the fixture is its output.
    A repository that ships no sample data can still verify an example that reads one, provided
    another example of the same README produced it (docs/RESEARCH_AND_GUIDELINES.md 27.2 RC6).
    """

    literal: str
    source_path: str
    produced_by: int | None = None


@dataclass(frozen=True)
class ExampleReceipt:
    """The verification outcome of one candidate, with redacted output.

    ``build_verified`` distinguishes what ``outcome == "EXECUTED"`` actually proved (TB-01,
    external review D1, 2026-09-08): a full, genuine build/install of the product, or a weaker
    path that still legitimately runs the example - a syntax-only compile check (C++'s
    ``-fsyntax-only``, which never links or builds the library) or a source-tree fallback used
    after the real package install failed. Defaults to ``True`` because most ecosystems' EXECUTED
    outcome already means exactly this; only the platforms with a weaker EXECUTED path (currently
    C++'s syntax check and Python's install-failure fallback) ever set it ``False``.
    ``extract.py::_source_build_fact`` reads this before promoting an install command to
    SUPPORTED, so a syntax-only or fallback run is never rendered as "verified against this
    revision" for a build that was never actually proven to succeed.
    """

    ordinal: int
    outcome: ExampleOutcome
    return_code: int | None
    stdout: str
    stderr: str
    detail: str
    fixtures: tuple[FixtureBinding, ...] = ()
    build_verified: bool = True


def write_receipts(receipts: list[ExampleReceipt], path: Path) -> None:
    """Write the receipts as one deterministic JSON document."""
    payload = [asdict(receipt) for receipt in sorted(receipts, key=lambda r: r.ordinal)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
