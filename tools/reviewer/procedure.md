# Reviewer wake procedure v3 (owner's steering session) — deadline mode until 2026-09-07 00:00 +05:00

**2026-09-06 ~10:30: the owner moved the primary loop and this session to a cheaper model (Sonnet,
from Opus/Fable) and said usage no longer limits scope — "finish all candidates today at any cost,
vigilant supervision required."** Usage is not the constraint anymore; executor capability and
correction latency are. Read every wake's compliance and quality sections with more suspicion than
before, not less: a weaker executor under "at any cost" pressure is the exact combination that
produces accept-in-part, weakened tests, and confident-sounding but unverified fixes. Cadence is
hourly (cron) plus the event monitor; drop to sub-hourly manual checks around any accept, any gate
transition, or any commit whose subject or body reads confident but vague.

Purpose: detect, within one wake, anything that would stop, stall, misdirect, or slow the loop — and
correct it without waiting: governance edits, queue surgery, and short corrective messages to the
loop session. A deterministic check first; judgment only on its flags; an action for every flag.
Cadence: cron hourly at :07 (job in CronList) plus the event monitor `stop_monitor.py` (Monitor task
b91h48h7c: LOOP_STOPPED / LOOP_CAPPED / LOOP_SILENT / LOOP_RESUMED) — on an event, run step 2's
liveness action at once.

Repo: D:\Users\prora\OneDrive\Documents\GitHub\repository-presenter
Scratchpad (this directory): reviewer_check.py, stop_monitor.py, portfolio_census.py,
reviewer_state.json (history + `watch`), commit_msg.txt.
Loop transcript: C:\Users\prora\.claude\projects\d--Users-prora-OneDrive-Documents-GitHub-repository-presenter\4705e217-53a5-4974-aa24-559ae9abbd05.jsonl
Never touch src/, tests/, prompts/, schemas/, or a path the active item owns (README_CONTRACT.md is
usually one). state.yaml only at a clean checkpoint, schema-validated. Stage own paths only; guard the
index (`git diff --cached --name-only` equals the intended list).

## 1. Run the check (one Bash)

`<repo>/.venv/Scripts/python.exe -X utf8 reviewer_check.py --record`
Sections: 1 liveness · 2 iteration accounting · 3 rule compliance (§0/§3/§4) · 4 governance
consistency · 4b behaviour, quality, deadline · 5 progress and rate · 6 flags.
"No flags — noop wake" → one-line report, stop.

## 2. Act on every flag — correction ladder

The correction channel to the loop is **SendMessage** to the loop session (ListAgents → the other
interactive repository-presenter session, never Remote Control or aspose-org). A message: starts
`Reviewer:`, states one correction and the rule or section it rests on, at most six lines, never a
question, and ends with the exact line `/loop Read project/loop-prompt.md in full and follow it.`
(loop-prompt §5 makes it binding and non-blocking). At most one message per wake unless the loop is
stopped. Every message is also a one-line §31 reviewer entry.

| Flag class | First wake | Persisting / severe |
|---|---|---|
| Stopped (stop:true) / capped / **stalled** (its last ScheduleWakeup delay has passed by > 10 min with no new record — 2026-09-06 08:45: a 300 s wakeup never fired; the session was simply idle and resumed 5 s after a message) | Re-arm at once: SendMessage `Reviewer: your <time> ScheduleWakeup (<delay>) did not fire; continue now.` + the re-arm line. Capped and reset time not passed → note it, re-arm at the first wake after; PushNotification the owner. The stop monitor alarms at delay + 10 min (min 15). | Stall twice in a day → §31 note; the loop's `ScheduleWakeup` is not reliable enough to be the only wake source, so the monitor's re-arm is standing procedure. |
| Stuck iteration (> 90 min without a commit; same test failing ≥3×; ≥15 edits without a commit; same command failing ≥3×) | SendMessage: checkpoint now — commit what passes the focused tests and one full suite, record the open predicate and the diagnosis in §31 (§5 two-attempt rule: change mechanism), continue. | Second wake same signature → split the item in §27.9 as owner (the stuck predicate becomes its own item behind the candidate-producing ones) + message. |
| Gate-exit satisfiability (active item is the gate's last) | Restate the bullet in the ESM within 500 lines against the rule it conflicts with (rule 14; §27.10 ≥3 compositions; §30.9 controls); mirror in state.yaml `current_gate.purpose` at a clean checkpoint; §31 owner entry; commit, push. | — |
| Gate purpose in state.yaml carries retired predicates | Fix at a clean checkpoint (schema-validated). | — |
| Queue / purpose differs from §27.9 | Expected for one wake after a §27.9 edit (the loop reconciles before promoting). | Second wake, or an item promoted out of order → fix state.yaml at a clean checkpoint + message. |
| Limits vs decisions (lanes flag etc.) | Fix state.yaml at a clean checkpoint. | — |
| Compliance (full-suite runs/commit > 1.5; CI watch > 5 min; bodies > 120 words; loop-prompt not read; RESEARCH read whole) | §31 control observation (measured numbers). | Second wake → SendMessage naming the rule and the measured number; one-line loop-prompt clarification only if the rule is ambiguous. Never a new rule from one reading. |
| Scope: loop commit touched loop-prompt / ESM / AGENTS / plans / workflows | Revert that hunk as owner (§6 rule 15: the loop writes measurements and §31 only) + §31 + message. | — |
| Prompts changed ≥3 commits in a window | §31 note (every prompt change re-seals). | Message: batch prompt changes, one re-seal. |
| Tests weakened (skip/xfail added; test count down; test files deleted) or a commit after a failing full suite | §31 + message: restore or justify with evidence in §31 next iteration (§5: never weaken a check). | Second wake unresolved → PushNotification the owner. |
| Active acceptance text changed while active | Compare with §27.9's Acceptance clause. Honest restatement (what happened, owner named for anything transferred) → §31 confirmation. A dropped predicate with no owner → restore it in §27.9 under the owning item + message. | — |
| Latest sealed review not ACCEPT for ≥2 wakes; present errors ≥3 | Read review.json findings: prose judgments on required rows → the two-reader rule (§31 2026-09-06 00:15) is the fix — message the loop to land it before the next composition; deterministic failures → let the loop route (§5), note in §31. | — |
| Deadline BEHIND (needed hours > hours left) | Queue surgery per §28.12's cut order as owner (defer, fold, time-box; never cut checks or dispositions); §31; message summarising the new order in two lines. | Every wake while behind: re-project; when a cohort item exceeds its box, message: seal what passes, dispositions for the rest, accept, next. |
| New §31 entries | Confirm silently unless flagged (no evidence / no reversal / scope movement / double reversal → freeze: §31 + PushNotification). **Under the weaker-model watch: read every entry, not just flagged ones, before confirming — a plausible-sounding entry with no real evidence is exactly what a weaker executor under pressure produces.** | — |
| Accept-in-part language; hedged/assumed-fixed language in a commit | Read the commit's diff and the item's acceptance predicates literally, one by one, against what actually landed. A predicate not met → the item is not accepted regardless of what the commit says; message the loop to re-open it and cite the unmet predicate. | — |
| An "ACCEPTED" gate/work-item evidence manifest with no visible evidence field | Read the full manifest before trusting the status line; if the acceptance is unearned, message the loop and record a §31 reviewer entry naming the exact unmet predicate. | — |
| Growth (module with no importer; ≥3 new check definitions; deferral language in evidence) | §31 entry asking for the importer or removal; accept-in-part → owning item named in §27.9. | Second wake → message. |

## 2b. Lanes (parallel loops; owner decisions 2026-09-06 01:20 and 08:00, RESEARCH §28.12 "Lanes")

Lanes are **Opus subagents in their own git worktrees**, one item per run: lane B (TypeScript, then
C++), lane C (Java), lane D (Go, then Rust) — files `project/lanes/<lane>.yaml`, generic prompt
`project/loop-prompt-lane.md`. Spawn with the Agent tool: `subagent_type: general-purpose`, `model:
opus`, `isolation: worktree`, `run_in_background: true`, prompt `Read project/loop-prompt-lane.md in
full and follow it; your lane is <lane>. Work ONE item this run — <ITEM> — land it by PR (branch
<lane>/<ITEM>, label <lane>, squash-merge when CI is green), then end with the report.` Keep at most
one live run per lane; note each spawn's agent id and item in reviewer_state.json `lanes`. A lane
`PROPOSAL` (shared-code defect) is admitted by adding it to G4-W17's arrival list in §27.9 (one line:
lane, file, defect, repository) — the primary lands it; when it lands, re-spawn the lane whose
dispositions it unblocks. Between runs only: edit a lane file (e.g. drop W15/W16 from lane-b.yaml,
owed since 08:00).
**While a lane run is live, never edit a lane-owned file** (`project/lanes/lane-b.yaml`,
`docs/RESEARCH_LANE_B.md`, its platform modules) — the first run hit a rebase conflict from exactly
that; corrections go by `Reviewer:` SendMessage or wait for the run to end. On its completion
notification: read its report, verify the PR merged with only lane paths touched, then spawn the next
run if an item's prerequisites hold. Spawn rules: (a) once now for `LANE-B-00`
(toolchains) — it ends when W09 is not yet accepted; (b) again when the check reports W09 accepted on
`main` and lane items are `PENDING`; (c) re-spawn if it ended with open items whose prerequisites hold
(use SendMessage to the same agent id first — context intact — else a fresh Agent). Supervise every
wake: lane-file statuses, `gh pr list --label <lane>`, CI on its PRs — **a PR with no checks at all
for several minutes is not "still queued", it is `mergeable: CONFLICTING` against a moved main and
GitHub never dispatched the workflow** (`gh pr view <n> --json mergeable,mergeStateStatus` confirms;
the lane rebases per its prompt §4) — `docs/RESEARCH_LANE_B.md` entries
(same confirm/flag rules as §31), and that its commits touch only its owned paths (`git log lane-b
--name-only`) — a lane commit outside them is reverted on `main` after merge and messaged. A lane
`PROPOSAL` entry that needs a shared-file change is the owner's decision: admit it into §27.9 for the
primary, or decline in §31. If the account's usage cap is hit, lane B pauses first (do not re-spawn
until the primary is running again). Lane B's sealed bundles count in `status` once merged.

## 3. Forward look (active item is the gate's last, or the gate changed)

Next gate's ESM section and first §27.9 item: exit predicates satisfiable? Toolchains present for the
items (§28.11 machine table; `.cmd` shims)? Owner items needed (OWNER-06 for C++)? Registry reachable?
Record gaps as owner items or §27.9 amendments *before* the gate opens. In deadline mode also: is the
next item candidate-producing, and does it carry its time box?

## 3b. §27.9 edits are atomic with state.yaml (since 2026-09-06 08:20)

`tests/test_queue_agreement.py` (the loop's, c2bfbee) fails `main` whenever a §27.9 entry is neither
queued, active, nor accepted — so a §27.9 queue edit (insert, move, removal to a lane) **must carry the
`state.yaml` reconcile in the same commit** (`git status` clean for state.yaml; rebuild
`next_ready_items` from §27.9 minus the active and worked items; schema-validate; run that test
locally before pushing). Red `main` from this class blocks every lane PR's CI; when it happens, fix
`main`, then message each lane with an open PR to rebase and push (its CI is not its defect).

## 4. Commit discipline

`git status` first; stage own paths only (docs/*.md, plans/, project/portfolio-census.json,
project/state.yaml when clean); index guard; body ≤120 words; trailer
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; push; do not wait for CI. Batch pushes.

## 5. Report (≤8 lines) and state

Wake time · loop alive/stopped (+re-armed) · CI · iterations / loop commits / accepted this window ·
compliance line · flags acted on, one clause each (message sent? yes/no) · progress N/34, h per item,
hours to deadline and BEHIND/on pace · next wake. Set `watch` in reviewer_state.json.
