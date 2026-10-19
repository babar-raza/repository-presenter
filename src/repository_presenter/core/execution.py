"""Bounded, secret-free execution of repository examples: no shell, no stdin, no inherited secrets.

This is a process and credential boundary, not an OS sandbox: the environment is an allow-list of
process essentials with every credential-like name removed, the command runs without a shell or
interactive input under a hard timeout, and its output is redacted of any secret value that was
live in the parent process. The same credential-name check applies to a caller's own
``extra_environment`` overlay, not only the OS-inherited base (TB-08, external review D8,
2026-09-08). Container isolation for hosted runs arrives at G4; there is no OS-level sandbox
today, and this module does not claim to be one.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
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


def _without_secret_names(mapping: dict[str, str]) -> dict[str, str]:
    """Every entry whose name does not look like a credential - the check applied to the
    OS-inherited base and, since a caller's ``extra_environment`` deliberately adds names outside
    ``_SAFE_ENV_NAMES`` (a toolchain cache directory, say), the same check applied to it too
    (TB-08, external review D8, 2026-09-08: ``execute`` used to merge ``extra_environment`` in raw
    after filtering the base, so a caller-supplied credential-like name bypassed the boundary
    entirely)."""
    return {name: value for name, value in mapping.items() if not _SECRET_NAME_RE.search(name)}


def secret_free_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Allow-list process essentials and reject every credential-like name."""
    source = dict(os.environ if base is None else base)
    clean = _without_secret_names(
        {name: value for name, value in source.items() if name.upper() in _SAFE_ENV_NAMES}
    )
    clean["CI"] = "true"
    clean["GIT_TERMINAL_PROMPT"] = "0"
    clean["GCM_INTERACTIVE"] = "never"
    clean["PYTHONDONTWRITEBYTECODE"] = "1"
    return clean


# Where a toolchain would otherwise write into the developer's own account: a package cache, a
# credential store, a global configuration file. Every one is redirected into the run's workspace
# so a verification cannot read state a previous run left behind, and cannot leave any
# (RESEARCH_AND_GUIDELINES.md section 29.6 E5, the legacy's disposable-profile idea).
_PROFILE_DIRECTORIES: dict[str, str] = {
    "HOME": "home",
    "USERPROFILE": "home",
    "APPDATA": "appdata",
    "LOCALAPPDATA": "localappdata",
    "XDG_CACHE_HOME": "cache",
    "XDG_CONFIG_HOME": "config",
    "PIP_CACHE_DIR": "cache/pip",
    "NUGET_PACKAGES": "cache/nuget",
    "DOTNET_CLI_HOME": "home",
    "CARGO_HOME": "cache/cargo",
    "GOPATH": "cache/go",
    "GOMODCACHE": "cache/go/pkg/mod",
    "MAVEN_OPTS_REPO": "cache/maven",
    "NPM_CONFIG_CACHE": "cache/npm",
    "GRADLE_USER_HOME": "cache/gradle",
}


def profile_environment(workspace: Path) -> dict[str, str]:
    """The names that point a toolchain's caches and configuration inside ``workspace``.

    Returned as an overlay for ``execute``'s ``extra_environment``, so a caller adds it to the
    secret-free base rather than replacing it. Directories are created, because a toolchain that
    finds its cache path missing usually creates it in the real home instead.
    """
    overlay: dict[str, str] = {}
    for name, relative in _PROFILE_DIRECTORIES.items():
        target = workspace.joinpath(*relative.split("/"))
        target.mkdir(parents=True, exist_ok=True)
        overlay[name] = str(target)
    return overlay


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
    overlay = dict(extra_environment or {})
    removed_secret_values = [
        value
        for name, value in (*source.items(), *overlay.items())
        if _SECRET_NAME_RE.search(name) and value
    ]
    environment = secret_free_environment(source)
    environment.update(_without_secret_names(overlay))
    result = run_bounded(argv, cwd=workspace, timeout=timeout_seconds, env=environment)
    return ExecutionResult(
        argv=tuple(argv),
        return_code=result.returncode,
        stdout=redact(result.stdout, removed_secret_values),
        stderr=redact(result.stderr, removed_secret_values),
        timed_out=result.returncode == TIMEOUT_EXIT_CODE,
        environment_names=tuple(sorted(environment)),
    )


# A line a tool wrote about its own failure, as opposed to progress or a banner: a diagnostic
# first, and only without one a line that merely says something failed.
_DIAGNOSTIC_LINE = re.compile(
    r"\b(?:error|errors|fatal|cannot|can't|could not|unable|not recognized|no such file|"
    r"not found|denied|refused|exception)\b",
    re.IGNORECASE,
)
_FAILED_LINE = re.compile(r"\b(?:failed|failure)\b", re.IGNORECASE)
# An absolute path of this machine: a drive-letter path, or a conventional POSIX home or temp root.
_MACHINE_PATH = re.compile(
    r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s'\"<>|\])]*"
    r"|(?<![\w.])/(?:home|Users|tmp|var|runner|root|opt|mnt)/[^\s'\"<>|\])]*"
)
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# MSBuild closes a diagnostic with the project that raised it in brackets.
_TRAILING_PROJECT = re.compile(r"\s*\[[^\]]*(?:proj|\.sln|<path>)[^\]]*\]\s*$")
_EXCERPT_LINES = 3
_EXCERPT_CHARS = 360


def error_excerpt(
    *outputs: str,
    bases: Iterable[Path] = (),
    lines: int = _EXCERPT_LINES,
    chars: int = _EXCERPT_CHARS,
) -> str:
    """The first lines a failed tool said about its failure, safe to put in a receipt.

    A receipt that says only "failed" cannot be told from a harness fault, which is how a missing
    ``node`` on ``PATH`` read as an upstream defect (2026-10-19). ``outputs`` are searched in the
    order given (pass stderr first): lines that read as a failure win, and when none do the first
    non-empty lines are used. A receipt becomes a fact's evidence and a fact is published, so every
    ``bases`` directory and every other absolute path of this machine is removed - a path that
    differs per machine would also move a sealed candidate's bytes for a reason that is not the
    repository. Returns "" when the tool said nothing.
    """
    roots = {path for base in bases for path in (base, base.resolve())}
    cleaned: list[str] = []
    for output in outputs:
        text = output
        for base in roots:
            for rendered in (str(base), base.as_posix()):
                text = text.replace(rendered + "\\", "").replace(rendered + "/", "")
                text = text.replace(rendered, "")
        for raw in text.splitlines():
            line = _ANSI.sub("", raw).strip()
            line = _MACHINE_PATH.sub("<path>", line)
            line = _TRAILING_PROJECT.sub("", line).strip()
            if line and line not in cleaned:
                cleaned.append(line)
    anchors = (
        [index for index, line in enumerate(cleaned) if _DIAGNOSTIC_LINE.search(line)]
        or [index for index, line in enumerate(cleaned) if _FAILED_LINE.search(line)]
        or list(range(len(cleaned)))
    )
    # CMake (`CMake Error at ...:`) and others put the message on the line after the anchor, so
    # the line that follows an anchor is kept with it.
    picked = sorted({i for index in anchors for i in (index, index + 1) if i < len(cleaned)})
    return " | ".join(cleaned[index] for index in picked[:lines])[:chars]
