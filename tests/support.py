"""Builders for synthetic project roots: a cursor and sealed candidate bundles."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def write_cursor(
    root: Path,
    *,
    gate: str = "G0_FOUNDATION",
    gate_status: str = "READY",
    work_item: str = "G0-W01",
    work_item_status: str = "READY",
    recorded_candidates: int = 0,
    denominator: int = 34,
    canary: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
) -> Path:
    """Write a minimal cursor with the fields the CLI reports."""
    path = root / "project" / "state.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        "progress:",
        f"  current_candidates: {recorded_candidates}",
        f"  denominator: {denominator}",
        f"  canary: {canary}",
        "current_gate:",
        f"  id: {gate}",
        f"  status: {gate_status}",
        "active_work_item:",
        f"  id: {work_item}",
        f"  status: {work_item_status}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_bundle(
    root: Path,
    repository_dir: str,
    revision: str,
    state: str | None,
    *,
    raw: str | None = None,
) -> Path:
    """Create a bundle directory; seal it with a manifest when ``state`` or ``raw`` is given."""
    bundle = root / "candidates" / repository_dir / revision
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / "manifest.json"
    if raw is not None:
        manifest.write_text(raw, encoding="utf-8")
    elif state is not None:
        manifest.write_text(json.dumps({"schema_version": 1, "state": state}), encoding="utf-8")
    return bundle
