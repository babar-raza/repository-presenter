# Defect class index

This file owns cross-repository defect-class tracking. `docs/DECISION_LOG.md` is the append-only
provenance record — every sighting's full evidence lives there and never moves. This file is the
index on top of it: one entry per causal *mechanism*, linking every sighting so a repeated pattern
is visible without re-reading thousands of lines of history.

Rule (`AGENTS.md`'s Work Loop): a mechanism with **three or more independent sightings** is settled
priority for the next shared-code-item slot, not a judgment call. `docs/SUPERVISION.md`'s mandatory
sweep checks this file every wake for a class that just crossed the threshold.

An entry is added the first time a session recognizes a defect as belonging to a named mechanism
(not merely "this repository failed") — usually on the second sighting, when a pattern first
becomes visible. Close an entry (move it to Resolved) only once a landed fix has been verified
against at least one of its own listed sightings, not merely proposed.

## Open

### `s4_reconciliation.output_runaway_past_budget`

S4 `source_reconciliation` replies run to the manifest's `max_output_tokens` (`finish_reason
length`) and the job stops before any blocking check. The schema let a disposition's `fact_ids`
array reach the batch's whole citable set (739 IDs on PDF-TypeScript, more elsewhere), and nothing
bounded the reply's total, so a repeating citation list could fill the budget. Three independent
sightings, all of the same mechanism:

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` | 2026-09-11 | 1,047 repeated `public_symbol:` entries in one array, `finish_reason length` on both runs (`docs/DECISION_LOG.md` S4-REGRESSION; `tests/components/readme/reconciliation/test_normalization.py`) |
| 2 | `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET` | G4-W17 item 121 (F27) | 32,000-token `TruncatedOutput` on one attempt, 3,016 tokens on an identical retry of the same request hash |
| 3 | `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` | 2026-10-04 (revision `a8661f8b`) | batch 1 (40 units) `finish_reason length` at 32,000 tokens; the identical request then answered `stop` at 4,666 tokens (qwen3-next, temperature 0, seed 1) |

Fix (branch `fix/s4-output-budget`): `fact_ids` capped per disposition at 16
(`RECONCILIATION_FACT_IDS_PER_DISPOSITION`), `destination_section` an enum of the shell's section
IDs, and batch size derived from the longest reply the schema admits at the budget's
characters-per-token floor (`output_chars_bound`). A truncated reply is kept beside the call store
(`*.rejected-N.json`) before the typed `TruncatedOutput` failure, so the runaway field is read from
evidence next time. Status: fixed on the branch; closes when the live proof on sighting 3 reaches
past S4.

### `readme.bc07_visible_budget_repaired_by_model_only`

Check 7's visible-line budget (`validation/registry.py`, `_check_structure`) measures the composed
README, never a plan, and stamps `causal_stage: PLANNING` on every overage (`composition/planning.py`
and `plan_checks` carry no visible-line notion; a plan has no line count). The only plan-owned
visible levers are the two optional example fields (`repair/targeted.py::VISIBLE_LINE_LEVER_FIELDS`).
The repair asked the model to clear one first; the deterministic clear sat behind the model's own
attempts as a last resort, and the model cleared no lever on any recorded draw, so the same overage
re-raised.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-font-foss/Aspose.Font-FOSS-for-Python` | 2026-09-16 | 307 of 792 visible; `docs/RESEARCH_LANE_E.md` (LANE-E-04) |
| 2 | (same) | 2026-09-16 18:06 UTC | 377 of 799; `docs/RESEARCH_LANE_E.md` (run 2) |
| 3 | (same) | 2026-09-17 10:24 UTC | 327 of 764; `docs/DECISION_LOG.md` |
| 4 | (same) | 2026-09-28 10:06 UTC | 305 of 713 after one repair, re-raised; `docs/DECISION_LOG.md` |
| 5 | `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` | 2026-10-04 | 328 of 1262 (fresh present, qwen3-next) |

**Status 2026-10-04**: the deterministic-first bound (`composition/planning.py::bound_visible_line_overage`,
called by `repair/rounds.py::repair_defect` before the targeted repair) clears the levers in code
when their exact saving clears the overage with `VISIBLE_LINE_RENDER_MARGIN` to spare; the model
is asked only when it does not. Not moved to Resolved: it is confirmed only by a live draw that
clears BC-07 on a repository in this index (resume predicate: a fresh Font-Python draw).
Open question for the owner: `README_CONTRACT.md` section 1 states a default budget of 320 visible
lines, while `composition/policy.py` enforces 300. The enforced value has been 300 in every
sighting above.

### `present_transaction.wrapper_outcome_no_registered_path`

`core/state/present_transaction.py`'s durable-state wrapper (landed G5-W05, PR #172/#181) crashes
with `'INVALIDATED' has no registered path toward a committed outcome` whenever the real pipeline's
own outcome is `VALID_UPDATE_AVAILABLE` - the wrapper's own docstring claims its scope "only ever
produces OBSERVED, a success-spine state, FAILED_INTERNAL, or INVALIDATED," but `VALID_UPDATE_AVAILABLE`
is none of those, so it has no registered commit path at all. The underlying pipeline itself
completes correctly every time this fires (facts extracted, review ACCEPT, bundle written) - the
crash is purely in the wrapper's own outcome-classification table, not the pipeline. Intermittent
across otherwise-identical runs (one run with this exact outcome succeeded), suggesting an
ordering/state race rather than a deterministic branch, though not yet root-caused to that level.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-3d-foss/Aspose.3D-FOSS-for-Python` | 2026-10-01 09:59 UTC | hosted run `36846316608`, 39s, failure |
| 2 | (same, re-run) | 2026-10-01 10:03 UTC | hosted run `36846738278`, 42s, failure, identical error |
| 3 | `aspose-3d-foss/Aspose.3D-FOSS-for-Python` | 2026-10-01 10:32 UTC | hosted run `36849829170`, 34s, failure |
| 4 | (same candidate, revision `65b1f577...`) | 2026-10-01 12:09-12:24 UTC | hosted run `36859856641`, 15m10s, failure - full log confirms real pipeline success (review ACCEPT, bundle state `VALID_UPDATE_AVAILABLE`, 14 files) immediately followed by `##[error]first present invocation failed (exit 1); skipping the no-op-proof rerun` |

**Status 2026-10-01 (independent owner-relayed QA pass, re-verified directly against the real run log
before recording)**: of the last 6 hosted `present.yml` runs, only 1 (10:41 UTC) succeeded - this is
not a flaky one-off, it is the dominant outcome right now. This blocks G5-W05's own acceptance bar
("a real hosted run... reaches the same accepted result as local execution... hosted CI green")
from being reliably met, which in turn blocks G7-W06 (turning on unattended scheduling - the literal
"hosted to work autonomously" requirement `plans/idea.md` names) from being safe to land. A lane was
already mid-fix on a related gap in this same module (`_BRIDGE_SOURCES`, adding an `INVALIDATED`
resume-source re-entry point) when this entry was written; directly messaged to confirm whether that
fix actually covers this specific `VALID_UPDATE_AVAILABLE`-outcome case or is a distinct gap, since
the wrapper's own error text names `INVALIDATED` literally, not `VALID_UPDATE_AVAILABLE`. Not yet
confirmed fixed - re-run the hosted workflow after the fix lands and check this exact candidate
before moving this entry to Resolved.

**Status 2026-10-04 (wiring audit, `origin/main` `ecdff0dc`)**: still Open. The success-path mapping that sends `VALID_UPDATE_AVAILABLE` to `ACCEPTED` (`core/state/present_transaction.py`, around lines 170-175) was introduced in `ffb5ccbd` (a `git log -S` search for its comment text finds only that commit); `73f76648` changed the failure branch. A hosted `present.yml` run on branch `g5-w05-hosted-proof` (run `37197380582`, 2026-10-04 11:02 UTC, head `a41662ce`) concluded success, but that branch is not `main`, and no record shows the sighted candidate (revision `65b1f577...`) re-run after any fix. Moves to Resolved only on that candidate's hosted re-run on `main` with no wrapper error.

**Status 2026-10-04 (fix in PR #215, branch `fix/durable-invalidated-path`; not yet verified on hosted `main`)**: fixed in code, still Open until that re-run. Root cause confirmed from the code: `INVALIDATED` is written by the wrapper's own failure branch (`ACCEPTED` -> `INVALIDATED`), and `admit_trigger` never resets a record's state, so a run that starts from a record left at `INVALIDATED` reached `_success_hops`, which had no path out of `INVALIDATED`. The `VALID_UPDATE_AVAILABLE` outcome already commits `ACCEPTED`, never `INVALIDATED`; the fix does not change that mapping. The fix registers the `INVALIDATED` -> `EXTRACTING` re-entry the schema already defines and closes the other unregistered pairs a table test found for wrapper-reachable states (`MONITORING`, `PROVING_NO_OP` / `ACCEPTED` behind an outcome, and a failure from `READY_FOR_PROPOSAL`). The hosted record's own history for the sighted candidate was not inspected.

### `section_authoring.rejection_no_recover`

`section_authoring`'s rejection-repair loop had no deterministic `recover=` backstop, unlike
`presentation_planning`'s (`composition/planning.py::recover_uncited_capability_titles`). Three
distinct sub-shapes share the same root gap (no last-resort deterministic correction before the
repair budget exhausts), tracked as one mechanism because the fix pattern is identical:

- **Forbidden-literal sub-shape**: a re-ask reproduces a `_FORBIDDEN`-marked literal (e.g. a
  `pip install` command) byte-for-byte despite the rejection template naming it forbidden.
- **Title-restatement sub-shape (repair path)**: `unit_checks`'s item-106 carve-out lets a
  repaired unit through (real detail follows the title), but independent review's own separate
  semantic judgment still flags the literal title-verbatim opening clause regardless of what
  follows it.
- **Title-restatement sub-shape (initial-draft path)**: a DIFFERENT call site than the one above -
  `section_authoring`'s own INITIAL-DRAFT job (the first `run_round` call, before any repair
  round), not a `targeted_repair`. Attempt 1's own unit already carries real member-level detail
  satisfying item 106's own carve-out, but is rejected anyway for an unrelated reason (the same
  detail cited as an unsupported identifier); the one universal re-ask correctly deletes the
  identifier the rejection named, but that deletion also deletes the only detail keeping the unit
  inside item 106's own carve-out, trading one rejection for a fresh one
  `recover_forbidden_command_units` (scoped to `_FORBIDDEN` command markers only) cannot see -
  and, since a section is one call for every one of its slots, taking every unit of that call down
  with it, not only the one the model touched.

| # | Repository | Sub-shape | Date | Evidence |
|---|---|---|---|---|
| 1 | `aspose-page-foss/Aspose.Page-FOSS-for-Python` | forbidden-literal | 2026-09-24 14:25 UTC | `docs/DECISION_LOG.md`, never sealed until fixed |
| 2 | `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` | title-restatement (repair path) | 2026-09-25 08:04 UTC | `docs/DECISION_LOG.md`, reseal regression |
| 3 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | title-restatement (repair path) | 2026-09-25 07:13 UTC (and `docs/RESEARCH_LANE_C.md` G4-W12-RERUN7 through RERUN13, earlier) | 7+ reruns, recurring |
| 4 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | title-restatement (initial-draft path) | 2026-09-26 03:06-08:35 UTC, corroborated 2026-09-27 | `docs/DECISION_LOG.md` — first surfaced when `section_authoring` exhausted its 2-attempt budget without ever reaching review; root-caused and fixed 2026-09-27 |

**Status 2026-09-25**: crossed 3 sightings; escalated same day per the owner's direct instruction.
Forbidden-literal and title-restatement (repair path) both have a landed fix: forbidden-literal via
`composition/authoring.py::recover_forbidden_command_units` (commit `1fff7d7`); title-restatement
(repair path) via a deterministic backstop for review's stricter standard (commit
`fadb001`/`a313864`).

**Status 2026-09-26 (verification session, full detail in `docs/DECISION_LOG.md` this timestamp)**:
both `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` and
`aspose-slides-foss/Aspose.Slides-FOSS-for-Java` were drawn live (a transient gateway outage on
`qwen3-next` was hit first, confirmed via a direct probe, and cleared on its own ~25 minutes later
— not code-related). Neither sealed. **BarCode-Python**: the title-restatement finding surfaced
only as an uncorroborated advisory this draw, never a blocker, so `fadb001`'s own repair-path
mechanism was never exercised either way; the candidate blocked instead on a new, unrelated defect
(`F08`, `development_testing`). **Slides-Java**: never reached independent review at all — the new
sighting #4 above (the initial-draft path), which `fadb001` does not cover by design (scoped to the
separate repair-path call site only).

**Status 2026-09-27**: all three sub-shapes now have a landed fix. Forbidden-literal via
`composition/authoring.py::recover_forbidden_command_units` (commit `1fff7d7`); title-restatement
(repair path) via a deterministic backstop for review's stricter standard (commit
`fadb001`/`a313864`); title-restatement (initial-draft path, sighting #4) via
`composition/authoring.py::recover_section_authoring_output`, which composes
`recover_forbidden_command_units` with the same opening-clause strip
`recover_title_verbatim_opening` already uses for the repair path, wired as
`section_authoring`'s own initial-draft `recover=` in `repair/rounds.py`
(`NORMALISATION_VERSION` 15 -> 16). Verified by mutation test against this exact reported shape
(`tests/components/readme/composition/test_authoring.py`); a fresh live redraw of Slides-Java at
the same revision (`docs/DECISION_LOG.md`, 2026-09-27) did not sample the attempt-1-detail/
attempt-2-deletion sequence this fix corrects, so it is not yet moved to Resolved - the mechanism
is fixed and mutation-tested, but not yet measured firing live on this or any other repository. The
repair-path fix (sightings 2-3) also remains landed but not yet live-verified as a success against
either of its own originating repositories - BarCode-Python's own reseal is still separately
blocked on the unrelated `F08` finding above.

**Status 2026-10-04 (wiring audit, `origin/main` `ecdff0dc`)**: not moved to Resolved. The three sub-shape fixes are in code (`composition/authoring.py`: `recover_forbidden_command_units` and `recover_section_authoring_output`; the title-restatement repair path via `recover_title_verbatim_opening`; the `recover=` call sites in `repair/rounds.py`) with mutation tests, but no listed sighting has been re-drawn with a fix observed firing. The Page-Python draw of 2026-09-25 cleared its first attempt without the forbidden-literal recovery. This entry keeps the bar its own 2026-09-27 status set: live measurement, not unit verification. Resume predicate: a live draw of one of the listed repositories in which a recovery fires and the candidate clears.

### `composition.authoring.superseded_unit_not_carried`

Reconciliation disposed an inherited prose unit `SUPERSEDE_REDUNDANT` into a placeable section
(its substance is meant to be re-authored there), but the section's own authoring call was never
given that unit: `composition/authoring.py::section_selections` handed `development_testing` only
its `build_test_asset` facts and placed units. On `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`
(revision `620a2614...`) the README's test-suite layout and conformance rule
(`inherited_unit:092.paragraph`, with `093`/`094`) therefore never reached the packet, and
`unit_checks` had no rule that a superseded unit be carried or explicitly omitted. Independent
review then blocked on it (`F08`, `development_testing`) on two of three pre-fix draws (the third
accepted on the same finding); one targeted repair
could not restore content the repair packet also withheld (`repair_packet` excludes inherited units
by default). Scoped fix, `NORMALISATION_VERSION` 18 -> 19: superseded prose units join the section's
citable set, each must be cited or explicitly omitted with a reason (`carried_unit_errors`), a
last-resort recovery records any still-uncarried unit as an omission (never invented content), and
the S6 repair packet carries the same units. Mutation-tested
(`tests/components/readme/composition/test_authoring.py`,
`tests/components/readme/repair/test_targeted.py`, `test_rounds.py`). Live (qwen3-next, `--fresh`,
three draws): the development section states the test-suite layout and the conformance rule in all
three; the review blocked on an unrelated `scope_limitations` finding in two of three. Not yet
moved to Resolved: the F08 class has not been observed blocking in a live draw since the fix, but
the candidate itself has not sealed. Other placeable sections with superseded inherited units
(e.g. `scope_limitations`, `additional_examples`) are not covered by this scope yet.

### `composition.coherence.inherited_diagram_content_loss`

Independent review's presentation criterion can catch S7 authoring/coherence rewriting an
inherited Mermaid diagram (an "At a glance"/"What it can do"-shaped original) into a simplified
form that drops specific capability, structure, or input/output detail the original carried - but
no deterministic check exists for this at all (unlike, say, `unit_checks`'s title-restatement
carve-out), so whether the loss is caught depends entirely on whether that draw's own independent-
review sample happens to notice it. A `targeted_repair` round on the finding does not reliably
restore the missing content either (both listed sightings below survived one repair round with the
rejection still standing). Distinct from `section_authoring.rejection_no_recover` above: that
mechanism is about a deterministic `unit_checks` rule being satisfied and then broken by a
recovery step with no fallback; this one has no deterministic check on either side; only an
independent-review sample, present or absent, decides whether the loss is ever caught.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | 2026-09-27 | `docs/DECISION_LOG.md` (the `recover_section_authoring_output`/item-4-sighting entry above): independent review's `F02` finding - "the candidate's `at_a_glance` Mermaid diagram omits specific capabilities and the input/output structure the original's diagram carried" - survived one `targeted_repair` round, `BC-10 REJECT_PRESENTATION` standing; recorded there as "a real, different, currently out-of-scope defect this work item was not asked to fix." |
| 2 | `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET` | 2026-09-27 05:33 UTC | `docs/DECISION_LOG.md` (this session's RC-01 verification entry): two independent fresh draws of the same revision (`86c441b5...`) each hit `BC-10 REJECT_PRESENTATION` after one repair round, both findings at `causal_stage S7`/`section_id key_capabilities` - draw 3's F07 ("rewrites the original README's 'At a glance' Mermaid diagram as a simplified flowchart..., losing the original's structure and XML output references") and draw 4's F03 (omits 3D-properties/document-properties capabilities the original's "What it can do" list names) - a different specific gap each time, same location and shape. |

**Status 2026-09-27**: two sightings, both today, on two different repositories in the same
product family (`aspose-slides-foss`, Java and .NET) - below the 3-sighting escalation threshold
but the pattern is now visible enough to name. No fix proposed yet; whoever picks this up next
should start from `composition/authoring.py`'s and S7 coherence's own handling of an inherited
Mermaid diagram/capability list (the same slot-rendering code path item 4 above already touched
for a different sub-problem) and consider whether a deterministic check belongs somewhere in this
path at all, given no reliable one currently exists.

**Status 2026-10-01 (G3-W05, `docs/DECISION_LOG.md` this date)**: fix landed, not yet moved to
Resolved. `composition/coherence.py::coherence_content_loss_errors` compares each S8 coherence
unit's pre- and post-revision `fact_ids`/text and rejects a revision that silently drops a
previously-cited fact with none of its own content left in the text; `recover_coherence_content_
loss` is S8's first `recover=`, reverting exactly the affected unit(s) to their own pre-coherence
version. A mutation test reproduces each sighting's exact shape. Live-verified firing and
correctly recovering on a real draw of sighting #1's own repository (`aspose-slides-foss/Aspose.
Slides-FOSS-for-Java`, same revision): the draw's own `key_capabilities` review finding (F05, the
same inherited-content-loss shape) was then repaired by `targeted_repair` and did not re-raise -
the candidate still does not seal, blocked only by a separate, unrelated `scope_limitations`
defect (F06). That same live draw surfaced and fixed a real false-positive (identity/package
provenance citations, never a named capability) in a second commit, covered by its own mutation
test; three further live draws after the fix each failed before reaching S8 on different,
unrelated, already-documented defects, so the refined check has not yet been re-exercised live -
honestly left here rather than moved to Resolved until a future draw confirms it end to end.

**Status 2026-10-04 (wiring audit, `origin/main` `ecdff0dc`)**: still Open. `G3-W05` is COMPLETE, with its gate-manifest record (`evidence/build/G3_PYTHON_COHORT/manifest.json`, `g3_w05`). Two mutation tests reproduce both sightings' shapes (`tests/components/readme/composition/test_coherence.py`). The only live draw that reached S8 ran before the identity/package exclusion; the three draws after the refinement failed at earlier, unrelated stages. This entry's own bar, a live draw that re-exercises the refined check end to end, is not yet met. Moves to Resolved on that draw.

### `registry.write_gate_unwired_mode_unenforced` (REV-V1-01)

`core/registry/loader.py::is_permitted` is the registry's write gate (a `disabled` entry is analyzed but never proposed to), yet nothing in `src/`, `scripts/` or `.github/workflows/` calls it. Every admission point uses the read gate `require_listed`, and `mode` (`full` / `dry_run` / `disabled`, `core/registry/models.py`) is only printed, never branched on. The live registry is recorded as 34 entries (full 2, dry_run 29, disabled 3, `docs/RESEARCH_AND_GUIDELINES.md:775`), so 32 of 34 are intended not to be proposal-eligible and nothing enforces that.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/registry/loader.py:54` (definition); the only other references are `tests/core/registry/test_loader.py:85,126,130` |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:966,1106,1383,1677` (`require_listed` at all four admission points); `cli.py:967,1108,1385` (`mode` printed only) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py` (no reference to `mode` or the registry) |

**Id** REV-V1-01 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 1 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: grep shows `is_permitted` has a production caller in `run_propose` (and in the effect path) and a test that a `dry_run` and a `disabled` entry are each refused before any write call; `grep -rn is_permitted src/` returns more than the definition.

### `propose.candidate_state_and_registry_not_checked` (REV-V1-02)

`run_propose` reads `--readme-file` directly with no `load_registry` / `require_listed`; the default path consults the registry but only tests that `CURRENT` and `README.md` exist, never `manifest.json`'s `state`. `core/candidates.py` (`COUNTED_STATES = {READY_FOR_PROPOSAL}`) documents that `CURRENT` can point at a revision that is not `READY_FOR_PROPOSAL`. Reproduced on live data: `candidates/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/CURRENT` is `620a2614...` whose manifest state is `VALID_UPDATE_AVAILABLE`, so the default path would propose that non-final candidate. `.github/workflows/propose.yml` takes `repo` and `readme_file` as free-text `workflow_dispatch` strings with no registry or state pre-check.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1090-1124` (`--readme-file` branch skips the registry; default branch checks only file existence) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/candidates.py:37` (`COUNTED_STATES`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/620a2614418854b4a18966a361e6907ddc88c7cb/manifest.json:111` (`state: VALID_UPDATE_AVAILABLE`) reached by `CURRENT` |
| 4 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:38-47` (free-text dispatch inputs) |

**Id** REV-V1-02 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 2 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows `run_propose` refuses a `CURRENT` whose manifest state is not `READY_FOR_PROPOSAL` (using the Slides-Java shape above), and refuses a `--readme-file` for a repository that is not a registry entry permitted by `is_permitted`; `grep -n READY_FOR_PROPOSAL src/repository_presenter/cli.py` finds the gate.

### `propose.workflow_shell_injection_and_shared_write_token_job` (REV-V1-03)

`.github/workflows/propose.yml` substitutes `${{ inputs.repo }}`, `inputs.expires_in_minutes`, `inputs.readme_file`, `inputs.source_revision` and `inputs.base_branch` directly into `run:` script text before bash parses it (the standard GitHub Actions script-injection class; YAML-level quoting does not help). The file has one job, `propose`, which holds the untrusted-input steps, the dry run, and the write-scoped App token mint (`actions/create-github-app-token@v2`), so injected shell runs with the write token reachable in the same runner.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:92,100,101,102,104,105` (`${{ inputs.* }}` inside `run:` blocks) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:70-71,117,134` (single `propose` job; token mint and `GH_PROPOSAL_WRITE_TOKEN` in the same job) |

**Id** REV-V1-03 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 3 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -n 'inputs\.' .github/workflows/propose.yml` shows each input reaches `run:` only through an `env:` mapping (never inline), the dry run and the token-minting write step are separate jobs with the mint in the write job only, and a workflow-audit test in `tests/` asserts both.

### `propose.authorization_self_minted_self_validated` (REV-V1-04)

`authorize_proposal` is a plain constructor with no validation; `run_propose` computes `candidate_hash = sha256_text(readme_text)` and passes it in, then `propose_candidate` calls `validate_authorization` with `expected_candidate_hash=sha256_text(readme_text)` over the same `readme_text`, plus the same repository, revision and branch values. No independently sourced record (a persisted approval or a separate approver) is checked, so validation can only detect a clock or in-process mismatch. The only external gates are the `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` variable and token presence, both set by whoever submits the dispatch form that also chose the target and file.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/authorization/proposal.py:55-85` (`authorize_proposal`, no validation) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1126-1139` (hash computed and authorization built in one call) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:205-218` (`write_authorized`, then `validate_authorization` over the same values) |

**Id** REV-V1-04 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 4 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `propose_candidate` accepts an authorization record loaded from a source the author path cannot write (a sealed-bundle approval or a separate approver artifact), a test shows a record whose `candidate_hash` was not independently approved is refused, and a test shows a record minted in the same process without that approval is refused.

### `propose.app_only_token_is_workflow_convention` (REV-V1-05)

PARTIAL: the claim that the code accepts any `GH_TOKEN` is wrong. The write path reads only `GH_PROPOSAL_WRITE_TOKEN` and `effect.py` states it refuses `GH_TOKEN`. The surviving part is real: nothing in code checks that the value in `GH_PROPOSAL_WRITE_TOKEN` is a GitHub App installation token (`effect.py` documents App tokens only 'in principle'; there is no prefix or claims check in `core/github/client.py` or `effect.py`). The 'App only' guarantee therefore lives in the `propose.yml` mint step, so a local or differently authored run with a hand-set PAT is treated identically.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1153-1161` (reads `GH_PROPOSAL_WRITE_TOKEN`, never `GH_TOKEN`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:22-25,109` (App token 'in principle'; `_NO_TOKEN_REASON`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:115-125` (the only enforcement) |

**Id** REV-V1-05 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 5 (PARTIAL), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: either a runtime check that rejects a non-App-installation token before any write (a test with a PAT-shaped value is refused), or a documented decision that the YAML-only guarantee is accepted, with the audit test that pins the mint step; a grep of `src/repository_presenter/components/propose/` for the token-shape check shows which.

### `metadata.description_overwrite_and_topics_full_replace` (REV-V1-06)

`diff_against_observed` flags `description_changed` on any difference with no quality or maintainer-authorship guard, and `apply` then calls `update_repository` unconditionally with the proposed description. `replace_topics` is `PUT /repos/{owner}/{repo}/topics`, a full replace, while `propose_topics` derives only a small deterministic set, so any maintainer-added topic outside it is dropped on write. Latent, not armed: no workflow in `.github/workflows/` invokes the `metadata --apply` path and `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED` is unset in this project's environment.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/metadata/proposal.py:210-212` (`description_changed`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/metadata/apply.py:157-181` (unconditional update once authorized) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/github/client.py:222-242` (`replace_topics`, full replace); `src/repository_presenter/components/metadata/proposal.py:141-168` (`propose_topics`) |

**Id** REV-V1-06 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 6 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows an existing non-empty maintainer description is not overwritten without an explicit owner decision, and a test shows `apply` merges the observed topics into the proposed set (union) rather than replacing them; `grep -rn replace_topics src/` shows the caller passes a union.

### `issues.filing_global_gate_no_per_handoff_approval` (REV-V1-07)

`issues-scheduled.yml`'s `file-and-close` job is gated only by `vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED == '1'` and fans out over every repository with a `HANDOFF_PENDING` or `FILED` handoff (`_ACTIONABLE_STATES`). When omitted, `file-upstream-defects --repo` files every `HANDOFF_PENDING` handoff. Live data: the Aspose.HTML-FOSS-for-Python and Aspose.TeX-FOSS-for-Python handoffs are both `HANDOFF_PENDING` today, so one repository variable set to `1` would file both as real issues against real `aspose-*-foss` repositories in one scheduled run with no review of either body.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/issues-scheduled.yml:143,149` (sole gate; matrix over all targets) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:438,787,797` (files all `HANDOFF_PENDING` when `--repo` omitted; `_ACTIONABLE_STATES`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `evidence/upstream-defects/aspose-html-foss__Aspose.HTML-FOSS-for-Python/ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a.json:32` and `evidence/upstream-defects/aspose-tex-foss__Aspose.TeX-FOSS-for-Python/c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188.json:28` (`status: HANDOFF_PENDING`) |

**Id** REV-V1-07 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 7 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: filing requires a per-handoff approval recorded outside the filing job (a handoff-level field or approval artifact checked by `file-upstream-defects --file`), a test shows an unapproved `HANDOFF_PENDING` handoff is not filed when the global variable is `1`, and the workflow matrix is restricted to approved handoffs.

### `propose.pr_lookup_open_only_recreates_merged_pr` (REV-V1-08)

`find_open_pull_request` queries `pulls?head=...&state=open`, and `propose_candidate` calls `create_pull_request` whenever no open PR is found, with no check of closed or merged PR history for the head branch. The presenter branch name is a constant (`presenter_branch_name()` returns `PRESENTER_BRANCH`), so after a presenter PR is merged or closed the next run that finds no open PR opens a duplicate PR for content already merged or declined upstream. `create_pull_request`'s own docstring treats 'none open' as 'never existed'.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/github/client.py:543` (`state=open`); `client.py:560-585` (`create_pull_request` after the open lookup) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:301-317` (create when `existing_pr is None`); `effect.py:97-102` (constant branch) |

**Id** REV-V1-08 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 8 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows that when a closed or merged PR exists for the presenter head branch, `propose_candidate` does not create a new PR and reports the prior outcome; `grep -n 'state=' src/repository_presenter/core/github/client.py` shows the lookup covers `state=all` (or a separate closed lookup) for the head branch.

## Resolved

### `review.cited_paraphrase_whole_fact_dilution`

`_cited_paraphrase`'s overlap ratio was computed against a fact's *entire* bundled value rather
than the specific bullet a quote restates, producing false-positive `REJECT_FACTUAL` findings on
any multi-bullet fact.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-words-foss/Aspose.Words-FOSS-for-.NET` | 2026-09-17 10:32 UTC | `docs/DECISION_LOG.md`, F05 |
| 2 | `aspose-email-foss/Aspose.Email-FOSS-for-Python` | 2026-09-23 09:59 UTC | `docs/DECISION_LOG.md`, F08 |

**Fixed** 2026-09-24, commit `9596a92` (`_value_segments` scopes the check per-bullet;
`REVIEWER_LOGIC_VERSION` 11→12). Verified against Email-Python's own reseal (F08 did not recur).

### `composition.planning.rc01_backstop_vs_link_ceiling_trim_ordering`

`planning.py`'s `plan_checks` ran the RC-01 links backstop (which appends every disposition-
required `link_target` fact a unit names, per `_missing_links`) *before* the Aspose-link-ceiling
trim (`DEFAULT_POLICY.aspose_links_max`). The trim then kept only the first N Aspose-domain links
it encountered in the disposition's own `fact_ids` insertion order — which carries no priority
signal at all — silently dropping whichever backstop-appended, deterministically-required link
landed last. The trim's own reasoning (favor whichever links the model named first) is sound for
the model's own free-choice links; it does not hold for backstop-injected ones, which the model
never chose to prioritize in the first place.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET` | 2026-09-17 10:53 UTC | `docs/DECISION_LOG.md` on branch `item92-slides-net-redraw` (commit `654d115`, never merged to `main`) |

**Correction, 2026-09-27: this entry's own previous text (added 2026-09-26) was wrong about the
fix's own status.** It read "Proposed fix, not implemented" from the stranded `item92-slides-net-
redraw` branch (a docs-only sighting, commit `654d115`) alone, without checking whether `main` had
already landed a fix independently. It had: commit `4b92ce3` (G4-W17 items 120/122/125), landed the
*same day* as the sighting, roughly 6.5 hours later, names this exact repository and mechanism in
its own commit message and inline comments. `4b92ce3` is confirmed an ancestor of `origin/main`
(`git merge-base --is-ancestor`).

**Fixed**, `4b92ce3` (`composition/planning.py::plan_checks`): `_required_link_sections` computes
every `VERIFIED_REWRITE`-required `link_target` independent of the plan's own links; `required_aspose`
counts how many of those are Aspose-domain; `trim_ceiling = max(policy.aspose_links_max -
preserved_aspose - required_aspose, 0)` reserves that many slots before the trim ever runs; and the
trim loop (`if is_aspose and target not in required_link_sections`) never removes a required link
regardless of insertion order — only the model's own optional Aspose links are still trimmed.
Offline test `test_five_disposition_required_aspose_links_survive_the_ceiling_trim_unconditionally`
(`tests/components/readme/composition/test_planning.py`) mirrors this repository's own original
five-links-against-a-ceiling-of-four shape byte for byte and passes.

**Verified live, 2026-09-27**, four fresh `present --repo aspose-slides-foss/Aspose.Slides-FOSS-
for-.NET --fresh` draws in an isolated worktree, current revision `86c441b5d81e707f2ea9e01b197dbb6ff7a3859b`:
every draw that reached `plan.json` (three of four) produced it with no link-completeness-gap defect
(`tests/test_bundle_audits.py::test_no_link_completeness_gap`'s own check class). This revision's
own `dispositions.json` no longer names a `VERIFIED_REWRITE` with five `link_target` facts against
the ceiling of four (content has drifted since the original 2026-09-17 sighting) — so this is
corroborating evidence the mechanism no longer misbehaves in the real pipeline, not a byte-for-byte
reproduction of the original failing shape followed by a live clear. Combined with the fix reading
correct by construction and the offline test's exact mirror of the original shape, that is enough to
close this entry.

**Repository still not sealed, for a wholly separate, unrelated reason**, out of this mechanism's own
scope. Draw 1: `HTTP 500` from the LLM gateway at S3 `repository_investigation` (3 retries exhausted;
cleared on retry, did not recur — flaky-backend class already documented elsewhere in this file's
history). Draw 2: got past S3-S8, then `HTTP 504` unreachable on the GitHub `.../issues` reachability
check at BC-06 (cleared on retry, did not recur — flaky-network class, also already documented).
Draws 3 and 4: both got past BC-06 and both were rejected `REJECT_PRESENTATION` at S9/BC-10 after one
repair round each — the same causal stage and section both times (`causal_stage: S7`, `section_id:
key_capabilities`), but a *different* specific finding each time (draw 3, F07: "the candidate
rewrites the original README's 'At a glance' Mermaid diagram as a simplified flowchart in 'Key
Capabilities', losing the original's structure and XML output references"; draw 4, F03: "the
candidate's Key Capabilities section is a generic template that omits specific capabilities like 3D
properties and document properties, which are verified by the original README's 'What it can do'
list"). Two equivalent failures at the same stage/section (draws 3 and 4) is this session's own
stopping point per `AGENTS.md`'s two-equivalent-attempts rule — a fifth draw was not attempted.
Notably, a *prior* session's own `docs/DECISION_LOG.md` entry (the `coordinate_neighbor_promises`/
BC-10 verification, PR #129) drew this exact same revision twice and got a clean `ACCEPT` both times
— so this revision is capable of sealing under the current code; the two S7/`key_capabilities`
rejections here look like this project's own already-documented class-I review-sampling
nondeterminism landing unluckily twice in a row on the same section, rather than a newly-introduced,
reliably-reproducible defect. Recorded honestly, not fixed, and not yet its own arrival-list
admission: `composition`'s S7 authoring/coherence handling of `key_capabilities` for this repository
does not reliably preserve every inherited capability/diagram element the original README carries,
and independent review's presentation criterion can (not always) catch the gap.
