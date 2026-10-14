authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
bundle_hash: cc02193b057c1de6ffea3b2e54871285225fde359fe85789d7d8b0f7ede8c32f
readme_sha256: 41d2ff4042c785a656dd944719620352f1a0449591fe604c4a02d65780101c22
source_revision: 66cb26df3b031f0bf6976d4e88dc89721983afa4
live_head: 66cb26df3b031f0bf6976d4e88dc89721983afa4
reviewed_at: 2026-10-11T18:50:00Z
verdict: FIX_REQUIRED
minor_major: MAJOR
net_vs_live: worse
confidence: medium
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run e407503a (wave 5), row sealed at G:\rp-w5\3d-typescript
claims_checked: 14
claims_failed: 1
forbidden_wording_hits: 1
could_not_verify: ["'81 types' count (141 exported declarations under src/, index re-exports not traced)", "Quick Start / Additional Example execution (receipts: type-checked against the clone, not re-run)", "Enterprise Edition target page content"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Documentation & Resources / Scope and Limitations / Key Capabilities", summary: "preserved inherited units are placed in sections that do not own their topic: build paragraph and the whole dev-dependency bullet list under Documentation & Resources, a ninth orphan bullet under Key Capabilities, the licence paragraph inside Scope AND again in License (preserve-first placement fallback, reconciliation/destinations.py _HOMES)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "At a Glance", summary: "diagram drops the live Starting Points and Outputs groups (OBJ/STL/glTF, FBX/COLLADA, 3MF in and out); only a product node and Core Capabilities remain"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "live per-area API tables (16 sections, 97 rows with member detail) flattened into one 81-row table; 33 of 97 live row keys lost"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities", summary: "live opening (free, open-source, MIT-licensed, pure TypeScript, Node.js) replaced by a symbol list; Format I/O bullet says read glTF/OBJ only and omits STL/FBX/COLLADA/3MF reading and 3MF entirely"}
  - {id: F6, kind: code_change, severity: MAJOR, section: "Installation", summary: "the renderer prints internal assurance narration 'build it from a source checkout instead, verified against this revision:' (composition/renderer.py L1113/1129/1144/1146); idea.md L109 and C16 forbid it, and the C16 text check does not catch it"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Scope and Limitations / Development and Testing", summary: "first Scope bullet fuses two unrelated statements; 'built for the typescript platform'; 'requires `Node`.js'; 'sibling 3d/net platform'"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Documentation & Resources", evidence: "cand README L296-310: 'npm run build compiles ...' and a bullet list of xmldom/typescript/jest/eslint/adm-zip under Documentation & Resources, headed by nothing", summary: "orphan preserved fragments in the wrong section"}
  - {id: B2, category: dropped_live_content, section: "At a Glance", evidence: "diff live L28-61 vs cand L23-49", summary: "Starting Points / Outputs dropped from the diagram"}
  - {id: B3, category: dropped_live_content, section: "Opening / Key Capabilities / API Reference", evidence: "retention.py: opening 2 sentences lost, 3MF capability lost, 33 of 97 table keys lost", summary: "valuable live content missing"}
  - {id: B4, category: false_claim, section: "Key Capabilities", evidence: "src/aspose/threed/formats/{stl,fbx,collada,threemf}/*Importer.ts exist; live README states glTF, OBJ, STL, FBX and COLLADA are read and written", summary: "MISLEADING understatement: 'Read glTF 2.0 and OBJ scenes, write STL, FBX, COLLADA, glTF'"}
  - {id: B6, category: forbidden_wording, section: "Installation", evidence: "cand README L67 'verified against this revision'", summary: "internal assurance narration in the public README (renderer-owned sentence)"}
  - {id: B5, category: dangling_prose, section: "Scope and Limitations", evidence: "cand README L316 (rendering and the 3MF packaging defect in one bullet), L331-334 (licence paragraph; the same paragraph is in License)", summary: "fused bullet and duplicated licence text"}
---

# 1 Bundle facts
manifest.state READY_FOR_PROPOSAL; revision equals live head; README sha256 equals manifest; no-op VERIFIED, 0 provider calls; validation BC-01..BC-12, BC-14 PASS; review ACCEPT/ACCEPT (as returned ACCEPT, no demoted findings); second_reader read 2 (trigger ADVISORY_DEFERRAL, nothing corroborated). Advisories: inherited 081.paragraph (AGENTS.md) INTERNAL_DEFERRAL (ruling: fine, an internal file); BC-14 pending, no registry reading (ruling: true, the package is unpublished, npm GET 404). Wave-3 (f69f75c7) and wave-4 (8c48f4d2) sealed this repository too; this is the third sealed variant.

# 2 Live comparison
ADDS (true): "not yet published on npm; build from a source checkout" (npm registry 404 for @aspose/3d: TRUE; live said the same), Dependencies section split Required/Development (TRUE, equals package.json), "32 test files under tests/" (TRUE: 32 *.test.ts), typecheck/lint commands (TRUE), no-licence-file note (TRUE: no LICENSE in clone).
DROPS (valuable): the live opening; 3MF as a format (Starting Point and Output, capability, API section); STL/FBX/COLLADA read; Starting Points/Outputs groups; per-area API sections; "Enumerate a loaded scene's node hierarchy" example (a live example whose receipt FAILED here: `Entity.controlPoints`, so dropping it is correct); lead-in sentences of examples; the `Importing files produced by other tools is unaffected` limitation clause; the License badge and the AGENTS.md link.
CHANGES: Scope and Development prose is wordier and partly garbled (`Node`.js, typescript platform).
NET: worse.

# 3 Claim checks
| # | Claim | How checked | Result |
|---|---|---|---|
| 1 | "@aspose/3d is not yet published on npm" | GET registry.npmjs.org/@aspose%2F3d -> 404 | PASS |
| 2 | version 24.12.0 | clone package.json | PASS |
| 3 | required dependency xmldom ^0.6.0 | package.json dependencies | PASS |
| 4 | 10 development dependencies and versions | package.json devDependencies | PASS |
| 5 | 32 test files under tests/ | find tests -name '*.test.ts' = 32 (33 files incl. setup) | PASS |
| 6 | scripts build/test/lint/typecheck | package.json scripts | PASS |
| 7 | build output path ./dist/aspose/threed and package.json main dist/index.js not produced | src has only aspose/; no src/index.ts | PASS (inherited true defect) |
| 8 | LightType POINT, DIRECTIONAL, SPOT, AREA, VOLUME | entities/LightType.ts | PASS |
| 9 | ObjLoadOptions.enableMaterials/normalizeNormal, StlSaveOptions.binaryMode | formats/obj, formats/stl | PASS |
| 10 | Scene.render, Node.selectSingleObject, Mesh.doBoolean throw | Scene.ts L382, Node.ts L223-224 | PASS |
| 11 | "Read glTF 2.0 and OBJ; write STL, FBX, COLLADA, glTF" | importers present for STL, FBX, COLLADA, 3MF | MISLEADING (introduced) |
| 12 | MIT, no licence file | package.json license; ls | PASS |
| 13 | links (21) | mech.py --net: none non-200; one duplicate target #api-reference | PASS |
| 14 | "81 types" | grep gives 141 exported declarations | COULD_NOT_VERIFY |

# 4 Mechanical and wording
mech.py: one H1, sections in required order, one mermaid fence (the whole At a Glance), fences have language, zero mechanical wording hits, but by reading Installation L67 says 'verified against this revision' (assurance narration; the protocol forbids narration of source revisions/evidence: 1 hit), Enterprise Edition anchor shape ok, no forum links. Mermaid: `flowchart LR`, rendered with the repository's Edge/mermaid toolchain: product node left, one Core Capabilities group right, horizontal, zero clipped fonts (PNG inspected). By reading: B1, B5, Key Capabilities has 9 list items (8 capabilities plus an orphan triangulation bullet) against the 3-8 rule; the preserved "Additional worked examples cover per-node inspection ..." sentence points at an example that was dropped.

# 5 Omitted information in the clone
AGENTS.md (internal, correctly withheld), jest.config.js, tsconfig target; Node engine floor (README says none declared: true).

# 6 Drafted upstream issues (TEXT ONLY)
1. package.json `main`/`types` point at dist/index.js and dist/index.d.ts which the build never produces (no src/index.ts). Severity medium. Repro: npm install && npm run build && ls dist.
2. `adm-zip` is a devDependency but ThreeMfImporter needs it at runtime (inherited claim; not reproduced here).

# 7 Verdict
FIX_REQUIRED (MAJOR): one introduced MISLEADING claim and five blocking template/dropped-content items, but nothing false enough for three independent introduced FAIL results. The fixes F1-F3 are code changes (placement, diagram renderer, API surface), so a redraw alone would reproduce them. Compared with wave 3 this candidate is much closer to publishable: sections and diagram are template-conformant and the factual spot-checks pass.
