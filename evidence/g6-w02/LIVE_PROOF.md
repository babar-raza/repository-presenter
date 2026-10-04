# G6-W02 live proof record (disposable target only)

Target: `babar-raza/repository-presenter` (the control repository, used as the disposable target).
Never any `aspose-*-foss` repository. Presenter branch: `repository-presenter/readme-update`.
Proof PR: #191, base `main`, closed unmerged on 2026-10-04 09:40:03Z.
Input fixture: `evidence/g6-w02/proof-readme-v1.md` (committed on `g6-w02-live-proof`).

## Hosted path (propose.yml)

- Dry run, run 37192739260, 2026-10-04 09:37:13Z: failed at "Mint a fresh installation token".
  The mint step returned HTTP 404 from the repository-installation lookup. The GitHub App is not
  installed on `babar-raza/repository-presenter`. No write was attempted (the dry-run step was skipped).
- Consequence: no hosted proposal step ran, so the hosted path is unproven for this target.

## Local path (repository-presenter propose --propose, real CLI and real client)

Credential: the user-level `GITHUB_TOKEN`, loaded in-process only as `GH_PROPOSAL_WRITE_TOKEN`
with `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED=1`. Never printed, logged, or persisted.
Used because the App is not installed on the target and the lost-response case cannot be produced
from a hosted dispatch.

| # | Outcome | Time (UTC) | Result |
|---|---------|-----------|--------|
| 3 | Stale source blocks before any write | before 09:38:39Z | PASS. Source revision `3509aca6...` against live `a1eb4f52`: `effected=False`, "stale source" refusal. Presenter branch still absent (404) and PR count unchanged (30) before and after. |
| 1 | Create branch and PR | 09:38:52Z | PASS. Source revision `a1eb4f52a92d8a7324117e4eaf8a5fe5601d32b7`. Branch created from main, commit `02d56519`, PR #191 created (`commit_written=True pr_created=True`). |
| 2 | Unchanged second invocation writes nothing | 09:39:07Z | PASS. `effected=True`, reason "no change needed", `commit_written=False pr_created=False pr_updated=False`. Still exactly one presenter PR (#191). |
| 4a | Lost put_contents, write landed | 09:39:17Z-09:39:28Z | PASS. One PUT (09:39:22Z, commit `62f0074d`). The response was reported lost. Reconciliation re-read the branch (09:39:25Z), matched, and made no retry. PR #191 updated in place (`pr_updated=True`). |
| 4b | Lost put_contents, write did not land | 09:39:34Z-09:39:44Z | PASS. Two PUTs total (09:39:39Z lost, 09:39:40Z reconciled retry, commit `1ae1e13d`). Reconciliation observed the old content first, so the retry was taken only after reconciliation. |
| 5 | No direct push to default branch | checked 09:40Z | PASS. Target `main` head stayed `a1eb4f52`. All three proof commits are on `repository-presenter/readme-update` only. |

Final presenter README content: v3 (`proof-readme-v3.md` text, scratch fixture, not committed).
The presenter branch was left in place as the proof record. It was not deleted.

## Still open

- Hosted propose.yml end to end: blocked (`BLOCKED_EXTERNAL`) until the GitHub App is installed on
  `babar-raza/repository-presenter`. Resume predicate: the Propose dry run's mint step succeeds, then
  one hosted `do_propose=true` run reproduces outcomes 1 and 2 with the same effect evidence.
- G6-W02 status remains PENDING in `project/state.yaml`. This record proves the write mechanism
  locally against the real target, not the hosted path.
