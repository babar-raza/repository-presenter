"""The Rust plugin supplies what is Rust's own and leaves the rest to the shared façades."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import rust
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact, slug

CARGO_TOML = """[package]
name = "aspose-widget-foss-rust"
version = "26.7.0"
edition = "2021"
license = "MIT"

[lib]
name = "aspose_widget_foss_rust"
path = "src/lib.rs"

[dependencies]
chrono = "0.4"
"""
LIB = """//! The widget library.

pub mod widget;

pub use widget::Widget;
"""
WIDGET = """/// A widget.
pub struct Widget {
    /// The widget's name.
    pub name: String,
}

impl Widget {
    /// Creates a widget.
    pub fn new() -> Self {
        Widget { name: String::new() }
    }
}

/// The kind of a widget.
pub enum WidgetKind {
    Round,
    Square,
}
"""


def _repository(root: Path) -> list[str]:
    (root / "Cargo.toml").write_text(CARGO_TOML, encoding="utf-8", newline="\n")
    source = root / "src"
    source.mkdir()
    (source / "lib.rs").write_text(LIB, encoding="utf-8", newline="\n")
    (source / "widget.rs").write_text(WIDGET, encoding="utf-8", newline="\n")
    tests = root / "tests"
    tests.mkdir()
    (tests / "integration.rs").write_text(
        WIDGET.replace("Widget", "TestOnlyWidget"), encoding="utf-8", newline="\n"
    )
    return ["Cargo.toml", "src/lib.rs", "src/widget.rs", "tests/integration.rs"]


def test_the_plugin_is_discovered_by_module_name_and_registers_its_spec() -> None:
    assert plugin_for("rust") is rust.PLUGIN
    assert "rust" in known_ecosystems()
    # §29.6 E3/E4: the renderer reads the vocabulary from the spec, never from a branch on the
    # ecosystem name, and the plugin's own module is where Rust's spec is declared.
    assert spec_for("rust") is rust.RUST
    assert spec_for("rust").registry == "crates.io"
    assert spec_for("rust").floor_fact_id == "package:rust_edition"


def test_the_verify_command_needs_no_module_and_survives_formatting() -> None:
    """README_CONTRACT §2 row 8: Rust's idiomatic verify line takes no import path."""
    assert rust.RUST.verify_command.format(module="aspose_widget_foss_rust") == "cargo check"


def test_the_governing_manifest_is_the_outermost_cargo_file(tmp_path: Path) -> None:
    _repository(tmp_path)
    for ignored in ("target", ".cargo"):
        nested = tmp_path / ignored / "member"
        nested.mkdir(parents=True)
        (nested / "Cargo.toml").write_text("[package]\nname = 'x'\n", encoding="utf-8")
    member = tmp_path / "fuzz"
    member.mkdir()
    (member / "Cargo.toml").write_text("[package]\nname = 'fuzz'\n", encoding="utf-8")
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "Cargo.toml"


def test_a_repository_with_no_manifest_has_no_manifest_and_no_surface(tmp_path: Path) -> None:
    assert rust.PLUGIN.detect_manifest(tmp_path) is None
    assert rust.PLUGIN.surface_facts(tmp_path, []) == []


def test_the_import_path_is_the_library_name_not_the_crate_name(tmp_path: Path) -> None:
    """§29.12: Cargo publishes hyphens and Rust imports underscores; they are two strings."""
    tree = _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in rust.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    assert facts["package:name"].value == "aspose-widget-foss-rust"
    assert facts["install_command:cargo"].value == "cargo add aspose-widget-foss-rust"
    assert facts["package:version"].value == "26.7.0"
    imports = [fact for fact in facts.values() if fact.kind == "import_path"]
    assert [fact.value for fact in imports] == ["aspose_widget_foss_rust"]


def test_the_declared_floor_is_the_edition_when_no_compiler_version_is_declared(
    tmp_path: Path,
) -> None:
    """The manifest's own vocabulary, not a version invented for it (§29.12)."""
    _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in rust.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    assert facts["package:rust_edition"].value == "2021"
    assert "package:rust_version" not in facts
    manifest.write_text(
        CARGO_TOML.replace('edition = "2021"', 'edition = "2021"\nrust-version = "1.74"'),
        encoding="utf-8",
        newline="\n",
    )
    with_floor = {fact.id: fact for fact in rust.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    assert with_floor["package:rust_version"].value == "1.74"
    assert with_floor["package:rust_edition"].value == "2021"


def test_a_requirement_carries_its_version_in_either_spelling(tmp_path: Path) -> None:
    """README_CONTRACT §2 row 9: a reader installs a version, not a name."""
    _repository(tmp_path)
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(
        CARGO_TOML + '\nzip = { version = "0.6", optional = true }\n'
        'local = { path = "../local" }\n\n[dev-dependencies]\ncriterion = "0.5"\n',
        encoding="utf-8",
        newline="\n",
    )
    facts = {
        fact.id: fact
        for fact in rust.PLUGIN.manifest_facts(tmp_path, manifest, [])
        if fact.kind == "dependency"
    }
    assert facts["dependency:chrono"].value == "chrono 0.4"
    assert facts[f"dependency:{slug('optional.zip')}"].value == "zip 0.6"
    # A requirement with a source and no version says so rather than claiming a version.
    assert facts[f"dependency:{slug('local')}"].value == "local (path)"
    assert facts[f"dependency:{slug('development.criterion')}"].value == "criterion 0.5"
    assert "dependency:none" not in facts


def test_a_crate_with_no_dependencies_proves_a_verified_zero(tmp_path: Path) -> None:
    """README_CONTRACT §2 row 9: the marker cites the clause, it is never an empty row."""
    _repository(tmp_path)
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(CARGO_TOML.split("[dependencies]")[0], encoding="utf-8", newline="\n")
    facts = {fact.id: fact for fact in rust.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    marker = facts["dependency:none"]
    assert marker.value == "none"
    assert "dependencies" in (marker.evidence[0].detail or "")


def test_a_manifest_that_will_not_parse_declares_no_requirement(tmp_path: Path) -> None:
    _repository(tmp_path)
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text("[package\nname =", encoding="utf-8", newline="\n")
    assert list(rust.requirements(manifest)) == []


def test_a_file_cargo_builds_as_its_own_target_is_no_part_of_the_surface() -> None:
    """Cargo's own target rules: a test, a bench or an example is not reachable by `use`."""
    assert rust.importable("src/widget.rs")
    assert rust.importable("src/format/xlsx.rs")
    assert not rust.importable("tests/integration.rs")
    assert not rust.importable("benches/throughput.rs")
    assert not rust.importable("examples/basic.rs")
    assert not rust.importable("samples/basic.rs")
    assert not rust.importable("build.rs")


def test_surface_facts_come_from_the_shared_extractor_and_skip_separate_targets(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    facts = rust.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    kinds = {fact.value: (fact.attributes or {})["symbol_kind"] for fact in facts}
    # The module path is derived from the crate's source root, never from the manifest's own
    # directory: `src` is not a Rust module and no consumer writes `src::widget::Widget`.
    assert "widget.Widget" in values
    assert not any(value.startswith("src") for value in values)
    assert kinds["widget.Widget"] == "class"
    assert "widget.WidgetKind" in values and kinds["widget.WidgetKind"] == "enum"
    # The `tests/` target beside it declares TestOnlyWidget and no consumer can reach it.
    assert not any(value.startswith("TestOnlyWidget") for value in values)
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "line " in fact.evidence[0].detail


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = rust.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("cargo", "crate", None, True, None, None, "offline")

    monkeypatch.setattr(rust, "observe", unreadable)
    resolved, probes = rust.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_crate_the_registry_does_not_carry_contradicts_the_install_claim(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Measured 2026-09-06: crates.io answers 404 for `aspose-cells-foss-rust`.

    The reading is conclusive, so the fact says so. README_CONTRACT §2 row 8 requires the
    Installation section to state an unpublished package plainly rather than print a command
    the registry contradicts, and the renderer already does; BC-02 does not yet allow it
    (PROPOSAL P5, docs/RESEARCH_LANE_D.md).
    """
    tree = _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = rust.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def absent(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation(
            "cargo",
            "crate",
            False,
            False,
            "https://crates.io/api/v1/crates/crate",
            "crates-io-api",
            "live_probe",
        )

    monkeypatch.setattr(rust, "observe", absent)
    resolved, probes = rust.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["CONTRADICTED"]
    assert "distribution not found" in (resolved[0].evidence[-1].detail or "")
    assert probes and probes[0].outcome == "CONTRADICTED"


def test_a_published_crate_supports_the_install_claim(monkeypatch: Any, tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = rust.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def published(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation(
            "cargo",
            "crate",
            True,
            False,
            "https://crates.io/api/v1/crates/crate",
            "crates-io-api",
            "live_probe",
        )

    monkeypatch.setattr(rust, "observe", published)
    resolved, _ = rust.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["SUPPORTED"]
    # BC-02 reads the evidence for both readings by name.
    details = " ".join(evidence.detail or "" for evidence in resolved[0].evidence)
    assert "manifest" in details and "package registry" in details


def test_a_missing_manifest_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """§29.6 E5: a check this plugin cannot run is UNRESOLVED, never CONTRADICTED."""
    from repository_presenter.core.examples import ExampleCandidate

    candidates = [ExampleCandidate(1, "rust", "let w = Widget::new();", "README.md", 1, 3, "u:1")]
    receipts = rust.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert "no Cargo.toml" in (receipts[0].detail or "")


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout §2.1: core, the shared façades, and its own file - nothing else."""
    import ast

    source = Path(rust.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("rust") for name in siblings), siblings
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
                "repository_presenter.components.readme.extractors.platforms.rust",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = rust.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *rust.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *rust.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)
