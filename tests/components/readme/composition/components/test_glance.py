"""The At a Glance label geometry: one common wrap width, at most three lines (V2 item 9)."""

from __future__ import annotations

from repository_presenter.components.readme.composition.components.glance import (
    GLANCE_LINE_CHARS,
    GLANCE_MAX_LINES,
    label_height,
    wrapped_lines,
)


def test_the_policy_is_the_contracts_own_twenty_eight_characters_and_three_lines() -> None:
    assert GLANCE_LINE_CHARS == 28 and GLANCE_MAX_LINES == 3


def test_a_short_label_is_one_line() -> None:
    assert wrapped_lines("Convert to PDF") == ["Convert to PDF"]
    assert label_height("") == 0


def test_a_label_wraps_greedily_at_whole_words() -> None:
    lines = wrapped_lines("Read and parse PostScript and EPS documents")
    assert lines == ["Read and parse PostScript", "and EPS documents"]
    assert all(len(line) <= GLANCE_LINE_CHARS for line in lines)


def test_a_word_longer_than_the_width_is_broken() -> None:
    lines = wrapped_lines("x" * 60)
    assert [len(line) for line in lines] == [28, 28, 4]


def test_wrapping_is_deterministic() -> None:
    label = "An existing OBJ, STL, 3MF, GLB, glTF, or FBX file"
    assert wrapped_lines(label) == wrapped_lines(label)
    assert label_height(label) == 2


def test_a_long_title_wraps_past_the_ceiling() -> None:
    long_title = " ".join(["Export", "scenes"] * 12)
    assert label_height(long_title) > GLANCE_MAX_LINES
