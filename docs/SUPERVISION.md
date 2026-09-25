# Session Supervision

This document owns how agent sessions supervising and executing this project relate: the
supervisor session, the primary executor loop, lane agents, the monitors, and the out-of-band
dead-man. `AGENTS.md` names it authoritative for this subject. It governs sessions, not the
product runtime — `docs/STATE_MACHINE.md`'s leases and recovery are the product's (deferred to
their own gates) and nothing here builds ahead of them.

Written 2026-09-11 (PHASE1/F3) after a measured failure: every supervision mechanism ran inside
one chat session, the watcher and the watched died together on 2026-09-06 19:31, and nothing
noticed for 4.5 days — two green lane PRs sat unmerged for 3 d 18 h, invisible to a label-scoped
query even had the supervisor been alive. The design rules below each trace to that incident
class; a rule with no incident behind it is a candidate for removal, not addition
(`tools/README.md`'s own standard).

## Roles

- **Owner** — the human. Sets goals, admits work (§27.9 / sprint plans), rules on
  `owner_decision_needed`. May delegate rulings to the supervisor; the delegation is recorded in
  `docs/DECISION_LOG.md` §31.
- **Supervisor (reviewer session)** — one interactive session running
  `tools/reviewer/procedure.md`. Steers, verifies, admits, spawns lanes, corrects; never patches
  `src/` or `tests/`. Its startup checklist is procedure §0 — self-liveness before trust.
- **Primary executor** — one interactive session running `project/loop-prompt.md` (or the active
  mission prompt, e.g. `project/loop-prompt-sprint.md`, which inherits it). Owns `src/`, `tests/`,
  the cursor, and gate evidence. Continues itself by self-scheduled wakeups (§ Wakeup policy).
- **Lane agents** — Sonnet subagents in isolated worktrees (`project/loop-prompt-lane.md`), one item
  per run, landing by self-merged PR. Spawned and supervised by the supervisor (procedure §2b). Never
  spawn a lane, or any background subagent, with the Agent tool's `model` parameter set to anything
  other than Sonnet (Opus and Fable are both prohibited there) — owner cost ruling 2026-09-06
  (primary/reviewer), extended to lanes 2026-09-16 (§31).
- **Monitors** — `stop_monitor.py`, `timestamp_monitor.py`, `unblock_monitor.py`, run under the
  supervisor's Monitor tool. In-band: they die with the supervisor, and know it — each announces
  `WATCHING <transcript>` at startup and warns on a stale target (transcript_path.py).
- **Dead-man** — `.github/workflows/liveness.yml`, the one supervisor that survives session death,
  reboot, and sleep. Scheduled every 30 minutes; read-only; fails loudly on stranded artifacts.

## The supervision matrix

| Actor | Watches | Watched by |
|---|---|---|
| Primary executor | its own CI, tree, cursor | monitors, supervisor wakes, liveness.yml (via main inactivity) |
| Lane agent | its own PR's CI | supervisor (spawn record, completion notification), liveness.yml (PR age) |
| Supervisor | everything above | **liveness.yml** (its only mechanical watcher — a dead supervisor's artifacts strand within 30–60 min and turn a scheduled run red), plus any owner-directed advisor session (see below) |
| Monitors | executor transcript, decision log, ledger | supervisor §0 re-arm; their own startup `WATCHING` line |
| liveness.yml | PRs, branches, main cadence | GitHub itself (schedule); the supervisor polls `gh run list --workflow liveness.yml` each wake |

**Advisor sessions.** The owner may run an independent verification session that re-derives real
git, CI and liveness state and cross-checks it against what this supervision layer claims. It owns
no paths, spawns nothing, and holds no authority over the queue — it reports. Its messages are
prefixed `Advisor:` and carry one finding with its evidence. Treat such a finding exactly like a
reviewer flag: verify it against the artifact yourself, then act or record why not. It answers the
one question this matrix otherwise answers only mechanically — who checks the checker — and its
value depends entirely on it re-deriving state rather than reading these records back (2026-09-11,
the owner stood one up mid-sprint).

No node is unwatched. The recovery from any single death is the same: a fresh session runs
procedure §0 end to end. Durable state (channels, cursors, taskcard tables, reviewer_state) lets
it resume from the first non-done unit of work.

## Channels

Two append-only JSONL files per mission, single writer each, committed with the work they
describe (the Phase-0 contract, proven 2026-09-10):

- `plans/<mission>/loop-status.jsonl` — the executor appends one line per transition
  (`{"ts","card","phase","verdict","summary","evidence","commit"}`); never edited.
- `plans/<mission>/loop-instructions.jsonl` — the supervisor appends steering; the executor reads
  it in full every Orient, and it overrides a card's text for that card on conflict.

Urgent mid-iteration corrections go by SendMessage: first word `Reviewer:`, one correction and the
rule it rests on, at most six lines, never a question, ending with the exact re-arm line for the
active prompt. At most one per wake unless the loop is stopped; every message is also a §31 line
(procedure §2). Lanes take corrections the same way, addressed to the recorded agent id — there is
deliberately no polled file for lanes; one-item-per-run keeps runs short enough that SendMessage
plus respawn covers every case. A lane-owned file is never edited while its run is live.

## Lane lifecycle and its liveness contract

Spawn (procedure §2b, recorded in `reviewer_state.json` `lanes.<lane>` as
`{live_run: <agent id>, item, spawned_at}`) → fresh short-path worktree off `origin/main` → one
item → PR carrying the `<lane>` label on a `<lane>/<ITEM>` branch (the lane confirms both after
`gh pr create`; an unlabeled PR is invisible to supervision) → CI → self-merge → lane-yaml
progress update in the follow-up commit → report → end.

Death at any step is covered by an age rule, not by hope: merged lane PRs land ~3 minutes after CI
turns green (27 of 29 measured), so **any open PR older than 30 minutes without a `hold` label is
stranded work** — flagged by liveness.yml and by `reviewer_check.py` label-independently, adopted
or closed by the supervisor within one wake (`loop-prompt.md` §1.1's recovery discipline, which
covers pushed-but-unmerged work explicitly). A dead lane's worktree stays on disk: `git worktree
list` is part of every Orient and every supervisor wake; orphans are inspected, then pruned.
Respawn: SendMessage to the same agent id first (context intact), else a fresh spawn; the
unblock ledger (`unblocked.jsonl`) fires the moment a landed shared-code item makes a lane's
disposition re-runnable.

## Concurrency floor

Whenever `execution_limits.parallel_repository_work_allowed` is true and at least one lane has
ready, unblocked work with no live run, the supervisor keeps **≥5 roles concurrently live** —
itself, the primary executor, and lanes — spawning per the lane spawn recipe (procedure §2b) until
the floor is met or ready work runs out (raised from ≥4 to ≥5 by direct owner instruction,
2026-09-25, §31; the reasoning below is unchanged by the raise). Best-effort: this never forces
speculative work and never overrides the standing usage-cap pause order (procedure §2b/§8: lane B
pauses first, then D; primary never). The only concurrency rule that existed before this one was a
cap, not a floor ("Keep at most one live run per lane", procedure §2b); PHASE1's own diagnosis
(`plans/sprint/PHASE1-SPRINT-PLAN.md` §1) named "idle gaps to 9 h" as a measured symptom of exactly
that gap — parallel capacity sat idle even when independent ready work and machine headroom both
existed, because nothing forced the supervisor to notice ready work promptly. Mechanical reader:
`tools/reviewer/reviewer_check.py`'s `concurrency_floor_flag` (§31 PHASE1/F13; threshold constant
needs updating alongside this doc, not landed by this entry).

`lanes.<lane>.live_run` alone is a timestamp with no expiry, so a stale entry left behind by a
session/machine restart reads as "live" forever and can make the floor look met while the lane is
actually idle (found and fixed 2026-09-17, §31 PHASE1/F13 follow-up). `reviewer_check.py` now only
counts a `live_run` toward the floor when it is corroborated by that lane's own PR count this wake
(`metrics["lanes"][name]["prs"]`) — `live_run` truthy with zero open/recent PRs is treated as not
live.

## Wakeup policy

The executor self-schedules every iteration, productive or not (`loop-prompt.md` §7) — that is the
load-bearing continuation, because a missed self-wake is detectable and self-recovering (five
recorded occurrences, all recovered; stop_monitor alarms at delay + 10 min), while
externally-triggered continuation makes the executor's liveness depend on the supervisor's — the
exact coupling that stranded the lanes. The 2026-09-10 17:35 instruction that reversed this is
itself reversed (§31, 2026-09-11). Supervisor nudges remain welcome and are never required.

The supervisor's own cadence is layered so no single source is load-bearing: event notifications
(lane completions, monitor lines), an hourly heartbeat wake whose first act is
`reviewer_check.py --record`, and the dead-man underneath both.

## No idle wakes

A background-task notification that repeats an agent's own prior status ("still waiting", "push in
progress", "will report when done") carries no new information and is not itself a unit of
supervision work. Answering it with a bare acknowledgment and nothing else is idling with extra
steps — measured this session (2026-09-25): dozens of consecutive "routine, holding" replies to
self-report notifications while genuinely idle capacity (unassigned ready work, unverified pushes,
an unauthorized `--no-verify` push, a stalled-looking agent that was actually fine, one that
genuinely needed a check-in) sat unexamined in the same window. The owner should never have to name
this; every wake names it for the supervisor instead.

Rule: on every wake, whether triggered by a real event or a routine self-report, the supervisor
takes at least one substantive action before replying — not a status message alone. Substantive
means one of: verifying a claimed state directly against disk/`origin/main` rather than trusting a
self-report (`git log`, `git ls-remote`, `status --stale`); advancing other ready, disjoint work
(the concurrency floor above); checking a long-running or repeatedly-idle-reporting agent's actual
worktree diff rather than accepting "still working" at face value; or recording/acting on a finding
already in hand. A wake with truly nothing new to check and nothing ready to advance is rare enough
that it should be named as such, not the default response.

## Enforcement placement

A check that must survive the supervisor lives in `tests/` (CI runs it per push — the
`test_bundle_audits.py` promotion pattern) or in `liveness.yml` (survives everything). A check
that reads a live session's transcript stays in `tools/reviewer/` and accepts that it is mortal —
which is acceptable only because the dead-man is not. When adding a check, place it by asking what
must outlive what; and every check traces to a measured incident it would have caught.
