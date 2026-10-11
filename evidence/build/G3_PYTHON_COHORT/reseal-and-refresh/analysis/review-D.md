authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Review D: six registry entries with no sealed candidate

Date of review: 2026-10-10. Read-only. Nothing was written to GitHub or to any Aspose repository. Only `gh api` GET calls, `git clone --depth 1` into `scratchpad/clones/D/`, and registry GETs (npm / PyPI / NuGet) were used. The `present`, `propose` and `file-upstream-defects` commands were not run. A portable Node 22.23.3 zip was downloaded to `scratchpad/nodedl/` (SHA-256 checked against nodejs.org SHASUMS256.txt) so the TypeScript repositories could be built and tested. Machine: Windows 11, .NET SDK 10.0.401, Python 3.13, so a few failures below may be platform-specific (flagged where relevant).

Limits of this review: I could not run the pipeline (no `present`), so every statement about what the pipeline will do is from code reading. Those statements are marked "by code reading".

## Summary table

| Repository | Classification | One-line reason | Issue drafts |
|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | PROCESSABLE | Builds (tsc 5.9.3, exit 0). The only recorded blockers were our own: a since-fixed authoring citation gap and reviewer paraphrase check, the gateway, and a missing BC-11 no-op proof. Not redrawn since 2026-09-30. | 3 |
| aspose-gis-foss/Aspose.GIS.FOSS-for-.Net | UPSTREAM_DEFECT_BLOCKED | `dotnet build` fails with 369 errors (41 types referenced but never declared). No README, no LICENSE. The earlier "gateway outage" record masked this. | 3 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | PROCESSABLE | Builds, typechecks, 22,715 of 22,723 tests pass, LICENSE present and matching. Blockers are ours: a 494 KB README, S4 and BC-07 budget fixes never live-proven, and a head that moves daily. | 0 |
| aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | PROCESSABLE | Builds, 77/77 tests pass, 8.5 KB README, license declared in the csproj and README. Never drawn since being enabled. Only hygiene defects upstream. | 1 (+ update note for open issue #5) |
| aspose-psd-foss/Aspose.PSD-FOSS-for-Python | UPSTREAM_DEFECT_BLOCKED (by code reading; soft) | The placeholder is gone (66 modules, 75 tests pass) but there is no manifest, no LICENSE and a 69-byte README. The Required License section has no license fact, and there is no install path. | 2 (+ update note for open issue #4) |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | UPSTREAM_DEFECT_BLOCKED | 35 of 45 files under `src/aspose_tex/` fail `ast.parse`, and `import aspose_tex` itself fails. Confirmed unchanged at `181015d2`. | 1 (existing handoff, extended) |

The existing handoffs under `evidence/upstream-defects/` for 3D-TS, PDF-TS and TeX are all `HANDOFF_PENDING` with `issue_ref: null`. None has been filed. See each section for whether it is still accurate.

---

## 1. aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript

### Why there is no sealed candidate
- `data/registry.json`: `mode: dry_run`, `active: true`, policy profile `aspose-3d-foss-typescript`.
- `candidates/` has no directory for it. `project/state.yaml` and `docs/DECISION_LOG.md` carry the history:
  - 2026-09-24: BC-02 `install_command:npm` CONTRADICTED. `@aspose/3d` is unpublished, and a global tsc 7.0.2 rejected the repo's `moduleResolution: node`.
  - 2026-09-25: registry-first tsc fix and the source-build rescue. BC-02 now passes, but `section_authoring` rejected "Node.js" as an identifier that is not an accepted fact value.
  - 2026-09-26: "Node.js" admitted as a curated proper noun. The next draws hit the gateway outage.
  - 2026-09-30: the F04 paraphrase false-negative in the reviewer was fixed (reviewer logic 14). One fresh draw reached ACCEPT (READY_FOR_PROPOSAL). That bundle was left uncommitted in a worktree, with no BC-11 fresh-process no-op proof. The bundle is not readable now (permission denied in the agent worktree).
  - `project/state.yaml` (2026-09-30 entry) still lists it among the "real content-authoring defects" group, which is stale after the fixes above.
  - Since then main gained #202 (BC-06 scheme position), #226 (npm source-install fallback) and many S6 and reviewer changes. I found no live 3D-TS draw after 2026-09-30.
- There is no `runs/transactions/` entry on the main checkout, and no `evidence/build/**/manifest.json` entry for it.

### Independent verification (head `66cb26df` = same revision as the handoff; default branch `master`, last push 2026-09-18)
- Inventory: 190 tracked files: `src/` 151, `tests/` 33, `README.md` 27,787 bytes, `AGENTS.md`, `package.json`, `tsconfig.json`, `jest.config.js`. No `docs/` folder and no `examples/` folder.
- **No LICENSE file.** `package.json` says `"license": "MIT"` and the README says MIT, but `git ls-files | grep -i licen` is empty, and the GitHub API reports `license: null`. The siblings (3D-Python, 3D-Java, 3D-.NET) each ship a 1,068-byte MIT `LICENSE`. The pipeline can still declare the license from the manifest (`evidence/facts/license.py`, `declared` path), so this does not block sealing.
- Build: `npm install` (383 packages) then `npm run build` (`tsc`, TypeScript 5.9.3 resolved from `^5.8.3`) exits 0. `npx tsc --noEmit` exits 0.
- **Entry point is broken.** `package.json` has `"main": "dist/index.js"`, but the build emits `dist/aspose/threed/index.js` and there is no `src/index.ts`. `node -e "require('.')"` fails: `Error: Cannot find module '...\dist\index.js'. Please verify that the package.json has a valid "main" entry`. The README admits this and imports from `./dist/aspose/threed`.
- **Undeclared runtime dependency.** `src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162` and `ThreeMfImporter.ts:53` call `require('adm-zip')`, but `adm-zip` is only in `devDependencies`. The README acknowledges this.
- Tests: `npx jest` gives 4 failed, 93 passed (97 total):
  - `Test3MFRoundTrip › testRoundTripExportImport`: `TypeError: rotation[0].eulerAngles is not a function` at `src/aspose/threed/Transform.ts:160`.
  - `TestGltfExporter › testSimpleTriangleBinary`: `RangeError: The value of "offset" is out of range. It must be >= 0 and <= 636. Received 640` at the `writeFloatLE` loop.
  - `TestSceneSaveSTL › testRoundtripFile`: expected 1, received 0.
  - `Test3MFMaterialImport › testMaterialImport`: ENOENT for `foss.3d.python/examples/3mf/dodeca_chain_loop_color.3mf`, a path outside the repository.
- Lint: `npm run lint` fails with "ESLint couldn't find a configuration file" (no `.eslintrc` is tracked). The README lists `npm run lint` as a development step.
- npm registry today: `https://registry.npmjs.org/%40aspose%2F3d` returns 404 (also `@aspose/3d-foss`, `aspose-3d-foss`). Unscoped `aspose.3d` returns 200, which is a different package.
- Upstream issues and PRs: only three closed PRs by babar-raza (README refreshes). No open issue.

### Classification: PROCESSABLE
The seal is blocked only by our own pipeline state. Upstream defects (missing LICENSE, broken `main`, test and lint failures) are real but none blocks sealing. The package builds, the README already discloses the entry-point and `adm-zip` gaps, and the pipeline has a source-build rescue for the unpublished npm name.
- Pipeline-side items (all recorded, none re-proven):
  1. A fresh `present --fresh` on current main has not been run since the 2026-09-30 fixes.
  2. The BC-11 fresh-process no-op proof was never produced.
  3. The F10 "enterprise relationship overclaim" is a sampling-dependent reviewer finding (decision log 2026-09-30).
  4. Gateway availability (BLOCKED_EXTERNAL history).

### Existing handoff
`evidence/upstream-defects/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript/a6f52c1a...json`: BC-02, npm 404 for `@aspose/3d`, revision `66cb26df`, status `HANDOFF_PENDING`, `issue_ref: null`.
- Evidence is still accurate today: npm returns 404, `package.json` name is `@aspose/3d`, and the revision is unchanged.
- Its `suggested_issue_body` is weak: "install_command:npm is CONTRADICTED" is pipeline jargon. An unpublished package with a documented source install is a distribution fact, not a code defect. Recommend superseding it with Draft 2 below.

### Issue drafts (text only; not filed)

**Draft 1 - title:** `Add a LICENSE file (package.json and README declare MIT, but the repository has none)`

```markdown
## Summary

`package.json` declares `"license": "MIT"` and the README's License section says the project is MIT licensed, but the repository contains no `LICENSE` file. GitHub reports no license for the repository (`gh api repos/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript --jq .license` returns `null`). Without the file, the MIT copyright notice and permission text that the license requires downstream users to retain are not shipped.

## Evidence (revision 66cb26df3b031f0bf6976d4e88dc89721983afa4)

- `git ls-files | grep -i -E "licen|copying"` returns nothing.
- `package.json`: `"license": "MIT"`.
- `README.md` "License" section: "This project is licensed under the MIT License."
- Sibling repositories ship an MIT `LICENSE` of about 1,068 bytes, for example `aspose-3d-foss/Aspose.3D-FOSS-for-Python`, `-Java` and `-.NET`.

## Suggested fix

Add the same MIT `LICENSE` file the sibling Aspose.3D FOSS repositories use at the repository root. Optionally also add `"files"` to `package.json` so the license is included in the published package.
```

**Draft 2 - title:** `package.json "main"/"types" point at dist/index.js, which the build never produces; adm-zip is required at runtime but is only a devDependency`

```markdown
## Summary

Three packaging problems mean this package cannot be consumed as an npm dependency, even after publishing:

1. `"main": "dist/index.js"` and `"types": "dist/index.d.ts"` point at files that `npm run build` does not produce.
2. `adm-zip` is `require()`d by the 3MF importer and exporter at runtime but is declared only in `devDependencies`.
3. `@aspose/3d` is not on the npm registry (HTTP 404), and `package.json` has no `repository`, `homepage`, `bugs` or `files` fields.

## Steps to reproduce (Node 22, TypeScript 5.9.3)

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript.git
cd Aspose.3D-FOSS-for-TypeScript
npm install
npm run build          # exits 0
ls dist                # only: aspose/
node -e "require('.')"
```

## Actual result

```
Error: Cannot find module '.../dist/index.js'. Please verify that the package.json has a valid "main" entry
```

The build output root is `dist/aspose/threed/index.js`; there is no `src/index.ts`.

`src/aspose/threed/formats/threemf/ThreeMfExporter.ts:162` (`new (require('adm-zip'))()`) and `ThreeMfImporter.ts:53` (`const AdmZip = require('adm-zip')`) need `adm-zip` at runtime, but `package.json` lists it only under `devDependencies`, so a consumer's 3MF code path throws on first use.

`curl -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org/%40aspose%2F3d` returns `404`.

## Suggested fix

- Add `src/index.ts` re-exporting `./aspose/threed`, or change `main`/`types` to `dist/aspose/threed/index.js` / `dist/aspose/threed/index.d.ts`.
- Move `adm-zip` to `dependencies`.
- Add `repository`, `homepage`, `bugs`, and `files` to `package.json`, and publish (or document that source install is the only path).
```

**Draft 3 - title:** `npm run lint has no ESLint config, and 4 of 97 jest tests fail at HEAD`

```markdown
## Summary

At revision 66cb26df the documented development commands do not pass.

## Evidence (Node 22.23.3, TypeScript 5.9.3 from `^5.8.3`, `npm install`, `npm run build` exits 0)

`npm run lint` reports: `ESLint couldn't find a configuration file`. No `.eslintrc*` or `eslint.config.*` is tracked, although `package.json` and the README both list `npm run lint`.

`npx jest` reports `Tests: 4 failed, 93 passed, 97 total`:

| Test | Failure |
|---|---|
| `tests/test_3mf_roundtrip.test.ts` Test3MFRoundTrip testRoundTripExportImport | `TypeError: rotation[0].eulerAngles is not a function` at `src/aspose/threed/Transform.ts:160` (via `ThreeMfImporter._createMeshNode`, `ThreeMfImporter.ts:289`) |
| `tests/test_gltf_exporter.test.ts` TestGltfExporter testSimpleTriangleBinary | `RangeError: The value of "offset" is out of range. It must be >= 0 and <= 636. Received 640` (`glbBuffer.writeFloatLE`, around line 419) |
| `tests/test_scene_save_stl.test.ts` TestSceneSaveSTL testRoundtripFile | `expect(received).toBe(expected)`: expected 1, received 0 |
| `tests/test_3mf_materials.test.ts` Test3MFMaterialImport testMaterialImport | `ENOENT: ... foss.3d.python/examples/3mf/dodeca_chain_loop_color.3mf` (the fixture lives outside this repository) |

(The `lint` script uses single quotes around the glob, which also breaks under Windows `cmd`; use double quotes or no quotes.)

## Suggested fix

Add an ESLint configuration, fix or skip the three failing tests, and vendor the 3MF fixture into `tests/`.
```

---

## 2. aspose-gis-foss/Aspose.GIS.FOSS-for-.Net

### Why there is no sealed candidate
- Registry: `dry_run`, `active: true`, `provider_identity.repository_id` 1381084812 (admitted 2026-09-25, OWNER-09).
- The decision log records only `BLOCKED_EXTERNAL` for it, citing the qwen3-next gateway outage. Entries: 2026-09-26 03:12, 04:12/04:20, 2026-09-27 04:20, 2026-10-01 09:59. Each draw passed snapshot, source, examples, facts and evaluation, then S5 returned HTTP 500.
- The head `b9b8c9c7` (2026-09-29) has not changed since the 2026-10-01 draw. The gateway masked a second, independent blocker: the library does not compile (below). No `runs/transactions/` entry exists on this checkout.

### Independent verification (head `b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4`, last push 2026-09-29)
- Inventory: 114 tracked files: `Aspose.GIS.FOSS/` (98 entries), `Aspose.GIS.FOSS.Tests/` (14 entries; one test source, `MainTests.cs`, 59 lines, 2 `[Test]`), `Aspose.GIS.FOSS.slnx`, `.gitignore`. 14 of the tracked files (both projects together) are `obj/` build output.
- **No README** of any kind. **No LICENSE** (GitHub `license: null`). `Aspose.GIS.FOSS.csproj` has no `PackageId`, `Version`, `Description`, `PackageLicenseExpression` or repository URL, so the pipeline has no declared license fact either. The `.gitignore` does not exclude `obj/` (14 build artifacts are tracked).
- **Does not compile.** `dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release` (SDK 10.0.401) returns 369 unique errors (CS0246 type-not-found, 0115, 0534, 0234, 0535, 0508, 8937). 41 distinct types are referenced but declared nowhere in the repository: Axis, BursaWolfParameters, Dataset, Driver, Ellipsoid, Extent, GeoJsonLayer, GeoJsonOptions, GeocentricAxisesOrder, GeographicAxisesOrder, GeographicCrsEntry, GeographicDatum, GeographicDatumEntry, IAttributeIndex, IFeatureStyle, ILinearRing, ISpatialIndex, JoinByGeometryOptions, JoinOptions, LayerEvaluationRestrictions, LayerIndices, LocalDatum, MapInfoCoordinateValidationError, MapInfoCoordinateValidationException, NumericFormat, ParameterType, PointsSequence, Polygon, ProjectedAxisesOrder, Projection, ProjectionMethodIdentifier, Projections, Renderer, SavingOptions, ToWgs84Entry, TransformationError, VectorSymbolizer, VerticalDatum, WkbVariant, WktVariant, WrapAttributesConverter. Also missing namespaces `Aspose.GIS.FOSS.Rendering.Symbolizers` and `Aspose.GIS.FOSS.Epsg`. Examples:
  - `Aspose.GIS.FOSS\Geometries\IGeometry.cs(5,33): error CS0234: ... 'Symbolizers' does not exist in the namespace 'Aspose.GIS.FOSS.Rendering'`
  - `Aspose.GIS.FOSS\SpatialReferencing\Internal\OgcEsriSrsTransformer.cs(6,23): error CS0234: ... 'Epsg' does not exist in the namespace 'Aspose.GIS.FOSS'`
  - `Aspose.GIS.FOSS\Geometries\IPolygon.cs(38,7): error CS0246: ... 'Polygon' could not be found`
  - `Aspose.GIS.FOSS\FileDriver.cs(346,16): error CS0246: ... 'Dataset' could not be found` (the repo has `DataSet.cs`)
  - `Aspose.GIS.FOSS\GeoJsonDriver.cs(18,30): error CS0115: no suitable method found to override`
  - `Aspose.GIS.FOSS\Geometries\Geometry.cs(12,35): error CS0535: 'Geometry' does not implement interface member 'IGeometry.AsImage(...)'`
  - The test project fails too: `MainTests.cs(36,40): CS0246 GeoPackageDataset`, `(36,58): CS0103 Dataset`, `(36,77): CS0103 Drivers`.
  - The latest commit message is "Second part", which suggests a partial import.
- NuGet: `aspose.gis.foss` returns 404 (not published); `aspose.gis` returns 200 (the commercial package).
- Upstream issues: none.

### Classification: UPSTREAM_DEFECT_BLOCKED
By code reading (`evidence/facts/extract.py::_source_build_fact`: "A build that did not exit 0 admits nothing here"; `net_examples.py` measures `dotnet build`), `install_command:dotnet` stays CONTRADICTED because the package is unpublished and the source build cannot exit 0, so BC-02 fails at S9. The Required License section would also have no license fact. This is not a defect of our pipeline, and a gateway retry will not change the result. Cross-checked: this directly contradicts the "plausibly fixable, gateway only" label in `project/state.yaml` (2026-09-30 / 2026-10-01 entries).
- Resume predicate: the solution builds with exit 0, a README exists, and a license is declared (LICENSE file or csproj `PackageLicenseExpression`).

### Existing handoff
None under `evidence/upstream-defects/`. All three drafts below are new.

### Issue drafts (text only; not filed)

**Draft 1 - title:** `The library does not compile: 369 build errors, 41 referenced types are not in the repository`

```markdown
## Summary

At the current default-branch head the solution does not build. `dotnet build` reports 369 errors. 41 types referenced across the library and test project are not declared anywhere in the repository (for example `Axis`, `Projection`, `GeographicDatum`, `Ellipsoid`, `Extent`, `Polygon`, `ILinearRing`, `Dataset`/`Driver`, `Renderer`, `VectorSymbolizer`), and two namespaces do not exist (`Aspose.GIS.FOSS.Rendering.Symbolizers`, `Aspose.GIS.FOSS.Epsg`). It looks like a partial import (the head commit is "Second part").

## Steps to reproduce

```bash
git clone https://github.com/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net.git
cd Aspose.GIS.FOSS-for-.Net
dotnet --version    # 10.0.401
dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release
```

## Actual result

`Build FAILED`, 369 distinct errors. Examples:

```
Aspose.GIS.FOSS\Geometries\IGeometry.cs(5,33): error CS0234: The type or namespace name 'Symbolizers' does not exist in the namespace 'Aspose.GIS.FOSS.Rendering'
Aspose.GIS.FOSS\SpatialReferencing\Internal\OgcEsriSrsTransformer.cs(6,23): error CS0234: The type or namespace name 'Epsg' does not exist in the namespace 'Aspose.GIS.FOSS'
Aspose.GIS.FOSS\Geometries\IPolygon.cs(38,7): error CS0246: The type or namespace name 'Polygon' could not be found
Aspose.GIS.FOSS\SpatialReferencing\GeocentricSpatialReferenceSystemParameters.cs(52,10): error CS0246: The type or namespace name 'Axis' could not be found
Aspose.GIS.FOSS\SpatialReferencing\ProjectedSpatialReferenceSystem.cs(60,19): error CS0246: The type or namespace name 'Projection' could not be found
Aspose.GIS.FOSS\FileDriver.cs(346,16): error CS0246: The type or namespace name 'Dataset' could not be found
Aspose.GIS.FOSS\GeoJsonDriver.cs(18,30): error CS0115: 'GeoJsonDriver.SupportsSpatialReferenceSystem(SpatialReferenceSystem)': no suitable method found to override
Aspose.GIS.FOSS\Geometries\Geometry.cs(12,35): error CS0535: 'Geometry' does not implement interface member 'IGeometry.AsImage(AbstractPath, Measurement, Measurement, Renderer, VectorSymbolizer)'
```

`dotnet test Aspose.GIS.FOSS.Tests` fails the same way (`MainTests.cs(36,40): CS0246 GeoPackageDataset`, `CS0103 Dataset`, `CS0103 Drivers`).

Types referenced but declared nowhere in the repository: Axis, BursaWolfParameters, Dataset, Driver, Ellipsoid, Extent, GeoJsonLayer, GeoJsonOptions, GeocentricAxisesOrder, GeographicAxisesOrder, GeographicCrsEntry, GeographicDatum, GeographicDatumEntry, IAttributeIndex, IFeatureStyle, ILinearRing, ISpatialIndex, JoinByGeometryOptions, JoinOptions, LayerEvaluationRestrictions, LayerIndices, LocalDatum, MapInfoCoordinateValidationError, MapInfoCoordinateValidationException, NumericFormat, ParameterType, PointsSequence, Polygon, ProjectedAxisesOrder, Projection, ProjectionMethodIdentifier, Projections, Renderer, SavingOptions, ToWgs84Entry, TransformationError, VectorSymbolizer, VerticalDatum, WkbVariant, WktVariant, WrapAttributesConverter.

## Suggested fix

Add the missing source files (or remove the references), then make `dotnet build` and `dotnet test` pass. A CI workflow that runs both on every push would catch this class of problem.
```

**Draft 2 - title:** `Add a README and a LICENSE, and package metadata in the csproj`

```markdown
## Summary

The repository has no README at all and no LICENSE file, and `Aspose.GIS.FOSS.csproj` carries no package metadata. GitHub reports no license for the repository, and a visitor cannot tell what the library is, how to build it, or under what terms it may be used.

## Evidence (revision b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4)

- `git ls-files` contains no `README*` and no `LICENSE*`/`COPYING*`.
- `gh api repos/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net --jq .license` returns `null`.
- `Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj` contains only `TargetFramework`, `ImplicitUsings` and `Nullable`: no `PackageId`, `Version`, `Description`, `Authors`, `PackageLicenseExpression`, `PackageReadmeFile` or `RepositoryUrl`.
- Comparable repositories in the organizations ship an MIT `LICENSE` (for example `aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET`, 1,063 bytes).

## Suggested fix

Add `README.md`, add the intended OSI-approved `LICENSE` at the repository root, and set the package metadata (id, version, description, authors, license expression, readme, repository URL) in the csproj.
```

**Draft 3 - title:** `Build output is committed (14 files under obj/) and .gitignore does not exclude obj/`

```markdown
## Summary

14 files under `Aspose.GIS.FOSS/obj/` and `Aspose.GIS.FOSS.Tests/obj/` (combined) are tracked (`project.assets.json`, `*.nuget.dgspec.json`, `*.AssemblyInfoInputs.cache`, ...). They contain machine-specific restore state and should not be in source control.

## Evidence (revision b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4)

`git ls-files | grep "/obj/" | wc -l` prints 14. The root `.gitignore` has no `obj/` or `bin/` rule.

## Suggested fix

`git rm -r --cached Aspose.GIS.FOSS/obj Aspose.GIS.FOSS.Tests/obj` and add `obj/` and `bin/` to `.gitignore` (the standard `dotnet new gitignore` output covers both).
```

---

## 3. aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript

### Why there is no sealed candidate
- Registry: `dry_run`, `active: true`. Local `runs/transactions/aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript/92446cce.../` is a stale 2026-09-06 attempt (S4 timeouts). The decision log records, in order:
  - 2026-09-26: S3 gateway 500; S5 context window overflow (283,065 input tokens).
  - 2026-09-27: schema de-duplication (PDFTS-SCHEMA-DEDUP) lets S5 clear.
  - Later in 2026-09: BC-07 example selection, then a drifted-revision BC-02 CONTRADICTED.
  - 2026-10-04 at `a8661f8b`: S4 batch 1 truncated at 32,000 tokens (DEFECT_INDEX `s4_reconciliation.output_runaway_past_budget`, sighting 3), and a fresh draw produced a BC-07 overage of 328 of 1262 visible lines (DEFECT_INDEX `readme.bc07_visible_budget_repaired_by_model_only`, sighting 5).
- Fixes on main: #210 (S4 reply bounded inside `max_output_tokens`), `bound_visible_line_overage` (deterministic-first BC-07 bound), #226 (npm source-install fallback), #202 (BC-06), #261 (per-call plan list caps). I found no live PDF-TS draw after these. DEFECT_INDEX itself says both defects close only on a live draw.

### Independent verification (head `c672b39` = 2026-10-09; the handoff's revision `a8661f8b` was 2026-10-02, so the head has moved by 7 commits; 29 commits total)
- Inventory: 2,553 tracked files: `src/` 453, `test/` 1,401, `docs/` 580, `scripts/` 49, `examples/` 38, `fonts/` 18. `LICENSE` is MIT (copyright 2026 Aspose Pty Ltd) and matches `package.json` `"license": "MIT"`. `THIRD-PARTY-NOTICES.md` is present. `README.md` is **494,633 bytes / 4,612 lines / 91 headings** (that size is why the pipeline works on 1,262 visible lines and 3,304 facts).
- Build: `npm ci` (50 packages), `npm run build` exits 0 (152 exports from `dist/index.js`), `npm run typecheck` exits 0.
- Tests: `npm test` gives 4 failed files, 22,715 passed, 4 skipped (22,723). The four failures look environment-specific (a retry-count assertion in `ai-openai-retry`, two `x-user-defined` windows-1252 meta charset tests that depend on ICU, and a timing ratio 3.07 vs 3 in `layout-pagination-cost`). Not reportable without a second environment.
- License disclosure is sound: `package.json` is MIT, and the bundled URW fonts under AGPLv3 with the font exception are disclosed in `THIRD-PARTY-NOTICES.md` and the README.
- npm registry today: `@asposefoss/pdf`, `@aspose/pdf` and `aspose-pdf-foss` all return 404. The README documents only a source install. `package.json` already has `publishConfig` and `prepublishOnly`, so publication is planned.
- Upstream issues: none open (two closed README-refresh PRs).

### Classification: PROCESSABLE
No upstream defect blocks sealing. Open work is on our side:
1. A fresh `present --fresh` at the current head. S4 and BC-07 fixes are unproven live.
2. A README this size is a structural stress test for the 300-visible-line budget (decision log notes 300 enforced vs 320 stated in README_CONTRACT; this is an owner question).
3. The head moves almost daily, so the seal must tolerate `VALID_UPDATE_AVAILABLE` re-draws.

### Existing handoff
`evidence/upstream-defects/aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript/ef667e7d...json` (BC-02, npm 404 for `@asposefoss/pdf`, revision `a8661f8b`, `HANDOFF_PENDING`, `issue_ref: null`).
- Evidence still accurate today: package name unchanged at `c672b39`; npm still 404.
- But the claim is not a defect: the README documents a source install and does not claim a registry install, and the package is prepared for publication. Recommend withdrawing this handoff (close as "not a defect / documented") rather than filing it. The "install_command:npm is CONTRADICTED" body would read as noise to maintainers. If an issue is wanted at all, make it a publication-plan note, not a defect.

### Issue drafts
None. (The only reportable fact is the unpublished npm package, which is documented and intentional. The 4 failing tests need a second environment before reporting.)

---

## 4. aspose-psd-foss/Aspose.PSD-FOSS-for-.NET

### Why there is no sealed candidate
- Registry: `dry_run`, `active: true` (enabled from `disabled` by the 2026-10-07 owner decision, `docs/DECISION_LOG.md` 2026-10-07 `feat/enable-psd-1009`, `project/state.yaml` OWNER entry). History: the 2026-09-30 retry list noted "disabled, no reason recorded"; the 2026-10-01 04:25 UTC owner ruling said "cannot be processed, leave it", based on a README-only tree (the PSD repos then held a two-line README and no source); the 2026-10-07 owner decision reversed it.
- The upstream put real source on `main` on 2026-10-01 (PR #6 "First implementation"). There is no `runs/transactions/` entry for the .NET repo, and no `present` draw has been recorded since the enablement. The reason there is no sealed candidate is simply that it has never been drawn.

### Independent verification (head `f4e1b261922d514591b898f01346af1c6bf59f92`, 2026-10-01)
- Inventory: 111 tracked files: `src/` 86 (83 `.cs`), `samples/` 18 (8 sample projects + `Common`), `documentation/` 4, `Aspose.PSD-FOSS-for-.NET.sln`, `README.md` **8,533 bytes** (Quick Start, Installation, Samples table, Supported Scope, Out of Scope, License: "MIT"). Test fixtures: 8+ `.psd`/`.psb` files under `src/Aspose.PSD.FOSS.Test/testdata`.
- **No LICENSE file** (GitHub `license: null`). The csproj has `<PackageLicenseExpression>MIT</PackageLicenseExpression>` and the README ends with "## License / MIT", so the pipeline can declare the license from the manifest.
- Build: `dotnet build src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj -c Release` exits 0, 0 warnings; `dotnet pack` happens on build (`GeneratePackageOnBuild`). `dotnet test src/Aspose.PSD.FOSS.Test` gives `Passed! 77, Failed 0`. `dotnet build samples/Aspose.PSD.FOSS.Samples.Basic` succeeds.
- **Placeholder metadata in the csproj:** `<PackageProjectUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</PackageProjectUrl>` and `<RepositoryUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</RepositoryUrl>` (both stay in the packed nuspec), and `<Authors>SID</Authors>`.
- NuGet: `aspose.psd.foss` returns 404 (README says: "not published to NuGet yet"); `aspose.psd` returns 200 (commercial).
- Open upstream issue **#5** (babar-raza, 2026-09-25): "Add a LICENSE file and merge real source to main". Its second request is now satisfied (source merged 2026-10-01); the LICENSE request is still open and still accurate. A short update comment would be useful, but I did not post it.

### Classification: PROCESSABLE
No upstream defect blocks sealing: it builds, tests pass, README substantive, license declared in manifest and README. The README's "## License MIT" has no link target (no LICENSE file), so the pipeline's license section will be a manifest-declared fact (by code reading, `license_facts(declared=...)`). The open items are ours: run a first live draw, verify the .NET source-build rescue admits install (build exits 0), and handle the NuGet-sample note (the repo has two parallel sample sets, one against the commercial `Aspose.PSD` package).

### Existing handoff
None.

### Issue drafts (text only; not filed)

**Draft 1 - title:** `Aspose.PSD.FOSS.csproj contains placeholder URLs (github.com/yourorg/...) and Authors "SID"`

```markdown
## Summary

`src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj` still carries template placeholders. Because `GeneratePackageOnBuild` is true, they are baked into every produced `.nupkg`/nuspec.

## Evidence (revision f4e1b261922d514591b898f01346af1c6bf59f92)

```xml
<Authors>SID</Authors>
<PackageProjectUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</PackageProjectUrl>
<RepositoryUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</RepositoryUrl>
```

`https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET` is not this repository. The correct URL is `https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`.

## Suggested fix

Set `PackageProjectUrl` and `RepositoryUrl` to the real repository and set `Authors`/`Company` to the intended owner (for the other FOSS repositories this is "Aspose"). The missing `LICENSE` file is tracked separately in #5.
```

Update note for existing issue #5 (suggested comment text): "The real source was merged to `main` on 2026-10-01 (PR #6), so the second request is done. Request 1 is still open: `git ls-files` at f4e1b261 has no LICENSE, although the csproj declares `PackageLicenseExpression` MIT and the README says MIT."

---

## 5. aspose-psd-foss/Aspose.PSD-FOSS-for-Python

### Why there is no sealed candidate
- Registry: `dry_run`, `active: true` (enabled 2026-10-07). The local transaction `runs/transactions/aspose-psd-foss__Aspose.PSD-FOSS-for-Python/2f6c746a.../disposition.json` is a **stale** `NON_PROCESSABLE` / `NO_IMPLEMENTATION_EVIDENCE` record: at that revision the tree held only `README.md` (one blob `7bdf4d4b`). `evidence/build/G1_FIRST_VALID_CANDIDATE/manifest.json` line 260 and `G3_PYTHON_COHORT` record the same placeholder finding. The resume predicate was "a later default-branch revision adds a python manifest or .py source". The `.py` half has since been met: head `664446b9` (2026-10-05) has 66 modules plus 16 test modules.

### Independent verification (head `664446b97952c063baf828f469995ad2a160bae7`)
- Inventory: 94 tracked files: `aspose_psd_foss/` (66 `.py`, 2 of them generated `obj/debug/net10_0/*.py`), `aspose_psd_foss_test/` (16 `.py` + 10 `.psd`/`.psb` fixtures), `README.md`, `.gitignore`. Nothing else.
- **README is 69 bytes:** `# Aspose.PSD-FOSS-for-Python` / `FOSS version of Aspose.PSD for Python`. **No LICENSE** (GitHub `license: null`). **No `pyproject.toml`, `setup.py` or `setup.cfg`**: `pip install --dry-run .` → `ERROR: Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.`
- **`aspose_psd_foss/__init__.py` is empty** (0 lines): no public API surface is exported.
- Code health: all 82 `.py` files pass `ast.parse`; `import aspose_psd_foss.psdimage` and the other probed modules import fine; **75 tests pass** when the files are named explicitly (`pytest aspose_psd_foss_test/*tests.py`), but a plain `pytest` from the repository root runs **zero tests** because the files are named `*tests.py` (not `test_*.py` or `*_test.py`).
- **Generated MSBuild output committed as Python files:** `aspose_psd_foss/obj/debug/net10_0/aspose_psd_foss_assemblyinfo.py` ("This code was generated by a tool ... Generated by the MSBuild WriteCodeFragment class", `__company__ = "SID"`), `..._globalusings_g.py`, and the two test counterparts. This looks like an automated C#-to-Python port that carried build artifacts along.
- PyPI: `aspose-psd-foss` returns 404; `aspose-psd` returns 200 (a different, commercial package).
- Open upstream issues: **#4** (babar-raza, 2026-09-25: no LICENSE and no source on main - second half now satisfied) and **#1** (lindent: asking about the timeline for "fully open-sourced"). Real source arrived via PR #3 (merged 2026-10-05).

### Classification: UPSTREAM_DEFECT_BLOCKED (by code reading; soft)
- It passes the `assess_processability` gate now (`.py` source present), so `present` will not stop at NON_PROCESSABLE.
- Likely blockers once it runs, all by code reading and not run: README contract section 20 `license` is `Required` with no condition, but the repository has no license file and no manifest to declare one (`license_facts` needs `declared`); there is no install fact source (no manifest, PyPI 404, no README example) so `install_command:pip` has nothing to support beyond a `source_checkout` tier that needs an EXECUTED example; the README has no inherited content to preserve.
- Resume predicate: a LICENSE file (or manifest `license`) and a Python manifest (`pyproject.toml`) are added, ideally with a real README.
- It deserves one honest draw to confirm; I did not run it. If the draw yields a processable candidate with only thin sections, then reclassify as PROCESSABLE.

### Existing handoff
None. Existing issue #4 covers only the LICENSE (its body is partly stale).

### Issue drafts (text only; not filed)

**Draft 1 - title:** `No pyproject.toml/setup.py (package is not installable), README is a two-line placeholder, and aspose_psd_foss/__init__.py is empty`

```markdown
## Summary

Now that the source is on `main`, the repository still cannot be installed, documented or used as a package:

1. There is no build manifest.
2. `README.md` is the original two-line placeholder (69 bytes).
3. `aspose_psd_foss/__init__.py` is empty, so the package exports nothing.

## Evidence (revision 664446b97952c063baf828f469995ad2a160bae7)

```
$ python -m pip install --dry-run --no-deps --no-build-isolation .
ERROR: Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.
```

`README.md` in full: `# Aspose.PSD-FOSS-for-Python` / `FOSS version of Aspose.PSD for Python`.

`wc -l aspose_psd_foss/__init__.py` prints 0. Users must import from deep module paths such as `aspose_psd_foss.psdimage`.

For reference, the .NET sibling `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET` ships an 8.5 KB README with install, quick start, supported scope and limitations.

## Suggested fix

Add a `pyproject.toml` (name, version, `requires-python`, license, `packages`), export the public API (`PsdImage`, `Image`, `Layer`, ...) from `__init__.py`, and write a README with install, a quick start and the supported scope. The missing `LICENSE` is tracked in #4.
```

**Draft 2 - title:** `Generated MSBuild obj/ files are committed as .py, and the test modules are not discovered by pytest`

```markdown
## Summary

1. Four MSBuild-generated files were committed as Python modules.
2. A plain `pytest` collects no tests because the test modules are named `*tests.py`.

## Evidence (revision 664446b97952c063baf828f469995ad2a160bae7)

Tracked files:

```
aspose_psd_foss/obj/debug/net10_0/aspose_psd_foss_assemblyinfo.py
aspose_psd_foss/obj/debug/net10_0/aspose_psd_foss_globalusings_g.py
aspose_psd_foss_test/obj/debug/net10_0/aspose_psd_foss_test_assemblyinfo.py
aspose_psd_foss_test/obj/debug/net10_0/aspose_psd_foss_test_globalusings_g.py
```

The first begins `# <auto-generated> This code was generated by a tool. Runtime Version:4.0.30319.42000 ... Generated by the MSBuild WriteCodeFragment class.` and sets `__company__ = "SID"`; they are C# build output with no meaning in a Python package.

```
$ python -m pytest -q
no tests ran
$ python -m pytest -q aspose_psd_foss_test/*tests.py
75 passed
```

pytest's default `python_files` is `test_*.py` or `*_test.py`, so `psdheadertests.py`, `psdimagesavetests.py` etc. are skipped unless named explicitly. The root `.gitignore` is the generic Python template.

## Suggested fix

Delete the four `obj/` files and add `obj/` to `.gitignore`; rename the test modules to `test_*.py` (or set `python_files = "*tests.py"` in the pytest configuration once a `pyproject.toml` exists).
```

Update note for existing issue #4: the source is on `main` since PR #3 (merged 2026-10-05); the LICENSE request remains and is accurate.

---

## 6. aspose-tex-foss/Aspose.TeX-FOSS-for-Python

### Why there is no sealed candidate
- Registry: `dry_run`, `active: true`. `project/state.yaml` and the decision log: "aspose-tex-foss/Python has a genuine upstream defect outside this project's control (35/45 source files fail ast.parse)". `evidence/build/G3_PYTHON_COHORT/manifest.json` line 499-500 records NOT_PROCESSABLE with a resume predicate ("a later default-branch revision restores the source indentation so ast.parse accepts src/aspose_tex/presentation/__init__.py"). The local `runs/transactions/.../181015d2.../` is a 2026-09-05 draw that died at S6 on `TeXJob` as an unaccepted identifier, before the cause was found.
- **Pipeline gap to note:** the only `NON_PROCESSABLE` producer in `present` is `assess_processability` (manifest or source suffix present), and TeX passes it. Unparseable source is handled only as a recorded "syntax-error" note by `python_surface.py` and by the re-detector `components/issues/redetect.py`. So `present` would proceed on TeX and fail late rather than stop with a typed NON_PROCESSABLE. By code reading.

### Independent verification (head `181015d2eee3e19f8af3d84e4a932ac84ad47c7c`, pushed 2026-09-02; default branch HEAD unchanged since the handoff)
- Inventory: 314 tracked files; `LICENSE` (MIT, copyright 2026 Aspose Pty Ltd) matches `pyproject.toml` `license = {text = "MIT"}` (name `aspose-tex`, version `26.5`); also `LICENSE-FONTS`. `README.md` 13,934 bytes. `src/aspose_tex` (45 `.py`), `tests/` (73 `.py`), `testdata/`, `run_hello.py`. No `docs/` or `examples/` folder. README says "No PyPI package has been published for this library yet"; PyPI `aspose-tex` returns 404.
- `ast.parse` over every `.py` in the repository (my script, `python -I`): **102 of 119 fail, all IndentationError**. By area: `src/aspose_tex/`: 35 of 45 fail (matches the handoff's 35/45), 10 parse (including all package `__init__.py` files except `presentation/__init__.py`); `tests/`: 66 of 73 fail; `run_hello.py` fails (line 66).
- `src/aspose_tex/presentation/__init__.py`: `IndentationError: expected an indented block after function definition on line 107 (line 108)`. The text at lines 107-108 is `' def __init__(self, destination: ...) -> None:'` followed by `' """'`: every line is indented one space per level, regardless of depth. There are no CR characters or tabs, so this is not a line-ending artifact of the clone.
- `import aspose_tex` fails at the package root: `aspose_tex/__init__.py` line 7 → `aspose_tex/_input/__init__.py` line 3 → `aspose_tex/_input/catcode.py`, line 66: `IndentationError: expected an indented block after 'for' statement on line 65`. So the README's `pip install -e .` followed by any import cannot work.
- Open upstream issues: none (one closed README-refresh PR).

### Classification: UPSTREAM_DEFECT_BLOCKED
Nothing the pipeline can do fixes this: the public API cannot be verified from source that does not parse, and every public symbol claim would lack evidence. Resume predicate stays as recorded: a later default-branch revision restores indentation and `ast.parse` accepts `presentation/__init__.py`.

### Existing handoff
`evidence/upstream-defects/aspose-tex-foss__Aspose.TeX-FOSS-for-Python/c00f9615...json` (NOT_PROCESSABLE v1, EXTRACTING, `HANDOFF_PENDING`, `issue_ref: null`, never filed). **Still accurate today**: same revision, 35 of 45 reproduced exactly, the same `presentation/__init__.py` error text. It understates the problem, though: it does not mention that `import aspose_tex` fails at the package root (catcode.py:66), or that 66 of 73 test files and `run_hello.py` also fail. The draft below extends the handoff's body with those numbers.

### Issue draft (text only; not filed)

**Draft 1 - title:** `102 of 119 .py files fail to parse (IndentationError): src/aspose_tex/ is 35 of 45, tests 66 of 73; "import aspose_tex" fails`

```markdown
## Summary

Most of this repository's Python source does not parse. Indentation has been collapsed to one space per nesting level, so the files are not valid Python. The package cannot be imported at all from this source tree, and the test suite cannot run.

## Environment

- Revision `181015d2eee3e19f8af3d84e4a932ac84ad47c7c` (default branch `main`, unchanged since 2026-09-02)
- Python 3.13, standard library only (`ast.parse`; any Python 3 interpreter reproduces it)

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

Then:

```bash
pip install -e .
python -c "import aspose_tex"
```

## Actual result

- 102 of 119 `.py` files raise `IndentationError`: `src/aspose_tex/` 35 of 45, `tests/` 66 of 73, and `run_hello.py`.
- `src/aspose_tex/presentation/__init__.py` (the module the package's own docstring calls the user-facing entry point, defining `TeXJob`, `TeXOptions` and the `OutputDevice` hierarchy):
  `IndentationError: expected an indented block after function definition on line 107 (line 108)`. Lines 107 and 108 are ` def __init__(self, destination: Path | io.BytesIO | None = None) -> None:` and ` """`, both indented by a single space.
- `import aspose_tex` fails immediately: `aspose_tex/__init__.py` line 7 imports `aspose_tex._input`, which imports `_input/catcode.py`:
  `IndentationError: expected an indented block after 'for' statement on line 65` (line 66).
- The same shape (`expected an indented block after ...`) recurs in every failing file. Affected source files include `_engine/interpreter.py`, `_engine/nodes.py`, `_engine/page_builder.py`, `_input/tokenizer.py`, `_input/reader.py`, `_fonts/font_manager.py`, `_output/pdf_writer.py`, `_output/svg_writer.py`, `_output/dvi_writer.py` and 26 more under `_engine/`, `_fonts/`, `_input/`, `_output/`.

## Suggested fix

Restore the original indentation (re-export from the original formatted source), then add a CI step that runs `python -m compileall src tests` (or `ruff check`) on every push so a collapsed-indentation commit cannot land again.
```

---

## Cross-cutting observations for the owner

1. **GIS was recorded as "BLOCKED_EXTERNAL (gateway)"; the code does not compile.** Treat it as UPSTREAM_DEFECT_BLOCKED and stop spending draws on it until the build passes. The registry's `dry_run` entry and `project/state.yaml`'s "plausibly fixable" label are stale for this repository.
2. **3D-TS and PDF-TS need a fresh live draw, not more code.** The blockers recorded in `project/state.yaml` (2026-09-30) predate fixes #202, #210, #226, #261 and the reviewer F04 fix. DEFECT_INDEX itself says S4 and BC-07 close only on a live draw against PDF-TS.
3. **Both PSD repositories changed state after the 2026-10-01 ruling.** The `.NET` repo is a processable library today; the Python repo has code but no manifest and no license.
4. **Pipeline gap:** unparseable-source NON_PROCESSABLE (TeX) has a re-detector but no producer in `present`. The TeX local transaction in `runs/` predates the diagnosis.
5. **Missing LICENSE file** is the common upstream gap: 3D-TS, GIS, PSD-.NET, PSD-Python (GitHub `license: null` for all four). Open issues #4 and #5 already cover the two PSD repos. G5-W06 (community-file replication) would cover the rest.
6. Test and build artifacts I created live only under `scratchpad/clones/D/`, `scratchpad/nodedl/` and `scratchpad/tools/`.
