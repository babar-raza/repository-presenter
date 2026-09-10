"""README CLI reference: every subcommand and flag cli.py defines is named in README.md.

The project's own top-level README has no other check on it - unlike a generated candidate
README, nothing validates its prose against the code it describes. This narrow check catches one
concrete drift shape (a subcommand or flag added to the CLI and never mentioned in README.md) by
reading the real parser, not by re-typing the CLI surface a second time to compare against.
"""

from __future__ import annotations

import argparse

from repository_presenter.cli import build_parser
from support import REPO_ROOT


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    # argparse exposes no public way to list registered subparsers.
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    raise AssertionError("build_parser() defines no subcommands")


_ARGPARSE_BUILTINS = {"-h", "--help"}


def _cli_tokens() -> set[str]:
    """Every subcommand name and flag the real CLI accepts, minus argparse's own -h/--help."""
    parser = build_parser()
    tokens = {"--version"}
    for name, subparser in _subparsers(parser).items():
        tokens.add(name)
        for action in subparser._actions:
            tokens.update(action.option_strings)
    return tokens - _ARGPARSE_BUILTINS


def test_every_cli_token_is_named_in_the_readme() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    missing = sorted(token for token in _cli_tokens() if token not in readme)
    assert missing == []


def test_cli_tokens_are_not_accidentally_empty() -> None:
    """A parser-introspection bug that returns nothing must not read as trivially passing."""
    tokens = _cli_tokens()
    assert {"status", "present", "preflight", "--repo", "--facts-only", "--fresh"} <= tokens
