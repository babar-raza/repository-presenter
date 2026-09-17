"""The Python verifier installs the package into a fresh venv and runs each candidate alone."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.examples.verify import example_facts
from repository_presenter.components.readme.extractors.platforms import python_examples
from repository_presenter.components.readme.extractors.platforms.python_examples import (
    stage_fixtures,
    verify_python_examples,
)
from repository_presenter.core.examples import ExampleCandidate
from repository_presenter.core.execution import ExecutionResult


def _package(root: Path) -> list[str]:
    (root / "widget").mkdir()
    (root / "widget" / "__init__.py").write_text(
        "def greet(name):\n    return f'hello {name}'\n\n"
        "def load(path):\n    with open(path, encoding='utf-8') as f:\n        return f.read()\n",
        encoding="utf-8",
    )
    (root / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="widget", version="1.0", packages=["widget"])\n',
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "sample.obj").write_text("v 0 0 0\n", encoding="utf-8")
    (root / "tests" / "big.stl").write_text("solid big\nendsolid\n", encoding="utf-8")
    (root / "tests" / "small.stl").write_text("solid\n", encoding="utf-8")
    return [
        "setup.py",
        "widget/__init__.py",
        "tests/sample.obj",
        "tests/big.stl",
        "tests/small.stl",
    ]


def _candidate(ordinal: int, code: str) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal, "python", code, "README.md", 1, 3, f"inherited_unit:{ordinal:03d}.code_block"
    )


def test_fixture_staging_prefers_a_same_name_file_then_the_smallest_same_suffix(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    workspace = tmp_path / "run"
    workspace.mkdir()
    code = (
        'a = open("sample.obj")\nb = open("mesh.stl")\n'
        'c = open("missing.xyz")\nd = "not/a/file.obj"\n'
    )
    bindings = stage_fixtures(code, root, tree, workspace)
    assert [(b.literal, b.source_path) for b in bindings] == [
        ("sample.obj", "tests/sample.obj"),
        ("mesh.stl", "tests/small.stl"),
    ]
    assert (workspace / "sample.obj").read_text(encoding="utf-8") == "v 0 0 0\n"
    assert not (workspace / "missing.xyz").exists()


def test_a_fixture_may_come_from_an_executed_examples_output(tmp_path: Path) -> None:
    """A repository that ships no sample data can still verify an example that reads one.

    Measured on the canary on 2026-09-05 (section 27.2 RC6): five of twelve examples ended
    NEEDS_INPUT on a model file, and the repository carries no model file of any kind - 751
    .py, 9 .md, 4 .txt, one .yml, and nothing else. Two executed examples do write one.
    """
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    workspace = tmp_path / "run"
    workspace.mkdir()
    # The tree has a .obj, so the repository's own file wins and the pool is not consulted.
    made = tmp_path / "made.obj"
    made.write_text("v 9 9 9\n", encoding="utf-8")
    pool = {".obj": [(2, made)], ".gltf": [(4, made)]}
    bindings = stage_fixtures('a = open("sample.obj")', root, tree, workspace, pool)
    assert [(b.literal, b.source_path, b.produced_by) for b in bindings] == [
        ("sample.obj", "tests/sample.obj", None)
    ]
    # An extension the tree never had is served by the earliest example that wrote one, and
    # the binding names it, so the receipt says whose output this is.
    other = tmp_path / "run2"
    other.mkdir()
    bindings = stage_fixtures('a = open("model.gltf")', root, tree, other, pool)
    assert [(b.literal, b.source_path, b.produced_by) for b in bindings] == [
        ("model.gltf", "made.obj", 4)
    ]
    assert (other / "model.gltf").read_text(encoding="utf-8")
    # Without a pool the same example simply goes unserved, as it did before.
    bare = tmp_path / "run3"
    bare.mkdir()
    assert stage_fixtures('a = open("model.gltf")', root, tree, bare) == []


def test_every_candidate_gets_an_honest_receipt(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    candidates = [
        _candidate(1, "from widget import greet\nprint(greet('world'))\n"),
        _candidate(2, "from widget import missing_symbol\n"),
        _candidate(3, "from widget import load\nprint(load('sample.obj'))\n"),
        _candidate(4, "from widget import load\nprint(load('absent.fbx'))\n"),
        _candidate(5, "import time\ntime.sleep(300)\n"),
    ]
    import repository_presenter.components.readme.extractors.platforms.python_examples as module

    original = module.EXAMPLE_TIMEOUT_SECONDS
    module.EXAMPLE_TIMEOUT_SECONDS = 3.0
    try:
        receipts = verify_python_examples(root, tree, candidates, tmp_path / "verify")
    finally:
        module.EXAMPLE_TIMEOUT_SECONDS = original

    by_ordinal = {r.ordinal: r for r in receipts}
    assert by_ordinal[1].outcome == "EXECUTED"
    assert by_ordinal[1].stdout.strip() == "hello world"
    assert by_ordinal[2].outcome == "FAILED"
    assert by_ordinal[2].detail == "ImportError"
    assert by_ordinal[3].outcome == "EXECUTED"
    assert [(b.literal, b.source_path) for b in by_ordinal[3].fixtures] == [
        ("sample.obj", "tests/sample.obj")
    ]
    assert by_ordinal[4].outcome == "NEEDS_INPUT"
    assert by_ordinal[4].fixtures == ()
    assert by_ordinal[5].outcome == "TIMED_OUT"
    assert by_ordinal[5].return_code == 124
    assert not (tmp_path / "verify" / "example_001" / "__pycache__").exists()


def test_no_candidates_means_no_venv_and_no_receipts(tmp_path: Path) -> None:
    assert verify_python_examples(tmp_path, [], [], tmp_path / "verify") == []
    assert not (tmp_path / "verify").exists()


def test_an_uninstallable_package_leaves_every_candidate_unverified(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "setup.py").write_text("raise SystemExit('no build for you')\n", encoding="utf-8")
    receipts = verify_python_examples(
        root, ["setup.py"], [_candidate(1, "print(1)\n")], tmp_path / "verify"
    )
    assert [(r.ordinal, r.outcome) for r in receipts] == [(1, "NOT_VERIFIED")]
    assert receipts[0].detail.startswith("package install failed")


def test_bootstrap_and_install_are_redirected_into_the_workspace_like_the_example_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TB-08, external review D8, 2026-09-08: bootstrap (venv creation) and install used to run
    with no ``extra_environment`` at all, so pip's own caches and config - and anything a build
    script reads via HOME - fell through to the developer's real account instead of the
    disposable workspace, unlike the later per-example run, which was already redirected. A
    host-file access attempt during install is now contained to the redirected profile."""
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    seen: list[dict[str, object]] = []

    def record(argv: list[str], **kwargs: object) -> ExecutionResult:
        seen.append(kwargs)
        return ExecutionResult(
            argv=tuple(argv),
            return_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            environment_names=(),
        )

    monkeypatch.setattr(python_examples, "execute", record)
    verify_python_examples(root, tree, [_candidate(1, "pass\n")], tmp_path / "run")

    assert len(seen) >= 2, seen
    bootstrap_kwargs, install_kwargs = seen[0], seen[1]
    for kwargs in (bootstrap_kwargs, install_kwargs):
        overlay = kwargs.get("extra_environment")
        assert isinstance(overlay, dict) and overlay, kwargs
        home = Path(str(overlay["HOME"]))
        assert home.is_relative_to(tmp_path / "run")
        assert home != Path.home()


def test_a_toolchain_that_cannot_be_provisioned_leaves_every_example_unresolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A machine that cannot build is not evidence that the code is wrong.

    RESEARCH_AND_GUIDELINES.md section 29.6 E5: a toolchain failure is UNRESOLVED, never
    CONTRADICTED - the difference between "we could not check" and "we checked and it is false",
    which is the whole basis of an honest disposition.
    """
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    candidates = [_candidate(1, "import widget\n"), _candidate(2, "boom(\n")]

    def refuse(argv: list[str], **kwargs: object) -> ExecutionResult:
        return ExecutionResult(
            argv=tuple(argv),
            return_code=1,
            stdout="",
            stderr="python: No module named venv",
            timed_out=False,
            environment_names=(),
        )

    monkeypatch.setattr(python_examples, "execute", refuse)
    receipts = verify_python_examples(root, tree, candidates, tmp_path / "run")
    assert [r.outcome for r in receipts] == ["NOT_VERIFIED", "NOT_VERIFIED"]
    assert all("venv creation failed" in (r.detail or "") for r in receipts)
    facts = example_facts(candidates, receipts, "examples.json")
    assert {f.polarity for f in facts} == {"UNRESOLVED"}
    assert all(f.confidence == 0.5 for f in facts)


def test_a_fuzzing_corpus_never_stands_in_as_an_examples_input(tmp_path: Path) -> None:
    """Sample data's opposite is not sample data.

    A fuzzing seed is malformed by design and is the smallest file of its type in the tree for
    exactly that reason, so the smallest-same-suffix rule chose one every time. Measured
    2026-09-07 on Aspose.PDF for Python: `fuzz/corpus/cos/truncated.pdf` (35 bytes) was staged
    as `input.pdf` for eight of thirteen examples, every one of which then raised
    `PdfParseException`, while `tests/fixtures_4pages.pdf` (707 bytes) sat unused.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "fuzz" / "corpus" / "cos").mkdir(parents=True)
    (root / "fuzz" / "corpus" / "cos" / "truncated.pdf").write_text("%PDF", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "fixtures_4pages.pdf").write_text("%PDF-1.7 whole\n", encoding="utf-8")
    tree = ["fuzz/corpus/cos/truncated.pdf", "tests/fixtures_4pages.pdf"]
    workspace = tmp_path / "run"
    workspace.mkdir()
    bindings = stage_fixtures('open("input.pdf")\n', root, tree, workspace)
    assert [(b.literal, b.source_path) for b in bindings] == [
        ("input.pdf", "tests/fixtures_4pages.pdf")
    ]


def test_a_corpus_file_is_not_taken_even_when_the_literal_names_it(tmp_path: Path) -> None:
    """The by-name rule reaches the same pool as the by-extension one, or the fix is half done."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "corpus").mkdir()
    (root / "corpus" / "input.pdf").write_text("%PDF", encoding="utf-8")
    workspace = tmp_path / "run"
    workspace.mkdir()
    assert stage_fixtures('open("input.pdf")\n', root, ["corpus/input.pdf"], workspace) == []
    assert not (workspace / "input.pdf").exists()


def test_a_package_that_will_not_build_still_runs_its_examples_from_source(
    tmp_path: Path,
) -> None:
    """A broken wheel build is not evidence that the repository's code is wrong.

    Measured 2026-09-07 on Aspose.BarCode for Python, reproducibly on a clean tree: setuptools'
    own `install_egg_info` step fails, so every example read NOT_VERIFIED and the Quick Start
    row lost its evidence - for a pure-Python package that imports fine from `src/`.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src" / "widget").mkdir(parents=True)
    (root / "src" / "widget" / "__init__.py").write_text(
        "VALUE = 'from source'\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "no.such.backend"\n',
        encoding="utf-8",
    )
    tree = ["pyproject.toml", "src/widget/__init__.py"]
    receipts = verify_python_examples(
        root,
        tree,
        [_candidate(1, "import widget\nprint(widget.VALUE)\n")],
        tmp_path / "run",
    )
    assert [(r.ordinal, r.outcome) for r in receipts] == [(1, "EXECUTED")]
    assert "from source" in receipts[0].stdout
    assert "ran against the repository source tree" in (receipts[0].detail or "")
    # TB-01, external review D1, 2026-09-08: the example running proves the code, never the
    # distribution - build_verified must be False so extract.py never promotes the registry
    # install command from this receipt as "verified against this revision".
    assert receipts[0].build_verified is False
    # RESEARCH_LANE_E.md's documented-PYTHONPATH-source-install observation: the directories
    # `_source_roots` found - the `src` layout's own parent, nearest first, then the checkout
    # root itself for a namespace package's sake - travel on the receipt so extract.py's weaker
    # source_checkout tier can name them without recomputing anything from the tree itself.
    assert receipts[0].source_roots == ("src", ".")


def test_a_genuinely_successful_install_still_marks_the_receipt_verified(tmp_path: Path) -> None:
    """The no-regression case: an ordinary successful install keeps build_verified True."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "widget.py").write_text("VALUE = 'installed'\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
        '[project]\nname = "widget"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    tree = ["pyproject.toml", "widget.py"]
    receipts = verify_python_examples(
        root, tree, [_candidate(1, "import widget\nprint(widget.VALUE)\n")], tmp_path / "run"
    )
    assert [(r.ordinal, r.outcome) for r in receipts] == [(1, "EXECUTED")]
    assert receipts[0].build_verified is True
    # A genuine install never touches the fallback path, so it names no source roots at all -
    # extract.py's weaker source_checkout tier must never fire for a receipt like this one.
    assert receipts[0].source_roots == ()


def test_the_source_fallback_installs_the_dependencies_the_manifest_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source tree with none of what it imports is a library nobody asked about.

    Measured 2026-09-07 on Aspose.BarCode for Python: with the build broken, all six examples
    ran from source and all six raised `ModuleNotFoundError: No module named 'PIL'` - the
    failed build had carried the dependency resolution with it.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src" / "widget").mkdir(parents=True)
    (root / "src" / "widget" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "no.such.backend"\n'
        '[project]\nname = "widget"\nversion = "1.0"\ndependencies = ["pillow>=10", "lxml"]\n',
        encoding="utf-8",
    )
    seen: list[list[str]] = []

    def record(argv: list[str], **kwargs: object) -> ExecutionResult:
        seen.append(list(argv))
        failed = "install" in argv and str(root) in argv
        return ExecutionResult(
            argv=tuple(argv),
            return_code=1 if failed else 0,
            stdout="",
            stderr="no build for you" if failed else "",
            timed_out=False,
            environment_names=(),
        )

    monkeypatch.setattr(python_examples, "execute", record)
    verify_python_examples(
        root,
        ["pyproject.toml", "src/widget/__init__.py"],
        [_candidate(1, "pass\n")],
        tmp_path / "run",
    )
    installs = [argv for argv in seen if "install" in argv]
    assert any("pillow>=10" in argv and "lxml" in argv for argv in installs), installs
    assert not any(str(root) in argv for argv in installs[1:])


def test_a_tree_with_no_importable_package_stays_unverified_when_the_build_fails(
    tmp_path: Path,
) -> None:
    """The source fallback never invents a checkable repository out of one that has no code."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "setup.py").write_text("raise SystemExit('no build for you')\n", encoding="utf-8")
    receipts = verify_python_examples(
        root, ["setup.py"], [_candidate(1, "print(1)\n")], tmp_path / "verify"
    )
    assert [(r.ordinal, r.outcome) for r in receipts] == [(1, "NOT_VERIFIED")]
    assert (receipts[0].detail or "").startswith("package install failed")


def test_the_missing_path_is_read_off_the_examples_own_failure(tmp_path: Path) -> None:
    """The traceback names what the example actually opened; the literal scan cannot."""
    run_dir = tmp_path / "example_001"
    run_dir.mkdir()
    trace = (
        'Traceback (most recent call last):\n  File "example.py", line 3, in <module>\n'
        "FileNotFoundError: [Errno 2] No such file or directory: 'sample.obj'\n"
    )
    assert python_examples.missing_input_path(trace, run_dir) == "sample.obj"
    # A path the example built with a directory, spelled with either separator.
    nested = "FileNotFoundError: [Errno 2] No such file or directory: 'fonts\\\\arial.ttf'\n"
    assert python_examples.missing_input_path(nested, run_dir) == "fonts/arial.ttf"
    # An absolute path inside the run directory is the same file, relative to it.
    absolute = (
        "FileNotFoundError: [Errno 2] No such file or directory: "
        f"{str(run_dir / 'data' / 'in.cff')!r}\n"
    )
    assert python_examples.missing_input_path(absolute, run_dir) == "data/in.cff"
    # Outside the run directory, or climbing out of it, is never staged; nor is a non-file error.
    outside = "FileNotFoundError: [Errno 2] No such file or directory: '/etc/fonts/x.ttf'\n"
    assert python_examples.missing_input_path(outside, run_dir) is None
    assert python_examples.missing_input_path("...directory: '../x.ttf'\n", run_dir) is None
    assert python_examples.missing_input_path("ValueError: bad input\n", run_dir) is None


def test_an_example_that_builds_the_path_it_opens_is_served_from_its_own_failure(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 53 (Aspose.Font-FOSS-for-Python @ c4c453b8, G3 second pass): all eight
    candidates ended NEEDS_INPUT - three spell no file literal at all and build the path at run
    time, five name one literal and then open a second input they never spelled - while the tree
    carries 107 .ttf, 46 .fntdata, 21 .cff, 20 .pfb and 13 .otf. A matching problem, not a
    scarcity one: the example's own FileNotFoundError names the path, so that path is staged
    (same name, then same suffix, then the produced pool - stage_fixtures' own order) and the
    example gets exactly one more attempt, the fold-not-reject shape the NEEDS_INPUT retry
    already has."""
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    loader = "from widget import load\n"
    candidates = [
        # Builds the name at run time: no literal for the scan, the failure names sample.obj.
        _candidate(1, loader + "name = 'sam' + 'ple'\nprint(load(name + '.obj'))\n"),
        # Names one literal (staged first time round) and then opens a second, unspelled input.
        _candidate(2, loader + "load('sample.obj')\nprint(load('mesh' + '.stl'))\n"),
        # Nothing in the tree or the pool can serve it: one attempt, honestly NEEDS_INPUT.
        _candidate(3, loader + "print(load('no' + 'where.xyz'))\n"),
    ]
    receipts = verify_python_examples(root, tree, candidates, tmp_path / "verify")
    by_ordinal = {receipt.ordinal: receipt for receipt in receipts}
    assert by_ordinal[1].outcome == "EXECUTED"
    assert [(b.literal, b.source_path) for b in by_ordinal[1].fixtures] == [
        ("sample.obj", "tests/sample.obj")
    ]
    assert by_ordinal[2].outcome == "EXECUTED"
    assert [(b.literal, b.source_path) for b in by_ordinal[2].fixtures] == [
        ("sample.obj", "tests/sample.obj"),
        ("mesh.stl", "tests/small.stl"),
    ]
    assert by_ordinal[3].outcome == "NEEDS_INPUT"
    assert by_ordinal[3].fixtures == ()


def test_the_missing_module_is_read_off_the_examples_own_failure() -> None:
    """The traceback names the module `import` could not find; a dotted submodule names its own
    top-level package, the one an extra's requirement actually installs."""
    trace = (
        'Traceback (most recent call last):\n  File "example.py", line 1, in <module>\n'
        "    from reportlab.lib.utils import ImageReader\n"
        "ModuleNotFoundError: No module named 'reportlab'\n"
    )
    assert python_examples.missing_module_name(trace) == "reportlab"
    submodule = "ModuleNotFoundError: No module named 'widget.saving.pdf_writer'\n"
    assert python_examples.missing_module_name(submodule) == "widget"
    assert python_examples.missing_module_name("ValueError: bad input\n") is None


def test_a_module_not_found_failure_is_retried_after_installing_its_declared_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 70 (Aspose.Note-FOSS-for-Python): `pdf_writer.py` imports `reportlab`,
    a declared `[project.optional-dependencies] pdf` extra `_declared_dependencies` never installs
    (it reads `project.dependencies` only) - so the example fails before proving PDF export and
    `format:output.pdf` goes UNRESOLVED for a reason unrelated to whether the format is genuinely
    supported. Retried once, after installing exactly the extra that names the missing module -
    never the whole extras set (`dev` here is never touched), never a second retry."""
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nversion = "1.0"\n'
        '[project.optional-dependencies]\npdf = ["reportlab>=3.6"]\ndev = ["pytest"]\n',
        encoding="utf-8",
    )
    tree.append("pyproject.toml")
    installs: list[list[str]] = []
    run_count = {"n": 0}

    def fake(argv: list[str], **kwargs: object) -> ExecutionResult:
        text = [str(a) for a in argv]
        if "install" in text:
            installs.append(text)
            return ExecutionResult(tuple(argv), 0, "", "", False, ())
        if text and text[-1].endswith("example.py"):
            run_count["n"] += 1
            if run_count["n"] == 1:
                return ExecutionResult(
                    tuple(argv),
                    1,
                    "",
                    "Traceback (most recent call last):\n"
                    "ModuleNotFoundError: No module named 'reportlab'\n",
                    False,
                    (),
                )
            return ExecutionResult(tuple(argv), 0, "ok\n", "", False, ())
        return ExecutionResult(tuple(argv), 0, "", "", False, ())

    monkeypatch.setattr(python_examples, "execute", fake)
    receipts = verify_python_examples(
        root, tree, [_candidate(1, "import reportlab\nprint('ok')\n")], tmp_path / "run"
    )
    assert len(receipts) == 1
    assert receipts[0].outcome == "EXECUTED"
    assert receipts[0].stdout.strip() == "ok"
    assert run_count["n"] == 2  # exactly one retry, never a third run
    assert "retried after installing declared extra providing 'reportlab'" in receipts[0].detail
    extra_installs = [argv for argv in installs if "reportlab>=3.6" in argv]
    assert len(extra_installs) == 1  # installed once, not once per example
    assert not any("pytest" in argv for argv in installs)  # the dev extra is never touched


def test_a_module_not_found_failure_with_no_matching_extra_stays_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A module no declared extra names (a genuinely missing or misspelled import) is left FAILED
    exactly as before this item - never a guess, never a second retry attempt."""
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nversion = "1.0"\n'
        '[project.optional-dependencies]\npdf = ["reportlab>=3.6"]\n',
        encoding="utf-8",
    )
    tree.append("pyproject.toml")
    run_count = {"n": 0}

    def fake(argv: list[str], **kwargs: object) -> ExecutionResult:
        text = [str(a) for a in argv]
        if "install" in text:
            return ExecutionResult(tuple(argv), 0, "", "", False, ())
        if text and text[-1].endswith("example.py"):
            run_count["n"] += 1
            return ExecutionResult(
                tuple(argv),
                1,
                "",
                "ModuleNotFoundError: No module named 'nosuchpackage'\n",
                False,
                (),
            )
        return ExecutionResult(tuple(argv), 0, "", "", False, ())

    monkeypatch.setattr(python_examples, "execute", fake)
    receipts = verify_python_examples(
        root, tree, [_candidate(1, "import nosuchpackage\n")], tmp_path / "run"
    )
    assert [(r.ordinal, r.outcome) for r in receipts] == [(1, "FAILED")]
    assert run_count["n"] == 1  # never retried


def _fake_pinned(root: Path, name: str, version: str) -> Path:
    """A uv-shaped pinned venv: pyvenv.cfg naming its version, an interpreter file beside it."""
    venv = root / name
    scripts = venv / ("Scripts" if sys.platform == "win32" else "bin")
    scripts.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text(
        f"home = /x\nimplementation = CPython\nuv = 0.12.9\nversion_info = {version}\n",
        encoding="utf-8",
    )
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    python.write_bytes(b"")
    return python


def test_the_interpreter_is_chosen_by_the_manifests_requires_python(tmp_path: Path) -> None:
    """G4-W17 arrival item 52 (Aspose.Words-FOSS-for-Python @ 2d2efee2, G3 second pass): the
    verifier built its venv from sys.executable (3.13.2) while the manifest declares
    requires-python '>=3.10,<3.13', so pip refused before any example ran and all twelve read
    NOT_VERIFIED. The presenter's own interpreter is used whenever the declaration admits it;
    otherwise the highest pinned toolchain under runs/verify that does; otherwise none - and
    the caller says so rather than running the wrong Python."""
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    older = _fake_pinned(tmp_path, "py309", "3.9")
    newer_pinned = _fake_pinned(tmp_path, "py310", "3.10")
    _fake_pinned(tmp_path, "py-broken", "not.a.version")
    (tmp_path / "not-a-venv").mkdir()
    assert python_examples.pinned_interpreters(tmp_path) == [
        ("3.9", older),
        ("3.10", newer_pinned),
    ]
    # No declaration, or one the presenter satisfies: the presenter itself, unlabeled.
    presenter = python_examples.select_interpreter("", tmp_path)
    assert presenter is not None and presenter.executable == Path(sys.executable)
    assert presenter.label == ""
    assert python_examples.select_interpreter(f">={running}", tmp_path) == presenter
    # A cap below the presenter: the highest pinned interpreter that satisfies it.
    capped = python_examples.select_interpreter(f">=3.8,<{running}", tmp_path)
    assert capped is not None
    assert (capped.executable, capped.version, capped.label) == (newer_pinned, "3.10", "py310")
    # Nothing satisfies: None, so the caller records the honest reason. (`>3.13` would still admit
    # 3.13.2 - PEP 440 compares the full version - so the floor is the next minor.)
    above = f">={sys.version_info.major}.{sys.version_info.minor + 1}"
    assert python_examples.select_interpreter(above, tmp_path) is None
    # A declaration nobody can parse constrains nothing; pip would say so itself.
    assert python_examples.select_interpreter("not a specifier", tmp_path) == presenter


def test_a_repository_capped_below_the_presenters_python_runs_under_a_pinned_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: a manifest whose requires-python excludes the running interpreter. Where a
    pinned toolchain satisfies it (RP_PYTHON_TOOLCHAINS, or the workspace's own runs/verify
    parent), the venv is built from that interpreter, the install runs under it, and each
    receipt says which Python verified it; where none does, every receipt is NOT_VERIFIED
    naming the declaration - never CONTRADICTED, never the wrong interpreter."""
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    root = tmp_path / "repo"
    root.mkdir()
    tree = _package(root)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nversion = "1.0"\n'
        f'requires-python = ">=3.8,<{running}"\n'
        '[tool.setuptools]\npackages = ["widget"]\n',
        encoding="utf-8",
    )
    tree.append("pyproject.toml")
    toolchains = Path(os.environ.get("RP_PYTHON_TOOLCHAINS", tmp_path / "no-toolchains"))
    monkeypatch.setenv("RP_PYTHON_TOOLCHAINS", str(toolchains))
    satisfying = [
        (version, path)
        for version, path in python_examples.pinned_interpreters(toolchains)
        if python_examples.select_interpreter(f">=3.8,<{running}", toolchains) is not None
        and python_examples.select_interpreter(f">=3.8,<{running}", toolchains).version == version
    ]
    receipts = verify_python_examples(
        root, tree, [_candidate(1, "from widget import greet\nprint(greet('x'))\n")], tmp_path / "v"
    )
    assert len(receipts) == 1
    if satisfying:
        version, _ = satisfying[0]
        assert receipts[0].outcome == "EXECUTED", receipts[0].detail
        assert f"ran under Python {version} (" in receipts[0].detail
        assert f"requires-python '>=3.8,<{running}'" in receipts[0].detail
    else:
        assert receipts[0].outcome == "NOT_VERIFIED"
        assert receipts[0].detail.startswith(
            f"no interpreter satisfies requires-python '>=3.8,<{running}'"
        )
