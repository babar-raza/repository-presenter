"""The Java platform plugin: identity from the POM, surface from the shared extractor.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3 and §29.12. Nothing here parses Java or reads a registry
itself: the `SurfaceExtractor`, `ManifestReader` and `RegistryProbe` façades do that for every
ecosystem, and this module supplies only what is Java's own — which POM governs a project, what a
Maven coordinate looks like, which `maven.compiler` property states the floor, and how a snippet
becomes something `javac` can compile.

Per `docs/REPOSITORY_LAYOUT.md` §2.1 this module imports `core/`, the shared façades under
`extractors/`, and its own helper file.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final
from xml.etree import ElementTree

from repository_presenter.components.readme.extractors.platforms.java_examples import (
    verify_java_examples,
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

JAVA: Final = EcosystemSpec(
    ecosystem="java",
    language="Java",
    fence="java",
    registry="Maven Central",
    install_fact_id="install_command:maven",
    # Still no version badge, but for a different reason than before: G4-W17 item 13 gave
    # `badge()` the `{group}`/`{artifact}` pair the shields.io *image* URL needs
    # (`img.shields.io/maven-central/v/org.aspose/aspose-3d-foss.svg`, live 200), so half the
    # gap PROPOSAL B named is closed. What is left is the badge's *landing* URL: the upstream
    # READMEs point it at `repo1.maven.org/maven2/<group as a path>/<artifact>/`, and no token
    # `badge()` offers renders a dotted group as a path, while the one-token alternative
    # (`central.sonatype.com/artifact/{group}/{artifact}`, also live 200) is neither a
    # `link_target` fact nor a `_RENDERER_HOSTS` entry, so BC-06 rejects it as an unverified
    # target. Measured 2026-09-06; PROPOSAL I in docs/RESEARCH_LANE_C.md.
    version_badge="",
    # A javac run compiles the product sources the snippet reaches, not just the snippet, so it
    # pays for the library's own compilation once per example; the ceiling in core.execution
    # bounds it.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"java"}),
    floor_fact_id="package:java_release",
    floor_label="Java",
    # The property family, not one property: a POM may state the floor as
    # `maven.compiler.release`, `.target` or `.source`, and all three occur across this cohort
    # (Slides declares `release`, 3D and Cells `target`, PDF `target`). The fact's own evidence
    # names the exact property that was read.
    floor_declaration="maven.compiler",
    manifest_globs=("pom.xml",),
    source_suffixes=frozenset({".java"}),
)
# §29.6 E3 and `core/ecosystems.py`'s own rule: adding an ecosystem is a spec, a verifier and a
# negative control, never an edit to a shared file - so the spec is declared beside the plugin
# that owns it and registered on import, which is the same import the facts stage already makes
# through `plugin_for`.
SPECS.setdefault(JAVA.ecosystem, JAVA)

_PARSER_LANGUAGE = "java"
# Build output and version control carry copies of a POM; a directory whose name says it is a
# sample, a test or a benchmark carries a project that is not the product.
_IGNORED_DIRECTORIES = frozenset({"target", "build", "out", ".git", ".mvn", "node_modules"})
_NOT_THE_PRODUCT = frozenset(
    {"samples", "sample", "examples", "example", "demo", "demos", "tests", "test", "benchmarks"}
)
# The Maven scopes whose dependencies a consumer of the published artifact never installs.
_DEVELOPMENT_SCOPES = frozenset({"test", "provided", "system"})
# In priority order, exactly as the vendored reader reads them: `release` also restricts the JDK
# API the code may call, so it outranks the pair that only sets the bytecode level.
_FLOOR_PROPERTIES = ("maven.compiler.release", "maven.compiler.target", "maven.compiler.source")
_PROPERTY = re.compile(r"\$\{([^}]+)\}")
_SOURCE_DIRECTORY = "src/main/java"


def _tag(element: ElementTree.Element) -> str:
    """The element's local name: a POM carries the Maven namespace on every tag."""
    return element.tag.rsplit("}", 1)[-1]


def _child(element: ElementTree.Element, name: str) -> str:
    for child in element:
        if _tag(child) == name:
            return (child.text or "").strip()
    return ""


def _section(root: ElementTree.Element, name: str) -> ElementTree.Element | None:
    for child in root:
        if _tag(child) == name:
            return child
    return None


def _read_pom(manifest: Path) -> ElementTree.Element | None:
    """The POM's root element, or None when it will not parse.

    A file that will not parse declares nothing, which leaves the remaining ranking keys to order
    it and the dependency snapshot with no requirement to report.
    """
    try:
        return ElementTree.parse(manifest).getroot()
    except (OSError, ElementTree.ParseError):
        return None


def _properties(root: ElementTree.Element) -> dict[str, str]:
    """The POM's own `<properties>`, plus the two `project.*` references Maven predefines."""
    values: dict[str, str] = {}
    section = _section(root, "properties")
    if section is not None:
        for child in section:
            values[_tag(child)] = (child.text or "").strip()
    for name, key in (("project.version", "version"), ("project.groupId", "groupId")):
        declared = _child(root, key)
        if declared:
            values[name] = declared
    return values


def _resolve(value: str, properties: dict[str, str]) -> str:
    """`${junit.version}` as the POM declares it; an unknown reference is left as written.

    Leaving it is the honest outcome: a dependency whose version this reader cannot resolve is
    still a dependency, and printing the placeholder says plainly that the POM defers it.
    """
    return _PROPERTY.sub(lambda match: properties.get(match.group(1), match.group(0)), value)


def _floor_property(root: ElementTree.Element) -> str:
    """Which `maven.compiler` property states the floor, in the reader's own priority order."""
    properties = _properties(root)
    for name in _FLOOR_PROPERTIES:
        if properties.get(name):
            return name
    return ""


def _dependencies(root: ElementTree.Element) -> list[tuple[str, str, str, bool]]:
    """The project's own direct dependencies: coordinate, version, scope, and whether optional.

    `<dependencyManagement>` states versions for dependencies a POM may never declare, and a
    plugin's dependencies are the build's, not the artifact's - so only the project's own
    `<dependencies>` block is read.
    """
    section = _section(root, "dependencies")
    if section is None:
        return []
    properties = _properties(root)
    found: list[tuple[str, str, str, bool]] = []
    for entry in section:
        if _tag(entry) != "dependency":
            continue
        group = _resolve(_child(entry, "groupId"), properties)
        artifact = _resolve(_child(entry, "artifactId"), properties)
        if not artifact:
            continue
        found.append(
            (
                f"{group}:{artifact}" if group else artifact,
                _resolve(_child(entry, "version"), properties),
                _child(entry, "scope").lower() or "compile",
                _child(entry, "optional").lower() == "true",
            )
        )
    return found


def _dependency_facts(root: ElementTree.Element | None, where: str) -> list[Fact]:
    """The dependency snapshot from the POM's own `<dependencies>` block.

    `docs/README_CONTRACT.md` §2 row 9 wants every required requirement, or the verified-zero
    marker citing the clause that proves it. Maven's scope says which bucket a dependency belongs
    in: `test`, `provided` and `system` are never resolved for a consumer of the published jar,
    so they are development dependencies; `<optional>true</optional>` is declared but not
    inherited, which is the optional bucket. Measured 2026-09-06 across the Java cohort: 3D
    declares JUnit alone, Cells JUnit and Apache POI, PDF JUnit, Slides JUnit and four more -
    every one of them `test`, so all four repositories have a verified zero of required
    dependencies, not a gap.
    """
    facts: list[Fact] = []
    for coordinate, version, scope, optional in _dependencies(root) if root is not None else []:
        development = scope in _DEVELOPMENT_SCOPES
        value = f"{coordinate} {version}".strip()
        if development:
            detail = f"declared with `<scope>{scope}</scope>`, never resolved for a consumer"
            identifier = fact_id("dependency", "development", coordinate)
        elif optional:
            detail = "declared with `<optional>true</optional>`, so it is not inherited"
            identifier = fact_id("dependency", "optional", coordinate)
        else:
            detail = f"dependency declared by the POM with `<scope>{scope}</scope>`"
            identifier = fact_id("dependency", coordinate)
        facts.append(Fact(identifier, "dependency", value, (Evidence(where, detail),)))
    if not any(
        not fact.id.startswith(("dependency:development.", "dependency:optional."))
        for fact in facts
    ):
        facts.append(
            Fact(
                fact_id("dependency", "none"),
                "dependency",
                "none",
                (
                    Evidence(
                        where,
                        "every `<dependency>` the POM declares is `test`, `provided` or optional",
                    ),
                ),
            )
        )
    return facts


def _coordinate(identity: PackageIdentity) -> str:
    """`groupId:artifactId`, the name a Java reader writes into a POM or a build file."""
    group = str(identity.raw.get("group_id") or "").strip()
    artifact = str(identity.raw.get("artifact_id") or "").strip() or identity.name
    if not artifact:
        return ""
    return f"{group}:{artifact}" if group else artifact


_INLINE_TAG_OPEN = re.compile(r"\{@(\w+)\s*")
# Only the tags that are presentation and nothing else are removed with their text position.
# Everything else in angle brackets keeps its word: Aspose.PDF's Javadoc describes XFA, whose
# element names (`<xfa:datasets>`, `<pageSet>`, `<caption>`, `<value>`) are the subject of the
# sentence, and deleting them would leave "The packet wrapper." saying nothing.
_FORMATTING = (
    "a|b|i|u|s|em|strong|code|tt|pre|p|br|hr|span|div|font|center|small|big|sup|sub"
    "|ul|ol|li|dl|dt|dd|table|thead|tbody|tfoot|tr|td|th|blockquote|cite|var|kbd|samp"
    "|h1|h2|h3|h4|h5|h6"
)
_HTML_TAG = re.compile(rf"</(?:[A-Za-z][^<>]*)>|<(?:{_FORMATTING})\b[^<>]*>", re.IGNORECASE)
_ANGLED = re.compile(r"<([^<>]+)>")
_ENTITIES = (
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&apos;", "'"),
    ("&nbsp;", " "),
    ("&#39;", "'"),
    ("&amp;", "&"),
)


def _javadoc_prose(doc: str) -> str:
    """A Javadoc comment as the plain prose the API Reference table renders.

    Javadoc is not Markdown, and the renderer's table cell is prose: `_symbol_description`
    strips backticks outright (a docstring is the source's spelling, not the document's), so a
    code span cannot be the escape hatch here and the markup has to go rather than be requoted.
    Measured 2026-09-06 on Aspose.PDF for Java: 104 `{@code ...}`/`{@link ...}` tags reached the
    rendered table verbatim ("Represents a collection of {@link Artifact} objects"), along with
    raw HTML ("the text <b>and images</b>") and `&quot;` entities - and one docstring,
    `Datasets`'s `The {@code <xfa:datasets>} packet wrapper.`, put bare angle brackets around a
    colon-qualified name, which CommonMark reads as an autolink: BC-06 then failed the whole
    candidate at EXTRACTING with `xfa:datasets: tree does not contain datasets`, at a stage no
    repair can act on. Six of PDF's docstrings carry `<xfa:data>` and a dozen more carry other
    `<element>` names, so which symbol the plan happens to pick decides whether the transaction
    survives - the brackets are dropped for every one of them, not just the one that broke.
    """
    text = doc
    for entity, character in _ENTITIES:
        text = text.replace(entity, character)
    # `{@code X}`, `{@literal X}` and `{@value X}` are their own argument; `{@link ref label}`
    # and `{@linkplain ref label}` read as the label when they carry one, else the reference
    # with Javadoc's `#` member separator written the way a caller writes it; `{@inheritDoc}`
    # and `{@docRoot}` carry no text at all. An unknown tag keeps its argument and loses only
    # the braces, which is the conservative reading for a tag this cohort has not met.
    text = _resolve_inline_tags(text)
    text = _HTML_TAG.sub(" ", text)
    text = _ANGLED.sub(r"\1", text)
    # A removed tag leaves the space it stood in, which reads as "docs ." before punctuation.
    return re.sub(r"\s+([.,;:)\]])", r"\1", " ".join(text.split()))


def _resolve_inline_tags(text: str) -> str:
    """Replace every `{@tag ...}` with its own text, innermost brace counted.

    A regex over `[^{}]*` cannot do this: Aspose.PDF's Javascript-AST types document themselves
    with `{@code { k: v, ... }}` and `{@code try { } catch (p) { } finally { }}`, whose argument
    is braces all the way down, and the vendored engine hands over the docstring's *first line*
    only - so six of them arrive already cut mid-tag (`{@code {...`). A scan closes what it can
    and treats an unterminated tag as running to the end of the line, which is the only reading
    left once the closing brace is on a line the extractor did not keep.
    """
    out: list[str] = []
    index = 0
    while (match := _INLINE_TAG_OPEN.search(text, index)) is not None:
        out.append(text[index : match.start()])
        depth, cursor = 1, match.end()
        while cursor < len(text) and depth:
            depth += (text[cursor] == "{") - (text[cursor] == "}")
            cursor += 1
        argument = text[match.end() : cursor - 1 if depth == 0 else len(text)]
        out.append(_inline_tag_text(match.group(1), argument))
        index = cursor
    out.append(text[index:])
    return "".join(out)


def _inline_tag_text(tag: str, raw: str) -> str:
    argument = _resolve_inline_tags(raw).strip()
    if tag in {"inheritDoc", "docRoot"}:
        return ""
    if tag in {"link", "linkplain"}:
        reference, _, label = argument.partition(" ")
        return label.strip() or reference.lstrip("#").replace("#", ".")
    return argument


class JavaPlugin:
    """What the facts stage asks of Java."""

    ecosystem = JAVA.ecosystem
    manifest_globs = JAVA.manifest_globs
    source_suffixes = JAVA.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The POM that governs the artifact.

        Depth alone is not enough. A multi-module build puts an aggregator POM
        (`<packaging>pom</packaging>`) at the root, where depth always prefers it, and it publishes
        nothing; a `samples/` or `tests/` module sits at the same depth as the product. Ranked
        instead by what a product POM looks like - it packages an artifact rather than aggregating
        modules, it is not under a directory whose name says it is not the product, and it has a
        Java source tree beside it - then by depth, then by path so the choice is deterministic.
        """
        candidates = [
            path
            for pattern in self.manifest_globs
            for path in root.rglob(pattern)
            if not any(part in _IGNORED_DIRECTORIES for part in path.parts)
        ]
        if not candidates:
            return None

        def rank(path: Path) -> tuple[int, int, int, int, str]:
            parts = path.relative_to(root).parts
            pom = _read_pom(path)
            aggregator = pom is not None and _child(pom, "packaging").lower() == "pom"
            aside = any(part.lower() in _NOT_THE_PRODUCT for part in parts)
            sources = (path.parent / _SOURCE_DIRECTORY).is_dir() or any(path.parent.rglob("*.java"))
            return (int(aggregator), int(aside), 0 if sources else 1, len(parts), str(path))

        return min(candidates, key=rank)

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Coordinate, version, the Java floor, the install command, and the dependency snapshot."""
        identity = read_identity(root, self.ecosystem, manifest)
        where = manifest.relative_to(root).as_posix()
        pom = _read_pom(manifest)
        coordinate = _coordinate(identity)
        facts: list[Fact] = []
        if coordinate:
            facts.append(
                Fact(
                    fact_id("package", "name"),
                    "package",
                    coordinate,
                    (Evidence(where, "`groupId` and `artifactId` declared by the POM"),),
                )
            )
            # `mvn dependency:get` is the one install form that is a command rather than a POM
            # edit, so it is what a bash fence can honestly show; it resolves the artifact from
            # Maven Central into the caller's local repository.
            artifact = f"{coordinate}:{identity.version}" if identity.version else coordinate
            facts.append(
                Fact(
                    fact_id("install_command", "maven"),
                    "install_command",
                    f"mvn dependency:get -Dartifact={artifact}",
                    # "the manifest", not "the POM": BC-02 reads the install fact's own evidence
                    # for the manifest's identity reading beside the registry's, and every other
                    # ecosystem's plugin says "manifest" (go, net, rust, typescript). Naming the
                    # file by its ecosystem nickname alone left the coordinate's own manifest
                    # reading invisible to the check - measured 2026-09-06 on all four Java
                    # repositories, which reached S9 with the registry half already SUPPORTED.
                    (
                        Evidence(
                            where,
                            "install command for the coordinate the `pom.xml` manifest declares",
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
                    (Evidence(where, "version declared by the POM"),),
                )
            )
        if identity.floor:
            declaration = _floor_property(pom) if pom is not None else ""
            facts.append(
                Fact(
                    fact_id("package", "java_release"),
                    "package",
                    identity.floor,
                    (
                        Evidence(
                            where,
                            f"`{declaration}` declared by the POM"
                            if declaration
                            else "Java release declared by the build",
                        ),
                    ),
                    # G4-W17 arrival item 14 (this lane's PROPOSAL C) landed the per-fact
                    # override the spec's ecosystem-wide `maven.compiler` family cannot express:
                    # this POM's own property, so the rendered parenthetical cites what this
                    # repository declares rather than a family three of the four do not.
                    attributes={"floor_declaration": declaration} if declaration else None,
                )
            )
        facts.extend(_dependency_facts(pom, where))
        return facts

    def source_root(self, root: Path) -> Path:
        """The Java source tree the surface is read from, never the test tree beside it.

        The vendored reader resolves `src/main/java`, `app/src/main/java` or `src`; taking the
        POM's own directory instead (which is what a manifest-first plugin does for .NET) would
        read `src/test/java` as public API.
        """
        relative = read_identity(root, self.ecosystem).package_root
        resolved = root / relative if relative else root
        return resolved if resolved.is_dir() else root

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """Public types and members, read from the main source tree by the shared extractor.

        The vendored engine excludes any package with an `internal` or `impl` segment for Java
        (§29.9). Measured 2026-09-06 against the four live READMEs: none of them names a type in
        such a package - Slides is the only repository that has one
        (`org.aspose.slides.foss.internal.*`) and its README mentions it nowhere - so parity holds
        with the exclusion on and the default stands for this cohort.
        """
        from tree_sitter_language_pack import get_parser

        symbols = surface_symbols(
            get_parser(_PARSER_LANGUAGE),
            _PARSER_LANGUAGE,
            self.source_root(root),
            root,
            self.ecosystem,
        )
        facts: list[Fact] = []
        for symbol in symbols:
            attributes: dict[str, str] = {"symbol_kind": symbol.symbol_kind}
            if symbol.signature:
                attributes["signature"] = symbol.signature
            if symbol.doc:
                # Javadoc, not Markdown, and not prose either until its tags are resolved.
                prose = _javadoc_prose(symbol.doc)
                if prose:
                    attributes["docstring"] = prose
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
        """Resolve the install claim against Maven Central; the fact keeps its ID, gains evidence.

        The shared probe reads `repo1.maven.org`'s `maven-metadata.xml`, never
        `search.maven.org` (§29.6 E3). `observe` once carried only a package *name* while that
        metadata path is built from the group and the artifact id separately, so no read ever
        happened for a Java package (docs/RESEARCH_LANE_C.md, PROPOSAL 2026-09-06 A); G4-W17
        arrival item 12 landed the split on 2026-09-06 and the reading is live - measured the
        same day, all four repositories come back SUPPORTED from
        `repo1.maven.org/maven2/org/aspose/<artifact>/maven-metadata.xml`. The inconclusive
        branch below keeps saying what did not happen rather than borrowing the façade's
        "answered ambiguously", which would claim a read that never happened.
        """
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(JAVA.install_fact_id)
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value)
        polarity: Polarity
        if not reading.conclusive:
            polarity, confidence = "UNRESOLVED", 0.5
            detail = (
                "package registry: Maven Central was not read - the shared probe takes a package "
                "name, and `maven-metadata.xml` is addressed by group and artifact id"
            )
        elif reading.published:
            polarity, confidence = "SUPPORTED", 1.0
            detail = reading.summary
        else:
            polarity, confidence = "CONTRADICTED", 1.0
            detail = reading.summary
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
        """Compile each candidate against the product's own sources in a disposable workspace.

        A toolchain this machine lacks is NOT_VERIFIED, which the facts stage records as
        UNRESOLVED - never CONTRADICTED, because "we could not check" is not "we checked and it
        is false" (§29.6 E5).
        """
        manifest = self.detect_manifest(root)
        pom = _read_pom(manifest) if manifest is not None else None
        identity = read_identity(root, self.ecosystem, manifest) if manifest is not None else None
        required = [
            coordinate
            for coordinate, _version, scope, optional in (_dependencies(pom) if pom else [])
            if scope not in _DEVELOPMENT_SCOPES and not optional
        ]
        return verify_java_examples(
            self.source_root(root),
            identity.floor if identity is not None else "",
            # `maven.compiler.release` restricts the JDK API the code may call; `target`/`source`
            # only set the language level and the bytecode version. javac spells the two
            # differently, and treating them alike fails a build Maven performs (§ PDF for Java).
            pom is not None and _floor_property(pom) == _FLOOR_PROPERTIES[0],
            required,
            candidates,
            workspace,
            JAVA.example_timeout_seconds,
        )

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not yet built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not yet built; the vendored format reader lands with the cohort that needs it."""
        return []


PLUGIN: Any = JavaPlugin()
