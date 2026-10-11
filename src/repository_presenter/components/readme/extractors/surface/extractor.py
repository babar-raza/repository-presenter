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
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Protocol

from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction import (
    api_surface,
    lang,
)
from repository_presenter.components.readme.extractors.surface.doc_text import (
    normalise_source_docs,
)
from repository_presenter.core.facts import slug

# The vendored engine keys its per-language adapters by grammar name and registers one for
# TypeScript only, although every `language in ("typescript", "javascript")` branch in it reads
# JavaScript through the same code. Without an adapter under "javascript", a JSDoc block before an
# `export class` is invisible to it: the declaration sits inside an `export_statement`, and it is
# the TypeScript adapter's `doc_anchor` that steps through it (measured 2026-10-11 on
# aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js: all 30 exported classes read as undocumented).
# TypeScript's grammar is a superset of JavaScript's, so JavaScript is parsed by it and its
# adapter is TypeScript's. Registered here, at the façade, rather than patched into the vendored
# package; a language registered by an earlier import is left alone.
lang.LANGUAGES.setdefault("javascript", lang.typescript)

# G5-W02 (27.2 RC7). Bumped whenever this module's own mapping or extraction logic changes, the
# same convention SHELL_VERSION/RENDERER_VERSION/NORMALISATION_VERSION already use for their own
# domains; dependencies.json's environment class records it so a change here reopens EXTRACTING
# for every sealed candidate, not only the ones a plugin file's own edit happens to touch.
# 2 (TC-EXT-01, G3-W08 cut 2): PEP 508 requirements kept whole, src-layout import paths, dynamic
# Python dependencies unresolved, relative manifest discovery, Maven identity from the project's
# own POM children, install claims gated on registry ownership, unexposed Rust items dropped.
# 3 (TC-COV-02, G3-W08, cut 3): build_test_asset facts for the build command, the test command and
# the CI matrix, read from the clone's workflows, package.json, Makefile and toolchain manifests.
# 4: CUT-4 (G3-W08): TypeScript nested type-literal fields are not members, license and notices
# files
# under License/ directories, the registry-lag fact, the JavaScript adapter.
EXTRACTOR_VERSION = "4"

SymbolKind = Literal["module", "class", "enum", "function", "method", "unknown"]

# The vendored engine names a symbol by its tree-sitter node type; the contract names it by what
# it is. A node type with no entry is "unknown", which is honest and still citable.
_KINDS: dict[str, SymbolKind] = {
    "class_declaration": "class",
    "abstract_class_declaration": "class",
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
    # Go: `type X struct {...}` or `type X int` is a `type_spec` inside a `type_declaration`.
    "type_spec": "class",
    "type_declaration": "class",
    "enum_declaration": "enum",
    "enum_specifier": "enum",
    "enum_item": "enum",
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    # The vendored engine's own literal for a top-level function, set in api_surface.py for
    # every language rather than read from a tree-sitter node type - not a language-specific
    # grammar name like the others in this table, but the same façade contract either way
    # (measured 2026-09-06 on Go and Rust: every top-level function rendered unknown for want
    # of this one entry).
    "function": "function",
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


class DocNormalisingParser:
    """A parser that resolves each doc comment's inline markup before the engine reads it.

    The vendored engine is never edited, and it loses text it meets in a doc comment
    (``<see langword="null"/>``, ``<see cref="X">label</see>``, ``cref="M:T.M(System.Int32)"``;
    ``doc_text`` has the measurements). It reads the source through ``parse``, so the rewrite sits
    here: same lines, same line count, only the text of a comment changes.
    """

    def __init__(self, parser: Parser, language: str) -> None:
        self._parser = parser
        self._language = language

    def parse(self, source: bytes) -> Any:
        return self._parser.parse(normalise_source_docs(source, self._language))


@dataclass(frozen=True)
class SurfaceSymbol:
    """One public symbol, with the provenance a fact's evidence needs."""

    value: str
    symbol_kind: SymbolKind
    source_path: str
    line: int
    doc: str = ""
    signature: str = ""
    # What a fact ID is derived from. It is the value, unless another symbol's value slugs to the
    # same thing: a fact ID is lowercased and C# is not, so `MimeType` and `MIMEType` collide.
    fact_slug: str = ""

    def __post_init__(self) -> None:
        if not self.fact_slug:
            object.__setattr__(self, "fact_slug", self.value)


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


def _simple_name(entry: dict[str, Any]) -> str:
    return slug_safe(str(entry.get("class_import") or entry.get("name", ""))).rsplit(".", 1)[-1]


def _inherited_constructor(
    method: dict[str, Any], owner: dict[str, Any], declared_in: dict[str, set[str]]
) -> bool:
    """Whether ``method`` is another type's constructor, listed under a type that derives from it.

    The engine lists a derived type's inherited members under it, and a base class's constructor
    comes along: Aspose.3D for .NET's ``Scene`` listed ``A3DObject`` and ``SceneObject``, its
    ancestors' constructors, as members of its own (wave-3 acceptance review, 2026-10-11). A
    constructor has no return type, is named after the type that declares it, and sits in that
    type's file; a method that merely shares a type's name does not meet all three.
    """
    name = slug_safe(str(method.get("name", "")))
    if not name or str(method.get("return_type") or "").strip():
        return False
    if name == _simple_name(owner):
        return False
    declared = str(method.get("file") or "")
    return bool(declared) and declared in declared_in.get(name, set())


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
    confirms_unreachable: Callable[[dict[str, Any]], bool] | None = None,
) -> list[SurfaceSymbol]:
    """Every public type the vendored engine finds, and the members it declares.

    The engine also marks a declaration `reachable: False` when it is syntactically public yet
    no re-export from the package root exposes it. That mark is a best-effort scan and
    measurably wrong in both directions for Rust (it called `semver::Version`, defined in
    `lib.rs`, and `aho_corasick::AhoCorasick`, re-exported through nested braces, unreachable),
    so it is never trusted alone: an entry is dropped only when `confirms_unreachable` - the
    caller's independent test - agrees. Without one the mark is ignored, as it always was.

    A type contributes itself, then one symbol per public method and property, so the API
    Reference's rows and its member bullets come from the same read of the same tree.

    A name appears once. C# overloads a method by signature and names a constructor after its
    type, so `Cell.GetStyle()` and `Cell.GetStyle(int)` are two declarations of one member;
    emitting both gave two facts with the same ID and the facts document refused them outright
    (measured 2026-09-06 on Aspose.Cells and Aspose.Email for .NET). The first declaration wins,
    which is the earliest line, and the contract's API Reference lists a member once anyway.
    """
    types, *_ = api_surface.extract_api_surface(
        DocNormalisingParser(parser, language), language, package_root, repository_root, family
    )
    declared_in: dict[str, set[str]] = {}
    for entry in types:
        declared_in.setdefault(_simple_name(entry), set()).add(str(entry.get("file", "")))
    symbols: list[SurfaceSymbol] = []
    for entry in types:
        # The vendored engine already knows a class from a vendor or private directory is not
        # public (H-04d, `_vendor_files`) and keeps it in its own output only for diagnostics,
        # tagged `visibility: "internal"`. Discarding that tag published it anyway: measured
        # 2026-09-06 on Aspose.PDF for C++ (393 of 2,044 symbols from `include/internal/`) and
        # Aspose.Slides for C++ (401 of 3,243 from `include/Aspose/Slides/Foss/_internal/`), the
        # same repositories a lane's own directory-name heuristic patched around in its own
        # plugin - a workaround this makes redundant rather than a second, parallel filter.
        if str(entry.get("visibility", "")) == "internal":
            continue
        if (
            entry.get("reachable") is False
            and confirms_unreachable is not None
            and confirms_unreachable(entry)
        ):
            continue
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
            if _inherited_constructor(method, entry, declared_in):
                continue
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
    return _disambiguate(_namespaces(unique) + unique)


def _namespaces(symbols: list[SurfaceSymbol]) -> list[SurfaceSymbol]:
    """One symbol per namespace a public type is declared in, as Python emits one per module.

    A job reads the source and names `Aspose.Pdf.Comparison` - a namespace that really does hold
    public types - and the facts carried no such ID, so `repository_investigation` was rejected
    twice and the repository produced nothing at all (measured 2026-09-06 on Aspose.PDF for .NET:
    `public_symbol:aspose.pdf.comparison`, `...structuredcontent`, `...devices`,
    `...structuredocument`). The Python extractor emits 52 module symbols for the canary, so the
    gap was this surface's, not the job's: a namespace is part of the public surface a reader
    navigates, and naming one was never a hallucination.

    A prefix that is itself a type is a nested type's container rather than a namespace, so it is
    skipped. Sorted, so the order does not depend on the grammar's traversal. A namespace spans
    files, so it is evidenced where the first symbol inside it is declared - that declaration is
    inside the namespace's own body, which is what proves the namespace exists.
    """
    types = {symbol.value for symbol in symbols}
    found: dict[str, SurfaceSymbol] = {}
    for symbol in symbols:
        parts = symbol.value.split(".")
        for depth in range(1, len(parts)):
            name = ".".join(parts[:depth])
            if name in types or name in found:
                continue
            found[name] = SurfaceSymbol(
                value=name,
                symbol_kind="module",
                source_path=symbol.source_path,
                line=symbol.line,
            )
    return [found[name] for name in sorted(found)]


def _disambiguate(symbols: list[SurfaceSymbol]) -> list[SurfaceSymbol]:
    """Give every symbol a fact-ID source no other symbol shares.

    A fact ID is lowercased and C# is not, so a library may expose two distinct public members
    whose slugs collide - measured 2026-09-06 on Aspose.PDF for .NET, which declares `MimeType`
    and `MIMEType`, `findField` and `FindField`, `LLx` and `Llx`: seven pairs, every one of them
    two real members, usually an alias kept for compatibility. Dropping either would delete a
    public member from a reference the contract says must be complete (loop-prompt §6 rule 8), so
    the later one takes a numbered suffix instead. The value - the name a reader sees - is
    untouched; only the identifier moves.
    """
    taken: dict[str, int] = {}
    resolved: list[SurfaceSymbol] = []
    for symbol in symbols:
        key = slug(symbol.value)
        count = taken.get(key, 0) + 1
        taken[key] = count
        source = symbol.value if count == 1 else f"{symbol.value}-{count}"
        resolved.append(replace(symbol, fact_slug=source))
    return resolved
