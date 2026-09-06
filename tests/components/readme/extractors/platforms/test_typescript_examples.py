"""`tsc --noEmit` proves the example's calls exist; the library's own build noise does not."""

from __future__ import annotations

import json
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
needs_tsc = pytest.mark.skipif(compiler is None, reason="no tsc on this machine")


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


def test_no_candidate_needs_no_workspace(tmp_path: Path) -> None:
    assert typescript_examples.verify_typescript_examples(tmp_path, None, [], tmp_path, 60.0) == []


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
    assert "--noEmit" in receipts[0].detail and "5." in receipts[0].detail
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
