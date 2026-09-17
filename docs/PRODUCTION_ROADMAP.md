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
| 2 | Repo metadata / social appearance / community-files component | "Visual Assets and Social Preview", "Central Agent" responsibilities bullet 2 | **partially ruled 2026-09-17 (supersedes the earlier full withdrawal):** description/topics/homepage ("product URL") — build the capture+proposal logic now, ready for a taskcard; visual assets and community-file *generation* stay next-phase. `OWNER-07` (SECURITY.md's verified-contact dependency) still stands. | supervisor, 2026-09-17 |
| 3 | Issue-tracking component — file confirmed upstream defects, dedupe, close stale ones | "Upstream Defect Reporting" | schema + evidence layout landed (`a024836`); closing-side design already complete (investigation §6); dedup ledger + re-detection logic ruled unblocked; **elevated 2026-09-17: ruled required to be complete within the pilot** (overrides `idea.md`'s own "not required for the initial pilot" allowance) — only the actual `gh issue create`/`close` calls stay blocked on `OWNER-04`/G5 | supervisor, 2026-09-17 |
| 4 | Portfolio discovery module — find new repos/products, reuse an existing aspose.org discovery mechanism if one exists | "Common Gate C0" | scanner built and run (`ea8ab8c`, `10-portfolio-discovery.md`); one admission decision pending (`OWNER-08`) | supervisor, 2026-09-17 |
| 5 | Full production autonomy — the system runs without routine human intervention | "Operating Model", "Production-Readiness Standard" | investigated (`05-production-autonomy.md`); worktree-isolation-for-every-write-role ruled as standing practice; two concrete hardening items queued, unscheduled | supervisor, 2026-09-17 |
| 6 | Deployer — open and merge the PR carrying a sealed candidate on its target repo (Gate C) | "Gate C", `propose.yml` | investigated live against `Aspose/aspose.org`'s own proven `readme_refresh_run.py` (owner-directed reuse target, 2026-09-17); design principles ruled adopted; **first live push stays owner-gated, same as a registry write** | supervisor, 2026-09-17 |

### Rulings landed 2026-09-17 (full ruling text: `docs/DECISION_LOG.md`, 2026-09-17 entries)

- **WS1**: `ci.yml` gets `cache: pip` (this commit); same for `monitor.yml`/`present.yml` when authored (G5). Never a shared/symlinked venv across a worktree or job — each isolated unit installs independently; speed comes only from the pip cache, not shared install state.
- **WS2**: earlier fully withdrawn 2026-09-17, then **partially re-ruled the same day, superseding that withdrawal in part.** Repo description, GitHub topics, and homepage ("product URL") are ruled in-scope now — build the read+proposal half (derive a validated description/topics/homepage from already-verified repository facts, diff against the currently-observed GitHub state) as a ready-now taskcard; the actual `PATCH`/`PUT` write calls stay gated on `OWNER-04`/G5's Administration:write scope, same discipline as every other write this session. Social-preview asset preparation and community-file *generation* (writing CONTRIBUTING/SECURITY/CODE_OF_CONDUCT content) stay next-phase, not ruled. Community/contribution/licensing/security file *checking*: ruled — when a file this project already detects (`core/snapshot/inventory.py::FileInventory.community_paths`) is missing, log it as an issue via WS3's mechanism once that write path exists; do not auto-generate the missing file. `community_paths` itself is currently dead code (computed, never consumed) — recorded here as the exact hook point for that future consumer, not wired up in this commit (a `src/` change, out of scope for a supervisor-authored commit). Releases/package-links auditing (beyond the existing package-registry badge work) is ruled a **priority** — a real GitHub Releases-page audit, not yet built. GitHub-generated-metadata auditing (stars/forks/contributors/languages/activity, never editable, observation-only) is ruled plan-only for now, implementation deferred to a later stage. `OWNER-07` (SECURITY.md needs a verified contact) still stands, unaffected by any of the above.
- **WS3**: write capability (`gh issue create`/`close`) shares the same G5/`OWNER-04` GitHub App gate as WS2 — Issues:Write is one more scope on that App, not a separate credential. A defect must be independently reproduced by the filing agent at file-time (not merely cited from a prior investigation) before it is ever filed — the discipline already applied to the HTML-Python/TeX-Python backfills becomes the standing bar. This system only ever creates and follows up on issues carrying its own fingerprint; it never comments on or closes an issue it did not file — matches investigation 03 §6's own scope limit and directly answers its §8 open question ("never close a pre-existing issue" — ruled, not merely deferred). **Elevated 2026-09-17: "should be complete with pilot. Do it well" — this workstream is no longer treated as pilot-optional** (idea.md itself allows deferring it; the owner rules otherwise for this project). Its scope now explicitly includes missing-community-file findings routed through this same mechanism (see WS2's community-file ruling above), not only source-code defects.
  - **Newly ruled, unblocked, ready now (2026-09-17 15:40 UTC):** investigation 03 §6 already fully designs the closing side — on a drift-triggered re-run, re-evaluate the same `triggering_check` that produced a `FILED` handoff artifact; if it now passes, transition the artifact's `status` to `RESOLVED_UPSTREAM` locally (`completed` reason if the check flipped, `not planned` if a check-version change or false positive is the cause, per §6's own two-reason split). This is a pure read + local-JSON-artifact update — no GitHub write scope needed, so it does not wait on `OWNER-04`/G5. Two concrete pieces, both buildable now: (a) the dedup ledger investigation 03 §4 point 3 specifies (`{repository, defect_fingerprint} → {issue_ref, filed_at revision, last-observed state}`, the natural analog of `evidence/build/lanes/<lane>/<ITEM>.json` receipts); (b) the re-detection pass itself, wired into the existing drift/re-seal path (`STATE_MACHINE.md`'s `NON_PROCESSABLE`/`OBSERVED` reopen-on-drift cycle already named in §6). Only the final step — actually calling `gh issue create`/`close` — stays gated on `OWNER-04`/G5; everything upstream of that call can be built, tested, and exercised (read-only) against the two already-backfilled artifacts (HTML-Python, TeX-Python) today.
- **WS4**: `repository_id` is the authoritative anti-rename/anti-transfer identity signal; `node_id` is corroborating/informational only, never compared strictly against a frozen historical value (GitHub's 2021-2022 global-ID re-encoding already broke that assumption once) — `Registry.validate_stable_identities` needs a follow-up code change to stop treating them as equally load-bearing; not yet implemented, ready for a taskcard. Registry admission (`OWNER-08`) stays a per-repository owner decision, never automatic. Re-scan cadence: on demand (rerun `tools/discovery/portfolio_discovery.py`) until G5's `monitor.yml` exists to schedule it — no new infrastructure needed before then. **Confirmed gap, 2026-09-17 (owner-directed re-check):** `tools/discovery/portfolio_discovery.py` enumerates repositories but never classifies `family`/`platform`/`ecosystem` — its own output table (`docs/investigations/10-portfolio-discovery.md`) has no such column. The classification logic does exist, real and battle-tested, just not here: `Aspose/aspose.org`'s `scripts/pipeline/commands/ops/update_product_registry.py` (investigation 04 §2.5) uses a three-regex classifier (canonical `Aspose.{Family}-FOSS-for-{Platform}`, lowercase variant, legacy form, case-insensitive after a documented 2026-09-11 upstream fix). This project's own `data/registry.json` was populated by a one-time manual re-emission of the legacy already-classified `data/products.json` (`b6efb73`, 2026-09-02) — no ongoing classification mechanism was ever ported into this project itself. Ruled: port/reimplement that classifier into `tools/discovery/` so every future discovery run classifies `family`/`platform` automatically, not just enumerates. Ready for a taskcard, not yet implemented.
- **WS5**: every write-capable role runs in its own isolated worktree, effective immediately as standing supervisor practice — never a shared checkout among concurrently live write-capable agents. Two concrete, code-level hardening items are queued (unscheduled, no taskcard yet): a deterministic fetch→rebase→retry push wrapper (closes failure classes A/D at the root), and a scheduled sweep of `docs/RESEARCH_LANE_*.md` for un-admitted `PROPOSAL` headings (closes class H). The detection/remediation split (`liveness.yml` detects, a human still remediates) stays as-is for now — closing it is G5-adjacent, not ruled today.
- **WS6 (new, owner-directed 2026-09-17):** `Aspose/aspose.org`'s `scripts/pipeline/commands/foss/readme_refresh_run.py` (~6,550 lines, read-only `gh api` review, no clone/pull — same discipline as investigation 04) is a real, production-hardened prior implementation of exactly this gate, adopted as the design baseline. Four principles ruled adopted directly: (1) **opening a PR is never publication** — `push()` only opens the PR; `data/readme_published_state.json`-equivalent state is written *exclusively* by a separate reconciler driven by a real, externally-confirmed merge event (`gh pr view`/merge state), never by the push call's own success — this project's own `propose.yml` must keep the same separation. (2) **mirror-vs-canonical target classification before any push** — their `classify_target_authority()` refuses to push to a clone that looks like a mirror (could be silently reset, confirmed live once against a real PR) without an explicit override; this project's registry has no equivalent check today and needs one before Gate C pushes anywhere. (3) **token redaction on every push-failure path**, not just success paths — matches and corroborates `core/secrets.py`'s existing discipline with a second real precedent. (4) **a surgical diff check** refusing any undeclared file change before commit. **Not ruled, deliberately: when Gate C's first live push happens.** Even this mature module's own header states plainly it has "not been exercised against a real external GitHub org... pending explicit authorization to push live" — the same caution applies here. The first live PR against any real product repo needs the owner's explicit go-ahead, the same standing rule already in force for registry writes (`OWNER-08`'s own precedent) — not something a ruling grants in advance. `scripts/pipeline/commands/foss/upstream_issue_workflow.py`, in the same directory, is flagged but not yet read — likely direct prior art for WS3's write side when that gets built.

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
