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
| 4 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | title-restatement (initial-draft path) | 2026-09-27 | `docs/DECISION_LOG.md`, reseal blocked - all 6 `key_capabilities` units regressed on the attempt meant to fix an unrelated rejection |

**Status 2026-09-27**: all three sub-shapes now have a landed fix. Forbidden-literal via
`composition/authoring.py::recover_forbidden_command_units` (commit `1fff7d7`); title-restatement
(repair path) via a deterministic backstop for review's stricter standard (commit
`fadb001`/`a313864`); title-restatement (initial-draft path, this 4th sighting) via
`composition/authoring.py::recover_section_authoring_output`, which composes
`recover_forbidden_command_units` with the same opening-clause strip
`recover_title_verbatim_opening` already uses for the repair path, wired as
`section_authoring`'s own initial-draft `recover=` in `repair/rounds.py`
(`NORMALISATION_VERSION` 15 -> 16). Verified by mutation test against this exact reported shape
(`tests/components/readme/composition/test_authoring.py`); a fresh live redraw of Slides-Java at
the same revision (`docs/DECISION_LOG.md`, 2026-09-27) did not sample the attempt-1-detail/
attempt-2-deletion sequence this fix corrects, so it is not yet moved to Resolved - the mechanism
is fixed and mutation-tested, but not yet measured firing live on this or any other repository.

### `composition.planning.rc01_backstop_vs_link_ceiling_trim_ordering`

`planning.py`'s `plan_checks` runs the RC-01 links backstop (which appends every disposition-
required `link_target` fact a unit names, per `_missing_links`) *before* the Aspose-link-ceiling
trim (`DEFAULT_POLICY.aspose_links_max`). The trim then keeps only the first N Aspose-domain links
it encounters in the disposition's own `fact_ids` insertion order — which carries no priority
signal at all — silently dropping whichever backstop-appended, deterministically-required link
lands last. The trim's own reasoning (favor whichever links the model named first) is sound for the
model's own free-choice links; it does not hold for backstop-injected ones, which the model never
chose to prioritize in the first place.

| # | Repository | Date | Evidence |
|---|---|---|---|
| 1 | `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET` | 2026-09-17 10:53 UTC | `docs/DECISION_LOG.md` on branch `item92-slides-net-redraw` (commit `654d115`, never merged to `main` — stranded 9 days, found via a `liveness.yml` failure on 2026-09-25 and backfilled into this index only now) |

**Status 2026-09-26**: one sighting, not yet escalated (below the 3-sighting threshold). Recorded
here specifically so it is never lost again the way it was for 9 days on an unmerged branch —
`docs/DEFECT_INDEX.md`'s whole purpose is to survive a branch going stranded. Repository not sealed;
its `READY_FOR_PROPOSAL` bundle was deliberately never committed (would have turned
`test_no_link_completeness_gap` red for everyone). Proposed fix, not implemented: reserve ceiling
headroom for RC-01 backstop links before trimming the model's own free-choice links, or trim from
the model's own links first and never touch backstop-injected ones — owner's choice, not
prescribed.

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
