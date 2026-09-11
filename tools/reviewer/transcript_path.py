"""Resolve the executor session's transcript path (owner/reviewer tooling).

Why this exists (PHASE1/F1, 2026-09-11): stop_monitor.py, timestamp_monitor.py and
reviewer_check.py each hard-coded one session's transcript as their default. That session ended
on 2026-09-10 and the executor moved on; every monitor restarted after that watched a dead file
and reported nothing, with no error on any channel. A per-session identifier is never a safe
module constant.

Resolution order, first hit wins:
  1. REVIEWER_LOOP_TRANSCRIPT environment variable (unchanged escape hatch).
  2. tools/reviewer/.local/executor_transcript.txt - one line, the absolute path, written by the
     supervisor at startup (procedure section 0) when it identifies the live executor session.
  3. The most recently modified *.jsonl in the project transcript directory - best effort only,
     and never silent: the caller gets a warning line to print whenever the fallback was used or
     the resolved file looks dead.

A resolved transcript whose mtime is older than STALE_MINUTES is reported loudly either way -
monitoring a dead transcript is indistinguishable from a healthy quiet loop otherwise.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

PROJECTS_DIR = Path(
    r"C:\Users\prora\.claude\projects\d--Users-prora-OneDrive-Documents-GitHub-repository-presenter"
)
RECORDED = Path(__file__).parent / ".local" / "executor_transcript.txt"
STALE_MINUTES = 45


def resolve_transcript() -> Path:
    env = os.environ.get("REVIEWER_LOOP_TRANSCRIPT")
    if env:
        return Path(env)
    if RECORDED.exists():
        recorded = RECORDED.read_text(encoding="utf-8").strip()
        if recorded:
            return Path(recorded)
    candidates = sorted(
        PROJECTS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if candidates:
        return candidates[0]
    return PROJECTS_DIR / "no-transcript-found.jsonl"


def resolution_report(path: Path) -> str | None:
    """One warning line when the resolved transcript deserves distrust, else None.

    Callers print it once at startup (monitors) or into section 0 (reviewer_check) - the point is
    that a dead or guessed transcript is announced, never silently monitored.
    """
    if not path.exists():
        return f"TRANSCRIPT_WARNING resolved path does not exist: {path}"
    age_min = (
        dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)
    ).total_seconds() / 60
    source = (
        "env"
        if os.environ.get("REVIEWER_LOOP_TRANSCRIPT")
        else ("recorded" if RECORDED.exists() and RECORDED.read_text(encoding="utf-8").strip() else "newest-fallback")
    )
    if age_min > STALE_MINUTES:
        return (
            f"TRANSCRIPT_WARNING {path.name} (source: {source}) last wrote {age_min:.0f} min ago"
            f" - the executor may be dead or this is the wrong session; re-run procedure section 0"
        )
    if source == "newest-fallback":
        return (
            f"TRANSCRIPT_NOTE watching {path.name} by newest-fallback (no recorded executor path);"
            f" write tools/reviewer/.local/executor_transcript.txt at the next supervisor startup"
        )
    return None
