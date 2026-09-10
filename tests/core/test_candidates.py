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
    StaleCandidate,
    count_current_candidates,
    examples_verification_summary,
    integrity_valid_candidates,
    iter_sealed_bundles,
    stale_candidates,
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


def _write_examples(bundle: Path, *outcomes: str) -> None:
    receipts = [{"ordinal": i + 1, "outcome": outcome} for i, outcome in enumerate(outcomes)]
    (bundle / "examples.json").write_text(json.dumps(receipts), encoding="utf-8")


def test_examples_verification_summary_counts_executed_out_of_total_across_current_bundles(
    tmp_path: Path,
) -> None:
    """Taskcard F Tier 4: a non-blocking, portfolio-visible signal - EXECUTED against every
    outcome an examples.json can carry, summed across every counted candidate."""
    a = write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_examples(a, "EXECUTED", "EXECUTED", "NOT_VERIFIED", "FAILED")
    b = write_bundle(tmp_path, "b__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_examples(b, "EXECUTED", "TIMED_OUT")
    assert examples_verification_summary(tmp_path) == (3, 6)


def test_examples_verification_summary_ignores_uncounted_or_missing_examples(
    tmp_path: Path,
) -> None:
    """A candidate not in a counted state contributes nothing, even with real examples.json data;
    one with none (an ecosystem that verifies nothing, or a seal predating this file) contributes
    zero to both counts, never an error - this signal is informational only."""
    counted = write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_examples(counted, "EXECUTED")
    not_counted = write_bundle(tmp_path, "b__repo", "rev1", "ACCEPTED")
    _write_examples(not_counted, "EXECUTED", "EXECUTED")
    write_bundle(tmp_path, "c__repo", "rev1", "READY_FOR_PROPOSAL")  # no examples.json at all
    assert examples_verification_summary(tmp_path) == (1, 1)


def test_examples_verification_summary_with_no_candidates_directory_is_zero_over_zero(
    tmp_path: Path,
) -> None:
    assert examples_verification_summary(tmp_path) == (0, 0)


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


def _write_dependencies(
    bundle: Path,
    components: dict[str, str] | None = None,
    validators: dict[str, str] | None = None,
    validator_version: str | None = "3",
) -> None:
    payload: dict[str, object] = {"schema_version": 1}
    if components is not None:
        payload["components"] = components
    if validators is not None:
        payload["validators"] = validators
    if validator_version is not None:
        payload["validator_version"] = validator_version
    (bundle / "dependencies.json").write_text(json.dumps(payload), encoding="utf-8")


def test_stale_candidates_reports_every_dependency_behind_current(tmp_path: Path) -> None:
    """2026-09-09, docs/CI_AND_STALENESS_ASSESSMENT.md: this is the same rule
    docs/STATE_MACHINE.md section 9 already defines (a changed dependency reopens the candidates
    that consumed it), read back as a report instead of a human-diffed test_sealed_bytes.py
    byte comparison."""
    behind = write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_dependencies(
        behind, components={"renderer": "17", "shell": "5"}, validators={"BC-03": "1"}
    )
    current = write_bundle(tmp_path, "b__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_dependencies(
        current, components={"renderer": "18", "shell": "5"}, validators={"BC-03": "2"}
    )
    found = stale_candidates(
        tmp_path,
        current_components={"renderer": "18", "shell": "5", "normalisation": "1"},
        current_validators={"BC-03": "2"},
        current_validator_version="3",
    )
    assert found == [
        StaleCandidate(
            "a__repo",
            "rev1",
            ("components.renderer 17 -> 18", "validators.BC-03 1 -> 2"),
        )
    ]


def test_stale_candidates_ignores_a_dependency_the_running_code_has_never_heard_of(
    tmp_path: Path,
) -> None:
    # A dependencies.json that never recorded a given component/check (an older schema) is not
    # judged stale for it - only a genuinely older recorded value counts, never an absence.
    bundle = write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")
    _write_dependencies(bundle, components={}, validators={}, validator_version=None)
    assert (
        stale_candidates(
            tmp_path,
            current_components={"renderer": "18"},
            current_validators={"BC-03": "2"},
            current_validator_version="3",
        )
        == []
    )


def test_stale_candidates_skips_a_candidate_with_no_dependencies_file_or_no_current_pointer(
    tmp_path: Path,
) -> None:
    write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")  # no dependencies.json
    write_bundle(tmp_path, "b__repo", "rev1", "READY_FOR_PROPOSAL", current=False)
    assert (
        stale_candidates(
            tmp_path,
            current_components={"renderer": "18"},
            current_validators={},
            current_validator_version="1",
        )
        == []
    )
    assert stale_candidates(tmp_path, {}, {}, "1") == []
    assert count_current_candidates(tmp_path) == 1  # unaffected: a_repo alone counts


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


def test_integrity_valid_candidates_with_no_candidates_directory_is_zero(tmp_path: Path) -> None:
    assert integrity_valid_candidates(tmp_path) == 0


def test_integrity_valid_candidates_counts_only_current_bundles_that_pass_verification(
    tmp_path: Path,
) -> None:
    """PA-03's second count: a pass/fail wrapper, never raising - a corrupt CURRENT bundle
    simply is not counted, the same way count_current_candidates raises on it (checked
    separately, above) but this one must not."""
    write_bundle(tmp_path, "a__repo", "rev1", "READY_FOR_PROPOSAL")  # valid, counted
    write_bundle(tmp_path, "b__repo", "rev1", "ACCEPTED")  # valid but not READY - still counted
    tampered = write_bundle(tmp_path, "c__repo", "rev1", "READY_FOR_PROPOSAL")
    (tampered / "README.md").write_bytes(b"tampered")  # digest mismatch - integrity failure
    write_bundle(tmp_path, "d__repo", "rev1", "READY_FOR_PROPOSAL", current=False)  # no CURRENT
    assert integrity_valid_candidates(tmp_path) == 2


def test_integrity_valid_candidates_does_not_raise_on_a_current_naming_no_bundle(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "candidates" / "a__repo"
    repository.mkdir(parents=True)
    (repository / "CURRENT").write_text("rev1\n", encoding="utf-8")
    assert integrity_valid_candidates(tmp_path) == 0
