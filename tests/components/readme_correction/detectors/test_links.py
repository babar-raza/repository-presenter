"""Broken relative links: repaired only to a unique tracked path, otherwise reported unchanged."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.detectors.links import broken_link


def missing(make_fact: Any, target: str, line: int, number: str = "001") -> Any:
    return make_fact(
        f"link_target:{number}",
        target,
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", f"line {line}; relative; text 'doc'"),
            ("README.md", f"MISSING: tree does not contain {target}"),
        ),
    )


def test_a_link_to_a_moved_file_is_repaired_to_its_unique_new_path(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "# T\n\nSee [the notes](upstream-issues.md) first.\n"
    facts = make_facts(missing(make_fact, "upstream-issues.md", 3))
    ctx = make_context(readme, facts, tree=("README.md", "docs/upstream-issues.md"))
    (edit,) = broken_link(ctx).edits
    assert (edit.original, edit.replacement, edit.fact_ids) == (
        "upstream-issues.md",
        "docs/upstream-issues.md",
        ("link_target:001",),
    )
    assert readme[edit.start : edit.end] == "upstream-issues.md"


def test_a_letter_case_mistake_is_repaired(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "docs/Install.md", 1))
    ctx = make_context("[a](docs/Install.md)\n", facts, tree=("README.md", "docs/install.md"))
    (edit,) = broken_link(ctx).edits
    assert edit.replacement == "docs/install.md"


def test_no_unique_stand_in_means_the_link_is_reported_and_left_as_written(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "gone.md", 1))
    for tree in (("README.md",), ("README.md", "a/gone.md", "b/gone.md")):
        result = broken_link(make_context("[a](gone.md)\n", facts, tree=tree))
        assert result.edits == ()
        assert "no unique file stands in" in result.findings[0].reason


def test_a_fact_whose_line_does_not_hold_the_link_is_reported_not_guessed(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "gone.md", 2))
    result = broken_link(
        make_context("[a](gone.md)\nother text\n", facts, tree=("README.md", "x/gone.md"))
    )
    assert result.edits == () and "not found on its line" in result.findings[0].reason


def test_external_and_resolved_links_are_never_touched(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    external = make_fact(
        "link_target:002",
        "https://example.com/gone",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "line 1; external; text 'x'"),
            ("https://example.com/gone", "MISSING: HTTP 404"),
        ),
    )
    ok = make_fact(
        "link_target:003",
        "LICENSE",
        evidence=(
            ("README.md", "line 1; relative; text 'x'"),
            ("README.md", "RESOLVED: tree contains LICENSE"),
        ),
    )
    result = broken_link(
        make_context("[x](https://example.com/gone) [y](LICENSE)\n", make_facts(external, ok))
    )
    assert result.edits == () and result.findings == ()
