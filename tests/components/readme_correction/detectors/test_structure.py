"""Broken markup: a second H1 and a never-closed <details>, each fixed by the smallest edit."""

from __future__ import annotations

from typing import Any

import pytest
from markdown_it import MarkdownIt

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
    order_edits,
)
from repository_presenter.components.readme_correction.detectors.structure import (
    second_h1,
    stray_fence,
    unclosed_details,
)
from repository_presenter.components.readme_correction.model import (
    STRUCTURE_FIX,
    Edit,
    InvalidEditError,
)


def fixed(readme: str, edits: Any) -> str:
    kept, _ = order_edits(edits)
    corrected, spans = apply_edits(readme, kept)
    assert confinement_violations(readme, corrected, kept, spans) == []
    return corrected


def test_a_second_h1_becomes_an_h2_and_the_title_is_untouched(make_context: Any) -> None:
    readme = "# Product\n\n## Installation\n\n# Requires Go 1.24.5+ (see `go.mod`).\n\ntext\n"
    result = second_h1(make_context(readme))
    (edit,) = result.edits
    assert edit.kind == STRUCTURE_FIX and edit.locators == ("README.md:5",)
    assert fixed(readme, result.edits) == readme.replace("# Requires", "## Requires")


def test_one_h1_hashes_in_fences_and_deeper_headings_are_left_alone(make_context: Any) -> None:
    readme = "# Product\n\n```bash\n# a shell comment\n```\n\n## A\n\n### B\n"
    assert second_h1(make_context(readme)).edits == ()


def test_an_unclosed_details_is_closed_before_the_next_h2(make_context: Any) -> None:
    readme = (
        "# P\n\n## API\n\n<details>\n<summary>All</summary>\n\n| a | b |\n\n"
        "## Detailed Documentation\n\ntext\n\n## License\n\nMIT\n"
    )
    result = unclosed_details(make_context(readme))
    (edit,) = result.edits
    assert edit.locators == ("README.md:5", "README.md:10")
    corrected = fixed(readme, result.edits)
    assert corrected.index("</details>") < corrected.index("## Detailed Documentation")
    assert corrected.count("</details>") == corrected.count("<details>") == 1
    assert "\n\n\n" not in corrected


def test_balanced_details_and_details_in_fences_are_left_alone(make_context: Any) -> None:
    readme = "# P\n\n<details>\nx\n</details>\n\n```html\n<details>\n```\n\n## A\n"
    assert unclosed_details(make_context(readme)).edits == ()


def test_two_unclosed_blocks_close_before_the_same_h2_without_stray_blank_lines(
    make_context: Any,
) -> None:
    readme = "# P\n\n<details>\n<details>\ninner\n\n## Next\n\nx\n"
    corrected = fixed(readme, unclosed_details(make_context(readme)).edits)
    assert corrected.count("</details>") == 2 and "\n\n\n" not in corrected


def test_no_h2_after_the_opening_means_no_guess(make_context: Any) -> None:
    assert unclosed_details(make_context("# P\n\n<details>\ntext\n")).edits == ()


def test_a_structure_fix_must_cite_the_readme_line_and_may_only_insert_a_closing_tag() -> None:
    with pytest.raises(InvalidEditError):
        Edit(STRUCTURE_FIX, "t", 0, 1, "#", "##", (), "r")  # no locator
    with pytest.raises(InvalidEditError):
        Edit(STRUCTURE_FIX, "t", 3, 3, "", "free text", (), "r", locators=("README.md:1",))


def test_a_tag_named_in_an_inline_code_span_is_text_not_an_opening(make_context: Any) -> None:
    readme = (
        "# P\n\n<details>\nx\n</details>\n\n"
        "| `HTMLDetailsElement` | HTML `<details>` disclosure widget element. |\n\n## Next\n"
    )
    assert unclosed_details(make_context(readme)).edits == ()


# ---------------------------------------------------------------- fence-aware details, stray fence
#: The shape of the Aspose.PSD for Python README: the table inside a <details> block ends in a
#: lone closing fence, so CommonMark reads everything up to the next fence line - the closing
#: </details> and three sections - as a code block.
STRAY = (
    "# P\n\n## API\n\n<details>\n<summary>Types</summary>\n\n### Core\n\n| a | b |\n|---|---|\n"
    "| `X` | y |\n```\n\n</details>\n\n## Docs\n\n- a link\n\n## Scope\n\ntext\n\n"
    "## Development\n\n```bash\npytest\n```\n\nafter\n\n## License\n\nMIT\n"
)


def _headings(text: str) -> int:
    return sum(t.type == "heading_open" for t in MarkdownIt("commonmark").parse(text))


def _both(make_context: Any, readme: str) -> Any:
    ctx = make_context(readme)
    return [*stray_fence(ctx).edits, *unclosed_details(ctx).edits]


def test_the_stray_closing_fence_is_emptied_and_no_closing_tag_is_added(make_context: Any) -> None:
    edits = _both(make_context, STRAY)
    (edit,) = edits
    assert edit.detector == "stray_fence" and edit.kind == STRUCTURE_FIX
    assert edit.original == "```" and edit.replacement == "" and edit.locators == ("README.md:13",)
    corrected = fixed(STRAY, edits)
    assert corrected.count("</details>") == corrected.count("<details>") == 1
    assert _headings(corrected) == _headings(STRAY) + 3  # Docs, Scope, Development
    # one line differs from the live README, and only in that line
    assert corrected.splitlines()[12] == ""
    assert corrected.splitlines()[:12] + corrected.splitlines()[13:] == (
        STRAY.splitlines()[:12] + STRAY.splitlines()[13:]
    )
    after = make_context(corrected)
    assert stray_fence(after).edits == () and unclosed_details(after).edits == ()


def test_a_closing_tag_inside_a_fence_never_closes_a_block(make_context: Any) -> None:
    readme = "# P\n\n<details>\nx\n\n```html\n</details>\n```\n\n## Next\n\ntext\n"
    result = unclosed_details(make_context(readme))
    (edit,) = result.edits  # the fenced </details> is text: the block really is unclosed
    assert edit.locators == ("README.md:3", "README.md:10")
    assert stray_fence(make_context(readme)).edits == ()
    assert fixed(readme, result.edits).count("</details>") == 2


def test_a_truly_unclosed_details_is_still_closed_when_a_stray_fence_is_also_present(
    make_context: Any,
) -> None:
    readme = "# P\n\n<details>\nx\n\n## A\n\ntext\n```\n\n## B\n\nmore\n"
    edits = _both(make_context, readme)
    assert {e.detector for e in edits} == {"stray_fence", "unclosed_details"}
    corrected = fixed(readme, edits)
    assert corrected.count("</details>") == 1
    assert corrected.index("</details>") < corrected.index("## A")


def test_a_longer_fence_holding_fence_like_text_is_not_stray(make_context: Any) -> None:
    readme = (
        "# P\n\n## A\n\n````markdown\n# Title\n\n```python\nx = 1\n```\n\n## Inner\n````\n\n"
        "<details>\nbody\n</details>\n\n## B\n\n~~~\n```\n~~~\n"
    )
    ctx = make_context(readme)
    assert stray_fence(ctx).edits == () and stray_fence(ctx).findings == ()
    assert unclosed_details(ctx).edits == ()


def test_a_balanced_readme_with_fenced_shell_comments_is_untouched(make_context: Any) -> None:
    readme = "# P\n\n```\n# a comment\n```\n\n## A\n\n```bash\n# another\n```\n"
    ctx = make_context(readme)
    assert stray_fence(ctx).edits == () and stray_fence(ctx).findings == ()


def test_equally_good_repairs_are_reported_not_guessed(make_context: Any) -> None:
    readme = "# P\n\n```\n```\n```\n## A\n"
    result = stray_fence(make_context(readme))
    assert result.edits == ()
    (finding,) = result.findings
    assert "not guessed" in finding.reason and "3, 4, 5" in finding.reason
