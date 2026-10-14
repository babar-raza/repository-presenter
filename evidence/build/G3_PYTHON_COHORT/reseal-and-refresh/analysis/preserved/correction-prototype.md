authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Correction prototype: live-first README patches (lane L-fix, FIX-01)

Date 2026-10-11. Code: branch `wt/lfix-fix01` (worktree `runs/wt/lfix`), package `src/repository_presenter/components/readme_correction/`. Commits:

```
c2c65f81 style(readme-correction): wrap the sections detector docstring
97642b71 fix(readme-correction): Third-party notices is not one of the ten template sections; never added
87ba0337 fix(readme-correction): public type counts are findings, not edits; example failures worded as the verifier's record
336aea72 fix(readme-correction): judge structure fixes against a structure-fixed baseline (revealed, not introduced)
e40bca38 fix(readme-correction): failing-example findings; two false positives caught on the live fleet (L-fix FIX-01)
2c34899e feat(readme-correction): structure fixes and non-correctable statuses (L-fix FIX-01, owner decisions D1/D2)
0488659a feat(readme-correction): correct-readme patch bundles from verified facts (L-fix FIX-01, owner decision 2026-10-11)
f69f75c7 fix(registry): read a NuGet package's own repository element as its source URL (CUT-2, NUGET-01)
```

Entry point: `repository-presenter correct-readme --repo OWNER/NAME [--facts PATH] --out DIR` (read-only toward the target, no model call). Without `--facts` it runs the existing facts-only path first (`present --facts-only`). `propose --correction-bundle DIR` is the typed alternative gate.

## 1. The five requested repositories

### 3D-Java (`3d2ed6be`)

- corrections.json summary: `{}` (0 edit(s)); README.patch: 0 bytes; deterministic=True, idempotent=True, provider_calls=0.

- Result: nothing to correct; no PR would be opened (the live README already matches the verified facts).

### Cells-Java (`c65329e7`)

- corrections.json summary: `{}` (0 edit(s)); README.patch: 0 bytes; deterministic=True, idempotent=True, provider_calls=0.

- Result: nothing to correct; no PR would be opened (the live README already matches the verified facts).

### Slides-Java (`620a2614`)

- corrections.json summary: `{}` (0 edit(s)); README.patch: 0 bytes; deterministic=True, idempotent=True, provider_calls=0.

- Result: nothing to correct; no PR would be opened (the live README already matches the verified facts).

### PDF-Java (`736cedaa`)

- corrections.json summary: `{"FALSE_CLAIM_FIX": 2}` (2 edit(s)); README.patch: 397 bytes; deterministic=True, idempotent=True, provider_calls=0.

- FALSE_CLAIM_FIX `claim_version` line 121: `26.6.0` -> `26.9.0`; evidence [('package:name', 'SUPPORTED'), ('package:published_version', 'SUPPORTED')]

- FALSE_CLAIM_FIX `claim_version` line 128: `26.6.0` -> `26.9.0`; evidence [('package:name', 'SUPPORTED'), ('package:published_version', 'SUPPORTED')]

- reported, not edited (`claim_public_types` line 330): the README states 1026 public types; the verified facts hold 1181 SUPPORTED class and enum symbols (1181 outside example and test code): its API tables are likely stale

### Words-Python (`2d2efee2`)

- corrections.json summary: `{}` (0 edit(s)); README.patch: 0 bytes; deterministic=True, idempotent=True, provider_calls=0.

- reported, not edited (`claim_public_types` line 607): the README states 146 public types; the verified facts hold 198 SUPPORTED class and enum symbols (189 outside example and test code): its API tables are likely stale

- Result: nothing to correct; no PR would be opened (the live README already matches the verified facts).


## 2. All 36 registry entries

Statuses: corrected 6, no_corrections 29, no_live_readme 1.

Each row is a real `correct-readme` run at the repository's live head; validation = `validate_candidate` (BC-01..BC-14) run on the live and the corrected README, introduced (blocking) / resolved failure counts.


| # | Repository | Head | Status | Edits (kind) | Patch (bytes, +/-) | Edits, quoted | Reported, not edited | Validation (introduced / resolved) |
|---|---|---|---|---|---|---|---|---|
| 1 | Aspose.3D-FOSS-for-.NET | 52b0f00e | no_corrections | - | 0, +0/-0 |  | failing_example L165: the example verifier recorded a failure for the example on lines 165-173: example 3: FAILED; Program.cs(3,41): | 0 / 0 |
| 2 | Aspose.3D-FOSS-for-Java | 3d2ed6be | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 3 | Aspose.3D-FOSS-for-Python | 65b1f577 | no_corrections | - | 0, +0/-0 |  | failing_example L274: the example verifier recorded a failure for the example on lines 274-286: example 8: FAILED; TypeError<br>claim_public_types L712: the README states 305 public types; the verified facts hold 337 SUPPORTED class and enum symbols (337 outside  | 0 / 0 |
| 4 | Aspose.3D-FOSS-for-TypeScript | 66cb26df | no_corrections | - | 0, +0/-0 |  | failing_example L143: the example verifier recorded a failure for the example on lines 143-155: example 2: FAILED; example_002.ts(9, | 0 / 0 |
| 5 | Aspose.BarCode-FOSS-for-Python | 06eca5c0 | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 6 | Aspose.Cells-FOSS-for-.NET | 941814fd | corrected | MISSING_SECTION 1 | 639, +10/-0 | + `## Dependencies` (L80) | failing_example L157: the example verifier recorded a failure for the example on lines 157-178: example 4: FAILED; Program.cs(1,20):<br>failing_example L185: the example verifier recorded a failure for the example on lines 185-201: example 5: FAILED; Program.cs(1,20):<br>failing_example L205: the example verifier recorded a failure for the example on lines 205-221: example 6: FAILED; Program.cs(1,20):<br>(+3 more) | 0 / 0 |
| 7 | Aspose.Cells-FOSS-for-Cpp | 9f852d0f | corrected | MISSING_SECTION 1 | 575, +10/-0 | + `## Dependencies` (L125) | failing_example L174: the example verifier recorded a failure for the example on lines 174-187: example 2: FAILED; example_002.cpp:1<br>claim_public_types L264: the README states 197 public types; the verified facts hold 195 SUPPORTED class and enum symbols (195 outside  | 0 / 0 |
| 8 | Aspose.Cells-FOSS-for-Go | 99c789e9 | corrected | STRUCTURE_FIX 2 | 829, +3/-1 | second_h1 L105: `#` -> `##`<br>+ `</details>` (L529) | failing_example L129: the example verifier recorded a failure for the example on lines 129-146: example 2: FAILED; the build failed <br>failing_example L152: the example verifier recorded a failure for the example on lines 152-161: example 3: FAILED; the build failed <br>failing_example L170: the example verifier recorded a failure for the example on lines 170-221: example 4: FAILED; the build failed <br>(+7 more) | 0 / 0 |
| 9 | Aspose.Cells-FOSS-for-Java | c65329e7 | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 10 | Aspose.Cells-FOSS-for-Python | 952317ca | corrected | MISSING_SECTION 1 | 460, +16/-0 | + `## Dependencies` (L46) | failing_example L112: the example verifier recorded a failure for the example on lines 112-120: example 5: FAILED; RuntimeError<br>broken_link L164: 'RELEASE_NOTES.md' is not in the tree and no unique file stands in for it<br>prose-only gaps: At a Glance, Documentation & Resources | 0 / 0 |
| 11 | Aspose.Cells-FOSS-for-Rust | 1a6004af | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 12 | Aspose.Cells-FOSS-for-TypeScript | fc186507 | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 13 | Aspose.Email-FOSS-for-.Net | 59125b47 | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 14 | Aspose.Email-FOSS-for-Cpp | c844a467 | no_corrections | - | 0, +0/-0 |  | failing_example L178: the example verifier recorded a failure for the example on lines 178-233: example 3: FAILED; example_003.cpp:3<br>failing_example L245: the example verifier recorded a failure for the example on lines 245-273: example 4: FAILED; example_004.cpp:5 | 0 / 0 |
| 15 | Aspose.Email-FOSS-for-Python | 10a906b4 | no_corrections | - | 0, +0/-0 |  | failing_example L174: the example verifier recorded a failure for the example on lines 174-186: example 5: FAILED; NameError | 0 / 0 |
| 16 | Aspose.Font-FOSS-for-Python | adf4885a | corrected | MISSING_SECTION 2 | 1615, +38/-0 | + `## Installation` (L33)<br>+ `## Dependencies` (L33) | failing_example L128: the example verifier recorded a failure for the example on lines 128-141: example 3: FAILED; TypeError<br>failing_example L295: the example verifier recorded a failure for the example on lines 295-418: example 5: FAILED; KeyError<br>broken_link L518: 'docs/one_command_web_optimizer.md' is not in the tree and no unique file stands in for it<br>prose-only gaps: At a Glance, Documentation & Resources, Key Capabilities, Scope and Limitations | 0 / 1 |
| 17 | Aspose.GIS.FOSS-for-.Net | b9b8c9c7 | no_live_readme | - | 0, +0/-0 | the repository has no README |  | - |
| 18 | Aspose.HTML-FOSS-for-Python | bf0f1e7a | no_corrections | - | 0, +0/-0 |  | failing_example L186: the example verifier recorded a failure for the example on lines 186-197: example 6: FAILED; ImportError; ran <br>claim_public_types L213: the README states 243 public types; the verified facts hold 303 SUPPORTED class and enum symbols (303 outside <br>claim_public_types L566: the README states 243 public types; the verified facts hold 303 SUPPORTED class and enum symbols (303 outside  | 0 / 0 |
| 19 | Aspose.Imaging-FOSS-for-.NET | 6ebb2091 | no_corrections | - | 0, +0/-0 |  | failing_example L153: the example verifier recorded a failure for the example on lines 153-163: example 1: FAILED; Program.cs(8,38):<br>failing_example L179: the example verifier recorded a failure for the example on lines 179-184: example 2: FAILED; Program.cs(3,58):<br>failing_example L204: the example verifier recorded a failure for the example on lines 204-209: example 4: FAILED; Program.cs(3,27): | 0 / 0 |
| 20 | Aspose.Note-FOSS-for-Python | 0fd1cf7b | no_corrections | - | 0, +0/-0 |  | failing_example L104: the example verifier recorded a failure for the example on lines 104-111: example 1: FAILED; AttributeError<br>claim_public_types L443: the README states 39 public types; the verified facts hold 37 SUPPORTED class and enum symbols (37 outside exa | 0 / 0 |
| 21 | Aspose.Page-FOSS-for-Python | 43cef367 | no_corrections | - | 0, +0/-0 |  | failing_example L265: the example verifier recorded a failure for the example on lines 265-270: example 8: FAILED; ImportError; ran  | 0 / 0 |
| 22 | Aspose-PDF-FOSS-for-Go | cdf43df1 | no_corrections | - | 0, +0/-0 |  | failing_example L261: the example verifier recorded a failure for the example on lines 261-292: example 1: FAILED; the build failed <br>failing_example L324: the example verifier recorded a failure for the example on lines 324-336: example 2: FAILED; the build failed <br>failing_example L348: the example verifier recorded a failure for the example on lines 348-366: example 3: FAILED; the build failed <br>(+3 more) | 0 / 0 |
| 23 | Aspose-PDF-FOSS-for-Python | 8f0edbe6 | no_corrections | - | 0, +0/-0 |  | failing_example L312: the example verifier recorded a failure for the example on lines 312-324: example 1: FAILED; FileExistsError<br>failing_example L329: the example verifier recorded a failure for the example on lines 329-337: example 2: FAILED; FileExistsError<br>failing_example L424: the example verifier recorded a failure for the example on lines 424-443: example 7: FAILED; NameError<br>(+7 more) | 0 / 0 |
| 24 | Aspose.PDF-FOSS-for-.NET | 10a36383 | no_corrections | - | 0, +0/-0 |  | claim_public_types L353: the README states 983 public types; the verified facts hold 969 SUPPORTED class and enum symbols (969 outside <br>claim_public_types L1778: the README states 983 public types; the verified facts hold 969 SUPPORTED class and enum symbols (969 outside  | 0 / 0 |
| 25 | Aspose.PDF-FOSS-for-Cpp | 4b83c9fe | no_corrections | - | 0, +0/-0 |  | failing_example L252: the example verifier recorded a failure for the example on lines 252-299: example 3: FAILED; example_003.cpp:3<br>failing_example L359: the example verifier recorded a failure for the example on lines 359-378: example 6: FAILED; example_006.cpp:1<br>claim_public_types L507: the README states 244 public types; the verified facts hold 249 SUPPORTED class and enum symbols (249 outside <br>(+1 more) | 0 / 0 |
| 26 | Aspose.PDF-FOSS-for-Java | 736cedaa | corrected | FALSE_CLAIM_FIX 2 | 397, +2/-2 | claim_version L121: `26.6.0` -> `26.9.0`<br>claim_version L128: `26.6.0` -> `26.9.0` | claim_public_types L330: the README states 1026 public types; the verified facts hold 1181 SUPPORTED class and enum symbols (1181 outsi | 0 / 2 |
| 27 | Aspose.PDF-FOSS-for-TypeScript | c672b391 | no_corrections | - | 0, +0/-0 |  | claim_public_types L3330: the README states 468 public types; the verified facts hold 477 SUPPORTED class and enum symbols (477 outside  | 0 / 0 |
| 28 | Aspose.PSD-FOSS-for-.NET | 85ed7eec | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 29 | Aspose.PSD-FOSS-for-Python | dbc90f46 | no_corrections | - | 0, +0/-0 |  | failing_example L134: the example verifier recorded a failure for the example on lines 134-167: example 2: FAILED; IndexError; ran a<br>failing_example L179: the example verifier recorded a failure for the example on lines 179-194: example 3: FAILED; IndexError; ran a | 0 / 0 |
| 30 | Aspose.Slides-FOSS-for-.NET | 86c441b5 | no_corrections | - | 0, +0/-0 |  | prose-only gaps: Key Capabilities, Scope and Limitations | 0 / 0 |
| 31 | Aspose.Slides-FOSS-for-Cpp | 469ce77a | no_corrections | - | 0, +0/-0 |  | failing_example L241: the example verifier recorded a failure for the example on lines 241-261: example 1: FAILED; example_001.cpp:1<br>failing_example L284: the example verifier recorded a failure for the example on lines 284-305: example 3: FAILED; example_003.cpp:1<br>failing_example L315: the example verifier recorded a failure for the example on lines 315-334: example 4: FAILED; example_004.cpp:1<br>(+3 more) | 0 / 0 |
| 32 | Aspose.Slides-FOSS-for-Java | 620a2614 | no_corrections | - | 0, +0/-0 |  |  | 0 / 0 |
| 33 | Aspose.Slides-FOSS-for-Python | 4e63447b | no_corrections | - | 0, +0/-0 |  | failing_example L413: the example verifier recorded a failure for the example on lines 413-433: example 15: FAILED; ValueError | 0 / 0 |
| 34 | Aspose.TeX-FOSS-for-Python | 181015d2 | no_corrections | - | 0, +0/-0 |  | failing_example L110: the example verifier recorded a failure for the example on lines 110-117: example 1: FAILED; IndentationError<br>failing_example L123: the example verifier recorded a failure for the example on lines 123-131: example 2: FAILED; IndentationError<br>failing_example L140: the example verifier recorded a failure for the example on lines 140-147: example 3: FAILED; IndentationError<br>(+6 more) | 0 / 0 |
| 35 | Aspose.Words-FOSS-for-.NET | 0d3f1add | no_corrections | - | 0, +0/-0 |  | broken_link L85: '../../issues' is not in the tree and no unique file stands in for it<br>claim_public_types L901: the README states 615 public types; the verified facts hold 618 SUPPORTED class and enum symbols (618 outside <br>claim_public_types L942: the README states 617 public types; the verified facts hold 618 SUPPORTED class and enum symbols (618 outside <br>prose-only gaps: Key Capabilities, Quick Start, Scope and Limitations | 0 / 0 |
| 36 | Aspose.Words-FOSS-for-Python | 2d2efee2 | no_corrections | - | 0, +0/-0 |  | claim_public_types L607: the README states 146 public types; the verified facts hold 198 SUPPORTED class and enum symbols (189 outside  | 0 / 0 |

## 3. What the yield says

- 36 of 36 registry entries ran through the official entry point with exit 0, each against its live head (facts reused where the sealed revision equals the head: 20; fresh facts-only extraction otherwise: 16, of which GIS has no README).
- Result: 6 repositories have a correction worth a PR (Cells-.NET, Cells-Cpp, Cells-Python: missing Dependencies from verified dependency facts; Font-Python: missing Installation and Dependencies; Cells-Go: a second H1 and an unclosed details block that swallowed License; PDF-Java: README pins 26.6.0 while Maven Central's current stable release is 26.9.0), 29 have nothing to correct (the live README already matches every verified fact the closed detector set can decide), 1 has no README (GIS: `no_live_readme`, handled by regeneration).
- Zero validation regressions across all 36 (introduced = 0 everywhere); the checks resolved (BC-14 on PDF-Java) are the only movement.
- The large remainder is reported, never edited: failing README examples (the verifier's own message and lines), stale `N public types` statements (the README's API tables are stale), dead links with no unique stand-in (Cells-Python RELEASE_NOTES.md, Font docs/one_command_web_optimizer.md, Words-.NET ../../issues), and sections that need prose (At a Glance, Key Capabilities, Quick Start, API Reference, Documentation & Resources, Scope).

## 4. Defects the real fleet exposed in my own detectors (all fixed, tests added)

1. `unclosed_details` counted a `<details>` named inside an inline code span (Aspose.HTML API table) and would have inserted a stray closer.
2. `claim_identity` (BC-14 rule c) flagged `go get <module>/v26/aspose/cells_foss`, a package inside the module, and would have rewritten it to the module root.
3. The BC-04 delta flagged a maintainer-written `v26` code span after a structure fix re-segmented the document for the judges; structure fixes are now judged against a structure-fixed baseline (recorded as `revealed`, never as introduced).
4. `claim_public_types` edited counts whose definition is disputed (Cells-C++ 197 stated, 195 verified, 196 hand-counted; PDF-.NET 983 vs 969): demoted to a finding.
5. A Third-party notices section (not one of the ten) was being inserted in four READMEs: removed from the derivable set.

## 5. Decisions for the owner

- `claim_version` updates a stale pin to the registry's current stable release (PDF-Java: 26.6.0 is still published, 26.9.0 is current), so it is a stale-pin fix rather than a falsehood fix; it never touches a manifest-ahead-of-registry statement (Slides-Java keeps its careful 26.7.0/26.8.0 wording) and never a `>=` floor. Restricting it to versions the registry does not list needs a versions-list fact the registry reader does not yet record.
- Public-type counts stay report-only until a definition of "public type" is ratified.
- `second_h1` demotes (text and anchor unchanged); turning a sentence-like H1 (Cells-Go L105) into a paragraph would also need its Navigation entry removed.
- The closed set has no build/test-command detector: the facts hold no command to compare against (only directories and file counts). `claim_test_files` fires only when the fact count and a recount by file name agree; it fired on none of the 36.
