"""The dedup ledger: `{repository, defect_fingerprint} -> {issue_ref, filed_at_revision,
last_observed_state}`, built by reading every handoff artifact under `evidence/upstream-defects/`
(docs/investigations/03-issue-tracking.md section 4 point 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.components.issues.ledger import (
    LedgerError,
    discover_handoff_paths,
    load_ledger,
    lookup,
)
from support import REPO_ROOT

REAL_UPSTREAM_DEFECTS = REPO_ROOT / "evidence" / "upstream-defects"


def _write_handoff(
    root: Path,
    owner_name: str,
    fingerprint: str,
    *,
    repository: str,
    status: str = "HANDOFF_PENDING",
    issue_ref: dict | None = None,
    check_id: str = "BC-02",
) -> Path:
    directory = root / owner_name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{fingerprint}.json"
    payload = {
        "schema_version": 1,
        "repository": repository,
        "source_revision": "a" * 40,
        "defect_fingerprint": f"sha256:{fingerprint}",
        "triggering_check": {"id": check_id, "version": "1", "causal_stage": "EXTRACTING"},
        "evidence": [{"path": "https://pypi.org/pypi/x/json", "detail": "not found"}],
        "claim": "a plain factual sentence",
        "suggested_issue_title": "t",
        "suggested_issue_body": "b",
        "status": status,
        "issue_ref": issue_ref,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_discover_handoff_paths_on_a_missing_directory_is_empty(tmp_path: Path) -> None:
    assert discover_handoff_paths(tmp_path / "nope") == ()


def test_discover_and_load_the_real_backfilled_artifacts() -> None:
    # 2026-09-26: a third real artifact was backfilled for aspose-cells-foss/Aspose.Cells-FOSS-for-
    # Cpp's own BC-02 trigraph finding (docs/DECISION_LOG.md, this date) - the automatic hook
    # (components/issues/draft.py, commit 6fa11ad) postdated the finding, so it was never drafted
    # live; constructed instead via the real Fact/FactsDocument/draft_handoff/write_handoff path,
    # never a handwritten JSON shape.
    paths = discover_handoff_paths(REAL_UPSTREAM_DEFECTS)
    assert len(paths) == 3
    ledger = load_ledger(REAL_UPSTREAM_DEFECTS)
    assert len(ledger) == 3
    html = lookup(
        ledger,
        "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
        "sha256:ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a",
    )
    assert html is not None
    assert html.triggering_check_id == "BC-02"
    assert html.last_observed_state == "HANDOFF_PENDING"
    assert html.issue_ref is None

    cells_cpp = lookup(
        ledger,
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
        "sha256:b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365",
    )
    assert cells_cpp is not None
    assert cells_cpp.triggering_check_id == "BC-02"
    assert cells_cpp.last_observed_state == "HANDOFF_PENDING"
    assert cells_cpp.issue_ref is None


def test_lookup_is_none_for_an_unrecorded_fingerprint(tmp_path: Path) -> None:
    ledger = load_ledger(tmp_path)
    assert lookup(ledger, "o/r", "sha256:" + "a" * 64) is None


def test_lookup_finds_a_recorded_fingerprint_regardless_of_status(tmp_path: Path) -> None:
    fingerprint = "c" * 64
    _write_handoff(
        tmp_path,
        "o__r",
        fingerprint,
        repository="o/r",
        status="FILED",
        issue_ref={"number": 7, "url": "https://github.com/o/r/issues/7"},
    )
    ledger = load_ledger(tmp_path)
    entry = lookup(ledger, "o/r", f"sha256:{fingerprint}")
    assert entry is not None
    assert entry.last_observed_state == "FILED"
    assert entry.issue_ref is not None and entry.issue_ref.number == 7
    # dedup keys on the fingerprint, not the status - a filer must not draft a second handoff for
    # this pair even though it has already moved past HANDOFF_PENDING.
    assert lookup(ledger, "o/r", "sha256:" + "d" * 64) is None


def test_two_different_repositories_never_collide(tmp_path: Path) -> None:
    fingerprint = "e" * 64
    _write_handoff(tmp_path, "o1__r", fingerprint, repository="o1/r")
    _write_handoff(tmp_path, "o2__r", fingerprint, repository="o2/r")
    ledger = load_ledger(tmp_path)
    assert len(ledger) == 2
    assert lookup(ledger, "o1/r", f"sha256:{fingerprint}") is not None
    assert lookup(ledger, "o2/r", f"sha256:{fingerprint}") is not None


def test_duplicate_key_across_two_artifacts_fails_closed(tmp_path: Path) -> None:
    fingerprint = "f" * 64
    _write_handoff(tmp_path, "o__r", fingerprint, repository="o/r")
    # A second artifact directory that (incorrectly) claims the same {repository, fingerprint}.
    duplicate_dir = tmp_path / "o__r2"
    duplicate_dir.mkdir()
    payload = json.loads((tmp_path / "o__r" / f"{fingerprint}.json").read_text(encoding="utf-8"))
    (duplicate_dir / f"{fingerprint}.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(LedgerError, match="duplicate handoff"):
        load_ledger(tmp_path)
