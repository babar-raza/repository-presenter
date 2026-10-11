"""The TypeScript platform plugin: identity from `package.json`, surface from the entry point.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses TypeScript or reads a registry itself:
the `SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem,
and this module supplies only what is TypeScript's own — which manifest governs a package, what an
install command looks like, and which of the many symbols a tree declares the package actually
publishes.

That last one is the difference from every ecosystem before it. C# has `public`, Python has
`__all__`, and TypeScript has neither at module scope: a file says `export` so its sibling can
import it, and only the entry point the manifest declares decides what a consumer can reach. So
the surface here is the tree's symbols filtered by the entry point's re-export closure - measured
2026-09-06, that is 81 names of 153 extracted types on Aspose.3D for TypeScript and 43 of its own
count on Aspose.Cells; publishing the rest would put a package's internals in a public API
reference. The npm-package half of that (manifest facts, the closure, the name-and-module filter)
is shared with the Node.js plugin through `surface/npm_package.py`.

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper modules.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.typescript_barrel import (
    entry_barrel,
)
from repository_presenter.components.readme.extractors.platforms.typescript_examples import (
    verify_typescript_build,
    verify_typescript_examples,
)
from repository_presenter.components.readme.extractors.surface import npm_package
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.components.readme.extractors.surface.npm_package import (
    TYPESCRIPT_MODULES,
)
from repository_presenter.components.readme.extractors.surface.registry import (
    observe,
    repository_of,
)
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec, SuiteFileRule
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
    MeasuredBuild,
)
from repository_presenter.core.facts import Evidence, Fact
from repository_presenter.core.grammars import get_parser
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
    source_dependencies="npm install",
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
    floor_is_minimum=True,
    manifest_globs=("package.json",),
    source_suffixes=frozenset({".ts", ".tsx"}),
    # Jest, Vitest, and Mocha all collect `*.test.*` and `*.spec.*`; `tests/setup.ts` (a global
    # hook the runner loads first) and fixtures beside them are not tests. A suite that names
    # its tests otherwise gets no size rather than a guess.
    suite_files=SuiteFileRule(name=r"\.(?:test|spec)\.[cm]?[jt]sx?$"),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(TYPESCRIPT.ecosystem, TYPESCRIPT)

_PARSER_LANGUAGE = "typescript"


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
        return npm_package.detect_manifest(
            root, self.manifest_globs, TYPESCRIPT_MODULES.config_names
        )

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the declared Node engine, and the install command it implies."""
        return npm_package.manifest_facts(self.ecosystem, root, manifest)

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """The symbols the package's entry point re-exports, read from the tree by the extractor.

        A repository whose entry point cannot be resolved has no evidence for what it publishes,
        so it publishes nothing here rather than every `export` in the tree.
        """
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        barrel = entry_barrel(package)
        if barrel is None:
            return []
        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, barrel.parent, root, self.ecosystem
        )
        return npm_package.public_symbol_facts(root, barrel, symbols, TYPESCRIPT_MODULES)

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against npm; the fact keeps its ID and gains evidence."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(TYPESCRIPT.install_fact_id)
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value, repository=repository_of(facts))
        polarity, confidence, detail = reading.install_verdict()
        resolved = Fact(
            install.id,
            install.kind,
            install.value,
            (
                *install.evidence,
                Evidence(reading.evidence_url or reading.registry, detail),
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
            TYPESCRIPT.install_timeout_seconds,
        )

    def verify_build(self, root: Path, manifest: Path, workspace: Path) -> MeasuredBuild:
        """The package's own `npm install` and `npm run build`, measured with no example needed.

        A registry 404 for the declared package (`install_command:npm` CONTRADICTED) is admitted
        only as the source install these steps exited 0 on; the one rule is in
        `evidence/facts/extract.py`, and `registry.verify_build` is what calls this.
        """
        return verify_typescript_build(
            manifest.parent, workspace, TYPESCRIPT.install_timeout_seconds
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = TypeScriptPlugin()
