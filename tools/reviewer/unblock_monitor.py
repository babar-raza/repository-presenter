"""Mechanized lane-unblock detector (runs under the Monitor tool; owner/reviewer tooling).

Root cause this exists to remove: on 2026-09-06, G4-W17 arrival item (0) landed at 12:30 and item
(1) (subsuming item 15) at 12:37 — both known, in advance, to make specific lane dispositions
re-runnable — and neither lane was re-spawned until a human noticed by hand at 13:42, over an hour
later. The trigger "when item N lands, re-run lane X's disposition Y" lived only in the reviewer's
prose memory and the reviewer's own cron did not fire reliably across an idle gap. This script makes
the trigger mechanical: it parses which arrival items have landed from RESEARCH_AND_GUIDELINES.md's
section 31 (self-contained; needs no cooperation from the loop), checks a maintained table of which
landed items each known disposition needs, and emits one line the instant a disposition becomes
newly re-runnable — an event, not a scheduled poll, so it does not depend on cron cadence at all.

Durable upgrade this stands in for (not yet built, needs loop-prompt cooperation): when the loop
lands a G4-W17 arrival item, it appends a line to
evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl naming exactly what it unblocks (it already
has this knowledge — the item's own bracket citation names the lane and repository). That removes
the ITEM_UNLOCKS table below, which is honest, bounded curation, not full automation, and needs a
manual entry for every new G4-W17 item. Until that lands, this script's fallback (regex over section
31 text) is the safety net; keep both once the ledger exists.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESEARCH = REPO / "docs" / "RESEARCH_AND_GUIDELINES.md"
LEDGER = REPO / "evidence" / "build" / "G4_MULTI_LANGUAGE_COHORTS" / "unblocked.jsonl"

# item number -> [(lane file stem, repository substring), ...] it is known (2026-09-06) to unblock.
# Maintain this by hand as new arrival items are proposed and landed — see the durable-upgrade note
# above for why this is curation, not automation, and how to remove the need for it.
ITEM_UNLOCKS: dict[int, list[tuple[str, str]]] = {
    0: [
        ("lane-b", "Aspose.Cells-FOSS-for-Cpp"), ("lane-b", "Aspose.Email-FOSS-for-Cpp"),
        ("lane-b", "Aspose.PDF-FOSS-for-Cpp"), ("lane-b", "Aspose.Slides-FOSS-for-Cpp"),
        ("lane-d", "Aspose.Cells-FOSS-for-Rust"),
    ],
    1: [
        ("lane-b", "Aspose.Email-FOSS-for-Cpp"),
        ("lane-b", "Aspose.3D-FOSS-for-TypeScript"),  # item 1's ORIGINAL subject, missed here for 6h
    ],
    2: [("lane-b", "Aspose.Cells-FOSS-for-TypeScript")],  # the MAX_PATH fix item 1's own text names
    5: [("lane-d", "Aspose.Cells-FOSS-for-Rust")],  # Verify-the-install, Rust's `use` syntax
    11: [("lane-d", "Aspose.Cells-FOSS-for-Rust")],
    12: [("lane-c", "Java")],  # all four Java repositories
    20: [("lane-b", "Aspose.Cells-FOSS-for-Cpp")],
    21: [("lane-b", "Aspose.Slides-FOSS-for-Cpp")],
    24: [
        ("lane-b", "Aspose.PDF-FOSS-for-Cpp"), ("lane-b", "Aspose.Cells-FOSS-for-Cpp"),
        ("lane-b", "Aspose.Email-FOSS-for-Cpp"), ("lane-b", "Aspose.Slides-FOSS-for-Cpp"),
    ],
    25: [("lane-b", "Aspose.Email-FOSS-for-Cpp")],
    26: [("lane-b", "Aspose.Slides-FOSS-for-Cpp")],
}

# Matches "item N landed", "item N declined ...; closed with a mutation test" (item 1's actual shape
# on 2026-09-06: the literal proposal was declined but its underlying defect was fixed under a
# different mechanism), and a comma/and-separated list of any length ("items 8, 9 and 12 landed
# together" — the exact phrasing that hid item 12 from this monitor for over four hours on
# 2026-09-06, silently costing lane C its whole re-run window; fixed once found). Free text is
# inherently fuzzy here; this errs toward over-notifying (a false positive costs one wasted check)
# rather than under-notifying (a false negative costs another silent multi-hour gap).
LANDED_CLAUSE_RE = re.compile(
    r"G4-W17 arrival item[s]?\s*((?:\(?\d+\)?[\s,]*(?:and)?[\s,]*)+)"
    r"[^.\n]{0,80}?\b(?:land(?:ed|s)|closed with a mutation test)\b",
    re.I,
)
NUMBER_RE = re.compile(r"\d+")


def landed_items() -> set[int]:
    if not RESEARCH.exists():
        return set()
    text = RESEARCH.read_text(encoding="utf-8", errors="replace")
    body = text[text.find("## 31"):]
    found: set[int] = set()
    for m in LANDED_CLAUSE_RE.finditer(body):
        for num in NUMBER_RE.findall(m.group(1)):
            found.add(int(num))
    return found


def main() -> None:
    """Emit one line per (landed item, its known unlocks) the first time each item is seen landed.
    Deliberately does NOT try to confirm the disposition is still open — that requires reading free
    prose reliably, which is fragile (see the module docstring); a human or the reviewer's next wake
    confirms in under a minute. The point is that the notification arrives at all, immediately."""
    reported: set[int] = set()
    while True:
        try:
            for item in sorted(landed_items() - reported):
                unlocks = ITEM_UNLOCKS.get(item)
                if not unlocks:
                    continue
                reported.add(item)
                targets = ", ".join(f"{lane}:{repo}" for lane, repo in unlocks)
                print(f"UNBLOCKED item({item}) landed -> check and re-run: {targets}", flush=True)
        except Exception as exc:
            print(f"MONITOR_ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()
