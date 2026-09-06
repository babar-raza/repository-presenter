"""Type-check each README example against the repository's own sources, in an isolated workspace.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: TypeScript's bar is a *type-checking* example, not an executed one. `tsc --noEmit` proves
exactly what the contract claims - the example's imports resolve, and its types and calls exist
and check against this revision.

Three rules the outcome respects. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED` - never `CONTRADICTED`, because "we could not check" is not
"we checked and it is false". Every cache and credential store is redirected into the run
directory, and the compiler is called by its resolved absolute path with nothing added to the
user's `PATH`. And the verdict is read from the diagnostics raised *in the example's own file*:
a diagnostic in the library's sources is a fact about the library's build environment, not about
whether the README's snippet is true, and letting one condemn the other would fail every example
of a package whose sources reference Node globals it does not declare types for (measured
2026-09-06: 37 such diagnostics on Aspose.3D for TypeScript, 45 on Aspose.Cells, none of them in
an example).
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.typescript_barrel import (
    IGNORED_DIRECTORIES,
    compiler_options,
)
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

_MAX_OUTPUT_CHARS = 4000
_WORKSPACE_ATTEMPTS = 5
# `<file>(<line>,<column>): error TSxxxx: <message>` is the only diagnostic shape tsc prints
# without `--pretty`, which is off by default when stdout is not a terminal.
_DIAGNOSTIC = re.compile(r"^(?P<file>[^(]+)\((?P<line>\d+),(?P<column>\d+)\): error (?P<rest>.+)$")
# The lane's toolchains are never on PATH (loop-prompt §1.3): a name is resolved by `which`, then
# by its `.cmd` shim, then by the machine-local registry the lane's receipt records.
_REGISTRY_VARIABLE = "RP_TOOLCHAIN_REGISTRY"
_REGISTRY_DEFAULT = Path("C:/tools/rp-toolchains/TOOLCHAIN_PATHS.txt")
# What a snippet is checked under. Not the package's own `strict` settings: the contract's claim
# is that the example's types and calls exist at this revision, and a README snippet is not
# required to satisfy the library's own lint policy to prove that.
_BASE_FLAGS = (
    "--noEmit",
    "--skipLibCheck",
    "--esModuleInterop",
    "--allowSyntheticDefaultImports",
    "--resolveJsonModule",
)
_DEFAULT_TARGET = "ES2020"
# A README snippet may await at top level, which only an ES module allows; the package's own
# `module` setting governs how it emits, not how a consumer's script is checked.
_DEFAULT_MODULE = "es2022"
_DEFAULT_RESOLUTION = "node"
_BUNDLER_MODULES = frozenset({"bundler", "node16", "nodenext"})
# TypeScript ships these declarations; `DOM` is what declares `console`, `Element` and `Document`,
# which a package targeting `lib: ["ES2020"]` alone does not have (measured 2026-09-06: three of
# Aspose.3D for TypeScript's nine examples failed on `console` alone).
_HOST_LIBRARY = "DOM"
_HOST_DECLARATIONS = "rp_host_environment.d.ts"
# A configuration file beside a file named on the command line is `error TS5112` on TypeScript 7,
# and the compiler then reports nothing else at all. Its options are read from the clone instead.
_CONFIG_FILES = frozenset({"tsconfig.json", "jsconfig.json"})
# The runtime a README script runs in, and the modules it may import from it. Declared as a
# shorthand ambient module - a name with no body, whose imports are `any` - so a missing
# `@types/node` cannot make a true example look false. The claim the contract makes about an
# example is that its calls into *the package* exist at this revision; the host's own surface is
# not that claim, and no assertion here can make a package's member appear.
_NODE_MODULES = (
    "assert",
    "buffer",
    "child_process",
    "crypto",
    "events",
    "fs",
    "fs/promises",
    "http",
    "https",
    "os",
    "path",
    "process",
    "stream",
    "stream/promises",
    "url",
    "util",
    "zlib",
)
_HOST_SOURCE = "\n".join(
    [
        "// Written by the TypeScript verifier, never by the repository: the Node host surface a",
        "// README script assumes, so that a missing @types/node is not read as a false example.",
        "declare var require: any;",
        "declare var process: any;",
        "declare var Buffer: any;",
        "declare var __dirname: string;",
        "declare var __filename: string;",
        "declare namespace NodeJS { type Timeout = any; type ReadableStream = any; }",
        *[f"declare module '{name}';" for name in _NODE_MODULES],
        *[f"declare module 'node:{name}';" for name in _NODE_MODULES],
        "",
    ]
)


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


def typescript_compiler() -> str | None:
    """`tsc` as this machine offers it, or None when it offers none.

    Resolved by `which`, then by the `.cmd` shim Windows installs instead of an executable, then
    by the absolute path the lane's toolchain registry records - nothing is on `PATH` here
    (`evidence/build/lanes/lane-b/LANE-B-00.json`).
    """
    for candidate in ("tsc", "tsc.cmd"):
        found = shutil.which(candidate)
        if found:
            return found
    return recorded_tool("tsc")


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

    The same rule the .NET verifier needs: this checkout is on OneDrive, which holds handles, and
    failing to clean scratch space must never cost a repository its candidate.
    """
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def stage_sources(root: Path, workspace: Path) -> None:
    """Copy the repository's sources beside the examples, with the build output it declares.

    A README's example imports the package by a path relative to the checkout - `./aspose_cells`
    on Cells, `./dist/aspose/threed` on 3D - so the snippet only resolves from a directory shaped
    like the checkout. The clone itself is read-only and must stay that way, so the sources are
    copied rather than written into.

    `dist/` is the case worth naming. Aspose.3D for TypeScript's README imports `./dist/...`, a
    directory the repository never contains because it is build output; `tsconfig.json` declares
    `rootDir: ./src` and `outDir: ./dist`, which says exactly which sources that output is built
    from. Copying `src` to `dist` is that declared mapping, so the example is checked against the
    sources its import names - not against a guess, and not against nothing.

    The host declarations go in beside them, for the reason `_HOST_SOURCE` records. The
    repository's own `tsconfig.json` does not come along: its options are read from the clone and
    passed as flags, and a configuration file sitting beside a file named on the command line is
    `error TS5112` on TypeScript 7 - measured 2026-09-06 on the hosted runner, whose `tsc` is
    7.0.2, where it made the compiler refuse to run and report nothing at all.
    """
    ignore = shutil.ignore_patterns(*sorted(IGNORED_DIRECTORIES))
    for child in root.iterdir():
        if child.name in IGNORED_DIRECTORIES or child.name in _CONFIG_FILES:
            continue
        if child.is_dir():
            shutil.copytree(child, workspace / child.name, ignore=ignore, dirs_exist_ok=True)
        elif child.is_file():
            shutil.copy2(child, workspace / child.name)
    options = compiler_options(root)
    out_dir = str(options.get("outDir", "")).strip().lstrip("./").rstrip("/")
    root_dir = str(options.get("rootDir", "")).strip().lstrip("./").rstrip("/")
    source = workspace / root_dir if root_dir else None
    if out_dir and source is not None and source.is_dir() and not (workspace / out_dir).exists():
        shutil.copytree(source, workspace / out_dir)
    (workspace / _HOST_DECLARATIONS).write_text(_HOST_SOURCE, encoding="utf-8", newline="\n")


def _flags(root: Path) -> list[str]:
    """The compiler flags for this package: its own language level, an ES module, its resolution.

    `target` and `moduleResolution` are the package's own declarations, because a snippet is
    checked against the library the way the library is built. `module` is not: a README snippet
    may `await` at top level, which CommonJS forbids and every published consumer of these
    packages is free to use.
    """
    options = compiler_options(root)
    target = str(options.get("target", "") or _DEFAULT_TARGET)
    resolution = str(options.get("moduleResolution", "") or _DEFAULT_RESOLUTION)
    module = "esnext" if resolution.lower() in _BUNDLER_MODULES else _DEFAULT_MODULE
    flags = [*_BASE_FLAGS, "--target", target, "--module", module]
    flags.extend(["--moduleResolution", resolution])
    declared = options.get("lib")
    library = [str(item) for item in declared] if isinstance(declared, list) else [target]
    if not any(item.lower() == _HOST_LIBRARY.lower() for item in library):
        library.append(_HOST_LIBRARY)
    flags.extend(["--lib", ",".join(library)])
    return flags


def _scrub(text: str, workspace: Path) -> str:
    """This machine's paths out of the compiler's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home directory
    must not appear in it - and a path that differs per machine would move a sealed candidate's
    bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {workspace, workspace.resolve()}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def split_diagnostics(output: str, example: str) -> tuple[list[str], list[str]]:
    """The compiler's diagnostics, separated into the example's own and the library's.

    The example's decide the outcome. The library's are counted into the detail so a reader of the
    receipt can see the check ran against a tree that does not fully compile on its own, which is
    a fact about the repository worth carrying rather than hiding.
    """
    mine: list[str] = []
    theirs: list[str] = []
    for line in output.splitlines():
        match = _DIAGNOSTIC.match(line.strip())
        if match is None:
            continue
        where = match.group("file").replace("\\", "/").lstrip("./")
        (mine if where == example else theirs).append(line.strip())
    return (mine, theirs)


def _version(compiler: str, workspace: Path) -> str:
    result = execute(
        [compiler, "--version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment=profile_environment(workspace),
    )
    return result.stdout.strip() if result.return_code == 0 else ""


def verify_typescript_examples(
    root: Path,
    barrel: Path | None,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
) -> list[ExampleReceipt]:
    """One receipt per candidate: type-checked, failed to type-check, or not verified at all."""
    if not candidates:
        return []
    if barrel is None:
        return _blocked(candidates, "no package entry point to check against; nothing to resolve")
    compiler = typescript_compiler()
    if compiler is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no tsc on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to type-check in")
    workspace = fresh
    version = _version(compiler, workspace)
    if not version:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: tsc did not report a version")
    try:
        stage_sources(root, workspace)
    except OSError as error:
        return _blocked(candidates, f"BLOCKED_TOOLCHAIN: the sources would not stage ({error})")

    flags = _flags(root)
    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        name = f"example_{candidate.ordinal:03d}.ts"
        (workspace / name).write_text(candidate.code, encoding="utf-8", newline="\n")
        result: ExecutionResult = execute(
            [compiler, *flags, _HOST_DECLARATIONS, name],
            workspace=workspace,
            timeout_seconds=timeout_seconds,
            extra_environment=profile_environment(workspace),
        )
        stdout = _scrub(result.stdout, workspace)
        stderr = _scrub(result.stderr, workspace)
        mine, theirs = split_diagnostics(stdout + "\n" + stderr, name)
        aside = f"; {len(theirs)} in the package's own sources" if theirs else ""
        outcome: Any
        if result.timed_out:
            outcome, detail = "TIMED_OUT", f"no exit within {timeout_seconds:g}s"
        elif mine:
            outcome, detail = "FAILED", mine[0][:400]
        elif result.return_code != 0 and not theirs:
            # The compiler refused, and named no file: nothing was checked, so nothing is proven
            # either way. Measured 2026-09-06 on the hosted runner, whose tsc is 7.0.2: a
            # `tsconfig.json` beside the file raised `TS5112` and the run exited 1 with no filed
            # diagnostic at all, which the two branches above would have read as a pass.
            said = (stdout + "\n" + stderr).strip().splitlines()
            outcome = "NOT_VERIFIED"
            detail = "BLOCKED_TOOLCHAIN: " + (
                said[0][:300] if said else f"tsc exited {result.return_code} and said nothing"
            )
        else:
            outcome = "EXECUTED"
            detail = f"type-checked against {root.name} with {version.strip()} --noEmit{aside}"
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,
                return_code=result.return_code,
                stdout=_clip(stdout),
                stderr=_clip(stderr),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts
