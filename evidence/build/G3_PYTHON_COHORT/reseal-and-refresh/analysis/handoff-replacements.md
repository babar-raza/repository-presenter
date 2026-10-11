authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Replacement text for weak existing handoffs (TC-ISS-01, G6-W01)

Status after the issue-text quality gate (TC-ISS-04) work in the same PR: R1 (TeX) was applied in
place -- same fingerprint, new title/body/claim/evidence, `reverification.json` entry re-measured
and its digest recomputed by `approval.evidence_digest`; no approval existed, so none is
invalidated. R2 (3D-TS BC-02) and R3 (PDF-TS) are not applied: both entries stay `NOT_A_DEFECT`
as instructed, and R2's real defect is a packaging issue the handoff model cannot represent (U06).
The text below is kept as the record of what was wrong with the old bodies. All numbers were
measured on 2026-10-10 at the revision shown; raw output is under `raw-logs/`.

---

## R1. TeX-Python: supersedes `aspose-tex-foss__Aspose.TeX-FOSS-for-Python__c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188`

What is wrong with the existing body: it says "35 of 45 files under src/aspose_tex/", which is the
smallest true subset. At the same revision the figure is 102 of 119 `.py` files, the package root
cannot be imported, and the test suite cannot be collected.

Re-verification at the live head `181015d2eee3e19f8af3d84e4a932ac84ad47c7c` (unchanged since the
handoff): `python -I scripts/ast_parse_all.py .` -> `FAILED/TOTAL: 102/119` (log
`raw-logs/ast-TeX-Python.txt`); `import aspose_tex` fails at `_input/catcode.py:66`
(`raw-logs/import-TeX-Python.txt`).

Triggering check: `NOT_PROCESSABLE` (version `1`), same as the existing handoff.

**Title:** `102 of 119 .py files fail to parse (IndentationError): src/aspose_tex/ is 35 of 45, tests are 66 of 73; "import aspose_tex" fails`

**Body:**

````markdown
## Summary

Most of this repository's Python source does not parse. Indentation has been collapsed to one space
per nesting level, so the files are not valid Python. The package cannot be imported from this
source tree and the test suite cannot be collected.

## Environment

- Revision `181015d2eee3e19f8af3d84e4a932ac84ad47c7c` (default branch `main`)
- Python 3.13.15, standard library only (`ast.parse`); any Python 3 interpreter reproduces it

## Steps to reproduce

```python
import ast, pathlib
bad = ok = 0
for p in pathlib.Path(".").rglob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8")); ok += 1
    except SyntaxError:
        bad += 1
print(bad, ok)
```

and

```sh
pip install -e .
python -c "import aspose_tex"
```

## Actual result

- 102 of the 119 `.py` files raise `IndentationError`: `src/aspose_tex/` 35 of 45, `tests/` 66 of 73
  (including `tests/_verification/`), and `run_hello.py`.
- `src/aspose_tex/presentation/__init__.py` (the module the package's own docstring calls the
  user-facing entry point; it defines `TeXJob`, `TeXOptions` and the `OutputDevice` hierarchy):
  `IndentationError: expected an indented block after function definition on line 107 (line 108)`.
  Lines 107 and 108 are indented by a single space.
- `import aspose_tex` fails immediately: `aspose_tex/__init__.py` imports `aspose_tex._input`, which
  imports `_input/catcode.py`, line 66:
  `IndentationError: expected an indented block after 'for' statement on line 65`.
- The same error shape (`expected an indented block after ...`) recurs in every failing file.

## Suggested fix

Restore the original indentation (re-export from the original formatted source), then add a CI step
that runs `python -m compileall src tests` on every push so a collapsed-indentation commit cannot
land again.
````

---

## R2. 3D-TypeScript BC-02: supersedes `aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript__a6f52c1a0cd2425fdc67e15964b43da031e2817dd111dd6ea706defcc9034d8d`

What is wrong with the existing body: its title and text are pipeline jargon
(`install_command:npm is CONTRADICTED`), and `reverification.json` already records it as
`NOT_A_DEFECT` (the package is unpublished and the README documents a source install, so nothing is
contradicted). The reportable defects at that revision are different and concrete: the declared
entry point does not exist, and a runtime dependency is declared as a dev dependency.

Re-verification at the live head `66cb26df3b031f0bf6976d4e88dc89721983afa4` (unchanged):
`raw-logs/node-3D-TS.txt` (build, `require('.')`, lint, jest in Docker `node:22`) and
`raw-logs/npm-registry-3D-TS.txt` (registry 404 for `@aspose/3d`, `@aspose/3d-foss`, `aspose-3d-foss`).

Disposition of the superseded handoff: record `NOT_A_DEFECT` (already recorded); do not file it.
Three smaller defects found in the same pass are in `issue-drafts-unrepresentable.md`
(U05 LICENSE, U06 this packaging issue, U07 lint, U08 failing tests); R2 below is the U06 text and
becomes the replacement for the `triggering_check` BC-02 slot once the schema can carry a
`defect_class` (TC-ISS-03) because it is a packaging defect, not an install-command claim.

**Title:** `package.json "main"/"types" point at dist/index.js, which the build never produces; adm-zip is required at runtime but listed only in devDependencies`

**Body:**

````markdown
## Summary

Two packaging problems keep this package from being used as an npm dependency:

1. `"main": "dist/index.js"` and `"types": "dist/index.d.ts"` name files that `npm run build` does
   not produce. The build output root is `dist/aspose/threed/index.js`.
2. `adm-zip` is `require()`d by the 3MF importer and exporter at runtime but is declared only under
   `devDependencies`.

## Steps to reproduce (Node 22.23.3, TypeScript 5.9.3)

```sh
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript.git
cd Aspose.3D-FOSS-for-TypeScript
npm install
npm run build          # exits 0
ls dist                # only: aspose
node -e "require('.')"
```

## Actual result

```
Error: Cannot find module '.../dist/index.js'. Please verify that the package.json has a valid "main" entry
```

`src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162` (`new (require('adm-zip'))()`) and
`ThreeMfImporter.ts:53` (`const AdmZip = require('adm-zip')`) need `adm-zip` when a 3MF is read or
written, but `package.json` lists it only under `devDependencies`, so a consumer who installs the
package gets a `Cannot find module 'adm-zip'` error on the first 3MF call.

`package.json` also has no `repository`, `homepage`, `bugs` or `files` fields.

## Suggested fix

- Add `src/index.ts` re-exporting `./aspose/threed`, or point `main`/`types` at
  `dist/aspose/threed/index.js` and `dist/aspose/threed/index.d.ts`.
- Move `adm-zip` to `dependencies`.
- Add `repository`, `homepage`, `bugs` and `files`.
````

---

## R3. PDF-TypeScript BC-02: withdraw `aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript__ef667e7d94656f902b0f73fa8f9338d5bfc886e11d2a9cb00ff6f6f6e41cb1f2`; no replacement

The body is pipeline jargon (`install_command:npm is CONTRADICTED`) and the finding is not a defect:
`raw-logs/npm-registry-PDF-TS.txt` (live head `c672b3918318ccd0c13bc9dc619620cac2674c9e`) shows `@asposefoss/pdf`, `@aspose/pdf` and `aspose-pdf-foss`
all return HTTP 404, and the README documents only a source install (`npm install` at
`README.md:277`). `reverification.json` already records `NOT_A_DEFECT` at the moved head. Nothing to
file; if the owner wants a publication reminder it is a product decision, not a defect report.
