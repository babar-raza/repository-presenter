"""The queue has one source: section 27.9's text is what `next_ready_items` carries."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from support import REPO_ROOT

RESEARCH = REPO_ROOT / "docs" / "RESEARCH_AND_GUIDELINES.md"
STATE = REPO_ROOT / "project" / "state.yaml"
LANE_B = REPO_ROOT / "project" / "lanes" / "lane-b.yaml"
NL = chr(10)


def queue_entries() -> list[dict[str, Any]]:
    """The entries section 27.9 states verbatim, from its one YAML block."""
    section = RESEARCH.read_text("utf-8").split("### 27.9 Queue", 1)[1].split(NL + "### ", 1)[0]
    blocks = re.findall(r"```yaml\n(.*?)```", section, re.DOTALL)
    assert len(blocks) == 1, "section 27.9 states the queue in exactly one YAML block"
    entries = yaml.safe_load(blocks[0])
    assert isinstance(entries, list) and entries
    return entries


def state() -> dict[str, Any]:
    loaded = yaml.safe_load(STATE.read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_every_queued_item_carries_section_27_9s_text_verbatim() -> None:
    """A purpose that drifts from section 27.9 is the queue disagreeing with itself.

    Loop-prompt section 2: section 27.9 is the single source for queued text, and a non-active
    entry whose purpose differs takes section 27.9's. Measured 2026-09-06: G4-W10's had drifted
    by 245 characters, which nothing would have caught.
    """
    queued = {item["id"]: item for item in state()["next_ready_items"]}
    drifted = [
        entry["id"]
        for entry in queue_entries()
        if entry["id"] in queued and queued[entry["id"]]["purpose"] != entry["purpose"]
    ]
    assert drifted == [], f"these entries differ from section 27.9's text: {drifted}"


EVIDENCE_BUILD = REPO_ROOT / "evidence" / "build"
# A manifest's top-level record says ACCEPTED; an item that closed at its own time box inside a
# gate still open says COMPLETE_AT_ITS_TIME_BOX (the G3 manifest's second_pass block, G3-W04).
ACCEPTING_STATUSES = frozenset({"ACCEPTED", "COMPLETE_AT_ITS_TIME_BOX"})


def _acceptance_records(node: Any) -> Iterator[dict[str, Any]]:
    """Every record in a manifest, at any depth, that names a work item and its status."""
    if isinstance(node, dict):
        if "work_item" in node and "work_item_status" in node:
            yield node
        for value in node.values():
            yield from _acceptance_records(value)
    elif isinstance(node, list):
        for value in node:
            yield from _acceptance_records(value)


def accepted_work_items(build_root: Path = EVIDENCE_BUILD) -> set[str]:
    """Every work item a gate's evidence manifest records as accepted, at any gate.

    The record is the manifest's own (``work_item``, ``work_item_status``) pair plus its
    ``previous_items`` - and, since PHASE1/F9, the same pair wherever it sits in the manifest: an
    item whose gate stays open when it closes writes its acceptance as a nested block (G3-W04's
    ``second_pass``), which this read the top level past for four days.
    """
    accepted: set[str] = set()
    for manifest in sorted(build_root.rglob("manifest.json")):
        record = json.loads(manifest.read_text("utf-8"))
        for entry in _acceptance_records(record):
            if entry["work_item_status"] in ACCEPTING_STATUSES and entry["work_item"]:
                accepted.add(entry["work_item"])
        accepted.update(record.get("previous_items", []))
    return accepted


def test_an_entry_section_27_9_states_is_queued_active_or_already_accepted() -> None:
    """Section 27.9's own rule: an entry is absent only if it is in none of the three places.

    The third place is the accepted evidence, which is the gate manifests - not `accepted_gates`.
    An item accepted inside a gate that is still open, as G3-W01 was on 2026-09-06 while G3 waits
    for its v1 freeze, is accounted for there and nowhere else.
    """
    cursor = state()
    known = {item["id"] for item in cursor["next_ready_items"]}
    known.add(cursor["active_work_item"]["id"])
    known |= accepted_work_items()
    known |= {
        entry["id"]
        for entry in queue_entries()
        if entry["id"].split("-")[0] in {gate.split("_")[0] for gate in cursor["accepted_gates"]}
    }
    missing = [entry["id"] for entry in queue_entries() if entry["id"] not in known]
    assert missing == [], f"section 27.9 states these but state.yaml does not carry them: {missing}"


def test_a_completed_queue_entry_is_backed_by_a_gate_manifests_acceptance_record() -> None:
    """A ``COMPLETE`` status in next_ready_items is a claim; a gate manifest is its evidence.

    PHASE1/F9. G3-W04 closed at its time box on 2026-09-07 and its acceptance was written as
    the G3 manifest's ``second_pass`` block, because the schema then admitted only PENDING or
    BLOCKED_BY_GATE for a queued entry (the block's own ``state_yaml_note``) - so the cursor
    read PENDING for four days of work that was done. The status exists now; this ties every
    use of it to an acceptance record on disk, so it is never written ahead of the evidence.
    """
    completed = [item["id"] for item in state()["next_ready_items"] if item["status"] == "COMPLETE"]
    assert "G3-W04" in completed, "G3-W04's second pass is recorded complete in the G3 manifest"
    unbacked = sorted(set(completed) - accepted_work_items())
    assert unbacked == [], f"marked COMPLETE with no gate manifest acceptance record: {unbacked}"


def test_accepted_work_items_reads_an_acceptance_record_at_any_depth(tmp_path: Path) -> None:
    """A record inside a block counts exactly as the top-level one; a non-accepting status never."""
    (tmp_path / "G7_EXAMPLE").mkdir()
    (tmp_path / "G7_EXAMPLE" / "manifest.json").write_text(
        json.dumps(
            {
                "work_item": "G7-W01",
                "work_item_status": "ACCEPTED",
                "previous_items": ["G7-W00"],
                "second_pass": {
                    "work_item": "G7-W02",
                    "work_item_status": "COMPLETE_AT_ITS_TIME_BOX",
                    "cohort": [{"repository": "owner/name", "outcome": "NOT_SEALED"}],
                },
                "third_pass": {"work_item": "G7-W03", "work_item_status": "IN_PROGRESS"},
                "notes": [{"work_item": "G7-W04", "work_item_status": "ACCEPTED"}],
            }
        ),
        encoding="utf-8",
    )
    assert accepted_work_items(tmp_path) == {"G7-W00", "G7-W01", "G7-W02", "G7-W04"}


def test_lane_bs_items_never_re_enter_the_queue() -> None:
    """Lane B works its items on its own branch; the primary must not take them."""
    lane = yaml.safe_load(LANE_B.read_text("utf-8"))
    owned = {item["id"] for item in lane["items"]}
    cursor = state()
    queued = {item["id"] for item in cursor["next_ready_items"]}
    assert owned & queued == set(), (
        f"lane B's items are in next_ready_items: {sorted(owned & queued)}"
    )
    assert cursor["active_work_item"]["id"] not in owned
