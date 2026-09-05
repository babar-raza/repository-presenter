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


# The receipt is sealed in the bundle, so it carries nothing that depends on where the run
# happened: a traceback names the disposable workspace by absolute path, and two machines - or
# two projects on one machine - would then seal different bytes for the same verification
# (docs/README_CONTRACT.md section 7; RESEARCH_AND_GUIDELINES.md 27.2 RC4).
WORKSPACE_TOKEN = "<workspace>"


def _redact(text: str, workspace: Path) -> str:
    """The run's own absolute path replaced by a stable token, in either separator."""
    literal = str(workspace)
    return text.replace(literal, WORKSPACE_TOKEN).replace(
        literal.replace("\\", "/"), WORKSPACE_TOKEN
    )


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


# Files an executed example wrote, by lower-case suffix, in the order they were produced: an
# example that reads a model can be given one the README's own examples made, when the repository
# ships no sample data of its own (docs/RESEARCH_AND_GUIDELINES.md 27.2 RC6).
ProducedFiles = dict[str, list[tuple[int, Path]]]


def stage_fixtures(
    code: str,
    root: Path,
    tree_paths: Sequence[str],
    workspace: Path,
    produced: ProducedFiles | None = None,
) -> list[FixtureBinding]:
    """Stage a file under each file-like literal the example names.

    A repository-owned file of that name, then one of that extension, then - only when the tree
    offers neither - the earliest output an executed example of this same README wrote with that
    extension. The receipt names which, so a reader sees a fixture is the product's own output
    and not something invented here.
    """
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
        if source is not None:
            shutil.copyfile(root / source, target)
            bindings.append(FixtureBinding(literal, source))
            continue
        made = (produced or {}).get(suffix) or []
        if not made:
            continue
        ordinal, path = made[0]
        shutil.copyfile(path, target)
        bindings.append(FixtureBinding(literal, path.name, produced_by=ordinal))
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

    def run(
        candidate: ExampleCandidate, produced: ProducedFiles
    ) -> tuple[ExampleReceipt, tuple[Path, ...]]:
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir()
        script = run_dir / "example.py"
        script.write_bytes(candidate.code.encode("utf-8"))
        fixtures = stage_fixtures(candidate.code, root, tree_paths, run_dir, produced)
        before = {path.name for path in run_dir.iterdir()}
        result = execute(
            [str(python), "-s", "-X", "utf8", str(script)],
            workspace=run_dir,
            timeout_seconds=EXAMPLE_TIMEOUT_SECONDS,
            extra_environment={"PYTHONPATH": str(site), "PYTHONNOUSERSITE": "1"},
        )
        outcome, detail = _classify(result, candidate.code)
        receipt = ExampleReceipt(
            ordinal=candidate.ordinal,
            outcome=outcome,  # type: ignore[arg-type]
            return_code=result.return_code,
            stdout=_redact(_clip(result.stdout), workspace),
            stderr=_redact(_clip(result.stderr), workspace),
            detail=detail,
            fixtures=tuple(fixtures),
        )
        written = sorted(
            path for path in run_dir.iterdir() if path.is_file() and path.name not in before
        )
        return receipt, tuple(written)

    produced: ProducedFiles = {}
    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        receipt, written = run(candidate, produced)
        receipts.append(receipt)
        # Only an example that ran to completion has output worth handing on: a failed run may
        # have left a file half written, as this canary's ObjExporter does.
        if receipt.outcome == "EXECUTED":
            for path in written:
                produced.setdefault(path.suffix.lower(), []).append((candidate.ordinal, path))
    # A producer may appear after its consumer, so the examples that lacked an input are given
    # one more attempt against the complete pool. Order is the ordinals', so the pass is
    # deterministic; an example the pool cannot serve is not run again.
    by_ordinal = {candidate.ordinal: candidate for candidate in candidates}
    for index, receipt in enumerate(receipts):
        if receipt.outcome != "NEEDS_INPUT":
            continue
        candidate = by_ordinal[receipt.ordinal]
        if not _serviceable(candidate.code, root, tree_paths, produced):
            continue
        retried, _ = run(candidate, produced)
        receipts[index] = retried
    return receipts


def _serviceable(code: str, root: Path, tree_paths: Sequence[str], produced: ProducedFiles) -> bool:
    """Whether the pool now holds an extension this example opens and the tree never had."""
    suffixes = {Path(path).suffix.lower() for path in tree_paths}
    wanted = {
        Path(literal).suffix.lower()
        for literal in _string_literals(code)
        if _FILE_LITERAL.match(literal) and "/" not in literal
    }
    return any(suffix in produced for suffix in wanted - suffixes)


def _all_not_verified(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
    return [
        ExampleReceipt(candidate.ordinal, "NOT_VERIFIED", None, "", "", detail)
        for candidate in candidates
    ]
