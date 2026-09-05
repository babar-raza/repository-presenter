"""The queue has one source: section 27.9's text is what `next_ready_items` carries."""

from __future__ import annotations

import re
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


def test_an_entry_section_27_9_states_is_queued_active_or_already_accepted() -> None:
    """Section 27.9's own rule: an entry is absent only if it is in none of the three places."""
    cursor = state()
    known = {item["id"] for item in cursor["next_ready_items"]}
    known.add(cursor["active_work_item"]["id"])
    accepted = set(cursor["accepted_gates"])
    missing = [
        entry["id"]
        for entry in queue_entries()
        if entry["id"] not in known and entry["id"].split("-")[0] not in {g[:2] for g in accepted}
    ]
    assert missing == [], f"section 27.9 states these but state.yaml does not carry them: {missing}"


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
