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
- **Title-restatement sub-shape (repair path)**: `unit_checks`'s item-106 carve-out lets a repaired
  unit through (real detail follows the title), but independent review's own separate semantic
  judgment still flags the literal title-verbatim opening clause regardless of what follows it.
- **Title-restatement sub-shape (initial-draft path)**: within `section_authoring`'s own first
  `run_job` call (never reaching review), `unit_checks`' identifier-acceptance check and its own
  item-106 title-restatement carve-out can pull one combined re-ask in opposite directions —
  removing an unaccepted identifier to satisfy one check strips the exact member-level detail the
  other check needs — and this call site's only `recover=` (`recover_forbidden_command_units`)
  does not cover either check.

| # | Repository | Sub-shape | Date | Evidence |
|---|---|---|---|---|
| 1 | `aspose-page-foss/Aspose.Page-FOSS-for-Python` | forbidden-literal | 2026-09-24 14:25 UTC | `docs/DECISION_LOG.md`, never sealed until fixed |
| 2 | `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` | title-restatement (repair path) | 2026-09-25 08:04 UTC | `docs/DECISION_LOG.md`, reseal regression |
| 3 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | title-restatement (repair path) | 2026-09-25 07:13 UTC (and `docs/RESEARCH_LANE_C.md` G4-W12-RERUN7 through RERUN13, earlier) | 7+ reruns, recurring |
| 4 | `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` | title-restatement (initial-draft path, new) | 2026-09-26 03:06-08:35 UTC | `docs/DECISION_LOG.md`, this timestamp — `section_authoring` itself exhausted its 2-attempt budget, never reached review |

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
(`F08`, `development_testing`). **Slides-Java**: never reached independent review at all — a new,
distinct sighting of this same mechanism family (sighting #4 above, the initial-draft path), which
`fadb001` does not cover by design (it is scoped to the separate repair-path call site only). The
repair-path fix (sightings 2-3) therefore remains landed but still not live-verified as a success
against either of its own originating repositories; the initial-draft path (sighting 4) has no fix
yet. Not moved to Resolved. Resume: re-draw either repository on a future independent sample for
the repair-path fix; diagnose and land a fix for the initial-draft path (proposal in
`docs/DECISION_LOG.md`) before its own verification is possible.

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
