"""The parsers the vendored surface extractor reads symbols from: pinned, probed, never fetched.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2: a symbol's `symbol_kind` is read from a tree-sitter node
type, so a grammar release can move a fact under a candidate that is already sealed. Every grammar
is therefore its own exactly pinned wheel, installed from the lock (`core/grammars.py`). The
previous `tree-sitter-language-pack` downloaded each parser from a GitHub release on first use, so
a release-host 500 failed a CI leg (run 37229453828, `DownloadError ... parsers.json: http status:
500`) and would have failed a hosted run the same way. The tests below hold the replacement to
three claims: each language parses with every socket closed, a language with no pinned wheel is a
typed refusal rather than a download, and nothing in `src/` can reach the old library again.
"""

from __future__ import annotations

import ast
import re
import socket
import sys
from importlib import metadata
from typing import Any

import pytest
import tree_sitter

from repository_presenter.core import grammars
from repository_presenter.core.grammars import GrammarUnavailableError, get_parser
from support import REPO_ROOT

# One statement per language whose root node the grammar must recognise. The parse is the probe:
# a grammar that loaded but does not understand the language returns an error node at the root.
PROBES: dict[str, tuple[bytes, str]] = {
    "python": (b"class Scene:\n    def save(self, path): ...\n", "module"),
    "csharp": (b"namespace N { public class C { public void M() {} } }", "compilation_unit"),
    "java": (b"package p; public class C { public void m() {} }", "program"),
    "go": (b"package p\n\nfunc F() {}\n", "source_file"),
    "typescript": (b"export class C { m(): void {} }", "program"),
    "cpp": (b"namespace n { class C { public: void m(); }; }", "translation_unit"),
    "rust": (b"pub struct S;\nimpl S { pub fn f(&self) {} }\n", "source_file"),
}

# language -> the wheel (distribution name) that carries its grammar, and the exact pin.
WHEELS: dict[str, tuple[str, str]] = {
    "cpp": ("tree-sitter-cpp", "0.23.4"),
    "csharp": ("tree-sitter-c-sharp", "0.23.5"),
    "go": ("tree-sitter-go", "0.25.0"),
    "java": ("tree-sitter-java", "0.23.5"),
    "python": ("tree-sitter-python", "0.23.6"),
    "rust": ("tree-sitter-rust", "0.24.2"),
    "typescript": ("tree-sitter-typescript", "0.23.2"),
}


def _refuse(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("a parser tried to reach the network for its grammar")


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every way Python opens a connection raises, so a fetch fails here rather than succeeds."""
    monkeypatch.setattr(socket, "socket", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


def test_probes_and_pins_cover_exactly_the_registered_languages() -> None:
    assert set(PROBES) == set(WHEELS) == set(grammars.GRAMMARS)


@pytest.mark.parametrize("language", sorted(PROBES))
def test_each_grammar_parses_offline(language: str, no_network: None) -> None:
    source, root = PROBES[language]
    tree = get_parser(language).parse(source)
    assert tree.root_node.type == root
    assert not tree.root_node.has_error, f"{language} grammar did not understand its own probe"


@pytest.mark.parametrize("language", ["ruby", "c_sharp", "", "CSharp"])
def test_an_unregistered_language_is_a_typed_refusal_not_a_download(
    language: str, no_network: None
) -> None:
    """Negative control: with the network closed, a missing grammar must still be this error.

    Were the lookup to fall back to a fetch, the closed socket would raise the fixture's
    AssertionError instead, so this fails if a download path ever returns.
    """
    with pytest.raises(GrammarUnavailableError) as raised:
        get_parser(language)
    assert repr(language) in str(raised.value)
    assert raised.value.exit_code == 2


def test_a_registered_grammar_whose_wheel_is_missing_is_named_not_fetched(
    monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    monkeypatch.setitem(grammars.GRAMMARS, "cobol", ("tree_sitter_cobol_not_installed", "language"))
    with pytest.raises(GrammarUnavailableError, match=r"cobol.*tree_sitter_cobol_not_installed"):
        get_parser("cobol")
    assert "tree_sitter_cobol_not_installed" not in sys.modules


@pytest.mark.parametrize("language", sorted(WHEELS))
def test_the_installed_wheel_is_the_pinned_one(language: str) -> None:
    """A floor would let a grammar bump move a sealed candidate's facts."""
    distribution, version = WHEELS[language]
    assert metadata.version(distribution) == version
    pyproject = (REPO_ROOT / "pyproject.toml").read_text("utf-8")
    assert f'"{distribution}=={version}"' in pyproject
    lock = (REPO_ROOT / "requirements-lock.txt").read_text("utf-8")
    assert re.search(rf"^{re.escape(distribution)}=={re.escape(version)} ", lock, re.M)


def test_the_tree_sitter_core_is_pinned() -> None:
    assert tree_sitter.__version__ == "0.26.0"


def test_nothing_can_reach_the_downloading_library_again() -> None:
    """The library that fetched parsers on first use is out of the dependencies and the source."""
    assert "tree_sitter_language_pack" not in sys.modules
    for name in ("pyproject.toml", "requirements-lock.txt"):
        text = (REPO_ROOT / name).read_text("utf-8")
        assert not re.search(r"^\s*\"?tree-sitter-language-pack", text, re.M), name
    for path in (REPO_ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            imported = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not any(name.startswith("tree_sitter_language_pack") for name in imported), path
