"""Build, test, and CI-matrix facts are read from the clone's own files, never composed.

TC-COV-02 (G3-W08). Each fixture is a trimmed copy of a real file from the 36-repository
portfolio's clones (named per test); the negative controls are the lines a reader must never be
told to run.
"""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    CI_MATRIX_FACT_ID,
    TEST_COMMAND_FACT_ID,
    ci_matrix_fact,
    command_facts,
    matrix_axes,
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
