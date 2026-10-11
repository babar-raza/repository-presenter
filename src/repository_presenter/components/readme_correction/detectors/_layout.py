"""Where an addition goes in a README the maintainers wrote (shared by the addition detectors).

An addition is appended to the end of a section the README already has - after its last
non-blank line, in the README's own line-ending style - so no maintainer byte moves. A section
that cannot be appended to safely (an unclosed fence or ``<details>`` inside it, which would hide
or swallow the addition) yields no insertion point, and the detector reports nothing rather than
guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.components.readme_correction.model import Context, ReadmeLine

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FENCE_MARK = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*(\S*)")
_OPEN = re.compile(r"<details\b", re.IGNORECASE)
_CLOSE = re.compile(r"</details\s*>", re.IGNORECASE)
_CODE_SPAN = re.compile(r"`[^`]*`")
_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+")


@dataclass(frozen=True)
class H2Section:
    title: str
    heading: ReadmeLine
    lines: tuple[ReadmeLine, ...]  # the lines after the heading, up to the next H2

    @property
    def end(self) -> int:
        return self.lines[-1].end if self.lines else self.heading.end


@dataclass(frozen=True)
class AppendPoint:
    offset: int  # where the insertion goes
    prefix: str  # what must precede the addition so it starts on its own paragraph
    after_list: bool  # the section's last block is a list: bullets may continue it


def eol(ctx: Context) -> str:
    return "\r\n" if "\r\n" in ctx.readme else chr(10)


def h2_sections(ctx: Context) -> list[H2Section]:
    found: list[tuple[str, ReadmeLine, int]] = []
    for index, line in enumerate(ctx.lines):
        match = None if line.in_fence else HEADING.match(line.text)
        if match is not None and len(match.group(1)) == 2:
            found.append((match.group(2).strip(), line, index))
    sections: list[H2Section] = []
    for position, (title, heading, index) in enumerate(found):
        stop = found[position + 1][2] if position + 1 < len(found) else len(ctx.lines)
        sections.append(H2Section(title, heading, tuple(ctx.lines[index + 1 : stop])))
    return sections


def find_section(ctx: Context, pattern: re.Pattern[str]) -> H2Section | None:
    return next((s for s in h2_sections(ctx) if pattern.search(s.title)), None)


def fence_lines(ctx: Context) -> list[tuple[str, str]]:
    """``(language, line)`` of every line inside a fenced block, markers excluded."""
    found: list[tuple[str, str]] = []
    language: str | None = None
    for line in ctx.lines:
        mark = _FENCE_MARK.match(line.text) if line.in_fence else None
        if mark is not None and language is None:
            language = mark.group(2).lower()
        elif mark is not None:
            language = None
        elif line.in_fence and language is not None:
            found.append((language, line.text))
    return found


def append_point(ctx: Context, section: H2Section) -> AppendPoint | None:
    body = [line for line in section.lines if line.text.strip()]
    markers = sum(1 for line in section.lines if line.in_fence and _FENCE_MARK.match(line.text))
    if markers % 2:
        return None  # a fence opened and never closed inside the section
    opens = closes = 0
    for line in section.lines:
        if not line.in_fence:
            text = _CODE_SPAN.sub(" ", line.text)
            opens += len(_OPEN.findall(text))
            closes += len(_CLOSE.findall(text))
    if opens != closes:
        return None  # a <details> block that would swallow (or hide) the addition
    last = body[-1] if body else section.heading
    terminator = ctx.readme[last.end : last.end + 2]
    if terminator.startswith("\r\n"):
        offset, prefix = last.end + 2, ""
    elif terminator.startswith(chr(10)):
        offset, prefix = last.end + 1, ""
    else:
        offset, prefix = last.end, eol(ctx)
    after_list = bool(body) and not last.in_fence and bool(_LIST_ITEM.match(last.text))
    return AppendPoint(offset, prefix, after_list)


def addition_text(
    ctx: Context, point: AppendPoint, lines: list[str], *, continue_list: bool
) -> str:
    """The text inserted at ``point``: a blank line first (unless the last block is a list the
    ``lines`` continue), the ``lines`` in the README's line endings, one trailing line ending."""
    newline = eol(ctx)
    lead = "" if continue_list and point.after_list else newline
    return point.prefix + lead + newline.join(lines) + newline
