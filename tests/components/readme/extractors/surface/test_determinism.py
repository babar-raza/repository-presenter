"""The vendored engine's reading is a function of the tree, not of the order it was walked.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2. A candidate's facts are content-addressed evidence, so a
surface reader that returned a different set - or the same set in a different order - for the same
tree would move a sealed bundle without any input changing. Filesystem iteration order is the
usual way that happens, and it varies by platform, so it is fixed here rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter_language_pack import get_parser

from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols

MODULES = {
    "zeta.cs": "namespace P { public class Zeta { public void Go() {} } }",
    "alpha.cs": "namespace P { public class Alpha { public string Name { get; set; } } }",
    "middle.cs": "namespace P { public enum Middle { One, Two } }",
}


def _package(root: Path, order: list[str]) -> Path:
    package = root / "src" / "P"
    package.mkdir(parents=True)
    for name in order:
        (package / name).write_text(MODULES[name], encoding="utf-8")
    return package


def _read(root: Path, package: Path) -> list[tuple[str, str, int]]:
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, root, "p")
    return [(s.value, s.symbol_kind, s.line) for s in symbols]


def test_the_same_tree_reads_the_same_twice(tmp_path: Path) -> None:
    package = _package(tmp_path, list(MODULES))
    assert _read(tmp_path, package) == _read(tmp_path, package)


def test_the_reading_does_not_depend_on_the_order_the_files_were_written(tmp_path: Path) -> None:
    """Two trees with the same content, written in opposite order, read identically."""
    forward = tmp_path / "forward"
    backward = tmp_path / "backward"
    first = _read(forward, _package(forward, list(MODULES)))
    second = _read(backward, _package(backward, list(reversed(list(MODULES)))))
    assert first, "the fixture produced no symbols"
    assert first == second


def test_every_symbol_carries_the_line_it_was_declared_on(tmp_path: Path) -> None:
    package = _package(tmp_path, list(MODULES))
    for value, _kind, line in _read(tmp_path, package):
        assert line > 0, value
