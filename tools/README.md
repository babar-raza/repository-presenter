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
  - `test_research_edit.py` — regression tests for `research_edit.py`'s three functions, run
    directly (`pytest tools/reviewer/test_research_edit.py`; outside `pyproject.toml`'s
    `pythonpath`/collection scope, so it never runs as part of `pytest tests/`). SR-02
    (`plans/healing/self-review-remediation.md`), added 2026-09-09 after `append_entry` and
    `safe_replace` had been relied on for three days with no test at all.
  - `audit_link_completeness.py` — walks every `candidates/*/*/` manifest directory checking
    whether a `VERIFIED_REWRITE` disposition's `link_target` facts all reached that revision's
    `plan.json` `links` list. Written 2026-09-08 landing the `planning.py` fix for exactly this
    gap, to check the fix's effect across the whole portfolio rather than just the candidate that
    surfaced it — found the same gap already sealed into two other candidates.
  - `audit_preserved_api_lists.py` — flags a `VERIFIED_PRESERVE` "list" unit placed into
    `api_reference` whose disposition cites only a module-level `public_symbol` fact, never an
    individual class or enum. A diagnostic sweep, not a fix (see `docs/DECISION_LOG.md`, 2026-09-08,
    for why a safe general fix isn't available without either a live re-dispositioning call or
    risking silent content loss).
  - `procedure.md` — the wake procedure both cron and a human reviewer follow: cheap check, full
    review, the lane-supervision addendum, commit discipline, the report shape.
  - `.local/` — gitignored. `reviewer_state.json` (wake history, the `watch` field for the next
    wake) and any cloned fixtures a run needs. Machine-local, not portfolio content, never committed.
- `census/` — one-shot planning data-gathering, not ongoing supervision.
  - `portfolio_census.py` — shallow-clones every non-Python registry entry read-only and produces a
    static census (manifest, deps, README shape, registry publication, toolchain probe). Output
    feeds `project/portfolio-census.json` (committed — that's owner planning data referenced by
    `docs/RESEARCH_AND_GUIDELINES.md` §28.11, distinct from this directory's *code*).
- `discovery/` — one-shot planning data-gathering, same shape as `census/`, for the portfolio
  itself rather than one repository's contents.
  - `portfolio_discovery.py` — enumerates every `aspose-<family>-foss` GitHub organization
    (search leg + a maintained/extensible probe leg over plausible family slugs, since GitHub has
    no direct "list orgs by name pattern" API — see the module's own docstring for exactly how the
    candidate list is assembled and its documented recall limitation), lists each org's public
    repositories, and diffs them against `data/registry.json`. **Read-only and report-only: it
    never writes `data/registry.json`** — admitting a discovered repository is a separate,
    human-reviewed decision, always (owner standing rule, 2026-09-17). Run it with
    `python tools/discovery/portfolio_discovery.py`; it writes
    `docs/investigations/10-portfolio-discovery.md` by default (`--output` to change). Commissioned
    by `docs/PRODUCTION_ROADMAP.md` workstream 4 / `plans/idea.md`'s Common Gate C0, following up
    `docs/investigations/04-portfolio-discovery.md`'s design analysis with the first actual
    enumeration pass.
  - `test_portfolio_discovery.py` — regression tests for the search/probe/diff/render logic, run
    directly (`pytest tools/discovery/test_portfolio_discovery.py`; outside `pyproject.toml`'s
    `pythonpath`/collection scope, so it never runs as part of `pytest tests/`), same convention as
    `tools/reviewer/test_research_edit.py`. Every test injects a fake fetch function — no test
    makes a live network call.
- `git/` — deterministic git-mechanics wrapper for the moment an isolated worktree's branch needs
  to land on a shared target branch other concurrently-live write-capable agents may also be
  pushing to right now (`docs/investigations/05-production-autonomy.md` §5's own highest-leverage
  recommendation; `docs/PRODUCTION_ROADMAP.md` WS5).
  - `push_retry.py` — fetch → rebase → push, bounded retries (`--max-retries`, default 5), never
    `--force`. On a rebase conflict, auto-resolves only the narrow, clean append-only case confined
    to `docs/DECISION_LOG.md` and/or `docs/RESEARCH_AND_GUIDELINES.md` (both sides only appended
    new content after a shared, unedited base — proven via `git -c merge.conflictstyle=diff3`'s
    base section, never guessed) — keeping both sides in chronological order and removing only the
    markers. Any other conflict shape or file aborts the rebase (`git rebase --abort`) and reports
    the exact file(s) needing human/agent judgment, never a guess. Run it with
    `python tools/git/push_retry.py [--branch main] [--remote origin] [--max-retries 5]`.
  - `test_push_retry.py` — regression tests, run directly (`pytest tools/git/test_push_retry.py`;
    same outside-`pyproject.toml`-scope convention as the other `tools/` test files). Includes
    pure-function tests against conflict text captured verbatim from real
    `git -c merge.conflictstyle=diff3 rebase` runs (both the clean append-only shape and a
    genuinely ambiguous edit-and-append shape), and integration tests driving real local git
    repositories end to end (bare "remote" plus two clones, no live network call) proving the
    auto-resolved case lands both sides on the remote and the ambiguous/out-of-scope cases abort
    and land nothing.
- `research_sweep/` — one-shot or recurring detection, same non-mutating shape as `discovery/`.
  - `proposal_sweep.py` — scans every `docs/RESEARCH_LANE_*.md` file for `PROPOSAL`-headed
    findings (both marker conventions the lane files actually use — a `###` heading, or the lead
    bold span of a list item/paragraph) and cross-references each detected code against
    `docs/DECISION_LOG.md`'s admission log (`--admission-file` to point elsewhere). **Read-only,
    report-only**: it never edits a lane file or the admission log, and never decides whether a
    PROPOSAL is correct or where it belongs — see its own module docstring's "Detection vs.
    admission" note, which is this tool's whole design boundary
    (`docs/investigations/05-production-autonomy.md` class H: "detection is automatable; admission
    is not"). Commissioned by that investigation and `docs/PRODUCTION_ROADMAP.md` WS5's queued
    "scheduled sweep of `docs/RESEARCH_LANE_*.md` for un-admitted `PROPOSAL` headings" hardening
    item — this lands the detection half; wiring it into an actual recurring cadence (cron,
    `liveness.yml`, or a `reviewer_check.py` addition) is a separate, later decision, deliberately
    not built here. Run it with `python tools/research_sweep/proposal_sweep.py`; add
    `--fail-on-findings` to get a non-zero exit when something needs review (useful once it is
    wired into a cadence — off by default, since a bare report is never itself a gate). A
    code-bearing PROPOSAL (lanes D/E/F's `<letter><digits>` codes, lane B's `LANE-B-...` shared-code
    codes) is checked by exact citation match; lane C's bare 1-2 letter codes are the weakest
    category (the admission log sometimes cites the lane/repository/check in prose instead of
    restating the letter — the tool's own report says so up front when it matters); lane B's plain
    parenthetical `PROPOSAL (primary loop, ...)` shape carries no identifier at all and is always
    surfaced for manual review, by design.
  - `test_proposal_sweep.py` — regression tests against small synthetic fixture text built to match
    the real marker conventions (never the real, large `docs/` files), run directly (`pytest
    tools/research_sweep/test_proposal_sweep.py`), same outside-collection-scope convention as
    `tools/discovery/test_portfolio_discovery.py`.

- `github_app/` — one-time registration for `OWNER-04`'s production GitHub App, not ongoing
  supervision.
  - `manifest.json` — the static app manifest (name, permissions, no webhook) submitted through
    GitHub's manifest flow. Requests `metadata:read`, `contents:write`, `issues:write`,
    `pull_requests:write`, `administration:write` — the last is new, needed for WS2's repo
    description/topics/homepage `PATCH`.
  - `register.html` — a local, no-dependency HTML form that POSTs `manifest.json`'s contents to
    `https://github.com/settings/apps/new`. The owner's one required click; opens locally, never
    published or hosted.
  - `register_exchange.py` — takes the code GitHub's redirect carries, exchanges it via
    `POST /app-manifests/{code}/conversions`, and stores the resulting `GH_APP_ID` /
    `GH_APP_PRIVATE_KEY` / `GH_APP_CLIENT_ID` / `GH_APP_CLIENT_SECRET` / `GH_APP_WEBHOOK_SECRET` as
    encrypted `gh secret set` values on `babar-raza/repository-presenter` directly — never printed
    in full, never written to disk, matching `OWNER-02`'s established process-env-only precedent.
    A second manual click (approving installation per `aspose-*-foss` org) still follows; GitHub
    has no API path around a first cross-org installation's consent. Full guide:
    `docs/DECISION_LOG.md`, 2026-09-23 16:04 UTC.

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
