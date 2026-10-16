# Ship loop — one bounded iteration (the executor's queue since 2026-10-14)

Run ONE bounded iteration of the ladder in §2, then yield. Start from the files, never from memory.
Lane R (a README from scratch, for any repository) is the primary lane (owner, 2026-10-14); it is
worth nothing until a version bump stops invalidating its candidates and acceptance is computed, so
those come first. Lane L (live-first correction) maintains the READMEs the owner's `/readme-refresh`
produced and proves the write path R reuses; `/readme-refresh` is the fallback when R fails a
repository. The issue component files system-found defects. Progress is one number, `authorizable
N/44` as the judge computes it, plus artifacts with URLs.

## 0. Rules

Read `project/loop-prompt.md` §0, §4, §5, §8 and follow them, with these substitutions:
- **Your queue is §2, in order.** Not `next_ready_items`, not the archived plan
  (`plans/archive/reseal-and-refresh/`, frozen; read a card only when a rung names it). Add no plan
  section, card, requirement or charter, except the G3-W12 cards (owner D8, 2026-10-16). One `docs/DECISION_LOG.md` entry per shipped artifact, at
  most eight lines, after it exists.
- **No governed version moves** without the necessity test in `AGENTS.md`. Until rung 3 lands, a bump
  invalidates every sealed bundle: that is the loop this ladder ends.
- **Ask the owner only for** a browser-only action a run proved missing (exact link, what to tick) or
  a new class of outbound effect. Standing authority (owner, 2026-10-14): R primary; L and issues
  proved on the seven `aspose-cells-foss` repositories; the executor may merge a pull request this
  system opened on a Cells repository when checks are green, the diff equals the authorized bundle,
  upstream is unchanged and no maintainer objected, pinned with `--match-head-commit`.
- **Before every commit:** `python -m ruff check .`, `ruff format --check .`, `mypy src`, and the tests
  that read the files you touched. The pre-push hook (about 40 minutes) is the last gate; never
  `--no-verify`, never force; run the push detached (PowerShell `Start-Process` of `bash`, log file).
- **Verify before you claim.** Pushed, merged, filed, green: only after reading the output in this
  iteration. Another session's or a lane's report is a claim.
- Environment: `runs/wt/<name>` from `scripts/new_worktree.sh`; `PYTHONPATH=$PWD/src`,
  `RP_VENV=E:/Users/prora/OneDrive/Documents/GitHub/repository-presenter/.venv`,
  `CI_TOOLS_VENV=C:/dev-tools/rp-ci-tools`, `GIT_CEILING_DIRECTORIES=C:\Users\babar` (a stray `.git` in the
  home folder makes fixture repos refuse to init and fails ~70 tests). `gh` uses the user-level `GITHUB_TOKEN`;
  if `gh api rate_limit` fails, stop and report; never hunt for a credential.

## 1. Orient (five minutes)

`git fetch origin`; `gh pr list --state open`; `gh run list --limit 6` (a red run on `main` is fixed
first); `repository-presenter status`. The current rung is the first whose "done when" is not true,
checked by command.

## 2. The ladder

1. **Hygiene.** Merge green open pull requests on their exact head (`gh pr update-branch` first);
   comment the rung that will revisit #328, #317, #233, #214 (no close); print `git worktree list`
   with merged/unmerged per branch; delete nothing. Done: no open pull request is behind `main`.
2. **One real issue, Cells-Cpp, handoff `3f1b3176`** (approval record expires 2026-10-19T02:16Z;
   needs the record from #333 and `"issues_mode": "file"` on Cells-Cpp, both on `main`).
   `repository-presenter issue-readiness --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` shows
   `approvable: YES`; `gh variable set REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED --body 1 -R
   babar-raza/repository-presenter`; `gh workflow run issues-scheduled.yml -R
   babar-raza/repository-presenter --ref main`; `gh run watch`. If the App cannot create it, the
   owner's one click is the App's installation permissions for `aspose-cells-foss` (Issues:
   read and write); report the run URL. Done: the issue is listed by `gh issue list -R
   aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, the handoff reads `FILED` with its URL, a second
   dispatch creates none.
3. **A bump never invalidates what it did not touch. DONE 2026-10-15.** On real wave-7 bundles sealed on
   `main` (Cells-Go, Note-Python) `python tools/reviewer/bump_proof/bump_proof.py --target ROOT=OWNER/NAME`
   gives `CURRENT`, and after a throwaway bump of NORMALISATION, RENDERER, REVIEWER_LOGIC, INHERITED_UNITS or
   VALIDATOR `RECHECKED_CURRENT` (evidence: `analysis/bump-proof-2026-10-15.json`). EXTRACTOR_VERSION gives
   `UNVERIFIED` (re-extraction needs the pinned clone): the one bump that always needs the necessity test.
   Re-run the command after any change to `bundle/recheck.py` or a governed file.
4. **The judge.** New `components/readme/acceptance/judge.py`: `README_STANDARD` conformance
   (`data/readme_standard`); every public claim cites an accepted fact; every material inherited unit
   has one disposition and kept text is printed; a rerun is byte-identical with zero provider calls;
   and, only when a standard live README exists, not worse than it. Typed verdict naming the failing
   clause, a fixture per clause; wired into `status` (prints `authorizable N/44` first),
   `wave-readiness` and `propose`; the LLM reviewer is advisory. Done: the cursor's
   `authorizable_candidates` equals `status`'s count.
5. **Frozen base; R where it is needed** (Lane R changes ride G3-W12's cards, `docs/investigations/14-lane-r-dependability.md`; C1 first, measure before change). Record the freeze commit. Run `tools/reviewer/reseal_wave`
   on repositories without a standard live README (`data/readme_standard/survey.json`: `readme:
   false`, `glance_form: null` or `banner: false`), then the judge. A failure is repaired outside the
   governed files, or with a necessity finding, or handed to `/readme-refresh`. Done: every such
   repository has a judge verdict, counts in the log.
6. **The write path (Lane L).** Sandbox canary (`docs/PROPOSAL_WAVE_RUNBOOK.md` §9; record expires
   2026-10-19T02:35Z): seed, dry-run, `do_propose`, approve the waiting `sandbox-canary` deployment
   via `gh api -X POST repos/babar-raza/repository-presenter/actions/runs/<run>/pending_deployments`,
   `python tools/canary/canary.py verify --root . --expect open`. Then Cells-.NET: fix the pull-request
   text first (`readme_correction/pull_request.py` quotes Lane R checks that do not apply to a live
   README), commit `corrections/<run>`, the authorization record, `mode: full`, `propose.yml`
   dry-run then `do_propose`. Done: the pull request is open, its diff equals the bundle, a second
   dispatch reports no change.
7. **R proposes.** The first rung-5 repository with a passing verdict goes through the rung-6 path.
   Done: its pull request is open and a rerun is a no-op. Then R continues repository by repository,
   L maintains, issues continue per handoff.

## 3. Stop rules and report

A failed run is read from its log and its cause named before anything else is tried; two equivalent
failures stop the rung. Write only to this repository, the sandbox and the seven Cells repositories.
A rung blocked on the owner is reported once with the exact link and the next independent rung
proceeds. Report (at most twelve lines): `authorizable N/44` first; artifacts with URLs; the rung and
its state; checked, not checked, remaining; the one owner ask, if any; the next command.
