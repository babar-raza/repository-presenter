"""Build and test assets are read from the tree inventory, never guessed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from repository_presenter.components.readme.evidence.facts import assets
from repository_presenter.components.readme.evidence.facts.assets import (
    CI_BADGE_FACT_ID,
    asset_facts,
    ci_badge_fact,
)
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems
from repository_presenter.core.ecosystems import NET, PYTHON, SPECS, SuiteFileRule

# Importing a platform module registers its spec; the suite rules under test live on them.
known_ecosystems()
CPP = SPECS["cpp"]
GO = SPECS["go"]
JAVA = SPECS["java"]
RUST = SPECS["rust"]
TYPESCRIPT = SPECS["typescript"]
# The renderer reads the suite size from the fact's evidence with this pattern.
RENDERER_COUNT = re.compile(r"(\d+) files")


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
    facts = asset_facts(paths, suite_files=PYTHON.suite_files)
    assert [(f.id, f.value) for f in facts] == [
        ("build_test_asset:tests", "tests/"),
        ("build_test_asset:ci", ".github/workflows/"),
        ("build_test_asset:docs", "docs/"),
    ]
    tests = facts[0]
    assert [e.path for e in tests.evidence] == ["tests/test_a.py", "tests/test_b.py", "tests/"]
    assert (
        tests.evidence[-1].detail == "2 files; test suite (2 test sources among the 2 files here)"
    )


def test_no_assets_yield_no_facts() -> None:
    assert asset_facts(["README.md", "LICENSE"]) == []


def test_evidence_paths_are_bounded() -> None:
    paths = [f"tests/test_{i}.py" for i in range(20)]
    facts = asset_facts(paths, suite_files=PYTHON.suite_files)
    assert len(facts[0].evidence) == 6
    assert (
        facts[0].evidence[-1].detail
        == "20 files; test suite (20 test sources among the 20 files here)"
    )


# --- G7-W12 (REG-18): tests and samples that do not sit at the repository root. ---
# Aspose.PSD-FOSS-for-.NET keeps its suite in src/Aspose.PSD.FOSS.Test/ and its samples in
# samples/; Aspose.Cells-FOSS-for-Cpp keeps tests in Aspose.Cells.Foss.Cpp.Tests/ and
# Aspose.Cells.Foss.Cpp/tests/. The root-only check recorded no build_test_asset for either, so
# Development and Testing could not render and the candidate died at BC-05
# (BUILD_TEST_PATH_UNRECORDED, an extractor gap).


def _write(root: Path, files: dict[str, str]) -> list[str]:
    """Write ``files`` under ``root`` and return their tree paths, sorted as a tree listing is."""
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return sorted(files)


FACT_TEST = "public class T {\n    [Fact]\n    public void Works() { }\n}\n"


def test_a_dotnet_test_project_and_a_samples_directory_become_facts(tmp_path: Path) -> None:
    paths = _write(
        tmp_path,
        {
            "README.md": "",
            "src/Aspose.PSD.FOSS/Psd.cs": "",
            "src/Aspose.PSD.FOSS.Test/ReaderTests.cs": FACT_TEST,
            "src/Aspose.PSD.FOSS.Test/WriterTests.cs": FACT_TEST,
            "samples/Common/Helpers.cs": "",
            "samples/Aspose.PSD.FOSS.Samples.Layers/Program.cs": "",
        },
    )
    by_id = {f.id: f for f in asset_facts(paths, suite_files=NET.suite_files, root=tmp_path)}
    assert by_id["build_test_asset:tests"].value == "src/Aspose.PSD.FOSS.Test/"
    assert by_id["build_test_asset:tests"].evidence[-1].detail == (
        "2 files; test suite (2 test sources among the 2 files here)"
    )
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


# --- TC-TST-01: "N test files" counts test sources, not what sits beside them ---
# The acceptance review of the wave-3 seals (2026-10-11) found the count wrong in four of five
# candidates: Aspose.3D for .NET said 18 (16 are .cs tests; the rest a .csproj and a run log),
# Aspose.3D for TypeScript 33 (32 are *.test.ts; tests/setup.ts is a global hook), Aspose.Cells
# for Java 38 (23 declare @Test; 15 are assertion helpers and scenario factories). Each fixture
# below is those trees, trimmed to the shapes that matter.


def _test_fact(paths: list[str], rule: SuiteFileRule | None, root: Path | None) -> tuple[str, int]:
    """The suite directory and the size the renderer would read from its evidence."""
    (tests,) = asset_facts(paths, suite_files=rule, root=root)
    assert tests.id == "build_test_asset:tests"
    match = RENDERER_COUNT.match(tests.evidence[-1].detail or "")
    return tests.value, int(match.group(1)) if match else -1


def test_dotnet_counts_files_that_declare_tests_not_the_project_file_or_the_run_log(
    tmp_path: Path,
) -> None:
    root = "src/test/Aspose.ThreeD.Tests/"
    paths = _write(
        tmp_path,
        {
            f"{root}ColladaTests.cs": "using Xunit;\npublic class ColladaTests {\n"
            "    [Fact]\n    public void Loads() { }\n}\n",
            f"{root}Formats/Test3DSImport.cs": "public class I {\n    [Theory]\n"
            "    [InlineData(1)]\n    public void Reads(int n) { }\n}\n",
            f"{root}roundtrip/SceneSaveErrorTests.cs": "[TestFixture]\npublic class S {\n"
            '    [Test, Category("io")]\n    public void Throws() { }\n}\n',
            f"{root}MsTests.cs": "[TestClass]\npublic class M {\n    [TestMethod]\n"
            "    public void Ok() { }\n}\n",
            f"{root}FixtureLoader.cs": "[TestClass]\npublic static class FixtureLoader {\n"
            "    public static string Path(string n) => n;\n}\n",
            f"{root}Aspose.ThreeD.Tests.csproj": '<Project Sdk="Microsoft.NET.Sdk" />\n',
            f"{root}test.log": "Failed: 53, Passed: 130\n",
            "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj": "<Project />\n",
        },
    )
    directory, count = _test_fact(paths, NET.suite_files, tmp_path)
    assert directory == "src/test/"
    assert count == 4  # Fact, Theory, Test, TestMethod; not the loader, the csproj, or the log
    (tests,) = asset_facts(paths, suite_files=NET.suite_files, root=tmp_path)
    assert [e.path for e in tests.evidence[:-1]] == sorted(
        f"{root}{name}"
        for name in (
            "ColladaTests.cs",
            "Formats/Test3DSImport.cs",
            "roundtrip/SceneSaveErrorTests.cs",
            "MsTests.cs",
        )
    )
    assert tests.evidence[-1].detail == (
        "4 files; test suite (4 test sources among the 7 files here)"
    )


def test_java_counts_classes_with_a_test_annotation_not_factories_and_helpers(
    tmp_path: Path,
) -> None:
    root = "src/test/java/org/aspose/cells_foss/"
    paths = _write(
        tmp_path,
        {
            f"{root}ChartTests.java": "import org.junit.jupiter.api.Test;\nclass ChartTests {\n"
            "    @Test\n    void draws() { }\n}\n",
            f"{root}WorkbookTests.java": "class WorkbookTests {\n    @ParameterizedTest\n"
            "    void saves(int n) { }\n}\n",
            f"{root}LegacyTests.java": "class LegacyTests {\n    @org.junit.Test\n"
            "    public void old() { }\n}\n",
            f"{root}Junit3Tests.java": "class Junit3Tests extends TestCase {\n"
            "    public void testIt() { }\n}\n",
            f"{root}AssertEx.java": "final class AssertEx {\n    static void same() { }\n}\n",
            f"{root}ChartScenarioFactory.java": "class ChartScenarioFactory {\n"
            "    // builds the workbook the @TestInstance lifecycle reuses\n}\n",
            f"{root}TemporaryDirectory.java": "class TemporaryDirectory { }\n",
            "pom.xml": "<project />\n",
        },
    )
    directory, count = _test_fact(paths, JAVA.suite_files, tmp_path)
    assert (directory, count) == ("src/test/", 4)


def test_typescript_counts_test_and_spec_files_not_the_setup_hook(tmp_path: Path) -> None:
    paths = _write(
        tmp_path,
        {
            "tests/setup.ts": "export {};\nglobal.pending = () => {};\n",
            "tests/entities/entity.test.ts": "describe('Entity', () => {});\n",
            "tests/mesh.test.ts": "describe('Mesh', () => {});\n",
            "tests/formats/step.spec.ts": "describe('Step', () => {});\n",
            "tests/formats/fixtures.ts": "export const cube = 1;\n",
            "jest.config.js": "module.exports = {};\n",
        },
    )
    assert _test_fact(paths, TYPESCRIPT.suite_files, tmp_path) == ("tests/", 3)


def test_python_counts_pytest_modules_not_conftest_init_or_data() -> None:
    paths = [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_scene.py",
        "tests/unit/mesh_test.py",
        "tests/unit/helpers.py",
        "tests/data/cube.obj",
    ]
    assert _test_fact(paths, PYTHON.suite_files, None) == ("tests/", 2)


def test_go_counts_test_files_that_declare_tests_not_shared_test_helpers(tmp_path: Path) -> None:
    paths = _write(
        tmp_path,
        {
            "tests/cells_test.go": "package tests\nfunc TestOpen(t *testing.T) {}\n",
            "tests/bench_test.go": "package tests\nfunc BenchmarkSave(b *testing.B) {}\n",
            "tests/suite_test.go": "package tests\nfunc (s *Suite) TestRead() {}\n",
            "tests/helpers_test.go": "package tests\nfunc newWorkbook() int { return 1 }\n",
            "tests/golden.json": "{}\n",
        },
    )
    assert _test_fact(paths, GO.suite_files, tmp_path) == ("tests/", 3)


def test_rust_counts_integration_tests_not_the_common_module(tmp_path: Path) -> None:
    paths = _write(
        tmp_path,
        {
            "tests/open.rs": "#[test]\nfn opens() {}\n",
            "tests/save.rs": "#[tokio::test]\nasync fn saves() {}\n",
            "tests/cfg.rs": "#[cfg(test)]\nmod inner { }\nfn not_a_test() {}\n",
            "tests/common/mod.rs": "pub fn fixture() {}\n",
        },
    )
    assert _test_fact(paths, RUST.suite_files, tmp_path) == ("tests/", 2)


def test_cpp_counts_framework_cases_and_test_executables_not_the_support_sources(
    tmp_path: Path,
) -> None:
    root = "Aspose.Cells.Foss.Cpp.Tests/"
    paths = _write(
        tmp_path,
        {
            f"{root}CMakeLists.txt": "add_executable(t tests/Unit/CellDataUnitTests.cpp)\n",
            f"{root}tests/Unit/CellDataUnitTests.cpp": "TEST(CellData, Reads) {}\n",
            f"{root}tests/Golden/WorkbookGoldenTests.cpp": "TEST_F(Golden, Matches) {}\n",
            f"{root}tests/Support/TestSupport.cpp": "void Prepare() {}\n",
            f"{root}tests/Support/TestSupport.h": "void Prepare();\n",
            f"{root}smoke/cell_value_test.cpp": "int main() { return 0; }\n",
        },
    )
    assert _test_fact(paths, CPP.suite_files, tmp_path) == (root, 3)


# Negative controls: when the sources cannot be told apart, no size is stated at all - never the
# directory's file count, which is the wrong number this fix replaces.


def _states_no_size(paths: list[str], rule: SuiteFileRule | None, root: Path | None) -> None:
    (tests,) = asset_facts(paths, suite_files=rule, root=root)
    detail = tests.evidence[-1].detail or ""
    assert RENDERER_COUNT.match(detail) is None, detail
    assert detail.startswith("test suite;")
    assert all(e.path.startswith("tests/") for e in tests.evidence)


def test_an_ecosystem_with_no_suite_rule_states_no_size() -> None:
    _states_no_size(["tests/a.x", "tests/b.x"], None, None)


def test_a_marker_rule_without_a_checkout_states_no_size() -> None:
    _states_no_size(["tests/AThing.cs", "tests/BThing.cs"], NET.suite_files, None)


def test_a_candidate_that_will_not_read_states_no_size(tmp_path: Path) -> None:
    paths = _write(tmp_path, {"tests/AThing.cs": FACT_TEST})
    paths.append("tests/Missing.cs")  # in the tree listing, absent on disk
    _states_no_size(paths, NET.suite_files, tmp_path)


def test_a_suite_with_no_recognisable_test_states_no_size(tmp_path: Path) -> None:
    paths = _write(tmp_path, {"tests/Helper.cs": "class Helper { }\n"})
    _states_no_size(paths, NET.suite_files, tmp_path)


def test_a_suite_too_large_to_read_states_no_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _write(tmp_path, {f"tests/T{i}.cs": FACT_TEST for i in range(3)})
    monkeypatch.setattr(assets, "_MAX_SUITE_FILES_READ", 2)
    _states_no_size(paths, NET.suite_files, tmp_path)
    monkeypatch.setattr(assets, "_MAX_SUITE_FILES_READ", 3)
    assert _test_fact(paths, NET.suite_files, tmp_path) == ("tests/", 3)


def test_a_test_file_too_large_to_read_states_no_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _write(tmp_path, {"tests/A.cs": FACT_TEST})
    monkeypatch.setattr(assets, "_MAX_SUITE_FILE_BYTES", 8)
    _states_no_size(paths, NET.suite_files, tmp_path)


def test_other_asset_directories_keep_their_plain_file_count() -> None:
    facts = {f.id: f for f in asset_facts(["docs/a.md", "docs/b.md", "examples/x.py"])}
    assert facts["build_test_asset:docs"].evidence[-1].detail == "2 files; documentation directory"
    assert facts["build_test_asset:examples"].evidence[-1].detail == "1 files; example directory"


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
