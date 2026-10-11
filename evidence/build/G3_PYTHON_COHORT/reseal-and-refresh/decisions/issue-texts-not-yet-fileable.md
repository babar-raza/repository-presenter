authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Verified issue texts the handoff model cannot carry (lane iss3b, 2026-10-11)

Each text below was re-run by command at the live head on 2026-10-11 (the logs are `analysis/raw-logs/iss3b-*.txt`), written in the shape of a handoff (title `Product: defect`, one defect, steps with the exact commands, expected, actual, location, suggested fix) and held to `components/issues/quality.py::issue_quality_findings` (all pass). They are not handoffs: `defect_class` has no entry for a packaging fault, a runtime error, a documentation contradiction or a library side effect, so `file-upstream-defects` cannot file them and `issue-readiness` does not list them. Until a class and redetector exist (a schema change through a named work item) the owner can post them by hand; nothing here was posted. The decisions are in `decisions/issue-approval-table-final.md`, section 4.

## U06: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (FILE wave 2)

Revision `66cb26df3b031f0bf6976d4e88dc89721983afa4`.

**Title:** Aspose.3D FOSS for TypeScript: package.json main and types point at dist/index.js, which the build does not produce

**Body:**

~~~markdown
## Summary

`package.json` declares `"main": "dist/index.js"` and `"types": "dist/index.d.ts"`, but `npm run build` (`tsc`) writes only `dist/aspose/...`. Requiring the package by its own entry point therefore fails.

## Environment

- Repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
- Revision: `66cb26df3b031f0bf6976d4e88dc89721983afa4` (the upstream revision this report was verified against, default branch `master`)
- Docker image `node:22` (Node v22.23.3, npm 10.9.9), TypeScript 5.9.3
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
cd Aspose.3D-FOSS-for-TypeScript
npm install
npm run build
ls dist
node -e "require('.')"
```

## Expected

`require('.')` loads the package: `main` and `types` name files that the build produces.

## Actual

`npm run build` exits 0 and `ls dist` prints `aspose`. Then:

```
Error: Cannot find module '/w/dist/index.js'. Please verify that the package.json has a valid "main" entry
```

## Where in the repository

- `package.json` lines 5 and 6 (`main`, `types`)
- `src/` has no `index.ts` that would produce `dist/index.js`

## Suggested fix

Add `src/index.ts` that re-exports `./aspose/threed` (so `dist/index.js` and `dist/index.d.ts` exist), or point `main` and `types` at `dist/aspose/threed/index.js` and `dist/aspose/threed/index.d.ts`.
~~~

## U06b: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (FILE wave 2)

Revision `66cb26df3b031f0bf6976d4e88dc89721983afa4`.

**Title:** Aspose.3D FOSS for TypeScript: adm-zip is required at run time for 3MF but is only listed in devDependencies

**Body:**

~~~markdown
## Summary

The 3MF importer and exporter load `adm-zip` with `require('adm-zip')` at run time, but `package.json` lists it only under `devDependencies`. An application that installs the package without development dependencies cannot read or write 3MF files.

## Environment

- Repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
- Revision: `66cb26df3b031f0bf6976d4e88dc89721983afa4` (the upstream revision this report was verified against, default branch `master`)
- Docker image `node:22` (Node v22.23.3, npm 10.9.9)
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
cd Aspose.3D-FOSS-for-TypeScript
grep -n "adm-zip" package.json
grep -n -F "require('adm-zip')" src/aspose/threed/formats/threemf/ThreeMfExporter.ts src/aspose/threed/formats/threemf/ThreeMfImporter.ts
```

## Expected

Every module that is required at run time is listed under `dependencies`.

## Actual

```
26:    "@types/adm-zip": "^0.5.7",
31:    "adm-zip": "^0.5.16",
```
Both lines sit inside `devDependencies`; the `dependencies` object lists only `xmldom`. The sources:

```
src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162:        const zip = new (require('adm-zip'))();
src/aspose/threed/formats/threemf/ThreeMfImporter.ts:53:            const AdmZip = require('adm-zip');
```

## Where in the repository

- `package.json:31` (`adm-zip` under `devDependencies`)
- `src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162`, `ThreeMfImporter.ts:53`

## Suggested fix

Move `adm-zip` to `dependencies` (keep `@types/adm-zip` in `devDependencies`).
~~~

## U14: aspose-cells-foss/Aspose.Cells-FOSS-for-Python (FILE wave 2)

Revision `952317cad8db1880ed85be9814c24e9303930d49`.

**Title:** Aspose.Cells FOSS for Python: save_as_csv uses the locale encoding by default and raises UnicodeEncodeError for CJK text

**Body:**

~~~markdown
## Summary

`CSVHandler` takes its default encoding from `locale.getpreferredencoding(False)` (`csv_handler.py:29-31`). On a machine whose locale encoding is not UTF-8, saving a workbook that holds non-Latin-1 text raises `UnicodeEncodeError`; with UTF-8 mode the same call succeeds. A file also reads differently on two machines.

## Environment

- Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Python
- Revision: `952317cad8db1880ed85be9814c24e9303930d49` (the upstream revision this report was verified against, default branch `main`)
- Windows 11, Python 3.13.15 with a cp1252 locale (`PYTHONUTF8=0`), `pip install -e .`
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python
cd Aspose.Cells-FOSS-for-Python
pip install -e .
PYTHONUTF8=0 python -c "from aspose.cells_foss import Workbook; wb = Workbook(); ws = wb.get_active_worksheet(); ws.cells['A1'].value = '你好'; wb.save_as_csv('o.csv')"
```

## Expected

`save_as_csv` writes the file with a deterministic default encoding (UTF-8), whatever the locale.

## Actual

```
  File "aspose/cells_foss/workbook.py", line 566, in save_as_csv
  File "aspose/cells_foss/csv_handler.py", line 191, in save_csv
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-1: character maps to <undefined>
```
With `PYTHONUTF8=1` the same command succeeds and `o.csv` contains `你好`.

## Where in the repository

- `aspose/cells_foss/csv_handler.py:29-31` (`_system_encoding`) and `:191` (`writer.writerow`)
- `aspose/cells_foss/workbook.py:566`

## Suggested fix

Default `CSVSaveOptions.encoding` and `CSVLoadOptions.encoding` to `utf-8` (honouring `write_bom` where it is set) and document the option.
~~~

## U16: aspose-cells-foss/Aspose.Cells-FOSS-for-Python (FILE wave 2)

Revision `952317cad8db1880ed85be9814c24e9303930d49`.

**Title:** Aspose.Cells FOSS for Python: the wheel installs a top-level examples package next to aspose

**Body:**

~~~markdown
## Summary

`pyproject.toml` lists `examples` among the setuptools `packages` (and its package data). The built wheel therefore puts a top-level `examples` package, with test modules, into `site-packages`, where a name this generic can collide with any other project or with the user's own package.

## Environment

- Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Python
- Revision: `952317cad8db1880ed85be9814c24e9303930d49` (the upstream revision this report was verified against, default branch `main`)
- Windows 11, Python 3.13.15, pip 26.2.1, `pip wheel . --no-deps`
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python
cd Aspose.Cells-FOSS-for-Python
sed -n 45,50p pyproject.toml
pip wheel . --no-deps -w whl
python -c "import zipfile,glob,collections; z=zipfile.ZipFile(glob.glob('whl/*.whl')[0]); print(dict(collections.Counter(n.split('/')[0] for n in z.namelist())))"
```

## Expected

The wheel contains the `aspose` package and its metadata only.

## Actual

```
[tool.setuptools]
packages = ["aspose", "aspose.cells_foss", "examples"]
[tool.setuptools.package-data]
"aspose.cells_foss" = ["*.py", "*.geojson"]
examples = ["*.py"]
```
```
{'aspose': 73, 'examples': 33, 'aspose_cells_foss-26.10.0.dist-info': 5}
```

## Where in the repository

- `pyproject.toml` lines 45 to 50 (`[tool.setuptools]` and its `package-data`)

## Suggested fix

Remove `examples` from `packages` and from `package-data`; keep the examples in the source distribution only if they are wanted there.
~~~

## U19: aspose-cells-foss/Aspose.Cells-FOSS-for-Rust (FILE wave 2)

Revision `1a6004af47b1ef15385f9d36d381a8172428cc7e`.

**Title:** Aspose.Cells FOSS for Rust: cargo test --all-targets runs 0 tests because the crate has no tests

**Body:**

~~~markdown
## Summary

The crate ships no automated tests: `tests/` has no tracked file and no source file contains a `#[test]` or `#[cfg(test)]` item. CI runs `cargo test --all-targets` and reports success, so a regression in workbook reading or writing would not be caught.

## Environment

- Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Rust
- Revision: `1a6004af47b1ef15385f9d36d381a8172428cc7e` (the upstream revision this report was verified against, default branch `master`)
- Docker image `rust:1` (cargo 1.99.0)
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust
cd Aspose.Cells-FOSS-for-Rust
git ls-files tests | wc -l
git grep -n -E '#\[(test|cfg\(test\))' -- '*.rs' | wc -l
cargo test --all-targets
```

## Expected

`cargo test` runs tests that exercise reading and writing a workbook.

## Actual

The first two commands print `0`. `cargo test --all-targets` exits 0 and, for each of its 15 targets, prints `running 0 tests` and `test result: ok. 0 passed; 0 failed`.

## Where in the repository

- `.github/workflows/ci.yml:56-57` (`cargo test --all-targets`) and `:71-72` (`cargo bench`)
- `tests/` (absent)

## Suggested fix

Add round-trip integration tests under `tests/` (the sample binaries already create, save, reload and print workbooks) and drop the `cargo bench` step or add benchmark targets.
~~~

## U31: aspose-3d-foss/Aspose.3D-FOSS-for-Java (FILE wave 2)

Revision `3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3`.

**Title:** Aspose.3D FOSS for Java: no workflow runs the tests, every Maven build step passes -DskipTests

**Body:**

~~~markdown
## Summary

The only workflow, `.github/workflows/maven-central-release.yml`, builds with `-DskipTests` in each of its build steps. No workflow runs the test suite on a push or a pull request, so a failing test is never noticed before a release.

## Environment

- Repository: aspose-3d-foss/Aspose.3D-FOSS-for-Java
- Revision: `3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3` (the upstream revision this report was verified against, default branch `main`)
- Repository files only (no JDK needed)
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java
cd Aspose.3D-FOSS-for-Java
ls .github/workflows
grep -n 'verify\|deploy' .github/workflows/*.yml | grep mvn
```

## Expected

A workflow runs `mvn -B verify` (with tests) on push and pull request.

## Actual

`ls` prints `maven-central-release.yml`. The Maven build steps are:

```
64:        run: mvn -B clean verify -Dgpg.skip=true -DskipTests
150:        run: mvn -B clean verify '-Dgpg.skip=true' '-DskipTests'
240:        run: mvn -B clean verify -DskipTests
268:        run: mvn -B deploy -DskipTests
```

## Where in the repository

- `.github/workflows/maven-central-release.yml` lines 64, 150, 240 and 268

## Suggested fix

Add a workflow that runs `mvn -B verify` on push and pull request, and keep `-DskipTests` only where the release job has already run them.
~~~

## U38: aspose-page-foss/Aspose.Page-FOSS-for-Python (FILE wave 2)

Revision `43cef367cd0b2cf00cc03064ca9d29d1ff507967`.

**Title:** Aspose.Page FOSS for Python: aspose.page.mcp.server.run() raises TypeError, host and port reach the stdio transport

**Body:**

~~~markdown
## Summary

`aspose.page.mcp.server.run()` calls `server.run(host=host, port=port)` without naming a transport. With FastMCP 4.1.0 the default transport is stdio, which does not accept `host`, so the call raises `TypeError`. `fastmcp` is also not declared as a dependency in `pyproject.toml`.

## Environment

- Repository: aspose-page-foss/Aspose.Page-FOSS-for-Python
- Revision: `43cef367cd0b2cf00cc03064ca9d29d1ff507967` (the upstream revision this report was verified against, default branch `main`)
- Windows 11, Python 3.13.15, fastmcp 4.1.0, skia-python 144.0.post2, `PYTHONUTF8=1`, run with `PYTHONPATH=src`
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-page-foss/Aspose.Page-FOSS-for-Python
cd Aspose.Page-FOSS-for-Python
pip install fastmcp skia-python
sed -n 28,37p src/aspose/page/mcp/server.py
PYTHONPATH=src python -c "from aspose.page.mcp import server; server.run()"
```

## Expected

`run()` starts the server on `127.0.0.1:8000`, as its signature (`host`, `port`) suggests.

## Actual

```
TypeError: TransportMixin.run_stdio_async() got an unexpected keyword argument 'host'
```

## Where in the repository

- `src/aspose/page/mcp/server.py` lines 29 to 37 (`run`)
- `pyproject.toml` line 11 (`dependencies = ["skia-python"]`)

## Suggested fix

Pass the HTTP transport explicitly (`server.run(transport="http", host=host, port=port)`), declare `fastmcp` as an optional dependency and add a test that starts the server.
~~~

## U43: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (FILE wave 2)

Revision `736cedaa2922e4952f429364bdb9a4bbb1d97863`.

**Title:** Aspose.PDF FOSS for Java: limitations.md lists XLSX and Markdown conversion as unsupported, conversion.md says it works

**Body:**

~~~markdown
## Summary

`docs/limitations.md` lists conversion to XLSX and Markdown among the unsupported features. `docs/conversion.md`, `SaveFormat.java` and `CHANGELOG.md` say the opposite: the library converts PDF to XLSX and to Markdown.

## Environment

- Repository: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java
- Revision: `736cedaa2922e4952f429364bdb9a4bbb1d97863` (the upstream revision this report was verified against, default branch `main`)
- Repository files only
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java
cd Aspose.PDF-FOSS-for-Java
sed -n 16p docs/limitations.md
sed -n 3p docs/conversion.md
grep -n -E '^    (Xlsx|Excel|Markdown)' src/main/java/org/aspose/pdf/SaveFormat.java
grep -n -E 'SaveFormat.Xlsx|SaveFormat.Markdown' CHANGELOG.md
```

## Expected

The documents agree: limitations.md lists only formats that are really unsupported.

## Actual

```
docs/limitations.md:16: - **Conversion to spreadsheet/presentation/e-book formats** — XLSX, PPTX, EPUB, MOBI, Markdown, LaTeX, ZUGFeRD, and similar. (HTML, DOCX and DOC conversion *are* supported — see [conversion.md](conversion.md).)
docs/conversion.md:3: Convert between PDF and other document formats: **PDF ↔ HTML**, **PDF ↔ DOCX**, **PDF ↔ XLSX**, and **PDF ↔ Markdown**.
SaveFormat.java:26:    Xlsx,
SaveFormat.java:32:    Excel,
SaveFormat.java:39:    Markdown
CHANGELOG.md:121: - New save format `SaveFormat.Xlsx` (alias `SaveFormat.Excel`)
CHANGELOG.md:146: - New save format `SaveFormat.Markdown`
```

## Where in the repository

- `docs/limitations.md:16`
- `docs/conversion.md:3`
- `src/main/java/org/aspose/pdf/SaveFormat.java:26-39`
- `CHANGELOG.md:121` and `:146`

## Suggested fix

Remove XLSX and Markdown from the unsupported list in `docs/limitations.md`.
~~~

## U44: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python (FILE wave 2)

Revision `8f0edbe6930f300088fc72f64711be3265a723d1`.

**Title:** Aspose.PDF FOSS for Python: the library adds an INFO StreamHandler on stdout when it is imported

**Body:**

~~~markdown
## Summary

`src/aspose_pdf/engine/logging.py` sets the `aspose_pdf` logger to INFO and attaches a `StreamHandler(sys.stdout)` as soon as the package is imported. Closing a `Document` then writes a log line to standard output, which corrupts any program that writes data to stdout.

## Environment

- Repository: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python
- Revision: `8f0edbe6930f300088fc72f64711be3265a723d1` (the upstream revision this report was verified against, default branch `main`)
- Windows 11, Python 3.13.15, `pip install -e .`
- Verified on 2026-10-11 from a fresh shallow clone.

## Steps to reproduce

```
git clone https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Python
cd Aspose-PDF-FOSS-for-Python
pip install -e .
sed -n 8,13p src/aspose_pdf/engine/logging.py
python -c "from aspose_pdf import Document
with Document('tests/fixtures_4pages.pdf') as d: pass" 2>/dev/null
```

## Expected

A library leaves logging configuration to the application (it adds only a `NullHandler`), see the Python logging how-to for libraries.

## Actual

```
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
```
Standard output receives `2026-10-11 23:02:36,571 [INFO] aspose_pdf: Document resources released.` and standard error is empty.

## Where in the repository

- `src/aspose_pdf/engine/logging.py` lines 8 to 13

## Suggested fix

Remove the level and handler configuration and add `logging.getLogger("aspose_pdf").addHandler(logging.NullHandler())` instead.
~~~
