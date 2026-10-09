# Repository Presenter

Repository Presenter is an autonomous, GitHub-native system that keeps the README files of
authorized product repositories accurate, credible, repository-specific, and current. Deterministic
code owns evidence, validation, state, and safety; a configurable LLM owns product interpretation,
editorial planning, composition, and independent review. README health is the first component;
other repository-presentation surfaces are planned to follow through the same core.

It is the successor to the legacy `babar-raza/foss-readme-optimizer` repository. Legacy behavior
migrates here only through the pull-based ledger in
[`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) — a file enters when a gate
actually needs it, never as a bulk port.

**Contents:** [Status](#project-status) · [Quick start](#quick-start) ·
[Mental model](#mental-model) · [How it works](#how-it-works) · [Repository map](#repository-map) ·
[Hosted workflows](#hosted-workflows) · [Built vs planned](#scope-built-vs-planned) ·
[Contributing](#contributing-as-a-human) · [For coding agents](#for-coding-agents) ·
[Configuration](#configuration) · [CLI reference](#cli-reference) ·
[Security](#security-and-effects) · [Docs](#project-documentation)

## Project status

Active development, not a stable release. Source install only — there is no PyPI package.

**Snapshot as of 2026-10-05** (the live numbers are whatever `repository-presenter status` prints
today; [`project/state.yaml`](project/state.yaml) is the one live cursor and wins over this table):

| Question | Answer |
|---|---|
| Accepted gates | `G0_FOUNDATION`, `G1_FIRST_VALID_CANDIDATE`, `G2_STABILITY_UNDER_CHANGE` |
| Current gate | `G3_PYTHON_COHORT` (READY) |
| Active work item | `G4-W17` — landing shared-code fixes from the lane agents, and resealing candidates they invalidate |
| Progress | **28 of 36** registry repositories hold a current, reviewable, no-op-proven candidate (29 ever sealed; 5 registry entries have no bundle yet; 2 are disabled) |
| Pending update | 1 candidate (`Aspose.Slides-FOSS-for-Java`) is `VALID_UPDATE_AVAILABLE`: still valid, update not yet re-sealed |
| Independent acceptance | 0 candidates — the 30-point acceptance profile is still advisory, not ratified (`G3-W02`) |
| Pull requests against target repos | **None opened yet.** The proposal path is built and gated; its first live proof is open (see below) |
| Hosted operation | Workflows exist and are wired; the scheduled, unattended path has not yet been proven by a real cron-fired run |

What is blocking the next milestones (`BLOCKED_EXTERNAL`, owner decisions — not code defects):

- **First real pull request.** `propose.yml` was dispatched twice on 2026-10-04 and stopped at
  GitHub App token minting (installation lookup returned HTTP 404). The disposable-target proof
  (create, update without duplicate, stale-source block, lost-response reconciliation) has not run,
  and every repository's first real PR also needs its own fresh owner authorization.
- **Unattended scheduling.** `monitor.yml` has a schedule trigger, but no cron-fired run has been
  reconciled against local state yet (`G7-W06`).

Do not copy these numbers into other documents; they change with nearly every merged work item.

## Quick start

**Goal: see the system work in about five minutes, with no credentials.**

```bash
git clone https://github.com/babar-raza/repository-presenter.git
cd repository-presenter
python -m venv .venv
.venv\Scripts\pip install -e .[dev]      # Windows
# .venv/bin/pip install -e .[dev]        # macOS/Linux
git config core.hooksPath .githooks      # once per clone: runs scripts/ci_check.sh before push

repository-presenter status              # gate, work item, candidate count — read-only, no network
repository-presenter status --stale      # which sealed candidates the running code has outgrown
bash scripts/ci_check.sh                 # the same checks CI runs (lint, format, types, tests, smoke)
```

Look at a finished product: any `candidates/<owner>__<name>/CURRENT` points at a sealed bundle
whose `README.md` is the proposed README and whose `facts.json`, `plan.json`, `validation.json`,
and `review.json` show how it was derived and checked.

To run the real pipeline on one repository you need an LLM gateway and, optionally, a read-only
GitHub token — see [Configuration](#configuration) and the [Example](#example).

## Mental model

| Term | Meaning |
|---|---|
| **Registry** | [`data/registry.json`](data/registry.json): the hard allow-list of admitted repositories (36 entries across 15 `aspose-*-foss` organizations; Python 13, .NET 9, Java 4, C++ 4, TypeScript 3, Go 2, Rust 1). Nothing outside it is ever reached. |
| **Mode** | Per registry entry: `dry_run` (analyze and seal locally, can never write), `full` (may propose, if separately authorized), or `disabled`. |
| **Facts** | Deterministic, provenance-bound claims extracted from an immutable upstream revision. Every public README claim must map to one. |
| **Candidate / bundle** | A proposed README plus the content-addressed evidence that justifies it, under `candidates/<owner>__<name>/<revision>/`; `CURRENT` points at the live one. |
| **Seal** | Writing a bundle after every blocking check and the independent review pass. |
| **No-op proof** | Re-running against a sealed revision reproduces byte-identical output with **zero** LLM calls. |
| **Gate / work item** | Build-order milestones (`G0`–`G7`) and the numbered items inside them. [`project/state.yaml`](project/state.yaml) says which is active. |
| **Cursor** | `project/state.yaml` — the only record of implementation status. |
| **Handoff** | A local, evidence-backed record of a genuine upstream product defect, which may become a GitHub issue (gated). |
| **`BLOCKED_EXTERNAL` / `FAILED_INTERNAL`** | Blocker classes: something only an owner can supply, versus a defect in this code. The second is never an acceptable stopping point. |

The unit of progress is one: **current reviewable no-op-proven candidates, N/36**. Code volume,
plans, and evidence files are supporting work, not progress.

## How it works

The LLM proposes; deterministic code disposes. The LLM interprets a repository and returns typed,
fact-ID-bound content — it never writes the final Markdown, never advances durable state, never
grants authorization, and never mutates a repository. Deterministic code owns commands, links,
badges, diagram topology, identifiers, validation, every state transition, and every GitHub effect.

```
 pinned snapshot ─▶ facts ─▶ investigation ─▶ reconciliation ─▶ planning ─▶ composition
 (read-only clone)  (7 ecosystem   (LLM: gaps)     (LLM: keep/merge/      (LLM)      (LLM units →
                     extractors)                    drop each unit)                   deterministic
                                                                                      Markdown renderer)
        ─▶ validation ─▶ independent review ─▶ targeted repair ─▶ seal ─▶ (gated) propose PR
           (blocking     (separate from the   (route to the      (bundle +   one stable branch,
            checks)       author)              causal stage)      no-op      authorized per repo)
                                                                  proof)
```

- **Truth.** The exact immutable upstream revision is the factual authority. An existing README is
  valuable evidence, not automatic truth; every material source README unit gets exactly one
  explicit disposition (kept, merged, rewritten, dropped).
- **Defects route to their earliest cause.** A failing check is never weakened to hide an upstream
  defect; repair goes back to the stage that caused it.
- **Invalidation is input-based.** A candidate is invalidated only through an input it consumed.
  Validator or reviewer changes re-check it and may yield `VALID_UPDATE_AVAILABLE`, never blanket
  invalidation.
- **Placeholder repositories** (README/license only) return `insufficient_evidence`; no candidate
  is fabricated.

The sealed README's shape and its blocking checks are specified in
[`docs/README_CONTRACT.md`](docs/README_CONTRACT.md). Full runtime design (scheduling, proposal,
effect authorization) is in [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md); build order is in
[`docs/EXECUTION_STATE_MACHINE.md`](docs/EXECUTION_STATE_MACHINE.md).

## Repository map

```
src/repository_presenter/
  cli.py                      the one entry point (also: python -m repository_presenter)
  cursor.py                   reads project/state.yaml and sealed bundles for `status`
  core/                       reusable capabilities, no README-specific logic:
                                registry, snapshot, git_safety, facts, llm (gateway, call cache),
                                state (durable CAS/lease/recovery), authorization, github,
                                secrets, grammars, toolchains, sealing_plan
  components/
    readme/                   the README transaction: extractors/ (one per ecosystem), evidence,
                              investigation, reconciliation, composition, validation, review,
                              repair, bundle (sealing, portfolio counts), upstream_defects
    metadata/                 repo description/topics/homepage: observe, propose, gated apply
    issues/                   upstream-defect ledger, handoff drafting, redetection, gated filing
    propose/                  the PR effect: idempotent branch/commit/PR, gated write
    monitor/                  read-only drift observation of upstream default branches
prompts/                      one governed YAML manifest per LLM job
schemas/                      JSON Schemas: state, manifest, bundle
data/registry.json            the admitted-repository allow-list
candidates/<owner>__<name>/   sealed bundles per revision, plus a CURRENT pointer
evidence/                     build/gate evidence, upstream-defect handoffs, SBOM — redacted, checksummed
ops/                          owner approval records (issue_approvals/; proposal authorizations)
tests/                        mirrors src/ path-for-path, plus flat repo-wide invariant tests
docs/  plans/  project/       authority documents, product authority, live cursor
migration/                    legacy reuse ledger
tools/                        owner/reviewer tooling — never imported by the product
.github/workflows/            hosted automation (below)
```

Where a new file belongs is decided by [`docs/REPOSITORY_LAYOUT.md`](docs/REPOSITORY_LAYOUT.md):
README-specific work under `components/readme`, reusable capabilities under `core`, ecosystems and
families through registries rather than central `if/elif` chains.

## Hosted workflows

| Workflow | Trigger | Does | Writes? |
|---|---|---|---|
| `ci.yml` | push, PR | Ruff, mypy, pytest on Python 3.11/3.12/3.13; SBOM and vulnerability audit. Red CI is a production defect. | no |
| `monitor.yml` | cron (every 6 h), manual | Observes each enabled repository's upstream head vs its `CURRENT` bundle; records drift evidence | no |
| `present.yml` | manual / dispatch | One isolated, durable-state-backed README transaction for one repository, with a fresh per-repository App token | state ref on this repo only |
| `sealing-scheduled.yml` | scheduled | Plans (≤3 `DRIFTED` repositories per run, `qwen3-next` only), seals, and hands sealed candidates to `propose.yml`; owner can pause with `REPOSITORY_PRESENTER_SEALING_PAUSED=1` | proposal leg only when authorized |
| `propose.yml` | manual / `workflow_call` | Opens or updates the one stable presenter PR on a target — the only target-write path | **yes**, gated (see [Security](#security-and-effects)) |
| `issues-scheduled.yml` | cron (daily) | Read-only defect analysis per repository; gated filing and closing of upstream issues | gated |
| `liveness.yml` | cron (every 30 min) | Out-of-band dead-man check; detects and fails loudly, repairs nothing | no |
| `verify-app-installation.yml`, `audit-app-installations.yml` | manual | Prove the GitHub App can mint a read-only token for one repository / every registry organization | no |
| `mirror-gitlab.yml` | push to `main` | Keeps a GitLab mirror of `main` and tags current (non-forced) | GitLab mirror |

## Scope: built vs planned

| Capability | Status |
|---|---|
| Snapshot → facts → investigation → reconciliation → planning → composition → validation → independent review → repair → seal | **Built**; 28 current sealed candidates |
| Deterministic Markdown renderer; the LLM never writes the final document | **Built** |
| Multi-ecosystem extraction (Python, .NET, Java, C++, Rust, Go, TypeScript) with pinned per-language tree-sitter wheels (no parser is downloaded at run time) | **Built**; sealed candidates exist for all seven |
| Safety: pinned, read-only, push-neutered clones; secret-canary scan before sealing | **Built** |
| Durable state (content-addressed storage, leases, fencing tokens, recovery) | **Built** (`core/state/`) |
| Drift monitoring (`monitor`) and unattended sealing plan (`sealing-plan`) | **Built**; the scheduled path is not yet proven by a real cron-fired run |
| Upstream-defect detection, re-detection, and gated issue filing/closing | **Built**; one live write proof exists (an issue on this control repository, not on a product repository) |
| Repo description/topics/homepage: observe, propose, diff | **Built**, read-only; applying is gated and unproven live |
| GitHub App credentials installed across the registry organizations | **Built** — a credential existing is not write authorization |
| Pull-request proposals (`propose`) | **Built and gated; first live disposable-target proof still open** (`G6-W02`) |
| Acceptance contract v1 frozen as a ratified 30-point profile | **Planned** (`G3-W02`); only the version constants are frozen so far |
| Hosted, autonomous portfolio operation in production | **Planned** (`G7-W06`) |
| Visual-asset / social-preview preparation; community and security file generation; release-link auditing | **Planned** |

## Contributing (as a human)

1. Read the [Quick start](#quick-start), then [`AGENTS.md`](AGENTS.md) — it governs conduct for
   people and agents alike — and `project/state.yaml` for what is active right now.
2. Pick the smallest coherent change that closes a gate predicate. Only one shared-code item is
   active at a time; disjoint paths may run in parallel.
3. Change code and its tests together. Behavior changes need focused tests, including negative
   controls (hallucinated or malformed model output, illegal transitions, stale evidence, secret
   leakage, duplicate effects). Unit tests do not prove live LLM, hosted, or GitHub behavior.
4. Run the broad checks, then finish any work item with a run of the official entry point
   (`repository-presenter present …`) on the canary — a module with no production importer is a
   defect, not a deliverable.
5. Open a branch and PR against `main`. `main` is protected: the three CI jobs
   (Python 3.11/3.12/3.13) are required and PRs auto-merge on green. Never force-push, never push to
   a product repository.

```bash
ruff check . && ruff format --check . && mypy src && pytest      # or: bash scripts/ci_check.sh
```

Reproduce CI's exact environment from the hashed lock file:
`pip install -r requirements-lock.txt && pip install --no-deps -e .`

Requirements: Python 3.11+; core dependencies `httpx`, `jsonschema`, `markdown-it-py`, `openai`,
`packaging`, `pydantic`, `tenacity`, `pyyaml`, plus pinned per-language `tree-sitter` wheels.

## For coding agents

This section is a map, not the rules — the rules live in [`AGENTS.md`](AGENTS.md) (≤200 lines).

**Read order at session start**

1. [`project/state.yaml`](project/state.yaml) — the only live cursor (it is large; read it in
   sections, or run `repository-presenter status` first).
2. The current gate in [`docs/EXECUTION_STATE_MACHINE.md`](docs/EXECUTION_STATE_MACHINE.md).
3. [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) for runtime behavior, and
   [`docs/README_CONTRACT.md`](docs/README_CONTRACT.md) when touching facts, composition,
   validation, or review.
4. [`docs/RESEARCH_AND_GUIDELINES.md`](docs/RESEARCH_AND_GUIDELINES.md) and
   [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) (§31) for context and recent decisions.
5. [`plans/idea.md`](plans/idea.md) — the product outcome standard; never a task list.

**Who owns what** — never create a competing plan, roadmap, or status file:

| Subject | Owner |
|---|---|
| Product outcome, standing constraints | `plans/idea.md` |
| Agent conduct and safety | `AGENTS.md` |
| Build order, gate acceptance | `docs/EXECUTION_STATE_MACHINE.md` |
| Runtime behavior | `docs/STATE_MACHINE.md` |
| README shape and blocking checks | `docs/README_CONTRACT.md` |
| File placement | `docs/REPOSITORY_LAYOUT.md` |
| Current implementation status | `project/state.yaml` |
| Legacy reuse | `migration/reuse-manifest.yaml` |
| Supervision and lanes | `docs/SUPERVISION.md` |
| Recurring defect classes (3 sightings = priority) | `docs/DEFECT_INDEX.md` |
| Implemented interfaces | `schemas/` and tests |

**Invariants that catch agents out**

- The LLM never advances state, grants authorization, asserts a gate result, or writes to a
  repository. Put deterministic things (links, commands, hashes, transitions) in code.
- Templates are presentation assets, never sources of facts, package names, or commands.
- Do not weaken a downstream check to hide an upstream defect; route to the earliest causal stage.
- Two equivalent failed attempts, or 15 minutes without narrowing the cause, forbids a third:
  write a first-principles diagnosis and change the evidence, prompt, model, component, or boundary.
- A candidate reaching `READY_FOR_PROPOSAL` never implies publication authorization.
- Update the cursor in the same commit that establishes its claimed state; AI-authored commits carry
  a `Co-Authored-By` trailer; after a push, watch CI to completion and fix red immediately.
- `tests/test_readme_reference.py` fails if a CLI subcommand or flag is missing from this README —
  update the [CLI reference](#cli-reference) whenever the parser changes.

**Handy commands for orientation:** `repository-presenter status --json` (machine-readable),
`repository-presenter status --stale`, `repository-presenter sealed-ready --repo OWNER/NAME`,
`repository-presenter present --repo OWNER/NAME --facts-only` (no provider calls).

## Configuration

The CLI reads credentials from the process environment, never from a `.env` file (see
[`.env.example`](.env.example) for the documented names only):

| Variable | Required for | Notes |
|---|---|---|
| `GPT_OSS_ENDPOINT` | `present`, `preflight` | OpenAI-compatible chat-completions gateway URL |
| `GPT_OSS_API_KEY` | `present`, `preflight` | Read once, never printed or written to disk |
| `GPT_OSS_MODEL` | optional | Overrides a prompt manifest's default model route; local experimentation only |
| `GH_TOKEN` | optional | Repository-scoped, read-only; used for `present`'s clone step and `metadata`'s `GET /repos/{owner}/{repo}` call |
| `GH_METADATA_WRITE_TOKEN` | optional | Write-scoped, distinct from `GH_TOKEN`; only `metadata --apply` reads it, and only after `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED` also authorizes a write |
| `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED` | optional | Owner-controlled go-ahead for `metadata --apply`'s write; a token's mere presence never implies this |
| `GH_ISSUES_WRITE_TOKEN` | optional | Write-scoped, distinct from `GH_TOKEN`; only `file-upstream-defects --file` and `redetect-upstream-defects --close` read it, and only after `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` also authorizes a write |
| `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` | optional | Owner-controlled kill switch for the issue filing and closing writes (`file-upstream-defects --file`, `redetect-upstream-defects --close`): unset or not `1` disables every write; `1` never authorizes a filing by itself (that needs the handoff's own `ops/issue_approvals/` record), and a token's mere presence never implies it. In CI it is set only from the repository variable of the same name, on the gated write job |
| `GH_PROPOSAL_WRITE_TOKEN` | optional | Write-scoped, distinct from `GH_TOKEN`/`GH_METADATA_WRITE_TOKEN`/`GH_ISSUES_WRITE_TOKEN`; only `propose --propose` reads it, and only after `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` also authorizes a write |
| `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` | optional | Owner-controlled go-ahead for `propose --propose`'s write; a token's mere presence never implies this |
| `GH_CANDIDATES_WRITE_TOKEN` | optional | Write-scoped, distinct from every token above; only `publish-candidates --publish` reads it, and only after `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED` also authorizes a write. In CI it is the job's own ambient `GITHUB_TOKEN` (G7-W14: the write target is this control repository itself, so no GitHub App installation token is needed) |
| `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED` | optional | Owner-controlled go-ahead for `publish-candidates --publish`'s write; a token's mere presence never implies this |
| `REPOSITORY_PRESENTER_SEALING_PAUSED` | optional | Owner pause switch for the scheduled sealing run (`sealing-scheduled.yml`, a repository Actions variable): exactly `1` makes `sealing-plan` report `has_work=false` with the notice "sealing paused by owner variable" (also written to the step summary), so no seal or propose leg starts; unset or any other value leaves sealing enabled, bounded by the three-repositories-per-run cap |

`GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY` are required even for `present --facts-only`: the gateway
configuration loads before that flag's short-circuit.

## CLI reference

The package installs one console script, `repository-presenter` (equivalently, `python -m
repository_presenter`).

```
repository-presenter --version
repository-presenter status [--root PATH] [--stale] [--json] [--drift PATH] [--authorizations PATH]
repository-presenter preflight [--root PATH]
repository-presenter present --repo OWNER/NAME [--root PATH] [--facts-only] [--fresh]
  [--invocation-record PATH]
  [--durable-state [--trigger-event-type TYPE] [--workflow-run-id ID] [--holder-id ID]
                    [--state-remote REMOTE]]
repository-presenter verify-noop-proof --first PATH --second PATH [--root PATH]
repository-presenter monitor [--root PATH] [--owner OWNER] [--out PATH]
repository-presenter monitor-install-record --owner OWNER --outcome {success,failure} --repositories NAMES --out PATH
repository-presenter monitor-install-summary DIR [--summary PATH]
repository-presenter monitor-drift-contract DIR --out PATH
repository-presenter health-check --repo OWNER/NAME [--root PATH] [--state-remote REMOTE]
  [--wall-clock-seconds N] [--provider-calls N] [--max-wall-clock-seconds N]
  [--max-provider-calls N] [--stale-after-hours N]
repository-presenter redetect-upstream-defects [--root PATH] [--repo OWNER/NAME] [--apply] [--close]
repository-presenter file-upstream-defects [--root PATH] [--repo OWNER/NAME] [--file] [--approvals-ref GIT_REF] [--count-writable]
repository-presenter issue-targets [--root PATH]
repository-presenter metadata --repo OWNER/NAME [--root PATH] [--apply]
repository-presenter propose --repo OWNER/NAME [--root PATH] [--authorization-record PATH] [--trigger-sha SHA] [--base-branch NAME] [--propose]
repository-presenter propose --repo OWNER/NAME --local-test-readme-file PATH --source-revision SHA   # dry-run plan only; never writes
repository-presenter draft-proposal-authorization --repo OWNER/NAME --approver NAME [--root PATH] [--base-branch NAME] [--expires-in-hours N] [--supersedes-pr N]
repository-presenter publish-candidates --repo OWNER/NAME --import-dir PATH [--root PATH] [--control-repo OWNER/NAME] [--base-branch NAME] [--publish]
repository-presenter sealing-plan [--root PATH] [--drift-file PATH] [--history-file PATH] [--github-output PATH]
repository-presenter sealed-ready --repo OWNER/NAME [--root PATH]
repository-presenter stage-transaction-artifact --transaction DIR --staging DIR
```

- **`status`** — prints the version, current gate, active work item, and candidate progress read
  from sealed bundles on disk. `--stale` additionally reports any current candidate whose recorded
  dependencies are behind the running code's component/check versions; it is a pure read and makes
  no provider call. It also prints the portfolio block: `plans/idea.md`'s seven separated counts
  (fact-valid, presentation-valid, independently accepted, no-op-proven, source-fresh,
  publication-eligible, effect-authorized) and a partition placing every live registry entry in
  exactly one bucket; the predicates are defined in `components/readme/bundle/portfolio.py`.
  `--json` prints one machine-readable document instead. `--drift PATH` supplies a monitor drift
  document so source-fresh can be observed (otherwise it is reported unobserved), and
  `--authorizations PATH` supplies authorization records for the effect-authorized count.
- **`preflight`** — reaches the LLM gateway using the process environment, lists its live models,
  and records the catalog under `runs/preflight/catalog.json`.
- **`present --repo OWNER/NAME`** — runs the full transaction for one repository listed in the
  registry: snapshot, facts, investigation, reconciliation, planning, composition, validation,
  independent review, and seal. `--facts-only` stops after the facts stage with a processability
  and coverage record, making no provider call. `--fresh` skips seeding this run's call cache from
  the sealed bundle's own history, forcing every job to make a genuinely live call. `--durable-state`
  (G5-W05) wires G5-W04's durable-state backend around the same, otherwise-unmodified run — a
  recovery sweep, trigger admission/deduplication, and a committed transition receipt against this
  control repository's own git-ref state store, never the target repository; it is what
  `.github/workflows/present.yml` uses, and a plain local run never needs it. `--trigger-event-type`,
  `--workflow-run-id` (defaults to `GITHUB_RUN_ID`), `--holder-id`, and `--state-remote` (defaults to
  `origin`) configure that wiring; see `core/state/present_transaction.py` for the full design.
- **`verify-noop-proof`** — the hosted gate on a no-op rerun. Given the two `present
  --invocation-record` files of a run and its rerun, it requires the two to have been different
  processes (process id, start time, boot marker and an in-memory nonce all recorded, none assumed)
  and counts the rerun's provider calls from the call ledger it wrote, never from an exit code; a
  nonzero count, a missing ledger, an invocation that recorded nothing, or one process claiming
  both runs each fails with a typed reason. `present.yml` runs it after its second invocation.
- **`monitor`** — observes each enabled registry repository's upstream default-branch head with the
  read-only `GH_TOKEN` and compares it with its `CURRENT` sealed bundle's revision, recording one
  status per repository (`CURRENT`, `DRIFTED`, `NO_BUNDLE`, `UNREACHABLE`) in a JSON evidence file
  under `runs/monitor/drift.json` (`--out` overrides the path; `--owner` limits the run to one
  owner's enabled entries). It makes no provider call and no write to any repository; it exits 1
  when any repository is `UNREACHABLE`, and the scheduled `monitor.yml` workflow runs it read-only.
- **`monitor-install-record`** / **`monitor-install-summary`** — `monitor.yml`'s own per-owner
  GitHub App installation bookkeeping (G7-W06). `monitor-install-record` turns one owner's token
  mint outcome (`--outcome success|failure`) into a state file under `--out`. A failed mint is never
  judged from the outcome alone, because the mint action hides the HTTP status: the command asks
  GitHub directly (`GET /repos/OWNER/NAME/installation`, authenticated as the App from
  `GH_APP_ID` / `GH_APP_PRIVATE_KEY`). Only a confirmed 404 is recorded as `NOT_INSTALLED` (a
  notice naming the owner, the App and `--repositories`, exit 0); any other answer (401, 403, 5xx,
  an unrecognized status, a network error, an unexplained failure, missing credentials) is
  `MINT_ERROR` and exits 1, failing that owner's leg. `monitor-install-summary DIR` reads every
  owner's state file under `DIR`, prints a `::notice::` per missing installation plus a markdown
  table (appended to `--summary` when given), and exits 1 only when no owner at all was
  `INSTALLED`. No token or key is ever written to disk.
- **`monitor-drift-contract DIR --out PATH`** — the handoff to the scheduled sealing run (G7-W06).
  `sealing-scheduled.yml`'s plan job downloads the `drift-*` artifacts of the latest successful
  `monitor.yml` run into `DIR` and merges them into the one sealing contract at `--out`. It refuses
  (exit 2, writes nothing) when an enabled owner or repository has no evidence (unless its App is
  `NOT_INSTALLED`, a notice) or when any evidence is older than 12 hours.
- **`health-check`** — dead-man monitoring for one repository's durable-state record (G7-W03), run by
  `present.yml` after each transaction. It reads the record (and the sealed bundle's `calls.jsonl`
  unless `--provider-calls` is given) and applies the deterministic rules in
  `core/state/health.py`: no record, a failed state, a stale last transition (`--stale-after-hours`),
  and wall-clock or provider-call budgets (`--max-wall-clock-seconds`, `--max-provider-calls`)
  against the observed `--wall-clock-seconds` and `--provider-calls`. `--state-remote` names the
  state remote. It only reads and reports; it makes no provider call and no state mutation.
- **`redetect-upstream-defects`** — re-evaluates each `evidence/upstream-defects/` handoff's own
  `triggering_check` against the target repository's current state (package-registry and GitHub
  Contents/tree reads) and reports whether it still fires. `--repo OWNER/NAME` limits the pass to
  one repository. `--apply` writes back the one schema-valid status change this can ever propose
  (`FILED` -> `RESOLVED_UPSTREAM`) without any GitHub call; a dry-run report otherwise. `--close`
  is the gated write: it closes the issue a `FILED` handoff points to, with the close reason the
  check proves (`completed` or `not planned`), and records `RESOLVED_UPSTREAM` only after GitHub
  confirmed the close. Without the gate it reports what it would close and makes no call.
- **`file-upstream-defects`** — files each eligible (`HANDOFF_PENDING`) `evidence/upstream-defects/`
  handoff as a real GitHub issue; dry-run by default (read-only: reports what would be filed, what
  is already filed upstream, and what would not be filed, with the reason). `--repo OWNER/NAME`
  limits the pass to one repository (required with `--file`). Each handoff is reported `WOULD-FILE` or
  `WOULD-NOT-FILE` with the reason. `--file` attempts the write, but only past explicit gates — the
  owner's kill switch `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED=1` (it can stop every write and
  never authorizes one), a write-scoped `GH_ISSUES_WRITE_TOKEN` (never `GH_TOKEN`), and an unexpired
  owner approval record `ops/issue_approvals/<handoff-id>.json` for that exact handoff, whose digest
  must match the handoff as it is now (`--approvals-ref` names the git ref it is read from;
  `--count-writable` prints how many handoffs the write job could act on). Before the write it searches the target
  for the handoff's fingerprint marker (so a fresh checkout cannot file a duplicate), rechecks that
  the defect still fires, and refuses on any inconclusive result. A handoff whose status is not
  `HANDOFF_PENDING` is skipped outright.
- **`issue-targets`** — prints, as compact JSON, the repositories with a pending or filed handoff.
  The scheduled `.github/workflows/issues-scheduled.yml` uses it as its matrix: a read-only analysis
  per repository always, and the gated write job only when the repository variable
  `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` is set to `1`.
- **`metadata --repo OWNER/NAME`** — workstream 2 capture and proposal, dry-run by default: reads
  GitHub's currently-observed `description`/`homepage`/`topics` for the repository, and, when a
  sealed `CURRENT` candidate exists, proposes a candidate value for each field derived only from
  already-verified facts, diffed against the observation. Makes one `GET /repos/{owner}/{repo}`
  call and prints the diff; no `PATCH`/`PUT` call is made without `--apply`. `--apply` attempts to
  write the diff, but only past two independent, explicit gates: the owner-controlled
  `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED=1`, and a write-scoped `GH_METADATA_WRITE_TOKEN`
  (never `GH_TOKEN`) — a production-scoped write credential now exists (see
  [Scope](#scope-built-vs-planned)), but the owner-controlled authorization variable is not set in
  this project's own environment, so `--apply` reports exactly why it wrote nothing rather than
  guessing or silently proceeding.
- **`propose --repo OWNER/NAME`** — creates or updates the one stable presenter branch and pull
  request proposing a README candidate to the target repository (G6-W02). It proposes exactly one
  thing: the repository's registry-admitted sealed `CURRENT` candidate, and only while that bundle
  is `READY_FOR_PROPOSAL` at the revision the target still has. Dry-run by default: prints the
  candidate hash, source revision and branch, checks source freshness with a read, and (with
  `--authorization-record`) reports whether that record would be accepted; it writes nothing. A
  `dry_run` registry entry can never get past this. `--propose` attempts the write, but only past
  independent, explicit gates, each refusing with a typed reason (exit `3`): a registry entry in
  mode `full`; an authorization record under `ops/proposal-authorizations/` — written by
  `draft-proposal-authorization`, reviewed and merged by a person, and merged to `origin/main`
  before the commit the run was triggered at (`--trigger-sha`, default `$GITHUB_SHA`), so the run
  that consumes it can never have created it; the owner-controlled
  `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED=1`; a `GH_PROPOSAL_WRITE_TOKEN` that is a GitHub App
  installation token scoped to exactly the target (never `GH_TOKEN`, never a personal access
  token); a fresh recheck of the target's live revision immediately before the write; and a
  pull-request history check, so a merged or closed presenter PR for the same candidate is not
  recreated unless the record names it. The mechanism is idempotent (a second, unchanged invocation
  writes nothing and opens nothing new). `--base-branch` overrides the target's default branch,
  read live from GitHub when omitted. `--local-test-readme-file PATH --source-revision SHA` assembles
  a dry-run plan for arbitrary content and skips the registry and bundle checks precisely because it
  can never write; combining it with `--propose` is refused.
- **`draft-proposal-authorization --repo OWNER/NAME --approver NAME`** — writes the authorization
  record for the repository's current `READY_FOR_PROPOSAL` candidate under
  `ops/proposal-authorizations/` (`--expires-in-hours` sets its window, at most 168;
  `--supersedes-pr N` explicitly permits a re-proposal after that merged or closed PR). Drafting
  authorizes nothing: the record counts only once a person has merged it.
- **`sealing-plan`** — the unattended sealing run's planner (G7-W06). Reads the drift monitor's
  output file (`--drift-file`, default `drift/drift.json`, root-relative) and selects only `DRIFTED`
  repositories that the registry lists and does not mark `disabled`, in sorted order, at most three
  per run; the rest are deferred. Also reads the sealing history file (`--history-file`, default
  `sealing/history.json`, root-relative; #1009 failure memory): a repository whose most recent
  recorded attempt there is `FAILED` is skipped for 24 hours unless the drift record shows a new
  commit since, so a repository stuck on the same unfixed defect stops burning a full provider-call
  budget every single run - each skip is a typed, logged reason, and the repository is retried
  automatically once the cooldown elapses, never abandoned. A missing or unreadable history file is
  never a failure; it just means nothing is skipped by it this run. Refuses to plan at all when a
  prompt manifest routes to any model other than `qwen3-next` or `GPT_OSS_MODEL` names one. Makes no
  provider and no GitHub call. `--github-output` appends the `repositories`, `has_work`,
  `publishable`, `has_publishable`, and `skipped` step outputs that
  `.github/workflows/sealing-scheduled.yml` reads.
- **`sealed-ready --repo OWNER/NAME`** — exits 0 only when the repository's `CURRENT` sealed bundle
  verifies and is `READY_FOR_PROPOSAL`; exits 1 otherwise, naming why. The scheduled workflow uses
  it to export a bundle for the gated proposal job and to refuse to propose anything else.
- **`publish-candidates --repo OWNER/NAME --import-dir PATH`** — commits the target repository's
  sealed `READY_FOR_PROPOSAL` candidate (downloaded to `--import-dir`, a `present.yml`-exported
  `sealed-<owner>__<name>` artifact) to this control repository's own `candidates/<slug>/` tree, on
  a dedicated branch, and opens or updates the one pull request that carries it (G7-W14). Dry-run
  by default: reports the revision and branch, and writes nothing. `--publish` attempts the
  commit/push/PR, but only past the owner switch
  `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED` and a write-scoped `GH_CANDIDATES_WRITE_TOKEN`
  that resolves to exactly `--control-repo` (default `$GITHUB_REPOSITORY`); idempotent by
  construction, so an unchanged candidate re-run commits and proposes nothing.
- **`stage-transaction-artifact --transaction DIR --staging DIR`** — copies a seal's transaction
  output to a staging directory for the failed-run artifact that `present.yml` uploads. It
  excludes the `calls/` call store and every file holding a configured secret's value or a
  secret-shaped value, naming each exclusion by path and reason, never by value.
- `--root PATH` — project root holding `project/state.yaml`; discovered from the working directory
  when omitted.

Exit codes: `0` success, `1` inconsistent state, `2` usage error, `3` unsafe condition (e.g. a
detected secret leak).

## Example

```bash
repository-presenter preflight
repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python --facts-only
repository-presenter present --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python
repository-presenter status
```

`preflight` confirms the LLM gateway is reachable. `present --facts-only` produces a processability
and coverage record with no provider calls. Dropping `--facts-only` runs the full transaction and,
if every blocking check and the independent review pass, seals a candidate under
`candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/<revision>/`. Running `present` again against
the same sealed revision reproduces the identical bundle with zero new provider calls — the no-op
proof. `status` then reports the updated candidate count. This repository is the project's canary.

## Security and effects

- Analysis clones are pinned to one revision, read-only, and push-disabled; a hard allow-list
  gates which repositories can be reached at all (`data/registry.json`).
- Write credentials are separate from analysis credentials, short-lived, and target-scoped, and
  exist only in a separate effect job. A write credential's mere presence never implies
  authorization — a distinct, owner-controlled variable must also be set, checked independently by
  the code that would write.
- Initial publication is pull-request-only; this project never pushes directly to a target
  repository's default branch. No pull request has been opened against any product repository yet
  (`G6-W02`/`G6-W03`); each repository's first one needs its own fresh owner authorization,
  recorded under `ops/` and merged by a person before the run that consumes it.
- Candidate acceptance never implies publication authorization.
- Secrets are never logged, committed, cached, or persisted; every CLI command scans for
  configured-secret leakage before reporting success.

Full rules are in [`AGENTS.md`](AGENTS.md)'s "Security and Effects" section; the threat model is in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), and credential rotation in
[`docs/CREDENTIAL_ROTATION_RUNBOOK.md`](docs/CREDENTIAL_ROTATION_RUNBOOK.md).

## Project documentation

| Subject | Document |
|---|---|
| Product outcome and standing constraints | [`plans/idea.md`](plans/idea.md) |
| Agent conduct, safety, work loop | [`AGENTS.md`](AGENTS.md) |
| Build order, gates, acceptance | [`docs/EXECUTION_STATE_MACHINE.md`](docs/EXECUTION_STATE_MACHINE.md) |
| Production runtime behavior | [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) |
| Candidate README shape, assembly, agentic decisions, blocking checks | [`docs/README_CONTRACT.md`](docs/README_CONTRACT.md) |
| Where a file lives | [`docs/REPOSITORY_LAYOUT.md`](docs/REPOSITORY_LAYOUT.md) |
| Session supervision: supervisor, lane agents, monitors, liveness | [`docs/SUPERVISION.md`](docs/SUPERVISION.md) |
| Research record and design reasoning | [`docs/RESEARCH_AND_GUIDELINES.md`](docs/RESEARCH_AND_GUIDELINES.md) |
| Decisions and provenance (append-only) | [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) |
| Recurring defect classes | [`docs/DEFECT_INDEX.md`](docs/DEFECT_INDEX.md) |
| Production workstreams beyond sealing | [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md) |
| Threat model | [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) |
| Live implementation cursor | [`project/state.yaml`](project/state.yaml) |
| Legacy-code disposition | [`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) |
| Owner/reviewer tooling | [`tools/README.md`](tools/README.md) |

## License

MIT. See [`LICENSE`](LICENSE).
