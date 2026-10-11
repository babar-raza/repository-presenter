authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Verified issue drafts the handoff model cannot represent (TC-ISS-01, G6-W01)

Every draft below was reproduced by command on 2026-10-10 at the live default-branch head named in
it; the raw command output is `raw-logs/<log>.txt` (command, head sha, UTC time and exit code are in
each log header). They are **not** handoffs: `schemas/upstream-defect-handoff.schema.json` /
`components/issues/model.py` carry a `triggering_check` that is a README/validation check id
(`BC-02`, `BC-03`, `BC-06`) or `NOT_PROCESSABLE`, and `draft.py` auto-drafts only `BC-02`. A missing
LICENSE, an uninstallable-from-source package, a failing upstream test suite, a stale manifest field
or a contradictory in-repo document is a real upstream defect but not a failure of one of those
checks. These drafts become handoffs when the schema gains a `defect_class` field (card TC-ISS-03,
classes `LICENSE_MISSING_ROOT`, `INSTALL_FAILS`, `TESTS_FAIL`, `PLACEHOLDER_METADATA`,
`DOC_CONTRADICTION`, ...). Until then they are text for the owner. Nothing here has been filed.

Each draft is one defect (TC-ISS-04), with a title, a severity (low / medium / high: how much it
hurts a user or maintainer who hits it), the exact reproduction, expected versus actual, and a
suggested fix. Severity is the lane's judgement, not a schema field.

Drafts that upstream already discloses (U33, U46, U47) are marked **disclosed upstream**: they are
release requests rather than surprises, and the recommendation is not to file them as defects.

---

## Licence and legal

### U01. Cells-Cpp: LICENSE only under License/, so GitHub reports no license
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, revision `9f852d0ff1cfdad2d661556d6b87a8eff8c063a2`, severity low, class LICENSE_MISSING_ROOT, log `license-Cells-Cpp`.
- **Title:** `Aspose.Cells-FOSS-for-Cpp: the MIT license is only in License/LICENSE.txt, so GitHub reports "no license"`
- **Reproduce:** `git ls-files | grep -i -E '^(licen[sc]e|copying)'` prints nothing; `git ls-files | grep -i -E '(^|/)(licen[sc]e|copying)'` prints `License/LICENSE.txt`; `gh api repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp --jq '"license=" + (.license|tostring)'` prints `license=null`.
- **Expected:** GitHub (and package scanners that read the repository root) detect the MIT license. **Actual:** `license=null`; the sidebar shows no license.
- **Fix:** add a `LICENSE` (or `LICENSE.txt`) file at the repository root with the same text; the directory may stay.

### U02. Cells-Java: LICENSE only under License/, so GitHub reports no license
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`, revision `c65329e7257b1311abb9686d7e4957a8cc002955`, severity low, class LICENSE_MISSING_ROOT, log `license-Cells-Java`.
- **Title:** `Aspose.Cells-FOSS-for-Java: the MIT license is only in License/LICENSE.txt, so GitHub reports "no license"`
- **Reproduce:** the same two `git ls-files` commands as U01 print `License/LICENSE.txt` (and a generated `docs/apidocs/legal/LICENSE`) but no root file; `gh api repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Java --jq '"license=" + (.license|tostring)'` prints `license=null`.
- **Expected / actual / fix:** as U01.

### U03. Cells-Python: LICENSE only under License/, so GitHub reports no license
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-Python`, revision `4f6768a7b349a1309644f456eb43bc35f70c16d7`, severity low, class LICENSE_MISSING_ROOT, log `license-Cells-Python`.
- **Title:** `Aspose.Cells-FOSS-for-Python: the MIT license is only in License/LICENSE.txt, so GitHub reports "no license"`
- **Reproduce / expected / actual / fix:** as U01 (`git ls-files` shows only `License/LICENSE.txt`; `license=null`).

### U04. Cells-TypeScript: LICENSE only under License/, so GitHub reports no license
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript`, revision `fc186507e5b7124f4664aa6035f25cfd3112367d`, severity low, class LICENSE_MISSING_ROOT, log `license-Cells-TS`.
- **Title:** `Aspose.Cells-FOSS-for-TypeScript: the MIT license is only in License/LICENSE.txt, so GitHub reports "no license"`
- **Reproduce / expected / actual / fix:** as U01 (`License/LICENSE.txt` is the only match; `license=null`).

### U05. 3D-TypeScript: no LICENSE file although package.json and README declare MIT
- Repository `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, revision `66cb26df3b031f0bf6976d4e88dc89721983afa4`, severity medium (the MIT terms require the notice to travel with copies), class LICENSE_MISSING_ROOT, logs `license-3D-TS`, `node-3D-TS`.
- **Title:** `Aspose.3D-FOSS-for-TypeScript: add a LICENSE file (package.json and the README say MIT, the repository has none)`
- **Reproduce:** `git ls-files | grep -i -E '(^|/)(licen[sc]e|copying)'` prints nothing; `grep -n '"license"' package.json` prints `"license": "MIT"`; `gh api repos/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript --jq '"license=" + (.license|tostring)'` prints `license=null`.
- **Expected:** a root `LICENSE` with the MIT text (the sibling repositories Aspose.3D-FOSS-for-Python, -Java and -.NET each ship one). **Actual:** none; GitHub reports no license.
- **Fix:** add the MIT `LICENSE` at the repository root and add `"files"` to `package.json` so it is published.

---

## 3D-TypeScript (revision `66cb26df3b031f0bf6976d4e88dc89721983afa4`, default branch `master`)

### U06. package.json "main"/"types" point at files the build never produces; adm-zip is a runtime dependency listed only as a devDependency
- Severity medium, class PACKAGING_BROKEN, logs `node-3D-TS`, `npm-registry-3D-TS`. Replacement text for the existing BC-02 npm handoff: `handoff-replacements.md` R2.
- **Title:** `package.json "main"/"types" point at dist/index.js, which the build never produces; adm-zip is required at runtime but listed only in devDependencies`
- **Reproduce** (Node 22.23.3, TypeScript 5.9.3): `npm install && npm run build` (exit 0), `ls dist` prints `aspose`, `node -e "require('.')"`.
- **Actual:** `Error: Cannot find module '/w/dist/index.js'. Please verify that the package.json has a valid "main" entry`. `src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162` and `ThreeMfImporter.ts:53` call `require('adm-zip')`; `package.json` lists `adm-zip` only under `devDependencies`. `package.json` has no `repository`, `homepage`, `bugs` or `files` field (keys: name, version, description, main, types, scripts, keywords, author, license, devDependencies, dependencies).
- **Expected:** `main`/`types` name built files; runtime requires are `dependencies`. **Fix:** add `src/index.ts` re-exporting `./aspose/threed` (or point `main`/`types` at `dist/aspose/threed/index.*`), move `adm-zip` to `dependencies`, add the missing metadata fields.

### U07. `npm run lint` fails: no ESLint configuration is tracked
- Severity low, class TOOLING_BROKEN, log `node-3D-TS`.
- **Title:** `npm run lint fails: ESLint cannot find a configuration file`
- **Reproduce:** `npm install && npm run lint`. **Actual:** `ESLint couldn't find a configuration file.` (ESLint 8.57.1); `package.json` scripts: `"lint": "eslint 'src/**/*.ts'"`, and the README lists `npm run lint` as a development step. **Expected:** lint runs. **Fix:** add an ESLint configuration (`.eslintrc.*` or `eslint.config.*`); also use double quotes around the glob so it works under Windows `cmd`.

### U08. `npx jest`: 4 of 97 tests fail at HEAD
- Severity medium, class TESTS_FAIL, log `node-3D-TS`.
- **Title:** `npx jest: 4 tests fail (3MF round trip, glTF binary export, STL round trip, and a fixture outside the repository)`
- **Reproduce:** `npm install && npx jest`. **Actual:** `Test Suites: 4 failed, 28 passed, 32 total; Tests: 4 failed, 93 passed, 97 total`; failing: `Test3MFMaterialImport > testMaterialImport`, `Test3MFRoundTrip > testRoundTripExportImport`, `TestGltfExporter > testSimpleTriangleBinary`, `TestSceneSaveSTL > testRoundtripFile`. The names of the four failing tests were re-run here; the failure causes below come from an earlier review of the same revision and were not re-derived: `rotation[0].eulerAngles is not a function` (Transform.ts:160), a `RangeError` in the binary glTF writer, an STL round-trip count mismatch, and a fixture path under `foss.3d.python/examples/3mf/` that is outside this repository.
- **Expected:** a green suite on a clean clone. **Fix:** fix or skip the three failing tests and vendor the 3MF fixture into `tests/`.

---

## GIS .NET (revision `b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4`)

(The build failure with the missing README/LICENSE is U51 at the end of this file. It was first written as a `NOT_PROCESSABLE` handoff and withdrawn: that check's redetector re-parses named source files, and a build failure names none, so its recheck can never conclude.)

### U09. Build output is committed: 14 files under obj/, and .gitignore has no obj/ or bin/ rule
- Severity low, class REPO_HYGIENE, logs `build-GIS-NET`.
- **Title:** `Build output is committed (14 files under obj/) and .gitignore does not exclude obj/ or bin/`
- **Reproduce:** `git ls-files | grep -c '/obj/'` prints `14`; `grep -n -E '^(obj|bin)' .gitignore` prints nothing. **Expected:** machine-specific restore state is not tracked. **Fix:** `git rm -r --cached Aspose.GIS.FOSS/obj Aspose.GIS.FOSS.Tests/obj` and add `obj/` and `bin/` to `.gitignore`.

---

## PSD .NET and PSD Python

### U10. PSD-.NET: csproj still has template placeholders (yourorg URLs, Authors "SID")
- Repository `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`, revision `f4e1b261922d514591b898f01346af1c6bf59f92`, severity low-medium (baked into every `.nupkg` because `GeneratePackageOnBuild` is true), class PLACEHOLDER_METADATA, log `placeholders-PSD-NET`.
- **Title:** `Aspose.PSD.FOSS.csproj contains placeholder URLs (github.com/yourorg/...) and Authors "SID"`
- **Reproduce:** `grep -n -E '<(Authors|PackageProjectUrl|RepositoryUrl|GeneratePackageOnBuild)>' src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj`.
- **Actual:** line 13 `<Authors>SID</Authors>`, line 16 `<PackageProjectUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</PackageProjectUrl>`, line 17 `<RepositoryUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</RepositoryUrl>`, line 20 `<GeneratePackageOnBuild>true</GeneratePackageOnBuild>`; `curl` of the `yourorg` URL returns HTTP 404, the real repository `https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-.NET` returns 200.
- **Expected:** real repository URLs and owner. **Fix:** set both URLs to the real repository and `Authors`/`Company` to the intended owner. Note: the missing LICENSE file is already tracked in upstream issue #5 (open); do not duplicate.

### U11. PSD-Python: no pyproject.toml/setup.py, a two-line README, and an empty package __init__
- Repository `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`, revision `664446b97952c063baf828f469995ad2a160bae7`, severity medium, class NOT_INSTALLABLE / README_MISSING, logs `psdpy-structure`, `ast-PSD-Python`.
- **Title:** `No pyproject.toml/setup.py (package is not installable), README is a two-line placeholder, and aspose_psd_foss/__init__.py is empty`
- **Reproduce:** `ls` (README.md, aspose_psd_foss, aspose_psd_foss_test); `python -m pip install --dry-run --no-deps --no-build-isolation .`; `wc -c README.md`; `wc -l aspose_psd_foss/__init__.py`.
- **Actual:** `ERROR: Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.`; `README.md` is 67 bytes (`# Aspose.PSD-FOSS-for-Python` and `FOSS version of Aspose.PSD for Python`); `__init__.py` has 0 lines (no public API is exported; callers must import deep modules such as `aspose_psd_foss.psdimage`). All 82 `.py` files do parse (`ast.parse`), so the code itself is present.
- **Expected:** an installable package with a README describing install, a quick start and the supported scope. **Fix:** add a `pyproject.toml` (name, version, `requires-python`, license, packages), export the public API from `__init__.py`, write a README. The missing LICENSE is tracked in upstream issue #4 (open); do not duplicate.

### U12. PSD-Python: generated MSBuild files are committed as .py modules
- Same revision, severity low, class REPO_HYGIENE, log `psdpy-structure`.
- **Title:** `Generated MSBuild obj/ files are committed as Python modules`
- **Reproduce:** `git ls-files | grep '/obj/'`. **Actual:** four files: `aspose_psd_foss/obj/debug/net10_0/aspose_psd_foss_assemblyinfo.py`, `..._globalusings_g.py`, and the two `aspose_psd_foss_test/obj/debug/net10_0/` counterparts; they are C# build artifacts with no meaning in a Python package. **Fix:** delete them and add `obj/` to `.gitignore`.

### U13. PSD-Python: plain `pytest` collects no tests (modules are named *tests.py)
- Same revision, severity low-medium, class TESTS_NOT_DISCOVERED, log `pytest-PSD-Python`.
- **Title:** `pytest finds no tests: the test modules are named *tests.py`
- **Reproduce:** `python -m pytest` from the repository root. **Actual:** `no tests ran`; `aspose_psd_foss_test/` holds 11 modules matching `*tests.py` and none matching `test_*.py`. Passing them by path does run them here, but the tests then fail with `FileNotFoundError` for `aspose_psd_foss_test/testdata/*.psd` (paths doubled with the working directory); the fixture helper `aspose_psd_foss_test/psdtestfixturebase.py:73` resolves test data from `os.path.abspath(os.getenv('PYTEST_CURRENT_TEST', ''))`, an environment variable that holds a test id rather than a directory. **Expected:** `pytest` runs the suite. **Fix:** rename the modules to `test_*.py` (or set `python_files = "*tests.py"` once a `pyproject.toml` exists) and resolve test data from `Path(__file__).parent / "testdata"`.

---

## Cells-Python (revision `4f6768a7b349a1309644f456eb43bc35f70c16d7`)

### U14. save_as_csv / load_csv default to the OS locale encoding; CJK text raises UnicodeEncodeError on Windows
- Severity medium, class LOCALE_DEPENDENT_BEHAVIOUR, log `csv-encoding-Cells-Python`.
- **Title:** `save_as_csv default encoding is locale-dependent; non-Latin-1 text raises UnicodeEncodeError on Windows`
- **Reproduce** (Python 3.13.15, Windows, locale encoding cp1252): `PYTHONPATH=. python -c "from aspose.cells_foss import Workbook; wb = Workbook(); ws = wb.get_active_worksheet(); ws.cells['A1'].value = '你好'; wb.save_as_csv('o.csv')"`.
- **Actual:** `UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-1: character maps to <undefined>` from `csv_handler.py:192 writer.writerow`. `aspose/cells_foss/csv_handler.py:29-31` defines `_system_encoding()` as `locale.getpreferredencoding(False) or 'utf-8'`. With `PYTHONUTF8=1` the same call succeeds and writes `你好`.
- **Expected:** a deterministic default (UTF-8) so a file written on one machine reads the same on another. **Fix:** default `CSVSaveOptions.encoding`/`CSVLoadOptions.encoding` to `utf-8` (optionally honouring `write_bom`) and document the option.

### U15. Two tests need an input/ directory that is not in the repository
- Severity low-medium, class TESTS_FAIL, log `tests-input-dir-Cells-Python`.
- **Title:** `examples/test_xlsx_to_json.py and test_xlsx_to_markdown.py fail on a clean checkout: input/ is not tracked`
- **Reproduce:** `git ls-files | grep -E '(^|/)input/'` prints nothing; `PYTHONPATH=. python -m pytest -q examples/test_xlsx_to_json.py examples/test_xlsx_to_markdown.py`.
- **Actual:** `2 failed, 19 passed`: `test_sales_report_to_json` (`Input file .../input/sales_report_comprehensive.xlsx does not exist`) and `test_convert_all_xlsx_to_markdown` (`No XLSX files found in input directory`). **Fix:** commit the fixture workbooks, generate them in a fixture, or skip when absent.

### U16. The wheel installs a top-level `examples` package into site-packages
- Severity medium, class PACKAGING_BROKEN, log `wheel-Cells-Python`.
- **Title:** `pyproject packages = [..., "examples"] installs a top-level examples package next to the library`
- **Reproduce:** `sed -n 48,53p pyproject.toml`; `pip wheel . --no-deps -w whl`; list the wheel.
- **Actual:** `[tool.setuptools] packages = ["aspose", "aspose.cells_foss", "examples"]` with `examples = ["*.py"]` package data; the built wheel `aspose_cells_foss-26.7.0-py3-none-any.whl` has top-level entries `aspose` (55), `examples` (32: `__init__.py`, `output_path_helper.py`, `test_*.py`, ...) and the dist-info. A generic top-level `examples` name collides with any other project or the user's own package. **Fix:** remove `examples` from `packages` and `package-data`; ship tests in an sdist only.

### U17. project.urls use the old repository name
- Severity low, class STALE_METADATA, log `urls-Cells-Python`.
- **Title:** `project.urls point at github.com/aspose-cells-foss/aspose-cells-python (the repository was renamed)`
- **Reproduce:** `grep -n -A5 'project.urls' pyproject.toml`; `curl -s -o /dev/null -w '%{http_code} %{url_effective}' -L https://github.com/aspose-cells-foss/aspose-cells-python`. **Actual:** Homepage, Documentation, Repository and Issues use the old name; the old URL answers `200 -> https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python` only through GitHub's rename redirect. **Fix:** use the current repository name.

---

## Words-Python (revision `2d2efee2787cb9e56d071d17f8d7b740dce8b784`)

### U18. dev extra omits pdfplumber, so one documented ApiExamples test fails
- Severity low-medium, class TESTS_FAIL, log `pdfplumber-Words-Python`. (Also observed, not drafted: `requires-python = ">=3.10,<3.13"` makes `pip install .` refuse Python 3.13.15 -- `raw-logs/requires-python-Words-Python.txt`; lifting the cap is a maintainer decision, not a defect.)
- **Title:** `pip install -e ".[dev]" then the documented pytest run fails: pdfplumber is imported but not in the dev extra`
- **Reproduce:** fresh venv, `pip install -e ".[dev]"` (add `--ignore-requires-python` on Python 3.13), `python -m pytest ApiExamples/ -q --rootdir=ApiExamples -c ApiExamples/pytest.ini`.
- **Actual:** `1 failed, 26 passed`; `ApiExamples/loading_markdown.py:163` does `import pdfplumber` -> `ModuleNotFoundError: No module named 'pdfplumber'`; the `dev` extra lists only `Pillow>=10.0.0` and `pytest>=9.0.2`. **Fix:** add `pdfplumber` to the `dev` extra (or `pytest.importorskip` it).

---

## Cells-Rust (revision `1a6004af47b1ef15385f9d36d381a8172428cc7e`, default branch `master`)

### U19. The crate ships no tests: cargo test runs 0 tests and CI passes vacuously
- Severity medium, class NO_TESTS, logs `cargo-test-Cells-Rust`, `notests-Cells-Rust`.
- **Title:** `No automated tests: cargo test --all-targets runs 0 tests`
- **Reproduce:** `git ls-files tests | wc -l` (0); `git grep -E '#\[(test|cfg\(test\))' -- '*.rs' | wc -l` (0); `cargo test --all-targets` (Docker `rust:1`, cargo 1.99.0).
- **Actual:** exit 0 with 15 targets each reporting `running 0 tests` / `test result: ok. 0 passed`. `.github/workflows/ci.yml` runs `cargo test --all-targets` (line 57) and `cargo bench` (line 72) but the tree has no `tests/` directory, no `#[test]`, and no bench targets, so a regression in XLSX read/write is not caught. **Fix:** add round-trip integration tests under `tests/` (the sample binaries already create, save, reload and print workbooks), and drop the `cargo bench` step or add bench targets.

### U20. README Installation still says "Once the repository is live at its real GitHub location"
- Severity low, class STALE_DOC, log `notests-Cells-Rust`.
- **Title:** `README Installation text is a pre-publication leftover`
- **Reproduce:** `grep -n -i 'once the repository is live' README.md` -> line 106: "Once the repository is live at its real GitHub location, add it as a Git dependency in `Cargo.toml`:". **Actual:** the repository is public. **Fix:** replace with the real Git URL snippet.

---

## Cells-Java (revision `c65329e7257b1311abb9686d7e4957a8cc002955`, default branch `master`)

### U21. Committed Javadoc documents a package that no longer exists
- Severity low, class STALE_GENERATED_DOC, log `javadoc-Cells-Java`.
- **Title:** `docs/apidocs is generated for the removed com.aspose.cells_foss package ("cells-foss 1.0.0")`
- **Reproduce:** `grep -o '<title>[^<]*' docs/apidocs/index.html`; `grep -o 'content="0;[^"]*' docs/apidocs/index.html`; `git ls-files docs/apidocs/com/aspose/cells_foss | wc -l`; `ls src/main/java/org/aspose`; `grep -n -m3 '<groupId>\|<artifactId>\|<version>' pom.xml`.
- **Actual:** the page title is `cells-foss 1.0.0 API` and it redirects to `com/aspose/cells_foss/package-summary.html` (112 tracked files under `docs/apidocs/com/aspose/cells_foss`), while the source package is `org.aspose.cells_foss` and the artifact is `org.aspose:aspose-cells-foss:26.7.0`; the README (lines 274 and 526) presents `docs/apidocs/` as the generated API docs. **Fix:** regenerate with `mvn javadoc:javadoc` or delete the folder and publish Javadoc from CI.

### U22. Mojibake in pom.xml and Agents.md
- Severity low, class ENCODING, log `javadoc-Cells-Java`.
- **Title:** `pom.xml and Agents.md contain mis-encoded characters (double-decoded UTF-8)`
- **Reproduce:** `grep -n 'â€' pom.xml`; `grep -n '鈫' Agents.md`. **Actual:** `pom.xml:62` `<!-- Apache POI â€” OOXML (xlsx) support -->`; `Agents.md:46` `... `mvn javadoc:javadoc` 鈫? output at ...`. **Fix:** re-save both as UTF-8 with the intended em dash and arrow.

---

## C++ build and example paths

### U23. Cells-Cpp: Aspose.Cells.Foss.Cpp.Tests/README.md uses a workspace/ directory that does not exist
- Revision `9f852d0ff1cfdad2d661556d6b87a8eff8c063a2`, severity low-medium (first command fails), class DOC_COMMAND_BROKEN, log `paths-Cells-Cpp-tests-readme`.
- **Title:** `Aspose.Cells.Foss.Cpp.Tests/README.md references a non-existent workspace/ directory`
- **Reproduce:** `grep -n workspace Aspose.Cells.Foss.Cpp.Tests/README.md`; `ls -d workspace`; `git ls-tree --name-only HEAD`. **Actual:** lines 8, 9, 15 and 19 use `.\workspace\Aspose.Cells.Foss.Cpp.Tests` and say the tests add `workspace/Aspose.Cells.Foss.Cpp` as a CMake subdirectory; there is no `workspace/` directory (the top level is `.gitignore AGENTS.md Aspose.Cells.Foss.Cpp.Tests Aspose.Cells.Foss.Cpp License README.md samples`). **Fix:** `cd Aspose.Cells.Foss.Cpp.Tests; cmake -S . -B build; cmake --build build; ctest --test-dir build --output-on-failure`.

### U24. Email-Cpp: examples/README.md build commands reference a non-existent cpp/ directory
- Repository `aspose-email-foss/Aspose.Email-FOSS-for-Cpp`, revision `c844a467cf7f2503819b655f4d6ceaef91056c40`, severity low-medium, class DOC_COMMAND_BROKEN, log `paths-Email-Cpp`.
- **Title:** `examples/README.md build commands reference a non-existent cpp/ directory`
- **Reproduce:** `grep -n 'cpp/' examples/README.md`; `ls -d cpp`; `git ls-files CMakeLists.txt CMakePresets.json`. **Actual:** line 30 `cmake -S cpp -B cpp/out/build/examples -DASPOSE_EMAIL_FOSS_BUILD_EXAMPLES=ON -DASPOSE_EMAIL_FOSS_BUILD_TESTS=OFF` and lines 31, 46, 62 `cmake --build cpp/out/build/examples ... --target aspose_email_foss_example_*`; there is no `cpp/` directory, `CMakeLists.txt` and `CMakePresets.json` are at the repository root. **Fix:** `cmake -S . -B out/build/examples ...` and `cmake --build out/build/examples ... --target aspose_email_foss_example_create_msg_and_eml` (likewise `_msg_reader`, `_msg_summary`).

### U25. Email-.NET: examples/README.md run commands reference a non-existent csharp/ directory
- Repository `aspose-email-foss/Aspose.Email-FOSS-for-.Net`, revision `59125b4732df0eedbc4d4c2ab978698ed4348eb7`, severity low-medium, class DOC_COMMAND_BROKEN, log `paths-Email-NET`.
- **Title:** `examples/README.md run commands point to non-existent csharp/examples/... paths`
- **Reproduce:** `grep -n 'csharp/' examples/README.md`; `ls -d csharp`; `git ls-files 'examples/*.csproj'`. **Actual:** lines 30, 45 and 61 run `dotnet run --project csharp/examples/<name>/<name>.csproj`; there is no `csharp/` directory, the projects are `examples/create_msg_and_eml/`, `examples/msg_reader/`, `examples/msg_summary/`. **Fix:** drop the `csharp/` prefix.

### U26. Email-.NET: project version 0.1.0 and CHANGELOG disagree with the published package (26.7.0)
- Same repository and revision as U25, severity low-medium, class VERSION_MISMATCH, log `nuget-Email-NET`.
- **Title:** `Project version (0.1.0) and CHANGELOG disagree with the published NuGet package (26.7.0)`
- **Reproduce:** `grep -rn '<Version>' --include=*.csproj .`; `grep -n -m3 '^## \[' CHANGELOG.md`; `curl -s https://api.nuget.org/v3-flatcontainer/aspose.email.foss/index.json`; `grep -n PackageReference README.md`. **Actual:** `src/Aspose.Email.Foss/Aspose.Email.Foss.csproj:5 <Version>0.1.0</Version>`; `CHANGELOG.md:5 ## [0.1.0] - 2026-03-18` is the newest entry; NuGet lists only `26.7.0`; the README (line 76) shows `<PackageReference Include="Aspose.Email.Foss" Version="26.7.0" />`. **Fix:** align the csproj version and changelog with the published release.

---

## 3D-.NET (revision `52b0f00ebf28a0b4173921725ff170685ec2c502`)

(The README Quick Start `NotImplementedException` is the new BC-03 handoff `aspose-3d-foss__Aspose.3D-FOSS-for-.NET__af8da760...`.)

### U27. The test suite needs an untracked testdata/ directory: 53 of 183 tests fail on a clean checkout
- Severity medium, class TESTS_FAIL, log `testdata-3D-NET`.
- **Title:** `Test suite requires an untracked testdata/ directory (53 of 183 tests fail on a clean checkout)`
- **Reproduce:** `grep -n -i testdata .gitignore`; `git ls-files | grep -i -c testdata`; `dotnet test src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj`.
- **Actual:** `.gitignore:8` is `testdata`; 0 tracked testdata files; `Failed! - Failed: 53, Passed: 130, Skipped: 0, Total: 183` (net10.0), 47 of them `FileNotFoundException : Test file not found: ../../../../../../testdata/...` (for example `input/cube.obj`, `stl\stl_ascii.stl`, `gltf/simple_cube.gltf`, `3mf/box.3mf`). **Fix:** commit the fixtures or generate them in the tests.

### U28. Build logs and a .bak file are committed
- Severity low, class REPO_HYGIENE, log `hygiene-3D-NET`.
- **Title:** `Stray build.log, test.log and FileFormat.cs.bak are committed`
- **Reproduce:** `git ls-files | grep -E '\.(log|bak)$'`; `grep -n -E 'log|bak' .gitignore`. **Actual:** `src/main/Aspose.ThreeD/Aspose/ThreeD/FileFormat.cs.bak`, `src/main/Aspose.ThreeD/build.log`, `src/test/Aspose.ThreeD.Tests/test.log` are tracked and `.gitignore` has no rule for them. **Fix:** remove them and add the patterns to `.gitignore`.

### U29. Package version 26.1.0 vs documentation describing 26.2.0
- Severity low, class VERSION_MISMATCH, log `hygiene-3D-NET`.
- **Title:** `csproj Version is 26.1.0 and NuGet has only 26.1.0, but AGENTS.md and docs/release-26.2.0.md describe 26.2.0`
- **Reproduce:** `grep -n -m2 '<Version>' src/main/Aspose.ThreeD/Aspose.ThreeD.csproj` (line 9: `26.1.0`); `curl -s https://api.nuget.org/v3-flatcontainer/aspose.3d.foss/index.json` (`["26.1.0"]`); `grep -n -m3 '26.2.0' AGENTS.md docs/release-26.2.0.md`. **Actual:** `AGENTS.md:5` "implementation of Aspose.3D for .NET 26.2.0" and `docs/release-26.2.0.md:5` "FOSS Version: 26.2.0". **Fix:** publish 26.2.0 or correct the documents.

---

## 3D-Java (revision `3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3`, default branch `main`)

### U30. FILE_FORMATS.md contradicts itself: duplicate glTF and FBX sections with opposite status
- Severity low-medium, class DOC_CONTRADICTION, log `fileformats-3D-Java`.
- **Title:** `FILE_FORMATS.md has duplicate glTF/GLB and FBX sections with opposite status`
- **Reproduce:** `grep -n -i -E '^#+ .*(gltf|fbx)' FILE_FORMATS.md`. **Actual:** headings at lines 32 and 48 (`### glTF/GLB`) and 39 and 53 (`### FBX`); the summary table says glTF "Full import/export" and FBX "Import only (binary)", the sections at lines 32 and 39 agree, the later duplicates at lines 48-56 say "Import: Not implemented / Export: Not implemented ... (format not yet implemented)". `src/main/java/com/aspose/threed/FileFormat.java` declares `GltfReader` (604) and `GltfWriter` (803). **Fix:** delete the stale duplicate sections.

### U31. The only workflow never runs the tests
- Severity medium, class NO_CI_TESTS, log `fileformats-3D-Java`.
- **Title:** `No CI runs the test suite: maven-central-release.yml builds with -DskipTests`
- **Reproduce:** `ls .github/workflows`; `grep -n 'mvn' .github/workflows/*.yml`. **Actual:** the only workflow is `maven-central-release.yml`; its build steps are `mvn -B clean verify -Dgpg.skip=true -DskipTests` (lines 64, 150) and `mvn -B clean verify -DskipTests` (240), `mvn -B deploy -DskipTests` (268). **Fix:** add a workflow that runs `mvn -B verify` on push and pull request.

### U32. README refers to an "Upstream Issues" section that does not exist
- Severity low, class DOC_BROKEN_REFERENCE, log `fileformats-3D-Java`.
- **Title:** `README says "see Upstream Issues in this repository" but there is no such section`
- **Reproduce:** `grep -n -i 'upstream issues' README.md`; `git grep -n -i 'upstream' -- '*.md'`. **Actual:** the only match is `README.md:587` ("... do not rely on OBJ import from the published package (see Upstream Issues in this repository, and build from source instead if you need it)"). **Fix:** add the section or link the issue.

### U33. Maven Central 26.5.0 ships stub OBJ/glTF/FBX loaders (**disclosed upstream**)
- Severity medium, class PUBLISHED_ARTIFACT_STALE, log `jar-stubs-3D-Java`. README.md:587 already warns that the published artifact "still ships a stub". Recommendation: do not file as a defect; it is a release request.
- **Title (if filed):** `Publish a release built from HEAD: the 26.5.0 jar on Maven Central ships OBJ, glTF and FBX loader/saver stubs`
- **Reproduce:** `curl -s https://repo1.maven.org/maven2/org/aspose/aspose-3d-foss/maven-metadata.xml` (latest and only version `26.5.0`); download the jar and list `FileFormat$*Loader/Saver` classes. **Actual:** `FileFormat$ObjLoader` 790 B, `$ObjSaver` 752 B, `$GltfLoader` 793 B, `$GltfSaver` 755 B, `$FbxLoader` 790 B, `$FbxSaver` 752 B; only `$StlLoader` (6046 B) and `$StlSaver` (7176 B) are substantive; the jar has no `ObjReader`/`GltfReader` while HEAD has them. **Fix:** release from HEAD.

---

## 3D-Python (revision `65b1f577c0f16d0d9112bb6c1153d3024543ac02`, default branch `master`)

(`Scene.save()` to `.obj` raising `TypeError` is the existing BC-03 handoff `aspose-3d-foss__Aspose.3D-FOSS-for-Python__094c4163...`.)

### U34. setup.py url points to a repository that does not exist
- Severity low, class STALE_METADATA, log `seturl-3D-Python`.
- **Title:** `setup.py url "https://github.com/aspose-3d/Aspose.3D-for-Python" returns 404`
- **Reproduce:** `grep -n 'url=' setup.py`; `curl -s -o /dev/null -w '%{http_code}' https://github.com/aspose-3d/Aspose.3D-for-Python`. **Actual:** `setup.py:15` -> HTTP 404 (and `api.github.com/repos/aspose-3d/Aspose.3D-for-Python` 404); it is the package's PyPI Homepage. **Fix:** use `https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python`.

### U35. `python -m unittest discover tests/` errors on a clean clone because examples/ is gitignored
- Severity low-medium, class TESTS_FAIL, log `unittest-3D-Python`.
- **Title:** `unittest discover tests/ fails on a fresh clone: the tests read examples/, which .gitignore excludes`
- **Reproduce:** `grep -n -i '^examples' .gitignore`; `git ls-files examples | wc -l`; `PYTHONIOENCODING=utf-8 python -m unittest discover tests/`. **Actual:** `.gitignore:8` is `examples`, 0 tracked files under `examples/`; `Ran 123 tests ... FAILED (errors=5, skipped=5)` with `FileNotFoundError` for `examples/stl/stl_ascii.stl`, `examples/stl/stl_binary.stl`, `examples/gltf2/Corset/glTF/Corset.gltf`, `examples/gltf2/BoomBox/glTF/BoomBox.gltf`. **Fix:** track the fixtures under `tests/` (not `examples/`) or generate them.

---

## HTML-Python and Page-Python

### U36. HTML-Python: tests/test_css/w3c package is missing, so pytest fails at collection
- Repository `aspose-html-foss/Aspose.HTML-FOSS-for-Python`, revision `bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11`, severity low-medium, class TESTS_FAIL, log `w3c-fixture-HTML-Python`.
- **Title:** `python -m pytest fails at collection: tests/test_css/w3c is not in the repository`
- **Reproduce:** `git ls-files tests/test_css/w3c | wc -l` (0); `sed -n 19p tests/test_css/test_w3c_fixture_loader.py`; `PYTHONPATH=src python -m pytest --collect-only -q tests/test_css/test_w3c_fixture_loader.py`. **Actual:** the module imports `tests.test_css.w3c.conftest` -> `ModuleNotFoundError: No module named 'tests.test_css.w3c'`; `Interrupted: 1 error during collection`. **Fix:** commit the `w3c` fixture package or ignore the loader test. (The `build-backend` defect is already the existing BC-02 handoff.)

### U37. Page-Python: `pip install .` fails on a fresh clone because local/Version.txt is gitignored
- Repository `aspose-page-foss/Aspose.Page-FOSS-for-Python`, revision `43cef367cd0b2cf00cc03064ca9d29d1ff507967`, severity medium (the README's source-build path reads the same file), class INSTALL_FAILS, log `version-txt-Page-Python`.
- **Title:** `pip install . and python package.py build fail on a fresh clone: local/Version.txt is missing`
- **Reproduce:** `git ls-files local | wc -l` (0); `grep -n '^local/' .gitignore` (line 9); `sed -n 35p setup.py`; `sed -n 45p package.py`; `pip install . --no-deps`. **Actual:** `FileNotFoundError: [Errno 2] No such file or directory: '.../local/Version.txt'` while getting requirements to build the wheel; `setup.py:35` and `package.py:45` both read `local/Version.txt`. **Fix:** commit a default `local/Version.txt` or fall back to the `pyproject.toml` version.

### U38. Page-Python: aspose.page.mcp.server.run() raises TypeError with the default transport
- Same revision, severity medium, class RUNTIME_ERROR, log `mcp-run-Page-Python`.
- **Title:** `aspose.page.mcp.server.run() raises TypeError: host/port are passed to the stdio transport`
- **Reproduce** (fastmcp 4.1.0): `PYTHONPATH=src python -c "from aspose.page.mcp import server; server.run()"`. **Actual:** `TypeError: TransportMixin.run_stdio_async() got an unexpected keyword argument 'host'`; `src/aspose/page/mcp/server.py:29-37` calls `server.run(host=host, port=port)` with no `transport`. fastmcp is not declared in `pyproject.toml` (`dependencies = ["skia-python"]`). **Fix:** pass `transport="http"` with host/port (or call `server.run()` for stdio), declare `fastmcp` as an optional dependency, add a test.

### U39. Page-Python: two tests import a top-level `tools` package that is not in the repository
- Same revision, severity low-medium, class TESTS_FAIL, log `tools-package-Page-Python`.
- **Title:** `tests/test_metrics_api_v1.py and tests/test_codex_hook_post_metrics.py import a missing tools package`
- **Reproduce:** `git grep -n -E '^(from|import) tools' -- tests`; `git ls-files tests/tools`; `PYTHONPATH=src python -m pytest --collect-only -q tests/test_metrics_api_v1.py tests/test_codex_hook_post_metrics.py`. **Actual:** `ImportError: cannot import name 'codex_hook_post_metrics' from 'tools' (unknown location)`; both files error at collection; `tests/tools/` holds only `pdf_render.py` and `pdf_validate.py`; the Makefile (lines 52, 73, 96, 108) runs `tools/metrics_api_v1.py`, which is absent. **Fix:** add the `tools/` package or remove the tests and Makefile targets.

---

## README and documentation consistency

### U40. Words-.NET: README says the NuGet package is "landing soon" and gives two different type counts
- Repository `aspose-words-foss/Aspose.Words-FOSS-for-.NET`, revision `0d3f1add920f5294d726b4f286c2d6ba7c3ae22c`, default branch `master`, severity low, class STALE_DOC, log `nuget-Words-NET`.
- **Title:** `README says the NuGet package is "landing soon" although it is published, and gives two different public-type counts (615 vs 617)`
- **Reproduce:** `grep -n -i 'landing soon' README.md`; `curl -s https://api.nuget.org/v3-flatcontainer/aspose.words.foss/index.json`; `grep -n -E 'all (615|617)|(615|617) (public )?types' README.md`. **Actual:** `README.md:952` "The NuGet package and new formats are landing soon."; NuGet lists `26.2.0` and `26.3.0`; `README.md:901` says 615 public types, `:942` says 617. **Fix:** update the sentence and make the counts agree.

### U41. Cells-Go: README lists only four formula functions and omits shipped APIs; stray top-level heading
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-Go`, revision `99c789e9175f2b12ad82bafeeba148ddcc1367fb`; severity low-medium, class STALE_DOC, log `stale-Cells-Go`.
- **Title:** `README is out of date: formula engine, chart/pivot/conditional-format/VBA APIs, and a malformed heading`
- **Reproduce:** `sed -n '59p;83,84p' README.md`; `grep -o -E 'case "[A-Z]+"' aspose/cells_foss/formula_engine.go | sort -u`; `for s in AddChart AddPivotTable AddConditionalFormatting SetVBAProject; do grep -c $s README.md; done`; `sed -n 105p README.md`.
- **Actual:** README lines 59 and 83-84 say the engine supports `SUM`, `AVERAGE`, `MAX` and `MIN`; `formula_engine.go` implements 22 functions (ABS AND AVERAGE CONCAT COUNT COUNTIF IF LEFT LEN LOWER MAX MID MIN NOT OR POWER RIGHT ROUND SQRT SUM UPPER VLOOKUP); `AddChart` (chart.go:84), `AddPivotTable` (pivot_table.go:65), `AddConditionalFormatting` (conditional_format.go:88) and `SetVBAProject` (macro.go:33) each have 0 README hits; `README.md:105` is a top-level heading `# Requires **Go 1.24.5+** ...` inside Installation, which also breaks the Navigation list; the latest tag is `v26.7.1`. **Fix:** update the capability text and API reference, make line 105 a normal paragraph, cut a release if the new APIs should be installable.

### U42. Cells-Go: generated CSV output is committed although AGENTS.md says not to
- Same repository and revision as U41, severity low, class REPO_HYGIENE, log `stale-Cells-Go`.
- **Title:** `examples/outputfiles/employees.csv and exported.csv are committed; .gitignore covers only *.xlsx`
- **Reproduce:** `git ls-files 'examples/outputfiles/*'`; `grep -n 'outputfiles' .gitignore AGENTS.md`. **Actual:** `.gitkeep`, `employees.csv`, `exported.csv` are tracked; `.gitignore:31` is `examples/outputfiles/*.xlsx`; `AGENTS.md:24` says "Never commit generated `.xlsx` files or contents from `outputfiles/`". **Fix:** remove the CSVs and ignore `examples/outputfiles/*` except `.gitkeep`.

### U43. PDF-Java: README and docs/limitations.md list XLSX, Markdown and DOCX conversion as unsupported, but they are implemented
- Repository `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`, revision `736cedaa2922e4952f429364bdb9a4bbb1d97863`, severity medium (users are told a shipped feature is absent), class DOC_CONTRADICTION, log `limitations-PDF-Java`.
- **Title:** `README and docs/limitations.md list XLSX, Markdown and DOCX conversion as unsupported, but docs/conversion.md and SaveFormat implement them`
- **Reproduce:** `sed -n 1608,1611p README.md`; `sed -n 16p docs/limitations.md`; `sed -n 3p docs/conversion.md`; `grep -n -E '^    (Xlsx|Excel|Markdown)' src/main/java/org/aspose/pdf/SaveFormat.java`; `grep -n -E 'SaveFormat.Xlsx|SaveFormat.Markdown' CHANGELOG.md`.
- **Actual:** `README.md:1608-1611` say conversion to DOCX, XLSX, PPTX, EPUB, MOBI, Markdown "are not supported" and conversion from DOC, DOCX, XLSX, PPTX ... "as input are not supported"; `docs/limitations.md:16` lists XLSX, PPTX, EPUB, MOBI, Markdown, LaTeX, ZUGFeRD as unsupported; `docs/conversion.md:3` says "PDF <-> HTML, PDF <-> DOCX, PDF <-> XLSX and PDF <-> Markdown"; `SaveFormat.java` declares `Xlsx` (26), `Excel` (32), `Markdown` (39); `CHANGELOG.md:121,146` record `SaveFormat.Xlsx` and `SaveFormat.Markdown` as new. **Fix:** reduce the unsupported lists to the formats that really are unsupported.

### U44. PDF-Python: the library attaches an INFO StreamHandler to stdout at import time
- Repository `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`, revision `8f0edbe6930f300088fc72f64711be3265a723d1`; severity medium (corrupts programs that write data to stdout), class LIBRARY_SIDE_EFFECT, log `stdout-logging-PDF-Python`.
- **Title:** `Library writes INFO log lines to stdout on Document close (engine/logging.py)`
- **Reproduce:** `sed -n 8,13p src/aspose_pdf/engine/logging.py`; `python -c "from aspose_pdf import Document
with Document('tests/fixtures_4pages.pdf') as d: pass"` with stderr discarded.
- **Actual:** the module sets the `aspose_pdf` logger to INFO and adds `logging.StreamHandler(sys.stdout)`; stdout receives `2026-10-10 20:17:29,028 [INFO] aspose_pdf: Document resources released.`. **Expected:** a library adds only a `NullHandler` and leaves configuration to the application (https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library). **Fix:** remove the handler and level configuration.

### U45. Imaging-.NET: csproj RepositoryUrl/PackageProjectUrl use the old repository name
- Repository `aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET`, revision `6ebb2091ad016a46489bef65eaad0f1eb9843e1a`, severity low, class STALE_METADATA, log `imaging-recheck`. Also a finding about the existing handoff, see the inventory (STALE).
- **Title:** `Aspose.Imaging.Foss.csproj RepositoryUrl/PackageProjectUrl use the old repository name`
- **Reproduce:** `grep -n 'RepositoryUrl\|PackageProjectUrl' src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj`; `curl -s -o /dev/null -w '%{http_code}' -L https://github.com/aspose-imaging-foss/Aspose.Imaging.Foss`. **Actual:** lines 19 and 20 are `https://github.com/aspose-imaging-foss/Aspose.Imaging.Foss`, which answers 200 only through GitHub's rename redirect to `Aspose.Imaging-FOSS-for-.NET`. **Fix:** use the current repository URL.

### U46. Slides-Java: Maven Central only has 26.7.0 (**disclosed upstream**)
- Repository `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`, revision `620a2614418854b4a18966a361e6907ddc88c7cb`, severity medium (the published version predates an XML hardening fix), class PUBLISHED_ARTIFACT_STALE, log `maven-Slides-Java`. `SECURITY.md:10-14` and `README.md:113-115` already state this. Recommendation: do not file as a defect.
- **Title (if filed):** `Publish 26.8.0: Maven Central still serves only 26.7.0, which predates the XML hardening fix`
- **Reproduce:** `curl -s https://repo1.maven.org/maven2/org/aspose/aspose-slides-foss/maven-metadata.xml | grep -E '<(latest|release|version)>'` (all `26.7.0`); `curl -s -o /dev/null -w '%{http_code}' .../26.8.0/aspose-slides-foss-26.8.0.pom` (404); `grep -n -m1 '<version>' pom.xml` (26.8.0). **Fix:** publish 26.8.0 (or 26.7.1).

### U47. Slides-Python: the PyPI release 26.8.0 lacks Hyperlink and other features the README examples use (**disclosed upstream**)
- Repository `aspose-slides-foss/Aspose.Slides-FOSS-for-Python`, revision `4e63447ba79d1c27a5192844847d9f872c5b92ad`, severity low-medium, class PUBLISHED_ARTIFACT_STALE, log `pypi-Slides-Python`. `README.md:134` already says "The PyPI release predates the source tree behind this page". Recommendation: do not file as a defect.
- **Title (if filed):** `Publish a release: aspose-slides-foss 26.8.0 on PyPI lacks Hyperlink and other features used in the README`
- **Reproduce** (from a directory outside the checkout): `pip install aspose-slides-foss==26.8.0`; `python -I -c "from aspose.slides_foss import Hyperlink"`. **Actual:** `ImportError: cannot import name 'Hyperlink' from 'aspose.slides_foss'`; the same import against the source tree succeeds; `pyproject.toml` still says `version = "26.8.0"`. **Fix:** cut and publish a release.

### U48. Cells-TypeScript: package.json lacks basic metadata and the README API table has placeholder descriptions
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript`, revision `fc186507e5b7124f4664aa6035f25cfd3112367d`, severity low, class PLACEHOLDER_METADATA, log `start-Cells-TS`. (`npm start` itself works and creates `outputfiles/`; the earlier "missing output directory" claim was **not reproduced** and is dropped.)
- **Title:** `package.json has no license, description, repository or engines field; README API table has 24 placeholder descriptions`
- **Reproduce:** `grep -n '"license"\|"description"\|"repository"\|"engines"' package.json`; `grep -c 'Class in the Cells TYPESCRIPT API' README.md`. **Actual:** no match in `package.json` (the package is named `excel-cells`, version `1.0.0`, `main` is `index.ts`); the README has 24 rows reading "Class in the Cells TYPESCRIPT API." (for example `AllConnectorShapeInfo`, `AllShapeInfo`, `ArrowShapeType`, lines 198-200). **Fix:** fill in the metadata and write real descriptions or drop the rows.

### U49. Font-Python: pyproject version 1.0.0 does not match the release tags
- Repository `aspose-font-foss/Aspose.Font-FOSS-for-Python`, revision `adf4885a3a5d4ddb7e30e737e83e72a44ee8dec6`, severity low, class VERSION_MISMATCH, log `tags-Font-Python`. (The `pip install "aspose-font[mcp]"` 404 is the existing BC-02 handoff.)
- **Title:** `pyproject.toml version is 1.0.0 but the repository is tagged 26.x`
- **Reproduce:** `grep -n -m2 '^version' pyproject.toml`; `git ls-remote --tags origin | sed 's#.*refs/tags/##' | grep -v '\^' | tail -5`. **Actual:** `version = "1.0.0"`; the newest tags are `26.9.1`..`26.9.4`. **Fix:** align the package version with the release tags.

### U50. Cells-.NET: agents.md names a release-notes file that does not exist, with an outdated version
- Repository `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET`, revision `941814fd138dc28cf47123d48194f329f283498d`, severity low, class DOC_BROKEN_REFERENCE, log `cells-net-agents`.
- **Title:** `agents.md references the missing RELEASE_NOTES_V26.5.0.md; the project is at 26.9.0`
- **Reproduce:** `grep -n 'RELEASE_NOTES' agents.md`; `git ls-files | grep -i release_notes`; `grep -rn -m1 '<Version' --include=*.csproj .`. **Actual:** `agents.md:18` and `:119` name `RELEASE_NOTES_V26.5.0.md`; no such file is tracked; `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj:12` is `<Version>26.9.0.0</Version>`. **Fix:** add the file or update the references.

---

## GIS .NET build failure

### U51. The library does not compile: 369 build errors, 41 referenced types are not in the repository; no README, LICENSE or package metadata
- Repository `aspose-gis-foss/Aspose.GIS.FOSS-for-.Net`, revision `b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4` (default branch `main`), severity high (nothing can be built or used), class BUILD_FAILS (+ README_MISSING, LICENSE_MISSING_ROOT), logs `build-GIS-NET`, `sample-errors-GIS-NET`, `missing-types-GIS-NET`, `license-GIS`. Reproduced 2026-10-10T15:39Z with .NET SDK 10.0.401.
- **Title:** `Aspose.GIS.FOSS-for-.Net: the library does not compile, 369 build errors, 41 referenced types missing`
- **Reproduce:** `git clone https://github.com/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net.git`, then `dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release`.
- **Expected:** the build exits 0, and the repository has a README and a LICENSE.
- **Actual:** `Build FAILED.`, `369 Error(s)`, `45 Warning(s)`: CS0246 (type or namespace not found), CS0115, CS0534, CS0234, CS0535, CS0508, CS8937. Of 57 distinct unresolved type names, 41 are declared nowhere in the tracked sources: Axis, BursaWolfParameters, Dataset, Driver, Ellipsoid, Extent, GeoJsonLayer, GeoJsonOptions, GeocentricAxisesOrder, GeographicAxisesOrder, GeographicCrsEntry, GeographicDatum, GeographicDatumEntry, IAttributeIndex, IFeatureStyle, ILinearRing, ISpatialIndex, JoinByGeometryOptions, JoinOptions, LayerEvaluationRestrictions, LayerIndices, LocalDatum, MapInfoCoordinateValidationError, MapInfoCoordinateValidationException, NumericFormat, ParameterType, PointsSequence, Polygon, ProjectedAxisesOrder, Projection, ProjectionMethodIdentifier, Projections, Renderer, SavingOptions, ToWgs84Entry, TransformationError, VectorSymbolizer, VerticalDatum, WkbVariant, WktVariant, WrapAttributesConverter. The namespaces `Aspose.GIS.FOSS.Rendering.Symbolizers` and `Aspose.GIS.FOSS.Epsg` do not exist. Examples: `Aspose.GIS.FOSS\Geometries\IGeometry.cs(5,33): error CS0234: The type or namespace name 'Symbolizers' does not exist in the namespace 'Aspose.GIS.FOSS.Rendering'`; `Aspose.GIS.FOSS\SpatialReferencing\Internal\OgcEsriSrsTransformer.cs(6,23): error CS0234: The type or namespace name 'Epsg' does not exist in the namespace 'Aspose.GIS.FOSS'`; `Aspose.GIS.FOSS\Geometries\IPolygon.cs(38,7): error CS0246: The type or namespace name 'Polygon' could not be found`; `Aspose.GIS.FOSS\FileDriver.cs(346,16): error CS0246: The type or namespace name 'Dataset' could not be found`; `Aspose.GIS.FOSS\GeoJsonDriver.cs(18,30): error CS0115: 'GeoJsonDriver.SupportsSpatialReferenceSystem(SpatialReferenceSystem)': no suitable method found to override`. The head commit is titled "Second part", which suggests a partial import. `git ls-files` lists 114 files and none is named `README*` or `LICENSE*`; `gh api repos/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net --jq .license` returns `null`; `Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj` has no `PackageId`, `Version`, `Description`, `PackageLicenseExpression` or `RepositoryUrl`.
- **Fix:** add the missing source files (or remove the references) so that `dotnet build` exits 0, then add a README, an OSI-approved LICENSE and package metadata. A CI job that builds on every push would catch this class of problem.
