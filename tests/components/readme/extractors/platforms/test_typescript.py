"""The TypeScript plugin publishes what the entry point re-exports and nothing else."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import typescript
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact, slug

MANIFEST = {
    "name": "@aspose/widget",
    "version": "1.2.3",
    "main": "dist/index.js",
    "types": "dist/index.d.ts",
    "dependencies": {"xmldom": "^0.6.0"},
    "devDependencies": {"typescript": "^5.9.3", "jest": "^29.7.0"},
}
TSCONFIG = {"compilerOptions": {"target": "ES2020", "rootDir": "./src", "outDir": "./dist"}}
BARREL = """
export { Widget } from './Widget';
export * from './shading';
"""
WIDGET = """
/** A widget. */
export class Widget {
  public name: string = '';
  save(path: string): void {}
}
"""
SHADING = "export { Material } from './Material';\n"
MATERIAL = "export class Material {\n  tint(colour: string): void {}\n}\n"
# Exported so a sibling can import it, and never re-exported by the entry point: a consumer of
# the published package cannot reach it, so it is not part of the surface.
INTERNAL = "export class InternalBuffer {\n  flush(): void {}\n}\n"


def _repository(root: Path, manifest: dict[str, Any] | None = None) -> list[str]:
    (root / "package.json").write_text(json.dumps(manifest or MANIFEST, indent=2), encoding="utf-8")
    (root / "tsconfig.json").write_text(json.dumps(TSCONFIG, indent=2), encoding="utf-8")
    source = root / "src"
    (source / "shading").mkdir(parents=True)
    (source / "index.ts").write_text(BARREL, encoding="utf-8")
    (source / "Widget.ts").write_text(WIDGET, encoding="utf-8")
    (source / "InternalBuffer.ts").write_text(INTERNAL, encoding="utf-8")
    (source / "shading" / "index.ts").write_text(SHADING, encoding="utf-8")
    (source / "shading" / "Material.ts").write_text(MATERIAL, encoding="utf-8")
    return [
        "package.json",
        "src/index.ts",
        "src/Widget.ts",
        "src/InternalBuffer.ts",
        "src/shading/index.ts",
        "src/shading/Material.ts",
    ]


def test_the_plugin_is_discovered_by_module_name() -> None:
    assert plugin_for("typescript") is typescript.PLUGIN
    assert "typescript" in known_ecosystems()


def test_the_spec_registers_itself_when_the_plugin_module_is_imported() -> None:
    """Section 29.6 E3: adding an ecosystem is adding its files, never editing a shared list."""
    spec = spec_for("typescript")
    assert spec is typescript.TYPESCRIPT
    assert spec.fence == "typescript" and spec.registry == "npm"
    assert spec.badge("@aspose/3d").startswith("[![npm](https://img.shields.io/npm/v/@aspose/3d")
    assert "ts" in spec.example_fences


def test_a_dependency_copy_never_governs_the_package(tmp_path: Path) -> None:
    """Every installed dependency ships a `package.json`; only the repository's own counts."""
    _repository(tmp_path)
    nested = tmp_path / "node_modules" / "left-pad"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text('{"name": "left-pad"}', encoding="utf-8")
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "package.json"


def test_the_entry_point_is_mapped_from_build_output_back_to_source(tmp_path: Path) -> None:
    """Measured 2026-09-06 on Aspose.3D for TypeScript.

    `package.json` declares `dist/index.js` and `dist/index.d.ts`, and the repository ships
    neither - `dist/` is build output. `tsconfig.json` says that output is built from `src/`, so
    the entry point resolves to a file the clone actually has.
    """
    _repository(tmp_path)
    barrel = typescript.entry_barrel(tmp_path)
    assert barrel is not None
    assert barrel.relative_to(tmp_path).as_posix() == "src/index.ts"


def test_a_declared_entry_point_that_re_exports_nothing_is_not_the_barrel(tmp_path: Path) -> None:
    """Measured 2026-09-06 on Aspose.Cells for TypeScript.

    Its `package.json` declares `main: index.ts`, and that file constructs a workbook, writes two
    spreadsheets and logs - a demo script. The real surface is the barrel beside it.
    """
    _repository(tmp_path, {**MANIFEST, "main": "demo.ts", "types": "demo.ts"})
    (tmp_path / "demo.ts").write_text(
        "import { Widget } from './src';\nconsole.log(new Widget());\n", encoding="utf-8"
    )
    barrel = typescript.entry_barrel(tmp_path)
    assert barrel is not None
    assert barrel.relative_to(tmp_path).as_posix() == "src/index.ts"


def test_the_surface_is_what_the_entry_point_re_exports(tmp_path: Path) -> None:
    """TypeScript has no `public` at module scope: only the barrel decides what is reachable.

    The negative control is `InternalBuffer`, which says `export` so a sibling can import it and
    is re-exported by nothing. A consumer of the published package cannot name it, so no fact
    claims it - while `Material`, reached through `export * from './shading'`, is public.
    """
    tree = _repository(tmp_path)
    facts = typescript.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    assert "Widget" in values and "Widget.save" in values and "Widget.name" in values
    assert "Material" in values and "Material.tint" in values
    assert not any(value.startswith("InternalBuffer") for value in values)
    # The name is the one a consumer writes, not the file it was declared in.
    assert not any("." in value.split(".")[0] for value in values)
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "re-exported by the package entry point" in (
            fact.evidence[0].detail
        )


def test_a_repository_with_no_entry_point_publishes_no_surface(tmp_path: Path) -> None:
    """No evidence for what a package exposes is not licence to publish every `export`."""
    (tmp_path / "package.json").write_text('{"name": "widget"}', encoding="utf-8")
    (tmp_path / "loose.ts").write_text(INTERNAL, encoding="utf-8")
    assert typescript.PLUGIN.surface_facts(tmp_path, ["loose.ts"]) == []


def test_manifest_facts_carry_identity_version_install_and_the_module_specifier(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in typescript.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    assert facts["package:name"].value == "@aspose/widget"
    assert facts["package:version"].value == "1.2.3"
    assert facts["install_command:npm"].value == "npm install @aspose/widget"
    # Unresolved until a registry says otherwise: a declared name is not a published package.
    assert facts["install_command:npm"].polarity == "UNRESOLVED"
    assert facts["import_path:aspose-widget"].value == "@aspose/widget"
    assert facts["dependency:xmldom"].value == "xmldom ^0.6.0"
    assert facts["dependency:development.typescript"].value == "typescript ^5.9.3"
    assert "dependency:none" not in facts
    # No `engines` clause, so no runtime floor is claimed at all.
    assert "package:node_engine" not in facts


def test_a_manifest_with_no_runtime_dependency_proves_a_verified_zero(tmp_path: Path) -> None:
    """Contract §2 row 9: zero is rendered as a sentence citing the clause that proves it."""
    tree = _repository(tmp_path, {**MANIFEST, "dependencies": {}})
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in typescript.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert "`dependencies`" in (marker.evidence[0].detail or "")
    # A development dependency is not a requirement a consumer installs, so it does not cancel it.
    assert "dependency:development.jest" in facts


def test_a_declared_node_engine_becomes_the_runtime_floor(tmp_path: Path) -> None:
    """The floor the renderer reports is the spec's fact, and `engines.node` is TypeScript's."""
    tree = _repository(tmp_path, {**MANIFEST, "engines": {"node": ">=20"}})
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in typescript.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    floor = facts[spec_for("typescript").floor_fact_id]
    assert floor.value == ">=20"
    assert spec_for("typescript").floor_declaration == "engines.node"


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = typescript.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("npm", "@aspose/widget", None, True, None, None, "offline")

    monkeypatch.setattr(typescript, "observe", unreadable)
    resolved, probes = typescript.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_missing_compiler_reports_not_verified_rather_than_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Section 29.6 E5: a check this plugin cannot run is UNRESOLVED, never CONTRADICTED."""
    from repository_presenter.components.readme.extractors.platforms import typescript_examples
    from repository_presenter.core.examples import ExampleCandidate

    _repository(tmp_path)
    monkeypatch.setattr(typescript_examples, "typescript_compiler", lambda: None)
    candidates = [
        ExampleCandidate(1, "typescript", "const w = new Widget();", "README.md", 1, 3, "unit:001")
    ]
    receipts = typescript.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in receipts[0].detail


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout section 2.1: core, the shared façades, and its own files - nothing else."""
    import ast

    source = Path(typescript.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("typescript") for name in siblings), siblings
    assert all(
        name.startswith(
            (
                "repository_presenter.core",
                "repository_presenter.components.readme.extractors.surface",
                "collections",
                "pathlib",
                "typing",
                "__future__",
                "tree_sitter_language_pack",
                "repository_presenter.components.readme.extractors.platforms.typescript",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = typescript.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *typescript.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *typescript.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)
