"""A JavaScript example is checked, not run: it parses, and what it imports from the package loads.

The checks use the Node this machine has (`core/toolchains.py`), because what is proven is what
Node itself says about the snippet; a machine without one is `NOT_VERIFIED` and the tests that
need it skip. The package's own `npm install` is a stand-in that records its arguments, since the
real one needs the network and is covered by what the verifier does with an exit code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.platforms import (
    nodejs,
    nodejs_examples,
)
from repository_presenter.components.readme.extractors.platforms.registry import verify_build
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt, MeasuredBuild
from repository_presenter.core.toolchains import resolve_tool
from support import fake_npm, npm_calls

needs_node = pytest.mark.skipif(resolve_tool("node") is None, reason="no node on this machine")

MANIFEST = {
    "name": "widget-js",
    "version": "0.1.0",
    "type": "module",
    "main": "src/index.js",
    "exports": {".": "./src/index.js"},
}
BARREL = 'export { Widget, makeWidget } from "./Widget.js";\n'
WIDGET = "export class Widget {\n  save(path) {}\n}\nexport function makeWidget() {}\n"


def _package(root: Path, manifest: dict[str, Any] | None = None) -> None:
    (root / "package.json").write_text(json.dumps(manifest or MANIFEST, indent=2), encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "index.js").write_text(BARREL, encoding="utf-8")
    (root / "src" / "Widget.js").write_text(WIDGET, encoding="utf-8")


def _candidate(code: str, ordinal: int = 1) -> ExampleCandidate:
    return ExampleCandidate(ordinal, "javascript", code, "README.md", 1, 5, f"unit:{ordinal:03d}")


def _verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    codes: list[str],
    *,
    manifest: dict[str, Any] | None = None,
    npm: str | None = "fake",
) -> tuple[list[ExampleReceipt], Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _package(repository, manifest)
    tools = fake_npm(tmp_path / "tools") if npm == "fake" else None
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: tools)
    candidates = [_candidate(code, index + 1) for index, code in enumerate(codes)]
    receipts = nodejs.PLUGIN.verify_examples(repository, [], candidates, tmp_path / "ws")
    return receipts, repository


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@needs_node
def test_an_example_whose_imports_load_is_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    [receipt], _ = _verify(
        tmp_path,
        monkeypatch,
        ['import { Widget, makeWidget } from "widget-js";\nconst w = new Widget();\n'],
    )
    assert receipt.outcome == "EXECUTED" and receipt.return_code == 0
    assert "syntax-checked with node v" in receipt.detail
    assert "2 import" not in receipt.detail and "1 import statement" in receipt.detail
    assert "not run" in receipt.detail
    # The package's own build was driven, and the receipt says which steps exited 0.
    assert receipt.build_verified is True and receipt.build_command == "npm install"
    assert "`npm install` exited 0" in receipt.detail


@needs_node
def test_a_named_import_the_package_does_not_export_is_a_failed_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Node's own linker refuses it, as it would refuse a consumer's program."""
    [receipt], _ = _verify(
        tmp_path, monkeypatch, ['import { Gadget } from "widget-js";\nnew Gadget();\n']
    )
    assert receipt.outcome == "FAILED"
    assert "does not provide an export named 'Gadget'" in receipt.detail


@needs_node
def test_a_snippet_that_does_not_parse_is_a_failed_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    [receipt], _ = _verify(
        tmp_path, monkeypatch, ['import { Widget } from "widget-js";\nconst = ;\n']
    )
    assert receipt.outcome == "FAILED"
    assert receipt.detail.startswith("SyntaxError")


@needs_node
def test_a_snippet_that_imports_nothing_from_the_package_proves_nothing_about_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fragment that leans on a variable an earlier snippet defined parses, and that is all.
    Negative control for the contract: it must not read as a verified example."""
    fragment = "const client = new JmapClient({ sessionUrl: 'x' });\nawait client.connect();\n"
    third_party = 'import express from "express";\nexpress();\n'
    receipts, _ = _verify(tmp_path, monkeypatch, [fragment, third_party])
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED", "NOT_VERIFIED"]
    assert all("imports nothing from the package" in receipt.detail for receipt in receipts)


@needs_node
def test_a_relative_import_into_the_checkout_is_the_package_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts, _ = _verify(
        tmp_path,
        monkeypatch,
        [
            'import { Widget } from "./src/index.js";\n',
            'import { Widget } from "./src/missing.js";\n',
        ],
    )
    assert [receipt.outcome for receipt in receipts] == ["EXECUTED", "NOT_VERIFIED"]


@needs_node
def test_a_subpath_the_exports_map_does_not_offer_is_a_failed_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts, _ = _verify(
        tmp_path,
        monkeypatch,
        ['import { Widget } from "widget-js/src/Widget.js";\n', 'import "widget-js";\n'],
    )
    assert receipts[0].outcome == "FAILED"
    assert "ERR_PACKAGE_PATH_NOT_EXPORTED" in receipts[0].detail
    assert receipts[1].outcome == "EXECUTED"


@needs_node
def test_a_package_whose_entry_is_build_output_not_in_the_clone_is_not_verified_not_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`main: dist/index.js` and no `dist/`: the snippet is not what is missing."""
    manifest = {"name": "widget-js", "main": "dist/index.js"}
    [receipt], _ = _verify(
        tmp_path, monkeypatch, ['import { Widget } from "widget-js";\n'], manifest=manifest
    )
    assert receipt.outcome == "NOT_VERIFIED"
    assert receipt.detail.startswith("BLOCKED_TOOLCHAIN")


@needs_node
def test_a_commonjs_snippet_is_checked_as_commonjs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = {"name": "widget-cjs", "main": "index.js"}
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    (repository / "index.js").write_text(
        "class Widget {}\nmodule.exports = { Widget };\n", encoding="utf-8"
    )
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: None)
    codes = [
        'const { Widget } = require("widget-cjs");\nconsole.log(new Widget());\n',
        'const widgetModule = require("widget-cjs");\n',
        'const { Gadget } = require("widget-cjs");\n',
        'const { Widget: Alias, ...rest } = require("widget-cjs");\n',
    ]
    candidates = [_candidate(code, index + 1) for index, code in enumerate(codes)]
    receipts = nodejs.PLUGIN.verify_examples(repository, [], candidates, tmp_path / "ws")
    assert [receipt.outcome for receipt in receipts] == [
        "EXECUTED",
        "EXECUTED",
        "FAILED",
        "EXECUTED",
    ]
    # Destructuring a CommonJS module yields `undefined` for a missing name; the check turns that
    # into the refusal an ES import would have had.
    assert "does not provide an export named Gadget" in receipts[2].detail


@needs_node
def test_a_scoped_package_resolves_by_its_published_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = {**MANIFEST, "name": "@aspose/widget-js"}
    [receipt], _ = _verify(
        tmp_path, monkeypatch, ['import { Widget } from "@aspose/widget-js";\n'], manifest=manifest
    )
    assert receipt.outcome == "EXECUTED"


@needs_node
def test_without_npm_the_examples_are_still_checked_and_the_build_is_said_unproven(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    [receipt], _ = _verify(
        tmp_path, monkeypatch, ['import { Widget } from "widget-js";\n'], npm=None
    )
    assert receipt.outcome == "EXECUTED"
    assert receipt.build_verified is False and receipt.build_command == ""
    assert "not attempted (no npm on this machine)" in receipt.detail


@needs_node
def test_a_build_script_that_fails_does_not_cost_the_example_its_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The snippet is checked against the sources either way; only `build_verified` moves, so a
    syntax-only path is never rendered as "verified against a build that succeeded"."""
    repository = tmp_path / "repository"
    repository.mkdir()
    _package(repository, {**MANIFEST, "scripts": {"build": "tsc"}})
    npm = fake_npm(tmp_path / "tools", fail_run=True)
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: npm)
    candidates = [_candidate('import { Widget } from "widget-js";\n')]
    [receipt] = nodejs.PLUGIN.verify_examples(repository, [], candidates, tmp_path / "ws")
    assert receipt.outcome == "EXECUTED"
    assert receipt.build_verified is False and receipt.build_command == ""
    assert "`npm run build` exited 3" in receipt.detail
    assert npm_calls(npm) == ["install", "run build"]


@needs_node
def test_the_clone_is_never_written_to_and_no_machine_path_reaches_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _package(repository)
    before = _tree_digest(repository)
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: fake_npm(tmp_path / "tools"))
    candidates = [
        _candidate('import { Gadget } from "widget-js";\n', 1),
        _candidate('import { Widget } from "widget-js";\n', 2),
    ]
    receipts = nodejs.PLUGIN.verify_examples(repository, [], candidates, tmp_path / "ws")
    assert _tree_digest(repository) == before
    for receipt in receipts:
        for text in (receipt.detail, receipt.stdout, receipt.stderr):
            assert str(tmp_path) not in text and tmp_path.as_posix() not in text


def test_a_machine_without_node_is_not_verified_never_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 29.6 E5: 'we could not check' is not 'we checked and it is false'."""
    monkeypatch.setattr(nodejs_examples, "resolve_tool", lambda name: None)
    receipts, _ = _verify(
        tmp_path, monkeypatch, ['import { Widget } from "widget-js";\n', "const x = ;\n"]
    )
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED", "NOT_VERIFIED"]
    assert all("BLOCKED_TOOLCHAIN: no node" in receipt.detail for receipt in receipts)


def test_a_repository_with_no_entry_point_has_nothing_to_resolve_against(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "package.json").write_text('{"name": "widget"}', encoding="utf-8")
    candidates = [_candidate('import x from "widget";\n')]
    [receipt] = nodejs.PLUGIN.verify_examples(repository, [], candidates, tmp_path / "ws")
    assert receipt.outcome == "NOT_VERIFIED"
    assert "no package entry point" in receipt.detail


def test_no_candidates_means_no_work(tmp_path: Path) -> None:
    assert nodejs.PLUGIN.verify_examples(tmp_path, [], [], tmp_path / "ws") == []


def test_the_cli_measures_the_packages_own_build_through_the_plugin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`run_present` reaches the build through `registry.verify_build`, which only a plugin that
    provides the capability answers - with no README example anywhere in the repository, which is
    the case a registry 404 on a repository whose snippet fails would otherwise leave unproven."""
    repository = tmp_path / "repository"
    repository.mkdir()
    _package(repository, {**MANIFEST, "scripts": {"build": "rollup -c"}})
    npm = fake_npm(tmp_path / "tools")
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: npm)
    manifest = nodejs.PLUGIN.detect_manifest(repository)
    assert manifest is not None
    measured = verify_build(nodejs.PLUGIN, repository, manifest, tmp_path / "ws")
    assert measured == MeasuredBuild(
        True,
        "npm install\nnpm run build",
        "succeeded (`npm install` exited 0; `npm run build` exited 0)",
    )


def test_a_package_without_a_build_script_is_measured_by_its_install_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _package(repository)
    npm = fake_npm(tmp_path / "tools")
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: npm)
    manifest = nodejs.PLUGIN.detect_manifest(repository)
    assert manifest is not None
    measured = verify_build(nodejs.PLUGIN, repository, manifest, tmp_path / "ws")
    assert measured.verified and measured.command == "npm install"
    assert "declares no build script" in measured.summary
    # Negative control: no npm means nothing was measured, and no command may be advertised.
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: None)
    unmeasured = verify_build(nodejs.PLUGIN, repository, manifest, tmp_path / "ws2")
    assert unmeasured == MeasuredBuild(False, "", "not attempted (no npm on this machine)")
