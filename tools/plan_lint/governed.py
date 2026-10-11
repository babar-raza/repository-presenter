"""The governed-source set, read from the one place that owns it.

``tests/test_version_bump_discipline.py`` holds ``GOVERNED``: the sources whose edit must move a
version constant. This module *parses* that file (``ast``, no import of the product, pytest or git)
instead of keeping a second copy, so a source added there is a governed path for the plan lint and
for ``tools/workflow_rehearsal/no_bump_check.py`` in the same commit. Fail closed: a file that
cannot be read, or that yields no path, raises ``GovernedSetError`` and never an empty set.
"""

from __future__ import annotations

import ast
from pathlib import Path

DISCIPLINE_TEST = "tests/test_version_bump_discipline.py"
ROOT = Path(__file__).resolve().parents[2]


class GovernedSetError(RuntimeError):
    """The governed set could not be read from the discipline test."""


def _path_of(call: ast.Call) -> str | None:
    """The ``path`` of one ``GovernedSource(component, path, constants)`` literal."""
    node: ast.expr | None = call.args[1] if len(call.args) > 1 else None
    for keyword in call.keywords:
        if keyword.arg == "path":
            node = keyword.value
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def parse_governed_files(source: str) -> tuple[str, ...]:
    """Every path in the module-level ``GOVERNED`` tuple of ``source`` (the discipline test)."""
    tree = ast.parse(source)
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        if not any(isinstance(t, ast.Name) and t.id == "GOVERNED" for t in targets):
            continue
        if not isinstance(value, ast.Tuple | ast.List):
            break
        paths = [
            path
            for element in value.elts
            if isinstance(element, ast.Call)
            for path in [_path_of(element)]
            if path
        ]
        if paths and len(paths) == len(value.elts):
            return tuple(paths)
        break
    raise GovernedSetError(
        f"no readable GOVERNED = (GovernedSource(...), ...) in {DISCIPLINE_TEST}"
    )


def governed_files(root: Path = ROOT) -> tuple[str, ...]:
    """The governed sources, repository-relative with forward slashes."""
    path = root / DISCIPLINE_TEST
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise GovernedSetError(f"cannot read {path}: {error}") from error
    return parse_governed_files(text)
