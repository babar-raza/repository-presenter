# Operations Runbook

Status: operational runbook, `TC-REF-10` (G7-W06; `plans/reseal-and-refresh/PLAN.md` section 11).
Owns: what runs when, what each hosted workflow needs (variables, secrets, permissions), how to stop
it, how to roll it back, and how every workflow was rehearsed locally before anything is hosted.
Does not own authorization policy (`AGENTS.md` "Security and Effects"), the write gates themselves
(`components/propose/effect.py`, `components/candidates_publish/effect.py`,
`components/issues/file.py`), per-secret rotation (`docs/CREDENTIAL_ROTATION_RUNBOOK.md`), or the
wave procedure (`docs/PROPOSAL_WAVE_RUNBOOK.md`); it points at them.

The inventory in section 3 is **generated from `.github/workflows/*.yml`** by
`tools/workflow_rehearsal/inventory.py`; a test (`tests/test_workflow_rehearsal.py`) fails when the
committed block differs from the YAML, so this document cannot drift from the workflows. Everything
else in this file is prose and is checked only by review.

## 1. The system in one paragraph

`monitor.yml` observes every enabled registry repository's upstream head against its sealed bundle
(read-only, no provider call) and uploads drift evidence. `sealing-scheduled.yml` turns that evidence
into at most three seals per run by calling `present.yml` (the one reusable pipeline, which uses the
LLM gateway), then optionally publishes the sealed candidates into this repository
(`candidates-publish.yml`) and proposes README pull requests to registry repositories in mode `full`
(`propose.yml`). `issues-scheduled.yml` re-verifies harvested upstream defects and files approved
issues. `liveness.yml` is the out-of-band dead-man for the supervision itself. `ci.yml` is the
required check on this repository. `audit-app-installations.yml` and `verify-app-installation.yml`
are manual GitHub App checks. `mirror-gitlab.yml` mirrors `main` to GitLab.

Nothing is written to an upstream repository unless every gate holds: registry mode `full`, an
authorization record reviewed and merged before the trigger commit, the owner variable set to
exactly `1`, a live-revision recheck, and the job's own scoped write token (section 5).

## 2. Schedules

All times are UTC; GitHub may delay a scheduled run under load.

| Workflow | Cron | Meaning | Writes |
|---|---|---|---|
| `monitor.yml` | `17 */6 * * *` | drift observation, every 6 hours | none (artifacts only) |
| `sealing-scheduled.yml` | `37 5 * * *` | daily plan, then seal (max 3 repositories), publish candidates, propose | control repo candidates PR and upstream PRs, each behind its own variable |
| `issues-scheduled.yml` | `41 3 * * *` | daily upstream-defect re-verification and, when authorized, filing | upstream issues, behind its variable and per-handoff approval records |
| `liveness.yml` | `13,43 * * * *` (also after every `CI` run) | dead-man check of the supervision | none |

Event-driven: `ci.yml` on pull requests and pushes to `main`; `mirror-gitlab.yml` on pushes to `main`
and tags; `present.yml`, `candidates-publish.yml`, `propose.yml` by `workflow_call` from the sealing
workflow or by `workflow_dispatch`; `audit-app-installations.yml` and `verify-app-installation.yml`
by `workflow_dispatch` only.

Order within a day: `issues-scheduled` 03:41, `sealing-scheduled` 05:37 (it consumes the latest
successful `monitor.yml` run's evidence and refuses evidence older than 12 hours; monitor runs at
00:17, 06:17, ...). **Alerts:** there is no pager. A red run is visible in the Actions tab;
`liveness.yml` goes red only when the observer is blind or `main` is quiet during a declared sprint;
stale pull requests are `::notice::` annotations. Watch the repository's Actions page and the
GitHub notification email for failed scheduled runs of the repository owner.

## 3. Variables, secrets, permissions and job graph, per workflow

<!-- BEGIN GENERATED: workflow-inventory (python tools/workflow_rehearsal/inventory.py --write) -->

#### Summary

| Workflow | File | Triggers | Workflow permissions | Concurrency |
|---|---|---|---|---|
| Audit GitHub App Installations Across Registry Orgs | `audit-app-installations.yml` | workflow_dispatch | contents: read | - |
| Candidates Publish | `candidates-publish.yml` | workflow_call inputs: candidate_artifact (string, required); do_publish (boolean, default False); repo (string, required)<br>workflow_dispatch inputs: candidate_artifact (string, required); do_publish (boolean, default False); repo (string, required) | contents: read | cancel-in-progress: False, group: candidates-publish-${{ inputs.repo }} |
| CI | `ci.yml` | pull_request<br>push (branches: ['main']) | contents: read | cancel-in-progress: True, group: ci-${{ github.ref }} |
| Upstream issues (scheduled) | `issues-scheduled.yml` | schedule `41 3 * * *` (UTC)<br>workflow_dispatch | contents: read | cancel-in-progress: False, group: upstream-issues |
| Liveness | `liveness.yml` | schedule `13,43 * * * *` (UTC)<br>workflow_dispatch<br>workflow_run (types: ['completed'], workflows: ['CI']) | contents: read, pull-requests: read | - |
| Mirror to GitLab | `mirror-gitlab.yml` | push (branches: ['main'], tags: ['*'])<br>workflow_dispatch | contents: read | cancel-in-progress: False, group: mirror-gitlab |
| Monitor | `monitor.yml` | schedule `17 */6 * * *` (UTC)<br>workflow_dispatch | contents: read | cancel-in-progress: True, group: monitor |
| Present | `present.yml` | repository_dispatch types: present<br>workflow_call inputs: repository (string, required)<br>workflow_dispatch inputs: repository (string, required) | contents: write | cancel-in-progress: False, group: present-${{ inputs.repository // github.event.client_payload.repository // 'unknown' }} |
| Propose | `propose.yml` | workflow_call inputs: authorization_record (string, optional); base_branch (string, optional); candidate_artifact (string, optional); do_propose (boolean, default False); repo (string, required)<br>workflow_dispatch inputs: authorization_record (string, optional); base_branch (string, optional); do_propose (boolean, default False); repo (string, required) | contents: read | cancel-in-progress: False, group: propose-${{ inputs.repo }} |
| Sealing (scheduled) | `sealing-scheduled.yml` | schedule `37 5 * * *` (UTC)<br>workflow_dispatch | contents: read | - |
| Verify GitHub App Installation | `verify-app-installation.yml` | workflow_dispatch | contents: read | - |

#### Variables, secrets and environment switches

| File | Repository variables (`vars.*`) | Secrets (`secrets.*`) | Switch names in scripts |
|---|---|---|---|
| `audit-app-installations.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY` | - |
| `candidates-publish.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY` | `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` |
| `ci.yml` | - | - | - |
| `issues-scheduled.yml` | `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` | `GH_APP_ID`, `GH_APP_PRIVATE_KEY` | `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` |
| `liveness.yml` | - | - | - |
| `mirror-gitlab.yml` | - | `GITLAB_TOKEN` | - |
| `monitor.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY`, `GPT_OSS_API_KEY`, `GPT_OSS_ENDPOINT` | - |
| `present.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY`, `GITHUB_TOKEN`, `GPT_OSS_API_KEY`, `GPT_OSS_ENDPOINT` | `REPOSITORY_PRESENTER_STATE_TOKEN` |
| `propose.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY` | `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` |
| `sealing-scheduled.yml` | `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_SEALING_PAUSED` | - + `secrets: inherit` | `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_SEALING_PAUSED` |
| `verify-app-installation.yml` | - | `GH_APP_ID`, `GH_APP_PRIVATE_KEY` | - |

#### `audit-app-installations.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `discover-orgs` | - | ubuntu-latest | contents: read (workflow) | - | - | - | - | - |
| `check-installation` | `discover-orgs` | ubuntu-latest | contents: read (workflow) | permission-metadata=read | - | - | yes | - |

#### `candidates-publish.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `plan` | - | ubuntu-latest | contents: read | - | - | - | - | - |
| `write` | `plan` | ubuntu-latest | contents: read | permission-contents=write+permission-metadata=read+permission-pull-requests=write | - | - | - | `${{ inputs.do_publish && needs.plan.result == 'success' && needs.plan.outputs.ready == 'true' }}` |

Artifacts: `down:${{ needs.plan.outputs.candidate_artifact }}`, `down:${{ steps.validate.outputs.candidate_artifact }}`

#### `ci.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `checks` | - | ubuntu-latest | contents: read (workflow) | - | - | - | yes | - |

Artifacts: `up:sbom-and-vulnerability-audit-py${{ matrix.python-version }}`

#### `issues-scheduled.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `targets` | - | ubuntu-latest | contents: read (workflow) | - | - | - | - | - |
| `analyse` | `targets` | ubuntu-latest | contents: read (workflow) | permission-contents=read+permission-issues=read+permission-metadata=read | - | - | yes | `${{ needs.targets.outputs.matrix != '[]' }}` |
| `file-and-close` | `targets` | ubuntu-latest | contents: read (workflow) | permission-contents=read+permission-issues=read+permission-metadata=read; permission-issues=write+permission-metadata=read | - | - | yes | `${{ vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED == '1' && needs.targets.outputs.matrix != '[]' }}` |

Artifacts: `up:issue-report-${{ matrix.target.owner }}__${{ matrix.target.name }}`

#### `liveness.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `liveness` | - | ubuntu-latest | contents: read, pull-requests: read (workflow) | - | - | - | - | - |

#### `mirror-gitlab.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `mirror` | - | ubuntu-latest | contents: read (workflow) | - | - | - | - | - |

#### `monitor.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `health-check` | - | ubuntu-latest | contents: read (workflow) | - | - | - | - | - |
| `drift-plan` | - | ubuntu-latest | contents: read (workflow) | - | - | - | - | - |
| `drift` | `drift-plan` | ubuntu-latest | contents: read (workflow) | permission-contents=read | - | - | yes | - |
| `coverage` | `drift-plan`, `drift` | ubuntu-latest | contents: read (workflow) | - | - | - | - | `always()` |

Artifacts: `down:drift-*`, `up:drift-${{ matrix.owner }}`

#### `present.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `present` | - | ubuntu-latest | contents: write (workflow) | permission-contents=read+permission-metadata=read | - | - | - | - |

Artifacts: `up:seal-transaction-${{ steps.target.outputs.owner }}__${{ steps.target.outputs.name }}-${{ github.run_attempt }}`, `up:sealed-${{ steps.target.outputs.owner }}__${{ steps.target.outputs.name }}`

#### `propose.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `dry-run` | - | ubuntu-latest | contents: read | permission-contents=read+permission-metadata=read | - | - | - | - |
| `write` | `dry-run` | ubuntu-latest | contents: read | permission-contents=write+permission-metadata=read+permission-pull-requests=write | - | - | - | `${{ inputs.do_propose && needs.dry-run.result == 'success' && needs.dry-run.outputs.proceed == 'true' }}` |

Artifacts: `down:${{ needs.dry-run.outputs.candidate_artifact }}`, `down:${{ steps.validate.outputs.candidate_artifact }}`

#### `sealing-scheduled.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `plan` | - | ubuntu-latest | actions: read, contents: read | - | - | - | - | - |
| `seal` | `plan` | (reusable call) | contents: write | - | - | cancel-in-progress: False, group: seal-${{ matrix.target.repository }} | yes | `${{ needs.plan.outputs.has_work == 'true' }}` |
| `publish-candidates` | `plan`, `seal` | (reusable call) | contents: read | - | - | - | yes | `${{ !cancelled() && needs.plan.outputs.has_work == 'true' && vars.REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED == '1' }}` |
| `propose` | `plan`, `seal` | (reusable call) | contents: read | - | - | - | yes | `${{ !cancelled() && needs.plan.outputs.has_publishable == 'true' && vars.REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED == '1' }}` |

#### `verify-app-installation.yml` job graph

| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |
|---|---|---|---|---|---|---|---|---|
| `verify-installation` | - | ubuntu-latest | contents: read (workflow) | permission-metadata=read | - | - | - | - |

<!-- END GENERATED: workflow-inventory -->

Notes the generated tables cannot say:

- **Secrets** (repository Actions secrets): `GH_APP_ID` and `GH_APP_PRIVATE_KEY` (the Repository
  Presenter GitHub App; every token is minted per job with `actions/create-github-app-token` and
  narrowed with `permission-*` inputs, shown in the "App token scope" column), `GPT_OSS_ENDPOINT`
  and `GPT_OSS_API_KEY` (the LLM gateway; only `present.yml` and the dispatch-only preflight in
  `monitor.yml`), `GITLAB_TOKEN` (the mirror only). `GITHUB_TOKEN` is the ambient per-run token,
  bounded by the `permissions` columns above. `sealing-scheduled.yml` passes secrets to the reusable
  workflows with `secrets: inherit`, so its callees see the same set.
- **Variables** (repository Actions variables, set by the owner; a gate opens only when the value is
  exactly `1`): `REPOSITORY_PRESENTER_SEALING_PAUSED`, `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED`,
  `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`, `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`.
  Unset means the default: sealing runs, every write stays off. `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED`
  exists in code (`components/metadata/apply.py`) but no workflow reads it: repository metadata is
  never written by a hosted run.
- **State credential:** `REPOSITORY_PRESENTER_STATE_TOKEN` is not an owner switch; `present.yml`
  sets it to the job's own `GITHUB_TOKEN` (hence `contents: write` on that workflow) in the steps that
  write durable-state refs to this repository, and `core/state/present_transaction.py` reads it. It
  is distinct from the read-only analysis App token and from the candidates write token.
- **Environments:** no workflow declares a GitHub `environment:`. The write jobs are guarded by the
  variables, the authorization records and branch protection, not by environment reviewers
  (`TC-REF-12-01` asks the owner whether to add reviewers; until then do not assume them).
- **Concurrency:** `monitor` cancels in flight; `present-<repo>`, `seal-<repo>`,
  `candidates-publish-<repo>` and `upstream-issues` never cancel a running transaction. Do not
  cancel a `write` job by hand; a write interrupted between branch, contents and pull request is
  reconciled by the next run.
- **Pinned toolchain per job:** python 3.11 everywhere (section 8), plus the toolchains `present.yml`
  installs itself (uv, dotnet, java 21, node 24, go 1.26, rust stable, g++ cmake ninja).

## 4. Kill switch

Fastest to slowest. Each is independent; use the narrowest that stops the harm.

1. **Pause sealing (no merge needed):** set the repository variable
   `REPOSITORY_PRESENTER_SEALING_PAUSED` to exactly `1`
   (`gh variable set REPOSITORY_PRESENTER_SEALING_PAUSED --body 1 -R babar-raza/repository-presenter`).
   The `plan` job of `sealing-scheduled.yml` then reports `has_work=false` and `has_publishable=false`
   with the notice "sealing paused by owner variable", before reading anything, so no `seal`,
   `publish-candidates` or `propose` leg starts. `monitor.yml` keeps observing. Any other value,
   empty or unset leaves sealing on. Resume: delete the variable or set it to `0`.
2. **Close a write gate:** unset (or set to anything but `1`) `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`
   (upstream pull requests), `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED` (this repository's
   `candidates/` pull requests) or `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` (upstream issues).
   The corresponding job does not run at all, and the code refuses independently of the YAML.
3. **Disable one workflow:** `gh workflow disable propose.yml -R babar-raza/repository-presenter`
   (re-enable with `enable`); later dispatches and schedules are refused by GitHub.
4. **Revoke a standing record:** revert the authorization record in `ops/proposal-authorizations/`
   (or the issue approval in `ops/issue_approvals/`); the write gate then refuses that target while
   everything else continues. Setting a registry entry's `mode` back to `dry_run` (or `disabled`) in
   `data/registry.json` has the same effect for the whole target.
5. **Hard stop:** suspend or uninstall the GitHub App on the organization; every token mint then
   fails before any write, and no workflow falls back to another credential.

After any stop, confirm with the next scheduled run (or `workflow_dispatch` of `monitor.yml`) that the
run is a no-op or skipped, and record the stop in `docs/DECISION_LOG.md`.

## 5. Rollback

- **A bad upstream pull request:** `gh pr close N -R <owner>/<repo> --delete-branch`. A closed or
  merged pull request for the same candidate is never recreated (`pr_already_closed` /
  `pr_already_merged`); to propose that candidate again draft a new record with `--supersedes-pr N`
  (`docs/PROPOSAL_WAVE_RUNBOOK.md`).
- **A bad candidate published into this repository:** the publication is a pull request on
  `candidates/<slug>/`; before merge, close it. After merge, `git revert` the merge commit through a
  pull request; `candidates/<slug>/CURRENT` then points back at the previous bundle, and the monitor
  reports the repository against it again.
- **A bad authorization or mode flip:** revert the wave pull request (records and mode flips go
  together); with the records absent and the entries at `dry_run`, both gates refuse any write.
- **A rotated credential that breaks a run:** restore the last known good value. Every credential path
  fails closed and none falls back to a weaker credential
  (`docs/CREDENTIAL_ROTATION_RUNBOOK.md` section 4).
- **A workflow change that breaks hosting:** revert the workflow commit; the workflows are not
  governed by a version cursor, only by `tests/test_*workflow*.py` and the rehearsal below.
- **Never** force-push, push a target's default branch, or edit state refs by hand.

## 6. Credential rotation

Per-secret procedure, App permission audit and rollback: `docs/CREDENTIAL_ROTATION_RUNBOOK.md`. The
secrets each workflow reads are listed in section 3; rotate only the names listed there for the
workflow concerned, then run `verify-app-installation.yml` (App credentials) or the monitor's
dispatch preflight (gateway credentials) once.

## 7. On red CI, an outage, a bad pull request

- **Red CI on `main` or a pull request:** a production defect (project rule: CI must stay green).
  Fix permanently in the same session; do not merge around it. Reproduce locally with
  `scripts/ci_check.sh`, and for a workflow-level cause with the rehearsal harness (section 8).
- **LLM gateway outage:** `present.yml` fails at its preflight and spends nothing. It is
  `BLOCKED_EXTERNAL`, retried at the next daily cycle; pause sealing (section 4) if the outage is
  long enough to burn the daily cap on retries.
- **GitHub outage or rate limit:** the monitor records `UNREACHABLE` per repository and stays green;
  `sealing-scheduled.yml` fails closed on partial or stale evidence rather than acting on it.
- **A bad pull request already open:** section 5, then record the defect in `docs/DEFECT_INDEX.md`
  through the normal work item path.

## 8. Local rehearsal: every workflow, in its hosted shape, before it is hosted

Tooling: `tools/workflow_rehearsal/` (never imported by `src/`). Prerequisites on this machine:
Docker, `act` (`C:\dev-tools\act\act.exe`, v0.2.89), the image `catthehacker/ubuntu:act-24.04`
(what `ubuntu-latest` is mapped to), and optionally `actionlint` (`D:\tools\actionlint`, v1.7.12).

| Command | What it does |
|---|---|
| `python tools/workflow_rehearsal/inventory.py [--write \| --check]` | prints or splices the section 3 tables |
| `python tools/workflow_rehearsal/shape_checks.py` | the repository's own YAML shape checks, then actionlint when installed |
| `python tools/workflow_rehearsal/harness.py dryrun` | `act -n` over every workflow: parse, resolve reusable calls, plan the job graph (no containers) |
| `python tools/workflow_rehearsal/harness.py monitor` | runs `monitor.yml` end to end against the local fakes |
| `python tools/workflow_rehearsal/harness.py down` | removes the harness's own sidecar container and network |

How the monitor run is wired: a Docker network `rp-rehearsal` carries one sidecar running
`fake_github.py`, which answers as `api.github.com` (REST) and as a git host (smart HTTP over bare
repositories built by `scenarios.py`). The job containers trust a throwaway CA, and a container-side
gitconfig rewrites `https://github.com/` to the local git host, so the **unmodified** workflow's
`create-github-app-token`, `repository-presenter monitor`, `git ls-remote` and clones all land on the
fakes. The App key and installation token are fake values; `result.json` records every request the
fakes saw, the count of recorded writes (always the fakes), and a leak scan over every output.

### Results (recorded 2026-10-11; evidence `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/validation/workflow-rehearsal-monitor.json`)

**Static.** `actionlint` 1.7.12 over all 11 workflows: exit 0, no findings (the shellcheck and pyflakes
integrations are not installed here, so `run:` scripts are not shell-linted). The repository's own shape
checks (`shape_checks.py`, pinned by `tests/test_workflow_rehearsal.py`, each defect class with a negative
control) are clean on every workflow. The generated inventory equals the section 3 block (a test).

**`monitor.yml`, end to end, unmodified, schedule event, image `catthehacker/ubuntu:act-24.04`, Python
3.11.17 from `setup-python`, App secrets and token fake, REST and git on the local fakes.**

| Scenario | Jobs | Result |
|---|---|---|
| `clean`: Cells-Java unchanged since its seal, 3D-Python head moved | health-check, drift-plan, drift (2 owner legs), coverage | **5 of 5 succeeded**, act exit 0. Cells-Java `CURRENT`; 3D-Python `UNKNOWN` (head moved; the fake cannot supply the sealed revision's tree, so the monitor says it cannot classify rather than guess). Coverage summary: both owners `INSTALLED`. 14 requests reached the fakes (13 REST, 1 git); 0 writes; leak scan clean |
| `mixed`: `clean` plus a registry repository deleted upstream (Cells-Go) | same | Product behaviour as designed: the Cells owner's leg goes **red** ("1 repositor(ies) unreachable, observation incomplete") and still uploads its evidence; the other leg's steps all pass (act marks it failed after its sibling; hosted GitHub would not); coverage stays green; 0 writes; leak scan clean |

**Hand-off replay.** The evidence artifacts of the `clean` run were fed through the two CLI steps of
`sealing-scheduled.yml`'s `plan` job (`monitor-drift-contract`, then `sealing-plan`): contract of 2
repository rows, `has_work=false` (nothing `DRIFTED`), exit 0. This is the replay that stands in for
the hosted Actions API download (`python tools/workflow_rehearsal/harness.py replay-plan`).

**Every workflow under `act -n` (parse, reusable-call resolution, job-graph plan, no containers):**
`audit-app-installations`, `candidates-publish`, `ci`, `liveness`, `mirror-gitlab`, `monitor`, `present`,
`propose`, `verify-app-installation` plan cleanly (2 to 155 seconds each; `present` is slowest because
`act` clones a dozen actions). `issues-scheduled` and `sealing-scheduled` stop in `act` with a fatal
decode error: `act` cannot unmarshal a `strategy.matrix` value that is a `${{ fromJSON(...) }}` expression.
GitHub accepts it and `actionlint` is clean; this is a typed `act` limitation, not a workflow defect.

**Per workflow: what runs locally, what is a documented gap** (the same table is `harness.py table`).

| Workflow | Local status | Gap, stated plainly |
|---|---|---|
| `monitor.yml` | **ran end to end** (above) | App-token mint ran against the fake; the real mint's server-side permission narrowing is hosted-only; the gateway preflight runs on dispatch only and was not exercised |
| `ci.yml` | ran fully under `act` on 2026-10-04 (`docs/DECISION_LOG.md`); planned here | three full pytest legs not re-run in this slice; the act image lacks cmake and ninja, the workflow installs them with apt |
| `sealing-scheduled.yml` | `plan` hand-off replayed (above); `act` cannot plan it | `gh run list/download` (Actions API and artifact store) is hosted-only; `seal`/`publish-candidates`/`propose` are the three workflows below |
| `present.yml` | planned by `act -n`; **not run** | needs the live LLM gateway, the toolchains, a read-only App token for the target and the state-ref token; a 2026-10-04 `act` run reached the mint step and failed closed |
| `candidates-publish.yml` | planned | its `write` job's pull request on this repository can be recorded by the fake REST; GitHub's checks, required reviews and branch protection are hosted-only; **not run** |
| `propose.yml` | planned | `dry-run` job is replayable; `write` needs an authorization record merged before the trigger commit and the target's live revision; **not run** |
| `issues-scheduled.yml` | `act` cannot plan it | analysis reads upstream through REST (fakeable); filing needs an approved record and the kill-switch variable; **not run** |
| `liveness.yml` | planned | reads Actions run history and pull requests through the hosted API; **not run** |
| `audit-app-installations.yml`, `verify-app-installation.yml` | planned | ask GitHub which organizations installed the App: hosted-only facts; **not run** |
| `mirror-gitlab.yml` | planned | pushes to GitLab with `GITLAB_TOKEN`: an outbound write, never run locally |

What the full autonomous cycle on synthetic upstreams needs next is `TC-REF-11`
(`tools/workflow_rehearsal/scenarios.py` already builds the six scenarios of `TC-REF-11-01`).

### Toolchains the hosted image lacks, and how the workflows provide them (TC-REF-10-03)

| Need | Hosted `ubuntu-latest` | How `present.yml` / `ci.yml` provide it | Typed limitation |
|---|---|---|---|
| Python 3.11 (presenter), 3.12, 3.13 (target venvs) | `setup-python` 3.11; others not present | `setup-uv` 0.12.21 then `uv python install` and `uv venv` under `RUNNER_TEMP` | none |
| Java | JDK present, version varies | `setup-java` temurin 21 (javac only; Maven is not invoked) | none |
| .NET | present | `setup-dotnet` 8.0.x and 10.0.x | none |
| Node, npm, tsc | node present | `setup-node` 24; `npm install typescript@5.9.3` on `PATH` | none |
| Go | present | `setup-go` 1.26 | none |
| Rust (cargo) | present | `dtolnay/rust-toolchain` pinned to a sha, stable | none |
| g++, cmake, ninja | g++ present; cmake and ninja not guaranteed | `apt-get install g++ cmake ninja-build` (in both workflows) | the machine's clang 19.1.7 (`C:/tools/rp-toolchains`) is not what runs hosted: a C++ example that depends on the compiler differs between a native seal and a hosted one |
| Windows-only examples | no Windows runner requested | none | a repository whose examples need Windows cannot be verified hosted; seal it where Windows exists |

**Decision for the owner (`TC-REF-10-03`, not made here):** where each ecosystem is sealed in production:
a hosted runner (consistent with the monitor; bundles must then be re-sealed once under hosted 3.11 Linux
because the environment fingerprint differs from the 3.13 Windows seals), or a self-hosted runner on this
machine (the existing runner is registered to a product repository, not this control repository: a new
registration for the control repository is an owner action). Until chosen, treat every hosted seal of a
natively sealed candidate as a re-seal.

### Hosted versus local: differences that matter

| Aspect | Hosted `ubuntu-latest` | This machine |
|---|---|---|
| Python | `actions/setup-python` installs **3.11** (`python-version: "3.11"` in monitor, present, sealing; CI runs 3.11, 3.12, 3.13) | bundles were **sealed on 3.13** natively on Windows |
| Bundle currency | `core` records the environment fingerprint (`python_version`, `os`, resolved site manifest, `inherited_units_version`) in each bundle (`components/readme/bundle/seal.py`). A hosted run on 3.11 / Linux therefore differs from a 3.13 / Windows seal: `evaluate()` reopens `EXTRACTING`, downstream stages make live provider calls, and the zero-call no-op claim does not hold across the two environments (`docs/DECISION_LOG.md` 2026-10-04 act verification; `docs/investigations/13-bump-cost-and-recheck-design.md`). | monitor is unaffected (it compares revisions, not fingerprints); sealing and no-op proof are |
| Fix / limitation | Decision for the owner (`TC-REF-10-03`): seal in the environment of record (hosted 3.11 Linux, so seals and the monitor agree), or run sealing on a self-hosted runner on this machine; until chosen a hosted seal of a natively sealed candidate is a re-seal, not a no-op | |
| Toolchains | image provides what GitHub documents (git, node, python, java, dotnet, go, rust, g++ preinstalled, **cmake and ninja not guaranteed**); `ci.yml` and `present.yml` install `g++ cmake ninja-build` with apt, `setup-dotnet`/`java`/`node`/`go`, `dtolnay/rust-toolchain`, `setup-uv` explicitly | machine-local registry `C:/tools/rp-toolchains` (llvm 19.1.7, cmake, ninja, cargo, dotnet, go, java via `RP_TOOLCHAIN_REGISTRY`), absent on a hosted runner |
| act image | n/a | `catthehacker/ubuntu:act-24.04` has no cmake, ninja or Python 3.11 in its toolcache (`setup-python` downloads it); same Ubuntu 24.04 userland, not the full GitHub image |
| Windows-only examples | not available on `ubuntu-latest` | a Windows example needs a Windows runner or this machine; none of the workflows requests one |
| `permissions:` | enforced by GitHub on `GITHUB_TOKEN` | **not enforced by act**; the YAML is checked statically (section 3) and the App token scopes are narrowed in the workflow, not by the local fake |
| `environment:` approvals, required reviewers, branch protection, required checks | hosted | not modelled (no workflow declares an environment) |
| Actions API (`gh run list`, artifacts of earlier runs), scheduling, concurrency queues | hosted services | `sealing-scheduled.yml` `plan` and `liveness.yml` read them; not reproducible locally, replayed by script where feasible |
| Real App token mint, installation lookup, rate limits | real | fake service; its server-side permission narrowing and 401/403 semantics are hosted-only |
| Network | outbound to GitHub, PyPI, registries | same reads (act fetches `actions/*` from GitHub; setup-python and pip fetch from the internet); **no write leaves the machine** |
