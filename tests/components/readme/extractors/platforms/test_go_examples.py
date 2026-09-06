"""The Go verifier completes a snippet into a program, and is honest when it cannot."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms import go_examples
from repository_presenter.core.examples import ExampleCandidate
from repository_presenter.core.execution import ExecutionResult

MODULE = "github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go/v26"
IMPORT_PATH = f"{MODULE}/aspose/widget_foss"
TIMEOUT = 300.0


def _candidate(ordinal: int, code: str) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal, "go", code, "README.md", 1, 3, f"inherited_unit:{ordinal:03d}.code_block"
    )


def _result(code: int, stdout: str = "", stderr: str = "", timed_out: bool = False):
    return ExecutionResult(
        argv=("go",),
        return_code=code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        environment_names=(),
    )


@pytest.fixture
def module(tmp_path: Path) -> Path:
    directory = tmp_path / "clone"
    directory.mkdir()
    (directory / "go.mod").write_text(f"module {MODULE}\n\ngo 1.24\n", encoding="utf-8")
    return directory


def test_a_machine_without_the_toolchain_reports_not_verified(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§29.6 E5: BLOCKED_TOOLCHAIN is UNRESOLVED downstream, never CONTRADICTED."""
    monkeypatch.setattr(go_examples, "go_executable", lambda: None)
    receipts = go_examples.verify_go_examples(
        module, MODULE, IMPORT_PATH, "1.24", [_candidate(1, "x := 1")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in (receipts[0].detail or "")


def test_a_repository_with_no_module_has_nothing_to_build_against(tmp_path: Path) -> None:
    receipts = go_examples.verify_go_examples(
        tmp_path, "", "", "", [_candidate(1, "x := 1")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "no module file" in (receipts[0].detail or "")


def test_no_candidates_means_no_toolchain_is_touched(tmp_path: Path, module: Path) -> None:
    assert (
        go_examples.verify_go_examples(module, MODULE, IMPORT_PATH, "1.24", [], tmp_path, TIMEOUT)
        == []
    )


def test_a_requirement_matches_the_module_paths_own_major_version() -> None:
    """Go refuses `require …/v26 v0.0.0` outright: "should be v26, not v0"."""
    assert go_examples.require_version(MODULE) == "v26.0.0"
    assert go_examples.require_version("github.com/aspose-pdf-foss/aspose-pdf-foss-for-go") == (
        "v0.0.0"
    )
    assert go_examples.require_version("example.com/mod/v2") == "v2.0.0"


def test_the_wrapper_module_resolves_the_product_from_the_clone(module: Path) -> None:
    rendered = go_examples.wrapper_module(MODULE, module, "1.24.5")
    assert f"require {MODULE} v26.0.0" in rendered
    assert f"replace {MODULE} => {module.resolve().as_posix()}" in rendered
    assert "go 1.24.5" in rendered
    # A module file that declares no language version still has to parse.
    assert "go 1.21" in go_examples.wrapper_module(MODULE, module, "")


def test_a_whole_file_is_compiled_exactly_as_written() -> None:
    code = 'package main\n\nimport "fmt"\n\nfunc main() { fmt.Println("x") }\n'
    assert go_examples.completed_source(code) == code
    # Never an import block: a whole file declares its own, and completing them would hide the
    # defect the verification exists to find.
    assert go_examples.completed_source(code, ['"os"']) == code


def test_a_run_of_declarations_gets_a_package_clause_and_loose_statements_get_a_main() -> None:
    declarations = go_examples.completed_source("func main() {\n\tw := widget.New()\n}\n")
    assert declarations.startswith("package main\n\nfunc main()")
    statements = go_examples.completed_source('w := widget.New()\nw.Save("a.pdf")\n')
    assert statements.startswith("package main\n\nfunc main() {\n\tw := widget.New()")
    assert statements.rstrip().endswith("}")


def test_an_unindented_declaration_inside_a_body_is_not_a_top_level_declaration() -> None:
    """Measured on Aspose.PDF for Go: `var buf bytes.Buffer` at column 0, mid-snippet."""
    code = "doc := pdf.New()\nvar buf bytes.Buffer\ndoc.Write(&buf)\n"
    completed = go_examples.completed_source(code)
    assert completed.startswith("package main\n\nfunc main() {\n\tdoc := pdf.New()")


def test_an_import_only_fence_has_nothing_to_compile() -> None:
    """Wrapping it is a syntax error and declaring it is an unused import; neither is a defect."""
    assert go_examples.declares_only_imports('import widget "example.com/widget"\n')
    assert go_examples.declares_only_imports('import (\n\t"fmt"\n\t"os"\n)\n')
    assert not go_examples.declares_only_imports('import "fmt"\n\nfunc main() {}\n')
    assert not go_examples.declares_only_imports("w := widget.New()\n")


def test_an_import_only_candidate_is_not_verified(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_examples, "go_executable", lambda: "go")
    monkeypatch.setattr(
        go_examples, "execute", lambda *a, **k: _result(0, stdout="go version go1.26.4 windows")
    )
    receipts = go_examples.verify_go_examples(
        module,
        MODULE,
        IMPORT_PATH,
        "1.24",
        [_candidate(1, f'import widget_foss "{IMPORT_PATH}"\n')],
        tmp_path / "run",
        TIMEOUT,
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "nothing to compile" in (receipts[0].detail or "")


def test_the_compiler_names_the_missing_imports_and_the_product_is_the_odd_one_out() -> None:
    diagnostics = "./main.go:4:8: undefined: widget_foss\n./main.go:7:2: undefined: fmt\n"
    code = "w := widget_foss.New()\nfmt.Println(w)\n"
    imports, unknown = go_examples.resolve_imports(diagnostics, IMPORT_PATH, code)
    assert imports == ['"fmt"', f'widget_foss "{IMPORT_PATH}"']
    assert unknown == []


def test_a_name_that_is_not_a_qualifier_is_never_given_an_import() -> None:
    """A helper the README never defines is a real defect, not a missing import."""
    diagnostics = "./main.go:16:31: undefined: generateSmallPNG\n"
    imports, unknown = go_examples.resolve_imports(
        diagnostics, IMPORT_PATH, "w.Add(generateSmallPNG())\n"
    )
    assert imports == [] and unknown == []


def test_two_unresolved_qualifiers_leave_the_example_unverified() -> None:
    """Aspose.PDF's signing example aliases `crypto/rand`; a guess would be a fabrication."""
    diagnostics = "undefined: ecdsa\nundefined: cryptorand\n"
    code = "k, _ := ecdsa.GenerateKey(cryptorand.Reader)\n"
    imports, unknown = go_examples.resolve_imports(diagnostics, IMPORT_PATH, code)
    assert unknown == ["cryptorand", "ecdsa"]
    assert imports == []


def test_a_build_that_never_returns_times_out_rather_than_failing(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_examples, "go_executable", lambda: "go")
    calls = {"n": 0}

    def fake(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _result(0, stdout="go version go1.26.4 windows/amd64")
        return _result(124, timed_out=True)

    monkeypatch.setattr(go_examples, "execute", fake)
    receipts = go_examples.verify_go_examples(
        module, MODULE, IMPORT_PATH, "1.24", [_candidate(1, "x := 1")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["TIMED_OUT"]


def test_a_diagnostic_carries_no_path_from_this_machine(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt becomes published evidence; the developer's home must not appear in it."""
    monkeypatch.setattr(go_examples, "go_executable", lambda: "go")
    run = (tmp_path / "run").absolute()
    calls = {"n": 0}

    def fake(argv, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _result(0, stdout="go version go1.26.4 windows/amd64")
        return _result(1, stderr=f"{run.as_posix()}/example_001/main.go:3:1: undefined: Widget\n")

    monkeypatch.setattr(go_examples, "execute", fake)
    receipts = go_examples.verify_go_examples(
        module,
        MODULE,
        IMPORT_PATH,
        "1.24",
        [_candidate(1, "w := Widget{}")],
        run,
        TIMEOUT,
    )
    assert receipts[0].outcome == "FAILED"
    assert str(run) not in (receipts[0].stderr or "")
    assert run.as_posix() not in (receipts[0].detail or "")
    assert "undefined: Widget" in (receipts[0].detail or "")


def test_a_workspace_that_can_never_be_cleaned_is_blocked_not_crashed(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_examples, "go_executable", lambda: "go")
    monkeypatch.setattr(go_examples, "_fresh_workspace", lambda _: None)
    receipts = go_examples.verify_go_examples(
        module, MODULE, IMPORT_PATH, "1.24", [_candidate(1, "x := 1")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "no clean workspace" in (receipts[0].detail or "")


def test_a_toolchain_that_reports_no_version_is_blocked(
    tmp_path: Path, module: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_examples, "go_executable", lambda: "go")
    monkeypatch.setattr(go_examples, "execute", lambda *a, **k: _result(1, stderr="broken"))
    receipts = go_examples.verify_go_examples(
        module, MODULE, IMPORT_PATH, "1.24", [_candidate(1, "x := 1")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "did not report a version" in (receipts[0].detail or "")
