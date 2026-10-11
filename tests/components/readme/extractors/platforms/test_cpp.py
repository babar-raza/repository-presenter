"""The C++ plugin reads CMake for identity and publishes only what a consumer may include."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms import cpp
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Evidence, Fact

# A super-build at the root that declares a project and builds nothing: depth alone would choose
# it, exactly as it chose `Directory.Build.props` for .NET and the samples project for Cells.
SUPERBUILD = """
cmake_minimum_required(VERSION 3.16)
project(WidgetSuperBuild LANGUAGES CXX)
add_subdirectory(Widget)
"""
LIBRARY = """
cmake_minimum_required(VERSION 3.20)
project(Widget VERSION 2.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(pugixml 1.14 CONFIG QUIET)
FetchContent_Declare(googletest URL https://example.invalid/gtest.tar.gz)

add_library(widget STATIC src/widget.cpp)
target_include_directories(widget PUBLIC include)
target_link_libraries(widget PUBLIC pugixml::pugixml PRIVATE miniz)
"""
# The harness beside the library: a project, no library, and it sorts first by path.
HARNESS = """
cmake_minimum_required(VERSION 3.16)
project(AAA.Widget.Tests LANGUAGES CXX)
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../Widget" "${CMAKE_BINARY_DIR}/widget")
"""
PUBLIC_HEADER = """
#pragma once
namespace Aspose {
namespace Widget {
/** A widget a consumer can reach. */
class Shape {
public:
  void Save(const char* path);
};
}
}
"""
# Under `internal/`, which no consumer includes: the same short names recur across unrelated
# private headers, which is why publishing them would be wrong as well as noisy.
PRIVATE_HEADER = """
#pragma once
namespace Aspose {
namespace Widget {
class Buffer {
public:
  void Flush();
};
}
}
"""


def _repository(root: Path, library: str = LIBRARY) -> Path:
    (root / "CMakeLists.txt").write_text(SUPERBUILD, encoding="utf-8", newline="\n")
    harness = root / "AAA.Widget.Tests"
    harness.mkdir()
    (harness / "CMakeLists.txt").write_text(HARNESS, encoding="utf-8", newline="\n")
    package = root / "Widget"
    headers = package / "include" / "widget"
    (headers / "internal").mkdir(parents=True)
    (package / "src").mkdir()
    (package / "CMakeLists.txt").write_text(library, encoding="utf-8", newline="\n")
    (headers / "shape.h").write_text(PUBLIC_HEADER, encoding="utf-8", newline="\n")
    (headers / "internal" / "buffer.h").write_text(PRIVATE_HEADER, encoding="utf-8", newline="\n")
    (package / "src" / "widget.cpp").write_text("int rp = 1;\n", encoding="utf-8", newline="\n")
    return package / "CMakeLists.txt"


def _by_id(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.id: fact for fact in facts}


def test_the_plugin_is_discovered_by_module_name() -> None:
    assert plugin_for("cpp") is cpp.PLUGIN
    assert "cpp" in known_ecosystems()


def test_the_spec_registers_itself_when_the_plugin_module_is_imported() -> None:
    """Section 29.6 E3: adding an ecosystem is adding its files, never editing a shared list."""
    spec = spec_for("cpp")
    assert spec is cpp.CPP
    assert spec.fence == "cpp" and spec.language == "C++"
    # No registry, so no version badge can ever render and the install claim never resolves.
    assert spec.registry == "any package registry" and spec.badge("Widget") == ""
    assert {"c++", "cxx"} <= spec.example_fences


def test_the_library_manifest_wins_over_a_shallower_project_that_builds_nothing(
    tmp_path: Path,
) -> None:
    """Measured 2026-09-06 on Aspose.Cells for C++, which has four `CMakeLists.txt` and none at
    the root: a `samples` project and an `Aspose.Cells.Foss.Cpp.Tests` harness both declare a
    `project()` one directory above the library, so depth and path both choose wrongly."""
    _repository(tmp_path)
    manifest = cpp.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "Widget/CMakeLists.txt"
    assert cpp.PLUGIN.include_root(tmp_path) == tmp_path / "Widget" / "include"


def test_a_build_directory_never_governs_the_package(tmp_path: Path) -> None:
    """FetchContent puts someone else's project under `_deps`, with its own `CMakeLists.txt`."""
    _repository(tmp_path)
    fetched = tmp_path / "build" / "_deps" / "googletest-src"
    fetched.mkdir(parents=True)
    (fetched / "CMakeLists.txt").write_text(
        "project(googletest)\nadd_library(gtest STATIC a.cc)\n", encoding="utf-8", newline="\n"
    )
    manifest = cpp.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "Widget/CMakeLists.txt"


def test_the_manifest_facts_are_cmake_declarations_and_never_an_install_command(
    tmp_path: Path,
) -> None:
    manifest = _repository(tmp_path)
    facts = _by_id(cpp.PLUGIN.manifest_facts(tmp_path, manifest, []))
    assert facts["package:name"].value == "Widget"
    assert facts["package:version"].value == "2.1.0"
    assert facts["package:cxx_standard"].value == "17"
    assert facts["package:cmake_minimum"].value == "3.20"
    assert facts["import_path:widget"].value == "widget"
    # The install is the source build the verifier itself drives, and it never resolves: there is
    # no registry to confirm a published package against.
    install = facts["install_command:cmake"]
    assert install.value == "cmake -S Widget -B build\ncmake --build build"
    assert install.polarity == "UNRESOLVED"
    assert facts["package:cxx_standard"].evidence[0].path == "Widget/CMakeLists.txt"


def test_the_registry_reading_is_observed_and_never_makes_the_install_supported(
    tmp_path: Path,
) -> None:
    """A registry that does not exist is read as inconclusive, not as a negative (section 29.6
    E5), and the reading becomes evidence so the absence is observed rather than assumed."""
    manifest = _repository(tmp_path)
    resolved, probes = cpp.PLUGIN.registry_facts(cpp.PLUGIN.manifest_facts(tmp_path, manifest, []))
    assert [fact.id for fact in resolved] == ["install_command:cmake"]
    assert resolved[0].polarity == "UNRESOLVED"
    # Both words BC-02 reads an install fact's evidence for, and neither is invented.
    details = " ".join(evidence.detail or "" for evidence in resolved[0].evidence)
    assert "manifest" in details and "package registry" in details
    assert [probe.outcome for probe in probes] == ["UNRESOLVED"]
    assert probes[0].target == "none:Widget"


def test_the_standard_is_read_from_target_compile_features_too(tmp_path: Path) -> None:
    """Aspose.Slides for C++ states it as `cxx_std_20` so it travels with the exported target,
    which is why `project/portfolio-census.json` records its floor as null."""
    manifest = _repository(
        tmp_path,
        LIBRARY.replace(
            "set(CMAKE_CXX_STANDARD 17)", "target_compile_features(widget PUBLIC cxx_std_20)"
        ),
    )
    facts = _by_id(cpp.PLUGIN.manifest_facts(tmp_path, manifest, []))
    assert facts["package:cxx_standard"].value == "20"


def test_a_dependency_is_required_only_on_the_library_public_link_interface(
    tmp_path: Path,
) -> None:
    """Measured 2026-09-06: Aspose.Slides for C++ links `pugixml::pugixml` PUBLIC and miniz
    PRIVATE, and Aspose.PDF for C++ declares GoogleTest and Python3 while its library target
    links neither."""
    manifest = _repository(tmp_path)
    facts = _by_id(cpp.PLUGIN.manifest_facts(tmp_path, manifest, []))
    assert facts["dependency:pugixml"].value == "pugixml"
    assert "public link interface" in facts["dependency:pugixml"].evidence[0].detail
    assert facts["dependency:development.googletest"].value == "googletest"
    assert "dependency:none" not in facts


def test_dependency_facts_are_emitted_in_the_order_their_own_ids_sort_in(tmp_path: Path) -> None:
    """A plugin's emission order is what the renderer lists, and `facts.json` is written sorted by
    fact ID - so the two must agree or a sealed candidate cannot re-render its own bytes.

    Measured 2026-09-11 on `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`, which declares `Python3` and
    `googletest` and sealed with Python3 listed first while a re-render from its own `facts.json`
    listed googletest first (`tests/test_sealed_bytes.py`). Raw-name order puts `Python3` first
    ('P' before 'g' in ASCII); slug order puts `googletest` first, which is what the document is
    canonicalised to. This test pins slug order, so the old sort fails it.
    """
    manifest = _repository(
        tmp_path,
        LIBRARY.replace(
            "FetchContent_Declare(googletest URL https://example.invalid/gtest.tar.gz)",
            "FetchContent_Declare(googletest URL https://example.invalid/gtest.tar.gz)\n"
            "find_package(Python3 COMPONENTS Interpreter QUIET)",
        ),
    )
    emitted = [
        fact.id
        for fact in cpp.PLUGIN.manifest_facts(tmp_path, manifest, [])
        if fact.kind == "dependency"
    ]
    # The renderer partitions `dependency` facts into required, optional and development and keeps
    # document order inside each; `facts.json` is stored in global ID order. So the property that
    # makes a bundle re-render its own bytes is that every partition is already in ID order.
    for prefix in ("dependency:development.", "dependency:optional."):
        partition = [fact_id for fact_id in emitted if fact_id.startswith(prefix)]
        assert partition == sorted(partition), prefix
    required = [
        fact_id
        for fact_id in emitted
        if not fact_id.startswith(("dependency:development.", "dependency:optional."))
    ]
    assert required == sorted(required)
    assert emitted.index("dependency:development.googletest") < emitted.index(
        "dependency:development.python3"
    )


def test_a_library_that_links_nothing_publicly_reports_a_verified_zero(tmp_path: Path) -> None:
    """Contract section 2 row 9: the marker cites the clause that proves the zero."""
    manifest = _repository(
        tmp_path, LIBRARY.replace("PUBLIC pugixml::pugixml PRIVATE miniz", "PRIVATE miniz")
    )
    facts = _by_id(cpp.PLUGIN.manifest_facts(tmp_path, manifest, []))
    assert facts["dependency:none"].value == "none"
    assert "public link interface" in facts["dependency:none"].evidence[0].detail
    assert facts["dependency:development.pugixml"].value == "pugixml"


def test_a_header_under_an_internal_directory_is_not_public_surface(tmp_path: Path) -> None:
    """Measured 2026-09-06: 393 of Aspose.PDF for C++'s 2044 extracted symbols come from
    `include/internal/` and 401 of Aspose.Slides' 3243 from `include/.../_internal/`. The
    vendored engine exempts `_internal` from its own private-directory rule by name, and the
    shared façade drops the visibility it computes for the rest, so the plugin decides by the
    only evidence a C++ header carries: where it sits."""
    _repository(tmp_path)
    facts = cpp.PLUGIN.surface_facts(tmp_path, [])
    values = {fact.value for fact in facts}
    assert "Aspose.Widget.Shape" in values
    assert not [fact for fact in facts if "Buffer" in fact.value]
    assert not [fact for fact in facts if "internal" in fact.evidence[0].path]


def test_a_namespace_survives_its_private_headers_and_is_evidenced_at_a_public_one(
    tmp_path: Path,
) -> None:
    """`Aspose.Slides.Foss` is introduced by a header under `_internal/`; the namespace is real
    and public, and citing a header no consumer may include would be evidence for the wrong
    claim."""
    _repository(tmp_path)
    facts = {fact.value: fact for fact in cpp.PLUGIN.surface_facts(tmp_path, [])}
    assert facts["Aspose"].attributes == {"symbol_kind": "module"}
    assert "internal" not in facts["Aspose"].evidence[0].path
    assert "internal" not in facts["Aspose.Widget"].evidence[0].path


def test_a_namespace_with_nothing_public_left_in_it_is_dropped(tmp_path: Path) -> None:
    _repository(tmp_path)
    private = tmp_path / "Widget" / "include" / "widget" / "internal" / "only.h"
    private.write_text(
        PRIVATE_HEADER.replace("namespace Widget", "namespace Hidden"),
        encoding="utf-8",
        newline="\n",
    )
    values = {fact.value for fact in cpp.PLUGIN.surface_facts(tmp_path, [])}
    assert "Aspose.Hidden" not in values


def test_a_repository_with_no_cmakelists_has_no_manifest(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# nothing here\n", encoding="utf-8", newline="\n")
    assert cpp.PLUGIN.detect_manifest(tmp_path) is None
    assert cpp.PLUGIN.include_root(tmp_path) == tmp_path


def _stub_toolchain(monkeypatch, phrase: str, calls: list[str]) -> None:  # type: ignore[no-untyped-def]
    from repository_presenter.components.readme.extractors.platforms import cpp_examples

    cpp_examples._BUILT.clear()
    monkeypatch.setattr(cpp_examples, "cpp_compiler", lambda: "/tools/gcc/bin/g++")
    monkeypatch.setattr(cpp_examples, "cmake_executable", lambda: "/tools/cmake")
    monkeypatch.setattr(cpp_examples, "ninja_executable", lambda: "/tools/ninja")

    def built(*args: object, **kwargs: object) -> tuple[str, list[Path]]:
        calls.append(phrase)
        return phrase, []

    monkeypatch.setattr(cpp_examples, "build_product", built)


def test_a_successful_cmake_build_is_a_measured_build_with_no_example_at_all(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """Aspose.PDF for C++ (CUT-2, 2026-10-11): install_command:cmake stayed UNRESOLVED -> BC-02
    unless a README snippet happened to compile. The library's own build, driven with no example,
    is the proof a registry-less install stands on, and the command is exactly the two steps."""
    manifest = _repository(tmp_path)
    calls: list[str] = []
    _stub_toolchain(monkeypatch, "succeeded", calls)
    build = cpp.PLUGIN.verify_build(tmp_path, manifest, tmp_path / "build-run")
    assert build.verified is True
    assert build.command == "cmake -S Widget -B build\ncmake --build build"
    assert build.summary.startswith("succeeded (")
    assert calls == ["succeeded"]


def test_a_failed_or_impossible_build_advertises_nothing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manifest = _repository(tmp_path)
    for phrase in ("failed", "configure failed", "configure timed out"):
        _stub_toolchain(monkeypatch, phrase, [])
        build = cpp.PLUGIN.verify_build(tmp_path, manifest, tmp_path / "build-run")
        assert (build.verified, build.command) == (False, "")
        assert build.summary == phrase
    from repository_presenter.components.readme.extractors.platforms import cpp_examples

    cpp_examples._BUILT.clear()
    monkeypatch.setattr(cpp_examples, "cpp_compiler", lambda: None)
    none = cpp.PLUGIN.verify_build(tmp_path, manifest, tmp_path / "build-run")
    assert (none.verified, none.command) == (False, "")
    assert none.summary == "not attempted (no C++ compiler on this machine)"


def test_the_examples_build_and_the_measured_build_are_one_build(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """A configure that fetches dependencies measured 95-140 s; running it twice per repository
    would double the cost and could disagree with itself."""
    from repository_presenter.components.readme.extractors.platforms import cpp_examples
    from repository_presenter.core.examples import ExampleCandidate
    from repository_presenter.core.execution import ExecutionResult

    manifest = _repository(tmp_path)
    calls: list[str] = []
    _stub_toolchain(monkeypatch, "succeeded", calls)
    monkeypatch.setattr(cpp_examples, "_version", lambda *a, **k: "g++ 16.2.0")
    monkeypatch.setattr(
        cpp_examples,
        "execute",
        lambda argv, **k: ExecutionResult(tuple(argv), 0, "", "", False, ()),
    )
    candidate = ExampleCandidate(1, "cpp", "int main() { return 0; }\n", "README.md", 1, 3, "u1")
    receipts = cpp.PLUGIN.verify_examples(tmp_path, [], [candidate], tmp_path / "ex-run")
    assert [r.outcome for r in receipts] == ["EXECUTED"] and receipts[0].build_verified
    build = cpp.PLUGIN.verify_build(tmp_path, manifest, tmp_path / "build-run")
    assert build.verified and calls == ["succeeded"]


CELLS_README = """# Aspose.Cells FOSS for C++

[![NuGet version](https://img.shields.io/nuget/v/Aspose.Cells.Cpp.FOSS.svg)](https://www.nuget.org/packages/Aspose.Cells.Cpp.FOSS/)

Aspose.Cells FOSS for C++ is published on NuGet as `Aspose.Cells.Cpp.FOSS`.

```bash
nuget install Aspose.Cells.Cpp.FOSS
```

```xml
<PackageReference Include="Aspose.Cells.Cpp.FOSS" Version="26.4.1" />
```
"""


def _nuget_reading(published, matched, name):  # type: ignore[no-untyped-def]
    from repository_presenter.components.readme.extractors.surface.registry import (
        RegistryObservation,
    )

    return RegistryObservation(
        "nuget",
        name,
        published,
        published is None,
        f"https://api.nuget.org/v3-flatcontainer/{name.lower()}/index.json",
        "flat-container",
        "test",
        repository_matched=matched,
    )


def test_the_nuget_package_the_readme_names_is_a_distribution_fact_apart_from_the_cmake_name(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """Aspose.Cells for C++ (CUT-2, 2026-10-11): `package:name` is the CMake project
    `Widget` - a build target - while the repository's own README, badge and install command name
    the NuGet package a reader installs. That is a second identity fact, derived from the same
    README and confirmed by NuGet only when NuGet's own project URL points back here."""
    manifest = _repository(tmp_path)
    (tmp_path / "README.md").write_text(CELLS_README, encoding="utf-8", newline="\n")
    declared = cpp.PLUGIN.manifest_facts(tmp_path, manifest, ["README.md", "Widget/CMakeLists.txt"])
    [candidate] = [f for f in declared if f.id.startswith("package:distribution")]
    assert candidate.value == "Aspose.Cells.Cpp.FOSS" and candidate.polarity == "UNRESOLVED"
    assert candidate.evidence[0].path == "README.md"
    assert {f.id: f for f in declared}["package:name"].value == "Widget"
    repository = Fact(
        "identity:repository", "identity", "aspose-cells-foss/Cells-Cpp", (Evidence("x"),)
    )
    for published, matched, wanted in (
        (True, True, "SUPPORTED"),
        (True, False, "UNRESOLVED"),  # a name another project owns
        (True, None, "UNRESOLVED"),
        (False, None, "CONTRADICTED"),
        (None, None, "UNRESOLVED"),
    ):
        seen: list[tuple[object, ...]] = []

        def observed(ecosystem, name, published=published, matched=matched, seen=seen, **kwargs):  # type: ignore[no-untyped-def]
            seen.append((ecosystem, name, kwargs.get("repository")))
            return _nuget_reading(published, matched, name)

        monkeypatch.setattr(cpp, "_observe", observed)
        resolved, probes = cpp.PLUGIN.registry_facts([repository, *declared])
        by_id = {f.id: f for f in resolved}
        distribution = next(f for f in resolved if f.id.startswith("package:distribution"))
        assert distribution.polarity == wanted
        assert seen == [("net", "Aspose.Cells.Cpp.FOSS", "aspose-cells-foss/Cells-Cpp")]
        assert by_id["install_command:cmake"].polarity == "UNRESOLVED"
        assert [p.outcome for p in probes] == ["UNRESOLVED", wanted]


def test_a_readme_naming_no_nuget_package_yields_no_distribution_fact(tmp_path: Path) -> None:
    manifest = _repository(tmp_path)
    (tmp_path / "README.md").write_text("# Widget\n\nBuild with CMake.\n", encoding="utf-8")
    facts = cpp.PLUGIN.manifest_facts(tmp_path, manifest, ["README.md"])
    assert not [f for f in facts if f.id.startswith("package:distribution")]
    assert cpp.declared_nuget_packages(CELLS_README) == ["Aspose.Cells.Cpp.FOSS"]
