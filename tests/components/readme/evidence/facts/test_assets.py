"""Build and test assets are read from the tree inventory, never guessed."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.evidence.facts.assets import (
    CI_BADGE_FACT_ID,
    asset_facts,
    ci_badge_fact,
)


def test_assets_present_in_the_tree_become_facts() -> None:
    paths = [
        "README.md",
        "setup.py",
        "tests/test_a.py",
        "tests/test_b.py",
        ".github/workflows/publish.yml",
        "docs/releasing.md",
        "aspose/threed/__init__.py",
    ]
    facts = asset_facts(paths)
    assert [(f.id, f.value) for f in facts] == [
        ("build_test_asset:tests", "tests/"),
        ("build_test_asset:ci", ".github/workflows/"),
        ("build_test_asset:docs", "docs/"),
    ]
    tests = facts[0]
    assert [e.path for e in tests.evidence] == ["tests/test_a.py", "tests/test_b.py", "tests/"]
    assert tests.evidence[-1].detail == "2 files; test suite"


def test_no_assets_yield_no_facts() -> None:
    assert asset_facts(["README.md", "LICENSE"]) == []


def test_evidence_paths_are_bounded() -> None:
    paths = [f"tests/test_{i}.py" for i in range(20)]
    facts = asset_facts(paths)
    assert len(facts[0].evidence) == 6
    assert facts[0].evidence[-1].detail == "20 files; test suite"


# --- G7-W12 (REG-18): tests and samples that do not sit at the repository root. ---
# Aspose.PSD-FOSS-for-.NET keeps its suite in src/Aspose.PSD.FOSS.Test/ and its samples in
# samples/; Aspose.Cells-FOSS-for-Cpp keeps tests in Aspose.Cells.Foss.Cpp.Tests/ and
# Aspose.Cells.Foss.Cpp/tests/. The root-only check recorded no build_test_asset for either, so
# Development and Testing could not render and the candidate died at BC-05
# (BUILD_TEST_PATH_UNRECORDED, an extractor gap).


def test_a_dotnet_test_project_and_a_samples_directory_become_facts() -> None:
    paths = [
        "README.md",
        "src/Aspose.PSD.FOSS/Psd.cs",
        "src/Aspose.PSD.FOSS.Test/ReaderTests.cs",
        "src/Aspose.PSD.FOSS.Test/WriterTests.cs",
        "samples/Common/Helpers.cs",
        "samples/Aspose.PSD.FOSS.Samples.Layers/Program.cs",
    ]
    by_id = {f.id: f for f in asset_facts(paths)}
    assert by_id["build_test_asset:tests"].value == "src/Aspose.PSD.FOSS.Test/"
    assert by_id["build_test_asset:tests"].evidence[-1].detail == "2 files; test suite"
    assert by_id["build_test_asset:examples"].value == "samples/"
    assert by_id["build_test_asset:examples"].evidence[-1].detail == "2 files; example directory"


def test_the_nested_test_directory_with_the_most_files_is_the_suite() -> None:
    paths = [
        "Aspose.Cells.Foss.Cpp/tests/cell_value_test.cpp",
        "Aspose.Cells.Foss.Cpp.Tests/tests/Unit/a.cpp",
        "Aspose.Cells.Foss.Cpp.Tests/tests/Unit/b.cpp",
        "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt",
    ]
    (tests,) = asset_facts(paths)
    assert (tests.id, tests.value) == (
        "build_test_asset:tests",
        "Aspose.Cells.Foss.Cpp.Tests/",
    )


def test_a_root_tests_directory_still_wins_over_a_nested_one() -> None:
    paths = ["tests/test_a.py", "pkg/tests/test_b.py", "pkg/tests/test_c.py"]
    (tests,) = asset_facts(paths)
    assert tests.value == "tests/"


def test_vendored_deep_and_lookalike_directories_are_not_a_test_suite() -> None:
    """Negative controls: dependency trees, directories deeper than two levels, and names that
    merely end in the letters (latest, contest) are not the repository's own suite."""
    paths = [
        "node_modules/leftpad/test/index.js",
        "third_party/gtest/tests/a.cc",
        "vendor/x/tests/b.go",
        "a/b/c/tests/deep.py",
        "latest/notes.md",
        "src/contest/a.py",
    ]
    assert asset_facts(paths) == []


# --- build-status badge target (plans/idea.md: "real build status ... may not be fabricated") ---

REPO = "acme-foss/Acme-FOSS-for-Python"
CI = """\
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest -q
"""


def _clone(tmp_path, workflows: dict[str, str]):
    paths = []
    for name, text in workflows.items():
        file = tmp_path / ".github" / "workflows" / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        paths.append(f".github/workflows/{name}")
    return tmp_path, paths


def test_a_push_triggered_test_workflow_becomes_the_build_badge_target(tmp_path) -> None:
    clone, paths = _clone(tmp_path, {"ci.yml": CI})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None
    assert fact.id == CI_BADGE_FACT_ID == "link_target:badge.ci"
    assert fact.value == f"https://github.com/{REPO}/actions/workflows/ci.yml"
    assert (fact.attributes or {})["branch"] == "main"
    assert fact.polarity == "SUPPORTED"


def test_the_branch_comes_from_the_workflow_never_a_default(tmp_path) -> None:
    master = CI.replace("[main]", "[master, release/**]")
    clone, paths = _clone(tmp_path, {"ci.yml": master})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None and (fact.attributes or {})["branch"] == "master"
    unfiltered = CI.replace("    branches: [main]\n", "")
    other = tmp_path / "other"
    clone, paths = _clone(other, {"ci.yml": unfiltered})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None and "branch" not in (fact.attributes or {})


def test_the_bare_on_key_and_the_list_form_are_read(tmp_path) -> None:
    listed = "on: [push, pull_request]\njobs:\n  b:\n    steps:\n      - run: cargo test\n"
    clone, paths = _clone(tmp_path, {"build.yaml": listed})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None and fact.value.endswith("/actions/workflows/build.yaml")


@pytest.mark.parametrize(
    ("name", "text"),
    [
        # no workflow at all is covered by the empty-tree case below
        ("publish.yml", CI),  # a publish workflow is not the build status
        ("ci.yml", CI.replace("  push:\n    branches: [main]\n", "")),  # pull_request only
        ("ci.yml", "on: workflow_dispatch\njobs:\n  b:\n    steps:\n      - run: pytest\n"),
        ("ci.yml", CI.replace("pytest -q", "echo hello")),  # runs nothing that builds or tests
        ("ci.yml", CI.replace("[main]", "['**/x*']")),  # only a glob: no literal branch to name
        ("ci.yml", ": : not yaml : ["),  # malformed
        ("ci.yml", "- just\n- a list\n"),  # not a mapping
        ("my ci.yml", CI),  # a name that cannot sit in a badge URL
    ],
)
def test_a_workflow_that_is_not_a_real_build_status_yields_no_fact(tmp_path, name, text) -> None:
    clone, paths = _clone(tmp_path, {name: text})
    assert ci_badge_fact(REPO, clone, paths) is None


def test_no_workflows_yield_no_fact(tmp_path) -> None:
    assert ci_badge_fact(REPO, tmp_path, ["README.md", "tests/test_a.py"]) is None


def test_a_path_in_the_tree_that_is_not_on_disk_is_skipped(tmp_path) -> None:
    assert ci_badge_fact(REPO, tmp_path, [".github/workflows/ci.yml"]) is None


def test_several_qualifying_workflows_resolve_to_the_preferred_name(tmp_path) -> None:
    clone, paths = _clone(tmp_path, {"zz.yml": CI, "lint.yml": CI, "ci.yml": CI})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None and fact.value.endswith("/ci.yml")


@pytest.mark.parametrize(
    ("push", "expected"),
    [
        ("  push:\n    branches: ['**']\n", None),  # every branch includes the default branch
        ("  push:\n    branches:\n      - '*'\n", None),
        ("  push:\n", None),
        ("  push:\n    branches-ignore: ['wip/**']\n", None),
        ("  push:\n    branches: [main, 'release/**']\n", "main"),
    ],
)
def test_a_push_that_covers_the_default_branch_is_usable(
    push: str, expected: str | None, tmp_path
) -> None:
    text = CI.replace("  push:\n    branches: [main]\n", push)
    clone, paths = _clone(tmp_path, {"ci.yml": text})
    fact = ci_badge_fact(REPO, clone, paths)
    assert fact is not None
    assert (fact.attributes or {}).get("branch") == expected


@pytest.mark.parametrize(
    "push",
    [
        "  push:\n    tags: ['v*']\n",  # a branch push never triggers a tags-only workflow
        "  push:\n    branches-ignore: [main]\n",  # the default branch is excluded
        "  push:\n    branches: ['release/**']\n",  # only a partial glob: no branch to name
    ],
)
def test_a_push_that_does_not_cover_the_default_branch_yields_no_fact(push: str, tmp_path) -> None:
    text = CI.replace("  push:\n    branches: [main]\n", push)
    clone, paths = _clone(tmp_path, {"ci.yml": text})
    assert ci_badge_fact(REPO, clone, paths) is None
