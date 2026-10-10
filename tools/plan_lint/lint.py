"""Run the whole lint: static rules, ledger fold, evidence hashes, state agreement."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cards import Plan, parse_plan
from .findings import Finding
from .ledger import FoldResult, check_state_items, fold_ledger, load_state, read_ledger
from .rules import lint_plan

DEFAULT_PLAN = "plans/reseal-and-refresh/PLAN.md"
DEFAULT_LEDGER = "plans/reseal-and-refresh/loop-status.jsonl"
DEFAULT_STATE = "project/state.yaml"
DEFAULT_MAPS_DIR = "evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/generated-artifacts"


def lint_all(
    plan: Plan,
    *,
    ledger_lines: list[str] | None = None,
    state: Any = None,
    root: Path,
) -> tuple[list[Finding], FoldResult]:
    findings = lint_plan(plan)
    fold = fold_ledger(plan, ledger_lines or [], root)
    findings.extend(fold.findings)
    if state is not None:
        findings.extend(check_state_items(plan, fold, state))
    return findings, fold


def lint_files(
    plan_path: Path, ledger_path: Path | None, state_path: Path | None, root: Path
) -> list[Finding]:
    plan = parse_plan(plan_path)
    lines = read_ledger(ledger_path) if ledger_path else []
    state = load_state(state_path) if state_path and state_path.is_file() else None
    findings, _ = lint_all(plan, ledger_lines=lines, state=state, root=root)
    return findings
