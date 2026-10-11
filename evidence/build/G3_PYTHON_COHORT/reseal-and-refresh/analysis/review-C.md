authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Review C: eleven DRIFTED candidates (read-only)

Date of review: 2026-10-10. Method: blobless clones of each upstream repo in the scratchpad `clones/` directory, `git log`/`git diff` between `candidates/<slug>/CURRENT` and current head, live README = README.md at head, claims checked against the head tree, and candidate code examples extracted from each sealed README and compiled or run against head (Go 1.24 / Maven+JDK 17 / gcc 13 via Docker; .NET SDK 10; Python 3.13 venvs). Nothing was written to GitHub or to the presenter checkout. Issue bodies below are text only.

Drift class key: (a) README-only / no effect, (b) version bump / release / CI chore, (c) code or API change that makes candidate claims false, (d) large restructure.

Cross-cutting findings (apply to most of the eleven):
1. In 9 of 11 bundles the reviewer's returned verdict was `REJECT_PRESENTATION` (Java: `REJECT_FACTUAL`) and was converted to `ACCEPT` in `review.json` (`verdict_as_returned` vs `verdict`); only PDF-Go and Slides-Python were natively `ACCEPT`. Many of the 12-18 advisories per bundle are genuine factual defects (wrong product name, invented version labels, false "not yet published", contradicted limitations). They are listed per candidate below. `validation.json` shows 11/11 checks PASS everywhere, so none of these defects is caught by the deterministic gate.
2. Forbidden/unsupported edition wording ("commercial edition", "commercial Aspose.X", invented list of what the commercial product adds) is present in Font, Imaging, Note, PDF-Go, .NET, PDF-Cpp, Java and Slides-Cpp. In 4 of them the invented claim contradicts the candidate's own capability list (PDF-Go, PDF-Cpp, Font, Slides-Cpp). Cells-Go, PDF-Python and Slides-Python only contain the licence boilerplate "commercial use" (allowed by MIT text), and have no Enterprise Edition paragraph at all.
3. "The suite covers N test files under `tests/`" counts every file under `tests/` including fixtures: PDF-Cpp says 976 (170 `.cpp`), Note says 27 (13 `.py`), Slides-Cpp 137 (126 matching test*.cpp). Systematic overstatement.
4. Product-name canonicalisation is wrong in the C++ candidates ("Aspose.PDF FOSS for Cpp", "Aspose.Slides FOSS for Cpp" vs upstream "for C++") and in PDF-Go / PDF-Python (H1 "Aspose PDF FOSS ..." vs upstream "Aspose.PDF FOSS ...").
5. Where upstream has already merged a README refresh (Imaging 2026-10-10, Slides-Python 2026-09-18, both by Babar Raza via "/readme-refresh ... Co-Authored-By Claude Sonnet 5"), the live README is longer and better than the sealed candidate.
6. The sealed READMEs state the install path as "published package" even when the registry release lags main (Cells-Go v26.7.1, PDF-Go v0.9.0, Slides-Python 26.8.0). A reseal at head must say which documented features are unreleased.
7. Process notes: parallel blobless clones left several of my scratch clones with a damaged index (`D`/`??` entries); I repaired them with `git reset --hard HEAD` inside the scratch clones only. The PDF-Go Docker build and example compile were re-run on the clean tree (still pass).

---

## 1. aspose-cells-foss/Aspose.Cells-FOSS-for-Go

Sealed `fa4e890e46` (2026-09-25 seal) -> head `99c789e917`, branch main.

Commits (15, 2026-09-27..10-02): refactor/optimize per AGENTS.md (850eeca); docs correct README/doc.go (9957a29); .gitignore; deprecate problematic APIs, add safe replacements (b83d2df); examples typed_access (1055c47); benchmarks, export NumToCol/ColToNum (5978d30); per-sheet Modified tracking for selective save (5606f48); "Delete empty placeholder files" (beeeb03); two commits whose messages are LLM chatter ("I'm happy to help craft a concise commit message...", "No changes detected - empty commit"); ISSUE-CELLSGO-307 and -308 "AI Matched": chart, pivot table, conditional formatting, DXF, VBA support, improved encryption, formula engine, streaming reader, tests; README conflict-marker cleanup (73eab2e).
Changed paths: 49 files, +5994/-646. New `aspose/cells_foss/{chart,pivot_table,conditional_format,macro,olecfb,errors}.go`; heavy edits to `workbook.go, worksheet.go, formula_engine.go, xmlsaver.go, xmlloader.go, crypto.go, csv_handler.go, streaming_reader.go`; new `examples/typed_access`; ~20 new test files.
Drift class: (c), with (d)-scale additions.

Candidate claims now false or outdated (quotes):
- "The `CalculateFormula` function supports only SUM, AVERAGE, MAX, and MIN formulas; any other formula causes an error instead of being evaluated." At head `formula_engine.go` also implements CONCAT, IF, COUNTIF, VLOOKUP, ROUND, ABS, POWER, SQRT, LEN, LEFT, RIGHT, MID, UPPER, LOWER, AND, OR, NOT, COUNT (the sealed revision had only the four). Same stale claim in Key Capabilities and Scope.
- "The verified public surface has 14 types" / "all 14 public types": head adds `Chart, ChartSeries, ChartAnchor, PivotTable, PivotDataField, VBAProject, ConditionalFormatting, ConditionalFormattingRule` plus `Worksheet.AddChart/AddPivotTable/AddConditionalFormatting`, `Workbook.SetVBAProject/GetVBAProject`, `StreamingReader.ProcessRowsWithFilter/Range/Columns`, `Workbook.CheckPassword`. Nothing of this is documented by the candidate (nor by the upstream README).
- "The suite covers 12 test files under `tests/`": now 23 entries.
- Never supported by any fact (grep of facts/content_units/plan finds nothing): "Aspose.Cells FOSS for Go provides a lightweight, open-source wrapper around the Aspose.Cells engine for Go". The library is a pure-Go ECMA-376 implementation; this sentence is false at the sealed revision too (flagged in advisory F05, not blocking).
- "12 test files" and "Verify the install: `go list ...`" are unsupported additions (advisories F03/F06).
Registry nuance: the published module is v26.7.0/v26.7.1 (proxy.golang.org; v26.7.1 is an ancestor of the sealed commit and differs from it by one file). So `go get .../v26` gives a version WITHOUT the charts/pivot/etc. A reseal must say these exist only on main.

Live README vs candidate: live (HEAD, 559 lines, still has the same `CalculateFormula` four-function text) is messier (a stray `# Requires Go 1.24.5+ ...` H1 inside Installation which also pollutes the nav list; nav list indented under the H1) but contains valuable content the candidate lacks: Project Structure tree, picture-embedding example, "Detailed Documentation"/"Constraints" lists. Candidate is cleaner but drops those and adds the false "wrapper" sentence. Overall: roughly equal, neither accurate for head.

validation/review/manifest: 11/11 PASS; review returned REJECT_PRESENTATION converted to ACCEPT; 14 advisories (Mermaid, details blocks, "A1-style" detail omitted, added "wrapper" paragraph, added "12 test files"). Examples.json: 8 EXECUTED, 1 NOT_VERIFIED (import-only), 1 FAILED (picture example needing `generateSmallPNG`, not rendered). READY_FOR_PROPOSAL, no-op proof OK.

Spot checks against head (all done in clone):
1. Go version: `go.mod` `go 1.24.5` - TRUE.
2. `go build ./...` and `go vet ./...` on the full module, plus `go vet` of examples basic/csv_export/csv_import/data_validation/formula/load_modify_save/picture/streaming/style/table/typed_access - all pass (Docker golang:1.24).
3. Encryption: `crypto.go` ECMA-376 Agile, SHA-512 spin, AES-256 - TRUE.
4. `ImportFromCSV(path, sheetName string, delimiter rune)`, `ExportToCSV(sheetIndex int, ...)`, `ProcessRows(sheetName, callback)` signatures - TRUE.
5. Picture formats png/jpeg - TRUE.
6. Formula functions "only 4" - FALSE at head (above). Type count 14 - FALSE. Test-file count 12 - FALSE.
7. LICENSE: MIT, "Copyright (c) 2026 Aspose.Cells FOSS Family", matches README badge/section - TRUE. Module published (proxy lists v26.7.0, v26.7.1).
Forbidden wording: none ("commercial use" only in licence boilerplate). No Enterprise Edition section.

Upstream defects (head):
- README formula-function list and Key Capabilities are stale vs code; new public APIs (Chart, PivotTable, ConditionalFormatting, VBA) undocumented.
- README structure: stray H1 "# Requires **Go 1.24.5+** ..." under Installation and malformed Navigation (nested under the title).
- Repo hygiene: `examples/outputfiles/employees.csv` and `exported.csv` are committed although the README says never to commit that directory; AI chatter as commit messages (6a3e9f4, cc0f097).
- Latest tag v26.7.1 (2026-07-26) predates the features on main; a user following "go get" never sees them.
Ready-to-file issue (text only):
```
Title: README is out of date: formula engine, new chart/pivot/conditional-format/VBA APIs, and malformed headings

README.md (main @ 99c789e) says CalculateFormula "supports SUM, AVERAGE, MAX, and MIN" (Key Capabilities, Scope and Limitations, At a Glance). aspose/cells_foss/formula_engine.go now also implements CONCAT, IF, COUNTIF, VLOOKUP, ROUND, ABS, POWER, SQRT, LEN, LEFT, RIGHT, MID, UPPER, LOWER, AND, OR, NOT and COUNT.
The README and docs/usage.md do not mention Worksheet.AddChart, AddPivotTable, AddConditionalFormatting, Workbook.SetVBAProject/GetVBAProject or the StreamingReader.ProcessRowsWith* variants added in 5606f48..99c789e.
Formatting: README line ~99 has "# Requires **Go 1.24.5+** ..." as a top-level heading inside "Installation", which also breaks the Navigation list.
Also: examples/outputfiles/*.csv are committed although README says not to commit that directory; the latest release tag is v26.7.1 so `go get .../v26` does not include any of the post-July features - consider cutting a release.
```
Verdict: **RESEAL_REQUIRED** (confidence high). The formula/type-count/test-count claims are false at head and a candidate that omits charts/pivots/VBA/conditional formatting misses a third of the product. Could not verify: pkg.go.dev rendering, tests run (`go test`) - only build/vet.

---

## 2. aspose-font-foss/Aspose.Font-FOSS-for-Python

Sealed `c520e3ebed` (seal 2026-10-05) -> head `adf4885a3a` (tag 26.10.2, "Release 26.10.2", 2026-10-09). One commit.
Changed paths: 149 files, +22871/-1992. src: new `autonomous.py, batch_workflow.py, capability.py, optimizer.py, performance.py, instances.py, variation.py, visual_proof.py, corpus_manifest.py, cff2/*, diagnostics/coverage.py, ci/*, perf/*`; `cli.py` +3244 lines; `web.py` +1074; `qa.py` +946; `preview.py` +744; `reporting.py` deleted (-764) and the `aspose-font-reporting` script removed from pyproject; ~60 new test files; website images removed; Dockerfile removed; README rewritten (+240/-167).
Drift class: (d) large feature restructure plus (b).

Candidate claims now false or incomplete:
- Opening: "It supports reading `.ttf` files and writing `.png`, `.svg`, and `.html` outputs." False at sealed and head: package description is "Pure-Python font library - TrueType, OpenType, CFF, Type1, WOFF, WOFF2"; head adds CFF2 variable-font instancing, WOFF2 export, `WebFontOptimizer`, CLI with many commands.
- Scope: "does not support direct manipulation of internal structures like _raw or `active_tuples`" and the "`FontConverter` class" framing is unsupported/odd (advisory F04/F05 call it contradicted by facts).
- Enterprise section: "These limitations don't apply to full-featured Aspose.Font - Enterprise Edition ... The commercial Aspose.Font - commercial edition extends this open-source offering with additional capabilities for variable font manipulation and web optimization workflows." Forbidden wording, and it contradicts the library's own headline features (variable fonts, web optimisation).
- Omits CLI (`aspose-font` entry point) and MCP server install (`pip install "aspose-font[mcp]"`) in Installation (advisories F02, F05).
- "package version 1.0.0" is true of pyproject, but upstream releases/tags are 26.10.2 (see defects).
- "29 test files" now 106 entries.

Live README vs candidate: live (559 lines, "Three Buyer Workflows", capability snapshot, Python API highlights, full CLI section, MCP server, development) is far richer and more useful but is marketing-styled with no standard header; candidate follows the template but is materially thinner (no CLI, no workflows tables) and wrong in the opening. Candidate = worse on content, better on structure.

validation/review: 11/11 PASS; returned REJECT_PRESENTATION -> ACCEPT; 12 advisories include real defects (F04 contradiction, F07 "enterprise section missing"/F06 wrong enterprise claim). Examples: 7 EXECUTED, 1 FAILED (`font.instantiate` ValueError, not rendered). `manifest.adopted` shows a prior adoption (classification factual).

Spot checks at head:
1. `requires-python >=3.10`, `mcp>=1.0`, dev extras `build>=1.2, pytest>=7.4, ruff>=0.4` - TRUE.
2. `pip install .` from a clone: succeeds (clean venv).
3. Quick Start 1 (`WebFontBuilder.build(... variable_mode="auto", include_woff=False)`; `bundle.manifest["export_mode"]`, `["subset"]["coverage"]["covered_count"]`) and Quick Start 2 (`FontQaReporter.build_package`, `.json_path/.html_path/.preview_path`) run successfully against `testdata/Roboto-VariableFont_wdth,wght.ttf` (output `static-subset-from-variable-default`, 194; qa-package paths).
4. Every `aspose_font.X.y` symbol named in the README resolves in src at head (only module name `aspose_font.subsetter` is not a def, it is a module) - TRUE.
5. "not yet published on PyPI": `https://pypi.org/pypi/aspose-font/json` -> 404 - TRUE.
6. LICENSE.txt is MIT, README links `LICENSE.txt` - TRUE.
7. "supports reading .ttf" only - FALSE.
Upstream defects:
- README (head) line ~539 tells users `pip install "aspose-font[mcp]"` but `aspose-font` does not exist on PyPI (404) and there is no base install section.
- pyproject `version = "1.0.0"` while git tags/releases are 26.10.2 (calendar versions) - version metadata mismatch.
- CHANGELOG "Unreleased" lists items already shipped in 26.x tags (changelog lags the release).
```
Title: README tells users to `pip install "aspose-font[mcp]"` but the package is not on PyPI; pyproject version (1.0.0) differs from release tags (26.10.2)

At main (adf4885): README.md line 539 instructs `pip install "aspose-font[mcp]"`. https://pypi.org/pypi/aspose-font/json returns 404, so the command fails. There is no "install from a clone" instruction (`pip install .` works and is the only verified path).
pyproject.toml has version = "1.0.0" while the repo is tagged 26.10.2/26.10.1/26.9.x and CHANGELOG.md keeps an "Unreleased" section describing features shipped in those tags. Please either publish to PyPI or change the install instructions, and align the package version with the release tags.
```
Verdict: **RESEAL_REQUIRED** (confidence high). Opening paragraph false, forbidden/contradicted enterprise wording, CLI/MCP and the v26.10 feature set absent. Not verified: the `Roboto` fonts' licence, MCP server run, Enterprise Edition link target.

---

## 3. aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET

Sealed `a7c7314b18` (seal 2026-10-04) -> head `6ebb2091ad`.
Commits: `5872b4a` (2026-10-10, #1) and `6ebb209` (2026-10-10, #2), both "Refresh README: verified examples and documentation links", author Babar Raza, "Co-authored-by: Claude Sonnet 5". Changed paths: README.md only (+251/-44). No code change.
Drift class: (a) README-only; but the new README is the better document.

Live README (300 lines) vs candidate (120 lines): live is accurate and complete: probe-only scope ("no rendering, editing, or format-conversion"), 14-format table with per-format capability, Quick Start with real calls, async examples, full member list (`ImageProbe.DetectFormat/Probe/ProbeFile/ProbeAsync/ProbeFileAsync`, `ImageInfo` ctor), Documentation & Resources, accurate Scope (non-placeable WMF, DICOM undefined length, CDR planned), Enterprise Edition paragraph, dev instructions, CI badge. Candidate is much worse and factually wrong:
- "enables developers to read, write, and convert raster images, vector graphics, and metafiles without requiring a commercial license ... format conversion, metadata inspection, and batch processing" - FALSE: the library only detects formats and reads headers (csproj description: "Zero-dependency image format detection and header probing ... without a full pixel decode").
- "Multi-page format support ... exposing each page as a distinct image layer for individual manipulation", "Robust error handling ... triggers predictable exceptions rather than crashes" (upstream: Probe never throws), "Extensible format support ... custom loaders and savers" - all invented/contradicted.
- "exposes the `Aspose.Imaging.Foss` class as its primary entry point ... loading, processing, and saving images ... sole public symbol"; "The verified public surface has 3 types" with a `### Foss` heading and "image transformation" - FALSE (public types: `ImageProbe`, `ImageInfo`, `ImageFormat`).
- Enterprise paragraph: "the commercial Aspose.Imaging for .NET adds advanced features, enterprise support, and additional format handling" and "without requiring a commercial license" - forbidden wording / unsupported.
- Requires `netstandard2.0` only (csproj multi-targets `netstandard2.0;net8.0`).
- "The suite covers 5 test files": tests/ has 5 files incl. helpers.

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT with 15 advisories that are mostly real factual defects (F02, F03, F04, F06, F07 above). Examples: 1 FAILED (`bytes` undefined, fragment) - none EXECUTED.

Spot checks (head): `ImageFormat` enum has 14 formats + Unknown - TRUE; csproj `TargetFrameworks netstandard2.0;net8.0`, zero PackageReference - TRUE; `dotnet build src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj -c Release` - 0 errors; `.github/workflows/ci.yml` and `release.yml` exist; LICENSE MIT "Copyright (c) 2026 Aspose" - TRUE; NuGet `aspose.imaging.foss` -> 404 (not published; the sealed install text "not yet published on NuGet" is TRUE and the live README correctly uses clone/ProjectReference); tests project targets net9.0.
Upstream defects (minor): `src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj` `RepositoryUrl`/`PackageProjectUrl` point to `aspose-imaging-foss/Aspose.Imaging.Foss` (old repo name; GitHub redirects to Aspose.Imaging-FOSS-for-.NET); `release.yml` pushes to NuGet on tag but no package exists yet; 65 CS1591 warnings (missing XML docs).
```
Title: csproj RepositoryUrl/PackageProjectUrl use the old repository name; package not on NuGet yet

src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj sets RepositoryUrl and PackageProjectUrl to https://github.com/aspose-imaging-foss/Aspose.Imaging.Foss, which is no longer the repository name (it only works through GitHub's rename redirect). Update both to .../Aspose.Imaging-FOSS-for-.NET. Also: .github/workflows/release.yml publishes on v*.*.* tags, but https://api.nuget.org/v3-flatcontainer/aspose.imaging.foss/index.json returns 404, i.e. nothing has been published yet; and the build emits 65 CS1591 missing-XML-comment warnings although GenerateDocumentationFile is on.
```
Verdict: **DO_NOT_PUSH** (confidence high). The live README is already comprehensive and accurate; the candidate would regress it and introduce false capability claims. Not verified: the Enterprise Edition and docs.aspose.org link targets, `dotnet test`.

---

## 4. aspose-note-foss/Aspose.Note-FOSS-for-Python

Sealed `41de2e8ab4` (seal 2026-09-17) -> head `17b5d7fe20`.
Commits (6): `91e4d2d` API Subset Compat Check agent (2026-03-26); `5c5eeae` TOON spec; `5388948` "Update package name to 'aspose-note-foss'" (2026-09-24); `e459eb5` legacy `aspose-note` redirect package (LICENSE/README/pyproject under `legacy/aspose-note/`); `0014dbe` best-effort parsing of truncated `.one` files (#4, 2026-10-09); `17b5d7f` decode TextExtendedAscii as cp1252 (2026-10-10).
Changed paths (15): `pyproject.toml` (name `aspose-note` -> `aspose-note-foss`, version `26.3.2` -> `26.9.0`), `README.md`, `examples/*`, `.github/workflows/publish-pypi.yml` (trusted publishing), `legacy/aspose-note/*`, `src/aspose/note/_internal/{onestore/parser.py,ms_one/loader.py}`, 2 new tests.
Drift class: (b) rename + version bump + two behavioural fixes. PyPI: `aspose-note-foss` 26.9.0 exists; `aspose-note` 26.9.0 is a stub "Renamed: this package is now aspose-note-foss".

Candidate statements now false/outdated:
- Opening: "Aspose.Note FOSS for Python version 26.3.2 enables ..." and Installation "Install the published package from PyPI (`aspose-note`, version 26.3.2): `pip install aspose-note`" - the install command now installs a deprecated empty stub; PyPI badge also points to `aspose-note`; both the current name and version are wrong. (The live README already says `pip install aspose-note-foss`, `pip install "aspose-note-foss[pdf]"`.)
- "raises specific exceptions like `FileCorruptedException` ... when handling malformed files": truncated files are now parsed best-effort (0014dbe), so truncated-file behaviour changed; not stated by the candidate but the generalisation is weaker now.
- Unsupported claim: "the commercial Aspose.Note for Python adds advanced features such as enhanced PDF export, batch processing, and support for additional file formats" - invented (the live README says Enterprise adds full read/write incl. writing OneNote back out, broader format conversion).
- "The verified public surface has 37 types" vs upstream/live "39 public types" (advisory F07).
- "The suite covers 27 test files under `tests/`": 27 is the file count of `tests/` at the sealed revision (including goldens); there are 13 `test_*.py` at seal, 12 at head.
- Duplicated limitation ("Writing back to `.one`..." appears twice).

Live README vs candidate: live (528 lines) is the better document: the same 10 sections plus a full Development and Testing (CI-equivalent unittest list, PDF golden tests, regeneration script), a License paragraph that names ReportLab BSD-3, an accurate Enterprise paragraph, and the corrected package name. Candidate drops all of that and renames nothing. Candidate = worse.

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT; 15 advisories, F01/F03/F07 real (version in opening, 37 vs 39 types). Examples: 11 EXECUTED, 1 FAILED (the Quick Start's first snippet, see defect below, which the candidate wisely did not render).

Spot checks at head: (1) `requires-python >=3.10`, optional `pdf = reportlab>=3.6`, `test-pdf = pypdf>=5.3, Pillow>=10.0, PyMuPDF>=1.25` - TRUE. (2) `pip install ".[pdf]"` then candidate Quick Start example 1 (`Document("SimpleTable.one").Save("out.pdf", SaveFormat.Pdf)`) - runs, writes a PDF. (3) Candidate image-extraction example against `3ImagesWithDifferentAlignment.one` - runs (images written). (4) `SaveFormat` only Pdf / `UnsupportedSaveFormatException` - consistent with live README. (5) LICENSE MIT "Aspose" - TRUE. (6) PyPI name/version - FALSE in candidate (above). (7) test file count - FALSE.
Upstream defects:
- README Quick Start example 1 crashes at head with `AttributeError: 'NoneType' object has no attribute 'TitleText'` on `testfiles/SimpleTable.one` (`page.Title` is None for untitled pages).
```
Title: README Quick Start crashes: page.Title is None for pages without a title

README.md "Quick Start" first example:
    doc = Document("SimpleTable.one")
    print(doc.DisplayName)
    for page in doc:
        print(page.Title.TitleText.Text)
With testfiles/SimpleTable.one at main (17b5d7f) this prints "SimpleTable" and then raises
    AttributeError: 'NoneType' object has no attribute 'TitleText'
because page.Title is None when the page has no title. Please guard it (e.g. `if page.Title and page.Title.TitleText: ...`) or use a fixture whose pages have titles.
```
- Root of the repo carries `[MS-ONE].pdf`, `[MS-ONESTORE].pdf` (specification PDFs) and a `sitecustomize.py`; the legacy stub package lives under `legacy/` - not defects per se.
Verdict: **RESEAL_REQUIRED** (confidence high). Install command and version are wrong; even after correcting those the candidate is thinner than the live README, so a reseal must start from the new head and keep the live Development and Testing content. Not verified: Enterprise Edition link, THIRD_PARTY_NOTICES content.

---

## 5. aspose-pdf-foss/Aspose-PDF-FOSS-for-Go

Sealed `286484d235` (seal 2026-09-23) -> head `cdf43df10c`, 24 commits (2026-09-21..09-30).
Highlights: AES-256 revision 5 read and wrong-password rejection on xref-stream PDFs (fda8651, 8957a6f); PDF417 barcode fields (7ea77e8, 1130bb7); `ConvertToPDFA(PDF/A-1)` now auto-flattens transparency (e9c65c5); FileAttachmentAnnotation AFRelationship and PDF/A-1 attachment sweep (b654ab2); `Optimize.UnembedFonts` (2cafb92, f66ab3e); graphical, side-by-side and diff-output document comparison (a60b54f, 65d2dfb); Tagged PDF /OBJR annotation references (3e023d1); showcase PDF regenerated 14 -> 20 pages.
Changed paths: 59 files, +7037/-165 (new `font_unembed.go, barcode_pdf417*.go, comparison_graphical.go, comparison_sidebyside.go, comparison_output*.go`, `third_party/APACHE-2.0.txt`, `tools/genpdf417`, edits to `pdfa_convert.go, tagged.go, validate_pdfa.go, xref_reconstruct.go, encrypt_aes256.go`).
Drift class: (c)+(d).

Candidate claims now false (quote):
- "`Document.ConvertToPDFA` ... does not flatten transparency itself (call `Document.FlattenTransparency` before converting to PDF/A-1)". Head `pdfa_convert.go` calls `d.FlattenTransparency()` inside `ConvertToPDFA` for part 1 (doc comment: "rasterizes any page using transparency for PDF/A-1").
- Barcode fields: candidate says form fields include "Form.AddBarcodeField" (fine) but does not know PDF417; Code128/QR only in older text.
- Not updated: comparison family (Text/Graphical/SideBySide + HTML/JSON/Markdown/PDF output generators), `Optimize.UnembedFonts`, AES-256 R5 read (the candidate's encryption bullet "AES-128 or AES-256" omits RC4, certificate encryption and R5 reading).
- Enterprise paragraph: "Aspose PDF FOSS for Go commercial edition extends functionality with advanced features such as digital signature validation, document protection, and commercial support." Forbidden wording and self-contradictory: the same candidate says the library already verifies digital signatures ("verify existing signatures"), encrypts, and redacts.
- "Releases run through the [lint workflow](.github/workflows/lint.yml)": wrong (lint.yml is a linter; there is also test.yml; releases are tags).
- H1 "Aspose PDF FOSS for Go" (upstream H1 "Aspose.PDF FOSS for Go"). The Documentation list repeats "Open an issue" twice.
- Install: `go get github.com/aspose-pdf-foss/aspose-pdf-foss-for-go` pulls v0.9.0 (tagged 2026-09-16); sealed already had 42 post-v0.9.0 commits, head 24 more, so none of the features above is in the published module.

Live README vs candidate: live (1045 lines) adds Feature Showcase, Project-structure-like detail, detailed sections per area (Encryption and Signing, Forms, Outlines, Attachments, JavaScript, Text/RTL, Vector/SVG, Annotations, Stamps, Validation, Tagged PDF, Rendering, HTML/SVG/Markdown, AI copilots, Text extraction), Constraints/Third-Party Notices, Limitations in detail. The candidate (817 lines) is shorter and loses the showcase, third-party notices and per-area narrative.

validation/review: 11/11 PASS; review ACCEPT as returned, 0 advisories; examples 5 EXECUTED + 1 NOT_VERIFIED. The claims above show a clean review does not imply factual currency.

Spot checks at head: (1) `go.mod` `go 1.24`, module path `github.com/aspose-pdf-foss/aspose-pdf-foss-for-go` - TRUE; proxy `@latest` = v0.9.0 - TRUE. (2) `go build ./...` + `go vet ./...` on the clean full tree - pass (Docker). (3) All 5 candidate Go snippets (Quick Start x2, table, AES-128 encrypt/`OpenStream`, `RenderImage`) compile against head (`go vet`). (4) `Document.Split/Append/Reorder/SetEncryption/SaveHTML/ConvertToPDFA` exist with the cited receivers - TRUE. (5) `EncryptionAlgAES128/AES256/RC4_128` - TRUE. (6) `ai` package has `Summary/Ocr/Chat/ImageDescription` copilots - TRUE. (7) LICENSE MIT, "Copyright (c) 2026 Aspose Pty Ltd" - TRUE. (8) ConvertToPDFA transparency statement - FALSE.
Upstream defects: none verified beyond release lag (24+42 commits unreleased). `CLAUDE.md` is tracked at the repo root (agent instructions in a public product repo; judgement call).
Verdict: **RESEAL_REQUIRED** (confidence high). One concrete false limitation plus forbidden/contradictory enterprise text; ≥5 notable new features missing. If resealed, state that comparison/PDF417/UnembedFonts are not in v0.9.0. Not verified: `go test ./...` (not run, long), AI copilots against a live endpoint, pkg.go.dev examples.

---

## 6. aspose-pdf-foss/Aspose-PDF-FOSS-for-Python

Sealed `580935ba0f` (seal 2026-09-25) -> head `8f0edbe693`, 39 commits (2026-10-01..10-09), all `feat(...)`/`fix(...)`.
Highlights: streaming read of attachments/signatures; encryption owner-password fix; PDF/A-4 `/Info`, attachments AF/mime fixes; CCITT decode; table drawing (`018d8b7`), list authoring, text blocks/justified flow, PDF/X five levels (`4f6c263`), shape text match, tagging decoration, facades task-shaped classes (`4ce296f`), forms styling, annotations typed subtypes, destinations, color (grey/ink), page boxes/resize, visible signatures (`a333b6b`), embed missing font, bookmark tree from headings, /P permission names, page import between documents (`8f0edbe`).
Changed paths: 179 files, +49051/-3277 (tests 287 -> 342 entries; `supported-features.md` +1588; `CHANGELOG.md` +1244; many `src/aspose_pdf/**`).
Drift class: (d) (a feature wave, but no sealed claim was falsified).

Candidate claims vs head: no claim could be shown false; version "0.1.0" still true (`_version.__release_version__ = "0.1.0"`); "not yet published on PyPI" still true (`aspose-pdf-foss-for-python` 404 on PyPI); python>=3.11, `cryptography>=50` (PyPI cryptography is 50.0.2), `asn1crypto>=1.5`, extras images/woff2/text-layout/fuzz/dev - all match `pyproject.toml`. But the candidate is incomplete and sloppy:
- H1 and all prose use "Aspose PDF FOSS for Python" (upstream "Aspose.PDF FOSS for Python"); advisory F01.
- Garbled bullet: "exporting entire documents or pages as SVG using `save_as_svg` or `save_as_svg` respectively".
- Dangling text at end of Development and Testing: "Activate the virtual environment and install the development extra, then run the same lint checks and tests CI runs:" followed by nothing (the commands were dropped).
- "The library is distributed under the MIT license and is version 0.1.0." (version in the opening flagged F02).
- No Enterprise Edition paragraph; no certificate encryption/signature/tables/shaping examples that the live README has (see below).

Live README vs candidate: live (1213 lines, same standard sections, Aspose.PDF name) carries many examples absent from the candidate: Encrypt for certificate recipients, Sign a document, Make the signature visible, Watermark on a layer, Build a table, Paths/graphics state, Put a missing font into the document, multi-script and complex-script text, plugin/batch workflow layer, detailed member reference for 9 areas. Candidate = worse (it lost valuable inherited content: advisory F07/F08 list exactly this).

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT; 18 advisories (F04 install lacks venv/dev extra, F06 missing first example, F07 omitted examples, F08 omitted member reference, F09 omitted limitations). Examples: 8 EXECUTED, 4 FAILED, 2 NEEDS_INPUT.

Spot checks at head (venv, `pip install ".[images]"`): (1) `import aspose_pdf; __version__` = 0.1.0. (2) Candidate Quick Start 1 (page_count/version/info) and 2 (`load_from`, `pages[0].save_as_image("page-1.png", dpi=144)`) run. (3) Additional examples (save_as_markdown, save_as_html(resources_directory=, split_into_pages=True), `to_markdown(pages=[0], markdown_format="CommonMark")`, SVG export, `FontSubstitutionOptions.system()` + `save_page_as_image`, `PdfExtractor`, `PdfFileEditor.concatenate`, `PdfLoadLimits`/`PdfResourceLimitException`) all run: "ALL OK". (4) Document methods named in Key Capabilities exist (`replace_text, redact_text, encrypt_for_recipients, validate_pdfa, validate_pdfua, auto_tag, optimize, merge, to_html, to_markdown, sign`). (5) LICENSE MIT "Aspose Pty Ltd" - TRUE. (6) "287 test files under `tests/`" is the entry count of tests/ at seal (342 at head), not test modules.
Upstream defects:
- `src/aspose_pdf/engine/logging.py` attaches a `logging.StreamHandler(sys.stdout)` at INFO level to the `aspose_pdf` logger at import time, so every `Document` close prints `<timestamp> [INFO] aspose_pdf: Document resources released.` to STDOUT. A library should not configure handlers; this corrupts CLI pipelines that print to stdout (verified: with stderr discarded the line is still printed).
```
Title: Library writes INFO log lines to stdout on import/Document close (engine/logging.py)

src/aspose_pdf/engine/logging.py (main @ 8f0edbe) does:
    _logger = logging.getLogger("aspose_pdf")
    if not _logger.handlers:
        _logger.setLevel(logging.INFO)
        _handler = logging.StreamHandler(sys.stdout)
        ...
        _logger.addHandler(_handler)
So merely using the library prints e.g. "2026-10-10 18:26:46,245 [INFO] aspose_pdf: Document resources released." to stdout every time a Document is closed:
    from aspose_pdf import Document
    with Document("input.pdf") as d: pass     # prints the INFO line on stdout
This breaks programs that write data to stdout. Library code should only add a NullHandler and leave configuration to the application (https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library).
```
Verdict: **RESEAL_REQUIRED** (confidence medium-high). Nothing sealed is false, but the candidate has a dangling sentence, wrong H1 and a large content regression against the live README; head added ~40 features. (If the product prefers a minimal-correction path instead of reseal: fix H1, the duplicated `save_as_svg`, the dangling sentence, add the venv/dev extra - that still leaves the content regression, so PUSH_AFTER_FIX is not recommended.) Not verified: signature/encryption flows with real certificates, PDF/A validation behaviour, 1.2k-line live README accuracy beyond sampling.

---

## 7. aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET

Sealed `d10e2c829e` (seal 2026-09-23; tree is the 2026-09-12 README refresh commit) -> head `10a363830f` ("Release 26.10.0", 2026-10-01). One commit.
Changed paths: 2004 files (1381 added, 798 modified, 5 deleted), +208063/-91016 (src: 2345 files; tests +dozens; docs: 18 files +1214/-467; README.md rewritten). `Aspose.Pdf.Foss.csproj`: `TargetFrameworks` now `netstandard2.0;net48;net8.0;net9.0;net10.0`, `<Version>26.10.0</Version>`, conditional extra PackageReferences for netstandard2.0/net48.
Drift class: (b)+(c)+(d).

Candidate claims now false (quote):
- "Install the published package from NuGet (`Aspose.PDF.FOSS`, version 26.9.0): `dotnet add package Aspose.PDF.FOSS`": NuGet now lists 26.6.0, 26.7.0, 26.8.0, 26.9.0, 26.10.0. The Quick Start also says "using `Aspose.PDF.FOSS` version 26.9.0 for net8.0".
- "The library supports .NET 8.0" (opening) and "Requires .NET `net8.0` (`TargetFramework` in `src/Aspose.Pdf.Foss.csproj`)" / "targeting .NET 8.0": csproj now has `TargetFrameworks` with netstandard2.0, net48, net8.0, net9.0, net10.0; live README badge: ".NET netstandard2.0 | net48 | net8+".
- Dependencies list "`System.Drawing.Common 8.0.0`" and "`SonarAnalyzer.CSharp`" only: for netstandard2.0/net48 head also needs System.Text.Json 8.0.5, System.Memory 4.5.5, System.Security.Cryptography.Pkcs 8.0.1, System.Text.Encoding.CodePages 8.0.0, Microsoft.Bcl.HashCode 6.0.0.
- "The verified public surface has 899 types", "128 test files" - both changed (tests/ rewritten; `docs/api-reference.md` +123/-52).
- Enterprise paragraph: "the commercial edition extends it with additional features, advanced rendering capabilities, and enterprise support" - forbidden wording (advisory F08 also wants a dedicated enterprise section).
- Scope bullets about `OcspSettings` "stored but not used", `PdfVersion` fix-ups, `ToUnicodeProcessingRules` limited: the types still exist in head, but 10 release notes' worth of signature/verification work (RFC 3161, chain checks) happened and I could not confirm these limitations still hold.
(Sealed vs live README: sealed-candidate "Dependencies" block also omitted the Windows-only caveat flagged in F05.)

Live README vs candidate: live README at head (updated for 26.10: multi-targets, redaction semantics, signature verification APIs `TryVerifySignature`, `SignaturesCompromiseDetector`, `UnsignedContentAbsorber`, `HiddenDataSanitizer`, `DictionaryEditor`, `OpenTypeFeatures`, barcode fields) is strictly ahead of the candidate on accuracy and breadth; its At-a-Glance diagram was turned into a PNG (mermaid removed), a style regression but harmless.

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT; 16 advisories (F04 PackageReference XML omitted, F06 invented version sentence, F07 type count "899" vs original "881" claimed contradictory, F08 limitations omitted). Examples: 11 EXECUTED, 1 FAILED (a form-option example using `Option.ExportValue`, not in the candidate).

Spot checks at head (dotnet 10.0.401): (1) csproj version/TFMs as above; (2) NuGet versions as above; (3) Candidate Quick Start (create doc, `TextFragment`, `Document.Open`, `TextAbsorber.Visit(existing.Pages[1])`, `Console.WriteLine(absorber.Text)`) builds and prints "Hello, World!" with a project reference to `src/Aspose.Pdf.Foss.csproj` (net10.0); (4) all 11 C# snippets of the candidate compile (wrapped in static methods): SvgDevice, link annotation, TextFragmentAbsorber, stamp annotation, replace, form fields, `Encrypt(... CryptoAlgorithm.AESx256)`, `HtmlLoadOptions`, `PngDevice(new Resolution(300))`, `PdfFileSignature.Sign` with `PKCS7` - 0 errors; (5) `OcspSettings.RequestTimeout` and `ToUnicodeProcessingRules` still exist; (6) LICENSE MIT "Copyright (c) 2026 Aspose Pty Ltd" - TRUE; (7) 128 test files / 899 types - not reproducible.
Upstream defects: none verified. (Observation: `docs/` are good; the README's PNG banner/at-a-glance now come from `docs/media/*.png` via raw.githubusercontent URLs on `main`.)
Verdict: **RESEAL_REQUIRED** (confidence high). Version, target frameworks and dependencies in the candidate are factually outdated at head and the library changed massively (class d). Not verified: `dotnet test` (not run), net48/netstandard2.0 builds, whether the OCSP/PdfVersion limitations are still true.

---

## 8. aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp

Sealed `888700a8e3` (seal 2026-09-17) -> head `4b83c9fec1`, 7 commits (2026-09-18..09-30): `c559fc3` README refresh (upstream); `57695cd` single entry header `aspose.pdf.foss.hpp`, stop leaking internals; `fc83027` release workflow, CHANGELOG, v1.0.0, CMake package export; `d81dfad` NuGet native package `Aspose.PDF.Cpp.FOSS` (x64/x86/ARM64); `f31c812` Release 1.0.1; `0a2abb1` ci artifact actions v7/v8; `4b83c9f` stop pushing to nuget.org from CI.
Changed paths: 33 files, +1967/-74 (new `include/aspose.pdf.foss.hpp`, `include/aspose/pdf/facades/*.hpp` forwarders, `nuget/*`, `cmake/aspose_pdf_fossConfig.cmake.in`, `CMakeLists.txt` +68, README +50/-9, CHANGELOG +131).
Drift class: (b)+(c): installation story and versioning changed.

Candidate claims now false:
- "`Aspose_PDF_FOSS` is not yet published on any package registry; build it from a source checkout instead": head README/NUGET: `Aspose.PDF.Cpp.FOSS` 1.0.1 is on NuGet (`https://api.nuget.org/v3-flatcontainer/aspose.pdf.cpp.foss/index.json` -> ["1.0.1"]), GitHub releases ship prebuilt archives (Linux x64 GCC 13, Windows x64 MSVC) with a CMake package; `find_package(aspose_pdf_foss 1.0 CONFIG REQUIRED)` and `target_link_libraries(... aspose_pdf_foss::aspose_pdf_foss)`.
- Installation is only `cmake -S . -B build` (no build step; advisory F02) and no `Requirements`/Build-from-source steps from the original.
- Version labels "Aspose.PDF FOSS for Cpp 1.0.0", "using Aspose_PDF_FOSS 1.0.0" in three example headings and the Quick Start: invented (project is 1.0.1 at head; the sealed README stated no version). These strings make the headings read as product-name noise.
- Name: "Aspose.PDF FOSS for Cpp", "Aspose.PDF for Cpp - Enterprise Edition" (canonical "C++").
- Scope/Enterprise: "Aspose.PDF commercial edition adds additional features such as advanced rendering, digital signing, and form handling not present in this open-source package" - forbidden wording and false: the same candidate lists digital signing (`PdfFileSignature`) and AcroForm fields as capabilities. Also "without commercial licensing" in the opening.
- Dependencies: lists `googletest`, `Python3` bare; upstream: googletest 1.14.0 via FetchContent (dev only), Python used by the font-embedding generator at build time.
- "The suite covers 976 test files" (170 .cpp).
Still true: C++20, CMake 3.20, XmpValue stubs always false (`xmp_value.hpp:47`), Standard-14 fallback covers 12 of 14, incremental `/Info` writer limitation (present in README at head).

Live README vs candidate: live (≈1050 lines): Visual Studio NuGet, release-archive and subdirectory install, requirements, Development Dependencies, Additional Examples table, Project Structure, detailed API tables. Candidate is clearly worse; the candidate's own advisories F05/F06/F08 list the lost sections.

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT; 15 advisories, F01/F04/F06/F07 above are real defects. Examples: 4 EXECUTED, 2 FAILED (incomplete type), 5 NOT_VERIFIED.

Spot checks at head: (1) `CMakeLists.txt`: `project(Aspose_PDF_FOSS VERSION 1.0.1)`, `CMAKE_CXX_STANDARD 20`, cmake 3.20 - TRUE. (2) NuGet package exists (1.0.1) and `nuget/README.md` lists encrypt/decrypt RC4-40/128 & AES-128/256, detached PKCS#7, facades - consistent. (3) All 4 candidate C++ snippets pass `g++-13 -std=c++20 -fsyntax-only -I include` against head headers (not linked). (4) `Aspose::Pdf::Permissions()`/`CryptoAlgorithm::AESx256` usage compiles. (5) LICENSE MIT "Copyright (c) 2026 Aspose Pty Ltd" - TRUE. (6) 976 test files - FALSE as a test-file count.
Upstream defects (verified on head README snippets, compiled with `g++ -fsyntax-only -Iinclude`):
```
Title: README snippets do not compile as written (missing includes)

Compiling the C++ snippets in README.md (main @ 4b83c9f) with `g++ -std=c++20 -fsyntax-only -Iinclude` shows:
 * the TIFF snippet (`Aspose::Pdf::Devices::TiffDevice tiff(...); tiff.Process(doc, 1, static_cast<int>(doc.Pages().Count()), tiffOut);`) fails with "invalid use of incomplete type 'class Aspose::Pdf::PageCollection'" - it needs `#include <aspose/pdf/page_collection.hpp>`;
 * the "create from scratch" snippet using `doc.Pages().Add()`, `Paragraphs()` and `Artifacts()` fails with incomplete types `Aspose::Pdf::Paragraphs` / `Aspose::Pdf::ArtifactCollection` - add the headers (or the single-entry `#include <aspose.pdf.foss.hpp>`).
Suggest the README snippets all start with `#include <aspose.pdf.foss.hpp>` now that the single-entry header exists.
```
Verdict: **RESEAL_REQUIRED** (confidence high). "Not published" is false at head, invented version labels, forbidden/contradictory enterprise text. Not verified: full CMake build/ctest (not run), NuGet package contents, Windows-only paths.

---

## 9. aspose-pdf-foss/Aspose.PDF-FOSS-for-Java

Sealed `db2d3f0622` (seal 2026-09-25) -> head `736cedaa29`. Commits: `2a49563` "PDF to XLSX conversion, PDF to Markdown conversion" (2026-10-05); `736ceda` "chore: release 26.9.0 (version bump, waitUntil=validated) (#11)" (2026-10-07).
Changed paths: 69 files, +12290/-237: new `org/aspose/pdf/sdm/xlsx/*` (XLSX writer/reader/formula translator ~3.5k lines), `sdm/markdown/SdmMarkdownWriter`, `PdfSdmReader`, TableAbsorber/TextFragment changes, ~12 new tests, `CHANGELOG.md` 26.9 section, `pom.xml` 26.9.0, README unchanged.
Drift class: (b)+(c).

Candidate claims now false:
- "version 26.8.0" in opening, Installation (`mvn dependency:get -Dartifact=org.aspose:aspose-pdf-foss:26.8.0`), Documentation list, Scope: Maven Central metadata shows latest/release 26.9.0 (versions 26.6.0, 26.8.0, 26.9.0).
- "OCR, conversion to non-PDF formats beyond HTML/XML, conversion from non-PDF formats beyond HTML ... are not supported": at head `SaveFormat.Xlsx`/`Excel` and `SaveFormat.Markdown` exist, `LoadFormat.Xlsx`/`Markdown` are added in 26.9; DOCX/DOC were already supported at the sealed revision (`docs/conversion.md`). The candidate's own Documentation list says "Document Conversion ... PDFs to other formats such as DOCX, HTML, and images", contradicting its Scope bullet. The false statement is inherited from README and docs/limitations.md (see defects).
- "The verified public surface has 1158 types": changed (new types), advisory F02 already disputed it vs original 1026.
- Enterprise paragraph: "the commercial edition extends these features with additional processing options, advanced rendering, and enterprise support" - forbidden wording.
- "Basic stream recompression works for resource optimization, but advanced strategies ... are limited" and "PDF/X validation and conversion lack dedicated test coverage": not re-verified at head.
- Candidate omits the Gradle install, `maven.compiler` detail, concurrency limitation (still included here), and the Maven compile/test/javadoc commands (F01-F08).

validation/review: 11/11 PASS but `review.json` returned **REJECT_FACTUAL** (F01 wrong version, F02 type count, F04 JUnit) and was converted to ACCEPT; 12 advisories. Examples: 9 EXECUTED. This is the one candidate where the reviewer's original verdict was a factual rejection.

Spot checks at head: (1) `pom.xml` version 26.9.0, `maven.compiler.source/target` 11, junit-jupiter 5.10.2 - consistent with candidate except version. (2) Maven Central metadata: latest 26.9.0 - candidate's 26.8.0 outdated. (3) `mvn -q -DskipTests compile` on the full tree (Docker maven:3.9-temurin-17) succeeds, and all 9 candidate Java snippets compile with `javac` against `target/classes` (wildcard `org.aspose.pdf.*` imports added for the snippets lacking imports). (4) `PdfFileSecurity.setAllowExceptions(false)` throws `UnsupportedOperationException` - TRUE. (5) thread-safety statement is in `docs/limitations.md` - TRUE. (6) LICENSE MIT "Copyright (c) 2001-2026 Aspose Pty Ltd" - TRUE. (7) conversion limitation - FALSE (above).
Upstream defects: README (lines ~1608-1610) and `docs/limitations.md` line 16 say "Conversion to non-PDF formats other than HTML/XML - DOCX, XLSX, PPTX, EPUB, MOBI, Markdown, ..." and "Conversion from non-PDF formats other than HTML - DOC, DOCX, XLSX, ..." are unsupported, while `docs/conversion.md` ("PDF <-> HTML, DOCX, XLSX, Markdown"), CHANGELOG 26.9 and `SaveFormat` say otherwise.
```
Title: README and docs/limitations.md list XLSX, Markdown and DOCX conversion as unsupported, but they are implemented

README.md (~line 1608) and docs/limitations.md (line 16) state that conversion to non-PDF formats other than HTML/XML (DOCX, XLSX, PPTX, EPUB, MOBI, Markdown, ...) and conversion from non-PDF formats other than HTML (DOC, DOCX, XLSX, ...) are out of scope. At main (736ceda):
 * docs/conversion.md documents PDF <-> HTML, DOCX, XLSX and Markdown;
 * CHANGELOG.md [26.9] adds SaveFormat.Xlsx/Excel, ExcelSaveOptions, LoadFormat.Xlsx, ExcelLoadOptions, SaveFormat.Markdown, MarkdownSaveOptions, LoadFormat.Markdown;
 * src/main/java/org/aspose/pdf/SaveFormat.java declares Xlsx and Markdown.
Please update the "Limitations/out of scope" lists so they only name formats that are truly unsupported (PPTX, EPUB, MOBI, LaTeX, ZUGFeRD, ...).
```
Verdict: **RESEAL_REQUIRED** (confidence high). Stale published version and a conversion-limitation claim that is false at head (and contradicted inside the candidate). Not verified: `mvn test`, javadoc, actual XLSX/Markdown output quality, 1158-type count.

---

## 10. aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp

Sealed `c41f8dddc4` (seal 2026-10-04) -> head `469ce77a07`.
Commits (3, 2026-04-02 authored by a contributor, merged 2026-10-06): `65cf349` "Remove wrongly placed nodiscard", `951b82c` "Fix nodiscards", merge `469ce77` (PR #1). `git rev-parse HEAD^{tree}` equals `c41f8dddc4^{tree}` (`ff2bac8c65...`): the two commits cancel out; `git diff c41f8dddc4 HEAD` is empty.
Drift class: (a): zero content change (merge commit changed the SHA only). The drift flag is spurious for content purposes.

Candidate vs live README (identical tree, so the live README = the README the candidate was built from): the candidate (423 lines) is much worse than the live README (884 lines).
Defects of the candidate (all independent of drift):
- H1 and prose "Aspose.Slides FOSS for Cpp" (canonical "C++").
- Installation: "`AsposeSlidesFoss` is not yet published on any package registry; build it from a source checkout instead": FALSE at the sealed revision too. The live README documents `Install-Package Aspose.Slides.Cpp.FOSS` (NuGet `aspose.slides.cpp.foss` exists, HTTP 200), FetchContent, installed CMake package. Advisory F04 flagged this and was not blocking.
- Dependencies: "Development Dependencies: AsposeSlidesFoss, googletest, GTest, miniz" (the library listing itself as a dependency; miniz is a private runtime link dependency; upstream: pugixml 1.14 and miniz 3.0.2 via FetchContent, googletest 1.15.2 test-only).
- Scope and Limitations is vacuous/circular: "The library exposes only the `Aspose.Slides.Foss` public symbol and does not provide access to internal implementation details..." (x3) instead of the real limitations (no rendering/conversion, unimplemented features, pugixml header leak).
- Enterprise paragraph: "the commercial edition extends functionality with advanced features such as digital signatures, watermarking, and enhanced export options" - forbidden wording, unsupported.
- "Third-Party Notices: See THIRD_PARTY_NOTICES." fine; "It covers all 234 verified public types ... It covers all 234 verified public types" duplicated sentence.
- "supporting formats such as PPTX as output" and "create, read, and convert PowerPoint presentations": the library does not convert.
- Key Capabilities "Embed images ... supporting common image formats" and "Export to PowerPoint formats" use generic phrasing not backed by specific symbols.
- Missing: charts/animations/text-frame etc. examples (live has 8 additional examples), NuGet/Windows requirements, Visual Studio v143 and stdcpp20 note, Project details.

validation/review: 11/11 PASS; REJECT_PRESENTATION -> ACCEPT; 16 advisories, F01-F07 real. Examples: 2 EXECUTED, 6 FAILED, 1 NOT_VERIFIED: the 6 failed ones are the upstream README's own examples (see defect).

Spot checks (head == sealed tree): (1) `CMakeLists.txt` `cmake_minimum_required 3.20`, `project(... VERSION 26.9.0)`, git tag `v26.9.0` - TRUE. (2) Candidate's 2 snippets compile with `g++-13 -std=c++20 -fsyntax-only` with `-Iinclude` and pugixml 1.14 headers - TRUE. (3) NuGet `Aspose.Slides.Cpp.FOSS` exists - candidate's "not published" FALSE. (4) pugixml/miniz as dependencies and googletest dev dep - TRUE (live README says so). (5) LICENSE MIT "Copyright (c) 2026 Aspose Pty Ltd" - TRUE. (6) "137 test files" is the number of files under tests/ (126 test*.cpp).
Upstream defects (verified): 6 of the 10 C++ snippets in the live README (the Quick Start and five of the Additional Examples; each uses `pres.slides()[0]`) do not compile as written because they use `pres.slides()[0]` but do not include `<Aspose/Slides/Foss/slide.h>` ("invalid use of incomplete type 'class Aspose::Slides::Foss::Slide'" under g++ 13 -std=c++20 with pugixml headers on the path).
```
Title: README C++ snippets fail to compile: missing #include <Aspose/Slides/Foss/slide.h>

Compiling the C++ examples in README.md (main @ 469ce77) with g++ 13 -std=c++20 -Iinclude (+ pugixml 1.14) fails for the Quick Start and five of the Additional Examples with:
    error: invalid use of incomplete type 'class Aspose::Slides::Foss::Slide'
because they call `auto& slide = pres.slides()[0];` but only include presentation.h/shape_type.h/auto_shape.h/save_format.h. Add `#include <Aspose/Slides/Foss/slide.h>` (and the other headers each snippet uses), or provide an umbrella header.
```
Verdict: **DO_NOT_PUSH** (confidence high): zero content drift; the candidate is a regression against the live README (false "not published", circular limitations, forbidden enterprise text, wrong name). A reseal at the same tree would not change this; fix the generator first. Not verified: building the full CMake project, the NuGet package contents, link-time behaviour.

---

## 11. aspose-slides-foss/Aspose.Slides-FOSS-for-Python

Sealed `becd199a77` (candidate sealed/adopted 2026-09-09, tree = 2026-08-28 merge) -> head `4e63447ba7`, 10 commits (2026-09-18..09-23): `a944320` README refresh (Babar Raza, "/readme-refresh", Co-Authored-By Claude Sonnet 5); `e1d389b` write `a:sp3d` children in schema order; `df10261` `a:bodyPr` children order; `8dd762d` insert `a:effectLst` at its schema position; `735551c` "Write transitions as PowerPoint does and replace an opened slide's transition"; `c5175f4` type container helpers; `64a4ad1` "Refuse unknown property assignments on presentations, slides, text, cells, transitions and links"; `010acc3` conformance floor 335 tests; `24c75b3`/`4e63447` changelog disclosures.
Changed paths: 24 files, +1519/-227: `README.md` (+877/-...: 456 -> 1013 lines), `CHANGELOG.md`, `SlideShowTransition.py`, `transition_mappings.py`, `child_order.py`, `EffectFormat.py`, `ThreeDFormat.py`, `TextFrameFormat.py` and the property-guard edits in ~9 classes, `.github/workflows/ci.yml`, conformance tests. `pyproject.toml` still `version = "26.8.0"`; PyPI still 26.8.0.
Drift class: (c)-light + (a): the upstream README already changed by the user's refresh tool; code changes mostly make previously-documented behaviour true (AttributeError on unknown properties was documented in the sealed README before the code did it).

Candidate claims vs head:
- Install: "Install the published package from PyPI (`aspose-slides-foss`, version 26.8.0): `pip install aspose-slides-foss`" is TRUE as a registry fact, but the candidate's hyperlink example ("Assign click and mouse-over hyperlinks to shapes": `from aspose.slides_foss import Hyperlink`) FAILS with the published 26.8.0 wheel: `ImportError: cannot import name 'Hyperlink' from 'aspose.slides_foss'` (verified by installing the 26.8.0 wheel in a fresh venv and running the snippet). The live README warns "The PyPI release predates the source tree behind this page ... hyperlinks ... and the six distinct PowerPoint save formats are not in that release ... install from the repository". The candidate omits that caveat, so a PyPI user following it hits ImportError. Also omitted: the `aspose` shared-namespace warning (installing it next to the commercial `aspose` package makes `aspose.slides_foss` unimportable).
- Scope: "Only seven `SaveFormat` values produce valid output files; fourteen others raise ValueError" - consistent with head (6 OOXML formats + `SaveFormat.MD`), but the candidate never mentions Markdown export as a capability although the upstream README (sealed and live) documents `SaveFormat.MD` with `MarkdownSaveOptions`/24 flavors (only listed in the API tables); live also says 74 chart types (verified `len(ChartType)==74`; sealed said 73).
- Scope: "Assigning to a property a shape or formatting object does not have raises `AttributeError`" - TRUE at head (64a4ad1), it was documentation ahead of code at the sealed revision.
- No Enterprise Edition paragraph, while the live README has one ("adds full non-PPTX export ... SmartArt and OLE ... VBA and digital signature handling, and commercial support").
- "The suite covers 52 test files" (entry count of tests/ at seal).

Live README vs candidate: live (1013 lines) is better: full 10-section template, Key Capabilities with specifics (74 chart types, hyperlinks, bullets, `NullableBool`), 14 titled examples incl. chart-from-scratch, Slide Transition, Export to Markdown; Installation with the PyPI-lag warning and shared-namespace warning; Scope with unimplemented-feature list; Enterprise paragraph. Candidate (1110 lines, mostly an API table dump) lacks the caveats. Candidate = worse on accuracy and install guidance.

validation/review: natively ACCEPT, 0 advisories, 11/11 PASS (the cleanest of the eleven); `manifest.adopted` shows a re-adoption (classification factual). Examples: 14 EXECUTED, 1 FAILED (Markdown subset example requiring 2+ slides).

Spot checks at head (venv from clone, plus the 26.8.0 wheel): (1) python>=3.10, `lxml>=4.9`, extras test (`pytest>=7`, `python-pptx>=1.0`) - TRUE. (2) Candidate Quick Start (create, save, reopen, `len(prs.slides)`) - runs at head. (3) All 14 candidate snippets run at head (only `picture.png` input missing, expected). (4) With the published 26.8.0 wheel: hyperlink snippet ImportError (above); the other snippets run. (5) Version 26.8.0 matches `pyproject.toml` and PyPI - TRUE. (6) LICENSE MIT "Copyright (c) 2026 Aspose Pty Ltd" - TRUE. (7) `len(ChartType)` 74 vs sealed text 73 - minor.
Upstream defects: the PyPI release (26.8.0) lacks features that the README examples use (hyperlinks, save formats); upstream README already states this. Suggest releasing 26.9.x.
```
Title: Publish a release: pip install aspose-slides-foss (26.8.0) lacks Hyperlink and other features used in README examples

README.md states "The PyPI release predates the source tree behind this page", and indeed `from aspose.slides_foss import Hyperlink` raises ImportError with the 26.8.0 wheel, while main has hyperlinks, the six PowerPoint save formats and (since 64a4ad1) AttributeError on unknown property assignment. Please cut and publish a new release (pyproject version is still 26.8.0) so the README's install instructions and examples agree with what `pip install aspose-slides-foss` delivers.
```
Verdict: **RESEAL_REQUIRED** (confidence medium-high). The install story in the candidate contradicts the source tree for hyperlinks, the candidate omits the live README's PyPI-lag and namespace warnings, Markdown export and the Enterprise paragraph, and upstream already rewrote the README. Not verified: transitions/3D/effects writer changes against PowerPoint, chart examples with python-pptx, the Enterprise Edition link.

---

## Summary table

| Candidate | Drift class | Verdict | Confidence | Main reason |
|---|---|---|---|---|
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | (c)+(d) | RESEAL_REQUIRED | high | Formula-engine claim ("only SUM/AVERAGE/MAX/MIN"), 14-type count and test count false at head; invented "wrapper around Aspose.Cells engine"; charts/pivots/conditional formats/VBA missing; published v26.7.1 lags main |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | (d)+(b) | RESEAL_REQUIRED | high | Opening says it only reads .ttf (false), forbidden/contradicted "commercial edition" text, no CLI/MCP, +12.8k lines in 26.10.2 |
| aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | (a) | DO_NOT_PUSH | high | Upstream README already refreshed on 2026-10-10 and far better; candidate falsely claims read/write/convert, a `Aspose.Imaging.Foss` class, 3 types, custom loaders |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | (b) | RESEAL_REQUIRED | high | Package renamed to `aspose-note-foss` (candidate installs the deprecated stub), version 26.3.2 -> 26.9.0, invented Enterprise feature list, thinner than live |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | (c)+(d) | RESEAL_REQUIRED | high | `ConvertToPDFA` limitation now false (auto-flattens), contradictory "commercial edition adds signature validation", new comparison/PDF417/UnembedFonts missing |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | (d) | RESEAL_REQUIRED | med-high | No claim falsified but 39 feature commits, dangling sentence, garbled bullet, wrong H1, large content regression vs live README |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | (b)+(c)+(d) | RESEAL_REQUIRED | high | Version 26.9.0 -> 26.10.0, net8.0-only claim now false (netstandard2.0/net48/net8/9/10), dependencies incomplete, forbidden wording, 2004 files changed |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | (b)+(c) | RESEAL_REQUIRED | high | "Not published on any registry" false (NuGet 1.0.1, release archives), invented 1.0.0 labels, "for Cpp" name, self-contradictory commercial text |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | (b)+(c) | RESEAL_REQUIRED | high | Version 26.8.0 outdated (26.9.0 on Central); XLSX/Markdown conversion "not supported" now false; REJECT_FACTUAL converted to ACCEPT |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | (a), identical tree | DO_NOT_PUSH | high | No content drift; candidate regresses live README (false "not published", circular limitations, forbidden text, "Cpp" name) |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | (c)-light + (a) | RESEAL_REQUIRED | med-high | Install via PyPI 26.8.0 breaks the hyperlink example (ImportError), PyPI-lag/namespace warnings and Markdown export missing, upstream README already refreshed |

Upstream issue bodies (text only, not filed): Cells-Go (stale README + hygiene), Font (PyPI/version), Imaging (csproj URLs), Note (Quick Start crash), PDF-Python (stdout logging), PDF-Cpp (snippet includes), Java (conversion limitations contradiction), Slides-Cpp (missing include), Slides-Python (release lag). No upstream defects found for PDF-Go, PDF-.NET.

What I could not verify: Enterprise Edition / docs.aspose.org / kb.aspose.org / reference.aspose.org link targets (BC-06 reports PASS but I did not re-fetch), full test suites (`go test`, `mvn test`, `dotnet test`, `pytest`, ctest were not run), full CMake builds of the C++ projects (headers only, `-fsyntax-only`), net48/netstandard2.0 compilation of the .NET library, behaviour of AI copilots / signatures with real certificates, and the factual accuracy of the long API tables beyond sampling.
