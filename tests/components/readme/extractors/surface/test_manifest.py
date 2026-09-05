"""The manifest façade reports what a manifest carries, in its own ecosystem's vocabulary."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.surface.manifest import read_identity

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>Aspose.Widget</PackageId>
    <Version>1.2.3</Version>
    <TargetFrameworks>net8.0;net6.0</TargetFrameworks>
  </PropertyGroup>
</Project>
"""
PYPROJECT = """[project]
name = "aspose-widget"
version = "2.0"
requires-python = ">=3.9"
"""
POM = (
    "<project><groupId>com.aspose</groupId><artifactId>widget</artifactId>"
    "<version>3.0</version><properties><maven.compiler.source>17</maven.compiler.source>"
    "</properties></project>"
)


def test_a_dotnet_project_reports_its_package_id_version_and_lowest_framework(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (source / "Widget.cs").write_text(
        "namespace Aspose.Widget { public class Widget {} }", encoding="utf-8"
    )
    identity = read_identity(tmp_path, "net")
    assert identity.name == "Aspose.Widget" and identity.version == "1.2.3"
    assert identity.floor == "net6.0", "the floor is the lowest target, not the first listed"
    assert identity.package_root == "src/Aspose.Widget"
    assert identity.raw["target_frameworks"] == ["net8.0", "net6.0"]


def test_a_python_project_reports_its_requires_python_as_the_floor(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    package = tmp_path / "aspose_widget"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    identity = read_identity(tmp_path, "python")
    assert identity.name == "aspose-widget" and identity.version == "2.0"
    assert identity.floor == ">=3.9"


def test_a_java_project_reports_its_compiler_level_as_the_floor(tmp_path: Path) -> None:
    """Each ecosystem names the floor differently; the façade reads all three, measured.

    The reader calls it `requires_python`, `min_framework` and `runtime_min_version`; a guessed
    key would have produced an empty floor with no error at all.
    """
    (tmp_path / "pom.xml").write_text(POM, encoding="utf-8")
    identity = read_identity(tmp_path, "java")
    assert identity.name == "widget" and identity.version == "3.0"
    assert identity.floor == "17"


def test_a_repository_with_no_manifest_reports_empty_rather_than_guessing(tmp_path: Path) -> None:
    """A fact with no evidence is not written at all, so the façade must not invent one."""
    (tmp_path / "README.md").write_text("# Nothing here\n", encoding="utf-8")
    identity = read_identity(tmp_path, "net")
    assert identity.name == "" and identity.version == "" and identity.floor == ""
