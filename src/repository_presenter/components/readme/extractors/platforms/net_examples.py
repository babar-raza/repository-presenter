"""Compile each README example against the repository's own project, in an isolated workspace.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: .NET's bar is a *compilable* C# example, not an executed one. A snippet in a README is not
a program, so it is wrapped in a console project that references the product's own project and
built; what that proves is exactly what the contract claims — the example's types and calls exist
and type-check against this revision.

Three rules the outcome must respect. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED` — never `CONTRADICTED`, because "we could not check" is not
"we checked and it is false". Every cache and credential store is redirected into the run
directory, so a build cannot read or leave state in the developer's account. And the resolved SDK
version goes into the receipt, because a build is only as reproducible as the toolchain that ran.
"""

from __future__ import annotations

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


def _sdk_version(dotnet: str, workspace: Path) -> str:
    result = execute(
        [dotnet, "--version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment=profile_environment(workspace),
    )
    return result.stdout.strip() if result.return_code == 0 else ""


def verify_net_examples(
    root: Path,
    project: Path | None,
    framework: str,
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
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    version = _sdk_version(dotnet, workspace)
    if not version:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: the dotnet SDK did not report a version")

    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        run_dir.mkdir()
        (run_dir / "Example.csproj").write_text(
            _PROJECT.format(
                framework=framework or _FALLBACK_FRAMEWORK,
                reference=project.resolve().as_posix(),
            ),
            encoding="utf-8",
            newline="\n",
        )
        (run_dir / "Program.cs").write_text(candidate.code, encoding="utf-8", newline="\n")
        result: ExecutionResult = execute(
            [dotnet, "build", "--nologo", "-v", "quiet"],
            workspace=run_dir,
            timeout_seconds=NET.example_timeout_seconds,
            extra_environment=profile_environment(run_dir),
        )
        if result.timed_out:
            outcome, detail = "TIMED_OUT", f"no exit within {NET.example_timeout_seconds:g}s"
        elif result.return_code == 0:
            outcome, detail = "EXECUTED", f"compiled against {project.name}; SDK {version}"
        else:
            outcome, detail = "FAILED", _first_error(result.stdout, result.stderr)
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(result.stdout),
                stderr=_clip(result.stderr),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts


def _first_error(stdout: str, stderr: str) -> str:
    """The compiler's own first diagnostic, which names the type or member that is missing."""
    for line in (stdout + "\n" + stderr).splitlines():
        if ": error " in line:
            return line.strip()[:400]
    return "the build failed without naming a diagnostic"
