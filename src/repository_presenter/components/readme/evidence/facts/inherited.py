"""Inventory of the existing README as inherited units on a real CommonMark token stream.

Every top-level block of the document (heading, paragraph, badge row, list, code block, table,
HTML block, blockquote) becomes one ``inherited_unit`` fact. The value is the unit's exact source
lines, so a preserving disposition can keep it byte for byte, and the evidence names the line
range and the heading path the unit sits under. IDs are ordinal within the revision. A regex
approximation of Markdown is exactly the failure class RESEARCH_AND_GUIDELINES.md section 18.1
records; the token stream comes from markdown-it-py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token

from repository_presenter.components.readme.evidence.facts.records import Evidence, Fact, fact_id

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


@dataclass(frozen=True)
class InheritedUnit:
    """One block of the existing README, located by line range and heading path."""

    ordinal: int
    unit_type: UnitType
    source: str
    start_line: int
    end_line: int
    section: str
    heading_level: int | None = None


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


def inventory_units(readme_text: str) -> list[InheritedUnit]:
    """Every top-level block of ``readme_text`` in document order."""
    lines = readme_text.splitlines()
    tokens = _parser().parse(readme_text)
    units: list[InheritedUnit] = []
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
        if source.strip():
            units.append(
                InheritedUnit(
                    ordinal=len(units) + 1,
                    unit_type=unit_type,
                    source=source,
                    start_line=start + 1,
                    end_line=end,
                    section=section,
                    heading_level=heading_level,
                )
            )
        index = end_index + 1
    return units


def inherited_unit_facts(readme_path: str, readme_bytes: bytes) -> list[Fact]:
    """One fact per inherited unit of the README at ``readme_path``."""
    text = readme_bytes.decode("utf-8", errors="replace")
    facts = []
    for unit in inventory_units(text):
        where = f"lines {unit.start_line}-{unit.end_line}; {unit.unit_type}"
        if unit.section:
            where += f"; under {unit.section}"
        facts.append(
            Fact(
                fact_id("inherited_unit", f"{unit.ordinal:03d}.{unit.unit_type}"),
                "inherited_unit",
                unit.source,
                (Evidence(readme_path, where),),
            )
        )
    return facts
