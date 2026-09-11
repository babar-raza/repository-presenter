"""Mechanized lane-unblock detector (runs under the Monitor tool; owner/reviewer tooling).

Root cause this exists to remove: on 2026-09-06, G4-W17 arrival items landed that were known, in
advance, to make specific lane dispositions re-runnable — and no lane was re-spawned until a human
noticed by hand over an hour later. The trigger "when item N lands, re-run lane X" must be
mechanical, an event rather than a scheduled poll.

PHASE1/F1 (2026-09-11) retired the hand-maintained ITEM_UNLOCKS table this module used to carry.
The table froze at item 33 while the arrival list reached 49, and the audit that was meant to catch
that compared the table against one prose phrasing the list had abandoned — a confident false OK.
Its own docstring had already named the durable design: the structured ledger at
evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl, one JSON object per landing,
`{"item": int, "landed_at": iso, "unlocks": [[lane, repository], ...]}`, appended by the executor
in the landing commit. That ledger is now the single source of unlock targets. The section-31
prose regex remains only as a landed-detector safety net: an item it sees landed that has no
ledger record is REPORTED as a ledger gap — never silently dropped (the old code's
`continue`-before-`reported.add` re-dropped such items every 60 s forever).

Section 31 itself moved to docs/DECISION_LOG.md on 2026-09-08; the old code kept reading the stub
left in RESEARCH_AND_GUIDELINES.md and its regex half went permanently blind. The whole decision
log is section 31, so the scan takes the full committed file — no heading slice to go stale.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECISION_LOG = "docs/DECISION_LOG.md"
LEDGER = REPO / "evidence" / "build" / "G4_MULTI_LANGUAGE_COHORTS" / "unblocked.jsonl"

# Matches "item N landed", "item N ... live-verified", and comma/and-separated lists of any length
# ("items 8, 9 and 12 landed together" — the exact phrasing that hid item 12 for over four hours on
# 2026-09-06). Free text is inherently fuzzy; this errs toward over-notifying (a false positive
# costs one wasted check) rather than under-notifying (a false negative costs a silent multi-hour
# gap). Prefix optional and verb list wide, per the 2026-09-06 21:48 lesson: a check fitted to one
# phrasing goes silently blind when the phrasing drifts.
LANDED_CLAUSE_RE = re.compile(
    r"(?:G4-W17 arrival )?item[s]?\s*((?:\(?\d+\)?[\s,]*(?:and)?[\s,]*)+)"
    r"[^.\n]{0,100}?\b(?:land(?:ed|s)|live-verified|flipped|raised|both\s+landed|"
    r"closed with a mutation test)\b",
    re.I,
)
NUMBER_RE = re.compile(r"\d+")


def _committed_text(rel_path: str) -> str | None:
    """The last COMMITTED content (`git show HEAD:<path>`), not whatever is on disk. Added
    2026-09-06 22:50 after this monitor read a draft, uncommitted section-31 entry straight off the
    shared working tree and reported an item "landed" mid-write. A claim is not a signal until it
    is committed."""
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel_path}"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        )
    except Exception:
        return None
    return result.stdout if result.returncode == 0 else None


def landed_items() -> dict[int, list[tuple[str, str]] | None]:
    """Item number -> its unlock targets from the ledger, or None when only the prose regex saw it
    land (a ledger gap to report, not to drop). Two independent signals, neither trusted alone:
    the ledger is authoritative for targets; the regex is the safety net for detection."""
    found: dict[int, list[tuple[str, str]] | None] = {}
    text = _committed_text(DECISION_LOG)
    if text is not None:
        for m in LANDED_CLAUSE_RE.finditer(text):
            for num in NUMBER_RE.findall(m.group(1)):
                found.setdefault(int(num), None)
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                item = int(record["item"])
                unlocks = [tuple(u) for u in record.get("unlocks") or []]
                found[item] = unlocks
            except Exception:
                continue  # one malformed line never blocks every other line's signal
    return found


def main() -> None:
    """Emit one line per landed item the first time it is seen: its ledger unlock targets when the
    ledger has them, an explicit ledger-gap line when it does not. Deliberately does NOT try to
    confirm a disposition is still open — a human or the reviewer's next wake confirms in under a
    minute. The point is that the notification arrives at all, immediately."""
    reported: set[int] = set()
    while True:
        try:
            for item, unlocks in sorted((landed_items()).items()):
                if item in reported:
                    continue
                reported.add(item)
                if unlocks:
                    targets = ", ".join(f"{lane}:{repo}" for lane, repo in unlocks)
                    print(f"UNBLOCKED item({item}) landed -> check and re-run: {targets}", flush=True)
                elif unlocks is None:
                    print(
                        f"LEDGER_GAP item({item}) reads as landed in section 31 but has no "
                        f"unblocked.jsonl record — check its bracket citation for lane targets and "
                        f"ask the executor to append the ledger line (procedure 2c)",
                        flush=True,
                    )
                # unlocks == [] is a landed item that unblocks nothing: recorded, no event needed.
        except Exception as exc:
            print(f"MONITOR_ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()
