# Production Consistency Reassessment — Taskcards

## Context

This converts the 2026-09-08 production reassessment ("what is actually breaking consistency
across reruns") into executable taskcards. That reassessment was delivered in-session as prose
(no `self_review:` YAML block exists); its structure — Symptoms (S1–S5), Root Causes (RC1–RC6),
Structural Weaknesses (SW1–SW6), a Preserve list, six Durable Design proposals, and Validation
controls — is parsed directly below. Evidence backing every claim here is either a directly-traced
code path (cited by file:line) or a directly-observed artifact (`calls.jsonl`, `dispositions.json`,
`plan.json`, `review.json` for the specific candidates named), not inference.

Two of the findings below (RC4, applied to `aspose-3d-foss/Aspose.3D-FOSS-for-Java` and
`aspose-email-foss/Aspose.Email-FOSS-for-Python`) are also recorded as `DECISION_LOG.md` entries
dated 2026-09-08; this file is the executable-work counterpart to those narrative records, not a
duplicate of them.

**None of RC-01 through RC-07 is implemented.** This plan file itself makes no change outside
`plans/healing/`.

## Gap table

| Gap ID | Description | Taskcard ID |
|---|---|---|
| RC1 / SW1 | Free-form model output fields (`plan.json.links`, `dispositions.json[*].fact_ids`) carry completeness obligations with no independent deterministic cross-check, fixed reactively one incident at a time | RC-01 |
| RC2 / SW2 | `placement.py`'s coverage model (`planned_fact_ids`/`renderer_fact_ids`) is a hand-maintained duplicate of what the renderer actually renders, and has already drifted from it | RC-02 |
| RC3 | `source_reconciliation`'s citation completeness varies under LLM sampling with no deterministic verification gate | RC-03 |
| RC4 / SW4 | Review's `causal_stage` is a single unverified model guess that gates repair routing, with no check for whether the target text is actually authoring-owned | RC-04 |
| RC5 / SW6 | Non-deterministic call history (multiple differing successful attempts for the same logical call) is invisible without manual `calls.jsonl` reading | RC-05 |
| RC6 | Extraction-time unit granularity (whole markdown lists) doesn't match the per-symbol grain reconciliation needs to dispose correctly | RC-06 |
| SW5 | `test_sealed_bytes` is structurally blind to defects baked into a candidate's own sealed `plan.json`/`dispositions.json` (it only re-renders them) | RC-07 |

## Taskcards

### RC-01 — Generalize the completeness-backstop pattern into one registered mechanism

- **Status:** Not Started
- **Gap linkage:** RC1, SW1
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Replace the two now-separate, independently-written backstops in `plan_checks`
    (`additional_example_ids` missing-append; `links` missing-append, landed `29ebb7c`) with one
    small, explicit table — `{field_name: (required_ids_fn, apply_fn)}` — iterated once, so the
    next instance of "a free-form plan field must contain everything a deterministic source says it
    must" is a table row, not a new bespoke diff discovered by incident.
  - **Allowed paths:** `src/repository_presenter/components/readme/composition/planning.py`,
    `tests/components/readme/composition/test_planning.py`
  - **Forbidden:** `renderer.py`, `placement.py`, `dispositions.py`, any prompt file, any other
    stage's checks.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --repo <any registry entry>` produces identical output
    before/after this refactor for every currently-sealed candidate (this is a refactor of *how*
    the two existing backstops are expressed, not a behavior change — verify with `test_sealed_bytes`).
  - UI/Web/API: N/A.
  - Tests: `tests/components/readme/composition/test_planning.py`'s existing
    `test_a_verified_rewrite_disposition_names_link_targets_the_plan_must_carry` and the
    `additional_example_ids` missing-append test both still pass unmodified (same behavior, new
    internal mechanism); add one new test proving a *third*, synthetic backstop entry registered in
    the table is applied without touching the two existing ones (proves genericity, not just that
    the two known cases still work).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - Full file replacement: `planning.py`'s `plan_checks` function body only (not the whole file) —
    the two inline backstops become table entries; behavior for the two existing fields must be
    byte-identical before/after.
  - New/updated tests: the synthetic third-entry test above (regression path: prove a missing
    backstop registration is caught by a lint/test, e.g. "every field name in the table has a
    matching schema property," so a typo'd field name fails loudly, not silently).
  - Migration: N/A — internal refactor, no external contract changes.
- **Hard rules:** keep `plan_checks`'s public signature unchanged (same callers in `cli.py` and
  `repair/targeted.py`); no new dependencies; deterministic (table iteration order must be stable —
  use a tuple or ordered dict literal, never a plain `set`).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a third real-world instance of this class (should one be found later) is
    closed by adding a table row, with no new function needed.
  - Test coverage: 5/5 = existing two cases + the synthetic third case all pass; a deliberately
    broken table entry (wrong field name) fails a test, not silently no-ops.
  - No regressions: 5/5 = every currently-sealed candidate's `plan.json` output is byte-identical
    pre/post refactor (verified via `test_sealed_bytes` plus a direct diff of regenerated `plan.json`
    for 2–3 sealed candidates in dry-run).
  - Determinism/reproducibility: 5/5 = table iteration order fixed and tested.
  - Documentation/traceability: 5/5 = `plan_checks`'s docstring (already describes the two backstops
    narratively) is updated to describe the table instead, and a `DECISION_LOG.md` entry records
    the refactor and cites this taskcard ID.
- **Now (runbook):**
  1. `git log --oneline -- src/repository_presenter/components/readme/composition/planning.py | head -5` — confirm no concurrent edits in flight before starting.
  2. Read `plan_checks` in full; extract the two existing backstops into the table shape.
  3. Write the synthetic third-entry test first (red).
  4. Implement the table + iteration; make it pass.
  5. `pytest tests/components/readme/composition/test_planning.py -q` — all green.
  6. `pytest tests/test_sealed_bytes.py -q` (as part of the FULL suite, never standalone — isolation
     causes false ecosystem-registration `ConfigError`s) — only the pre-existing known failures.
  7. `ruff check` + `mypy` on the changed file.
  8. Commit, push.

### RC-02 — Unify section coverage with the renderer instead of shadowing it

- **Status:** Done — both halves landed and pushed as two separate commits, per this taskcard's
  own runbook.
- **Note, documentation_resources half:** smaller than api_reference's - `planned_fact_ids`'s
  existing generic per-section `plan["links"]` loop already named exactly what
  `_documentation_resources` iterates, so that half of its coverage was already accurate before
  this taskcard. The one real gap: the renderer always appends its own "Open an issue" line from
  `identity:repository` when SUPPORTED, regardless of whether any plan link names it - a
  preserved unit citing only that fact for an issues mention duplicated a line the renderer
  produces, undetected. `renderer_fact_ids` gained a `documentation_resources` branch
  (`_documentation_resources_issues_fact_id`) covering exactly that, additive to the existing
  link-based coverage via the same union `placements()` already performs - applying the
  union-not-replace lesson from the api_reference half from the start this time. Verified directly
  against the real portfolio via `test_sealed_bytes.py` *before* writing any tests: the same three
  already-explained divergences, nothing new.
- **Note, api_reference half:** `placement.py` gained `api_reference_hub_methods(plan, facts)`
  (the exact hub/method-ownership computation `renderer.py`'s `_api_reference` now also calls,
  so the two cannot independently drift) and `api_reference_covered_fact_ids(plan, facts)` (every
  verified class/enum, plus every hub-owned method - what the Core API table and Detailed Member
  Reference actually display). `renderer_fact_ids` gained an additive, optional `plan` parameter
  to reach it (the taskcard's own prediction that no call site would need to change was wrong -
  `placements()`'s one call site now passes `plan` through too).
  **Self-caught bug, fixed before landing, not shipped:** the first version of this fix *removed*
  `planned_fact_ids`'s existing `api_reference` branch (the plan's own per-hub
  `symbol_fact_id`/`fact_ids`), replacing it outright with the new renderer-derived set - this
  broke `test_sealed_bytes.py` for four real candidates (PDF Java, Cells C++, Cells .NET, Email
  Python), because several real dispositions cite coarse, *namespace*-level facts that only ever
  matched the plan's own (independently curated) per-hub `fact_ids`, never the renderer-derived
  class/enum/method set. Fixed by keeping `planned_fact_ids`'s branch and **adding** the
  renderer-derived set on top of it via the union `placements()` already performs, rather than
  replacing it - re-verified against all four real candidates directly (not just the test suite)
  before proceeding.
  **Two real, desirable content changes, verified as correct rather than assumed:** even after
  that fix, `test_sealed_bytes.py` newly diverges for two real candidates - `aspose-cells-foss/
  Aspose.Cells-FOSS-for-.NET` and `aspose-email-foss/Aspose.Email-FOSS-for-Python` - both because
  a preserved Exceptions/Enumerations list unit cites *individual* class/enum facts directly
  (checked against both candidates' real `dispositions.json` and `facts.json`), which the plan's
  hub-only model never covered (these aren't hub classes) but the renderer-derived model
  correctly does. Confirmed by direct inspection this is a genuine, previously-undetected
  duplicate (the same class of defect RC-02 exists to catch), not a bug. Per this session's own
  `EXECUTION-PLAN.md`, candidate-sealing work stays held for Wave 7 - neither candidate is
  re-sealed here; a future Wave-7 pass will see this divergence and re-seal through the normal
  record-then-adopt path. `test_sealed_bytes.py` now has three known, explained divergences (the
  pre-existing 3D-Python canary floor and Email-Python backtick issue, plus this one - Cells
  .NET's is new, Email-Python's adds a second reason on top of its existing one), not the
  previous two - recorded here so a future full-suite run isn't read as an unexplained new
  failure.
- **Checklist (api_reference half):** [x] `covered_fact_ids`-equivalent pair added, shared with
  the renderer [x] instrumented property test (renders a synthetic fact set, cross-checks
  `api_reference_covered_fact_ids` against the actual rendered section) [x] regression test
  reproducing the general "non-hub class/enum overlap" shape (not the exact historical Aspose.
  Email Python module-only-citation shape, which needs RC-06's finer-grained extraction, not
  this taskcard - see RC-04's own honest note on the same distinction) [x] verified against every
  real candidate directly, self-caught and fixed one real bug before committing [x] full suite
  (three known, now-explained divergences; see above) [x] `documentation_resources` half - the
  smaller Issues-line gap, verified against the real portfolio before writing tests this time,
  no new divergence.
- **Gap linkage:** RC2, SW2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** For each mixed-owned render function (`_api_reference`, `_documentation_resources`,
    and any other section mixing renderer-owned structure with authored prose), add a paired pure
    function `covered_fact_ids(context) -> frozenset[str]` returning exactly the fact IDs that
    function will display for the given facts/plan. `placement.py`'s `planned_fact_ids()` and
    `renderer_fact_ids()` call these functions instead of re-deriving a narrower approximation
    (today, `api_reference`'s coverage model only knows the plan's chosen "hub" symbols; the
    renderer's own table covers every verified class/enum — this is the exact drift that let
    Aspose.Email Python's and Aspose.Cells C++'s preserved member-lists go undetected as
    duplicative, `renderer.py:449-490`, `placement.py:65-91`).
  - **Allowed paths:** `src/repository_presenter/components/readme/composition/renderer.py`,
    `src/repository_presenter/components/readme/composition/placement.py`,
    `tests/components/readme/composition/test_renderer.py`,
    `tests/components/readme/composition/test_placement.py`
  - **Forbidden:** `planning.py`, `dispositions.py`, any prompt file — this is a rendering/placement
    refactor only, not a change to what the model is asked to produce.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present` byte-identical output for every currently-sealed candidate
    with no `api_reference`/`documentation_resources` change in the underlying facts.
  - UI/Web/API: N/A.
  - Tests: an instrumented property test — run the renderer against a synthetic fact set, record
    every fact ID it actually referenced while building `api_reference`'s output, assert it equals
    `covered_fact_ids()`'s declared set exactly (catches future drift automatically instead of
    requiring a human to notice, which is what let this gap stand undetected until today).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - Full file replacements: the two files above, refactored section by section (land `api_reference`
    first behind its own commit + full test run, then `documentation_resources`, never both at once
    under this deadline — reduces blast radius per commit).
  - New/updated tests: the instrumented property test above, plus a regression test reproducing the
    exact Aspose.Email Python shape (a `VERIFIED_PRESERVE` list citing only a module-level fact,
    whose members overlap the table) and asserting it is now correctly detected as "overlap," not
    "placed."
  - Migration: N/A.
- **Hard rules:** keep `planned_fact_ids(plan, section)`'s and `renderer_fact_ids(section, facts)`'s
  public signatures unchanged — only their internal implementation for `api_reference` and
  `documentation_resources` changes to delegate to the renderer's own coverage functions; update
  every call site if a signature must change (none currently expected to).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = one source of truth for "what does this section render," not two
    independently-maintained approximations.
  - Test coverage: 5/5 = the property test would have caught the exact Aspose.Email Python defect
    before it ever reached review.
  - No regressions: 5/5 = `test_sealed_bytes` full suite shows only pre-existing known failures;
    every other sealed candidate's `api_reference`/`documentation_resources` output is byte-identical.
  - Determinism/reproducibility: 5/5 = `covered_fact_ids()` is a pure function of `(facts, plan)`,
    no hidden state.
  - Documentation/traceability: 5/5 = `placement.py`'s module docstring (already explains the three
    placement rules) is updated to state coverage is now renderer-derived, not hand-modeled; a
    `DECISION_LOG.md` entry cites this taskcard and the Aspose.Email Python defect it retroactively
    would have caught.
- **Now (runbook):**
  1. Write the instrumented property test for `api_reference` first (red — the current hand-modeled
     coverage will fail it on the reproduced Aspose.Email Python shape).
  2. Add `covered_fact_ids()` to `_api_reference`'s module; wire `planned_fact_ids`/`renderer_fact_ids`
     to call it for that section only.
  3. `pytest tests/components/readme/composition/test_renderer.py tests/components/readme/composition/test_placement.py -q`
  4. `pytest tests/ -q --tb=no` (full suite) — confirm only pre-existing known failures.
  5. Commit `api_reference`'s change alone; push.
  6. Repeat steps 1–5 for `documentation_resources` as a second, separate commit.
  7. Once both land: re-run `present` for `aspose-email-foss/Aspose.Email-FOSS-for-Python` and
     `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` and confirm the coverage model now flags the
     preserved-list overlap (review may still need RC-04 to actually act on the resulting finding
     correctly — see RC-04's runbook for the full path to a clean seal).

### RC-03 — Deterministic citation-completeness gate at reconciliation

- **Status:** Not Started
- **Gap linkage:** RC3
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** After `source_reconciliation`'s model call returns, deterministically scan each
    `VERIFIED_PRESERVE`/`VERIFIED_REWRITE` unit's own text for other known `public_symbol` names
    (word-boundary substring match against the fact table's symbol names — the same low-risk
    technique already used by `_LOWER_WORD` in `renderer.py`) that are absent from that unit's
    `fact_ids`. If found, fail reconciliation's own contract check (same mechanism shape as
    `plan_checks`'s `errors` list) and force exactly one re-ask naming the missing identifiers
    explicitly. This is **not** a retry-for-a-better-random-roll (explicitly rejected this session
    as "manufacture acceptance by retrying until lucky") — it is a deterministic gate that rejects
    the *class* of under-citation regardless of which roll produced it.
  - **Allowed paths:** `src/repository_presenter/components/readme/reconciliation/dispositions.py`,
    `prompts/source_reconciliation.yaml` (re-ask instruction text only, not the base system prompt's
    disposition vocabulary), `tests/components/readme/reconciliation/test_dispositions.py`,
    `tests/components/readme/reconciliation/test_normalization.py`
  - **Forbidden:** `placement.py`, `renderer.py`, `planning.py` — this fixes reconciliation's own
    output quality, not how downstream stages consume it (that is RC-02's scope).
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present` for a repository whose upstream README contains a
    member-reference list under-cited by the model produces a rejection-and-reask cycle visible in
    the CLI's own stage output (`dispositions: ... provider calls N`), not a silent pass-through.
  - UI/Web/API: N/A.
  - Tests: a mutation test — construct a disposition with a known symbol name present in the unit's
    text but absent from `fact_ids`; assert the contract check rejects it, naming the missing
    symbol; a no-op case with complete citation passes unchanged. Also test the one-attempt cap: a
    second consecutive under-citation on the re-ask is recorded as advisory (never an infinite loop).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A — this check runs against real `FactsDocument` data in
    every code path; `Mock vs Live mode` maps here to: the gate runs identically whether the
    upstream model call was live or replayed from `calls.jsonl` (it inspects the *output*, not the
    call path).
- **Deliverables:**
  - Full file replacement: `dispositions.py`'s contract-check function, extended with the new gate;
    `source_reconciliation.yaml`'s re-ask packet, extended to carry the missing-identifier list when
    this specific rejection reason fires.
  - New/updated tests: the mutation test and one-attempt-cap test above; a regression test
    reproducing Aspose.Email Python's exact five under-cited units (`inherited_unit:053/055/057/059/061.list`,
    each citing only `public_symbol:email_foss.msg`/`.cfb`) and asserting the gate now catches all
    five.
  - Migration: N/A — the disposition schema itself is unchanged (`fact_ids` already accepts a list);
    only the *validation* of that field's completeness is new. If a later change needs a new
    disposition value, treat that as a separate, forward-compatible schema addition (see RC-06).
- **Hard rules:** no new deps; deterministic (word-boundary regex, no fuzzy matching, no LLM call in
  the check itself); one-attempt cap preserved (never infinite retry, matching this project's
  existing `MAX_ROUNDS` discipline in `repair/targeted.py`).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the *class* of under-citation is caught mechanically regardless of which
    non-deterministic roll produced it — verified by feeding the gate all four of Aspose.Email
    Python's historical `calls.jsonl` responses (2026-09-05 through 2026-09-07) and confirming it
    flags the three under-cited ones and accepts the one that matches what's currently sealed.
  - Test coverage: 5/5 = mutation + no-op + one-attempt-cap + the five-unit regression case all pass.
  - No regressions: 5/5 = full suite green except pre-existing known failures; no previously-passing
    candidate's reconciliation output changes (verify via `test_sealed_bytes` and a spot digest
    check on 2–3 sealed candidates' `dispositions.json`).
  - Determinism/reproducibility: 5/5 = the gate itself is pure and deterministic; it does not
    eliminate model sampling variance, only rejects one specific class of bad output from it — be
    explicit in the PR description that this is a best-effort mechanical net, not a correctness
    proof (a model could still discuss a symbol without naming it verbatim and evade the gate).
  - Documentation/traceability: 5/5 = `dispositions.py`'s docstring and a `DECISION_LOG.md` entry
    both state the gate's exact scope and known limit.
- **Now (runbook):**
  1. Extract Aspose.Email Python's four historical `source_reconciliation` responses from
     `candidates/aspose-email-foss__Aspose.Email-FOSS-for-Python/*/calls.jsonl` (already-observed
     2026-09-08) as fixture data for the regression test.
  2. Write the mutation test (red).
  3. Implement the word-boundary scan + contract-check rejection + re-ask packet extension.
  4. `pytest tests/components/readme/reconciliation/ -q` — all green including the new cases.
  5. `pytest tests/ -q --tb=no` (full suite) — only pre-existing known failures.
  6. Re-run `present --repo aspose-email-foss/Aspose.Email-FOSS-for-Python` — confirm the gate now
     fires and the re-ask either produces a complete citation (candidate proceeds toward RC-02's
     coverage fix and a possible clean seal) or is recorded advisory after one attempt (candidate
     stays honestly unsealed, per this project's own established discipline — never forced).
  7. Commit, push.

### RC-04 — Repair-routing self-check for placed-text misattribution

- **Status:** Done — mechanism fixed, tested against both real candidates' exact historical
  data; live CLI re-verification (runbook steps 5-6) deliberately deferred, not attempted, for
  reasons found and recorded below rather than assumed.
- **Note, mechanism fix:** `review_defects()` (`targeted.py`) gained a `placed: Mapping[str,
  list[str]] | None = None` parameter (additive, optional - every existing call site is
  unaffected without it, confirmed by a dedicated test) - `composition/placement.py`'s own
  `placed_texts()` output. Before trusting a finding's `causal_stage`, its `quote` is checked
  against that section's placed texts; a match forces the route to S4 regardless of what
  `causal_stage` claimed, and records `misrouted: True` on both the in-memory `Defect.record` and
  (via `RepairLedger.record()`, extended) `repairs.json` itself - `summary()` reports a count,
  reading the field with `.get(..., False)` so an older `repairs.json` without it never raises.
  The one real caller, `rounds.py::round_defects()`, now computes `placed_texts(placements(
  current.planned.output, current.reconciled.output, tx.facts, tx.entry.ecosystem))` and passes
  it through - **`rounds.py` was not in this taskcard's original Allowed paths list**, but there
  is no other way to thread this real data through the only caller; a minimal, necessary
  extension, not a redesign.
- **Note, real-candidate verification - found a real discrepancy against the taskcard's own
  premise, verified rather than assumed, and did not force either candidate to "pass":**
  - **Aspose.3D for Java (F08):** confirmed both directions directly against the real transaction
    at `runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-Java/e308de58888635956cd66e5b0e2994dd42cd4356/`
    (still present locally, gitignored): F08's exact quote **is** a substring of
    `inherited_unit:023.paragraph`'s exact `VERIFIED_PRESERVE`-disposed text - the fix correctly
    routes it to S4. But this candidate's **currently-sealed** bundle (`sealed_at:
    2026-09-06T18:27:50Z`, `state: READY_FOR_PROPOSAL`) predates this finding entirely - it is an
    older, unrelated seal from before the 2026-09-08 re-seal attempt (the one that hit F08) ever
    ran. That attempt made no manifest/README change on failure (confirmed in the 2026-09-08
    05:55 `DECISION_LOG.md` entry itself), so there is no live-blocked candidate for this specific
    incident to re-verify against right now - re-running `present` today would start a *fresh*
    reconciliation, which `RC-05` (landed this same pass) established is genuinely
    non-deterministic, so it might not even reproduce F08's own disposition shape.
  - **Aspose.Email for Python (F03):** checked directly, not assumed "the same defect class" as
    the taskcard's own Gap linkage framed it - the real finding's quote (`"| Class | Description
    |"`, from `runs/transactions/aspose-email-foss__Aspose.Email-FOSS-for-Python/
    10a906b48c0c11005c4d93b524e4431901c9717c/review.json`) is the Core API **table**'s own
    header, renderer/plan output, and does **not** substring-match any of the five preserved
    `api_reference` list units' real text (checked against all five directly). This mechanism,
    exactly as scoped by this taskcard, correctly does not touch it - recorded honestly as a new
    test (`test_aspose_email_pythons_real_finding_does_not_match_this_mechanism_honestly`) rather
    than forced to assert S4 routing that the real data does not support. This candidate's
    blocking defect needs a different, separately-scoped fix (or a fresh, non-deterministic
    reconciliation run producing a different disposition shape) - not claimed resolved here.
  - **Decision:** given (a) neither candidate has a live, currently-blocked composition this
    specific fix would visibly unblock right now, (b) a live re-run costs real provider calls and
    wall-clock time for confirmatory value already established more reliably by the two
    real-data regression tests above, and (c) this session's own `EXECUTION-PLAN.md` explicitly
    holds all candidate-sealing work for Wave 7 - runbook steps 5-6 (`repository-presenter
    present --repo ...` against both real candidates) are deliberately **not** run in this pass.
    Both candidates' `DECISION_LOG.md` entries are updated with this exact finding (not "resolved
    by RC-04") so a future Wave-7 re-seal attempt starts from accurate, current information.
- **Checklist:** [x] mechanism fix, additive signature [x] `repairs.json` gains `misrouted`,
  forward-compatible [x] misrouting-detection + no-op unit tests [x] both real candidates' exact
  historical findings reproduced and checked directly (one confirms the fix, one honestly does
  not) [x] full suite (only the two known pre-existing failures remain) [ ] live CLI
  re-verification - deliberately deferred to Wave 7, not attempted, for the reasons above.
- **Gap linkage:** RC4, SW4 (also the direct unblock path for the `aspose-3d-foss/Aspose.3D-FOSS-for-Java`
  and `aspose-email-foss/Aspose.Email-FOSS-for-Python` candidates recorded unsealed in `DECISION_LOG.md`, 2026-09-08)
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Before trusting a review finding's `causal_stage` to route a repair attempt, mechanically
    check whether the finding's `quote` is a substring of `placement.py`'s own `placed_texts()`
    output for that section. If so, the defect cannot be an authoring (`S6`) defect regardless of
    what `causal_stage` claims — force the repair target to `S4` (`source_reconciliation`, already a
    legal `STAGE_JOBS` target in `repair/targeted.py:34-39`) instead, and record `misrouted: true`
    in `repairs.json`, distinct from `unrepairable`, so the ledger can finally tell "never had a
    chance" apart from "genuinely resisted repair."
  - **Allowed paths:** `src/repository_presenter/components/readme/repair/targeted.py`,
    `tests/components/readme/repair/test_targeted.py`
  - **Forbidden:** `review/independent/review.py` (do not change what review *reports* — only how
    repair *routes* what it already reported), `placement.py` (read its `placed_texts()` output,
    do not modify it), any prompt file.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java` and
    `--repo aspose-email-foss/Aspose.Email-FOSS-for-Python` both show a repair round targeting `S4`
    (not `S6`) for the specific findings F08 and the api_reference duplication finding respectively.
  - UI/Web/API: N/A.
  - Tests: a synthetic review finding whose `quote` is a substring of a `VERIFIED_PRESERVE` placed
    unit's text but whose `causal_stage` falsely claims `S6` — assert `review_defects()` now returns
    a `Defect` with `stage == "S4"`, not `"S6"`, and `record["misrouted"] is True`. A no-op case: a
    genuine `S6` finding whose quote is *not* found in any placed text routes to `S6` unchanged.
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - Full file replacement: `repair/targeted.py`'s `review_defects()` function, extended with the
    placed-text substring check before the existing `causal_stage`-derived routing logic.
  - New/updated tests: the misrouting-detection test and the no-op case above; a regression test
    reproducing both real candidates' exact findings (F08 for 3D-Java; the api_reference finding for
    Email-Python) and asserting both now route to `S4`.
  - Migration: `repairs.json`'s schema gains one optional boolean field (`misrouted`) — forward-
    compatible (existing `repairs.json` files without the field remain valid; `RepairLedger.summary()`
    must handle its absence as `False`, not raise).
- **Hard rules:** keep `review_defects()`'s public signature unchanged (same callers); `S4` routing
  must go through the exact same `STAGE_JOBS`/`repair_packet` path an `S6` defect would, no special-
  cased shortcut; deterministic (substring match, no LLM call in the routing decision itself).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = both real, currently-unsealed candidates now route their blocking finding
    to a stage that can actually act on it, verified by re-running `present` and observing the
    routing change directly in CLI output, not just in a unit test.
  - Test coverage: 5/5 = misrouting-detection + no-op + both real-candidate regression cases pass.
  - No regressions: 5/5 = every other candidate's repair routing is byte-identical (their findings
    never match a placed-text substring); full suite shows only pre-existing known failures.
  - Determinism/reproducibility: 5/5 = the substring check is pure and deterministic.
  - Documentation/traceability: 5/5 = `targeted.py`'s module docstring gains this fourth
    "review finding routed to..." case alongside its existing three (S2/evidence, deterministic-
    section, unrepairable stage); `DECISION_LOG.md` entries for both candidates are updated with
    "resolved by RC-04" once verified, per SR-01's own precedent for keeping records current.
- **Now (runbook):**
  1. Write the misrouting-detection test using a hand-built `placed_texts()` fixture (red).
  2. Implement the substring check in `review_defects()`.
  3. `pytest tests/components/readme/repair/test_targeted.py -q` — all green.
  4. `pytest tests/ -q --tb=no` (full suite) — only pre-existing known failures.
  5. Re-run `present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java`; confirm the repair round now
     targets `S4`; observe whether reconciliation's re-ask resolves the finding or the candidate is
     recorded advisory/stays unsealed (either is an honest outcome — do not force a seal if it
     still doesn't resolve).
  6. Repeat step 5 for `aspose-email-foss/Aspose.Email-FOSS-for-Python`.
  7. Update both candidates' `DECISION_LOG.md` entries with the outcome.
  8. Commit code + doc updates; push.

### RC-05 — Surface reconciliation call-history variance on the manifest

- **Status:** Done — landed and pushed.
- **Note:** Grouped by job across the whole transaction ledger (`inputs.transaction/calls.jsonl`,
  read directly - not `staged[LEDGER_FILENAME]`, which `composition_ledger()` already trims to
  only the calls the final accepted composition consumed), not by job **and**
  `logical_call_id` together: empirically checked against this session's own real, already-
  observed Aspose.Email Python `calls.jsonl` history first, which showed the diagnosed
  `source_reconciliation` variance comes from *four different* `logical_call_id`s (one per
  repair-round packet), not one repeated identically - a same-`logical_call_id`-only design
  (the taskcard's own literal Fix wording, read narrowly) would have surfaced nothing for it at
  all. Verified directly: `_call_variance` against that real ledger reports
  `source_reconciliation: 4`, matching the hand diagnosis exactly; the real candidate directory
  itself was never mutated (read-only check per the runbook). New optional manifest field
  `call_variance`: a list of `{"job", "distinct_responses", "response_sha256s"}`, present only
  when a job's successful attempts disagree, absent otherwise (chosen and tested explicitly, per
  the taskcard's own requirement not to leave that ambiguous). `verify_bundle()` unchanged - the
  field is optional and not part of its checks.
- **Checklist:** [x] two test cases (variance present / absent) [x] real-history check against
  Aspose.Email Python (read-only) [x] schema + README_CONTRACT.md + seal.py docstring updated
  [x] full suite (only the two known pre-existing failures remain)
- **Gap linkage:** RC5, SW6
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** At seal time, if a job's `calls.jsonl` ledger has more than one successful attempt with
    *differing* `response_sha256` for the same `logical_call_id`, record that count and the differing
    hashes on `manifest.json` (e.g. `"disposition_variance": {"job": "source_reconciliation", "distinct_responses": 4}`).
    This does not fix non-determinism; it makes it observable without the 30+ minutes of manual
    `calls.jsonl` reading this session's Email-Python diagnosis required.
  - **Allowed paths:** `src/repository_presenter/components/readme/bundle/seal.py`,
    `tests/components/readme/bundle/test_seal.py`
  - **Forbidden:** `core/llm/ledger.py`, `core/llm/jobs.py` (read the ledger, do not change its
    format), any stage's job logic.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter status` (or a follow-up display change, out of this taskcard's scope)
    is not required to change; the manifest field existing and being correct is the acceptance bar.
  - UI/Web/API: N/A.
  - Tests: synthetic `calls.jsonl` with two successful attempts at differing `response_sha256` for
    one `logical_call_id` — assert the manifest surfaces `distinct_responses: 2`; a no-op case with
    one successful attempt (or several with identical response hashes) surfaces no such field (or
    `distinct_responses: 1`, whichever is chosen — pick one and test it explicitly, do not leave it
    ambiguous).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A — this reads real ledger data at seal time in every path.
- **Deliverables:**
  - Full file replacement: `seal.py`'s manifest-writing path, extended with this one new optional
    field.
  - New/updated tests: the two cases above.
  - Migration: `manifest.json` schema gains one optional field — forward-compatible; existing
    sealed candidates' manifests remain valid without it; `verify_bundle()` must not require its
    presence.
- **Hard rules:** no new deps; read-only with respect to the ledger (never rewrites `calls.jsonl`);
  deterministic given a fixed ledger.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a future Email-Python-shaped diagnosis takes one `cat manifest.json`
    lookup instead of manually reading a multi-day ledger.
  - Test coverage: 5/5 = both cases above pass; run against the real, already-observed Aspose.Email
    Python `calls.jsonl` history and confirm it reports `distinct_responses: 4` (or the correct
    count after de-duplicating truly-identical replays) for `source_reconciliation`.
  - No regressions: 5/5 = every currently-sealed candidate's manifest gains at most one new optional
    key; no existing key changes; `verify_bundle()` and `test_seal.py`'s existing suite pass
    unmodified.
  - Determinism/reproducibility: 5/5 = pure function of the ledger's own content.
  - Documentation/traceability: 5/5 = `seal.py`'s module docstring and `docs/STATE_MACHINE.md`
    (wherever the manifest schema is documented) both gain a line describing the new field.
- **Now (runbook):**
  1. Write the two test cases using synthetic `calls.jsonl` fixtures (red).
  2. Implement the ledger scan + manifest field in `seal.py`.
  3. `pytest tests/components/readme/bundle/test_seal.py -q` — all green.
  4. Run the real-history check against Aspose.Email Python's actual `calls.jsonl` (read-only,
     scratch script or a one-off `pytest -k` invocation against a copy — never mutate the real
     candidate directory to test this).
  5. `pytest tests/ -q --tb=no` (full suite) — only pre-existing known failures.
  6. Commit, push.

### RC-06 — Extraction-time unit granularity for member-reference lists (high-risk, prototype first)

- **Status:** Not Started — **explicitly flagged as not safe to build under deadline pressure**
  without further prototyping. Requires an owner go/no-go before any code is written.
- **Gap linkage:** RC6
- **Role:** Senior engineer. Drop-in, production-ready — **but only after the prototype gate below
  passes**; this is the one taskcard in this file where "drop-in" does not mean "start now."
- **Scope (only this):**
  - **Fix:** Teach extraction to split a "member reference list" shape (a markdown list whose
    top-level bullets each name one API symbol) into one `inherited_unit` per top-level bullet,
    deterministically, at extraction time — not at reconciliation time. Reconciliation then disposes
    each symbol's own bullet at the grain the decision actually needs (e.g. `SUPERSEDE_REDUNDANT`
    for the four hub classes already covered by the renderer's own detail sections,
    `VERIFIED_PRESERVE` for the remaining ~20 non-hub classes), using **existing** disposition
    vocabulary — no new disposition type required.
  - **Allowed paths:** `src/repository_presenter/components/readme/evidence/facts/inherited.py`,
    `tests/components/readme/evidence/facts/test_formats.py` (or a new
    `tests/components/readme/evidence/facts/test_inherited.py` if the existing file does not already
    cover unit extraction — verify at execution time), and any sealed candidate's `facts.json` that
    re-extraction touches (re-sealed through the existing record-then-adopt path in `seal.py`, not
    hand-edited).
  - **Forbidden:** `reconciliation/dispositions.py`'s disposition vocabulary (no new enum value);
    `placement.py`; `renderer.py` — this fixes the *input grain*, not how later stages consume it.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --facts-only --repo aspose-email-foss/Aspose.Email-FOSS-for-Python`
    shows `inherited_unit:053.list` replaced by multiple per-symbol units (e.g.
    `inherited_unit:053.001`..`.005`) with zero provider calls (facts-only mode makes none).
  - UI/Web/API: N/A.
  - Tests: extraction unit tests proving the split fires only for the specific shape (a list whose
    every top-level bullet starts with a single backtick-quoted identifier matching a known
    `public_symbol` fact) and does not fire for an unrelated bulleted list (a regression/failure
    path guarding against over-eager splitting).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - **Before any implementation:** a written prototype note (add it to this taskcard's own file,
    or a short addendum in `plans/healing/`) checking the shape against at least 2–3 more real
    candidates beyond Aspose.Email Python and Aspose.Cells C++ (both already confirmed to have it).
    This is the prototype gate — do not skip it under time pressure; the 2026-09-08 reassessment
    explicitly named "an untested heuristic under deadline pressure" as the exact mistake this
    project has already made once (R4 item 49) and once declined to repeat.
  - If the gate passes: full file replacement for `inherited.py`'s extraction logic; new tests as
    above.
  - If contracts change: unit-ID renumbering is itself a forward-compatible migration only if every
    consumer (`dispositions.py`, `placement.py`, `content_units.json` slot binding) reads unit IDs
    generically (by string, never by assuming `.list` suffix count) — verify this holds *before*
    counting the gate as passed, not after.
- **Hard rules:** no change to disposition vocabulary (explicit constraint above); every existing
  sealed candidate whose facts change at `EXTRACTING` goes through the existing record-then-adopt
  re-seal path (`seal.py`'s `_record_update`/`_adopt_update`) — never a direct overwrite.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the granularity mismatch (RC6) is closed at its actual source (extraction)
    rather than papered over with a coarser disposition-level workaround.
  - Test coverage: 5/5 = the shape-detection test's failure-path case (does not fire on an unrelated
    list) is as strong as its happy-path case — over-eager splitting is a real regression risk here.
  - No regressions: 5/5 = every sealed candidate without this exact shape shows zero `facts.json`
    change; every one with it goes through record-then-adopt, never a silent overwrite.
  - Determinism/reproducibility: 5/5 = extraction is already deterministic code; the new splitting
    logic must be too (same input tree → same unit IDs, every run).
  - Documentation/traceability: 5/5 = the prototype note itself is the traceability artifact —
    it must exist and be honest about what it did and did not check before code is written.
- **Now (runbook):**
  1. **Stop. Get an explicit owner go/no-go before step 2.** This is the one taskcard in this plan
     where starting without that is itself the risk being flagged.
  2. If approved: identify 2–3 more real candidates with this exact "member-by-member API list"
     shape (start from `tools/reviewer/audit_preserved_api_lists.py`'s existing sweep, which already
     flagged `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`; extend the sweep, do not re-derive it).
  3. Write the prototype note; get it reviewed.
  4. Only then: write the shape-detection tests (happy path + over-eager-splitting regression path).
  5. Implement the extraction split.
  6. `pytest tests/components/readme/evidence/facts/ -q` — all green.
  7. `pytest tests/ -q --tb=no` (full suite) — only pre-existing known failures.
  8. For each affected sealed candidate: `present`, confirm `EXTRACTING`-stage drift recorded as a
     pending update (never auto-applied), then a second identical run to adopt it via zero provider
     calls, exactly as done for `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` on 2026-09-08.
  9. Commit, push.

### RC-07 — Portfolio-wide completeness regression tests in CI (closes the `test_sealed_bytes` blind spot)

- **Status:** Not Started
- **Gap linkage:** SW5
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `test_sealed_bytes.py` only re-renders a candidate's own stored `plan.json`/
    `dispositions.json` — it cannot see a defect baked into those inputs (exactly how three
    candidates sealed with the RC1 links-completeness gap and nothing caught it). Promote
    `tools/reviewer/audit_link_completeness.py` and (once RC-02 lands, giving it a ground truth to
    check against) `tools/reviewer/audit_preserved_api_lists.py` from manual scripts into real,
    CI-gated pytest tests parametrized over every `candidates/*/*/` manifest directory, so a future
    regression is caught automatically, not by another manual archaeology pass.
  - **Allowed paths:** `tests/test_link_completeness.py` (new, or fold into `tests/test_sealed_bytes.py`
    if that reads more naturally as a project convention — decide by matching the existing file's
    parametrization style), `tools/reviewer/audit_link_completeness.py`,
    `tools/reviewer/audit_preserved_api_lists.py` (promote logic out of these into an importable
    function the new test calls, rather than duplicating the sweep logic).
  - **Forbidden:** any `src/` production code — this taskcard only adds regression coverage; if it
    finds a real gap, that gap gets its own taskcard (this file already covers the ones found as of
    2026-09-08 — RC-01 through RC-06), not an inline fix bundled into a test-only change.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A — this is a test-suite addition.
  - UI/Web/API: N/A.
  - Tests: the new test(s) must currently **pass** for every sealed candidate as of the point they
    land (i.e., land this *after* RC-01/RC-02/RC-03 close the currently-known gaps, or the new test
    will immediately fail against real sealed content — which is itself acceptable evidence the
    fixes above are still incomplete, but must be a deliberate, documented outcome, not a surprise).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A — this test reads real `candidates/` content, never a
    fixture standing in for it (the whole point is checking the real, currently-sealed portfolio).
- **Deliverables:**
  - Full file replacement: the new test file; the two audit scripts refactored so their core check
    logic is a plain importable function (`tests/` calls it; the scripts keep a thin CLI wrapper for
    manual/ad hoc use, per `tools/README.md`'s existing convention).
  - New/updated tests: this taskcard's entire deliverable is the new tests themselves.
  - Migration: N/A.
- **Hard rules:** no network (reads only local `candidates/` files); deterministic (same portfolio
  state → same result every run); must not weaken any existing check to make itself pass (if a
  currently-sealed candidate genuinely has the gap, the correct fix is re-sealing it via the normal
  record-then-adopt path, never excluding it from the new test).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = `test_sealed_bytes`'s specific blind spot (verifies self-consistency, not
    ground truth) now has a companion control that checks against ground truth.
  - Test coverage: 5/5 = parametrized over every manifest directory, not a hand-picked subset.
  - No regressions: 5/5 = existing `audit_*.py` scripts keep working standalone for manual use;
    full suite shows only pre-existing known failures once RC-01/02/03 have actually closed the
    gaps this test checks for.
  - Determinism/reproducibility: 5/5 = no LLM calls, no network, no timing sensitivity.
  - Documentation/traceability: 5/5 = `tools/README.md`'s entries for both audit scripts are updated
    to note they are now also exercised as CI tests, not just manual sweeps.
- **Now (runbook):**
  1. Confirm RC-01 and RC-02 (at minimum) have landed and every sealed candidate currently passes
     their corresponding manual audit script with zero findings — if not, fix those candidates
     first via the normal re-seal path; do not land this test against known-red content.
  2. Refactor each audit script's core loop into an importable, parametrizable function.
  3. Write the new pytest file parametrized over `candidates/*/*/`.
  4. `pytest tests/test_link_completeness.py -q` (or wherever it lands) — green against current
     portfolio state.
  5. `pytest tests/ -q --tb=no` (full suite) — only pre-existing known `test_sealed_bytes` failures.
  6. Update `tools/README.md`.
  7. Commit, push.
