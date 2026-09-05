"""The .NET plugin supplies what is .NET's own and leaves the rest to the shared façades."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import net
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.facts import Fact, slug

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>Aspose.Widget</PackageId>
    <Version>1.2.3</Version>
    <TargetFrameworks>net8.0;net6.0</TargetFrameworks>
  </PropertyGroup>
</Project>
"""
WIDGET = """
namespace Aspose.Widget
{
    /// <summary>A widget.</summary>
    public class Widget
    {
        public string Name { get; set; }
        public void Save(string path) { }
    }
}
"""


def _repository(root: Path) -> list[str]:
    source = root / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (source / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    sample = root / "samples" / "Demo"
    sample.mkdir(parents=True)
    (sample / "Demo.csproj").write_text(CSPROJ, encoding="utf-8")
    return ["src/Aspose.Widget/Aspose.Widget.csproj", "src/Aspose.Widget/Widget.cs"]


def test_the_plugin_is_discovered_by_module_name() -> None:
    assert plugin_for("net") is net.PLUGIN
    assert "net" in known_ecosystems()


def test_the_governing_manifest_is_the_product_project_not_a_sample(tmp_path: Path) -> None:
    """Depth cannot separate two project files at the same level; sources beside them can."""
    _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    # Both project files sit three levels deep, so depth cannot separate them and sorting by
    # path would hand it to samples/. The product is the one with C# sources beside it.
    assert manifest.relative_to(tmp_path).as_posix() == "src/Aspose.Widget/Aspose.Widget.csproj"


def test_manifest_facts_carry_identity_version_framework_and_the_install_command(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    assert facts["package:name"].value == "Aspose.Widget"
    assert facts["package:version"].value == "1.2.3"
    assert facts["package:target_framework"].value == "net6.0"
    install = facts["install_command:dotnet"]
    assert install.value == "dotnet add package Aspose.Widget"
    # Unresolved until a registry says otherwise: a declared id is not a published package.
    assert install.polarity == "UNRESOLVED" and install.confidence == 0.5


def test_surface_facts_come_from_the_shared_extractor_with_slug_safe_values(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    facts = net.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    assert "Aspose.Widget.Widget" in values
    assert "Aspose.Widget.Widget.Save" in values
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "line " in fact.evidence[0].detail


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = net.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("nuget", "Aspose.Widget", None, True, None, None, "offline")

    monkeypatch.setattr(net, "observe", unreadable)
    resolved, probes = net.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_missing_verifier_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """Section 29.6 E5: a check this plugin cannot run is UNRESOLVED, never CONTRADICTED."""
    from repository_presenter.core.examples import ExampleCandidate

    candidates = [
        ExampleCandidate(1, "csharp", "var w = new Widget();", "README.md", 1, 3, "unit:001")
    ]
    receipts = net.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout section 2.1: core, the shared façades, and its own file - nothing else."""
    import ast

    source = Path(net.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    # Its own helper modules are allowed and are the established shape - python.py imports
    # python_surface and python_examples the same way. What section 2.1 forbids is another
    # ecosystem's module, so the rule is the prefix, not the package.
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("net") for name in siblings), siblings
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
                "repository_presenter.components.readme.extractors.platforms.net",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *net.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *net.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)
