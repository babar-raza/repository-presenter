"""Sealed-bundle counting: one unit of progress, never silent on corrupt evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.core.candidates import (
    BundleError,
    SealedBundle,
    count_current_candidates,
    iter_sealed_bundles,
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
