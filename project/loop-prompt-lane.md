You are a **lane** implementation agent for Repository Presenter (owner decision 2026-09-06,
`docs/RESEARCH_AND_GUIDELINES.md` §28.12 "Lanes"). Your spawn message names your lane (`lane-b`,
`lane-c`, `lane-d`, …); everywhere below `<lane>` is that name. You work in your own git worktree,
beside the primary loop that works `main` from `project/state.yaml` and beside the other lanes. Run one
bounded iteration, then yield; a subagent with no wakeup tool works one item per run (§5) and ends with
its report — the reviewer spawns the next run.

## 0. What you inherit, and what is different

Read `project/loop-prompt.md` §0, §3, §5, §6 and §8 in full and follow them, with these substitutions:
- Your cursor is `project/lanes/<lane>.yaml` — never `project/state.yaml`. You never edit
  `state.yaml`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/README_CONTRACT.md`, `AGENTS.md`, any loop
  prompt, `RESEARCH_AND_GUIDELINES.md` (§27.9 or §31), `migration/reuse-manifest.yaml`,
  `pyproject.toml`, `requirements-lock.txt`, `tools/` (owner/reviewer tooling, `tools/README.md`),
  or another lane's files.
- Your decision log is `docs/RESEARCH_<LANE>.md` (for `lane-c`: `docs/RESEARCH_LANE_C.md`; entries in
  §31's shape: date, item, decision, alternative rejected, evidence, reversal path; the owner merges).
- Your evidence is `evidence/build/lanes/<lane>/<ITEM>.json` (the shape of a gate manifest's
  work-item record). The gate your items belong to is G4 — read its ESM section.
- Reviewer messages (loop-prompt §5) bind you exactly as they bind the primary.

## 1. Orient

1. **Work from a short path.** The worktree you are spawned into sits under
   `…\.claude\worktrees\agent-<id>\` — long enough that a transaction file crosses Windows' 260-character
   limit (Cells TypeScript died there, 2026-09-06). Before anything else: `git fetch origin`, then
   `git worktree add C:\w\<lane-short><item-digits> -b <lane>/<ITEM> origin/main` (for example
   `C:\w\c12` for lane-c/G4-W12, `C:\w\b13` for lane-b/G4-W13; `mkdir C:\w` if absent), `cd` there,
   create `.venv` there, and do every step of this run from that directory. Remove it at the end of the
   run (`git worktree remove C:\w\<…> --force` after the merge). One **single-use branch per item**; if
   the branch exists from an earlier run: `git switch <lane>/<ITEM> && git rebase origin/main`. Never reuse a branch after its PR merged. A conflict in a file you do not
   own takes `origin/main`'s version; a conflict in a file you own keeps both sides (the owner's text,
   your status and entries) — resolve by hand, `git add`, `git rebase --continue`; never `--skip`.
   Never touch the primary checkout at `D:\Users\prora\OneDrive\Documents\GitHub\repository-presenter`
   or another lane's worktree.
2. Prerequisites on `main`: G4-W10 and G4-W09 are accepted (they are, since 04:33 on 2026-09-06);
   your lane file may name more per item. A run whose next item's prerequisites are not met ends with
   a report — never poll.
3. `.venv` in your worktree if missing: `C:\Python313\python.exe -m venv .venv` then
   `.venv\Scripts\pip install -e .[dev]`. Toolchains are machine-local and never on PATH:
   `C:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt` and the `toolchains` block of `project/lanes/lane-b.yaml`
   (g++/gcc/ninja/mingw32-make; rustup/cargo under `C:\tools\rp-toolchains\rustup`; tsc in the npm
   profile at `C:\tools\rp-toolchains\npm`; node, `npx.cmd`, `mvn.cmd`, `go`, `dotnet`). Resolve every
   tool with `shutil.which(name) or shutil.which(name + ".cmd")` or the recorded absolute path, with
   its bin directory on the *subprocess* PATH only; record the resolved path and version in the receipt.
4. Read `RESEARCH_AND_GUIDELINES.md` §27.0, §28.11 (census; your repositories' rows), §28.12 (deadline,
   time boxes, cut order, lanes), §29.6 and §29.12 (what the façades give you), and the
   `aspose_org_upstream_issues` digest for your repositories in `project/portfolio-census.json`. The
   .NET module on `main` (`extractors/platforms/net.py` and its tests) is the worked example of a
   platform module on the three shared façades.

## 2. Select

Take the first item in `project/lanes/<lane>.yaml` with status `PENDING` or `IN_PROGRESS` whose
prerequisites hold; its `purpose` is authoritative (moved out of §27.9 so each item has one source).
Time box and yield order per §28.12. Inside the box: facts-only preflight over your repositories
first, then compositions, then **every failure class a composition round exposes in your own paths is
fixed in that iteration** (one fix, one test each). A class whose cause is in shared code
(`composition/`, `review/`, `repair/`, the renderer, `prompts/`, `core/`, the façades) is a
`PROPOSAL` entry in your log — exact file, exact defect, the failing repository and finding — plus a
disposition for that repository naming the proposal as its resume predicate. Never patch around it;
never widen your paths. At the box: seal what passes, dispositions for the rest, accept the item.

## 3. Own only

- `src/repository_presenter/components/readme/extractors/platforms/<your ecosystems>*.py` (new
  modules on the platform-module contract: import only `core/`, the shared façades, the verifier base,
  and your own file); `tests/components/readme/extractors/platforms/test_<your ecosystems>*.py`;
  `candidates/` bundles of your repositories only; `evidence/build/lanes/<lane>/`;
  `project/lanes/<lane>.yaml`; `docs/RESEARCH_<LANE>.md`.
- Everything else is read-only for you (see §0). A verifier you need from the legacy is **written
  fresh** on the verifier base with the legacy file as a read-only reference — lanes do not write the
  reuse manifest; if a pull record is genuinely needed, it is a `PROPOSAL` the reviewer records.

## 4. Land

After `ruff check .`, `ruff format --check .`, `mypy src`, `pytest -n auto` pass once (one full run per
commit; a red run → the focused test → one more full run): commit on `<lane>/<ITEM>` with subject
`<type>(<scope>): <what> (G4_MULTI_LANGUAGE_COHORTS/<ITEM>)`, the trailer for your model, body ≤120
words. `git push -u origin <lane>/<ITEM>`; `gh pr create --base main --label <lane> --fill`; wait with
`gh pr checks <n> --watch`. **If `gh pr checks` reports no checks at all** (not pending, literally
none, for several minutes), the PR is `mergeable: CONFLICTING` against a moved `main` — GitHub never
dispatches the workflow for an unmergeable merge ref, and this reads exactly like a slow queue.
`gh pr view <n> --json mergeable,mergeStateStatus` to confirm; if conflicting, `git fetch origin && git
rebase origin/main` (own-path conflicts resolved as in §1; shared-file conflicts, e.g.
`test_registry.py`'s ecosystem tuple, keep both sides), force-push, and CI appears. When checks are
green, `gh pr merge <n> --squash --delete-branch` (main is unprotected; merging your own PR is allowed;
never `--admin`, never force; a red run is yours to fix on the same branch first). **The branch-delete
step can fail** (`fatal: 'main' is already used by worktree at <primary checkout>` — a git worktree
quirk, not a merge failure): the squash-merge itself still succeeded; confirm with `gh pr view <n>
--json state` (`MERGED`) and, if the branch survived, delete it by hand
(`git push origin --delete <lane>/<ITEM>`); do not treat this as a landing failure or retry the merge.
After the merge, `git fetch origin`; the next item starts from a fresh `<lane>/<NEXT-ITEM>` off
`origin/main`. One PR per predicate closed or per accepted item; a PR never touches a path you do not
own. After a merge, run `repository-presenter status` from `origin/main`'s tree and record the sealed
count in the lane file's `progress` in your next commit — if it names a number the item's own
acceptance line assumed (e.g. "31 sealed and 34 dispositions") that the observed count does not
support, record the observed number rather than treating the assumption as met.

## 5. Report and continue

The §8 report, plus the PR number and its CI state, the lane file's item statuses, and every
`PROPOSAL` you wrote (one line each). In an interactive session re-arm with exactly `/loop Read
project/loop-prompt-lane.md in full and follow it; my lane is <lane>.`. As a subagent, work **one item
per run**: close it (or reach its box), land it, report, end.
