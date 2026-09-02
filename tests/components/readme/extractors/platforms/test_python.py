"""The Python plugin: manifest precedence, static parsing, and facts with evidence."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms.python import (
    PythonPlugin,
    package_directories,
    parse_manifests,
    parse_pyproject,
)

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
