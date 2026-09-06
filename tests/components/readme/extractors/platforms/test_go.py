"""The Go plugin supplies what is Go's own and leaves the rest to the shared façades."""

from __future__ import annotations

import re
from functools import partial
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import go
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import EcosystemSpec, spec_for
from repository_presenter.core.facts import Fact, slug


def _names_module(pattern: str, text: str, *, module: str) -> bool:
    """Exactly what `composition/renderer.py::_installation` asks of an example's own source."""
    return re.search(pattern.format(module=re.escape(module)), text) is not None


GO_MOD = """module github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go/v26

go 1.24.5
"""
WIDGET = """package widget_foss

// Widget is a widget.
type Widget struct {
\tName string
}

// Save writes the widget to path.
func (w *Widget) Save(path string) error {
\treturn nil
}

// NewWidget creates a widget.
func NewWidget() *Widget {
\treturn &Widget{}
}
"""
DOC = """// Package widget_foss is a widget library.
package widget_foss
"""


def _repository(root: Path) -> list[str]:
    (root / "go.mod").write_text(GO_MOD, encoding="utf-8", newline="\n")
    (root / "doc.go").write_text(DOC, encoding="utf-8", newline="\n")
    source = root / "aspose" / "widget_foss"
    source.mkdir(parents=True)
    (source / "widget.go").write_text(WIDGET, encoding="utf-8", newline="\n")
    (source / "widget_test.go").write_text(
        WIDGET.replace("Widget", "TestOnlyWidget"), encoding="utf-8", newline="\n"
    )
    return ["go.mod", "doc.go", "aspose/widget_foss/widget.go"]


def test_the_plugin_is_discovered_by_module_name_and_registers_its_spec() -> None:
    assert plugin_for("go") is go.PLUGIN
    assert "go" in known_ecosystems()
    # §29.6 E3/E4: the renderer reads the vocabulary from the spec, never from a branch on the
    # ecosystem name, and the plugin's own module is where Go's spec is declared.
    assert spec_for("go") is go.GO
    assert spec_for("go").registry == "pkg.go.dev"
    assert spec_for("go").floor_fact_id == "package:go_version"


def test_the_import_pattern_is_gos_quoted_path_and_not_pythons_import() -> None:
    """§28.12 G4-W17 item 11: the Verify-the-install match is the spec's own.

    The renderer asks whether an executed example names the import path, with
    `spec.import_pattern.format(module=re.escape(value))`. Go writes the path *quoted*, usually
    inside an `import ( … )` block whose keyword is on an earlier line, which the inherited
    Python-shaped default never matches - the reason no Go candidate has rendered the block.
    Both fences below are the opening import of a cohort repository's own executed example.
    """
    module = "github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26/aspose/cells_foss"
    matches = partial(_names_module, module=module)
    aliased = f'package main\n\nimport cells_foss "{module}"\n\nfunc main() {{}}\n'
    assert matches(go.GO.import_pattern, aliased)
    # The bug this replaces, reproduced directly: Python's shape sees nothing here.
    assert not matches(EcosystemSpec("x", "X", "x", "x", "x").import_pattern, aliased)
    # Aspose.PDF's own executed example writes it inside a block, keyword on an earlier line.
    assert matches(go.GO.import_pattern, f'import (\n\t"fmt"\n\tpdf "{module}"\n)\n')
    # The plain and blank-identifier spellings are the same claim.
    assert matches(go.GO.import_pattern, f'import "{module}"\n')
    assert matches(go.GO.import_pattern, f'import _ "{module}"\n')
    # A longer path that merely starts with this one is a different package.
    assert not matches(go.GO.import_pattern, f'import "{module}/extra"\n')
    # The path named in prose, or a call on the package, is not an import.
    assert not matches(go.GO.import_pattern, f"The module lives at {module} today.\n")
    assert not matches(go.GO.import_pattern, "wb := cells_foss.NewWorkbook()\n")


def test_the_verify_command_takes_the_import_path_so_it_is_go_list_not_go_list_m() -> None:
    """The renderer fills `{module}` with an `import_path` fact, not the module path.

    Measured 2026-09-06 in a disposable consumer module after `go get`:
    `go list -m …/v26/aspose/cells_foss` exits 1 ("not a known dependency") because the package
    below the module root is not a module, while `go list …/v26/aspose/cells_foss` exits 0. The
    `-m` form would have rendered a command that fails for every Go repository whose package is
    not at the module root - never an unverified command (README_CONTRACT.md §2 row 8).
    """
    rendered = go.GO.verify_command.format(
        module="github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26/aspose/cells_foss"
    )
    assert rendered == (
        "go list github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26/aspose/cells_foss"
    )
    assert " -m " not in f" {rendered} "


def test_the_governing_manifest_is_the_outermost_module_file(tmp_path: Path) -> None:
    """A repository may carry a module file the go command itself ignores."""
    _repository(tmp_path)
    for ignored in ("_examples", "tools", "vendor"):
        nested = tmp_path / ignored
        nested.mkdir()
        (nested / "go.mod").write_text("module example\n", encoding="utf-8", newline="\n")
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "go.mod"


def test_a_repository_with_no_module_file_has_no_manifest_and_no_surface(tmp_path: Path) -> None:
    assert go.PLUGIN.detect_manifest(tmp_path) is None
    assert go.PLUGIN.surface_facts(tmp_path, []) == []


def test_the_import_path_carries_the_subdirectory_the_package_is_declared_in(
    tmp_path: Path,
) -> None:
    """§29.12: the module root and the importable package are not always the same directory."""
    tree = _repository(tmp_path)
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in go.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    module = "github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go/v26"
    assert facts["package:name"].value == module
    # The install line keeps the major-version suffix: without it `go get` resolves a different
    # module, or nothing at all (census §28.11, Cells Go).
    assert facts["install_command:go"].value == f"go get {module}"
    assert facts["package:go_version"].value == "1.24.5"
    imports = [fact for fact in facts.values() if fact.kind == "import_path"]
    assert [fact.value for fact in imports] == [f"{module}/aspose/widget_foss"]


def test_a_module_whose_package_is_at_the_root_imports_the_module_path(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        "module github.com/aspose-widget-foss/widget\n\ngo 1.24\n", encoding="utf-8", newline="\n"
    )
    (tmp_path / "widget.go").write_text(WIDGET, encoding="utf-8", newline="\n")
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = go.PLUGIN.manifest_facts(tmp_path, manifest, ["go.mod", "widget.go"])
    imports = [fact.value for fact in facts if fact.kind == "import_path"]
    assert imports == ["github.com/aspose-widget-foss/widget"]


def test_a_require_directive_becomes_a_dependency_in_either_spelling(tmp_path: Path) -> None:
    _repository(tmp_path)
    (tmp_path / "go.mod").write_text(
        GO_MOD + "\nrequire golang.org/x/crypto v0.31.0\n\n"
        "require (\n\tgolang.org/x/text v0.21.0 // indirect\n)\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {
        fact.id: fact
        for fact in go.PLUGIN.manifest_facts(tmp_path, manifest, [])
        if fact.kind == "dependency"
    }
    assert facts[f"dependency:{slug('golang.org/x/crypto')}"].value == "golang.org/x/crypto v0.31.0"
    indirect = facts[f"dependency:{slug('golang.org/x/text')}"]
    assert indirect.value == "golang.org/x/text v0.21.0"
    assert "indirect" in (indirect.evidence[0].detail or "")
    # A module that requires something is not a verified zero.
    assert "dependency:none" not in facts


def test_a_module_with_no_require_directive_proves_a_verified_zero(tmp_path: Path) -> None:
    """README_CONTRACT §2 row 9: the marker cites the clause, it is never an empty row."""
    _repository(tmp_path)
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in go.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    marker = facts["dependency:none"]
    assert marker.value == "none"
    assert "require" in (marker.evidence[0].detail or "")


def test_an_unimportable_file_is_no_part_of_the_surface() -> None:
    """Go's own build rules, not a naming convention (§28.11: 1,589 of Aspose.PDF's 3,056)."""
    assert go.importable("aspose/widget_foss/widget.go")
    assert not go.importable("aspose/widget_foss/widget_test.go")
    assert not go.importable("internal/scratch/widget.go")
    assert not go.importable("_examples/demo/main.go")
    assert not go.importable("testdata/fixture/widget.go")
    assert not go.importable("vendor/other/widget.go")


def test_surface_facts_come_from_the_shared_extractor_and_skip_test_files(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    facts = go.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    assert "Widget" in values
    assert "Widget.Save" in values
    assert "NewWidget" in values
    # The `_test.go` file beside it declares TestOnlyWidget and it is not importable.
    assert not any(value.startswith("TestOnlyWidget") for value in values)
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "line " in fact.evidence[0].detail


def test_a_package_below_the_module_root_qualifies_its_symbols(tmp_path: Path) -> None:
    """A consumer writes `ai.ChatOptions`, so the fact does too (Aspose.PDF for Go's `ai`)."""
    tree = _repository(tmp_path)
    nested = tmp_path / "aspose" / "widget_foss" / "ai"
    nested.mkdir(parents=True)
    (nested / "chat.go").write_text(
        "package ai\n\n// Chat is a chat.\ntype Chat struct {\n\tName string\n}\n",
        encoding="utf-8",
        newline="\n",
    )
    facts = go.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    assert "ai.Chat" in values
    assert "Widget" in values
    package = next(fact for fact in facts if fact.value == "ai")
    assert (package.attributes or {})["symbol_kind"] == "module"


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = go.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("goproxy", "module", None, True, None, None, "offline")

    monkeypatch.setattr(go, "observe", unreadable)
    resolved, probes = go.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_published_module_supports_the_install_claim(monkeypatch: Any, tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = go.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def published(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation(
            "go_modules",
            "module",
            True,
            False,
            "https://proxy.golang.org/x/@v/list",
            "go-proxy-api",
            "live_probe",
        )

    monkeypatch.setattr(go, "observe", published)
    resolved, _ = go.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["SUPPORTED"]
    # BC-02 reads the evidence for both readings by name.
    details = " ".join(evidence.detail or "" for evidence in resolved[0].evidence)
    assert "manifest" in details and "package registry" in details


def test_a_missing_toolchain_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """§29.6 E5: a check this plugin cannot run is UNRESOLVED, never CONTRADICTED."""
    from repository_presenter.core.examples import ExampleCandidate

    candidates = [ExampleCandidate(1, "go", "w := widget.New()", "README.md", 1, 3, "unit:001")]
    receipts = go.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert "no module file" in (receipts[0].detail or "")


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout §2.1: core, the shared façades, and its own file - nothing else."""
    import ast

    source = Path(go.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("go") for name in siblings), siblings
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
                "repository_presenter.components.readme.extractors.platforms.go",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = go.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *go.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *go.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)
