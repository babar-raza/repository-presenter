"""tools/plan_lint: every structural promise of the plan's section 6 is a failing test (TC-LNT-01).

Each rule has a failing fixture (the synthetic plan with one defect injected) and a passing one
(the synthetic plan itself). The real plan (plans/reseal-and-refresh/PLAN.md, or the file named by
PLAN_LINT_PLAN) is linted when it exists; it is skipped, loudly, when it does not.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.plan_lint import __main__ as cli
from tools.plan_lint import cards, ledger, lint, maps, rules
from tools.plan_lint.findings import Finding, errors

from support import REPO_ROOT
from test_version_bump_discipline import GOVERNED

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "plan_lint" / "synthetic_plan.md"
PLAN_TEXT = FIXTURE.read_text(encoding="utf-8")
EVIDENCE = "ev/evidence.txt"


def codes(findings: list[Finding]) -> set[str]:
    return {f.rule for f in errors(findings)}


def lint_text(text: str) -> list[Finding]:
    return rules.lint_plan(cards.parse_plan_text(text))


def mutate(old: str, new: str, text: str = PLAN_TEXT) -> str:
    assert text.count(old) == 1, f"fixture anchor {old!r} must occur exactly once"
    return text.replace(old, new)


# --------------------------------------------------------------------------- parsing


def test_the_synthetic_plan_parses_to_a_card_tree() -> None:
    plan = cards.parse_plan_text(PLAN_TEXT)
    assert [p.id for p in plan.parents] == ["TC-AAA-01", "TC-BBB-01", "TC-CCC-01"]
    assert [c.id for c in plan.parents[0].children] == ["TC-AAA-01-01", "TC-AAA-01-02"]
    assert plan.defined_reqs == {"REQ-AAA-01", "REQ-BBB-01", "REQ-CCC-01", "REQ-CCC-02"}
    # The micro-step ID is derived from the 1-based position of the step in its child.
    steps = plan.parents[0].children[0].steps
    assert [s.id for s in steps] == ["MS-AAA-01-01-01", "MS-AAA-01-01-02"]
    assert (steps[0].op, steps[0].target, steps[0].done_when) == (
        "inspect",
        "docs/synthetic/one/a.md",
        "notes recorded",
    )


def test_the_header_mapping_block_is_not_a_card() -> None:
    assert len(cards.parse_plan_text(PLAN_TEXT).parents) == 3


def test_requirement_ranges_expand() -> None:
    assert cards.expand_requirements("REQ-ISS-01…03 and REQ-A1-07") == {
        "REQ-ISS-01",
        "REQ-ISS-02",
        "REQ-ISS-03",
        "REQ-A1-07",
    }


def test_reordering_steps_changes_the_micro_ids() -> None:
    swapped = mutate(
        '        - "inspect | docs/synthetic/one/a.md | notes recorded"\n'
        '        - "create | docs/synthetic/one/b.md | file exists"\n',
        '        - "create | docs/synthetic/one/b.md | file exists"\n'
        '        - "inspect | docs/synthetic/one/a.md | notes recorded"\n',
    )
    first = cards.parse_plan_text(swapped).parents[0].children[0].steps[0]
    assert (first.id, first.op) == ("MS-AAA-01-01-01", "create")


# --------------------------------------------------------------------------- static rules


def test_the_synthetic_plan_lints_clean() -> None:
    assert lint_text(PLAN_TEXT) == []


STATIC_DEFECTS: list[tuple[str, str, str, str]] = [
    # (name, old, new, expected rule)
    ("unparsable yaml", "  outcome: something observable\n", "  outcome: a: b: c\n", "PARSE"),
    ("duplicate parent id", "id: TC-BBB-01\n", "id: TC-AAA-01\n", "ID_DUPLICATE"),
    ("duplicate child id", "id: TC-AAA-01-02\n", "id: TC-AAA-01-01\n", "ID_DUPLICATE"),
    ("malformed parent id", "id: TC-BBB-01\n", "id: TC-bbb-1\n", "ID_FORMAT"),
    ("child under the wrong parent", "id: TC-BBB-01-01\n", "id: TC-AAA-01-09\n", "ID_FORMAT"),
    ("bad item id", "item: G7-W91\n", "item: W91\n", "ITEM_FORMAT"),
    (
        "undefined requirement",
        "reqs: [REQ-AAA-01]",
        "reqs: [REQ-AAA-01, REQ-ZZZ-01]",
        "REQ_UNDEFINED",
    ),
    (
        "requirement without a parent",
        "REQ-BBB-01 second requirement",
        "REQ-BBB-01 second requirement · REQ-BBB-02 orphan",
        "REQ_UNREFERENCED",
    ),
    ("parent without a requirement", "reqs: [REQ-BBB-01]", "reqs: []", "PARENT_NO_REQ"),
    (
        "range member without a parent",
        "reqs: [REQ-CCC-01, REQ-CCC-02]",
        "reqs: [REQ-CCC-01]",
        "REQ_UNREFERENCED",
    ),
    (
        "parent without a child",
        "  children:\n    - id: TC-BBB-01-01\n"
        "      title: Only child\n"
        "      steps:\n"
        '        - "edit | docs/synthetic/two/x.md | text changed"\n'
        '        - "validate | pytest tests/test_plan_lint.py -q | passes"\n',
        "  children: []\n",
        "PARENT_NO_CHILD",
    ),
    (
        "child without a step",
        '      steps:\n        - "run | python -V | version printed"\n',
        "      steps: []\n",
        "CHILD_NO_STEP",
    ),
    (
        "step that is not an op/target/done-when triple",
        '"run | python -V | version printed"',
        '"run | python -V"',
        "STEP_FORMAT",
    ),
    (
        "step with an empty done-when",
        '"run | python -V | version printed"',
        '"run | python -V | "',
        "STEP_FORMAT",
    ),
    (
        "step with an unknown op",
        '"run | python -V | version printed"',
        '"execute | python -V | version printed"',
        "STEP_OP",
    ),
    (
        "depends on an unknown card",
        "depends: [TC-AAA-01]",
        "depends: [TC-NOPE-01]",
        "DEPEND_UNKNOWN",
    ),
    (
        "dependency cycle",
        "  depends: []\n",
        "  depends: [TC-BBB-01]\n",
        "DEPEND_CYCLE",
    ),
    (
        "card that depends on its own child",
        "depends: [TC-AAA-01]",
        "depends: [TC-BBB-01-01]",
        "DEPEND_CYCLE",
    ),
    (
        "allowed and forbidden paths overlap",
        "forbidden: [docs/synthetic/other/]",
        "forbidden: [docs/synthetic/one/sub/]",
        "PATHS_ALLOWED_FORBIDDEN",
    ),
    (
        "card without write paths",
        "paths: {write: [docs/synthetic/two/]}",
        "paths: {}",
        "PATHS_NO_WRITE",
    ),
    (
        "child writes outside its parent",
        "      title: Only child\n",
        "      title: Only child\n      paths: {write: [docs/elsewhere/]}\n",
        "PATHS_OUTSIDE_PARENT",
    ),
    (
        "parallel cards share a write path",
        "paths: {write: [docs/synthetic/two/]}",
        "paths: {write: [docs/synthetic/three/deep/]}",
        "PARALLEL_WRITE_CONFLICT",
    ),
    (
        "governed without a ground",
        '  ground: "factual-accuracy plus owner approval D-OWN-2"\n',
        "",
        "GOVERNED_NO_GROUND",
    ),
    (
        "governed with a blank ground",
        '  ground: "factual-accuracy plus owner approval D-OWN-2"\n',
        '  ground: "  "\n',
        "GOVERNED_NO_GROUND",
    ),
    (
        "governed source written without governed: true",
        "  governed: true\n",
        "  governed: false\n",
        "GOVERNED_UNDECLARED",
    ),
    (
        "governed flag missing",
        "  governed: true\n",
        "",
        "GOVERNED_UNDECLARED",
    ),
    (
        "investigation child that names no cards",
        "      produces: [TC-CCC-02]\n",
        "",
        "INVESTIGATION_NO_PRODUCES",
    ),
]


@pytest.mark.parametrize(("name", "old", "new", "rule"), STATIC_DEFECTS)
def test_each_static_rule_fails_its_bad_fixture(name: str, old: str, new: str, rule: str) -> None:
    assert rule in codes(lint_text(mutate(old, new))), name


def test_a_missing_requirements_section_fails() -> None:
    text = mutate("## 3. Requirements (stable IDs)", "## 3. Something else")
    assert "REQ_UNDEFINED" in codes(lint_text(text))


def test_a_governed_card_with_a_ground_passes() -> None:
    parent = cards.parse_plan_text(PLAN_TEXT).parent("TC-CCC-01")
    assert parent is not None and parent.governed is True and parent.ground


def test_an_ungoverned_card_outside_governed_paths_needs_no_ground() -> None:
    assert "GOVERNED_NO_GROUND" not in codes(lint_text(PLAN_TEXT))


def test_dependency_on_a_child_resolves_to_its_parent() -> None:
    plan = cards.parse_plan_text(PLAN_TEXT)
    assert rules.depends_graph(plan)["TC-CCC-01"] == ["TC-AAA-01"]


def test_parallel_cards_in_one_lane_are_serialised_by_the_lane() -> None:
    conflicting = mutate(
        "paths: {write: [docs/synthetic/two/]}", "paths: {write: [docs/synthetic/three/deep/]}"
    )
    assert "PARALLEL_WRITE_CONFLICT" in codes(lint_text(conflicting))
    same_lane = conflicting.replace("lane: L-two", "lane: L-three")
    assert "PARALLEL_WRITE_CONFLICT" not in codes(lint_text(same_lane))


def test_a_dependency_path_makes_cards_sequential_not_parallel() -> None:
    conflicting = mutate(
        "paths: {write: [docs/synthetic/two/]}", "paths: {write: [docs/synthetic/three/deep/]}"
    )
    chained = conflicting.replace(
        "  depends: [TC-AAA-01]\n  governed: false\n  paths: {write: [docs/synthetic/three/deep/]}",
        "  depends: [TC-CCC-01]\n  governed: false\n  paths: {write: [docs/synthetic/three/deep/]}",
    )
    assert chained != conflicting
    assert "PARALLEL_WRITE_CONFLICT" not in codes(lint_text(chained))


def test_a_header_serialised_path_waives_a_hot_file_overlap() -> None:
    conflicting = mutate(
        "paths: {write: [docs/synthetic/two/]}", "paths: {write: [docs/synthetic/three/deep/]}"
    )
    waived = conflicting.replace(
        "serialised_paths: []", "serialised_paths: [docs/synthetic/three/]"
    )
    assert "PARALLEL_WRITE_CONFLICT" in codes(lint_text(conflicting))
    assert "PARALLEL_WRITE_CONFLICT" not in codes(lint_text(waived))


def test_write_path_overlap_is_segment_wise() -> None:
    assert rules.paths_overlap("docs/a/", "docs/a/b.md")
    assert rules.paths_overlap("docs", "docs/a/b.md")
    assert not rules.paths_overlap("docs/a/", "docs/ab/")


def test_governed_files_agree_with_the_version_bump_discipline_test() -> None:
    assert set(rules.GOVERNED_FILES) == {source.path for source in GOVERNED}


# --------------------------------------------------------------------------- ledger


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "ev").mkdir()
    (tmp_path / EVIDENCE).write_text("evidence body\n", encoding="utf-8")
    return tmp_path


def _scores(kind: str, value: int = 5) -> dict[str, int]:
    dims = ledger.PARENT_SCORES if kind == "parent" else ledger.CHILD_SCORES
    return dict.fromkeys(dims, value)


PATHS = {
    "parent": [
        "PROPOSED",
        "READY",
        "IN_PROGRESS",
        "CHILDREN_IN_PROGRESS",
        "INTEGRATION_PENDING",
        "VERIFIED",
        "SCORED",
        "CLOSED",
    ],
    "child": ["TODO", "READY", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED", "SCORED", "CLOSED"],
    "micro": ["PENDING", "READY", "ACTIVE", "COMPLETE"],
}


def walk(
    root: Path, card: str, kind: str, start: str, stop: str, *, scorer: str = "reviewer"
) -> list[dict[str, Any]]:
    """Ledger rows moving ``card`` along its main path from ``start`` to ``stop``."""
    path = PATHS[kind]
    rows: list[dict[str, Any]] = []
    span = path[path.index(start) : path.index(stop) + 1]
    for src, dst in pairwise(span):
        row: dict[str, Any] = {
            "ts": "2026-10-10T00:00:00Z",
            "card": card,
            "from": src,
            "to": dst,
            "actor": scorer if dst == "SCORED" else "dev",
            "commit": "abc1234",
        }
        if dst in ("COMPLETE", "CLOSED"):
            row["evidence"] = [{"path": EVIDENCE, "sha256": _sha(root / EVIDENCE)}]
        if dst == "SCORED":
            row["scores"] = _scores(kind)
        rows.append(row)
    return rows


def full_ledger(root: Path) -> list[dict[str, Any]]:
    """Every card of the synthetic plan taken legally from its initial state to CLOSED."""
    plan = cards.parse_plan_text(PLAN_TEXT)
    rows: list[dict[str, Any]] = []
    for card_id in maps.topological_order(plan):
        parent = plan.parent(card_id)
        assert parent is not None
        rows += walk(root, card_id, "parent", "PROPOSED", "IN_PROGRESS")
        for child in parent.children:
            for step in child.steps:
                rows += walk(root, step.id, "micro", "PENDING", "COMPLETE")
            rows += walk(root, child.id, "child", "TODO", "CLOSED")
        rows += walk(root, card_id, "parent", "IN_PROGRESS", "CLOSED")
    return rows


def fold(root: Path, rows: list[dict[str, Any]]) -> ledger.FoldResult:
    plan = cards.parse_plan_text(PLAN_TEXT)
    return ledger.fold_ledger(plan, [json.dumps(row) for row in rows], root)


def test_a_complete_legal_ledger_folds_clean_to_closed(root: Path) -> None:
    result = fold(root, full_ledger(root))
    assert result.findings == []
    assert {result.states[p] for p in ("TC-AAA-01", "TC-BBB-01", "TC-CCC-01")} == {"CLOSED"}


def test_a_card_without_lines_is_in_its_initial_state(root: Path) -> None:
    result = fold(root, [])
    plan = cards.parse_plan_text(PLAN_TEXT)
    assert result.state_of("TC-AAA-01") == "PROPOSED"
    assert result.state_of("TC-AAA-01-01") == "TODO"
    assert result.state_of("MS-AAA-01-01-01") == "PENDING"
    assert plan.child("TC-AAA-01-01") is not None


def card_to_scored(root: Path, card: str, kind: str) -> list[dict[str, Any]]:
    return walk(root, card, kind, PATHS[kind][0], "SCORED")


def test_the_transition_tables_match_section_6() -> None:
    parent = ledger.TRANSITIONS["parent"]
    assert parent["SCORED"] == {
        "CLOSED",
        "REROUTED",
        "BLOCKED",
        "BLOCKED_EXTERNAL",
        "DEFERRED_WITH_REASON",
    }
    assert parent["BLOCKED"] == {"READY", "BLOCKED_EXTERNAL", "DEFERRED_WITH_REASON"}
    assert parent["REROUTED"] >= {"IN_PROGRESS"} and "CLOSED" not in parent["REROUTED"]
    assert parent["CLOSED"] == set()
    child = ledger.TRANSITIONS["child"]
    assert "CLOSED" not in child["IMPLEMENTED"] and "CLOSED" not in child["READY"]
    micro = ledger.TRANSITIONS["micro"]
    assert micro["PENDING"] == {"READY", "SKIPPED_NOT_APPLICABLE"}
    assert micro["FAILED"] == {"READY"} and micro["BLOCKED"] == {"READY"}


@pytest.mark.parametrize(
    ("kind", "card", "frm", "to"),
    [
        ("child", "TC-AAA-01-01", "TODO", "CLOSED"),
        ("child", "TC-AAA-01-01", "READY", "CLOSED"),
        ("child", "TC-AAA-01-01", "IMPLEMENTED", "CLOSED"),
        ("parent", "TC-AAA-01", "PROPOSED", "CLOSED"),
        ("parent", "TC-AAA-01", "PROPOSED", "IN_PROGRESS"),
        ("micro", "MS-AAA-01-01-01", "PENDING", "COMPLETE"),
    ],
)
def test_illegal_transitions_are_rejected(
    root: Path, kind: str, card: str, frm: str, to: str
) -> None:
    rows = walk(root, card, kind, PATHS[kind][0], frm) if frm != PATHS[kind][0] else []
    rows.append({"ts": "t", "card": card, "from": frm, "to": to, "actor": "dev"})
    assert "LEDGER_ILLEGAL_TRANSITION" in codes(fold(root, rows).findings)


def test_a_line_whose_from_is_not_the_current_state_is_rejected(root: Path) -> None:
    rows = [{"ts": "t", "card": "TC-AAA-01", "from": "READY", "to": "IN_PROGRESS", "actor": "dev"}]
    assert "LEDGER_STATE_MISMATCH" in codes(fold(root, rows).findings)


def test_an_unknown_card_and_malformed_lines_are_rejected(root: Path) -> None:
    plan = cards.parse_plan_text(PLAN_TEXT)
    unknown = json.dumps(
        {"ts": "t", "card": "TC-ZZZ-01", "from": "PROPOSED", "to": "READY", "actor": "dev"}
    )
    result = ledger.fold_ledger(
        plan, [unknown, "{not json", "[1]", json.dumps({"card": "x"})], root
    )
    assert codes(result.findings) == {"LEDGER_UNKNOWN_CARD", "LEDGER_FORMAT"}


def test_a_child_cannot_close_with_a_micro_step_not_complete(root: Path) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")  # the second stays PENDING
    rows += walk(root, "TC-AAA-01-01", "child", "TODO", "CLOSED")
    assert "LEDGER_CLOSE_INCOMPLETE" in codes(fold(root, rows).findings)


def test_a_skipped_micro_step_with_a_reason_lets_the_child_close(root: Path) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    rows.append(
        {
            "ts": "t",
            "card": "MS-AAA-01-01-02",
            "from": "PENDING",
            "to": "SKIPPED_NOT_APPLICABLE",
            "actor": "dev",
            "reason": "the file already exists",
        }
    )
    rows += walk(root, "TC-AAA-01-01", "child", "TODO", "CLOSED")
    assert fold(root, rows).findings == []


def test_a_skip_without_a_reason_is_rejected(root: Path) -> None:
    rows = [
        {
            "ts": "t",
            "card": "MS-AAA-01-01-01",
            "from": "PENDING",
            "to": "SKIPPED_NOT_APPLICABLE",
            "actor": "dev",
        }
    ]
    assert "LEDGER_REASON" in codes(fold(root, rows).findings)


def test_a_deferral_needs_a_reason(root: Path) -> None:
    row = {
        "ts": "t",
        "card": "TC-AAA-01",
        "from": "PROPOSED",
        "to": "DEFERRED_WITH_REASON",
        "actor": "dev",
    }
    assert "LEDGER_REASON" in codes(fold(root, [row]).findings)
    assert fold(root, [{**row, "reason": "owner gate D-OWN-4"}]).findings == []


def test_a_parent_cannot_close_with_a_child_not_closed(root: Path) -> None:
    rows = walk(root, "TC-AAA-01", "parent", "PROPOSED", "IN_PROGRESS")
    rows += walk(root, "TC-AAA-01", "parent", "IN_PROGRESS", "CLOSED")
    assert "LEDGER_CLOSE_INCOMPLETE" in codes(fold(root, rows).findings)


def test_a_rerouted_card_cannot_close_without_a_new_cycle(root: Path) -> None:
    rows = card_to_scored(root, "TC-AAA-01-01", "child")
    rows.append(
        {"ts": "t", "card": "TC-AAA-01-01", "from": "SCORED", "to": "REROUTED", "actor": "rev"}
    )
    rows.append(
        {"ts": "t", "card": "TC-AAA-01-01", "from": "REROUTED", "to": "CLOSED", "actor": "dev"}
    )
    assert "LEDGER_ILLEGAL_TRANSITION" in codes(fold(root, rows).findings)


def test_a_rerouted_card_restarts_through_in_progress(root: Path) -> None:
    rows = card_to_scored(root, "TC-AAA-01-01", "child")
    rows.append(
        {"ts": "t", "card": "TC-AAA-01-01", "from": "SCORED", "to": "REROUTED", "actor": "rev"}
    )
    rows.append(
        {"ts": "t", "card": "TC-AAA-01-01", "from": "REROUTED", "to": "IN_PROGRESS", "actor": "dev"}
    )
    assert fold(root, rows).findings == []


def test_leaving_blocked_external_needs_unblock_evidence(root: Path) -> None:
    park = {
        "ts": "t",
        "card": "TC-AAA-01",
        "from": "PROPOSED",
        "to": "BLOCKED_EXTERNAL",
        "actor": "dev",
    }
    resume = {
        "ts": "t",
        "card": "TC-AAA-01",
        "from": "BLOCKED_EXTERNAL",
        "to": "READY",
        "actor": "dev",
    }
    assert "LEDGER_UNBLOCK_EVIDENCE" in codes(fold(root, [park, resume]).findings)
    evidenced = {**resume, "evidence": [{"path": EVIDENCE, "sha256": _sha(root / EVIDENCE)}]}
    assert fold(root, [park, evidenced]).findings == []


def test_blocked_external_cannot_close_without_unblock_evidence(root: Path) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "MS-AAA-01-01-02", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "TC-AAA-01-01", "child", "TODO", "IN_PROGRESS")
    rows.append(
        {
            "ts": "t",
            "card": "TC-AAA-01-01",
            "from": "IN_PROGRESS",
            "to": "BLOCKED_EXTERNAL",
            "actor": "dev",
        }
    )
    rows.append(
        {
            "ts": "t",
            "card": "TC-AAA-01-01",
            "from": "BLOCKED_EXTERNAL",
            "to": "CLOSED",
            "actor": "dev",
        }
    )
    found = codes(fold(root, rows).findings)
    assert {"LEDGER_UNBLOCK_EVIDENCE", "LEDGER_EVIDENCE"} <= found


@pytest.mark.parametrize("low", [3, 0])
def test_closing_with_a_mandatory_score_below_four_is_rejected(root: Path, low: int) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "MS-AAA-01-01-02", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "TC-AAA-01-01", "child", "TODO", "CLOSED")
    scored = next(r for r in rows if r["to"] == "SCORED")
    scored["scores"] = {**scored["scores"], "maintainability": low}
    assert "LEDGER_SCORE_LOW" in codes(fold(root, rows).findings)


def test_a_score_of_exactly_four_closes(root: Path) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "MS-AAA-01-01-02", "micro", "PENDING", "COMPLETE")
    rows += walk(root, "TC-AAA-01-01", "child", "TODO", "CLOSED")
    scored = next(r for r in rows if r["to"] == "SCORED")
    scored["scores"] = {**scored["scores"], "maintainability": 4}
    assert fold(root, rows).findings == []


def test_scoring_needs_every_mandatory_dimension(root: Path) -> None:
    rows = card_to_scored(root, "TC-AAA-01-01", "child")
    del rows[-1]["scores"]["scope_discipline"]
    assert "LEDGER_SCORES" in codes(fold(root, rows).findings)
    rows = card_to_scored(root, "TC-AAA-01-01", "child")
    del rows[-1]["scores"]
    assert "LEDGER_SCORES" in codes(fold(root, rows).findings)


def test_a_card_cannot_be_scored_by_its_author(root: Path) -> None:
    rows = card_to_scored(root, "TC-AAA-01-01", "child")
    rows[-1]["actor"] = "dev"
    assert "LEDGER_SELF_SCORED" in codes(fold(root, rows).findings)


def test_a_parent_cannot_start_before_its_dependencies_are_closed(root: Path) -> None:
    rows = walk(root, "TC-BBB-01", "parent", "PROPOSED", "IN_PROGRESS")
    assert "LEDGER_DEPENDENCY_OPEN" in codes(fold(root, rows).findings)


def test_a_dependency_on_a_child_is_checked_on_the_child(root: Path) -> None:
    rows = walk(root, "TC-CCC-01", "parent", "PROPOSED", "IN_PROGRESS")
    assert "LEDGER_DEPENDENCY_OPEN" in codes(fold(root, rows).findings)


EVIDENCE_DEFECTS = ["missing", "empty", "no_sha", "short_sha", "wrong_sha", "escapes", "absolute"]


@pytest.mark.parametrize("defect", EVIDENCE_DEFECTS)
def test_completing_with_defective_evidence_is_rejected(root: Path, defect: str) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    entry = rows[-1]["evidence"][0]
    if defect == "missing":
        entry["path"] = "ev/absent.txt"
    elif defect == "empty":
        (root / "ev" / "empty.txt").write_bytes(b"")
        entry.update(path="ev/empty.txt", sha256=_sha(root / "ev" / "empty.txt"))
    elif defect == "no_sha":
        del entry["sha256"]
    elif defect == "short_sha":
        entry["sha256"] = "abc123"
    elif defect == "wrong_sha":
        entry["sha256"] = "0" * 64
    elif defect == "escapes":
        entry["path"] = "../outside.txt"
    else:
        entry["path"] = str((root / EVIDENCE).resolve())
    assert "LEDGER_EVIDENCE" in codes(fold(root, rows).findings), defect


def test_completing_without_any_evidence_is_rejected(root: Path) -> None:
    rows = walk(root, "MS-AAA-01-01-01", "micro", "PENDING", "COMPLETE")
    del rows[-1]["evidence"]
    assert "LEDGER_EVIDENCE" in codes(fold(root, rows).findings)


def test_a_bad_line_changes_no_state(root: Path) -> None:
    rows = [{"ts": "t", "card": "TC-AAA-01", "from": "PROPOSED", "to": "CLOSED", "actor": "dev"}]
    assert fold(root, rows).state_of("TC-AAA-01") == "PROPOSED"


# --------------------------------------------------------------------------- state.yaml


def _state(**statuses: str) -> dict[str, Any]:
    return {
        "active_work_item": {"id": "G7-W90", "status": statuses.get("g7_w90", "IN_PROGRESS")},
        "next_ready_items": [{"id": "G7-W91", "status": statuses.get("g7_w91", "PENDING")}],
    }


def state_findings(root: Path, rows: list[dict[str, Any]], state: Any) -> list[Finding]:
    plan = cards.parse_plan_text(PLAN_TEXT)
    result = ledger.fold_ledger(plan, [json.dumps(r) for r in rows], root)
    return ledger.check_state_items(plan, result, state)


def test_a_work_item_complete_with_an_open_mapped_parent_is_rejected(root: Path) -> None:
    findings = state_findings(root, [], _state(g7_w90="COMPLETE"))
    assert "STATE_ITEM_COMPLETE_OPEN" in codes(findings)


def test_a_work_item_complete_once_all_mapped_parents_are_closed(root: Path) -> None:
    rows = full_ledger(root)
    assert errors(state_findings(root, rows, _state(g7_w90="COMPLETE", g7_w91="COMPLETE"))) == []


def test_one_open_parent_of_several_blocks_completion(root: Path) -> None:
    rows = [r for r in full_ledger(root) if not r["card"].startswith(("TC-BBB", "MS-BBB"))]
    findings = state_findings(root, rows, _state(g7_w90="COMPLETE"))
    assert [f.message for f in errors(findings)] == [
        "work item COMPLETE but mapped parent TC-BBB-01 is PROPOSED"
    ]


def test_a_pending_work_item_is_not_held_to_its_parents(root: Path) -> None:
    assert errors(state_findings(root, [], _state())) == []


def test_an_unregistered_item_is_a_warning_not_an_error(root: Path) -> None:
    findings = state_findings(
        root, [], {"active_work_item": {"id": "G1-W01", "status": "COMPLETE"}}
    )
    assert {f.rule for f in findings} == {"STATE_ITEM_UNKNOWN"}
    assert errors(findings) == []


def test_the_real_state_file_loads() -> None:
    state = ledger.load_state(REPO_ROOT / "project" / "state.yaml")
    assert isinstance(state, dict) and state["next_ready_items"]


# --------------------------------------------------------------------------- mutation checks


def test_mutating_an_id_dependency_transition_or_hash_makes_the_lint_fail(root: Path) -> None:
    plan_path = root / "PLAN.md"
    ledger_path = root / "loop-status.jsonl"

    def run(plan_text: str, rows: list[dict[str, Any]]) -> list[Finding]:
        plan_path.write_text(plan_text, encoding="utf-8")
        ledger_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return lint.lint_files(plan_path, ledger_path, None, root)

    rows = full_ledger(root)
    assert errors(run(PLAN_TEXT, rows)) == []  # the unmutated pair is clean

    assert errors(run(mutate("id: TC-BBB-01\n", "id: TC-AAA-01\n"), rows))  # an ID
    assert errors(run(mutate("depends: [TC-AAA-01]", "depends: [TC-AAA-99]"), rows))  # a dependency
    mutated = copy.deepcopy(rows)
    next(r for r in mutated if r["card"] == "TC-AAA-01-01" and r["to"] == "CLOSED")["to"] = "SCORED"
    assert errors(run(PLAN_TEXT, mutated))  # a transition
    mutated = copy.deepcopy(rows)
    mutated[-1]["evidence"][0]["sha256"] = "f" * 64
    assert errors(run(PLAN_TEXT, mutated))  # an evidence hash
    (root / EVIDENCE).write_text("tampered\n", encoding="utf-8")
    assert errors(run(PLAN_TEXT, rows))  # the evidence file itself


# --------------------------------------------------------------------------- maps


def _plan() -> cards.Plan:
    return cards.parse_plan_text(PLAN_TEXT)


def test_every_map_carries_the_non_authority_header() -> None:
    for name, text in maps.generate_maps(_plan(), "plans/reseal-and-refresh/PLAN.md").items():
        head = text.splitlines()[:3]
        if name.endswith(".csv"):
            head = [line.removeprefix("# ") for line in head]
        assert head == [
            "authoritative_plan: plans/reseal-and-refresh/PLAN.md",
            "artifact_role: analysis_or_evidence_only",
            "execution_authority: false",
        ], name


def test_maps_regenerate_byte_identically_twice(tmp_path: Path) -> None:
    first = maps.write_maps(_plan(), "PLAN.md", tmp_path / "one")
    second = maps.write_maps(cards.parse_plan_text(PLAN_TEXT), "PLAN.md", tmp_path / "two")
    assert [p.name for p in first] == list(maps.MAP_FILES)
    for left, right in zip(first, second, strict=True):
        assert left.read_bytes() == right.read_bytes()
        assert b"\r" not in left.read_bytes()
    again = maps.write_maps(_plan(), "PLAN.md", tmp_path / "one")  # overwrite in place
    for left, right in zip(first, again, strict=True):
        assert left.read_bytes() == right.read_bytes()


def _csv_rows(text: str) -> list[list[str]]:
    import csv

    return list(csv.reader(line for line in text.splitlines() if not line.startswith("#")))


def test_the_traceability_map_has_one_row_per_micro_step() -> None:
    plan = _plan()
    rows = _csv_rows(maps.traceability_csv(plan, "PLAN.md"))
    assert rows[0] == ["requirement", "parent", "child", "micro", "op", "target", "done_when"]
    expected = sum(len(p.reqs) * len(c.steps) for p in plan.parents for c in p.children)
    ccc = [r for r in rows[1:] if r[1] == "TC-CCC-01"]
    assert len(rows) - 1 == expected
    assert [
        "REQ-AAA-01",
        "TC-AAA-01",
        "TC-AAA-01-01",
        "MS-AAA-01-01-02",
        "create",
        "docs/synthetic/one/b.md",
        "file exists",
    ] in rows
    # a parent with two requirements appears under each
    assert {r[0] for r in ccc} == {"REQ-CCC-01", "REQ-CCC-02"}


def test_the_dag_map_orders_dependencies_first() -> None:
    document = yaml.safe_load(maps.dag_yaml(_plan(), "PLAN.md"))
    assert document["execution_authority"] is False
    order = document["topological_order"]
    assert order.index("TC-AAA-01") < order.index("TC-BBB-01")
    assert order.index("TC-AAA-01") < order.index("TC-CCC-01")
    nodes = {n["id"]: n for n in document["nodes"]}
    assert nodes["TC-CCC-01"]["depends"] == ["TC-AAA-01"] and nodes["TC-CCC-01"]["governed"] is True


def test_the_dependency_matrix_marks_direct_and_transitive() -> None:
    text = mutate("depends: [TC-AAA-01]", "depends: [TC-AAA-01, TC-CCC-01]")
    rows = _csv_rows(maps.dependency_matrix_csv(cards.parse_plan_text(text), "PLAN.md"))
    header = rows[0]
    by_card = {r[0]: dict(zip(header[1:], r[1:], strict=True)) for r in rows[1:]}
    assert by_card["TC-BBB-01"]["TC-AAA-01"] == "1" and by_card["TC-BBB-01"]["TC-CCC-01"] == "1"
    assert by_card["TC-AAA-01"]["TC-BBB-01"] == ""
    chained = mutate("depends: [TC-AAA-01]", "depends: [TC-CCC-01]")
    rows = _csv_rows(maps.dependency_matrix_csv(cards.parse_plan_text(chained), "PLAN.md"))
    by_card = {r[0]: dict(zip(rows[0][1:], r[1:], strict=True)) for r in rows[1:]}
    assert by_card["TC-BBB-01"]["TC-AAA-01"] == "t" and by_card["TC-BBB-01"]["TC-CCC-01"] == "1"


def test_the_file_lock_map_names_parallel_collisions() -> None:
    clash = mutate(
        "paths: {write: [docs/synthetic/two/]}", "paths: {write: [docs/synthetic/three/deep/]}"
    )
    rows = _csv_rows(maps.file_lock_csv(cards.parse_plan_text(clash), "PLAN.md"))
    by_path = {(r[0], r[1]): r[4] for r in rows[1:]}
    assert by_path[("docs/synthetic/three/deep/", "TC-BBB-01")] == "TC-CCC-01"
    assert by_path[("docs/synthetic/one/", "TC-AAA-01")] == ""
    clean = _csv_rows(maps.file_lock_csv(_plan(), "PLAN.md"))
    assert all(r[4] == "" for r in clean[1:])


# --------------------------------------------------------------------------- command line


def test_the_cli_lint_exit_codes(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan = root / "PLAN.md"
    plan.write_text(PLAN_TEXT, encoding="utf-8")
    argv = ["lint", "--root", str(root), "--plan", str(plan), "--state", str(root / "no.yaml")]
    assert cli.main(argv) == 0
    plan.write_text(mutate("id: TC-BBB-01\n", "id: TC-AAA-01\n"), encoding="utf-8")
    assert cli.main(argv) == 1
    assert "ID_DUPLICATE" in capsys.readouterr().out
    assert cli.main(["lint", "--root", str(root), "--plan", str(root / "absent.md")]) == 2


def test_the_cli_maps_writes_the_four_files(root: Path) -> None:
    plan = root / "PLAN.md"
    plan.write_text(PLAN_TEXT, encoding="utf-8")
    out = root / "maps"
    assert cli.main(["maps", "--root", str(root), "--plan", str(plan), "--out", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == sorted(maps.MAP_FILES)
    assert "authoritative_plan: PLAN.md" in (out / "dag.yaml").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- the real plan


def _real_plan_path() -> Path:
    override = os.environ.get("PLAN_LINT_PLAN")
    return Path(override) if override else REPO_ROOT / lint.DEFAULT_PLAN


def test_the_real_plan_lints_clean() -> None:
    plan_path = _real_plan_path()
    if not plan_path.is_file():
        pytest.skip(f"real plan not present yet ({plan_path}); only the fixtures were linted")
    ledger_path = REPO_ROOT / lint.DEFAULT_LEDGER
    findings = lint.lint_files(plan_path, ledger_path, REPO_ROOT / lint.DEFAULT_STATE, REPO_ROOT)
    assert [f.render() for f in errors(findings)] == []
