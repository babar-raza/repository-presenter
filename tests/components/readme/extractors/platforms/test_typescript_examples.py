"""`tsc --noEmit` proves the example's calls exist; the library's own build noise does not."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms import typescript_examples
from repository_presenter.core.examples import ExampleCandidate

MANIFEST = {
    "name": "@aspose/widget",
    "version": "1.0.0",
    "main": "dist/index.js",
    "types": "dist/index.d.ts",
}
TSCONFIG = {"compilerOptions": {"target": "ES2020", "rootDir": "./src", "outDir": "./dist"}}
BARREL = "export { Widget } from './Widget';\n"
# `require` is a Node global this package declares no types for, exactly as both cohort
# repositories do: a diagnostic the library raises about its own environment.
WIDGET = """
export class Widget {
  name: string = '';
  save(path: string): void {
    const fs = require('fs');
  }
}
"""
GOOD = "import { Widget } from './dist';\nconst w = new Widget();\nw.save('out.obj');\n"
BAD = "import { Widget } from './dist';\nconst w = new Widget();\nw.explode('out.obj');\n"
# What a README script does that the package's own `lib: ["ES2020"]` and missing `@types/node`
# do not declare: log, and read a file. Neither is a claim about the package.
HOSTED = (
    "import { Widget } from './dist';\n"
    "import { readFileSync } from 'fs';\n"
    "const w = new Widget();\n"
    "w.save('out.obj');\n"
    "console.log(readFileSync('out.obj'));\n"
)

compiler = typescript_examples.typescript_compiler()


def _refusal() -> str:
    """What this machine's tsc says about the verifier's own flags, or empty when it accepts them.

    The lane qualified tsc 5.9.3 (`evidence/build/lanes/lane-b/LANE-B-00.json`); the hosted runner
    carries 7.0.2, a different compiler this lane has not qualified, and it refuses these options.
    The verifier's answer there is `NOT_VERIFIED` for every candidate, which is what
    `test_a_compiler_this_lane_has_not_qualified_verifies_nothing` asserts - so the tests that need
    a compiler that *works* skip rather than pretend, and the honest behaviour is still asserted.
    """
    if compiler is None:
        return "no tsc on this machine"
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        return typescript_examples.probe_compiler(
            compiler, workspace, typescript_examples._flags(workspace)
        )


REFUSAL = _refusal()
needs_tsc = pytest.mark.skipif(bool(REFUSAL), reason=f"no usable tsc here: {REFUSAL}")


def _repository(root: Path) -> Path:
    (root / "package.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (root / "tsconfig.json").write_text(json.dumps(TSCONFIG), encoding="utf-8")
    source = root / "src"
    source.mkdir()
    (source / "index.ts").write_text(BARREL, encoding="utf-8")
    (source / "Widget.ts").write_text(WIDGET, encoding="utf-8")
    return source / "index.ts"


def test_a_diagnostic_in_the_library_is_not_a_diagnostic_in_the_example() -> None:
    """Measured 2026-09-06: 37 such diagnostics on Aspose.3D for TypeScript, none in an example.

    Every one is a Node global - `require`, `Buffer`, `NodeJS` - that the package's own sources
    use without declaring types for. Letting them decide the verdict would report every README
    example of both cohort repositories as false.
    """
    output = "\n".join(
        [
            "dist/aspose/threed/Scene.ts(125,24): error TS2580: Cannot find name 'require'.",
            "example_003.ts(3,7): error TS2339: Property 'explode' does not exist on 'Widget'.",
            "not a diagnostic at all",
        ]
    )
    mine, theirs = typescript_examples.split_diagnostics(output, "example_003.ts")
    assert len(mine) == 1 and "explode" in mine[0]
    assert len(theirs) == 1 and "require" in theirs[0]


def test_the_build_output_the_manifest_declares_is_staged_from_the_sources_it_maps_to(
    tmp_path: Path,
) -> None:
    """A README importing `./dist/...` resolves, because `tsconfig` says what builds `dist`."""
    root = tmp_path / "repository"
    root.mkdir()
    _repository(root)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    typescript_examples.stage_sources(root, workspace)
    assert (workspace / "src" / "index.ts").is_file()
    assert (workspace / "dist" / "index.ts").is_file()
    # The configuration file stays behind: its options are passed as flags, and its presence beside
    # a file named on the command line is `error TS5112` on TypeScript 7 (the hosted runner's).
    assert not (workspace / "tsconfig.json").exists()
    assert (workspace / typescript_examples._HOST_DECLARATIONS).is_file()


def test_no_candidate_needs_no_workspace(tmp_path: Path) -> None:
    assert typescript_examples.verify_typescript_examples(tmp_path, None, [], tmp_path, 60.0) == []


@pytest.mark.skipif(compiler is None, reason="no tsc at all on this machine")
def test_a_compiler_this_lane_has_not_qualified_verifies_nothing(tmp_path: Path) -> None:
    """Section 29.6 E5, proven on whichever tsc this machine has.

    The lane qualified 5.9.3; the hosted runner carries 7.0.2, which refuses these options and
    exits non-zero with no diagnostic naming a file - the shape that would read as a clean run to
    anything that only counts diagnostics. Whichever compiler is present, the outcome here is
    honest: `EXECUTED` when it checked and found nothing wrong, `NOT_VERIFIED` naming the refusal
    when it could not check at all. Never `EXECUTED` because a refusal was silent.
    """
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    candidate = ExampleCandidate(1, "typescript", GOOD, "README.md", 1, 4, "unit:001")
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    if REFUSAL:
        assert receipts[0].outcome == "NOT_VERIFIED"
        assert "BLOCKED_TOOLCHAIN" in receipts[0].detail
    else:
        assert receipts[0].outcome == "EXECUTED"


@needs_tsc
def test_a_compiler_that_refuses_without_naming_a_file_verifies_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Section 29.6 E5, the case that nearly passed silently.

    Measured 2026-09-06 on the hosted runner (tsc 7.0.2): a `tsconfig.json` beside the file named
    on the command line raises `error TS5112`, the run exits 1, and no diagnostic carries a file -
    so a rule that reads only filed diagnostics would have called every example, true or false, a
    pass. A compiler that refused checked nothing, and nothing checked is NOT_VERIFIED.
    """
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    workspace = tmp_path / "run"
    candidate = ExampleCandidate(1, "typescript", BAD, "README.md", 1, 4, "unit:001")
    original = typescript_examples.stage_sources

    def stage_with_config(source: Path, target: Path) -> None:
        original(source, target)
        (target / "tsconfig.json").write_text(json.dumps(TSCONFIG), encoding="utf-8")

    monkeypatch.setattr(typescript_examples, "stage_sources", stage_with_config)
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], workspace, 180.0
    )
    # tsc 5 checks the file anyway and reports the real error; tsc 7 refuses. Either verdict is
    # honest, and neither is the silent pass the missing branch would have produced.
    assert receipts[0].outcome in {"FAILED", "NOT_VERIFIED"}


@needs_tsc
def test_an_example_whose_calls_exist_type_checks(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    candidate = ExampleCandidate(1, "typescript", GOOD, "README.md", 1, 4, "unit:001")
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    assert [receipt.outcome for receipt in receipts] == ["EXECUTED"]
    # The receipt names the compiler that ran, because a check is only as reproducible as it is.
    # The version itself is not asserted: this machine has 5.9.3 and the hosted runner has 7.0.2.
    assert "--noEmit" in receipts[0].detail and "Version" in receipts[0].detail
    assert receipts[0].return_code == 0


@needs_tsc
def test_the_host_surface_a_readme_script_assumes_is_not_the_packages_claim(
    tmp_path: Path,
) -> None:
    """Measured 2026-09-06 on Aspose.3D for TypeScript: four of nine examples failed on this.

    Three raised `TS2584: Cannot find name 'console'` because the package declares
    `lib: ["ES2020"]` and nothing else, and one raised `TS2307: Cannot find module 'fs'` because
    `@types/node` is not installed in the check. Neither says anything about whether the
    example's calls into the package exist, which is the only claim the contract makes for it.
    """
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    candidate = ExampleCandidate(1, "typescript", HOSTED, "README.md", 1, 6, "unit:001")
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    assert [receipt.outcome for receipt in receipts] == ["EXECUTED"]


@needs_tsc
def test_an_example_calling_a_member_that_does_not_exist_fails(tmp_path: Path) -> None:
    """The negative control: the check has to be able to say no, and to say why."""
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    candidate = ExampleCandidate(1, "typescript", BAD, "README.md", 1, 4, "unit:001")
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    assert [receipt.outcome for receipt in receipts] == ["FAILED"]
    assert "explode" in receipts[0].detail


def _fake_npm(directory: Path, fail_run: bool = False) -> str:
    """A stand-in `npm` that records its arguments and exits 0 - or 3 on `npm run ...` when asked.

    The real one needs the network and a minute; what the verifier is tested on is what it does
    with an exit code. Written per platform because `execute` runs argv[0] directly: a `.cmd`
    where Windows resolves batch files, a `sh` script with its mode bit where the hosted runner
    (ubuntu) does not.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if fail_run:
        (directory / "fail_run").write_text("", encoding="utf-8")
    if os.name == "nt":
        path = directory / "npm.cmd"
        path.write_text(
            "@echo off\r\n"
            'echo %*>>"%~dp0npm.log"\r\n'
            'if "%1"=="run" if exist "%~dp0fail_run" exit /b 3\r\n'
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / "npm"
        path.write_text(
            "#!/bin/sh\n"
            'd=$(dirname "$0")\n'
            'echo "$@" >> "$d/npm.log"\n'
            'if [ "$1" = "run" ] && [ -f "$d/fail_run" ]; then exit 3; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(path)


def _npm_calls(npm: str) -> list[str]:
    log = Path(npm).parent / "npm.log"
    return [line.strip() for line in log.read_text("utf-8").splitlines()] if log.is_file() else []


def _building_repository(root: Path, build_script: bool) -> Path:
    barrel = _repository(root)
    manifest = {**MANIFEST, "scripts": {"build": "tsc"}} if build_script else MANIFEST
    (root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    return barrel


def test_the_manifests_own_build_is_driven_and_only_the_steps_it_proved_are_named(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 50 (lane B, RESEARCH_LANE_B 617-645). A type-checked example says
    nothing about whether the library builds - Aspose.Cells for TypeScript has 3 of 3 examples
    EXECUTED while its own sources do not compile - so the verifier drives the manifest's own
    build, in a copy, and the receipt names exactly the steps that exited 0, nothing more.
    Measured by the lane on Aspose.3D: `npm install` exit 0, then `npm run build` exit 0."""
    root = tmp_path / "repository"
    root.mkdir()
    _building_repository(root, build_script=True)
    npm = _fake_npm(tmp_path / "tools")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    product = typescript_examples.build_product(root, workspace, npm, 60.0)
    assert product.verified is True
    assert product.command == "npm install\nnpm run build"
    assert product.summary == "succeeded (`npm install` exited 0; `npm run build` exited 0)"
    assert _npm_calls(npm) == ["install", "run build"]
    # Driven in a copy that carries the manifest and its configuration; the read-only clone gains
    # nothing (no lockfile, no node_modules).
    assert sorted(path.name for path in root.iterdir()) == ["package.json", "src", "tsconfig.json"]
    copy = workspace / typescript_examples._PRODUCT_DIRECTORY
    assert (copy / "tsconfig.json").is_file() and (copy / "src" / "Widget.ts").is_file()
    # No wall-clock reaches a receipt: a duration cannot repeat between two runs of the same
    # revision, and a receipt that carried one withdrew a seal's no-op proof (net_examples.py).
    assert re.search(r"\d+(?:\.\d+)?\s*s\b", product.summary) is None


def test_a_manifest_with_no_build_script_proves_only_its_install(tmp_path: Path) -> None:
    """Aspose.Cells for TypeScript's shape: `npm install` exits 0 and there is nothing declared to
    build, so the honest command is the install alone and the receipt says nothing compiled."""
    root = tmp_path / "repository"
    root.mkdir()
    _building_repository(root, build_script=False)
    npm = _fake_npm(tmp_path / "tools")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    product = typescript_examples.build_product(root, workspace, npm, 60.0)
    assert product.verified is True
    assert product.command == "npm install"
    assert product.summary == (
        "succeeded (`npm install` exited 0; the manifest declares no build script, so nothing "
        "was compiled)"
    )
    assert _npm_calls(npm) == ["install"]


def test_a_build_step_that_fails_proves_nothing(tmp_path: Path) -> None:
    """The negative control: a failed step leaves no command to advertise and says which failed."""
    root = tmp_path / "repository"
    root.mkdir()
    _building_repository(root, build_script=True)
    npm = _fake_npm(tmp_path / "tools", fail_run=True)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    product = typescript_examples.build_product(root, workspace, npm, 60.0)
    assert product.verified is False
    assert product.command == ""
    assert product.summary == "failed (`npm run build` exited 3 after `npm install` exited 0)"


def test_without_npm_the_build_is_not_attempted(tmp_path: Path) -> None:
    """Section 29.6 E5: a toolchain this machine lacks proves nothing either way."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    product = typescript_examples.build_product(tmp_path, workspace, None, 60.0)
    assert product == typescript_examples.ProductBuild(
        False, "", "not attempted (no npm on this machine)"
    )


@needs_tsc
def test_a_receipt_carries_what_the_packages_own_build_proved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The type check and the product build are two facts on one receipt: `build_verified` and
    `build_command` say what the manifest's own build proved, the outcome what the snippet did."""
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _building_repository(root, build_script=True)
    candidate = ExampleCandidate(1, "typescript", GOOD, "README.md", 1, 4, "unit:001")
    npm = _fake_npm(tmp_path / "tools")
    monkeypatch.setattr(typescript_examples, "npm_executable", lambda: npm)
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    assert receipts[0].outcome == "EXECUTED"
    assert receipts[0].build_verified is True
    assert receipts[0].build_command == "npm install\nnpm run build"
    assert receipts[0].detail.endswith(
        "; the package's own npm build succeeded (`npm install` exited 0; `npm run build` exited 0)"
    )
    failing = _fake_npm(tmp_path / "tools-failing", fail_run=True)
    monkeypatch.setattr(typescript_examples, "npm_executable", lambda: failing)
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run-failing", 180.0
    )
    # The snippet still type-checks; the build it says nothing about is recorded as unproven.
    assert receipts[0].outcome == "EXECUTED"
    assert receipts[0].build_verified is False
    assert receipts[0].build_command == ""
    assert receipts[0].detail.endswith(
        "; the package's own npm build failed (`npm run build` exited 3 after `npm install` "
        "exited 0)"
    )


@needs_tsc
def test_no_absolute_path_of_this_machine_reaches_a_receipt(tmp_path: Path) -> None:
    """A receipt becomes a published fact's evidence; a developer's home must not appear in it."""
    root = tmp_path / "repository"
    root.mkdir()
    barrel = _repository(root)
    candidate = ExampleCandidate(1, "typescript", BAD, "README.md", 1, 4, "unit:001")
    receipts = typescript_examples.verify_typescript_examples(
        root, barrel, [candidate], tmp_path / "run", 180.0
    )
    for text in (receipts[0].stdout, receipts[0].stderr, receipts[0].detail):
        assert str(tmp_path) not in text and tmp_path.as_posix() not in text
