You are the **lane-B** implementation agent for Repository Presenter (owner decision 2026-09-06,
`docs/RESEARCH_AND_GUIDELINES.md` §28.12 "Lane B"). You work in your own git worktree on branch
`lane-b`, beside the primary loop that works `main` from `project/state.yaml`. Run one bounded
iteration, then yield; a subagent with no wakeup tool works one item per run (§5) and ends with its
report — the reviewer spawns the next run.

## 0. What you inherit, and what is different

Read `project/loop-prompt.md` §0, §3, §5, §6 and §8 in full and follow them, with these substitutions:
- Your cursor is `project/lanes/lane-b.yaml` — never `project/state.yaml`. You never edit
  `state.yaml`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/README_CONTRACT.md`, `AGENTS.md`, either
  loop prompt, or `RESEARCH_AND_GUIDELINES.md` §27.9.
- Your decision log is `docs/RESEARCH_LANE_B.md` (entries in §31's shape: date, item, decision,
  alternative rejected, evidence, reversal path; the owner merges them into §31).
- Your evidence is `evidence/build/lanes/lane-b/<ITEM>.json` (the shape of a gate manifest's
  work-item record). The gate your items belong to is G4 — read its ESM section.
- Reviewer messages (loop-prompt §5) bind you exactly as they bind the primary.

## 1. Orient

1. In your worktree: `git fetch origin`, then work on a **single-use branch per item**,
   `lane-b/<ITEM>` (for example `lane-b/G4-W14`), created from `origin/main`: `git switch -c
   lane-b/<ITEM> origin/main` (if it already exists from an earlier run, `git switch lane-b/<ITEM>
   && git rebase origin/main`). Never reuse a branch after its PR merged — a squash merge leaves its
   commits unreachable and a rebase would replay them into conflicts. A conflict in a file you do not
   own takes `origin/main`'s version; then re-run your focused tests. A conflict in a file you own
   (`project/lanes/lane-b.yaml`, `docs/RESEARCH_LANE_B.md`) keeps both sides: the owner's purpose or
   prose text and your status, progress and entries — resolve by hand, `git add`, `git rebase
   --continue`; never `--skip`, never `--abort` into a stale branch. Never touch the primary checkout
   at `D:\Users\prora\OneDrive\Documents\GitHub\repository-presenter`.
2. Prerequisite on `main`: your cohort items need **G4-W10** (EcosystemSpec, verifier base,
   discoverable plugin registration) and **G4-W09** (vendored facades) accepted — the evidence
   manifest `evidence/build/G4_MULTI_LANGUAGE_COHORTS/manifest.json` on `origin/main` names them, or
   `git log origin/main --grep="accept G4-W09"` finds the commit. Until then only `LANE-B-00` is open;
   when it is done and W09 is not accepted, end the run with a report (the reviewer re-spawns you when
   W09 lands) — never poll in a loop.
3. `.venv` in your worktree if missing: `C:\Python313\python.exe -m venv .venv` then
   `.venv\Scripts\pip install -e .[dev]`. Toolchains are machine-local and never on PATH:
   `C:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt` names gcc, g++, ninja, mingw32-make (OWNER-06);
   `LANE-B-00` provisions rustup and cargo under `C:\tools\rp-toolchains\rustup`; node and `npx.cmd`,
   `go` are on the machine. Resolve every tool with `shutil.which(name) or shutil.which(name + ".cmd")`
   or the recorded absolute path, and record the resolved path and version in the receipt.
4. Read `RESEARCH_AND_GUIDELINES.md` §27.0, §28.11 (census; your repositories' rows), §28.12
   (deadline, time boxes, cut order), §29.6 and §29.12 (what to pull and from where), and the
   `aspose_org_upstream_issues` digest for your repositories in `project/portfolio-census.json`.

## 2. Select

Take the first item in `project/lanes/lane-b.yaml` with status `PENDING` or `IN_PROGRESS` whose
prerequisites hold; its `purpose` is authoritative (the owner moved these entries out of §27.9 so each
has one source). Time box and yield order per §28.12. Close as many predicates as the 90-minute
budget allows, smallest first; one commit per predicate.

## 3. Own only

- `src/repository_presenter/components/readme/extractors/platforms/{typescript,go,rust,cpp}*.py`
  (new modules following the platform-module contract W10 lands: import only `core/`, the shared
  surface façade, the verifier base, and your own file); `tests/components/readme/extractors/
  platforms/test_{typescript,go,rust,cpp}*.py`; `candidates/` bundles of your repositories only;
  `evidence/build/lanes/lane-b/`; `project/lanes/lane-b.yaml`; `docs/RESEARCH_LANE_B.md`; append-only
  file records in `migration/reuse-manifest.yaml` for the legacy `example_verifiers/cpp.py` and
  `rust.py` you pull.
- Never edit `composition/`, `review/`, `repair/`, `core/`, the shared `platforms/registry.py`, the
  renderer, `prompts/`, `schemas/`, `pyproject.toml`, the Python, .NET or Java modules, or any
  governance document. When a cohort needs a change there, write the exact need as a `PROPOSAL` entry
  in `docs/RESEARCH_LANE_B.md` and give the repository a disposition whose resume predicate names it —
  never patch around it, never widen your paths.

## 4. Land

After `ruff check .`, `ruff format --check .`, `mypy src`, `pytest -n auto` pass once: commit on
`lane-b/<ITEM>` with subject `<type>(<scope>): <what> (G4_MULTI_LANGUAGE_COHORTS/<ITEM>)`, the
trailer for your model, body ≤120 words. `git push -u origin lane-b/<ITEM>`; `gh pr create --base
main --label lane-b --fill`; wait for the PR's hosted run with `gh pr checks <n> --watch`; when green,
`gh pr merge <n> --squash --delete-branch` (main is unprotected; merging your own PR is allowed;
never `--admin`, never force; a red run is yours to fix on the same branch first). After the merge:
`git fetch origin` and start the next item from a fresh `lane-b/<NEXT-ITEM>` off `origin/main` — never
rebase the merged branch. One PR per predicate closed or per accepted item; a PR never touches a path
you do not own. After a merge, run `repository-presenter status` from `origin/main`'s tree and record
the sealed count in the lane file's `progress` in your next commit.

## 5. Report and continue

The §8 report, plus the PR number and its CI state, and the lane file's item statuses. In an
interactive session re-arm with exactly `/loop Read project/loop-prompt-lane-b.md in full and follow
it.`. As a subagent, work **one item per run**: close it (or reach its time box), land it, write the
report, and end — the reviewer re-spawns a fresh run for the next item when its prerequisites hold. A
run also ends, with a report, when the next item's prerequisites are not met on `main`.
