"""The tree-sitter grammars fact extraction parses source with, each from a pinned wheel.

Every grammar is an ordinary per-language wheel installed from ``requirements-lock.txt``; loading
one is a local import of a compiled extension, so no parse ever reaches the network. The
``tree-sitter-language-pack`` this replaced downloaded each parser from a GitHub release on first
use (``DownloadError: Failed to fetch manifest ... http status: 500`` failed a CI leg and would
have failed a hosted run the same way); the fault was that a build artifact was fetched at run
time, so the fix is that none is.

A language not registered here raises :class:`GrammarUnavailableError` naming it, and nothing
falls back to a download. A grammar is added to ``GRAMMARS`` only together with its exact pin in
``pyproject.toml`` and a probe in ``tests/test_grammar_pins.py``.
"""

from __future__ import annotations

import importlib
from typing import Any

from repository_presenter.core.errors import PresenterError


class GrammarUnavailableError(PresenterError):
    """No pinned grammar is installed for a language; the parse is refused, never fetched."""

    exit_code = 2


# language -> (importable module of the pinned wheel, function returning the grammar capsule).
# TypeScript's wheel carries two grammars; the extractor reads ``.ts``, so ``typescript`` is it.
GRAMMARS: dict[str, tuple[str, str]] = {
    "cpp": ("tree_sitter_cpp", "language"),
    "csharp": ("tree_sitter_c_sharp", "language"),
    "go": ("tree_sitter_go", "language"),
    "java": ("tree_sitter_java", "language"),
    "python": ("tree_sitter_python", "language"),
    "rust": ("tree_sitter_rust", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
}


def get_parser(language: str) -> Any:
    """A new tree-sitter ``Parser`` for *language*, built from its pinned wheel."""
    entry = GRAMMARS.get(language)
    if entry is None:
        raise GrammarUnavailableError(
            f"no pinned tree-sitter grammar is registered for {language!r}; "
            f"registered: {', '.join(sorted(GRAMMARS))}"
        )
    module_name, function = entry
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise GrammarUnavailableError(
            f"the pinned grammar wheel for {language!r} ({module_name}) is not installed"
        ) from exc

    from tree_sitter import Language, Parser

    return Parser(Language(getattr(module, function)()))
