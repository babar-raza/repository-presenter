"""A governed version moves only behind a DECISION_LOG necessity entry (G3-W12, card C1).

``tests/test_version_bump_discipline.py`` proves a governed source's meaning never changes without
its constant moving. This test proves the converse the Lane R plan adds: no constant (or ``Check``
version) of a governed source moves between ``origin/main`` and ``HEAD`` unless
``docs/DECISION_LOG.md`` carries an entry written for that exact move, naming the metric, the
test-split cases that prove the defect and why no ungoverned fix works.

The entry is a heading line ``**Bump entry: <NAME> <old> -> <new>.**`` followed, within the same
entry, by the three markers ``Metric:``, ``Cases:`` and ``No ungoverned fix:``. A move with no such
entry, or an entry missing a marker, fails.

It fails, never skips, when ``origin/main`` is not fetched: a skipped check would let a branch move
a governed version unobserved (the same rule as the ratchet, ``tests/test_lane_r_ratchet.py``).
"""

from __future__ import annotations

import re

import pytest

from repository_presenter.core.git_safety.git import run_git
from support import REPO_ROOT
from test_version_bump_discipline import GOVERNED, GovernedSource, versions

DECISION_LOG = REPO_ROOT / "docs" / "DECISION_LOG.md"
MARKERS = ("Metric:", "Cases:", "No ungoverned fix:")
ENTRY_WINDOW = 14  # lines after the heading within which the three markers must appear


def _blob(revision: str, path: str) -> str | None:
    result = run_git(["show", f"{revision}:{path}"], cwd=REPO_ROOT)
    return result.stdout if result.returncode == 0 else None


def moves(base: str, head: str, source: GovernedSource) -> list[tuple[str, str | None, str | None]]:
    """(name, old value, new value) for each governed version that differs between two texts."""
    before = versions(base, source) if base is not None else {}
    after = versions(head, source) if head is not None else {}
    return [
        (name, before.get(name), after.get(name))
        for name in sorted({*before, *after})
        if before.get(name) != after.get(name)
    ]


def entry_for(log: str, name: str, old: str | None, new: str | None) -> str | None:
    """The text of the bump entry for exactly this move, or None."""
    heading = re.compile(
        rf"\*\*Bump entry: {re.escape(name)} {re.escape(str(old))} -> {re.escape(str(new))}\.\*\*"
    )
    lines = log.splitlines()
    for index, line in enumerate(lines):
        if heading.search(line):
            return "\n".join(lines[index : index + ENTRY_WINDOW])
    return None


def missing_entries(log: str, found: list[tuple[str, str, str | None, str | None]]) -> list[str]:
    problems: list[str] = []
    for path, name, old, new in found:
        entry = entry_for(log, name, old, new)
        if entry is None:
            problems.append(
                f"{path}: {name} {old} -> {new} has no '**Bump entry: ...**' in DECISION_LOG"
            )
            continue
        for marker in MARKERS:
            if marker not in entry:
                problems.append(f"{path}: the bump entry for {name} lacks '{marker}'")
            elif not re.search(re.escape(marker) + r"[ \t]*[^\s*][^\n]{3,}", entry):
                problems.append(f"{path}: the bump entry for {name} has an empty '{marker}'")
    return problems


def _require_main() -> None:
    probe = run_git(["rev-parse", "--verify", "--quiet", "origin/main^{commit}"], cwd=REPO_ROOT)
    if probe.returncode != 0:
        pytest.fail(
            "origin/main is not fetched: this test never skips (git fetch origin main; hosted CI "
            "needs fetch-depth 0 or an explicit fetch)"
        )


def test_no_governed_version_moves_without_a_necessity_entry() -> None:
    _require_main()
    log = DECISION_LOG.read_text(encoding="utf-8")
    found: list[tuple[str, str, str | None, str | None]] = []
    for source in GOVERNED:
        base = _blob("origin/main", source.path)
        head = _blob("HEAD", source.path)
        if base is None or head is None:
            continue
        found += [(source.path, name, old, new) for name, old, new in moves(base, head, source)]
    assert not missing_entries(log, found), "\n".join(missing_entries(log, found))


# --- the check itself, held to known answers (a negative control per rule) ------------------------

_SOURCE = GovernedSource("renderer", "x.py", ("RENDERER_VERSION",))


def test_a_moved_constant_is_found() -> None:
    assert moves('RENDERER_VERSION = "1"\n', 'RENDERER_VERSION = "2"\n', _SOURCE) == [
        ("RENDERER_VERSION", "1", "2")
    ]


def test_an_unmoved_constant_and_unrelated_edits_are_not_moves() -> None:
    same = 'RENDERER_VERSION = "1"\nOTHER = 1\n'
    assert moves(same, same + "OTHER2 = 2\n", _SOURCE) == []


def test_a_move_without_an_entry_is_a_problem() -> None:
    problems = missing_entries("nothing here", [("x.py", "RENDERER_VERSION", "1", "2")])
    assert len(problems) == 1 and "has no" in problems[0]


def test_an_entry_missing_a_marker_is_a_problem() -> None:
    log = "**Bump entry: RENDERER_VERSION 1 -> 2.**\nMetric: M4 claim escapes\nCases: traced-T6\n"
    problems = missing_entries(log, [("x.py", "RENDERER_VERSION", "1", "2")])
    assert problems == ["x.py: the bump entry for RENDERER_VERSION lacks 'No ungoverned fix:'"]


def test_a_complete_entry_for_the_exact_move_passes() -> None:
    log = (
        "**Bump entry: RENDERER_VERSION 1 -> 2.**\n"
        "Metric: M4 claim escapes\nCases: traced-T6\nNo ungoverned fix: the renderer prints it\n"
    )
    assert missing_entries(log, [("x.py", "RENDERER_VERSION", "1", "2")]) == []


def test_an_entry_for_another_move_does_not_cover_this_one() -> None:
    log = "**Bump entry: RENDERER_VERSION 1 -> 3.**\nMetric: M4\nCases: t\nNo ungoverned fix: x\n"
    assert missing_entries(log, [("x.py", "RENDERER_VERSION", "1", "2")])


def test_an_entry_with_empty_markers_is_a_problem() -> None:
    log = "**Bump entry: RENDERER_VERSION 1 -> 2.**\nMetric:\nCases:\nNo ungoverned fix:\n"
    problems = missing_entries(log, [("x.py", "RENDERER_VERSION", "1", "2")])
    assert len(problems) == 3 and all("empty" in p for p in problems)
