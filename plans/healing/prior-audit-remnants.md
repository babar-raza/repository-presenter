# Prior-Audit Remnants — Taskcards

## Context

While compiling a complete, prioritized gap list on 2026-09-09, a direct re-read of
`docs/DECISION_LOG.md`'s own recorded verdicts (the fact-checked conclusions from the first two
external-review rounds — AUD-001–005/REC-001–009, and R1–R6 — both predating the D1–D9 packet
`trust-boundary-corrections.md` covers) surfaced five real, CONFIRMED gaps that were never
converted into a Taskcard anywhere. They existed only as prose. This file closes that coverage
gap.

**R5 (PA-01) is the most consequential item in this file** and the one most likely to be
confused with something already fixed: `trust-boundary-corrections.md`'s TB-07 (part 1, landed
`511e5e5`) fixed a *different*, narrower instance of the same cache-key-identity family of bugs
(the ledger's own `request_sha256` field used the wrong hash formula). R5 lives in the primary
session's still-stashed, uncommitted G5-W02 work (`stash@{0}`) and was never landed. Its own diff
(read directly via `git stash show -p`, not assumed from the prose description) shows it
independently fixes the *same* `seed_call_store` mismatch a third way (reading the always-correct
`logical_call_id` field instead of `request_sha256`) — compatible with, not conflicting with,
TB-07's fix — **and** adds a genuinely new, currently-uncommitted feature
(`reconstructed_task_output`, a `section_authoring`-level cache-seeding optimization) that carries
its own, separate, confirmed integrity gap. Both must be understood together; PA-01's taskcard
below covers landing the good part and fixing the gap in the same pass, not just the gap in
isolation.

## Gap table

| Gap ID | Description | Taskcard ID |
|---|---|---|
| R5 | `reconstructed_task_output`'s reuse of a sealed bundle's old content is verified only by section+slot name, never by whether the underlying facts that produced it are still the same | PA-01 |
| REC-005 (remainder) | `quote_located` has the identical whole-document-search shape `absence_defect` was fixed for (AUD-002), but was never itself scoped to a finding's own section | PA-02 |
| REC-002 | The portfolio's "N/34" headline count doesn't distinguish sealed / current-code-reproducible / independently-accepted, the exact ambiguity AUD-002 demonstrated matters | PA-03 |
| REC-007 | The G4-W17 arrival list lives embedded inside `state.yaml` prose, a structural re-discovery-latency risk this session hit directly at least once | PA-04 |
| AUD-005 / G3-W02 | Every sealed candidate carries `contract_version: "readme-contract-v1-draft"` and `acceptance_profile_version: null` — the contract-freeze/versioning work item has never run | PA-05 |

## Taskcards

### PA-01 — Land the stashed cache-seeding work, with a real lineage check on the part that needs one

- **Status:** Done — fixed and pushed. Popped `stash@{0}` cleanly (zero file overlap with the
  held 3D-Python canary-floor changes, verified before popping; auto-merged cleanly with TB-04's
  and TB-07's already-landed changes to the same files). Landed the stash's own `seed_call_store`
  (`logical_call_id`-keyed) and `request_hash()` additions as-is. Added
  `_reconstruction_lineage_holds()` to `authoring.py`: a reconstruction is trusted only when the
  sealed bundle's own `dependencies.json` shows both the `section_authoring` prompt's sha256 and
  every cited fact's `canonical_hash` are still bit-identical to what is sealed - reusing the
  exact same hashing this project's dependency-evaluation already trusts, not a new comparison
  mechanism. Caught and fixed for real: `tests/test_cli.py::test_a_changed_prompt_reopens_only_its_stage_and_records_an_update`
  failed against the stash's own code before this check existed (the prompt-changed case, not
  just the fact-changed case originally designed for) and passes with it.
- **Checklist:** [x] pop the stash cleanly [x] land the good `seed_call_store`/`request_hash` work
  [x] add the lineage check (facts AND prompt, both needed - the live test caught the prompt case)
  [x] regression tests (new synthetic pair + the pre-existing live integration test now passing)
  [x] full suite - only the 2 pre-existing known failures
- **Gap linkage:** R5
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Two parts, landed together because they are one stashed diff:
    1. **Land as-is (already correct, already tested in the stash):** `seed_call_store` reading
       `logical_call_id` instead of `request_sha256`; the new `request_hash()` helper in
       `core/llm/jobs.py`; `cli.py`'s `sealed_bundle=` wiring into `TransactionInputs`. These are
       compatible with TB-07's already-landed fix (TB-07 corrected what `request_sha256` itself
       computes; this reads a different, already-correct field instead — belt and suspenders, not
       a conflict — confirmed by direct diff inspection, not assumed).
    2. **Fix before landing (the confirmed gap):** `reconstructed_task_output`'s reuse in
       `rounds.py` (the `if tx.sealed_bundle is not None: ... tx.store.put(task_hash, ...)` block)
       trusts a section+slot name match alone. Add a real check: after reconstructing candidate
       units from the sealed bundle, compare the *sealed* facts each reconstructed unit actually
       cites (`unit["fact_ids"]`, resolved against the **sealed bundle's own** `facts.json`) to
       what those same fact IDs resolve to in the **current** `FactsDocument` — same value, same
       polarity, for every cited ID. If any cited fact's value or polarity has changed, or a cited
       ID no longer exists, the reconstruction is stale: return `None` (fall through to a real
       call), never seed the store with it. This is the exact, direct answer to R5's own finding
       ("no check anywhere that the reconstructed content was ever produced by a request matching
       that hash") — a request matches when the facts it would be built from are unchanged.
  - **Allowed paths:** `src/repository_presenter/cli.py`,
    `src/repository_presenter/components/readme/bundle/seal.py`,
    `src/repository_presenter/components/readme/composition/authoring.py`
    (`reconstructed_task_output` only),
    `src/repository_presenter/components/readme/repair/rounds.py`,
    `src/repository_presenter/core/llm/jobs.py` (`request_hash` only — already added by the
    stash, do not re-derive), plus the four stashed test files
    (`tests/components/readme/bundle/test_seal.py`,
    `tests/components/readme/composition/test_authoring.py`, `tests/test_cli.py`) and one new
    test module if the fact-comparison logic is substantial enough to warrant its own tests
    separate from `test_reconstructed_task_output_rebuilds_one_tasks_own_content`.
  - **Forbidden:** `core/llm/jobs.py::_Attempts._base()` (TB-07's own fix; do not touch again);
    any change to `content_units.json`'s or `facts.json`'s schema — this taskcard reads both
    documents, it does not restructure either.
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present` against an already-sealed revision, run from a genuinely
    empty `runs/` directory (the stash's own new test,
    `test_present_from_an_empty_runs_directory_reuses_a_sealed_bundle`, already does exactly
    this), shows the non-batch `section_authoring` tasks costing zero provider calls; a *second*
    scenario — the same revision but with one fact's value changed since the seal (simulate by
    editing the sealed bundle's own `facts.json` in a `tmp_path` fixture, never a real candidate)
    — must show that task costing a real call, not a stale reuse.
  - Tests: the four stashed tests, unmodified where they already pass; the fact-comparison logic
    gets its own regression pair — a matching-facts case (reconstruction accepted) and a
    changed-fact-value or changed-polarity case (reconstruction rejected, falls through to a real
    call) — using real `FactsDocument`/`content_units.json` shapes, not placeholders.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:**
  - Full file replacements for the five `src/` files above (the stash's own diff for four of them,
    plus the new fact-comparison logic added to `reconstructed_task_output` or its call site —
    decide which module owns the check by where the sealed bundle's `facts.json` is most
    naturally already loaded, do not duplicate a `FactsDocument` loader).
  - New/updated tests: the stash's own four files, plus the changed-fact regression pair above.
  - Forward-compatible: no schema change; this only adds a stricter internal condition for when a
    reconstruction is trusted.
- **Hard rules:** keep every touched function's public signature (the stash already does this —
  `reconstructed_task_output`, `request_hash`, `seed_call_store` all keep their existing
  signatures); no new deps; deterministic (the fact-comparison is a pure function of two
  `FactsDocument` snapshots).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = a reconstruction is only ever trusted when the facts it would have been
    built from are provably unchanged — verified with a real changed-fact test case, not just the
    happy path.
  - Test coverage: 5/5 = the stash's own four tests plus the new changed-fact pair, all passing.
  - No regressions: 5/5 = every currently-sealed candidate's re-seal behavior (record-then-adopt,
    zero-provider-call proof) is unaffected when nothing about its facts has changed.
  - Determinism: 5/5 = same sealed bundle + same current facts → same accept/reject decision, every
    run.
  - Documentation/traceability: 5/5 = `reconstructed_task_output`'s docstring states the lineage
    check explicitly, citing R5; a `DECISION_LOG.md` entry records that R5 is now fixed and cites
    this taskcard, superseding the "must not land as-is" flag.
- **Now (runbook):**
  1. `git stash show -p stash@{0}` — re-confirm the diff is still exactly what was inspected
     (nothing else may have touched the stash between now and then).
  2. `git status` — confirm a clean tree before popping (this project's own explicit rule: never
     pop a stash into a dirty tree).
  3. `git stash pop` — apply the four-file diff; resolve if `core/llm/jobs.py` conflicts with
     TB-07's already-landed change (expected to apply cleanly — different regions of the same
     file, confirmed by inspection — but verify, don't assume).
  4. `pytest tests/components/readme/bundle/test_seal.py tests/components/readme/composition/test_authoring.py tests/test_cli.py tests/core/llm/test_jobs.py -q` — confirm the stash's own tests pass against current `main`.
  5. Design and implement the fact-comparison lineage check; write its two regression tests (red,
     then green).
  6. `pytest tests/components/readme/composition/ tests/components/readme/repair/ -q`
  7. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  8. Append a `DECISION_LOG.md` entry (via `tools/reviewer/research_edit.py`'s `append_entry`)
     closing R5.
  9. Commit, push.

### PA-02 — Scope `quote_located` to the finding's own section, matching `absence_defect`'s fix

- **Status:** Not Started
- **Gap linkage:** REC-005 (remainder)
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `quote_located` (used for direct-quote matching in review adjudication, not just
    absence claims) currently searches the whole document, the identical shape AUD-002 fixed in
    `absence_defect` via `_section_slice`. Apply the same section-scoping: locate a quote within
    the finding's own named section first, falling back to whole-document search only when the
    section heading cannot be located — exactly `_section_slice`'s existing fallback rule, reused,
    not reinvented.
  - **Allowed paths:**
    `src/repository_presenter/components/readme/review/independent/review.py` (`quote_located` and
    call sites only), `tests/components/readme/review/test_independent.py`.
  - **Forbidden:** `absence_defect`/`_section_slice` themselves (already correct; reuse, don't
    duplicate their logic — import or call them directly if the shapes align, write a thin
    section-scoped wrapper only if they don't).
- **Acceptance checks (customized for this repo):**
  - Tests: a regression reproducing the exact AUD-002 shape but for `quote_located` specifically —
    a quote that exists elsewhere in the document (wrong section) must not be treated as located
    within a finding naming a different section; the existing whole-document-fallback behavior
    (section heading not found) stays covered by a no-regression case.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** full file replacement for the changed function(s); the two tests above; no
  schema change.
- **Hard rules:** keep `quote_located`'s public signature unless every call site is updated;
  no new deps; deterministic.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the identical defect class AUD-002 fixed once is now closed everywhere
    it appears in this module, not just where it was first found.
  - Test coverage: 5/5 = both cases present.
  - No regressions: 5/5 = every existing `test_independent.py` case passes unmodified.
  - Determinism: 5/5 = pure function of the candidate text and the finding's section.
  - Documentation/traceability: 5/5 = a one-line note in `absence_defect`'s or `_section_slice`'s
    own docstring that `quote_located` now shares the same scoping, so a future reader doesn't
    have to rediscover the connection.
- **Now (runbook):**
  1. Write the regression test (red).
  2. Apply section-scoping to `quote_located`.
  3. `pytest tests/components/readme/review/ -q`
  4. `pytest tests/ -q --tb=no` (full suite, once) — only pre-existing known failures.
  5. Commit, push.

### PA-03 — Report sealed / reproducible / accepted as distinct counts, not one headline

- **Status:** Not Started — **needs a short design decision before implementation** (which field
  in `manifest.json`/`status` output is the source of truth for each count), not a rushed addition.
- **Gap linkage:** REC-002
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Wherever the CLI/status reporting currently produces a single "N/34"-shaped headline,
    report the four separately-meaningful counts this session has been computing by hand all
    along (see the 2026-09-08 closure report's own "separately reported" section for the exact
    definitions to reuse, not reinvent): historical sealed pointers; integrity-valid bundles
    (`verify_bundle`, once TB-06 lands — until then, note the caveat); current-code reproducible
    (`test_sealed_bytes`); independently accepted under the current contract (review verdict
    ACCEPT on the current code path). This is a reporting change, not a new computation - every
    number already has a mechanical source.
  - **Allowed paths:** `src/repository_presenter/cli.py` (`status` command output only),
    `tests/test_cli.py`.
  - **Forbidden:** `core/candidates.py`'s counting logic itself beyond what TB-06 already touches;
    this taskcard changes what is *displayed*, not the underlying mechanism (TB-06 owns that).
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter status` prints four distinct counts, each labeled plainly, against
    the real current portfolio (8 current pointers as of 2026-09-09).
  - Tests: a snapshot-shaped test asserting the four counts appear and are computed from the
    expected sources, using a small synthetic portfolio (2-3 candidates) with deliberately
    different values for each count, so the test would fail if any two counts were accidentally
    computed the same way.
- **Deliverables:** full file replacement for the changed CLI output function; the new test.
- **Hard rules:** keep the `status` command's existing flags/signature; no new deps.
- **Review dimensions (5/5 = ):** root-cause fix 5/5 = the four counts are genuinely independent,
  verified by the synthetic-divergence test; test coverage 5/5; no regressions 5/5 = existing
  `status` tests still pass structurally (update their assertions to the new output shape, don't
  delete them); determinism 5/5; documentation 5/5 = `cli.py`'s `status` docstring states what each
  count means.
- **Now (runbook):**
  1. Decide and write down (in this taskcard, one paragraph) the exact source field for each of
     the four counts before writing code.
  2. Write the synthetic-divergence test (red).
  3. Implement the four-count output.
  4. `pytest tests/test_cli.py -q`; `pytest tests/ -q --tb=no` (full suite, once).
  5. Run `repository-presenter status` against the real portfolio; sanity-check the four numbers
     by hand against this session's own prior manual counts.
  6. Commit, push.

### PA-04 — Move the G4-W17 arrival list out of `state.yaml`'s prose into a bounded, structured backlog

- **Status:** Not Started — **structural/process change, needs a deliberate, careful pass, not a
  quick patch; explicitly not to be done hastily** (REC-007's own recorded caution: "a second-
  authority-creation risk of its own if done hastily").
- **Gap linkage:** REC-007
- **Role:** Senior engineer / process owner. Drop-in, production-ready — but read the caution
  above before starting.
- **Scope (only this):**
  - **Fix:** The arrival list (currently a long prose paragraph embedded in one `state.yaml` work
    item's `purpose` field, already past 40+ items) should live in its own structured file
    (YAML or Markdown with stable per-item IDs, matching the numbering already in use) that
    `state.yaml` references by pointer, not by inlining. The exact same content, relocated — this
    is not a rewrite of the list's own items, only where they live. `tests/test_queue_agreement.py`
    (which already enforces "one source of truth" for a different list, §27.9's queue) is the
    precedent to match, not a new mechanism to invent.
  - **Allowed paths:** `project/state.yaml` (the one field, replaced with a pointer), a new
    `project/arrival-list.yaml` (or similarly named) file, `tests/test_queue_agreement.py` or a new
    sibling test enforcing the same "single source of truth, no drift" property for this list.
  - **Forbidden:** rewording, reordering, or renumbering any existing arrival-list item during the
    move — a lossy or reordered relocation would itself be a new defect; this is a structural
    move, verified byte-for-byte content-preserving.
- **Acceptance checks (customized for this repo):**
  - Tests: a new test (mirroring `test_queue_agreement.py`'s shape) asserting `state.yaml` and the
    new arrival-list file agree - no drift possible without a test catching it, the same property
    §27.9's queue already has.
  - Config respected end-to-end: `state.yaml` remains the loop's own live cursor for everything
    else; only this one field's *storage location* changes.
- **Deliverables:** the new structured file; the updated `state.yaml` pointer; the new agreement
  test; a diff proving the full item list transferred without loss (e.g. a line-count or item-ID-
  set comparison before/after, checked once during implementation, not left as a permanent CI
  check unless cheap to keep).
- **Hard rules:** no content loss; no reordering; `state.yaml` schema changes (if any) are
  additive and forward-compatible with whatever currently reads it.
- **Review dimensions (5/5 = ):** root-cause fix 5/5 = the re-discovery-latency risk REC-007 named
  is closed (the list has its own stable, searchable home); test coverage 5/5 = the drift-guard
  test exists and is proven to catch a deliberately-introduced mismatch; no regressions 5/5 = every
  currently-referenced item ID still resolves the same content; determinism 5/5; documentation 5/5
  = `docs/REPOSITORY_LAYOUT.md` gains an entry for the new file.
- **Now (runbook):**
  1. **Read the full current arrival list once, completely, before touching anything** — this is
     the step most likely to be rushed and shouldn't be.
  2. Write the drift-guard test first, against the *current* (embedded) location, to establish a
     baseline that must keep passing through the move.
  3. Create the new structured file; verify byte-for-byte / item-for-item content preservation.
  4. Replace `state.yaml`'s field with a pointer; update the drift-guard test's source location.
  5. `pytest tests/test_queue_agreement.py <new test> -q`; `pytest tests/ -q --tb=no` (full suite,
     once).
  6. Commit, push.

### PA-05 — Freeze and version the acceptance contract (G3-W02)

- **Status:** Excluded from autonomous execution (2026-09-09) — **do not run without explicit
  owner direction.** While preparing to execute this, `project/state.yaml`'s own G3-W02 entry was
  re-read and it explicitly says: "Freeze acceptance contract v1 after every cohort has sealed
  against it (moved behind the cohorts 2026-09-05, section 28.12)." That has not happened - only
  8 of 34 portfolio items are sealed, and G3-W04 (Python cohort second pass) and the G4
  multi-language cohorts are themselves still `PENDING`. This taskcard's own text (authored
  earlier this session from AUD-005's "high, CONFIRMED, still PENDING" verdict) did not check
  that constraint and told a future executor to run it now. Running it now would freeze the
  contract version, and re-seal all 8 current candidates against that freeze, *before* the
  cohorts the freeze is deliberately timed to wait for - preempting a real, dated project-
  sequencing decision, not a style preference. Left Not Started technically, but excluded here
  exactly like RC-06 and the 3D-Python canary floor: a design/timing decision only the owner can
  resolve, not a case for autonomous judgment. AUD-005 itself remains an accurate, still-open
  finding; only the *timing* of its fix is in question.
- **Original status text (superseded by the above, kept for record):** Not Started — "this is the
  largest, least-bounded item in this file; treat the 'Now' runbook's step 1 as a hard gate, not a
  suggestion."
- **Gap linkage:** AUD-005 / G3-W02
- **Role:** Senior engineer. Drop-in, production-ready — for the bounded technical half only; the
  versioning *scheme* itself (what bumps `contract_version`, what bumps
  `acceptance_profile_version`, and under what rule) is a design decision this taskcard must state
  plainly and get confirmed before implementing, not invent silently.
- **Scope (only this):**
  - **Fix:** Every sealed candidate currently carries `contract_version: "readme-contract-v1-draft"`
    (a literal, never-incremented placeholder) and `acceptance_profile_version: null`. Freeze the
    current contract as a real version (e.g. `readme-contract-v1`, dropping "-draft"), define the
    rule for when it increments (a `BC-*` check's meaning changing, a new check added, a check
    removed — never a bug fix that keeps a check's own contract meaning the same), and populate
    `acceptance_profile_version` with a real, incrementing value the same way. Every currently-
    sealed candidate's manifest gets re-stamped with the frozen version through the normal
    record-then-adopt path (a version-only change is a "presentation" classification, not
    "factual" - it does not change any candidate's actual rendered content).
  - **Allowed paths:** `src/repository_presenter/components/readme/bundle/seal.py` (wherever
    `contract_version`/`acceptance_profile_version` are read/written), `docs/README_CONTRACT.md`
    (state the frozen version number and the increment rule in prose), `tests/components/readme/bundle/test_seal.py`.
  - **Forbidden:** changing any `BC-*` check's actual behavior as part of this taskcard - freezing
    the version number is a labeling change; a behavior change is a *different*, separately-tracked
    fix (this file's or `trust-boundary-corrections.md`'s other taskcards) that would itself be the
    next version bump, not bundled into this one.
- **Acceptance checks (customized for this repo):**
  - CLI: every current candidate's `manifest.json` shows a real `contract_version` (not
    `-draft`) and a real `acceptance_profile_version` after re-sealing.
  - Tests: a test asserting the version constants are non-null, non-draft, and that
    `test_seal.py`'s existing coverage of manifest fields is updated to the new values, not
    silently left asserting the old draft string.
- **Deliverables:** the version constants; updated `README_CONTRACT.md` prose stating the increment
  rule explicitly; every current candidate re-sealed through record-then-adopt (an OPS-shaped
  follow-up once the code change lands, tracked in `r1-reseal-operations.md` if it doesn't fit
  cleanly in this taskcard's own runbook).
- **Hard rules:** the increment rule must be written down before any code changes it; no candidate
  content changes as a side effect of this taskcard.
- **Review dimensions (5/5 = ):** root-cause fix 5/5 = AUD-005's exact observation (`-draft`,
  forever null) is closed, with a real rule for future increments, not just a one-time value bump;
  test coverage 5/5; no regressions 5/5 = every candidate's actual rendered content is byte-
  identical before/after (this is a metadata-only change - verify directly, don't assume); determinism 5/5;
  documentation 5/5 = `README_CONTRACT.md` states the rule plainly enough that a future contributor
  knows when to bump which field.
- **Now (runbook):**
  1. **Write the version-increment rule down in `README_CONTRACT.md` first, in plain language, and
     re-read it once before writing any code** - this is the design-decision gate.
  2. Implement the frozen version constants.
  3. `pytest tests/components/readme/bundle/test_seal.py -q`
  4. `pytest tests/ -q --tb=no` (full suite, once).
  5. Re-seal every current candidate (record-then-adopt, sequential, never parallel - this
     project's own established discipline) to pick up the new version stamp; confirm every
     candidate's actual `README.md` bytes are unchanged (a version-only classification should
     never touch rendered content).
  6. Commit, push.
