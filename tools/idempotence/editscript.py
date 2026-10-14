"""How big the edit script from the live README to a candidate is (metric b).

An idempotent system changes a README by a short, enumerable script. A regeneration changes it by
a rewrite. The measure is the plain line diff: how many unified-diff hunks (the unit a reviewer
reads in ``README.patch``, three lines of context), how many separate runs of changed lines, and
how many lines were removed and added.

Pure function of the two texts.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

CONTEXT = 3  # lines of context in a unified-diff hunk, the same as git and README.patch


@dataclass(frozen=True)
class Change:
    """One run of changed lines (``replace``, ``delete`` or ``insert``), 1-based and inclusive."""

    tag: str
    live_first: int
    live_last: int  # live_first - 1 for a pure insertion
    candidate_first: int
    candidate_last: int

    @property
    def removed(self) -> int:
        return self.live_last - self.live_first + 1

    @property
    def added(self) -> int:
        return self.candidate_last - self.candidate_first + 1


@dataclass
class EditScript:
    live_lines: int
    candidate_lines: int
    hunks: int = 0  # unified-diff hunks with CONTEXT lines of context
    removed: int = 0
    added: int = 0
    changes: list[Change] = field(default_factory=list)

    @property
    def runs(self) -> int:
        """Separate runs of changed lines, before hunks merge the ones that sit close together."""
        return len(self.changes)

    @property
    def changed_lines(self) -> int:
        return self.removed + self.added

    @property
    def identical(self) -> bool:
        return not self.changes


def edit_script(live: str, candidate: str) -> EditScript:
    a = [line.rstrip() for line in live.splitlines()]
    b = [line.rstrip() for line in candidate.splitlines()]
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    script = EditScript(len(a), len(b))
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        script.changes.append(Change(tag, i1 + 1, i2, j1 + 1, j2))
        script.removed += i2 - i1
        script.added += j2 - j1
    script.hunks = len(list(matcher.get_grouped_opcodes(CONTEXT))) if script.changes else 0
    return script
