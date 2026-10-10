"""A file name an inherited README unit spells is a recorded attribute only when the tree has it.

The strings are the real ones the 2026-10-09 re-seal transactions were refused on
(docs/DEFECT_INDEX.md "readme.dotted_file_name_in_prose_not_a_recorded_fact"):
Slides-.NET's CONTRIBUTING.md and SECURITY.md, Cells-Rust's samples, PDF-Go's examples_test.go and
main.go, Cells-TypeScript's AGENTS.md.
"""

from __future__ import annotations

from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.repository_files import (
    repository_files,
    tree_index,
)
from repository_presenter.core.facts import REPOSITORY_FILES_ATTRIBUTE

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
