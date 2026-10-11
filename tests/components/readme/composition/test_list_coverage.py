"""The item test for a list kept as written (composition/list_coverage.py).

The first fixture is the real list from the cut-2 BC-10 triage, aspose-pdf-foss/Aspose.PDF-FOSS-for-
Java inherited_unit:131.list: a "Partially implemented today" list of six bullets that was preserved
into Scope and Limitations, where each bullet is authored into a limitation slot. The authored
section stated five of them; the sixth (`PdfFileSecurity.setAllowExceptions` throws) vanished.

``fixtures/wave4_list_replies.json`` holds the lists and replies of the wave-4 run (reseal 8c48f4d2)
exactly as archived. Five repositories (JMAP-Go, JMAP-Node.js, JMAP-TypeScript, JMAP-Rust, PSD-.NET)
were refused for a list their reply HAD restated; four (3D-.NET, 3D-Java, PDF-.NET, PDF-Java) for
items it really had dropped. Email-.NET and Imaging-.NET were refused for a list item that could
not be stated without a stray identifier, which is why authoring no longer refuses an unstated item
(placement prints it; see the last test and test_authoring.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.coverage import Destinations, uncovered
from repository_presenter.components.readme.composition.list_coverage import (
    OWED_SECTIONS,
    item_links,
    kept_lists,
    list_items,
    missing_items,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from support import JAVA3D_DOCS_LIST, JAVA3D_SCOPE_LIST

FIXTURES = Path(__file__).parent / "fixtures"
WAVE4: dict[str, dict[str, Any]] = json.loads(
    (FIXTURES / "wave4_list_replies.json").read_text(encoding="utf-8")
)

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


def test_only_a_list_kept_as_written_in_the_section_is_named_for_folding() -> None:
    """Negative control: a rewritten or superseded list is the composer's to condense, a list
    placed in another section is not this section's, and a one-item list is not a list."""
    owed = {UNIT}
    assert set(kept_lists(_dispositions(), "scope_limitations", owed, _facts())) == {UNIT}
    for disposition in ("VERIFIED_REWRITE", "SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED"):
        assert kept_lists(_dispositions(disposition), "scope_limitations", owed, _facts()) == {}
    assert kept_lists(_dispositions(), "additional_examples", owed, _facts()) == {}
    assert kept_lists(_dispositions(), "scope_limitations", set(), _facts()) == {}  # not owed
    one = FactsDocument(
        "org/x",
        "a" * 40,
        (Fact(UNIT, "inherited_unit", "- **Only item** - it is limited.", (Evidence("R", None),)),),
    )
    assert kept_lists(_dispositions(), "scope_limitations", owed, one) == {}


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


def test_the_scope_list_3d_java_lost_three_bullets_from_is_named_with_them() -> None:
    """The sealed candidate's six units state six of the nine bullets. The three it lost are the
    ones the independent acceptance review found missing (PbrSpecularMaterial; the NurbsCurve
    sampling limit; the licensing, trial and ZIP exclusions)."""
    missing = missing_items(JAVA3D_SCOPE_LIST, " ".join(JAVA3D_AUTHORED.values()))
    assert len(list_items(JAVA3D_SCOPE_LIST)) == 9 and len(missing) == 3
    joined = " ".join(missing)
    assert "NurbsCurve" in joined and "PbrSpecularMaterial" in joined


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
    assert missing_items(JAVA3D_SCOPE_LIST, " ".join(texts.values())) == []


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


def test_an_unbound_section_is_told_of_the_list_placement_drops_from_it() -> None:
    facts = FactsDocument(
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        "5" * 40,
        (Fact(DOTNET3D_UNIT, "inherited_unit", DOTNET3D_DEV_DEPS, (Evidence("README.md", None),)),),
    )
    dispositions = _dispositions_for(DOTNET3D_UNIT, "VERIFIED_MOVE", "development_testing")
    assert "development_testing" in OWED_SECTIONS
    named = kept_lists(dispositions, "development_testing", {DOTNET3D_UNIT}, facts)
    assert list(named) == [DOTNET3D_UNIT]
    # The sealed summary mentions code-coverage collection, which the list's second item is about;
    # a summary that does not leaves that item unstated - and placement prints it (below).
    assert missing_items(named[DOTNET3D_UNIT], DOTNET3D_SUMMARY) == []
    silent = DOTNET3D_SUMMARY.replace("The test suite includes code-coverage collection, and ", "")
    missing = missing_items(named[DOTNET3D_UNIT], silent)
    assert len(missing) == 1 and "coverlet.collector" in missing[0]


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


# --- Wave 4 (reseal 8c48f4d2, triage cause 1): the label is not the item -------------------------


def _case(key: str) -> tuple[str, str]:
    """The archived list and the text of the units the model's reply authored for it."""
    case = WAVE4[key]
    return str(case["list"]), " ".join(str(text) for text in case["units"].values())


def test_a_bold_label_the_reply_folds_into_its_sentences_does_not_make_the_item_missing() -> None:
    """JMAP-Go, JMAP-Node.js, JMAP-TypeScript and JMAP-Rust (the same README structure) and PSD-.NET
    were refused in three identical replies for a list the reply had restated: the item test judged
    the words of the bold label ("Out of scope for v1", "Protocol", "No full Photoshop feature
    set"), and no reply says "out of scope" when it states the three things that are. Before: one
    or two items missing at every attempt; now: none."""
    for key in ("jmap_go", "jmap_node", "psd_net"):
        text, stated = _case(key)
        items = list_items(text)
        assert any("**" in item for item in items), key
        assert missing_items(text, stated) == [], key


def test_the_label_alone_is_still_a_valid_way_to_state_an_item() -> None:
    """Negative control for the fix's other direction: an item named by its lead only, in a
    section that says nothing else of it, remains present - the first test is unchanged."""
    text = (
        "- **Rendering**: not implemented in this build, so pages stay blank.\n- **Fonts**: none."
    )
    assert missing_items(text, "Rendering is a gap.") == ["**Fonts**: none."]


def test_items_a_reply_really_dropped_are_still_named() -> None:
    """The true omissions of the same run, from the archived replies, stay caught: the fix looks
    at the item's own words, and a reply that does not say them has not stated the item."""
    expected = {
        # 3D .NET's first reply states neither the watermark nor the licence limitation; the
        # watermark item shares only the product's name and two generic words with the section.
        "3d_net_a1": ["Text watermarking", "License and trial-management"],
        "3d_net_a2": ["Microsoft3MFFormat", "RvmFormat.LoadAttributes"],
        "3d_java": ["PbrSpecularMaterial"],
        "pdf_java": ["Public-key-encrypted PDFs"],
    }
    for key, names in expected.items():
        text, stated = _case(key)
        missing = missing_items(text, stated)
        assert len(missing) == len(names), (key, missing)
        for item, name in zip(missing, names, strict=True):
            assert name in item, (key, item)


def test_pdf_dot_net_keeps_the_items_its_reply_dropped_and_not_the_ones_it_restated() -> None:
    text, stated = _case("pdf_net")
    assert len(list_items(text)) == 16
    missing = missing_items(text, stated)
    assert len(missing) == 3
    for fragment in ("Dynamic XFA", "Colour management", "pixel-identical"):
        assert any(fragment in item for item in missing), fragment


def test_a_phrase_every_item_repeats_does_not_state_one_of_them() -> None:
    """3D TypeScript's limitations all end 'throw Error ... is not implemented in this FOSS
    build'; a section that says so once has stated none of the members it lists."""
    text = "\n".join(
        [
            "- `VertexElement.setIndices()`/`clear()` throw `Error('... is not implemented')` in "
            "this FOSS build.",
            "- `Node.selectSingleObject()`/`selectObjects()` throw `Error('... is not "
            "implemented')` in this FOSS build.",
            "- `Mesh.doBoolean()` throws `Error('... is not implemented')` in this FOSS build.",
        ]
    )
    generic = "These members throw an error that is not implemented in this FOSS build."
    assert len(missing_items(text, generic)) == 3
    named = generic + " VertexElement setIndices and clear, selectSingleObject and doBoolean."
    assert missing_items(text, named) == []


def test_what_placement_prints_is_what_the_item_test_finds_missing() -> None:
    """Authoring no longer refuses a reply that leaves an item out: placement prints the items the
    section does not state, and the item test finds none missing afterwards. Replayed on the
    archived final replies of PDF .NET (three items of sixteen) and 3D .NET (the two the first
    reply dropped): the 16-item list cannot be stated by six limitation slots, and the printed
    remainder is the three items, as written."""
    for key in ("pdf_net", "3d_net_a1"):
        text, stated = _case(key)
        before = missing_items(text, stated)
        assert before, key
        shown = Destinations.of({"scope_limitations": stated})
        remainder = uncovered(WAVE4[key]["unit"], text, shown, "scope_limitations")
        assert remainder, key
        assert len(list_items(remainder)) == len(before), key
        assert missing_items(text, stated + "\n" + remainder) == [], key
