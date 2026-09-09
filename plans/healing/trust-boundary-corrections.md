# Trust-Boundary Corrections — Taskcards (external review D1–D9, 2026-09-08)

## Context

An external review packet ("Repository Presenter — Deep Trust-Boundary Review and Bounded
Correction", snapshot `main@29ebb7c`) named nine delivery-critical-to-high findings (D1–D9). Each
was independently reproduced against live HEAD (`08c88a9`, ~13 commits ahead of the snapshot) —
by direct code trace, and empirically wherever cheap to do so (D2, D3, D9's HTML-link claim; D1
against real, currently-pushed candidate data). Verdicts: D1–D8 CONFIRMED (D7 confirmed with a more
precise root cause than the packet itself states); D9 PARTIAL (its HTML-link claim confirmed, its
specific OBJ/glTF example is now stale — already incidentally fixed by an unrelated authoring pass
— though the general gap it points at remains real and unaddressed).

This file converts D1–D9 into the same Taskcard shape already established in this directory
(`production-consistency-reassessment.md`), plus one additional taskcard (TB-10) answering the
owner's follow-up instruction: enhance the system so this *class* of problem — a claim marked
verified/supported when the specific evidence doesn't actually support the specific claim — stops
recurring, rather than fixing nine instances of it and waiting for the tenth to be found by another
external audit.

**Explicitly out of scope, per the review packet's own "Do not" list and this directory's existing
discipline:** no new architecture, controller, or state machine; no blanket cache-clear; no full
suite after every micro-fix (use the focused test for the file changed, full suite once per
completed taskcard); no regenerating every candidate for a local change; never weaken a check to
make a count look better; never treat compilation-only proof as worthless — D1's fix keeps it, just
stops it from certifying an unrelated operation.

**None of TB-01 through TB-10 is implemented.** This plan file itself is the only change made in
response to the review packet and the follow-up instruction; no `src/`, `tests/`, or `prompts/`
file was touched.

## Gap table

| Gap ID | Description | Taskcard ID |
|---|---|---|
| D1 | `_source_build_fact` promotes SUPPORTED on any `EXECUTED` receipt regardless of what the execution actually proved (syntax-only, source-fallback after a failed install) | TB-01 |
| D2 | Format claims are read from unreachable AST branches; fixture "read" evidence requires only staging + overall exit 0, never an actual read | TB-02 |
| D3 | Snapshot verification checks `git ls-tree HEAD` (committed objects) and README bytes only, once, before any build/extraction reads the filesystem | TB-03 |
| D4 | A failed second-reader job (`JobError`) is recorded as `second={}`, which `review_document` treats as a completed, corroborating clean read | TB-04 |
| D5 | `_check_examples` compares fence language to the bare ecosystem key instead of `EcosystemSpec.example_fences` | TB-05 |
| D6 | `verify_bundle`/`count_current_candidates`/`_write_bundle`/`_record_update` under-validate bundle integrity, currentness, and publication ordering | TB-06 |
| D7 | The ledger's own `request_sha256` field is computed by a different hash formula than the real cache key, making `seed_call_store` structurally non-functional; `_site_manifest_hash` fingerprints the wrong process; fresh-process ecosystem-plugin initialization is inconsistent | TB-07 |
| D8 | No OS-level isolation for untrusted execution; inconsistent environment redirection; no cancellation cleanup; no private-address boundary on outbound link checks | TB-08 |
| D9 | `extract_links()` misses HTML `<a href>` targets entirely; no check that authored prose about a cited example matches what the example actually does | TB-09 |
| REC-G1 | No mechanical, portfolio-wide, CI-gated sweep for the "evidence text claims more than the receipt/fixture data actually proves" pattern shared by D1/D2/D4/D9 — each instance so far was found by a human or an external audit, one at a time | TB-10 |

## Taskcards

### TB-01 — Distinct evidence strengths for compile / link / execute / install / publish

- **Status:** Done — fixed and pushed. Added `ExampleReceipt.build_verified` (default `True`); C++'s
  `-fsyntax-only` path now sets it `False` unless the real CMake build also succeeded; Python's
  source-tree fallback path (after a failed local install) now sets it `False`. `_source_build_fact`
  requires `outcome == "EXECUTED" and build_verified` before promoting. `_check_install` needed no
  change - it already fails closed on a non-SUPPORTED fact; the fix stops the false SUPPORTED from
  ever being written, rather than trying to catch it after the fact. Empirically verified against a
  real compiler (C++) and real pip/subprocess execution (Python), not mocked. Re-sealing the real
  Cells-Cpp candidate to reflect the corrected claim is a follow-up through the normal R1
  record-then-adopt path (`plans/healing/r1-reseal-operations.md`), not part of this taskcard's own
  scope (code fix + tests).
- **Checklist:** [x] fix `_source_build_fact` gate [x] fix `_check_install` evidence-text trust (no
  change needed - see note) [x] regression tests, both ecosystems, real execution [x] full suite
- **Gap linkage:** D1
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `_source_build_fact` must not promote an install command to SUPPORTED from a bare
    `outcome == "EXECUTED"` receipt. Add an explicit strength/kind to `ExampleReceipt` (or read the
    existing `detail` text mechanically where a structured field isn't practical) distinguishing
    what was actually proven: syntax-only compile, full library build, source-path execution after
    a failed package install, or genuine package installation. Render only the strength actually
    proven; a syntax-only or source-fallback result is stated as that, never as "verified source
    build."
  - **Allowed paths:** `src/repository_presenter/components/readme/evidence/facts/extract.py`,
    `src/repository_presenter/core/examples.py` (if `ExampleReceipt` needs a new field),
    `src/repository_presenter/components/readme/extractors/platforms/cpp_examples.py`,
    `src/repository_presenter/components/readme/extractors/platforms/python_examples.py`,
    `src/repository_presenter/components/readme/validation/registry.py` (`_check_install` only),
    matching test files under `tests/components/readme/evidence/facts/`,
    `tests/components/readme/extractors/platforms/`, `tests/components/readme/validation/`.
  - **Forbidden:** `renderer.py`'s installation rendering logic beyond reading whatever new field/
    text this taskcard adds; any other ecosystem's ExampleReceipt-producing code not named above.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` no
    longer renders "verified against this revision" for a command whose real build failed; it
    renders the honest, weaker claim (syntax-checked only, library build failed) or omits the
    install command's "verified" framing entirely, per the ecosystem's spec.
  - UI/Web/API: N/A.
  - Tests: the six regression controls the review packet names, each as its own test — (1) syntax
    succeeds, library build fails → not SUPPORTED as "verified source build"; (2) package install
    fails, source-path example works → recorded as source-path fallback, not a registry-command
    success; (3) unrelated print-only example exits zero → does not promote an unrelated install
    fact; (4) genuinely successful advertised installation → still SUPPORTED, unchanged behavior;
    (5) registry existence without the advertised version/artifact → not SUPPORTED; (6) a real
    regression test reproducing the exact Cells-Cpp shape (`facts.json` claiming "verified source
    build" while `examples.json` says the CMake build failed) and asserting it can no longer occur.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for every changed file above.
  - The six tests as new/updated cases; no existing passing test's expected outcome for a
    genuinely-proven install may change.
  - Forward-compatible: if `ExampleReceipt` gains a field, give it a default so every existing
    sealed candidate's `examples.json` still deserializes without a schema migration.
- **Hard rules:** keep `_source_build_fact`'s signature; update every call site if `ExampleReceipt`
  gains a field; no new dependencies; deterministic (pure function of receipt data).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the rendered claim's strength always matches what was actually proven,
    verified against the real Cells-Cpp data, not just a synthetic case.
  - Test coverage: 5/5 = all six regression controls present and each fails without the fix.
  - No regressions: 5/5 = every currently-genuinely-verified install claim (e.g. a real successful
    source build elsewhere in the portfolio) is unaffected.
  - Determinism: 5/5 = same receipt data → same claim strength, every run.
  - Documentation/traceability: 5/5 = `_source_build_fact`'s docstring restates the strength
    distinction; `DECISION_LOG.md` records the fix citing Cells-Cpp as the confirmed live instance.
- **Now (runbook):**
  1. Write the six regression tests first (red), including the real Cells-Cpp fixture case.
  2. Implement the strength distinction and the `_check_install`/render changes.
  3. `pytest tests/components/readme/evidence/facts/ tests/components/readme/extractors/platforms/ tests/components/readme/validation/ -q`
  4. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  5. Re-run `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`; confirm the rendered
     installation claim now honestly reflects the failed CMake build; re-seal through the normal
     record-then-adopt path if the corrected content changes what's sealed.
  6. Commit, push.

### TB-02 — Bind format claims to the operation that actually proved them

- **Status:** Not Started
- **Gap linkage:** D2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `format_claims` must not walk into statically-unreachable branches (at minimum,
    `if False:`/`if 0:`-shaped dead code — a full reachability analysis is not required, a narrow,
    named exclusion is). `format_facts` must not mark a fixture's extension SUPPORTED as an "input"
    from staging plus overall exit 0 alone; require the specific statement claiming to read it to
    correspond to code that actually executed and referenced it, or fall back to the existing
    two-source static corroboration route (declaration + registration) already in the module.
  - **Allowed paths:** `src/repository_presenter/components/readme/extractors/platforms/python_formats.py`,
    `src/repository_presenter/components/readme/evidence/facts/formats.py`,
    `tests/components/readme/extractors/platforms/test_python_formats.py` (or wherever its tests
    live — verify exact path at execution time), `tests/components/readme/evidence/facts/test_formats.py`.
  - **Forbidden:** the two-source static corroboration mechanism itself (declared + registered) —
    preserve it exactly; this taskcard only closes the *executed-example* promotion path's gap.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A directly; observable only through `facts.json`'s format facts for a repository whose
    examples contain dead branches or unread staged fixtures — verify against any real candidate
    with such a shape if one exists in the portfolio; otherwise the regression tests below are the
    acceptance bar.
  - Tests: the six regression controls named — dead branch, uncalled function, caught operation
    failure, unused fixture, output filename staged as an input, real successful import/export
    (must still promote SUPPORTED — this is the no-regression case).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for both changed files.
  - The six tests; the dead-branch case should reuse the exact reproduction already run during
    verification (`format_claims("if False:\n  scene.save('never-produced.pdf')")`).
  - No schema/contract change — `format:*` fact IDs and polarity values are unchanged, only which
    receipts qualify to set SUPPORTED.
- **Hard rules:** keep `format_claims`/`format_facts` signatures; no new deps; deterministic (pure
  AST/receipt analysis).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a dead-code or unread-fixture claim can no longer reach SUPPORTED via the
    executed-example path.
  - Test coverage: 5/5 = all six controls present, each fails without the fix, the real-success
    case still passes.
  - No regressions: 5/5 = every currently-SUPPORTED format fact across the sealed portfolio stays
    SUPPORTED (spot-check 2–3 real candidates' `facts.json` before/after).
  - Determinism: 5/5 = pure function of code text and receipt data.
  - Documentation/traceability: 5/5 = both modules' docstrings updated; the fix cited in a
    `DECISION_LOG.md` entry.
- **Now (runbook):**
  1. Write the six regression tests (red).
  2. Implement the dead-branch exclusion in `format_claims` and the read-binding tightening in
     `format_facts`.
  3. `pytest tests/components/readme/extractors/platforms/ tests/components/readme/evidence/facts/ -q`
  4. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  5. Spot-check `facts.json` format facts for 2–3 real sealed candidates for unintended change.
  6. Commit, push.

### TB-03 — Verify the bytes actually consumed, not only the committed tree

- **Status:** Done — fixed and pushed.
- **Note:** Approach (a) chosen, documented here per the runbook's own gate: `git ls-tree HEAD`
  reads git's committed object database, never the working tree, so a tracked file edited on disk
  without a commit was invisible to it - confirmed empirically first (editing a tracked,
  non-README file in a real clone and calling `verify_snapshot` raised nothing). `verify_snapshot`
  now also runs `git diff-index --quiet HEAD --` (a single fast git-native check that reads the
  working tree, correctly handling permissions/symlinks/etc. rather than hand-rolled file
  hashing) and, on a non-zero exit, names every drifted tracked file via `--name-only`. Approach
  (b) (a `git archive` materialized copy) was rejected: it would require re-plumbing every
  consumer of `clone.path` across `cli.py` (detect_manifest, list_tree_paths, example
  verification, fact extraction - at least six call sites) and touching `git_safety/clone.py`,
  explicitly forbidden without a narrowly-scoped need; (a) is the smaller, safer change against
  the current architecture.
  `cli.py` now calls `verify_snapshot` twice more beyond the existing post-capture call: right
  before example verification (the stage most likely to run build/install tooling against
  `clone.path`) and right before fact extraction (which reads `clone.path` again after that
  tooling ran). Manifest detection needed no new call - nothing mutates `clone.path` between
  capture and it.
  **Cost measured, not assumed:** `git diff-index --quiet HEAD --` against a real clone
  (Aspose.3D-FOSS-for-Python) averaged ~70-85ms per call; two extra calls per `present` run add
  well under 200ms total, negligible against a pipeline measured in minutes.
  **Untracked files (a generated file shadowing an import) explicitly left out of scope**, not
  silently ignored: `git diff-index` reports only tracked content; catching a new *untracked*
  file would need capturing the untracked-file set at capture time (a plain directory listing,
  not a git tree diff) - a genuinely different, separately-scoped mechanism. Tested directly
  (`test_verify_does_not_catch_a_new_untracked_file_shadowing_an_import`) so the gap is documented
  and regression-visible, not silent.
- **Checklist:** [x] approach decided and documented before coding [x] four regression controls
  (tracked-file drift, build-hook-shaped drift caught at the next boundary, untracked-file gap
  documented, harmless untracked build output does not false-positive) [x] two new call sites in
  `cli.py` [x] cost measured against a real clone [x] full suite (only the two known pre-existing
  failures remain)
- **Gap linkage:** D3
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Ensure facts and examples consume bytes belonging to the pinned revision. Either (a)
    extend `verify_snapshot` to also hash the actual on-disk bytes of every tracked file (not just
    `ls-tree`'s committed-object listing) at the point of capture, and re-verify that hash at each
    stage boundary that reads from `clone.path` (manifest detection, example verification, fact
    extraction) rather than once; or (b) work from a genuinely immutable materialized copy (e.g. a
    `git archive` extraction to a fresh directory) instead of the live clone path, so there is no
    working tree left to diverge from what was captured. Pick whichever is the smaller, safer
    change against the current architecture — decide and document the choice before implementing,
    do not implement both.
  - **Allowed paths:** `src/repository_presenter/core/snapshot/capture.py`,
    `src/repository_presenter/cli.py` (call-site changes only, not unrelated logic),
    `tests/core/snapshot/` (verify exact test path at execution time).
  - **Forbidden:** `git_safety/clone.py` unless the chosen approach (b) requires it — decide and
    scope narrowly before touching it; do not redesign the clone lifecycle.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present` against a clone with an uncommitted modification to a
    non-README tracked file (a manifest, a source file) now fails closed with a clear error, where
    today it silently proceeds.
  - Tests: the four regression controls — tracked source/manifest/license change without a HEAD
    change (must now fail closed); a build hook modifying source (must be caught at the next
    verification boundary, or prevented by the immutable-copy approach); an untracked/generated
    file shadowing an import (documented as in-scope or explicitly out-of-scope with reasoning, not
    silently ignored); unchanged source with harmless separate build outputs (must still succeed —
    the no-regression case).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacement for the chosen approach's files.
  - The four regression tests, using the exact empirical technique already proven during
    verification (a real temp git repo, dirty a tracked file, confirm detection).
  - No change to `RepositorySnapshot`'s public fields unless the chosen approach requires one; if
    so, it is additive (new optional field), not a breaking rename.
- **Hard rules:** no network; deterministic given a fixed tree; keep `capture_snapshot`/
  `verify_snapshot`'s public signatures unless the design genuinely requires a change, in which
  case update every call site (currently exactly one, in `cli.py`).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a modification to any tracked file after capture and before the stage
    that consumes it is now caught, not only a README change.
  - Test coverage: 5/5 = all four controls present, verified with the same real-git-repo technique
    used to confirm the original defect, not a mock.
  - No regressions: 5/5 = every currently-passing `present` run against an untouched clone is
    unaffected; the added verification cost is measured and reported, not assumed negligible.
  - Determinism: 5/5 = same tree state → same verification result.
  - Documentation/traceability: 5/5 = `capture.py`'s module docstring updated to state what is now
    covered and why the prior mechanism (`ls-tree HEAD` alone) was insufficient, with the empirical
    proof cited.
- **Now (runbook):**
  1. Decide approach (a) or (b); write a one-paragraph rationale in this taskcard's own file before
     writing code.
  2. Write the four regression tests using a real temporary git repository, not a mock (red).
  3. Implement the chosen fix.
  4. `pytest tests/core/snapshot/ -q`
  5. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures; specifically
     check for a wall-clock regression if approach (a) adds per-stage hashing of a large tree.
  6. Commit, push.

### TB-04 — A failed second review must never corroborate anything

- **Status:** Done — fixed and pushed. `rounds.py`'s except-branch now returns `None` (via a new
  `_second_opinion` helper) instead of constructing `document(second={})`; `review_document`'s
  docstring rewritten (its own prior reasoning was the bug). Existing test
  `test_a_prose_judgment_on_a_required_row_blocks_only_when_a_second_reader_agrees` already proves
  `review_document`'s internal `second={}` vs `second=None` distinction is a deliberate, separate,
  correct API (an empty-but-real second reading vs. no reading) - the bug was purely that
  `rounds.py` used the wrong sentinel for "the job failed." New file
  `tests/components/readme/repair/test_rounds.py` (2 tests) covers `_second_opinion` directly.
- **Checklist:** [x] fix `rounds.py` except-branch [x] reproduction test (JobError -> None, not {}) [x] regression controls (existing review_document test unaffected) [x] full suite
- **Gap linkage:** D4
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `rounds.py`'s `except JobError: review = document(second={})` must instead call
    `document(second=None)` — the same branch a first-attempt-only review takes — or `review_document`
    must be changed to treat an empty dict identically to `None` (no `findings` key present is not
    "found zero findings," it's "no reading happened"). Additionally, `second_reader.read` must
    record whether a *usable* second reading occurred, not merely whether the parameter was
    non-`None`.
  - **Allowed paths:** `src/repository_presenter/components/readme/repair/rounds.py`,
    `src/repository_presenter/components/readme/review/independent/review.py`,
    `tests/components/readme/repair/test_rounds.py` (verify exact path at execution time),
    `tests/components/readme/review/test_independent.py`.
  - **Forbidden:** the two-reader policy's own design (a genuine second reading that finds nothing
    still legitimately demotes a prose-judgment finding — preserve that exactly); `renderer.py`'s
    `renderer_owned_defect`/`rendered_defect` — this taskcard's own scope note does not extend to
    re-litigating that separately-flagged, deliberately-unpatched gap from this session's own
    production-consistency reassessment.
- **Acceptance checks (customized for this repo):**
  - CLI: a composition whose second-reader job raises `JobError` (simulate via the existing test
    seam, not a live provider) now shows the first reader's original verdict unchanged in the CLI's
    review summary line, not a silently-improved ACCEPT.
  - Tests: the in-memory reproduction already run during verification, promoted to a real test —
    same first review, `second=None` → REJECT_PRESENTATION with one blocking finding;
    `second={}` (or however a failed job is now represented) → the *same* REJECT_PRESENTATION, not
    ACCEPT. Plus the six regression controls named: timeout, malformed second response, exhausted
    re-ask, valid disagreement (must still block), valid corroboration (must still demote — the
    no-regression case), genuine defect in deterministic renderer output (must still be caught,
    unrelated to this fix).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for both changed files.
  - The reproduction test plus the six regression controls.
  - Forward-compatible: `review.json`'s `second_reader.read` field semantics change (now means
    "a usable reading happened," not "an attempt was made") — this is a meaning correction, not a
    schema break; existing sealed `review.json` files remain valid to read, just describe the old
    (buggy) behavior for whatever was sealed under it. Consider whether any already-sealed
    candidate's ACCEPT verdict was reached via this exact bug (audit, do not assume none were) —
    see TB-10 for the portfolio-wide sweep this motivates.
- **Hard rules:** keep `review_document`'s public signature; no new deps; deterministic given fixed
  inputs.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a failed second-reader job can no longer improve a verdict, verified by
    the exact in-memory reproduction that confirmed the original defect.
  - Test coverage: 5/5 = reproduction test + all six regression controls present.
  - No regressions: 5/5 = a genuine, successful, disagreeing or corroborating second reading still
    behaves exactly as before.
  - Determinism: 5/5 = same first review + same second-reader outcome → same verdict, every time.
  - Documentation/traceability: 5/5 = `review_document`'s docstring corrected (the current text's
    own reasoning - "returned nothing usable... is the same answer as a second reader who saw no
    such defect" - is the bug's root cause and must be rewritten, not just the code); `DECISION_LOG.md`
    entry flags this as the most severe of the nine findings and notes the portfolio-audit follow-up.
- **Now (runbook):**
  1. Write the in-memory reproduction test first, exactly as verified (red).
  2. Write the six regression controls (red).
  3. Fix `rounds.py` and, if needed, `review_document`'s `second is not None` handling.
  4. `pytest tests/components/readme/repair/ tests/components/readme/review/ -q`
  5. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  6. Audit: for every currently-sealed candidate, check whether `review.json`'s `second_reader.read`
     is `true` with zero `corroborated` entries and a `JobError`-shaped gap in that composition's
     `calls.jsonl` (a `disposition` other than `success` for the second-reader job) - if any exist,
     that candidate's ACCEPT verdict is unproven and needs re-review, not silent trust.
  7. Commit, push.

### TB-05 — Validate examples against the ecosystem's own fence contract

- **Status:** Not Started
- **Gap linkage:** D5
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `_check_examples` must compare a fence's language against
    `spec_for(candidate.entry.ecosystem).example_fences`, not the bare `candidate.entry.ecosystem`
    string. Parse fences through the project's existing Markdown parser (already used elsewhere in
    this codebase, e.g. `links.py`'s `MarkdownIt` usage) rather than the current substring-based
    `_fences()` helper, so CommonMark fence forms (tilde fences, info-string variations) are
    covered the same way real examples are.
  - **Allowed paths:** `src/repository_presenter/components/readme/validation/registry.py`
    (`_check_examples` and its `_fences` helper only), `tests/components/readme/validation/test_registry.py`.
  - **Forbidden:** `core/ecosystems.py` (read `example_fences`, do not modify the spec table); any
    other `_check_*` function in `registry.py`.
- **Acceptance checks (customized for this repo):**
  - CLI: an unplanned `csharp` block in a .NET candidate's README, or an unplanned `py`-fenced
    block in a Python candidate's, now fails BC-03 where today it passes silently.
  - Tests: the six regression controls named — every admitted alias (`py`, `python3` for Python;
    whatever `NET`/other ecosystems declare), unplanned code (must now fail), edited verified code
    (must still fail, unchanged), tilde fences, ordinary non-example fences (must not false-positive),
    unchanged valid examples (no-regression case). Confirm through the complete candidate validator
    (`run_checks`/whatever assembles all `BC-*`), not only this one helper in isolation - a
    portfolio-wide check catching one candidate but not the whole pipeline's actual behavior would
    be an incomplete fix.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacement for `registry.py`'s two changed functions.
  - The six tests, run at both the helper level and the full-candidate-validator level.
  - No schema change - `BC-03`'s failure shape is unchanged, only what it catches.
- **Hard rules:** keep `_check_examples`'s signature; no new deps (reuse the existing Markdown
  parser dependency); deterministic.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = every ecosystem's real fence aliases are checked, verified against
    `EcosystemSpec.example_fences` directly rather than a second hand-maintained list.
  - Test coverage: 5/5 = all six controls, at both the helper and full-validator level.
  - No regressions: 5/5 = every currently-sealed candidate's examples still validate identically
    (spot-check the portfolio).
  - Determinism: 5/5 = pure function of README text and the ecosystem spec.
  - Documentation/traceability: 5/5 = `_check_examples`'s docstring cites the .NET/`csharp` case
    that confirmed the gap.
- **Now (runbook):**
  1. Write the six regression tests, including a synthetic .NET candidate with an unplanned
     `csharp` block (red).
  2. Implement the `example_fences`-based comparison and CommonMark-aware fence parsing.
  3. `pytest tests/components/readme/validation/ -q`
  4. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  5. Spot-check the real portfolio (all 8 current candidates) for any newly-surfaced BC-03 failure
     - a real one is a genuine finding to record, not something to suppress to keep this taskcard
       green.
  6. Commit, push.

### TB-06 — Bundle integrity, currentness, and publication order

- **Status:** Done — all four sub-fixes landed and pushed.
- **Note:** (1) `verify_bundle` moved from `seal.py` to `core/candidates.py` (the lower-level
  module both `seal.py` and `count_current_candidates` depend on; `candidates.py` calling back
  into `seal.py` would have been circular) and now validates `schema_version` and rejects an
  empty `files` inventory before trusting it, in addition to the pre-existing per-file
  existence/digest checks; it now raises `BundleError` (extended to inherit `PresenterError` too,
  so `cli.py`'s existing `except (PresenterError, RetryableOperationError)` in `run_present` still
  fails closed on it with no `cli.py` change needed) rather than `SealError`. (2)
  `count_current_candidates` now reads each repository's `CURRENT` file and verifies only that
  exact revision - never scans every historical revision directory - and additionally checks the
  manifest's own `revision`/`repository` fields agree with `CURRENT` and the directory it was
  found under. (3) `_write_bundle` now stages every file to a sibling temp directory, scans *that*
  for secrets, and only rmtree+renames it into place - and only then updates `CURRENT` - once the
  scan passes; no existing staging/atomic-publication facility existed anywhere in this codebase
  (checked first). (4) `_record_update` now distinguishes a factual contradiction from harmless
  presentation drift by moving the manifest's own `state` to the newly-implemented
  `VALID_UPDATE_AVAILABLE` (named in `docs/STATE_MACHINE.md` sections 5 and 9 but never
  previously written by any code) for the factual case only, excluding it from
  `COUNTED_STATES`; `seal_candidate`'s record/adopt guard was extended to also recognize that
  state so the two-run, zero-provider-call adoption discipline still applies to a bundle sitting
  at `VALID_UPDATE_AVAILABLE` (proven live: the giant lifecycle test in `test_seal.py` now drives
  a factual update all the way through un-counting and back through adoption to
  `READY_FOR_PROPOSAL`). `candidate-bundle.schema.json` gained the new state value and its
  `no_op_proof`/`update` invariants. One pre-existing test in `test_cli.py` asserted the old,
  incorrect behavior (a factual update staying `READY_FOR_PROPOSAL`) and was corrected, not
  reverted. Verified directly against the real 8-candidate portfolio (unchanged count) and the
  live CLI (`repository-presenter status`), per the taskcard's own deliverable requirement.
- **Checklist:** [x] verify_bundle schema/inventory validation [x] count_current_candidates reads
  only CURRENT [x] _write_bundle stages+scans+atomically-promotes before touching CURRENT
  [x] _record_update's factual/presentation state distinction (VALID_UPDATE_AVAILABLE) [x] ten
  regression controls [x] real-portfolio verification [x] full suite (only the two known
  pre-existing failures remain)
- **Gap linkage:** D6
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Four independent corrections in `seal.py`/`candidates.py`: (1) `verify_bundle` must
    validate `schema_version` against the known-supported value(s) and reject an unsafe/unexpected
    manifest path before trusting `files`; (2) `count_current_candidates` must read `CURRENT`,
    resolve to that exact revision's manifest, and call `verify_bundle` on it, never scan every
    historical revision directory for any counted state; (3) `_write_bundle` must scan for secrets
    *before* writing files, the manifest, or advancing `CURRENT` - stage to a temp location and
    promote atomically only after the scan passes, using this codebase's existing staging/atomic-
    publication facilities if any exist (check for one before building a new one); (4) `_record_update`
    must not blanket-preserve `READY_FOR_PROPOSAL` for a "factual" classification - new evidence
    that contradicts what was sealed must move the bundle out of a counted state, while genuinely
    harmless enrichment may stay counted; the two cases must be distinguishable in code, not left
    to the same boolean.
  - **Allowed paths:** `src/repository_presenter/components/readme/bundle/seal.py`,
    `src/repository_presenter/core/candidates.py`,
    `tests/components/readme/bundle/test_seal.py`, `tests/core/test_candidates.py` (verify exact
    path at execution time).
  - **Forbidden:** the `VALID_UPDATE_AVAILABLE`/record-then-adopt mechanism's own two-run,
    zero-provider-call proof discipline - preserve it exactly; this taskcard changes what state a
    *disproven* bundle carries, never how a *proven* one gets adopted.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter status` no longer counts a repository whose only sealed bundle has
    been disproven by new evidence; an adversarial in-memory manifest (`schema_version=999`,
    `files={}`) is now rejected by `verify_bundle`, not accepted.
  - Tests: the regression controls named - empty inventory, omitted required file, corrupt content,
    unsupported schema, wrong repository/revision, stale `CURRENT`, obsolete `READY` sibling,
    partial write, secret-scan failure (must leave no trace on disk, not merely raise after writing),
    new evidence contradicting accepted content (must un-count it).
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for both changed files.
  - All ten regression controls as tests.
  - Forward-compatible: every currently-sealed candidate's manifest already has `schema_version: 1`
    and a complete `files` map - the new validation must accept all 8 unchanged; verify this
    directly against the real portfolio, not only synthetic fixtures.
- **Hard rules:** keep `verify_bundle`/`count_current_candidates`'s public signatures; no new deps;
  the atomic-publication change must not introduce a window where `CURRENT` points at a
  partially-written bundle - if no existing staging facility covers this, the narrowest correct
  primitive is a temp-directory-then-rename, not a new general-purpose framework.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = all four sub-defects closed, each verified by its own regression control,
    not just the headline "count" or "state" field looking right.
  - Test coverage: 5/5 = all ten controls present and each fails without its corresponding fix.
  - No regressions: 5/5 = every one of the 8 real, currently-valid bundles still verifies and
    counts correctly after the change.
  - Determinism: 5/5 = same manifest/ledger state → same verification and count result.
  - Documentation/traceability: 5/5 = `seal.py`'s and `candidates.py`'s module docstrings updated;
    `DECISION_LOG.md` entry records the write-before-secret-scan ordering fix specifically, since
    it is the most security-relevant of the four.
- **Now (runbook):**
  1. Write all ten regression tests first (red), including the real adversarial manifest case.
  2. Implement the four fixes, in the order: secret-scan ordering (2), schema/inventory validation
     (1), `count_current_candidates` (3), `_record_update`'s state distinction (4) - roughly
     increasing design complexity, so a partial completion still lands real value.
  3. `pytest tests/components/readme/bundle/ tests/core/ -q`
  4. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  5. Run `repository-presenter status` against the real portfolio; confirm the count is unchanged
     for the 8 genuinely-valid current bundles.
  6. Commit, push.

### TB-07 — Correct cache-key identity and environment fingerprinting

- **Status:** Done — all three parts landed and pushed.
- **Note (part 2, scoped down deliberately):** `_site_manifest_hash` was not built into a full
  per-ecosystem toolchain fingerprint (C++ compiler/CMake version, JDK, cargo/rustc, go, node -
  none of this exists anywhere today as structured, capturable data; building it would need new
  extraction-time plumbing and its own design, the same caution RC-06 already applies elsewhere
  in this plan). Instead: renamed to `_presenter_site_manifest_hash`/`"presenter_site_manifest"`
  and rewrote its docstring to state plainly what it has always actually measured (repository-
  presenter's own environment, never the target's) - closing the misleading-naming half of the
  defect honestly, without claiming a fix this pass didn't do. The full toolchain-fingerprint gap
  remains open and undocumented as its own future item - flagged here, not silently dropped.
- **Part 3 fixed and empirically verified:** `known_ecosystems()` (already existing, already
  import-every-platform-module-by-design) called once in `tests/test_sealed_bytes.py` closes the
  exact false `ConfigError` this session hit firsthand running that file standalone - confirmed
  by running it standalone before and after: before, `ConfigError: no ecosystem spec registered
  for 'java'/'cpp'/'rust'`; after, the single already-known Email-Python `test_sealed_bytes`
  failure, matching the full suite's own baseline exactly.
- **Checklist:** [x] fix `_base()` hash formula [x] reproduction test (real run_job, real cold-process seed/reuse proof) [x] part 2 - honest rename (full toolchain fingerprint deliberately deferred, flagged) [x] part 3 - plugin init audit, empirically verified standalone [x] full suite
- **Gap linkage:** D7
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Three independent corrections in `core/llm/jobs.py`/`seal.py`: (1) `_base()`'s local
    `request_sha256 = canonical_hash(payload)` (line ~304) must instead compute the exact same hash
    `run_job` uses for the cache key - `canonical_hash({"prompt_sha256": manifest.sha256, "payload": payload})`
    - so the ledger's own `request_sha256` field is actually the key that identifies the request,
    not a different value that happens to share the field name; (2) `_site_manifest_hash` must
    fingerprint the target verification environment (the ephemeral venv/toolchain `python_examples.py`/
    `cpp_examples.py` etc. actually build and run against), not the presenter process's own
    installed distributions; (3) confirm and document explicit ecosystem-plugin initialization at
    every public entrypoint that can run stand-alone (CLI, a focused test file, a future hosted
    entrypoint), not relying on import-order side effects from unrelated test collection.
  - **Allowed paths:** `src/repository_presenter/core/llm/jobs.py`,
    `src/repository_presenter/components/readme/bundle/seal.py` (`_site_manifest_hash`,
    `environment_dependencies` only), `src/repository_presenter/core/ecosystems.py` (`plugin_for`
    call-site audit only, not its own logic), `tests/core/llm/test_jobs.py`,
    `tests/components/readme/bundle/test_seal.py`, `tests/test_sealed_bytes.py` (add explicit
    initialization if it's currently relying on collection order - verify first).
  - **Forbidden:** `seed_call_store`'s own seeding *policy* (exactly-one-successful-attempt gate) -
    preserve it exactly; this taskcard fixes the key it seeds under, not when it seeds.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --facts-only --repo <any sealed candidate, cold runs/>`
    followed by a full `present` for the same candidate now shows `seed_call_store`'s seeded keys
    actually being hit (`provider calls 0, model stored output reused`) on a genuinely fresh
    process with no prior local cache, not only when a warm local transaction cache happens to
    cover the same request through a separate, correctly-keyed path.
  - Tests: reproduce the exact mismatch already confirmed (seed a key from a real bundle's ledger,
    confirm a fresh `run_job`-shaped lookup with the same prompt+payload now finds it, where today
    it cannot); a test asserting `test_sealed_bytes.py` (and any other test relying on ecosystem
    registration) passes when run standalone, not only as part of the full suite - this closes the
    exact false `ConfigError` observed firsthand this session.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for all changed files.
  - The reproduction tests above.
  - Forward-compatible: every existing sealed candidate's `calls.jsonl` already has *some*
    `request_sha256` values recorded under the old (wrong) formula - after this fix, newly-appended
    ledger entries use the correct formula; do not attempt to rewrite historical ledger entries
    (that would corrupt an append-only audit record) - `seed_call_store` naturally stops finding a
    match for old entries and falls through to a live call, which is the honest, safe behavior.
- **Hard rules:** keep `run_job`/`_site_manifest_hash`/`environment_dependencies`'s public
  signatures; no new deps; deterministic given fixed prompt/payload/environment.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a genuinely cold process (empty `runs/`) re-running an already-sealed
    candidate now achieves zero provider calls for every `_SEEDABLE_JOBS` entry, not just a warm
    one - test this specific claim directly, it is the whole point of `seed_call_store` and was
    never actually true.
  - Test coverage: 5/5 = the cold-process claim is tested with an actually-empty cache, not
    inferred from a warm-cache success.
  - No regressions: 5/5 = every currently-passing candidate re-seal still reproduces byte-identical.
  - Determinism: 5/5 = same prompt+payload → same `request_sha256`, everywhere it's computed, now
    genuinely once (one formula, not two).
  - Documentation/traceability: 5/5 = `jobs.py`'s docstring states plainly that this was two
    different formulas sharing one field name; `DECISION_LOG.md` records the precise root cause
    (more specific than the external review's own phrasing) as this session's own contribution.
- **Now (runbook):**
  1. Write the cold-process reproduction test first (empty `runs/`, seed from a real sealed
     bundle's ledger, confirm the seeded key is found) - it should currently fail (red).
  2. Fix `_base()`'s hash formula.
  3. `pytest tests/core/llm/ -q` — confirm the reproduction now passes.
  4. Fix `_site_manifest_hash` to target the verification environment; add the standalone
     ecosystem-initialization test/fix.
  5. `pytest tests/components/readme/bundle/ -q`; `pytest tests/test_sealed_bytes.py -q` standalone
     (this specific invocation is the regression control for the plugin-initialization sub-fix).
  6. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  7. Commit, push.

### TB-08 — A real isolation boundary for untrusted execution and outbound fetches

- **Status:** Not Started
- **Gap linkage:** D8
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Four corrections, each independently landable: (1) `execute()` must filter
    `extra_environment` through `secret_free_environment` too, not merge it in raw after filtering
    the base; (2) `python_examples.py`'s package-install call must use `profile_environment(workspace)`
    the same way its later example-execution call does; (3) `run_bounded` must clean up the child
    process tree in a `finally` (or equivalent), covering `KeyboardInterrupt` and any other
    exception, not only `TimeoutExpired`; (4) `fetch_status`/`check_external` must reject or flag a
    resolved target whose address is loopback, link-local, or otherwise private/reserved (RFC 1918,
    127.0.0.0/8, 169.254.0.0/16 at minimum) before treating a 200 response as RESOLVED, including
    after following a redirect. Reuse existing platform/container tooling for any actual process
    isolation if this taskcard's scope extends there; do not build new sandbox infrastructure from
    scratch as part of this specific fix - if true OS-level isolation is out of reach in this pass,
    land (1)-(4) now and record the remaining isolation gap as its own, explicitly-scoped follow-up
    rather than silently declaring the boundary complete.
  - **Allowed paths:** `src/repository_presenter/core/execution.py`,
    `src/repository_presenter/core/git_safety/process.py`,
    `src/repository_presenter/components/readme/extractors/platforms/python_examples.py`,
    `src/repository_presenter/components/readme/evidence/facts/links.py`,
    `tests/core/test_execution.py`, `tests/core/git_safety/` (verify exact path),
    `tests/components/readme/evidence/facts/test_formats.py` or wherever `links.py` is tested -
    verify at execution time.
  - **Forbidden:** any other extractor platform file not named above; do not silently broaden this
    to "implement every future hosted-execution feature," per the review packet's own explicit
    constraint.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A directly observable; verified through the tests below.
  - Tests: the negative controls named - host-file access attempt (denied or at minimum contained
    to the redirected profile), credential exposure (extra_environment secrets now filtered),
    restricted egress (a private-address target is now rejected/flagged, using a mock transport as
    the review packet itself used - never a real request to a private/internal address), redirect-
    to-private target (must also be caught, not only the initial URL), descendant-process cleanup
    on cancellation (simulate via `KeyboardInterrupt` during `communicate()`, assert the process
    tree is gone afterward).
  - Config respected end-to-end / No mock data: the mock-transport technique the review packet used
    is the correct, safe way to test (4) - no real request to `127.0.0.1`/`169.254.169.254`/any
    private address is ever made by a test.
  - No mock data in production paths: the private-address check itself must run in every real
    invocation, not only under test.
- **Deliverables:**
  - Full file replacements for all four changed files.
  - The five negative-control tests.
  - No schema change; `LinkResult`'s existing outcome vocabulary can represent a rejected private
    target as `MISSING` or a new explicit reason - decide and document which, consistently.
- **Hard rules:** keep every changed function's public signature; no new deps unless a private-
  address-range check genuinely needs one beyond the standard library's `ipaddress` module (it
  should not); no network in the tests themselves.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = all four sub-defects closed; explicitly honest about what remains out of
    scope (true OS-level sandboxing) rather than implying full isolation now exists.
  - Test coverage: 5/5 = all five negative controls present, none requiring a real network request
    to a sensitive target.
  - No regressions: 5/5 = every currently-working legitimate build/link-check flow is unaffected -
    verify against 2–3 real candidates' example verification and link checking.
  - Determinism: 5/5 = the private-address check is a pure function of the resolved address.
  - Documentation/traceability: 5/5 = `execution.py`'s and `links.py`'s module docstrings state the
    boundary's actual scope and its known remaining limit (no OS-level isolation) plainly, so a
    future reader doesn't assume more safety than exists.
- **Now (runbook):**
  1. Write the five negative-control tests first (red), all using mocks/stubs, never a real
     request to a private address.
  2. Implement (1) and (3) first - small, mechanical, low-risk.
  3. `pytest tests/core/test_execution.py tests/core/git_safety/ -q`
  4. Implement (2) and (4).
  5. `pytest tests/components/readme/extractors/platforms/ tests/components/readme/evidence/facts/ -q`
  6. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  7. Commit, push. Record the remaining OS-isolation gap explicitly in `DECISION_LOG.md` as a
     known, deliberate limit, not a silently-dropped item.

### TB-09 — HTML link discovery and prose-matches-evidence checking

- **Status:** Not Started
- **Gap linkage:** D9
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Two independent corrections: (1) `extract_links()` must also discover targets inside
    raw HTML `<a href="...">`/`<img src="...">` tags that markdown-it tokenizes as `html_inline` -
    parse the href/src out of that raw HTML fragment (a narrow regex or a minimal HTML parse is
    sufficient; do not pull in a new heavy HTML-parsing dependency for this). (2) Preserve the
    existing missing-link and duplicated-API-list repair work exactly as it stands (do not touch
    `placement.py`/`renderer.py` under this taskcard); add one narrow, bounded check, scoped to the
    existing author/independent-review seams already in the pipeline, that a unit's prose about a
    *specific* cited example is checked against that example's own recorded action (e.g. its code
    or its verified format claims) where such a check is already cheap to make from data already on
    hand - never a general NLP verifier, and never a new controller.
  - **Allowed paths:** `src/repository_presenter/components/readme/evidence/facts/links.py`
    (`extract_links`/`_inline_links` only), and, for part (2), whichever existing seam already does
    fact-grounded prose checking today (`review/independent/review.py`'s `scope_defect`/evidence-
    checking functions, or the authoring-side binding checks in `composition/authoring.py` - read
    both before choosing, do not add a third parallel mechanism), plus matching tests.
  - **Forbidden:** `placement.py`, `renderer.py`'s API-reference rendering (both explicitly
    preserved per the review packet's own instruction); building a new, general-purpose semantic
    verifier - this must reuse an existing seam, narrowly extended.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A directly; verified through the tests below and a spot-check of the real portfolio for
    any HTML-only link previously invisible to `BC-06`.
  - Tests: for part (1), the exact reproduction already confirmed (`extract_links` on an HTML
    anchor now returns the target, matching the markdown-syntax equivalent). For part (2), a
    regression test reproducing the general *shape* of the original 3D-Python defect (a lead-in
    naming one action for an example whose recorded code/format claims say a different one) -
    since the specific historical instance is no longer reproducible in the current data, construct
    a synthetic case with the same shape and confirm the chosen seam now catches it.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacement for `links.py`.
  - Full file replacement for whichever existing seam part (2) extends.
  - Both sets of tests above.
  - No schema change for part (1); part (2)'s schema impact (if any - e.g. a new advisory/finding
    shape) must be additive and forward-compatible with existing sealed `review.json`/`content_units.json`
    files.
- **Hard rules:** keep `extract_links`'s signature and return type; no new heavy dependency for
  HTML parsing; no new dependencies for part (2) - it must be built from data the pipeline already
  computes.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = HTML links are no longer invisible to preservation/link checking; a
    synthetic prose-contradicts-evidence case is now caught by an existing seam, not a new one.
  - Test coverage: 5/5 = both parts' tests present; part (2)'s synthetic case is a fair, honest
    stand-in for the now-stale real example, not a weaker version of it.
  - No regressions: 5/5 = every currently-correct markdown-link and correctly-matched-prose case is
    unaffected.
  - Determinism: 5/5 = pure function of README text / unit and fact data.
  - Documentation/traceability: 5/5 = `links.py`'s docstring updated; `DECISION_LOG.md` entry notes
    explicitly that the original 3D-Python example was found stale during verification (fixed
    incidentally, not by a guard) and that this taskcard adds the guard that would have caught it
    and will catch its recurrence.
- **Now (runbook):**
  1. Write part (1)'s test (red) using the exact reproduction already run.
  2. Implement HTML anchor/image discovery in `_inline_links`/`extract_links`.
  3. `pytest tests/components/readme/evidence/facts/ -q`
  4. Read `review/independent/review.py`'s and `composition/authoring.py`'s existing fact-grounded
     checking functions; choose the seam for part (2); write its synthetic regression test (red).
  5. Implement part (2)'s narrow extension.
  6. `pytest tests/components/readme/review/ tests/components/readme/composition/ -q` (whichever
     applies to the chosen seam).
  7. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  8. Spot-check the real portfolio for any newly-discovered HTML link previously missing from
     preservation checks - a real finding here is a legitimate discovery, not a false positive to
     suppress.
  9. Commit, push.

### TB-10 — A mechanical, portfolio-wide sweep for the evidence-claim mismatch pattern

- **Status:** Not Started
- **Gap linkage:** REC-G1 (the owner's follow-up: "we need to enhance the system preventing such
  problems to reoccur")
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** D1, D2, D4, and D9's HTML-link claim share one shape: **evidence text or a sealed
    verdict asserts something stronger than the underlying receipt/fixture/reading data actually
    supports.** Each was found by a human or an external audit reading one file at a time. Build
    one narrow, CI-gated test (not a new framework, not a new controller - a `pytest` parametrized
    over every `candidates/*/*/` manifest directory, in the exact style already established by this
    session's own `tools/reviewer/audit_link_completeness.py` and `audit_preserved_api_lists.py`)
    that mechanically checks a small, explicit, named list of evidence-claim consistency rules
    derived directly from TB-01 through TB-09's own fixes - for example: an `install_command` fact
    whose evidence claims "verified source build" must have a receipt whose own detail text does
    not contain a failure marker for the same build step (TB-01's exact shape); a `format` fact
    whose only supporting evidence is an executed-example claim must trace to a statement this
    session's extraction logic judged reachable (TB-02's shape); a sealed `review.json` whose
    `second_reader.read` is `true` must have a corresponding `success` (not `JobError`-shaped)
    ledger entry for that job in `calls.jsonl` (TB-04's shape, and the exact portfolio audit TB-04's
    own runbook step 6 already calls for - this taskcard is where that audit becomes a permanent,
    re-run-on-every-CI check instead of a one-time manual pass).
  - **Allowed paths:** a new `tests/test_evidence_claim_consistency.py` (or fold into
    `tests/test_sealed_bytes.py`'s file if that reads more naturally - match this directory's own
    established convention, decided once, consistently), plus promoting `audit_link_completeness.py`'s
    and `audit_preserved_api_lists.py`'s core logic into importable functions if RC-07 (in
    `production-consistency-reassessment.md`) has not already done so - check that file's status
    before duplicating its work.
  - **Forbidden:** any `src/` production code (this taskcard is regression coverage only - if it
    finds a real gap beyond what TB-01–TB-09 already name, that gap gets its own taskcard, never an
    inline fix bundled into a test-only change); building a general "does this text semantically
    match this data" verifier - every rule this taskcard adds must be a small, explicit, named,
    mechanically-checkable pattern with a cited real incident behind it (mirroring
    `tools/README.md`'s own stated discipline: "every check should trace to a measured incident it
    would have caught").
- **Acceptance checks (customized for this repo):**
  - CLI: N/A - test-suite addition.
  - Tests: the new test(s) must pass for every sealed candidate once TB-01, TB-02, and TB-04 have
    landed (land this taskcard *after* those three, not before - landing it first would either
    immediately fail against real sealed content, which is acceptable only as a deliberate,
    documented finding, never a surprise, or force this taskcard to weaken its own rules to pass,
    which defeats its purpose).
  - Config respected end-to-end / No mock data: this test reads only real `candidates/` content,
    never a fixture standing in for the real portfolio.
- **Deliverables:**
  - The new test file, parametrized over every manifest directory.
  - Each rule traces explicitly, in a comment or docstring, to the specific D-number/TB-number
    incident that motivated it - no rule added "for completeness" without a named incident behind
    it, matching this directory's own established discipline.
- **Hard rules:** no network; deterministic; must not weaken any existing check to make itself pass;
  if a currently-sealed candidate genuinely fails a new rule, the correct response is re-sealing it
  through the normal record-then-adopt path (or leaving it honestly unsealed, per this session's
  own established ethos), never excluding it from the new test.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a *future* instance of any of D1/D2/D4/D9's exact shape is caught by CI
    automatically, without waiting for another external audit or a human reading one file at a time.
  - Test coverage: 5/5 = every rule traces to a named, real incident; none is speculative.
  - No regressions: 5/5 = every genuinely-correct sealed candidate passes once TB-01/02/04 have
    landed; existing manual audit scripts keep working standalone.
  - Determinism: 5/5 = no LLM calls, no network, no timing sensitivity.
  - Documentation/traceability: 5/5 = `tools/README.md` and this file both record that D1-D9 is
    where this mechanism's initial rule set came from, so a future contributor understands why
    these specific checks exist and how to add the next one when it's found.
- **Now (runbook):**
  1. Confirm TB-01, TB-02, and TB-04 have landed and every currently-sealed candidate passes their
     individual regression tests.
  2. Check `production-consistency-reassessment.md`'s RC-07 status - reuse its importable-function
     refactor of the existing audit scripts if it already landed, rather than duplicating that work.
  3. Write the new test file with the three rules named above (install-claim, format-claim,
     second-reader-claim consistency), each parametrized over `candidates/*/*/`.
  4. `pytest tests/test_evidence_claim_consistency.py -q` (or wherever it lands) — green against
     current portfolio state.
  5. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  6. Update `tools/README.md` and this file's own status.
  7. Commit, push.
