"""Ledger fold, legal transitions and evidence hashes (card TC-LNT-01-03).

``plans/reseal-and-refresh/loop-status.jsonl`` is append-only; one line is one transition::

    {"ts", "card", "from", "to", "actor", "evidence": [{"path", "sha256"}], "scores": {...},
     "commit", "reason"}

The current state of every card is the fold of its lines. The fold rejects any line whose ``from``
is not the card's current state, any transition outside the tables of the plan's section 6, and
the illegal examples listed there (closing with open children or micro-steps, a low score,
evidence that is missing, empty or unhashed, ...). A card with no line is in its initial state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .cards import CHILD_ID, MICRO_ID, PARENT_ID, Plan
from .findings import Finding

PARENT_INITIAL, CHILD_INITIAL, MICRO_INITIAL = "PROPOSED", "TODO", "PENDING"

_PARENT_MAIN = {
    "PROPOSED": {"READY"},
    "READY": {"IN_PROGRESS"},
    "IN_PROGRESS": {"CHILDREN_IN_PROGRESS"},
    "CHILDREN_IN_PROGRESS": {"INTEGRATION_PENDING"},
    "INTEGRATION_PENDING": {"VERIFIED"},
    "VERIFIED": {"SCORED"},
    "SCORED": {"CLOSED", "REROUTED"},
    "REROUTED": {"IN_PROGRESS"},
    "BLOCKED": {"READY"},
    "BLOCKED_EXTERNAL": {"READY", "CLOSED"},  # either way only with unblock evidence
    "DEFERRED_WITH_REASON": {"READY"},
    "CLOSED": set(),
}
_CHILD_MAIN = {
    "TODO": {"READY"},
    "READY": {"IN_PROGRESS"},
    "IN_PROGRESS": {"IMPLEMENTED"},
    "IMPLEMENTED": {"VERIFIED"},
    "VERIFIED": {"SCORED"},
    "SCORED": {"CLOSED", "REROUTED"},
    "REROUTED": {"IN_PROGRESS"},
    "BLOCKED": {"READY"},
    "BLOCKED_EXTERNAL": {"READY", "CLOSED"},
    "DEFERRED_WITH_REASON": {"READY"},
    "CLOSED": set(),
}
_PARKED = ("BLOCKED", "BLOCKED_EXTERNAL", "DEFERRED_WITH_REASON")


def _with_parking(table: dict[str, set[str]]) -> dict[str, set[str]]:
    """Add 'any non-closed state -> BLOCKED | BLOCKED_EXTERNAL | DEFERRED_WITH_REASON'."""
    return {
        state: (nxt | {p for p in _PARKED if p != state}) if state != "CLOSED" else set(nxt)
        for state, nxt in table.items()
    }


TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "parent": _with_parking(_PARENT_MAIN),
    "child": _with_parking(_CHILD_MAIN),
    "micro": {
        "PENDING": {"READY", "SKIPPED_NOT_APPLICABLE"},
        "READY": {"ACTIVE"},
        "ACTIVE": {"COMPLETE", "FAILED", "BLOCKED"},
        "FAILED": {"READY"},
        "BLOCKED": {"READY"},
        "COMPLETE": set(),
        "SKIPPED_NOT_APPLICABLE": set(),
    },
}
INITIAL = {"parent": PARENT_INITIAL, "child": CHILD_INITIAL, "micro": MICRO_INITIAL}

PARENT_SCORES = (
    "root_cause_coverage",
    "child_completeness",
    "integration_completeness",
    "dependency_correctness",
    "preserved_behavior",
    "evidence_completeness",
    "rerun_consistency",
    "production_readiness",
)
CHILD_SCORES = (
    "requirement_correctness",
    "implementation_correctness",
    "scope_discipline",
    "validation_strength",
    "evidence_completeness",
    "regression_safety",
    "maintainability",
    "production_readiness",
)
SCORE_FLOOR = 4
SCORE_CEILING = 5
_SHA256_CHARS = set("0123456789abcdef")


def card_kind(card_id: str) -> str | None:
    if PARENT_ID.match(card_id):
        return "parent"
    if CHILD_ID.match(card_id):
        return "child"
    if MICRO_ID.match(card_id):
        return "micro"
    return None


@dataclass
class FoldResult:
    """Current state per card id (only cards that have a ledger line) plus the findings."""

    states: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def state_of(self, card_id: str) -> str:
        kind = card_kind(card_id) or "parent"
        return self.states.get(card_id, INITIAL[kind])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_evidence(entries: Any, root: Path, where: str, *, required: bool) -> list[Finding]:
    """Evidence entries must name an existing, non-empty file whose sha256 matches."""
    if entries is None or entries == []:
        if required:
            return [Finding("LEDGER_EVIDENCE", where, "COMPLETE/CLOSED needs evidence entries")]
        return []
    if not isinstance(entries, list):
        return [Finding("LEDGER_EVIDENCE", where, "`evidence` must be a list")]
    found: list[Finding] = []
    for entry in entries:
        if not isinstance(entry, dict):
            found.append(Finding("LEDGER_EVIDENCE", where, "evidence entry is not an object"))
            continue
        raw_path, digest = entry.get("path"), entry.get("sha256")
        if not isinstance(raw_path, str) or not raw_path:
            found.append(Finding("LEDGER_EVIDENCE", where, "evidence entry has no path"))
            continue
        relative = PurePosixPath(raw_path.replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or ":" in relative.parts[0]:
            found.append(Finding("LEDGER_EVIDENCE", where, f"{raw_path}: path leaves the repo"))
            continue
        target = root.joinpath(*relative.parts)
        if not target.is_file():
            found.append(Finding("LEDGER_EVIDENCE", where, f"{raw_path}: evidence file missing"))
            continue
        if target.stat().st_size == 0:
            found.append(Finding("LEDGER_EVIDENCE", where, f"{raw_path}: evidence file is empty"))
            continue
        if not isinstance(digest, str) or len(digest) != 64 or not set(digest) <= _SHA256_CHARS:
            found.append(Finding("LEDGER_EVIDENCE", where, f"{raw_path}: sha256 missing/invalid"))
            continue
        if sha256_file(target) != digest:
            found.append(Finding("LEDGER_EVIDENCE", where, f"{raw_path}: sha256 does not match"))
    return found


def _known_cards(plan: Plan) -> dict[str, str]:
    known: dict[str, str] = {}
    for parent in plan.parents:
        known[parent.id] = "parent"
        for child in parent.children:
            known[child.id] = "child"
            for step in child.steps:
                known[step.id] = "micro"
    return known


def _score_findings(scores: Any, kind: str, where: str, *, floor: int | None) -> list[Finding]:
    dims = PARENT_SCORES if kind == "parent" else CHILD_SCORES
    if not isinstance(scores, dict):
        return [Finding("LEDGER_SCORES", where, f"mandatory scores {dims} are missing")]
    found: list[Finding] = []
    for dim in dims:
        value = scores.get(dim)
        if isinstance(value, bool) or not isinstance(value, int | float):
            found.append(Finding("LEDGER_SCORES", where, f"score {dim} missing or not a number"))
        elif value > SCORE_CEILING or value < 0:
            found.append(Finding("LEDGER_SCORES", where, f"score {dim}={value} is out of 0..5"))
        elif floor is not None and value < floor:
            found.append(
                Finding("LEDGER_SCORE_LOW", where, f"CLOSED with {dim}={value} (< {floor}/5)")
            )
    return found


def _close_findings(
    plan: Plan, states: dict[str, str], card_id: str, kind: str, where: str
) -> list[Finding]:
    """Parent CLOSED needs every mandatory child CLOSED; child CLOSED needs every micro done."""
    found: list[Finding] = []
    if kind == "parent":
        parent = plan.parent(card_id)
        for child in parent.children if parent else []:
            if child.optional:
                continue
            if states.get(child.id, INITIAL["child"]) != "CLOSED":
                found.append(
                    Finding(
                        "LEDGER_CLOSE_INCOMPLETE", where, f"parent closed, child {child.id} not"
                    )
                )
    elif kind == "child":
        child_card = plan.child(card_id)
        for step in child_card.steps if child_card else []:
            if states.get(step.id, INITIAL["micro"]) not in ("COMPLETE", "SKIPPED_NOT_APPLICABLE"):
                found.append(
                    Finding(
                        "LEDGER_CLOSE_INCOMPLETE", where, f"child closed, micro {step.id} not done"
                    )
                )
    return found


def fold_ledger(plan: Plan, lines: list[str], root: Path) -> FoldResult:
    """Fold the ledger lines; every violation is a finding (a bad line changes no state)."""
    result = FoldResult()
    known = _known_cards(plan)
    authors: dict[str, str] = {}
    scored: dict[str, Any] = {}
    states = result.states
    for number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        where = f"ledger:{number}"
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as error:
            result.findings.append(Finding("LEDGER_FORMAT", where, f"not JSON: {error.msg}"))
            continue
        if not isinstance(row, dict):
            result.findings.append(Finding("LEDGER_FORMAT", where, "line is not a JSON object"))
            continue
        missing = [
            k for k in ("ts", "card", "from", "to", "actor") if not isinstance(row.get(k), str)
        ]
        if missing:
            result.findings.append(Finding("LEDGER_FORMAT", where, f"missing/non-string {missing}"))
            continue
        card, src, dst, actor = row["card"], row["from"], row["to"], row["actor"]
        kind = known.get(card)
        if kind is None:
            result.findings.append(Finding("LEDGER_UNKNOWN_CARD", where, f"{card} is not in plan"))
            continue
        table = TRANSITIONS[kind]
        current = states.get(card, INITIAL[kind])
        if src != current:
            result.findings.append(
                Finding(
                    "LEDGER_STATE_MISMATCH", where, f"{card} is {current}, line says from {src}"
                )
            )
            continue
        if dst not in table.get(src, set()):
            result.findings.append(
                Finding("LEDGER_ILLEGAL_TRANSITION", where, f"{card}: {src} -> {dst} is not legal")
            )
            continue
        problems = check_evidence(
            row.get("evidence"), root, where, required=dst in ("COMPLETE", "CLOSED")
        )
        if src == "BLOCKED_EXTERNAL" and not row.get("evidence"):
            problems.append(
                Finding(
                    "LEDGER_UNBLOCK_EVIDENCE",
                    where,
                    f"{card}: leaving BLOCKED_EXTERNAL needs unblock evidence",
                )
            )
        if dst in ("DEFERRED_WITH_REASON", "SKIPPED_NOT_APPLICABLE") and not (
            isinstance(row.get("reason"), str) and row["reason"].strip()
        ):
            problems.append(Finding("LEDGER_REASON", where, f"{card}: {dst} requires a `reason`"))
        if dst == "IN_PROGRESS" and kind == "parent":
            owner = plan.parent(card)
            for ref in owner.depends if owner else []:
                ref_kind = known.get(ref, "parent")
                if states.get(ref, INITIAL[ref_kind]) != "CLOSED":
                    problems.append(
                        Finding(
                            "LEDGER_DEPENDENCY_OPEN", where, f"{card} started, {ref} not CLOSED"
                        )
                    )
        if dst == "IN_PROGRESS" and card not in authors:
            authors[card] = actor
        if dst == "SCORED":
            if authors.get(card) == actor:
                problems.append(
                    Finding("LEDGER_SELF_SCORED", where, f"{card} scored by its author {actor}")
                )
            problems.extend(_score_findings(row.get("scores"), kind, where, floor=None))
            scored[card] = row.get("scores")
        if dst == "CLOSED":
            if src == "SCORED":
                problems.extend(
                    _score_findings(
                        row.get("scores") or scored.get(card), kind, where, floor=SCORE_FLOOR
                    )
                )
            problems.extend(_close_findings(plan, states, card, kind, where))
        result.findings.extend(problems)
        states[card] = dst  # the line was well formed and legal; its violations are findings
    return result


def read_ledger(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def check_state_items(plan: Plan, fold: FoldResult, state: Any) -> list[Finding]:
    """A state.yaml work item may be COMPLETE only when its mapped parents are CLOSED."""
    if not isinstance(state, dict):
        return [Finding("STATE_FORMAT", "project/state.yaml", "state file is not a mapping")]
    items: dict[str, str] = {}
    active = state.get("active_work_item")
    candidates = [active] if isinstance(active, dict) else []
    queue = state.get("next_ready_items")
    candidates += queue if isinstance(queue, list) else []
    for entry in candidates:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            items[entry["id"]] = str(entry.get("status", ""))
    found: list[Finding] = []
    for item in sorted({p.item for p in plan.parents if p.item}):
        mapped = [p for p in plan.parents if p.item == item]
        if item not in items:
            found.append(
                Finding(
                    "STATE_ITEM_UNKNOWN",
                    item,
                    "no such work item in state.yaml yet",
                    severity="warn",
                )
            )
            continue
        if items[item] != "COMPLETE":
            continue
        for parent in mapped:
            if parent.optional:
                continue
            if fold.state_of(parent.id) != "CLOSED":
                found.append(
                    Finding(
                        "STATE_ITEM_COMPLETE_OPEN",
                        item,
                        f"work item COMPLETE but mapped parent {parent.id} is "
                        f"{fold.state_of(parent.id)}",
                    )
                )
    return found


def load_state(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
