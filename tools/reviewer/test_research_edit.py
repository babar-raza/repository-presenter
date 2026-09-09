"""Regression tests for research_edit.py's append_entry, safe_replace, and load_yaml_block.

SR-02 (plans/healing/self-review-remediation.md). Every case runs against a `tmp_path` fixture,
never the real docs/*.md files - a test that mutates the real governance docs would itself be a
bug (this file's own established rule, see research_edit.py's own module docstring).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# tools/reviewer/ is deliberately outside pyproject.toml's pythonpath (["tests"] only, this
# directory's own boundary from src/ - tools/README.md) - inserted here, in this one file, rather
# than adding a conftest.py, to keep this taskcard's own footprint to the single file it names.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_edit import append_entry, load_yaml_block, safe_replace


def test_append_entry_adds_a_new_entry_onto_an_existing_multi_entry_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "DECISION_LOG.md"
    target.write_text(
        "# Decision Log\n\n- entry one\n\n- entry two\n", encoding="utf-8", newline="\n"
    )
    result = append_entry(target, "- entry three\n")
    assert result == "# Decision Log\n\n- entry one\n\n- entry two\n\n- entry three\n"
    assert target.read_text(encoding="utf-8") == result
    # A second append lands after the first, still separated by exactly one blank line - the
    # append shape this file exists to stop reimplementing ad hoc, every time.
    again = append_entry(target, "- entry four\n")
    assert again.endswith("- entry three\n\n- entry four\n")


def test_append_entry_handles_a_file_with_no_trailing_newline(tmp_path: Path) -> None:
    target = tmp_path / "no_trailing_newline.md"
    target.write_text("# Title\n\n- only entry", encoding="utf-8", newline="\n")
    result = append_entry(target, "- new entry\n")
    assert result == "# Title\n\n- only entry\n\n- new entry\n"
    # newline="\n" (the Windows trap, project/loop-prompt.md section 3): no stray \r\n introduced.
    assert b"\r" not in target.read_bytes()


def test_append_entry_strips_leading_and_trailing_blank_lines_from_the_new_entry(
    tmp_path: Path,
) -> None:
    target = tmp_path / "file.md"
    target.write_text("# Title\n\n- one\n", encoding="utf-8", newline="\n")
    result = append_entry(target, "\n\n- two\n\n\n")
    assert result == "# Title\n\n- one\n\n- two\n"


def test_safe_replace_raises_instead_of_silently_no_opping_on_a_count_mismatch(
    tmp_path: Path,
) -> None:
    target = tmp_path / "state.yaml"
    target.write_text("a: 1\nb: 2\na: 1\n", encoding="utf-8", newline="\n")
    with pytest.raises(AssertionError, match="found 2 times.*expected 1"):
        safe_replace(target, "a: 1", "a: 9", expected_count=1)
    # Never a silent no-op: the file on disk is byte-for-byte unchanged after the raise.
    assert target.read_text(encoding="utf-8") == "a: 1\nb: 2\na: 1\n"


def test_safe_replace_succeeds_when_the_count_matches(tmp_path: Path) -> None:
    target = tmp_path / "state.yaml"
    target.write_text("a: 1\nb: 2\n", encoding="utf-8", newline="\n")
    result = safe_replace(target, "a: 1", "a: 9", expected_count=1)
    assert result == "a: 9\nb: 2\n"
    assert target.read_text(encoding="utf-8") == result


def test_load_yaml_block_raises_before_anything_is_written_on_malformed_yaml() -> None:
    # The write-before-validate risk research_edit.py's own module docstring names: a caller
    # combining safe_replace then load_yaml_block must see the parse failure before trusting the
    # write - proven here directly against load_yaml_block, which replace_and_validate composes.
    text = "prose before\n\n```yaml\n- id: G4-W17\n  purpose: [unterminated\n```\n\nprose after\n"
    with pytest.raises(
        yaml.YAMLError
    ):  # yaml.safe_load's own parse error, not this module's
        load_yaml_block(text, "- id: G4-W17")


def test_load_yaml_block_raises_when_the_marker_or_its_fence_is_missing() -> None:
    with pytest.raises(AssertionError, match="not found"):
        load_yaml_block("no marker here", "- id: G4-W17")
    with pytest.raises(AssertionError, match="no enclosing"):
        load_yaml_block("- id: G4-W17\nno fence around it", "- id: G4-W17")


def test_load_yaml_block_parses_a_real_fenced_block_keyed_by_item_id() -> None:
    text = (
        "prose\n\n```yaml\n- id: G4-W17\n  purpose: land shared fixes\n"
        "- id: G4-W16\n  purpose: something else\n```\n"
    )
    items = load_yaml_block(text, "- id: G4-W17")
    assert set(items) == {"G4-W17", "G4-W16"}
    assert items["G4-W17"]["purpose"] == "land shared fixes"
