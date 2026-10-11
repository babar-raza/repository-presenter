"""A sentence that points at a table, list, example or section must have it to point at."""

from __future__ import annotations

from repository_presenter.components.readme.composition.references import dangling_references


def _reasons(readme: str) -> list[str]:
    return [reference.reason for reference in dangling_references(readme)]


def test_a_table_below_needs_a_table_after_it_in_the_section() -> None:
    """Wave-3 acceptance review, Cells-.NET: 'The table below summarizes ...' with no table."""
    lost = "# P\n\n## API\n\nThe table below summarizes the surface.\n\n## License\n\nMIT.\n"
    assert _reasons(lost) == ["says 'table below' but no table follows it in this section"]
    kept = lost.replace("\n## License", "\n| A | B |\n| - | - |\n| 1 | 2 |\n\n## License")
    assert _reasons(kept) == []


def test_a_table_in_the_next_section_is_not_below_this_one() -> None:
    readme = "# P\n\n## One\n\nThe table below lists them.\n\n## Two\n\n| A |\n| - |\n| 1 |\n"
    assert len(_reasons(readme)) == 1


def test_a_sections_lead_in_reaches_the_subsections_it_introduces() -> None:
    """The scope runs to the next heading of the same or a higher level, so Additional Examples'
    lead-in reaches its flagship subsection's fence."""
    readme = (
        "# P\n\n## Additional Examples\n\nThe examples below show more.\n\n"
        "### Save a file\n\n```python\nsave()\n```\n"
    )
    assert _reasons(readme) == []


def test_every_example_below_after_the_last_example_is_dangling() -> None:
    """Slides-.NET: 'Every example below was compiled ...' printed after the last fence."""
    readme = (
        "# P\n\n## Additional Examples\n\n### Save\n\n```csharp\nSave();\n```\n\n"
        "Every example below was compiled and executed.\n\n"
        "Those samples use System.IO.\n"
    )
    assert _reasons(readme) == ["says 'example below' but no code follows it in this section"]


def test_above_looks_back_to_the_start_of_the_scope() -> None:
    readme = "# P\n\n## Usage\n\nThe example above saves a file.\n\n```python\nsave()\n```\n"
    assert _reasons(readme) == ["says 'example above' but no code precedes it in this section"]
    fixed = "# P\n\n## Usage\n\n```python\nsave()\n```\n\nThe example above saves a file.\n"
    assert _reasons(fixed) == []


def test_the_following_kind_and_bare_below_each_need_something_after() -> None:
    assert len(_reasons("# P\n\n## Usage\n\nThe following table lists the options.\n")) == 1
    assert len(_reasons("# P\n\n## Usage\n\nThe options are described below.\n")) == 1
    ok = "# P\n\n## Usage\n\nThe options are described below.\n\n- `fast`\n- `slow`\n"
    assert _reasons(ok) == []
    diagram = "# P\n\n## Glance\n\nThe diagram below shows it.\n\n```mermaid\nflowchart TD\n```\n"
    assert _reasons(diagram) == []


def test_a_named_section_must_be_a_heading_of_the_readme() -> None:
    """Slides-.NET's opening sent the reader to a 'What it cannot do' section it had deleted."""
    lost = "# P\n\nThe limits are listed in full under What it cannot do.\n\n## Installation\n\nx\n"
    assert _reasons(lost) == ["refers to a 'What it cannot do' section this README does not have"]
    named = "# P\n\nSee the Scope and Limitations section.\n\n## Scope and Limitations\n\nx\n"
    assert _reasons(named) == []
    # Generic references and the shell's own headings are never flagged.
    assert _reasons("# P\n\nRead the Installation section first.\n\n## Installation\n\nx\n") == []
    assert _reasons("# P\n\nSee the next section for details.\n") == []


def test_fenced_code_and_headings_are_not_prose() -> None:
    readme = "# P\n\n## Usage\n\n```text\nsee the table below\n```\n\n## The table below\n"
    assert _reasons(readme) == []


def test_a_paragraph_ending_on_a_colon_needs_something_after_it_before_the_next_heading() -> None:
    """Cells-Java, HTML-Python, Page-Python and PDF-Python each ended 'Run the test suite:' and
    went on to the next heading; prose that continues into a paragraph is not judged."""
    lost = "# P\n\n## Development\n\nRun the test suite:\n\n## License\n\nMIT.\n"
    assert _reasons(lost) == ["ends with a colon but nothing follows it before the next heading"]
    assert len(_reasons("# P\n\n## Development\n\nRun the test suite:\n")) == 1
    code = "# P\n\n## Development\n\nRun the test suite:\n\n```bash\npytest\n```\n\n## License\n"
    assert _reasons(code) == []
    prose = "# P\n\n## About\n\nTo be upfront about it:\n\nThe subsystems were removed.\n"
    assert _reasons(prose) == []
    wrapped = "# P\n\n## Usage\n\n<details>\n\nRun the test suite:\n\n</details>\n\n## License\n"
    assert len(_reasons(wrapped)) == 1
