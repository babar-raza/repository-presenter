"""The register: nothing logged can be dropped.

``docs/DEFECT_INDEX.md`` logs reviewer defects (``REV-Vn-nn``) and register items (``REG-nn``);
``project/state.yaml`` carries the work (``next_ready_items``) and the owner questions
(``owner_items``); ``docs/EXECUTION_STATE_MACHINE.md`` names the work items. A defect with no
work item, a work item the plan never mentions, or an owner question with no resume predicate is
how a finding gets dropped between sessions. These tests fail on each of those, and each rule has
a negative control that proves the check fires.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from support import REPO_ROOT

INDEX = REPO_ROOT / "docs" / "DEFECT_INDEX.md"
STATE = REPO_ROOT / "project" / "state.yaml"
PLAN = REPO_ROOT / "docs" / "EXECUTION_STATE_MACHINE.md"
SUPERVISION = REPO_ROOT / "docs" / "SUPERVISION.md"

STATUS = re.compile(r"^(OPEN|PENDING|OWNER|WRONG|FIXED\(#\d+(?:,#\d+)*\))$")
WORK_LINE = re.compile(r"^\*\*Work item\*\* (\S+) · \*\*Register status\*\* (\S+) · (.*)$", re.M)
REG_ROW = re.compile(r"^\| (REG-\d\d) \| .* \| (\S+) \| (\S+) \|$", re.M)
WORK_ID = re.compile(r"^G[0-7]-W\d\d$")
OWNER_ID = re.compile(r"^OWNER-\d\d$")
REGISTER_PREFIX = "REGISTER: "


def load_state() -> dict[str, Any]:
    loaded = yaml.safe_load(STATE.read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def known_ids(state: dict[str, Any]) -> tuple[set[str], set[str]]:
    """``(work item ids, owner item ids)`` the cursor carries."""
    work = {item["id"] for item in state["next_ready_items"]}
    work.add(state["active_work_item"]["id"])
    owners = {item["id"] for item in state["owner_items"]}
    return work, owners


def rev_blocks(index_text: str) -> dict[str, str]:
    """Each ``### `mechanism` (REV-Vn-nn)`` entry's text, keyed by its REV id."""
    blocks: dict[str, str] = {}
    chunks = re.split(r"^### ", index_text, flags=re.M)
    for chunk in chunks:
        heading = chunk.split("\n", 1)[0]
        match = re.search(r"\((REV-V\d-\d\d)\)\s*$", heading)
        if match:
            blocks[match.group(1)] = chunk
    return blocks


def check_status(
    label: str, work: str, status: str, text: str, state_work: set[str], state_owner: set[str]
) -> list[str]:
    """Problems with one register line, or an empty list."""
    problems: list[str] = []
    if not STATUS.match(status):
        problems.append(
            f"{label}: status {status!r} is not OPEN, PENDING, OWNER, WRONG or FIXED(#PR)"
        )
    if not (WORK_ID.match(work) and work in state_work) and not (
        OWNER_ID.match(work) and work in state_owner
    ):
        problems.append(
            f"{label}: work item {work!r} is in neither next_ready_items nor owner_items"
        )
    if status == "PENDING" and work not in state_work:
        problems.append(
            f"{label}: PENDING needs an owner lane (a next_ready_items entry), got {work!r}"
        )
    if status == "OWNER":
        named = set(re.findall(r"OWNER-\d\d", work + " " + text))
        if not named or not named <= state_owner:
            problems.append(
                f"{label}: OWNER status needs an existing owner_items question, "
                f"found {sorted(named)}"
            )
    return problems


def check_index(index_text: str, state_work: set[str], state_owner: set[str]) -> list[str]:
    problems: list[str] = []
    blocks = rev_blocks(index_text)
    if not blocks:
        return ["DEFECT_INDEX has no REV entries; the check would hold vacuously"]
    for rev_id, block in blocks.items():
        lines = WORK_LINE.findall(block)
        if len(lines) != 1:
            problems.append(
                f"{rev_id}: needs exactly one Work item / Register status line, found {len(lines)}"
            )
            continue
        work, status, text = lines[0]
        problems += check_status(rev_id, work, status, text, state_work, state_owner)
    rows = REG_ROW.findall(index_text)
    reg_ids = re.findall(r"^\| (REG-\d\d) \|", index_text, re.M)
    if len(rows) != len(reg_ids):
        problems.append("a REG row does not end with `| work item | status |`")
    for rid, work, status in rows:
        problems += check_status(rid, work, status, "", state_work, state_owner)
    return problems


def check_state(state: dict[str, Any], plan_text: str) -> list[str]:
    problems: list[str] = []
    for item in state["next_ready_items"]:
        if not str(item.get("owner", "")).startswith(REGISTER_PREFIX):
            continue
        if item["id"] not in plan_text:
            problems.append(f"{item['id']}: a register work item the plan never names")
        purpose = item["purpose"]
        if "Exit predicate:" not in purpose:
            problems.append(f"{item['id']}: purpose states no 'Exit predicate:'")
        if item["status"] != "COMPLETE" and "Depends on:" not in purpose:
            problems.append(f"{item['id']}: purpose states no 'Depends on:'")
    work, _ = known_ids(state)
    for owner in state["owner_items"]:
        if not str(owner.get("resume_predicate", "")).strip():
            problems.append(f"{owner['id']}: owner item has no resume predicate")
        if not str(owner.get("summary", "")).strip():
            problems.append(f"{owner['id']}: owner item states no question")
        recorded_here = str(owner.get("note", "")).startswith("Recorded by the register PR")
        for consumer in owner.get("consumed_by", []) if recorded_here else []:
            if WORK_ID.match(consumer) and consumer not in work:
                problems.append(f"{owner['id']}: consumed_by {consumer} is not a work item")
    return problems


# --- the real register -------------------------------------------------------------------------


def test_every_logged_defect_has_a_work_item_and_a_valid_status() -> None:
    work, owners = known_ids(load_state())
    problems = check_index(INDEX.read_text("utf-8"), work, owners)
    assert problems == [], "\n".join(problems)


def test_every_register_work_item_is_named_in_the_plan_and_every_owner_item_asks_a_question() -> (
    None
):
    problems = check_state(load_state(), PLAN.read_text("utf-8"))
    assert problems == [], "\n".join(problems)


def test_no_register_entry_is_marked_resolved_without_reverification() -> None:
    """A FIXED status names the merged fix; the entry itself stays Open until reverified."""
    resolved = INDEX.read_text("utf-8").split("\n## Resolved", 1)[1].split("\n## ", 1)[0]
    assert not re.findall(r"\(REV-V\d-\d\d\)", resolved), "a REV entry moved to Resolved"


def test_the_supervisor_sweep_reads_the_register() -> None:
    text = SUPERVISION.read_text("utf-8")
    assert (
        "Register integrity" in text and "owner_items" in text and "test_register_integrity" in text
    )


# --- negative controls: each rule fires --------------------------------------------------------

WORK = {"G6-W05", "G3-W06"}
OWNERS = {"OWNER-13"}
ENTRY = (
    "### `a.b` (REV-V1-01)\n\ntext\n\n**Id** REV-V1-01 · x\n\n"
    "**Work item** G6-W05 · **Register status** FIXED(#241) · detail.\n"
)


def test_a_clean_entry_passes() -> None:
    assert check_index(ENTRY, WORK, OWNERS) == []


def test_an_entry_without_a_work_item_line_is_reported() -> None:
    bare = ENTRY.split("**Work item**")[0]
    assert any("exactly one" in p for p in check_index(bare, WORK, OWNERS))


def test_an_unknown_work_item_or_status_is_reported() -> None:
    assert any("neither" in p for p in check_index(ENTRY.replace("G6-W05", "G9-W99"), WORK, OWNERS))
    assert any(
        "not OPEN" in p for p in check_index(ENTRY.replace("FIXED(#241)", "DONE"), WORK, OWNERS)
    )
    assert any(
        "not OPEN" in p for p in check_index(ENTRY.replace("FIXED(#241)", "FIXED"), WORK, OWNERS)
    )


def test_pending_needs_an_owner_lane_and_owner_needs_a_question() -> None:
    pending_on_owner = ENTRY.replace("G6-W05", "OWNER-13").replace("FIXED(#241)", "PENDING")
    assert any("owner lane" in p for p in check_index(pending_on_owner, WORK, OWNERS))
    owner_without_question = ENTRY.replace("FIXED(#241)", "OWNER")
    assert any("OWNER status" in p for p in check_index(owner_without_question, WORK, OWNERS))
    owner_with_question = ENTRY.replace("FIXED(#241)", "OWNER").replace(
        "detail.", "OWNER-13 decides."
    )
    assert check_index(owner_with_question, WORK, OWNERS) == []


def test_a_reg_row_without_a_known_work_item_is_reported() -> None:
    table = ENTRY + "\n| REG-01 | an item | G7-W07 | PENDING |\n"
    assert any("REG-01" in p for p in check_index(table, WORK, OWNERS))


def test_a_register_item_missing_from_the_plan_or_without_predicates_is_reported() -> None:
    state: dict[str, Any] = {
        "next_ready_items": [
            {
                "id": "G6-W05",
                "status": "PENDING",
                "owner": REGISTER_PREFIX + "x",
                "purpose": "Depends on: a. Exit predicate: b.",
            },
            {
                "id": "G3-W06",
                "status": "PENDING",
                "owner": REGISTER_PREFIX + "x",
                "purpose": "nothing stated",
            },
        ],
        "active_work_item": {"id": "G4-W17"},
        "owner_items": [
            {
                "id": "OWNER-13",
                "summary": "q",
                "resume_predicate": "",
                "consumed_by": ["G6-W99"],
                "note": "Recorded by the register PR; x",
            },
        ],
    }
    problems = check_state(state, "the plan names G6-W05 only")
    joined = "\n".join(problems)
    assert "G3-W06: a register work item the plan never names" in joined
    assert "G3-W06: purpose states no 'Exit predicate:'" in joined
    assert "G3-W06: purpose states no 'Depends on:'" in joined
    assert "OWNER-13: owner item has no resume predicate" in joined
    assert "consumed_by G6-W99" in joined
    assert not any(p.startswith("G6-W05") for p in problems)


def test_the_real_register_files_exist() -> None:
    for path in (INDEX, STATE, PLAN, SUPERVISION):
        assert isinstance(path, Path) and path.exists(), path
