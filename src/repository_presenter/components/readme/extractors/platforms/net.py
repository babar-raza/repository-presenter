"""The .NET platform plugin: identity from the project file, surface from the shared extractor.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses C# or reads a registry itself: the
`SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem, and
this module supplies only what is .NET's own — which manifest governs a project, what an install
command looks like, and how a symbol's provenance becomes a fact's evidence.

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from repository_presenter.components.readme.extractors.platforms.net_examples import (
    verify_net_examples,
)
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.components.readme.extractors.surface.registry import observe
from repository_presenter.core.ecosystems import NET
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Evidence, Fact, Polarity, fact_id
from repository_presenter.core.probes import ProbeRecord

_PARSER_LANGUAGE = "csharp"
# Build output and version control carry copies of the project file; a directory whose name says
# it is a sample, a test or a benchmark carries a project that is not the product.
_IGNORED_DIRECTORIES = frozenset({"bin", "obj", ".git", "packages", "node_modules"})
_NOT_THE_PRODUCT = frozenset(
    {"samples", "sample", "examples", "example", "demo", "demos", "tests", "test", "benchmarks"}
)
# A project builds something; `Directory.Build.props` only lends properties to the projects
# beside it, and it sits at the repository root, where depth alone would always prefer it.
_PROJECT_SUFFIXES = frozenset({".csproj", ".fsproj"})
_EXECUTABLE_OUTPUTS = frozenset({"exe", "winexe"})
# A project that references a test runner is a test project even when it never says so: measured
# 2026-09-06 on Aspose.Words for .NET, whose `Aspose.JavaMs.Tests` declares no `IsTestProject`,
# no `IsPackable` and no `OutputType`, and sorted ahead of `Aspose.Words` at the same depth.
_TEST_PACKAGES = ("microsoft.net.test.sdk", "xunit", "nunit", "mstest")


def _declares(project: Path) -> tuple[bool, bool]:
    """Whether the project file says it is a test project, and whether it builds an executable.

    Both are declarations, not inferences from a name: `IsTestProject`, `IsPackable` and a
    reference to a test runner say a project ships nothing, and `OutputType` says a project is an
    application rather than the library a package publishes. A file that will not parse claims
    neither, which leaves the remaining keys to rank it.
    """
    try:
        root = ElementTree.parse(project).getroot()
    except (OSError, ElementTree.ParseError):
        return (False, False)
    properties: dict[str, str] = {}
    packages: list[str] = []
    for element in root.iter():
        # Old-style projects carry the MSBuild namespace on every tag; SDK-style carry none.
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag == "packagereference":
            packages.append(str(element.get("Include", "")).strip().lower())
        elif element.text is not None:
            properties[tag] = element.text.strip().lower()
    is_test = (
        properties.get("istestproject") == "true"
        or properties.get("ispackable") == "false"
        or any(package.startswith(_TEST_PACKAGES) for package in packages)
    )
    return (is_test, properties.get("outputtype", "") in _EXECUTABLE_OUTPUTS)


class NetPlugin:
    """What the facts stage asks of .NET."""

    ecosystem = NET.ecosystem
    manifest_globs = NET.manifest_globs
    source_suffixes = NET.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The project file that governs the package.

        Depth alone is not enough: a repository that ships `samples/Demo/Demo.csproj` beside
        `src/Aspose.Widget/Aspose.Widget.csproj` has two project files at the same depth, and
        sorting by path lets the sample win. Ranked instead by what a product project looks like -
        a project rather than a shared property file, not a test project, not an application, not
        under a directory whose name says it is not the product, and with C# sources beside it -
        then by depth, then by path so the choice is deterministic.

        Measured 2026-09-06 on the .NET cohort. Aspose.3D ships `src/converter/Converter.csproj`
        one directory above the library it references, so depth chose the console tool, whose
        only source declares no public type: the repository produced zero public symbols and the
        API Reference row had no evidence at all. Email, Slides and Words each carry a
        `Directory.Build.props` at the root, which depth preferred over every project, so the
        surface was read from the whole tree - tests and samples included.
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(part in _IGNORED_DIRECTORIES for part in path.parts)
        ]
        if not candidates:
            return None

        def rank(path: Path) -> tuple[int, int, int, int, int, int, str]:
            parts = path.relative_to(root).parts
            is_project = path.suffix.lower() in _PROJECT_SUFFIXES
            is_test, is_executable = _declares(path) if is_project else (False, False)
            aside = any(part.lower() in _NOT_THE_PRODUCT for part in parts)
            sources = any(path.parent.rglob("*.cs"))
            return (
                0 if is_project else 1,
                int(is_test),
                int(is_executable),
                int(aside),
                0 if sources else 1,
                len(parts),
                str(path),
            )

        return min(candidates, key=rank)

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the lowest target framework, and the install command it implies."""
        identity = read_identity(root, self.ecosystem)
        where = manifest.relative_to(root).as_posix()
        facts: list[Fact] = []
        if identity.name:
            facts.append(
                Fact(
                    fact_id("package", "name"),
                    "package",
                    identity.name,
                    (Evidence(where, "package id declared by the project file"),),
                )
            )
            facts.append(
                Fact(
                    fact_id("install_command", "dotnet"),
                    "install_command",
                    f"dotnet add package {identity.name}",
                    (Evidence(where, "install command for the declared package id"),),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )
        if identity.version:
            facts.append(
                Fact(
                    fact_id("package", "version"),
                    "package",
                    identity.version,
                    (Evidence(where, "version declared by the project file"),),
                )
            )
        if identity.floor:
            facts.append(
                Fact(
                    fact_id("package", "target_framework"),
                    "package",
                    identity.floor,
                    (Evidence(where, "lowest target framework the project declares"),),
                )
            )
        return facts

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """Public types and members, read from the tree by the shared extractor."""
        from tree_sitter_language_pack import get_parser

        package_root = self.detect_manifest(root)
        source_root = package_root.parent if package_root is not None else root
        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, source_root, root, self.ecosystem
        )
        facts: list[Fact] = []
        for symbol in symbols:
            attributes: dict[str, str] = {"symbol_kind": symbol.symbol_kind}
            if symbol.signature:
                attributes["signature"] = symbol.signature
            if symbol.doc:
                attributes["docstring"] = symbol.doc
            facts.append(
                Fact(
                    fact_id("public_symbol", symbol.fact_slug),
                    "public_symbol",
                    symbol.value,
                    (
                        Evidence(
                            symbol.source_path,
                            f"line {symbol.line}; {symbol.symbol_kind}; public by declaration",
                        ),
                    ),
                    attributes=attributes,
                )
            )
        return facts

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against NuGet; the fact keeps its ID and gains evidence."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get("install_command:dotnet")
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value)
        polarity: Polarity
        if not reading.conclusive:
            polarity, confidence = "UNRESOLVED", 0.5
            detail = f"{reading.registry or 'no registry'} could not be read conclusively"
        elif reading.published:
            polarity, confidence = "SUPPORTED", 1.0
            detail = f"published on {reading.registry}"
        else:
            polarity, confidence = "CONTRADICTED", 1.0
            detail = f"not found on {reading.registry}"
        resolved = Fact(
            install.id,
            install.kind,
            install.value,
            (*install.evidence, Evidence(reading.evidence_url or reading.registry, detail)),
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
        """Not yet built: every candidate is reported unverified, never contradicted.

        A toolchain result this plugin cannot produce must read as "we did not check", so the
        facts stage writes UNRESOLVED (§29.6 E5). The verifier lands with the cohort run.
        """
        project = self.detect_manifest(root)
        framework = ""
        if project is not None:
            framework = read_identity(root, self.ecosystem).floor
        return verify_net_examples(root, project, framework, candidates, workspace)

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = NetPlugin()
