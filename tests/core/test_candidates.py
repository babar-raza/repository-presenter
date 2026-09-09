"""Sealed-bundle counting: one unit of progress, only from CURRENT, never silent on corrupt
evidence (TB-06, external review D6, 2026-09-08)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repository_presenter.core.candidates import (
    BundleError,
    SealedBundle,
    count_current_candidates,
    iter_sealed_bundles,
    verify_bundle,
)
from support import write_bundle


def test_missing_candidates_directory_counts_zero(tmp_path: Path) -> None:
    assert count_current_candidates(tmp_path) == 0
    assert list(iter_sealed_bundles(tmp_path)) == []


def test_iter_sealed_bundles_is_ordered_and_skips_unsealed(tmp_path: Path) -> None:
    write_bundle(tmp_path, "z__repo", "rev1", "ACCEPTED")
    write_bundle(tmp_path, "a__repo", "rev2", "READY_FOR_PROPOSAL")
    write_bundle(tmp_path, "a__repo", "rev1", None)
    (tmp_path / "candidates" / "stray.txt").write_text("", encoding="utf-8")
    assert list(iter_sealed_bundles(tmp_path)) == [
        SealedBundle("a__repo", "rev2", "READY_FOR_PROPOSAL"),
        SealedBundle("z__repo", "rev1", "ACCEPTED"),
    ]


def test_count_is_per_repository_and_only_no_op_proven(tmp_path: Path) -> None:
    write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    write_bundle(tmp_path, "a__repo", "rev2", "READY_FOR_PROPOSAL")
    write_bundle(tmp_path, "b__repo", "rev1", "ACCEPTED")
    write_bundle(tmp_path, "c__repo", "rev1", "PROVING_NO_OP")
    assert count_current_candidates(tmp_path) == 1


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("{not json", "unreadable bundle manifest"),
        ("[]", "not an object"),
        ('{"schema_version": 1}', "has no state"),
        ('{"state": ""}', "has no state"),
        ('{"state": 3}', "has no state"),
    ],
)
def test_corrupt_manifest_is_an_error(tmp_path: Path, raw: str, message: str) -> None:
    write_bundle(tmp_path, "a__repo", "rev1", None, raw=raw)
    with pytest.raises(BundleError, match=message):
        count_current_candidates(tmp_path)


def test_a_repository_with_no_current_file_is_silently_not_counted(tmp_path: Path) -> None:
    # A sealed, otherwise-valid revision that CURRENT never points at is the same as never
    # having sealed anything from count_current_candidates's point of view - it never scans
    # revision directories directly (module docstring).
    write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL", current=False)
    assert count_current_candidates(tmp_path) == 0


def test_current_naming_a_revision_with_no_bundle_is_an_error(tmp_path: Path) -> None:
    repository = tmp_path / "candidates" / "a__repo"
    repository.mkdir(parents=True)
    (repository / "CURRENT").write_text("rev1\n", encoding="utf-8")
    with pytest.raises(BundleError, match="CURRENT names revision 'rev1' with no sealed bundle"):
        count_current_candidates(tmp_path)


def test_an_older_ready_sibling_that_is_not_current_is_not_counted_or_even_read(
    tmp_path: Path,
) -> None:
    # rev1 is left with a corrupt manifest (as if _supersede_siblings never ran to retire it, or
    # a stray hand edit), but CURRENT points at rev2, which is only ACCEPTED - the repository
    # must not count, and rev1's own manifest must never even be opened: a scan-based count would
    # fail here trying to read it, not merely miscount.
    write_bundle(tmp_path, "a__repo", "rev1", None, raw="{not json", current=False)
    write_bundle(tmp_path, "a__repo", "rev2", "ACCEPTED")
    assert count_current_candidates(tmp_path) == 0


def test_verify_bundle_rejects_an_unsupported_schema_version(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 999,
        "repository": "a/repo",
        "revision": "r" * 40,
        "state": "READY_FOR_PROPOSAL",
        "files": {},
    }
    write_bundle(tmp_path, "a__repo", "rev1", None, raw=json.dumps(manifest))
    with pytest.raises(BundleError, match="unsupported schema_version 999"):
        verify_bundle(tmp_path / "candidates" / "a__repo" / "rev1")
    with pytest.raises(BundleError, match="unsupported schema_version"):
        count_current_candidates(tmp_path)


def test_verify_bundle_rejects_an_empty_inventory(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "repository": "a/repo",
        "revision": "rev1",
        "state": "READY_FOR_PROPOSAL",
        "files": {},
    }
    write_bundle(tmp_path, "a__repo", "rev1", None, raw=json.dumps(manifest))
    with pytest.raises(BundleError, match="lists no files"):
        count_current_candidates(tmp_path)


def test_count_current_candidates_rejects_a_manifest_whose_revision_disagrees_with_current(
    tmp_path: Path,
) -> None:
    digest = {"README.md": {"sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}}
    manifest = {
        "schema_version": 1,
        "repository": "a/repo",
        "revision": "a-different-revision",
        "state": "READY_FOR_PROPOSAL",
        "files": digest,
    }
    bundle = write_bundle(tmp_path, "a__repo", "rev1", None, raw=json.dumps(manifest))
    (bundle / "README.md").write_bytes(b"")
    with pytest.raises(BundleError, match="does not match CURRENT 'rev1'"):
        count_current_candidates(tmp_path)


def test_count_current_candidates_rejects_a_manifest_whose_repository_disagrees_with_its_directory(
    tmp_path: Path,
) -> None:
    digest = {"README.md": {"sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}}
    manifest = {
        "schema_version": 1,
        "repository": "someone-else/repo",
        "revision": "rev1",
        "state": "READY_FOR_PROPOSAL",
        "files": digest,
    }
    bundle = write_bundle(tmp_path, "a__repo", "rev1", None, raw=json.dumps(manifest))
    (bundle / "README.md").write_bytes(b"")
    with pytest.raises(BundleError, match="does not match its directory"):
        count_current_candidates(tmp_path)


def test_verify_bundle_none_without_a_bundle_and_rejects_a_corrupt_or_missing_artifact(
    tmp_path: Path,
) -> None:
    assert verify_bundle(tmp_path / "nowhere") is None
    bundle = write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    assert verify_bundle(bundle) is not None
    (bundle / "README.md").write_bytes(b"tampered")
    with pytest.raises(BundleError, match=r"artifact README\.md is corrupt"):
        verify_bundle(bundle)
    (bundle / "README.md").unlink()
    with pytest.raises(BundleError, match=r"artifact README\.md is missing"):
        verify_bundle(bundle)
