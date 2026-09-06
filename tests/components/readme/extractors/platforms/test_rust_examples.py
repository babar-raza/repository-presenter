"""The Rust verifier completes a fence into a Cargo example, and is honest when it cannot."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms import rust_examples
from repository_presenter.core.examples import ExampleCandidate
from repository_presenter.core.execution import ExecutionResult

CRATE = "aspose-widget-foss-rust"
LIB = "aspose_widget_foss_rust"
TIMEOUT = 300.0


def _candidate(ordinal: int, code: str) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal, "rust", code, "README.md", 1, 3, f"inherited_unit:{ordinal:03d}.code_block"
    )


def _result(code: int, stdout: str = "", stderr: str = "", timed_out: bool = False):
    return ExecutionResult(
        argv=("cargo",),
        return_code=code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        environment_names=(),
    )


@pytest.fixture
def crate(tmp_path: Path) -> Path:
    directory = tmp_path / "clone"
    (directory / "src").mkdir(parents=True)
    (directory / "Cargo.toml").write_text(
        f'[package]\nname = "{CRATE}"\nversion = "1.0.0"\nedition = "2021"\n', encoding="utf-8"
    )
    (directory / "src" / "lib.rs").write_text("pub struct Widget;\n", encoding="utf-8")
    return directory


def test_a_machine_without_the_toolchain_reports_not_verified(
    tmp_path: Path, crate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§29.6 E5: BLOCKED_TOOLCHAIN is UNRESOLVED downstream, never CONTRADICTED."""
    monkeypatch.setattr(rust_examples, "cargo_executable", lambda: None)
    receipts = rust_examples.verify_rust_examples(
        crate, CRATE, LIB, [_candidate(1, "let w = 1;")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in (receipts[0].detail or "")


def test_a_repository_with_no_crate_has_nothing_to_check_against(tmp_path: Path) -> None:
    receipts = rust_examples.verify_rust_examples(
        tmp_path, "", "", [_candidate(1, "let w = 1;")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "no Cargo.toml" in (receipts[0].detail or "")


def test_no_candidates_means_no_toolchain_is_touched(tmp_path: Path, crate: Path) -> None:
    assert rust_examples.verify_rust_examples(crate, CRATE, LIB, [], tmp_path, TIMEOUT) == []


def test_a_whole_program_is_left_exactly_as_the_readme_wrote_it() -> None:
    """Completing a program's own imports would hide the defect the check exists to find."""
    program = "use aspose_widget_foss_rust::Widget;\n\nfn main() {\n    let w = Widget;\n}\n"
    assert rust_examples.completed_source(program, LIB) == program


def test_a_run_of_statements_is_wrapped_in_a_main_that_returns_result() -> None:
    """A README snippet uses `?` freely; a `main` returning unit would fail on the wrapper."""
    completed = rust_examples.completed_source("let w = Workbook::new()?;", LIB)
    assert f"use {LIB}::*;" in completed
    assert "fn main() -> Result<(), Box<dyn Error>> {" in completed
    assert "    let w = Workbook::new()?;" in completed
    assert completed.rstrip().endswith("Ok(())\n}")


def test_a_crate_with_no_library_name_still_wraps_the_snippet() -> None:
    completed = rust_examples.completed_source("let w = 1;", "")
    assert "use ::*;" not in completed
    assert "fn main()" in completed


def test_only_an_unbound_value_makes_a_fence_an_excerpt_rather_than_a_falsehood() -> None:
    """Measured 2026-09-06: six of seven Cells for Rust fences open on `sheet` or `workbook`."""
    excerpt = (
        "error[E0425]: cannot find value `sheet` in this scope\n"
        "  --> examples/rp_example_007.rs:6:22\n"
        "error[E0425]: cannot find value `workbook` in this scope\n"
    )
    assert rust_examples.unbound_values(excerpt) == ["sheet", "workbook"]


def test_cargos_closing_summary_is_not_counted_as_a_second_error() -> None:
    """Cargo restates the failure after the diagnostics; counting it condemned every excerpt."""
    reported = (
        "error[E0425]: cannot find value `valid_path` in this scope\n"
        "  --> examples\\rp_example_006.rs:12:52\n"
        "For more information about this error, try `rustc --explain E0425`.\n"
        'error: could not compile `aspose-cells-foss-rust` (example "rp_example_006") '
        "due to 1 previous error\n"
    )
    assert rust_examples.unbound_values(reported) == ["valid_path"]


def test_a_fence_that_names_a_type_the_crate_lacks_is_not_an_excerpt() -> None:
    """A path the crate does not export is a real defect, and must not be excused as context."""
    mixed = (
        "error[E0425]: cannot find value `sheet` in this scope\n"
        "error[E0412]: cannot find type `Missing` in this scope\n"
    )
    assert rust_examples.unbound_values(mixed) == []
    assert rust_examples.unbound_values("error: could not compile `x`\n") == []


def test_an_excerpt_is_not_verified_and_a_real_error_fails(crate: Path) -> None:
    excerpt = _result(101, stderr="error[E0425]: cannot find value `sheet` in this scope\n")
    outcome, detail = rust_examples._outcome(excerpt, excerpt.stderr, CRATE, "1.98.1", TIMEOUT)
    assert outcome == "NOT_VERIFIED"
    assert "`sheet`" in detail and "without binding it" in detail
    broken = _result(101, stderr="error[E0599]: no method named `save_it` found\n")
    outcome, detail = rust_examples._outcome(broken, broken.stderr, CRATE, "1.98.1", TIMEOUT)
    assert outcome == "FAILED"
    assert "E0599" in detail


def test_a_check_that_passes_records_the_crate_and_the_toolchain_it_ran(crate: Path) -> None:
    """§29.6 E5: a check is only as reproducible as the toolchain that ran it."""
    outcome, detail = rust_examples._outcome(_result(0), "", CRATE, "1.98.1", TIMEOUT)
    assert outcome == "EXECUTED"
    # BC-10 reads ": COMPILED" as the proof the example was exercised, not merely parsed.
    assert ": COMPILED" in f": {detail}" or detail.startswith("COMPILED")
    assert CRATE in detail and "cargo 1.98.1" in detail


def test_a_check_that_never_returns_is_timed_out_not_failed() -> None:
    outcome, detail = rust_examples._outcome(
        _result(None, timed_out=True), "", CRATE, "1.98.1", TIMEOUT
    )
    assert outcome == "TIMED_OUT"
    assert "300s" in detail


def test_the_toolchain_registry_resolves_a_tool_that_is_not_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """loop-prompt §1.3: nothing this lane needs is on PATH."""
    recorded = tmp_path / "cargo.exe"
    recorded.write_text("", encoding="utf-8")
    registry = tmp_path / "TOOLCHAIN_PATHS.txt"
    registry.write_text(f"cargo={recorded}\nrustup_home={tmp_path}\n", encoding="utf-8")
    monkeypatch.setenv(rust_examples._REGISTRY_VARIABLE, str(registry))
    monkeypatch.setattr(rust_examples.shutil, "which", lambda name: None)
    assert rust_examples.cargo_executable() == str(recorded)
    assert rust_examples.recorded_tool("nothing-recorded") is None


def test_the_rustup_home_is_named_explicitly_because_the_profile_moves_the_real_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The disposable profile points USERPROFILE at an empty directory, and the proxy reads it."""
    registry = tmp_path / "TOOLCHAIN_PATHS.txt"
    home = tmp_path / "rustup-home"
    home.mkdir()
    registry.write_text(f"rustup_home={home}\n", encoding="utf-8")
    monkeypatch.setenv(rust_examples._REGISTRY_VARIABLE, str(registry))
    monkeypatch.delenv(rust_examples._RUSTUP_HOME, raising=False)
    assert rust_examples.rustup_home("C:/nowhere/cargo.exe") == str(home)
    monkeypatch.setenv(rust_examples._RUSTUP_HOME, "C:/ambient")
    assert rust_examples.rustup_home("C:/nowhere/cargo.exe") == "C:/ambient"


def test_a_crate_that_does_not_check_condemns_no_example(
    tmp_path: Path, crate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An example checked against a library that will not build reports the library's defect."""
    monkeypatch.setattr(rust_examples, "cargo_executable", lambda: "cargo")
    monkeypatch.setattr(rust_examples, "rustup_home", lambda cargo: None)
    calls: list[list[str]] = []

    def fake_execute(argv, *, workspace, timeout_seconds, extra_environment=None, **kwargs):
        calls.append(list(argv))
        if argv[1] == "--version":
            return _result(0, stdout="cargo 1.98.1 (797e8a9bc 2026-08-05)\n")
        return _result(101, stderr="error[E0432]: unresolved import `serde`\n")

    monkeypatch.setattr(rust_examples, "execute", fake_execute)
    receipts = rust_examples.verify_rust_examples(
        crate, CRATE, LIB, [_candidate(1, "let w = 1;")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED"]
    assert "the crate does not check at this revision" in (receipts[0].detail or "")
    # The example target was never even written: the crate's own check is the gate.
    assert not any("--example" in call for call in calls)


def test_every_example_is_checked_against_the_lock_the_crate_check_resolved(
    tmp_path: Path, crate: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fence must not silently resolve a different dependency set than the crate itself."""
    monkeypatch.setattr(rust_examples, "cargo_executable", lambda: "cargo")
    monkeypatch.setattr(rust_examples, "rustup_home", lambda cargo: None)
    calls: list[list[str]] = []

    def fake_execute(argv, *, workspace, timeout_seconds, extra_environment=None, **kwargs):
        calls.append(list(argv))
        if argv[1] == "--version":
            return _result(0, stdout="cargo 1.98.1 (797e8a9bc 2026-08-05)\n")
        return _result(0)

    monkeypatch.setattr(rust_examples, "execute", fake_execute)
    receipts = rust_examples.verify_rust_examples(
        crate, CRATE, LIB, [_candidate(1, "let w = 1;")], tmp_path / "run", TIMEOUT
    )
    assert [r.outcome for r in receipts] == ["EXECUTED"]
    example = [call for call in calls if "--example" in call]
    assert example and example[0][-1] == "rp_example_001"
    assert "--locked" in example[0]
    # The crate ships no lock file, so its own check may resolve one; the fences may not.
    crate_check = [call for call in calls if call[1] == "check" and "--example" not in call]
    assert crate_check and "--locked" not in crate_check[0]


def test_the_machines_own_paths_never_reach_a_receipt(tmp_path: Path) -> None:
    """A receipt becomes a published fact's evidence; a home directory must not appear in it."""
    noisy = f"error: could not read {tmp_path.as_posix()}/crate/src/lib.rs"
    assert str(tmp_path) not in rust_examples._scrub(noisy, tmp_path)
    assert tmp_path.as_posix() not in rust_examples._scrub(noisy, tmp_path)
