"""Static public surface of the Python packages: definitions, ``__all__``, and re-exports.

Nothing is imported or executed. Every module under the product packages is parsed with ``ast``.
A top-level class or function is public when its name has no leading underscore and, when the
module declares a literal ``__all__``, is listed there. A package ``__init__`` re-export is
public by the same rule and keeps the origin it came from. Star imports, unresolvable relative
imports, and syntax errors are recorded as unresolved, never guessed. Class members are not
inventoried here; they arrive with the example verifier, bounded to the classes the README uses.
"""

from __future__ import annotations

import ast
import importlib.util
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from repository_presenter.core.facts import Evidence, Fact, fact_id

SymbolKind = Literal["module", "class", "function", "unknown"]
PublicBy = Literal["name", "__all__", "reexport"]

_EXCLUDED_PARTS = frozenset({"__pycache__", "build", "dist", "tests", "test", "docs", "examples"})


@dataclass(frozen=True)
class PublicSymbol:
    """One statically visible symbol with exact source provenance."""

    qualified_name: str
    module: str
    name: str
    kind: SymbolKind
    source_path: str
    line: int
    public_by: PublicBy
    reexported_from: str | None = None


@dataclass(frozen=True)
class PublicSurface:
    """Every public symbol of the inspected packages plus what could not be resolved."""

    symbols: tuple[PublicSymbol, ...]
    unresolved: tuple[str, ...]


def _literal_all(tree: ast.Module) -> set[str] | None:
    names: set[str] = set()
    found = False
    for node in tree.body:
        value: ast.AST | None = None
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            )
        ) or (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and isinstance(node.op, ast.Add)
        ):
            value = node.value
            found = True
        if value is None:
            continue
        try:
            resolved = ast.literal_eval(value)
        except (ValueError, TypeError):
            continue
        if isinstance(resolved, list | tuple | set):
            names.update(item for item in resolved if isinstance(item, str))
    return names if found else None


def _public_name(name: str, explicit: set[str] | None) -> tuple[bool, PublicBy]:
    if name.startswith("_"):
        return False, "name"
    if explicit is not None:
        return name in explicit, "__all__"
    return True, "name"


def _module_name(path: Path, source_root: Path) -> tuple[str, bool]:
    relative = path.relative_to(source_root)
    is_package = path.name == "__init__.py"
    parts = relative.parent.parts if is_package else relative.with_suffix("").parts
    return ".".join(parts), is_package


def _resolved_relative(module: str, is_package: bool, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    package = module if is_package else module.rpartition(".")[0]
    try:
        return importlib.util.resolve_name("." * node.level + (node.module or ""), package)
    except (ImportError, ValueError):
        return None


def _module_symbols(
    path: Path, source_root: Path, repository_root: Path
) -> tuple[list[PublicSymbol], list[str]]:
    module, is_package = _module_name(path, source_root)
    relative = path.relative_to(repository_root).as_posix()
    if not module or any(part.startswith("_") for part in module.split(".")):
        return [], []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        return [], [f"{module}:{exc.lineno or 0}:syntax-error:{relative}:{exc.msg}"]
    explicit = _literal_all(tree)
    symbols = [
        PublicSymbol(module, module, module.rsplit(".", 1)[-1], "module", relative, 1, "name")
    ]
    unresolved: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            public, public_by = _public_name(node.name, explicit)
            if public:
                kind: SymbolKind = "class" if isinstance(node, ast.ClassDef) else "function"
                symbols.append(
                    PublicSymbol(
                        f"{module}.{node.name}",
                        module,
                        node.name,
                        kind,
                        relative,
                        node.lineno,
                        public_by,
                    )
                )
        elif isinstance(node, ast.ImportFrom) and (is_package or explicit is not None):
            origin = _resolved_relative(module, is_package, node)
            if origin is None or any(alias.name == "*" for alias in node.names):
                unresolved.append(f"{module}:{node.lineno}:{ast.unparse(node)}")
                continue
            for alias in node.names:
                exposed = alias.asname or alias.name
                if _public_name(exposed, explicit)[0]:
                    symbols.append(
                        PublicSymbol(
                            f"{module}.{exposed}",
                            module,
                            exposed,
                            "unknown",
                            relative,
                            node.lineno,
                            "reexport",
                            reexported_from=f"{origin}.{alias.name}",
                        )
                    )
    return symbols, unresolved


def _origin_kind(origin: str, source_root: Path) -> SymbolKind | None:
    """The kind of one re-exported definition, read from its own file; ``None`` if absent."""
    origin_path = source_root / Path(*origin.split("."))
    if origin_path.is_dir() or origin_path.with_suffix(".py").is_file():
        return "module"
    module, name = origin.rsplit(".", 1)
    package_path = source_root / Path(*module.split("."))
    for candidate in (package_path.with_suffix(".py"), package_path / "__init__.py"):
        if not candidate.is_file():
            continue
        try:
            tree = ast.parse(candidate.read_text(encoding="utf-8-sig", errors="replace"))
        except SyntaxError:
            return None
        for item in tree.body:
            if isinstance(item, ast.ClassDef) and item.name == name:
                return "class"
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name == name:
                return "function"
        return None
    return None


def _minimal_roots(package_dirs: Sequence[str]) -> list[str]:
    """Drop package directories that another listed directory already contains."""
    ordered = sorted(set(package_dirs))
    return [d for d in ordered if not any(d.startswith(other + "/") for other in ordered)]


def inspect_public_surface(repository_root: Path, package_dirs: Sequence[str]) -> PublicSurface:
    """Inspect the packages at ``package_dirs`` (repository-relative) without importing them."""
    symbols: dict[str, PublicSymbol] = {}
    unresolved: list[str] = []
    for package_dir in _minimal_roots(package_dirs):
        package_path = repository_root / package_dir
        source_root = package_path.parent
        for path in sorted(package_path.rglob("*.py")):
            if any(part in _EXCLUDED_PARTS for part in path.relative_to(source_root).parts):
                continue
            module_symbols, module_unresolved = _module_symbols(path, source_root, repository_root)
            unresolved.extend(module_unresolved)
            for symbol in module_symbols:
                current = symbols.get(symbol.qualified_name)
                if current is None or (symbol.public_by == "reexport" and current.kind == "module"):
                    symbols[symbol.qualified_name] = symbol
        for name, symbol in list(symbols.items()):
            if symbol.reexported_from is None or symbol.kind != "unknown":
                continue
            origin = symbols.get(symbol.reexported_from)
            kind = (
                origin.kind
                if origin is not None and origin.kind != "unknown"
                else _origin_kind(symbol.reexported_from, source_root)
            )
            if kind is None:
                unresolved.append(
                    f"{symbol.module}:{symbol.line}:unresolved-reexport:{symbol.reexported_from}"
                )
            else:
                symbols[name] = replace(symbol, kind=kind)
    return PublicSurface(
        symbols=tuple(symbols[name] for name in sorted(symbols)),
        unresolved=tuple(sorted(set(unresolved))),
    )


def public_symbol_facts(surface: PublicSurface) -> list[Fact]:
    """One ``public_symbol`` fact per symbol; IDs stay unique when names differ only by case."""
    facts: list[Fact] = []
    seen: dict[str, int] = {}
    for symbol in surface.symbols:
        base = fact_id("public_symbol", symbol.qualified_name)
        seen[base] = seen.get(base, 0) + 1
        identifier = base if seen[base] == 1 else f"{base}-{seen[base]}"
        detail = f"line {symbol.line}; {symbol.kind}; public by {symbol.public_by}"
        if symbol.reexported_from is not None:
            detail += f"; re-export of {symbol.reexported_from}"
        facts.append(
            Fact(
                identifier,
                "public_symbol",
                symbol.qualified_name,
                (Evidence(symbol.source_path, detail),),
                polarity="SUPPORTED" if symbol.kind != "unknown" else "UNRESOLVED",
                confidence=1.0 if symbol.kind != "unknown" else 0.5,
            )
        )
    return facts
