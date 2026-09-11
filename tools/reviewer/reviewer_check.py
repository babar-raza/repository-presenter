"""Reviewer check for the repository-presenter loop: deterministic, cheap, repeatable.

Reads the loop session's transcript (JSONL), the repository, and reviewer_state.json, and prints a
compact report: liveness, iteration accounting, rule compliance (loop-prompt sections 0, 3, 4),
governance consistency (state.yaml vs section 27.9, ESM exit predicates, budgets, limits vs
decisions), time-box overrun on the active item, growth signals (the legacy pattern), new section 31
entries with heuristic flags, and a caveated rate projection. Judgment is applied only to [FLAG] lines.

This tool is owner/reviewer tooling (docs/REPOSITORY_LAYOUT.md): it supervises the loop from outside
and is never imported by src/repository_presenter, never touched by the loop or a lane.

Usage: python -X utf8 reviewer_check.py [--since ISO] [--hours N] [--record] [--json]
  --record appends this wake's metrics to reviewer_state.json history (the cron wake does this).

Environment (all optional; defaults suit this machine's current reviewer session):
  REVIEWER_LOOP_TRANSCRIPT   path to the loop session's .jsonl transcript
  REVIEWER_STATE_PATH        path to the reviewer's own state JSON (history, watch field)
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from transcript_path import resolution_report, resolve_transcript

REPO = Path(__file__).resolve().parents[2]  # tools/reviewer/this_file.py -> repo root
# PHASE1/F1: resolved, never hard-coded — the baked-in session path went dead on 2026-09-10 and
# every consumer silently monitored a file the executor no longer wrote.
TRANSCRIPT = resolve_transcript()
STATE = Path(os.environ.get("REVIEWER_STATE_PATH", str(Path(__file__).parent / ".local" / "reviewer_state.json")))
LOOP_SUBJECT = re.compile(r"\((G\d_[A-Z_]+)/(G\d-W\d+)\)\s*$")
GROWTH_IDENT = re.compile(
    r"^\+.*\b(def (check|validate|verify|guard|audit|assert)_\w+|class \w*(Check|Validator|Guard|Auditor)\b)"
)
FLAGS: list[str] = []


def flag(msg: str) -> str:
    FLAGS.append(msg)
    return f"[FLAG] {msg}"


def ok(msg: str) -> str:
    return f"[OK]   {msg}"


def info(msg: str) -> str:
    return f"[INFO] {msg}"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout


def to_utc_z(iso: str) -> str:
    return (
        dt.datetime.fromisoformat(iso).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    )


def parse_ts(z: str) -> dt.datetime:
    return dt.datetime.strptime(z[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def local(z: str) -> str:
    return parse_ts(z).astimezone().strftime("%H:%M")


# ----------------------------------------------------------------------------- transcript


FILE_IN_CMD = re.compile(r"[\w./\\-]+\.(?:md|py|yaml|yml|json|toml|txt|jsonl)\b")
READ_HEAD = re.compile(r"^\s*(?:cd\s+\"?[^&;|\"]*\"?\s*&&\s*)?(sed|cat|head|tail|grep|rg|awk|less|type)\b")


def categorise(cmd: str) -> str:
    if READ_HEAD.match(cmd) and not re.search(r"\bpytest\b|\bgit\b", cmd):
        return "read_bash"
    if re.search(r"\bpytest\b", cmd):
        focused = bool(re.search(r"pytest[^|\n]*(\s-k\s|\stests?[/\\]\S)", cmd))
        return "pytest_focused" if focused else "pytest_full"
    if re.search(r"repository-presenter(\.exe)?\s+present\b|\bpresent\s+--repo", cmd):
        return "present"
    if re.search(r"\bgh run (watch|view|list)", cmd):
        return "ci_watch"
    if re.search(r"\b(ruff|mypy)\b", cmd):
        return "lint"
    if re.search(r"\bpip\b|venv", cmd):
        return "env"
    if re.search(r"\bgit\b", cmd):
        return "git"
    return "other"


def parse_transcript(since_z: str) -> dict:
    uses: dict[str, tuple[str, str, dict]] = {}
    durations: collections.Counter[str] = collections.Counter()
    counts: collections.Counter[str] = collections.Counter()
    reads: collections.Counter[str] = collections.Counter()
    read_calls = 0
    edits = writes = 0
    wakeups: list[tuple[str, dict]] = []
    pytest_times: list[tuple[str, str, float]] = []
    presents: list[str] = []
    ci_watch_seconds = 0.0
    first_ts = last_ts = None
    last_text = ""
    limit_hit = None
    stop_text_hits = []
    pending_result: dict[str, str] = {}  # tool_use_id -> category
    records = 0
    lp_touches = 0
    events: list[dict] = []  # compact per-tool events for behaviour checks
    event_by_tid: dict[str, dict] = {}
    with TRANSCRIPT.open("rb") as fh:
        for raw in fh:
            try:
                o = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                continue
            ts = o.get("timestamp") or ""
            if not ts or ts < since_z:
                continue
            records += 1
            first_ts = first_ts or ts
            last_ts = ts
            m = o.get("message") or {}
            role = m.get("role")
            content = m.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                kind = part.get("type")
                if kind == "text" and role == "assistant":
                    text = part.get("text") or ""
                    last_text = text
                    if re.search(r"session limit|hit your (session|usage) limit|usage limit", text, re.I):
                        limit_hit = (ts, text[:160])
                elif kind == "tool_use":
                    name = part.get("name") or ""
                    inp = part.get("input") or {}
                    uses[part.get("id") or ""] = (ts, name, inp)
                    counts[name] += 1
                    ev = {"ts": ts, "tool": name, "cat": "", "arg": "", "result": "", "error": False}
                    if name == "Bash":
                        ev["cat"] = categorise(inp.get("command", ""))
                        ev["arg"] = inp.get("command", "")[:300]
                    elif name in ("Edit", "Write"):
                        ev["arg"] = str(inp.get("file_path", ""))
                    elif name == "ScheduleWakeup":
                        ev["arg"] = json.dumps(inp)[:200]
                    events.append(ev)
                    event_by_tid[part.get("id") or ""] = ev
                    if name == "ScheduleWakeup":
                        wakeups.append((ts, inp))
                    elif name == "Bash":
                        cmd = inp.get("command", "")
                        cat = categorise(cmd)
                        counts[f"bash:{cat}"] += 1
                        if "loop-prompt.md" in cmd:
                            lp_touches += 1
                        if cat == "read_bash":
                            read_calls += 1
                            fm = FILE_IN_CMD.search(cmd)
                            pending_result[part.get("id") or ""] = "read:" + (fm.group(0) if fm else cmd[:50])
                        else:
                            pending_result[part.get("id") or ""] = cat
                        if cat == "present":
                            presents.append(ts)
                    elif name == "Read":
                        read_calls += 1
                        fp = str(inp.get("file_path", ""))
                        if "loop-prompt" in fp:
                            lp_touches += 1
                        pending_result[part.get("id") or ""] = "read:" + fp
                    elif name == "Edit":
                        edits += 1
                    elif name == "Write":
                        writes += 1
                elif kind == "tool_result":
                    tid = part.get("tool_use_id") or ""
                    if tid in uses:
                        t0, name, inp = uses[tid]
                        secs = (parse_ts(ts) - parse_ts(t0)).total_seconds()
                        body = part.get("content")
                        if isinstance(body, list):
                            body = " ".join(
                                x.get("text", "") for x in body if isinstance(x, dict)
                            )
                        body = str(body or "")
                        ev = event_by_tid.get(tid)
                        if ev is not None:
                            ev["error"] = bool(part.get("is_error"))
                            ev["secs"] = secs
                            fails = re.findall(r"FAILED (tests?[\w/\\.]+::[\w\[\]\-\.]+)", body)
                            tail = body.strip().splitlines()[-3:] if body.strip() else []
                            ev["result"] = (" | ".join(fails[:6]) + " || " if fails else "") + " / ".join(x[:160] for x in tail)
                        tag = pending_result.get(tid, name.lower())
                        if tag.startswith("read:"):
                            reads[tag[5:]] += len(body)
                            durations["read"] += secs
                        else:
                            durations[tag] += secs
                            if tag.startswith("pytest"):
                                mt = re.search(r"(\d+ passed[^\n]{0,60}?) in (\d+\.?\d*)s", body)
                                if mt:
                                    pytest_times.append((ts, mt.group(1)[:50], float(mt.group(2))))
                            if tag == "ci_watch":
                                ci_watch_seconds += secs
    return {
        "records": records,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "counts": counts,
        "durations": durations,
        "reads": reads,
        "read_calls": read_calls,
        "edits": edits,
        "writes": writes,
        "wakeups": wakeups,
        "pytest_times": pytest_times,
        "presents": presents,
        "ci_watch_seconds": ci_watch_seconds,
        "last_text": last_text,
        "limit_hit": limit_hit,
        "lp_touches": lp_touches,
        "events": events,
    }


# ----------------------------------------------------------------------------- repository


def load_yaml(path: Path):
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def section(text: str, start_pat: str, end_pat: str) -> str:
    s = re.search(start_pat, text, re.M)
    if not s:
        return ""
    e = re.search(end_pat, text[s.end():], re.M)
    return text[s.start(): s.end() + (e.start() if e else len(text))]


def queue_from_27_9(research: str) -> list[dict]:
    import yaml

    block = section(research, r"^### 27\.9\b", r"^### 27\.10\b")
    entries: list[dict] = []
    for fence in re.findall(r"```yaml\n(.*?)```", block, re.S):
        try:
            loaded = yaml.safe_load(fence)
        except Exception:
            continue
        if isinstance(loaded, list):
            entries.extend(e for e in loaded if isinstance(e, dict) and "id" in e)
    return entries


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def repo_checks(state: dict, since_iso: str) -> tuple[list[str], dict]:
    out: list[str] = []
    metrics: dict = {}
    research = (REPO / "docs/RESEARCH_AND_GUIDELINES.md").read_text(encoding="utf-8")
    esm = (REPO / "docs/EXECUTION_STATE_MACHINE.md").read_text(encoding="utf-8")
    contract = (REPO / "docs/README_CONTRACT.md").read_text(encoding="utf-8")
    sy = load_yaml(REPO / "project/state.yaml")
    active = sy.get("active_work_item") or {}
    queue = sy.get("next_ready_items") or []
    gate = sy["current_gate"]["id"]
    metrics["active_id"] = active.get("id")
    metrics["active_status"] = active.get("status")
    metrics["candidates"] = sy["progress"]["current_candidates"]
    metrics["queue_ids"] = [q["id"] for q in queue]

    # schema
    try:
        import jsonschema

        schema = json.loads((REPO / "schemas/state.schema.json").read_text(encoding="utf-8"))
        errs = list(jsonschema.Draft202012Validator(schema).iter_errors(sy))
        out.append(ok("state.yaml validates") if not errs else flag(f"state.yaml schema errors: {len(errs)}: {errs[0].message[:120]}"))
    except Exception as exc:  # pragma: no cover
        out.append(info(f"schema check skipped: {exc.__class__.__name__}"))

    # queue vs 27.9
    entries = queue_from_27_9(research)
    # An item is accepted (or folded away) when the loop has committed under its ID and it is no
    # longer queued or active; acceptance is phrased many ways in subjects, so derive it this way.
    subjects = git("log", "--format=%s", "-600")
    worked = set(re.findall(r"/(G\d-W\d+)\)\s*$", subjects, re.M))
    expected = [e for e in entries if e["id"] != active.get("id") and e["id"] not in worked]
    exp_ids = [e["id"] for e in expected]
    q_ids = metrics["queue_ids"]
    if exp_ids == q_ids:
        out.append(ok(f"queue order matches section 27.9 ({len(q_ids)} items)"))
    else:
        out.append(flag(f"queue order differs from 27.9: state={q_ids[:6]}... vs 27.9={exp_ids[:6]}..."))
    purpose_by_id = {e["id"]: norm(e.get("purpose", "")) for e in entries}
    drift = [q["id"] for q in queue if norm(q.get("purpose", "")) != purpose_by_id.get(q["id"], "")]
    out.append(ok("queued purposes identical to 27.9") if not drift else flag(f"queued purpose text differs from 27.9 for {drift}"))
    if active.get("id") in purpose_by_id:
        p = purpose_by_id[active["id"]]
        acc_text = norm(" ".join(active.get("acceptance", [])))
        m = re.search(r"Acceptance: (.*)$", p)
        if m:
            words_p = set(re.findall(r"[A-Za-z]{5,}", m.group(1).lower()))
            words_a = set(re.findall(r"[A-Za-z]{5,}", acc_text.lower()))
            missing = sorted(words_p - words_a)[:8]
            out.append(info(f"active {active['id']} acceptance vs 27.9 Acceptance clause — terms only in 27.9: {missing or 'none'}"))

    # time-box overrun: an item's own prerequisites/purpose may state "Time box N hours from
    # promotion" (RESEARCH 28.12). No rule enforced this mechanically until 2026-09-06, when G4-W11
    # ran 67 minutes past its stated 5-hour box with nothing catching it - the same silent-scope-creep
    # shape as the legacy project. Anchor: the most recent commit whose subject promotes this item
    # (an accept-and-promote commit naming the active id, or the item's own first commit if none).
    active_text = " ".join(active.get("prerequisites", []) + [active.get("purpose", "")])
    box_m = re.search(r"[Tt]ime box (\d+(?:\.\d+)?)\s*hours?\s*from promotion", active_text)
    if box_m and active.get("id"):
        box_hours = float(box_m.group(1))
        aid = active["id"]
        # Walk state.yaml's history newest-first; the promotion commit is the OLDEST one in the
        # unbroken run where active_work_item.id already equals aid (i.e. the first commit that made
        # it active). Bounded to the last 40 touches of state.yaml - plenty for one gate's lifetime.
        promo_ts = None
        hashes = git("log", "--format=%H", "-40", "--", "project/state.yaml").split()
        for h in hashes:
            raw = git("show", f"{h}:project/state.yaml")
            try:
                snap = yaml.safe_load(raw)
                sid = (snap.get("active_work_item") or {}).get("id")
            except Exception:
                sid = None
            if sid == aid:
                promo_ts = int(git("log", "-1", "--format=%ct", h).strip())
            else:
                break  # walked past the commit that first set it to aid
        if promo_ts:
            elapsed_h = (dt.datetime.now().timestamp() - promo_ts) / 3600
            over_h = elapsed_h - box_hours
            metrics["active_box_hours"] = box_hours
            metrics["active_elapsed_hours"] = round(elapsed_h, 2)
            if over_h > 0:
                out.append(flag(f"{aid} is {over_h:.1f} h PAST its {box_hours:.0f}-hour time box (active {elapsed_h:.1f} h) — accept with dispositions now, per 28.12"))
            else:
                out.append(info(f"{aid}: {elapsed_h:.1f} h of its {box_hours:.0f}-hour time box used ({-over_h:.1f} h remaining)"))
        else:
            out.append(info(f"{aid} states a {box_hours:.0f}-hour time box but no promotion commit found to anchor it"))
    elif active.get("id"):
        out.append(info(f"{active['id']}: no time box stated in its purpose/prerequisites — unbounded (RESEARCH 28.12 gives every cohort item a box; a shared-infra item without one is a growth risk)"))

    block = section(research, r"^### 27\.9\b", r"^### 27\.10\b")
    preamble = block[: block.find("```yaml")] if "```yaml" in block else block
    expanded: set[str] = set()
    for g, lo, hi in re.findall(r"(G\d)-W(\d+) to G\d-W(\d+)", preamble):
        expanded.update(f"{g}-W{n:02d}" for n in range(int(lo), int(hi) + 1))
    not_indexed = [i for i in q_ids if i not in preamble and i not in expanded]
    out.append(ok("every queued item is named in the 27.9 order narrative") if not not_indexed else flag(f"queued items absent from the 27.9 order narrative: {not_indexed}"))

    # budgets
    budget = sy["execution_limits"]["governance_budget"]
    for name, path, cap in (
        ("AGENTS.md", "AGENTS.md", budget["agents_md_max_lines"]),
        ("ESM", "docs/EXECUTION_STATE_MACHINE.md", budget["execution_state_machine_max_lines"]),
    ):
        n = len((REPO / path).read_text(encoding="utf-8").splitlines())
        out.append(ok(f"{name} {n}/{cap} lines") if n <= cap else flag(f"{name} over budget {n}/{cap}"))
    lp = len((REPO / "project/loop-prompt.md").read_text(encoding="utf-8").splitlines())
    out.append(info(f"loop-prompt {lp} lines"))
    metrics["loop_prompt_lines"] = lp

    # limits vs decisions
    lanes_mentioned = [q["id"] for q in queue if re.search(r"\blanes?\b", q.get("purpose", ""))]
    if lanes_mentioned and not sy["execution_limits"]["parallel_repository_work_allowed"]:
        out.append(flag(f"parallel_repository_work_allowed is false but {lanes_mentioned} plan repository lanes"))
    elif lanes_mentioned:
        out.append(ok("lane decision and execution_limits agree"))

    # blocking checks count vs rule 15
    sec5 = section(contract, r"^## 5\. Blocking checks", r"^## 6\.")
    n_checks = len(re.findall(r"^\| \d+ \|", sec5, re.M))
    out.append(ok(f"blocking checks in contract: {n_checks} (cap 15)") if n_checks <= 15 else flag(f"blocking checks {n_checks} exceed cap 15"))
    metrics["blocking_checks"] = n_checks

    # gate exit predicates: satisfiability heuristics
    label = {"G2_STABILITY_UNDER_CHANGE": "G2", "G3_PYTHON_COHORT": "G3", "G4_MULTI_LANGUAGE_COHORTS": "G4",
             "G5_RERUN_DURABILITY_AND_HOSTED_OPERATION": "G5", "G6_PROPOSAL_EFFECT_PROOF": "G6",
             "G7_PRODUCTION_AND_CONTINUOUS_OPERATION": "G7"}.get(gate, gate[:2])
    gsec = section(esm, rf"^## {label} —", r"^## ")
    exits = section(gsec, r"^### Exit predicates", r"^## ")
    bullets = [norm(b) for b in re.findall(r"^- (.*?)(?=^- |\Z)", exits, re.M | re.S)]
    gate_items_left = [i for i in q_ids if i.startswith(label + "-")]
    last_item = not gate_items_left
    out.append(info(f"gate {label}: {len(bullets)} exit bullets; gate items still queued: {gate_items_left or 'none (active item is the last)'}"))
    for b in bullets:
        risky = []
        if re.search(r"\d+\s?%|percent", b):
            risky.append("numeric threshold (27.10: thresholds need >=3 compositions)")
        if re.search(r"under (three|\d+) minutes|<\s?\d+\s?min", b):
            risky.append("wall-clock as gate (30.9: a control, not a gate)")
        if re.search(r"blocking [a-z ]*check", b) and not re.search(r"check 1[2-5]", contract[contract.find("## 5."):contract.find("## 6.")]):
            risky.append("names a blocking check the contract does not carry (rule 14)")
        line = f"  exit: {b[:150]}"
        out.append(flag(line + f"  <- {'; '.join(risky)}") if (risky and last_item) else (info(line + (f"  <- {'; '.join(risky)}" if risky else ""))))

    # growth signals since window start
    base = git("rev-list", "-1", f"--before={since_iso}", "HEAD").strip()
    if base:
        stat = git("diff", "--shortstat", f"{base}..HEAD", "--", "src", "tests").strip()
        added = git("diff", "--name-status", "--diff-filter=A", f"{base}..HEAD", "--", "src").strip().splitlines()
        added_files = [l.split("\t", 1)[1] for l in added if "\t" in l]
        orphan = []
        for f in added_files:
            mod = Path(f).stem
            if mod == "__init__":
                continue
            listing = git("grep", "-l", mod, "HEAD", "--", "src").splitlines()
            if not [l for l in listing if not l.endswith(f)]:
                orphan.append(f)
        growth = sum(1 for l in git("diff", f"{base}..HEAD", "--", "src").splitlines() if GROWTH_IDENT.search(l))
        out.append(info(f"src+tests diff since window start: {stat or 'none'}; new src files {len(added_files)}"))
        out.append(flag(f"new src modules with no importer in src: {orphan}") if orphan else ok("every new src module has a production importer"))
        out.append(flag(f"{growth} new check/validate/verify/guard definitions in src this window") if growth >= 3 else info(f"{growth} new check/validate/verify/guard definitions in src this window"))
        metrics["growth_defs"] = growth
    ev = []
    for mf in (REPO / "evidence").rglob("manifest.json"):
        try:
            t = mf.read_text(encoding="utf-8")
        except Exception:
            continue
        if re.search(r"\b(deferred|in part|partial(ly)?|moved to G)\b", t, re.I):
            ev.append(mf.relative_to(REPO).as_posix())
    out.append(flag(f"evidence manifests with deferral language (accept-in-part signal): {ev}") if ev else ok("no deferral language in evidence manifests"))

    # section 31 — lives in docs/DECISION_LOG.md since the 2026-09-08 split; RESEARCH keeps only a
    # stub whose "## 31" heading made this scan report a confident zero (PHASE1/F1). The whole log
    # is section 31, so scan the full file rather than slicing on a heading that can move again.
    body = (REPO / "docs/DECISION_LOG.md").read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(r"^- \*\*2026", body, re.M)]
    metrics["s31_total"] = len(starts)
    reviewed = state.get("reviewed_entries", 0)
    new_entries = []
    for i, s in enumerate(starts):
        if i < reviewed:
            continue
        e = body[s: starts[i + 1]] if i + 1 < len(starts) else body[s:]
        title = norm(re.sub(r"\*\*", "", e.split("**")[1] if e.count("**") >= 2 else e[:120]))[:140]
        fl = []
        if "Evidence" not in e and "evidence" not in e:
            fl.append("no evidence cited")
        if not re.search(r"Reverse by|reversal|Reversed|reverse", e):
            fl.append("no reversal path")
        if re.search(r"\b(defer|moves? to G|in part|rewrit|widen|new check|blocking check)\b", e, re.I):
            fl.append("scope/predicate movement — read closely")
        if re.search(r"\bREVIEWED\b.*reversed", e) and re.search(r"\bREVIEWED\b.*reversed", body[:s]):
            fl.append("possible double reversal (freeze rule)")
        new_entries.append((i + 1, title, fl))
    out.append(info(f"section 31: {len(starts)} entries, {len(new_entries)} new since last wake"))
    for n, title, fl in new_entries:
        out.append((flag if fl else info)(f"  #{n} {title}" + (f"  <- {'; '.join(fl)}" if fl else "")))
    metrics["s31_new"] = len(new_entries)
    return out, metrics


# ----------------------------------------------------------------------------- commits & CI


def commits_since(since_iso: str) -> dict:
    raw = git("log", f"--since={since_iso}", "--format=%h%x1f%s%x1f%b%x1e", "HEAD")
    loop, owner = [], []
    for rec in raw.split("\x1e"):
        if not rec.strip():
            continue
        h, s, b = (rec.strip("\n").split("\x1f") + ["", ""])[:3]
        body_words = len(re.findall(r"\S+", re.sub(r"^Co-Authored-By.*$", "", b, flags=re.M)))
        m = LOOP_SUBJECT.search(s)
        (loop if m else owner).append({"sha": h, "subject": s[:90], "words": body_words, "type": s.split("(")[0]})
    return {"loop": loop, "owner": owner}


def ci_state() -> str:
    try:
        raw = subprocess.run(
            ["gh", "run", "list", "--limit", "6", "--branch", "main", "--json", "status,conclusion,headSha"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=60,
        ).stdout
        runs = json.loads(raw or "[]")
    except Exception as exc:
        return f"gh unavailable ({exc.__class__.__name__})"
    done = [r for r in runs if r["status"] == "completed" and r["conclusion"] != "cancelled"]
    if not done:
        return "no completed run"
    r = done[0]
    return f"{r['conclusion']} on {r['headSha'][:7]}" + (" (a newer run is in progress)" if runs and runs[0]["status"] != "completed" else "")


# ----------------------------------------------------------------------------- behaviour, quality, deadline

DEADLINE = dt.datetime.fromisoformat("2026-09-15T08:00:00+05:00")  # owner, 2026-09-11: PHASE1 sprint "before Monday" (plans/sprint/PHASE1-SPRINT-PLAN.md)
CANDIDATE_ITEMS = {"G3-W01", "G3-W04", "G4-W11", "G4-W12", "G4-W13", "G4-W14", "G4-W15", "G4-W16"}
LOOP_ALLOWED_PREFIXES = ("src/", "tests/", "prompts/", "candidates/", "evidence/", "runs/", "docs/README_CONTRACT.md",
                         "docs/RESEARCH_AND_GUIDELINES.md", "project/state.yaml", "pyproject.toml", "uv.lock", "docs/STATE_MACHINE.md",
                         "docs/REPOSITORY_LAYOUT.md", "schemas/", "migration/", "data/")
ITERATION_BUDGET_MIN = 90


def behaviour_checks(t: dict, state: dict, metrics: dict, since_iso: str, now: dt.datetime, loop_commits: list[dict]) -> list[str]:
    out: list[str] = []
    events = t["events"]
    # --- iterations: boundaries at ScheduleWakeup; commits per iteration; edits; repeated failures
    commit_times: list[tuple[int, str]] = []
    for rec in git("log", f"--since={since_iso}", "--format=%ct%x1f%s", "HEAD").splitlines():
        if "\x1f" in rec:
            ct, s = rec.split("\x1f", 1)
            if LOOP_SUBJECT.search(s):
                commit_times.append((int(ct), s[:70]))
    bounds: list[tuple[dt.datetime, dt.datetime, bool]] = []
    start = dt.datetime.fromisoformat(since_iso).astimezone(dt.timezone.utc)
    for ev in events:
        if ev["tool"] == "ScheduleWakeup":
            end = parse_ts(ev["ts"])
            bounds.append((start, end, True))
            start = end
    bounds.append((start, now.astimezone(dt.timezone.utc), False))  # the open iteration
    stuck_lines = []
    for b0, b1, closed in bounds:
        mins = (b1 - b0).total_seconds() / 60
        n_commits = sum(1 for ct, _ in commit_times if b0.timestamp() <= ct <= b1.timestamp())
        evs = [e for e in events if b0 <= parse_ts(e["ts"]) <= b1]
        edits = sum(1 for e in evs if e["tool"] in ("Edit", "Write"))
        fails: collections.Counter[str] = collections.Counter()
        for e in evs:
            if e["cat"].startswith("pytest") and "||" in e["result"]:
                for name in e["result"].split("||")[0].split(" | "):
                    if name.strip():
                        fails[name.strip()] += 1
        repeated = [(n, c) for n, c in fails.most_common(3) if c >= 3]
        label = "open" if not closed else "ended"
        if (mins > ITERATION_BUDGET_MIN and n_commits == 0) or repeated or (edits >= 15 and n_commits == 0):
            stuck_lines.append(flag(f"iteration ({label}, {mins:.0f} min): commits {n_commits}, edits {edits}"
                                    + (f", same test failing {repeated[0][1]}x: {repeated[0][0]}" if repeated else "")
                                    + " — stuck-iteration signature (budget 90 min; checkpoint or split)"))
        elif not closed and mins > 45 and n_commits == 0:
            stuck_lines.append(info(f"open iteration {mins:.0f} min without a commit yet (budget {ITERATION_BUDGET_MIN})"))
    out.extend(stuck_lines or [ok(f"no stuck-iteration signature in {len(bounds)} iterations (budget {ITERATION_BUDGET_MIN} min)")])
    # repeated identical failing commands
    import hashlib as _h

    full_cmds: dict[str, str] = {}
    errs: collections.Counter[str] = collections.Counter()
    for e in events:
        if e["tool"] == "Bash" and e.get("error"):
            key = _h.sha1(e["arg"].encode("utf-8", "replace")).hexdigest()[:10]
            full_cmds[key] = e["arg"]
            errs[key] += 1
    rep = [(full_cmds[k], n) for k, n in errs.most_common(2) if n >= 3]
    out.append(flag(f"same command failed {rep[0][1]}x: {rep[0][0][:90]}") if rep else ok("no identical command failed three times"))
    # present outcomes
    pres = [e for e in events if e["cat"] == "present"]
    bad = [e for e in pres if re.search(r"Traceback|EXIT_INCONSISTENT|exit code [1-9]|error", e["result"], re.I)]
    out.append((flag if len(bad) >= 3 else info)(f"present runs {len(pres)}, with error/inconsistent result {len(bad)}"))
    # --- scope: loop commits touching paths outside what the loop may write
    outside: list[str] = []
    prompts_touched = 0
    for c in loop_commits:
        files = git("show", "--name-only", "--format=", c["sha"]).split()
        if any(f.startswith("prompts/") for f in files):
            prompts_touched += 1
        for f in files:
            if not f.startswith(LOOP_ALLOWED_PREFIXES):
                outside.append(f"{c['sha']}:{f}")
    out.append(flag(f"loop commits touched governance/other paths: {outside[:5]}") if outside else ok("loop commits stayed within its paths"))
    out.append((flag if prompts_touched >= 3 else info)(f"loop commits changing prompts/ this window: {prompts_touched} (each one re-seals the canary)"))
    # --- weaker-executor watch (owner switched the loop to a cheaper model, 2026-09-06 ~10:30;
    # "at any cost" pressure + a less capable executor is exactly the combination that produces
    # shortcuts, so these checks run every wake regardless of whether anything else flagged).
    subj_all = git("log", f"--since={since_iso}", "--format=%s%x1f%b%x1e", "HEAD")
    accept_in_part = [rec.split("\x1f")[0] for rec in subj_all.split("\x1e") if re.search(r"accept.{0,40}(in part|partial|most|remaining)", rec, re.I)]
    out.append(flag(f"possible accept-in-part language in a commit: {accept_in_part[:3]}") if accept_in_part else ok("no accept-in-part language in commit subjects/bodies"))
    fabrication_words = [rec.split("\x1f")[0] for rec in subj_all.split("\x1e") if re.search(r"\b(assume|assumed|should work|probably|likely fixes|presumably)\b", rec, re.I)]
    out.append(flag(f"unverified-confidence language in a commit body: {fabrication_words[:3]}") if fabrication_words else ok("no hedged/assumed-fixed language in commit bodies"))
    # a fingerprint sanity check: does every claimed acceptance still cite real evidence paths?
    for gate_dir in (REPO / "evidence/build").glob("*/manifest.json"):
        try:
            txt = gate_dir.read_text(encoding="utf-8")
            if re.search(r'"work_item_status"\s*:\s*"ACCEPTED"', txt) and not re.search(r'"(preflight|cohort|predicates|work_item_acceptance)"', txt):
                out.append(flag(f"{gate_dir.relative_to(REPO)}: ACCEPTED with no visible evidence field — read before trusting"))
        except Exception:
            pass
    # --- quality: tests weakened?
    base = git("rev-list", "-1", f"--before={since_iso}", "HEAD").strip()
    if base:
        tdiff = git("diff", f"{base}..HEAD", "--", "tests")
        skips = [l for l in tdiff.splitlines() if l.startswith("+") and re.search(r"pytest\.mark\.(skip|xfail|skipif)", l)]
        removed_assert = sum(1 for l in tdiff.splitlines() if l.startswith("-") and re.search(r"^\-\s*assert\b", l))
        added_assert = sum(1 for l in tdiff.splitlines() if l.startswith("+") and re.search(r"^\+\s*assert\b", l))

        def count_tests(rev: str) -> int:
            return sum(int(x.rsplit(":", 1)[1]) for x in git("grep", "-c", "def test_", rev, "--", "tests").splitlines() if ":" in x)

        n0, n1 = count_tests(base), count_tests("HEAD")
        deleted = [l.split("\t", 1)[1] for l in git("diff", "--name-status", "--diff-filter=D", f"{base}..HEAD", "--", "tests").splitlines() if "\t" in l]
        weak = bool(skips) or n1 < n0 or deleted
        out.append((flag if weak else ok)(f"tests: {n0} -> {n1} test functions; skip/xfail added {len(skips)}; deleted files {len(deleted)}; asserts -{removed_assert}/+{added_assert}"))
        # committed after a failing full suite?
        bad_commits = []
        for ct, subj in commit_times:
            before = [e for e in events if e["cat"] == "pytest_full" and parse_ts(e["ts"]).timestamp() < ct and parse_ts(e["ts"]).timestamp() > ct - 3600]
            if before and re.search(r"\d+ failed|\d+ error", before[-1]["result"]) and " passed" not in before[-1]["result"].split("||")[-1].split("/")[-1]:
                bad_commits.append(subj[:60])
        out.append(flag(f"commits whose last full suite before them failed: {bad_commits[:3]}") if bad_commits else ok("every loop commit followed a passing full suite (or none was run within the hour)"))
    # --- predicate drift: active acceptance text changed while the item stayed active
    sy = load_yaml(REPO / "project/state.yaml")
    active = sy.get("active_work_item") or {}
    import hashlib

    acc_hash = hashlib.sha1(norm(" ".join(active.get("acceptance", []))).encode()).hexdigest()[:10]
    metrics["acceptance_hash"] = acc_hash
    hist = state.get("history", [])
    if hist and hist[-1].get("active_id") == active.get("id") and hist[-1].get("acceptance_hash") and hist[-1]["acceptance_hash"] != acc_hash:
        out.append(flag(f"active {active.get('id')} acceptance text changed since last wake (was {hist[-1]['acceptance_hash']}, now {acc_hash}) — compare with 27.9 before accepting"))
    else:
        out.append(ok(f"active acceptance unchanged ({acc_hash})"))
    # --- gate purpose in state.yaml vs ESM exit predicates (duplicated text drifts)
    esm = (REPO / "docs/EXECUTION_STATE_MACHINE.md").read_text(encoding="utf-8")
    gate = sy["current_gate"]
    label = {"G2_STABILITY_UNDER_CHANGE": "G2", "G3_PYTHON_COHORT": "G3", "G4_MULTI_LANGUAGE_COHORTS": "G4",
             "G5_RERUN_DURABILITY_AND_HOSTED_OPERATION": "G5", "G6_PROPOSAL_EFFECT_PROOF": "G6",
             "G7_PRODUCTION_AND_CONTINUOUS_OPERATION": "G7"}.get(gate["id"], gate["id"][:2])
    gsec = section(esm, rf"^## {label} —", r"^## ")
    stale = []
    for phrase in re.findall(r"(?:at least|at most|under)\s+\w+\s+(?:percent|minutes)|blocking coverage check", gate.get("purpose", "")):
        key = re.sub(r"\s+", " ", phrase)
        alt = key.replace("at least ", "≥").replace(" percent", "%").replace("at most ", "≤")
        if key not in gsec and alt not in gsec:
            stale.append(key)
    out.append(flag(f"state.yaml current_gate.purpose carries predicates the ESM no longer states: {stale}") if stale else ok("state.yaml gate purpose agrees with the ESM exit predicates"))
    # --- canary bundle health
    reviews = sorted((REPO / "candidates").rglob("review.json"), key=lambda p: p.stat().st_mtime)
    if reviews:
        try:
            rv = json.loads(reviews[-1].read_text(encoding="utf-8"))
            verdict = rv.get("verdict") or rv.get("decision") or "?"
            findings = rv.get("findings") or []
            blocking = sum(1 for f in findings if isinstance(f, dict) and str(f.get("severity", f.get("blocking", ""))).lower() in ("blocking", "true"))
            out.append((info if verdict == "ACCEPT" else flag)(f"latest sealed review: {verdict}, findings {len(findings)}, blocking {blocking} ({reviews[-1].parent.name[:12]}, {dt.datetime.fromtimestamp(reviews[-1].stat().st_mtime).strftime('%d %H:%M')})"))
        except Exception as exc:
            out.append(info(f"review.json unreadable: {exc.__class__.__name__}"))
    sealed = len([p for p in (REPO / "candidates").rglob("manifest.json")])
    out.append(info(f"sealed bundles on disk: {sealed}; progress.current_candidates {sy['progress']['current_candidates']}"))
    # --- lanes (project/lanes/*.yaml; branches <lane>/<ITEM>; PRs labelled <lane>)
    metrics["lanes"] = {}
    for lane_path in sorted((REPO / "project/lanes").glob("*.yaml")):
        try:
            lane = load_yaml(lane_path)
            name = lane.get("lane", lane_path.stem)
            label = lane.get("pr_label", name)
            statuses = {i["id"]: i["status"] for i in lane.get("items", [])}
            prs = json.loads(subprocess.run(["gh", "pr", "list", "--label", label, "--state", "all", "--limit", "8", "--json", "number,state,title,headRefName,mergedAt"],
                                            cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=60).stdout or "[]")
            pr_line = "; ".join(f"#{p['number']} {p['state']} {p['headRefName'][:22]}" for p in prs[:4]) or "no PRs yet"
            open_items = [i for i, s in statuses.items() if s not in ("ACCEPTED", "DONE", "BLOCKED_EXTERNAL")]
            metrics["lanes"][name] = {"statuses": statuses, "prs": len(prs), "open": open_items}
            out.append(info(f"{name}: items {statuses}; PRs: {pr_line}; progress {lane.get('progress')}"))
            if open_items:
                out.append(info(f"{name}: open items {open_items} — a run must be live for the first one, else spawn (procedure 2b); one item per run"))
            # merged lane PRs touching non-lane paths
            for p in prs:
                if p.get("mergedAt"):
                    sha = git("log", "--format=%h", f"--grep=(#{p['number']})", "-1", "origin/main").strip()
                    if sha:
                        files = git("show", "--name-only", "--format=", sha).split()
                        KNOWN_SHARED_TOUCH = ("tests/components/readme/extractors/platforms/test_registry.py",)  # known_ecosystems() literal; every lane needs this until G4-W17 (6) lands
                        bad = [f for f in files if not (f.startswith(("candidates/", f"evidence/build/lanes/{name}/", f"project/lanes/{name}.yaml", f"docs/RESEARCH_{name.upper().replace('-', '_')}.md")) or re.search(r"extractors/platforms/(test_)?(typescript|go|rust|cpp|java|net)\w*\.py$", f) or f in KNOWN_SHARED_TOUCH)]
                        if bad:
                            out.append(flag(f"{name} PR #{p['number']} ({sha}) touched non-lane paths: {bad[:4]}"))
        except Exception as exc:
            out.append(info(f"lane check skipped for {lane_path.name}: {exc.__class__.__name__}: {exc}"))
    # --- open PRs by AGE, label-independent (PHASE1/F1: PRs #29/#30 carried no lane label, and no
    # code anywhere computed a PR's age — 3 d 18 h stranded, invisible to the label-scoped query
    # above even when the reviewer was alive; merged lane PRs normally land ~3 min after CI green)
    try:
        allprs = json.loads(subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "30", "--json", "number,createdAt,labels,headRefName"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=60).stdout or "[]")
        aged = 0
        for p in allprs:
            pr_labels = {lb.get("name", "") for lb in p.get("labels", [])}
            age_min = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00"))).total_seconds() / 60
            if age_min > 30 and "hold" not in pr_labels:
                aged += 1
                out.append(flag(f"open PR #{p['number']} ({p['headRefName'][:30]}) is {age_min:.0f} min old with no 'hold' label — adopt or close it this wake (loop-prompt §1.1 pushed-but-unmerged)"))
        if not aged:
            out.append(ok(f"no open PR older than 30 min ({len(allprs)} open)"))
    except Exception as exc:
        out.append(info(f"open-PR age check skipped: {exc.__class__.__name__}"))
    wt_raw = git("worktree", "list", "--porcelain")
    wt_blocks = [b for b in wt_raw.strip().split("\n\n") if b.strip()]
    prunable_wt = [b.splitlines()[0].split(" ", 1)[1] for b in wt_blocks if "prunable" in b]
    leftover_wt = [b.splitlines()[0].split(" ", 1)[1] for b in wt_blocks if ".claude" in b.splitlines()[0]]
    if prunable_wt or leftover_wt:
        out.append(flag(f"worktrees needing attention — prunable: {prunable_wt}; .claude leftovers: {leftover_wt} — a dead lane leaves its worktree behind; inspect for unlanded work, then `git worktree prune`"))
    else:
        out.append(ok("no stale worktrees"))
    # --- deadline
    hours_left = (DEADLINE - now).total_seconds() / 3600
    q = [x["id"] for x in sy.get("next_ready_items") or []]
    cand_items = [i for i in q if i in CANDIDATE_ITEMS]
    non_cand = [i for i in q if i not in CANDIDATE_ITEMS]
    metrics["hours_left"] = round(hours_left, 1)
    out.append(info(f"deadline {DEADLINE.strftime('%a %d %b %H:%M')}: {hours_left:.1f} h left; queue {len(q)} = {len(cand_items)} candidate-producing {cand_items} + {len(non_cand)} other {non_cand}"))
    rate_h = state.get("hours_per_item")
    if rate_h:
        need = rate_h * len(q)
        out.append((flag if need > hours_left else ok)(f"at {rate_h:.1f} h/item the queue needs ~{need:.0f} h vs {hours_left:.0f} h left — " + ("BEHIND: defer non-candidate items, split cohorts, message the loop" if need > hours_left else "on pace")))
    return out


# ----------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    now = dt.datetime.now().astimezone()
    if a.since:
        since = dt.datetime.fromisoformat(a.since)
    elif a.hours:
        since = now - dt.timedelta(hours=a.hours)
    else:
        since = dt.datetime.fromisoformat(state.get("last_wake", (now - dt.timedelta(hours=2)).isoformat()))
    since_iso = since.isoformat(timespec="seconds")
    since_z = to_utc_z(since_iso)
    window_min = (now - since).total_seconds() / 60

    t = parse_transcript(since_z)
    lines: list[str] = []
    lines.append(f"# Reviewer check {now.strftime('%Y-%m-%d %H:%M')} — window since {since.strftime('%H:%M')} ({window_min:.0f} min)")

    # 0 self-liveness: verify the reviewer's OWN mechanisms are actually running, not just built.
    # Added 2026-09-06 after three incidents in one day, all the same shape (a safeguard built,
    # never re-checked): a scheduled cron silent for ~6 hours unnoticed; unblock_monitor.py's own
    # ITEM_UNLOCKS table missing entries for instructions already written in RESEARCH's own arrival
    # list. This section is deliberately first — "did my own tools actually fire" is checked before
    # anything they were supposed to catch.
    lines.append("## 0 Self-liveness (reviewer's own mechanisms, not the loop's)")
    prior_wake = state.get("last_wake")
    if prior_wake:
        gap_min = (now - dt.datetime.fromisoformat(prior_wake)).total_seconds() / 60
        # This script is invoked every 20 min by cron; a gap over ~35 min means a scheduled fire
        # was missed (own history, not the loop's — this is exactly the check that would have
        # caught the ~6-hour 2026-09-06 gap on its own next run, instead of by accident).
        if gap_min > 35:
            lines.append(flag(f"reviewer's own last wake was {gap_min:.0f} min ago (cron expects ~20) — a scheduled fire was missed; do not trust cron alone, cross-check active Monitor tasks"))
        else:
            lines.append(ok(f"reviewer cadence: last wake {gap_min:.0f} min ago"))
    else:
        lines.append(info("no prior wake recorded (first run, or state file reset)"))
    tr_note = resolution_report(TRANSCRIPT)
    if tr_note and tr_note.startswith("TRANSCRIPT_WARNING"):
        lines.append(flag(tr_note))
    elif tr_note:
        lines.append(info(tr_note))
    else:
        lines.append(ok(f"transcript: {TRANSCRIPT.name} (fresh)"))
    # PHASE1/F1: the old check here compared unblock_monitor's hand table against one prose phrasing
    # ("after (N)... re-spawn") the arrival list stopped using — it printed a confident OK while the
    # table was 16 items behind. The table is retired; the check is now structure vs structure: every
    # item the section-31 prose says landed must have an unblocked.jsonl ledger record (the executor
    # appends one per landing — a gap means the ledger discipline broke, procedure section 2c).
    try:
        from unblock_monitor import landed_items
        landed = landed_items()
        no_ledger = sorted(item for item, unlocks in landed.items() if unlocks is None)
        if no_ledger:
            lines.append(flag(f"arrival item(s) {no_ledger} read as landed in section 31 but have no unblocked.jsonl record — ask the executor to append them (unlock targets are in each item's own bracket citation)"))
        else:
            lines.append(ok(f"unblock ledger covers every landed arrival item the log names ({len(landed)} landed)"))
    except Exception as exc:
        lines.append(info(f"ledger self-check skipped: {exc.__class__.__name__}: {exc}"))

    # 1 liveness
    lines.append("## 1 Liveness")
    last_ts = t["last_ts"]
    idle_min = (now - parse_ts(last_ts).astimezone()).total_seconds() / 60 if last_ts else None
    wk = t["wakeups"]
    last_wk = wk[-1] if wk else None
    if last_wk and last_wk[1].get("stop"):
        lines.append(flag(f"loop STOPPED itself (ScheduleWakeup stop:true at {local(last_wk[0])}) — re-arm"))
    if t["limit_hit"]:
        lines.append(flag(f"session limit text at {local(t['limit_hit'][0])}: {t['limit_hit'][1][:100]} — re-arm when reset passes"))
    if idle_min is None:
        lines.append(flag("no transcript records in window — loop silent all window"))
    elif idle_min > 45:
        lines.append(flag(f"loop silent for {idle_min:.0f} min (last record {local(last_ts)})"))
    else:
        lines.append(ok(f"loop active {idle_min:.0f} min ago; last wakeup {local(last_wk[0]) if last_wk else '-'} delay {last_wk[1].get('delaySeconds') if last_wk else '-'}s"))
    lines.append(info(f"last text: {norm(t['last_text'])[:160]}"))
    lines.append(info(f"CI: {ci_state()}"))

    # 2 iteration accounting
    lines.append("## 2 Iteration accounting (window)")
    d = t["durations"]
    tool_total = sum(d.values())
    span_min = ((parse_ts(t["last_ts"]) - parse_ts(t["first_ts"])).total_seconds() / 60) if t["first_ts"] else 0
    n_iter = len(wk)
    lines.append(info(f"iterations ended: {n_iter}; span {span_min:.0f} min; avg {span_min / n_iter:.0f} min/iteration" if n_iter else f"iterations ended: 0; span {span_min:.0f} min (one long iteration or silence)"))
    parts = ", ".join(f"{k} {v / 60:.0f}m" for k, v in d.most_common(7))
    lines.append(info(f"tool wall-clock {tool_total / 60:.0f} min of {span_min:.0f} ({(tool_total / 60 / span_min * 100) if span_min else 0:.0f}%): {parts}"))
    c = t["counts"]
    cm = commits_since(since_iso)
    loop_commits = cm["loop"]
    full = c.get("bash:pytest_full", 0)
    lines.append(info(f"loop commits {len(loop_commits)} ({collections.Counter(x['type'] for x in loop_commits).most_common(4)}); owner commits {len(cm['owner'])}"))
    # rules
    lines.append("## 3 Rule compliance (loop-prompt 0, 3, 4)")
    if loop_commits:
        ratio = full / len(loop_commits)
        lines.append((ok if ratio <= 1.5 else flag)(f"full pytest runs per loop commit: {full}/{len(loop_commits)} = {ratio:.1f} (rule: once per commit; focused runs {c.get('bash:pytest_focused', 0)})"))
    else:
        lines.append(info(f"full pytest runs {full}, focused {c.get('bash:pytest_focused', 0)}, no loop commit in window"))
    pt = t["pytest_times"]
    if pt:
        lines.append((ok if pt[-1][2] <= 150 else flag)(f"suite wall-clock (last 3 full): {', '.join(f'{x[2]:.0f}s' for x in pt[-3:])} — {pt[-1][1]}"))
    pres = len(t["presents"])
    lines.append((ok if pres <= max(1, len(loop_commits)) else flag)(f"canary present runs {pres} vs commits {len(loop_commits)} (rule: at predicate closure or acceptance)"))
    lines.append((ok if t["ci_watch_seconds"] < 300 else flag)(f"CI watch time {t['ci_watch_seconds'] / 60:.0f} min (rule: push and continue)"))
    long_bodies = [x for x in loop_commits if x["words"] > 120]
    lines.append((ok if not long_bodies else flag)(f"commit bodies over 120 words: {len(long_bodies)}" + (f" e.g. {long_bodies[0]['sha']} {long_bodies[0]['words']}w" if long_bodies else "")))
    lp_touch = t["lp_touches"]
    lines.append((ok if lp_touch >= n_iter else flag)(f"loop-prompt reads {lp_touch} vs iterations {n_iter} (rule 0: read in full each iteration)"))
    total_read = sum(t["reads"].values())
    top = sorted(t["reads"].items(), key=lambda kv: -kv[1])[:5]
    lines.append(info(f"reads (Read tool + sed/cat/grep): {t['read_calls']} calls, ~{total_read / 4 / 1000:.0f}k tokens; top: " + "; ".join(f"{Path(k).name} ~{v / 4 / 1000:.0f}k" for k, v in top)))
    big_research = sum(v for k, v in t["reads"].items() if k.endswith("RESEARCH_AND_GUIDELINES.md"))
    if big_research / 4 > 60_000:
        lines.append(flag(f"RESEARCH read volume ~{big_research / 4 / 1000:.0f}k tokens this window (rule 0: read named sections, not the file)"))

    # 4 governance + growth + section 31
    lines.append("## 4 Governance consistency, growth signals, section 31")
    rc, metrics = repo_checks(state, since_iso)
    lines.extend(rc)
    lines.append("## 4b Behaviour, quality, deadline")
    try:
        lines.extend(behaviour_checks(t, state, metrics, since_iso, now, loop_commits))
    except Exception as exc:  # a broken check must not hide the rest of the report
        lines.append(flag(f"behaviour_checks crashed: {exc.__class__.__name__}: {exc}"))

    # 5 progress & rate
    lines.append("## 5 Progress and rate")
    hist = state.get("history", [])
    cands = metrics["candidates"]
    since_rise = 0
    for h in reversed(hist):
        if h.get("candidates", cands) < cands:
            break
        since_rise += h.get("iterations", 0)
    since_rise += n_iter
    same_active = sum(1 for h in reversed(hist) if h.get("active_id") == metrics["active_id"]) + 1
    # accepted = worked under its ID (commit subject suffix) and no longer queued or active
    subj_dates = git("log", "--format=%ct%x1f%s", "--since=2026-09-02")
    last_seen: dict[str, int] = {}
    for rec in subj_dates.splitlines():
        if "\x1f" not in rec:
            continue
        ct, s = rec.split("\x1f", 1)
        m = LOOP_SUBJECT.search(s)
        if m:
            last_seen.setdefault(m.group(2), int(ct))  # newest first
    queued_or_active = set(metrics["queue_ids"]) | {metrics["active_id"]}
    accepted = {i: ct for i, ct in last_seen.items() if i not in queued_or_active}
    now_ct = int(now.timestamp())
    acc_24h = sorted((ct, i) for i, ct in accepted.items() if now_ct - ct <= 86400)
    acc_window = [i for ct, i in acc_24h if now_ct - ct <= window_min * 60]
    lines.append(info(f"candidates {cands}/34; iterations since the count last rose: {since_rise}; active {metrics['active_id']} seen at {same_active} consecutive wakes"))
    lines.append((flag if same_active >= 4 and not acc_window else info)(
        f"items accepted: {len(acc_window)} this window, {len(acc_24h)} in 24 h, {len(accepted)} since 2026-09-02; queue {len(metrics['queue_ids'])} items"))
    if acc_24h:
        hours_per = 24 / len(acc_24h)
        state["hours_per_item"] = round(hours_per, 2)
        newest = dt.datetime.fromtimestamp(acc_24h[-1][0]).astimezone().strftime("%H:%M")
        lines.append(info(f"rate: ~{hours_per:.1f} h per accepted item over 24 h (last: {acc_24h[-1][1]} at {newest}); "
                          f"queue at that rate ~{hours_per * len(metrics['queue_ids']):.0f} h vs {metrics.get('hours_left', '?')} h to the deadline"))

    lines.append("## 6 Flags to judge" if FLAGS else "## 6 No flags — noop wake")
    for f in FLAGS:
        lines.append(f"  - {f[:200]}")

    report = "\n".join(lines)
    print(report)
    if a.record:
        hist.append({
            "ts": now.isoformat(timespec="seconds"), "window_min": round(window_min), "iterations": n_iter,
            "candidates": cands, "active_id": metrics["active_id"], "loop_commits": len(loop_commits),
            "accepted": len(acc_window), "pytest_full": full, "presents": pres,
            "tool_min": round(tool_total / 60), "read_ktok": round(total_read / 4000), "flags": len(FLAGS),
            "acceptance_hash": metrics.get("acceptance_hash"), "hours_left": metrics.get("hours_left"),
        })
        state["history"] = hist[-60:]
        state["last_wake"] = now.isoformat(timespec="seconds")
        state["reviewed_entries"] = metrics["s31_total"]
        state["reviewed_head"] = git("rev-parse", "--short", "HEAD").strip()
        STATE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
        print(f"\n[recorded] history {len(hist)} wakes; reviewed_entries {metrics['s31_total']}")
    if a.json:
        print(json.dumps({"metrics": metrics, "flags": FLAGS}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
