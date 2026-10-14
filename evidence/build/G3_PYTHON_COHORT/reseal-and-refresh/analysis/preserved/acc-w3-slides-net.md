authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-slides-foss/Aspose.Slides-FOSS-for-.NET
bundle_hash: b40dc52a669aa9f042717cdd183119072537340537de457c1d9d2e54a44ed617
readme_sha256: 780c6b94438b53980d398f1bb9a5e1d04450a334a6af0fb6d57df677e44164f8
source_revision: 86c441b5d81e707f2ea9e01b197dbb6ff7a3859b
live_head: 86c441b5d81e707f2ea9e01b197dbb6ff7a3859b
reviewed_at: 2026-10-11T10:05:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 20
claims_failed: 7
forbidden_wording_hits: 1
could_not_verify: ["root `dotnet build` (README L77): both attempts failed with MSB3021 'access denied' copying obj->bin; the same csproj builds in Release, and an Application Control policy on this machine blocks loading unsigned managed assemblies from the scratch directory, so this is environmental and not a README finding", "no example was executed (the same policy blocks running compiled output); examples were compile-checked only against the clone's csproj, execution relies on the pipeline's receipts", "187 of 189 ShapeType values (distinct prstGeom per value) not re-measured"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Scope and Limitations / Save formats", summary: "the live 'What it cannot do' section (13 verified API gaps, 'only 3 of 21 SaveFormat values are written, 18 raise NotSupportedException', round-trip and language caveats) is dropped; Scope lists seven positive 'supports...' bullets instead; OMIT_UNSUPPORTED/VERIFIED_MOVE decisions did not carry the limitation tables (tables are not rendered into the limitation list)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Additional Examples", summary: "three of seven printed examples do not compile (CS0103 Color x2, CS0246 PointF): the `using Aspose.Slides.Foss.Drawing;` block was withheld (receipt 2 failed with CS5001 'no Main') although the harness supplied the usings for the other receipts; leftover sentences refer to the missing block and are placed inside the collapsed details after the last example"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "API Reference", summary: "264-type dump with an unsorted Core API table (interleaved groups), internal types, tautological enum descriptions, 'exposes the Aspose.Slides FOSS for .NET class as its primary entry point', and a garbage 'Detailed Member Reference / ### Foss' stub; XML-doc claims for GroupShape and IHyperlinkContainer (empty types) are now unqualified"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "'139 test files' counts every file under tests/ (csproj, pptx/jpg/png fixtures); real figure 128 .cs files, 121 with test attributes; Install-the-CI-package material is appended under Development without its heading"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities / Scope", summary: "opening duplicates itself (L7 vs L9-12) and points to a 'What it cannot do' section that no longer exists; the unsupported phrase 'without requiring a full commercial suite' (the audience itself is restated from the live README); Key Capabilities 'Embed images.' and 'Apply visual effects.' are sentence fragments; 'runs only on the net platform' is meaningless; restore Contributing/Security/Changelog/Code of Conduct links, API reference and knowledge-base links, package-id vs namespace casing note, Starting Points/Outputs in the diagram"}
blocking_findings:
  - {id: B1, category: dropped_live_content, section: "Scope and Limitations", evidence: "live README L373-456 ('This section is the point of this file') vs candidate L562-582; source checks: no AddChart/AddGroupShape/HyperlinkClick/AddSmartArt/SlideShowTransition/MasterTheme in src (grep -rl = 0); GroupShape.cs and IHyperlinkContainer.cs are empty; SaveFormat has 21 values, SaveFormatSupport throws NotSupportedException for all but Pptx/Ppsx/Potx", summary: "INTRODUCED LOSS: every verified limitation is gone; the candidate tells a visitor what the library supports and nothing it refuses, while its API table lists GroupShape and IHyperlinkContainer as working features"}
  - {id: B2, category: false_claim, section: "Additional Examples", evidence: "dotnet build -c Release of a console project referencing src/Aspose.Slides.Foss.csproj, ImplicitUsings on, only `using Aspose.Slides.Foss; using Aspose.Slides.Foss.Export;`: error CS0103 'Color' (text and effects examples), CS0246 'PointF' (notes and comments example)", summary: "INTRODUCED: three of seven examples do not compile as printed; the live README states the three required usings"}
  - {id: B3, category: false_claim, section: "Development and Testing", evidence: "find tests -type f = 139; find tests -name '*.cs' = 128 (ConformanceTests 20, IntegrationTests 17, Tests 91); grep -rlE '\\[(Fact|Theory)' tests = 121", summary: "INTRODUCED: '139 test files' counts fixtures and project files (MISLEADING)"}
  - {id: B4, category: false_claim, section: "Scope and Limitations", evidence: "candidate L567 'runs only on the net platform'; csproj TargetFrameworks net8.0;net10.0; live README: CI runs on ubuntu, windows and macos", summary: "INTRODUCED: meaningless/wrong platform statement"}
  - {id: B5, category: dangling_prose, section: "Opening", evidence: "README.md L7 vs L9-12 (the same sentence twice); L12 'What it cannot do.' unlinked and pointing at a deleted section; L244-261 live fragments ('Those three are this library's own namespaces', 'Every example below') orphaned after the last example", summary: "INTRODUCED: duplicated and dangling prose"}
  - {id: B6, category: dangling_prose, section: "Key Capabilities / API Reference", evidence: "L59 'Embed images. From byte arrays or streams as image objects and insert them ...'; L60 'Apply visual effects. Such as outer shadow ...'; L55 'using the Aspose.Slides FOSS for .NET class'; L267 'exposes the Aspose.Slides FOSS for .NET class as its primary entry point'; L550-552 '### Foss' stub", summary: "INTRODUCED: fragments and a product name used as a class"}
  - {id: B7, category: forbidden_wording, section: "Opening", evidence: "L7 'without requiring a full commercial suite' (absent from live and clone); the audience clause ('generate or modify decks on a server or in a build') is restated from live L12-13 and appears twice (L7, L9)", summary: "INTRODUCED: edition-adjacent wording; the audience itself is inherited but duplicated"}
  - {id: B8, category: template, section: "Scope and Limitations / Quick Start", evidence: "mech.py: fences at L117 (Output) and L573 (content types) have no language", summary: "fence without a language (inherited for the Output block; the content-type fence is orphaned in Scope without its lead-in)"}
  - {id: B9, category: dropped_live_content, section: "Documentation & Resources", evidence: "live L499-545; retention.py", summary: "drops the API-reference and knowledge-base links, Contributing/Code of Conduct/Changelog/Security links (all four files exist in the clone), the package-id vs namespace casing note, 'Why the !' nullable note, the XML-output verification notes for each example, Requirements table, 13-part package fact; 'Choosing an edition' dropped (policy-compatible, but its measured edition facts are lost)"}
  - {id: B10, category: demoted_finding_true, section: "Additional Examples", evidence: "validation.json advisory inherited_unit:033 LEADIN_OF_WITHHELD_CONTENT; examples.json receipt 2 FAILED CS5001", summary: "the advisory hides the real cause of B2: the namespace block was withheld because it is not a standalone program"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision 86c441b5 == live head (git clone --depth 1); README sha256 equals manifest; review ACCEPT (as returned ACCEPT; second_reader read 2, trigger ADVISORY_DEFERRAL, findings []); validation BC-01..BC-12, BC-14 PASS; no-op VERIFIED, 0 provider calls on rerun.
- Profile: C01 NOT_MET, C13 NOT_MET (fences without a language at L117, L573; C13 is advisory and did not block); D14 UNEVALUATED.
- Receipts: 8 EXECUTED, 1 FAILED (receipt 2, the namespace `using` block, CS5001 no Main - correct to fail, wrong to withhold).
- Dispositions: 19 VERIFIED_MOVE (15 of them headings), 40 VERIFIED_PRESERVE, 22 SUPERSEDE_REDUNDANT, 3 CORRECT_WITH_EVIDENCE; 8 OMIT_UNSUPPORTED (the 46-part round-trip measurement, the edition comparison table, the "Requirements" heading, the namespace code block); VERIFIED_MOVE for the 'Not in the public API' and 'Save formats' tables ("aligns with the Scope and Limitations section") yet the Scope section renders none of those rows.
- Advisories ruled: unit 007 (diagram caption) acceptable; unit 033 (namespaces lead-in) TRUE loss, root cause of B2/B10; unit 083 (list of other-edition links) acceptable under the contract.

# 2 Live comparison

The live README is not the standard template: it is a bespoke document (Requirements, Examples, What it can do, What it cannot do, Choosing an edition, Contributing, Security). Its own structure is therefore the standard here; the candidate replaces it with the generic 11-section shape and the replacement carries much less.

ADDS (TRUE unless noted): banner image and a four-badge row (TRUE); `dotnet build` at the repository root (a root `Aspose.Slides.Foss.sln` exists; could not execute); explicit "Dependencies" and "Key Capabilities" sections (TRUE content); 264 public types statement (TRUE); API table with 222 class/interface rows and 42 enumerations (TRUE as a list; several rows describe internals); "Enterprise Edition" paragraph (content is the live "When you want the commercial product" text; TRUE per live); "without requiring a full commercial suite" (UNSUPPORTED); "runs only on the net platform" (FALSE).
DROPS (valuable): all of "What it cannot do" (13 missing-API rows, save formats 3 of 21 and the refusal message, round-trip measurement, language attribute caveat); "What it can do" feature inventory (15 bullets: 187 of 189 shapes, fills, lines, 3-D, document properties, unknown parts); the `using` block and its explanation; "Why the `!`" nullable note; per-example XML evidence sentences; package-id vs namespace casing note (`Aspose.Slides.FOSS` vs `Aspose.Slides.Foss`); "13-part package, 4:3, no API to change slide size"; "Requirements" platforms row (CI on three OSes); CI-package install heading; links to API reference, knowledge base, CONTRIBUTING.md, CODE_OF_CONDUCT.md, CHANGELOG.md, SECURITY.md; the Contributing and Security sections; diagram Starting Points and Outputs nodes; seven of eight effects and the 3-D/fill/line/document-property capabilities from Key Capabilities.
DROPS (justified): the forum.aspose.com link; the sentence "mirrors the naming of the commercial Aspose.Slides for .NET product"; the cross-edition comparison table (platform comparison labels are forbidden by the protocol; its facts about this edition are duplicated in the dropped limitations, which should have been kept).
CHANGES: opening worse (duplicated, generic); capabilities worse (single effect, fragments); install equal+ (source checkout added) but the namespace casing note lost; API reference worse (unsorted dump of 264 rows, internal types); Scope far worse.
NET: worse.

Retention of live content (retention.py; verbatim = whitespace-collapsed exact substring; reworded = similarity >= 0.80; repo-file links count equal whether absolute or relative):

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 81 | 15 | 19% | 2 | 64 |
| list items | 23 | 2 | 9% | 1 | 20 |
| links (unique targets) | 24 | 9 | 38% | 0 | 15 |
| code blocks | 18 | 15 | 83% | 0 | 3 (mermaid rewritten, the usings block, the refusal message) |
| CORE (four kinds) | 146 | 41 | 28% | 3 | 102 (70%) |
| table rows (supplemental) | 46 | 0 | 0% | 0 | 46 (all key/value and comparison tables) |

Lost links: CHANGELOG, CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, kb.aspose.com, reference.aspose.com, forum (justified), dotnet.microsoft.com, three sibling-edition repositories (policy), the .NET and licence shields, two in-page anchors (sections removed).

# 3 Claim checks

| # | Claim (line) | How checked | Result |
|---|---|---|---|
| 1 | NuGet `Aspose.Slides.FOSS` version 26.9.0 (L66, L620) | api.nuget.org/v3-flatcontainer/aspose.slides.foss/index.json = ["26.9.0"]; Directory.Build.props | PASS |
| 2 | `dotnet add package Aspose.Slides.FOSS` (L69) | package id exists on NuGet | PASS |
| 3 | Targets net8.0 and net10.0 (L7, L88) | csproj `<TargetFrameworks>net8.0;net10.0` | PASS |
| 4 | No package dependencies (L7, L84) | `grep PackageReference src/Aspose.Slides.Foss/*.csproj` empty | PASS |
| 5 | 264 public types (L269) | regex count of `public` class/interface/enum/struct declarations in src = 264 (incl. types in the Internal namespace folders) | PASS (but includes internals) |
| 6 | Source checkout `dotnet build` at the root (L77) | root has Aspose.Slides.Foss.sln; two builds failed MSB3021 access denied (environment) | COULD_NOT_VERIFY |
| 7 | `dotnet build src/Aspose.Slides.Foss/Aspose.Slides.Foss.csproj --configuration Release` (L593) | ran: Build succeeded, 0 warnings | PASS |
| 8 | `ProjectReference` snippet (L600) | project file exists at that relative layout | PASS |
| 9 | Quick Start compiles (L94-113) | compiled in a console project referencing the csproj; receipt 1 EXECUTED | PASS |
| 10 | Additional Examples compile as printed (L129-242) | same project with only the Quick Start usings: CS0103 `Color` (L143, L193), CS0246 `PointF` (L213) | FAIL - introduced |
| 11 | "The suite covers 139 test files under `tests/`" (L588) | `find tests -type f` = 139 (fixtures, csproj); `*.cs` = 128; files with [Fact]/[Theory] = 121 | FAIL (MISLEADING) - introduced |
| 12 | `GroupShape` "contains a collection of shapes" (L336) | GroupShape.cs: `public sealed class GroupShape : Shape { }` | FAIL (MISLEADING) - introduced (live says no shape can hold children) |
| 13 | `IHyperlinkContainer` "can contain hyperlinks" (L378) | IHyperlinkContainer.cs is an empty interface | FAIL (MISLEADING) - introduced |
| 14 | "runs only on the net platform" (L567) | csproj + live README (CI on three OSes) | FAIL - introduced |
| 15 | PPTX/PPSX/POTX supported, content types (L564, L573-577) | SaveFormatSupport.cs L31-32 and presentation main part | PASS |
| 16 | Add 187 of the 189 `ShapeType` values (L56) | ShapeType.cs has 189 members; per-value output not re-measured | PASS count; COULD_NOT_VERIFY per-value (inherited) |
| 17 | "... without requiring a full commercial suite" (L7) | audience clause restated from live L12-13 (supported); "full commercial suite" absent from live and clone | FAIL (unsupported, edition-adjacent wording) - introduced |
| 18 | "exposes the Aspose.Slides FOSS for .NET class as its primary entry point" (L267) | entry point is `Presentation` | FAIL - introduced |
| 19 | Links (27) | mech.py --net: no non-200; relative links (LICENSE, workflow) resolve | PASS |
| 20 | MIT licence (L628) | LICENSE file present, MIT | PASS |

# 4 Mechanical and wording

- mech.py: 1 H1; sections in the standard order, none missing; one mermaid fence; two fences without a language (L117, L573); Enterprise Edition anchor shape OK; no forum link; duplicate targets `https://products.aspose.com/slides/net/` (L558, L582) and `LICENSE`.
- Wording: "without requiring a full commercial suite" (L7), BLOCKING by judgement. mech.py also flagged "wrapper" (L429, `Image`: "Concrete image wrapper holding raw bytes", class description, not an implementation bridge) and seven "backed by" API descriptions (L278-L473, XML-guide/OPC part explanations, not a cross-platform bridge): reported, not counted.
- Dangling/garbled: B5, B6; L243-261 orphan paragraphs; L566 "installed using the dotnet CLI with the command dotnet add package `Aspose.Slides.FOSS`." duplicates Installation and breaks the span; L568 "adding notes slides with comments" conflates two features; table descriptions contain HTML entities (`&lt;a:rPr&gt;`).
- Duplicates: opening paragraphs; the install route appears under Installation and again under Development; the `dotnet add package ... --version 26.9.0` line repeats.
- Table of API rows unsorted (`Color`, `PointF`, `Size`, `SizeF` inside the D- group; `IThemeable` after `TextFrameFormat`; OPC internals between `Images` and `Template`).

# 5 Omitted information in the clone

- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `PUBLISHING.md`, `AGENTS.md`, `docs/` exist; live README links the first four, the candidate none (defect: live has it).
- `.github/workflows/ci.yml` (three-OS matrix) and `nuget-release.yml`: matrix not stated by candidate (live states it in Requirements).
- Three test suites (Tests, ConformanceTests, IntegrationTests) with `tests/test_data/*.pptx` fixtures: the candidate says "three test suites" but does not name them or give the `dotnet test` command (neither does live; CONTRIBUTING.md holds it).

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: Public API advertises group shapes and hyperlink containers that are empty types. Where: src/Aspose.Slides.Foss/GroupShape.cs (`public sealed class GroupShape : Shape { }` with the doc comment "Represents a group shape that contains a collection of shapes."), src/Aspose.Slides.Foss/IHyperlinkContainer.cs (empty interface, "can contain hyperlinks"). Repro: `grep -n '' src/Aspose.Slides.Foss/GroupShape.cs src/Aspose.Slides.Foss/IHyperlinkContainer.cs`. Fix: mark them `[EditorBrowsable(Never)]`/internal or correct the XML docs to say "reserved, not implemented". Severity: low (the README already documents it). Proof: file contents above.
2. Possible, unreproduced: `dotnet build` at the repository root fails on a machine with Application Control restrictions (MSB3021 access denied on obj->bin copy); not attributable to the repository.

# 7 Verdict and reasons

DO_NOT_PROPOSE (MAJOR). Seven independent introduced FAIL/MISLEADING results (rows 10-14, 17 and 18: uncompilable examples, '139 test files', GroupShape, IHyperlinkContainer, 'net platform', 'commercial suite' wording, entry-point sentence) plus a dropped section the live README calls "the point of this file". A maintainer would reject a PR that deletes the limitations table, strips the `using` lines that make the examples compile and adds a "139 test files" claim. The live README is already richer and accurate.

Needed before reconsideration (code): (a) limitation tables (the two-column 'Not in the public API' and 'Save formats' tables) must render as limitation bullets when VERIFIED_MOVE'd to Scope and BC-05 must verify each row appears; (b) an example check that requires every printed example to compile with only the usings printed in the README (print the harness-supplied usings or a `using` preamble; never withhold the namespace block); (c) test-file count over test declarations; (d) opening must not duplicate itself or reference a section the candidate did not render; (e) API reference renderer must group, sort and suppress internal namespaces and must not describe empty types as features.

Universal defects (routing): U-PARTIAL-PRESERVE / U-LIMITATIONS-DROPPED (VERIFIED_MOVE of table limitations renders nothing); U-EXAMPLE-USINGS (NEW: harness-supplied usings not printed, examples do not compile as shown); U-COUNT; U-AUDIENCE; U-DANGLING-REFERENCE (NEW: text points at a section the candidate removed); U-FRAGMENT (capability bullets that start with "From"/"Such as"); U-DETAILED-REFERENCE; U-FENCE-LANG.

Confidence high on all compile- and source-derived findings. Could not verify: see front matter.
