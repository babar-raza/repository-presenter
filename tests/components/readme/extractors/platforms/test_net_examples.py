"""The .NET verifier compiles a snippet against the product, and is honest when it cannot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.platforms import net_examples
from repository_presenter.core.examples import ExampleCandidate
from repository_presenter.core.execution import ExecutionResult


def _candidate(ordinal: int, code: str) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal, "csharp", code, "README.md", 1, 3, f"inherited_unit:{ordinal:03d}.code_block"
    )


def _result(code: int, stdout: str = "", stderr: str = "", timed_out: bool = False):
    return ExecutionResult(
        argv=("dotnet",),
        return_code=code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        environment_names=(),
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    source = tmp_path / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    path = source / "Aspose.Widget.csproj"
    path.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    return path


def test_a_machine_without_the_sdk_reports_not_verified(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 29.6 E5: BLOCKED_TOOLCHAIN is UNRESOLVED downstream, never CONTRADICTED."""
    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: None)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var w = 1;")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in (receipts[0].detail or "")


def test_a_repository_with_no_project_has_nothing_to_compile_against(tmp_path: Path) -> None:
    receipts = net_examples.verify_net_examples(
        tmp_path, None, [_candidate(1, "var w = 1;")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "no project file" in (receipts[0].detail or "")


def test_a_snippet_that_compiles_is_executed_and_carries_the_sdk_version(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bar for .NET is compilation; the receipt records the SDK that judged it."""
    calls: list[list[str]] = []

    def fake(argv: list[str], **kwargs: Any) -> ExecutionResult:
        calls.append(argv)
        if argv[1] == "--version":
            return _result(0, stdout="10.0.204\n")
        return _result(0)

    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "execute", fake)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var w = new Widget();")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["EXECUTED"]
    assert "SDK 10.0.204" in (receipts[0].detail or "")
    assert calls[-1][:2] == ["dotnet", "build"]
    # The wrapper references the product's own project and targets what this SDK builds.
    written = (tmp_path / "run" / "example_001" / "Example.csproj").read_text("utf-8")
    assert "net10.0" in written and "Aspose.Widget.csproj" in written
    assert (tmp_path / "run" / "example_001" / "Program.cs").read_text("utf-8").startswith("var w")


def test_a_compile_error_reports_the_compilers_own_first_diagnostic(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A named diagnostic is what a disposition can act on; "the build failed" is not."""

    def fake(argv: list[str], **kwargs: Any) -> ExecutionResult:
        if argv[1] == "--version":
            return _result(0, stdout="10.0.204\n")
        return _result(1, stdout="Program.cs(1,9): error CS0246: type 'Widget' not found\n")

    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "execute", fake)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var w = new Widget();")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["FAILED"]
    assert "CS0246" in (receipts[0].detail or "")


def test_a_build_that_never_returns_times_out_rather_than_failing(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(argv: list[str], **kwargs: Any) -> ExecutionResult:
        if argv[1] == "--version":
            return _result(0, stdout="10.0.204\n")
        return _result(1, timed_out=True)

    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "execute", fake)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "while(true);")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["TIMED_OUT"]


def test_no_candidates_means_no_toolchain_is_touched(tmp_path: Path) -> None:
    assert net_examples.verify_net_examples(tmp_path, None, [], tmp_path / "run") == []


def test_the_wrapper_targets_the_sdk_rather_than_the_packages_floor() -> None:
    """Measured 2026-09-06 on the .NET cohort, two ways.

    Aspose.3D declares its multi-target list only under Release, so a Debug build of the library
    produces `net10.0` alone and a `netcoreapp3.1` wrapper - the true declared floor - failed
    every example with NU1201. Cells and Words declare `netstandard2.0`, which no executable may
    target at all. A current framework consumes a library built for any lower one.
    """
    assert net_examples._sdk_framework("10.0.204") == "net10.0"
    assert net_examples._sdk_framework("8.0.404") == "net8.0"
    assert net_examples._sdk_framework("9.0.100-preview.3") == "net9.0"
    assert net_examples._sdk_framework("") == net_examples._FALLBACK_FRAMEWORK


def test_a_diagnostic_carries_no_path_from_this_machine(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt becomes a fact's evidence and a fact is published.

    Measured 2026-09-06 on Aspose.Slides for .NET, whose facts carried the developer's home
    directory: a path that differs per machine would also move a sealed candidate's bytes for a
    reason that is not the repository.
    """
    run = tmp_path / "run"
    noisy = (
        f"{run / 'example_001' / 'Program.cs'}(1,30): error CS0246: "
        f"'Presentation' not found [{run / 'example_001' / 'Example.csproj'}]"
    )

    def fake(argv: list[str], **kwargs: Any) -> ExecutionResult:
        if argv[1] == "--version":
            return _result(0, stdout="10.0.204\n")
        return _result(1, stdout=noisy + "\n")

    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "execute", fake)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var p = new Presentation();")], run
    )
    detail = receipts[0].detail or ""
    assert detail == "Program.cs(1,30): error CS0246: 'Presentation' not found"
    assert str(tmp_path) not in detail
    assert str(tmp_path) not in receipts[0].stdout and str(tmp_path) not in receipts[0].stderr


def test_a_workspace_windows_will_not_release_does_not_end_the_stage(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured 2026-09-06 on Aspose.Words for .NET: `rmtree` raised WinError 145 on a NuGet
    cache file inside the previous run's profile and took the whole facts stage down."""
    run = tmp_path / "run"
    run.mkdir()
    (run / "stuck.txt").write_text("held open", encoding="utf-8")
    monkeypatch.setattr(net_examples.shutil, "rmtree", lambda *a, **k: None)

    def fake(argv: list[str], **kwargs: Any) -> ExecutionResult:
        if argv[1] == "--version":
            return _result(0, stdout="10.0.204\n")
        return _result(0)

    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "execute", fake)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var w = 1;")], run
    )
    assert [r.outcome for r in receipts] == ["EXECUTED"]
    # The undeletable directory is untouched and the build ran beside it.
    assert (run / "stuck.txt").exists()
    assert (tmp_path / "run-1" / "example_001" / "Program.cs").exists()


def test_a_workspace_that_can_never_be_cleaned_is_blocked_not_crashed(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 29.6 E5: what we could not check is UNRESOLVED, never CONTRADICTED."""
    monkeypatch.setattr(net_examples, "dotnet_executable", lambda: "dotnet")
    monkeypatch.setattr(net_examples, "_fresh_workspace", lambda workspace: None)
    receipts = net_examples.verify_net_examples(
        tmp_path, project, [_candidate(1, "var w = 1;")], tmp_path / "run"
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in (receipts[0].detail or "")
