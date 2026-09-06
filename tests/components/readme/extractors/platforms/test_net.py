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


CONSOLE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <PackageId>Aspose.Widget.Converter</PackageId>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\main\\Aspose.Widget\\Aspose.Widget.csproj" />
  </ItemGroup>
</Project>
"""
UNDECLARED_TESTS = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="NUnit" version="4.2.2" />
  </ItemGroup>
</Project>
"""
BUILD_PROPS = """<Project>
  <PropertyGroup>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>
"""


def test_a_console_tool_one_level_up_does_not_outrank_the_library(tmp_path: Path) -> None:
    """Measured 2026-09-06 on Aspose.3D for .NET: depth chose the converter, not the product.

    `src/converter/Converter.csproj` is one directory above `src/main/Aspose.ThreeD/`, and its
    only source declares no public type, so the repository produced zero public symbols and the
    API Reference row had no evidence at all. `OutputType` says which one is an application.
    """
    library = tmp_path / "src" / "main" / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    console = tmp_path / "src" / "converter"
    console.mkdir(parents=True)
    (console / "Converter.csproj").write_text(CONSOLE, encoding="utf-8")
    (console / "Program.cs").write_text("internal class Program { }\n", encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    where = manifest.relative_to(tmp_path).as_posix()
    assert where == "src/main/Aspose.Widget/Aspose.Widget.csproj"


def test_a_shared_property_file_at_the_root_never_governs(tmp_path: Path) -> None:
    """Measured 2026-09-06 on Email, Slides and Words for .NET.

    `Directory.Build.props` only lends properties to the projects beside it, and sits where depth
    always prefers it - so the surface was read from the whole tree, tests and samples included.
    """
    library = tmp_path / "src" / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    (tmp_path / "Directory.Build.props").write_text(BUILD_PROPS, encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "src/Aspose.Widget/Aspose.Widget.csproj"


def test_a_test_project_that_declares_nothing_is_still_a_test_project(tmp_path: Path) -> None:
    """Measured 2026-09-06 on Aspose.Words for .NET: `Aspose.JavaMs.Tests` declares no
    `IsTestProject`, no `IsPackable` and no `OutputType`, sits at the same depth as
    `Aspose.Words`, and sorts before it. A reference to a test runner is the declaration."""
    library = tmp_path / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    suite = tmp_path / "Aspose.JavaMs.Tests"
    suite.mkdir(parents=True)
    (suite / "Aspose.JavaMs.Tests.csproj").write_text(UNDECLARED_TESTS, encoding="utf-8")
    (suite / "WidgetTests.cs").write_text(WIDGET, encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "Aspose.Widget/Aspose.Widget.csproj"


DEPENDENT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>Aspose.Widget</PackageId>
    <TargetFrameworks>net10.0;net6.0;netcoreapp3.1</TargetFrameworks>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="SkiaSharp" Version="2.88.8" />
    <PackageReference Include="SonarAnalyzer.CSharp" Version="10.33.0" PrivateAssets="all" />
    <PackageReference Include="ILRepack" Version="2.0.46" ExcludeAssets="all" />
    <ProjectReference Include="..\\Other\\Other.csproj" />
  </ItemGroup>
</Project>
"""


def test_a_package_reference_becomes_a_dependency_and_a_private_one_is_development(
    tmp_path: Path,
) -> None:
    """Contract §2 row 9. A reference a consumer never installs is a development dependency.

    Measured 2026-09-06: SkiaSharp on Cells and System.Drawing.Common on PDF are required;
    SonarAnalyzer.CSharp on PDF and ILRepack on Words are private. A `ProjectReference` is not a
    package a reader installs at all.
    """
    source = tmp_path / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(DEPENDENT, encoding="utf-8")
    (source / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}

    assert facts["dependency:skiasharp"].value == "SkiaSharp 2.88.8"
    assert (
        facts["dependency:development.sonaranalyzer.csharp"].value == "SonarAnalyzer.CSharp 10.33.0"
    )
    assert facts["dependency:development.ilrepack"].value == "ILRepack 2.0.46"
    assert "dependency:none" not in facts
    assert not any("other" in fact_id for fact_id in facts)
    # The floor is the lowest target across every lineage, not the lowest the vendored table
    # happens to name: netcoreapp3.1 is older than net6.0 and both are older than net10.0.
    assert facts["package:target_framework"].value == "netcoreapp3.1"


def test_a_project_with_no_package_reference_proves_a_verified_zero(tmp_path: Path) -> None:
    """3D, Email and Slides for .NET declare none, which the contract renders as a sentence."""
    _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert marker.evidence[0].path == "src/Aspose.Widget/Aspose.Widget.csproj"
    assert "PackageReference" in (marker.evidence[0].detail or "")


def test_the_broadest_target_framework_orders_first() -> None:
    """netstandard runs everywhere; netcoreapp and net5+ are one lineage; net48 is another."""
    targets = ["net48", "net10.0", "netcoreapp3.1", "netstandard2.0", "net6.0"]
    assert sorted(targets, key=net._framework_order) == [
        "netstandard2.0",
        "netcoreapp3.1",
        "net6.0",
        "net10.0",
        "net48",
    ]
    # A target the pattern does not know sorts last rather than raising.
    assert net._framework_order("uap10.0")[0] == 3


def test_a_project_file_that_will_not_parse_still_ranks(tmp_path: Path) -> None:
    """A malformed project claims nothing rather than raising: the remaining keys rank it."""
    broken = tmp_path / "Aspose.Broken"
    broken.mkdir(parents=True)
    (broken / "Aspose.Broken.csproj").write_text("<Project", encoding="utf-8")
    assert net._declares(broken / "Aspose.Broken.csproj") == (False, False)
    assert net.PLUGIN.detect_manifest(tmp_path) == broken / "Aspose.Broken.csproj"


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
                # A project file is XML, and reading what it declares about itself is .NET's
                # own knowledge; the standard library parser keeps it out of shared code.
                "xml.etree",
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
