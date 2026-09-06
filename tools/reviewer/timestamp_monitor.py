"""Real-time watch for fabricated §31 timestamps and unearned acceptances (runs under Monitor).

Polls the loop's transcript every 45 s for new §31-shaped text and new ACCEPTED/accept commits, and
emits one line the instant either looks wrong — well ahead of the 20-minute reviewer cron. This exists
because the owner moved the loop to a cheaper model and asked for vigilant supervision: a fabricated
timestamp or an unearned accept is exactly the failure mode a weaker, pressured executor produces, and
the earlier it's caught the cheaper the correction.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Owner/reviewer tooling (docs/REPOSITORY_LAYOUT.md) — never imported by src/repository_presenter,
# never touched by the loop or a lane.
REPO = Path(__file__).resolve().parents[2]
TRANSCRIPT = Path(os.environ.get(
    "REVIEWER_LOOP_TRANSCRIPT",
    r"C:\Users\prora\.claude\projects\d--Users-prora-OneDrive-Documents-GitHub-repository-presenter"
    r"\4705e217-53a5-4974-aa24-559ae9abbd05.jsonl",
))
STAMP = re.compile(r"\*\*(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})")


def tail_lines(n_bytes: int = 400_000) -> list[str]:
    size = TRANSCRIPT.stat().st_size
    with TRANSCRIPT.open("rb") as fh:
        fh.seek(max(0, size - n_bytes))
        return fh.read().decode("utf-8", errors="replace").splitlines()[1:]


def main() -> None:
    seen_stamps: set[str] = set()
    seen_accepts: set[str] = set()
    while True:
        try:
            now = dt.datetime.now()
            for ln in tail_lines():
                try:
                    o = json.loads(ln)
                except Exception:
                    continue
                m = o.get("message") or {}
                if m.get("role") != "assistant":
                    continue
                c = m.get("content")
                if not isinstance(c, list):
                    continue
                for part in c:
                    if not isinstance(part, dict) or part.get("type") != "text":
                        continue
                    text = part.get("text") or ""
                    for date_s, hh, mm in STAMP.findall(text):
                        key = f"{date_s} {hh}:{mm}:{text[:40]}"
                        if key in seen_stamps:
                            continue
                        seen_stamps.add(key)
                        try:
                            stamped = dt.datetime.strptime(f"{date_s} {hh}:{mm}", "%Y-%m-%d %H:%M")
                        except ValueError:
                            continue
                        drift_min = abs((stamped - now).total_seconds()) / 60
                        if drift_min > 20:
                            print(f"BAD_TIMESTAMP {date_s} {hh}:{mm} drift {drift_min:.0f} min from now ({now.strftime('%H:%M')}) — {text[:100]!r}", flush=True)
                    for accept_m in re.finditer(r"\b(accept(?:ed|s)?|ACCEPTED)\b[^.\n]{0,80}(G\d[-_]?W?\d*)", text):
                        key = accept_m.group(0)[:80]
                        if key in seen_accepts:
                            continue
                        seen_accepts.add(key)
                        if not re.search(r"predicate|evidence|manifest|acceptance", text, re.I):
                            print(f"UNSUPPORTED_ACCEPT_CLAIM {accept_m.group(0)[:90]!r} — no predicate/evidence word nearby", flush=True)
        except Exception as exc:
            print(f"MONITOR_ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        time.sleep(45)


if __name__ == "__main__":
    main()
