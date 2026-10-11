# Candidate README Contract

> **Superseded in part, 2026-10-11.** This document is not the structure and composition standard.
> By the owner directive of 2026-10-11 the standard is the live upstream README of each repository,
> and `docs/README_STANDARD.md` defines it: the common schema, the product-wise differences schema,
> the improvement rules and the migration plan. **Section 2 below** (the semantic shell table and the
> prose after it) is superseded and is kept only as the legacy encoding of what the code does today
> (`SEMANTIC_SHELL`, BC-07, the renderer) until the gates are migrated (`README_STANDARD.md`
> section 6); do not edit it to track a live README, change the standard instead. Section 2.1 (At a
> Glance topology) is an owner rule and stays. **Section 8** (prose rules) now binds only text a
> change adds; `README_STANDARD.md` section 3.5 re-bases it on the live tone. Sections 1 and 3 to 7
> keep their authority, amended as `README_STANDARD.md` section 6.1 lists.
>
> **Owner rulings R1 to R7, 2026-10-11** (`README_STANDARD.md` section 7, `docs/DECISION_LOG.md`).
> Where the legacy text below conflicts with them, the ruling governs and the text is history, not
> to be repaired: the linked banner of row 3 is not promotion before the product is explained
> (§1 and `plans/idea.md`, R1); the anchor of row 18 reads `Aspose.{Family} for {Platform} — Enterprise
> Edition` and never opens "full-featured", so BC-06's prefix check is void (R2); Enterprise Edition
> is the only name of the aspose.com product, with no exception (R3); the maintainers' tone, prose
> structure and headings are followed (R4); the "Deliberate product-specific sections" paragraph
> and its plan `deviation` give way to inherited additions retained in place beside a fixed core
> (R5); row 7's three-to-eight cap and the 320-line visible budget are void, the badge order of row
> 2 binds added badges only, and a README documents the release (R6); the `flowchart TD` of §2.1
> and BC-07 gives way to a diagram that never clips a label and runs left to right, accepted by a
> real render (R7). The code that still encodes the replaced wording is owner-ruled, pending the
> next governed cut (`README_STANDARD.md` section 6.2).

Status: normative for every candidate. Version 1 froze as `readme-contract-v1` at G3 exit
(G3-W02, 2026-10-01 — deferred past the originally-planned G2 exit while G3/G4's own multi-cohort
work was still in flight, per the flip-timing paragraph below); it now changes only at a declared
version boundary with regression evaluation across every current candidate. Every bundle's
`dependencies.json` names the version it was built against. [2026-10-04 correction: only the two version constants froze. The 30-point criterion profile named in the flip paragraph and in section 5 is NOT implemented (no scorer in `src/`), and G3 is not yet accepted, so "at G3 exit" is premature. See `project/state.yaml` G3-W02.]  
**Revision discipline (2026-09-03, hold met 2026-09-04):** this draft was revised three times in two
days ahead of any candidate sealing against it — the legacy pattern of the target moving faster than
output — and was held until one did (G2-W02 sealed at `65b1f577`). The discipline stays: a change
enters only as a coherent fix to a predicate that a sealed candidate's defects proved insufficient,
never as a new requirement ahead of output. The 2026-09-04 revisions are three such fixes — check 4's
slot binding, check 4's title support (G2-W13, the defect measured in §27.2 RC2), and row 14's
uniqueness — each traced to a verified defect in `RESEARCH_AND_GUIDELINES.md` §26 or §27. The
2026-09-05 revisions are the fourth and fifth, both G2-W16's and both landed with their code in
the commit that made them true: §6's demotion rule (the defect measured in §27.2 RC5: acceptance
depended on `repairs.json`'s directory history, not on content), and §6's zero-advisory rule for
required rows, which check 10 now judges — its version moves to 2 with the sentence. §25 records
the reasoning for the discipline itself. A sixth landed on 2026-09-05 with G2-W17's code: §6's
absence claims name text the code looks for, and a refuted finding is not deferred work (§27.8,
§31). A seventh landed on 2026-09-07 with G5-W02's code: check 11 names what it actually proves -
a fresh process alone was never enough, since a second local run always finds the same machine's
gitignored `runs/` directory still populated from the first, the exact gap `RESEARCH_AND_
GUIDELINES.md` §27.2 RC4 measured; the check now names an empty `runs/` too. An eighth landed on
2026-09-16 with G4-W17 arrival item 54's code: row 10's Quick Start is conditional on a verified
example rather than Required (the 2026-09-06 20:05 DIRECTIVE, rules 2 and 4 - one unverifiable
example never blocks a candidate, and a row nothing can honestly fill is omitted, never fabricated;
measured on Aspose.Words for .NET, whose five README examples are all CONTRADICTED and whose plan
therefore could not exist), with the shell, the planning schema and its checks moving in the same
commit; measured against every sealed candidate, each carries a verified quick start, so the
condition holds for all twelve and no sealed byte moves. Pending revisions,
each traced to a measured defect in §27 and carried by a named work item — a new check 12 only
when a sealed candidate exhibits a required-row coverage gap (none does at `65b1f577`; expected
from the G3 cohort, per loop-prompt §6 rule 14) — are specified in `RESEARCH_AND_GUIDELINES.md`
§27.8 and enter this document only in that item's commit, together with its code and tests.  
**Flip landed (G3-W02, 2026-10-01; prep recorded 2026-09-10 as PHASE0/PA-05):** `bundle/seal.py`'s
`CONTRACT_VERSION` is now `"readme-contract-v1"` and `ACCEPTANCE_PROFILE_VERSION` is `"1"` — the
two-line diff PA-05 specified, applied exactly as recorded, with the same two matching assertions
in `tests/components/readme/bundle/test_seal.py` updated alongside. `evaluation.py`'s own
exact-value comparison reopened every currently-sealed candidate's `VALIDATING`/`REVIEWING` stage
the moment it landed, as PA-05 always said it would; G3-W02 re-sealed each one in the same work
item rather than leaving the reopen to trickle in — see `DECISION_LOG.md`, this date, for the
per-candidate record. Contract revisions from here follow the same convention every other
component version already uses (`RENDERER_VERSION`, `SHELL_VERSION`, etc.) — a plain
incrementing value, bumped only when a blocking check's own *meaning* changes (a `BC-*` predicate
now judges something new or different), never for a same-meaning bug fix or prose clarification;
the existing "check 10 now judges... its version moves to 2" precedent above is the pattern to
keep following, not a one-off.  
Authority: `plans/idea.md` decides what a README must be; this document implements it; the
aspose.org candidates and the live READMEs they produced are an oracle for what is achievable and
how a reader receives it — evidence to check against, never a third authority (`EXECUTION_STATE_MACHINE.md`
principle 9). When the two disagree, the loop decides on first principles, records the decision and the
alternative it rejected as `PROVISIONAL` in `DECISION_LOG.md` §31, and continues; the owner
may reverse it asynchronously; the settled decision is written once, here.  
Derived from: `plans/idea.md` (Portfolio README Presentation Contract and standing constraints),
`RESEARCH_AND_GUIDELINES.md` §4 to §7 and §24, and the legacy template registry pulled as an asset.  
Owns: the candidate's required shape, how content is assembled, which decisions are agentic, and
which checks block. `EXECUTION_STATE_MACHINE.md` G1 builds to this document.

## 1. Outcome

A visitor understands within the first screen what the product does, who it is for, which formats
and capabilities it supports, how to install it, how to run one working example, and whether it is
maintained. Product before promotion; Aspose links only where they help the reader. Concise where it
is read: the default policy budget is 320 visible lines (outside `<details>`); content inside a
collapsed block — above all the complete public API reference, which most FOSS repositories have
nowhere else — is unbounded but every line of it is verified. No synthetic prose, no mechanically
generated descriptions. The legacy candidate that split an identifier into "A3 D Object" and padded
its reference with unverified filler is the failure this contract prevents; a long, verified,
collapsed reference is not (`RESEARCH_AND_GUIDELINES.md` §24).

## 2. Document structure: semantic shell v1

Sections appear in this order. `Required` sections may not be omitted; `Conditional` sections are
omitted only when their condition is false, and the plan records why. `Owner` says who produces the
content: `D` deterministic renderer from facts, `L` LLM content units bound to fact IDs, `M` mixed
(LLM selects or describes, renderer emits every identifier, command, link, and code block).

| # | Section id | Heading | Required | Visibility | Owner | Content |
|---|---|---|---|---|---|---|
| 1 | `identity` | complete canonical product name | Required | visible | D | Exactly one H1, the full product name (for example `Aspose.3D FOSS for Python`), never a package or namespace shorthand. |
| 2 | `badges` | none | Required | visible | D | One row, from a badge registry keyed by ecosystem — never a Python-only hardcode. In order (the order is a blocking check, BC-07), each only when its target is verified: package-registry version (PyPI, Maven Central, NuGet, npm, crates.io; pkg.go.dev reference for Go), language or runtime floor from the ecosystem spec's floor fact (`EcosystemSpec.runtime_badge`: Python, .NET target framework, Java release, Go version, C++ standard, Rust edition, Node engine; an ecosystem with no floor fact has no runtime badge), real CI status only when extraction found a push-triggered build or test workflow in the clone (`link_target:badge.ci`, from `evidence/facts/assets.py`; the workflow file and its branch come from the workflow itself, never a guessed URL), license, contributors only when the source README's own contributors target resolved (a `link_target` fact for `https://github.com/{repository}/graphs/contributors`). Floor: the license badge whenever a license file exists plus at least one more verified badge when any is available. Omit a badge whose target is unavailable; never duplicate, split into two rows, or fabricate: BC-07 rejects a badge no fact supports, a repeated slot, and any out-of-order row. |
| 3 | `banner` | none | Conditional: a verified product illustration and homepage exist | visible | D | Linked image immediately below the badge row: `[![alt](image_url)](homepage_url)`, alt text naming the product. Both `image_url` and `homepage_url` come from verified facts, never a guess or a placeholder graphic. Omit entirely when either is unresolved — never an unlinked image, never a broken link. |
| 4 | `opening` | none | Required | visible | L | Two to four sentences: what the product is and does, as its own actions, and the problems it solves where a fact states them. An audience, use case, suitability, or spared cost ("developers use it to ...", "used by ...", "enables developers to ...", "ideal for ...", "without requiring a license") appears only when an accepted fact or a preserved inherited unit states it (`composition/audience.py`, enforced by check 4); the platform, license, and runtime are not an audience. No Aspose promotion, no marketing superlatives. |
| 5 | `navigation` | Navigation | Required | visible | D | An explicit `## Navigation` heading, then a compact list of in-page links to the visible headed sections actually present, in document order. |
| 6 | `at_a_glance` | At a Glance | Conditional: at least three verified core capabilities | visible | M | Exactly one Mermaid fence and nothing else (§2.1). Starting Points appear only when a verified input format exists; a product that creates from scratch still gets the diagram, without them. |
| 7 | `key_capabilities` | Key Capabilities | Required | visible | L | Three to eight items. Each title is an action-led natural phrase grounded in facts; each description is one sentence naming the real classes or members it rests on. A capability with a known limitation says so inline with a link to Scope and Limitations rather than overstating. At most one search-intent keyword per title, with an output-lineage record; no keyword repeats across titles. |
| 8 | `installation` | Installation | Required | visible | D | Verified install for the ecosystem's package manager from manifest plus package-registry observation, in every idiomatic form the ecosystem uses, each in its own fenced block (Maven and Gradle for Java; pip for Python; `go get`; `cargo add`; `dotnet add package`; npm); then the verified source install as a fallback (clone, then build or editable install); then a one-line verify command when the ecosystem has an idiomatic one (an import or version print); then one sentence on supported runtimes from manifest facts. Never an unverified command. State plainly when the package-registry observation shows the package is not yet published, rather than presenting an unqualified install command the registry itself contradicts. When the registry's own answer is that nothing is published (a 404, an empty Go version list, crates.io or Maven Central "not found") or the ecosystem has no registry, and the maintainers' own README says the package is unpublished, the install is the source checkout: the clone, then a measured build when one exited 0 at this revision, else the build the repository's own workflow, script or toolchain names, stated as not run here (`install_kind: source_checkout`, `source_basis: documented`); no registry install command is printed for it. A registry that could not be read admits none of this (it is retried, not reported as an absent package). |
| 9 | `dependencies` | Dependencies | Required | visible | D | From the dependency snapshot, in four subsections in this order — Required Package Dependencies, Optional Dependencies, Native and System Requirements, Development Dependencies. Optional, Native and System, and Development omit silently when their own bucket is genuinely empty; Required omits only its bullet list, rendering the fixed sentence "No required third-party package dependencies." plus the manifest evidence in one clause, instead of vanishing, so a reader can never mistake verified-zero for generation forgetting the section. Never a flat, unstructured list; never merged into Installation. |
| 10 | `quick_start` | Quick Start | Conditional: at least one example executed or compiled in isolation at this revision | visible | M | One or two minimal examples, each executed or compiled in isolation and each introduced by one lead-in sentence: when the product reads files, the first opens an existing input; when it creates them, one builds from scratch. Correct fence language, normalized spacing. |
| 11 | `feature_showcase` | Feature Showcase | Conditional: the existing README carries a verified, repository-owned visual proof of capability the plan preserves | visible | D | A linked preview image (`[![alt](preview)](full asset)`) with alt text naming what it shows, repository-relative, resolving against the snapshot tree; one sentence of context may follow. Never a stock or generated graphic. |
| 12 | `additional_examples` | Additional Examples | Conditional: at least one further verified example, or a verified repository-owned image the plan preserves | collapsible | M | One lead-in sentence; one flagship example visible under its own task-named `###` heading when the plan selects one; then a single `<details><summary>View Additional Examples</summary>` block holding every further verified example, each under its own real, unique, task-named `###` heading — never "Example N", never a heading reused. A one-sentence explanation may precede a block when the code alone would not make the task obvious. A code comment that records a real, verified API gotcha is kept, not stripped. Verified repository-owned images from the inherited README (screenshots, rendered outputs, generated previews, embedded data-URI images) are preserved here under their own descriptive `###` heading with alt text, resolving against the snapshot tree — never excluded on the ground that no section exists for them. |
| 13 | `project_structure` | Project Structure | Conditional: the existing README carries a repository tree the plan preserves | visible | D | The preserved tree rendered with canonical box-drawing characters (`├──`, `└──`, `│`) regardless of the source's own style; every path resolves against the snapshot tree or the unit is corrected with evidence, never carried stale. |
| 14 | `api_reference` | API Reference | Required | collapsible | M | Most FOSS repositories carry no dedicated reference, so the README is it. A visible one-to-two-sentence intro naming the real entry-point classes, how they relate, and the verified public type count; then a single `<details><summary>View the Complete Public API Surface</summary>` block holding the complete verified public surface: a `### Core API` table (`\| Class \| Description \|`, every name in a code span) covering every verified public type exactly once — keyed by its canonical defining location, so a package re-export and the class inside a same-named module are one row, never two — split by kind where the ecosystem warrants (`#### Enumerations`, `#### Interfaces`, `#### Structs`, `#### Traits`), then `#### Detailed Member Reference` with `### <Topic>` groups listing the hub types' verified members as nested bullets. Every description is evidence-backed from the symbol's own documentation or signature; a type with no verifiable description gets its verified signature summary, never an invented sentence and never mechanical filler ("class with N methods", "extends Exception"). A documentation summary with a lost or cut word ("Base class for  and") is not a description, and is treated as no documentation. A member is listed only with its own documentation summary: one with none, or only a constructor's stock "Initializes a new instance of the X class." sentence, is left out rather than described by its signature ("Defined as `string`."). Inherited API content the plan places here renders inside the same block, deduplicated, never outside it. Depth scales with the surface; the table is deterministic from the verified public-symbol facts and the LLM owns only the intro, the topic grouping, and description wording bound to fact IDs. |
| 15 | `documentation_resources` | Documentation & Resources | Conditional: verified relevant targets exist | visible | M | One list, each item a bold link, an em dash, and one sentence on what it covers: the verified documentation, knowledge-base, and reference targets (the reference item states the verified public type count and points to the in-page API Reference for the essentials); repository-relative links to verified tracked docs when they exist (a publishing or contributor guide, implementation notes, labeled as such); and a closing "Found a bug or have a feature request? Open an issue" line to the repository's issues page. Aspose links within the configured or derived ceilings. Never the same target twice. |
| 16 | `scope_limitations` | Scope and Limitations | Required | visible | L | A bulleted list of designed or declared limitations, each naming the precise mechanism a fact records (an exact exception type, a named unimplemented class or method) — never a vaguer paraphrase ("raises an exception") when the fact is more precise ("raises `NotImplementedError`"). At most one scope sentence before the list, only when it says something the bullets do not; never a prose paragraph restating them. When nothing traces to a public source, omit the list rather than invent filler. Transient defects (a package that fails to import at this commit, a broken build backend) are never limitations. The section closes with the Enterprise Edition paragraph (row 18). |
| 17 | `development_testing` | Development and Testing | Conditional: build or test assets exist | visible | M | Prose with fenced commands from the actual build files and CI: install or build and run the suite; a single-target run when the ecosystem has one, copied exactly from its verified example fact, never approximated; one sentence sizing what the suite covers when a test-file count is verified; a release sentence linking the workflow one of whose steps publishes a package, uploads release assets or creates a release (`build_test_asset:release-workflow`), and no release sentence when no workflow has such a step (a file name proves nothing). The renderer prints, from the clone's own files, the build command and the test command (`build_test_asset:build-command` and `:test-command`: a non-release workflow `run` step, else a `package.json` script, a `Makefile` target, the standard command of the toolchain manifest at the root - `test` only when the tree shows tests - and last a release workflow's step) as one fenced `bash` block after the sentences. A workflow command is read from one job's own steps, never a sanitizer, coverage, benchmark, documentation, package-test, minimum-toolchain, release or package job (outside a release workflow), never a step in another directory or under shell control flow, and a command that works in a build directory only when the same job configures that directory earlier with one unconditional `cmake -S . -B <directory>`, which the block prints first; otherwise no command is named. A command that needs a tool the project does not declare prints its precondition first (`pip install build` for `python -m build`). Any command, and any precondition, the README already shows in an equivalent form anywhere (a code fence or inline code: same program, subcommand words and target, however spelled) is omitted. One sentence puts the operating systems and runtimes of the CI matrix (`build_test_asset:ci-matrix`) in words ("on Ubuntu and Windows, with Python 3.10 and 3.12"), never as workflow keys. Representative assets are named in prose, never as a bare directory list. Never collapsed. |
| 18 | `enterprise_relationship` | none (closing paragraph of Scope and Limitations) | Conditional: a verified aspose.com product target exists in policy | visible, below the fold | M | The final paragraph of Scope and Limitations, separated from the bullets by a blank line, never inside a bullet: one or two sentences of the shape "These limitations don't apply to [full-featured Aspose.{Family} for {Platform} — Enterprise Edition](url), which adds …" (the anchor text is renderer-owned: `plans/idea.md` asks for "an informative **full-featured ... Enterprise Edition** anchor below the fold", and BC-06 rejects a link to the verified target whose text does not open "full-featured" and end "Enterprise Edition"), naming what the Enterprise Edition adds from verified facts or policy, never invented. "Enterprise Edition" is the only edition name anywhere in the document, and it appears exactly once. A family-level target names no platform at all; a platform-level target names exactly the one real platform and never the resolved URL's own implementation detail (a compound or bridge slug never surfaces in the anchor or surrounding prose). Omit the paragraph entirely on an unresolved target — never guess a platform or fall back to a family link for convenience. |
| 19 | `third_party_notices` | Third-Party Notices | Conditional: the file exists | visible | D | Repository-relative link with normal link text, not code styling. |
| 20 | `license` | License | Required | visible | D | Prose declaration from the license fact: "This project is licensed under the [<name>](<path>)." then, for a permissive license such as MIT, one sentence of practical permissions and the notice condition, and that the software is provided without warranty. Never a bare link, no README-level copyright line unless portfolio policy enables it. |

**Deliberate product-specific sections.** The live portfolio is one shell with a small, evidenced set
of additions, not a rigid template: across all 32 published candidates the only sections outside the
standard set are Project Structure (4), Third-Party Notices (2), and Feature Showcase (1), each present
because the repository genuinely carries that material. The same rule holds here: `presentation_planning`
may include a section beyond the required set only to preserve a material inherited section the shell
has no better destination for, or to present verified repository-owned assets — recorded as a plan
`deviation` naming the unit or asset IDs it rests on, placed at its row's position above. Never a
promotional, "Other platforms", or implementation-label section (those stay in the list below). Within
a section, depth varies by product too: an API Reference with 11 types and one with 1,026 both follow row
14; a product with 49 verified limitations lists 49.

Headings use title case, with the exact strings in the table above (including the ampersand in
"Documentation & Resources"), so anchors stay stable across the portfolio. Technical abbreviations
use their canonical forms, uppercase where the standard is uppercase (PDF, XLSX, HTML, PS, EPS, XPS)
and mixed where the standard is mixed (glTF, npm) — never "Gltf" or "GLTF" in a heading. Exact
package names, paths, imports, namespaces, API members, commands, and link destinations keep their
source spelling inside code spans.

Never present: an "Other platforms" or promotional section, internal assurance narration (source
revisions, provider calls, validators, evidence, isolated-build conditions), the label "Preserved
repository details" or any other implementation label, a repeated capability inventory in two
sections, a non-canonical edition name, a split identifier such as "A3 D Object", a phrase
disclosing that one platform's implementation depends on another ("via Java", "a wrapper around
X", "backed by X", "implemented through X" — a real, confirmed defect class on this exact
portfolio; `RESEARCH_AND_GUIDELINES.md` §19), or an unscoped absolute dependency claim ("no
dependencies", "dependency-free", "no external runtime") unless the same clause names the exact
dependency class it excludes and the `dependencies` fact record actually proves it.

### 2.1 At a Glance topology

Inputs are verified input formats, never selector parameters. Outputs are verified output formats,
never intermediate structures or delivery methods. The diagram is one chain: a `Starting Points`
group holding a single node that lists the verified input formats ("An existing OBJ, STL, or 3MF
file"), the product node, the `Core Capabilities` group, and an `Outputs` group holding a single
node that lists the verified output formats — connected by exactly one edge per hop
(`StartingPoints --> PRODUCT --> Capabilities --> Outputs`); `Starting Points` is omitted, with its
edge, when no input format is verified, and `Outputs` likewise. Individual capabilities never fan
out to the product or to outputs; no per-format node edges. The blocks run left to right
(`flowchart LR`: Starting Points, the product, Core Capabilities, Outputs), each group a column of
boxes in reading order, split by key capability. Up to five capability nodes form one column; six
to eight form two balanced columns, side by side. Every label is geometry-safe and every box
grows with its text: labels are SVG text (`htmlLabels: false`), wrapped by one character-width
model into lines inside one pixel budget per diagram, so no word is wider than the budget and no
label wraps past four lines - a longer title is shortened at planning, never clipped at render.
No custom styling directives. The drawing is `components/readme_diagram`'s, shared with the
live-first correction path; the diagram is accepted by its own structure and width model and, in
tests, by a real render (README_STANDARD.md STR-28, owner ruling R7). The LLM
chooses which verified formats and which core capabilities appear; the renderer owns every node,
edge, and label.

## 3. Assembly pipeline

The LLM never writes Markdown and never writes the document. Each agentic job returns typed content
bound to fact IDs; the deterministic renderer assembles the document from the shell, the plan, the
units, and the facts. Claim accountability is therefore structural, never substring matching on
rendered prose.

| Stage | Owner | Input | Output artifact |
|---|---|---|---|
| S1 Snapshot | D | registry entry, default branch | `source/`: pinned revision, exact README bytes, tree inventory |
| S2 Facts | D | snapshot | `facts.json`: typed records `{id, kind, value, evidence[], polarity, confidence}` |
| S3 Investigation | L | bounded fact dossier | `investigation.json`: interpretation fields, each citing fact IDs |
| S4 Reconciliation | L | inherited units, facts, investigation | `dispositions.json`: exactly one disposition per inherited unit |
| S5 Planning | L | facts, investigation, dispositions, shell, policy | `plan.json`: section inclusion and every selection (§4) |
| S6 Authoring | L | per-section fact packets from the plan | `content_units.json`: `{section, slot, text, fact_ids[]}` |
| S7 Render | D | shell, plan, units, facts, dispositions | `README.md`, `README.patch` |
| S8 Coherence | L | the rendered document | revised LLM-owned units only, once; then re-render |
| S9 Validation | D | README, facts, plan, units, dispositions | `validation.json` |
| S10 Review | L (separate identity) | README, facts, plan, dispositions, validation | `review.json` |
| S11 Repair | L, bounded | typed defect | revised outputs of the causal stage, at most once per fingerprint |
| S12 Seal and no-op | D | all artifacts | `manifest.json`, `dependencies.json`, `calls.jsonl`; fresh-process replay |

Fact kinds at S2: `identity`, `package`, `install_command`, `import_path`, `public_symbol`,
`example` (with its verification receipt), `format` (direction input or output), `capability`,
`dependency`, `license`, `third_party_notices`, `build_test_asset`, `link_target` (verified), and
`inherited_unit` (heading, paragraph, list, code block, badge, or link of the existing README with a
stable ID). Every record carries its evidence paths and a polarity (`SUPPORTED`, `CONTRADICTED`,
`UNRESOLVED`).

Content units at S6 are plain prose. They contain no Markdown structure, URLs, commands, or code;
every identifier they mention must be a fact value, and the renderer wraps it in a code span. A unit
with an unknown fact ID, a contradicted fact, or an unlisted identifier is rejected before render.

Inherited units at S7: `VERIFIED_PRESERVE`, `VERIFIED_REWRITE`, `VERIFIED_MOVE`, and
`CORRECT_WITH_EVIDENCE` units are placed in their destination section; `SUPERSEDE_REDUNDANT` and
`OMIT_UNSUPPORTED` carry evidence in the dispositions file; `DEFER_UNRESOLVED` units are never
rendered and are judged by cause in `validation/deferrals.py`: a BLOCK cause fails BC-05 at its
causal stage, an ADVISORY cause is recorded in `validation.json`'s `advisory` list for reviewers,
and a cause no registered class recognises blocks. `NON_CONTENT` is ignored. A material unit with
no safe destination fails the transaction closed instead of being dumped.

**Placement is exclusive, never additive, on fact-ID overlap (a real, confirmed defect: the G1
canary's own `scope_limitations` rendered three `VERIFIED_PRESERVE`d inherited paragraphs in full
*and* three independently-authored `material_limitations` bullets covering the identical facts —
caught by `independent_review`, survived one `targeted_repair` attempt because the defect is in
render placement, not in either unit's own prose, so no content revision could ever fix it).
Reconciliation (S4) decides a unit's disposition before planning (S5) exists, so it cannot know in
advance whether planning will independently select the same `fact_ids` for fresh authoring — S7 is
the first point both are known simultaneously, and owns the conflict: before placing a
`VERIFIED_PRESERVE`/`VERIFIED_MOVE`/`CORRECT_WITH_EVIDENCE` unit into a section, the renderer drops
it if its `fact_ids` intersect the `fact_ids` of that section's own plan-driven content
(`material_limitations`, `links`, or any future such field) for the same section; the planned,
freshly-authored content wins, since it is what evidence-bound content-unit validation (§3) already
checked. No section may show the same material twice regardless of which stage produced each copy.

That exclusivity holds only if the planned content really states what it drops, so a dropped list is
owed in full (wave-3 acceptance review of reseal `f69f75c7`, LST-01: one shared fact dropped a whole
list while the section stated half of it, and BC-05 passed every such unit). A `VERIFIED_PRESERVE`/
`VERIFIED_MOVE` list unit with two or more items that the plan hands to a limitation slot
(`unit_ids`) is also dropped, never printed beside the bullets authored from it (Cells .NET stated its
Scope list twice). Planning completes the hand-off: every `link_target` fact such a list cites into
Documentation and Resources joins the plan's `links` when the plan already carries one of them, and
a list placement drops from Scope and Limitations is added to every limitation's `unit_ids`. The
authoring objective names those lists so the units fold their items in where they fit, but authoring
does not refuse a reply that leaves one out (wave-4 triage, cause 1: a list longer than its slots,
or an item naming an identifier no fact spells, made the refusal unsatisfiable): placement prints
every item the section does not state, as written, and BC-05 fails the candidate naming each item the
rendered section still does not state — by the link it carries in Documentation and Resources, by
the item's own words elsewhere (`list_coverage.missing_items`, the one test placement, BC-05 and the
objective share: an item is stated when the section holds half the words of its lead or half the
words only that item says, so a bold label the composer folds into its sentences is not the item).

Two more placement rules, both from the same G1 canary bundle: a placed unit inherits its section's
visibility — in a `collapsible` section it renders inside the section's `<details>` block after the
composed content, never appended outside it (17 inherited API units landed visible below a closed
`</details>` as a 58-line uncollapsed block, outside the reference they belonged in). And a placed unit whose
destination section the plan excludes is not silently dropped: reconciliation re-routes it to a
destination the plan includes, or the transaction fails closed naming the unit — the same standard
as a unit with no safe destination (one `VERIFIED_PRESERVE` unit was routed to `at_a_glance` while
the plan excluded that section, and vanished).

A kept unit belongs to the section its topic belongs in, and the renderer's own sections are not
printed twice (wave-6 acceptance reviews, cause 4: 124 install and dependency units, 15 licence
paragraphs and 17 API listings filed in sections whose rows (§2, 7, 10, 15, 16) hold capabilities,
one example, links or limitations). The topic is read from the unit's source heading
(`composition/source_topics.py`). S4 moves a unit about installing, building or the API out of a
section that has no place for it to the topic's home (`destinations.rehomed`: Development and
Testing for install and build material), and placement then reads a unit about installing against
the Installation and Dependencies text, and one under the licence heading against the License
text, as a second place that may state it: a sentence, a list item or a block those sections already
state is not printed again (`coverage.uncovered`, `coverage.uncovered_block`), a release number
never makes two declarations different, a shell command or a link is still demanded as the unit
spells it (BC-08, BC-06), and a lead-in follows its block's fate. A unit no fact ties to its
destination is judged against those renderer sections only. The must-carry gate does not owe an
authored unit what a kept unit in the same section already states (`authoring.carried_units`).

## 4. Agentic decisions

Judgment belongs to the LLM where a fixed rule cannot decide. Every decision is bounded by a typed
output and a deterministic guard.

| Decision | Job | Output constraint | Deterministic guard |
|---|---|---|---|
| What the product is, who it is for, which problems and workflows the repository evidences | `repository_investigation` | Every statement cites fact IDs | Unknown ID rejects the output |
| Which inherited README units to preserve, rewrite, move, correct, supersede, omit, or defer, and where they go | `source_reconciliation` | Exactly one disposition per unit; evidence for correct and omit | Missing or duplicate dispositions reject; a material unit without destination fails closed |
| Which conditional sections to include and which deliberate additions (§2) a preserved unit or asset justifies, which three to eight capabilities are core, which formats appear in At a Glance, which example is minimal, which is the visible flagship, and which are additional, which types are the entry-point hubs the API Reference intro and Detailed Member Reference lead with and how the complete surface groups by topic, which limitations are material, which verified links help which section, any justified deviation | `presentation_planning` | Only fact, example, symbol, unit, and link IDs; required sections cannot be omitted; the API table itself is not a selection — it is the whole verified public surface | Selections outside the fact set reject; ceilings and column rules enforced at render |
| How to phrase the opening, capability titles and descriptions, lead-ins, limitation prose, resource prose, development summary, Enterprise Edition context | `section_authoring` | Plain prose units with fact IDs | Renderer rejects unknown IDs and unlisted identifiers; length budget enforced |
| Whether the whole document reads as one coherent developer journey | coherence pass of `section_authoring` | Revised LLM-owned units only, once | Deterministic blocks unchanged |
| Whether the candidate is factually sound, complete, specific, and visitor-useful | `independent_review` | One verdict from `ACCEPT`, `REJECT_FACTUAL`, `REJECT_PRESERVATION`, `REJECT_PRESENTATION`, `REJECT_EXAMPLE`, `REJECT_LIMITATIONS`, `REJECT_LINKS`, `REJECT_COHERENCE`, `INSUFFICIENT_EVIDENCE`; each finding names a section and a causal stage | Reviewer never authored the candidate; unrepairable findings become advisory |
| How to fix a typed defect | `targeted_repair` | Revised outputs of the named causal stage only | One attempt per equivalent fingerprint; then change mechanism |

Deterministic code alone decides: admission and processability, snapshots and hashes, fact
extraction and verification, every command, link, badge, code block, diagram, identifier, and
license statement, validation, sealing, no-op proof, and state.

## 5. Blocking checks

Exactly these block acceptance at G1. Everything else is advisory until contract v1 freezes.

| # | Check | Sections |
|---|---|---|
| 1 | Source revision pinned; original README bytes exact; every fact carries evidence | all |
| 2 | Install command verified against manifest and package-registry observation; or the source build a receipt proved; or, for a package the registry answers is unpublished that the maintainers' README also calls unpublished, the documented source checkout (`evidence/facts/unpublished.py`). A registry that could not be read (`RETRY_REGISTRY_READ`) and a package it lists as absent without that corroboration (`PACKAGE_ABSENT`) refuse as different causes; a README never prints the registry install of an unpublished package; a registry-less install is not refused for being unresolved when the Installation states a registry-confirmed distribution and prints no command | `installation` |
| 3 | Every rendered example was executed or compiled in isolation at this revision | `quick_start`, `additional_examples` |
| 4 | Every content unit's fact IDs exist, are `SUPPORTED`, and lie within the fact set the plan assigned to that unit's slot — a capability description cites its own title's facts, never another slot's, and the capability's title is supported by the facts its unit cites; every identifier in prose is a fact value in a code span; an `opening` sentence that names an audience, use case, suitability, or spared cost is refused unless an accepted fact of that section states the same claim (`composition/audience.py`) | `opening`, `key_capabilities`, `scope_limitations`, `api_reference`, `documentation_resources`, `enterprise_relationship` |
| 5 | Every material inherited unit has exactly one disposition; placed units appear in their destination | all |
| 6 | Every link resolves; Aspose links are contextual and within the ceilings derived for this document (total, `aspose.org`/`aspose.com`, and `products`/`docs`/`kb`/`blog`/`reference` slots, from its visible content size and verified examples, or the configured maxima; `composition/link_budget.py`); "Enterprise Edition" is the only edition name (no substitute such as "commercial edition" or "paid version", in any letter case — `plans/idea.md` L51-53); no unsafe raw HTML (`<script>`/`<iframe>`/an event-handler attribute, or a `javascript:` or `vbscript:` scheme at a URL position - a link or image destination, a reference definition, an autolink, or a URL-bearing attribute value; prose that merely contains the words is not a URL) renders outside a fenced code block | `documentation_resources`, `enterprise_relationship`, `badges` |
| 7 | Exactly one factual H1; one badge row in the stable order, each badge supported by a verified fact; title-case headings of every level; canonical abbreviations in prose and headings; At a Glance topology, column rules and label geometry (the horizontal drawing; no label wraps past four lines at the line budget); every code fence carries a language and no empty-line run appears in the document or an example; no section the shell marks visible renders inside `<details>`; no internal narration; within the visible-length budget (content inside `<details>` is unbounded but verified) | structure |
| 8 | Protected content preserved | all |
| 9 | No configured secret in the bundle | bundle |
| 10 | Independent review returns `ACCEPT` with the reviewer identity separate from authoring, and no advisory is left on a required row (§6) | review |
| 11 | Fresh-process rerun from an empty `runs/` directory is byte-identical with zero provider calls | bundle |
| 12 | Every product-name position in the prose spells the registry's canonical product name exactly (row 1 of §2; `plans/idea.md` L84-85): no separator, case, or suffix variant such as `Aspose.3D.FOSS` for `Aspose.3D FOSS for .NET`; exact technical identifiers stay in code spans, or beside a package/namespace/version cue | all |
| 14 | A package version, install command, or publication statement matches the facts (`validation/claims.py`): a version attached to the package name or an install command (`name==1.2`, `name@1.2`, `group:artifact:1.2`, `name version 1.2`, `--version 1.2`) equals the registry's current stable release (`package:published_version`, present only when the registry answered conclusively) or, with no such fact, the manifest's `package:version`; a sentence saying the package is "not (yet) published" is flagged only when a registry reading lists it; an install command's package is the package identity fact (`package:name`), and a near-miss such as `aspose-note` for `aspose-note-foss` is refused, while an unrelated package or a declared dependency is not. An unreadable registry yields no `published_version` fact and an advisory note, never a failure | all |

Advisory at G1, candidates for v1 blocking at G2: search-intent lineage per title, prose quality
(sentence length, hedges, superlatives), navigation completeness, badge floor, dependency claim
accuracy against the `dependencies` fact record (the unscoped-claim rule above names the shape;
this is its check), a fidelity score naming missing words for a `VERIFIED_REWRITE` disposition
(never just its category — `RESEARCH_AND_GUIDELINES.md` §19), development section inventory link,
the three placement rules of §3 (exclusive on fact-ID overlap, section visibility inherited, excluded
destination never dropped — each a confirmed G1 defect, so each gets a regression test now and a
blocking check at v1), the banner present whenever a verified illustration and homepage exist, the
Enterprise Edition paragraph present and exactly once whenever a target resolves, 30-point
criterion profile.

## 6. Repair scope

Repair may change LLM-owned content units and plan selections, and may reopen extraction when
evidence is missing. Deterministic blocks change only when their facts change. A reviewer finding
demotes to advisory only when a deterministic check contradicts it or shows the section it names is
outside repair's scope — content decides, never how many times the finding has been seen. A finding
re-raised after its one repair attempt never demotes on that account alone: it is code-caused (a
deterministic check should have caught it, so the check is added and the cause fixed at its stage)
or it blocks, reported as the transaction's outcome rather than retried a third time. Repair
attempts are one per equivalent fingerprint; the second failure changes evidence, prompt, model
route, or stage. A finding that alleges an absence states what it claims is missing as text the
code can look for; a string it names that the candidate does contain refutes the finding, which is
recorded with its reason. A finding may state the same claim as a typed `omission` — the section and
the fact or example IDs and exact phrases it says are missing; code, never the reviewer, decides:
every named ID or phrase present in that section's rendered text refutes it, an ID no SUPPORTED fact
carries or a phrase in no original text is nothing to restore and refutes it too, any one truly
absent upholds it and routes the repair to the named section, and a claim naming nothing checkable
is advisory with its reason. A finding that blames a composition stage (S6, S7, S8) for text the
composer does not write — a section the shell marks deterministic or At a Glance, or a rendered
API Reference row no content unit carries — names no stage repair can act on: it is demoted, kept
in `advisory` under `demoted: {rule, section, stage, owner, reason, evidence}`, never called
refuted, and still counted by the acceptance score. A finding that names S2 for a wrong fact, one
that says something is missing that code cannot settle, and one about text a unit or a kept
inherited unit carries are not demoted. A required row of §2 admits zero advisories left standing
before `READY_FOR_PROPOSAL`: an advisory is deferred repair work, not accepted work, so a finding
nothing contradicted, against a section every candidate must have, blocks and is reported. A
refuted or demoted finding is not deferred work — no revision could act on it — so it never
blocks; `review.json` keeps it with the reason that refuted or demoted it. An optional row may carry one; the bundle records the
advisory count either way.

## 7. Bundle layout

`candidates/<owner>__<name>/<revision>/` holds `README.md`, `README.patch`, `facts.json`,
`investigation.json`, `dispositions.json`, `plan.json`, `content_units.json`, `raw_calls.json`,
`examples.json`, `probes.json`, `validation.json`, `review.json`, `repairs.json`, `calls.jsonl`,
`dependencies.json`, and `manifest.json`. A bundle carries every artifact its own facts cite as
evidence: `examples.json` is the verification receipt each `example` fact names, and
`repairs.json` the record of what a repair attempted, so neither is left dangling outside the
seal. `probes.json` records every live read that informed a fact — its status, how long it took,
and any reading that changes without the repository changing, such as a registry's latest
version — because a fact's evidence is hashed and must not move when only the world does.
`raw_calls.json` (G5-W02, 27.2 RC4) seals, verbatim and keyed by each call's own request hash,
every accepted call no other artifact already answers for byte for byte - each source_reconciliation
batch, a coherence batch, an independent_review read, and a batch section_authoring task - so a fresh clone with an empty
`runs/` directory can replay an unchanged revision with zero provider calls; a non-batch
section_authoring task is reconstructed from `content_units.json` alone instead, and is not
duplicated here. A transaction that composed without one seals without it; `probes.json` and
`calls.jsonl` carry a clock, so neither is compared byte for byte in the no-op proof.
`calls.jsonl` keeps every attempt of the transaction: a line for a call the sealed composition did
not consume carries `retained_reason` (audit only: replay seeding ignores it, and a measure of
first-attempt acceptance filters on it). The manifest records `sealed_by` (the invocation and
process that wrote the bundle) and `ledger_totals` (sums over `calls.jsonl`), and verification
fails closed when they stop reconciling with the ledger. The
manifest seals the
bundle (`schemas/candidate-bundle.schema.json`); `READY_FOR_PROPOSAL` is the sealed state. Progress
is the authorizable count, N of the registry size (44 on 2026-10-11), under owner decision D4 and
`AGENTS.md`.
The manifest also carries an optional `call_variance`: when a job's successful attempts across
the transaction's whole history - every repair round and reopening, not only what the accepted
composition ultimately consumed - never settled on one response, that job and every distinct
response hash it returned are listed there, so provider non-determinism is visible from
`manifest.json` alone rather than a manual `calls.jsonl` read (RC-05, RESEARCH_AND_GUIDELINES.md
27.2 RC5/SW6). Absent when no such variance exists.
`candidates/<owner>__<name>/CURRENT` names the revision of the current candidate so a reviewer
opens one stable path. Superseded revisions stay in place with state `SUPERSEDED`.

`dependencies.json` lists exactly the inputs this candidate consumed: source revision and relevant
tree hash, every fact ID with its hash, every prompt manifest ID and content hash, model route, this
contract's version, every template component version rendered, every validator ID and version that
ran, the acceptance profile version, the protected-content fingerprint, and the policy hash. Nothing
else can invalidate the candidate.

## 8. Prose rules for LLM units

Natural English a maintainer would write. Identifiers stay intact inside code spans; never split
CamelCase or pad with spaces. No superlatives, no hedged capability claims such as "may support",
no first-person or agent voice, no references to the generation process. One capability inventory
per document. Sentences average under 25 words. A unit that reads as a template sentence with the
product name substituted fails the coherence pass.
