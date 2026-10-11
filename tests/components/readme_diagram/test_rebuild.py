"""Rewriting a README's diagram without touching a byte elsewhere."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme_diagram import (
    NotAGlanceError,
    lint_source,
    parse,
    rebuild_body,
    rebuild_readme,
)
from repository_presenter.components.readme_diagram.rebuild import mermaid_fences

DIAGRAM = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing PDF document (including encrypted)"]
    i2["Nothing - authored from scratch"]
  end
  PRODUCT["Aspose.PDF FOSS for Go"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Page-level operations (split, merge, extract, impose)"]
    c2["Encryption and digital signatures"]
    c3["Tables and vector graphics"]
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["PDF documents (file path or in-memory stream)"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""

SEQUENCE = "sequenceDiagram\n  Alice->>Bob: hello\n"


def readme(diagram: str = DIAGRAM, eol: str = "\n") -> str:
    parts = [
        "# Aspose.PDF FOSS for Go",
        "",
        "Some prose a maintainer wrote.  Two spaces, kept.   ",
        "",
        "## At a Glance",
        "",
        "```mermaid",
        *diagram.rstrip("\n").split("\n"),
        "```",
        "",
        "## Installation",
        "",
        "```sh",
        "go get example.com/x",
        "```",
        "",
    ]
    return eol.join(parts)


def test_only_the_lines_between_the_fence_markers_change() -> None:
    text = readme()
    result = rebuild_readme(text)
    assert len(result.changes) == 1 and result.skipped == ()
    start = text.index("```mermaid\n") + len("```mermaid\n")
    end = text.index("\n```\n", start) + 1
    assert result.text.startswith(text[:start])
    assert result.text.endswith(text[end:])
    assert result.text[start : len(result.text) - len(text) + end] == rebuild_body(DIAGRAM)


def test_the_change_names_what_was_wrong_and_both_sources() -> None:
    change = rebuild_readme(readme()).changes[0]
    assert change.first_line == 8
    assert "ORIENTATION_VERTICAL" in change.report.codes
    assert change.before == DIAGRAM and change.after == rebuild_body(DIAGRAM)


def test_a_second_run_finds_nothing_to_do() -> None:
    once = rebuild_readme(readme())
    again = rebuild_readme(once.text)
    assert again.changes == () and again.text == once.text


def test_a_readme_with_crlf_line_endings_keeps_them() -> None:
    text = readme(eol="\r\n")
    result = rebuild_readme(text)
    assert result.changes
    assert "\n" not in result.text.replace("\r\n", "")
    assert result.text.count("\r\n") > text.count("\r\n")
    assert rebuild_readme(result.text).changes == ()


def test_a_readme_without_a_diagram_or_with_another_kind_of_diagram_is_untouched() -> None:
    plain = "# Title\n\nSome text.\n\n```python\nprint(1)\n```\n"
    assert rebuild_readme(plain).text == plain and rebuild_readme(plain).changes == ()
    other = readme(SEQUENCE)
    result = rebuild_readme(other)
    assert result.text == other and result.changes == ()
    assert [reason for _, reason in result.skipped] == [
        "no flowchart declaration before 'sequenceDiagram'"
    ]


def test_each_at_a_glance_diagram_is_rebuilt_and_other_fences_are_left_alone() -> None:
    text = (
        readme()
        + "\n## Other\n\n```mermaid\n"
        + SEQUENCE
        + "```\n\n```mermaid\n"
        + DIAGRAM
        + "```\n"
    )
    result = rebuild_readme(text)
    assert len(result.changes) == 2 and len(result.skipped) == 1
    assert SEQUENCE in result.text
    assert DIAGRAM not in result.text


def test_tilde_fences_are_found_and_an_indented_or_unclosed_fence_is_not_rewritten() -> None:
    tilde = "~~~mermaid\n" + DIAGRAM + "~~~\n"
    assert len(rebuild_readme(tilde).changes) == 1
    indented = (
        "- item\n\n  ```mermaid\n"
        + "".join("  " + line + "\n" for line in DIAGRAM.splitlines())
        + "  ```\n"
    )
    assert rebuild_readme(indented).changes == ()
    unclosed = "```mermaid\n" + DIAGRAM
    assert rebuild_readme(unclosed).text == unclosed
    assert mermaid_fences(unclosed.splitlines(keepends=True)) == []


def test_a_longer_fence_marker_closes_only_on_a_marker_at_least_as_long() -> None:
    text = "````mermaid\n" + DIAGRAM + "```\nstill inside\n````\nafter\n"
    fences = mermaid_fences(text.splitlines(keepends=True))
    assert len(fences) == 1 and "still inside" in fences[0].body


def test_rebuild_body_refuses_a_diagram_it_does_not_own() -> None:
    with pytest.raises(NotAGlanceError):
        rebuild_body(SEQUENCE)


def test_every_live_readme_diagram_is_rewritten_in_place_and_stays_valid(
    live: dict[str, str],
) -> None:
    for name, source in live.items():
        text = "# T\n\nIntro.\n\n```mermaid\n" + source + "```\n\nTail text.\n"
        result = rebuild_readme(text)
        assert len(result.changes) == 1, name
        assert result.text.startswith("# T\n\nIntro.\n\n```mermaid\n"), name
        assert result.text.endswith("```\n\nTail text.\n"), name
        body = result.text.split("```mermaid\n", 1)[1].rsplit("```\n\nTail text.\n", 1)[0]
        assert lint_source(body).conforming, name
        assert parse(body).glance == parse(source).glance, name
        assert rebuild_readme(result.text).changes == (), name
