"""The no-bump proof: a branch's diff moved no governed version (TC-REF-10/11/12).

The local-rehearsal and hosting cards must never be able to bump a governed version (a bump marks
every sealed candidate stale). The plan lint refuses such a card on paper (``NO_BUMP_BREACH``,
``GOVERNED_PATH_IN_UNGOVERNED_CARD``); this tool checks the *actual diff* of a branch.

    python tools/workflow_rehearsal/no_bump_check.py <base-ref> [--head REF] [--no-src] [--root DIR]

The changed files are ``git diff --name-only $(git merge-base <base> <head>) <head>``: what the
branch changed, never what the base gained since. The run fails (exit 1) when

1. a changed file is a governed source: the list is parsed from
   ``tests/test_version_bump_discipline.py`` (``tools/plan_lint/governed.py``), never copied;
2. a changed ``src/**/*.py`` file moved a version constant (a module-level
   ``*VERSION = <literal>`` or a ``Check("id", "version", ...)`` literal) between the merge-base
   and the head - a bump of any version, governed or not (conservative: it also flags a
   fallback-version literal); or
3. with ``--no-src``, any changed file lies under ``src/`` (what a ``no_bump: true`` card allows).

Exit 2 means it could not decide (unknown ref, git failure, unreadable governed list): doubt never
passes. Standard library only; read-only; no network.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.plan_lint.governed import GovernedSetError, governed_files  # noqa: E402

_GIT_TIMEOUT = 120
_REDIRECTING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")


class Undecidable(RuntimeError):
    """The check could not be run; the caller must treat this as a failure, never a pass."""


def _git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in _REDIRECTING}
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Undecidable(f"git {' '.join(args)}: {error}") from error
    if done.returncode != 0:
        raise Undecidable(f"git {' '.join(args)} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def _blob(root: Path, revision: str, path: str) -> str | None:
    try:
        return _git(root, "show", f"{revision}:{path}")
    except Undecidable:
        return None  # absent at that revision (added or deleted)


def changed_files(root: Path, base: str, head: str) -> tuple[str, list[str]]:
    """``(merge_base, paths)``: the files the branch changed since it left ``base``."""
    merge_base = _git(root, "merge-base", base, head).strip()
    if not merge_base:
        raise Undecidable(f"no merge-base between {base!r} and {head!r}")
    raw = _git(root, "diff", "--name-only", "--no-renames", "-z", merge_base, head)
    return merge_base, sorted(p for p in raw.split("\0") if p)


def version_constants(text: str) -> dict[str, str]:
    """Module-level ``*VERSION = <literal>`` constants and ``Check(id, version, ...)`` literals."""
    found: dict[str, str] = {}
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Constant):
                for target in targets:
                    if isinstance(target, ast.Name) and target.id.endswith("VERSION"):
                        found[target.id] = repr(value.value)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Check"
        ):
            literals = [a for a in node.args[:2] if isinstance(a, ast.Constant)]
            if len(literals) == 2:
                found[f"Check:{literals[0].value}"] = repr(literals[1].value)
    return found


def check(root: Path, base: str, head: str = "HEAD", *, no_src: bool = False) -> list[str]:
    """Every violation (empty list = the diff moved no governed version); raises Undecidable."""
    try:
        governed = set(governed_files(root))
    except GovernedSetError as error:
        raise Undecidable(str(error)) from error
    merge_base, files = changed_files(root, base, head)
    violations: list[str] = []
    for path in files:
        if path in governed:
            violations.append(f"governed source changed: {path}")
        if not path.startswith("src/"):
            continue
        if no_src:
            violations.append(f"changed under src/ (not allowed for a no_bump card): {path}")
        if not path.endswith(".py"):
            continue
        old, new = _blob(root, merge_base, path), _blob(root, head, path)
        if old is None:
            continue  # added whole: it carries its own constants, as the discipline test reads it
        try:
            before = version_constants(old)
            after = version_constants(new) if new is not None else {}
        except SyntaxError as error:
            raise Undecidable(f"{path} does not parse: {error}") from error
        for name in sorted(before.keys() | after.keys()):
            if before.get(name) != after.get(name):
                violations.append(
                    f"version moved in {path}: {name} {before.get(name, '<absent>')} -> "
                    f"{after.get(name, '<absent>')}"
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base", help="the ref the branch started from (e.g. origin/main)")
    parser.add_argument("--head", default="HEAD", help="the branch under test (default HEAD)")
    parser.add_argument("--no-src", action="store_true", help="also fail on any change under src/")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args(argv)
    try:
        violations = check(args.root, args.base, args.head, no_src=args.no_src)
        merge_base, files = changed_files(args.root, args.base, args.head)
    except Undecidable as error:
        print(f"no_bump_check: UNDECIDABLE: {error}", file=sys.stderr)
        return 2
    for line in violations:
        print(f"no_bump_check: VIOLATION: {line}")
    verdict = "FAIL" if violations else "OK"
    print(
        f"no_bump_check: {verdict} ({len(files)} changed file(s) since {merge_base[:8]}; "
        f"{len(violations)} violation(s))"
    )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
