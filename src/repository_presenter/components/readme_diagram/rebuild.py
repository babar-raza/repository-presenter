"""Rewrite the At a Glance diagram of a README, changing nothing else.

``rebuild_body`` turns one diagram's source into the canonical drawing of the same meaning and
proves, by parsing both, that every node label, group title and chain edge survived.
``rebuild_readme`` finds the Mermaid fences of a README, rewrites the lines *between* the fence
markers of each At a Glance diagram that is not already conforming, and returns the rest of the
text byte for byte (line endings included). A fence that is not an At a Glance chain is never
touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.components.readme_diagram.build import build_body
from repository_presenter.components.readme_diagram.lint import lint_parsed, normalize
from repository_presenter.components.readme_diagram.model import LintReport, NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse

_OPEN = re.compile(r"^(`{3,}|~{3,})[ \t]*mermaid\b[^\r\n]*$", re.IGNORECASE)


class RebuildError(ValueError):
    """A rewrite that would have changed what the diagram says; never returned, never applied."""


@dataclass(frozen=True)
class Fence:
    """A Mermaid fence of a README: the opening marker is ``lines[first - 1]``, the body is
    ``lines[first:last]`` and the closing marker is ``lines[last]``."""

    first: int
    last: int
    body: str


@dataclass(frozen=True)
class FenceChange:
    """One rewritten diagram: where, what was wrong, and the two sources."""

    first_line: int  # 1-based number of the diagram's first source line
    report: LintReport
    before: str
    after: str


@dataclass(frozen=True)
class Rebuilt:
    text: str
    changes: tuple[FenceChange, ...]
    #: Mermaid fences left alone: ``(first source line, reason)``.
    skipped: tuple[tuple[int, str], ...]


def rebuild_body(body: str) -> str:
    """The canonical source for the diagram ``body`` says; the same meaning, proven."""
    before = parse(body)
    after = build_body(before.glance)
    if parse(after).glance != before.glance:
        raise RebuildError("the rebuilt diagram does not say what the original said")
    return after


def mermaid_fences(lines: list[str]) -> list[Fence]:
    """Every fenced ``mermaid`` block of ``lines`` (a README split with ``keepends=True``)."""
    found: list[Fence] = []
    index = 0
    while index < len(lines):
        match = _OPEN.match(lines[index].rstrip("\r\n"))
        if match is None:
            index += 1
            continue
        marker = match.group(1)
        end = index + 1
        while end < len(lines):
            text = lines[end].strip()
            if len(text) >= len(marker) and set(text) == {marker[0]}:
                break
            end += 1
        if end >= len(lines):
            break  # an unclosed fence: nothing after it is trustworthy
        found.append(Fence(index + 1, end, "".join(lines[index + 1 : end])))
        index = end + 1
    return found


def rebuild_readme(text: str) -> Rebuilt:
    """``text`` with every non-conforming At a Glance diagram rewritten; the rest untouched."""
    lines = text.splitlines(keepends=True)
    changes: list[FenceChange] = []
    skipped: list[tuple[int, str]] = []
    out: list[str] = []
    cursor = 0
    for fence in mermaid_fences(lines):
        opener = lines[fence.first - 1]
        eol = "\r\n" if opener.endswith("\r\n") else "\n"
        number = fence.first + 1
        if opener[0] in " \t":
            skipped.append((number, "an indented fence"))
            continue
        try:
            parsed = parse(fence.body)
        except NotAGlanceError as error:
            skipped.append((number, str(error)))
            continue
        report = lint_parsed(parsed, fence.body)
        if report.conforming:
            continue
        after = rebuild_body(fence.body)
        if normalize(fence.body) == after:
            continue
        out.extend(lines[cursor : fence.first])
        out.append(after.replace("\n", eol))
        cursor = fence.last
        changes.append(FenceChange(number, report, fence.body, after))
    out.extend(lines[cursor:])
    return Rebuilt("".join(out), tuple(changes), tuple(skipped))
