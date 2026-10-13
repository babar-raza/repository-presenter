authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Java
bundle_hash: c05cb97797a0dcf08b6edec3a650c7aac6f94c12de4383f933d903b9f5b14876
readme_sha256: 550fe60cb0e4610c972fde59cfab6b953214dfb8b6b34c6a518cc7ad6c97af5e
source_revision: c65329e7257b1311abb9686d7e4957a8cc002955
live_head: c65329e7257b1311abb9686d7e4957a8cc002955
reviewed_at: 2026-10-11T08:20:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 17
claims_failed: 4
forbidden_wording_hits: 0
could_not_verify: ["Quick Start / Additional Example compile receipts taken from examples.json (no JDK on reviewer machine)", "mvn test / javadoc not run"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "API Reference", summary: "published-version statement 'version 26.7.0 ... is the sole published version' is false (Maven Central has 26.5.0 and 26.7.0); registry-derived 'only version' claims must be checked against the whole versions list"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "Enterprise paragraph assembled as '...](url). it adds ...' (lower-case fragment)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "'38 test files' counts 15 scenario-factory/helper classes; only 23 files contain @Test"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "API Reference", summary: "Project Structure tree is demoted into 'Detailed Member Reference > cells_foss' as an unlabelled code fence with a mangled lead-in (`cells_foss` code-span split inside a path); two enums named DiagnosticSeverity listed as 'cells_foss.DiagnosticSeverity' and 'core.DiagnosticSeverity' (the latter is internal)"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities", summary: "remove invented audience ('Users include Java developers who need to generate reports, process financial data ...', 'lightweight, self-contained applications'); 'Comments, images, and tables' capability title names tables but the text omits them; restore capabilities for tables/ListObjects, shapes, merged cells, defined names, hyperlinks, calculation properties, tab color/zoom"}
  - {id: F6, kind: redraw, severity: MINOR, section: "badges / Scope and Limitations / Dependencies", summary: "restore Maven Central version badge, the 'Apache POI is test scope only, never at runtime' sentence, and the two dropped scope bullets (unimplemented skeleton XML-mapper classes; metadata-fidelity APIs)"}
blocking_findings:
  - {id: B1, category: false_claim, section: "API Reference", evidence: "curl https://repo1.maven.org/maven2/org/aspose/aspose-cells-foss/maven-metadata.xml -> versions 26.5.0, 26.7.0", summary: "INTRODUCED: '26.7.0 ... is the sole published version' is false"}
  - {id: B2, category: template, section: "API Reference", evidence: "mech.py: fence at L418 has no language; acceptance_profile C13 NOT_MET", summary: "INTRODUCED: code fence without a language (template rule)"}
  - {id: B3, category: dangling_prose, section: "Scope and Limitations", evidence: "README.md L440-446: '...Enterprise Edition](https://products.aspose.com/cells/java/). it adds additional spreadsheet save formats ...'", summary: "INTRODUCED: sentence starts lower-case after a full stop"}
  - {id: B4, category: false_claim, section: "Opening", evidence: "no README/doc/test text names this audience; the live README never says it", summary: "INTRODUCED: invented audience/use-case sentence and 'without requiring a commercial license' framing"}
  - {id: B5, category: false_claim, section: "Development and Testing", evidence: "find src/test -name '*.java' = 38; grep -L '@Test|@ParameterizedTest' lists 15 files (AssertEx, *ScenarioFactory ...); 23 contain tests", summary: "INTRODUCED: '38 test files' misleading"}
  - {id: B6, category: dropped_live_content, section: "Key Capabilities / badges / Scope / Dependencies", evidence: "diff live vs candidate", summary: "drops tables (ListObjects), shapes (38 presets), merged cells, defined names, hyperlinks, CalculationProperties, Maven Central badge, Apache-POI-test-only statement, two limitations, At a Glance start/output nodes, Project Structure section, per-type API detail"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision equals live head; README sha256 equals manifest. review ACCEPT/ACCEPT; findings []; second_reader triggered (ADVISORY_DEFERRAL), read 2, corroborated [].
- validation BC-01..BC-12, BC-14 PASS. Advisories 013/015 (Maven XML, Gradle snippets) deferred NOT_CARRIED_BY_NAMED_SECTION: the candidate does render both snippets from facts (L66-81), so the deferral is harmless.
- acceptance_profile: C01 NOT_MET, C13 NOT_MET ("fence without a language at line 418"). The pipeline recorded a template miss as advisory only and still sealed READY_FOR_PROPOSAL.
- Dispositions: "Project Structure" heading OMIT_UNSUPPORTED while its paragraph and tree are VERIFIED_MOVE into the API section (a heading dropped, body kept - the tree is orphaned and unlabelled).

# 2 Live comparison

ADDS (verified): Gradle and `mvn dependency:get` forms (TRUE; artifact exists); explicit Required/Native/Development Dependencies with versions (TRUE: pom junit 5.10.2, poi-ooxml 5.3.0, both test scope); "183 types" (TRUE: 183 table rows; 182 distinct simple names + two enums both named DiagnosticSeverity); second Quick Start example (receipt EXECUTED); "38 test files" (MISLEADING); "sole published version" (FALSE); invented audience (FALSE).
DROPS: see B6; plus the Maven Central version badge, "pure-Java ... keeps OOXML packaging inside this repository" framing, Project Structure heading.
CHANGES: Key Capabilities 8 items vs live 13 (worse); Scope: 3 of 5 bullets kept; Enterprise paragraph degraded by B3; Development: prose paragraph added, `PUBLISHING.md` pointer removed from Dev (still in Docs) - equal.
NET: worse.

# 3 Claim checks

| # | Claim (line) | How checked | Result |
|---|---|---|---|
| 1 | Maven Central `org.aspose:aspose-cells-foss` 26.7.0 published (L61) | maven-metadata.xml; .../26.7.0/aspose-cells-foss-26.7.0.pom HTTP 200 | PASS |
| 2 | "version 26.7.0 ... is the sole published version" (L212) | maven-metadata.xml lists 26.5.0 and 26.7.0 | FAIL (introduced) |
| 3 | pom version 26.7.0; Java 17 (L87, badge) | pom.xml `<version>26.7.0</version>`, maven.compiler.source/target 17 | PASS |
| 4 | no required third-party deps; dev deps poi-ooxml 5.3.0, junit 5.10.2 (L83-96) | pom: both `<scope>test</scope>` | PASS |
| 5 | 183 public types (L214, L435) | 183 table rows; 182 distinct names + duplicate DiagnosticSeverity enum (cells_foss and core) | PASS |
| 6 | 38 test files (L454) | find src/test -name '*.java' = 38; only 23 contain @Test | FAIL (introduced, misleading) |
| 7 | 18 of 25 ChartType values creatable; 7 ChartEx not creatable (L52, L443) | ChartType.java has 25 constants; same statement in live README | PASS (not independently exercised) |
| 8 | PictureCollection supports JPEG, PNG, GIF, BMP (L55) | live README says the same; source detection not re-read | COULD_NOT_VERIFY |
| 9 | Saving limited to .xlsx (L443) | SaveFormat sources not found other than xlsx; live says same | PASS |
| 10 | Formulas stored, no calc engine (L445) | no evaluator class under src/main | PASS |
| 11 | Quick Start APIs exist: Workbook(), getWorksheets().get(0), Cells.get("A1").putValue, Style.setCustom, Rows.get(0).setHeight (L98-135) | receipts EXECUTED (javac 21.0.11) | PASS (receipt) |
| 12 | `LoadOptions.setTryRepairPackage/Xml/StrictMode`, `getLoadDiagnostics().hasRepairs()/getIssues()` (L137-155) | receipt EXECUTED | PASS (receipt) |
| 13 | Release workflow link (L454) | .github/workflows/maven-central-release.yml exists | PASS |
| 14 | `Agents.md` contributor guide (L434) | file Agents.md exists, case matches | PASS |
| 15 | MIT licence (L468) | License/LICENSE.txt | PASS |
| 16 | Links (28) | mech.py --net: no non-200, no missing relative targets | PASS |
| 17 | "Users include Java developers who need to generate reports, process financial data ..." (L7) | no supporting text | FAIL (introduced) |
| 18 | Unlabelled fence at L418 (template rule: every fence has a language) | mech.py | FAIL (introduced) |

# 4 Mechanical and wording

- mech.py: 1 H1; 11 H2 in order; required present; one mermaid fence; one fence without a language (B2); 1 suspect hit 'commercial license' (L7, "without requiring a commercial license": licence not edition; borderline, reported); Enterprise Edition anchor shape OK (but see B3); no forum links.
- Dangling/garbled: B3; "### cells_foss ... under src/main/java/org/aspose/`cells_foss`/ alongside integration tests" (code span splitting a path); the heading `cells_foss` for a module; duplicate-named enum rows (`cells_foss.DiagnosticSeverity`, `core.DiagnosticSeverity`); enums `BorderStyle`/`HorizontalAlignment`/`PageOrientation`/`SheetVisibility` are listed alongside `...Type` twins (internal duplicates) without distinction.
- Duplicates: "all 183 public types" appears in API Reference, Detailed Member Reference and Documentation (x2); the Documentation bullet says "for all 183 public types ... It covers all 183 verified public types".
- 'Comments, images, and tables' title/body mismatch (tables absent).

# 5 Omitted information in the clone

- ListObject/table, shape, merged cell, defined name, hyperlink, CalculationProperties support (live covers them); docs/apidocs (generated Javadoc) pointer: advisory.
- `.actrc`, `.env.act.example`, `.secrets.example` indicate local act-based CI runs: marginal.
- No GitHub releases queried (200 on pom suffices).

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: two public enums both named `DiagnosticSeverity` (`org.aspose.cells_foss.DiagnosticSeverity` and `org.aspose.cells_foss.core.DiagnosticSeverity`). Where: src/main/java/org/aspose/cells_foss/DiagnosticSeverity.java, .../core/DiagnosticSeverity.java. Severity: low (API ambiguity; `core` is documented as internal).
2. Possible, unreproduced: committed `.secrets.example` / `.env.act.example` could be mistaken for real secrets; confirm they hold placeholders only.

# 7 Verdict and reasons

DO_NOT_PROPOSE (MAJOR): an INTRODUCED false published-version statement (B1) together with other blocking findings (template fence B2, sentence fragment B3, invented audience B4, misleading test count B5) and substantial loss of verified live capability content (B6). The live README is already conformant and richer.

Universal defects for routing: (U1) "only published version" derived from the manifest/one registry reading without reading the full versions list (npm/NuGet/Maven all list several); (U2) Enterprise paragraph fragment ". it adds" (also Cells-.NET; the clause is stored in lower case and appended after a full stop); (U3) a directory tree rendered in a fence with no language (BC-07 should block; C13 NOT_MET was advisory only); (U4) test-file count includes helper/factory classes (same family as 3D-.NET csproj/log and 3D-TypeScript setup.ts); (U5) invented audience sentence in the opening (4 of 4 candidates reviewed so far with a free-form opening); (U6) VERIFIED_MOVE of a Project Structure body after OMIT of its heading leaves an orphan unlabelled block; (U7) duplicate simple-name types (`core.DiagnosticSeverity`) listed without qualification of public vs internal.

Confidence high. Could not verify: see front matter.

# 8 Retention of live content (added in the wave-3 completion pass)

Method (retention.py, read-only): the live README and the candidate are split into sentences (prose outside fences, tables and headings), list items, unique link targets (an absolute repo-file link equals the same relative link) and fenced code blocks. "Verbatim" = the whitespace-collapsed live unit appears unchanged in the candidate; "reworded" = best similarity >= 0.80 to a candidate unit of the same kind; "lost" = below 0.80. Table rows are reported separately (API tables are rewritten by the pipeline, so row text is a weaker signal than row keys).

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 42 | 4 | 10% | 3 | 35 |
| list items | 37 | 13 | 35% | 3 | 21 |
| links (unique targets) | 30 | 24 | 80% | 0 | 6 |
| code blocks | 9 | 8 | 89% | 0 | 1 |
| CORE (four kinds) | 118 | 49 | 42% | 6 | 63 (53%) |
| table rows (supplemental) | 186 | 181 | 97% | 2 | 3 (183 of 186 row keys kept) |

Lost: the opening (pure-Java, Java 17, Apache POI only in test scope), ten capability paragraphs (worksheets, load options and diagnostics, styles, row/column layout, defined names/hyperlinks, validation, AutoFilter, print layout/freeze panes, comments, charts 18 of 25, shapes 38 presets, calculation settings); the install lead-ins ('Add the dependency to your pom.xml', 'Gradle (Groovy DSL)'; the code blocks are kept) and the Java 17 requirement sentences (`maven.compiler.source/target`); the dependency explanations (JUnit 5.10.2, Apache POI 5.3.0 as independent verifier); Maven Central badge, Java 17 badge, `repo1.maven.org` link, `openjdk.org` link; `Project Structure` navigation entry and the 'public API lives under src/main/java/...' paragraph; the 183-types sentence; two limitation sentences (unimplemented XML-mapper skeleton classes, OOXML-metadata-only APIs); the 'other common commands' paragraph; `PUBLISHING.md`/`Agents.md` link text (reworded); the mermaid diagram (rewritten). Table: 3 rows lost, 183 of 186 keys kept.
