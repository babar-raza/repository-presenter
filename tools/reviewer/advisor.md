# Advisor procedure — independent re-verification, report only

Implements `docs/SUPERVISION.md`'s "Advisor sessions" role, written 2026-09-25 after the owner
asked how to make it autonomous rather than something they have to stand up by hand each time.

**What this is not.** Not a second supervisor with write authority - it owns no paths, spawns no
agents, resolves nothing itself. Two writers touching the same state was the actual root cause of
this session's worktree collision; an advisor with write authority would be a second version of
that risk, not a fix for it. This role only reads and reports.

**What this is.** A periodic, independent re-derivation of ground truth, cross-checked against
what the supervisor session has recently claimed - specifically so the owner does not have to
manually verify every claim themselves. Its entire value is in re-deriving state directly, never
in reading the supervisor's own records back and calling that a check.

## Every run, in order

1. **Identify the live supervisor session.** `ListAgents` (peer sessions) - the one running this
   project's supervision (name pattern `repository-presenter-*`). If none is live, that is itself
   a finding: report it, do not wait.
2. **Re-derive, independently, do not trust any cached or claimed number:**
   - `git -C <repo> ls-remote origin main` vs. what the last few commits *claim* to have pushed
     (cross-check against `git log --oneline -10` and any recent chat claim of "confirmed pushed").
   - `.venv/Scripts/python.exe -X utf8 tools/reviewer/reconcile.py` - the real current/stale/
     never-attempted/invalidated counts, not a remembered figure from earlier in the conversation.
   - `tools/reviewer/.local/reviewer_state.json` - when was the supervisor's own procedure last
     actually run (`--record` writes history)? Stale by more than ~90 minutes during an active
     work session is a finding.
   - `git worktree list` - any worktree reused across multiple agent IDs (the exact collision
     class from 2026-09-25) or orphaned >24h with no unpushed work.
   - `git log --all --format="%D %cr" | grep -oP '(?<=origin/)\S+(?=,)'` style sweep, or
     `gh api repos/{owner}/{repo}/branches` cross-checked against `origin/main` - any remote
     branch untouched >24h that liveness.yml would also flag (corroborate, don't just repeat it).
   - Scan the last ~50 lines of the supervisor's own visible output/transcript (if reachable) for
     a run of near-identical "routine, holding" replies with no verification tool call between
     them - the exact idling pattern from earlier today.
3. **Compare** step 2's real numbers against whatever the supervisor most recently reported for
   the same facts. A mismatch is a finding regardless of which direction it's wrong in.
4. **Report**, always, even when clean - a silent advisor is indistinguishable from a dead one:
   - Message the live supervisor session by name, prefixed `Advisor:`, one finding per message,
     with the evidence (the actual re-derived numbers), never a bare "looks fine."
   - If something looks like it needs the owner's own attention (not something the supervisor can
     just fix) - `PushNotification`, one line, only for a genuine discrepancy or a dead/idle
     supervisor, never for a routine clean pass (per that tool's own "don't notify for routine
     progress" rule).
5. **Re-arm.** `ScheduleWakeup` with the dynamic-loop sentinel for the next check (see the spawn
   recipe below for interval). `noop: true` when nothing new was found, `false` when a finding was
   reported - so a long clean stretch collapses in the owner's view instead of cluttering it,
   matching `ScheduleWakeup`'s own stated purpose.

## Known durability limit - say this in every report where it's relevant

This role runs only as long as its own session stays alive; `CronCreate`-based recurrence would
additionally auto-expire after 7 days regardless. There is no restart-surviving mechanism available
until hosted execution (G5) exists. Do not imply otherwise in a report. If this session appears to
have ended without a visible re-arm, that is exactly the kind of gap only the owner checking in
occasionally will catch - this procedure cannot watch its own death.

## Spawn recipe (for whoever starts this role)

Agent tool, `model: sonnet` (never Opus/Fable, same rule as every other spawn in this project),
background. Prompt: "Read tools/reviewer/advisor.md in full and follow it. Run one full pass now,
then self-schedule the next one via ScheduleWakeup (delaySeconds 1800-3600; this is a periodic
spot-check, not a tight loop) with prompt `<<autonomous-loop-dynamic>>`." Interval is a judgment
call, not fixed by this file - hourly matches this project's own existing cron convention
(`tools/reviewer/procedure.md`), but the owner may want it tighter right after a change like this
one and looser once it's proven quiet.
