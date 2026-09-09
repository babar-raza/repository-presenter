# Healing Execution Plan — 2026-09-09

## Purpose

Every remaining, not-yet-fixed gap found by three external-review rounds this session (the
original AUD-001–005/REC-001–009 packet, the R1–R6 technical follow-up, and the D1–D9 trust-
boundary packet), plus this session's own self-review, now has a Taskcard across five files under
`plans/healing/`. This document is the single execution order for all of them: what depends on
what, what touches the same files (and therefore cannot run in parallel with itself), what is
explicitly excluded from autonomous execution and why, and the checkpoint/pause rules that govern
how this runs without stopping to ask after every item while still catching a genuine problem
before it compounds.

**Candidate sealing does not resume until Wave 7.** Per the owner's explicit instruction, the
fixes come first.

## Full inventory (24 items, 6 files)

| File | Done | Remaining |
|---|---|---|
| `trust-boundary-corrections.md` | TB-01, TB-03, TB-04, TB-06, TB-07 | TB-02, TB-05, TB-08, TB-09, TB-10 |
| `production-consistency-reassessment.md` | RC-05 | RC-01, RC-02, RC-03, RC-04, RC-06*, RC-07 |
| `self-review-remediation.md` | SR-01 | SR-02 (SR-03 deferred by choice) |
| `r1-reseal-operations.md` | PA-01 (resolves OPS-02†) | OPS-01, OPS-03 |
| `prior-audit-remnants.md` | PA-01 | PA-02, PA-03, PA-04, PA-05* |

`*` RC-06 and PA-05 are explicitly excluded from this pass — see "Excluded" below.
`†` OPS-02 (pop the stash) is subsumed by PA-01, which pops the same stash as part of its own
runbook. Executing PA-01 resolves OPS-02; it is not run separately.

## Same-file clusters (must run sequentially, never in parallel with each other)

`bundle/seal.py` was touched by **four** taskcards actually executed: PA-01, TB-07(pt.2), TB-06,
RC-05 (PA-05 would have been a fifth, but is excluded — see below). Each landed as its own commit
with a full-suite check before the next started — this was the single biggest sequencing
constraint in this plan.

`evidence/facts/links.py` is touched by both TB-08 (private-address boundary on `fetch_status`)
and TB-09 (HTML discovery in `extract_links`) — different functions, same file; sequential, not
parallel.

TB-10 and RC-07 build the *same* mechanism (a portfolio-wide, CI-gated evidence-consistency
sweep, reusing this session's existing `audit_link_completeness.py`/`audit_preserved_api_lists.py`
scripts). They are **merged into one execution**, not built twice.

## Execution order

### Wave 1 — `seal.py`/`jobs.py` cluster (sequential, P0)
1. **PA-01** [DONE] — land the stashed cache-seeding work + fix R5's lineage gap. First, because
   it's the largest, most foundational item and resolves OPS-02 as a side effect.
2. **TB-07 (parts 2–3)** [DONE] — `_site_manifest_hash` target fix + plugin-init audit. Same file
   area, immediately after.
3. **TB-06** [DONE] — bundle integrity (`verify_bundle`, `_write_bundle` secret-scan ordering,
   `_record_update`, `count_current_candidates`).
4. **RC-05** [DONE] — surface call-history variance on the manifest.
5. ~~**PA-05**~~ [EXCLUDED 2026-09-09 — see "Excluded" below] — freeze and version the acceptance
   contract. `state.yaml`'s own G3-W02 entry says this is deliberately deferred until every
   cohort has sealed, which has not happened; moved to Excluded rather than executed.

### Wave 2 — other independent P0 items
6. **TB-03** [DONE] — snapshot immutability (`git ls-tree` blind to uncommitted tracked-file
   edits).
7. **TB-08** — isolation boundary + private-address (SSRF) check.

### Wave 3 — machinery correctness (P0/P1)
8. **RC-04** — repair-routing self-check. Highest-priority machinery fix: this is what actually
   unblocks Email-Python and 3D-Java.
9. **RC-02** — unify section coverage with the renderer (root cause of the duplicated-API-list
   defect).
10. **RC-01** — generalize the completeness-backstop pattern into one registered mechanism.
11. **RC-03** — deterministic citation-completeness gate at reconciliation.

### Wave 4 — remaining defect fixes (P1)
12. **TB-02** — format claims from unreachable code / unread fixtures.
13. **TB-05** — fence validation via `EcosystemSpec.example_fences`.
14. **TB-09** — HTML link discovery + prose-matches-evidence seam (after TB-08, same file).
15. **PA-02** — scope `quote_located` to the finding's own section.

### Wave 5 — prevention/observability (P2, depends on Wave 3–4)
16. **TB-10 + RC-07 (merged)** — portfolio-wide CI-gated evidence-consistency sweep. Requires
    TB-01, TB-02, TB-04 landed (TB-01/TB-04 already are; TB-02 lands in Wave 4).

### Wave 6 — process/reporting (P3)
17. **PA-03** — four-count status reporting (after TB-06, for the integrity-valid definition).
18. **PA-04** — relocate the arrival list out of `state.yaml` prose. Extra care, not extra haste.
19. **SR-02** — tests for `research_edit.py`'s `append_entry`.

### Wave 7 — resume candidate work
20. **OPS-03** — re-attempt Email-Python and 3D-Java (now that RC-04 has landed).
21. **OPS-01** — 3D-Python remains paused on the canary-floor decision (see "Excluded" below)
    unless that decision lands first; otherwise pick a non-canary candidate for any remaining
    routine R1-shaped work.
22. **R2 historical re-adjudication list** — when each of the following candidates is next
    re-sealed, explicitly check its specific previously-swallowed findings, not just the general
    mechanism fixes: 3D Java (F01, F06, F08), 3D Python (F01–F03), Cells .NET (F03, F07), Cells
    C++ (F01–F04), Email Python (F01).

## Excluded from this autonomous pass — explicit decisions, not oversights

- **RC-06** (extraction-time unit-granularity fix): explicitly flagged high-risk, prototype-first
  in its own taskcard. Not attempted without an owner go/no-go on the prototype step first.
- **The 3D-Python canary call-volume floor** (`>= 20` calls): a tracked-metric policy call with
  three options recorded in `DECISION_LOG.md`, none chosen. Not resolved unilaterally.
- **SR-03** (RESEARCH_AND_GUIDELINES.md phase-2 split): already explicitly deferred by owner
  choice, optional.
- **AUD-003** (`plans/idea.md`'s denominator): owner-owned file, not mine to edit.
- **AUD-004** (gate-cursor drift): confirmed intentional parallelization, not a defect — no action.
- **PA-05** (freeze and version the acceptance contract, G3-W02): discovered mid-pass, 2026-09-09,
  re-reading `state.yaml` before starting it — G3-W02's own entry there says this is "moved behind
  the cohorts" (§28.12): deliberately deferred until every cohort has sealed, which has not
  happened (8 of 34 sealed; G3-W04 and the G4 cohorts are themselves still `PENDING`). This
  taskcard's own text did not check that constraint when it was authored. Not executed; would
  freeze the contract and re-seal every current candidate against that freeze ahead of a real,
  dated project-sequencing decision. AUD-005 (the underlying finding) stays open; only its timing
  is disputed. Needs owner direction, not autonomous judgment.

## Checkpoint and pause rules

- One taskcard = one commit (or a small, clearly-related set for a single taskcard's own multi-
  file diff) = one push, following this session's established discipline throughout: fetch,
  verify no divergence, push after each.
- Full test suite (`pytest tests/ -q --tb=no`, never `test_sealed_bytes.py` alone — isolation
  causes false ecosystem-registration errors) runs once per taskcard before its commit, not after
  every micro-edit.
- Each taskcard's plan-file `Status`/`Checklist` is updated in place as it completes, same as the
  D1–D9 execution pass.
- **Stop and flag, don't push through, if:** a fix reveals a genuinely new, previously-unknown
  defect outside its own taskcard's scope (record it, don't scope-creep the current taskcard to
  fix it too — give it its own taskcard, per this session's whole established discipline); a
  taskcard's own design decision (explicitly called out in several taskcards above, e.g. PA-03's
  count-source mapping, PA-05's version-increment rule) cannot be resolved from the taskcard's own
  text without guessing; a fix would require touching a file this plan didn't anticipate needing
  changed.
- Never weaken a test to make a taskcard's acceptance checks pass.
- Never force a candidate seal past a genuine, still-unresolved review rejection.

## Self-validation (performed before Wave 1 starts)

- [x] Every item from the 2026-09-09 prioritized gap list has a Taskcard: cross-checked P0/P1/P2/P3
  against the five plan files' Gap tables — all present.
- [x] Every `seal.py`-touching taskcard identified and sequenced (five: PA-01, TB-07pt.2, TB-06,
  RC-05, PA-05) — none scheduled in parallel with another.
- [x] Every `links.py`-touching taskcard identified and sequenced (two: TB-08, TB-09).
- [x] TB-10/RC-07 duplication caught and merged rather than built twice.
- [x] OPS-02/PA-01 overlap caught and resolved (one execution, not two).
- [x] RC-04 confirmed as the actual unblocker for OPS-03 (not TB-04, which fixes a different,
  already-landed defect — this distinction was already flagged to the owner directly, restated
  here so the plan itself doesn't silently rely on it being remembered).
- [x] Two pure-policy decisions (canary floor, RC-06 go/no-go) explicitly excluded rather than
  guessed at.
