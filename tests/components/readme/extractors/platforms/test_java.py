"""The Java plugin supplies what is Java's own and leaves the rest to the shared façades."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms import java, java_examples
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact, slug

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>org.aspose</groupId>
    <artifactId>aspose-widget</artifactId>
    <version>26.5.0</version>
    <packaging>jar</packaging>
    <properties>
        <maven.compiler.target>21</maven.compiler.target>
        <junit.version>5.10.0</junit.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${junit.version}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""
WIDGET = """package org.aspose.widget;

/** A widget. */
public class Widget {
    public String getName() { return "widget"; }
    public void save(String path) { }
}
"""
INTERNAL = """package org.aspose.widget.internal;

public class Buffer {
    public void flush() { }
}
"""


def _repository(root: Path, pom: str = POM) -> list[str]:
    (root / "pom.xml").write_text(pom, encoding="utf-8", newline="\n")
    source = root / "src" / "main" / "java" / "org" / "aspose" / "widget"
    (source / "internal").mkdir(parents=True)
    (source / "Widget.java").write_text(WIDGET, encoding="utf-8", newline="\n")
    (source / "internal" / "Buffer.java").write_text(INTERNAL, encoding="utf-8", newline="\n")
    tests = root / "src" / "test" / "java" / "org" / "aspose" / "widget"
    tests.mkdir(parents=True)
    (tests / "WidgetTest.java").write_text(
        WIDGET.replace("class Widget", "class WidgetTest"), encoding="utf-8", newline="\n"
    )
    return [
        "pom.xml",
        "src/main/java/org/aspose/widget/Widget.java",
        "src/main/java/org/aspose/widget/internal/Buffer.java",
        "src/test/java/org/aspose/widget/WidgetTest.java",
    ]


def test_the_plugin_and_its_spec_are_registered_by_the_module_alone() -> None:
    """Section 29.6 E3: adding an ecosystem is a spec, a verifier and a negative control."""
    assert plugin_for("java") is java.PLUGIN
    assert "java" in known_ecosystems()
    assert spec_for("java") is java.JAVA
    assert java.JAVA.example_fences == frozenset({"java"})
    assert java.JAVA.registry == "Maven Central"


def test_the_governing_pom_is_the_module_that_packages_the_artifact(tmp_path: Path) -> None:
    """An aggregator publishes nothing and sits where depth always prefers it."""
    (tmp_path / "pom.xml").write_text(
        POM.replace("<packaging>jar</packaging>", "<packaging>pom</packaging>"),
        encoding="utf-8",
        newline="\n",
    )
    module = tmp_path / "library"
    module.mkdir()
    _repository(module)
    sample = tmp_path / "samples"
    sample.mkdir()
    _repository(sample)

    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "library/pom.xml"


def test_build_output_never_governs_and_a_broken_pom_still_ranks(tmp_path: Path) -> None:
    """`target/` holds a copy of the POM at every build; a malformed POM claims nothing."""
    _repository(tmp_path)
    copied = tmp_path / "target" / "classes"
    copied.mkdir(parents=True)
    (copied / "pom.xml").write_text(POM, encoding="utf-8", newline="\n")
    assert java.PLUGIN.detect_manifest(tmp_path) == tmp_path / "pom.xml"

    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "pom.xml").write_text("<project", encoding="utf-8", newline="\n")
    assert java._read_pom(broken / "pom.xml") is None
    assert java.PLUGIN.detect_manifest(broken) == broken / "pom.xml"


def test_manifest_facts_carry_the_coordinate_version_floor_and_install_command(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, tree)}

    assert facts["package:name"].value == "org.aspose:aspose-widget"
    assert facts["package:version"].value == "26.5.0"
    floor = facts["package:java_release"]
    assert floor.value == "21"
    # The spec names the property family; the fact's evidence names the property that was read,
    # because a POM may state the floor as release, target or source and this cohort uses all.
    assert floor.evidence[0].detail == "`maven.compiler.target` declared by the POM"
    assert spec_for("java").floor_declaration == "maven.compiler"
    install = facts["install_command:maven"]
    assert install.value == "mvn dependency:get -Dartifact=org.aspose:aspose-widget:26.5.0"
    # Unresolved until a registry says otherwise: a declared coordinate is not a published jar.
    assert install.polarity == "UNRESOLVED" and install.confidence == 0.5


def test_the_floor_prefers_release_over_target_and_source(tmp_path: Path) -> None:
    """`release` also restricts the JDK API the code may call, so it outranks the other two.

    Measured 2026-09-06: Slides declares `maven.compiler.release`, 3D and Cells declare
    `maven.compiler.target`, PDF declares both `target` and `source`.
    """
    _repository(
        tmp_path,
        POM.replace(
            "<maven.compiler.target>21</maven.compiler.target>",
            "<maven.compiler.release>17</maven.compiler.release>\n"
            "        <maven.compiler.target>21</maven.compiler.target>",
        ),
    )
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    floor = facts["package:java_release"]
    assert floor.value == "17"
    assert floor.evidence[0].detail == "`maven.compiler.release` declared by the POM"


def test_a_test_scoped_dependency_is_development_and_leaves_a_verified_zero(
    tmp_path: Path,
) -> None:
    """Contract §2 row 9. Every declared dependency of this cohort is `test` scope.

    Measured 2026-09-06: 3D declares JUnit, Cells JUnit and Apache POI, PDF JUnit, Slides JUnit
    and four more - all `test`, so all four repositories have a verified zero of required
    dependencies rather than an unread manifest.
    """
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, tree)}

    development = facts["dependency:development.org.junit.jupiter-junit-jupiter"]
    # `${junit.version}` resolved from the POM's own `<properties>`.
    assert development.value == "org.junit.jupiter:junit-jupiter 5.10.0"
    assert "<scope>test</scope>" in (development.evidence[0].detail or "")
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert marker.evidence[0].path == "pom.xml"


def test_a_compile_scoped_dependency_is_required_and_an_optional_one_is_not(
    tmp_path: Path,
) -> None:
    """A consumer installs what Maven resolves; `<optional>` is declared but never inherited."""
    _repository(
        tmp_path,
        POM.replace(
            "    </dependencies>",
            """        <dependency>
            <groupId>org.apache.poi</groupId>
            <artifactId>poi-ooxml</artifactId>
            <version>5.3.0</version>
        </dependency>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>2.0.13</version>
            <optional>true</optional>
        </dependency>
    </dependencies>""",
        ),
    )
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in java.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    assert facts["dependency:org.apache.poi-poi-ooxml"].value == "org.apache.poi:poi-ooxml 5.3.0"
    assert facts["dependency:optional.org.slf4j-slf4j-api"].value == "org.slf4j:slf4j-api 2.0.13"
    assert "dependency:none" not in facts


def test_the_surface_is_read_from_the_main_tree_and_excludes_internal_packages(
    tmp_path: Path,
) -> None:
    """`src/test/java` is not public API, and the vendored engine drops `internal`/`impl` (§29.9).

    Measured 2026-09-06 against the four live READMEs: none names a type in such a package -
    Slides is the only repository that has one (`org.aspose.slides.foss.internal.*`) and its
    README mentions it nowhere - so parity holds with the exclusion on.
    """
    tree = _repository(tmp_path)
    assert java.PLUGIN.source_root(tmp_path) == tmp_path / "src" / "main" / "java"
    facts = java.PLUGIN.surface_facts(tmp_path, tree)
    values = {fact.value for fact in facts}
    assert "org.aspose.widget.Widget" in values
    assert "org.aspose.widget.Widget.save" in values
    assert not any(value.endswith("WidgetTest") for value in values)
    assert not any(".internal." in value for value in values)
    for fact in facts:
        assert slug(fact.value), fact.value
        assert fact.evidence[0].detail and "line " in fact.evidence[0].detail


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = java.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repository_presenter.components.readme.extractors.surface.registry import (
            RegistryObservation,
        )

        return RegistryObservation("maven", "org.aspose:aspose-widget", False, True, None, None, "")

    monkeypatch.setattr(java, "observe", unreadable)
    resolved, probes = java.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    # Not the façade's "answered ambiguously": the shared probe takes a name, and Maven Central's
    # metadata is addressed by group and artifact id, so no read happened at all.
    assert "was not read" in (resolved[0].evidence[-1].detail or "")
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_statement_snippet_is_wrapped_and_a_declared_type_keeps_its_file_name() -> None:
    """javac names a public type's file after it; a run of statements needs a `main` around it."""
    name, source, supplied = java_examples.compilation_unit(
        'import org.aspose.widget.Widget;\nWidget w = new Widget();\nw.save("out.txt");\n',
        ("java.io",),
        {"Widget": "org.aspose.widget.Widget"},
    )
    assert name == "Example.java"
    # The snippet's own import is kept and wins: a single-type import takes precedence over any
    # on-demand one, and `Widget` is already imported, so nothing is added for it.
    assert source.startswith("import org.aspose.widget.Widget;\nimport java.io.*;\n")
    assert supplied == ["import java.io.*;"]
    assert "public static void main(String[] args) throws Exception" in source
    assert 'w.save("out.txt");' in source

    name, source, _ = java_examples.compilation_unit(
        "package demo;\nimport org.aspose.widget.Widget;\n\npublic class Demo {\n"
        "    public static void main(String[] a) { new Widget(); }\n}\n"
    )
    assert name == "Demo.java"
    # The package declaration is dropped: a unit compiled outside its declared directory is a
    # javac complaint about the layout, never about the example.
    assert "package demo;" not in source
    assert source.count("public class Demo") == 1


def test_a_snippet_is_given_the_product_types_it_names_and_nothing_else(tmp_path: Path) -> None:
    """Java has no implicit usings; the .NET wrapper enables C#'s, so this is the same
    accommodation, made explicit and recorded.

    Measured 2026-09-06 on Aspose.3D for Java, where five of ten README examples name `Scene`,
    `File` and `FileInputStream` with no import line at all, and on Aspose.Slides for Java, where
    seven of eight name `Color` and `SaveFormat` - types in `…foss.drawing` and `…foss.export`
    while the snippet reaches only `…foss`. Resolving by name rather than by wildcard is what
    makes the second case work without the ambiguity eighty wildcards would cause on Aspose.PDF.
    """
    _repository(tmp_path)
    source_root = tmp_path / "src" / "main" / "java"
    assert java_examples.root_package(source_root) == "org.aspose.widget"
    # The index is file names and directories, and `internal` is still part of the tree here -
    # what the surface excludes and what the compiler can see are different questions.
    assert java_examples.public_types(source_root) == {
        "Widget": "org.aspose.widget.Widget",
        "Buffer": "org.aspose.widget.internal.Buffer",
    }

    name, source, supplied = java_examples.compilation_unit(
        "Widget w = new Widget();\nList<String> names = new ArrayList<>();\n",
        ("java.io", "java.util"),
        {"Widget": "org.aspose.widget.Widget", "List": "org.aspose.widget.List"},
    )
    assert name == "Example.java"
    # `List` stays java.util's: a name the supplied on-demand imports already provide is never
    # redirected to a product type, however unambiguous that type is.
    assert supplied == [
        "import java.io.*;",
        "import java.util.*;",
        "import org.aspose.widget.Widget;",
    ]
    assert "org.aspose.widget.List" not in source


def test_a_simple_name_two_packages_declare_is_dropped_rather_than_guessed(tmp_path: Path) -> None:
    """An on-demand import of both would be a javac ambiguity error; picking one is an invention."""
    source_root = tmp_path / "src" / "main" / "java"
    for package in ("a", "b"):
        (source_root / package).mkdir(parents=True)
        (source_root / package / "Shape.java").write_text("", encoding="utf-8", newline="\n")
    (source_root / "a" / "Scene.java").write_text("", encoding="utf-8", newline="\n")
    assert java_examples.public_types(source_root) == {"Scene": "a.Scene"}


def test_a_missing_verifier_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """Section 29.6 E5: a check this plugin cannot run is UNRESOLVED, never CONTRADICTED."""
    from repository_presenter.core.examples import ExampleCandidate

    candidates = [ExampleCandidate(1, "java", "new Widget();", "README.md", 1, 3, "unit:001")]
    # No source tree at all: nothing to compile against, and no compile failure invented for it.
    receipts = java.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]


def test_a_required_dependency_blocks_the_compiler_rather_than_failing_the_example(
    tmp_path: Path,
) -> None:
    """javac resolves no artifacts, so a missing jar would look like the example's defect."""
    from repository_presenter.core.examples import ExampleCandidate

    _repository(tmp_path)
    candidates = [ExampleCandidate(1, "java", "new Widget();", "README.md", 1, 3, "unit:001")]
    receipts = java_examples.verify_java_examples(
        java.PLUGIN.source_root(tmp_path),
        "21",
        False,
        ["org.apache.poi:poi-ooxml"],
        candidates,
        tmp_path / "run",
        300.0,
    )
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert "BLOCKED_TOOLCHAIN" in receipts[0].detail
    assert "poi-ooxml" in receipts[0].detail


def test_the_floor_becomes_the_javac_flags_the_pom_itself_implies() -> None:
    """`maven.compiler.release` is `--release`; `target`/`source` are `-source`/`-target`.

    Measured 2026-09-06 on Aspose.PDF for Java, whose POM declares `target`/`source` 11 while its
    sources call APIs `--release 11` refuses: every one of its nine examples failed inside the
    product's own `Interpreter.java` until the flags matched what Maven actually does.
    """
    assert java_examples._release_flags("21", True) == ["--release", "21"]
    assert java_examples._release_flags("11", False) == ["-source", "11", "-target", "11"]
    # A floor the POM states as a range or a word is no javac flag at all, not a guess.
    assert java_examples._release_flags("1.8.0_402", True) == []


def test_the_plugin_imports_no_sibling_ecosystem() -> None:
    """Layout section 2.1: core, the shared façades, and its own file - nothing else."""
    import ast

    source = Path(java.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    siblings = [name.rsplit(".", 1)[-1] for name in imported if ".platforms." in name]
    assert siblings and all(name.startswith("java") for name in siblings), siblings
    assert all(
        name.startswith(
            (
                "repository_presenter.core",
                "repository_presenter.components.readme.extractors.surface",
                "collections",
                "pathlib",
                "typing",
                "__future__",
                "tree_sitter_language_pack",
                # A POM is XML, and reading what it declares about itself is Java's own
                # knowledge; the standard library parser keeps it out of shared code.
                "xml.etree",
                "repository_presenter.components.readme.extractors.platforms.java",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = java.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *java.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *java.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)
