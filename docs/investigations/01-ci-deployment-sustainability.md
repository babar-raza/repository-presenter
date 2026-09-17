# Investigation 01 — CI/Deployment Sustainability (`act` → Real GitHub Actions Runners)

Written 2026-09-17. Workstream 1 of `docs/PRODUCTION_ROADMAP.md`. Reports against `plans/idea.md`
(human product authority) and the current codebase; invents no new obligations. This is a research
report, not an implementation plan — no code changes accompany it.

Scope, per the roadmap's own framing: how do we verify the eventual production pipeline is
sustainable under GitHub Actions — first locally with `act` (the runner `plans/idea.md`'s
"Execution Environments and GitHub Access" section names explicitly), then on real GitHub Actions
runners. The relevant `plans/idea.md` text:

> Local testing will use a local GitHub Actions-compatible runner to reproduce the production
> workflow as closely as practical before changes are exercised on GitHub. Production workloads
> will run on actual GitHub Actions runners in the configured production workflows.
>
> GitHub authentication will be environment-specific: local testing will use the operator-provided
> `GH_TOKEN` environment variable; and production will use a dedicated GitHub App and its
> short-lived installation access tokens. ... Credentials must never be embedded in workflow
> definitions, source code, caches, state, logs, or evidence. Production must fail closed if
> GitHub App authentication is unavailable; it must not silently fall back to a personal access
> token or local-development credential.

## 1. Current state

### 1.1 Existing workflows — none of them are the production pipeline

`.github/workflows/` has exactly three files, all CI/repo-hygiene, not product execution:

- **`ci.yml`** — push-to-`main`/PR gate. Matrix over Python 3.11/3.12/3.13; installs from
  `requirements-lock.txt`, runs `ruff check`, `ruff format --check`, `mypy src`, `pytest`, and the
  official entry point (`repository-presenter --version` / `status`). Every step runs with
  `continue-on-error: true` and a final `Summary` step reads all five `steps.*.outcome` values and
  fails the job if any is not `success` — a deliberate design (comment cites
  `docs/CI_AND_STALENESS_ASSESSMENT.md` §2.3) so a fail-fast pipeline never again hides which gate
  actually broke. `permissions: contents: read` only — no write, no secrets beyond the ambient
  `GITHUB_TOKEN` it never uses.
- **`liveness.yml`** — a read-only "dead-man" monitor (`permissions: contents: read,
  pull-requests: read`) that runs every 30 minutes via cron plus on `workflow_run` completion of
  CI. It checks for stale open PRs, stranded branches, and main-branch inactivity during an active
  sprint. It repairs nothing by design ("DETECTS and fails loudly; it repairs nothing").
- **`mirror-gitlab.yml`** — pushes `main` and tags to a GitLab mirror using a `GITLAB_TOKEN`
  repository secret. Unrelated to the presenter pipeline; it exists purely to keep a second git
  remote current.

**None of these executes the repository-presentation pipeline itself** (clone a target repo,
extract facts, compose a README candidate, validate, propose). That workflow does not exist yet.
The project's own build plan already names where it is supposed to land: `docs/
EXECUTION_STATE_MACHINE.md`'s **G5 — Rerun Durability and Hosted Operation** gate specifies two
workflows by name that have not been written:

> `monitor.yml` (schedule, manual, workflow-call, repository-dispatch) and `present.yml` (isolated
> per-repository job); proven locally under `act` with `GH_TOKEN`, then hosted with a read-only
> App token; ambient tokens ignored, fail closed.

The current build gate recorded in `project/state.yaml` (`current_gate.id`) is
`G3_PYTHON_COHORT`/`G4_MULTI_LANGUAGE_COHORTS` work (branch names throughout this session are all
`G4_MULTI_LANGUAGE_COHORTS/...`), i.e. the project is still two gates before G5. **This workstream
is investigation-only for exactly that reason: G5's own preconditions (G4's registry freeze, the
durable runtime backend, the candidate/no-op machinery) are not built yet**, so no production
workflow can be meaningfully authored today — only researched.

### 1.2 `act` is not installed, referenced, or used anywhere in this repo

Grepped the full tree (`*.md`, `*.yml`, `*.yaml`, `*.py`) for `nektos`, `catthehacker`, `act -j`,
`.actrc` — zero matches outside this new report and the planning documents that merely name the
tool (`plans/idea.md`, `docs/EXECUTION_STATE_MACHINE.md` G5, `migration/reuse-manifest.yaml`,
`docs/RESEARCH_AND_GUIDELINES.md` §16.6's "local `act` proof" phrase). `act` itself is not
installed on this machine (`which act` — not found on `PATH`).

**What today's local verification actually does instead**: `scripts/ci_check.sh` is a hand-written
bash script that re-implements `ci.yml`'s five steps directly (lint, format, typecheck, pytest,
entrypoint) by calling the same tools the workflow calls, in the same order, with the same
independent/non-short-circuiting semantics. Its own header comment is explicit about what this is
and is not:

> Each check runs independently (never short-circuits on an earlier failure) ... NOT
> auto-generated from `.github/workflows/ci.yml`: the two must be kept in sync by hand when either
> changes.

This script exists precisely because of a prior incident: `docs/CI_AND_STALENESS_ASSESSMENT.md`
(CS-06) records that during the 2026-09-09 healing pass only `pytest` was run out of habit before
pushes, letting lint/format/mypy drift silently for an entire pass. `scripts/ci_check.sh` is the
project's real, working answer to "did I break CI" — but it is a **parallel hand-maintained
implementation of the workflow, not the workflow itself run locally**. It cannot drift-detect a
change to `ci.yml`'s own YAML (a new step, a changed matrix, a permissions change) the way running
the actual workflow file locally would; that is exactly the gap `act` is designed to close, and
exactly why `plans/idea.md` names a "GitHub Actions-compatible runner" rather than "an equivalent
local script."

### 1.3 What `act` needs, and what this environment already has

`act` (github.com/nektos/act) runs `.github/workflows/*.yml` files directly by executing each job
inside a Docker container that stands in for a GitHub-hosted runner image, so the same YAML that
GitHub will interpret is the input — no separate script to keep in sync.

Checked on this machine:

- **Docker**: installed and running — Docker Desktop 28.4.0, daemon reachable (`docker info`
  succeeded), `OSType: linux` (WSL2 backend). This is the one hard prerequisite `act` has, and it
  is already satisfied — `act` needs a Linux container runtime even on Windows, and this machine's
  Docker Desktop is already configured for Linux containers rather than Windows containers, which
  is the configuration that actually matters here.
- **`act` binary itself**: not installed. It ships as a single Go binary (`choco install act-cli`,
  `winget install nektos.act`, or a direct release download all work on Windows) — a small,
  low-risk install, but it is a new tool this environment does not have today.
- **Runner image choice**: `act` does not use GitHub's actual multi-gigabyte hosted-runner images
  by default; it maps `runs-on: ubuntu-latest` to a community substitute image (commonly
  `catthehacker/ubuntu:act-latest`, several GB) via `-P ubuntu-latest=<image>` or a repository
  `.actrc` file. No `.actrc` exists in this repo. `ci.yml`'s steps (pip install, ruff, mypy,
  pytest, the console-script entry point) are all plain Python/pip and should run fine under a
  standard `act` image, but this has not been verified — nothing has ever invoked `act` against
  this repo's workflows.
- **Secrets for local runs**: `plans/idea.md`'s rule is that local testing authenticates with the
  operator's own `GH_TOKEN` environment variable. `act` supports this directly via `--secret
  GH_TOKEN="$GH_TOKEN"` or a local, gitignored secrets file passed with `--secret-file`. None of
  the three existing workflows currently consume a `GH_TOKEN` secret (`ci.yml` and `liveness.yml`
  use only the ambient `github.token`; `mirror-gitlab.yml` uses `GITLAB_TOKEN`), so there is
  nothing to exercise this path against yet — it becomes relevant only once `present.yml` exists
  and needs to clone/read target repositories.
- **Triggers `act` cannot simulate faithfully**: `liveness.yml`'s `schedule:` cron and
  `workflow_run` triggers, and any future `monitor.yml` schedule/`repository-dispatch` trigger, are
  not naturally fired by `act` — `act` runs a named event with `act <event> -e <event.json>`, so
  scheduled/dispatch behavior has to be hand-simulated with a crafted event payload rather than
  proven end-to-end locally. This is a real, structural limit of "local GitHub-Actions-compatible
  runner," not a configuration gap to fix — it bounds what local `act` proof can ever claim for a
  scheduled production workflow.

### 1.4 Credential handling today

- **`.env.example`** documents `GH_TOKEN` as a "Repository-scoped, read-only GitHub token for
  analysis. Write credentials never live here," and states the project reads credentials from the
  process environment, not a `.env` file (`docs/RESEARCH_AND_GUIDELINES.md` §18.4).
- **`src/repository_presenter/core/secrets.py`** already has a general secret-leak-prevention
  mechanism: `SECRET_VARIABLES = frozenset({"GPT_OSS_API_KEY", "GH_TOKEN"})` plus a
  suffix-based heuristic (`_API_KEY`, `_TOKEN`, `_SECRET`, `_PASSWORD`), a `redact()` helper that
  masks secret-shaped strings (`ghp_...`, `ghu_...`, `sk-...`, `Bearer ...`, etc.) before text is
  persisted, and `find_secret_leaks()` which scans an entire candidate bundle directory for any
  configured secret's literal value. This is real, working, tested infrastructure
  (`tests/core/test_secrets.py`) — the redaction/leak-detection half of the credential story is
  already in place and ecosystem-agnostic (it would need a GitHub-App-token variable name added to
  `SECRET_VARIABLES`, or already matches via the `_TOKEN` suffix if the new variable is named
  accordingly).
- **`src/repository_presenter/cli.py:416`** is the only current production use of `GH_TOKEN`: it
  is read with `os.environ.get("GH_TOKEN") or None` and passed into
  `pinned_read_only_clone(...)` — a read-only, push-neutered clone
  (`src/repository_presenter/core/git_safety/clone.py`) used for the local development/analysis
  transaction. There is no GitHub App code path anywhere in current `src/` to compare it against —
  this is the only auth path that exists today, and it is exactly the "local testing" side of
  `plans/idea.md`'s rule, not the production side.
- **No `GITHUB_PAT`/`README_AGENT_PRODUCTION_AUTH` fail-closed switch exists in current `src/`.**
  It existed in the legacy `foss-readme-optimizer` codebase's `env.py` and is recorded, not yet
  ported, in `migration/reuse-manifest.yaml`:

  > `CPL-07 — chain: env.py resolves GH_TOKEN then GITHUB_PAT unless
  > README_AGENT_PRODUCTION_AUTH=github_app ... The fail-closed production mode required by
  > plans/idea.md exists; port github_app as the only production mode and keep the PAT path for
  > local act runs only.`

  and in the reuse manifest's per-file disposition for `src/readme_agent/{env,paths}.py` →
  `EXTRACT_AND_REFACTOR` to `src/repository_presenter/core/config/`, retaining "`github_app` as
  the only production credential mode; fail closed without the App token." **This module has not
  been ported.** `src/repository_presenter/core/config.py` today only handles the LLM gateway
  (`GPT_OSS_ENDPOINT`/`GPT_OSS_API_KEY`) — there is no GitHub-side equivalent yet.

### 1.5 GitHub App — prior art and current status

- **`project/state.yaml` `owner_items`** already records the two concrete owner-only blockers for
  this exact workstream, both `status: OPEN`:
  - **`OWNER-04`**: "Create the GitHub App for production tokens and install it on the authorized
    organizations; provide `GH_APP_CLIENT_ID` and `GH_APP_PRIVATE_KEY` as repository secrets, plus
    `GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY`." Resume predicate: "A hosted workflow run mints a
    read-only installation token for the canary repository." `consumed_by: [G5_RERUN_DURABILITY_
    AND_HOSTED_OPERATION, G6_PROPOSAL_EFFECT_PROOF]`.
  - **`OWNER-01`**: branch protection on `main` requiring the three CI matrix jobs as required
    status checks, plus auto-merge — `consumed_by: [G5_RERUN_DURABILITY_AND_HOSTED_OPERATION]`.
    Until resolved, the note says the agent pushes `main` directly after the local CI-equivalent
    passes, and hosted CI still runs on every push.
  - `docs/EXECUTION_STATE_MACHINE.md` independently confirms these are deliberately *not* gate
    work: "Owner-only predicates never live in a gate. Branch protection, secrets, App
    installation, and product decisions are `owner_items`."
- **No GitHub App SDK/JWT dependency exists.** `pyproject.toml`'s `dependencies` list
  (`httpx`, `jsonschema`, `markdown-it-py`, `openai`, `packaging`, `pydantic`, `tenacity`,
  `pyyaml`, `tree-sitter*`) and `requirements-lock.txt` contain no `PyJWT`, `cryptography`,
  `PyGithub`, or `gidgethub` — nothing that can currently sign a JWT or exchange it for an
  installation token. `httpx` is present and sufficient for the plain REST calls a GitHub App
  integration needs; a JWT-signing library is the one clearly missing piece.
- **What a GitHub App for this purpose actually requires** (general knowledge, confirmed against
  no local prior art since none exists beyond the CPL-07 note above):
  1. **App registration** (owner action, one-time, in the GitHub organization/account UI or via
     the App manifest flow): a name, homepage URL, and a **permissions** grant. For this project's
     scope that means, at minimum, repository-level **Contents: Read & write** (read the README
     and source to build facts; later, write a branch/PR for Gate C's proposal path — read-only
     is sufficient until then), **Pull requests: Read & write** (Gate C only), **Metadata: Read**
     (mandatory baseline), and **Issues: Write** (Workstream 3, upstream defect filing — separate
     from this workstream but the same App likely carries both scopes to avoid a second
     credential axis). No organization-wide or account-wide permissions are implied by anything in
     `plans/idea.md` — the opposite: "authorized organizations" and a hard allow-list
     (`data/products.json`) are named repeatedly as the scope boundary.
  2. **Installation** (owner action): the App is installed on the authorized GitHub
     organization(s)/account(s), scoped to "selected repositories" (ideally the exact allow-listed
     set, or all-repos with the runtime allow-list as the enforcing boundary — `plans/idea.md`
     does not decide between these, see open question below).
  3. **Credential material**: the App's numeric **App ID**, and a **private key** (`.pem`) GitHub
     generates once at App-creation time (regeneratable, not recoverable if lost). `state.yaml`'s
     `OWNER-04` names `GH_APP_CLIENT_ID` and `GH_APP_PRIVATE_KEY` as the two repository secrets to
     provide — note "client ID" is usually distinct from "App ID" in GitHub's own vocabulary (the
     client ID is OAuth-flow-specific; App-to-installation-token minting normally keys off the
     numeric App ID), so this naming should be revisited once someone actually walks the
     registration screen — flagged as an open question below rather than corrected speculatively.
  4. **Token exchange at runtime**, no third-party service required: (a) build a signed JWT using
     the App ID as issuer and the private key (RS256), valid a few minutes; (b) call
     `POST /app/installations/{installation_id}/access_tokens` with that JWT as bearer auth to
     mint a short-lived (1-hour, non-renewable) **installation access token**, optionally scoped
     down further to specific repositories/permissions in the request body; (c) use that token as
     the `Authorization: Bearer` (or `token`) value for the actual git/API operations; (d) let it
     expire — no revocation call needed for the normal case. This is the "short-lived installation
     access tokens" `plans/idea.md` names, and it is what the legacy `env.py`'s `github_app` mode
     already implemented once (per CPL-07) — that logic is a real, if unported, prior
     implementation to pull from rather than design fresh.
  5. **Fail-closed enforcement**: the legacy behavior recorded in CPL-07 — resolve `GH_TOKEN` then
     `GITHUB_PAT` *unless* a production-mode flag (`README_AGENT_PRODUCTION_AUTH=github_app` in
     the legacy naming) is set, in which case ambient tokens are ignored entirely and a missing App
     token is a hard failure, not a fallback — is exactly the shape `plans/idea.md` mandates. It
     needs porting/redesigning behind this project's own `core/config.py`-style boundary, not
     reinventing.
  6. **A real, on-record safety argument for urgency, not hypothetical**: `docs/
     PRODUCTION_ROADMAP.md`'s own "known constraints" for this workstream cites a live incident
     this sprint — "a lane agent's diagnostic `echo` accidentally printed a literal `GH_TOKEN`
     value into its own transcript ... flagged to the owner as a rotation candidate." This
     investigation did not locate the specific transcript/decision-log entry (it is not in the
     root `docs/DECISION_LOG.md` under a `GH_TOKEN` grep — it may live in a lane-local log this
     search did not cover), but the roadmap document itself is the authoritative record of it and
     is reason enough to treat "credentials never in logs" as a currently-imperfect invariant, not
     an already-solved one.

## 2. What the production workflow would need to do end-to-end (sketch, not a plan)

Grounded in `docs/EXECUTION_STATE_MACHINE.md` G5's own naming (`monitor.yml`, `present.yml`) and
`docs/STATE_MACHINE.md` §13 (durable per-repository state record) — not invented from scratch:

1. **Trigger** (`monitor.yml`): schedule (cron), `workflow_dispatch` (manual), `workflow_call`
   (composability), and `repository_dispatch` (external trigger). This job's role is to decide
   *which* repositories are due (changed-or-due matrix against `data/products.json` and the
   registry revision), not to do any presentation work itself.
2. **Fan-out**: for each due repository, dispatch an isolated `present.yml` job — "repository
   workers stay serial per `plans/idea.md`" is already the stated concurrency model (§27.1 of
   `docs/RESEARCH_AND_GUIDELINES.md`, bounded concurrency of four *within* one repository's own
   composition calls, not across repositories).
3. **Auth** (`present.yml`, start of job): mint a repository-scoped GitHub App installation token
   inside the job (never a token minted once and passed between jobs/artifacts) — `docs/
   RESEARCH_AND_GUIDELINES.md` §6.2 already states this exact rule for the effect path ("mint a
   fresh repository-scoped GitHub App token in the effect job"); the read path for facts-gathering
   should follow the same discipline even though it does not write.
4. **Checkout / clone**: the target repository (not this control repository) is pulled through the
   existing `pinned_read_only_clone` machinery (`core/git_safety/clone.py`) — already push-neutered
   and hook-verified — using the freshly minted token in place of today's `GH_TOKEN` local
   variable. The control repository itself (this repo) is checked out normally via
   `actions/checkout` for its own code/state.
5. **Run the pipeline**: the official entry point (`repository-presenter`, per `AGENTS.md`'s
   established rule that this is the only real entry point) executes the actual
   extract → reconcile → compose → validate → review transaction against the cloned snapshot,
   producing a candidate bundle under the transaction's evidence path.
6. **Persist durable state**: write the repository's CAS record (`docs/STATE_MACHINE.md` §13.1 —
   revision, dependency hashes, accepted artifact, proposal pointer, lease) to the control
   repository's dedicated state namespace, explicitly *not* to GitHub Actions cache — "GitHub
   Actions cache accelerates execution but is never authoritative durable state" (§13.2 and
   `docs/RESEARCH_AND_GUIDELINES.md` line 484). This durable backend (`state/git_backend.py`,
   `cas.py`, `trigger_v2.py`, `recovery.py`, `health.py`, `freshness_contract.py` in the legacy
   naming) does not exist in current `src/` yet — confirmed by direct search; it is itself G5 work
   item 2, not something this workflow can call today.
7. **Effects, gated separately**: any repository-affecting write (a proposal/PR under Gate C, later
   an issue filing under Workstream 3) is a **separately authorized** action per
   `docs/RESEARCH_AND_GUIDELINES.md` §6.3's three-workflow split (facts → candidate →
   `propose.yml`), not something `present.yml` does implicitly as a side effect of running.
8. **Evidence and redaction**: every persisted log/evidence artifact passes through
   `core/secrets.py`'s `redact()`/`find_secret_leaks()` before it is written or promoted, so a
   token can't leak into evidence even if a step accidentally prints it — this machinery exists
   today and should be wired into whatever logging the new workflow produces, not rebuilt.
9. **Failure semantics**: fail closed, not silently degrade — no ambient `GH_TOKEN`/PAT fallback in
   this job under any condition (`README_AGENT_PRODUCTION_AUTH`-style guard, ported from CPL-07),
   and no partial/undocumented write on an auth failure.

This is a sketch of shape, not a spec: exact YAML, job boundaries, and matrix strategy are
G5-authoring work and depend on the durable-state backend existing first.

## 3. Gaps — concrete, not aspirational

### 3.1 Local `act` verification loop

- `act` binary: **not installed**. Low-effort to add (single binary), but zero current usage to
  build on.
- Docker: **already satisfied** — Docker Desktop running, Linux containers (WSL2), verified via
  `docker info`. This is the one prerequisite that is *not* a gap.
- No `.actrc` / runner-image pin exists — first-run image choice and pull (multi-GB) has never
  been exercised against this repo.
- `ci.yml` and `liveness.yml` have never been run under `act`, so it is unverified whether they
  work unmodified (e.g., `actions/checkout@v5`/`@v4`, `actions/setup-python@v6` compatibility with
  whatever image gets pinned; `liveness.yml`'s `gh pr list`/`git for-each-ref` steps assume
  `gh` CLI and network access to `origin`, which a local container may not have preconfigured).
- No production workflow (`monitor.yml`/`present.yml`) exists to `act`-test in the first place —
  this is the larger gap and it is upstream of everything else in this section: local `act` proof
  needs something to prove.
- `scripts/ci_check.sh` is a working substitute for `ci.yml` specifically, but is explicitly *not*
  drift-proof against the workflow YAML itself, which is the exact property `act` exists to
  provide. It should not be discarded (it is faster, needs no Docker, and is the documented
  pre-push habit per `AGENTS.md`) but it does not answer "does the real workflow file still work,"
  which matters more once a scheduled/multi-job production workflow exists.
- Secrets-for-local-runs path (`act --secret GH_TOKEN=...`) has never been exercised because no
  current workflow consumes a secret named `GH_TOKEN`.

### 3.2 Real-runner production verification

- No production workflow file exists to run on real runners at all — G5's `monitor.yml`/
  `present.yml` are unwritten.
- The durable state backend (`docs/STATE_MACHINE.md` §13) the production workflow needs to persist
  results to does not exist in current `src/` — confirmed absent (`git_backend.py`, `cas.py`,
  `trigger_v2.py`, `recovery.py`, `health.py`, `freshness_contract.py` all return zero matches).
  Without it, a hosted run has nowhere durable to record its outcome (Actions cache is explicitly
  disallowed for this).
- `OWNER-01` (branch protection + required status checks + auto-merge) is `OPEN`. Until resolved,
  the project pushes directly to `main` after local checks — a real-runner production workflow
  that eventually needs to open/merge its own PRs (Gate C) has no protected-branch/review gate to
  land against yet.
- `OWNER-04` (GitHub App creation + installation + secrets) is `OPEN` — this is the hard blocker
  for any real-runner authentication test; "a hosted workflow run mints a read-only installation
  token for the canary repository" is its own resume predicate, i.e. this exact verification *is*
  what closes the owner item, not something that can be proven before the App exists.
- No monitoring of scheduled-trigger reliability exists yet for a *production* workflow, though
  `liveness.yml` already demonstrates the project is aware cron can misbehave under load (its own
  header records a measured 3h54m scheduled-trigger silence during high Actions load, which is why
  it chains off `workflow_run` as a backstop) — that lesson should carry over to `monitor.yml`'s
  own trigger design rather than being rediscovered.

### 3.3 GitHub App setup specifically

- No App has been created (owner action, `OWNER-04`, `OPEN`).
- No JWT-signing dependency (`PyJWT` + `cryptography`, or equivalent) is in `pyproject.toml`/
  `requirements-lock.txt`.
- No `core/config`-equivalent module exists for GitHub-side auth (only the LLM gateway side does,
  in `src/repository_presenter/core/config.py`); the fail-closed `github_app`-only production mode
  the legacy `env.py` already implemented (CPL-07) has not been ported into this codebase's typed
  boundary.
- Naming ambiguity flagged, not resolved: `state.yaml` names `GH_APP_CLIENT_ID` +
  `GH_APP_PRIVATE_KEY` as the two secrets; GitHub's own installation-token minting flow keys off
  the numeric **App ID** (not the OAuth client ID) plus the private key — this should be confirmed
  against whichever App-creation flow the owner actually uses, not assumed.
- `secrets.py`'s `SECRET_VARIABLES`/`SECRET_SUFFIXES` will need the eventual App-token variable
  name added (or already matches via the `_TOKEN`/`_KEY` suffix rule, depending on final naming) —
  a one-line addition once the naming is settled, not a design gap.

## 4. Concrete next steps (research/decision items, not implementation)

1. **Sequencing decision for the owner/supervisor**: confirm this workstream stays
   investigation-only until G5's own preconditions land (durable state backend, G4 registry
   freeze) — building `monitor.yml`/`present.yml` before the state backend exists would have
   nowhere durable to write results, per §3.2 above.
2. Install `act` and run it against the three *existing* workflows first (`ci.yml`,
   `liveness.yml`) as a cheap, immediately gettable proof point — this validates the Docker/image
   pipeline and surfaces any incompatibility (checkout/setup-python action versions, `gh` CLI
   availability inside the chosen image) well before a production workflow exists to test.
3. When `monitor.yml`/`present.yml` are authored (G5), `act`-test them against a single canary
   repository before any hosted run, per `plans/idea.md`'s own ordering.
4. Port the legacy `github_app`-only fail-closed credential mode (CPL-07) into
   `core/config`-equivalent code as part of that same G5 work, rather than redesigning it — the
   behavior `plans/idea.md` requires already exists once, in the legacy `env.py`.
5. Add a JWT-signing dependency (`PyJWT` + `cryptography`, both widely used, battle-tested per
   `plans/idea.md`'s own "prefer battle-tested" principle) when that porting work starts.
6. Locate the specific transcript/decision-log entry for the `GH_TOKEN`-printed-in-transcript
   incident the roadmap references (not found in `docs/DECISION_LOG.md` by direct search in this
   investigation — likely in a lane-local log) so the rotation status and remediation are on
   record before production credentials exist to leak.

## 5. Open questions for the owner

1. **App installation scope**: install the GitHub App on "all repositories" in the authorized
   organization(s) (simpler, relies entirely on the runtime allow-list in `data/products.json` as
   the enforcing boundary) or "selected repositories" pinned to the exact allow-list (narrower
   blast radius, but needs updating on every intake change)? `plans/idea.md` does not decide this.
2. **Permission scope for the single App**: one GitHub App carrying both the README-presentation
   permissions (Contents, Pull requests, Metadata) and the future issue-filing permission
   (Workstream 3, Issues: Write), or two separate Apps/credentials so a defect in one capability
   can't touch the other's permissions? The roadmap treats them as separate workstreams; nothing
   says whether they share a credential.
3. **`GH_APP_CLIENT_ID` vs App ID naming** (§3.3): which does the owner actually intend to provide
   as a repository secret — please confirm against the real App-creation screen before this is
   wired into code, since GitHub's own token-minting flow needs the numeric App ID specifically.
4. **`act` in CI itself**: should there be a CI job that runs `act` against the workflows on every
   push (a meta-check that the workflows stay `act`-runnable), or is `act` purely a manual
   pre-push developer step? `plans/idea.md` names it for "local testing," not for CI-checking CI.
5. **Branch protection (`OWNER-01`) timing**: does it need to land before or can it land
   independently of the GitHub App work? They are both G5-consumed owner items but nothing ties
   their sequencing together explicitly.

## Reverse by

`git revert` — this is a pure documentation addition (one new file under `docs/investigations/`),
no code or check coupling, no schema change.
