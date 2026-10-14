authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Acceptance review, reseal run f69f75c7 (wave 3): summary of all 8 sealed rows

Protocol: TC-ACC-01 v1.1 (wt/lacc-acc01). Reviewer: independent, read-only. Scope: the 8 SEALED rows of runs/reseal/f69f75c7/results.jsonl (3D-.NET, 3D-Java, 3D-TypeScript, Cells-.NET, Cells-Java reviewed first; Note-Python, Slides-.NET, Slides-Python added in the completion pass). All eight bundles were READY_FOR_PROPOSAL, review ACCEPT (as returned ACCEPT), zero validation failures, no-op VERIFIED with 0 provider calls, revision == live head, README sha256 == manifest. The other 22 rows of the run are FAILED or INVALIDATED at the pipeline and have no sealed README.

Result: 0 AUTHORIZABLE, 0 FIX_REQUIRED, 8 DO_NOT_PROPOSE. In every case the live README was already conformant (or, for Slides-.NET, a richer bespoke document) and richer than the candidate, so a PR would degrade the repository. ACCEPT plus BC-01..BC-14 PASS detected none of the blocking items below.

## Verdict table

| # | Candidate | Verdict | minor_major | NET vs live | Claims checked / failed | CORE retention (verbatim) | Headline blocking findings |
|---|---|---|---|---|---|---|---|
| 1 | 3D .NET | DO_NOT_PROPOSE | MAJOR | mixed/worse | 24 / 6 | 58% | introduced: `dotnet build` at repo root fails (MSB1003); "18 test files" (real 16 .cs); 14+ API rows with holes; inherited: U3D/RVM/AMF/HTML5 read/write claims false, NurbsSurface.ToMesh/RenderFactory do not throw; dropped PLY/PDF/Draco/3MF limitations and dev deps |
| 2 | 3D Java | DO_NOT_PROPOSE | MAJOR | worse | 20 / 4 | 49% | introduced: invented audience, "other 3D formats" contradicts Scope (STL only), package called a class + duplicated lead paragraph; dropped 5 repo-doc links, limitations (PbrSpecularMaterial...), Maven badge, Kotlin DSL block |
| 3 | Cells .NET | DO_NOT_PROPOSE | MAJOR | worse | 15 / 1 (+4 prose defects) | 76% | introduced: mangled Development paragraph (split code spans), Scope list rendered twice, ". it adds" fragment, raw member dump with dangling "table below", invented audience; dropped namespace/package-id note, capabilities |
| 4 | 3D TypeScript | DO_NOT_PROPOSE | MAJOR | worse | 18 / 4 | 39% | introduced: StepMode described wrongly, "33 test files" (32 + setup.ts), invented audience, Scope "saves to OBJ and glTF" contradicts capabilities; dropped 3MF + its runtime-dependency defect and six limitations |
| 5 | Cells Java | DO_NOT_PROPOSE | MAJOR | worse | 17 / 4 | 42% | introduced: "26.7.0 is the sole published version" (registry has 26.5.0 and 26.7.0), fence without language, ". it adds" fragment, invented audience, "38 test files" (23 test classes); dropped tables/shapes/names/hyperlinks capabilities |
| 6 | Note Python | DO_NOT_PROPOSE | MAJOR | worse | 21 / 7 | 71% | introduced: documented install drops the `[pdf]` extra so the first Quick Start example crashes (RuntimeError: PDF export requires reportlab, reproduced); "29 test files" (12 test modules); "distributed under the LicenseRef-Aspose-Split license" vs MIT; garbled API reference (headingless pasted fragments, orphan "All inherit from AsposeNoteError" with 1 of 6 exceptions); invented audience + "full commercial suite" |
| 7 | Slides .NET | DO_NOT_PROPOSE | MAJOR | worse | 20 / 7 | 28% | dropped the whole "What it cannot do" section (13 verified API gaps, 3 of 21 save formats written); 3 of 7 examples do not compile (`using Aspose.Slides.Foss.Drawing` dropped: CS0103 `Color`, CS0246 `PointF`); "139 test files" (121 with tests); "runs only on the net platform"; opening duplicated and pointing at a deleted section; GroupShape/IHyperlinkContainer (empty types) presented as features |
| 8 | Slides Python | DO_NOT_PROPOSE | MAJOR | worse | 22 / 8 | 42% | Scope bullet of 2,254 characters cut off mid-word with a Chinese character ("never strips content this库") after the same limitations stated once already; PyPI 26.8.0 lacks Hyperlink/strict properties documented, and the live "PyPI predates source" warning and `aspose` namespace-collision warning are dropped; Enterprise Edition paragraph missing; "create, read, modify, and convert"; `MarkdownExportType` called the dialects (it has 1 member; `Flavor` has 24); "55 test files" (44) |

Per-candidate records (in this directory): acc-w3-3d-net.md, acc-w3-3d-java.md, acc-w3-cells-net.md, acc-w3-3d-typescript.md, acc-w3-cells-java.md, acc-w3-note-python.md, acc-w3-slides-net.md, acc-w3-slides-python.md.

## Retention of live content (what survives verbatim)

Method (retention.py in accw3/, read-only): live and candidate README are split into sentences (prose outside fences/tables/headings), list items, unique link targets (absolute repo-file link == relative link) and fenced code blocks. Verbatim = whitespace-collapsed exact substring; reworded = best similarity >= 0.80 to a candidate unit of the same kind; lost = below 0.80. Table rows are supplemental (row key = first cell). The CORE figure pools the four requested kinds. Limits: "verbatim" is strict, so a legitimate light edit counts as reworded or lost; a near-duplicate block (Kotlin vs Groovy snippet) can be counted as reworded; justified drops (forum links, non-compiling examples, forbidden edition wording) are included in "lost". Lost items are listed per candidate in section 8 (older five) or section 2 (newer three) of each record.

| Candidate | sentences | list items | links | code blocks | CORE verbatim | CORE reworded | CORE lost | API row keys kept |
|---|---|---|---|---|---|---|---|---|
| 3D .NET | 16/45 (36%) | 20/37 (54%) | 26/27 (96%) | 8/11 (73%) | 70/120 (58%) | 6 | 44 (37%) | 292/296 (99%) |
| 3D Java | 15/39 (38%) | 20/54 (37%) | 24/35 (69%) | 9/12 (75%) | 68/140 (49%) | 10 | 62 (44%) | 268/269 (100%) |
| 3D TypeScript | 7/47 (15%) | 15/42 (36%) | 19/22 (86%) | 6/8 (75%) | 47/119 (39%) | 3 | 69 (58%) | 64/97 (66%) |
| Cells .NET | 7/23 (30%) | 81/100 (81%) | 24/26 (92%) | 12/15 (80%) | 124/164 (76%) | 4 | 36 (22%) | 99/101 (98%) |
| Cells Java | 4/42 (10%) | 13/37 (35%) | 24/30 (80%) | 8/9 (89%) | 49/118 (42%) | 6 | 63 (53%) | 183/186 (98%) |
| Note Python | 11/31 (35%) | 79/108 (73%) | 27/31 (87%) | 17/20 (85%) | 134/190 (71%) | 7 | 49 (26%) | 40/42 (95%) |
| Slides .NET | 15/81 (19%) | 2/23 (9%) | 9/24 (38%) | 15/18 (83%) | 41/146 (28%) | 3 | 102 (70%) | 0/46 (0%) |
| Slides Python | 14/73 (19%) | 54/151 (36%) | 30/34 (88%) | 17/19 (89%) | 115/277 (42%) | 12 | 150 (54%) | 267/267 (100%) |
| mean of 8 | 25% | 45% | 79% | 79% | 51% | | 45% lost | |

Reading: sentence-level prose is where almost everything is lost (mean 25% verbatim): the opening, the explanatory sentences that give the live README its voice and caveats, and every disclosed defect/limitation sentence. Code blocks and links survive best (79%); lost code blocks are mostly the mermaid diagram (rewritten by design), examples that do not compile upstream (correct drops: 3D-.NET node enumeration, Cells-.NET chart, TypeScript node enumeration, Note-Python Quick Start) and install variants. API tables survive by row key except where the extractor lost types (TypeScript 66%, Slides-.NET 0% because its tables were key/value limitation tables). The two worst retention cases (Slides .NET 28%, 3D TypeScript 39%) are the two with the richest, most defect-aware live READMEs.

## Universal defects (route to code), updated for all 8 (N = new in the completion pass)

1. U-AUDIENCE (6 of 8 invent an audience/use-case sentence: all but 3D-.NET and Slides-.NET, whose audience clause is restated from the live README; 5 of 8 add 'without a full commercial suite / commercial licensing' framing: 3D-Java, Cells-.NET, Note-Python, Slides-.NET, Slides-Python): no fact supports it, BC-04 does not cover sentence-level audience claims. Stage: S6 opening + BC-04 coverage; forbid edition-adjacent 'commercial' phrases in the opening.
2. U-COUNT (7 of 8): "N test files" counts non-test files: 29 (Note-Python: 12 test modules + 13 json + 1 pdf + helpers), 139 (Slides-.NET: csproj, pptx/jpg/png fixtures; 121 files with tests), 55 (Slides-Python: 44 test modules), plus the four earlier. Stage: fact extractor for build_test_asset counts; count only files with test declarations.
3. U-PARTIAL-PRESERVE / U-DEFER-IS-SILENT-LOSS (8 of 8; the channel is now identified, N): in the three new bundles every true loss was flagged by an advisory that does not block: NOT_CARRIED_BY_NAMED_SECTION (Note-Python unit 013 = the `[pdf]` extra install; Slides-Python 014/018 = the PyPI-predates-source and namespace-collision warnings), LEADIN_OF_WITHHELD_CONTENT (Slides-.NET 033 = the `using` block that makes examples compile), ENTERPRISE_NO_VERIFIED_TARGET (Slides-Python 117 = Enterprise paragraph), ENTERPRISE_NON_PROSE (Slides-.NET 083). Stage: validation/deferrals.py: these deferral classes must block or force a fallback render; BC-05/BC-08 item-level coverage of preserved lists.
4. U-LIMITATIONS-NOT-RENDERED (N, Slides-.NET; related 3D/TS): inherited limitations held in two-column tables ("Not in the public API", "Save formats") are VERIFIED_MOVE'd to Scope yet nothing renders, so the candidate lists only positive "supports ..." bullets; the API table then advertises empty types (GroupShape, IHyperlinkContainer) as features. Stage: composer: tabular limitations -> bullet rows; BC-05 must verify every row; limitations section must be non-empty of negatives.
5. U-EXAMPLE-USINGS (N, Slides-.NET): the example harness supplies usings (receipts: "usings supplied: using Aspose.Slides.Foss.Drawing"), the README prints none, and the standalone `using` block fails receipt CS5001 and is withheld; three examples then fail to compile as printed. Stage: BC-03/BC-06 example verification: every printed example must compile with only the usings printed in the README (print a using preamble).
6. U-TRUNCATION-LANG (N, Slides-Python): a rendered bullet is cut off mid-word and ends with a Chinese character after a 2,254-character run-on that restates five bullets already present. Stage: BC-07: reject units not ending in terminal punctuation, containing non-Latin scripts in an English README or exceeding a length bound; duplicate-content check between a VERIFIED_PRESERVE unit and authored units of the same section (also Cells-.NET).
7. U-VERSION-SKEW (N, Slides-Python): the registry release (PyPI 26.8.0) lacks documented source-only features (Hyperlink, strict property assignment, real POTX); the live README's caveat and git-install instruction were dropped. Stage: extractor: registry-vs-source skew fact (CHANGELOG [Unreleased], pyproject version vs registry latest); authoring must render the caveat when examples/API rely on source-only members.
8. U-FRAGMENT (5 of 8: Cells-.NET, Cells-Java, Slides-.NET, Slides-Python, 3D-Java): capability bullets that are fragments ("From byte arrays ...", "Such as outer shadow ..."), ". it adds" lower-case fragments, stray bullets (Slides-Python L63-66). Stage: composer sentence normalisation; BC-07.
9. U-ORPHAN-LIVE-FRAGMENT (N, generalises Cells-.NET "table below"): VERIFIED_PRESERVE paragraphs/lists emitted at the end of the nearest section without their heading or lead-in: Note-Python API reference (headingless lists, orphan "All inherit from ..."), Slides-.NET Examples ("Those three are this library's own namespaces", "Every example below" after the last example), Slides-Python Examples (chart note after the Import example) and Key Capabilities, Slides-.NET opening referencing a deleted "What it cannot do". Stage: composer placement of preserved units; dangling-reference check (text referring to a section/block the candidate does not contain).
10. U-DETAILED-REFERENCE (8 of 8): mechanical member dumps with tautological "Defined as `def ...`" bullets (26 in Slides-Python, 35 in Note-Python), `/` for unions, base-class/`as_i_*` internals, unsorted 264/516-row tables with internal types, tautological enum descriptions, garbage stubs ("### Foss"). Stage: S6 api_reference rendering.
11. U-CAPABILITY-FROM-CONSTANTS (2 of 8: 3D-.NET, TypeScript; also Slides-Python "MarkdownExportType dialects" = misnamed symbol N): capability/limitation facts derived from constants/greps instead of the dispatch registry; symbol roles confused (dialects are `Flavor`). Stage: extractor + symbol-role check.
12. U-LICENSE-ID (N, Note-Python): the pyproject SPDX LicenseRef identifier ("LicenseRef-Aspose-Split") is rendered as the licence next to an MIT LICENSE and MIT License section. Stage: licence fact must prefer the LICENSE file text and flag a conflict instead of rendering both.
13. U-CONTRADICTION (3 of 8: 3D-Java, TypeScript, Note-Python "39 ... covers all 37"): opening/scope/count sentences contradict other sections. Stage: reviewer/coherence pass.
14. U-REGISTRY-ONLY-VERSION (Cells-Java), U-BUILD-COMMAND (3D-.NET), U-DOC-COMMENT-HOLES (3D-.NET), U-FENCE-LANG (Cells-Java, Slides-.NET): unchanged from the first pass; U-FENCE-LANG now 2 of 8 (the C13 miss is advisory in both).

New compared with the first five: items 4, 5, 6, 7, 9 (as defined), 12, the identification of the deferral advisories as the silent-loss channel (item 3), and the Enterprise Edition paragraph being dropped as an advisory (Slides-Python).

## Positive observations (wave-3 trio)

- The pipeline correctly drops live examples that do not compile or run: Note-Python Quick Start page-walk (AttributeError: `page.Title` is None for SimpleTable.one), plus the four from the first pass.
- All 11 Note-Python and all 14 Slides-Python printed examples run (Slides-Python against the PyPI 26.8.0 release); Slides-.NET Quick Start compiles.
- Slides-Python moves CONTRIBUTING/CHANGELOG/SECURITY/CODE_OF_CONDUCT into Documentation & Resources (an improvement over the live Development paragraph); Slides-.NET and Slides-Python drop forum/commercial-product links the live READMEs carry (correct).
- Zero-call no-op proofs are present for all eight.

## Upstream issues drafted (text only, in each record)

3D-.NET: dotnet test fails on clean checkout (53 of 183), NurbsSurface.ToMesh placeholder, committed logs, no root solution. TypeScript: no LICENSE file, package `main` points at non-existent dist/index.js, adm-zip devDependency needed at runtime by 3MF. Cells-.NET: Chart.Name read-only vs README example. Cells-Java: duplicate DiagnosticSeverity enums. 3D-Java: Torus/Pyramid.toMesh throw. Note-Python: README Quick Start raises AttributeError for SimpleTable.one; `license = "LicenseRef-Aspose-Split"` contradicts the MIT LICENSE. Slides-.NET: GroupShape and IHyperlinkContainer are empty public types with feature-implying XML docs. Slides-Python: PyPI 26.8.0 differs from the documented API (Hyperlink, strict property assignment) until the next release.

## Environment caveats

An Application Control policy on the review machine blocks loading unsigned managed assemblies from the scratch directory, so no .NET example could be executed and the root `dotnet build` of Slides-.NET could not be confirmed (Release build of the library csproj succeeded; examples were compile-checked). No JDK was available for the Java records. Python registry installs and example runs were done in throw-away venvs.
