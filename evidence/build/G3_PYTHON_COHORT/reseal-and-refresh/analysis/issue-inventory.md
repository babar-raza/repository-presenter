authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Upstream-defect inventory (TC-ISS-01, G6-W01)

One deduplicated, command-verified inventory of the upstream defects found by the four candidate reviews,
measured against the 18 handoffs already under `evidence/upstream-defects/`. Verified 2026-10-10 at the live
default-branch head of every repository (`raw-logs/live-heads.txt`, `gh api repos/<r>/commits/<branch>`).
Nothing was filed, commented, forked or branched on any Aspose repository: the lane used `git clone --depth 1`,
`gh api` GET, package-registry GETs and local build/parse commands only.

## Result

- Review candidates considered: 77 rows (A 17, B 31, C 13, D 16).
- NEW: 65. Of these REPRODUCED 59, NOT_REPRODUCED 1, NOT_ATTEMPTED 4 (informational or needs a toolchain this lane lacked), NOT_A_DEFECT 1.
- ALREADY_COVERED by an existing handoff or an open upstream issue: 9. WEAKER_THAN_EXISTING (review draft adds nothing): 1. SUPERSEDES_EXISTING (review draft is stronger than the existing body): 2.
- New handoffs created (HANDOFF_PENDING, digests computed by `approval.evidence_digest`, CONFIRMED entries appended to `reverification.json`): 6, all BC-03 (README example fails). Total handoffs: 24. (A seventh, a `NOT_PROCESSABLE` handoff for GIS .NET, was withdrawn: `NOT_PROCESSABLE`'s redetector only re-parses named source files, and a build failure has no such file, so the committed-corpus replay test rejects it; the GIS build failure is draft U51.)
- Reproduced defects the model cannot represent: 51 complete drafts in `issue-drafts-unrepresentable.md` (U01..U51; three are marked disclosed-upstream and not recommended for filing).
- Replacement text for weak existing handoffs: `handoff-replacements.md` (TeX R1 applied in place; 3D-TS R2 and PDF-TS R3 not applied, both stay NOT_A_DEFECT).
- Issue-text quality gate (TC-ISS-04, PR #319): all 14 existing CONFIRMED handoffs except Imaging-.NET, and the 6 new ones, were re-drafted from the same verified evidence (new product-prefixed title, an Expected section, no pipeline wording; same fingerprint, revision, check and evidence; TeX re-measured to 102/119) and pass `issue_quality_findings`; their `reverification.json` digests were recomputed with `approval.evidence_digest`. Still failing, deliberately: 3D-TS BC-02 and PDF-TS (NOT_A_DEFECT), Imaging-.NET (FIXED_OR_CHANGED) and the synthetic FILED record.
- One existing handoff is now stale: Imaging-.NET `2c99dc76` (see the existing-handoff table).

## What the handoff model can and cannot represent

`schemas/upstream-defect-handoff.schema.json` and `components/issues/model.py`: `triggering_check.id` is a
non-empty string described as a validation check id (`BC-02`, `BC-03`, `BC-06`) or the repository-level disposition
`NOT_PROCESSABLE`; `causal_stage` is the constant `EXTRACTING`; the artifact carries evidence, a claim, a title,
a body and a lifecycle status. `components/issues/draft.py` auto-drafts only `BC-02`, and `redetect.py` can replay
only a PyPI-name `BC-02` and an unparseable `.py` `NOT_PROCESSABLE` (the `replay_gap` of `issue-readiness`).

| Defect kind | Representable? | How |
|---|---|---|
| README example fails (compile error, runtime exception, missing include) | yes | `BC-03` |
| README install command or badge names a package that is not published | yes | `BC-02` |
| README link target missing | yes | `BC-06` |
| Repository cannot be processed at all (unparseable source, library does not build, no README) | yes | `NOT_PROCESSABLE` |
| LICENSE missing or only in a subdirectory | no | not a check failure; needs `defect_class` `LICENSE_MISSING_ROOT` |
| Package metadata: placeholder URLs/author, stale URL, wrong version, missing fields | no | `PLACEHOLDER_METADATA` / `STALE_METADATA` / `VERSION_MISMATCH` |
| Packaging: `main` points nowhere, runtime dependency in devDependencies, wheel ships `examples` | no | `PACKAGING_BROKEN` |
| Install from source fails (`pip install .`, build script reads an untracked file) | no (BC-02 only when the README claims it and the PyPI redetector can replay it) | `INSTALL_FAILS` |
| Upstream test suite fails or is not discovered, fixtures untracked | no | `TESTS_FAIL` / `NO_TESTS` |
| In-repo documents contradict each other or the code (limitations lists, version notes, file-format tables) | no | `DOC_CONTRADICTION` / `STALE_DOC` |
| Documented commands in a non-README file point at paths that do not exist | no | `DOC_COMMAND_BROKEN` |
| Library side effect or runtime error outside a README example (stdout logging, MCP `run()`) | no | `RUNTIME_ERROR` / `LIBRARY_SIDE_EFFECT` |
| Repository hygiene: build output or logs committed | no | `REPO_HYGIENE` |

The class names are proposals for TC-ISS-03's `defect_class` registry; this lane did not change `schemas/` or `src/`.

## Existing handoffs (before this lane)

Handoff short id is the first 8 hex of the fingerprint. `heads` compares the handoff's `source_revision` with the live head on 2026-10-10. Verdicts are from `reverification.json` (2026-10-09).

| Repository | Handoff | Check | Status | Revision | Live head | Heads | Re-verification | Note |
|---|---|---|---|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | ad94a06d | BC-03 | HANDOFF_PENDING | 52b0f00e | 52b0f00e | same | CONFIRMED |  |
| Aspose.3D-FOSS-for-Python | 094c4163 | BC-03 | HANDOFF_PENDING | 65b1f577 | 65b1f577 | same | CONFIRMED |  |
| Aspose.3D-FOSS-for-TypeScript | 9264bf05 | BC-03 | HANDOFF_PENDING | 66cb26df | 66cb26df | same | CONFIRMED |  |
| Aspose.3D-FOSS-for-TypeScript | a6f52c1a | BC-02 | HANDOFF_PENDING | 66cb26df | 66cb26df | same | NOT_A_DEFECT | NOT_A_DEFECT; jargon body; see R2 |
| Aspose.Cells-FOSS-for-.NET | 7e755ed8 | BC-03 | HANDOFF_PENDING | 941814fd | 941814fd | same | CONFIRMED |  |
| Aspose.Cells-FOSS-for-Cpp | 3f1b3176 | BC-02 | HANDOFF_PENDING | 9f852d0f | 9f852d0f | same | CONFIRMED |  |
| Aspose.Cells-FOSS-for-Cpp | b3df5761 | BC-02 | HANDOFF_PENDING | 9f852d0f | 9f852d0f | same | CONFIRMED |  |
| Aspose.Cells-FOSS-for-TypeScript | c04f74bf | BC-02 | HANDOFF_PENDING | fc186507 | fc186507 | same | CONFIRMED |  |
| Aspose.Email-FOSS-for-Cpp | 7f0f3388 | BC-02 | HANDOFF_PENDING | c844a467 | c844a467 | same | CONFIRMED |  |
| Aspose.Font-FOSS-for-Python | 0dcf9304 | BC-06 | HANDOFF_PENDING | adf4885a | adf4885a | same | CONFIRMED |  |
| Aspose.Font-FOSS-for-Python | 52ba0e1d | BC-03 | HANDOFF_PENDING | adf4885a | adf4885a | same | CONFIRMED |  |
| Aspose.Font-FOSS-for-Python | a241746e | BC-02 | HANDOFF_PENDING | adf4885a | adf4885a | same | CONFIRMED |  |
| Aspose.Font-FOSS-for-Python | dc90b681 | BC-03 | HANDOFF_PENDING | adf4885a | adf4885a | same | CONFIRMED |  |
| Aspose.HTML-FOSS-for-Python | ae9f06b9 | BC-02 | HANDOFF_PENDING | bf0f1e7a | bf0f1e7a | same | CONFIRMED |  |
| Aspose.Imaging-FOSS-for-.NET | 2c99dc76 | BC-02 | HANDOFF_PENDING | a7c7314b | 6ebb2091 | moved | CONFIRMED | STALE: the head moved after the 2026-10-09 re-verification (commit 6ebb2091, 2026-10-10 04:55 -07:00 'Refresh README'); the README no longer contains `dotnet add package` or a NuGet badge (`raw-logs/imaging-recheck.txt`). The claim is no longer true at the live head: its re-verification entry is changed from CONFIRMED to FIXED_OR_CHANGED in this PR (the Re-verification column shows the value before the change) |
| Aspose.PDF-FOSS-for-TypeScript | ef667e7d | BC-02 | HANDOFF_PENDING | a8661f8b | c672b391 | moved | NOT_A_DEFECT | NOT_A_DEFECT; jargon body; withdraw (R3) |
| Aspose.TeX-FOSS-for-Python | c00f9615 | NOT_PROCESSABLE | HANDOFF_PENDING | 181015d2 | 181015d2 | same | CONFIRMED | understated (35 of 45); see R1 |
| repository-presenter | b7bf37c2 | BC-02 | FILED | b7715aa5 | - | n/a | - | synthetic filing-path test record (issue #189), not a product defect |

Counts: 18 existing handoffs; 15 CONFIRMED, 2 NOT_A_DEFECT, 1 synthetic FILED. Heads equal the handoff revision for all but Imaging-.NET and PDF-TS (the latter already NOT_A_DEFECT at its moved head).

## New handoffs (this lane)

| Repository | Handoff | Check | Status | Revision | Reproduction log |
|---|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | af8da760 | BC-03 | HANDOFF_PENDING | 52b0f00e | quickstart-3D-NET, quickstart-3D-NET-without-format |
| Aspose.Cells-FOSS-for-Cpp | 74b4b0a3 | BC-03 | HANDOFF_PENDING | 9f852d0f | load-example-Cells-Cpp |
| Aspose.Note-FOSS-for-Python | 6532670d | BC-03 | HANDOFF_PENDING | 17b5d7fe | quickstart-Note-Python |
| Aspose.PDF-FOSS-for-Cpp | a1a661ef | BC-03 | HANDOFF_PENDING | 4b83c9fe | snippets-PDF-Cpp |
| Aspose.PDF-FOSS-for-Cpp | f49213f4 | BC-03 | HANDOFF_PENDING | 4b83c9fe | snippets-PDF-Cpp |
| Aspose.Slides-FOSS-for-Cpp | 8b8b2cae | BC-03 | HANDOFF_PENDING | 469ce77a | snippets-Slides-Cpp |

Each body states one defect, the exact reproduction, expected versus actual, the location in the repository and a suggested fix, and ends with the `repository-presenter-defect` fingerprint marker that `file.py` uses for duplicate search. Fingerprints are `draft._fingerprint(repository, check id, signature)`; each signature names the file and line range plus the symptom. Digests are `approval.evidence_digest` of the handoff as committed; the matching `CONFIRMED` entries are in `reverification.json`.

## Delta table

Source: A = review-A (8 candidates), B = review-B (11 candidates with forbidden edition wording), C = review-C (11 drifted candidates), D = review-D (6 unsealed repositories). `Outcome` is the new handoff short id, a draft number (`U..` in `issue-drafts-unrepresentable.md`, `R..` in `handoff-replacements.md`), the existing handoff, or why the row was dropped. `Log` names a file under `raw-logs/`.

| Src | Id | Repository | Candidate | Class | Verdict | Outcome | Log |
|---|---|---|---|---|---|---|---|
| A | A1 | Cells-Cpp | LICENSE only under License/ | NEW | REPRODUCED | U01 | license-Cells-Cpp |
| A | A2 | Cells-Cpp | Tests README uses non-existent workspace/ paths | NEW | REPRODUCED | U23 | paths-Cells-Cpp-tests-readme |
| A | A3 | Cells-Cpp | README "Load an Existing Workbook": no match for operator[] (draft said "do not file until reproduced") | NEW | REPRODUCED | HANDOFF 74b4b0a3 (root cause: WorksheetCollection.h not included) | load-example-Cells-Cpp |
| A | A4 | Cells-Java | Committed Javadoc is for the removed com.aspose.cells_foss package | NEW | REPRODUCED | U21 | javadoc-Cells-Java |
| A | A5 | Cells-Java | Mojibake in pom.xml and Agents.md | NEW | REPRODUCED | U22 | javadoc-Cells-Java |
| A | A6 | Cells-Java | LICENSE only under License/ | NEW | REPRODUCED | U02 | license-Cells-Java |
| A | A7 | Cells-Python | save_as_csv default encoding is locale-dependent (UnicodeEncodeError on cp1252) | NEW | REPRODUCED | U14 | csv-encoding-Cells-Python |
| A | A8 | Cells-Python | Two tests need an input/ directory that is not tracked | NEW | REPRODUCED | U15 | tests-input-dir-Cells-Python |
| A | A9 | Cells-Python | Wheel ships a top-level examples package | NEW | REPRODUCED | U16 | wheel-Cells-Python |
| A | A10 | Cells-Python | project.urls use the old repository name | NEW | REPRODUCED | U17 | urls-Cells-Python |
| A | A11 | Cells-Python | LICENSE only under License/ | NEW | REPRODUCED | U03 | license-Cells-Python |
| A | A12 | Cells-Rust | No tests: cargo test runs 0 tests | NEW | REPRODUCED | U19 | cargo-test-Cells-Rust |
| A | A13 | Cells-Rust | README Installation: pre-publication wording | NEW | REPRODUCED | U20 | notests-Cells-Rust |
| A | A14 | Slides-Java | Maven Central serves only 26.7.0 (disclosed upstream in SECURITY.md/README) | NEW | REPRODUCED | U46 (do not file: disclosed) | maven-Slides-Java |
| A | A15 | Slides-Java | getMasters().addClone silently dropped (draft: unverified, no JDK) | NEW | NOT_ATTEMPTED | dropped: needs a JDK 21 build; upstream README Scope already discloses it | - |
| A | A16 | Words-Python | dev extra omits pdfplumber (1 ApiExamples test fails) | NEW | REPRODUCED | U18 | pdfplumber-Words-Python |
| A | A17 | Words-Python | requires-python <3.13 blocks Python 3.13 | NEW | REPRODUCED | dropped: an observation / feature request, not a defect (log kept) | requires-python-Words-Python |
| B | B1 | 3D-.NET | README Quick Start Scene.Save(path, FileFormat.FBX7400Binary) throws NotImplementedException | NEW | REPRODUCED | HANDOFF af8da760 | quickstart-3D-NET |
| B | B2 | 3D-.NET | README Scene.FromFile(string, FileFormat) does not compile (CS1503) | ALREADY_COVERED | CONFIRMED 2026-10-09 | existing ad94a06d | - |
| B | B3 | 3D-.NET | Test suite needs an untracked testdata/ (53 of 183 fail) | NEW | REPRODUCED | U27 | testdata-3D-NET |
| B | B4 | 3D-.NET | Stray build.log, test.log and FileFormat.cs.bak committed | NEW | REPRODUCED | U28 | hygiene-3D-NET |
| B | B5 | 3D-.NET | csproj 26.1.0 / NuGet 26.1.0 vs docs describing 26.2.0 | NEW | REPRODUCED | U29 | hygiene-3D-NET |
| B | B6 | 3D-Java | FILE_FORMATS.md has duplicate glTF/FBX sections with opposite status | NEW | REPRODUCED | U30 | fileformats-3D-Java |
| B | B7 | 3D-Java | Published 26.5.0 jar ships stub OBJ/glTF/FBX loaders (README line 587 discloses it) | NEW | REPRODUCED | U33 (do not file: disclosed) | jar-stubs-3D-Java |
| B | B8 | 3D-Java | README refers to an "Upstream Issues" section that does not exist | NEW | REPRODUCED | U32 | fileformats-3D-Java |
| B | B9 | 3D-Java | Only workflow skips tests (-DskipTests) | NEW | REPRODUCED | U31 | fileformats-3D-Java |
| B | B10 | 3D-Python | Scene.save() to .obj raises TypeError (B also lists the stream NotImplementedError) | ALREADY_COVERED | CONFIRMED 2026-10-09 | existing 094c4163 (the stream variant was not re-verified here) | - |
| B | B11 | 3D-Python | setup.py url returns 404 | NEW | REPRODUCED | U34 | seturl-3D-Python |
| B | B12 | 3D-Python | unittest discover fails on a fresh clone (examples/ gitignored) | NEW | REPRODUCED | U35 | unittest-3D-Python |
| B | B13 | Cells-.NET | README Chart.Name = ... (CS0200) | ALREADY_COVERED | CONFIRMED 2026-10-09 | existing 7e755ed8 | - |
| B | B14 | Cells-.NET | Additional Examples omit `using Aspose.Cells_FOSS;` | NEW | NOT_A_DEFECT | dropped: the blocks continue the Quick Start and claim nothing | - |
| B | B15 | Cells-.NET | agents.md references a missing RELEASE_NOTES_V26.5.0.md | NEW | REPRODUCED | U50 | cells-net-agents |
| B | B16 | Cells-TS | tsc --noEmit reports 3 type errors | ALREADY_COVERED | CONFIRMED 2026-10-09 | existing c04f74bf | - |
| B | B17 | Cells-TS | index.ts / examples fail: outputfiles/ missing, saves not awaited | NEW | NOT_REPRODUCED | dropped: npm start creates outputfiles/ and exits 0 | start-Cells-TS |
| B | B18 | Cells-TS | LICENSE only under License/; package.json lacks metadata | NEW | REPRODUCED | U04 and U48 | license-Cells-TS |
| B | B19 | Cells-TS | README API table has placeholder descriptions (draft said ~50; measured 24) | NEW | REPRODUCED | U48 | start-Cells-TS |
| B | B20 | Email-.NET | csproj 0.1.0 / CHANGELOG vs NuGet 26.7.0 | NEW | REPRODUCED | U26 | nuget-Email-NET |
| B | B21 | Email-.NET | examples/README.md uses non-existent csharp/ paths | NEW | REPRODUCED | U25 | paths-Email-NET |
| B | B22 | Email-Cpp | examples/README.md uses non-existent cpp/ paths | NEW | REPRODUCED | U24 | paths-Email-Cpp |
| B | B23 | Email-Python | SECURITY.md says "package wrapper" (nit) | NEW | NOT_ATTEMPTED | dropped: wording nit | - |
| B | B24 | HTML-Python | build-backend "setuptools.backends.legacy:build" does not exist | ALREADY_COVERED | CONFIRMED 2026-10-09 | existing ae9f06b9 | w3c-fixture-HTML-Python |
| B | B25 | HTML-Python | tests/test_css/w3c is missing: pytest fails at collection | NEW | REPRODUCED | U36 | w3c-fixture-HTML-Python |
| B | B26 | Page-Python | pip install . fails: local/Version.txt is gitignored | NEW | REPRODUCED | U37 | version-txt-Page-Python |
| B | B27 | Page-Python | mcp.server.run() raises TypeError | NEW | REPRODUCED | U38 | mcp-run-Page-Python |
| B | B28 | Page-Python | Two tests import a missing top-level tools package | NEW | REPRODUCED | U39 | tools-package-Page-Python |
| B | B29 | Page-Python | PyPI license/urls null; repository size 637 MB | NEW | NOT_ATTEMPTED | dropped: informational | - |
| B | B30 | Words-.NET | README "landing soon" for a published package; 615 vs 617 type counts | NEW | REPRODUCED | U40 | nuget-Words-NET |
| B | B31 | Words-.NET | Repository size about 560 MB | NEW | NOT_ATTEMPTED | dropped: informational | - |
| C | C1 | Cells-Go | README formula list, missing APIs, stray heading | NEW | REPRODUCED | U41 | stale-Cells-Go |
| C | C2 | Cells-Go | Generated CSV output committed | NEW | REPRODUCED | U42 | stale-Cells-Go |
| C | C3 | Font-Python | pip install "aspose-font[mcp]": no such distribution on PyPI | WEAKER_THAN_EXISTING | CONFIRMED 2026-10-09 | existing a241746e (carries the PyPI 404 and the pip failure; the C draft adds nothing) | tags-Font-Python |
| C | C4 | Font-Python | pyproject version 1.0.0 vs release tags 26.x | NEW | REPRODUCED | U49 | tags-Font-Python |
| C | C5 | Imaging-.NET | csproj RepositoryUrl/PackageProjectUrl use the old repository name | NEW | REPRODUCED | U45 | imaging-recheck |
| C | C6 | Imaging-.NET | Package not on NuGet / README install command | ALREADY_COVERED | STALE: README no longer claims it (head moved) | existing 2c99dc76: needs FIXED_OR_CHANGED re-verification | imaging-recheck |
| C | C7 | Note-Python | README Quick Start crashes: page.Title is None | NEW | REPRODUCED | HANDOFF 6532670d | quickstart-Note-Python |
| C | C8 | PDF-Python | Library writes INFO lines to stdout (engine/logging.py) | NEW | REPRODUCED | U44 | stdout-logging-PDF-Python |
| C | C9 | PDF-Cpp | README TIFF snippet: PageCollection incomplete | NEW | REPRODUCED | HANDOFF f49213f4 | snippets-PDF-Cpp |
| C | C10 | PDF-Cpp | README create-from-scratch snippet: Paragraphs/ArtifactCollection incomplete | NEW | REPRODUCED | HANDOFF a1a661ef | snippets-PDF-Cpp |
| C | C11 | PDF-Java | README/limitations.md list XLSX, Markdown, DOCX conversion as unsupported | NEW | REPRODUCED | U43 | limitations-PDF-Java |
| C | C12 | Slides-Cpp | 6 README snippets lack slide.h | NEW | REPRODUCED | HANDOFF 8b8b2cae | snippets-Slides-Cpp |
| C | C13 | Slides-Python | PyPI 26.8.0 lacks Hyperlink (README line 134 discloses it) | NEW | REPRODUCED | U47 (do not file: disclosed) | pypi-Slides-Python |
| D | D1 | 3D-TS | No LICENSE file (package.json declares MIT) | NEW | REPRODUCED | U05 | license-3D-TS |
| D | D2 | 3D-TS | package.json main/types broken; adm-zip only a devDependency | NEW | REPRODUCED | U06 (and R2) | node-3D-TS |
| D | D3 | 3D-TS | npm run lint: no ESLint config | NEW | REPRODUCED | U07 | node-3D-TS |
| D | D4 | 3D-TS | npx jest: 4 of 97 tests fail | NEW | REPRODUCED | U08 | node-3D-TS |
| D | D5 | 3D-TS | BC-02 npm 404 handoff (jargon body; recorded NOT_A_DEFECT) | SUPERSEDES_EXISTING | REPRODUCED | R2 replaces it; the old handoff stays NOT_A_DEFECT | npm-registry-3D-TS |
| D | D6 | GIS-.NET | Library does not compile: 369 errors, 41 types declared nowhere | NEW | REPRODUCED | U51 | build-GIS-NET |
| D | D7 | GIS-.NET | No README, no LICENSE, no csproj package metadata | NEW | REPRODUCED | U51 (same draft) | license-GIS |
| D | D8 | GIS-.NET | 14 obj/ files tracked, no obj/bin ignore rule | NEW | REPRODUCED | U09 | build-GIS-NET |
| D | D9 | PDF-TS | BC-02 npm 404 handoff (jargon body; recorded NOT_A_DEFECT) | ALREADY_COVERED | NOT_A_DEFECT confirmed (404 x3, README documents source install) | withdraw (R3); no replacement | npm-registry-PDF-TS |
| D | D10 | PSD-.NET | csproj placeholders: yourorg URLs, Authors SID | NEW | REPRODUCED | U10 | placeholders-PSD-NET |
| D | D11 | PSD-.NET | No LICENSE file | ALREADY_COVERED | REPRODUCED | open upstream issue #5; not re-drafted | license-PSD-NET |
| D | D12 | PSD-Python | No pyproject.toml, 2-line README, empty __init__ | NEW | REPRODUCED | U11 | psdpy-structure |
| D | D13 | PSD-Python | Generated MSBuild obj/ files committed as .py | NEW | REPRODUCED | U12 | psdpy-structure |
| D | D14 | PSD-Python | Plain pytest collects no tests (modules named *tests.py) | NEW | REPRODUCED | U13 | pytest-PSD-Python |
| D | D15 | PSD-Python | No LICENSE file | ALREADY_COVERED | REPRODUCED | open upstream issue #4; not re-drafted | license-PSD-Py |
| D | D16 | TeX-Python | 102 of 119 .py files fail ast.parse (existing handoff says 35 of 45) | SUPERSEDES_EXISTING | REPRODUCED | R1 replaces it | ast-TeX-Python |

## Drops (not softened, not carried forward)

- A15 Slides-Java: getMasters().addClone silently dropped (draft: unverified, no JDK) -- NOT_ATTEMPTED; dropped: needs a JDK 21 build; upstream README Scope already discloses it.
- A17 Words-Python: requires-python <3.13 blocks Python 3.13 -- REPRODUCED; dropped: an observation / feature request, not a defect (log kept).
- B14 Cells-.NET: Additional Examples omit `using Aspose.Cells_FOSS;` -- NOT_A_DEFECT; dropped: the blocks continue the Quick Start and claim nothing.
- B17 Cells-TS: index.ts / examples fail: outputfiles/ missing, saves not awaited -- NOT_REPRODUCED; dropped: npm start creates outputfiles/ and exits 0.
- B23 Email-Python: SECURITY.md says "package wrapper" (nit) -- NOT_ATTEMPTED; dropped: wording nit.
- B29 Page-Python: PyPI license/urls null; repository size 637 MB -- NOT_ATTEMPTED; dropped: informational.
- B31 Words-.NET: Repository size about 560 MB -- NOT_ATTEMPTED; dropped: informational.

## Findings the supervisor should act on

1. Imaging-.NET handoff `2c99dc76` is stale (its README claim no longer exists at the live head). Its `reverification.json` entry is changed in this PR from CONFIRMED to `FIXED_OR_CHANGED` at live head `6ebb2091ad016a46489bef65eaad0f1eb9843e1a` (the handoff text is not rewritten: its claim does not hold). Do not approve it.
2. The review's `A3` Cells-Cpp "possible issue, do not file until reproduced" reproduces, and the cause is a missing `#include` in the README snippet, not a library defect.
3. Three reproduced items are already disclosed by the maintainers (U33 3D-Java jar stubs, U46 Slides-Java 26.7.0, U47 Slides-Python PyPI lag). They are release requests; recommended not to file.
4. Review claims that did not hold or changed: Cells-TS `outputfiles/` missing (not reproduced: `npm start` works), PSD-Python "75 tests pass when named explicitly" (here they error on fixture paths; plain `pytest` collects 0 tests, which does reproduce), Cells-TS placeholder rows (24, not about 50), PSD-Python README size (67 bytes at LF, not 69).
5. `tests/components/issues/test_ledger.py::test_discover_and_load_the_real_backfilled_artifacts` asserts the number of committed handoffs (18); it is updated to 24 in this PR (a one-line, necessary change outside the lane's write paths: adding handoffs without it fails `scripts/ci_check.sh`).
6. `issue-readiness` reports `recheck: NOT replayable` for all of the new handoffs (the PyPI-only redetector); that is TC-ISS-02's gap, unchanged here.

## Method and environment

- Shallow clones (`git clone --depth 1`, `core.autocrlf=false`) of each default branch under the worktree's gitignored `runs/iss01/`; Page and Words-.NET as blobless sparse clones (very large test data).
- Native: Python 3.13.15 (venvs per repository), .NET SDK 10.0.401, git, gh (GET only). Docker: `node:22` (v22.23.3), `gcc:13` (g++ 13.5.0, libpugixml-dev 1.13 for Slides-Cpp), `rust:1` (cargo 1.99.0). No JDK/Maven in the lane: Java items were verified by file inspection and registry GETs.
- Every log header records the repository, the head sha the command ran against, the UTC time, the command and the exit code. Helper scripts that are too long for a one-liner are in `scripts/` (AST parse, jar class sizes, GIS missing-type list, container scripts for the C++, Node and Rust runs). `raw-logs/` contains no credential; `GH_TOKEN` was not set or printed (the `gh` CLI used its stored login for GET requests only).
- Probe sources (the README examples wrapped in `main()`) are in `scripts/` as `*.cpp`/`*.cs`.

## Not done / limits

- No Java build (no JDK): Slides-Java master-clone claim and the 3D-Java/Cells-Java items that need `mvn` were not executed.
- Existing handoffs were not re-run command by command; they were re-checked only for revision drift against the 2026-10-09 re-verification (Imaging-.NET showed a real change).
- Severity in the drafts is the lane's judgement and is not part of the handoff schema.
