"""Push neutering: the first of two independent controls that make a clone read-only."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety.git import run_git

DISABLED_PUSH_URL = "DISABLED"


def neuter_push(repo_path: Path) -> None:
    """Point the origin push URL at a non-URL so no push can ever resolve a remote."""
    result = run_git(["remote", "set-url", "--push", "origin", DISABLED_PUSH_URL], cwd=repo_path)
    if result.returncode != 0:
        raise GitSafetyError(f"failed to neuter push remote in {repo_path}: {result.stderr}")
