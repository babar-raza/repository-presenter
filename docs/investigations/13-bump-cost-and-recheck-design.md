# 13 - What a version bump costs, measured, and a re-check design

Written 2026-10-10 at the owner's request. Measurement and proposal only: no `src/` code and no
behavior changed, no provider call made, nothing written outside this branch. The owner's
complaint: every enhancement stales the sealed candidates, so re-sealing never ends, and
`repository-presenter status` fell "from 29 to 2" although 29 bundles are `READY_FOR_PROPOSAL` and
intact. Raw tables: `evidence/bump-cost/*.csv` (manifest with SHA-256 beside them). Scripts that
produced them: `tools/reviewer/bump_cost/` (read-only, no network, no provider call). Rules this
document is held to: `AGENTS.md` ("Invalidate a candidate only through an input it consumed. Never
add a global control-plane hash; validator and reviewer changes re-check and may yield
`VALID_UPDATE_AVAILABLE`, never blanket invalidation") and `docs/STATE_MACHINE.md` section 9.

## 1. Answer in brief

1. **The "29 to 2" is mostly a metric correction, not a regression.** Before #276 (2026-10-07) the
   headline counted every `READY_FOR_PROPOSAL` bundle (29); the funnel under it already showed 0
   independently accepted. Counting by the project's own stale rule, the number of bundles that
   were current at any moment since 2026-09-23 peaked at **10 of 23** (2026-09-25, mid re-seal
   sweep), fell to 1 the same day (one normalisation bump staled 10), and has been 0 to 2 since.
   Today it is 2 (BarCode-Python, Cells-Python, both re-sealed 2026-10-09).
2. **Of 39 bump commits since 2026-09-24, 7 changed what at least one sealed candidate would
   say; 25 changed nothing a candidate consumed; 7 cannot be replayed offline for the whole
   population.** Measured by re-running the deterministic stage (re-render, blocking checks,
   authoring gate) with the code from the commit's parent and from the commit, over the sealed
   inputs of the 22 to 30 bundles current at that moment (section 3). All 7 are stricter
   contract rules the owner asked for (edition naming, badges and Enterprise anchor, heading
   case, deferral classes, must-carry units). They explain every blocking failure the 28 stale
   bundles carry today.
3. **The treadmill is real but it is two different things.** (a) Record staleness: all 25
   zero-effect bumps still moved a version constant, and `stale_candidates` reports a bundle
   stale as soon as any component version, any check version or `VALIDATOR_VERSION` differs from
   its sealed record, so a bundle sealed on Monday is stale after the next merge that bumps
   anything. (b) Content staleness: 7 bumps genuinely made the sealed READMEs non-conforming. A
   consumed-input re-check removes (a) and leaves (b).
4. **A re-check does not raise today's count.** Of the 28 stale bundles, 26 fail a current
   blocking check even after a free re-render (they need re-composition, i.e. LLM calls), 2 need
   only a re-render plus a fresh review read, 0 are "still valid". Day-one effect of the proposal:
   2 stays 2. Its value is in what happens next: a bundle sealed on the frozen code stays counted
   across the 25 bumps that change nothing, instead of going stale on the first of them.
5. **One routing defect is worth fixing regardless:** the dry-run routes 24 of 30 bundles to
   `INVALIDATED` on `environment.inherited_units_version 1 -> 2` (scope `facts`), yet regenerating
   the inherited units offline changes only 2 of those 24 (and 2 more that record no version at
   all, which the rule silently skips). That is the blanket invalidation `AGENTS.md` forbids.

## 2. Method, and what it can and cannot see

Everything is a pure read of committed state. Population at each bump = the `CURRENT` bundles in
`git ls-tree <parent> candidates/`; the stale rule is `core/candidates.py::stale_candidates`
applied to those bundles' `dependencies.json` with the constants in force at that commit
(`bump_history.py`; it reproduces `status` at HEAD: 29 ready, 27 stale plus 1 held update).

- **Integrity** (`verify_bundle`) checks manifest digests and ledger totals only, never a version
  constant: no bump can fail it, and all 30 verify today (`status`: 30 integrity-valid).
- **Renderer / shell** effect: `render_readme` from sealed `facts/plan/content_units/dispositions`,
  compared byte for byte (the `tests/test_sealed_bytes.py` method), before and after each bump.
- **Validator / authoring-gate** effect: `validate_candidate` run on the sealed README with the
  parent's code and the commit's code (checks BC-01..03, 05..09, 12; BC-04 for normalisation
  bumps - BC-04 *is* `authoring.unit_checks`). BC-10 and BC-11 are judged at S10 and by the no-op
  rerun, not here. The tree for BC-06's relative links is approximated by the README's own
  relative targets plus evidence paths (the sealed README resolved them at seal time), and
  BC-01's original-bytes comparison and BC-09's secret scan are not re-run.
- **Extraction environment** (`INHERITED_UNITS_VERSION`): the original README is rebuilt by
  reverse-applying `README.patch` to `README.md`, the inherited units regenerated under the running
  code and compared with `facts.json` (26 of 30 identical, 4 differ).
- **Reviewer logic**: `review_document` replayed from the raw reads in `raw_calls.json`; only 6 of
  30 bundles retain them.
- **Fidelity checks that passed**: the offline BC-04 run finds 17 bundles with a forbidden edition
  substitute (the register's REG-01 says 17); #265's message says 19 of 29 bundles would carry an
  uncarried must-carry unit, the measured effect of that commit is 19 of 30; and a mutation
  (`scope_defect` returning `None`) flips 5 of the 6 reviewer replays, so the replay is sensitive.
- **Not measured**: any provider cost (see section 7), a real `present` run, hosted CI. Reseal cost
  is quoted from `docs/DECISION_LOG.md` (10 to 33 provider calls per clean draw).

## 3. Timeline and cost per bump

61 constant changes in 40 commits (`bump_timeline.csv`): `NORMALISATION_VERSION` 11 to 30 (19
bumps), `VALIDATOR_VERSION` 3 to 15 (12), per-check versions (BC-06 x4, BC-07 x3, BC-02, BC-05,
BC-10, BC-11, BC-12 added), `REVIEWER_LOGIC_VERSION` 11 to 18 (7), `RENDERER_VERSION` 24 to 30 (6),
`CONTRACT_VERSION` draft to v1 and `ACCEPTANCE_PROFILE_VERSION` none to 1 (one commit), and
`INHERITED_UNITS_VERSION` 1 to 2. `SHELL_VERSION`, `POLICY_VERSION` and `EXTRACTOR_VERSION` did not
move; #218 moved `ACCEPTANCE_PROFILE_VERSION` to an alias of `PROFILE_VERSION` with the value still
1 (not a bump). Columns below: *new* = bundles newly stale by record (the stale rule) because of
this commit; *changed* = then-current bundles whose re-render bytes or check verdict or failure
set differ pre versus post; *n* = bundles measured. Full table: `bump_cost.csv`; per-cell diffs:
`bump_cost_per_bundle.csv`.

Bumps that changed at least one candidate (all stricter):

| Date | Commit (PR) | Bump | new | changed / n | What changed |
|---|---|---|---|---|---|
| 09-24 | ef2ee5e1 | Norm 11-12 | 2 | 5 / 22 | BC-04 pass to fail: dev-testing unit restating a placed command |
| 10-04 | ce355281 (#211) | Norm 19-20 | 1 | 14 / 29 | BC-04: superseded units must be carried in development_testing |
| 10-04 | 48201b67 (#251) | Norm 21-22, BC-06 6-7, BC-12 new | 0 | 17 / 29 | edition-substitute rejected (BC-04, BC-06); BC-12 fails 3 |
| 10-04 | 761f3b30 (#246) | Render 26-27, BC-06 5-6, BC-07 7-8 | 0 | 26 / 29 | README bytes differ for 26; BC-06 pass to fail 23, BC-07 12 |
| 10-05 | 38defe4f (#265) | Norm 23-24 | 0 | 19 / 30 | BC-04: superseded units must be carried in scope_limitations |
| 10-05 | 75b5cf73 (#249) | Render 28-29, Norm 24-25, BC-07 8-9 | 0 | 23 / 30 | README bytes differ for 23; BC-07 16 pass to fail, 7 more failures |
| 10-05 | 65b96971 (#272) | BC-05 1-2, Val 10-11 | 0 | 7 / 30 | BC-05: deferred units judged by cause |

Bumps measured to change nothing any candidate consumed (24), with the record cost they carried:

| Group | Commits (PR) | new by record |
|---|---|---|
| Renderer (4 of 6) | 03110a4b #153 (24-25), 7e56716e #209 (25-26), 268faac3 #230 (27-28), 5e5cb3c7 #291 (29-30) | 1 (7e56716e) |
| Normalisation (13 of 19; recover=, re-ask text, packet content, loosened identifier checks) | 84546aa0, fadb0017, d8b3a9de #125, ffb1476f #143, a14a22fe #146, 599659d2 #195, 2dba63e8 #221, 1c188006 #258, a47336f6 #255, 9cc25fc0 #268, cc5a4e9e #287, ae8620a4 #289, 5cffa343 #298 | 12 (84546aa0 alone: 10) |
| Validator only (7 commits, listed with the above where a renderer or reviewer bump shares the commit) | d842b7b0 #169, 8f30d5d5 #201, cdaf793d #202, 89c9f2af #250, a1e6f797 #290, 99320d8a #275, feab4437 #278 | 0 |

One more (2d380177 #281) rewrote the failure text of 23 bundles that already fail BC-04, no verdict
or count changed. Not replayable for the historical population: five reviewer-logic-only bumps
(9596a923, 0f523a34 #124, ae6c4373 #164, 7e567085 #253, 14cdd181 #302), the contract/profile label
bump (af08a2ea #182) and `INHERITED_UNITS_VERSION` (8faea803 #297). Evidence for them: reviewer
logic v14 or v15 to v18 replays to the identical verdict and finding set on the 4 older bundles
that keep raw reads (and on the 2 sealed under v18); regeneration under the new splitter changes
4 of 30 bundles' inherited units. The label bump changes no file a check reads.

**The key finding.** Of 39 bump commits, 7 (18%) are content changes, 25 (64%) changed nothing a
bundle consumed, 7 (18%) are unmeasurable offline for all bundles but have no counter-evidence.
By the record rule every one of the 39 stales every bundle sealed before it. In practice only 7
commits newly staled anyone (23 bundle-events), because the portfolio was already almost entirely
stale; 6 of those 7 are measurable: 2 changed content (ef2ee5e1, ce355281) and 4 did not (84546aa0
staled 10 bundles, fadb0017, 7e56716e and 5cffa343 1 each: 13 bundle-events of pure staling). The
seventh, 9596a923, is a reviewer-logic bump (7 bundle-events), not replayable for the old bundles.
Bump messages are uneven: 5 of the 7 content changes say what they do to sealed bundles (#265
"19 of them carry an uncarried unit", #249 "22 of 29 would newly fail BC-07", #251 "19 sealed
READMEs carry the lowercase phrase"), two (ef2ee5e1, ce355281) are silent, and most of the 25
zero-effect bumps say nothing about sealed bundles; three that did measure it (#169 "zero false
positives", #221 "none changes verdict", #230) match this measurement. The owner cannot tell the two
kinds apart from the commit list, which is what the bump-impact preview in 6.4 is for.

A bundle sealed on the code of the evening of 2026-09-25 (after 84546aa0) would have stayed
counted under a consumed-input rule until 2026-10-04 (the next content change, ce355281), nine
days and 13 intervening bumps, none of which changed an outcome (10 measured, 3 reviewer or
label bumps with no counter-evidence); under the record rule it was stale at the next bump.

## 4. Current state, grouped by constant

`current_state_per_bundle.csv`. 30 sealed, 30 integrity-valid, 2 current. 28 bundles differ by the
stale rule (292 differing records, mean 10.4; 116 of those bundle-dimensions have a measured content
effect). The dry-run adds records the stale rule ignores (prompts, contract, profile, extraction
environment).

| Record that differs | Behind | Offline re-check says |
|---|---|---|
| `components.renderer` 17..25 to 30 | 28 | re-render differs for **28 of 28** (by design: badges, anchor, heading case) |
| `components.shell` 5 to 6 | 4 | part of the render; same 4 |
| `components.normalisation` 1..18 to 30 | 28 | BC-04 fails on sealed units for **26**, passes for 2 |
| `validators.BC-06` | 28 | fails on sealed bytes for 24 (18 still fail after a re-render: edition text) |
| `validators.BC-07` | 28 | fails on sealed bytes for 26; none fail after a re-render |
| `validators.BC-05` | 28 | fails for 9 (deferred-unit causes) |
| `validators.BC-02` | 26, `BC-03` 1, `BC-08` 4 | all pass everywhere: pure record staling |
| `validators.BC-04` | 6 | its own version is behind for 6 only, yet its gate fails for 26: BC-04 *is* the normalisation gate and moves with `NORMALISATION_VERSION`, not with its own version |
| `validators.BC-10`, `BC-11` | 28 each | judged at S10 / by the no-op rerun; not re-runnable here |
| `validator_version` 3..14 to 15 | 28 | a scalar derived from the check versions; no check of its own |
| `components.reviewer_logic` | 27 | replay identical for 4 of 4 older bundles that keep raw reads; 23 not replayable |
| `contract_version` draft to v1 | 24 | label; no check reads it |
| `acceptance_profile_version` none to 1 | 24 | label; no blocking check reads it (profile unratified) |
| `environment.inherited_units_version` 1 to 2 | 24 | regenerated units differ for 2 (PDF-Go, PDF-Python) |
| `prompts.section_authoring` etc. | 28 | provenance of an LLM output; validity is judged on the output |
| BC-12 (added after sealing) | 0 flagged | **fails on 3 bundles but is never reported**: a check the sealed record lacks is skipped |

Re-check classes (columns `recheck_class`): 2 `CURRENT`; **2 `UPDATE_RERENDER_ONLY`** (Cells-Go,
Slides-Python: re-render passes every deterministic check, but the bytes change so a fresh review
read is needed); **26 `UPDATE_RECOMPOSE`** (still fail BC-04, plus BC-05/06/12 on some, after a
re-render). The dry-run routing (`status --stale`) says 24 `INVALIDATED` (all through
`environment.inherited_units_version`) and 4 `VALID_UPDATE_AVAILABLE` (3D-Python,
Cells-.NET, Cells-Rust, Slides-Python: they predate the `inherited_units_version` record, so that
row never fires for them).

## 5. Which constants must restale content, and which should not

| Constant | Must restale a bundle when | Should not restale it when | Measured |
|---|---|---|---|
| `RENDERER_VERSION`, `SHELL_VERSION` | re-render bytes differ (a different README is a different candidate; its review and validation judged the old bytes) | bytes are identical | 2 of 6 renderer bumps changed bytes (26 of 29 and 23 of 30 bundles); 4 changed none |
| `NORMALISATION_VERSION` | the sealed units fail the tightened authoring gate (BC-04) | the bump changes re-ask text, recovery paths, packet content or loosens a check; none of those can change an accepted output | 5 of 19 changed outcomes; 14 did not (13 zero, 1 text-only) |
| Per-check `Check.version` | the check's verdict or failure set on the sealed bytes differs | it does not | 4 of 13 validator-bearing commits |
| `VALIDATOR_VERSION` | never by itself: it is derived from the check versions | always | 3 commits bumped it with no check version (7e56716e, 5e5cb3c7, 99320d8a) and changed nothing |
| `REVIEWER_LOGIC_VERSION` | a replay of the retained raw reads yields a different verdict or finding set | replay identical, or the bundle keeps no raw read (then the verdict is unverified, not changed) | replay identical on 6 of 6 |
| `CONTRACT_VERSION`, `ACCEPTANCE_PROFILE_VERSION` | never: labels; the checks are versioned on their own | always | one label bump, no effect |
| `INHERITED_UNITS_VERSION`, `EXTRACTOR_VERSION` | regenerating that fact kind from the bundle's own material yields different facts (the fact records are the consumed input; the version is a proxy) | regeneration identical | 2 of 24 |
| Prompt text/hash | never invalidates: a prompt shapes how a unit was made, not whether it is valid; at most "optional update" | always | not an input of any check |

Changes the owner still wants (new contract rules) will always restale the bundles that break them.
That is not a defect of the mechanism; section 6 only stops the other 25 of 39 from doing it too.

## 6. Proposal: consumed-scope re-check

### 6.1 Principle

Version constants stop being the arbiter of validity and become change signals and cache keys.
The arbiter is a deterministic re-run of exactly the scopes whose recorded inputs differ, over the
bundle's own sealed artifacts. A re-check can only produce "still current" when every scope it was
triggered by re-ran and gave the same outcome; anything it cannot run is `UNVERIFIED`, never
"current". It never invalidates (`INVALIDATED` stays reserved for the `facts` scope with different
fact records, or a failing factual/safety/protected-content check, as today).

### 6.2 What is compared per bundle

The existing table in `bundle/invalidation.py` (`SCOPES`, `DEPENDENCY_SCOPES`) already maps each
`dependencies.json` input class to a scope. Add a second table of the same shape, `RECHECKS`, one
row per scope, in a new `bundle/recheck.py` (a lookup miss raises, as `scope_of` does):

| Scope | Triggered by a difference in | Re-check (offline, zero calls) | Passes when |
|---|---|---|---|
| presentation | `components.renderer`, `components.shell` | `render_readme` from sealed facts/plan/units/dispositions | bytes equal `README.md` |
| authoring | `components.normalisation` | BC-04 judge over sealed units, tasks rebuilt from sealed investigation/dispositions/plan | verdict and failure set equal sealed |
| validator | any `validators.BC-*` that differs, **and any check the record lacks** | the deterministic judges (BC-01..03, 05..09, 12) on the sealed bytes | same verdict as sealed; a check with no sealed baseline must pass |
| reviewer | `components.reviewer_logic`, `acceptance_profile_version`, review/repair prompts | `review_document` replay from the raw reads in `raw_calls.json` | same verdict, blocking and advisory ids; no raw reads: `UNVERIFIED` |
| facts (extraction) | `environment.*_version` | regenerate that producer's fact kinds from material in the bundle (inherited units from the original README, rebuilt from `README.patch`); other kinds need a clone: left to the monitor | identical fact ids and values |
| planning, reconciliation, evidence, authoring prompts; `contract_version` | prompt hash, label | none | never stale: reported as `provenance` only |

Run *all* deterministic judges, not only those whose version moved, whenever any validator-scope
record differs: the discipline test (`tests/test_version_bump_discipline.py`) only demands that
*some* constant in `validation/registry.py` moves, and 7e56716e changed BC-07's meaning moving only
`VALIDATOR_VERSION`. Selecting judges by version would call that bundle current. Versions then
only decide whether a cached receipt is reusable.

### 6.3 States and counts

Per bundle a **currency**, computed from the receipt, with the manifest state untouched (sealed
bundles stay immutable):

- `CURRENT`: no difference. `RECHECKED_CURRENT`: differences exist and every triggered re-check
  passed. Both count as today's "not stale".
- `UPDATE_OPTIONAL`: only provenance differences (prompts, labels). Counted, flagged.
- `UPDATE_REQUIRED`: a re-check failed. Split by cost for planning: `rerender_only` (re-render passes
  all deterministic judges; needs one review read) versus `recompose` (a content gate fails;
  needs authoring).
- `UNVERIFIED`: a triggered re-check could not run (reviewer scope without raw reads; extraction
  kinds that need a clone). Not counted at "independently accepted" (conservative; owner may relax).

The seven counts (`bundle/portfolio.py`) keep their definitions. Only predicate 3's "not behind the
running code" changes to "currency in {CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL}", and
`assess_portfolio(stale_directories=...)` takes a currency map instead of a set. The partition
splits `update_available` into `update_required` and `update_unverified` (every entry still lands
in exactly one bucket). The headline keeps the byte-reproducibility term, which `RECHECKED_CURRENT`
implies. `fact_valid` and `presentation_valid` are unchanged: they already ignore staleness (30 and
30 today).

### 6.4 Storage, migration, and the dry-run fix

- Receipts, not edits: `candidates/<owner>__<name>/rechecks/<revision>.json`, keyed by the bundle
  manifest digest and the running values of the constants its scopes consumed; a receipt for any
  other key is ignored. They are a cache. The existing hosted job that keeps `candidates/` current
  (G7-W14) refreshes them after each merge to `main`; `status` computes on the fly when absent
  (measured 3 to 6 minutes for 30 bundles, mostly BC-04), so correctness never depends on a cache.
- Migration: no bundle changes. Run once, review the 30 receipts against section 4 (expect 2
  `CURRENT`, 2 `rerender_only`, 26 `recompose`, 0 `RECHECKED_CURRENT`), commit.
- Dry-run and `evaluate()`: an `environment.*_version` difference must reopen EXTRACTING as "would
  re-extract", not route to `INVALIDATED` by scope alone; only a difference in the `facts` hash map
  invalidates. This is one row in `DEPENDENCY_SCOPES` plus an `evaluate` comparison, and removes the
  24 false `INVALIDATED` routes. The absent-record skip needs a counterpart: a check or key the
  sealed record lacks must be run, not skipped (BC-12 fails on 3 bundles that never report it).
- Bump-impact preview: a CI step runs the re-check over `candidates/` when a PR touches a governed
  source and prints the table of section 3 for it ("this PR changes the outcome of N of 30
  bundles"). It makes a zero-effect bump visible before merge and a content-changing one an
  explicit, reviewed decision; with G3-W07's freeze it is what makes "no further version-bumping
  change" checkable. Warn-only, like `check_staleness.sh`.

### 6.5 Risk of a false "still valid"

| Risk | Mitigation |
|---|---|
| A re-check reads less than the real run (no clone: original bytes, tree, secret scan, live link probes) | Source-derived halves are not re-observed; they stay with the drift monitor and `source_fresh`. Re-check records which judges ran partially (`tree_approximated`, `original_unavailable`); a validator bump that adds a tree-based rule makes the receipt `UNVERIFIED` until `tree.json` is sealed (schema change, named work item) |
| A check or version missed by the bump discipline | Judges are selected by running all, not by version; a check the record lacks must run |
| Reviewer replay depends on retained raw reads | `UNVERIFIED` otherwise; only 6 of 30 keep them today, every new seal does |
| A prompt change hides a real quality regression | It is reported as `UPDATE_OPTIONAL`, visible in `status`, and the owner can promote it; no input to a check is ignored |
| A stale or forged receipt | Keyed by manifest digest and constants; `verify_bundle` still runs first; tampered or mismatching receipt is recomputed |
| The re-check disagrees with a real `present` run | The harness reproduces known facts (17 edition substitutes, 19 uncarried units); add a CI check that re-checks a freshly sealed bundle as `CURRENT` and one with a mutated renderer, judge, normalisation gate or fold stack as `UPDATE_REQUIRED` |

### 6.6 Tests

Focused tests with negative controls, per scope: a mutated renderer, a judge forced to fail, a
tightened authoring gate and a mutated `scope_defect` each give `UPDATE_REQUIRED` (the last is
already shown by the probe: 5 of 6 replays flip); deleting `raw_calls.json` gives `UNVERIFIED`; a
check absent from the record must run; a tampered file fails integrity before any re-check; a
receipt under another key is ignored; a constant bumped with no behavior change leaves
`RECHECKED_CURRENT`; a freshly sealed fixture is `CURRENT`; the funnel stays monotone and the
partition still sums to the denominator; the environment-version dry-run no longer routes to
`INVALIDATED`. Production-shaped proof: run the official entry point on the canary and `status` on
the committed 30, expecting section 4's numbers.

### 6.7 Effort

| Item | Hours |
|---|---|
| `recheck.py`: bundle loader, five scope re-checks (the probes already do render, validators, BC-04, inherited units, reviewer replay) | 10 |
| Receipt schema, writer, `recheck` command, refresh in the G7-W14 job | 5 |
| `portfolio.py`/`status`/`candidates.py` currency integration, bucket split, JSON | 5 |
| Dry-run/`evaluate` environment-version routing and absent-record fix | 3 |
| Bump-impact preview in CI (warn-only) | 4 |
| Tests and negative controls, production-shaped proof | 9 |
| Docs: STATE_MACHINE section 9, DECISION_LOG entry, layout | 2 |
| Migration run and review of the 30 receipts | 2 |
| **Total** | **about 40 (minimum useful slice: loader + status integration + routing fix, about 18)** |

Honest counterweight: the slice that changes today's numbers is the routing fix (24 false
`INVALIDATED` routes) and a more informative split of the 28 into 2 cheap and 26 expensive. The
re-check's larger payoff comes only if the contract stops moving: after a re-seal on frozen code,
the 25 zero-effect bumps of the last 15 days would have cost nothing.

## 7. Not verified, and decisions for the owner

Not verified: the real-run routing (only the dry run was read; `present` was not run); provider
cost per re-seal (quoted from the decision log, not measured here); pre/post runs use the commit's
own code but today's registry; reviewer and label scopes for bundles without raw reads; BC-01
original-bytes and BC-09 secret scan in the offline judge run; the claim that a prompt change
cannot affect validity is a policy reading, not a measurement. The hand-kept
ledger in `tests/test_sealed_bytes.py` (`KNOWN_BLOCKED_STALE`, entries expiring 2026-10-19 and
2026-11-04) is the same re-render idea kept by hand; receipts would replace it.

Decisions needed: (1) prompt-only differences: provenance (recommended) or optional update that
still stales; (2) whether `UNVERIFIED` reviewer scope counts at "independently accepted"
(recommended: no, until replayable); (3) release cadence: batch contract-hardening commits (the 7
above landed on 3 days) and honour G3-W07's freeze before the next re-seal; (4) `docs/` forbids
dated filenames (`REPOSITORY_LAYOUT.md` section 5), so this report is `docs/investigations/13-...`
rather than `docs/BUMP_COST_REPORT_2026-10-10.md`.
