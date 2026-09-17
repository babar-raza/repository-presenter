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
| 1 | CI/deployment sustainability — verify locally via `act`, then on real GitHub Actions runners | "Execution Environments and GitHub Access" | investigated; one ruling landed (pip caching, `e74077b`/`ci.yml`), rest blocked on `OWNER-04`/G5 | supervisor, 2026-09-17 |
| 2 | Repo metadata / social appearance / community-files component | "Visual Assets and Social Preview", "Central Agent" responsibilities bullet 2 | investigated (`02-repo-metadata-community-files.md`); **no decision taken — left open on the owner's explicit instruction, 2026-09-17.** `OWNER-07` (SECURITY.md's verified-contact dependency) stands as a recorded fact independent of this, not a ruling on the workstream. | supervisor, 2026-09-17 |
| 3 | Issue-tracking component — file confirmed upstream defects, dedupe, close stale ones | "Upstream Defect Reporting" | schema + evidence layout landed (`a024836`); write path (`gh issue create`) ruled, blocked on `OWNER-04`/G5 | supervisor, 2026-09-17 |
| 4 | Portfolio discovery module — find new repos/products, reuse an existing aspose.org discovery mechanism if one exists | "Common Gate C0" | scanner built and run (`ea8ab8c`, `10-portfolio-discovery.md`); one admission decision pending (`OWNER-08`) | supervisor, 2026-09-17 |
| 5 | Full production autonomy — the system runs without routine human intervention | "Operating Model", "Production-Readiness Standard" | investigated (`05-production-autonomy.md`); worktree-isolation-for-every-write-role ruled as standing practice; two concrete hardening items queued, unscheduled | supervisor, 2026-09-17 |

### Rulings landed 2026-09-17 (full ruling text: `docs/DECISION_LOG.md`, 2026-09-17 entries)

- **WS1**: `ci.yml` gets `cache: pip` (this commit); same for `monitor.yml`/`present.yml` when authored (G5). Never a shared/symlinked venv across a worktree or job — each isolated unit installs independently; speed comes only from the pip cache, not shared install state.
- **WS2**: **withdrawn 2026-09-17, same day — the owner asked for this workstream to stay open rather than ruled.** None of the Phase 0/1/2 sequencing, bundle-shape, or custom-properties decisions below stand; investigation 02's own open questions are all still open. `OWNER-07` (SECURITY.md needs a verified contact) remains recorded as a standing fact, not a ruling on the workstream — it would block SECURITY.md generation under any future ruling, so it stays tracked regardless.
- **WS3**: write capability (`gh issue create`) shares the same G5/`OWNER-04` GitHub App gate as WS2 — Issues:Write is one more scope on that App, not a separate credential. A defect must be independently reproduced by the filing agent at file-time (not merely cited from a prior investigation) before it is ever filed — the discipline already applied to the HTML-Python/TeX-Python backfills becomes the standing bar. This system only ever creates and follows up on issues carrying its own fingerprint; it never comments on or closes an issue it did not file.
- **WS4**: `repository_id` is the authoritative anti-rename/anti-transfer identity signal; `node_id` is corroborating/informational only, never compared strictly against a frozen historical value (GitHub's 2021-2022 global-ID re-encoding already broke that assumption once) — `Registry.validate_stable_identities` needs a follow-up code change to stop treating them as equally load-bearing; not yet implemented, ready for a taskcard. Registry admission (`OWNER-08`) stays a per-repository owner decision, never automatic. Re-scan cadence: on demand (rerun `tools/discovery/portfolio_discovery.py`) until G5's `monitor.yml` exists to schedule it — no new infrastructure needed before then.
- **WS5**: every write-capable role runs in its own isolated worktree, effective immediately as standing supervisor practice — never a shared checkout among concurrently live write-capable agents. Two concrete, code-level hardening items are queued (unscheduled, no taskcard yet): a deterministic fetch→rebase→retry push wrapper (closes failure classes A/D at the root), and a scheduled sweep of `docs/RESEARCH_LANE_*.md` for un-admitted `PROPOSAL` headings (closes class H). The detection/remediation split (`liveness.yml` detects, a human still remediates) stays as-is for now — closing it is G5-adjacent, not ruled today.

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

**Standing rule for whoever reads this next:** all five workstreams are now investigated and ruled
(see "Rulings landed 2026-09-17" above) — implementation may proceed on exactly the pieces each
ruling clears (WS1's `ci.yml` cache; WS4's `repository_id`/`node_id`
fix). Everything else stays blocked on the owner item or gate its ruling names (most commonly
`OWNER-04`/G5) — a ruling clearing the *decision* does not itself clear a credential or gate
precondition that decision depends on. Investigation reports:

- Workstream 1: `docs/investigations/01-ci-deployment-sustainability.md` (pending)
- Workstream 2: `docs/investigations/02-repo-metadata-community-files.md` (pending)
- Workstream 3: `docs/investigations/03-issue-tracking.md` (pending)
- Workstream 4: `docs/investigations/04-portfolio-discovery.md` (design analysis); a first live
  enumeration pass and its reusable, read-only tool followed on 2026-09-17:
  `docs/investigations/10-portfolio-discovery.md`, `tools/discovery/portfolio_discovery.py`. This
  covers only the discover-and-report half of Gate C0 (org/repo enumeration, diff against
  `data/registry.json`) — the staging/observation artifact, exclusions ledger, and reconciliation
  step investigation 04 §4 recommends before any intake remain undone; the workstream's own
  `not started` status above still stands for the gate as a whole.
- Workstream 5: `docs/investigations/05-production-autonomy.md` (pending)

## Reverse by

`git revert` — this is a pure documentation addition, no code or check coupling; removing it
returns the project to tracking only sealing progress, which was the state before 2026-09-17.
