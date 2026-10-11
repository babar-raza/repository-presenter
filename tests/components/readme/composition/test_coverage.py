"""Whole-content coverage: a kept unit is dropped only when its destination states ALL of it.

The units are the real ones the wave-3 transactions (reseal ``f69f75c7``) dropped by the fact-id
overlap rule and BC-08 then demanded back: Cells-Go 024, Page-Python 092, PDF-Go 025, PDF-.NET 019.
"""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.composition.coverage import (
    COMMAND,
    SENTENCE_SHARE,
    Destinations,
    hard_tokens,
    sentences,
    states_all,
    uncovered,
    uncovered_block,
    unversioned,
)
from repository_presenter.components.readme.composition.list_coverage import (
    list_items,
    missing_items,
)
from repository_presenter.components.readme.validation import registry

CELLS_GO_RUN = "Run `go run main.go` to produce `hello.xlsx`."
PAGE_PYTHON_MAKE = (
    "`make test` runs `python3 -m unittest discover -s tests` (see [`Makefile`](Makefile)); "
    "`make\nbuild` produces wheel and sdist artifacts, and `make check` runs both test and build."
)
PDF_GO_SHOWCASE = (
    "[**docs/feature_showcase.pdf**](docs/feature_showcase.pdf) is a single 20-page PDF generated "
    "by\n[`_examples/feature_showcase`](_examples/feature_showcase/main.go) that walks nearly "
    "every\ncapability above in one document. Regenerate it locally with\n"
    "`go run ./_examples/feature_showcase`."
)
PDF_NET_REFERENCE = (
    "Building all five targets needs the .NET 10 SDK (add `-f net8.0`, for example, to build "
    "one). Then reference `src/Aspose.Pdf.Foss.csproj` from your project (e.g. `dotnet add "
    "reference`), or\nadd the built `Aspose.Pdf.Foss.dll` as an assembly reference."
)


def _shown(sections: dict[str, str]) -> Destinations:
    return Destinations.of(sections)


def test_the_command_shape_is_the_one_bc08_holds_the_document_to() -> None:
    """The coverage test and BC-08 must call the same spans commands, or a unit this module drops
    as stated could still be demanded by BC-08 (a drift pin, not a second definition)."""
    assert COMMAND.pattern == registry._COMMAND.pattern
    assert COMMAND.flags == registry._COMMAND.flags


def test_a_sentence_boundary_never_falls_inside_a_span_a_link_or_a_url() -> None:
    text = (
        "Open `a.b. Then c` first. See [the guide](docs/a.b.Next/x.md) and https://x.io/a.b.Next "
        "now. Then stop."
    )
    assert sentences(text) == [
        "Open `a.b. Then c` first.",
        "See [the guide](docs/a.b.Next/x.md) and https://x.io/a.b.Next now.",
        "Then stop.",
    ]


def test_hard_tokens_are_the_commands_and_links_bc08_and_bc06_demand() -> None:
    assert hard_tokens(CELLS_GO_RUN) == ["go run main.go"]
    tokens = hard_tokens(PAGE_PYTHON_MAKE)
    assert {"make test", "python3 -m unittest discover -s tests", "make check", "Makefile"} <= set(
        tokens
    )
    # An in-page anchor names a heading, not a document.
    assert hard_tokens("See [Scope](#scope-and-limitations).") == []
    assert hard_tokens("A plain sentence with `Workbook` and `hello.xlsx`.") == []


# --- the four units BC-08 demanded back --------------------------------------------------------
def test_a_sentence_after_an_example_carrying_a_command_the_document_lacks_is_not_covered() -> None:
    """Cells-Go: the paragraph beside example:002 told the reader to run the program. Calling it
    the example's lead-in dropped it while BC-08 demanded ``go run main.go``."""
    shown = _shown({"quick_start": "Create a workbook and save it.\n\n```go\nfmt.Println(1)\n```"})
    kept = uncovered(
        "inherited_unit:024.paragraph", CELLS_GO_RUN, shown, "quick_start", lead_in=True
    )
    assert kept == CELLS_GO_RUN  # as written, byte for byte


def test_the_same_sentence_is_covered_once_the_document_states_its_command() -> None:
    shown = _shown({"quick_start": "Create a workbook.\n\n```bash\ngo run main.go\n```"})
    assert (
        uncovered("inherited_unit:024.paragraph", CELLS_GO_RUN, shown, "quick_start", lead_in=True)
        == ""
    )


def test_a_lead_in_the_example_lead_in_already_states_is_still_dropped() -> None:
    """Negative control (items 65/76/92): "Load a workbook with recovery diagnostics:" adds no
    command and no link, and the section's own lead-in introduces the example."""
    shown = _shown({"quick_start": "The following example loads a workbook.\n\n```go\nx()\n```"})
    lead_in = "Load a workbook with recovery diagnostics:"
    assert (
        uncovered("inherited_unit:018.paragraph", lead_in, shown, "quick_start", lead_in=True) == ""
    )
    # ... but the same words are a statement of their own anywhere else, so not covered there.
    assert uncovered("inherited_unit:018.paragraph", lead_in, shown, "quick_start") == lead_in


def test_a_paragraph_of_make_targets_is_carried_whole_when_no_command_of_it_renders() -> None:
    """Page-Python: development_testing prints the suite size and the build and test commands the
    facts name, not ``make test`` / ``make check`` -- the paragraph overlapped on
    ``build_test_asset:tests`` and was dropped; BC-08 then demanded three commands."""
    shown = _shown(
        {
            "development_testing": (
                "The suite covers 12 test files under `tests`.\n\n"
                "To run the tests from a clone, run:\n\n```bash\npython -m pytest\n```"
            )
        }
    )
    kept = uncovered("inherited_unit:092.paragraph", PAGE_PYTHON_MAKE, shown, "development_testing")
    assert kept == PAGE_PYTHON_MAKE


def test_a_paragraph_linking_a_document_nothing_links_is_carried() -> None:
    """PDF-Go: the paragraph explains ``go run ./_examples/feature_showcase`` and links
    docs/feature_showcase.pdf; the plan's link to ``_examples/`` covered it by one shared fact."""
    shown = _shown({"additional_examples": "The following examples demonstrate common tasks."})
    assert (
        uncovered("inherited_unit:025.paragraph", PDF_GO_SHOWCASE, shown, "additional_examples")
        == PDF_GO_SHOWCASE
    )


def test_a_paragraph_naming_a_dotnet_command_the_sdk_row_does_not_print_is_carried() -> None:
    """PDF-.NET: ``dotnet add reference`` is in no fact, so only the paragraph can carry it."""
    shown = _shown({"development_testing": "The suite covers 40 test files under `tests`."})
    assert (
        uncovered("inherited_unit:019.paragraph", PDF_NET_REFERENCE, shown, "development_testing")
        == PDF_NET_REFERENCE
    )


# --- a unit is dropped when, and only when, all of it is stated --------------------------------
def test_a_paragraph_the_destination_states_in_full_is_dropped_not_duplicated() -> None:
    sentence = "OBJ import is not verified in this release."
    shown = _shown({"scope_limitations": f"{sentence}\n\n- Other note."})
    assert uncovered("inherited_unit:010.paragraph", sentence, shown, "scope_limitations") == ""
    # In other words, with at least SENTENCE_SHARE of its word stems present, it is stated too.
    paraphrase = _shown(
        {"scope_limitations": "Importing OBJ files is not verified in this release."}
    )
    assert SENTENCE_SHARE <= 0.8
    assert (
        uncovered("inherited_unit:010.paragraph", sentence, paraphrase, "scope_limitations") == ""
    )


def test_a_paragraph_the_destination_only_shares_a_topic_with_is_carried() -> None:
    """Sharing a fact is not stating the sentence: the destination speaks of OBJ, the unit says
    what it cannot do."""
    unit = "OBJ import silently drops texture coordinates and every material."
    shown = _shown({"scope_limitations": "OBJ files are listed under the formats."})
    assert uncovered("inherited_unit:010.paragraph", unit, shown, "scope_limitations") == unit


def test_a_unit_with_nothing_to_compare_by_is_carried_never_assumed_covered() -> None:
    table = "| a | b |\n|---|---|\n| x | y |"
    shown = _shown({"scope_limitations": "Unrelated text about limits."})
    assert uncovered("inherited_unit:023.table", table, shown, "scope_limitations") == table


def test_only_the_sentences_the_destination_does_not_state_are_carried() -> None:
    unit = (
        "The package writes GLB only. OBJ import silently drops every material. "
        "Run `make check` before sending a change."
    )
    shown = _shown({"scope_limitations": "The package writes GLB only.\n\n- Other note."})
    assert uncovered("inherited_unit:011.paragraph", unit, shown, "scope_limitations") == (
        "OBJ import silently drops every material. Run `make check` before sending a change."
    )


# --- lists: the item test BC-05 uses, item by item ---------------------------------------------
LIMITATIONS = (
    "- Texture baking is not implemented in this edition.\n"
    "- OBJ import is a stub in the published artifact; do not rely on it.\n"
    "  A second line of the same item.\n"
    "- Scene rendering is not implemented in this edition."
)


def test_a_list_is_carried_only_for_the_items_the_destination_does_not_state() -> None:
    shown = _shown(
        {
            "scope_limitations": (
                "- Texture baking is not implemented.\n- Scene rendering is not implemented."
            )
        }
    )
    kept = uncovered("inherited_unit:064.list", LIMITATIONS, shown, "scope_limitations")
    assert kept == (
        "- OBJ import is a stub in the published artifact; do not rely on it.\n"
        "  A second line of the same item."
    )
    # What it keeps is exactly what BC-05's item test says the destination lacks.
    assert list_items(kept) == missing_items(LIMITATIONS, shown.text("scope_limitations"))


def test_a_list_every_item_of_which_is_stated_is_dropped_and_none_stated_is_whole() -> None:
    stated = _shown({"scope_limitations": LIMITATIONS})
    assert uncovered("inherited_unit:064.list", LIMITATIONS, stated, "scope_limitations") == ""
    elsewhere = _shown({"scope_limitations": "Nothing relevant here at all."})
    assert (
        uncovered("inherited_unit:064.list", LIMITATIONS, elsewhere, "scope_limitations")
        == LIMITATIONS
    )


def test_a_list_item_is_judged_by_its_link_in_documentation_and_resources() -> None:
    items = (
        "- [Getting started](https://docs.aspose.org/3d/java/) - The guide.\n"
        "- [Publishing](PUBLISHING.md) - How releases are cut.\n"
        "- [Progress notes](docs/foss-java-progress.md) - Where the port stands."
    )
    shown = _shown(
        {
            "documentation_resources": (
                "- **[Docs](https://docs.aspose.org/3d/java/)** - The guide.\n"
                "- **[Notes](docs/foss-java-progress.md)** - Progress."
            )
        }
    )
    kept = uncovered(
        "inherited_unit:070.list", items, shown, "documentation_resources", by_link=True
    )
    assert kept == "- [Publishing](PUBLISHING.md) - How releases are cut."


def test_a_list_item_carrying_a_command_the_document_lacks_is_carried_despite_its_words() -> None:
    """Stricter than BC-05's subject-word test on purpose: the words 'make' and 'test' are in any
    development section, the command ``make test`` is in none."""
    items = "- `make test` - run the tests\n- `make build` - build the wheel"
    shown = _shown(
        {"development_testing": "Run the tests, then build the wheel.\n\n```bash\nmake build\n```"}
    )
    kept = uncovered("inherited_unit:090.list", items, shown, "development_testing")
    assert kept == "- `make test` - run the tests"


def test_what_is_dropped_is_always_something_bc05s_item_test_accepts() -> None:
    """Consistency: for every list this module calls covered, BC-05's dropped-list rule finds no
    missing item (the rule it applies to an ``overlap`` unit)."""
    for text, section in (
        (
            LIMITATIONS,
            "Texture baking is not implemented in this edition. OBJ import is a stub in "
            "the published artifact. Scene rendering is not implemented in this edition.",
        ),
        (
            "- Alpha beta gamma delta.\n- Epsilon zeta eta theta.",
            "Alpha beta gamma delta. Epsilon zeta eta theta.",
        ),
    ):
        shown = _shown({"scope_limitations": section})
        if uncovered("inherited_unit:001.list", text, shown, "scope_limitations") == "":
            assert missing_items(text, section) == []


def test_a_list_restated_under_its_bold_labels_is_dropped_not_printed_a_second_time() -> None:
    """Wave 4, JMAP-Go: the Scope list ("Protocol", "Out of scope for v1", the unit-test note) is
    stated by the five authored units without ever saying "out of scope". Placement shares the
    item test with BC-05, so it too no longer reads the label for the item: nothing is printed
    twice, and a list the units do not state is still carried whole."""
    archived = json.loads(
        (Path(__file__).parent / "fixtures" / "wave4_list_replies.json").read_text(encoding="utf-8")
    )["jmap_go"]
    stated = " ".join(archived["units"].values())
    shown = _shown({"scope_limitations": stated})
    assert uncovered(archived["unit"], archived["list"], shown, "scope_limitations") == ""
    silent = _shown({"scope_limitations": "The library targets Go 1.21."})
    assert (
        uncovered(archived["unit"], archived["list"], silent, "scope_limitations")
        == archived["list"]
    )


# --- a release number is not content; the renderer's own sections may state a unit (wave 6) -------
#
# The units are the real ones of the wave-6 transactions: PDF-Java 015 (the Gradle line at 26.6.0
# the Installation row prints at 26.9.0), BarCode-Python 014 and Cells-Java 019 (install prose),
# PDF-Python 021 (the extras and what each adds), 3D-.NET 014 (a paragraph one sentence of which is
# the Dependencies section's), Slides-Python 122 (a pointer at documents the section lists).

GRADLE_KEPT = "```groovy\nimplementation 'org.aspose:aspose-pdf-foss:26.6.0'\n```"
INSTALLATION = (
    "Add the dependency to your build file.\n\n```xml\n<dependency>\n"
    "    <groupId>org.aspose</groupId>\n    <artifactId>aspose-pdf-foss</artifactId>\n"
    "    <version>26.9.0</version>\n</dependency>\n```\n\n```groovy\n"
    "implementation 'org.aspose:aspose-pdf-foss:26.9.0'\n```"
)


def test_a_release_number_of_three_components_is_one_token_a_floor_is_not() -> None:
    assert unversioned("aspose-pdf-foss:26.6.0") == unversioned("aspose-pdf-foss:26.9.0")
    assert unversioned("v1.2.3-rc1 and 1.2.3.4") == "<release> and <release>"
    # a floor and a count are compared as written
    assert unversioned("Python 3.10, Java 17") == "Python 3.10, Java 17"
    assert unversioned("Python 3.10") != unversioned("Python 3.12")


def test_a_kept_block_the_installation_row_prints_at_another_release_is_covered() -> None:
    shown = _shown({"installation": INSTALLATION, "development_testing": "Run the tests."})
    rows = ("installation", "dependencies")
    assert uncovered_block(GRADLE_KEPT, shown, rows) == ""
    # the Kotlin DSL line is not printed by the row: the block is carried whole
    kotlin = '```kotlin\nimplementation("org.aspose:aspose-pdf-foss:26.6.0")\n```'
    assert uncovered_block(kotlin, shown, rows) == kotlin
    # one line the row lacks carries the whole block (its lines only mean something together)
    two = GRADLE_KEPT.replace("\n```", "\nrepositories { mavenCentral() }\n```", 1)
    assert uncovered_block(two, shown, rows) == two
    # nothing to compare by: carried, never assumed covered
    assert uncovered_block("```\n# only a comment\n```", shown, rows) == (
        "```\n# only a comment\n```"
    )
    # only the renderer's sections named are read: a line Development and Testing prints (and
    # drops when a placed block shows it) is not the Installation row's
    other = _shown({"installation": "Open a document.", "development_testing": INSTALLATION})
    assert uncovered_block(GRADLE_KEPT, other, rows) == GRADLE_KEPT


def test_a_shell_command_is_compared_as_written_never_at_another_release() -> None:
    """BC-08 demands the unit's own spelling of a command, so a command at another release than the
    document's is not the document's command - for a prose sentence and for a block alike - while
    a build-file declaration (which BC-08 does not protect) is compared release number aside."""
    unit = "Install it with `pip install aspose-foo==1.2.3` or from source."
    other_release = _shown(
        {
            "development_testing": (
                "Install it with pip or from source: `pip install aspose-foo==2.0.0`."
            )
        }
    )
    assert (
        uncovered("inherited_unit:010.paragraph", unit, other_release, "development_testing")
        == unit
    )
    same = _shown(
        {
            "development_testing": (
                "Install it with pip or from source: `pip install aspose-foo==1.2.3`."
            )
        }
    )
    assert uncovered("inherited_unit:010.paragraph", unit, same, "development_testing") == ""
    block = "```bash\npip install aspose-foo==1.2.3\n```"
    rows = ("installation",)
    assert (
        uncovered_block(block, _shown({"installation": "pip install aspose-foo==2.0.0"}), rows)
        == block
    )
    assert (
        uncovered_block(block, _shown({"installation": "pip install aspose-foo==1.2.3"}), rows)
        == ""
    )


BARCODE_INSTALL = (
    "The distribution is named `aspose-barcode-foss`; the import package is "
    "`aspose_barcode_foss`.\nRequires Python 3.12+ and Pillow >= 10.1.0 (a real, declared runtime "
    "dependency, used only for\nPNG rendering) - otherwise the library has no system-level "
    "dependencies, and ships a `py.typed`\nmarker for full type-checker support."
)
DEPENDENCIES = (
    "### Required Package Dependencies\n\n- `Pillow>=10.1.0`\n\n"
    "### Native and System Requirements\n\n- Requires Python 3.12 or later "
    "(`python_requires` in `pyproject.toml`)."
)


def test_a_unit_about_installing_may_be_stated_by_the_renderers_own_sections() -> None:
    """The destination is Scope and Limitations (the model's filing); the second sentence of the
    unit is new (the ``py.typed`` marker, the import package), so it is carried and only that
    sentence is - the first, stated by the Installation and Dependencies text, is not repeated."""
    shown = _shown(
        {
            "installation": "Install `aspose-barcode-foss` with pip; the import package is "
            "`aspose_barcode_foss`.",
            "dependencies": DEPENDENCIES,
            "scope_limitations": "The library does not decode barcodes.",
        }
    )
    unit = (
        "Requires Python 3.12 or later and `Pillow>=10.1.0`. It ships a `py.typed` marker for "
        "full type-checker support."
    )
    carried = uncovered(
        "inherited_unit:014.paragraph",
        unit,
        shown,
        "scope_limitations",
        also=("installation", "dependencies"),
        only_also=True,
    )
    assert carried == "It ships a `py.typed` marker for full type-checker support."
    # without the renderer's sections the paragraph is carried whole, as before
    assert uncovered("inherited_unit:014.paragraph", unit, shown, "scope_limitations") == unit


def test_the_destination_is_not_a_haystack_for_a_unit_nominated_by_its_topic_alone() -> None:
    """3D-.NET 014: ``The repository also contains a separate console conversion tool ... it is not
    published to NuGet.`` shares enough identifiers with the long Development and Testing text to be
    "stated" by it. A unit no fact ties to the destination is judged against the renderer's
    Installation and Dependencies text only."""
    unit = (
        "The repository also contains a separate console conversion tool "
        "(`src/converter/Converter.csproj`, package id `Aspose.3D.Converter`) that references the "
        "library as a project; it is not published to NuGet."
    )
    long_authored = (
        "Build the repository with the converter project and the console tool, which references "
        "the library as a project, from src/converter/Converter.csproj; package ids such as "
        "Aspose.3D.Converter are not published to NuGet."
    )
    shown = _shown(
        {
            "installation": "Install the published package from NuGet (`Aspose.3D.FOSS`).",
            "dependencies": "No required third-party package dependencies.",
            "development_testing": long_authored,
        }
    )
    kwargs = {"also": ("installation", "dependencies")}
    assert (
        uncovered("inherited_unit:014.paragraph", unit, shown, "development_testing", **kwargs)
        == ""
    )
    assert (
        uncovered(
            "inherited_unit:014.paragraph",
            unit,
            shown,
            "development_testing",
            only_also=True,
            **kwargs,
        )
        == unit
    )


def test_a_dependency_item_is_judged_as_a_sentence_against_the_renderers_text() -> None:
    """PDF-Python 021: the lead word of an item ("images", "pytest") is stated by any unrelated
    mention and would hide what the item says about it. Against the renderer's sections an item is
    stated only when it is stated as a sentence."""
    extras = (
        "- `images` - Pillow-based image support (JPX/JPEG 2000 decoding, arithmetic-coded JPEG).\n"
        "- `Pillow` >=12.3"
    )
    shown = _shown(
        {
            "dependencies": "- `Pillow>=12.3` (extra `images`)\n- `Brotli>=1.2` (extra `woff2`)",
            "development_testing": "Run the tests.",
        }
    )
    carried = uncovered(
        "inherited_unit:021.list",
        extras,
        shown,
        "development_testing",
        also=("dependencies",),
        only_also=True,
    )
    assert carried == extras.splitlines()[0]  # the item that says what the extra adds


def test_a_paragraph_that_only_points_at_listed_documents_is_dropped_in_documentation() -> None:
    """Slides-Python 122: ``See agents.md ... and CONTRIBUTING.md ... for how to build`` repeats two
    items of the list above it (README_CONTRACT.md row 15 never names a target twice)."""
    pointer = (
        "See [`agents.md`](agents.md) for the package's internal structure and contribution "
        "conventions, and\n[CONTRIBUTING.md](CONTRIBUTING.md)\n"
        "(https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python/blob/main/"
        "CONTRIBUTING.md)\nfor how to build, how to run the tests, and how to report a fix."
    )
    listed = (
        "- **[Contributor guide](agents.md)** - architecture notes.\n"
        "- **[CONTRIBUTING.md](CONTRIBUTING.md)** - how to build and test."
    )
    shown = _shown({"documentation_resources": listed})
    assert (
        uncovered(
            "inherited_unit:122.paragraph",
            pointer,
            shown,
            "documentation_resources",
            by_link=True,
        )
        == ""
    )
    # negative control: one document the section does not list keeps the paragraph
    other = pointer.replace("CONTRIBUTING.md](CONTRIBUTING.md)", "SECURITY.md](SECURITY.md)")
    assert (
        uncovered(
            "inherited_unit:122.paragraph",
            other,
            shown,
            "documentation_resources",
            by_link=True,
        )
        == other
    )


def test_states_all_asks_every_sentence_of_the_unit_of_the_kept_text() -> None:
    kept = (
        "Reading is limited to `.pptx`; `SaveFormat` declares `Ppt` and `Pdf` but only `Pptx` "
        "is written."
    )
    assert states_all(kept, "Only `Pptx` is written; `SaveFormat` declares `Ppt` and `Pdf`.")
    assert not states_all(kept, "Only `Pptx` is written. Comment threads are classic.")
    assert not states_all(kept, "")
