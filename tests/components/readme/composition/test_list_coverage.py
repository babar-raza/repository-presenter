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
    item_links,
    list_coverage_errors,
    list_items,
    missing_items,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from support import JAVA3D_DOCS_LIST, JAVA3D_SCOPE_LIST

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


def _dispositions_for(
    unit: str, disposition: str = "VERIFIED_PRESERVE", section: str = "scope_limitations"
) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": unit,
                "disposition": disposition,
                "destination_section": section,
                "fact_ids": [],
                "rationale": "r",
            }
        ]
    }


# --- LST-01: the wave-3 candidates (reseal f69f75c7), from their sealed bundles -------------------
# 3D Java 3d2ed6be: the Scope list (nine bullets) was dropped by placement because ONE fact it cites
# is covered by a limitation slot; the composer stated six of its bullets and neither the plan nor
# any check owed it the other three. These are the six units the sealed candidate authored.
JAVA3D_UNIT = "inherited_unit:072.list"
JAVA3D_AUTHORED = {
    "scope": (
        "Aspose.3D FOSS for Java provides a Java library for working with 3D scenes, with full "
        "support for STL import and export in the published 26.5.0 package; it targets Java 21 "
        "and is distributed under the MIT license as open-source software."
    ),
    "limitation:1": (
        "The only fully functional format in the published 26.5.0 package is STL (import and "
        "export); other formats have recognized options classes registered with FileFormat but "
        "no working load/save path in that package."
    ),
    "limitation:2": (
        "OBJ import has a working parser in the upstream GitHub source but the currently "
        "published Maven Central artifact ships a stub there, so OBJ import is not reliable from "
        "the published package."
    ),
    "limitation:3": (
        "Several recognized-but-unfinished formats fail silently rather than throwing an error, "
        "so loading or saving through them can return successfully while producing no real data."
    ),
    "limitation:4": "Additional format coverage beyond STL is a higher-tier offering.",
    "limitation:5": (
        "A handful of primitive-shape classes have a mesh-conversion method that is present but "
        "not yet implemented; Box, Cylinder, Sphere, and Dish are confirmed to convert correctly."
    ),
    "limitation:6": "Scene rendering is not implemented in this edition.",
}
JAVA3D_SLOTS = [slot for slot in JAVA3D_AUTHORED if slot.startswith("limitation:")]


def _java3d_facts() -> FactsDocument:
    return FactsDocument(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "3" * 40,
        (Fact(JAVA3D_UNIT, "inherited_unit", JAVA3D_SCOPE_LIST, (Evidence("README.md", None),)),),
    )


def _java3d_task(handed: bool = True) -> SectionTask:
    return SectionTask(
        "scope_limitations",
        {},
        frozenset({JAVA3D_UNIT}),
        ("scope", *JAVA3D_SLOTS),
        slot_facts={slot: frozenset({JAVA3D_UNIT}) for slot in JAVA3D_SLOTS} if handed else {},
    )


def _java3d_output(texts: dict[str, str], cited: list[str]) -> dict[str, Any]:
    return {
        "units": [
            {
                "section": "scope_limitations",
                "slot": slot,
                "text": text,
                "fact_ids": cited if slot == "scope" else [],
            }
            for slot, text in texts.items()
        ],
        "omitted": [],
    }


def test_the_scope_list_3d_java_lost_three_bullets_from_is_refused_with_them_named() -> None:
    """The sealed candidate's six units state six of the nine bullets. The three it lost are the
    ones the independent acceptance review found missing (PbrSpecularMaterial; the NurbsCurve
    sampling limit; the licensing, trial and ZIP exclusions)."""
    errors = list_coverage_errors(
        _java3d_output(JAVA3D_AUTHORED, [JAVA3D_UNIT]),
        _java3d_task(),
        _dispositions_for(JAVA3D_UNIT),
        _java3d_facts(),
    )
    assert len(errors) == 1 and errors[0].startswith(f"{JAVA3D_UNIT}: list_item_missing")
    assert "NurbsCurve" in errors[0] and "PbrSpecularMaterial" in errors[0]
    assert "9 items" in errors[0]


def test_a_list_nobody_cited_is_still_owed_in_full() -> None:
    """The earlier guard skipped a list no unit cited; a composer that states six of nine bullets
    without citing the list passed it."""
    errors = list_coverage_errors(
        _java3d_output(JAVA3D_AUTHORED, []),
        _java3d_task(),
        _dispositions_for(JAVA3D_UNIT),
        _java3d_facts(),
    )
    assert len(errors) == 1 and "PbrSpecularMaterial" in errors[0]
    assert "limitation:1" in errors[0]  # the slots the plan bound the list to


def test_a_scope_section_that_states_all_nine_bullets_passes() -> None:
    texts = {
        **JAVA3D_AUTHORED,
        "limitation:6": (
            "Scene rendering is not implemented in this edition. NurbsCurve sampling points "
            "along the curve is not yet implemented. The PbrSpecularMaterial accessors are "
            "unimplemented. Licensing, trial and DRM functionality, cryptographic helpers and "
            "ZIP file-system read and write are excluded from the FOSS edition."
        ),
    }
    assert (
        list_coverage_errors(
            _java3d_output(texts, [JAVA3D_UNIT]),
            _java3d_task(),
            _dispositions_for(JAVA3D_UNIT),
            _java3d_facts(),
        )
        == []
    )


def test_a_list_the_plan_never_handed_to_a_slot_is_not_owed_here() -> None:
    """Negative control: placement prints it whole, so no authored unit stands in for it; and a
    one-item list is not a list."""
    errors = list_coverage_errors(
        _java3d_output(JAVA3D_AUTHORED, []),
        _java3d_task(handed=False),
        _dispositions_for(JAVA3D_UNIT),
        _java3d_facts(),
    )
    assert errors == []


# 3D .NET 52b0f00e: the development dependencies list was moved into Development and Testing,
# dropped by placement (it cites build_test_asset:tests, which the section prints itself), and the
# one summary unit authored there stated neither package.
DOTNET3D_UNIT = "inherited_unit:021.list"
DOTNET3D_DEV_DEPS = "\n".join(
    [
        "- `Microsoft.NET.Test.Sdk` (17.12.0), `xunit` (2.9.2), and `xunit.runner.visualstudio` "
        "(2.8.2) — the test framework and runner used by the test suite (see",
        "  [Development and Testing](#development-and-testing)).",
        "- `coverlet.collector` (6.0.2) — code-coverage collection for the test suite.",
    ]
)
DOTNET3D_SUMMARY = (
    "Aspose.3D FOSS for .NET targets netcoreapp3.1, net6.0, net8.0, and net10.0 frameworks and "
    "uses the xunit testing framework for its test suite located under src/test/. The test suite "
    "includes code-coverage collection, and contributors must follow the guidelines in AGENTS.md "
    "for current implementation status and development rules."
)


def test_an_unbound_section_owes_the_list_placement_dropped_from_it() -> None:
    facts = FactsDocument(
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        "5" * 40,
        (Fact(DOTNET3D_UNIT, "inherited_unit", DOTNET3D_DEV_DEPS, (Evidence("README.md", None),)),),
    )
    task = SectionTask(
        "development_testing",
        {},
        frozenset({DOTNET3D_UNIT}),
        ("summary",),
        owed_lists=frozenset({DOTNET3D_UNIT}),
    )
    dispositions = _dispositions_for(DOTNET3D_UNIT, "VERIFIED_MOVE", "development_testing")
    output = {
        "units": [
            {
                "section": "development_testing",
                "slot": "summary",
                "text": DOTNET3D_SUMMARY,
                "fact_ids": [DOTNET3D_UNIT],
            }
        ],
        "omitted": [],
    }
    # The sealed summary mentions code-coverage collection, which the list's second item is about;
    # a summary that does not is refused with that item named.
    assert list_coverage_errors(output, task, dispositions, facts) == []
    silent = {
        **output["units"][0],
        "text": DOTNET3D_SUMMARY.replace(
            "The test suite includes code-coverage collection, and ", ""
        ),
    }
    output = {"units": [silent], "omitted": []}
    errors = list_coverage_errors(output, task, dispositions, facts)
    assert len(errors) == 1 and "coverlet.collector" in errors[0]
    assert "xunit.runner.visualstudio" not in errors[0]  # that item's subject, xunit, is stated
    stated = {
        **output["units"][0],
        "text": DOTNET3D_SUMMARY
        + " It uses coverlet.collector for coverage and Microsoft.NET.Test.Sdk.",
    }
    assert list_coverage_errors({"units": [stated], "omitted": []}, task, dispositions, facts) == []
    # Negative control: the same section without the owed marker is not held to the list.
    unmarked = SectionTask("development_testing", {}, frozenset({DOTNET3D_UNIT}), ("summary",))
    assert list_coverage_errors(output, unmarked, dispositions, facts) == []


# 3D Java 3d2ed6be: Documentation and Resources prints one authored line per planned link; the plan
# carried four of the eight links the list cites, and the list's lead words ("guide", "notes") are
# too common to tell one link from another.
JAVA3D_DOCS_SECTION = "\n".join(
    [
        "- **[Getting started guide](https://docs.aspose.org/3d/java/)** — The getting "
        "started guide covers installation, walkthroughs, and feature guides.",
        "- **[How-to guides & FAQ](https://kb.aspose.org/3d/java/)** — The how-to guides.",
        "- **[Full API reference](https://reference.aspose.org/3d/java/)** — The full API "
        "reference offers the complete, browsable reference for all 266 public types.",
        "- Found a bug or have a feature request? [Open an issue]"
        "(https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java/issues).",
    ]
)


def test_a_documentation_item_is_stated_when_its_link_is_printed() -> None:
    by_lead = missing_items(JAVA3D_DOCS_LIST, JAVA3D_DOCS_SECTION)
    by_link = missing_items(
        JAVA3D_DOCS_LIST, JAVA3D_DOCS_SECTION, by_link=True, document_text=JAVA3D_DOCS_SECTION
    )
    # The four repository documents are the ones lost; by lead words alone "guide" and "notes"
    # make some of them look present.
    assert [item.split("](")[1].split(")")[0] for item in by_link] == [
        "PUBLISHING.md",
        "docs/api-diff-26.1.0.md",
        "docs/directory-structures.md",
        "docs/foss-java-progress.md",
    ]
    assert len(by_lead) < len(by_link)
    printed = (
        JAVA3D_DOCS_SECTION
        + "\n"
        + "\n".join(f"- [x]({link})" for link in ("PUBLISHING.md", "docs/api-diff-26.1.0.md"))
    )
    assert len(missing_items(JAVA3D_DOCS_LIST, printed, by_link=True, document_text=printed)) == 2
    # An in-page anchor is no document link: that item falls back to its subject words.
    assert item_links("- **[API reference](#api-reference)** — the essentials.") == []
