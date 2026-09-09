# CI and Staleness Follow-Up — 2026-09-09

## Context

Triggered by the owner flagging CI as red mid-pass on 2026-09-09, which led to a full
production-grade reassessment (`docs/CI_AND_STALENESS_ASSESSMENT.md`) informed directly by the
`foss-readme-optimizer` post-mortem (0/32 candidates ever sealed in 46 days — "validation
thoroughness did not trade off against shipping, it substituted for it"). That reassessment's own
safe, non-spiral fixes (lint/format/mypy corrections, a CI-workflow visibility fix, three
retroactively-corrected version-bump misses, and a new `stale_candidates`/`status --stale` report)
have already landed and been pushed. Running the fixed CI workflow for real for the first time then
surfaced additional, previously-invisible findings that this file turns into taskcards.

Every taskcard below is either a **reporting/visibility fix** or a **process-discipline fix** — none
adds a new blocking check, new acceptance criterion, or new class of rejection over candidate
content, per `docs/CI_AND_STALENESS_ASSESSMENT.md` section 5 ("What NOT to build") and the owner's
explicit instruction to avoid the validator-spiral failure mode `foss-readme-optimizer` fell into.

This file is scoped to gaps discovered or confirmed **today** (2026-09-09, after
`docs/CI_AND_STALENESS_ASSESSMENT.md` was written). Gaps already tracked as their own taskcards
before today (TB-10, RC-03, RC-06, RC-07, SR-02, SR-03, OPS-01, OPS-02, OPS-03, PA-03, PA-04, PA-05)
are consolidated, in the exact schema this file uses, in
`plans/healing/remaining-execution-plan-items.md` — not duplicated here.

## Gap table

| Gap ID | Gap/Blocker | Taskcard ID |
|---|---|---|
| G1 | Held, uncommitted 3D-Python candidate WIP masks local test runs across ≥3 test files | CS-01 |
| G2 | Cells .NET and Email-Python's sealed bytes are stale relative to already-landed, desirable renderer fixes (RC-02) | CS-02 |
| G3 | 3D-Python (the canary)'s sealed bytes are stale relative to three landed version bumps, and its re-seal is blocked by the still-open canary call-volume-floor policy decision | CS-03 |
| G4 | `review.py` (independent review's deterministic code) has no version-tracking constant, unlike renderer/authoring/registry — a structural gap in the invalidation mechanism, not a missed bump | CS-04 |
| G5 | Tests read live, mutable candidate directories directly as fixtures (`test_sealed_bytes.py`, `test_evaluation.py`, `test_control_plane.py` confirmed; scope of the pattern elsewhere unaudited) | CS-05 |
| G6 | No pre-push local CI-parity discipline exists; only `pytest` was ever run locally before a push, letting lint/format/mypy drift silently for an entire pass | CS-06 |
| G7 | CI is currently red end-to-end, for reasons now fully diagnosed but not yet resolved (G1–G3) | CS-07 |

Every gap above maps to exactly one taskcard; CS-07 is the umbrella taskcard whose own Definition
of Done depends on CS-01/CS-02/CS-03 (or an explicit owner decision to accept the staleness) —
listed as a dependency, not a duplicate mapping.

---

### CS-01 — Move the held candidate WIP out of the ambient working tree

- **Status:** Not Started — owner explicitly said "leave it for now" on 2026-09-09 when this was
  first found; this taskcard exists so the decision is executable the moment it is revisited, not
  because it is authorized to run now.
- **Gap linkage:** G1
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Commit the held `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/65b1f577.../`
    working-tree changes to a clearly-named branch (e.g. `wip/3d-python-canary`) rather than main,
    so `main`'s working tree stays clean and every local test run reads what is actually
    committed. Does not resolve the canary call-volume-floor policy question (CS-03) — only
    removes the ambient masking effect.
  - **Allowed paths:** `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/**` (via `git` branch
    operations only — `git checkout -b`, `git add`, `git commit` — no content edits), plus this
    taskcard's own status update.
  - **Forbidden:** any other candidate directory; any code, test, or doc path; do not touch the
    canary call-volume-floor decision itself (CS-03's own scope).
- **Acceptance checks (customize):**
  - CLI: `git status` on `main` shows zero modifications under `candidates/`; `repository-presenter
    status` output is unchanged before/after (the branch move must not alter `CURRENT` on `main`).
  - UI/Web/API: N/A — this project exposes only a CLI entry point.
  - Tests: `pytest tests/test_sealed_bytes.py tests/components/readme/bundle/test_evaluation.py
    tests/test_control_plane.py -q` run on a clean `main` checkout (no stash, no held WIP) before
    and after, confirming the divergence set matches what CI already shows (G2/G3's known
    failures) rather than something new appearing once the working tree is clean.
  - Config respected end-to-end: N/A (no config surface for this operation).
  - No mock data in production paths: N/A — a `git` branch operation, no data is generated.
- **Deliverables:**
  - The WIP committed to its own branch, pushed, `main` unaffected.
  - A one-line note in `plans/healing/ci-staleness-followup.md` (this file) recording the branch
    name and that this taskcard is Done.
  - No test changes required by this taskcard itself (CS-05 covers the fixture-fragility this
    exposed).
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — N/A, no code changed.
  - No network in offline tests — unaffected.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — N/A, CLI-only project, no
    entry-point change.
  - Mock vs Live mode where relevant (flag/config driven) — N/A.
  - Deterministic runs (seed/stable ordering) where needed — N/A, a `git` operation.
  - No new deps without explicit justification — none added.
  - Keep code/docs/tests in sync — this taskcard's own status update is the sync point.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the working tree is clean on `main`; no test run can silently read
    uncommitted content again for this candidate.
  - Test coverage: 5/5 = the three affected test files were run clean-tree before and after, with
    the divergence set explicitly confirmed to match G2/G3, not expanded.
  - No regressions: 5/5 = `CURRENT` on `main` is byte-identical before and after; no candidate is
    newly sealed, unsealed, or altered by this move.
  - Determinism: 5/5 = a `git` branch/commit operation, no ambiguity in outcome.
  - Documentation/traceability: 5/5 = the branch name and commit are recorded here and the WIP's
    own history explains why it exists (the canary policy question).
- **Now (runbook):**
  1. `git status` — confirm the ONLY dirty files are under the held candidate's directory.
  2. `git checkout -b wip/3d-python-canary`
  3. `git add candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/` (only this directory)
  4. `git commit -m "wip: 3D-Python canary re-render, pending canary call-volume-floor decision"`
  5. `git push -u origin wip/3d-python-canary`
  6. `git checkout main` — confirm `git status` on `main` is now clean.
  7. `pytest tests/test_sealed_bytes.py tests/components/readme/bundle/test_evaluation.py tests/test_control_plane.py -q --tb=short` — confirm the failure set matches G2/G3 exactly, nothing new.
  8. Update this taskcard's Status to Done with the branch name.

### CS-02 — Re-seal Cells .NET and Email-Python against the landed renderer fix

- **Status:** Partially Done, 2026-09-09 (owner confirmed via independent review: "up to the mark
  should mean a green `gh run watch`").
  - **Cells .NET: Done.** Two-run record-then-adopt cycle completed exactly as designed - first
    run recorded `VALID_UPDATE_AVAILABLE` (15 provider calls), second run adopted it with
    `provider calls 0; update adopted (factual): a fresh process reproduced the waiting update
    byte for byte`. `test_sealed_bytes.py`'s Cells .NET case now passes; `status --stale` dropped
    from 8 to 7. Committed.
  - **Email-Python: genuinely rejected, not forced through - a new, real finding, not a retry
    candidate.** `present`'s first run failed at `BC-10`/`REJECT_PRESENTATION`: the composed
    candidate's API reference carries the class table *and* a duplicate list-format rendering of
    the same classes. Traced directly: this transaction's `source_reconciliation` was seeded from
    the sealed bundle (reused, not re-run), so the disposition keeping that list-format unit
    `VERIFIED_PRESERVE` predates RC-02's placement-coverage fix - the *placement* layer now
    correctly recognizes the overlap (RC-02 working as designed), but the *disposition* driving
    what gets preserved was never revisited to match. A repair round tried and the equivalent
    failure recurred, meaning this needs `RECONCILING` to genuinely re-run with the RC-02-aware
    model, not a `COMPOSING`-stage patch. **New, previously-undiscovered structural gap found as a
    side effect**: `bundle/evaluation.py`'s `evaluate()` maps every `components.*` change to
    `COMPOSING` uniformly (see CS-04's own honest note in `docs/STATE_MACHINE.md` section 9) -
    never `RECONCILING` - so a placement-coverage improvement like RC-02's can land, verify clean
    in isolation, and never actually get exercised against a real candidate's reconciliation
    output until something else independently reopens `RECONCILING`. No bundle was written (exit
    code 1); Email-Python's prior sealed state is completely unaffected. Full finding in
    `docs/DECISION_LOG.md`'s 2026-09-09 21:50 entry. Tracked going forward under
    `r1-reseal-operations.md`'s OPS-03 shape (a candidate correctly left unsealed pending a
    mechanism fix) - the mechanism fix itself (either a narrow `evaluate()` addition mapping a
    coverage-relevant component change to `RECONCILING`, or a more targeted trigger) is a new,
    not-yet-taskcarded gap this file does not invent a fix for unilaterally.
  - **Deep-dive follow-up, 2026-09-09 22:20**: root-caused precisely and prototyped
    (`docs/RECONCILIATION_COVERAGE_ASSESSMENT.md`) - `dispositions.py`'s existing deterministic
    `api_reference` normalization only ever covered `.table`-shaped duplicates, never `.list`.
    A fix was implemented, then verified against all 8 real sealed candidates before trusting it:
    it correctly closed 4 of Email-Python's 5 duplicates, but flagged 22 units on Aspose.Cells
    FOSS for Rust, including content unrelated to the API reference entirely, and - even narrowed
    to `.list` only - risked real content loss (method-signature detail the Core API table does
    not show). **Not shipped** - reverted before commit. This is RC-06's own "member reference
    list granularity, high-risk, prototype-first" territory, not a quick fix; Email-Python stays
    genuinely unresolved under OPS-03 until RC-06's own prototype process runs.
- **Gap linkage:** G2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Re-run `present` for `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` and
    `aspose-email-foss/Aspose.Email-FOSS-for-Python` so their sealed bytes pick up RC-02's
    already-landed, already-verified-desirable duplicate-detection fix (confirmed 2026-09-09:
    both candidates' divergence is a genuine improvement, not a regression — see RC-02's own note
    in `plans/healing/production-consistency-reassessment.md`).
  - **Allowed paths:** `candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-.NET/**`,
    `candidates/aspose-email-foss__Aspose.Email-FOSS-for-Python/**` (new revision directories and
    `CURRENT` pointer updates only, via the normal `present`/seal pipeline — no hand edits).
  - **Forbidden:** any source code path (the fix is already landed; this is a re-seal only); any
    other candidate directory; the canary (3D-Python, CS-03's own scope).
- **Acceptance checks (customize):**
  - CLI: `repository-presenter present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` and
    the Email-Python equivalent both complete with a `READY_FOR_PROPOSAL`-or-better manifest
    state and zero unexpected provider-call cost overruns.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: `pytest tests/test_sealed_bytes.py -q` shows both candidates passing after re-seal;
    `repository-presenter status --stale` no longer lists either repository.
  - Config respected end-to-end: the real registry/gateway config drives the run, no shortcuts.
  - No mock data in production paths: the run makes real provider calls against the real
    repositories; nothing is stubbed.
- **Deliverables:**
  - Two new sealed revisions (or updated `CURRENT` pointers), each a full, real `present` output —
    no partial or hand-edited bundle files.
  - A `docs/DECISION_LOG.md` entry recording the re-seal, citing RC-02 and this taskcard.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — N/A, no code changed.
  - No network in offline tests — the re-seal itself is the one place real network/provider calls
    are expected and correct; no *test* gains new network access.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — N/A, CLI-only.
  - Mock vs Live mode where relevant (flag/config driven) — this is explicitly a Live-mode run
    (real provider calls); do not run it in `dry_run` mode and call it sealed.
  - Deterministic runs (seed/stable ordering) where needed — the seal's own no-op-proof mechanism
    (record-then-adopt) is the existing determinism guarantee; reuse it, do not bypass it.
  - No new deps without explicit justification — none needed.
  - Keep code/docs/tests in sync — `status --stale`'s output is the sync check.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = both candidates' sealed bytes match current code; `status --stale` shows
    neither.
  - Test coverage: 5/5 = `test_sealed_bytes.py` passes for both, confirmed via a full local run.
  - No regressions: 5/5 = every other currently-sealed candidate's byte-identity is unaffected
    (spot-checked before/after).
  - Determinism: 5/5 = the seal used the existing record-then-adopt mechanism, not a forced write.
  - Documentation/traceability: 5/5 = `DECISION_LOG.md` entry cites RC-02 and this taskcard by ID.
- **Now (runbook):**
  1. `repository-presenter status --stale` — confirm current baseline (both candidates listed).
  2. `repository-presenter present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-.NET`
  3. `repository-presenter present --repo aspose-email-foss/Aspose.Email-FOSS-for-Python`
  4. `pytest tests/test_sealed_bytes.py -q --tb=short` — confirm both now pass.
  5. `repository-presenter status --stale` — confirm neither is listed.
  6. Append the `DECISION_LOG.md` entry; commit and push per this session's one-taskcard-one-commit
     discipline.

### CS-03 — Re-seal or explicitly hold the canary (3D-Python), gated on the call-volume-floor decision

- **Status:** Blocked — by the still-open canary call-volume-floor policy decision (3 options
  recorded in `docs/DECISION_LOG.md`, none chosen; see `plans/healing/EXECUTION-PLAN.md`'s
  Excluded section). Not executable until the owner decides.
- **Gap linkage:** G3
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Once the canary call-volume-floor policy question is resolved (owner decision, not
    this taskcard's to make): re-run `present` for the canary
    (`aspose-3d-foss/Aspose.3D-FOSS-for-Python`) so its sealed bytes pick up the three landed
    version bumps (`RENDERER_VERSION` 18, `NORMALISATION_VERSION` 2, `BC-03` v2), following
    whichever of the three recorded options the owner selects. If the owner instead picks a
    non-canary candidate for routine work (the alternative `EXECUTION-PLAN.md` already names),
    this taskcard's Fix becomes "pick and document the new canary" instead — do not guess which
    branch applies.
  - **Allowed paths:** `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/**` (new revision or
    `CURRENT` update via the normal pipeline only); `project/state.yaml`'s `canary` field, only if
    the owner picks the "different canary" branch.
  - **Forbidden:** any source code path; any other candidate directory; do not resolve the policy
    question itself autonomously — that is explicitly excluded from this pass, per
    `plans/healing/EXECUTION-PLAN.md`'s own "Excluded from this autonomous pass" section.
- **Acceptance checks (customize):**
  - CLI: `repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python` completes
    with a state consistent with whichever policy option was chosen (a raised floor may change
    what "holds its floor" means for `test_the_sealed_canarys_first_attempt_acceptance_holds_its_floor`).
  - UI/Web/API: N/A — CLI-only project.
  - Tests: `pytest tests/core/llm/test_ledger.py tests/test_sealed_bytes.py -q` both pass
    afterward, under the new, owner-chosen floor semantics.
  - Config respected end-to-end: real registry/gateway config, no shortcuts.
  - No mock data in production paths: real provider calls, nothing stubbed.
- **Deliverables:**
  - A new sealed revision (or an explicit, documented decision not to re-seal, if the owner picks
    a different path).
  - A `docs/DECISION_LOG.md` entry recording which of the three floor options was chosen, by whom,
    and why — this is the actual deliverable this taskcard has been blocked on.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — N/A unless the floor's own
    check function needs a signature change to express the new policy, in which case update its
    one call site in `tests/core/llm/test_ledger.py`.
  - No network in offline tests — unaffected.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — N/A, CLI-only.
  - Mock vs Live mode where relevant (flag/config driven) — Live mode, same as CS-02.
  - Deterministic runs (seed/stable ordering) where needed — reuse the existing record-then-adopt
    mechanism.
  - No new deps without explicit justification — none needed.
  - Keep code/docs/tests in sync — the floor test and the decision log must agree.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the canary's own policy question is resolved and recorded, not just its
    symptom (a stale seal) patched over.
  - Test coverage: 5/5 = the floor test and `test_sealed_bytes.py` both pass under the new policy.
  - No regressions: 5/5 = every other currently-sealed candidate is unaffected.
  - Determinism: 5/5 = the seal mechanism itself is unchanged, only its policy input.
  - Documentation/traceability: 5/5 = `DECISION_LOG.md` names the chosen option and the reasoning.
- **Now (runbook):**
  1. Obtain the owner's decision on the canary call-volume-floor question (not automatable).
  2. If re-sealing the same canary: `repository-presenter present --repo
     aspose-3d-foss/Aspose.3D-FOSS-for-Python`, then `pytest tests/core/llm/test_ledger.py
     tests/test_sealed_bytes.py -q`.
  3. If switching canaries: update `project/state.yaml`'s `canary` field and document why.
  4. Append the `DECISION_LOG.md` entry naming the chosen option.
  5. Commit and push per the one-taskcard-one-commit discipline.

### CS-04 — Add a code-level version constant for independent review's deterministic logic

- **Status:** Done
- **Checklist:**
  - [x] Add `REVIEWER_LOGIC_VERSION` constant to `review.py` (starts at "2", retroactively
    crediting PA-02's already-landed `quote_located` scoping change)
  - [x] Wire into `upstream_dependencies()` (`seal.py`) as `components.reviewer_logic`
  - [x] Wire into `cli.py`'s `--stale` report
  - [x] Update `test_dependencies_name_exactly_the_consumed_inputs` (`test_seal.py`) +
    `test_cli.py`'s hardcoded dict
  - [x] Presence test — satisfied by the two updated assertions above (they fail if the key is
    missing); no separate test needed
  - [x] Full suite run once — only the three already-tracked pre-existing divergences (canary
    floor, Cells .NET, Email-Python), nothing new
  - [x] `docs/STATE_MACHINE.md` section 9 updated with an honest note: `evaluate()`'s `components`
    comparison currently reopens `COMPOSING` for every component uniformly (including
    `reviewer_logic`), not the more precise `REVIEWING` a reviewer-logic change ideally deserves -
    conservative (never under-reopens) but imprecise; refining `evaluate()` itself is out of this
    taskcard's scope, flagged rather than silently left inconsistent with the doc.
- **Gap linkage:** G4
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `review.py` has no equivalent to `RENDERER_VERSION`/`NORMALISATION_VERSION`/
    `VALIDATOR_VERSION` for its own deterministic code (`scope_defect`, `absence_defect`,
    `quote_located`, `review_checks`, `factuality_defect`, `renderer_owned_defect`,
    `excluded_evidence_defect`) — only the *prompt's* hash/version is tracked
    (`prompts["independent_review"]`). Add a `REVIEWER_LOGIC_VERSION` constant (name is a proposal,
    not fixed — confirm against the existing naming convention before landing), wire it into
    `upstream_dependencies()`'s `components` dict alongside `shell`/`renderer`/`normalisation`, and
    bump it now to reflect PA-02's already-landed `quote_located`-scoping change (which predates
    this constant's own existence, so it is retroactively due a bump too, matching CS-01/CS-02's
    own pattern in `docs/CI_AND_STALENESS_ASSESSMENT.md`).
  - **Allowed paths:** `src/repository_presenter/components/readme/review/independent/review.py`,
    `src/repository_presenter/components/readme/bundle/seal.py` (`upstream_dependencies` only),
    `src/repository_presenter/cli.py` (`run_status`'s `current_components` dict, to include the
    new constant in the existing `--stale` report), `schemas/candidate-bundle.schema.json` if the
    `dependencies.json` schema enumerates `components`' keys explicitly (check before assuming),
    matching tests.
  - **Forbidden:** the review logic's own behavior (`scope_defect` etc.) — this taskcard adds
    tracking, it does not change what is judged; `renderer.py`/`authoring.py`/`registry.py`'s own
    constants (read, never modified, except where re-verifying CS-01–03's own bumps happens to
    overlap — coordinate, do not duplicate).
- **Acceptance checks (customize):**
  - CLI: `repository-presenter status --stale` now includes a `reviewer_logic` (or chosen name)
    row wherever a candidate's `dependencies.json` predates the new constant.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: a new test confirming `upstream_dependencies()`'s `components` dict includes the new
    key; `tests/components/readme/bundle/test_seal.py`'s existing
    `test_dependencies_name_exactly_the_consumed_inputs` updated to expect it (do not leave a
    stale hardcoded dict, the exact mistake this whole follow-up traces back to).
  - Config respected end-to-end: N/A, a pure code/schema change.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - Full file replacement for `review.py`'s new constant and its docstring (explaining scope, the
    same way `NORMALISATION_VERSION`'s comment does).
  - `seal.py`, `cli.py`, and (if needed) the schema updated to carry it through.
  - Tests for the new key's presence and for `stale_candidates` correctly reporting it.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — `upstream_dependencies`'s
    return shape gains a key, not a breaking change; every call site already reads it as a dict.
  - No network in offline tests — unaffected.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — the CLI's `--stale` report is
    the one entry point this touches; keep it consistent with the existing three components.
  - Mock vs Live mode where relevant — N/A.
  - Deterministic runs (seed/stable ordering) where needed — a version string, inherently
    deterministic.
  - No new deps without explicit justification — none.
  - Keep code/docs/tests in sync — `docs/STATE_MACHINE.md` section 9's table should gain an
    explicit row for this component too, closing the exact asymmetry
    `docs/CI_AND_STALENESS_ASSESSMENT.md` section 6 (PA-02 bullet) flagged.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = independent review's deterministic code is now versioned the same way
    every other stage's is — the asymmetry this taskcard exists to close is gone.
  - Test coverage: 5/5 = presence test plus a `stale_candidates` reporting test, both passing.
  - No regressions: 5/5 = every currently-sealed candidate's `dependencies.json` gains the new key
    at its next seal without breaking `verify_bundle`'s existing checks (additive field).
  - Determinism: 5/5 = a version string constant, no runtime computation.
  - Documentation/traceability: 5/5 = `docs/STATE_MACHINE.md` section 9 updated; a
    `DECISION_LOG.md` entry names the retroactive bump and why.
- **Now (runbook):**
  1. Read `review.py` in full to confirm the exact function set this constant should cover (match
     `NORMALISATION_VERSION`'s own precedent of naming its scope precisely in a comment).
  2. Add the constant, wire it into `upstream_dependencies`, `cli.py`'s `--stale` report, and the
     schema if needed.
  3. Bump it once, retroactively, to reflect PA-02.
  4. Update `test_dependencies_name_exactly_the_consumed_inputs` and add the new presence test.
  5. `pytest tests/components/readme/bundle/ tests/core/test_candidates.py tests/test_cli.py -q`
  6. `pytest tests/ -q --tb=no` (full suite, once).
  7. Update `docs/STATE_MACHINE.md` section 9, append the `DECISION_LOG.md` entry, commit, push.

### CS-05 — Audit and, where safe, fix tests that read live candidate directories as fixtures

- **Status:** Done
- **Notes (file list and decisions):** `grep -rln "candidates/aspose" tests/` found 6 real source
  files beyond `test_sealed_bytes.py` (already correctly excluded):
  - **Frozen (structural shape only, no real content needed):**
    `tests/components/readme/bundle/test_evaluation.py` (2 tests, renamed
    `test_a_real_dependency_record_reopens_nothing_when_nothing_changed` /
    `test_each_dependency_class_of_a_real_record_reopens_its_own_state`) and
    `tests/test_control_plane.py` (1 test, renamed
    `test_a_dependency_record_depends_only_on_per_candidate_classes`) — all three only checked a
    *shape* (a top-level key set, or a dependency-path-to-reopened-state mapping), so each now
    calls the real production function (`upstream_dependencies`) with minimal synthetic
    `FactsDocument`/real prompt-manifest inputs instead of reading any `candidates/` path - this
    is stronger than a frozen JSON snapshot, since it stays accurate automatically as the function
    evolves rather than needing manual re-freezing.
  - **Documented as deliberately live** (matching `test_sealed_bytes.py`'s own precedent, per this
    taskcard's own Forbidden clause): `tests/components/readme/bundle/test_seal.py`'s
    `test_the_sealed_canary_carries_the_receipt_its_example_facts_cite`,
    `tests/components/readme/review/test_independent.py`'s
    `test_the_sealed_canarys_advisories_are_each_adjudicated_against_the_bundle`, and
    `tests/core/llm/test_ledger.py`'s
    `test_the_sealed_canarys_first_attempt_acceptance_holds_its_floor` (the canary call-volume
    floor test) - each genuinely tests real, evolving canary content on purpose; freezing any of
    them would remove the exact regression coverage they exist for. Each now carries an explicit
    docstring/comment saying so, citing this taskcard.
  - **New regression test**: `tests/test_control_plane.py`'s
    `test_a_dependency_record_is_immune_to_a_mutated_candidate_directory` monkeypatches
    `Path.read_text` to assert (raise) on any path containing `candidates`, then confirms the
    fixed test still passes - proving it no longer touches that directory at all, not merely that
    it happens to produce the same answer today.
  - Full suite run once (`pytest tests/ -q --tb=no`): only the three already-tracked pre-existing
    divergences plus the two already-known-and-tracked CI findings this taskcard exists to close
    (see `docs/CI_AND_STALENESS_ASSESSMENT.md`) - nothing new.
- **Gap linkage:** G5
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `test_sealed_bytes.py` (by design — it is explicitly a check against real sealed
    state, this is correct for it), `test_evaluation.py`, and `test_control_plane.py` (confirmed
    today) read `candidates/aspose-3d-foss__.../dependencies.json` directly off disk as a fixture,
    not a frozen/pinned copy — so any uncommitted, in-flight change to that live directory (as the
    held 3D-Python WIP did) silently changes what these tests actually exercise, without the test
    file itself changing. Audit the full test suite for this pattern (`grep` for
    `candidates/aspose` path literals outside `test_sealed_bytes.py`), and for each genuine case
    found, either (a) freeze a copy of the specific fields needed as an inline fixture (preferred
    for tests like `test_evaluation.py`'s that only need a *shape*, not real content), or (b)
    document explicitly, in the test's own docstring, that it is deliberately testing live state
    the same way `test_sealed_bytes.py` does, so a future reader is not surprised.
  - **Allowed paths:** any test file found to have this pattern (list them explicitly once found,
    do not blanket-authorize all of `tests/`); no `src/` changes.
  - **Forbidden:** `test_sealed_bytes.py` itself (its live-read design is correct and intentional,
    per its own module docstring — do not "fix" it into a frozen fixture, that would remove its
    entire purpose).
- **Acceptance checks (customize):**
  - CLI: N/A.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: every converted test passes identically before and after freezing its fixture (byte-
    for-byte the same assertions, just no longer reading live disk state); a new regression test
    confirms a frozen test's result no longer changes if the live candidate directory is mutated
    (simulate by editing a scratch copy, not the real repo).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: this taskcard is specifically about test fixtures, not
    production code — freezing a fixture is not introducing mock data into a production path.
- **Deliverables:**
  - A short list (in this taskcard's own Notes, once done) of every file found with the pattern
    and which fix (freeze vs. document) was applied to each.
  - Full file replacements for each converted test file.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — test-only change, no public
    API affected.
  - No network in offline tests — unaffected either way.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — N/A.
  - Mock vs Live mode where relevant (flag/config driven) — this taskcard is exactly about drawing
    that line explicitly for each test, per its own Fix.
  - Deterministic runs (seed/stable ordering) where needed — a frozen fixture is strictly MORE
    deterministic than a live-disk read; this is the point.
  - No new deps without explicit justification — none needed.
  - Keep code/docs/tests in sync — each test's own docstring states which mode it uses.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = no test that should be insulated from in-flight candidate work can be
    silently affected by it again.
  - Test coverage: 5/5 = the new "mutation doesn't change a frozen test's result" regression check
    passes for every converted file.
  - No regressions: 5/5 = every converted test's actual assertions are unchanged, only their input
    source.
  - Determinism: 5/5 = frozen fixtures are pinned, not read live.
  - Documentation/traceability: 5/5 = the taskcard's own Notes list every file touched and why.
- **Now (runbook):**
  1. `grep -rn "candidates/aspose" tests/` — enumerate every test file reading a live candidate
     path.
  2. For each, decide freeze vs. document, per this taskcard's Fix.
  3. Apply the fix per file; run that file's own test module after each.
  4. Add the mutation-insulation regression test for at least one converted file.
  5. `pytest tests/ -q --tb=no` (full suite, once).
  6. Record the file list and decisions in this taskcard's Notes; commit, push.

### CS-06 — A documented, and where possible enforced, pre-push local CI-parity check

- **Status:** Done
- **Notes:** `scripts/ci_check.sh` mirrors `.github/workflows/ci.yml`'s five steps exactly (lint,
  format, type-check, pytest, entry-point), each running independently and reporting its own
  outcome in a final Summary, matching the CI workflow's own fixed design (CS-06 predates this,
  reusing it rather than inventing a second scheme). `AGENTS.md`'s existing "may be pushed... after
  the full local CI-equivalent passes" line now names the script directly (a targeted, in-place
  edit, not a net addition, given the file's own 200-line budget was already 1 line over before
  this taskcard - now 2 over; flagged honestly rather than silently ignored, tightening it further
  is a separate, small follow-up if the owner wants the budget strictly enforced).
  **Verified against a real failure, not only a synthetic one**: the script's first live run
  against the current tree (`bash scripts/ci_check.sh`, 368s) correctly reported `lint: success`,
  `format: success`, `typecheck: success`, `pytest: failure` (the three already-known, already-
  tracked divergences - canary floor, Cells .NET, Email-Python), `entrypoint: success`, and exited
  non-zero with the correct summary message - proving the per-step differentiation and non-fail-
  fast execution work correctly on a real, current failure state, which is stronger evidence than
  a synthetic scratch-commit test would have been (a real failure is not something the script's
  author could have accidentally special-cased for). Not separately re-tested with an artificial
  lint break, given the mechanism (independent execution + per-step outcome capture + accurate
  summary) is already demonstrated end-to-end by this real run.
- **Gap linkage:** G6
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Nothing enforced that the four CI gates (`ruff check`, `ruff format --check`, `mypy
    src`, `pytest`) plus the entry-point smoke run locally before a push — only `pytest` was ever
    run by habit this whole pass, letting lint/format/mypy drift silently. Add a single script
    (e.g. `scripts/ci_check.sh` and/or a documented sequence in `AGENTS.md`/`CLAUDE.md` if one
    exists in this repo — check first) that runs exactly what CI runs, in the same order, so
    "green locally" and "green on CI" mean the same thing. A git pre-push hook is the stronger,
    optional second step — propose it, do not silently install one without the owner's sign-off
    (a hook that blocks pushes is a workflow change, not a pure bugfix).
  - **Allowed paths:** a new `scripts/ci_check.sh` (or equivalent), a short addition to whichever
    top-level contributor-facing doc already exists (`AGENTS.md`, `README.md`, or similar — check
    before assuming one is the right place), optionally `.git/hooks/pre-push` (local-only, never
    committed — git hooks are not versioned by default; if a committed, installable hook is
    wanted, that is a distinct, larger decision to flag, not assume).
  - **Forbidden:** the CI workflow itself (`.github/workflows/ci.yml`, already fixed this pass —
    this taskcard's script must match it, not duplicate divergent logic); any source/test path.
- **Acceptance checks (customize):**
  - CLI: `scripts/ci_check.sh` (or chosen name) run against a deliberately lint-broken scratch
    commit correctly reports failure with the same message shape CI would; run clean, it reports
    success.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: N/A directly (this is a shell/process script, not application code) — validated by
    running it against both a known-good and a known-bad state, per Acceptance's CLI bullet.
  - Config respected end-to-end: the script reads the same `requirements-lock.txt`/tool config CI
    does, no separate, drifting configuration.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - The script itself, executable, with a one-line usage comment at the top.
  - A short doc addition pointing to it as the pre-push step.
- **Hard rules:**
  - Keep public signatures unless justified; update all call sites — N/A, no code changed.
  - No network in offline tests — the script itself may need network for `pip install`
    verification parity with CI; document that clearly, do not silently assume it is offline-safe.
  - Keep entrypoints in parity where applicable (CLI/UI/API/MCP) — this IS the parity mechanism
    for CI vs. local; that is its whole purpose.
  - Mock vs Live mode where relevant — N/A.
  - Deterministic runs (seed/stable ordering) where needed — the script's own output should be
    deterministic given the same tree state.
  - No new deps without explicit justification — reuses `ruff`/`mypy`/`pytest`, already
    dependencies; no new ones.
  - Keep code/docs/tests in sync — the script and `.github/workflows/ci.yml` must be kept
    manually in sync (note this explicitly in the script's own header comment, since there is no
    single source of truth generating both from one definition — flagging that limitation is part
    of this taskcard's own honest scope, not a defect to silently fix by inventing a
    config-generation layer, which would be new machinery beyond this taskcard's bounds).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a contributor (or this agent, next session) has one command that
    reproduces CI's real verdict locally, closing the exact gap that let this pass's lint/format/
    mypy drift go unnoticed.
  - Test coverage: 5/5 = verified against both a known-good and a known-bad scratch state.
  - No regressions: 5/5 = the script changes nothing about the actual CI workflow, only adds a
    local mirror of it.
  - Determinism: 5/5 = same tool versions, same order, same commands as CI.
  - Documentation/traceability: 5/5 = referenced from the contributor-facing doc, not hidden.
- **Now (runbook):**
  1. Check whether `AGENTS.md`, `CLAUDE.md`, or a similar top-level doc already exists in this
     repo before deciding where to document this.
  2. Write `scripts/ci_check.sh` mirroring `.github/workflows/ci.yml`'s five steps exactly.
  3. Test it against a deliberately lint-broken scratch commit (confirm it fails with a clear
     message); test it clean (confirm it passes).
  4. Add the doc pointer.
  5. Propose (do not silently install) a pre-push hook as a follow-up, separate decision.
  6. Commit, push.

### CS-07 — CI genuinely green: umbrella tracking taskcard

- **Status:** Blocked — depends on CS-01, CS-02, and CS-03 (or an explicit owner decision to
  accept the current staleness as a known, documented state rather than fix it).
- **Gap linkage:** G7
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** No independent code change — this taskcard's own "fix" is verification and
    bookkeeping: confirm, via a real `gh run watch` on a real push, that every one of CI's five
    steps (lint, format, type-check, pytest, entry-point) passes with the Summary step reporting
    all-success, not just that no individual gate is broken for an unrelated reason.
  - **Allowed paths:** this taskcard's own Status field; no code, test, or doc path beyond that
    (the actual fixes live in CS-01–03; this taskcard only verifies and records the outcome).
  - **Forbidden:** forcing a candidate seal, weakening a test, or marking a known-failing test
    `xfail`/skipped to make this taskcard's own acceptance checks pass artificially — that would
    be exactly the kind of validator-spiral shortcut this whole follow-up exists to avoid.
- **Acceptance checks (customize):**
  - CLI: `gh run list --branch main --limit 1` shows `completed / success` for the latest push.
  - UI/Web/API: N/A — CLI-only project.
  - Tests: the CI run's own `pytest` step log shows zero `FAILED` lines.
  - Config respected end-to-end: N/A, a verification taskcard.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - A `docs/DECISION_LOG.md` entry recording the first genuinely green CI run's URL/ID, closing
    the loop this whole follow-up opened.
- **Hard rules:** N/A beyond the Forbidden note above — this taskcard changes nothing, it only
  confirms.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = CI is green because the real causes (CS-01–03) were resolved, not
    because a symptom was hidden.
  - Test coverage: 5/5 = confirmed via the CI run's own log, not assumed.
  - No regressions: 5/5 = the green run is on `main`, at a commit that also passed every other
    taskcard's own acceptance checks.
  - Determinism: 5/5 = a `gh run` observation, not a local claim.
  - Documentation/traceability: 5/5 = the green run is cited by ID in `DECISION_LOG.md`.
- **Now (runbook):**
  1. Confirm CS-01, CS-02, and CS-03 are each Done (or the owner has explicitly accepted residual
     staleness in their place).
  2. Push to `main` (whatever the last pending change is).
  3. `gh run watch <run-id> --exit-status`
  4. Confirm the Summary step's own per-check outcome lines are all `success`.
  5. Append the `DECISION_LOG.md` entry with the run's URL/ID; mark this taskcard Done.
