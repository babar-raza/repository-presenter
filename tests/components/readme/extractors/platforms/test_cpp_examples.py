"""`-fsyntax-only` proves the example's calls exist; a broken header leaves it unchecked."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms import cpp_examples
from repository_presenter.core.examples import ExampleCandidate

CMAKELISTS = """
cmake_minimum_required(VERSION 3.16)
project(Widget VERSION 1.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
add_library(widget STATIC src/widget.cpp)
target_include_directories(widget PUBLIC include)
"""
HEADER = """
#pragma once
#include <string>
namespace Aspose {
namespace Widget {
class Shape {
public:
  void Save(const std::string& path);
};
}
}
"""
# A public header a consumer cannot compile: it includes a third party's header that is not on
# the include path, exactly as Aspose.Slides for C++'s `shape_collection.h` includes pugixml's.
# The compiler stops at that line, so it files no diagnostic about the example at all.
BROKEN_HEADER = """
#pragma once
#include <rp_no_such_dependency.hpp>
namespace Aspose {
namespace Widget {
class Shape {
public:
  void Save(const char* path);
};
}
}
"""
GOOD = (
    '#include "widget/shape.h"\n'
    "using namespace Aspose::Widget;\n"
    "Shape shape;\n"
    'shape.Save("out.bin");\n'
)
BAD = (
    '#include "widget/shape.h"\n'
    "using namespace Aspose::Widget;\n"
    "Shape shape;\n"
    'shape.Explode("out.bin");\n'
)
PROGRAM = (
    '#include "widget/shape.h"\n'
    "int main() {\n"
    "  Aspose::Widget::Shape shape;\n"
    '  shape.Save("out.bin");\n'
    "  return 0;\n"
    "}\n"
)

compiler = cpp_examples.cpp_compiler()
needs_compiler = pytest.mark.skipif(compiler is None, reason="no C++ compiler on this machine")


def _repository(root: Path, header: str = HEADER) -> Path:
    (root / "CMakeLists.txt").write_text(CMAKELISTS, encoding="utf-8", newline="\n")
    headers = root / "include" / "widget"
    headers.mkdir(parents=True)
    (headers / "shape.h").write_text(header, encoding="utf-8", newline="\n")
    (root / "src").mkdir()
    (root / "src" / "widget.cpp").write_text(
        '#include "widget/shape.h"\n'
        "void Aspose::Widget::Shape::Save(const std::string& path) { (void)path; }\n",
        encoding="utf-8",
        newline="\n",
    )
    return root / "CMakeLists.txt"


def _candidates(*sources: str) -> list[ExampleCandidate]:
    return [
        ExampleCandidate(
            ordinal=index + 1,
            language="cpp",
            code=source,
            source_path="README.md",
            start_line=1,
            end_line=9,
            unit_id=f"inherited_unit:{index + 1:03d}.code_block",
        )
        for index, source in enumerate(sources)
    ]


def test_a_body_is_given_a_main_and_its_preamble_stays_at_file_scope() -> None:
    """C++ has no top-level statements: six of Aspose.Cells for C++'s seven README examples,
    nine of Aspose.Slides' ten and eight of Aspose.PDF's eleven are bodies, not programs."""
    wrapped = cpp_examples.wrap_example(
        "#include <memory>\n"
        "// a comment\n"
        "namespace pdf = Aspose::Pdf;\n"
        "using namespace Aspose;\n"
        "pdf::Document doc;\n"
        'doc.Save("out.pdf");\n'
    )
    lines = wrapped.splitlines()
    assert lines[0] == "#include <memory>"
    assert "namespace pdf = Aspose::Pdf;" in lines[:4]
    assert "using namespace Aspose;" in lines[:5]
    assert "int main() {" in lines
    body = lines[lines.index("int main() {") :]
    assert "    pdf::Document doc;" in body
    assert '    doc.Save("out.pdf");' in body
    assert body[-2:] == ["    return 0;", "}"]


def test_a_snippet_that_is_already_a_program_is_compiled_as_it_stands() -> None:
    assert cpp_examples.wrap_example(PROGRAM) == PROGRAM
    assert cpp_examples.wrap_example("int main(int argc, char** argv) { return 0; }\n").startswith(
        "int main("
    )


def test_the_example_diagnostics_are_separated_from_every_other_file() -> None:
    output = (
        "example_003.cpp:4:7: error: 'Explode' is not a member of 'Shape'\n"
        "include/widget/shape.h:7:15: error: 'NoSuchType' was not declared in this scope\n"
        "C:/tools/gcc/include/c++/16.2.0/bits/unique_ptr.h:90:23: error: invalid application\n"
        "example_003.cpp:4:7: note: suggested alternative\n"
    )
    mine, theirs = cpp_examples.split_diagnostics(output, "example_003.cpp")
    assert len(mine) == 1 and "Explode" in mine[0]
    assert len(theirs) == 2
    # A note is not an error and decides nothing.
    assert not any("note:" in line for line in mine + theirs)


def test_only_unbound_identifiers_make_a_fence_an_excerpt_rather_than_a_falsehood() -> None:
    """Live-verified 2026-09-10 against the real repository's current source: five of Aspose.
    Cells-FOSS-for-Cpp's seven examples open on names their README establishes in an earlier,
    un-inherited section (Taskcard C; the same class rust_examples.py's unbound_values() already
    excludes for Rust's own E0425). GCC raises two diagnostic shapes for this - "was not
    declared in this scope" for a bare identifier (`sheet`), "has not been declared" for one used
    to its own left of `::` (`CellArea::CreateCellArea`, example:003's own real shape)."""
    lines = [
        "example_003.cpp:3:25: error: 'sheet' was not declared in this scope",
        "example_003.cpp:5:24: error: 'CellArea' has not been declared",
        "example_007.cpp:3:17: error: 'workbook' was not declared in this scope",
    ]
    assert cpp_examples.unbound_identifiers(lines) == ["sheet", "CellArea", "workbook"]


def test_a_fence_that_names_something_the_library_lacks_is_not_an_excerpt() -> None:
    """A real type mismatch is a real defect, and must not be excused as missing context -
    Aspose.Cells-FOSS-for-Cpp's own example:002."""
    real_bug = [
        "example_002.cpp:10:48: error: no match for 'operator[]' (operand types are "
        "'Aspose::Cells_FOSS::WorksheetCollection' and 'const char [9]')"
    ]
    assert cpp_examples.unbound_identifiers(real_bug) == []
    mixed = [
        "example_003.cpp:3:25: error: 'sheet' was not declared in this scope",
        "example_003.cpp:4:1: error: 'Missing' was not declared in this scope",
        "example_003.cpp:5:1: error: no match for 'operator[]' (operand types are 'int' and 'int')",
    ]
    assert cpp_examples.unbound_identifiers(mixed) == []


def test_the_toolchain_reaches_the_subprocess_path_and_never_the_process_one() -> None:
    """Loop-prompt section 1.3: nothing this lane provisions is on the user or system PATH."""
    before = os.environ.get("PATH", "")
    path = cpp_examples.toolchain_path("/tools/gcc/bin/g++", "/tools/ninja/ninja", None)
    assert path.split(os.pathsep)[:2] == [
        str(Path("/tools/gcc/bin")),
        str(Path("/tools/ninja")),
    ]
    assert path.endswith(before)
    assert os.environ.get("PATH", "") == before


def test_a_dependency_the_configure_step_fetched_becomes_an_include_root(tmp_path: Path) -> None:
    """Aspose.Slides for C++'s public `shape_collection.h` opens with `#include <pugixml.hpp>`,
    and pugixml's own header lives in `src/`, not `include/`."""
    (tmp_path / "_deps" / "pugixml-src" / "src").mkdir(parents=True)
    (tmp_path / "_deps" / "miniz-src" / "include").mkdir(parents=True)
    (tmp_path / "_deps" / "pugixml-build").mkdir()
    found = cpp_examples.fetched_includes(tmp_path)
    assert [path.relative_to(tmp_path).as_posix() for path in found] == [
        "_deps/miniz-src/include",
        "_deps/pugixml-src/src",
    ]


def test_nothing_is_verified_without_a_manifest(tmp_path: Path) -> None:
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path, None, tmp_path, "17", _candidates(GOOD), tmp_path / "run", 60.0
    )
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert "nothing to resolve" in receipts[0].detail


def test_no_candidates_means_no_receipts(tmp_path: Path) -> None:
    manifest = _repository(tmp_path)
    assert (
        cpp_examples.verify_cpp_examples(
            tmp_path, manifest, tmp_path / "include", "17", [], tmp_path / "run", 60.0
        )
        == []
    )


@needs_compiler
def test_a_true_example_compiles_and_a_false_one_does_not(tmp_path: Path) -> None:
    """The negative control: nothing the verifier stages can make a member that is not there
    appear, so a false claim about the library still fails (section 29.6 E5)."""
    manifest = _repository(tmp_path)
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path,
        manifest,
        tmp_path / "include",
        "17",
        _candidates(GOOD, BAD, PROGRAM),
        tmp_path / "run",
        120.0,
    )
    assert [receipt.outcome for receipt in receipts] == ["EXECUTED", "FAILED", "EXECUTED"]
    assert "-fsyntax-only" in receipts[0].detail
    assert "Explode" in receipts[1].detail
    # A receipt becomes a fact's evidence, so no absolute path of this machine may survive in it.
    for receipt in receipts:
        assert str(tmp_path) not in receipt.detail + receipt.stdout + receipt.stderr


@needs_compiler
def test_an_undeclared_binding_is_not_verified_but_a_real_type_error_still_fails(
    tmp_path: Path,
) -> None:
    """Taskcard C, end to end with the real compiler: a fence opening on names its README
    established elsewhere - both GCC's diagnostic shapes at once, matching Aspose.Cells-FOSS-
    for-Cpp's own real example:003 (`sheet` was not declared in this scope; `Missing` has not
    been declared) - is incomplete, not false. `BAD` (a real, genuinely wrong member call) still
    fails alongside it in the same run, so the relabeling never excuses an actual defect."""
    manifest = _repository(tmp_path)
    unbound = 'sheet.Save("out.bin");\nMissing::Create();\n'
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path,
        manifest,
        tmp_path / "include",
        "17",
        _candidates(unbound, BAD),
        tmp_path / "run",
        120.0,
    )
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED", "FAILED"]
    assert receipts[0].detail == (
        "the fence uses `sheet`, `Missing` without binding it; the README establishes it in an "
        "earlier section"
    )
    assert "Explode" in receipts[1].detail


@needs_compiler
def test_a_header_that_stops_the_compiler_leaves_the_example_unchecked(tmp_path: Path) -> None:
    """A "could not check" is not a "checked and it is false" (section 29.6 E5). Measured
    2026-09-06 on Aspose.PDF for C++: two of its eleven examples include a facade header whose
    `unique_ptr<Document>` over an incomplete type stops the compiler before any call of
    theirs."""
    manifest = _repository(tmp_path, BROKEN_HEADER)
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path,
        manifest,
        tmp_path / "include",
        "17",
        _candidates(GOOD),
        tmp_path / "run",
        120.0,
    )
    assert receipts[0].outcome == "NOT_VERIFIED"
    assert receipts[0].detail.startswith("BLOCKED_TOOLCHAIN: no diagnostic in the example itself")


@needs_compiler
def test_a_syntax_only_pass_does_not_claim_the_library_itself_builds(tmp_path: Path) -> None:
    """TB-01, external review D1, 2026-09-08: `-fsyntax-only` only compiles the example file,
    which includes the header, never `src/widget.cpp` - a broken implementation still lets a
    correct example syntax-check EXECUTED while the real `cmake --build` fails. Measured on
    Aspose.Cells for C++: the sealed README called `cmake -S . -B build` "verified against this
    revision" while its own examples.json recorded the CMake build failing. `build_verified` must
    be False here so extract.py never promotes the advertised build command from this receipt."""
    manifest = _repository(tmp_path)
    (tmp_path / "src" / "widget.cpp").write_text(
        "this is not valid C++ and cmake --build must fail\n", encoding="utf-8", newline="\n"
    )
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path, manifest, tmp_path / "include", "17", _candidates(GOOD), tmp_path / "run", 120.0
    )
    assert receipts[0].outcome == "EXECUTED"
    assert "CMake build failed" in receipts[0].detail
    assert receipts[0].build_verified is False


@needs_compiler
def test_a_genuinely_successful_build_still_marks_the_receipt_verified(tmp_path: Path) -> None:
    """The no-regression case: an EXECUTED receipt whose CMake build genuinely succeeded keeps
    build_verified True, exactly as every EXECUTED receipt behaved before TB-01."""
    manifest = _repository(tmp_path)
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path, manifest, tmp_path / "include", "17", _candidates(GOOD), tmp_path / "run", 120.0
    )
    assert receipts[0].outcome == "EXECUTED"
    assert "CMake build succeeded" in receipts[0].detail
    assert receipts[0].build_verified is True


def test_a_machine_without_a_compiler_verifies_nothing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manifest = _repository(tmp_path)
    monkeypatch.setattr(cpp_examples, "cpp_compiler", lambda: None)
    receipts = cpp_examples.verify_cpp_examples(
        tmp_path, manifest, tmp_path / "include", "17", _candidates(GOOD), tmp_path / "run", 60.0
    )
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert receipts[0].detail == "BLOCKED_TOOLCHAIN: no C++ compiler on this machine"


def test_the_toolchain_registry_is_read_by_absolute_path(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Every tool this lane provisioned is recorded there and nowhere else (LANE-B-00)."""
    tool = tmp_path / "g++.exe"
    tool.write_text("", encoding="utf-8", newline="\n")
    registry = tmp_path / "TOOLCHAIN_PATHS.txt"
    registry.write_text(
        f"gxx={tool}\nninja={tmp_path / 'absent.exe'}\n", encoding="utf-8", newline="\n"
    )
    monkeypatch.setenv(cpp_examples._REGISTRY_VARIABLE, str(registry))
    assert cpp_examples.recorded_tool("gxx") == str(tool)
    # A recorded path that no longer exists is no tool at all.
    assert cpp_examples.recorded_tool("ninja") is None
    assert cpp_examples.recorded_tool("cargo") is None
