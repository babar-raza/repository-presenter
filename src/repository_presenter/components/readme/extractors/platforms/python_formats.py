"""Format claims of a Python example: the file extensions its statements load or save.

Read from the example's syntax tree, never from prose. A file-name or extension literal counts
only when the identifiers of the same statement carry an input verb (open, load, read, import,
parse, detect) or an output verb (save, write, export, dump), and not both. The direction is the
example's claim; whether it holds is decided by the example's verification receipt, not here.

A statement inside the body of an `if` whose test is a compile-time-constant falsy value
(`if False:`, `if 0:`) never runs, so it claims nothing; neither does a statement inside a
function definition whose own name is never loaded anywhere else in the example - it cannot be
called from anywhere in it either. Both are narrow, named dead-code exclusions, not a full
reachability analysis (TB-02, external review D2, 2026-09-08: `ast.walk` visits every node
regardless of reachability, so `if False:\\n    scene.save("never-produced.pdf")` claimed an
output format the example could never actually produce, and a `def unused(): ...` helper claimed
one no call in the example could ever reach either).
"""

from __future__ import annotations

import ast
import re
from collections import deque
from collections.abc import Iterator
from pathlib import Path

from repository_presenter.core.examples import FormatClaim, FormatDirection

_EXTENSION_LITERAL = re.compile(r"^\.[A-Za-z0-9]{1,5}$")
_FILE_LITERAL = re.compile(r"^[\w./-]+\.[A-Za-z0-9]{1,5}$")
_WORD = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")
_INPUT_WORDS = frozenset({"open", "load", "read", "import", "parse", "detect"})
_OUTPUT_WORDS = frozenset({"save", "write", "export", "dump"})
_SOURCE_SUFFIXES = frozenset({".py", ".pyc", ".pyi"})
_BODY_FIELDS = frozenset({"body", "orelse", "finalbody", "handlers", "cases"})
_FUNCTION_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _statically_false(test: ast.expr) -> bool:
    return isinstance(test, ast.Constant) and not test.value


def _referenced_names(root: ast.AST) -> frozenset[str]:
    """Every identifier loaded anywhere in the tree - a function definition's own name must be
    one of these for anything in the example to be able to call it."""
    return frozenset(
        node.id
        for node in ast.walk(root)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    )


def _non_body_children(node: ast.AST) -> Iterator[ast.AST]:
    """``node``'s own child nodes, except its ``body`` - the part a caller has decided never
    actually runs."""
    for field, value in ast.iter_fields(node):
        if field == "body":
            continue
        if isinstance(value, ast.AST):
            yield value
        elif isinstance(value, list):
            yield from (item for item in value if isinstance(item, ast.AST))


def _dead_body(node: ast.AST, referenced: frozenset[str]) -> bool:
    """Whether ``node``'s own ``body`` field never runs: an ``if`` whose test is a
    compile-time-constant falsy value, or a function definition never referenced by name
    anywhere in the tree."""
    if isinstance(node, ast.If):
        return _statically_false(node.test)
    if isinstance(node, _FUNCTION_DEFS):
        return node.name not in referenced
    return False


def _reachable_nodes(root: ast.AST) -> Iterator[ast.AST]:
    """Every node ``ast.walk`` would yield, except a dead ``body`` (``_dead_body``) - nothing
    inside one can claim a format ``ast.walk`` alone cannot tell apart from live code."""
    referenced = _referenced_names(root)
    todo: deque[ast.AST] = deque([root])
    while todo:
        node = todo.popleft()
        yield node
        if _dead_body(node, referenced):
            todo.extend(_non_body_children(node))
        else:
            todo.extend(ast.iter_child_nodes(node))


def _words(identifier: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(identifier)}


def _own_nodes(statement: ast.stmt) -> Iterator[ast.AST]:
    """Every node of a statement except those of the statements nested inside it."""
    for field, value in ast.iter_fields(statement):
        if field in _BODY_FIELDS:
            continue
        if isinstance(value, ast.AST):
            yield from ast.walk(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield from ast.walk(item)


def _extension(literal: str) -> str | None:
    if _EXTENSION_LITERAL.match(literal):
        return literal.lower()
    if _FILE_LITERAL.match(literal):
        return Path(literal).suffix.lower() or None
    return None


def format_claims(code: str) -> list[FormatClaim]:
    """Distinct (direction, extension) claims in code order; unparsable code claims nothing."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    claims: list[FormatClaim] = []
    seen: set[tuple[str, str]] = set()
    for statement in _reachable_nodes(tree):
        if not isinstance(statement, ast.stmt):
            continue
        nodes = list(_own_nodes(statement))
        words: set[str] = set()
        for node in nodes:
            if isinstance(node, ast.Name):
                words |= _words(node.id)
            elif isinstance(node, ast.Attribute):
                words |= _words(node.attr)
        is_input = bool(words & _INPUT_WORDS)
        is_output = bool(words & _OUTPUT_WORDS)
        if is_input == is_output:
            continue
        direction: FormatDirection = "input" if is_input else "output"
        for node in nodes:
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            extension = _extension(node.value)
            if extension is None or extension in _SOURCE_SUFFIXES:
                continue
            if (direction, extension) in seen:
                continue
            seen.add((direction, extension))
            claims.append(FormatClaim(extension, direction, statement.lineno))
    return sorted(claims, key=lambda claim: (claim.line, claim.direction, claim.extension))
