"""Build the library with CMake, then syntax-check each README example against its headers.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: C++'s bar is a *compilable* example, not an executed one. A README snippet is not a
program, so it is given a `main` when it has none and compiled with `-fsyntax-only` against the
library's public include root - which proves exactly what the contract claims, that the example's
types and calls exist and check against this revision, without linking or running anything the
repository built.

Five rules the outcome respects. A toolchain this machine lacks is `NOT_VERIFIED`, which the facts
stage records as `UNRESOLVED` - never `CONTRADICTED`, because "we could not check" is not "we
checked and it is false". The compiler is called by its resolved absolute path with the toolchain's
own directories prepended to the *subprocess* `PATH` only, never the user's or the machine's
(`evidence/build/lanes/lane-b/LANE-B-00.json`). Every cache and configuration store is redirected
into the run directory. The verdict is read from where the diagnostics were raised: a diagnostic
in the example's own file makes the example false, while a tree whose *own* headers do not compile
with this compiler leaves the example unchecked rather than condemned - measured 2026-09-06 on
Aspose.Cells for C++, whose sources use `std::numeric_limits` without including `<limits>` and
whose build GCC 16.2 rejects outright, which is a fact about the repository's portability and says
nothing about whether its README is true. And an example whose *only* diagnostics are unbound
identifiers is `NOT_VERIFIED`, not false: a fence opening on `sheet`/`workbook` its README
established in a section this extractor never inherited alongside it (Taskcard C; the same class
`rust_examples.py`'s `unbound_values()` already excluded, Aspose.Cells-FOSS-for-Cpp's own
example:003-007) is incomplete, not wrong - a fence naming something the library genuinely does
not export (example:002's real `operator[]` mismatch) still fails.

A sixth rule, added for the trigraph finding (`docs/DECISION_LOG.md`, 2026-09-10/09-23/09-27): a
target repository's own `-Werror`-under-GCC/Clang build policy is never a defect this codebase may
patch around - `toolchain-detect.cmake` is the target's own file, read and built unmodified. But a
*second, real* compiler that raises no such diagnostic for the identical, unmodified source is a
legitimate second observation, not a workaround - the same "prefer a battle-tested facility, and
name the alternative" discipline `AGENTS.md` already asks of this codebase's own mechanisms, applied
to which compiler builds the target's own configuration. `build_product` below tries the primary
(GCC/Clang) toolchain first, exactly as before - a repository whose primary build already succeeds
is completely unaffected, byte for byte. Only when the primary toolchain's own `cmake --build`
genuinely fails does it retry with `msvc_toolchain`'s own MSVC, if the machine has one recorded
(`TOOLCHAIN_PATHS.txt`'s `vcvarsall` key, OWNER-06) - never with the target's warning policy
altered, and named in the receipt's own detail either way.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

_MAX_OUTPUT_CHARS = 4000
_WORKSPACE_ATTEMPTS = 5
_DEFAULT_STANDARD = "17"
# `<path>:<line>:<column>: error: <message>` is GCC's diagnostic shape; the column is absent from
# a few and `fatal error:` is the same diagnostic with the compiler stopping after it. The file
# group is non-greedy so a Windows drive letter's colon does not end it.
_DIAGNOSTIC = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<column>\d+):)?\s*(?:fatal )?error:\s*(?P<rest>.+)$"
)
# GCC's two diagnostic shapes for a name the fence never declared: "was not declared in this
# scope" for a bare identifier (`sheet`), "has not been declared" for one used to its own left of
# `::` (`CellArea::CreateCellArea`) - both raised by Aspose.Cells-FOSS-for-Cpp's own
# example_003-007, all opening on a binding (`sheet`, `workbook`, `PageSetup`, and the enum/type
# names only their local scope would resolve) their README establishes in an earlier, un-
# inherited section (Taskcard C; rust_examples.py's unbound_values() is the same check for
# Rust's own E0425 - measured live 2026-09-10, the real repository's current source). GCC's own
# quote style in a diagnostic follows the build's locale: this machine's GCC quotes with plain
# ASCII apostrophes, the hosted Ubuntu CI runner's own GCC quotes with Unicode curly quotes
# (U+2018 LEFT SINGLE QUOTATION MARK / U+2019 RIGHT SINGLE QUOTATION MARK) - confirmed from the
# real hosted stderr (2026-09-10, this taskcard's own hosted-CI-red incident), not guessed; both
# quote characters are accepted on either side.
_UNBOUND_IDENTIFIER = re.compile(
    "[\u2018']([^\u2018\u2019']+)[\u2019'] "
    r"(?:was not declared in this scope|has not been declared)"
)
# The lane's toolchains are never on PATH (loop-prompt §1.3): a name is resolved by `which`, then
# by the absolute path the machine-local registry the lane's receipt records.
_REGISTRY_VARIABLE = "RP_TOOLCHAIN_REGISTRY"
_REGISTRY_DEFAULT = Path("C:/tools/rp-toolchains/TOOLCHAIN_PATHS.txt")
# A snippet with one of these is already a program; everything else is a body that needs one.
_HAS_MAIN = re.compile(r"^[^\S\n]*(?:[A-Za-z_][\w:<>,\s*&]*\s+)?main\s*\(", re.MULTILINE)
# What stays at file scope when a body is wrapped: preprocessor lines, comments, `using` and
# namespace-alias declarations. Everything from the first other statement down goes into `main`.
_PREAMBLE = re.compile(r"^\s*(?:#|//|/\*|\*|using\b|namespace\s+\w+\s*=)")
# The configure step is the network-bound one: `FetchContent` downloads a dependency archive per
# `find_package` that finds nothing, so its duration tracks the link rather than the machine, and
# a ceiling here exists to stop a hang, never to enforce a performance budget. Measured
# 2026-09-16 on Aspose.Slides for C++, which fetches pugixml, miniz and GoogleTest: the same
# configure of the same revision on the same machine reported 57.8 s, 71.7 s and 141.7 s across
# three cold runs - a 2.4x spread - and the run before them exceeded 180 s and was cut off with
# only `_deps/pugixml-src` on disk, which cost all ten of its examples their verdict. A ceiling
# must sit clear of the top of that spread, so this is `core.execution.MAX_TIMEOUT_SECONDS`, the
# most one bounded execution may be given at all - which is why the durable fix is below, in
# `build_product`: no ceiling this side of the boundary can outrun a slow enough link, so a
# configure that does not finish must keep what it fetched rather than discard it.
_TIMEOUT_CONFIGURE = 300.0
_TIMEOUT_BUILD = 300.0


def _registry_path() -> Path:
    recorded = os.environ.get(_REGISTRY_VARIABLE, "").strip()
    return Path(recorded) if recorded else _REGISTRY_DEFAULT


def recorded_tool(name: str) -> str | None:
    """The absolute path the machine-local toolchain registry records for ``name``, if any."""
    registry = _registry_path()
    try:
        text = registry.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name and Path(value.strip()).is_file():
            return value.strip()
    return None


def _resolve(names: Sequence[str], recorded: Sequence[str]) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for key in recorded:
        found = recorded_tool(key)
        if found:
            return found
    return None


def cpp_compiler() -> str | None:
    """A C++ compiler this machine offers, or None when it offers none.

    `which` first, so a hosted runner's own GCC or Clang is used where one is on `PATH`, then the
    workspace-local GCC the lane's registry records - which is the only one on this machine
    (OWNER-06; `TOOLCHAIN_PATHS.txt` records `gxx`).
    """
    return _resolve(("g++", "c++", "clang++"), ("gxx",))


def cmake_executable() -> str | None:
    """CMake as this machine offers it.

    `which` before the registry deliberately. The winlibs toolchain bundles a `cmake.exe` with no
    certificate bundle, and a project whose configure step fetches a dependency over HTTPS dies in
    it with "SSL certificate verification failed: certificate signer not trusted" - measured
    2026-09-06 on Aspose.PDF for C++, which fetches GoogleTest at configure time and configured
    and built in 95 seconds under the machine's own CMake and not at all under the bundled one.
    """
    return _resolve(("cmake",), ("cmake",))


def ninja_executable() -> str | None:
    """Ninja as this machine offers it, or the one the lane's registry records."""
    return _resolve(("ninja",), ("ninja",))


def toolchain_path(*tools: str | None) -> str:
    """The subprocess `PATH`: each tool's own directory, then whatever the process already had.

    Never the user's or the machine's `PATH` (loop-prompt §1.3, `RESEARCH_AND_GUIDELINES.md` §29.6
    E5). The built compiler needs its own directory on `PATH` to find its runtime DLLs, and CMake
    finds the compiler and the generator by name, so both directories must be here.
    """
    directories = list(dict.fromkeys(str(Path(tool).parent) for tool in tools if tool))
    inherited = os.environ.get("PATH", "")
    if inherited:
        directories.append(inherited)
    return os.pathsep.join(directories)


_MSVC_ENV_VARS = ("INCLUDE", "LIB", "LIBPATH", "PATH")
_MSVC_ACTIVATE_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class MsvcToolchain:
    """A native MSVC (`cl.exe`) toolchain, activated for x64 via its own `vcvarsall.bat` - the one
    lever this codebase has for a target repository whose own `-Werror`-under-GCC/Clang build
    policy rejects a diagnostic MSVC does not raise at all for the identical, unmodified source
    (`docs/DECISION_LOG.md`, the trigraph finding). This never changes what the target's own
    `CMakeLists.txt`/`toolchain-detect.cmake` declares - it is a different, real compiler building
    that same, unmodified configuration.
    """

    cl: str
    environment: dict[str, str]
    version: str = ""


def _run_in_activated_shell(vcvarsall: str, command: str, workspace: Path) -> ExecutionResult:
    """Run ``command`` in a `cmd.exe` shell after sourcing ``vcvarsall.bat x64`` - the only way
    MSVC's own environment variables (`INCLUDE`/`LIB`/`LIBPATH`, and `cl.exe`'s own `PATH` entry)
    become available; `cl.exe` alone, without them, cannot find the standard library headers.

    Written to a small `.cmd` script in ``workspace`` and invoked by path, rather than assembled
    as a single ``cmd.exe /c "...&&..."`` argument: a path with spaces (a standard, non-custom VS
    install lives under `Program Files (x86)`) needs its own quotes, and Python's own argv-to-
    command-line quoting (MSVCRT rules) does not agree with `cmd.exe`'s own quote parsing when both
    have to nest in one string - a script file sidesteps the mismatch entirely, each line parsed by
    `cmd.exe` on its own.

    ``vcvarsall.bat`` itself calls ``vswhere.exe`` to locate the VS instance; if this machine
    records one (`TOOLCHAIN_PATHS.txt`'s own ``vswhere`` key - a pre-existing, per-machine
    Installer component this project did not install), its directory is prepended to this
    activating shell's own `PATH` so that lookup succeeds rather than silently degrading.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    vswhere = recorded_tool("vswhere")
    lines = ["@echo off"]
    if vswhere:
        lines.append(f'set "PATH={Path(vswhere).parent}\\;%PATH%"')
    lines.append(f'call "{vcvarsall}" x64 >nul')
    lines.append(command)
    script = workspace / "_msvc_activate.cmd"
    script.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    # No `profile_environment` overlay here deliberately: this activation step is a one-off
    # bootstrap that only reads INCLUDE/LIB/LIBPATH/cl.exe's own path back out, never a toolchain
    # invocation whose cache/config needs isolating - and `vswhere.exe`'s own state cache expects
    # a real `LOCALAPPDATA`, not a fresh, empty redirected directory (which fails activation with
    # "the system cannot find the path specified", measured 2026-09-27). `build_product`'s own
    # configure/build calls still get the full `profile_environment` isolation, unaffected.
    return execute(
        ["cmd.exe", "/c", str(script)],
        workspace=workspace,
        timeout_seconds=_MSVC_ACTIVATE_TIMEOUT_SECONDS,
    )


def msvc_toolchain(workspace: Path) -> MsvcToolchain | None:
    """The registered MSVC toolchain (`TOOLCHAIN_PATHS.txt`'s own `vcvarsall` key, OWNER-06),
    activated for x64 - or ``None`` when this machine has none recorded, or activation itself
    failed (never raises; a missing second toolchain is exactly the "this machine lacks it" case
    every other resolver in this module already handles the same way).

    Only `INCLUDE`, `LIB`, `LIBPATH`, and `PATH` are captured from the activated shell - never the
    whole `set` output, so this stays a small, evidenced addition on top of the subprocess's own
    base environment rather than an opaque copy of the machine's entire activated state. `PATH` is
    included because `cl.exe`'s own directory alone is not enough: a real build also needs the
    Windows SDK's `rc.exe`/`mt.exe` (`cmake`'s own MSVC-link helper shells out to `rc.exe` for a
    manifest resource even for a plain static-library ABI check - measured 2026-09-27, "no such
    file or directory" from `rc` with only `cl.exe`'s directory on `PATH`), which `vcvarsall.bat`
    itself adds to `PATH`, not to any of the other three variables.
    """
    vcvarsall = recorded_tool("vcvarsall")
    if vcvarsall is None:
        return None
    env_probe = _run_in_activated_shell(vcvarsall, "set", workspace)
    if env_probe.return_code != 0:
        return None
    captured: dict[str, str] = {}
    for line in env_probe.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().upper() in _MSVC_ENV_VARS:
            captured[key.strip().upper()] = value.strip()
    if not all(name in captured for name in _MSVC_ENV_VARS):
        return None
    cl_probe = _run_in_activated_shell(vcvarsall, "where cl", workspace)
    lines = [line.strip() for line in cl_probe.stdout.splitlines() if line.strip()]
    if cl_probe.return_code != 0 or not lines or not Path(lines[0]).is_file():
        return None
    # `cl.exe` has no `--version` flag (unlike GCC/Clang) - its identity is the banner it prints to
    # its own stderr for any invocation, valid or not; captured the same way as the other probes.
    version_probe = _run_in_activated_shell(vcvarsall, "cl 2>&1", workspace)
    version = next(
        (
            line.strip().removeprefix("Microsoft (R) C/C++ Optimizing Compiler ").strip()
            for line in version_probe.stdout.splitlines()
            if "C/C++ Optimizing Compiler" in line
        ),
        "",
    )
    return MsvcToolchain(cl=lines[0], environment=captured, version=version)


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_OUTPUT_CHARS else text[:_MAX_OUTPUT_CHARS] + "..."


def _blocked(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
    return [
        ExampleReceipt(
            ordinal=candidate.ordinal,
            outcome="NOT_VERIFIED",
            return_code=None,
            stdout="",
            stderr="",
            detail=detail,
            fixtures=(),
        )
        for candidate in candidates
    ]


def _fresh_workspace(workspace: Path) -> Path | None:
    """An empty run directory, even when Windows will not let the last one go.

    The rule the .NET and TypeScript verifiers need for the same reason: this checkout sits on
    OneDrive, which holds handles, and failing to clean scratch space must never cost a repository
    its candidate.
    """
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def wrap_example(code: str) -> str:
    """A snippet as a translation unit: its own program, or its body given a `main`.

    C++ has no top-level statements, so a README body that constructs a document and saves it is
    not compilable as written - and six of Aspose.Cells for C++'s seven examples, nine of
    Aspose.Slides' ten and eight of Aspose.PDF's eleven are exactly that. The preprocessor lines,
    comments, `using` declarations and namespace aliases the snippet opens with stay at file
    scope, where the language requires them; everything from the first other statement down
    becomes the body of `main`. A snippet that already declares `main` is compiled as it stands.
    """
    if _HAS_MAIN.search(code):
        return code
    lines = code.splitlines()
    cut = 0
    for index, line in enumerate(lines):
        if line.strip() and not _PREAMBLE.match(line):
            cut = index
            break
        cut = index + 1
    head = lines[:cut]
    body = lines[cut:]
    indented = "\n".join(f"    {line}" if line.strip() else line for line in body)
    return "\n".join([*head, "", "int main() {", indented, "    return 0;", "}", ""])


def _scrub(text: str, *bases: Path) -> str:
    """This machine's paths out of the compiler's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home directory
    must not appear in it - and a path that differs per machine would move a sealed candidate's
    bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {path for original in bases for path in (original, original.resolve())}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def split_diagnostics(output: str, example: str) -> tuple[list[str], list[str]]:
    """The compiler's errors, separated into the example's own and the library's headers'.

    The example's decide the verdict. A run whose only errors are the library's leaves the example
    unchecked: the snippet never got as far as being compiled, so neither "it is true" nor "it is
    false" has been observed (§29.6 E5).
    """
    mine: list[str] = []
    theirs: list[str] = []
    for line in output.splitlines():
        match = _DIAGNOSTIC.match(line.strip())
        if match is None:
            continue
        where = match.group("file").replace("\\", "/").lstrip("./")
        (mine if where.endswith(example) else theirs).append(line.strip())
    return (mine, theirs)


def unbound_identifiers(diagnostics: Sequence[str]) -> list[str]:
    """The names an example uses and never binds, when they are the only thing wrong.

    A fence opens on a binding its README established in prose - `sheet`, `workbook`,
    `PageSetup`. That is the one error class which says the fence is incomplete rather than
    false, so it counts only when every diagnostic the compiler raised is of that class; a fence
    that also names something genuinely wrong (Aspose.Cells-FOSS-for-Cpp's own example:002, a
    real `no match for 'operator[]'` type mismatch) must still say so, never be relabeled.
    """
    found: list[str] = []
    for line in diagnostics:
        match = _UNBOUND_IDENTIFIER.search(line)
        if match is None:
            return []
        found.append(match.group(1))
    return found


def _version(compiler: str, workspace: Path, path: str) -> str:
    result = execute(
        [compiler, "--version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment={**profile_environment(workspace), "PATH": path},
    )
    first = result.stdout.strip().splitlines()
    return first[0].strip() if result.return_code == 0 and first else ""


def fetched_includes(build: Path) -> list[Path]:
    """Header directories the configure step's own dependency fetches produced.

    A public header may include a third party's: Aspose.Slides for C++'s `shape_collection.h`
    opens with `#include <pugixml.hpp>`, which is why pugixml is on its library target's public
    link interface, and without it every one of its ten examples stops at that line with a fatal
    error before a single call is checked (measured 2026-09-06). `FetchContent` puts what it
    fetched under `_deps/<name>-src`, so the build the verifier just ran is where a consumer's
    include path comes from - never a download of this module's own.
    """
    deps = build / "_deps"
    if not deps.is_dir():
        return []
    return [
        directory
        for source in sorted(deps.glob("*-src"))
        for name in ("include", "src")
        if (directory := source / name).is_dir()
    ]


def build_product(
    source: Path, workspace: Path, path: str, cmake: str | None, ninja: str | None
) -> tuple[str, list[Path]]:
    """Configure and build the library with CMake and Ninja, and say in one phrase how it went.

    The phrase reaches the receipt because it is a fact about the repository worth carrying, the
    way the TypeScript verifier carries the count of diagnostics in a package's own sources: a
    reader of a receipt should be able to see whether the tree an example was checked against
    builds at all. It never decides an example's verdict on its own - Aspose.Cells for C++ does
    not build with GCC 16.2 and its first example still type-checks - but the configure step is
    what puts a fetched dependency's headers where the syntax check can find them.
    """
    if cmake is None or ninja is None:
        return ("not attempted (no CMake or Ninja on this machine)", [])
    build = workspace / "cmake-build"
    environment = {**profile_environment(workspace), "PATH": path}
    configure = execute(
        [cmake, "-S", str(source), "-B", str(build), "-G", "Ninja"],
        workspace=workspace,
        timeout_seconds=_TIMEOUT_CONFIGURE,
        extra_environment=environment,
    )
    if configure.return_code != 0:
        # A configure that stops partway has still written to disk every dependency it had
        # already fetched, and those headers are the whole reason this step runs at all. Throwing
        # them away turns one slow download into ten unverified examples: measured 2026-09-16 on
        # Aspose.Slides for C++, whose configure was cut off after pugixml and before miniz, so
        # `shape_collection.h` could not find `pugixml.hpp` and every one of its ten examples was
        # NOT_VERIFIED - including the ones that compile, and including the `quick_start` row the
        # contract requires. The phrase separates the two ways a configure ends without
        # finishing, because a receipt saying "failed" of a step that was cut off is not true,
        # and neither phrase is "succeeded", so `build_verified` stays false either way (TB-01).
        stopped = "timed out" if configure.timed_out else "failed"
        return (f"configure {stopped}", fetched_includes(build))
    built = execute(
        [cmake, "--build", str(build)],
        workspace=workspace,
        timeout_seconds=_TIMEOUT_BUILD,
        extra_environment=environment,
    )
    if built.return_code == 0:
        return ("succeeded", fetched_includes(build))
    # The primary (GCC/Clang) toolchain's own build genuinely failed. Before reporting failure,
    # try a second, real compiler if this machine has one recorded - never by altering the
    # target's own CMakeLists.txt/toolchain-detect.cmake, which stays completely unmodified either
    # way; this is a different compiler building that exact same configuration. A repository whose
    # primary build already succeeds never reaches this branch at all.
    msvc = msvc_toolchain(workspace)
    if msvc is not None:
        msvc_build = workspace / "cmake-build-msvc"
        # `msvc.environment["PATH"]` is vcvarsall's own activated PATH (cl.exe's directory, the
        # Windows SDK's rc.exe/mt.exe, and more) - ninja is not part of the VS installation, so its
        # own directory is still prepended explicitly, same as the primary toolchain's own PATH.
        ninja_directory = str(Path(ninja).parent) if ninja else None
        msvc_path = os.pathsep.join(
            part for part in (ninja_directory, msvc.environment.get("PATH", "")) if part
        )
        msvc_environment = {
            **profile_environment(workspace),
            **msvc.environment,
            "PATH": msvc_path,
        }
        msvc_configure = execute(
            [cmake, "-S", str(source), "-B", str(msvc_build), "-G", "Ninja"],
            workspace=workspace,
            timeout_seconds=_TIMEOUT_CONFIGURE,
            extra_environment=msvc_environment,
        )
        if msvc_configure.return_code == 0:
            msvc_built = execute(
                [cmake, "--build", str(msvc_build)],
                workspace=workspace,
                timeout_seconds=_TIMEOUT_BUILD,
                extra_environment=msvc_environment,
            )
            if msvc_built.return_code == 0:
                identity = f" ({msvc.version})" if msvc.version else ""
                return (
                    f"succeeded (MSVC{identity}, after the primary toolchain's own build failed)",
                    fetched_includes(msvc_build),
                )
    return ("failed", fetched_includes(build))


def verify_cpp_examples(
    root: Path,
    manifest: Path | None,
    include_root: Path,
    standard: str,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
) -> list[ExampleReceipt]:
    """One receipt per candidate: compiled, failed to compile, or not verified at all."""
    if not candidates:
        return []
    if manifest is None:
        return _blocked(candidates, "no CMakeLists.txt to compile against; nothing to resolve")
    compiler = cpp_compiler()
    if compiler is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no C++ compiler on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to compile in")
    workspace = fresh
    cmake, ninja = cmake_executable(), ninja_executable()
    path = toolchain_path(compiler, ninja)
    version = _version(compiler, workspace, path)
    if not version:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: the C++ compiler did not report a version")

    product, fetched = build_product(manifest.parent, workspace, path, cmake, ninja)
    language = standard or _DEFAULT_STANDARD
    includes = [
        argument
        for directory in dict.fromkeys([include_root, root / "include", *fetched])
        if directory.is_dir()
        for argument in ("-I", str(directory.resolve()))
    ]
    # The compiler's own tree, so its standard headers are named relatively in a receipt: an
    # absolute path there differs per machine and would move a sealed candidate's bytes.
    toolchain = Path(compiler).parent.parent
    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        name = f"example_{candidate.ordinal:03d}.cpp"
        (workspace / name).write_text(wrap_example(candidate.code), encoding="utf-8", newline="\n")
        result: ExecutionResult = execute(
            [compiler, f"-std=c++{language}", "-fsyntax-only", *includes, name],
            workspace=workspace,
            timeout_seconds=timeout_seconds,
            extra_environment={**profile_environment(workspace), "PATH": path},
        )
        stdout = _scrub(result.stdout, workspace, root, include_root, toolchain)
        stderr = _scrub(result.stderr, workspace, root, include_root, toolchain)
        mine, theirs = split_diagnostics(stdout + "\n" + stderr, name)
        outcome: Any
        build_verified = True
        if result.timed_out:
            outcome, detail = "TIMED_OUT", f"no exit within {timeout_seconds:g}s"
        elif mine:
            unbound = unbound_identifiers(mine)
            if unbound:
                outcome = "NOT_VERIFIED"
                detail = (
                    "the fence uses "
                    + ", ".join(f"`{name}`" for name in dict.fromkeys(unbound))
                    + " without binding it; the README establishes it in an earlier section"
                )
            else:
                outcome, detail = "FAILED", mine[0][:400]
        elif result.return_code == 0:
            outcome = "EXECUTED"
            detail = (
                f"syntax-checked against {manifest.parent.name} with {version} "
                f"-std=c++{language} -fsyntax-only; the library's own CMake build {product}"
            )
            # -fsyntax-only never links or builds the library - it proves the snippet's own calls
            # are well-formed against the headers, nothing about whether `cmake --build` itself
            # succeeds. Only a genuinely successful CMake build lets _source_build_fact promote
            # the advertised `cmake -S . -B build` command as verified (TB-01, external review
            # D1, 2026-09-08: measured on Aspose.Cells for C++, whose CMake build fails while
            # every example still syntax-checks - the sealed README nonetheless called `cmake -S
            # . -B build` "verified against this revision"). `product` starts with "succeeded"
            # both for the primary toolchain's own build and for `build_product`'s own MSVC
            # fallback after the primary toolchain's build genuinely failed - either way this is
            # a real, unmodified build of the target's own configuration.
            build_verified = product.startswith("succeeded")
        elif theirs:
            # Not one diagnostic in the example itself: a header it includes stopped the compiler
            # first, so nothing about the snippet's own calls was observed either way. Measured
            # 2026-09-06 on Aspose.PDF for C++, whose `facades/facade.hpp` holds a
            # `unique_ptr<Document>` with a defaulted destructor over an incomplete type.
            outcome = "NOT_VERIFIED"
            detail = (
                "BLOCKED_TOOLCHAIN: no diagnostic in the example itself; a header it includes "
                f"stopped {version} -std=c++{language} first - {theirs[0][:280]}"
            )
        else:
            said = (stdout + "\n" + stderr).strip().splitlines()
            outcome = "NOT_VERIFIED"
            detail = "BLOCKED_TOOLCHAIN: " + (
                said[0][:300] if said else f"the compiler exited {result.return_code} in silence"
            )
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,
                return_code=result.return_code,
                stdout=_clip(stdout),
                stderr=_clip(stderr),
                detail=detail,
                fixtures=(),
                build_verified=build_verified,
            )
        )
    return receipts
