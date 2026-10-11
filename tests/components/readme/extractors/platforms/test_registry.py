"""Plugins are found through the registry; an unknown ecosystem is a configuration failure."""

from __future__ import annotations

import re
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

import pytest

from repository_presenter.components.readme.extractors import platforms as _platforms_package
from repository_presenter.components.readme.extractors.platforms.python import PythonPlugin
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.errors import ConfigError


def _package_module_names() -> list[str]:
    """Every module beside `registry.py` itself in `extractors/platforms/`, ecosystem or not."""
    directory = str(Path(_platforms_package.__file__).parent)
    return sorted(info.name for info in iter_modules([directory]) if info.name != "registry")


def test_python_is_the_first_registered_plugin() -> None:
    # G4-W17 item 6: no lane touches this file to add its own ecosystem's name - discovery finds
    # each without this module listing any, so the assertion checks a property, never a roster.
    assert "python" in known_ecosystems()
    assert known_ecosystems() == tuple(sorted(known_ecosystems()))
    plugin = plugin_for("python")
    assert isinstance(plugin, PythonPlugin)
    assert plugin.manifest_globs == ("pyproject.toml", "setup.cfg", "setup.py")
    assert plugin.source_suffixes == frozenset({".py"})
    assert [(c.direction, c.extension) for c in plugin.format_claims('s.save("a.glb")\n')] == [
        ("output", ".glb")
    ]


def test_unknown_ecosystem_fails_closed() -> None:
    with pytest.raises(ConfigError, match="no platform plugin registered for ecosystem 'cobol'"):
        plugin_for("cobol")


def test_a_plugin_is_discovered_by_module_name_and_its_plugin_attribute() -> None:
    """Adding an ecosystem is adding its file; this registry never lists plugins, and neither
    does this test (G4-W17 item 6) - every module beside `registry.py` is read from the package
    directory itself, so a lane's own helper module (python_surface, typescript_barrel,
    cpp_examples, and the rest) needs no name added here to stay proven not an ecosystem.
    """
    from repository_presenter.components.readme.extractors.platforms import python

    assert python.PLUGIN is plugin_for("python")
    assert plugin_for("python") is plugin_for("python")  # resolved once, then cached
    ecosystems = known_ecosystems()
    for name in _package_module_names():
        module = import_module(
            f"repository_presenter.components.readme.extractors.platforms.{name}"
        )
        if hasattr(module, "PLUGIN"):
            assert name in ecosystems
        else:
            assert name not in ecosystems
            with pytest.raises(ConfigError, match=re.escape(repr(name))):
                plugin_for(name)


# TC-EXT-01 (G3-W08 cut 2): manifest discovery filtered on the ABSOLUTE path, so a checkout that
# merely sat under a directory called build, out, lib or bin (a CI workspace, a user's `~/out`)
# lost every manifest fact. Trimmed real manifests: aspose cells-ts (package.json), 3d-java
# (pom.xml), 3d-net (Aspose.ThreeD.csproj), email-cpp (CMakeLists.txt).
_MANIFESTS = Path(__file__).parent / "fixtures" / "manifests"


@pytest.mark.parametrize(
    ("ecosystem", "fixture", "manifest", "ancestor"),
    [
        ("typescript", "ts", "package.json", "build"),
        ("typescript", "ts", "package.json", "lib"),
        ("typescript", "ts", "package.json", "dist"),
        ("java", "java", "pom.xml", "build"),
        ("java", "java", "pom.xml", "out"),
        ("java", "java", "pom.xml", "target"),
        ("net", "net", "Aspose.ThreeD.csproj", "bin"),
        ("net", "net", "Aspose.ThreeD.csproj", "obj"),
        ("cpp", "cpp", "CMakeLists.txt", "build"),
        ("cpp", "cpp", "CMakeLists.txt", "out"),
    ],
)
def test_a_checkout_under_a_build_named_directory_keeps_its_manifest(
    tmp_path: Path, ecosystem: str, fixture: str, manifest: str, ancestor: str
) -> None:
    import shutil

    checkout = tmp_path / ancestor / "workspace" / "repo"
    shutil.copytree(_MANIFESTS / fixture, checkout)
    assert plugin_for(ecosystem).detect_manifest(checkout) == checkout / manifest
    # Negative control: the same file INSIDE the repository's own build output is not a manifest.
    nested = tmp_path / "other" / "repo"
    (nested / ancestor / "copy").mkdir(parents=True)
    shutil.copy(_MANIFESTS / fixture / manifest, nested / ancestor / "copy" / manifest)
    assert plugin_for(ecosystem).detect_manifest(nested) is None


def test_the_typescript_entry_barrel_ignores_directories_above_the_package(
    tmp_path: Path,
) -> None:
    from repository_presenter.components.readme.extractors.platforms.typescript_barrel import (
        entry_barrel,
    )

    package = tmp_path / "samples" / "docs" / "pkg"
    package.mkdir(parents=True)
    (package / "package.json").write_text('{"name": "excel-cells"}', encoding="utf-8")
    (package / "index.ts").write_text('export * from "./workbook";\n', encoding="utf-8")
    (package / "workbook.ts").write_text("export class Workbook {}\n", encoding="utf-8")
    assert entry_barrel(package) == package / "index.ts"


# TC-EXT-01: a package NAME found on a registry is not ownership. Every registry-reading plugin
# asks the façade about THIS repository, and a published distribution nothing corroborates is
# UNRESOLVED - never SUPPORTED, so the README cannot tell a reader to install another project.
@pytest.mark.parametrize("ecosystem", ["typescript", "go", "java", "net", "rust"])
@pytest.mark.parametrize("matched", [False, None])
def test_a_published_name_that_nothing_ties_to_the_repository_is_not_a_supported_install(
    monkeypatch: pytest.MonkeyPatch, ecosystem: str, matched: bool | None
) -> None:
    from repository_presenter.components.readme.extractors.surface import registry as facade
    from repository_presenter.core.ecosystems import spec_for
    from repository_presenter.core.facts import Evidence, Fact

    plugin = plugin_for(ecosystem)
    module = import_module(type(plugin).__module__)
    asked: list[dict[str, object]] = []

    def observe(eco: str, name: str, **kwargs: object) -> facade.RegistryObservation:
        asked.append(kwargs)
        return facade.RegistryObservation(
            "registry",
            name,
            True,
            False,
            "https://registry.example/x",
            "api",
            "live_probe",
            repository_matched=matched,
        )

    monkeypatch.setattr(module, "observe", observe)
    facts = [
        Fact("identity:repository", "identity", "owner/name", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "taken-name", (Evidence("manifest"),)),
        Fact(
            spec_for(ecosystem).install_fact_id,
            "install_command",
            "install taken-name",
            (Evidence("manifest", "pending"),),
            polarity="UNRESOLVED",
            confidence=0.5,
        ),
    ]
    [resolved], [probe] = plugin.registry_facts(facts)
    assert asked == [{"repository": "owner/name"}]
    assert (resolved.polarity, resolved.confidence) == ("UNRESOLVED", 0.5)
    assert "ownership not confirmed" in (resolved.evidence[-1].detail or "")
    assert probe.outcome == "UNRESOLVED"
