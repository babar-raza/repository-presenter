authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
bundle_hash: 4f55f2cbed727dc44c76fdb659cfac1df4fbf404a21906be6d56364c4f5c81eb
readme_sha256: 976a823a0f6fda07461bbc242917d8d1228545e096a38992a80ed4c275b82446
source_revision: 66cb26df3b031f0bf6976d4e88dc89721983afa4
live_head: 66cb26df3b031f0bf6976d4e88dc89721983afa4
reviewed_at: 2026-10-11T08:05:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 18
claims_failed: 4
forbidden_wording_hits: 0
could_not_verify: ["npm install / npm run build / npm test not run (no Node.js on reviewer machine)", "Quick Start and Additional Example type-check receipts taken from examples.json (not re-run)"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Key Capabilities / Scope and Limitations / Dependencies", summary: "3MF import/export (ThreeMfImporter/ThreeMfExporter, wired into Scene.open/save) and its verified packaging defect (adm-zip is only a devDependency but required at runtime) are dropped; adm-zip is listed as a plain development dependency with no caveat"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "six verified live limitations lost (Scene.render throws; VertexElement.setIndices/clear; Node.selectSingleObject/selectObjects; Text watermarking; Mesh height-map constructor; 'FileSystem abstraction does not affect open/save'); Mesh Boolean named as doBoolean instead of union/difference/intersect; Scope sentence 'Scene.save supports saving to OBJ and glTF' contradicts Key Capabilities (STL, FBX, COLLADA also written)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "StepMode described as 'how vertex data is advanced per vertex or per instance during rendering' (it is the keyframe step interpolation mode; live was right); 312 tautological 'Defined as ...' bullets; 'VERSION: Public method.' (it is a static string constant)"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "'33 test files' counts tests/setup.ts; real test files are 32"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Opening", summary: "remove invented audience ('Developers use it to build 3D content pipelines ... inspecting scene hierarchies'); restore 'free, open-source, MIT-licensed ... pure TypeScript, no native bindings'"}
  - {id: F6, kind: redraw, severity: MINOR, section: "At a Glance / badges / Installation / Documentation", summary: "restore Starting Points/Outputs, the MIT badge, build/Node/TypeScript notes, AGENTS.md pointer (file exists; deferred as INTERNAL_DETAIL), Mesh.triangulate capability, per-class API descriptions"}
blocking_findings:
  - {id: B1, category: false_claim, section: "API Reference", evidence: "src/aspose/threed/animation/KeyFrame.ts L13 `_stepMode = StepMode.PREVIOUS_VALUE` (keyframe stepped-interpolation mode); live README row: 'controlling how stepped (constant) interpolation is applied ... PREVIOUS_VALUE, NEXT_VALUE'", summary: "INTRODUCED: wrong description of StepMode"}
  - {id: B2, category: false_claim, section: "Development and Testing", evidence: "find tests -type f = 33, of which tests/setup.ts is not a test; *.test.ts = 32", summary: "INTRODUCED: 'The suite covers 33 test files' misleading"}
  - {id: B3, category: false_claim, section: "Opening", evidence: "no README/AGENTS/docs text states this audience; keywords in package.json are only format names", summary: "INTRODUCED: invented audience sentence"}
  - {id: B4, category: dropped_live_content, section: "Key Capabilities / Scope and Limitations", evidence: "src/aspose/threed/formats/threemf/*.ts, Scene.ts L196-238 require('./formats/threemf/...'); package.json adm-zip only under devDependencies; src/aspose/threed/Scene.ts L383 render throws", summary: "dropped 3MF capability and its packaging defect, and five other verified limitations; candidate now lists adm-zip as a dev-only dependency, hiding the runtime failure"}
  - {id: B5, category: false_claim, section: "Scope and Limitations", evidence: "README L640 vs Key Capabilities L54", summary: "INTRODUCED: Scope states Scene.save supports 'OBJ and glTF' while the capability list says STL, FBX and COLLADA are also written; reader is left unsure which formats work"}
  - {id: B6, category: dropped_live_content, section: "At a Glance / API Reference", evidence: "diff live vs candidate", summary: "At a Glance loses Starting Points/Outputs (3MF, STL, FBX, COLLADA inputs); Mesh.triangulate capability, AGENTS.md pointer and MIT badge dropped; per-class curated API detail replaced by member dump"}
  - {id: B7, category: other, section: "API Reference", evidence: "table has 81 rows; src exports 140 classes/interfaces/enums; format option types the README itself imports (ObjLoadOptions, StlSaveOptions) are absent", summary: "INHERITED/MISLEADING: 'The verified public surface has 81 types' and 'covers all 81 verified public types' while option/format types used in examples are not listed"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision equals live head; README sha256 equals manifest. review ACCEPT/ACCEPT; findings []; second_reader triggered (ADVISORY_DEFERRAL), read 2, corroborated [].
- validation BC-01..BC-12, BC-14 PASS. Advisories:
  - inherited_unit:081 (AGENTS.md pointer) deferred INTERNAL_DETAIL: ruling: AGENTS.md exists in the clone and the live README links it for contributors; the deferral loses a true, useful pointer (minor, B6). Same pattern appears in 3D-.NET where the candidate does keep AGENTS.md; inconsistent.
  - BC-14 pending: no registry reading for the version; version held to the manifest. Ruling: acceptable - I verified the package is NOT on npm (404 for @aspose/3d, @aspose-3d-foss/3d, aspose-3d-foss), so "not yet published on npm" is TRUE.
- Examples: #1 EXECUTED, #2 FAILED (`Entity.controlPoints` does not exist: the live "Enumerate a loaded scene's node hierarchy" example does not type-check - correctly dropped), #3, #4 EXECUTED.
- 15 headings (Transform and Spatial, Materials, ...) OMIT_UNSUPPORTED: the live "Detailed Member Reference" structure was discarded wholesale and replaced by machine member dumps.

# 2 Live comparison

ADDS (verified TRUE): "@aspose/3d is not yet published on npm" (TRUE); version 24.12.0 (package.json); "no license file is present at this revision" (TRUE: clone has no LICENSE; package.json license MIT - valuable disclosure); Scope note that example code imports from the local build path because `main` is `dist/index.js` but tsc emits `dist/aspose/threed/...` (TRUE: rootDir src, no src/index.ts); "33 test files" (MISLEADING); invented audience (FALSE); StepMode description (FALSE).
DROPS: see B4, B6; plus "Triangulate ... or `Mesh.triangulate()`", the 3MF capability, "pure TypeScript with no native bindings", TypeScript 5.0+ / Node 18/20/22 build note, dependency explanations (what xmldom/adm-zip are used for), Contributors-only badge row (MIT badge dropped), Documentation "Issues" bullet kept.
CHANGES: Quick Start equal; Installation equal (source build); Key Capabilities: 7 vs live 10 (worse); Scope: 6 bullets vs live 13 (worse, B4/B5); Development: equal plus test-count (misleading) and prose.
NET: worse.

# 3 Claim checks

| # | Claim (line) | How checked | Result |
|---|---|---|---|
| 1 | `@aspose/3d` not published on npm (L59) | curl registry.npmjs.org/@aspose%2F3d -> 404 (+2 variant names) | PASS |
| 2 | package version 24.12.0 (L103,144) | package.json | PASS |
| 3 | `xmldom ^0.6.0` required dependency (L72) | package.json dependencies | PASS |
| 4 | ten development dependencies with versions (L76-85) | package.json devDependencies equal | PASS |
| 5 | `npm run build/test/typecheck/lint` scripts (L61-669) | package.json scripts | PASS (not executed: no Node) |
| 6 | 33 test files (L652) | find tests -type f = 33; tests/setup.ts is a setup file; 32 *.test.ts | FAIL (introduced, misleading) |
| 7 | Mesh.doBoolean/optimize/isManifold throw 'not implemented' (L639) | Mesh.ts L78-99 | PASS |
| 8 | FileSystem methods unimplemented (L644) | utilities/FileSystem.ts L5-21 | PASS |
| 9 | declared entry point does not match build output (L640) | package.json main dist/index.js; tsconfig outDir dist rootDir src; no src/index.ts | PASS |
| 10 | OBJ `enableMaterials`, `normalizeNormal`, STL `binaryMode` (L110-120) | ObjLoadOptions.ts, StlSaveOptions.ts | PASS |
| 11 | Light types POINT, DIRECTIONAL, SPOT, AREA, VOLUME (L50) | LightType.ts includes AREA, VOLUME | PASS |
| 12 | writes STL, FBX (ASCII), COLLADA, glTF; reads glTF, OBJ (L54) | exporters/importers exist in formats/{stl,fbx,collada,gltf,obj} | PASS (incomplete: also reads STL, FBX, COLLADA, 3MF) |
| 13 | "Scene.save supports saving to OBJ and glTF" (L640) | contradicts L54 and the exporters list | FAIL (introduced, MISLEADING) |
| 14 | `StepMode` = per-vertex/instance advance during rendering (L238) | KeyFrame.ts usage | FAIL (introduced) |
| 15 | 81 public types (L146, L630) | table rows 81; exported classes/interfaces/enums 140; ObjLoadOptions/StlSaveOptions used in examples are not rows | MISLEADING (inherited) |
| 16 | MIT licence, no licence file (L673) | package.json license MIT; no LICENSE file | PASS |
| 17 | Links (21) | mech.py --net: no non-200, no missing relative targets | PASS |
| 18 | "Developers use it to build 3D content pipelines ..." (L7) | no supporting text | FAIL (introduced) |

# 4 Mechanical and wording

- mech.py: 1 H1; sections in order; required present; one mermaid fence; fences typed; 0 forbidden hits; Enterprise Edition anchor shape OK; no forum links; one duplicate target (#api-reference).
- Prose faults: "requiring `Node`.js and npm" (code span splitting a product name); "accessible via childNodes", "createPolygon", "rootNode property", "open and save methods" etc. bare identifiers without code spans in several places (BC-04 intent violated, passed); "VERSION: Public method."; 312 'Defined as ...' bullets; first-person-free but the Scope bullet "must be installed by cloning the repository ... shown in the install command" is clumsy.
- Duplicates: Detailed Member Reference closes by repeating the API Reference lead sentence about `scene.open()`; "81 verified public types" appears twice.
- Garbled description rows: `StepMode` (false), `WeightedMode` ("represents a mode for applying weighted influence in Aspose.3D FOSS for TypeScript": vacuous), `ImageRenderOptions` ("controls how a 3D scene is rendered to an image file": rendering is not implemented).

# 5 Omitted information in the clone

- AGENTS.md (implementation status, dev rules): live links it; omitted (B6).
- 3MF exporter/importer: valuable (B4). FBX/COLLADA/STL importers: the capability list says only "write" for these.
- tests/ (32 suites) as usage documentation; jest.config.js: marginal.
- No CHANGELOG, no CI workflows, no LICENSE file (an upstream defect, below).

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: no LICENSE file although package.json declares MIT. Where: repository root; package.json `"license": "MIT"`. Fix: add LICENSE with copyright holder. Severity: medium (licence clarity for a vendor repository). Proof: `ls -a` of a fresh clone shows no LICENSE.
2. Title: package entry point `dist/index.js` does not exist after `npm run build`. Where: package.json `main`/`types`, tsconfig.json `rootDir: ./src`; build emits `dist/aspose/threed/index.js`. Fix: point main/types at `dist/aspose/threed/index.js` or add src/index.ts. Severity: medium (published install cannot be imported by name). Possible, unreproduced here (no Node): reasoning from tsconfig and tree.
3. Title: `adm-zip` is a devDependency but required at runtime by ThreeMfImporter/ThreeMfExporter (`require('adm-zip')`). Fix: move to `dependencies`. Severity: medium.
4. Title: README (live) example enumerating `node.entity.controlPoints` does not type-check (TS2339: Property 'controlPoints' does not exist on type 'Entity'). Severity: low.

# 7 Verdict and reasons

DO_NOT_PROPOSE (MAJOR): three independent INTRODUCED false/misleading claims (B1 StepMode, B2 test count, B3 invented audience, plus B5 contradictory format statement) and heavy loss of verified live content (B4, B6: 3MF and its defect, six limitations, At a Glance sources/outputs). The candidate's honest "not yet published on npm" and no-licence-file statements are good but already implied by the live README's source-install route and are outweighed.

Universal defects for routing: (U1) 15 live API-group headings OMIT_UNSUPPORTED "No heading ... is supported" - the reconciler treats a heading as needing its own fact, discarding curated live API grouping in favour of a machine dump; (U2) test-file count includes support files (setup.ts, csproj, logs) - same as 3D-.NET; (U3) enum/class descriptions authored by the model from the NAME only (StepMode, WeightedMode, ImageRenderOptions) without checking usage - the factual gate does not cover API-table descriptions; (U4) invented audience sentence in the opening (now seen in 3D-Java, Cells-.NET, 3D-TypeScript); (U5) dropped capability whose fact exists (3MF) because the capability list is capped and no coverage check compares extracted capabilities against the source's registered formats; (U6) Scope limitations list is rebuilt from a subset of facts rather than carrying every VERIFIED_PRESERVE'd live bullet; (U7) 'Defined as `X`.' member bullets (tautological) emitted for every member.

Confidence high. Could not verify: see front matter.

# 8 Retention of live content (added in the wave-3 completion pass)

Method (retention.py, read-only): the live README and the candidate are split into sentences (prose outside fences, tables and headings), list items, unique link targets (an absolute repo-file link equals the same relative link) and fenced code blocks. "Verbatim" = the whitespace-collapsed live unit appears unchanged in the candidate; "reworded" = best similarity >= 0.80 to a candidate unit of the same kind; "lost" = below 0.80. Table rows are reported separately (API tables are rewritten by the pipeline, so row text is a weaker signal than row keys).

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 47 | 7 | 15% | 2 | 38 |
| list items | 42 | 15 | 36% | 1 | 26 |
| links (unique targets) | 22 | 19 | 86% | 0 | 3 |
| code blocks | 8 | 6 | 75% | 0 | 2 |
| CORE (four kinds) | 119 | 47 | 39% | 3 | 69 (58%) |
| table rows (supplemental) | 97 | 16 | 16% | 0 | 81 (64 of 97 row keys kept) |

Lost: the opening's two sentences; most feature bullets (mesh construction, camera/light placement, 3MF read/write, per-format options types); every dependency explanation (`xmldom`, `typescript`, `jest`, `ts-jest`, `eslint`, `adm-zip`, `@types/*`); the Node.js version statement; all disclosed defects: the 3MF runtime-dependency/npm packaging defect, the `package.json` entry point not produced by the build, `Scene.render()`, Boolean operations/`optimize()`/`isManifold()`, `VertexElement.setIndices()/clear()`, `Node.selectSingleObject()`, text watermarking, FileSystem virtualization, OBJ import per-face materials, OBJ export of nested geometry, binary GLB export failing for non-empty meshes, glTF re-import duplicates; the Enterprise sentence (reworded); the TypeScript node-enumeration example (does not compile upstream, justified) and the mermaid diagram (rewritten); `AGENTS.md` link, MIT badge. Table: 81 of 97 rows differ by more than 20%; only 64 of 97 row keys kept (33 types dropped from the API tables).
