# CI red and seal staleness — a production assessment (2026-09-09)

Triggered by the owner flagging CI as red mid-way through the 2026-09-09 healing pass, and asking
for a deep, production-grade reassessment rather than a local patch, informed directly by the
`foss-readme-optimizer` post-mortem (0/32 candidates ever sealed in 46 days; see
`DECISION_LOG.md`-equivalent context carried in this session). That project's own retrospective
line is the standard this document holds itself to: **"Validation thoroughness did not trade off
against shipping — it substituted for it."** This repository is not there (8/34 candidates are
genuinely sealed), but this pass has the same *shape* of risk, and this document exists to name it
precisely rather than paper over it with another fix.

## 1. Symptoms (what was observed)

- CI (`ruff check`, `ruff format --check`, `mypy src`, `pytest`, entry-point smoke) has been
  failing on every push to `main` since at least 2026-09-07 — before this healing pass started.
- This session's own commits (TB-08 onward) added 2 new `ruff check` violations and left 7 files
  unformatted per `ruff format --check`, plus 2 `mypy` errors — none caught locally, because only
  `pytest` was ever run before a push, never the other three CI steps.
- `test_sealed_bytes.py` locally showed 2 known, already-documented divergences (Cells .NET,
  Email-Python) all session. Checking the same test against **committed HEAD** directly — bypassing
  the working tree — surfaces a **third**: 3D-Python. The working tree's held, uncommitted 3D-Python
  candidate WIP (parked there for the canary call-volume-floor policy decision, unrelated to this
  pass) happens to already contain corrected content, which silently substituted for the real,
  pushed state in every local test run this session.
- CI's four steps run sequentially with no `continue-on-error`; a failure in step 1 (lint) aborts
  the job before `pytest` ever runs. Since lint has been broken since TB-08, **no CI run since has
  told anyone whether the test suite itself passes on Linux** — the signal that matters most has
  been invisible, not merely red.

## 2. Root causes (verified against the repository's own history, not inferred)

### 2.1 An existing, working staleness-tracking discipline was skipped twice this session

This is not a missing mechanism. `RENDERER_VERSION` (`composition/renderer.py`), `SHELL_VERSION`,
`NORMALISATION_VERSION`, `VALIDATOR_VERSION`, and each `Check.version` in
`validation/registry.py`'s `BLOCKING_CHECKS` are a **real, actively-maintained versioning
discipline**: every prior renderer-output change bumped `RENDERER_VERSION` (17 bumps in the
project's history, most recently commit `47cdb14`, well before this pass), and `BC-07`/`BC-10`
have each been bumped before for exactly this reason ("versioned so a change re-checks accepted
candidates" — the `Check` dataclass's own docstring). `docs/STATE_MACHINE.md` section 9
("Invalidation") documents the intended design directly: a dependency-hash change reopens the
earliest affected stage of every candidate that consumed it.

**This session broke that discipline twice, confirmed by direct diff inspection:**
- Commit `81c2f95` (RC-02) changed `_api_reference`'s hub/method grouping in `renderer.py` — a
  change that, by this session's own verification, altered real rendered bytes for two real
  candidates (Cells .NET, Email-Python) — without bumping `RENDERER_VERSION` (still `"17"`, last
  bumped by an unrelated, much earlier commit).
- Commit `0bb967e` (TB-05) changed `_check_examples`'s fence-language comparison and rewrote
  `_fences` to use a CommonMark parser — a real behavior change to `BC-03` — without bumping
  `BC-03`'s `Check.version` (still `"1"`, never bumped, unlike `BC-07`/`BC-10` which correctly were
  when their own logic changed in the past).

This is the direct, mechanical reason 3D-Python's `test_sealed_bytes.py` divergence is invisible
to anything except a raw byte diff: the system that exists specifically to make "this candidate's
inputs changed, it needs re-checking" a structured fact was not fed the fact.

### 2.2 Local verification silently diverged from what is actually shipped

Every `pytest tests/ -q --tb=no` run this session read the **working tree**, which has carried an
indefinite-duration, uncommitted candidate WIP (3D-Python) for the whole pass. That WIP happens to
already contain content matching current code, so it silently absorbed the very divergence
`RENDERER_VERSION`'s discipline (had it been followed) would have flagged mechanically. The
"only the known divergences" claim repeated in this session's own `DECISION_LOG.md` entries and
plan-file notes was accurate *for the working tree*, never verified against the committed,
pushed state until now.

### 2.3 CI's own design hides its signal behind whichever gate breaks first

Four sequential, fail-fast steps in one job mean a broken `ruff check` (a two-line, trivial fix)
has been sufficient to make CI report "red" without anyone — including this session — learning
whether the actual test suite passes on Linux. `foss-readme-optimizer`'s own CI-red discovery
commit ("I did not look at CI until the end of this session... every local claim this cycle made
about a green suite was a claim about Windows") is close to a literal description of what happened
here, except caught mid-pass instead of at the very end.

### 2.4 Nobody was watching CI

Independent of the design flaw in 2.3: `gh run list` was never once run during this pass until the
owner asked. CI existing and CI being observed are different things, and only the second one has
any effect. `foss-readme-optimizer` had 13 workflow files and was still red for its entire life.

## 3. What to preserve

- The `RENDERER_VERSION`/`SHELL_VERSION`/`NORMALISATION_VERSION`/`VALIDATOR_VERSION`/`Check.version`
  discipline itself. It is correct, it is precedented, and it is exactly the mechanism a durable
  design needs — it does not need to be reinvented, only followed and made harder to skip.
- `test_sealed_bytes.py`'s core design: a pure function of on-disk documents, no provider calls, no
  clone, covering every sealed candidate at once. Keep it as the ground-truth byte check.
- The Wave-ordered healing plan's *principle* of not re-sealing mid-fix-storm — resealing every
  candidate after every single fix would be its own kind of thrash. The problem is not that
  resealing is deferred; it is that the deferred set is currently tracked by hand (prose in
  `DECISION_LOG.md`) instead of by the versioning mechanism that already exists for this purpose.

## 4. What is structurally weak and should change

None of the following are new validators, new blocking gates, or new judgment layers over
candidate content — the distinction matters directly against the `foss-readme-optimizer` lesson.
Each item below is either a **reporting/visibility fix** (surfaces a fact that is already true) or
a **process-discipline fix** (makes an existing, correct rule harder to silently skip). None of
them reject a candidate or invent a new acceptance criterion.

1. **`test_sealed_bytes.py` conflates two different questions** — "is this a renderer regression"
   vs. "is this a known, desirable staleness already tracked elsewhere" — and currently answers
   both by asking a human to read a byte diff and write a paragraph about it. A cheap, additive
   report (reads `dependencies.json`'s recorded component/check versions against the running
   code's current constants) turns "which candidates are stale, and on what" into one command's
   output instead of a growing decision-log narrative.
2. **The version-bump discipline has no enforcement**, so it was silently skipped twice in one
   session despite being followed 19 times previously (17 renderer bumps + 2 check bumps). A cheap
   local check — not a CI gate on candidate content, a hygiene check on the *code diff itself* —
   that flags "you touched `renderer.py`'s output-affecting logic without touching
   `RENDERER_VERSION`" closes this gap where it actually occurred: at commit time, for whoever is
   editing, not after the fact via forensic diffing.
3. **CI hides its own signal.** Splitting lint/format/mypy/pytest into independently-reporting
   steps (or parallel jobs) means a broken lint gate never again hides whether the test suite
   passes — this is fixing a reporting blind spot that has existed since before this pass, not
   adding new scope.
4. **Working-tree hygiene**: an indefinite-duration uncommitted candidate WIP sitting in the
   primary working tree makes every local test run unrepresentative of the actually-shipped state.
   This needs to move somewhere the working tree stays clean (a branch, or an explicitly labeled,
   dated stash) — not because the WIP itself is wrong, but because its ambient presence corrupted
   this session's own verification without anyone deciding that trade-off on purpose.

## 5. What NOT to build

- No new blocking check, no new acceptance criterion, no new class of rejection over candidate
  content. Everything above reads existing, already-true facts (a version constant, a CI step's
  own exit code, `git status`) — none of it can invalidate a candidate that isn't already stale by
  the existing rules, and none of it demands new work from a future fix beyond "remember to bump a
  number," which is already the standing rule.
- No redesign of the Wave-ordered healing plan's sequencing principle. The fix is enforcement and
  visibility of the existing rule, not a new rule.

## 6. Concrete implementation, in order

1. **Retroactively correct the confirmed missed bumps** (commit, don't silently patch):
   `RENDERER_VERSION` 17→18 (RC-02's real output change) and `BC-03`'s `Check.version` "1"→"2"
   (TB-05's real behavior change). Done.
2. **Audit this pass's remaining commits against the same discipline**, each checked individually
   against real before/after output, not assumed clean:
   - **RC-01** (`planning.py`'s backstop-table refactor): no bump needed — this session's own
     verification at the time confirmed byte-identical output against the real portfolio, and
     `planning.py` has no existing version constant of its own to bump in the first place.
   - **TB-02 part 1** (`format_claims`'s dead-code exclusion): no bump needed — verified
     hash-identical (zero differences) across all 75 real `example:*` facts in the sealed
     portfolio; extraction-stage fact values are tracked by content hash
     (`upstream_dependencies`'s `facts` dict), not a static code-version constant, so an
     extraction change with zero effect on real fact values leaves nothing stale to flag.
   - **TB-09** (`authoring.py`'s `unit_checks`, gaining `unit_example_action_mismatches`): **a
     real, confirmed miss** — `NORMALISATION_VERSION`'s own comment explicitly names "the
     rewrites `unit_checks` makes before judging" as its scope. Re-confirmed zero false positives
     against all 866 real authored units across the portfolio, then bumped "1"→"2". Done.
   - **PA-02** (`review.py`'s `quote_located` scoping): **a genuine structural gap, not a missed
     bump** — `review.py` has no code-level version constant at all, unlike `renderer.py`
     (`RENDERER_VERSION`), `authoring.py` (`NORMALISATION_VERSION`), or `validation/registry.py`
     (`VALIDATOR_VERSION`/`Check.version`). `docs/STATE_MACHINE.md` section 9's table row
     ("Reviewer prompt/model/rubric → REVIEWING") covers the *prompt*, already tracked via
     `prompts["independent_review"]`'s hash/version — there is no equivalent for the deterministic
     Python code around it (`scope_defect`, `absence_defect`, `quote_located`, `review_checks`
     itself). This is not fixed here: inventing a new versioned component is a real design
     decision (naming, scope — does it cover `scope_defect` too? `factuality_defect`?) that
     deserves its own consideration, not a rushed addition under this already-large stabilization
     pass. Flagged for a follow-up decision, not silently left unmentioned.
3. **Fix CI's workflow** so `ruff check`, `ruff format --check`, `mypy src`, and `pytest` each
   report independently rather than fail-fast-and-hide. Done (`.github/workflows/ci.yml`).
4. **Add a stale-candidate report** — `core.candidates.stale_candidates`, wired into
   `repository-presenter status --stale`. Done, and run live against the real portfolio: with the
   corrected version bumps in place, it reports all 8 current candidates behind the running code
   on `components.renderer` (17→18), `components.normalisation` (1→2), and `validators.BC-03`
   (1→2) — the mechanical version of exactly what `test_sealed_bytes.py`'s byte-diffs had been
   separately, manually establishing as "known, desirable divergences" all session. This is the
   report converging with the byte-level ground truth, which is the validation this design was
   for (section 7 above).
5. **Move the held 3D-Python WIP out of the ambient working tree** — not done; owner's call on
   where (a branch is the more durable option), since it is tied to the unresolved canary policy
   question.
6. **Only after 1–4 land and CI is verifiably green** (a real CI run observed via `gh run list`,
   not assumed): decide, with the owner, whether any of the now-mechanically-flagged stale
   candidates (3D-Python is blocked on the canary policy question regardless; the other 7 are
   not) should be re-sealed now or held for Wave 7 as planned. This document does not decide that
   question — it makes the decision informed instead of ad hoc.

## 7. Validation

- After step 1: `pytest tests/components/readme/validation/ tests/components/readme/composition/test_renderer.py -q`
  plus the full `test_sealed_bytes.py` run should show `BC-03`'s version change causes no new
  validation.json shape issue (schema is unaffected — `Check.version` is already a free-form
  string) and `RENDERER_VERSION`'s bump is a pure metadata change with zero effect on rendered
  bytes (confirm via the same before/after byte-identity check this session used throughout).
- After step 3: push a deliberately lint-broken throwaway commit to a scratch branch and confirm
  the workflow still reports the `pytest` step's own result rather than stopping at lint — proves
  the fix actually removes the blind spot rather than just reordering it.
- After step 4: run the report against the current 8 sealed candidates and manually cross-check
  its output against `test_sealed_bytes.py`'s actual pass/fail set (against committed HEAD, not
  the working tree) — the two must agree, or the report itself has a bug.
- Ongoing regression control: this document's section 2.1 finding (two skipped bumps in ten
  commits) is itself the evidence that step 2's proposed pre-push discipline check would have
  caught, had it existed — the honest baseline to compare future adherence against.

## 8. Tradeoffs and honest limits

- The stale-candidate report (step 4) can only be as good as the version constants it reads; if a
  future change to renderer-output-affecting code is *also* not paired with a version bump, the
  report will silently miss it too, exactly as happened this session. It reduces the chance of a
  miss (a cheap, always-available check instead of remembering to run `test_sealed_bytes.py` and
  manually reason about a diff) but does not eliminate human error at the point a diff is authored
  — only a commit-time discipline check (step 2's audit informs whether that's worth building
  as a standing habit, not a blocking hook) closes that fully, and even that only catches the
  specific files it's told to watch.
- Splitting CI's steps (step 3) increases the number of red/green signals a reader has to parse
  per run; this is the correct tradeoff (visibility over false simplicity) but means CI's summary
  view will look "noisier" even once genuinely healthier.
- None of this addresses whether the remaining EXECUTION-PLAN waves (5 and 6, particularly
  TB-10+RC-07's "portfolio-wide CI-gated evidence-consistency sweep") are themselves worth
  building before more candidates ship — that is a separate, larger question this document
  deliberately does not answer, flagged here so it is not mistaken for having been decided.
