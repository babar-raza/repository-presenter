authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Survey 4 - validation, review, repair, bundle, issues, metadata, monitor, propose

Read-only survey of `src/repository_presenter/components/` (paths below are relative to that directory unless prefixed `src/` or `core/`). Everything was verified from code; docstrings were treated as hypotheses. Line numbers are from the checkout as of 2026-10-10.

Registry (data/registry.json): 36 entries, 34 `dry_run`, 2 `full` (aspose-3d-foss/Aspose.3D-FOSS-for-Java, aspose-cells-foss/Aspose.Cells-FOSS-for-Java). Committed `candidates/`: 30 CURRENT bundles, 29 READY_FOR_PROPOSAL, 1 VALID_UPDATE_AVAILABLE (Slides-Java). Most committed bundles were sealed under VALIDATOR_VERSION 3-7; code is at "15".

---------------------------------------------------------------------------------------------------

## 0. File inventory

Format: purpose; public API; production importer; versions.

### readme/validation/
- `validation/__init__.py`, `validation/links/__init__.py`, `review/__init__.py`, `review/acceptance/__init__.py`, `review/independent/__init__.py`, `repair/__init__.py`, `bundle/__init__.py` - 1-line package markers.
- `validation/registry.py` (2244 lines) - Stage S9: the BLOCKING_CHECKS registry (12 checks), the `Candidate` input record, `validate_candidate`, plus coverage ledger, advisory notes, and the BC-10/BC-11 verdict recorders. Public: `BLOCKING_CHECKS`, `Check`, `Failure`, `Candidate`, `validate_candidate` (2003), `record_review_verdict` (2101), `record_replay_verdict` (2197), `blocking_failures` (2225), `summarize_validation`, `write_validation` (2237), `advisory_notes` (1894), `coverage_ledger` (1931), `coverage_rows` (1948), `protected_fragments`/`protected_fingerprint` (1803/1832), `canonical_name_pattern` (1173), `narration_patterns` (576), `deferred_on_required_rows` (2076). Importers: `repair/rounds.py`, `bundle/seal.py`, `review/acceptance/scorer.py` (BLOCKING_CHECKS), `issues/redetect.py` (BLOCKING_CHECKS versions), `cli.py` (VALIDATOR_VERSION, blocking_failures). Versions: `VALIDATOR_VERSION = "15"` (134) -> validation.json:2060, dependencies.json `validator_version` (seal.py:304), `stale_candidates` (cli.py:2221); per-check `Check.version` -> dependencies.json `validators` map (seal.py:303).
- `validation/deferrals.py` (317) - deferral policy: classifies each DEFER_UNRESOLVED disposition into BLOCK/ADVISORY classes (10 classes, first match wins, unmatched = BLOCK). Public: `review_deferrals`, `DEFERRAL_CLASSES`, `DeferralContext`, `DeferralFinding`. Importers: `registry.py` (BC-05, advisory notes), `repair/rounds.py` (feeds the second-reader trigger). No own version constant (changes ride VALIDATOR_VERSION/BC-05 version).
- `validation/links/rules.py` (131) - pure rules for BC-06 Aspose-link ceilings / Enterprise anchor and BC-07 badge row. Public: `readme_link_budget`, `badge_slot`, `badge_problems`, `enterprise_anchor_problems`, `verified_example_hashes`. Importer: `registry.py` only. No version.

### readme/review/
- `review/independent/review.py` (2051) - Stage S10: reviewer packet, deterministic fold stack that decides which LLM findings block, second/third reader mechanics, and review.json document. Public: `review_packet` (268), `blocking` (301), `second_read_decision` (338), `second_reader`/`third_reader` (379/397), `review_checks` (1531), `scope_defect` (1716), `review_document` (1782), `quote_located` (245), `write_review` (2044), many `*_defect` folders. Importers: `repair/rounds.py`, `repair/targeted.py` (circular-ish: review imports `defect_fingerprint` from targeted; targeted does not import review), `bundle/seal.py` (REVIEWER_LOGIC_VERSION), `cli.py`. Versions: `REVIEWER_LOGIC_VERSION = "17"` (157) -> dependencies.json `components.reviewer_logic` (seal.py:301) -> scope `reviewer`, stage override COMPOSING (invalidation.py:158). Prompt `independent_review.yaml` version "11" is a separate input (`prompts.independent_review`).
- `review/acceptance/profile.py` (480) - ADVISORY, UNRATIFIED 30-point acceptance profile (26 criteria C01-C26, 14 disqualifiers D01-D14). `RATIFIED = False` (41), all `points=None`. Importers: `bundle/portfolio.py` (RATIFIED), `bundle/seal.py` (PROFILE_VERSION="1" -> `acceptance_profile_version`), `scorer.py`.
- `review/acceptance/scorer.py` (285) - `score_candidate(readme, validation, review)` writes `review["acceptance_profile"]` (rounds.py:580). Never blocks. `SCORER_VERSION="1"` recorded only in review.json, not in dependencies.json.
- `review/acceptance/text_checks.py` (379) - 12 regex predicates over the README text (single_h1, single_badge_row, edition_name, assurance_narration, ...). Importers: scorer, template_check.
- `review/acceptance/template_check.py` (168) - D14 mechanical-template-filling checker. **ORPHAN in src/** (only tests import it; its own docstring says "not wired into the scorer"). D14 is `Evaluator("unevaluated")` in the profile.

### readme/repair/
- `repair/rounds.py` (1094) - one composition round `run_round` (S3-S10) and the bounded loop `run_transaction`. Public: `TransactionInputs`, `Round`, `run_round` (326), `round_defects` (599), `repair_defect` (838), `escalate_to_plan` (1005), `composition_id` (1042), `run_transaction` (1059). Importer: `cli.py` (via `_run_present`, cli.py:2762). No version constant.
- `repair/targeted.py` (971) - S11 targeted repair: Defect routing, fingerprinting, `RepairLedger` (repairs.json), repair packet/schema/checks. Public: `Defect`, `SlotSetProbe`, `review_defects` (176), `validation_defects` (262), `merge_equivalent`, `RepairLedger`, `repair_packet`, `repair_checks`, `MAX_ROUNDS = 3` (43). Importers: rounds.py, review.py. Version: `REPAIR_LOGIC_VERSION = "1"` (358) - used only inside repairs.json attempts (targeted.py:398,421); **not** part of dependencies.json (a repair-behaviour change does not mark any sealed candidate stale).

### readme/bundle/
- `bundle/seal.py` (1147) - S12: seals a transaction into a content-addressed bundle, proves the no-op, records updates/invalidations. Public: `SealInputs`, `SealResult`, `seal_candidate` (986), `invalidates` (940), `invalidate_bundle` (950), `code_dependencies` (278), `upstream_dependencies` (310), `dependencies_document` (335), `seed_call_store` (635), `seed_additional_calls` (690), `sealed_models` (500), `bundle_directory` (206), `record_upstream_blobs` (210). Importer: `cli.py`. Version: `CONTRACT_VERSION = "readme-contract-v1"` (117) -> `contract_version` -> scope `validator`; `ACCEPTANCE_PROFILE_VERSION` (123).
- `bundle/invalidation.py` (246) - scope table (8 scopes), `route()`, dependency/prompt/component -> scope maps. Importers: seal.py, evaluation.py, dry_run.py, cli.py.
- `bundle/evaluation.py` (212) - `evaluate(sealed_deps, current_deps)` -> `Evaluation(changes)`; writes evaluation.json. Importers: cli.py, dry_run.py.
- `bundle/dry_run.py` (174) - `portfolio_routing` (what each CURRENT bundle would become under running code, pure read), `held_updates`. Importer: cli.py (status).
- `bundle/portfolio.py` (445) - the seven cumulative counts + partition buckets (`assess_portfolio`), `load_drift`, `load_authorizations`. Importer: cli.py (status).
- `bundle/reproducibility.py` (119) - `reproducible_repositories`: re-renders README from facts/plan/units/dispositions and byte-compares. Importer: cli.py (status).

### issues/
- `issues/__init__.py` (44) docstring only.
- `issues/model.py` (182) - typed `Handoff` for `evidence/upstream-defects/<owner>__<name>/<hex>.json` (statuses HANDOFF_PENDING/HANDOFF_ACKNOWLEDGED/FILED/RESOLVED_UPSTREAM). Used by all siblings + cli.
- `issues/ledger.py` (104) - dedup ledger is a read layer over the handoff files; fail-closed on duplicates.
- `issues/draft.py` (188) - automatic handoff drafting from `run_present`. Importer: cli.py:2811.
- `issues/redetect.py` (444) - registry of redetectors (`BC-02`, `NOT_PROCESSABLE`), `_propose_close_reason`, `apply_redetection`. Importers: file.py, cli.py.
- `issues/approval.py` (294) - per-handoff approval record + `GitApprovalStore` (reads a git ref, rejects bot authors, rejects shallow clones).
- `issues/close_approval.py` (215) - per-issue close approval (exact issue number + reason).
- `issues/file.py` (571) - the gated write half: `file_handoff` (270), `close_handoff` (492), `plan_filing`, `plan_close_gated`. Imported as `issues_file` by cli.py (my importer grep missed it because of the alias; it is live).

### metadata/
- `metadata/__init__.py`, `capture.py` (50: GET repo metadata, read-only), `preservation.py` (291: deterministic weak/strong rules, topic merge/removal), `proposal.py` (384: derive description/topics/homepage from facts + sealed README, diff vs observed), `apply.py` (285: gated PATCH/PUT). Importer for all: cli.py `run_metadata` (1758). No version constants.

### monitor/
- `monitor/__init__.py`, `drift.py` (325: head vs CURRENT bundle revision + upstream blob drift; `assemble_drift_contract` merges owner evidence into the sealing contract with 12h max age), `install_state.py` (246: GitHub App installation classification via openssl-signed JWT). Importer: cli.py (`monitor`, `monitor-install-record`, `monitor-install-summary`, `monitor-drift-contract`). `drift.py` feeds `core/sealing_plan` (via cli `monitor-drift-contract`).

### propose/
- `propose/__init__.py` docstring only; `propose/effect.py` (440): `propose_candidate`, `write_authorized`, `PRESENTER_BRANCH`. Importer: cli.py `run_propose` (1888).

---------------------------------------------------------------------------------------------------

## 1. Blocking and advisory checks

### The battery
`validate_candidate(candidate: Candidate, transaction: Path, secrets: Sequence[ConfiguredSecret])` (`validation/registry.py:2003`). It maps check id -> judge function (2014-2025); BC-10 and BC-11 are not run there, they are written PENDING with `judged_at` S10/S12 (2037-2039). It is called once per round inside `run_round` (`repair/rounds.py:507-523`) BEFORE the reviewer, and the reviewer runs only if no deterministic check fails (rounds.py:539-541). BC-10 is then filled by `record_review_verdict` (rounds.py:577) and BC-11 by `record_replay_verdict` at seal time (seal.py:894/1133).

Inputs (`Candidate`, registry.py:396): registry `entry`, `FactsDocument`, `plan`, `units` (content_units), `dispositions`, `readme` text, `original_readme` bytes (optional), `source_revision`, `readme_sha256`, `tree_paths`, `tasks` (list of `SectionTask`, from `authoring_tasks(entry, facts, investigation, dispositions, plan)`), `policy`. Plus `transaction` dir + env-configured secrets for BC-09.

The docstring says "exactly the eleven blocking checks" (registry.py:3) but the registry holds twelve (BC-01..BC-12). Stale docstring.

### Table (version = `Check.version` at registry.py:185-377)

| Check | v | What it verifies | Judge (line) | Deterministic? | Clone/network/toolchain at check time? | Runnable on sealed bundle bytes? |
|---|---|---|---|---|---|---|
| BC-01 | 1 | facts.json revision == snapshot revision; `identity:revision` fact; original README sha256 == snapshot digest; every fact has evidence | `_check_source` 727 | yes | no | Mostly. Needs `original_readme`+`readme_sha256` for the digest clause (skipped silently when `original_readme is None`, 743); original is recoverable by reverse-applying README.patch, digest only from the transaction's snapshot.json |
| BC-02 | 4 | install_command facts: SUPPORTED, manifest + (registry or verified source build or source_checkout), no "distribution not found" on registry kind, build steps match receipt, install fence rendered | `_check_install` 760 | yes, but keyed on substrings of evidence `detail` text ("manifest", "package registry", "verified source build", "distribution not found") 771-810 | no | yes (facts + README only). The facts were produced earlier by network/toolchain extraction, but the check re-reads only stored facts |
| BC-03 | 2 | each planned example fact has `: EXECUTED`/`: COMPILED` in evidence detail (416, 854-858); every fence in the ecosystem's example languages equals a planned verified body | `_check_examples` 831 | yes (evidence-string marker) | no | yes |
| BC-04 | 2 | every unit cites existing SUPPORTED facts; `unit_checks` per task; every backticked span outside fences is a fact value/identifier/member | `_check_units` 884 | yes | no | yes (needs `tasks`, hence investigation.json; present in all 30 CURRENT bundles) |
| BC-05 | 2 | each inherited unit exactly one disposition; placed units render in destination; DEFER_UNRESOLVED judged by `deferrals.py` class (BLOCK vs ADVISORY) | `_check_dispositions` 974 | yes | no | yes |
| BC-06 | 7 | anchors resolve; relative links resolve against `tree_paths`; external links must be verified `link_target` facts (SUPPORTED) or renderer-owned; Aspose link ceilings (total/domain/slot); Enterprise anchor text; edition substitutes; unsafe HTML/dangerous scheme outside fences | `_check_links` 1252 | yes. No live HTTP: external links are judged by stored link_target facts | no network. Needs `tree_paths` for relative links (1279) | Almost. `tree_paths` is not in the bundle (source/tree.txt lives only in runs/transactions); everything else is |
| BC-07 | 10 | one H1; one badge row in stable order with each badge verified; title-case headings; canonical abbreviations; At a Glance topology; fence languages/spacing; no collapsed visible sections; no internal narration; visible-line budget; Core API table row count | `_check_structure` 1542 | yes | no | yes |
| BC-08 | 2 | commands/examples/verbatim-placed units of the original README preserved in the candidate | `_check_protected` 1840 | yes | no | yes (uses inherited_unit facts, not the original bytes) |
| BC-09 | 1 | no configured secret value in the bundle dir | `check_secrets` 2008 (closure) | yes | needs process env secrets + transaction dir | yes only if secrets are supplied |
| BC-10 | 5 | independent review ACCEPT, corroborated by a second read when the typed trigger fires, reviewer identity != authoring, no unrefuted advisory on required row | `record_review_verdict` 2101 | verdict assembly deterministic; findings come from an LLM | judged from review.json | Verdict re-derivation from review.json: yes. Re-folding the raw reviewer reply: only for the 5 bundles that have raw_calls.json (see section 2) |
| BC-11 | 2 | fresh-process rerun, byte-identical, zero provider calls measured from ledger | `record_replay_verdict` 2197, seal.py | yes | needs a fresh process rerun (LLM store replay, clone) | not offline-recheckable (it is a process fact) |
| BC-12 | 1 | every product-name position spells the canonical name exactly (no separator/case/suffix variants) | `_check_canonical_name` 1217 | yes | no | yes |

Other registry outputs: `coverage_ledger` (1931, per shell row which fact kinds resolved - informational), `advisory_notes` (1894: ADVISORY deferrals, BC-12 elisions, rewrite-dropped code spans) - context for the reviewer, never a verdict.

### Advisory (non-blocking) machinery
- Acceptance profile/scorer (`review/acceptance/*`): 26 criteria + 14 disqualifiers, evaluators `check` (reads BC verdicts), `text` (regex predicates), `review` (8 criteria), `unevaluated`. Output in `review.json["acceptance_profile"]`, `advisory: true`, `ratified: false`, outcome UNSCORED/INCOMPLETE/... The only consumer is `bundle/portfolio.py`'s `publication_eligible` stage (portfolio.py:314). Deterministic, offline.
- Deferral ADVISORY classes (deferrals.py): INTERNAL_DETAIL, UNVERIFIED_EXAMPLE, ENTERPRISE_NO_VERIFIED_TARGET, ENTERPRISE_NON_PROSE, EXCLUDED_BY_PLAN, SECTION_ABSENT, LEADIN_OF_WITHHELD_CONTENT. BLOCK classes: NO_VERIFIED_QUICK_START, BUILD_TEST_PATH_UNRECORDED, NOTICES_WITHOUT_RECORD, plus UNCLASSIFIED.
- Reviewer advisories (`review["advisory"]`): findings that folded to "reviewer-scope defect" or single-reader advisory.

### Offline "recheck over sealed bytes": feasibility
`validate_candidate` is a pure function of its arguments (no I/O except BC-09's directory scan). `bundle/reproducibility.py:57-119` already shows the recipe for loading a bundle offline (facts.json -> FactsDocument, `find_entry` from data/registry.json, plan.json, content_units.json, dispositions.json). Missing pieces for a full recheck:
1. `tree_paths` (BC-06 relative links) - not sealed. Could be approximated from facts but not exactly.
2. `tasks` - derivable from investigation.json, which IS sealed in all 30 CURRENT bundles.
3. original README bytes (BC-01 digest) - recoverable from README.patch but the snapshot digest is not sealed.
4. BC-09 secrets - env only.
Nothing in the code today performs such a recheck: grep shows `validate_candidate` is called only from rounds.py (and tests). Re-validation currently requires a full `present` run (clone + build/example verification + extraction + LLM replay). `tools/reviewer/audit_*.py` (outside this slice) do five bundle-only audits (link completeness, preserved API lists, install claims, format claims, second-reader ledger) and `tests/test_sealed_bytes.py` re-renders every CURRENT README.

---------------------------------------------------------------------------------------------------

## 2. Independent review (BC-10)

Flow (`repair/rounds.py:543-596`):
1. `review_packet` (review.py:268) hands the LLM the original README, candidate README, bounded facts (SUPPORTED/CONTRADICTED/UNRESOLVED, excluding inherited_unit), plan, dispositions, and the validation checks as context.
2. `run_job(independent_review.yaml)` -> first read. The prompt: route `qwen3-next`, temperature 0.0, seed 1, max_output_tokens 6000, `response_format: json_schema`. The authoring prompt (`section_authoring.yaml`) uses the SAME model route (qwen3-next) and temperature. "Independence" is only a different prompt id/sha (`identity_separate`, review.py:2027) and ledger attribution, not a different model.
3. `review_checks` (1531) drops findings whose quote cannot be located in the named section (folding rather than failing the whole review unless none remain).
4. `review_document` (1782) runs each finding through the deterministic fold stack `scope_defect` (1716): absence/omission claims refuted by the candidate (`absence_defect` 921, `omission_defect` 1114), quotes of non-SUPPORTED facts (`excluded_evidence_defect` 1610), OMIT_UNSUPPORTED dispositions (`excluded_disposition_defect` 1654), renderer-owned text (`rendered_defect` 1584, `renderer_owned_defect` 1217), then criterion-specific refutations (`factuality_defect` 420, `cited_fact_defect` 799 - literal/paraphrase token-overlap grounding with `_PARAPHRASE_MIN_OVERLAP = 0.6`, 551). A finding that survives and names a section plus a repairable stage blocks; otherwise it is advisory (`reviewer_scope_defect` field).
5. Verdict downgrade: `verdict = returned if findings or returned == ACCEPT else ACCEPT` (1899). A REJECT whose findings all fold to advisory becomes ACCEPT (committed example: Slides-Java manifest `review_verdict_as_returned: REJECT_PRESENTATION`, `review_verdict: ACCEPT`, 12 advisories).

Second reader (OWNER-15, `second_read_decision` 338-358) triggers on:
- `PROSE_JUDGMENT_ON_REQUIRED_ROW`: the first read raised a `presentation`-criterion finding on a required shell row, or
- `ADVISORY_DEFERRAL`: any DEFER_UNRESOLVED unit classified ADVISORY (decisions come from `review_deferrals`, rounds.py:573).
A clean first ACCEPT with neither condition makes no second call; `second_reader.trigger.triggered=false` is recorded and BC-10 accepts the single read (registry.py:2117-2120). The second read is the same prompt and hash with `seed = prompt seed + 2` (`second_reader` 379); a third read (`seed + 3`) only if the first read ACCEPTs and the second read disagrees (rounds.py:314-317). A prose-judgment finding blocks only if the other read raised the same class (`finding_class` 369: section+stage+criterion) - the "two-reader rule". Failure of the second read is returned as `SecondReadFailure` and recorded under `second_reader.failed`; BC-10 then fails (fail-closed, registry.py:2141-2151).

What review.json stores (review.py:1995-2029): `schema_version`, `readme_sha256`, `verdict`, `verdict_as_returned`, `findings` (blocking, with `causal_state`, `reader`, standing partitions), `advisory` (with `reviewer_scope_defect` or `single_reader_advisory`), `second_reader{read:1|2|3, corroborated, failed?, trigger{triggered,reasons}}`, `preserve`, `reviewer{job,stage,prompt_sha256,model_route}`, `authoring{...}`, `identity_separate`, and (added after) `acceptance_profile` (rounds.py:580). Raw LLM replies are NOT in review.json; they go to `raw_calls.json` keyed by request hash (rounds.py:587-592). Only 5 of 30 CURRENT bundles carry raw_calls.json (Imaging-.NET, Slides-Cpp, BarCode-Python, Font-Python, Slides-.NET), so the fold cannot be replayed from the sealed bytes for the rest.

Sources of non-determinism: (a) hosted LLM sampling variance even at temperature 0/seed (manifest `call_variance` shows `independent_review` with 3 distinct responses across the transaction history for Slides-Java); (b) the second/third read seeds; (c) the CallStore: unchanged request hash reuses the accepted output with zero calls (core/llm/jobs), so replays are deterministic only because the stored reply is reused, not because the model is; (d) fold stack is purely deterministic given the raw reply. A change to the model route is scoped as a prompt-class change (seal.py:529).

---------------------------------------------------------------------------------------------------

## 3. bundle/

Seal (seal.py `seal_candidate` 986-1147):
1. Stage artifacts from the transaction (`_staged_artifacts` 428): REQUIRED = README.md, README.patch, facts.json, dispositions.json, plan.json, validation.json, review.json, calls.jsonl; OPTIONAL = investigation.json, content_units.json, raw_calls.json, examples.json, probes.json, repairs.json; plus `dependencies.json` computed from inputs (335) and the ledger relabelled by `composition_ledger` (444).
2. Provider-call count is re-measured from the on-disk ledger by invocation id and must equal the in-memory count (993-1000).
3. No manifest -> write bundle at `ACCEPTED`, proof none (1003-1019). Existing manifest -> `verify_bundle`, compute differing artifacts (replay-exempt: calls.jsonl, probes.json, manifest.json; validation.json compared with BC-11 blanked).
4. Rerun differs + proven bundle + waiting state -> adopt a waiting update if a fresh zero-call process reproduces the exact recorded update (`_adopt_update` 883), else `_record_update` (745). Rerun differs + unproven -> re-seal at ACCEPTED, withdraw proof (1067-1084). Identical + zero calls + fresh process -> `_proof` (856) -> READY_FOR_PROPOSAL, BC-11 PASS, `_supersede_siblings` (971). Identical but this process sealed it -> "proof withheld".
5. `_write_bundle` (541): stages to a sibling temp dir, reconciles ledger totals, scans for secrets (BundleLeakError), `rename`s into place, then updates `CURRENT` last (610-613). Note: `CURRENT` moves at the first seal of a new revision (state ACCEPTED), not at READY.

What is checksummed (`core/candidates.py::verify_bundle` 114-164): manifest must be a JSON object with non-empty `state`, `schema_version` in {1}, non-empty `files` map; every file in `files` must exist and match `{sha256, bytes}`; if `calls.jsonl` is listed, `ledger_totals` must reconcile. NOT checksummed: `manifest.json` itself (state, update, invalidated, no_op_proof, sealed_by, models_used, upstream_blobs are all unauthenticated and can be hand-edited, e.g. state -> READY_FOR_PROPOSAL), the `CURRENT` pointer, and sibling revision dirs. `files` is built from staged artifacts only (seal.py:551).

dependencies.json (what the candidate "consumed"): `source{revision,tree_sha256}`, `environment{python_version, os, extractor_version, inherited_units_version, presenter_site_manifest, toolchains}`, per-fact hash map, `prompts{name:{sha256,version,model_route}}`, `contract_version`, `components{shell,renderer,normalisation,reviewer_logic}`, `validators{BC-xx: version}`, `validator_version`, `acceptance_profile_version`, `policy{version,sha256}`, `protected_content_fingerprint` (seal.py:278-343).

State computation:
- `bundle/evaluation.py::evaluate` (82): diff sealed dependencies.json vs the upcoming run's `upstream_dependencies` (cli.py:2703-2706); each change -> `Change(dependency, detail, reopens, scope)` via invalidation tables. Written to `evaluation.json` in the transaction (not sealed).
- `bundle/invalidation.py` scope table (68-117): only `facts` (source, tree, environment, fact records) -> `INVALIDATED` re-entering at EXTRACTING; evidence, reconciliation, presentation, planning, authoring, validator, reviewer -> `VALID_UPDATE_AVAILABLE`. `route()` (223) picks the invalidating scope if any. Unknown input classes raise `ScopeError` (fail closed).
- `bundle/dry_run.py::portfolio_routing` (96): compares sealed deps to the running code's `code_dependencies` for the keys the sealed record holds; cannot see facts/source/host environment, so a `facts` scope never appears.
- `bundle/portfolio.py`: funnel of 7 cumulative counts (fact_valid, presentation_valid, independently_accepted, no_op_proven, source_fresh, publication_eligible, effect_authorized). FACT_CHECKS = BC-01..06, 08, 09; PRESENTATION = BC-07; BC-12 is in neither list. `publication_eligible` requires `acceptance_profile.RATIFIED` and a PASS acceptance record (portfolio.py:312-315); RATIFIED is False so counts 6 and 7 are structurally 0.
- `bundle/reproducibility.py`: README re-render byte compare, counted in `status`.

Who writes manifest.json state (all in seal.py unless noted):
- `_write_bundle` 541-614: ACCEPTED or READY_FOR_PROPOSAL (+ adopted).
- `_record_update` 745-845: VALID_UPDATE_AVAILABLE or INVALIDATED (+ `update`, `invalidated`), rewriting manifest only (artifacts untouched).
- `invalidate_bundle` 950-965: INVALIDATED + `invalidated` record, called from cli.py:2796 only.
- `_supersede_siblings` 971-983: SUPERSEDED on older READY revisions.
Nothing else writes state. Failing checks that do NOT invalidate (`INVALIDATING_CHECKS` = BC-01..06, 08, 09 plus BC-10 with REJECT_FACTUAL/REJECT_PRESERVATION, seal.py:934-947): BC-07, BC-12, other BC-10 verdicts. See finding F2 below.

Versions feeding invalidation: VALIDATOR_VERSION, each Check.version, CONTRACT_VERSION, REVIEWER_LOGIC_VERSION, ACCEPTANCE_PROFILE_VERSION, EXTRACTOR_VERSION, INHERITED_UNITS_VERSION (extractors), SHELL/RENDERER/NORMALISATION/POLICY versions (composition modules, outside slice), prompt sha/version/route. REPAIR_LOGIC_VERSION and SCORER_VERSION feed nothing.

---------------------------------------------------------------------------------------------------

## 4. Outbound paths

### 4a. propose (PR creation)  - `propose/effect.py` + `cli.py::run_propose` (1888) + `.github/workflows/propose.yml`

What is created: nothing is pushed as a git object. The effect uses the GitHub contents API on the TARGET repository itself (no fork): create ref `repository-presenter/readme-update` from the base branch HEAD if missing (effect.py:318-333, `PRESENTER_BRANCH` 103), `put_contents` of exactly one file, `README.md`, with commit message "Update README via repository-presenter" plus candidate_hash/source_revision/approver (341-353, 168-174), then create or update one PR (title "Update README via repository-presenter", body lists candidate_hash, source_revision, policy_version; cli.py:2053-2059). Idempotent: unchanged README -> no commit; unchanged title/body -> no PR edit. One branch and one open PR per target.

Gate sequence (all must pass before the first write; each a typed `Refusal`):
1. Registry: `require_write_permitted(registry, repo, "readme_proposal")` (cli.py:1953; core/registry/write_gate.py) - entry listed, active, `mode == "full"`. `dry_run`/`disabled` never get a `WritePermit`. Only 2 of 36 entries are full today.
2. Bundle: `load_proposable_candidate` (core/candidates.py:433-481): CURRENT exists, `verify_bundle` passes, manifest revision/repository match, state must be exactly `READY_FOR_PROPOSAL` (463-469) and README.md must be in `files`. README bytes are read from the bundle.
3. Env kill switch `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` in {1,true,yes} (effect.py:94,142,261). Set only in the "Propose for real" step of propose.yml.
4. Token `GH_PROPOSAL_WRITE_TOKEN` (never `GH_TOKEN`); `verify_installation_token` proves an App installation token reaching exactly the target (effect.py:283).
5. Authorization record: JSON file `ops/proposal-authorizations/<owner>__<name>__<hash[:12]>.json` (core/authorization/proposal.py:34, 100-102), pydantic `ProposalAuthorization` with fields schema_version, repository, candidate_hash (sha256 of exact README text), source_revision, base_branch, branch, pr_intent, policy_version ("1"), approver, issued_at, expires_at (max 7 days), supersedes_prs. `verify_record_provenance` (core/authorization/record_provenance.py): tracked, no uncommitted diff, last commit reachable from `origin/main` AND an ancestor of the run's trigger commit (`--trigger-sha`/$GITHUB_SHA). `validate_authorization` re-checks every field against the actual candidate and live target (proposal.py:154-238). `draft-proposal-authorization` (cli.py:2103) writes a draft; a human merges it.
6. Stale source: `recheck_source()` reads the live default-branch SHA and must equal `authorization.source_revision` (effect.py:291-300). The dry run checks bundle revision == live head (cli.py:1986).
7. PR history: merged/closed PR for the same candidate hash blocks recreation unless named in `supersedes_prs`; an existing open PR must be attributed to the expected App (effect.py:303-314, 184-205).
Lost-response reconciliation for `put_contents` (355-380). Dry-run by default (`--propose` flag); `--local-test-readme-file` can never combine with `--propose` (cli.py:1923-1946).

Can it run for a VALID_UPDATE_AVAILABLE or stale candidate?
- VALID_UPDATE_AVAILABLE (or INVALIDATED, ACCEPTED, SUPERSEDED): no. `load_proposable_candidate` refuses anything but READY_FOR_PROPOSAL.
- "Stale" candidates (READY_FOR_PROPOSAL but behind the running code's validator/component/prompt versions, or sealed under validator v3 when code is v15): YES. `run_propose`/`propose_candidate`/`run_draft_proposal_authorization` never call `stale_candidates`, the portfolio assessor, or the acceptance score (grep of cli.py shows `stale_candidates` only in `run_status`, line 2221). The authorization binds only the README hash. 29 of 30 committed CURRENT bundles are READY while sealed under older validators (e.g. v3 vs v15). Related: a re-run that newly fails a non-invalidating check leaves the old bundle READY (see F2).
- Source drift: blocked at propose time by the live-head recheck, so a bundle behind upstream HEAD is refused. A dependency drift (non-README upstream blob change at an unchanged head) is not possible; head equality is required.
- Residual race: branch creation and base SHA are read after the recheck (effect.py:319-331); a base-branch move between them is not re-checked. An already-existing presenter branch is not reset to the base (only README.md is rewritten), so it can diverge from a moved base.

### 4b. issues (upstream defect handoffs)

Detection and drafting: `cli.py::_run_present` (2787-2823). When validation fails and `invalidates(failed[0])` AND `invalidate_bundle` returned a manifest (i.e., a bundle for the same revision already existed), it calls `eligible_for_handoff` (draft.py:68: `causal_stage == EXTRACTING` and id in {BC-02}) then `record_handoff_if_new` -> `draft_handoff` requires a non-SUPPORTED `install_command` fact with evidence; fingerprint = sha256(repo, check id, `fact.id:polarity:value`); dedup against ledger by `{repository, fingerprint}`; writes `evidence/upstream-defects/<owner>__<name>/<hex>.json` at HANDOFF_PENDING. Never writes to GitHub.

Defect classes that exist vs have detectors:
- Broken install (BC-02 non-SUPPORTED install_command): drafter + redetector (PyPI only).
- Unparseable source (`NOT_PROCESSABLE`, `ast.parse` fails): redetector exists (redetect.py:343) but NO automatic drafter - the one such handoff (Aspose.TeX-FOSS-for-Python) was authored by hand. The actual processability check (`evidence/processability.py::assess_processability`) only raises `NO_IMPLEMENTATION_EVIDENCE` (no manifest/source), not unparseable source.
- Uncompilable/failed example (BC-03/EXTRACTING): no drafter or redetector. Unverified examples become an ADVISORY deferral (UNVERIFIED_EXAMPLE) and are silently withheld.
- Broken relative link (BC-06, EXTRACTING): no drafter (id not in `_AUTO_DRAFT_CHECK_IDS`).
- Missing license: no detector at all in components/issues (license facts only feed badges/the License section).
So effectively one defect class (BC-02) is auto-detected.

Behaviour gaps found:
- No bundle at the current revision -> no handoff (the `invalidate_bundle(...) is not None` condition, cli.py:2796). A first-time failing repository yields nothing. Only `failed[0]` (first failing check) is examined.
- The redetector for BC-02 is hardcoded to PyPI (`_REGISTRY_ECOSYSTEM = "python"`, redetect.py:75; `_PYPI_EVIDENCE_URL` 77) and needs exactly one pypi.org evidence URL (266). Of the 5 real BC-02 handoffs on disk, only HTML-Python carries a PyPI URL; npm (3D-TS, PDF-TS), NuGet (Imaging-.NET), and Cells-Cpp (no registry) yield `still_fires=None`, which `plan_filing` treats as "inconclusive - refusing to file" (file.py:262-266). Those four can never be filed by the tool as written. For HTML-Python the handoff's claim is about `build-backend` while the redetector replays only the PyPI "distribution not found" half (redetect.py:257-258).
- Current state on disk: 6 real handoffs, all HANDOFF_PENDING, all six target repositories are `dry_run` (none full), `ops/issue_approvals/` and `ops/issue_close_approvals/` contain only README.md. So nothing can be filed today. One synthetic FILED handoff (#189 on this repo) exists as a live proof.

Approval / token / filing sequence (`file.py` `file_handoff` 270-361, cli.py `run_file_upstream_defects` 1552):
1. Registry permit for effect `issue_filing` (mode full) per handoff (cli.py:1659).
2. Kill switch `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` truthy (file.py:87,103).
3. Token `GH_ISSUES_WRITE_TOKEN`, verified by `default_verify_installation_token` for exactly the target (cli.py:1686).
4. Per-handoff approval record `ops/issue_approvals/<owner>__<name>__<64hex>.json` with fields handoff_id, repository, evidence_digest (digest of repo, revision, fingerprint, triggering_check, evidence, claim, title, body), approver (non-bot string), approved_at, expires_at (max 30 days) (approval.py:9-18, 51-52). `GitApprovalStore` reads from the trigger commit via `git ls-tree/show` (never the working tree), rejects bot-authored commits and shallow clones (approval.py:251-294). It does NOT require the commit to be reachable from `origin/main` (compare record_provenance.py for proposals, which does). The approver string is not matched to the commit author or any owner list.
5. Handoff status must be HANDOFF_PENDING; target must be valid owner/name; upstream search for the fingerprint marker (`<!-- repository-presenter-defect: sha256:... -->`) must complete and find none (else records as FILED without a write); `recheck` must confirm the defect still fires. Then `create_issue`.
Close: `close_handoff` (file.py:492) needs registry `issue_close` permit, kill switch, token provenance, a separate close approval `ops/issue_close_approvals/<id>.json` (adds issue_number and close_reason `completed`|`not_planned`), a FILED handoff whose redetector proposes RESOLVED_UPSTREAM with a deterministic reason (`_propose_close_reason`, redetect.py:202), and a live issue carrying the marker, open, not a PR.
Issue "readiness" commands: there is no command with that name. The nearest are `issue-targets` (cli.py:1503: JSON matrix of repositories having a PENDING or FILED handoff), `file-upstream-defects` dry-run (WOULD-FILE/WOULD-NOT-FILE with reason) and its `--count-writable` (committed files only), and `redetect-upstream-defects` dry-run (would close / would not close). The scheduled workflow `issues-scheduled.yml` runs the analyse job daily and the write job only when the kill-switch variable is 1.
Dedup across runs: the workflow holds no `contents: write` and never commits handoff status back. After a filing, `write_handoff(updated FILED)` (cli.py:1706-1707) changes only the runner's working tree; the committed artifact stays HANDOFF_PENDING, so a later close (needs FILED + issue_ref in the checked-out artifact) cannot act unless a human commits the FILED artifact.

### 4c. metadata apply (`metadata/*`, `cli.py::run_metadata` 1758)

Capture (GET /repos) -> proposal (description = first prose sentence of the sealed README opening paragraph, topics = verified platform/family/license facts + constants `aspose`,`foss`, homepage = `link_target:product.homepage` fact) -> diff with `preservation` rules (default preserve; replace only empty/placeholder/filler/contradicted descriptions or invalid/placeholder/self-reference homepages; topics are merged and removed only when they name another platform). Writes proposal record under runs/metadata (not sealed). Apply gates (apply.py:182-285): `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED`, `GH_METADATA_WRITE_TOKEN`, registry `metadata_write` permit (mode full), non-empty diff, mandatory live compare-and-swap refetch, strong live values never overwritten. Real writes: PATCH description/homepage, PUT topics. No workflow runs it; CLI only.
Gaps: (1) `run_metadata` reads the CURRENT bundle's facts/README without `verify_bundle` and without checking manifest state (cli.py:1798-1810), so metadata can derive from an INVALIDATED, ACCEPTED or corrupt bundle. (2) No token-provenance verification (propose and issues both call `verify_installation_token`; metadata does not). (3) No per-effect authorization record (propose and issues each have a committed, expiring, hash-bound one). (4) The write token is used for the compare-and-swap read.

---------------------------------------------------------------------------------------------------

## 5. Dead code, duplicated authority, bypasses, hidden fallbacks, manual-only steps

Dead / orphan / unreachable:
- `review/acceptance/template_check.py`: no production importer; D14 stays unevaluated.
- Acceptance profile: `RATIFIED=False`, every `points=None`; scorer only writes an advisory record; its only consumer (`portfolio` stages 6-7) is structurally zero and `propose` ignores it. 8 of 26 criteria are `review`-evaluated, 1 `unevaluated`.
- `registry.py` module docstring says eleven checks; there are twelve. `REQUIRED_SECTIONS` re-declared in review.py:311 (identical to registry.py:137).
- `ACCEPTANCE_PROFILE_VERSION`, `SCORER_VERSION`, `REPAIR_LOGIC_VERSION` are versions whose only effects are recording or ledger scoping.
- `redetect.py` NOT_PROCESSABLE branch and `HANDOFF_ACKNOWLEDGED` status have no producer.
- Slides-Java committed bundle is `VALID_UPDATE_AVAILABLE` with `update.classification: "factual"`, a leftover of the pre-2026-10-04 inverted routing (seal.py docstring); the current code would mark that INVALIDATED.

Duplicated authority:
- Narration vocabulary and edition substitutes exist twice: blocking `_NARRATION`/`_edition_substitute_failures` in registry.py (493-560, 1146) and advisory `_NARRATION`/`_BANNED_EDITIONS` in text_checks.py:48-58; lists differ (e.g., text_checks adds `provider calls?` and `validation status` as D01 patterns). Same for single H1 / badge row / fence-and-spacing.
- "Which checks are factual": `INVALIDATING_CHECKS` (seal.py:934) vs `FACT_CHECKS`/`PRESENTATION_CHECKS` (portfolio.py:102-112) vs `INVALIDATING_VERDICTS`. BC-12 is in none.
- Fence parsing is implemented three ways in registry.py (`_fences` via markdown-it 606; hand-rolled `_outside_fences` 622 and `_section_lines` 645), plus `text_checks.scan`.
- `_normalized` is defined three times (registry.py:602, review.py:211, template_check.py:154) with different meanings.
- Two authorization-provenance mechanisms: `core/authorization/record_provenance.py` (must be on origin/main and an ancestor of the trigger) vs `GitApprovalStore` (any commit visible at the ref, not-bot). Issue approval is the weaker one.
- Constants copied across the layer boundary: `DEPENDENCIES_FILENAME`, `README_FILENAME`, `CURRENT_FILENAME` (core/candidates.py vs seal.py).
- Three near-identical write-authorization helpers (`write_authorized` in effect.py, file.py, apply.py) differing only in the variable name.

Bypasses / weak points:
- B1. `propose` ignores staleness and acceptance (see 4a).
- B2. A failing validation on a rerun returns EXIT_INCONSISTENT before `seal_candidate` (cli.py:2787-2828); only `invalidates(first)` touches the manifest. For BC-07/BC-12/other BC-10 failures nothing is recorded, so an old bundle that no longer passes the current validator stays READY_FOR_PROPOSAL and proposable. The VALIDATOR_VERSION 9 comment ("newly fails -> VALID_UPDATE_AVAILABLE") describes a path that only exists when validation passes but artifacts differ.
- B3. `manifest.json`/`CURRENT` are not checksummed (see section 3); every gate (propose state check, portfolio, monitor) trusts them.
- B4. Reviewer asymmetry: the fold stack only demotes blocking findings (token-overlap paraphrase grounding, absence refutation, two-reader rule) and the verdict is rewritten to ACCEPT when all findings fold. Authoring and review use the same model route and temperature. A rejected review can become ACCEPT with 12 advisories (Slides-Java).
- B5. Validator control-plane text matching: BC-02/BC-03 decide by substrings of evidence `detail` prose (`"distribution not found"`, `": EXECUTED"`, `"verified source build"`, registry.py:416, 771-810, 854-858), contradicting the project's "routing reads fields" rule (RC8) that other code observes.
- B6. `Candidate.original_readme=None` silently skips the BC-01 digest comparison (743). `review_document` with `facts=None`, `units=None`, `dispositions=None` silently degrades to a weaker fold (1876, 1863); `rounds.py` passes all of them, but any other caller would not.
- B7. `invalidate_bundle` handoff drafting ignores all but the first failing check and requires a prior bundle at the same revision.
- B8. Metadata path (4c) bypasses bundle verification, state, token provenance and authorization records.
- B9. `monitor` status CURRENT/DRIFTED reflects only head SHA + upstream blob ids; it does not look at manifest state, validator/prompt staleness, or whether the bundle is INVALIDATED.
- B10. `seed_call_store`/`seed_additional_calls` seed the LLM CallStore from sealed artifacts without lineage checks; only the request hash gates reuse (documented intent). raw_calls.json exists in 5 of 30 bundles.

Manual-only steps:
- Committing proposal authorization records through a reviewed PR (draft command exists; merge is human).
- Committing issue approval and close approval records; committing the FILED handoff artifact after a filing (workflow never does); authoring NOT_PROCESSABLE and non-BC-02 handoffs by hand.
- Ratifying the acceptance profile (points, disqualifiers, applicability) - needed for portfolio `publication_eligible`.
- Selecting the first live target for each effect (documented owner-selected, effect.py docstring).
- Setting the owner variables (`REPOSITORY_PRESENTER_*_WRITE_AUTHORIZED`), minting App installation tokens in the write jobs.
- Metadata apply has no workflow; only a manual CLI run.
- Recheck of sealed candidates against a new validator: no command exists; requires a full `present` run.

---------------------------------------------------------------------------------------------------

## Appendix: file:line pointers (most useful)
- Battery: `validation/registry.py:2003` (validate_candidate), 2014-2025 (judge map), 2037 (PENDING for S10/S12), 2101 (BC-10), 2197 (BC-11).
- Version constants: registry.py:134 (VALIDATOR_VERSION), review.py:157 (REVIEWER_LOGIC_VERSION), targeted.py:358 (REPAIR_LOGIC_VERSION), seal.py:117 (CONTRACT_VERSION), profile.py:38 (PROFILE_VERSION), scorer.py:46 (SCORER_VERSION).
- Loop wiring: rounds.py:326 (run_round), 507 (validation), 543 (review), 1059 (run_transaction); cli.py:2762 (calls run_transaction), 2787-2828 (failure handling), 2832 (seal_candidate).
- Seal states: seal.py:986-1147; invalidation tables invalidation.py:68-177; verify_bundle core/candidates.py:114.
- Propose: effect.py:208-440; cli.py:1888-2100; candidate load core/candidates.py:433; authorization core/authorization/proposal.py, record_provenance.py; workflow .github/workflows/propose.yml.
- Issues: draft.py:64-188; redetect.py:75-77, 251, 343; approval.py:251; file.py:270, 492; cli.py:1286, 1503, 1552; workflow issues-scheduled.yml.
- Metadata: cli.py:1758; apply.py:182; proposal.py:275; preservation.py:206-291.
