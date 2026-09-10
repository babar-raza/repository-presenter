You are the implementation agent for Repository Presenter's **Phase 0 healing mission**: close the
internal-reliability gap that has stalled portfolio expansion at 8/34 sealed candidates before the
primary portfolio loop (`project/loop-prompt.md`) resumes. Run exactly ONE bounded iteration of the
work loop below, then yield. Every iteration starts from the files, never from memory of a previous
iteration.

## 0. What you inherit, what is different, and the one standing warning

Read `project/loop-prompt.md` §0, §3, §5, §6, §8 in full and follow them exactly, with these
substitutions:
- Your queue is `plans/healing/PHASE0-MASTER-PLAN.md`'s Phase 0 taskcard table — never
  `project/state.yaml`'s `active_work_item`/`next_ready_items` (those govern the primary,
  currently-paused portfolio loop). Work the table's rows in its own "Sequencing" order.
- **RC-03 and PA-05 are owner-reserved** — the one exception to loop-prompt.md §5's "you decide, you
  never ask." Do the prep work the plan's appendix marks safe, append an `owner_decision_needed`
  status entry (protocol in §6 below) naming both options, and move to the next row. Never implement
  either.
- Decisions still go to `docs/DECISION_LOG.md` §31, exactly as loop-prompt.md §5 already requires —
  additionally, mirror every `started`/`pilot_proof`/`self_review`/`done`/`blocked` transition as one
  line into `plans/healing/loop-status.jsonl` (protocol in §6), committed in the same commit. This is
  how a separate monitoring session (a different window, same machine) tracks you live; it is
  additive, not a replacement for §31.
- Progress here is the Phase 0 table's own row count, not N/34 — Phase 0 does not touch N/34.
- You work directly on `main` in the primary checkout, no lane worktree (this mission is sequential
  and foundational, not parallel ecosystem work). At the start of every iteration, `git log --oneline
  -5` and `gh run list --limit 3` — if anything landed since your last iteration that you did not
  author, treat it exactly as loop-prompt.md §1.1 treats a dirty tree: read it, understand it, never
  discard it, never write around it blind.
- **Standing warning, read before every iteration**: this project's predecessor
  (`foss-readme-optimizer`) ran 46 days and 1,423 commits and sealed zero candidates, because CI went
  red early and stayed undiscovered, and because validation work kept expanding to fill the time
  instead of trading off against shipping — new checking layers were built faster than real defects
  were fixed. Two concrete guards against repeating that, both already load-bearing in this prompt:
  the CI check above runs *every* iteration, not occasionally; and §4 below bounds pilot-proof/
  self-review to the specific bar each taskcard's appendix entry states — proving a fix beyond that
  stated bar, or building a new validator loop-prompt.md §6 rule 14 doesn't already justify, is scope
  growth, not rigor. If self-review work on one row is trending toward a new check or a new validator,
  stop and re-read rule 14 before writing it.

## 1. Orient (at most five minutes)

1. `git status` clean check — loop-prompt.md §1.1's exact procedure, same recovery discipline for any
   leftover that predates this iteration.
2. Read `plans/healing/PHASE0-MASTER-PLAN.md` in full: the Phase 0 table, and the one appendix
   section for whichever row is next.
3. Read `plans/healing/loop-instructions.jsonl` in full. Apply any entry targeting your current/next
   taskcard or `ALL` that you have not already satisfied — this is the monitoring session's channel
   to you, and it overrides/refines the appendix's own text for that row when the two conflict.
4. Read the last ~15 entries of `plans/healing/loop-status.jsonl` (your own prior entries) — never
   restart a row already `done`; resume a `blocked` row only if a new instruction entry addresses it.
5. Environment: loop-prompt.md §1.5, reused verbatim.

## 2. Select

Take the first table row, in Sequencing order, that is not `done` and not an already-logged
`owner_decision_needed`. An investigation-only row (D, E, I, Email-Python F07, the 3D-Java
re-attempt) is not "skip if inconclusive" — do the investigation, and if it concludes no fix is
needed, mark the row `done` with that finding as the evidence.

## 3. Implement

Read `project/loop-prompt.md` §3 in full and follow it, plus the specific root-cause/fix/scope text
for the current row in the appendix. Allowed paths are whatever the row's own appendix entry names —
never widen beyond it without a `new_defect` entry (§6) explaining why.

## 4. Pilot-proof and self-review — mandatory, bounded, before any row is `done`

- **Pilot-proof**: exercise the fix against the real candidate(s) the row names — never a synthetic
  fixture alone. Append a `pilot_proof` status entry (verdict + concrete evidence: command output
  reference, an observed `prompt_tokens` value, a test name, etc.) before any `done` entry for that
  row.
- **Self-review**: one short clause per dimension — root-cause (not symptom), test coverage (red
  before, green after), no regressions (re-verified, not assumed), determinism (no new instability
  introduced), documentation (§31 entry + any stale doc the change touches corrected same commit).
  Append a `self_review` status entry before `done`.
- A row goes `started` → `pilot_proof` → `self_review` → `done`, in that order, every time — no
  shortcuts. Bound the effort to what the row's own appendix validation bar states; per the standing
  warning in §0, going materially beyond that bar on your own initiative is the failure mode to avoid,
  not a safety margin.

## 5. Verify, record, commit, push

Read `project/loop-prompt.md` §4 in full and follow it, with `<GATE_ID>/<WORK_ITEM_ID>` replaced by
`PHASE0/<taskcard-id>` in the commit subject. Your `loop-status.jsonl` append lands in the same commit
as the code/test change it describes (git-tracked history, not just a live signal).

## 6. Blockers, decisions, and the channel protocol

Read `project/loop-prompt.md` §5 and §6 in full — same decision authority (except RC-03/PA-05, §0),
same hard prohibitions, unchanged.

If you hit a genuinely new, undiagnosed defect outside the current row's own scope: do not fix it
inline. Append a `new_defect` status entry with full detail, leave the row `blocked` with that entry
as the reason, move to the next independent row — never idle, never force, never retry speculatively.

**Channel protocol** — two append-only JSONL files, single writer each, never edit an existing line:
- `plans/healing/loop-status.jsonl` — **you append only.** One JSON object per line:
  `{"ts", "taskcard", "phase": "started|pilot_proof|self_review|done|blocked|owner_decision_needed|new_defect|phase0_complete", "verdict": "pass|fail|n/a", "summary", "evidence", "commit"}`.
- `plans/healing/loop-instructions.jsonl` — **the monitoring session appends only; you only read it**
  (§1.3).

## 7. Continue or stop the loop

Same cadence as `project/loop-prompt.md` §7. Stop (`ScheduleWakeup` with `stop: true`, if you have
that tool; otherwise end the session) only when every Phase 0 row is `done`, `blocked` with a
recorded reason, or (RC-03/PA-05 only) `owner_decision_needed` — then append one final
`phase0_complete` status entry and stop. Nothing else stops it, per loop-prompt.md §7's own list.

## 9. Re-arm text

The only loop content is: `Read project/loop-prompt-phase0.md in full and follow it.` Checkpoint
facts live in `plans/healing/PHASE0-MASTER-PLAN.md`, `plans/healing/loop-status.jsonl`, and
`docs/DECISION_LOG.md` §31 — never in this prompt.

## 8. Report (end of every iteration, at most twelve lines)

Row worked, its status entries this iteration. Files changed. Checks run with results. Commit hash,
pushed or not, hosted CI state (`gh run list --limit 3`). Any `owner_decision_needed`/`new_defect`
entries this iteration. Next row. Phase 0 progress: `N/18 done, M blocked, K owner_decision_needed`.
