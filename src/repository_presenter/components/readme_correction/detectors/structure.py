"""Markup the README shows broken, fixed by the smallest edit that restores it.

Two defects measured on live portfolio READMEs (Aspose.Cells for Go): a second H1 (the template
has exactly one) and a ``<details>`` block opened and never closed, which makes every section after
it - Detailed Documentation, Constraints, License - render collapsed. Neither needs a fact: the
README's own text is the evidence, recorded as a ``README.md:<line>`` locator, and each fix is one
character run (a heading marker, or one closing tag in front of the next H2).
"""

from __future__ import annotations

import re

from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    STRUCTURE_FIX,
    Context,
    DetectorResult,
    Edit,
)

NL = chr(10)
_H1 = re.compile(r"^#(?!#)[ \t]+\S")
_H2 = re.compile(r"^##(?!#)[ \t]+\S")
_OPEN = re.compile(r"<details\b", re.IGNORECASE)
_CLOSE = re.compile(r"</details\s*>", re.IGNORECASE)
_CODE_SPAN = re.compile(r"`[^`]*`")


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

    An H2 inside a collapsed block is a section heading that the block was never meant to hold,
    so the first one after the opening tag is where the block ends. No H2 after it: reported by
    leaving the README as written (an unclosed block at the very end hides nothing)."""
    stack: list[int] = []  # line numbers of the openings not yet closed
    for line in ctx.lines:
        if line.in_fence:
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
                if line.number > opened and not line.in_fence and _H2.match(line.text)
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
