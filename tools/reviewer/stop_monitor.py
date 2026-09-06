"""Event-driven stop detection for the loop session (runs under the Monitor tool).

Every 60 s reads the tail of the loop transcript and emits one line per state change:
  LOOP_STOPPED  - the last ScheduleWakeup carried stop:true (the loop ended itself)
  LOOP_CAPPED   - the last assistant text names a session/usage limit (harness stop)
  LOOP_SILENT   - no new record for longer than the last wakeup delay + 40 min
  LOOP_RESUMED  - activity after any of the above
Nothing else is printed, so each event is a notification worth acting on (re-arm per procedure 2c).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

# Owner/reviewer tooling (docs/REPOSITORY_LAYOUT.md) — supervises the loop from outside; never
# imported by src/repository_presenter, never touched by the loop or a lane.
TRANSCRIPT = Path(os.environ.get(
    "REVIEWER_LOOP_TRANSCRIPT",
    r"C:\Users\prora\.claude\projects\d--Users-prora-OneDrive-Documents-GitHub-repository-presenter"
    r"\4705e217-53a5-4974-aa24-559ae9abbd05.jsonl",
))
TAIL_BYTES = 3_000_000
LIMIT = re.compile(r"session limit|hit your (session|usage) limit|usage limit|resets \d", re.I)


def tail_state() -> dict:
    size = TRANSCRIPT.stat().st_size
    with TRANSCRIPT.open("rb") as fh:
        fh.seek(max(0, size - TAIL_BYTES))
        chunk = fh.read().decode("utf-8", errors="replace")
    last_ts = None
    last_wake = None
    last_text = ""
    for ln in chunk.splitlines()[1:]:
        try:
            o = json.loads(ln)
        except Exception:
            continue
        ts = o.get("timestamp")
        if ts:
            last_ts = ts
        m = o.get("message") or {}
        c = m.get("content")
        if isinstance(c, list):
            for p in c:
                if not isinstance(p, dict):
                    continue
                if p.get("type") == "tool_use" and p.get("name") == "ScheduleWakeup":
                    last_wake = (ts, p.get("input") or {})
                if p.get("type") == "text" and m.get("role") == "assistant":
                    last_text = p.get("text") or ""
    return {"last_ts": last_ts, "last_wake": last_wake, "last_text": last_text}


def main() -> None:
    reported: set[str] = set()
    alerted = False
    while True:
        try:
            s = tail_state()
            now = dt.datetime.now(dt.timezone.utc)
            events = []
            lw = s["last_wake"]
            if lw and lw[1].get("stop"):
                key = f"stop:{lw[0]}"
                if key not in reported:
                    events.append(f"LOOP_STOPPED ScheduleWakeup stop:true at {lw[0]} — re-arm: /loop Read project/loop-prompt.md in full and follow it.")
                    reported.add(key)
            if LIMIT.search(s["last_text"] or ""):
                key = "cap:" + (s["last_ts"] or "")
                if key not in reported:
                    snippet = re.sub(r"\s+", " ", s["last_text"])[:160]
                    events.append(f"LOOP_CAPPED {s['last_ts']}: {snippet}")
                    reported.add(key)
            if s["last_ts"]:
                last = dt.datetime.strptime(s["last_ts"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
                idle = (now - last).total_seconds()
                delay = float((lw[1].get("delaySeconds") or 0) if lw else 0)
                # a wakeup that has not fired 10 minutes after its delay is a stall (2026-09-06 08:45:
                # a 300 s wakeup never fired and the old 40-minute allowance hid it)
                allowance = max(delay + 10 * 60, 15 * 60)
                if idle > allowance:
                    key = f"silent:{int(idle // 3600)}:{s['last_ts']}"
                    if key not in reported:
                        events.append(f"LOOP_SILENT {idle / 60:.0f} min since {s['last_ts']} (allowance {allowance / 60:.0f} min)")
                        reported.add(key)
                elif alerted and idle < 300:
                    events.append(f"LOOP_RESUMED activity at {s['last_ts']}")
                    alerted = False
            if events:
                alerted = True
                for e in events:
                    print(e, flush=True)
        except Exception as exc:  # keep watching through transient errors
            print(f"MONITOR_ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()
