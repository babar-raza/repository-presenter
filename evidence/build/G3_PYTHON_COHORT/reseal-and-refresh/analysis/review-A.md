authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Candidate review A - 8 source-current candidates (read-only)

Reviewer: read-only audit. Nothing was written to GitHub or to any Aspose repository. All upstream access was `git clone --depth 1` and `gh api` GET / `curl` GET.
Clones: `scratchpad/clones/A_*` (each at the sealed revision == upstream head, confirmed by `git rev-parse HEAD`). Scratch venvs/dotnet project: `scratchpad/venv_*`, `scratchpad/dn_chk`.

## 0. Headline findings (apply to the whole batch)

1. **In all eight cases the live upstream README is already richer than the sealed candidate** (live is 262-851 lines of mostly human-curated, example-tested text; the sealed one drops content in every case). Seven of the eight live READMEs are already in the 10-section template shape (only Slides .NET is not). A PR from these candidates would be a regression for the repository, not an improvement.
2. **Every manifest records `review_verdict_as_returned: REJECT_PRESENTATION`, overridden to `ACCEPT`** by the "reviewer_scope_defect" mechanism. I checked the dismissed findings: many are correct and describe real defects (Barcode F04 wrong install block; Cells Cpp F02 "not published" is false; Slides Java F04 "getFontName only font API" is false; Slides Java F05 dropped security warning; Cells Java F08 "PDF export" unsupported claim; .NET F04 "PPTX and PDF" false). The override discards true positives. This is a pipeline defect, not an upstream one.
3. **Recurrent generator defects visible in these candidates**: (a) dangling lead-in sentence whose code block was dropped ("Run the test suite:" followed directly by `## License`: Cells Java, Cells Python); (b) the word "member" injected into prose ("member AUTO or member H", "calling member render", Barcode); (c) "N test files under tests/" counts fixtures/`__init__`/data files (Barcode 48 vs 37 real, .NET 139, Words 16 fixture files and zero tests); (d) "Detailed Member Reference" emitting bare namespace stubs (`### org`, `### aspose`, `### cells_foss`, `### Aspose`, `### Slides`) and internal members (Cells Cpp `GetModel`, `EnsureUniqueDefinedName`); (e) installation lines contradicting reality ("not published" when it is, "version X published" when it is not); (f) Quick Start/Additional Examples silently removed when examples are NOT_VERIFIED, yet BC-03 still PASSes vacuously (.NET, Words, Cells Cpp); (g) Enterprise paragraph invents differences ("adds conditional formatting" while the same README says the FOSS lib supports it); (h) toolchain-blocked receipts (`dotnet SDK did not report a version` although dotnet 10.0.401 runs fine on this machine; Words `requires-python <3.13` vs presenter Python 3.13.2).
4. Real upstream defects found (details in each section): Cells Cpp/Java/Python LICENSE only under `License/` so GitHub reports no license; Cells Python CSV default encoding is locale-dependent (crashes on cp1252 for CJK), 2 tests depend on a non-existent `input/` dir, wheel installs a top-level `examples` package; Words Python dev extras miss `pdfplumber` (1 test fails), `<3.13` upper bound unnecessary; Cells Rust ships zero tests; Cells Java stale committed Javadoc for removed package; Slides Java published 26.7.0 is the only Maven Central version while it has a known XML hardening gap.

## 1. Summary table

| Candidate | State in manifest | Examples receipts | Verdict | One-line reason |
|---|---|---|---|---|
| aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | READY_FOR_PROPOSAL | 6 EXECUTED (not build-verified) | DO_NOT_PUSH | Says "no install command succeeds" (false: `pip install .` works), replaces verified `pip install .` with a PYTHONPATH hack, drops dev deps/Enterprise/diagram outputs; live README strictly better |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | READY_FOR_PROPOSAL | 1 EXECUTED, 1 FAILED, 5 NOT_VERIFIED | DO_NOT_PUSH | Claims package "not published on any registry" (NuGet 26.4.1 exists) and `cmake -S . -B build` at root (no root CMakeLists); no Additional Examples/Dev&Testing; API table lists internals |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | READY_FOR_PROPOSAL | 3 EXECUTED | DO_NOT_PUSH | Dangling "Run the test suite:" with no command, false "PDF export", self-contradicting Enterprise paragraph, junk limitation bullet, drops reference link and Maven/Gradle snippets |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | READY_FOR_PROPOSAL | 6 EXECUTED | DO_NOT_PUSH | Closest to acceptable but drops CSV from diagram, loses most capability detail, dangling "run the test suite:", misleading limitations text, no Enterprise link |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | READY_FOR_PROPOSAL | 1 compiled, 6 NOT_VERIFIED | DO_NOT_PUSH | Loses Additional Examples/Project Structure/crates.io link/Rust badge; run-on Development paragraph; "Releases run through the ci workflow" false; `Workbook.new` notation |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | READY_FOR_PROPOSAL | 9 NOT_VERIFIED (BLOCKED_TOOLCHAIN) | RESEAL_REQUIRED | No Quick Start at all; says net8.0 only (real: net8.0+net10.0), says PDF export supported (throws NotSupportedException), 3D limitation contradicts own capabilities; live is non-template so a good reseal has real upside |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | VALID_UPDATE_AVAILABLE | 12 EXECUTED, 1 NOT_VERIFIED | DO_NOT_PUSH | Install command targets 26.8.0, which is not on Maven Central (404); drops the security warning; invented `org.aspose.slides` package and `Relationship` class; "getFontName is the only font API" false |
| aspose-words-foss/Aspose.Words-FOSS-for-Python | READY_FOR_PROPOSAL | 12 NOT_VERIFIED | DO_NOT_PUSH | No Quick Start/Additional Examples, API table counts ApiExamples classes (198 vs 146 real) and contradicts itself, "16 test files under tests/" are fixtures, pure-Python claim ignores pydantic |

Confidence: high for all verdicts (each rests on at least one independently verified false claim or a clear loss versus the live README). Not verifiable here: Java/C++/Rust builds and test suites (no JDK, Maven, CMake, g++, cargo on this machine), Slides .NET full test suite (not run).

Candidate wording checks (all 8): exactly 1 `mermaid` fence each; no `forum.aspose.com` in any sealed README; no literal "commercial edition" / "paid version"; no "via Java"; "commercial Aspose.X product/offering" phrasing appears in Cells Cpp, Cells Java, Rust, .NET (4x), Slides Java, Words (borderline, not a literal forbidden string). All 65 external URLs in the 8 sealed READMEs resolve (HTTP 200) except placeholders in code. Note `https://products.aspose.com/cells/rust/` is 404 (the sealed Rust README correctly avoids it, using `https://products.aspose.com/cells/`).

---

## 2. aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python  (06eca5c0...)

**Bundle state**: READY_FOR_PROPOSAL; BC-01..BC-11 all PASS; review ACCEPT (as returned REJECT_PRESENTATION), 15 advisories; examples 6/6 EXECUTED but `build_verified: false` ("the package would not build" - the receipt harness ran them against `src` via PYTHONPATH).

**Sealed vs live**
- Live (262 lines) is a complete template README. Sealed is 301 lines but weaker.
- Adds: Python-version badge, a `RenderOptions` example promoted to the first Additional Example, a long duplicated API table (module-path aliases such as `exceptions.BarcodeError`, `options.Code39Options`, `renderers.PdfRenderer` repeated next to the top-level names: 51 "types" for ~25 real ones).
- Drops/changes (all regressions): factual opening ("pure-Python, deterministic, standards-compliant, no system dependencies beyond Pillow") replaced by a generic paragraph; At a Glance loses specific symbologies and the Outputs subgraph; Key Capabilities lose Code Set switching, modulo-43 check, `code39ext`, `allow_check_digit_input`, QR versions 1-40, `RenderOptions` details; Installation `pip install .` replaced by `export PYTHONPATH="src:.:$PYTHONPATH"`; Development Dependencies (pytest >=8.0, ruff >=0.15.7) removed; `pip install -e . pytest ruff && pytest` dev block removed; Enterprise Edition paragraph removed; Scope text rewritten into garbled prose ("using the member AUTO or member H encoding modes").

**Spot checks (clone)**
1. Name `aspose-barcode-foss`, version 0.1.0, requires-python >=3.12, MIT: PASS (pyproject.toml).
2. Pillow>=10.1.0 only runtime dep: PASS.
3. Root `LICENSE` MIT, GitHub detects MIT: PASS.
4. `code128("Hello-World").to_svg()` and `.to_png()`: PASS (ran in fresh venv: 2228-char SVG, 793 PNG bytes).
5. `to_pdf()` raises NotImplementedError: PASS.
6. `generate`, `qr`, `code39`, `ean13`, `ean8`, `upca`, `upce`, `RenderOptions`, `SvgRenderer`, `QrOptions`, enums exported from `__init__`: PASS.
7. "no build or install command succeeds for this revision": **FAIL**. `pip install ./A_barcode_py` succeeded in a clean venv and `import aspose_barcode_foss` works. The live README's `pip install .` is correct.
8. "The suite covers 48 test files under tests/": **FAIL (misleading)**. 48 tracked files in `tests/` include `__init__.py`/`conftest.py`; 37 are `test_*.py`. The suite has 646 tests, all pass (231 s).
9. "classes like AUTO, H": **FAIL** - they are enum members of `QrEncodeMode`/`QrErrorCorrectionLevel`, not classes.
10. "exposes methods to render barcodes to PNG, SVG, or PDF formats" (API intro): **misleading** - PDF always raises NotImplementedError (the same README says so under Scope).
11. Examples dir and four scripts exist and exit 0: PASS (`quickstart.py`, `all_symbologies.py`, `render_options.py`, `error_handling.py`).
12. Links (docs/kb/reference/products/banner, issues): PASS (HTTP 200). Relative links `LICENSE`, `examples/`, `examples/README.md`: PASS.

**Completeness**: omitted from sealed (present in clone): `py.typed`/typing support, `code39ext()` helper, `allow_check_digit_input`, QR `version`/`mask`, `Code128EncodeMode` members, dev tooling (ruff, pytest) and how to run them, `examples/README.md` table (still linked). No docs/, CHANGELOG, CONTRIBUTING, SECURITY in repo.

**Template conformance**: 10 sections + Additional Examples present; one mermaid fence (but low-information); no forum link; Enterprise link absent (live has one). OK structurally; fails on accuracy.

**Upstream defects**: none worth an issue. Tests pass (646), examples run, `pip install .` works, license correct. (pyproject `project.urls` use `Aspose.Barcode-FOSS-for-Python` casing - harmless, GitHub is case-insensitive.)

**Verdict: DO_NOT_PUSH** (confidence high). A hand-edit would amount to restoring the live README. Reason: contains a false statement about installation and replaces a verified install with a worse one.

---

## 3. aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp  (9f852d0f...)

**Bundle state**: READY_FOR_PROPOSAL; checks 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 11 advisories; examples: ex1 EXECUTED (MSVC CMake build ok), ex2 FAILED (`workbook.GetWorksheets()["Products"]` - `no match for operator[]`), ex3-7 NOT_VERIFIED ("uses sheet without binding"). Only ex1 (Quick Start) is rendered. coverage advisory 1.

**Sealed vs live** (live 598 lines, 11 sections, NuGet/License/Contributors/Issues badges)
- Adds: a "Dependencies" section (live has none - worth porting, see below), 195-type API table.
- Drops: NuGet badge and Windows-only NuGet install route (`nuget install Aspose.Cells.Cpp.FOSS`, PackageReference, CMake `find_package`), Additional Examples (load, conditional formatting, validation, hyperlinks, page setup, defined names), Development and Testing (GoogleTest, samples), Contributor guide link, `.xlsx`-only scope bullets and real limitations (legacy SpreadsheetML mappers throw, no cell comments, CF dropped on load, AutoFilter date-group), Enterprise explanation of real differences, "Project structure"/AGENTS link.
- Introduces false/odd content: install paragraph "not yet published on any package registry"; `cmake -S . -B build` from the repo root; "read, write, and convert spreadsheet files" (only xlsx); Scope section is mostly "DefinedName exposes only members GetComment, ..." (member lists, not limitations); namespace written `Aspose.Cells_FOSS.Workbook` (real: `Aspose::Cells_FOSS`); "Detailed Member Reference" exposes internals (`GetModel() -> Core::WorkbookModel`, `EnsureUniqueDefinedName`, `Dispose`, `FromCore`/`ToCore`).

**Spot checks (clone)**
1. C++17 and `cmake_minimum_required(VERSION 3.16)`: PASS (`Aspose.Cells.Foss.Cpp/CMakeLists.txt`).
2. Dependency-free (no find_package/FetchContent in library CMake): PASS.
3. NuGet package: **FAIL** - `https://api.nuget.org/v3-flatcontainer/aspose.cells.cpp.foss/index.json` lists 26.4.0 and 26.4.1. The sealed "not yet published on any package registry" is false.
4. `cmake -S . -B build` at repo root: **FAIL** - root contains only `.gitignore AGENTS.md README.md License samples Aspose.Cells.Foss.Cpp Aspose.Cells.Foss.Cpp.Tests`; no root CMakeLists.txt. The command errors. (The receipt's "library's own CMake build succeeded" was in the library subfolder.)
5. License MIT at `License/LICENSE.txt`: PASS (relative link resolves).
6. Quick Start code identical to live; receipt says it compiled with MSVC CMake: PASS (not re-compiled here, no compiler).
7. `Workbook` ctors: default, path, byte vector, +LoadOptions: PASS (Workbook.h:39-59) - README mentions only default/path/vector.
8. "195 types" vs live "197": cannot reconcile; 116 header files; unverified.
9. `GetWorksheets()` has `operator[](int)` and `operator[](std::string_view)`: PASS in header (WorksheetCollection.h:39,44). The receipt compile error for the string form contradicts the header and could not be reproduced (no compiler) - unverified; if real it is an upstream defect in the live README example.
10. "Scope" claim "convert spreadsheet files": **FAIL** - only `Xlsx` in `LoadFormat`/`SaveFormat`; other save formats throw `UnsupportedFeatureException`.
11. Relative/external links: all 200.
12. Sample count: `samples/` contains one `main.cpp`; live describes "samples" correctly.

**Completeness**: omitted - GoogleTest suite under `Aspose.Cells.Foss.Cpp.Tests` and how to run it, samples build, Windows-only NuGet binaries, `AGENTS.md`, load diagnostics/warnings, exceptions list.

**Template**: has Dependencies; missing Additional Examples (optional) and Development and Testing (mandatory); Enterprise link present with "commercial Aspose.Cells for C++ product" wording.

**Upstream defects (ready-to-file, text only)**
- *Issue 1 - LICENSE not recognised by GitHub (low)*
  Title: `LICENSE lives only in License/LICENSE.txt, so GitHub reports "no license"`
  Body: `The repository's MIT license is at License/LICENSE.txt, a sub-folder. GitHub license detection and most scanners (deps.dev, FOSSA, ClearlyDefined) only look at the repository root, so the repo sidebar shows no license (GET /repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp -> "license": null). Compare Aspose.BarCode-FOSS-for-Python, which has a root LICENSE and is detected as MIT. Also the copyright line says "2001-2025" while other Aspose FOSS repos use 2001-2026. Suggest: add LICENSE (or LICENSE.txt) at the repo root (the Rust repo keeps both), keep or remove License/ as preferred, and refresh the year.`
- *Issue 2 - stale paths in test README (low)*
  Title: `Aspose.Cells.Foss.Cpp.Tests/README.md references a non-existent workspace/ directory`
  Body: `The build and run commands in Aspose.Cells.Foss.Cpp.Tests/README.md use .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc and say the test project adds workspace/Aspose.Cells.Foss.Cpp as a subdirectory. Neither path exists in this repository (the folders are at the root: Aspose.Cells.Foss.Cpp, Aspose.Cells.Foss.Cpp.Tests). A newcomer following the README fails at the first command. Suggested replacement: cd Aspose.Cells.Foss.Cpp.Tests; cmake -S . -B build; cmake --build build; ctest --test-dir build --output-on-failure.`
- *Possible issue 3 (needs compile confirmation)*: README "Load an existing workbook" example `workbook.GetWorksheets()["Products"]` reported as `no match for operator[]` (const char[9]) by the presenter's g++ 16.2 / -std=c++17 syntax check. Header declares `operator[](std::string_view)`, so this may be a harness include-path problem. Do not file until reproduced.

**Verdict: DO_NOT_PUSH** (confidence high). Only item worth porting into the live README: a "Dependencies" section (statement of no third-party deps, C++17, CMake >=3.16), which the live README lacks.

---

## 4. aspose-cells-foss/Aspose.Cells-FOSS-for-Java  (c65329e7...)

**Bundle state**: READY_FOR_PROPOSAL; 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 13 advisories; 3 examples EXECUTED (javac 17, compiled against product classes).

**Sealed vs live** (live 537 lines, adds Project Structure, Maven + Gradle snippets, Maven Central/Java/Contributors badges, `reference.aspose.org` link, repo-structure tree)
- Drops: Maven/Gradle snippets (only `mvn dependency:get`), Maven Central + Java badges, full capability set (auto filters, freeze panes, protection, merged cells, defined names, hyperlinks, calc properties, 18/25 chart types, 38 preset shapes), Project Structure, API Reference reduced to junk "Detailed Member Reference" (`### org`, `### aspose`, `### cells_foss`), `reference.aspose.org/cells/java/` link, `mvn compile`/`clean package`/`javadoc:javadoc` commands, correct Enterprise statement.
- Defects introduced: Development and Testing ends with a dangling "Requires JDK 17+ and Maven as the build tool. Run the test suite:" and **no command**; Key Capabilities claim page setup is "to prepare documents for printing or PDF export" (no PDF export exists - `grep -ri pdf src/main` has no hit); first Scope bullet fuses limitation with "the artifact can be installed using the Maven command ..."; Enterprise paragraph says the commercial product "adds ... conditional formatting" while the same README says the FOSS lib supports conditional formatting, and cites DOCX/XLSM/ODS support without evidence; "Cells.getRows()`.setHeight()" broken markup; Dependencies says "every <dependency> the POM declares is test, provided or optional" (verified correct, but phrased oddly).

**Spot checks (clone)**
1. groupId/artifact/version `org.aspose:aspose-cells-foss:26.7.0`: PASS (pom.xml 8-10).
2. Published on Maven Central at 26.7.0: PASS (maven-metadata.xml: 26.5.0, 26.7.0, latest 26.7.0).
3. Java 17 (`maven.compiler.source/target` 17): PASS.
4. Only test-scope deps (junit-jupiter, poi-ooxml): PASS.
5. Package is `org.aspose.cells_foss`: PASS (src/main/java/org/aspose/cells_foss).
6. Quick Start / load-with-repair / validation+CF examples compile: PASS per receipts (3 EXECUTED; not recompiled).
7. `Agents.md`, `PUBLISHING.md`, `.github/workflows/maven-central-release.yml`, `License/LICENSE.txt` links resolve: PASS.
8. "PDF export" via PageSetup: **FAIL** (no PDF code in `src/main`).
9. "The suite ... mvn test as defined in CI" and the `Run the test suite:` command block: **FAIL** (command missing).
10. Enterprise claim "commercial adds conditional formatting": **FAIL** (FOSS has `ConditionalFormattingCollection`, `FormatConditionCollection`).
11. ChartEx types cannot be created: PASS (consistent with live: 18 of 25 creatable).
12. API surface "183 types": not independently verified.

**Completeness gaps** (info in clone, absent from sealed): Project structure, CHANGELOG-style notes (none in repo), `docs/apidocs/` (Javadoc), 38 test files under `src/test`, `.actrc`/`.secrets.example` (act-based local release), full capability list.

**Upstream defects (ready-to-file)**
- *Issue - stale committed Javadoc (low)*
  Title: `docs/apidocs is generated for the removed com.aspose.cells_foss package ("cells-foss 1.0.0")`
  Body: `docs/apidocs/index.html says "cells-foss 1.0.0 API", generated 2026-05-18, and redirects to com/aspose/cells_foss/package-summary.html. The source tree and published artifact use org.aspose.cells_foss (src/main/java/org/aspose/cells_foss; org.aspose:aspose-cells-foss:26.7.0). The committed Javadoc therefore documents a package that no longer exists (112 files under docs/apidocs/com/aspose/cells_foss). README links this folder as the generated API docs. Regenerate with mvn javadoc:javadoc or delete the folder and publish Javadoc from CI.`
- *Issue - mojibake in repo files (low)*: `pom.xml` line ~62 comment `Apache POI â€” OOXML` and `Agents.md` line 46 (`鈫?`) are mis-encoded UTF-8 (double-decoded em dash / arrow). Save as UTF-8.
- *Issue - LICENSE not detected (low)*: same body as Cells Cpp Issue 1 (repo `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`, `license: null`, copyright 2001-2025).

**Verdict: DO_NOT_PUSH** (confidence high).

---

## 5. aspose-cells-foss/Aspose.Cells-FOSS-for-Python  (4f6768a7...)

**Bundle state**: READY_FOR_PROPOSAL; 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 15 advisories (F01/F02 diagram omits CSV start and JSON/Markdown outputs; F04 wrong claim about `conditional_format` module vs `ConditionalFormat` class and encryption mechanism; F07 CSV/JSON/Markdown limitation misworded); 6 examples EXECUTED.

**Sealed vs live** (live 416 lines)
- Adds: source-checkout install + `python -c "import aspose.cells_foss"` verify (reasonable), PyPI/Python badges (Python badge hard-coded 3.7+ instead of dynamic pyversions).
- Drops: CSV import start and JSON/Markdown outputs in the diagram; most capabilities (page setup/pane, merged cells, defined names, hyperlinks, comments, pictures, 16 chart types, sparklines, Agile encryption details, `Workbook.save(password=...)`); Enterprise link; `llms.md`; dev install block.
- Defects introduced: "Encrypt and decrypt workbooks ... `encrypt_xlsx` mechanism ... `decrypt_xlsx` operation via the `xlsx_encryptor` interface" (the real user API is `Workbook.save(password=...)` and `Workbook(path, password=...)`); "`aspose.cells_foss.conditional_format`" presented as an API (it is a module); Scope bullet "CSV, JSON, and Markdown are limited to export targets, with CSV also permitting import, and none serving as general spreadsheet formats" is garbled; Development and Testing ends with dangling "Install the development dependencies and run the test suite:" and no command; API reference stubs for Shape/Table/Sparkline empty; summary says "exporting to .csv" only in the Scope intro.

**Spot checks (clone + venv)**
1. Version 26.7.0 on PyPI, requires-python >=3.7, deps `pycryptodome>=3.15.0`, `olefile>=0.46`, dev `pytest>=7.0.0`, `pytest-cov>=4.0.0`: PASS (pyproject + PyPI JSON agree).
2. `pip install aspose-cells-foss`; `pip install .` from checkout: PASS (installed and imported in a clean venv).
3. Quick Start (create, set A1/B1/A2/B2, save; reopen and read A1): PASS (ran; printed "Hello").
4. Style example (`get_style`, `font.bold/color/size`, `apply_style`): PASS (ran).
5. Dropdown validation `worksheet.data_validations.add("A1:A10")`, `DataValidationType.LIST`: PASS (ran).
6. `workbook.save_as_csv("output.csv")`: PASS for ASCII (ran); **fails for CJK on Windows default code page** (see defect).
7. Password save/open `save(..., password=)` and `Workbook(path, password=)`: PASS (ran).
8. `aspose.cells_foss.conditional_format` is a module and `ConditionalFormat` the class: README presents the module as the API surface - misleading (advisory F04 real).
9. `encrypt_xlsx`, `decrypt_xlsx`, `xlsx_encryptor`, `AgileEncryptionParameters`, `CSVSaveOptions`, `JsonHandler`, `Sparkline`, `MsoDrawingType` exported: PASS.
10. Python badge "3.7+" and statement `python_requires >=3.7`: PASS.
11. Relative links `License/LICENSE.txt`, `examples`, `AGENTS.md`: PASS. External links: 200.
12. "Standard encryption not supported for reading" (dropped) is correct in live; sealed omits it, and sealed Scope bullet mentions only Agile - OK.

**Completeness**: omitted - `llms.md` (LLM-oriented API reference), `requirements.txt`, 54-module API, 30 example test scripts in `examples/`, CSV/JSON/Markdown handlers, formula evaluator, comments/pictures/pane.

**Upstream defects (ready-to-file)**
- *Issue 1 - CSV export defaults to the OS locale encoding (medium)*
  Title: `save_as_csv default encoding is locale-dependent; CJK text raises UnicodeEncodeError on Windows`
  Body: `CSVSaveOptions.encoding and CSVLoadOptions.encoding default to locale.getpreferredencoding(False) (aspose/cells_foss/csv_handler.py:29-31,60,108). On Windows with cp1252 this makes workbook.save_as_csv("o.csv") raise UnicodeEncodeError for any non-Latin-1 text. Repro (Python 3.13.15, Windows 11, cp1252): examples/test_csv_import_export.py::TestCSVUnicodeAndInternationalization::test_chinese_characters and ::test_japanese_characters fail with "UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-1" from csv_handler.save_csv line 192 (writer.writerow). With PYTHONUTF8=1 they pass. Files written on one machine also read differently on another. Suggested: default to "utf-8" (optionally write BOM per write_bom) and document the option.`
- *Issue 2 - two tests depend on a missing input/ directory (low-medium)*
  Title: `examples/test_xlsx_to_json.py and test_xlsx_to_markdown.py fail on a clean checkout: input/ directory is not in the repository`
  Body: `After pip install -e ".[dev]" && pytest on a fresh clone, test_xlsx_to_json.py::test_sales_report_to_json fails with "Input file .../input/sales_report_comprehensive.xlsx does not exist" and test_xlsx_to_markdown.py::test_convert_all_xlsx_to_markdown fails with "No XLSX files found in input directory". git ls-files contains no input/ folder. Either commit the fixture workbooks, generate them in a fixture, or skip when absent. (Result on 3.13/Windows: 4 failed, 291 passed; 2 of the 4 are this issue, 2 are the encoding issue.)`
- *Issue 3 - wheel ships a top-level "examples" package (medium)*
  Title: `pyproject packages = [..., "examples"] installs a top-level examples package into site-packages`
  Body: `[tool.setuptools] packages = ["aspose","aspose.cells_foss","examples"] plus package-data for examples means pip install aspose-cells-foss puts site-packages/examples/ (test_*.py, output_path_helper.py) next to the library. Verified in a fresh venv: site-packages contains aspose/, aspose_cells_foss-26.7.0.dist-info/ and examples/. A generic top-level name "examples" collides with any other project or the user's own examples package. Remove "examples" from packages/package-data (ship tests in an sdist only).`
- *Issue 4 - project.urls point at old repository name (low)*: Homepage/Documentation/Repository/Issues use github.com/aspose-cells-foss/aspose-cells-python (redirects today, but fragile). Use Aspose.Cells-FOSS-for-Python.
- *Issue 5 - LICENSE not detected (low)*: as Cells Cpp Issue 1 (`license: null`; 2001-2025). Also the GitHub description still reads "High-performance Python Excel processing library with advanced conversion capabilities".

**Verdict: DO_NOT_PUSH** (confidence high). No part of the candidate is better than the live README except the optional "verify install" line.

---

## 6. aspose-cells-foss/Aspose.Cells-FOSS-for-Rust  (1a6004af...)

**Bundle state**: READY_FOR_PROPOSAL; 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION) with 7 mostly generic advisories (the F01 "omits crates.io" is actually mis-scoped; candidate states it); examples: 1 COMPILED (Quick Start, cargo 1.98.1), 6 NOT_VERIFIED; coverage advisories 2; link-coverage reports one 404 target (`products.aspose.com/cells/rust/`) which the final README does not use.

**Sealed vs live** (live 717 lines)
- Adds: nothing material.
- Drops: Rust-edition badge, Additional Examples, Project Structure section (the tree is dumped inside the API `<details>` with no heading), per-dependency purpose, crates.io link, path/git dependency snippets for Cargo.toml, Enterprise detail ("legacy XLS, CSV, ODS").
- Defects introduced: the opening paragraph is a 130-word method-name list ("Workbook.new and load_xlsx...", C#-style `Workbook.new` instead of `Workbook::new`); "The crate is not yet published to crates.io and must be added as a Git dependency" but Installation gives only `cargo build` (no Cargo.toml git-dependency snippet - this is how a user would use it); Development and Testing is a run-on sentence listing `cargo build, cargo check ... cargo bench` followed by a code block, and then "Releases run through the ci workflow" (ci.yml is build/test/bench only, no release job); `CellsError`::Unsupported markup; Scope intro "built for the rust ecosystem".

**Spot checks (clone)**
1. Crate `aspose-cells-foss-rust` 26.7.0, edition 2021, lib `aspose_cells_foss_rust`: PASS (Cargo.toml).
2. Seven runtime deps (chrono 0.4, zip 0.6, sha2 0.10, base64 0.22, serde_json 1, roxmltree 0.20, getrandom 0.3): PASS.
3. Not published to crates.io: PASS (`index.crates.io/as/po/aspose-cells-foss-rust` 404).
4. `Workbook::new`, `Workbook::load_xlsx`, `load_xlsx_from_bytes`, `load_xlsx_from_stream`, `Workbook::worksheet(&str)`: PASS (Workbook.rs lines 186, 236, 398, 429, 487).
5. `put_value_string`, `put_value_i32`, `put_formula_with_cached_value`, `get_display_string_value`, `get_formatted_string_value`: PASS (Cell.rs).
6. `get_worksheets_mut`, `get_cells_mut`: PASS (Workbook.rs:277, Worksheet.rs:394).
7. Removing last worksheet returns `CellsError::Unsupported("remove last worksheet")`: PASS (WorksheetCollection.rs:212).
8. "No automated test suite ... cargo test reports zero tests": PASS (no `tests/`, zero `#[test]`).
9. "Releases run through the ci workflow": **FAIL** (ci.yml has fmt/build/test/bench only; pages.yml deploys docs).
10. `cargo bench` listed as a command: PASS in CI yml (`cargo bench`) but there are no bench targets in the tree (`git ls-files | grep -i bench` = 0).
11. `samples/` binaries `sample_basic`, `sample_loading`, `sample_styles` declared in Cargo.toml: PASS.
12. Links: docs/kb/reference/products.aspose.com/cells/ all 200; `.github/workflows/ci.yml`, `samples/`, `samples/README.md`, `AGENTS.md`, `LICENSE.txt` exist: PASS.
13. Quick Start code compiles: PASS per receipt only (no cargo here).

**Completeness**: omitted - Cargo git/path dependency usage, 14 sample binaries and what each demonstrates, GitHub Pages rustdoc, `pages.yml`, project layout, `chrono`/`zip` roles.

**Upstream defects (ready-to-file)**
- *Issue - repository ships no tests (medium)*
  Title: `No automated tests: cargo test --all-targets runs 0 tests`
  Body: `The crate has no tests/ directory and no #[test]/#[cfg(test)] anywhere under src/ or samples/ (grep returns 0). CI runs cargo test --all-targets, which therefore passes vacuously, so read/write regressions (XLSX load/save, styles, charts, validations) are not caught except by manually running the sample binaries. Suggest adding round-trip integration tests under tests/ (the samples already create workbooks, save, reload and print), and optionally cargo bench targets or removing the bench step from ci.yml (no bench targets exist).`
- *Issue - stale README wording (low)*: "Once the repository is live at its real GitHub location, add it as a Git dependency" (live README Installation) is a leftover from pre-publication; the repo is public.
- Default branch is `master` while the Slides/Barcode repos use `main` (informational).

**Verdict: DO_NOT_PUSH** (confidence high).

---

## 7. aspose-slides-foss/Aspose.Slides-FOSS-for-.NET  (86c441b5...)

**Bundle state**: READY_FOR_PROPOSAL; 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 13 advisories; all 9 example receipts `NOT_VERIFIED: BLOCKED_TOOLCHAIN: the dotnet SDK did not report a version`. The README contains **no Quick Start and no Additional Examples** (the generator removed every example). Navigation has 9 entries.

**Sealed vs live** (live 545 lines, hand-written, not template-shaped: headings "At a glance", "Requirements", "Quick start", "Examples", "What it can do", "What it cannot do", "Choosing an edition", "Documentation and support", "Contributing", "Security"; contains a forum.aspose.com link and CI/NuGet/license/.NET badges)
- Adds: template skeleton (Navigation, Key Capabilities, Dependencies, API Reference, Development and Testing), links to sibling FOSS ports (Java, C++, Python) - the one valuable new element.
- Drops: net10.0 support, build-from-source and CI-package install routes, the whole Quick Start with verified output, 8+ worked examples (text, tables, effects, comments, notes), "What it can do" XML-level detail, "What it cannot do" table, "Choosing an edition", Contributing/CHANGELOG/CODE_OF_CONDUCT/SECURITY links, CI badge.
- Defects introduced: "runs on net8.0" (csproj `TargetFrameworks` net8.0;net10.0); Scope bullet "does not support exporting presentations to formats other than PPTX and PDF" - PDF is not supported (verified: `Save(..., SaveFormat.Pdf)` throws `NotSupportedException: ... Supported formats: Pptx, Ppsx, Potx`); Scope bullet "does not support editing or rendering of 3D shapes or 3D effects" contradicts Key Capabilities "Effects and 3D"; API intro: "The Aspose.Slides namespace contains the commercial API surface" (invented namespace stubs `### Aspose`, `### Slides`, `### Foss`); Enterprise paragraph contains run-on text "When you want the commercial product instead of this one - if you need to render or convert ... none of that is here"; "The suite covers 139 test files under tests/" (139 files incl. test_data; 124 are *Test(s).cs).

**Spot checks (clone, dotnet 10.0.401 on this machine)**
1. Package `Aspose.Slides.FOSS` on NuGet at 26.9.0: PASS (flatcontainer index) - sealed does not state the version.
2. TargetFrameworks `net8.0;net10.0`: sealed says net8.0 only - **FAIL (incomplete)**.
3. PDF export: **FAIL** - throws NotSupportedException (ran `new Presentation().Save("x.pdf", SaveFormat.Pdf)`).
4. `Save(..., SaveFormat.Pptx)`: PASS (ran).
5. Live Quick Start (`AddAutoShape`, `AddTextFrame`, save, reopen) compiled and ran on net10.0: PASS (output "slides: 1 / shapes: 1 / text: Hello from Aspose.Slides FOSS") - sealed has no equivalent.
6. "no PackageReference" / zero dependencies: PASS (live text; csproj has none).
7. MIT LICENSE at root, copyright 2026: PASS.
8. Links to Java/Cpp/Python sibling repos: PASS (200).
9. `.github/workflows/nuget-release.yml` exists: PASS.
10. Scope "no 3D": **FAIL** (`BevelPresetType.cs` etc. exist; live "Fill, line, and 3D shape styling").
11. 139 test files: **FAIL (misleading)**.
12. Docs/kb/reference links (docs.aspose.com, kb.aspose.com, reference.aspose.com for .NET): PASS (200). Note this candidate alone uses the `.com` hosts for docs/kb/reference while all other candidates use `.org`.

**Completeness**: omitted - CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, PUBLISHING.md, issue/PR templates, docs/ folder, three test projects (Tests, IntegrationTests, ConformanceTests), PPSX/POTX output, `nuget.config`.

**Upstream defects**: none found in code (live quick start works, PDF refusal is explicit and documented). Observation only: the live README links `forum.aspose.com/c/slides/11`, which the project template forbids - a reseal should not carry it over.

**Verdict: RESEAL_REQUIRED** (confidence high). The live README is not template-shaped, so a correct candidate has real value. Required for reseal: working dotnet toolchain so BC-03 can verify examples (this machine's SDK works; the receipt's "did not report a version" looks like a presenter-environment fault), restore Quick Start + Additional Examples from live, net8.0/net10.0 from csproj, correct the PDF/3D statements, drop invented namespace stubs, add CHANGELOG/CONTRIBUTING/SECURITY/CoC links. Not fixable by a small hand edit.

---

## 8. aspose-slides-foss/Aspose.Slides-FOSS-for-Java  (620a2614...)

**Bundle state**: **VALID_UPDATE_AVAILABLE** (not READY_FOR_PROPOSAL); 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 12 advisories; 12/13 examples EXECUTED (javac 21), one NOT_VERIFIED.

**Sealed vs live** (live 851 lines; badges Build/Maven Central/License/Java 21+/Contributors; strong Installation with security warning; SECURITY.md/CHANGELOG/CONTRIBUTING/CoC links)
- Installation: "Install the published package from Maven Central (org.aspose:aspose-slides-foss, version 26.8.0): `mvn dependency:get -Dartifact=org.aspose:aspose-slides-foss:26.8.0`" - **26.8.0 is not published** (Maven Central metadata lists only 26.7.0; `.../26.8.0/aspose-slides-foss-26.8.0.pom` returns HTTP 404; SECURITY.md in the clone states "26.8.0 is the version in this source tree and is not published yet"; GitHub has only tag/release v26.7.0). The command in the README would fail for every reader.
- Drops the live README's explicit warning that 26.7.0 lacks the XML hardening fix and that untrusted-.pptx users should build from source; drops Maven/Gradle snippets, Java 21/25 CI matrix, SBOM/reproducible-build notes, `mvn verify -Dgpg.skip=true` explanation (kept only partially: code block present but lead-in sentence is garbled "-`Dgpg.skip`=true"), CONTRIBUTING/CHANGELOG/SECURITY links, `build.yml` badge, sibling-port links, known-defect (master clone) disclosure, round-trip guarantees.
- Defects introduced: "The public API surface is limited to the `org.aspose.slides` package under the `org.aspose` namespace" - there is no `org.aspose.slides` package, only `org.aspose.slides.foss`; API intro says `org.aspose.slides.foss` "contains the concrete implementations of the interfaces defined in `org.aspose.slides`" (nonexistent); a `### Relationship` entry (only `internal.opc.RelationshipsManager` exists); "The getFontName method is the only font-related API exposed" (its own examples call `setFontHeight`, `setFontBold`, `FontData` exists); bullet "Installation requires Maven and the explicit artifact coordinate ...; no other build tools or installation methods are provided" under Scope; leaked sentence "This section is the point of this file. Nothing here is a 'coming soon'..." is correct in live but out of context here; Enterprise paragraph claims "commercial offering extends functionality ..." (acceptable); "Embed images and create tables ... leverage the Relationship class".

**Spot checks (clone)**
1. pom version 26.8.0, `maven.compiler.release` 21: PASS.
2. Maven Central contains 26.8.0: **FAIL** (404; only 26.7.0).
3. `org.aspose.slides.foss` package: PASS; `org.aspose.slides` package exists: **FAIL**.
4. `Relationship` public class: **FAIL**.
5. `save()` supports only PPTX/PPSX/POTX and throws `UnsupportedOperationException` otherwise: PASS (live Scope; pom/tests consistent, not run).
6. Dev deps junit-jupiter-api/engine/params 5.11.4: PASS; sealed Development Dependencies also lists `org.apache.poi:poi-ooxml 5.4.1` and `assertj-core 3.27.3`: PASS (pom).
7. "No runtime dependencies": PASS.
8. Test counts: 45 files under `tests/` (37 contain "Test"): the "45 test files" figure is files not tests; unit tests also under `src/test/java` - misleading.
9. LICENSE MIT 2026 at root; GitHub detects MIT: PASS.
10. `PUBLISHING.md`, `maven-central-release.yml` links: PASS.
11. Quick Start/12 examples compile per receipts: PASS (not recompiled).
12. Links docs/kb/reference/products/AGENTS.md: PASS (200).

**Completeness**: omitted - SECURITY.md (private vulnerability reporting route), CHANGELOG.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, `build.yml` matrix (Linux/Windows/macOS, Java 21/25), SBOM, reproducible builds, round-trip fidelity measurements, known defect list.

**Upstream defects (ready-to-file)**
- *Issue - only published version has a known XXE-class gap (high, maintainers already aware)*
  Title: `Maven Central still serves only 26.7.0, which predates the XML hardening fix`
  Body: `SECURITY.md and README state that 26.7.0 (the only version on Maven Central: repo1.maven.org/maven2/org/aspose/aspose-slides-foss/maven-metadata.xml -> versions: 26.7.0) predates the secure-XML-factory hardening (DOCTYPE refused, external entities/DTD/XInclude disabled) now in the source tree (pom.xml = 26.8.0, not published). Anyone following "mvn dependency:get ...:26.7.0" and opening untrusted .pptx files is exposed. Please publish 26.8.0 (or a 26.7.1) via the existing maven-central-release workflow, and keep README/SECURITY wording in sync once released. Also tracked in README: getMasters().addClone(...) reports size 2 but the saved package contains one sldMasterId; consider a separate issue.`
- *Issue - master clone silently dropped (medium, unverified here)*: per live README "Scope and Limitations", `getMasters().addClone(...)` returns and the collection reports size 2, yet the saved package has one `<p:sldMasterId>`/`slideMaster1.xml` and nothing reports a problem. I could not reproduce (no JDK). File only after a repro; otherwise it is already disclosed by the maintainers.

**Verdict: DO_NOT_PUSH** (confidence high). Fix path is reseal against a fresh registry observation (version 26.7.0 is the published one) - not a hand edit - and the manifest is already VALID_UPDATE_AVAILABLE.

---

## 9. aspose-words-foss/Aspose.Words-FOSS-for-Python  (2d2efee2...)

**Bundle state**: READY_FOR_PROPOSAL; 11 PASS; review ACCEPT (as returned REJECT_PRESENTATION), 9 advisories; 12/12 examples NOT_VERIFIED ("no interpreter satisfies requires-python '>=3.10,<3.13': presenter runs Python 3.13.2"). The README has no Quick Start/Additional Examples.

**Sealed vs live** (live 655 lines, template-shaped, with Quick Start, Additional Examples, Enterprise link, ApiExamples table, `146` public types)
- Adds: nothing.
- Drops: Quick Start (load -> Markdown/PDF), Additional Examples (Markdown/PDF options, extract text, convert every format, load from stream), ApiExamples table, nightly install route, Enterprise link, accurate scope list (8 `PdfSaveOptions` fields not consumed), badges (`pypi/pyversions`), `LICENSE`-adjacent details.
- Defects introduced: Python badge text "python-3.10,<3.13+" (nonsense hybrid); opening says "without requiring a commercial license" and "Users include developers building reporting tools, document converters, and content extraction pipelines" (promotional, unsupported); "depends on fpdf2 and olefile" and "Pure-Python ... relying only on fpdf2 and olefile" while Dependencies lists `pydantic>=2.0.0` too (pydantic is imported by `light_document_model.py`; it has a compiled core); `` `Run` entirely in pure Python`` stray markup; API Reference lists `ConvertDocument`, `DocsExamplesBase` etc. (examples, not API) producing 198 "public types", and Documentation & Resources says "reference for all 146 public types. It covers all 198 verified public types" (self-contradiction); "The suite covers 16 test files under tests/" - `tests/` holds only 16 fixture files (`tests/data/input/*.docx|doc|rtf|md|txt`), the runnable suite is `ApiExamples/` (12 files); Development paragraph repeats the same instruction twice and mis-formats `` `ApiExamples`/output/ ``.

**Spot checks (clone, venv)**
1. Version 26.7.0 on PyPI; requires-python `>=3.10,<3.13`; deps fpdf2>=2.7.5, olefile>=0.46, pydantic>=2.0.0; dev Pillow>=10.0.0, pytest>=9.0.2: PASS (pyproject + PyPI JSON).
2. `pip install aspose-words-foss`: PASS (published).
3. Load DOCX -> Markdown/PDF -> `get_text()`: PASS (ran on Python 3.13.15 with `--ignore-requires-python`; 232 characters of text).
4. `SaveFormat.DOC` raises `ValueError` ("Supported formats: Markdown, Text, PDF, DOCX"): PASS (ran).
5. `OoxmlCompliance.ISO29500_2008_STRICT` raises NotImplementedError: PASS (docx_writer/writer.py:138-140).
6. `MarkdownSaveOptions().export_underline_formatting = True`: PASS (ran).
7. "16 test files under tests/": **FAIL** (fixtures only; zero `test_*.py` in tests/).
8. "relying only on fpdf2 and olefile": **FAIL** (pydantic is a declared runtime dependency and is imported).
9. 198 public types: **FAIL** (includes ApiExamples classes; live says 146).
10. Dev-instruction `pip install -e ".[dev]" && python -m pytest ApiExamples/ -v --rootdir=ApiExamples -c ApiExamples/pytest.ini`: **partly FAIL** - 26 pass, 1 fails (`ModuleNotFoundError: pdfplumber`, imported at ApiExamples/loading_markdown.py:163 but absent from the `dev` extra).
11. Python 3.13 support: the `<3.13` upper bound looks unnecessary (conversion flows and 26/27 example tests passed on 3.13.15 with `--ignore-requires-python`).
12. Links docs/kb/reference/products/pypi/issues: PASS (200).

**Completeness**: omitted - ApiExamples scripts table and how to run them, readers/writers architecture (Light Document Model), PDF option gaps, DOC read via olefile, known issue #3 (Chinese text lost in PDF/text extraction, standard RTF fails to load) which belongs in Scope and Limitations.

**Upstream defects (ready-to-file)**
- *Issue 1 - dev extras miss pdfplumber (low-medium)*
  Title: `pip install -e ".[dev]" then pytest ApiExamples fails: pdfplumber is imported but not in the dev extra`
  Body: `ApiExamples/loading_markdown.py::LoadingMarkdown::test_save_markdown_with_base64_image_to_docx_and_pdf imports pdfplumber (line 163), but pyproject.toml [project.optional-dependencies].dev lists only Pillow>=10.0.0 and pytest>=9.0.2. Repro: fresh venv, pip install -e ".[dev]", python -m pytest ApiExamples/ -v --rootdir=ApiExamples -c ApiExamples/pytest.ini -> 1 failed, 26 passed ("ModuleNotFoundError: No module named 'pdfplumber'"). Add pdfplumber to the dev extra (or importorskip it).`
- *Issue 2 - Python upper bound <3.13 (low)*
  Title: `Consider lifting requires-python <3.13; library and ApiExamples work on Python 3.13`
  Body: `requires-python = ">=3.10,<3.13" blocks installation on 3.13 for all users. With pip install --ignore-requires-python on CPython 3.13.15 (Windows), Document("tests/data/input/test_full_article.docx").save(".md"/".pdf") and get_text() work and 26 of 27 ApiExamples tests pass (the 27th is the pdfplumber issue). If there is a specific 3.13 incompatibility, please document it in README; otherwise add 3.13 to CI and to the classifiers and drop the cap. Add a Python 3.13 job to CI (there is no .github/workflows directory at all).`
- *Note*: upstream issue #3 (Chinese text lost in PDF and text extraction; standard RTF fails to load) is already open - do not duplicate; mention in README limitations in any reseal.

**Verdict: DO_NOT_PUSH** (confidence high). Reseal with a Python 3.12 interpreter (so the 12 examples verify) would be needed before it could even match live; since live is already template-shaped and richer, the right action is "no update".

---

## 10. What could not be verified

- Builds/tests for Java (Cells, Slides), C++ (Cells), Rust (Cells): no JDK/Maven/CMake/g++/cargo on this machine; example compile results and test passes for those repos rely on the sealed receipts or on file inspection.
- Slides .NET full test suite (not run; only Presentation load/save, Pdf refusal and the live Quick Start were run).
- Counts of public types (195/183/130/213/264/238/198) were not independently recounted (not derivable cheaply); only the Words 198-vs-146 and Barcode duplication inconsistencies were checked.
- Whether the Cells Cpp `operator[]` compile failure in receipt 2 is real.
- GitHub "license: null" for Cells Cpp/Java/Python came from `gh api repos/...` (GET); no further confirmation was attempted.
