authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# README correction approach: measured on 10 live READMEs

Read-only analysis lane. Date 2026-10-11. No tracked file edited, nothing pushed, no write to any Aspose repository
(shallow clones, GET-only API calls, package registries read-only). Working files: `scratchpad/corr/`
(clones, scripts, `patched/*.ABC.diff`, `patched/*.live.md`).

## 1. Answer

Yes. Keeping the maintainers' README and changing only what a clone/registry check proves wrong, stale or missing
delivers more value than replacing it, on this evidence:

| Measure (10 repos) | Regenerated candidate | Minimal correction patch |
|---|---|---|
| Lines changed vs live (+/-), mean / median | 702 / 560 (README.patch, 2 to 16 hunks) | 12.5 / 9.5 (1 to 8 hunks) |
| Live lines kept verbatim | 40% mean (range 19% to 75%) | 99% mean |
| Net vs live (independent review, wave-3, 5 of 5) | worse (3D-.NET: mixed, leaning worse), DO_NOT_PROPOSE | no regression by construction: every edit carries evidence |
| Deterministic acceptance text predicates (12), fail instances | live 15, candidate 17 | patched 10 (all remaining = the banner link, section 7) |
| Repos where the result is a PR worth opening | 0 of 5 reviewed | 6 of 10 (60%) |

Share of the 10 where a correction PR is valuable AND safe: **6 of 10**
(3D-.NET, Cells-.NET, 3D-TypeScript, Cells-Go, Cells-Cpp, Page-Python).
- 3 of the 6 are reachable with detectors that already exist (Cells-.NET, 3D-TypeScript, Cells-Cpp: failing example,
  missing Dependencies section, non-public API row) plus a new apply layer.
- 3 need evidence the pipeline cannot produce today: a prose-claim audit against code (3D-.NET false format and
  "throws" claims; the formula and type list in Cells-Go) or running the documented build in a clean clone
  (Page-Python).
- 2 are marginal (3D-Java, Cells-Rust: 2 to 11 lines, style or wording), 2 need nothing (Cells-Java, Email-Python).

Why it works: the 10 live READMEs already carry the 10-section shell (section 4); the git history shows the same
shell arriving through README-refresh PRs under the owner's account ("docs: refresh README with verified content,
structure, and examples"). 29 of the 35 portfolio READMEs I fetched contain all ten headings. Regeneration therefore
re-authors content that is already conformant and keeps only about 40% of it; the genuine defects are few, local and
mostly checkable.

Recommendation: make correction the default mode for any live README that already has the shell (31 of 35,
including the two missing only Dependencies); keep regeneration/section-fill only for the 4 off-template READMEs
(Cells-Python, Font-Python, Slides-.NET, Words-.NET) and README-less/placeholder repositories. Phase 1 (about 11
working days) reaches 4 of the 6 valuable repos in reduced form (Cells-.NET, Cells-Cpp, Cells-Go markdown, 3D-TS).
Section 8 has the machinery inventory and effort.

## 2. Method, and what I could not verify

- Fresh `git clone --depth 1` at live head, into `scratchpad/corr/clones/`. Heads equal the sealed revisions for
  3D-.NET, 3D-Java, Cells-.NET, 3D-TypeScript, Cells-Java, Cells-Rust, Cells-Cpp, Email-Python, Page-Python.
  Cells-Go moved: sealed fa4e890e, head 99c789e9 (15 commits later), so its sealed facts are stale and I measured the
  clone directly.
- Repos: the 5 wave-3 repos plus Cells-Rust (Rust), Cells-Go (Go), Cells-Cpp (C++), Email-Python and Page-Python
  (Python). Blobs are LF (my CRLF working copies come from autocrlf); patches were built from `git show HEAD:README.md`.
- Checks run: registry reads (NuGet flat container, Maven metadata, npm registry, PyPI JSON, crates.io API, Go
  module proxy, NuGet package listing); link check of every URL (GET, redirects followed) and every relative
  target; in-page anchors; path-like code spans against the tree; API-table identifiers against source;
  counts recomputed; CI claims against workflow files; examples compiled where a toolchain exists (dotnet 10.0.401,
  g++ 16.2 MinGW); the documented Python source commands run in scratch venvs; the repo's own 12 deterministic
  acceptance text predicates (`review/acceptance/text_checks.py`) run on live READMEs, sealed candidates and patched
  copies.
- Not verified: no JDK/Maven, no Go, no Node here, so `mvn`, `go test`, `npm` commands and the TypeScript example fix
  were not executed (TS fix is by source reading: `controlPoints` lives on `Geometry.ts` L51, not `Entity`). Rust:
  `cargo build` not re-run; the sealed quick-start receipt says "COMPILED ... cargo 1.98.1" at the same revision.
  Claims in the 3D-TS and Go READMEs "confirmed by direct testing" (OBJ export, GLB export) were not re-run.
  For the 5 wave-3 repos I reproduced the headline items and otherwise rely on the acceptance reports
  (`acc-w3-*.md`), flagged "per acceptance" below.

## 3. Per-repo table

Tier A = verified false, stale or broken. B = verified clone information a template section lacks. C = mechanical
shell conformance (predicate-driven, no facts). Size = changed lines (+/-) of the minimal patch, with hunks.
"Sealed patch" = README.patch of the regenerated candidate.

| Repo (head) | Verified false / stale / broken (A) | Missing or thin sections (B) | Size A / A+B / A+B+C | Sealed patch | PR a maintainer would take? |
|---|---|---|---|---|---|
| 3D-.NET (52b0f00e) | 5 groups: U3D/RVM/AMF/HTML5 read-write claims (intro, Key Capabilities, 5 diagram nodes, RvmFormat row); `RenderFactory` "throws" (returns null); `NurbsSurface.ToMesh` "throws" (returns a z=0 grid); "core RVM import/export works"; example CS1503 | none missing; 3DS (works, tested) absent | 37 / 37 / 37, 8 hunks (2.9% of lines) | +499/-469 | Yes, small and quotable from `IOService.cs`; needs an audit step to produce |
| 3D-Java (3d2ed6be) | none false; Scope hides which primitives fail (Torus, Pyramid); API row `Stream` = "Created by lexchou on 12/14/2016."; 29 filler rows "Class with N methods"; "commercial On-Premise edition" | JUnit version (optional) | 4 / 6 / 11 | +214/-295 | Low value; style PR only |
| Cells-.NET (941814fd) | example `chart.Name = ...` CS0200; "pure managed code" while SkiaSharp 2.88.8 is a dependency | **Dependencies section missing** | 3 / 14 / 14 | +264/-138 | Yes |
| 3D-TypeScript (66cb26df) | example `node.entity.controlPoints` TS2339 | Native/System sub-section (optional) | 4 / 8 / 8 | +534/-305 | Yes (small); no Node here to re-run tsc |
| Cells-Java (c65329e7) | none | none | 0 / 0 / 2 | +260/-329 | No PR (fence language only) |
| Cells-Rust (1a6004af) | stale phrase "Once the repository is live..."; 63 of 213 API rows filler | none | 3 / 3 / 5 | +748/-570 | Low value |
| Cells-Go (99c789e9) | second H1 at L105 (and its nav entry); `<details>` opened L501 never closed, so Detailed Documentation, Constraints and **License** render collapsed; README matches v26.7.1 but not main: formula list (4 vs 22 functions), "14 public types" (28 exported on main), project tree misses 6 source files | thin: new capabilities (charts, conditional formatting, pivot tables, VBA) | 11 / 20 / 22, 6 hunks | +199/-184 | Yes for the markdown fixes; the stale-vs-main part needs a release-policy decision |
| Cells-Cpp (9f852d0f) | example fails without `#include ".../WorksheetCollection.h"` (reproduced); API table lists private `Workbook_Impl` (count 197 -> 196) | **Dependencies section missing** | 4 / 20 / 20, 5 hunks | +517/-504 | Yes |
| Email-Python (10a906b4) | none (`pip install -e .` + `unittest discover` run: 18 tests OK) | Dev-dependencies sub-section (optional; bucket is empty by pyproject) | 0 / 4 / 4 | +207/-257 | No PR |
| Page-Python (43cef367) | documented source build `python package.py build` and `make sync` fail on a clean clone: `local/Version.txt` is git-ignored (reproduced); 60 of 139 API rows filler | none | 2 / 2 / 2 | +194/-336 | Yes, 1 line, high impact |

## 4. The 10 template sections: live READMEs

ok = present and sufficient; THIN = present, a material verified item missing; MISSING; DEFECT = present but wrong
or broken. All 10 also have the Mermaid chain with Starting Points and Outputs, a Scope list and the Enterprise
Edition paragraph.

| Section | 3D-.NET | 3D-Java | Cells-.NET | 3D-TS | Cells-Java | Rust | Go | Cpp | Email-Py | Page-Py |
|---|---|---|---|---|---|---|---|---|---|---|
| At a Glance | DEFECT (U3D/RVM/AMF/HTML5 nodes) | ok | ok | ok | ok | ok | THIN (4-function formula node, stale) | ok | ok | ok |
| Key Capabilities | DEFECT (format sentence) | ok | DEFECT ("pure managed") | ok | ok | ok | THIN (no charts/CF/pivot/VBA on main) | ok | ok | ok |
| Installation | ok | ok | ok | ok | ok | ok | ok | ok | ok | DEFECT (source build) |
| Dependencies | ok | ok | **MISSING** | THIN (optional) | ok | ok | ok | **MISSING** | THIN (optional) | ok |
| Quick Start | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| API Reference | ok | THIN (29 filler, 1 residue) | ok | ok | ok | THIN (63 filler) | THIN (14 of 28 types on main) | THIN (1 private row, 5 odd ids) | ok | THIN (60 filler) |
| Documentation & Resources | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Scope and Limitations | DEFECT (3 false bullets) | THIN (Torus/Pyramid) | ok | ok | ok | ok | THIN (formula bullet) | ok | ok | ok |
| Development and Testing | ok (53/183 tests fail upstream) | ok | ok | ok | ok | ok (0 tests, disclosed) | DEFECT (License/Detailed Docs swallowed by `<details>`) | ok | ok | DEFECT (make sync) |
| License | ok | ok | ok | ok (no LICENSE file upstream) | ok | ok | DEFECT (inside unclosed details) | ok | ok | ok |

Missing sections with a ready fact source (acceptance reports did not flag these as false):
- Cells-.NET Dependencies: `dependency:skiasharp` = "SkiaSharp 2.88.8"; `package:target_framework` =
  "netstandard2.0;net8.0" (sealed bundle 941814fd; the acceptance report praises the SkiaSharp finding).
- Cells-Cpp Dependencies: sealed facts `dependency:none`, `package:cxx_standard` = 17, `package:cmake_minimum` = 3.16.
  GoogleTest v1.14.0 and the Windows-only static libraries are not facts; I took them from
  `Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt` and the published nupkg listing.
- 3D-Java JUnit: `dependency:development.org.junit.jupiter-junit-jupiter` = 5.10.0.
- 3D-.NET: nothing in facts.json fills the gap. The pipeline has no importer/exporter registry fact, which is exactly
  why the sealed candidate repeated the false format claims (acceptance U5).
- Cells-Go: the sealed bundle is at the old revision; the new exported types and 22 formula functions need a
  re-extraction at head.

## 5. Minimal patch versus regenerated candidate

| Repo | Live lines | Corrected (+/-) | Hunks | Sealed README.patch (+/-) | Hunks | Live lines kept in candidate |
|---|---|---|---|---|---|---|
| 3D-.NET | 630 | +18/-19 | 8 | +499/-469 | 7 | 28% |
| 3D-Java | 634 | +5/-6 | 4 | +214/-295 | 12 | 54% |
| Cells-.NET | 535 | +12/-2 | 3 | +264/-138 | 16 | 75% |
| 3D-TypeScript | 444 | +6/-2 | 2 | +534/-305 | 7 | 32% |
| Cells-Java | 537 | +1/-1 | 1 | +260/-329 | 9 | 39% |
| Cells-Rust | 717 | +2/-3 | 2 | +748/-570 | 7 | 23% |
| Cells-Go | 545 | +16/-6 | 6 | +199/-184 | 13 | 57% (old revision) |
| Cells-Cpp | 598 | +18/-2 | 5 | +517/-504 | 2 | 19% |
| Email-Python | 411 | +4/-0 | 1 | +207/-257 | 7 | 44% |
| Page-Python | 590 | +1/-1 | 1 | +194/-336 | 8 | 34% |

The diffs are in `scratchpad/corr/patched/<repo>.ABC.diff`; each edit is an exact-match replacement with its
evidence recorded in `make_patches.py`. The Rust, Cpp and Page sealed bundles are older seals from the main checkout;
the wave-3 five are the f69f75c7 bundles.

The authored-text exposure also shrinks: a correction adds about 12 lines per repo, mostly deterministic (a rendered
Dependencies section, an include line, a deleted line), against 180 to 730 new lines in a candidate (rendered and
LLM-composed together).
The defect classes the acceptance reviewer found in 5 of 5 candidates (invented audience, "N test files", ". it adds"
fragment, partial VERIFIED_PRESERVE, mechanical member dumps) all live in that authored text.

## 6. Evidence by repo

### 3D-.NET
False or stale, with evidence:
1. Format claims. README intro, Key Capabilities, 5 Mermaid nodes and the `RvmFormat` row say U3D is read and
   written, RVM geometry import/export works, AMF and HTML5 are exported.
   `src/main/.../Formats/IOService.cs` L59-66 `CreateImporter` and L80-87 `CreateExporter` register exactly OBJ, STL,
   glTF, FBX, 3MF, COLLADA, PLY, 3DS. `grep -rln "RvmReader|RvmWriter|U3dReader|U3DReader|AmfReader|Html5" src` returns
   only `Html5SaveOptions.cs`. `FileFormat.cs` L90 defines `Universal3D` as a constant only.
2. Scope: "`RenderFactory` ... throw `NotImplementedException`": every `RenderFactory.cs` method is `return null;`
   (L25, L33, ...).
3. Scope: "`NurbsSurface.ToMesh` throw[s] `NotImplementedException`": `NurbsSurface.cs` L45-90 builds a grid,
   comment L68 "For now, generate a simple grid", `var z = 0.0f;`.
4. Example "Enumerate a Scene's Node Hierarchy": `Scene.FromFile("input.fbx", FileFormat.FBX7400Binary)` does not
   compile (CS1503, `Scene.cs` L314 takes a `CancellationToken` third). My fix `Scene.FromFile("input.fbx")` builds
   (dotnet 10.0.401).
5. Not edited: "Release 26.2.0 notes" while NuGet has only 26.1.0 (`{"versions":["26.1.0"]}`) and the csproj says
   26.1.0; `dotnet test` fails 53 of 183 (per acceptance: 48 missing fixtures). Upstream issues, not README text.
Verified true: NuGet 26.1.0 and `--version 26.1.0`; zero `PackageReference`; MIT; 4 relative links, 12 external links
2xx; anchors resolve.
Why the pipeline missed 1 to 3: its facts record only the example failure (`example:003` CONTRADICTED); format and
"throws" prose is checked for fact membership, never against code.

### 3D-Java
No false claim found. Verified: Maven metadata lists only 26.5.0; Java 21 in pom; 266 table rows = "266 types";
PUBLISHING.md, docs/api-diff-26.1.0.md, docs/directory-structures.md, docs/foss-java-progress.md, FILE_FORMATS.md exist
(the sealed candidate dropped all five); the published-jar OBJ stub disclosure is accurate (acceptance: `ObjLoader`
790 B vs `StlLoader` 6046 B).
Fixable: Scope "A handful of primitive-shape classes..." versus `Torus.java:95` and `Pyramid.java:80`
(`throw new UnsupportedOperationException();`); `| Stream | Created by lexchou on 12/14/2016. |` (`Stream.java` L5-6);
29 rows "Class with N methods and M properties." (banned by contract section 2 row 14); intro "commercial
On-Premise edition" (predicate `edition_name` FAIL); Dependencies omit `junit.version` 5.10.0 (pom L43).

### Cells-.NET
1. Additional Examples "Create a Chart" ends `chart.Name = "Revenue";`. `Chart.cs` L47 `public string Name =>
   _model.Name;`. Reproduced: with the line, `error CS0200: Property or indexer 'Chart.Name' cannot be assigned to --
   it is read only`; without it, build succeeded.
2. Intro: "The library is pure managed code". `Aspose.Cells_FOSS.csproj` L52-53: `<!-- SkiaSharp powers the
   XLSX-to-PDF renderer ... --> <PackageReference Include="SkiaSharp" Version="2.88.8" />`. The live README has no
   Dependencies section at all.
Verified true: NuGet `Aspose.Cells.FOSS` = 26.5.0, 26.6.0, 26.7.0, 26.9.0 (csproj 26.9.0.0 resolves); 15 sample
projects listed all exist; root `.sln` present; 3 relative and 14 external links fine.

### 3D-TypeScript
1. Additional Examples L152 `node.entity.controlPoints.length` fails type-check, TS2339 (sealed receipt `example_002.ts(9,54)`);
   `controlPoints` is declared on `Geometry` (`entities/Geometry.ts` L51), `Mesh` is exported from the package index.
   Proposed fix `if (node.entity instanceof Mesh)`; not compiled here (no Node).
Verified true: `@aspose/3d` returns 404 on npm, so "not published" holds; `package.json` scripts build/test/typecheck/lint
exist; version 24.12.0; the README itself discloses the `main` -> `dist/index.js` mismatch, the runtime-only `adm-zip` and
the missing LICENSE file (all three are upstream defects, correctly described). The sealed candidate dropped 3MF and six
limitations that the live README carries.

### Cells-Java
Nothing wrong found. Verified: Maven metadata 26.5.0 and 26.7.0 (README's 26.7.0 is latest), Java 17, `junit` 5.10.2 and
`poi-ooxml` 5.3.0 in test scope (pom), `docs/apidocs`, `PUBLISHING.md`, `Agents.md`, `maven-central-release.yml`, 183
table rows = "183 public types". Only a tree fence without a language (L266).

### Cells-Rust
Nothing false. Verified: crates.io API 404 for `aspose-cells-foss-rust`, `aspose-cells-foss`, so "not yet published" is
true; every dependency version in the README matches `Cargo.toml`; 213 rows = "213 public types"; the CI description
matches `ci.yml` (fmt job, 4-OS matrix, samples on ubuntu, `cargo bench`) and `pages.yml`; "0 tests" true (no `#[test]`,
no `tests/`). Stale: "Once the repository is live at its real GitHub location" (it is). Quality: 63 filler rows
"Struct with N methods", and internal helper types (`XlsxWorkbookPicturesLoader`, ...) presented as the public surface.

### Cells-Go (head 99c789e9, sealed fa4e890e)
1. README L105 `# Requires **Go 1.24.5+** ...` is a second H1 (predicate `single_h1`: "2 H1 headings at lines [1, 105]");
   the generated Navigation links it (L18).
2. `<details>` opens at L223, L436, L501; `</details>` at L380, L458 only. Everything after L501 (Detailed
   Documentation, Constraints, License) renders inside the collapsed block.
3. Stale against main, accurate against the published module (Go proxy: `v26.7.0`, `v26.7.1`; `go get` works).
   `git show v26.7.1:aspose/cells_foss/formula_engine.go` has cases SUM, AVERAGE, MAX, MIN; head has 22 (adds ABS AND
   CONCAT COUNT COUNTIF IF LEFT LEN LOWER MID NOT OR POWER RIGHT ROUND SQRT UPPER VLOOKUP). Exported types: 14 at
   v26.7.1 (README table, "14 public types"), 28 at head (adds Chart, ChartSeries, ChartAnchor, ChartType,
   ConditionalFormatting(Rule), PivotTable, PivotDataField, VBAProject, errors, StreamOptions). Source files
   chart.go, conditional_format.go, pivot_table.go, macro.go, olecfb.go, errors.go are absent from the Project
   Structure tree. Chronology: 6fd9d1c (2026-10-01) added the extended formula engine, charts, pivot tables and VBA;
   the README was then touched only by merge clean-ups (516b2ad "fix merged issue.", 73eab2e "clean up README
   conflict markers", both 2026-10-01), which is the likely origin of the stray H1 and the unclosed `<details>`;
   99c789e9 (2026-10-02) added more. 15 commits separate the sealed revision from head. This is the drift case the
   monitor exists for.
4. The PNG example "fails" in the sealed receipt (`undefined: generateSmallPNG`) only because the snippet cites a
   helper it points to; not a defect.

### Cells-Cpp
1. Additional Example "Load an Existing Workbook and Read Cells" lacks `#include "aspose/cells_foss/WorksheetCollection.h"`.
   `g++ -std=c++17 -fsyntax-only`: `error: no match for 'operator[]' (operand types are
   'Aspose::Cells_FOSS::WorksheetCollection' and 'const char [9]')`; with the include it compiles
   (`WorksheetCollection.h` L44 `operator[](std::string_view)`).
2. API table: `Workbook_Impl` is `struct Impl;` (Workbook.h L172, private pimpl); three `*_Iterator` rows and two
   `DiagnosticSeverity-Aspose_Cells_FOSS(_Core)` rows are not identifiers in the source (6 of 197 rows).
3. No Dependencies section.
Verified true: NuGet `Aspose.Cells.Cpp.FOSS` 26.4.0, 26.4.1; the 26.4.1 nupkg holds
`build/native/.../lib/win_x86{,_64}/{Debug,Release}/aspose_cells_foss.lib` only (Windows-only claim true); CMake
`CXX_STANDARD 17`; GoogleTest `v1.14.0` FetchContent URL; no Comment/Chart/Picture headers (limitations true).

### Email-Python
Nothing false. PyPI `aspose-email-foss` = 26.3, `requires_python >=3.10`; CI matrix 3.10 to 3.13 on `master`;
release.yml fires on tags `v*`; 30 rows = "30 public types". Ran `pip install -e .` and
`python -m unittest discover -s tests -v` in a scratch venv: Ran 18 tests, OK. One snippet uses an undefined
`msg_path` (pipeline reports NameError; a placeholder, not counted).

### Page-Python
1. Installation `python package.py build`/`verify`: `setup.py` L36 and `package.py` L45 read `local/Version.txt`;
   `.gitignore` L9 is `local/`. Reproduced on a fresh clone: `setup.py --version` (setuptools in a scratch venv) and
   `package.version()` raise `FileNotFoundError: ...\local\Version.txt`. The README says the version "comes from
   local/Version.txt" and never says to create it. `make sync`/`make build` go through `uv` and the same `setup.py`, so
   they are expected to fail the same way (uv is not installed here; not run).
2. 60 of 139 API rows are mechanical filler.
Verified true: PyPI `aspose-page-foss` 26.9.0 requires `skia-python` (extras pypdf, pypdfium2, Pillow);
`ASPOSE_PAGE_RASTERIZER` read at `raster_writer.py` L65; Makefile targets sync/test/build/check; 139 rows = "139 types".
Counter-example for naive rules: the sealed run marked the MCP example CONTRADICTED (`ModuleNotFoundError: fastmcp`),
but the README documents `fastmcp` as an optional dependency, and the candidate then dropped the whole MCP section.

## 7. Cross-cutting findings

1. Contradicted example is not the same as false: of 7 live examples the verifiers marked CONTRADICTED across these
   bundles, 4 are real defects (3D-.NET, Cells-.NET, 3D-TS, Cells-Cpp) and 3 are not (Go helper snippet, Email
   undefined placeholder, Page optional dependency). Today the pipeline answers all 7 the same way, OMIT_UNSUPPORTED.
2. Banner: 32 of 35 live READMEs fail predicate `promotion_after_product` (banner image linked to products.aspose.org
   at line 5); the sealed candidates fail it too (acceptance criterion C01 NOT_MET). Contract section 2 row 3
   prescribes the link and the ratified profile penalises it. An owner decision, 1 line per README; it caps every
   approach below 30/30 until decided.
3. Other predicate failures in live READMEs: 9 READMEs fail the fence/spacing predicate (mostly an untyped fence around a
   directory tree), 1 second H1 (Go), 1 non-canonical edition name (3D-Java), 1 license-prose (Font-Python). 25 of 35
   pass every predicate except the banner rule.
4. Links: 0 broken in the 10 (every external URL 2xx, every relative target exists, 0 unresolved anchors); the
   `crates.io/` 404 is a bare-curl artefact (the API answers). So "broken links" contributes nothing here.
5. Published versus main: 3D-Java (jar stubs vs source), Cells-Go (v26.7.1 vs main) and 3D-TS (unpublished) show the
   live authors already separate "what you get from the registry" from "what is on main". A regenerated README that
   flattens to head loses that (3D-Java candidate: "other 3D formats" contradicting its own Scope). A correction mode
   needs this concept explicitly.
6. Portfolio (35 live READMEs fetched; GIS has none): 29 contain all ten headings, 2 only miss Dependencies (Cells-.NET,
   Cells-Cpp), 4 are off-template (Cells-Python 7 missing, Font-Python 9, Slides-.NET 6, Words-.NET 4).

## 8. Machinery: what exists, what is missing, effort

Effort is focused engineer-days for one lane, including the focused tests AGENTS.md requires; schema work needs an
owner-admitted work item.

Exists and reusable as is:
- Exact unit addressing: `evidence/facts/inherited.py` makes each block an `inherited_unit` fact whose value is the exact
  source lines, with line range and heading path in the evidence (markdown-it token stream; lists split per member).
- Dispositions: 8 classes in `reconciliation/dispositions.py`; across 38 sealed bundles: SUPERSEDE_REDUNDANT 1854
  (53%), VERIFIED_PRESERVE 777 (22%), OMIT_UNSUPPORTED 453, VERIFIED_MOVE 195, DEFER 93, VERIFIED_REWRITE 45,
  CORRECT_WITH_EVIDENCE **6 of 3486 (0.17%)**.
- `render_patch` (`composition/renderer.py` L1133) is a plain `difflib` unified diff of live to candidate, so a small
  edit set gives a small README.patch with no new code.
- `propose` / `propose_candidate` (`components/propose/effect.py`, `cli.py` `run_propose`) is content-agnostic: it
  writes exactly `README.md` from the sealed bundle, bound by `sha256(readme)`, source recheck, authorization record,
  presenter branch, idempotence. `--local-test-readme-file` already dry-runs arbitrary README text.
- Fact producers a corrector needs: example verifiers per ecosystem (CONTRADICTED facts with compiler output), link
  verification, install/registry observation (BC-02), dependency snapshot and the D-owned Dependencies renderer,
  public-symbol facts, `text_checks.py` predicates, seal, no-op proof, `monitor/drift.py` (DRIFTED triggers the
  Cells-Go case), independent review and acceptance profile.

Missing:
1. The correction itself. `CORRECT_WITH_EVIDENCE` has no replacement-text field (disposition schema: unit_id,
   disposition, destination_section, fact_ids, rationale) and is not in `placement.PLACED`; "the only stage a preserved
   unit is ever rewritten is anchor resolution" (placement.py docstring). Repair edits authored units only. There is no
   "edit span X to Y with evidence Z" artefact and no apply step.
2. Default direction. The reconciliation prompt supersedes any unit a deterministic or planned section covers, which is
   why 53% of live units are regenerated even when conformant. Correction mode must default to keep-in-place.
3. A baseline-relative validator: BC checks run on plan + content units; the live text has none, and the live README
   itself fails some (Go H1, fences). The rule must be "no new failure vs live, every changed line maps to an edit".
4. A prose-claim audit. Nothing checks a limitation, capability or format sentence against code. The 3D-.NET claims,
   the Go formula list and the Cells-.NET "pure managed" sentence were found only by independent acceptance review or
   by hand here. (Acceptance U5 in the summary is the same gap.)
5. Documented-command execution in a clean clone (Page-Python class). Only the primary install command is verified.
6. Published-versus-head model for claims (Go, 3D-Java).
7. PR body with the per-edit evidence table (current body is three metadata lines).
8. Counting/status semantics (does a correction bundle count in N/34?), invalidation scope table for a new bundle kind,
   schema changes (`schemas/`): owner admission.

Effort (working days):

| Phase | # | Item | Days | Notes |
|---|---|---|---|---|
| 1 | 1 | Edit ledger + apply engine on unit spans (exact-match, overlap, idempotent, README.patch) | 2.0 | uses existing unit facts and `render_patch` |
| 1 | 2 | Correction bundle kind: seal, manifest, invalidation inputs, status counting, schema | 2.5 | needs owner admission |
| 1 | 3 | Baseline-relative validation (no new failure vs live), diff budget, byte-preservation proof | 2.5 | `validation/registry.py` is 2262 lines built around plan/units |
| 1 | 4a | Deterministic detectors to typed edits: insert missing D-section (Dependencies, nav link), markdown fixes (H1, unclosed details, fence language, edition name), contradicted-example removal with triage (unbound variable or optional dependency = keep) | 3.0 | no LLM |
| 1 | 6a | PR body from the ledger (per-edit evidence table) | 1.0 | `propose` otherwise unchanged |
| 2 | 4b | API-row and count staleness vs symbol facts; project-tree path diff | 2.0 | no LLM |
| 2 | 5 | Example repair: bounded LLM fix, accepted only if the existing verifier compiles it | 3.0 | replaces removal with a fix |
| 2 | 6b | Diff-scoped independent review (reads about 20 lines, not about 600) | 2.0 | |
| 2 | 8 | Clean-clone execution of documented commands (static first: scripts, targets, paths, gitignored inputs) | 3.5 | Page-Python class |
| 2 | 9 | Published-vs-head claim model (registry versions vs tag diff) | 2.0 | Go, 3D-Java |
| 3 | 7 | Prose-claim audit: LLM with read-only repo tools; evidence must be a quote that exists at the cited file and lines; calibrate on the 10 repos with the acceptance ground truth | 6 to 8 | highest risk: precision decides whether findings become edits or advisory text |

Phase 1 = 11.0 days. Reaches Cells-.NET (Dependencies, broken example), Cells-Cpp (Dependencies, example removed rather
than fixed), Cells-Go (H1, `<details>`, fence), 3D-TS (broken example) and the tier-C fixes: 4 of the 6 valuable repos, in
reduced form, and each PR stands on its own.
Phase 2 = 12.5 days: example fixes instead of removals, the Cpp row, Go's stale-vs-main part, Page-Python.
Phase 3 = 6 to 8 days with real calibration risk; the only route to the 3D-.NET class (1 of 10, but the only one where
the live README states false capability facts).
Total about 30 days for one lane (range 29.5 to 31.5), about 3 calendar weeks with two lanes. Production-shaped proof
(the G6-W02 disposable live write) is already on the roadmap and is not counted.

## 9. Risks and decisions for the owner

1. Maintainer fit: the recent README PRs on all 10 repos are authored by `babar-raza` (the owner's account), so the
   reviewer of a correction PR is effectively the owner. Rust, Cpp and Email were last pushed in August 2026
   (Cpp 08-13, Rust 08-14, Email 08-15); Cells-Go on 2026-10-04.
2. Precision first: a wrong "correction" is worse than none. Rule: an edit ships only with machine-reproducible
   evidence (compiler output, registry JSON, grep line, predicate); otherwise it becomes an issue or advisory.
3. Banner policy (C01) and "Enterprise Edition" wording: decide once; both are 1-line edits across 32 of 35.
4. Release-versus-main policy for READMEs (Go): document main, document the release, or document both explicitly (my
   Go patch does the last, with "unreleased").
5. Upstream issues, not README text: 3D-.NET failing tests and committed logs, 3D-TS missing LICENSE and `main` path,
   Page-Python `local/Version.txt` (a committed default would fix it better than a README note), Cells-Java duplicate
   `DiagnosticSeverity`.
6. What stays regeneration: README-less or placeholder repos and the 4 off-template READMEs. For those, section
   insertion that keeps their existing content is still preferable to a rewrite.

## 10. Reproduce

`scratchpad/corr/`: `clones/` (live heads), `mech.py` (links), `scan.py` (paths, counts, versions, API ids),
`bundles.py` (facts and dispositions of sealed bundles), `textcheck.py` / `textcheck_all.py` (12 acceptance predicates),
`patchstat.py` (live vs candidate), `make_patches.py` (edits and diffs to `patched/`), `vfy3d/`, `vfycells/` (compiled
fixes), `readmes/` (35 portfolio READMEs).
