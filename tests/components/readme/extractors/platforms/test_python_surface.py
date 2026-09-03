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
        "pkg.widget.Widget.render",
        "pkg.widget",
        "render",
        "method",
        "pkg/widget.py",
        2,
        "name",
        signature="def render(self)",
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
        signature="class Widget",
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


def test_symbols_carry_their_kind_signature_and_docstring_as_structured_attributes(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "lib/__init__.py",
        '"""Lib: scenes and shapes.\n\nMore."""\nfrom .shapes import Shape, Kind\n',
    )
    _write(
        tmp_path,
        "lib/shapes.py",
        "from enum import Enum\n\n\nclass Kind(Enum):\n"
        '    """Which shape."""\n\n    BOX = 1\n\n\nclass Shape(Base):\n'
        '    """A shape in a scene.\n\n    Longer text.\n    """\n\n'
        "    def area(self, scale: float = 1.0) -> float:\n"
        '        """The area, scaled."""\n        return 0.0\n\n\n'
        "async def load(path: str) -> Shape:\n    return Shape()\n",
    )
    surface = inspect_public_surface(tmp_path, ["lib"])
    by_name = {symbol.qualified_name: symbol for symbol in surface.symbols}
    assert by_name["lib"].docstring == "Lib: scenes and shapes."
    assert by_name["lib.shapes.Kind"].kind == "enum"
    assert by_name["lib.shapes.Kind"].signature == "class Kind(Enum)"
    assert by_name["lib.shapes.Shape"].docstring == "A shape in a scene."
    assert by_name["lib.shapes.Shape"].signature == "class Shape(Base)"
    assert by_name["lib.shapes.Shape.area"].signature == "def area(self, scale: float=1.0) -> float"
    assert by_name["lib.shapes.Shape.area"].docstring == "The area, scaled."
    assert by_name["lib.shapes.load"].signature == "async def load(path: str) -> Shape"
    # A re-export carries its origin's evidence.
    assert by_name["lib.Kind"].kind == "enum" and by_name["lib.Kind"].docstring == "Which shape."
    facts = {fact.value: fact for fact in public_symbol_facts(surface)}
    assert facts["lib.Shape"].attributes == {
        "symbol_kind": "class",
        "signature": "class Shape(Base)",
        "docstring": "A shape in a scene.",
        "defined_at": "lib.shapes.Shape",
        "public_paths": "lib.shapes.Shape",
    }
    assert facts["lib.Kind"].attributes["symbol_kind"] == "enum"
    assert facts["lib"].attributes == {
        "symbol_kind": "module",
        "docstring": "Lib: scenes and shapes.",
    }
    assert "lib.shapes.Shape" not in facts
    assert facts["lib.Shape.area"].attributes["defined_at"] == "lib.shapes.Shape.area"


def test_reexport_paths_collapse_to_one_fact_named_by_the_shortest_public_path(
    tmp_path: Path,
) -> None:
    surface = inspect_public_surface(_package(tmp_path), ["pkg"])
    facts = public_symbol_facts(surface)
    assert [fact.value for fact in facts] == [
        "pkg",
        "pkg.Widget",
        "pkg.Widget.render",
        "pkg.Widget.size",
        "pkg.factory",
        "pkg.factory.other",
        "pkg.make",
        "pkg.sub",
        "pkg.sub.Leaf",
        "pkg.sub.leaf",
        "pkg.widget",
    ]
    widget = next(fact for fact in facts if fact.value == "pkg.Widget")
    assert widget.id == "public_symbol:pkg.widget"
    assert widget.attributes["defined_at"] == "pkg.widget.Widget"
    assert widget.attributes["public_paths"] == "pkg.widget.Widget"
    assert [(e.path, e.detail) for e in widget.evidence] == [
        ("pkg/widget.py", "line 1; class; public by name"),
        ("pkg/__init__.py", "line 1; re-exported as pkg.Widget"),
    ]
    make = next(fact for fact in facts if fact.value == "pkg.make")
    assert make.attributes["symbol_kind"] == "function"
    assert make.attributes["defined_at"] == "pkg.factory.make"
    sub = next(fact for fact in facts if fact.value == "pkg.sub")
    assert sub.attributes["symbol_kind"] == "module"
