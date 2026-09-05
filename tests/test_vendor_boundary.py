"""The vendor boundary: vendored code is reached through its façade, never imported directly.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2 and `docs/REPOSITORY_LAYOUT.md` §2.1. Vendored code stays
byte-close to its origin so the next pull is a diff rather than a merge, which is only affordable
if the relaxed lint and typing inside the directory cannot leak, and if nothing outside it depends
on the origin's shape. Both are held here rather than by convention.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from support import REPO_ROOT

SURFACE = (
    REPO_ROOT / "src" / "repository_presenter" / "components" / "readme" / "extractors" / "surface"
)
VENDOR = SURFACE / "_vendor"
VENDOR_MODULE = "repository_presenter.components.readme.extractors.surface._vendor"
# The two sibling checkouts are read-only reuse sources; importing either at runtime would make
# this repository depend on a working tree nobody ships (loop-prompt §0).
SIBLINGS = ("readme_agent", "scripts.pipeline", "extraction.", "aspose_extraction.")


def python_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*.py") if "__pycache__" not in path.parts]


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_the_vendor_directory_exists_and_carries_its_origin_in_every_file() -> None:
    files = python_files(VENDOR)
    assert files, "nothing is vendored yet; this control would pass vacuously"
    for path in files:
        if path.name == "__init__.py" and path.parent == VENDOR / "aspose_extraction":
            continue  # the seam this repository cut, written here rather than pulled
        head = path.read_text("utf-8").splitlines()[0]
        assert head.startswith("# Vendored from aspose.org at 16d75e95d4"), path


def test_nothing_outside_the_facade_imports_a_vendored_module() -> None:
    """One way in. A second importer is how a vendor boundary stops being one."""
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in python_files(REPO_ROOT / "src")
        if VENDOR not in path.parents and path.parent != SURFACE
        for module in [imported_modules(path)]
        if any(name.startswith(VENDOR_MODULE) for name in module)
    ]
    assert offenders == [], f"these import vendored code directly: {offenders}"


def test_no_module_imports_a_sibling_checkout_at_runtime() -> None:
    outside_vendor = [
        path for path in python_files(REPO_ROOT / "src") if VENDOR not in path.parents
    ]
    for path in outside_vendor:
        for name in imported_modules(path):
            assert not name.startswith(SIBLINGS), f"{path} imports {name} from a reuse source"


def test_the_linter_relaxations_name_the_vendor_directory_and_nothing_else() -> None:
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text("utf-8"))
    # The formatter is excluded as well as the linter: a reformat would end "byte-close to its
    # origin", which is the whole reason the next pull can be read as a diff.
    excluded = config["tool"]["ruff"]["extend-exclude"]
    assert excluded == [
        "candidates",
        "src/repository_presenter/components/readme/extractors/surface/_vendor",
    ]
    overrides = config["tool"]["mypy"]["overrides"]
    relaxed = [entry for entry in overrides if entry.get("ignore_errors")]
    assert [entry["module"] for entry in relaxed] == [f"{VENDOR_MODULE}.*"]
