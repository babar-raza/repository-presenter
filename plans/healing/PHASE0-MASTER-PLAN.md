# Master plan: close the internal-reliability gap, resume portfolio expansion, and sequence what comes after

_Companion channel files: `plans/healing/loop-status.jsonl` (executor appends progress here),
`plans/healing/loop-instructions.jsonl` (monitoring session appends steering here). See the bottom
of this file for the protocol. This plan supersedes nothing in `plans/healing/EXECUTION-PLAN.md` /
`remaining-execution-plan-items.md` / `ci-staleness-followup.md` — read those too for full current
state; this file is the execution sequence for the next concrete phase of work._

## Context

Portfolio expansion has stalled at 8/34 sealed candidates. Not from lack of effort — a full day of
real, live-validated fixes landed (RC-06, the mis-hub fix, three re-seals) — but because **every
attempt to expand the sealed set keeps surfacing a new reliability regression before it can complete**:
RC-06 fixed one duplication defect and, on live validation, triggered two new size-ceiling failures
(Taskcards G/H below); the mis-hub fix took three iterations before it stuck; a foundational
stage-reopening bug (Taskcard EVAL-01 below) means some future fixes of this exact shape won't even
get re-exercised against already-sealed candidates once shipped. This is why the portfolio is stuck,
not a string of unrelated bad luck — and it's why this plan leads with closing that gap before
resuming expansion, rather than pushing candidates through around it.

This document has two jobs: (1) give the **forest** — the full roadmap from here to a complete,
deployed portfolio, and the standing rules that make autonomous execution of that roadmap safe — and
(2) preserve the **trees** — the specific, evidence-backed taskcards needed for the immediate next
phase — as a reference appendix, not the headline. Two prior audits feed this plan: a deep live-
validation sweep of RC-06 against 4 real candidates (surfaced Taskcards G/H), and an independent
three-agent audit of all 12 previously-tracked backlog items plus a fresh codebase read (surfaced
Taskcard EVAL-01 and five smaller items). Both are cited by finding, not re-derived.

---

## The forest: five phases from here to a complete, deployed portfolio

```
Phase 0            Phase 1              Phase 2             Phase 3            Phase 4
Internal      →    Resume portfolio →   G5: rerun         → G6: proposal   →   G7: production
reliability        expansion            durability +         effect proof      deploy +
(now)              (8/34 → all          hosted op proof                       continuous
                   processable          (act-proven                          operation
                   candidates)          monitor/present)
```

- **Phase 0 (now)** — fix the reliability defects that make fixes not stick: an urgent live
  regression (Taskcard H), a foundational stage-reopening bug that silently defeats future coverage
  fixes (Taskcard EVAL-01), a real architectural size limit (Taskcard G), and a cluster of smaller,
  well-scoped gaps. Nothing in Phase 1 should resume at scale until Phase 0's urgent items ship.
- **Phase 1** — resume the candidate-by-candidate, cohort-by-cohort expansion this plan exists to
  unblock. Governed by the same one-candidate-at-a-time, live-validate-before-trust discipline already
  proven this session, now with the Phase 0 fixes underneath it and a real progress-reporting metric
  (Taskcard PA-03) instead of a single opaque headline.
- **Phases 2-4** — already named and scoped at a high level in this project's own documentation
  (`docs/EXECUTION_STATE_MACHINE.md`'s G5/G6/G7), not invented here. Genuinely future work, gated on
  Phase 1's own exit condition, and **not designed in this plan** — see "Phases 2-4" below for why,
  and what's real vs. undecided about them today.

**Open item to resolve at the start of Phase 1, not assumed**: the portfolio is tracked both as
"8/34" (this session's own `status` output) and, in `project/state.yaml`, G4's exit predicate reads
"31/31 local, census recorded." These may be the same 31 processable candidates plus 3 accounted for
differently (already sealed under an earlier gate, or excluded by policy), or the 34 figure may
include repositories G4's own scope doesn't cover. Confirm which, directly against
`project/state.yaml` and `project/lanes/*.yaml`, before reporting Phase 1 progress against either
number — don't silently pick one.

---

## Autonomous execution framework (applies to every step, every phase — stated once, not repeated per taskcard)

This plan is meant to run unattended. Three rules make that safe, matching what this project has
already proven works this session (RC-06's own three-iteration mis-hub saga; the reconciliation-
coverage investigation's reverted fixes) and what the audits above found missing (item 35; EVAL-01).

**1. Pilot-proof, always, before "Done"**
No taskcard is complete on the strength of its unit tests alone. Every fix must be exercised against
at least one real, live candidate transaction — not a synthetic fixture — before being marked shipped,
and where the taskcard names a specific candidate that motivated it (e.g. Taskcard H against PDF-Java),
that exact candidate is the non-negotiable pilot, not a stand-in. Two extra rules the audits surfaced
the hard way:
  - **Validate against a size/shape extreme, not just the motivating candidate.** Every reliability
    regression found this session (Taskcards G, H, and the mis-hub fix's own reverted attempts) is a
    fix that worked on the candidate that motivated it and broke on a different one. Before calling
    any packet/schema-construction change Done, check it against the portfolio's current largest
    candidate by the relevant dimension (symbol count, unit count, etc.), not only the original
    motivating candidate.
  - **Never force, never retry speculatively.** A genuine rejection (`BC-*` failure, `BC-10` reject) is
    signal, not an obstacle — revert and document, per `docs/RECONCILIATION_COVERAGE_ASSESSMENT.md`'s
    and `docs/CI_AND_STALENESS_ASSESSMENT.md`'s own precedent. A candidate that cannot cleanly re-seal
    is left stale with a recorded reason, never hand-pushed through.

**2. Self-review against fixed quality dimensions before commit**
Every taskcard gets checked against the same five dimensions before it's considered ready to commit —
this is the rubric the EVAL-01 taskcard (Phase 0 appendix) already used, generalized here to apply
everywhere:
  - **Root-cause, not symptom** — does the fix close the actual mechanism, or relabel the failure?
  - **Test coverage** — new tests that fail pre-fix and pass post-fix, not just pass post-fix.
  - **No regressions** — existing, currently-passing behavior (other candidates, other checks) is
    re-verified unchanged, not assumed unchanged.
  - **Determinism** — where the fix touches anything LLM-facing, its own output shape must not
    introduce new non-determinism beyond what already exists (e.g. `BC-10`'s own accepted instability).
  - **Documentation** — `docs/DECISION_LOG.md` gets a real entry (what changed, why, what was
    validated against); any stale doc the change touches (a plan file's own "Status" line, a
    `STATE_MACHINE.md` note) gets corrected in the same commit, not left drifting — the buzzing-cherny
    audit found exactly this kind of drift (RC-06's own taskcard still marked "Not Started" in
    `remaining-execution-plan-items.md` after shipping) and it costs real time to re-discover later.

**3. Repo rules, non-negotiable**
  - One taskcard = one commit = one push. Full local suite (`pytest tests/`) after each.
  - Never push without `scripts/ci_check.sh` passing; never bypass the pre-push hook (`--no-verify`)
    except for a specific, already-documented, already-understood reason — never as a default.
  - Route defects through the project's own tracking (state.yaml / arrival-list / plan files /
    `docs/DECISION_LOG.md`) — never patch `src/`/`tests/` outside a scoped, recorded taskcard.
  - `tools/` is never imported by `src/`; `tests/` importing `tools/reviewer/*` is fine (already this
    project's own established direction, confirmed in the buzzing-cherny audit).
  - Owner-gated decisions (marked explicitly below) are never executed autonomously — they get
    surfaced, with options and tradeoffs, and wait.
  - Parallel subagents only for independent, disjoint work (different candidates, different files) —
    never two agents touching `present`/`seal.py` or the same candidate concurrently.

---

## Phase 0 — internal reliability taskcards (what's blocking Phase 1)

Full detail for every row below (root cause, exact fix, test plan, validation bar) is in the appendix.
This table is the forest view: what exists, its state, and the order to run it in.

| # | ID | What it closes | Status | Owner-gated? |
|---|---|---|---|---|
| 1 | **EVAL-01** | Stage-reopening bug: a `shell`/`renderer` version bump reopens `COMPOSING`, reuses stale `RECONCILING` output — future coverage fixes silently won't re-exercise on resealed candidates | **Done, shipped, pilot-proven** (`docs/DECISION_LOG.md` §31, 2026-09-10 10:50 UTC) | No |
| 2 | **H** | Urgent live regression: `c575035`'s unbounded schema-enum breaks `presentation_planning` on the portfolio's largest candidates (PDF-Java confirmed failing now) | **Done, shipped, live-validated** (`docs/DECISION_LOG.md` §31, 2026-09-10 11:19 UTC) | No |
| 3 | **J1** | Structural boundedness test that would have caught H (and G1a) before shipping — ship alongside H | **Done, shipped** (`docs/DECISION_LOG.md` §31, 2026-09-10 11:39 UTC) — 1 genuine pass (H), 5 honest `xfail`s recording real open gaps (link/example enums, G1a's two sites, `undocumented_types()`) | No |
| 4 | A | RC-06: duplicate API-reference content | **Done, shipped, live-validated** | — |
| 5 | B | Mis-hubbed API symbol | **Done, shipped** | — |
| 6 | 3D-Java re-attempt | Confirm RC-06 alone resolves 3D-Java's earlier BC-10 rejection | Not started — cheap, just a rerun | No |
| 7 | Email-Python F07 | Diagnose (not yet fix) why Development/Testing content is missing post-RC-06 | Not started — investigation only | No |
| 8 | C | Give C++'s example verifier Rust's honest `NOT_VERIFIED` relabeling | Not started | No |
| 9 | F (Tiers 0, 4) | Same relabeling for Java/.NET + a non-blocking example-coverage visibility signal | Not started | No |
| 10 | D | Read-only alternate-toolchain investigation for Cells-Cpp's real build failure | Not started | No |
| 11 | G (+ G1a) | Durable `source_reconciliation` batching fix; folds in `reconciliation_schema()`'s own older unbounded-enum twin | Not started — larger, architectural | No |
| 12 | F (Tier 2) | .NET missing-`using` inference | Not started | No |
| 13 | F (Tier 1) | Real cross-snippet stitching for the sibling-fence majority | Not started — highest content-risk item in Phase 0 | No |
| 14 | TB-10+RC-07 | Promote two audit scripts into real `tests/` coverage | Not started | No |
| 15 | PA-03 | Real 4-count progress reporting, replacing the single "N/34" headline | Not started | No |
| 16 | PA-04 | Restructure `state.yaml`'s embedded arrival-list prose into `project/arrival-list.yaml` | Not started | No |
| 17 | E | Investigate: does a non-adopting `present` run wrongly invalidate an already-sealed-good bundle? | Not started — investigation only | No |
| 18 | I | Investigate: is `SYMBOL_MAX_DEPTH`'s fixed threshold under-serving deeply-qualified (Java) naming? | Not started — investigation only | No |
| — | **RC-03** | Citation-completeness gate: hard (blocking) vs. soft (advisory) — both options now designed | Presented, not executed | **Yes — present both options, wait** |
| — | **PA-05** | README-contract version flip (`-draft` → `v1`) | Prep work only; flip itself waits | **Yes — flip is cohort-gated, needs owner signal** |

**Sequencing**: 1→2→3 (EVAL-01, H, J1 — foundational + urgent, minimal delay between them) →
4-5 already done → 6-7 (cheap, unblock specific candidates) → 8-9 (cheap, safe, portfolio-wide honesty)
→ 10 → 11 → 12→13 (F's own internal order: cheaper/safer tiers before the highest-risk one) →
14-16 (process items, fully parallelizable across disjoint files via independent subagents) → 17-18
(low-urgency investigations, pick up whenever). RC-03 and PA-05 get surfaced to the owner in parallel
with this sequence, not blocking it — neither is a dependency of anything else in Phase 0.

---

## Phase 1 — resume portfolio expansion (runbook)

Once Phase 0's urgent items (EVAL-01, H, J1) ship and are pilot-proven:

1. **Resolve the 31-vs-34 count** (see "Open item" above) before reporting progress.
2. **Resume the proven per-candidate loop**: attempt `present` → live-validate against blocking
   checks and `BC-10`'s judgment → real rejection found → stop, don't force, record in
   `docs/DECISION_LOG.md`, open an investigation-only taskcard if the defect is new and open-ended,
   move to the next independent candidate rather than blocking the whole cohort on one.
3. **Cohort order** follows the existing gate structure: finish whatever remains of the current
   in-progress backlog item (G4-W17), then work through the six ecosystem cohorts (.NET/Java/C++/
   TypeScript/Go/Rust) — .NET is currently the most-advanced non-Python cohort. Re-check each
   cohort's real current count directly (`project/lanes/*.yaml`) rather than trusting a stale figure.
4. **Parallelize only across disjoint candidates** (different repos, never the same `present`/
   `seal.py` invocation) — per the framework's own repo-rules section above.
5. **Track real progress** via Taskcard PA-03's four counts once shipped (historical sealed pointers,
   integrity-valid bundles, current-code reproducible, independently accepted under current contract)
   instead of the single headline number — this makes silent regressions (a candidate that was sealed
   but is no longer reproducible under current code) visible instead of hidden inside one aggregate.
6. **Exit condition**: matches G4's own documented predicate in `docs/EXECUTION_STATE_MACHINE.md` —
   confirm the exact wording and number directly before treating Phase 1 as complete.

---

## Phases 2-4 — what's already real, and what isn't (honesty note, no design here)

Per this project's own documentation (`docs/EXECUTION_STATE_MACHINE.md`, `docs/RESEARCH_AND_GUIDELINES.md`
§8.3, `project/state.yaml`) these phases are already named, sequenced, and scoped at a high level —
cited below, not invented for this plan:

- **Phase 2 / G5 — rerun durability and hosted operation**: prove byte-stable reruns, then prove
  `monitor.yml` and `present.yml` locally under `act` (with a `GH_TOKEN`), then host them via a
  GitHub App using a read-only token. Entry condition: all Phase 1 candidates sealed locally, census
  recorded.
- **Phase 3 / G6 — proposal effect proof**: `propose.yml`, the first write-capable workflow (opens or
  updates a presenter-owned PR — this project's docs are explicit that publication is never a direct
  push), proven first against a disposable target repository, then against the real Java cohort.
- **Phase 4 / G7 — production deploy and continuous operation**: App and gateway secrets, a scheduled
  monitor running in read-only observation, plus a named set of explicitly *deferred* surfaces —
  description, topics, community files, release links, visuals, social preview. **No metadata-file
  format or deployment mechanism beyond "PR via GitHub App" is specified anywhere in this project's
  docs today** — "metadata" in this project's own usage refers to README-content elements (e.g. a
  Mermaid diagram label), not a separate deliverable file.

**What this plan deliberately does not do**: design the `act` harness setup, GitHub App scoping,
secret management, or the G6/G7 write-path mechanics. The evidence needed to design those safely
(how the real target repos actually consume a presenter PR today, what secrets/scopes a hosted App
realistically needs, what "act" proof actually catches vs. misses relative to hosted execution) hasn't
been gathered — producing detailed implementation steps now would be exactly the "exaggerated
confidence" this project's own standard requires avoiding. **Recommendation**: treat Phases 2-4 as
real, sequenced, and unblocked-in-principle by Phase 1's completion, but plan each one in its own
dedicated pass, started when Phase 1's exit condition is actually in sight — not now, and not by
guessing today.

---

## Verification (Phase 0, the part actually executing now)

- Each taskcard's own unit/regression tests pass; `pytest tests/ -q` clean; `scripts/ci_check.sh`
  clean before every push.
- Every Phase 0 fix pilot-proven per the framework's own rule 1 — see the appendix's per-taskcard
  validation bar for the specific candidate each one must be checked against.
- `docs/DECISION_LOG.md` gets one real entry per taskcard on completion; this plan file's own Status
  table (above) gets updated in the same pass — not left to drift, per framework rule 2's own
  documentation dimension.
- `git status` clean on every touched candidate directory after any re-seal attempt, adopted or not.

---

## Appendix: Phase 0 taskcard detail (the trees — reference material for execution, not the headline)

### EVAL-01 — fix `evaluate()`'s component-to-stage mapping

**Root cause**: `evaluate()` (`bundle/evaluation.py:67-158`) maps all four `components` keys (`shell`,
`renderer`, `normalisation`, `reviewer_logic`) uniformly to reopening `"COMPOSING"` on a version bump
(`:125-135`). `RECONCILING` runs before `COMPOSING` (`STATE_ORDER`, `:27-35`). `dispositions.py` uses
`shell`'s section functions inside `normalize()`/`placement_errors()`, and `renderer.py`'s coverage
logic is exactly what RC-02 (reverted) and RC-06 (landed) changed — so a `shell`/`renderer` version
bump today reopens `COMPOSING` and silently reuses `RECONCILING`'s stale, cached `dispositions.json`.
`docs/STATE_MACHINE.md` §9 already documents this as a known, "conservative" approximation for
`reviewer_logic` — but it is not actually conservative for `shell`/`renderer`, and this traces directly
to the mechanism behind Email-Python's original F03 investigation.

**Fix**: replace the blanket string with a per-component lookup, mirroring `PROMPT_STATES`'s existing
shape (`:36-43`):
```python
COMPONENT_STATES: dict[str, str] = {
    "shell": "RECONCILING",
    "renderer": "RECONCILING",
    "normalisation": "COMPOSING",
    "reviewer_logic": "COMPOSING",
}
```
`normalisation`/`reviewer_logic` keep current behavior (genuinely correct); `shell`/`renderer` move to
`RECONCILING`, the earliest stage either actually touches.

**Allowed paths**: `bundle/evaluation.py`, `tests/components/readme/bundle/test_evaluation.py`,
`docs/STATE_MACHINE.md` §9 (correct the stale "conservative" claim). **Forbidden**: `seal.py`'s
`upstream_dependencies()`; any component's version constant itself.

**Tests**: assert `evaluate(...).earliest == "RECONCILING"` for a `renderer` bump and for a `shell`
bump (today both would incorrectly read `"COMPOSING"`); explicit control cases proving
`normalisation`/`reviewer_logic` are unchanged.

**Pilot-proof bar**: full suite once post-fix — expect zero behavior change for any *currently* sealed
candidate (this only changes what a *future* version bump reopens), so the real proof is the new test
cases failing red pre-fix and passing post-fix, not a live candidate re-run.

---

### Taskcard H — urgent: `c575035`'s unbounded schema enum

**What happened**: `planning_schema()`'s `hub_properties["symbol_fact_id"]` enum is built directly
from `facts.by_kind("public_symbol")` — no cap, no depth filter — unlike every other packet field,
which routes through `core/facts.py::bounded_records()` (`SYMBOL_MAX_DEPTH`/`SYMBOL_CAP`). For
PDF-Java (24,830 symbols, the portfolio's largest surface by 4.6x), this injects an estimated
~460,256 tokens into the request and produces a real, confirmed HTTP 400 — reverting just this one
field and re-rendering matches the real recorded successful call's `prompt_tokens` to within 0.3%,
validating both the diagnosis and the reconstruction method used to reach it. Every sealed candidate
carries this same tax sized to its own symbol count (3D-Java ~81,792 tokens next most exposed).

**Why it happened**: the fix that introduced this (`c575035`) was live-validated — but only against
Email-Python, the portfolio's *smallest* surface (185 symbols). "Validated against a real candidate"
is not the same as "validated against the portfolio's own size extremes" — the same lesson the
mis-hub fix's own three iterations already taught, one layer further in.

**Fix**: route `hubbable` through `bounded_records()` the same way every other field does:
```python
visible_symbol_ids = {record["id"] for record in bounded_records(facts, {"public_symbol"})}
hubbable = sorted(visible_symbol_ids - mis_hubbed)
```
**Scope**: fix all three unbounded enum sites in `planning_schema()` in the same change —
`symbol_fact_id` (the confirmed break), `link_fact_id`, and the four example-ID enums (currently
dormant, identically shaped, currently low-risk only because no candidate's `link_target`/`example`
population is large yet — not because the code is safer).

**Do not fold in**: `SYMBOL_MAX_DEPTH`'s own cross-ecosystem calibration question (why Java's
fully-qualified naming gets almost entirely filtered before this bug even applies) — track as
Taskcard I, its own investigation, not urgent-fix scope.

**Pilot-proof bar**: live-validate against PDF-Java specifically — the exact candidate that failed —
before Done. Re-run the token-reconstruction estimate against all 8 sealed candidates post-fix,
confirm every one drops back to its pre-`c575035` size.

---

### Taskcard J1 — structural boundedness test (ships with H)

For every confirmed unbounded site — `planning_schema()`'s three (Taskcard H), `reconciliation_schema()`'s
older twin (`unit_id`'s enum + `minItems`/`maxItems`, predates `c575035` by weeks, currently dormant
only because no candidate's `inherited_unit` count is large yet — see Taskcard G1a), and
`reconciliation_packet()`'s own uncapped `"inherited_units"` field — construct two synthetic
`FactsDocument`s differing only in the relevant fact kind's count (one realistic, one 10x that), and
assert the function's own output size grows **sub-linearly**, not proportionally. This is the test
that would have caught `c575035`'s bug before it ever reached a real candidate, expressed as a
structural property, not a hand-tuned number. `undocumented_types()`'s own batch-count-explosion risk
gets the equivalent assertion on call count. Note `bounded_records()`'s own cap logic is hard-wired to
`fact.kind == "public_symbol"` — every other kind passes through with zero limit even at "correctly"
bounded call sites; design the test per-kind, not just "routes through `bounded_records()` = safe."

This closes "item 35" — a real, previously-named `docs/DECISION_LOG.md` audit item (2026-09-06) that
shipped only its timeout half, never its token/packet-size half.

---

### Taskcard G — durable `source_reconciliation` batching (+ G1a)

**RC-06's real, measured contribution** to Cells-Rust's `source_reconciliation` truncation is real
but smaller than first assumed: input packet grows only +0.24%; output/completion is the real
fingerprint (~3x tokens/unit vs. its own prior baseline — splitting one list-block record into N
per-class records multiplies rationale/citation volume). The deeper, pre-existing, RC-06-independent
cause: `SYMBOL_MAX_DEPTH = 3` admits 100% of Cells-Rust's shallow-named symbols into its reconciliation
packet vs. 0.01% of PDF-Java's deeply-qualified ones — already made this packet unusually dense before
RC-06 touched it.

**G1a**: `reconciliation_schema()` has its own, older, unfixed instance of Taskcard H's bug class —
`unit_id`'s enum plus `minItems`/`maxItems` built from raw fact counts, no bounding, predating
`c575035` by weeks. Worse in one respect: `minItems`/`maxItems` *require* exact record counts, so this
inflates required input and output simultaneously — and RC-06 itself grows `inherited_unit` counts
going forward. Fold this fix into G's own batching redesign (correctly-batched design naturally bounds
each batch's own enum); if G's timeline slips, ship this bounding-only fix standalone first — it
doesn't need to wait for the larger redesign.

**Fix direction**: batch `source_reconciliation` the way `section_authoring` already proves works
(`repair/rounds.py:210-233` — one `run_job()` call per section task, not one monolithic call) — a
real, already-proven "too big for one call → split by natural unit" precedent, not a new pattern.
Batch boundary candidate: the source document's own heading groups, via `InheritedUnit.section`
(already computed, currently discarded — the same signal Taskcard F's Tier 1 needs, worth threading
through once for both). Open questions to resolve during implementation, not guessed at here: does
batching lose cross-batch context (e.g. the same symbol cited by two units in different batches)?
What's the real cost/latency tradeoff of more, smaller calls?

**Portfolio risk re-ranking**: Email-Python is the next most exposed candidate (largest relative
RC-06 growth + second-highest symbol density), not the raw-growth leaders. Slides-Python is a latent,
RC-06-*independent* risk (2nd-largest reconciliation packet, 53.5% density, zero unit growth from
RC-06) — worth knowing regardless of this taskcard's own scope.

**Pilot-proof bar**: live-validate against Cells-Rust specifically; a candidate that currently
reconciles in one call must produce byte-identical (or provably equivalent) dispositions after
batching — the real regression risk if batch boundaries lose cross-batch context.

---

### Taskcard C + Taskcard F (Tiers 0-4) — cross-ecosystem example-verification honesty and coverage

**Symptom**: examples fail to compile/execute in isolation with errors naming a variable/import the
fence itself never declares. **Root cause**: `select_examples()` extracts every fenced block as a
fully independent unit, discarding the ordinal/heading-path grouping `inherited.py` already computes.
Only Rust compensates today (`NOT_VERIFIED` relabeling). **Structural weakness**: no automated signal
for this exists anywhere — the one place it could surface (the independent reviewer) is architecturally
designed to suppress it (`excluded_evidence_defect`), correctly, but with the side effect that a
candidate can pass all blocking checks with 6 of 7 examples `CONTRADICTED` and nothing shows it.

**Portfolio blast radius**: 75 total examples, 27 non-`EXECUTED`, 20 (74%) share this shape across
four ecosystems (C++ 5, Rust 6 already relabeled, .NET 6, Java 2). Two corrections to the shape: .NET's
6 are a missing-`using` problem, not undeclared-variable (Java's `_needed_imports()` pattern applies
directly); one Email-Python case references an external file, not a sibling fence — out of scope this
round (Tier 3).

**Tiered fix** (each independently shippable, increasing risk):
- **Tier 0** (= Taskcard C for C++, extended to Java/.NET): relabel the matching diagnostic shape
  `CONTRADICTED`→`UNRESOLVED` per ecosystem. Status-only change, zero effect on `BC-02`/`BC-03`
  (confirmed: neither reads this polarity distinction).
- **Tier 1** (highest risk — its own careful pass, never bundled): thread a `section`/heading-path
  field through `select_examples()`, group sibling fences under the same nearest H2, and for a
  Tier-0-shaped failure, attempt one re-verification with earlier sibling fences concatenated as a
  synthesized preamble before falling back to Tier 0's relabeling. Real verified-example-count
  improvement, not just a status change — but the one tier that risks changing compile-result
  correctness, not just a label.
- **Tier 2**: port Java's `_needed_imports()` pattern to `net_examples.py`. Small, isolated.
- **Tier 3**: explicitly deferred (external-file-reference case) — flag in
  `plans/healing/remaining-execution-plan-items.md`, don't silently absorb into Tier 1.
- **Tier 4**: a non-blocking, portfolio-visible "`N` of `M` examples verified" signal — closes the
  actual visibility gap without touching any blocking check.

**Pilot-proof bar**: Tier 0/2/4 — extend each ecosystem's own verifier test file with positive/
negative/mixed cases. Tier 1 — test against the real, confirmed sibling groups (C++'s `example:002`-
`007`, Java's two pairs) as regression fixtures, asserting exactly which now pass vs. must still fail
(e.g. C++'s real `operator[]` bug must still fail post-stitching).

---

### Taskcard D — Cells-Cpp toolchain investigation (read-only)

Cells-Cpp's real `cmake --build` fails under the available GCC 16.2/MinGW toolchain on a narrow
`<limits>`-include gap. Try an older GCC or Clang if available, without touching code or candidate
state. If a working toolchain is found, the existing `BC-02` check passes honestly under unmodified
code — proceed to normal re-seal. If none succeeds, bring the concrete matrix tried back as a real
decision point (caveated-build-state policy vs. leaving genuinely stale) — don't implement either
without that decision.

---

### Taskcard E — manifest mutation on non-adopting runs (investigation lead)

A plain, rejection-ending `present` run was observed mutating an already-sealed-good bundle's
`manifest.json` (`READY_FOR_PROPOSAL` → `INVALIDATED`) with nothing adopted — traced to `cli.py:536`'s
unconditional call into `seal.py`'s `invalidate_bundle()`. Reproduce against a disposable, throwaway
candidate only (never a real portfolio entry) before designing any fix — the right answer differs
depending on whether this is universal current behavior or a missing reconnaissance-mode flag.

---

### Taskcard I — `SYMBOL_MAX_DEPTH` cross-ecosystem calibration (investigation, deferred)

`SYMBOL_MAX_DEPTH = 3` admits ~100% of Rust/C++'s shallow-named symbols vs. ~0.01-0.06% of Java's
fully-qualified ones. Unknown, and must be investigated before any fix: does this actually degrade
real Java-candidate quality (sparse Detailed Member Reference sections), or is it a cost-control
tradeoff already working as intended that just looks stark in a raw percentage table? Inspect real
sealed Java candidates' own rendered output first; only design a scaling fix if a real gap is
confirmed, and explicitly close this as "measured, not a problem" if not.

---

### Email-Python F07 (needs a real ID once admitted) — investigation only

Development/Testing section omits CI-matrix (Python 3.10-3.13) and release-tag convention (vYY.M)
detail present in the original, post-RC-06. First step: determine whether this is a facts-extraction
gap (the fact was never captured) or a placement/reconciliation drop (the fact exists, its citing unit
was superseded/excluded) — diff the real upstream README against the sealed candidate's `facts.json`
directly. Do not fix speculatively; diagnose, verify against real data, then design, matching
OPS-04/OPS-05's own established pattern.

---

### 3D-Java OPS-03 re-attempt (line item, not a taskcard)

3D-Java hit the same `BC-10` class as Email-Python, deferred to RC-06 at the time. RC-06 is now Done;
3D-Java has not yet been re-attempted against the landed fix. A `present` re-run, not new engineering —
do it (or explicitly defer with a stated reason) before drafting anything new for this candidate.

---

### TB-10+RC-07 — promote audit scripts into real test coverage

`tools/reviewer/audit_link_completeness.py` and `audit_preserved_api_lists.py` both already expose
`audit_one(manifest_dir: Path) -> list[str]` with an identical call contract — promoting them into
`tests/` is an import, not a rewrite (`tests/` importing `tools/reviewer/*` is an unrestricted
direction; only `src/` importing `tools/` is forbidden). Both audit scripts already glob every
historical revision directory under `candidates/*/*`, broader than `test_sealed_bytes.py`'s own
`CURRENT`-only walk — state that scope explicitly in the new test rather than silently picking one.
Three new rule functions needed (none exist yet): install-claim (`ExampleReceipt.build_verified`
against `_check_install`'s evidence markers), format-claim (covers only the landed reachable-AST-
statement shape, not the reverted fixture-binding gap), second-reader-ledger (≥2 distinct
`request_sha256`/`logical_call_id` values in `calls.jsonl` for `job == "independent_review"` whenever
`review.json`'s `second_reader.read == true`, each terminating `success`/`cache_reuse`).

---

### PA-03 — real four-count progress reporting

| Count | Source |
|---|---|
| Historical sealed pointers | `len({b.repository_dir for b in iter_sealed_bundles(root)})` (`core/candidates.py:64-83`) — needs one new aggregation line |
| Integrity-valid bundles | `verify_bundle(bundle_path)` per `CURRENT` pointer (`core/candidates.py:90-131`) — needs a pass/fail wrapper instead of raising |
| Current-code reproducible | Promote `test_sealed_bytes.py`'s render-and-compare logic into `core/candidates.py::reproducible_candidates()` — does not exist as an importable function today |
| Independently accepted under current contract | `count_current_candidates(root)` minus `stale_candidates(root, ...)` — today's number doesn't exclude known-stale bundles |

Keep `cursor.recorded_candidates`'s existing consistency check pointed at count 4 (the historical
"N/34" figure) so `state.yaml`'s own invariant stays intact. The synthetic-divergence test needs real
fixture scaffolding (a genuine `render_readme()` call against minimal, deliberately-mismatched
synthetic facts/plan/dispositions) — not just `tests/support.py`'s existing `write_bundle` helper.

---

### PA-04 — restructure the arrival-list

`project/lanes/lane-b.yaml`'s `items:` array shape (`{id, status, accepted_at?, evidence,
prerequisites: [...], purpose: '...'}`) is already validated across three lane files in production
use — copy it for `project/arrival-list.yaml`, don't design a new schema. Two decisions to state
explicitly: a `notes:` field for non-numbered narrative asides currently interleaved in `state.yaml`'s
prose (PA-04's own "no content loss" rule needs a home for these); a `lands_with`/`batch_id` field for
items that land together, so batching isn't lost by flattening. Drift-guard test mirrors
`tests/test_queue_agreement.py`'s byte-identity pattern → new `tests/test_arrival_list_agreement.py`.
Update `docs/REPOSITORY_LAYOUT.md`'s `project/` section in the same commit.

---

### RC-03 — owner decision: hard vs. soft citation-completeness gate

Two real options, not one:
- **Hard gate** (the existing taskcard's only previously-offered option): blocking, catches citation
  gaps before seal. Real bug that must be fixed first if chosen: `reconcile_checks` has no `JobError`
  catch in `run_job` (`repair/rounds.py:186-192`, unlike the second-reader path at `:158-166`) — a
  rejection surviving the one bounded re-ask crashes the entire transaction, not just triggers one
  extra re-ask. Combined with `source_reconciliation`'s already-confirmed non-determinism, a candidate
  could seal clean on one run and hard-crash on the next with zero repo change.
- **Soft/advisory gate** (new option): reuse the existing `advisory`-list pattern (`validation.json`,
  `review.json`, both read into `manifest.json`'s quality-cost record with zero effect on outcome) —
  add a `dispositions.json["citation_gaps"]` annotation, written after schema validation, never
  triggering a re-ask or risking the crash above. Closes the *visibility* half (49 real gaps become
  traceable) with none of the hard gate's aggregate-non-determinism cost.

Both share one detection core (backtick-span extraction against known `public_symbol` display names,
reusing `authoring.py:778-779`'s existing primitive), so building soft first and upgrading later is
cheap, not a redo. **This stays the owner's call** — present both, do not pick.

---

### PA-05 — owner decision: README-contract version flip timing

The flip (`"readme-contract-v1-draft"` → `"readme-contract-v1"`) is exact-value-compared in
`evaluate()` (`bundle/evaluation.py:117-152`) — the moment it lands, every currently-sealed candidate's
`VALIDATING`/`REVIEWING` reopens. No staged/flag-gated way around that. Real cohort distance: G3-W04
(10 more Python repos) is `PENDING`; G4-W17 is a 26-item backlog with an explicit "two consecutive
zero-delta boxes, stop and escalate" rule; six ecosystem cohorts each need their own seal count, most-
advanced non-Python (.NET) at 2/6 — realistically weeks-to-months, not days.

**Safe to do now, without triggering the flip**: write the increment-rule prose in
`docs/README_CONTRACT.md` (pure documentation) and the full code diff (version constants +
`test_seal.py` updates), reviewed and ready, with the constant's *value* left unflipped until the
owner signals cohorts have cleared — so the eventual flip is a one-line change, not a design-from-
scratch task. Version convention matches every other component (`RENDERER_VERSION`, etc. — plain
incrementing integers): `CONTRACT_VERSION` increments only when a `BC-*` check's *meaning* changes,
never for a same-meaning bug fix. `ACCEPTANCE_PROFILE_VERSION` (currently `None`) starts at `"1"`.

---

## Monitoring channel protocol

Two append-only JSONL files, single writer each:

- `plans/healing/loop-status.jsonl` — **the executor (Codex loop) appends only.** One JSON object per
  line: `{"ts", "taskcard", "phase": "started|pilot_proof|self_review|done|blocked|owner_decision_needed|new_defect|phase0_complete", "verdict": "pass|fail|n/a", "summary", "evidence", "commit"}`.
- `plans/healing/loop-instructions.jsonl` — **the monitoring session appends only.** One JSON object
  per line: `{"ts", "target_taskcard": "<id or ALL>", "instruction", "ack_required"}`.

The executor reads the full instructions file at the start of every taskcard iteration and applies
any entry targeting its current/next taskcard or `ALL` that it hasn't already satisfied.
