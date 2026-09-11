# lane-f decision log (append-only; entries in DECISION_LOG.md section 31 shape; the owner merges)

Lane: `lane-f` (project/lanes/lane-f.yaml). Prompt: project/loop-prompt-lane.md.

Lane F owns the .NET cohort candidate runs (opened 2026-09-11 so the primary can work shared-code
items only). It owns no platform module: the .NET module is shared and mature (G4-W11), so a
platform or shared-code defect is a `PROPOSAL` here and never an edit. Entries take
`DECISION_LOG.md` §31's shape — date, item, decision, alternative rejected, evidence, reversal path.

## 2026-09-11 — LANE-F-01, .NET cohort re-attempt (run 1, halted at S4 by reviewer instruction)

### F1 Ground truth: 3D-.NET's pre-S4 evidence at the un-sealed revision, measured against the 2026-09-06 row

**Decision.** Record `aspose-3d-foss/Aspose.3D-FOSS-for-.NET` at
`042a1e5f731d8fbca65e2a47a15891b2ba32b352` — the same revision the 2026-09-06 seal used and the
`f8e3bf0` un-seal deleted — as *re-attemptable with its S2/S3 evidence intact and one class better
than at seal time*, and write no disposition for it this run. A disposition recorded while S4
(`RECONCILING`) is known broken (F2) would name a failure class that is not this repository's.

**Measured 2026-09-11 08:16–08:18 UTC, lane worktree `C:\w\f01`, one provider call total.**

| | 2026-09-06 seal (G4 manifest row) | 2026-09-11 run 1 |
|---|---|---|
| revision | `042a1e5f…b352` | `042a1e5f…b352` (identical) |
| facts | 3931 | 3931 |
| public symbols | 3812 | 3812 |
| examples | 7 candidates; executed 5, failed 2 | 7 candidates; executed 6, failed 1 |
| required rows without evidence | (not recorded) | none |

- Facts stage: 3931 records — `build_test_asset` 1, `dependency` 1, `example` 7, `identity` 5,
  `inherited_unit` 70, `install_command` 1, `license` 2, `link_target` 29, `package` 3,
  `public_symbol` 3812; 3930 SUPPORTED, 0 UNRESOLVED, 1 CONTRADICTED. Facts digest
  `bdb5ae9087bcabe7d083fdcff99eba805f303d31962c88cfbcac6e5833cbc37a`; source digest
  `917c306831a06b53b148a6134798b5e4f9c0dd3cfdfe6001e8b8754afb450424` (3 files, 314 tree entries).
- The single CONTRADICTED fact is `example:003`: `Program.cs(3,41): error CS1503: Argument 2: cannot
  convert from 'Aspose.ThreeD.FileFormat' to 'System.Threading.CancellationToken'` — a genuine
  upstream compile error in the README's own fence, one example, not a task-wide blocker (rule 16).
  The second failure the 2026-09-06 row recorded is gone: one formerly-failing example now EXECUTES.
- **3D-.NET does not need `EcosystemSpec.source_install`.** The registry probe
  `nuget:Aspose.3D.FOSS` returned `SUPPORTED` via `nuget-flatcontainer-api`, and
  `install_command:dotnet` = `dotnet add package Aspose.3D.FOSS` is SUPPORTED. §28.11's census row
  ("3D .NET … NuGet not found", owner 2026-09-05) is stale for this repository; the package is
  published now. All 12 link probes RESOLVED.
- **The 2026-09-06 fabrication is provably a fabrication, and this run did not reproduce it.**
  The un-seal was caused by `independent_review` stably regenerating a `PlyReader`/`PlyWriter`
  paragraph. Neither name exists in the 3931 facts: `public_symbol:aspose.threed.formats.plyreader`
  and `…plywriter` are both absent, and no fact ID anywhere contains `plyreader` or `plywriter`.
  The only real symbol in that neighbourhood is `public_symbol:aspose.threed.formats.plyformat`.
  This run's S3 (`INVESTIGATING`) receipt names `PlyFormat` only — `Ply(Reader|Writer)` appears
  nowhere in it — and all 26 fact IDs it cites resolve to real facts, 0 unknown.

**Alternative rejected.** Re-running `present` to a verdict and dispositioning on whatever came
back. The reviewer's stop instruction is binding (loop-prompt §5, "Reviewer messages"), and with S4
returning fact IDs that name no fact, any review verdict reached through it would be evidence about
the broken stage, not about this candidate.

**Evidence.** `runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/042a1e5f…b352/`
(`preflight.json`, `facts.json`, `probes.json`, `investigation.json`, `calls.jsonl` — 1 call,
`repository_investigation`, outcome `success`, `logical_call_id` `25dcd982b086a274`; the run was
halted before its S4 call). `evidence/build/lanes/lane-f/LANE-F-01.json`. G4 manifest row for this
repository (`outcome: SEALED_THEN_UNSEALED`).

**Reversal path.** None needed — this is a measurement, not a change. If the re-attempt after the S4
fix lands a review verdict that again names `PlyReader`/`PlyWriter`, this entry is the standing
proof the paragraph is fabricated and the verdict must be rejected, not folded.

### F2 PROPOSAL — `reconciliation_schema`'s `fact_ids` pattern is unbounded and prefix-only (S4)

**Defect.** `src/repository_presenter/components/readme/reconciliation/dispositions.py:195-198`
(shared code — `reconciliation/`, not a lane-F path):

```python
dispositions["items"]["properties"]["fact_ids"]["items"] = {
    "type": "string",
    "pattern": "^(" + "|".join(kinds) + "):",
}
```

Two independent problems, both read directly off the shipped code and the prompt manifest, and both
matching the failure the reviewer reports lanes C and D measured independently this hour
(`852047a`, `3bc7999`):

1. **The pattern is prefix-only, so it admits IDs that name no fact.** It anchors the start and
   stops at the colon. The bare string `public_symbol:` — kind prefix, empty slug — satisfies it,
   as does any kind prefix plus any text. The docstring's own claim, "an ID that matches the pattern
   but names no fact is rejected by the binding guard exactly as before", is true but is the
   *expensive* rejection this schema change existed to avoid: the whole transaction is spent first.
2. **`fact_ids` has no `maxItems` and its items have no `maxLength`.** `prompts/source_reconciliation.yaml`
   types it `{"type": "array", "items": {"type": "string"}}` with no bound at either level, and the
   patch above replaces only `items`. Constrained decoding over an unbounded array of unbounded
   strings has nothing to terminate it — the runaway to the 32000-token cap.

Additionally, `pattern` is the one keyword §27.0 D1 rules out by name: "The gateway answers HTTP 400
for `pattern` in strict `json_schema`: never use `pattern`; use enums, `minItems`/`maxItems`,
`maxLength` (27.10)." The same subsection names the replacements this schema already has everywhere
else — `unit_id` is given an explicit `enum` of the batch's own unit IDs four lines below.

**Proposed shape (the primary's to land, not lane F's).** Give `fact_ids` the treatment `unit_id`
already gets in the same function: an `enum` of the packet's own fact IDs (the code knows them
exactly, which is this function's whole stated principle), plus a `maxItems`. That refuses
`public_symbol:` at decode time, bounds the array, and removes the `pattern` keyword D1 prohibits.

**Alternative rejected.** Lane F patching `dispositions.py` to unblock its own cohort. `reconciliation/`
is shared code; §2 of the lane prompt makes this a `PROPOSAL`, and the primary is landing a fix.

**Evidence.** `dispositions.py:163-205`; `prompts/source_reconciliation.yaml`
`output.schema.properties.dispositions.items.properties.fact_ids`; `packet.fact_kinds` includes
`public_symbol`; `RESEARCH_AND_GUIDELINES.md` §27.0 D1.

**Reversal path.** The primary's fix supersedes this entry; if it lands a different shape that holds,
this entry is a corroborating third measurement, not a competing proposal.

**Observed while landing this record (2026-09-11 08:53 UTC):** the primary checkout's local `HEAD`
reads `352fd35 fix(reconciliation): fact_ids decode from an enum of the packet's own IDs, never a
bare kind prefix (PHASE1/S4-REGRESSION)` — the enum shape this entry proposes — not yet on
`origin/main` (which is at `1a8fbae`). Lanes C and D landed the same measurement from their own
cohorts as PRs #32 and #33 in the meantime. This entry stands as the third independent measurement
and as .NET's own baseline for the re-attempt; it proposes nothing further.

### F3 A lane worktree's `.venv` is built from `requirements-lock.txt`, never from `pip install -e .[dev]`

**Decision.** Build the lane venv as `pip install --no-deps -r requirements-lock.txt`, then
`pip install --no-deps -e .`, then `pip install --no-deps uv==0.12.9`, and verify
`_presenter_site_manifest_hash()` equals the primary's before running `present`.

**Why.** `project/loop-prompt-lane.md` §1.3 says `.venv\Scripts\pip install -e .[dev]`. Done
literally on 2026-09-11 that resolved *newer* versions than the lock pins — `anyio 4.15.1` (lock
4.14.2), `ast-serialize 0.11.1` (0.8.0), `openai 3.13.0` (3.7.0), `ruff 0.16.7` (0.16.5),
`types-PyYAML …20260906` (…20260815) — and `_presenter_site_manifest_hash()` came out
`613b742b997a5a87…`. The primary's venv and all 8 sealed bundles read
`f4406f1b04d81ecdf2ea4e421776ef2be7f8cdc27090f395a815277a561fd411`. That hash is
`environment_dependencies()["presenter_site_manifest"]`, and a change in it "reopens EXTRACTING, the
same stage a source or fact change would" (`bundle/seal.py:179-192`). A lane sealing from the naive
venv therefore lands a candidate in an environment class of its own — instantly stale under the
primary's `status --stale`, for no reason but an unpinned install. This is the same mechanism as the
owner's 2026-09-11 11:19 "tool venv frozen for the sprint" decision, reached from the other side:
that entry forbids *changing* the primary's venv; this one says a *new* lane venv must be built to
match it.

After the lock install the two sets differed by exactly one distribution (`uv==0.12.9`, present in
the primary, not a project dependency and not in the lock); pinning it made the hash identical —
`f4406f1b…`, verified equal before any candidate work.

**Alternative rejected.** Sealing from the drifted venv and letting the environment class differ.
It costs a portfolio-wide re-open for a difference no candidate's content reflects.

**Evidence.** `requirements-lock.txt` (anyio 4.14.2, ast-serialize 0.8.0, openai 3.7.0, ruff 0.16.5);
`bundle/seal.py:157-192`; measured hashes above; `DECISION_LOG.md` 2026-09-11 11:19 venv-freeze entry.

**Reversal path.** If `pyproject.toml`'s dev extra and the lock are ever re-synced so a plain
`pip install -e .[dev]` reproduces the lock, this entry becomes redundant; until then a lane that
skips it seals into the wrong environment class.

### F4 No disposition is written for any .NET repository this run

**Decision.** LANE-F-01 stays `IN_PROGRESS`. 3D-.NET is measured (F1) but not sealed and not
dispositioned; Email-.NET, PDF-.NET and Slides-.NET were not run at all, so the G4 manifest's
existing rows for them stand unamended.

**Why.** Every one of the three remaining repositories is blocked behind a stage that is known
broken (F2): Email-.NET's unlock is a review-side fold, PDF-.NET's is a planning-side fact-ID fix,
and Slides-.NET's is the `source_install` BC-02 path — none of which can be observed through an S4
that returns fact IDs naming no fact. A failure class recorded now would be S4's, recorded against
the wrong repository, and the manifest's dispositions are read as that repository's own history.

**Alternative rejected.** Recording `BLOCKED_*` rows naming the S4 defect. It would put the same
cause in four repository rows and bury the real per-repository predicates the lane file already
carries.

**Evidence.** This run's transaction directory (1 provider call, halted before S4); the reviewer's
2026-09-11 instruction; `project/lanes/lane-f.yaml` LANE-F-01 `purpose`.

**Reversal path.** The supervisor re-spawns LANE-F-01 when the S4 fix lands; the re-attempt starts
from 3D-.NET with F1 as its pre-S4 baseline.

### F5 Recovery: the pre-push hook's own `git push` rewrote this lane's branch with fixture commits

**What happened, in full (a recovery is never silently absorbed — loop-prompt §1.1).** The first
`git push -u origin lane-f/LANE-F-01` at 2026-09-11 08:35 UTC failed its pre-push
`scripts/ci_check.sh` on `pytest`. The eight failures were all
`tests/test_version_bump_discipline.py`, all asserting "… is not tracked at HEAD". They were true:
by then `refs/heads/lane-f/LANE-F-01` no longer pointed at this lane's commit. Git exports `GIT_DIR`
into every hook environment and `GIT_DIR` outranks both cwd and `-C`, so the suite's throwaway
repository fixtures — which reach git through `core/git_safety/git.py::run_git`, which forwards
`os.environ` wholesale — operated on *this worktree* instead of their `tmp_path`. The worktree
reflog records six fixture commits (`seed`, `seed`, `initial`, `seed`, `seed`, `seed`, `placeholder`,
`Test <test@example.com>`, 08:35:31–08:37:32) walking the branch off `1f74766` and down to a
two-file tree (`LICENSE`, `README.md`); `git ls-files` reported 2 tracked files where there are 465.

**This is not a new defect.** The versioned `.githooks/pre-push` already carries lane D's
2026-09-11 diagnosis verbatim and scrubs `GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_NAMESPACE GIT_PREFIX`
before running `ci_check.sh`, naming the durable fix as `run_git` refusing to forward them. Lane F
was bitten because it branched at `692f57c`, where `.githooks/pre-push` was still at `b9ba2be`
(2026-09-09) — and `core.hooksPath` is an absolute path into the primary checkout, so which hook
text runs is decided by the primary's working copy at push time, not by the branch being pushed.
Recorded here as the second measured occurrence, on a third lane, which is the argument for the
durable `run_git` fix over the hook-side scrub: the scrub closes one caller, and any other entry
point that runs the suite under an inherited `GIT_DIR` reopens it. Lane C's PR #33 (PROPOSAL U,
merged as `1a8fbae` while this record was being written) supplies the missing half of the
mechanism from its own occurrence — `init_git_repository` asserts only `git init`'s exit status,
and a no-op re-init exits 0, so under an inherited `GIT_DIR` the fixture's `git init` silently
re-initialises the *real* repository and every later fixture command follows it there. Lane F adds
no proposal of its own on top of that; this entry is the third occurrence's evidence.

**Recovered.** `git reset --hard 1f747663048ebfad5d652ed4c681a43b22d92b68` restored the branch;
`git ls-files` is back to 465, `git status` clean, the commit's tree byte-identical (nothing was
re-created by hand). The eight version-bump failures were the corruption's symptom, not a real
red: they pass on the restored tree.

**One consequence kept, not hidden:** the same mechanism had already set `user.name Test` /
`user.email test@example.com` on this checkout before the lane's own commit was made (the worktree's
very first reflog entry, 08:10:48, is already `Test <test@example.com>`), so that commit was
mis-authored. Re-authored to the repository's own identity when the corruption was found. Every
byte of its content is unchanged.

**Alternative rejected.** Pushing with `--no-verify` to get past the failing hook. The failures
looked like a stale-version-constant complaint and would have been read as a real red by the next
reader; and bypassing the gate would have left the branch corrupted on the remote.

**Evidence.** `D:\…\.git\worktrees\f01\logs\HEAD` (13 entries; the six fixture commits and their
`Test <test@example.com>` identity); `.githooks/pre-push` (the `unset` block and its lane-D
diagnosis); `tests/test_version_bump_discipline.py:160,173`;
`src/repository_presenter/core/git_safety/git.py::run_git` (`full_env = {**os.environ, …}`).

**Reversal path.** None — a recovery record. The open follow-up is lane D's own: `run_git` stops
forwarding the git-plumbing environment variables, at which point the hook's scrub is belt-and-braces
rather than the only guard.
