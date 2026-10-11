"""Broken markup: a second H1 and a never-closed <details>, each fixed by the smallest edit."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
    order_edits,
)
from repository_presenter.components.readme_correction.detectors.structure import (
    second_h1,
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
