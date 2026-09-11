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

## 2026-09-11 — LANE-F-01, .NET cohort re-attempt (run 2, after the S4 fix landed)

Lane-F entry numbering continues F1–F5 above. These are *lane* entries; the sprint item
`PHASE1/F6` cited throughout this file is a different namespace and is always written with its
`PHASE1/` prefix.

### F6 Correction to F3 — the lock alone does not reproduce the primary's venv

**Decision.** F3's recipe is incomplete and is corrected here rather than amended in place. The
complete recipe is: `pip install --no-deps -r requirements-lock.txt`, then `pip install --no-deps
-e .`, then `pip install --no-deps uv==0.12.9 pytest-xdist==3.8.0 execnet==2.1.2 pip==24.3.1`, and
**never** `pip install --upgrade pip`.

**Why.** Built exactly as F3 prescribes on 2026-09-11, `_presenter_site_manifest_hash()` came out
`688c606066a7dd626d80f4502d825d4928a14d72ca19f6297c55410c91f7413c`, not `f4406f1b…`. The package
sets differed by exactly three distributions: `pytest-xdist==3.8.0` and `execnet==2.1.2` present in
the primary and absent here, and `pip` at `26.2.1` against the primary's `24.3.1`. The first two are
absent because `requirements-lock.txt`, although compiled `--extra dev`, predates `pytest-xdist`
entering `pyproject.toml`'s dev extra — the lock contains neither it nor its `execnet` dependency,
so a `--no-deps` lock install cannot produce them. The third is self-inflicted: `pip` is itself a
distribution, so upgrading it moves the very hash being matched. After pinning all three the hash
was `f4406f1b04d81ecdf2ea4e421776ef2be7f8cdc27090f395a815277a561fd411`, verified equal to the
primary's and to all 8 sealed bundles before any candidate work.

**Alternative rejected.** Editing F3 in place. A correction to a standing fact gets its own entry
(loop-prompt §5), or every reader who already acted on F3 misses it.

**Evidence.** Measured hashes above; `requirements-lock.txt` (no `xdist`/`execnet` entry);
`pyproject.toml:30-34` (`dev = [… "pytest-xdist>=3.6"]`); `bundle/seal.py:157-192`.

**Reversal path.** Re-compiling the lock from the current `pyproject.toml` would fold the first two
pins back in; the `pip` rule stands regardless.

### F7 3D-.NET run 2: reached S9 (VALIDATING), blocked by BC-07; dispositioned, not sealed

**Decision.** `aspose-3d-foss/Aspose.3D-FOSS-for-.NET` is dispositioned `BLOCKED_VALIDATION (BC-07)`,
not sealed. Its resume predicate is F8 (BC-07's heading model), with F9 as a second, independent
predicate for BC-02.

**Measured 2026-09-11, worktree `C:\w\f02`; 17 provider-call records, 16 `success` and 1
`response_invalid`, spanning 09:28:27–09:36:08 UTC.** The S4 fix
(`352fd35`) works: `source_reconciliation` returned `success` twice, 70 dispositions over 70
inherited units, **128 fact IDs cited, 57 distinct, 0 unknown, 0 bare kind-prefixes**. Run 1's
blocker is gone and the run advanced five stages further, to S9. The facts stage reproduced run 1
byte-for-byte on its second attempt — 3931 records, digest `bdb5ae90…cbc37a` (see F9 for the first
attempt). Composition produced 83 units across 9 sections and a 184-visible-line README.

`validation.json`: **pass 7, fail 2, pending 2**.

- **BC-07 FAIL at COMPOSING** — `heading '### ThreeD.Property' is not a shell heading in title
  case`. Cause in shared code, diagnosed in F8. `targeted_repair` recorded it `unrepairable`,
  reason `no failing check names an LLM-owned section`: content revision cannot fix it.
- **BC-02 FAIL at EXTRACTING** — `install_command:dotnet is UNRESOLVED: package registry: nuget
  could not be read`. Not a fact about this repository: the package **is** published. Cause in
  shared code, diagnosed in F9. `unrepairable`, reason `EXTRACTING is not repairable by revision`.
- BC-10 and BC-11 never ran (`PENDING`, judged at S10/S12), so **this run did not observe an
  independent review verdict at all.** The 2026-09-06 `PlyReader`/`PlyWriter` question F1 exists to
  settle is still open; it cannot be answered until a run reaches S10.

**Alternative rejected.** Re-running to get past BC-02. BC-02's reading is transient and a re-run
would very likely clear it, but BC-07 is deterministic and would fail the identical bytes again, so
the re-run would spend another ~14 provider calls and still not seal. Also rejected: choosing a
different API hub to dodge the heading. The hub set is the planner's own choice from a schema enum,
steering it is not a lane-F path, and dodging a blocking check is exactly the forced seal §2 forbids.

**Evidence.** `runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/042a1e5f…b352/`
(`calls.jsonl` 14 calls, `dispositions.json`, `plan.json`, `content_units.json`, `README.md`,
`validation.json`, `repairs.json`); `evidence/build/lanes/lane-f/LANE-F-01.json`.

**Reversal path.** When F8 lands, re-run this repository first; F1 and this entry are its baseline.

### F8 PROPOSAL — BC-07 re-implements the renderer's heading model and rejects a heading the contract requires

**Defect.** `src/repository_presenter/components/readme/validation/registry.py:856-869` (shared
code — `validation/`, not a lane-F path). BC-07 exempts a level-three API-reference heading only
when its text is in `topics`:

```python
topics = {fact.value.rsplit(".", 1)[-1] for fact in candidate.facts.by_kind("public_symbol") ...}
...
if level == 3 and line in api_lines and text in topics:
    continue
```

`topics` is the bare final dotted segment of every verified symbol. The renderer does **not** name
hubs that way. `composition/renderer.py:430-447` (`_table_names`) gives each type "its final
segment, or the shortest dotted suffix that tells it apart when two verified types share that
segment (README_CONTRACT.md row 14 …, under names a visitor can import)", and `renderer.py:481`
emits `### {names.get(symbol.value, …)}`. So the two are independent models of one thing, and they
drift on exactly the names `_table_names` disambiguates.

**Measured on 3D-.NET.** Of 293 verified types, two share the final segment `Property` —
`Aspose.ThreeD.Property` and `Aspose.ThreeD.Formats.GLTF.Property` — so `_table_names` correctly
yields `ThreeD.Property` and `GLTF.Property`. The plan made `Aspose.ThreeD.Property` an API hub, the
renderer emitted `### ThreeD.Property` as row 14 requires, and BC-07 failed it because
`ThreeD.Property` is not in `topics` (which holds only `Property`). The renderer is right and the
check is wrong. This is not repository-specific: any surface with two same-named types in different
namespaces hits it, which is ordinary in large .NET and Java surfaces.

**Proposed shape (the primary's to land).** BC-07 computes its allowed hub headings with the
renderer's own `_table_names()` over the same `(classes, enums)` list `renderer.py:462` uses,
instead of re-deriving a bare-suffix set — the principle already stated at `renderer.py:470-471`
("one answer, not two that can independently drift") and at `reconciliation/dispositions.py:164-166`
("one function, so the packet and the schema's citable set can never drift apart"). Mutation test: a
facts fixture with two verified classes sharing a final segment, one of them a hub — BC-07 passes on
the rendered heading, and still fails on a genuinely non-shell heading.

**Alternative rejected.** Lane F patching `validation/registry.py`. `validation/` is shared code;
lane prompt §2 makes this a `PROPOSAL`.

**Evidence.** `validation/registry.py:856-869`; `composition/renderer.py:430-447,462,481`;
3D-.NET `validation.json` BC-07 detail and `repairs.json` (`unrepairable`, `no failing check names
an LLM-owned section`); the two colliding symbols measured above.

**Reversal path.** If the owner rules that a disambiguated hub heading should not be emitted at all,
the fix belongs in the renderer instead and this entry names the wrong side; the drift itself is the
defect either way.

### F9 PROPOSAL — the shared registry façade never retries, so one timeout fails BC-02 on a published package

**Defect.** `src/repository_presenter/components/readme/extractors/surface/registry.py:103-108`
(shared façade). `observe()` calls `publication_probe.probe_publication(...)` exactly once. There is
no retry there, and none inside the vendored probe (`_vendor/aspose_extraction/publication_probe.py`
has only a 10-second `timeout`; no adapter under `package_registries/` retries).

`core/retry.py:40-42` already declares the policy this call wants —
`"package_registry": RetryPolicy(max_attempts=3, initial_seconds=1, maximum_seconds=20)` — and
`run_with_retry("package_registry", …)` is used at
`extractors/platforms/python_registry.py:123`. **That is the Python platform's own path.** Every
other ecosystem reaches its registry through the shared façade, which never uses the policy. So
`python` probes three times with backoff and `net`, `java`, `typescript`, `go` and `rust` probe once.

**Measured 2026-09-11, whole cohort — this is a majority failure rate, not an unlucky run.** Ten
nuget readings were observed in `C:\w\f02` over this run; **five could not be read**:

| reading | result |
|---|---|
| 3D-.NET facts-only #1 | could not be read → UNRESOLVED |
| 3D-.NET facts-only #2 | found on nuget → SUPPORTED |
| 3D-.NET `present` (full run) | could not be read → UNRESOLVED → **BC-02 FAIL** |
| Email-.NET facts-only | found on nuget → SUPPORTED |
| Email-.NET `present` (full run) | could not be read → UNRESOLVED |
| PDF-.NET facts-only | could not be read → UNRESOLVED |
| Slides-.NET facts-only | found on nuget → SUPPORTED |
| 3 direct `httpx` requests to the 3D URL, back to back | 1 `ConnectTimeout`, 2 × `HTTP 200` |

Every one of those packages is published — the successful readings and the two direct `HTTP 200
{"versions":["26.1.0"]}` responses prove it. An unreadable probe gives `install_command:<eco>`
polarity `UNRESOLVED` with evidence `package registry: nuget could not be read`, which fails
**BC-02 at EXTRACTING**; `repairs.json` records it `unrepairable`, `EXTRACTING is not repairable by
revision`, so the run cannot seal. At an observed 4-in-7 failure rate per extraction, a .NET
candidate reaching a seal is close to a coin toss on this probe alone, independently of anything
about the repository.

The reproducibility cost is separate from the blocking cost: the unread probe changes the facts
digest (`32f5d319…` against the correct `bdb5ae90…cbc37a`), and facts feed
`upstream_dependencies()`, so a bundle sealed under the unlucky reading reopens EXTRACTING
(`bundle/seal.py:179-192`).

**Proposed shape (the primary's to land).** Wrap the `probe_publication` call in
`run_with_retry("package_registry", …)`, raising `RetryableOperationError` when the reading comes
back unreadable (`published is None`), exactly as `python_registry.py:123` already does. Mutation
test: a fetch stub that times out once and then answers 200 yields `published=True`; one that always
fails still yields `published=None`, so "we could not check" never becomes "we checked and it is
false" (§29.6 E5 is preserved, not weakened).

**Alternative rejected.** Treating an UNRESOLVED registry reading as admissible for a
registry-having ecosystem. `evidence/facts/extract.py:64-70` rules that out by name and is right to:
the fix belongs at the probe, not at the admission gate. Also rejected: lane F patching the façade —
`extractors/surface/` is shared (lane prompt §2, §3).

**Evidence.** `extractors/surface/registry.py:77-118`; `core/retry.py:38-45`;
`extractors/platforms/python_registry.py:74,123`; 3D-.NET `validation.json` BC-02 detail,
`repairs.json`, and the two facts digests above; the ten readings tabulated above, each from its
repository's `facts.json` `install_command:dotnet` evidence or from the direct request.

**Priority note.** Of everything this lane measured, this is the one defect that blocks candidates
across every non-Python cohort rather than one repository: lanes B (C++ has no registry, so it is
spared), C (maven), D (go\_modules), and this lane (nuget) all reach their registry through this
façade. It is also the cheapest to fix — one `run_with_retry` wrapper around an existing, already
declared policy.

**Reversal path.** If retrying proves to mask a genuine registry outage, lower `max_attempts`; the
asymmetry between Python and every other ecosystem is the defect regardless of the number chosen.

### F10 PROPOSAL — `presentation_planning`'s four `fact_ids` arrays carry no enum (arrival item 40's class, at S5)

**Defect.** `prompts/presentation_planning.yaml` (version 11) types `fact_ids` under
`core_capabilities`, `api_hubs`, `material_limitations` and `deviations` all as
`{"type": "array", "items": {"type": "string"}}` — no `enum`, no `maxItems`, no `maxLength`.
`composition/planning.py::planning_schema()` specialises `section_id`, `link_fact_id`,
`symbol_fact_id` and the four example-ID fields with enums built from `bounded_records()`, and
leaves all four `fact_ids` arrays untouched.

**Measured on 3D-.NET, S5 attempt 1 (`call_id …-response_invalid-20260911T093129451-0005`).** The
job returned 11 invented IDs — `format:fbx`, `format:gltf`, `format:obj`, `format:stl`,
`format:collada`, `format:u3d`, `format:3mf`, `format:rvm`, `format:ply`, `format:amf`,
`format:html5` — and `core/llm/binding.py:162` rejected the whole transaction after it was spent.
Attempt 2 succeeded, so on this repository the cost was one wasted S5 call.

**On Email-.NET it cost the entire run.** The same defect fired again at S5 attempt 1 with
`format:msg`, `format:eml`, `format:cfb` — that repository likewise has **0** `format` facts.
Attempt 2 then failed for an unrelated, self-inflicted reason (`at_a_glance is included, so its
formats and capabilities are given`: the plan listed `at_a_glance` among its included sections and
set the object to `null`, which `planning.py:431-433` refuses). The retry budget is two, so
`present` aborted at S5 with `presentation_planning: output rejected twice` and the repository
never reached composition. Had the enum refused `format:msg` at decode, attempt 1 would not have
been spent on an impossible citation and the run would still have had a good attempt in hand.
That both repositories reached for invented `format:*` IDs is itself the signal: the .NET extractor
emits no `format` facts at all, the packet shows none, and nothing in the schema says so.

Two details make this the same class arrival item 40 fixed at the reconciliation site, not a
near-miss. `format` **is** a member of `core.facts.FACT_KINDS`, and this repository has **0**
`format` facts — so item 40's original `^(<kinds>):` prefix pattern would have *admitted* all 11,
and only an enum of the packet's own IDs refuses them. That is exactly `352fd35`'s argument, one
stage earlier. And the fix is cheap here: planning's own citable set for this repository is 85
records, 2,507 bytes of IDs (`bounded_records(facts, kinds)`, the packet's own `facts` field).

**Proposed shape (the primary's to land).** Give the four `fact_ids` arrays an `enum` of the
planning packet's own fact IDs plus a `maxItems`, in `planning_schema()`, beside the enums it
already builds. Mutation test: a planner output citing a well-formed but unshown ID is refused at
decode rather than at `binding_errors`.

**Alternative rejected.** Leaving it, since the binding guard already catches it. That guard is the
*expensive* rejection the enum work exists to avoid — F2 made the same argument for S4 and the
primary accepted it.

**Evidence.** `prompts/presentation_planning.yaml` (`output.schema.properties.*.items.properties.
fact_ids`); `composition/planning.py:188-221`; `core/llm/binding.py:149-168`; the `rejection` array
of the call record above; `core.facts.FACT_KINDS`.

**Reversal path.** Superseded if the owner instead removes `format` and other never-extracted kinds
from `FACT_KINDS`, which would make the prefix shape sufficient — but the unbounded array would
remain.

### F11 Lane E's proposal E3 does not materialise at either enum site on 3D-.NET (measured)

**Decision.** Record E3 as **not reproduced here**, with the numbers, rather than as a risk carried
forward. No S4 or S5 call in this run returned HTTP 400; every one of the 14 calls has
`http_status: 200`.

**Why the surface size did not drive the enum size.** 3D-.NET has 3812 `public_symbol` facts, but
neither enum is built from that number:

| site | bound that actually binds | entries | JSON bytes |
|---|---|---|---|
| `reconciliation_schema` `fact_ids` | `symbol_kinds=DECLARED_SYMBOL_KINDS` | 352 | 16,713 |
| `planning_schema` `symbol_fact_id` | `symbol_max_depth=3` | 39 | 1,603 |

Of the 3812 symbols, 3508 are `method` and only 304 are of a declared kind (class 239, enum 54,
module 11), so `DECLARED_SYMBOL_KINDS` cuts the reconciliation enum to 352 packet records; the
per-batch enum adds only that batch's own inherited units (70 across 2 batches) and the
investigation's 26 cited IDs, most already shown. `SYMBOL_CAP` (6000) never binds at either site
for this repository. Taskcard H's confirmed 400 was `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` at
24,830 symbols and ~460,256 estimated enum tokens; `planning.py:189-194` already carries that fix.

**What this does not say.** It does not clear E3 for the portfolio. Within lane F alone,
`Aspose.PDF-FOSS-for-.NET` has 12,270 public symbols — 3.2× this repository — and is the cohort's
real test of the bound; `Aspose.Words-FOSS-for-.NET` has 6,638. 3D-.NET was not the largest surface
in flight, only the first attempted.

**Alternative rejected.** Reporting E3 as "did not fire" without the measurement. A negative result
with no number cannot tell a bounded enum from a lucky one.

**Evidence.** `runs/transactions/…/042a1e5f…b352/calls.jsonl` (14 calls, all `http_status` 200);
`core/facts.py::bounded_records` (`SYMBOL_CAP` 6000, `SYMBOL_MAX_DEPTH` 3);
`reconciliation/dispositions.py:163-171`; `composition/planning.py:189-214`; the counts above,
measured from this run's `facts.json`.

**Reversal path.** None — a measurement. If PDF-.NET returns HTTP 400 at either site, that is E3
materialising and this table is the contrast that localises it.

### F12 The cohort's facts-only preflight: two repositories' recorded blockers no longer exist

**Decision.** Record the .NET cohort's facts-only readings (lane prompt §2 — "facts-only preflight
over your repositories first") and correct two stale predicates from them:
`Aspose.Slides-FOSS-for-.NET`'s BC-02 blocker **is gone**, and `Aspose.PDF-FOSS-for-.NET` carries
34 instances of F8's defect.

**Measured 2026-09-11, worktree `C:\w\f02`, zero provider calls; `preflight.json` written at
09:41:31Z (Email), 09:50:45Z (PDF) and 09:58:32Z (Slides).**

| repository | revision | facts | S / U / C | examples | verified types | F8 collisions |
|---|---|---|---|---|---|---|
| Email-.NET | `59125b47…48eb7` | 341 | 341 / 0 / 0 | 4 of 4 EXECUTED | 29 | **0** |
| PDF-.NET | `b7172877…2406b` | 12,580 | 12,578 / 1 / 1 | 11 of 12 | 899 | **34** |
| Slides-.NET | `9f2d8710…62ce5` | 2,734 | 2,733 / 0 / 1 | 8 of 9 | 264 | **0** |

- **Slides-.NET's BC-02 disposition is stale.** The G4 manifest row and this lane file both record
  it `BLOCKED_VALIDATION (BC-02)` because the package was "not on NuGet, a CONCLUSIVE
  CONTRADICTED", and name `EcosystemSpec.source_install` (arrival item 10) as its unlock. That is no
  longer the repository's state: `install_command:dotnet` now reads **SUPPORTED**, evidence
  `package registry: found on nuget`, for `dotnet add package Aspose.Slides.FOSS`. It therefore
  needs no `source_install` path at all. Upstream also moved — the manifest row's revision
  `622cd5ed…29c6d85` is gone; this reading is at `9f2d8710…5b762ce5` — and its examples went from
  "executed 1, failed 8" to **8 of 9 EXECUTED**, its one CONTRADICTED fact being `example:002`
  (`CSC : error CS5001: Program does not contain a static 'Main' method`, genuine upstream).
- **PDF-.NET is F8's worst case in this cohort**: 34 of its 899 verified types share a final
  segment with another (`Aspose.Pdf.Color` vs `Aspose.Pdf.Drawing.Color`, `Aspose.Pdf.Facades.Form`,
  `Aspose.Pdf.Drawing.Rectangle`, …), against 2 for 3D-.NET. Its `install_command:dotnet` also came
  back UNRESOLVED on this reading — F9's defect, third occurrence today — and its one CONTRADICTED
  fact is `example:005` (`error CS1061: 'Option' does not contain a definition for 'ExportValue'`).
- **Email-.NET is the cohort's cleanest repository**: every one of its 341 facts SUPPORTED, all four
  examples EXECUTED, no F8 collision. Its recorded blocker (`BLOCKED_REVIEW`, a reviewer-hallucinated
  Development Dependencies heading) is a review-stage predicate, and S10 is now reachable.

**Alternative rejected.** Amending the G4 manifest rows for Slides-.NET and PDF-.NET from this
lane. The manifest is the primary's evidence file, not a lane-owned path (lane prompt §0, §3); the
readings are recorded here and in `evidence/build/lanes/lane-f/LANE-F-01.json` for the owner to fold.

**Evidence.** `runs/transactions/{aspose-email-foss__Aspose.Email-FOSS-for-.Net/59125b47…,
aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET/b7172877…,
aspose-slides-foss__Aspose.Slides-FOSS-for-.NET/9f2d8710…}/{facts.json,preflight.json}`;
`composition/renderer.py::_table_names` run over each type list.

**Reversal path.** Each row is a dated reading of a moving upstream; re-measure before acting on one
that is more than a few days old, exactly as this entry did to the 2026-09-06 rows.

### F13 Email-.NET run 2: aborted at S5 (PLANNING); dispositioned `BLOCKED_PLANNING`

**Decision.** `aspose-email-foss/Aspose.Email-FOSS-for-.Net` is dispositioned `BLOCKED_PLANNING`,
not sealed, with **F10** (the planning `fact_ids` enum) as its resume predicate and **F9** as a
second, independent one. Its recorded blocker changes: the G4 manifest row and this lane file both
say `BLOCKED_REVIEW` (a reviewer-hallucinated Development Dependencies heading), and that is no
longer where it stops — it now stops two stages earlier and the review-stage unlocks named for it
(arrival item 28's fold-not-reject, PA-02's section-scoped `quote_located`) remain untested.

**Measured 2026-09-11, worktree `C:\w\f02`; 7 provider-call records, 5 `success` and 2
`response_invalid`, spanning 10:03:08–10:06:42 UTC.** S3 and S4 both
succeeded — `source_reconciliation` again returned `success` with no unknown fact ID, corroborating
`352fd35` on a second repository. S5 then rejected twice and `present` exited 1:

- attempt 1: `unknown fact ID format:msg`, `format:eml`, `format:cfb` — F10's defect, second
  repository.
- attempt 2: `at_a_glance is included, so its formats and capabilities are given` — the plan kept
  `at_a_glance` in its included sections while setting the object to `null`
  (`composition/planning.py:431-433`). Self-inflicted and satisfiable in principle: with 0 `format`
  facts the empty-list form passes `planning.py:435-451` cleanly, so this is model variance, not a
  deadlock. It is recorded, not proposed.

This repository would not have sealed even past S5: its full-run extraction read
`install_command:dotnet` as `UNRESOLVED` (F9's defect, fourth occurrence today) where its own
facts-only preflight 21 minutes earlier (09:41:31Z) read it `SUPPORTED`, so BC-02 would have failed at S9 as it
did for 3D-.NET. Facts digest `e4d8144e…16bd0` on the run against `33ed76be…2a7a6c6` at preflight —
341 records both times, one polarity apart.

**Alternative rejected.** Re-running to spend two more planning attempts on the chance the model
does not reach for `format:*` a third time. Two equivalent failed attempts prohibit a third
(loop-prompt §5) and nothing about the inputs would have changed; the mechanism to change is F10's,
and it is not a lane-F path.

**Evidence.** `runs/transactions/aspose-email-foss__Aspose.Email-FOSS-for-.Net/59125b47…48eb7/`
(`calls.jsonl` 7 calls — the two `response_invalid` records carry the rejection arrays quoted above;
`investigation.json`, `dispositions.json`; no `plan.json`); the run log line
`presentation_planning: output rejected twice`; `facts.json` polarity counts above.

**Reversal path.** When F10 lands, re-run this repository; if it then reaches S10, its original
`BLOCKED_REVIEW` predicate becomes testable for the first time since 2026-09-06.

### F14 What this run leaves for the cohort

**Decision.** LANE-F-01 stays `IN_PROGRESS`. Two of four repositories were run to a verdict and
dispositioned (F7, F13); PDF-.NET and Slides-.NET were measured facts-only (F12) and **not** run to
composition, and their existing G4 manifest rows stand unamended rather than being rewritten from a
facts-only reading.

**Why those two were not run.** Both of this run's compositions ended on shared-code defects with
no lane-F remedy, and the box was reached. Running PDF-.NET next would have been the worst use of
what remained: it carries **34** instances of F8 against 3D-.NET's 2 (F12), so it is the repository
most certain to fail BC-07, and at 12,580 facts it is the cohort's most expensive run. Slides-.NET
is the opposite case and the cohort's best remaining prospect — 0 F8 collisions, 2,733 of 2,734
facts SUPPORTED, and its recorded BC-02 blocker no longer exists (F12) — but it needs a run that can
survive S5 and BC-02, which is exactly what F10 and F9 are for.

**Order for the next run**, revised from the item's original order on this run's evidence:
Slides-.NET first (cleanest, and its old blocker is gone), then 3D-.NET (F8), then Email-.NET
(F10), then PDF-.NET (F8 ×34). The item's stated order put 3D-.NET first because it was the
2026-09-06 un-seal; that question is now known to be unanswerable until a run reaches S10, so it no
longer earns the first slot.

**Alternative rejected.** Spending the remaining box on PDF-.NET or Slides-.NET anyway, to raise the
count of repositories attempted. Neither could seal through F8/F9/F10, and a fourth and fifth
disposition naming the same three shared-code causes would bury the per-repository predicates
exactly as F4 warned on run 1.

**Evidence.** F7, F12, F13 above; `evidence/build/lanes/lane-f/LANE-F-01.json`.

**Reversal path.** The supervisor re-spawns LANE-F-01 when F8, F9 or F10 lands; F9 alone unblocks
BC-02 for every repository here, and F9 plus F10 is enough for Slides-.NET to be worth a full run.
