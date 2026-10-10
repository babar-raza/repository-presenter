"""Does one source file parse? The check behind a `NOT_PROCESSABLE` re-detection, for any language.

The first `NOT_PROCESSABLE` handoff (TeX-Python) was reproduced with Python's own ``ast.parse``,
so Python keeps that exact parser: a file that fails ``ast.parse`` is the finding itself, not an
approximation of it. Every other language goes through the pinned tree-sitter grammars
(`core/grammars.py`), the same registry fact extraction parses source with - this module adds no
parser of its own and a language with no pinned grammar is *unsupported*, never skipped or passed.

``syntax_error`` returns a one-line description of the first syntax error, or ``None`` for a file
that parses. Whether a suffix is parseable at all is :func:`supported`, so a caller can tell
"does not parse" from "this tool cannot say".
"""

from __future__ import annotations

import ast
from pathlib import PurePosixPath
from typing import Any

from repository_presenter.core.grammars import GrammarUnavailableError, get_parser

# suffix -> the `core/grammars.py` language that parses it. Python is absent on purpose: it is
# parsed by `ast`. Adding a language is a row here only if `GRAMMARS` already pins its grammar.
_TREE_SITTER_SUFFIXES: dict[str, str] = {
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".h": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".ts": "typescript",
}


class UnsupportedSourceError(ValueError):
    """No parser is registered for this file's suffix."""


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def supported(path: str) -> bool:
    """Whether a parser is registered for ``path``'s suffix."""
    suffix = _suffix(path)
    return suffix == ".py" or suffix in _TREE_SITTER_SUFFIXES


def parser_name(path: str) -> str:
    """What parses ``path``, for the evidence line that records a clean parse."""
    language = _TREE_SITTER_SUFFIXES.get(_suffix(path))
    return "ast.parse" if language is None else f"tree-sitter ({language})"


def _python_error(text: str) -> str | None:
    try:
        ast.parse(text)
    except SyntaxError as exc:
        return f"ast.parse: {type(exc).__name__}: {exc}"
    return None


def _first_error_node(node: Any) -> Any | None:
    """The first ERROR or MISSING node in document order, found without recursion (a deeply
    nested broken file must not blow the interpreter's stack)."""
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "ERROR" or current.is_missing:
            return current
        stack.extend(reversed(current.children))
    return None


def _tree_sitter_error(language: str, text: str) -> str | None:
    parser = get_parser(language)
    tree = parser.parse(text.encode("utf-8"))
    if not tree.root_node.has_error:
        return None
    node = _first_error_node(tree.root_node)
    if node is None:  # has_error with no locatable node: still a parse failure, say so plainly
        return f"tree-sitter ({language}): syntax error"
    line = node.start_point[0] + 1
    what = "missing " + node.type if node.is_missing else "unexpected token"
    return f"tree-sitter ({language}): {what} at line {line}"


def syntax_error(path: str, text: str) -> str | None:
    """A description of ``text``'s first syntax error, or ``None`` when it parses.

    Raises :class:`UnsupportedSourceError` for a suffix with no registered parser, and lets
    :class:`GrammarUnavailableError` through when a registered language's wheel is not installed -
    both mean "cannot say", which a caller must not round to "parses".
    """
    suffix = _suffix(path)
    if suffix == ".py":
        return _python_error(text)
    language = _TREE_SITTER_SUFFIXES.get(suffix)
    if language is None:
        raise UnsupportedSourceError(f"no parser is registered for {suffix or 'this file'!r}")
    return _tree_sitter_error(language, text)


__all__ = [
    "GrammarUnavailableError",
    "UnsupportedSourceError",
    "parser_name",
    "supported",
    "syntax_error",
]
