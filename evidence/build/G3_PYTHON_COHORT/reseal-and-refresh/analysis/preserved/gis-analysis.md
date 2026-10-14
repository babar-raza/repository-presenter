authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# aspose-gis-foss/Aspose.GIS.FOSS-for-.Net: what a README could truthfully say, what blocks it, what to do

Read-only lane, 2026-10-12. Live head re-read today: `b9b8c9c760bf02f6e7f06438feeabb3d0e43c1e4` ("Second part", pushed 2026-09-29, unchanged since the 2026-10-01 draw). Nothing was written to any repository. Own reproduction ran in a push-disabled shallow clone under the scratchpad (`clone/gis`), .NET SDK 10.0.401. Standard read: `docs/README_STANDARD.md` and `data/readme_standard/*` on `integration/cut4b`; handoffs read on `wt/liss3-iss3b`.

## 0. Verdict

1. A truthful README is possible but it would be a status page, not the standard ten-section README. At most 7 of the 12 standard sections can be written from verified facts; Quick Start, Additional Examples, At a Glance, Documentation and Resources, and License have no verifiable content. Installation can carry no working command.
2. The right pipeline behaviour is a typed `BLOCKED_UPSTREAM` disposition (three handoff ids plus the resume predicate "`dotnet build` exits 0"), decided with zero model calls. It is not `insufficient_evidence` (that token means placeholder / no surface) and not `NON_PROCESSABLE` (that state means no manifest and no source; GIS has both). No code producer for `BLOCKED_UPSTREAM` exists today; the current behaviour burns 24 provider calls and then fails at BC-02.
3. Three upstream handoffs exist (build, LICENSE, README), all `HANDOFF_PENDING`, all re-verified CONFIRMED at this head, none fileable yet (registry `dry_run`, no approval record). Not covered: committed `obj/` (text-only draft U09, no defect class), and the test project defects. One of the handoff numbers is wrong (41 should be 42, section 4).
4. Recommendation: HOLD the README, file the issues on the owner's approval, add a zero-call preflight that types this shape. Decision list in section 6.

## 1. Verified facts (each re-checked today)

| Fact | Evidence |
|---|---|
| Default branch `main`, 2 commits ("First commit" 2026-09-22, "Second part" 2026-09-29), one contributor (FilatovVitaliy, 2), 0 tags, 0 releases, 0 workflows, 0 issues, no description, no topics, org has only this repository | `gh api` GETs |
| No README: `gh api repos/<r>/readme` is 404; root holds `.gitignore`, `Aspose.GIS.FOSS.slnx`, two project folders | tree at head (114 tracked files) |
| No license: GitHub `license: null`, no LICENSE/COPYING anywhere in the tree, csproj has no `PackageLicenseExpression` | `gh api`, tree |
| Not on NuGet: `api.nuget.org/v3-flatcontainer/aspose.gis.foss/index.json` is 404 (the id `aspose.gis` is 200 but is a different, commercial package; nothing ties it to this repository, so a README must not mention it as an install) | curl GET |
| csproj: `net10.0`, ImplicitUsings, Nullable; no PackageId, Version, Description, repository URL; zero PackageReference. Class1.cs is the empty template stub | `Aspose.GIS.FOSS.csproj` |
| Test project: NUnit 4.3.2, NUnit3TestAdapter 5.0.0, NUnit.Analyzers 4.7.0, Microsoft.NET.Test.Sdk 17.14.0, coverlet.collector 6.0.4; no ProjectReference to the library; one file `MainTests.cs` with 2 `[Test]` | csproj, file |
| Source: about 19.6k lines of C# in nine namespaces (`Aspose.GIS.FOSS`, `.Common`, `.Formats`, `.Formats.Wkt`, `.Geometries`, `.Operations`, `.Rendering`, `.SpatialReferencing`, `.SpatialReferencing.Internal`); roughly 70 public type declarations (rough regex count, the pipeline's public_symbol facts are the authority); 83 files carry XML `<summary>`; 5 files carry `<example>` blocks | grep over clone |
| Library build FAILS: `dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release` gives 369 Error(s), 45 Warning(s); 57 distinct unresolved type names; codes CS0246, CS0115, CS0534, CS0234, CS0535, CS0508, CS8937. **Reproduced today, identical to the 2026-10-10 and 2026-10-11 logs** | `src/gisbuild-now.txt` |
| Test build FAILS: 12 errors (`VectorLayer`, `Drivers`, `Dataset`, `GeoPackageDataset` not found; the project does not reference the library) | `src/gistestbuild-now.txt` |
| `obj/` is committed: 14 tracked files (12 in `Aspose.GIS.FOSS.Tests/obj`, 2 in `Aspose.GIS.FOSS/obj`). Nuance the draft misses: `.gitignore` is not empty, it lists 11 individual `/Aspose.GIS.FOSS/obj/...` files and has no directory rule for `obj/` or `bin/`, so a fresh build leaves `obj/Release/` untracked and unignored | tree, `.gitignore` |
| Aspose pages: `products.aspose.org/gis/net/`, `docs.`, `reference.`, `kb.aspose.org/gis/net/` all 404; `products.aspose.com/gis/net/` and `docs.aspose.com/gis/net/` are 200 | curl GET |
| Provenance hint, stated neutrally: sources contain `ForumLink = https://forum.aspose.com/c/gis` in user-facing error strings and a `DoMeteringLicenseNotification` method; there is no license file. A README must not call this "free" or "open-source" | grep |

## 2. The minimal true README, element by element (greenfield archetype)

Rules used: `data/readme_standard/archetypes/greenfield.yaml`; PRC-07, PRC-04, BTL-GRN-01 to -04, DEF-26, DEF-07; `std-source` channel rule ("that no package is published, in one plain sentence"; the build receipt must name exactly the steps printed). Insertion policy of the archetype: "omit every element whose facts are missing and record why; no placeholder prose".

| Element | Req. | Writable from verified facts? | Content |
|---|---|---|---|
| `identity_h1` | required | yes | `# Aspose.GIS FOSS for .NET` (repo name spells `.Net` and puts a dot before FOSS; the renderer already splits this name wrongly, BC-12 defect noted "not fixed" in DECISION_LOG for GIS) |
| `badge_row` | required | partly | one runtime badge (.NET 10.0, from `TargetFramework`). No license, package, build or contributors badge has a verified target |
| `opening` | required | yes, narrowly | what the source declares (geometries, spatial reference systems, WKT tokenizer and writer, vector layer abstraction from the XML docs) plus the plain sentence that the library does not compile at this revision. No "free", "open-source" or capability verbs |
| `navigation` | required | yes | in-page list |
| `at_a_glance` | conditional (3 verified capabilities) | no | omit: nothing can be verified as working |
| `key_capabilities` | required | weak | only "declared in source" bullets bound to public_symbol facts; no behavioural claim can be bound to a fact (BC-04) |
| `installation` | required | statement only | "No package is published (nuget.org 404 for `Aspose.GIS.FOSS`)". Source steps: `git clone ...`, then `dotnet build ...` with the explicit outcome "fails with 369 errors". A SUPPORTED install command with a build receipt is impossible (the receipt is a failure) |
| `dependencies` | required | yes | runtime: none declared; SDK: .NET 10; development: the five test packages above |
| `quick_start` | conditional (one verified example) | no | omit: the library does not compile, no example can be built |
| `additional_examples` | conditional | no | omit |
| `api_reference` | conditional | yes, short | namespaces and declared type names with XML-doc descriptions, labelled "declared, not compiled" |
| `docs_resources` | conditional | no | omit: the `.org` trio is 404; repository-relative files that help a reader: none |
| `scope_limitations` | required | yes | 369 build errors with the 42 undeclared type names, test project 12 errors and not linked to the library, no package, no example, no tests that can run |
| `enterprise_paragraph` | conditional | arguable | `products.aspose.com/gis/net/` is 200, so the conditional is true under `product_pages.py`; but "naming only what verified facts state it adds" leaves nothing to name beyond the link. LNK-11 (`no_aspose_product_pages`) would drop it; `assignments.yaml` records GIS with `special_structures: []`, which a ruling should confirm (the `.org` pages 404, the `.com` pages 200) |
| `development_testing` | conditional | yes | `dotnet build` (fails, 369), `dotnet build Aspose.GIS.FOSS.Tests` (fails, 12); never a passing claim |
| `third_party_notices` | conditional | n/a | no notices file |
| `license` | conditional on a license file | no | omit; the archetype says the README then "says nothing about a license" and the handoff carries it (owner decision D below) |

Result: H1, badge, opening, Navigation, Key Capabilities (weak), Installation (statement), Dependencies, API Reference, Scope and Limitations, Development and Testing, about 60 to 80 lines. The owner's "standard 10 sections" goal cannot be met honestly: five elements are omitted and three more are thin. BTL-GRN-01 says "not a thin README" when the surface cannot be supported; this is the thin case with a real tree behind it.

## 3. Where the pipeline blocks, and what the right behaviour is

Path today:
- Live-first (`correct-readme`, `components/readme_correction/run.py`): returns `no_live_readme`, writes `status.json`, and defers to "the regeneration lane". Lane L can never serve GIS.
- Regeneration (`present`): processability gate passes. `assess_processability` returns a disposition only when the tree has no manifest and no source suffix; GIS has a csproj and 96 hand-written `.cs` files, so the preflight tool reports `processable=true` and the run proceeds to the model stages (triage board: 1 attempt, 24 provider calls, 4.3 minutes).
- Block: S9 validation, `BC-02` v5, causal stage EXTRACTING, `validation/registry.py::_check_install`: any `install_command` fact whose polarity is not SUPPORTED is a failure ("install_command:dotnet is CONTRADICTED: package registry: distribution not found on nuget"). The fact is CONTRADICTED because NuGet has no `Aspose.GIS.FOSS`.
- The rescue (`evidence/facts/extract.py::_source_build_fact`) promotes a CONTRADICTED install to a SUPPORTED source install only `if build is not None and build.verified and build.command`. `dotnet build` exits 1, so nothing is admitted and the fact stays CONTRADICTED. The repair loop cannot act on an EXTRACTING defect ("after one repair attempt the equivalent failure stands"). Co-failures seen: BC-12 on the product-name split; BC-10/BC-11 never reached.
- Consequence: Lane R cannot reach GIS until upstream builds; Lane L cannot reach it ever without a README. GIS stays at 0 by construction, and the model calls are wasted each attempt.

Is a typed outcome the right behaviour? Yes, for these reasons:
1. `insufficient_evidence` (AGENTS.md, PRC-07) is for README or license-only placeholders and for a tree with no public surface. GIS has a large declared surface, so applying it would misdescribe the evidence.
2. `NON_PROCESSABLE` (STATE_MACHINE section 6, `processability.py`) is defined as no manifest and no source; reusing it for a non-building tree would contradict its own contract. Adding a second reason code (for example `SOURCE_DOES_NOT_BUILD`) is possible but stretches "lacks implementation evidence".
3. `BLOCKED_UPSTREAM(handoff ids, resume predicate)` is what the triage board and `plans/reseal-and-refresh/PLAN.md` (line 479, 805) already call this class; the plan wires its redetect result into `sealing_plan`. The token is plan-level only, no code produces it (`git grep` in `src`, `schemas`, `tests`: no hits).
4. BC-02 as written is correct: the install fact is CONTRADICTED, that is the truth, and the blocker is an upstream defect. Weakening it to let a "not published, does not build" README through is the pattern AGENTS.md forbids ("never weaken a downstream check to hide an upstream defect"). Note that the renderer already has the sentence ("The package X is not yet published on NuGet (...)"), so the content is renderable; the validator is what refuses it, deliberately.
5. Cost of the alternative: shared-code changes in BC-02 (v5 to v6), a new fact shape for a measured failed build (the attribute `SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE` "no build exited 0: ..." already exists on the install fact), the nonexistent greenfield gate (`data/readme_standard` mentions it, no code does), the BC-12 name-split fix, version bumps and negative-control tests, all for one repository.

Suggested mechanism (not implemented, for the owner's register): a deterministic preflight before S5, zero model calls: registry observation CONTRADICTED and no live README and measured build exit != 0 (the facts-only path already runs the build) gives `BLOCKED_UPSTREAM` with the handoff ids and resume predicate "`dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj` exits 0 at a later head, a README or license appears". The existing BC-02 redetector never proposes RESOLVED on a toolchain finding ("a fix is recognised only by a re-run"), so the resume check must be a re-run of the build, which the sealing plan would do on a drifted head.

## 4. Upstream handoffs

| Handoff (fingerprint prefix) | Class | State | Notes |
|---|---|---|---|
| `cd17e99e` build fails | `BUILD_OR_TESTS_FAIL`, trigger BC-02 v5, wave 1b, severity High | HANDOFF_PENDING, CONFIRMED at b9b8c9c7 (2026-10-11) | **Correct the number before filing**: it says 41 of 57 unresolved names are declared nowhere. My recount is 42. The count script matched `class X : AbstractPathInternal` (a base-type use) as a declaration, so `AbstractPathInternal` was wrongly counted as declared. Also, the 369 errors are declaration-stage only; `dotnet build` reported no CS0103 body errors, yet `LocalFilePath`, `SingleStreamPath`, `FormatDriverFactory`, `GisConverter`, `EventableStream` are used in method bodies and declared nowhere, so at least 47 types are missing and more errors will surface after the first 369 are fixed. The text also says `Dataset` is "declared nowhere" without noting `DataSet.cs` exists (a casing mismatch, which helps the maintainers) |
| `9cdfad3e` no LICENSE | `LICENSE_MISSING_ROOT`, wave 3, Low | HANDOFF_PENDING, CONFIRMED | accurate |
| `d0228692` no README | `README_MISSING_OR_PLACEHOLDER`, wave 3, Low | HANDOFF_PENDING, CONFIRMED | if a README is ever authored, this handoff should be withdrawn or closed RESOLVED_UPSTREAM when it merges (BTL-GRN-03 expects the handoff to exist alongside the README, so file order matters) |
| U09 committed `obj/` | `REPO_HYGIENE` | text-only HOLD, no handoff | the registry has no such defect class (needs a G6-W07 admission). Correct the text: `.gitignore` has per-file entries, no directory rule |
| not drafted: test project not linked to library, 12 errors, `MainTests.cs` calls types that do not exist | `BUILD_OR_TESTS_FAIL` | none | could ride in the build issue as a second finding |

Filing gates (approval table `issue-approval-table-final.csv`): registry mode is `dry_run` for GIS (needs `issues_mode: file`, G6-W07), and there is no owner approval record for the exact ids (`issue-approval-ids-wave-1b.txt` lists the build handoff, `-wave-3.txt` the other two). OWNER-20 and D6 (push pause) also hold all product-repository writes.

The BC-02 redetector for the build handoff cites repository paths, so while the head is unchanged it reports the defect as still present; after any commit it is inconclusive until the build is re-run.

## 5. Options

| Option | What happens | For | Against |
|---|---|---|---|
| A. Hold (recommended) | No README. File the build issue first, LICENSE and README issues after, on approval. Add the zero-call `BLOCKED_UPSTREAM` preflight. Regenerate when the build passes | truthful by construction; matches mission ("monitor upstream") and PRC-07/BTL-GRN-01; no shared-code churn for one repo; no stale negative text on a vendor front page; the full standard README becomes reachable the moment upstream builds | GIS stays 0 of 44 until upstream acts; the upstream repo is a two-commit partial import idle for 13 days, so the wait may be long |
| B. Status README via PR | Author the section 2 content (draft in the appendix), seal it, PR it | closes the "every repository has a README" count; tells readers the truth | needs shared-code changes (section 3 item 5) and an owner ruling on negative statements in a vendor repo; goes stale at the next upstream commit (PRC-09 then needs a correction PR each time); five of twelve standard sections are absent so the owner's ten-section goal is not met anyway; blocked from any PR by D6/OWNER-20 and `dry_run` until a per-repository `full` flip and dated authorization |
| C. Issues only, no pipeline change | Same as A without the preflight | cheapest | the pipeline keeps spending 24 model calls per attempt and reports a misleading `FAILED` |

## 6. Decisions for the owner

1. README for GIS now: hold (A) or status README (B)? Recommendation A.
2. Approve filing: the build handoff first (after correcting 41 to 42 and adding the body-level missing types and the test-project finding), then LICENSE and README (Low). The README issue is moot if B is chosen. Registry `issues_mode` for this one repository must also be set.
3. Vocabulary: add `BLOCKED_UPSTREAM` as a real, zero-call typed disposition with a producer (recommended), or give `NON_PROCESSABLE` a second reason code. Recommendation: `BLOCKED_UPSTREAM`; keep `NON_PROCESSABLE` for no-implementation trees.
4. If a README is ever authored: say nothing about the license (archetype rule) or one factual sentence "no license file is present at this revision" (more useful to a reader, deviates from the archetype note). The text must in either case avoid "free" and "open-source".
5. `assignments.yaml` for GIS: keep `special_structures: []` or add `no_aspose_product_pages` (the FOSS-site pages 404, the aspose.com product and docs pages are 200).

## Appendix A: the minimal true README (draft, not for publication; every sentence maps to a fact above)

```markdown
# Aspose.GIS FOSS for .NET

[![.NET 10.0](https://img.shields.io/badge/.NET-10.0-512BD4)](https://dotnet.microsoft.com/download/dotnet/10.0)

Aspose.GIS FOSS for .NET is the C# source of a geographic information system library for .NET, in the
namespace `Aspose.GIS.FOSS`. Its sources declare geometry types (`Point`, `LineString`,
`GeometryCollection`), spatial reference systems (`SpatialReferenceSystem` and its geographic,
projected, geocentric, vertical, local and compound kinds), a vector layer abstraction (`VectorLayer`)
and a Well-Known Text tokenizer and writer (`WktTokenizer`, `WktWriter`). At this revision the library
project does not compile, so none of these types can be used yet.

## Navigation
- [Key Capabilities](#key-capabilities) - [Installation](#installation) - [Dependencies](#dependencies)
- [API Reference](#api-reference) - [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)

## Key Capabilities
- Declared in source, not compiled: geometry types `Point`, `LineString`, `GeometryCollection`.
- Declared in source, not compiled: spatial reference systems and transformations
  (`SpatialReferenceSystem`, `SpatialReferenceSystemTransformation`).
- Declared in source, not compiled: Well-Known Text reading and writing (`WktTokenizer`, `WktWriter`).

## Installation
No package is published: NuGet has no package named `Aspose.GIS.FOSS`. To work from the source:

    git clone https://github.com/aspose-gis-foss/Aspose.GIS.FOSS-for-.Net
    cd Aspose.GIS.FOSS-for-.Net
    dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release

The build fails at this revision with 369 errors; see Scope and Limitations.

## Dependencies
- Required package dependencies: none declared by `Aspose.GIS.FOSS.csproj`.
- Native and system requirements: the .NET 10 SDK (`net10.0`).
- Development dependencies (`Aspose.GIS.FOSS.Tests`): NUnit 4.3.2, NUnit3TestAdapter 5.0.0,
  NUnit.Analyzers 4.7.0, Microsoft.NET.Test.Sdk 17.14.0, coverlet.collector 6.0.4.

## API Reference
The sources declare public types in the namespaces `Aspose.GIS.FOSS`, `.Common`, `.Formats`,
`.Formats.Wkt`, `.Geometries`, `.Operations`, `.Rendering` and `.SpatialReferencing`. (Type table from
the public_symbol facts, collapsed; count taken from the facts, not from this draft.)

## Scope and Limitations
- The library project does not compile: `dotnet build` reports 369 errors. 57 type names are
  unresolved and 42 of them are declared nowhere in the repository (for example `Dataset`, `Polygon`,
  `Projection`, `Renderer`); the namespaces `Aspose.GIS.FOSS.Rendering.Symbolizers` and
  `Aspose.GIS.FOSS.Epsg` do not exist.
- The test project does not compile (12 errors) and does not reference the library project.
- No example has been built, so none is shown. No package is published.

## Development and Testing
    dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj -c Release    # fails, 369 errors
    dotnet build Aspose.GIS.FOSS.Tests/Aspose.GIS.FOSS.Tests.csproj    # fails, 12 errors
```

Omitted with reasons (recorded, not placeholders): At a Glance, Quick Start, Additional Examples, Documentation and Resources, Third-Party Notices (no verified capability, example, page or file), License (no license file). Enterprise paragraph: pending ruling (decision 5).

## Appendix B: reproduction

Scratch clone: `scratchpad/clone/gis` (push URL set to `DISABLED`). Logs: `scratchpad/src/gisbuild-now.txt` (library, 369 errors, exit 1), `scratchpad/src/gistestbuild-now.txt` (tests, 12 errors, exit 1). Handoff JSON copies: `scratchpad/src/gis-defect-*.json`. Probe URLs and statuses are in section 1.
