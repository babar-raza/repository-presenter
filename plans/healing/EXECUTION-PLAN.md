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
| `trust-boundary-corrections.md` | TB-01, TB-02 (pt.1), TB-03, TB-04, TB-05, TB-06, TB-07, TB-08, TB-09 | TB-10 |
| `production-consistency-reassessment.md` | RC-01, RC-02, RC-04, RC-05 | RC-03*, RC-06*, RC-07 |
| `self-review-remediation.md` | SR-01 | SR-02 (SR-03 deferred by choice) |
| `r1-reseal-operations.md` | PA-01 (resolves OPS-02†) | OPS-01, OPS-03 |
| `prior-audit-remnants.md` | PA-01 | PA-02, PA-03, PA-04, PA-05* |

`*` RC-03, RC-06, and PA-05 are explicitly excluded from this pass — see "Excluded" below.
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
7. **TB-08** [DONE] — isolation boundary + private-address (SSRF) check.

### Wave 3 — machinery correctness (P0/P1)
8. **RC-04** [DONE, live re-verification deferred to Wave 7 — see its own Note] — repair-routing
   self-check. Verified against both real candidates' exact historical data directly: 3D-Java's
   F08 confirms the fix; Email-Python's F03 honestly does not match this mechanism (a different,
   separately-scoped defect). Neither candidate has a live composition blocked by this specific
   issue right now to re-run `present` against - see the taskcard's own Note for the full finding.
9. **RC-02** [DONE] — unify section coverage with the renderer (root cause of the duplicated-
   API-list defect). Landed additively (union with the plan's own signal, not a replacement) in
   two separate commits (api_reference, then documentation_resources) after a self-caught bug
   during api_reference's implementation broke four real candidates by replacing instead of
   adding; two real candidates (Cells .NET, Email-Python) now show a genuine, desirable new
   divergence in `test_sealed_bytes.py` - see the taskcard's own Note.
10. **RC-01** [DONE] — generalize the completeness-backstop pattern into one registered
    mechanism. Pure refactor, verified byte-identical against the real portfolio; a taskcard
    claim of a pre-existing append-behavior test didn't hold (none existed) - added directly.
11. ~~**RC-03**~~ [EXCLUDED 2026-09-09 — see "Excluded" below] — deterministic citation-
    completeness gate at reconciliation. Investigated and prototyped twice, both verified
    empirically against the real portfolio; the real remaining question (how many additional
    reconciliation re-asks across the whole portfolio is an acceptable cost) is a policy call,
    not resolved by further engineering. Reverted before commit, not landed.

### Wave 4 — remaining defect fixes (P1)
12. **TB-02** [DONE, part 1 only — part 2 excluded, see below] — format claims from unreachable
    code (landed) / unread fixtures (excluded: same verb-vocabulary ambiguity class as RC-03,
    would introduce real false negatives against real portfolio data).
13. **TB-05** [DONE] — fence validation via `EcosystemSpec.example_fences`, plus a CommonMark-
    based `_fences` (tilde fences, multi-word info strings). Verified against all 8 real sealed
    candidates directly - zero new BC-03 failures, exercised (Cells .NET's three real ```csharp
    fences correctly recognized).
14. **TB-09** [DONE] — HTML link discovery (`extract_links`, `html_inline` shape only - a
    `html_block`-only raw tag stays a documented, out-of-scope gap, unused by the real portfolio)
    + a new authoring-side seam (`unit_example_action_mismatches`) checking a unit's prose about
    a cited example against that example's own recorded format claims. Verified against all 8
    real sealed candidates: zero regressions, zero false positives across 866 real units, and
    confirmed genuinely exercised (not vacuous) by real matching-direction cases.
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
- **RC-03** (deterministic citation-completeness gate at reconciliation): investigated and
  prototyped twice this pass, both verified empirically against every real candidate's sealed
  `dispositions.json` (not assumed) - a bare word-boundary match (the taskcard's own literal Fix
  text) produced 20-38 false positives per candidate from short/generic symbol names doubling as
  ordinary English words; a backtick-code-span-restricted redesign found real, previously-unknown
  citation gaps with realistic precision, but still 3-10 per candidate portfolio-wide. The
  question left open is not precision - it is whether the aggregate cost of that many additional
  reconciliation re-asks across the whole portfolio (`source_reconciliation` is independently
  confirmed non-deterministic, `RC-05` this pass) is worth the completeness gain, a policy/product
  call the owner should make, not this session unilaterally. No code was committed; the
  in-progress prototype was reverted before commit. `plans/healing/production-consistency-
  reassessment.md`'s own RC-03 entry has the full investigation and a concrete reversal path.
- **TB-02 part 2** (`format_facts`'s fixture-to-input-claim binding tightening, `formats.py`):
  implemented, then verified against real portfolio data before trusting it - found it wrongly
  downgrades two genuinely-true facts, `format:input.pptx` (Slides-Python, read via a bare
  `Presentation("new.pptx")` constructor) and `format:input.msg` (Email-Python, read via
  `MapiMessage.from_file(...)`, a factory method) - `format_claims`'s verb vocabulary recognizes
  neither shape as an input operation. A follow-up literal-occurrence heuristic fixed those two but
  introduced a third false-positive class (Email-Python's `"note.txt"`, an attachment name paired
  with inline bytes, never read from disk). Same class of ambiguity as RC-03: the heuristic cannot
  separate a genuine-but-unrecognized read from a non-read use of a file-like string without a real
  false case on one side or the other. Reverted before commit; `trust-boundary-corrections.md`'s
  TB-02 entry has the full investigation.
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
