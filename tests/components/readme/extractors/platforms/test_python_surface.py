"""The static public surface: definitions, __all__, re-exports with provenance, nothing guessed."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms.python_surface import (
    PublicSymbol,
    inspect_public_surface,
    public_symbol_facts,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _package(tmp_path: Path) -> Path:
    _write(
        tmp_path,
        "pkg/__init__.py",
        "from .widget import Widget, _Hidden\nfrom .factory import make, other\n"
        "from .sub import *\nfrom . import sub\n__all__ = ['Widget', 'make', 'sub']\n",
    )
    _write(
        tmp_path,
        "pkg/widget.py",
        "class Widget:\n    def render(self):\n        pass\n\n    def _hide(self):\n"
        "        pass\n\n    @property\n    def size(self):\n        return 1\n\n"
        "    def render(self):\n        pass\n\nclass _Hidden:\n    def visible(self):\n"
        "        pass\n",
    )
    _write(
        tmp_path, "pkg/factory.py", "def make():\n    return Widget()\n\ndef other():\n    pass\n"
    )
    _write(tmp_path, "pkg/sub/__init__.py", "from .leaf import Leaf\n")
    _write(tmp_path, "pkg/sub/leaf.py", "class Leaf:\n    pass\n")
    _write(tmp_path, "pkg/_private.py", "class Exposed:\n    pass\n")
    _write(tmp_path, "pkg/tests/test_widget.py", "class NotPublic:\n    pass\n")
    return tmp_path


def test_definitions_all_and_reexports_are_inventoried_without_importing(tmp_path: Path) -> None:
    surface = inspect_public_surface(_package(tmp_path), ["pkg"])
    by_name = {symbol.qualified_name: symbol for symbol in surface.symbols}

    assert sorted(by_name) == [
        "pkg",
        "pkg.Widget",
        "pkg.factory",
        "pkg.factory.make",
        "pkg.factory.other",
        "pkg.make",
        "pkg.sub",
        "pkg.sub.Leaf",
        "pkg.sub.leaf",
        "pkg.sub.leaf.Leaf",
        "pkg.widget",
        "pkg.widget.Widget",
        "pkg.widget.Widget.render",
        "pkg.widget.Widget.size",
    ]
    assert by_name["pkg.widget.Widget.render"] == PublicSymbol(
        "pkg.widget.Widget.render", "pkg.widget", "render", "method", "pkg/widget.py", 2, "name"
    )
    assert by_name["pkg.widget.Widget.size"].kind == "method"
    assert "pkg.widget.Widget._hide" not in by_name
    assert "pkg.widget._Hidden.visible" not in by_name
    assert by_name["pkg.Widget"] == PublicSymbol(
        "pkg.Widget",
        "pkg",
        "Widget",
        "class",
        "pkg/__init__.py",
        1,
        "reexport",
        "pkg.widget.Widget",
    )
    assert by_name["pkg.make"].kind == "function"
    assert by_name["pkg.make"].reexported_from == "pkg.factory.make"
    assert by_name["pkg.sub"].kind == "module"
    assert by_name["pkg.sub"].public_by == "reexport"
    assert by_name["pkg.sub.Leaf"].reexported_from == "pkg.sub.leaf.Leaf"
    assert by_name["pkg.factory.other"].public_by == "name"
    assert "pkg.other" not in by_name
    assert "pkg._Hidden" not in by_name and "pkg.widget._Hidden" not in by_name
    assert not any(name.startswith("pkg._private") for name in by_name)
    assert not any("tests" in name for name in by_name)
    assert surface.unresolved == ("pkg:3:from .sub import *",)


def test_a_malformed_module_is_recorded_and_skipped(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "from .good import Good\n")
    _write(tmp_path, "pkg/good.py", "class Good:\n    pass\n")
    _write(tmp_path, "pkg/broken.py", "class Broken(:\n")
    surface = inspect_public_surface(tmp_path, ["pkg"])
    assert [s.qualified_name for s in surface.symbols] == [
        "pkg",
        "pkg.Good",
        "pkg.good",
        "pkg.good.Good",
    ]
    assert len(surface.unresolved) == 1
    assert surface.unresolved[0].startswith("pkg.broken:1:syntax-error:pkg/broken.py:")


def test_a_reexport_of_a_missing_origin_stays_unresolved(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "from .gone import Ghost\n")
    surface = inspect_public_surface(tmp_path, ["pkg"])
    ghost = next(s for s in surface.symbols if s.name == "Ghost")
    assert ghost.kind == "unknown"
    assert surface.unresolved == ("pkg:1:unresolved-reexport:pkg.gone.Ghost",)
    facts = public_symbol_facts(surface)
    unresolved_fact = next(f for f in facts if f.value == "pkg.Ghost")
    assert (unresolved_fact.polarity, unresolved_fact.confidence) == ("UNRESOLVED", 0.5)


def test_utf8_bom_and_src_layout_are_accepted(tmp_path: Path) -> None:
    _write(tmp_path, "src/pkg/__init__.py", "﻿from .core import Core\n")
    _write(tmp_path, "src/pkg/core.py", "﻿class Core:\n    pass\n")
    surface = inspect_public_surface(tmp_path, ["src/pkg"])
    assert [s.qualified_name for s in surface.symbols] == [
        "pkg",
        "pkg.Core",
        "pkg.core",
        "pkg.core.Core",
    ]
    assert surface.symbols[1].source_path == "src/pkg/__init__.py"


def test_nested_package_dirs_are_walked_once_and_facts_are_unique(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/sub/__init__.py", "class Item:\n    pass\n\nclass item:\n    pass\n")
    surface = inspect_public_surface(tmp_path, ["pkg", "pkg/sub"])
    facts = public_symbol_facts(surface)
    assert [f.id for f in facts] == [
        "public_symbol:pkg",
        "public_symbol:pkg.sub",
        "public_symbol:pkg.sub.item",
        "public_symbol:pkg.sub.item-2",
    ]
    assert [f.value for f in facts][2:] == ["pkg.sub.Item", "pkg.sub.item"]
    assert facts[2].evidence[0].detail == "line 1; class; public by name"
    assert public_symbol_facts(inspect_public_surface(tmp_path, ["pkg", "pkg/sub"])) == facts
