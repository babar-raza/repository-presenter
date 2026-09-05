"""The Python plugin: manifest precedence, static parsing, and facts with evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms.python import (
    PythonPlugin,
    package_directories,
    parse_manifests,
    parse_pyproject,
)
from repository_presenter.core.facts import Evidence, Fact

CANARY_TREE = [
    ".github/workflows/publish.yml",
    "LICENSE",
    "README.md",
    "setup.py",
    "aspose/__init__.py",
    "aspose/pydrawing/__init__.py",
    "aspose/threed/__init__.py",
    "aspose/threed/entities/__init__.py",
    "aspose/threed/Scene.py",
    "tests/__init__.py",
    "tests/test_scene.py",
    "docs/releasing.md",
]


def test_parses_pyproject_project_table(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-3d-foss"\nversion = "1.0.0"\n'
        'license = { text = "MIT" }\nrequires-python = ">=3.11"\n',
        encoding="utf-8",
    )
    info = parse_pyproject(tmp_path / "pyproject.toml")
    assert info == {
        "name": "aspose-3d-foss",
        "version": "1.0.0",
        "license": "MIT",
        "requires_python": ">=3.11",
    }


def test_declared_packages_come_from_either_setuptools_shape(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "pyproject.toml").write_text(
        '[project]\nname = "aspose-email-foss"\n[tool.setuptools.packages.find]\n'
        'include = ["aspose.email_foss", "aspose.email_foss.*"]\n',
        encoding="utf-8",
    )
    assert parse_pyproject(nested / "pyproject.toml")["declared_packages"] == "aspose.email_foss"

    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "pyproject.toml").write_text(
        '[project]\nname = "aspose-cells-foss"\n[tool.setuptools]\n'
        'packages = ["aspose", "aspose.cells_foss", "examples"]\n',
        encoding="utf-8",
    )
    assert parse_pyproject(flat / "pyproject.toml")["declared_packages"] == (
        "aspose,aspose.cells_foss,examples"
    )


def test_dynamic_setuptools_version_is_resolved_statically(tmp_path: Path) -> None:
    (tmp_path / "src" / "aspose_pdf").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-pdf-foss-for-python"\ndynamic = ["version"]\n'
        '[tool.setuptools]\npackage-dir = {"" = "src"}\n[tool.setuptools.dynamic]\n'
        'version = {attr = "aspose_pdf._version.__release_version__"}\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "aspose_pdf" / "_version.py").write_text(
        '__release_version__: str = "0.1.0a0"\n', encoding="utf-8"
    )
    assert parse_pyproject(tmp_path / "pyproject.toml")["version"] == "0.1.0a0"


def test_dynamic_version_module_is_never_executed(tmp_path: Path) -> None:
    (tmp_path / "src" / "package").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "package"\ndynamic = ["version"]\n'
        '[tool.setuptools]\npackage-dir = {"" = "src"}\n'
        '[tool.setuptools.dynamic]\nversion = {attr = "package._version.VERSION"}\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "package" / "_version.py").write_text(
        'raise RuntimeError("must not execute")\nVERSION = build_version()\n', encoding="utf-8"
    )
    assert "version" not in parse_pyproject(tmp_path / "pyproject.toml")


def test_setup_cfg_and_setup_py_are_fallbacks_only(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text(
        "[metadata]\nname = cfg-name\nversion = 2.0\n[options]\npython_requires = >=3.9\n",
        encoding="utf-8",
    )
    (tmp_path / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="py-name", version="1.2.3")\n', encoding="utf-8"
    )
    parsed = parse_manifests(tmp_path)
    assert list(parsed) == ["setup.cfg"]
    assert parsed["setup.cfg"] == {"name": "cfg-name", "version": "2.0", "requires_python": ">=3.9"}

    (tmp_path / "setup.cfg").unlink()
    assert parse_manifests(tmp_path) == {"setup.py": {"name": "py-name", "version": "1.2.3"}}

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "toml-name"\n', encoding="utf-8")
    assert list(parse_manifests(tmp_path)) == ["pyproject.toml"]


def test_package_directories_come_from_the_tree_in_depth_order() -> None:
    assert package_directories(CANARY_TREE) == ["aspose", "aspose.pydrawing", "aspose.threed"]


def test_plugin_detects_the_governing_manifest(tmp_path: Path) -> None:
    plugin = PythonPlugin()
    assert plugin.detect_manifest(tmp_path) is None
    (tmp_path / "setup.py").write_text("", encoding="utf-8")
    assert plugin.detect_manifest(tmp_path) == tmp_path / "setup.py"
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    assert plugin.detect_manifest(tmp_path) == tmp_path / "pyproject.toml"


def test_plugin_facts_for_a_canary_shaped_repository(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup, find_packages\n"
        'setup(name="aspose-3d-foss", version="26.1.0", packages=find_packages(),\n'
        '      python_requires=">=3.7", classifiers=["Programming Language :: Python :: 3.12"])\n',
        encoding="utf-8",
    )
    plugin = PythonPlugin()
    facts = plugin.manifest_facts(tmp_path, tmp_path / "setup.py", CANARY_TREE)
    by_id = {fact.id: fact for fact in facts}
    assert by_id["package:name"].value == "aspose-3d-foss"
    assert by_id["package:name"].evidence[0].path == "setup.py"
    assert by_id["package:version"].value == "26.1.0"
    assert by_id["package:python_requires"].value == ">=3.7"
    assert by_id["package:python_versions"].value == "3.12"
    install = by_id["install_command:pip"]
    assert (install.value, install.polarity, install.confidence) == (
        "pip install aspose-3d-foss",
        "UNRESOLVED",
        0.5,
    )
    assert [f.value for f in facts if f.kind == "import_path"] == [
        "aspose",
        "aspose.pydrawing",
        "aspose.threed",
    ]
    assert by_id["import_path:aspose.threed"].evidence[0].path == "aspose/threed/__init__.py"


def test_declared_packages_take_precedence_over_the_tree(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-cells-foss"\n[tool.setuptools]\n'
        'packages = ["aspose", "aspose.cells_foss"]\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "pyproject.toml", CANARY_TREE)
    import_paths = [f for f in facts if f.kind == "import_path"]
    assert [f.value for f in import_paths] == ["aspose", "aspose.cells_foss"]
    assert import_paths[0].evidence[0].path == "pyproject.toml"


def test_declared_dependencies_become_facts(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-x-foss"\ndependencies = ["numpy>=1.20", "pillow"]\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "pyproject.toml", ["x/__init__.py"])
    dependencies = [(f.id, f.value, f.evidence[0].path) for f in facts if f.kind == "dependency"]
    assert dependencies == [
        ("dependency:numpy-1.20", "numpy>=1.20", "pyproject.toml"),
        ("dependency:pillow", "pillow", "pyproject.toml"),
    ]


def test_registry_facts_reissue_the_install_claim_with_the_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from repository_presenter.components.readme.extractors.platforms import python as plugin_module
    from repository_presenter.components.readme.extractors.platforms.python_registry import (
        RegistryObservation,
    )

    plugin = PythonPlugin()
    facts = [
        Fact("package:name", "package", "aspose-3d-foss", (Evidence("setup.py"),)),
        Fact("package:version", "package", "26.1.0", (Evidence("setup.py"),)),
        Fact(
            "install_command:pip",
            "install_command",
            "pip install aspose-3d-foss",
            (Evidence("setup.py", "pending"),),
            polarity="UNRESOLVED",
            confidence=0.5,
        ),
    ]
    seen: list[tuple[str, str | None]] = []

    def observe(name: str, version: str | None) -> RegistryObservation:
        seen.append((name, version))
        return RegistryObservation(name, f"https://pypi.org/pypi/{name}/json", True, "26.1.0", True)

    monkeypatch.setattr(plugin_module, "observe_pypi", observe)
    [resolved], [probe] = plugin.registry_facts(facts)
    assert seen == [("aspose-3d-foss", "26.1.0")]
    assert (resolved.id, resolved.polarity, resolved.confidence) == (
        "install_command:pip",
        "SUPPORTED",
        1.0,
    )
    assert resolved.evidence[1].path == "https://pypi.org/pypi/aspose-3d-foss/json"
    assert "manifest version published" in resolved.evidence[1].detail
    # The version the registry happens to hold today is the probe's, never the fact's: hashing
    # it reopened EXTRACTING whenever PyPI published (section 27.2 RC7).
    assert "26.1.0" not in resolved.evidence[1].detail
    assert (probe.kind, probe.target, probe.outcome) == (
        "package_registry",
        "https://pypi.org/pypi/aspose-3d-foss/json",
        "FOUND",
    )
    assert probe.observation == "latest 26.1.0"

    monkeypatch.setattr(
        plugin_module,
        "observe_pypi",
        lambda name, version: RegistryObservation(name, "u", False),
    )
    assert plugin.registry_facts(facts)[0][0].polarity == "CONTRADICTED"
    monkeypatch.setattr(
        plugin_module,
        "observe_pypi",
        lambda name, version: RegistryObservation(name, "u", False, error="ConnectError"),
    )
    assert plugin.registry_facts(facts)[0][0].polarity == "UNRESOLVED"
    # No install claim to resolve means no fact re-issued and no read made.
    assert plugin.registry_facts(facts[:1]) == ([], [])


def test_the_dependency_snapshot_records_verified_zero_and_extras_by_bucket(
    tmp_path: Path,
) -> None:
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\n"
        'setup(name="aspose-x-foss", install_requires=[], '
        'extras_require={"dev": ["pytest>=7.0.0"], "viz": ["matplotlib"]})\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "setup.py", ["x/__init__.py"])
    snapshot = [
        (f.id, f.value, f.evidence[0].path, f.evidence[0].detail)
        for f in facts
        if f.kind == "dependency"
    ]
    assert snapshot == [
        ("dependency:none", "none", "setup.py", "the `install_requires` list is empty"),
        (
            "dependency:development.dev.pytest-7.0.0",
            "pytest>=7.0.0",
            "setup.py",
            "extra 'dev' declared",
        ),
        ("dependency:optional.viz.matplotlib", "matplotlib", "setup.py", "extra 'viz' declared"),
    ]
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-x-foss"\n[project.optional-dependencies]\ntest = ["pytest"]\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "pyproject.toml", ["x/__init__.py"])
    snapshot = [(f.id, f.evidence[0].detail) for f in facts if f.kind == "dependency"]
    assert snapshot == [
        ("dependency:none", "no `project.dependencies` is declared"),
        ("dependency:development.test.pytest", "extra 'test' declared"),
    ]
