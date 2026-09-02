"""Builders for synthetic project roots, cursors, sealed bundles, and disposable git repos."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.core.git_safety.git import run_git

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


def init_git_repository(path: Path, *, with_commit: bool = True) -> Path:
    """A disposable local repository on branch ``main`` with a local identity."""
    path.mkdir(parents=True, exist_ok=True)
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        result = run_git(args, cwd=path)
        assert result.returncode == 0, result.stderr
    if with_commit:
        (path / "README.md").write_text("# test\n", encoding="utf-8")
        commit_all(path, "initial")
    return path


def commit_all(path: Path, message: str) -> str:
    """Stage everything, commit, and return the new HEAD revision."""
    assert run_git(["add", "."], cwd=path).returncode == 0
    result = run_git(["commit", "-q", "-m", message], cwd=path)
    assert result.returncode == 0, result.stderr
    return head_revision(path)


def head_revision(path: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd=path)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()
