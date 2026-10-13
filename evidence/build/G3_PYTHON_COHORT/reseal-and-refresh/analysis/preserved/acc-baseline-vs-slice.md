authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Acceptance review: baseline (origin/main 7c5acbf7) versus slice (review-gate integrity + claim-support check, e38cabc2)

Reviewer: L-verifier2, Sonnet 5.5, a non-author of all six candidates. Protocol: acceptance-protocol.md v1.1 (read from origin/wt/lacc-acc01). Reviewed 2026-10-10.
Method common to all six: manifest and README hashes recomputed (all README hashes equal manifest.files); a fresh `git clone --depth 1` of each upstream (HEAD equals the sealed revision in every case, so none is stale); `mech.py --net` run on each README (all external links return 200; relative links resolve); registries queried read-only (PyPI, Maven Central, Go proxy); source facts checked in the clone. No GitHub write. No `present` run. No bundle or clone modified. README example snippets were not re-executed by me (no Pillow or toolchains installed; I did not install packages); I relied on `examples.json` receipts and say so under could_not_verify.

All six bundles exist and are READY_FOR_PROPOSAL with byte-identical zero-call no-op proofs. Five baseline bundles show `review_verdict_as_returned: REJECT_PRESENTATION` converted to `ACCEPT`. The slice 3D bundle shows `ACCEPT` as returned, with no conversion.

Common finding for every baseline bundle: the demoted findings were mostly TRUE. Each demotion carried a `reviewer_scope_defect` label that argued the content was fact-supported, and "supported" is not "the live README's valuable content was kept". The pipeline's own marker for the problem (`inherited_unit:...: the rewrite no longer names ...`) was left as an advisory.

---

## 1. BASELINE aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python

```
---
repository: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python
bundle_path: E:\rp\barcode-python\candidates\aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python\06eca5c01e13ed6d59a640f1cf330c1c5a57d151
code_version: baseline (origin/main 7c5acbf7)
bundle_hash: 8d70781f0b36ab805dfce491ffc098688bdd0e37c71e78b5adb458fc010b8539
readme_sha256: 1d87152a21cfe527024f33be782f45d40e540c31f1c5f608f099ca095c15b3c0
source_revision: 06eca5c01e13ed6d59a640f1cf330c1c5a57d151
live_head: 06eca5c01e13ed6d59a640f1cf330c1c5a57d151
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 14
claims_failed: 6
forbidden_wording_hits: 0
could_not_verify: ["README snippets not re-run (Pillow not installed); examples.json receipts show 6 EXECUTED", "'51 types' public-surface count not recounted"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Documentation & Resources, Development and Testing", summary: "renderer emits 'classes like AUTO, H' and 'member AUTO, member H, member data...' garble"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "same PDF limitation emitted three times; Enterprise Edition paragraph not rendered (ENTERPRISE_NO_VERIFIED_TARGET)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "table lists each type under two names (aspose_barcode_foss.X and exceptions.X/options.X); QrErrorCorrectionLevel row says 'AUTO and H'"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Development and Testing", summary: "test count must not include __init__.py/conftest.py; restore pytest commands"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Installation, Key Capabilities, At a Glance", summary: "restore py.typed, distribution/import names, Pillow-only-for-PNG, per-symbology detail, Outputs subgraph"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Development and Testing L265", evidence: "mech.py garble hits L265; cat -n README.md", summary: "'demonstrate member AUTO, member H, member data, member render, member to_png, and member to_svg usage' is garbled (enum members called members of an example)"}
  - {id: B2, category: dangling_prose, section: "Documentation & Resources L251", evidence: "mech.py L251; README.md", summary: "'including classes like AUTO, H, and methods such as data, render' is garbled"}
  - {id: B3, category: false_claim, section: "API Reference L217", evidence: "up_clone src/aspose_barcode_foss/_internal/models/options.py:38-44 (L, M, Q, H)", summary: "'QrErrorCorrectionLevel ... supporting AUTO and H levels' is false; the enum is L, M, Q, H (introduced; live README is correct)"}
  - {id: B4, category: false_claim, section: "Development and Testing L267", evidence: "find tests -name '*.py' = 48; find tests -name 'test_*.py' = 37", summary: "'48 test files' counts __init__.py, conftest.py and helpers: MISLEADING (introduced)"}
  - {id: B5, category: dropped_live_content, section: "Scope and Limitations", evidence: "diff -u live README", summary: "Enterprise Edition paragraph (live links products.aspose.com/barcode/python-net/) is dropped"}
  - {id: B6, category: dropped_live_content, section: "Development and Testing, Dependencies, Installation", evidence: "diff -u live README", summary: "pytest/ruff commands, dev dependencies, py.typed, distribution-versus-import-name line all dropped"}
  - {id: B7, category: demoted_finding_true, section: "At a Glance, Key Capabilities, Scope", evidence: "review.json advisory F01/F02/F04/F05/F08", summary: "demoted findings are true: diagram lost symbology names and the Outputs subgraph; encode_mode, allow_check_digit_input and code39ext detail lost; PDF limitation repeated 3 times; garbled examples sentence; py.typed lost"}
  - {id: B8, category: template, section: "API Reference", evidence: "README.md L160-204", summary: "same type listed twice under different names (protocol 5.4 garble)"}
---
```

Evidence notes. PyPI `aspose-barcode-foss` returns 404, so "not yet published" is TRUE (PASS). `python_requires >=3.12` and `Pillow>=10.1.0` match pyproject.toml (PASS). The quick start and options names exist in the source (PASS). Introduced FAIL or MISLEADING results: B1, B2, B3, B4 (four, so the "several" threshold is met). Verdict rule: three or more introduced failures, therefore DO_NOT_PROPOSE.

---

## 2. BASELINE aspose-cells-foss/Aspose.Cells-FOSS-for-Python

```
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Python
bundle_path: E:\rp\cells-python\candidates\aspose-cells-foss__Aspose.Cells-FOSS-for-Python\4f6768a7b349a1309644f456eb43bc35f70c16d7
code_version: baseline (origin/main 7c5acbf7)
bundle_hash: 97c53a74446b5568558fd0cc1cf6da1f38f70f8f78964a880fd8b1af1f4ff034
readme_sha256: fbc96d06c3f48659736169bb167cc3a372b8c92a9c1ed7ace6514dd430a93932
source_revision: 4f6768a7b349a1309644f456eb43bc35f70c16d7
live_head: 4f6768a7b349a1309644f456eb43bc35f70c16d7
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: medium
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 13
claims_failed: 3
forbidden_wording_hits: 0
could_not_verify: ["snippets not re-run", "'130 types' not recounted", "Standard-encryption read limitation not re-derived (inherited, live README says the same)"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "Enterprise Edition paragraph not rendered (ENTERPRISE_NO_VERIFIED_TARGET deferral); live links products.aspose.com/cells/python-net/"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "API Reference", summary: "member reference is filler ('Defined as `def copy(self)`', 'Defined as `def lower_right_column(self)`'), not documentation"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Opening, At a Glance, Scope", summary: "restore CSV import, JSON and Markdown outputs, AutoFilter, 16 chart types, merged cells/defined names/hyperlinks, page setup"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Key Capabilities", summary: "password-open path is Workbook(path, password=...), not 'decrypt_xlsx automatically'"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Opening L7, Scope, At a Glance", evidence: "up_clone aspose/cells_foss/workbook.py:539 def load_csv; live README 'CSV also supports import'", summary: "CSV described as output/export-only; CSV import (load_csv) exists and the live README says so (introduced, MISLEADING)"}
  - {id: B2, category: false_claim, section: "At a Glance", evidence: "README.md L23-54 against Key Capabilities L63", summary: "diagram Outputs say 'CSV or XLSX file' while Key Capabilities lists JSON and Markdown export too; inputs omit CSV (introduced, MISLEADING)"}
  - {id: B3, category: false_claim, section: "Key Capabilities (encryption)", evidence: "xlsx_encryptor.py:387 decrypt_xlsx(input_path, output_path, password); workbook.py:92 Workbook(file_path, password)", summary: "'open encrypted files by providing the correct password to decrypt_xlsx automatically' misdescribes the API (introduced, MISLEADING)"}
  - {id: B4, category: dropped_live_content, section: "Scope and Limitations", evidence: "diff -u live README", summary: "Enterprise Edition paragraph dropped"}
  - {id: B5, category: demoted_finding_true, section: "Opening, At a Glance, Key Capabilities", evidence: "review.json advisory F01-F04 (readers 1-3)", summary: "demoted omissions are true: AutoFilter, 16 chart types, page setup, merged cells, defined names, hyperlinks, borders/alignment, FormulaEvaluator detail, 'pure-Python', dependency purposes all dropped from live"}
  - {id: B6, category: other, section: "API Reference, Detailed Member Reference", evidence: "README.md L420-650", summary: "filler member lines 'Defined as `def ...`' added with no visitor value"}
---
```

Evidence notes. PASS: PyPI 26.7.0 equals pyproject 26.7.0 and is the latest release; `python_requires >=3.7`; `olefile>=0.46` and `pycryptodome>=3.15.0` match; `pip install aspose-cells-foss` valid; `save_workbook_as_csv/json/markdown`, `get_worksheet_by_name`, `copy_worksheet` exist; AGENTS.md exists. The only-Agile-encryption limitation is true (xlsx_encryptor.py raises NotImplementedError otherwise).

---

## 3. BASELINE aspose-cells-foss/Aspose.Cells-FOSS-for-Java

```
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Java
bundle_path: E:\rp\cells-java\candidates\aspose-cells-foss__Aspose.Cells-FOSS-for-Java\c65329e7257b1311abb9686d7e4957a8cc002955
code_version: baseline (origin/main 7c5acbf7)
bundle_hash: ddb99054caed5a86b395ca8ea53964399fa450e62b829f6a99c185b15b7b132d
readme_sha256: a7c2c03bd9a81f753f6e97576e256e58a77c55e111e7f18cd1e308bb7c9452d6
source_revision: c65329e7257b1311abb9686d7e4957a8cc002955
live_head: c65329e7257b1311abb9686d7e4957a8cc002955
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 12
claims_failed: 4
forbidden_wording_hits: 0
could_not_verify: ["snippets not re-run (no JDK build attempted)", "'183 types' not recounted"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "API Reference", summary: "the table is empty: 'Core API' has only a sentence, yet the section says it 'contains the full supported public API surface - 183 public types'"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Installation", summary: "pom dependency and Gradle snippets replaced by a bare 'mvn dependency:get' command that does not add the dependency to a project"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Opening", summary: "remove unsupported 'formats such as XLSX', 'convert', 'data export' and audience sentence; restore POI-test-scope and .xlsx-only statements"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Key Capabilities, At a Glance, Scope, Project Structure", summary: "restore merged cells/defined names/hyperlinks, AutoFilter, charts (18 of 25 ChartType), Project Structure, skeleton-code limitation"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Opening L7", evidence: "live README 'Saving is currently limited to .xlsx'; Scope bullet in the same candidate", summary: "'reads and writes Excel files in formats such as XLSX ... convert spreadsheets ... data export' implies multiple formats; only .xlsx is supported (introduced, MISLEADING)"}
  - {id: B2, category: false_claim, section: "Opening L7", evidence: "no source for an audience", summary: "'Users include developers building enterprise reporting tools, data analysis pipelines, and document generation services' is unsupported (introduced)"}
  - {id: B3, category: dropped_live_content, section: "API Reference", evidence: "live README L277-480 lists the public types; candidate L190-199 has none", summary: "entire API table (classes, interfaces, enumerations) dropped while the text claims the full surface"}
  - {id: B4, category: dropped_live_content, section: "Installation", evidence: "live README L111-130", summary: "pom.xml <dependency> and Gradle forms dropped; mvn dependency:get misleads about adding a dependency (introduced, MISLEADING)"}
  - {id: B5, category: dropped_live_content, section: "Project Structure; Key Capabilities", evidence: "live README L261-276", summary: "Project Structure section dropped (even though the Navigation F08 finding named it); AutoFilter, charts, merged cells, hyperlinks, skeleton-code limitation dropped"}
  - {id: B6, category: demoted_finding_true, section: "Opening, At a Glance, Installation, Dependencies, API", evidence: "review.json advisory F01-F08 (readers 1-3)", summary: "demoted findings true: promotional opening, simplified diagram, mvn command replaces XML, POI test-scope note lost, API table truncated"}
---
```

Evidence notes. PASS: Maven Central latest and release 26.7.0, POM 26.7.0 returns 200; Java 17 target; "38 test files" is TRUE (38 .java under src/test); 38 AutoShapeType members; POI 5.3.0 and JUnit 5.10.2 match pom properties; `Agents.md` file exists (case matches). The Enterprise Edition paragraph is present and uses the canonical anchor shape.

---

## 4. BASELINE aspose-cells-foss/Aspose.Cells-FOSS-for-Go

```
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Go
bundle_path: E:\rp\cells-go\candidates\aspose-cells-foss__Aspose.Cells-FOSS-for-Go\99c789e9175f2b12ad82bafeeba148ddcc1367fb   (CURRENT; two earlier revision dirs exist)
code_version: baseline (origin/main 7c5acbf7)
bundle_hash: 899e98d779538e2e3c37d27f2db2aa6f8dad7fc07cf812fdeb85fa5eb336e470
readme_sha256: 099343e180cd58ef8b84f2652c05e093eec12cad639c17a6dfc132337c5144f7
source_revision: 99c789e9175f2b12ad82bafeeba148ddcc1367fb
live_head: 99c789e9175f2b12ad82bafeeba148ddcc1367fb
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 12
claims_failed: 3
forbidden_wording_hits: 0
could_not_verify: ["snippets not re-run (no Go toolchain run); examples.json shows #1 NOT_VERIFIED and #6 FAILED (the picture example, which the candidate dropped)", "'28 types' not recounted"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "lead-in 'Run every bundled example program:' is followed by prose, and the live `go test ./...` and `cd examples; for d in */; do go run ./$d; done` commands are lost (the code block was withheld but the lead-in and prose survived)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "Enterprise Edition paragraph not rendered (live links products.aspose.com/cells/go-cpp/)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "filler lines 'Tables: Defined as `[]*Table`'; the table also lists Chart, PivotTable and VBAProject"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Scope and Limitations", summary: "garbled A1 bullet"}
  - {id: F5, kind: redraw, severity: MINOR, section: "At a Glance, Key Capabilities, Additional Examples", summary: "restore CSV input/output, Picture embedding capability, encryption detail, Starting Points/Outputs"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Development and Testing L531", evidence: "mech.py: 'Run every bundled example program:' lead-in with no code block", summary: "dangling lead-in; real commands absent"}
  - {id: B2, category: false_claim, section: "Scope and Limitations L520", evidence: "up_clone aspose/cells_foss/cell.go:14-17 (Ref, XMLName are struct fields)", summary: "'Cell references must be A1-style strings such as Cell.Ref and Cell.XMLName' is garbled; Ref/XMLName are struct fields, not example references (introduced; live gives \"A1\", \"B2\")"}
  - {id: B3, category: dropped_live_content, section: "Scope and Limitations", evidence: "diff -u live README L486-490", summary: "Enterprise Edition paragraph dropped"}
  - {id: B4, category: dropped_live_content, section: "Development and Testing, Key Capabilities, Additional Examples", evidence: "diff -u live README", summary: "go test commands, Picture embedding capability and example, Project Structure, 'Detailed Documentation' and Constraints dropped"}
  - {id: B5, category: demoted_finding_true, section: "At a Glance, Key Capabilities, Installation", evidence: "review.json advisory (F01-F05 per reader)", summary: "demoted findings true: diagram loses Starting Points/Outputs and CSV input; Picture and encryption detail lost; install path differs from live (go get without /aspose/cells_foss)"}
  - {id: B6, category: other, section: "Key Capabilities", evidence: "up_clone aspose/cells_foss/workbook.go:65-77", summary: "recommends VerifyPassword, whose source comment says it is a non-constant-time comparison and to use CheckPassword instead (inherited from live; candidate lists both)"}
---
```

Evidence notes. PASS: Go proxy for module `.../v26` lists v26.7.0 and v26.7.1, so "published package" is TRUE; go.mod says `go 1.24.5`; "23 test files under tests/" is TRUE (23 `*_test.go`); `CalculateFormula` supports SUM/AVERAGE/MAX/MIN; ImportFromCSV stores strings; pkg.go.dev returns 200. The unreferenced second Quick Start snippet lacks imports and `fmt` (inherited from live).

---

## 5. BASELINE aspose-3d-foss/Aspose.3D-FOSS-for-Python

```
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-Python
bundle_path: E:\rp\3d-python\candidates\aspose-3d-foss__Aspose.3D-FOSS-for-Python\65b1f577c0f16d0d9112bb6c1153d3024543ac02
code_version: baseline (origin/main 7c5acbf7)
bundle_hash: 9855f39caae2f13c48c070fce79293c49480aa830228d67509024e0202eebbd0
readme_sha256: b0a0f4e5fc56d57d275f50a859a6f8f96b1e283c09e72f882a16edaabbd8174b
source_revision: 65b1f577c0f16d0d9112bb6c1153d3024543ac02
live_head: 65b1f577c0f16d0d9112bb6c1153d3024543ac02
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 15
claims_failed: 7
forbidden_wording_hits: 0
could_not_verify: ["snippets not re-run; examples.json has 4 NEEDS_INPUT and 1 FAILED (Position a Node, dropped)", "'337 types' versus live '305 public types' not reconciled"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "the opening sentence claims read AND write access to COLLADA and FBX; FBX export and COLLADA export are not implemented (claim-support check absent)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Additional Examples, Development and Testing", summary: "lead-ins 'Build a scene from scratch and export it to glTF:' and 'Install the repository and run the test suite:' have no block after them (code blocks withheld, lead-ins kept)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Documentation & Resources", summary: "the live link list is pasted a second time under a new list, so the section holds duplicate entries and a lone orphan bullet"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Key Capabilities, Quick Start", summary: "triangulation attributed to PolygonBuilder; 'textured crate' for an untextured example; '34 test files'"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Key Capabilities (Triangulate)", evidence: "up_clone aspose/threed/entities/PolygonBuilder.py (begin/add_vertex/end only); PolygonModifier.py:120-140 has the ear-clipping", summary: "'triangulated ... using PolygonBuilder, which implements a real ear-clipping algorithm' is wrong; PolygonModifier does it (introduced)"}
  - {id: B2, category: false_claim, section: "Scope and Limitations opening", evidence: "FbxExporter.save raises NotImplementedError; live Scope bullets; repro scene.save('o.dae') -> NotImplementedError", summary: "'provides read and write access to COLLADA and FBX geometry' is false (introduced)"}
  - {id: B3, category: false_claim, section: "Development and Testing", evidence: "tests/ has 34 .py files of which verify_module.py is not test_*; test_*.py = 33; live says 33", summary: "'34 test files' MISLEADING (introduced)"}
  - {id: B4, category: false_claim, section: "Quick Start", evidence: "example uses LambertMaterial.diffuse_color only; Texture raises NotImplementedError on construction", summary: "'textured crate' is untrue; no texture is applied (introduced, MISLEADING)"}
  - {id: B5, category: false_claim, section: "API Reference vs Documentation", evidence: "README states 337 types in API Reference and 305 in the live docs bullet", summary: "type count inconsistent with the live README's 305 (introduced, MISLEADING)"}
  - {id: B6, category: dangling_prose, section: "Additional Examples L280; Development and Testing L729", evidence: "mech.py dangling lines", summary: "two lead-ins with no code; the second ends the section"}
  - {id: B7, category: template, section: "Documentation & Resources", evidence: "mech.py duplicate targets L702-708", summary: "duplicated list block"}
  - {id: B8, category: dropped_live_content, section: "Scope and Limitations, Quick Start, Examples", evidence: "diff -u live README", summary: "nine limitations dropped (PDF/PLY formats, import-path trap, Watermark, TransformBuilder, PointCloud, AxisSystem), OBJ import example, unittest discover command, dev-extra note, Phong, skeleton data"}
---
```

Evidence notes. PASS: PyPI 26.1.0 (single release) equals setup.py version and requires_python >=3.7; `install_requires` empty; PyPI badge and license MIT; Enterprise paragraph present. Introduced failures: B1-B5 (five).

---

## 6. SLICE aspose-3d-foss/Aspose.3D-FOSS-for-Python

```
---
repository: aspose-3d-foss/Aspose.3D-FOSS-for-Python
bundle_path: E:\rp-slice\3d-python\candidates\aspose-3d-foss__Aspose.3D-FOSS-for-Python\65b1f577c0f16d0d9112bb6c1153d3024543ac02   (CURRENT; one earlier dir exists)
code_version: slice (origin/main + review-gate integrity + claim-support check, e38cabc2)
bundle_hash: 8b51cff5acc3730ee6f25a7006745489436786655aad452386afdc72c39580c7
readme_sha256: b8aa7f3d845b3938df5c152c6e7c0887b023c70f09657dd22da76b18d76c881b
source_revision: 65b1f577c0f16d0d9112bb6c1153d3024543ac02
live_head: 65b1f577c0f16d0d9112bb6c1153d3024543ac02
reviewed_at: 2026-10-10
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: L-verifier2 (Sonnet 5.5)
claims_checked: 15
claims_failed: 6
forbidden_wording_hits: 0
could_not_verify: ["snippets not re-run; examples.json same receipts as baseline (4 NEEDS_INPUT, 1 FAILED)", "'337 types' versus '305' not reconciled", "PolygonBuilder-with-Vertex statement in the Mesh member text not tested"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Key Capabilities, At a Glance, Scope", summary: "COLLADA export asserted in three places although Scene.save('x.dae') raises NotImplementedError; the claim-support check did not catch a fact the candidate contradicts in its own Scope bullet"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "API Reference", summary: "Mesh member list shows union/difference/intersect/do_boolean with no note that they raise NotImplementedError; the live Boolean and the Watermark/TransformBuilder/NURBS/PointCloud/AxisSystem limitations are dropped"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Additional Examples, Development and Testing", summary: "narration 'More real, verified snippets are collected below' and an orphan lead-in 'Construct a mesh vertex by vertex ... :' with no code; 'run the test suite:' shows a single-file command"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Quick Start, Development and Testing, Documentation", summary: "'textured crate'; '33 test files' then 'covers 34 test files'; '305 public types' then 'covers all 337'"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Key Capabilities, At a Glance Outputs", evidence: "repro in clone: Scene.save('o.dae') -> NotImplementedError: supports_format is not implemented; live Scope bullet; candidate Scope bullet says the same", summary: "'exports scenes to .3mf, .dae, ...' and Outputs 'COLLADA' are false; the README contradicts itself (introduced)"}
  - {id: B2, category: false_claim, section: "Scope and Limitations opening", evidence: "same repro; FbxExporter raises NotImplementedError", summary: "'read and write access to ... COLLADA' is false (introduced)"}
  - {id: B3, category: false_claim, section: "Development and Testing L774", evidence: "33 test_*.py; tests/ has 34 .py (verify_module.py)", summary: "same paragraph says '33 real test files' and 'covers 34 test files': one is wrong (MISLEADING, introduced)"}
  - {id: B4, category: false_claim, section: "Quick Start", evidence: "diffuse_color only; Texture raises NotImplementedError", summary: "'textured crate' untrue (introduced, MISLEADING)"}
  - {id: B5, category: false_claim, section: "Documentation & Resources", evidence: "README L744 text", summary: "'all 305 public types ... It covers all 337' self-contradictory (introduced)"}
  - {id: B6, category: dangling_prose, section: "Additional Examples", evidence: "README L283-285", summary: "lead-in with no code and process narration ('real, verified snippets')"}
  - {id: B7, category: dropped_live_content, section: "Scope and Limitations, Development and Testing, Key Capabilities", evidence: "diff -u live README", summary: "Boolean, NURBS, Watermark, TransformBuilder, PointCloud, AxisSystem limitations, `unittest discover` command, PolygonModifier.triangulate(), primitives list, Phong, skeleton, dev-extra note dropped"}
  - {id: B8, category: other, section: "API Reference Detailed Member Reference", evidence: "README L690-740 ('Defined as `def ...`')", summary: "filler member lines; shading section describes only LambertMaterial"}
---
```

Evidence notes. This bundle is better than its baseline twin in these ways only: the review verdict came back ACCEPT unconverted (0 demoted advisories); no PolygonBuilder-triangulation falsehood; no duplicated Documentation block; the limitation bullets for PDF/PLY, FBX, COLLADA, import path, render, Texture are kept. It is not authorizable because the claim-support check missed an introduced, repro-able false claim (COLLADA export) and the review let through the dangling lead-in and test-count contradictions.

---

## Summary table

| candidate | code version | manifest state | review verdict as sealed | protocol verdict | MINOR or MAJOR | top blocking finding |
|---|---|---|---|---|---|---|
| barcode-python (Aspose.BarCode FOSS Python) | baseline 7c5acbf7 | READY_FOR_PROPOSAL | ACCEPT (as returned: REJECT_PRESENTATION) | DO_NOT_PROPOSE | MAJOR | garbled "member AUTO, member H" / "classes like AUTO, H"; false "QrErrorCorrectionLevel supports AUTO and H"; "48 test files" counts non-tests; Enterprise paragraph and test commands dropped |
| cells-python (Aspose.Cells FOSS Python) | baseline 7c5acbf7 | READY_FOR_PROPOSAL | ACCEPT (as returned: REJECT_PRESENTATION) | DO_NOT_PROPOSE | MAJOR | CSV described as export-only (load_csv exists); diagram/opening drop JSON/Markdown/AutoFilter/charts; Enterprise paragraph dropped |
| cells-java (Aspose.Cells FOSS Java) | baseline 7c5acbf7 | READY_FOR_PROPOSAL | ACCEPT (as returned: REJECT_PRESENTATION) | DO_NOT_PROPOSE | MAJOR | API Reference table empty yet claims full 183-type surface; opening implies multi-format and invents an audience; pom/Gradle install replaced |
| cells-go (Aspose.Cells FOSS Go) | baseline 7c5acbf7 | READY_FOR_PROPOSAL | ACCEPT (as returned: REJECT_PRESENTATION) | DO_NOT_PROPOSE | MAJOR | dangling "Run every bundled example program:"; garbled "Cell.Ref and Cell.XMLName" A1 bullet; Enterprise paragraph, go test commands, Picture dropped |
| 3d-python (Aspose.3D FOSS Python) | baseline 7c5acbf7 | READY_FOR_PROPOSAL | ACCEPT (as returned: REJECT_PRESENTATION) | DO_NOT_PROPOSE | MAJOR | five introduced false/misleading claims (PolygonBuilder triangulates; COLLADA/FBX write; textured crate; 34 test files; type counts) plus two dangling lead-ins and a duplicated docs list |
| 3d-python (same repo) | slice e38cabc2 | READY_FOR_PROPOSAL | ACCEPT (as returned: ACCEPT) | DO_NOT_PROPOSE | MAJOR | false ".dae export" in Key Capabilities, diagram and Scope intro (repro: Scene.save('o.dae') raises NotImplementedError); self-contradictory test and type counts; orphan lead-in plus "real, verified snippets" narration |

None of the six bundles was missing and none was INVALIDATED. All six carry byte-identical no-op proofs with zero provider calls.

Comparative note (baseline versus slice, only one pair is comparable): the slice 3D bundle is the same repo and revision as the baseline 3D bundle, with a different draw. The slice removes the review-gate conversion (no REJECT to ACCEPT) and the PolygonBuilder, duplicated-docs and two-dangling-lead-in defects, but still contains an introduced false capability claim, which the claim-support check did not stop, and the contradictory counts. Fixes needed in both versions are code changes (lead-in without block, count rules for test files, capability formats must not exceed what a registered exporter really reaches, member-reference filler).

## Count of AUTHORIZABLE per code version

- baseline (origin/main 7c5acbf7): 0 of 5
- slice (e38cabc2): 0 of 1
