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
import os
import re
import shutil
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.ecosystems import PYTHON
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt, FixtureBinding
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

# The spec owns the numbers; these names keep the module readable and the failure message
# honest about what it waited for (RESEARCH_AND_GUIDELINES.md section 29.6 E5).
EXAMPLE_TIMEOUT_SECONDS = PYTHON.example_timeout_seconds
INSTALL_TIMEOUT_SECONDS = PYTHON.install_timeout_seconds
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

# A fuzzing corpus is sample data's opposite: every file in it exists to be malformed, and they
# are the smallest files of their type in the tree precisely because a crash seed is truncated -
# so the by-extension fallback below, which takes the smallest match, picked one every time.
# Measured 2026-09-07 on Aspose.PDF for Python: `fuzz/corpus/cos/truncated.pdf` (35 bytes) was
# staged as `input.pdf` for eight of thirteen examples, each of which then raised
# `PdfParseException` and was recorded FAILED, while `tests/fixtures_4pages.pdf` (707 bytes), a
# valid document the repository ships for exactly this purpose, sat unused. These are the
# directory names libFuzzer, AFL and Atheris write by convention.
_NEGATIVE_ASSET_PARTS = frozenset({"fuzz", "fuzzing", "corpus", "corpora", "crashes", "seeds"})


def _representative(path: str) -> bool:
    """Whether a repository file may stand in as an example's input at all."""
    return not any(part.lower() in _NEGATIVE_ASSET_PARTS for part in Path(path).parts)


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
    representative = [path for path in tree_paths if _representative(path)]
    by_name = {Path(path).name.lower(): path for path in sorted(representative)}
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
                (path for path in representative if Path(path).suffix.lower() == suffix),
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
    import_roots = [site]
    source_note = ""
    if install.return_code != 0:
        # A package that will not build is not a repository whose code does not work, and the
        # two were being conflated: every example went NOT_VERIFIED, the Quick Start row lost
        # its evidence, and the whole candidate was blocked by its packaging. Measured
        # 2026-09-07 on Aspose.BarCode for Python, reproducibly on a clean tree - setuptools'
        # own `install_egg_info` step fails building the wheel - while the package itself is
        # pure Python and imports fine from `src/`. So the examples run against the
        # repository's own source tree instead, and every receipt says so: the run proves the
        # code, never the distribution, exactly as a verified source build is admitted as a
        # *source* install kind and never as a registry command (section 27.9 item (0)/(24)).
        fallback = _source_roots(root, tree_paths)
        if not fallback:
            return _all_not_verified(candidates, f"package install failed: {_clip(install.stderr)}")
        # The build carried the dependency resolution with it, so the source tree alone is a
        # library with none of what it imports: every Aspose.BarCode example then failed with
        # `ModuleNotFoundError: No module named 'PIL'` (2026-09-07), an honest failure of a
        # question nobody asked. The manifest already declares them, so install those and keep
        # the repository's own packages ahead of the installed set on the path.
        requirements = _declared_dependencies(root)
        if requirements:
            execute(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--quiet",
                    "--target",
                    str(site),
                    *requirements,
                ],
                workspace=workspace,
                timeout_seconds=INSTALL_TIMEOUT_SECONDS,
            )
        import_roots = [*fallback, site]
        source_note = "ran against the repository source tree; the package would not build"

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
            # The example is the repository's own code: it runs with its caches and its
            # home redirected into the run directory, so it can neither read state a
            # previous run left in the developer's account nor leave any there
            # (RESEARCH_AND_GUIDELINES.md section 29.6 E5). The install above keeps the
            # shared package cache: no repository code runs there that this does not.
            extra_environment={
                **profile_environment(run_dir),
                "PYTHONPATH": os.pathsep.join(str(path) for path in import_roots),
                "PYTHONNOUSERSITE": "1",
            },
        )
        outcome, detail = _classify(result, candidate.code)
        if source_note:
            detail = f"{detail}; {source_note}"
        receipt = ExampleReceipt(
            ordinal=candidate.ordinal,
            outcome=outcome,  # type: ignore[arg-type]
            return_code=result.return_code,
            stdout=_redact(_clip(result.stdout), workspace),
            stderr=_redact(_clip(result.stderr), workspace),
            detail=detail,
            fixtures=tuple(fixtures),
            # `source_note` is set only when the real package install failed and this example ran
            # against the repository's own source tree instead (TB-01, external review D1,
            # 2026-09-08): the example running proves the code, never the distribution, so an
            # EXECUTED outcome here must not promote the registry install command as verified.
            build_verified=not source_note,
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


def _declared_dependencies(root: Path) -> list[str]:
    """The runtime requirements the manifest states, read without building anything."""
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return []
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
    except tomllib.TOMLDecodeError:
        return []
    project = data.get("project")
    declared = project.get("dependencies", []) if isinstance(project, dict) else []
    return [item for item in declared if isinstance(item, str) and item.strip()]


def _source_roots(root: Path, tree_paths: Sequence[str]) -> list[Path]:
    """Directories an interpreter can import the repository's own packages from, uninstalled.

    A top-level package is one whose parent directory is not itself a package. Every directory
    from that parent up to the repository root is a path entry, nearest first, so a ``src``
    layout (``src/aspose_barcode_foss``) and a namespace one (``aspose/threed``, with no
    ``aspose/__init__.py``, imported as ``aspose.threed``) are both importable. A tree with no
    package at all yields nothing, and the caller records every candidate NOT_VERIFIED as before
    - a repository whose code cannot be imported has not been checked, and is never guessed at.
    """
    packages = {
        Path(path).parent.as_posix() for path in tree_paths if Path(path).name == "__init__.py"
    }
    tops = {package for package in packages if Path(package).parent.as_posix() not in packages}
    ordered: list[Path] = []
    for package in sorted(tops):
        current = (root / package).parent
        while True:
            if current not in ordered and current.is_dir():
                ordered.append(current)
            if current == root or root not in current.parents:
                break
            current = current.parent
    return ordered


def _all_not_verified(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
    return [
        ExampleReceipt(candidate.ordinal, "NOT_VERIFIED", None, "", "", detail)
        for candidate in candidates
    ]
