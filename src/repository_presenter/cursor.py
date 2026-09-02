"""Read the durable implementation cursor, ``project/state.yaml``.

The cursor is the only live statement of build status. This module reads the fields the CLI
reports; it never writes the cursor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CURSOR_RELATIVE_PATH = Path("project") / "state.yaml"


class CursorError(ValueError):
    """The cursor is missing or lacks the shape the CLI depends on."""


@dataclass(frozen=True)
class Cursor:
    """The cursor fields that ``repository-presenter status`` reports."""

    current_gate_id: str
    current_gate_status: str
    active_work_item_id: str
    active_work_item_status: str
    recorded_candidates: int
    denominator: int
    canary: str


def find_project_root(start: Path) -> Path | None:
    """Return the nearest directory at or above ``start`` that holds the cursor, if any."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / CURSOR_RELATIVE_PATH).is_file():
            return directory
    return None


def load_cursor(root: Path) -> Cursor:
    """Load the cursor beneath ``root``; raise :class:`CursorError` if absent or malformed."""
    path = root / CURSOR_RELATIVE_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CursorError(f"cursor not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise CursorError(f"cursor is not valid YAML: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise CursorError(f"cursor is not a mapping: {path}")
    gate = _mapping(raw, "current_gate")
    item = _mapping(raw, "active_work_item")
    progress = _mapping(raw, "progress")
    return Cursor(
        current_gate_id=_text(gate, "id", "current_gate"),
        current_gate_status=_text(gate, "status", "current_gate"),
        active_work_item_id=_text(item, "id", "active_work_item"),
        active_work_item_status=_text(item, "status", "active_work_item"),
        recorded_candidates=_count(progress, "current_candidates", "progress"),
        denominator=_count(progress, "denominator", "progress"),
        canary=_text(progress, "canary", "progress"),
    )


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CursorError(f"cursor field {key!r} must be a mapping")
    return value


def _text(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value:
        raise CursorError(f"cursor field {context}.{key} must be a non-empty string")
    return value


def _count(parent: dict[str, Any], key: str, context: str) -> int:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CursorError(f"cursor field {context}.{key} must be a non-negative integer")
    return value
