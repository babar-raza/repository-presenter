"""Git provenance of an authorization record: it must pre-date the run that consumes it.

An authorization the consuming run could write for itself is no authorization. The run's
``GITHUB_SHA`` (the commit it was triggered at) is fixed when the run is dispatched and no step can
change it. A record therefore counts only when the commit that last touched its file

1. is reachable from ``origin/main`` (it was merged through whatever review ``main`` requires), and
2. is an ancestor of - or equal to - the trigger commit (it existed when the run was dispatched).

A record created, edited, or pushed by the run itself, or one that only exists in the working tree,
on an unmerged branch, or as an uncommitted edit, fails one of those and is refused with
``AUTHORIZATION_NOT_COMMITTED``. A shallow clone cannot answer these questions, so it also refuses
(the workflow must check out full history). The mechanism needs no repository setting; protecting
``main`` with required reviews strengthens "reviewed", and a protected GitHub Environment with
required reviewers is the stronger alternative recorded in ``docs/DECISION_LOG.md``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError

MAIN_REF = "refs/remotes/origin/main"

#: ``(args, cwd) -> (returncode, stdout)``; injectable so tests need no real git.
GitFn = Callable[[Sequence[str], Path], "tuple[int, str]"]


def run_git(args: Sequence[str], cwd: Path) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            env=_git_env(),
        )
    except OSError as exc:
        return 127, str(exc)
    return completed.returncode, completed.stdout


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


@dataclass(frozen=True)
class RecordProvenance:
    """Where an accepted record came from, for the audit line the caller prints."""

    commit: str
    author: str
    committed_at: str


def _refuse(message: str) -> WriteRefusedError:
    return WriteRefusedError(Refusal.AUTHORIZATION_NOT_COMMITTED, message)


def verify_record_provenance(
    record_path: Path, *, control_root: Path, trigger_sha: str, git: GitFn = run_git
) -> RecordProvenance:
    """Return the record's provenance, or raise :class:`WriteRefusedError` (typed) when it was not
    committed to ``origin/main`` before ``trigger_sha``."""
    try:
        relative = record_path.resolve().relative_to(control_root.resolve()).as_posix()
    except ValueError as exc:
        raise _refuse(f"authorization record {record_path} is outside {control_root}") from exc

    code, _ = git(["ls-files", "--error-unmatch", "--", relative], control_root)
    if code != 0:
        raise _refuse(f"authorization record {relative} is not tracked by git")
    code, _ = git(["diff", "--quiet", "HEAD", "--", relative], control_root)
    if code != 0:
        raise _refuse(f"authorization record {relative} has uncommitted changes")

    code, out = git(["log", "-n", "1", "--format=%H%x1f%an%x1f%cI", "--", relative], control_root)
    parts = out.strip().split("\x1f")
    if code != 0 or len(parts) != 3 or not parts[0]:
        raise _refuse(f"cannot establish the commit that introduced {relative}")
    commit, author, committed_at = parts

    code, _ = git(["merge-base", "--is-ancestor", commit, MAIN_REF], control_root)
    if code != 0:
        raise _refuse(
            f"authorization record {relative} (commit {commit[:12]}) is not on origin/main - merge "
            "it through review first (a shallow clone cannot prove this either: check out full "
            "history)"
        )
    code, _ = git(["merge-base", "--is-ancestor", commit, trigger_sha], control_root)
    if code != 0:
        raise _refuse(
            f"authorization record {relative} (commit {commit[:12]}) is not an ancestor of the "
            f"commit this run was triggered at ({trigger_sha[:12]}) - a run cannot authorize "
            "itself"
        )
    return RecordProvenance(commit=commit, author=author, committed_at=committed_at)
