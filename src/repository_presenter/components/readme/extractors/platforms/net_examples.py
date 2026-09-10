"""Compile each README example against the repository's own project, in an isolated workspace.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: .NET's bar is a *compilable* C# example, not an executed one. A snippet in a README is not
a program, so it is wrapped in a console project that references the product's own project and
built; what that proves is exactly what the contract claims — the example's types and calls exist
and type-check against this revision.

Four rules the outcome must respect. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED` — never `CONTRADICTED`, because "we could not check" is not
"we checked and it is false". Every cache and credential store is redirected into the run
directory, so a build cannot read or leave state in the developer's account. The resolved SDK
version goes into the receipt, because a build is only as reproducible as the toolchain that ran.
And a snippet naming a product type without its own `using` is supplied one, the way
`ImplicitUsings` already supplies the base class library's own common namespaces but never the
product's (Taskcard F Tier 2; `java_examples.py`'s own `_needed_imports()` is the same check for
Java's imports) - a snippet naming something the product genuinely does not export still fails.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.ecosystems import NET
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

_MAX_OUTPUT_CHARS = 4000
# Top-level statements need no class or Main, so a README snippet drops straight in. The
# implicit usings and the nullable setting match what a modern project template emits, so a
# snippet written against the product's own samples compiles the same way here.
_PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>{framework}</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <RestorePackages>true</RestorePackages>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="{reference}" />
  </ItemGroup>
</Project>
"""
_FALLBACK_FRAMEWORK = "net8.0"
_SDK_VERSION = re.compile(r"^(\d+)\.(\d+)\.")
# MSBuild appends the project that raised a diagnostic in brackets; the diagnostic is the part
# a disposition acts on.
_TRAILING_PROJECT = re.compile(r"\s*\[[^\]]*\]\s*$")
# The wall-clock cost of this build, on this machine, right now - never reproducible and never
# evidence about the repository.
_TIME_ELAPSED = re.compile(r"(?m)^Time Elapsed .*\r?\n?")
_WORKSPACE_ATTEMPTS = 5
# A README fence is written for a reader who already has the `using` its surrounding prose
# established - the same gap java_examples.py's own _needed_imports() already closes for Java
# (Taskcard F Tier 2). Real Aspose .NET source (measured 2026-09-10 across all six cohort
# repositories) declares exactly one namespace per file - block-scoped (`namespace X { ... }`,
# Cells and Words) or file-scoped (`namespace X;`, 3D/PDF/Slides/Email all use it extensively) -
# so the first namespace found in a file is the namespace every public type declared in that
# same file belongs to; no brace-tracking needed.
# \s* (not [ \t]*) between the name and its terminator: Allman style puts the opening brace of a
# block-scoped namespace on its own line (measured 2026-09-10 on the real Cells-.NET source),
# which a same-line-only whitespace class would miss entirely.
_CS_NAMESPACE = re.compile(r"(?m)^[ \t]*namespace[ \t]+([\w.]+)\s*[;{]")
_CS_TYPE = re.compile(
    r"(?m)^[ \t]*public[ \t]+"
    r"(?:(?:abstract|sealed|static|partial|readonly|unsafe)[ \t]+)*"
    r"(?:class|struct|interface|enum|record)[ \t]+"
    r"(\w+)"
)
# `using static X;` targets a type's own static members, not a namespace - excluded, the same
# way ImplicitUsings only ever supplies namespace-level usings.
_CS_USING = re.compile(r"(?m)^[ \t]*using[ \t]+(?!static\b)([\w.]+)[ \t]*;")
_CS_IDENTIFIER = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")


def dotnet_executable() -> str | None:
    """The SDK this machine offers, `.cmd` shim included, or None when it has none."""
    for name in ("dotnet", "dotnet.exe", "dotnet.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


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


def _sdk_framework(version: str) -> str:
    """The framework the wrapper project targets: the one this SDK builds by default.

    Not the package's floor. Measured 2026-09-06 on the .NET cohort: Aspose.3D declares its
    multi-target list only under Release, so a Debug build of the library produces `net10.0`
    alone and a `netcoreapp3.1` wrapper failed every example with NU1201; Cells and Words
    declare `netstandard2.0`, which no executable may target at all. A current framework
    consumes a library built for any lower one, which is what the wrapper needs, while the floor
    stays what it is - the requirement the Dependencies row reports to a reader.
    """
    match = _SDK_VERSION.match(version.strip())
    return f"net{match.group(1)}.{match.group(2)}" if match else _FALLBACK_FRAMEWORK


def _fresh_workspace(workspace: Path) -> Path | None:
    """An empty run directory, even when Windows will not let the last one go.

    Measured 2026-09-06 on Aspose.Words for .NET: `rmtree` raised WinError 145 on a NuGet cache
    file inside the previous run's disposable profile - this checkout is on OneDrive, which holds
    handles - and the exception took the whole facts stage down. A run that cannot have the
    directory back can always have the next one; failing to clean scratch space must never cost
    a repository its candidate. None means every attempt was refused, which is BLOCKED_TOOLCHAIN.
    """
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def _scrub(text: str, run_dir: Path) -> str:
    """This machine's paths, and this run's own clock, out of a compiler's output.

    MSBuild prints absolute paths and appends the project in brackets. A receipt becomes a
    fact's evidence and a fact is published, so the developer's home directory must not appear
    in it - and a path that differs per machine would move a sealed candidate's bytes for a
    reason that is not the repository. Measured 2026-09-06 on Aspose.Slides for .NET, whose
    facts carried `D:\\Users\\...\\runs\\verify\\a50008248340\\example_003\\Program.cs(1,30):
    error CS0246`.

    MSBuild also prints its own wall-clock cost on the last line of every build, succeeded or
    failed - `Time Elapsed 00:00:26.84` - which cannot repeat between two runs of the same
    example by its very nature. Measured 2026-09-06 on Aspose.Cells for .NET: two runs of an
    otherwise byte-identical, zero-provider-call composition produced two different
    `examples.json` files and withdrew the seal's no-op proof, because that timing line is
    stored verbatim in the receipt. The SDK version stays - a build is only as reproducible as
    the toolchain that ran it - but how long this machine took to run it is not evidence of
    anything the repository did.
    """
    cleaned = text
    for base in {run_dir, run_dir.resolve()}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return _TIME_ELAPSED.sub("", cleaned)


def _sdk_version(dotnet: str, workspace: Path) -> str:
    result = execute(
        [dotnet, "--version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment=profile_environment(workspace),
    )
    return result.stdout.strip() if result.return_code == 0 else ""


def public_types(source_root: Path) -> dict[str, str]:
    """Every product type whose simple name is unambiguous, mapped to its fully qualified name.

    A simple name two files disagree on is dropped rather than guessed - a `using` naming one of
    them would silently prefer whichever this scan happened to see last, which is picking one
    when picking one would be an invention (the same rule java_examples.py's own public_types()
    already applies).
    """
    seen: dict[str, str] = {}
    ambiguous: set[str] = set()
    for path in sorted(source_root.rglob("*.cs")):
        text = path.read_text(encoding="utf-8", errors="replace")
        found_namespace = _CS_NAMESPACE.search(text)
        if found_namespace is None:
            continue
        namespace = found_namespace.group(1)
        for match in _CS_TYPE.finditer(text):
            name = match.group(1)
            qualified = f"{namespace}.{name}"
            if name in seen and seen[name] != qualified:
                ambiguous.add(name)
            seen[name] = qualified
    return {name: qualified for name, qualified in seen.items() if name not in ambiguous}


def _needed_usings(code: str, declared: Sequence[str], types: dict[str, str]) -> list[str]:
    """Namespace usings for the product types the snippet names and whose namespace it does not
    already bring in - a `using` targets a namespace, not a single type, so a reference is
    already covered whenever its own namespace is among the ones the snippet already declares
    (``declared``: the namespaces ``_CS_USING`` already found in the snippet, not raw lines).

    Ported from java_examples.py's own _needed_imports() (Taskcard F Tier 2, PHASE0-MASTER-
    PLAN.md's appendix: ".NET's 6 non-EXECUTED examples are a missing-using problem, not
    undeclared-variable - Java's _needed_imports() pattern applies directly").
    """
    already = set(declared)
    wanted = {
        types[name].rsplit(".", 1)[0]
        for name in _CS_IDENTIFIER.findall(code)
        if name in types and types[name].rsplit(".", 1)[0] not in already
    }
    return sorted(f"using {namespace};" for namespace in wanted)


def verify_net_examples(
    root: Path,
    project: Path | None,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
) -> list[ExampleReceipt]:
    """One receipt per candidate: compiled, failed to compile, or not verified at all."""
    if not candidates:
        return []
    if project is None:
        return _blocked(candidates, "no project file to reference; nothing to compile against")
    dotnet = dotnet_executable()
    if dotnet is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no dotnet SDK on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to build in")
    workspace = fresh
    version = _sdk_version(dotnet, workspace)
    if not version:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: the dotnet SDK did not report a version")
    types = public_types(project.parent)

    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        run_dir.mkdir()
        (run_dir / "Example.csproj").write_text(
            _PROJECT.format(
                framework=_sdk_framework(version),
                reference=project.resolve().as_posix(),
            ),
            encoding="utf-8",
            newline="\n",
        )
        declared = _CS_USING.findall(candidate.code)
        supplied = _needed_usings(candidate.code, declared, types)
        program = "".join(f"{line}\n" for line in supplied) + candidate.code
        (run_dir / "Program.cs").write_text(program, encoding="utf-8", newline="\n")
        result: ExecutionResult = execute(
            # WarningLevel=0 silences the compiler entirely, not just this project: the
            # ProjectReference rebuilds the product from source every time (§29.6 E5 - the
            # workspace is disposable, so nothing about the product is ever cached), and its own
            # warnings drown out the one thing this build proves. Measured 2026-09-06 on
            # Aspose.3D for .NET: two runs of the identical wrapper produced two different
            # truncated receipts, because the product alone emits far more than the 4000-
            # character clip and the compiler's own warning order is not stable between builds -
            # a receipt that changes for a reason the repository did not cause voids the seal's
            # no-op proof exactly as the wall-clock line did.
            [dotnet, "build", "--nologo", "-v", "quiet", "-p:WarningLevel=0"],
            workspace=run_dir,
            timeout_seconds=NET.example_timeout_seconds,
            extra_environment=profile_environment(run_dir),
        )
        if result.timed_out:
            outcome, detail = "TIMED_OUT", f"no exit within {NET.example_timeout_seconds:g}s"
        elif result.return_code == 0:
            added = f"; usings supplied: {', '.join(supplied)}" if supplied else ""
            outcome = "EXECUTED"
            detail = f"compiled against {project.name}; SDK {version}{added}"
        else:
            outcome, detail = "FAILED", _first_error(result.stdout, result.stderr, run_dir)
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(_scrub(result.stdout, run_dir)),
                stderr=_clip(_scrub(result.stderr, run_dir)),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts


def _first_error(stdout: str, stderr: str, run_dir: Path) -> str:
    """The compiler's own first diagnostic, which names the type or member that is missing.

    Reported without this machine's paths and without MSBuild's trailing project bracket, so the
    diagnostic a reader and a disposition see is the diagnostic and nothing else.
    """
    for line in _scrub(stdout + "\n" + stderr, run_dir).splitlines():
        if ": error " in line:
            return _TRAILING_PROJECT.sub("", line.strip())[:400]
    return "the build failed without naming a diagnostic"
