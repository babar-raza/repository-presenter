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


def _before_trailing_details(section: H2Section, body: list[ReadmeLine]) -> ReadmeLine | None:
    """The line an addition follows: the section's last line, unless that line closes a
    ``<details>`` block, in which case the last visible line before the block opened (an addition
    never lands after a closing tag, detached from the commands it concerns). ``None`` when nothing
    visible comes before the block."""
    if not _CLOSE.search(_CODE_SPAN.sub(" ", body[-1].text)) or body[-1].in_fence:
        return body[-1]
    depth = 0
    opener: ReadmeLine | None = None
    for line in section.lines:
        if line.in_fence:
            continue
        text = _CODE_SPAN.sub(" ", line.text)
        for _ in _OPEN.findall(text):
            if depth == 0:
                opener = line
            depth += 1
        for _ in _CLOSE.findall(text):
            depth = max(0, depth - 1)
    if opener is None:
        return body[-1]
    earlier = [line for line in body if line.start < opener.start]
    return earlier[-1] if earlier else None


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
    last = _before_trailing_details(section, body) if body else section.heading
    if last is None:
        return None  # the section is only a collapsed block: nothing visible to sit beside
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


# ------------------------------------------------------------------------------------ Navigation
_TOC_ITEM = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>[-*+])[ \t]+\[(?P<text>[^\]]+)\]\(#(?P<anchor>[^)\s]+)\)[ \t]*$"
)
_NAV_HEADING = re.compile(r"navigation|table of contents|^contents$", re.IGNORECASE)
_SLUG_STRIP = re.compile(r"[^\w\- ]")


def slug(heading: str) -> str:
    """GitHub's anchor for ``heading`` (what the renderer's ``anchor`` computes)."""
    return _SLUG_STRIP.sub("", heading.strip().lower()).replace(" ", "-")


@dataclass(frozen=True)
class NavigationPlan:
    status: str  # "none" (no contents list), "ok", or "unsafe" (one this path cannot extend)
    offset: int = 0
    text: str = ""
    line: int = 0  # the contents-list line the new item sits beside


def _toc_group(ctx: Context) -> list[ReadmeLine] | None:
    group: list[ReadmeLine] = []
    best: list[ReadmeLine] = []
    for line in ctx.lines:
        if not line.in_fence and _TOC_ITEM.match(line.text):
            group.append(line)
            continue
        if len(group) >= 3 and not best:
            best = group
        group = []
    if len(group) >= 3 and not best:
        best = group
    return best or None


def navigation_plan(ctx: Context, heading: str, following_h2_start: int | None) -> NavigationPlan:
    """Where the contents list gets the new section's item: in front of the item for the H2 that
    now follows it, else behind the item for the nearest H2 before it. ``none`` when the README
    has no contents list; ``unsafe`` when it has one this path cannot place an item in (a
    Navigation heading with no parseable list, or no neighbour of the section in the list)."""
    group = _toc_group(ctx)
    has_heading = any(_NAV_HEADING.search(section.title) for section in h2_sections(ctx))
    if group is None:
        return NavigationPlan("unsafe" if has_heading else "none")
    items: dict[str, tuple[ReadmeLine, re.Match[str]]] = {}
    for line in group:
        match = _TOC_ITEM.match(line.text)
        assert match is not None
        items.setdefault(match.group("anchor").lower(), (line, match))
    sections = h2_sections(ctx)
    newline = eol(ctx)
    top = min((len(m.group("indent")) for _line, m in items.values()), default=0)

    def bullet(match: re.Match[str]) -> str:
        return f"{match.group('indent')}{match.group('marker')} [{heading}](#{slug(heading)})"

    following = next((s for s in sections if s.heading.start == following_h2_start), None)
    if following is not None and slug(following.title) in items:
        line, match = items[slug(following.title)]
        if len(match.group("indent")) == top:
            return NavigationPlan("ok", line.start, bullet(match) + newline, line.number)
    preceding = [
        s for s in sections if following_h2_start is None or s.heading.start < following_h2_start
    ]
    for section in reversed(preceding):
        if slug(section.title) in items:
            line, match = items[slug(section.title)]
            if len(match.group("indent")) != top:
                continue
            last = line
            for candidate in group[group.index(line) + 1 :]:
                found = _TOC_ITEM.match(candidate.text)
                if found is None or len(found.group("indent")) <= top:
                    break
                last = candidate
            terminator = ctx.readme[last.end : last.end + 2]
            if terminator.startswith("\r\n"):
                return NavigationPlan("ok", last.end + 2, bullet(match) + newline, line.number)
            if terminator.startswith(chr(10)):
                return NavigationPlan("ok", last.end + 1, bullet(match) + newline, line.number)
            return NavigationPlan("ok", last.end, newline + bullet(match), line.number)
    return NavigationPlan("unsafe")
