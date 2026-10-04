# Repository Presenter

Repository Presenter is an autonomous, GitHub-native system that keeps the README files of
authorized product repositories accurate, credible, repository-specific, and current. It combines
deterministic evidence, validation, state, and safety controls with a configurable LLM for product
interpretation, editorial planning, composition, and independent review. README health is the
foundational component; other repository-presentation surfaces are planned to follow through the
same core.

It is the successor to the legacy `babar-raza/foss-readme-optimizer` repository. Reusable legacy
behavior migrates here only through the pull-based ledger in
[`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) — a file enters when a gate
actually needs it, never as a bulk port.

## Project status

Active development, not yet a stable release. Source install only — there is no PyPI package.
Gates `G0_FOUNDATION`, `G1_FIRST_VALID_CANDIDATE`, and `G2_STABILITY_UNDER_CHANGE` are accepted;
the project is currently working through `G3_PYTHON_COHORT` and `G4_MULTI_LANGUAGE_COHORTS`. It
does not yet open pull requests against target repositories — today it produces and seals local
README candidates only (see [Scope](#scope-built-vs-planned) below).

For the live gate, active work item, and exact candidate count, run `repository-presenter status`
yourself, or read [`project/state.yaml`](project/state.yaml) — the one live cursor for this
project. This file intentionally never restates those numbers: they change with nearly every
merged work item, and a number frozen into prose here would be wrong within days.

## What it does

The goal is a central repository-presentation agent, not a one-off README rewriter. Given an
authorized repository, it:

- reads the repository's own source, manifests, tests, examples, license, and releases as ground
  truth, and never treats an existing README or another agent's claim as trusted without
  verification;
- extracts and reconciles facts against that evidence, then plans and composes a candidate README
  from the accepted facts;
- validates the candidate against a fixed set of blocking checks and an independent, non-authoring
  review before it can be sealed;
- proves the result reproducible: an immediate rerun against an already-sealed revision must
  reproduce byte-identical output while making zero further calls to the LLM gateway (the
  project's "no-op proof").

## Scope: built vs. planned

| Capability | Status |
|---|---|
| Facts → investigation → reconciliation → planning → composition → validation → independent review → seal pipeline | **Built** (gates G0–G2 accepted) |
| Local CLI (`status`, `present`, `preflight`, `redetect-upstream-defects`, `file-upstream-defects`, `metadata`, `propose`) | **Built** |
| Multi-ecosystem extraction (Python, .NET, Java, C++, Rust, Go, TypeScript) | **Partially built** — extractor plugins exist for all seven; sealed candidates so far cover fewer |
| Deterministic Markdown renderer; the LLM never writes the final document, only fact-ID-bound content units | **Built** |
| Safety: pinned, read-only, push-neutered git clones; secret-canary scan before any bundle is sealed | **Built** |
| Upstream-defect detection and re-detection (`redetect-upstream-defects`); local, evidence-backed handoff records | **Built** — read-only re-checks; a status-only local write; a gated `close` of an issue this system filed, once its check proves the defect resolved |
| Upstream defect *reporting* (`file-upstream-defects`; filing genuine product defects as GitHub issues) | **Built** — gated: refuses without an owner-controlled authorization variable and a write-scoped token. Scheduled by `.github/workflows/issues-scheduled.yml`; its write job runs only once the owner sets the repository variable (see [Security](#security-and-effects)) |
| Production GitHub App credentials, installed across every registry organization | **Built** — a write-capable credential existing; it is not itself write authorization (see [Security](#security-and-effects)) |
| Repo description/topics/homepage: read GitHub's observed values, propose a candidate from verified facts, diff | **Built** — read-only; no write call without explicit dual authorization |
| Hosted, autonomous, scheduled portfolio monitoring | **Planned** (Gate G5) |
| Automatic pull-request proposals via a GitHub App, with independent effect authorization (`propose`) | **Built**, disposable-target live proof still open — gated: refuses without an owner-controlled authorization variable and a write-scoped token, both unset in this project's own environment; no disposable test repository is yet named to exercise it live (see [Security](#security-and-effects)) |
| Production deployment and continuous unattended operation | **Planned** (Gate G7) |
| Visual-asset / social-preview image preparation | **Planned** — same pilot carve-out |
| Repo description/topics/homepage: apply the proposal to GitHub; community/security file generation; release-link auditing | **Planned** |

For the exact current candidate count against the full target set, run `repository-presenter
status` — see [Project status](#project-status).

## How it works

Deterministic code and an LLM each own a distinct half of the work. The LLM interprets a
repository and proposes typed, fact-ID-bound content — it never writes the final Markdown, never
advances durable state, and never mutates a repository directly. Deterministic code owns commands,
links, badges, diagram topology, exact identifiers, validation, and every state transition; it
accepts or rejects what the LLM proposes.

Each repository moves through one linear transaction: snapshot the pinned revision, extract facts,
investigate and reconcile them against any existing README content, plan and compose a candidate,
validate it against a fixed set of blocking checks, pass it through an independent review, then
seal it into a content-addressed bundle. Sealing also proves the no-op guarantee described above.

A sealed candidate itself follows a fixed shape — a semantic template with a default visible-line
budget and its own set of blocking checks — documented in full in
[`docs/README_CONTRACT.md`](docs/README_CONTRACT.md). Full runtime design (portfolio-wide
scheduling, proposal creation, effect authorization) is in
[`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md); most of it is still G5+ future scope, not what
runs today.

## Repository structure

```
src/repository_presenter/   cli.py (entry point), core/ (shared capabilities), components/ (pipeline)
  components/readme/          the README transaction: evidence, investigation, reconciliation,
                               composition, validation, independent review, repair, bundle sealing
  components/metadata/        repo description/topics/homepage capture, proposal, gated apply
  components/issues/          upstream-defect ledger, handoff drafting, redetection, gated issue filing
  components/propose/         README-proposal PR effect: idempotent branch/commit/PR, gated write
prompts/                    one governed YAML manifest per LLM job
schemas/                    JSON Schemas for state, manifest, and bundle validation
data/                       registry.json — the admitted-repository allow-list
candidates/<owner>__<name>/<revision>/   sealed README bundles, with a CURRENT pointer
tests/                      mirrors src/ path-for-path, plus flat repo-wide invariant tests
docs/                       authority and research documents
plans/, project/, migration/   product authority, live cursor, legacy reuse ledger
tools/                      owner/reviewer tooling — not part of the shipped package
```

## Requirements

- Python 3.11 or later (CI tests 3.11, 3.12, and 3.13).
- Core dependencies: `httpx`, `jsonschema`, `markdown-it-py`, `openai`, `packaging`, `pydantic`,
  `tenacity`, `pyyaml`, plus pinned `tree-sitter` packages used by the multi-language source
  extractor.

## Installation

```bash
git clone https://github.com/babar-raza/repository-presenter.git
cd repository-presenter
python -m venv .venv
.venv\Scripts\pip install -e .[dev]      # Windows
# .venv/bin/pip install -e .[dev]        # macOS/Linux
```

Or install exactly what CI installs, from the hashed lock file:

```bash
pip install -r requirements-lock.txt
pip install --no-deps -e .
```

There is no published package yet — install from source only.

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
| `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` | optional | Owner-controlled go-ahead for the issue filing and closing writes (`file-upstream-defects --file`, `redetect-upstream-defects --close`); a token's mere presence never implies this. In CI it is set only from the repository variable of the same name, on the gated write job |
| `GH_PROPOSAL_WRITE_TOKEN` | optional | Write-scoped, distinct from `GH_TOKEN`/`GH_METADATA_WRITE_TOKEN`/`GH_ISSUES_WRITE_TOKEN`; only `propose --propose` reads it, and only after `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` also authorizes a write |
| `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` | optional | Owner-controlled go-ahead for `propose --propose`'s write; a token's mere presence never implies this |

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
  [--durable-state [--trigger-event-type TYPE] [--workflow-run-id ID] [--holder-id ID]
                    [--state-remote REMOTE]]
repository-presenter monitor [--root PATH] [--owner OWNER] [--out PATH]
repository-presenter redetect-upstream-defects [--root PATH] [--repo OWNER/NAME] [--apply] [--close]
repository-presenter file-upstream-defects [--root PATH] [--repo OWNER/NAME] [--file]
repository-presenter issue-targets [--root PATH]
repository-presenter metadata --repo OWNER/NAME [--root PATH] [--apply]
repository-presenter propose --repo OWNER/NAME [--root PATH] [--readme-file PATH --source-revision SHA] [--base-branch NAME] [--expires-in-minutes N] [--propose]
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
- **`monitor`** — observes each enabled registry repository's upstream default-branch head with the
  read-only `GH_TOKEN` and compares it with its `CURRENT` sealed bundle's revision, recording one
  status per repository (`CURRENT`, `DRIFTED`, `NO_BUNDLE`, `UNREACHABLE`) in a JSON evidence file
  under `runs/monitor/drift.json` (`--out` overrides the path; `--owner` limits the run to one
  owner's enabled entries). It makes no provider call and no write to any repository; it exits 1
  when any repository is `UNREACHABLE`, and the scheduled `monitor.yml` workflow runs it read-only.
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
  limits the pass to one repository. `--file` attempts the write, but only past two independent,
  explicit gates — the owner-controlled `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED=1`, and a
  write-scoped `GH_ISSUES_WRITE_TOKEN` (never `GH_TOKEN`). Before the write it searches the target
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
  request proposing a README candidate to the target repository (G6-W02). By default reads the
  repository's registry-admitted sealed `CURRENT` candidate; `--readme-file PATH
  --source-revision SHA` bypasses the registry and sealed bundle entirely, for proving the
  mechanism against a disposable test repository that is never registry-admitted and never a real
  `aspose-*-foss` product repository. Dry-run by default: assembles and prints the typed
  authorization payload (candidate hash, source revision, branch, PR intent, policy version,
  expiry — `--expires-in-minutes` sets how long it stays valid) and makes no GitHub call at all.
  `--propose` attempts the write, but only past two independent, explicit gates — the
  owner-controlled `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED=1`, and a write-scoped
  `GH_PROPOSAL_WRITE_TOKEN` (never `GH_TOKEN`, never `GH_METADATA_WRITE_TOKEN`/
  `GH_ISSUES_WRITE_TOKEN`) — plus a fresh recheck of the target's live current revision
  immediately before the write (a stale source blocks the effect) and an idempotent branch/PR
  mechanism (a second, unchanged invocation writes nothing and opens nothing new). Neither gate is
  set in this project's own environment, so `--propose` reports exactly why it wrote nothing
  rather than guessing. `--base-branch` overrides the target's default branch, read live from
  GitHub when omitted.
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
proof. `status` then reports the updated candidate count.

## Security and effects

- Analysis clones are pinned to one revision, read-only, and push-disabled; a hard allow-list
  gates which repositories can be reached at all (`data/registry.json`).
- Write credentials are separate from analysis credentials, short-lived, and target-scoped; a
  write credential's mere presence never implies authorization to use it — a distinct,
  owner-controlled variable must also be set, checked independently by the code that would write.
- Initial publication is pull-request-only; this project never pushes directly to a target
  repository's default branch, and does not open pull requests against any target repository yet
  (Gate G6).
- Secrets are never logged, committed, cached, or persisted; every CLI command scans for
  configured-secret leakage before reporting success.

Full rules are in [`AGENTS.md`](AGENTS.md)'s "Security and Effects" section.

## Development and testing

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

`tests/` mirrors `src/` path-for-path, plus a handful of flat, repository-wide invariant tests at
`tests/test_*.py`. `bash scripts/ci_check.sh` runs the same checks CI runs, followed by a smoke
test of the built entry point, resolving the repo-local `.venv` automatically on Windows or POSIX.

Run `git config core.hooksPath .githooks` once per clone so `scripts/ci_check.sh` runs
automatically before every push to this repository's own `origin`.

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
| Live implementation cursor | [`project/state.yaml`](project/state.yaml) |
| Legacy-code disposition | [`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) |

Read order for a new session is defined in `AGENTS.md`.

## License

MIT. See [`LICENSE`](LICENSE).
