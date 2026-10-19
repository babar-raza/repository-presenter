# 16 - Recovery M1: source freeze, reuse decisions, first Lane R input (2026-10-19)

One named question: what is true of the repository, its PRs, its evidence and its code today, and
which of it does the first independently accepted Lane R README (and its upstream PR) build on?
History and analysis, never a cursor or a task list. The cursor is `project/state.yaml`; the work is
G3-W12 (C1) then G3-W13 to G3-W19 (`docs/investigations/14-lane-r-dependability.md`). The recovery
mission text asked for a supervisor port and a new vertical slice; both resolve through the existing
authority hierarchy (section 5), not beside it. File-level inventory:
`evidence/recovery-m1/inventory.csv` (272 rows, sha256 `9ccc3136...3c9cbdd`).

## 1. Source freeze (verified 2026-10-19, not taken from the mission text)

| Source | Mission pin | Verified | Note |
|---|---|---|---|
| repository-presenter `main` | `802efa2f` | `bf2a71ee` (origin/main, merge of #346) | #345 merged first; the pin was one merge old |
| PR #346 | open, `2e99f0c7` | MERGED 2026-10-19T09:35Z, head `2e99f0c7` | pinned head is right, state is not |
| foss-mcp | main | origin `0e6eadf4`; local checkout `9e67c6ab` is 45 commits ahead of origin | unpushed supervisor commits; ops files read from the local copy are not published |
| CI | - | `main` push run in progress at freeze; Liveness and scheduled Sealing green | read `gh run list`, not memory |
| Control cursor | - | G3_PYTHON_COHORT READY, G3-W11 IN_PROGRESS, G3-W12 STARTED (C1), OWNER-27 satisfied 2026-10-17 | OWNER-23/24/25/26 still open |
| Registry | 44 | 36 (8 JMAP entries removed 2026-10-17, owner ruling) | denominator is N/36 |

`repository-presenter status` at `bf2a71ee`: `authorizable 0/36`; 28 READY_FOR_PROPOSAL (sealed, never
counted), 1 VALID_UPDATE_AVAILABLE, 1 INVALIDATED, 6 no bundle; recheck: 30 UNVERIFIED. A sealed count
is not progress; the judge's count is, and it is zero.

## 2. Outcomes that exist upstream (verified with `gh`)

- Lane L: two open pull requests by the App, `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp#7`
  (+31/-16, one file, opened 2026-10-19T10:44Z) and `...-for-Java#7` (+25/-20, opened 2026-10-17); both
  MERGEABLE, no review. Eleven earlier Cells README-refresh PRs are merged (Go, Rust, TypeScript, .NET, Python,
  Java, Cpp; some opened by `/readme-refresh`, not the App). One issue filed (Cells-Cpp). Lane L's pathway is therefore proven on the seven Cells
  repositories; it is the only lane that has delivered.
- Lane R: **no upstream PR, no authorizable candidate.** The judge fails 29 of 30 sealed bundles on J4
  (dispositions) and 26 on J6 (not worse than live); C1's harness reproduces this
  (`python -m tools.lane_r_audit measure`: M1 0.470, M2 318, M3 680, M4 881, M5 44, M9 0 of 30).

## 3. Salvage: what the code is (file level in the CSV)

Static import closure from `repository_presenter.cli` plus the registry-loaded plugins (platform
extractors, correction detectors) reaches all 272 source files; none is an orphan. Of 88,691 source
lines: **REUSE 61,913, ADAPT 16,133, REPLACE 10,645** (`readme/composition`, the legacy Lane R
renderer). Nothing is RETIRE in `src/`; the legacy manifest's 162 records map as PORT_NEARLY_INTACT 40
to REUSE, EXTRACT_AND_REFACTOR 64 and ADAPT_AS_PLUGIN 5 to ADAPT, FIXTURE_OR_ORACLE_ONLY 5 to
FIXTURE_ONLY, RETIRE 11, EXCLUDED 33 (dirty-tree exclusions), MIGRATION_READER_ONLY 2.

| Area | Disposition | Reason (evidence) |
|---|---|---|
| Lane L correction engine, gate, PR text (`readme_correction/`) | REUSE | 2 open App PRs and merged Cells refreshes; confinement proven |
| GitHub effects, authorization, push-disabled clones, `propose`, issues | REUSE | first real PRs and one issue went through them |
| Registry admission, hard allow-list | REUSE | registry safety; 36 entries |
| Extractors (ecosystems, `_vendor/aspose_extraction`), facts, snapshot | REUSE | the facts are what the judge trusts; GIS-.NET produced 1,448 in 16 s with no provider call |
| Bundle, recheck, judge | REUSE | bump-proof 2026-10-15; the judge is frozen for the pilot |
| `validation/` BC-04, BC-14 | ADAPT (C2) | F2: citation check, not entailment |
| `reconciliation/` ledger | ADAPT (C3) | F1/F4/F5: 52% of keep decisions unprinted |
| `review/` independent | ADAPT (C6) | F3: REJECT on 26 of 30, folded to ACCEPT on all |
| `repair/`, `investigation/` | ADAPT (C4) | rewriting repair becomes targeted operation repair |
| `composition/` (legacy Lane R renderer) | REPLACE (C4, C5) | not imported as production-ready; stays the default only until C8 |

Rejected as reuse: the legacy renderer's acceptance semantics (a citation existing is not a claim
being true); any model verdict as a gate; a second state cursor or mission graph.

## 4. First Lane R input: the evidence changes the choice

- **Aspose.GIS-FOSS for .NET (the only repository without a live README) is not a publishable pilot.**
  `present --facts-only` at `b9b8c9c7` (0 provider calls, 16 s): README absent, no LICENSE (preflight:
  "required rows without evidence: license"), NuGet `Aspose.GIS.FOSS` CONTRADICTED (unpublished), no
  runnable example, and `dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj` fails with 369 errors
  (missing types such as `BoundingBox`, `PointsSequence`): an upstream defect, already an issue
  handoff class. Any README from this input would assert a library that does not compile. Decision:
  not the pilot; the defect stays an issue, not a README.
- **Candidate pilot: Aspose.Cells-FOSS for Python.** Cells is the only family in the write scope; its
  sealed candidate fails only J4 (M1 0.725, 37 of 51 units accounted, 1 OMIT_UNSUPPORTED without a
  fact, 7 supersessions unproved, 5 moves and 1 preserve not printed) and passes J6. Upstream has moved
  since the seal (`4f6768a7` to `952317ca`, "Update Readme"), so the candidate is stale and must be
  re-derived at the current head, by the live-anchored route (C4) rather than the legacy rewrite.

## 5. Supervision: reuse, do not re-import

foss-mcp's gate mechanism (card, holdout, cardlint, `gateverify` clean-worktree check, derived state)
is already represented here by `docs/SUPERVISION.md`, `tools/reviewer/procedure.md`, `tools/plan_lint/`
and the ESM gates with `evidence/build/<gate>/manifest.json` acceptance records ("COMPLETE only when the
record exists" is tested by `tests/test_queue_agreement.py`). The recovery rules map onto these as
follows: the supervisor authors cards (G3-W12 to G3-W19 are the cards); workers own named paths
(`owned_paths`); a worker cannot accept its own work (the judge and C1's harness import nothing from
the gates they grade); one cursor (`project/state.yaml`). A port of `gatectl.py` would add a second
cursor, which `AGENTS.md` forbids, and any `tools/` change needs a work item that owns it. Not ported.

## 6. Cost and blocker

Provider usage this session: one `preflight` (gateway catalog and two schema-valid chat probes), zero
`present` calls. Repeat work avoided: the facts-only run is call-free and the C1 harness replays pinned
bundles offline. Actual blocker for M3: C1 is unfinished (the labeled corpus, split and ratchet are
missing), so C2, the claim gate that must precede any proposed Lane R candidate, may not start
(G3-W13 prerequisite "C1 ACCEPTED"). That is internal and owned, not external.
