# Phase 1 sprint loop — one bounded iteration

## 0. What you inherit, what is different

Read `project/loop-prompt.md` §0, §3, §5, §6, §8 in full and follow them exactly, with these
substitutions:
- Your queue is `plans/sprint/PHASE1-SPRINT-PLAN.md`'s taskcard table — F-cards in slot order,
  W-cards by wave — never `project/state.yaml`'s `next_ready_items`. `state.yaml` stays the
  portfolio cursor: a seal updates `progress.current_candidates` only by `loop-prompt-lane.md`
  §0's rebase-then-recount rule; arrival-item landings stay under the active item exactly as
  today (`(G3_PYTHON_COHORT/G4-W17)` commits); `next_ready_items` is untouched by sprint work.
- Progress here has two units: the card table's own row count AND N/34 from
  `repository-presenter status`. A W-card candidate closes only on a bundle at
  `READY_FOR_PROPOSAL` verified on disk.
- Arrival item 54 (quick_start conditional) is owner-authorized (§31, 2026-09-11) but lands
  through the README_CONTRACT revision protocol: the contract row edit, schema, tests, and the
  measured zero-sealed-byte-movement acceptance line in the same commit.
- Standing warning: `loop-prompt-phase0.md` §0's predecessor warning applies verbatim —
  validation work never expands to fill time; a new check needs loop-prompt §6 rule 14
  justification.

## 1. Orient (at most five minutes)

1. `git status` clean check — `loop-prompt.md` §1.1's exact procedure, including its
   pushed-but-unmerged and worktree sweeps.
2. Read `plans/sprint/PHASE1-SPRINT-PLAN.md` in full: the table, and the appendix for the next
   card.
3. Read `plans/sprint/loop-instructions.jsonl` in full — the supervisor's channel to you; it
   overrides a card's text for that card when the two conflict.
4. Read the last ~15 entries of `plans/sprint/loop-status.jsonl` — never restart a done card;
   resume a blocked card only if a new instruction entry addresses it.
5. `gh run list --limit 3` (a red completed main run is this iteration's first work).
6. Environment: `loop-prompt.md` §1.5, reused verbatim.

## 2. Select

Take the first card, F-cards in slot order before W-cards, that is not done and not blocked with
an unaddressed reason. One shared-code item in progress, ever (loop-prompt §2). Within a wave,
the wave's own candidate order; a candidate that hits a real rejection gets its disposition
(failure class + resume predicate) and you move to the next candidate — stop, don't force (§5).

## 4. Ladder and seal verification

F-cards: `started` → `pilot_proof` → `self_review` → `done`, `loop-prompt-phase0.md` §4's exact
bars, each transition one status line committed with the work. W-cards: the seal is the
evidence — read the bundle manifest on disk (state, BC results, review verdict +
`second_reader.read` ≥ 2 once F6 is done, no-op proof) before appending the `seal` status line;
never report the intent as the result.

## 5. Verify, record, commit, push

`loop-prompt.md` §4 in full, with commit subjects: F-cards
`<type>(<scope>): <what> (PHASE1/<card>)`; arrival-item landings keep `(<GATE>/G4-W17)`; seals
keep the existing seal convention. The status.jsonl append lands in the same commit as the work
it describes. On landing any arrival item, append its `unblocked.jsonl` ledger line in the same
commit (item, landed_at, unlocks from the item's own bracket citation).

## 6. Blockers, decisions, channel

`loop-prompt.md` §5 and §6 in full — same decision authority, same prohibitions. A genuinely new
undiagnosed defect outside the current card: append a `new_defect` status line, leave the card
blocked, move to the next independent card — never idle, never force, never retry speculatively.

Channel protocol — two append-only JSONL files, single writer each, never edit an existing line:
- `plans/sprint/loop-status.jsonl` — **you append only.** One JSON object per line:
  `{"ts", "card", "phase": "started|pilot_proof|self_review|done|blocked|new_defect|seal|disposition|sprint_complete",
  "verdict": "pass|fail|n/a", "summary", "evidence", "commit"}`.
- `plans/sprint/loop-instructions.jsonl` — **the supervisor appends only; you only read it**
  (§1.3).

## 7. Continue or stop the loop

`loop-prompt.md` §7 verbatim — every iteration, productive or not, schedules the next wakeup;
60–120 s after a productive one. Self-scheduling is load-bearing (§31 2026-09-11 REVERSES the
2026-09-10 17:35 external-continuation instruction); the supervisor's nudges are additive, never
required. Stop only when every card is done or blocked with a recorded reason — then append one
`sprint_complete` line and stop.

## 9. Re-arm text

The only `/loop` content is: `Read project/loop-prompt-sprint.md in full and follow it.`
Checkpoint facts live in `plans/sprint/PHASE1-SPRINT-PLAN.md`, `plans/sprint/loop-status.jsonl`,
and `docs/DECISION_LOG.md` §31 — never in this prompt.

## 8. Report (end of every iteration, at most twelve lines)

Card worked + its transitions. Files changed. Checks run with results. Commit hash, pushed or
not, hosted CI state. Count from `repository-presenter status` (recomputed, not remembered).
Flags raised (aged PRs, orphan worktrees). Next card. Sprint progress: `F <a>/<b> done, seals
N/34`.
