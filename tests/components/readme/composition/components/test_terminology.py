"""The governed terminology registry and heading-case grammar (verification V2 item 8).

plans/idea.md: "Every Markdown heading uses title case. Visitor-facing technical abbreviations use
their canonical uppercase forms throughout, including PS, EPS, PDF, XPS, XLSX, HTML, and equivalent
discovered formats or protocols." Each rule below has a negative control beside its positive one.
"""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    SUBSECTION_HEADINGS,
)
from repository_presenter.components.readme.composition.components.terminology import (
    LOWER_WORD,
    MIXED_CASE_TERMS,
    UPPERCASE_TERMS,
    canonical_forms,
    noncanonical_terms,
    title_case_violations,
    to_title_case,
)


def test_the_registry_names_every_abbreviation_idea_md_lists_including_ps() -> None:
    forms = canonical_forms()
    for term in ("PS", "EPS", "PDF", "XPS", "XLSX", "HTML"):
        assert forms[term.lower()] == term
    assert "PS" in UPPERCASE_TERMS


def test_the_mixed_case_standards_keep_their_own_spelling() -> None:
    forms = canonical_forms([".gltf", ".npm"])
    assert forms["gltf"] == "glTF" and forms["npm"] == "npm"
    assert {"glTF", "npm"} == MIXED_CASE_TERMS


def test_a_two_letter_discovered_extension_is_an_abbreviation_unless_it_is_a_word() -> None:
    forms = canonical_forms([".ai", ".go", ".to", ".dae", ".one"])
    assert forms["ai"] == "AI" and forms["dae"] == "DAE"
    assert "go" not in forms and "to" not in forms and "one" not in forms


def test_ps_is_found_and_raised_in_lowercase_prose() -> None:
    forms = canonical_forms()
    found = [w for w in LOWER_WORD.findall("It reads ps and eps files.") if w in forms]
    assert found == ["ps", "eps"]
    assert forms["ps"] == "PS"
    # a word after a dot or inside a hyphenated name is not a bare use
    assert [w for w in LOWER_WORD.findall("the .ps file and aspose-ps-tools") if w in forms] == []


def test_a_mis_cased_abbreviation_is_found_whatever_its_case() -> None:
    forms = canonical_forms([".gltf"])
    assert noncanonical_terms("Convert Pdf to Image", forms) == [("Pdf", "PDF")]
    assert noncanonical_terms("Open a GLTF File", forms) == [("GLTF", "glTF")]
    assert noncanonical_terms("Open a Gltf File", forms) == [("Gltf", "glTF")]
    assert noncanonical_terms("Install with NPM", forms) == [("NPM", "npm")]
    assert noncanonical_terms("Convert ps to PDF", forms) == [("ps", "PS")]


def test_the_canonical_forms_pass_and_code_spans_keep_their_source_spelling() -> None:
    forms = canonical_forms([".gltf"])
    assert noncanonical_terms("Convert PS to PDF", forms) == []
    assert noncanonical_terms("Open a glTF File with npm", forms) == []
    assert noncanonical_terms("Call `pdf` and `Gltf`", forms) == []
    assert noncanonical_terms("Use aspose-pdf-foss", forms) == []


@pytest.mark.parametrize(
    "heading",
    [
        "Load a Scene from a File",
        "Convert PS to PDF",
        "Read-Only Access",
        "Install with npm",
        "Documentation & Resources",
        "Extract Text Using `TextAbsorber`",
        "Open an OBJ File and Save as STL",
        "Use Node.js 18 Runtimes",
        "Native and System Requirements",
    ],
)
def test_a_heading_in_title_case_has_no_violation(heading: str) -> None:
    assert title_case_violations(heading, canonical_forms()) == []


@pytest.mark.parametrize(
    ("heading", "words"),
    [
        ("Load a scene from a file", ["scene", "file"]),
        ("load a Scene from a File", ["load"]),
        ("Load a Scene from a file", ["file"]),
        ("convert PS to PDF", ["convert"]),
        ("Read-only access", ["access"]),
        ("Export the Scene to glTF format", ["format"]),
    ],
)
def test_a_heading_not_in_title_case_names_the_words_that_break_it(
    heading: str, words: list[str]
) -> None:
    assert title_case_violations(heading, canonical_forms([".gltf"])) == words


def test_minor_words_may_be_lower_case_between_the_first_and_last_word() -> None:
    assert title_case_violations("Walk the Graph of a Scene") == []
    # ... but the first and last word of a heading are always capitalised
    assert title_case_violations("a Scene to Walk") == ["a"]
    assert title_case_violations("Scene Graph to") == ["to"]


@pytest.mark.parametrize(
    "heading",
    [
        "Load an OBJ file and save as STL",
        "Create a triangle mesh with a PBR material and export to glTF",
        "Format a text portion's font size, weight, and color",
        "`Encrypt` a document with AES-128 and verify it cannot be opened",
        "Add a list-type data validation to restrict input",
        "Extract all text from a PDF using `TextAbsorber`",
        "install with npm",
    ],
)
def test_to_title_case_repairs_exactly_what_the_grammar_rejects(heading: str) -> None:
    forms = canonical_forms([".gltf"])
    assert title_case_violations(heading, forms) != []
    repaired = to_title_case(heading, forms)
    assert title_case_violations(repaired, forms) == []
    # nothing but capitalisation changed
    assert repaired.lower() == heading.lower()


def test_to_title_case_leaves_a_heading_already_in_title_case_untouched() -> None:
    heading = "Load a Scene from a File Using `Scene.open`"
    assert to_title_case(heading) == heading


def test_every_fixed_shell_heading_is_in_title_case() -> None:
    forms = canonical_forms()
    headings = {section.heading for section in SEMANTIC_SHELL if section.heading}
    for heading in headings | SUBSECTION_HEADINGS:
        assert title_case_violations(heading, forms) == [], heading
        assert noncanonical_terms(heading, forms) == [], heading
