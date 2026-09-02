"""The pre-push hook blocks a real push against a real local remote; without it, the push works."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.hooks import BLOCK_MARKER, install_pre_push_hook
from support import init_git_repository


def _work_clone_with_bare_remote(tmp_path: Path) -> Path:
    bare_remote = tmp_path / "remote.git"
    assert run_git(["init", "-q", "--bare", "-b", "main", str(bare_remote)]).returncode == 0
    work = init_git_repository(tmp_path / "work")
    run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)
    return work


def test_hook_blocks_a_real_push_attempt(tmp_path: Path) -> None:
    work = _work_clone_with_bare_remote(tmp_path)
    hook = install_pre_push_hook(work)
    assert hook.read_text(encoding="utf-8").startswith("#!/bin/sh\n")

    result = run_git(["push", "origin", "main"], cwd=work)

    assert result.returncode != 0
    assert BLOCK_MARKER in result.stderr


def test_without_the_hook_the_same_push_succeeds(tmp_path: Path) -> None:
    work = _work_clone_with_bare_remote(tmp_path)

    result = run_git(["push", "origin", "main"], cwd=work)

    assert result.returncode == 0, result.stderr
