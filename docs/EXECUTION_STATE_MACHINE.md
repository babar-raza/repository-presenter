# Repository Presenter Implementation State Machine

Status: authoritative build and delivery plan, revision 3 (2026-10-04, plan forensics; §13-§14)  
Audience: the coding agent responsible for implementing Repository Presenter  
Companion authority: [`STATE_MACHINE.md`](STATE_MACHINE.md) defines the runtime target;
[`../plans/idea.md`](../plans/idea.md) owns the product outcome; `migration/reuse-manifest.yaml`
owns legacy disposition; `project/state.yaml` is the only cursor  
Legacy source baseline: `babar-raza/foss-readme-optimizer` at
`a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815`

This is the only active build plan. It supersedes nothing and is superseded by nothing; the competing
plan channels found in revision 3 are retired by taskcard H-01 (§3). Revision 1's four-infrastructure-
gate sequence was replaced per `RESEARCH_AND_GUIDELINES.md` §17. Cap: 500 lines, eight gates.

## 1. Mission

Build and deploy Repository Presenter as an autonomous GitHub-native system whose foundational
component keeps the README files of authorized repositories accurate, credible, repository-specific,
and current, using a configurable custom LLM inside deterministic controls.

Progress has one unit: **current, reviewable, no-op-proven README candidates**, counted as `READY_FOR_PROPOSAL`
bundles and printed by `status` against the live registry count. This document never states a count.
Code volume, tests, evidence, schemas, transitions, and closed items are not progress. The observable transaction:
inspect an immutable real revision; interpret the product agentically from
repository-grounded evidence; reconcile the existing README without losing valuable content; plan and
compose a concise repository-specific README; validate it with a few blocking checks; obtain one
independent agentic approval; prove an unchanged rerun is byte-identical with zero provider calls;
keep the candidate valid as the system changes; later monitor drift on hosted runners and open or
update a safe proposal; recover correctly after interruption or an uncertain remote effect.

## 2. Binding principles

1. Autonomous on GitHub-hosted runners, on schedules and explicit triggers; the production LLM is a configurable OpenAI-compatible gateway supplied through GitHub secrets.
2. Agentic reasoning is mandatory for interpretation, reconciliation, planning, composition, independent review, and targeted repair. Deterministic code owns evidence, validation, state, transitions, safety, authorization, idempotency, recovery, and GitHub effects.
3. The presentation contract is a brand/assurance shell, not a universal prose template. Each platform extractor is independent of every other and of every downstream stage, sharing only `facts.json` (`REPOSITORY_LAYOUT.md` §2.1).
4. The exact immutable snapshot is factual authority. Existing README content is high-value evidence: validate, preserve, improve, correct, or explicitly omit every material unit.
5. Aspose.org and prior candidates are development oracles, never runtime dependencies. Legacy profiles and catalogs are pulled per repository or family, never in bulk (`RESEARCH_AND_GUIDELINES.md` §7.2.1).
6. A README-only placeholder ends its run as `insufficient_evidence` (AGENTS.md) and persists a `NON_PROCESSABLE` disposition with a typed reason and resume predicate (`STATE_MACHINE.md` §6). Content is never invented (F06).
7. An accepted unchanged transaction makes zero new provider calls.
8. Analysis and write credentials are separate, repository-scoped, and short-lived.
9. One repository failure never stops safe work on unrelated repositories.
10. Research a battle-tested library or standard facility before a custom mechanism; a departure names the alternative considered (`RESEARCH_AND_GUIDELINES.md` §18). A pulled legacy module is judged by this rule too. The legacy mission graph, trusted lane, and proof bureaucracy are never imported.
11. Initial publication is PR-only: opening or updating one, never a direct default-branch commit. Candidate acceptance and permission to publish are separate decisions.
12. **Infrastructure is just-in-time.** A mechanism enters when the current or next gate's end-to-end run consumes it. Early machinery is a gate-ahead item (§4), never gate progress.
13. **Every work item ends with a run of the official entry point on the canary.** A module with no production importer is a defect, not a deliverable.
14. **A candidate is invalidated only by a change to an input it consumed.** Each bundle carries a per-candidate dependency manifest; no global control-plane hash exists.
15. **Validators and reviewers re-check; they do not invalidate.** Only a typed factual, safety, or protected-content failure invalidates; otherwise the result is `VALID_UPDATE_AVAILABLE`.
16. **Reviewer findings must be repairable.** A finding names a candidate section and a causal stage from a fixed vocabulary; anything else is advisory and never blocks twice.
17. **Governance stays compact.** `AGENTS.md` at most 200 lines, this document at most 500, at most eight gates. A new rule replaces an old one.
18. **One authority per fact.** Status lives only in `project/state.yaml`, sequence only here, the denominator only in the live registry. No other file holds a queue, plan, taskcard list, or status (AGENTS.md); a disagreement is a defect routed to the owning file.
19. **The acceptance contract freezes at G3 exit** as version 1 (§8 G3; revision 2 said G2, which its own exit predicates never required, F31) and changes only at declared version boundaries.

## 3. Authority and conflict resolution

Authority resolves by subject (AGENTS.md), not by rank. Sequence, gates, exit predicates, gate-ahead rule,
taskcards: this document. Status (current gate, queue, owner items, publication policy):
`project/state.yaml` only. Runtime states: `docs/STATE_MACHINE.md`. Candidate shape and the eleven
blocking checks: `docs/README_CONTRACT.md`. File locations: `docs/REPOSITORY_LAYOUT.md`. Threats:
`docs/THREAT_MODEL.md`. Legacy disposition: `migration/reuse-manifest.yaml`. Prompt manifests: `prompts/`
(never planning authority). Executor, lane, and supervision machinery: `project/loop-prompt.md`,
`project/loop-prompt-lane.md`, `tools/reviewer/procedure.md`, `docs/SUPERVISION.md`. Settled defect
priority: `docs/DEFECT_INDEX.md`. Decisions since a document was written: `docs/DECISION_LOG.md` §31.
Background, never a gate or queue: `docs/RESEARCH_AND_GUIDELINES.md` (its §27.9 queue text is pinned by
`tests/test_queue_agreement.py` until H-01) and `docs/PRODUCTION_ROADMAP.md`. Retired by H-01:
`plans/healing/*`, `plans/sprint/*` (PHASE1's deadline, 2026-09-15, is past), and
`project/loop-prompt-{phase0,sprint,lane-b}.md`.

`plans/idea.md` is the human product authority for outcomes and constraints, and owns no sequence or state;
§12 maps each of its obligations to a gate. If implementation proves a design assumption wrong, record
evidence, update the affected authoritative document and its tests in one change, and resume from the
earliest invalidated gate. Never create a competing plan.

## 4. Build-state overview

Research may run ahead. Building a later gate's machinery is allowed only as a **gate-ahead item**:
the cursor records it with its consuming gate, it counts toward no gate, and it is either wired to a
production importer or held dormant with a resume predicate (§2 rules 12-13). Revision 2 forbade
building ahead of the gate, and at least six landed items did so anyway (§13, F08); the gate-ahead
entry is now their record.

## 5. Durable implementation cursor

`project/state.yaml` is updated in the same commit as every accepted transition and is the only
status authority. Its vocabulary is the schema's, and this document matches it: current gate and
active item `READY | IN_PROGRESS | VERIFYING | ACCEPTED | BLOCKED_EXTERNAL | FAILED_INTERNAL`;
queued items `PENDING | BLOCKED_BY_GATE | COMPLETE`; owner items `OPEN | SATISFIED | OVERRIDDEN |
DEFAULT_APPLIED`. Work-item IDs (`G<n>-W<nn>`) are assigned by the cursor; this document never numbers
work. Each queued entry is one line of status, a resume predicate, and a consuming gate; history lives
in `docs/DECISION_LOG.md` §31 and gate manifests, not the cursor (revision 2's cursor was 283 lines of
prose; taskcard H-02). A gate-ahead item names its `consumed_by_gate`. At most one shared-code item is
`IN_PROGRESS`. A JSON Schema under `schemas/` validates the file in CI from G0 onward.

Gate identifiers: `G0_FOUNDATION`, `G1_FIRST_VALID_CANDIDATE`, `G2_STABILITY_UNDER_CHANGE`,
`G3_PYTHON_COHORT`, `G4_MULTI_LANGUAGE_COHORTS`, `G5_RERUN_DURABILITY_AND_HOSTED_OPERATION`,
`G6_PROPOSAL_EFFECT_PROOF`, `G7_PRODUCTION_AND_CONTINUOUS_OPERATION`.

**Owner-only predicates never live in a gate.** Branch protection, secrets, App installation, and
product decisions are `owner_items` with an exact resume predicate and the gate or work item that
consumes them. They hard-block only there, are re-checked every iteration, and a work item is
`BLOCKED_EXTERNAL` only when it itself consumes an unmet owner item. Everything else proceeds. Prose-only predicates
(G6's disposable target, the push policy, the outage policy; F11, F03, F26) are proposed as OWNER-11, -10, -12 (H-08, H-03, H-13).

## 6. Global execution loop

1. Observe the current gate; read the relevant code and evidence.
2. Select the smallest change that closes a predicate; implement it with focused tests.
3. Run the official entry point on the canary; if production behavior is claimed, run production-shaped proof.
4. Record evidence and commit. If predicates pass, advance the cursor; otherwise route the defect to its causal boundary and return to step 1.

Rules: inspect before replacing; change the smallest causal boundary; two equivalent failures or 15
minutes without narrowing force a first-principles review; unit tests never prove hosted workflows, live
gateways, Git safety, recovery, or GitHub effects; every commit names its gate and work item; never mutate
a target repository while proving read-only behavior.

Control-repository changes ship by branch and PR into `main`, protected since 2026-09-26 (OWNER-01: required
checks Python 3.11-3.13; auto-merge on). Direct pushes are retired; the cursor's `push: NEVER` contradicts AGENTS.md
and is open defect F03 until OWNER-10 is answered. `.githooks/pre-push` (needs `CI_TOOLS_VENV`) complements the
required checks. Never force; never a product repository. A red hosted run is `FAILED_INTERNAL` at the next iteration.

Next item, in order (F02): (1) a defect class with three independent sightings in `docs/DEFECT_INDEX.md`
(settled priority); (2) an open exit predicate of the current gate; (3) the lowest-numbered cursor queue
entry whose consumed owner items are satisfied. Gate-ahead items never outrank (1) or (2).

## 7. Legacy reuse protocol: pull-based

The legacy repository holds 171,345 lines of production Python, and its entry point imports 79% of it, so reuse
by entry point is impossible. A legacy file enters only when a gate needs it, with a manifest record, its tests,
and a cut closure. Each pulled file gets one disposition (`PORT_NEARLY_INTACT`, `EXTRACT_AND_REFACTOR`,
`ADAPT_AS_PLUGIN`, `FIXTURE_OR_ORACLE_ONLY`, `MIGRATION_READER_ONLY`); unpulled files are `RETIRE`. Dirty-tree
exclusions use `EXCLUDED_BY_DEFAULT_PENDING_OWNER_OVERRIDE` (33 records; F21), a reconciliation state, not a
disposition. Each record carries source path, SHA-256 at the frozen revision, disposition, destination, retained
and removed behavior and coupling, tests, and acceptance.

Pull rules: compute the import closure before pulling; a pull that drags a retired module or a
`supervisor`, `capabilities`, or `specialists` module fails until the chain is cut (known chains `CPL-01`
to `CPL-08`). Seam-cut order: shared identity types out of `capabilities/schema.py`; `sha256_text` out of
`readme/facts.py`; the validation ruleset version; then `llm/*`. Non-Python assets (prompt manifests,
registries, policy files, link data, benchmark profile, presentation standard, golden sample) are pulled
per asset with a record. The legacy suite is not green at the frozen revision (`RESEARCH_AND_GUIDELINES.md`
§16.9); record the Linux baseline before the first pull. The G4 exit census records totals by disposition;
no reuse percentage is claimed before it.

## 8. Gates

## G0 — Foundation

Goal: make the repository buildable, checkable, and protected in at most two working days, without
importing legacy runtime behavior or building speculative infrastructure.

### Work

1. Python 3.11+ `src/` package, `pyproject.toml`, lock file, CLI with `--version` and `status`.
2. Formatting, linting, typing, and unit-test CI on Python 3.11, 3.12, and 3.13.
3. JSON Schemas under `schemas/` for `project/state.yaml`, the reuse manifest, and the candidate
   bundle; CI validates the first two now.
4. Secret canary test proving configured secrets cannot enter a candidate bundle; `.env.example`
   names only (no `.env` is read): `GH_TOKEN`, `GPT_OSS_ENDPOINT`, `GPT_OSS_API_KEY`, `GPT_OSS_MODEL`
   (OWNER-02; the names `LLM_BASE_URL` and the like were revision 2's error, F07).
5. Path-budget test: no tracked path exceeds 200 characters.
6. Record the owner items (branch protection, gateway credentials, dirty legacy tree, GitHub
   App) with exact resume predicates; apply the recorded default for the dirty tree.

Explicit non-goals: decision-record folders, evidence frameworks, typed error taxonomies beyond what
the CLI needs, configuration precedence machinery, any legacy port.

### Exit predicates

- Clean environment installs from the lock; lint, format, types, tests pass on Python 3.11-3.13.
- CLI reports version, current gate, and the candidate count against the live denominator (§1).
- Schemas validate the cursor and manifest; canary and path-budget tests pass.
- The accepted commits reach `main` through a PR with required checks green (G0 was accepted by direct
  push before OWNER-01; its manifest records that, and the predicate is now PR-only).
- Owner items are recorded with exact resume predicates; none is consumed by G0.
- No legacy production file has been copied.

## G1 — First Valid Candidate

Goal: `repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python` produces a
concise, product-first candidate at
`candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/<revision>/README.md` with a sealed bundle,
and an immediate rerun is a zero-call no-op. This is the first milestone of the recovery direction:
one README that a human can open and judge.

### Work

The transaction is a linear pipeline with stage artifacts on disk. No durable multi-machine state,
leases, or hosted execution yet; those are G5.

1. **Snapshot.** Allow-list check against the registry, push-neutered clone at the pinned default-
   branch revision, exact README bytes, tree inventory. Pull `gitsafety/`, `repository_snapshot.py`,
   `inspection/`, `registry/loader.py`, `evidence/redaction.py`, `errors.py`, `retry.py`.
2. **Facts.** Distribution name, import path, exported symbols, Python range, verified executable
   examples, formats, license, and the material-unit inventory of the existing README, all as typed
   `facts.json` records with evidence IDs and polarity. Pull the Python consumer and example
   verifier as the first platform plugin behind a registry. A PSD-style README-only fixture returns
   `insufficient_evidence` with a resume predicate and zero LLM calls.
3. **LLM jobs** (the first item that consumes the gateway credentials owner item; items 1 and 2
   proceed without them). Governed prompt manifests for `repository_investigation`,
   `source_reconciliation`, `presentation_planning`, `section_authoring`, `independent_review`, and
   `targeted_repair`, one file each under `prompts/`, plus a `preflight` command that reaches the
   gateway without leaking the key and lists its model catalog; each prompt manifest's `model_route`
   is chosen from that catalog for job fit, never assumed (`RESEARCH_AND_GUIDELINES.md` §18.4). The
   transport is the `openai` SDK (§18.2) unless the gateway test documents a reason not to. The call
   ledger and schema (after the `CPL-01` cut) are project accounting the SDK does not replace. LLM prose
   may only express fact IDs supplied in its packet; deterministic code renders commands, links,
   badges, Mermaid, example code, and license identity.
4. **Composition** to `docs/README_CONTRACT.md`: the semantic shell in its §2, the assembly
   pipeline in its §3, and the agentic decisions in its §4. The LLM returns typed content units
   bound to fact IDs; the deterministic renderer emits the Markdown; one coherence pass may revise
   LLM-owned units only.
5. **Blocking checks:** exactly the eleven in `docs/README_CONTRACT.md` §5. Everything else is
   advisory until G3 freezes contract v1 (F31).
6. **Independent review** per `docs/README_CONTRACT.md` §4 and §6: separate prompt and identity;
   findings name a section and a causal stage; one targeted repair per equivalent fingerprint;
   unrepairable findings are advisory.
7. **Bundle.** `README.md`, `README.patch`, `facts.json`, `dispositions.json`, `plan.json`, `validation.json`,
   `review.json`, `calls.jsonl`, `dependencies.json` (exact hashes of every consumed input: source revision and
   tree, fact records, prompts, model route, component and validator versions, acceptance profile, protected-content
   fingerprint, policy), and `manifest.json` with checksums.
8. **No-op.** Fresh process, same inputs: same bytes, zero calls, ledger records cache reuse per job.
9. `status` prints the READY_FOR_PROPOSAL count against the live denominator (§1).

### Exit predicates

- A human can open the candidate at its stable path and it reads as a concise, product-first README
  for this repository, within budget, with every required section of the semantic shell present.
- All eleven blocking checks pass; review verdict is `ACCEPT`; no-op is proven in a fresh process.
- Every pulled legacy file has a manifest record and ported tests; every new module has a production
  importer; provider calls reconcile with the ledger.
- The PSD fixture yields `insufficient_evidence` with zero calls.

## G2 — Stability Under Change

Goal: the G1 candidate remains valid while the system evolves — the milestone the legacy never
reached — and the first-candidate causes of drift (`RESEARCH_AND_GUIDELINES.md` §27, §28) are closed.

### Work

1. Dependency evaluation from `dependencies.json`: a changed component reopens only its consumers,
   at the earliest affected stage, reusing unaffected work; corrupt or missing artifacts fail closed.
2. Change each dependency class in isolation — source revision, fact extractor, prompt, model route,
   template component, validator, reviewer rubric, link policy — and prove routing: presentation
   changes yield `VALID_UPDATE_AVAILABLE`; factual, safety, or preservation failures invalidate.
3. Inject one factual defect and one preservation defect; prove rejection and repair at the causal
   stage with accepted unaffected work retained; prove the two-attempt rule terminates honestly.
4. Grep-enforced test: no global control-plane hash anywhere in `src/`.
5. The first-candidate half of D1–D7 (§27.5, §28.5) on the canary: test fixture, constructive
   generation, title binding, content-only acceptance, coverage ledger; D3, D4, fan-out → G5, freeze → G3.

### Exit predicates

- The invalidation matrix is green; unaffected artifacts are reused; no global hash exists;
  injected defects are rejected and repaired at their causal stage.
- On the canary: the sealed composition accepts with zero blocking findings and zero required-row
  advisories; every job holds the 85 first-attempt floor (per-job thresholds need three sealed
  compositions, §27.10); the coverage ledger is in the bundle. The coverage-ledger check is promoted only under
  `README_CONTRACT.md`'s measured-defect rule; the blocking set is that contract's §5 rows, eleven (F16).

## G3 — Python Cohort and Contract Freeze

Goal: every processable Python repository has a candidate or an evidence-bound disposition, and the
contract freezes against thirteen sealed products rather than one (§28.5).

### Work

1. Python cohort: the twelve remaining Python registry entries through the existing pipeline, one
   transaction each; seal what passes all eleven checks; an evidence-bound disposition with a resume
   predicate for the rest (PSD-Python `NON_PROCESSABLE`, persisted per `STATE_MACHINE.md` §6; its producer
   does not exist yet, F06); fixes by failure class, a regression test each.
2. Freeze acceptance contract v1: ratify the landed advisory 30-point scorer (`components/readme/review/acceptance/scorer.py`, commit 12eefef1, wired in `repair/rounds.py`; F05) with its hard disqualifiers, the blocking checks,
   and the advisory set, each versioned in every bundle's `dependencies.json`.

### Exit predicates

- `status` prints the sealed count against the live denominator; the gate manifest carries the cohort report by
  repository (sealed, disposition, failure class); every sealed bundle is zero-call proven; v1 frozen.

## G4 — Multi-Language Cohorts, Local

Goal: a README for every enabled registry entry (`data/registry.json`, derived) and a disposition
for every registry entry, through one shared surface extractor and six thin plugins, before hosted machinery.

Mandatory truth per ecosystem: Python, distribution name, import path, exported symbols, Python range, extras,
executable example; .NET, NuGet identity, TFMs, namespaces, project references, native dependencies, compilable
C# example; Java, Maven coordinates, repository availability, JDK level, packages, dependencies, compilable example;
C++, compiler and standard, CMake or build files, includes, namespaces, linkage, compilable example; Go, module and
import path, Go version, exported API, dependencies, compilable example; Rust, crate identity, edition and MSRV,
visibility and re-exports, features, safety claims, compilable example; TypeScript, npm identity, exports and types,
runtime targets, ESM/CJS behavior, dependencies, compilable example.

### Work

1. Second reuse source (§29.6 E1–E2): aspose.org's extraction engine and tests, admitted under the pull discipline
   (pinned revision, file records, ported tests, minimal closure, never a runtime import) behind a `_vendor/` boundary with
   confined `mypy`/`ruff` overrides, recorded patches, and a typed `SurfaceExtractor` façade; census.
2. Layered plugins (§29.6 E3–E5): `EcosystemSpec` + one thin verifier + one negative control each;
   shared `RegistryProbe`; ecosystem-generic renderer, badges, Installation, fences, aliases, slugs. One item
   per ecosystem with its cohort: .NET (6), Java (4), C++ (4), TypeScript (2), Go (2), Rust (1); fixes by failure class.
3. Extractor parity per repository against the live README's API rows (§24); a shortfall routes to
   EXTRACTING; compiler-emitted corroboration (E6) is admitted per ecosystem only when parity fails.
4. Report separated counts against the live denominator. The registry revision in force at G4 exit is
   recorded in the manifest, not frozen (owner ruling 2026-09-30 reversed the 2026-09-23 freeze).

### Exit predicates

- `status` prints at least 20 current, reviewable, no-op-proven candidates sealed (2026-09-28 floor
  ruling, `docs/DECISION_LOG.md`); every verifier has a negative control; cohort reports and census
  in the gate manifest; parity recorded per repository in the manifest's parity table (F24).

## G5 — Rerun Durability and Hosted Operation

Goal: the sealed candidates stay byte-stable across reruns, revisions, and machines, then the
read-only transaction runs autonomously on GitHub-hosted runners (§27.5 D3, D4, D7).

### Work

1. Anchored canonical plans (D3), portable reproducibility with the fresh-state proof (D4), bounded
   fan-out inside a candidate; every candidate re-sealed byte-identically or with its recorded delta.
2. Durable runtime (`STATE_MACHINE.md` §13-§15): repository record with CAS, leases and fencing, trigger
   deduplication, recovery before scheduling, transition receipts; pull and slim the legacy state modules
   named in the manifest.
3. `monitor.yml` (schedule and manual dispatch, read-only) and `present.yml` (manual and
   repository_dispatch, one isolated job per repository). `act` proves `ci.yml` locally (commit 6de6c159);
   `present.yml` is hosted-only, so its proof is a hosted run on `main` with its run ID in the manifest
   (F12). Read-only App tokens; ambient tokens ignored; fail closed. Consumes OWNER-01 and OWNER-04.
4. Authorized discovery and intake (new repositories disabled and read-only, exclusions explicit);
   changed-or-due matrix; TTL-governed package and release surfaces, caches never authoritative;
   isolated lanes with bounded concurrency; adversarial audit; `BenchmarkQualityProfileV1` comparison.

### Exit predicates

- At least 20 candidates (G4's own floor) pass the fresh-state proof (empty `runs/`, fresh process,
  zero calls); an unchanged revision reuses every call and an unchanged hosted rerun makes zero
  provider calls, matching local execution; a synthetic upstream change schedules only the affected
  repository; the aggregate report reconciles with repository receipts.

## G6 — Proposal Effect Proof

Goal: prove automatic PR creation and maintenance against a disposable target with isolated
credentials, then qualify any sealed candidate from the Cells family, any platform (widened from
Java-only, 2026-09-28 — `docs/DECISION_LOG.md`).

### Work

1. `propose.yml` as a separately authorized write-capable workflow; exact authorization payload
   binding candidate hash, source revision, branch, PR intent, policy version, and expiry.
2. Fresh repository-scoped App token minted only inside the effect job; source revision rechecked
   immediately before the effect; one stable presenter branch and PR per target.
3. Update rather than duplicate; reconcile lost responses before retry; upstream README overlap
   returns to reconciliation; merged and closed-unmerged outcomes observed without recreation.
4. Kill switch and rollback (F10): a write runs only while its `REPOSITORY_PRESENTER_*_WRITE_AUTHORIZED` is `1`.
   Rollback closes the presenter PR, deletes its branch, and writes a receipt, under its own authorization (H-09).

### Exit predicates

- Disposable PR created and updated with exact effect evidence; the analysis token cannot write;
  stale source blocks the effect; repeated invocation creates no duplicate; lost-response simulation
  reconciles; no default-branch push exists; rollback is exercised once on the disposable target that
  OWNER-11 names (H-08).

## G7 — Production Readiness, Deployment, and Continuous Operation

Goal: harden for unattended operation, enable it on the approved repository and App installation,
then keep the system useful without weakening the README foundation.

### Work

1. Threat model (`THREAT_MODEL.md`); failure exercises (leases, crash recovery, duplicate triggers,
   corrupt state, gateway and GitHub outages, rate limits, matrix partial failure), each with a recorded
   outcome labelled unit-level or hosted; dependency locking, SBOM, vulnerability audit; budgets, health,
   alerts naming the causal repository, dead-man monitoring; App permissions, rotation, rollback.
2. Upstream-defect handoff for a confirmed product defect (seed: Email .NET `CS1929`): evidence-backed,
   deduplicated, never a fabricated severity; automated later behind its own authorization.
3. Deploy: App and gateway secrets; scheduled monitor in read-only observation; hosted output compared
   with accepted local bundles; automatic PR mode for the cohort G6 admitted (the Cells family, any
   platform; F23), with fresh effect authorization, expanding only after observed stability.
4. Operate: monitor quality, cost, repair rate, drift, proposal acceptance, and time to update; refresh
   prompts and routes only at declared version boundaries; admit new repositories disabled and read-only
   (one plugin, one test, one registry entry); add the other surfaces as separate machines; Level 7 and 8.

### Exit predicates

- Security suite and failure exercises pass; no write credential in analysis jobs; state survives
  runner loss; hosted monitoring runs unattended; approved repositories receive safe proposals after
  drift; unchanged repositories incur no LLM work; `delivery_complete` (`plans/idea.md`: executable work
  through deployable Level 6, F23) closes the gate and `certification_complete` the background tracks.
  Operating objectives: drift to accepted proposal within 24 hours of `monitor.yml` observing it, from
  its receipts (F24); no unsupported claim, inherited-content loss, duplicate PR, or halt.

## 9. Gate failure routing

| Failure | Route |
|---|---|
| Pulled legacy code drags retired machinery | Cut the seam or reimplement the narrow contract; never widen the pull. |
| Custom gateway malformed output | Tighten the typed job schema or prompt, or change the routed model; never weaken validation. |
| Facts incomplete, or candidate generic, too long, or missing source material | Improve deterministic extraction or evidence tools; reopen investigation, planning, or reconciliation and disposition mapping; enforce the budget; never polish prose only. |
| Example does not compile or run | Reopen example selection; never explain it away in prose. |
| Reviewer rejects | Route the typed defect to its causal stage; an unrepairable finding becomes advisory and reviewer scope is fixed. |
| Candidate invalidated by a component it did not consume | Fix the dependency manifest; never widen invalidation. |
| Validator change fails accepted candidates on presentation only | Emit `VALID_UPDATE_AVAILABLE`; never invalidate. |
| No-op invokes the LLM | Fix dependency identity, cache, or state; never exempt the call. |
| Module has no production importer, or governance or module growth exceeds budget | Wire or delete it in the same work item; remove, do not document around it. |
| Hosted state missing, or GitHub effect uncertain | Fix the durable backend, caches cannot substitute; reconcile the remote branch and PR before retrying. |
| Owner item unmet | Skip only the work items that consume it; record the exact action; never wait on anything else. |
| Internal bug blocks progress | `FAILED_INTERNAL`; repair and resume; never acceptable completion. |
| Machinery built ahead of its gate, or unwired | Record a gate-ahead item with `consumed_by_gate`; it counts for no gate; wire it or hold it dormant (F08). |
| Hosted write must stop, or a PR is wrong | Unset its `WRITE_AUTHORIZED` variable; roll back per G6 item 4; write a receipt (F10). |
| Two authorities disagree | The authority that owns the subject wins (§3); fix the other in the same commit; never pick silently (F01, F03). |
| A count appears in prose | Delete it; counts come from the registry and the cursor (F04). |

## 10. Evidence

Each accepted gate writes `evidence/build/<gate-id>/manifest.json` (revisions, exact commands and exit statuses,
test results, proof identity, artifact hashes, LLM call summary, predicate verdicts, next work item). Candidates'
sealed bundles are the evidence. Evidence is redacted, checksum-valid, and reproducible; no schema validates gate
manifests yet (H-07, F13). A hosted claim cites a run ID on `main`; a wiring claim cites an assertion test; a
unit-level exercise is labelled so (F12). No-op and fresh-state proofs show replay of recorded responses, not
regeneration (F24).

## 11. Definition of done

Complete when: the repository is independent of the legacy and Aspose.org trees at runtime; scheduled hosted
monitoring covers the admitted portfolio; every processable repository has a current independently accepted
candidate; every unchanged accepted repository proves zero-call idempotency; changes reopen exactly the affected
work; LLM investigation, planning, composition, review, and repair are live and attributable; PR creation and
update run through the isolated App effect job; placeholders and unresolved facts fail honestly; recovery,
concurrency, stale authorization, and lost-response behavior are proven; and no routine human initiation or
template selection is needed.

## 12. Product-outcome coverage of `plans/idea.md`

| Obligation in `plans/idea.md` | Gate | Note |
|---|---|---|
| Product explained before promotion; contextual Aspose links within configured-or-derived ceilings; "Enterprise Edition" only; below-the-fold **full-featured ... Enterprise Edition** anchor | G1 | Blocking check; legacy `links/allocation.py` behavior pulled. |
| Presentation contract: one H1, badge row, canonical product name, title case, abbreviations, At a Glance topology and column rules, visible-versus-collapsible rules, Third-Party Notices, license prose, no internal narration | G1 essential subset, G2 full | Ported from the legacy template registry and presentation standard. |
| Search-intent vocabulary as corroborating evidence with output lineage, never repeated across headings | G2 | The legacy tests for this are red at the frozen revision. |
| Exactly one disposition per material source unit; LLM reasoning mandatory; every call attributable; zero-call no-op; small governed prompt registry | G1 | Blocking checks, six prompt manifests, ledger, fresh-process replay. |
| System decides product and platform; ecosystem truth includes the public consumer surface | G1 (Python), G2, G4 (all) | Plugin registry and platform verifiers with negative controls. |
| Aspose.org and sibling assets are oracles, never runtime dependencies; benchmark quality profile met or exceeded (`BENCHMARK_REFRESH_AVAILABLE`) | G1 rule, G4 pull, G5 benchmark | Fixture-only, plus file pulls with records and tests in G4, never a runtime import; benchmark comparison is development-only. |
| 30-point acceptance, zero hard disqualifiers, criterion-specific evidence | G3 | Advisory scorer landed and wired (`review/acceptance/scorer.py`; `repair/rounds.py`); unratified, so ratification is G3 item 2 (F05). |
| Independent non-authoring review; second reviewer only on typed trigger | G1 | Hard invariant. |
| Complete authorized discovery; hard allow-list; frozen registry revision; new repositories disabled and read-only; explicit exclusions | G4 registry freeze, G5 intake | Registry modules pulled and refactored. |
| README-only placeholders end `insufficient_evidence` and persist `NON_PROCESSABLE` with resume predicates (§2 rule 6) | G1 fixture, G3 and G4 PSD | Zero LLM calls. |
| Versions freeze, design does not; component invalidation scopes; `VALID_UPDATE_AVAILABLE`; drift detection and protected content as a durable control; portfolio reporting with separated counts | G2, G4, G5 | Per-candidate dependency manifests; broader-than-SHA freshness; health report. |
| Autonomous hosted operation with schedules, triggers, and recovery; `act` local testing with `GH_TOKEN`; GitHub App only in production, fail closed | G5 | Two workflows, `act` proof, token boundary. |
| Separate analysis and write credentials; PR-only publication; recheck before effect; Cells-family repositories (any platform, widened from Java-only 2026-09-28) as the first verified-proposal cohort | G6, G7 | Disposable target; after disposable proof and fresh authorization. |
| Other surfaces (description, topics, visuals, social preview, community files, release links); upstream defect reporting; Level 7 and 8 certification | G7 | Deferred by `plans/idea.md`; seed case `CS1929`; background tracks. |
| Two-attempt rule; serial calibration with at most three disjoint workers; battle-tested libraries | `AGENTS.md`, `project/state.yaml`, principle 10 | Governance and execution limits; at most three disjoint workers (the cursor's "up to 4" is corrected by H-05, F16). |
| Baseline figures are dated observations | G4 | 34 entries at `a8a163f7` (a dated observation); the live denominator is the registry's own count (§1), not frozen. |

## 13. Plan forensics, revision 3 (2026-10-04)

Method, severity scale, root causes RC-1 to RC-7, per-finding six-part causes, and the verified-sound list are in
`docs/DECISION_LOG.md` §31, entry 2026-10-04 (the 500-line cap leaves no room here).

| ID | Sev | § | Finding (evidence) | Heal |
|---|---|---|---|---|
| F01 | Critical | §3 | Competing plan channels: `plans/healing/*` (9 files, "supersedes nothing"), `plans/sprint/*` (deadline passed), three `project/loop-prompt-*` files, RESEARCH §27.9 queue; the healing and sprint lineage is undeclared; AGENTS forbids all of it. | §3 done; H-01 |
| F02 | Critical | §5, §6 | Cursor vocabulary (COMPLETE, owner statuses, W-IDs) absent from revision 2; the cursor is 283 lines of prose with unenforced size (F14) and a "PRIORITY n" selection the plan never stated (F18). | §5, §6 done; H-02 |
| F03 | Critical | §6 | Publication contradiction: cursor `push: NEVER`; AGENTS allows a push after `ci_check`; revision 2 allowed direct `main` pushes; `main` protected since 2026-09-26. | §6 done; H-03 |
| F04 | High | §1, §8, §12 | Restated counts (0/34, 1/34, 12/34, 36/36, "frozen at G4") while the cursor and registry are 36 (owner ruling 2026-09-30); `cli.py` docstring says N/34. | done; H-06 |
| F05 | High | §8 G3, §12 | Scorer marked NOT IMPLEMENTED; it is wired (`repair/rounds.py`, `bundle/seal.py`) and advisory, unratified (commit 12eefef1). | done; H-11 |
| F06 | High | §2, §8 | Placeholder outcome: STATE_MACHINE §6 `NON_PROCESSABLE` versus AGENTS and CLI `insufficient_evidence`; the persisted disposition has no producer (cursor-known gap). | §2 done; H-11 |
| F07 | High | §8 G0 | Gateway names wrong: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; code and `.env.example` use `GPT_OSS_*`. | done |
| F08 | High | §4, §5, §9 | Build-ahead: state backend (G5-W04), G6 write paths, threat model, SBOM, and rotation runbook landed under G3; gate accounting inconsistent (accepted G0-G2, G3 and G4 manifests READY, G4 item active). | §4, §9 done; H-07 |
| F10 | High | §8 G6 | No rollback, revert, or kill switch for hosted writes; "rollback" appeared only as a G7 bullet. | G6 item 4 done; H-09 |
| F11 | High | §5, §8 G6 | G6 needs an owner-named disposable target (STATE_MACHINE §12.1); no owner item exists; the predicate lived in prose. OWNER-04 is 14 of 15 orgs installed and OPEN/SATISFIED cannot express partial satisfaction (F11 also covers it). | §5 done; H-08, H-14 |
| F12 | High | §8 G5, §10 | Wiring claims wrong or overstated: `present.yml` "proven under act" (commit 6de6c159 records a hosted-only gap); monitor triggers listed that do not exist; "exercised for real" was unit-level; cursor said lockdrift and sbom do not gate (the CI Summary step fails the job on them). | done; H-05, H-10 |
| F13 | High | §10 | No schema validates gate manifests; G3 and G4 manifests are stale. | §10 done; H-07 |
| F16 | Medium | §8 G2, §12 | Exit cites "check 12", which §5 does not define (eleven rows); the cursor's "up to 4" workers conflicts with the plan's three. | done; H-05 |
| F17 | Medium | §3 | Governance tests pin prose: cursor queue to RESEARCH §27.9, a test to the sprint plan, ESM residues recorded as xfail. | H-01, H-01 |
| F20 | Medium | §14 | Taskcards required by the owner did not exist, and no status vocabulary was defined for them. | §14 done; H-00 |
| F21 | Low | §7 | Reconciliation state `EXCLUDED_BY_DEFAULT_PENDING_OWNER_OVERRIDE` (33 records) was undocumented. | §7 done |
| F23 | Medium | §8 G7 | `delivery_complete` and Level 7 and 8 used as gate terms without `plans/idea.md`'s definition; G7's automatic PR mode said "the Java cohort" while G6 admits any Cells candidate (F15). | G7 done |
| F24 | Medium | §10, §8 G4, G7 | Hidden assumption: no-op and fresh-state proofs replay recorded responses, not regeneration; predicates such as "one daily cycle" and "parity recorded" name no artifact. | §10, G4, G7 done; H-16 |
| F26 | High | §5, §9 | One gateway model route; no declared outage behavior; repeated qwen3-next outages recorded in the cursor. | §5 done; H-13 |
| F30 | Medium | §8 G4 | The "2026-09-28 floor ruling" the G4 exit cites was not located by text search in `docs/DECISION_LOG.md`. | H-16 |
| F31 | Medium | §2, §8 G1 | Contract freeze stated at G2 exit (revision 2's principle 23, now 19) while G3 owns it. | done |

## 14. Taskcards (revision 3)

Owner-brief statuses are a revision-3 snapshot; live status is the cursor's. OWNER-10 to -12 are proposed until H-02 records them.

| ID | Status | Objective (findings) | Validation and evidence | Rollback |
|---|---|---|---|---|
| H-00 | validation | Revision 3 of this document, within 500 lines; the budget note lives in DECISION_LOG (F20, F25) | governance budget test; PR checks on `main` | revert the PR |
| H-01 | backlog | Retire `plans/healing/*`, `plans/sprint/*`, `project/loop-prompt-{phase0,sprint,lane-b}.md`; repoint the PHASE1 reference in `tests/test_governance_consistency.py`; rewrite the queue oracle to the cursor (`tests/test_queue_agreement.py`; F01, F17) | grep finds no authority reference; suite green | revert |
| H-02 | backlog | Cursor to schema vocabulary, one-line entries, history moved to DECISION_LOG, size rule with a test (F02, F14, F18) | cursor and queue tests green | revert |
| H-03 | blocked: OWNER-10 | Cursor `publication.control_repository` set to the owner's answer, matching AGENTS.md (F03) | schema and `test_cursor` | revert |
| H-05 | backlog | Correct cursor claims: G7-W02 gating, present under `act`, G7-W05 wording, scorer, "check 12", "up to 4" (F12, F16, F16) | each claim cites a file or run | revert |
| H-06 | backlog | `cli.py` N/34 docstring; test that status denominator equals registry entries (F04) | mutation: add an entry, test fails | revert |
| H-07 | backlog | `schemas/gate-manifest.schema.json`; gate-ahead register in cursor; G3 and G4 manifests refreshed (F08, F13) | CI validates every manifest | revert |
| H-08 | blocked: OWNER-11 | Owner names the disposable G6 target; OWNER-11 SATISFIED (F11) | owner-item predicate | none |
| H-09 | backlog, G6 | Rollback runbook and kill-switch tests: close PR, delete branch, unset variable, receipt (F10) | rollback exercised on the disposable target | the rollback itself |
| H-10 | backlog | `monitor.yml` triggers: add `workflow_call` or correct the text; test asserts the trigger set and the CI Summary gating (F12) | test; hosted run | revert |
| H-11 | backlog, G3 | NON_PROCESSABLE producer for a README-only fixture; ratify the scorer as contract v1 (F05, F06) | fixture yields `NON_PROCESSABLE`; v1 frozen | revert |
| H-13 | blocked: OWNER-12 | Gateway outage policy: fail closed, or a fallback route re-reviewed (F26) | G7 failure exercise expects the declared behavior | none |
| H-14 | blocked: OWNER-04 | Install the App on `aspose-html-foss`; fresh audit shows 15 of 15 (F11) | audit workflow run | none |
| H-16 | backlog | Measurement sources: G4 parity table, G7 cycle receipts, regeneration variance beside replay proofs (F24); the floor ruling text is located or G4's exit wording corrected (F30) | manifests carry the fields | revert |
