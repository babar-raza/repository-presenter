"""The Node.js plugin publishes what the package entry point exports and nothing else."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import nodejs
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact, slug
from repository_presenter.core.toolchains import resolve_tool

MANIFEST = {
    "name": "widget-js",
    "version": "0.1.0",
    "type": "module",
    "main": "src/index.js",
    "exports": {".": "./src/index.js"},
    "engines": {"node": ">=18.0.0"},
}
BARREL = """
export { Widget } from "./Widget.js";
export * from "./shading/index.js";
"""
WIDGET = """/**
 * A widget that tints things.
 *
 * @class Widget
 */
export class Widget {
  /**
   * Save the widget to a path.
   *
   * @param {string} path - Where to write it.
   * @returns {Promise<void>}
   */
  save(path) {}

  /** @private */
  _secret() {}
}
"""
SHADING = 'export { Material } from "./Material.js";\n'
MATERIAL = (
    "/** A material. */\n"
    "export class Material {\n"
    "  /** Tint the material. */\n"
    "  tint(colour) {}\n"
    "}\n"
)
# Exported so a sibling can import it, and never re-exported by the entry point: a consumer of the
# published package cannot reach it, so it is not part of the surface.
INTERNAL = "export class InternalBuffer {\n  flush() {}\n}\n"


def _repository(root: Path, manifest: dict[str, Any] | None = None) -> list[str]:
    (root / "package.json").write_text(json.dumps(manifest or MANIFEST, indent=2), encoding="utf-8")
    source = root / "src"
    (source / "shading").mkdir(parents=True)
    (source / "index.js").write_text(BARREL, encoding="utf-8")
    (source / "Widget.js").write_text(WIDGET, encoding="utf-8")
    (source / "InternalBuffer.js").write_text(INTERNAL, encoding="utf-8")
    (source / "shading" / "index.js").write_text(SHADING, encoding="utf-8")
    (source / "shading" / "Material.js").write_text(MATERIAL, encoding="utf-8")
    return [
        "package.json",
        "src/index.js",
        "src/Widget.js",
        "src/InternalBuffer.js",
        "src/shading/index.js",
        "src/shading/Material.js",
    ]


def _values(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.value: fact for fact in facts}


def test_the_plugin_is_discovered_by_module_name() -> None:
    assert plugin_for("nodejs") is nodejs.PLUGIN
    assert "nodejs" in known_ecosystems()


def test_the_spec_registers_itself_when_the_plugin_module_is_imported() -> None:
    """Section 29.6 E3: adding an ecosystem is adding its files, never editing a shared list."""
    spec = spec_for("nodejs")
    assert spec is nodejs.NODEJS
    assert spec.fence == "javascript" and spec.registry == "npm"
    assert spec.badge("aspose-jmap-foss").startswith(
        "[![npm](https://img.shields.io/npm/v/aspose-jmap-foss"
    )
    assert {"javascript", "js", "mjs", "cjs"} <= spec.example_fences
    # Negative control: another language's fence is not a JavaScript example.
    assert "typescript" not in spec.example_fences and "python" not in spec.example_fences
    assert spec.floor_fact_id == "package:node_engine" and spec.floor_is_minimum
    assert spec.runtime_badge(">=18.0.0").endswith("-18.0.0%2B-blue.svg)")


def test_no_verify_the_install_block_can_be_rendered_for_a_package_built_from_source() -> None:
    """The renderer prints "Verify the install: npm ls <name>" whenever an executed example
    names the module, whatever the install kind, and `npm ls <name>` proves nothing for a package
    built from a source checkout - the only state the one Node.js library is in. So the spec keeps
    the default pattern, which a quoted specifier never matches (TypeScript's state too), until the
    renderer withholds the block for a source install."""
    spec = spec_for("nodejs")
    pattern = spec.import_pattern.format(module=re.escape("widget-js"))
    assert not re.search(pattern, 'import { Widget } from "widget-js";\n')
    assert not re.search(pattern, 'const { Widget } = require("widget-js");\n')


def test_the_suite_rule_counts_test_sources_and_not_the_files_beside_them() -> None:
    rule = spec_for("nodejs").suite_files
    assert rule is not None
    for name in ("client.test.js", "client.spec.mjs", "client-test.js", "client_test.js"):
        assert rule.accepts_name(f"test/models/{name}"), name
    assert rule.accepts_name("test-client.js")
    for name in ("helper.js", "fixtures.js", "setup.js", "index.js", "latest.js"):
        assert not rule.accepts_name(f"test/{name}"), name


def test_the_surface_is_what_the_entry_point_exports(tmp_path: Path) -> None:
    """JavaScript has no `public` at module scope: only the entry point decides what is reachable.

    The negative control is `InternalBuffer`, which says `export` so a sibling can import it and
    is re-exported by nothing. A consumer of the published package cannot name it, so no fact
    claims it - while `Material`, reached through `export * from './shading/index.js'`, is public.
    """
    tree = _repository(tmp_path)
    facts = nodejs.PLUGIN.surface_facts(tmp_path, tree)
    published = _values(facts)
    assert {"Widget", "Widget.save", "Material", "Material.tint"} <= set(published)
    assert not any(value.startswith("InternalBuffer") for value in published)
    # `_secret` is private by convention and by its own `@private` tag.
    assert "Widget._secret" not in published
    # The name is the one a consumer writes, not the file it was declared in.
    assert not any("." in value.split(".")[0] for value in published)
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "re-exported by the package entry point" in (
            fact.evidence[0].detail
        )
    assert published["Widget"].evidence[0].path == "src/Widget.js"


def test_jsdoc_describes_the_class_and_its_members(tmp_path: Path) -> None:
    """A JSDoc block before an `export class` sits outside the class declaration, in the
    `export_statement` around it; the TypeScript adapter steps through that, and the façade
    registers it for JavaScript (measured on Aspose.JMAP-FOSS-for-Node.js: 30 of 30 exported
    classes read as undocumented without it)."""
    tree = _repository(tmp_path)
    published = _values(nodejs.PLUGIN.surface_facts(tmp_path, tree))
    assert (published["Widget"].attributes or {})["docstring"] == "A widget that tints things."
    assert (published["Widget.save"].attributes or {})["docstring"] == "Save the widget to a path."
    assert (published["Widget.save"].attributes or {})["signature"] == "save(path)"
    assert (published["Material"].attributes or {})["symbol_kind"] == "class"
    assert (published["Material.tint"].attributes or {})["symbol_kind"] == "method"


def test_an_exported_top_level_function_is_published(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    (tmp_path / "src" / "util.js").write_text(
        "/** Turn a column letter into an index. */\n"
        "export function colToIndex(column) { return 0; }\n"
        "export function internalOnly() {}\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "index.js").write_text(
        BARREL + 'export { colToIndex } from "./util.js";\n', encoding="utf-8"
    )
    tree.append("src/util.js")
    published = _values(nodejs.PLUGIN.surface_facts(tmp_path, tree))
    assert (published["colToIndex"].attributes or {})["symbol_kind"] == "function"
    assert published["colToIndex"].evidence[0].path == "src/util.js"
    assert "internalOnly" not in published


def test_a_commonjs_package_publishes_what_module_exports_assigns(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "widget-cjs", "main": "lib/index.js"}), encoding="utf-8"
    )
    library = tmp_path / "lib"
    library.mkdir()
    (library / "index.js").write_text(
        "const { Engine } = require('./engine');\n"
        "const { Gauge } = require('./gauge');\n"
        "module.exports = { Engine, Gauge };\n",
        encoding="utf-8",
    )
    (library / "engine.js").write_text(
        "/** Drives the thing. */\n"
        "class Engine {\n  /** Start it. */\n  start() {}\n}\n"
        "module.exports = { Engine };\n",
        encoding="utf-8",
    )
    (library / "gauge.js").write_text(
        "class Gauge {\n  read() {}\n}\nmodule.exports = { Gauge };\n", encoding="utf-8"
    )
    (library / "hidden.js").write_text(
        "class Hidden {\n  peek() {}\n}\nmodule.exports = { Hidden };\n", encoding="utf-8"
    )
    published = _values(nodejs.PLUGIN.surface_facts(tmp_path, ["lib/index.js"]))
    assert {"Engine", "Engine.start", "Gauge", "Gauge.read"} <= set(published)
    assert not any(value.startswith("Hidden") for value in published)
    assert (published["Engine"].attributes or {})["docstring"] == "Drives the thing."


def test_a_repository_with_no_entry_point_publishes_no_surface(tmp_path: Path) -> None:
    """No evidence for what a package exposes is not licence to publish every declaration."""
    (tmp_path / "package.json").write_text('{"name": "widget"}', encoding="utf-8")
    (tmp_path / "loose.js").write_text(INTERNAL, encoding="utf-8")
    assert nodejs.PLUGIN.surface_facts(tmp_path, ["loose.js"]) == []


def test_a_class_assembled_from_mixins_publishes_only_what_its_own_body_declares(
    tmp_path: Path,
) -> None:
    """The measured shape of Aspose.JMAP-FOSS-for-Node.js: the entry point extends an aliased
    base and mixes object-literal methods into the prototype. Their members are declared behind an
    import alias the extractor does not follow, so none is claimed - an unsupported claim stays
    unsupported rather than being invented."""
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "mixed", "main": "src/index.js"}), encoding="utf-8"
    )
    source = tmp_path / "src"
    source.mkdir()
    (source / "index.js").write_text(
        'import { Client as CoreClient } from "./core.js";\n'
        'import { MailMixin } from "./mail.js";\n'
        "class Client extends CoreClient {}\n"
        "Object.assign(Client.prototype, MailMixin);\n"
        "export { Client };\n",
        encoding="utf-8",
    )
    (source / "core.js").write_text("export class Client {\n  connect() {}\n}\n", encoding="utf-8")
    (source / "mail.js").write_text(
        "export const MailMixin = {\n  async listMailboxes() {},\n};\n", encoding="utf-8"
    )
    values = {fact.value for fact in nodejs.PLUGIN.surface_facts(tmp_path, [])}
    assert "Client" in values
    assert "MailMixin" not in values and "Client.listMailboxes" not in values


def test_manifest_facts_carry_identity_version_install_and_the_module_specifier(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path, {**MANIFEST, "dependencies": {"left-pad": "^1.3.0"}})
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    assert facts["package:name"].value == "widget-js"
    assert facts["package:version"].value == "0.1.0"
    assert facts["install_command:npm"].value == "npm install widget-js"
    # Unresolved until a registry says otherwise: a declared name is not a published package.
    assert facts["install_command:npm"].polarity == "UNRESOLVED"
    assert facts["import_path:widget-js"].value == "widget-js"
    assert facts["dependency:left-pad"].value == "left-pad ^1.3.0"
    assert facts[spec_for("nodejs").floor_fact_id].value == ">=18.0.0"
    assert spec_for("nodejs").floor_declaration == "engines.node"


def test_a_manifest_with_no_runtime_dependency_proves_a_verified_zero(tmp_path: Path) -> None:
    """Contract §2 row 9: zero is rendered as a sentence citing the clause that proves it."""
    tree = _repository(tmp_path)
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert "`dependencies`" in (marker.evidence[0].detail or "")


def test_a_dependency_copy_never_governs_the_package(tmp_path: Path) -> None:
    """Every installed dependency ships a `package.json`; only the repository's own counts."""
    _repository(tmp_path)
    nested = tmp_path / "node_modules" / "left-pad"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text('{"name": "left-pad"}', encoding="utf-8")
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "package.json"


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("npm", "widget-js", None, True, None, None, "offline")

    monkeypatch.setattr(nodejs, "observe", unreadable)
    resolved, probes = nodejs.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_published_name_is_confirmed_only_for_this_repository(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """The registry is asked who owns the name, so the README cannot tell a reader to install
    another project's package (TC-EXT-01)."""
    from repository_presenter.components.readme.extractors.surface.registry import (
        RegistryObservation,
    )

    asked: list[dict[str, object]] = []

    def observe(ecosystem: str, name: str, **kwargs: object) -> RegistryObservation:
        asked.append({"ecosystem": ecosystem, "name": name, **kwargs})
        return RegistryObservation(
            "npm", name, True, False, "https://registry.npmjs.org/x", "api", "live_probe"
        )

    monkeypatch.setattr(nodejs, "observe", observe)
    tree = _repository(tmp_path)
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = [
        Fact(
            "identity:repository",
            "identity",
            "aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js",
            nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree)[0].evidence,
        ),
        *nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree),
    ]
    [resolved], [probe] = nodejs.PLUGIN.registry_facts(facts)
    assert asked == [
        {
            "ecosystem": "nodejs",
            "name": "widget-js",
            "repository": "aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js",
        }
    ]
    assert probe.target == "npm:widget-js"
    assert resolved.id == "install_command:npm"


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout section 2.1: core, the shared façades, and its own files - nothing else.

    Least of all the TypeScript plugin, whose machinery this one shares through
    `surface/npm_package.py` rather than by importing it.
    """
    source = Path(nodejs.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("nodejs") for name in siblings), siblings
    assert all(
        name.startswith(
            (
                "repository_presenter.core",
                "repository_presenter.components.readme.extractors.surface",
                "collections",
                "pathlib",
                "typing",
                "__future__",
                "repository_presenter.components.readme.extractors.platforms.nodejs",
            )
        )
        for name in imported
    ), sorted(imported)
    for helper in ("nodejs_examples.py",):
        tree = ast.parse(Path(nodejs.__file__).with_name(helper).read_text("utf-8"))
        names = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not [name for name in names if "typescript" in name], (helper, sorted(names))


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = nodejs.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *nodejs.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *nodejs.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)


README = """# Widget JS

A widget library.

## Quick start

```javascript
import { Widget } from "widget-js";

const widget = new Widget();
```

A fragment that leans on the variable above:

```js
widget.save("out.bin");
```

```bash
npm install widget-js
```
"""


def test_the_facts_document_for_a_local_nodejs_clone(tmp_path: Path, monkeypatch: Any) -> None:
    """The official facts path on a real (local) clone: the entry validates as a registry entry,
    the plugin is found by its ecosystem, and every stage that consumed an ecosystem name before
    this one existed - fences, the registry read, the product-page lookup, the install fact, the
    runtime floor, the examples - answers for it. Offline: the registry answer is recorded (the
    package is not published, which is the measured state of the Node.js JMAP library) and the
    package's own `npm install` is a stand-in."""
    from repository_presenter.components.readme.evidence.facts import links
    from repository_presenter.components.readme.evidence.facts.extract import extract_facts
    from repository_presenter.components.readme.extractors.examples.selection import (
        select_examples,
    )
    from repository_presenter.components.readme.extractors.platforms import nodejs_examples
    from repository_presenter.components.readme.extractors.platforms.registry import verify_build
    from repository_presenter.components.readme.extractors.surface.registry import (
        RegistryObservation,
    )
    from repository_presenter.core.git_safety.clone import pinned_read_only_clone
    from repository_presenter.core.registry.models import RegistryEntry
    from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths
    from support import commit_all, fake_npm, init_git_repository

    entry = RegistryEntry.model_validate(
        {
            "repository": "example-org/Aspose.Example-FOSS-for-Node.js",
            "family": "example",
            "platform": "nodejs",
            "ecosystem": "nodejs",
            "mode": "dry_run",
            "policy_profile": "example",
            "active": True,
            "provider_identity": {"provider": "github", "repository_id": 9, "node_id": "R_9"},
        }
    )
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    _repository(source)
    (source / "README.md").write_text(README, encoding="utf-8")
    (source / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    (source / "test").mkdir()
    (source / "test" / "widget.test.js").write_text("// a test\n", encoding="utf-8")
    commit_all(source, "seed")

    monkeypatch.setattr(links, "fetch_status", lambda url: (404, url))
    monkeypatch.setattr(
        nodejs,
        "observe",
        lambda ecosystem, name, **kw: RegistryObservation(
            "npm", name, False, False, f"https://registry.npmjs.org/{name}", "api", "fixture"
        ),
    )
    npm = fake_npm(tmp_path / "tools")
    monkeypatch.setattr(nodejs_examples, "npm_executable", lambda: npm)

    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(entry.repository, clone)
    tree_paths = list_tree_paths(clone.path)
    plugin = plugin_for(entry.ecosystem)
    manifest = plugin.detect_manifest(clone.path)
    assert snapshot.readme_path is not None
    examples = select_examples(
        snapshot.readme_path, (clone.path / snapshot.readme_path).read_bytes(), entry.ecosystem
    )
    # Only the two JavaScript fences are examples; the bash block is a command, not a snippet.
    assert [candidate.language for candidate in examples] == ["javascript", "js"]
    receipts = plugin.verify_examples(clone.path, tree_paths, examples, tmp_path / "examples")
    assert manifest is not None
    build = verify_build(plugin, clone.path, manifest, tmp_path / "build")

    document, probes = extract_facts(
        entry, snapshot, clone.path, tree_paths, plugin, manifest, examples, receipts, build=build
    )
    by_id = {fact.id: fact for fact in document.facts}
    assert by_id["identity:ecosystem"].value == "nodejs"
    symbols = {fact.value for fact in document.facts if fact.kind == "public_symbol"}
    assert {"Widget", "Widget.save", "Material", "Material.tint"} <= symbols
    assert not any(value.startswith("InternalBuffer") for value in symbols)
    assert by_id["package:name"].value == "widget-js"
    assert by_id["package:node_engine"].value == ">=18.0.0"
    # An unpublished package's install command is the source install its own build proved.
    install = by_id["install_command:npm"]
    assert install.polarity == "SUPPORTED"
    assert (install.attributes or {})["install_kind"] == "source"
    assert install.value.endswith("cd Aspose.Example-FOSS-for-Node.js\nnpm install")
    # The first example imports the package and loads (given a Node to load it with); the second
    # is a fragment and stays open either way.
    loaded = "SUPPORTED" if resolve_tool("node") is not None else "UNRESOLVED"
    assert by_id["example:001"].polarity == loaded
    assert by_id["example:002"].polarity == "UNRESOLVED"
    assert by_id["build_test_asset:tests"].polarity == "SUPPORTED"
    assert any(probe.kind == "registry" and probe.outcome == "CONTRADICTED" for probe in probes)
    # The product-page lookup consulted the nodejs slugs, not the platform name alone.
    assert any("/example/nodejs-java/" in probe.target for probe in probes if probe.kind == "link")
