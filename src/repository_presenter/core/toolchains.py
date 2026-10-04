"""Machine toolchains: one resolver for every example verifier and for the environment fingerprint.

Every `extractors/platforms/*_examples.py` verifier finds its compiler here, and the sealed
environment class records what was found (`components/readme/bundle/seal.py`). Before this module,
each verifier searched `PATH` on its own, so the same machine produced different example receipts
in different shells: `javac` was absent from one shell's PATH while a JDK sat under the machine's
own install root, and the Java verifier reported BLOCKED_TOOLCHAIN there and EXECUTED elsewhere
(measured 2026-10-04). Three rules follow.

Resolution order is per tool, because the right answer differs by tool
(`docs/RESEARCH_AND_GUIDELINES.md` §29.6 E7). `path` tools (C++ compiler, CMake, Ninja, Cargo,
npm) keep PATH first: a PATH tool is at
least as capable as the registry's own. `registry` tools (tsc) keep the registry first, because a
newer PATH `tsc` can drop a `moduleResolution` the repository still declares (TS5108). `installed`
tools (javac, mvn) take the machine's own record and install root before PATH: a JDK on PATH may be
older than the one the repository's floor needs, and the install root is the same whichever shell
ran the present. A hosted runner has no registry and no Windows install root, so it resolves by
PATH exactly as before.

The registry (`TOOLCHAIN_PATHS.txt`, OWNER-06) is read as data, never trusted as a PATH edit. Its
entries name the absolute path each tool was provisioned at; when that path no longer exists but
the tree it belongs to does (the owner's registry records `C:\\tools\\rp-toolchains\\...` while the
tree lives under `D:\\tools\\rp-toolchains` on this machine), the tail below the registry's own
directory is re-rooted under it. The subprocess PATH gets each tool's own directory prepended and
is passed to the one call only; `os.environ["PATH"]` is never written.

The environment fingerprint (`toolchain_fingerprint`) names every known tool by its resolved
version, or `absent`. A change in availability or version between two computations is an
environment-class change, so it reopens EXTRACTING: the receipts it could have changed are
re-derived rather than reused. The probe is cached by the binary's identity (path, mtime, size).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from repository_presenter.core.execution import execute, profile_environment

REGISTRY_VARIABLE = "RP_TOOLCHAIN_REGISTRY"
# The registry's known locations on the owner's machine: the C: path its own entries were written
# against, then the D: tree that actually holds the binaries on this machine. Read only when
# RP_TOOLCHAIN_REGISTRY does not name one.
REGISTRY_DEFAULTS = (
    Path("C:/tools/rp-toolchains/TOOLCHAIN_PATHS.txt"),
    Path("D:/tools/rp-toolchains/TOOLCHAIN_PATHS.txt"),
)
ABSENT = "absent"
UNVERSIONED = "present (no version reported)"
_PROBE_TIMEOUT_SECONDS = 60.0
_MAX_VERSION_CHARS = 120


@dataclass(frozen=True)
class Tool:
    """One machine tool: how to find it, in what order, and how to ask it for its version.

    ``name`` is also the registry key and the fingerprint key. ``commands`` are PATH names in the
    order they are tried. ``installed`` are glob patterns under each Windows install root, searched
    newest version first. ``environment`` maps a variable the tool needs (a rustup proxy needs
    RUSTUP_HOME) to the registry key holding its value.
    """

    name: str
    commands: tuple[str, ...]
    order: str = "path"
    installed: tuple[str, ...] = ()
    version_args: tuple[str, ...] = ("--version",)
    environment: tuple[tuple[str, str], ...] = ()


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in (
        Tool(
            "javac",
            ("javac", "javac.exe", "javac.cmd"),
            order="installed",
            installed=("Eclipse Adoptium/jdk-*/bin/javac.exe", "Java/jdk-*/bin/javac.exe"),
            version_args=("-version",),
        ),
        Tool(
            "mvn",
            ("mvn", "mvn.cmd"),
            order="installed",
            installed=("apache-maven-*/bin/mvn.cmd",),
            version_args=("-v",),
        ),
        Tool("dotnet", ("dotnet", "dotnet.exe", "dotnet.cmd"), installed=("dotnet/dotnet.exe",)),
        Tool("node", ("node", "node.exe"), installed=("nodejs/node.exe",)),
        Tool("npm", ("npm.cmd", "npm")),
        Tool("tsc", ("tsc", "tsc.cmd"), order="registry"),
        Tool(
            "go",
            ("go", "go.exe", "go.cmd"),
            installed=("Go/bin/go.exe",),
            version_args=("version",),
        ),
        Tool(
            "cargo",
            ("cargo", "cargo.exe"),
            environment=(("RUSTUP_HOME", "rustup_home"), ("CARGO_HOME", "cargo_home")),
        ),
        Tool("cmake", ("cmake",)),
        Tool("gxx", ("g++", "c++", "clang++")),
        Tool("ninja", ("ninja",)),
    )
}


def registry_path() -> Path | None:
    """The toolchain registry this machine names, or None when it has none."""
    recorded = os.environ.get(REGISTRY_VARIABLE, "").strip()
    if recorded:
        return Path(recorded)
    for candidate in REGISTRY_DEFAULTS:
        if candidate.is_file():
            return candidate
    return None


def _existing(value: str, registry: Path) -> str | None:
    """``value`` as recorded if it still exists, else the same tail under the registry's tree."""
    if not value:
        return None
    if Path(value).exists():
        return value
    parts = [part for part in re.split(r"[\\/]+", value) if part]
    anchor = registry.parent.name
    if anchor in parts:
        tail = parts[parts.index(anchor) + 1 :]
        if tail:
            moved = registry.parent.joinpath(*tail)
            if moved.exists():
                return str(moved)
    return None


def recorded_path(key: str) -> str | None:
    """What the registry records for ``key`` - a file or a directory - if it exists here."""
    registry = registry_path()
    if registry is None:
        return None
    try:
        text = registry.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            found = _existing(value.strip(), registry)
            if found:
                return found
    return None


def recorded_tool(key: str) -> str | None:
    """The file the registry records for ``key``, if it exists here (a tool, not a directory)."""
    found = recorded_path(key)
    return found if found is not None and Path(found).is_file() else None


def _install_roots() -> tuple[Path, ...]:
    """The conventional Windows install roots a JDK, Maven, .NET or Go installer uses.

    Windows only: a POSIX runner's tools are on PATH, and an install-root search there would be a
    second, unrecorded source of truth.
    """
    if os.name != "nt":
        return ()
    roots: list[Path] = []
    program_files = os.environ.get("PROGRAMFILES", "").strip()
    if program_files:
        roots.append(Path(program_files))
    roots.extend((Path("D:/Program Files"), Path("D:/tools")))
    return tuple(dict.fromkeys(roots))


def _version_key(path: Path) -> list[object]:
    """Natural order, so jdk-21.0.11 sorts above jdk-17.0.19 and 3.10 above 3.9."""
    parts = re.split(r"(\d+)", str(path))
    return [int(part) if index % 2 else part for index, part in enumerate(parts)]


def _installed(tool: Tool) -> str | None:
    found: list[Path] = []
    for root in _install_roots():
        for pattern in tool.installed:
            try:
                found.extend(path for path in root.glob(pattern) if path.is_file())
            except OSError:
                continue
    if not found:
        return None
    return str(max(found, key=_version_key))


def _on_path(tool: Tool) -> str | None:
    for command in tool.commands:
        found = shutil.which(command)
        if found:
            return found
    return None


# The order each precedence class tries its sources in (see the module docstring).
_PRECEDENCE: dict[str, tuple[str, ...]] = {
    "path": ("path", "recorded", "installed"),
    "registry": ("recorded", "path", "installed"),
    "installed": ("recorded", "installed", "path"),
}


def resolve_tool(name: str) -> str | None:
    """The absolute path of the tool ``name`` on this machine, or None when it has none."""
    tool = TOOLS[name]
    lookups: dict[str, Callable[[], str | None]] = {
        "path": partial(_on_path, tool),
        "recorded": partial(recorded_tool, name),
        "installed": partial(_installed, tool),
    }
    for step in _PRECEDENCE.get(tool.order, _PRECEDENCE["path"]):
        found = lookups[step]()
        if found:
            return found
    return None


def subprocess_path(*tools: str | None) -> str:
    """The PATH a verifier's subprocess gets: each tool's own directory first, then the process's.

    Passed as an overlay to one call only. The process's own ``PATH`` is never written, which is
    the boundary `RESEARCH_AND_GUIDELINES.md` §29.6 E5 and the lane's loop prompt both state.
    """
    directories = list(dict.fromkeys(str(Path(tool).parent) for tool in tools if tool))
    inherited = os.environ.get("PATH", "")
    if inherited:
        directories.append(inherited)
    return os.pathsep.join(directories)


_PROBE_CACHE: dict[tuple[str, str, int, int], str] = {}


def probe_version(name: str, path: str) -> str:
    """The first line of ``name``'s own version report at ``path``, or "" when it reports none.

    Run through the same bounded, secret-free boundary as every verifier, with the same profile
    redirection and the tool's own registry-recorded environment (a rustup proxy reports nothing
    without RUSTUP_HOME). Cached by the binary's identity, so an unchanged tool is asked once per
    process and a replaced one is asked again.
    """
    tool = TOOLS[name]
    try:
        stat = Path(path).stat()
    except OSError:
        return ""
    key = (name, path, stat.st_mtime_ns, stat.st_size)
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    # `go version` leaves a telemetry child holding its directory on Windows for a moment, so a
    # scratch directory that cannot be removed yet is left for the OS, never a failed probe.
    with tempfile.TemporaryDirectory(prefix="rp-toolchain-", ignore_cleanup_errors=True) as scratch:
        workspace = Path(scratch)
        overlay = profile_environment(workspace)
        for variable, registry_key in tool.environment:
            value = recorded_path(registry_key)
            if value:
                overlay[variable] = value
        overlay["PATH"] = subprocess_path(path)
        result = execute(
            [path, *tool.version_args],
            workspace=workspace,
            timeout_seconds=_PROBE_TIMEOUT_SECONDS,
            extra_environment=overlay,
        )
    version = ""
    if result.return_code == 0 and not result.timed_out:
        lines = [
            line.strip()
            for line in (result.stdout + "\n" + result.stderr).splitlines()
            if line.strip()
        ]
        version = lines[0][:_MAX_VERSION_CHARS] if lines else ""
    _PROBE_CACHE[key] = version
    return version


def toolchain_fingerprint() -> dict[str, str]:
    """Every known tool by the version this machine resolves, or ``absent``, in name order."""
    fingerprint: dict[str, str] = {}
    for name in sorted(TOOLS):
        path = resolve_tool(name)
        if path is None:
            fingerprint[name] = ABSENT
            continue
        fingerprint[name] = probe_version(name, path) or UNVERSIONED
    return fingerprint
