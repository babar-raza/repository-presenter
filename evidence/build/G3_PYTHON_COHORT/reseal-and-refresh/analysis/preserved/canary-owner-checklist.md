authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Sandbox canary - OWNER CHECKLIST (one page)

Target: `babar-raza/presenter-sandbox` only. Every product repository stays paused. **Nothing below has
been done and nothing is enabled by opening the pull request.** Full runbook:
`docs/PROPOSAL_WAVE_RUNBOOK.md` section 9. Pull request: https://github.com/babar-raza/repository-presenter/pull/334 (branch
`canary/sandbox-seed-1012`).

**Deadline: the authorization record expires 2026-10-19T02:35:31Z (7 days from 2026-10-12T02:35:31Z).**
Dispatch the write (step 7) before then; if it lapses the operator re-drafts it (only the window changes).

**Read this first - one correction to the plan.** Do NOT set the repository variable
`REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`. The sandbox workflow sets that switch itself, inside
its one write step, only when you tick `do_propose`. The *repository* variable of that name instead arms
`sealing-scheduled.yml`'s unattended propose job (today held only by `REPOSITORY_PRESENTER_SEALING_PAUSED=1`;
two production entries, `3D-FOSS-for-Java` and `Cells-FOSS-for-Java`, are already `mode: full`). The
canary does not need it. Leave it unset.

What the canary proposes: the sandbox is seeded with `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET @
941814fd138d` (454 files, no `.github/`). The pull request the App then opens in the sandbox has THREE
hunks: a `- [Dependencies](#dependencies)` contents-list item, a new `## Dependencies` section
(`SkiaSharp 2.88.8`; `netstandard2.0;net8.0`, each cited to its `.csproj`), and the At a Glance diagram
redrawn left to right (same labels and edges; drawn headless on Mermaid 11.4 to 12.1, 0 clipped).

| # | You do (exact names) | You will see | Undo |
|---|---|---|---|
| 1 | https://github.com/settings/installations > **Repository Presenter** (App id 5092474) > **Configure** > Repository access > **Only select repositories** > select `presenter-sandbox` > **Save**. Not installed yet: Install on account `babar-raza`, pick **Only select repositories** > `presenter-sandbox`, accept the permission list (Contents, Pull requests, Issues, Administration: read/write; Metadata: read; each hosted token is narrowed to Contents + Pull requests + Metadata for this one repository) | `presenter-sandbox` listed under the installation | Configure > remove the repository, or Suspend |
| 2 | `babar-raza/repository-presenter` > Settings > Environments > **New environment** > name `sandbox-canary` > Configure environment > tick **Required reviewers** > add **babar-raza** > **Save protection rules**. Leave "Prevent self-review" OFF | the environment with one required reviewer | delete the environment |
| 3 | Settings > Secrets and variables > Actions > **Variables**: confirm only `REPOSITORY_PRESENTER_SEALING_PAUSED` is listed. **Do not add `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`.** No secret or variable is added for the canary (`GH_APP_ID` and `GH_APP_PRIVATE_KEY` already exist) | one variable, `REPOSITORY_PRESENTER_SEALING_PAUSED = 1` | - |
| 4 | **Review and merge the pull request** (merge commit, like #331/#332). Files changed: `ops/sandbox-canary/seed.json` (the one commit you will push), `ops/sandbox-canary/bundle/` (read `PULL_REQUEST.md` first, then `README.patch`; `corrections.json` is the evidence; `facts.json`/`tree.txt` are what the gate re-derives the edit from; `SHA256SUMS` checks the copy), `data/registry_sandbox.json` (`mode` `dry_run` -> `full`, plus the `family`/`platform`/`ecosystem` lines = the seed product's vocabulary), `ops/proposal-authorizations/babar-raza__presenter-sandbox__fa4a4f68a6d6.json` (repository, candidate hash `fa4a4f68a6d6...`, source revision = the seed commit `5c41a5028b37...`, approver `babar-raza`, window), tools, tests, docs | the files above on `main`; Actions list has **Propose (sandbox canary)**. Merged but not yet seeded, every dispatch refuses `source_moved` (nothing can write) | revert the merge (record, bundle and flip go together) |
| 5 | **Seed the sandbox** (your git login; ONE fast-forward push to your own throwaway repo). In a `main` checkout of this repo after the merge, with Python 3.11+ and git 2.30+: `git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.git product` ; `git -C product checkout 941814fd138dc28cf47123d48194f329f283498d` ; `git clone https://github.com/babar-raza/presenter-sandbox.git sandbox` ; `python tools/canary/seed.py --product product --sandbox sandbox` (plan: 454 files, changes nothing) ; `python tools/canary/seed.py --product product --sandbox sandbox --commit` (must end `commit 5c41a5028b37fa3e9812dcd0c1320fe7248929f5 equals the pin ... Nothing is pushed.` - any other id: do NOT push) ; `git -C sandbox push origin seed:main` (never `--force`) | github.com/babar-raza/presenter-sandbox: 454 files, the product's README, head commit `Seed the sandbox with Aspose.Cells-FOSS-for-.NET at 941814fd...` by "Repository Presenter canary seed"; `python tools/canary/canary.py preflight --root .` (with `GH_TOKEN`) then shows `OK sandbox seeded`, `OK bundle freshness` | `git -C sandbox revert --no-edit 5c41a5028b37fa3e9812dcd0c1320fe7248929f5` and push (no force); or delete and recreate the repo (new id: tell the operator) |
| 6 | Actions > **Propose (sandbox canary)** > **Run workflow** > Branch `main`; `authorization_record` = `ops/proposal-authorizations/babar-raza__presenter-sandbox__fa4a4f68a6d6.json`; `do_propose` **unchecked** > Run workflow | green `dry-run` job; log: `the authorization record matches this candidate`; the "Mint a read-only installation token" step is green (= the App is installed on the sandbox); no `write` job | - |
| 7 | Same dispatch with `do_propose` **checked**. The `write` job shows *Waiting*: click **Review deployments** > tick `sandbox-canary` > **Approve and deploy** | log ends `effected=True - proposed` and `pr: https://github.com/babar-raza/presenter-sandbox/pull/1`; PR by `repository-presenter[bot]`, branch `repository-presenter/readme-update` -> `main`, one file `README.md`, title `docs(readme): add the Dependencies section ...`, body ends with `candidate_hash` and `source_revision` | `gh pr close 1 -R babar-raza/presenter-sandbox --delete-branch` |
| 8 | Tell the operator; they run `python tools/canary/canary.py verify --root . --expect open` | every line `OK` | - |

**Optional proofs after step 7** (each tells you the safety property held): P2 dispatch again with
`do_propose` checked -> `no change needed`, still one PR. P3 close PR 1 without merging, dispatch again ->
`pr_already_closed`, nothing written. P4 commit anything to sandbox `main`, dispatch again -> `source_moved`,
nothing written. P5 (before step 7, on the clean sandbox) create branch `repository-presenter/readme-update`
from `main` in the UI -> the run still ends with one commit and one PR.

**Stop everything at any time:** `gh workflow disable propose-sandbox.yml -R babar-raza/repository-presenter`
(or remove the repo from the App installation). Nothing here touches an Aspose repository, the production
registry or the daily runs.
