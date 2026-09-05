"""The typed way in to the vendored surface extraction: the only importer of `_vendor`.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2. The vendored engine reads tree-sitter nodes for six
languages and returns loosely typed dictionaries keyed by node type. This module is where that
becomes something the contract can use: a node type becomes a `symbol_kind` from the same
vocabulary the Python extractor already emits, a language's separators become a value a fact ID's
slug accepts (§29.2 F8 - `Aspose::ThreeD::Scene` and C# `Outer+Inner` are mapped, never passed
through), and every symbol carries the file and line it was declared on.

Nothing here decides whether a symbol is true. The extractor's output is admitted only through
the parity control and the contract's own checks; origin never makes a fact true.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction import (
    api_surface,
)

SymbolKind = Literal["module", "class", "enum", "function", "method", "unknown"]

# The vendored engine names a symbol by its tree-sitter node type; the contract names it by what
# it is. A node type with no entry is "unknown", which is honest and still citable.
_KINDS: dict[str, SymbolKind] = {
    "class_declaration": "class",
    "class_specifier": "class",
    "class_definition": "class",
    "struct_declaration": "class",
    "struct_specifier": "class",
    "struct_item": "class",
    "record_declaration": "class",
    "interface_declaration": "class",
    "type_alias_declaration": "class",
    "trait_item": "class",
    "impl_item": "class",
    "enum_declaration": "enum",
    "enum_specifier": "enum",
    "enum_item": "enum",
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    "method_declaration": "method",
    "method_definition": "method",
}
# What separates a namespace from a type, per language, and what C# puts between a type and the
# type nested inside it. Both become "." so one slug rule serves every ecosystem.
_SEPARATORS = ("::", "+", "->", "/")
_GENERIC = re.compile(r"<[^<>]*>")
_UNSAFE = re.compile(r"[^A-Za-z0-9._]+")


class Parser(Protocol):
    """What tree-sitter gives us; typed here so the façade needs no stub for the pack."""

    def parse(self, source: bytes) -> Any: ...


@dataclass(frozen=True)
class SurfaceSymbol:
    """One public symbol, with the provenance a fact's evidence needs."""

    value: str
    symbol_kind: SymbolKind
    source_path: str
    line: int
    doc: str = ""
    signature: str = ""


def slug_safe(value: str) -> str:
    """A symbol's dotted form: every language's separator mapped, every generic dropped.

    Generics are dropped rather than encoded because a fact names the type, not the
    instantiation: `List<Widget>` and `List<Mode>` are one symbol in the surface.
    """
    # Innermost first, repeatedly: one pass leaves Dictionary<string, List> behind.
    plain = value
    while True:
        stripped = _GENERIC.sub("", plain)
        if stripped == plain:
            break
        plain = stripped
    for separator in _SEPARATORS:
        plain = plain.replace(separator, ".")
    plain = _UNSAFE.sub(".", plain)
    return ".".join(part for part in plain.split(".") if part)


def symbol_kind(node_type: str) -> SymbolKind:
    """The contract's name for a tree-sitter node type."""
    return _KINDS.get(node_type, "unknown")


def _line(entry: dict[str, Any]) -> int:
    """The declaring line, or zero when the grammar gave none.

    Measured 2026-09-06 on Aspose.PDF and Aspose.Slides for .NET: the key is present and null for
    some C# members, and a dictionary default only applies when the key is absent, so converting
    it raised a TypeError and the whole facts stage died.
    """
    value = entry.get("line")
    return int(value) if isinstance(value, int | float | str) and str(value).strip() else 0


def _signature(method: dict[str, Any]) -> str:
    parameters = ", ".join(
        f"{item.get('type', '')} {item.get('name', '')}".strip()
        for item in method.get("params", [])
    )
    returns = str(method.get("return_type", "")).strip()
    call = f"{method.get('name', '')}({parameters})"
    return f"{returns} {call}".strip()


def surface_symbols(
    parser: Parser,
    language: str,
    package_root: Path,
    repository_root: Path,
    family: str,
) -> list[SurfaceSymbol]:
    """Every public type the vendored engine finds, and the members it declares.

    A type contributes itself, then one symbol per public method and property, so the API
    Reference's rows and its member bullets come from the same read of the same tree.

    A name appears once. C# overloads a method by signature and names a constructor after its
    type, so `Cell.GetStyle()` and `Cell.GetStyle(int)` are two declarations of one member;
    emitting both gave two facts with the same ID and the facts document refused them outright
    (measured 2026-09-06 on Aspose.Cells and Aspose.Email for .NET). The first declaration wins,
    which is the earliest line, and the contract's API Reference lists a member once anyway.
    """
    types, *_ = api_surface.extract_api_surface(
        parser, language, package_root, repository_root, family
    )
    symbols: list[SurfaceSymbol] = []
    for entry in types:
        qualified = slug_safe(str(entry.get("class_import") or entry.get("name", "")))
        if not qualified:
            continue
        path = str(entry.get("file", ""))
        symbols.append(
            SurfaceSymbol(
                value=qualified,
                symbol_kind=symbol_kind(str(entry.get("kind", ""))),
                source_path=path,
                line=_line(entry),
                doc=str(entry.get("doc", "")),
            )
        )
        for method in entry.get("methods", []):
            symbols.append(
                SurfaceSymbol(
                    value=f"{qualified}.{slug_safe(str(method.get('name', '')))}",
                    symbol_kind="method",
                    source_path=str(method.get("file", path)),
                    line=_line(method),
                    doc=str(method.get("doc", "")),
                    signature=_signature(method),
                )
            )
        for prop in entry.get("properties", []):
            symbols.append(
                SurfaceSymbol(
                    value=f"{qualified}.{slug_safe(str(prop.get('name', '')))}",
                    symbol_kind="method",
                    source_path=str(prop.get("file", path)),
                    line=_line(prop),
                    doc=str(prop.get("doc", "")),
                    signature=str(prop.get("type", "")),
                )
            )
    seen: set[str] = set()
    unique: list[SurfaceSymbol] = []
    for symbol in symbols:
        if symbol.value in seen:
            continue
        seen.add(symbol.value)
        unique.append(symbol)
    return unique
