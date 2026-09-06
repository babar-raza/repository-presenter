"""The C++ plugin reads CMake for identity and publishes only what a consumer may include."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms import cpp
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact

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
