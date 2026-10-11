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
        Fact(
            "identity:repository",
            "identity",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            (Evidence("data/registry.json"),),
        ),
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
    seen: list[tuple[str, str | None, str | None]] = []

    def observe(name: str, version: str | None, *, repository: str | None) -> RegistryObservation:
        seen.append((name, version, repository))
        return RegistryObservation(
            name,
            f"https://pypi.org/pypi/{name}/json",
            True,
            "26.1.0",
            True,
            repository_matched=True,
        )

    monkeypatch.setattr(plugin_module, "observe_pypi", observe)
    [resolved], [probe] = plugin.registry_facts(facts)
    assert seen == [("aspose-3d-foss", "26.1.0", "aspose-3d-foss/Aspose.3D-FOSS-for-Python")]
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
        lambda name, version, repository: RegistryObservation(name, "u", False),
    )
    assert plugin.registry_facts(facts)[0][0].polarity == "CONTRADICTED"
    monkeypatch.setattr(
        plugin_module,
        "observe_pypi",
        lambda name, version, repository: RegistryObservation(
            name, "u", False, error="ConnectError"
        ),
    )
    assert plugin.registry_facts(facts)[0][0].polarity == "UNRESOLVED"
    # A name that exists on PyPI but whose project URLs point elsewhere is another project's
    # package: UNRESOLVED, never SUPPORTED ownership (and not CONTRADICTED either).
    for matched in (False, None):
        monkeypatch.setattr(
            plugin_module,
            "observe_pypi",
            lambda name, version, repository, matched=matched: RegistryObservation(
                name, "u", True, "26.1.0", True, repository_matched=matched
            ),
        )
        [other], _ = plugin.registry_facts(facts)
        assert (other.polarity, other.confidence) == ("UNRESOLVED", 0.5)
        assert "ownership not confirmed" in (other.evidence[1].detail or "")
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


# TC-EXT-01 (G3-W08 cut 2): defects found by review against real repositories. The fixtures are
# trimmed copies of the repository files themselves (aspose-html-foss at bf0f1e7a: a src layout
# with comma-joined specifiers; jazzband-style segment-geospatial at 0d7a4ac1: dynamic
# dependencies read from requirements.txt).
_FIXTURES = Path(__file__).parent / "fixtures"


def _checkout(tmp_path: Path, name: str) -> Path:
    import shutil

    target = tmp_path / name
    shutil.copytree(_FIXTURES / name, target)
    return target


def _tree(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_a_comma_in_a_pep_508_specifier_does_not_split_the_requirement(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "aspose_html_py")
    facts = PythonPlugin().manifest_facts(root, root / "pyproject.toml", _tree(root))
    dependencies = {f.id: f.value for f in facts if f.kind == "dependency"}
    assert dependencies == {
        "dependency:skia-python-87.0-145": "skia-python>=87.0,<145",
        "dependency:optional.js.quickjs-1.19-2": "quickjs>=1.19,<2",
        "dependency:development.test.pytest-8": "pytest>=8",
    }


def test_setup_py_and_setup_cfg_specifiers_keep_their_commas(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\n"
        'setup(name="x-foss", install_requires=["numpy>=1.20,<2", "pillow"])\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "setup.py", ["x/__init__.py"])
    assert [f.value for f in facts if f.kind == "dependency"] == ["numpy>=1.20,<2", "pillow"]
    (tmp_path / "setup.py").unlink()
    (tmp_path / "setup.cfg").write_text(
        "[metadata]\nname = x-foss\n[options]\ninstall_requires =\n    numpy>=1.20,<2\n",
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "setup.cfg", ["x/__init__.py"])
    assert [f.value for f in facts if f.kind == "dependency"] == ["numpy>=1.20,<2"]


def test_a_requirement_pep_508_cannot_parse_is_not_asserted(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x-foss"\ndependencies = ["-r requirements.txt", "numpy>=1,<2"]\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "pyproject.toml", ["x/__init__.py"])
    by_value = {f.value: f.polarity for f in facts if f.kind == "dependency"}
    assert by_value == {"numpy>=1,<2": "SUPPORTED", "-r requirements.txt": "UNRESOLVED"}


def test_a_src_layout_package_is_imported_without_the_src_directory(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "aspose_html_py")
    tree = _tree(root)
    assert package_directories(tree) == ["aspose_html", "aspose_html.dom"]
    facts = PythonPlugin().manifest_facts(root, root / "pyproject.toml", tree)
    imports = [(f.value, f.evidence[0].path) for f in facts if f.kind == "import_path"]
    assert imports == [
        ("aspose_html", "src/aspose_html/__init__.py"),
        ("aspose_html.dom", "src/aspose_html/dom/__init__.py"),
    ]
    # The surface reads the same packages relative to src, so symbols and import paths agree.
    symbols = [
        f.value for f in PythonPlugin().surface_facts(root, tree) if f.kind == "public_symbol"
    ]
    assert symbols
    assert all(not value.startswith("src") for value in symbols)


def test_a_top_level_src_package_is_not_mistaken_for_a_layout(tmp_path: Path) -> None:
    # `src` is a package itself when it has an __init__.py: nothing to strip.
    assert package_directories(["src/__init__.py", "src/pkg/__init__.py"]) == ["src", "src.pkg"]
    assert package_directories(["src/tests/__init__.py"]) == []


def test_dynamic_dependencies_are_unknown_not_verified_zero(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "segment_geospatial")
    facts = PythonPlugin().manifest_facts(root, root / "pyproject.toml", ["samgeo/__init__.py"])
    dependencies = [
        f
        for f in facts
        if f.kind == "dependency"
        and not f.id.startswith(("dependency:optional.", "dependency:dev"))
    ]
    assert [(f.id, f.polarity) for f in dependencies] == [("dependency:dynamic", "UNRESOLVED")]
    assert "dynamic" in (dependencies[0].evidence[0].detail or "")
    assert not any(f.id == "dependency:none" for f in facts)


def test_computed_install_requires_is_unknown_not_verified_zero(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\n"
        'REQUIRED = open("requirements.txt").read().split()\n'
        'setup(name="x-foss", install_requires=REQUIRED)\n',
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "setup.py", ["x/__init__.py"])
    assert [(f.id, f.polarity) for f in facts if f.kind == "dependency"] == [
        ("dependency:dynamic", "UNRESOLVED")
    ]
    (tmp_path / "setup.py").unlink()
    (tmp_path / "setup.cfg").write_text(
        "[metadata]\nname = x-foss\n[options]\ninstall_requires = file: requirements.txt\n",
        encoding="utf-8",
    )
    facts = PythonPlugin().manifest_facts(tmp_path, tmp_path / "setup.cfg", ["x/__init__.py"])
    assert [(f.id, f.polarity) for f in facts if f.kind == "dependency"] == [
        ("dependency:dynamic", "UNRESOLVED")
    ]
