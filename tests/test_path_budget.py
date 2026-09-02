"""Path budget: no tracked path may exceed 200 characters."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

from support import REPO_ROOT

PATH_BUDGET = 200


def tracked_paths(root: Path) -> list[str]:
    """Every path in the Git index, as Git records it."""
    listing = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    return [entry.decode("utf-8") for entry in listing.split(b"\0") if entry]


def over_budget(paths: Iterable[str], limit: int = PATH_BUDGET) -> list[str]:
    return [path for path in paths if len(path) > limit]


def test_every_tracked_path_is_within_budget() -> None:
    paths = tracked_paths(REPO_ROOT)
    assert paths, "git ls-files listed nothing; the budget check needs a Git checkout"
    assert over_budget(paths) == []


def test_budget_check_flags_a_path_over_200_characters() -> None:
    at_budget = "a" * PATH_BUDGET
    over = "src/" + "n" * 196 + ".py"
    assert len(over) == PATH_BUDGET + 3
    assert over_budget(["src/ok.py", at_budget, over]) == [over]
