"""License, public-type-count and test-file-count statements."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.detectors.statements import (
    claim_license,
    claim_public_types,
    claim_test_files,
)


def symbol(make_fact: Any, name: str, path: str, kind: str = "class") -> Any:
    return make_fact(
        f"public_symbol:{name.lower()}",
        name,
        evidence=((path, f"line 1; {kind}; public by name"),),
        attributes={"symbol_kind": kind},
    )


# ---------------------------------------------------------------------------------- license
def test_a_wrong_license_name_in_the_license_sentence_is_corrected(make_context: Any) -> None:
    readme = "## License\n\nThis project is licensed under the [Apache License 2.0](LICENSE).\n"
    edits = claim_license(make_context(readme)).edits
    assert [(e.original, e.replacement, e.fact_ids) for e in edits] == [
        ("Apache License 2.0", "MIT License", ("license:spdx",))
    ]


def test_the_right_license_and_the_link_target_are_untouched(make_context: Any) -> None:
    readme = "Licensed under the [MIT License](License/LICENSE.txt). The MIT License permits use.\n"
    result = claim_license(make_context(readme))
    assert result.edits == () and result.findings == ()


def test_a_dual_license_sentence_is_reported_not_edited(make_context: Any) -> None:
    readme = "Licensed under the Apache License 2.0 or the BSD 3-Clause License.\n"
    result = claim_license(make_context(readme))
    assert result.edits == () and "ambiguous" in result.findings[0].reason


def test_a_license_the_table_does_not_know_is_never_touched(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(make_fact("license:spdx", "Artistic-2.0", evidence=(("LICENSE", None),)))
    assert claim_license(make_context("Licensed under the MIT License.\n", facts)).edits == ()


# ------------------------------------------------------------------------- public type count
def test_a_stale_type_count_is_corrected_when_the_count_is_unambiguous(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    classes = [symbol(make_fact, f"C{i}", f"src/main/C{i}.java") for i in range(5)]
    readme = "The library ships 3 public types.\n| `X` | 12 public types in a table row |\n"
    ctx = make_context(readme, make_facts(*classes))
    edits = claim_public_types(ctx).edits
    assert [(e.original, e.replacement) for e in edits] == [("3", "5")]
    assert readme[edits[0].start : edits[0].end] == "3"


def test_a_count_with_two_defensible_figures_is_reported_not_edited(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    # Aspose.Words for Python: 198 verified types, 189 outside ApiExamples; the README said 146.
    classes = [symbol(make_fact, f"C{i}", f"pkg/C{i}.py") for i in range(4)]
    classes.append(symbol(make_fact, "Demo", "ApiExamples/Demo.py"))
    ctx = make_context("It ships 2 public types.\n", make_facts(*classes))
    result = claim_public_types(ctx)
    assert result.edits == () and "outside example and test code" in result.findings[0].reason


def test_a_matching_count_needs_no_edit(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    classes = [symbol(make_fact, f"C{i}", f"src/main/C{i}.java") for i in range(2)]
    ctx = make_context("all 2 public types\n", make_facts(*classes))
    assert claim_public_types(ctx).edits == ()


# ---------------------------------------------------------------------------- test file count
TESTS_TREE = (
    "README.md",
    "src/test/AATests.java",
    "src/test/BBTests.java",
    "src/test/CCTests.java",
)


def test_a_wrong_test_file_count_is_corrected_when_the_recount_agrees(make_context: Any) -> None:
    ctx = make_context("The suite has 18 test files.\n", tree=TESTS_TREE)
    edits = claim_test_files(ctx).edits
    assert [(e.original, e.replacement, e.fact_ids) for e in edits] == [
        ("18", "3", ("build_test_asset:tests",))
    ]


def test_a_count_the_two_derivations_dispute_is_never_edited(make_context: Any) -> None:
    # The fact counts every file under the directory (3); only two are test classes by name, so a
    # README number is not moved to a figure that may be counting helpers.
    tree = ("README.md", "src/test/AATests.java", "src/test/BBTests.java", "src/test/Helper.java")
    result = claim_test_files(make_context("The suite has 18 test files.\n", tree=tree))
    assert result.edits == () and "the two disagree" in result.findings[0].reason


def test_a_true_test_file_count_needs_no_edit(make_context: Any) -> None:
    assert claim_test_files(make_context("It has 3 test files.\n", tree=TESTS_TREE)).edits == ()
