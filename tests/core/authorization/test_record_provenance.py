"""An authorization record counts only if it was merged to origin/main before the run's trigger
commit. These tests use a real disposable git repository: the property is about git history, so a
fake would only restate the implementation."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.core.authorization.record_provenance import verify_record_provenance
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.git_safety.git import run_git
from support import commit_all, head_revision, init_git_repository, merge_to_origin_main

RECORD = "ops/proposal-authorizations/record.json"


def _write(root: Path, text: str = "{}\n") -> Path:
    path = root / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _refused(root: Path, trigger: str) -> WriteRefusedError:
    with pytest.raises(WriteRefusedError) as info:
        verify_record_provenance(root / RECORD, control_root=root, trigger_sha=trigger)
    assert info.value.code is Refusal.AUTHORIZATION_NOT_COMMITTED
    return info.value


def test_a_record_merged_before_the_trigger_commit_is_accepted(tmp_path: Path) -> None:
    _write(tmp_path)
    record_commit = merge_to_origin_main(tmp_path, "approve the candidate")
    (tmp_path / "later.txt").write_text("unrelated\n", encoding="utf-8")
    trigger = merge_to_origin_main(tmp_path, "an unrelated later change")

    provenance = verify_record_provenance(
        tmp_path / RECORD, control_root=tmp_path, trigger_sha=trigger
    )
    assert provenance.commit == record_commit
    assert provenance.author == "Test"


def test_a_record_created_after_the_trigger_commit_is_refused_a_run_cannot_authorize_itself(
    tmp_path: Path,
) -> None:
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    trigger = merge_to_origin_main(tmp_path, "the commit the run is triggered at")
    _write(tmp_path)
    merge_to_origin_main(tmp_path, "record pushed by the run itself")

    error = _refused(tmp_path, trigger)
    assert "not an ancestor" in str(error)


def test_a_record_edited_after_the_trigger_commit_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, '{"expires_at": "2026-10-01T01:00:00Z"}\n')
    trigger = merge_to_origin_main(tmp_path, "original approval")
    _write(tmp_path, '{"expires_at": "2099-01-01T00:00:00Z"}\n')
    merge_to_origin_main(tmp_path, "run extends its own authorization")

    _refused(tmp_path, trigger)


def test_a_record_committed_locally_but_not_on_origin_main_is_refused(tmp_path: Path) -> None:
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    merge_to_origin_main(tmp_path, "main")
    _write(tmp_path)
    local = commit_all(tmp_path, "local only, never merged")

    error = _refused(tmp_path, local)
    assert "not on origin/main" in str(error)


def test_an_uncommitted_record_is_refused(tmp_path: Path) -> None:
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    trigger = merge_to_origin_main(tmp_path, "main")
    _write(tmp_path)

    error = _refused(tmp_path, trigger)
    assert "not tracked" in str(error)


def test_a_tracked_record_with_working_tree_edits_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, "approved\n")
    trigger = merge_to_origin_main(tmp_path, "approval")
    _write(tmp_path, "edited after checkout\n")

    error = _refused(tmp_path, trigger)
    assert "uncommitted changes" in str(error)


def test_a_clone_without_origin_main_cannot_establish_provenance(tmp_path: Path) -> None:
    init_git_repository(tmp_path, with_commit=False)
    _write(tmp_path)
    trigger = commit_all(tmp_path, "approval, but no origin/main ref (shallow or fresh clone)")

    _refused(tmp_path, trigger)


def test_a_record_outside_the_control_root_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "control"
    root.mkdir()
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    trigger = merge_to_origin_main(root, "main")
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("{}\n", encoding="utf-8")

    with pytest.raises(WriteRefusedError) as info:
        verify_record_provenance(elsewhere, control_root=root, trigger_sha=trigger)
    assert info.value.code is Refusal.AUTHORIZATION_NOT_COMMITTED


def test_head_is_an_acceptable_trigger_for_a_local_checkout_on_main(tmp_path: Path) -> None:
    _write(tmp_path)
    merge_to_origin_main(tmp_path, "approval")
    assert run_git(["rev-parse", "HEAD"], cwd=tmp_path).returncode == 0
    provenance = verify_record_provenance(
        tmp_path / RECORD, control_root=tmp_path, trigger_sha="HEAD"
    )
    assert provenance.commit == head_revision(tmp_path)
