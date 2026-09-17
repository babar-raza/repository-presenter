# Production Roadmap — full mission state, not just candidate sealing

Written 2026-09-17 (owner direction, mid-sprint) after the owner named five production
workstreams beyond portfolio README sealing and asked for a durable record so every future
agent — supervisor, primary, lane, or one-off — has the full goal in view, not only the sealing
metric this sprint has been optimizing. `plans/idea.md` remains the human product authority this
document reports against; nothing here overrides it. Read `docs/SUPERVISION.md` first for who
this document assumes is acting (owner, supervisor, primary, lanes).

## Where portfolio sealing fits

Sealing candidates (the G4-W17 work this whole sprint has driven) is `plans/idea.md`'s **Gate A**
("full-registry verified local README proof") plus its independent-review completion — one slice
of a six-gate lifecycle (Historical → C0 → A → B → C, plus the production-readiness standard
above all of them). Gate A does not by itself reach `plans/idea.md`'s production-readiness bar
(§"Production-Readiness Standard": 7/8 maturity, autonomous, no routine manual intervention). The
five workstreams below are gates and standing obligations `plans/idea.md` already names that this
project has not yet built. This document is the first record connecting sprint-level sealing work
to that larger, already-authorized scope — it does not invent new obligations.

## The five workstreams (owner-named, 2026-09-17)

Each gets its own investigation before any implementation starts. Status column is honest, not
aspirational — `not started` means exactly that.

| # | Workstream | `plans/idea.md` anchor | Status | Investigation owner |
|---|---|---|---|---|
| 1 | CI/deployment sustainability — verify locally via `act`, then on real GitHub Actions runners | "Execution Environments and GitHub Access" | not started | pending assignment |
| 2 | Repo metadata / social appearance / community-files component | "Visual Assets and Social Preview", "Central Agent" responsibilities bullet 2 | not started | pending assignment |
| 3 | Issue-tracking component — file confirmed upstream defects, dedupe, close stale ones | "Upstream Defect Reporting" | not started | pending assignment |
| 4 | Portfolio discovery module — find new repos/products, reuse an existing aspose.org discovery mechanism if one exists | "Common Gate C0" | not started | pending assignment |
| 5 | Full production autonomy — the system runs without routine human intervention | "Operating Model", "Production-Readiness Standard" | not started | pending assignment |

### Known constraints already on record, before investigation starts

- **Workstream 1**: `plans/idea.md` requires GitHub App + short-lived installation tokens in
  production, environment-specific credential providers, and a **fail-closed** rule — production
  must not silently fall back to a personal access token. Local testing uses operator `GH_TOKEN`.
  Credentials must never be embedded in workflow definitions, source, caches, state, logs, or
  evidence. This session already has one live incident on record worth the investigator reading:
  a lane agent's diagnostic `echo` accidentally printed a literal `GH_TOKEN` value into its own
  transcript earlier this sprint (flagged to the owner as a rotation candidate) — a concrete
  argument for why the fail-closed and never-embedded rules above are not hypothetical.
- **Workstream 2**: explicitly **not required for the initial pilot** per `plans/idea.md`
  ("Visual Assets and Social Preview"). A social-preview image has no supported GitHub automation
  mechanism as of the document's writing — the fallback is a validated asset plus a precise
  manual-application handoff, never a claim that it was applied automatically.
- **Workstream 3**: also explicitly **not required to be fully delivered during the initial
  pilot** — a bounded interim fallback (an evidence-backed handoff for a human to file) is
  acceptable until direct issue creation is authorized. Filing bar: independently confirmed
  defect (not suspected), deduplicated against agent-filed and existing upstream issues, never
  fabricated severity, never a claimed fix the agent hasn't verified. The seed example named in
  the document is Aspose.Email FOSS for .NET's genuine `CS1929` build failure.
- **Workstream 4**: `plans/idea.md`'s Gate C0 already specifies the shape — authenticated
  all-visibility pagination across every explicitly authorized source, recording public, private,
  internal, archived, unmatched, ambiguous, inaccessible, renamed, and transferred observations by
  stable provider identity; new eligible repositories enter **disabled and read-only**. The
  document names "aspose.org" as an existing discovery/extraction source under a "pull discipline"
  (pinned revision, one file record per file, ported tests, cut import closure, typed façade) —
  **this session found no `aspose.org` checkout on this machine** (only `products.aspose.*`
  sibling directories under `..\`); confirming whether that source exists anywhere accessible, and
  where, is the investigation's first job before assuming reuse is possible.
- **Workstream 5**: `plans/idea.md`'s bar is specific, not vague — "a prototype, collection of
  disconnected capabilities, or system that works only through routine manual intervention does
  not meet this standard," but also "does not require every possible enhancement to be complete."
  This sprint's own overnight experience is direct evidence for what autonomy still lacks: every
  push race, merge conflict, and concurrent-checkout collision this session hit and resolved by
  hand (documented throughout `docs/DECISION_LOG.md`'s 2026-09-16/17 entries) is a manual
  intervention today's system still needs a human-supervised agent to absorb.

## How this relates to current sealing work

Sealing continues at full priority — it is Gate A's own completion criterion and the nearer-term,
better-understood goal. The five workstreams above are investigated in parallel (research only,
isolated worktrees, no shared-checkout contention with active sealing/fix-landing work) rather
than sequenced after sealing finishes, since they are independent of the G4-W17 candidate queue
and estimated to need substantial dedicated design before any implementation begins.

**Standing rule for whoever reads this next:** do not start implementing any of the five
workstreams from this document alone — each needs its own investigation report (recorded under
`docs/investigations/`, one file per workstream, linked below once written) reconciled with
`plans/idea.md` and the current codebase before a taskcard is written. Investigation reports:

- Workstream 1: `docs/investigations/01-ci-deployment-sustainability.md` (pending)
- Workstream 2: `docs/investigations/02-repo-metadata-community-files.md` (pending)
- Workstream 3: `docs/investigations/03-issue-tracking.md` (pending)
- Workstream 4: `docs/investigations/04-portfolio-discovery.md` (pending)
- Workstream 5: `docs/investigations/05-production-autonomy.md` (pending)

## Reverse by

`git revert` — this is a pure documentation addition, no code or check coupling; removing it
returns the project to tracking only sealing progress, which was the state before 2026-09-17.
