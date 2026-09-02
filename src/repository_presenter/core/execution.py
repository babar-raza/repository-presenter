"""Bounded, secret-free execution of repository examples: no shell, no stdin, no inherited secrets.

This is a process and credential boundary, not an OS sandbox: the environment is an allow-list of
process essentials with every credential-like name removed, the command runs without a shell or
interactive input under a hard timeout, and its output is redacted of any secret value that was
live in the parent process. Container isolation for hosted runs arrives at G4.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE, run_bounded
from repository_presenter.core.secrets import redact

MAX_TIMEOUT_SECONDS = 300.0

_SAFE_ENV_NAMES = frozenset(
    {
        "CI",
        "COMSPEC",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
        "APPDATA",
        "COMPUTERNAME",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "USERDOMAIN",
        "USERNAME",
        "USERPROFILE",
    }
)
_SECRET_NAME_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|CREDENTIAL)", re.IGNORECASE
)


@dataclass(frozen=True)
class ExecutionResult:
    """What one bounded execution produced, with output already redacted."""

    argv: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool
    environment_names: tuple[str, ...] = field(default_factory=tuple)


def secret_free_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Allow-list process essentials and reject every credential-like name."""
    source = dict(os.environ if base is None else base)
    clean = {
        name: value
        for name, value in source.items()
        if name.upper() in _SAFE_ENV_NAMES and not _SECRET_NAME_RE.search(name)
    }
    clean["CI"] = "true"
    clean["GIT_TERMINAL_PROMPT"] = "0"
    clean["GCM_INTERACTIVE"] = "never"
    clean["PYTHONDONTWRITEBYTECODE"] = "1"
    return clean


def execute(
    argv: list[str],
    *,
    workspace: Path,
    timeout_seconds: float,
    base_environment: dict[str, str] | None = None,
    extra_environment: dict[str, str] | None = None,
) -> ExecutionResult:
    """Run ``argv`` in ``workspace`` under the boundary and return its redacted result."""
    if not argv or not argv[0]:
        raise ValueError("example argv must identify an executable")
    if timeout_seconds <= 0 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"example timeout must be within (0, {MAX_TIMEOUT_SECONDS:g}] seconds")
    if not workspace.is_dir():
        raise ValueError(f"example workspace does not exist: {workspace}")
    source = dict(os.environ if base_environment is None else base_environment)
    removed_secret_values = [
        value for name, value in source.items() if _SECRET_NAME_RE.search(name) and value
    ]
    environment = secret_free_environment(source)
    environment.update(extra_environment or {})
    result = run_bounded(argv, cwd=workspace, timeout=timeout_seconds, env=environment)
    return ExecutionResult(
        argv=tuple(argv),
        return_code=result.returncode,
        stdout=redact(result.stdout, removed_secret_values),
        stderr=redact(result.stderr, removed_secret_values),
        timed_out=result.returncode == TIMEOUT_EXIT_CODE,
        environment_names=tuple(sorted(environment)),
    )
