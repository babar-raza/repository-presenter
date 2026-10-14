authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-.NET
bundle_hash: effd73dfa42873d2f706b3667e6084b2dfb089b7fc11b82b8293e2eaf3bb072e
readme_sha256: 5864a5047eb8727e70ad62c64f2c227849ee5c721f0e4f4767f17cb468a1480f
source_revision: 52b0f00ebf28a0b4173921725ff170685ec2c502
live_head: 52b0f00ebf28a0b4173921725ff170685ec2c502
reviewed_at: 2026-10-12T12:55:00Z
verdict: FIX_REQUIRED
minor_major: MAJOR
net_vs_live: mixed
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run e19b0f3b (wave 7) SEALED row, G:\rp-w7\3d-net
claims_checked: 16
claims_failed: 3 (1 introduced, 2 inherited)
forbidden_wording_hits: 0
could_not_verify: ["'293 types' exactly (grep of public type declarations in src/main = 294)", "Mermaid diagram wording against runtime behaviour (diagram has no inputs/outputs)"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Opening / Key Capabilities", summary: "the opening says the library reads and writes 22 formats (AMF, ASE, DXF, HTML5, IFC, Maya, PCD, PDF, RVM, USD, USDZ, VRML, U3D ...) because FileFormat constants exist; Scene.Save fails for 14 of them (ArgumentException Unsupported file format) and the live README's own Scope says PDF/Draco are not functional (that bullet is dropped). A format-support claim must rest on an implemented reader/writer (IOService dispatch, a passing round trip), never on a constant or an option type"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "At a Glance", summary: "plan.json at_a_glance input_format_ids and output_format_ids are empty, so the diagram drops the live README's Starting Points and Outputs subgraphs (live: 3 inputs, 4 outputs); the diagram now says only 'product -> eight capabilities'"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Development and Testing / API Reference", summary: "kept inherited fragments printed in the wrong section without their lead-in: Development and Testing holds the Dependencies bullet 'Targets netcoreapp3.1 ... runs on any compatible runtime' (also in Dependencies and twice more in prose), the converter paragraph that belongs to Installation, and a code block `dotnet build src/converter/Converter.csproj` whose lead-in ('The console converter tool builds separately ...') was dropped; the API Reference ends with the live API-intro paragraph (hard-wrapped, repeats the Scene paragraph above) under '### Animation'"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "five of nine live limitations dropped: PDF and Draco have no reader/writer, Usd/A3dw/Jt option types have no codec, Microsoft3MF build-instruction metadata, RvmFormat.LoadAttributes; the remaining list restates the same facts as the opening differently"}
  - {id: F5, kind: data_change, severity: MINOR, section: "Scope and Limitations", summary: "inherited and now printed as verified: 'NurbsSurface.ToMesh ... throw NotImplementedException' is false (ToMesh returns a flat placeholder grid, NurbsSurface.cs L45-85); needs an upstream README/source fix, not a pipeline fix"}
  - {id: F6, kind: redraw, severity: MINOR, section: "Quick Start / Documentation & Resources", summary: "assurance wording for the visitor: 'using Aspose.3D.FOSS version 26.1.0.' tacked onto both Quick Start lead-ins, 'The verified public surface has 293 types.', 'covers all 293 verified public types'"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Opening", evidence: "probe project (clone + dotnet 10.0.401): new Scene().Save('x.<ext>') for 22 extensions: OK only for .obj .stl .fbx .gltf .dae .3mf .ply .3ds; .pdf .u3d .usd .usdz .wrl .dxf .ifc .ma .pcd .amf .html .rvm .ase .drc throw ArgumentException 'Unsupported file format'; IOService.cs CreateImporter/CreateExporter switch lists exactly those 8", summary: "INTRODUCED false claim: opening says the library reads and writes AMF, ASE, DXF, HTML5, IFC, Maya ASCII/Binary, PCD, PDF, RVM, USD, USDZ, VRML, U3D"}
  - {id: B2, category: false_claim, section: "Key Capabilities / Scope", evidence: "same probe: .u3d .amf .html .rvm fail; NurbsSurface.cs ToMesh returns a mesh", summary: "INHERITED false claims carried (U3D/AMF/HTML5/RVM conversion; NurbsSurface.ToMesh throws)"}
  - {id: B3, category: dropped_live_content, section: "At a Glance", evidence: "cand L25-49 vs live L30-62; plan.json at_a_glance.input_format_ids == []", summary: "Starting Points and Outputs gone"}
  - {id: B4, category: dropped_live_content, section: "Scope and Limitations", evidence: "live L228-246 vs cand L569-580; retention.py lost sentences 27 of 45", summary: "the live statement that PDF/Draco are not functional, three more limitations, and the Development Dependencies versions (xunit 2.9.2, runner 2.8.2, coverlet 6.0.2, Test.Sdk 17.12.0) are gone"}
  - {id: B5, category: dangling_prose, section: "Development and Testing", evidence: "cand L584-603", summary: "orphan bullet, orphan converter code block with no lead-in, Dependencies content repeated"}
---

# 1 Bundle facts
READY_FOR_PROPOSAL, revision == live head (52b0f00e), README sha256 == manifest, no-op VERIFIED (25 provider calls in run 1, exit 0 on the fresh-process rerun), validation BC-01..BC-14 12 PASS 0 FAIL (1 pending before the proof), review ACCEPT (as returned ACCEPT, 0 findings, read 1, second read not triggered), 0 advisories. Examples: 6 EXECUTED, 1 FAILED (receipt 3, the live "Enumerate a Scene's Node Hierarchy" example: `FromFile("input.fbx", FileFormat.FBX7400Binary)` does not compile, the overload needs a CancellationToken). The candidate dropped that live example, which is correct (a genuine upstream README defect).

# 2 Live comparison
ADDS (true): a source-checkout install route (dotnet build) and the `Vector3` using (Aspose.ThreeD.Utilities, correct), 16 test files, a .NET badge row, the dev-dependency kinds, Documentation links kept, an Enterprise Edition paragraph in the contract shape.
ADDS (false): the opening's 22-format list (B1), the 'Aspose.3D.FOSS version 26.1.0' wording.
DROPS (valuable): live Starting Points/Outputs, five limitations (PDF/Draco etc.), Development Dependencies versions, the AGENTS.md documentation link (kept as prose), the live opening sentence (free, open-source, MIT-licensed, no external engine, pure managed code), the "Enumerate hierarchy" example (broken, drop is right), the "Save to COLLADA through a stream" lead-in sentences.
CHANGES: Key Capabilities are now bold-led bullets with the same content (equal); the two-column diagram is horizontal (better geometry, less content); API tables 292 of 296 live row keys present (equal), plus a Detailed Member Reference for Scene and FileFormat (better).
NET: mixed; worse on the opening claim and Scope, better on the install/dependency structure and the broken example.

# 3 Claim checks
| # | Claim (README line) | How checked | Result |
|---|---|---|---|
| 1 | NuGet package Aspose.3D.FOSS version 26.1.0 (L64) | api.nuget.org flatcontainer index: ["26.1.0"] | PASS |
| 2 | targets netcoreapp3.1, net6.0, net8.0, net10.0 (L7, L86) | csproj L22 TargetFrameworks net10.0;net8.0;net6.0;netcoreapp3.1 | PASS |
| 3 | no required third-party packages (L82) | no PackageReference in Aspose.ThreeD.csproj | PASS |
| 4 | 16 test files under src/test/ (L586) | find src/test -name '*.cs' = 16 | PASS |
| 5 | converter package id Aspose.3D.Converter, not published to NuGet (L588-590) | Converter.csproj PackageId; NuGet 404 | PASS |
| 6 | opening: reads and writes AMF, ASE, DXF, HTML5, IFC, Maya ASCII, Maya Binary, PCD, PDF, RVM, USD, USDZ, VRML, Universal 3D (L7) | probe: Scene.Save to each extension; IOService dispatch | FAIL (introduced; 14 of 22 listed formats cannot be saved, PDF/Draco are documented as not functional by the live README) |
| 7 | Key Capabilities: FBX, glTF, OBJ, STL, COLLADA, Universal 3D with full round-trip, plus 3MF, RVM, AMF, HTML5 export (L56) | probe | FAIL (inherited: .u3d .rvm .amf .html fail; live L82-85 same) |
| 8 | Scope: NurbsSurface.ToMesh throws NotImplementedException (L576) | NurbsSurface.cs L45-85 returns a mesh | FAIL (inherited, MISLEADING: it returns a flat placeholder grid) |
| 9 | Scope: Scene.Render, RenderFactory, IRenderTarget throw NotImplementedException (L573) | Scene.cs L457-500 throws; Render/RenderFactory.cs | PASS |
| 10 | Scope: FileFormat.PLY non-dispatched PlyFormat throws; Scene.Open/Save work (L574) | PlyFormat.cs 8 throws; probe .ply SAVE OK | PASS |
| 11 | Scope: NurbsCurve.Evaluate/EvaluateAt throw (L576) | NurbsCurve.cs L107-118 | PASS |
| 12 | Scope: Text watermarking not functional (L577) | Utilities/Watermark.cs NotImplemented | PASS |
| 13 | Quick Start 1 and 2 compile and run (L92-117) | receipts 1 and 2 EXECUTED (SDK 10.0.401); Vector3 is in Aspose.ThreeD.Utilities (using present) | PASS |
| 14 | source-checkout build and test paths (L72-76, L595-603) | csproj paths exist in the clone | PASS |
| 15 | License MIT (L607) | LICENSE | PASS |
| 16 | 29 links (27 unique) | mech.py --net: none non-200; duplicate targets #api-reference, LICENSE | PASS |
| 17 | 293 types (L188, L564) | grep of `public (class|struct|enum|interface)` = 294 | COULD_NOT_VERIFY exactly |

# 4 Mechanical and wording
mech.py: 12 sections in contract order, one mermaid fence, nothing else in At a Glance, no fence without a language, no forum link, Enterprise Edition anchor shape ok, no forbidden edition wording ("backed by" in the PLY bullet is not a platform bridge). Mermaid: `flowchart LR`; rendered with the repository's Edge/mermaid check: horizontal, zero clipped fonts (live: vertical, 4 clipped fonts). Assurance wording: "verified public surface", "verified public types", "using Aspose.3D.FOSS version 26.1.0".

# 5 Omitted information in the clone
docs/foss-net-progress.md and release-26.2.0.md (linked), AGENTS.md (linked via prose), test project dependencies (dropped). No CHANGELOG/SECURITY.

# 6 Drafted upstream issues (TEXT ONLY)
1. README lists U3D, RVM, AMF and HTML5 as supported output formats, but `Scene.Save` raises `ArgumentException: Unsupported file format` for each (IOService.CreateExporter supports 8 formats: OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS). Severity medium. Reproduce: `new Scene().Save("x.u3d")` on net10.0.
2. README states `NurbsSurface.ToMesh` throws NotImplementedException; it returns a flat placeholder grid and the comment says "a real NURBS implementation would evaluate the basis functions". Severity low.
3. README example `Scene.FromFile("input.fbx", FileFormat.FBX7400Binary)` does not compile: CS1503, the overload is `FromFile(string, FileFormat, CancellationToken)`. Severity low.

# 7 Verdict
FIX_REQUIRED, MAJOR, confidence high. The facts the pipeline checks (version, frameworks, test count, links, license, commands) are right and the structure is tidy, but the visitor-facing opening makes a new false claim about 14 formats and the live README's most important limitation (PDF/Draco not functional) is gone, the diagram lost its inputs and outputs, and the Development and Testing section prints orphan fragments. A reseal reproduces all of F1-F4 (code changes): the format claim rests on constants, the empty `input_format_ids` plan is accepted, and kept units are printed in the wrong section. Not AUTHORIZABLE.
