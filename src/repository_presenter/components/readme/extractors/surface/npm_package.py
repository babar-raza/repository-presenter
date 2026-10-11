"""What an npm package's manifest and entry point say it publishes - shared by every npm plugin.

`RESEARCH_AND_GUIDELINES.md` §7.4 and §29.6 E3. TypeScript and Node.js packages are the same
artefact to npm: a `package.json` that names the package, its dependencies and its runtime floor,
and an entry point whose re-exports - not the `export` keyword on a file - decide what a consumer
can reach. Only the source language differs, so everything that does not depend on it lives here,
once, and each plugin supplies its own `ModuleDialect`: which suffixes a module specifier can name
and whether CommonJS assignments count as exports. A plugin imports this module (a shared façade,
like `manifest.py` and `registry.py` beside it) and never another plugin's, which keeps
`docs/REPOSITORY_LAYOUT.md` §2.1 true for both.

The entry point matters because neither language has `public` at module scope. A file says
`export` (or assigns `module.exports`) so its sibling can import it; only the entry point the
manifest declares decides what a consumer of the published package can name. Two things this
module has to survive, both measured 2026-09-06 on the TypeScript cohort. The declared entry point
usually names build output that no clone contains - Aspose.3D for TypeScript declares
`dist/index.js` and ships no `dist/` - so a built path is mapped back through `tsconfig.json`'s
`outDir` and `rootDir` to the source it would be built from. And an entry point may be a program
rather than a barrel: Aspose.Cells for TypeScript declares `index.ts`, a demo script, while the
real barrel is `aspose_cells/index.ts` beside it. A file that re-exports nothing is not an entry
point.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.core.facts import Evidence, Fact, fact_id, slug

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
# What JavaScript can declare behind `export`: no `declare`, `abstract`, `interface`, `enum` or
# `type`, but `async` functions and generators, which a Node library exports as readily as a class.
_DECLARED_JAVASCRIPT = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?"
    r"(?:class\s+|function\s*\*?\s*|const\s+|let\s+|var\s+)([A-Za-z_$][\w$]*)"
)
_ALIAS = re.compile(r"^(?:type\s+)?(\S+)(?:\s+as\s+(\S+))?$")
# CommonJS, for a dialect that reads it. `module.exports = require('./x')` and a spread of one
# re-export a whole module; `exports.A = ...` and a key of a literal `module.exports = { ... }`
# bind one name; `module.exports = Name;` publishes the one thing a single-class module is.
_CJS_REQUIRE = r"require\(\s*['\"]([^'\"]+)['\"]\s*\)"
_CJS_WHOLE = re.compile(r"\bmodule\.exports\s*=\s*" + _CJS_REQUIRE)
_CJS_SINGLE = re.compile(r"\bmodule\.exports\s*=\s*([A-Za-z_$][\w$]*)\s*[;\n]")
# A `require` binds a whole module only when nothing is read off it (`require('./x').Thing` is a
# property of the module, not the module).
_CJS_WHOLE_REQUIRE = r"(?:" + _CJS_REQUIRE + r"(?![\w$.\[(]))?"
_CJS_PROPERTY = re.compile(
    r"\b(?:module\.)?exports\.([A-Za-z_$][\w$]*)\s*=(?!=)\s*" + _CJS_WHOLE_REQUIRE
)
_CJS_LITERAL = re.compile(r"\bmodule\.exports\s*=\s*\{([^{}]*)\}")
_CJS_SPREAD = re.compile(r"^\.\.\.\s*" + _CJS_REQUIRE + r"$")
_CJS_PAIR = re.compile(r"^([A-Za-z_$][\w$]*)\s*:\s*" + _CJS_WHOLE_REQUIRE)
_IDENTIFIER = re.compile(r"^[A-Za-z_$][\w$]*$")
# A barrel graph is small; a cycle or a generated tree must not make it unbounded.
_MAX_FILES = 400
_ENTRY_FIELDS = ("types", "typings", "main", "module")
_EXPORT_CONDITIONS = ("types", "import", "require", "default")
_BUILT_SOURCE = re.compile(r"\.(d\.ts|ts|tsx|js|mjs|cjs|jsx)$")


@dataclass(frozen=True)
class ModuleDialect:
    """How one source language spells a module on disk, and what counts as exporting from it.

    ``suffixes`` are the extensions a module specifier can name, preferred first; a specifier that
    names a directory resolves to ``index`` plus the first of them. ``strip`` removes the
    extension a specifier writes: TypeScript ESM imports ``./x.js`` for the ``x.ts`` it compiles
    from, so its ``.js`` is stripped and the sources searched, while JavaScript's own ``./x.js``
    names a real file and is tried as written first (``exact``). ``commonjs`` admits
    `module.exports` and `exports.X` as exports, which the TypeScript dialect does not read.
    ``config_names`` are the compiler configurations whose ``outDir``/``rootDir`` say what build
    output was built from, the first that declares options winning. ``declared`` finds the names a
    file declares behind `export`.
    """

    suffixes: tuple[str, ...]
    strip: re.Pattern[str]
    config_names: tuple[str, ...]
    exact: bool = False
    commonjs: bool = False
    declared: re.Pattern[str] = _DECLARED

    @property
    def index_names(self) -> tuple[str, ...]:
        return tuple(f"index{suffix}" for suffix in self.suffixes)


TYPESCRIPT_MODULES = ModuleDialect(
    suffixes=(".ts", ".tsx"),
    strip=re.compile(r"\.(js|ts)$"),
    config_names=("tsconfig.json",),
)
JAVASCRIPT_MODULES = ModuleDialect(
    suffixes=(".js", ".mjs", ".cjs"),
    strip=re.compile(r"\.(?:js|mjs|cjs)$"),
    config_names=("jsconfig.json", "tsconfig.json"),
    exact=True,
    commonjs=True,
    declared=_DECLARED_JAVASCRIPT,
)


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


def compiler_options(
    package: Path, names: Sequence[str] = TYPESCRIPT_MODULES.config_names
) -> dict[str, Any]:
    """The package's own compiler options from the first of ``names`` that declares any, or an
    empty mapping (`tsconfig.json` unless the caller's dialect names others)."""
    for name in names:
        options = read_json(package / name).get("compilerOptions")
        if isinstance(options, dict):
            return options
    return {}


# --- Manifest ----------------------------------------------------------------------------------


def detect_manifest(
    root: Path, globs: Sequence[str], configuration: Sequence[str] = ()
) -> Path | None:
    """The `package.json` that governs the package.

    Ranked by what a package manifest looks like rather than by depth alone: one that declares a
    name, one with a compiler configuration beside it, then depth, then path so the choice is
    deterministic. Copies under `node_modules`, `dist` and the rest carry a `package.json` of
    their own and are excluded outright - a dependency's manifest would otherwise name the package
    for us.
    """
    candidates = [
        path
        for pattern in globs
        for path in root.rglob(pattern)
        if not any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
    ]
    if not candidates:
        return None

    def rank(path: Path) -> tuple[int, int, int, str]:
        declared = read_json(path)
        named = bool(str(declared.get("name", "")).strip())
        configured = any((path.parent / name).is_file() for name in configuration)
        return (
            0 if named else 1,
            0 if configured else 1,
            len(path.relative_to(root).parts),
            str(path),
        )

    return min(candidates, key=rank)


# What `dependencies` a consumer of the published package installs, and what is only the
# repository's own build. `peerDependencies` are required of the consumer, which is what makes
# them required here; `optionalDependencies` are the Optional bucket the contract renders.
_REQUIRED_SECTIONS = (
    ("dependencies", "dependencies"),
    ("peerDependencies", "peer dependency the consumer installs"),
)
_DEVELOPMENT_SECTION = "devDependencies"
_OPTIONAL_SECTION = "optionalDependencies"


def dependency_facts(manifest: Path, where: str) -> list[Fact]:
    """The dependency snapshot from the manifest's own sections.

    `docs/README_CONTRACT.md` §2 row 9 wants every required requirement, or the verified-zero
    marker citing the clause that proves it. The vendored reader returns dependency *names* for
    JavaScript and no version and no development section at all, so the versions are read from the
    manifest here - the same shape the .NET plugin uses to read a project file's package
    references, and for the same reason: a reader installs a version, not a name.
    """
    declared = read_json(manifest)
    facts: list[Fact] = []
    required = 0
    for section, detail in _REQUIRED_SECTIONS:
        entries = declared.get(section)
        if not isinstance(entries, dict):
            continue
        for name, version in sorted(entries.items()):
            required += 1
            facts.append(
                Fact(
                    fact_id("dependency", str(name)),
                    "dependency",
                    f"{name} {version}".strip(),
                    (
                        Evidence(
                            where, f"declared by `{section}` in the package manifest ({detail})"
                        ),
                    ),
                )
            )
    for section, prefix in ((_OPTIONAL_SECTION, "optional"), (_DEVELOPMENT_SECTION, "development")):
        entries = declared.get(section)
        if not isinstance(entries, dict):
            continue
        for name, version in sorted(entries.items()):
            facts.append(
                Fact(
                    fact_id("dependency", prefix, str(name)),
                    "dependency",
                    f"{name} {version}".strip(),
                    (Evidence(where, f"declared by `{section}` in the package manifest"),),
                )
            )
    if not required:
        facts.append(
            Fact(
                fact_id("dependency", "none"),
                "dependency",
                "none",
                (Evidence(where, "no `dependencies` a consumer would install is declared"),),
            )
        )
    return facts


def manifest_facts(ecosystem: str, root: Path, manifest: Path) -> list[Fact]:
    """Identity, version, the declared Node engine, and the install command it implies."""
    identity = read_identity(root, ecosystem, manifest)
    where = manifest.relative_to(root).as_posix()
    facts: list[Fact] = []
    if identity.name:
        facts.append(
            Fact(
                fact_id("package", "name"),
                "package",
                identity.name,
                (Evidence(where, "package name declared by the manifest"),),
            )
        )
        facts.append(
            Fact(
                fact_id("install_command", "npm"),
                "install_command",
                f"npm install {identity.name}",
                (Evidence(where, "install command for the name declared by the manifest"),),
                polarity="UNRESOLVED",
                confidence=0.5,
            )
        )
        facts.append(
            Fact(
                fact_id("import_path", identity.name),
                "import_path",
                identity.name,
                (Evidence(where, "module specifier a consumer of the package imports"),),
            )
        )
    if identity.version:
        facts.append(
            Fact(
                fact_id("package", "version"),
                "package",
                identity.version,
                (Evidence(where, "version declared by the manifest"),),
            )
        )
    engine = str(identity.raw.get("engines_node", "")).strip()
    if engine:
        facts.append(
            Fact(
                fact_id("package", "node_engine"),
                "package",
                engine,
                (Evidence(where, "Node runtime the manifest declares under `engines`"),),
            )
        )
    facts.extend(dependency_facts(manifest, where))
    return facts


# --- Entry point and re-exports ------------------------------------------------------------------


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


def _sources_for(
    package: Path, specifier: str, options: dict[str, Any], dialect: ModuleDialect
) -> list[Path]:
    """The source files a declared entry-point path could be built from, in preference order.

    A specifier that already names a source resolves to itself. One that names build output is
    mapped through `outDir` and `rootDir`: `dist/index.js` with `outDir: ./dist` and
    `rootDir: ./src` is built from `src/index.ts`, which is the file a clone actually has.
    """
    relative = specifier.lstrip("./").replace("\\", "/")
    stem = _BUILT_SOURCE.sub("", relative)
    candidates = [stem]
    out_dir = str(options.get("outDir", "")).strip().lstrip("./").rstrip("/")
    root_dir = str(options.get("rootDir", "")).strip().lstrip("./").rstrip("/")
    if out_dir and stem.startswith(out_dir + "/"):
        remainder = stem[len(out_dir) + 1 :]
        candidates.append(f"{root_dir}/{remainder}" if root_dir else remainder)
    found: list[Path] = []
    for candidate in candidates:
        shapes = [f"{candidate}{suffix}" for suffix in dialect.suffixes]
        shapes.append(f"{candidate}/{dialect.index_names[0]}")
        for shape in shapes:
            path = package / shape
            if path.is_file() and path not in found:
                found.append(path)
    return found


def _is_barrel(path: Path, dialect: ModuleDialect) -> bool:
    """Whether the file re-exports another module, which is what makes it an entry point.

    Aspose.Cells for TypeScript declares `main: index.ts`, and that file imports a workbook,
    writes two spreadsheets and logs - a demo, not a surface. Its `aspose_cells/index.ts` is the
    barrel. Requiring a re-export separates them without guessing from the name.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if _NAMED_FROM.search(text) or _STAR_FROM.search(text):
        return True
    if not dialect.commonjs:
        return False
    return bool(
        _CJS_WHOLE.search(text)
        or any(
            _CJS_SPREAD.match(item)
            for literal in _CJS_LITERAL.findall(text)
            for item in _split_items(literal)
        )
        or any(match.group(2) for match in _CJS_PROPERTY.finditer(text))
    )


def entry_barrel(
    package: Path, dialect: ModuleDialect, options: dict[str, Any] | None = None
) -> Path | None:
    """The source file that is this package's public entry point, or None when it has none.

    The manifest's own declaration is preferred, mapped back to source where it names build
    output. When nothing it declares resolves to a barrel, the shallowest `index` file in the tree
    that re-exports is taken instead, which is the convention every published package follows and
    the only evidence a repository without a usable manifest field offers.
    """
    manifest = read_json(package / "package.json")
    settings = compiler_options(package, dialect.config_names) if options is None else options
    fallbacks: list[Path] = []
    for specifier in _entry_specifiers(manifest):
        for source in _sources_for(package, specifier, settings, dialect):
            if _is_barrel(source, dialect):
                return source
            fallbacks.append(source)
    barrels = sorted(
        (
            path
            for name in dialect.index_names
            for path in package.rglob(name)
            if not any(part in IGNORED_DIRECTORIES for part in path.relative_to(package).parts)
            and not any(
                part.lower() in _NOT_THE_PRODUCT for part in path.relative_to(package).parts
            )
            and _is_barrel(path, dialect)
        ),
        key=lambda path: (len(path.relative_to(package).parts), str(path)),
    )
    if barrels:
        return barrels[0]
    return fallbacks[0] if fallbacks else None


def _resolve(module_path: Path, specifier: str, dialect: ModuleDialect) -> Path | None:
    """A relative module specifier as the file it names; a package specifier resolves to None."""
    if not specifier.startswith("."):
        return None
    base = (module_path.parent / specifier).resolve()
    if dialect.exact and base.is_file():
        return base
    stem = dialect.strip.sub("", str(base))
    for suffix in dialect.suffixes:
        if Path(f"{stem}{suffix}").is_file():
            return Path(f"{stem}{suffix}")
    for suffix in dialect.suffixes:
        if Path(f"{stem}/index{suffix}").is_file():
            return Path(f"{stem}/index{suffix}")
    return None


def _named(clause: str) -> list[str]:
    """The names one `{ ... }` clause exports, taking the alias where it renames."""
    found: list[str] = []
    for item in clause.split(","):
        match = _ALIAS.fullmatch(item.strip())
        if match:
            found.append(match.group(2) or match.group(1))
    return found


def _split_items(literal: str) -> list[str]:
    """The comma-separated members of a shallow object literal, trimmed and non-empty."""
    return [item.strip() for item in literal.split(",") if item.strip()]


def reexported_bindings(barrel: Path, dialect: ModuleDialect) -> dict[str, frozenset[Path] | None]:
    """Every name the entry point re-exports, and the module each name is bound *from*.

    `export { A } from './x'` publishes the `A` that `x` declares, not every `A` in the tree, so
    the binding is a name *and* a module. A name maps to `None` when the barrel names no module
    this can resolve for it - a local `export { A }`, a package specifier, or the namespace object
    an `export * as ns from` binds - and the caller then has no file to check it against.

    Bounded by a visited set and a file ceiling, because a re-export cycle is legal and a
    generated tree can be large. A `export * as ns from` binds a namespace object rather than the
    names inside it, so its own name is what the package exports and the recursion stops.

    Measured 2026-09-06, which is why the module is carried at all: matching on the name alone
    published `BoundingBoxExtent` twice for Aspose.3D for TypeScript - `utilities/BoundingBox.ts`
    declares one at line 188 while the barrel re-exports only `BoundingBox` from that file and
    takes `BoundingBoxExtent` from its own module - and forty times over for Aspose.Cells, whose
    `util.ts` declares classes named `CellCoordinates` and `CellRange` that the barrel binds from
    `./types` instead. BC-07 rejects exactly that: "recorded 2 times; one fact per canonical
    defining location".
    """
    bindings: dict[str, frozenset[Path] | None] = {}

    def bind(name: str, module: Path | None) -> None:
        if name in bindings and bindings[name] is None:
            return
        if module is None:
            bindings[name] = None
            return
        bindings[name] = frozenset({module}) | (bindings.get(name) or frozenset())

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
            target = _resolve(current, specifier, dialect)
            for name in _named(clause):
                bind(name, target)
        for alias, specifier in _STAR_FROM.findall(text):
            if alias:
                bind(alias, None)
                continue
            target = _resolve(current, specifier, dialect)
            if target is not None:
                queue.append(target)
        for clause in _LOCAL_NAMED.findall(text):
            for name in _named(clause):
                bind(name, None)
        for name in dialect.declared.findall(text):
            bind(name, resolved)
        if dialect.commonjs:
            _commonjs_bindings(current, text, dialect, bind, queue)
    return bindings


def _commonjs_bindings(
    current: Path,
    text: str,
    dialect: ModuleDialect,
    bind: Callable[[str, Path | None], None],
    queue: list[Path],
) -> None:
    """The names `current` assigns to `exports` / `module.exports`, bound as the ESM forms are.

    A whole-module re-export (`module.exports = require('./x')`, or `...require('./x')` inside a
    literal) queues the module so its own assignments are read; a key bound to a `require` is
    bound from that module, and any other key, shorthand member or single assigned name is bound
    unconstrained (`None`), because the local declaration it names is the file's own.
    """
    for specifier in _CJS_WHOLE.findall(text):
        target = _resolve(current, specifier, dialect)
        if target is not None:
            queue.append(target)
    for single in _CJS_SINGLE.findall(text):
        bind(single, None)
    for name, specifier in _CJS_PROPERTY.findall(text):
        bind(name, _resolve(current, specifier, dialect) if specifier else None)
    for literal in _CJS_LITERAL.findall(text):
        for item in _split_items(literal):
            spread = _CJS_SPREAD.match(item)
            if spread:
                target = _resolve(current, spread.group(1), dialect)
                if target is not None:
                    queue.append(target)
                continue
            if _IDENTIFIER.match(item):
                bind(item, None)
                continue
            pair = _CJS_PAIR.match(item)
            if pair:
                bind(
                    pair.group(1),
                    _resolve(current, pair.group(2), dialect) if pair.group(2) else None,
                )


def reexported_names(barrel: Path, dialect: ModuleDialect) -> frozenset[str]:
    """Every name the entry point re-exports, without the module each is bound from."""
    return frozenset(reexported_bindings(barrel, dialect))


# --- Which of a tree's symbols the entry point publishes ------------------------------------------


def public_name(
    value: str,
    kind: str,
    exported: Mapping[str, frozenset[str] | None],
    where: str,
    declaring: Mapping[str, frozenset[str]],
) -> str:
    """A symbol's name as a consumer of the package writes it, or empty when it has none.

    The shared extractor qualifies a TypeScript symbol by the file it was declared in, because
    that is the only qualification the grammar offers: `Scene` in `src/aspose/threed/Scene.ts`
    arrives as `aspose.threed.Scene.Scene`. A consumer never writes that - the entry point
    re-exports `Scene`, so `Scene` is the name, and a symbol the entry point does not re-export is
    not part of the surface at all.

    Re-export is a name *and* a module, so `where` - the file this symbol was declared in - is
    checked against the module the entry point binds that name from, whenever the barrel names
    one. Without it a second declaration of the same name anywhere under the entry point was
    published as if the package exported it twice (`reexported_bindings`).

    A top-level function is the one kind the façade hands back unqualified (`colToIndex`, not
    `aspose_cells.util.colToIndex`), so requiring a dotted value dropped every exported function
    a package has - eight of them in Aspose.Cells for TypeScript, each named in its own barrel.
    Only a `module` entry is never a symbol; every other kind is judged by the binding above,
    which is a stricter test than the dot ever was.
    """
    parts = value.split(".")
    if kind == "module":
        return ""
    if kind == "method":
        if len(parts) < 2:
            return ""
        owner, member = parts[-2], parts[-1]
        return f"{owner}.{member}" if binds(exported, owner, where, declaring) else ""
    name = parts[-1]
    return name if binds(exported, name, where, declaring) else ""


def binds(
    exported: Mapping[str, frozenset[str] | None],
    name: str,
    where: str,
    declaring: Mapping[str, frozenset[str]],
) -> bool:
    """Whether the entry point publishes ``name`` as declared in the file ``where``.

    The file only disqualifies a symbol when it holds a *rival* declaration of that name: an
    inherited member is declared in the base class's own file (the façade reports
    `AssetInfo.AssetInfo.toString` from `A3DObject.ts`, where `toString` is written) and is still
    the exported type's member, while `BoundingBoxExtent.toString` from `utilities/BoundingBox.ts`
    belongs to that file's own second, unexported class of the same name. `declaring` says which
    files declare a type called ``name``, so the two are told apart by evidence rather than by
    whether the member happens to sit in its owner's module.

    Known limitation, deliberately not built for: a barrel that re-exports a name from *another*
    barrel rather than from the declaring file binds the intermediate `index` file, and the
    declaration one level deeper reads as a rival. Neither cohort repository does this - both name
    the declaring module directly and use `export *` for directories - so following the chain is
    machinery with no consumer yet (`project/loop-prompt.md` section 6 rule 1).
    """
    if name not in exported:
        return False
    modules = exported[name]
    if modules is None or where in modules:
        return True
    return where not in declaring.get(name, frozenset())


def declaring_files(symbols: Sequence[Any]) -> dict[str, frozenset[str]]:
    """Which files declare a type of each name, from the extractor's own reading of the tree."""
    found: dict[str, set[str]] = {}
    for symbol in symbols:
        if symbol.symbol_kind in ("method", "module"):
            continue
        found.setdefault(symbol.value.split(".")[-1], set()).add(symbol.source_path)
    return {name: frozenset(paths) for name, paths in found.items()}


def bindings_under(
    root: Path, barrel: Path, dialect: ModuleDialect
) -> dict[str, frozenset[str] | None]:
    """`reexported_bindings` with each module as the tree path a symbol's evidence carries.

    A module that resolves outside the clone is no constraint this can check, so the name it
    binds keeps the unconstrained reading rather than being dropped on a path comparison that
    could never match.
    """
    base = root.resolve()
    bound: dict[str, frozenset[str] | None] = {}
    for name, modules in reexported_bindings(barrel, dialect).items():
        if modules is None:
            bound[name] = None
            continue
        paths: set[str] = set()
        for module in modules:
            try:
                paths.add(module.resolve().relative_to(base).as_posix())
            except ValueError:
                paths.clear()
                break
        bound[name] = frozenset(paths) if paths else None
    return bound


def public_symbol_facts(
    root: Path, barrel: Path, symbols: Sequence[Any], dialect: ModuleDialect
) -> list[Fact]:
    """One `public_symbol` fact per extracted symbol the entry point ``barrel`` publishes.

    ``symbols`` are the extractor's reading of the tree; only those the barrel's re-export closure
    binds survive, named as a consumer writes them (`public_name`). A name taken twice gets a
    numbered ID rather than a collision, and every fact cites the declaring file and line and the
    entry point that makes it reachable.
    """
    exported = bindings_under(root, barrel, dialect)
    where = barrel.relative_to(root).as_posix()
    declaring = declaring_files(symbols)
    facts: list[Fact] = []
    taken: dict[str, int] = {}
    for symbol in symbols:
        name = public_name(
            symbol.value, symbol.symbol_kind, exported, symbol.source_path, declaring
        )
        if not name:
            continue
        key = slug(name)
        count = taken.get(key, 0) + 1
        taken[key] = count
        attributes: dict[str, str] = {"symbol_kind": symbol.symbol_kind}
        if symbol.signature:
            attributes["signature"] = symbol.signature
        if symbol.doc:
            attributes["docstring"] = symbol.doc
        facts.append(
            Fact(
                fact_id("public_symbol", name if count == 1 else f"{name}-{count}"),
                "public_symbol",
                name,
                (
                    Evidence(
                        symbol.source_path,
                        f"line {symbol.line}; {symbol.symbol_kind}; "
                        f"re-exported by the package entry point `{where}`",
                    ),
                ),
                attributes=attributes,
            )
        )
    return facts
