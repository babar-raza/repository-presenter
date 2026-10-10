"""``python -m tools.plan_lint lint|maps`` (run from the repository root)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cards import parse_plan
from .findings import errors
from .lint import DEFAULT_LEDGER, DEFAULT_MAPS_DIR, DEFAULT_PLAN, DEFAULT_STATE, lint_files
from .maps import write_maps


def plan_label(plan_path: Path, root: Path) -> str:
    """The plan as the maps name it: repo-relative POSIX when inside the repo, else its name."""
    try:
        return plan_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return plan_path.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="plan_lint", description=__doc__)
    parser.add_argument("command", choices=("lint", "maps"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--plan", type=Path, help=f"plan file (default {DEFAULT_PLAN})")
    parser.add_argument("--ledger", type=Path, help=f"loop-status.jsonl (default {DEFAULT_LEDGER})")
    parser.add_argument("--state", type=Path, help=f"state.yaml (default {DEFAULT_STATE})")
    parser.add_argument("--out", type=Path, help=f"maps directory (default {DEFAULT_MAPS_DIR})")
    args = parser.parse_args(argv)
    root: Path = args.root
    plan_path: Path = args.plan or root / DEFAULT_PLAN
    if not plan_path.is_file():
        print(f"plan_lint: plan file not found: {plan_path}", file=sys.stderr)
        return 2
    if args.command == "maps":
        out: Path = args.out or root / DEFAULT_MAPS_DIR
        for path in write_maps(parse_plan(plan_path), plan_label(plan_path, root), out):
            print(path)
        return 0
    ledger: Path = args.ledger or root / DEFAULT_LEDGER
    state: Path = args.state or root / DEFAULT_STATE
    findings = lint_files(plan_path, ledger, state, root)
    for finding in findings:
        print(finding.render())
    failed = errors(findings)
    print(f"plan_lint: {len(failed)} error(s), {len(findings) - len(failed)} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
