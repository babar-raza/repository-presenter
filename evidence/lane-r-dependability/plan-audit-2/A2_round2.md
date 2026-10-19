# Plan audit round 2 (A2): commit 5f8f7ef5 on wt/laner-plan (parent 1aafd9dc)

Auditor: second-round adversarial, read-only. Burden of proof on the plan. Line numbers are at 5f8f7ef5 in `runs/wt/laner-plan`.
Edits to a queue item's `purpose` must be applied byte-identically to `project/state.yaml` (G3-W12 purpose line 76, W13 80, W14 84, W15 88, W16 92, W17 96, W18 100, W19 104) AND the YAML block in `docs/RESEARCH_AND_GUIDELINES.md` section 27.9 (starts about line 2211); `tests/test_queue_agreement.py::test_every_queued_item_carries_section_27_9s_text_verbatim` enforces it. The `owner:` field is not mirrored and not tested.

## 0. Checks run

| Check | Result |
|---|---|
| pytest `test_governance_consistency`, `test_queue_agreement`, `test_register_integrity`, `test_schemas`, `test_cursor`, `test_path_budget`, `test_plan_lint`, `test_version_bump_discipline` | all pass (4 xfail marks, 0 failures) |
| pytest `test_no_bump_check`, `test_routing_fields`, `test_debt_ledger`, `test_control_plane`, `test_readme_standard` (other tests that read touched files) | all pass |
| `ruff check .` / `ruff format --check .` | clean / 829 files formatted |
| Budgets | AGENTS.md 207 of 210; ESM 509 of 520 (11 spare); 8 gates |
| Verbatim-move check | every line removed from the ESM (1aafd9dc^ to HEAD) that is not an intended edit is present in `docs/investigations/15-esm-g7-history-2026-10-16.md`: the move is faithful |
| Machine facts | queue statuses allowed by `schemas/state.schema.json:115` are PENDING, BLOCKED_BY_GATE (needs `blocked_by` = a gate id), COMPLETE; active statuses are READY, IN_PROGRESS, VERIFYING, ACCEPTED, BLOCKED_EXTERNAL, FAILED_INTERNAL. E: has 27.2 GB free (measured now). `corrections/` has 0 tracked files. `ci.yml` uses `actions/checkout@v5` with no fetch-depth. |

The repository's tests see none of the findings below (all semantic or procedural).

## 1. Closure matrix (round 1 Critical and High)

Legend: RESOLVED, PARTIAL, OPEN, ACCEPTED-AS-RISK. "New" means a new defect the fix introduced is filed in section 2.

### Auditor A (governance)

| ID | Sev | Status | Resolving text or why not |
|---|---|---|---|
| A01 | Crit | PARTIAL | Rung 5a added (`project/loop-prompt-ship.md:75`: promotion "when G3-W11's acceptance holds ... into `active_work_item`"). But the same line says G3-W12 "may start beside G3-W11 now" with no mechanism: the cursor has one `active_work_item`, a queued item cannot be IN_PROGRESS (enum), the ship loop works "§2, in order, not `next_ready_items`", and 5a has no "Done:" line. A fresh executor still cannot start C1. R2-06. |
| A02 | Crit | RESOLVED | OWNER-24 (`state.yaml:420`) is the owner approval G7-W22 clause (2) allows for C3's content-loss bumps; W12 text (line 76): "a content-loss ground (C3: M1 to M3) needs OWNER-24 first"; factual-accuracy grounds (C2, C5, C6) need none. Residual: W14 as a whole becomes BLOCKED_EXTERNAL by loop-prompt s2 line 101 even for work that bumps nothing (Low). |
| A03 | High | RESOLVED | tools/ exception written into `docs/REPOSITORY_LAYOUT.md:220`, `tools/README.md:11`, `project/loop-prompt.md:24`. New: effective now, before any go, and D8 condition (2) still lists it as to-do (R2-20). |
| A04 | High | RESOLVED | W12 step 2: M1 to M3 and M9 from bundle files; "define M4 to M6 as interfaces over a detector registry", "write M7 and M8 as procedures"; M4/M5 independent of the C2 gate. New: M6 reviewer part not CI-computable (R2-04). |
| A05 | High | PARTIAL | D8 reframed as a plan (`DECISION_LOG.md:5998-6003`: "not an authorization ... follow a line `Owner go:`"). The 2026-10-15 owner direction ("no Lane R fix cycle"; Lane L first) is still not in the repository, and D8 now silently drops any mention of it (1aafd9dc said "supersedes"). The only record of that direction is the owner's auto-memory. The Owner go line will settle it if the owner writes it, but D8 should say the 10-15 direction is not recorded and that the go line supersedes it. R2-22. |
| A06 | High | RESOLVED | OWNER-23 `consumed_by: ["NONE"]` (`state.yaml:417`), precedent at lines 274, 288, 311, 318. |
| A07 | High | PARTIAL | W18 (line 100) "call-store seeding in core/llm/ belongs to G5-W02 and is imported, not edited". But W18's own M7 clause (fresh process, empty `runs/`, seeded from the sealed bundle, zero calls) IS G5-W02's acceptance, so C7 cannot complete, and the G3 exit "M7 holds" depends on a G5 item. R2-09. |
| A08 | High | RESOLVED | W15 owns `schemas/candidate-bundle.schema.json` after a section 31 proposal, `prompts/section_patch.yaml`; W14 mapping field and W18 digests likewise; OWNER-26 consumes them. Prompts are self-describing yaml validated by `tests/test_schemas.py`; no separate manifest file needed. |
| A09 | High | PARTIAL | Protocol now exists (W19: seeded blind script, 20 claims per README, 200 in all, stricter-verdict rule, blinding-quality measure; OWNER-25). Gaps: a second human rater who "did not write the cards" is a hard step but the owner is the only rater; OWNER-25's "before G3-W15" is not wired to W15. R2-14. |
| A10 | High | RESOLVED | Rung 5 note (line 70), rung 7 gated "Only after G3-W13 (C2) and G3-W17 (C6) are COMPLETE" (line 85), rung 5a. New: rung 5's selector contradicts its new sentence (R2-12) and rung 7 contradicts G3-W11's purpose (R2-13). |

### Auditor B (feasibility)

| ID | Sev | Status | Resolving text or why not |
|---|---|---|---|
| F1 | Crit | PARTIAL | M1 redefined over all live units, "DEFER_UNRESOLVED counts as not accounted" (line 76). Ambiguity: "removed with computed evidence" does not say whether a SUPERSEDE with an M3 coverage proof is accounted; and W12's Validation still says "M1 to M3 match ledger_baseline.json", which carries the OLD M1 (389 of 746). R2-03. |
| F2 | Crit | PARTIAL | W14: "M1 to M3 floors are measured on the live-anchored route in C4 and C8, not on the legacy composer". But the ESM exit (line 326) still measures M1 100 percent "on the test half of the frozen holdout", i.e. the legacy bundles. R2-08. |
| F3 | High | PARTIAL | Offline replay over frozen inputs and `present --at-revision` (W15). The replay input is unavailable: bundles keep `calls.jsonl` with `response_sha256` only, no reply text (checked on a real bundle), so "replies replayed" (W14) can only mean the sealed post-normalisation ledger. R2-15. |
| F4 | High | RESOLVED | W12 step 2 "implement M4 and M5 independently of the C2 gate and at least as broad"; "M1 to M5 are computed by tools/lane_r_audit without importing validation/, reconciliation/ or composition/ decision logic". Cost: two implementations of CONTRADICTED and claim-token matching (note in R2-26). |
| F5 | High | PARTIAL | FP now recorded "on the clean set and as the share of the LLM-owned units of the 30 stored candidates (about 25 percent of 3066 in the strict-rule prototype); above 5 percent C2 records a further owner item" (W13). The quoted 25 percent exceeds 5 before C2 starts, so C2 is born BLOCKED_EXTERNAL unless "5 percent" is scoped to the clean set. R2-16. |
| F6 | High | RESOLVED | W13 owned paths name `evidence/facts/published_version.py`, `extractors/surface/registry.py`, `core/package_registry.py`, `bundle/seal.py` (head re-resolution); typed reasons NO_REGISTRY/NOT_OWNED/UNREAD; "no new BC id". |
| F7 | High | RESOLVED | Rollback sentence rewritten (line 76): REVIEWER/VALIDATOR/NORMALISATION/RENDERER revert leaves candidates rechecked, EXTRACTOR revert UNVERIFIED, fact-record changes invalidate "every candidate without consumed_fact_ids", with a bump-and-revert test on the stored bundles. |
| F8 | High | PARTIAL | Dev/test split by hash of repository name, split committed before C2, detectors tuned on dev only (honor system), at least 4 of the 10 pilot repositories outside the corpus. Residual leakage: every class, rule and trace case was derived by agents reading all 30 bundles, so the test half is not a blind set; only the 4 or more fresh pilot repositories and the 14 unsealed registry entries are. R2-23. |
| F9 | High | RESOLVED | W12 step 4: at least 60 labeled cases, excerpts committed (review packets are not in the repo), clean twin per case, differential catch, at least 8 cases per class that carries a bar, probe readings as fixtures. |
| F10 | High | RESOLVED | W12 step 6: "control re-run ... deterministic stages offline over the frozen inputs ... baseline, because 23 of the 30 bundles were validated by validator version 3". |

### Auditor C (adversarial)

| ID | Sev | Status | Resolving text or why not |
|---|---|---|---|
| A-01 | Crit | RESOLVED | W19 Complete: "default is switched only when at least 8 of 10 new-route READMEs are accepted ... otherwise the item stays IN_PROGRESS with a typed finding ... Keeping the legacy default is a failed exit, never a completion"; ESM exit (line 326) has numeric thresholds and a named rater (OWNER-25). Thresholds are marked "(proposed)": acceptable while OWNER-25 is open. |
| A-02 | Crit | RESOLVED (by prose) | Rung 7 gated (line 85); W12 rule "until C2 is ACCEPTED no legacy candidate is proposed"; W13 propose gate refuses UPDATE_REQUIRED/UNVERIFIED bundles. Enforcement before W13 lands is prose only. New: the W13 gate changes stale-but-proposable semantics that G7-W22 clause (4) reserves for owner approval (R2-17). |
| A-03 | Crit | RESOLVED | Floors are numbers (line 76: M1 100 percent, M2 to M5 zero, M6 at least 95 and 90 per class, M8 zero in 200, M9 at least 8 of 10), yield metric M9 added, independence rule for M1 to M5. New: M1 to M3 are trivially met by the KEEP-default patch route (R2-08, R2-27). |
| A-04 | High | PARTIAL | See F8 (R2-23). |
| A-05 | High | PARTIAL | See A09 (R2-14); zero-in-200 statistics (R2-14). |
| A-06 | High | PARTIAL | Ratchet compares to `git show origin/main:...` (cannot be lowered by its own PR), "fails, never skips" when main is not fetched, waiver = owner item with expiry at most 14 days, one frozen base. But `ci.yml` is `actions/checkout@v5` at depth 1 and neither `.github/workflows/ci.yml`, `scripts/ci_check.sh` nor `.githooks/` is in any card's owned paths, so "never skips" fails every hosted run until a path nobody owns is edited. R2-07. |
| A-07 | High | PARTIAL | See F3 (R2-15). |
| A-08 | High | PARTIAL | Scratch-root script, refuses when `candidates/` is modified, sequential batches with clone deletion (line 76). The disk guard "refuses to run when the drive has under 40 GB free" can never pass on E: (27.2 GB free). R2-05. |
| A-09 | High | RESOLVED | W15: "a malformed, unknown-id, out-of-span or unverifiable operation is dropped, its unit is KEPT byte-identical ... nothing falls back to a replace". |
| A-10 | High | RESOLVED | W14: CONTRADICTED is computed by code (FAILED execution receipt, deterministic token-vs-fact mismatch, link the probe found missing) and "a fact id the model cites is never evidence by itself"; W15 DELETE "the applier recomputes". |
| A-11 | High | RESOLVED | W15: BC-05/BC-08/J4/J6 computed "from the live README bytes and the output bytes ... never from dispositions the same route wrote"; "seal refuses to replace a bundle of another route at the same revision"; schema change via section 31 proposal and OWNER-26. |
| A-12 | High | PARTIAL | W15: route in the PR body, refuse a candidate when an open presenter PR of the other route exists unless `supersedes_prs` names it. AGENTS.md line 137 still says Lane R is "regeneration from scratch" (flagged in D8, not edited), while the ESM, README_STANDARD PRC-07 and the ship loop say live-anchored. Two authorities disagree about what Lane R is. R2-24. |
| A-13 | High | PARTIAL | W13 adds capability-claim rules and a 90 percent bar for invented-capability and polarity classes. The rule is a trigger-word lexicon ("supports, adds, includes ..."); Q_claims T4 ("Model-View-Presenter server") and T2 ("image transformation") contain none of those words, so recall is unproven and rests on the reviewer. Measured at C2, so acceptable as risk (ACCEPTED-AS-RISK), but the card should say the lexicon is not the only mechanism. Low. |
| A-14 | High | PARTIAL | W17: presentation REJECT stays advisory, factual REJECT stands, reviewer-alone at least 70 percent, J7_REVIEW reconciles judge and propose. Still two contradictory statements: "gates plus reviewer together at least 95 percent with zero injected factual errors passing". R2-18. |

Tally of the 34 Critical/High findings (A01-A10 = 10, F1-F10 = 10, A-01..A-14 = 14): RESOLVED 17 (A02, A03, A04, A06, A08, A10, F4, F6, F7, F9, F10, A-01, A-02, A-03, A-09, A-10, A-11); PARTIAL 16 (A01, A05, A07, A09, F1, F2, F3, F5, F8, A-04, A-05, A-06, A-07, A-08, A-12, A-14); OPEN 0; ACCEPTED-AS-RISK 1 (A-13, recall of the capability lexicon, measured at C2).

## 2. New and remaining findings

Severity count: Critical 0, High 9 (R2-01 to R2-09), Medium 18 (R2-10 to R2-27), Low 4 (R2-28 to R2-31): 31 findings.

### High

**R2-01 High. The central authority gate (the owner's go) has no machine form.**
Evidence: W13 to W19 are `status: PENDING` (state.yaml lines 78-106) with no `blocked_by`, and no owner item gates them; the block lives only in prose ("Until the owner's go is recorded ... only G3-W12 may start") and in a DECISION_LOG line that any agent can write (`Owner go: <date, words>` has no author check). `schemas/state.schema.json:115-123` allows BLOCKED_BY_GATE only with `blocked_by` = a gate id, so the purpose text "C2 to C8 are BLOCKED_BY_GATE" (line 76) is not representable. `project/loop-prompt.md:101`: an item is BLOCKED_EXTERNAL only if it consumes an OPEN owner item. A rule-following executor that finishes G3-W12 sees W13 PENDING, unblocked.
Fix: add an owner item and reference it.
- `project/state.yaml`, after OWNER-26 (line 434 block), add:
```
  - id: OWNER-27
    status: OPEN
    summary: "The owner's go for G3-W13 to G3-W19 (Lane R dependable rebuild, cards C2 to C8), after reading the round-1 and round-2 audits."
    resume_predicate: "A line 'Owner go: <date, words>' in the D8 entry of docs/DECISION_LOG.md in a commit the owner authored; an agent never writes it. The line may name which cards it admits."
    consumed_by: ["G3-W13", "G3-W14", "G3-W15", "G3-W16", "G3-W17", "G3-W18", "G3-W19"]
    recorded_at: "2026-10-16T22:00:00+05:00"
    note: "Recorded with the second audit round. G3-W12 (C1, measurement only) does not consume it."
```
- W12 purpose (state.yaml 76 and 27.9), old: `C2 to C8 are BLOCKED_BY_GATE until the owner's go is recorded as a line 'Owner go: <date, words>' in the D8 entry of docs/DECISION_LOG.md.` -> new: `C2 to C8 are BLOCKED_EXTERNAL on OWNER-27 until the owner's go is recorded as a line 'Owner go: <date, words>' in the D8 entry of docs/DECISION_LOG.md, in a commit the owner authored.` Same replacement for the "Status words" sentence: old `blocked=BLOCKED_BY_GATE or BLOCKED_EXTERNAL` -> new `blocked=BLOCKED_EXTERNAL (an item consuming an OPEN owner item)`.
- Also drop "ready=READY ... complete=ACCEPTED" from the queue status words: old `Status words: backlog=PENDING, ready=READY, active=IN_PROGRESS, validation=VERIFYING, blocked=BLOCKED_BY_GATE or BLOCKED_EXTERNAL, complete=ACCEPTED.` -> new `Status words: a queued item is PENDING or COMPLETE; the active item is READY, IN_PROGRESS, VERIFYING, ACCEPTED or BLOCKED_EXTERNAL; "X ACCEPTED" in a prerequisite means the item is COMPLETE in the queue or ACCEPTED in the cursor.`

**R2-02 High. The judge hash that C8 pins is invalidated by C6.**
Evidence: W14 (line 84) "Evidence: lane-r/C3.json, which records the SHA-256 of acceptance/judge.py"; W19 (line 104) "the pilot is judged by the acceptance/judge.py whose SHA-256 C3's evidence records (a mismatch voids the pilot)"; W17 (line 96) owns `acceptance/judge.py (the new clause J7_REVIEW only)` and lands after W14. Adding J7 changes the file, so the hash C3 recorded can never match at pilot time: the rule voids its own pilot. Also W19 says "any J4 or J6 alignment lands in C3" but `acceptance/judge.py` is not in W14's owned paths.
Fix (state.yaml and 27.9):
- W14, old `Evidence: lane-r/C3.json, which records the SHA-256 of acceptance/judge.py.` -> new `Evidence: lane-r/C3.json. Any J4 or J6 alignment (acceptance/judge.py, those two clause definitions only, after G3-W11 is ACCEPTED, with the baseline re-derived and the change recorded in DECISION_LOG) is owned here; add acceptance/judge.py (J4 and J6 definitions only) to this card's owned paths.`
- W17, old `Evidence: lane-r/C6.json.` -> new `Evidence: lane-r/C6.json, which records the SHA-256 of acceptance/judge.py; C6 is the last card that may edit that file.`
- W19, old `the pilot is judged by the acceptance/judge.py whose SHA-256 C3's evidence records (a mismatch voids the pilot)` -> new `the pilot is judged by the acceptance/judge.py whose SHA-256 C6's evidence records (a mismatch voids the pilot)`; and old `acceptance/judge.py is not edited here (any J4 or J6 alignment lands in C3 with the judge's SHA-256 recorded, and only after G3-W11 is ACCEPTED)` -> new `acceptance/judge.py is not edited here (any J4 or J6 alignment lands in C3, J7 in C6, which records the final SHA-256)`.

**R2-03 High. C1's own Validation cannot be met: the committed baseline measures the old M1.**
Evidence: W12 Validation: "M1 to M3 match ledger_baseline.json". `evidence/lane-r-dependability/ledger_baseline.json` totals are `kept 746, kept_not_printed 389, omit_unsupported 338, omit_unsupported_without_fact 316, supersede_redundant 1514` (verified by summing the 30 bundles: 746, 389, 338, 316, 1514 all reproduce). The new M1 (all live units, byte-identical or removed with computed evidence) and new M2 (no CONTRADICTED evidence, 318) and M3 (coverage threshold "frozen in the baseline") have no field in that file; 318 appears only in the audit report B. M1 is also ambiguous for SUPERSEDE rows.
Fix (state.yaml 76 and 27.9), W12:
- old `Validation: two runs give identical M1 to M6 and M9; M1 to M3 match ledger_baseline.json; every test above passes.` -> new `Validation: two runs give identical M1 to M5 and M9 (M6 per R2-04); the harness reproduces ledger_baseline.json's v1 totals (746, 389, 338, 316, 1514, J4 29, J6 26) and writes ledger_baseline_v2.json holding the new M1 to M3 baselines, the 318 count and the frozen M3 threshold; every test above passes.`
- M1 definition, old `removed with computed evidence, over all live units;` -> new `removed with computed evidence (CONTRADICTED as W14 defines it, or an M3 coverage proof for a SUPERSEDE), over all live units;`.

**R2-04 High. M6's reviewer component is nondeterministic and cannot be a CI ratchet or a "two runs identical" quantity.**
Evidence: W12 step 2 makes "the reviewer" a baseline detector whose corpus catch rate is the M6 baseline; step 5 ratchets M1 to M6 computed "in CI"; Validation requires identical M1 to M6 across two runs. The reviewer is a gateway model (qwen3-next) whose repeated identical requests answered differently in 8 of 8 cases (`docs/investigations/14` F7); hosted CI has no model access. W17 then asserts reviewer-alone at least 70 percent as a single number.
Fix (state.yaml 76 and 27.9):
- W12, old `M6 catch rate on the corpus test split, differential (the detector fails the injected text and not its clean twin), per class and for reviewer alone and together;` -> new `M6 catch rate on the corpus test split, differential (the detector fails the injected text and not its clean twin), per class: M6d for the deterministic gates (computed in CI, ratcheted), M6r for the reviewer (live, run by a committed command at least three times, the per-case catch fraction and the lower bound reported, never in CI and never ratcheted), and together;`
- W12 step 5, old `holds the best value of M1 to M6 and M9` -> `holds the best value of M1 to M5, M6d and M9`.
- W17 Validation, old `the reviewer alone (gates off) catches at least 70 percent of the injected factual cases` -> `the reviewer alone (gates off), over three live runs, catches at least 70 percent of the injected factual cases in every run`.

**R2-05 High. The scratch-root disk guard can never pass on this machine.**
Evidence: W12 common rule (line 76): "refuses to run when the drive has under 40 GB free". E: has 27.2 GB free now (the project's disk; D: 52 GB, C: 1063 GB). Every live batch (C4 pilot, C8) would refuse. The pilot sizing in doc 14 R7 says a clone may be 1 GB, so the real need is a few GB.
Fix (state.yaml 76 and 27.9): old `refuses to run when the drive has under 40 GB free or git status shows a modified path under candidates/` -> new `refuses to run when the scratch drive has under 10 GB free (the batch deletes each clone after its repository and states its peak need first) or git status shows a modified path under candidates/; the scratch root may sit on another drive (C: has about 1 TB free)`.

**R2-06 High. "C1 may start beside G3-W11" is unexecutable and rung 5a has no done-when.**
Evidence: `project/state.yaml` has one `active_work_item` (G3-W11, IN_PROGRESS); a queued item's status cannot be IN_PROGRESS; `project/loop-prompt-ship.md:13-14` "Your queue is §2, in order. Not next_ready_items"; line 75 offers C1 "beside G3-W11 now" but its promotion clause fires only "when G3-W11's acceptance holds"; lines 44-86 give every other rung a "Done:" and §1 says the current rung is "the first whose done-when is not true". While C1 is half built, state.yaml reads PENDING and a fresh executor cannot tell it from untouched.
Fix: `project/loop-prompt-ship.md`, rung 5a, add at its start and end:
- old `G3-W12 (C1, measurement, no shared code) may start beside G3-W11 now.` -> new `G3-W12 (C1, measurement, no shared code) is started by the owner's order (a line "Start G3-W12" in the D8 entry), in its own worktree, beside G3-W11; the first C1 commit appends "STARTED <date> <commit>" to G3-W12's owner field in project/state.yaml, so a later session sees it is begun.`
- append `Done: G3-W19 is COMPLETE, or the owner has recorded a typed stop; until then, when the owner's go is absent, report 5a once as blocked on OWNER-27 and proceed to rung 6.`
And mirror the same sentence in the W12 owner field and `docs/EXECUTION_STATE_MACHINE.md` G3 item 4 ("G3-W12 (C1, measurement only) may start beside G3-W11" -> "G3-W12 (C1) starts on the owner's order beside G3-W11").

**R2-07 High. The ratchet and the bump-entry test need CI wiring no card owns.**
Evidence: W12 step 5 and `tests/test_governed_bump_entry.py` need `origin/main` and a pinned control revision "fetched, failing never skipping"; `.github/workflows/ci.yml:24` is a depth-1 `actions/checkout@v5` (the existing bump-discipline test documents that it skips there, `tests/test_version_bump_discipline.py:156-158`). W12 owned paths: `tools/lane_r_audit/`, three tests, `data/lane_r_corpus/`, evidence. Editing ci.yml also triggers `tests/test_workflow_rehearsal*` (fakes) and the operations-runbook generated block.
Fix: W12 owned paths, old `evidence/build/G3_PYTHON_COHORT/lane-r/.` (end of C1 owned list) -> new `evidence/build/G3_PYTHON_COHORT/lane-r/, .github/workflows/ci.yml (fetch-depth 0 or an explicit fetch of origin/main and the control revision, for these tests only), scripts/ci_check.sh and .githooks/ (the same fetch, local), docs/OPERATIONS_RUNBOOK.md (the generated workflow block), tests/test_workflow_rehearsal.py fixtures if the rehearsal reads ci.yml.` Add to Validation: `a hosted run of the ratchet on a branch whose file was lowered fails.`

**R2-08 High. The exit predicate measures M1 to M3 where the plan itself says they cannot be met.**
Evidence: ESM line 326: "measured on the test half of the frozen holdout ... M1 ledger completeness 100 percent and M2, M3, M4, M5 zero". The holdout is the 30 sealed LEGACY bundles; W14 (line 84): "the M1 to M3 floors are measured on the live-anchored route in C4 and C8, not on the legacy composer (only 56 percent of absent superseded non-heading units reach 0.8 coverage and 30 percent reach 0.95)". Meanwhile the live-anchored route gets M1 to M3 free (KEEP default; W15 "M1 is 100 percent by construction under KEEP and is not counted as a win"), so those three exit numbers are either unreachable (legacy) or non-discriminating (patch).
Fix (ESM line 326 and the cursor gate purpose line 33 need no change; ESM only):
old `measured on the test half of the frozen holdout, the C1 corpus and ten pilot repositories, at the final merged code revision (floors in the card text, changeable only by an owner decision): M1 ledger completeness 100 percent and M2, M3, M4, M5 zero;` -> new `measured at the final merged code revision (floors in the card text, changeable only by an owner decision): M1 ledger completeness 100 percent and M2, M3 zero on the ten pilot READMEs and on the test half of the holdout re-run through the live-anchored route at pinned revisions; M4, M5 zero on the same sets and on the corpus test split;`.

**R2-09 High. The G3 exit depends on a G5 work item.**
Evidence: W18 (line 100) Validation M7 requires "two runs in two fresh processes with an empty runs/ seeded only from the sealed bundle ... zero calls"; the same sentence says seeding "belongs to G5-W02", which is `PENDING`, in gate G5, whose acceptance is exactly that ("delete runs/, run present for every current candidate: byte-identical, zero calls"; it also removes identity:revision from every job packet, changing all request hashes). If G5-W02 is not accepted, W18 "records the digest only" and cannot meet its own Complete line "M7 holds on the pilot repositories"; the G3 exit (line 326 "M7 holds") then waits on G5.
Fix (state.yaml 100 and 27.9; ESM line 326): old `M7: two runs in two fresh processes with an empty runs/ seeded only from the sealed bundle are byte-identical with zero calls (regression evidence, since J5 already passes 30 of 30; it is memoization), and` -> new `M7: with a counting fake provider, a rerun over unchanged sections makes zero calls and is byte-identical (J5 already passes 30 of 30, so this is regression evidence and memoization); the fresh-process, empty-runs/ proof is G5-W02's acceptance and is not a G3 predicate; and`. ESM line 326 and W12 Metrics M7: drop "in fresh processes with an empty runs/ seeded only from the sealed bundle" correspondingly.

### Medium

**R2-10 Medium. C3 spends three governed bumps on a route the plan replaces.**
Evidence: W14 changes legacy `reconciliation/`, `placement.py`, NORMALISATION, INHERITED_UNITS and VALIDATOR (needs OWNER-24), then states the M1 to M3 floors are not reachable on that route (56 and 30 percent) and are measured on the C4 route. For a repository with a usable README the patch route copies live bytes; for one without there is nothing to preserve, so the legacy ledger defects (doc 14 F1, F4, F5, F6) are exactly those C4 removes. C3's reusable parts are the computed CONTRADICTED function, the M3 proof and BC-05 over every unit kind (C4 consumes "CONTRADICTED ... as C3 defines it").
Fix: W14 purpose, add after `Objective: a keep decision is honoured and a removal is justified.` -> `Scope rule: land the computed CONTRADICTED function, the M3 coverage proof and BC-05 over every unit kind first (they serve both routes); change the legacy reconciliation/placement behaviour only where the C1 harness shows a defect that route still ships after G3-W15 would not remove, and record that finding in DECISION_LOG before the NORMALISATION or INHERITED_UNITS bump.` Consider ordering W15 before the legacy-route parts of W14; the owner decides.

**R2-11 Medium. C5 edits extractors without an EXTRACTOR bump and its prerequisite violates one-at-a-time.**
Evidence: W16 (line 92) owns `extractors/surface/doc_text.py` and the `build_test_asset` fact, yet its Governed line is "RENDERER_VERSION only when a named case needs it"; extractor output changes need EXTRACTOR_VERSION (W13 already bumps it once, leaving candidates UNVERIFIED). Prerequisite "C4 started" while "one shared-code card at a time".
Fix: W16, old `Prerequisites: C4 started (the sections must be reachable from the patch engine). Dependencies: C4.` -> `Prerequisites: C4 ACCEPTED. Dependencies: C4.`; old `Governed: RENDERER_VERSION only when a named case needs it, otherwise the card ships without that bump.` -> `Governed: EXTRACTOR_VERSION (the doc_text and build_test_asset fixes change fact records; fold them into C2's single extractor bump if C5 is pulled before C2 lands) and RENDERER_VERSION only when a named case needs it, each behind its own entry.`

**R2-12 Medium. Rung 5's selector contradicts its new sentence.**
Evidence: `project/loop-prompt-ship.md:70-73` selects "repositories without a standard live README (`readme: false`, `glance_form: null` or `banner: false`)" and then (new) says "This rung seals only repositories without a usable live README (from scratch is correct there, README_STANDARD PRC-07)". `data/readme_standard/survey.json` (44 rows): `readme: false` is 1 row; the other 12 matching rows have a README with no banner or glance form. PRC-07 (`docs/README_STANDARD.md:118`) forbids authoring from scratch where a README exists. So the selector sweeps 12 rows the sentence forbids.
Fix: rung 5, old `(from scratch is correct there, README_STANDARD PRC-07)` -> `(from scratch is correct only where survey.json says readme: false, one row at 5f8f7ef5; the other twelve rows the selector matches have a README, wait for the live-anchored route of G3-W15, and get a judge verdict on their existing sealed bundle meanwhile)`.

**R2-13 Medium. Three statements disagree on when Lane R may first propose.**
Evidence: `state.yaml:47` (active G3-W11): "the first Lane R proposal is the G3 exit predicate and waits for G3-W19 (C8)"; ship rung 7 (line 85): "Only after G3-W13 (C2) and G3-W17 (C6) are COMPLETE" a judge-authorized candidate proposes; W12 rule: "until C2 is ACCEPTED no legacy candidate is proposed" (implying after C2). Rung 7 also cites "J7 included" and "the C1 harness shows ... zero M4 escapes".
Fix (the owner chooses; recommended): `project/state.yaml` active item purpose, old `the first Lane R proposal is the G3 exit predicate and waits for G3-W19 (C8)` -> `the first Lane R proposal (ship rung 7) waits for G3-W13 and G3-W17 and the owner's order; the dependable default waits for G3-W19`.

**R2-14 Medium. The human review plan assumes a rater the owner does not have, and its completion is hostage to the owner's hours.**
Evidence: W19 step: "a second human rater who did not write the cards rates a random half"; OWNER-25 asks the owner to "name ... a second human rater". With the owner as the only rater this is BLOCKED_EXTERNAL at the last card. OWNER-25's resume predicate says the ten repositories are committed "before G3-W15 starts" but `consumed_by: ["G3-W19"]` and W15's prerequisites name only OWNER-26. M8 (200 claims, zero NOT SUPPORTED) at a true per-claim error rate of 1 percent passes with probability 0.99^200, about 13 percent; and every claim inherited unchanged from a live README that has drifted (14 of 34 candidates drifted since seal, Q_claims class E) counts as NOT SUPPORTED.
Fix: OWNER-25 `consumed_by` -> `["G3-W15", "G3-W19"]`; W15 Prerequisites old `C2 and C3 ACCEPTED; OWNER-26 answered.` -> `C2 and C3 ACCEPTED; OWNER-26 and OWNER-25's repository list answered.`; W19 step, old `and a second human rater who did not write the cards rates a random half (an agent session is not a rater)` -> `and, if OWNER-25 names a second human rater, that rater rates a random half; with no second rater the owner rates all ten alone, the blinding-quality number is reported as weakened and the exit says so (an agent session is never a rater)`; M8 text old `M8 passes only at zero NOT SUPPORTED` -> `M8 samples only claims the route added or changed, plus a separate count of NOT SUPPORTED claims inherited from the live README (reported, not a pass criterion); M8 passes at zero NOT SUPPORTED among added or changed claims`.

**R2-15 Medium. C3's offline "replies replayed" has no replay source.**
Evidence: W14 Validation "S4 reconciliation, placement and BC-05 are re-run offline over the frozen inputs (sealed facts, investigation and replies replayed ...)". Checked a sealed bundle: `calls.jsonl` records `request_sha256`/`response_sha256`, token counts and job, not reply text; `raw_calls.json` exists for 6 of 30 and covers the reviewer only; the run cache `runs/` is gitignored (G5-W02's motivation). Only the post-normalisation `dispositions.json` and `content_units.json` are committed.
Fix: W14 Validation, old `(sealed facts, investigation and replies replayed; no clone, no provider call, writes only under the scratch root;` -> `(sealed facts, investigation, content_units.json and the post-normalisation dispositions.json replayed as the ledger; raw model replies are not committed (calls.jsonl keeps hashes only), so a rule that changes normalisation is tested on the sealed ledger rows and reported as "rows it would reject", never as a re-derived ledger; no clone, no provider call, writes only under the scratch root;`.

**R2-16 Medium. C2's 5 percent owner trigger fires on its own prototype number.**
Evidence: W13 (line 80): "the false-positive rate recorded on the clean set and as the share of the LLM-owned units of the 30 stored candidates the gate flags (about 25 percent of 3066 in the strict-rule prototype); above 5 percent C2 records a further owner item and is BLOCKED_EXTERNAL". The 30 stored candidates carry real errors, so the flagged share is not a false-positive rate, and 25 percent is already above 5.
Fix: old `above 5 percent C2 records a further owner item and is BLOCKED_EXTERNAL on it;` -> `a false-positive rate above 5 percent on the clean set records a further owner item and C2 is BLOCKED_EXTERNAL on it; the flagged share of the 30 stored candidates is reported for the owner and is not a trigger;`.

**R2-17 Medium. C2's propose gate changes counting and proposability that G7-W22 clause (4) reserves to the owner.**
Evidence: G7-W22 clause (4) (`state.yaml` G7-W22): "no invalidation or counting behavior changes until the owner has seen that report" and its status "the owner's approval of the counting change is not recorded". W13 makes `proposal_gate_refusal` refuse UPDATE_REQUIRED/UNVERIFIED bundles that `wave.py` today calls "still proposable by hash", and prints such rows BLOCKED.
Fix: OWNER-24 summary, old `Whether the C3 governed-version bumps (NORMALISATION, INHERITED_UNITS, VALIDATOR) are approved under G7-W22 clause (2) when the ground is inherited-content loss (M1 to M3) and not a factual-accuracy defect.` -> `(a) whether the C3 governed-version bumps ... are approved under G7-W22 clause (2) when the ground is inherited-content loss; and (b) whether G3-W13's propose gate (a stale bundle is refused, not proposable by hash) is the counting change G7-W22 clause (4) reserves for the owner.`; `consumed_by` -> `["G3-W13", "G3-W14"]`; the "G3-W12, G3-W13 and G3-W17 proceed without it" sentence in its resume predicate -> `G3-W12 and G3-W17 proceed without it`.

**R2-18 Medium. C6's validation states 95 percent and zero in one sentence.**
Evidence: W17 (line 96): "gates plus reviewer together at least 95 percent with zero injected factual errors passing" (A-14 flagged the same two-number shape).
Fix: old `gates plus reviewer together at least 95 percent with zero injected factual errors passing` -> `gates plus reviewer together at least 95 percent, and zero of the ten traced cases T1 to T10 passing`.

**R2-19 Medium. Stale cross-references and counts left by the card split.**
Evidence and fixes:
- `docs/EXECUTION_STATE_MACHINE.md:31` "dependability is rebuilt in G3-W12 (idempotence, G3-W11)" -> `dependability is rebuilt in G3-W12 to G3-W19 (idempotence, G3-W11)`.
- ESM line 83 principle 26 "(G3-W12)" -> `(G3-W12 to G3-W19)`.
- `docs/investigations/14-lane-r-dependability.md:52` "(G3-W12 C4)" -> `(G3-W15, C4)`; line 69 (section 5 item 4) "built on the Lane L engine" -> `reusing Lane L's apply and confinement ideas only (its Edit is a line fragment of at most 200 characters with no delete or heading insertion, so the operation type is new; G3-W15)`; item 7 "copy-through; only units whose input facts changed call the model" -> `per-section memoization (G3-W18), honestly named`; section 7 R1 "run it on the 30 live READMEs as a negative control" -> `run it on the clean set and report the flagged share of the 30 stored candidates separately (G3-W13)`; R2 "AGENTS necessity test" -> `the G3-W12 bump rule (G7-W22 clause 2)`; R4 "compared with legacy R on M1-M8" -> `M1-M9`.
- `docs/investigations/14-lane-r-dependability.md` section 9: "feasibility and measurement 17 (2 Critical, 6 High)" -> `17 (2 Critical, 8 High)` (B's table: F3 to F10 are High).
- `project/loop-prompt-ship.md:16` "except the G3-W12 cards" -> `except the cards G3-W12 to G3-W19`; line 70 "Lane R changes ride G3-W12's cards ... C1 first" -> `ride G3-W12 to G3-W19`.
- `docs/DECISION_LOG.md:6001` condition (3) "OWNER-24 before C3's first bump and if C2 flags more than 5 percent" -> the 5 percent case is a separate owner item C2 records, not OWNER-24; condition (7) "G5-W02 ACCEPTED or untouched before C7 edits core/llm/" is obsolete (W18 never edits core/llm) -> replace with `(7) G3-W18's M7 is the memoization proof only; the fresh-process proof stays G5-W02's`.
- Nomenclature: "necessity test" (ship loop line 18, G3-W11 acceptance bullet 4 "necessity finding"), "necessity entry" (ship rung 3), "ground-naming entry" (ESM item 4) name one thing; AGENTS.md has no such rule (A15). Use "bump entry" everywhere.
- `project/loop-prompt.md:23-24` the edited bullet is indented four spaces (renders as a code block continuation); unindent.

**R2-20 Medium. A governance loosening took effect before any go.**
Evidence: the `tools/` exception is already written into REPOSITORY_LAYOUT, tools/README.md and loop-prompt.md (5f8f7ef5), i.e. the boundary "the loop never touches tools/" is relaxed by a plan commit; D8 condition (2) and doc 14 section 8 (2) still say C1 records it in its first commit.
Fix: DECISION_LOG D8 condition (2) and doc 14 section 8 (2), old `C1 records its tools/ exception in layout, tools/README.md and loop-prompt.md in its first commit` -> `the tools/ exception is recorded (5f8f7ef5) and is dormant until C1 creates tools/lane_r_audit/; if the owner does not start C1, revert those three lines`.

**R2-21 Medium. The correction-bundle regression guard is vacuous today.**
Evidence: W12 rule: "before and after each card load_proposable_correction passes unchanged on every committed correction bundle under corrections/". `git ls-files corrections/` is empty at 5f8f7ef5, so the test passes on zero bundles.
Fix: old `passes unchanged on every committed correction bundle under corrections/` -> `passes unchanged on every committed correction bundle under corrections/ and on a fixture bundle committed under tests/ (the test fails when it finds zero bundles of either kind)`.

**R2-22 Medium. The 2026-10-15 owner direction is not recorded, and D8 no longer addresses it.**
Evidence: the owner's 2026-10-15 direction (hold the freeze, no Lane R fix cycle, Lane L is the goal) exists only in the user's auto-memory; D8 (`DECISION_LOG.md:5999`) says it "does not supersede the 2026-10-14 directive" and is silent on 10-15.
Fix: D8 "What" sentence, append: `The 2026-10-15 direction (no Lane R fix cycle) is not recorded in this repository; the plan is the owner's 2026-10-16 request to plan, and the Owner go line either supersedes that direction for the cards it admits or leaves it standing.`

**R2-23 Medium. The held-out set is not held out, and the floors are point estimates on small n.**
Evidence: the dev/test split (W12 step 4) is by repository inside the same 30 bundles that produced Q_claims' classes and T1 to T10; "detectors tuned on dev only" is unenforced. With 60 cases split in two, the test half has about 30 cases and classes with 5 test cases; "at least 95 percent" on 20 cases means at most one miss, a 29-of-30 result has a 95 percent lower bound of about 83 percent. The plan presents the numbers as guarantees.
Fix: W12 step 4, append `The C1 evidence reports, for every floor, the number of test cases and the exact binomial lower bound; the floors are acceptance numbers for this corpus, not claims of a population rate; the only genuinely unseen inputs are the at least four fresh pilot repositories, so C8 raises that to at least six of ten.` (and W19 "at least four" -> "at least six").

**R2-24 Medium. AGENTS.md and the plan define Lane R differently.**
Evidence: `AGENTS.md:137` "Two product lanes: live-first ... and regeneration from scratch"; ESM line 30 "Lane R ... is live-anchored where a usable README exists"; README_STANDARD PRC-07 allows from-scratch only without a README; D8 flags it for the owner. A new executor reads AGENTS.md first (Read Before Acting 1) and sees the old definition.
Fix (owner decision; one-line, no line-count change): `AGENTS.md:137`, old `regeneration from scratch` -> `regeneration (live-anchored where a usable README exists, from scratch only where none does, README_STANDARD PRC-07)`. Until the owner makes this edit, add to W12's purpose head: `AGENTS.md line 137 is superseded on this point by README_STANDARD PRC-07 and ESM section 1`.

**R2-25 Medium. Two plan rules are internally inconsistent with existing principles.**
Evidence: (a) ESM principle 8 (line 63): "an omission only on CONTRADICTED evidence" while W14 allows SUPERSEDE_REDUNDANT with an M3 coverage proof and shell-owned kinds: a removal that is not on CONTRADICTED evidence. (b) ESM principle 23 (line 80): the acceptance contract changes only at declared version boundaries with regression evaluation across every current candidate; W13 and W14 change BC-04, BC-05, BC-14 meaning and the judge (W17 adds J7) with no CONTRACT_VERSION or ACCEPTANCE_PROFILE_VERSION decision (both appear in G7-W22 clause 2's governed list).
Fix: principle 8, old `or omit every material unit, an omission only on CONTRADICTED evidence (G3-W14, C3); everything else is kept and flagged.` -> `or omit every material unit, an omission only on CONTRADICTED evidence and a supersession only with a coverage proof (G3-W14, C3); everything else is kept and flagged.` W12 rule, append: `a card that changes a blocking check's meaning states whether CONTRACT_VERSION or ACCEPTANCE_PROFILE_VERSION moves and records the regression evaluation of principle 23 over the 30 bundles in its evidence.`

**R2-26 Medium. M1 to M5 and the claim gate are built twice.**
Evidence: W12 step 2 requires M4 and M5 "independently of the C2 gate and at least as broad" and M1 to M5 without importing reconciliation/validation/composition logic; so C1 implements CONTRADICTED computation and claim-token matching, and C3 and C2 implement them again. Two implementations drift; C1's "at least as broad" bar makes C1 larger than C2.
Fix: W12 step 2, append `Size cap: the independent implementation is a reference checker over the corpus and the pinned bundles (no new fact kinds, no network), at most a few hundred lines; where it and the gate disagree the disagreement is a finding for the owner, not an automatic C2 failure.`

**R2-27 Medium. A kept live byte is never checked by M4, but M8 counts it.**
Evidence: W13's gate checks "LLM-owned prose"; a unit kept byte-identical from the live README has no cited fact, so M4 is vacuous for it (and M1 to M3 are vacuous under KEEP). Q_claims class E: 14 of 34 candidates have drifted since seal; the live READMEs carry stale claims ("Python 3.7+"). Lane L's detectors cover this, but W15 only forwards "Lane L detector gaps" to the model.
Fix: W15 Validation, append `a kept live unit that makes a version, identifier or package claim is checked by the same deterministic comparison against current facts (a mismatch is a finding, and the section's operation list may REPLACE it with the fact value); the count of such stale kept claims is reported per pilot README.`

### Low

**R2-28 Low.** Queue purposes remain 10 to 3 times the loop's own limit ("about a thousand characters", `loop-prompt.md:39`): W12 10,286 characters (grew from 9,816), W13 3,839, W14 3,019, W15 4,065, W16 1,455, W17 2,455, W18 1,815, W19 3,044 (about 30,000 in all). The split put the common rules into W12 rather than shrinking anything. Fix: move W12's common-rules and metrics paragraphs to `docs/investigations/14-lane-r-dependability.md` section 10 ("Rules and metrics") and leave in W12 one sentence naming it; but the tests require 27.9 and state.yaml text equal, so edit both together.

**R2-29 Low.** `owner:` strings (about 430 characters) are repeated verbatim on 8 items and not mirrored in 27.9, so no test catches drift. Fix: `owner: "D8 plan 2026-10-16; see G3-W12"` on W13 to W19.

**R2-30 Low.** W12 step 4 "approve the sample list G3-W12 commits" and M8 "committed sample list": the sample of claims is drawn from pilot READMEs that do not exist until C8; C1 can commit only the sampler and seed. Fix: step 2, old `write M7 and M8 as procedures with a committed sample list` -> `write M7 and M8 as procedures with a committed sampler and seed (the claim sample itself is drawn by C8)`.

**R2-31 Low.** The three governed constants W14 owns include `INHERITED_UNITS_VERSION` and `NORMALISATION_VERSION`, but `tests/test_version_bump_discipline.py` governs only renderer, normalisation, reviewer_logic and validator; reconciliation/ and placement.py have no constant, so meaning changes there are undetected. Fix: W14, append `a change to reconciliation/ or placement.py that alters output names the constant it moves (NORMALISATION) in its entry.`

## 3. Fresh attack (what round 1 did not examine)

### 3a. Card set: sufficient and necessary?

Coverage of doc 14 section 2 failure classes:
| Finding | Covered by | Gap |
|---|---|---|
| F1 keep not honoured | C3, C4 (KEEP default) | none, but see R2-10 (legacy route) |
| F2 citation not truth | C2 | recall of capability claims unproven (A-13); kept live bytes unchecked (R2-27) |
| F3 reviewer overruled | C6 | reviewer-alone metric nondeterministic (R2-04) |
| F4 unsupported used as false | C3 | none |
| F5 redundant unverified | C3 (M3) | legacy-only |
| F6 no position or grouping | C4 (live is the skeleton) | none on patch route; legacy route unfixed by design |
| F7 reruns memoized | C7 | honestly named; proof leans on G5-W02 (R2-09) |
| F8 same-model reviewer | C6 / OWNER-23 | entailment route unmeasured until C6 |
| F9 staleness | C2 (published_version, head re-resolution) | drift of kept live bytes (R2-27) |
| F10 junk | C2 lint (C5 fixes upstream) | C5 EXTRACTOR bump (R2-11) |

Not covered by any card: (1) examples verification (`BLOCKED_TOOLCHAIN: tsc did not report a version` appears in DEFECT_INDEX for the same era): a README that keeps or inserts an unverified example is not a factual-claim token; the plan relies on C4's "FAILED execution receipt" for deletion only, not for blocking insertion. (2) Gateway outage as a first-class outcome in the pilot (W15 says "stops at the first gateway failure" but no card defines what a partial pilot reports). (3) Examples and commands that the live README carries and C4 KEEPs are covered only by Lane L.

Unnecessary or mis-ordered: C5 is mostly an inventory ("which sections already render from facts ... already do") plus two upstream extractor fixes; its extractor fixes belong in C2's single EXTRACTOR bump (R2-11), leaving a smaller card. C3 should follow, or be reduced by, C4 (R2-10). C6 depends on C1 and C2 only, so it can run before C3 to C5; the ordering by number is not a dependency order (state this: W17 may run right after W13). C7 is the weakest card: it is memoization and its only unique content (a per-section digest) belongs inside C4's design (W15 already calls per section), so a separate card plus a G5 dependency is questionable. Recommend folding C7's digest into W15 and keeping the fresh-process proof with G5-W02.

### 3b. Executable under this project's constraints?

- One shared-code item at a time and a 40-minute pre-push hook: eight serial cards, each with at least two pushes (code, then evidence/cursor) means at least 16 pushes, about 11 hours of hook time alone; acceptable. The risk is not the hook but the voiding rules.
- Disk: 27.2 GB free on E: against a 40 GB guard (R2-05); the guard also blocks every live batch.
- Gateway outage history and no determinism: offline-first validation is correct (W12 step 6, W14); the live parts are W15 pilot (about 20 calls times 7 repositories), W17 reviewer trials (three runs times the corpus test split), W19 (about 10 repositories). Outage handling is "stop at first failure" with no resumption rule; add "resume at the next repository, never repeat a completed one".
- Human raters: only the owner (R2-14).
- Estimate (my judgment, agent working days, serial, healthy gateway): C1 5 to 8; C2 4 to 6; C3 4 to 6; C4 8 to 12; C5 2 to 4; C6 4 to 6; C7 3 to 5; C8 3 to 5 plus the owner's blind review; about 33 to 52 working days, so 7 to 10 calendar weeks, before any owner wait. Plausibly completable only if the owner commits review time; as written, completion within a month is not plausible.
- Single biggest schedule and cost risk: the pilot-voiding rules combined with one human rater. W19 voids the pilot on any governed-version move after it, on a judge hash mismatch (R2-02), and requires it at "the final merged code revision"; with eight serial cards and one fresh extractor, validator or reviewer fix per late defect, each void costs another round of the owner reading 10 READMEs and auditing 200 claims against pinned sources (about 10 to 15 hours of owner time per round by my estimate). A single missed round restarts that. Mitigation: freeze all governed versions at W18's close, run the pilot once, and treat a defect found later as the next plan, not a void.

### 3c. Conflicts with standing rules

- D6 (no product writes): not violated; the common rule (line 76) bars registry mode changes and a test pins registry modes. Note the registry has 2 `full` entries (sealing-scheduled reads `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`); W19's rollback keeps `REPOSITORY_PRESENTER_SEALING_PAUSED` at 1 (correct and precise, value of that variable not read by me).
- G7-W22: clause (2) handled (OWNER-24, factual-accuracy grounds); clause (4) not (R2-17); clause (3) (non-blocking defects logged, left unfixed) is in tension with W13's lint rules for formatting junk (non-blocking class) which W13 turns into blocking gates; state that the lint is blocking only for the defect classes named.
- Principle 25 (write-scope expansion): untouched; C8 never flips a mode.
- Principle 23: not addressed (R2-25b).
- AGENTS.md: Lane R definition (R2-24); "Independent review separate from candidate authorship": C6 cross-family route is gated on OWNER-23, fine; "Count progress in one unit": M9 and the C8 status line print yield beside, never as progress, correct; "keep governance within budget": 509 of 520 ESM lines, 207 of 210 AGENTS lines: any further card-status edit to the ESM breaks the cap, so R2-19's edits must be net-zero lines (they are word replacements).
- "Research a battle-tested library before writing a custom mechanism" (AGENTS): W13's capability lexicon and W14's coverage proof are custom; W17 names MiniCheck-class entailment as the alternative, which is the right instinct; add to W13 that the lexicon rule is the fallback and the registry's first choice (RESEARCH section 18) is consulted and cited in the commit.

### 3d. Honesty of quoted numbers

Checked against `evidence/lane-r-dependability/ledger_baseline.json` (summed over its 30 bundles) and the reports:
| Quoted figure | Verdict |
|---|---|
| 746 kept, 389 not printed, 338 OMIT_UNSUPPORTED, 316 without a fact, 1514 SUPERSEDE_REDUNDANT | Supported exactly (totals block and per-bundle sums agree). |
| 29 of 30 fail J4, 26 of 30 fail J6 | Supported (`judge_failing` counts 29 and 26; J6 "applies to 26" per DECISION_LOG, so the other four are not applicable, not passes). |
| 26 of 30 model REJECTs folded to ACCEPT (22 presentation, 4 factual) | Supported by `R_determinism_review.md` line 23. |
| 318 of 338 OMIT_UNSUPPORTED lack CONTRADICTED evidence; 56 and 30 percent coverage | Not in ledger_baseline.json; produced by auditor B's scratch scripts (committed only as prose in `plan-audit-1/B_feasibility.md`). Plausible, unreproducible from the repository until C1 re-derives them; the W12 baseline sentence cites ledger_baseline.json for them implicitly (R2-03). |
| "about 22 hand-found factual errors in 14 sealed bundles" | Supported only as approximate (`R_determinism_review.md` line 44: "14 bundles (about 22 errors, 15 with Email-.NET)"). `Q_claims.md` counts "candidates affected (of 34)": class B 16, C 11, D 13 (40 candidate-class incidences, denominator 34 including 4 draft candidates) cannot be reconciled with 22 errors in 14 of 30; the plan hedges "agent-read, approximate" in W12 but D8 (`DECISION_LOG.md:6000`) states it without the hedge. Add the hedge. |
| "1514 ... 55 percent" and "389 of 746 (52 percent)" | Arithmetic correct (1514/2761 = 54.8; 389/746 = 52.1). |
| "2 of the 4 factual REJECTs were wrong" (W17) | Soft: rests on one hand reviewer finding "no invented claims" in two bundles; a REJECT_FACTUAL can name a non-invention error. State "2 of 4 not confirmed by the hand reviewer". |
| "313 stored advisory findings", "raw_calls.json for 6 only" | From B (committed report); not independently re-counted by me. |
| "23 of the 30 bundles validated by validator version 3", "14 of 34 drifted" | From B and Q; not independently re-counted by me. |
| doc 14 section 9 "17 (2 Critical, 6 High)" | Wrong: 8 High (R2-19). |

## 4. Verdicts

**G3-W12 (C1, measurement card): READY WITH CONDITIONS.** C1 touches no product code and can safely be built, but it will fail its own gate or never run in hosted CI unless these text corrections land first (all are edits to the queue text, none needs the owner's go):
1. R2-03 (validation text and baseline v2), 2. R2-04 (M6 split), 3. R2-05 (disk guard), 4. R2-06 (a start order and a visible STARTED marker), 5. R2-07 (CI wiring ownership), 6. R2-21 (non-vacuous correction guard), 7. R2-30 and R2-26 (sampler, size cap), 8. the owner's start order (C1 competes with G3-W11 for the single active slot and with the 2026-10-15 direction, R2-22).

**G3-W13 to G3-W19: NOT READY, pending the owner's go.** Conditions, in addition to the go (R2-01 gives it a machine form as OWNER-27):
- before W13: R2-16, R2-17, R2-25b, R2-11 (extractor bump scheduling);
- before W14: R2-02, R2-10, R2-15, OWNER-24;
- before W15: R2-14 (OWNER-25 repository list), R2-23, R2-27, OWNER-26;
- before W17: R2-18, R2-04, R2-02;
- before W18: R2-09, OWNER-26;
- before W19: R2-14, R2-02, R2-08, OWNER-25;
- cross-cutting: R2-12, R2-13, R2-19, R2-20, R2-22, R2-24.

## 5. Report summary

Closure of 34 Critical/High findings from round 1: RESOLVED 17, PARTIAL 16, OPEN 0, ACCEPTED-AS-RISK 1. New or remaining: Critical 0, High 9, Medium 18, Low 4 (31 findings). Repository tests and ruff are green; none of the findings is visible to them.
