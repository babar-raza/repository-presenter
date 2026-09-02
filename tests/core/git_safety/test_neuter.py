"""Push neutering replaces the origin push URL with a non-URL."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.neuter import DISABLED_PUSH_URL, neuter_push
from support import init_git_repository


def test_neuter_disables_push_but_keeps_fetch(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "repo")
    run_git(["remote", "add", "origin", "https://github.com/example/example.git"], cwd=repo)

    neuter_push(repo)

    remotes = run_git(["remote", "-v"], cwd=repo).stdout
    assert f"origin\t{DISABLED_PUSH_URL} (push)" in remotes
    assert "origin\thttps://github.com/example/example.git (fetch)" in remotes


def test_neuter_fails_closed_without_an_origin(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "repo")
    with pytest.raises(GitSafetyError, match="failed to neuter push remote"):
        neuter_push(repo)
