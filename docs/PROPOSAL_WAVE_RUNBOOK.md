# Proposal wave runbook

How to open many real README pull requests in one sitting, under one owner signature, without
weakening any gate. Authority: `docs/EXECUTION_STATE_MACHINE.md` G6, `docs/STATE_MACHINE.md`
sections 11-12, `AGENTS.md` Security and Effects. This file adds no gate and no work item; it
sequences the existing ones (G6-W02 mechanism, G6-W03 first real PRs, G6-W06 mode flips, OWNER-04
App installation, OWNER-20 per-repository decision). A candidate reaching `READY_FOR_PROPOSAL`
never implies authorization: each target needs its own exact, dated owner authorization.

Tool: `repository-presenter wave-readiness` (`components/propose/wave.py`). It reads, prints and
writes only into a scratch directory you name. It never writes to GitHub, never writes into
`ops/proposal-authorizations/`, never edits `data/registry.json`.

## 0. What the pipeline needs, per target (all four, every time)

| # | Requirement | Where it is enforced |
|---|---|---|
| 1 | Registry entry listed, active, `mode: full` | `core/registry/write_gate.py` (refusal `registry_dry_run`) |
| 2 | A sealed `READY_FOR_PROPOSAL` candidate on `main` under `candidates/<slug>/` whose sealed revision equals the target's live default-branch head right now | `core/candidates.py::load_proposable_candidate`, `propose` dry-run and again inside `write` (refusal `source_moved`) |
| 3 | `ops/proposal-authorizations/<owner>__<name>__<first 12 of candidate hash>.json`, merged to `origin/main` before the commit the run is triggered at, unexpired (at most 7 days from issue), bound to repository, candidate hash, source revision, base branch, presenter branch `repository-presenter/readme-update`, PR intent, policy version | `core/authorization/proposal.py`, `record_provenance.py` |
| 4 | The GitHub App installed on the target with contents:write, pull_requests:write, metadata:read (analysis: contents:read) | `propose.yml` mints a read token in `dry-run` and a write token in `write`; both fail the job if the App is not installed on that repository |

Not required for the manual path, and kept OFF during the wave: the repository variable
`REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`. It gates only the unattended caller in
`sealing-scheduled.yml`. A manual `workflow_dispatch` of `propose.yml` with `do_propose=true` sets
the in-step switch itself, and is the owner's explicit act. Leave the variable unset: otherwise the
daily sealing run could also propose for full-mode repositories that hold a record.

Two things the effect does not do, so plan for them: it writes `README.md` exactly (a target whose
live head has no `README.md` would receive a second file; `wave-readiness` flags that as a
blocker), and it requires the live head to equal the sealed revision, not merely the README to be
unchanged. Any commit to the default branch since sealing refuses that target with `source_moved`
until it is re-sealed. Measured 2026-10-10 on 29 sealed candidates: 10 already had a moved head.
Re-seal immediately before the wave and run it the same day.

## 1. Owner prerequisites (manual, have latency, do these first)

1. App installation, for every organization holding a target (OWNER-04). In GitHub:
   `https://github.com/organizations/<org>/settings/installations` then Configure on
   repository-presenter. Repository access must be "All repositories" (or every target listed).
   The permissions panel must show Contents: write, Pull requests: write, Issues: write
   (issue filing), Metadata: read. Accept any pending permission update. Then dispatch
   `audit-app-installations.yml` and read each leg's final line (it proves one representative
   repository per organization with metadata:read only; it cannot show write permissions or the
   other repositories of an organization).
2. Decide the repositories (OWNER-20) and sign the batch authorization (section 7). The signature
   names each repository and the first 12+ characters of its candidate hash.
3. Confirm the first-live-exercise rule (`docs/STATE_MACHINE.md` 12.1): the very first real PR of
   the whole project goes to the target the owner names, alone, and is verified (section 5) before
   the rest are dispatched. No live external write has ever been made (DECISION_LOG 2026-10-10).

## 2. Pre-checks (operator, read-only)

```
git fetch origin && git switch --detach origin/main          # a fresh main checkout
export GH_TOKEN="$(gh auth token)"                           # read-only calls; avoids the 60/h anonymous limit
repository-presenter wave-readiness                          # every READY_FOR_PROPOSAL candidate
```

Columns: registry mode, candidate hash, sealed revision, `live` (current, or MOVED to the new
head), `README.md` at the live head, authorization record state (none, valid+merged, valid but not
merged, expired, mismatch), staleness (informational: a bundle behind the running code is still
proposable by hash; the owner decides whether stale content is acceptable). Verdict BLOCKED lists
the reason (`source_moved`, no README, not final, not listed, or a propose-gate refusal:
`review_predates_honesty_record`, `review_rejection_overridden`, `no_op_proof_missing`,
`acceptance_not_passed`); re-seal those or leave them out. The propose gate (not READY_FOR_PROPOSAL
itself) requires an honest review, a measured no-op proof and the ratified 30-point outcome PASS.
Budget about 6 seconds per candidate for the live reads.

## 3. The signature, then the one pull request

1. Owner approves the list in the exact form of section 7 (recorded in `docs/DECISION_LOG.md`).
2. Emit the records and the flipped registry into a scratch directory (never `ops/`):

```
repository-presenter wave-readiness \
  --authorize-file wave.txt --approver "<owner login>" \
  --issued-at 2026-10-11T09:00:00Z --expires-at 2026-10-13T09:00:00Z \
  --emit-records "$TEMP/wave-1011"
```

   `wave.txt` holds one `OWNER/NAME@HASH` line per approved repository. `--issued-at` must not be
   later than the moment the wave pull request merges (omit it to use now); `draft-proposal-
   authorization` is not used here because it requires the entry to be `full` already. The command refuses the
   whole batch (writes nothing) when a repository is unlisted, blocked, source-moved, has no
   README, is not in the assessed selection, when a hash no longer matches what the owner approved,
   or when the window is expired, empty, or longer than 7 days.
3. In a fresh worktree from `scripts/new_worktree.sh`: copy the emitted `*.json` record files into
   `ops/proposal-authorizations/`, copy the emitted `registry.json` over `data/registry.json`
   (it differs from the committed one only in the `mode` of the listed entries), run
   `bash scripts/ci_check.sh`, open ONE pull request, have a person review it (reviewers read the
   diff: N record files, N one-line mode changes), merge it. The records authorize nothing until
   this merge; the run that consumes them must be triggered after it.
4. Verify: `repository-presenter wave-readiness` on the new main shows READY_TO_DISPATCH for each.

## 4. Dispatch, paced

`dispatch-plan.sh` (from the emit step) is a reviewed list of lines like
`gh workflow run propose.yml -R babar-raza/repository-presenter --ref main -f repo=<owner/name>
-f authorization_record=ops/proposal-authorizations/<file>.json -f do_propose=true`, separated by
`sleep 30`. The tool never runs it; the operator does, after the first target (prerequisite 3) is verified.

- Concurrency: `propose.yml` serializes per target (`propose-<repo>`), so two runs never race on
  one presenter branch. Different targets run in parallel; a run is two jobs, roughly 3-5 minutes.
- GitHub limits (docs.github.com, "Rate limits for the REST API" and "Best practices"): secondary
  limits are 100 concurrent requests, 900 REST points per minute, and no more than 80
  content-generating requests per minute and 500 per hour; wait at least one second between
  mutating requests; honor `retry-after`. App installation tokens get at least 5,000 requests per
  hour per installation. One target makes three content-generating requests (branch ref, contents
  PUT, pull request), so 20 targets make 60 in total. The 30-second stagger therefore keeps every
  installation far below the limits; its purpose is that the operator can watch each run and stop.
  A rate-limited run fails with `github_error`; re-dispatch it later (the effect is idempotent).
- Watch: `gh run list --workflow propose.yml -R babar-raza/repository-presenter --limit 30`.
  A refusal prints `proposal refused (exit 3)` with a typed code and writes nothing.

## 5. Verify each pull request

For each target `R` and PR number `N` (from the run log line `pr: <url>`):

1. Authored by the App, from the target's own presenter branch, to its default branch:
   `gh pr view N -R R --json author,headRefName,baseRefName,isCrossRepository,files,commits`
   expects author `app/repository-presenter`, head `repository-presenter/readme-update`,
   `isCrossRepository` false, exactly one file `README.md`.
   `gh api repos/R/issues/N --jq .user.login` must print `repository-presenter[bot]` (the
   `performed_via_github_app` field is null on App-created pull requests; do not use it).
2. The diff equals the sealed README byte for byte:
   `gh api "repos/R/contents/README.md?ref=repository-presenter/readme-update" --jq .content |
   base64 -d | sha256sum` equals the sha256 of `candidates/<slug>/<revision>/README.md` (the
   `files["README.md"].sha256` entry in its `manifest.json`; the record's `candidate_hash` is the
   same text with line endings normalized to LF).
3. No direct push to a default branch: `gh api repos/R/commits/<base> --jq .sha` still equals the
   record's `source_revision` (or only the owner's own later commits sit above it), and the
   `base_branch` has no commit authored by the App.
4. The PR body carries `candidate_hash` and `source_revision` equal to the record's.

## 6. Roll back, and stop midway

- Stop dispatching: Ctrl-C the loop. Targets not yet dispatched are never started. In-flight
  `write` jobs finish on purpose (a write interrupted between branch, contents and PR leaves the
  reconciliation to the next run); do not cancel them.
- Emergency brake, no merge needed: `gh workflow disable propose.yml -R babar-raza/repository-presenter`
  (re-enable with `enable`). Every later dispatch is refused by GitHub.
- Undo one target: `gh pr close N -R R --delete-branch`. Note that a closed or merged PR for the
  same candidate is never recreated (`pr_already_closed` / `pr_already_merged`); to propose that
  candidate again, draft a new record with `--supersedes-pr N`.
- Undo the authorization: revert the wave pull request (records and mode flips go together). With
  the records absent and the entries back at `dry_run`, both gates refuse any further write.
- Hard stop: remove the App from the organization (`Settings > Installations > Configure >
  Uninstall` or suspend). All token mints then fail before any write.
- Nothing here ever force-pushes or pushes a target default branch; the only writes are the
  presenter branch, one `README.md` commit on it, and its pull request.

## 7. Batch authorization text (the owner approves exactly this)

Record in `docs/DECISION_LOG.md` (append-only), in this form, with the real values:

```
- **YYYY-MM-DD HH:MM UTC · owner batch authorization of the README proposal wave · G6-W03, G6-W06, OWNER-20**
  - Authorization. I, <owner name and GitHub login>, authorize repository-presenter to open one
    pull request against each repository below, carrying that exact sealed README and nothing else.
  - Repositories (OWNER/NAME @ candidate hash, first 16 characters; sealed source revision):
      aspose-xxx-foss/Aspose.Xxx-FOSS-for-Java @ 0123456789abcdef; rev <40 hex>
      ... (N lines; no repository is authorized unless it appears here)
  - Effect. Pull request only, from branch `repository-presenter/readme-update` to the repository's
    default branch, authored by the repository-presenter GitHub App; no merge, no direct push, no
    other file, no issue, no metadata change. Registry mode becomes `full` for exactly these N
    repositories (which also makes them eligible for issue filing; that still needs its own
    approval records and the issues kill switch).
  - Window. Valid from <issued_at> to <expires_at> UTC (at most 7 days). A candidate whose hash or
    sealed revision differs from the line above is not authorized and is re-listed, not proposed.
  - Conditions I rely on and the operator verified before dispatch: wave-readiness showed each
    repository current with a README.md; the App holds contents:write and pull_requests:write on
    each; REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED is unset.
  - Revocation. I may revoke at any time by reverting the wave pull request or disabling propose.yml.
```

## 8. The upstream issue logger has its own registry switch

`issues-scheduled.yml` files an issue only for a repository whose registry entry is issue-eligible:
`issues_mode` is `file`. `issues_mode` (`off | dry_run | file`) is optional; when absent it derives
from `mode` (`full` -> `file`, otherwise `dry_run`), so an entry that sets nothing behaves as it
did before. Issue filing and issue closing consult `issues_mode`; README proposals and metadata
writes consult `mode` only. An entry with `issues_mode: file` and `mode: dry_run` can therefore
have an issue filed while its README proposal stays refused, and `issues_mode: off` refuses issue
effects even at `mode: full`. A `disabled` entry is refused every effect. The workflow's target
matrix comes from the handoff ledger (`issue-targets`), not the registry; the write gate decides
per leg. A filing also needs a committed `ops/issue_approvals/<handoff-id>.json` for that exact
handoff (`ops/issue_approvals/README.md`), the repository variable
`REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` set to `1`, and the App holding issues:write.
As of 2026-10-10 six aspose repositories hold a `HANDOFF_PENDING` handoff, all registry `dry_run`,
none filed upstream. Setting `issues_mode: file` on an entry (an owner act, separate from the wave
pull request's mode flip) arms issue filing for it without arming its README pull request; the
approvals and the variable remain separate owner acts.

## 9. The sandbox canary (owner decision D6, 2026-10-11)

The pause on real upstream pushes stands. The one exception is a README-correction pull request
against the owner's throwaway repository `babar-raza/presenter-sandbox` (OWNER-11), opened by the
real propose path so that the first write to a product repository is not also the first write ever.
It adds no gate: every gate of section 0 applies unchanged. Nothing below is run by an agent; each
step says who acts, and every step is reversible (section 9.7).

### 9.1 How the sandbox is a target without touching the portfolio

The sandbox is not an Aspose product (the name gate refuses it) and must not move a denominator, so
it lives in its own file, `data/registry_sandbox.json`, read only when a command is given
`--sandbox` (`core/registry/sandbox.py`). The production registry, the monitor, the sealing run,
`status` counts and `wave-readiness` are never given the file; the target is a literal in
`core/registry/sandbox.py` (a second sandbox is a reviewed code change), the entry is
README-proposal only (`issues_mode: off`), and a repository in both registries is refused. The
entry shipped at `mode: dry_run`: closed. `canary.py assemble` sets it to `full` in the same pull
request as the authorization record, exactly as the wave flips modes (section 3), so the owner
reads that line (the `family`, `platform` and `ecosystem` lines beside it in the same diff are the
seed product's own vocabulary, section 9.2). The workflow is `propose-sandbox.yml`: dispatch only, the target a literal (no
`repo` input), the same two jobs and App-token scopes as `propose.yml`, and a `sandbox-canary`
environment on the write job. The repository variable
`REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` stays UNSET (it arms the unattended sealing run);
the write step sets the in-process switch itself, only on `do_propose`.

### 9.2 What is proposed, and why it is the sandbox's own copy of a product

A correction needs facts, and facts need a source tree, so a README-and-LICENSE sandbox (what it was:
2 files, head `fb26260d`) would end as `insufficient_evidence`. The owner seeds it once with one
product's committed tree. The seed is `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET @
941814fd138dc28cf47123d48194f329f283498d` (454 files, 9.7 MB; no `.github/`, so nothing runs or is
offered in the sandbox). Its correction is the first real pull request in miniature: **one
`DIAGRAM_FIX`** (the At a Glance diagram redrawn left to right, same labels and edges) and **one
content change** (`MISSING_SECTION` plus its `MISSING_INFO` contents-list item: a `## Dependencies`
section stating `SkiaSharp 2.88.8` and the target frameworks `netstandard2.0;net8.0`, each cited to
the `.csproj` that declares it). The diagram was drawn headless on Mermaid 11.17.2, 11.4.1, 11.12.0
and 12.1.0, natively and in five wider fonts: horizontal, 0 clipped. The typed gate accepts the
bundle; the correction is byte-identical to the one `correct-readme` makes against the product
itself at that revision. Since the sandbox is a copy, the registry entry carries the product's own
vocabulary (family `cells`, platform `net`, ecosystem `net`), and a test pins that. Diagram-only
(Email-Python, 14 other products) and other content corrections are the same path with another seed.
Not `Aspose.Cells-FOSS-for-Go`: its bundle is refused by the correction gate on this base with `a
run over the corrected README finds further corrections: the result is not final` (a defect in the
correction lane's settle step, reported to the lead).

**One commit, reproducible, so the bundle can be merged before the owner pushes.** The bundle, the
record and the hosted dry run all name the sandbox's source revision: the commit the seeding creates.
`tools/canary/seed.py --commit` makes that commit offline and identically on every machine: its tree
is the product's tree at the pinned revision minus `.github/`, its parent is the sandbox head
`fb26260d`, and its author, committer, date and message are constants. `ops/sandbox-canary/seed.json`
records it (`5c41a5028b37fa3e9812dcd0c1320fe7248929f5`); `--commit` refuses unless the commit it
makes equals the pin, so what the owner pushes is exactly what the reviewed bundle corrects. Until
the owner pushes it the sandbox head stays `fb26260d`, and every run refuses `source_moved`
(nothing can write). It reads the product's blobs with git plumbing, so `core.autocrlf`, file-mode,
signing or identity settings on the owner's machine cannot change the id (the rehearsal proves it
with a hostile configuration).

### 9.3 Owner prerequisites (UI, once, latency; do first)

| # | Where | Exactly what | You will see |
|---|---|---|---|
| O1 | github.com/settings/installations, the App `repository-presenter` | Install it on account `babar-raza`, "Only select repositories", choose `presenter-sandbox`; or, if already installed, Configure and add that repository. Accept the permission list the App registered (Contents, Pull requests, Issues, Administration read/write; Metadata read): each hosted token is narrowed to contents + pull requests + metadata | the repository listed under the installation |
| O2 | `babar-raza/repository-presenter` > Settings > Environments > New environment | Name `sandbox-canary`; Required reviewers: yourself; leave "Prevent self-review" OFF | the environment with one reviewer. Skipped, GitHub creates it unprotected on first use and the write job runs without a pause |
| O3 | Settings > Secrets and variables > Actions | Nothing to add: `GH_APP_ID` and `GH_APP_PRIVATE_KEY` exist. Confirm the variable `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` is NOT listed, and **do not create it**: the write job sets that switch itself, in its one step, only when `do_propose` is ticked; the repository variable would arm `sealing-scheduled.yml`'s unattended propose job instead (`REPOSITORY_PRESENTER_SEALING_PAUSED=1` is what holds that job today) | only `REPOSITORY_PRESENTER_SEALING_PAUSED` among the variables |

`PYTHONPATH=src python tools/canary/canary.py preflight --root .` (read-only, `GH_TOKEN` from `gh auth token`)
lists every item with its owner action; the App installation is the one line a user token cannot
read (`CONFIRM`): the dry-run job's token step is its proof.

### 9.4 The sequence (O = owner acts; A = operator, local, read-only toward GitHub)

The operator has already done the work of steps A1 to A3; they arrive as ONE pull request, merged in
step 4. Nothing is enabled until the owner has done steps 1 to 4 and dispatched step 6. The record's
window is **7 days from its issue time** (`issued_at` 2026-10-12T02:35:31Z, `expires_at`
2026-10-19T02:35:31Z): dispatch inside it, or the operator re-drafts it (`canary.py assemble
--replace` after re-checking `preflight`; a re-draft changes only the window).

- **A1: the bundle**, made against the not-yet-pushed seed commit: a local bare copy of the pinned
  seed commit stands in for the sandbox's clone URL (the only seam replaced; facts extraction, the
  build and the correction are the repository's own code, `GH_TOKEN` set, no model call):
  `repository-presenter correct-readme --sandbox --repo babar-raza/presenter-sandbox --out DIR`
  expects `corrected: 3 edit(s) (DIAGRAM_FIX 1, MISSING_INFO 1, MISSING_SECTION 1)`.
- **A2: seed pin**: `python tools/canary/seed.py --product product --sandbox sandbox --write-pin
  --product-repository aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` wrote `ops/sandbox-canary/seed.json`.
- **A3: assemble**: `PYTHONPATH=src python tools/canary/canary.py assemble --root . --bundle DIR
  --approver babar-raza` wrote `ops/sandbox-canary/bundle/` (the bundle, `PULL_REQUEST.md` = the text the
  effect will post, `SHA256SUMS`), set the sandbox entry to `full` and drafted
  `ops/proposal-authorizations/babar-raza__presenter-sandbox__fa4a4f68a6d6.json`. `assemble` refuses a
  bundle that does not correct the pinned seed commit. Then `bash scripts/ci_check.sh`.

The owner's steps (1 to 3 in any order; 4 before 5, because the seed pin comes with the pull request):

1. **O: install the App on the sandbox** (section 9.3, O1).
2. **O: create the `sandbox-canary` environment** (O2).
3. **O: confirm the variable `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` is NOT set** (O3). It must
   stay unset: the write step sets it in-process, only when `do_propose` is ticked; the repository
   variable of that name arms the unattended `sealing-scheduled.yml` propose job instead (and two
   production entries are already `mode: full`).
4. **O: review and merge the canary pull request.** Files changed shows `ops/sandbox-canary/seed.json`
   (the commit to be pushed), the bundle (`PULL_REQUEST.md` first, then `README.patch`, the exact edit,
   and `corrections.json`, its evidence; `facts.json` and `tree.txt` are what the gate re-derives it
   from), the sandbox entry's `mode` `dry_run` to `full` (and the product vocabulary lines), and the
   record (repository, candidate hash, source revision = the seed commit, approver `babar-raza`,
   window). The record authorizes nothing until this merge, and a run triggered before it cannot use
   it. Merged but not seeded, every dispatch refuses `source_moved`.
5. **O: seed the sandbox** (your own git login; the only push of this canary to the sandbox, a
   fast-forward). From a checkout of this repository on `main` after the merge:
   ```
   git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.git product
   git -C product checkout 941814fd138dc28cf47123d48194f329f283498d       # read-only
   git clone https://github.com/babar-raza/presenter-sandbox.git sandbox
   python tools/canary/seed.py --product product --sandbox sandbox            # plan; changes nothing
   python tools/canary/seed.py --product product --sandbox sandbox --commit   # makes the pinned commit
   git -C sandbox push origin seed:main                                       # the one write; never --force
   ```
   The `--commit` run ends `commit 5c41a5028b37fa3e9812dcd0c1320fe7248929f5 equals the pin ... Nothing is
   pushed.` Any other id is a refusal: do not push. After the push the sandbox shows 454 files, the
   product's README, and the head commit `Seed the sandbox with Aspose.Cells-FOSS-for-.NET at
   941814fd...` by "Repository Presenter canary seed". `PYTHONPATH=src python tools/canary/canary.py
   preflight --root .` then reads `OK sandbox seeded` and `OK bundle freshness`.
6. **O: hosted dry run.** Actions > Propose (sandbox canary) > Run workflow, `authorization_record` =
   `ops/proposal-authorizations/babar-raza__presenter-sandbox__fa4a4f68a6d6.json`, `do_propose`
   unchecked. A green `dry-run` job whose log says `the authorization record matches this candidate`
   and whose token step succeeded (the App is installed). No `write` job.
7. **O: the write (P1).** The same dispatch with `do_propose` checked. The `write` job waits for your
   approval (O2); approve it. The log ends `effected=True - proposed` and `pr: .../pull/1`.
8. **A: verify (read-only):** `PYTHONPATH=src python tools/canary/canary.py verify --root . --expect open`.

### 9.5 The proofs, and what each looks like

| # | Do | Observe |
|---|---|---|
| P1 | step 7 | one pull request from `repository-presenter/readme-update` to `main`, authored by the App (`verify`: `performed by the App`, id 5092474; `gh api repos/babar-raza/presenter-sandbox/issues/1 --jq .user.login` prints `repository-presenter[bot]`), one file `README.md`, branch README equal to the bundle's, `main` untouched, body carrying `candidate_hash` and `source_revision`, one commit `Update README via repository-presenter` naming the approver. The title is the bundle's `PULL_REQUEST.md` title (`docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right`); Files changed shows exactly the three hunks of `README.patch` (the contents-list item, the `## Dependencies` section, the diagram) |
| P2 no duplicate | dispatch step 7 again | `effected=True - no change needed`; still one pull request, no new commit (`verify` unchanged) |
| P3 closed is final | O closes pull request 1 without merging, then dispatch again | the `write` job fails with `pr_already_closed`; no new pull request or commit; `verify --expect closed` |
| P4 stale source | O commits anything to the sandbox `main` (UI: edit a file), then dispatch again | `source_moved` (the dry-run job already refuses); nothing written; the next canary needs a new seed pin, bundle and record (A1 to A3, then steps 4 to 5) |
| P5 interrupted run | optional, before P1 on a clean sandbox: O creates the branch `repository-presenter/readme-update` from `main` in the UI, then step 7 | the run finds the branch, writes the one commit, opens the one pull request: the state a run that died between its writes converges. A lost response cannot be injected on GitHub; it is proven in `tests/test_canary_rehearsal.py` (a PUT whose answer is lost is reconciled by reading, never re-sent) |

Not proven by the canary, said plainly: GitHub's required-review and branch-protection behavior on a
product repository (the sandbox's `main` is unprotected), a maintainer's response, and any
organization-level App permission screen.

### 9.6 Rehearsal

`tests/test_canary_rehearsal.py` takes every step above through the same entry points against a local
bare sandbox, a local bare product, a control repository with a real `origin/main`, and the workflow
rehearsal's stateful fake REST: seeding (the pinned commit, made on a clone with a hostile git
configuration, and its refusals), `correct-readme --sandbox`, `assemble` (and its refusal of a bundle
that is not for the pinned commit), `preflight` before and after the seed, the dry run and the
write, `verify`, a rerun, a closed pull request, a moved head, an interrupted write, a lost response,
and the refusals (switch closed, no token, a personal access token, a token reaching more than the
sandbox, an unmerged or edited record, an edited bundle, the sandbox without `--sandbox`, a product
with it). `tests/test_propose_sandbox_workflow.py` pins the workflow.

### 9.7 Rollback, every step

- Stop everything: `gh workflow disable propose-sandbox.yml -R babar-raza/repository-presenter`.
- Undo the pull request: `gh pr close N -R babar-raza/presenter-sandbox --delete-branch`. A closed
  pull request is never recreated for the same candidate.
- Revoke the authorization: revert the canary pull request in the control repository (record, bundle
  and the `full` flip go together). With the record absent and the entry `dry_run`, both gates refuse.
- Undo the seed (no force): `git -C sandbox fetch origin && git -C sandbox checkout main && git -C
  sandbox pull --ff-only origin main && git -C sandbox revert --no-edit 5c41a5028b37fa3e9812dcd0c1320fe7248929f5
  && git -C sandbox push origin main` (the sandbox is README and LICENSE again; the canary's record then
  refuses `source_moved`), or delete and recreate the throwaway repository (a new repository id:
  update `data/registry_sandbox.json`).
- Hard stop: Configure the installation and remove `presenter-sandbox`, or Suspend the App.

### 9.8 Removal after the canary

When the canary is recorded (run ids, the pull request URL, the `verify` output) and the owner has
decided the exact real list (OWNER-20), one revert removes `propose-sandbox.yml`,
`data/registry_sandbox.json`, `ops/sandbox-canary/`, `core/registry/sandbox.py`, the `--sandbox`
flags, `tools/canary/` and their tests; `propose.yml`'s sealed-candidate path was never changed by it.
The real list then goes through `propose.yml`'s correction mode (a dispatch that names
`correction_run`; `docs/OPERATIONS_RUNBOOK.md` section 12 has the exact owner steps), with its own
bundles, records and registry flips assembled by `tools/corrections/assemble.py`.
