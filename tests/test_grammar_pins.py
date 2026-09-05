"""The parsers the vendored surface extractor reads symbols from, pinned and probed.

`RESEARCH_AND_GUIDELINES.md` §29.6 E2: a symbol's `symbol_kind` is read from a tree-sitter node
type, so a grammar release can move a fact under a candidate that is already sealed. The three
packages are pinned exactly rather than by floor, and this probes each language the cohorts need -
with the network blocked, because a parser that had to fetch its grammar would make fact
extraction depend on a download.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest
import tree_sitter
import tree_sitter_c_sharp
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_parser

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


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """A grammar that is not already on disk fails here rather than reaching for it."""

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a parser tried to reach the network for its grammar")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.mark.parametrize("language", sorted(PROBES))
def test_each_grammar_parses_offline(language: str, no_network: None) -> None:
    source, root = PROBES[language]
    tree = get_parser(language).parse(source)
    assert tree.root_node.type == root
    assert not tree.root_node.has_error, f"{language} grammar did not understand its own probe"


def test_c_sharp_parses_through_its_own_package_as_well_as_the_pack(no_network: None) -> None:
    """The extractor imports the standalone package; the pack spells the language `csharp`.

    Measured 2026-09-06: a first `get_parser("c_sharp")` - the underscored spelling the extractor
    uses for its own package - raised DownloadError naming a 371-language manifest, which reads
    like a network dependency. It is not one: every language the cohorts need parses with the
    network blocked, and the standalone package needs no lookup at all. Only the pack's spelling
    is asserted here, because the underscored name's behaviour was not stable across calls.
    """
    parser = Parser(Language(tree_sitter_c_sharp.language()))
    tree = parser.parse(PROBES["csharp"][0])
    assert tree.root_node.type == "compilation_unit" and not tree.root_node.has_error
    assert get_parser("csharp").parse(PROBES["csharp"][0]).root_node.type == "compilation_unit"


def test_the_pins_are_exact() -> None:
    """A floor would let a grammar bump move a sealed candidate's facts."""
    assert tree_sitter.__version__ == "0.26.0"
