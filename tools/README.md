# tools/

Owner/reviewer tooling for running and supervising the `/loop` agent and its lanes. This is **not**
part of the shipped product (`src/repository_presenter/`): nothing here is imported at runtime,
nothing here is read by the loop's own acceptance predicates, and nothing here counts toward any
gate. It exists so the governance work this project's owner does — supervision, census, corrective
messaging — is reusable and versioned instead of living in a session-local scratchpad that vanishes
when the session ends (as it did for most of 2026-09-05/06 before this directory existed).

**Boundary, stated plainly** (mirrored in `docs/REPOSITORY_LAYOUT.md`, `project/loop-prompt.md`, and
`project/loop-prompt-lane.md`): the loop and every lane never read, write, or import anything under
`tools/`. The owner/reviewer never writes to `src/`, `tests/`, `prompts/`, or `schemas/`. Two
governance tracks, two directories, no overlap.

## Layout

- `reviewer/` — supervises the primary loop.
  - `reviewer_check.py` — the deterministic wake check: liveness, iteration accounting, rule
    compliance, time-box overrun on the active item, governance consistency (state.yaml vs
    RESEARCH §27.9), growth signals, section 31 review, deadline projection. Run it; act only on
    `[FLAG]` lines; everything else is context. `python -X utf8 reviewer_check.py --record` (the
    cron wake's form) also appends the wake to `.local/reviewer_state.json`'s history.
  - `stop_monitor.py` — event-driven: reports within ~60s when the loop's own `ScheduleWakeup`
    stalls (fires late), the session hits a usage cap, or a session-limit message appears. Run it
    under the `Monitor` tool.
  - `timestamp_monitor.py` — event-driven: reports within ~45s when a new `§31` entry's stamped
    timestamp drifts more than 20 minutes from the real clock, or an accept-shaped claim appears
    with no predicate/evidence word nearby. Added 2026-09-06 after catching three fabricated
    timestamps from a model change (see `procedure.md`'s weaker-model-watch note).
  - `research_edit.py` — reusable helpers for editing `docs/RESEARCH_AND_GUIDELINES.md` and
    `docs/DECISION_LOG.md` safely. `safe_replace` asserts an anchor's occurrence count before
    writing (never a silent no-op against a moved file); `load_yaml_block` re-parses the §27.9
    fenced YAML block afterward so a broken edit is caught before it is staged; `append_entry`
    appends a new dated entry (§31's shape) with consistent blank-line spacing, with `newline="\n"`
    handled for you. Written 2026-09-06 to replace two near-identical scratchpad throwaways for the
    anchor-replace shape; `append_entry` added 2026-09-08 after ten more near-identical throwaways
    accumulated for the append shape (see the module docstring) — check here first before writing a
    new one-off script for either shape of edit.
  - `procedure.md` — the wake procedure both cron and a human reviewer follow: cheap check, full
    review, the lane-supervision addendum, commit discipline, the report shape.
  - `.local/` — gitignored. `reviewer_state.json` (wake history, the `watch` field for the next
    wake) and any cloned fixtures a run needs. Machine-local, not portfolio content, never committed.
- `census/` — one-shot planning data-gathering, not ongoing supervision.
  - `portfolio_census.py` — shallow-clones every non-Python registry entry read-only and produces a
    static census (manifest, deps, README shape, registry publication, toolchain probe). Output
    feeds `project/portfolio-census.json` (committed — that's owner planning data referenced by
    `docs/RESEARCH_AND_GUIDELINES.md` §28.11, distinct from this directory's *code*).

## Environment variables

Both `reviewer_check.py`, `stop_monitor.py`, and `timestamp_monitor.py` default to this machine's
current reviewer session but can point at a different one:

| Variable | Meaning | Default |
|---|---|---|
| `REVIEWER_LOOP_TRANSCRIPT` | Path to the loop session's `.jsonl` transcript | this machine's 2026-09-05 session |
| `REVIEWER_STATE_PATH` | Path to the reviewer's own state JSON | `tools/reviewer/.local/reviewer_state.json` |
| `CENSUS_CLONE_DIR` | Where `portfolio_census.py` shallow-clones repositories | `tools/census/.local/portfolio` |

A future reviewer session (a new conversation, or a different machine continuing this project) sets
these once rather than editing the scripts.

## Why this exists as a directory, not a one-off script

The legacy project's failure mode (`AGENTS.md`, `RESEARCH_AND_GUIDELINES.md` §30.8) was machinery
that kept growing with no tangible outcome — validators checking validators. The temptation with
reviewer tooling is the same: it is easy to keep adding checks that make the reviewer feel more
thorough without ever verifying they catch a real, previously-missed defect. Every check in
`reviewer_check.py` should trace to a measured incident it would have caught (the time-box check
traces to G4-W11 running 67 minutes over its stated box with nothing noticing; the timestamp monitor
traces to three fabricated `§31` stamps). A check with no such incident behind it is a candidate for
removal, not addition — this file's own existence is the one place that discipline is written down.
