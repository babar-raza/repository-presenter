# Candidate README Contract

Status: normative for every candidate. Version 1 is a draft that freezes at G2 exit as
`readme-contract-v1`; afterwards it changes only at a declared version boundary with regression
evaluation across every current candidate. Every bundle's `dependencies.json` names the version it
was built against.  
Derived from: `plans/idea.md` (Portfolio README Presentation Contract and standing constraints),
`RESEARCH_AND_GUIDELINES.md` §4 to §7, and the legacy template registry pulled as an asset.  
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
| 2 | `badges` | none | Required | visible | D | One row, from a badge registry keyed by ecosystem — never a Python-only hardcode. In order, each only when its target is verified: package-registry version (PyPI, Maven Central, NuGet, npm, crates.io; pkg.go.dev reference for Go), language or runtime floor from the manifest, real CI status when a workflow badge target resolves, license, contributors. Floor: the license badge whenever a license file exists plus at least one more verified badge when any is available. Omit a badge whose target is unavailable; never duplicate, split into two rows, or fabricate. |
| 3 | `banner` | none | Conditional: a verified product illustration and homepage exist | visible | D | Linked image immediately below the badge row: `[![alt](image_url)](homepage_url)`, alt text naming the product. Both `image_url` and `homepage_url` come from verified facts, never a guess or a placeholder graphic. Omit entirely when either is unresolved — never an unlinked image, never a broken link. |
| 4 | `opening` | none | Required | visible | L | Two to four sentences: what it does, problems it solves, who uses it. No Aspose promotion, no marketing superlatives. |
| 5 | `navigation` | Navigation | Required | visible | D | An explicit `## Navigation` heading, then a compact list of in-page links to the visible headed sections actually present, in document order. |
| 6 | `at_a_glance` | At a Glance | Conditional: at least three verified core capabilities | visible | M | Exactly one Mermaid fence and nothing else (§2.1). Starting Points appear only when a verified input format exists; a product that creates from scratch still gets the diagram, without them. |
| 7 | `key_capabilities` | Key Capabilities | Required | visible | L | Three to eight items. Each title is an action-led natural phrase grounded in facts; each description is one sentence naming the real classes or members it rests on. A capability with a known limitation says so inline with a link to Scope and Limitations rather than overstating. At most one search-intent keyword per title, with an output-lineage record; no keyword repeats across titles. |
| 8 | `installation` | Installation | Required | visible | D | Verified install for the ecosystem's package manager from manifest plus package-registry observation, in every idiomatic form the ecosystem uses, each in its own fenced block (Maven and Gradle for Java; pip for Python; `go get`; `cargo add`; `dotnet add package`; npm); then the verified source install as a fallback (clone, then build or editable install); then a one-line verify command when the ecosystem has an idiomatic one (an import or version print); then one sentence on supported runtimes from manifest facts. Never an unverified command. State plainly when the package-registry observation shows the package is not yet published, rather than presenting an unqualified install command the registry itself contradicts. |
| 9 | `dependencies` | Dependencies | Required | visible | D | From the dependency snapshot, in four subsections in this order — Required Package Dependencies, Optional Dependencies, Native and System Requirements, Development Dependencies. Optional, Native and System, and Development omit silently when their own bucket is genuinely empty; Required omits only its bullet list, rendering the fixed sentence "No required third-party package dependencies." plus the manifest evidence in one clause, instead of vanishing, so a reader can never mistake verified-zero for generation forgetting the section. Never a flat, unstructured list; never merged into Installation. |
| 10 | `quick_start` | Quick Start | Required | visible | M | One or two minimal examples, each executed or compiled in isolation and each introduced by one lead-in sentence: when the product reads files, the first opens an existing input; when it creates them, one builds from scratch. Correct fence language, normalized spacing. |
| 11 | `feature_showcase` | Feature Showcase | Conditional: the existing README carries a verified, repository-owned visual proof of capability the plan preserves | visible | D | A linked preview image (`[![alt](preview)](full asset)`) with alt text naming what it shows, repository-relative, resolving against the snapshot tree; one sentence of context may follow. Never a stock or generated graphic. |
| 12 | `additional_examples` | Additional Examples | Conditional: at least one further verified example, or a verified repository-owned image the plan preserves | collapsible | M | One lead-in sentence; one flagship example visible under its own task-named `###` heading when the plan selects one; then a single `<details><summary>View Additional Examples</summary>` block holding every further verified example, each under its own real, unique, task-named `###` heading — never "Example N", never a heading reused. A one-sentence explanation may precede a block when the code alone would not make the task obvious. A code comment that records a real, verified API gotcha is kept, not stripped. Verified repository-owned images from the inherited README (screenshots, rendered outputs, generated previews, embedded data-URI images) are preserved here under their own descriptive `###` heading with alt text, resolving against the snapshot tree — never excluded on the ground that no section exists for them. |
| 13 | `project_structure` | Project Structure | Conditional: the existing README carries a repository tree the plan preserves | visible | D | The preserved tree rendered with canonical box-drawing characters (`├──`, `└──`, `│`) regardless of the source's own style; every path resolves against the snapshot tree or the unit is corrected with evidence, never carried stale. |
| 14 | `api_reference` | API Reference | Required | collapsible | M | Most FOSS repositories carry no dedicated reference, so the README is it. A visible one-to-two-sentence intro naming the real entry-point classes, how they relate, and the verified public type count; then a single `<details><summary>View the Complete Public API Surface</summary>` block holding the complete verified public surface: a `### Core API` table (`\| Class \| Description \|`, every name in a code span) covering every verified public type, split by kind where the ecosystem warrants (`#### Enumerations`, `#### Interfaces`, `#### Structs`, `#### Traits`), then `#### Detailed Member Reference` with `### <Topic>` groups listing the hub types' verified members as nested bullets. Every description is evidence-backed from the symbol's own documentation or signature; a type with no verifiable description gets its verified signature summary, never an invented sentence and never mechanical filler ("class with N methods", "extends Exception"). Inherited API content the plan places here renders inside the same block, deduplicated, never outside it. Depth scales with the surface; the table is deterministic from the verified public-symbol facts and the LLM owns only the intro, the topic grouping, and description wording bound to fact IDs. |
| 15 | `documentation_resources` | Documentation & Resources | Conditional: verified relevant targets exist | visible | M | One list, each item a bold link, an em dash, and one sentence on what it covers: the verified documentation, knowledge-base, and reference targets (the reference item states the verified public type count and points to the in-page API Reference for the essentials); repository-relative links to verified tracked docs when they exist (a publishing or contributor guide, implementation notes, labeled as such); and a closing "Found a bug or have a feature request? Open an issue" line to the repository's issues page. Aspose links within the configured or derived ceilings. Never the same target twice. |
| 16 | `scope_limitations` | Scope and Limitations | Required | visible | L | A bulleted list of designed or declared limitations, each naming the precise mechanism a fact records (an exact exception type, a named unimplemented class or method) — never a vaguer paraphrase ("raises an exception") when the fact is more precise ("raises `NotImplementedError`"). At most one scope sentence before the list, only when it says something the bullets do not; never a prose paragraph restating them. When nothing traces to a public source, omit the list rather than invent filler. Transient defects (a package that fails to import at this commit, a broken build backend) are never limitations. The section closes with the Enterprise Edition paragraph (row 18). |
| 17 | `development_testing` | Development and Testing | Conditional: build or test assets exist | visible | M | Prose with fenced commands from the actual build files and CI: install or build and run the suite; a single-target run when the ecosystem has one, copied exactly from its verified example fact, never approximated; one sentence sizing what the suite covers when a test-file count is verified; a release sentence linking the repository's release or publish workflow file when one exists. Representative assets are named in prose, never as a bare directory list. Never collapsed. |
| 18 | `enterprise_relationship` | none (closing paragraph of Scope and Limitations) | Conditional: a verified aspose.com product target exists in policy | visible, below the fold | M | The final paragraph of Scope and Limitations, separated from the bullets by a blank line, never inside a bullet: one or two sentences of the shape "These limitations don't apply to [Aspose.{Family} for {Platform} — Enterprise Edition](url), which adds …", naming what the Enterprise Edition adds from verified facts or policy, never invented. "Enterprise Edition" is the only edition name anywhere in the document, and it appears exactly once. A family-level target names no platform at all; a platform-level target names exactly the one real platform and never the resolved URL's own implementation detail (a compound or bridge slug never surfaces in the anchor or surrounding prose). Omit the paragraph entirely on an unresolved target — never guess a platform or fall back to a family link for convenience. |
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
out to the product or to outputs; no per-format node edges. Up to five capability nodes form one
column; six to eight form two balanced columns. Every label is geometry-safe: no unbroken token over
28 characters, and no label wrapping past three lines at Mermaid's default node width — a longer
title is shortened at planning, never clipped at render. No custom styling directives. The LLM
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
`OMIT_UNSUPPORTED` carry evidence in the dispositions file; `DEFER_UNRESOLVED` units are listed for
owner resolution and never rendered; `NON_CONTENT` is ignored. A material unit with no safe
destination fails the transaction closed instead of being dumped.

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

Two more placement rules, both from the same G1 canary bundle: a placed unit inherits its section's
visibility — in a `collapsible` section it renders inside the section's `<details>` block after the
composed content, never appended outside it (17 inherited API units landed visible below a closed
`</details>` as a 58-line uncollapsed block, outside the reference they belonged in). And a placed unit whose
destination section the plan excludes is not silently dropped: reconciliation re-routes it to a
destination the plan includes, or the transaction fails closed naming the unit — the same standard
as a unit with no safe destination (one `VERIFIED_PRESERVE` unit was routed to `at_a_glance` while
the plan excluded that section, and vanished).

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

Exactly these eleven block acceptance at G1. Everything else is advisory until contract v1 freezes.

| # | Check | Sections |
|---|---|---|
| 1 | Source revision pinned; original README bytes exact; every fact carries evidence | all |
| 2 | Install command verified against manifest and package-registry observation | `installation` |
| 3 | Every rendered example was executed or compiled in isolation at this revision | `quick_start`, `additional_examples` |
| 4 | Every content unit's fact IDs exist and are `SUPPORTED`; every identifier in prose is a fact value in a code span | `opening`, `key_capabilities`, `scope_limitations`, `api_reference`, `documentation_resources`, `enterprise_relationship` |
| 5 | Every material inherited unit has exactly one disposition; placed units appear in their destination | all |
| 6 | Every link resolves; Aspose links are contextual and within ceilings; "Enterprise Edition" is the only edition name | `documentation_resources`, `enterprise_relationship`, `badges` |
| 7 | Exactly one factual H1; one badge row; title-case headings; canonical abbreviations; At a Glance topology and column rules; no internal narration; within the visible-length budget (content inside `<details>` is unbounded but verified) | structure |
| 8 | Protected content preserved | all |
| 9 | No configured secret in the bundle | bundle |
| 10 | Independent review returns `ACCEPT` with the reviewer identity separate from authoring | review |
| 11 | Fresh-process rerun is byte-identical with zero provider calls | bundle |

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
that cannot be acted on within that scope is recorded as advisory, never blocks a second time, and
is reported as a reviewer-scope defect. Repair attempts are one per equivalent fingerprint; the
second failure changes evidence, prompt, model route, or stage.

## 7. Bundle layout

`candidates/<owner>__<name>/<revision>/` holds `README.md`, `README.patch`, `facts.json`,
`investigation.json`, `dispositions.json`, `plan.json`, `content_units.json`, `validation.json`,
`review.json`, `calls.jsonl`, `dependencies.json`, and `manifest.json`. The manifest seals the
bundle (`schemas/candidate-bundle.schema.json`); only `READY_FOR_PROPOSAL` counts toward N/34.
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
