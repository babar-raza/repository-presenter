"""Pinned read-only clones: fresh, verified, pinned, and retried on transient failure only.

No network: local disposable repositories stand in for remotes, exactly as they do for git.
"""

from __future__ import annotations

import errno
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety import clone as clone_module
from repository_presenter.core.git_safety import neuter as neuter_module
from repository_presenter.core.git_safety import verify as verify_module
from repository_presenter.core.git_safety.clone import (
    MAX_CLONE_ATTEMPTS,
    clone_pinned,
    force_rmtree,
    pinned_read_only_clone,
    remote_head_revision,
)
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.hooks import BLOCK_MARKER
from repository_presenter.core.git_safety.neuter import DISABLED_PUSH_URL
from support import commit_all, head_revision, init_git_repository


class TestRemoteHeadRevision:
    def test_returns_the_default_branch_head(self, tmp_path: Path) -> None:
        source = init_git_repository(tmp_path / "source")
        revision = remote_head_revision(str(source))
        assert revision == head_revision(source)
        assert revision is not None and len(revision) == 40

    def test_returns_none_for_an_unreachable_remote(self, tmp_path: Path) -> None:
        assert remote_head_revision(str(tmp_path / "does-not-exist")) is None

    def test_changes_after_a_new_commit(self, tmp_path: Path) -> None:
        source = init_git_repository(tmp_path / "source")
        first = remote_head_revision(str(source))
        (source / "CHANGED.txt").write_text("new commit\n", encoding="utf-8")
        second_commit = commit_all(source, "second")
        assert remote_head_revision(str(source)) == second_commit != first


class TestPinnedReadOnlyClone:
    def test_clone_is_pinned_neutered_hooked_and_verified(self, tmp_path: Path) -> None:
        source = init_git_repository(tmp_path / "source")
        destination = tmp_path / "runs" / "clones" / "example__Example"

        clone = pinned_read_only_clone(str(source), destination)

        assert clone.path == destination
        assert clone.revision == head_revision(source)
        assert head_revision(destination) == clone.revision
        assert (destination / "README.md").read_text(encoding="utf-8") == "# test\n"
        assert clone.proof.ok
        assert clone.proof.push_url == DISABLED_PUSH_URL
        push = run_git(["push", "origin", "HEAD:refs/heads/main"], cwd=destination)
        assert push.returncode != 0
        assert BLOCK_MARKER in push.stderr or "DISABLED" in push.stderr

    def test_every_clone_is_fresh(self, tmp_path: Path) -> None:
        source = init_git_repository(tmp_path / "source")
        destination = tmp_path / "clone"
        pinned_read_only_clone(str(source), destination)
        (destination / "stray.txt").write_text("must not survive\n", encoding="utf-8")

        pinned_read_only_clone(str(source), destination)

        assert not (destination / "stray.txt").exists()

    def test_a_moved_default_branch_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = init_git_repository(tmp_path / "source")
        stale = "0" * 40
        monkeypatch.setattr(clone_module, "remote_head_revision", lambda *a, **k: stale)

        with pytest.raises(GitSafetyError, match="moved from 0000000"):
            pinned_read_only_clone(str(source), tmp_path / "clone")

    def test_an_unresolvable_remote_fails_closed_before_cloning(self, tmp_path: Path) -> None:
        with pytest.raises(GitSafetyError, match="cannot resolve the default-branch revision"):
            pinned_read_only_clone(str(tmp_path / "missing"), tmp_path / "clone")
        assert not (tmp_path / "clone").exists()


def _fake_git(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[tuple[int, str]],
    destination: Path,
    revision: str,
) -> tuple[list[float | None], list[dict[str, str] | None]]:
    """Answer clone calls from ``responses`` in order and every other call as a healthy repo."""
    timeouts: list[float | None] = []
    environments: list[dict[str, str] | None] = []

    def fake_run_git(
        args: list[str], cwd: Path | None = None, timeout: float | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        if args[0] == "clone":
            timeouts.append(timeout)
            environments.append(kwargs.get("env"))
            code, stderr = responses.pop(0)
            if code == 0:
                (destination / ".git" / "hooks").mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args=args, returncode=code, stdout="", stderr=stderr)
        if args[0] == "rev-parse":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=revision, stderr="")
        if args[:2] == ["remote", "-v"]:
            stdout = f"origin\thttps://x (fetch)\norigin\t{DISABLED_PUSH_URL} (push)\n"
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(clone_module, "run_git", fake_run_git)
    monkeypatch.setattr(neuter_module, "run_git", fake_run_git)
    monkeypatch.setattr(verify_module, "run_git", fake_run_git)
    return timeouts, environments


class TestCloneRetryAndTimeout:
    URL = "https://github.com/example/private.git"
    REVISION = "d" * 40

    def test_clone_skips_lfs_smudge_and_uses_header_auth_without_the_raw_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "clone"
        _, environments = _fake_git(monkeypatch, [(0, "")], destination, self.REVISION)

        clone_pinned(self.URL, self.REVISION, destination, token="private-read-token")

        env = environments[0]
        assert env is not None
        assert env["GIT_LFS_SKIP_SMUDGE"] == "1"
        assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
        assert "private-read-token" not in env["GIT_CONFIG_VALUE_0"]

    def test_non_github_remotes_get_no_auth_header(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "clone"
        _, environments = _fake_git(monkeypatch, [(0, "")], destination, self.REVISION)
        clone_pinned("https://example.invalid/x.git", self.REVISION, destination, token="t")
        assert environments[0] == {"GIT_LFS_SKIP_SMUDGE": "1"}

    def test_retries_a_transient_timeout_then_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "clone"
        timeouts, _ = _fake_git(
            monkeypatch, [(124, "timed out"), (0, "")], destination, self.REVISION
        )
        sleeps: list[float] = []

        clone = clone_pinned(self.URL, self.REVISION, destination, timeout=42, sleep=sleeps.append)

        assert clone.revision == self.REVISION
        assert timeouts == [42, 42]
        assert len(sleeps) == 1
        assert 0 <= sleeps[0] <= clone_module.RETRY_POLICIES["clone"].maximum_seconds

    def test_does_not_retry_a_real_not_found_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "clone"
        responses = [(128, "fatal: repository 'https://github.com/example/private.git/' not found")]
        timeouts, _ = _fake_git(monkeypatch, responses, destination, self.REVISION)

        def never(_seconds: float) -> None:
            pytest.fail("a permanent error must not be retried")

        with pytest.raises(GitSafetyError, match="not found"):
            clone_pinned(self.URL, self.REVISION, destination, sleep=never)
        assert len(timeouts) == 1

    def test_gives_up_after_the_policy_bound(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "clone"
        responses = [(1, "error: RPC failed; curl 56 Recv failure")] * MAX_CLONE_ATTEMPTS
        timeouts, _ = _fake_git(monkeypatch, responses, destination, self.REVISION)

        with pytest.raises(GitSafetyError, match=f"after {MAX_CLONE_ATTEMPTS} attempts"):
            clone_pinned(self.URL, self.REVISION, destination, sleep=lambda _s: None)
        assert len(timeouts) == MAX_CLONE_ATTEMPTS


class TestForceRmtree:
    def test_removes_a_read_only_file(self, tmp_path: Path) -> None:
        victim = tmp_path / "victim"
        victim.mkdir()
        locked = victim / "readonly.txt"
        locked.write_text("git writes objects read-only", encoding="utf-8")
        os.chmod(locked, stat.S_IREAD)

        force_rmtree(victim)

        assert not victim.exists()

    @pytest.mark.skipif(sys.platform != "win32", reason="exercises Windows long-path deletion")
    def test_recovers_from_a_deep_path_dir_not_empty_error_via_long_path_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        victim = tmp_path / "victim"
        victim.mkdir()
        (victim / "file.txt").write_text("x", encoding="utf-8")
        real_rmdir = os.rmdir
        seen: list[str] = []

        def fake_rmdir(path: Any, *args: Any, **kwargs: Any) -> None:
            seen.append(str(path))
            if str(path).startswith("\\\\?\\"):
                real_rmdir(str(path), *args, **kwargs)
                return
            raise OSError(errno.ENOTEMPTY, "The directory is not empty", str(path), 145)

        monkeypatch.setattr(os, "rmdir", fake_rmdir)

        force_rmtree(victim)

        assert not victim.exists()
        assert any(p.startswith("\\\\?\\") for p in seen)

    @pytest.mark.skipif(sys.platform != "win32", reason="exercises Windows directory retry")
    def test_gives_up_after_bounded_retries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        victim = tmp_path / "victim"
        victim.mkdir()
        (victim / "file.txt").write_text("x", encoding="utf-8")

        def always_fails(path: Any, *args: Any, **kwargs: Any) -> None:
            raise OSError(errno.ENOTEMPTY, "The directory is not empty", str(path), 145)

        monkeypatch.setattr(os, "rmdir", always_fails)
        monkeypatch.setattr(clone_module.time, "sleep", lambda _s: None)

        with pytest.raises(OSError) as info:
            force_rmtree(victim)
        assert info.value.winerror == 145  # type: ignore[attr-defined]

    def test_an_unrelated_oserror_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        victim = tmp_path / "victim"
        victim.mkdir()
        (victim / "file.txt").write_text("x", encoding="utf-8")

        def fails(path: Any, *args: Any, **kwargs: Any) -> None:
            raise OSError(None, "no space left on device", str(path))

        monkeypatch.setattr(os, "rmdir", fails)

        with pytest.raises(OSError, match="no space left on device"):
            force_rmtree(victim)

    def test_the_windows_remedy_is_a_no_op_elsewhere(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        victim = tmp_path / "victim"
        victim.mkdir()
        (victim / "file.txt").write_text("x", encoding="utf-8")
        monkeypatch.setattr(clone_module.sys, "platform", "linux")

        def dir_not_empty(path: Any, *args: Any, **kwargs: Any) -> None:
            raise OSError(errno.ENOTEMPTY, "The directory is not empty", str(path), 145)

        monkeypatch.setattr(os, "rmdir", dir_not_empty)

        with pytest.raises(OSError) as info:
            force_rmtree(victim)
        assert info.value.errno == errno.ENOTEMPTY
