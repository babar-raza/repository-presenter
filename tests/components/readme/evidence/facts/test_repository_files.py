"""A file name an inherited README unit spells is a recorded attribute only when the tree has it.

The strings are the real ones the 2026-10-09 re-seal transactions were refused on
(docs/DEFECT_INDEX.md "readme.dotted_file_name_in_prose_not_a_recorded_fact"):
Slides-.NET's CONTRIBUTING.md and SECURITY.md, Cells-Rust's samples, PDF-Go's examples_test.go and
main.go, Cells-TypeScript's AGENTS.md.
"""

from __future__ import annotations

from repository_presenter.components.readme.composition.authoring import allowed_identifiers
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.repository_files import (
    repository_files,
    tree_index,
)
from repository_presenter.core.facts import REPOSITORY_FILES_ATTRIBUTE, FactsDocument

SLIDES_NET_TREE = [
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "src/Aspose.Slides.Foss/Aspose.Slides.Foss.csproj",
]
SLIDES_NET_README = """# Aspose.Slides FOSS for .NET

## Contributing

Pull requests are welcome. Read
[CONTRIBUTING.md](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/blob/main/CONTRIBUTING.md)
first - it explains the build.

## Security

Do not report a vulnerability in a public issue. See
[SECURITY.md](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/blob/main/SECURITY.md)
for the reporting route.
"""


def _files(text: str, tree: list[str]) -> list[str]:
    return repository_files(text, tree_index(tree))


def test_the_real_slides_net_community_files_are_recorded_from_the_tree() -> None:
    facts = inherited_unit_facts(
        "README.md", SLIDES_NET_README.encode("utf-8"), (), SLIDES_NET_TREE
    )
    recorded = {
        fact.id: (fact.attributes or {}).get(REPOSITORY_FILES_ATTRIBUTE)
        for fact in facts
        if fact.kind == "inherited_unit"
    }
    assert recorded["inherited_unit:003.paragraph"] == "CONTRIBUTING.md"
    assert recorded["inherited_unit:005.paragraph"] == "SECURITY.md"
    # A heading that names no file carries no attribute, and still carries its section.
    assert REPOSITORY_FILES_ATTRIBUTE not in (facts[0].attributes or {})


def test_the_url_a_link_points_at_contributes_nothing_only_its_text_does() -> None:
    text = "[the guide](https://example.com/blob/main/GUIDE.md) and [Support](SUPPORT.md)"
    assert _files(text, ["GUIDE.md", "SUPPORT.md"]) == ["SUPPORT.md"]


def test_a_bare_sample_name_is_recorded_when_a_tree_path_ends_in_it() -> None:
    tree = ["samples/basic.rs", "samples/charts.rs", "src/lib.rs"]
    text = "The samples/ directory holds basic.rs, charts.rs and styles.rs."
    assert _files(text, tree) == ["basic.rs", "charts.rs"]


def test_a_path_with_a_placeholder_segment_still_records_the_file_after_it() -> None:
    tree = ["_examples/acroform_build/main.go", "examples_test.go"]
    text = "Run _examples/<name>/main.go, or see the ExampleXxx functions in examples_test.go."
    assert _files(text, tree) == ["examples_test.go", "main.go"]


def test_a_path_is_recorded_as_spelled_and_by_its_final_segment() -> None:
    tree = [".github/workflows/pages.yml", "docs/guide.md"]
    text = "Docs deploy through .github/workflows/pages.yml; see ./docs/guide.md."
    assert _files(text, tree) == [
        ".github/workflows/pages.yml",
        "docs/guide.md",
        "guide.md",
        "pages.yml",
    ]


def test_a_name_the_readme_spells_and_the_tree_lacks_is_not_recorded() -> None:
    # Negative control: the README mentions HACKING.md and gone.md; only the tree decides.
    text = "Read HACKING.md and gone.md first, then CONTRIBUTING.md."
    assert _files(text, SLIDES_NET_TREE) == ["CONTRIBUTING.md"]


def test_a_name_that_differs_in_case_is_another_name() -> None:
    # Cells-TypeScript: the README's link text says AGENTS.md; the tree holds agents.md.
    tree = ["agents.md", "src/index.ts"]
    assert _files("See [AGENTS.md](agents.md) for contributor guidance.", tree) == ["agents.md"]
    assert "AGENTS.md" not in _files("Read AGENTS.md.", tree)
    assert "contributing.md" not in _files("Read contributing.md.", SLIDES_NET_TREE)


def test_a_path_must_match_on_a_directory_boundary() -> None:
    tree = ["mydocs/guide.md", "docs/other.md"]
    assert _files("See docs/guide.md.", tree) == []
    assert _files("See docs/other.md.", tree) == ["docs/other.md", "other.md"]


def test_a_path_that_climbs_out_of_the_tree_is_never_recorded() -> None:
    assert _files("See ../CONTRIBUTING.md.", SLIDES_NET_TREE) == []


def test_a_name_with_a_longer_extension_is_not_its_prefix() -> None:
    assert _files("Read CONTRIBUTING.md.bak", SLIDES_NET_TREE) == []
    assert _files("Read CONTRIBUTING.mdx", SLIDES_NET_TREE) == []


def test_an_empty_tree_records_nothing() -> None:
    assert _files("Read CONTRIBUTING.md.", []) == []
    facts = inherited_unit_facts("README.md", SLIDES_NET_README.encode("utf-8"))
    assert all(REPOSITORY_FILES_ATTRIBUTE not in (fact.attributes or {}) for fact in facts)


# CUT-2 (BC-12, G3-W08): the PDF-.NET stop. The upstream README names its test project in a code
# span ("The test project (`Aspose.Pdf.Foss.Tests`) is an xUnit suite ..."); the model dropped the
# span, the guard admitted the dotted proper noun, the renderer left it bare (a noun is never
# wrapped), and BC-12 then read its "Aspose.Pdf.Foss" head as a short spelling of the product
# name. The tree holds tests/Aspose.Pdf.Foss.Tests.csproj, so the name is a recorded fact of the
# repository like a file name is: allowed_identifiers admits it, the renderer wraps it, BC-04 and
# BC-12 see a code span.

PDF_NET_TREE = [
    "README.md",
    "src/Aspose.Pdf.Foss.csproj",
    "src/Document.cs",
    "tests/Aspose.Pdf.Foss.Tests.csproj",
    "tests/DocumentTests.cs",
]
PDF_NET_UNIT = (
    "The test project (`Aspose.Pdf.Foss.Tests`) is an xUnit suite that runs on net8.0 and\n"
    "net48 (add `-f net8.0` to run one target)."
)


def test_pdf_net_a_project_name_the_readme_spells_and_the_tree_holds_is_recorded() -> None:
    assert "Aspose.Pdf.Foss.Tests" in _files(PDF_NET_UNIT, PDF_NET_TREE)
    # The library project is a project name too; the authoring rule, not this record, decides
    # that a name which is itself a spelling of the product is never a spellable identifier.
    assert "Aspose.Pdf.Foss" in _files("Build `Aspose.Pdf.Foss` first.", PDF_NET_TREE)


def test_gis_net_a_directory_name_the_readme_spells_is_recorded() -> None:
    tree = ["Aspose.GIS.FOSS.Tests/UnitTest1.cs", "Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj"]
    text = "Its test suite resides in the Aspose.GIS.FOSS.Tests/ directory."
    assert "Aspose.GIS.FOSS.Tests" in _files(text, tree)


def test_a_project_name_the_tree_lacks_or_spells_in_another_case_is_not_recorded() -> None:
    # Negative controls: the README spells a project the tree does not hold, one that differs in
    # case, and one that is only the prefix of a longer project's name.
    assert "Aspose.Pdf.Foss.Benchmarks" not in _files(
        "Run `Aspose.Pdf.Foss.Benchmarks`.", PDF_NET_TREE
    )
    assert "aspose.pdf.foss.tests" not in _files("Run `aspose.pdf.foss.tests`.", PDF_NET_TREE)
    longer = ["tests/Aspose.Pdf.Foss.Tests.Integration.csproj"]
    assert "Aspose.Pdf.Foss.Tests" not in _files(PDF_NET_UNIT, longer)


def test_a_source_file_stem_is_not_a_project_name() -> None:
    # Negative control: only a project or solution file names a project; Document.cs does not make
    # "Document" or "Aspose.Pdf.Foss.Document" a recorded name.
    tree = ["src/Aspose.Pdf.Foss.Document.cs"]
    assert "Aspose.Pdf.Foss.Document" not in _files("See `Aspose.Pdf.Foss.Document`.", tree)


def test_the_recorded_project_name_is_a_spellable_identifier() -> None:
    facts = inherited_unit_facts(
        "README.md", f"# Aspose.PDF FOSS for .NET\n\n{PDF_NET_UNIT}\n".encode(), (), PDF_NET_TREE
    )
    document = FactsDocument("aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET", "a" * 40, tuple(facts))
    allowed = allowed_identifiers(document, "Aspose.PDF FOSS for .NET")
    assert "Aspose.Pdf.Foss.Tests" in allowed
    # Not recorded when the tree lacks it: the guard still refuses it.
    bare = inherited_unit_facts("README.md", PDF_NET_UNIT.encode(), (), ["README.md"])
    refused = allowed_identifiers(
        FactsDocument("aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET", "a" * 40, tuple(bare)),
        "Aspose.PDF FOSS for .NET",
    )
    assert "Aspose.Pdf.Foss.Tests" not in refused


def test_a_project_name_that_is_a_spelling_of_the_product_is_never_a_spellable_identifier() -> None:
    """Negative control (BC-12 must not be bypassed): the library project ``Aspose.Pdf.Foss`` is a
    separator and case variant of the product name 'Aspose.PDF FOSS for .NET'. Recording that it
    exists in the tree must not make the short spelling admissible, and so wrapped in a code
    span where BC-12 would no longer see it."""
    facts = inherited_unit_facts(
        "README.md",
        b"# Aspose.PDF FOSS for .NET\n\nBuild `Aspose.Pdf.Foss` first.\n",
        (),
        PDF_NET_TREE,
    )
    assert any(
        "Aspose.Pdf.Foss" in (fact.attributes or {}).get(REPOSITORY_FILES_ATTRIBUTE, "")
        for fact in facts
    )
    allowed = allowed_identifiers(
        FactsDocument("aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET", "a" * 40, tuple(facts)),
        "Aspose.PDF FOSS for .NET",
    )
    assert "Aspose.Pdf.Foss" not in allowed
