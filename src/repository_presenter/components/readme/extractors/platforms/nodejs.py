"""The Node.js platform plugin: identity from `package.json`, surface from the package entry point.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. A pure-JavaScript npm package - no `.ts` anywhere, as in
aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js - is the TypeScript case without the types. It has
no `public` at module scope either, so the surface is the tree's symbols filtered by what the
entry point the manifest declares exports: `export { A } from './a.js'`, `export * from`, a local
`export { A }`, or the CommonJS forms `module.exports = { A, B }`, `exports.A = ...` and
`module.exports = require('./x')`. Descriptions are the JSDoc blocks the extractor reads before
each declaration.

Nothing here parses JavaScript or reads a registry itself. The `SurfaceExtractor`, manifest and
`RegistryProbe` façades do that for every ecosystem, and `surface/npm_package.py` holds everything
an npm package shares whatever its language - manifest facts, the entry point, the re-export
closure and the name-and-module filter - composed here with the JavaScript `ModuleDialect`
(`.js`/`.mjs`/`.cjs`, CommonJS read). This module never imports the TypeScript plugin, and the
TypeScript plugin never imports this one (`docs/REPOSITORY_LAYOUT.md` §2.1).

The grammar is TypeScript's: its wheel parses JavaScript as a subset, so no second grammar is
pinned for a language the same tree-sitter package already reads. A file with JSX would not parse
cleanly under it; none of the packages this plugin serves ships one.

Two known limits, measured on the Node.js JMAP library and not built for. A class assembled at its
entry point from mixins (`Object.assign(JmapClient.prototype, MailClientMixin)`) has the members
of its base and mixins declared elsewhere, behind an import alias the extractor does not follow, so
only what the class body itself declares is a fact; a claim about a mixed-in member stays
unsupported rather than invented. And the vendored engine keys a JavaScript class by its bare name
(it qualifies a TypeScript one by module path), so two classes of one name in different files are
one class to it: it keeps one (folding the members of the rest into it, each member's evidence
still naming the file that declares it), and the name is published only if the entry point binds
it from the kept file. Neither limit ever yields a second fact for one name.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.nodejs_examples import (
    verify_nodejs_build,
    verify_nodejs_examples,
)
from repository_presenter.components.readme.extractors.surface import npm_package
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.components.readme.extractors.surface.npm_package import (
    JAVASCRIPT_MODULES,
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

NODEJS = EcosystemSpec(
    ecosystem="nodejs",
    language="JavaScript",
    fence="javascript",
    registry="npm",
    install_fact_id="install_command:npm",
    version_badge=(
        "[![npm](https://img.shields.io/npm/v/{package}.svg)](https://www.npmjs.com/package/"
        "{package})"
    ),
    verify_command="npm ls {module}",
    # `import_pattern` is deliberately left at the default (`import x`), which a quoted specifier
    # never matches, so no Verify-the-install block is rendered - the same state TypeScript is in.
    # The renderer prints that block whatever the install kind, and `npm ls <name>` proves nothing
    # for a package built from a source checkout, which is the only state the one Node.js library
    # is in (not published on npm). Teach the pattern to read `from "x"` and `require("x")` only
    # together with a renderer rule that withholds the block for a source install.
    # A snippet is checked by `node --check` and by loading its imports against the package's own
    # sources: seconds, and an `npm install` of the package's dependencies is the only slow step.
    example_timeout_seconds=120.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"javascript", "js", "mjs", "cjs", "node", "nodejs"}),
    # The floor a `package.json` declares about the runtime is `engines.node`, as for TypeScript;
    # a package that declares no engine gets no requirement line.
    floor_fact_id="package:node_engine",
    floor_label="Node.js",
    floor_declaration="engines.node",
    floor_is_minimum=True,
    manifest_globs=("package.json",),
    source_suffixes=frozenset({".js", ".mjs", ".cjs"}),
    # The built-in `node --test` runner collects `*.test.js`, `*-test.js`, `*_test.js` and
    # `test-*.js`; Jest, Vitest and Mocha collect `*.test.*` and `*.spec.*`. A helper or fixture
    # beside the tests is not a test, and a suite that names its tests otherwise gets no size.
    suite_files=SuiteFileRule(name=r"(?:[._-](?:test|spec)\.[cm]?jsx?$|^test-.+\.[cm]?jsx?$)"),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(NODEJS.ecosystem, NODEJS)

# JavaScript is read by the TypeScript grammar (a superset), under the language name the vendored
# engine's own JavaScript branches key on.
_GRAMMAR = "typescript"
_ENGINE_LANGUAGE = "javascript"


class NodeJsPlugin:
    """What the facts stage asks of a pure-JavaScript npm package."""

    ecosystem = NODEJS.ecosystem
    manifest_globs = NODEJS.manifest_globs
    source_suffixes = NODEJS.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `package.json` that governs the package.

        Ranked as for every npm package: one that declares a name, one with a `jsconfig.json` (or
        `tsconfig.json`) beside it, then depth, then path so the choice is deterministic. A copy
        under `node_modules` or `dist` is excluded outright - a dependency's manifest would
        otherwise name the package for us.
        """
        return npm_package.detect_manifest(
            root, self.manifest_globs, JAVASCRIPT_MODULES.config_names
        )

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the declared Node engine, and the install command it implies."""
        return npm_package.manifest_facts(self.ecosystem, root, manifest)

    def entry_barrel(self, package: Path) -> Path | None:
        """The source file that is the package's public entry point, or None when it has none."""
        return npm_package.entry_barrel(package, JAVASCRIPT_MODULES)

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """The symbols the package's entry point exports, read from the tree by the extractor.

        A repository whose entry point cannot be resolved has no evidence for what it publishes,
        so it publishes nothing here rather than every top-level declaration in the tree.
        """
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        barrel = self.entry_barrel(package)
        if barrel is None:
            return []
        symbols = surface_symbols(
            get_parser(_GRAMMAR), _ENGINE_LANGUAGE, barrel.parent, root, self.ecosystem
        )
        return npm_package.public_symbol_facts(root, barrel, symbols, JAVASCRIPT_MODULES)

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against npm; the fact keeps its ID and gains evidence."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(NODEJS.install_fact_id)
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
        """Check each candidate's syntax and its imports of the package, in a disposable copy.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        return verify_nodejs_examples(
            package,
            self.entry_barrel(package),
            candidates,
            workspace,
            NODEJS.example_timeout_seconds,
            NODEJS.install_timeout_seconds,
        )

    def verify_build(self, root: Path, manifest: Path, workspace: Path) -> MeasuredBuild:
        """The package's own `npm install` (and `npm run build`, if declared), with no example.

        A registry 404 for the declared package (`install_command:npm` CONTRADICTED) is admitted
        only as the source install these steps exited 0 on; the one rule is in
        `evidence/facts/extract.py`, and `registry.verify_build` is what calls this.
        """
        return verify_nodejs_build(manifest.parent, workspace, NODEJS.install_timeout_seconds)

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not built; a format declaration this plugin cannot read is no declaration at all."""
        return []


PLUGIN: Any = NodeJsPlugin()
