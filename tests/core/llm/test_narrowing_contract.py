"""Every ``Narrowing`` built anywhere accepts the four arguments ``run_job`` hands its ``ask``.

Wave 5 (2026-10-11, cut e407503a) crashed with ``ask() takes 3 positional arguments but 4 were
given`` at the third reconciliation ask: one lane widened ``Narrowing.ask`` with ``repeated`` and
updated two of the three builders, and each lane's own tests were green alone. This contract reads
the source of every ``Narrowing(...)`` construction and checks the ``ask`` it is given, so a
fourth builder (or a fifth argument) cannot be merged half-done.
"""

from __future__ import annotations

import ast
from pathlib import Path

from support import REPO_ROOT

SRC = REPO_ROOT / "src" / "repository_presenter"
ASK_ARGUMENTS = 4  # parts, content, rejection, repeated


def _positional_capacity(node: ast.Lambda | ast.FunctionDef) -> tuple[int, int]:
    """(required, accepted) positional arguments of a lambda or function definition."""
    args = node.args
    accepted = len(args.posonlyargs) + len(args.args)
    required = accepted - len(args.defaults)
    if args.vararg is not None:
        return required, 10**6
    return required, accepted


def _local_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _narrowing_builders() -> list[tuple[Path, int, str, tuple[int, int]]]:
    found: list[tuple[Path, int, str, tuple[int, int]]] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = _local_functions(tree)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Narrowing"
            ):
                continue
            ask = next((kw.value for kw in node.keywords if kw.arg == "ask"), None)
            if ask is None:
                continue
            if isinstance(ask, ast.Lambda):
                found.append((path, node.lineno, "<lambda>", _positional_capacity(ask)))
            elif isinstance(ask, ast.Name) and ask.id in functions:
                found.append((path, node.lineno, ask.id, _positional_capacity(functions[ask.id])))
    return found


def test_there_are_narrowing_builders_to_check() -> None:
    assert len(_narrowing_builders()) >= 3  # authoring_retry, reconciliation, jobs


def test_every_narrowing_ask_accepts_the_four_arguments_run_job_passes() -> None:
    bad = [
        f"{path.relative_to(REPO_ROOT)}:{line} {name} takes {required}..{accepted} positional "
        f"arguments, run_job passes {ASK_ARGUMENTS}"
        for path, line, name, (required, accepted) in _narrowing_builders()
        if not required <= ASK_ARGUMENTS <= accepted
    ]
    assert bad == []
