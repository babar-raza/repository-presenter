"""The C++ platform plugin: identity from CMake, surface from the public header tree.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. Nothing here parses C++ or reads a registry itself: the
`SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every ecosystem, and
this module supplies only what is C++'s own — which `CMakeLists.txt` governs the library, what a
consumer links, and which headers are public.

Two things separate C++ from every ecosystem before it. It has no registry: `surface/registry.py`
says so outright and no `CMakeLists.txt` names a package on one, so the install command is the
source build the verifier itself drives and its claim stays UNRESOLVED — a package registry that
does not exist was read, not assumed away. And its public surface is a directory rather than a
declaration — `include/` is what a consumer may include and `src/` is not, which is why the
surface is read from the include root alone and narrowed to the headers a consumer may reach
(Aspose.PDF ships `include/internal/`, Aspose.Slides `include/.../_internal/`).

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper module.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.cpp_examples import (
    verify_cpp_examples,
)
from repository_presenter.components.readme.extractors.surface.extractor import (
    SurfaceSymbol,
    surface_symbols,
)
from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.components.readme.extractors.surface.registry import observe
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Evidence, Fact, fact_id, slug
from repository_presenter.core.probes import ProbeRecord

CPP = EcosystemSpec(
    ecosystem="cpp",
    language="C++",
    fence="cpp",
    # C++ has no portfolio-wide package registry, which `surface/registry.py` states and
    # `REGISTRY_TYPES` encodes by having no `cpp` entry. The name is a phrase rather than a
    # registry because the only sentence the renderer builds from it is the unresolved one -
    # "could not be confirmed on any package registry at this revision" - and the install fact
    # is never SUPPORTED here, so the published-package sentence is unreachable.
    registry="any package registry",
    install_fact_id="install_command:cmake",
    version_badge="",
    # G4-W17 arrival item 24: with no registry, install_command:cmake can never become
    # CONTRADICTED - there is nothing to read as "not there" - so it starts and stays UNRESOLVED,
    # and the source-build admission (item 0) never had anything to admit for this ecosystem.
    # Measured working for all four C++ repositories in the cohort (2026-09-06).
    source_install="git clone https://github.com/{repository}.git\ncd {name}\ncmake -S . -B build",
    source_install_lead="configure the clone with cmake",
    # Nothing a consumer can run to verify an install: there is no install. The renderer only
    # reaches this template when an `import_path` fact matches an executed example's import
    # statement, and C++ writes `#include`, not `import`.
    verify_command="",
    # A configure that fetches dependencies plus a syntax-only compile; the ceiling in
    # core.execution is 300 seconds and Aspose.PDF's configure-and-build measured 95.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"cpp", "c++", "cxx", "cc"}),
    # The floor a `CMakeLists.txt` declares about a consumer is the language standard its public
    # headers require: a consumer compiling against them with an older `-std` will not build.
    floor_fact_id="package:cxx_standard",
    floor_label="C++",
    floor_declaration="CMAKE_CXX_STANDARD",
    manifest_globs=("CMakeLists.txt",),
    source_suffixes=frozenset({".h", ".hpp", ".hxx", ".cpp", ".cc", ".cxx"}),
)
# The spec layer registers by name and never grows a list of ecosystems (§29.6 E3): a plugin
# module declares its own spec when it is imported, which is what `plugin_for` does before any
# stage asks `spec_for` for the vocabulary. `setdefault` so a re-import is not a redefinition.
SPECS.setdefault(CPP.ecosystem, CPP)

_PARSER_LANGUAGE = "cpp"
# Build output, dependency caches and version control carry `CMakeLists.txt` copies of their own;
# `_deps` is where FetchContent puts someone else's project.
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        "_deps",
        "build",
        "cmake-build-debug",
        "cmake-build-release",
        "external",
        "node_modules",
        "out",
        "third_party",
        "vendor",
    }
)
# What a header directory is called when it is the public one.
_INCLUDE_DIRECTORY = "include"

_PROJECT = re.compile(
    r"project\s*\(\s*([A-Za-z0-9_.+-]+)(?:\s+VERSION\s+([0-9][0-9A-Za-z.+-]*))?", re.IGNORECASE
)
_MINIMUM = re.compile(r"cmake_minimum_required\s*\(\s*VERSION\s+([0-9][0-9.]*)", re.IGNORECASE)
# Two ways a project states the standard. `CMAKE_CXX_STANDARD` is the variable the vendored
# reader knows; `cxx_std_NN` through `target_compile_features` is the form that travels with an
# exported target, which is what Aspose.Slides uses and why its census floor is null.
_STANDARD_VARIABLE = re.compile(r"CMAKE_CXX_STANDARD\s+(\d+)", re.IGNORECASE)
_STANDARD_FEATURE = re.compile(r"cxx_std_(\d+)", re.IGNORECASE)
# `add_library(<name> ...)`, excluding the alias and interface forms, which add no build.
_ADD_LIBRARY = re.compile(
    r"add_library\s*\(\s*([A-Za-z_][A-Za-z0-9_.+:-]*)\s+(?!ALIAS\b)", re.IGNORECASE
)
_FETCH_CONTENT = re.compile(
    r"FetchContent_Declare\s*\(\s*([A-Za-z_][A-Za-z0-9_.+-]*)", re.IGNORECASE
)
_FIND_PACKAGE = re.compile(r"find_package\s*\(\s*([A-Za-z_][A-Za-z0-9_.+-]*)", re.IGNORECASE)
_LINK_LIBRARIES = re.compile(
    r"target_link_libraries\s*\(\s*([A-Za-z_][A-Za-z0-9_.+:-]*)([^)]*)\)", re.IGNORECASE | re.DOTALL
)
_PUBLIC_KEYWORDS = ("PUBLIC", "INTERFACE")
_LINK_KEYWORDS = frozenset({"PUBLIC", "PRIVATE", "INTERFACE"})
# A header directory whose name says a consumer must not include what is inside it. `internal`
# is the C++ convention the vendored engine already knows; `_internal` is the same convention
# with the leading underscore the language reserves for implementation detail, and upstream
# exempts it by name from its own private-directory rule.
_PRIVATE_SEGMENTS = frozenset({"internal", "_internal", "detail", "details", "impl"})


def _is_private(source_path: str) -> bool:
    """Whether a header sits under a directory whose name says it is not part of the surface."""
    parts = source_path.replace("\\", "/").split("/")[:-1]
    return any(part.lower() in _PRIVATE_SEGMENTS for part in parts)


def public_symbols(symbols: Sequence[SurfaceSymbol]) -> list[SurfaceSymbol]:
    """The symbols a consumer of the library can actually reach.

    C++ has no module-scope visibility keyword, so what a consumer may include is decided by
    where a header sits: `include/internal/` on Aspose.PDF and `include/Aspose/Slides/Foss/
    _internal/` on Aspose.Slides are unreachable from the public `#include` surface and reuse
    short names across unrelated files. Measured 2026-09-06: 393 of Aspose.PDF's 2044 extracted
    symbols and 401 of Aspose.Slides' 3243 come from those trees, and publishing them would put a
    library's internals in a reference the contract says is a consumer's only one (loop-prompt §6
    rule 8).

    A namespace survives when anything public is still declared inside it, and is re-evidenced at
    the first such declaration - the namespace's own evidence would otherwise cite a private
    header, and `Aspose.Slides.Foss` is introduced by one.
    """
    reachable = [
        symbol
        for symbol in symbols
        if symbol.symbol_kind != "module" and not _is_private(symbol.source_path)
    ]
    anchor: dict[str, SurfaceSymbol] = {}
    for symbol in reachable:
        parts = symbol.value.split(".")
        for depth in range(1, len(parts)):
            anchor.setdefault(".".join(parts[:depth]), symbol)
    namespaces = [
        replace(
            symbol,
            source_path=anchor[symbol.value].source_path,
            line=anchor[symbol.value].line,
        )
        for symbol in symbols
        if symbol.symbol_kind == "module" and symbol.value in anchor
    ]
    return namespaces + reachable


def source_build_command(directory: str) -> str:
    """The two commands that build the library from a checkout, as the verifier drives them."""
    source = directory or "."
    return f"cmake -S {source} -B build\ncmake --build build"


def read_cmake(manifest: Path) -> str:
    """The manifest's text, or an empty string when it will not read.

    A file that will not read declares nothing, which leaves the remaining ranking keys to order
    it and the dependency snapshot with no requirement to report.
    """
    try:
        return manifest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def library_target(text: str) -> str:
    """The name of the library this `CMakeLists.txt` builds, or an empty string."""
    match = _ADD_LIBRARY.search(text)
    return match.group(1) if match else ""


def cxx_standard(text: str) -> str:
    """The C++ standard the project declares, as its bare number, or an empty string.

    Both spellings are read, the variable first: a project that sets `CMAKE_CXX_STANDARD` and
    also requests `cxx_std_NN` on one target states the same thing twice, and the variable is
    what the vendored reader and the census already name.
    """
    for pattern in (_STANDARD_VARIABLE, _STANDARD_FEATURE):
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ""


def _link_interface(text: str, target: str) -> set[str]:
    """The names on ``target``'s PUBLIC and INTERFACE link interface, lowercased.

    What a consumer of the library must also have. A `PRIVATE` item is the library's own build
    and is reported as a development dependency instead, which is what the declaration says -
    measured 2026-09-06 on Aspose.Slides for C++, whose library links `pugixml::pugixml` PUBLIC
    and miniz PRIVATE, and on Aspose.PDF for C++, whose library declares no link libraries at all
    while its test executable links GoogleTest.
    """
    names: set[str] = set()
    for match in _LINK_LIBRARIES.finditer(text):
        if match.group(1).lower() != target.lower():
            continue
        section = ""
        for token in match.group(2).split():
            upper = token.upper()
            if upper in _LINK_KEYWORDS:
                section = upper
                continue
            if section in _PUBLIC_KEYWORDS:
                names.add(token.split("::")[0].strip("${}").lower())
    return names


def declared_dependencies(text: str) -> list[tuple[str, str]]:
    """Every dependency the manifest declares, as ``(name, how it was declared)``.

    `FetchContent_Declare` and `find_package` are the two ways a CMake project names something it
    did not write. Sorted and de-duplicated by name, because a project commonly does both - a
    `find_package(... QUIET)` first and a fetch when that finds nothing.
    """
    found: dict[str, str] = {}
    for pattern, how in ((_FIND_PACKAGE, "find_package"), (_FETCH_CONTENT, "FetchContent_Declare")):
        for match in pattern.finditer(text):
            found.setdefault(match.group(1), how)
    return sorted(found.items())


def _dependency_facts(text: str, where: str) -> list[Fact]:
    """The dependency snapshot from the manifest's own declarations.

    `docs/README_CONTRACT.md` §2 row 9 wants every required requirement, or the verified-zero
    marker citing the clause that proves it. CMake carries no version for a `find_package` that
    asks for none, so the value is the name the project writes; the split between required and
    development is the library target's own link interface, never a guess from the name.
    """
    target = library_target(text)
    public = _link_interface(text, target) if target else set()
    facts: list[Fact] = []
    required = 0
    for name, how in declared_dependencies(text):
        if name.lower() in public:
            required += 1
            facts.append(
                Fact(
                    fact_id("dependency", name),
                    "dependency",
                    name,
                    (
                        Evidence(
                            where,
                            f"declared by `{how}` and on `{target}`'s public link interface, "
                            "so a consumer links it too",
                        ),
                    ),
                )
            )
        else:
            facts.append(
                Fact(
                    fact_id("dependency", "development", name),
                    "dependency",
                    name,
                    (
                        Evidence(
                            where,
                            f"declared by `{how}`; not on the library target's public link "
                            "interface, so it belongs to this repository's own build",
                        ),
                    ),
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
                        where,
                        "no dependency is on the library target's public link interface, so a "
                        "consumer links nothing beyond the library itself",
                    ),
                ),
            )
        )
    return facts


class CppPlugin:
    """What the facts stage asks of C++."""

    ecosystem = CPP.ecosystem
    manifest_globs = CPP.manifest_globs
    source_suffixes = CPP.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `CMakeLists.txt` that governs the library.

        Depth alone is wrong here and so is a name test. Aspose.Cells for C++ has no
        `CMakeLists.txt` at the root at all and four below it: the library's, its tests', a
        sibling `Aspose.Cells.Foss.Cpp.Tests` harness and a `samples` project - and the last two
        declare a `project()` at a *shallower* depth than the library. Ranked instead by what a
        library's own manifest looks like: it declares a project, it declares a library with
        `add_library`, and it has an `include` directory beside it - then by depth, then by path
        so the choice is deterministic. A name test would not do it: the harness that fools depth
        is `Aspose.Cells.Foss.Cpp.Tests`, whose path segment is not the word "tests", while the
        library itself sits under a directory whose name contains "Cpp".
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(part in IGNORED_DIRECTORIES for part in path.parts)
        ]
        if not candidates:
            return None

        def rank(path: Path) -> tuple[int, int, int, int, str]:
            text = read_cmake(path)
            return (
                0 if _PROJECT.search(text) else 1,
                0 if library_target(text) else 1,
                0 if (path.parent / _INCLUDE_DIRECTORY).is_dir() else 1,
                len(path.relative_to(root).parts),
                str(path),
            )

        return min(candidates, key=rank)

    def include_root(self, root: Path) -> Path:
        """The directory a consumer's `#include` paths are relative to.

        `include/` beside the manifest when the project has one, else the manifest's own
        directory. Never the repository root when they differ: Aspose.Cells for C++ keeps tests,
        samples and a second harness beside the library, and reading the surface from the root
        would publish their types as the library's.
        """
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        headers = package / _INCLUDE_DIRECTORY
        return headers if headers.is_dir() else package

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the C++ standard, the CMake floor, and the target a consumer links.

        The install command is the source build, and it stays UNRESOLVED: `CMakeLists.txt` names a
        CMake project and a link target, neither of which is a package on a registry, and the
        `RegistryProbe` has no registry for C++ to ask. The command itself is the one the verifier
        drives - `cmake -S <the manifest's directory> -B build` then `cmake --build build` - so
        the Installation section carries what a reader of these repositories actually does
        (`project/portfolio-census.json` records "no registry (source build)" for all four).
        """
        identity = read_identity(root, self.ecosystem, manifest)
        text = read_cmake(manifest)
        where = manifest.relative_to(root).as_posix()
        facts: list[Fact] = []
        if identity.name:
            facts.append(
                Fact(
                    fact_id("package", "name"),
                    "package",
                    identity.name,
                    (Evidence(where, "project name declared by `project()`"),),
                )
            )
            facts.append(
                Fact(
                    fact_id("install_command", "cmake"),
                    "install_command",
                    source_build_command(manifest.parent.relative_to(root).as_posix()),
                    (
                        Evidence(
                            where,
                            "source build for the CMake project the manifest declares; C++ has "
                            "no package registry to install from",
                        ),
                    ),
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
                    (Evidence(where, "version declared by `project(... VERSION ...)`"),),
                )
            )
        standard = cxx_standard(text)
        if standard:
            facts.append(
                Fact(
                    fact_id("package", "cxx_standard"),
                    "package",
                    standard,
                    (Evidence(where, "C++ standard the project's own build requires"),),
                )
            )
        minimum = _MINIMUM.search(text)
        if minimum:
            facts.append(
                Fact(
                    fact_id("package", "cmake_minimum"),
                    "package",
                    minimum.group(1),
                    (Evidence(where, "lowest CMake version `cmake_minimum_required` accepts"),),
                )
            )
        target = library_target(text)
        if target:
            facts.append(
                Fact(
                    fact_id("import_path", target),
                    "import_path",
                    target,
                    (Evidence(where, "CMake target a consumer links against `add_library`"),),
                )
            )
        facts.extend(_dependency_facts(text, where))
        return facts

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """The public types and members declared under the library's include root.

        Read by the shared extractor, which brings the vendored engine's namespace handling, so
        `Aspose::Pdf::Document` becomes one dotted symbol rather than a split identifier
        (loop-prompt §6 rule 8), then narrowed to the headers a consumer may include.
        """
        from tree_sitter_language_pack import get_parser

        headers = self.include_root(root)
        symbols = public_symbols(
            surface_symbols(
                get_parser(_PARSER_LANGUAGE), _PARSER_LANGUAGE, headers, root, self.ecosystem
            )
        )
        facts: list[Fact] = []
        taken: dict[str, int] = {}
        for symbol in symbols:
            attributes: dict[str, str] = {"symbol_kind": symbol.symbol_kind}
            if symbol.signature:
                attributes["signature"] = symbol.signature
            if symbol.doc:
                attributes["docstring"] = symbol.doc
            key = slug(symbol.value)
            count = taken.get(key, 0) + 1
            taken[key] = count
            facts.append(
                Fact(
                    fact_id(
                        "public_symbol",
                        symbol.value if count == 1 else f"{symbol.value}-{count}",
                    ),
                    "public_symbol",
                    symbol.value,
                    (
                        Evidence(
                            symbol.source_path,
                            f"line {symbol.line}; {symbol.symbol_kind}; "
                            "declared in a public header",
                        ),
                    ),
                    attributes=attributes,
                )
            )
        return facts

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Record that there is no registry to ask, and leave the install claim UNRESOLVED.

        `surface/registry.py`'s `REGISTRY_TYPES` has no `cpp` entry, so `observe` reads nothing
        and returns an inconclusive observation without a network call - which is the honest
        answer and not a negative one (§29.6 E5). The reading still becomes evidence, because a
        reader of the install fact should see that the absence of a published package was
        observed rather than assumed.
        """
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(CPP.install_fact_id)
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value)
        resolved = Fact(
            install.id,
            install.kind,
            install.value,
            (
                *install.evidence,
                Evidence(
                    reading.evidence_url or reading.registry or "no package registry",
                    reading.summary,
                ),
            ),
            polarity="UNRESOLVED",
            confidence=0.5,
        )
        probe = ProbeRecord(
            kind="registry",
            target=f"{reading.registry or 'none'}:{name.value}",
            outcome="UNRESOLVED",
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
        """Configure and build the product, then syntax-check each candidate against its headers.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        return verify_cpp_examples(
            root,
            manifest,
            self.include_root(root),
            cxx_standard(read_cmake(manifest)) if manifest is not None else "",
            candidates,
            workspace,
            CPP.example_timeout_seconds,
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = CppPlugin()
