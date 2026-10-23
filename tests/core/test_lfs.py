"""Git LFS build inputs: fetched into a build copy only when the three guards all hold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core import lfs
from repository_presenter.core.execution import ExecutionResult

POINTER = b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"a" * 64 + b"\nsize 4096\n"


def _result(code: int = 0, stderr: str = "") -> ExecutionResult:
    return ExecutionResult(
        argv=("git",), return_code=code, stdout="", stderr=stderr, timed_out=False
    )


def _checkout(root: Path, attributes: str | None) -> tuple[Path, Path]:
    """A clone with an index, and a build copy holding one pointer dll and one real dll."""
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "index").write_bytes(b"DIRC")
    if attributes is not None:
        (root / ".gitattributes").write_text(attributes, encoding="utf-8", newline="\n")
    copy = root.parent / "copy"
    (copy / "packages" / "Lib").mkdir(parents=True)
    (copy / "packages" / "Lib" / "Lib.dll").write_bytes(POINTER)
    (copy / "packages" / "Real").mkdir()
    (copy / "packages" / "Real" / "Real.dll").write_bytes(b"MZ" + b"\0" * 5000)
    return root, copy


class _Recorder:
    """A fake `execute`: `git lfs version` answers, `git lfs pull` is recorded and (optionally)
    replaces the pointer files the way the real one does."""

    def __init__(self, copy: Path, *, version_ok: bool = True, pull: ExecutionResult | None = None):
        self.copy = copy
        self.version_ok = version_ok
        self.pull = pull or _result(0)
        self.calls: list[list[str]] = []
        self.environments: list[dict[str, str]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> ExecutionResult:
        self.calls.append(list(argv))
        self.environments.append(dict(kwargs.get("extra_environment") or {}))
        if argv[1:3] == ["lfs", "version"]:
            return _result(0 if self.version_ok else 1)
        if self.pull.return_code == 0:
            (self.copy / "packages" / "Lib" / "Lib.dll").write_bytes(b"MZ" + b"\0" * 5000)
        return self.pull


@pytest.fixture(autouse=True)
def _git_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lfs.shutil, "which", lambda name: "git")


def test_the_declaration_is_read_from_the_root_gitattributes(tmp_path: Path) -> None:
    root, _copy = _checkout(tmp_path / "a", "*.dll filter=lfs diff=lfs merge=lfs -text\n")
    assert lfs.declares_lfs(root)
    other, _ = _checkout(tmp_path / "b" / "c", "*.txt text eol=lf\n# *.dll filter=lfs\n")
    assert not lfs.declares_lfs(other)
    assert not lfs.declares_lfs(tmp_path / "nowhere")


def test_only_build_input_pointer_files_are_listed(tmp_path: Path) -> None:
    _root, copy = _checkout(tmp_path / "clone", "*.dll filter=lfs\n")
    (copy / "TestData").mkdir()
    (copy / "TestData" / "image.jpg").write_bytes(POINTER)  # a pointer, but not a build input
    assert lfs.pointer_files(copy) == ["packages/Lib/Lib.dll"]


def test_the_pointer_dll_is_pulled_into_the_copy_and_the_clone_is_not_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, copy = _checkout(tmp_path / "clone", "*.dll filter=lfs diff=lfs merge=lfs -text\n")
    recorder = _Recorder(copy)
    monkeypatch.setattr(lfs, "execute", recorder)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    fetched = lfs.fetch_lfs_build_inputs(root, copy, workspace, 120.0)
    assert fetched.attempted and fetched.ok
    assert "1 Git LFS build input" in fetched.note
    pull = recorder.calls[-1]
    assert pull[pull.index("lfs") :][:2] == ["lfs", "pull"]
    assert "--include=packages/Lib/Lib.dll" in pull
    assert pull[pull.index("--work-tree") + 1] == str(copy)
    # The clone's own index and object storage are not what git writes to.
    assert recorder.environments[-1]["GIT_INDEX_FILE"] == str(workspace / "lfs-index")
    assert f"lfs.storage={workspace / 'lfs-objects'}" in pull
    # The disposable HOME carries no core.longpaths, which deep-path repositories need.
    assert "core.longpaths=true" in pull
    assert (root / ".git" / "index").read_bytes() == b"DIRC"
    assert lfs.pointer_files(copy) == []


def test_no_lfs_declaration_means_no_git_call_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, copy = _checkout(tmp_path / "clone", "*.txt text\n")
    recorder = _Recorder(copy)
    monkeypatch.setattr(lfs, "execute", recorder)
    fetched = lfs.fetch_lfs_build_inputs(root, copy, tmp_path, 120.0)
    assert fetched == lfs.NOT_ATTEMPTED and fetched.note == ""
    assert recorder.calls == []
    # A repository with no .gitattributes at all is the same.
    root2, copy2 = _checkout(tmp_path / "other" / "clone", None)
    assert lfs.fetch_lfs_build_inputs(root2, copy2, tmp_path, 120.0) == lfs.NOT_ATTEMPTED


def test_a_machine_without_git_lfs_does_not_pull(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, copy = _checkout(tmp_path / "clone", "*.dll filter=lfs\n")
    recorder = _Recorder(copy, version_ok=False)
    monkeypatch.setattr(lfs, "execute", recorder)
    assert lfs.fetch_lfs_build_inputs(root, copy, tmp_path, 120.0) == lfs.NOT_ATTEMPTED
    assert [call[1:3] for call in recorder.calls] == [["lfs", "version"]]
    monkeypatch.setattr(lfs.shutil, "which", lambda name: None)
    assert lfs.fetch_lfs_build_inputs(root, copy, tmp_path, 120.0) == lfs.NOT_ATTEMPTED


def test_a_declaring_repository_with_no_pointer_build_input_pulls_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 6,000 LFS test assets a repository tracks are not build inputs and are never fetched."""
    root, copy = _checkout(tmp_path / "clone", "*.jpg filter=lfs\n")
    (copy / "packages" / "Lib" / "Lib.dll").write_bytes(b"MZ" + b"\0" * 5000)
    recorder = _Recorder(copy)
    monkeypatch.setattr(lfs, "execute", recorder)
    assert lfs.fetch_lfs_build_inputs(root, copy, tmp_path, 120.0) == lfs.NOT_ATTEMPTED
    assert all(call[1:3] != ["lfs", "pull"] and "pull" not in call for call in recorder.calls)


def test_a_pull_that_fails_is_recorded_with_what_git_said(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, copy = _checkout(tmp_path / "clone", "*.dll filter=lfs\n")
    failing = _result(2, stderr=f"error: smudge filter lfs failed in {copy}/packages")
    monkeypatch.setattr(lfs, "execute", _Recorder(copy, pull=failing))
    fetched = lfs.fetch_lfs_build_inputs(root, copy, tmp_path, 120.0)
    assert fetched.attempted and not fetched.ok
    assert "failed: error: smudge filter lfs failed" in fetched.note
    assert str(copy) not in fetched.note
    assert lfs.pointer_files(copy) == ["packages/Lib/Lib.dll"]
