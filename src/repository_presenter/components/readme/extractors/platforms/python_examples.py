"""Run the README's Python examples against the repository's own package, in isolation.

A disposable, pip-less virtual environment is created from the presenter's interpreter under a
short workspace, the pinned clone is installed by the presenter's pip into a target directory
that only that environment's interpreter sees, and every candidate runs as its own process under
the bounded secret-free execution boundary with a fresh working directory.
Input files an example opens are staged from repository-owned files of the same name or
extension when the tree has one, and the receipt names what was staged. An example that fails
is recorded as failed; nothing is explained away.
"""

from __future__ import annotations

import ast
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt, FixtureBinding
from repository_presenter.core.execution import ExecutionResult, execute

EXAMPLE_TIMEOUT_SECONDS = 120.0
INSTALL_TIMEOUT_SECONDS = 300.0
_MAX_OUTPUT_CHARS = 4000
_FILE_LITERAL = re.compile(r"^[\w./-]+\.[A-Za-z0-9]{1,5}$")
_ERROR_LINE = re.compile(r"^(\w+(?:\.\w+)*(?:Error|Exception|Warning))(?::|$)", re.MULTILINE)


def _venv_python(venv: Path) -> Path:
    scripts = venv / ("Scripts" if sys.platform == "win32" else "bin")
    return scripts / ("python.exe" if sys.platform == "win32" else "python")


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_OUTPUT_CHARS else text[-_MAX_OUTPUT_CHARS:]


def _string_literals(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def stage_fixtures(
    code: str, root: Path, tree_paths: Sequence[str], workspace: Path
) -> list[FixtureBinding]:
    """Copy a repository-owned file under each file-like literal the example names."""
    bindings: list[FixtureBinding] = []
    by_name = {Path(path).name.lower(): path for path in sorted(tree_paths)}
    for literal in _string_literals(code):
        if not _FILE_LITERAL.match(literal) or "/" in literal:
            continue
        target = workspace / literal
        if target.exists():
            continue
        suffix = Path(literal).suffix.lower()
        source = by_name.get(literal.lower())
        if source is None:
            same_suffix = sorted(
                (path for path in tree_paths if Path(path).suffix.lower() == suffix),
                key=lambda path: ((root / path).stat().st_size, path),
            )
            source = same_suffix[0] if same_suffix else None
        if source is None:
            continue
        shutil.copyfile(root / source, target)
        bindings.append(FixtureBinding(literal, source))
    return bindings


def _classify(result: ExecutionResult, code: str) -> tuple[str, str]:
    """Outcome and detail for one run, read from the exit status and the traceback."""
    if result.timed_out:
        return "TIMED_OUT", f"no exit within {EXAMPLE_TIMEOUT_SECONDS:g}s"
    if result.return_code == 0:
        return "EXECUTED", "exit 0"
    error = _ERROR_LINE.findall(result.stderr)
    last = error[-1] if error else f"exit {result.return_code}"
    if last in {"FileNotFoundError", "IsADirectoryError", "PermissionError"} or (
        "No such file" in result.stderr
        and any(_FILE_LITERAL.match(s) for s in _string_literals(code))
    ):
        return "NEEDS_INPUT", f"{last}: the example opens an input the repository does not provide"
    return "FAILED", last


def verify_python_examples(
    root: Path,
    tree_paths: Sequence[str],
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
) -> list[ExampleReceipt]:
    """Install the clone into a fresh venv and run every candidate; one receipt each."""
    if not candidates:
        return []
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    venv = workspace / "venv"
    site = workspace / "site"
    bootstrap = execute(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)],
        workspace=workspace,
        timeout_seconds=INSTALL_TIMEOUT_SECONDS,
    )
    if bootstrap.return_code != 0:
        return _all_not_verified(candidates, f"venv creation failed: {_clip(bootstrap.stderr)}")
    python = _venv_python(venv)
    install = execute(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "--target",
            str(site),
            str(root),
        ],
        workspace=workspace,
        timeout_seconds=INSTALL_TIMEOUT_SECONDS,
    )
    if install.return_code != 0:
        return _all_not_verified(candidates, f"package install failed: {_clip(install.stderr)}")

    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        run_dir.mkdir()
        script = run_dir / "example.py"
        script.write_bytes(candidate.code.encode("utf-8"))
        fixtures = stage_fixtures(candidate.code, root, tree_paths, run_dir)
        result = execute(
            [str(python), "-s", "-X", "utf8", str(script)],
            workspace=run_dir,
            timeout_seconds=EXAMPLE_TIMEOUT_SECONDS,
            extra_environment={"PYTHONPATH": str(site), "PYTHONNOUSERSITE": "1"},
        )
        outcome, detail = _classify(result, candidate.code)
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(result.stdout),
                stderr=_clip(result.stderr),
                detail=detail,
                fixtures=tuple(fixtures),
            )
        )
    return receipts


def _all_not_verified(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
    return [
        ExampleReceipt(candidate.ordinal, "NOT_VERIFIED", None, "", "", detail)
        for candidate in candidates
    ]
