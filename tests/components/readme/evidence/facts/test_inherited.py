"""The inherited-unit inventory: one unit per top-level block, exact source, located by lines."""

from __future__ import annotations

import itertools
import json

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts.inherited import (
    LIST_SPLIT_CHAR_THRESHOLD,
    LIST_SPLIT_CHUNK_SIZE,
    LIST_SPLIT_ITEM_THRESHOLD,
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


# Oversized-list split (docs/DECISION_LOG.md section 31; this item): a second, independent split
# for a plain list RC-06 leaves whole (no member-reference shape at all) because its own rendered
# size or item count signals it bundles many unrelated claims into one reconciliation-indivisible
# blob. Fixtures below reproduce the two real, measured shapes from the diagnosis
# (aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript's inherited_unit:014.list and 016.list - module
# docstring has the full survey) as synthetic text sized to the same scale, not the real README
# text itself (not committed to this repository).


def _catalog_bullet(n: int) -> str:
    """One capability-catalog bullet naming a single unique symbol, sized like 014.list's own
    bullets (~1,500 characters each) - many moderately-large, individually unrelated claims. The
    dotted name is a plain inline code span (``_DOTTED``'s own shape) so it round-trips exactly
    through ``identifier_tokens`` for the candidate-matching test further down."""
    filler = "covering a realistic amount of descriptive prose about this one capability. " * 18
    return f"- **Capability {n:02d}** uses `lib.doThing{n:02d}` for case {n:02d}: {filler}".rstrip()


_MANY_ITEMS_COUNT = 69  # 014.list's own measured item count (module docstring)
MANY_ITEMS_README = (
    "# Lib\n\n## Capabilities\n\n"
    + "\n".join(_catalog_bullet(n) for n in range(1, _MANY_ITEMS_COUNT + 1))
    + "\n"
)


def _verbose_bullet(label: str) -> str:
    """One individually long bullet naming several symbols at once, sized like 016.list's own
    bullets (~1,800 characters each) - few items, each one large on its own."""
    sentence = (
        f"interacts with `{label}.optionA`, `{label}.optionB`, `{label}.optionC`, and "
        f"`{label}.optionD` in a long, descriptive sentence that keeps elaborating on exactly "
        "how this one save option changes the writer's own behaviour at output time. "
    ) * 6
    return f"- **{label}** {sentence}".rstrip()


_FEW_ITEMS_COUNT = 9  # 016.list's own measured item count (module docstring)
FEW_ITEMS_README = (
    "# Lib\n\n## Save options\n\n"
    + "\n".join(_verbose_bullet(f"Mode{n}") for n in range(1, _FEW_ITEMS_COUNT + 1))
    + "\n"
)

NORMAL_LIST_README = """# Lib

## Capabilities

- Load and save documents
- Inspect pages and metadata
- Convert to common output formats
"""


def _only_list(units: list) -> list:
    return [u for u in units if u.unit_type == "list"]


def test_a_list_oversized_by_both_item_count_and_length_splits_into_fixed_chunks() -> None:
    """014.list's own shape: enough items, each large enough, to cross both thresholds at once."""
    assert len(MANY_ITEMS_README) > LIST_SPLIT_CHAR_THRESHOLD
    assert _MANY_ITEMS_COUNT > LIST_SPLIT_ITEM_THRESHOLD
    split = _only_list(inventory_units(MANY_ITEMS_README))
    expected_chunks = -(-_MANY_ITEMS_COUNT // LIST_SPLIT_CHUNK_SIZE)  # ceil division
    assert len(split) == expected_chunks
    assert [u.sub_ordinal for u in split] == list(range(1, expected_chunks + 1))
    assert all(u.ordinal == split[0].ordinal for u in split)
    # Every chunk but a possible last partial one holds exactly LIST_SPLIT_CHUNK_SIZE items.
    for unit in split[:-1]:
        assert unit.source.count("\n- ") + 1 == LIST_SPLIT_CHUNK_SIZE
    last_count = _MANY_ITEMS_COUNT - LIST_SPLIT_CHUNK_SIZE * (expected_chunks - 1)
    assert split[-1].source.count("\n- ") + 1 == last_count


def test_a_list_oversized_only_by_length_still_splits_with_few_items() -> None:
    """016.list's own shape: only 9 items (well under the item-count threshold), but each one
    long enough that the whole block clears the character threshold on its own."""
    assert len(FEW_ITEMS_README) > LIST_SPLIT_CHAR_THRESHOLD
    assert _FEW_ITEMS_COUNT < LIST_SPLIT_ITEM_THRESHOLD
    split = _only_list(inventory_units(FEW_ITEMS_README))
    expected_chunks = -(-_FEW_ITEMS_COUNT // LIST_SPLIT_CHUNK_SIZE)
    assert len(split) == expected_chunks > 1
    assert [u.sub_ordinal for u in split] == list(range(1, expected_chunks + 1))


def test_a_list_oversized_only_by_item_count_still_splits_with_few_characters() -> None:
    """Pure edge case for the OR logic's other branch: many short items whose combined length
    never crosses the character threshold, but whose item count alone crosses the item threshold."""
    item_count = LIST_SPLIT_ITEM_THRESHOLD + 5
    readme = (
        "# Lib\n\n## Tags\n\n" + "\n".join(f"- tag{n:03d}" for n in range(1, item_count + 1)) + "\n"
    )
    assert len(readme) <= LIST_SPLIT_CHAR_THRESHOLD
    assert item_count > LIST_SPLIT_ITEM_THRESHOLD
    split = _only_list(inventory_units(readme))
    expected_chunks = -(-item_count // LIST_SPLIT_CHUNK_SIZE)
    assert len(split) == expected_chunks > 1


def test_a_normal_sized_list_is_not_split_byte_for_byte() -> None:
    """Negative control: a list far under both thresholds stays exactly as it was before this
    change - one whole unit, ``sub_ordinal`` ``None``, byte-identical source."""
    original_source = (
        "- Load and save documents\n"
        "- Inspect pages and metadata\n"
        "- Convert to common output formats"
    )
    split = _only_list(inventory_units(NORMAL_LIST_README))
    assert len(split) == 1
    assert split[0].sub_ordinal is None
    assert split[0].source == original_source


def test_the_split_loses_and_duplicates_no_original_item_text() -> None:
    """Every one of the 69 catalog bullets' own unique marker appears exactly once across all
    resulting sub-units, and the chunks are contiguous (no gap, no overlap) over the original
    list's own line range."""
    units = inventory_units(MANY_ITEMS_README)
    split = _only_list(units)
    assert len(split) > 1
    joined = "\n".join(u.source for u in split)
    for n in range(1, _MANY_ITEMS_COUNT + 1):
        marker = f"Capability {n:02d}"
        assert joined.count(marker) == 1
    # Contiguous: each next chunk starts exactly one line after the previous chunk ends, and the
    # whole run covers precisely the original list's own line span (no lines dropped or repeated).
    for earlier, later in itertools.pairwise(split):
        assert later.start_line == earlier.end_line + 1
    # The whole run covers precisely the original list's own line span - computed independently
    # from the source text itself, not from any inventory_units() call, so this does not just
    # check the split against itself.
    whole_list_text = "\n".join(_catalog_bullet(n) for n in range(1, _MANY_ITEMS_COUNT + 1))
    lines_before_list = MANY_ITEMS_README.split(whole_list_text)[0].count("\n")
    expected_span = (lines_before_list + 1, lines_before_list + len(whole_list_text.splitlines()))
    assert (split[0].start_line, split[-1].end_line) == expected_span


def test_split_unit_ids_are_stable_and_collision_free() -> None:
    """Facts built from the oversized list get sequential, 1-indexed, collision-free sub-ordinal
    IDs, and re-extracting the identical text is fully deterministic (no model call involved)."""
    facts_a = inherited_unit_facts("README.md", MANY_ITEMS_README.encode("utf-8"))
    facts_b = inherited_unit_facts("README.md", MANY_ITEMS_README.encode("utf-8"))
    assert facts_a == facts_b
    list_ids = [f.id for f in facts_a if f.kind == "inherited_unit" and f.id.endswith(".list")]
    assert len(list_ids) == len(set(list_ids))  # collision-free
    expected_chunks = -(-_MANY_ITEMS_COUNT // LIST_SPLIT_CHUNK_SIZE)
    ordinal = list_ids[0].split(":")[1].split(".")[0]
    assert list_ids == [
        f"inherited_unit:{ordinal}.{i:03d}.list" for i in range(1, expected_chunks + 1)
    ]

    document = FactsDocument("o/Lib-FOSS-for-Python", "a" * 40, tuple(facts_a))
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []


def test_oversized_split_never_fires_when_rc06_already_split_the_list() -> None:
    """RC-06's member-reference split is tried first; a list it splits per-bullet never also
    goes through the oversized-list chunker, even when the whole block is itself large enough
    (by item count) to qualify for the oversized split on its own."""
    item_count = LIST_SPLIT_ITEM_THRESHOLD + 5  # over the item threshold by itself
    many_symbols = [f"Symbol{n:02d}" for n in range(1, item_count + 1)]
    readme = (
        "# Lib\n\n## API\n\n"
        + "\n".join(
            f"- `{name}` is a class used throughout this library's own API surface."
            for name in many_symbols
        )
        + "\n"
    )
    assert len(many_symbols) > LIST_SPLIT_ITEM_THRESHOLD
    units = inventory_units(readme, known_class_enum_names=frozenset(many_symbols))
    split = _only_list(units)
    # RC-06 splits one unit per bullet, never the fixed-chunk-size grouping the oversized-list
    # path would have produced (ceil(item_count / LIST_SPLIT_CHUNK_SIZE)) for the identical text.
    assert len(split) == len(many_symbols)
    assert len(split) != -(-item_count // LIST_SPLIT_CHUNK_SIZE)
    assert [u.sub_ordinal for u in split] == list(range(1, len(many_symbols) + 1))


def test_an_oversized_list_reduces_the_uncited_omit_candidate_count_per_sub_unit() -> None:
    """Demonstrates the actual fix for the PDF-TypeScript diagnosis (PR #1008) using the existing
    deterministic candidate-surfacing function, no live reconciliation call needed: a disposition
    refusal's re-ask names every SUPPORTED symbol the refused unit's own text spells
    (``uncited_omit_candidates``). Against the whole, unsplit 69-bullet unit this list names every
    one of the 69 symbols at once - the exact "candidate list bound to one giant unit" shape the
    diagnosis named. Once split, each sub-unit's own candidate count drops to at most
    ``LIST_SPLIT_CHUNK_SIZE``, so the re-ask the model receives for any one disposition is always
    small enough to act on inline.
    """
    from repository_presenter.components.readme.reconciliation.dispositions import (
        uncited_omit_candidates,
    )

    symbol_facts = tuple(
        Fact(
            fact_id("public_symbol", f"lib.doThing{n:02d}"),
            "public_symbol",
            f"lib.doThing{n:02d}",
            (Evidence("src/x.ts"),),
            attributes={"symbol_kind": "function"},
        )
        for n in range(1, _MANY_ITEMS_COUNT + 1)
    )
    facts = FactsDocument("o/Lib-FOSS-for-TypeScript", "a" * 40, symbol_facts)

    # "Before": the whole, unsplit list text, built independently of inventory_units() - the
    # exact 69-claim blob the real diagnosis hit.
    whole_list_text = "\n".join(_catalog_bullet(n) for n in range(1, _MANY_ITEMS_COUNT + 1))
    before = uncited_omit_candidates(whole_list_text, facts)
    assert len(before) == _MANY_ITEMS_COUNT  # every symbol named at once - the overload shape

    # "After": each of this change's own sub-units, taken straight from inventory_units().
    split = _only_list(inventory_units(MANY_ITEMS_README))
    assert len(split) > 1
    for unit in split:
        after = uncited_omit_candidates(unit.source, facts)
        assert 0 < len(after) <= LIST_SPLIT_CHUNK_SIZE
