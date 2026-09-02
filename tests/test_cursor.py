"""Cursor reading reports the live build status and rejects malformed state."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.cursor import CursorError, find_project_root, load_cursor
from support import write_cursor


def test_load_cursor_reads_reported_fields(tmp_path: Path) -> None:
    write_cursor(
        tmp_path,
        gate="G1_FIRST_VALID_CANDIDATE",
        gate_status="IN_PROGRESS",
        work_item="G1-W01",
        work_item_status="VERIFYING",
        recorded_candidates=1,
    )
    cursor = load_cursor(tmp_path)
    assert cursor.current_gate_id == "G1_FIRST_VALID_CANDIDATE"
    assert cursor.current_gate_status == "IN_PROGRESS"
    assert cursor.active_work_item_id == "G1-W01"
    assert cursor.active_work_item_status == "VERIFYING"
    assert cursor.recorded_candidates == 1
    assert cursor.denominator == 34
    assert cursor.canary == "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def test_find_project_root_walks_upward(tmp_path: Path) -> None:
    write_cursor(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == tmp_path.resolve()


def test_load_cursor_requires_the_file(tmp_path: Path) -> None:
    with pytest.raises(CursorError, match="cursor not found"):
        load_cursor(tmp_path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("- not a mapping\n", "not a mapping"),
        ("current_gate: [\n", "not valid YAML"),
        ("current_gate: {id: G0, status: READY}\n", "'active_work_item' must be a mapping"),
        (
            "current_gate: {id: '', status: READY}\n"
            "active_work_item: {id: W, status: READY}\n"
            "progress: {current_candidates: 0, denominator: 34, canary: c}\n",
            "current_gate.id must be a non-empty string",
        ),
        (
            "current_gate: {id: G0, status: READY}\n"
            "active_work_item: {id: W, status: READY}\n"
            "progress: {current_candidates: 0, denominator: '34', canary: c}\n",
            "progress.denominator must be a non-negative integer",
        ),
        (
            "current_gate: {id: G0, status: READY}\n"
            "active_work_item: {id: W, status: READY}\n"
            "progress: {current_candidates: true, denominator: 34, canary: c}\n",
            "progress.current_candidates must be a non-negative integer",
        ),
        (
            "current_gate: {id: G0, status: READY}\n"
            "active_work_item: {id: W, status: READY}\n"
            "progress: {current_candidates: -1, denominator: 34, canary: c}\n",
            "progress.current_candidates must be a non-negative integer",
        ),
    ],
)
def test_load_cursor_rejects_malformed_state(tmp_path: Path, content: str, message: str) -> None:
    path = write_cursor(tmp_path)
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CursorError, match=message):
        load_cursor(tmp_path)
