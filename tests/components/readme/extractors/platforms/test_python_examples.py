"""The Python verifier installs the package into a fresh venv and runs each candidate alone."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms.python_examples import (
    stage_fixtures,
    verify_python_examples,
)
from repository_presenter.core.examples import ExampleCandidate


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
