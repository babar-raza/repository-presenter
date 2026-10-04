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
