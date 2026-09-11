"""The single git subprocess wrapper: pinned determinism flags, no prompts, bounded time.

Every git invocation pins line-ending behavior per call (never the operator's ambient config),
enables long-path checkout on Windows, and disables interactive credential prompts at the source:
``GIT_TERMINAL_PROMPT=0`` stops git's own prompt and ``GCM_INTERACTIVE=never`` stops a configured
Git Credential Manager from opening its own flow. Both are merged last so no caller can re-enable
them. A timeout is reported as an ordinary failed result with exit 124, never as an exception.
The repository a command acts on is always the one at ``cwd`` (or its explicit path argument):
``GIT_DIR`` and its siblings are scrubbed from the child environment, never forwarded
(``REPOSITORY_REDIRECTING_ENV``).
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

# Git exports these into every hook's environment, and a harness that spawns a process may set
# them too; each one outranks both ``cwd`` and ``-C``, so a forwarded one silently redirects a
# command meant for the repository at ``cwd`` to some other repository. Measured 2026-09-11
# (RESEARCH_AND_GUIDELINES.md section 29, G4-W17 arrival item 55): under the pre-push hook the
# suite's fixtures re-initialised THIS checkout, chained 16 and 8 commits onto two live lane
# branches, rewrote its user identity, and flipped ``core.bare`` - while the same run by hand was
# green. The wrapper's contract is "the repository at ``cwd``", so none of these ever reaches git,
# neither from the process environment nor from a caller's ``env``. ``GIT_PREFIX`` carries no
# repository but is a hook-only export with the same provenance, scrubbed for the same reason.
REPOSITORY_REDIRECTING_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


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
    """Run one git command under the safety flags and environment, on the repository at ``cwd``.

    The repository-redirecting variables are dropped from the inherited environment and from
    ``env`` alike, so the command can only ever act on ``cwd`` (or an explicit path argument) -
    never on whatever repository a hook or harness exported ``GIT_DIR`` for.
    """
    inherited = {**os.environ, **(env or {})}
    full_env = {
        **{k: v for k, v in inherited.items() if k not in REPOSITORY_REDIRECTING_ENV},
        **GIT_SAFETY_ENV,
    }
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
