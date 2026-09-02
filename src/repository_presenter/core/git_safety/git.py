"""The single git subprocess wrapper: pinned determinism flags, no prompts, bounded time.

Every git invocation pins line-ending behavior per call (never the operator's ambient config),
enables long-path checkout on Windows, and disables interactive credential prompts at the source:
``GIT_TERMINAL_PROMPT=0`` stops git's own prompt and ``GCM_INTERACTIVE=never`` stops a configured
Git Credential Manager from opening its own flow. Both are merged last so no caller can re-enable
them. A timeout is reported as an ordinary failed result with exit 124, never as an exception.
"""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE, run_bounded

DETERMINISM_FLAGS = ["-c", "core.autocrlf=false", "-c", "core.eol=lf"]
LONG_PATH_SAFETY_FLAGS = ["-c", "core.longpaths=true"]
GIT_SAFETY_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}


def github_https_auth_env(token: str | None) -> dict[str, str]:
    """Process-local GitHub HTTPS authentication; the token never touches a URL or a file."""
    if token is None:
        return {}
    basic_auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic_auth}",
    }


def run_git(
    args: list[str],
    cwd: Path | None = None,
    timeout: float = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one git command under the safety flags and environment."""
    full_env = {**os.environ, **(env or {}), **GIT_SAFETY_ENV}
    git_args = ["git", *DETERMINISM_FLAGS, *LONG_PATH_SAFETY_FLAGS, *args]
    result = run_bounded(git_args, cwd=cwd, timeout=timeout, env=full_env)
    if result.returncode == TIMEOUT_EXIT_CODE:
        return subprocess.CompletedProcess(
            args=git_args,
            returncode=TIMEOUT_EXIT_CODE,
            stdout=result.stdout,
            stderr=f"git {' '.join(args)} timed out after {timeout}s",
        )
    return result
