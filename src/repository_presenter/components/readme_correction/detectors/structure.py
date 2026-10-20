"""Markup the README shows broken, fixed by the smallest edit that restores it.

Three defects measured on live portfolio READMEs: a second H1 (the template has exactly one), a
``<details>`` block opened and never closed, which makes every section after it - Detailed
Documentation, Constraints, License - render collapsed (Aspose.Cells for Go), and a stray closing
code fence, a lone fence line that closes nothing and turns the sections after it into a literal
code block (Aspose.PSD for Python). None needs a fact: the README's own text is the evidence,
recorded as a ``README.md:<line>`` locator, and each fix is one character run (a heading marker,
one closing tag in front of the next H2, or the one fence line emptied).

Fence state is the project's own (``text_checks.scan``), and ``<details>`` tags are counted only
outside fences. A ``</details>`` that a stray fence hides is not missing: the stray fence is the
defect, so ``unclosed_details`` reads the README as it is once that one line is gone.
"""

from __future__ import annotations

import functools
import re

from markdown_it import MarkdownIt

from repository_presenter.components.readme.review.acceptance.text_checks import scan
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    STRUCTURE_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
    ReadmeLine,
)

NL = chr(10)
_H1 = re.compile(r"^#(?!#)[ \t]+\S")
_H2 = re.compile(r"^##(?!#)[ \t]+\S")
_OPEN = re.compile(r"<details\b", re.IGNORECASE)
_CLOSE = re.compile(r"</details\s*>", re.IGNORECASE)
_CODE_SPAN = re.compile(r"`[^`]*`")
#: A fence line with no info string: the only kind that can close a block, so the only kind that
#: can be a stray closer (the fence rule itself is ``text_checks._FENCE``).
_BARE_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*$")
_MARKDOWN = MarkdownIt("commonmark")


def _headings(text: str) -> int:
    """Headings CommonMark parses in ``text`` (a heading inside a code block is not one)."""
    return sum(token.type == "heading_open" for token in _MARKDOWN.parse(text))


def _unterminated(text: str) -> bool:
    """Whether a fenced block in ``text`` runs to the end of its container without a closer."""
    lines = text.splitlines()
    for token in _MARKDOWN.parse(text):
        if token.type != "fence" or token.map is None:
            continue
        first, last = token.map
        closer = lines[last - 1].lstrip("> \t") if last - 1 > first else ""
        if not re.fullmatch(
            re.escape(token.markup[0]) + "{" + str(len(token.markup)) + r",}\s*", closer
        ):
            return True
    return False


@functools.lru_cache(maxsize=8)
def _stray_fence_number(readme: str) -> int | tuple[int, ...]:
    """The 1-based line of the one stray closing fence, else ``0`` (none), else every line that
    ties for the best repair (ambiguous).

    A fence line is stray when emptying it alone makes the parsed heading count rise and leaves
    every fenced block closed: the lone fence that turns the sections after it into a code block.
    The repair that exposes the most headings wins."""
    lines = readme.splitlines()
    base = _headings(readme)
    best = 0
    winners: list[int] = []
    for number, text in enumerate(lines, start=1):
        if not _BARE_FENCE.match(text):
            continue
        without = NL.join(lines[: number - 1] + lines[number:])
        gain = _headings(without) - base
        if gain > 0 and gain >= best and not _unterminated(without):
            winners = [number] if gain > best else [*winners, number]
            best = gain
    if not winners:
        return 0
    return winners[0] if len(winners) == 1 else tuple(winners)


def _stray_fence(ctx: Context) -> ReadmeLine | None:
    found = _stray_fence_number(ctx.readme)
    return ctx.lines[found - 1] if isinstance(found, int) and found else None


def _fence_flags(ctx: Context) -> list[bool]:
    """Per README line, whether it lies in a fenced block once a stray fence is gone (the stray
    line itself counts as fenced: it is the one line that is not content)."""
    stray = _stray_fence(ctx)
    if stray is None:
        return [line.in_fence for line in ctx.lines]
    kept = [line.text for line in ctx.lines if line.number != stray.number]
    flags = [line.code for line in scan(NL.join(kept))]
    flags.insert(stray.number - 1, True)
    return flags


@detector("second_h1")
def second_h1(ctx: Context) -> DetectorResult:
    """Every H1 after the first becomes an H2: one character, the heading text and its in-page
    anchor unchanged, so a Navigation entry that links it keeps working."""
    h1s = [line for line in ctx.lines if not line.in_fence and _H1.match(line.text)]
    edits = [
        Edit(
            kind=STRUCTURE_FIX,
            detector="second_h1",
            start=line.start,
            end=line.start + 1,
            original="#",
            replacement="##",
            fact_ids=(),
            locators=(f"{ctx.readme_path}:{line.number}",),
            rationale=(
                f"line {line.number} is a second H1 ({line.text[:60]!r}); the template has "
                f"exactly one, the product title on line {h1s[0].number}"
            ),
        )
        for line in h1s[1:]
    ]
    return DetectorResult(edits=tuple(edits))


@detector("unclosed_details")
def unclosed_details(ctx: Context) -> DetectorResult:
    """A ``<details>`` with no ``</details>``: close it in front of the next H2 after it.

    Tags count only outside fenced blocks, with a stray closing fence (``stray_fence``) read as
    already gone: a ``</details>`` it hides is not missing. An H2 inside a collapsed block is a
    section heading that the block was never meant to hold, so the first one after the opening tag
    is where the block ends. No H2 after it: reported by leaving the README as written (an
    unclosed block at the very end hides nothing)."""
    fenced = _fence_flags(ctx)
    stack: list[int] = []  # line numbers of the openings not yet closed
    for line in ctx.lines:
        if fenced[line.number - 1]:
            continue
        # A tag named inside an inline code span is text, not markup (an API table row that
        # documents `<details>`; measured on Aspose.HTML for Python).
        text = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line.text)
        for token in sorted(
            [(m.start(), True) for m in _OPEN.finditer(text)]
            + [(m.start(), False) for m in _CLOSE.finditer(text)]
        ):
            if token[1]:
                stack.append(line.number)
            elif stack:
                stack.pop()
    edits: list[Edit] = []
    closed_at: set[int] = set()
    for opened in stack:
        heading = next(
            (
                line
                for line in ctx.lines
                if line.number > opened and not fenced[line.number - 1] and _H2.match(line.text)
            ),
            None,
        )
        if heading is None:
            continue
        blank_before = (
            heading.start == 0
            or heading.start in closed_at
            or ctx.readme[: heading.start].endswith(NL * 2)
        )
        closed_at.add(heading.start)
        edits.append(
            Edit(
                kind=STRUCTURE_FIX,
                detector="unclosed_details",
                start=heading.start,
                end=heading.start,
                original="",
                replacement=("" if blank_before else NL) + "</details>" + NL * 2,
                fact_ids=(),
                locators=(f"{ctx.readme_path}:{opened}", f"{ctx.readme_path}:{heading.number}"),
                rationale=(
                    f"the <details> opened on line {opened} is never closed, so everything after "
                    f"it renders collapsed; it ends before the next H2, line {heading.number}"
                ),
                order=-100 + len(edits),  # before any section inserted at the same heading
            )
        )
    return DetectorResult(edits=tuple(edits))


@detector("stray_fence")
def stray_fence(ctx: Context) -> DetectorResult:
    """A closing code fence that closes nothing: empty its line.

    CommonMark pairs fences from the top, so one lone fence line makes everything up to the next
    fence a literal code block: the headings in it stop being headings (a Navigation anchor to
    them resolves to nothing) and a ``</details>`` in it stops closing its block. The fence is
    named only when emptying that one line alone raises the parsed heading count and leaves no
    block unclosed; a tie between lines is reported, not guessed."""
    found = _stray_fence_number(ctx.readme)
    if isinstance(found, tuple):
        first = ctx.lines[found[0] - 1]
        return DetectorResult(
            findings=(
                Finding(
                    "stray_fence",
                    first.number,
                    first.text,
                    "more than one fence line could be the stray one "
                    f"(lines {', '.join(map(str, found))}); not guessed",
                    locators=(f"{ctx.readme_path}:{first.number}",),
                ),
            )
        )
    line = _stray_fence(ctx)
    if line is None:
        return DetectorResult()
    return DetectorResult(
        edits=(
            Edit(
                kind=STRUCTURE_FIX,
                detector="stray_fence",
                start=line.start,
                end=line.end,
                original=line.text,
                replacement="",
                fact_ids=(),
                locators=(f"{ctx.readme_path}:{line.number}",),
                rationale=(
                    f"line {line.number} is a closing code fence that closes nothing; it turns "
                    "the lines after it into a code block until the next fence, so their "
                    "headings and tags are not rendered as such"
                ),
            ),
        )
    )
