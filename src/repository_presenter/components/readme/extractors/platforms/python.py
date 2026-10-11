"""The Python platform plugin: manifest facts from pyproject.toml, setup.cfg, and setup.py.

Adapted from the legacy Python manifest parser, itself adapted from a production reference tuned
against the same Aspose FOSS corpus. pyproject.toml is authoritative when it yields a name;
setup.cfg and setup.py are consulted only when it is absent or incomplete. Nothing is executed:
setup.py is read through the AST and only literal keywords of a proven setuptools call count.
Import paths come from the packages the manifest declares or, failing that, from the package
directories the tree inventory proves.
"""

from __future__ import annotations

import ast
import json
import tomllib
from collections.abc import Sequence
from configparser import ConfigParser
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement

from repository_presenter.components.readme.extractors.platforms.python_examples import (
    verify_python_examples,
)
from repository_presenter.components.readme.extractors.platforms.python_format_declarations import (
    format_declarations,
)
from repository_presenter.components.readme.extractors.platforms.python_formats import (
    format_claims,
)
from repository_presenter.components.readme.extractors.platforms.python_registry import (
    observe_pypi,
)
from repository_presenter.components.readme.extractors.platforms.python_setup_py import (
    parse_setup_py,
)
from repository_presenter.components.readme.extractors.platforms.python_surface import (
    inspect_public_surface,
    public_symbol_facts,
)
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import (
    Evidence,
    Fact,
    fact_id,
)
from repository_presenter.core.package_registry import install_verdict
from repository_presenter.core.probes import ProbeRecord

MANIFEST_NAMES = ("pyproject.toml", "setup.cfg", "setup.py")
_NON_PRODUCT_TOP_LEVEL = frozenset({"tests", "test", "docs", "examples", "pyi", "scripts", "build"})
_MAX_IMPORT_PATH_DEPTH = 2
# The conventional "src layout": packages live under `src/`, which is a directory, not a package.
_SOURCE_LAYOUT_DIRECTORY = "src"
# Extras whose requirements serve development, not users of the package.
_DEVELOPMENT_EXTRAS = frozenset({"dev", "develop", "development", "test", "tests", "testing"})
_NOT_DECLARED = {
    "pyproject.toml": "no `project.dependencies` is declared",
    "setup.cfg": "no `options.install_requires` is declared",
    "setup.py": "no `install_requires` is declared",
}
_DYNAMIC_DEPENDENCIES = (
    "`dependencies` is declared dynamic in pyproject.toml, so the requirements are computed at "
    "build time and not statically known"
)


def _requirement_fact(identifier: str, requirement: str, path: str, detail: str) -> Fact:
    """A dependency fact for one declared requirement string.

    The string is taken whole: a PEP 508 specifier is ``numpy>=1.20,<2``, one requirement with
    two clauses, never two requirements. One a PEP 508 parser rejects (a ``-r file`` line, a
    URL typo) is recorded but not asserted, so a README never states it as a package.
    """
    try:
        Requirement(requirement)
    except InvalidRequirement:
        return Fact(
            identifier,
            "dependency",
            requirement,
            (Evidence(path, f"{detail}; not a valid PEP 508 requirement"),),
            polarity="UNRESOLVED",
            confidence=0.5,
        )
    return Fact(identifier, "dependency", requirement, (Evidence(path, detail),))


def _literal_assignment(path: Path, name: str) -> str | None:
    """Read one module-level string assignment without importing repository code."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        value = None
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is None:
            continue
        try:
            literal = ast.literal_eval(value)
        except (TypeError, ValueError):
            return None
        return literal if isinstance(literal, str) and literal.strip() else None
    return None


def _dynamic_setuptools_version(pyproject_path: Path, data: dict[str, Any]) -> str | None:
    """Resolve a PEP 621 setuptools ``version.attr`` from static source only."""
    project = data.get("project", {})
    if "version" not in project.get("dynamic", []):
        return None
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    version_cfg = setuptools_cfg.get("dynamic", {}).get("version", {})
    attr = version_cfg.get("attr") if isinstance(version_cfg, dict) else None
    if not isinstance(attr, str) or "." not in attr:
        return None
    module_name, attribute_name = attr.rsplit(".", 1)
    if not module_name or not attribute_name.isidentifier():
        return None
    package_dirs = setuptools_cfg.get("package-dir", {})
    source_root = ""
    if isinstance(package_dirs, dict):
        configured = package_dirs.get("")
        if isinstance(configured, str):
            source_root = configured
    module_path = (pyproject_path.parent / source_root).joinpath(*module_name.split("."))
    for candidate in (module_path.with_suffix(".py"), module_path / "__init__.py"):
        version = _literal_assignment(candidate, attribute_name)
        if version is not None:
            return version
    return None


def parse_pyproject(pyproject_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8", errors="replace"))
    project = data.get("project", {})
    if project.get("name"):
        info["name"] = project["name"]
    if project.get("version"):
        info["version"] = project["version"]
    elif dynamic_version := _dynamic_setuptools_version(pyproject_path, data):
        info["version"] = dynamic_version
    license_value = project.get("license", "")
    if isinstance(license_value, dict):
        license_value = license_value.get("text", license_value.get("file", ""))
    if license_value:
        info["license"] = str(license_value)
    if project.get("requires-python"):
        info["requires_python"] = project["requires-python"]
    dependencies = [d for d in project.get("dependencies", []) if isinstance(d, str) and d.strip()]
    dynamic = project.get("dynamic", [])
    if dependencies:
        info["dependencies"] = json.dumps([d.strip() for d in dependencies])
    elif isinstance(dynamic, list) and "dependencies" in dynamic:
        # PEP 621: a field listed in `dynamic` is computed by the build backend. "Not written
        # here" is not "none": the requirements exist, and only a build would reveal them.
        info["dependencies_dynamic"] = _DYNAMIC_DEPENDENCIES
    elif "dependencies" in project:
        info["dependency_evidence"] = "the `project.dependencies` list is empty"
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        buckets = {
            str(extra): [d.strip() for d in reqs if isinstance(d, str) and d.strip()]
            for extra, reqs in optional.items()
            if isinstance(reqs, list)
        }
        if any(buckets.values()):
            info["extras"] = json.dumps({k: v for k, v in buckets.items() if v}, sort_keys=True)
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    packages_cfg = setuptools_cfg.get("packages", [])
    if isinstance(packages_cfg, dict):
        candidates = packages_cfg.get("find", {}).get("include", [])
    elif isinstance(packages_cfg, list):
        candidates = packages_cfg
    else:
        candidates = []
    declared = [
        candidate
        for candidate in candidates
        if isinstance(candidate, str) and candidate and not candidate.endswith(("*", ".*"))
    ]
    if declared:
        info["declared_packages"] = ",".join(declared)
    return info


def parse_setup_cfg(setup_cfg_path: Path) -> dict[str, str]:
    parser = ConfigParser()
    parser.read(setup_cfg_path, encoding="utf-8")
    info: dict[str, str] = {}
    if parser.has_section("metadata"):
        for source, target in (("name", "name"), ("version", "version"), ("license", "license")):
            value = parser.get("metadata", source, fallback="").strip()
            if value:
                info[target] = value
    if parser.has_section("options"):
        requires_python = parser.get("options", "python_requires", fallback="").strip()
        if requires_python:
            info["requires_python"] = requires_python
        if parser.has_option("options", "install_requires"):
            raw = parser.get("options", "install_requires")
            declared = _requirement_lines(raw)
            if raw.strip().startswith(("file:", "attr:")):
                info["dependencies_dynamic"] = (
                    "`options.install_requires` reads its requirements from "
                    f"`{raw.strip().split(maxsplit=1)[0]}`, which is not statically known"
                )
            elif declared:
                info["dependencies"] = json.dumps(declared)
            else:
                info["dependency_evidence"] = "the `options.install_requires` list is empty"
    if parser.has_section("options.extras_require"):
        buckets = {
            extra: _requirement_lines(parser.get("options.extras_require", extra))
            for extra in parser.options("options.extras_require")
        }
        if any(buckets.values()):
            info["extras"] = json.dumps({k: v for k, v in buckets.items() if v}, sort_keys=True)
    return info


def _requirement_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def parse_manifests(root: Path) -> dict[str, dict[str, str]]:
    """Metadata per manifest file, in authority order, for every manifest present at the root."""
    parsed: dict[str, dict[str, str]] = {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        parsed["pyproject.toml"] = parse_pyproject(pyproject)
    if not any(info.get("name") for info in parsed.values()) and (root / "setup.cfg").is_file():
        parsed["setup.cfg"] = parse_setup_cfg(root / "setup.cfg")
    if not any(info.get("name") for info in parsed.values()) and (root / "setup.py").is_file():
        parsed["setup.py"] = parse_setup_py(root / "setup.py")
    return parsed


def package_locations(tree_paths: list[str]) -> list[tuple[str, str]]:
    """``(dotted import path, repository-relative directory)`` per proven package directory.

    Shallowest first. In a src layout (``src/`` holds packages and is itself no package) the
    import path omits ``src``: ``src/pkg/__init__.py`` is imported as ``pkg``, which is also the
    name the public surface reads its symbols under.
    """
    in_tree = set(tree_paths)
    src_layout = f"{_SOURCE_LAYOUT_DIRECTORY}/__init__.py" not in in_tree
    found: dict[str, str] = {}
    for path in tree_paths:
        parts = path.split("/")
        if parts[-1] != "__init__.py" or len(parts) < 2:
            continue
        directory = parts[:-1]
        package = (
            directory[1:] if src_layout and directory[0] == _SOURCE_LAYOUT_DIRECTORY else directory
        )
        if not package or len(package) > _MAX_IMPORT_PATH_DEPTH:
            continue
        if package[0] in _NON_PRODUCT_TOP_LEVEL or not all(part.isidentifier() for part in package):
            continue
        found.setdefault(".".join(package), "/".join(directory))
    ordered = sorted(found, key=lambda dotted: (dotted.count("."), dotted))
    return [(dotted, found[dotted]) for dotted in ordered]


def package_directories(tree_paths: list[str]) -> list[str]:
    """Dotted import paths of the package directories the tree proves, shallowest first."""
    return [dotted for dotted, _ in package_locations(tree_paths)]


class PythonPlugin:
    """Python packages: manifest facts and the import paths the tree proves."""

    ecosystem = "python"
    manifest_globs: tuple[str, ...] = MANIFEST_NAMES
    source_suffixes = frozenset({".py"})

    def detect_manifest(self, root: Path) -> Path | None:
        for name in MANIFEST_NAMES:
            candidate = root / name
            if candidate.is_file():
                return candidate
        return None

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        package_dirs = [directory for _, directory in package_locations(tree_paths)]
        return public_symbol_facts(inspect_public_surface(root, package_dirs))

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the pip install claim against PyPI; the fact keeps its ID and gains evidence.

        The read's status, its duration, and the registry's current latest version go to the
        probe record instead of the evidence, so a release published upstream cannot reopen a
        stage for a repository that did not change (section 27.2 RC7).
        """
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get("install_command:pip")
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        version = by_id.get("package:version")
        repository = next((f.value for f in facts if f.id == "identity:repository"), None)
        observation = observe_pypi(
            name.value, version.value if version else None, repository=repository
        )
        polarity, confidence, detail = install_verdict(
            conclusive=observation.error is None,
            published=observation.found,
            repository_matched=observation.repository_matched,
            summary=observation.summary,
        )
        return [
            Fact(
                install.id,
                install.kind,
                install.value,
                (
                    Evidence(
                        install.evidence[0].path, "distribution name declared by the manifest"
                    ),
                    Evidence(observation.url, detail),
                ),
                polarity=polarity,
                confidence=confidence,
            )
        ], [observation.probe]

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        return verify_python_examples(root, tree_paths, candidates, workspace)

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        return format_claims(code)

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        return format_declarations(root, tree_paths)

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        facts: list[Fact] = []
        merged: dict[str, str] = {}
        sources: dict[str, str] = {}
        for filename, info in parse_manifests(root).items():
            for key, value in info.items():
                if key not in merged:
                    merged[key] = value
                    sources[key] = filename

        def add(kind: Any, slug: str, key: str, detail: str) -> None:
            if key in merged:
                facts.append(
                    Fact(
                        fact_id(kind, slug),
                        kind,
                        merged[key],
                        (Evidence(sources[key], detail),),
                    )
                )

        add("package", "name", "name", "distribution name declared by the manifest")
        add("package", "version", "version", "version declared by the manifest")
        add("package", "python_requires", "requires_python", "python_requires declared")
        add("package", "python_versions", "python_classifier_versions", "Python classifiers")
        add("package", "license", "license", "license declared by the manifest")
        # The dependency snapshot (README_CONTRACT.md section 2 row 9): every required
        # requirement, or the verified-zero marker citing the manifest clause that proves it,
        # then each extra's requirements in the optional or development bucket.
        for requirement in json.loads(merged.get("dependencies", "[]")):
            facts.append(
                _requirement_fact(
                    fact_id("dependency", requirement),
                    requirement,
                    sources["dependencies"],
                    "install requirement declared",
                )
            )
        if "dependencies_dynamic" in merged:
            facts.append(
                Fact(
                    fact_id("dependency", "dynamic"),
                    "dependency",
                    "dynamic",
                    (Evidence(sources["dependencies_dynamic"], merged["dependencies_dynamic"]),),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )
        elif "dependencies" not in merged and "name" in merged:
            # A parsed manifest that declares no requirement proves verified-zero: an empty
            # list when the manifest spells one out, else the absence of the declaration.
            path = sources.get("dependency_evidence", sources["name"])
            clause = merged.get("dependency_evidence") or _NOT_DECLARED[sources["name"]]
            facts.append(
                Fact(fact_id("dependency", "none"), "dependency", "none", (Evidence(path, clause),))
            )
        for extra, requirements in json.loads(merged.get("extras", "{}")).items():
            bucket = "development" if extra.lower() in _DEVELOPMENT_EXTRAS else "optional"
            for requirement in requirements:
                facts.append(
                    _requirement_fact(
                        fact_id("dependency", bucket, extra, requirement),
                        requirement,
                        sources["extras"],
                        f"extra '{extra}' declared",
                    )
                )

        if "name" in merged:
            facts.append(
                Fact(
                    fact_id("install_command", "pip"),
                    "install_command",
                    f"pip install {merged['name']}",
                    (Evidence(sources["name"], "package-registry observation pending"),),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )

        declared = merged.get("declared_packages", "")
        locations = (
            [(dotted, "") for dotted in declared.split(",")]
            if declared
            else package_locations(tree_paths)
        )
        for dotted, directory in locations:
            evidence_path = sources["declared_packages"] if declared else f"{directory}/__init__.py"
            facts.append(
                Fact(
                    fact_id("import_path", dotted),
                    "import_path",
                    dotted,
                    (Evidence(evidence_path, "package declared" if declared else "package dir"),),
                )
            )
        return facts


# The registry discovers a plugin by module name and this attribute; it never lists plugins
# (docs/REPOSITORY_LAYOUT.md section 2.1, RESEARCH_AND_GUIDELINES.md section 29.6 E3).
PLUGIN = PythonPlugin()
