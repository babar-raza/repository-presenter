"""What an npm package's entry point publishes, for both source dialects that share the reading."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.surface import npm_package
from repository_presenter.components.readme.extractors.surface.npm_package import (
    JAVASCRIPT_MODULES,
    TYPESCRIPT_MODULES,
)


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _bindings(barrel: Path, dialect: npm_package.ModuleDialect) -> dict[str, set[str] | None]:
    base = barrel.resolve().parent
    return {
        name: None if modules is None else {m.relative_to(base).as_posix() for m in modules}
        for name, modules in npm_package.reexported_bindings(barrel.resolve(), dialect).items()
    }


def test_read_json_survives_comments_and_trailing_commas(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{\n  // a line comment\n  "compilerOptions": {"outDir": "dist", /* inline */},\n}\n',
        encoding="utf-8",
    )
    assert npm_package.read_json(tmp_path / "tsconfig.json") == {
        "compilerOptions": {"outDir": "dist"}
    }
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    assert npm_package.read_json(tmp_path / "broken.json") == {}
    assert npm_package.read_json(tmp_path / "absent.json") == {}


def test_a_javascript_specifier_naming_a_real_file_is_that_file(tmp_path: Path) -> None:
    """ESM JavaScript writes the extension (`./models/Mailbox.js`), and it names a real file;
    TypeScript's ESM writes `.js` for a `.ts` source, so there the extension is searched for."""
    _write(
        tmp_path,
        {
            "index.js": (
                'export { Mailbox } from "./models/Mailbox.js";\n'
                'export * from "./errors/index.js";\n'
                'export { Thread } from "./models/Thread";\n'
                'export * from "./util";\n'
            ),
            "models/Mailbox.js": "export class Mailbox {}\n",
            "models/Thread.js": "export class Thread {}\n",
            "errors/index.js": "export class JmapError {}\nexport function fail() {}\n",
            "util/index.mjs": "export const helper = 1;\n",
        },
    )
    found = _bindings(tmp_path / "index.js", JAVASCRIPT_MODULES)
    assert found["Mailbox"] == {"models/Mailbox.js"}
    assert found["Thread"] == {"models/Thread.js"}
    assert found["JmapError"] == {"errors/index.js"}
    assert found["fail"] == {"errors/index.js"}
    assert found["helper"] == {"util/index.mjs"}


def test_a_typescript_js_specifier_is_searched_as_its_ts_source(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "index.ts": 'export { Widget } from "./Widget.js";\n',
            "Widget.ts": "export class Widget {}\n",
            # Negative control: a built file beside the source is not what the barrel binds.
            "Widget.js": "export class Widget {}\n",
        },
    )
    assert _bindings(tmp_path / "index.ts", TYPESCRIPT_MODULES) == {"Widget": {"Widget.ts"}}


def test_a_local_export_binds_a_name_with_no_module_to_check(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "index.js": (
                'import { JmapClient as CoreClient } from "./client-core.js";\n'
                "class JmapClient extends CoreClient {}\n"
                "export { JmapClient };\n"
                "export default JmapClient;\n"
            ),
            "client-core.js": "export class JmapClient {}\n",
        },
    )
    assert _bindings(tmp_path / "index.js", JAVASCRIPT_MODULES)["JmapClient"] is None


def test_commonjs_assignments_are_exports_in_the_javascript_dialect(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "index.js": (
                "const Plain = require('./plain');\n"
                "module.exports = {\n"
                "  Plain,\n"
                "  Renamed: require('./renamed').Thing,\n"
                "  Bound: require('./bound'),\n"
                "  ...require('./rest'),\n"
                "};\n"
                "module.exports.Late = function Late() {};\n"
                "exports.Early = require('./early');\n"
            ),
            "plain.js": "class Plain {}\nmodule.exports = Plain;\n",
            "renamed.js": "exports.Thing = class Thing {};\n",
            "bound.js": "class Bound {}\nmodule.exports = Bound;\n",
            "early.js": "module.exports = class Early {};\n",
            "rest.js": "exports.FromRest = 1;\nmodule.exports.AlsoRest = 2;\n",
        },
    )
    found = _bindings(tmp_path / "index.js", JAVASCRIPT_MODULES)
    assert found["Plain"] is None  # a shorthand member names the file's own declaration
    assert found["Renamed"] is None  # `.Thing` is a property read, not a module binding
    assert found["Bound"] == {"bound.js"}
    assert found["Late"] is None
    assert found["Early"] == {"early.js"}
    # The spread re-exports another module's own assignments.
    assert {"FromRest", "AlsoRest"} <= set(found)
    # Negative control: a name nothing assigns is not an export.
    assert "Hidden" not in found


def test_commonjs_is_not_read_in_the_typescript_dialect(tmp_path: Path) -> None:
    """`export =` and `module.exports` are not how a TypeScript entry point is read."""
    _write(tmp_path, {"index.ts": "module.exports = { Widget };\nexports.Other = 1;\n"})
    assert _bindings(tmp_path / "index.ts", TYPESCRIPT_MODULES) == {}


def test_a_single_assigned_name_and_a_whole_module_reexport(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "index.js": "module.exports = require('./lib/main');\n",
            "lib/main.js": "class Engine {}\nmodule.exports = Engine;\n",
        },
    )
    assert _bindings(tmp_path / "index.js", JAVASCRIPT_MODULES) == {"Engine": None}


def test_a_reexport_cycle_terminates(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "a.js": 'export * from "./b.js";\nexport class A {}\n',
            "b.js": 'export * from "./a.js";\nexport class B {}\n',
        },
    )
    assert set(_bindings(tmp_path / "a.js", JAVASCRIPT_MODULES)) == {"A", "B"}


def test_the_entry_point_is_the_manifests_main_when_it_re_exports(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget", "main": "src/index.js"}),
            "src/index.js": 'export { Widget } from "./Widget.js";\n',
            "src/Widget.js": "export class Widget {}\n",
            "index.js": 'export { Other } from "./src/Widget.js";\n',
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "src/index.js"


def test_an_exports_map_names_the_entry_point(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps(
                {"name": "widget", "exports": {".": {"import": "./esm/index.mjs"}}}
            ),
            "esm/index.mjs": 'export * from "./Widget.mjs";\n',
            "esm/Widget.mjs": "export class Widget {}\n",
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "esm/index.mjs"


def test_build_output_is_mapped_back_to_source_through_jsconfig(tmp_path: Path) -> None:
    """A declared `dist/index.js` that no clone contains is built from `src/index.js`."""
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget", "main": "dist/index.js"}),
            "jsconfig.json": json.dumps({"compilerOptions": {"rootDir": "src", "outDir": "dist"}}),
            "src/index.js": 'export { Widget } from "./Widget.js";\n',
            "src/Widget.js": "export class Widget {}\n",
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "src/index.js"


def test_a_demo_script_is_not_the_entry_point_but_the_barrel_beside_it_is(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget", "main": "demo.js"}),
            "demo.js": 'import { Widget } from "./pkg/index.js";\nconsole.log(new Widget());\n',
            "pkg/index.js": 'export { Widget } from "./Widget.js";\n',
            "pkg/Widget.js": "export class Widget {}\n",
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "pkg/index.js"


def test_a_commonjs_barrel_counts_as_re_exporting(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget", "main": "index.js"}),
            "index.js": "module.exports = { ...require('./widget') };\n",
            "widget.js": "exports.Widget = class Widget {};\n",
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "index.js"


def test_no_declared_entry_falls_back_to_the_shallowest_barrel_outside_noise(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget"}),
            "node_modules/dep/index.js": 'export * from "./x.js";\n',
            "examples/index.js": 'export * from "./x.js";\n',
            "src/index.js": 'export * from "./Widget.js";\n',
            "src/Widget.js": "export class Widget {}\n",
        },
    )
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) == tmp_path / "src/index.js"


def test_a_package_with_no_entry_point_has_none(tmp_path: Path) -> None:
    _write(tmp_path, {"package.json": json.dumps({"name": "widget"}), "loose.js": "export {};\n"})
    assert npm_package.entry_barrel(tmp_path, JAVASCRIPT_MODULES) is None


def test_a_dependency_copy_never_governs_the_package(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"name": "widget"}),
            "node_modules/left-pad/package.json": json.dumps({"name": "left-pad"}),
            "dist/package.json": json.dumps({"name": "widget-dist"}),
        },
    )
    assert npm_package.detect_manifest(tmp_path, ("package.json",), ()) == (
        tmp_path / "package.json"
    )
    # Negative control: with the repository's own manifest gone, only copies remain, and a
    # dependency's manifest must not name the package for us.
    (tmp_path / "package.json").unlink()
    assert npm_package.detect_manifest(tmp_path, ("package.json",), ()) is None


def test_a_named_manifest_outranks_an_unnamed_shallower_one(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "package.json": json.dumps({"private": True}),
            "packages/widget/package.json": json.dumps({"name": "widget"}),
        },
    )
    assert npm_package.detect_manifest(tmp_path, ("package.json",), ()) == (
        tmp_path / "packages/widget/package.json"
    )


def test_manifest_facts_are_the_same_for_both_ecosystems(tmp_path: Path) -> None:
    manifest = {
        "name": "@aspose/widget",
        "version": "1.2.3",
        "engines": {"node": ">=18"},
        "dependencies": {"left-pad": "^1.0.0"},
        "peerDependencies": {"react": ">=17"},
        "optionalDependencies": {"fsevents": "^2"},
        "devDependencies": {"jest": "^29"},
    }
    (tmp_path / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    for ecosystem in ("typescript", "nodejs"):
        facts = {
            fact.id: fact
            for fact in npm_package.manifest_facts(ecosystem, tmp_path, tmp_path / "package.json")
        }
        assert facts["package:name"].value == "@aspose/widget"
        assert facts["package:version"].value == "1.2.3"
        assert facts["package:node_engine"].value == ">=18"
        assert facts["install_command:npm"].polarity == "UNRESOLVED"
        assert facts["dependency:left-pad"].value == "left-pad ^1.0.0"
        assert "peer dependency" in (facts["dependency:react"].evidence[0].detail or "")
        assert "dependency:optional.fsevents" in facts
        assert "dependency:development.jest" in facts
        assert "dependency:none" not in facts


def test_no_declared_dependency_is_a_verified_zero(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "widget", "devDependencies": {"jest": "^29"}}), encoding="utf-8"
    )
    facts = {
        fact.id: fact
        for fact in npm_package.manifest_facts("nodejs", tmp_path, tmp_path / "package.json")
    }
    assert facts["dependency:none"].value == "none"
    assert facts["dependency:none"].polarity == "SUPPORTED"
    assert "package:node_engine" not in facts


def _symbol(value: str, kind: str, path: str, doc: str = "", signature: str = "") -> Any:
    return SimpleNamespace(
        value=value, symbol_kind=kind, source_path=path, line=3, doc=doc, signature=signature
    )


def test_only_what_the_entry_point_binds_is_published(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "index.js": 'export { Widget } from "./Widget.js";\nexport { run } from "./run.js";\n',
            "Widget.js": "export class Widget {}\n",
            "run.js": "export function run() {}\n",
            "Hidden.js": "export class Hidden {}\n",
            "Rival.js": "export class Widget {}\n",
        },
    )
    symbols = [
        _symbol("Widget", "class", "Widget.js", doc="A widget."),
        _symbol("Widget.save", "method", "Widget.js", signature="save(path)"),
        _symbol("run", "function", "run.js"),
        _symbol("Hidden", "class", "Hidden.js"),
        # A second `Widget` the barrel does not bind from this file is no export of the package.
        _symbol("Widget", "class", "Rival.js"),
        _symbol("pkg.sub", "module", "Widget.js"),
    ]
    facts = npm_package.public_symbol_facts(
        tmp_path, tmp_path / "index.js", symbols, JAVASCRIPT_MODULES
    )
    assert [fact.value for fact in facts] == ["Widget", "Widget.save", "run"]
    widget, save, run = facts
    assert widget.attributes == {"symbol_kind": "class", "docstring": "A widget."}
    assert save.attributes == {"symbol_kind": "method", "signature": "save(path)"}
    assert run.evidence[0].path == "run.js"
    assert "re-exported by the package entry point `index.js`" in (widget.evidence[0].detail or "")


@pytest.mark.parametrize(
    ("value", "kind", "expected"),
    [
        ("aspose.threed.Scene", "module", ""),
        ("Scene.save", "method", "Scene.save"),
        ("Orphan.save", "method", ""),
        ("save", "method", ""),
        ("aspose.threed.Scene.Scene", "class", "Scene"),
    ],
)
def test_a_symbol_is_named_as_a_consumer_writes_it(value: str, kind: str, expected: str) -> None:
    exported: dict[str, frozenset[str] | None] = {"Scene": None}
    assert npm_package.public_name(value, kind, exported, "Scene.ts", {}) == expected


def test_javascript_declares_async_functions_and_generators_behind_export(tmp_path: Path) -> None:
    """A Node library exports `async function` as readily as a class; the TypeScript reading
    (unchanged) does not name them, and a function missed here is a public function never
    published."""
    _write(
        tmp_path,
        {
            "index.js": 'export * from "./api.js";\n',
            "api.js": (
                "export async function fetchAll() {}\n"
                "export function* walk() {}\n"
                "export default class Main {}\n"
                "export const VERSION = 1;\n"
            ),
            "index.ts": 'export * from "./api";\n',
            "api.ts": "export async function fetchAll() {}\nexport class Main {}\n",
        },
    )
    found = _bindings(tmp_path / "index.js", JAVASCRIPT_MODULES)
    assert {"fetchAll", "walk", "Main", "VERSION"} <= set(found)
    assert set(_bindings(tmp_path / "index.ts", TYPESCRIPT_MODULES)) == {"Main"}
