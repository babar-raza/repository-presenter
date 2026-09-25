"""Regression tests for reconcile.py's bucketing and defect-index escalation logic.

Each helper that reads a small, self-contained file (registry.json, DEFECT_INDEX.md, a candidate
bundle's CURRENT/manifest.json) is tested against a `tmp_path` fixture, never the real repo -
matching test_research_edit.py's own established rule for this directory. `reconcile()` itself
also calls `repository_presenter.core.candidates.stale_candidates`, which expects a full sealed
bundle's `dependencies.json`/component-version shape; building a synthetic one for every case here
would duplicate that function's own test suite rather than testing this file's actual logic (the
bucketing and priority order), so `reconcile()` end-to-end is verified by running it live against
this repository's real state instead (2026-09-25, output recorded in the commit that added this
file) - the same "run it for real once, unit-test the pieces" split this project's own CI uses for
present vs its component checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reconcile import _dirname_to_repo, _enabled_registry_entries, _escalated_defect_classes, _invalidated_repos


def test_dirname_to_repo_splits_on_the_first_double_underscore_only() -> None:
    assert _dirname_to_repo("aspose-words-foss__Aspose.Words-FOSS-for-Python") == (
        "aspose-words-foss/Aspose.Words-FOSS-for-Python"
    )


def _write_registry(tmp_path: Path, entries: list[dict]) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "registry.json").write_text(
        json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8"
    )


def test_enabled_registry_entries_excludes_disabled_mode(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {"repository": "aspose-a-foss/A", "mode": "dry_run"},
            {"repository": "aspose-b-foss/B", "mode": "full"},
            {"repository": "aspose-c-foss/C", "mode": "disabled"},
        ],
    )
    assert _enabled_registry_entries(tmp_path) == ["aspose-a-foss/A", "aspose-b-foss/B"]


def test_escalated_defect_classes_requires_three_sightings_and_open_status(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "DEFECT_INDEX.md").write_text(
        "# Defect class index\n\n"
        "## Open\n\n"
        "### `two_sightings.mechanism`\n\n"
        "| # | Repository | Sub-shape | Date | Evidence |\n"
        "|---|---|---|---|---|\n"
        "| 1 | repo-a | x | d1 | e1 |\n"
        "| 2 | repo-b | x | d2 | e2 |\n\n"
        "### `three_sightings.mechanism`\n\n"
        "| # | Repository | Sub-shape | Date | Evidence |\n"
        "|---|---|---|---|---|\n"
        "| 1 | repo-a | x | d1 | e1 |\n"
        "| 2 | repo-b | x | d2 | e2 |\n"
        "| 3 | repo-c | x | d3 | e3 |\n\n"
        "## Resolved\n\n"
        "### `three_sightings_but_resolved.mechanism`\n\n"
        "| # | Repository | Sub-shape | Date | Evidence |\n"
        "|---|---|---|---|---|\n"
        "| 1 | repo-a | x | d1 | e1 |\n"
        "| 2 | repo-b | x | d2 | e2 |\n"
        "| 3 | repo-c | x | d3 | e3 |\n",
        encoding="utf-8",
    )
    assert _escalated_defect_classes(tmp_path) == ["three_sightings.mechanism"]


def test_escalated_defect_classes_handles_a_missing_file(tmp_path: Path) -> None:
    assert _escalated_defect_classes(tmp_path) == []


def _seal(candidates_dir: Path, dirname: str, revision: str, state: str) -> None:
    bundle = candidates_dir / dirname / revision
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "manifest.json").write_text(json.dumps({"state": state}), encoding="utf-8")
    (candidates_dir / dirname / "CURRENT").write_text(revision, encoding="utf-8")


def test_invalidated_repos_reads_the_current_pointed_manifest(tmp_path: Path) -> None:
    candidates_dir = tmp_path / "candidates"
    _seal(candidates_dir, "aspose-a-foss__A", "rev1", "READY_FOR_PROPOSAL")
    _seal(candidates_dir, "aspose-b-foss__B", "rev1", "INVALIDATED")
    assert _invalidated_repos(candidates_dir) == {"aspose-b-foss/B"}


def test_invalidated_repos_ignores_a_repository_with_no_current_pointer(tmp_path: Path) -> None:
    candidates_dir = tmp_path / "candidates"
    (candidates_dir / "aspose-a-foss__A").mkdir(parents=True)
    assert _invalidated_repos(candidates_dir) == set()


def test_invalidated_repos_handles_a_missing_candidates_directory(tmp_path: Path) -> None:
    assert _invalidated_repos(tmp_path / "does-not-exist") == set()
