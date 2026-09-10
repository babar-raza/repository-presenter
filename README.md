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
| Local CLI (`status`, `present`, `preflight`) | **Built** |
| Multi-ecosystem extraction (Python, .NET, Java, C++, Rust, Go, TypeScript) | **Partially built** — extractor plugins exist for all seven; sealed candidates so far cover fewer |
| Deterministic Markdown renderer; the LLM never writes the final document, only fact-ID-bound content units | **Built** |
| Safety: pinned, read-only, push-neutered git clones; secret-canary scan before any bundle is sealed | **Built** |
| Hosted, autonomous, scheduled portfolio monitoring | **Planned** (Gate G5) |
| Automatic pull-request proposals via a GitHub App, with independent effect authorization | **Planned** (Gate G6) |
| Production deployment and continuous unattended operation | **Planned** (Gate G7) |
| Upstream defect reporting (filing genuine product defects found during reconciliation) | **Planned** — marked not required for the initial pilot in `plans/idea.md` |
| Visual-asset / social-preview image preparation | **Planned** — same pilot carve-out |
| Non-README presentation surfaces (website, topics, community/security files, release links) | **Planned** — README health is the foundational surface only |

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

A sealed candidate itself follows a fixed shape — a 20-section semantic template with a default
320-visible-line budget and its own set of blocking checks — documented in full in
[`docs/README_CONTRACT.md`](docs/README_CONTRACT.md). Full runtime design (portfolio-wide
scheduling, proposal creation, effect authorization) is in
[`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md); most of it is still G5+ future scope, not what
runs today.

## Repository structure

```
src/repository_presenter/   cli.py (entry point), core/ (shared capabilities), components/readme/ (pipeline)
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
- Core dependencies: `httpx`, `jsonschema`, `markdown-it-py`, `openai`, `pydantic`, `tenacity`,
  `pyyaml`, plus pinned `tree-sitter` packages used by the multi-language source extractor.

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
| `GH_TOKEN` | optional | Repository-scoped, read-only; used only for `present`'s clone step |

`GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY` are required even for `present --facts-only`: the gateway
configuration loads before that flag's short-circuit.

## CLI reference

The package installs one console script, `repository-presenter` (equivalently, `python -m
repository_presenter`).

```
repository-presenter --version
repository-presenter status [--root PATH] [--stale]
repository-presenter preflight [--root PATH]
repository-presenter present --repo OWNER/NAME [--root PATH] [--facts-only] [--fresh]
```

- **`status`** — prints the version, current gate, active work item, and candidate progress read
  from sealed bundles on disk. `--stale` additionally reports any current candidate whose recorded
  dependencies are behind the running code's component/check versions; it is a pure read and makes
  no provider call.
- **`preflight`** — reaches the LLM gateway using the process environment, lists its live models,
  and records the catalog under `runs/preflight/catalog.json`.
- **`present --repo OWNER/NAME`** — runs the full transaction for one repository listed in the
  registry: snapshot, facts, investigation, reconciliation, planning, composition, validation,
  independent review, and seal. `--facts-only` stops after the facts stage with a processability
  and coverage record, making no provider call. `--fresh` skips seeding this run's call cache from
  the sealed bundle's own history, forcing every job to make a genuinely live call.
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
| Research record and design reasoning | [`docs/RESEARCH_AND_GUIDELINES.md`](docs/RESEARCH_AND_GUIDELINES.md) |
| Live implementation cursor | [`project/state.yaml`](project/state.yaml) |
| Legacy-code disposition | [`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) |

Read order for a new session is defined in `AGENTS.md`.

## License

MIT. See [`LICENSE`](LICENSE).
