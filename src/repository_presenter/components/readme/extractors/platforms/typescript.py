"""The TypeScript platform plugin: identity from `package.json`, surface from the entry point.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses TypeScript or reads a registry itself:
the `SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem,
and this module supplies only what is TypeScript's own — which manifest governs a package, what an
install command looks like, and which of the many symbols a tree declares the package actually
publishes.

That last one is the difference from every ecosystem before it. C# has `public`, Python has
`__all__`, and TypeScript has neither at module scope: a file says `export` so its sibling can
import it, and only the entry point the manifest declares decides what a consumer can reach. So
the surface here is the tree's symbols filtered by `typescript_barrel`'s re-export closure -
measured 2026-09-06, that is 81 names of 153 extracted types on Aspose.3D for TypeScript and 43 of
its own count on Aspose.Cells; publishing the rest would put a package's internals in a public API
reference.

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper modules.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.typescript_barrel import (
    IGNORED_DIRECTORIES,
    entry_barrel,
    read_json,
    reexported_names,
)
from repository_presenter.components.readme.extractors.platforms.typescript_examples import (
    verify_typescript_examples,
)
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.components.readme.extractors.surface.registry import observe
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Evidence, Fact, Polarity, fact_id, slug
from repository_presenter.core.probes import ProbeRecord

TYPESCRIPT = EcosystemSpec(
    ecosystem="typescript",
    language="TypeScript",
    fence="typescript",
    registry="npm",
    install_fact_id="install_command:npm",
    version_badge=(
        "[![npm](https://img.shields.io/npm/v/{package}.svg)](https://www.npmjs.com/package/"
        "{package})"
    ),
    verify_command="npm ls {module}",
    # tsc type-checks a snippet against a few hundred source files in seconds; the ceiling in
    # core.execution is 300 and the whole cohort has never come near it.
    example_timeout_seconds=180.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"typescript", "ts", "tsx"}),
    # The floor a `package.json` actually declares about the runtime is `engines.node`; the
    # `typescript` devDependency is a build tool, and rendering it as a consumer's requirement
    # would tell a reader to install a compiler to use a published package. A package that
    # declares no engine gets no requirement line, which is what the manifest supports.
    floor_fact_id="package:node_engine",
    floor_label="Node.js",
    floor_declaration="engines.node",
    manifest_globs=("package.json",),
    source_suffixes=frozenset({".ts", ".tsx"}),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(TYPESCRIPT.ecosystem, TYPESCRIPT)

_PARSER_LANGUAGE = "typescript"
# What `dependencies` a consumer of the published package installs, and what is only the
# repository's own build. `peerDependencies` are required of the consumer, which is what makes
# them required here; `optionalDependencies` are the Optional bucket the contract renders.
_REQUIRED_SECTIONS = (
    ("dependencies", "dependencies"),
    ("peerDependencies", "peer dependency the consumer installs"),
)
_DEVELOPMENT_SECTION = "devDependencies"
_OPTIONAL_SECTION = "optionalDependencies"


def _dependency_facts(manifest: Path, where: str) -> list[Fact]:
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


def _public_name(value: str, kind: str, exported: frozenset[str]) -> str:
    """A symbol's name as a consumer of the package writes it, or empty when it has none.

    The shared extractor qualifies a TypeScript symbol by the file it was declared in, because
    that is the only qualification the grammar offers: `Scene` in `src/aspose/threed/Scene.ts`
    arrives as `aspose.threed.Scene.Scene`. A consumer never writes that - the entry point
    re-exports `Scene`, so `Scene` is the name, and a symbol the entry point does not re-export is
    not part of the surface at all.
    """
    parts = value.split(".")
    if kind == "module" or len(parts) < 2:
        return ""
    if kind == "method":
        owner, member = parts[-2], parts[-1]
        return f"{owner}.{member}" if owner in exported else ""
    return parts[-1] if parts[-1] in exported else ""


class TypeScriptPlugin:
    """What the facts stage asks of TypeScript."""

    ecosystem = TYPESCRIPT.ecosystem
    manifest_globs = TYPESCRIPT.manifest_globs
    source_suffixes = TYPESCRIPT.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `package.json` that governs the package.

        Ranked by what a package manifest looks like rather than by depth alone: one that declares
        a name, one with a `tsconfig.json` beside it, then depth, then path so the choice is
        deterministic. Copies under `node_modules`, `dist` and the rest carry a `package.json` of
        their own and are excluded outright - a dependency's manifest would otherwise name the
        package for us.
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(part in IGNORED_DIRECTORIES for part in path.parts)
        ]
        if not candidates:
            return None

        def rank(path: Path) -> tuple[int, int, int, str]:
            declared = read_json(path)
            named = bool(str(declared.get("name", "")).strip())
            configured = (path.parent / "tsconfig.json").is_file()
            return (
                0 if named else 1,
                0 if configured else 1,
                len(path.relative_to(root).parts),
                str(path),
            )

        return min(candidates, key=rank)

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the declared Node engine, and the install command it implies."""
        identity = read_identity(root, self.ecosystem, manifest)
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
        facts.extend(_dependency_facts(manifest, where))
        return facts

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """The symbols the package's entry point re-exports, read from the tree by the extractor.

        A repository whose entry point cannot be resolved has no evidence for what it publishes,
        so it publishes nothing here rather than every `export` in the tree.
        """
        from tree_sitter_language_pack import get_parser

        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        barrel = entry_barrel(package)
        if barrel is None:
            return []
        exported = reexported_names(barrel)
        where = barrel.relative_to(root).as_posix()
        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, barrel.parent, root, self.ecosystem
        )
        facts: list[Fact] = []
        taken: dict[str, int] = {}
        for symbol in symbols:
            name = _public_name(symbol.value, symbol.symbol_kind, exported)
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

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against npm; the fact keeps its ID and gains evidence."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(TYPESCRIPT.install_fact_id)
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value)
        polarity: Polarity
        if not reading.conclusive:
            polarity, confidence = "UNRESOLVED", 0.5
        elif reading.published:
            polarity, confidence = "SUPPORTED", 1.0
        else:
            polarity, confidence = "CONTRADICTED", 1.0
        resolved = Fact(
            install.id,
            install.kind,
            install.value,
            (
                *install.evidence,
                Evidence(reading.evidence_url or reading.registry, reading.summary),
            ),
            polarity=polarity,
            confidence=confidence,
        )
        probe = ProbeRecord(
            kind="registry",
            target=f"{reading.registry}:{name.value}",
            outcome=polarity,
            status=None,
            elapsed_ms=0,
            observation=reading.method or reading.source,
        )
        return [resolved], [probe]

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        """Type-check each candidate against the package's own sources in a disposable profile.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        return verify_typescript_examples(
            package,
            entry_barrel(package),
            candidates,
            workspace,
            TYPESCRIPT.example_timeout_seconds,
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = TypeScriptPlugin()
