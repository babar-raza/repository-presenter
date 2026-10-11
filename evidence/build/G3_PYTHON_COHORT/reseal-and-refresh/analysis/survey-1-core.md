authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Survey 1 - src/repository_presenter/core/, cli.py, cursor.py, __init__/__main__

Method: every file in the slice was read (cli.py in full, 3126 lines). Production importers were found by a
script over `src/` (scratchpad `imports.py`) and spot-checked with Grep. Components files outside the slice
(`components/readme/bundle/{seal,portfolio,invalidation,evaluation,reproducibility,dry_run}.py`,
`components/propose/effect.py`, `validation/registry.py`) were read only where the questions required it.
I also ran `.venv/Scripts/python.exe -B -m repository_presenter status --stale` (read-only, no bytecode written,
`git status` unchanged) and a throw-away in-memory render comparison to verify the status numbers below.
Legend: "prod importers" = non-test modules under `src/` that import the file.

---------------------------------------------------------------------------------------------------------------

## PART A - FILE-BY-FILE

### Top level

| File | Purpose | Public API | Prod importers | Versions / hash inputs it owns |
|---|---|---|---|---|
| `__init__.py` | Package marker | `__version__ = "0.1.0"` | `cli.py` (prints it) | none recorded in state |
| `__main__.py` | `python -m repository_presenter` shim | calls `cli.main` | entry point | - |
| `cursor.py` | Reads `project/state.yaml` (never writes) | `Cursor`, `find_project_root`, `load_cursor`, `CursorError`, `CURSOR_RELATIVE_PATH` | `cli.py` only | Feeds `status` headline text and the consistency check `cursor.recorded_candidates == count_current_candidates` (cli.py:2326). Fields read: `current_gate`, `active_work_item`, `progress.{current_candidates,denominator,canary}` |
| `cli.py` (3126 lines) | The single CLI: 17 subcommands (see Part B Q3) | `build_parser`, `main`, `run_*` functions | console script / `__main__` | Imports every version constant (`SHELL_VERSION`, `RENDERER_VERSION`, `NORMALISATION_VERSION`, `REVIEWER_LOGIC_VERSION`, `VALIDATOR_VERSION`, `BLOCKING_CHECKS[*].version`) only to build the `status` staleness inputs (cli.py:2214-2221). Exit codes: 0 ok, 1 inconsistent, 2 usage, 3 unsafe (cli.py:343-346) |

### core/ (root modules)

| File | Purpose | Main public API | Prod importers | Versions/hash inputs |
|---|---|---|---|---|
| `core/__init__.py` | docstring | - | - | - |
| `core/candidates.py` (481) | Reads sealed bundles on disk: integrity (`verify_bundle`), CURRENT resolution, counting, staleness, proposable-candidate loading | `verify_bundle` (114), `count_current_candidates` (195), `integrity_valid_candidates` (167), `independently_accepted_candidates` (207), `current_counted_repository_dirs` (250), `ready_revision` (264), `examples_verification_summary` (277), `stale_candidates` (337), `load_proposable_candidate` (433), `iter_sealed_bundles` (88), `BundleError`, `BundleLedgerError` | cli, components.monitor.drift, bundle.{dry_run,portfolio,reproducibility,seal}, core.secrets, core.state.present_transaction | `COUNTED_STATES={"READY_FOR_PROPOSAL"}` (49), `SUPPORTED_SCHEMA_VERSIONS={1}` (53), `UPSTREAM_BLOBS_FIELD="upstream_blobs"` (44). Duplicates `DEPENDENCIES_FILENAME`, `README_FILENAME`, `CURRENT_FILENAME` that also exist in seal.py/renderer.py (comments say core may not import components) |
| `core/noop_proof.py` (523) | Measured no-op proof: process identity, invocation records, ledger measurement/reconciliation | `Invocation` (229), `current_process_identity` (189), `verify_noop_pair` (417), `measure_invocation` (365), `ledger_totals` (448), `reconcile_ledger` (465), `NoOpProofError` + 11 typed reasons | cli, bundle.seal, core.candidates | `RECORD_SCHEMA_VERSION=1`; `_PROCESS_NONCE` minted at import. Feeds manifest `sealed_by`, `ledger_totals`, `no_op_proof.{first_run,rerun}` |
| `core/config.py` (80) | Gateway config from env (`GPT_OSS_ENDPOINT`, `GPT_OSS_API_KEY`, optional `GPT_OSS_MODEL`) | `load_gateway_config`, `GatewayConfig` | cli, repair.rounds, llm.{fallback,jobs,transport}, preflight | `DEFAULT_TIMEOUT_SECONDS=900` (not in any hash) |
| `core/errors.py` (67) | Typed exception hierarchy + exit codes | `PresenterError`, `ConfigError(2)`, `NotAllowlistedError(3)`, `GitSafetyError(3)`, `JobError`, `ProviderCallBudgetError`, `StateBackendError`, ... | ~everything | - |
| `core/hashing.py` (14) | `sha256_text` (CRLF/CR normalised to LF) | `sha256_text` | cli, propose.effect, portfolio, candidates, llm.prompts | Prompt-manifest hash and the authorization `candidate_hash` both come from here |
| `core/facts.py` (324) | Typed fact records, `facts.json` writer/reader, packet record bounding | `Fact`, `FactsDocument` (`canonical()`, `to_json`), `bounded_records` (234), `write_facts`, `read_facts` (295), `fact_id`, `slug` | 36 modules | `SYMBOL_CAP=6000`, `LINK_CAP=100`, `EXAMPLE_CAP=30`, `_EXCLUDED_FROM_PACKETS={"identity:revision"}` - these shape LLM packets, hence request hashes and cache keys; `schema_version=1` |
| `core/examples.py` (154) | Shared example-verification types (`ExampleCandidate`, `ExampleReceipt`, `MeasuredBuild`) + `examples.json` writer | `write_receipts`, `collapse_blank_runs` | cli, 23 components | `RECEIPTS_FILENAME="examples.json"` |
| `core/ecosystems.py` (280) | Per-ecosystem presentation vocabulary (`EcosystemSpec`; built-ins PYTHON, NET; others register at import) | `spec_for`, `SPECS`, `EcosystemSpec` | 13 components (renderer, extract, platforms) | Templates feed rendered README bytes -> `RENDERER_VERSION` must be bumped by hand when they change |
| `core/execution.py` (162) | Secret-free, bounded subprocess execution for example verification | `execute`, `profile_environment`, `secret_free_environment` | 7 platform verifiers, toolchains | `MAX_TIMEOUT_SECONDS=300` |
| `core/toolchains.py` (304) | Resolve machine toolchains (javac, mvn, dotnet, node, npm, tsc, go, cargo, cmake, g++, ninja) incl. the owner's `TOOLCHAIN_PATHS.txt` registry; fingerprint | `resolve_tool`, `toolchain_fingerprint` (295), `probe_version`, `recorded_tool` | bundle.seal + 6 platform verifiers | `toolchain_fingerprint()` is recorded as `dependencies.json -> environment.toolchains`; any version change = environment change = reopens EXTRACTING / scope `facts` = INVALIDATED. Hard-coded Windows paths `C:/tools/rp-toolchains`, `D:/tools` (50-52, 181) |
| `core/grammars.py` (60) | Pinned tree-sitter grammar loader (7 languages) | `get_parser` | 7 platform extractors | pins live in pyproject |
| `core/long_paths.py` (76) | `\\?\` long-path helper | `long_path` (used), `exceeds_max_path` (**unused anywhere**) | platforms.net_examples, core.git_safety.clone | - |
| `core/package_registry.py` (95) | Observer registry for package-registry lookups (PyPI etc.) used by `redetect` | `register_observer`, `observe_distribution`, `RegistryObservation` | issues.redetect, platforms.python_registry | `summary` deliberately excludes latest version so it stays out of dependencies.json |
| `core/probes.py` (39) | Live-probe record -> `probes.json` (volatile, unhashed, excluded from replay compare) | `ProbeRecord`, `write_probes` | cli + facts/platform extractors | `PROBES_FILENAME="probes.json"` |
| `core/preflight.py` (124) | Gateway preflight: list models, check routes, seed probe, availability probe; record `runs/preflight/catalog.json` | `run_gateway_preflight`, `read_catalog_ids`, `write_catalog` | cli only | Catalog is a hard prerequisite of `present` (`read_catalog_ids`, cli.py:2596) |
| `core/retry.py` (95) | tenacity-based bounded retry policies (`clone`, `package_registry`, `link_check`, `llm_call`, `github_api`, `state_cas`) | `run_with_retry`, `RetryableOperationError`, `RETRY_POLICIES` | cli, git_safety.clone, github.read_client, llm.jobs, state.*, 3 extractors | - |
| `core/secrets.py` (163) | Secret-name detection, `redact`, bundle leak canary, upload staging | `configured_secrets`, `redact`, `scan_for_secrets`, `find_secret_leaks`, `stage_transaction_for_upload` | cli, monitor.*, bundle.seal, repair.rounds, validation.registry, execution, clone, git_backend | `SECRET_VARIABLES`, `SECRET_SUFFIXES`, `MIN_SECRET_LENGTH=8` |
| `core/sealing_plan.py` (418) | Plan one scheduled sealing run from the drift contract + failure-memory history; model pin | `plan_sealing_run`, `read_drift_contract`, `read_sealing_history_contract`, `require_sealing_model`, `sealing_paused`, `github_output_lines` | cli, monitor.drift | `DRIFT_CONTRACT_VERSION=1`, `SEALING_HISTORY_CONTRACT_VERSION=1`, `MAX_REPOSITORIES_PER_RUN=3`, `SEALING_MODEL="qwen3-next"` (hard-coded, 79), cooldown 24h, pause var `REPOSITORY_PRESENTER_SEALING_PAUSED=="1"` |

### core/authorization/

| File | Purpose | API | Prod importers | Versions |
|---|---|---|---|---|
| `__init__.py` | docstring | - | - | - |
| `proposal.py` (238) | Typed authorization record for a README-proposal PR; `validate_authorization` re-checks every bound field | `ProposalAuthorization`, `authorize_proposal`, `validate_authorization` (158), `load_authorization_file`, `render_record`, `record_filename`, `MAX_LIFETIME=7d` | cli, propose.effect, bundle.portfolio | `CURRENT_POLICY_VERSION="1"` (34); a bump invalidates all minted records. Binds repository, candidate_hash (sha256 of README text only), source_revision, base_branch, branch, pr_intent, policy_version, approver, window, supersedes_prs |
| `record_provenance.py` (106) | Proves the record file was committed on `origin/main` and is an ancestor of the trigger commit (via git) | `verify_record_provenance` | cli | `MAIN_REF="refs/remotes/origin/main"` (needs full-history checkout and fetched origin/main) |
| `refusals.py` (55) | `Refusal` StrEnum + `WriteRefusedError` (exit 3) | - | cli, propose.effect, candidates, write_gate, token_provenance | - |

### core/registry/

| File | Purpose | API | Prod importers |
|---|---|---|---|
| `loader.py` (66) | Load `data/registry.json`; read gate `require_listed`; `enabled_entries` (mode != disabled); `is_permitted` | `load_registry`, `find_entry`, `require_listed`, `enabled_entries` | cli, bundle.reproducibility, core.sealing_plan, write_gate |
| `models.py` (107) | pydantic `Registry`/`RegistryEntry` (repository, family, platform, ecosystem, mode full/dry_run/disabled, policy_profile, active, provider_identity) | - | 18 modules |
| `naming.py` (58) | Name contract: only `Aspose[.-]X[.-]FOSS-for-Y` can be registered | - | models only |
| `write_gate.py` (57) | `require_write_permitted(registry, repo, effect)` -> `WritePermit`; the one write choke point (listed, not disabled, `active`, mode `full`) | `WritePermit`, `require_write_permitted` | cli, issues.file, metadata.apply, propose.effect |

### core/llm/

| File | Purpose | API | Importers | Versions/hash inputs |
|---|---|---|---|---|
| `__init__.py` | doc | - | - | - |
| `jobs.py` (707) | `run_job`: render packet, call gateway, validate (schema+binding+checks), one re-ask, store accepted output by request hash; `CallStore`; `request_hash` | `run_job`, `CallStore`, `JobContext`, `JobResult`, `request_hash`, `render_messages`, `request_payload` | cli, bundle.seal, repair.rounds | Cache key = `canonical_hash({"prompt_sha256": manifest.sha256, "payload": {model, messages, temperature, max_tokens, response_format(+json_schema incl. call_schema), seed?}})` (jobs.py:556). `_PROMPT_ENUM_INLINE_LIMIT=50` (65) changes message text, therefore keys. `CALLS_DIRNAME="calls"` |
| `ledger.py` (248) | Append-only `calls.jsonl`; `CallRecord`; budget | `Ledger`, `CallRecord`, `load_records`, `parse_records`, `canonical_hash`, `summarize` | cli, seal, authoring, rounds, targeted, noop_proof | `PROVIDER_CALL_BUDGET=100` (46), `LEDGER_FILENAME="calls.jsonl"`, `CallRecord.schema_version=1`. `Ledger(call_budget=0)` makes `reserve_provider_call` raise before any request (176-186) |
| `prompts.py` (214) | Load/validate the six `prompts/*.yaml` manifests; content hash = sha256_text of file | `load_manifests`, `validate_routes`, `PromptRegistry`, `JOB_STAGES` | cli, seal, 8 components | prompt `sha256`, `version`, `model_route` recorded in dependencies.json `prompts.*` |
| `fallback.py` (167) | Per-route model availability: 2 consecutive strict-schema probe calls; `FALLBACK_CHAINS` empty by owner decision | `select_models`, `describe`, `ModelSelection` | cli, jobs, preflight | `PROBE_CONSECUTIVE_PASSES=2` -> manifest `models_used` |
| `transport.py` (207) | openai-SDK client factory (`build_client`, the one network seam), model list, seed probe, availability probe | `build_client`, `list_models`, `probe_seed`, `probe_availability` | fallback, jobs, preflight (no component imports it) | - |
| `binding.py` (231) | Structural citation guard: unknown/unsupported fact IDs reject output; symbol-id rewrite; unit dedupe/merge | `binding_errors`, `resolve_symbol_ids`, `fold_duplicate_units`, `merge_partial_units`, `collect_ids` | jobs, planning, dispositions, targeted | - |

### core/git_safety/ and core/snapshot/

| File | Purpose | Importers |
|---|---|---|
| `git_safety/clone.py` (251) | `pinned_read_only_clone`: ls-remote HEAD, **shallow depth-1 clone of the default branch**, require HEAD==observed, neuter push, hook, verify | cli, snapshot.capture |
| `git_safety/git.py` (85) | the only git wrapper (determinism flags, scrubbed GIT_DIR etc., HTTPS token via env header) | components.issues.approval + git_safety, state |
| `git_safety/hooks.py`, `neuter.py`, `verify.py`, `process.py` | pre-push block hook, push-URL neuter, independent proof, bounded subprocess with tree-kill | git_safety.clone/verify/git; `process` also used by execution |
| `snapshot/capture.py` (167) | `capture_snapshot`, `write_source_artifacts` (`source/{tree.txt,README,snapshot.json}`), `verify_snapshot` (rev, tree hash, README hash, `diff-index`), `list_tree_paths` | cli, bundle.seal, evidence.facts.extract, processability |
| `snapshot/inventory.py` (85) | case-insensitive README/LICENSE/NOTICE/community file detection | snapshot.capture |

### core/github/

| File | Purpose | Importers | Notes |
|---|---|---|---|
| `__init__.py` | **Stale docstring**: says "Only the read half exists so far ... No module under this package ever performs POST/PATCH/PUT/DELETE" - false: `client.py` has `default_post/patch/put`, `create_issue`, `put_contents`, ... | - | doc drift |
| `client.py` (739) | REST client: metadata read; gated writes (`update_repository`, `replace_topics`, `create_issue`, `close_issue`, `create_ref`, `put_contents`, `create_pull_request`, `update_pull_request`) + reads (`get_ref`, `get_contents`, `find_pull_requests`, `get_issue`, `find_issue_with_marker`). Does **no** authorization itself | cli, issues.file, metadata.{apply,capture}, propose.effect | `find_open_pull_request` (649) has no caller anywhere; writes not wrapped in `run_with_retry` (single attempt) |
| `read_client.py` (220) | Retrying read-only GETs: `fetch_file`, `fetch_tree` (blob shas), `fetch_default_branch_sha` | cli, issues.redetect, monitor.drift, monitor.install_state | `github_api` retry policy |
| `token_provenance.py` (117) | Proves a write token is a `ghs_` installation token reaching exactly the target; proves PR was performed by App | cli, issues.file, propose.effect | `EXPECTED_APP_ID = 5092474` (36). **Not used by metadata.apply** |

### core/state/ (durable-state, G5)

| File | Purpose | Importers | Notes |
|---|---|---|---|
| `schema.py` (345) | `RepositoryRecord`, 23-state `TransactionState`, `TRANSITION_REGISTRY`, `TransitionReceipt`, `LeaseRecord` | state.* only | `schema_version=1`. Fields `source`, `surfaces`, `dependencies`, `accepted_artifact`, `proposal` are **never populated by production code** (grep: no writer outside schema.py) |
| `cas.py` (306) | `StateBackend` protocol; CAS patch; leases/fencing; `record_transition` | present_transaction, recovery, trigger, git_backend | `DEFAULT_LEASE_SECONDS=900`; `renew_lease` (168) and `lease_is_current` (220) have **no production caller** |
| `git_backend.py` (351) | Real backend: one ref per repo `refs/repository-presenter-state/records/<owner__name>` on the control repo's own remote, plumbing-only CAS | cli (`present --durable-state`, `health-check`) | token `REPOSITORY_PRESENTER_STATE_TOKEN` |
| `trigger.py` (236) | Trigger normalisation + dedup/admission | present_transaction, cli (TriggerEventType) | `MAX_TRIGGER_DEDUP_ENTRIES=50` |
| `recovery.py` (230) | Sweep stale leases -> RETRYABLE; resume | present_transaction | `current_source_revisions` param is never passed in production, so the SUPERSEDED branch (131-151) is unreachable in prod |
| `present_transaction.py` (456) | Wraps one `run_present` call in sweep/admit/receipt hops (coarse receipts) | cli | `POLICY_VERSION = "readme-contract-v1-draft"` (83) - comment says it duplicates `seal.CONTRACT_VERSION`, but that is `"readme-contract-v1"` (seal.py:117): **they differ** |
| `health.py` (196) | Deterministic dead-man alerts over a durable record | cli (`health-check`) | `DEFAULT_MAX_WALL_CLOCK_SECONDS=3600`, `DEFAULT_MAX_PROVIDER_CALLS=500` (the ledger hard budget is 100) |

No true ORPHAN module in core/ (every file has at least one production importer, directly or via another core module).
Function-level dead code: `long_paths.exceeds_max_path`, `github.client.find_open_pull_request`, `state.cas.renew_lease`, `state.cas.lease_is_current`.
`core/llm/transport.py`, `core/git_safety/{hooks,neuter,verify,process}.py`, `core/state/{cas,schema,recovery}.py`, `core/registry/naming.py`, `core/snapshot/inventory.py` have importers only inside core (fine).

---------------------------------------------------------------------------------------------------------------

## PART B - CROSS-CUTTING QUESTIONS

### Q1. What `present` does end to end, and the replay / call-store mechanism

`present --repo OWNER/NAME [--facts-only] [--fresh] [--durable-state ...] [--invocation-record PATH]`
(parser cli.py:401-487, dispatch 916-935). `run_present` (2512) creates an `Invocation` (id + OS process identity,
noop_proof.py:229/242) and writes the invocation record to `--invocation-record` in a `finally` (2544-2552).
`_run_present` (2555) stages, in order:

1. Resolve project root via `project/state.yaml` (`_resolve_root` 3094). Collect configured secret values for redaction.
2. `load_registry(data/registry.json)` + `require_listed` (allow-list read gate; mode is *not* checked, so `dry_run` and `disabled` repos are analysed) - 2586.
3. `load_gateway_config(os.environ)` (needs `GPT_OSS_ENDPOINT`+`GPT_OSS_API_KEY`), `load_manifests(prompts/)` (exactly six yaml files), `read_catalog_ids(runs/preflight/catalog.json)` (**must exist - written by the separate `preflight` command**), `validate_routes` - 2594-2597.
4. `pinned_read_only_clone` -> `runs/clones/<owner>__<name>` (ls-remote HEAD, `clone --depth 1`, HEAD must equal observed SHA, push neutered + hook + verified). Always the **current upstream default-branch head**; there is no way to ask for an older revision - 2598.
5. `capture_snapshot`; transaction dir `runs/transactions/<owner>__<name>/<revision>`; `write_source_artifacts` -> `source/{tree.txt,<README>,snapshot.json}` (dir is wiped and rewritten); `verify_snapshot` - 2607-2612.
6. `plugin_for(ecosystem)`, `detect_manifest`, `assess_processability`; if insufficient evidence write `disposition.json`, print NON_PROCESSABLE, return 0 (no ledger, no bundle) - 2618-2635.
7. `select_examples` from the existing README, `verify_snapshot` again, `plugin.verify_examples` (executes/compiles in `runs/verify/<hash>`), write `examples.json` - 2636-2658.
8. `verify_build` (manifest's own build) - 2664-2672.
9. `verify_snapshot` again, `extract_facts` (this performs live network reads: package registry, link checks) -> `probes.json`, `facts.json` - 2675-2694.
10. `bundle_directory(candidates/, entry, revision)`; **`verify_bundle` of any existing bundle at this revision (corrupt -> fail closed)**; if it has `dependencies.json`, `evaluate(sealed deps, upstream_dependencies(...))` -> `evaluation.json` (earliest affected stage + changed classes) - 2698-2712.
11. `--facts-only`: write `preflight.json` (coverage per fact kind / contract row), return - 2713-2714. No provider call.
12. `select_models` - **live provider probes** (2 consecutive tiny strict-json_schema completions per route model; failure = hard stop). These are *not* recorded in the ledger (transport.py:168-175) - 2719.
13. Open `Ledger(transaction/calls.jsonl, invocation_id)` and `CallStore(transaction/calls/)`; under `--fresh` the `calls/` dir is deleted and seeding skipped (2737-2743).
14. Seeding (unless `--fresh` or no sealed bundle): `seed_call_store(bundle, store)` + `seed_additional_calls(bundle, store)` - 2744-2759.
15. `run_transaction` (repair/rounds.py:1059): rounds of S3 investigation -> S4 reconciliation -> S5 planning -> S6 authoring (+coherence) -> deterministic render -> S9 validation (BC checks) -> S10 independent review; up to MAX_ROUNDS with one repair per defect fingerprint. Writes into the transaction dir: `investigation.json`, `dispositions.json`, `plan.json`, `content_units.json`, `raw_calls.json`, `README.md`, `README.patch`, `validation.json`, `review.json`, `repairs.json`, `calls.jsonl` - 2762-2780.
16. Blocking failure: if `seal.invalidates(check)` (BC-01..06, 08, 09, or BC-10 with REJECT_FACTUAL/REJECT_PRESERVATION) and a bundle exists, `invalidate_bundle` rewrites that bundle's manifest `state=INVALIDATED`; for BC-02 upstream defects `record_handoff_if_new` writes `evidence/upstream-defects/...` (HANDOFF_PENDING); return exit 1 - 2788-2828.
17. Else `seal_candidate` (bundle/seal.py:986): stage artifacts to a sibling temp dir, secret-scan, rename into `candidates/<o>__<n>/<revision>/`, then write `CURRENT`. Writes `dependencies.json` and `manifest.json`. State machine inside `seal_candidate`: no manifest -> `ACCEPTED`; fresh-process byte-identical zero-call rerun -> `READY_FOR_PROPOSAL` + `no_op_proof`; differing artifacts on a proven bundle -> `_record_update` (`VALID_UPDATE_AVAILABLE` or `INVALIDATED`) without touching artifacts; ... - 2831-2861.
18. `--durable-state` (`run_present_hosted`, 2952): wraps the above in recovery sweep, trigger admission (`run:<run_id>:<repo>` dedup), and a *coarse* walk of transition hops on the control repo's git-ref state; adds nothing the bundle does not already say.

**Replay / call-store / seeding, exactly**
- *What is cached*: only **accepted job outputs** (`CallStore.put` after schema+binding+`checks` pass; jobs.py:643/672), as `runs/transactions/<repo>/<revision>/calls/<first-12-hex-of-key>.json` = `{job, model_served, output}`. Rejected replies are written beside it (`*.rejected-N.json`) for forensics only and are never replayed. `runs/` is gitignored, so the store is ephemeral.
- *Key*: `canonical_hash({"prompt_sha256": <sha256_text of the manifest yaml>, "payload": {model, messages, temperature, max_tokens, response_format(+schema), seed}})` (jobs.py:556). Anything in the packet (facts excluding `identity:revision`, caps, bounded records), the prompt text, the call schema, the sampling contract, or the **effective model** changes the key.
- *Hit behaviour*: `run_job` re-judges a stored output under the **current** `checks` (not the call schema) before reuse (571). Accepted -> `cache_reuse` ledger record, 0 provider calls. Rejected by current rules -> `cache_stale` record and a live call (606-616). So a validator/normalisation change can silently turn a replay into live calls.
- *Seeding from the sealed bundle* (the only way a fresh checkout/hosted runner can replay): `seed_call_store` (seal.py:635) seeds only the three 1:1 jobs (`repository_investigation`->investigation.json, `source_reconciliation`->dispositions.json, `presentation_planning`->plan.json), keyed by `logical_call_id` from the sealed `calls.jsonl`, and only if exactly one successful attempt exists for that job. `seed_additional_calls` (690) seeds everything in `raw_calls.json` (coherence, independent_review, batch authoring, per-batch reconciliation) keyed by request hash with no lineage check. Audit-only ledger lines (`retained_reason`) are ignored.
- *Not replayable / outside the proof*: (a) availability probes in `select_models` (live calls on every non-facts-only run, even a 100% cache-hit rerun; unledgered) - so "zero provider calls" means zero **ledger** calls; (b) `targeted_repair` outputs are not in `_SEEDABLE_JOBS` and are only covered if present in `raw_calls.json` (I did not trace this); (c) any call whose key moved (prompt/fact/model/schema change); (d) rejected attempts; (e) the live-network parts of extraction (registry, link probes) and the clone itself - a "replay" always re-clones current upstream HEAD and re-runs example execution, so a replay cannot reproduce an *old* revision; (f) `--fresh` deliberately disables all of it.
- *No-op proof mechanics*: proof requires a second `present` in a different process (OS start time + boot id + in-memory nonce, noop_proof.py:189-218) whose own ledger records (stamped by `invocation_id`) contain 0 `provider_call` dispositions and whose artifacts equal the sealed ones byte-for-byte except ledger/probes/manifest (`REPLAY_EXEMPT`, seal.py:150; `validation.json` compared with BC-11 blanked). `verify-noop-proof` re-measures from two invocation records.

### Q2. How current / stale / VALID_UPDATE_AVAILABLE / INVALIDATED / READY_FOR_PROPOSAL are computed; why the headline is 0

All "states" live in each bundle's `manifest.json["state"]`, a plain string written **only** by seal.py (and `invalidate_bundle`). `status` never recomputes a state; it reads it (candidates.py `_read_state`, `verify_bundle`).

- **current**: a repository is "current" iff `candidates/<o>__<n>/CURRENT` exists and names a revision dir whose manifest verifies (`verify_bundle` 114-164: JSON object, non-empty state, `schema_version==1`, non-empty `files`, every file's sha256+bytes match, ledger totals reconcile if present), `manifest.revision == CURRENT`, `manifest.repository` maps back to the dir (`_verified_current`, 220-247). Anything else under a revision dir is ignored (only CURRENT is consulted). Note `verify_bundle` ignores files in the dir that are not in the manifest, and does not hash the manifest itself.
- **READY_FOR_PROPOSAL** (the "counted" state, `COUNTED_STATES`, candidates.py:49): set only in `seal_candidate` when a fresh process reproduces a sealed bundle byte-identically with 0 ledger provider calls (seal.py:1130-1137), or when a fresh zero-call rerun reproduces a waiting update (`_adopt_update`, 883). `count_current_candidates` just counts manifests whose state string is in the set (cli.py:2213/2344). It does **not** check that `no_op_proof` exists or that the bundle is not stale.
- **stale**: `stale_candidates` (candidates.py:337) compares each CURRENT bundle's `dependencies.json` against only: `components.{shell,renderer,normalisation,reviewer_logic}`, per-check `validators.<BC-id>`, and `validator_version` (cli.py:2214-2221). Equality test; missing recordings are skipped. It does not look at prompt hashes, policy, contract_version, acceptance profile, extractor/environment (those are covered only by `evaluation.evaluate` at `present` time and by the `status --stale` routing dry-run `portfolio_routing`, dry_run.py:96).
- **VALID_UPDATE_AVAILABLE / INVALIDATED (update)**: written by `_record_update` (seal.py:745) when a rerun of a *proven* bundle produces differing artifacts or a different effective model. Routing via `bundle/invalidation.py` `SCOPES` (68-117): only scope `facts` (source/tree/environment/fact records) -> `INVALIDATED` (re-enter EXTRACTING); `evidence, reconciliation, presentation, planning, authoring, validator, reviewer` -> `VALID_UPDATE_AVAILABLE`. The update then waits until a later fresh zero-call process adopts it (back to READY). `status` shows these via `held_updates` (dry_run.py:142).
- **INVALIDATED (failure)**: `invalidate_bundle` (seal.py:950) from `_run_present` when `invalidates(first_failing_check)` (INVALIDATING_CHECKS BC-01-06,08,09; BC-10 with REJECT_FACTUAL/REJECT_PRESERVATION) - cli.py:2796. Other failing checks (e.g. BC-07, BC-11, BC-12) do not invalidate.
- **SUPERSEDED**: `_supersede_siblings` (seal.py:971) older READY revisions once a newer one is proven.
- **Portfolio funnel** (`bundle/portfolio.py::_assess`, 243-338): depth 1 fact-valid (state READY/VALID_UPDATE and BC-01..06,08,09 PASS at the same revision); depth 2 presentation-valid (BC-07 PASS); depth 3 independently accepted (**halts at depth 2 with bucket `update_available` if state is VALID_UPDATE_AVAILABLE *or the directory is in `stale_directories`*** - line 295; then review.json verdict ACCEPT + BC-10 PASS); depth 4 no-op-proven (manifest `no_op_proof` byte_identical/fresh_process True/provider_calls 0, BC-11 PASS); 5 source-fresh (needs `--drift`); 6 publication-eligible (mode `full` and `RATIFIED` acceptance profile score PASS); 7 effect-authorized (valid authorization record supplied via `--authorizations`).
- **Headline** (`candidates: N/36`): `current_reproducible_no_op_proven(portfolio, reproducible)` (portfolio.py:220) = entries with depth >= 4 **and** in `reproducible_repositories(root)` (reproducibility.py:63: re-render README in memory from sealed facts/plan/content_units/dispositions under the running renderer and compare bytes with sealed README.md).

**Why it is 0 today (verified)**: running `status --stale` printed `candidates: 0/36`, `30 ever sealed, 30 integrity-valid, 0 current-code reproducible, 0 independently accepted`, `29 READY_FOR_PROPOSAL (counted); 1 VALID_UPDATE_AVAILABLE`, `portfolio ... fact-valid 30, presentation-valid 30, independently accepted 0, no-op-proven 0`, `partition: no_bundle 6, update_available 30`. Two independent causes, either sufficient:
1. All 30 CURRENT bundles are stale. Running code: SHELL 6, RENDERER 30, NORMALISATION 29, REVIEWER_LOGIC 17, VALIDATOR_VERSION 15 (+ BC-02 4, BC-05 2, BC-06 7, BC-07 10, BC-10 5, BC-11 2). Sealed bundles carry e.g. renderer 18-28, normalisation 2-21, reviewer_logic 2-15, validator_version 3-7. `portfolio._assess` therefore stops every one at depth 2 (`update_available`).
2. 0 bundles reproduce: I rendered all 30 under the current code in memory (no exceptions); each differs from its sealed README by 2-36 diff lines. So `reproducible` is empty regardless.
The cursor (`project/state.yaml progress.current_candidates: 29`) tracks the READY count and `status` exits 1 if it disagrees with `count_current_candidates` (cli.py:2326); the AGENTS.md "N/34 current reviewable no-op-proven" headline is a different, stricter number.

### Q3. CLI commands: re-check, propose, issue filing, and their gates

**Re-checking an existing sealed bundle offline: there is no dedicated command.** Closest existing pieces:
- `status [--stale] [--json] [--drift P] [--authorizations P]` (cli.py:2175): offline, zero LLM; verifies bundle integrity of every CURRENT bundle, scans candidates/ for leaked secrets, computes staleness, re-renders READMEs (`reproducible_repositories`), builds portfolio funnel, routing dry run with `--stale`. It does **not** re-run validators or the reviewer.
- `sealed-ready --repo R` (1086): exit 0 only if CURRENT bundle verifies and state == READY_FOR_PROPOSAL (`ready_revision`). Checks nothing about staleness/proof.
- `verify-noop-proof --first A --second B` (2479): needs two `present --invocation-record` files from real reruns.
- `present --facts-only` (clone + extraction, no LLM) and `monitor` (network, read-only).
Gates: `status`/`sealed-ready`: none (project root only). `monitor`: `GH_TOKEN` required (1147), registry; `present`: gateway env, catalog from `preflight`, `GH_TOKEN` optional (anonymous clone otherwise).

**Propose a PR** - three commands:
- `draft-proposal-authorization --repo R --approver NAME [--base-branch] [--expires-in-hours<=168] [--supersedes-pr N]` (2103): needs registry mode `full` + active (`require_write_permitted(..., "readme_proposal")`), `load_proposable_candidate` (CURRENT verifies, state READY, README listed), live head read (`GH_TOKEN` optional) must equal the bundle revision. Writes `ops/proposal-authorizations/<owner>__<name>__<hash12>.json`; a human must merge it to `origin/main`.
- `propose --repo R [--authorization-record P] [--trigger-sha S] [--base-branch B]` dry run (1888): reports plan; reads live head with `GH_TOKEN` and requires equality with bundle revision (else `source_moved`, exit 3); if a record is given, runs `verify_record_provenance` + `validate_authorization`. `--local-test-readme-file` is a dry-run-only path that skips registry/bundle checks and refuses `--propose`.
- `propose ... --propose` write: requires in order: registry entry `full` and active (`require_write_permitted`), CURRENT bundle verified + READY_FOR_PROPOSAL, env `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` in {1,true,yes}, `GH_PROPOSAL_WRITE_TOKEN` present and verified as a `ghs_` installation token whose reach is exactly the target (`token_provenance`), authorization record committed on `origin/main` and an ancestor of `--trigger-sha`/`$GITHUB_SHA`/HEAD (full-history checkout), record fields == candidate (repo, sha256 of README text, revision, base branch, branch, policy_version `1`, unexpired, <=7d), live source revision recheck, no settled (merged/closed) presenter PR unless the record lists it in `supersedes_prs`, App attribution of PR (id 5092474). Currently `data/registry.json`: 34 `dry_run`, 2 `full` (3D-Java, Cells-Java); `ops/proposal-authorizations/` does not exist (none ever committed). Hosted path: `propose.yml` runs `sealed-ready` then `propose`, with the env flag set only in its "Propose for real" step.
- NOT gated by `propose`: staleness vs the running code, acceptance-profile `RATIFIED`, BC-11/no_op_proof existence. Those are only portfolio/status concepts.

**File an upstream issue**:
- `issue-targets` (1503) prints the matrix of repos with PENDING/FILED handoffs.
- `file-upstream-defects [--repo R] [--file] [--approvals-ref REF] [--count-writable]` (1552): default is dry run (read-only checks; `GH_TOKEN` optional). `--file` requires `--repo`, registry `full` (`issue_filing` permit), env `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` truthy, `GH_ISSUES_WRITE_TOKEN` verified as installation token scoped to exactly the target, a committed unexpired per-handoff owner approval `ops/issue_approvals/<handoff-id>.json` read from git at `--approvals-ref` (digest must match the handoff), upstream dedup via fingerprint marker scan, and a recheck that the defect still fires. `ops/issue_approvals/` contains only a README: nothing approved today.
- `redetect-upstream-defects [--repo] [--apply] [--close]` (1286): `--apply` writes a local status transition only; `--close` needs the same gates plus a separate `ops/issue_close_approvals/<id>.json` and a live issue carrying the marker.
- Handoff creation is automatic inside `present` (cli.py:2811) when BC-02 fails with a real non-SUPPORTED install fact.
- `metadata --repo R [--apply]` (1758): dry-run capture/diff; `--apply` needs registry `full` (`metadata_write`), env `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED`, `GH_METADATA_WRITE_TOKEN`. **No token-provenance verification** unlike propose/issues.

Other commands: `sealing-plan` (read-only planner, forces `qwen3-next`, pause var), `monitor`, `monitor-install-record`, `monitor-install-summary`, `monitor-drift-contract`, `stage-transaction-artifact`, `preflight` (needs gateway env; writes `runs/preflight/catalog.json`), `health-check` (reads git state ref; needs `REPOSITORY_PRESENTER_STATE_TOKEN` in CI).

### Q4. Dead code, duplicated authority, bypasses, hidden fallbacks, manual-only steps

Dead / unreachable
- `core/long_paths.exceeds_max_path`, `core/github/client.find_open_pull_request`, `core/state/cas.renew_lease`, `cas.lease_is_current` have no production caller.
- `core/state/recovery.recovery_sweep(current_source_revisions=...)` is never given a value in production -> the SUPERSEDED path never runs.
- Durable `RepositoryRecord` fields `source`, `surfaces`, `dependencies`, `accepted_artifact`, `proposal` are never written; states `AWAITING_AUTHORIZATION`, `PROPOSING`, `UNCHANGED`, `MONITORING` are only used as traversal hops, never entered by propose/monitor. The durable state machine is a receipt-only sidecar with no decision authority; it can disagree with `manifest.state`.
- `core/github/__init__.py` docstring is false (says no write calls exist).
- `RENDERER_VERSION` is assigned three times in `renderer.py` (82, 90, 96; effective 30) - comment-log-as-code.

Duplicated authority / drift risk
- Candidate state: manifest `state` string (authority for count/propose) vs durable git-ref record vs `project/state.yaml progress.current_candidates` (29) vs the `status` headline (0). Two different "N" in one `status` output, and `status` exits 1 on cursor/READY mismatch.
- "Stale" is defined twice: `candidates.stale_candidates` (components + validators only) vs `bundle/evaluation.evaluate` + `portfolio_routing` (adds prompts, policy, contract, acceptance profile, extractor/environment). The funnel's stale exclusion uses only the narrow one; a prompt-only change leaves candidates "not stale" in the headline.
- Constants duplicated across core/components "because core may not import components": `CURRENT_FILENAME` (candidates.py:39 and seal.py:116), `DEPENDENCIES_FILENAME`, `README_FILENAME`, `REGISTRY_RELATIVE_PATH` (loader.py:21 and reproducibility.py:31); `present_transaction.POLICY_VERSION` ("readme-contract-v1-draft") vs `seal.CONTRACT_VERSION` ("readme-contract-v1") despite a comment saying they are the same; `facts.read_facts` vs `reproducibility._load_facts` (two sealed-facts readers); `COUNTED_STATES` vs `portfolio.STATE_READY`.
- Budgets: ledger hard cap 100 calls/invocation (ledger.py:46) vs health alert 500 (health.py:47).

Bypasses / weak points
- READY_FOR_PROPOSAL is trusted from a single manifest string: `verify_bundle` does not cross-check state against `no_op_proof`, nor hash/sign the manifest, nor flag extra unlisted files. A hand-edited `state` makes `ready_revision`, `count_current_candidates`, `sealed-ready` and `load_proposable_candidate` accept it. Only the portfolio funnel (`_no_op_proven`, BC-11) looks at the proof.
- `propose --propose` does not consult staleness, BC-checks, or the acceptance profile: all 30 (stale) bundles would pass the bundle gate; the stricter "publication-eligible" in `status` is advisory only.
- Registry `active` is honoured only by `require_write_permitted`; `require_listed`, `enabled_entries`, `monitor`, `sealing_plan` ignore it (no entry is inactive today).
- `metadata --apply` skips token-provenance verification that propose and issues enforce.
- None of the 30 on-disk manifests has `ledger_totals`, `sealed_by`, `upstream_blobs`, or a measured `no_op_proof.rerun` (checked by script). So `reconcile_ledger` returns immediately (candidates.py:159 / noop_proof.py:474), the process-identity no-op proof has never been applied to any sealed bundle, their proofs are the legacy literal shape (`fresh_process: true`), and `monitor` reports UNKNOWN for all of them (no blob ids). Only 5 manifests record `models_used`.
- `select_models` live probes are outside the "zero provider calls" proof (see Q1).
- Cache re-judging (`run_job` 571) means a replay silently costs calls after any validator/normalisation change; `ProviderCallBudgetError` only triggers at 100.

Hidden fallbacks
- `read_sealing_history_contract` returns `()` on any error (intentional, but means failure-memory silently disappears).
- `_portfolio_report` returns None without a registry; `reproducible_repositories` silently skips any bundle it cannot render (exceptions swallowed) - "0 reproducible" cannot distinguish "renders differently" from "cannot render" (I confirmed here it is the former).
- `reproducible` and `held_updates` skip unreadable manifests quietly; `examples_verification_summary` ignores bad JSON.
- `toolchains` falls back across registry/PATH/install-root with machine-specific Windows paths; results get hashed into `environment.toolchains`, so the same repo seals differently on different machines.
- `_trigger_commit` falls back to local `HEAD` when no `--trigger-sha`/`GITHUB_SHA`.
- Packet caps (SYMBOL_CAP etc.) silently drop facts from LLM view.

Manual-only steps
- `preflight` must be run before `present` (catalog under gitignored `runs/`).
- Authorization record: human drafts (or runs `draft-proposal-authorization`), reviews, merges to `origin/main`; max 7-day life; owner sets `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`, mints installation tokens.
- Owner approvals for issues in `ops/issue_approvals/` and `ops/issue_close_approvals/`.
- Flipping a repo to registry `mode: full` (hand edit of `data/registry.json`); ratifying the acceptance profile (`RATIFIED=False` in code).
- Cursor `project/state.yaml` must be edited by hand to match disk counts.
- Version bumps (`RENDERER_VERSION`, `NORMALISATION_VERSION`, `REVIEWER_LOGIC_VERSION`, check versions) are manual; forgetting one means silent non-staleness.
- Re-sealing after any component bump is a manual `present` (or the scheduled sealing workflow, capped at 3 repos/run, qwen3-next only).

### Q5. What in core/ already supports "recheck sealed bytes against current validators with zero LLM calls"

Present in core/ (reusable as-is):
- `candidates.verify_bundle` (digest inventory + schema version + ledger totals), `candidates.load_proposable_candidate` / `ProposableCandidate` (README bytes, `candidate_hash`), `candidates.stale_candidates`, `iter_sealed_bundles`, `_verified_current`.
- `noop_proof.reconcile_ledger`, `ledger_totals`, `load_records` (ledger.py) to verify the sealed proof claims against `calls.jsonl`; `measure_invocation`.
- `facts.read_facts` (sealed `facts.json`), `hashing.sha256_text`, `registry.loader.load_registry/find_entry`, `llm.prompts.load_manifests` (to compare prompt hashes with `dependencies.json`), `secrets.find_secret_leaks/scan_for_secrets` (BC-09-style canary over sealed bytes), `authorization.proposal.validate_authorization` (authorization recheck without network).
- A hard "no LLM" guard already exists: `Ledger(path, call_budget=0)` makes `reserve_provider_call()` raise `ProviderCallBudgetError` *before* any request (ledger.py:176-186, called in jobs.py `_Attempts.call` before the network). `transport.build_client` is the single network seam. `CallStore.get/record` and `jobs.request_hash(...)` allow cache-only lookups. `seal.seed_call_store/seed_additional_calls` rebuild a store from a bundle.
- Models: sealed `manifest.models_used` can stand in for `select_models` so that no availability probe is made.

Outside core but already offline/zero-LLM (what a recheck would call):
- `bundle/reproducibility.reproducible_repositories` / `render_readme(entry, facts, plan, units, dispositions)` - sealed-bytes re-render under the running renderer.
- `bundle/dry_run.portfolio_routing` + `evaluation.evaluate` + `seal.code_dependencies` - which dependency classes changed and which state they would give.
- `validation.registry.validate_candidate(Candidate, transaction, secrets)` and `record_replay_verdict` - the validators themselves.

Gaps a recheck would hit:
- `validate_candidate` needs a `Candidate` with `original_readme` bytes (BC-01 hash check, registry.py:743), `tree_paths` (BC-06 relative links, :1279) and `tasks`; the sealed bundle contains `README.patch` (original->candidate diff) but not the original README, `source/tree.txt`, or snapshot. Reconstructing original bytes from the patch is possible in principle (unverified); `upstream_blobs` exists in new-format manifests only.
- BC-02/03/06 judgments depend on live probes and executed examples captured at seal time (`examples.json`, `probes.json`, facts evidence); a pure recheck can validate against those recorded receipts but cannot re-prove them.
- `run_job` has no cache-miss-fails-offline mode other than the `call_budget=0` trick; with it a miss raises `ProviderCallBudgetError` (typed, non-retryable).
- No existing function composes these into "bundle -> verdict"; `status` stops at integrity + render equality + versions.
- Legacy manifests (all 30 on disk) lack `ledger_totals`/`sealed_by`/`upstream_blobs`, so integrity-of-proof checks degrade to "skip".
