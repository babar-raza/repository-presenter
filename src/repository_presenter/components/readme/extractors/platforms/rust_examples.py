"""Check each README example against the crate's own sources, as a Cargo example target.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: Rust's bar is a *type-checked* example, not an executed one. `cargo check` on the crate
proves the library compiles at this revision, and `cargo check --example` proves the snippet's
paths, types and calls exist in that library - which is exactly the claim the contract makes about
an example, and all a README snippet that writes files to disk could honestly be asked for.

The work is done once per composition, not once per fence. A cold `cargo check` of Aspose.Cells
for Rust resolves seven requirements, compiles two native build scripts and takes 253 seconds
(measured 2026-09-06, disposable `CARGO_HOME`); every example after it reuses that target
directory and returns in under a second. So the crate is copied into one run workspace, checked
once, and each fence is then written into that copy's `examples/` directory and checked by name.
The copy is what keeps the pinned clone untouched, and `--locked` on every example check keeps
each fence honest about the same resolved dependency set the crate itself was checked against.

A fence is an excerpt far more often than it is a program: six of this crate's seven Rust fences
open on `sheet`, `workbook` or `valid_path`, bindings the README's own prose established a
section earlier. The compiler names those - `error[E0425]: cannot find value ... in this scope` -
and a fence whose only errors are that is `NOT_VERIFIED`, never `FAILED`: an excerpt we could not
complete is not an example that is false (§29.6 E5). Inventing the missing binding would be
writing the example rather than checking it.

Three rules the outcome respects. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED`. Every cache and credential store is redirected into the run
directory, and `cargo` is called by its resolved absolute path with nothing added to the user's
`PATH`. And the resolved toolchain version goes into the receipt, because a check is only as
reproducible as the toolchain that ran it.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

_MAX_OUTPUT_CHARS = 4000
_WORKSPACE_ATTEMPTS = 5
_CRATE_DIRECTORY = "crate"
_EXAMPLE_STEM = "rp_example"
# The lane's toolchains are never on PATH (loop-prompt §1.3): a name is resolved by `which`, then
# by its `.cmd` shim, then by the absolute path the machine-local registry records.
_REGISTRY_VARIABLE = "RP_TOOLCHAIN_REGISTRY"
_REGISTRY_DEFAULT = Path("C:/tools/rp-toolchains/TOOLCHAIN_PATHS.txt")
# `cargo` and `rustc` are rustup proxies; they find the toolchain through RUSTUP_HOME, and the
# disposable profile has already moved USERPROFILE away from the `.rustup` beside it.
_RUSTUP_HOME = "RUSTUP_HOME"
_CARGO_VERSION = re.compile(r"cargo\s+(\d+\.\d+\.\d+)")
# What the compiler prints for a name the snippet uses and never binds. It is the one diagnostic
# that says "this fence is an excerpt" rather than "this fence is wrong".
_UNBOUND_VALUE = re.compile(r"error\[E0425\]:\s*cannot find value `([^`]+)`")
_ERROR_CODE = re.compile(r"^error(?:\[(E\d+)\])?:")
# Cargo's own closing summary - `error: could not compile ... due to 1 previous error` - is a
# restatement of the diagnostics above it, not a diagnostic. Counting it as one uncoded error made
# every excerpt read FAILED instead of NOT_VERIFIED (caught 2026-09-06 before the cohort ran).
_CARGO_SUMMARY = re.compile(r"^error:\s*(?:could not compile|aborting due to)")
_MAIN_FUNCTION = re.compile(r"(?m)^\s*(?:pub\s+)?(?:async\s+)?fn\s+main\s*\(")
# Directories a crate copy must not carry: version control, and anything a previous build left.
_UNCOPIED = frozenset({".git", "target", ".github", "node_modules"})


def _registry_path() -> Path:
    recorded = os.environ.get(_REGISTRY_VARIABLE, "").strip()
    return Path(recorded) if recorded else _REGISTRY_DEFAULT


def recorded_tool(name: str) -> str | None:
    """The absolute path the machine-local toolchain registry records for ``name``, if any."""
    try:
        text = _registry_path().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name and Path(value.strip()).exists():
            return value.strip()
    return None


def cargo_executable() -> str | None:
    """`cargo` as this machine offers it, or None when it offers none."""
    for candidate in ("cargo", "cargo.exe"):
        found = shutil.which(candidate)
        if found:
            return found
    return recorded_tool("cargo")


def rustup_home(cargo: str) -> str | None:
    """Where the toolchain the `cargo` proxy resolves actually lives.

    The proxy reads `RUSTUP_HOME`, and failing that `~/.rustup` - which the disposable profile
    has just pointed at an empty run directory, so leaving it unset makes every check fail with
    "no default toolchain configured". The ambient value wins, then the registry's record, then
    the home rustup installs beside its own `cargo-home`.
    """
    ambient = os.environ.get(_RUSTUP_HOME, "").strip()
    if ambient:
        return ambient
    recorded = recorded_tool("rustup_home")
    if recorded:
        return recorded
    sibling = Path(cargo).parent.parent.parent / "rustup-home"
    return str(sibling) if sibling.is_dir() else None


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
    """An empty run directory, even when Windows will not let the last one go."""
    workspace = Path(workspace).absolute()
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def _scrub(text: str, *paths: Path) -> str:
    """This machine's paths out of the toolchain's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home
    directory must not appear in it - and a path that differs per machine would move a sealed
    candidate's bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {path for source in paths for path in (source, source.resolve())}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def completed_source(code: str, lib_path: str) -> str:
    """The snippet as a compilable Cargo example.

    A fence that declares `fn main` is a program and is left exactly as written - completing it
    would hide the very defect the check is for. Anything else is a run of statements, and Rust
    lets a block hold items as well as statements, so the whole fence goes inside one `main` that
    returns `Result`: a README snippet uses `?` freely and a `main` returning `()` would report a
    type error about the wrapper rather than about the example. The glob import is the fence's
    import block, synthesized the way the Go verifier synthesizes one - a path the crate does not
    re-export still fails, which is what makes the check worth running.
    """
    body = code if code.endswith("\n") else code + "\n"
    if _MAIN_FUNCTION.search(code):
        return body
    prelude = "#![allow(unused)]\n"
    if lib_path:
        prelude += f"use {lib_path}::*;\n"
    prelude += "use std::error::Error;\n\n"
    indented = "\n".join(f"    {line}" if line.strip() else "" for line in body.splitlines())
    return f"{prelude}fn main() -> Result<(), Box<dyn Error>> {{\n{indented}\n    Ok(())\n}}\n"


def unbound_values(diagnostics: str) -> list[str]:
    """The names the fence uses and never binds, when they are the only thing wrong.

    An excerpt opens on a binding its README established in prose - `sheet`, `workbook`,
    `valid_path`. That is the one error class which says the fence is incomplete rather than
    false, so it counts only when every error the compiler raised is of that class; a fence that
    also names a type the crate does not export is genuinely wrong and must say so.
    """
    codes = [
        match.group(1)
        for line in diagnostics.splitlines()
        if not _CARGO_SUMMARY.match(line.strip()) and (match := _ERROR_CODE.match(line.strip()))
    ]
    reported = sorted(set(_UNBOUND_VALUE.findall(diagnostics)))
    if not reported or any(code != "E0425" for code in codes):
        return []
    return reported


def _copy_crate(source: Path, destination: Path) -> bool:
    """The crate's own files, without version control or a previous build's output."""
    try:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(*_UNCOPIED),
            dirs_exist_ok=True,
        )
    except OSError:
        return False
    return True


def _first_diagnostic(output: str) -> str:
    """The compiler's own first error line, which names what is missing."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("error"):
            return stripped[:400]
    return "the check failed without naming a diagnostic"


def _check(
    cargo: str,
    crate: Path,
    environment: dict[str, str],
    timeout: float,
    *,
    locked: bool,
    example: str = "",
) -> tuple[ExecutionResult, str]:
    argv = [cargo, "check"]
    if locked:
        argv.append("--locked")
    if example:
        argv.extend(["--example", example])
    result = execute(argv, workspace=crate, timeout_seconds=timeout, extra_environment=environment)
    return (result, _scrub(result.stdout + "\n" + result.stderr, crate))


def verify_rust_examples(
    crate_directory: Path,
    crate_name: str,
    lib_path: str,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
) -> list[ExampleReceipt]:
    """One receipt per candidate: type-checked, wrong, or an excerpt we would not invent."""
    if not candidates:
        return []
    if not crate_name:
        return _blocked(candidates, "no Cargo.toml to check against; nothing to compile")
    cargo = cargo_executable()
    if cargo is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no Cargo toolchain on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to check in")
    crate = fresh / _CRATE_DIRECTORY
    if not _copy_crate(crate_directory, crate):
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: the crate could not be copied to check it")
    environment = {**profile_environment(fresh), "CARGO_TERM_COLOR": "never"}
    home = rustup_home(cargo)
    if home:
        environment[_RUSTUP_HOME] = home
    probe = execute(
        [cargo, "--version"], workspace=crate, timeout_seconds=60.0, extra_environment=environment
    )
    found = _CARGO_VERSION.search(probe.stdout) if probe.return_code == 0 else None
    if found is None:
        return _blocked(
            candidates, "BLOCKED_TOOLCHAIN: the Cargo toolchain did not report a version"
        )
    toolchain = found.group(1)

    # The crate itself first: an example checked against a library that does not compile would
    # report the library's defect as the example's.
    shipped_lock = (crate / "Cargo.lock").is_file()
    build, output = _check(cargo, crate, environment, timeout_seconds, locked=shipped_lock)
    if build.timed_out:
        return _blocked(
            candidates,
            f"BLOCKED_TOOLCHAIN: cargo check did not finish within {timeout_seconds:g}s",
        )
    if build.return_code != 0:
        return _blocked(
            candidates, f"the crate does not check at this revision: {_first_diagnostic(output)}"
        )
    examples = crate / "examples"
    examples.mkdir(exist_ok=True)

    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        name = f"{_EXAMPLE_STEM}_{candidate.ordinal:03d}"
        (examples / f"{name}.rs").write_text(
            completed_source(candidate.code, lib_path), encoding="utf-8", newline="\n"
        )
        # `--locked` from here on: `cargo check` above wrote the lock, so every fence is checked
        # against the same resolved dependency set the crate itself was.
        result, diagnostics = _check(
            cargo, crate, environment, timeout_seconds, locked=True, example=name
        )
        outcome, detail = _outcome(result, diagnostics, crate_name, toolchain, timeout_seconds)
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(_scrub(result.stdout, crate)),
                stderr=_clip(_scrub(result.stderr, crate)),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts


def _outcome(
    result: ExecutionResult,
    diagnostics: str,
    crate_name: str,
    toolchain: str,
    timeout_seconds: float,
) -> tuple[str, str]:
    """What the check said, and the sentence a fact's evidence or a disposition acts on."""
    if result.timed_out:
        return ("TIMED_OUT", f"no exit within {timeout_seconds:g}s")
    if result.return_code == 0:
        return ("EXECUTED", f"COMPILED against {crate_name}; cargo {toolchain}")
    unbound = unbound_values(diagnostics)
    if unbound:
        return (
            "NOT_VERIFIED",
            "the fence uses "
            + ", ".join(f"`{name}`" for name in unbound)
            + " without binding it; the README establishes it in an earlier section",
        )
    return ("FAILED", _first_diagnostic(diagnostics))
