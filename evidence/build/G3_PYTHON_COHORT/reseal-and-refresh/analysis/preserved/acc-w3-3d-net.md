authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-.NET
bundle_hash: 77f546fa27299328b99432a4f07d4c0d3e9ff33c6e4029aa1ab96dc1aa3c8a52
readme_sha256: 5e57921e8981d7b429affe6d78d067fada658f0d6ebc4f4d15f306a9ab4a1514
source_revision: 52b0f00ebf28a0b4173921725ff170685ec2c502
live_head: 52b0f00ebf28a0b4173921725ff170685ec2c502
reviewed_at: 2026-10-11T05:40:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: mixed
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 24
claims_failed: 6
forbidden_wording_hits: 0
could_not_verify: ["'full round-trip fidelity' (inherited superlative; no fidelity test is runnable: 48 of 53 test failures are missing fixtures)", "Quick Start/Additional Example compile receipts were taken from examples.json, not re-run"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Installation", summary: "source-checkout command `dotnet build` at repo root fails (MSB1003); BC-02 accepted a build command that cannot succeed from the stated cwd"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "'18 test files' counts test.log and the .csproj; real count is 16 .cs files"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "doc-comment descriptions with <see cref> stripped leave holes ('The  contains', 'Base class for  and'); 14+ rows garbled; live had these repaired"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Key Capabilities / Scope and Limitations", summary: "format capability claims taken from FileFormat constants, not the importer/exporter registry (U3D, RVM, AMF, HTML5 have none); 'throws NotImplementedException' claims not verified per member (NurbsSurface.ToMesh returns a placeholder grid; RenderFactory returns null)"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Scope and Limitations / Dependencies / Installation / At a Glance", summary: "restore dropped live content: PLY-via-Scene note, PDF/Draco/USD/A3DW/JT/3MF-metadata limitations, Development Dependencies, converter-not-published, 3DS format, At a Glance Starting Points/Outputs"}
  - {id: F6, kind: redraw, severity: MINOR, section: "API Reference", summary: "heading levels inverted (#### Detailed Member Reference then ###), Scene member list lists constructors of base classes (A3DObject, SceneObject) as Scene members, 'Defined as `FileFormat`.' bullets are empty; interfaces/structs in a table headed 'Class'"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Installation", evidence: "git clone --depth 1 ... ; cd clone; dotnet build -> 'MSBUILD : error MSB1003: Specify a project or solution file' (no .sln/.csproj at root)", summary: "INTRODUCED: documented source-build command fails"}
  - {id: B2, category: false_claim, section: "Development and Testing", evidence: "find src/test -type f (excluding bin/obj) = 18 incl. Aspose.ThreeD.Tests.csproj + test.log; 16 .cs, all 16 contain [Fact]/[Theory]", summary: "INTRODUCED: 'The suite covers 18 test files' is misleading/false"}
  - {id: B3, category: dangling_prose, section: "API Reference", evidence: "README.md L203,206,207,214,215,233,234,320,321,323,335,351,371,392 (e.g. '`Deformer` | Base class for  and |')", summary: "INTRODUCED: garbled descriptions with missing words; live README has proper text"}
  - {id: B4, category: false_claim, section: "Key Capabilities", evidence: "src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/IOService.cs CreateImporter/CreateExporter handle only OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS; FileFormat._formats registers the same 8; Scene.Open/Save for U3D/RVM/AMF/HTML5 -> NotSupportedException/ArgumentException", summary: "INHERITED: 'reading and writing ... Universal 3D (U3D)' and 'plus ... AVEVA PDMS RVM models, AMF, and an HTML5 ... export' are false"}
  - {id: B5, category: false_claim, section: "Scope and Limitations", evidence: "NurbsSurface.cs ToMesh() returns a flat placeholder grid and does not throw; RenderFactory.cs methods return null and do not throw", summary: "INHERITED: 'NurbsSurface.ToMesh throw NotImplementedException' and 'RenderFactory ... all throw NotImplementedException' are false"}
  - {id: B6, category: dropped_live_content, section: "Scope and Limitations", evidence: "diff live vs candidate", summary: "candidate drops verified live limitations: PdfFormat/DracoFormat non-functional, USD/A3DW/JT option types unwired, 3MF build-metadata not implemented, PLY works via Scene API but PlyFormat.Encode/Decode throw; Enterprise paragraph no longer names PDF/Draco"}
  - {id: B7, category: dropped_live_content, section: "Dependencies / Installation", evidence: "diff live vs candidate", summary: "drops Development Dependencies list (xunit 2.9.2, runner 2.8.2, Test.Sdk 17.12.0, coverlet 6.0.2), and 'converter is not published to NuGet' statement"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision 52b0f00e... equals live head. README sha256 equals `manifest.files["README.md"].sha256` (OK, bundle not corrupt).
- review.json: verdict ACCEPT, verdict_as_returned ACCEPT, findings [] (nothing demoted or waived). second_reader triggered (ADVISORY_DEFERRAL), corroborated [].
- validation.json: BC-01..BC-12 PASS (BC-14 pending=1 per row), advisories:
  - inherited_unit:014 (target frameworks + converter paragraph) deferred NOT_CARRIED_BY_NAMED_SECTION. Ruling: TRUE loss. The live paragraph "converter ... not published to NuGet" is valuable and verified (Converter.csproj exists, builds). Not carried -> counts as dropped live content (B7).
  - inherited_unit:031 (node-hierarchy lead-in) deferred with its code block. Ruling: correct. examples.json #3 FAILED to compile (`Scene.FromFile("input.fbx", FileFormat.FBX7400Binary)` -> CS1503); the live README example is wrong, dropping it is an improvement (inherited defect fixed).
- acceptance_profile criterion C01 NOT_MET (Aspose destination before explanation).
- dispositions: 33 SUPERSEDE_REDUNDANT, 26 VERIFIED_PRESERVE, 3 OMIT_UNSUPPORTED, 3 NON_CONTENT, 2 DEFER_UNRESOLVED, 2 VERIFIED_MOVE, 1 VERIFIED_REWRITE. Note unit 021 (development dependencies list) was VERIFIED_MOVE to development_testing but the candidate's Development section does not carry the list (silently lost: BC-05 passed anyway).

# 2 Live comparison

ADDS (all verified TRUE unless noted):
- Static `.NET` badge (netcoreapp3.1|net6.0|net8.0|net10.0): TRUE (csproj TargetFrameworks).
- Install for source checkout (`git clone; dotnet build`): FALSE as written (B1).
- "The verified public surface has 293 types": TRUE (293 unique public type names counted in src/main).
- "18 test files": FALSE/MISLEADING (B2).
- Per-capability bold titles in Key Capabilities: fine. Opening rewritten, shorter, drops "pure managed code, no native dependencies" but says "no external dependencies" (TRUE).
- API table descriptions regenerated from doc comments: includes garbled rows (B3).
- "Detailed Member Reference" Scene/FileFormat member bullets: low-value; Scene list includes base-class constructors; FileFormat list is 60 bullets of "Defined as `FileFormat`." (F6).

DROPS (live content missing from the candidate):
- Scope bullets: PLY note, PdfFormat/DracoFormat, USD/A3DW/JT, 3MF build metadata (valuable, verified: B6).
- Enterprise paragraph names PDF/Draco (live) -> candidate generic (minor).
- Development Dependencies section and versions (B7); converter not published statement.
- At a Glance: Starting Points and Outputs subgraphs (live showed formats in/out; candidate shows capabilities only) - minor.
- Maven-style "targets in Release builds" explanation; interface/struct sub-tables (merged into one table headed "Class" - worse).
- 3DS format (Discreet3ds importer/exporter exist and are tested) was never in live either; omission from the candidate's format list is a completeness gap.
- Dropped and justified: broken "Enumerate a Scene's Node Hierarchy" example (does not compile).

CHANGES:
- Install: live `dotnet add package Aspose.3D.FOSS --version 26.1.0` -> candidate unversioned plus text version: equal.
- Documentation & Resources: equal links, wordier; "Found a bug" bullet kept.
- Opening: live richer (says free, MIT, no engine, pure managed). Candidate fine but plainer: equal/slightly worse.
- API tables: worse (garbled descriptions; mixed kinds under "Class").

NET vs live: mixed leaning worse (adds one false install command and a false count, regresses the API table, drops verified limitations).

# 3 Claim checks

| # | Claim (README line) | How checked | Result |
|---|---|---|---|
| 1 | Package `Aspose.3D.FOSS` version 26.1.0 published (L61) | curl https://api.nuget.org/v3-flatcontainer/aspose.3d.foss/index.json -> ["26.1.0"] | PASS |
| 2 | version = manifest version (L61/L87) | csproj `<Version>26.1.0</Version>` | PASS |
| 3 | `dotnet add package Aspose.3D.FOSS` (L64) | NuGet exists, single version 26.1.0 | PASS |
| 4 | `dotnet build` in clone root (L69-73) | ran in clone: MSB1003, no project/sln at root | FAIL (introduced) |
| 5 | TFMs netcoreapp3.1;net6.0;net8.0;net10.0 (L83, badge) | csproj TargetFrameworks | PASS |
| 6 | no required package deps (L79) | `grep -c PackageReference` main csproj = 0 | PASS |
| 7 | 293 public types (L184, L618) | grep public class/interface/enum/struct names, sort -u = 293 | PASS |
| 8 | 18 test files (L641) | find src/test (no bin/obj) = 18 files = 16 .cs + csproj + test.log | FAIL (introduced) |
| 9 | Scene.Render throws NotImplementedException (L628) | Scene.cs L455-505 | PASS |
| 10 | RenderFactory throws NotImplementedException (L628) | RenderFactory.cs virtual methods `return null;`, no throw | FAIL (inherited) |
| 11 | NurbsCurve.EvaluateAt throws (L630) | NurbsCurve.cs L109,117 | PASS |
| 12 | NurbsSurface.ToMesh throws (L630) | NurbsSurface.cs L45-90 returns a flat grid Mesh | FAIL (inherited) |
| 13 | reads+writes U3D; RVM, AMF, HTML5 export (L53) | IOService.cs + FileFormat._formats: no importer/exporter for them | FAIL (inherited) |
| 14 | `RvmFormat.LoadAttributes` not implemented (L633) | RvmFormat.cs L28,36 throws | PASS |
| 15 | PolygonModifier/TriMesh throw NotImplementedException (L629) | grep: 20 and 26 occurrences | PASS |
| 16 | Text watermarking not functional (L631) | Watermark.cs throws NotImplementedException | PASS |
| 17 | ObjLoadOptions.FlipCoordinateSystem/NormalizeNormal (L127-128) | FormatOptions.cs L26,42 | PASS |
| 18 | PbrMaterial.FromMaterial (L143) | PbrMaterial.cs L154 | PASS |
| 19 | `scene.Open("unknown.xyz")` -> ArgumentException (L172) | FileFormat.GetFormatByExtension throws ArgumentException; .xyz not in _formats | PASS |
| 20 | `CreateChildNode("Box", new Box(2,2,2), material)`, FBX7400Binary (L100-103) | Node.cs L229; FileFormat constants | PASS |
| 21 | MIT licence (L660) | LICENSE "MIT License", 2024-2026 Aspose | PASS |
| 22 | xunit + coverlet used (L639) | test csproj PackageReference xunit 2.9.2, coverlet 6.0.2 | PASS |
| 23 | `dotnet build src/converter/Converter.csproj` (L652) | ran: 0 errors | PASS |
| 24 | Links (31) | mech.py --net: no non-200; relative targets docs/foss-net-progress.md, docs/release-26.2.0.md, AGENTS.md, LICENSE exist | PASS |
| 25 | "full round-trip fidelity" (L53) | no runnable evidence | COULD_NOT_VERIFY |

Also noted (inherited, not a failure by itself): README links "Release 26.2.0 notes" while the only published and manifest version is 26.1.0; the release note claims 26.2.0 / 2026-07-15.

# 4 Mechanical and wording

- mech.py: 1 H1, 11 H2 in correct order, all required sections present, exactly one mermaid fence in At a Glance, all fences have a language, 0 forbidden-wording hits, Enterprise Edition anchor shape OK, no forum links. Duplicate targets: `#api-reference`, `AGENTS.md` (Documentation and Development), `LICENSE` (badge and License): minor.
- Dangling/garbled: B3 (14+ rows). `Requires .NET netcoreapp3.1;net6.0;net8.0;net10.0` (raw MSBuild property) reads as a stumble. `#### Detailed Member Reference` followed by `###` headings (inverted levels). "(Scene) A3DObject: Initializes a new instance of the A3DObject class with no name." lists a base constructor as a Scene member. Non-alphabetical, un-grouped "Core API" table headed "Class" that includes interfaces/structs.
- Duplicates: AGENTS.md pointer appears three times (Documentation, Development paragraph, final line); the Scene/FileFormat description appears at the top of API Reference and again in Detailed Member Reference.
- 10-section conformance: structurally conformant; Scope and Limitations closes with the Enterprise Edition paragraph. At a Glance has no Starting Points/Outputs (acceptable per contract).

# 5 Omitted information in the clone

- 3DS (Discreet) import/export works and is tested (Test3DSImport/Export): marginal-valuable, absent from candidate and live.
- docs/release-26.2.0.md content (API categories: stub vs full) - linked only.
- Test data: the test project needs fixtures that are not in the repo (see issue 1).
- AGENTS.md describes the coding rules; linked.
- No CI workflows, no CHANGELOG; GitHub releases not queried (none needed).

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: `dotnet test` fails on a clean checkout - 53 of 183 tests fail (48 for missing fixtures). Body: In `src/test/Aspose.ThreeD.Tests/roundtrip/*.cs` tests load `./collada/cameras.dae`, `./gltf/simple_cube.gltf`, etc.; those files are not in the repository (`git ls-files | grep -i '\.dae\|\.gltf'` returns nothing). Repro: `git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET; cd ...; dotnet test src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj` (SDK 10.0.401) -> `Failed: 53, Passed: 130, Total: 183`; messages `FileNotFoundException : Test file not found: ./collada/cameras.dae`. Fix: commit the fixtures or mark the tests skipped when absent. Severity: medium.
2. Title: `NurbsSurface.ToMesh()` returns a flat placeholder grid instead of evaluating the surface (and no NotImplementedException). Where: `src/main/Aspose.ThreeD/Aspose/ThreeD/Entities/NurbsSurface.cs` L45-90 ("For now, generate a simple grid"). Repro: build any NurbsSurface and call ToMesh(); observe z=0 plane. Severity: medium (silent wrong output).
3. Title: `src/test/Aspose.ThreeD.Tests/test.log` and `src/main/Aspose.ThreeD/build.log` are committed build artifacts. Severity: low.
4. Title: no solution file at repository root, so the `dotnet build` / `dotnet test` in AGENTS.md L240-241 fail from the root. Severity: low.

# 7 Verdict and reasons

DO_NOT_PROPOSE (minor_major MAJOR). Reasons: (a) an INTRODUCED false install instruction (B1) together with other blocking findings; (b) three independent introduced defects (B1 false build command, B2 false test-file count, B3 garbled API descriptions that the live README had repaired); (c) the candidate drops verified live limitations (B6) and dev dependencies (B7) and regresses the API tables; (d) the inherited falsehoods (B4, B5) are carried over, so the candidate is not an improvement on the factual front, and a skeptical maintainer would see "reads and writes U3D/RVM/AMF/HTML5" fail on first use.

Fixes (kind/severity): F1 code_change MAJOR (build-command admission must require the command to succeed from the cwd it states; the clone has no project at root); F2 code_change MAJOR (test-file counting must count test sources, not every file under test/); F3 code_change MAJOR (strip/resolve `<see cref>` in summary extraction; a description with a hole must be rejected or regenerated); F4 code_change MAJOR (capability/limitation facts must come from the dispatch registry and per-member bodies, not from constants and file-level greps); F5/F6 redraw MINOR.

Universal defects for routing: (U1) build-command verifier accepts commands that fail from the stated working directory (also seen as "Install ... from source checkout"); (U2) count facts ("N test files") include non-test files (log, csproj); (U3) doc-comment extraction drops `<see cref>`/`<c>` text leaving double-space holes in API tables; (U4) format-support claims derive from a constants list not an importer/exporter registry; (U5) "throws NotImplementedException" claims lumped per type not per member; (U6) reconciliation silently loses VERIFIED_MOVE content (dev deps) with BC-05 still PASS; (U7) API Reference "Detailed Member Reference" emits constructors of base classes and tautological "Defined as X." bullets.

Confidence high: every blocking item reproduced against the clone at the sealed revision. Could not verify: items listed in the front matter.

# 8 Retention of live content (added in the wave-3 completion pass)

Method (retention.py, read-only): the live README and the candidate are split into sentences (prose outside fences, tables and headings), list items, unique link targets (an absolute repo-file link equals the same relative link) and fenced code blocks. "Verbatim" = the whitespace-collapsed live unit appears unchanged in the candidate; "reworded" = best similarity >= 0.80 to a candidate unit of the same kind; "lost" = below 0.80. Table rows are reported separately (API tables are rewritten by the pipeline, so row text is a weaker signal than row keys).

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 45 | 16 | 36% | 3 | 26 |
| list items | 37 | 20 | 54% | 3 | 14 |
| links (unique targets) | 27 | 26 | 96% | 0 | 1 |
| code blocks | 11 | 8 | 73% | 0 | 3 |
| CORE (four kinds) | 120 | 70 | 58% | 6 | 44 (37%) |
| table rows (supplemental) | 296 | 10 | 3% | 117 | 169 (292 of 296 row keys kept) |

Lost (not even reworded): the opening's two sentences (rewritten); the target-framework statement that includes `netcoreapp3.1` and the whole sentence that the library runs on any compatible .NET Core 3.1 or later runtime; the separate `Aspose.3D.Converter` console tool paragraph; the zero-`PackageReference` statement; the dev-dependency items (`Microsoft.NET.Test.Sdk`, `xunit`, `xunit.runner.visualstudio`, `coverlet.collector`); all six worked-example lead-ins; the PLY, PDF and Draco limitation sentences, the `UsdSaveOptions`/`A3dwSaveOptions`/`JtLoadOptions` and NURBS limitation sentences and the 3MF build-instruction limitation; the `Issues and feature requests` bullet and the weaker rewording of the other documentation bullets (Getting started, How-to/FAQ, Full API reference, progress notes, release notes, AGENTS.md); `dotnet add package --version 26.1.0` block, the FBX node-enumeration example and the mermaid diagram (rewritten). Table: 169 of 296 rows differ by more than 20% (117 are reworded with the holes reported above), 292 of 296 row keys kept.
