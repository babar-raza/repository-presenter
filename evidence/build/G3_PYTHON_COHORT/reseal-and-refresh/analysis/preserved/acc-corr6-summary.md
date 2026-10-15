authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-summary: independent check of the live-first correction run 20261012-90a5a934 (detectors add_dev_commands and add_doc_links enabled)

Reviewer: independent (Sonnet 5.5), read-only; I did not author the run. Reviewed copy: `scratchpad/acc6/90a5a934` (byte copy of `scratchpad/lfix/runs/20261012-90a5a934`; `sha256sum -c SHA256SUMS` 471 of 471 OK, the list covers every file; `diff -r` against the source empty). Code: `git archive wt/lfix2-fix02` (tip 90a5a9349daafe4eecfd8f633c0069e5ff3bf66d, confirmed) into `scratchpad/acc6/code`. Fresh clones of the 10 content repositories at the pinned revisions (shallow fetch of the sha) in `acc6/clones`, `git archive` exports in `acc6/exports`, renders in `acc6/png`. My scripts: `acc6/scripts/` (`replay.py`, `idem.py`, `semdiag.py`, `chain_check.py`, `check_pr6.py`, `anchors.py`, `render40.py`, `drift.py`, `regen.py`, `ctx.py`). Records for every non-PUSHABLE repo: `acc-corr6-<name>.md` (9 files). The owner approved for the first wave exactly Cells-.NET, Cells-Cpp, Cells-Go, PDF-Java (Words-.NET removed on purpose).

## 1. Result

| Verdict | Repos | Patch bytes | Meaning |
|---|---|---|---|
| PUSHABLE | 35 (7 content, 28 diagram-only) | 71536 | patch verified; PR text true, readable, no overclaim |
| FIX_REQUIRED (PR text only; patch final) | 3: Cells-Go, PSD-.NET, Font-Python | 4588 | the generated lead or title says something the patch does not do |
| HOLD (owner-recorded, re-confirmed) | 2: 3D-.NET, TeX-Python | 4021 | hold reasons still true at the same heads |
| DO_NOT_PUSH (nothing to push) | 4: Cells-Python, Cells-Rust, PDF-.NET, GIS-.NET | 0 | |

40 patches, 80145 bytes in all (equals the owner table, per bundle: bytes, +lines, -lines). Of the owner's four: Cells-.NET, Cells-Cpp, PDF-Java PUSHABLE; Cells-Go FIX_REQUIRED (text only, suggested replacement text in `acc-corr6-cells-go.md`).

## 2. Step 1: replay confinement and idempotence, all 40 (and the 3 empty bundles)

- Against the previous reviewed run `0f6828d3`: README.md and README.patch are byte-identical in 34 of 40; they changed in the six that gained an addition (Cells-Go, Font-Python, Imaging, PDF-Go, PDF-Cpp, PSD-.NET). The other bundle files that changed are `corrections.json` report-only entries and `validation_delta.json` counts of the re-extracted facts (JMAP-Rust BC-04 35 to 36 in both columns, Words-Python BC-06 gone in both).
- `replay.py`, 40 of 40: sha256 of `README.original.md` and `README.md` equals `corrections.json` and `manifest.json` (every file hash and size); `git apply` (autocrlf off) of `README.patch` to `README.original.md` gives `README.md` byte for byte; replaying only the listed edits (offset spans, each `original` equal to the text at its span, no overlaps) gives `README.md` byte for byte; the corrected text with every edit span removed equals the original with the same spans removed; every line a line-level diff changes lies inside an edit span (one-line blank alignment tolerated); no CR, same final newline; patch bytes sum 80145.
- `idem.py` with the archived tip code, venv Python 3.13.2 (package path checked): for each of the 43 bundles `correct_settled` on the corrected README as the new live one makes 0 further edits (40 of 40 corrected; the 3 empty stay empty); re-running the original gives the bundle's bytes and the same edit list (detector, start, end) in 43 of 43.
- Drift (`drift.py`, read-only `gh api`): all 43 heads equal the bundle revisions today; `README.original.md` equals the live blob at that revision (sha256) in 43 of 43; GIS-.NET still has no README (404).
- Markup hygiene of every corrected README: fence parity even, `<details>`/`</details>` balance introduced nowhere (Cells-Go 2/3 closed becomes 3/3), no CRLF change, no trailing whitespace added, exactly one `%%{init}%%` per redrawn diagram. Anchors (`anchors.py`, own GitHub-slug implementation): no internal link breaks in any README; every new `#dependencies` item resolves; H1 count 1 in 43 of 43 after (Cells-Go 2 to 1).
- Focused tests of the archived tip (`tests/components/readme_correction`, `tests/components/readme_diagram`, venv Python 3.13.2): 477 tests, 0 failures, 0 errors, 10 skipped (renderer or toolchain gated), exit 0.

## 3. Step 2: every ADDED command, CI sentence and link, on a clean clone

| Repo | Addition | How I checked | Result |
|---|---|---|---|
| Cells-Go (approved) | `go build ./...` at the end of Development and Testing, before the `<details>` | fresh clone 99c789e9, Go 1.26.4 (`resolve_tool("go")`): build and test exit 0; Linux container `golang:1` (Go 1.27.2, no network): build ok, `tests` ok. README showed only `go test`; one occurrence of `go build` now. No CI workflow exists | true; wording defects in the PR text, see section 4 |
| Cells-Go | `</details>` before `## Detailed Documentation`; `#` to `##` on line 105 | tag balance 3/3; H1 2 to 1; anchors | true; the TOC entry of the demoted heading keeps indent 0 (cosmetic) |
| Cells-.NET (approved) | `## Dependencies`: SkiaSharp 2.88.8; "Requires .NET `netstandard2.0;net8.0`"; Navigation item | csproj at 941814fd (one PackageReference SkiaSharp 2.88.8; `TargetFrameworks netstandard2.0;net8.0`); the published nuspec of Aspose.Cells.FOSS 26.9.0 lists SkiaSharp 2.88.8 for both frameworks; item sits between Installation and Quick Start like the section; `#dependencies` resolves; no other Dependencies heading | true; advisories A-2 |
| Cells-Cpp (approved) | `## Dependencies`: no required third-party packages; C++ 17; CMake 3.16; Navigation item | `Aspose.Cells.Foss.Cpp/CMakeLists.txt`: `cmake_minimum_required(VERSION 3.16)`, `CMAKE_CXX_STANDARD 17`, no find_package/FetchContent; sources include only standard headers; GoogleTest is fetched only by the test project (the README's dev section says so) | true; advisories A-3 |
| PDF-Java (approved) | `26.6.0` to `26.9.0` on lines 121 and 128 | Maven Central `maven-metadata.xml`: latest and release 26.9.0 (versions 26.6.0, 26.8.0, 26.9.0); the 26.9.0 pom and jar answer 200; `pom.xml` version 26.9.0; no other 26.x in the README | true |
| Words-.NET (not in wave 1) | NuGet badge in the badge row | NuGet flat container lists 26.2.0, 26.3.0 (the badge's package id exists, 26.3.0 current) | true |
| Imaging | "The ci workflow runs on Ubuntu and Windows." | `.github/workflows/ci.yml` parsed: matrix `os: [ubuntu-latest, windows-latest]`, push and pull_request triggers; link target exists | true |
| PDF-Go | "The test workflow runs on Ubuntu, Windows and macOS." | `test.yml`: matrix ubuntu/windows/macos-latest, runs `go build ./...` and `go test ./...` | true |
| PDF-Cpp | CI sentence + "Releases run through the release workflow" | `ci.yml` matrix: Linux gcc-13 and clang-16 (ubuntu-latest), Windows MSVC; `release.yml` on `v*` tags builds, tests, packages and creates a draft GitHub Release | CI true; release sentence loose, A-4 |
| PSD-.NET | `dotnet build Aspose.PSD-FOSS-for-.NET.sln` | `git archive` export, .NET SDK 10.0.401: exit 0, 0 warnings, 0 errors | true; text defect |
| Font-Python | Changelog and Security policy links | both files exist at adf4885a, non-empty, read like their labels; README names neither elsewhere | true; text defect |

None of the ten duplicates anything in the whole README, none contradicts it (grep of the added commands and sentences over the corrected file: one occurrence each), each lies at depth 0 (outside `<details>` and fences) at the end of its section or in the new section, and the Navigation items added are the only contents edits.

## 4. Step 3: the 40 PR texts

- Regenerated all 40 with the archived tip code (`compose_correction_pull_request`): byte-identical to `pr_text/` (40 of 40). Plain ASCII; grep for `BC-\d+`, `OD-\d+`, `R\d`, `validate_candidate`, allowance, `DIAGRAM_FIX` and the other kinds, fact ids, run ids, paths, tokens, "owner", "ruling", "template", "detector": nothing in 40; `pr_text_scan.txt` agrees. How to review and How to decline in 40 of 40; tone respectful, "we" not "you must", decline says closing is enough.
- `check_pr6.py` against `corrections.json`, `validation_delta.json` and the original READMEs: candidate hash, source revision, idempotent, deterministic, model calls, render sentence (releases, fonts, clipped, splits, problems) in 40 of 40. The new checks sentence ("They report N failure(s) on yours and M on the corrected one: it removes R of the N and adds none") is exact in 40 of 40: N and M are the totals of `live_failures` and `corrected_failures`, R and the added count are computed check by check and N - R + added = M; where it says "adds 1" (Cells-Go, Email-Cpp, PDF-Java) the added one is explained by the revealed or length bullet and none is introduced. This closes the predecessor's finding on "has N fewer". `chain_check.py` (own parser): label count, group-title count and the chain of every diagram sentence equal the original diagram, 39 of 39. Semantic comparison of every redraw against its original (`semdiag.py`: id to label map with `<br/>` read as a space, group titles, edges, group membership, no `& < >`): 0 differences in 39.
- The four approved texts read in full. Cells-.NET, Cells-Cpp, PDF-Java: accurate, plain, every statement matches the delta and the clone; PDF-Java's length bullet (304 lines, 4 over the 300-line limit the checks apply, yours was 299) is right (patch adds 5 lines). Cells-Go: defects (section 6 and `acc-corr6-cells-go.md`).
- The other content texts read in full: Imaging, PDF-Go, PDF-Cpp, Words-.NET fine (A-4 for PDF-Cpp); PSD-.NET and Font-Python carry the defects of the same generator branches as Cells-Go (records).
- The 30 diagram-only texts share one template (3D-Java read in full; every number, chain and count checked by script); the two length bullets in the whole run (Email-Cpp, PDF-Java) are exact.

## 5. Step 4: every changed diagram on Mermaid 11.4.1 and 12.1.0

`render40.py` (harness `components/readme_diagram/render_check.py`, `RP_MERMAID_TOOLS=D:/tools/mermaid/tools`, Chrome 154): the 39 redrawn diagrams of the corrected READMEs, on 11.4.1 and on 12.1.0, natively and in five wider fonts: 39 of 39 horizontal, 0 clipped, 0 word splits, 0 other problems, 0 foreignObject boxes, on both releases (the author's record covers 11.12.0 and 11.17.2 too and is byte-identical to the last run's). I looked at the PNGs of the four approved diagrams on both releases: horizontal, no word broken across lines, nothing clipped. Known and carried over: on 12.1.0 the second capability column is drawn left of the first in two-column diagrams (seen in Cells-Cpp, Cells-Go, PDF-Java; Cells-.NET is in order); whether github.com runs 12.x is unverified. The one corrected-bundle diagram the author's `render_verdicts.json` lists as vertical and clipped is Cells-Rust's unredrawn live diagram (no push); the owner table sentence "Of the 40 diagrams in the corrected READMEs, 1 ... " is about it.

## 6. Verdicts

PUSHABLE (35): Cells-.NET, Cells-Cpp, PDF-Java (approved), Words-.NET, Imaging, PDF-Go, PDF-Cpp, and the diagram-only 3D-Java, 3D-Python, 3D-TypeScript, BarCode-Python, Cells-Java, Cells-TypeScript, Email-.Net, Email-Cpp, Email-Python, JMAP (.NET, Cpp, Go, Java, Node.js, Python, Rust, TypeScript), HTML-Python, Note-Python, Page-Python, PDF-Python, PDF-TypeScript, PSD-Python, Slides (.NET, Cpp, Java, Python), Words-Python.
FIX_REQUIRED (3, PR text only): Cells-Go (approved), PSD-.NET, Font-Python. HOLD (2): 3D-.NET (IOService lines 67 and 88 still throw; diagram labels U3D, RVM, AMF, HTML5), TeX-Python (102 of 119 `.py` files unparsable, re-counted). DO_NOT_PUSH (4): Cells-Python, Cells-Rust, PDF-.NET (`NO_DETECTOR_FIRED` or `ONLY_CHANGE_UNPORTABLE_DIAGRAM`), GIS-.NET (no README).

## 7. Final owner-ready list for the approved four

| Repo | PR title | Patch (+/-) | Verdict |
|---|---|---|---|
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2588 bytes (+31/-15) | PUSHABLE |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2799 bytes (+32/-17) | PUSHABLE |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | docs(readme): show the current release (26.9.0) in the install snippets and lay out the At a Glance diagram left to right | 2541 bytes (+26/-21) | PUSHABLE |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | generated: docs(readme): 4 verified corrections; suggested: docs(readme): fix two markup problems, add the go build command and lay out the At a Glance diagram left to right | 2956 bytes (+30/-17) | FIX_REQUIRED (text only); push after the generator change or a hand-edited body (`acc-corr6-cells-go.md`) |

Send the three PUSHABLE ones now. The Cells-Go patch itself is final.

## 8. Advisories (none blocks)

- A-1, Cells-Go: the contents entry of the demoted heading stays at indent 0 (line 20); cosmetic.
- A-2, Cells-.NET: the intro says "pure managed code ... runs on Windows, Linux, and macOS" while the new section lists SkiaSharp 2.88.8 (a native binding; the Linux native assets are a separate package); the section is true as written (the nuspec says so) and the tension was already there. "Requires .NET `netstandard2.0;net8.0`" is the property value verbatim and reads like a typo; the Installation paragraph says the same correctly.
- A-3, Cells-Cpp: "Requires CMake 3.16 or later" is unconditional while the NuGet and MSBuild path needs no CMake. Separate upstream finding, not this PR: the pinned library does not build today with its own `-Wall -Wextra -Werror` on GCC 16.2 (trigraph `??/` in `NumberFormat.cpp:30`) or clang 22.1 (`-Wstring-concatenation` in `DisplayTextDateFormatSupport.cpp:85`); worth an issue.
- A-4, PDF-Cpp: "Releases run through the release workflow": the workflow creates a draft release; signing and the nuget.org push are done by the maintainers' internal pipeline (said in the workflow's own header). The bullet in the PR shows the sentence cut with "....".
- A-5: on 12.1.0 two-column capability blocks reverse (carried over).
- A-6: Imaging, PSD-.NET and PSD-Python: the redraw replaces the maintainers' own `%%{init: {"flowchart": {"useMaxWidth": true}}}%%` line with its own; the PR text calls it "one `%%{init}%%` line" without saying it replaces theirs.
- A-7, carried: the redraw rides in the same PR as the fix (declining one declines both); no human contact and no reason why this repository was chosen; the provenance block names `candidate_hash`, `policy_version`.
- A-8: the Cells-Go `go build` block comes after the `go test` block (build is conventionally first); fixed text from the detector.

## 9. What I could not verify

- Rendering on github.com (its Mermaid version and fonts).
- Library builds and tests other than: Cells-Go (Windows and Linux), PSD-.NET build (Windows). Cells-Cpp was built (does not build on today's compilers, A-3); Imaging, PDF-Go, PDF-Cpp, Words-.NET additions are sentences and badges and rest on the workflow YAML and the registry, not on a build.
- Truth of the maintainers' own diagram labels (the redraw republishes them verbatim), except 3D-.NET (the hold).
- The three no-detector READMEs: I confirm there is no patch, not that they are accurate.
- Tests beyond those two directories (the full suite, hosted workflows, `scripts/ci_check.sh`) were not run.
