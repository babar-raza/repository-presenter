"""The Go platform plugin: identity from `go.mod`, surface from the shared extractor.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses Go or reads a registry itself: the
`SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem, and
this module supplies only what is Go's own — which manifest governs a module, what an install
command looks like, which files belong to the importable surface at all, and how a symbol's
package becomes part of the name a consumer writes.

Three things are Go's alone and nobody else's. A module path may carry a major-version suffix
(`…/Aspose.Cells-FOSS-for-Go/v26`), and that suffix is part of the path a reader types into
`go get` — dropping it installs a different module or nothing at all. A module's importable
package is not always the module root: Cells keeps a doc-comment-only `doc.go` at the root and
the real package under `aspose/cells_foss`, so the import path needs that subdirectory appended.
And a Go file whose name ends `_test.go`, or which sits under `internal/`, `testdata/` or a
directory whose name starts with `_`, is not importable by a consumer at all — Go's own build
rules say so, and 1,589 of the 3,056 symbols the shared extractor returns for Aspose.PDF for Go
come from exactly those files (measured 2026-09-06).

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper module.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.go_examples import (
    verify_go_examples,
)
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.components.readme.extractors.surface.manifest import (
    PackageIdentity,
    read_identity,
)
from repository_presenter.components.readme.extractors.surface.registry import observe
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Evidence, Fact, Polarity, fact_id
from repository_presenter.core.probes import ProbeRecord

GO = EcosystemSpec(
    ecosystem="go",
    language="Go",
    fence="go",
    registry="pkg.go.dev",
    install_fact_id="install_command:go",
    # pkg.go.dev's own badge is the one a Go reader recognises, and it is keyed by the module
    # path rather than by a short package name, which is why the template takes `{package}`
    # whole - suffix included.
    version_badge="[![Go Reference](https://pkg.go.dev/badge/{package}.svg)](https://pkg.go.dev/{package})",
    # The renderer fills `{module}` with an `import_path` fact - the module path plus the
    # subdirectory the package is declared in - never the module path alone, so `go list -m`
    # is the wrong verb: measured 2026-09-06 in a disposable consumer module after `go get`,
    # `go list -m …/v26/aspose/cells_foss` exits 1 ("not a known dependency") while
    # `go list …/v26/aspose/cells_foss` exits 0 and prints the import path back. `go list` is
    # right for both repositories in this cohort - Cells declares its package below the module
    # root, Aspose.PDF at the root, and the same one line verifies each.
    verify_command="go list {module}",
    # Go names an import by its *quoted* path: `import "path"`, `import alias "path"`, or - most
    # often - a line inside an `import ( … )` block, where the keyword sits on an earlier line
    # entirely. The inherited Python-shaped default wants an unquoted module right after
    # `import`, and matches none of those: measured 2026-09-06, 0 of 8 executed Cells examples
    # and 0 of 5 Aspose.PDF ones, which is why no Go candidate has ever rendered a
    # Verify-the-install block (RESEARCH_AND_GUIDELINES.md section 28.12 G4-W17 arrival item 11,
    # whose mechanism is landed and whose pattern is each ecosystem's own to name).
    import_pattern=r'(?m)^\s*(?:import\s+)?(?:[\w.]+\s+)?"{module}"',
    # A cold `go build` resolves the module graph and compiles the package before it can say
    # anything; the ceiling in core.execution is 300 seconds.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"go", "golang"}),
    floor_fact_id="package:go_version",
    floor_label="Go",
    floor_declaration="go",
    manifest_globs=("go.mod",),
    source_suffixes=frozenset({".go"}),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(GO.ecosystem, GO)

_PARSER_LANGUAGE = "go"
# A directory that carries a `go.mod` of its own but is not the product: Go's own toolchain
# ignores `testdata` and any directory whose name starts with `_` or `.`, and `vendor` holds
# copies of other modules.
_IGNORED_DIRECTORIES = frozenset({"vendor", "testdata", ".git", "node_modules"})
# What a consumer of the published module cannot import, by Go's own rules rather than by
# convention: `internal/` is unreachable outside the module that declares it, `_test.go` files
# are compiled only by `go test`, and a directory whose name starts with `_` or `.` is invisible
# to the go command.
_UNIMPORTABLE_DIRECTORIES = frozenset({"internal", "testdata", "vendor"})
_TEST_SUFFIX = "_test.go"
# `require github.com/x/y v1.2.3`, in the single-line form and inside a `require ( … )` block.
_REQUIRE_LINE = re.compile(r"^\s*(?:require\s+)?([^\s()/][^\s]*)\s+(v[^\s]+)\s*(//.*)?$")
_REQUIRE_BLOCK = re.compile(r"^\s*require\s*\($")
_BLOCK_END = re.compile(r"^\s*\)\s*$")


def import_path(identity: PackageIdentity) -> str:
    """The path a consumer writes in an `import` statement, subdirectory included.

    The module path alone is the import path only when the importable package sits at the module
    root. Cells for Go keeps a documentation-only `doc.go` there and the real `cells_foss`
    package under `aspose/cells_foss`, so `import "…/v26"` resolves to a package with no
    declarations and every symbol in the README would be undefined; the vendored reader reports
    that subdirectory and this is where it is joined on (§29.12).
    """
    module = identity.name
    subpath = str(identity.raw.get("package_subpath", "")).strip("/")
    return f"{module}/{subpath}" if module and subpath else module


def package_directory(root: Path, manifest: Path, identity: PackageIdentity) -> Path:
    """The directory holding the importable package, which the surface is read from."""
    subpath = str(identity.raw.get("package_subpath", "")).strip("/")
    base = manifest.parent if manifest.is_file() else root
    return base.joinpath(*subpath.split("/")) if subpath else base


def importable(source_path: str) -> bool:
    """Whether a file the extractor read belongs to the surface a consumer can import.

    Go's build rules, not a naming convention: `_test.go` is compiled only by `go test`, a path
    under `internal/` is unreachable outside its own module, and the go command ignores a
    directory whose name begins with `_` or `.` outright.
    """
    parts = source_path.split("/")
    if parts[-1].endswith(_TEST_SUFFIX):
        return False
    return not any(
        part in _UNIMPORTABLE_DIRECTORIES or part.startswith(("_", ".")) for part in parts[:-1]
    )


def _requirements(manifest: Path) -> Iterator[tuple[str, str, bool]]:
    """Every `require` directive in ``go.mod``: module path, version, and whether it is indirect.

    Both spellings, because `go.mod` allows either: a single `require path version` line and a
    `require ( … )` block. A directive marked `// indirect` is not imported by this module's own
    code, and its evidence says so rather than pretending the module names it directly.
    """
    try:
        text = manifest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if _REQUIRE_BLOCK.match(line):
            in_block = True
            continue
        if in_block and _BLOCK_END.match(line):
            in_block = False
            continue
        if not in_block and not stripped.startswith("require "):
            continue
        match = _REQUIRE_LINE.match(line)
        if match is None:
            continue
        yield (match.group(1), match.group(2), "indirect" in (match.group(3) or ""))


def _dependency_facts(manifest: Path, where: str) -> list[Fact]:
    """The dependency snapshot from `go.mod`'s own `require` directives.

    `docs/README_CONTRACT.md` §2 row 9 wants every required requirement, or the verified-zero
    marker citing the clause that proves it. The vendored reader returns a Go module's identity
    and its language version but no requirements at all (§29.12), so they are read here - the
    same shape the .NET plugin uses for a project file's package references, and for the same
    reason: a reader installs a version, not a name. Measured 2026-09-06: neither Cells for Go
    nor Aspose.PDF for Go declares a single requirement, which is a verified zero, not a gap.
    """
    facts: list[Fact] = []
    direct = 0
    for name, version, indirect in _requirements(manifest):
        direct += 0 if indirect else 1
        detail = (
            "required by the module, resolved indirectly (`// indirect`)"
            if indirect
            else ("module requirement declared by `require` in the module file")
        )
        facts.append(
            Fact(
                fact_id("dependency", name),
                "dependency",
                f"{name} {version}".strip(),
                (Evidence(where, detail),),
            )
        )
    if not direct:
        facts.append(
            Fact(
                fact_id("dependency", "none"),
                "dependency",
                "none",
                (Evidence(where, "no `require` directive a consumer would install is declared"),),
            )
        )
    return facts


class GoPlugin:
    """What the facts stage asks of Go."""

    ecosystem = GO.ecosystem
    manifest_globs = GO.manifest_globs
    source_suffixes = GO.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `go.mod` that declares the published module.

        A repository may carry more than one: a `tools/go.mod` for its build helpers, an
        `_examples/go.mod` so the samples resolve, a `vendor` copy. The published module is the
        outermost one that is not inside a directory Go itself ignores, so the ranking is
        depth first and then path, with those directories excluded outright.
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(
                part in _IGNORED_DIRECTORIES or part.startswith(("_", "."))
                for part in path.relative_to(root).parts[:-1]
            )
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda path: (len(path.relative_to(root).parts), str(path)))

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Module path, import path, the declared Go version, and the install command."""
        identity = read_identity(root, self.ecosystem, manifest)
        where = manifest.relative_to(root).as_posix()
        facts: list[Fact] = []
        if identity.name:
            facts.append(
                Fact(
                    fact_id("package", "name"),
                    "package",
                    identity.name,
                    (Evidence(where, "module path declared by the module file"),),
                )
            )
            facts.append(
                Fact(
                    fact_id("install_command", "go"),
                    "install_command",
                    f"go get {identity.name}",
                    (
                        Evidence(
                            where,
                            "install command for the module path declared by the manifest, "
                            "major-version suffix included",
                        ),
                    ),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )
            path = import_path(identity)
            facts.append(
                Fact(
                    fact_id("import_path", path),
                    "import_path",
                    path,
                    (
                        Evidence(
                            where,
                            "import path of the module's importable package"
                            + (
                                ", module path and the subdirectory the package is declared in"
                                if path != identity.name
                                else ""
                            ),
                        ),
                    ),
                )
            )
        version = str(identity.raw.get("go_version", "")).strip()
        if version:
            facts.append(
                Fact(
                    fact_id("package", "go_version"),
                    "package",
                    version,
                    (Evidence(where, "Go language version the module file declares"),),
                )
            )
        facts.extend(_dependency_facts(manifest, where))
        return facts

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """Exported declarations of the module's importable packages, read by the extractor.

        A name a consumer writes is qualified by the package it lives in, so a symbol declared
        in a package below the module's own root - Aspose.PDF for Go's `ai` package - carries
        that package in its value, and the package itself is a symbol too, exactly as a .NET
        namespace is. A symbol from a file Go would not let a consumer import is dropped before
        any of that: it never was part of the surface.
        """
        from tree_sitter_language_pack import get_parser

        manifest = self.detect_manifest(root)
        if manifest is None:
            return []
        identity = read_identity(root, self.ecosystem, manifest)
        package_root = package_directory(root, manifest, identity)
        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, package_root, root, self.ecosystem
        )
        prefix = package_root.relative_to(root).as_posix()
        facts: list[Fact] = []
        packages: dict[str, tuple[str, int]] = {}
        for symbol in symbols:
            if not importable(symbol.source_path):
                continue
            package = _package_of(symbol.source_path, prefix)
            value = f"{package}.{symbol.value}" if package else symbol.value
            if package and package not in packages:
                packages[package] = (symbol.source_path, symbol.line)
            attributes: dict[str, str] = {"symbol_kind": symbol.symbol_kind}
            if symbol.signature:
                attributes["signature"] = symbol.signature
            if symbol.doc:
                attributes["docstring"] = symbol.doc
            facts.append(
                Fact(
                    fact_id("public_symbol", value),
                    "public_symbol",
                    value,
                    (
                        Evidence(
                            symbol.source_path,
                            f"line {symbol.line}; {symbol.symbol_kind}; "
                            "exported by an upper-case name",
                        ),
                    ),
                    attributes=attributes,
                )
            )
        return [
            Fact(
                fact_id("public_symbol", package),
                "public_symbol",
                package,
                (Evidence(where, f"line {line}; module; package below the module root"),),
                attributes={"symbol_kind": "module"},
            )
            for package, (where, line) in sorted(packages.items())
        ] + facts

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against the Go module proxy; the fact keeps its ID."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(GO.install_fact_id)
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
                Evidence(reading.evidence_url or reading.registry or GO.registry, reading.summary),
            ),
            polarity=polarity,
            confidence=confidence,
        )
        probe = ProbeRecord(
            kind="registry",
            target=f"{reading.registry or GO.registry}:{name.value}",
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
        """Build and vet each candidate against the module's own sources in a disposable profile.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        if manifest is None:
            return verify_go_examples(
                root, "", "", "", candidates, workspace, GO.example_timeout_seconds
            )
        identity = read_identity(root, self.ecosystem, manifest)
        return verify_go_examples(
            manifest.parent,
            identity.name,
            import_path(identity),
            str(identity.raw.get("go_version", "")).strip(),
            candidates,
            workspace,
            GO.example_timeout_seconds,
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


def _package_of(source_path: str, prefix: str) -> str:
    """The dotted package a file's symbols belong to, empty for the module's own root package."""
    parts = source_path.split("/")[:-1]
    root = prefix.split("/") if prefix else []
    if parts[: len(root)] == root:
        parts = parts[len(root) :]
    return ".".join(parts)


PLUGIN: Any = GoPlugin()
