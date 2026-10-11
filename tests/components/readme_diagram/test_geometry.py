"""The label-width model: where a label breaks, decided once and the same way every time."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme_diagram.geometry import (
    FALLBACK_PX,
    WIDTHS,
    label_lines,
    text_px,
    tokens,
    widest_token_px,
    wrap_label,
)

LONG = "Multi-format scene import (OBJ, STL, glTF, COLLADA, 3MF)"


def test_the_table_prices_every_printable_ascii_character() -> None:
    missing = [chr(code) for code in range(32, 127) if chr(code) not in WIDTHS]
    assert missing == []
    assert all(0 < width <= 20 for width in WIDTHS.values())


def test_a_character_outside_the_table_is_charged_a_full_em() -> None:
    assert text_px("中") == pytest.approx(FALLBACK_PX * 1.04, abs=0.1)


def test_the_model_is_the_envelope_so_it_prices_text_above_a_typical_font() -> None:
    # Trebuchet MS averages 8.11 px a character over printable ASCII at 16 px; the envelope of
    # five fonts, with its margin for unmeasured ones, is wider than every one of them.
    sample = "Aspose.Cells FOSS for Python"
    assert text_px(sample) > len(sample) * 8.11


def test_wrapping_is_deterministic_and_never_loses_or_splits_a_word() -> None:
    for budget in (120.0, 160.0, 200.0, 400.0):
        lines = wrap_label(LONG, budget)
        assert lines == wrap_label(LONG, budget)
        assert " ".join(lines).split() == LONG.split()
        assert all(line == line.strip() and "  " not in line for line in lines)


def test_every_line_fits_the_budget_unless_it_is_one_word_wider_than_the_budget() -> None:
    for budget in (110.0, 140.0, 160.0, 200.0):
        for line in wrap_label(LONG, budget):
            assert text_px(line) <= budget or len(line.split()) == 1


def test_a_word_wider_than_the_budget_stands_alone_and_is_not_broken() -> None:
    wide = "W" * 40
    lines = wrap_label(f"ab {wide} cd", 100.0)
    assert lines == ("ab", wide, "cd")
    assert widest_token_px(f"ab {wide} cd") == text_px(wide)


def test_the_lines_are_evened_inside_the_line_count_greedy_fill_decides() -> None:
    label = "Auto filters with color, dynamic, top-10, and custom filter types"
    lines = wrap_label(label, 176.0)
    greedy_widest = 176.0
    assert len(lines) == 4
    assert max(text_px(line) for line in lines) < greedy_widest
    # Evened: no line is more than half as wide as the widest unless it is one short word.
    widest = max(text_px(line) for line in lines)
    assert all(text_px(line) > widest / 2 or len(line.split()) <= 2 for line in lines)


def test_a_label_that_fits_is_one_line_and_an_empty_label_is_none() -> None:
    assert wrap_label("Data validation", 400.0) == ("Data validation",)
    assert wrap_label("   ", 160.0) == ()
    assert label_lines("", 160.0) == 0


def test_a_narrower_budget_never_gives_fewer_lines() -> None:
    counts = [label_lines(LONG, budget) for budget in (400.0, 300.0, 200.0, 160.0, 120.0)]
    assert counts == sorted(counts)


def test_tokens_are_the_whitespace_separated_words() -> None:
    assert tokens("  a  b\tc\n") == ["a", "b", "c"]
