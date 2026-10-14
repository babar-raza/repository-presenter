authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-.NET
bundle_hash: d608f48a7d71e7ea542b6f84668d93edafc67ac106414af6f212ebc157c6c891
readme_sha256: fee1b04e18a7d1c5b8bf28ab4ebb4e4f0c887a540999d482f5555bc974f9d72c
source_revision: 941814fd138dc28cf47123d48194f329f283498d
live_head: 941814fd138dc28cf47123d48194f329f283498d
reviewed_at: 2026-10-11T07:55:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 15
claims_failed: 1
forbidden_wording_hits: 0
could_not_verify: ["Quick Start / Additional Example compile receipts taken from examples.json (not re-run)", "'dotnet run' sample commands not executed"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "prose paragraph is mangled: identifiers with path separators are split into separate code spans ('dotnet build src `Aspose.Cells_FOSS` `Aspose.Cells_FOSS.csproj` -c Debug'); the same 15-project list is a wall of code spans"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "the same seven limitations are rendered twice (six prose bullets, then seven bold bullets); VERIFIED_MOVE of the live list plus a freshly authored list are both emitted"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "Enterprise Edition paragraph assembled as '...](url). it adds broader ...' (lower-case fragment start)"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "API Reference", summary: "Detailed Member Reference is an unsorted raw dump: per-class member lists then a second class-signature dump introduced by 'The table below summarizes ...' with no table; opening paragraph repeated; filler members ('Performs delete.', 'Adds the specified item.', 'Gets or sets the formula1.')"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Opening", summary: "remove invented audience sentence ('Developers use it to generate reports ...'); fix 'version 26.9.0.0 is available under the MIT license' run-on; 'without requiring a commercial license' is edition-adjacent wording"}
  - {id: F6, kind: redraw, severity: MINOR, section: "Key Capabilities / Installation / At a Glance / badges", summary: "restore dropped live content: Issues badge, Starting Points/Outputs in At a Glance, namespace `Aspose.Cells_FOSS` vs package id `Aspose.Cells.FOSS` note, .NET Framework 4.6.1+ consumption note, capabilities for pictures/shapes/comments/protection/filters/cell value types"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Development and Testing", evidence: "README.md L644 (single 1,000-character paragraph with split code spans)", summary: "INTRODUCED: garbled paragraph; live had clean bullet list and plain commands"}
  - {id: B2, category: dangling_prose, section: "Scope and Limitations", evidence: "README.md L625-630 duplicate L632-638", summary: "INTRODUCED: duplicated limitations list (protocol 5.5)"}
  - {id: B3, category: dangling_prose, section: "Scope and Limitations", evidence: "README.md L640 '... Enterprise Edition](...). it adds broader ...'", summary: "INTRODUCED: sentence fragment"}
  - {id: B4, category: dangling_prose, section: "API Reference", evidence: "README.md L376-609, L543 'The table below summarizes ...' (no table follows); L50 'with `Workbook`(fileName)'; L380 mixed code-span/no-span member names", summary: "INTRODUCED: unsorted dump, duplicated lead paragraph, dangling reference"}
  - {id: B5, category: false_claim, section: "Opening", evidence: "no README/doc/sample text supports 'Developers use it to generate reports, process spreadsheets programmatically, and integrate Excel-like functionality into their applications'", summary: "INTRODUCED: invented audience/use-case sentence"}
  - {id: B6, category: dropped_live_content, section: "Installation / Key Capabilities / badges / At a Glance", evidence: "diff live vs candidate", summary: "drops namespace-vs-package-id note, .NET Framework 4.6.1 note, Issues badge, At a Glance Starting Points/Outputs, five capability areas"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision equals live head; README sha256 equals manifest. review ACCEPT/ACCEPT, findings [], second_reader not triggered (single read). validation BC-01..BC-12, BC-14 PASS, advisory [].
- Dispositions: OMIT_UNSUPPORTED for the `<PackageReference ... Version="26.9.0.0">` snippet (rationale "not supported by any fact": the snippet is valid; NuGet normalises 26.9.0.0 to 26.9.0, ruling: minor loss), OMIT for the Create a Chart example (CORRECT: examples.json #8 FAILED, CS0200 `Chart.Name` read-only; live example does not compile - an upstream-text defect the candidate removes), OMIT of "Detailed Member Reference" heading, VERIFIED_MOVE of Documentation and Scope lists.
- Profile: C01 NOT_MET; D14 (mechanical template filling) UNEVALUATED ("no template evidence supplied"). The BC-05 pass hides that the moved Scope list AND a re-authored list both render (duplication).

# 2 Live comparison

ADDS (TRUE unless noted): Dependencies section with `SkiaSharp 2.88.8` (TRUE: csproj PackageReference and the published nuspec; the live README omitted this and called the library "pure managed code", which is questionable for a package depending on SkiaSharp natives: the candidate is better here); version 26.9.0 stated (TRUE); 98 types (TRUE); badge `.NET netstandard2.0 | net8.0` (TRUE); installation via source checkout `dotnet build` (TRUE, root has Aspose.Cells_FOSS.sln); a second Quick Start example and A4/OnePagePerSheet example promoted (TRUE); Table/validation/conditional formatting/hyperlink/PDF examples (receipts EXECUTED); invented audience (FALSE/unsupported, B5).
DROPS: see B6; plus `Detailed Member Reference` sections for Cells/Style/Save options reorganised; Interfaces/Structs sub-tables merged into one table; "Exceptions" group; `QUICKSTART.html`/`USER_GUIDE.html` under documentation/_site are in neither.
CHANGES: opening: live precise (pure managed/no Excel dependency/platforms) vs candidate generic with a run-on; Scope: equal content but duplicated; Dev section: worse (garbled); API: worse.
NET: worse. The live README is already template-conformant and richer.

# 3 Claim checks

| # | Claim (line) | How checked | Result |
|---|---|---|---|
| 1 | NuGet `Aspose.Cells.FOSS` 26.9.0 published (L61) | api.nuget.org flat container versions [26.5.0,26.6.0,26.7.0,26.9.0] | PASS |
| 2 | version = csproj (L7 "26.9.0.0") | csproj `<Version>26.9.0.0</Version>`; nuspec 26.9.0 | PASS (wording run-on) |
| 3 | `dotnet add package Aspose.Cells.FOSS` (L64) | package exists | PASS |
| 4 | source checkout `dotnet build` (L72) | ran at clone root: succeeds (Aspose.Cells_FOSS.sln present) | PASS |
| 5 | Dependency `SkiaSharp 2.88.8` (L79) | csproj L53; nuspec group deps | PASS |
| 6 | TFMs netstandard2.0;net8.0 (L83) | csproj TargetFrameworks | PASS |
| 7 | 98 public types (L263, L617) | grep public type names sort -u = 98; table rows 98 | PASS |
| 8 | Load limited to XLSX (`LoadFormat.Auto`/`Xlsx`) (L625) | LoadFormat.cs enum {Auto, Xlsx} | PASS |
| 9 | Save covers XLSX and PDF only (L626) | SaveFormat enum Xlsx, Pdf | PASS |
| 10 | `PdfSaveOptions.OnePagePerSheet`, `AllColumnsInOnePagePerSheet`, `DefaultFont` (L52,L422) | PdfSaveOptions.cs L38,L46 | PASS |
| 11 | LoadOptions TryRepairPackage/TryRepairXml/StrictMode (L56) | LoadOptions.cs | PASS |
| 12 | `Hyperlink`/`DefinedNameCollection`/`ListObjectCollection` Add overloads used in examples | source L112-143 etc. | PASS |
| 13 | MIT licence (L660) | License/LICENSE.txt "The MIT License (MIT)" | PASS |
| 14 | Contributor guide link `agents.md` (L618) | file exists lower-case | PASS |
| 15 | Links (29) | mech.py --net: no non-200; relative links resolve | PASS |
| 16 | "Developers use it to generate reports ..." (L7) | no supporting text in clone | FAIL (introduced) |

# 4 Mechanical and wording

- mech.py: 1 H1; sections in order; required sections present; one mermaid fence; fences have language; 1 suspect hit "commercial license" (L7: "without requiring a commercial license": names a licence, not an edition; borderline, report); Enterprise Edition anchor shape OK; no forum links; duplicate targets `#api-reference`, `License/LICENSE.txt`.
- Dangling/garbled: B1-B4. `Worksheet` row says "supported v0.1 worksheet features" (internal version narration). `Key Capabilities`: "Repair malformed workbooks. Repair malformed workbooks by..." (title repeated in the body of three bullets). Bash fences use backslash Windows paths (inherited).
- Scope intro sentence duplicates the opening.

# 5 Omitted information in the clone

- `documentation/_site/QUICKSTART.html`, `USER_GUIDE.html`: marginal (rendered docs).
- `samples/` (15 runnable projects): carried in Dev section but unreadably (B1).
- No tests directory; no CI workflow files observed; ThirdPartyNotices.txt and SkiaSharp.LICENSE.txt under License/: valuable - the library depends on SkiaSharp (MIT), candidate has no Third-Party Notices pointer (live neither); advisory.
- GitHub release notes (V26.9.0 tag referenced by the nuspec): not linked.

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: README "Create a Chart" example does not compile: `Chart.Name` is read-only. Where: README.md (Additional Examples) `chart.Name = "Revenue";`; Chart.cs L47 `public string Name => _model.Name;`. Repro: paste example into a console project referencing Aspose.Cells_FOSS.csproj, SDK 10.0.401 -> `error CS0200: Property or indexer 'Chart.Name' cannot be assigned to -- it is read only`. Fix: drop the assignment or add a setter. Severity: low (documentation example).
2. Possible, unreproduced: README states the library is "pure managed code" while the package depends on SkiaSharp (native assets).

# 7 Verdict and reasons

DO_NOT_PROPOSE (MAJOR): the live README is already conformant and richer; the candidate introduces four garbled/duplicated passages (B1-B4) that a maintainer would reject on sight, an invented audience sentence (B5) and drops verified content (B6). Its genuine improvements (Dependencies/SkiaSharp, removal of the non-compiling chart example) are outweighed.

Universal defects for routing: (U1) BC-04's "every identifier in prose must be a code span" rule is applied to paths and shell commands and splits them into adjacent code spans, wrecking development prose; (U2) a VERIFIED_MOVE'd inherited list and a freshly authored list for the same section both render (no duplicate-content check across inherited and authored units); (U3) Enterprise relationship text is concatenated after "Enterprise Edition](url)." without sentence-case normalisation; (U4) Detailed Member Reference emits a raw member dump with a dangling "The table below summarizes" lead-in (this lead-in is a live-README leftover carried by VERIFIED_PRESERVE); (U5) audience/use-case sentence invented in the opening (seen also in 3D-Java).

Confidence high. Could not verify: see front matter.

# 8 Retention of live content (added in the wave-3 completion pass)

Method (retention.py, read-only): the live README and the candidate are split into sentences (prose outside fences, tables and headings), list items, unique link targets (an absolute repo-file link equals the same relative link) and fenced code blocks. "Verbatim" = the whitespace-collapsed live unit appears unchanged in the candidate; "reworded" = best similarity >= 0.80 to a candidate unit of the same kind; "lost" = below 0.80. Table rows are reported separately (API tables are rewritten by the pipeline, so row text is a weaker signal than row keys).

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 23 | 7 | 30% | 1 | 15 |
| list items | 100 | 81 | 81% | 3 | 16 |
| links (unique targets) | 26 | 24 | 92% | 0 | 2 |
| code blocks | 15 | 12 | 80% | 0 | 3 |
| CORE (four kinds) | 164 | 124 | 76% | 4 | 36 (22%) |
| table rows (supplemental) | 101 | 96 | 95% | 2 | 3 (99 of 101 row keys kept) |

Lost: the opening's three sentences ('pure managed code', multi-targeting, Windows/Linux/macOS/containers), the .NET Framework 4.6.1 consumption sentence, the namespace-vs-package-id sentence (`Aspose.Cells_FOSS` vs `Aspose.Cells.FOSS`), the three Quick Start lead-ins and the 'Run a sample from the repository root' lead-in; capability bullets (workbook load/save, repair diagnostics, page setup, cell value types, styles, validation/conditional formatting, hyperlinks/defined names/protection, ListObjects, charts/comments, PDF export); the six exception-class items; Issues and Contributors badges; `PackageReference` snippet (valid; NuGet normalises 26.9.0.0), the chart example (does not compile upstream, justified) and the mermaid diagram (rewritten without Starting Points). Table: 3 rows lost, 99 of 101 keys kept (the API tables are the best-preserved area).
