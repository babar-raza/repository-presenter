"""Format claims of a Python example: the file extensions its statements load or save.

Read from the example's syntax tree, never from prose. A file-name or extension literal counts
only when the identifiers of the same statement carry an input verb (open, load, read, import,
parse, detect) or an output verb (save, write, export, dump), and not both. The direction is the
example's claim; whether it holds is decided by the example's verification receipt, not here.
"""

from __future__ import annotations

import ast
import re
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
    for statement in ast.walk(tree):
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
