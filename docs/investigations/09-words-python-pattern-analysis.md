# Investigation 09: The Words-Python LANE-E-05 redraw pattern

Status: investigation only, no implementation, no redraw attempted by this session. Written
2026-09-17. Commissioned directly by the owner after `aspose-words-foss/Aspose.Words-FOSS-for-Python`
was drawn at least five times this sprint by lane E (`LANE-E-05`, `-R2`, `-R3`, `-R4`, `-R5`) and hit a
new, different blocker on almost every draw. Modeled on `docs/investigations/06-words-net-pattern-
analysis.md`'s structure and evidentiary standard. Question asked: build the complete run-by-run
timeline, verify the named waypoints rather than assume them, confirm run 5's own just-recorded finding
(`PROPOSAL E24`) is still fresh and unlanded, and classify its root cause against item 115's diagnosis.

Primary evidence: `docs/DECISION_LOG.md`'s G4-W17 arrival-item entries (the single, 99,130-character
`(NNN) ...` catalogue at `docs/RESEARCH_AND_GUIDELINES.md:2214`, and the individual landing entries in
`docs/DECISION_LOG.md`), `docs/RESEARCH_LANE_E.md`'s dated `LANE-E-05` run sections (runs 1-4, merged
into this worktree's `main`) and the same file's run-5 section (present only on the unmerged
`lane-e/LANE-E-05-R5` branch, read from its own worktree `C:\w\e05r5`), `git log --all` and `gh pr
list`/`gh pr view` against `origin/main`, and the current source tree
(`prompts/section_authoring.yaml`, `src/repository_presenter/components/readme/composition/
authoring.py`, `src/repository_presenter/core/llm/jobs.py`,
`src/repository_presenter/components/readme/repair/rounds.py`). Before writing anything, `git fetch
origin main` (no new commits; `origin/main` unchanged at `e5efae1` throughout this session) and `git
worktree list` / `git status` inside `C:\w\e05r5` were used to confirm the branch is merged nowhere,
its worktree is clean and idle (not mid-run), and `gh pr list --state open` shows exactly one open PR
touching this repository (`#110`, `lane-e/LANE-E-05-R5`) — no sixth run is in flight to duplicate or
interrupt.

## 1. The timeline, run by run

| When | Run (branch / PR / commit) | Drawn against | Stage reached | What blocked it |
|---|---|---|---|---|
| 2026-09-16 12:43 UTC | *(precondition, not a lane-E-05 run)* item 52 lands | — | — | `EXAMPLE_RUNNER_IGNORES_REQUIRES_PYTHON`: the Python verifier built its venv from `sys.executable` instead of the manifest's `requires-python`; all 12 of Words-Python's examples read `NOT_VERIFIED`. Fixed: venv now selects `py312` for this repository's `>=3.10,<3.13` declaration. This is what first let a `LANE-E-05` run begin at all. |
| 2026-09-16 20:00:08 +0500 | **run 1** — `lane-e/LANE-E-05`, PR #73, `92a4c5f` | item 52 | **S10 `independent_review`/BC-10** (one repair attempt, re-raised) | `REVIEW_FOLD_STACK_CANNOT_SEE_RECONCILIATIONS_OWN_OMIT_UNSUPPORTED_DISPOSITION` → **PROPOSAL E17**: `review.py`'s `excluded_evidence_defect`/`scope_defect` read only a fact's `polarity`, never `dispositions.json`, so finding `F08` (`additional_examples`) demanded restoration of `inherited_unit:038.table` — a table S4 reconciliation had already, correctly, marked `OMIT_UNSUPPORTED` as unverified. |
| 18:31 UTC then 19:32 UTC, 2026-09-16 | item 86/E17 fix (two-part) | — | — | `review.py` gained the disposition-aware exclusion mechanism at 18:31 UTC (inert — nothing called it yet); `846a9b1` at 19:32 UTC threads `dispositions=dispositions` through `rounds.py`'s `review_document` call site, the one remaining wire. |
| 2026-09-17 01:56:49 +0500 | **run 2** — `lane-e/LANE-E-05-R2`, PR #86, `2a1eb4b` | `846a9b1` (E17) | **S10 again** (two full rounds: one repair, one coherence pass each) | E17 verified closed live (S10 ran twice, `F08`/`inherited_unit:038.table` never recurred). `COHERENCE_PASS_REVERTS_AN_ACCEPTED_REPAIR_WITH_NO_TITLE_RESTATEMENT_GUARD` → **PROPOSAL E19**: the accepted repair correctly stripped a title-restating prefix from all six `key_capabilities` units, but the very next call — S8 coherence (`coherence.py::coherence_packet`/`coherence_checks`, which invokes `authoring.py`'s `unit_checks` unmodified) — silently regenerated the pre-repair, title-restating text, and `write_content_units` persisted the reverted state as final. Finding `F04` re-raised. Secondary, unrepaired finding `F02` (`opening`: two `SUPPORTED` dependency facts uncited) also named here for the first time. |
| 2026-09-16 23:16 UTC | item 99/E19 fix, `4df1b08` | — | — | `unit_checks` gains a deterministic rule against a unit restating its own slot's rendered title, shared by both the `section_authoring` and `coherence_checks` call sites (`NORMALISATION_VERSION` 4→5). |
| 2026-09-17 06:05:48 +0500 | **run 3** — `lane-e/LANE-E-05-R3`, PR #90, `a1334c2` | `4df1b08` (E19) | **S3 `repository_investigation`** (two independent live attempts, both rejected twice; no repair round reached) | E19 closed *as a mechanism* by reading the landed diff — the run never reached S6/S8 to re-observe it live, since it stalled two stages earlier both times it tried. `INVESTIGATION_FACT_ID_ARRAYS_HAVE_NO_ENUM_PIN…` → **PROPOSAL E22**: `repository_investigation` is the one fact-citing job `rounds.py` calls with no `call_schema=` at all (unlike `source_reconciliation`/`presentation_planning`/`section_authoring`, all `$defs`/`enum`-pinned). Two live calls against the byte-identical request hash hallucinated two *different* wrong-but-plausible fact IDs (a live, measured same-digest-different-output nondeterminism, the fourth such corroboration on record). |
| 2026-09-17 02:42 UTC | item 105/E22 fix, `bec76ba` | — | — | `repository_investigation` gets its own `investigation_schema(...)` as `call_schema`, pinning its `fact_ids` arrays the same way the other three jobs already were. |
| 2026-09-17 08:45:35 +0500 | **run 4** — `lane-e/LANE-E-05-R4`, PR #98, `0c65b30` | `bec76ba` (E22) | **S6 `section_authoring`** (two logical calls; the second rejected twice across three live attempts) | E22 verified **CLOSED live** — S3 succeeded on attempt 1 with zero rejections, and the pipeline ran on through S4 and S5 into S6, the furthest any lane-E attempt had yet driven this repository. `FIXTURE_STAGING_AND_FORMAT_FACTS_DISAGREE_ON_ONE_EXAMPLES_DIRECTION_FOR_THE_SAME_EXTENSION` → **PROPOSAL E23**: `python_examples.py`'s `stage_fixtures` stages a fixture under every file-like string literal with no read/write distinction, and `evidence/facts/formats.py`'s `format_facts` then unconditionally reports every staged-and-executed fixture as *input* evidence — contradicting the same function's own, more precise `claims_for`-derived *output* evidence for the identical example. `capability:1` cited `.md` as input from `report.md` (actually the Quick Start's `.save()` target) on all three live attempts. |
| 2026-09-17 05:01 UTC | item 109/E23 fix, `3ff0784` | — | — | `format_facts` now suppresses a fixture-staging `("input", extension)` claim when the same example's `claims_for` already asserts `("output", extension)` for that extension. |
| drawn 2026-09-17 08:45 UTC, committed 13:54:15 +0500 | **run 5** — `lane-e/LANE-E-05-R5`, **PR #110, still OPEN**, `de46355` | `3ff0784` (E23) | **S6 `section_authoring`, `key_capabilities`** (one logical call, rejected twice; job re-ask budget exhausted) | E23 independently verified closed (838 facts, down from 839; `format:input.md`'s contradictory example-1 evidence gone). The pipeline reached `key_capabilities` for the first time with a materially larger, different fact set and found **PROPOSAL E24** (below) — not yet admitted, not yet landed. |

Two corrections found while building this table, the same kind the Words-.NET report flagged for its
own cohort: (1) the pipeline's *stage reached* is **not monotonic** run over run — run 1 and run 2 both
reached S10 (the furthest stage), run 3 *regressed* to S3 because E22's defect sits upstream of
everything runs 1-2 exercised, and only run 4 re-passed S3-S5 to reach S6 for the first time. A naive
reading of "stage reached" as a progress metric would wrongly call run 3 a regression in the pipeline
itself; it is not — it is the arrival-item mechanism working exactly as designed, surfacing whichever
defect sits nearest the front of the pipeline once every defect ahead of it is cleared. (2) Item 86/E17
landed in two physical commits eleven hours apart (18:31 UTC mechanism, 19:32 UTC wiring) under one
item number — run 2 was correctly drawn against the second, completing commit, not the first.

## 2. Is Words-Python special, or a general defect surfacing here first?

Reading each PROPOSAL's own text, not just its headline, as the Words-.NET report did for items 85/89/90:

- **E17** (review fold stack blind to `OMIT_UNSUPPORTED`): the site is `review.py`'s general exclusion
  logic and `rounds.py`'s one `review_document` call site — shared code every repository's S10 pass runs
  through. Words-Python is simply the first repository whose S4 reconciliation excluded a whole
  `inherited_unit` table as unverified *and* whose S10 reviewer then independently flagged the same
  content as missing.
- **E19** (coherence reverts an accepted repair): `coherence.py`'s `coherence_packet`/`coherence_checks`
  call the same `authoring.py::unit_checks` every `section_authoring` call uses, with no rule against
  title restatement at either site before the fix. Any repository whose repair round touches a titled
  slot and is followed by a coherence pass exercises this same path.
- **E22** (S3 has no enum pin): explicitly the one fact-citing job lane E's own text names as the *only*
  one of four still built with no `call_schema=` — a straightforward asymmetry in shared code
  (`rounds.py:189-191`), not a Words-Python defect. Any repository whose S3 call cites a real-but-
  misremembered symbol path is equally exposed.
- **E23** (fixture-staging vs. syntax-tree direction contradiction): `format_facts` runs this same
  two-branch, no-cross-check logic for every Python repository; Words-Python is simply the first
  repository lane E measured whose Quick Start both opens one format and, in the same script, on a
  commented-alternative literal, saves to a format the static scanner also picks up as staged.
- **E24** (see §4): both candidate sites (`authoring.py::unit_checks`, `core/llm/jobs.py`'s universal
  re-ask) are shared code with no Words-Python-specific logic at all.

**None of the five is a defect in the Words-Python *repository* itself** (its upstream README, its
`pyproject.toml`, its package code). All five are gaps in this codebase's own shared composition,
validation, or job-retry logic that Words-Python happened to be large and structurally rich enough (12
executed examples, 838-839 facts, a maintainer-written `additional_examples` table, a six-slot
`key_capabilities` plan) to reach far enough into the pipeline to trip, one stage at a time, exactly as
each stage ahead of it was cleared. This matches the Words-.NET report's own finding for its cohort:
"the first time a repository reaches a not-yet-fully-exercised pipeline stage at real scale, that stage
tends to reveal more than one latent defect at once" is not quite the shape here (Words-Python found
exactly one new class per run, never two at once) — but the underlying dynamic, a large repository
acting as the portfolio's stage-by-stage debugger, is the same one.

## 3. The three named waypoints, verified

**Item 109/E23** (fixture-staging vs. syntax-tree double-count in `format_facts`): confirmed exactly as
described. `evidence/facts/formats.py`'s two branches — the syntax-tree `claims_for` branch (lines
39-57) and the fixture-staging branch (lines 60-71 pre-fix) — computed directions independently and
never compared notes; `3ff0784` (landed 2026-09-17 05:01 UTC) adds a `claimed_directions` cross-check
that suppresses the staging claim when `claims_for` already asserts the opposite direction for the same
extension. Run 5 re-verified this live and independently (not by reading the commit): `git merge-base
--is-ancestor 3ff0784 origin/main` passed, and a fresh `--facts-only --fresh` run reproduced 838 facts
(down from 839) with `format:input.md`'s example-1 evidence gone.

**Item 111/PGPY-04** (`recover=` in `core/llm/jobs.py`): confirmed present in the current tree.
`run_job`'s `recover` parameter (`jobs.py:399-410`, docstring at 419-428) is "a last-resort, job-specific
correction... runs only after the FINAL attempt is still rejected... re-validated from scratch through
the same schema, binding and checks... This exists because the generic one-universal-reask budget below
cannot distinguish an informed rejection... from a blind one." It is wired to exactly one call site
today: `rounds.py:246`, `recover=functools.partial(recover_uncited_capability_titles, facts=facts)`,
attached only to the `presentation_planning` job (`rounds.py:236-248`). **The `section_authoring`
per-task `run_job` call (`rounds.py:267-273`) passes no `recover=` at all** — it relies solely on the
generic one-universal-reask-plus-`rejection_template` path, the exact mechanism item 111's own docstring
says "cannot distinguish an informed rejection from a blind one." This is directly relevant to E24 (§4).

**PROPOSAL E24** (this session's own arrival, run 5): confirmed **not yet admitted, not yet landed**.
`gh pr view 110 --json files` shows the run-5 PR touches exactly three paths — `docs/RESEARCH_LANE_E.md`
(+143), `evidence/build/lanes/lane-e/LANE-E-05.json`, `project/lanes/lane-e.yaml` — none of them
`docs/RESEARCH_AND_GUIDELINES.md` (where G4-W17's arrival catalogue lives, at line 2214) or
`docs/DECISION_LOG.md`. `git log --all -S"E24" -- docs/RESEARCH_AND_GUIDELINES.md docs/DECISION_LOG.md`
returns no commits on any ref, and a direct grep of both files on `main` finds no occurrence of `E24`
anywhere. The PR itself is still `OPEN` (`gh pr list --state open`), so the branch is not merged either.
Lane E's own text is explicit that this is deliberate: "Lane E writes no fix... Words for Python takes a
disposition naming this proposal as its resume predicate" — it names three owner options (§4) and picks
none.

**Liveness check**: `git worktree list` shows `C:/w/e05r5` at `de46355` on branch
`lane-e/LANE-E-05-R5`, `git status` there reports a clean tree "up to date with
'origin/lane-e/LANE-E-05-R5'" — the run-5 worktree is idle, not mid-draw. No other worktree in the list
references `lane-e`, `words`, or `LANE-E-05`. `gh pr list --state open` shows exactly one PR touching
this repository (`#110`). No sixth run is in flight; this investigation's timeline is current as of
`origin/main` at `e5efae1` (confirmed unchanged by a second `git fetch` immediately before writing this
file).

## 4. E24's root cause: prompt-clarity gap, schema gap, or neither — and its relation to item 115

**What actually happened, read against the live prompt and code.** `prompts/section_authoring.yaml`
already states the rule E24's defect breaks, twice, before any rejection ever occurs:

- The **system prompt** (`section_authoring.yaml:116-117`): "Fact IDs, fact kinds, and packet field
  names (`link_target`, `package:python_requires`, `accepted_facts`) are provenance, never words in
  prose."
- The **`rejection_template`** (`:16`, landed as `ef40284` on 2026-09-06 — eleven days before run 5, not
  something added in response to E24): "A rejected identifier that IS one of the unit's own cited
  `fact_ids` is not a spelling problem either: the citation belongs only in `fact_ids`, and the unit's
  text never lists, names, or says which facts support it (`"citing X, Y, and Z"` and similar phrases
  are never written) — state the fact's content in prose instead, exactly as its own value reads."

Despite both, the model's first live attempt on run 5 appended a bracketed, comma-separated list of the
unit's own `fact_ids` inside the visible `text` field for **all six** `key_capabilities` slots — a
different literal shape (`[format:input.doc, format:input.docx, ...]`) from the "citing X, Y, and Z"
phrasing the template's prose anticipates, but the identical underlying rule violation. `unit_checks`
(`authoring.py:1385-1396`, the `identifier_tokens`/`identifier_allowed` stray-token scan) correctly
rejected all six. The one re-ask — which necessarily includes the exact rejection-template sentence
above, verbatim, via `_re_ask`'s `string.Template` substitution (`jobs.py:554-565`) — reproduced five of
six slots **byte-identical**, brackets intact, and on the sixth made the wrong edit: it stripped the
correct, allowed module names from the sentence body while leaving the disallowed bracket in place.

**Why this is not a prompt-clarity gap the way item 115 was.** Item 115 (PGPY-05, `b4e3e9c`, landed
2026-09-17 12:54 UTC — after E24 was found, and for a different repository) added an entirely **new**
`rejection_template` sentence because the template had **zero** coverage for a `_FORBIDDEN`-marker
rejection: a Page-Python unit narrating a literal `"pip install"` command got a rejection message
written "entirely for the identifier/citation defect class," found nothing in it that named its own
failure, and returned byte-for-byte identical output — the commit message states this plainly: "gave the
model's one re-ask no signal for what to change." That is a genuine coverage hole: one rejection *class*
(`_FORBIDDEN` markers) had no corresponding guidance sentence at all, and adding one measurably fixed it
(a new test exercising the real `run_job`/`unit_checks` path is part of that same commit).

E24's rejection class — a stray identifier that is one of the unit's own cited `fact_ids` — **already
had** its own guidance sentence, added over a week earlier, textually on-point for exactly this failure.
The rejection was not a blind one; the model received the precise, correctly-worded rule both before
generation (system prompt) and again as the correction (rejection_template), and still reproduced the
defect on five of six slots and made an incorrect edit on the sixth. Re-running item 115's fix *pattern*
— write a clearer sentence — is not a hypothesis here; it is a control that has already been tried,
against this near-exact failure shape, and measurably did not hold under a harder case (a bracketed
citation list rather than a prose "citing X, Y" phrase, six repetitions in one call instead of one).

**Classification: E24 is a class item 115 does not cover, and it is closer to a schema/mechanism gap
than a prompt-clarity gap.** Item 115's shape is "the rejection_template has no signal for this failure
— add one." E24's shape is "the rejection_template already has an on-topic signal, restated at the
moment of correction, and the model's one re-ask still does not reliably act on it." These are different
defects in the same *family* (both are "the model's one re-ask attempt didn't fix what it was rejected
for," project vocabulary for the class loop-prompt.md §5 and the arrival-item mechanism exist to catch),
but item 115's fix — more/better prose — is not evidence that more prose fixes E24's shape, because
E24's shape already had prose and it did not hold. The stronger reading is a **mechanism** gap: nothing
in the pipeline enforces this specific, easy-to-state rule deterministically. `authoring.py` already has
a working precedent for exactly this move — the backtick-stripping branch immediately above the
`_FORBIDDEN` check (`authoring.py:1357-1361`): "The renderer owns every code span: a span the job wrote
is dropped in place," silently normalizing a formatting artifact instead of spending a re-ask on it.
Lane E's own three owner-facing options (§27.9-shape, not landed) span exactly this spectrum: (1)
extend that same silent-strip precedent to a trailing bracketed fact-ID list (schema/code-level, highest
confidence given the backtick precedent's proven pattern); (2) give `section_authoring` its own
`recover=` hook the way item 111 gave `presentation_planning` one — noting, per §3 above, that
`section_authoring`'s `run_job` call passes no `recover=` today, so this option is currently unavailable
to it at zero cost, unlike a job that already has the hook and only needs a narrower trigger; (3) add a
worked bad-example to the prompt — the one option that repeats item 115's own fix pattern, and the one
this investigation's own evidence gives the least confidence in, since a *working* prose rule already
existed and the failure happened anyway.

This investigation takes no position on which of the three the owner should choose — that decision is
explicitly reserved to the owner in lane E's own PROPOSAL text and is out of this investigation's scope
(diagnosis only, no fix attempted here either). What this section adds beyond lane E's own record is the
direct comparison: E24 is not "the same defect as item 115 recurring on a new marker" and it is not
simply "a harder version of the same clarity problem" — it is the next rung up a spectrum item 115 sits
on, where the cheap fix (clearer prose) has already been tried for this exact rule and measurably failed
to generalize from a short phrase to a structured, repeated, six-slot bracket list.

## 5. Current precise blocker and honest recommendation

As of `origin/main` at `e5efae1` and PR #110 (`de46355`, still open): Words-Python is **NOT_SEALED**,
stopped at **S6 `section_authoring`, `key_capabilities`**, class
`SECTION_AUTHORING_UNIT_TEXT_ECHOES_ITS_OWN_FACT_ID_CITATIONS`, resume predicate "PROPOSAL E24 lands,
then re-run." `repository-presenter status` reads **18/34** before and after run 5 (per the PR's own
commit body); no seal is claimed. E23 (item 109) is closed and independently reconfirmed and is not a
predicate for the next run. F02 (`opening`, dependency completeness, first named in run 2) has never
been repaired and was not re-observed this run either (S10 never ran) — it remains a live, distinct,
unrepaired thread for whichever future run next reaches S10, separate from E24 entirely.

Do not expect the next redraw to seal Words-Python outright even once E24 lands. Following the same
reasoning the Words-.NET report applied to its own cohort: this repository has now revealed one new
shared-code defect on four of its five runs, each one stage further into the pipeline than the last
(S10 → S10 → S3 → S6 → S6), and has never yet reached S7 (repair) on this fact set, S8 (coherence) past
run 2's now-fixed defect, or S10/S11/S12 at all past run 2. F02 alone is a known, unrepaired, currently-
non-blocking finding waiting at S10. The pattern across five runs is consistent, not alarming: one real,
evidenced, shared-code defect found per run, immediately fixed or handed to the owner, never the same
class twice. That is the arrival-item mechanism working as designed on a large repository, not evidence
that this repository or the mechanism is broken.
