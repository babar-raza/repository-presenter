"""The parity control: the vendored engine is held to this repository's own Python extractor.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2 - "the extractor's output is admitted only through the
parity control and the contract's checks; origin never makes a fact true." Python is the one
language where both a vendored reader and a first-party reader exist, so it is where the vendored
engine can be checked against something already trusted. What the control asserts is not that the
two agree everywhere - they read different things on purpose - but that every difference falls in
a class named here.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter_language_pack import get_parser

from repository_presenter.components.readme.extractors.platforms.python_surface import (
    inspect_public_surface,
)
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols

PACKAGE = '''
"""A small product package."""


class Scene:
    """The root of a scene graph."""

    def save(self, path):
        """Write the scene."""
        return None

    def _internal(self):
        return None


class Node:
    """A node."""

    def attach(self, child):
        return child


class _Private:
    pass


def helper(value):
    """A module-level function."""
    return value
'''


def _package(root: Path) -> Path:
    package = root / "aspose" / "threed"
    package.mkdir(parents=True)
    (root / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text(PACKAGE, encoding="utf-8")
    return package


def test_the_two_readers_agree_on_every_public_class_and_method(tmp_path: Path) -> None:
    """Both read the same tree; only their scopes differ, and the differences are named."""
    _package(tmp_path)
    vendored = surface_symbols(
        get_parser("python"), "python", tmp_path / "aspose", tmp_path, "threed"
    )
    own = inspect_public_surface(tmp_path, ["aspose"])

    def leaf(value: str) -> str:
        return value.rsplit(".", 1)[-1]

    from_vendor = {leaf(symbol.value) for symbol in vendored}
    classes = {leaf(s.qualified_name) for s in own.symbols if s.kind == "class"}
    methods = {leaf(s.qualified_name) for s in own.symbols if s.kind == "method"}
    assert classes and methods, "the first-party reader found nothing; the fixture is wrong"

    # Every public class and method the trusted reader found, the vendored engine found too.
    assert classes <= from_vendor, sorted(classes - from_vendor)
    assert methods <= from_vendor, sorted(methods - from_vendor)
    # And neither invents a private name.
    assert "_Private" not in from_vendor and "_internal" not in from_vendor


def test_the_differences_are_modules_and_module_level_functions(tmp_path: Path) -> None:
    """The two named classes of difference, measured rather than assumed.

    The first-party reader emits a `module` symbol per module and the vendored engine does not;
    the vendored engine reports a module-level function under the file it was declared in, where
    the first-party reader gives it a package-qualified name. Measured on the sealed canary
    (2026-09-06): 931 of 953 final segments in both, 7 vendored-only - dunders and members the
    first-party reader excludes - and 22 first-party-only, of which the sample was all modules.
    """
    _package(tmp_path)
    vendored = surface_symbols(
        get_parser("python"), "python", tmp_path / "aspose", tmp_path, "threed"
    )
    own = inspect_public_surface(tmp_path, ["aspose"])

    def leaf(value: str) -> str:
        return value.rsplit(".", 1)[-1]

    from_vendor = {leaf(symbol.value) for symbol in vendored}
    only_first_party = {leaf(s.qualified_name) for s in own.symbols} - from_vendor
    kinds = {s.kind for s in own.symbols if leaf(s.qualified_name) in only_first_party}
    assert kinds <= {"module", "function"}, sorted(kinds)
