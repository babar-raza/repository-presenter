"""Snapshot capture is deterministic per revision and fails closed on drift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.core.errors import RepositorySnapshotError
from repository_presenter.core.git_safety.clone import ReadOnlyClone, pinned_read_only_clone
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.snapshot.capture import (
    capture_snapshot,
    verify_snapshot,
    write_source_artifacts,
)
from support import commit_all, head_revision, init_git_repository

REPOSITORY = "example-org/Aspose.Example-FOSS-for-Python"


def _source(tmp_path: Path, *, readme: bool = True) -> Path:
    source = init_git_repository(tmp_path / "source", with_commit=False)
    if readme:
        (source / "README.md").write_bytes(b"# Example\r\n\nA Python library.\n\xe2\x9c\x93\n")
    (source / "License.txt").write_text("MIT\n", encoding="utf-8")
    (source / "pkg").mkdir()
    (source / "pkg" / "__init__.py").write_text("VERSION = '1.0'\n", encoding="utf-8")
    commit_all(source, "seed")
    return source


def _clone(tmp_path: Path, source: Path, name: str = "clone") -> ReadOnlyClone:
    return pinned_read_only_clone(str(source), tmp_path / name)


def test_capture_records_revision_tree_readme_and_license(tmp_path: Path) -> None:
    source = _source(tmp_path)
    clone = _clone(tmp_path, source)

    snapshot = capture_snapshot(REPOSITORY, clone)

    assert snapshot.repository == REPOSITORY
    assert snapshot.clone_url == str(source)
    assert snapshot.source_revision == head_revision(source)
    assert snapshot.tree_entries == 3
    assert len(snapshot.tree_sha256) == 64
    assert snapshot.readme_path == "README.md"
    assert snapshot.readme_sha256 is not None and len(snapshot.readme_sha256) == 64
    assert snapshot.license_path == "License.txt"
    verify_snapshot(snapshot, clone.path)


def test_capture_without_a_readme_records_its_absence(tmp_path: Path) -> None:
    clone = _clone(tmp_path, _source(tmp_path, readme=False))
    snapshot = capture_snapshot(REPOSITORY, clone)
    assert (snapshot.readme_path, snapshot.readme_sha256) == (None, None)
    artifacts = write_source_artifacts(snapshot, clone.path, tmp_path / "source_artifacts")
    assert artifacts.files == ("snapshot.json", "tree.txt")


def test_source_artifacts_carry_exact_bytes_and_no_host_details(tmp_path: Path) -> None:
    source = _source(tmp_path)
    clone = _clone(tmp_path, source)
    snapshot = capture_snapshot(REPOSITORY, clone)

    artifacts = write_source_artifacts(snapshot, clone.path, tmp_path / "out" / "source")

    assert artifacts.files == ("README.md", "snapshot.json", "tree.txt")
    assert (artifacts.directory / "README.md").read_bytes() == (source / "README.md").read_bytes()
    tree = (artifacts.directory / "tree.txt").read_text(encoding="utf-8")
    assert [line.split("\t")[1] for line in tree.splitlines()] == [
        "License.txt",
        "README.md",
        "pkg/__init__.py",
    ]
    document = json.loads((artifacts.directory / "snapshot.json").read_text(encoding="utf-8"))
    assert document["source_revision"] == snapshot.source_revision
    assert document["schema_version"] == 1
    assert document["clone_url"] == str(source)
    without_url = {key: value for key, value in document.items() if key != "clone_url"}
    assert str(tmp_path) not in json.dumps(without_url)
    assert tmp_path.as_posix() not in json.dumps(without_url)
    assert "captured_at" not in document


def test_two_captures_of_the_same_revision_are_byte_identical(tmp_path: Path) -> None:
    source = _source(tmp_path)
    first_clone = _clone(tmp_path, source, "first")
    second_clone = _clone(tmp_path, source, "second")

    first = write_source_artifacts(
        capture_snapshot(REPOSITORY, first_clone), first_clone.path, tmp_path / "a" / "source"
    )
    second = write_source_artifacts(
        capture_snapshot(REPOSITORY, second_clone), second_clone.path, tmp_path / "b" / "source"
    )

    assert first.digest == second.digest
    for name in first.files:
        assert (first.directory / name).read_bytes() == (second.directory / name).read_bytes()


def test_rewriting_artifacts_clears_stale_files(tmp_path: Path) -> None:
    clone = _clone(tmp_path, _source(tmp_path))
    snapshot = capture_snapshot(REPOSITORY, clone)
    directory = tmp_path / "artifacts"
    directory.mkdir()
    (directory / "stale.json").write_text("{}", encoding="utf-8")

    artifacts = write_source_artifacts(snapshot, clone.path, directory)

    assert "stale.json" not in artifacts.files
    assert not (directory / "stale.json").exists()


def test_capture_rejects_a_clone_that_is_not_at_its_pinned_revision(tmp_path: Path) -> None:
    source = _source(tmp_path)
    clone = _clone(tmp_path, source)
    stale = ReadOnlyClone(clone.path, clone.clone_url, "0" * 40, clone.proof)
    with pytest.raises(RepositorySnapshotError, match="not the pinned"):
        capture_snapshot(REPOSITORY, stale)


def test_verify_fails_closed_when_the_readme_changes(tmp_path: Path) -> None:
    clone = _clone(tmp_path, _source(tmp_path))
    snapshot = capture_snapshot(REPOSITORY, clone)
    (clone.path / "README.md").write_text("# Mutated\n", encoding="utf-8")
    with pytest.raises(RepositorySnapshotError, match="README changed"):
        verify_snapshot(snapshot, clone.path)


def test_verify_fails_closed_when_the_revision_moves(tmp_path: Path) -> None:
    clone = _clone(tmp_path, _source(tmp_path))
    snapshot = capture_snapshot(REPOSITORY, clone)
    run_git(["config", "user.email", "t@example.com"], cwd=clone.path)
    run_git(["config", "user.name", "T"], cwd=clone.path)
    (clone.path / "NEW.txt").write_text("x\n", encoding="utf-8")
    commit_all(clone.path, "local drift")
    with pytest.raises(RepositorySnapshotError, match="revision drifted"):
        verify_snapshot(snapshot, clone.path)


def test_verify_fails_closed_when_the_clone_disappears(tmp_path: Path) -> None:
    clone = _clone(tmp_path, _source(tmp_path))
    snapshot = capture_snapshot(REPOSITORY, clone)
    with pytest.raises(RepositorySnapshotError, match="disappeared"):
        verify_snapshot(snapshot, tmp_path / "gone")
