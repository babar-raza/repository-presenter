This file is the execution-control layer (taskcards, micro-steps, gates) of the registered work items G7-W21 and G7-W22 in project/state.yaml; it is not a new plan, and on any conflict the registered entry wins.

# Taskcard Execution Layer for G7-W21 / G7-W22: Reseal Once, Operate the Issue System, Run the Refresh App

```yaml
plan_id: PLAN-MONDAY-RESEAL-ISSUES-REFRESH
authoritative_plan: >
  The REGISTERED plan is authoritative: project/state.yaml items G7-W21 (Monday delivery) and G7-W22
  (candidate-currency freeze), with G6-W01, G6-W03, G7-W14, G7-W06, G7-W20 and the 2026-10-10
  DECISION_LOG entries. THIS FILE is only their execution-control layer (taskcards, micro-steps, gates).
  On any conflict the registered entry wins. This file is NOT a new plan.
artifact_role: execution_control_layer
execution_authority: only through the registered items it names; none of its own
home: plans/reseal-and-refresh/PLAN.md   # sprint/healing precedent: static plan + loop-status.jsonl + loop-instructions.jsonl
base_commit: origin/main 7c5acbf7 (2026-10-10)
authored: 2026-10-10 (Saturday); Monday delivery target is 2026-10-12
placed: 2026-10-10 by TC-GOV-01 (lane L-gov); card statuses printed here are initial, the live fold is loop-status.jsonl
```

**Read first (honest status of this document).** My first draft of this plan was built on a main checkout that was **22 commits behind `origin/main`**, so it duplicated work the owner had already registered (G7-W21/W22) and landed (#304 candidates publish, #308 profile ratification, #309 proposal-wave tool, #311, #313 bump-cost investigation, #314 issue harvest). Everything below is re-based on `origin/main 7c5acbf7`. Where a number came from the stale checkout it is marked **STALE-BASE** and a card re-derives it.

**Reading guide.** §1 context and findings · §2 what already exists · §3 requirements · §4 authority and storage · §5 options · §6 machine state · §7 tracks, order, locks · §8–§11 taskcards · §12 validation, evidence, scoring · §13 handoff · §14 feedback and decisions for you.

---

## 1. Context and findings

The owner's complaint (register G7-W22): each enhancement bumps a governed version, every sealed candidate reads stale, and re-sealing starts again. The owner's standing rulings (DECISION_LOG 2026-10-09/10): one cut, one portfolio reseal, no governed-version bump afterwards except safety/factual-accuracy defects or owner approval; **no real upstream push until 20 candidates are re-sealed**; the name gate is unchanged; Monday 2026-10-12 targets "the live autonomous system proven once", at least 20 candidates pushed *as a target, not a claim*, with an upstream issue logger active.

The owner's quality bar (this session): ALL useful information from the cloned repository in ONE README, every claim true, valuable existing content preserved, the standard 10-section template; better than the aspose.org skill.

### 1.1 Findings register (class: **RUN** I executed it · **READ** I read it · **AGENT** an agent claimed it, evidence in its report · **STALE-BASE** from the stale checkout, to be re-derived)

| ID | Finding | Class |
|---|---|---|
| F-01 | On origin/main: `status` = 2/36 current-code reproducible (BarCode-Python, Cells-Python); 28 stale. Versions now NORMALISATION 32, REVIEWER_LOGIC 18, VALIDATOR 17, RENDERER 30 | RUN |
| F-02 | Doc 13 (measured): of 39 bump commits since 09-24, 7 changed some candidate's outcome (all stricter contract rules the owner wanted), 25 changed nothing a candidate consumed, 7 not replayable; of the 28 stale bundles 26 need re-composition, 2 need re-render + a review read, 0 are still valid | READ |
| F-03 | `tests/test_version_bump_discipline.py` forces a bump on any non-docstring AST change to the four governed files | READ+AGENT |
| F-04 | Bundles were sealed on Windows/Python 3.13; hosted sealing runs ubuntu/3.11; `environment.*` is a recorded dependency | READ |
| F-05 | Monitor (pre-#305 checkout, **STALE-BASE** for two bundles): 11 DRIFTED, 19 source-equal, 6 NO_BUNDLE. `wave-readiness` on origin/main: 29 READY, 19 source-current, 10 `source_moved` | RUN+READ |
| F-06 | 17/30 sealed READMEs contain forbidden edition wording; doc 13 also finds 17 | RUN+READ |
| F-07 | Four review agents compared all 30 sealed candidates with the live upstream README: **0 pushable**; 21 RESEAL_REQUIRED, 9 DO_NOT_PUSH; every live README is richer. Two spot-checks by me held (Cells-Java dangling "Run the test suite:"; Slides-Java `26.8.0` not on Maven Central, only 26.7.0). **BarCode-Py and Cells-Py were re-sealed by #305 after the reviewed bundles**: their verdicts must be redone | AGENT, 2 RUN |
| F-08 | 28/30 reviewer verdicts are REJECT demoted to ACCEPT by deterministic fold code (`review_document`, `scope_defect`, `review_checks`); second/third reader differ only by sampling seed (+2/+3), same prompt and route; `require_sealing_model` restricts sealing to qwen3-next. Re-confirmed on origin/main: `review_document` ~1829, `verdict = returned if findings or returned == ACCEPT else ACCEPT` ~1946, `second_reader` ~393 | READ (origin/main, via code re-baseline agent; I did not run it) |
| F-09 | `propose` already refuses `source_moved`; it does not check review honesty, no-op proof, or the ratified score ("`wave-readiness` staleness is informational") | READ |
| F-10 | Facts map is compared whole; link/product-page HTTP status is inside hashed evidence | AGENT |
| F-11 | No fact kind for `docs/*.md`, CHANGELOG/releases, CONTRIBUTING/SECURITY (now partially: #316 records repository files a README names), CLI entry points, framework matrices; `capability` has no producer; no fact carries the live published version | AGENT+READ |
| F-12 | `raw_calls.json` in 5/30 bundles (6 retain raw reads per doc 13) | RUN |
| F-13 | Commit-back exists but is **un-hosted-proven**: `candidates-publish.yml` + `publish-candidates` job (#304), App-installation-token fix (#311); gated by `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED`; G7-W14 stays open until a real hosted run is observed | READ |
| F-14 | Issue path: harvest + `issue-readiness` landed (#314): 15 CONFIRMED handoffs, 2 NOT_A_DEFECT; none filed upstream; no approval records; redetector is PyPI-only (registered gap `issues.redetect_only_pypi_and_unparseable`); only BC-02 is auto-drafted; issue filing needs registry mode `full`, which also arms PR eligibility | READ+AGENT |
| F-15 | Replay pilot (Note-Python, fresh seal because upstream moved): 13 min, BC-10 REJECT_FACTUAL. Recon verdict (owner log): median 11 min/repo; ~20% of model calls rejected | RUN+READ |
| F-16 | No live external write has ever been made (a 2026-10-04 "disposable proof" was a dry run); `ops/proposal-authorizations/` does not exist; the sandbox repo `babar-raza/presenter-sandbox` exists, untouched | READ |
| F-17 | App installation: audit green for all 15 orgs (run 37989099994), `aspose-html-foss` flapped; `issues:write` and per-repo reach unproven; owner declined a JWT-based audit step via classifier | READ |
| F-18 | Every presenter PR has an identical title and an uninformative body (recorded follow-up gap) | READ |
| F-19 | `test_sealed_bytes` known-failure pins expire 2026-10-19 (3) and 2026-11-04 (27) | AGENT |
| F-20 | aspose.org skill: no template engine, agent writes prose, ~64 hard gates, prose not byte-reproducible, human approval before push | READ |
| F-21 | Extractor defects: comma-split Python deps; manifest lost under paths containing `build/out/lib/bin`; `src.pkg` import path; dynamic deps as verified-zero; registry presence = ownership; Maven `<parent>` read | AGENT (one RUN) |
| F-22 | Upstream defects: misplaced/missing LICENSE (Cells Cpp/Java/Python, 3D-TS, PSD-Py), 102/119 TeX files unparseable, GIS-.NET 369 build errors and no README, locale-dependent CSV encoding, and more (~35 drafts) | AGENT |
| F-23 | My main checkout was 22 commits behind; `scripts/check_staleness.sh` warns only at 20 and is warn-only | RUN |
| F-24 | Uncommitted `test_independent.py` edit and untracked `seal/` attempts in the main checkout | RUN |

### 1.2 Unknowns resolved on 2026-10-10 (owner asked to resolve them; all read-only)

| Unknown | Resolution | Evidence |
|---|---|---|
| Toolchains | **Present on this machine**; earlier "none found" reports looked only at `PATH`. The project's own resolver (`core/toolchains.py`, registry `D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt`, C: paths re-rooted to D:) reports: javac 21.0.11 (`D:\Program Files\Eclipse Adoptium`), dotnet 10.0.401, go 1.26.4, g++ 16.2.0 (winlibs MinGW), cmake 4.4.2, ninja 1.13.2, cargo 1.98.1, node v24.13.1, tsc and mvn present (Maven 3.9.16 in `D:\tools`). MSVC lives under `D:\Program Files\Microsoft Visual Studio`; clang 19.1.7 is also provisioned. **One gap: `npm` reports absent** (the resolver has no install-root glob for it). Fix without a code change: put `D:\Program Files\nodejs` on the run's subprocess PATH (the resolver keeps PATH first for `npm`). | `toolchain_fingerprint()` output |
| Where to reseal | **On this machine (Windows, Python 3.13)**: it is the environment of record of every existing bundle, so the `environment.*` mismatch (F-04) does not arise, and it has the toolchains hosted ubuntu would have to be provisioned with. Hosted runs remain the proof for Track D, not for Monday. | READ |
| Capacity | 32 logical processors, 63.7 GB RAM, drives C D E G H with ample space (E: 79.7 GB free; `candidates/` is 125 MB). Parallelism is limited by the gateway, not the machine. | RUN |
| Parallel `present` safety | `plans/healing/r1-reseal-operations.md` forbids concurrent `present` runs because of a `state.yaml` counter race. Mitigation here: one isolated worktree per repository (the #305 pattern, `runs/wt/<short>`), only the supervisor edits `state.yaml`, bundles land through wave PRs. | READ |
| Self-hosted runner on D: | `D:\tools\actions-runner-cells-foss` is registered to **a product repository** (`aspose-cells-foss/Aspose.Cells-FOSS-for-Java`), not the control repo, and is not running as a service. Not used by this plan; do not touch. | RUN |
| `test_sealed_bytes` pin expiry (2026-10-19, 11-04) | Resolved by sequencing: the reseal lands before 10-19 and TC-ACC-02 removes the rows (an XPASS fails strict). | AGENT+plan |
| `candidates/` size | 125 MB tracked; per-wave PRs of 6 to 12 bundles stay small. | RUN |

**Still unknown, measured by cards:** gateway limits at parallel load (TC-PRE-01-03); how many reseals pass the review lane (TC-PIL-01, TC-ACC-01); per-organization App `issues:write` (owner action, TC-ISS-06); whether the uncommitted test edit is still wanted after #278 (TC-CON-01-02).

---

## 2. What already exists on origin/main (cards must not rebuild it)

| Capability | Landed in | State | Remaining gap (→ card) |
|---|---|---|---|
| Freeze policy, one cut/one reseal | G7-W22 (#307) | policy registered | cut not yet declared with a commit (→ TC-CUT-01) |
| Profile ratified, score computed live, funnel gates publication-eligible | G7-W20 (#308) | landed | READY_FOR_PROPOSAL not gated on score by design; banner fails C01 in all 30 (owner decision pending) |
| S6 must-carry, UNCLASSIFIED deferral classes, dotted-file names | G7-W15/W18 (#312), G7-W12 (#310, #315), G7-W23 (#316) | landed | unproven on a full reseal; G7-W24 cells/python parity (#317) open |
| Bump-cost report + consumed-scope recheck design | doc 13 (#313) | proposal, awaits owner decisions | implementation (→ TC-CUR-01, owner-gated by G7-W22) |
| Commit-back of hosted seals | G7-W14 (#304, #311) | built, dormant, no hosted proof | hosted run + owner variable (→ TC-RSL-02) |
| Proposal wave mechanics | G6-W03 (#309): `wave-readiness`, `docs/PROPOSAL_WAVE_RUNBOOK.md` | landed | content gate before authorization (→ TC-ACC-01); PR title/body quality (→ TC-REF-04) |
| Issue harvest, `issue-readiness`, approvals tooling | G6-W01 (#314) | landed | redetectors, detectors, mode coupling, credentials, first filing (→ Track B) |
| Unattended workflows | G7-W06/W07 | monitor + sealing scheduled; propose manual | observation period, hosted proofs (→ Track D) |

---

## 3. Requirements (stable IDs)

REQ-GOV-01 one authority, taskcard layer subordinate · REQ-LNT-01 plan structure and transitions machine-checked · REQ-CON-01 no churn/races before the cut · REQ-CUT-01 the cut is a recorded commit · REQ-RSL-01 all 36 entries reach a terminal typed state on the cut code, sealed on the production environment · REQ-RSL-02 hosted seals land in `candidates/` by workflow-authored PR · REQ-ACC-01 **no authorization list is built from a candidate that has not passed independent comparison with the live README** · REQ-WAV-01 push wave follows the runbook; owner approves the exact list · REQ-ISS-01…11 issue system (§10) · REQ-REV-01 reviewer REJECT not demoted without recorded deterministic refutation · REQ-REV-02 independence real or honestly compensated · REQ-DSP-01 disposition truth · REQ-DSP-02 live-README floor · REQ-CLM-01 version/install/publication claims equal manifest or registry facts · REQ-CLM-02 capability claims cite facts · REQ-COV-01 every material clone-information unit has one explicit disposition · REQ-EXT-01 extractor defects fixed · REQ-INV-01 reopen only through consumed facts · REQ-INV-02 volatile web observations do not invalidate · REQ-CUR-01 consumed-scope recheck and currency states (doc 13) · REQ-BND-01 bundle integrity and replay completeness · REQ-CTR-01 optional sections follow verified facts inside the 10-section template · REQ-PRP-01 `propose` refuses unproven content · REQ-VER-01 version literals from one source · REQ-REF-01…09 refresh app (§11).

---

## 4. Authority, storage, identifiers (decisions D-1…D-7)

- **D-1 No competing plan.** `AGENTS.md`: "Never create a competing plan…". The registered items remain the plan; this layer is stored as `plans/reseal-and-refresh/PLAN.md` following the `plans/sprint/` and `plans/healing/` precedent (static plan + append-only `loop-status.jsonl`/`loop-instructions.jsonl`, rules in `docs/SUPERVISION.md` "Channels"). It begins with the sentence in the header above. `AGENTS.md` (200/200 lines) is **not** edited; `docs/EXECUTION_STATE_MACHINE.md` (500/500 per #307) gets at most a pointer **only if** a line can be freed in the same edit (TC-GOV-01 decides; otherwise the pointer lives in each work item's `purpose` text).
- **D-2 One representation.** Cards live once, as fenced YAML blocks in `PLAN.md`. Generated CSV/YAML maps (traceability, DAG, matrices) are derived by the lint tool and carry `authoritative_plan:`, `artifact_role: analysis_or_evidence_only`, `execution_authority: false`.
- **D-3 Status.** Work-item status stays in `project/state.yaml` (existing mechanism; ids must match `^G[0-7]-W[0-9]{2}$`; extra fields are rejected by the schema). Parent/child/micro transitions go to `plans/reseal-and-refresh/loop-status.jsonl` (`card` key, per sprint precedent). A work item is COMPLETE only with a gate-manifest acceptance record (existing test) *and* all mapped parents CLOSED (new lint rule). Statuses printed here are initial.
- **D-4 Identifiers.** `REQ-<DOMAIN>-NN`; parent `TC-<AREA>-NN`; child `TC-<AREA>-NN-CC`; micro `MS-<AREA>-NN-CC-SS` where SS is the 1-based position in the child's `steps` list (derived, never random; reordering = new child). Areas: CON GOV LNT CUT PRE PIL RSL TRI ACC WAV ISS REV DSP CLM COV EXT INV CUR BND CTR PRP VER R2 REF.
- **D-5 Evidence.** `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/{analysis,decisions,taskcards,validation,raw-logs,generated-artifacts,quality,closeout}/` plus `run-record.yaml` (the current gate is `G3_PYTHON_COHORT`; REPOSITORY_LAYOUT gets one line for it in TC-GOV-01).
- **D-6 Register entries.** Reuse existing items wherever one exists (§2). Three NEW entries, each needing a verbatim entry in `docs/RESEARCH_AND_GUIDELINES.md` §27.9 in the same order, a mention in the narrative, and (if `owner` starts `REGISTER:`) `Exit predicate:`/`Depends on:` in `purpose` and the id named in the build plan: **G3-W08** (candidate content gate and coverage: Track C), **G6-W07** (issue-system operations: Track B), **G7-W25** (consumed-scope recheck: Track C, doc 13). All `PENDING`.
- **D-7 Lanes.** Sonnet-only, isolated worktrees from `scripts/new_worktree.sh` (always off a fresh `origin/main`; never the main checkout), one shared-code item at a time except disjoint paths, supervisor serialises merges, no merge without green head commit and a diff scan for removed asserts or new skips, no `--no-verify`. Plan-mode boundary: outbound effects (issues, PRs, variables, secrets, App changes, registry mode flips) always need the owner's approval of the exact list at the time.

---

## 5. Solution options (judgment scores /60 over: root-cause coverage, durability, rerun consistency, safety, testability, maintainability, integration, compatibility, evidence quality, regression risk, operational complexity, fit with the registered plan)

| Problem | A minimal | B structural | C redesign | D hybrid | E validate more | Selected |
|---|---|---|---|---|---|---|
| **P1 Loop (currency)** | count stale-but-passing: 30 | doc-13 consumed-scope recheck + freeze: 50 | candidate bytes are the artifact, never regenerate (aspose.org style): 38 | **B after the owner accepts doc 13; until then the G7-W22 freeze alone** : 51 | freeze only: 36 | **D** |
| **P2 Pushing regressions** (reviews: 0/30 pushable) | tighten demotion list in code: 41 (governed bump, inside freeze) | remove demotions: 36 | human review of all: 34 | **non-code independent review lane now (zero bump) + code gates (REV/DSP/CLM) in one owner-approved second cut after wave 1: 52** | none: 8 | **D** |
| **P3 Completeness (all clone info)** | prompt tweaks: 25 | new fact kinds + dispositions: 47 | aspose.org agent-authored: 40 | **coverage inventory (read-only, now) then fact kinds in the second cut: 51** | advisory: 22 | **D** |
| **P4 Commit-back** | by hand: 34 | existing `candidates-publish.yml`: 48 | direct push: 25 | **prove B hosted; hand PR as fallback: 51** | none: 10 | **D** |
| **P5 Publication authorization** | per-hash records forever: 38 | standing per-repo record: 46 | full autonomy: 22 | **per-hash for the pilot wave, standing record after (owner-signed): 50** | manual: 30 | **D** |
| **P6 Issue pipeline** | manual drafts: 30 | detector + redetector registries: 49 | LLM-found defects: 33 | **B + review-lane drafts as seeds, each re-verified by command: 51** | status quo: 18 | **D** |

Rejected: counting stale candidates after a weak recheck (F-07 shows candidates can be wrong); hand-editing sealed READMEs (forbidden, breaks checksums); resealing per fix; direct push to `main`; widening the freeze exceptions silently.

---

## 6. Machine state (enforced by `tools/plan_lint` + `tests/test_plan_lint.py`, built in TC-LNT-01)

**States.** Parent: PROPOSED READY IN_PROGRESS CHILDREN_IN_PROGRESS INTEGRATION_PENDING VERIFIED SCORED CLOSED REROUTED BLOCKED BLOCKED_EXTERNAL DEFERRED_WITH_REASON. Child: TODO READY IN_PROGRESS IMPLEMENTED VERIFIED SCORED CLOSED REROUTED BLOCKED BLOCKED_EXTERNAL DEFERRED_WITH_REASON. Micro: PENDING READY ACTIVE COMPLETE FAILED BLOCKED SKIPPED_NOT_APPLICABLE.

**Legal transitions.** Parent: PROPOSED→READY→IN_PROGRESS→CHILDREN_IN_PROGRESS→INTEGRATION_PENDING→VERIFIED→SCORED→CLOSED; SCORED→REROUTED→IN_PROGRESS; non-closed→BLOCKED|BLOCKED_EXTERNAL|DEFERRED_WITH_REASON; BLOCKED→READY. Child: TODO→READY→IN_PROGRESS→IMPLEMENTED→VERIFIED→SCORED→CLOSED; SCORED→REROUTED→IN_PROGRESS; same blocked/deferred. Micro: PENDING→READY→ACTIVE→COMPLETE|FAILED|BLOCKED; FAILED→READY; BLOCKED→READY; PENDING→SKIPPED_NOT_APPLICABLE (reason required).

**Illegal (lint fails):** TODO/READY/IMPLEMENTED→CLOSED; child CLOSED with a mandatory micro not COMPLETE/skipped-with-reason; parent CLOSED with a mandatory child not CLOSED; REROUTED→CLOSED without a new IN_PROGRESS cycle; BLOCKED_EXTERNAL→CLOSED without unblock evidence; SKIPPED without reason; CLOSED with any mandatory score below 4/5; COMPLETE/CLOSED whose evidence path is missing, empty or unhashed; a work item COMPLETE while a mapped parent is not CLOSED.

**Ledger line (`loop-status.jsonl`):** `{"ts","card","from","to","actor","evidence":[{"path","sha256"}],"scores":{…},"commit"}`; current state = fold. **Static lint:** unique stable IDs · every REQ has ≥1 parent · every parent has ≥1 REQ and ≥1 child · every child ≥1 micro with op/target/done-when · DAG acyclic · parallel cards share no write path · allowed∩forbidden=∅ · every INVESTIGATION child names the cards it will produce · every card has rollback/stop/reroute (defaults in §12 apply when omitted) · no card writes outside its parent's allowed set · a card touching a governed path declares `governed: true` and names its G7-W22 ground (safety/factual-accuracy, or owner approval record), else lint fails.

**Scoring.** Child: requirement correctness, implementation correctness, scope discipline, validation strength, evidence completeness, regression safety, maintainability, production readiness. Parent: root-cause coverage, child completeness, integration completeness, dependency correctness, preserved behavior, evidence completeness, rerun consistency, production readiness. All mandatory dimensions ≥4/5, scored by a **non-author**, stored in `quality/<card>.yaml`. Below 4 → REROUTED, weakest dimension recorded, smallest new child created, validation repeated.

---

## 7. Tracks, order, file ownership

Today is Saturday; Monday 2026-10-12 is the owner's target for "live system proven once". Honest sequencing:

**Owner constraints received 2026-10-10 (plan review): (1)** the first wave must include as many candidates as possible, to prove the system handles a large part of the portfolio without major changes: so wave 1 attempts all 36 and there is no cap of 20. **(2)** A second planned reseal is accepted. **(3)** Do not miss Monday 2026-10-12; Tuesday 2026-10-13 is the latest extension. **(4)** Coverage extension goes into the first cut only if it fits those dates. **(5)** Reuse the toolchains on this machine. **(6)** Placement of this layer: supervisor's call.

**Time-boxed schedule (estimates; I will report slippage rather than hide it):**

| When | Work | Exit |
|---|---|---|
| Sat 10-10 | TC-CON-01, TC-GOV-01, TC-PRE-01 (local toolchains, gateway probe), TC-COV-01 (measurement), start the cut-1 slice lanes on disjoint paths, Track B starts | main synced; toolchains and parallelism verified; coverage gaps ranked |
| Sun 10-11 | Land the cut-1 slice serially if ready; TC-CUT-02 pilot on the slice branch; decide cut | **Go/no-go Sun 22:00**: slice in, or cut = current origin/main with the slice moved to cut 2 |
| Mon 10-12 | TC-CUT-01 recorded; TC-RSL-03 reseal of all 36 in parallel worktrees on this machine; TC-TRI-01; TC-ACC-01 starts per candidate as bundles land | boards for 36; operator wave PRs merged |
| Tue 10-13 (latest) | TC-ACC-01 complete; TC-WAV-01 list; owner authorization of the list; canary then wave if the owner lifts the pause; issues filing per Track B approvals | authorizable list and shortfall reported |

- **Track A, containment and control (now):** TC-CON-01, TC-GOV-01, TC-LNT-01.
- **Track B, issue system (parallel, unaffected by the freeze: no governed-version file is touched):** TC-ISS-01…11. Shipping-first: this reaches real value earliest.
- **Track C-0, the cut and the reseal, run locally on this machine:** TC-PRE-01 → TC-PIL-01 (pilot of three, baseline and slice branch) → TC-CUT-02 (Sunday go/no-go on the time-boxed cut-1 slice) → TC-CUT-01 (declare the cut) → TC-RSL-03 (all 36, parallel worktrees, using the local wave runner TC-RSL-01) → TC-TRI-01 ∥ TC-ACC-01 → TC-WAV-01 → TC-ACC-02. TC-RSL-02 (hosted commit-back proof) runs beside this, off the critical path. Includes the **non-code independent review lane (TC-ACC-01)**, the compensating control for F-07/F-08.
- **Cut-1 slice (time-boxed, governed, `cut: 1-if-ready`):** TC-REV-01 (REJECT stands, so the repair loop can fix findings instead of shipping them), TC-CLM-01 (published-version fact and BC-14), and a thin TC-COV-02 limited to fact kinds that existing template sections already render; each declares its G7-W22 ground (factual accuracy: unsupported public claims in sealed READMEs) and rests on the owner's 2026-10-10 plan-review answers (TC-R2-00). TC-VER-01 bumps the affected constants once. Anything not green by Sunday 22:00 moves to cut 2; the cut is then current `origin/main`.
- **Track C-1, read-only analysis that may start now:** TC-COV-01 (coverage inventory of clone information per repository). No `src/` change.
- **Track C-2, second cut (accepted by the owner; governed changes land only after wave 1's reseal so the reseal runs on one fixed code):** TC-DSP-01/02, TC-COV-02 (remaining kinds)/03, TC-EXT-01, TC-INV-01/02, TC-CUR-01, TC-BND-01, TC-CTR-01, TC-PRP-01, TC-VER-02, plus whatever of the cut-1 slice did not make it; then TC-R2-01 (declare the second cut) and TC-R2-02 (second portfolio reseal, re-using the Track C-0 cards). Development may overlap wave 1 on branches; landing may not.
- **Track D, refresh app (after Monday; staged):** TC-REF-01…09.

**Path ownership (lint-checked).** L-gov: `docs/`, `plans/reseal-and-refresh/`, `project/state.yaml`, `tools/plan_lint/`, `tests/test_plan_lint.py`, `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/`. L-seal: `candidates/`, `runs/` (gitignored). L-hosted: `.github/workflows/`, `components/monitor/`, `components/propose/`, `components/candidates_publish/`, `core/sealing_plan.py`. L-issues: `components/issues/`, `evidence/upstream-defects/`, `ops/issue_approvals/` (records only after owner approval). L-review: `components/readme/review/`. L-disp: `components/readme/reconciliation/`, `components/readme/validation/`. L-extract: `components/readme/extractors/`, `components/readme/evidence/facts/`, `core/facts.py` (FactKind only). L-core: `core/` (rest), `components/readme/bundle/`, `cli.py`. L-compose: `components/readme/composition/` (serialised after L-disp and L-extract). Verifier: read-only, writes only `quality/` and `analysis/`. Hot files, one writer at a time: `validation/registry.py`, `reconciliation/dispositions.py`, version-pin tests (TC-VER-01 only), `project/state.yaml` (L-gov only), `docs/RESEARCH_AND_GUIDELINES.md` §27.9 (L-gov only).

**Condensed deep analysis (20-question protocol, per track).**

| Track | Objective / value | Root cause addressed | Inputs → outputs | Main failure modes | Scope-drift risk | Rollback |
|---|---|---|---|---|---|---|
| A | one authority, checkable plan | F-23, F-24, F-03 | this file → registered items, lint | lint grows into governance weight (the project's known failure) | rules not tied to an incident | revert PR; prose remains valid |
| B | upstream defects reported accurately | F-14, F-17, F-22 | verified defects → approved, filed, tracked issues | false positive; duplicate; token leak; arming PR eligibility via mode flip | filing without approval | close "not planned" + comment; revoke records |
| C-0 | 36 terminal-typed, nothing worse than live pushed | F-02, F-07, F-13 | cut code, hosted runners → bundles in PRs, review verdicts | gateway load, toolchains, variance, regressions | chasing one product | revert wave PR restores prior bundles |
| C-1/C-2 | honest, complete candidates; no reseal storms after | F-08–F-11, F-21 | reviews, doc 13 → gates, facts, recheck | new gates reject many reseals (honest) | per-product patches | revert PR; checks versioned |
| D | READMEs stay fresh autonomously | F-09, F-13, F-18 | upstream change → candidate → PR | PR spam, overwriting maintainer edits, outage burns budget | enabling writes early | revoke standing record; mode back to `dry_run` |

---

## 8. Taskcards, Track A (containment, control layer) and Track C-0 (the cut and the reseal)

**Card format.** Each parent is one YAML block. `steps` are `"op | target | done-when"` triples (ops: inspect, create, edit, run, validate, record, decide-owner, package); the micro-step ID is derived from position (D-4). **Defaults for every card unless it says otherwise:** *rollback* = revert the PR / restore the prior bundles / re-point the variable; *stop* = red CI on the head commit, a write outside `paths.write`, any outbound effect lacking the owner's approval of the exact list, or two equivalent failed attempts or 15 minutes without narrowing the cause (AGENTS.md rule: diagnose, change the mechanism); *reroute* = any mandatory score below 4/5; *evidence* lands under `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/` with the card id in its header. `status` is the initial state (PROPOSED parents, TODO children, PENDING micro-steps).

```yaml
- id: TC-CON-01
  title: Containment and synchronisation before anything else
  reqs: [REQ-CON-01]
  item: G7-W22
  lane: supervisor
  depends: []
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: main checkout equals origin/main; uncommitted work accounted for; sealing quiet; baseline evidence frozen
  accept: ["git status clean on main", "no scheduled sealing run starts before TC-CUT-01 closes", "baseline evidence hashed"]
  children:
    - id: TC-CON-01-01
      title: Synchronise and prove the base (F-23)
      steps:
        - "inspect | scripts/sync_main.sh header and scripts/check_staleness.sh | procedure understood; no destructive command involved"
        - "run | git fetch origin; git rev-list --count HEAD..origin/main | behind-count recorded"
        - "run | scripts/sync_main.sh (or fast-forward by the documented route) | main checkout HEAD == origin/main sha, recorded"
    - id: TC-CON-01-02
      title: Account for uncommitted work (F-24)
      steps:
        - "inspect | git diff tests/components/readme/review/test_independent.py versus the origin/main copy (PR #278 landed typed trigger records) | verdict recorded: obsolete / still needed"
        - "inspect | seal/attempt1-transaction, attempt2-transaction, attempt3-transaction | contents, size, owner session guess recorded (Font-Python bundle?)"
        - "edit | if still needed: commit the test edit on branch park/test-independent-1010 via scripts/new_worktree.sh (no push); else record discard-candidate | git status shows neither file untracked/modified on main"
        - "decide-owner | confirm seal/ may be moved outside the repository or removed | owner answer recorded"
    - id: TC-CON-01-03
      title: Quiet the schedule and hold open PRs (owner action)
      steps:
        - "inspect | gh variable list; gh run list --workflow sealing-scheduled.yml --limit 3 | pause variable state and any in-progress run recorded"
        - "decide-owner | set REPOSITORY_PRESENTER_SEALING_PAUSED=1 until TC-CUT-01 closes | variable confirmed by gh variable list"
        - "decide-owner | hold PRs #317, #233, #214 (label hold) pending the cut decision | labels visible"
    - id: TC-CON-01-04
      title: Freeze the evidence baseline
      steps:
        - "create | analysis/ copies of survey-1..6 and review-A..D reports, runs/monitor/drift.json, status and status --stale output | each file starts with authoritative_plan / artifact_role / execution_authority:false header"
        - "record | sha256 of every file in analysis/MANIFEST.csv | manifest hash verified by re-reading"
        - "record | note that BarCode-Python and Cells-Python reviews predate PR #305 and must be redone (TC-ACC-01-02) | note present in the manifest"

- id: TC-GOV-01
  title: Register this layer under the existing items; one authority
  reqs: [REQ-GOV-01]
  item: G7-W21
  lane: L-gov
  depends: [TC-CON-01]
  governed: false
  paths: {write: [plans/reseal-and-refresh/, project/state.yaml, docs/RESEARCH_AND_GUIDELINES.md, docs/DECISION_LOG.md, docs/REPOSITORY_LAYOUT.md, docs/EXECUTION_STATE_MACHINE.md]}
  outcome: PLAN.md placed with its subordinate statement; three new PENDING register entries; governance tests green
  accept: ["tests/test_queue_agreement.py, test_register_integrity.py, test_governance_consistency.py, test_schemas.py pass", "AGENTS.md unchanged at 200 lines", "ESM still <=500 lines, <=8 gates"]
  children:
    - id: TC-GOV-01-01
      title: Decide how the pointer is carried without breaking the caps
      steps:
        - "inspect | wc -l docs/EXECUTION_STATE_MACHINE.md (500) and AGENTS.md (200) | exact headroom recorded (none)"
        - "decide-owner | pointer lives in the purpose text of G7-W21/W22/G6-W01/G7-W14 (no ESM line) unless a line can be freed in the same edit | decision recorded in DECISION_LOG entry (TC-GOV-01-06)"
    - id: TC-GOV-01-02
      title: Place the layer
      steps:
        - "create | plans/reseal-and-refresh/PLAN.md from this file with the header authority statement as its first block | file exists; lint (once built) passes"
        - "create | plans/reseal-and-refresh/loop-status.jsonl and loop-instructions.jsonl (empty, single-writer rules per docs/SUPERVISION.md Channels) | files exist"
    - id: TC-GOV-01-03
      title: Register G3-W08, G6-W07, G7-W25
      steps:
        - "inspect | docs/RESEARCH_AND_GUIDELINES.md section 27.9 YAML block and its narrative; project/state.yaml next_ready_items order | insertion points identified"
        - "edit | add three entries to state.yaml (status PENDING, owner starting REGISTER:, purpose with Depends on: and Exit predicate:) | schema validates"
        - "edit | add the same three entries verbatim, same relative order, to section 27.9 and name them in its narrative | test_queue_agreement and test_governance_consistency pass"
    - id: TC-GOV-01-04
      title: Cross-reference existing items
      steps:
        - "edit | append 'Taskcards: plans/reseal-and-refresh/PLAN.md' to purposes of G7-W21, G7-W22, G6-W01, G7-W14 in BOTH state.yaml and section 27.9 (byte-identical) | tests pass"
    - id: TC-GOV-01-05
      title: Layout and decision record
      steps:
        - "edit | REPOSITORY_LAYOUT.md section 2: document plans/<mission>/ (static plan + channels) and evidence/build/<gate>/<mission>/ | layout tests pass"
        - "edit | DECISION_LOG.md: dated entry recording owner delegation of decisions D-OWN-1..6 (section 14) and this layer's subordinate status | entry appended"
        - "run | scripts/ci_check.sh in the worktree; open PR; supervisor verifies head green and merges | merged"

- id: TC-LNT-01
  title: Plan lint, ledger fold, derived maps
  reqs: [REQ-LNT-01]
  item: G7-W21
  lane: L-gov
  depends: [TC-GOV-01-02]
  governed: false
  paths: {write: [tools/plan_lint/, tests/test_plan_lint.py, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/generated-artifacts/]}
  outcome: every structural promise of section 6 is a failing test when broken
  accept: ["lint passes on PLAN.md", "each rule has a failing fixture", "mutating an ID, a link, a transition or an evidence hash makes lint fail"]
  children:
    - id: TC-LNT-01-01
      title: Parse cards
      steps:
        - "inspect | src/repository_presenter/core/cursor.py loader and tests/support.py | reuse notes (tools/ is never imported by src/; tests may import tools/)"
        - "create | tools/plan_lint/cards.py extracting fenced yaml blocks with PyYAML (already a dependency) | fixture parses to parent/child/micro tree"
    - id: TC-LNT-01-02
      title: Static rules
      steps:
        - "create | rules: unique IDs, REQ coverage both ways, child/micro presence, DAG acyclic, disjoint parallel writes, allowed vs forbidden disjoint, governed:true requires ground | one failing fixture per rule"
        - "validate | pytest tests/test_plan_lint.py -q | all rules red on bad fixtures, green on PLAN.md"
    - id: TC-LNT-01-03
      title: Ledger fold and evidence hashes
      steps:
        - "create | fold loop-status.jsonl; legal-transition table of section 6; evidence path existence, non-empty, sha256 | illegal sequences from section 6 each rejected"
        - "create | check state.yaml work-item status vs mapped parents (COMPLETE only when all CLOSED) | mismatch fixture fails"
    - id: TC-LNT-01-04
      title: Derived maps
      steps:
        - "create | generator for requirement->parent->child->micro CSV, DAG yaml, dependency matrix, file-lock map with non-authority headers | files regenerate byte-identically twice (idempotency)"

- id: TC-CUT-01
  title: Declare the cut (G7-W22 clause 1) as a recorded commit
  reqs: [REQ-CUT-01]
  item: G7-W22
  lane: supervisor
  depends: [TC-CUT-02]
  governed: false
  paths: {write: [project/state.yaml, docs/DECISION_LOG.md, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/]}
  outcome: one commit named as the cut; counts before the reseal recorded
  accept: ["cut sha recorded in G7-W22 text and DECISION_LOG", "no governed constant differs between the cut and the reseal run's code"]
  children:
    - id: TC-CUT-01-01
      title: Verify the in-flight batch landed
      steps:
        - "inspect | G7-W20 (#308), G7-W15/W18 (#312), G7-W12 (#310, #315), G7-W23 (#316), candidates-publish fix (#311), G7-W24 (#317 open) | table: landed / open with PR numbers"
    - id: TC-CUT-01-02
      title: Decide G7-W24 (#317) relative to the cut
      steps:
        - "inspect | gh pr diff 317 for governed-constant edits (NORMALISATION/RENDERER/REVIEWER/VALIDATOR/per-check/INHERITED_UNITS) | list of constants it moves, or none"
        - "decide-owner | land #317 before the cut, or exclude until after wave 1 (supervisor recommends: land only if it fixes the Cells-Python parity defect the reviews found and is green) | decision recorded"
    - id: TC-CUT-01-03
      title: Record the cut and the baseline
      steps:
        - "run | repository-presenter status --stale and wave-readiness --offline at the cut sha, in a fresh worktree | counts recorded (baseline: 2 current, 29 READY, 19 source-current)"
        - "edit | name the cut sha in G7-W22 purpose (state.yaml and section 27.9) and append a DECISION_LOG entry | tests pass"

- id: TC-PRE-01
  title: Local toolchains, environment of record, gateway headroom (the owner's "reuse this machine's toolchains")
  reqs: [REQ-RSL-01]
  item: G3-W07
  lane: L-seal
  depends: [TC-CON-01]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: a measured table of what this machine can verify per ecosystem and how parallel the reseal can go
  accept: ["every ecosystem has a recorded toolchain verdict from the project's own resolver", "chosen parallelism backed by a gateway probe", "no change to the machine's PATH or profile"]
  children:
    - id: TC-PRE-01-01
      title: Toolchain verdict per ecosystem (resolved; this card re-proves it at the cut)
      steps:
        - "run | python -c toolchain_fingerprint() with RP_TOOLCHAIN_REGISTRY unset (defaults read D:\\tools\\rp-toolchains\\TOOLCHAIN_PATHS.txt) | javac 21.0.11, dotnet 10.0.401, go 1.26.4, g++ 16.2.0, cmake 4.4.2, ninja 1.13.2, cargo 1.98.1, node v24.13.1, tsc, mvn recorded; npm absent noted"
        - "run | the reseal shell gets D:\\Program Files\\nodejs prepended to the SUBPROCESS PATH only | npm resolves via PATH; fingerprint shows npm present"
        - "decide-owner | only if a verifier still reports BLOCKED_TOOLCHAIN for a repository: provision the missing piece under D:\\tools\\rp-toolchains following that file's no-elevation discipline (never a user or system PATH edit) | gap closed or recorded as a typed disposition"
    - id: TC-PRE-01-02
      title: Processability of all 36 without model calls
      steps:
        - "run | repository-presenter present --facts-only --repo <each of 36> from a short-path worktree (runs/wt/<name>) | processability and coverage record per repo; zero provider calls verified in each ledger"
        - "record | the 6 NO_BUNDLE entries separately (3D-TS, GIS-.NET, PDF-TS, PSD-.NET, PSD-Python, TeX-Python) with expected class | table"
    - id: TC-PRE-01-03
      title: Gateway headroom
      steps:
        - "run | repository-presenter preflight at increasing concurrency (1,2,4,6,8) | 429/5xx rates recorded per level"
        - "decide-owner | max parallel `present` runs for the reseal (default: highest level with zero errors, never above 8 without a clean probe) | value recorded"
    - id: TC-PRE-01-04
      title: Environment of record
      steps:
        - "inspect | dependencies.json environment of existing bundles (Windows, Python 3.13.2) | confirmed identical to this machine"
        - "record | decision: reseal here; hosted ubuntu/3.11 is the Track D proof environment | decision in decisions/"

- id: TC-PIL-01
  title: Pilot reseal of three candidates, baseline code versus the cut-1 slice (local)
  reqs: [REQ-RSL-01]
  item: G3-W07
  lane: L-seal
  depends: [TC-PRE-01]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/]}
  outcome: measured wall time, provider calls, review verdicts and review-lane verdicts for Words-Python, Cells-Java and Slides-.NET on origin/main, and again on the slice branch if one exists
  accept: ["comparison table baseline vs slice", "no candidates/ change committed", "each run in its own short-path worktree"]
  children:
    - id: TC-PIL-01-01
      title: Run the three on baseline
      steps:
        - "decide-owner | approve gateway spend for three local `present` runs (cost approval; median 11 min each per owner log) | approval recorded"
        - "run | scripts/new_worktree.sh pilot-<repo> then repository-presenter preflight and present --repo <each> with the toolchain PATH of TC-PRE-01-01 | transaction directories and bundle diffs, not committed"
        - "validate | second `present` invocation in a fresh process (verify-noop-proof) | zero provider calls, or the failure recorded"
    - id: TC-PIL-01-02
      title: Repeat on the slice branch
      steps:
        - "run | the same three on the cut-1 slice branch (skipped if no slice branch exists by Sunday noon) | same records"
    - id: TC-PIL-01-03
      title: Judge
      steps:
        - "run | TC-ACC-01 protocol on each result (verifier lane, non-author) | verdict per candidate and per code version"
        - "record | table: reached READY_FOR_PROPOSAL, review verdict, authorizable by the lane, calls, minutes | table feeds TC-CUT-02"

- id: TC-CUT-02
  title: Sunday 22:00 go/no-go on the cut-1 slice
  reqs: [REQ-CUT-01]
  item: G7-W22
  lane: supervisor
  depends: [TC-PIL-01]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/]}
  outcome: either the slice branch is the cut, or origin/main is the cut and the slice moves to cut 2
  accept: ["decision uses the TC-PIL-01 table, not opinion", "Monday is not missed: no slice that is not green and merged by the deadline"]
  children:
    - id: TC-CUT-02-01
      title: Decide by rule
      steps:
        - "inspect | slice cards TC-REV-01, TC-CLM-01, thin TC-COV-02: merged, CI green on head, mutation tests, constants bumped once (TC-VER-01) | status per card"
        - "record | rule: slice is in only if all merged cards are green AND the pilot shows authorizable-by-lane count on the slice >= baseline (honest rejection that triggers repair is fine, a drop that repair cannot recover is not) | go or no-go with the numbers"
        - "decide-owner | owner may overrule either way; Tuesday 13th is the latest extension | decision recorded"

- id: TC-RSL-01
  title: Local parallel reseal runner (operator tooling, not a governed change)
  reqs: [REQ-RSL-01]
  item: G3-W07
  lane: L-seal
  depends: [TC-PRE-01]
  governed: false
  paths: {write: [tools/reviewer/reseal_wave/, plans/reseal-and-refresh/]}
  outcome: one command starts N isolated `present` runs (one short-path worktree per repository, bounded by the gateway probe), collects bundle diffs and a per-repository result row, and never edits state.yaml
  accept: ["precedent followed: the 2026-10-09 re-seal pass (PR #305, runs/wt/reseal20261009) and plans/healing/r1-reseal-operations.md rules: never force a seal past a genuine review rejection, never hand-edit dispositions or plans, only the supervisor edits state.yaml", "each run's transaction and bundle live only in its own worktree until the supervisor stages them", "a failed or timed-out run leaves no partial bundle in candidates/"]
  children:
    - id: TC-RSL-01-01
      title: Read the precedent
      steps:
        - "inspect | plans/healing/r1-reseal-operations.md and the #305 re-seal transcript in DECISION_LOG (2026-10-09/10) | procedure and known pitfalls listed (state.yaml counter race, shared index, MAX_PATH)"
        - "inspect | scripts/new_worktree.sh refusals (C: drive forbidden, short path under runs/wt) | constraints listed"
    - id: TC-RSL-01-02
      title: Build the runner
      steps:
        - "create | a script that, per repository in a list, creates a worktree at the cut sha, exports PYTHONPATH and the toolchain PATH, runs preflight then present --repo (resumable; logs to the worktree), up to max_parallel at a time | dry run on two repositories prints the plan and starts nothing"
        - "create | result row per repository: exit code, stage reached, validation counts, review verdict, provider calls, minutes, bundle path | CSV in analysis/"
        - "validate | run on Words-Python and Slides-.NET | rows match a manual `present`"

- id: TC-RSL-02
  title: Hosted proof of commit-back (G7-W14 exit predicate); off the critical path
  reqs: [REQ-RSL-02]
  item: G7-W14
  lane: L-hosted
  depends: [TC-PIL-01]
  governed: false
  paths: {write: [project/state.yaml, docs/EXECUTION_STATE_MACHINE.md]}
  outcome: one observed hosted run whose workflow-authored PR updates candidates/<slug>/ for a dry_run entry
  accept: ["run id and PR recorded in the G7-W14 entry", "CI ran and was green on the PR", "second dispatch is a no-op"]
  children:
    - id: TC-RSL-02-01
      title: Prove it once
      steps:
        - "run | gh workflow run present.yml -f repository=<one pilot repository> on origin/main (hosted ubuntu; needs hosted toolchains for that ecosystem, so pick Python) | a hosted sealed-<slug> artifact exists (the local pilot produces none)"
        - "decide-owner | set REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED=1 and confirm the App has contents/pull-requests write on the control repo (the 2026-10-04 token lookup for this repo returned 404) | variable and App state recorded"
        - "run | dispatch candidates-publish.yml with that artifact (do_publish true) | PR opened, authored by the App"
        - "validate | required checks Python 3.11/3.12/3.13 triggered on the PR (GITHUB_TOKEN PRs would not) | checks visible and green"
        - "run | dispatch again with the same artifact | no new commit, PR unchanged"
        - "record | run id and PR number in G7-W14 text (state.yaml and section 27.9) | tests pass"
      negative: "variable unset -> workflow refuses and writes nothing"

- id: TC-RSL-03
  title: Reseal all 36 once, in parallel, on this machine
  reqs: [REQ-RSL-01]
  item: G3-W07
  lane: L-seal
  depends: [TC-CUT-01, TC-RSL-01]
  governed: false
  paths: {write: [candidates/, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/]}
  outcome: every registry entry has a fresh sealed bundle or a typed reason, from one pass on one fixed code
  accept: ["every one of the 36 is attempted in the first pass (the owner's requirement: maximise the first wave)", "no governed constant moved during the pass (worktrees are pinned to the cut sha)", "bundles reach candidates/ only through wave PRs that the supervisor stages and that pass CI on the exact head; the operator-PR pattern of #305 and #259 (hosted commit-back is proven separately in TC-RSL-02)"]
  children:
    - id: TC-RSL-03-01
      title: Order and start
      steps:
        - "record | start order by expected success: source-current and clean first, drifted next, first seals (6 NO_BUNDLE) last; all 36 queued so the gateway stays saturated up to the TC-PRE-01-03 limit | queue table"
        - "run | the TC-RSL-01 runner over the queue | result rows accumulate"
    - id: TC-RSL-03-02
      title: Land bundles as they finish
      steps:
        - "validate | per bundle: sealed-ready exits 0; verify-noop-proof passes (fresh process, zero provider calls) | per-bundle pass/fail"
        - "package | a wave PR per 6 to 12 passing bundles, disjoint candidate paths; supervisor runs scripts/ci_check.sh, verifies the head is green, scans the diff for removed asserts or new skips, merges | merged"
        - "edit | after each merge re-run the tests that read candidates/ (test_sealed_bytes etc.) and queue TC-ACC-02 un-pins | no red head on main"
    - id: TC-RSL-03-03
      title: Failures go to triage, not to code
      steps:
        - "record | every failure with its stage, check id and log excerpt, no fix attempted | rows handed to TC-TRI-01"

- id: TC-TRI-01
  title: Terminal typed state for all 36
  reqs: [REQ-RSL-01]
  item: G5-W08
  lane: verifier
  depends: [TC-RSL-03]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: a board with one terminal row per entry
  accept: ["36 rows", "each is SEALED, BLOCKED_UPSTREAM(handoff id + resume predicate), NON_PROCESSABLE, DEFERRED(class) or FAILED_INTERNAL(diagnosis)", "universal defects are logged in DEFECT_INDEX with evidence and NOT fixed (G7-W22 clause 3) unless a safety/factual ground is recorded"]
  children:
    - id: TC-TRI-01-01
      title: Classify
      steps:
        - "inspect | each failed run's calls/*.rejected-*.json, validation.json, review.json | class: upstream / universal / variance"
        - "run | at most two redraws per variance case, no code change | outcome recorded"
        - "record | upstream cases to TC-ISS-01 with evidence; universal cases to DEFECT_INDEX as unfixed | rows linked"
    - id: TC-TRI-01-02
      title: Close the board
      steps:
        - "validate | board against state.yaml G5-W08 partition (every entry in exactly one bucket) | agreement or discrepancy list"

- id: TC-ACC-01
  title: Independent acceptance review lane (non-code compensating control)
  reqs: [REQ-ACC-01]
  item: G7-W21
  lane: verifier
  depends: [TC-RSL-03]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/quality/]}
  outcome: no candidate reaches an authorization list without a recorded comparison with its live upstream README
  accept: ["protocol file exists and was calibrated on a deliberately broken README", "one record per candidate", "author != reviewer"]
  children:
    - id: TC-ACC-01-01
      title: Write and calibrate the protocol
      steps:
        - "create | decisions/acceptance-protocol.md from the four review briefs: live-README comparison, >=10 claim spot-checks incl. versions against the registry, forbidden wording, 10-section conformance, completeness gaps, upstream defects as text | protocol file"
        - "validate | run the protocol on a copy of a known-good README with one false version and one dropped section | both defects found, else the protocol is rerouted"
    - id: TC-ACC-01-02
      title: Redo the stale reviews
      steps:
        - "run | protocol on the CURRENT bundles of BarCode-Python and Cells-Python (re-sealed by PR #305 after the earlier reviews) | records written"
    - id: TC-ACC-01-03
      title: Review every resealed candidate
      steps:
        - "run | protocol per resealed candidate, <=8 per agent, non-author | quality/acceptance/<slug>.md with verdict AUTHORIZABLE / FIX_REQUIRED / DO_NOT_PROPOSE"
    - id: TC-ACC-01-04
      title: Honest count
      steps:
        - "record | table: authorizable count versus the target of 20, shortfall and reasons | table; no claim beyond it"

- id: TC-WAV-01
  title: Prepare the push wave; stop at the owner's list
  reqs: [REQ-WAV-01]
  item: G6-W03
  lane: supervisor
  depends: [TC-ACC-01]
  governed: false
  paths: {write: [evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/]}
  outcome: a drafted owner authorization naming exact repositories and hashes; no write performed
  accept: ["nothing written to any external repository", "list is the intersection of wave-readiness READY and ACCEPTANCE AUTHORIZABLE", "no arbitrary cap: the owner wants the first wave as large as the gates allow; GitHub limits (runbook: 80 content-generating requests/min, 500/hour; 3 content requests per target) fit all 36 in about 108 requests, paced 30 s apart", "every candidate not authorizable carries a one-line reason and a minor-or-major flag"]
  children:
    - id: TC-WAV-01-01
      title: Intersect the gates
      steps:
        - "run | repository-presenter wave-readiness at the cut head, immediately after the last wave PR merges (sealed revision must equal the live head: 10 of 29 had moved on 2026-10-10 and are refused with source_moved) | table (registry mode, hash, source current, README present, record state)"
        - "record | intersection with TC-ACC-01 AUTHORIZABLE | list L, with its size and the shortfall to 36"
        - "record | for each non-authorizable candidate: is the cause a minor change (a redraw, a data entry, an upstream fix) or a major one (code gate, new fact kind)? | the owner's test of whether the system handles a large portion 'without major changes'"
    - id: TC-WAV-01-02
      title: Draft the authorization
      steps:
        - "create | text per docs/PROPOSAL_WAVE_RUNBOOK.md section 7 for list L, canary first (runbook section 5; first target named by the owner; sandbox babar-raza/presenter-sandbox exists) | draft in decisions/, nothing merged"
        - "decide-owner | the owner either signs (a DECISION_LOG authorization plus a merged ops/proposal-authorizations records PR plus registry mode flips under G6-W06/OWNER-20) or lifts/keeps the pause | BLOCKED_EXTERNAL until recorded; the pause of 2026-10-10 stands until 20 are re-sealed"
    - id: TC-WAV-01-03
      title: Execution is a separate, later card
      steps:
        - "record | on approval a new card TC-WAV-02 is created (runbook sections 3 to 6) | not part of this plan until approved"

- id: TC-ACC-02
  title: Gate bookkeeping after the reseal
  reqs: [REQ-RSL-01]
  item: G3-W07
  lane: L-gov
  depends: [TC-TRI-01, TC-ACC-01]
  governed: false
  paths: {write: [tests/test_sealed_bytes.py, tests/test_debt_ledger.py, tests/test_bundle_audits.py, project/state.yaml, evidence/build/G3_PYTHON_COHORT/]}
  outcome: pins removed for resealed bundles; cursor counts true; gate record written if its predicate is met
  accept: ["scripts/ci_check.sh green", "XPASS rows removed (they fail strict)", "status counts before/after recorded"]
  children:
    - id: TC-ACC-02-01
      title: Un-pin
      steps:
        - "run | pytest tests/test_sealed_bytes.py tests/test_debt_ledger.py tests/test_bundle_audits.py -q on the reseal branch | XPASS and mismatch list"
        - "edit | remove KNOWN_BLOCKED_STALE / VALID_UPDATE_AVAILABLE_REFS / audit ledger rows that now pass; update canary revision pins if the canary revision moved | tests green"
    - id: TC-ACC-02-02
      title: Cursor and manifest
      steps:
        - "edit | progress.current_candidates, G7-W22 exit predicate statuses; gate manifest only if every exit predicate truly passes | tests/test_cursor tests green"
```

---

## 9. Taskcards, Track B (the issue system: operational first, then operated)

**Baseline on origin/main (read, not assumed):** `components/issues/{model,draft,ledger,redetect,approval,close_approval,file,readiness}.py`; CLI `redetect-upstream-defects`, `issue-targets`, `file-upstream-defects`, `issue-readiness`; `issues-scheduled.yml` (cron `41 3 * * *`; jobs targets, analyse, file-and-close). 18 handoffs under `evidence/upstream-defects/`: 15 CONFIRMED live (2026-10-09), 2 NOT_A_DEFECT (3D-TS and PDF-TS npm handoffs), 1 synthetic FILED (issue #189 on the control repo). Only 3 of the 15 pass the automatic recheck (`replay_gap` for the rest: PyPI-only redetector, BC-02 evidence without exactly one PyPI URL, NOT_PROCESSABLE naming no `.py` file). Only BC-02 is auto-drafted. `ops/issue_approvals/` holds a README only. Registry `full` entries are 3D-Java and Cells-Java, neither with a handoff, so **no confirmed issue can be filed today**. The path to a filed issue (read from the code): owner flips the target to `full` (G6-W06 + OWNER-20) → `issue-readiness --emit-approvals` → a person merges `ops/issue_approvals/<handoff-id>.json` → variable `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED=1` → `issues-scheduled.yml` → `file_handoff` (WritePermit `issue_filing`, token provenance, evidence-digest match, duplicate search by fingerprint marker, recheck immediately before the write). Token: `GH_ISSUES_WRITE_TOKEN` (installation token, issues:write on that one repository).

```yaml
- id: TC-ISS-01
  title: One verified defect inventory (harvest + review drafts, deduplicated, re-verified by command)
  reqs: [REQ-ISS-01]
  item: G6-W01
  lane: L-issues
  depends: [TC-CON-01]
  governed: false
  paths: {write: [evidence/upstream-defects/, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: each defect is a handoff in the schema's shape, reproducible by a recorded command at the live head
  accept: ["delta table old vs new", "every handoff carries reproduction command output", "unreproducible drafts dropped, not softened"]
  children:
    - id: TC-ISS-01-01
      title: Read what exists
      steps:
        - "inspect | evidence/upstream-defects/*/ and reverification.json (15 CONFIRMED, 2 NOT_A_DEFECT) | classification table"
        - "inspect | schemas/upstream-defect-handoff.schema.json and components/issues/model.py (triggering_check limited to BC ids and NOT_PROCESSABLE; causal_stage EXTRACTING) | list of defect kinds the model can and cannot represent"
    - id: TC-ISS-01-02
      title: Merge the review drafts
      steps:
        - "inspect | the four review reports (review-A..D) issue drafts (~35: misplaced LICENSE Cells-Cpp/Java/Python, 3D-TS no LICENSE and wrong main, GIS-.NET 369 build errors, TeX 102/119 unparseable, PSD placeholders, Cells-Py CSV encoding and wheel packaging, Words-Py pdfplumber, Cells-Rust no tests, Cells-Java stale Javadoc, Slides-Java 26.7.0 only) | candidate list"
        - "record | dedupe against the 15 CONFIRMED handoffs | delta: new / covered / weaker-than-existing"
    - id: TC-ISS-01-03
      title: Re-verify by command
      steps:
        - "run | for each new candidate, shallow clone at the live head and run the minimal reproducing command (license path check, build, ast.parse, package registry probe) | raw-logs/<repo>-<class>.txt with command and exit code"
        - "record | verdict REPRODUCED / NOT_REPRODUCED per candidate; drop NOT_REPRODUCED | table"
    - id: TC-ISS-01-04
      title: Rewrite weak handoffs
      steps:
        - "edit | strengthen the 3D-TS, PDF-TS (jargon-only) and TeX (understated: 102/119 files) bodies via draft tooling, never hand-edited JSON digests | digests recomputed; old approvals none"

- id: TC-ISS-02
  title: Redetectors for every ecosystem (retire the PyPI-only gap)
  reqs: [REQ-ISS-02]
  item: G6-W07
  lane: L-issues
  depends: [TC-ISS-01-01]
  governed: false
  paths: {write: [src/repository_presenter/components/issues/redetect.py, tests/components/issues/]}
  outcome: issue-readiness replay_gap count falls to the genuinely unreplayable
  accept: ["each ecosystem observer has a resolved-vs-persists pair of tests", "12 of the 15 CONFIRMED handoffs no longer report replay_gap for lack of a redetector (target; measured)", "DEFECT_INDEX issues.redetect_only_pypi_and_unparseable moves toward Resolved only on a measured replay"]
  children:
    - id: TC-ISS-02-01
      title: Design on existing probes
      steps:
        - "inspect | redetect.py (@register, _REGISTRY_ECOSYSTEM, _pypi_package_names, RedetectionReads) and extractors/surface/registry.py::observe / _vendor publication_probe REGISTRY_TYPES | reuse plan; no new HTTP client"
    - id: TC-ISS-02-02
      title: Observers, one per registry
      steps:
        - "edit | npm observer behind RedetectionReads | test: package present -> resolved; absent -> persists"
        - "edit | NuGet observer | same pair"
        - "edit | Maven Central observer (the check that found Slides-Java 26.8.0 missing) | same pair"
        - "edit | crates.io and Go proxy observers | same pair"
    - id: TC-ISS-02-03
      title: NOT_PROCESSABLE beyond .py
      steps:
        - "edit | generalise the unparseable-source redetect through the language parser registry (tree-sitter pins in core/grammars.py) | TeX fixture re-detected from live head"
    - id: TC-ISS-02-04
      title: Measure
      steps:
        - "run | repository-presenter issue-readiness --json before and after | replay_gap counts recorded in quality/"

- id: TC-ISS-03
  title: Detectors for the defect classes the reviews found (not only BC-02)
  reqs: [REQ-ISS-03]
  item: G6-W07
  lane: L-issues
  depends: [TC-ISS-02]
  governed: false
  paths: {write: [src/repository_presenter/components/issues/, schemas/upstream-defect-handoff.schema.json, tests/components/issues/, docs/DEFECT_INDEX.md]}
  outcome: license, build, unparseable-source, own-example and metadata-placeholder defects become handoffs automatically, with a class registry instead of an if/elif chain
  accept: ["schema change landed through the named item G6-W07 with a DECISION_LOG admission", "each class has a detector, a redetector, a template and a negative control", "present --facts-only on TeX-Python and GIS-.NET produces their handoffs unprompted"]
  children:
    - id: TC-ISS-03-01
      title: Class registry and model extension
      steps:
        - "inspect | draft.py::eligible_for_handoff and the DEFECT_INDEX entry stating draft.py was deliberately not widened in PR #314 | scope of the deliberate limit understood"
        - "decide-owner | admit an additive 'defect_class' field in the handoff schema (owner admission recorded in DECISION_LOG) | admission recorded"
        - "edit | schema + model: defect_class from a registry (LICENSE_MISSING_ROOT, LICENSE_MISMATCH, MANIFEST_INVALID, BUILD_FAILS, SOURCE_UNPARSEABLE, EXAMPLE_FAILS, INSTALL_FAILS, PACKAGE_UNPUBLISHED, LINK_BROKEN, PLACEHOLDER_METADATA, README_MISSING) | tests/test_schemas.py green"
    - id: TC-ISS-03-02
      title: Detectors
      steps:
        - "create | LICENSE_*: from license facts and the file inventory (License/ directory case) | fixture from Cells-Cpp/Java/Python"
        - "create | SOURCE_UNPARSEABLE and README_MISSING producing the typed NON_PROCESSABLE outcome the cursor says has no producer for unparseable source | TeX and GIS fixtures"
        - "create | BUILD_FAILS / EXAMPLE_FAILS from build and example receipts when the failure is in upstream code, not the README | GIS-.NET and Cells-Cpp fixtures"
        - "create | PLACEHOLDER_METADATA from manifest facts (yourorg URLs, author 'SID') | PSD-.NET fixture"
    - id: TC-ISS-03-03
      title: Wire into present
      steps:
        - "edit | record_handoff_if_new called from the extraction/validation path for these classes, deterministic only | a facts-only run writes handoffs; zero provider calls"

- id: TC-ISS-04
  title: Issue body quality gate and templates
  reqs: [REQ-ISS-04]
  item: G6-W07
  lane: L-issues
  depends: [TC-ISS-01-01]
  governed: false
  paths: {write: [src/repository_presenter/components/issues/draft.py, tests/components/issues/]}
  outcome: no issue can be approved whose body fails deterministic checks
  accept: ["checks listed below are tests", "bodies read as maintainer-actionable"]
  children:
    - id: TC-ISS-04-01
      title: Gate
      steps:
        - "create | checks: one defect per issue; exact reproduction command and expected vs actual; file path (and line when known); no secrets and no internal artifact names (upstream-issues.md, content-dispositions.json, reports/…); no bridge/edition wording; title format '<product>: <defect>' | each check has a failing fixture"
        - "run | the gate over the 15 CONFIRMED + new handoffs | pass/fail list; failures rewritten in TC-ISS-01-04"

- id: TC-ISS-05
  title: Decouple issue filing from PR mode (flipping to full must not arm PRs)
  reqs: [REQ-ISS-05]
  item: G6-W07
  lane: L-core
  depends: []
  governed: false
  paths: {write: [src/repository_presenter/core/registry/, src/repository_presenter/components/issues/file.py, schemas/, data/registry.json (not before owner approval), docs/PROPOSAL_WAVE_RUNBOOK.md, .github/workflows/issues-scheduled.yml, tests/core/registry/]}
  outcome: an entry can be issue-eligible while PR-ineligible
  accept: ["negative control: issues_mode=file with mode=dry_run files issues but propose is refused", "the .yaml vs .json approval-record wording mismatch in issues-scheduled.yml's header is corrected"]
  children:
    - id: TC-ISS-05-01
      title: Choose
      steps:
        - "inspect | core/registry/write_gate.py (effects readme_proposal, metadata_write, issue_filing, issue_close all map to mode full) and the registry model/schema | exact coupling points"
        - "decide-owner | Option 1: add issues_mode off|dry_run|file with back-compat default derived from mode (schema change, named item G6-W07, owner admission). Option 2 (fallback, no schema change): flip issue targets to full while REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED stays unset and no ops/proposal-authorizations record names them (PRs then impossible) | choice recorded; supervisor default: Option 1"
    - id: TC-ISS-05-02
      title: Implement Option 1
      steps:
        - "edit | model + loader + write_gate so issue effects read issues_mode; PR and metadata effects read mode | focused tests, including the negative control"
        - "edit | runbook section 8 and issues-scheduled gating text | docs match code"
    - id: TC-ISS-05-03
      title: Fallback safeguard if Option 2
      steps:
        - "validate | assert (test or pre-check) that no authorization record names the flipped repositories and the PR variable is unset before each filing run | check recorded in the dispatch record"

- id: TC-ISS-06
  title: Credentials and App permissions (OWNER-04) for issue filing
  reqs: [REQ-ISS-06]
  item: G6-W07
  lane: L-hosted
  depends: []
  governed: false
  paths: {write: [.github/workflows/audit-app-installations.yml, docs/CREDENTIAL_ROTATION_RUNBOOK.md, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: issues:write is proven for each organization that has an approved issue, by a method the owner accepts
  accept: ["no token value appears in any log or artifact", "per-organization permission proof recorded"]
  children:
    - id: TC-ISS-06-01
      title: Choose a read-only permission proof
      steps:
        - "inspect | audit-app-installations.yml (metadata:read, one representative repo per org) and the classifier denial of a JWT-based step recorded in DECISION_LOG 2026-10-10 | limits understood"
        - "decide-owner | accept either (a) reading the permissions map from the installation-token response inside the filing job's preflight, or (b) a JWT-based audit step | method recorded"
    - id: TC-ISS-06-02
      title: Owner installs and verifies
      steps:
        - "decide-owner | per organization: Settings > Installed GitHub Apps > repository-presenter > Configure: repository access covering the issue targets; Issues write, Metadata read (and Contents/Pull requests write only for PR waves); aspose-html-foss flapped (runs 37225172128 vs 37989099994): confirm stable | owner confirmation recorded"
        - "run | audit-app-installations.yml dispatch | all legs green"

- id: TC-ISS-07
  title: The owner's approval list (one reviewed PR)
  reqs: [REQ-ISS-07]
  item: G6-W01
  lane: L-issues
  depends: [TC-ISS-01, TC-ISS-04, TC-ISS-05]
  governed: false
  paths: {write: [ops/issue_approvals/]}
  outcome: approval records exist only for issues the owner read
  accept: ["records carry the owner as approver (bot approvers are refused by the code)", "records bind the evidence digest, so an edited handoff is not covered", "window <=30 days"]
  children:
    - id: TC-ISS-07-01
      title: Present the table
      steps:
        - "create | table: repository, class, title, severity, evidence link, reproduced yes/no, ready (issue-readiness blockers) | owner-readable list"
        - "decide-owner | owner marks the issues to approve and the window | list recorded"
    - id: TC-ISS-07-02
      title: Emit and merge
      steps:
        - "run | repository-presenter issue-readiness --emit-approvals <scratch> --approver <owner login> --handoff-id <id>@sha256:… (all or nothing; refuses unlisted ids, stale digests, unconfirmed handoffs) | records in scratch only"
        - "package | PR adding the records under ops/issue_approvals/; the owner's merge is the approval act | merged"

- id: TC-ISS-08
  title: First live filing, alone, then idempotency
  reqs: [REQ-ISS-08]
  item: G6-W01
  lane: L-hosted
  depends: [TC-ISS-05, TC-ISS-06, TC-ISS-07]
  governed: false
  paths: {write: [evidence/upstream-defects/, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/validation/]}
  outcome: one real upstream issue exists, verified, and a second run creates none
  accept: ["issue body equals the approved digest", "second dispatch creates no duplicate", "token absent from every log", "handoff status FILED with issue_ref"]
  children:
    - id: TC-ISS-08-01
      title: Pre-flight
      steps:
        - "decide-owner | confirm the pause of 2026-10-10 ('skip the real upstream push') covers pull requests only, not approved issues; G7-W21 clause 1 includes the issue logger | answer recorded (D-OWN-3)"
        - "run | repository-presenter issue-readiness --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | zero blockers"
        - "decide-owner | set REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED=1 | variable confirmed"
    - id: TC-ISS-08-02
      title: File, verify, repeat
      steps:
        - "run | dispatch issues-scheduled.yml for that repository only | one issue created; URL recorded"
        - "validate | issue title/body vs approved digest; labels/assignees unchanged by us; token pattern absent in the run log (grep) | verified"
        - "run | dispatch again | no new issue; ledger skip recorded"

- id: TC-ISS-09
  title: Batch filing with reconciliation
  reqs: [REQ-ISS-09]
  item: G6-W01
  lane: L-hosted
  depends: [TC-ISS-08]
  governed: false
  paths: {write: [.github/workflows/issues-scheduled.yml, src/repository_presenter/components/issues/file.py, tests/]}
  outcome: all approved handoffs filed once
  accept: ["per-repository daily cap and pacing", "lost-response reconciliation proven by test (search by fingerprint marker before retry)", "every FILED handoff has its URL"]
  children:
    - id: TC-ISS-09-01
      title: Run the approved list
      steps:
        - "run | issues-scheduled.yml over the approved matrix | filed/skipped/failed table"
        - "validate | a simulated lost response (fake transport) is reconciled, not duplicated | test green"

- id: TC-ISS-10
  title: Lifecycle: redetect, update, close, resume
  reqs: [REQ-ISS-10]
  item: G6-W01
  lane: L-issues
  depends: [TC-ISS-09, TC-ISS-02]
  governed: false
  paths: {write: [src/repository_presenter/components/issues/, src/repository_presenter/core/sealing_plan.py, .github/workflows/issues-scheduled.yml, tests/]}
  outcome: a fixed upstream defect is noticed, closed with an approval, and its blocked candidate becomes eligible to seal
  accept: ["synthetic upstream fix is detected within one scheduled cycle", "close needs ops/issue_close_approvals", "BLOCKED_UPSTREAM resume predicate feeds sealing_plan"]
  children:
    - id: TC-ISS-10-01
      title: Cycle
      steps:
        - "edit | redetect each cycle (issues-scheduled analyse job); evidence change -> comment, never a duplicate issue; RESOLVED_UPSTREAM -> close_approval path | tests with fakes"
        - "edit | sealing_plan selects a BLOCKED_UPSTREAM entry whose redetect says resolved, regardless of drift | test: cooldown respected"

- id: TC-ISS-11
  title: Safeguards and visibility
  reqs: [REQ-ISS-11]
  item: G6-W07
  lane: L-hosted
  depends: [TC-ISS-09]
  governed: false
  paths: {write: [.github/workflows/issues-scheduled.yml, src/repository_presenter/components/issues/, src/repository_presenter/cli.py]}
  outcome: bounded, observable, pausable
  accept: ["pause variable honoured", "max open presenter issues per repository", "alert when a handoff stays PENDING beyond N days", "status shows the issue funnel"]
  children:
    - id: TC-ISS-11-01
      title: Limits and alerts
      steps:
        - "edit | open-issue cap per repository and age alert via health-check annotations | tests"
        - "edit | status gains issue funnel counts (PENDING, APPROVED, FILED, RESOLVED) | status output test"
```

---

## 10. Taskcards, Track C-1 / C-2 (completeness and honest gates; governed changes are owner-gated)

**Why a second track exists.** The compensating review lane (TC-ACC-01) protects upstream repositories during the first wave without changing a governed version. But F-07/F-08 show the pipeline itself accepts what the lane would reject, so autonomy (Track D) needs the same judgments in code. Under G7-W22 clause 2 a governed-version change after the cut needs a safety/factual-accuracy ground or the owner's approval. Cards marked `governed: true` carry `ground:`; **none may start until the owner records D-OWN-2** (section 14). They land together as one second cut (TC-R2-01) followed by one second reseal (TC-R2-02), so the loop does not restart. Cards marked `owner_gate` change counting or invalidation behavior, which G7-W22 clause 4 reserves until the owner has read doc 13.

```yaml
- id: TC-COV-01
  title: Coverage inventory of clone information (read-only; may start now)
  reqs: [REQ-COV-01]
  item: G3-W08
  lane: verifier
  depends: [TC-CON-01]
  governed: false
  paths: {write: [tools/reviewer/coverage_inventory/, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/]}
  outcome: a per-repository table of what information exists in each clone and where (or whether) the sealed README carries it
  accept: ["36 rows (or typed reason)", "gaps ranked by prevalence across repositories", "no src/ change"]
  children:
    - id: TC-COV-01-01
      title: Define material information
      steps:
        - "create | spec: README units; docs/**/*.md; CHANGELOG/RELEASE notes; CONTRIBUTING/SECURITY/CODE_OF_CONDUCT; CLI entry points (manifest scripts, bin, main); target-framework / platform matrices (csproj, pom, tsconfig, CI matrix); examples/ and tests as usage; LICENSE/NOTICE; build and test commands | spec file with the ecosystem-specific sources named"
    - id: TC-COV-01-02
      title: Measure
      steps:
        - "create | tools/reviewer/coverage_inventory/ script (precedent: tools/reviewer/bump_cost/; read-only, no provider call) listing clone units and matching them against the CURRENT bundle's facts.json and README | runs on one repository"
        - "run | shallow clones of the 36 at their live heads | analysis/coverage-gap-table.csv"
        - "record | top gaps by number of repositories affected; feeds TC-COV-02 scope | ranked list"

- id: TC-REV-01
  title: Review-gate integrity (REJECT is not silently converted to ACCEPT)
  reqs: [REQ-REV-01, REQ-REV-02]
  item: G3-W08
  lane: L-review
  depends: [TC-R2-00]
  cut: "1-if-ready (Sunday 22:00 rule, TC-CUT-02), else 2"
  governed: true
  ground: "factual-accuracy (reviews: unsupported public claims shipped under ACCEPT) plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/review/, tests/components/readme/review/]}
  outcome: a returned REJECT stands unless every demotion carries a recorded deterministic refutation
  accept: ["replaying the 30 sealed review.json files: every candidate the four reviews rejected yields REJECT", "no regression on the 6 bundles that keep raw reads", "REVIEWER_LOGIC_VERSION bumped once, in TC-VER-01"]
  children:
    - id: TC-REV-01-01
      title: Map the fold (investigation)
      steps:
        - "inspect | review_document, scope_defect, review_checks, blocking(), the 'alone' corroboration test and the final verdict line in review/independent/review.py (origin/main: def ~1829, alone ~1930, verdict ~1946) | each demotion path listed with file:line"
        - "inspect | the nine sealed reviews whose REJECT became ACCEPT (Slides-Java, Cells-Java, Words-Py, PDF-Java REJECT_FACTUAL…) | for each, the exact rule that demoted it"
        - "record | decomposition: which demotions are legitimate refutations (renderer-owned text, excluded evidence) and which are not | table; creates the next children"
    - id: TC-REV-01-02
      title: Refutation record
      steps:
        - "edit | each demotion writes refuted_by: {rule, evidence} into review.json (additive) | unit test per rule"
        - "edit | verdict stays REJECT when any factual or severe-presentation finding lacks a recorded refutation | mutation test: remove a rule -> REJECT"
    - id: TC-REV-01-03
      title: Independence, honestly
      steps:
        - "inspect | second_reader / third_reader (seed +2/+3 only), require_sealing_model (qwen3-next), load_manifests (exactly six manifests) | constraints listed"
        - "decide-owner | keep one route and rely on TC-ACC-01 + deterministic refutation (default), or admit a second review route (changes the sealing-model rule) | decision D-OWN-5 recorded"
    - id: TC-REV-01-04
      title: Replay proof
      steps:
        - "validate | replay all 30 sealed review.json and the raw reads of the 6 that retain them under the new logic | results table in validation/ matching expectations"

- id: TC-DSP-01
  title: Disposition truth (redundant needs a covering destination; unsupported needs no supporting fact)
  reqs: [REQ-DSP-01]
  item: G3-W08
  lane: L-disp
  depends: [TC-R2-00, TC-RSL-03]
  cut: "2 (lands after wave 1's reseal)"
  governed: true
  ground: "factual-accuracy (valuable verified content dropped as 'redundant'/'unsupported') plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/reconciliation/, src/repository_presenter/components/readme/validation/, tests/components/readme/reconciliation/, tests/components/readme/validation/]}
  outcome: a unit is dropped only when something true takes its place or nothing supports it
  accept: ["Words-Python Quick Start and Cells-Rust Project Structure negatives fail the new rule on their sealed inputs", "BC-05 version bumped once in TC-VER-01"]
  children:
    - id: TC-DSP-01-01
      title: Read the normaliser
      steps:
        - "inspect | dispositions.py::normalize and placement_errors (SUPERSEDE_REDUNDANT produced by placement into deterministic sections, banner, enterprise, opening, api_reference table, at_a_glance, install; OMIT_UNSUPPORTED on CONTRADICTED) | every production path listed"
        - "inspect | docs/RECONCILIATION_COVERAGE_ASSESSMENT.md (plan-independent coverage function idea) | reuse noted"
    - id: TC-DSP-01-02
      title: Coverage predicate
      steps:
        - "edit | SUPERSEDE_REDUNDANT requires the covering fact ids to be rendered in the destination section (plan-independent, decidable at reconciliation time) | test with the Email-Python .list vs .table case"
        - "edit | OMIT_UNSUPPORTED requires a failed support lookup, citing the contradicting fact | test with an invented-support negative"
    - id: TC-DSP-01-03
      title: Integrate with BC-05
      steps:
        - "edit | _check_dispositions reports the new failures with a causal stage of RECONCILING | test"

- id: TC-DSP-02
  title: Live-README floor (starts as an investigation: how much of it must-carry already covers)
  reqs: [REQ-DSP-02]
  item: G3-W08
  lane: L-disp
  depends: [TC-DSP-01]
  governed: true
  ground: "factual-accuracy plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/validation/, tests/components/readme/validation/, docs/README_CONTRACT.md]}
  outcome: a candidate cannot be worse than the live README on carried, verified information
  accept: ["BC-13 added (README_CONTRACT section 5 allows 15 blocking rows; 12 exist)", "negative controls from the reviews fail BC-13", "no duplicate of the must-carry gate (#265, #312)"]
  children:
    - id: TC-DSP-02-01
      title: Measure the gap the existing gates leave
      steps:
        - "inspect | must-carry (S6) and BC-07 structure rules for required sections; why Words-Python sealed without Quick Start | gap statement"
        - "run | the TC-ACC-01 protocol's floor comparison over the 30 sealed READMEs | which reviews' findings no current gate would catch"
    - id: TC-DSP-02-02
      title: Define and implement
      steps:
        - "edit | BC-13: every verified fact the live README states is rendered or its omission is explained by a contradicting fact (Candidate.original_readme is available to validate_candidate) | focused tests"
        - "edit | README_CONTRACT section 5 row and Check entry with version, judge in the judges dict, INVALIDATING decision in bundle/seal.py | contract parity test green"

- id: TC-CLM-01
  title: Claim support: versions, install, publication, capability claims
  reqs: [REQ-CLM-01, REQ-CLM-02]
  item: G3-W08
  lane: L-disp
  depends: [TC-R2-00]
  cut: "1-if-ready (Sunday 22:00 rule, TC-CUT-02), else 2"
  governed: true
  ground: "factual-accuracy (false install version, 'not published', invented capabilities in sealed READMEs) plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/validation/, src/repository_presenter/components/readme/evidence/facts/, src/repository_presenter/core/facts.py, tests/]}
  outcome: a version, install command or publication statement in the README equals a manifest or live-registry fact
  accept: ["BC-14 fails Slides-Java 26.8.0, Note-Python 'pip install aspose-note', Cells-Cpp 'not published', PDF-Java and PDF-.NET stale versions", "published_version is consumed only by version statements"]
  children:
    - id: TC-CLM-01-01
      title: A fact for the live published version
      steps:
        - "inspect | extractors/surface/registry.py::observe, _vendor publication_probe, core/package_registry.py (only 'python' registers an observer; RegistryObservation.latest_version lives only in probes.json) | gap confirmed"
        - "edit | emit package:published_version from the observation with deterministic evidence text (no timestamps) | fixture for npm, NuGet, Maven, PyPI"
    - id: TC-CLM-01-02
      title: The check
      steps:
        - "edit | BC-14: version/install strings equal manifest or published version; 'not published' matches install_command; capability 'adds…' clauses cite facts | each reviewed false claim is a failing fixture"

- id: TC-COV-02
  title: New fact kinds for the information the clones hold
  reqs: [REQ-COV-01]
  item: G3-W08
  lane: L-extract
  depends: [TC-COV-01, TC-CLM-01]
  cut: "thin slice 1-if-ready: only kinds whose information an existing template section already renders (decided from TC-COV-01-02's ranked gaps); remaining kinds 2"
  governed: true
  ground: "owner approval D-OWN-2 (owner goal: all clone information in one README); extractor registry, no if/elif"
  paths: {write: [src/repository_presenter/core/facts.py, src/repository_presenter/components/readme/evidence/facts/, src/repository_presenter/components/readme/extractors/, tests/]}
  outcome: repo_doc, changelog, community, cli, framework_matrix facts and a producer for capability, each with a disposition path
  accept: ["each kind has a fixture from a real repository and a focused test", "one-line change per kind in FactKind, extract_facts, ROW_FACT_KINDS (validation) and RENDERING_FACT_KINDS (reconciliation)", "scope limited to the top gaps of TC-COV-01-02"]
  children:
    - id: TC-COV-02-01
      title: repo_doc (docs/**/*.md headings and summaries)
      steps:
        - "edit | FactKind literal in core/facts.py; emitter in evidence/facts/ | fixture"
        - "edit | ROW_FACT_KINDS and RENDERING_FACT_KINDS entries | test"
    - id: TC-COV-02-02
      title: changelog / release notes
      steps:
        - "edit | emitter from CHANGELOG* and the repository release notes already observed read-only | fixture; same registration steps"
    - id: TC-COV-02-03
      title: community files (CONTRIBUTING, SECURITY, CODE_OF_CONDUCT)
      steps:
        - "edit | give FileInventory.community_paths a reader (it has none) | fixture; same registration steps"
    - id: TC-COV-02-04
      title: CLI entry points and framework/platform matrix
      steps:
        - "edit | per-ecosystem plugins register cli and framework facts (e.g. PDF-.NET netstandard2.0/net48/net8/9/10) | one fixture per ecosystem plugin"
    - id: TC-COV-02-05
      title: capability producer
      steps:
        - "edit | emit capability facts where the manifest or API surface supports them | test; unsupported capabilities never emitted"

- id: TC-COV-03
  title: Placement and rendering of the new units inside the 10-section template
  reqs: [REQ-COV-01, REQ-CTR-01]
  item: G3-W08
  lane: L-compose
  depends: [TC-COV-02]
  governed: true
  ground: "owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/composition/, docs/README_CONTRACT.md, tests/components/readme/composition/]}
  outcome: new information appears in Documentation & Resources, Scope and Limitations, Development and Testing or an optional section, never as free-form filler
  accept: ["optional sections appear only when verified facts exist (Additional Examples, Project Structure, CLI, Releases)", "At a Glance remains exactly one mermaid fence", "mechanical template filling is still refused (D14)"]
  children:
    - id: TC-COV-03-01
      title: Contract rows then code
      steps:
        - "edit | README_CONTRACT rows for the optional sections and their evidence rules | parity test green"
        - "edit | planning/authoring/renderer changes bounded to those rows | sealed_bytes diff reviewed card by card"

- id: TC-EXT-01
  title: Extractor defect fixes (real-repository fixtures first)
  reqs: [REQ-EXT-01]
  item: G3-W08
  lane: L-extract
  depends: [TC-R2-00, TC-RSL-03]
  cut: "2 (lands after wave 1's reseal)"
  governed: true
  ground: "factual-accuracy (wrong dependencies, lost manifests, wrong import paths) plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/extractors/, tests/components/readme/extractors/]}
  outcome: six known defects fixed, each with a failing fixture that now passes
  accept: ["fixtures come from the repositories where the defect was seen", "EXTRACTOR_VERSION bumped once in TC-VER-01"]
  children:
    - id: TC-EXT-01-01
      title: Python dependency specifiers
      steps:
        - "create | fixture 'numpy>=1.20,<2' (currently two facts) | fails"
        - "edit | parse with a PEP 508 parser instead of splitting on commas | passes"
    - id: TC-EXT-01-02
      title: Manifest lost under paths containing build/out/lib/bin
      steps:
        - "create | fixture with the checkout under such a directory | fails"
        - "edit | filter on the path relative to the repository root in ts/java/net/cpp detect_manifest | passes"
    - id: TC-EXT-01-03
      title: src-layout import path, dynamic dependencies, ownership, facade reachability, Maven parent
      steps:
        - "create | five fixtures (import_path:src.pkg; dynamic deps must not be 'verified zero'; registry presence is not ownership; facade honours reachable; Maven <parent> first-match) | each fails"
        - "edit | one fix per fixture, each its own commit-sized change | all pass"

- id: TC-INV-01
  title: Reopen a candidate only through the facts it consumed
  reqs: [REQ-INV-01]
  item: G7-W25
  lane: L-core
  depends: [TC-COV-02]
  governed: false
  owner_gate: D-OWN-4
  paths: {write: [src/repository_presenter/components/readme/bundle/, tests/components/readme/bundle/, schemas/ (dependencies shape, via the named item)]}
  outcome: adding a fact kind or changing an unconsumed fact reopens nothing
  accept: ["dependencies.json records consumed fact ids (additive)", "evaluate() compares only those", "negative controls both directions"]
  children:
    - id: TC-INV-01-01
      title: Record and compare
      steps:
        - "inspect | bundle/seal.py::upstream_dependencies (facts hash map) and bundle/evaluation.py::evaluate | exact comparison sites"
        - "edit | record the fact ids the sealed units/plan cited; compare that subset | unit tests: unconsumed change -> no reopen; consumed change -> EXTRACTING"

- id: TC-INV-02
  title: Volatile web observations out of hashed evidence
  reqs: [REQ-INV-02]
  item: G7-W25
  lane: L-extract
  depends: [TC-INV-01]
  governed: true
  ground: "owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/evidence/facts/links.py, src/repository_presenter/components/readme/evidence/facts/product_pages.py, tests/]}
  outcome: HTTP codes, redirects and timings live in ProbeRecord; evidence keeps only RESOLVED/BROKEN
  accept: ["a changed HTTP status with the same verdict invalidates nothing", "a broken link still fails BC-06"]
  children:
    - id: TC-INV-02-01
      title: Move the detail
      steps:
        - "edit | link_facts and the product-page lookup write status/timing/final URL to ProbeRecord only | tests"

- id: TC-CUR-01
  title: Consumed-scope recheck and currency states (doc 13 minimum slice)
  reqs: [REQ-CUR-01]
  item: G7-W25
  lane: L-core
  depends: [TC-INV-01]
  governed: false
  owner_gate: D-OWN-4
  paths: {write: [src/repository_presenter/components/readme/bundle/recheck.py, src/repository_presenter/components/readme/bundle/portfolio.py, src/repository_presenter/components/readme/bundle/dry_run.py, src/repository_presenter/core/candidates.py, src/repository_presenter/cli.py, tests/, docs/STATE_MACHINE.md]}
  outcome: a bundle sealed on frozen code stays counted across bumps that change nothing it consumed; stale-and-failing is reported separately
  accept: ["doc 13 section 6.6 tests all present", "day-one numbers equal doc 13 section 4 (2 current, 2 rerender_only, 26 recompose)", "environment.*_version no longer routes 24 bundles to INVALIDATED"]
  children:
    - id: TC-CUR-01-01
      title: Owner decisions of doc 13 section 7
      steps:
        - "decide-owner | (1) prompt-only differences are provenance; (2) UNVERIFIED reviewer scope does not count as independently accepted; (3) batch contract hardening per the freeze | recorded as D-OWN-4"
    - id: TC-CUR-01-02
      title: Routing fix first (smallest useful slice)
      steps:
        - "edit | environment.*_version difference reopens EXTRACTING as 'would re-extract', not INVALIDATED; only a facts-hash difference invalidates; a check the sealed record lacks must run | status --stale: 24 false INVALIDATED routes gone"
    - id: TC-CUR-01-03
      title: Recheck module
      steps:
        - "create | bundle/recheck.py: loader plus five scope rechecks reusing tools/reviewer/bump_cost/current_recheck.py logic | doc 13 section 4 table reproduced"
        - "create | receipts at candidates/<slug>/rechecks/<revision>.json keyed by manifest digest and the constants consumed; ignored when the key differs | tamper test"
    - id: TC-CUR-01-04
      title: Funnel and CI preview
      steps:
        - "edit | portfolio/status use currency states; partition splits update_available into update_required and update_unverified | partition still sums to the denominator"
        - "create | warn-only CI step: a PR touching a governed source prints how many of N bundles change outcome | prints on a synthetic bump"

- id: TC-BND-01
  title: Bundle integrity and replay completeness
  reqs: [REQ-BND-01]
  item: G3-W08
  lane: L-core
  depends: [TC-INV-01]
  governed: false
  paths: {write: [src/repository_presenter/components/readme/bundle/, src/repository_presenter/core/candidates.py, src/repository_presenter/core/llm/, tests/]}
  outcome: any bundle written by the second cut is fully replayable and tamper-evident enough to trust
  accept: ["raw_calls.json always written", "model-availability probes appear in the ledger totals", "original README recoverable (doc 13: reverse-apply README.patch) or stored", "manifest/CURRENT tamper evidence decided and recorded"]
  children:
    - id: TC-BND-01-01
      title: Replay completeness
      steps:
        - "edit | always write raw_calls.json; count select_models probes in the ledger | verify-noop-proof reconciles totals"
    - id: TC-BND-01-02
      title: Tamper evidence
      steps:
        - "decide-owner | record manifest digest in the durable-state receipt (no CURRENT format change) versus accept git history and PR review as the control | decision recorded"

- id: TC-CTR-01
  title: Template variation and the two open ratification follow-ups
  reqs: [REQ-CTR-01]
  item: G3-W08
  lane: L-compose
  depends: [TC-COV-03]
  governed: true
  ground: "owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/composition/, src/repository_presenter/components/readme/review/acceptance/, docs/README_CONTRACT.md]}
  outcome: product-specific shape expressed as data inside the 10-section template
  accept: ["a diagram-archetype table (transform / generative / compile / hybrid) as data", "the banner-vs-C01 and renderer-owned-section-vs-D14 conflicts that make 30/30 unreachable are resolved by an owner ruling and implemented"]
  children:
    - id: TC-CTR-01-01
      title: Resolve what blocks the full 30
      steps:
        - "decide-owner | change the renderer or change the rules for the banner (fails C01 in all 30) and the renderer-owned License/Navigation sections (D14 fires in all 30) | ruling recorded in DECISION_LOG (follow-up from G7-W20)"
        - "edit | implement the ruling | score distribution re-measured over the sealed set"

- id: TC-PRP-01
  title: Propose gate and pull-request content
  reqs: [REQ-PRP-01]
  item: G6-W03
  lane: L-hosted
  depends: [TC-REV-01, TC-CUR-01]
  governed: false
  paths: {write: [src/repository_presenter/components/propose/, src/repository_presenter/core/candidates.py, tests/components/propose/]}
  outcome: propose refuses stale/unproven candidates and every PR tells a maintainer what changed
  accept: ["refusals: no review-honesty marker, currency not in {CURRENT, RECHECKED_CURRENT}, no measured no-op proof, score below the ratified threshold (owner sets whether the score gates)", "PR title names the product and change; body lists changed sections, verification summary, how to review and how to decline (F-18)"]
  children:
    - id: TC-PRP-01-01
      title: Gates
      steps:
        - "edit | load_proposable_candidate and wave.py assess_wave add the checks; refusal codes typed | one test per refusal"
    - id: TC-PRP-01-02
      title: Pull-request content
      steps:
        - "edit | generate title and body from the README diff and the validation/review records; no internal artifact names | golden-file test"

- id: TC-VER-01
  title: Version literals from one source; one bump per constant for the cut-1 slice
  reqs: [REQ-VER-01]
  item: G3-W08
  lane: L-core
  depends: [TC-REV-01, TC-CLM-01, TC-COV-02]
  cut: "1-if-ready"
  governed: true
  ground: "owner approval D-OWN-2; with TC-VER-02 this is the only place pins move"
  paths: {write: [src/repository_presenter/components/readme/, tests/components/readme/validation/test_registry.py, tests/components/readme/bundle/test_seal.py, tests/test_cli.py]}
  outcome: each governed constant moves exactly once for the second cut, derived from one place
  accept: ["a later bump is a single edit", "tests/test_version_bump_discipline.py green", "pins in test_registry/test_seal/test_cli derived, not hard-coded"]
  children:
    - id: TC-VER-01-01
      title: Single source then bump
      steps:
        - "inspect | where each pinned literal appears (validator_version == '17' in test_registry etc.) | list"
        - "edit | derive pins from the constants; bump only what the cut-1 slice changed (REVIEWER_LOGIC, VALIDATOR plus the new BC-14 Check, the fact-kind constants of any thin COV-02 kind) once | CI green"

- id: TC-VER-02
  title: One bump per constant for cut 2
  reqs: [REQ-VER-01]
  item: G3-W08
  lane: L-core
  depends: [TC-VER-01, TC-DSP-01, TC-DSP-02, TC-COV-03, TC-EXT-01, TC-INV-02, TC-CTR-01]
  cut: 2
  governed: true
  ground: "owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/, tests/components/readme/validation/test_registry.py, tests/components/readme/bundle/test_seal.py, tests/test_cli.py]}
  outcome: the second cut's changes bump each affected governed constant exactly once
  accept: ["tests/test_version_bump_discipline.py green", "no pin hard-coded in the three test files"]
  children:
    - id: TC-VER-02-01
      title: Bump
      steps:
        - "edit | bump NORMALISATION, VALIDATOR, affected Check versions, INHERITED_UNITS, EXTRACTOR as the cut-2 cards require, once each | CI green"

- id: TC-R2-00
  title: Record the owner's approvals for governed changes (cut-1 slice and cut 2)
  reqs: [REQ-GOV-01]
  item: G7-W22
  lane: supervisor
  depends: [TC-GOV-01]
  governed: false
  paths: {write: [docs/DECISION_LOG.md, project/state.yaml]}
  outcome: the owner's plan-review answers of 2026-10-10 are in the decision log as the approval G7-W22 clause 2 requires
  accept: ["every governed:true card names this record as its ground", "the record states exactly what was approved: a second planned reseal; coverage extension in the first cut only if it fits Monday (Tuesday 2026-10-13 at the latest); first wave as large as possible", "doc 13 decisions (D-OWN-4) are NOT covered by it and stay owner-gated"]
  children:
    - id: TC-R2-00-01
      title: Write it down
      steps:
        - "record | DECISION_LOG entry quoting the owner's answers of 2026-10-10 on this plan (second reseal: yes; coverage in first cut only if Monday holds, Tuesday at most; first wave maximal; reuse local toolchains; placement left to the supervisor) | entry appended, tests pass"

- id: TC-R2-01
  title: Declare the second cut
  reqs: [REQ-CUT-01]
  item: G7-W22
  lane: supervisor
  depends: [TC-VER-02, TC-CUR-01, TC-PRP-01]
  governed: false
  paths: {write: [docs/DECISION_LOG.md, project/state.yaml]}
  outcome: a named commit; no governed change afterward
  accept: ["same predicate as TC-CUT-01"]
  children:
    - id: TC-R2-01-01
      title: Repeat TC-CUT-01 for the new code
      steps:
        - "record | cut sha, before-counts, list of governed changes and their grounds | entry appended"

- id: TC-R2-02
  title: Second portfolio reseal with the code gates
  reqs: [REQ-RSL-01, REQ-ACC-01]
  item: G7-W22
  lane: L-seal
  depends: [TC-R2-01]
  governed: false
  paths: {write: [candidates/, evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/]}
  outcome: candidates sealed under the honest gates; the review lane now confirms rather than rescues
  accept: ["TC-RSL-03, TC-TRI-01, TC-ACC-01, TC-ACC-02 repeated with R2 in their evidence names", "the count that results is reported as measured, not as targeted"]
  children:
    - id: TC-R2-02-01
      title: Re-run the reseal cards
      steps:
        - "run | TC-RSL-03 .. TC-ACC-02 on the second cut | boards and records for R2"
```

---

## 11. Taskcards, Track D (the autonomous refresh app on GitHub)

**Baseline on origin/main:** `monitor.yml` (cron `17 */6 * * *`; per-owner drift legs; statuses CURRENT / DRIFTED / UNKNOWN / NO_BUNDLE / UNREACHABLE; content drift via recorded `upstream_blobs`, #274), `sealing-scheduled.yml` (cron `37 5 * * *`; plan → seal matrix, max-parallel 1 → publish-candidates, propose), `present.yml` (durable-state, two invocations + `verify-noop-proof`), `propose.yml` (manual dispatch; one stable branch `repository-presenter/readme-update`), `candidates-publish.yml` (dormant), `liveness.yml`, `core/sealing_plan.py` (drift-only, cap 3, 24h cooldown), `core/state/` (CAS, leases, fencing; `renew_lease` has no production caller). A hosted schedule-fired monitor run reconciled with local state, a hosted unattended seal-to-commit-back, and any live external write have **never been observed**.

```yaml
- id: TC-REF-01
  title: Relevance-aware monitor (what changed that this README consumed)
  reqs: [REQ-REF-01]
  item: G7-W06
  lane: L-hosted
  depends: [TC-INV-01, TC-RSL-02]
  governed: false
  paths: {write: [src/repository_presenter/components/monitor/, .github/workflows/monitor.yml, src/repository_presenter/core/sealing_plan.py, tests/]}
  outcome: each cycle classifies NO_CHANGE / IRRELEVANT_CHANGE / RELEVANT_CHANGE / UNREACHABLE and records a zero-LLM freshness check every 30 days
  accept: ["a version-bump-only upstream commit (e.g. PDF-Java release chore) is IRRELEVANT unless the README states that version", "a changed consumed fact or maintainer README edit is RELEVANT", "a schedule-fired run (not workflow_dispatch) is observed and reconciled with local state"]
  children:
    - id: TC-REF-01-01
      title: Classify with consumed scope
      steps:
        - "inspect | components/monitor/drift.py observe_repository, _content_status, assemble_drift_contract (fails closed on stale >12h evidence) | extension points"
        - "edit | compare recorded consumed fact ids and upstream_blobs to the live tree; emit the four classes | tests with fake reads"
    - id: TC-REF-01-02
      title: Freshness check without a model
      steps:
        - "edit | every 30 days re-extract facts, probe registry versions, re-resolve links; differing consumed facts mark RELEVANT | zero provider calls proven in the ledger"
    - id: TC-REF-01-03
      title: Observe it for real
      steps:
        - "record | first schedule-fired monitor run id, reconciled against status | evidence in G7-W06 stage-1 text"

- id: TC-REF-02
  title: Unattended seal to commit-back, bounded
  reqs: [REQ-REF-02]
  item: G7-W06
  lane: L-hosted
  depends: [TC-REF-01, TC-RSL-02, TC-R2-02]
  governed: false
  paths: {write: [.github/workflows/sealing-scheduled.yml, src/repository_presenter/core/sealing_plan.py, tests/test_sealing_workflow.py]}
  outcome: a relevant upstream change produces a candidate PR on the control repo without a person
  accept: ["cap, cooldown and a per-run provider-call budget enforced", "paused by REPOSITORY_PRESENTER_SEALING_PAUSED", "a synthetic upstream change yields a workflow-authored candidates/ PR within one cycle"]
  children:
    - id: TC-REF-02-01
      title: Select by relevance, not by drift alone
      steps:
        - "edit | plan_sealing_run takes RELEVANT_CHANGE and resolved-BLOCKED_UPSTREAM entries; keep cap and cooldown | tests"
    - id: TC-REF-02-02
      title: Budget
      steps:
        - "edit | per-run and per-day provider-call budget; exceeding it stops the matrix and alerts | test with fake ledger"
    - id: TC-REF-02-03
      title: Observe
      steps:
        - "run | one unattended cycle after the owner enables the variables | run id, PR and zero-call no-op proof on an unchanged revision recorded"

- id: TC-REF-03
  title: Standing authorization (owner-signed) replacing per-hash records after the pilot wave
  reqs: [REQ-REF-03]
  item: G6-W06
  lane: L-hosted
  depends: [TC-WAV-01]
  governed: false
  owner_gate: D-OWN-7
  paths: {write: [src/repository_presenter/core/authorization/, schemas/, ops/, tests/]}
  outcome: a per-repository policy record (README-only scope, branch convention, minimum PR interval, expiry <=90 days, revocable) lets the system open or update its one PR when a gated candidate exists; every run still writes an effect receipt bound to the candidate hash
  accept: ["schema through a named item with owner admission", "revocation by reverting one file", "AGENTS.md 'candidate acceptance never implies publication authorization' still holds: the record is the owner act"]
  children:
    - id: TC-REF-03-01
      title: Design and admit
      steps:
        - "inspect | core/authorization/proposal.py (7-day per-hash record), record_provenance.verify_record_provenance | what a standing record must still bind"
        - "decide-owner | admit the standing-record schema (D-OWN-7) | admission recorded"
    - id: TC-REF-03-02
      title: Implement
      steps:
        - "edit | validate_authorization accepts a standing record plus dynamic candidate binding; receipts written; tests for expiry, scope, revocation, hash mismatch | green"

- id: TC-REF-04
  title: Update in place, maintainer edits, closed PRs, and the disposable live proof
  reqs: [REQ-REF-04]
  item: G6-W02
  lane: L-hosted
  depends: [TC-PRP-01, TC-REF-03, TC-WAV-01]
  governed: false
  paths: {write: [src/repository_presenter/components/propose/, .github/workflows/propose.yml, tests/components/propose/]}
  outcome: one stable PR per repository that is updated, not duplicated; behavior for maintainer edits and closed PRs defined and tested
  accept: ["live proof against the owner-named throwaway target (babar-raza/presenter-sandbox exists; OWNER-11) only after the pause of 2026-10-10 is lifted", "create, update without duplicate, stale-source block, lost-response reconciliation all observed", "PR attribution (performed_via_github_app) and write-token provenance (/installation/repositories) verified live for the first time"]
  children:
    - id: TC-REF-04-01
      title: Policies
      steps:
        - "edit | if the README changed upstream since the candidate: reconcile and re-seal, never overwrite; if the PR was closed unmerged: cool-down and record, no recreation unless a new record names it in supersedes_prs; after merge: new baseline, skip preservation tracking when candidate == live | tests per policy"
    - id: TC-REF-04-02
      title: Live proof (blocked by the pause)
      steps:
        - "decide-owner | lift the pause for the disposable target and install the App there (OWNER-11, G6-W02) | recorded"
        - "run | runbook sections 3 to 5 against the throwaway target | all four proofs observed"

- id: TC-REF-05
  title: Refresh policy: when to open, update, or stay silent
  reqs: [REQ-REF-05]
  item: G7-W06
  lane: L-hosted
  depends: [TC-REF-01]
  governed: false
  paths: {write: [src/repository_presenter/core/, docs/STATE_MACHINE.md, tests/]}
  outcome: three tested tiers: factual/security fix now; consumed-fact change within the interval; cosmetic or our-own-improvement never opens a PR (effect-report path)
  accept: ["minimum PR interval per repository enforced", "our own component improvements never open PRs by themselves", "documented in STATE_MACHINE section on refresh"]
  children:
    - id: TC-REF-05-01
      title: Encode and test
      steps:
        - "create | policy table in code with tests for each tier and the interval | green"

- id: TC-REF-06
  title: Failure, outage and recovery
  reqs: [REQ-REF-06]
  item: G7-W07
  lane: L-hosted
  depends: [TC-REF-02]
  governed: false
  owner_gate: OWNER-12
  paths: {write: [src/repository_presenter/core/state/, src/repository_presenter/core/llm/, .github/workflows/, tests/]}
  outcome: a gateway outage is BLOCKED_EXTERNAL and retried next cycle without spending the budget; long runs renew leases; kill-mid-transaction recovers hosted
  accept: ["OWNER-12 (gateway outage policy) decided and asserted by test", "renew_lease has a production caller", "hosted kill and stale-lease rehearsals pass (G7-W05)"]
  children:
    - id: TC-REF-06-01
      title: Policy then code
      steps:
        - "decide-owner | OWNER-12 outage policy (retry window, budget behavior, alerting) | recorded"
        - "edit | wire renew_lease into long runs; classify outage as BLOCKED_EXTERNAL; no budget burn | tests"
        - "run | hosted rehearsal: kill a run mid-transaction; hold a stale lease | recovery without double processing"

- id: TC-REF-07
  title: Observability and dead-man coverage
  reqs: [REQ-REF-07]
  item: G7-W07
  lane: L-hosted
  depends: [TC-REF-02]
  governed: false
  paths: {write: [.github/workflows/liveness.yml, src/repository_presenter/cli.py, src/repository_presenter/core/state/health.py, tests/]}
  outcome: every run emits a funnel summary, per-candidate freshness age, cost; the dead-man covers monitor, sealing, publish and issues
  accept: ["a stalled schedule alerts within the dead-man interval", "status prints freshness age and the issue funnel"]
  children:
    - id: TC-REF-07-01
      title: Summaries and alerts
      steps:
        - "edit | job summaries; health-check annotations for each workflow | synthetic stall triggers the alert"

- id: TC-REF-08
  title: Security of the unattended path
  reqs: [REQ-REF-08]
  item: G7-W01
  lane: L-hosted
  depends: [TC-REF-02]
  governed: false
  paths: {write: [docs/THREAT_MODEL.md, .github/workflows/, tests/]}
  outcome: threat model deltas for commit-back, standing authorization and issue filing; residual example-execution risk addressed or recorded
  accept: ["analysis tokens read-only; write tokens minted only inside the effect job", "no credential in any artifact (grep test over a sample run)", "network-egress plan for example execution recorded (execution is secret-stripped but not network-sandboxed)"]
  children:
    - id: TC-REF-08-01
      title: Review and test
      steps:
        - "inspect | each new workflow's permissions and token use against THREAT_MODEL areas | deltas listed"
        - "create | adversarial-content tests per new surface (issue body, PR body, README unit) | green"

- id: TC-REF-09
  title: Staged rollout and service levels
  reqs: [REQ-REF-09]
  item: G7-W06
  lane: supervisor
  depends: [TC-REF-02, TC-REF-04, TC-REF-06, TC-REF-07]
  governed: false
  paths: {write: [project/state.yaml, docs/DECISION_LOG.md]}
  outcome: shadow, then issues, then a PR pilot on the two `full` repositories, then per-repository expansion each with its own owner record
  accept: ["stage exit evidence recorded per stage", "measured service levels replace the proposed ones: relevant change -> candidate within 24h and PR within 48h; unchanged revision -> zero provider calls"]
  children:
    - id: TC-REF-09-01
      title: Stages
      steps:
        - "run | stage 1 shadow: monitor + seal + commit-back only (control repo writes only) for N cycles | no incident, counts recorded"
        - "run | stage 2: approved issues live (Track B) | issues filed once"
        - "decide-owner | stage 3: PR pilot on Cells-Java and 3D-Java only after their candidates pass the review lane and the owner signs | recorded"
        - "decide-owner | stage 4: expand per repository, one owner record each | recorded"
```

---

## 12. Validation, evidence, rollback, defaults

**Official proof chain for every outcome:** real input (a live upstream head) → official entry point (`present`, `monitor`, `issue-readiness`, `wave-readiness`, `file-upstream-defects`, `propose`, `publish-candidates`, or the matching workflow) → processing → artifact (bundle, handoff, record, PR) → validator/gate (blocking checks, `verify-noop-proof`, `sealed-ready`, `issue-readiness`) → downstream consumer (CI tests that read `candidates/`, `status`, the next workflow) → observed result (run id, PR/issue URL, counts).

| Category | Commands / methods | Mandatory for |
|---|---|---|
| Focused | `pytest <path> -q` per card; mutation test per new rule | every code child |
| Integration | `scripts/ci_check.sh` (preflight, lockdrift, sbom, ruff, format, mypy, pytest, entrypoint) | every PR |
| Negative controls | hallucinated/unsupported/malformed output; stale lease; duplicate trigger; secret leakage; source drift before publication; non-processable placeholders (AGENTS.md list); plus the review-derived false claims (Slides-Java 26.8.0, Note `aspose-note`, Cells-Cpp "not published", Words-Py no Quick Start, forbidden wording) | gates and checks |
| Rerun/idempotency | second `present` zero provider calls (`verify-noop-proof`); second `publish-candidates`, `issues-scheduled`, `propose` create nothing | every effect |
| Recovery | kill-mid-transaction, stale lease, lost-response simulation | Track D |
| Downstream consumer | `status`, `wave-readiness`, `issue-readiness` read the artifact the card produced | every artifact card |
| Plan integrity | `pytest tests/test_plan_lint.py` | every plan-affecting PR |
| Hosted | `gh run view <id>`; `git ls-remote origin refs/repository-presenter-state/*`; PR checks on the exact head commit | hosted claims |
| Scale | reseal wall time and calls versus the pilot's estimate (median 11 min per repo; ~20% of calls rejected per owner log) | TC-RSL-03 |

**Evidence rules.** Evidence is redacted, revision-bound, checksum-valid and attributable; creating evidence is not delivery. Every artifact header carries `authoritative_plan: plans/reseal-and-refresh/PLAN.md`, the requirement, the card and (if any) the micro-step. Nothing in `evidence/` may contain instructions that conflict with the plan. Supporting generated maps are regenerated by lint, never edited.

**Global rollback.** Code and docs: revert the PR. Bundles: revert the wave PR to restore the previous `candidates/` tree. Hosted effects: a filed issue is closed "not planned" with a comment and its approvals revoked by revert; a PR is closed and the standing/per-hash record reverted; variables returned to their prior values. Durable-state transitions are append-only: rollback is a new transition, never a rewrite.

**Idempotent reruns of this plan.** Stable IDs derive from area/number/position; re-running the taskcardization reuses IDs and repairs only missing, broad, stale or contradictory cards; completed verified cards are preserved; lint proves no duplicate cards, no orphan micro-steps, and no state/evidence disagreement.

---

## 13. Execution handoff (what a Sonnet lane agent does, in order)

1. Read `plans/reseal-and-refresh/PLAN.md` only (this one path) and the registered work item it serves.
2. Read the selected parent card, then the selected child card; confirm its `depends` are CLOSED in the ledger (`loop-status.jsonl` fold) and its path ownership is free.
3. Start from `scripts/new_worktree.sh <name>`; run `git fetch`; confirm base == `origin/main`; never work in the main checkout.
4. Answer the seven stay-on-track questions in the first ledger line: parent, requirement, expected output, allowed paths, forbidden paths, evidence, next valid step.
5. Execute exactly one micro-step at a time; write evidence immediately; append the ledger transition with the evidence hash.
6. Run the child's checks; a non-author scores it; below 4/5 → REROUTED and the smallest new child is added.
7. Close the child only with proof; run parent integration checks after the last child; close the parent only with integration proof.
8. Continue to the next card per the DAG. Do not choose unrelated work, widen scope, skip a micro-step silently, treat code existence or test existence as proof, or treat an evidence path as evidence without opening its contents.
9. Outbound effects (issue, PR, variable, secret, registry mode, App change): stop and present the exact list to the owner; proceed only on the recorded approval.

---

## 14. Feedback, decisions for you, and what I am unsure of

**What is solid.** The problem is already diagnosed and partly governed by you (G7-W21/W22, doc 13). The shipping path that needs no governed change is real: issue system (Track B), the cut and reseal on frozen code (Track C-0), and a review lane that stops upstream regressions. Doc 13's measurement agrees with my independent reviews: 26 of 28 stale bundles need re-composition, so no recheck or counting change makes the count honest by itself.

**What I got wrong, so you can discount the rest accordingly.** I planned on a main checkout 22 commits behind origin/main; my first plan duplicated your registered plan and rebuilt tools that exist. The corrected layer only adds what is missing. Two reviewed candidates (BarCode-Python, Cells-Python) were re-sealed after my review and must be re-reviewed. The code anchors from my first surveys are from the stale base: every `inspect` step re-verifies them.

**Your answers of 2026-10-10 and how the plan now honours them.** (1) *First wave as large as possible, to show the system handles a large part of the portfolio without major changes*: the plan attempts all 36 in the first pass (no cap of 20), and TC-WAV-01 records for every candidate that is not authorizable whether a minor or a major change would fix it, which is exactly your test. (2) *Second reseal: yes*: Track C-2 and TC-R2-02. (3) *Monday, Tuesday at the latest; coverage in the first cut only if it fits*: a time-boxed cut-1 slice with a rule-based Sunday 22:00 go/no-go (TC-CUT-02); the full coverage extension is cut 2. (4) *Reuse the machine's toolchains*: resolved, reseal runs here. (5) *Placement*: `plans/reseal-and-refresh/` (sprint/healing precedent), decided by me.

**Honest expectations (unchanged by your answers, so you can hold me to them).** Your own recon put 20 re-sealed by Monday at about 10%, and my reviews say the *currently sealed* READMEs would make upstream READMEs worse. The plan therefore maximises the *attempted* and *sealed* count, but keeps one non-negotiable rule: no candidate is proposed unless the independent comparison with its live README says it is not worse. If that rule yields fewer than 20, the report says so with reasons, and your 2026-10-10 pause ("no real push until 20 are re-sealed") means the owner, not I, decides whether a smaller wave goes. Issues (Track B) carry real value regardless and are not blocked by the review rule.

**Weak points in this plan.**
1. **Independent review is compensated, not solved** in Track C-0: the reviewer still demotes REJECT to ACCEPT and the second read is the same prompt with a different seed. The review lane is a process control run by agents; code gates arrive only in the second cut.
2. **The second cut is a second reseal.** You accepted it. The risk is that G7-W22 clause 2 limits bumps after the cut: the cut-1 slice and cut 2 each rest on your recorded approval (TC-R2-00) and on a factual-accuracy ground; if either is challenged, the lint tool will refuse a `governed: true` card without its ground.
3. **The cut-1 slice can lower the pass count before it raises it.** A REJECT that stands means more repair rounds and more rejections at seal time. It should raise the count of *genuinely good* candidates (repair fixes findings instead of shipping them), but that is a hypothesis; TC-PIL-01 and the Sunday rule measure it, and the fallback is to cut at current origin/main.
4. **Parallel `present` on one machine.** The old runbook forbids concurrent runs because of a `state.yaml` counter race; the mitigation (one worktree each, supervisor alone edits `state.yaml`) is the #305 pattern but has not been run at 6 to 8 parallel; the first wave could expose it. Gateway limits are the real ceiling and are measured first (TC-PRE-01-03).
5. **Weight.** A plan layer with a lint tool and a ledger is the kind of governance weight this project already carries (`docs/CI_AND_STALENESS_ASSESSMENT.md`: validation substituting for shipping). I kept it to one lint tool and one ledger, and Track B and the review lane do not depend on it. If you want less ceremony, TC-LNT-01 can be cut to a ledger fold and a link check.
6. **Unknowns still open (the earlier ones were resolved in §1.2):** gateway limits at parallel load (measured first), App `issues:write` per organization (your hands), and the fraction of reseals the review lane authorizes (the pilot answers it).
7. **Your meta-prompt's 46 artifacts.** I propose that ~30 of them (maps, matrices, audits) are *generated by the lint tool* and regenerated, not hand-written; the rest (analysis, decisions, solution scorecards, readiness verdict) are authored once under `evidence/…/analysis` and `decisions`. They are created when the plan is approved and executed, not now, because plan mode forbids writing them.

**Decisions I made as supervisor (override any).** D-OWN-1: ship Track B and Track C-0 first; attempt all 36; report the shortfall; push only what TC-ACC-01 authorizes. D-OWN-2: **approved by your answers of 2026-10-10**: a cut-1 slice (REV-01, CLM-01, thin COV-02) if green by Sunday 22:00, everything else in cut 2 after wave 1's reseal. D-OWN-3: your 2026-10-10 pause covers pull requests and the disposable write proof, not approved issues (confirm in TC-ISS-08-01). D-OWN-4: adopt doc 13 slice by slice; the routing fix is first. D-OWN-5: keep the single review route and rely on the review lane plus deterministic refutation. D-OWN-6: decouple issue filing from PR mode (Option 1). D-OWN-7: per-hash authorization for the pilot wave, standing records only after it.

**Needs your hands (owner actions; I will never do these for you):** pause/enable repository variables; confirm App installation and `issues:write` per organization; approve the exact issue list (merge the approvals PR); sign any proposal wave; decide OWNER-12 (gateway outage policy) and OWNER-11 (throwaway target); lift or keep the pause.

**Remaining questions for your feedback (none blocks the start; defaults apply if unanswered):** (a) D-OWN-3: confirm that your 2026-10-10 pause is about pull requests, not about approved upstream issues (default: issues proceed after you approve the list). (b) D-OWN-5: is one review route plus the independent comparison lane acceptable for now (default yes), or do you want a second review model admitted for cut 1? (c) D-OWN-6: issue filing decoupled from PR mode (default: build the `issues_mode` switch) or the fallback of flipping only issue targets to `full` with PRs made impossible by the missing authorization records. (d) If, on Tuesday, fewer than 20 candidates are authorizable, do you want a smaller canary-then-wave (default: yes, owner signs the exact list) or to hold all pushes?

