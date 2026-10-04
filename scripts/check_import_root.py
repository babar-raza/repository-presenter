"""Fail loudly unless ``import repository_presenter`` resolves inside this checkout's ``src/``.

scripts/ci_check.sh exports PYTHONPATH to this checkout's src, but an editable install of another
checkout can still be what gets imported: the repo venv's install is a path entry pointing at
whichever checkout ran ``pip install -e .``, and a ``.venv`` junction shares that install across
worktrees. Measured 2026-10-04: from a worktree, ``import repository_presenter`` without PYTHONPATH
resolved to the main checkout's src. Every check would then test stale code and report a result for
a tree that is not the one being checked. This script makes that a loud, named failure instead.

Usage: python scripts/check_import_root.py <repository root>
Exit 0 when the package resolves under <root>/src; exit 1 when it resolves elsewhere or not at all.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_import_root.py <repository root>", file=sys.stderr)
        return 2
    src = (Path(argv[1]).resolve() / "src").resolve()
    try:
        package = importlib.import_module("repository_presenter")
    except ImportError as error:
        print(f"repository_presenter does not import: {error}")
        return 1
    location = getattr(package, "__file__", None)
    if location is None:
        print("repository_presenter has no __file__ (namespace package); cannot place it")
        return 1
    resolved = Path(location).resolve()
    if not resolved.is_relative_to(src):
        print(f"repository_presenter resolves to {resolved}, outside {src}")
        return 1
    print(f"repository_presenter resolves to {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
