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
the reason (`source_moved`, no README, not final, not listed); re-seal those or leave them out.
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
   `gh api repos/R/issues/N --jq .performed_via_github_app.id` must print `5092474`.
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

## 8. The upstream issue logger shares the same preconditions

`issues-scheduled.yml` files an issue only for a repository in registry mode `full`, only with a
committed `ops/issue_approvals/<handoff-id>.json` for that exact handoff
(`ops/issue_approvals/README.md`), only while the repository variable
`REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` is `1`, and only where the App holds issues:write.
As of 2026-10-10 six aspose repositories hold a `HANDOFF_PENDING` handoff, all registry `dry_run`,
none filed upstream. The mode flip in the wave pull request is therefore also what arms issue
filing for them; the approvals and the variable are separate owner acts.
