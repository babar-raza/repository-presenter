"""The façade turns tree-sitter node types into the contract's vocabulary, for every language."""

from __future__ import annotations

from pathlib import Path

import pytest
from tree_sitter_language_pack import get_parser

from repository_presenter.components.readme.extractors.surface.extractor import (
    SurfaceSymbol,
    slug_safe,
    surface_symbols,
    symbol_kind,
)
from repository_presenter.core.facts import slug

CSHARP = """
namespace Aspose.Widget
{
    /// <summary>A widget.</summary>
    public class Widget
    {
        public string Name { get; set; }
        public void Save(string path) { }
        private void Hidden() { }
    }

    public enum Mode { Fast, Slow }

    internal class NotPublic { }
}
"""


def _package(root: Path, name: str, source: str) -> Path:
    package = root / "src" / "Aspose.Widget"
    package.mkdir(parents=True)
    (package / name).write_text(source, encoding="utf-8")
    return package


def test_a_csharp_package_yields_types_and_their_members(tmp_path: Path) -> None:
    package = _package(tmp_path, "Widget.cs", CSHARP)
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "widget")
    by_value = {symbol.value: symbol for symbol in symbols}

    widget = by_value["Aspose.Widget.Widget"]
    assert widget.symbol_kind == "class" and widget.doc == "A widget."
    assert widget.source_path.endswith("Widget.cs") and widget.line == 5
    assert by_value["Aspose.Widget.Mode"].symbol_kind == "enum"
    save = by_value["Aspose.Widget.Widget.Save"]
    assert save.symbol_kind == "method" and save.signature == "Save(string path)"
    assert by_value["Aspose.Widget.Widget.Name"].signature == "string"
    # Visibility is the engine's to judge, and it judged: nothing private or internal is here.
    assert "Aspose.Widget.Widget.Hidden" not in by_value
    assert not any("NotPublic" in value for value in by_value)


def test_every_value_the_facade_emits_is_a_legal_fact_id_slug(tmp_path: Path) -> None:
    """Section 29.2 F8: a symbol that cannot be slugged cannot become a fact."""
    package = _package(tmp_path, "Widget.cs", CSHARP)
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "widget")
    assert symbols
    for symbol in symbols:
        assert slug(symbol.value), symbol.value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Aspose::ThreeD::Scene", "Aspose.ThreeD.Scene"),
        ("Outer+Inner", "Outer.Inner"),
        ("List<Widget>", "List"),
        ("Dictionary<string, List<int>>", "Dictionary"),
        ("crate::module::Type", "crate.module.Type"),
        ("pkg/sub.Type", "pkg.sub.Type"),
        ("Has Space", "Has.Space"),
        ("..Leading.And.Trailing..", "Leading.And.Trailing"),
    ],
)
def test_a_language_separator_becomes_a_dot_and_a_generic_is_dropped(
    raw: str, expected: str
) -> None:
    """A fact names the type, not the instantiation: List<Widget> and List<Mode> are one symbol."""
    assert slug_safe(raw) == expected
    assert slug(slug_safe(raw))


def test_an_unmapped_node_type_is_unknown_rather_than_invented() -> None:
    assert symbol_kind("class_declaration") == "class"
    assert symbol_kind("enum_item") == "enum"
    assert symbol_kind("method_definition") == "method"
    assert symbol_kind("something_the_grammar_added_last_week") == "unknown"


def test_the_facade_is_a_dataclass_the_contract_can_carry() -> None:
    symbol = SurfaceSymbol("A.B", "class", "src/a.cs", 3)
    assert symbol.doc == "" and symbol.signature == ""
    with pytest.raises(AttributeError):
        symbol.value = "changed"  # type: ignore[misc]


OVERLOADED = """
namespace P
{
    public class Cell
    {
        public Cell() { }
        public Cell(int index) { }
        public string GetStyle() { return null; }
        public string GetStyle(int index) { return null; }
        public void PutValue(int v) { }
        public void PutValue(string v) { }
    }
}
"""


def test_an_overloaded_member_is_one_symbol_not_several(tmp_path: Path) -> None:
    """A fact ID must be unique, and the API Reference lists a member once.

    Measured 2026-09-06: Aspose.Cells and Aspose.Email for .NET both died at the facts stage with
    "duplicate fact IDs" naming Cell.GetStyle, Cell.PutValue and CfbDocument.CfbDocument - C#
    overloads a method by signature and names a constructor after its type, which Python never
    does, so the defect could not appear until the second ecosystem arrived.
    """
    package = tmp_path / "src" / "P"
    package.mkdir(parents=True)
    (package / "Cell.cs").write_text(OVERLOADED, encoding="utf-8")
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "p")
    values = [symbol.value for symbol in symbols]
    assert len(values) == len(set(values)), sorted(v for v in values if values.count(v) > 1)
    assert "P.Cell.GetStyle" in values and "P.Cell.PutValue" in values
    # The first declaration wins: the no-argument overload, whose signature carries no
    # parameters. The engine leaves return_type empty for this shape, so the signature is the
    # call alone - measured, not assumed.
    by_value = {symbol.value: symbol for symbol in symbols}
    assert by_value["P.Cell.GetStyle"].signature == "GetStyle()"


def test_a_member_the_grammar_gives_no_line_for_is_kept_at_line_zero(tmp_path: Path) -> None:
    """A null line is not a missing key, so a dictionary default never applied.

    Measured 2026-09-06 on Aspose.PDF and Aspose.Slides for .NET, where converting it raised a
    TypeError and took the whole facts stage down.
    """
    from repository_presenter.components.readme.extractors.surface.extractor import _line

    assert _line({"line": 12}) == 12
    assert _line({"line": None}) == 0
    assert _line({}) == 0
    assert _line({"line": ""}) == 0
    assert _line({"line": "7"}) == 7
