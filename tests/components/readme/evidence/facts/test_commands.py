"""Build, test, and CI-matrix facts are read from the clone's own files, never composed.

TC-COV-02 (G3-W08). Each fixture is a trimmed copy of a real file from the 36-repository
portfolio's clones (named per test); the negative controls are the lines a reader must never be
told to run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.components.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    CI_MATRIX_FACT_ID,
    TEST_COMMAND_FACT_ID,
    ci_jobs,
    ci_matrix_fact,
    command_facts,
    command_form,
    commands_in_text,
    matrix_axes,
    release_workflow_fact,
)
from repository_presenter.core.facts import Fact

# aspose-email-foss/Aspose.Email-FOSS-for-Python, .github/workflows/ci.yml (trimmed)
EMAIL_PYTHON_CI = """\
name: CI
on:
  push:
    branches:
      - master
jobs:
  tests:
    name: Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version:
          - "3.10"
          - "3.11"
          - "3.12"
          - "3.13"
    steps:
      - uses: actions/checkout@v6
      - name: Install package
        run: python -m pip install --upgrade pip && python -m pip install -e .
      - name: Run test suite
        run: python -m unittest discover -s tests -v
  packaging:
    runs-on: ubuntu-latest
    steps:
      - name: Install packaging tools
        run: python -m pip install --upgrade pip build twine
      - name: Build distributions
        run: python -m build
      - name: Validate distributions
        run: python -m twine check --strict dist/*
"""

# the same repository's release.yml (trimmed): it also builds, and also uploads
EMAIL_PYTHON_RELEASE = """\
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - run: python -m build
      - run: python -m twine upload dist/*
"""

# aspose-cells-foss/Aspose.Cells-FOSS-for-Rust, .github/workflows/ci.yml (trimmed)
CELLS_RUST_CI = """\
name: CI
on:
  push:
    branches: [main, master]
jobs:
  fmt:
    runs-on: ubuntu-latest
    steps:
      - run: cargo fmt --all --check
  build-and-test:
    name: ${{ matrix.name }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - name: Linux x64
            os: ubuntu-latest
          - name: Windows x64
            os: windows-latest
          - name: macOS ARM
            os: macos-14
    steps:
      - name: cargo check
        run: cargo check --all-targets
      - name: cargo clippy
        run: cargo clippy --all-targets
      - name: cargo test
        run: cargo test --all-targets
      - name: cargo bench
        run: cargo bench
"""

# The coverage inventory's own fixture (tools/reviewer/coverage_inventory/fixtures/clone), whose
# matrix has a non-runtime axis and whose run step chains two commands with &&.
INVENTORY_CI = """\
name: ci
on: [push]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]
        archive: [tar.gz, zip]
    runs-on: ${{ matrix.os }}
    steps:
      - run: pip install -e .
      - run: |
          python -m pytest -q
          dotnet build -c Release && dotnet test src/Lib
"""

# aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript, package.json (trimmed)
PDF_TYPESCRIPT_PACKAGE = {
    "name": "@aspose/pdf",
    "scripts": {
        "build": "npm run clean && tsc -p tsconfig.build.json",
        "test": "vitest run",
        "gen:fonts": "node scripts/gen-std14-fonts.mjs",
    },
}

# aspose-font-foss/Aspose.Font-FOSS-for-Python, Makefile (trimmed)
FONT_PYTHON_MAKEFILE = """\
.PHONY: all test build
all: lint test build
install: ## Install package and dev dependencies
\tpip install -e .
test: ## Run all tests
\tpytest
lint: ## Run linter (ruff check)
\truff check .
build: ## Build wheel and sdist
\tpython -m build
publish: ## Publish to PyPI
\ttwine upload dist/*
"""


def _clone(tmp_path: Path, files: dict[str, str]) -> tuple[Path, list[str]]:
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, "utf-8", newline="\n")
    return tmp_path, sorted(files)


def _by_id(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.id: fact for fact in facts}


def test_a_workflow_run_step_names_the_build_and_the_test_command(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/ci.yml": EMAIL_PYTHON_CI,
            ".github/workflows/release.yml": EMAIL_PYTHON_RELEASE,
            "tests/test_a.py": "",
        },
    )
    facts = _by_id(command_facts(clone, tree))
    test = facts[TEST_COMMAND_FACT_ID]
    assert (test.kind, test.value) == (
        "build_test_asset",
        "python -m unittest discover -s tests -v",
    )
    assert [(e.path, e.detail) for e in test.evidence] == [
        (
            ".github/workflows/ci.yml",
            "test command; job tests runs `python -m unittest discover -s tests -v`",
        )
    ]
    assert test.attributes == {"role": "test command", "source": "ci workflow"}
    build = facts[BUILD_COMMAND_FACT_ID]
    assert build.value == "python -m build"
    # The CI workflow outranks the release workflow that runs the same command.
    assert build.evidence[0].path == ".github/workflows/ci.yml"


def test_a_cargo_workflow_names_check_and_test_and_never_clippy_or_bench(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": CELLS_RUST_CI})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "cargo check --all-targets"
    assert facts[TEST_COMMAND_FACT_ID].value == "cargo test --all-targets"


def test_a_line_that_chains_branches_or_carries_a_flag_for_release_is_never_admitted(
    tmp_path: Path,
) -> None:
    # `dotnet build -c Release && dotnet test src/Lib` holds shell control (&&) and a release
    # word; only the clean pytest line on its own is a command a reader may be told to run.
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": INVENTORY_CI})
    facts = _by_id(command_facts(clone, tree))
    assert facts[TEST_COMMAND_FACT_ID].value == "python -m pytest -q"
    assert BUILD_COMMAND_FACT_ID not in facts


def test_expressions_secrets_pipes_and_publishing_are_never_commands(tmp_path: Path) -> None:
    workflow = (
        "on: [push]\n"
        "jobs:\n"
        "  j:\n"
        "    steps:\n"
        "      - run: dotnet test --logger ${{ matrix.logger }}\n"
        "      - run: dotnet build -p:Token=abc\n"
        "      - run: pytest | tee out.txt\n"
        "      - run: npm publish\n"
        "      - run: mvn deploy\n"
        "      - run: python -m twine upload dist/*\n"
        "      - run: pip install pytest\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": workflow})
    assert command_facts(clone, tree) == []


def test_a_package_json_script_names_the_npm_commands(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {"package.json": json.dumps(PDF_TYPESCRIPT_PACKAGE)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[TEST_COMMAND_FACT_ID].value == "npm test"
    assert facts[BUILD_COMMAND_FACT_ID].value == "npm run build"
    assert facts[TEST_COMMAND_FACT_ID].attributes == {
        "role": "test command",
        "source": "package.json script",
    }


def test_the_npm_placeholder_test_script_is_not_a_test_command(tmp_path: Path) -> None:
    package = {"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}
    clone, tree = _clone(tmp_path, {"package.json": json.dumps(package)})
    assert command_facts(clone, tree) == []


def test_a_makefile_names_make_test_and_make_build(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {"Makefile": FONT_PYTHON_MAKEFILE})
    facts = _by_id(command_facts(clone, tree))
    assert facts[TEST_COMMAND_FACT_ID].value == "make test"
    assert facts[BUILD_COMMAND_FACT_ID].value == "make build"
    assert facts[BUILD_COMMAND_FACT_ID].evidence[0].path == "Makefile"


def test_a_workflow_outranks_a_makefile_and_a_script(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            "Makefile": FONT_PYTHON_MAKEFILE,
            "package.json": json.dumps(PDF_TYPESCRIPT_PACKAGE),
            ".github/workflows/ci.yml": CELLS_RUST_CI,
        },
    )
    facts = _by_id(command_facts(clone, tree))
    assert facts[TEST_COMMAND_FACT_ID].value == "cargo test --all-targets"


def test_a_toolchain_manifest_names_its_standard_commands_only_when_tests_exist(
    tmp_path: Path,
) -> None:
    clone, tree = _clone(tmp_path, {"Cargo.toml": '[package]\nname = "x"\n', "src/lib.rs": ""})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "cargo build"
    assert TEST_COMMAND_FACT_ID not in facts  # no test directory: `cargo test` is not asserted
    detail = facts[BUILD_COMMAND_FACT_ID].evidence[0].detail or ""
    assert "no workflow step or script names it" in detail

    with_tests = tmp_path / "t2"
    clone, tree = _clone(with_tests, {"Cargo.toml": '[package]\nname = "x"\n', "tests/it.rs": ""})
    assert _by_id(command_facts(clone, tree))[TEST_COMMAND_FACT_ID].value == "cargo test"


def test_a_solution_file_names_the_dotnet_commands_with_its_own_path(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            "Aspose.Cells_FOSS.sln": "",
            "src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj": "",
            "src/Aspose.Cells_FOSS.Tests/A.cs": "",
        },
    )
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "dotnet build Aspose.Cells_FOSS.sln"
    assert facts[TEST_COMMAND_FACT_ID].value == "dotnet test Aspose.Cells_FOSS.sln"


def test_pytest_by_convention_needs_the_manifest_to_mention_pytest(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    clone, tree = _clone(plain, {"pyproject.toml": "[project]\nname='x'\n", "tests/t.py": ""})
    assert command_facts(clone, tree) == []
    configured = tmp_path / "configured"
    clone, tree = _clone(
        configured,
        {"pyproject.toml": "[tool.pytest.ini_options]\ntestpaths=['tests']\n", "tests/t.py": ""},
    )
    assert _by_id(command_facts(clone, tree))[TEST_COMMAND_FACT_ID].value == "pytest"


def test_a_release_workflow_command_is_the_last_resort_below_convention(tmp_path: Path) -> None:
    workflow = (
        "on:\n  push:\n    tags: ['v*']\n"
        "jobs:\n  j:\n    steps:\n      - run: mvn -B verify\n      - run: python -m build\n"
    )
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/maven-central-release.yml": workflow,
            "pom.xml": "<project/>",
            "src/test/java/ATest.java": "",
        },
    )
    facts = _by_id(command_facts(clone, tree))
    # Cells-Java: the convention `mvn test` beats the release workflow's `mvn verify`.
    assert facts[TEST_COMMAND_FACT_ID].value == "mvn test"
    assert facts[BUILD_COMMAND_FACT_ID].value == "mvn package"


def test_a_build_only_a_release_workflow_names_is_still_a_command_that_exists(
    tmp_path: Path,
) -> None:
    # Note-Python: `python -m build` appears only in publish-pypi.yml.
    workflow = (
        "on:\n  release:\n    types: [published]\n"
        "jobs:\n  j:\n    steps:\n      - run: python -m build\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/publish-pypi.yml": workflow})
    build = _by_id(command_facts(clone, tree))[BUILD_COMMAND_FACT_ID]
    assert (build.value, build.evidence[0].path) == (
        "python -m build",
        ".github/workflows/publish-pypi.yml",
    )


def test_nothing_is_invented_for_a_repository_without_build_files(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {"README.md": "# x\n", "LICENSE": "MIT\n"})
    assert command_facts(clone, tree) == []
    assert ci_matrix_fact(clone, tree) is None


def test_the_facts_are_the_same_bytes_every_run_and_carry_no_timestamp(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path,
        {".github/workflows/ci.yml": EMAIL_PYTHON_CI, "tests/test_a.py": ""},
    )
    first = [*command_facts(clone, tree), ci_matrix_fact(clone, tree)]
    second = [*command_facts(clone, tree), ci_matrix_fact(clone, tree)]
    assert first == second
    rendered = json.dumps([f.evidence[0].detail for f in first if f is not None])
    assert not any(token in rendered for token in ("20", "T0", "UTC")), rendered


# --- The CI matrix ---------------------------------------------------------------------------


def test_the_matrix_keeps_python_versions_as_written_not_as_floats(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": EMAIL_PYTHON_CI})
    matrix = ci_matrix_fact(clone, tree)
    assert matrix is not None
    assert matrix.id == CI_MATRIX_FACT_ID
    assert matrix.value == "python-version=3.10,3.11,3.12,3.13"  # "3.10", never 3.1
    assert matrix.evidence[0].path == ".github/workflows/ci.yml"
    assert matrix.evidence[0].detail == "job tests strategy.matrix axes python-version"
    assert matrix_axes(matrix) == [("python-version", ["3.10", "3.11", "3.12", "3.13"])]


def test_the_matrix_reads_os_and_runtime_axes_and_skips_the_rest(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": INVENTORY_CI})
    matrix = ci_matrix_fact(clone, tree)
    assert matrix is not None
    assert matrix.value == "os=ubuntu-latest,windows-latest;python-version=3.10,3.11,3.12"
    assert "archive" not in matrix.value


def test_the_matrix_reads_the_os_names_a_matrix_lists_only_under_include(tmp_path: Path) -> None:
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": CELLS_RUST_CI})
    matrix = ci_matrix_fact(clone, tree)
    assert matrix is not None
    assert matrix.value == "os=ubuntu-latest,windows-latest,macos-14"


def test_a_release_workflow_matrix_and_an_expression_matrix_are_not_reported(
    tmp_path: Path,
) -> None:
    release = (
        "on: [push]\njobs:\n  j:\n    strategy:\n      matrix:\n        os: [ubuntu-latest]\n"
        "    steps:\n      - run: true\n"
    )
    expression = (
        "on: [push]\njobs:\n  j:\n    strategy:\n      matrix:\n"
        "        python-version: ${{ fromJson(needs.x.outputs.v) }}\n"
        "    steps:\n      - run: true\n"
    )
    clone, tree = _clone(
        tmp_path,
        {".github/workflows/publish.yml": release, ".github/workflows/ci.yml": expression},
    )
    assert ci_matrix_fact(clone, tree) is None


# --- One job, one chain (L-cov3, independent reviews of 2026-10-11) ----------------------------
# The fixtures are the real workflows of the two C++ repositories the reviewers found stitched:
# Aspose.PDF-FOSS-for-Cpp (a release job's Debug build beside the package-consumer test's
# `ctest --test-dir build-pkgtest`) and Aspose.Slides-FOSS-for-Cpp (the AddressSanitizer job's
# `cmake --build build-asan` without the configure step that creates `build-asan`).


def _fixture(name: str) -> str:
    return (Path(__file__).parent / "fixtures" / name).read_text("utf-8")


def _workflow(jobs: str) -> str:
    return "name: CI\non: [push]\njobs:\n" + jobs


def test_the_pdf_cpp_workflows_name_no_command_rather_than_a_pair_stitched_from_two_jobs(
    tmp_path: Path,
) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/ci.yml": _fixture("pdf_cpp_ci.yml"),
            ".github/workflows/release.yml": _fixture("pdf_cpp_release.yml"),
            ".github/package-test/CMakeLists.txt": "",
            "CMakeLists.txt": "",
            "tests/CMakeLists.txt": "",
        },
    )
    # ci.yml configures Linux and Windows in two conditional steps (no single configure to print);
    # release.yml's Package job does the same, and its smoke test is a shell `if` over another
    # source tree. The old pair was `cmake --build build --config Debug --target ...` from the
    # Windows leg and `ctest --test-dir build-pkgtest ...` from the smoke test.
    assert command_facts(clone, tree) == []


def test_the_slides_cpp_workflows_name_no_sanitizer_command(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/ci.yml": _fixture("slides_cpp_ci.yml"),
            ".github/workflows/nuget-release.yml": _fixture("slides_cpp_release.yml"),
            "CMakeLists.txt": "",
            "tests/CMakeLists.txt": "",
        },
    )
    # The primary job configures through a shell variable (`$arch`), so its chain cannot be
    # printed; the sanitizer job's `build-asan` and the minimum-CMake job's `build-floor` are
    # variants a reader cannot reproduce from the plain commands.
    assert command_facts(clone, tree) == []


def _single_configure_pdf_cpp_ci() -> str:
    """The real PDF-Cpp ci.yml with the Windows configure leg removed: one unconditional configure
    for the build directory."""
    text = _fixture("pdf_cpp_ci.yml")
    leg = "      - name: Configure (Windows)\n        if: runner.os == 'Windows'\n"
    leg += "        run: cmake -S . -B build\n\n"
    assert leg in text
    return text.replace(leg, "").replace("        if: runner.os == 'Linux'\n", "")


def test_a_job_with_one_configure_names_its_chain_and_carries_the_configure_as_precondition(
    tmp_path: Path,
) -> None:
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/ci.yml": _single_configure_pdf_cpp_ci(),
            ".github/workflows/release.yml": _fixture("pdf_cpp_release.yml"),
            "tests/CMakeLists.txt": "",
        },
    )
    facts = _by_id(command_facts(clone, tree))
    configure = "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release"
    build = facts[BUILD_COMMAND_FACT_ID]
    test = facts[TEST_COMMAND_FACT_ID]
    # `--config Release` and `-DCMAKE_BUILD_TYPE=Release` name a configuration, not a release.
    assert build.value == "cmake --build build --config Release --parallel 4"
    assert test.value == "ctest --test-dir build --build-config Release --output-on-failure"
    assert build.attributes == {
        "role": "build command",
        "source": "ci workflow",
        "precondition": configure,
    }
    assert (test.attributes or {})["precondition"] == configure
    assert [(e.path, e.detail) for e in build.evidence] == [
        (
            ".github/workflows/ci.yml",
            "build command; job build-and-test runs "
            f"`cmake --build build --config Release --parallel 4`; after `{configure}`",
        )
    ]


_CPP_PLAIN_AND_SANITIZER = r"""
  asan:
    runs-on: ubuntu-24.04
    steps:
      - run: cmake -S . -B build-asan -DSANITIZE_ADDRESS=ON
      - run: cmake --build build-asan --parallel 4
      - run: ctest --test-dir build-asan --output-on-failure
  main:
    runs-on: ubuntu-24.04
    steps:
      - run: cmake -S . -B build-main
      - run: cmake --build build-main --parallel 4
      - run: ctest --test-dir build-main --output-on-failure
"""


def test_the_plain_job_is_named_over_a_sanitizer_job_that_sorts_first(tmp_path: Path) -> None:
    clone, tree = _clone(
        tmp_path, {".github/workflows/ci.yml": _workflow(_CPP_PLAIN_AND_SANITIZER)}
    )
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "cmake --build build-main --parallel 4"
    assert facts[TEST_COMMAND_FACT_ID].value == "ctest --test-dir build-main --output-on-failure"
    assert (facts[BUILD_COMMAND_FACT_ID].attributes or {})["precondition"] == (
        "cmake -S . -B build-main"
    )


@pytest.mark.parametrize(
    "job",
    [
        "sanitizer",
        "asan",
        "ubsan",
        "valgrind",
        "coverage",
        "benchmarks",
        "docs",
        "package-test",
        "pkgtest",
        "smoke-test",
        "consumer",
        "nuget-pack",
        "cmake-floor",
        "minimum",
        "reproducible",
        "release",
        "publish",
        "package",
    ],
)
def test_a_side_job_names_no_command_in_a_workflow_that_is_not_a_release_workflow(
    tmp_path: Path, job: str
) -> None:
    jobs = f"  {job}:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest -q\n"
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    assert command_facts(clone, tree) == []


def test_a_job_named_by_its_function_is_still_read(tmp_path: Path) -> None:
    # `packaging` (Aspose.Email-FOSS-for-Python) and `tests` are jobs, not side jobs.
    jobs = (
        "  packaging:\n    steps:\n      - run: python -m build\n"
        "  tests:\n    steps:\n      - run: pytest -q\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "python -m build"
    assert facts[TEST_COMMAND_FACT_ID].value == "pytest -q"


def test_a_step_named_for_the_package_is_still_read_but_a_smoke_test_step_is_not(
    tmp_path: Path,
) -> None:
    jobs = (
        "  j:\n    steps:\n"
        "      - name: Build the package\n        run: cargo build\n"
        "      - name: Smoke-test the built package\n        run: cargo test --test smoke\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "cargo build"
    assert TEST_COMMAND_FACT_ID not in facts


def test_a_release_workflows_own_job_is_still_the_last_resort(tmp_path: Path) -> None:
    jobs = "  publish:\n    steps:\n      - run: python -m build\n      - run: pytest -q\n"
    clone, tree = _clone(tmp_path, {".github/workflows/publish.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "python -m build"
    assert facts[TEST_COMMAND_FACT_ID].value == "pytest -q"


def test_python_m_build_carries_the_tool_it_needs_as_a_precondition(tmp_path: Path) -> None:
    # 3D-Python, Note-Python: `python -m build` fails on a clean venv without `pip install build`.
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": EMAIL_PYTHON_CI})
    build = _by_id(command_facts(clone, tree))[BUILD_COMMAND_FACT_ID]
    assert build.value == "python -m build"
    assert build.attributes == {
        "role": "build command",
        "source": "ci workflow",
        "precondition": "pip install build",
    }
    assert build.evidence[0].detail == (
        "build command; job packaging runs `python -m build`; after `pip install build`"
    )


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        # `ctest` in a directory no earlier step of the job configured.
        ("      - run: cmake --build build\n      - run: ctest --test-dir build\n", None),
        # a bare `ctest` works in a directory nothing says: the build stays, the test is not named.
        (
            "      - run: cmake -S . -B build\n      - run: cmake --build build\n"
            "      - run: ctest\n",
            "cmake --build build",
        ),
        # the configure comes after the build.
        ("      - run: cmake --build build\n      - run: cmake -S . -B build\n", None),
        # the configure is for another source tree.
        (
            "      - run: cmake -S sub -B build\n      - run: cmake --build build\n",
            None,
        ),
        # a conditional configure is not every reader's.
        (
            "      - if: runner.os == 'Linux'\n        run: cmake -S . -B build\n"
            "      - run: cmake --build build\n",
            None,
        ),
        # two configures that differ.
        (
            "      - run: cmake -S . -B build\n      - run: cmake -S . -B build -DX=1\n"
            "      - run: cmake --build build\n",
            None,
        ),
        # an unprintable configure (a shell variable, a continuation).
        (
            "      - run: cmake -S . -B build $arch\n      - run: cmake --build build\n",
            None,
        ),
        (
            "      - run: |\n          cmake -S . -B build \\\n            -DX=1\n"
            "      - run: cmake --build build\n",
            None,
        ),
        # steps in another directory.
        (
            "      - working-directory: sub\n        run: cmake -S . -B build\n"
            "      - working-directory: sub\n        run: cmake --build build\n",
            None,
        ),
        # shell control flow runs the commands conditionally.
        (
            "      - run: |\n          if [ -d build ]; then\n            cmake --build build\n"
            "          fi\n",
            None,
        ),
        # a decidable chain.
        (
            "      - run: cmake -S . -B build\n      - run: cmake --build build\n",
            "cmake --build build",
        ),
    ],
)
def test_a_build_directory_command_needs_one_printable_configure_earlier_in_its_job(
    tmp_path: Path, steps: str, expected: str | None
) -> None:
    jobs = f"  build:\n    runs-on: ubuntu-latest\n    steps:\n{steps}"
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert (facts[BUILD_COMMAND_FACT_ID].value if BUILD_COMMAND_FACT_ID in facts else None) == (
        expected
    )
    assert TEST_COMMAND_FACT_ID not in facts


def test_a_test_in_a_build_directory_is_named_only_beside_the_build_of_its_own_job(
    tmp_path: Path,
) -> None:
    jobs = (
        "  main:\n    steps:\n      - run: cmake -S . -B build\n"
        "      - run: cmake --build build\n"
        "  other:\n    steps:\n      - run: cmake -S . -B other\n"
        "      - run: ctest --test-dir other\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[BUILD_COMMAND_FACT_ID].value == "cmake --build build"
    assert TEST_COMMAND_FACT_ID not in facts


def test_a_test_that_works_in_no_build_directory_is_named_beside_a_directory_build(
    tmp_path: Path,
) -> None:
    jobs = (
        "  main:\n    steps:\n      - run: cmake -S . -B build\n"
        "      - run: cmake --build build\n      - run: pytest -q\n"
    )
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": _workflow(jobs)})
    facts = _by_id(command_facts(clone, tree))
    assert facts[TEST_COMMAND_FACT_ID].value == "pytest -q"


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        (None, None),
        ({"scripts": {"test": "vitest run"}}, None),
        ({"scripts": {"build": "tsc", "test": "vitest run"}}, "npm run build"),
        ({"scripts": {"build": "tsc"}}, "npm run build"),
    ],
)
def test_an_npm_run_command_names_a_script_the_package_defines(
    tmp_path: Path, package: dict[str, object] | None, expected: str | None
) -> None:
    files = {
        ".github/workflows/ci.yml": _workflow("  j:\n    steps:\n      - run: npm run build\n")
    }
    if package is not None:
        files["package.json"] = json.dumps(package)
    clone, tree = _clone(tmp_path, files)
    facts = _by_id(command_facts(clone, tree))
    assert (facts[BUILD_COMMAND_FACT_ID].value if BUILD_COMMAND_FACT_ID in facts else None) == (
        expected
    )


def test_npm_test_from_ci_needs_a_test_script(tmp_path: Path) -> None:
    workflow = _workflow("  j:\n    steps:\n      - run: npm test\n")
    clone, tree = _clone(tmp_path, {".github/workflows/ci.yml": workflow})
    assert command_facts(clone, tree) == []
    placeholder = tmp_path / "placeholder"
    package = {"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}
    clone, tree = _clone(
        placeholder, {".github/workflows/ci.yml": workflow, "package.json": json.dumps(package)}
    )
    assert command_facts(clone, tree) == []


# --- The release workflow --------------------------------------------------------------------


def _release_of(tmp_path: Path, files: dict[str, str]) -> Fact | None:
    clone, tree = _clone(tmp_path, files)
    return release_workflow_fact(clone, tree)


# acc-corr2-set2: the ci.yml of the eight JMAP repositories is a secret scan and a test run.
JMAP_CI = """\
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gitleaks/gitleaks-action@v2
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cargo test --all-targets
      - uses: actions/upload-artifact@v4
        with:
          name: results
          path: target/
"""
# acc-corr2-set2: PDF-Go's lint.yml is golangci-lint; its releases are manual.
PDF_GO_LINT = """\
name: lint
on: [push, pull_request]
jobs:
  golangci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: golangci/golangci-lint-action@v6
"""


@pytest.mark.parametrize(
    "files",
    [
        {".github/workflows/ci.yml": JMAP_CI},
        {".github/workflows/lint.yml": PDF_GO_LINT},
        {".github/workflows/ci.yml": JMAP_CI, ".github/workflows/lint.yml": PDF_GO_LINT},
        # a file name that says release proves nothing
        {".github/workflows/release-notes.yml": PDF_GO_LINT},
        {".github/workflows/release.yml": _workflow("  j:\n    steps:\n      - run: echo hi\n")},
    ],
)
def test_no_workflow_with_no_releasing_step_is_a_release_workflow(
    tmp_path: Path, files: dict[str, str]
) -> None:
    assert _release_of(tmp_path, files) is None


@pytest.mark.parametrize(
    "step",
    [
        "uses: pypa/gh-action-pypi-publish@release/v1",
        "uses: softprops/action-gh-release@v2",
        "uses: goreleaser/goreleaser-action@v6",
        "run: python -m twine upload dist/*",
        "run: npm publish --access public",
        "run: yarn publish",
        "run: cargo publish",
        "run: dotnet nuget push pkg.nupkg --source nuget.org",
        "run: mvn -B deploy",
        "run: ./gradlew publish",
        "run: gh release create v1 dist/*",
        "run: gh release upload v1 dist/*",
        "run: poetry publish",
    ],
)
def test_a_step_that_publishes_or_releases_makes_its_workflow_the_release_workflow(
    tmp_path: Path, step: str
) -> None:
    jobs = f"  j:\n    steps:\n      - {step}\n"
    fact = _release_of(tmp_path, {".github/workflows/deliver.yml": _workflow(jobs)})
    assert fact is not None
    assert (fact.id, fact.kind, fact.value, fact.polarity) == (
        "build_test_asset:release-workflow",
        "build_test_asset",
        ".github/workflows/deliver.yml",
        "SUPPORTED",
    )
    assert fact.evidence[0].path == ".github/workflows/deliver.yml"
    assert (fact.evidence[0].detail or "").startswith("release step; job j ")


@pytest.mark.parametrize(
    "step",
    [
        "run: python -m twine check --strict dist/*",
        "run: python -m twine upload --repository testpypi dist/*",
        "run: npm publish --dry-run",
        "run: cargo publish --dry-run",
        "run: ./gradlew publishToMavenLocal",
        "run: gh release view v1",
        "run: |\n          # npm publish\n          echo npm publish to registry\n"
        "          printf cargo-publish",
        "uses: actions/upload-artifact@v4",
        "uses: actions/checkout@v4",
        "uses: pypa/gh-action-pypi-publish@release/v1\n        with:\n          repository-url: https://test.pypi.org/legacy/",
    ],
)
def test_a_rehearsal_or_an_artifact_upload_is_not_a_release(tmp_path: Path, step: str) -> None:
    jobs = f"  j:\n    steps:\n      - {step}\n"
    assert _release_of(tmp_path, {".github/workflows/deliver.yml": _workflow(jobs)}) is None


def test_the_workflow_named_publish_or_release_is_preferred_and_the_choice_is_deterministic(
    tmp_path: Path,
) -> None:
    publishing = "  publish:\n    steps:\n      - run: npm publish\n"
    files = {
        ".github/workflows/a-ci.yml": _workflow(publishing),
        ".github/workflows/release.yml": _workflow(publishing),
        ".github/workflows/z-publish.yml": _workflow(publishing),
    }
    fact = _release_of(tmp_path, files)
    assert fact is not None and fact.value == ".github/workflows/release.yml"
    assert fact == _release_of(tmp_path, files)


def test_the_cpp_release_workflows_are_found_by_their_releasing_steps(tmp_path: Path) -> None:
    pdf = _release_of(
        tmp_path / "pdf", {".github/workflows/release.yml": _fixture("pdf_cpp_release.yml")}
    )
    assert pdf is not None
    assert pdf.evidence[0].detail == "release step; job release runs gh release"
    slides = _release_of(
        tmp_path / "slides",
        {
            ".github/workflows/ci.yml": _fixture("slides_cpp_ci.yml"),
            ".github/workflows/nuget-release.yml": _fixture("slides_cpp_release.yml"),
        },
    )
    assert slides is not None
    assert (slides.value, slides.evidence[0].detail) == (
        ".github/workflows/nuget-release.yml",
        "release step; job publish runs nuget push",
    )


# --- Equivalent commands ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("shown", "wanted"),
    [
        ("pytest", "python -m pytest -q"),
        ("python -m pytest -q", "pytest"),
        ("pytest tests/", "pytest"),
        ("uv run pytest", "pytest"),
        ("mvn clean package -DskipTests", "mvn package"),
        ("./mvnw -B clean package", "mvn package"),
        ("mvn   test", "mvn test"),
        ("$ mvn test", "mvn test"),
        ("npm run test", "npm test"),
        ("yarn test", "npm test"),
        ("dotnet build src/App/App.csproj", "dotnet build App.sln"),
        ("dotnet test App.sln --no-build", "dotnet test"),
        ("cargo build --release", "cargo build"),
        ("go test -v ./...", "go test ./..."),
        ("cmake --build build --config Release", "cmake --build build --parallel 4"),
        ("cmake -S . -B build -DCMAKE_BUILD_TYPE=Release", "cmake -S . -B build"),
        ("ctest --test-dir build -j4", "ctest --test-dir build --output-on-failure"),
        ("pip install build", "python -m pip install build"),
        ("CI=1 npm test", "npm test"),
        ("make test", "make test"),
        ("gradlew build", "./gradlew build"),
    ],
)
def test_a_shown_command_covers_the_equivalent_wanted_one(shown: str, wanted: str) -> None:
    have, want = command_form(shown), command_form(wanted)
    assert have is not None and want is not None
    assert have.covers(want), (have, want)


@pytest.mark.parametrize(
    ("shown", "wanted"),
    [
        ("mvn test", "mvn package"),
        ("mvn package", "mvn test"),
        ("make", "make test"),
        ("make test", "make"),
        ("go test ./internal/...", "go test ./..."),
        ("pytest", "pip install pytest"),
        ("pip install pytest", "pytest"),
        ("npm test", "npm run build"),
        ("cargo test", "cargo build"),
        ("cmake --build build", "cmake -S . -B build"),
        ("cmake -S . -B build", "cmake --build build"),
        ("cmake --build build", "cmake --build other"),
        ("ctest --test-dir build", "cmake --build build"),
        ("dotnet build", "dotnet test"),
        ("pytest -k slow", "pytest"),
        ("python script.py", "python -m pytest"),
    ],
)
def test_a_shown_command_does_not_cover_a_different_wanted_one(shown: str, wanted: str) -> None:
    have, want = command_form(shown), command_form(wanted)
    assert have is not None and want is not None
    assert not have.covers(want), (have, want)


def test_commands_are_read_from_fences_indented_blocks_prompts_and_inline_code() -> None:
    text = (
        "Run `mvn test` first, then `pytest -q`.\n\n"
        "```bash\n# build it\nmake build  # all targets\ncd x && cmake --build build\n```\n\n"
        "~~~console\n$ npm run build\n~~~\n\n"
        "    cargo test\n\n"
        "$ go test ./...\n\n"
        "Plain prose about npm and mvn is not a command.\n"
    )
    programs = [(f.program, tuple(sorted(f.verbs))) for f in commands_in_text(text)]
    assert programs == [
        ("mvn", ("test",)),
        ("pytest", ()),
        ("make", ("build",)),
        ("cd", ("x",)),
        ("cmake", ("--build",)),
        ("npm", ("build",)),
        ("cargo", ("test",)),
        ("go", ("test",)),
    ]


def test_the_jobs_a_command_can_belong_to_are_the_ones_the_commands_are_read_from(
    tmp_path: Path,
) -> None:
    """``ci_jobs`` is the one place that says which jobs count: a sanitizer job and a step of
    another directory are not there, a release workflow's job is, flagged, and every line keeps
    whether it is a plain command and whether its step is conditional."""
    workflow = """\
name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pip install -e .
      - run: pytest -q
        if: matrix.os == 'linux'
      - run: echo "$HOME" | tee log
      - run: make docs
        working-directory: docs
  asan:
    runs-on: ubuntu-latest
    steps:
      - run: pytest
"""
    clone, tree = _clone(
        tmp_path,
        {
            ".github/workflows/ci.yml": workflow,
            ".github/workflows/publish.yml": EMAIL_PYTHON_RELEASE,
        },
    )
    jobs = {(job.path, job.job): job for job in ci_jobs(clone, tree)}
    assert set(jobs) == {
        (".github/workflows/ci.yml", "test"),
        (".github/workflows/publish.yml", "publish"),
    }
    test = jobs[(".github/workflows/ci.yml", "test")]
    assert test.release is False and jobs[(".github/workflows/publish.yml", "publish")].release
    assert [(run.line, run.admitted, run.conditional) for run in test.runs] == [
        ("pip install -e .", True, False),
        ("pytest -q", True, True),
        ('echo "$HOME" | tee log', False, False),
    ]
