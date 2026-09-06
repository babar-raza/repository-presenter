"""The Rust platform plugin: identity from `Cargo.toml`, surface from the shared extractor.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses Rust or reads a registry itself: the
`SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem, and
this module supplies only what is Rust's own.

Three things are Rust's alone. A crate is *named* one thing and *imported* as another - Cargo
publishes `aspose-cells-foss-rust` and a consumer writes `use aspose_cells_foss_rust::…` - so the
install command and the import path are two different strings from two different keys, and the
vendored reader reports the second as `canonical_package` (§29.12). A crate's declared
compatibility floor is usually its *edition* rather than a compiler version: `rust-version` is
optional and Aspose.Cells for Rust declares none, while `edition = "2021"` is what the manifest
really commits to, so the floor is reported in the vocabulary the manifest used. And a Rust source
file that a consumer of the published crate cannot reach - a `tests/` or `benches/` target, a
`build.rs`, anything under `examples/` or `samples/` - is not part of the importable surface at
all, because Cargo compiles those as separate targets against the library rather than into it.

The dependency snapshot is read here rather than taken from the façade: the vendored reader
returns a Rust crate's requirement *names* and no versions (`_parse_rust_manifest`), and a reader
installs a version, not a name (`docs/README_CONTRACT.md` §2 row 9). That is the same cut the .NET
plugin makes for a project file's package references and the Go plugin for `require` directives.

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper module.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.rust_examples import (
    verify_rust_examples,
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

RUST = EcosystemSpec(
    ecosystem="rust",
    language="Rust",
    fence="rust",
    registry="crates.io",
    install_fact_id="install_command:cargo",
    version_badge=(
        "[![crates.io](https://img.shields.io/crates/v/{package}.svg)]"
        "(https://crates.io/crates/{package})"
    ),
    # Rust's verify line takes no module: after `cargo add`, what a reader runs to prove the
    # dependency resolves and type-checks is `cargo check`, and `str.format` leaves a template
    # with no placeholder exactly as written.
    verify_command="cargo check",
    # The source-checkout path (§28.12 G4-W17 arrival item 0, PROPOSAL P5 in RESEARCH_LANE_D.md).
    # A crate no registry lists is still usable from a clone, and these are the three commands the
    # repository's own README names for it. Cargo cannot install a library into a consumer's
    # project from the command line without knowing that project - the dependency is a `git` or
    # `path` entry in the consumer's own `Cargo.toml` - so a build is the honest claim here, the
    # same cut the .NET spec makes. Measured 2026-09-06 against
    # `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at `1a6004af`: `cargo build` exits 0 in 39
    # seconds with cargo 1.98.1.
    source_install="git clone https://github.com/{repository}.git\ncd {name}\ncargo build",
    source_install_lead="build the clone with cargo build",
    # Rust names an import `use <crate>::…`, never `import` or `from`, so the renderer's default
    # (Python's own shape) matched no Rust fence and no Rust candidate ever rendered a
    # Verify-the-install block. G4-W17 arrival items 5 and 11 landed the mechanism - the pattern
    # is the spec's - and this is Rust's. `pub use` is a re-export and reads the same way at the
    # top of a fence; `extern crate` is the 2015-edition spelling a README may still carry. The
    # crate is imported under its library name, which is not its published name, so the module
    # the renderer substitutes is `import_path`'s value (`aspose_cells_foss_rust`), and `\b`
    # stops before the `::` that follows it.
    import_pattern=r"(?m)^\s*(?:pub\s+)?(?:use|extern\s+crate)\s+{module}\b",
    # A cold `cargo check` of this crate resolves seven requirements and compiles two native
    # build scripts: 253 seconds measured 2026-09-06. The ceiling in core.execution is 300.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"rust", "rs"}),
    # The floor a Cargo manifest always declares. `rust-version` is optional and is emitted
    # beside this one when a crate has it; pointing the renderer at the optional key would have
    # left Aspose.Cells for Rust telling a reader nothing about which compiler it needs.
    floor_fact_id="package:rust_edition",
    floor_label="Rust edition",
    floor_declaration="edition",
    manifest_globs=("Cargo.toml",),
    source_suffixes=frozenset({".rs"}),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(RUST.ecosystem, RUST)

_PARSER_LANGUAGE = "rust"
# A directory that carries a `Cargo.toml` of its own but is not the product.
_IGNORED_DIRECTORIES = frozenset({"target", ".git", "node_modules", "vendor"})
# What Cargo compiles as a target *beside* the library rather than into it, so nothing declared
# there is reachable through `use <crate>::…`. `build.rs` runs at build time and is not shipped.
_UNIMPORTABLE_DIRECTORIES = frozenset(
    {"tests", "benches", "examples", "samples", "target", "vendor"}
)
_BUILD_SCRIPT = "build.rs"


def import_path(identity: PackageIdentity) -> str:
    """The path a consumer writes after `use`, which is rarely the crate's published name.

    Cargo names a crate with hyphens and Rust cannot: `aspose-cells-foss-rust` is imported as
    `aspose_cells_foss_rust`, and a crate that declares `[lib] name` may rename it again. The
    vendored reader resolves both into `canonical_package` (§29.12).
    """
    canonical = str(identity.raw.get("canonical_package", "")).strip()
    return canonical or identity.name.replace("-", "_")


def importable(source_path: str) -> bool:
    """Whether a file the extractor read belongs to the surface a consumer can `use`.

    Cargo's own target rules, not a naming convention: a file under `tests/`, `benches/`,
    `examples/` or the crate's samples directory is compiled as its own target *against* the
    library, and `build.rs` runs at build time. None of them is reachable from a dependent crate.
    """
    parts = source_path.split("/")
    if parts[-1] == _BUILD_SCRIPT:
        return False
    return not any(
        part in _UNIMPORTABLE_DIRECTORIES or part.startswith((".",)) for part in parts[:-1]
    )


def _table(manifest: Path, name: str) -> dict[str, Any]:
    """One table of `Cargo.toml`, or an empty one when the file will not parse."""
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8", errors="replace"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    table = data.get(name)
    return table if isinstance(table, dict) else {}


def requirements(manifest: Path) -> Iterator[tuple[str, str, str]]:
    """Every declared requirement of the crate: name, version requirement, and which bucket.

    Cargo writes a requirement two ways - `zip = "0.6"` and `zip = { version = "0.6" }` - and a
    requirement with no version at all (a `path` or `git` source) is reported as the source it
    names rather than as a version it does not have.
    """
    for table, bucket in (
        ("dependencies", ""),
        ("dev-dependencies", "development"),
        ("build-dependencies", "development"),
    ):
        for name, declared in _table(manifest, table).items():
            if isinstance(declared, str):
                yield (name, declared, bucket)
                continue
            if not isinstance(declared, dict):
                continue
            version = str(declared.get("version", "")).strip()
            if not version:
                source = next(
                    (key for key in ("path", "git", "workspace") if key in declared), "unversioned"
                )
                version = f"({source})"
            optional = bool(declared.get("optional", False))
            yield (name, version, "optional" if optional and not bucket else bucket)


def _dependency_facts(manifest: Path, where: str) -> list[Fact]:
    """The dependency snapshot from the manifest's own requirement tables.

    `docs/README_CONTRACT.md` §2 row 9 wants every required requirement, or the verified-zero
    marker citing the clause that proves it. Optional and development requirements take the ID
    prefixes the renderer's own buckets read (`composition/renderer.py::_dependencies`).
    """
    facts: list[Fact] = []
    required = 0
    for name, version, bucket in requirements(manifest):
        required += 0 if bucket else 1
        detail = {
            "": "requirement declared in the manifest's `[dependencies]` table",
            "optional": "optional requirement, enabled by a Cargo feature (`optional = true`)",
            "development": "requirement of the crate's own tests and build scripts, "
            "not of a consumer",
        }[bucket]
        facts.append(
            Fact(
                fact_id("dependency", f"{bucket}.{name}" if bucket else name),
                "dependency",
                f"{name} {version}".strip(),
                (Evidence(where, detail),),
            )
        )
    if not required:
        facts.append(
            Fact(
                fact_id("dependency", "none"),
                "dependency",
                "none",
                (
                    Evidence(
                        where, "the manifest declares no `[dependencies]` table a consumer installs"
                    ),
                ),
            )
        )
    return facts


class RustPlugin:
    """What the facts stage asks of Rust."""

    ecosystem = RUST.ecosystem
    manifest_globs = RUST.manifest_globs
    source_suffixes = RUST.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `Cargo.toml` that declares the published crate.

        A repository may carry more than one: a workspace member, a fuzz target, a copy under
        `target/`. The published crate is the outermost manifest that is not inside a directory
        Cargo itself generates, so the ranking is depth first and then path.
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(
                part in _IGNORED_DIRECTORIES or part.startswith((".",))
                for part in path.relative_to(root).parts[:-1]
            )
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda path: (len(path.relative_to(root).parts), str(path)))

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Crate name and version, import path, the declared floor, and the install command."""
        identity = read_identity(root, self.ecosystem, manifest)
        where = manifest.relative_to(root).as_posix()
        facts: list[Fact] = []
        if identity.name:
            facts.append(
                Fact(
                    fact_id("package", "name"),
                    "package",
                    identity.name,
                    (Evidence(where, "crate name declared by the manifest's `[package]` table"),),
                )
            )
            facts.append(
                Fact(
                    fact_id("install_command", "cargo"),
                    "install_command",
                    f"cargo add {identity.name}",
                    (Evidence(where, "install command for the crate name the manifest declares"),),
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
                            "import path of the crate's library target"
                            + (
                                ", which Rust spells with underscores rather than hyphens"
                                if path != identity.name
                                else ""
                            ),
                        ),
                    ),
                )
            )
        if identity.version:
            facts.append(
                Fact(
                    fact_id("package", "version"),
                    "package",
                    identity.version,
                    (Evidence(where, "crate version declared by the manifest"),),
                )
            )
        edition = str(identity.raw.get("edition", "")).strip()
        if edition:
            facts.append(
                Fact(
                    fact_id("package", "rust_edition"),
                    "package",
                    edition,
                    (Evidence(where, "Rust edition the manifest declares for the crate"),),
                )
            )
        floor = str(identity.raw.get("rust_version", "")).strip()
        if floor:
            facts.append(
                Fact(
                    fact_id("package", "rust_version"),
                    "package",
                    floor,
                    (Evidence(where, "minimum compiler version the manifest declares"),),
                )
            )
        facts.extend(_dependency_facts(manifest, where))
        return facts

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """Public items of the crate's library, read by the shared extractor.

        The façade decides what is public - `pub` reachable from the crate root, re-exports
        included - and what each node type is called; this plugin only drops what Cargo compiles
        as a separate target, which was never part of the importable surface.

        The root the extractor reads from is the crate's *source* directory, which the vendored
        reader resolves (§29.12), not the directory the manifest sits in. The engine derives a
        symbol's module path from its location relative to that root, so passing the manifest's
        own directory prefixed every name with `src` - `src::widget::Widget`, a path no consumer
        can write (measured 2026-09-06 against a two-module fixture).
        """
        from tree_sitter_language_pack import get_parser

        manifest = self.detect_manifest(root)
        if manifest is None:
            return []
        identity = read_identity(root, self.ecosystem, manifest)
        package_root = (
            root.joinpath(*identity.package_root.split("/"))
            if (identity.package_root)
            else manifest.parent
        )
        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, package_root, root, self.ecosystem
        )
        facts: list[Fact] = []
        for symbol in symbols:
            if not importable(symbol.source_path):
                continue
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
                            f"line {symbol.line}; {symbol.symbol_kind}; "
                            "public in the crate's own library target",
                        ),
                    ),
                    attributes=attributes,
                )
            )
        return facts

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against crates.io; the fact keeps its ID."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(RUST.install_fact_id)
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
                Evidence(
                    reading.evidence_url or reading.registry or RUST.registry, reading.summary
                ),
            ),
            polarity=polarity,
            confidence=confidence,
        )
        probe = ProbeRecord(
            kind="registry",
            target=f"{reading.registry or RUST.registry}:{name.value}",
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
        """Type-check each candidate against the crate's own sources in a disposable profile.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        if manifest is None:
            return verify_rust_examples(
                root, "", "", candidates, workspace, RUST.example_timeout_seconds
            )
        identity = read_identity(root, self.ecosystem, manifest)
        return verify_rust_examples(
            manifest.parent,
            identity.name,
            import_path(identity),
            candidates,
            workspace,
            RUST.example_timeout_seconds,
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = RustPlugin()
