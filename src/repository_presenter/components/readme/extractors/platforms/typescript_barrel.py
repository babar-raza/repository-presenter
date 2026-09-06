"""Which TypeScript sources a package actually publishes: its entry point, and what it re-exports.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. TypeScript has no `public` keyword at module scope and no
namespace a file belongs to: a symbol is part of the package's surface only if the entry point the
manifest declares re-exports it, directly or through another barrel. Everything else is an
implementation file that happens to say `export` so a sibling can import it.

Two things this module has to survive, both measured 2026-09-06 on the cohort. The declared entry
point usually names build output that no clone contains - Aspose.3D for TypeScript declares
`dist/index.js` and `dist/index.d.ts`, and the repository ships neither - so a built path is mapped
back through `tsconfig.json`'s `outDir` and `rootDir` to the source it would be built from. And an
entry point may be a program rather than a barrel: Aspose.Cells for TypeScript declares
`index.ts`, a demo script that constructs a workbook and saves it, while the real barrel is
`aspose_cells/index.ts` beside it. A file that re-exports nothing is not an entry point.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# A repository carries copies of its own sources under these; none of them is the package.
IGNORED_DIRECTORIES = frozenset(
    {".git", "node_modules", "dist", "build", "out", "lib", "coverage", ".next"}
)
_NOT_THE_PRODUCT = frozenset(
    {
        "test",
        "tests",
        "__tests__",
        "spec",
        "example",
        "examples",
        "sample",
        "samples",
        "demo",
        "docs",
    }
)
# `export { A, B as C } from './x'`, with the optional `type` modifier TypeScript 5 allows.
_NAMED_FROM = re.compile(r"export\s+(?:type\s+)?\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")
_STAR_FROM = re.compile(r"export\s+\*\s+(?:as\s+([A-Za-z_$][\w$]*)\s+)?from\s*['\"]([^'\"]+)['\"]")
_LOCAL_NAMED = re.compile(r"export\s+(?:type\s+)?\{([^}]*)\}\s*(?!from)[;\n]")
_DECLARED = re.compile(
    r"export\s+(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?"
    r"(?:class|interface|enum|function|const|let|var|type)\s+([A-Za-z_$][\w$]*)"
)
_ALIAS = re.compile(r"^(?:type\s+)?(\S+)(?:\s+as\s+(\S+))?$")
# A barrel graph is small; a cycle or a generated tree must not make it unbounded.
_MAX_FILES = 400
_ENTRY_FIELDS = ("types", "typings", "main", "module")
_EXPORT_CONDITIONS = ("types", "import", "require", "default")


def read_json(path: Path) -> dict[str, Any]:
    """A JSON manifest as a mapping; a file that will not parse declares nothing.

    `tsconfig.json` is JSON with comments and trailing commas by convention, so both are stripped
    before parsing rather than letting a comment cost the whole file (measured 2026-09-06: neither
    cohort repository uses either, but the convention is common enough that failing closed on it
    would be a silent gap).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    stripped = re.sub(r"(?m)^\s*//.*$", "", stripped)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    for candidate in (text, stripped):
        try:
            loaded = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def compiler_options(package: Path) -> dict[str, Any]:
    """The package's own `tsconfig.json` compiler options, or an empty mapping."""
    options = read_json(package / "tsconfig.json").get("compilerOptions")
    return options if isinstance(options, dict) else {}


def _entry_specifiers(manifest: dict[str, Any]) -> list[str]:
    """Every path the manifest offers as the package's entry point, types first.

    `types` before `main` because a TypeScript consumer resolves the declaration file, and it is
    the one whose source this module has to find.
    """
    found: list[str] = []
    for field in _ENTRY_FIELDS:
        value = manifest.get(field)
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
    exports = manifest.get("exports")
    dot = exports.get(".") if isinstance(exports, dict) else None
    if isinstance(dot, str):
        found.append(dot)
    elif isinstance(dot, dict):
        found.extend(
            str(dot[key]).strip()
            for key in _EXPORT_CONDITIONS
            if isinstance(dot.get(key), str) and str(dot[key]).strip()
        )
    return found


def _sources_for(package: Path, specifier: str, options: dict[str, Any]) -> list[Path]:
    """The TypeScript files a declared entry-point path could be built from, in preference order.

    A specifier that already names a source resolves to itself. One that names build output is
    mapped through `outDir` and `rootDir`: `dist/index.js` with `outDir: ./dist` and
    `rootDir: ./src` is built from `src/index.ts`, which is the file a clone actually has.
    """
    relative = specifier.lstrip("./").replace("\\", "/")
    stem = re.sub(r"\.(d\.ts|ts|tsx|js|mjs|cjs|jsx)$", "", relative)
    candidates = [stem]
    out_dir = str(options.get("outDir", "")).strip().lstrip("./").rstrip("/")
    root_dir = str(options.get("rootDir", "")).strip().lstrip("./").rstrip("/")
    if out_dir and stem.startswith(out_dir + "/"):
        remainder = stem[len(out_dir) + 1 :]
        candidates.append(f"{root_dir}/{remainder}" if root_dir else remainder)
    found: list[Path] = []
    for candidate in candidates:
        for shape in (f"{candidate}.ts", f"{candidate}.tsx", f"{candidate}/index.ts"):
            path = package / shape
            if path.is_file() and path not in found:
                found.append(path)
    return found


def _is_barrel(path: Path) -> bool:
    """Whether the file re-exports another module, which is what makes it an entry point.

    Aspose.Cells for TypeScript declares `main: index.ts`, and that file imports a workbook,
    writes two spreadsheets and logs - a demo, not a surface. Its `aspose_cells/index.ts` is the
    barrel. Requiring a re-export separates them without guessing from the name.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_NAMED_FROM.search(text) or _STAR_FROM.search(text))


def entry_barrel(package: Path) -> Path | None:
    """The source file that is this package's public entry point, or None when it has none.

    The manifest's own declaration is preferred, mapped back to source where it names build
    output. When nothing it declares resolves to a barrel, the shallowest `index.ts` in the tree
    that re-exports is taken instead, which is the convention every published TypeScript package
    follows and the only evidence a repository without a usable manifest field offers.
    """
    manifest = read_json(package / "package.json")
    options = compiler_options(package)
    fallbacks: list[Path] = []
    for specifier in _entry_specifiers(manifest):
        for source in _sources_for(package, specifier, options):
            if _is_barrel(source):
                return source
            fallbacks.append(source)
    barrels = sorted(
        (
            path
            for path in package.rglob("index.ts")
            if not any(part in IGNORED_DIRECTORIES for part in path.parts)
            and not any(part.lower() in _NOT_THE_PRODUCT for part in path.parts)
            and _is_barrel(path)
        ),
        key=lambda path: (len(path.parts), str(path)),
    )
    if barrels:
        return barrels[0]
    return fallbacks[0] if fallbacks else None


def _resolve(module_path: Path, specifier: str) -> Path | None:
    """A relative module specifier as the file it names; a package specifier resolves to None."""
    if not specifier.startswith("."):
        return None
    base = (module_path.parent / specifier).resolve()
    stem = re.sub(r"\.(js|ts)$", "", str(base))
    for shape in (f"{stem}.ts", f"{stem}.tsx", f"{stem}/index.ts", f"{stem}/index.tsx"):
        path = Path(shape)
        if path.is_file():
            return path
    return None


def _named(clause: str) -> list[str]:
    """The names one `{ ... }` clause exports, taking the alias where it renames."""
    found: list[str] = []
    for item in clause.split(","):
        match = _ALIAS.fullmatch(item.strip())
        if match:
            found.append(match.group(2) or match.group(1))
    return found


def reexported_names(barrel: Path) -> frozenset[str]:
    """Every name the entry point re-exports, following `export * from` into other barrels.

    Bounded by a visited set and a file ceiling, because a re-export cycle is legal TypeScript and
    a generated tree can be large. A `export * as ns from` binds a namespace object rather than
    the names inside it, so its own name is what the package exports and the recursion stops.
    """
    names: set[str] = set()
    seen: set[Path] = set()
    queue = [barrel]
    while queue and len(seen) < _MAX_FILES:
        current = queue.pop()
        resolved = current.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            text = current.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for clause, specifier in _NAMED_FROM.findall(text):
            names.update(_named(clause))
            _ = specifier
        for alias, specifier in _STAR_FROM.findall(text):
            if alias:
                names.add(alias)
                continue
            target = _resolve(current, specifier)
            if target is not None:
                queue.append(target)
        for clause in _LOCAL_NAMED.findall(text):
            names.update(_named(clause))
        names.update(_DECLARED.findall(text))
    return frozenset(names)
