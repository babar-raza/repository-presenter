"""Does a source file parse: Python through `ast`, any other language through its grammar."""

from __future__ import annotations

import pytest

from repository_presenter.components.issues import source_parse

# (path, a clean file, a broken file)
CASES = [
    ("a.py", "def f():\n    return 1\n", "def f():\nreturn 1\n"),
    ("A.java", "class A { void f() {} }\n", "class A { void f( }\n"),
    ("A.cs", "class A { void F() {} }\n", "class A { void F( }\n"),
    ("a.go", "package a\nfunc F() {}\n", "package a\nfunc F( {\n"),
    ("a.rs", "fn f() {}\n", "fn f( {\n"),
    ("a.ts", "export const a: number = 1;\n", "export const a: number = ;\n"),
    ("a.cpp", "int f() { return 1; }\n", "int f( { return 1;\n"),
    ("a.hpp", "struct A { int x; };\n", "struct A { int x;\n"),
]


@pytest.mark.parametrize(("path", "clean", "broken"), CASES, ids=[c[0] for c in CASES])
def test_a_clean_file_parses_and_a_broken_one_is_described(
    path: str, clean: str, broken: str
) -> None:
    assert source_parse.syntax_error(path, clean) is None
    problem = source_parse.syntax_error(path, broken)
    assert problem is not None and problem.startswith(source_parse.parser_name(path))


def test_python_keeps_the_exact_parser_the_finding_was_made_with() -> None:
    problem = source_parse.syntax_error("a.py", "def f():\n return (\n")
    assert problem is not None and problem.startswith("ast.parse: ")
    assert source_parse.parser_name("a.py") == "ast.parse"
    assert source_parse.parser_name("A.java") == "tree-sitter (java)"


def test_a_tree_sitter_error_names_a_line() -> None:
    problem = source_parse.syntax_error("A.java", "class A {\n  void f() {}\n  int x = ;\n}\n")
    assert problem is not None and "line 3" in problem


def test_an_unregistered_suffix_cannot_be_checked_and_is_not_called_clean() -> None:
    """Negative control: no parser is not the same as 'parses'."""
    assert not source_parse.supported("notes.txt")
    assert not source_parse.supported("Makefile")
    with pytest.raises(source_parse.UnsupportedSourceError):
        source_parse.syntax_error("notes.txt", "anything")


@pytest.mark.parametrize("path", ["a.PY", "dir/A.JAVA", "x/y/z.Rs"])
def test_the_suffix_match_ignores_case_and_directories(path: str) -> None:
    assert source_parse.supported(path)
