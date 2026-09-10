"""Inventory of the existing README as inherited units on a real CommonMark token stream.

Every top-level block of the document (heading, paragraph, badge row, list, code block, table,
HTML block, blockquote) becomes one ``inherited_unit`` fact. The value is the unit's exact source
lines, so a preserving disposition can keep it byte for byte, and the evidence names the line
range and the heading path the unit sits under. IDs are ordinal within the revision. A regex
approximation of Markdown is exactly the failure class RESEARCH_AND_GUIDELINES.md section 18.1
records; the token stream comes from markdown-it-py.

RC-06 (plans/healing/production-consistency-reassessment.md): a "member reference list" - a
bulleted list whose every top-level bullet names one known class/enum symbol in a leading
backtick-quoted identifier - is split into one unit per bullet instead of one unit for the whole
list. Reconciliation could not safely dispose these as one blob: the real, sealed Email-Python
transaction showed every such unit cited only a coarse module/package-level symbol, never the
individual classes its own text names, which is exactly why the list survived as a verbatim
duplicate of the deterministic Core API table. Splitting moves the fix upstream, to the input
grain, rather than trying to read a finer citation out of an indivisible blob (see
docs/RECONCILIATION_COVERAGE_ASSESSMENT.md for two reconciliation-time attempts that were tried
and reverted for exactly this reason). The split is deliberately conservative: it requires EVERY
top-level bullet to match, not "most" - a list with one bare category-label bullet (real example:
Aspose.Cells FOSS for C++'s "- Exceptions" heading a nested group of real exception names) is left
whole rather than guessed at, matching this project's own repeated finding that a heuristic which
looks right on the one candidate that motivated it must be checked against the whole portfolio
(and erring toward under-triggering) before it can be trusted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token

from repository_presenter.core.facts import Evidence, Fact, fact_id

UnitType = Literal[
    "heading",
    "paragraph",
    "badge_row",
    "list",
    "code_block",
    "table",
    "html_block",
    "blockquote",
]

_BLOCK_TYPES: dict[str, UnitType] = {
    "heading_open": "heading",
    "paragraph_open": "paragraph",
    "bullet_list_open": "list",
    "ordered_list_open": "list",
    "fence": "code_block",
    "code_block": "code_block",
    "table_open": "table",
    "html_block": "html_block",
    "blockquote_open": "blockquote",
}
_BADGE_CHILD_TYPES = frozenset({"link_open", "link_close", "image", "softbreak", "text"})
_LEADING_IDENTIFIER = re.compile(r"^`([A-Za-z_][A-Za-z0-9_]*)`")

# New constant (RC-06, plans/healing/production-consistency-reassessment.md), not a bump of an
# existing one: bumped whenever this module's own inventory/splitting logic changes, the same
# convention EXTRACTOR_VERSION (extractors/surface/extractor.py) uses for its own, separate
# domain - kept distinct rather than overloaded onto that constant because the two modules'
# logic changes independently. dependencies.json's environment class records it, so a sealed
# candidate from before this field existed (a missing key, never "1") correctly reopens
# EXTRACTING the first time this ships, the same as any other environment field's change would
# (docs/STATE_MACHINE.md section 9).
INHERITED_UNITS_VERSION = "1"


@dataclass(frozen=True)
class InheritedUnit:
    """One block of the existing README, located by line range and heading path.

    ``sub_ordinal`` is ``None`` for an ordinary unit. A member-reference-list bullet split out of
    a larger list block (RC-06) shares its parent block's own ``ordinal`` and carries a distinct,
    1-indexed ``sub_ordinal`` instead - the block's position among top-level blocks never shifts,
    and no other unit in the document is renumbered, however many pieces one block expands into.
    """

    ordinal: int
    unit_type: UnitType
    source: str
    start_line: int
    end_line: int
    section: str
    heading_level: int | None = None
    sub_ordinal: int | None = None


def _parser() -> MarkdownIt:
    return MarkdownIt("commonmark").enable(["table", "strikethrough"])


def _is_badge_row(inline: Token) -> bool:
    children = inline.children or []
    has_image = any(child.type == "image" for child in children)
    only_badge_parts = all(
        child.type in _BADGE_CHILD_TYPES and (child.type != "text" or not child.content.strip())
        for child in children
    )
    return has_image and only_badge_parts


def _block_end(tokens: list[Token], start: int) -> int:
    """Index of the token that closes the block opened at ``start`` (or ``start`` itself)."""
    depth = 0
    for index in range(start, len(tokens)):
        depth += tokens[index].nesting
        if depth == 0:
            return index
    return len(tokens) - 1


def _list_items(tokens: list[Token], list_open: int, list_close: int) -> list[tuple[int, int]]:
    """(open, close) token-index pairs of each direct ``list_item_open``/``_close`` inside a
    list block - siblings only, never reaching into a nested sub-list's own items."""
    items: list[tuple[int, int]] = []
    index = list_open + 1
    while index < list_close:
        if tokens[index].type == "list_item_open":
            end = _block_end(tokens, index)
            items.append((index, end))
            index = end + 1
        else:
            index += 1
    return items


def _item_leading_identifier(tokens: list[Token], item_open: int, item_close: int) -> str | None:
    """The backtick-quoted identifier opening this item's own text, if that is how it starts -
    never looking inside a nested sub-list, only the item's own first inline content."""
    for index in range(item_open + 1, item_close):
        if tokens[index].type == "inline":
            match = _LEADING_IDENTIFIER.match(tokens[index].content)
            return match.group(1) if match else None
        if tokens[index].type in ("bullet_list_open", "ordered_list_open"):
            return None
    return None


def _item_line_range(tokens: list[Token], item_open: int, item_close: int) -> tuple[int, int]:
    """The source line span covering a list item's own content, nested children included."""
    maps = [m for i in range(item_open, item_close + 1) if (m := tokens[i].map) is not None]
    return min(m[0] for m in maps), max(m[1] for m in maps)


def _split_member_reference_list(
    tokens: list[Token],
    list_open: int,
    list_close: int,
    lines: list[str],
    known_class_enum_names: frozenset[str],
) -> list[tuple[int, int]] | None:
    """If every top-level bullet of this list opens on a known class/enum identifier, the
    (start_line, end_line) 0-indexed span of each bullet; ``None`` if the shape does not match
    (fewer than two bullets, or any bullet that does not qualify) - the list stays one unit."""
    items = _list_items(tokens, list_open, list_close)
    if len(items) < 2:
        return None
    spans: list[tuple[int, int]] = []
    for item_open, item_close in items:
        identifier = _item_leading_identifier(tokens, item_open, item_close)
        if identifier is None or identifier not in known_class_enum_names:
            return None
        start, end = _item_line_range(tokens, item_open, item_close)
        while end > start and not lines[end - 1].strip():
            end -= 1
        spans.append((start, end))
    return spans


def inventory_units(
    readme_text: str, known_class_enum_names: Iterable[str] = frozenset()
) -> list[InheritedUnit]:
    """Every top-level block of ``readme_text`` in document order, splitting a member-reference
    list into one unit per bullet when every bullet names a known class/enum symbol (RC-06)."""
    known = frozenset(known_class_enum_names)
    lines = readme_text.splitlines()
    tokens = _parser().parse(readme_text)
    units: list[InheritedUnit] = []
    block_ordinal = 0
    heading_path: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        unit_type = _BLOCK_TYPES.get(token.type)
        end_index = _block_end(tokens, index) if token.nesting == 1 else index
        if unit_type is None or token.map is None:
            index = end_index + 1
            continue
        start, end = token.map
        while end > start and not lines[end - 1].strip():
            end -= 1
        source = "\n".join(lines[start:end])
        heading_level: int | None = None
        if unit_type == "heading":
            heading_level = int(token.tag[1])
            heading_text = tokens[index + 1].content.strip()
            del heading_path[heading_level - 1 :]
            heading_path.extend([""] * (heading_level - 1 - len(heading_path)))
            heading_path.append(heading_text)
            section = " > ".join(part for part in heading_path[:-1] if part)
        else:
            section = " > ".join(part for part in heading_path if part)
            if unit_type == "paragraph" and _is_badge_row(tokens[index + 1]):
                unit_type = "badge_row"
        if not source.strip():
            index = end_index + 1
            continue
        block_ordinal += 1
        split_spans = (
            _split_member_reference_list(tokens, index, end_index, lines, known)
            if unit_type == "list" and known
            else None
        )
        if split_spans is None:
            units.append(
                InheritedUnit(
                    ordinal=block_ordinal,
                    unit_type=unit_type,
                    source=source,
                    start_line=start + 1,
                    end_line=end,
                    section=section,
                    heading_level=heading_level,
                )
            )
        else:
            for sub_ordinal, (bullet_start, bullet_end) in enumerate(split_spans, start=1):
                units.append(
                    InheritedUnit(
                        ordinal=block_ordinal,
                        unit_type=unit_type,
                        source="\n".join(lines[bullet_start:bullet_end]),
                        start_line=bullet_start + 1,
                        end_line=bullet_end,
                        section=section,
                        heading_level=heading_level,
                        sub_ordinal=sub_ordinal,
                    )
                )
        index = end_index + 1
    return units


def _known_class_enum_names(public_symbol_facts: Sequence[Fact]) -> frozenset[str]:
    return frozenset(
        fact.value.rsplit(".", 1)[-1]
        for fact in public_symbol_facts
        if fact.polarity == "SUPPORTED"
        and (fact.attributes or {}).get("symbol_kind") in ("class", "enum")
    )


def inherited_unit_facts(
    readme_path: str, readme_bytes: bytes, public_symbol_facts: Sequence[Fact] = ()
) -> list[Fact]:
    """One fact per inherited unit of the README at ``readme_path``."""
    text = readme_bytes.decode("utf-8", errors="replace")
    known = _known_class_enum_names(public_symbol_facts)
    facts = []
    for unit in inventory_units(text, known):
        where = f"lines {unit.start_line}-{unit.end_line}; {unit.unit_type}"
        if unit.section:
            where += f"; under {unit.section}"
        key = (
            f"{unit.ordinal:03d}.{unit.unit_type}"
            if unit.sub_ordinal is None
            else f"{unit.ordinal:03d}.{unit.sub_ordinal:03d}.{unit.unit_type}"
        )
        facts.append(
            Fact(
                fact_id("inherited_unit", key),
                "inherited_unit",
                unit.source,
                (Evidence(readme_path, where),),
            )
        )
    return facts
