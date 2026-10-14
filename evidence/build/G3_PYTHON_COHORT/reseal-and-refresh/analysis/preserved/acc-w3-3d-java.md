authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-Java
bundle_hash: 8e8074fb68ac74372eae1b9d467a190fe6023229a6936baa9a9173d633da0a62
readme_sha256: 79dabcd8454b64f5e8d755669469065868c9c876ec4ca7548d89d03c1438acac
source_revision: 3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3
live_head: 3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3
reviewed_at: 2026-10-11T05:41:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 20
claims_failed: 4
forbidden_wording_hits: 0
could_not_verify: ["Quick Start / Additional Example compile receipts taken from examples.json (no JDK on reviewer machine; javap/javac absent)", "OBJ import 'working parser in GitHub source': confirmed ObjReader exists in FileFormat.java but not executed"]
fixes:
  - {id: F1, kind: redraw, severity: MINOR, section: "Opening", summary: "remove invented audience ('CAD viewers, simulation tools, 3D printing workflows'), 'without requiring a full commercial suite', and 'as well as other 3D formats' (contradicts Scope: STL is the only functional format)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations / Documentation & Resources / badges / License", summary: "VERIFIED_PRESERVE dispositions are accepted although not all of the unit renders: 4 repository doc links, FILE_FORMATS.md pointer, 4 scope bullets (PbrSpecularMaterial, NurbsCurve sampling in Scope, Licensing/crypto/ZIP excluded, FILE_FORMATS caveat), Maven Central badge, clean-room acknowledgement are lost with BC-05/BC-08 PASS"}
  - {id: F3, kind: redraw, severity: MINOR, section: "API Reference", summary: "Detailed Member Reference: '### threed' says 'The `com.aspose.threed` class serves as the root namespace' (a package is not a class) and repeats the API Reference lead paragraph verbatim incl. 'listed below by module' (nothing is listed by module); interfaces/structs now in one table headed 'Class'"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Development and Testing", summary: "release workflow sentence and link stated twice; AGENTS.md/TODO.md mentioned twice"}
  - {id: F5, kind: data_change, severity: MINOR, section: "Scope and Limitations", summary: "'higher-tier offering' and 'simply swap to the commercial package' are promotional edition wording; use Enterprise Edition only"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Opening", evidence: "grep -rn -i 'cad viewer|simulation|3d printing|printing' --include=*.md in clone: no hit; no fact supports an audience", summary: "INTRODUCED: invented audience sentence"}
  - {id: B2, category: false_claim, section: "Opening", evidence: "Scope L524: 'The only fully functional format in the published 26.5.0 package is STL'; published jar FileFormat$ObjLoader/GltfLoader/FbxLoader are 790-793 bytes (stubs) vs StlLoader 6046", summary: "INTRODUCED: 'supports reading and writing STL files, as well as other 3D formats' is misleading and contradicts the README's own Scope section"}
  - {id: B3, category: dangling_prose, section: "API Reference", evidence: "README.md L478-485", summary: "INTRODUCED: package called a class; duplicated lead paragraph; 'listed below by module' false"}
  - {id: B4, category: dropped_live_content, section: "Documentation & Resources", evidence: "diff live vs candidate: PUBLISHING.md, docs/api-diff-26.1.0.md, docs/directory-structures.md, docs/foss-java-progress.md, FILE_FORMATS.md all exist in clone (ls) and are linked live", summary: "five verified repository doc links dropped"}
  - {id: B5, category: dropped_live_content, section: "Scope and Limitations", evidence: "PbrSpecularMaterial.java has 18 UnsupportedOperationException; CryptoUtils/License throw; live Scope L592-593", summary: "dropped limitations that still apply: PbrSpecularMaterial accessors unimplemented, licensing/crypto/ZIP file-system excluded; API table still lists these types without caveat"}
  - {id: B6, category: dropped_live_content, section: "badges / Installation / License", evidence: "diff live vs candidate", summary: "drops Maven Central version badge, Gradle Kotlin DSL snippet, 'other build tools' note, 'also available for Python, .NET and TypeScript', clean-room acknowledgement (deferred)"}
  - {id: B7, category: other, section: "Scope and Limitations", evidence: "README.md L527, L531", summary: "'higher-tier offering' / 'swap to the commercial package' are non-canonical edition wording (borderline forbidden)"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision equals live head 3d2ed6be...; README sha256 equals manifest (not corrupt).
- review.json: ACCEPT / verdict_as_returned ACCEPT; findings []; second_reader triggered (ADVISORY_DEFERRAL), read 2, corroborated [].
- validation.json: BC-01..BC-12, BC-14 PASS. Advisories (5), my rulings:
  - 014/016/018 code blocks (Maven XML, Gradle Kotlin, Gradle Groovy) deferred NOT_CARRIED_BY_NAMED_SECTION: candidate does carry Maven XML and Groovy but not Kotlin DSL; the Kotlin snippet loss is real but minor (B6).
  - 044 (node transform example) deferred UNVERIFIED_EXAMPLE: example #7 uses `scene` unbound; dropping is correct.
  - 084 (License clean-room acknowledgement) deferred OWN_LICENSE_COVERED_BY_LICENSE_SECTION: the deferral reason names only licence identity; the acknowledgement is a distinct, true statement (live L633-634) and is lost (B6, minor).
- Dispositions of note: 070.list VERIFIED_PRESERVE says "All links in the list are verified" but 5 of them are absent from the candidate; 072.list VERIFIED_PRESERVE lists PbrSpecularMaterial yet candidate Scope has no such bullet. A rationale string contains CJK text ("Scene渲染未...") - model language leakage in an internal artifact (not public).
- Examples: #1-#6 EXECUTED (javac 21.0.11), #7 NOT_VERIFIED (dropped).

# 2 Live comparison

ADDS: junit version in Dev Dependencies (TRUE, pom property 5.10.0); `mvn dependency:get` command (TRUE syntax; artifact exists); "11 test files" (TRUE); "266 types" twice (TRUE); static Java badge value `java-21%2B` (TRUE); audience sentence (FALSE/unsupported); "other 3D formats" (MISLEADING); API table descriptions re-authored from signatures (acceptable, some generic fill like "Options for JPEG2000 loading" for `JtLoadOptions`, inherited from source javadoc).
DROPS: Maven Central badge; Kotlin DSL snippet and other-tools note; Python/.NET/TypeScript family sentence; five repo doc links (PUBLISHING.md, api-diff, directory-structures, progress notes) and the FILE_FORMATS.md pointer; limitations (PbrSpecularMaterial, licensing/crypto/ZIP exclusions, FILE_FORMATS summary caveat); "NurbsCurve sampling not implemented" in Scope (kept in Key Capabilities); interface/struct sub-tables; At a Glance Starting Points/Outputs; clean-room acknowledgement; "Project status: work-in-progress port" bold line (text kept in Dev paragraph).
CHANGES: opening shorter but less accurate; Key Capabilities with bold titles equal; Quick Start equal; Scope bullets: Scope intro sentence added (fine); Enterprise paragraph gains "simply swap to the commercial package" (kept from live). API Reference: live had per-area curated detail (Scene Graph, Geometry, Materials, Format I/O, Math, Exceptions); candidate has six one-line `- Scene/Node/Mesh/NurbsCurve/PbrMaterial/FileFormat` bullets: worse.
NET: worse.

# 3 Claim checks

| # | Claim (README line) | How checked | Result |
|---|---|---|---|
| 1 | Maven Central `org.aspose:aspose-3d-foss` 26.5.0 published (L57) | maven-metadata.xml versions=[26.5.0]; .../26.5.0/aspose-3d-foss-26.5.0.pom HTTP 200 | PASS |
| 2 | version = pom version | pom.xml `<version>26.5.0</version>` | PASS |
| 3 | `mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0` (L60) | coordinates exist (above) | PASS |
| 4 | Maven XML / Gradle Groovy coordinates (L66-77) | same coordinates | PASS |
| 5 | Java 21 (L87, badge) | pom maven.compiler.source/target = 21 | PASS |
| 6 | No required deps; dev dep junit-jupiter 5.10.0 (L83, L91) | pom: single dependency junit-jupiter, scope test, junit.version 5.10.0 | PASS |
| 7 | 266 public types (L193,195,517) | public class/interface/enum names in src/main (nested included) = 266; README table rows = 266 | PASS |
| 8 | 11 test files (L537) | find src/test -name '*.java' = 11 | PASS |
| 9 | Library "supports reading and writing STL files, as well as other 3D formats" (L7) | Scope L524 + published jar class sizes (ObjLoader 790 B, GltfLoader 793, FbxLoader 790 vs StlLoader 6046) | FAIL (introduced, MISLEADING) |
| 10 | "used by Java developers building ... CAD viewers, simulation tools, 3D printing workflows" (L7) | grep README/docs/TODO | FAIL (introduced, unsupported) |
| 11 | Box, Cylinder, Sphere, Dish toMesh() implemented (L50, L528) | source: implemented; Torus.java L94 and Pyramid.java L79 throw UnsupportedOperationException | PASS |
| 12 | PbrMaterial channels albedo/metallic/roughness/occlusion/emissive (L51) | PbrMaterial.java getters/setters | PASS |
| 13 | NurbsCurve sampling not implemented (L52) | NurbsCurve.java has 2 throws | PASS |
| 14 | Scene rendering not implemented (L529) | Scene.java L435-440 throws UnsupportedOperationException | PASS |
| 15 | OBJ import stub in published artifact (L525) | jar entry FileFormat$ObjLoader.class 790 bytes vs source ObjReader in FileFormat.java L513 | PASS |
| 16 | `Stream.wrap(InputStream)`, `FileFormat.getFormatByExtension(".stl")` (L184-185) | Stream.java L46; FileFormat.java L186 | PASS |
| 17 | `FileFormat.detect(Stream, String)` automatic detection from stream (L49) | FileFormat.java L257 | PASS |
| 18 | MIT licence (L553) | LICENSE "MIT License" | PASS |
| 19 | maven-central-release.yml exists (L537,L549) | .github/workflows/maven-central-release.yml | PASS |
| 20 | links (30) | mech.py --net: no non-200, no missing relative targets | PASS |

# 4 Mechanical and wording

- mech.py: 1 H1; 11 H2 in order; all required sections; one mermaid fence only; fences have languages; 1 hit: "wrapper" in the `ArrayListAdapter` API row (a class description, not an implementation bridge: acceptable). No forum links, 0 edition-name hits except one correct Enterprise Edition anchor.
- Wording to judge: "without requiring a full commercial suite" (L7) is close to the forbidden "full version/commercial edition" family: report as borderline; "higher-tier offering" (L527) and "simply swap to the commercial package" (L531): edition wording not in canonical form (B7).
- Duplicates: release workflow link/statement twice (L537, L549 -> F4); `#api-reference`, `#scope-and-limitations`, `LICENSE` anchors repeated (minor).
- Garbled: "### threed ... The `com.aspose.threed` class" (B3). Enumerations table includes `BindPoint` (a class). `Interface` types listed under "Class".
- Descriptions with trailing " / " artifacts: `BonePose`, `BoundingBox`, `BoundingBox2D`, `Frustum`, `InitializationException`, `BooleanOperation`, `Rect`, `RotationMode` (javadoc `<br/>` residue).
- Stray/odd: `Stream` row "Created by lexchou on 12/14/2016." (source javadoc authored comment leaking into a public API table; live had it too).

# 5 Omitted information in the clone

- FILE_FORMATS.md (format-by-format status; the live README links it): valuable; its absence is a defect because live carries it.
- PUBLISHING.md, docs/api-diff-26.1.0.md, docs/directory-structures.md, docs/foss-java-progress.md: live carries them -> defect (B4).
- TODO.md named but not linked (text only).
- Tests as usage documentation (StlFormatTest, GltfFormatTest): marginal.
- No py.typed analogue; no CI test workflow (only release workflow).

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: published Maven artifact 26.5.0 ships stub OBJ/glTF/FBX loaders while the source tree has an OBJ reader. Body: `FileFormat$ObjLoader.class` in aspose-3d-foss-26.5.0.jar is 790 bytes (StlLoader 6046) while src FileFormat.java L513 defines `ObjReader`; the README itself documents this. Repro: download https://repo1.maven.org/maven2/org/aspose/aspose-3d-foss/26.5.0/aspose-3d-foss-26.5.0.jar and list class sizes. Fix: cut a release from current main. Severity: medium. (Possible, byte-level behaviour not executed: no JDK here.)
2. Title: `Torus.toMesh()` and `Pyramid.toMesh()` throw UnsupportedOperationException. Where: Torus.java L94-96, Pyramid.java L79-81. Severity: low (documented in the README Scope).
3. Possible, unreproduced: FILE_FORMATS.md summary table versus later sections disagree (live README warns about it).

# 7 Verdict and reasons

DO_NOT_PROPOSE, minor_major MAJOR. Three or more independent introduced FAIL/MISLEADING results (B1 invented audience, B2 "other 3D formats", B3 package-called-class plus duplicated paragraph) plus dropped verified live content (B4, B5, B6) mean the PR would make the README less accurate and less complete than the live one. The opening is the only place where the candidate is better than live on forbidden wording (live names "commercial On-Premise edition" in prose), but it replaced that with invented marketing.

Fixes: F1 redraw MINOR; F2 code_change MAJOR (partial-render of a VERIFIED_PRESERVE unit is not detected); F3-F5 minor. Reconsider after: the opening is grounded to facts only (audience must come from evidence or be omitted), docs links and the four verified limitations are restored, and the validator fails a VERIFIED_PRESERVE whose items are not all rendered.

Universal defects for routing: (U1) BC-05/BC-08 accept VERIFIED_PRESERVE units that are only partially rendered (documentation list, scope list); (U2) the opening author invents an audience/use-case sentence not backed by any fact and "without requiring ..." framing; (U3) a general claim in the opening ("other 3D formats") is not reconciled against the README's own Scope limitation (cross-section contradiction check absent); (U4) Detailed Member Reference intro paragraph duplicates the API Reference lead and misdescribes a package as a class; (U5) source-javadoc residue ("/ ", "Created by lexchou ...") emitted verbatim into API tables; (U6) disposition rationale text can leak other-language characters.

Confidence high (all blocking items reproduced against clone and the published jar). Could not verify: see front matter.

# 8 Retention of live content (added in the wave-3 completion pass)

Method (retention.py, read-only): the live README and the candidate are split into sentences (prose outside fences, tables and headings), list items, unique link targets (an absolute repo-file link equals the same relative link) and fenced code blocks. "Verbatim" = the whitespace-collapsed live unit appears unchanged in the candidate; "reworded" = best similarity >= 0.80 to a candidate unit of the same kind; "lost" = below 0.80. Table rows are reported separately (API tables are rewritten by the pipeline, so row text is a weaker signal than row keys).

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 39 | 15 | 38% | 3 | 21 |
| list items | 54 | 20 | 37% | 6 | 28 |
| links (unique targets) | 35 | 24 | 69% | 0 | 11 |
| code blocks | 12 | 9 | 75% | 1 | 2 |
| CORE (four kinds) | 140 | 68 | 49% | 10 | 62 (44%) |
| table rows (supplemental) | 269 | 146 | 54% | 13 | 110 (268 of 269 row keys kept) |

Lost: the 'About Aspose.3D FOSS' clean-room paragraph, the product-family sentence and the commercial On-Premise sentence (the last two are forbidden wording in a candidate, so their loss is justified); the Gradle lead-ins, the Gradle Kotlin DSL block (the script counts it as 'reworded' because the retained Groovy block is more than 80% similar; it is in fact dropped) and the sentence on SBT/Ivy/Leiningen coordinates; the Maven Central artifact id sentence (`org.aspose:aspose-3d-foss`), the Maven Central badge and the Java 21 badge; 'Requires Java 21 or later per pom.xml' and the 'no native libraries beyond the JVM' item; the JUnit item; seven API-feature bullets (`Entity/SceneObject/A3DObject`, `Group`, `BoundingBox`, `Material`, `TextureData`, `Vector2/3/4`, `Matrix4/Quaternion/Transform`, exceptions); five repo-doc links (`FILE_FORMATS.md`, `PUBLISHING.md`, `docs/api-diff-26.1.0.md`, `docs/directory-structures.md`, `docs/foss-java-progress.md`); the limitation sentences (OBJ importer ships an older state in the published artifact, formats failing silently, `NurbsCurve`, `PbrSpecularMaterial`, licensing exclusions); the 'Development Notes' details block and the Acknowledgments sentence; a Java node-transform example and the mermaid diagram (rewritten). Table: 110 of 269 rows differ by more than 20%, 268 of 269 row keys kept.
