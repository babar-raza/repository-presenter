"""The chain a Development and Testing addition rests on: one CI job's steps, or one project file's.

``plan_chain`` reads the build and test facts and the pinned workflows; nothing here runs a command.
The negative controls are the review's own findings: a build and a test from different jobs, a
release workflow's step, a step that needs a configure the job never runs, a test narrowed to one
module, an install the job runs that cannot be printed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_correction.chain import (
    CI_JOB,
    PROJECT_FILES,
    narrows_test,
    plan_chain,
    setup_parts,
)
from repository_presenter.core.facts import Fact, FactsDocument

CI = ".github/workflows/ci.yml"


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def tree_of(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def facts_of(*facts: Fact) -> FactsDocument:
    return FactsDocument("o/r", "a" * 40, tuple(facts))


def command(
    make_fact: Any, role: str, value: str, *, path: str = CI, job: str = "test", source: str = "ci"
) -> Fact:
    detail = f"{role} command; job {job} runs `{value}`" if source == "ci" else f"{role} command"
    return make_fact(
        f"build_test_asset:{role}-command",
        value,
        evidence=((path, detail),),
        attributes={
            "role": f"{role} command",
            "source": "ci workflow" if source == "ci" else source,
        },
    )


WORKFLOW = """\
name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python -m pip install --upgrade pip && python -m pip install -e '.[test]'
      - run: cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
      - run: cmake --build build --config Release
      - run: python -m pytest -q
  packaging:
    runs-on: ubuntu-latest
    steps:
      - run: python -m build
"""


def test_a_ci_job_gives_its_installs_then_its_build_then_its_test(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, CI, WORKFLOW)
    build = command(make_fact, "build", "cmake --build build --config Release")
    build = Fact(
        build.id,
        build.kind,
        build.value,
        build.evidence,
        attributes={
            **(build.attributes or {}),
            "precondition": "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release",
        },
    )
    test = command(make_fact, "test", "python -m pytest -q")
    plan = plan_chain(facts_of(build, test), tmp_path, tree_of(tmp_path))
    assert plan.kind == CI_JOB and plan.source == f"{CI} job test"
    assert [(s.role, s.command) for s in plan.steps] == [
        ("setup", "python -m pip install -e '.[test]'"),  # the pip self-upgrade is noise
        ("setup", "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release"),  # the job's own order
        ("build", "cmake --build build --config Release"),
        ("test", "python -m pytest -q"),
    ]
    assert plan.excluded == ()
    assert plan.setup_before(test.id) == (
        "python -m pip install -e '.[test]'",
        "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release",
    )
    assert len(plan.digest()) == 64 and plan.digest() == plan.digest()


def test_a_command_of_another_job_is_left_out_not_joined(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, CI, WORKFLOW)
    build = command(make_fact, "build", "python -m build", job="packaging")
    test = command(make_fact, "test", "python -m pytest -q")
    plan = plan_chain(facts_of(build, test), tmp_path, tree_of(tmp_path))
    assert plan.kind == CI_JOB and plan.source.endswith("job test")
    assert [s.command for s in plan.steps if s.role in {"build", "test"}] == ["python -m pytest -q"]
    (left_out,) = plan.excluded
    assert left_out.fact_id == build.id and "is not a step of the CI job" in left_out.reason


def test_a_step_of_a_release_workflow_is_never_part_of_a_chain(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, ".github/workflows/publish.yml", WORKFLOW)
    build = command(make_fact, "build", "python -m build", path=".github/workflows/publish.yml")
    plan = plan_chain(facts_of(build), tmp_path, tree_of(tmp_path))
    assert plan.kind == "" and plan.steps == ()
    assert "release workflow" in plan.excluded[0].reason


def test_a_test_narrowed_to_part_of_the_suite_is_not_the_projects_test_command(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, CI, WORKFLOW)
    test = command(make_fact, "test", "python -m unittest tests.test_smoke -v")
    plan = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert plan.kind == "" and "only part of the test suite" in plan.excluded[0].reason


@pytest.mark.parametrize(
    ("text", "narrowed"),
    [
        ("pytest -q", False),
        ("python -m pytest tests/", False),
        ("pytest tests/test_one.py", True),
        ("pytest -k fast", True),
        ("python -m unittest discover -s tests -v", False),
        ("python -m unittest -v", False),
        ("python -m unittest tests.test_smoke -v", True),
        ("go test ./...", False),
        ("go test -run TestOne ./...", True),
        ("dotnet test A.sln", False),
        ("dotnet test A.sln --filter Name~Fast", True),
        ("mvn -B test", False),
        ("mvn test -Dtest=One", True),
        ("cargo test --all-targets", False),
        ("cargo test --lib", True),
        ("npm test", False),
        ("ctest --test-dir build", False),
        ("ctest --test-dir build -R unit", True),
    ],
)
def test_which_test_commands_run_only_part_of_the_suite(text: str, narrowed: bool) -> None:
    assert narrows_test(text) is narrowed


def test_a_job_install_that_cannot_be_printed_ends_the_chain_with_the_reason(
    tmp_path: Path, make_fact: Any
) -> None:
    write(
        tmp_path,
        CI,
        "on: [push]\njobs:\n  test:\n    runs-on: x\n    steps:\n"
        "      - run: pip install twine pytest\n      - run: pytest -q\n",
    )
    test = command(make_fact, "test", "pytest -q")
    plan = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert plan.kind == "" and "cannot be printed safely" in plan.note


def test_a_conditional_install_ends_the_chain(tmp_path: Path, make_fact: Any) -> None:
    write(
        tmp_path,
        CI,
        "on: [push]\njobs:\n  test:\n    runs-on: x\n    steps:\n"
        "      - run: npm install\n        if: runner.os == 'Linux'\n      - run: npm test\n",
    )
    test = command(make_fact, "test", "npm test")
    plan = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert plan.kind == "" and "conditional" in plan.note


def test_a_tool_the_extractor_found_missing_is_installed_first_unless_the_job_installs_it(
    tmp_path: Path, make_fact: Any
) -> None:
    write(
        tmp_path,
        CI,
        "on: [push]\njobs:\n  b:\n    runs-on: x\n    steps:\n"
        "      - run: python -m pip install --upgrade pip build\n      - run: python -m build\n",
    )
    build = command(make_fact, "build", "python -m build", job="b")
    declared = Fact(
        build.id,
        build.kind,
        build.value,
        build.evidence,
        attributes={**(build.attributes or {}), "precondition": "pip install build"},
    )
    plan = plan_chain(facts_of(declared), tmp_path, tree_of(tmp_path))
    assert [s.command for s in plan.steps] == [
        "python -m pip install --upgrade pip build",
        "python -m build",
    ]  # one install covers `pip install build`: not printed twice


def test_the_build_and_test_of_one_makefile_are_one_chain(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "Makefile", "build:\n\ttrue\n\ntest:\n\ttrue\n")
    build = command(make_fact, "build", "make build", path="Makefile", source="Makefile")
    test = command(make_fact, "test", "make test", path="Makefile", source="Makefile")
    plan = plan_chain(facts_of(build, test), tmp_path, tree_of(tmp_path))
    assert plan.kind == PROJECT_FILES and plan.source == "Makefile"
    assert [s.command for s in plan.steps] == ["make build", "make test"]


def test_commands_of_different_project_files_are_not_joined(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "Makefile", "test:\n\ttrue\n")
    write(tmp_path, "package.json", '{"scripts": {"build": "tsc"}}')
    build = command(
        make_fact, "build", "npm run build", path="package.json", source="package.json script"
    )
    test = command(make_fact, "test", "make test", path="Makefile", source="Makefile")
    plan = plan_chain(facts_of(build, test), tmp_path, tree_of(tmp_path))
    assert plan.kind == PROJECT_FILES and [s.command for s in plan.steps] == ["make test"]
    assert plan.excluded[0].fact_id == build.id


def test_a_package_script_chain_starts_with_npm_install(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "package.json", '{"scripts": {"build": "tsc", "test": "jest"}}')
    build = command(
        make_fact, "build", "npm run build", path="package.json", source="package.json script"
    )
    test = command(make_fact, "test", "npm test", path="package.json", source="package.json script")
    plan = plan_chain(facts_of(build, test), tmp_path, tree_of(tmp_path))
    assert [(s.role, s.command) for s in plan.steps] == [
        ("setup", "npm install"),
        ("build", "npm run build"),
        ("test", "npm test"),
    ]


def test_pytest_is_installed_by_the_extra_that_lists_it_and_by_nothing_else(
    tmp_path: Path, make_fact: Any
) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname = "p"\n[project.optional-dependencies]\n'
        'docs = ["sphinx"]\ndev = ["ruff", "pytest>=8"]\n',
    )
    test = command(
        make_fact, "test", "pytest", path="pyproject.toml", source="toolchain convention"
    )
    plan = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert [s.command for s in plan.steps] == ['python -m pip install -e ".[dev]"', "pytest"]
    write(tmp_path, "pyproject.toml", '[project]\nname = "p"\n')
    bare = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert [s.command for s in bare.steps] == ["pytest"]  # nothing declared: nothing is invented


def test_a_dependency_group_that_lists_pytest_is_installed_with_the_group_flag(
    tmp_path: Path, make_fact: Any
) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname = "p"\n[dependency-groups]\ndev = ["pytest>=8", "ruff"]\n',
    )
    test = command(
        make_fact, "test", "pytest", path="pyproject.toml", source="toolchain convention"
    )
    plan = plan_chain(facts_of(test), tmp_path, tree_of(tmp_path))
    assert plan.steps[0].command == "python -m pip install -e . --group dev"


def test_no_command_fact_means_no_chain(tmp_path: Path) -> None:
    plan = plan_chain(facts_of(), tmp_path, [])
    assert plan.kind == "" and "no build or test command" in plan.note


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("python -m pip install --upgrade pip", []),
        ("python -m pip install --upgrade pip setuptools wheel", []),
        (
            "python -m pip install --upgrade pip && python -m pip install -e .",
            ["python -m pip install -e ."],
        ),
        ("pip install -e '.[test]'", ["pip install -e '.[test]'"]),
        ('python -m pip install ".[test]"', ['python -m pip install ".[test]"']),
        ("npm install --no-audit --no-fund", ["npm install --no-audit --no-fund"]),
        ("go vet ./...", []),
        ("pip install twine", None),
        ("pip install -r req.txt | tee log", None),
        ("pip install $PKG", None),
        ("pip install foo>=1.0", None),
        ("pip install $(cat req.txt)", None),
    ],
)
def test_which_install_lines_of_a_job_may_be_printed(line: str, expected: list[str] | None) -> None:
    assert setup_parts(line) == expected
