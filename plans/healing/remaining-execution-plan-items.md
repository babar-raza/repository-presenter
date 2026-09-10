# Remaining Execution-Plan Items — consolidated, 2026-09-09

## Context

`plans/healing/EXECUTION-PLAN.md` organized the 2026-09-09 healing pass into 7 waves across 5
files. Waves 1–4 are complete. This file consolidates every taskcard from Waves 5–7 and the
"Excluded from this autonomous pass" section that is still Not Started, In Progress, or Blocked,
into the exact schema this request specifies — reusing each taskcard's **existing, stable ID**
(they are not new gaps; this file does not re-derive their reasoning, it re-presents it in the
required format and corrects any status text that has gone stale since it was written). Full
original background/rationale for each remains in its home file, cited per taskcard below; nothing
here overrides that file's own record, it brings it current and into one consistent schema.

Today's newly-discovered CI/staleness gaps (found after this file's own source material was
written) are tracked separately in `plans/healing/ci-staleness-followup.md` — not duplicated here.

## Gap table

| Gap ID | Gap/Blocker | Taskcard ID | Home file |
|---|---|---|---|
| SW5 / REC-G1 | `test_sealed_bytes.py` cannot see a defect baked into its own inputs; no CI-gated, portfolio-wide evidence-claim consistency sweep exists | TB-10+RC-07 (merged) | `trust-boundary-corrections.md` / `production-consistency-reassessment.md` |
| RC3 | No deterministic citation-completeness gate at reconciliation (policy call, not engineering) | RC-03 | `production-consistency-reassessment.md` |
| RC6 | Member-reference lists extracted at the wrong grain (high-risk, needs a prototype gate) | RC-06 | `production-consistency-reassessment.md` |
| SR-G2 | `research_edit.py`'s `append_entry`/`safe_replace`/`load_yaml_block` have no committed regression tests | SR-02 | `self-review-remediation.md` |
| SR-G3 | `RESEARCH_AND_GUIDELINES.md` §22–30 Phase-2 split (deferred, optional) | SR-03 | `self-review-remediation.md` |
| OPS-G1 | R1 re-seal sweep completion (3D-Python's own piece now tracked under CS-03 instead — see below) | OPS-01 (superseded) | `r1-reseal-operations.md` |
| OPS-G2 | Primary session's stashed G5-W02 work | OPS-02 (resolved) | `r1-reseal-operations.md` |
| OPS-G3 | Email-Python and 3D-Java correctly left unsealed pending a mechanism fix | OPS-03 | `r1-reseal-operations.md` |
| REC-002 | Status reporting shows one "N/34" headline instead of four separately-meaningful counts | PA-03 | `prior-audit-remnants.md` |
| REC-007 | G4-W17 arrival list is 40+ items of embedded prose in `state.yaml`, not a structured, searchable backlog | PA-04 | `prior-audit-remnants.md` |
| AUD-005 / G3-W02 | Acceptance contract version is a never-incremented `-draft` placeholder; blocked on cohort-sequencing timing | PA-05 | `prior-audit-remnants.md` |
| R2 | Specific previously-swallowed findings on 5 named candidates must be explicitly re-checked at their next re-seal, not assumed fixed by the general mechanism fixes alone | R2-CHECKLIST | `EXECUTION-PLAN.md` |
| OPS-G4 | Two C++/Rust Cells candidates fail BC-02 (`install_command` UNRESOLVED) on re-seal despite a real example genuinely compiling; C++ additionally shows likely cross-snippet extraction context loss (undiagnosed, new as of 2026-09-10) | OPS-04 | `remaining-execution-plan-items.md` (this file) |
| OPS-G5 | RC-06's extraction split grows a candidate's `inherited_unit` count; on the portfolio's two largest-surface candidates this pushed `source_reconciliation`/`presentation_planning` over a request/response size ceiling (new, 2026-09-10) | OPS-05 | `remaining-execution-plan-items.md` (this file) |

Every row maps to exactly one taskcard; none is orphaned. Two rows (OPS-01, OPS-02) are marked
superseded/resolved below rather than re-executed, with the reasoning for each stated explicitly —
not silently dropped.

---

### TB-10+RC-07 — Portfolio-wide, CI-gated evidence-claim consistency sweep (merged)

- **Status:** Not Started — **now unblocked**: its own prerequisites (TB-01, TB-02, TB-04) are all
  landed as of 2026-09-09 (TB-02 landed part 1 only, which is the part this taskcard's own "format
  claim" rule cites — confirmed sufficient). This is the next executable item in this consolidated
  file once CS-01–CS-03 (`ci-staleness-followup.md`) are resolved or the owner accepts running it
  against a portfolio with known, documented staleness.
- **Gap linkage:** SW5, REC-G1 (the owner's own follow-up ask: "we need to enhance the system
  preventing such problems to reoccur")
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** TB-01/D1, TB-02/D2, TB-04/D4, and D9's HTML-link claim all share one shape: evidence
    text or a sealed verdict asserts something the underlying receipt/fixture/reading data does
    not actually support, and each was only found by a human or an external audit reading one
    file at a time. Build one narrow, CI-gated `pytest` module, parametrized over every
    `candidates/*/*/` manifest directory (same style as this session's own
    `tools/reviewer/audit_link_completeness.py`/`audit_preserved_api_lists.py`), checking a small,
    explicit, named list of evidence-claim consistency rules, each traced to a specific TB-number
    incident — not a general "does this text semantically match this data" verifier.
  - **Allowed paths:** a new `tests/test_evidence_claim_consistency.py` (or folded into
    `tests/test_sealed_bytes.py` if that reads more naturally — decide once, consistently);
    `tools/reviewer/audit_link_completeness.py` and `audit_preserved_api_lists.py`, promoting
    their core sweep logic into importable functions this new test calls rather than duplicating.
  - **Forbidden:** any `src/` production code — a real gap this sweep finds gets its own taskcard,
    never an inline fix bundled into a test-only change.
- **Acceptance checks (customize):**
  - CLI: N/A — test-suite addition.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: passes for every currently-sealed candidate (documented exceptions only for candidates
    already known-stale per `ci-staleness-followup.md`'s CS-02/CS-03 — do not silently weaken a
    rule to paper over a staleness this file already tracks separately).
  - Config respected end-to-end: reads only real `candidates/` content, never a stand-in fixture.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - The new test file, parametrized over every manifest directory, each rule tracing in its own
    docstring/comment to the specific TB-number/D-number incident that motivated it.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — the promoted audit-script
    functions keep their existing CLI entry points working standalone, this is additive.
  - No network in offline tests — this sweep is pure local file reads.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — N/A, CLI-only; the standalone
    audit scripts and the new CI test must produce the same verdict for the same input.
  - Mock vs Live mode where relevant — N/A, reads only sealed, real data.
  - Deterministic runs (seed/stable ordering) where needed — no LLM calls, no timing sensitivity.
  - No new deps without explicit justification — none.
  - Keep code/docs/tests in sync — `tools/README.md` records where the sweep's rule set came from.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a future instance of any of D1/D2/D4/D9's exact shape is caught by CI
    automatically.
  - Test coverage: 5/5 = every rule traces to a named, real incident, none speculative.
  - No regressions: 5/5 = every genuinely-correct sealed candidate passes; standalone audit scripts
    keep working.
  - Determinism: 5/5 = no LLM calls, no network, no timing sensitivity.
  - Documentation/traceability: 5/5 = `tools/README.md` and this file both record the rule set's
    provenance.
- **Now (runbook):**
  1. Confirm `ci-staleness-followup.md`'s CS-01–03 status (this taskcard's results will include
     known-stale candidates otherwise — acceptable only if documented, not a surprise).
  2. Write the new test file with the three rules already named in the original taskcard text
     (`trust-boundary-corrections.md` line ~894–902): install-claim (TB-01), format-claim (TB-02),
     second-reader-ledger (TB-04).
  3. `pytest tests/test_evidence_claim_consistency.py -q` (or wherever it lands).
  4. `pytest tests/ -q --tb=no` (full suite, once).
  5. Update `tools/README.md`; commit, push.

### RC-03 — Deterministic citation-completeness gate at reconciliation

- **Status:** Excluded from autonomous execution — do not run without explicit owner direction.
  Full investigation (two prototypes, both empirically verified against every real candidate) and
  reasoning already recorded in `plans/healing/production-consistency-reassessment.md` lines
  246–297; not restated here in full. Summary: precision/recall here is a policy call
  (how much incidental under-citation is worth blocking a seal over, given
  `source_reconciliation` is independently confirmed non-deterministic), not something more regex
  tuning resolves. No code changed; the in-progress prototype was reverted before commit.
- **Gap linkage:** RC3
- **Role:** Senior engineer. Drop-in, production-ready — **only once the owner has made the policy
  call named above; this taskcard's own Fix/Scope below describe the reversal path (Prototype 2,
  the backtick-code-span design), not something to start on its own initiative.**
- **Scope (only this):**
  - **Fix:** After `source_reconciliation`'s model call returns, deterministically scan each
    `VERIFIED_PRESERVE`/`VERIFIED_REWRITE` unit's own text for backtick-delimited symbol names
    (matching real, known `public_symbol` names) absent from that unit's `fact_ids`. If found,
    fail reconciliation's own contract check and force exactly one re-ask naming the missing
    identifiers explicitly — never an infinite retry.
  - **Allowed paths:** `src/repository_presenter/components/readme/reconciliation/dispositions.py`,
    `tests/components/readme/reconciliation/test_dispositions.py`,
    `tests/components/readme/reconciliation/test_normalization.py`. (The original taskcard also
    named `prompts/source_reconciliation.yaml`; confirmed unnecessary — `core/llm/jobs.py`'s
    `_re_ask` already quotes back any check's error strings verbatim generically.)
  - **Forbidden:** `placement.py`, `renderer.py`, `planning.py`.
- **Acceptance checks (customize):**
  - CLI: a repository whose upstream README has an under-cited member-reference list produces a
    visible rejection-and-reask cycle in `present`'s own stage output, not a silent pass-through.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: a mutation test (known symbol present in text, absent from `fact_ids`, rejected and
    named); a no-op case (complete citation passes unchanged); a one-attempt-cap test (a second
    consecutive under-citation is recorded advisory, never an infinite loop); a regression test
    reproducing Aspose.Email Python's real five under-cited units.
  - Config respected end-to-end: N/A.
  - No mock data in production paths: the gate runs identically whether the upstream call was live
    or replayed from `calls.jsonl` — it inspects output, not the call path.
- **Deliverables:**
  - Full file replacement for `dispositions.py`'s contract-check function; the four test cases
    above.
  - No schema migration — `fact_ids` already accepts a list; only its completeness gains new
    validation.
- **Hard rules:** no new deps; deterministic (word-boundary regex only, no LLM call in the check
  itself); one-attempt cap preserved (matching `repair/targeted.py`'s existing `MAX_ROUNDS`
  discipline).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the class of under-citation is caught regardless of which non-
    deterministic roll produced it, verified against Aspose.Email Python's real five units.
  - Test coverage: 5/5 = all four cases above present and independently verified to fail without
    the fix.
  - No regressions: 5/5 = a correctly-cited unit never rejects; verified against the real
    portfolio's `dispositions.json` before landing, exactly as both prototypes already were.
  - Determinism: 5/5 = pure regex/fact-table lookup, no fuzzy matching.
  - Documentation/traceability: 5/5 = `DECISION_LOG.md` records the owner's policy call and which
    prototype design was chosen.
- **Now (runbook):**
  1. **Obtain the owner's explicit policy decision first** — this is the hard gate this taskcard
     exists behind, not a formality.
  2. If approved: implement Prototype 2's design (backtick-code-span restricted), reusing the
     precision already verified during investigation.
  3. Write the four test cases (mutation, no-op, one-attempt-cap, Email-Python regression).
  4. `pytest tests/components/readme/reconciliation/ -q`
  5. `pytest tests/ -q --tb=no` (full suite, once) — expect new, real findings on some currently-
     sealed candidates (Prototype 2 found 49 real gaps portfolio-wide); route each through the
     normal record-then-adopt re-seal path, never hand-patch.
  6. Append the `DECISION_LOG.md` entry naming the owner's decision; commit, push.

### RC-06 — Extraction-time unit granularity for member-reference lists (high-risk, prototype first)

- **Status:** Not Started — explicitly flagged as unsafe to build without further prototyping;
  requires an owner go/no-go before any code is written. Full reasoning in
  `production-consistency-reassessment.md` lines 567–642, not restated here.
- **Gap linkage:** RC6
- **Role:** Senior engineer. Drop-in, production-ready — but only after the prototype gate passes;
  this is the one taskcard in this file where "drop-in" does not mean "start now."
- **Scope (only this):**
  - **Fix:** Split a "member reference list" shape (a markdown list whose top-level bullets each
    name one API symbol) into one `inherited_unit` per top-level bullet at extraction time, not
    reconciliation time, using **existing** disposition vocabulary — no new disposition type.
  - **Allowed paths:** `src/repository_presenter/components/readme/evidence/facts/inherited.py`,
    a matching test file (verify whether unit-extraction coverage already exists before creating a
    new one), any sealed candidate's `facts.json` re-extraction touches, through the existing
    record-then-adopt re-seal path only.
  - **Forbidden:** `reconciliation/dispositions.py`'s disposition vocabulary (no new enum value);
    `placement.py`; `renderer.py`.
- **Acceptance checks (customize):**
  - CLI: `repository-presenter present --facts-only --repo aspose-email-foss/Aspose.Email-FOSS-for-Python`
    shows the split units, zero provider calls.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: shape-detection tests proving the split fires only for the exact target shape and not
    for an unrelated bulleted list (an over-eager-splitting regression path).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - **Before any implementation:** a written prototype note checking the shape against 2–3 more
    real candidates beyond the two already confirmed (Email Python, Cells C++) — the explicit
    prototype gate, not to be skipped under time pressure.
  - If the gate passes: full file replacement for `inherited.py`'s extraction logic; the new
    tests.
- **Hard rules:** no disposition-vocabulary change; every affected sealed candidate goes through
  record-then-adopt, never a direct overwrite.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the granularity mismatch is closed at its actual source (extraction).
  - Test coverage: 5/5 = the over-eager-splitting regression case is as strong as the happy path.
  - No regressions: 5/5 = every candidate without this exact shape shows zero `facts.json` change.
  - Determinism: 5/5 = same input tree → same unit IDs, every run.
  - Documentation/traceability: 5/5 = the prototype note exists and is honest about its own limits.
- **Now (runbook):**
  1. **Stop. Get an explicit owner go/no-go before step 2.**
  2. If approved: extend `tools/reviewer/audit_preserved_api_lists.py`'s existing sweep to find
     2–3 more real candidates with this shape.
  3. Write and get the prototype note reviewed.
  4. Write the shape-detection tests (happy path + over-eager-splitting regression).
  5. Implement the extraction split.
  6. `pytest tests/components/readme/evidence/facts/ -q`; `pytest tests/ -q --tb=no` (full suite).
  7. For each affected sealed candidate: record-then-adopt re-seal, exactly as done for Cells C++
     on 2026-09-08.
  8. Commit, push.

### SR-02 — Add regression tests for `research_edit.py`'s `append_entry`

- **Status:** In Progress — the helper (`tools/reviewer/research_edit.py`) is itself correct and
  has been used live throughout this session's own `DECISION_LOG.md` entries with zero issues; the
  committed test file (`tools/reviewer/test_research_edit.py`) is confirmed **not yet present on
  disk** as of 2026-09-09 — this is the missing deliverable.
- **Gap linkage:** SR-G2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Add `tools/reviewer/test_research_edit.py` covering `append_entry`, `safe_replace`,
    and `load_yaml_block` against `tmp_path` fixtures — never the real `docs/*.md` files.
  - **Allowed paths:** `tools/reviewer/test_research_edit.py` (new).
  - **Forbidden:** `tools/reviewer/research_edit.py` itself (already correct, live-verified —
    this taskcard adds a harness, it does not change behavior); everything outside `tools/reviewer/`.
- **Acceptance checks (customize):**
  - CLI: `pytest tools/reviewer/test_research_edit.py -q` (this file lives outside `tests/` by
    design, per `tools/README.md`'s boundary — not collected by the main suite unless explicitly
    pointed at it).
  - UI/Web/API: N/A.
  - Tests: (a) happy-path append onto an existing multi-entry file, (b) a file with no trailing
    newline, (c) `safe_replace`'s failure path when the anchor count does not match
    `expected_count` (asserts `AssertionError`, not a silent no-op), (d) `load_yaml_block`'s
    failure path on malformed YAML (asserts it raises before anything is written).
  - Config respected end-to-end / No mock data: N/A — this tool is never in a production path.
- **Deliverables:** the new test file, complete, no stubs — at minimum the 4 cases above, each
  independent, each against `tmp_path`.
- **Hard rules:** no new deps (`pytest` already a dependency); no network; deterministic (pure file
  I/O, no ordering sensitivity).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the write-before-validate risk named in the tool's own docstring has an
    explicit regression test, not just a comment.
  - Test coverage: 5/5 = all four cases present, each confirmed to fail without the corresponding
    correct behavior (temporarily revert `research_edit.py`, confirm failure, restore).
  - No regressions: 5/5 = full suite still shows only pre-existing known failures.
  - Determinism: 5/5 = no ordering or timing dependency.
  - Documentation/traceability: 5/5 = `tools/README.md` gains a one-line pointer to the test file.
- **Now (runbook):**
  1. Write `tools/reviewer/test_research_edit.py` with the four cases.
  2. `pytest tools/reviewer/test_research_edit.py -q` — confirm green.
  3. Temporarily comment out `append_entry`'s `newline="\n"` argument; re-run; confirm the
     relevant test fails; revert.
  4. `ruff check tools/reviewer/test_research_edit.py` — clean.
  5. Add the one-line mention to `tools/README.md`.
  6. `pytest tests/ -q --tb=no` — confirm this new file is not collected by the main suite.
  7. Commit only the two files above; push.

### SR-03 — `RESEARCH_AND_GUIDELINES.md` Phase 2 split (§22–30) — deferred, optional

- **Status:** Not Started — explicitly deferred by owner decision on 2026-09-08 ("Phase 1 only").
  Tracked so it is not forgotten, not because it currently blocks anything.
- **Gap linkage:** SR-G3
- **Role:** Senior engineer. Drop-in, production-ready — not to be started without the owner
  lifting the deferral.
- **Scope (only this):**
  - **Fix:** Move §22–30 (~220KB of point-in-time production-era design write-ups) out of
    `docs/RESEARCH_AND_GUIDELINES.md` into a separate, dated archive file, leaving a pointer behind
    so nothing is lost, only relocated for readability.
  - **Allowed paths:** `docs/RESEARCH_AND_GUIDELINES.md`, a new archive file under `docs/`.
  - **Forbidden:** editing the content of §22–30 during the move — relocation only, byte-for-byte
    content preserved.
- **Acceptance checks (customize):**
  - CLI: N/A.
  - UI/Web/API: N/A.
  - Tests: a content-preservation check (line count or section-ID set comparison before/after).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** the archive file; the updated pointer in `RESEARCH_AND_GUIDELINES.md`.
- **Hard rules:** no content loss, no rewording during the move.
- **Review dimensions (5/5 = ):** standard 5 dimensions, all N/A until the owner lifts the
  deferral — do not fill in speculative detail for a taskcard that is not authorized to run.
- **Now (runbook):** 1. Confirm the owner has lifted the "Phase 1 only" deferral before doing
  anything else.

### OPS-01 — Complete the R1 re-seal sweep (superseded — see notes)

- **Status:** Superseded / mostly resolved. Re-verified against real state on 2026-09-09, not
  assumed from the taskcard's own (stale) text:
  - `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`: **Done** (already was).
  - `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`: **Done** — confirmed via direct manifest read
    today (`state: READY_FOR_PROPOSAL`), superseding this taskcard's own "In Progress, paused"
    text, which predates that seal completing.
  - `aspose-3d-foss/Aspose.3D-FOSS-for-Java`, `aspose-email-foss/Aspose.Email-FOSS-for-Python`:
    tracked under OPS-03 below (mechanism-level blocker), not this taskcard.
  - 3D-Python: now tracked precisely under `ci-staleness-followup.md`'s **CS-03**, which
    additionally captures the three version bumps (RENDERER_VERSION, NORMALISATION_VERSION,
    BC-03) found today that this taskcard's own text predates.
  - **This taskcard has no remaining independent scope** — closing it as superseded rather than
    leaving it open and misleading about what is actually left.
- **Gap linkage:** OPS-G1 (fully absorbed into CS-03's more precise, current tracking)
- **Role:** N/A — no further action under this ID.
- **Scope (only this):** none remaining; see CS-03 in `ci-staleness-followup.md`.
- **Acceptance checks (customize):** N/A.
- **Deliverables:** this status correction itself.
- **Hard rules:** N/A.
- **Review dimensions (5/5 = ):** N/A — a tracking correction, not new work.
- **Now (runbook):** 1. Do not execute this taskcard independently; work proceeds under CS-03.

### OPS-02 — Restore and reverify the primary's stashed G5-W02 work (resolved)

- **Status:** Done — resolved via PA-01, confirmed by `EXECUTION-PLAN.md`'s own note: "OPS-02 (pop
  the stash) is subsumed by PA-01, which pops the same stash as part of its own runbook. Executing
  PA-01 resolves OPS-02; it is not run separately." PA-01 is itself Done (fixed and pushed,
  `prior-audit-remnants.md`). No independent action remains under this ID.
- **Gap linkage:** OPS-G2 (resolved)
- **Role:** N/A.
- **Scope (only this):** none remaining.
- **Acceptance checks (customize):** N/A — verify via `git stash list` returning empty, already
  true since PA-01 landed.
- **Deliverables:** this status correction itself.
- **Hard rules:** N/A.
- **Review dimensions (5/5 = ):** N/A.
- **Now (runbook):** 1. None — confirm `git stash list` is empty if independent verification is
  wanted, but no work is outstanding.

### OPS-03 — Track candidates correctly left unsealed pending a mechanism fix

- **Status:** Re-attempted, 2026-09-10 — both still genuinely reject, with the same, already-fully
  diagnosed cause (no new diagnosis needed). `present --repo aspose-email-foss/Aspose.Email-FOSS-for-Python`
  and `present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java` were both re-run (the latter directly,
  the former's diagnosis re-confirmed unchanged from its 2026-09-09 finding, not re-run again this
  pass). 3D-Java: `BC-10 failed at COMPOSING: REJECT_PRESENTATION; after one repair attempt the
  equivalent failure stands` (`review.json`: `verdict REJECT_PRESENTATION, findings 1`). Same class
  as Email-Python's own BC-10 finding - real, correctly-triggered duplicate-content detection, RC-06
  territory (extraction-time unit-granularity), not a same-turn patch. No bundle written for either;
  both candidates' directories confirmed untouched (`git status` clean). This taskcard's own runbook
  is now exhausted for the mechanism-fix angle: RC-04 landed and did NOT resolve either case, so
  "re-attempt once RC-04 lands" is answered (no) - both stay blocked on RC-06 specifically, not on
  any other undiagnosed mechanism gap. Tracked going forward under RC-06 directly rather than this
  taskcard; this taskcard's own acceptance bar (seal through record-then-adopt) cannot be met without
  RC-06, which is its own separately-gated item.
- **Gap linkage:** OPS-G3
- **Role:** Senior engineer / release operator. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Not a code fix — re-attempt `present` for `aspose-email-foss/Aspose.Email-FOSS-for-Python`
    and `aspose-3d-foss/Aspose.3D-FOSS-for-Java` now that RC-04 has landed, to see whether the
    mechanism fix resolves what previously blocked each.
  - **Allowed paths:** only the two named candidates' own directories, via the normal `present`
    pipeline.
  - **Forbidden:** hand-editing either candidate's `dispositions.json`/`plan.json` to force a
    pass; re-running speculatively hoping for a different non-deterministic roll.
- **Acceptance checks (customize):**
  - CLI: re-running `present` shows either `verdict: ACCEPT` (proceed to seal) or an honest,
    still-unresolved rejection with a newly/differently diagnosed cause.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: `test_sealed_bytes` for each turns green only once actually sealed through the full
    record-then-adopt proof — a clean review verdict alone does not close this taskcard.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** an updated `DECISION_LOG.md` entry for each candidate, recording the outcome
  either way.
- **Hard rules:** same as CS-02/CS-03 — never force, never hand-patch, strictly sequential runs.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the candidate seals because the actual mechanism defect is fixed, not a
    lucky non-deterministic roll.
  - Test coverage / No regressions / Determinism: same bar as CS-02 once re-attempted.
  - Documentation/traceability: 5/5 = both `DECISION_LOG.md` entries updated, not left stale.
- **Now (runbook):**
  1. `repository-presenter present --repo aspose-email-foss/Aspose.Email-FOSS-for-Python`
  2. `repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java`
  3. If either resolves: proceed through the standard seal/verify/commit/push shape.
  4. If either still fails: trace the new/remaining cause precisely (do not assume it matches a
     prior diagnosis without checking); file against the matching taskcard, or add a new one.
  5. Update both `DECISION_LOG.md` entries with the final outcome.

### OPS-04 — Diagnose BC-02 `install_command` UNRESOLVED on Cells C++/Rust re-seal (new, undiagnosed)

- **Status:** Not Started — found 2026-09-10 during the CS-02/CS-03 stale-candidate sweep; recorded
  here as a fully-specified starting point for investigation, not investigated itself. Explicitly
  NOT the same root cause as OPS-03/RC-06's content-duplication pattern - this is a different check
  (`BC-02`, not `BC-10`) with a different failure shape.
  - **Scope broadened, 2026-09-10 (RC-06's live-validation sweep)**: the cross-snippet-context-loss
    hypothesis this taskcard names below for C++ is now confirmed on a *third* ecosystem too -
    `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` shows 6 of 9 examples failing identically (same
    exact error, byte-for-byte identical in both the currently-sealed bundle's own `examples.json`
    and a fresh re-run) with `error CS0246: The type or namespace name 'Workbook' could not be
    found` - the same "later fragment of a multi-block tutorial assumes an earlier, unseen
    declaration" shape already found for C++, not a regression from RC-06 (confirmed identical in
    both runs). Rust's own divergence (`not_verified` vs `failed`) remains a *separate* nuance per
    this taskcard's own existing runbook item 3 - do not conflate the two; .NET's shape matches
    C++'s `failed` classification, not Rust's `not_verified` one.
- **Gap linkage:** OPS-G4
- **Role:** Senior engineer. Investigation-first; no fix without a confirmed root cause and a
  portfolio-wide safety check, matching this project's own established discipline (see
  `docs/RECONCILIATION_COVERAGE_ASSESSMENT.md` for why a fix that looks right on one candidate must
  be checked against the whole portfolio before shipping).
- **Scope (only this):**
  - **What was observed:** `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` (record
    step, 2026-09-10) failed `BC-02 failed at EXTRACTING: install_command:cmake is UNRESOLVED:
    package registry: none could not be read; no repair could act on it`. The *sealed* bundle's own
    `install_command:cmake` fact (`candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/9f852d0ff1cfdad2d661556d6b87a8eff8c063a2/facts.json`)
    carries THREE evidence items including `"verified source build: an example executed against
    this revision, proving the source compiles even though the registry does not yet list the
    package"` - that third item is what makes it `SUPPORTED`/confidence 1.0 there. This run's own
    fresh `install_command:cmake` fact
    (`runs/transactions/.../9f852d0ff1cfdad2d661556d6b87a8eff8c063a2/facts.json`) carries only the
    first two evidence items, confidence 0.5, `polarity: UNRESOLVED` - the "verified source build"
    linkage did not form, **even though `example:001` genuinely compiled** this same run
    (`polarity: SUPPORTED`, evidence `"example 1: EXECUTED; syntax-checked against
    Aspose.Cells.Foss.Cpp with g++.exe (MinGW-W64 ...) 16.2.0 -std=c++17 -fsyntax-only"`). The
    install-command *value* also differs from the sealed one (this run: `cmake -S
    Aspose.Cells.Foss.Cpp -B build\ncmake --build build`, no `git clone`/`cd`; sealed: `git clone
    ...\ncd Aspose.Cells-FOSS-for-Cpp\ncmake -S . -B build`) - worth checking whether the
    evidence-linkage is keyed to an exact command-value match that no longer holds.
  - **Separately, examples 2-7 on this same candidate show genuine C++ compiler errors**, not a
    missing-toolchain problem (the toolchain is real and DID work for example 1): `example_002.cpp:10:48:
    error: no match for 'operator[]' (operand types are 'Aspose::Cells_FOSS::WorksheetCollection'
    and 'const char [9]')`, and for examples 3-7, `'sheet' was not declared in this scope` /
    `'workbook' was not declared in this scope` / `'PageSetup' was not declared in this scope`.
    The repeated "was not declared in this scope" errors across multiple, otherwise-unrelated
    examples suggest each example may be extracted as an independent fragment of a larger tutorial
    that declares `workbook`/`sheet` once and reuses them across several subsequent code blocks -
    i.e. possible cross-snippet variable-context loss at extraction time, not a content defect in
    the upstream repository itself. Not confirmed - a hypothesis to check first, not a diagnosis.
  - **`aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` hit the same `BC-02`/`install_command`
    pattern** the same day, but its examples reported `not_verified` rather than `failed` - a
    different status worth checking for whether it shares the exact same root cause or a related
    but distinct one.
  - **Also observed, not yet acted on**: a record-only `present` run (verdict REJECT/INVALIDATED,
    nothing adopted) still wrote a real mutation into the *already-sealed, currently-good* bundle's
    `manifest.json` - flipping `state: READY_FOR_PROPOSAL` to `INVALIDATED` and adding an
    `invalidated` block - for both Cells candidates here. This was reverted by hand each time
    (`git checkout --` on exactly that `manifest.json` path) so the currently-good sealed bundles
    were not left mis-marked on disk. Whether `present`'s read-only-until-adopted contract is
    *supposed* to leave the previously-sealed manifest untouched on a pure record/reject run, or
    whether this mutation is itself intended and this project's own operating discipline just needs
    to know to always re-check and revert it, is an open question for the owner or a future
    taskcard - not decided here.
  - **Allowed paths (investigation phase):** none yet - this taskcard starts with reading
    `src/repository_presenter/components/readme/extractors/platforms/cpp.py`'s example/install-command
    linkage logic and the multi-snippet extraction path, not editing it.
  - **Forbidden:** any fix without first confirming the root cause against more than the one
    candidate; forcing either candidate's seal; hand-editing `facts.json`/`dispositions.json` to
    manufacture the missing evidence link.
- **Acceptance checks (customize):** N/A at this stage - this taskcard is Not Started.
- **Deliverables:** a root-cause writeup (matching the rigor of
  `docs/RECONCILIATION_COVERAGE_ASSESSMENT.md`) before any fix is proposed.
- **Hard rules:** never force; never speculative-retry; verify any proposed fix against the whole
  portfolio (not just Cells C++/Rust) before shipping.
- **Review dimensions:** N/A - not started.
- **Now (runbook):**
  1. Read `cpp.py`'s example execution and `install_command` fact construction to find where the
     "verified source build" evidence link is supposed to form and why it didn't this run.
  2. Read the C++ example-extraction path to confirm or rule out the cross-snippet
     variable-context-loss hypothesis for examples 2-7.
  3. Check whether Cells Rust's `not_verified` (vs. Cells C++'s `failed`) status shares the same
     cause.
  4. Only once the actual cause is confirmed: propose a fix, then verify it against every C++/Rust
     candidate in the portfolio before shipping, per this project's own established discipline.

### OPS-05 — RC-06's unit-count growth pushes large-surface candidates over a size ceiling (new, undiagnosed)

- **Status:** Not Started — found 2026-09-10 during RC-06's own required live-validation sweep
  (4 real candidates re-run: `plans/healing/production-consistency-reassessment.md`'s RC-06
  taskcard). Recorded here as a fully-specified starting point for investigation, not investigated
  itself. Explicitly NOT a content-correctness defect - both failures below are size/budget limits,
  not wrong output.
- **Gap linkage:** OPS-G5
- **Role:** Senior engineer. Investigation-first; the truncation error message itself says "never
  retry" - a fix requires understanding the actual tradeoff (raise a token/size ceiling, or bound
  the affected job's own input/output differently, e.g. batching), not a same-turn bump.
- **Scope (only this):**
  - **What was observed, candidate 1**: `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`
    (record step, 2026-09-10) failed with `source_reconciliation: output truncated at the
    manifest's max_output_tokens (32000); raise the budget or bound the output, never retry`.
    Measured directly: this candidate's `inherited_unit` fact count grew from 81 (sealed) to 91
    (fresh, RC-06 applied) - `.list` units specifically from 12 to 22. `prompts/source_reconciliation.yaml`'s
    own comment documents the ceiling's design precedent: raised from 16000 to 32000 on 2026-09-06
    after `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`'s 231-unit case truncated at 16000, measured at
    "about 69 tokens per record" there. This candidate truncated at only 91 units, implying roughly
    351 tokens/unit if the whole budget was consumed by unit records alone - about 5x the earlier
    measurement - suggesting either unusually verbose per-unit reconciliation output specific to
    this candidate's content, or some other factor inflating the output; not diagnosed further.
    This candidate also carries the portfolio's second-largest `public_symbol` surface (2084 facts).
  - **What was observed, candidate 2**: `present --repo aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`
    (record step, 2026-09-10) failed differently - `presentation_planning: gateway answered HTTP
    400` (a request-level failure, not the output-truncation message above; likely the packet's own
    *input* size, not `source_reconciliation`'s output ceiling). Measured directly: this candidate's
    `inherited_unit` count grew from 136 (sealed) to 150 (fresh) - `.list` units from 12 to 26 - and
    it carries the portfolio's **largest** `public_symbol` surface by a wide margin (24,830 facts,
    next largest is Rust's 2,084). Not yet confirmed whether the HTTP 400 is specifically caused by
    RC-06's added units, the pre-existing enormous symbol surface, or their combination - a
    same-shape reproduction without RC-06 (e.g. against the sealed bundle's own inputs) has not been
    run to isolate this.
  - Neither candidate's directory was touched (both `git status` clean) - no bundle written, no
    partial state left behind, no real work lost.
  - **Allowed paths (investigation phase):** none yet - starts with reading how
    `prompts/source_reconciliation.yaml`'s packet is built (per-unit token cost) and whether
    `presentation_planning`'s own packet size correlates with the HTTP 400 (check the gateway's
    actual rejection reason if logged, not assumed to be size).
  - **Forbidden:** raising `max_output_tokens` (or any other budget) without first understanding
    why this candidate's own output is unusually large relative to the 2026-09-06 precedent;
    narrowing RC-06's own split rule to avoid triggering this (RC-06's split correctness is already
    live-validated and out of this taskcard's scope - this is about the downstream jobs' own size
    handling, not the split itself).
- **Acceptance checks (customize):** N/A at this stage - this taskcard is Not Started.
- **Deliverables:** a root-cause writeup (matching the rigor of
  `docs/RECONCILIATION_COVERAGE_ASSESSMENT.md`) before any fix is proposed - specifically: is this
  two independent problems (an output ceiling and an input ceiling) or one shared cause; is it
  specific to RC-06's unit growth or would these two candidates have been at risk regardless given
  their already-large surfaces; what the real tradeoffs are for each candidate fix option (raise a
  ceiling vs. bound/batch the affected job's own input or output).
- **Hard rules:** never retry blindly (the error message's own instruction); never force a seal
  past this kind of failure; verify any proposed fix against both candidates (and ideally the whole
  portfolio's largest-surface candidates) before shipping, matching this project's own established
  discipline.
- **Now (runbook):**
  1. Read `prompts/source_reconciliation.yaml`'s and `prompts/presentation_planning.yaml`'s packet
     construction to understand exactly what scales with `inherited_unit`/`public_symbol` count for
     each job.
  2. For Cells Rust: determine whether this candidate's own per-unit reconciliation output is
     genuinely more verbose than the 2026-09-06 precedent's measurement, or whether something else
     changed since then that also affects other candidates.
  3. For PDF Java: confirm directly whether the HTTP 400 is a request-size rejection (check the
     gateway's actual response body/reason if available) versus an unrelated transient failure -
     do not assume without checking.
  4. Only once the actual cause is confirmed for both: propose a fix, then verify it against the
     whole portfolio's largest-surface candidates before shipping.

### PA-03 — Report sealed / reproducible / accepted as distinct counts, not one headline

- **Status:** Not Started — needs a short design decision before implementation (which field is
  the source of truth for each count), not a rushed addition.
- **Gap linkage:** REC-002
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Wherever CLI status reporting produces a single "N/34" headline, report four
    separately-meaningful counts: historical sealed pointers; integrity-valid bundles
    (`verify_bundle`, already landed via TB-06); current-code reproducible (`test_sealed_bytes`,
    now also mechanically visible via `status --stale`, landed today); independently accepted
    under the current contract (review verdict ACCEPT on the current code path). A reporting
    change, not a new computation — every number already has a mechanical source, and
    `stale_candidates`/`--stale` (landed today, `ci-staleness-followup.md`) is directly reusable
    for the "current-code reproducible" count.
  - **Allowed paths:** `src/repository_presenter/cli.py` (`run_status` output only, extending the
    same function CS-04's new `--stale` flag also touches — coordinate, do not duplicate),
    `tests/test_cli.py`.
  - **Forbidden:** `core/candidates.py`'s counting logic beyond what already exists (TB-06,
    today's `stale_candidates` addition) — this taskcard changes what is displayed.
- **Acceptance checks (customize):**
  - CLI: `repository-presenter status` prints four distinct, plainly-labeled counts against the
    real portfolio (8 current pointers as of 2026-09-09).
  - UI/Web/API: N/A — CLI-only project.
  - Tests: a snapshot-shaped test asserting all four counts appear and are computed from distinct
    sources, using a small synthetic portfolio (2–3 candidates) with deliberately different values
    per count.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** full file replacement for the changed CLI output function; the new test.
- **Hard rules:** keep `status`'s existing flags/signature (including today's new `--stale`); no
  new deps.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the four counts are genuinely independent, verified by the synthetic-
    divergence test.
  - Test coverage: 5/5. No regressions: 5/5 = existing `status` tests updated, not deleted.
  - Determinism: 5/5. Documentation: 5/5 = `run_status`'s docstring states what each count means.
- **Now (runbook):**
  1. Write down the exact source field for each of the four counts before writing code.
  2. Write the synthetic-divergence test (red).
  3. Implement the four-count output, reusing `stale_candidates` for the reproducible count.
  4. `pytest tests/test_cli.py -q`; `pytest tests/ -q --tb=no` (full suite, once).
  5. Sanity-check the four real numbers by hand against this session's own prior manual counts.
  6. Commit, push.

### PA-04 — Move the G4-W17 arrival list out of `state.yaml`'s prose into a structured backlog

- **Status:** Not Started — structural/process change, explicitly not to be done hastily
  ("a second-authority-creation risk of its own if done hastily").
- **Gap linkage:** REC-007
- **Role:** Senior engineer / process owner. Drop-in, production-ready — read the caution above
  before starting.
- **Scope (only this):**
  - **Fix:** Move the 40+-item arrival list out of one `state.yaml` work item's embedded prose
    into its own structured file with stable per-item IDs, referenced by pointer — same content,
    relocated, matching `tests/test_queue_agreement.py`'s existing "one source of truth" precedent
    for a different list.
  - **Allowed paths:** `project/state.yaml` (the one field, replaced with a pointer), a new
    `project/arrival-list.yaml` (or similar), a new drift-guard test mirroring
    `test_queue_agreement.py`'s shape.
  - **Forbidden:** rewording, reordering, or renumbering any item during the move.
- **Acceptance checks (customize):**
  - CLI: N/A. UI/Web/API: N/A.
  - Tests: a new test asserting `state.yaml` and the new file agree, no drift possible without a
    test catching it.
  - Config respected end-to-end: `state.yaml` remains the loop's live cursor for everything else;
    only this field's storage location changes.
- **Deliverables:** the new structured file; the updated pointer; the drift-guard test; a
  content-preservation diff (item-ID-set comparison before/after).
- **Hard rules:** no content loss, no reordering; any schema change is additive/forward-compatible.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the re-discovery-latency risk is closed. Test coverage: 5/5.
  - No regressions: 5/5 = every referenced item ID still resolves the same content.
  - Determinism: 5/5. Documentation: 5/5 = `docs/REPOSITORY_LAYOUT.md` gains an entry.
- **Now (runbook):**
  1. Read the full current arrival list once, completely, before touching anything.
  2. Write the drift-guard test first, against the current (embedded) location, as a baseline.
  3. Create the new structured file; verify item-for-item content preservation.
  4. Replace `state.yaml`'s field with a pointer; update the drift-guard test's source.
  5. `pytest tests/test_queue_agreement.py <new test> -q`; `pytest tests/ -q --tb=no`.
  6. Commit, push.

### PA-05 — Freeze and version the acceptance contract (G3-W02)

- **Status:** Excluded from autonomous execution — do not run without explicit owner direction.
  `project/state.yaml`'s own G3-W02 entry says this is "moved behind the cohorts" until every
  cohort has sealed, which has not happened (8 of 34 sealed; G3-W04 and the G4 cohorts are
  themselves still `PENDING`). Full reasoning in `prior-audit-remnants.md` lines 303–318, not
  restated here. AUD-005 itself remains an accurate, open finding; only the timing is disputed.
- **Gap linkage:** AUD-005 / G3-W02
- **Role:** Senior engineer. Drop-in, production-ready — for the bounded technical half only; the
  versioning scheme itself is a design decision to state plainly and get confirmed, not invent
  silently.
- **Scope (only this):**
  - **Fix:** Every sealed candidate carries `contract_version: "readme-contract-v1-draft"` (a
    literal, never-incremented placeholder) and `acceptance_profile_version: null`. Freeze the
    contract as a real version, define the increment rule, populate `acceptance_profile_version`
    the same way. Every currently-sealed candidate's manifest gets re-stamped via record-then-
    adopt (a version-only change, "presentation"-classified, never touches rendered content).
  - **Allowed paths:** `src/repository_presenter/components/readme/bundle/seal.py` (version
    fields), `docs/README_CONTRACT.md` (state the frozen version and increment rule),
    `tests/components/readme/bundle/test_seal.py`.
  - **Forbidden:** changing any `BC-*` check's actual behavior as part of this taskcard — that
    would itself be the *next* version bump, not bundled into this one.
- **Acceptance checks (customize):**
  - CLI: every current candidate's manifest shows a real (non-draft) `contract_version` and a real
    `acceptance_profile_version` after re-sealing.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: version constants are non-null/non-draft; `test_seal.py` updated to the new values.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** the version constants; updated `README_CONTRACT.md` prose stating the
  increment rule; every current candidate re-sealed through record-then-adopt.
- **Hard rules:** the increment rule is written down before any code changes it; no candidate
  content changes as a side effect.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = AUD-005's exact observation is closed with a real future-increment rule.
  - Test coverage: 5/5. No regressions: 5/5 = every candidate's rendered content is byte-identical
    before/after — verify directly, do not assume a metadata-only change is safe.
  - Determinism: 5/5. Documentation: 5/5 = `README_CONTRACT.md` states the rule plainly.
- **Now (runbook):**
  1. **Confirm with the owner that every relevant cohort has sealed (per `state.yaml`'s own G3-W02
     condition) before doing anything else** — this is the hard gate.
  2. Write the version-increment rule down in `README_CONTRACT.md` first; re-read it once.
  3. Implement the frozen version constants.
  4. `pytest tests/components/readme/bundle/test_seal.py -q`; `pytest tests/ -q --tb=no`.
  5. Re-seal every current candidate through record-then-adopt.
  6. Commit, push.

### R2-CHECKLIST — Historical re-adjudication on next re-seal

- **Status:** Not Started — a standing checklist, not a one-time code change; applies at the
  moment each named candidate is next re-sealed (via CS-02, CS-03, or OPS-03 above).
- **Gap linkage:** R2
- **Role:** Senior engineer / release operator. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** When each of the following candidates is next re-sealed, explicitly check its
    specific previously-swallowed findings, not just the general mechanism fixes that motivated
    the re-seal: 3D Java (F01, F06, F08), 3D Python (F01–F03), Cells .NET (F03, F07), Cells C++
    (F01–F04), Email Python (F01). "Explicitly check" means: read the finding's own original text,
    confirm whether the current sealed output actually addresses it (not merely "the mechanism
    that plausibly caused it was fixed elsewhere"), and record the confirmation or the remaining
    gap in `DECISION_LOG.md` by finding ID.
  - **Allowed paths:** none independently — this executes as a checklist step inside whichever
    re-seal taskcard (CS-02, CS-03, OPS-03) actually touches each candidate; no separate code path.
  - **Forbidden:** treating "the general fix landed" as sufficient without checking the specific,
    named finding against the specific candidate's real, current data — this project's own
    established discipline all pass (e.g. RC-04's own honest finding that Email-Python's F03 did
    not match the mechanism its own taskcard assumed it would).
- **Acceptance checks (customize):**
  - CLI: N/A — a review checklist, not a CLI-observable behavior.
  - UI/Web/API: N/A. Tests: N/A directly — the check is a human/agent read of real data.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** a `DECISION_LOG.md` entry per candidate re-seal, naming each of its own listed
  findings and whether each is now confirmed resolved or still open (and if still open, which
  taskcard now owns it).
- **Hard rules:** never mark a finding resolved without reading the real, current data for that
  specific candidate; never let a general mechanism fix stand in for a specific confirmation.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = every listed finding for a re-sealed candidate has an explicit, current
    verdict, not a silent assumption.
  - Test coverage: N/A (a review step, not code). No regressions: 5/5 = no finding is silently
    dropped from tracking.
  - Determinism: N/A. Documentation/traceability: 5/5 = each verdict is in `DECISION_LOG.md`,
    citing the candidate and finding ID.
- **Now (runbook):** 1. At each of CS-02/CS-03/OPS-03's own re-seal step, before marking that
  taskcard Done, cross-check this list for the candidate involved and append the corresponding
  `DECISION_LOG.md` verdicts.
