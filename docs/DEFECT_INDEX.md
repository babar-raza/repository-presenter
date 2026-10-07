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

**New sighting, 2026-10-07** (`aspose-note-foss/Aspose.Note-FOSS-for-Python` and
`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`, two independent live transactions): when
`_CARRY_SECTIONS` grew to include `scope_limitations` (Slides-Java F04, 2026-10-05, noted above),
only half the original fix's pairing was repeated - `carried_units` was wired into `must_carry`
(`authoring_tasks`'s direct call), but `section_selections`'s own `scope_limitations` branch was
never given the matching `ids.extend(carried_units(...))` call `development_testing` already had.
Reconciliation's enterprise-rewrite path (`reconciliation/dispositions.py` "PLACING and
destination == enterprise_relationship") supersedes an Enterprise Edition relationship paragraph
into `scope_limitations` with `destination_section` rewritten there; the carry gate then obliged
the section to cite or omit `inherited_unit:084.paragraph`, but citing it (the carry rule's own
first-named compliance: "state their substance in your units") was rejected by `unit_checks`'
"cites facts outside this section's set" check on the identical ID in the identical call - a unit
could neither cite the must-carry unit nor safely ignore the instruction to state its substance.
Both transactions exhausted the one-reask budget (S6, #281) on this exact unit. Fixed by extending
`scope_limitations`' own `ids` with `carried_units`, exactly mirroring `development_testing`
(`composition/authoring.py::section_selections`); no change to `carried_unit_errors` or the
binding check itself. `additional_examples` remains outside `_CARRY_SECTIONS` and is unaffected.

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

### `composition.planning.unit_ids_decode_admits_fact_ids`

S5 `presentation_planning` rejects a plan whose `material_limitations[].unit_ids` holds a real fact
ID of another kind (`identity:*`, `package:*`, `dependency:*`) and burns both of the job's attempts
on it. The array was pinned (item 77) to the same `citable_fact_id` enum as the `fact_ids` arrays,
which contains every fact the planner can see, but the binding admits only `inherited_unit` facts
in a unit array, so the ID decoded and was refused only after the call was spent. The one re-ask
saw a bare "unknown inherited unit X" and repeated the reply.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-email-foss/Aspose.Email-FOSS-for-.Net` | 2026-09-16 | `docs/RESEARCH_LANE_F.md` F22: `package:target_framework` written into `unit_ids`, S5 attempt 1 rejected (attempt 2 succeeded) |
| 2 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | 2026-10-01 | `docs/DECISION_LOG.md` (the refined-check verification entry): a `--fresh` draw failed S5 on "unknown inherited unit identity:ecosystem" |
| 3 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | 2026-10-05 | both S5 attempts of one `--fresh` draw (`calls/*.rejected-{1,2}.json`, retained under `runs/`) filled every `material_limitations[].unit_ids` with the same `identity:*`/`package:java_release`/`dependency:none` IDs as `fact_ids`; `presentation_planning: output rejected twice` |

**Status 2026-10-05**: fix landed on its branch, not yet moved to Resolved. `unit_ids` now has its
own `citable_unit_id` enum (the citable IDs that are inherited units, `planning.citable_unit_ids`);
the binding's message for a real fact of the wrong kind names the field mistake; and
`core/llm/jobs.py` keeps a failed `recover` correction as `rejected-N-fix.json` and reports it after
the model's own rejection. Replayed offline over the 27 sealed bundles: all 81 `unit_ids` citations
lie inside the new enum. Not yet confirmed on a live draw of sighting #3's repository.

### `registry.write_gate_unwired_mode_unenforced` (REV-V1-01)

`core/registry/loader.py::is_permitted` is the registry's write gate (a `disabled` entry is analyzed but never proposed to), yet nothing in `src/`, `scripts/` or `.github/workflows/` calls it. Every admission point uses the read gate `require_listed`, and `mode` (`full` / `dry_run` / `disabled`, `core/registry/models.py`) is only printed, never branched on. The live registry is recorded as 34 entries (full 2, dry_run 29, disabled 3, `docs/RESEARCH_AND_GUIDELINES.md:775`), so 32 of 34 are intended not to be proposal-eligible and nothing enforces that.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/registry/loader.py:54` (definition); the only other references are `tests/core/registry/test_loader.py:85,126,130` |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:966,1106,1383,1677` (`require_listed` at all four admission points); `cli.py:967,1108,1385` (`mode` printed only) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py` (no reference to `mode` or the registry) |

**Id** REV-V1-01 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 1 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: grep shows `is_permitted` has a production caller in `run_propose` (and in the effect path) and a test that a `dry_run` and a `disabled` entry are each refused before any write call; `grep -rn is_permitted src/` returns more than the definition.

**Work item** G6-W05 · **Register status** FIXED(#241) · registry write gate `core/registry/write_gate.py:24` (`WritePermit`); propose, metadata apply and issue filing call it. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `propose.candidate_state_and_registry_not_checked` (REV-V1-02)

`run_propose` reads `--readme-file` directly with no `load_registry` / `require_listed`; the default path consults the registry but only tests that `CURRENT` and `README.md` exist, never `manifest.json`'s `state`. `core/candidates.py` (`COUNTED_STATES = {READY_FOR_PROPOSAL}`) documents that `CURRENT` can point at a revision that is not `READY_FOR_PROPOSAL`. Reproduced on live data: `candidates/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/CURRENT` is `620a2614...` whose manifest state is `VALID_UPDATE_AVAILABLE`, so the default path would propose that non-final candidate. `.github/workflows/propose.yml` takes `repo` and `readme_file` as free-text `workflow_dispatch` strings with no registry or state pre-check.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1090-1124` (`--readme-file` branch skips the registry; default branch checks only file existence) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/candidates.py:37` (`COUNTED_STATES`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/620a2614418854b4a18966a361e6907ddc88c7cb/manifest.json:111` (`state: VALID_UPDATE_AVAILABLE`) reached by `CURRENT` |
| 4 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:38-47` (free-text dispatch inputs) |

**Id** REV-V1-02 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 2 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows `run_propose` refuses a `CURRENT` whose manifest state is not `READY_FOR_PROPOSAL` (using the Slides-Java shape above), and refuses a `--readme-file` for a repository that is not a registry entry permitted by `is_permitted`; `grep -n READY_FOR_PROPOSAL src/repository_presenter/cli.py` finds the gate.

**Work item** G6-W05 · **Register status** FIXED(#241,#229) · only a verified READY_FOR_PROPOSAL CURRENT bundle at the live revision; dispatch inputs validated. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `propose.workflow_shell_injection_and_shared_write_token_job` (REV-V1-03)

`.github/workflows/propose.yml` substitutes `${{ inputs.repo }}`, `inputs.expires_in_minutes`, `inputs.readme_file`, `inputs.source_revision` and `inputs.base_branch` directly into `run:` script text before bash parses it (the standard GitHub Actions script-injection class; YAML-level quoting does not help). The file has one job, `propose`, which holds the untrusted-input steps, the dry run, and the write-scoped App token mint (`actions/create-github-app-token@v2`), so injected shell runs with the write token reachable in the same runner.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:92,100,101,102,104,105` (`${{ inputs.* }}` inside `run:` blocks) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:70-71,117,134` (single `propose` job; token mint and `GH_PROPOSAL_WRITE_TOKEN` in the same job) |

**Id** REV-V1-03 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 3 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -n 'inputs\.' .github/workflows/propose.yml` shows each input reaches `run:` only through an `env:` mapping (never inline), the dry run and the token-minting write step are separate jobs with the mint in the write job only, and a workflow-audit test in `tests/` asserts both.

**Work item** G6-W05 · **Register status** FIXED(#229) · inputs through `env:`, strict allow-patterns, separate dry-run and write jobs, `propose.yml:112` concurrency group. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `propose.authorization_self_minted_self_validated` (REV-V1-04)

`authorize_proposal` is a plain constructor with no validation; `run_propose` computes `candidate_hash = sha256_text(readme_text)` and passes it in, then `propose_candidate` calls `validate_authorization` with `expected_candidate_hash=sha256_text(readme_text)` over the same `readme_text`, plus the same repository, revision and branch values. No independently sourced record (a persisted approval or a separate approver) is checked, so validation can only detect a clock or in-process mismatch. The only external gates are the `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` variable and token presence, both set by whoever submits the dispatch form that also chose the target and file.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/authorization/proposal.py:55-85` (`authorize_proposal`, no validation) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1126-1139` (hash computed and authorization built in one call) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:205-218` (`write_authorized`, then `validate_authorization` over the same values) |

**Id** REV-V1-04 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 4 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `propose_candidate` accepts an authorization record loaded from a source the author path cannot write (a sealed-bundle approval or a separate approver artifact), a test shows a record whose `candidate_hash` was not independently approved is refused, and a test shows a record minted in the same process without that approval is refused.

**Work item** G6-W05 · **Register status** FIXED(#241) · reviewed record under `ops/proposal-authorizations/`, accepted only if merged before the trigger commit. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `propose.app_only_token_is_workflow_convention` (REV-V1-05)

PARTIAL: the claim that the code accepts any `GH_TOKEN` is wrong. The write path reads only `GH_PROPOSAL_WRITE_TOKEN` and `effect.py` states it refuses `GH_TOKEN`. The surviving part is real: nothing in code checks that the value in `GH_PROPOSAL_WRITE_TOKEN` is a GitHub App installation token (`effect.py` documents App tokens only 'in principle'; there is no prefix or claims check in `core/github/client.py` or `effect.py`). The 'App only' guarantee therefore lives in the `propose.yml` mint step, so a local or differently authored run with a hand-set PAT is treated identically.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1153-1161` (reads `GH_PROPOSAL_WRITE_TOKEN`, never `GH_TOKEN`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:22-25,109` (App token 'in principle'; `_NO_TOKEN_REASON`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/propose.yml:115-125` (the only enforcement) |

**Id** REV-V1-05 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 5 (PARTIAL), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: either a runtime check that rejects a non-App-installation token before any write (a test with a PAT-shaped value is refused), or a documented decision that the YAML-only guarantee is accepted, with the audit test that pins the mint step; a grep of `src/repository_presenter/components/propose/` for the token-shape check shows which.

**Work item** G6-W05 · **Register status** PENDING · part FIXED(#241): installation token scoped to the target, App id attested on the PR after the first write; open: no pre-write App-token proof. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `metadata.description_overwrite_and_topics_full_replace` (REV-V1-06)

`diff_against_observed` flags `description_changed` on any difference with no quality or maintainer-authorship guard, and `apply` then calls `update_repository` unconditionally with the proposed description. `replace_topics` is `PUT /repos/{owner}/{repo}/topics`, a full replace, while `propose_topics` derives only a small deterministic set, so any maintainer-added topic outside it is dropped on write. Latent, not armed: no workflow in `.github/workflows/` invokes the `metadata --apply` path and `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED` is unset in this project's environment.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/metadata/proposal.py:210-212` (`description_changed`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/metadata/apply.py:157-181` (unconditional update once authorized) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/github/client.py:222-242` (`replace_topics`, full replace); `src/repository_presenter/components/metadata/proposal.py:141-168` (`propose_topics`) |

**Id** REV-V1-06 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 6 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows an existing non-empty maintainer description is not overwritten without an explicit owner decision, and a test shows `apply` merges the observed topics into the proposed set (union) rather than replacing them; `grep -rn replace_topics src/` shows the caller passes a union.

**Work item** G6-W05 · **Register status** FIXED(#240) · description replaced only when weak; topics merged, never replaced; live re-read before write. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `issues.filing_global_gate_no_per_handoff_approval` (REV-V1-07)

`issues-scheduled.yml`'s `file-and-close` job is gated only by `vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED == '1'` and fans out over every repository with a `HANDOFF_PENDING` or `FILED` handoff (`_ACTIONABLE_STATES`). When omitted, `file-upstream-defects --repo` files every `HANDOFF_PENDING` handoff. Live data: the Aspose.HTML-FOSS-for-Python and Aspose.TeX-FOSS-for-Python handoffs are both `HANDOFF_PENDING` today, so one repository variable set to `1` would file both as real issues against real `aspose-*-foss` repositories in one scheduled run with no review of either body.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/issues-scheduled.yml:143,149` (sole gate; matrix over all targets) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:438,787,797` (files all `HANDOFF_PENDING` when `--repo` omitted; `_ACTIONABLE_STATES`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `evidence/upstream-defects/aspose-html-foss__Aspose.HTML-FOSS-for-Python/ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a.json:32` and `evidence/upstream-defects/aspose-tex-foss__Aspose.TeX-FOSS-for-Python/c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188.json:28` (`status: HANDOFF_PENDING`) |

**Id** REV-V1-07 · **Severity** High · **Status** Open, awaiting independent reverification; a further fix (the gated close path, work item `fix/issue-close-gate-1005`, PR #257) is merged on GitHub; the entry remains open until independently reverified. Source: independent reviewer finding, verification report V1 item 7 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: filing requires a per-handoff approval recorded outside the filing job (a handoff-level field or approval artifact checked by `file-upstream-defects --file`), a test shows an unapproved `HANDOFF_PENDING` handoff is not filed when the global variable is `1`, and the workflow matrix is restricted to approved handoffs.

**Work item** G6-W05 · **Register status** FIXED(#237,#257) · per-handoff approval for filing (#237); the gated close path and filing token provenance (#257). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `propose.pr_lookup_open_only_recreates_merged_pr` (REV-V1-08)

`find_open_pull_request` queries `pulls?head=...&state=open`, and `propose_candidate` calls `create_pull_request` whenever no open PR is found, with no check of closed or merged PR history for the head branch. The presenter branch name is a constant (`presenter_branch_name()` returns `PRESENTER_BRANCH`), so after a presenter PR is merged or closed the next run that finds no open PR opens a duplicate PR for content already merged or declined upstream. `create_pull_request`'s own docstring treats 'none open' as 'never existed'.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/github/client.py:543` (`state=open`); `client.py:560-585` (`create_pull_request` after the open lookup) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/propose/effect.py:301-317` (create when `existing_pr is None`); `effect.py:97-102` (constant branch) |

**Id** REV-V1-08 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V1 item 8 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05 and still holding. Fixes are tracked by the 'write-path hardening' work items; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows that when a closed or merged PR exists for the presenter head branch, `propose_candidate` does not create a new PR and reports the prior outcome; `grep -n 'state=' src/repository_presenter/core/github/client.py` shows the lookup covers `state=all` (or a separate closed lookup) for the head branch.

**Work item** G6-W05 · **Register status** FIXED(#241) · `core/github/client.py:328` lists PR history with `state=all` before any write. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `snapshot.community_paths_dead_code` (REV-V4-01)

`core/snapshot/inventory.py` declares and populates `FileInventory.community_paths` in `scan()`, but no module in `src/` outside `inventory.py` reads it; the only other consumer is `tests/core/snapshot/test_inventory.py` (assertions only). `AGENTS.md` states 'a module with no production importer is a defect'. The project already acknowledges this (`docs/DECISION_LOG.md:3671`; the WS2 ruling, 2026-09-17, `docs/DECISION_LOG.md:3681`), so this entry tracks it as an open defect rather than a known note.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/snapshot/inventory.py:52,75-83` (declaration and population) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `tests/core/snapshot/test_inventory.py:49-75` (the only other reader) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/DECISION_LOG.md:3671` (self-acknowledged dead code) |

**Id** REV-V4-01 · **Severity** Low · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 1 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -rn community_paths src/` shows a production reader outside `inventory.py` (for example the metadata or community-file component), or the field is removed with its test; either way a reviewer finds no write-only field.

**Work item** G4-W18 · **Register status** PENDING · `core/snapshot/inventory.py:52` `community_paths` has no reader. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `github.no_releases_audit_no_product_agent_ingest` (REV-V4-02)

`core/github/client.py` and `read_client.py` enumerate every REST call the project makes (repos, topics, issues, git refs, contents, pulls, commits, trees); there is no `/releases` call and no stargazers, forks or watchers read anywhere in `src/`. `schemas/facts.schema.json` has no `release` field. `plans/idea.md` ('Product Agents', lines 466-478) says product agents supply release changes to the central agent and names `ProductFactsV2` as the mechanism, but `ProductFactsV2` has no implementation in `src/` or `schemas/`. The WS2 ruling (2026-09-17, `docs/DECISION_LOG.md:3681`) records the Releases and package-links audit as a priority 'not yet built' and GitHub-generated-metadata auditing as plan-only.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/github/client.py:1-3`, `src/repository_presenter/core/github/read_client.py:183-199` (no `/releases`; only `default_branch` read from repo metadata) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `schemas/facts.schema.json` (no `release` field); `grep -rn ProductFactsV2 src schemas` returns nothing |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:466-478`; `docs/investigations/02-repo-metadata-community-files.md:261-263` (open question: needs owner input); `docs/DECISION_LOG.md:3681` |

**Id** REV-V4-02 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 2 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -rn '/releases' src/repository_presenter/core/github/` shows a read-only releases audit with a test, a `release` fact kind exists in `schemas/facts.schema.json` with an extractor, and `ProductFactsV2` has a schema and an ingest path or an owner decision withdrawing it is recorded in section 31.

**Work item** G4-W19 · **Register status** OWNER · OWNER-17; no `/releases` call in `src/` (REG-07). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `assets.visual_assets_social_preview_deferred` (REV-V4-03)

No `social_preview` or `visual_asset` code exists in `src/`. `plans/idea.md:513-522` ('Visual Assets and Social Preview') makes this part of the central agent's intended responsibility but not required for the initial pilot, treats the social preview as a manual-UI surface until GitHub documents a supported automation, and `plans/idea.md:535-536` places full delivery outside the README POC's required scope. The absence matches the authority's own deferral, so this is informational, logged so the intended-but-unbuilt capability stays visible.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rn 'social_preview\|visual_asset' src/` returns no files |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:513-522,535-536` (deferral) |

**Id** REV-V4-03 · **Severity** Low · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 3 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a reviewer confirms `plans/idea.md:513-536` still defers the capability (then this entry stays informational), or a component exists under `components/` registered in `docs/REPOSITORY_LAYOUT.md` with a test and a manual-UI step recorded for the social preview.

**Work item** G4-W19 · **Register status** OWNER · OWNER-17; deferred by `plans/idea.md`, recorded as deferred (REG-12). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `prompts.registry_lacks_owner_dependency_hash_and_inline_scan` (REV-V4-04)

`schemas/prompt-manifest.schema.json` sets `additionalProperties: false` and defines no `owner` or `dependency_hash` field, so either would be rejected; `core/llm/prompts.py::PromptManifest` (`extra="forbid"`) mirrors it. The only hash is `LoadedManifest.sha256`, the whole file's own content hash, not a reference to an upstream dependency. The module docstring says prompt content 'never' appears as a string literal in code, but no scan of `src/` enforces it; `tests/test_schemas.py:270-272` only checks that an extra `few_shot` field is schema-rejected.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `schemas/prompt-manifest.schema.json:7-22` (closed field set, no `owner`, no `dependency_hash`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/llm/prompts.py:98-116,141-145,200` (`PromptManifest`, `LoadedManifest.sha256`); docstring at `prompts.py:1-4` |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `tests/test_schemas.py:270-272` (not an inline-prompt scan) |

**Id** REV-V4-04 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 4 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `schemas/prompt-manifest.schema.json` and `PromptManifest` both define `owner` and a dependency hash, every manifest under `prompts/` carries them, and a test fails when `src/` contains a prompt-like literal outside a manifest (a negative control that plants one).

**Work item** G7-W08 · **Register status** PENDING · prompt-manifest schema has no owner or dependency-hash field. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `tests.stale_known_blocked_entries_and_registry_contradiction_control_gap` (REV-V4-05)

PARTIAL, recorded as the verifier narrowed it. EXACT: `tests/test_sealed_bytes.py:129-232` holds exactly three live `KNOWN_BLOCKED_STALE` entries, `aspose-cells-foss__Aspose.Cells-FOSS-for-.NET` (item 65, since 2026-09-11) and `aspose-3d-foss__Aspose.3D-FOSS-for-Python` and `aspose-slides-foss__Aspose.Slides-FOSS-for-Python` (item 69, since 2026-09-16); five sibling item-69 entries were removed on real re-seals between 2026-09-23 and 2026-10-01 and these three have not had that re-seal. OVERSTATED: the claim that Go, .NET and Rust lack negative controls is wrong for Rust, which has a contradiction control at `tests/components/readme/extractors/platforms/test_rust.py:308-342` (`test_a_crate_the_registry_does_not_carry_contradicts_the_install_claim`, asserting `polarity == "CONTRADICTED"`). The real gap is one specific case, a registry 'not found' observation that contradicts the install claim: `test_go.py` and `test_net.py` only assert the weaker 'unreadable registry is UNRESOLVED, never CONTRADICTED' shape (`test_go.py:240-305`, `test_net.py:256-292`), and the same gap exists for Java and TypeScript, so it is not unique to Go and .NET. Go and .NET still carry other negative controls (unreadable registry, missing manifest or toolchain, unparseable manifest).

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `tests/test_sealed_bytes.py:129-232` (three stale entries; comments at 175-231 record the five removed siblings) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `tests/components/readme/extractors/platforms/test_rust.py:308-342` (the Rust control that exists) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `tests/components/readme/extractors/platforms/test_go.py:240-305`, `test_net.py:256-292` (UNRESOLVED shape only; no CONTRADICTED case) |

**Id** REV-V4-05 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 5 (PARTIAL), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `KNOWN_BLOCKED_STALE` in `tests/test_sealed_bytes.py` is empty or each remaining entry names a dated owner decision, and the Go, .NET, Java and TypeScript platform tests each contain a registry-'not found' case asserting `CONTRADICTED` (grep `CONTRADICTED` in each `test_<ecosystem>.py`).

**Work item** G7-W08 · **Register status** PENDING · part FIXED(#235) dated debt and Go/.NET controls; open: Java/TypeScript controls, three stale re-seals. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

**Fix in flight or landed:** PR #235 (merged on GitHub 2026-10-04; dated test debt and Go/.NET negative controls) - not yet reverified.

### `issues.redetect_imports_python_ecosystem_extractor` (REV-V4-06)

`components/issues/redetect.py` imports `RegistryObservation` and `observe_pypi` from `components/readme/extractors/platforms/python_registry.py` (its docstring names the dependency). That is a cross-component, single-ecosystem import: `AGENTS.md` requires ecosystems to be added through registries and forbids one ecosystem's extractor being imported across stages (`RESEARCH_AND_GUIDELINES.md` section 7.4), and a BC-02 upstream-defect handoff from Go, .NET, Rust, Java and others has no re-detection path; only PyPI-backed findings can be re-checked.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/issues/redetect.py:58-61` (the import); self-documented at `redetect.py:17-20` |

**Id** REV-V4-06 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 6 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -n 'extractors.platforms' src/repository_presenter/components/issues/redetect.py` returns nothing, registry observation goes through a registered per-ecosystem interface, and a test re-detects a non-Python handoff.

**Work item** G7-W08 · **Register status** FIXED(#235) · issues/extractor import boundary. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

**Fix in flight or landed:** PR #235 (merged on GitHub 2026-10-04; issues/extractor import boundary) - not yet reverified.

### `docs.stale_paths_roadmap_and_idea_products_json` (REV-V4-07)

`docs/PRODUCTION_ROADMAP.md:30` cites `components/repo_metadata/{capture,proposal}.py` and `:31` cites `components/readme/upstream_defects/ledger.py` as landed; neither path exists. The real files are `components/metadata/{capture,proposal}.py` and `components/issues/ledger.py` (`docs/REPOSITORY_LAYOUT.md:83` and `:51`). `plans/idea.md:151` and `:396` name `data/products.json`, which does not exist; the allow-list is `data/registry.json`, and the authority note at the top of `idea.md` does not map one to the other, so it is an unresolved stale reference.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/PRODUCTION_ROADMAP.md:30,31` versus `docs/REPOSITORY_LAYOUT.md:51,83` |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:151,396` versus `data/registry.json` (the only file in `data/`) |

**Id** REV-V4-07 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 7 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `grep -n 'repo_metadata\|upstream_defects/ledger' docs/PRODUCTION_ROADMAP.md` returns nothing, each cited path exists on disk, and `plans/idea.md` either maps `data/products.json` to `data/registry.json` in its authority note or no longer names it (owner decision, since `plans/idea.md` is the human authority).

**Work item** G7-W08 · **Register status** FIXED(#235) · PRODUCTION_ROADMAP paths; the idea.md wording is OWNER-18. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

**Fix in flight or landed:** PR #235 (merged on GitHub 2026-10-04; `docs/PRODUCTION_ROADMAP.md` path corrections only, `plans/idea.md` `data/products.json` left as an owner decision) - not yet reverified.

### `seal.ready_for_proposal_acceptance_profile_advisory` (REV-V4-08)

`components/readme/bundle/seal.py` states in its own comment that the acceptance profile (`review/acceptance/profile.py`) is UNRATIFIED and its scorer ADVISORY, so no blocking check reads it. `docs/STATE_MACHINE.md`'s transition table for `READY_FOR_PROPOSAL` to `AWAITING_AUTHORIZATION` to `PROPOSING` names no acceptance-profile score as an input, so a candidate becomes sealed, counted and proposal-eligible on BC-01..11 and the no-op proof alone. Severity is bounded by `AGENTS.md`'s rule that candidate acceptance never implies publication authorization and by the credential gate in front of any write, so the gap is an overclaim of quality, not an unauthorized effect.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/bundle/seal.py:86-90` (UNRATIFIED, ADVISORY) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/STATE_MACHINE.md:140-142` (transition table with no acceptance-profile input) |

**Id** REV-V4-08 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 8 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: either the owner ratifies the profile and a blocking check reads its score before `READY_FOR_PROPOSAL` (a test shows a below-threshold candidate is not sealed READY), or `docs/STATE_MACHINE.md` and the progress counter state that READY means 'blocking checks and no-op proof only'; the `seal.py` comment no longer says UNRATIFIED/ADVISORY without a matching doc statement.

**Work item** G3-W02 · **Register status** OWNER · OWNER-13 (same ruling as REV-V2-02); `bundle/seal.py:99-104` comment. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `status.docs_disagree_with_code` (REV-V4-09)

Three concrete cases. (1) `project/state.yaml` G7-W05 (line 131): the 2026-10-01 claim that 'all six failure modes were exercised for real' was admitted overclaimed on 2026-10-04; the six exercises are unit-level only (`tests/core/state/test_recovery.py`, `tests/core/llm/test_jobs.py` via `httpx.MockTransport`) and no hosted run or live gateway exercise is recorded. (2) `project/state.yaml` G5-W04 (line 83): the purpose text says the durable-state backend is 'deliberately NOT wired' into `present`, and a 2026-10-04 correction (wiring audit, `origin/main` `ecdff0dc`) says that is stale because `present --durable-state` wraps one run and `.github/workflows/present.yml` sets the flag. (3) the stale paths in `docs/PRODUCTION_ROADMAP.md` (REV-V4-07). Items 1 and 2 are the project's own dated self-corrections, recorded here as evidence of the defect class; `project/state.yaml` is not edited by this entry.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `project/state.yaml:131` (G7-W05, 2026-10-04 self-correction: unit-level only) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `project/state.yaml:83` (G5-W04, 2026-10-04 correction: 'deliberately NOT wired into present' is stale); `src/repository_presenter/cli.py:308` (`--durable-state`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/PRODUCTION_ROADMAP.md:30,31` (see REV-V4-07) |

**Id** REV-V4-09 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 9 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `project/state.yaml` G5-W04's purpose text no longer says 'deliberately NOT wired', G7-W05's acceptance cites a hosted or live exercise for each of the six failure modes (or its status is lowered), and `docs/PRODUCTION_ROADMAP.md` cites only existing paths; a docs-vs-code audit (a test that every path named in the roadmap exists) passes.

**Work item** G7-W09 · **Register status** PENDING · cursor claims are edited only by the cursor owner. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `wiring.discovery_unreached_and_three_states_never_assigned` (REV-V4-10)

PARTIAL, recorded as the verifier narrowed it. CONFIRMED: `tools/discovery/portfolio_discovery.py` has no importer under `src/repository_presenter/`, no CLI subcommand wires it, and it appears only in its own test, `tools/research_sweep/test_proposal_sweep.py` and prose; `AGENTS.md` calls a module with no production importer a defect. CONFIRMED: `AWAITING_AUTHORIZATION`, `PROPOSING` and `MONITORING` exist in `core/state/schema.py` and the path-finding helper in `core/state/present_transaction.py`, but are never assigned to a real candidate's manifest; sealed bundles only reach `ACCEPTED`, `READY_FOR_PROPOSAL`, `INVALIDATED` or `VALID_UPDATE_AVAILABLE`. NOT a defect as first claimed: `metadata apply` and the GitHub write functions (`update_repository`, `replace_topics`, `create_issue`, `close_issue`, `create_pull_request`, `update_pull_request`, `put_contents`, `create_ref`) ARE wired through the CLI (`run_metadata` with `--apply`, `components/issues/file.py`, `components/propose/effect.py`); they are credential-gated and never live-exercised, which is a different, narrower problem.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `tools/discovery/portfolio_discovery.py` (importers: its test and `tools/research_sweep/test_proposal_sweep.py` only); `grep -n discovery src/repository_presenter/cli.py` returns nothing |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/state/schema.py:44-46,73-88,132-136`; `src/repository_presenter/core/state/present_transaction.py:202-242` (states only in transition tables and path-finding) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:42-44,566,941,1024,1078-1084` (write functions wired, credential-gated, never live) |

**Id** REV-V4-10 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V4 item 10 (PARTIAL), re-read directly against `origin/main` `ce355281` on 2026-10-05. Fixes are tracked by the owning work items named in the matching `docs/DECISION_LOG.md` entry (the 'write-path hardening' items for write-path findings); the fix PR will be named in a follow-up entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `portfolio_discovery` has a production importer (a CLI subcommand or workflow) with a test, or is removed per the reuse manifest; a real candidate manifest reaches `AWAITING_AUTHORIZATION`/`PROPOSING`/`MONITORING` through the effect path (a production-shaped proof against the disposable target), or the states are documented as reserved; the credential-gated write functions get their live proof under the active gate.

**Work item** G4-W18 · **Register status** PENDING · write functions wired (#241, #237, #240); discovery has no importer, three states never assigned. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `autonomy.drift_to_reseal_to_propose_chain_not_wired` (REV-V3-01)

`.github/workflows/monitor.yml` triggers on `schedule` (every 6 hours) and `workflow_dispatch`, and its `drift` job's only effect is `actions/upload-artifact@v4` of `runs/monitor/`; it never calls `gh workflow run`, emits a `repository_dispatch`, or invokes `present.yml` or `propose.yml`. `present.yml` triggers on `workflow_dispatch` and `repository_dispatch` only (no `schedule:`), and `propose.yml` on `workflow_dispatch` only with a manual `repo` input. `plans/idea.md:317-319` (Gate B) requires 'reopen only drifted repositories at their earliest affected boundary, independently reseal every changed candidate'; the drift, reopen and reseal chain has no wiring.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/monitor.yml:27,160` (schedule; the only effect is the artifact upload) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/present.yml:31-38` and `.github/workflows/propose.yml:37-38` (manual and dispatch triggers only) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:317-319` (Gate B) |

**Id** REV-V3-01 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 1 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: G7-W06 (unattended scheduling) and the Gate B wiring; no separate work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `monitor.yml` (or a workflow it dispatches) triggers `present.yml` for each `DRIFTED` repository, a hosted run shows a drifted canary reopened and resealed without a manual dispatch, and `propose.yml` is still reachable only through the authorization gate.

**Work item** G7-W07 · **Register status** PENDING · part FIXED(#242) chain wired in `sealing-scheduled.yml`; open: it has never run (REG-11). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `monitor.hosted_scheduled_run_red_app_installation_404` (REV-V3-02)

`gh run list --workflow=monitor.yml --branch main` shows exactly two runs ever: a `workflow_dispatch` on 2026-10-01 (success) and the only scheduled run, 2026-10-04T16:52:41Z (run `37218382559`), conclusion `failure`. Verifier note: the failing step is narrow. 13 of 14 per-owner drift legs passed; the `aspose-html-foss` leg failed at 'Mint a read-only installation token' with `Not Found` (HTTP 404) on `GET /repos/aspose-html-foss/Aspose.HTML-FOSS-for-Python/installation`, a GitHub App installation gap for that owner (the App is not installed there or cannot see the repository), not a gateway or infrastructure outage. With `fail-fast: false`, the single bad leg still turns the run red. `AGENTS.md` requires a red hosted run to be fixed in the same session; this one was not as of verification.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | hosted run `37218382559` (schedule, 2026-10-04T16:52:41Z, failure); step 'Mint a read-only installation token, scoped to this owner's enabled repositories' on the `aspose-html-foss` leg |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `gh run list --workflow=monitor.yml --branch main --limit 5` (two runs: the 2026-10-01 dispatch and this schedule run) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `AGENTS.md` 'Git and Commits' (a red hosted run is fixed immediately) |

**Id** REV-V3-02 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 2 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: OWNER-04 (GitHub App installation across the registry organizations); the App must be installed for `aspose-html-foss`, or that owner's leg must be excluded or made non-fatal by an owner decision; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a scheduled `monitor.yml` run on `main` concludes `success` (or the `aspose-html-foss` leg is excluded by a recorded decision), checked with `gh run list --workflow=monitor.yml --event schedule`; and `gh api` for the App installation on `aspose-html-foss` returns 200.

**Work item** G7-W07 · **Register status** PENDING · part FIXED(#228) notice instead of failure; open: no schedule-fired run since; OWNER-04 still open. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `registry.registry_revision_v1_absent_denominator_is_live_count` (REV-V3-03)

`plans/idea.md:152` says `RegistryRevisionV1` supplies the campaign denominator and every observation's disposition. The type has no hits in `src/` (only `docs/investigations/11-idea-md-gap-analysis.md:92,210`). `project/state.yaml:17-19` sets `denominator: 36` with `denominator_status` stating it tracks `data/registry.json`'s live entry count (owner ruling 2026-09-30, reversing the 2026-09-23 freeze-at-G4 policy), and `data/registry.json` holds 36 entries. This is a deliberate, documented divergence rather than a hidden defect; the requirement in `idea.md` is nevertheless unmet.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rn RegistryRevisionV1 src docs` (only the two gap-analysis lines) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `project/state.yaml:17-19`; `data/registry.json` (36 entries) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:152` |

**Id** REV-V3-03 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 3 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: owner decision (2026-09-30 ruling stands); a frozen-revision type is a proposal only the owner can admit; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: either a frozen `RegistryRevisionV1` schema and loader exist with the denominator derived from a named revision, or `plans/idea.md:152` and the authority note record the live-count ruling; `grep -rn RegistryRevisionV1 src schemas` shows which.

**Work item** G4-W18 · **Register status** OWNER · OWNER-16; names only in the docstring at `bundle/portfolio.py:47-50`. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `status.three_terminal_states_prose_only_four_counts_not_seven` (REV-V3-04)

`PORTFOLIO_AGENT_ACCEPTED`, `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION` and `PR_ELIGIBLE` have no hits in `src/` or `schemas/`; they appear in `plans/idea.md:16,199-200,318-319` and in docs that note the gap. `run_status` prints one `candidates: N/denominator` ratio and a `progress:` line with four counts (ever sealed, integrity-valid, current-code reproducible, independently accepted). `plans/idea.md:212-213` requires portfolio reporting to separate fact-valid, presentation-valid, independently accepted, no-op-proven, source-fresh, publication-eligible and effect-authorized counts.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1278-1289` (`run_status`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:16,199-200,212-213,318-319`; `docs/investigations/11-idea-md-gap-analysis.md:66-67`; `docs/DECISION_LOG.md:3670` |

**Id** REV-V3-04 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 4 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: no work item yet; `AGENTS.md` says progress is counted in one unit only (N/34), so adding counts needs an owner decision; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `repository-presenter status` output includes the source-fresh, publication-eligible and effect-authorized counts (or an owner ruling drops them), and the three terminal state names have a schema or code home; `grep -rn PR_ELIGIBLE src schemas` shows it.

**Work item** G5-W08 · **Register status** FIXED(#243) · `status` reports the seven separated portfolio counts. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `discovery.gate_c0_not_part_of_the_product` (REV-V3-05)

`tools/discovery/portfolio_discovery.py` lives outside `src/` and no production module imports it (the only `src/` mentions are doc comments in `core/github/client.py`). It lists `GET /orgs/{org}/repos?type=public`, and its status taxonomy is `populated|empty|not_found|inaccessible`, not the nine-way inventory `plans/idea.md:290-292` requires (public, private, internal, archived, unmatched, ambiguous, inaccessible, renamed, transferred, by stable provider identity). No workflow references it, and `docs/investigations/11-idea-md-gap-analysis.md:54-62` agrees Gate C0 was built after Gate A, the reverse of the required order. Overlaps REV-V4-10, which records the same unreached module.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `tools/discovery/portfolio_discovery.py:379,386` (`type=public`); status taxonomy near `:363` |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rln portfolio_discovery .github/workflows/` returns nothing |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:290-292`; `docs/investigations/11-idea-md-gap-analysis.md:54-62` |

**Id** REV-V3-05 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 5 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: no work item yet (discovery integration); see also REV-V4-10; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: discovery runs as a scheduled workflow through a CLI subcommand with authenticated all-visibility pagination, records all nine observation classes by stable provider identity, and a test covers private, archived and renamed repositories; `grep -rn portfolio_discovery src/` shows a production importer.

**Work item** G4-W18 · **Register status** PENDING · `tools/discovery/portfolio_discovery.py:379` public repositories only, no importer under `src/` (REG-15). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `present.non_processable_producer_missing_seven_registry_entries_orphaned` (REV-V3-06)

The literal token `NON_PROCESSABLE_NO_IMPLEMENTATION` does not exist; the real tokens are the state `NON_PROCESSABLE` (`docs/STATE_MACHINE.md:126-127,174`, `core/state/schema.py`) and the reason code `NO_IMPLEMENTATION_EVIDENCE` (`components/readme/evidence/processability.py`). The local, non-durable `present` path prints a generic `insufficient_evidence: <reason_code> ...` line and returns `EXIT_INCONSISTENT` without surfacing a `NON_PROCESSABLE` transition. Seven registry entries have no directory under `candidates/` (29 exist) and no recorded disposition: `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, `aspose-font-foss/Aspose.Font-FOSS-for-Python`, `aspose-gis-foss/Aspose.GIS.FOSS-for-.Net`, `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`, `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`, `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`, `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`, because `present` has evidently never been run against them. Verifier note: PR #216 ('feat(readme): NON_PROCESSABLE disposition for README-only placeholders') is OPEN and unmerged, and fixes only the generic durable-state mechanism; it does not run `present` against the seven orphaned entries, so they stay uncovered even if it merges.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1421-1424` (generic `insufficient_evidence` line and exit) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/evidence/processability.py:19,53`; `src/repository_presenter/core/state/schema.py:30,81,112,186` |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `ls candidates/` (29 directories, none for the seven); PR #216 state OPEN, `mergedAt` null (checked 2026-10-05) |

**Id** REV-V3-06 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 6 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: PR #216 (generic durable-state mechanism, open); the seven orphaned entries have no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: PR #216 is merged and `present` has been run against each of the seven entries with a recorded outcome (a `NON_PROCESSABLE` or `insufficient_evidence` disposition, or a sealed candidate); `ls candidates/` or the durable-state records account for all 36 registry entries.

**Work item** G5-W08 · **Register status** PENDING · part FIXED(#216) generic NON_PROCESSABLE producer; open: six entries without a candidate (REG-04). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

**Fix in flight or landed:** PR #216 (merged on GitHub 2026-10-04; the generic NON_PROCESSABLE mechanism only, the seven orphaned registry entries are still uncovered) - not yet reverified.

### `monitor.drift_sha_only_no_reopen_and_local_bundle_bytes_unverified` (REV-V3-07)

PARTIAL, recorded as the verifier narrowed it. CONFIRMED: `components/monitor/drift.py::observe_repository` compares the upstream default-branch head SHA against the sealed bundle's recorded `source_revision` only (`status = "CURRENT" if read.sha == bundle_revision else "DRIFTED"`); no tree or content hash is compared. CONFIRMED: nothing re-enters reconciliation, because `DRIFTED` is only written to the uploaded JSON (`write_drift_document`) and no workflow or code path reopens the candidate (same evidence as REV-V3-01). OVERSTATED: 'cannot see a README overwrite' is wrong, since any upstream content change, including a README edit, produces a new commit SHA and flips the status to `DRIFTED`. The real gap is narrower: the local sealed bundle's own README bytes are never re-verified against anything upstream (`core/candidates.py::verify_bundle` checks only the bundle's internal digest self-consistency, so a tampered bundle with a matching manifest digest passes), and `DRIFTED` repositories are not reopened downstream.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/monitor/drift.py:94` (SHA-only comparison); `:145-149` (`write_drift_document`, evidence only) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/candidates.py:91` (`verify_bundle`, internal consistency only) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:317-318` |

**Id** REV-V3-07 · **Severity** Medium-High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 7 (PARTIAL), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: same Gate B wiring as REV-V3-01; bundle-bytes verification has no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a test shows a `DRIFTED` repository is reopened downstream, and a test shows a sealed bundle whose README bytes were altered with its manifest digest rewritten is detected against the recorded source revision; `drift.py` or `candidates.py` re-derives the README digest from the recorded source.

**Work item** G7-W07 · **Register status** PENDING · `components/monitor/drift.py:94` compares the head SHA only (REG-05). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `noop_proof.soft_exit_code_literal_fresh_process_unreconciled_totals` (REV-V3-08)

Four sub-claims, all confirmed. (1) The hosted `present.yml` no-op rerun checks only the exit code; `run_present_transaction` returns the process exit code unchanged regardless of `classify(exit_code)`, so a run landing at `ACCEPTED` (not proven) exits 0 like one at `READY_FOR_PROPOSAL`, and the workflow cannot tell them apart. (2) `"fresh_process": True` is a hard-coded literal in both proof dictionaries in `seal.py`, not computed or verified. (3) `composition_ledger` drops any `calls.jsonl` line whose `logical_call_id` is not in the composition's `consumed_calls`, so the sealed ledger is not a complete transcript of every attempt (a documented design choice, not a concealed one). (4) `provider_calls_made` is used once, to populate `inputs.provider_calls`; nothing sums provider calls across bundles or cross-checks totals against raw ledger records, which `plans/idea.md:347-352` requires ('per-README and portfolio totals must reconcile with the underlying call records').

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/state/present_transaction.py:372-379` (exit code returned unchanged); `.github/workflows/present.yml` no-op proof step |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/bundle/seal.py:680,874` (`fresh_process: True`); `:356-375` (`composition_ledger`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:1631` (the only `provider_calls_made` use); `plans/idea.md:347-352` |

**Id** REV-V3-08 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 8 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: no work item yet (no-op proof hardening, G5/G7); the zero-call no-op proof is a core `AGENTS.md` requirement; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: the hosted rerun step fails unless the second run's output reports zero provider calls and a byte-identical bundle (a workflow audit test asserts it), `fresh_process` is derived from a recorded process identity rather than a literal, and a test reconciles per-README call totals against the raw ledger.

**Work item** G5-W09 · **Register status** PENDING · PR #250 open. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `operations.missing_safeguards_concurrency_budget_deadman_lease_heartbeat` (REV-V3-09)

Four confirmed gaps. (1) `concurrency:` exists only in `ci.yml`, `issues-scheduled.yml` and `mirror-gitlab.yml`; it is absent from `monitor.yml`, `present.yml`, `propose.yml`, `liveness.yml`, `audit-app-installations.yml` and `verify-app-installation.yml`. (2) No budget or cost cap exists in `src/` (no `budget_cap`, `cost_cap`, `max_provider_calls` or similar) although `docs/STATE_MACHINE.md:488` states 'LLM call and cost budgets are enforced per repository transaction and portfolio run.' (3) `liveness.yml` is a real 30-minute dead-man switch, but it watches stale open PRs, stranded branches and `main` inactivity during an active sprint; it never checks `monitor.yml`'s run history or conclusion, so a silent or failing monitor schedule raises no alert (REV-V3-02's red run is exactly that case). (4) Verifier note: `renew_lease` (`core/state/cas.py:168`) and the `heartbeat_at` lease field exist and are unit-tested (`tests/core/state/test_cas.py:139-192`), but `renew_lease` has no production caller; `run_present_transaction` acquires the lease once and releases it, never renewing during a long hosted run.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -ln '^concurrency:' .github/workflows/*.yml` returns three files |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/STATE_MACHINE.md:488` versus no budget symbol in `src/` |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/liveness.yml:48-136` |
| 4 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/state/cas.py:168` (`renew_lease`); `src/repository_presenter/core/state/schema.py:284` (`heartbeat_at`); `src/repository_presenter/core/state/present_transaction.py:332-381` (no renewal) |

**Id** REV-V3-09 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 9 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: G7 operations hardening; no work item yet for each of the four; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `present.yml`, `monitor.yml` and `propose.yml` each declare a `concurrency:` group, a per-transaction provider-call budget is enforced in code with a test that refuses over-budget runs, `liveness.yml` (or a sibling) alerts on a stale or failed `monitor.yml` run, and `grep -rn renew_lease src/` shows a production caller with a test.

**Work item** G7-W07 · **Register status** PENDING · part FIXED(#239) dead-man for present, FIXED(#229) propose concurrency; open: REG-08, REG-09, REG-10. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

**Fix in flight or landed:** PR #239 (merged on GitHub 2026-10-04; G7-W03 dead-man health check for `present.yml` only, not for `monitor.yml`) - not yet reverified.

### `state.durable_state_used_only_by_present` (REV-V3-10)

`cli.py` imports `GitStateBackend`, the `present_transaction` helpers and `TriggerEventType` from `core.state.*`, and uses them in exactly one place, the `present --durable-state` branch. No other command (`monitor`, `propose`, `status`, `--facts-only`) touches `core.state`. `present.yml` is the only workflow that passes `--durable-state`; `monitor.yml`'s own header says 'this workflow does not use it' and `propose.yml` has no such flag. `AGENTS.md` assigns transitions, invalidation, caching, leases and recovery to deterministic code, so only one of the three effect-adjacent workflows participates. Sequenced by design, but it leaves monitor and propose outside recovery.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/cli.py:229-235` (imports); `:1689-1702` (the only uses) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `.github/workflows/monitor.yml:4` (header: this workflow does not use it); `.github/workflows/propose.yml` (no `--durable-state`) |

**Id** REV-V3-10 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V3 item 10 (CONFIRMED), re-read directly against `origin/main` `ce355281` on 2026-10-05. Owning item: G7 wiring; no work item yet for monitor and propose durable-state use; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `monitor` and `propose` runs record their transitions through `GitStateBackend` (a test shows a `propose` effect advances `AWAITING_AUTHORIZATION` to `PROPOSING` in durable state), and the `monitor.yml` header comment no longer says it does not use the backend.

**Work item** G5-W08 · **Register status** PENDING · durable state is used only by `present`. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.forbidden_edition_name_generated_and_missed_by_bc06` (REV-V2-01)

`plans/idea.md:52` requires every visitor-facing reference to an `aspose.com` product to say 'Enterprise Edition' and never 'commercial edition'. `composition/authoring.py` rewrites 'Enterprise Edition' to lowercase 'commercial edition' in the `enterprise_relationship` unit (`_EDITION = re.compile(r"\bEnterprise Edition\b")`, then `_EDITION.sub("commercial edition", ...)` in `unit_checks`), and its authoring prompt instructs the model to say 'the commercial edition'. The edition-casing guard wired into blocking check BC-06 (`validation/registry.py`, `_EDITION = re.compile(r"\b([A-Z][A-Za-z]+) Edition\b")` inside `_check_links`, registered as `"BC-06": _check_links`) matches only the capitalised form, so it can never match the lowercase string the code generates. Verifier nuance: a separate case-insensitive `edition_name()` exists in `review/acceptance/text_checks.py`, but it is consumed only by the advisory, unratified scorer (REV-V2-02), not by BC-06. Measured: 19 sealed `README.md` files under `candidates/` contain 'commercial edition' (case-insensitive), for example `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/52b0f00ebf28a0b4173921725ff170685ec2c502/README.md:550`, whose manifest is `READY_FOR_PROPOSAL` with review verdict `ACCEPT`.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/authoring.py:255,411,1601` (`_EDITION` regex, prompt text, the substitution) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/validation/registry.py:317,1528` (BC-06 capitalised-only `_EDITION`; `"BC-06": _check_links`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/review/acceptance/text_checks.py:155` (`edition_name`, advisory only) |
| 4 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rli 'commercial edition' candidates --include=README.md` returns 19 files; `plans/idea.md:52` |

**Id** REV-V2-01 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 1 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README composition and validation (authoring rewrite and BC-06); no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `authoring.py` no longer produces 'commercial edition' (a test feeds an 'Enterprise Edition' unit and asserts the output contains 'Enterprise Edition'), BC-06 or another blocking check rejects any case-insensitive forbidden edition substitute (a negative-control test with the lowercase string fails), and `grep -rli 'commercial edition' candidates --include=README.md` returns nothing after the affected candidates are resealed.

**Work item** G3-W06 · **Register status** FIXED(#251) · no generated edition substitute, BC-06 case-insensitive; 17 sealed READMEs still contain the old text (REG-01). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `acceptance.no_blocking_30_point_gate_and_docs_claim_no_scorer_is_false` (REV-V2-02)

`plans/idea.md:118,177,318` require a native 30-point acceptance with zero hard disqualifiers and 30/30 for every processable repository. `review/acceptance/profile.py` states it is 'ADVISORY AND UNRATIFIED': `RATIFIED = False` (line 41), every `Criterion.points` is `None`, and the scorer records a score in `review.json` and blocks nothing. Only one sealed `review.json` carries an `acceptance_profile` block, `candidates/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET/a7c7314b18e1a5bd209fab38c15e72574337366f/review.json`: outcome `UNSCORED`, `ratified` false, four criteria `NOT_MET` (C01, C02, C10, C22), while its verdict is `ACCEPT` and its manifest state `READY_FOR_PROPOSAL`. Verifier nuance: the doc claim at `docs/EXECUTION_STATE_MACHINE.md:491` and `project/state.yaml:111` (both dated 2026-10-04) that there is 'no scorer in `src/`' is itself false: `scorer.py`, `profile.py` and `text_checks.py` exist under `review/acceptance/`, added by commit `12eefef1` (#218) the same day. The docs' wider conclusion (non-blocking, unratified) is correct; the specific sentence is stale. Also, `status --stale` (`cli.py`, `core/candidates.py::stale_candidates`) compares components, validators and validator version only; `dependencies.json` records `contract_version` and `acceptance_profile_version` (`bundle/seal.py:233,242`) but neither is ever compared.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/review/acceptance/profile.py:1-7,41` (`RATIFIED = False`, advisory) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET/a7c7314b18e1a5bd209fab38c15e72574337366f/review.json` (`UNSCORED`, four `NOT_MET`, verdict `ACCEPT`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/EXECUTION_STATE_MACHINE.md:491`; `project/state.yaml:111` (the false 'no scorer in `src/`' sentence, not edited here) |
| 4 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/core/candidates.py:284` (`stale_candidates`); `src/repository_presenter/components/readme/bundle/seal.py:233,242`; `plans/idea.md:118,177,318` |

**Id** REV-V2-02 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 2 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: G3-W02 (acceptance profile; advisory landed in #218) and the owner's ratification decision; the doc correction belongs to the cursor and EXECUTION_STATE_MACHINE owners. Overlaps REV-V4-08; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: the owner ratifies the profile and a blocking check reads its score before `READY_FOR_PROPOSAL` (a test shows a below-30 candidate is not sealed READY), `RATIFIED` is True with every `points` value set, `stale_candidates` compares `contract_version` and `acceptance_profile_version`, and the two docs no longer say 'no scorer in `src/`'; `grep -n 'no scorer' docs/EXECUTION_STATE_MACHINE.md project/state.yaml` returns nothing.

**Work item** G3-W02 · **Register status** OWNER · OWNER-13; `profile.py:41` `RATIFIED = False`; plan row corrected by this PR, cursor text is G7-W09. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `reconciliation.defer_unresolved_unit_not_flagged_for_review` (REV-V2-03)

Counted across every sealed `dispositions.json` whose manifest state is `READY_FOR_PROPOSAL` (28 bundles): 82 `DEFER_UNRESOLVED` entries across 14 of the 28 bundles (13 in Words-FOSS-for-Python, 11 in Words-FOSS-for-.NET, 10 in Slides-FOSS-for-.NET, down to 1 in several). `validation/registry.py::_check_dispositions` (BC-05) checks only that each inherited unit has exactly one disposition and that a placed unit renders where planned; it never inspects which disposition a unit received, so `DEFER_UNRESOLVED` passes like any resolved one. No schema or manifest field surfaces a deferred count (`grep -rn 'DEFER_UNRESOLVED\|deferred' schemas/` returns nothing) and the seal summary carries no such counter. `plans/idea.md:110,463-464` require material detail with no safe destination to fail closed for upstream reconciliation and the gap to be flagged for review; the per-unit omission is correctly fail-closed, but the required flag-for-review visibility does not exist.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/validation/registry.py:846-887` (`_check_dispositions`, BC-05) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `schemas/` (no deferred-unit field); `src/repository_presenter/components/readme/bundle/seal.py` composition summary (no counter) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:110,463-464` |

**Id** REV-V2-03 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 3 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: source reconciliation and bundle summary; no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: the sealed manifest or composition summary records a `deferred_units` count and ids, `repository-presenter status` or the PR body surfaces them for review, and a test shows a candidate with unflagged `DEFER_UNRESOLVED` units is not sealed READY (or is sealed with the flag visible).

**Work item** G5-W08 · **Register status** PENDING · OWNER-14 resolved as a per-class deferral registry (fix/deferral-policy-1007 pending); no reader of DEFER_UNRESOLVED under `validation/` or `bundle/` yet; 14 READY bundles, 82 units. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.canonical_name_enforced_only_in_renderer_slots` (REV-V2-04)

In `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/52b0f00ebf28a0b4173921725ff170685ec2c502/README.md`, line 1 (renderer-owned H1) is the canonical `# Aspose.3D FOSS for .NET`, but authored prose at lines 74, 93, 169, 550 and 554 uses the package shorthand 'Aspose.3D.FOSS' as the sentence subject (for example line 169, 'Aspose.3D.FOSS for .NET provides core 3D scene management'). No rule in `validation/registry.py` forbids a package or namespace shorthand standing in for the product name in model-authored sections; the product-name logic in `authoring.py` (`allowed_identifiers`, `unit_checks`) governs citation and identifier legality, not identity substitution. `docs/README_CONTRACT.md:81` (row 1) defines the rule ('the full product name ... never a package or namespace shorthand') and `plans/idea.md:84-85` requires it, but no blocking check enforces it outside the deterministic H1 and opening slots.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/52b0f00ebf28a0b4173921725ff170685ec2c502/README.md:1,74,93,169,550,554` |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/validation/registry.py` (no shorthand rule); `src/repository_presenter/components/readme/composition/authoring.py` (`allowed_identifiers`, `unit_checks`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/README_CONTRACT.md:81`; `plans/idea.md:84-85` |

**Id** REV-V2-04 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 4 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README validation (a canonical-name check for authored prose); no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: a blocking check rejects a shorthand product name in authored prose (a negative-control test with 'Aspose.3D.FOSS for .NET provides ...' fails), and the affected candidates are resealed so `grep -n 'Aspose.3D.FOSS ' candidates/*/*/README.md` finds no prose use.

**Work item** G3-W06 · **Register status** FIXED(#251) · BC-12 canonical product name. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.link_ceiling_fixed_constant_not_derived` (REV-V2-05)

`composition/policy.py` sets `aspose_links_max: int = 4`, one hard-coded default used identically by every candidate regardless of README length or verified example count, consumed unchanged in `composition/planning.py` and by the BC-06 ceiling check in `validation/registry.py`. `grep -rn 'products_max\|docs_max\|kb_max\|blog_max\|reference_max'` across `src/` and `docs/README_CONTRACT.md` returns nothing, so there is no per-slot products, docs, kb, blog or reference breakdown and no formula that derives a maximum from visible content size or verified examples. `plans/idea.md:61-64` allows repository policy to configure per-slot maxima and otherwise requires conservative maxima derived deterministically from visible content size and verified code examples.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/policy.py:21` (`aspose_links_max: int = 4`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/planning.py:1007,1069-1070`; `src/repository_presenter/components/readme/validation/registry.py:1026` (consumers) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:61-64` |

**Id** REV-V2-05 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 5 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README composition policy; no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `policy.py` derives the ceiling from visible content size and verified example count (or reads repository policy per slot), a test shows two READMEs of different size get different ceilings, and `grep -rn aspose_links_max src/` shows no bare constant used as the final ceiling.

**Work item** G3-W06 · **Register status** FIXED(#246) · derived link ceilings, `composition/link_budget.py`. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.full_featured_enterprise_edition_anchor_not_rendered` (REV-V2-06)

`composition/renderer.py::_enterprise_paragraph` renders exactly `These limitations don't apply to [{name} — Enterprise Edition]({target})`; the word 'full-featured' appears nowhere in `renderer.py` or `components/shell.py`, and `grep -rl 'full-featured' candidates --include=README.md` returns 0 across all sealed candidates. `docs/README_CONTRACT.md:98` (row 18) defines the anchor without 'full-featured', while `docs/EXECUTION_STATE_MACHINE.md:485` still lists the 'below-the-fold full-featured ... Enterprise Edition anchor' as an enforced Gate G1 blocking check, and `plans/idea.md:109` requires an informative full-featured Enterprise Edition anchor below the fold. The authorities disagree with each other and the renderer satisfies neither the idea nor the EXECUTION_STATE_MACHINE claim.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/renderer.py:564-581` (`_enterprise_paragraph`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rl 'full-featured' candidates --include=README.md` returns 0 |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/README_CONTRACT.md:98` versus `docs/EXECUTION_STATE_MACHINE.md:485` and `plans/idea.md:109` |

**Id** REV-V2-06 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 6 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README contract and renderer; needs an owner decision on which wording governs, then a code or doc change; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: either the renderer emits an informative full-featured anchor and a test asserts it (with sealed candidates resealed), or `docs/EXECUTION_STATE_MACHINE.md:485` and `docs/README_CONTRACT.md:98` agree with a recorded owner ruling on `plans/idea.md:109`; `grep -n 'full-featured' docs/EXECUTION_STATE_MACHINE.md docs/README_CONTRACT.md` and the renderer agree.

**Work item** G3-W06 · **Register status** FIXED(#246) · Enterprise Edition anchor rendered. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.badge_row_python_only_runtime_no_build_status_unconditional_contributors` (REV-V2-07)

All four sub-claims confirmed. In `composition/renderer.py::_badges`: the package and license badges are fact-gated; the platform/runtime badge is hard-wired to `context.fact("package:python_requires")`, so no .NET, Java, Go, Rust, C++ or TypeScript equivalent exists; no build-status badge exists anywhere in the renderer; and the contributors badge is appended unconditionally, with no fact lookup or polarity check, unlike every other badge. Empirically, `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/.../README.md:3` renders only NuGet, License and Contributors. `review/acceptance/text_checks.py::single_badge_row` checks only one row and no duplicate URL, never order, and it is advisory only (REV-V2-09). `plans/idea.md:75-78` requires one compact badge row in the stable order package or release, platform/runtime, real build status, license, then contributors.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/renderer.py:238-279` (`_badges`; runtime badge at 263-266, contributors at 275-278) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/review/acceptance/text_checks.py:143` (`single_badge_row`, no order check) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/52b0f00ebf28a0b4173921725ff170685ec2c502/README.md:3`; `plans/idea.md:75-78` |

**Id** REV-V2-07 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 7 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README renderer badge slots; no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `_badges` derives a runtime badge per ecosystem from facts, emits a real build-status badge only from a verified workflow fact, emits the contributors badge only when supported, a blocking check asserts the stable order, and a test covers a .NET repository with and without a build workflow.

**Work item** G3-W06 · **Register status** FIXED(#246) · verified badge row. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.abbreviation_set_fixed_headings_unchecked_deep_headings_skip_title_case` (REV-V2-08)

All three sub-claims confirmed. (1) `composition/authoring.py::ABBREVIATIONS` is exactly 14 fixed entries (PDF, XLSX, HTML, EPS, XPS, API, JSON, XML, CSV, SVG, URL, HTTP, SDK, CLI); 'PS' is absent, and `canonical_abbreviations` extends the set from facts only for extensions of 3 or more characters (`len(extension) >= 3`), so a 2-character 'ps' can never qualify. Real exposure: the Aspose.Page-FOSS-for-Python README names 'PS' (for example `An existing EPS, PS, or XPS file`) with no casing enforcement, the exact product area `plans/idea.md:98` names. (2) `validation/registry.py::_prose` strips every line starting with `#` before the abbreviation-casing scan, so heading text is never checked. (3) Level-3 headings that are Additional-Examples task names or API-Reference topic names hit an explicit `continue` that skips the `_HEADING_OK` membership check, and `_HEADING_OK` itself tests fixed-set membership, not a title-case grammar rule, for level-3 and level-4 headings.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/composition/authoring.py:262` (`ABBREVIATIONS`); `:1326-1335` (`canonical_abbreviations`, `len(extension) >= 3`) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/validation/registry.py:312` (`_HEADING_OK`); `:508-514` (`_prose` drops headings); `:1194-1197` (the `continue` and membership test); `:1206` (`authored_prose`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `candidates/aspose-page-foss__Aspose.Page-FOSS-for-Python/` README (`PS` named); `plans/idea.md:98` |

**Id** REV-V2-08 · **Severity** High · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 8 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: README validation and authoring; no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: 'PS' is canonicalised (a test with a PostScript README asserts it), headings are included in the abbreviation scan, a title-case rule applies to all heading levels including task and topic names, and negative-control tests for each fail on a lowercase 'ps' or a non-title-case level-3 heading.

**Work item** G3-W06 · **Register status** PENDING · PR #249 open (heading case, abbreviations, BC-07 version 8). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `readme.advisory_only_clauses_and_keyword_lineage_absent` (REV-V2-09)

`review/acceptance/text_checks.py` says its phrase lists and thresholds are proposals awaiting owner ratification; its only importers are `profile.py` and `scorer.py`, so every predicate it defines (`fences_and_spacing`, `visible_core_sections`, `assurance_narration`, `single_badge_row`, `edition_name`) feeds only the advisory, unratified scorer (REV-V2-02), never `validation/registry.py`'s blocking BC-01..BC-11. At-a-Glance wrapping and width: `registry.py::_topology_failures` enforces only a flat 28-character token cap, not deterministic wrapping and a common rendered-width policy. Keyword lineage: `grep -rln 'keyword.lineage\|output.lineage\|output_lineage' src/` returns zero files; the mechanism does not exist. Verifier nuance: no literal '10 phrases' threshold exists in code; `_NARRATION` in `text_checks.py` is a flat any-match pattern list with no count threshold. The 'advisory, not blocking' claim holds, the specific number is unconfirmed as a coded constant. `plans/idea.md:99,107,109` require wrapping and width policy, output lineage, and no internal assurance narration.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/review/acceptance/text_checks.py:1-7,51` (`_NARRATION`),`:143,155,174,326` (the advisory predicates); importers `profile.py` and `scorer.py` only |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/validation/registry.py:1052,1112` (`_topology_failures`, the 28-character cap) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rn 'output_lineage' src/` returns nothing; `plans/idea.md:99,107,109` |

**Id** REV-V2-09 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 9 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: G3-W02 ratification (overlaps REV-V2-02) and README validation; keyword lineage has no work item yet; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: the owner-ratified narration, fence and badge predicates are called from a blocking check in `registry.py` (a test fails a README containing assurance narration), At-a-Glance wrapping and width are policy-checked, and an output-lineage record exists with a test; `grep -rn text_checks src/` shows `registry.py` as an importer.

**Work item** G3-W06 · **Register status** PENDING · PR #249 open; keyword lineage recorded there as a finding, not built (REG-06). The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `review.second_reviewer_unconditional_on_accept_hardcoded_three_names` (REV-V2-10)

`repair/rounds.py` runs `_second_opinion` when `review["verdict"] == ACCEPT or any(prose_judgment(finding) ...)`, so the second reviewer runs on every plain first-reviewer ACCEPT, not on a typed risk condition. `review/independent/review.py::MAJORITY_VOTE_REPOSITORIES` is a literal frozenset of three repositories (Words-FOSS-for-.NET, Slides-FOSS-for-Java, 3D-FOSS-for-TypeScript) escalated to a 2-of-3 vote; it is the only trigger-like mechanism and is a hard-coded identity list, not a typed risk classification. `plans/idea.md:311` says a second reviewer runs only for a typed risk trigger proven by the regression corpus.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/repair/rounds.py:529-532` (second opinion on ACCEPT) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/review/independent/review.py:317-322` (`MAJORITY_VOTE_REPOSITORIES`) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `plans/idea.md:311` |

**Id** REV-V2-10 · **Severity** Medium · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 10 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: independent review (typed risk trigger); no work item yet. Reducing the ACCEPT second read is an owner decision because it trades cost against assurance; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: `rounds.py` invokes the second reviewer only when a typed risk trigger fires (a test shows a clean first-reviewer ACCEPT makes no second call), and `MAJORITY_VOTE_REPOSITORIES` is replaced by a typed classification backed by a regression-corpus record.

**Work item** G3-W06 · **Register status** PENDING · OWNER-15 decided: a typed risk trigger replaces `MAJORITY_VOTE_REPOSITORIES` (`review/independent/review.py:325`, used at `repair/rounds.py:534`); the replacement is not built yet. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

### `seal.valid_update_available_routing_inverted_no_typed_invalidation_scopes` (REV-V2-11)

Both sub-claims confirmed. In `bundle/seal.py`, `FACTUAL_ARTIFACTS = frozenset({"facts.json", "dispositions.json"})` and `factual = bool(FACTUAL_ARTIFACTS & set(differing)) or inputs.earliest_affected_stage in EARLY_STATES or bool(model_changes)`, then `state = STATE_UPDATE_AVAILABLE if factual else STATE_READY`: a factual change moves the bundle to `VALID_UPDATE_AVAILABLE`, while a non-factual (presentation-only) change stays `READY_FOR_PROPOSAL`, unmarked. `docs/STATE_MACHINE.md:322-324` (the runtime authority) states the opposite: factual, safety, protected-content or severe acceptance defects invalidate an accepted candidate, and non-critical presentation improvements create `VALID_UPDATE_AVAILABLE` without mislabeling the README as factually invalid (see also `STATE_MACHINE.md:168-170`). The code gives the VALID_UPDATE_AVAILABLE label to the factual case and no label to the non-critical case. Typed scopes: `grep -rniw 'cosmetic\|prose-policy\|fact-slot\|major-document'` across `src/`, `docs/STATE_MACHINE.md` and `docs/README_CONTRACT.md` returns zero hits; the only classification is the binary factual test above, not the distinct typed scopes `plans/idea.md:208-212` requires.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `babar-raza/repository-presenter` | 2026-10-05 | `src/repository_presenter/components/readme/bundle/seal.py:603,626-638` (`FACTUAL_ARTIFACTS`; `state = STATE_UPDATE_AVAILABLE if factual else STATE_READY` at 638) |
| 2 | `babar-raza/repository-presenter` | 2026-10-05 | `docs/STATE_MACHINE.md:322-324,168-170` (the opposite mapping) |
| 3 | `babar-raza/repository-presenter` | 2026-10-05 | `grep -rniw 'cosmetic\|prose-policy\|fact-slot\|major-document' src docs/STATE_MACHINE.md docs/README_CONTRACT.md` returns nothing; `plans/idea.md:208-212` |

**Id** REV-V2-11 · **Severity** Critical · **Status** Open, awaiting independent reverification. Source: independent reviewer finding, verification report V2 item 11 (CONFIRMED), re-read directly against `origin/main` `cdaf793d` on 2026-10-05. Owning item: state machine and seal logic (G5 state routing); no work item yet. The seal comment cites TB-06 (2026-09-08) as a deliberate choice, so the owner must rule which mapping governs before code changes; the fix PR will be named in a follow-up `docs/DECISION_LOG.md` entry. Not fixed. Moves to Resolved only on a fix that an independent reviewer has re-verified by this predicate: the owner records which mapping governs (and `docs/STATE_MACHINE.md` or `seal.py` is changed to match), a test shows a non-critical presentation-only drift yields `VALID_UPDATE_AVAILABLE` and a factual or safety drift invalidates, and the typed invalidation scopes (cosmetic, structural, prose-policy, fact-slot, factuality/safety, major-document) exist with a test per scope.

**Work item** G5-W08 · **Register status** FIXED(#254) · typed invalidation scopes, `bundle/invalidation.py`. The entry stays Open in this index, awaiting independent reverification; a FIXED status here names the merged fix, not a reverified one.

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

## Register addendum (items without a REV id, 2026-10-05)

Every row names its work item (`project/state.yaml` `next_ready_items` or `owner_items`) and a status of OPEN, PENDING, OWNER, FIXED(PR) or WRONG. `tests/test_register_integrity.py` fails when a row loses either.

| Id | Item | Work item | Status |
|---|---|---|---|
| REG-01 | 17 READY/VALID_UPDATE_AVAILABLE sealed READMEs contain 'commercial edition'; 25 of 30 bundles (24 of 29 READY) carry readme-contract-v1-draft; none is independently accepted on current code | G3-W07 | PENDING |
| REG-02 | Pinned version literals are not computed from one source, so every bump makes all sealed bundles stale | G3-W07 | PENDING |
| REG-03 | READY_FOR_PROPOSAL is set before any acceptance score exists (label semantics; `bundle/seal.py:99-104`) | OWNER-13 | OWNER |
| REG-04 | Six registry entries have no current candidate: 3D-TypeScript (scope_limitations limitation:6), GIS-.NET (pinned upstream revision does not compile; BLOCKED_EXTERNAL), PDF-TypeScript (BC-07 visible-line overage), TeX-Python (upstream parse failures), PSD-.NET and PSD-Python (disabled). Font-Python is sealed (#259). The per-entry causes are as the sprint lanes reported them, not reproduced here | G5-W08 | PENDING |
| REG-05 | Drift is head-SHA only: no README-content or protected-content drift check | G7-W07 | PENDING |
| REG-06 | No search-intent keyword lineage per title (README_CONTRACT row 7; `plans/idea.md`) | G3-W06 | PENDING |
| REG-07 | No Releases audit, GitHub-generated statistics observation or product-agent ingest contract | OWNER-17 | OWNER |
| REG-08 | No concurrency groups on monitor.yml, present.yml, sealing-scheduled.yml | G7-W07 | PENDING |
| REG-09 | Only spend control is the three-repositories-per-run cap (`core/sealing_plan.py:46`); no cost budget | G7-W07 | PENDING |
| REG-10 | `renew_lease` (`core/state/cas.py:168`) has no production caller: no lease heartbeat in a long run | G7-W07 | PENDING |
| REG-11 | sealing-scheduled.yml has never run; no schedule-fired monitor run has confirmed the #228 notice-only behavior | G7-W07 | PENDING |
| REG-12 | Visual assets and social preview absent; `plans/idea.md` permits deferral | OWNER-17 | OWNER |
| REG-13 | Docs drift: the plan's 'no scorer' row (fixed by this PR); `project/state.yaml:111` same claim; `plans/idea.md` data/products.json | G7-W09 | PENDING |
| REG-14 | Code freeze after the open gap-closing PRs: #250, #248 and #249 remain open (#257, #258, #260, #261 and #262 are merged) | G3-W07 | PENDING |
| REG-15 | Gate C0 discovery is tools-only, public repositories only, no observation taxonomy, wired to no workflow | G4-W18 | PENDING |
| REG-16 | `project/state.yaml`'s `updated_at` had not advanced since 2026-10-05 despite dozens of merges since (#249, #250, #257-#273, #277, #279-#281); no check fails on cursor staleness, so the gap recurred silently (2026-10-07 four-reviewer finding, confirmed live before this row was added) | G7-W10 | PENDING |
| REG-17 | The sealing loop retries a repeatedly-failing candidate identically every cycle with no recorded failure history (2026-10-07 four-reviewer finding). A fix was reported in progress on branch `feat/sealing-failure-memory-1009`; re-checked directly this session (`git branch -a`, `git worktree list`, `gh pr list --state all`) and no such branch, worktree or PR exists | G7-W11 | PENDING |
| REG-18 | `aspose-cells-foss`'s Go candidate hits `validation/deferrals.py`'s `UNCLASSIFIED` fallback (no registered class matches its real cause); a root-cause investigation was reported in flight elsewhere, re-checked this session with no matching branch, worktree or PR found | G7-W12 | PENDING |
| REG-19 | Most registry entries lack write (`full`) mode; production publication beyond the N entries already `full` is not yet possible. Verified live, 2026-10-07: 36 active entries, 2 `full` (`aspose-3d-foss/Aspose.3D-FOSS-for-Java`, `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`), 34 `dry_run`, 0 `disabled`; `ops/proposal-authorizations/` does not exist as a directory, so no repository has a committed authorization record of any kind | OWNER-20 | OWNER |
