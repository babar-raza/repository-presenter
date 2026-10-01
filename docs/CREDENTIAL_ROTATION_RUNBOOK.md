# Credential Rotation Runbook

Status: operational runbook, G7-W04 (`docs/EXECUTION_STATE_MACHINE.md` G7 Work item 1).
Owns: the rotation procedure for every secret this project's runtime reads
(`src/repository_presenter/core/secrets.py`'s `SECRET_VARIABLES`) plus the GitHub App's own
registered credentials (`tools/github_app/manifest.json`), the App's permission-minimum audit, and
rollback/fail-closed behavior. Does not own authorization policy (`AGENTS.md` "Security and
Effects") or the write-gating mechanism itself (`components/metadata/apply.py`,
`components/issues/file.py`), which this document follows, not sets.

## 1. Scope

Nine credentials, in two families:

- **Runtime secrets** (`core/secrets.py`'s `SECRET_VARIABLES`, as of this writing):
  `GPT_OSS_API_KEY`, `GH_TOKEN`, `GH_METADATA_WRITE_TOKEN`, `GH_ISSUES_WRITE_TOKEN`.
- **GitHub App credentials** (`tools/github_app/register_exchange.py`'s `SECRET_MAP`, added to
  `SECRET_VARIABLES` explicitly in this same work item - see §5.1): `GH_APP_ID`,
  `GH_APP_PRIVATE_KEY`, `GH_APP_CLIENT_ID`, `GH_APP_CLIENT_SECRET`, `GH_APP_WEBHOOK_SECRET`.

`GPT_OSS_ENDPOINT` and `GPT_OSS_MODEL` are configuration, not credentials - they carry no secret
value and are never in `SECRET_VARIABLES`. `GITLAB_TOKEN` (used by `.github/workflows/mirror-gitlab.yml`)
is a real GitHub Actions secret on this repository but is not one of this project's own runtime
credentials (`mirror-gitlab.yml` is infrastructure, not `src/`); it is still caught by
`SECRET_SUFFIXES`' `_TOKEN` match if it is ever read into this project's own process environment, but
it has no rotation procedure here - it is GitLab's own credential, rotated on GitLab's own schedule.

Every credential below is read only from the process environment, never from a file
(`.env.example`, `core/config.py`); every one is masked by `core/secrets.py::redact()` before any
text is persisted, and every one is scanned for verbatim leakage into a sealed candidate bundle by
`find_secret_leaks()` (`tests/core/test_secrets.py`).

## 2. Per-secret rotation procedure

### 2.1 `GPT_OSS_API_KEY`

- **What it is:** bearer key for the OpenAI-compatible chat-completions gateway at
  `https://llm.professionalize.com/v1/` - a LiteLLM proxy in front of a self-hosted vLLM backend
  (`docs/DECISION_LOG.md`, 2026-09-24 entries name the backend directly:
  `text-model.vllm-qwen.svc.cluster.local`, and the key-validation error body names LiteLLM's own
  `LiteLLM_VerificationTokenTable`). Every LLM-backed job in this project routes through it
  (`core/config.py::load_gateway_config`, `core/preflight.py`).
- **Where generated/obtained:** the LiteLLM proxy's own virtual-key issuance, controlled by
  whoever administers `llm.professionalize.com` (the "gateway operator" named in
  `docs/DECISION_LOG.md`'s 2026-09-24 10:02 UTC entry) - **not** self-service from this project's
  own tooling. A LiteLLM proxy issues/regenerates virtual keys through its admin API
  (`POST /key/generate`, `POST /key/regenerate`) authenticated by the proxy's own master key, which
  this project does not hold; the bearer key this project uses (`GPT_OSS_API_KEY`) cannot mint or
  regenerate itself.
- **Where stored:** `GPT_OSS_API_KEY` and `GPT_OSS_ENDPOINT` as GitHub Actions repository secrets
  on `babar-raza/repository-presenter` (consumed by `.github/workflows/monitor.yml`), plus the
  owner's own local shell/User-environment copy for interactive `preflight`/`present` runs
  (`docs/DECISION_LOG.md`'s 2026-09-24 entries read it via
  `[System.Environment]::GetEnvironmentVariable('GPT_OSS_API_KEY','User')`).
- **Rotation steps:**
  1. Gateway operator issues a new virtual key on the LiteLLM proxy (new value, old value still
     live - LiteLLM's `/key/regenerate` and most virtual-key schemes support an overlap window;
     confirm this before relying on one, since a hard-cutover scheme has no overlap step).
  2. `gh secret set GPT_OSS_API_KEY --repo babar-raza/repository-presenter` with the new value
     (stdin, never a shell arg - a value passed as `--body` on the command line can land in shell
     history/process listings; pipe it in instead).
  3. Update the owner's own local User-environment copy to the same new value.
  4. **Verify:** trigger `.github/workflows/monitor.yml` (`gh workflow run monitor.yml`) and
     confirm the "LLM gateway reachable" step succeeds (`repository-presenter preflight` reaches
     the gateway, lists the model catalog, and routes every prompt manifest cleanly) - this is the
     one step in this project that calls the gateway from a hosted run today. Locally, `repository-presenter preflight` succeeding with the new key value is the same proof.
  5. Gateway operator revokes/expires the old key at the proxy once the hosted and local checks
     both pass.
- **What "verify" means:** `repository-presenter preflight` exits cleanly and prints a model
  catalog (not a `ConfigError`/`GatewayError`), either locally or as `monitor.yml`'s "LLM gateway
  reachable" step - never "a request didn't immediately fail," since `preflight`'s own fail-closed
  design (`core/preflight.py::run_gateway_preflight`) already requires every routed model to appear
  in the live catalog before it reports success.
- **Fail-closed behavior, confirmed by direct code read:** `core/config.py::load_gateway_config`
  raises `ConfigError` naming `OWNER-02` and its resume predicate if the key is absent or empty -
  no job ever runs against a guessed or default endpoint. A present-but-wrong key reaches the
  gateway and gets a `401`/`403` from LiteLLM's own `LiteLLM_VerificationTokenTable` check
  (reproduced live, `docs/DECISION_LOG.md` 2026-09-24 10:02 UTC), which `core/preflight.py`
  surfaces as a `GatewayError` - no silent fallback to a cached catalog or a different key exists
  anywhere in this path.

### 2.2 `GH_TOKEN`

- **What it is:** repository-scoped, read-only GitHub token for local analysis clones
  (`cli.py`'s `pinned_read_only_clone` call, `core/git_safety/clone.py`). Never used by any
  `.github/workflows/*.yml` today (confirmed: no workflow file references `secrets.GH_TOKEN`).
- **Where obtained:** a GitHub personal access token (classic or fine-grained), scoped read-only
  to the repositories this project analyzes - created by the owner at
  `https://github.com/settings/tokens` (or the fine-grained equivalent) under the owner's own
  account, since this project's analysis clones are attributed to the operator running them, not
  to the GitHub App (the App's own installation tokens are reserved for App-scoped production
  effects - see §3).
- **Where stored:** the operator's own local process environment only (`.env.example`); not a
  GitHub Actions secret on this repository today.
- **Rotation steps:**
  1. Generate a new PAT with the same read-only repository scope at
     `https://github.com/settings/tokens`.
  2. Set it in the operator's own shell/User environment as `GH_TOKEN`.
  3. **Verify:** `repository-presenter status` (reads the canary via `pinned_read_only_clone`) or
     a direct `gh api user` call with the new token returns HTTP 200
     (`docs/DECISION_LOG.md`'s own diagnostic precedent:
     `env -u GH_TOKEN -u GITHUB_TOKEN gh api user`).
  4. Revoke the old PAT at `https://github.com/settings/tokens` once the new one is confirmed
     working.
- **What "verify" means:** a fresh `present`/`status` run reaches the clone step without a
  `GitSafetyError`/authentication failure, or the direct `gh api user`/`.../repos/{owner}/{repo}`
  probe returns 200.
- **Fail-closed behavior:** `cli.py` reads `GH_TOKEN` as `os.environ.get("GH_TOKEN") or None` and
  passes it straight into `pinned_read_only_clone`; an invalid or expired token fails the clone
  with a real git/HTTP error, never a silent anonymous/unauthenticated fallback that would just
  rate-limit sooner.

### 2.3 `GH_METADATA_WRITE_TOKEN`

- **What it is:** write-scoped token for `components/metadata/apply.py`'s gated PATCH
  (description/homepage) and PUT (topics) calls - deliberately never `GH_TOKEN`
  (`AGENTS.md` "Write credentials exist only in a separate effect job and are short-lived and
  target-scoped"). **Unset in this project's environment today** - the write path is built and
  tested, never fired (`docs/REPOSITORY_LAYOUT.md`, `docs/DECISION_LOG.md`).
- **Where obtained:** either (a) a GitHub App installation token minted with `administration:write`
  from the App already registered in `tools/github_app/manifest.json` (preferred once G6/G7's
  effect path is live - short-lived, target-scoped, minted per run via
  `actions/create-github-app-token`, matching `verify-app-installation.yml`'s own precedent), or
  (b) until that path is wired into a real write workflow, a manually-provisioned fine-grained PAT
  with `Administration: write` on the specific target repository.
- **Where stored:** not currently a GitHub Actions secret (confirmed:
  `gh api repos/babar-raza/repository-presenter/actions/secrets` does not list it). When the
  write path is armed, it belongs in the effect job's own environment only, per `AGENTS.md`
  - never alongside `GH_TOKEN` in the same job.
- **Rotation steps:** same generate -> store -> verify -> revoke shape as `GH_METADATA_WRITE_TOKEN`'s own
  sibling below; since nothing holds a live value today, "rotation" is moot until OWNER-04/G6 arms
  it. Once armed: mint or generate the replacement, set the Actions secret, verify (next), revoke
  the old credential at its source (App installation token: nothing to revoke, it already expired;
  PAT: revoke at `https://github.com/settings/tokens`).
- **What "verify" means:** `apply_metadata_diff` (`components/metadata/apply.py`) for one target
  repository returns `authorized=True` and `wrote_anything=True` for at least one field a real diff
  proposes, observed by re-reading the repository's own `description`/`homepage`/`topics` after the
  call - never just "the call returned 200," since GitHub's own eventual-consistency window makes a
  read-back the only real confirmation.
- **Fail-closed behavior, confirmed by direct code read:** `apply.py::write_authorized` returns
  `True` only when `REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED` is exactly `1`/`true`/`yes`
  (absence or any other value is unauthorized); `core/github/client.py::update_repository`/
  `replace_topics` separately raise `RepositoryMetadataError` ("PATCH/PUT refused - no write-scoped
  token") if `token` is falsy. Both conditions are independent and both must hold - a token's mere
  presence never implies authorization, and authorization never substitutes for a real token. This
  is a design property, not an assumption: read directly in `apply.py` lines 50-64 and
  `client.py`'s `update_repository`/`replace_topics` guards for this runbook.

### 2.4 `GH_ISSUES_WRITE_TOKEN`

- **What it is:** write-scoped token for `components/issues/file.py`'s gated `POST .../issues`
  call - the `Issues: write` analog of §2.3, same separation-from-`GH_TOKEN` discipline. Unset
  today; built and tested, never fired.
- **Where obtained:** a GitHub App installation token minted with `issues:write` (preferred, same
  App), or a manually-provisioned PAT scoped to `Issues: write` on the target repository, until the
  App-minting path is wired into a real issue-filing workflow.
- **Where stored:** not currently a GitHub Actions secret (confirmed, same listing as §2.3). Lives
  in the effect job's own environment only once armed.
- **Rotation steps:** identical shape to §2.3 - generate, store, verify, revoke; moot until
  OWNER-04/G6-W01 arms the path.
- **What "verify" means:** `components/issues/file.py`'s gated path successfully files one real
  issue against a disposable or already-confirmed-safe target and the returned `CreatedIssue`
  (`number`, `url`) is read back via a GET on the same issue - not just a 201 status.
- **Fail-closed behavior, confirmed by direct code read:** mirrors §2.3 exactly -
  `AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"`, same truthy-value-only
  gate, same `_NO_TOKEN_REASON`/`RepositoryMetadataError("... POST refused - no write-scoped
  token")` pairing in `core/github/client.py::create_issue`.

### 2.5 `GH_APP_ID`

- **What it is:** the numeric GitHub App identifier (`5092474`, per `project/state.yaml`'s
  OWNER-04 note) - not secret-valued in the sense of granting access by itself, but named in
  `SECRET_VARIABLES` (added this work item, §5.1) because it is one credential field of a single
  atomic registration and because `actions/create-github-app-token` requires it paired with the
  private key in every workflow that mints a token.
- **Where obtained:** GitHub's App-manifest conversion flow
  (`tools/github_app/register.html` -> `register_exchange.py`), a one-time registration; GitHub
  never reissues a different ID for the same App.
- **Where stored:** GitHub Actions repository secret `GH_APP_ID` on
  `babar-raza/repository-presenter` (confirmed present).
- **Rotation:** this value does not rotate on its own - it is immutable for the App's lifetime.
  It is only ever replaced if the App itself is deleted and re-registered (an extreme, last-resort
  action - see §4), in which case every other App credential (§2.6-§2.9) is replaced in the same
  action.
- **What "verify" means:** not applicable on its own; verified jointly with `GH_APP_PRIVATE_KEY`
  (§2.6) since both are required together to mint a token.

### 2.6 `GH_APP_PRIVATE_KEY`

- **What it is:** the GitHub App's RSA private key (PEM) - the single highest-privilege credential
  this project holds. Paired with `GH_APP_ID`, it mints short-lived (1-hour), installation-scoped
  tokens carrying the App's full registered permission set (`metadata:read`, `contents:write`,
  `issues:write`, `pull_requests:write`, `administration:write` - `tools/github_app/manifest.json`)
  against any organization the App is installed on (15 orgs today, per OWNER-04's note).
- **Where generated/obtained:** GitHub's App settings UI -
  `https://github.com/settings/apps/repository-presenter/keys` (or
  `https://github.com/organizations/<org>/settings/apps/repository-presenter/keys` if the App
  is later transferred to an org) - "Generate a private key" button. **This is a manual,
  owner-only UI action; there is no API to generate an App private key.** GitHub allows multiple
  active private keys simultaneously (each download is a distinct key the App will accept), which
  makes a real overlap-then-revoke rotation possible without any downtime.
- **Where stored:** GitHub Actions repository secret `GH_APP_PRIVATE_KEY` on
  `babar-raza/repository-presenter`, consumed by `.github/workflows/verify-app-installation.yml`
  and `.github/workflows/audit-app-installations.yml` via `actions/create-github-app-token`. Never
  written to disk or printed by `register_exchange.py` (confirmed by direct code read - it is
  received from `gh api`'s JSON response and piped straight to `gh secret set` without an
  intermediate file).
- **Rotation steps:**
  1. Owner opens `https://github.com/settings/apps/repository-presenter/keys` and clicks
     "Generate a private key" - downloads a new `.pem`. The old key stays valid until explicitly
     deleted (real overlap window).
  2. Owner (or an agent session handed the `.pem` content directly, never via a file committed or
     logged) runs
     `gh secret set GH_APP_PRIVATE_KEY --repo babar-raza/repository-presenter` with the new PEM
     content on stdin.
  3. **Verify:** `gh workflow run verify-app-installation.yml` then confirm the run mints a token
     and reads the canary repository successfully (the exact resume-predicate proof OWNER-04
     already used once, 2026-09-28, run `36392582131`) - this is the project's own existing,
     already-proven verification mechanism for this exact credential, reused here rather than
     invented fresh.
  4. Owner deletes the old private key from the App's settings page once the verification run is
     green.
- **What "verify" means:** `verify-app-installation.yml`'s "Mint an installation token, read the
  canary repository with it" step succeeds and its log line reads
  `installation reaches <canary> (default branch: ...)` - proof the new key mints a real,
  working, correctly-scoped token, not merely that the secret was accepted by `gh secret set`.
- **Fail-closed behavior, confirmed by direct code read:** `actions/create-github-app-token`
  (the official GitHub action, not hand-rolled JWT signing - `verify-app-installation.yml`'s own
  comment names this as the deliberate battle-tested choice) fails the step outright if the key is
  invalid, revoked, or does not match `GH_APP_ID` - there is no fallback token source anywhere in
  either workflow that consumes it, and both workflows hold only `permissions: contents: read` at
  the job level, so a failed mint cannot fall back to the workflow's own ambient `GITHUB_TOKEN`
  either (that token has no cross-organization reach regardless).

### 2.7 `GH_APP_CLIENT_ID` / 2.8 `GH_APP_CLIENT_SECRET`

- **What they are:** the App's OAuth client credentials - used for user-to-server OAuth flows
  (a human logging in "as" the App), not for the server-to-server installation-token flow this
  project actually uses. **Reserved: no code path in `src/` or `.github/workflows/` reads either
  value today** (confirmed: no reference outside `register_exchange.py`'s own storage step and
  `SECRET_VARIABLES`).
- **Where obtained:** the same App-manifest conversion response as `GH_APP_ID`/
  `GH_APP_PRIVATE_KEY` (`register_exchange.py`'s `SECRET_MAP`); re-obtaining them individually (not
  as part of a full re-registration) is not exposed anywhere in the App settings UI - GitHub shows
  the client ID on the App's settings page but only re-generates the client *secret* there
  (`https://github.com/settings/apps/repository-presenter` -> "Generate a new client secret").
- **Where stored:** GitHub Actions repository secrets `GH_APP_CLIENT_ID`/`GH_APP_CLIENT_SECRET`
  (confirmed present).
- **Rotation steps (client secret only - client ID does not rotate, same reasoning as `GH_APP_ID`):**
  1. Owner clicks "Generate a new client secret" on the App's settings page (old secret is
     invalidated immediately on this one - GitHub does not offer an overlap window for client
     secrets, unlike the private key).
  2. `gh secret set GH_APP_CLIENT_SECRET --repo babar-raza/repository-presenter` with the new
     value on stdin.
  3. **Verify:** not applicable today in the sense of a hosted check, since nothing consumes it -
     verification is "no code path broke," confirmed by `scripts/ci_check.sh` passing (it does not
     exercise this value, so this is a weak verification; the honest statement is that this
     credential has no real exercise path until an OAuth user-flow is built).
- **What "verify" means today:** there is nothing to verify against live behavior - record the
  rotation in `docs/DECISION_LOG.md` and move on; do not invent a test against unused code.

### 2.9 `GH_APP_WEBHOOK_SECRET`

- **What it is:** HMAC secret for validating GitHub webhook payload signatures. **Reserved: the
  App's `hook_attributes.active` is `false`** (`tools/github_app/manifest.json`) - webhooks are
  registered but not delivered, and no code in this project receives or validates a webhook today.
- **Where obtained:** same App-manifest conversion response; re-obtaining it alone is exposed at
  `https://github.com/settings/apps/repository-presenter` -> "Webhook" section -> regenerate.
- **Where stored:** GitHub Actions repository secret `GH_APP_WEBHOOK_SECRET` (confirmed present).
- **Rotation steps:** regenerate on the App settings page, `gh secret set
  GH_APP_WEBHOOK_SECRET --repo babar-raza/repository-presenter` with the new value on stdin.
- **What "verify" means today:** nothing to verify against live behavior - same honest statement
  as §2.7/2.8. If a future work item activates webhook delivery, this runbook's §2.9 gets a real
  verify step added in that same item, not invented speculatively here.

## 3. App permission-minimum audit (this work item's own required cross-check)

`tools/github_app/manifest.json`'s `default_permissions`, checked against what `src/` actually
exercises today, by direct code search (not assumed from the manifest's own intent):

| Permission             | Used today                                             | Code path                                                                 |
|-------------------------|--------------------------------------------------------|----------------------------------------------------------------------------|
| `metadata: read`         | **Yes** - every read.                                   | `core/github/client.py::get_repository`, `core/github/read_client.py`, `verify-app-installation.yml`/`audit-app-installations.yml`'s own GET calls |
| `administration: write`  | Built, gated, **not yet fired live**                    | `components/metadata/apply.py::apply_metadata_diff` -> `update_repository`/`replace_topics` (PATCH description/homepage, PUT topics) |
| `issues: write`          | Built, gated, **not yet fired live**                    | `components/issues/file.py` -> `core/github/client.py::create_issue` |
| `contents: write`        | **Reserved - no code path yet**                         | G6-W02's planned PR-effect path: pushing a candidate's committed README change to a branch before opening a PR (not built; `project/state.yaml` G6-W02 `PENDING`) |
| `pull_requests: write`   | **Reserved - no code path yet**                         | G6-W03's planned path: opening the PR itself via `POST /repos/{owner}/{repo}/pulls` (not built; `project/state.yaml` G6-W03 `PENDING`) |

**Conclusion: the registered set is the minimum actually needed, including for work not yet
built.** Nothing registered is speculative-forever - `contents:write` and `pull_requests:write`
are both the literal, named scope of G6-W02/G6-W03 (`project/state.yaml`, both `PENDING`, both
priority-ordered ahead of most other open work), not a guess at future need. No permission is
requested beyond this set (no `checks`, no `actions`, no `organization_*` permission exists in the
manifest). Per this work item's own instruction, nothing is removed - `contents:write`/
`pull_requests:write` stay registered for the landed-but-not-yet-fired-in-this-direction work
that already has a work-item id and a priority slot.

## 4. Rollback

**If a rotated credential breaks a live run, the project's own code already fails closed - verified
by direct read, not assumed, for every write-capable credential:**

- **`GPT_OSS_API_KEY`:** `core/config.py::load_gateway_config` raises `ConfigError` if absent;
  `core/preflight.py::run_gateway_preflight` raises `GatewayError` if the live catalog rejects a
  routed model or the gateway returns a non-2xx (a bad/revoked key included, since LiteLLM answers
  `401` through its own `LiteLLM_VerificationTokenTable` check). No job proceeds on a failed
  preflight - `cli.py`'s entry points call `preflight` before any job that needs the gateway, and a
  `ConfigError`/`GatewayError` is an uncaught, process-exiting failure, never swallowed into a
  default/cached catalog. **Rollback:** re-set the GitHub Actions secret (and the owner's local
  environment copy) to the last-known-working value; re-run `preflight` to confirm; this is
  reversible within minutes since the old key is only revoked at the gateway *after* a new key is
  confirmed working (§2.1 step 5 - never revoke-then-verify).
- **`GH_METADATA_WRITE_TOKEN` / `GH_ISSUES_WRITE_TOKEN`:** confirmed above (§2.3/2.4) - a missing
  or invalid token raises `RepositoryMetadataError` naming exactly which call was refused
  (`"PATCH/PUT/POST refused - no write-scoped token"` for absence; GitHub's own 401/403 surfaces
  unchanged for an invalid-but-present token, since `client.py` never inspects or interprets the
  body of an auth failure beyond raising). **Rollback:** both write paths are already gated behind
  a separate, owner-controlled authorization flag (`REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED`
  / `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`) that defaults to unauthorized - flipping either
  flag back off is itself an immediate, total rollback of that write path, independent of the
  token's own state.
- **`GH_APP_PRIVATE_KEY`:** confirmed above (§2.6) - `actions/create-github-app-token` fails the
  workflow step outright on an invalid/mismatched key; neither workflow that consumes it has a
  fallback credential at all (`permissions: contents: read` is the whole grant at the job level).
  **Rollback:** GitHub supports multiple simultaneously active private keys per App, so the
  rotation procedure itself (generate new, verify, *then* delete old) already is the rollback-safe
  order - if the new key's own verify step fails, the old key is still valid and the secret can be
  reset to the prior PEM with no App-side action needed.
- **`GH_TOKEN`:** read-only; a bad value fails the clone step with a real git/HTTP authentication
  error (`core/git_safety/clone.py`), never a silent anonymous fallback. Rollback is "set it back
  to the last-known-working value."
- **General principle, confirmed project-wide:** no code path in `src/` catches a credential
  failure and substitutes a different, weaker credential to keep going - every one of the five
  write/mint-capable paths above either raises all the way up (uncaught `ConfigError`/
  `GatewayError`/`RepositoryMetadataError`) or fails the GitHub Actions step outright. This matches
  `AGENTS.md`'s "Security and Effects" requirement directly: rollback is always "restore the last
  good secret value," never "the code quietly degrades."

## 5. What this work item actually exercised

### 5.1 Code fix, not merely documented

While auditing `core/secrets.py::SECRET_VARIABLES` (§1) against the GitHub App's own five
credential fields, found that `GH_APP_PRIVATE_KEY`, `GH_APP_ID`, and `GH_APP_CLIENT_ID` were not
covered by either the explicit set or the `_API_KEY`/`_TOKEN`/`_SECRET`/`_PASSWORD` suffix
heuristic (`GH_APP_PRIVATE_KEY` ends in `_KEY`, not the narrower `_API_KEY`; the two ID fields have
no secret-shaped suffix at all) - meaning the single highest-privilege credential this project
holds was silently exempt from `find_secret_leaks()`'s candidate-bundle leak canary. Fixed by
adding all five GitHub App credential names to `SECRET_VARIABLES` explicitly
(`src/repository_presenter/core/secrets.py`), with a regression test
(`tests/core/test_secrets.py::test_every_github_app_credential_is_a_configured_secret`).

### 5.2 Real dry-run rotation exercised: `GPT_OSS_ENDPOINT` / `GPT_OSS_API_KEY` wired into GitHub Actions for the first time, and verified hosted

Before touching anything, confirmed via `gh api repos/babar-raza/repository-presenter/actions/secrets`
that only six secrets exist on this repository (`GH_APP_ID`, `GH_APP_PRIVATE_KEY`,
`GH_APP_CLIENT_ID`, `GH_APP_CLIENT_SECRET`, `GH_APP_WEBHOOK_SECRET`, `GITLAB_TOKEN`) -
`GPT_OSS_ENDPOINT`/`GPT_OSS_API_KEY` were **not** present, despite `project/state.yaml`'s
`OWNER-04` summary listing them as part of what it provided. Cross-checked against
`.github/workflows/monitor.yml`'s own run history: `gh run list --workflow=monitor.yml` and a
direct `gh api .../actions/workflows/<id>/runs` both returned zero runs, ever - `monitor.yml` had
never executed even once, so OWNER-04's own resume predicate was verified only for the GitHub
App half (correctly, via `verify-app-installation.yml`/`audit-app-installations.yml`'s real runs),
never for the gateway half. This is a real, previously-undocumented gap, found by re-verifying
live state rather than trusting the recorded `SATISFIED` claim at face value.

Given this project's own `GPT_OSS_API_KEY`/`GPT_OSS_ENDPOINT` process-environment values (the
credential OWNER-02 already provides to every session, per `project/state.yaml`), the following was
exercised for real, this session, with real evidence:

1. `repository-presenter preflight` run locally first, confirming the current key value genuinely
   reaches the gateway (`gateway: llm.professionalize.com reachable`, 7-model catalog, 6 prompt
   manifests routed) - a safe, read-only baseline before touching any stored secret.
2. `GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY` set as real GitHub Actions repository secrets on
   `babar-raza/repository-presenter` for the first time (`gh secret set`, value piped via stdin
   from a scratch file under `runs/` deleted immediately after, never passed as a CLI argument or
   committed) - closing the gap found above, not a value change.
3. `gh workflow run monitor.yml` dispatched; the resulting run
   (`https://github.com/babar-raza/repository-presenter/actions/runs/36832254935`) completed
   successfully end to end, including the "LLM gateway reachable" step, which printed the same
   `gateway: llm.professionalize.com reachable` / 7-model-catalog output as the local run, with
   both `GPT_OSS_ENDPOINT`/`GPT_OSS_API_KEY` correctly masked (`***`) in the step's own logged
   `env:` block. This is `monitor.yml`'s first-ever successful execution.

**What this is, honestly: establishing a working credential in its first hosted use, not a value
rotation** - the key material itself did not change. It proves the half of the rotation procedure
this session could safely exercise end-to-end (store -> verify, via a real hosted run), and it
closes a real, previously-undiscovered prerequisite gap (the gateway secrets were never wired into
Actions at all) that would otherwise have made a genuine rotation dry-run impossible to verify
hosted regardless of what this session did.

### 5.3 What remains for the owner / a future session

A genuine value-rotation of `GPT_OSS_API_KEY` needs the gateway operator to issue a new virtual key
at the LiteLLM proxy admin level (§2.1) - this session holds only the regular bearer key, not the
proxy's own master key, and has no dashboard login for `llm.professionalize.com`. Once a new key
exists: `gh secret set GPT_OSS_API_KEY --repo babar-raza/repository-presenter` (stdin) with the new
value, `gh workflow run monitor.yml` to verify hosted, then revoke the old key at the proxy. This is
the literal, remaining half of §2.1's own rotation procedure.

`GH_APP_PRIVATE_KEY`'s own dry-run rotation (§2.6) needs the owner to click "Generate a private
key" at `https://github.com/settings/apps/repository-presenter/keys` - a manual UI action this
agent session has no login to perform, and GitHub provides no API equivalent. Once a new key is
downloaded and its content handed to a session (never as a committed file), the same
`gh secret set` -> `gh workflow run verify-app-installation.yml` -> confirm -> delete-old-key
sequence in §2.6 completes the exercise; `verify-app-installation.yml` is already proven to work as
a verification mechanism (OWNER-04, 2026-09-28, run `36392582131`), so the remaining work is purely
the owner's one manual click, not any undemonstrated code or process risk.

No other credential in this runbook (§2.3, §2.4, §2.7, §2.8, §2.9) has a live value to rotate today
- each is either unset (§2.3/2.4) or has no code path exercising it yet (§2.7/2.8/2.9); their
rotation procedures above are real and actionable the moment each is armed, but nothing was or
could be dry-run against them without inventing a code path this work item does not own.
