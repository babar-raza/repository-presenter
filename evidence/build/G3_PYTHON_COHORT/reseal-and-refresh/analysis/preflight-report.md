authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
card: TC-PRE-01 (children 01 toolchains, 02 processability, 03 gateway headroom, 04 environment of record)
measured: 2026-10-10, Windows 11 (user babar), Python 3.13.2 (shared .venv), origin/main 7c5acbf7

# Local reseal preflight

Read-only measurement. No file outside this folder changed, no `candidates/` change, no PATH or
profile edit, no write to GitHub, no `present` run without `--facts-only`. Every table has a CSV
beside this report; the scripts that produced them are in `harness/` (stored as `.txt`).

## Summary

| Question | Answer |
|---|---|
| Can this machine verify every ecosystem? | Yes for 7 of 7 once `D:\Program Files\nodejs` is on the reseal shell's PATH. Zero BLOCKED_TOOLCHAIN in 36 facts-only runs. Without it npm is absent and the TypeScript repositories fail (control run below). |
| Gaps found | (1) Go example builds fail inside a git worktree (use a plain clone for Cells-Go and PDF-Go). (2) The registry has no `vcvarsall` key, so the MSVC fallback is inert (affects Cells-Cpp `install_command`). (3) No Python 3.10 to 3.12 (Words-Python examples stay NOT_VERIFIED, same as sealed). |
| Processability | All 36 admitted and `processable=true` by the tool; 0 provider calls in all 36. Expected classes differ from the tool's answer for 2 of the 6 unsealed entries (below). |
| Max parallel `present` runs | **8** by the card's rule (zero 429/5xx and flat latency at 1, 2, 4, 6, 8); see the caveat on probe weight. |
| Environment of record | Confirmed: 29 of 30 current bundles record os=Windows, python_version=3.13.2; this machine's venv is 3.13.2 on Windows 11. Cells-Rust's bundle carries no environment record. The bare `python` on PATH is 3.13.15 and must not be used. |

## 01 Toolchains (project resolver, `RP_TOOLCHAIN_REGISTRY` unset)

Registry read: `D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt` (the C: entries are re-rooted to D:).
`resolve_tool("npm")` is `None` by default and `D:\Program Files\nodejs\npm.cmd` once the directory is
prepended to the subprocess PATH.

| tool | default | node dir prepended |
|---|---|---|
| cargo | cargo 1.98.1 (797e8a9bc 2026-08-05) | cargo 1.98.1 (797e8a9bc 2026-08-05) |
| cmake | cmake version 4.4.2 | cmake version 4.4.2 |
| dotnet | 10.0.401 | 10.0.401 |
| go | go version go1.26.4 windows/amd64 | go version go1.26.4 windows/amd64 |
| gxx | g++.exe (MinGW-W64 x86_64-ucrt-posix-seh, built by Brecht Sanders, r1) 16.2.0 | g++.exe (MinGW-W64 x86_64-ucrt-posix-seh, built by Brecht Sanders, r1) 16.2.0 |
| javac | javac 21.0.11 | javac 21.0.11 |
| mvn | present (no version reported) | present (no version reported) |
| ninja | 1.13.2 | 1.13.2 |
| node | v24.13.1 | v24.13.1 |
| npm | absent | 11.8.0 |
| tsc | present (no version reported) | Version 5.9.3 |

Readings:

- Every expected version matches: javac 21.0.11, dotnet 10.0.401, go 1.26.4, g++ 16.2.0, cmake 4.4.2, ninja 1.13.2, cargo 1.98.1, node v24.13.1.
- npm is absent by default, as the plan said, and present (11.8.0) with the node directory prepended. Extra finding: `tsc` also changes from "present (no version reported)" to "Version 5.9.3", because the registry's tsc.cmd needs `node` on PATH to report. `mvn` stays "present (no version reported)" in both; Java examples still execute.
- The fingerprint is part of the sealed environment class. Resealing all 36 from one shell with the same exports keeps the class uniform. Most sealed bundles record no `environment.toolchains` (only 3 do), so every facts-only evaluation lists `environment.toolchains.* -> EXTRACTING`; expected and harmless for a full reseal.
- Control run without the node directory (Cells-TypeScript, plain clone): `npm install` exited 1 and 3 of 3 examples NOT_VERIFIED with "BLOCKED_TOOLCHAIN: tsc did not report a version". With it, Cells-TS builds and its 3 examples execute. The PATH export is mandatory for the three TypeScript repositories.
- `reseal-env.sh.txt` lists the exact exports. Nothing was written to the user or system PATH or any profile.

### MSVC (read-only listing)

| Location | vcvarsall.bat | MSVC tools |
|---|---|---|
| `D:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools` | present | 14.43.34808 |
| `D:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools` | present | 14.29.30133 |
| `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools` | present | 14.44.35207 |
| `D:\Program Files\Microsoft Visual Studio\2022\Community` | not found within 7 levels | not checked |

`cpp_examples.msvc_toolchain` reads the registry key `vcvarsall`; **`TOOLCHAIN_PATHS.txt` has no such key**, so it returns None and the MSVC fallback is not used on this machine. Effect measured: Cells-Cpp's sealed `install_command` fact is SUPPORTED ("verified source build"), while facts-only here yields UNRESOLVED (1 executed, 1 failed, 5 not_verified; the GCC `-Werror` upstream defect). A Cells-Cpp reseal here will therefore differ from the sealed bundle unless the owner adds one `vcvarsall=` line to the registry (data only, no PATH change). Owner decision; not made here.

## 02 Processability of all 36 (`present --facts-only`, no model call)

Run as 3 parallel processes in 3 worktrees (each its own `state.yaml` and `runs/`), clones read-only
via `GH_TOKEN`. Total 59.0 minutes of process time, median 1.1 min, longest 7.6 min (PDF-.NET).
Zero provider calls: the wrapper logs every HTTP request the process makes; `chat_completion_posts`
is 0 and no request touched the gateway's `/v1/` path in any of the 36 (column `calls`). A facts-only
run writes no call ledger (`calls.jsonl`) because it stops before any job. All 36 exited 0.
Columns: `ex` = executed/failed/other (not_verified + needs_input + blocked_toolchain);
`unres` and `contra` from the preflight record; `missing` = required README rows without evidence.

| repo | eco | bundle | proc | facts | ex | unres | contra | missing | min | calls |
|---|---|---|---|---|---|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | net | SEALED | True | 3933 | 6/1/0 | 1 | 1 | none | 0.9 | 0 |
| Aspose.3D-FOSS-for-Java | java | SEALED | True | 5521 | 6/0/1 | 1 | 0 | none | 0.7 | 0 |
| Aspose.3D-FOSS-for-Python | python | SEALED | True | 1724 | 7/1/4 | 38 | 1 | none | 0.9 | 0 |
| Aspose.3D-FOSS-for-TypeScript | typescript | NO_BUNDLE | True | 1162 | 3/1/0 | 1 | 1 | none | 2.2 | 0 |
| Aspose.BarCode-FOSS-for-Python | python | SEALED | True | 178 | 6/0/0 | 1 | 0 | none | 1.2 | 0 |
| Aspose.Cells-FOSS-for-.NET | net | SEALED | True | 794 | 8/1/0 | 1 | 1 | none | 3.1 | 0 |
| Aspose.Cells-FOSS-for-Cpp | cpp | SEALED | True | 2060 | 1/1/5 | 7 | 1 | none | 0.8 | 0 |
| Aspose.Cells-FOSS-for-Go | go | SEALED | True | 339 | 0/9/1 | 11 | 9 | none | 0.6 | 0 |
| Aspose.Cells-FOSS-for-Java | java | SEALED | True | 2838 | 3/0/0 | 0 | 0 | none | 0.6 | 0 |
| Aspose.Cells-FOSS-for-Python | python | SEALED | True | 1100 | 6/0/0 | 1 | 0 | none | 0.8 | 0 |
| Aspose.Cells-FOSS-for-Rust | rust | SEALED | True | 2236 | 1/0/6 | 7 | 1 | none | 2.8 | 0 |
| Aspose.Cells-FOSS-for-TypeScript | typescript | SEALED | True | 419 | 3/0/0 | 0 | 0 | none | 0.7 | 0 |
| Aspose.Email-FOSS-for-.Net | net | SEALED | True | 341 | 4/0/0 | 0 | 0 | none | 1.4 | 0 |
| Aspose.Email-FOSS-for-Cpp | cpp | SEALED | True | 357 | 2/2/0 | 2 | 2 | none | 0.5 | 0 |
| Aspose.Email-FOSS-for-Python | python | SEALED | True | 346 | 5/1/0 | 39 | 1 | none | 0.8 | 0 |
| Aspose.Font-FOSS-for-Python | python | SEALED | True | 953 | 3/2/0 | 18 | 3 | none | 1.4 | 0 |
| Aspose.GIS.FOSS-for-.Net | net | NO_BUNDLE | True | 1448 | 0/0/0 | 2 | 1 | license | 0.2 | 0 |
| Aspose.HTML-FOSS-for-Python | python | SEALED | True | 497 | 6/1/0 | 2 | 1 | none | 1.2 | 0 |
| Aspose.Imaging-FOSS-for-.NET | net | SEALED | True | 123 | 1/3/0 | 3 | 3 | none | 1.1 | 0 |
| Aspose.Note-FOSS-for-Python | python | SEALED | True | 352 | 11/1/0 | 1 | 1 | none | 0.9 | 0 |
| Aspose.Page-FOSS-for-Python | python | SEALED | True | 741 | 7/1/0 | 1 | 1 | none | 5.4 | 0 |
| Aspose-PDF-FOSS-for-Go | go | SEALED | True | 1905 | 0/6/0 | 6 | 6 | none | 0.8 | 0 |
| Aspose-PDF-FOSS-for-Python | python | SEALED | True | 2144 | 9/9/2 | 28 | 9 | none | 1.4 | 0 |
| Aspose.PDF-FOSS-for-.NET | net | SEALED | True | 13859 | 12/0/0 | 0 | 0 | none | 7.6 | 0 |
| Aspose.PDF-FOSS-for-Cpp | cpp | SEALED | True | 1878 | 5/2/5 | 8 | 2 | none | 0.8 | 0 |
| Aspose.PDF-FOSS-for-Java | java | SEALED | True | 25174 | 9/0/0 | 1 | 0 | none | 1.1 | 0 |
| Aspose.PDF-FOSS-for-TypeScript | typescript | NO_BUNDLE | True | 3849 | 13/104/0 | 104 | 104 | none | 4.5 | 0 |
| Aspose.PSD-FOSS-for-.NET | net | NO_BUNDLE | True | 298 | 2/0/0 | 0 | 0 | license | 0.4 | 0 |
| Aspose.PSD-FOSS-for-Python | python | NO_BUNDLE | True | 572 | 0/0/0 | 0 | 2 | installation,dependencies,license | 0.4 | 0 |
| Aspose.Slides-FOSS-for-.NET | net | SEALED | True | 2735 | 8/1/0 | 1 | 1 | none | 2.5 | 0 |
| Aspose.Slides-FOSS-for-Cpp | cpp | SEALED | True | 3045 | 2/6/1 | 7 | 6 | none | 2.4 | 0 |
| Aspose.Slides-FOSS-for-Java | java | SEALED | True | 5290 | 12/0/1 | 1 | 0 | none | 1.1 | 0 |
| Aspose.Slides-FOSS-for-Python | python | SEALED | True | 3410 | 14/1/0 | 3 | 1 | none | 1.1 | 0 |
| Aspose.TeX-FOSS-for-Python | python | NO_BUNDLE | True | 156 | 1/9/0 | 20 | 9 | none | 1.0 | 0 |
| Aspose.Words-FOSS-for-.NET | net | SEALED | True | 6791 | 0/5/0 | 6 | 6 | none | 5.1 | 0 |
| Aspose.Words-FOSS-for-Python | python | SEALED | True | 834 | 0/0/12 | 39 | 0 | none | 0.6 | 0 |

Facts by kind per repository: `factsonly_36.csv`. Every non-executed example with its reason: `examples_not_executed.csv`.

### Ecosystem rollup (examples across the 36)

| ecosystem | repos | processable | executed | failed | not_verified | needs_input | blocked_toolchain |
|---|---|---|---|---|---|---|---|
| cpp | 4 | 4 | 10 | 11 | 11 | 0 | 0 |
| go | 2 | 2 | 0 | 15 | 1 | 0 | 0 |
| java | 4 | 4 | 30 | 0 | 2 | 0 | 0 |
| net | 9 | 9 | 41 | 11 | 0 | 0 | 0 |
| python | 13 | 13 | 75 | 26 | 12 | 6 | 0 |
| rust | 1 | 1 | 1 | 0 | 6 | 0 | 0 |
| typescript | 3 | 3 | 19 | 105 | 0 | 0 | 0 |

`blocked_toolchain` is 0 everywhere. Most `failed` examples are real upstream compile or runtime errors or unbound-name fences, not machine gaps. The three machine-related findings:

1. **Go in a worktree.** Cells-Go and PDF-Go: 15 of 16 examples FAILED with "error obtaining VCS status: exit status 128 / Use -buildvcs=false". Reproduced in isolation with the runner's own `execute()`: the build passes outside any repository and in a plain `git clone`, and fails when the workspace sits inside a git worktree under the redirected HOME. The runner overrides `GOFLAGS` with `-mod=mod`, so the flag cannot be added from the shell. Verified fix without code change: a plain clone of the origin (`git clone --depth 1 <origin url>`; a local-path clone is refused for dubious ownership) gives Cells-Go 8 executed / 1 failed / 1 not_verified, identical to the sealed bundle. The lanes' worktree pattern is wrong for these two entries only.
2. **Words-Python.** All 12 examples NOT_VERIFIED: "no interpreter satisfies requires-python '>=3.10,<3.13'" (this machine has only 3.13). Identical to the sealed bundle. Optional: a 3.12 under `D:\tools\rp-toolchains` would let them run; not needed for a typed outcome.
3. **Words-.NET.** Sealed outcome was BLOCKED_TOOLCHAIN ("no clean workspace"); in a worktree here 5 FAILED with CS0234 `Aspose.JavaAttributes` (the known git-LFS-pointer harness artefact recorded in `docs/DECISION_LOG.md`). Plain-clone result: also 5 FAILED in a plain clone (`dotnet build Aspose.Words/Aspose.Words.csproj` exits 1), so it is not a worktree effect: the live head fails to compile on this machine, and the sealed BLOCKED_TOOLCHAIN came from an older harness path. Expect a changed outcome class on reseal.

### Same revision as the sealed bundle: do the examples reproduce?

For the 19 entries whose live head equals the sealed revision, outcome counts match exactly in 15; 3 improve under the current toolchains (3D-Java 0 to 6 executed, Cells-.NET 3 to 8, Slides-.NET 0 to 8) and 1 differs in class (Words-.NET, above). The other 11 sealed entries are drifted (different revision) and 6 have no bundle. Detail: `examples_vs_sealed.csv`.

### The 6 entries with no sealed bundle (3D-TS, GIS-.NET, PDF-TS, PSD-.NET, PSD-Python, TeX-Python)

| repository | eco | tool says processable | facts | ex exec/fail/other | rows without evidence | expected class |
|---|---|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | typescript | True | 1162 | 3/1/0 | none | PROCESSABLE |
| aspose-gis-foss/Aspose.GIS.FOSS-for-.Net | net | True | 1448 | 0/0/0 | license | NON_PROCESSABLE (README_MISSING; build fails) |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | typescript | True | 3849 | 13/104/0 | none | PROCESSABLE (high contradiction load; risk of UPSTREAM_DEFECT_BLOCKED) |
| aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | net | True | 298 | 2/0/0 | license | PROCESSABLE |
| aspose-psd-foss/Aspose.PSD-FOSS-for-Python | python | True | 572 | 0/0/0 | installation,dependencies,license | PROCESSABLE (thin evidence) |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | python | True | 156 | 1/9/0 | none | UPSTREAM_DEFECT_BLOCKED |

Evidence per row (build line, handoff ids, reasons): `no_bundle_6.csv`.

- The tool reports `processable=true` for all six. Two expected classes (GIS-.NET NON_PROCESSABLE, TeX-Python UPSTREAM_DEFECT_BLOCKED) have no producer yet; the plan's SOURCE_UNPARSEABLE / README_MISSING card is what closes that. Until then `present` will not stop at a typed non-processable outcome for these two by itself, so the reseal should not queue them as ordinary candidates.
- Pending handoffs exist in `evidence/upstream-defects/` for TeX-Python (check NOT_PROCESSABLE), 3D-TS (BC-02, BC-03) and PDF-TS (BC-02). None exists for GIS-.NET or PSD.

## 03 Gateway headroom

`repository-presenter preflight` run as parallel processes (one root per worker so the catalog
write does not race), 5 rounds per level, each round started together. Each preflight is 5 HTTP calls to
the gateway: one `GET /v1/models` and four `POST /v1/chat/completions` (seed probe and the two-pass
availability probe for `qwen3-next`). Per-request latency is the gap between consecutive logged
responses (the calls are sequential). Keys are never printed; no error bodies occurred.

| concurrency | processes | requests | status | 429/5xx | failed | req p50 s | req p95 s | wall p50 s | wall p95 s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 25 | 200:25 | 0 | 0 | 1.15 | 2.54 | 5.91 | 7.78 |
| 2 | 10 | 50 | 200:50 | 0 | 0 | 1.11 | 2.02 | 5.9 | 7.37 |
| 4 | 20 | 100 | 200:100 | 0 | 0 | 1.15 | 1.92 | 6.05 | 7.31 |
| 6 | 30 | 150 | 200:150 | 0 | 0 | 1.14 | 1.93 | 5.92 | 7.02 |
| 8 | 40 | 200 | 200:200 | 0 | 0 | 1.21 | 1.84 | 6.09 | 7.05 |

**Recommendation: max 8 parallel `present` runs** (the card's rule: highest tested level with zero
429/5xx; 200 of 200 at level 8; no probe above 8, so none recommended). Caveats:

- The probe is a liveness-size call (about 1 s). A real `present` holds long, large prompts; a gateway token or concurrency limit would show there, not here. The pilot (TC-PIL-01) should start at 3, the wave runner should back off on the first 429/5xx and record it, and the level should ramp to 8 only after a clean pilot.
- Each non-facts-only `present` also makes model-availability probe calls (`select_models`) at its start that are not in the provider ledger; at 8 runs that is about 8 x 4 small calls at launch. The probe above is exactly that shape and was clean.
- The facts-only batches ran concurrently with the probe and other lanes may have used the gateway; neither changed the status distribution.

## 04 Environment of record

- `candidates/*/<CURRENT>/dependencies.json` (`environment`), 30 bundles: `os` Windows in 29 and `python_version` 3.13.2 in 29. The 30th, Cells-Rust, records no environment at all (it predates the field), which is why its facts-only evaluation lists 29 changes. 3 bundles also record `toolchains` (BarCode-Python, Cells-Python, Font-Python). Table: `environment_of_record.csv`.
- This machine: Windows 11 (10.0.26200); `.venv/Scripts/python.exe` is 3.13.2 (`D:{BS}Python313`), identical to the record.
- **Trap:** bare `python` on PATH is `C:{BS}Users{BS}babar{BS}AppData{BS}Local{BS}Programs{BS}Python{BS}Python313` = 3.13.15. Anything run with it would seal `python_version=3.13.15` and differ from every bundle. Always call the venv's interpreter or `repository-presenter.exe`.
- Decision recorded: reseal on this machine; hosted ubuntu/3.11 stays the Track D proof environment.
- The sealed machine was probably a different Windows account (paths under `C:{BS}Users{BS}prora`); the Go finding and the dubious-ownership refusal of a local-path clone are the visible consequences.

## Blockers and open decisions

- None blocking. Owner decisions: (a) add a `vcvarsall=` line to the toolchain registry for Cells-Cpp parity; (b) optional Python 3.12 for Words-Python; (c) accept plain clones instead of worktrees for Cells-Go and PDF-Go.
- Not done on purpose: no change to the registry file, PATH, profile, `safe.directory`, or any tool install.
