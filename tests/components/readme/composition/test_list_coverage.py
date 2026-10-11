"""A list kept as written (VERIFIED_PRESERVE) states every item (composition/list_coverage.py).

The fixture is the real list from the cut-2 BC-10 triage, aspose-pdf-foss/Aspose.PDF-FOSS-for-Java
inherited_unit:131.list: a "Partially implemented today" list of six bullets that was preserved
into Scope and Limitations, where each bullet is authored into a limitation slot. The authored
section stated five of them; the sixth (`PdfFileSecurity.setAllowExceptions` throws) vanished, and
every later repair was blocked because the item names an identifier that is not a fact value.
"""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.composition.authoring import SectionTask
from repository_presenter.components.readme.composition.list_coverage import (
    list_coverage_errors,
    list_items,
    missing_items,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

UNIT = "inherited_unit:131.list"
PARTIAL = "\n".join(
    [
        "- **`PdfFileSecurity.setAllowExceptions`** throws `UnsupportedOperationException` —",
        "  the legacy `AllowExceptions=false` toolkit-key-size path is not implemented.",
        "- **Text replacement** with non-Latin scripts (CJK, Arabic, Hebrew) — basic cases",
        "  work; complex bidi reordering and shaping edge cases may differ from a reference.",
        "- **Resource optimization** — basic stream recompression works; advanced strategies",
        "  (image downsampling profiles, font merging across resources) are limited.",
        "- **Tagged PDF / logical structure** — readable, and programmatic construction of",
        "  structure trees is supported, but coverage for well-formed trees is partial.",
        "- **PDF/X validation and conversion** — `PdfFormat.PDF_X_1A` is supported through the",
        "  same `Document.validate`/`Document.convert` API used for PDF/A, but has no tests yet.",
        "- **Public-key-encrypted PDFs** are supported through the `ICustomSecurityHandler`",
        "  interface, but no out-of-the-box helper for the common cases is provided yet.",
    ]
)
AUTHORED = {
    "limitation:1": (
        "Text replacement with non-Latin scripts (CJK, Arabic, Hebrew) works for basic cases, but "
        "complex bidirectional reordering and shaping edge cases may differ from a reference."
    ),
    "limitation:2": (
        "Resource optimization supports basic stream recompression, but advanced strategies such "
        "as image downsampling profiles and font merging are limited."
    ),
    "limitation:3": (
        "Tagged PDF and logical structure support includes readable content and construction of "
        "structure trees, but coverage for building fully well-formed trees is partial."
    ),
    "limitation:4": (
        "PDF/X validation and conversion is supported through the same validate and convert API "
        "used for PDF/A, but this path has no dedicated test coverage yet."
    ),
    "limitation:5": (
        "Public-key-encrypted PDFs are supported through the ICustomSecurityHandler interface, "
        "but no out-of-the-box helper for the common cases is provided yet."
    ),
}


def _facts() -> FactsDocument:
    return FactsDocument(
        "org/Aspose.PDF-FOSS-for-Java",
        "a" * 40,
        (Fact(UNIT, "inherited_unit", PARTIAL, (Evidence("README.md", None),)),),
    )


def _dispositions(
    disposition: str = "VERIFIED_PRESERVE", section: str = "scope_limitations"
) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": UNIT,
                "disposition": disposition,
                "destination_section": section,
                "fact_ids": [],
                "rationale": "r",
            }
        ]
    }


def _task(slots: list[str], section: str = "scope_limitations") -> SectionTask:
    return SectionTask(
        section,
        {},
        frozenset({UNIT}),
        tuple(slots),
        slot_facts={slot: frozenset({UNIT}) for slot in slots},
    )


def _output(texts: dict[str, str], cited: str = UNIT) -> dict[str, Any]:
    return {
        "units": [
            {"section": "scope_limitations", "slot": slot, "text": text, "fact_ids": [cited]}
            for slot, text in texts.items()
        ],
        "omitted": [],
    }


def test_the_list_is_read_as_its_top_level_items() -> None:
    items = list_items(PARTIAL)
    assert len(items) == 6
    assert items[0].startswith("**`PdfFileSecurity.setAllowExceptions`**")
    assert "downsampling profiles" in items[2]  # a wrapped line belongs to its bullet


def test_a_dropped_item_is_named_not_merely_counted() -> None:
    """The pdf-java defect: five of six items stated, the first one gone."""
    destination = " ".join(AUTHORED.values())
    missing = missing_items(PARTIAL, destination)
    assert len(missing) == 1
    assert "setAllowExceptions" in missing[0]


def test_every_item_stated_in_other_words_is_present() -> None:
    """Negative control: the composer rewrites the items (BC-04 forbids unevidenced identifiers),
    so presence is judged on the item's subject words, not on its exact text."""
    destination = " ".join(AUTHORED.values()) + (
        " Setting allow exceptions on the file security class throws an unsupported error."
    )
    assert missing_items(PARTIAL, destination) == []


def test_the_authoring_check_refuses_a_section_that_drops_an_item() -> None:
    task = _task(list(AUTHORED))
    errors = list_coverage_errors(_output(AUTHORED), task, _dispositions(), _facts())
    assert len(errors) == 1
    assert errors[0].startswith(f"{UNIT}: list_item_missing")
    assert "setAllowExceptions" in errors[0]
    assert "limitation:1" in errors[0]  # where the item can be folded in


def test_a_section_that_states_every_item_passes() -> None:
    texts = {
        **AUTHORED,
        "limitation:6": "Setting allow exceptions on the file security class throws an error.",
    }
    task = _task(list(texts))
    assert list_coverage_errors(_output(texts), task, _dispositions(), _facts()) == []


def test_only_a_list_kept_as_written_is_held_to_every_item() -> None:
    """Negative control: a rewritten or superseded list is the composer's to condense."""
    task = _task(list(AUTHORED))
    for disposition in ("VERIFIED_REWRITE", "SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED"):
        assert (
            list_coverage_errors(_output(AUTHORED), task, _dispositions(disposition), _facts())
            == []
        )


def test_a_list_placed_in_another_section_is_not_this_sections_to_state() -> None:
    task = _task(list(AUTHORED))
    other = _dispositions(section="additional_examples")
    assert list_coverage_errors(_output(AUTHORED), task, other, _facts()) == []


def test_a_list_no_slot_of_the_section_was_given_is_not_checked() -> None:
    """Placement prints such a list as written; no authored unit stands in for it."""
    task = SectionTask("scope_limitations", {}, frozenset(), ("limitation:1",))
    assert list_coverage_errors(_output(AUTHORED), task, _dispositions(), _facts()) == []


def test_a_one_item_list_is_not_checked() -> None:
    facts = FactsDocument(
        "org/x",
        "a" * 40,
        (Fact(UNIT, "inherited_unit", "- **Only item** - it is limited.", (Evidence("R", None),)),),
    )
    task = _task(["limitation:1"])
    output = _output({"limitation:1": "Something else entirely."})
    assert list_coverage_errors(output, task, _dispositions(), facts) == []
