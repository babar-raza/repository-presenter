"""Pinned, push-neutered, read-only clones under ``runs/``.

The only git verbs ever issued against a real remote here are ``ls-remote`` and ``clone``. The
remote's default-branch revision is observed first, the clone is taken, and the checked-out
revision must equal the observed one or the clone fails closed; a race with an upstream push is
therefore a visible failure, never a silently different snapshot. Every clone is neutered and
hooked, then independently verified before it is returned.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety.git import github_https_auth_env, run_git
from repository_presenter.core.git_safety.hooks import install_pre_push_hook
from repository_presenter.core.git_safety.neuter import neuter_push
from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE
from repository_presenter.core.git_safety.verify import PushBlockProof, verify_push_blocked
from repository_presenter.core.retry import RETRY_POLICIES, RetryableOperationError, run_with_retry

CLONE_TIMEOUT_SECONDS = 600.0
MAX_CLONE_ATTEMPTS = RETRY_POLICIES["clone"].max_attempts

_TRANSIENT_CLONE_STDERR_MARKERS = (
    "Connection reset",
    "Connection timed out",
    "Connection refused",
    "Could not resolve host",
    "The remote end hung up unexpectedly",
    "early EOF",
    "unexpected disconnect",
    "RPC failed",
    "Recv failure",
    "Empty reply from server",
)

_DIR_NOT_EMPTY_WINERROR = 145
_LONG_PATH_PREFIX = "\\\\?\\"
_DIR_NOT_EMPTY_RETRY_ATTEMPTS = 3
_DIR_NOT_EMPTY_RETRY_BACKOFF_SECONDS = 0.5


@dataclass(frozen=True)
class ReadOnlyClone:
    """A verified push-disabled clone checked out at exactly ``revision``."""

    path: Path
    clone_url: str
    revision: str
    proof: PushBlockProof


def _github_read_auth_env(clone_url: str, token: str | None) -> dict[str, str]:
    if not clone_url.casefold().startswith("https://github.com/"):
        return {}
    return github_https_auth_env(token)


def remote_head_revision(
    clone_url: str, *, token: str | None = None, timeout: float = 15
) -> str | None:
    """The remote default branch's HEAD revision via ``ls-remote``; ``None`` on any failure."""
    result = run_git(
        ["ls-remote", clone_url, "HEAD"],
        timeout=timeout,
        env=_github_read_auth_env(clone_url, token),
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    first_line = result.stdout.strip().splitlines()[0]
    parts = first_line.split()
    return parts[0] if parts and len(parts[0]) == 40 else None


def _is_transient_clone_failure(result: CompletedProcess[str]) -> bool:
    if result.returncode == TIMEOUT_EXIT_CODE:
        return True
    return any(marker in result.stderr for marker in _TRANSIENT_CLONE_STDERR_MARKERS)


def clone_pinned(
    clone_url: str,
    revision: str,
    destination: Path,
    *,
    token: str | None = None,
    timeout: float = CLONE_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> ReadOnlyClone:
    """Fresh shallow clone of the default branch, required to land on ``revision``."""
    if destination.exists():
        force_rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    def clone_once() -> None:
        result = run_git(
            ["clone", "--depth", "1", "--no-tags", clone_url, str(destination)],
            timeout=timeout,
            env={"GIT_LFS_SKIP_SMUDGE": "1", **_github_read_auth_env(clone_url, token)},
        )
        if result.returncode == 0:
            return
        if destination.exists():
            force_rmtree(destination)
        if _is_transient_clone_failure(result):
            raise RetryableOperationError(f"transient clone failure: {result.stderr}")
        raise GitSafetyError(f"clone of {clone_url} failed: {result.stderr}")

    try:
        run_with_retry("clone", clone_once, sleep=sleep)
    except RetryableOperationError as exc:
        raise GitSafetyError(
            f"clone of {clone_url} failed after {MAX_CLONE_ATTEMPTS} attempts: {exc}"
        ) from exc

    head = run_git(["rev-parse", "HEAD"], cwd=destination, timeout=10)
    if head.returncode != 0:
        raise GitSafetyError(f"cannot read the cloned revision of {clone_url}: {head.stderr}")
    checked_out = head.stdout.strip()
    if checked_out != revision:
        raise GitSafetyError(
            f"default branch of {clone_url} moved from {revision} to {checked_out} during clone"
        )

    neuter_push(destination)
    install_pre_push_hook(destination)
    proof = verify_push_blocked(destination)
    if not proof.ok:
        raise GitSafetyError(f"push is not proven blocked in {destination}: {proof.detail}")
    return ReadOnlyClone(path=destination, clone_url=clone_url, revision=revision, proof=proof)


def pinned_read_only_clone(
    clone_url: str,
    destination: Path,
    *,
    token: str | None = None,
    timeout: float = CLONE_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> ReadOnlyClone:
    """Observe the remote default-branch revision, then clone pinned to it."""
    revision = remote_head_revision(clone_url, token=token)
    if revision is None:
        raise GitSafetyError(f"cannot resolve the default-branch revision of {clone_url}")
    return clone_pinned(clone_url, revision, destination, token=token, timeout=timeout, sleep=sleep)


def _is_windows_dir_not_empty_error(exc: BaseException) -> bool:
    return (
        sys.platform == "win32"
        and isinstance(exc, OSError)
        and getattr(exc, "winerror", None) == _DIR_NOT_EMPTY_WINERROR
    )


def _with_long_path_prefix(target_path: Path) -> str:
    resolved = str(target_path.resolve())
    if resolved.startswith(_LONG_PATH_PREFIX):
        return resolved
    return f"{_LONG_PATH_PREFIX}{resolved}"


def _force_clear_directory_contents(directory: str) -> None:
    """Sweep whatever remains under ``directory`` through the long-path form, best effort."""
    long_directory = _with_long_path_prefix(Path(directory))
    try:
        with os.scandir(long_directory) as it:
            children = list(it)
    except OSError:
        return
    for child in children:
        try:
            if child.is_dir(follow_symlinks=False):
                _force_clear_directory_contents(child.path)
                os.rmdir(child.path)
            else:
                os.chmod(child.path, stat.S_IWRITE)
                os.unlink(child.path)
        except OSError:
            pass


def _retry_dir_not_empty(
    func: Callable[[str], object], target_path: str, original_exc: OSError
) -> None:
    """Two remedies for the same ``WinError 145``: a long-path sweep, then a bounded retry."""
    _force_clear_directory_contents(target_path)
    try:
        func(_with_long_path_prefix(Path(target_path)))
        return
    except OSError:
        pass
    last_exc: OSError = original_exc
    for _attempt in range(_DIR_NOT_EMPTY_RETRY_ATTEMPTS):
        time.sleep(_DIR_NOT_EMPTY_RETRY_BACKOFF_SECONDS)
        _force_clear_directory_contents(target_path)
        try:
            func(target_path)
            return
        except OSError as retry_exc:
            last_exc = retry_exc
    raise last_exc


def force_rmtree(path: Path) -> None:
    """Remove a clone even though git writes read-only objects and Windows paths run long."""

    def handle(func: Callable[..., object], target_path: str, exc: BaseException) -> None:
        if isinstance(exc, PermissionError):
            os.chmod(target_path, stat.S_IWRITE)
            func(target_path)
            return
        if _is_windows_dir_not_empty_error(exc):
            assert isinstance(exc, OSError)
            _retry_dir_not_empty(func, target_path, exc)
            return
        raise exc

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=handle)
    else:

        def on_error(
            func: Callable[..., object],
            target_path: str,
            exc_info: tuple[object, BaseException, object],
        ) -> None:
            handle(func, target_path, exc_info[1])

        shutil.rmtree(path, onerror=on_error)
