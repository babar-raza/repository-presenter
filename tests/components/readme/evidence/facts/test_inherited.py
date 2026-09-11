"""The inherited-unit inventory: one unit per top-level block, exact source, located by lines."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts.inherited import (
    inherited_unit_facts,
    inventory_units,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id
from support import REPO_ROOT

README = """# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An open-source 3D file format library.

## Installation

```bash
pip install aspose-3d-foss
```

## Key capabilities

- Load and save **FBX**, glTF, and STL
  - nested detail line
- Build scenes programmatically

| Format | Read | Write |
|---|---|---|
| FBX | yes | yes |

<details>
<summary>More</summary>
</details>

> A quote about the library.

### Scene graph (`aspose.threed`)

Nodes form a tree. See `Scene`.

---

## License

MIT
"""


def test_every_top_level_block_becomes_one_unit_in_order() -> None:
    units = inventory_units(README)
    assert [(u.ordinal, u.unit_type) for u in units] == [
        (1, "heading"),
        (2, "badge_row"),
        (3, "paragraph"),
        (4, "heading"),
        (5, "code_block"),
        (6, "heading"),
        (7, "list"),
        (8, "table"),
        (9, "html_block"),
        (10, "blockquote"),
        (11, "heading"),
        (12, "paragraph"),
        (13, "heading"),
        (14, "paragraph"),
    ]


def test_units_carry_exact_source_lines_and_heading_paths() -> None:
    units = {u.ordinal: u for u in inventory_units(README)}
    assert units[1].source == "# Aspose.3D FOSS for Python"
    assert (units[1].heading_level, units[1].section) == (1, "")
    assert units[2].source.startswith("[![PyPI](https://img.shields.io")
    assert units[5].source == "```bash\npip install aspose-3d-foss\n```"
    assert (units[5].start_line, units[5].end_line) == (10, 12)
    assert units[5].section == "Aspose.3D FOSS for Python > Installation"
    assert units[7].source == (
        "- Load and save **FBX**, glTF, and STL\n"
        "  - nested detail line\n"
        "- Build scenes programmatically"
    )
    assert (units[7].start_line, units[7].end_line) == (16, 18)
    assert units[8].source.startswith("| Format | Read | Write |")
    assert units[9].source == "<details>\n<summary>More</summary>\n</details>"
    assert units[10].source == "> A quote about the library."
    assert units[11].section == "Aspose.3D FOSS for Python > Key capabilities"
    assert (
        units[12].section
        == "Aspose.3D FOSS for Python > Key capabilities > Scene graph (`aspose.threed`)"
    )
    assert units[13].section == "Aspose.3D FOSS for Python"
    assert units[14].source == "MIT"


def test_a_paragraph_with_prose_and_an_image_is_not_a_badge_row() -> None:
    units = inventory_units("![logo](logo.png) The library logo above.\n")
    assert [u.unit_type for u in units] == ["paragraph"]
    units = inventory_units("![a](a.svg)\n![b](b.svg)\n")
    assert [u.unit_type for u in units] == ["badge_row"]


def test_crlf_and_empty_documents_are_handled() -> None:
    units = inventory_units("# Title\r\n\r\nText line.\r\n")
    assert [(u.unit_type, u.source) for u in units] == [
        ("heading", "# Title"),
        ("paragraph", "Text line."),
    ]
    assert inventory_units("") == []
    assert inventory_units("\n\n---\n\n") == []


def test_facts_are_stable_ordinal_ids_with_located_evidence() -> None:
    facts = inherited_unit_facts("README.md", README.encode("utf-8"))
    assert [f.id for f in facts][:3] == [
        "inherited_unit:001.heading",
        "inherited_unit:002.badge_row",
        "inherited_unit:003.paragraph",
    ]
    code = next(f for f in facts if f.id == "inherited_unit:005.code_block")
    assert code.value == "```bash\npip install aspose-3d-foss\n```"
    assert code.evidence[0].path == "README.md"
    assert code.evidence[0].detail == (
        "lines 10-12; code_block; under Aspose.3D FOSS for Python > Installation"
    )
    # PHASE0/G's own prerequisite: .section is now structured too, not only free text above -
    # the same value, available to a consumer (reconciliation batching) without parsing prose.
    assert code.attributes == {"section": "Aspose.3D FOSS for Python > Installation"}
    heading = next(f for f in facts if f.id == "inherited_unit:001.heading")
    assert heading.attributes is None  # the document's own H1 has no ancestor section
    assert inherited_unit_facts("README.md", README.encode("utf-8")) == facts

    document = FactsDocument("o/Aspose.X-FOSS-for-Go", "a" * 40, tuple(facts))
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []


# RC-06: a member-reference list - every top-level bullet opens on a backtick-quoted identifier
# naming a known class/enum symbol - splits into one unit per bullet. Shapes below mirror real
# production content found on the portfolio's own sealed candidates (docs/DECISION_LOG.md,
# 2026-09-10): nested method sub-bullets, an inline no-children bullet, a multi-identifier
# bullet, a feature-list near-miss (most but not every bullet matches), and - the most important
# regression guard - a bare category-label bullet ("- Exceptions") whose own *nested* children
# are real class names but which itself does not open on one, matching Aspose.Cells FOSS for
# C++'s real inherited_unit:050.list exactly.
MEMBER_LIST_README = """# Example FOSS for Python

## API Reference

### High-level API

- `MapiMessage`
  - `create(subject, body) -> "MapiMessage"`
  - `from_file(path, strict) -> "MapiMessage"`
- `MapiAttachment`
  - `from_bytes(data) -> "MapiAttachment"`

### Storage errors

- `CFBError`
- `MsgError`

### Property identifiers

- `CommonMessagePropertyId` / `PropertyId` - common MAPI property identifiers (`SUBJECT`)
- `CFBError` - raised for malformed compound file binary containers

### Feature overview

- `CFBStorage` is used to build and write containers
- Read and write Outlook `.msg` files end to end
- Parse attachments without loading the whole message

### Exception types

- `Workbook`
  - `Workbook()`
- `PageSetup`
  - `PageSetup()`
- Exceptions
  - `CellsException` - base error type for invalid indices and arguments
  - `WorkbookLoadException` - raised when a load fails

### Lone mention

- `Widget`
  - has exactly one nested detail line
"""


def _symbol(value: str, kind: str = "class") -> Fact:
    return Fact(
        fact_id("public_symbol", value),
        "public_symbol",
        value,
        (Evidence("src/x.py"),),
        attributes={"symbol_kind": kind},
    )


KNOWN_SYMBOLS = [
    "example_foss.MapiMessage",
    "example_foss.MapiAttachment",
    "example_foss.CFBError",
    "example_foss.MsgError",
    "example_foss.CommonMessagePropertyId",
    "example_foss.PropertyId",
    "example_foss.CFBStorage",
    "example_foss.Workbook",
    "example_foss.PageSetup",
    "example_foss.Widget",
]
KNOWN_NAMES = frozenset(name.rsplit(".", 1)[-1] for name in KNOWN_SYMBOLS)


def _units_by_section(units: list, heading: str) -> list:
    return [u for u in units if u.section.endswith(heading)]


def test_a_nested_member_reference_list_splits_one_unit_per_bullet() -> None:
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    split = _units_by_section(units, "High-level API")
    assert [(u.ordinal, u.sub_ordinal, u.unit_type) for u in split] == [
        (4, 1, "list"),
        (4, 2, "list"),
    ]
    assert split[0].source == (
        '- `MapiMessage`\n  - `create(subject, body) -> "MapiMessage"`\n'
        '  - `from_file(path, strict) -> "MapiMessage"`'
    )
    assert split[1].source == '- `MapiAttachment`\n  - `from_bytes(data) -> "MapiAttachment"`'


def test_an_inline_no_children_member_reference_list_splits() -> None:
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    split = _units_by_section(units, "Storage errors")
    assert [(u.sub_ordinal, u.source) for u in split] == [
        (1, "- `CFBError`"),
        (2, "- `MsgError`"),
    ]


def test_a_multi_identifier_bullet_splits_as_one_whole_bullet_not_per_symbol() -> None:
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    split = _units_by_section(units, "Property identifiers")
    assert [u.sub_ordinal for u in split] == [1, 2]
    assert "`CommonMessagePropertyId`" in split[0].source
    assert "`PropertyId`" in split[0].source
    assert split[1].source == (
        "- `CFBError` - raised for malformed compound file binary containers"
    )


def test_a_feature_list_where_not_every_bullet_matches_does_not_split() -> None:
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    whole = _units_by_section(units, "Feature overview")
    assert len(whole) == 1
    assert whole[0].sub_ordinal is None
    assert whole[0].source.count("\n") == 2


def test_a_bare_category_label_bullet_blocks_the_split_even_with_real_siblings() -> None:
    """The single most important regression guard: Aspose.Cells FOSS for C++'s real
    inherited_unit:050.list has 15 of 16 bullets cleanly matching and one bare "- Exceptions"
    label bullet whose nested children are real class names. Every bullet must match, not most -
    this unit must stay whole, not split on the 3 bullets that do qualify."""
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    whole = _units_by_section(units, "Exception types")
    assert len(whole) == 1
    assert whole[0].sub_ordinal is None


def test_a_plain_unrelated_list_is_unaffected_by_known_symbol_names() -> None:
    units = inventory_units(README, frozenset({"Scene"}))
    lists = [u for u in units if u.unit_type == "list"]
    assert len(lists) == 1
    assert lists[0].sub_ordinal is None
    assert lists[0].source.startswith("- Load and save **FBX**")


def test_a_single_bullet_list_never_splits_even_when_it_matches() -> None:
    units = inventory_units(MEMBER_LIST_README, KNOWN_NAMES)
    whole = _units_by_section(units, "Lone mention")
    assert len(whole) == 1
    assert whole[0].sub_ordinal is None
    assert whole[0].source.startswith("- `Widget`")


def test_split_units_are_deterministic_and_schema_valid() -> None:
    facts_a = inherited_unit_facts(
        "README.md", MEMBER_LIST_README.encode("utf-8"), [_symbol(v) for v in KNOWN_SYMBOLS]
    )
    facts_b = inherited_unit_facts(
        "README.md", MEMBER_LIST_README.encode("utf-8"), [_symbol(v) for v in KNOWN_SYMBOLS]
    )
    assert facts_a == facts_b
    split_ids = [f.id for f in facts_a if f.id.startswith("inherited_unit:004.")]
    assert split_ids == ["inherited_unit:004.001.list", "inherited_unit:004.002.list"]

    document = FactsDocument("o/Example-FOSS-for-Python", "a" * 40, tuple(facts_a))
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []


def test_a_split_unit_id_round_trips_through_fact_id() -> None:
    assert fact_id("inherited_unit", "053.001.list") == "inherited_unit:053.001.list"
