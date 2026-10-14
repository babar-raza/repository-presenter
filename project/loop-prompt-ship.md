# Ship loop — one bounded iteration (the active mission prompt since 2026-10-14)

You are the executor for Repository Presenter. Run ONE bounded iteration of the ladder in §2,
then yield. Start from the files, never from memory. This prompt exists because six weeks of
plans, cards and records produced zero deliverables; its only purpose is artifacts with URLs.

## 0. What you inherit, what is different

Read `project/loop-prompt.md` §0 (rules), §4 (verify, record, commit, push), §5 (blockers) and
§8 (report) and follow them exactly, with these substitutions, which win on any conflict:

- **Your queue is the ladder in §2, in order.** Never `project/state.yaml`'s `next_ready_items`,
  never a card in `plans/reseal-and-refresh/PLAN.md`. Sections 11A to 11D of that plan are
  backlog: read a card only when a rung names it. **Do not add** a plan section, card,
  requirement, charter, investigation, owner item or register sentence. One `docs/DECISION_LOG.md`
  entry per shipped artifact, at most eight lines, written after the artifact exists.
- **Progress has one unit here: artifacts with URLs** (upstream issues filed; correction pull
  requests opened and merged on the Cells repositories), with `authorizable N/44` beside it.
  Sealed counts, tests, evidence and closed cards are not progress.
- **No governed version moves** (`NORMALISATION_VERSION`, `RENDERER_VERSION`,
  `REVIEWER_LOGIC_VERSION`, `EXTRACTOR_VERSION`, `VALIDATOR_VERSION`, check versions,
  `INHERITED_UNITS_VERSION`). A rung that seems to need one stops and reports why; the owner
  decides (`PLAN.md` §11D.2 necessity test).
- **Ask the owner only for** (a) a browser-only action that a run has proved missing (give the
  exact link and what to tick), or (b) a new class of outbound effect. Everything else you decide
  and do. Standing authority: owner directive D8 to D13 and the Cells merge delegation
  (`docs/DECISION_LOG.md`, 2026-10-14): both lanes and the issue component are proved on the seven
  `aspose-cells-foss` repositories first; the owner approved filing the system-found Cells issues;
  the executor may merge a pull request this system opened on a Cells repository when its checks
  are green, the diff equals the authorized bundle, upstream is unchanged and no maintainer
  objected, pinned with `--match-head-commit`.
- **Before every commit:** `python -m ruff check .`, `python -m ruff format --check .`,
  `python -m mypy src`, and the tests that read the files you touched. The pre-push hook (about
  40 minutes) is the last gate, not the first test. Never `--no-verify`, never force.
- **A push outlives the session only if detached.** Run `git push` through a detached process
  (PowerShell `Start-Process` of `bash` with a log file) or a background shell with the full
  timeout; two pushes were lost on 2026-10-14 when a session ended mid-hook.
- **Verify before you claim.** Pushed, merged, filed, green: only after reading the command or
  API output in this iteration. A lane's or an earlier session's report is a claim.
- Environment: work in `runs/wt/<name>` from `scripts/new_worktree.sh`; export
  `PYTHONPATH=$PWD/src`, `RP_VENV=E:/Users/prora/OneDrive/Documents/GitHub/repository-presenter/.venv`,
  `CI_TOOLS_VENV=C:/dev-tools/rp-ci-tools`; the toolchain registry defaults to
  `D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt`. `gh` authenticates through the user-level
  `GITHUB_TOKEN`; if `gh api rate_limit` fails, stop and report, never hunt for another credential.

## 1. Orient (at most five minutes)

1. `git status`, `git fetch origin`, `gh pr list --state open`, `gh run list --limit 6`: a red
   hosted run on `main` is fixed before anything else.
2. Scoreboard, by command, not memory: `gh issue list -R aspose-cells-foss/<repo> --search "<title words>"`
   for each filed handoff; `gh pr list -R aspose-cells-foss/<repo> --state all` for presenter pull
   requests; `repository-presenter status` for the counts. Print it first in the report.
3. The current rung is the first one whose "done when" is not yet true. Check it; do not assume.

## 2. The ladder

**Rung 1 — one real upstream issue, Cells-Cpp, handoff `3f1b3176`** (`std::numeric_limits`
without `<limits>`; CONFIRMED at live head `9f852d0f`; approval record expires 2026-10-19T02:16Z).
Preconditions on `origin/main`: `ops/issue_approvals/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__3f1b3176…json`
(pull request #333) and `data/registry.json` Cells-Cpp `"issues_mode": "file"` (the reset pull request).
- 1a `repository-presenter issue-readiness --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`
  must print `approvable: YES` with no write-gate blocker for `3f1b3176`; otherwise fix the
  precondition that is missing, nothing else.
- 1b `gh variable set REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED --body 1 -R babar-raza/repository-presenter`
  (a kill switch: it authorizes nothing by itself; approval records do).
- 1c `gh workflow run issues-scheduled.yml -R babar-raza/repository-presenter --ref main`, then
  `gh run watch <id>`. The file job mints an App token with `issues: write` for `aspose-cells-foss`.
  If the mint or the create fails on permission, the owner's one click is the App's installation
  settings for the `aspose-cells-foss` organization (Issues: Read and write); report it with the
  run URL and stop this rung.
- Done when: the issue is listed by `gh issue list -R aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`,
  the handoff file under `evidence/upstream-defects/` reads `FILED` with the issue URL (the
  workflow commits it; pull or fetch), and a second dispatch creates no second issue. Then one
  log entry with the URL.
- If `issue-targets` lists repositories other than Cells-Cpp: expected; the write gate refuses
  them (`dry_run`) and only approved handoffs are filed.

**Rung 2 — the other approved Cells issues** (handoffs `9bc5df82`, `b3df5761` on Cpp;
`c04f74bf`, `5dc560bf` on TypeScript; `cf626176` .NET; `83a93576` Java; `a2e2612a` Python; the
FILE rows of `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/issue-approval-table-final.csv`).
For each: `issue-readiness --repo <r>` shows CONFIRMED at the live head and the quality gate
passing; emit records with `issue-readiness --emit-approvals <scratch> --approver babar-raza
--handoff-id <id>@sha256:<digest>`; set `"issues_mode": "file"` on each of those Cells entries;
one pull request, hosted CI green, merge; dispatch; verify every URL; second dispatch creates
none. A handoff that no longer reproduces is dropped, not filed. The three text-only drafts
(U14, U16, U19) wait for rung 5.

**Rung 3 — the sandbox canary** (`docs/PROPOSAL_WAVE_RUNBOOK.md` §9; files under
`ops/sandbox-canary/`, record `ops/proposal-authorizations/babar-raza__presenter-sandbox__fa4a4f68a6d6.json`,
expires 2026-10-19T02:35Z; re-draft with `tools/canary` if lapsed). Seed the sandbox with
`tools/canary/seed.py` as the runbook says and push `seed:main` to `babar-raza/presenter-sandbox`;
dispatch `propose-sandbox.yml` with `do_propose` false; if the App cannot reach the sandbox, the
owner's one click is https://github.com/settings/installations → Repository Presenter → Configure
→ Only select repositories → add `presenter-sandbox`; then dispatch with `do_propose` true and
approve the waiting `sandbox-canary` deployment through
`gh api -X POST repos/babar-raza/repository-presenter/actions/runs/<run>/pending_deployments`
(`environment_ids`, `state=approved`). Done when `python tools/canary/canary.py verify --root .
--expect open` prints only OK and a second dispatch reports no change.

**Rung 4 — the first correction pull request, Cells-.NET** (`docs/OPERATIONS_RUNBOOK.md` §12.3).
First fix the pull-request text: `components/readme_correction/pull_request.py` (near the
"They report N failure(s) on yours" sentence) quotes checks written for generated READMEs that do
not apply to a live one; restrict it to checks that apply to a live document or drop it, update
`tests/components/readme_correction/test_pull_request.py` deliberately (no assertion deleted
without a replacement), `no_bump_check` clean. Then `correct-readme --repo` for the Cells entries,
`tools/corrections/assemble.py`, commit `corrections/<run-id>/`, the authorization record for the
exact README hash, `mode: full` for the entries with something to push (one reviewed pull
request), `propose.yml` dry-run then `do_propose`. Merge on the Cells repository only under the
delegation above. Done when merged and a second dispatch reports no change.

**Rung 5 — the rest of the Cells scope.** Cells-Cpp and Cells-Go pull requests (content), then
Java and TypeScript (diagram-only); the three text-only issues after their classes are registered
in `components/issues/classes.py` (model and schema together, a negative control each). After
rung 5 Lane L and the issue component are proved on Cells; production for all repositories is
the backlog card TC-LPD-01 / TC-IPD-01 and starts only then.

**Lane R** runs, if at all, as a separate lane: local, on frozen versions, no bump, no plan text;
its whole report is counts. It never blocks rungs 1 to 5.

## 3. Stop rules

A failed run is read from its log and its cause named in the report before anything else is
tried. Two equivalent failures: stop, diagnose, change the mechanism, never a third try. Nothing
is written outside this repository, the sandbox and the seven Cells repositories. A rung that is
blocked on the owner is reported once, with the exact link, and the next rung that does not
depend on it proceeds.

## 4. Report (end of every iteration, at most twelve lines)

Scoreboard first (issues filed, pull requests opened and merged, each with its URL;
`authorizable N/44`); the rung and its state; what was checked, what was not checked, what
remains; the one owner ask, if any; the next command.
