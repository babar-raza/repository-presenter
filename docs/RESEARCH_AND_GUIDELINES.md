# Repository Presenter Research and Design Guidelines

Status: durable research record and implementation guidance  
Recorded through: 2026-09-02  
Legacy repository: `babar-raza/foss-readme-optimizer`  
Legacy source baseline used by the new project: `a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815`

## 1. Purpose and authority

This document preserves the useful investigation, reasoning, rejected approaches, measurements,
and design guidance developed before implementation began. It exists so a future agent can recover
the reasoning without relying on conversation history.

It is deliberately not another execution plan:

- [`EXECUTION_STATE_MACHINE.md`](EXECUTION_STATE_MACHINE.md) owns build order, gates, deliverables,
  and execution state.
- [`STATE_MACHINE.md`](STATE_MACHINE.md) owns production runtime states and transitions.
- This document explains why those contracts exist, records their empirical basis, and identifies
  conclusions that must be retained or revalidated.
- [`DECISION_LOG.md`](DECISION_LOG.md) is the append-only provisional decision log this document's
  own §31 grew into (split out 2026-09-08) — the loop's and lanes' running record of decisions made
  without stopping to ask, in the shape date · item · decision · alternative rejected · evidence ·
  reversal path. Read it alongside this document, not instead of it: this document is the durable
  "why"; the decision log is the dated "what happened since."

Labels used below:

- **Observed** — directly inspected in source, state, history, workflows, or target repositories.
- **Measured** — produced from a bounded count or inventory at the recorded revision/date.
- **Inferred** — reasoned conclusion from observations; implementation must test it.
- **Decision** — selected direction for the new project.
- **Rejected** — approach considered and deliberately not selected.
- **Revalidate** — time-sensitive or incomplete observation that cannot remain permanently assumed.

## 2. Original problem

The legacy README optimizer accumulated extensive machinery but failed to provide a dependable,
current, contract-valid README transaction. The central problem was not absence of code, tests,
state, plans, or evidence. It was failure to convert those assets into the primary observable
result: one current repository-grounded README, independently accepted and immediately no-op
proven.

The new product must therefore optimize for completed repository outcomes rather than machinery
completion.

### 2.1 Intended product outcome recovered from `plans/idea.md`

**Observed:** the permanent intent is a central repository-presentation agent, not a link injector,
static template renderer, or one-time cleanup script.

The system must:

- establish a FOSS product as useful, credible, and professionally maintained before promotion;
- explain what it does, the problems it solves, supported capabilities/formats, installation,
  usage, limitations, and maintenance;
- place relevant Aspose and Enterprise Edition links only where they help the reader;
- continuously inventory and monitor authorized repositories;
- run autonomously on GitHub-hosted runners through schedules and explicit triggers;
- use repository-grounded facts and reconcile product-agent/current-README claims;
- employ agentic reasoning for interpretation, editorial planning, composition, review, and repair;
- keep deterministic control over safety, evidence, validation, state, effects, and idempotency;
- remain durable across ephemeral runners;
- update presentations after upstream changes without routine human operation; and
- eventually manage other repository presentation surfaces through the same core.

README health is foundational and cannot be displaced by social preview, metadata, research,
governance, or future-surface infrastructure.

## 3. Legacy-system investigation

### 3.1 Repository scale

**Measured during the 2026-09-01 audit:** approximately:

| Measure | Result |
|---|---:|
| Legacy repository commits since 2026-07-17 | 1,423 |
| First-party production Python | 171,345 lines |
| Vendored Aspose.org Python | 23,574 lines |
| Tests | 156,031 lines |
| `facts/` | 36,455 lines |
| `readme/` | 30,920 lines |
| `supervisor/` | 26,376 lines |
| `specialists/` | 20,682 lines |
| `presentation/` | 13,867 lines |
| `state/` | 6,627 lines |
| `capabilities/` | 6,485 lines |
| Foundation-oriented packages | approximately 18,690 lines |

These counts describe scale, not value. Large areas contain valuable implementation mixed with
historical lanes, product-specific fixes, proof scaffolding, compatibility paths, and orchestration
that should not be reproduced.

### 3.2 Live delivery state found during the audit

**Observed at legacy state reference `827881b...` on 2026-09-01:**

- registry/accountability denominator: 34;
- `facts_ready`: 1;
- `candidate_generated`: 0;
- no-op proven: 0;
- active task: null;
- durable transitions: 1,209;
- attempts: 247;
- ineffective attempts: 115;
- closed tasks: 81, including closures later shown not to establish the promised result.

The first candidate-focused task, PF02, had 159 transitions and 21 staleness regressions. PF04 had
to reopen because its proven-transaction runner had no production importer. This is strong evidence
that transition volume and task closure were decoupled from user-visible delivery.

### 3.3 Stale candidate evidence

**Observed:** an older finalized evidence area contained ten Python candidates from 2026-08-11/12,
but those artifacts were stale relative to current source and current control contracts.

Approximately 619 control-repository commits followed the last promotion without a corresponding
change to the canonical finalized candidate set. One old 3D/Python candidate was approximately 793
README lines and included weak generated API prose.

**Guideline:** candidate existence, historical approval, generated evidence, or task closure never
counts as current acceptance. Source, facts, candidate, validation, independent review, provider
calls, and no-op proof must form one current transaction.

### 3.4 Two generations of legacy product

**Observed:** the legacy repository contains:

1. A narrow deterministic `generate/run` path that detects four promotional gaps and writes a
   bounded owned span.
2. A much broader `supervise/verified_repository_presentation` path intended to perform agentic,
   repository-verified presentation work.

The narrow path remains useful only as historical behavior or a migration reader. It is not the
new product's foundation. The broader path contains significant reusable intelligence, but its
supervisor/mission/proof architecture became too elaborate to carry forward safely.

### 3.5 What was structurally sound

The following ideas were valuable and must not be lost:

- immutable source revision binding;
- exact preservation of original README bytes;
- hard repository allow-list;
- push-neutered read-only clones;
- separate read and write credentials;
- per-job custom-LLM routing and typed outputs;
- provider-call attribution and zero-call accounting;
- prompt registry and prompt hashes;
- ecosystem-aware public consumer-surface extraction;
- claim accountability and source-content dispositions;
- deterministic validation and independent review;
- component-scoped dependency hashes and invalidation;
- repository-scoped durable state and CAS;
- trigger deduplication, leases, recovery, effect reconciliation, and health reporting;
- no-op as a complete-transaction property;
- independent processability classification; and
- portfolio accounting that retains non-processable entries.

### 3.6 What caused failure or unnecessary drag

**Inferred from code/state/history:**

- the mission/task apparatus became a product of its own;
- multiple trusted/verified/POC/compatibility paths created ambiguous authority;
- proof machinery was built before one simple current transaction worked;
- state transitions could grow without narrowing the README defect;
- historical artifacts could look like progress despite stale dependencies;
- numerous specialist, capability, promotion, cohort, and lifecycle abstractions increased wiring
  risk;
- product-specific fact machinery accumulated without a clean plugin boundary;
- infrastructure and acceptance contracts expanded faster than visible output;
- runtime and project-development governance became entangled; and
- repeated retries could preserve the same causal owner instead of changing mechanism.

## 4. Target-repository research

### 4.1 Corpus scope

**Observed:** all 34 repositories listed in the legacy product registry were inspected at their
then-current default branches on 2026-09-01. They span 13 families and seven ecosystems.

| Family | Platforms | Presentation observation |
|---|---|---|
| 3D | Java, .NET, Python, TypeScript | Shared semantic portfolio structure. |
| Barcode | Python | Standard structure. |
| Cells | C++, Go, Java, .NET, Python, Rust, TypeScript | Standard structure. |
| Email | C++, .NET, Python | Standard structure. |
| Font | Python | Purposefully product-specific. |
| HTML | Python | Standard structure. |
| Note | Python | Standard structure. |
| Page | Python | Standard structure with visual-output content. |
| PDF | C++, Go, Java, .NET, Python, TypeScript | Five standard; TypeScript is a detailed product manual. |
| PSD | .NET, Python | README-only placeholders. |
| Slides | C++, Java, .NET, Python | Shared Slides-family presentation. |
| TeX | Python | Compact, output-oriented presentation. |
| Words | .NET, Python | Standard structure. |

Classification at the time of inspection:

- 25 repositories used substantially the same semantic README contract;
- seven had legitimate bespoke family/product compositions; and
- two PSD repositories lacked implementation evidence.

This classification must be frozen with exact revisions during the reuse/corpus gate and refreshed
before portfolio proof.

### 4.2 Standard does not mean identical

The 25 standard-shell repositories share a reader journey, not a universal prose body. Common
semantic identities are:

1. Identity and badges
2. Navigation
3. At a Glance
4. Key Capabilities
5. Installation
6. Dependencies
7. Quick Start
8. Additional Examples
9. API Reference
10. Documentation and Resources
11. Scope and Limitations
12. Development and Testing
13. License

Each repository must still supply its own facts, audience, emphasis, workflows, examples, API hubs,
limitations, development instructions, and coherent prose.

### 4.3 Legitimate variations

- **Font/Python:** variable-font-first workflows, generated outputs, CLI behavior, MCP server and
  review artifacts are central to the product story.
- **PDF/TypeScript:** extensive capabilities and examples justify a manual-like composition.
- **Slides family:** supported/unsupported behavior and edition choice are more useful than a
  generic API inventory.
- **Page/Python:** visual output evidence materially improves comprehension.
- **TeX/Python:** a compact output-oriented journey is more appropriate.
- **PSD/.NET and PSD/Python:** no implementation evidence means no README authoring.

Profiles must make these compositions expressible, but the planning agent must select and justify
the result from current evidence.

### 4.4 Live README refreshes and lineage gap

**Observed:** many target READMEs were refreshed during August 2026, including standard-shell
changes across 3D, Cells, Email, HTML, Note, Page, PDF, and Words. Other product repositories were
updated through independent release or product workflows.

This explains the apparent contradiction: useful live READMEs exist while the legacy optimizer's
current canonical state has no valid candidate. The live files are valuable source material and a
development corpus, but must be requalified because the legacy system cannot trace them to a
current complete transaction.

## 5. Factual authority and content guidance

### 5.1 Evidence hierarchy

The exact immutable repository snapshot is primary authority. Relevant evidence includes:

- Git identity, default branch, tags, releases, and history;
- manifests and lock files;
- public consumer surface, exports, namespaces, modules, and declarations;
- implementation source;
- tests and examples;
- build/CI configuration;
- license and community files;
- current README and repository assets; and
- verified package registry observations.

Product agents, Aspose.org pages, package pages, external documentation, SEO vocabulary, and
previous candidates are leads, oracles, and presentation evidence. They cannot override
contradictory repository/package evidence or solely support a public factual claim.

### 5.2 Field-to-evidence mapping

| README material | Expected evidence |
|---|---|
| Identity and repository links | Git metadata, registry and repository configuration. |
| Package/install command | Ecosystem manifests plus verified public consumer/package surface. |
| Dependencies/runtime | Manifests, lock files, native loading, build configuration and CI. |
| Quick Start | Tested example/test or independently verified public-consumer example. |
| Capabilities | Public symbols corroborated by examples, tests, formats and implementation. |
| API Reference | Parsed public/exported surface, grouped for reader utility. |
| Build/test instructions | Actual build files and CI. |
| Limitations | Explicit implementation boundaries, omissions and unsupported paths. |
| License | Repository license evidence; absence remains absence. |
| Images/links | Existing assets plus destination/context validation. |
| Positioning and journey | Agentic interpretation of accepted evidence. |

### 5.3 Preservation

Maintainer/product-agent README material is neither disposable nor automatically true. Every
meaningful unit must receive exactly one outcome: preserve, rewrite, move, correct, supersede,
omit with evidence, defer as unresolved, or classify as non-content.

The approved presentation contract owns tone, headings, organization, and formatting. Source prose
structure is not itself protected, but validated information and maintainer intent are.

## 6. Deterministic and agentic responsibilities

### 6.1 Agentic work

Agents must perform genuine judgment for:

- understanding the product and audience;
- identifying important workflows and evidence gaps;
- reconciling conflicting or stale claims;
- determining the visitor journey and useful section depth;
- selecting the best examples and API hubs;
- composing coherent repository-specific prose;
- independently reviewing factual and visitor quality; and
- choosing targeted causal repairs.

A candidate produced solely by phrase matching, rules, or template population fails the product
intent even if deterministic checks pass.

### 6.2 Deterministic work

Code owns:

- registry admission and processability;
- immutable snapshots and hashes;
- evidence extraction and provenance;
- state transitions, leases and recovery;
- prompt/model/component dependency identities;
- commands, code blocks, verified links, badges and diagram topology;
- claim and source-unit accountability;
- Markdown, structure, link, example and safety validation;
- caching and no-op decisions;
- credential isolation and authorization;
- GitHub effect execution and reconciliation; and
- terminal artifact production.

### 6.3 Correct composition flow

```mermaid
flowchart TD
    S["Immutable snapshot"] --> E["Evidence extraction"]
    E --> F["Typed facts"]
    F --> I["Agentic investigation"]
    I --> R["Source reconciliation"]
    R --> P["Agentic presentation plan"]
    P --> C["Profiles and editable components"]
    C --> W["Agentic composition"]
    W --> V["Validation and independent review"]
    V --> O["Candidate, evidence and patch"]
```

Profiles and templates constrain and enable presentation. They do not replace interpretation.

## 7. Template and modularity guidelines

### 7.1 Semantic components

Templates should be ordinary Markdown/Jinja files, with layout/order/applicability in YAML.
They may define presentation framing, stable headings, slots, and deterministic structure.

They must not hardcode:

- package names or versions;
- product capabilities or supported formats;
- install/build commands;
- public API claims;
- limitations;
- repository-specific links; or
- unsupported marketing statements.

Those values come from versioned typed facts and an accepted agentic plan. Missing or unresolved
required facts fail compilation.

### 7.2 Profiles

- Platform profiles contain ecosystem knowledge and validation requirements.
- Family profiles contain accepted recurring terminology, workflows, and composition hints.
- Repository profiles are reviewed declarative overlays used only for true residual exceptions.
- No profile may bypass evidence, force a fact, or predetermine the entire document.

### 7.2.1 Importing legacy profiles and catalogs (2026-09-02)

**Observed in the legacy source:** `config/policies/*.yml` (34 files) hardcode a per-product
`products_org_link`, `products_com_link`, label, and prohibited-term list each. `data/
aspose_org_links.json` is a generated catalog of 7,755 link records whose own provenance block
records only 44 as live-verified, at a probe dated a month before freeze; `data/aspose_com_links.json`
is the same shape. `data/families.json` (17 records) and `data/platform_priorities.json` (a seven-item
execution order) are different in kind: small, global, structural, and low-risk to pull in full.

Rule: a policy file or a catalog record is pulled only when the repository or family currently being
composed needs it, never as the full 34-file or 7,755-record set ahead of G4 — the same pull-based
discipline `EXECUTION_STATE_MACHINE.md` §7 requires of code, applied to data. The pulling work item
re-verifies what it pulls before writing the file record: the link target resolves now (the check
`README_CONTRACT.md` §5 already requires of every rendered link), and the label and terminology still
match current product reality. A stale or unverifiable entry is corrected or dropped, never carried
forward on the legacy catalog's word. Record what was checked, changed, and dropped in the file
record's `note`. A pulled profile or catalog value is a lead, in the same evidentiary tier as an
Aspose.org page (§5.1): it can corroborate `presentation_planning`'s link and ceiling choices, never
override contradictory repository evidence or stand alone as a public factual claim.

### 7.3 Component boundary

README is one component of Repository Presenter. Shared `core` services own snapshot, evidence,
artifacts, state, LLM access, validation primitives, authorization, and GitHub integration.

Future components may manage:

- repository description;
- homepage and topics;
- community/contribution/security files;
- release and package links;
- visual assets and social preview; and
- drift protection across those surfaces.

They consume public core contracts and must not depend on README-private implementation.

### 7.4 Extraction and platform independence (2026-09-02)

Knowledge extraction (`extractors/`, facts stage S2) and knowledge processing (`investigation/`,
`reconciliation/`, `composition/`, S3 onward) are independent: `facts.json` is the only artifact that
crosses the boundary; no processing module imports an extractor module directly. Within extraction,
each platform's module (`extractors/platforms/<ecosystem>.py`) depends only on `core/`, the shared
ecosystem-agnostic surface façade and verifier base under `extractors/` (§29.6 E2–E3, from
2026-09-04), and its own file, sharing no import with any other ecosystem's module; only the registry
(`extractors/platforms/registry.py`) references more than one ecosystem, and only to register them.

**The registry is open-ended, not fixed at seven.** `ecosystem` is a pattern-constrained string in
the registry schema and model (`^[a-z][a-z0-9_]*$`), never a closed enum, and the extractor registry
holds plugins in a plain `{ecosystem: plugin}` dict that fails closed with `ConfigError` on anything
unregistered — verified in the built code, not just planned. G3 qualifies seven representatives
because that is what the frozen 34-repository portfolio needs; it proves the pattern generalizes, and
is a milestone, not a ceiling. An eighth ecosystem, or a fiftieth, enters exactly the same way at any
later gate: one plugin file implementing the same protocol, one test, one entry in the registry's
dict — nothing else changes. A repository in an ecosystem with no registered plugin stays
non-processable, correctly, until that plugin exists; that is the fail-closed default working, never
a defect to route around.

**Verified in the legacy source:** `ecosystems/registry.py` is already the sole file importing more
than one ecosystem module; `ecosystems/python.py` and `ecosystems/rust.py` import no sibling ecosystem
module. This one boundary was sound and this repository keeps it. Adding, fixing, or extending one
ecosystem's extractor must change only that file, its test, and its registration line — never another
ecosystem's file, the registry's dispatch logic, or any downstream stage. `REPOSITORY_LAYOUT.md` §2.1
states this as a placement and test requirement.

## 8. Autonomous GitHub operation

### 8.1 Trigger and monitoring model

Recommended initial cadence:

- frequent cheap remote-revision/open-proposal probe;
- daily changed/due repository processing;
- weekly complete discovery and all-surface freshness audit;
- `repository_dispatch` for product release/upstream-change notification;
- manual/workflow-call entry points for bounded diagnosis and integration; and
- recovery before new scheduling.

Scheduled polling remains the dependable recovery mechanism even if product workflows later emit
events.

### 8.2 Drift is broader than Git SHA

Track independently:

- source/default-branch revision and relevant file fingerprints;
- exact README blob and material-unit inventory;
- package/release observations with TTL;
- repository description/homepage/topics with TTL;
- presentation assets and observable GitHub state;
- prompts, models, schemas, extractors, validators, profiles and template components; and
- open presenter proposal state.

A changed repository should invalidate only dependent work. A test-only commit may require no
README update; a package identity change reopens installation; a new exported API reopens public
surface/capability/example analysis; an upstream README edit reopens reconciliation.

### 8.3 GitHub workflow boundary

Use three focused workflows:

1. `monitor.yml` — registry reconciliation, recovery, cheap probes, due-work matrix, health.
2. `present.yml` — isolated read-only repository transaction using the custom LLM.
3. `propose.yml` — separately authorized, repository-scoped PR creation/update.

GitHub Actions cache accelerates execution but is never authoritative durable state. Use
repository-scoped CAS state in a dedicated control-repository namespace plus immutable
content-addressed artifacts.

### 8.4 Publication

Initial autonomous update mode means open or update one presenter-owned PR. It does not mean direct
default-branch pushes.

Before a write:

- mint a fresh repository-scoped GitHub App token in the effect job;
- bind target repository, candidate hash, source revision, branch, PR intent, policy, and expiry;
- refetch source and cancel if stale;
- reconcile an uncertain prior effect before retrying; and
- preserve/reconcile overlapping upstream README edits.

Auto-merge can later be enabled by explicit repository policy after production proof.

## 9. Custom LLM guidance

### 9.1 Reusable legacy capability

The legacy custom-LLM implementation already supports:

- OpenAI-compatible `/chat/completions`;
- configurable base URL and API key;
- per-job model routing;
- deterministic sampling defaults;
- bounded transport retry;
- typed response validation;
- request/response hashes;
- attempt, latency and token accounting;
- prompt registry and prompt hashes;
- fixture clients; and
- cache-reuse/zero-call accounting.

This is a high-value reuse area and should be simplified, not rewritten casually.

### 9.2 Initial job set

Use a small governed set:

- `repository_investigation`;
- `source_reconciliation`;
- `presentation_planning`;
- `section_authoring`;
- `independent_review`; and
- `targeted_repair`.

The custom model may have a modest reliable context window. Supply bounded evidence dossiers and
small fact packets, but retain one final whole-document coherence step. An LLM cannot write exact
commands, APIs, links, badges, example code, or diagram topology without deterministic evidence.

### 9.3 Failure behavior

- Required route unavailable or deliberately disabled: block honestly.
- Malformed structured response: reject; do not loosen schema silently.
- One normal semantic attempt plus one targeted correction for an equivalent fingerprint.
- Third equivalent attempt prohibited until evidence, prompt, model, component, stage, or mechanism
  changes.
- Every physical provider attempt remains attributable to repository, revision, job, prompt, model,
  outcome, latency, and usage.

## 10. Legacy-code reuse findings

### 10.1 Quantified expectation

At audit time, approximately 31–37% of first-party production code appeared to contain behavior
worth carrying into the new repository:

- approximately 11% near-intact foundations;
- approximately 20–26% surgical extraction/refactoring; and
- approximately 63–69% not suitable for production migration.

This was an audit estimate, not a license to bulk copy. The execution gate must produce a file-level
reuse manifest and measured final result.

### 10.2 Reuse substantially intact

- LLM transport, attempt accounting, call schema/ledger, prompt registry/hygiene;
- Git safety and push blocking;
- allow-list loader and selected discovery/intake primitives;
- immutable repository snapshot and inspection;
- ecosystem/public consumer-surface parsers;
- evidence redaction and atomic writing;
- contextual link validation;
- selected deterministic public-quality validators;
- read-only GitHub API and preflight; and
- authorization data contracts.

### 10.3 Extract and refactor

- `ProductFactsV2` concepts and general repository facts;
- ecosystem consumer/example verification;
- format, identity, protected-content and interpretive evidence logic;
- README assessment, source disposition, preservation and document assembly;
- agentic section authoring and whole-document composition;
- presentation component compiler and claim validation;
- independent separated review;
- repository-scoped Git CAS, triggers, freshness, recovery and health; and
- product-specific fact logic converted into registered plugins.

### 10.4 Reference or fixture only

- bulk vendored Aspose.org tree;
- imported knowledge snapshots;
- previously generated candidates;
- old benchmark reports; and
- old acceptance/proof artifacts.

Useful mechanisms may be adapted natively with provenance and regression tests. Production must
not depend on a sibling checkout or an unbounded vendored system.

### 10.5 Retire

- legacy four-gap renderer and marker writer, except a migration reader if required;
- trusted transformation lane and trusted cohort machinery;
- Level-8 mission graph and mission command system;
- PF04/proven-transaction proof machinery;
- generic planner-driven capability/task graph;
- compatibility commands and duplicated lifecycle schemas;
- overlapping evidence manifest versions; and
- thirteen overlapping workflows (§16.3), replaced by three.

## 11. Tangible output and success contracts

Every README-component invocation returns exactly one public outcome:

| Outcome | Meaning |
|---|---|
| `candidate` | README, exact patch, facts/dispositions, evidence, validation, review and call summary exist. |
| `no_change` | Byte-identical accepted result with checksum-valid evidence and zero provider calls. |
| `insufficient_evidence` | No candidate; typed missing evidence and resume predicate. |
| `failed` | Bounded redacted diagnostic, causal state and retry/block classification. |

Internal runtime states may be richer, but no repository is left with an ambiguous external result.

The initial project is not done because it has code, tests, workflows, candidate files, task
closures, or evidence. It is done only when the GitHub-hosted system monitors the admitted
portfolio, produces independently accepted current candidates for all processable repositories,
proves zero-call no-op, responds to drift, and safely opens/updates authorized PRs.

## 12. Rejected approaches and cautionary lessons

### 12.1 Repair the legacy architecture wholesale

**Rejected:** it would preserve the ambiguity and complexity that prevented tangible delivery.
Reusable implementation should migrate behind new narrow contracts.

### 12.2 Build a deterministic README compiler

**Rejected:** typed facts plus platform/family templates alone cannot decide product meaning,
audience, emphasis, example quality, useful API depth, limitations, inherited-content correction,
or coherent prose.

### 12.3 Use one editable Markdown template

**Rejected:** the corpus demonstrates legitimate product/family compositions. Use a semantic shell,
editable components, profiles as evidence-aware hints, and agentic planning.

### 12.4 Give equal writing authority to multiple agents

**Rejected:** product/evidence agents provide technical truth and critique, while one central
composer owns final document coherence. An independent non-authoring reviewer owns acceptance
judgment.

### 12.5 Treat Aspose.org as permanent truth or runtime dependency

**Rejected:** it is an evolving development oracle and may contain defects. Repository/package
evidence remains authoritative.

### 12.6 Treat Git SHA as complete freshness

**Rejected:** package releases, metadata, proposals, presentation policy, prompts and external
surfaces can change independently.

### 12.7 Treat Actions cache/artifacts as durable mutable state

**Rejected:** caches can evict and artifacts expire. They are acceleration and review surfaces.

### 12.8 Build broad infrastructure before one transaction

**Rejected:** the first vertical slice must complete investigation through no-op and then a
disposable PR. Infrastructure is admitted only when the current/next proof consumes it.

## 13. Implementation heuristics

1. Lead every development increment with the observable repository outcome it unlocks.
2. Maintain one build cursor and one runtime state machine; do not create parallel authorities.
3. Port behavior with its tests and provenance, not files by reputation.
4. Keep orchestration small; stages call public seams and contain no domain implementation.
5. Add ecosystems and product families through registries/plugins, never expanding a central
   `if/elif` chain.
6. Preserve exact target revisions in corpus fixtures and refresh only at declared boundaries.
7. Validate model output before state advancement.
8. Route defects to the earliest causal stage; validation should not paper over extraction or
   planning errors.
9. Retain unaffected accepted work across repair and invalidation.
10. Run the exact production workflow in production-like conditions before claiming it works.
11. Keep write credentials physically absent from analysis jobs.
12. Continue safe unrelated repositories when one is retryable, blocked, or internally failed.
13. Expose honest portfolio health and a concrete resume predicate.
14. Measure provider cost, repair rate, false-positive drift, proposal acceptance, and update delay.
15. Do not let evidence production become a substitute for candidate delivery.

## 14. Items requiring revalidation

The implementation agent must not treat these dated findings as permanent:

- current default-branch revisions and README bytes of all 34 target repositories;
- registry denominator and processability classification;
- 25/7/2 composition grouping;
- package/release/public-consumer information;
- custom gateway models, context behavior, tool/structured-output reliability and limits;
- GitHub App installation coverage and permissions;
- live source counts and legacy module dependency closures;
- link targets, banners and repository assets;
- exact GitHub Actions behavior and supported action versions;
- whether a social-preview write API remains unavailable;
- the disposition of the legacy working-tree changes that were uncommitted at freeze (§16.2); and
- the legacy test-suite baseline at the frozen revision (§16.9), which must be re-measured if the
  frozen revision moves.

Revalidation updates evidence and, when necessary, the relevant authoritative contract. It does
not silently rewrite history.

## 15. Research reading order

A new implementation agent should read:

1. this document for context and design reasoning;
2. [`EXECUTION_STATE_MACHINE.md`](EXECUTION_STATE_MACHINE.md) for the current build gate;
3. [`project/state.yaml`](../project/state.yaml) for the live cursor;
4. [`STATE_MACHINE.md`](STATE_MACHINE.md) for the behavior being implemented;
5. [`plans/idea.md`](../plans/idea.md) for the product outcome and standing constraints, through
   the authority note at its top;
6. [`DECISION_LOG.md`](DECISION_LOG.md) for every decision made since, in date order — this
   document does not restate them;
7. the reuse manifest's file records as pulls create them, and the corpus inventory once the G3
   census produces it; and
8. only the legacy modules explicitly named by the active reuse record.

This order prevents both context-free implementation and a return to reading the entire legacy
project as an undifferentiated authority.

## 16. Pre-migration verification (2026-09-02)

These measurements were taken before Gate 0 began, directly against the frozen legacy revision and
the legacy working tree, to test the claims in §3 and §10 and the seed dispositions in the reuse
manifest. Labels follow §1.

### 16.1 Frozen revision

**Observed:** `a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815` exists in the local legacy clone and was
its `main` HEAD: author Babar Raza, authored 2026-09-01 18:39 +05:00, subject "fix(readme): drop the
ungrounded Project Structure summary phrase (PWD-060-FOLLOWUP5)". The local clone is shallow (two
shallow roots), so the 1,423 commits in §3.1 are the visible history, not necessarily the complete
history; provenance reasoning beyond the shallow boundary needs the remote.

### 16.2 Working tree at freeze

**Observed:** the legacy working tree was dirty when the revision was frozen: 15 modified tracked
files (496 insertions, 77 deletions) and 9 untracked files. Modified production files:
`facts/portfolio_facts_readiness.py`, `presentation/verified_template_api_reference.py`,
`presentation/verified_template_example_presentation.py`, `presentation/verified_template_sections.py`,
`specialists/review_standard_mermaid_premises.py`, `supervisor/mission_execution_guard.py`, plus
seven of their tests. Modified documents: `plans/idea.md` (adds the "Upstream Defect Reporting"
section) and `plans/investigations/control/mission-resume-capsule.md`. Untracked: a golden-corpus
reconstruction investigation with its roster, taskcards, evidence directory, and five tools.

**Decision:** this repository's `plans/idea.md` deliberately carries the uncommitted worktree text
(so it includes Upstream Defect Reporting) and says so in its authority note. The code changes are
not part of the frozen revision. The default exclusion was applied on 2026-09-02 as owner item
OWNER-03 in `project/state.yaml`; the owner may override it by committing the changes upstream and
naming a new frozen revision. The manifest records each exclusion under
`source.working_tree_at_freeze.exclusions`.

### 16.3 Scale measurements

**Measured** from a `git archive` of the frozen revision:

| Measure | Result | Comparison with §3.1 |
|---|---:|---|
| First-party production Python (excluding vendored) | 171,345 lines | exact match |
| Vendored Aspose.org Python | 23,574 lines | exact match |
| Tests | 156,031 lines | exact match |
| Test files | 457 unit, 12 integration, 9 security, 5 fixtures | new |
| Unit tests collected | 5,669 (4 `live` tests deselected) | new |
| Workflow files | 13 | earlier text said eleven; corrected |
| Scheduled workflows | production daily 05:17 UTC and weekly Sunday 04:43 UTC; registry update weekly Monday 07:00 UTC; log-coverage audit daily 06:00 UTC | new |
| Registry entries | 34, all `active: true`; mode `full` 2, `dry_run` 29, `disabled` 3 | matches §4.1 |
| Registry by ecosystem | python 13, net 7, java 4, cpp 4, typescript 3, go 2, rust 1; 13 families | matches §4.1 |
| Registry at `df864ffd` (2026-08-20, the baseline commit named in `plans/idea.md`) | 33 entries | the TypeScript entry was admitted 2026-08-26 |
| Legacy `LICENSE` file | absent; README says "all rights reserved by default" | provenance recorded per ported file |

The two PSD repositories are `disabled` in the registry, consistent with their non-processable
classification.

### 16.4 Real production entry point

**Observed:** `.github/workflows/readme-agent-production.yml` runs `registry-preflight` (App token
scoped to one control repository), `recovery-sweep` (control-repository `contents: write` for
`refs/readme-agent-state`), then `readme-agent supervise --repo <repo> --resume-trigger-key <key>
--no-registry-heal --execution-profile github_observe` per matrix member, a serialized
`staging_effect` job with a separately minted target-scoped token, and `health-report`.

**Measured:** the static import closure of the `supervise` command is 760 modules and 154,167 of
194,919 first-party lines (79%), including 83 `supervisor`, 75 `specialists`, 43 `capabilities`,
22 retired-disposition, and 2 vendored modules. The legacy narrow `orchestrator` path closes at
122 modules and 16,385 lines.

**Inferred:** the production path is effectively the whole codebase. Reuse by entry point is
impossible; reuse must be by module with each import closure cut deliberately. This confirms §3.6.

### 16.5 Reuse-manifest seed coverage

**Measured:** the seed globs in the pre-audit manifest match 176 files and 56,767 lines, 29.1% of
first-party lines (port 2,558; extract 17,088; plugin 6,182; fixture 23,574; retire 7,365).
138,152 lines have no seed disposition: `facts` 30,995; `readme` 29,298; `specialists` 20,221;
`supervisor` 19,601; `presentation` 9,240; `capabilities` 6,485; `state` 5,239; root modules 4,782;
`verification` 4,769; `llm` 1,881; `validation` 1,602; `golden_set` 1,341; `registry` 1,176;
`profile` 331; `authorization` 295; `evidence` 288; `github_api` 279; `preflight` 261; `license`
49; `effects` 19.

**Inferred:** the 31–37% estimate in §10.1 cannot be confirmed from the seeds. `github_api`,
`preflight`, and `authorization`, which §10.2 names as reusable, had no manifest entry; they are now
seeded. Only the pull-based ledger and the G3 census can settle the fraction, and a census-first
audit of 138,152 unseeded lines would itself become the machinery project §3.6 warns against.

### 16.6 Import-closure findings

**Measured** by static AST analysis of the 156 seed-retained modules: 31 reach a `RETIRE` module and
13 reach `supervisor`, `capabilities`, or `specialists`. The chains, recorded in the manifest as
`CPL-01` to `CPL-08`:

- `CPL-01` — every `llm/*` module reaches the retired `readme/markers.py` through
  `prompt_registry` → `readme/facts.py::sha256_text` → `validation/registry.py` →
  `validation/rules/change_boundary.py` → `markers`. `call_transport` alone closes at 44 modules
  and 3,962 lines because of this; after the cut it should be a handful.
- `CPL-02` — `evidence/writer.py`, `state/git_backend.py`, `state/cas.py`, `state/recovery.py`,
  `state/health.py`, `state/freshness_contract.py`, and `registry/revision_store.py` reach
  `capabilities/schema.py` through `state/proposal_schema.py` (`OrgRepoRef`); that module has 62
  direct importers.
- `CPL-03` — `specialists/separated_readme_review.py` closes at 592 modules and 115,816 lines,
  including `readme/candidate_pipeline.py` via `capabilities.dispatcher` → `capabilities.registry`
  → `capabilities.check_install_path` → `orchestrator`. The contract is reusable; the module is not.
- `CPL-04` — the production `supervise` command imports `_durable_state_backend` from
  `commands_compatibility.py`, a retire-disposition module.
- `CPL-05` — `paths.runs_dir()` defaults to `Path.cwd() / "runs"`; 69 modules import `paths`.
- `CPL-06` — 15 production modules carry 30 references to `plans/investigations/...` paths; most
  are docstrings or comments, but `supervisor/proven_transaction_runner/pf04_evidence.py` loads the
  Level-8 mission graph from that tree and the 30-point rubric modules cite `RUBRIC_30.md` there.
  Each reference is classified as fixture, oracle, or dead when its module is pulled.
- `CPL-07` — `env.py` resolves `GH_TOKEN` then `GITHUB_PAT` unless
  `README_AGENT_PRODUCTION_AUTH=github_app`, in which case ambient tokens are ignored and a missing
  App token fails closed. The behavior `plans/idea.md` requires exists and is the only production
  mode to port.
- `CPL-08` — 11 `specialists` modules import `langgraph` or `langchain-core`;
  `separated_readme_review.py` does not import them directly.

Fan-in for orientation: `errors` 123 direct importers, `paths` 69, `capabilities.schema` 62, `env`
45, `readme.markers` 17. "Port nearly intact" therefore describes module bodies, never their
closures.

### 16.7 Non-Python contract assets

**Observed:** much of the presentation contract in `plans/idea.md` lives in assets the manifest's
Python globs did not cover:

- 17 prompt manifests under `prompts/` with schema fields `prompt_id`, `category`, `version`,
  `model_route`, `owner`, `runtime_consumer`, `output_contract`, `invalidation_scope`,
  `dependent_artifacts`, and `system`/`user_template` text;
- `templates/readme/repository-presentation-v1.json` (template version 1.21.0,
  `reference_status: requires_requalification`) with invariants for badge rows, minimum badges,
  Mermaid visual grammar, capability layout and column threshold, topology, and minimum/target
  inputs, capabilities, and outputs;
- `templates/readme/section-registry-v2.json` with 16 sections including Third-Party Notices,
  Security, Contributing, and License, plus nine unmapped badge and banner checks;
- 34 per-repository policy files under `config/policies/` (link targets, labels, UTM, talking
  points, prohibited terms, allowed domains);
- `data/products.json`, `aspose_org_links.json`, `aspose_com_links.json`, `families.json`,
  `platform_priorities.json`, and the frozen `aspose_benchmark_quality_profile.json`
  (`BenchmarkQualityProfileV1`, development-only, 31 audited, 26 clean);
- `docs/presentation-standard.md` (ten dimensions, first-screen rules, search-intent guidance);
- `golden-sample/`.

**Decision:** these now have seed dispositions in `EXECUTION_STATE_MACHINE.md` §7.2 and the
manifest's `expected_asset_dispositions`.

Legacy prompt to new job mapping (**Inferred**, to verify while pulling prompts in G1 and G2):

| New job | Legacy prompt(s) | Disposition |
|---|---|---|
| `repository_investigation` | `draft_product_truth` (partial) | Extract |
| `source_reconciliation` | `claim_disposition_check` plus `verified_source_*` code | Extract |
| `presentation_planning` | `plan_readme_composition` | Extract |
| `section_authoring` | `section_cluster_authoring` | Extract |
| `independent_review` | `independent_readme_review`, `blind_readme_quality_review`, `factual_readme_plan_review` | Extract, consolidate |
| `targeted_repair` | `repair_capability_selection` (partial) | Extract |
| none | `relationship_explained`, `trusted_readme_section_transform`, `trusted_readme_fidelity_review`, `supervisor_turn`, `specialist_selection_turn`, `merged_readme_review` | Retire |
| evaluate later | `presentation_standard_compliance`, `prose_quality_check`, `visual_asset_accuracy` | Reference until a gate consumes them |

### 16.8 Windows path-length hazard

**Observed:** `LongPathsEnabled` is 0 on the development machine. The longest tracked legacy path
is 220 characters and 86 exceed 150. Under a 161-character root, 1,348 tracked files are unreachable
to Python (`FileNotFoundError` on an existing file); under the developer worktree root
(63 characters) 25 files exceed the 260-character limit; under a drive-letter mapping none do.

**Guideline:** every clean-checkout measurement of the legacy repository on Windows uses a short
root (for example `subst W: <clone>`), and this repository keeps evidence and fixture paths short
enough that no tracked path exceeds roughly 200 characters.

### 16.9 Legacy test-suite baseline at the frozen revision

Two initial runs from a deep scratchpad path were invalidated by §16.8: the archive run reported
347 failures and 3,241 passes before its failure cap, the long-path clone run 487 failures, 5,173
passes, 1 skip, and 13 errors, and every sampled failure was a `FileNotFoundError` on an existing
file. The valid measurements are recorded below.

**Measured** with the legacy virtual environment (Python 3.13.2, pytest 9.1.1, `-n 8`, `-m "not
live"`), the full non-live `tests/` inventory:

| Run | Root | Tests | Passed | Failed | Errors | Skipped |
|---|---|---:|---:|---:|---:|---:|
| Clean frozen clone at `a8a163f7`, drive-letter mapped | 3 chars (real path 161) | 5,674 | 5,399 | 261 | 13 | 1 |
| Developer worktree, dirty (adds 9 tests) | 63 chars | 5,683 | 5,669 | 13 | 0 | 1 |

The two runs share exactly 13 failing tests; every failure in the developer worktree also fails in
the clean clone, and the clean clone's other 261 failures are environmental: 267 of its 269 failing
paths exceed 260 characters, because `Path.resolve()` expands the mapped drive back to the real
161-character root and pytest's temporary directories under `AppData\Local\Temp\pytest-of-*` reach
281 to 328 characters on their own. The `test_prompt_hygiene` `shutil.Error` failures and the
`test_readme_proposal_bundle_verifier` errors are the same defect class.

Failures reproducible in both environments and attributable to the frozen revision itself:

| Test | Class | Assessment |
|---|---|---|
| `test_verified_template_capabilities_seo_keyword_lineage` (3 tests) | `AssertionError` on rendered Key Capabilities titles | **Confirmed** pre-existing failure at `a8a163f7`; directly relevant to the search-intent lineage obligation in `plans/idea.md` |
| `test_portfolio_stage_transactions::test_candidate_transaction_observation_tampering_still_breaks_seal` | `DID NOT RAISE ValueError` | **Confirmed** pre-existing failure; a seal-integrity negative control does not fire |
| `test_portfolio_stage_transactions::test_candidate_transaction_observations_do_not_change_semantic_receipt` | `FileNotFoundError` on a 179-character path | **Probable** genuine failure (sibling of the seal test; path is under the limit) |
| `test_supervisor_loop::TestBasicLoop::test_local_poc_records_snapshot_and_profile_before_later_stages` | `FileNotFoundError` on a 185-character directory | **Uncertain**: path is under the limit, but a deeper child may not be |
| 7 tests in `test_portfolio_worker_integration`, `test_trusted_readme_extraction`, `test_trusted_transform_review` | `FileNotFoundError` on 281–282-character temporary paths | Environmental |

**Inferred:** the legacy suite at the frozen revision is close to green but not green: four
confirmed and up to two probable failures exist independent of environment, and two of the confirmed
failures sit inside behavior the reuse manifest expects to extract (SEO lineage in
`presentation/`, stage sealing in `supervisor/portfolio_stage_transactions`). The definitive
baseline is the legacy CI on a Linux runner, which has no path limit; it is recorded, or a local run
with `LongPathsEnabled` is, before the first pull in G1 ports any test.

### 16.10 Governance corrections made in this repository on 2026-09-02

- `plans/IDEA.md` renamed to `plans/idea.md`, the path every reference and the product owner use;
  the case matters on Linux runners.
- `plans/idea.md` named retired legacy authorities as live. An authority note at its top maps them
  to this repository's documents; `AGENTS.md` lists the file as product authority; and
  `EXECUTION_STATE_MACHINE.md` §12 maps every obligation to a gate. Obligations that previously had
  no gate: the presentation-contract invariants, search-intent lineage, the benchmark quality
  profile, local `act` proof, the Java proposal cohort, upstream defect reporting, Level 7 and 8
  certification, and separated portfolio counts.
- `project/state.yaml` used `PENDING` and `BLOCKED_BY_GATE` and a nested shape that
  `EXECUTION_STATE_MACHINE.md` §5 did not allow or show; §5 now matches the file.
- `EXECUTION_STATE_MACHINE.md` said eleven legacy workflows; thirteen exist. Its record example
  pointed at `src/repository_presenter/llm/transport.py` while the manifest used
  `core/llm/transport.py`; both now use `core/`.
- The manifest now records the verified revision, the dirty working tree, the verified baseline,
  the coupling findings, seed dispositions for the packages and assets it had omitted, and two
  additional acceptance predicates.
- A `.gitignore`, a `.gitattributes`, and a descriptive `README.md` were added.

## 17. Re-evaluation against the recovery direction (2026-09-02)

**Observed:** the recovery direction recorded in §2 and §12.8, and in the conversation that produced
this repository, was: one repository, the smallest end-to-end path to a visible concise candidate,
only essential blocking gates, a candidate saved at a stable reviewable path, per-candidate
dependency manifests instead of global hashes, a frozen acceptance contract while qualifying seven
representatives, and progress counted as 1/34, 7/34, 34/34.

**Observed:** revision 1 of `EXECUTION_STATE_MACHINE.md` did not follow that direction. It placed
four infrastructure gates before any README: a foundation with decision records and an evidence
framework, a census-first file-level audit of 171,345 legacy lines, every schema and transition rule,
and the full durable kernel with leases, fencing, recovery, and a GitHub App boundary. The first
candidate appeared at its seventh gate. §16.5 and §16.6 show why the audit gate alone would have
consumed weeks: 138,152 lines had no seed disposition and the "port intact" modules were entangled
at import level.

**Decision:** revision 2 re-sequences the plan around the outcome. G0 is a two-day foundation; G1
produces the first valid candidate for Aspose.3D FOSS for Python at a stable path with eleven
blocking checks and a sealed bundle; G2 proves that candidate survives change through per-candidate
dependency manifests and freezes acceptance contract v1; G3 qualifies seven representatives and runs
the legacy census; G4 adds hosted monitoring and the durable runtime for 34/34; G5 proves the
proposal effect; G6 hardens and deploys; G7 operates and expands. Legacy reuse became pull-based:
a file enters only when a gate needs it, with its record, tests, and a cut closure, and everything
unpulled is retired at the G3 census.

**Decision:** five guardrails from the legacy failure analysis became binding principles: just-in-
time infrastructure; every work item ends with an end-to-end run and no module lacks a production
importer; candidates are invalidated only through consumed inputs and no global hash exists;
validators and reviewers re-check rather than invalidate, and reviewer findings must be repairable;
governance is budgeted at 200 lines for `AGENTS.md`, 500 for the build plan, and eight gates.

**Accepted risks:** pull-based reuse can under-reuse valuable legacy behavior that no gate happens
to need; the census at G3 exists to make that visible. A two-day foundation may leave configuration
and error handling thin until G1 needs them; that is intended. The eleven blocking checks may let a
weak candidate through at G1 that contract v1 later catches; G1 accepts that because a human reads
the candidate before G2 begins.

## 18. Preferred libraries over bespoke code (2026-09-02)

`plans/idea.md` states this twice: "Battle-tested, proven tools and libraries are preferred over
new custom infrastructure. Building a bespoke mechanism where an established one already solves the
problem requires a documented reason — naming the proven alternative considered and why it was not
used — not a silent default choice," and again under "Prefer Battle-Tested Solutions": existing
solutions are "actively researched and evaluated before custom functionality is developed." Before
this section, `AGENTS.md`, `EXECUTION_STATE_MACHINE.md` principle 16, and `project/loop-prompt.md`
each carried a one-line paraphrase — but every occurrence paired "established libraries" with
"proven retained code" or "proven legacy modules," which reads as permission to port a legacy
module unexamined rather than as the evaluate-and-document duty `plans/idea.md` actually states. A
ported legacy module is not exempt from this test merely for having run in production; §16.6's
import-closure findings already show ported modules need seam cuts on their own terms.

### 18.1 The concrete failure this prevents

The PWD-060 cascade named in the recovery discussion (a project-tree diagram misclassified as
emoji, exposing a crash on a language-less code fence, exposing missing provenance, exposing an
evidence mismatch, ending in a deleted phrase) is a hand-rolled-text-handling failure chain. Each
fix exposed the next defect because no step used a real, tested parser for the input class it was
classifying. A maintained CommonMark parser and a maintained Unicode/emoji classifier do not
misclassify a box-drawing tree diagram as emoji; a regex-based approximation can. This is the
concrete stake behind the principle, not an abstract preference.

### 18.2 What the legacy code already got right, and wrong

Reading the legacy modules the manifest seeds for G1 (`retry.py`, `errors.py`, `llm/call_transport.py`,
`llm/live_client.py`) on 2026-09-02:

- `retry.py` is a thin, typed `pydantic` model wrapping `tenacity.Retrying` with a per-operation-
  class policy table (attempts, backoff bounds, jitter). This already follows the principle — the
  legacy project's own dependency comment records replacing an earlier bespoke retry loop with
  Tenacity for exactly this reason. Porting the policy table is fine; the mechanism underneath it
  should keep depending directly on `tenacity`, declared as such, not reimplemented.
- `errors.py` is a plain exception hierarchy with no third-party import. No library replaces a
  project's own typed error taxonomy; this is correctly bespoke and not a candidate for this rule.
- `llm/call_transport.py`, `llm/live_client.py`, and every `llm/*_client.py` module build the
  OpenAI-compatible chat-completions protocol — request construction, response parsing, retries,
  fail-closed errors — directly on `requests`. `plans/idea.md` already specifies "a configurable
  OpenAI-compatible gateway"; the official `openai` Python SDK accepts a custom `base_url` and
  `api_key` and already implements request construction, typed responses, retries, and streaming
  against that exact protocol. The manifest's seed dispositions for these modules (`PORT_NEARLY_INTACT`
  for `call_transport.py`; `EXTRACT_AND_REFACTOR` for `live_client.py` and `*_client.py`) predate
  this review and do not yet reflect an evaluation of the SDK. Before either is pulled, G1-W03
  evaluates the `openai` SDK against the gateway's actual compatibility and records the outcome
  either way in the pull's manifest file record — reuse it if it fits, and if it does not (the
  gateway diverges from the protocol in a way the SDK cannot express), the file record names that
  divergence as the documented reason, not a default. The call ledger and provider-call attribution
  logic in `call_ledger.py` and `call_schema.py` are project-specific accounting, not something an
  HTTP client replaces, and stay ported as seeded.

### 18.3 Registry

One entry per cross-cutting concern this project will need. "First choice" is the option to reach
for; a work item that departs from it records why in its commit and, if the concern maps to a
manifest entry, in that entry's `note` field.

| Concern | First choice | Why | First needed |
|---|---|---|---|
| OpenAI-compatible LLM gateway client | `openai` SDK against a configurable `base_url` | Implements the protocol `plans/idea.md` already specifies; see §18.2 | G1-W03 |
| Bounded retry with backoff | `tenacity` | Already proven in the legacy retry policy table; stdlib has no equivalent | G1-W01 (clone, package-registry checks) |
| Typed data validation | stdlib `dataclasses` for simple records; `pydantic` only where a work item needs parsing, coercion, or nested validation a dataclass cannot express cheaply | Avoid a project-wide dependency until a concrete need states it; §5's fact record and disposition types may not need it | Declared per work item, not pre-added |
| CommonMark/Markdown parsing for inherited-README material-unit extraction | `markdown-it-py` | Legacy's own justification stands: a real token stream, not regex, is what a validator needs to not misclassify real input (§18.1) | G1-W02 (facts stage, inherited-unit inventory) |
| HTTP client for package-registry and link checks | `httpx` (or `requests` if a work item finds a concrete reason to prefer it — either is an established library, so this is not a departure either way) | Both are proven; pick one and use it consistently rather than mixing | G1-W01 or W02, first network check |
| PEP 440 / version-range matching | `packaging` | Legacy's own justification: proven interpreter/version-range resolution, not textual comparison | G1-W02 (Python range fact) |
| Multi-language public-surface parsing (.NET, Java, C++, Go, Rust, TypeScript) | `tree-sitter` with per-language grammars | Legacy's own justification for Rust applies to every ecosystem G3 adds: a maintained grammar, not textual pattern matching, resolves visibility, exports, and re-exports correctly | G4 (the shared extractor, §29.6 E2), then per ecosystem |
| Diffing for `README.patch` | stdlib `difflib`, unified format | A stdlib facility already solves this; no third-party dependency is a departure here, it is the default | G1-W01 (bundle stage) |
| Git operations | the `git` CLI via `subprocess`, never a custom client | The CLI is itself the established, battle-tested tool; a Python wrapper library adds a dependency without adding proven behavior | G1-W01 (snapshot) |
| Comment detection in generated example code, if a "no comments in visitor code" rule is adopted | `Pygments` lexers | Legacy's own justification: maintained lexers, not regexes that mistake URL-like string literals for comments | Only if `README_CONTRACT.md` adopts the rule; not yet decided |
| Dependency vulnerability and SBOM scanning | `pip-audit` | Already found a real CVE in the legacy project's own bootstrap `pip` the first time it ran | G6 (production readiness) |

A work item that needs a concern not listed here follows the same duty directly from `plans/idea.md`
§"Prefer Battle-Tested Solutions": research an existing option before writing one, and if none
fits, document why in the commit and add the concern to this table in the same change.

### 18.4 Model discovery and per-job routing (2026-09-02)

**Credentials.** The owner will not commit the gateway key, not even gitignored: `GPT_OSS_ENDPOINT`
(the OpenAI-compatible base URL) and `GPT_OSS_API_KEY` are process environment variables, already
present wherever this project runs; no `.env` is read or required for them. `GPT_OSS_MODEL` is an
optional override of a manifest's default route, for local experimentation only — it is never the
mechanism jobs use to pick a model day to day (below).

**Observed:** a `GET {GPT_OSS_ENDPOINT}/models` on 2026-09-02, authenticated, without printing the
key, returned HTTP 200 and seven entries: `qwen3-next`, `gpt-oss`, `qwen3-embedding-8b`,
`Qwen2.5-VL-7B`, `stable-diffusion-3.5-large`, plus two alias slots, `recommended` and `experimental`.
Only the first two are general-purpose chat/completion models suited to the six governed jobs;
`qwen3-embedding-8b` is an embedding model, `Qwen2.5-VL-7B` a vision-language model, and
`stable-diffusion-3.5-large` an image generator — none fit a job that returns typed prose or JSON
content units. The catalog is heterogeneous and gateway-controlled, not a small fixed set this
project can hardcode.

**Rule.** `preflight` (G1-W03) discovers the catalog from `/models`, not from an assumption, and
records it; it is not queried again mid-job. Each prompt manifest declares its own `model_route`,
chosen from the discovered catalog for that job's fit — reasoning depth for
`independent_review`/`targeted_repair`, lighter cost for `section_authoring`, and so on — as a
reviewed, versioned decision recorded in the manifest, exactly like every other manifest field
tracked in a candidate's `dependencies.json`. "Explore and use whichever fits" means this review,
done when a manifest is authored or updated, never a live per-call choice: principle 20 already
requires model route to be a stable, attributable input, and a route that varied call to call would
break no-op proof (S12) and per-candidate invalidation alike.

An alias route (`recommended`, `experimental`) is allowed in a manifest only if the ledger records
the concrete model ID the gateway actually served for every call, not just the alias name — an alias
can resolve differently over time on the gateway's side, and attribution must survive that. A model
that disappears from the catalog is `FAILED_INTERNAL` for any manifest still routed to it, fixed by
re-pointing the manifest to a discovered replacement, never by silently retrying another model.

## 19. Comparative research: a sibling system that shipped (2026-09-02)

**Observed:** `aspose.org`'s `readme-refresh` skill (`skills/readme-refresh.md`, 1,471 lines) and
its companion checks module (`readme_refresh_checks.py`, 11,002 lines, 115 `check_*` functions) —
18,532 lines total across the three core scripts — generate and validate READMEs for 31 products
in this same portfolio, accumulated over 57+ documented incidents from 2026-08-04 onward. Unlike
`foss-readme-optimizer`, it works: real PRs, real merges, a real portfolio in production.

**The load-bearing difference, not to lose sight of:** it is not fully autonomous. `approve` and
the PR merge step are explicitly documented as "never on this skill's own initiative, only on an
unambiguous, fresh instruction from the user in that turn," and composition itself happens inside
an interactive session — "the script does not write README prose — the agent reads `factpack.json`
and writes `readme.md` directly." `plans/idea.md` commits this project to scheduled, unattended
runs with no per-candidate human touch. That target is unchanged and correct, but this sibling
system's track record is evidence for its deterministic-extraction-and-validation layer, not proof
that unsupervised composition reaches the same quality — the two are different claims.

**Adopted directly into `README_CONTRACT.md` this session** (both real, confirmed defects on this
exact portfolio, not hypotheticals): the implementation-bridge non-disclosure rule ("via Java", "a
wrapper around X" — never anywhere in the document) and the Enterprise Edition anchor's family-vs-
platform precision (a platform anchor never leaks which implementation the resolved URL happens to
use). Both are now in §2's "Never present" list and the `enterprise_relationship` row.

**Recorded here, not yet built — each tagged with the gate whose work actually consumes it:**

- **Rewrite fidelity scoring** (a word-overlap score naming missing content for a
  `VERIFIED_REWRITE` disposition, not just the category label — the sibling system caught a
  reframe that silently dropped "returns a copy of the messages collected during the most recent
  run" while every categorical check passed). Belongs in `source_reconciliation` (S4) or validation
  (S9), first needed when G1-W04/W05 build those stages; `README_CONTRACT.md` §5's advisory list
  already names it.
- **Doc/code parity check** — a test failing if `README_CONTRACT.md`'s semantic shell or blocking-
  check list names something the real renderer/validator code doesn't implement, or vice versa
  (the sibling system's `check_readme_template_contract_parity.py`). Cannot be written before the
  renderer exists; first needed at G1-W05 once S7/S9 are real, as an acceptance criterion for that
  work item, not before.
- **Already-published self-diff tautology** — once a candidate has merged, re-running preservation
  tracking against the now-identical live README is a pure tautology and produces false failures
  (confirmed live on the sibling system: 158 of them, one product, before it added the check). Not
  relevant before G5 (proposal/update-vs-duplicate); a design note for whoever builds that gate.

**Deliberately not adopting**: the sibling system's per-product run-state-machine — file locks,
orphaned-session adoption, cross-session ownership checks. Real infrastructure it needs because
multiple human operators work the same portfolio concurrently; building it now would violate
principle 18 (infrastructure is just-in-time). G4's own leases/fencing/CAS design is this
project's answer to the same underlying problem, timed to when concurrent hosted runs actually
exist. Do not port theirs; do study its `--adopt-orphaned` liveness-check shape when G4 designs
its own.

## 20. Enterprise/backlink resolution: adopt the algorithm, not the data (2026-09-02)

**Observed, following up on §19 at the user's direction:** `aspose.org/data/aspose_com_targets.json`
(19.5 MB, real sitemap fetches from products/docs/reference/kb/blog.aspose.com, `http_status: 200`
and a `last_verified` timestamp on every entry, generated 2026-08-21) and its consumer,
`scripts/pipeline/lib/backlink_targets.py` (1,658 lines). This is a materially better-verified
source than the legacy `foss-readme-optimizer` catalog flagged in §7.2.1 (that one: 44 of 7,755
records ever live-checked). `resolve_backlink()` is the specific, reusable piece: family/platform
lookup with a canonical `PLATFORM_ALIASES` table (real bridge slugs — `python-cpp`, `go-cpp`,
`rust-cpp` — each a documented, hard-won correction), a platform-then-family fallback, and explicit
`AMBIGUOUS_PLATFORM_TARGETS` handling when two verified variants exist with no rule to pick between
them (never silently choosing one).

**Decision: adopt the resolution shape and the alias taxonomy as a design reference; do not pull
the data file or the module.** Three reasons, not just caution for its own sake:

1. **Wrong shape for the need.** That data file and module solve aspose.org's own problem — bulk,
   offline backlink resolution for SEO compliance across an entire site's worth of pages, plus
   anchor-slot registries and per-page link-quota policy this project has no use for.
   `enterprise_link` here is one lookup per candidate, not a portfolio-wide precomputed catalog; a
   live, on-demand check (`GET https://products.aspose.com/{family}/{platform}/`, falling back to
   `/{family}/`) is simpler, always current, and matches this project's own "verify what you
   actually use" rule (§7.2.1) better than ingesting 5,200 curated + 75,729 raw entries most
   candidates will never touch.
2. **Wrong source model.** `migration/reuse-manifest.yaml`'s pull-based reuse is scoped to one
   frozen revision of `foss-readme-optimizer`, retired and never changing again. `aspose.org` is a
   live, actively-developed sibling repository — pulling code or data from it is a different kind
   of dependency than migrating a dead system's parts, and would need its own, explicitly-decided
   sourcing model (a second reuse source, or a periodic-refresh boundary) before any file crosses
   over. That decision was not made here — flagged for the owner, not assumed.
3. **The genuinely portable part is small.** `resolve_backlink`'s core logic and the
   `PLATFORM_ALIASES`/`KNOWN_FAMILIES` tables are a few hundred lines of real, tested knowledge
   about this exact product portfolio's platform-naming quirks — worth reimplementing cleanly for
   `enterprise_link`'s own fact extractor, citing this research, not copy-pasted from a non-migration
   source.

**First needed**: G1-W04 (composition) — `enterprise_relationship` and `documentation_resources`
are exactly what's being built now. A minimal version for the canary: live HTTP check against
`products.aspose.com/{family}/{platform}/` then `/{family}/`, `family`/`platform`/`unresolved`
classification matching `README_CONTRACT.md` row 15's existing rule, omit the section on
`unresolved` — no bulk catalog required for one product. The alias table only matters once a second
ecosystem's platform-slug quirks show up (G2 onward); adapt entries from `PLATFORM_ALIASES` as
that need appears, not all at once now.

## 21. Two future components: research only, not scheduled (2026-09-02)

Per the owner: the metadata component and the upstream-defect logger (both named in `plans/idea.md`
— "Central Agent" responsibilities and the "Upstream Defect Reporting" section) will be logged and
implemented separately once the README component is done. Nothing here creates a gate or work item;
`EXECUTION_STATE_MACHINE.md` already carries their eventual seams (G6 item 4 and G7 items 4 and 5)
and is left alone. This section only records what already exists to draw from, so the research
isn't repeated or lost by the time either component starts.

### 21.1 Metadata (repository description, topics, social preview, org icon)

**The real, ready-to-adopt design already exists in `foss-readme-optimizer`, not aspose.org.**
`docs/github-surface-control.md` (102 lines) and `docs/repository-presentation-surface-model.md`
(83 lines) define five control classes covering every GitHub-repository-page surface, each with a
truth owner, a real documented API endpoint or its absence, and a forbidden-operations list:

| Class | Surfaces | Apply channel |
|---|---|---|
| A — repository-file | README, LICENSE, community files, issue/PR templates | Normal PR flow — already this project's native model |
| B — API/settings | description, homepage, topics, feature settings | `PATCH`/`PUT /repos/{owner}/{repo}[/topics]`; proposal-only until a write credential and apply gate exist |
| C — manual UI | social-preview image | No documented write API; prepare an asset + instructions, track a status machine, never claim applied without operator evidence |
| D — product-agent owned | releases, packages | Audit/handoff only, no writer, ever |
| E — GitHub-generated | contributors, languages, stars/forks/activity, page layout | Audit-only, never a quality gate |

This maps directly onto `plans/idea.md`'s own list ("repository description... topics, visuals,
and social-preview image... community, contribution, licensing, and security files... auditing
GitHub-generated information without treating it as directly editable metadata") almost clause for
clause — the framework already fits the product spec, not the other way round. Concrete,
transferable findings baked into those two documents, independently verified there:

- **License-file placement, not presence, is the highest-value target**: 28% of that project's own
  25-repository registry had real license content GitHub's Community Profile API didn't recognize
  (wrong filename or location) — a Class-A, file-only fix. Worth checking against this project's
  own 34 repositories when this component starts; plausibly a quick, high-value win.
- **GitHub Packages is universally unused**: confirmed empty on n8n, iText, EPPlus, SheetJS, and
  Apache PDFBox despite all being real, widely-distributed libraries. Never target populating it;
  validate the real external registry instead (already this project's own `installation` design).
- **Community-file quick-links are automatic** — GitHub renders the README/Contributing/License/
  Security row itself from file presence and Community-Profile-API recognition; nothing to build
  for that appearance beyond placing the files correctly (Class A).
- **The org-level icon/avatar is not covered by either document** — both are scoped to
  per-repository surfaces; an organization icon is shared across every repository in one Aspose
  GitHub org and would need its own control-class entry (likely B, via the orgs API, pending
  verification) when this component is actually scoped.

`src/readme_agent/capabilities/propose_metadata_changes.py` (150 lines) is a working, small,
already-correctly-scoped reference implementation of the Class-B slice: read current
description/homepage/topics via the real GitHub API, propose a value only where the field is
genuinely empty and governed facts support it, cite the facts, never PATCH. A reasonable
`EXTRACT_AND_REFACTOR` candidate when this component's own work item exists — not pulled now.

### 21.2 Upstream defect logger

**`aspose.org/scripts/pipeline/commands/foss/upstream_issue_workflow.py`** (2,059 lines) is a
working, production-proven implementation of close to exactly `plans/idea.md`'s own spec: fires
only after independent verification against evidence, deduplicated, never fabricates severity,
interim evidence-backed handoff until issue creation is authorized. Confirmed not present in the
`foss-readme-optimizer` migration source (including its `vendored_asposeorg/` subset) — this is the
one place to look when the time comes.

Real, transferable shape:

- **Two-tier state machine**: a `Finding` (`DISCOVERED → VERIFYING → VERIFIED →
  DUPLICATE_CHECKED → BUNDLED`, or a named terminal — `REJECTED_NOT_UPSTREAM`,
  `DUPLICATE_EXISTING`, `FIXED_UPSTREAM`, `PRIVATE_SECURITY_ROUTE`, `BLOCKED_MISSING_EVIDENCE`,
  `DEFERRED_LOW_PRIORITY`) and a `Bundle` (`BUNDLED → DRAFTED → INDEPENDENTLY_REVIEWED →
  READY_TO_CREATE → CREATED → REMOTE_VERIFIED`) — kept as two entity types with two lifecycles
  deliberately, not one graph, because a finding and a filed issue are genuinely different things.
- **A real GitHub Issue is created only via an explicit `--live` flag, never the default** — the
  same dry-run-first posture this project already requires for every effect (`AGENTS.md` Security
  and Effects). `severity == "critical"` unconditionally forces a private security route at
  classification time, never left to drafting-time judgment.
- **Deduplication is a real, read-only search across five GitHub surfaces** (issues, PRs, cross-repo
  issue search, commit messages, latest release) before a bundle may be drafted.
- **A bundle can never reach `INDEPENDENTLY_REVIEWED` on automated checks alone** — a real, separate
  positive reviewer verdict is structurally required before creation, matching this project's own
  "independent review... separate identity" invariant for README candidates.
- **The draft is composed from structured, already-verified fields, never by copying raw internal
  evidence text verbatim** — a real, confirmed leak (internal audit-trail phrasing reaching a public
  draft) was fixed by hand-editing the draft directly, not by re-deriving it, since the leak
  originated in the internal field itself.
- **Identity is re-verified on every call, dry-run or not** — a rehearsal whose preview doesn't
  reflect a real identity check would be a misleading rehearsal.

**Same sourcing caveat as §20**: this is a live sibling repository, not the frozen migration
source — the state-machine shape and safety mechanisms above are worth reimplementing cleanly for
this project's own upstream-defect logger, cited as precedent, not pulled as code, unless the owner
separately decides to treat `aspose.org` as a formal second reuse source.

**Already anticipated correctly**: `EXECUTION_STATE_MACHINE.md` G6 item 4 (interim handoff, seeded
by the real Aspose.Email FOSS for .NET `CS1929` case) and G7 item 4 (automated creation behind its
own authorization and deduplication ledger) already match this shape — this section grounds that
plan in a working reference, it does not change it.

## 22. The G1 canary candidate against a live comparable (2026-09-03)

**Why this matters more than a normal quality review**: `aspose-3d-foss/Aspose.3D-FOSS-for-Python`'s
live, currently-published `README.md` was confirmed byte-identical (`diff -B -b`) to aspose.org's
own regenerated candidate for the same product. That candidate cannot be rolled back and a reduced
version cannot be pushed over it. This project's own candidate for the same repository is therefore
not competing against an abstract quality bar — it is competing against what a real visitor already
sees today, and it currently loses on several fronts.

### 22.1 Confirmed defects in the sealed G1 bundle, with cause

- **Duplicated `scope_limitations` and `documentation_resources`.** `renderer.py` placed disposed
  inherited units after the section's own plan-driven content with no overlap check. Fixed as a
  contract rule in §3 above (placement is exclusive on fact-ID overlap); the code fix is
  `components/readme/composition/renderer.py`.
- **Missing Enterprise Edition link.** `plan.json` correctly omitted it — `enterprise_target_url`
  was `null` because nothing has ever computed it. §20 above already scopes the fix (a live
  `products.aspose.com/{family}/{platform}/` check); it was never built during G1-W04.
- **Missing banner image.** No fact kind, no shell row existed for it at all — not a deferred
  visual-asset decision (that's GitHub's social-preview surface, genuinely out of scope per
  `plans/idea.md`); a verified image-plus-homepage link is the same kind of fact as the Enterprise
  link and was simply never modeled. Added as shell row 3 above.
- **Missing At a Glance.** Every *input*-direction format fact (`.dae`, `.obj`, `.stl`) was
  `UNRESOLVED` while *output* formats (`.gltf`, `.stl`) were `SUPPORTED` — the bundled verification
  examples only build-and-save, never load an existing file, so input formats never get corroborating
  evidence even though the product genuinely reads them (the candidate's own opening sentence says
  so). A facts/verification-coverage gap, not a shell-rule gap; first relevant work: whichever future
  iteration extends example verification or adds static corroboration for a format claim, matching
  the "2-of-3 corroboration" pattern aspose.org already uses for exactly this problem.
- **Dependencies omitted entirely rather than stating verified-zero.** Fixed as a contract rule
  (row 9 above, `Required` not `Conditional`, four subsections, explicit-zero sentence).

### 22.2 The candidate's own review already caught three of these — and one repair attempt failed for a structural reason

`review.json` for the sealed bundle records `verdict_as_returned: REJECT_FACTUAL`, downgraded to
`ACCEPT` with seven advisory findings after `targeted_repair` (S11) re-raised on each. Three of the
seven (F04, F05, F06) are exactly the duplication defect above. **The repair attempt could not have
fixed it**: `targeted_repair` revises LLM-owned content units; this defect's cause is in the
deterministic renderer's placement logic, a layer no content revision touches. The process followed
its own rule correctly (one repair attempt per fingerprint, then advisory, never a second block) —
the gap is that an advisory finding caused by a code defect needs to reach that code, not just stay
advisory forever. §23 below makes this a durable rule. The other four advisory findings, also still
live in the sealed bundle and worth folding into the same repair pass:

- **F02** (`installation`): the candidate's install command doesn't disclose that the original
  README flagged the package as not yet published on PyPI — now covered by shell row 8's addition
  above.
- **F07** (`development_testing`): the shipped candidate still reads "run... a single test file with
  `python -m unittest tests`" — an incomplete command; the verified example fact names
  `python -m unittest tests.test_obj_importer`. Now covered by shell row 17's addition above.
- **F01** and **F03** are narrower wording judgment calls (a "current version" phrasing nuance; the
  non-standard "Hub APIs" sub-heading) — real, but lower priority than the five above; leave for the
  same repair pass to triage, not a contract change.

### 22.3 Portfolio-wide, from aspose.org's own operational reference

`docs/readme-refresh/current-operational-reference.md` §11 lists genuinely open items across their
31-product portfolio, current as of their last snapshot (2026-08-20) — useful both as things to
avoid and as evidence of where this project can concretely do better, not just avoid regressing:

- **Real per-language example verification exists only for Python** (partial for TypeScript);
  Java/.NET/Go/Rust/C++ get an honest `BLOCKED-WITH-REASON` stub, never an executed example. This
  project's own G3 (one verified representative per ecosystem, each with a negative control) is
  already scoped to do better across all seven ecosystems — this is independent confirmation the
  gate is pointed at a real, currently-unsolved gap in the comparable system, not a redundant one.
- **Fabricated API claims reached published candidates before being caught**: a hallucinated
  `SheetVisibility` API (`cells/java`), a hallucinated public `FontRepository` type (`pdf/go`), a
  false "PDF/X out of scope" claim (`pdf/java`), a stale fabricated dev-dependency claim
  (`words/python`, `slides/python`) — all found and fixed 2026-08-20, all real, all shipped for some
  period first. This is the concrete cautionary evidence for why this project's own
  fact-ID-binding-checked-before-render design (§3 above; `binding_errors` in
  `core/llm/jobs.py::_parse`) exists — the failure mode is real and has happened to a system that
  otherwise works well. Never weaken that binding check for convenience.
- **"Local ahead of live" has no general detection** (`W5`, open, blocked on design): their
  byte-compare `published` check can tell local-differs-from-live but not local-is-strictly-ahead.
  Worth remembering once this project's own G2 dependency-invalidation and eventual G5
  publish-vs-live reconciliation are designed, so the same structural gap isn't reintroduced.
- A specific, named, still-open content-quality defect: `pdf/cpp` carries "182 filler descriptions"
  in its API Reference (P4, deferred) — a reminder that "collapsed in `<details>`" (this project's
  own rule, §2 row 12) bounds visible length but says nothing about whether what's inside is
  curated or mechanically generated filler; `key_capabilities`/`api_reference`'s existing
  evidence-backed-description requirement already guards against this, worth keeping in mind as a
  review question when G2's acceptance profile is written.

## 23. Advisory review findings are deferred work, not resolved work (2026-09-03)

An advisory finding is not "done" because it stopped blocking. `EXECUTION_STATE_MACHINE.md` §9
already says a reviewer rejection routes to its causal stage, or — if unrepairable within
`targeted_repair`'s scope — becomes advisory and the *reviewer scope* gets fixed. §22.2 above is a
concrete case where the second half of that rule didn't happen: the finding went advisory and
nothing then routed it to the renderer. Any work item that touches a candidate's sealed bundle reads
that bundle's `review.json` `advisory` list first; a finding whose cause is a deterministic-code
defect (not a prose-quality judgment call) is real, tracked repair work, not accepted permanently.

## 24. Systematic shell comparison against the live portfolio (2026-09-03)

**Method.** A scripted structural census of **all 32** aspose.org candidates under
`reports/repo-presenter-regen-full/` (headings, badges, banner, Enterprise link count and section,
Mermaid fences, per-section fence and bullet counts, API table rows, `<details>` summaries, images,
visible-versus-total lines), plus full reads of `3d/python` (live byte-identical), `cells/java`,
`barcode/python`, `pdf/go`, `cells/rust`, and their machine-readable contract
(`data/readme_template_contract.json`: ten required sections, six section-body invariants each tied
to an enforcing check, 117 checks). Compared section by section against `README_CONTRACT.md` §2 and
against what `renderer.py` and `shell.py` actually emit for the G1 canary. A first pass on five
candidates reached a wrong conclusion on the API Reference (below); the census and the owner's
product decision corrected it. Portfolio-wide constants, all 32/32: banner present; exactly one
Enterprise link, always the closing paragraph of Scope and Limitations; exactly one Mermaid fence
with nothing else in At a Glance; every one of the twelve standard sections present. Visible lines
115–310; total lines 272–3,172; API table rows 11 (`tex/python`) to 1,026 (`pdf/java`).

| Aspect | Live portfolio convention | Was in this project | Decision |
|---|---|---|---|
| Badges | Evidence-driven per ecosystem (Maven Central + Java floor; CI + pkg.go.dev for Go; crates.io absent when unpublished); floor = license + one more | Fixed list, renderer hardcoded to `install_command:pip` and `package:python_requires` | Matched: badge registry keyed by ecosystem, floor rule (row 2). Generalises with G4-W10's second ecosystem |
| Banner | `[![Name](products.aspose.org/media/{f}/{p}/banner-readme.png)](products.aspose.org/{f}/{p}/)` on all 5 | absent, unmodeled | Matched (row 3) |
| Navigation | explicit `## Navigation` heading | headerless list | Matched (row 5) |
| At a Glance | present on all 5, including the generative one (no Starting Points); `flowchart TD`; one Starting Points node listing formats; single chain edge; ≤28-char tokens (hard gate) | condition required an input format, so the canary got none; `graph LR` with one node per input format and per-format edges | Matched and simplified: condition is three capabilities, inputs optional; single listing nodes; one edge per hop; label-geometry rule (§2.1) |
| Key Capabilities | 6–8 dense bullets naming real members; a limited capability says so inline with a link | bold title + one sentence | Kept ours, added the inline-limitation cross-reference (row 7) |
| Installation | registry install in every idiomatic form (Maven **and** Gradle), source-install fallback, verify command, runtime sentence | one `pip install` line | Matched (row 8) |
| Dependencies | always present, four subsections, explicit verified-zero sentence with manifest evidence | omitted when zero deps | Matched (row 9; §22) |
| Quick Start | one or two examples, each with a lead-in | one | Matched (row 10) |
| Additional Examples | lead-in, one visible flagship under a `###` heading, then one `<details>` holding the rest under task-named `###` headings | one `<details>` per example | Matched (row 12) — a visible flagship aids scanning (22 of 32 have one); the live anchors follow this shape |
| Project Structure | optional, when the old README had a tree; canonical box-drawing characters | no section id — a preserved tree would have no destination | Added (row 13) |
| API Reference | 32/32 present. Visible intro naming entry-point classes and the public type count; one `<details>` (summary text varies across nine wordings — "View the Supported Public API Surface" 13, "View the Core API Surface" 9, …); `### Core API` table on 22, module-grouped `###` tables on the rest; `#### Enumerations` (71 occurrences), `#### Interfaces` (22), `#### Structs`/`#### Traits` (Rust); `#### Detailed Member Reference` on 24/32 with `### Topic` groups of nested member bullets. Rows: 11 to 1,026. Quality gap, not a design gap: mechanical filler rows exist ("Class with 9 methods and 8 properties and 49 members"; "Class extending Exception"), and their own tracker carries "182 filler descriptions" on `pdf/cpp` | ≤12 curated hubs; no visible intro; summary "Hub APIs"; **bug**: 17 inherited units rendered visible below the closed `</details>` | **Matched and exceeded — the first-pass "deliberate divergence" was wrong and is withdrawn.** The owner's product decision: most FOSS repositories have no dedicated reference, so the README's complete API reference is required. `plans/idea.md` never forbade it (its line 107 names API Reference as a canonical destination for preserved APIs; line 117's "not a fact inventory" is about the composer's prose); the "no generated API inventory" phrase was this project's own governance overreach, now removed from the contract and loop prompt. Row 14: required, complete verified surface, standard summary text, kind-split tables, Detailed Member Reference — and the exceed: every description evidence-backed, filler rows structurally impossible because the table is deterministic from `public_symbol` facts |
| Documentation & Resources | `&` in the heading; bold link — em dash — one sentence; reference item states the public type count; repository-relative tracked docs; "Open an issue" line | "and"; LLM intro sentence; compact link list **and** a preserved descriptive list (duplication bug) | Matched: heading, item shape, type count, tracked docs, issues line, one list (row 15) |
| Scope and Limitations | bullets only, precise mechanism per bullet (`NotImplementedError`, `RuntimeError`, exact class); **Enterprise paragraph is the section's closing paragraph** | LLM scope sentence + bullets + duplicated preserved paragraphs; Enterprise as a separate later section | Matched: bullets with one optional scope sentence, precision rule, Enterprise paragraph moved to close the section (rows 16, 18). The owner's own reading — "the missing Enterprise link in the limitations section" — confirms this is where a reader expects it |
| Development and Testing | prose + fenced commands, suite-size sentence, release-workflow link | summary + bare asset list (`tests/`, `.github/workflows/`, `docs/`) + commands | Matched (row 17): assets named in prose, release link (8 of 32 carry one — conditional, not required), exact single-target command |
| License | fixed sentence + permissions + "provided without warranty" | prose from the license fact | Matched (row 20); 31 of 32 use the linked form |
| Length | Visible 115–310 lines across all 32; total 272–3,172, the difference almost entirely the collapsed reference | 300 visible / 600 total budget | Visible budget kept and set to 320 (the portfolio's own ceiling); the total cap was wrong once the complete reference is required and is removed — what is read stays short, what is looked up is complete. Also corrected: the "793-line candidate" this project's governance named as the failure was an *old* 3D/Python candidate (§3, line 114) whose defects were a split identifier and unverified filler; the live 3d/python being the same length is coincidence, not the failure |
| Images | `font/python` 5 (generated SVG/PNG previews), `page/python` 3 (rendered outputs), `words/python` 1 (embedded data-URI PNG), all inside Additional Examples under their own headings; `pdf/go` 1 preview in a Feature Showcase section linking the full asset. Their own history records excluding screenshots "because no template section exists" as a real defect (MT051) | no image handling beyond the banner; a preserved image unit would have had no destination | Matched: row 12 preserves verified repository-owned images inside Additional Examples with alt text and snapshot-resolved paths; row 11 adds Feature Showcase |
| Deliberate additional sections | Across all 32: Project Structure (4: `cells/go`, `cells/java`, `cells/rust`, `pdf/cpp`), Third-Party Notices (2: `pdf/cpp`, `pdf/go`), Feature Showcase (1: `pdf/go`). Nothing else. Every one exists because the repository genuinely carries that material | closed shell; a material inherited section with no row failed closed or was dumped | Matched: the deliberate-additions rule (§2, after the table) — a plan `deviation` naming the units or assets it rests on, at the row's position; the observed set is exactly the three rows added |
| Preserved-unit placement | disposition sidecars + retention report + gates | trailing append, no overlap check, no collapse awareness, excluded destination dropped silently | Three rules added (§3): exclusive on fact-ID overlap, inherits section visibility, excluded destination fails closed or re-routes |

**Where this project is already ahead, and should stay ahead**: fact-ID binding checked before render
(no fabricated API claim can reach a candidate — the failure class §22.3 shows reached production
in the comparable); a fresh-process zero-call no-op proof; per-candidate `dependencies.json`; a
visible-length budget; and, once G3 lands, executed example verification for every ecosystem rather
than Python alone. Matching the live portfolio's shape is the floor; these are the reasons a reader
should prefer this project's candidate.

## 25. Steering correction: converge before expanding (2026-09-03)

**The risk, measured.** Between 2026-09-02 and 2026-09-03 this file grew from 1,013 to 1,419 lines
and `README_CONTRACT.md` from 177 to 237, with three contract revisions, while `G2-W02`'s purpose
grew from "fix five defects" to a 3,077-character item spanning the whole revised shell — and
candidates stayed at 1/34. That is the legacy post-mortem's own line, "infrastructure and acceptance
contracts expanded faster than visible output" (§3.6), reappearing in the steering layer even while
the architecture the legacy lacked (per-candidate invalidation, no supervisor loop, a working
transaction at gate 2) is present and proven. Two contract citations of `plans/idea.md` were also
written before being verified against the file, and were wrong (§24). The corrections:

- **`G2-W02` split into three converging items.** (a) `G2-W02`: seal the deterministic rows already
  built plus the small remaining ones, superseding `65b1f577`; the interim candidate keeps the
  hub-list API Reference and says so. (b) `G2-W03`: the complete API Reference, with the extraction
  work below done first. (c) `G2-W04`: banner, Enterprise paragraph, At a Glance, images, the two
  optional rows. Each seals something a reader can see.
- **Contract revision hold** (its status line) until `G2-W02` seals; only a proved-wrong predicate may
  change. Gaps go in this file, not the contract.
- **Authority written once** (contract status line): `plans/idea.md` decides, the contract implements,
  aspose.org's output is an oracle — evidence, never a third authority.
- **A work-item size rule** in `loop-prompt.md`: about a thousand characters, a handful of iterations,
  split rather than widen.
- **My own discipline**: verify a `plans/idea.md` citation against the file before writing it into a
  rule; consolidate §19–§25 into one comparative-research section once `G2-W04` seals rather than
  keep appending.

**The API Reference extraction gap, for `G2-W03` — read before touching the facts stage.** Checked
on the sealed `65b1f577` bundle's `facts.json`: 1,918 `public_symbol` facts, every one with
presence-only evidence (`"line 15; class; public by name"` — a path, a line, a kind word inside a
free-text `detail`). Three specific gaps stand between that and row 14's "every description
evidence-backed":

1. **No descriptive evidence is extracted.** No docstring, no signature. The rule cannot be met from
   these facts as they stand; the extractor must record the symbol's docstring first line and its
   signature (or the class's public member names) as evidence fields.
2. **Re-export paths are separate facts.** `Box` is three facts (`aspose.threed.box`,
   `aspose.threed.entities.box`, `aspose.threed.entities.box.box`). The live README's table for this
   product has 305 rows; 1,918 raw facts collapse to roughly that once each symbol is recorded once at
   its canonical defining location, with its public re-export paths as evidence, not as duplicates.
3. **Kind is not a field.** "module"/"class" lives inside the `detail` string; the table's split by
   kind (`#### Enumerations`, `#### Interfaces`, …) needs a structured `symbol_kind` on the record.

And a budget consequence: `section_authoring` allows 8,000 output tokens (already the largest of the
six jobs) — not enough for one description per type in one call. Author the descriptions in bounded
batches keyed to the deduplicated type list, or derive the description deterministically from the
docstring first line where one exists and reserve the LLM for types without one — either is
consistent with §3's "renderer owns structure, LLM owns bound prose"; a single oversized call is not.

## 26. Advisory findings whose cause was code, verified against the artifacts (2026-09-04)

The candidate sealed at `65b1f577` after G2-W02–W04 matches the live README on every structural
axis (§24's twelve sections, banner, one fence, 343 API rows with no filler, 128 visible lines). Its
`review.json` carries five advisories under `verdict_as_returned: REJECT_PRESENTATION`. Checked each
against the rendered sections and the plan, not the reviewer's wording:

- **F03 and F05 are false alarms.** Installation has the source fallback, the verify command, and the
  runtime sentence; Scope and Limitations has six precise bullets naming `RuntimeError`,
  `NotImplementedError`, `IOService`. The reviewer's quotes were truncated to the first block.
- **F02 is real and code-caused.** Three of seven Key Capabilities describe a different capability
  than their title: comparing each `capability:N` unit's `fact_ids` with its plan slot's, slots 1, 6,
  and 7 overlap their own title's facts 2/5, 0/1, and 0/4 and best-match other slots. `binding_errors`
  checks that cited facts exist and are `SUPPORTED`; it never checks that they belong to the slot's
  planned fact set. The previous candidate showed the same symptom. Reader-visible: "Load multiple 3D
  formats" followed by a sentence about constructing meshes.
- **F04 is real and code-caused, for a different reason than the reviewer gave.** 343 rows against
  the live 305 is not "match the old README" — it is 14 duplicate pairs of the form
  `formats.ColladaLoadOptions` / `ColladaLoadOptions.ColladaLoadOptions`: the package `__init__`
  re-export and the class inside a same-named module survive the re-export collapse as two facts, the
  disambiguation rule then qualifies both, and each gets its own authored description. ~329 unique
  after collapse.
- **F01 is real and a coverage gap** (§22.1): no input format is `SUPPORTED`, so At a Glance has no
  Starting Points, and Outputs lists glTF and STL only while the product also writes OBJ and 3MF.
  Executed save-examples are the only corroboration today; `FileFormat` and importer/exporter plugin
  registrations are static evidence that would corroborate every format the product declares.
- Minor, prose: the Enterprise paragraph's second sentence adds "enhanced performance, and commercial
  licensing" — not a verified addition; the live version names PDF, PLY, USD, rendering, mesh operations.

**The process gap.** G2-W02–W04 were accepted under "zero advisory findings whose cause is
deterministic code" with F02 and F04 present. Cause was read off the reviewer's repair text — all five
are phrased as prose edits — instead of being tested. The durable fix: a finding's cause is decided by
whether a deterministic check can express it. Slot-bound facts and canonical-identity uniqueness both
can, so both become checks that block at S9 and never reach the reviewer as a judgment call; only a
finding no check could express is prose. `loop-prompt.md` §5 now says so; G2-W07 does the work.

**Gaps G2-W02 recorded (2026-09-03), for the rows it owned.** Neither is a contract change; both are
report lines under the revision hold:

1. Row 17's "single-target run copied exactly from its verified example fact": the facts stage
   executes example code, not build or test commands, so no fact verifies
   `python -m unittest tests.test_obj_importer`. The candidate keeps the inherited README's command
   block verbatim (reconciliation refuses to omit a shell-fenced block while build or install facts
   exist) rather than claiming verification. Executing one test target in the isolated workspace
   belongs with G2-W03's facts-stage work.
2. "A new sealed bundle supersedes 65b1f577 per `superseded_by`": a bundle is addressed by source
   revision, so a re-composition at the same revision cannot supersede itself by directory. The seal
   adopts a proven update in place and keeps the previous proof under `adopted`; that is the
   equivalent the evidence manifest records, and `superseded_by` stays for a newer source revision.
3. Row 6's Starting Points on the canary (G2-W04, 2026-09-04): the diagram renders without them
   because every `format:input.*` fact is UNRESOLVED, while the live README lists five inputs. The
   examples that read a file (`example:001`, `:007`, `:011`) do not execute in the isolated
   workspace, which has no fixture files, so no input format is verified; the outputs are verified
   because the writing examples run. The section itself now renders under the revised condition,
   as the contract requires for a product that creates from scratch. Provisioning fixtures for
   file-reading examples belongs with the facts stage, not the contract.

## 27. Production reassessment: what breaks consistency across reruns, and the durable design (2026-09-04)

Evidence base: four read-only code audits at HEAD `3a59a6b` (cache and determinism; planning and
authoring; review, repair and acceptance; fact extraction) plus a census of the sealed canary at
`65b1f577` (395 provider calls, 39 rejected outputs on disk, 27 repair attempts, 11 checks, 191
content units) and its predecessor `d9f3bfe5`. Every mechanism below is cited to a file and line;
every magnitude comes from one repository in one ecosystem and is indicative, not general. Where
the evidence is thin it is said.

### 27.0 Decisions in force (read this first; updated 2026-09-11, PHASE1/F3)

The loop reads this list every iteration and the subsection an item cites; whole sections only when
diagnosing. Each line names where the detail lives.

- **Currency note (2026-09-11).** This list predates the arrival-list era: rulings on G4-W17
  arrival items 0–49 live in `docs/DECISION_LOG.md` (§31, append-only; an entry stands until a
  later entry names it with `REVERSES`), and the PHASE1 sprint's standing rulings (item 49
  declined; RC-03 and PA-05 deferred; NEW-A..E authorized; Cells-Cpp re-seal policy; venv freeze)
  are recorded there dated 2026-09-11. `plans/sprint/PHASE1-SPRINT-PLAN.md` is the sprint
  reference. This subsection stays the index for pre-arrival-era decisions D1–D7 below; it is
  refreshed at each gate change, not per item — per-item currency is the DECISION_LOG's job.

- **D1 constructive generation — landed (W12).** Per-call schemas for four jobs; measured
  first-attempt acceptance 85–92%; the regression floor is 85% (27.10 f/u 3). Remaining prose
  families (URL, command in a sentence) become referential in **G2-W20**. The gateway answers
  HTTP 400 for `pattern` in strict `json_schema`: never use `pattern`; use enums, `minItems`/
  `maxItems`, `maxLength` (27.10).
- **D2 title binding — landed (W13). D5 content-only acceptance — W16 in progress** (bounded review
  output landed; a re-raised finding blocks, never demotes). **D6 coverage ledger — W17.**
  **D3 anchoring, D4 portable proof, fan-out — G5** (27.10: anchoring cannot help a first candidate).
- **`seed` is honoured** by `qwen3-next` (two identical calls, identical bytes; `catalog.json`),
  declared per manifest, versioned. Cold-run determinism is measured by **G2-W23**.
- **Thresholds** come from at least three sealed compositions, never one (27.10 f/u 3).
- **Repair routing**: structured fields, never regex over prose (W16); one plan-level escalation
  when a content-stage repair would need a slot-set change (**G2-W22**, 27.2 decision).
- **Contract**: a revision lands only with its item's code and tests (27.8); v1 freezes at G3-W02.
- **Queue**: §27.9 is the single source for queued item text — moved entries, pending edits, and
  purposes are reconciled from it (loop-prompt §2).
- **Reuse**: aspose.org is a second reuse source under the pull discipline; vendor boundary; never a
  runtime import; minimal closure only; every pulled file tested (§29, loop-prompt §3).
- **Toolchains** are provisioned workspace-locally by the loop, never system-wide (29.6 E5).
- **Autonomy**: the loop never asks. Every decision is taken on first principles, recorded as
  `PROVISIONAL` in §31 with the alternative rejected, and acted on in the same iteration; the owner
  reviews §31 asynchronously and may reverse. `stop: true` only for done, all-remaining-items-owner-
  blocked, or a prohibition (loop-prompt §5, §7, §9; §30).
- **Scope is not the loop's to grow** (30.8). Autonomy covers *how* to close queued items, never
  *what* to add: the loop proposes new work in §31 and only the owner admits it to §27.9; no new
  blocking check without a sealed defect, a mutation test, and a subsumption review, and never a
  check about a check; blocking checks stay ≤ 15 without an owner decision; from G3 on, three
  accepted items without the candidate count rising means the next item must raise it. G2's queue
  is frozen at W22, W17, W20, W23 — no new G2 items, by the owner's rule too.
- **Throughput (30.9, 2026-09-05 21:40)**: full suite once per commit with `pytest -n auto` (32
  cores; the serial 7-minute suite cost 33% of the day); `present` on the canary only when a
  predicate closes or at acceptance; push and continue. **G2-W17 accepts when the coverage ledger,
  receipt sealing, volatile-observation sealing, and the proxy/CA environment hold** — fixtures for
  file-reading examples move to G3-W01 as failure-class fixes; **G2-W23 is folded into G3-W01**
  (cold-run measurement in the preflight, the parity test); its floor fix already landed at `9e5f780`.
- **Throughput, second pass (30.9 B–E)**: close as many predicates per iteration as the budget
  allows, one commit each; grep or Read with offsets before whole-file reads; commit bodies ≤ 120
  words; **G3-W03** (facts cache keyed by tree hash + extractor version + environment fingerprint,
  wheel cache, per-stage timings) runs only if G3-W01's preflight measures a median facts stage
  above 90 s per repository (30.9 decision 7); otherwise it is deferred behind G3-W02.
- **Third pass (30.9 decisions 7–9, 2026-09-05 23:05)**: G2's exit predicates restated to what the
  rules allow (85 floor, zero blocking findings, zero required-row advisories, ledger in the bundle;
  no per-job 95%, no blocking check before a sealed defect, no suite wall-clock as a gate);
  `parallel_repository_work_allowed: true` for the lanes; the cohort census is §28.10.
- **Order to 31/31**: G2 (W17 closes it) → G3: **the Python cohort first** — facts-only preflight
  over the twelve (§28.10 confirms each failure class), then compositions in **up to three repository
  lanes** — W03 only on the preflight's measurement, then freeze → G4 second source, spec layer,
  extractor, six cohorts → G5 durability and hosted (§28).

### 27.1 Symptoms, measured

| Symptom | Measure | Where |
|---|---|---|
| Re-asked calls | 78 of 395 (20%); first-attempt invalid by job: reconciliation 31%, planning 32%, repair 26%, authoring 16%, review 17%; every one `OutputRejected` (schema, binding or check), none HTTP | `calls.jsonl` |
| Rejection families | repair: 69 of 76 "cites facts outside this section's set"; authoring: URL in text 11, identifier not a fact value 17, command in text 4, wrong slot set 2; planning: "exactly one decision for every shell section" 7; investigation: unknown fact ID 9; review: quote not in the candidate 3 | `runs/transactions/.../calls/*.rejected-*.json` |
| Accepted with known defects | `verdict_as_returned` REJECT_PRESENTATION became ACCEPT; five advisories, three marked "re-raised after the one repair attempt its fingerprint allows"; F02 and F04 were code defects (§26) | `review.json` |
| Unrepairable | 6 of 27 attempts: four "names no LLM-owned section" (a regex missed the section in a detail string), two "section is deterministic" | `repairs.json` |
| Plan drift | 34 distinct plans drawn for one revision; the two transactions chose 7 capabilities and 12 hubs versus 6 and 6, with different titles | `plan.json` ×2, ledger |
| Coverage | 6 of 12 examples and 5 of 7 formats never SUPPORTED; 59 units omitted before prose began | `content_units.json` |
| Structure leaks | 58 visible lines outside `<details>` (visibility is a string compare on the last emitted line); two raw bash fences after prose (`.code_block` bypasses the overlap rule) | `renderer.py:692-705`, `placement.py:124-128` |
| Wall clock | ~30 min per iteration: one local `pytest` pass ≈7 min (twelve `tests/test_cli.py` invalidation tests at ≈30 s each), ×3 interpreters at acceptance; LLM 3–9 min per composition, strictly serial (0 of 315 calls overlapped); CI watch 3 min | `--durations`, ledger |

### 27.2 Root causes (mechanisms, not symptoms)

- **RC1 Generation/validation asymmetry.** Constraints live in validators and in English inside the
  objective; the model is asked to reproduce structure the code already knows: the slot set
  (`authoring.py:351-383`), the shell decision list (code decides inclusion anyway,
  `planning.py:70-73`, then rejects a missing decision at `:123-134`), fact-ID spellings, allowed
  identifiers, forbidden URLs and commands, dispositions a rule forces
  (`reconciliation/dispositions.py:318`). The repair packet (`targeted.py:257-275`) carries the
  finding and the causal stage's output but not the section's fact set, which is why 69 of its 76
  rejections cite facts outside that set. Each rejection costs a stateful re-ask whose accepted
  answer depends on the rejected one (`jobs.py:425-436`); a second rejection fails the whole
  transaction closed (`jobs.py:422`).
- **RC2 Title and prose are never bound.** The Key Capabilities author receives the union of all
  slots' facts (27 for seven slots), slot names that are bare ordinals, and no titles
  (`authoring.py:205-216`; `title` occurs in that module only in a docstring and one objective
  sentence). Slot fact sets overlap (`example:002/004/009/012` sit in capabilities 1 and 2), so a
  fact-ID subset check cannot separate them even in principle. Title and sentence meet for the
  first time in `renderer.py:616`, joined positionally. Nothing in packet, guard, coherence or
  validator holds the one binding a reader checks.
- **RC3 The plan is redrawn from scratch and rendered in LLM order.** Planning receives every
  SUPPORTED fact (231 packet records), two upstream LLM artifacts, and no previous plan
  (`rounds.py:164-176`; no `previous_plan` anywhere). Every array that drives visible structure
  (capability order and count, hub order, example order, link order, the six-title two-column flip
  at `renderer.py:547-567`) is carried in the model's output order with no canonicalisation. A
  semantically identical re-plan renders as a different document.
- **RC4 Reproducibility is cache-derived, not model-derived.** The response cache is
  `runs/transactions/<repo>/<revision>/calls/` — gitignored, machine-local, per revision, excluded
  from the sealed bundle (`seal.py:54-65`). `identity:revision` (the commit SHA) is a fact in every
  job's packet (`extract.py:35-40`), so every upstream revision is a guaranteed cold cache even when
  no relevant fact changed. Temperature is 0 with strict `json_schema` (`jobs.py:148-164`) but there
  is no `seed`. Check 11 therefore proves that the cache was present, not that the pipeline is
  reproducible from the repository. On a GitHub-hosted runner `runs/` is always empty, so as built
  the zero-call proof can never pass hosted (G4).
- **RC5 Acceptance depends on directory history.** Whether a finding demotes to advisory depends on
  `repairs.json` in the transaction directory (`targeted.py:200-203`, `rounds.py:367-373`): the same
  review output blocks in a clean directory and accepts in this one. A finding whose causal stage
  is `unclear` or S9 can never block (`review.py:33-41,133`); one against a deterministic section
  auto-demotes (`review.py:191`); a three-character fact value inside the quote demotes
  (`review.py:160-167`); a prompt version bump reopens every fingerprint (`targeted.py:94`).
  `verdict = returned if findings or returned == ACCEPT else ACCEPT` (`review.py:277`).
- **RC6 Coverage defects dead-end as presentation advisories.** A finding that really means "a fact
  is UNRESOLVED" (F01: no input format verified) routes to presentation repair, which cannot touch a
  deterministic section (`targeted.py:100-116`), and becomes advisory. There is no per-row coverage
  record, no route from a finding to EXTRACTING, and file-reading examples are never executed
  (§22.1, §26).
- **RC7 The extraction environment is unfingerprinted and live network sits inside hashed facts.**
  `dependencies.json` records what was consumed from the repository, nothing about what consumed it:
  no Python version (the venv is cloned from `sys.executable`, `python_examples.py:109`), no OS, no
  extractor version, no resolved install manifest. The PyPI "latest 26.1.0" string is baked into
  `install_command:pip` evidence (`python_registry.py:50`), so an upstream release reopens
  EXTRACTING with no repository change; 17 of 38 link facts and the product-page probes are one
  HTTP status from flipping; a 120 s timeout turns SUPPORTED into CONTRADICTED; the stripped
  execution environment (`execution.py:21-48`) omits proxy and CA variables, so a proxied host
  demotes all 12 example facts at once; `examples.json` is cited by 23 facts but not sealed;
  `sorted(Path)` orders case-insensitively on Windows and case-sensitively on POSIX
  (`python_surface.py:271`).
- **RC8 Free text is a control plane.** The causal stage is regex-recovered from a bracketed prefix
  in the finding's prose (`review.py:231,243-245`); the target section is regex-extracted from a
  validator detail string (`targeted.py:48,143-149`, three repairs died there); invalidation keys on
  `details[0]` (`seal.py:372-373`); validators and renderer match substrings of evidence prose
  (`registry.py:392,425`; `renderer.py:115,254`).

**Measured (the loop, 2026-09-04, G2-W13).** RC2's overlap is real on the canary: of seven
capabilities, five facts sit in two or more (`public_symbol:aspose.threed.scene` in 1 and 2,
`example:002`/`example:004` in 4, 5 and 6, `example:005` in 3, 4 and 5, `example:010` in 3 and 6).
With the plan rule in force the planner declared every one of them in `shared_fact_ids` — six of
seven capabilities carry a declaration — and the one live rejection it earned
(`fact example:002 is cited by capabilities 4, 5, 6`) was corrected on its single re-ask. Title
support was judged on all seven and flagged none: every canary title is ordinary prose
(`Support keyframe animation`, `Assign and configure materials`), so it names no identifier and no
recorded format, and the check has nothing to require. It separates the synthetic pair the subset
check cannot (two capabilities that both declare one example, their sentences exchanged). Three
compositions were sealed while the title travelled in the packet: with no further instruction all
seven sentences opened by restating their own title verbatim; with the packet also saying to name
the products, none restated the title and all seven opened with the product name instead, which
§8 already forbids as a template sentence; with the packet saying only that a unit never restates
its title and never opens with the product name, format names returned to their canonical
spellings (`OBJ`, `glTF`, `3MF` rather than `.obj`, `.gltf`, `.3mf`) and all seven again opened
with their title's words. Advisories across the three: 5, 0, 2; each verdict ACCEPT, each
validation 10 pass, 0 fail, 1 pending. `README_CONTRACT.md` row 7 requires a description to name
the classes or members it rests on and §8 forbids the product-name template; neither addresses a
description that repeats its title.

**Decision (owner, 2026-09-05), closing the gap the loop measured above.** The routing table in
`targeted.py` gains one rule: a repair attempt at a content stage (S6/S7/S8, all currently
collapsed to S6) that fails because its own binding proves the requested revision would change the
plan's slot set or example selection — S6's per-task schema requires exactly the plan's existing
slots, so a fix that would add, drop, or re-choose one is a planning decision by construction, never
inferred from the finding's prose — escalates **once** to a plan-level repair at S5
(`presentation_planning`), carrying the finding's context; the revised plan then re-enters S6
through S8 normally, under the same two-attempt and one-fingerprint-per-defect rules as any other
repair. A repair that still cannot produce a schema-valid revision after the escalation blocks, as
today. This is the same principle dependency evaluation already applies to pre-composition changes
(reopen at the earliest affected stage), extended to a gap discovered at repair time rather than
before it. Owned by G2-W22, split from G2-W16 on 2026-09-05 because the extension pushed W16 past the size rule; W16's re-seal predicate now names the sealed candidate's replay, and the fresh-composition ACCEPT predicate travels with W22.

**Measured (the loop, 2026-09-05, G2-W16).** Bounding `independent_review`'s schema (`findings`
`maxItems` 16; `text`, `quote`, `repair` each `maxLength`) moved the manifest to a new version, so
the canary's next composition made a fresh, uncached review call rather than replaying the stored
v6-era verdict. The reply named five presentation findings, one against `quick_start` (F01) whose
suggested repair - drop the first example, keep only the second - asks for something no S6
revision can do: `section_authoring`'s per-task schema requires the plan's exact slot set
(`lead_in`, `lead_in:2`) filled once each, and dropping an example is a planning decision (S5),
not an authoring one. `targeted_repair`'s own reply failed that requirement on both of its
attempts (the manifest's one internal re-ask included), so the repair job itself was unable to
produce a schema-valid revision - a different failure from a defect the loop knows in advance no
stage can reach. `repair_defect` (rounds.py) now catches this and records the fingerprint
unrepairable at this attempt rather than letting the exception cross the CLI boundary raw; the
resulting BC-10 failure blocks under this item's own rule (a re-raised finding is code-caused or
it blocks) rather than crashing, and the immediate rerun is byte-identical with zero further
provider calls. The sealed candidate (`65b1f577`, built under manifest v6) is untouched and stays
`READY_FOR_PROPOSAL`; a fresh composition on the canary under manifest v7 currently ends
`EXIT_INCONSISTENT` on this finding, which is not yet closed by any work item.

**Measured (the loop, 2026-09-05, G2-W16, second entry).** That `EXIT_INCONSISTENT` did not
survive a clean transaction. `repairs.json` persists across `present` invocations in one
transaction directory, and a review defect's fingerprint carries `targeted_repair`'s own hash, so
the directory the paragraph above describes held attempts recorded before and after each fix of
that iteration - layered diagnostic state, not one composition's judgment. Deleting the
transaction directory (disposable, under `runs/`) and composing from scratch under
`independent_review` v7 and `targeted_repair` v7 returned **ACCEPT with zero findings and zero
advisories on the first review**, no repair round at all: 24 provider calls, 3 rejections,
87.5 per cent first attempt, `validation` 10 pass, 0 fail, 1 pending, and the update adopted and
reproduced byte for byte with zero calls. The three rejections were the known families, each
corrected on its single re-ask: the shared-fact plan rule G2-W13 added, and a URL and a command
written as prose in two units, which is the pair G2-W20 is queued to make referential. Two
observations the run leaves standing. First, the quick_start repair that could not fill both
slots did succeed once `targeted_repair`'s prompt said in words that the causal stage's slot set
is fixed and a finding reading as "drop a slot" is answered by revising the slots that exist;
whether the reviewer should have named S5 for it is untested. Second, a dotted call still renders
with its parentheses outside the code span - `` `Scene.open` ``() - and a chained call leaves the
rest outside it entirely, as in `` `FileFormat.get_format_by_extension` ``().create_save_options();
BC-07 passes, and §6 rule 8 names a split identifier a defect even when every check passes. The
API reference is unchanged at 337 rows and the visible budget improved from 237 to 228 lines.
On the acceptance predicate that asks for the `65b1f577` `review.json` replayed under the new
policy: that document no longer carries the five advisories §26 records - today it carries zero
findings and zero advisories - so there is no stored artifact to replay. F02 and F04 as §26
describes them can no longer reach a reviewer at all: a unit citing another slot's facts fails
check 4 at S9 (`authoring.py`, "cites facts outside its slot's planned set", G2-W07 and G2-W13)
and two facts at one canonical defining location fail row 14 at S9 (`registry.py`, "one fact per
canonical defining location"), both blocking before S10 runs.

**Measured (the loop, 2026-09-05, RC7 observed on the canary).** RC7's link volatility invalidated
the sealed candidate during a verification run, from one network hiccup and nothing else. A
`present` whose extraction re-probed `https://pypi.org/project/aspose-3d-foss/` recorded
`UNCHECKED: unreachable: ReadTimeout`, so `link_target:008` moved SUPPORTED (confidence 1.0) to
UNRESOLVED (0.5). That is one altered fact record, which reopened EXTRACTING and re-composed
everything downstream; BC-06 then failed at EXTRACTING on the same unreachable link, and because a
factual failure invalidates an accepted candidate (`STATE_MACHINE.md` §9), `manifest.json` moved to
`INVALIDATED` and `repository-presenter status` read 0/34. The probe answered HTTP 200 in 1.06 s
about four minutes later; re-running restored every fact, replayed every stage from the store with
zero provider calls, and re-sealed, and a second run proved the no-op again at
`READY_FOR_PROPOSAL`, 1/34. Two artifacts of the recovery are worth naming: the degraded round
wrote an entry into the transaction's `repairs.json`, which persists across invocations, so the
re-seal carried a `repairs.json` recording a defunct attempt until that file was deleted; and a
bundle that stops recording a file keeps the file on disk, since seal does not prune what its
manifest no longer names. Nothing about the repository or the world changed in those four minutes.

**PROVISIONAL (the loop, 2026-09-05, G2-W16's replay predicate restated).** The predicate read
"the 65b1f577 review.json replayed under the new policy blocks on F02 and F04". Three iterations
measured it unmeetable as written: that `review.json` is the live artifact of a bundle re-sealed
many times since §26 was written, and it now carries zero findings and zero advisories, so the five
advisories §26 records exist only as §26's prose — there is no stored artifact to replay, and
reconstructing one would be a fixture I wrote, not evidence. What the predicate was after is
provable another way, and already is: the two defects §26 calls code-caused can no longer reach a
reviewer at all. A capability unit citing another slot's facts fails check 4 at S9
(`test_check_four_blocks_a_unit_citing_another_slots_facts`), and two facts at one canonical
defining location fail row 14 at S9 (`test_row_fourteen_refuses_two_facts_at_one_canonical_location`),
both before S10 runs. The predicate is restated to that, and the item is accepted against the
restatement. **The alternative not taken:** reconstruct the five findings from §26's prose as a
fixture and replay them through `review_document`. It was rejected because the fixture's fields —
`criterion`, `causal_stage`, the exact quotes — are not in §26, so the replay would test wording I
chose rather than a defect the system produced, and a passing result would assert something never
observed. If the owner prefers that fixture, it is a §27.9-shaped entry, not work done here.

**Measured (the loop, 2026-09-05, G2-W22).** A from-scratch composition of the canary, the
transaction directory deleted first, under `presentation_planning` v9 and the escalation: 6 review
findings, 2 advisories, 5 repairs, 4 of them re-raised, `EXIT_INCONSISTENT`. Zero escalations - no
repair's binding proved a slot-set change, so the rule this item adds never fired, and the block is
elsewhere. The six: a command written as prose in Development and Testing (`pip install -e .` where
the verified fact reads `python3 -m pip install -e .`), an API-reference omission, a
scope-limitations omission, a quick-start example claim, an enterprise-relationship preservation
claim, and one claim the document contradicts. (Corrected 2026-09-05 by the count below: the
Additional Examples introduction that finding called duplicated does appear twice, so that
finding was sound; the ones the document contradicts are the four named below.) Every round-two finding named S7, which `review_defects` maps to
S6, so each shared a fingerprint with its round-one finding in the same section and blocked as
re-raised. Two further facts. The planner failed twice, before the v9 wording, on `shared_fact_ids`:
it read "shared" as facts a capability shares but does not itself list, declaring
`public_symbol:aspose.threed.scene` shared by capabilities 2 and 3 while only capability 1 cited it.
And deleting a transaction directory destroys the call store a sealed bundle's zero-call replay
depends on: the bundle keeps its recorded proof and still counts, but reproducing it byte for byte
afterwards would need the same 24 replies again. Both reruns of the rejected composition are
identical with zero provider calls at every stage.

**Measured (the loop, 2026-09-05, G2-W17).** The canary's blocking review findings were counted
against the candidate's own bytes. Of the six that blocked the 2026-09-05 composition, four were
claims the document contradicts: the API reference "omits" `ColladaLoadOptions`, `GltfSaveOptions`,
`ObjSaveOptions` and `StlSaveOptions`, which occur in it 1, 5, 3 and 4 times; scope and limitations
"omits" the COLLADA export note, which is the finding's own quote, located in the candidate;
Development and Testing "uses `pip install -e .` instead of the verified `python3 -m pip install
-e .`", where the candidate contains the verified form once and the bare form never; and the quick
start "contradicts the verified example that uses positional arguments `Box(10, 20, 30)`", a string
in neither the candidate, the original README, nor any fact - `example:002` is keyword-argument
code, verbatim, and it is what the candidate renders. The repair loop spent five attempts and four
re-raises on that set. Separately, the 33 `public_symbol` facts that are UNRESOLVED are not a
coverage gap: each is a deep-module duplicate of a SUPPORTED re-export (`aspose.threed.formats.
collada.ColladaLoadOptions.ColladaLoadOptions` behind `aspose.threed.formats.ColladaLoadOptions`),
and every class the reviewer called missing is in the document. Six of twelve examples stay
UNRESOLVED on `NEEDS_INPUT`: `example:001`, `:003` and `:006` open a `.obj`, `:007` a `.gltf`,
`:011` a `.dae`, and the repository carries no model file of any kind (751 `.py`, 9 `.md`, 4
`.txt`, 1 `.yml`, no data assets). Of the executed examples only `:002` writes a file the tree
keeps, `crate.gltf`, and `:004` writes `ball.stl`; the one example that saves a `.obj`, `:008`, is
CONTRADICTED by the product's own `ObjExporter` (`stream.write(content)`, `TypeError: a bytes-like
object is required, not 'str'`), so no executed example can produce a `.obj` and nothing anywhere
produces a COLLADA file. After the absence rule landed, a re-reviewed composition returned ten
findings: four advisory (one refuted by the absence rule, three by the renderer-owned-section
rule) and six blocking, of which three allege an omission - `AGENTS.md`, `IOService`, the
top-level `ColladaSaveOptions` duplicate - that the candidate contains 1, 3 and 2 times while
leaving `absent` empty, and one lists `Box(2.0, 1.0, 1.0)`, a string in no fact value and not in
the original README. The reviewer filled `absent` on four of ten findings at its first version.
Both reruns of the composition are identical, every stage reused, zero provider calls.

**Measured (the loop, 2026-09-05, G2-W17, second).** With `absent` checked both ways - a claim the
candidate contains, and a claim that occurs in no fact value and nowhere in the original README -
the canary's composition reached `ACCEPT`: 0 blocking findings, 8 advisories, all eleven checks
PASS, and the update was adopted by a fresh process that reproduced it byte for byte with zero
provider calls. Of the 8 advisories, 5 are refuted because the candidate contains what they say it
lacks (`python3 -m pip install -e .`, `AGENTS.md`, `34 test files`, whole import lines, a
four-sentence COLLADA paragraph), 1 because it asks for `pip install -e '.[dev]'`, which no fact
value and no line of the original README holds, and 2 by the renderer-owned-section rule. The
sealed candidate this produced is **not committed**: its `calls.jsonl` measures 80.0% first-attempt
acceptance against the 85 floor of §27.6 control 1. The cause is the control's subject, not the
model. That ledger is a transaction's whole history - 309 records, 65 provider calls, 41 logical
calls, four prompt versions - where the two compositions the floor rests on were single
compositions of 46 and about 24 provider calls that called `targeted_repair` **zero** times. This
one called it 22 times, and repair is the job with the lowest first-attempt rate: authoring 19/21
(90.5%), review 10/13 (76.9%), repair 17/22 (77.3%), planning 4/7 (57.1%). No job regressed against
§27.10's measured per-job rates (repair 74%, review 83%); the aggregate fell because the mix moved
toward repair. An aggregate over a varying job mix is not a stable control.

**Measured (the loop, 2026-09-05, G2-W17, third: a rejected mechanism).** A `claim` enum
(`absence` / `contradiction` / `judgement`) was added to the review schema so that a validity check
could require an absence claim to name its missing text. The reviewer classified **all eleven**
findings as `judgement` and returned six near-identical findings of the form "the candidate's X
section is not in the same order as the original README's X section" - a template, where the same
composition had previously produced six substantive findings. The mechanism was reverted in the
same iteration. A shape the constrained party declares is not a constraint: the enum gave the model
a branch with no obligations and it took it. What survived is the rule that reads the model's
output against the candidate and the evidence, neither of which the model controls.

**Measured (the loop, 2026-09-05, G2-W17, fourth).** The seal now keeps only the ledger records of
the logical calls the composition consumed, made or reused. On the canary that is 312 records and
**28 provider calls**, where the transaction holds 327 records and 65 provider calls across four
prompt versions. First-attempt acceptance on the composition's own calls is **82.1%** (5 rejected
of 28): `repository_investigation` 1/1, `source_reconciliation` 1/1, `section_authoring` 16/18
(88.9%), `presentation_planning` 2/3, `independent_review` 3/5. The five rejections are named. Two
are `section_authoring` calls carrying exactly the two prose families §27.0's D1 line leaves to
**G2-W20** - three link units wrote `https://` with the host (`docs.aspose.org`, `kb.aspose.org`,
`reference.aspose.org`) as a non-fact identifier, and a summary unit wrote `pip install` as text.
One is `presentation_planning`'s `shared_fact_ids` family, whose wording the v9 prompt fixed after
this call was made. Two are `independent_review` quoting a heading that is not the candidate's text.
Without W20's two, the same composition measures 89.3%, above the 85 floor; with them it is below
it, so the accepting bundle stays uncommitted for a second iteration. The gate's own exit predicate
asks 95%.

**Measured (the loop, 2026-09-05, G2-W20).** A slot now carries `renders` - the material the
deterministic renderer prints beside it, from the slot's own facts - and `fact_ids` is a per-call
enum of the section's accepted set. Re-authoring the canary under `section_authoring` v11 made 18
authoring calls, 16 accepted first (88.9%), and **neither prose family this item owns appeared in
any rejection**: no URL, no host as a non-fact identifier, no command in text, where the same two
calls carried six and one such rejection on 2026-09-05 before the change. The rendered Development
and Testing sentence now reads "Install the package in editable mode and run the full test suite
with unittest, or execute a specific test file to validate individual components", with the
commands only in the blocks the renderer prints. The two rejections that remain are a different
family the enum does not reach - `cites facts outside its slot's planned set` (the enum carries the
section's set; the slot's narrower set varies per unit, which uniform array items cannot express)
and `identifiers that are not accepted fact values` (`Scene.add_child_node`, `test_obj_importer`).
Blocking review findings fell from 6 to 3; the composition still ends `EXIT_INCONSISTENT`, and both
reruns are identical with zero provider calls at every stage.

**Measured (the loop, 2026-09-05, G2-W17).** Every one of the canary's twelve `example` facts
names `examples.json` as the evidence for its outcome, and the bundle did not carry that file: the
verification receipt lived only in the gitignored transaction, so a reader of the sealed candidate
could not see why an example was SUPPORTED or UNRESOLVED, and a fresh clone had no way to recover
it. The seal now writes it, and `repairs.json` beside it, and the bundle is 13 files. Sealing it
exposed a second defect the CLI's invalidation tests caught immediately: the receipt embedded the
disposable workspace by absolute path in every traceback, so the same verification sealed different
bytes under a different project root - four matrix tests failed on `examples.json changed` where
nothing about the repository had changed. The run's own path is now replaced by `<workspace>`
before the receipt is written, in either separator; the canary's receipt carries six such tokens
and no absolute path, the bundle re-sealed with a presentation-only update, and a fresh process
reproduced it byte for byte with zero provider calls.

**Measured (the loop, 2026-09-05, G2-W17, RC7).** `install_command:pip` carried
`package registry: found; latest 26.1.0; manifest version published` as hashed evidence, so every
release PyPI published would have rewritten the fact and reopened EXTRACTING for a repository that
had not changed - the same shape as the `ReadTimeout` that reopened EXTRACTING and invalidated the
bundle earlier that day. The evidence now reads `package registry: found; manifest version
published`, and the volatile part travels in a sealed `probes.json`: 15 records on the canary, 14
link reads and one registry read, each with its HTTP status and its duration, the registry record
carrying `latest 26.1.0` as its observation. No `latest` string survives anywhere in the hashed
evidence. Sealing the record exposed the same defect the receipt had: timing differs on every run,
so the first re-seal withdrew the no-op proof with `probes.json changed since the last seal`.
`probes.json` joins `calls.jsonl` and the manifest as a file that carries a clock by design and is
not compared byte for byte - three files, none of which a candidate depends on. The bundle is 14
files, the update was adopted by a fresh process with zero provider calls, and the run after it was
a no-op.

**Measured (the loop, 2026-09-05, G2-W17, fixtures).** An example that reads a file is now offered
one an executed example of the same README wrote, when the repository ships none: the pool is keyed
by extension, filled in ordinal order from runs that exited zero, and consulted only after a
repository file of that name and then of that extension have failed. A second pass gives the
examples that lacked an input one more attempt against the complete pool, so a producer may appear
after its consumer. On the canary that moves **executed from 6 to 7 of 12**: `example:007` opens
`model.gltf` and now runs on `crate.gltf`, the file `example:002` writes, recorded in the receipt as
`staged as model.gltf from example 2's output crate.gltf`. The four that remain are the three
opening a `.obj` and the one opening a `.dae`: no executed example writes either, because the only
`.obj` producer is `example:008`, which the product's own `ObjExporter` fails with `TypeError: a
bytes-like object is required, not 'str'`, and nothing anywhere produces COLLADA. A half-written
file from a failed run is never handed on - only a run that exited zero contributes. The input
formats OBJ, STL, glTF and COLLADA are all SUPPORTED from the product's own format declarations,
and were before this change. The composition that followed the new fact ended `EXIT_INCONSISTENT`
on seven findings, six of them prose judgments about ordering and density that the same document
did not attract an hour earlier: composition variance (27.10), not a family this item owns.

**Measured (the loop, 2026-09-05, G2-W17, the repair ledger's scope).** The canary's composition
of that evening reported seven blocking findings and nineteen re-raised, with **no repair
attempted**: `repairs.json` is written into the transaction, the transaction outlives its
compositions, and a defect fingerprint is only a source, a section, a stage and a criterion plus
the judge's identity - never the composition being judged. So the first round of a rebuilt
composition found each of its defects already attempted against a document that no longer existed,
took the re-raised branch, and stopped before repairing anything. The ledger is now scoped by the
inputs its composition was built from - the revision, the facts, and the prompt set - which every
round of one composition shares, a replay reproduces, and a rebuilt composition never matches; a
rebuilt composition is exactly the changed evidence the contract's one-attempt rule asks for. Two
identities were tried and rejected first: the round-one document digest, which a repair changes by
rewriting the stored response round one consumes, and the planning request hash, which an
escalation moves mid-loop. **Parallel suite (same day).** `pytest -n auto` runs 500 tests in 104
to 113 seconds against 175 at `-n 4`, both under the 120-second ceiling. Three `tests/test_cli.py`
invalidation tests fail intermittently under `-n auto` and never serially or on a clean re-run:
each builds a virtual environment and installs the clone to verify examples, and enough of them at
once exhausts the machine. Four consecutive full runs: green, green with three lost, green.

**Measured (the loop, 2026-09-05, G2-W17, the repair loop engaging).** With the ledger scoped to
its composition, the canary's repair loop attempted **seven repairs where it had attempted none**,
and blocking findings fell from seven to four; all six advisories were refuted, by the absence rule
and the renderer-owned rule. The composition still ends `EXIT_INCONSISTENT`. Before that run the
review failed closed a second time on quote location: the reviewer quoted the install verification
as one flattened string, fence and all, and the fence's language tag survived where the candidate's
own fence line dropped it - `verify the install: bash python -c ...` against `verify the install:
python -c ...`. Two rejections, then a `JobError` instead of a verdict; the normaliser now drops a
fence marker and its language wherever it appears, as it already did for a Mermaid label's
quotation marks. The four findings that remain: one calls Key Capabilities' phrasing generic, one
says Enterprise Relationship omits a link, and **two are the original README contradicting a
verified fact** - the candidate renders 337 public types and 34 test files, both computed from
facts, and the reviewer prefers the original's stale 305 and 33. The contract already says an
inherited README unit is maintainer text, not evidence; the reviewer's packet does not enforce it
for a `presentation` finding that cites no fact at all.

**Measured (the loop, 2026-09-05, G2-W17, the renderer's own sentences).** Two of the canary's four
remaining findings disputed counts the renderer computes: the candidate says 337 verified public
types and 34 test files, the reviewer preferred the original README's 305 and 33. The facts carry
exactly 337 SUPPORTED symbols of kind class or enum, and the clone holds exactly 34 files under
`tests/`, so the renderer is right and the original is stale maintainer text - which the contract
already refuses as evidence, but only for a `factuality` finding that cites a fact. The renderer now
names the sentences it writes into a section an LLM otherwise owns - the suite size, the release
line, the surface count, the reference count - and a finding whose quote sits inside them is the
reviewer's own defect, as one against a deterministic section already is. Verified against the
canary's own review without recomposing: both count findings refute, the other two stand. Reaching
that took two corrections the first attempt missed - the inventory omitted the API-reference
sentence, and a quote may span two adjacent renderer sentences - and a **third normalisation
asymmetry**: the candidate carries `[publish workflow](.github/workflows/publish.yml)` where the
reviewer quotes the words it clicked. After the Mermaid label's quotation marks and the fence's
language tag, the rule is now explicit in `_normalized`: a reviewer quotes what it reads, and every
piece of syntax the renderer wrapped around it is ours to strip.

### 27.3 Structural weaknesses (the design-level statements behind RC1–RC8)

- **W1 Constraints have three homes and no machine-readable source.** Contract prose, prompt
  English and validator code each restate the rules and drift apart: "cites its own title's facts"
  became "cites its own slot's fact IDs"; visibility inheritance exists only as a renderer string
  compare; the `.code_block` carve-out exists only in code.
- **W2 The evidence model has no provenance.** No retrieval time, no environment, and one
  polarity for "verified false" and "could not verify here"; volatile observations are hashed as
  facts.
- **W3 Acceptance mixes content with process history** — fingerprints, round budgets and prompt
  versions decide what ships.
- **W4 Determinism is asserted at the document level but guaranteed only by a gitignored
  directory.**
- **W5 The model reproduces structure the code owns**, then is punished for getting it wrong.

### 27.4 Preserve — proven, not to be redesigned

The S1–S12 split with a deterministic final verdict (`cli.py:368`); all eleven blocking checks; the
renderer owning every byte of Markdown; fact-bound content units; canonical serialisation
everywhere (`sort_keys`, sorted records, `dict.fromkeys` — unusually clean); per-candidate
`dependencies.json` with per-fact hashes and earliest-affected-stage evaluation; the frozen model
catalog with fail-closed routing; the two-attempt rule; `cache_stale` re-judging of stored
outputs; push-disabled clones and secret scans; seal, supersede and adopt-in-place; the loop's own
discipline (small commits, green CI, evidence per item).

### 27.5 The durable design

- **D1 Constructive generation.** The code emits each call's skeleton and a per-call JSON schema:
  slots enumerated with their allowed fact IDs as enums, fixed-length slot arrays,
  `additionalProperties: false`. Shell decisions leave the planner's output. Forced dispositions are
  computed in code; the model is asked only for the free ones. Allowed identifiers travel as a list
  (and as an enum where finite). The repair packet is the same skeleton plus the section's fact set
  and the slot's subject. Prose stays the model's — structure is constructive, interpretation is
  not (AGENTS.md's ban on mechanical template filling is about content, and holds).
- **D2 Title-bound capabilities.** The planner assigns pairwise-disjoint fact sets per capability
  or declares shared facts explicitly; each title travels in the authoring packet and the slot
  identity; a deterministic check confirms the unit cites only its slot's facts and that the
  title's identifiers and format names appear among the cited facts' values; contract check 4 says
  so (27.8).
- **D3 Anchored, canonical plans.** Planning receives the CURRENT bundle's accepted plan as anchor
  with the fact delta since; every deviation must cite a changed or new fact ID; layout arrays are
  canonically ordered (anchor order, then a stable key) before prompt serialisation and rendering.
- **D4 Portable reproducibility.** `identity:revision` leaves every job packet (the renderer keeps
  the fact). The call store is seeded from the sealed bundle's accepted artifacts by recomputed
  request hash, so a fresh clone — or a hosted runner — replays with zero calls; check 11 becomes a
  fresh-state proof (fresh process *and* empty `runs/`). Ledger records carry temperature,
  `max_tokens`, `response_format` and `derived_via_reask`. `dependencies.json` gains an environment
  class (Python version, OS, extractor version, resolved site manifest) that reopens EXTRACTING.
  Live probes record retrieval time and status; volatile observations leave the hashed fact;
  the execution environment passes proxy and CA variables; `examples.json` is sealed. `seed` is
  adopted if the gateway honours it (a discovery task, §18.4).
- **D5 Content-only acceptance.** A finding demotes only when a deterministic check contradicts it;
  `unclear` is classified by code from the section's owner; a re-raised finding never demotes — it
  is code-caused (§26: add the check) or it blocks; every failure record carries `section_id` and
  `causal_stage` as fields, retiring the regexes of RC8; required rows admit zero advisories before
  READY_FOR_PROPOSAL; advisory counts appear in the portfolio report. Contract §6 is revised (27.8).
- **D6 Coverage ledger and fixtures.** A per-row record of required fact kinds and their
  resolution with reason; a new blocking check fails closed when a required row's facts are
  unresolved and routes to EXTRACTING, never to repair; file-reading examples receive fixtures from
  the repository's test assets or from the saved output of an executed example. What still cannot
  execute stays UNRESOLVED, honestly.
- **D7 Throughput without weakening checks.** A session-scoped sealed-canary fixture for the twelve
  invalidation tests (≈7 → ≈2 min per pass); the local CI-equivalent on one interpreter with the
  hosted matrix authoritative; bounded fan-out (4) of independent jobs with the ledger written in
  logical-call order, after D1 has cut the re-ask share; consolidation of §19–§26 once G2-W07
  closes (its prerequisites cite them by number).

### 27.6 Validation and regression controls

1. **Rejection telemetry as a predicate**: first-attempt acceptance per job and re-ask share,
   computed from the sealed `calls.jsonl` by a test helper; G3 exit requires ≥95% and ≤5% on every
   representative.
2. **Fresh-state proof**: delete `runs/`, run `present`; byte-identical, zero calls — a test, and
   check 11's new meaning.
3. **Golden-delta perturbations** (fake gateway): change one fact → only units citing it change;
   add one capability fact → exactly one bullet changes; a new revision with identical facts →
   zero calls and an identical README.
4. **Plan stability**: shuffled planner arrays render identically; identical facts plus anchor
   yield an identical plan.
5. **Title-binding mutation**: swapping two capability sentences fails the check.
6. **Coverage ratios** (SUPPORTED examples/total, formats/declared) in the manifest, compared to the
   live oracle for each G3 representative.
7. **Environment fingerprint**: 3.11 versus 3.13 differs → EXTRACTING reopens.
8. **Structured routing**: a grep-enforced test that no regex over prose or detail strings decides
   routing or invalidation.
9. **Validator mutation tests** — the loop's existing pattern: every new check blocks on a
   synthetic violation.

### 27.7 Trade-offs, risks, limits

- D1 narrows the model's freedom over structure. The line is: structure constructive, prose free,
  coherence pass kept. Per-call schemas with large enums may exceed what the gateway's strict mode
  accepts — unverified for `qwen3-next`; fall back to post-validation for oversized enums and
  measure.
- D3 can entrench a stale plan. Deviations are forced whenever facts change, and a full re-plan is
  an explicit, reviewed update, not a side effect.
- D5 will lower the acceptance rate before it raises it: candidates that accept with advisories
  today will block. That is the correct direction for a production system and the honest cost.
- D4's seeding adds no storage (accepted outputs are already bundle artifacts); `seed` support and
  the served model's build stability are unknown — `model_route` is a name, not a pinned build.
- D6 cannot reach full coverage; examples needing external assets stay UNRESOLVED.
- Magnitudes come from one repository. Rates for .NET or Java may differ; the mechanisms do not.
- Cost: seven items before contract v1 freezes and the second ecosystem lands — roughly two days at
  the measured cadence. Freezing the contract before D2, D5 and D6 would freeze the wrong
  predicates.

### 27.8 Contract revisions these items carry (applied with their code, never before)

- Check 4: "…and the capability's title is supported by the facts its unit cites."
- §6: advisory demotion is content-only; a re-raised finding never demotes; required rows admit
  zero advisories before READY_FOR_PROPOSAL.
- New check 12 (coverage): a required row whose facts are unresolved fails closed and routes to
  EXTRACTING — admitted only when a sealed candidate exhibits the defect (loop-prompt §6 rule 14;
  §31, 2026-09-05). None does at `65b1f577`; the G3 cohort supplies the evidence or shows the
  check unnecessary.
- §6, two-reader rule (owner, 2026-09-06 00:15, §31; lands with G3-W01 before its step two): a
  review finding classified as a prose judgment — no deterministic check expresses it (§26) — on a
  required row blocks READY_FOR_PROPOSAL only when a second independent review under a different
  seed raises an equivalent finding (same section, same fingerprint class); a single-reader finding
  is recorded in `review.json` as `single_reader_advisory` and does not block. Deterministic checks
  and code-caused findings are untouched. Evidence: the canary's composition of 2026-09-05 23:36,
  unsealed by one such finding after its single repair.
- §6 (G2-W17, 2026-09-05): a finding that alleges an absence states what it claims is missing as
  text the code can look for, and a required row admits zero advisories *left standing* - a finding
  a deterministic check refuted is not deferred work and never blocks.
- §7 (G2-W17, 2026-09-05): the bundle's file list names `examples.json`, `probes.json` and
  `repairs.json`, and says why - a bundle carries every artifact its own facts cite as evidence,
  so nothing a fact points at is left dangling outside the seal; `probes.json` records what a live
  read cost and any reading that moves without the repository, and carries a clock, so it is not
  compared byte for byte in the no-op proof.
- Check 11 (G5-W02, 2026-09-07): fresh-state proof (fresh process and empty `runs/`) - landed in
  the row's own wording; the mechanism that makes the claim true for every job kind (seeding for
  `section_authoring`/`independent_review`) is not yet complete, so the claim is honest for the
  three seedable jobs only until it lands.
- §3 placement rule 3: visibility inheritance as a section property, and the `.code_block`
  carve-out documented or removed.

### 27.9 Queue

Execution order in `project/state.yaml` (list order is execution order; IDs are identities, not
positions), as restructured by §28 and §29 on the owner's go (2026-09-04): G2 — G2-W11 D7 fixture,
G2-W12 D1 (accepted 2026-09-04 at the measured 91.7/8.3, §27.10), G2-W19 sampling determinism
probe, G2-W21 output-shaping code as a recorded dependency, G2-W13 D2, G2-W16 D5 (review output
bounded), G2-W22 plan-level repair escalation (split from W16, 2026-09-05), G2-W17 D6 (accepts on
the ledger, sealing, volatile observations, proxy/CA environment; fixtures move to G3-W01), G2-W20
referential links and commands; G2-W23 folded into G3-W01 on 2026-09-05 (30.9); G3 — G3-W01 Python
cohort first (its preflight measures; census §28.10), G3-W03 facts cache only if that measurement
admits it (30.9 decision 7); G4 — G4-W10 layered plugins and generic shared code, G4-W09 shared
surface extractor carrying the second reuse source's schema and records (G4-W08 folded in,
2026-09-05 23:30, §28.12), then G4-W11 .NET, **G4-W17 shared-code fixes the lanes and the Python dispositions need** (moved
ahead 2026-09-06 09:00; stays active while any lane is open), **G3-W04 Python second pass** (inserted
07:45 — the first pass sealed one of eleven); in lanes — G4-W12
Java (lane C), G4-W14 TypeScript then G4-W13 C++ (lane B), G4-W15 Go then G4-W16 Rust (lane D); then
G3-W02 freeze v1 after
every cohort (moved 2026-09-05 23:30, §28.12); G5 — G5-W01 D3, G5-W02 D4, G5-W03 fan-out. Each
cohort item carries a time box (§28.12). The entries below are the exact
`next_ready_items` text; whichever session finds an entry absent from `state.yaml` on a clean tree
inserts it verbatim at the stated position (loop-prompt §2), validates the schema, and commits that
one file. **Moved — remove from `state.yaml` if present:** G2-W09 → G3-W02, G2-W10 → G4-W11/W12,
G2-W14 → G5-W01, G2-W15 → G5-W02, G2-W18 → G5-W03, and the §28 drafts G4-W01 → G4-W09, G4-W02 →
G4-W11, G4-W03 → G4-W12, G4-W04 → G4-W13, G4-W05 → G4-W14, G4-W06 → G4-W15, G4-W07 → G4-W16
(superseded by §29 on 2026-09-04; IDs are never reused); **G2-W23 → G3-W01** (folded, 2026-09-05,
30.9); **G4-W08 → G4-W09** (folded, 2026-09-05 23:30, §28.12 — remove G4-W08 from the queue);
**G3-W02** moved behind G4-W16 and **G4-W13** moved behind G4-W15 (2026-09-05 23:30, §28.12; the
entries below stand at their new positions); **G4-W14, G4-W15, G4-W16, G4-W13 → lane B**
(2026-09-06 01:20, §28.12 "Lane B": their text lives verbatim in `project/lanes/lane-b.yaml`, worked
by the lane-B agent on branch `lane-b`; the primary removes them from `next_ready_items` and never
re-inserts them). **G4-W12 → lane C** (`project/lanes/lane-c.yaml`, 2026-09-06 08:00) and **G4-W15, G4-W16 → lane D**
(`project/lanes/lane-d.yaml`; lane B keeps G4-W14 and G4-W13 — its file drops W15/W16 at its next
between-run edit).
**Pending state edits, applied in the same commit:** `owner_items` `consumed_by` gate IDs
`G4_HOSTED_PORTFOLIO` → `G5_RERUN_DURABILITY_AND_HOSTED_OPERATION` and `G5_PROPOSAL_EFFECT_PROOF`
→ `G6_PROPOSAL_EFFECT_PROOF`; `current_gate.purpose` restated from the ESM G2 goal and exit
predicates; `migration/reuse-manifest.yaml` `census_gate` and `census_evidence` →
`G4_MULTI_LANGUAGE_COHORTS`.


**2026-09-30, owner-directed Monday production deadline - re-sequenced.** G5-W02 (fresh-state proof) moves ahead of every G3 item still open; two new G5 items (G5-W04 durable state backend, G5-W05 the real hosted present.yml) and five new G7 items (G7-W01 threat model, G7-W02 SBOM, G7-W03 dead-man monitoring, G7-W04 credential rotation, G7-W05 failure exercises) are admitted, all sequenced ahead of G6's actual PR-effect rollout. G6-W01 (issue-filing write path, unblocked now that OWNER-04 is SATISFIED) is admitted next - the go-live prerequisite for ever unblocking an upstream-blocked candidate. G5-W06 (community-file discovery and replication, superseding OWNER-07's original resume path) and G6-W02/G6-W03 (propose.yml against a disposable target, then the real rollout) follow. G3-W05 (S8 coherence/Mermaid-diagram deterministic backstop, a new prerequisite to G3-W02) is admitted immediately before G3-W02, which stays gated behind it - freezing the acceptance contract now would send every sealed candidate through a mandatory fresh review pass with this known, uncorrected gap still open. Full rationale: docs/DECISION_LOG.md, this date.

**2026-09-30 (second pass, same day) - re-sequenced again after a fresh, evidence-based project-wide audit and three owner decisions (merged-upstream is the live bar, G5/G7 get full builds, plausibly-fixable candidates are retried) plus a real representational gap the owner caught directly: the state machine never gave EXECUTION_STATE_MACHINE.md's own G7 Work item 3 ("scheduled monitor in read-only observation... automatic PR mode... expanding only after observed stability" - the literal act of plans/idea.md's Operating Model, lines 392-405 and 409-411) a trackable work-item id. New item G7-W06 is admitted for exactly that, positioned right after G6-W03 - it depends on G5-W02/W04/W05 (the mechanism proven hosted) but not on G6-W03 having already run, since G6-W03's own PR-opening can and should start the moment G6-W02's disposable-target proof is stable. G6-W03 itself moves up, immediately after G6-W02 and ahead of G7-W06/G3-W05/G3-W02/the G7 hardening items - the owner ruled "live on GitHub" means an actually-merged upstream PR, and merge timing depends on Aspose's own repository maintainers, outside this project's control, so every day a real PR sits open matters; deferring it behind G5/G7's full builds would waste that review window for no dependency reason. G7-W01/W02/W04 (threat model, SBOM, credential rotation - each with no dependency on anything else in the queue) are re-sequenced ahead of G7-W03/W05 (dead-man monitoring and failure exercises, which need G5-W05/G7-W06's real hosted runs and G5-W04's durable state respectively to have something genuine to exercise). Full rationale, the three-question discussion, and the idea.md quotes grounding G7-W06: docs/DECISION_LOG.md, this date (second entry).

**2026-10-01 - two items admitted at the lowest priority (20 and 21), found ready-but-unclaimed by a fresh supervisor session's procedure.md section 0 mandatory sweep, sitting unbuilt since 2026-09-17 despite docs/PRODUCTION_ROADMAP.md recording both as "ready for a taskcard."** G6-W04 (the upstream-defect re-detection/closing side, WS3) and G5-W07 (registry identity-validation hardening plus the aspose.org family/platform classifier port, WS4) are both admitted after the priority-numbered go-live items and the existing speed/quality-only items (G3-W03, G5-W01, G5-W03) - neither blocks Monday's go-live bar, both are genuine, previously-recorded gaps that would otherwise keep sitting unrecorded in a queue nobody reads. Full rationale: docs/DECISION_LOG.md, this date.

**2026-10-05 - ten items admitted by the register PR (`docs/DEFECT_INDEX.md` work-item column), appended in this order after G3-W04:** G6-W05, G3-W06, G3-W07, G5-W08, G5-W09, G7-W07, G4-W18, G4-W19, G7-W08, G7-W09. They own the reviewer ids REV-V1 to REV-V4 and the register ids REG-01 to REG-15, so no logged defect is invisible to the build order. Each carries its depends-on and exit predicate; none outranks an open exit predicate of the current gate.

**2026-10-07 - three items admitted by the register PR (`docs/DEFECT_INDEX.md` work-item column, REG-16 to REG-18), appended in this order after G7-W09:** G7-W10 (cursor-staleness guard: `updated_at` had gone stale with no mechanical check), G7-W11 (sealing-loop failure memory: a repeatedly-failing candidate retried identically with no recorded history; a claimed in-progress fix on branch `feat/sealing-failure-memory-1009` was re-checked live and found not to exist), G7-W12 (Cells-Go's `UNCLASSIFIED` deferral gap: a claimed in-flight root-cause investigation was likewise re-checked live and found not to exist). Each carries its depends-on and exit predicate; none outranks an open exit predicate of the current gate.

**2026-10-07 (later the same day) - one item admitted by a full-history audit of every `sealing-scheduled.yml` run since the workflow existed (`docs/DEFECT_INDEX.md` REG-20), appended after G7-W12:** G7-W13 (unattended sealing hosted proof: six runs so far, zero have ever sealed a repository; #285, #286, #287, #289 and #290 all merged to `main` the same day, all after the last of the six runs, so none is hosted-verified yet - a merged fix is registered here as fixed-but-unverified, never as the gap closing itself). Carries its depends-on and exit predicate; it does not outrank an open exit predicate of the current gate.

**2026-10-07 (second entry) - one item admitted by this session's write-scope-expansion investigation (`docs/DEFECT_INDEX.md` REG-19), appended after G7-W12:** G6-W06 (write-scope expansion gate - a registry entry's `mode` moves from `dry_run` to `full` only with a per-repository owner authorization dated in `docs/DECISION_LOG.md`, a committed `ops/proposal-authorizations/` record for that repository, and a current, independently accepted, no-op-proven candidate; never a blanket switch, and never an agent's own unilateral registry edit). It owns owner question `OWNER-20` (per-repository go/no-go). Full rationale: `docs/DECISION_LOG.md`, this date.

**2026-10-08 - two items admitted by this session's hosted-sealing durability audit (`docs/DEFECT_INDEX.md` REG-21), appended after G6-W06:** G7-W13 (unattended sealing hosted pipeline proof - SATISFIED by hosted run `37712681751`, the first observed hosted success since `sealing-scheduled.yml` was wired), G7-W14 (hosted portfolio-currency durability - OPEN: that success never commits the sealed bundle back to this control repository's own `candidates/` tree, for any registry mode, so `status`'s counts stay stale under the scheduled loop until a human/agent commits a PR by hand). Each carries its depends-on and exit predicate; full rationale and independent re-verification: `docs/DECISION_LOG.md`, this date.

**2026-10-08 (second entry) - one item admitted by a verification/registration session, appended after G7-W14:** G7-W15 (S6 must-carry packet-bundling gap, `docs/DEFECT_INDEX.md` REG-22 / `composition.authoring.superseded_unit_not_carried` - a third independently-sighted occurrence, on `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`, of a must-carry superseded unit not reliably carried through S6 `section_authoring`, surviving #281/#286/#287/#289/#290 all landed; settled priority per AGENTS.md's three-sighting rule). Carries its depends-on and exit predicate; full rationale, the direct evidence read, and the attempt-2 discrepancy left unexplained: `docs/DECISION_LOG.md`, this date.

**2026-10-08 (third entry) - one item admitted by a verification/registration session, appended after G7-W15:** G7-W16 (coherence silent symbol-citation drop, `docs/DEFECT_INDEX.md` REG-23 / new entry `composition.coherence.cited_symbol_silent_drop` - a single sighting, on `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript`, of S8 coherence revision dropping four previously-cited `public_symbol` citations from a prose unit with none of their own text surviving; the existing `coherence_content_loss_errors` check, built for the unrelated Mermaid-diagram shape, correctly catches it on both attempts, so the open question is upstream, not the check). Below AGENTS.md's three-sighting threshold - PENDING investigation, not settled priority. Carries its depends-on and exit predicate; full rationale and the direct evidence read: `docs/DECISION_LOG.md`, this date.

**2026-10-08 (fourth entry) - one item admitted by a verification/registration session, appended after G7-W16:** G7-W17 (S8 coherence must-carry recovery gap, `docs/DEFECT_INDEX.md`'s `composition.authoring.superseded_unit_not_carried` entry - the seventh independent sighting of that mechanism, post-#298, on `aspose-3d-foss/Aspose.3D-FOSS-for-.NET`, `aspose-email-foss/Aspose.Email-FOSS-for-.Net` and relayed `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`: well past AGENTS.md's three-sighting settle bar. #298's own naming fix only clarified the rejection; it never gave S8 coherence a deterministic `recover=` path for a must-carry fact_id moved into a section never granted it, unlike the sibling G3-W05 content-loss gap - fixed in this item, not merely registered, by `composition/coherence.py::recover_coherence_carried_units`/`recover_coherence_regressions`). Carries its depends-on and exit predicate; full rationale and the direct re-execution of the real checks: `docs/DECISION_LOG.md`, this date.

**2026-10-09 (fifth entry) - one item admitted by a verification/registration session, appended after G7-W17:** G7-W18 (the same `scope_limitations`/`enterprise_relationship` dual-violation shape G7-W17 fixed for S8 coherence, now sighted at S6 `section_authoring`'s own re-ask budget instead - `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`, revision `181015d2eee3e19f8af3d84e4a932ac84ad47c7c`, a first-time-seal attempt against current main). A single sighting, below AGENTS.md's three-sighting threshold - PENDING, not settled priority. G7-W17's fix never runs here: S6 exhausts its own two attempts before S8 coherence is ever reached, so the gap is a distinct causal stage, not a regression in G7-W17's own fix. Carries its depends-on and exit predicate; full rationale and the direct transaction evidence: `docs/DECISION_LOG.md`, this date.

**2026-10-09 (sixth entry) - one item admitted by a porting session, appended after G7-W18:** G7-W19 (absence-finding restated-claim fold gap, `LANE-B-W14R8-F1` - ported from a stale, never-merged branch, `land/absence-refute-1008`, rather than re-diagnosed; `review/independent/review.py::absence_partition`'s `present` fold recognized only a literal `quote_located` match, so an `absent` claim copied verbatim from the ORIGINAL README was never recognized as present when the candidate correctly restated the same substance in different, shorter wording - measured live 2026-10-04 on `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, BC-10 F06, eight claims, none refuted by literal lookup. Fixed by new `absence_restated`, gated by a minimum-word floor so a too-short claim is still refuted only by a literal occurrence; `REVIEWER_LOGIC_VERSION` "17" -> "18"). Registered as `G7-W19`, not `G7-W18`: this branch was cut before PR #301's own unrelated `G7-W18` registration (the fifth entry above) landed on `main`. Carries its depends-on and exit predicate; full rationale, the stale branch's own history, and the version re-derivation: `docs/DECISION_LOG.md`, this date.

**2026-10-10 (seventh entry) - one item admitted on an owner decision, appended after G7-W19:** G7-W20 (acceptance profile ratification, closes OWNER-13; the owner decided on 2026-10-09 to ratify now using the weights table confirmed 2026-10-06 - C01, C02, C21 and C24 weigh 2, the other 22 criteria weigh 1, total 30 - with not-applicable criteria credited as met, banner links failing C01, and D14 evaluated by the #279 checker). The weights table and sub-decisions are recorded in `docs/DECISION_LOG.md` 2026-10-10 so they no longer live only in a session transcript. Carries its depends-on and exit predicate.

**2026-10-10 (eighth entry) - two items admitted on the owner directive, appended after G7-W20:** G7-W21 (Monday delivery plan: the live autonomous system proven once, G7-W01, W02, W03 and W05 as parallel agent work Monday to Wednesday, the multi-day hosted observation and the Level 7 and 8 certification periods as background tracks that never block delivery) and G7-W22 (candidate currency freeze and re-seal batching policy, breaking the enhance, invalidate, re-seal loop). Each carries its own acceptance text; neither adds a gate.

**2026-10-10 (ninth entry) - one item admitted by the dotted-identifier session, appended after G7-W22:** G7-W23 (S6 dotted file name in prose: an authored unit that repeats a file name the upstream README names and the pinned tree contains - `CONTRIBUTING.md`, `SECURITY.md`, `basic.rs`, `examples_test.go`, `main.go` - was refused by `unit_checks` because no fact recorded the file; fixed at the extractor by recording tree-verified names on the `inherited_unit` fact, not by loosening the identifier rule). Carries its depends-on and exit predicate; full rationale and the classification of every rejected string: `docs/DECISION_LOG.md`, this date.

**2026-10-10 (tenth entry) - three items registered by the taskcard layer `plans/archive/reseal-and-refresh/PLAN.md` (TC-GOV-01), appended after G7-W23:** G3-W08 (candidate content gate and coverage: the coverage inventory, the cut-1 slice and the second-cut content gates), G6-W07 (issue-system operations: detector and redetector registries, the `issues_mode` field, App credentials) and G7-W25 (consumed-scope recheck and currency states, `docs/investigations/13-bump-cost-and-recheck-design.md`). The same date's `Taskcards:` pointer is appended to G7-W21, G7-W22, G6-W01 and G7-W14. The plan file is the execution-control layer of G7-W21 and G7-W22, not a new plan; each entry carries its depends-on and exit predicate, and the owner's approvals and the schema admissions are recorded in `docs/DECISION_LOG.md`, this date.

**2026-10-16 - eight items admitted by the plan of D8 (docs/DECISION_LOG.md; G3-W13 to G3-W19 wait for the owner's go), placed first in the queue in this order:** G3-W12 to G3-W19 (Lane R dependable rebuild, cards C1 to C8, one item each; analysis docs/investigations/14-lane-r-dependability.md). The first of them that is not COMPLETE becomes the active item by project/loop-prompt-ship.md rung 5a when G3-W11 is ACCEPTED, or on the owner's order; G3-W12 (C1) touches no shared code and may start beside G3-W11. The cursor's active item is unchanged by this entry.

**2026-10-11 (eleventh entry) - three items admitted on the owner decisions D1 to D7 of this date (docs/DECISION_LOG.md), appended after G7-W25:** G3-W09 (live-first correction lane, Lane L: start from the live README and add only verified corrections and verified missing information; the Monday deliverable), G3-W10 (README structure, composition, link and tone standard derived from the 36 live READMEs; `docs/README_CONTRACT.md` is under revision) and G3-W11 (Lane R regeneration idempotence: a conformant source reaches a fixed point). The same date appends a dated status sentence to G3-W06, G3-W08, G7-W06, G7-W13, G7-W21 and G7-W22 (contract under revision, progress unit authorizable, runner decision D5, push pause D6, the cut-3 facts, the #329 correction); each new entry carries its depends-on and exit predicate and adds no gate. The queue order is unchanged; list position is not the priority of G3-W09, which D7 makes the Monday deliverable.

```yaml
- id: G3-W12
  status: PENDING
  purpose: "Lane R dependable rebuild (plan of 2026-10-16, D8; analysis docs/investigations/14-lane-r-dependability.md; evidence evidence/lane-r-dependability/; three adversarial audits shaped these cards). This is a plan answering the owner's request to investigate and plan a permanent fix; it is not an authorization to run C2 to C8: C1 (measurement, no product change) may start beside G3-W11, C2 to C8 are BLOCKED_BY_GATE until the owner's go is recorded as a line 'Owner go: <date, words>' in the D8 entry of docs/DECISION_LOG.md. Promoted to the active item by project/loop-prompt-ship.md rung 5a when G3-W11 is ACCEPTED, or on the owner's order. The live README is the skeleton, the model emits operations, deterministic code owns every fact and every kept byte, and a factual REJECT stands. Eight cards in order. Common rules, every card: a worktree from scripts/new_worktree.sh; one shared-code card at a time (C1 touches no shared code); focused tests with negative controls; the official entry point on the canary at the end; evidence at evidence/build/G3_PYTHON_COHORT/lane-r/<card>.json (redacted, checksum-valid, revision-bound, counts and ids only, never provider output); a card item is COMPLETE only when that file exists with control_revision equal to the closing commit's parent and evidence/build/G3_PYTHON_COHORT/manifest.json carries an acceptance record naming the item (tests/test_queue_agreement.py already ties COMPLETE to such a record); the cards are the queued items G3-W12 to G3-W19 and an item's text is split again if a card is reworked; a card that adds a bundle field, a fact kind or a prompt first lands a docs/DECISION_LOG.md section 31 proposal naming the schema file and version, which the owner admits there, because schemas/ changes only through a named work item; a card that changes a blocking check's meaning names the docs/README_CONTRACT.md and docs/STATE_MACHINE.md revision it lands in the same commit; no card runs present, a reseal or any candidate-writing command with --root at a checkout that tracks candidates/ (seal replaces candidates/<repo>/<revision>/ and CURRENT in place): a committed script builds a scratch root with an empty candidates/ and copies of project/state.yaml, data/registry.json, prompts/ and runs/preflight, refuses to run when the drive has under 40 GB free or git status shows a modified path under candidates/, and a live batch is sequential, deletes each clone after its repository, stops at the first gateway failure and states its expected provider-call count (about 20 per repository) before it starts; no card changes data/registry.json modes, ops/proposal-authorizations/ or a workflow variable (D6 stands) and a test asserts the registry modes equal those at the plan's commit; before and after each card load_proposable_correction passes unchanged on every committed correction bundle under corrections/; a governed version bumps only for a false claim or an unsafe effect that cannot be fixed outside the governed files, or on the owner's approval under G7-W22 clause (2), behind a docs/DECISION_LOG.md entry written first that names the C1 metric, the test-split cases that prove it and why no ungoverned fix works; a bump on a factual-accuracy or safety ground (C2, C5, C6: M4, M5, M6, M8) needs no further approval and a content-loss ground (C3: M1 to M3) needs OWNER-24 first; tests/test_governed_bump_entry.py (C1) fails when origin/main..HEAD moves a governed constant or a Check version without such an entry, and fails, never skips, when main is not fetched; two equivalent failures stop the card; rollback is reverting the card's commits: a revert of VALIDATOR, NORMALISATION, REVIEWER_LOGIC or RENDERER leaves candidates rechecked and never invalidated, an EXTRACTOR revert leaves them UNVERIFIED pending a pinned re-extraction, and a bump that adds or alters fact records (a package:published_version fact, regenerated inherited units) invalidates every candidate without consumed_fact_ids, so it lands only with a test that bumps and reverts it on the stored bundles and reports the currency of all 30 (a VALID_UPDATE_AVAILABLE candidate is neither counted nor proposable until rechecked); the legacy Lane R route stays the default until C8, and until C2 is ACCEPTED no legacy candidate is proposed. Status words: backlog=PENDING, ready=READY, active=IN_PROGRESS, validation=VERIFYING, blocked=BLOCKED_BY_GATE or BLOCKED_EXTERNAL, complete=ACCEPTED. Metrics: M1 ledger completeness (live units, NON_CONTENT aside, that are byte-identical in the candidate or removed with computed evidence, over all live units; DEFER_UNRESOLVED counts as not accounted); M2 omissions with no CONTRADICTED evidence (baseline 318 of 338 OMIT_UNSUPPORTED, of which 316 cite no fact); M3 supersessions with no coverage proof (the destination section carries at least 80 percent of the unit's identifier and word tokens; the threshold is frozen in the baseline); M4 claim escapes (identifiers, numbers, versions, packages, formats in prose not equal to a cited non-identity fact value); M5 junk-lint hits; M6 catch rate on the corpus test split, differential (the detector fails the injected text and not its clean twin), per class and for reviewer alone and together; M7 rerun behaviour (two runs in fresh processes with an empty runs/ seeded only from the sealed bundle are byte-identical with zero calls, which J5 already passes 30 of 30 and is regression evidence only; and a changed fact re-renders only the units whose digest includes it); M8 claim-level blind audit (the C8 protocol); M9 yield (judge-authorizable candidates over processable inputs), printed beside every other metric so a gate that rejects everything cannot read as green. Floors are numbers, changeable only by an owner decision in docs/DECISION_LOG.md (proposed values): M1 100 percent and M2, M3, M4, M5 zero on the test half and on every pilot README; M6 at least 95 percent on the test split and at least 90 percent in every class with at least 5 test cases; M7 as defined; M8 zero unsupported claims in 200 sampled; M9 not below its value at C3 and at least 8 of 10 at C8. M1 to M5 are computed by tools/lane_r_audit without importing validation/, reconciliation/ or composition/ decision logic, so a gate never grades itself. Baseline at control revision 4a7baf11 (evidence/lane-r-dependability/ledger_baseline.json): 389 of 746 kept units not printed; 316 of 338 OMIT_UNSUPPORTED cite no fact; 1514 SUPERSEDE_REDUNDANT; 29 of 30 fail J4, 26 of 30 fail J6; 26 of 30 model REJECTs folded to ACCEPT; about 22 hand-found factual errors in 14 sealed bundles (agent-read, approximate until C1 re-derives them). C1 MEASURE. Objective: make dependable measurable before any product change. Owned paths: tools/lane_r_audit/ (new; the loop writes it, it imports src/ read-only and is the source of the G3-W12 exit numbers, an exception to the tools boundary recorded in docs/REPOSITORY_LAYOUT.md, tools/README.md and project/loop-prompt.md in C1's first commit), tests/test_lane_r_audit.py, tests/test_lane_r_ratchet.py, tests/test_governed_bump_entry.py (flat invariant tests), data/lane_r_corpus/, evidence/build/G3_PYTHON_COHORT/lane-r/. Prerequisites: none; read-only on candidates/. Dependencies: none. Steps: (1) freeze the holdout by pinning, not copying: the 30 sealed bundles as (repository, revision, manifest sha256) triples read through git at the control revision by a tested pinned reader (the CI job fetches that revision and fails, never skips, if it cannot), their live README hashes and the sha256 of data/readme_standard/survey.json, and record that revision in docs/DECISION_LOG.md as the single frozen base shared with G3-W11 rung 5; (2) implement M1 to M3 and M9 from bundle files through the judge's clause readers (a thin read-only wrapper that cites the judge's private helpers by name), define M4 to M6 as interfaces over a detector registry whose baseline detectors are the existing BC-04, BC-14 and the reviewer (their corpus catch rate is the M6 baseline), implement M4 and M5 independently of the C2 gate and at least as broad (the two are compared on the corpus and the disagreements reported), and write M7 and M8 as procedures with a committed sample list; (3) reproduce the baseline numbers as the harness's own regression test; (4) build a corpus of at least 60 labeled cases under data/lane_r_corpus/ with the excerpts that justify each (the review-packets are not in the repository): the ten traced cases T1 to T10 in evidence/lane-r-dependability/Q_claims.md, at least 10 further hand-found errors re-derived and labeled from the 30 sealed bundles with the sentence, the cited facts and the live text, at least 20 ledger cases, at least 20 synthetic mutants from a seeded mutator that changes a version, package name, format, count or polarity in a clean candidate, and at least 20 clean negatives; each case has a clean twin and catch is differential; at least 8 cases for every class that carries a bar; registry probe readings are stored as fixtures; the corpus is split by a fixed hash of the repository name into a dev half and a test half, the split file committed before C2 starts and detectors tuned on dev only; (5) the ratchet: data/lane_r_corpus/ratchet.json holds the best value of M1 to M6 and M9; CI computes them from the pinned reader and fails when any is worse than the value in origin/main's file (read with git show origin/main:..., so a branch cannot lower its own baseline); the file may only improve; a waiver is an owner item naming the metric, the old and new value and an expiry at most 14 days out, which a test parses, and status prints the live waivers; two tiers, a seven-second ledger tier and a three-minute judge tier; (6) control re-run: before C2 starts, re-run the deterministic stages (reconciliation, placement, validation) offline over the frozen inputs with no provider call and record it as the baseline, because 23 of the 30 bundles were validated by validator version 3. Validation: two runs give identical M1 to M6 and M9; M1 to M3 match ledger_baseline.json; every test above passes. Evidence: lane-r/C1.json. Rollback: tools, tests and data only, delete. Complete: baseline, corpus, split and ratchet committed and green, and the corpus is reviewable by the owner."
- id: G3-W13
  status: PENDING
  purpose: "Card C2 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C2 CLAIM GATE. Objective: no wrong identifier, number, version, package, format or capability claim reaches a candidate. Owned paths: components/readme/validation/ (BC-04 and BC-14 extended; no new BC id, 13 exist, at most fifteen), components/readme/evidence/facts/published_version.py, components/readme/extractors/surface/registry.py and extractor.py (EXTRACTOR_VERSION), core/package_registry.py, components/readme/bundle/seal.py (head re-resolution), core/candidates.py and components/propose/wave.py (the propose gate below), tests. Prerequisites: C1 ACCEPTED, the owner go. Dependencies: none beyond C1. Steps: every identifier, number, version, package name, format name and framework in LLM-owned prose, in the units BC-04 already lists (renderer-owned lines excluded), equals a value of a cited non-identity, non-symbol fact; a sentence whose cited facts are all identity, package or public_symbol kinds states no capability, edition or support claim (trigger words: supports, support for, adds, includes, provides, enables, not supported, not functional, unsupported, free, commercial, Enterprise), and a token named in a SUPPORTED not-supported inherited unit is not asserted positively anywhere; a package:published_version fact for every registry-ecosystem package that is published and owned, with a typed reason (NO_REGISTRY, NOT_OWNED, UNREAD) recorded otherwise and UNREAD blocking sealing as BLOCKED_EXTERNAL; the package named in prose and commands equals package:name read at the re-resolved head (BC-14 rule c, the rename check; registry summary or deprecation text where the registry facade is extended to carry it); the head is re-resolved at seal and again before propose (bundle/seal.py; no network in validation/), a moved head giving VALID_UPDATE_AVAILABLE; deterministic lint for a line ending in a colon before a heading or end of file, badge syntax, split PEP 508 specs, scraped XML-doc fragments and counts not derived from facts, each naming its upstream cause in docs/DEFECT_INDEX.md (the lint is a gate, not the fix); the propose gate: proposal_gate_refusal computes the consumed-scope recheck (a pure read) and refuses, with a new typed Refusal, a bundle whose currency is UPDATE_REQUIRED or UNVERIFIED in the validator, extraction or reviewer scope, and wave-readiness prints such a row BLOCKED, not stale-but-proposable (this blocks a proposal only and changes no bundle state). Validation: test-split differential catch at least 95 percent for the version, formatting, scraped-text, count and symbol-prose classes and at least 90 percent for the invented-capability and polarity-contradiction classes (drift is the monitor's classification, tested as a sealed/head fixture pair, not a catch rate); the false-positive rate recorded on the clean set and as the share of the LLM-owned units of the 30 stored candidates the gate flags (about 25 percent of 3066 in the strict-rule prototype); above 5 percent C2 records a further owner item and is BLOCKED_EXTERNAL on it; a negative control per rule; a propose negative control (seal a fixture bundle, bump VALIDATOR_VERSION so a BC-04 rule fails it, expect the refusal and BLOCKED). Governed: VALIDATOR_VERSION and EXTRACTOR_VERSION on the factual-accuracy ground (the extractor bump leaves candidates UNVERIFIED pending re-extraction and conflicts with the first G3 exit bullet, so the necessity entry says so). Evidence: lane-r/C2.json. Rollback: revert. Complete: M4, M5 and M6 for these classes meet their floors on the test split and M9 is not below its C1 baseline."
- id: G3-W14
  status: PENDING
  purpose: "Card C3 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C3 HONEST LEDGER. Objective: a keep decision is honoured and a removal is justified. Owned paths: components/readme/reconciliation/, components/readme/composition/placement.py, components/readme/composition/authoring.py (NORMALISATION_VERSION only), components/readme/evidence/facts/inherited.py (INHERITED_UNITS_VERSION and the unit inventory), BC-05 and validation/deferrals.py in validation/, tests. Prerequisites: C2 ACCEPTED (same validation file); OWNER-24 answered before the first bump. Dependencies: C2. Steps: OMIT_UNSUPPORTED is allowed only with CONTRADICTED evidence that code computes and the model cannot assert: a FAILED execution receipt for an example inside that unit, a deterministic mismatch between a token in that unit (identifier, number, version, package, format) and the value of the fact with the same key, or a link whose target the probe found missing; a fact id the model cites is never evidence by itself (that is the BC-04 citation check); everything else is kept and printed, or, where the plan cannot place it, DEFER_UNRESOLVED, which BC-05 blocks for every unit kind outside the deferrals.py advisory classes and which M1 counts as not accounted (DEFER_UNRESOLVED is never printed today); SUPERSEDE_REDUNDANT requires the M3 coverage proof or a shell-owned unit kind; a PRESERVE or MOVE heading, badge row or html block renders, or the plan reclassifies it through a typed mapping field (a dispositions.json schema change: a section 31 proposal and owner admission first); BC-05 inspects every unit kind. Validation: a mutation test per rule; each rule is applied to the 30 stored ledgers and the number of rows it would reject is reported; S4 reconciliation, placement and BC-05 are re-run offline over the frozen inputs (sealed facts, investigation and replies replayed; no clone, no provider call, writes only under the scratch root; a live present re-run is not the gate because present clones the current upstream head and 14 of 34 candidates had drifted); every holdout input counts in the denominator and an input that does not seal counts as failing; the M1 to M3 floors are measured on the live-anchored route in C4 and C8, not on the legacy composer (only 56 percent of absent superseded non-heading units reach 0.8 coverage and 30 percent reach 0.95). Governed: NORMALISATION_VERSION, INHERITED_UNITS_VERSION (only when a named case needs it) and VALIDATOR_VERSION, on the content-loss ground. Evidence: lane-r/C3.json, which records the SHA-256 of acceptance/judge.py. Rollback: revert (an INHERITED_UNITS revert is a fact-record change, see the common rollback rule). Complete: each rule landed with its mutation test and the rows-rejected report, and M1 to M3 are executable definitions."
- id: G3-W15
  status: PENDING
  purpose: "Card C4 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C4 LIVE-ANCHORED PATCH ENGINE. Objective: when a usable live README exists it is the skeleton and the model emits only operations. Owned paths: components/readme/composition/patch/ (new), prompts/section_patch.yaml (new), components/readme/evidence/facts/inherited.py (byte spans and a content-derived key added beside the ordinal id), components/readme/bundle/ (the patch route seals the dispositions.json, plan.json and content_units.json the judge reads, mapping KEEP to VERIFIED_PRESERVE, DELETE to OMIT_UNSUPPORTED with a computed CONTRADICTED fact and REPLACE to CORRECT_WITH_EVIDENCE), cli.py and core/state/present_transaction.py (present --mode live-anchored and present --at-revision <sha> using clone_pinned; the defaults are unchanged), schemas/candidate-bundle.schema.json (a route field, after the section 31 proposal), components/propose/effect.py (one writer per repository, below), tests including an import-cycle test; it imports readme_correction (apply and confinement ideas only: its Edit is a line fragment of at most 200 characters with no delete and no heading insertion, so the operation type is new). Prerequisites: C2 and C3 ACCEPTED; OWNER-26 answered. Dependencies: C2, C3. Steps: parse the live README into the inherited_unit inventory with byte spans and a content-derived key (heading path, ordinal under it, text hash), because ordinal ids shift when one block is inserted; the operation schema is KEEP (the default for any unmentioned unit), REPLACE, INSERT_AFTER and DELETE, each with its evidence kind; a deterministic applier copies kept bytes and refuses an operation that touches protected content, a closed set computed by code (badge rows, the first H1 and banner block, HTML blocks, license, notice and security headings, fenced code), never a model label; the model is called once per section (the units under one live H2), sees only that section's gaps (standard conformance, Lane L detector gaps, stale facts) and returns operations only; REPLACE and INSERT pass the C2 gate; DELETE needs CONTRADICTED evidence the applier recomputes as C3 defines it, never a model assertion; a malformed, unknown-id, out-of-span or unverifiable operation is dropped, its unit is KEPT byte-identical and the drop is recorded as a finding, and nothing falls back to a replace; the bundle records route live_anchored and seal refuses to replace a bundle of another route at the same revision; one writer per repository: Lane L and Lane R share the presenter branch repository-presenter/readme-update, so propose carries the route in the pull request body and refuses a candidate whose repository has an open presenter pull request of the other route unless the authorization record names it in supersedes_prs (a negative control in components/propose). Validation: property tests (zero operations is the identity; bytes outside the touched spans are unchanged); BC-05, BC-08 and the judge's J4 and J6 are computed for a patch candidate from the live README bytes and the output bytes (every live unit span is byte-identical or inside a recorded operation), never from dispositions the same route wrote, because KEEP mapped to VERIFIED_PRESERVE passes them by construction; adding prompts/section_patch.yaml leaves all 30 holdout bundles at their current recheck currency; every pilot command writes to a scratch root; the pilot on the seven Cells repositories (development, not acceptance) runs on pinned inputs and is compared with the legacy route on M1 to M9, then goes to the C8 blind review. Governed: a new prompt (a new governed prompt version). Rollback: remove the mode flag. Complete: on pinned inputs the pilot beats the legacy route on M4, M6 and M8 and loses on none (M1 is 100 percent by construction under KEEP and is not counted as a win)."
- id: G3-W16
  status: PENDING
  purpose: "Card C5 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C5 FACT-RENDERED SECTIONS. Objective: nothing a fact can state is written by a model. Owned paths: components/readme/composition/renderer.py and its section renderers, components/readme/extractors/surface/doc_text.py and the build_test_asset fact (scraped symbol text and file counts, the earliest causal stage of Q classes G and H), tests. Prerequisites: C4 started (the sections must be reachable from the patch engine). Dependencies: C4. Steps: inventory which sections already render from facts (badges, Navigation, Dependencies, Installation, API reference rows, the Enterprise paragraph, At a Glance and the Development and Testing sentences already do); make them callable from the patch engine; counts print only from facts; fix the two upstream defects (scraped XML-doc text as API rows; the test-file count taken from an evidence string). Validation: M4 and M5 zero on those sections on the test split; a test per section. Governed: RENDERER_VERSION only when a named case needs it, otherwise the card ships without that bump. Evidence: lane-r/C5.json. Rollback: revert. Complete: the inventory is closed, every such section is fact-rendered, M4 and M5 are zero."
- id: G3-W17
  status: PENDING
  purpose: "Card C6 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C6 A REVIEWER THAT CAN SAY NO. Objective: a factual REJECT that names a claim stands. Owned paths: components/readme/review/independent/, prompts/independent_review.yaml, components/readme/acceptance/judge.py (the new clause J7_REVIEW only), core/llm/ (the per-model request profile only), tests. Prerequisites: C1 and C2 ACCEPTED. Dependencies: C1, C2. Steps: a fold registry listing each permitted byte-level refutation with its test; remove the folds that rest on the contested fact itself (a cited-fact literal when the fact is the thing in dispute) and the absent-field misparse that folded the Words-.NET RTF/HTML finding; only a factual finding that names a section and a claim stands, while a presentation REJECT stays repairable and advisory (22 of the 26 stored REJECTs were presentation and 2 of the 4 factual ones were wrong); a surviving REJECT routes to its causal stage; J7_REVIEW is the sealed review being an honest ACCEPT by the rule of core/candidates.py::_review_refusal, so that status's authorizable count equals the bundles propose would accept (the reviewer is advisory to J1 to J6 and binding through J7); if OWNER-23 admits it, gpt-oss as a reviewer-only route with a per-model request profile (its strict 16-token probe returns no content), blind to the author's rationale and never sealing a gpt-oss-authored result; otherwise a sampled per-claim entailment check (MiniCheck class) evaluated offline on the corpus first. Validation: on the corpus test split the reviewer alone (gates off) catches at least 70 percent of the injected factual cases and gates plus reviewer together at least 95 percent with zero injected factual errors passing; on the clean set the factual REJECT rate is recorded and the owner decides above 10 percent; fold removals are replayed offline over the 313 stored advisory findings of all 30 bundles (raw_calls.json exists for 6 only) and the number of REJECTs that stand is reported, a live re-read reported separately. Governed: REVIEWER_LOGIC_VERSION and the prompt route, on the factual-accuracy ground. Evidence: lane-r/C6.json. Rollback: revert. Complete: M6 at floor and the reviewer-alone catch rate recorded."
- id: G3-W18
  status: PENDING
  purpose: "Card C7 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C7 FIXED POINT. Objective: a rerun after a changed fact recalls the model only for the sections whose input digest changed (a deliberate per-section memoization, not model determinism); the independent first run uses an empty call store. Owned paths: components/readme/bundle/ (not recheck.py), components/readme/composition/patch/, schemas/candidate-bundle.schema.json (per-unit digests, after the section 31 proposal), tests; the call-store seeding in core/llm/ belongs to G5-W02 and is imported, not edited (if G5-W02 is not ACCEPTED when C7 starts, the digest is recorded in the bundle only). Prerequisites: C4 ACCEPTED; OWNER-26 answered. Dependencies: C4. Steps: a per-unit input digest (the facts it cites, the prompt, the unit text); only a section whose digest changed may call the model; the verdict is stored per candidate hash; a human-approved golden file per pilot repository. Validation: M7: two runs in two fresh processes with an empty runs/ seeded only from the sealed bundle are byte-identical with zero calls (regression evidence, since J5 already passes 30 of 30; it is memoization), and for each unit kind a mutation of one input fact re-renders exactly the units whose digest includes it and leaves every other unit byte-identical, and a prompt-text change outside a unit's digest calls the model for no unit; the G3-W11 synthetic-bump test runs as the closing check. Governed: none planned; a bump needs its own entry. Evidence: lane-r/C7.json. Rollback: revert. Complete: M7 holds on the pilot repositories."
- id: G3-W19
  status: PENDING
  purpose: "Card C8 of the Lane R dependable rebuild (plan of 2026-10-16, D8; the head text, common rules and metrics M1 to M9 are in G3-W12; item ids G3-W12 to G3-W19 are cards C1 to C8, in order). Until the owner's go is recorded in the D8 entry of docs/DECISION_LOG.md only G3-W12 may start. C8 PILOT AND EXIT. Objective: decide the default route on evidence. Owned paths: cli.py (a status line printing M1 to M4 and M9 only), tests, evidence/build/G3_PYTHON_COHORT/lane-r/, ops/lane-r-pilot/ (the owner's verdict files); acceptance/judge.py is not edited here (any J4 or J6 alignment lands in C3 with the judge's SHA-256 recorded, and only after G3-W11 is ACCEPTED). Prerequisites: C2 to C7 ACCEPTED; OWNER-25 answered. Dependencies: C2 to C7. Steps: ten repositories chosen and committed by the owner before C4 starts, at least four of which contributed no corpus case (registry entries outside the 30 sealed bundles count); blind review run by a committed seeded script that assigns each README a random id and strips route markers, generator headers and PR text; the owner rates every README of the ten (ACCEPT_AS_IS, ACCEPT_WITH_EDITS of at most 5 lines, REJECT) and a second human rater who did not write the cards rates a random half (an agent session is not a rater); disagreement takes the stricter verdict; the raters also say which route they believe each README is from and the rate of correct guesses is recorded as the blinding quality; M8 is a claim-level audit: the same script draws 20 factual claims per new-route README (200 in all), the raters mark each SUPPORTED or NOT SUPPORTED against the pinned source revision, and M8 passes only at zero NOT SUPPORTED; sample, seed and verdict files are committed before unblinding; the pilot is judged by the acceptance/judge.py whose SHA-256 C3's evidence records (a mismatch voids the pilot) and runs at the final merged code revision (a governed version moved after the pilot voids it). Validation: the G3-W12 exit predicate in docs/EXECUTION_STATE_MACHINE.md holds. Evidence: lane-r/C8.json and the verdict files. Rollback: the default stays legacy; before the default is switched REPOSITORY_PRESENTER_SEALING_PAUSED stays 1 (the daily sealing cron would otherwise reseal the portfolio unattended on the new route) and the first portfolio re-seal is a separate owner-started wave whose expected provider calls, clone disk and target N/44 are written in this card's evidence. Complete: the exit predicate holds at the final merged code revision and a verdict file ops/lane-r-pilot/<owner>__<name>.json, committed by the owner, exists for each of the ten READMEs (blinded id, verdict, rater, date); the default is switched only when at least 8 of 10 new-route READMEs are accepted (proposed), none carries an unflagged factual error and the new route is rated at least equal to live on at least 8 of 10 (proposed), against OWNER-25's threshold; otherwise the item stays IN_PROGRESS with a typed finding and the owner decides. Keeping the legacy default is a failed exit, never a completion."
# G2 entries already in state.yaml (the active item is not repeated here); an entry is "absent" only
# if it is in neither next_ready_items, active_work_item, nor the accepted evidence
- id: G2-W19
  status: PENDING
  purpose: "Sampling determinism probe (section 27.5 D4, pulled forward on the 2026-09-04 composition-variance measurement in 27.10): probe the gateway for seed support per section 18.4's discovery pattern with one bounded call per served model; if honoured, add seed to Sampling and to the request payload (the cache key rotates once, recorded) and prove by test that two identical requests return identical content, through the fake gateway and live on one canary job; if not honoured, record the finding in 27.10 and in the ledger. Either way, every sealed bundle's manifest records the composition's advisory count and blocking failures so variance is measured per composition rather than sampled by accident. Acceptance: the probe result is recorded; seed is adopted or its absence recorded; the canary re-seals byte-identically with zero calls; hosted CI green."
- id: G2-W12
  status: PENDING
  purpose: "Make every LLM job's structural constraints constructive instead of post-hoc (section 27.5 D1; cause RC1 in 27.2). The code emits each call's skeleton and a per-call JSON schema: slots enumerated with their allowed fact IDs as enums, fixed-length slot arrays, additionalProperties false. Shell section decisions leave the planner's output (code already decides them in planning.py condition_holds). Dispositions a reconciliation rule forces are computed in code and only the free ones are asked. Allowed identifiers travel as a list. The repair packet carries the same skeleton, the section's fact set, and the slot's subject. Prose stays the model's. Acceptance: on a fresh canary composition, first-attempt acceptance is at least 95 percent for every job and the re-ask share at most 5 percent, measured from the sealed calls.jsonl by a test helper; the rejection families of 27.1 (outside-section citation, wrong slot set, missing shell decision, non-fact identifier) cannot be produced by a schema-valid reply, proven by tests; rerun byte-identical with zero calls."
- id: G2-W21
  status: PENDING
  purpose: "Every code path that shapes rendered bytes is a recorded dependency (G2's own promise; the gap the loop named at d147b4a): dependencies.json's component classes gain the composition package's normalisation logic (authoring.py's canonical_abbreviations and the unit_checks rewrites, and any validator normalisation that mutates output) as a versioned component that reopens COMPOSING, beside shell and renderer; the invalidation-matrix test gains the case that a normalisation change altering output reopens COMPOSING and one that does not yields NONE. Insert before G2-W13. Acceptance: the new matrix case passes; the canary's dependencies.json records the component; re-seal byte-identical with zero calls; hosted CI green."
- id: G2-W13
  status: PENDING
  purpose: "Bind each capability's prose to its title, which nothing holds today (27.2 RC2: authoring packs the union of all slots' facts and never the titles; the renderer joins title and sentence positionally). The planner assigns pairwise-disjoint fact sets per capability or declares shared facts explicitly, enforced by plan_check; the title travels in the authoring packet and the slot identity; a deterministic check confirms each unit cites only its slot's facts and that the title's identifiers and format names appear among the cited facts' values; README_CONTRACT.md check 4 gains that sentence (27.8). Acceptance: swapping two capability sentences in a synthetic candidate fails the check; the canary's seven capabilities each describe their own title, judged by the check; re-seal byte-identical."
- id: G2-W16
  status: PENDING
  purpose: "Acceptance decided by content, never by directory history (27.2 RC5 and RC8). A reviewer finding demotes to advisory only when a deterministic check contradicts it; a finding with causal_stage unclear is classified by code from its section's owner, never auto-demoted; a finding re-raised after its one repair attempt never demotes: it is code-caused (section 26 rule: add the check) or it blocks; every failure record carries section_id and causal_stage as fields, retiring the bracket-prefix and detail-string regexes; the three-character substring demotion goes; required rows admit zero advisories before READY_FOR_PROPOSAL; README_CONTRACT.md section 6 is revised accordingly (27.8); independent_review's output is bounded (a capped findings list with anchored quotes) so its token budget never truncates, and a truncation is a defect routed to the prompt manifest, never a retry (the reviewer truncated at 6000 tokens during W12). Acceptance: the 65b1f577 review.json replayed under the new policy blocks on F02 and F04; a synthetic oversized review is bounded, not truncated; a synthetic re-raised finding blocks; a grep-enforced test proves no regex over prose or detail strings decides routing or invalidation; canary re-seal ACCEPT with zero advisories."
- id: G2-W22
  status: PENDING
  purpose: "Plan-level repair escalation (section 27.2 decision of 2026-09-05; split from G2-W16 for size): a repair attempt at a content stage that fails because its own binding proves the requested revision would change the plan's slot set or example selection (S6's per-task schema requires exactly the plan's slots, so such a fix is a planning decision by construction, never inferred from prose) escalates once to a plan-level repair at S5 carrying the finding's context; the revised plan re-enters S6 through S8 under the same two-attempt and one-fingerprint rules; a repair still unable to produce a schema-valid revision after escalation blocks as today. Acceptance: a synthetic finding whose fix drops or adds a plan slot escalates once and round-trips to ACCEPT; one still unrepairable after escalation blocks; the canary's fresh composition under the bounded-review manifest ends ACCEPT with zero advisories rather than EXIT_INCONSISTENT; rerun byte-identical with zero calls; hosted CI green."
- id: G2-W17
  status: PENDING
  purpose: "Coverage defects stop dead-ending as presentation advisories (27.2 RC6: six of twelve examples and five of seven formats never SUPPORTED, 59 units omitted). A per-row coverage ledger records each contract row's required fact kinds and their resolution with reason; check 12 (a required row whose facts are unresolved fails closed and routes to EXTRACTING, never to repair, 27.8) is admitted only when a sealed candidate exhibits that defect - none does at 65b1f577, every required row has SUPPORTED facts - so per loop-prompt section 6 rule 14 it waits for the G3 cohort and is proposed in section 31 when a cohort candidate shows the gap (reviewer decision 2026-09-05); file-reading examples receive fixtures from the repository's test assets (build_test_asset facts) or from the saved output of an executed example, and are executed; examples.json is sealed (its evidence path dangles today); live probes record retrieval time and status, and volatile observations such as the PyPI latest version string leave the hashed fact; the execution environment passes proxy and CA variables. Acceptance: the canary's example:001, :007 and :011 execute; input formats OBJ, STL, glTF and COLLADA reach SUPPORTED; the ledger and coverage ratios are in the bundle; re-seal byte-identical."
- id: G2-W20
  status: PENDING
  purpose: "Referential links and commands in authored units (D1 completion; the two prose families W12 left post-validated because the gateway answers HTTP 400 for a pattern in strict json_schema, 27.10): an authored unit never writes a URL or a command as text; it references link_target and install_command facts by ID from a per-call enum the packet and schema carry for the slot, and the renderer emits the link or command deterministically from the fact; unit_checks keeps rejecting a literal URL or command. Insert after G2-W17, before G3-W01. Acceptance: a synthetic reply with a literal URL is rejected while the referential form renders the same link; section_authoring first-attempt acceptance reaches at least 97 percent on the re-seal, measured by the ledger helper; the canary re-seals byte-identically or with its recorded delta; hosted CI green."
- id: G3-W01
  status: PENDING
  purpose: "Python cohort (section 28.5; 30.9; census 28.10). Step one, before any composition: a facts-only pass (a present flag that stops after S2 with the processability and coverage record) over all twelve remaining Python registry repositories, recording every failure class with zero provider calls, plus per-repository stage timings (venv, install, examples, probes), fixture availability by suffix, and registry publication status; each anticipated class in 28.10 is confirmed or refuted here before any fix. In the same preflight, the cold-run determinism measurement folded in from G2-W23 (delete the canary's runs/ transaction, present once from cold, compare byte for byte to the sealed bundle, record the result and any differing stage in 27.10; identical demotes G5-W02's bundle-seeding to a fallback). Before step two, the two-reader rule lands with a test (27.8; owner decision 2026-09-06 00:15, section 31): a review finding classified as a prose judgment on a required row blocks only when a second independent review under a different seed raises an equivalent finding (same section, same fingerprint class); a single-reader finding is recorded in review.json as single_reader_advisory and the candidate seals - the canary's fresh composition of 2026-09-05 23:36 already exhibits the class. Step two: compose the twelve in up to three repository lanes (separate transactions, serialised aggregation, per plans/idea.md; lanes scaled from the first lane's rate-limit evidence), sealing every candidate that passes all eleven checks and recording an evidence-bound disposition with its resume predicate for every one that does not. Fix by failure class with a regression test each, never per repository - including fixtures for file-reading examples from test assets or an executed example's output, moved here from G2-W17. The loop reads the cohort report, never a per-repository bundle, unless a failure class needs the look. Time box 6 hours from promotion (section 28.12): inside it, fix by failure class in yield order (published package, no native dependency, fixtures present, tests present first); at the box, seal what passes, give every other repository an evidence-bound disposition naming its failure class and resume predicate, and accept. Add the test that section 27.9 and state.yaml agree on every non-active queued item. Acceptance: preflight report, cold-run measurement, and cohort report (sealed, disposition, failure class per repository) in the gate evidence manifest; status prints the sealed count; every sealed bundle fresh-process zero-call proven; hosted CI green."
- id: G4-W10
  status: PENDING
  purpose: "Layered plugins and ecosystem-generic shared code (section 29.6 E3-E5): EcosystemSpec (ecosystem, language, manifest globs, source suffixes, fence aliases, registry template, badge templates, install-command template, symbol separator); shared RegistryProbe on httpx ported nearly intact from the legacy ecosystems/registry_request.py with resolver.py's lessons (Maven via repo1.maven.org never search.maven.org, crates.io named User-Agent, C++ has no registry); ExampleVerifier base on core/execution.py with a disposable profile environment, per-ecosystem timeouts, lockfile flags, resolved versions in the receipt, BLOCKED_TOOLCHAIN to UNRESOLVED never CONTRADICTED; renderer badges, Installation, fence language, REGISTRY_NAMES, _LANGUAGE_ALIASES, PLATFORM_SLUGS, and bounded_records depth all read from the spec; the Python plugin re-expressed as a spec with its facts unchanged; plugin registration discoverable by module name (platforms/<ecosystem>.py exposes PLUGIN; registry.py imports by ecosystem name and never lists plugins), so lane B (section 28.12) adds TypeScript, Go, Rust and C++ without editing a shared file; docs/REPOSITORY_LAYOUT.md section 2.1 restated so a platform module imports core/, the shared surface facade and verifier base, and its own file. Acceptance: canary re-seals byte-identically; a synthetic net spec renders csharp fences, a NuGet badge, and a dotnet install block in a test; toolchain-absent and network-off tests; hosted CI green."
- id: G4-W09
  status: PENDING
  purpose: "Shared surface extractor (section 29.6 E2): vendor aspose.org's 17-file extraction closure (named in section 29.2) plus extraction/package_manifest.py, commands/foss/dependency_extract.py, lib/publication_probe.py and lib/package_registries.py (section 29.12) under extractors/surface/_vendor/aspose_extraction at revision 16d75e95d4 (the checkout's committed HEAD on 2026-09-06; re-pinned from b3ad363a; the 509-file dirty working tree recorded, never pulled), one file record each, mypy and ruff overrides confined to _vendor, recorded patches only (sorted package-root and csproj picks, case-sensitive suffix matching, MAX_FILES a constant, family vocabularies as parameters). Minimal closure only, never wholesale; a file no test exercises is not pulled; known upstream defects (section 29) are patched by record or quarantined behind the facade. Folded in from G4-W08 (2026-09-05, section 28.12): schemas/reuse-manifest.schema.json gains a sources array with the legacy source's fields per source and a per-record source_id (tests/test_schemas.py updated); aspose.org is recorded as the second source at D:/onedrive/Documents/GitHub/aspose.org pinned to b3ad363aaf69ce4d00d9aa02ecc59616b9705814 with working_tree_at_freeze DIRTY, honestly, with the seed dispositions (scripts/pipeline/extraction/** EXTRACT_AND_REFACTOR, its tests ported, the legacy vendored_asposeorg/** superseded as fixtures) and census_gate G4_MULTI_LANGUAGE_COHORTS; extractors/surface/_vendor/ is named in docs/REPOSITORY_LAYOUT.md under the vendor-boundary rule. Time box 4 hours together with G4-W10 (section 28.12). A typed SurfaceExtractor facade normalises node types to symbol_kind, maps :: + and generics to slug-safe values, emits defined_at from the declaring file and line, and serves surface, format, and manifest facts; beside it a ManifestReader facade over the vendored package_manifest.parse_manifest (identity, floor) and dependency_extract.extract_dependencies (the contract row 9 snapshot: required, optional, native and system, development, with versions), and a RegistryProbe facade over publication_probe for every registry (section 29.12); first consumer the .NET spec's surface_facts, no cohort. Port the site-independent extraction tests (about 19 of 25); pin the three tree-sitter packages exactly with a parse-probe test per language. Acceptance: canary facts unchanged; run-twice and shuffled-order determinism identical; vendor-boundary grep test; parity control implemented; hosted CI green."
- id: G4-W11
  status: PENDING
  purpose: ".NET spec and cohort (section 29.6 E3-E6): identity, floor and the dependency snapshot from the vendored ManifestReader (aspose.org package_manifest and dependency_extract, section 29.12; the legacy ecosystems/dotnet.py only for a field they lack), surface through the shared extractor with the C# preprocessor rules, a fresh verifier on the base (dotnet build in the isolated workspace, restore disabled where a lock exists, NuGet config redirected; tools resolved with shutil.which including .cmd shims), registry facts through the vendored RegistryProbe, a negative control that rejects one realistic invalid example; then the six active .NET repositories as a cohort with fixes by failure class and evidence-bound dispositions (the Email .NET CS1929 build failure; PSD-.NET NON_PROCESSABLE). Parity per repository; a reflection-stub corroboration (E6) only if parity fails. Time box 5 hours from promotion (section 28.12): yield order from the section 28.11 census; at the box, seal what passes, dispositions for the rest, accept. Acceptance: cohort report in the gate manifest; every sealed bundle zero-call proven; hosted CI green."
- id: G4-W17
  status: PENDING
  purpose: Shared-code fixes the lanes propose, landed in arrival order (owner, 2026-09-06). The active
    item from 2026-09-06 to 2026-10-14; superseded as the active item by G3-W11 (Lane R primary, owner
    decision 2026-10-14, docs/DECISION_LOG.md). Its arrival list (items 1 onward, cited in code and tests
    as 'G4-W17 arrival item N') is preserved verbatim at evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/preserved/g4-w17-arrival-list-2026-10-14.md;
    landed fixes are on main, open proposals are in docs/DEFECT_INDEX.md. Not a queue head.
- id: G5-W02
  status: PENDING
  purpose: "Make the sealed proof hold without this machine's runs/ directory (27.2 RC4: the cache is gitignored, per revision, keyed on a prompt that embeds identity:revision; a hosted runner always starts empty). Remove identity:revision from every job packet, the renderer keeps the fact; seed the call store from the sealed bundle's accepted artifacts by recomputed request hash so a fresh clone replays with zero provider calls; extend check 11 to a fresh-state proof (fresh process and empty runs/), the README_CONTRACT.md revision this item carries (27.8); record temperature, max_tokens, response_format and derived_via_reask per ledger record; add an environment class to dependencies.json (Python version, OS, extractor version, resolved site manifest) that reopens EXTRACTING; probe the gateway for seed support and adopt it if honoured (section 18.4). Acceptance: delete runs/, run present for every current candidate: byte-identical, zero calls, proven by a test; a new revision with unchanged facts reuses every call; running under 3.11 versus 3.13 reopens EXTRACTING."
- id: G6-W01
  status: PENDING
  purpose: "Issue-filing write path (components/issues/file.py - the one piece missing from draft.py/ledger.py/model.py/redetect.py, all already landed and exercised read-only). The GitHub App already carries issues:write in its registered permission set (tools/github_app/manifest.json, confirmed 2026-09-30 - this was previously declined mid-session specifically because OWNER-04 was still OPEN; OWNER-04 is now SATISFIED, so the credential-side blocker this item was correctly gated behind no longer exists). Mirrors metadata/apply.py's own gated-write pattern exactly: a write-capable function, an owner-controlled environment flag (REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED, never inferred from credential presence), a distinct write-scoped token, a duplicate-filing guard against components/issues/ledger.py's own fingerprint, and a recheck-before-effect via redetect.py immediately before the actual create call. This is the single item every currently upstream-blocked candidate (Cells-Cpp's trigraph, and whichever others this week's re-verification confirms are genuinely upstream, not this project's own code) is waiting on - without it, those candidates have no path to ever unblock, seal, or go live. Acceptance: a real gh issue create call against a disposable/test repository succeeds, is idempotent on a second identical attempt (no duplicate, per the ledger), and the token is never logged; hosted CI green; then, for real: Cells-Cpp's trigraph defect is actually filed against its own upstream repository, with the issue URL recorded in evidence/upstream-defects/. 2026-10-01: the write-path mechanism itself (components/issues/file.py, core/github/client.py::create_issue, cli.py's file-upstream-defects --file) recovered from a 4-day-stranded branch and re-landed against current code, mirroring metadata/apply.py's gated pattern exactly - 58 tests, all against injected fakes, zero live GitHub calls, hosted CI green (docs/DECISION_LOG.md, this date). Status stays PENDING: neither GH_ISSUES_WRITE_TOKEN nor REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED is set in this environment and no disposable/test repository is named anywhere in this project's own records as this item's live-fire target, so neither the disposable-repository gh issue create proof nor the real Cells-Cpp filing was attempted - both remain this item's own open resume predicate, needing an owner-named target repository and a provisioned write-scoped token before either can proceed. 2026-10-11 status: nothing filed. The registry-ownership decision (docs/DECISION_LOG.md, this date) adds two handoff candidates, 3D-Python (a PyPI url= that 404s) and Page-Python (no project URL); redetect still asks whether a distribution of the name exists without asking who owns it (docs/DEFECT_INDEX.md, extractors.six_defects_found_by_review_and_fixtures). A lane printed the GITHUB_TOKEN and GITLAB_TOKEN variables on 2026-10-11: the owner is advised to rotate both, and any step that would use either credential waits on the owner's confirmation. The fixes of the sprint are on integration/cut2c, pull request pending, nothing on main. 2026-10-11 (latest, docs/DECISION_LOG.md): cut 2 and cut 3 are on main since pull request #330 (904aa756), including the issue lifecycle, the bounded batch filing and the issue funnel (TC-ISS-09 to TC-ISS-11, 4de2a682), so the earlier sentence that the sprint fixes are on integration/cut2c with a pull request pending is out of date. Nothing is filed on any Aspose repository; the final issue list awaits the owner (TC-ISS-12 is READY), and the advice to rotate GITHUB_TOKEN and GITLAB_TOKEN stands until the owner confirms. Status stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G6-W02
  status: PENDING
  purpose: "propose.yml as a separately authorized write-capable workflow; exact authorization payload binding candidate hash, source revision, branch, PR intent, policy version, and expiry. Fresh repository-scoped App token minted only inside the effect job; source revision rechecked immediately before the effect; one stable presenter branch and PR per target. Proven first against a disposable target (never a real product repository) per this project's own standing rule and EXECUTION_STATE_MACHINE.md G6's own design. Acceptance: disposable PR created and updated with exact effect evidence; the analysis token cannot write; stale source blocks the effect; repeated invocation creates no duplicate; lost-response simulation reconciles; no default-branch push exists; hosted CI green. 2026-10-01: the write mechanism itself (.github/workflows/propose.yml; core/authorization/proposal.py; components/propose/effect.py; core/github/client.py's new branch/contents/pull-request primitives; cli.py's propose subcommand) landed and is fully tested against injected fakes - zero live GitHub calls anywhere in the suite, full local CI-equivalent green (scripts/ci_check.sh). Mirrors components/issues/file.py's own gated pattern exactly: REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED never inferred from credential presence, a distinct GH_PROPOSAL_WRITE_TOKEN never GH_TOKEN and never reused from GH_METADATA_WRITE_TOKEN/GH_ISSUES_WRITE_TOKEN, idempotent branch/PR creation (a second unchanged invocation writes nothing and opens nothing new), a stale-source recheck immediately before the write, and reconciliation of a lost put_contents response (re-observing the branch's real content) before ever retrying. Status stays PENDING: no disposable/test repository is named anywhere in this project's own records as this item's live-fire target - the identical gap G6-W01's own 2026-10-01 entry recorded for the issue-filing path, and docs/STATE_MACHINE.md section 12.1 requires that first live exercise to be owner-selected, never agent-selected. The disposable-target PR proof (create, update-not-duplicate, stale-source block, lost-response reconciliation, all against a real repository) was therefore not attempted and remains this item's own open resume predicate: an owner names a disposable repository (never a real aspose-*-foss product repository) and confirms the existing GitHub App (GH_APP_ID/GH_APP_PRIVATE_KEY, already provisioned per OWNER-04) is installed on it, then propose.yml is dispatched against it with --readme-file for the first live proof."
- id: G6-W03
  status: PENDING
  purpose: "Qualify any sealed, currently-reproducible candidate from the Cells family first (2026-09-28 owner ruling widened this from Java-only), then expand to the rest of whatever is sealed by Monday. Each repository's first real PR needs its own separate, fresh owner authorization per AGENTS.md's Security and Effects section - a candidate reaching READY_FOR_PROPOSAL never implies publication authorization on its own. Acceptance: a real PR opens against a real product repository's default branch's own PR-target (never the default branch directly), carries the exact candidate content, and is later observed as merged, closed-unmerged, or superseded without this project recreating a duplicate; the owner's authorization for each repository (or batch) is recorded before that repository's effect fires. 2026-09-30 owner ruling: the completion bar for 'live on GitHub' is an actually-merged upstream PR, not merely an opened one - merge timing depends on Aspose's own repository maintainers, entirely outside this project's control, so this item's first real PR should open the moment G6-W02's disposable-target proof is stable, to maximize the review window remaining before Monday, rather than waiting on G5/G7 to finish first."
- id: G7-W06
  status: PENDING
  purpose: "Deploy the scheduled, unattended pipeline in production (EXECUTION_STATE_MACHINE.md G7 Work item 3 - 'scheduled monitor in read-only observation... automatic PR mode... expanding only after observed stability' - written since revision 2 but never given its own work-item id until now, discovered as a real representational gap 2026-09-30 when the owner asked directly whether the state machine represents this requirement). This is the literal act plans/idea.md's Operating Model requires (lines 392-405: 'runs at regular intervals or in response to specific triggers; performs the repository-presentation work described below without routine human intervention... their role will primarily be passive oversight rather than operating the system or initiating its routine work'; lines 409-411: 'Production workloads will run on actual GitHub Actions runners') - owner clarification 2026-09-30, verbatim: 'this app will be actually hosted in GitHub to work autonomously to keep readme files updated across all candidate repos.' Two stages, matching EXECUTION_STATE_MACHINE.md G7 Work item 3's own staging: (1) monitor.yml's schedule: trigger goes live in production in read-only observation mode (no writes) covering every current registry entry, completing at least one real, unattended, cron-fired run (not workflow_dispatch) whose output is compared against accepted local bundles; (2) after that observation period shows stability, propose.yml (G6-W02/W03) is wired so a due or changed sealed candidate is proposed automatically, with zero manual triggering, closing the autonomy loop idea.md describes. Acceptance: a real scheduled Actions run (visible in the repository's own Actions history as schedule-triggered, never manually dispatched) exists and reconciles cleanly against local state; a synthetic upstream change is detected and proposed within one scheduled cycle with no human invoking anything; hosted CI green. 2026-10-11 status: TC-REF-01 is on integration/cut2c (66eae9ad), pull request pending, nothing on main: the monitor classifies an upstream change by what the README consumed (NO_CHANGE, IRRELEVANT_CHANGE, RELEVANT_CHANGE, UNKNOWN, UNREACHABLE), an irrelevant head change leaves a bundle CURRENT and is never selected for reseal, and a zero-provider-call 30-day registry re-check folds only a relevant reading into DRIFTED; monitor.yml is unchanged. The path to hosting is now three ordered cards: TC-REF-10 (every workflow executed locally in its hosted shape), TC-REF-11 (the whole autonomous cycle rehearsed locally on synthetic upstreams, failure modes included) and TC-REF-12 (the staged go-live on GitHub Actions, stage H0 before the owner enables the variables). Stage 1 acceptance (a real cron-fired run) is still not met; status stays PENDING. 2026-10-11 owner decision D5 (docs/DECISION_LOG.md): production sealing runs on a self-hosted runner on the owner machine, which the owner registers for the control repository (OWNER-21); hosted GitHub runners are used only for monitor and publish. This answers TC-REF-10-03's open question and re-scopes TC-REF-12: monitor.yml and the publish workflows stay hosted, sealing-scheduled.yml targets the self-hosted label once the runner is registered, and stage 1 acceptance (a real cron-fired run) is unchanged. Status stays PENDING. 2026-10-11 (latest, docs/DECISION_LOG.md): on main since pull request #330 (904aa756) are TC-REF-01 (the monitor classifies a change by what the README consumed), TC-REF-10 (every workflow run locally in its hosted shape, tools/workflow_rehearsal and the operations runbook), TC-REF-11 (the whole autonomous cycle rehearsed locally on synthetic upstreams) and the hosting preflight with the staged go-live runbook. On integration/cut4 (e407503a, pull request pending) is registry discovery (components/monitor/discovery.py, TC-DIS-01): the drift document gains a discovery section, status prints a registry line, the registry-gaps command lists the unregistered repositories of the authorized organizations, and monitor.yml gains a warn-only last step in its coverage job (46 listed, 44 registered, 1 unregistered and 1 excluded by policy once the JMAP family was admitted). TC-REF-12 (the staged go-live) has not started, and owner decision D5 stands (sealing on a self-hosted runner, OWNER-21 not registered). Stage 1 acceptance (a real cron-fired run reconciled against local state) is still not met; the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G3-W02
  status: PENDING
  purpose: "Freeze acceptance contract v1 after every cohort has sealed against it (moved behind the cohorts 2026-09-05, section 28.12): the 30-point criterion-specific profile with hard disqualifiers, the blocking checks, and the advisory set, each with a version identifier recorded in every bundle's dependencies.json; a candidate built against another version reopens VALIDATING (section 28.5). Concretely: drop CONTRACT_VERSION's \"-draft\" suffix (bundle/seal.py) and give ACCEPTANCE_PROFILE_VERSION a real value; every currently-sealed candidate re-seals against the frozen version in the same work item, not left to trickle in. 2026-10-01 addition, an independent QA review caught this gap: landing the contract freeze is G3's own literal, named exit predicate (EXECUTION_STATE_MACHINE.md G3, \"v1 frozen\") - this work item does not actually close until the formal gate-acceptance step also runs in the same commit, not left for a later session to notice: update evidence/build/G3_PYTHON_COHORT/manifest.json's gate_status to ACCEPTED with current, re-derived counts (not the stale 2026-09-06 snapshot G4's own manifest still carries), append G3_PYTHON_COHORT to project/state.yaml's accepted_gates, and advance current_gate to G4_MULTI_LANGUAGE_COHORTS if G4's own remaining exit predicates (every verifier has a negative control; cohort reports and census in the gate manifest; parity recorded per repository) are also genuinely true by then - re-check each clause directly against current code/evidence, never assumed carried-over from the 20-candidate floor ruling alone (that ruling satisfies G4's own candidate-count clause only, not G3's contract-freeze clause nor G4's other three clauses)."
- id: G7-W04
  status: PENDING
  purpose: "Credential rotation policy and App permission/rotation/rollback review (EXECUTION_STATE_MACHINE.md G7 Work item 1). Document the rotation procedure for GH_APP_PRIVATE_KEY and every other secret in core/secrets.py's SECRET_VARIABLES; confirm the App's registered permission set (metadata:read, contents:write, issues:write, pull_requests:write, administration:write - confirmed 2026-09-30 via tools/github_app/manifest.json) is the minimum actually needed for what's built by Monday, not a speculative superset; document rollback (what happens if a rotated credential breaks a live run - fail closed, per this project's own existing discipline, not silent fallback). Acceptance: a written rotation runbook exists and names every secret; a dry-run rotation (rotate GH_APP_PRIVATE_KEY, confirm the next hosted run still succeeds) is exercised at least once; hosted CI green."
- id: G5-W06
  status: PENDING
  purpose: "Owner-directed 2026-09-30, supersedes OWNER-07's original resume path (docs/DECISION_LOG.md, 2026-09-30). Scan every currently-admitted registry repository (read-only, same discipline as every other fact extraction this project does) for SECURITY.md, CONTRIBUTING.md, and LICENSE; where a genuinely consistent version already exists across enough sibling repositories in the same portfolio to be confident it's Aspose's own standard (not a per-repository accident), that becomes citable evidence - never fabricated, never invented, exactly the same 'never a fabricated public claim' bar every other fact this project cites already meets. LICENSE specifically: docs/PRODUCTION_ROADMAP.md's own WS2 ruling already treats MIT as this portfolio's by-policy standard (NEW-B item) - confirm this holds across the current registry before treating it as settled, don't re-assume it. A repository whose siblings carry no consistent version keeps the existing 2026-09-17 WS2 ruling's own behavior: logged as a missing-file finding via G6-W01's issue-filing path once that lands, never auto-generated from nothing. Acceptance: a discovery report names, per file type, how many of the current registry's repositories already have one, how many share a consistent version, and what that consistent version is (or that none exists); a proposal-generation path exists for a repository missing a file its siblings agree on, gated the same way README candidate content is (deterministic evidence, no LLM fabrication of the file's own substance); hosted CI green."
- id: G3-W04
  status: PENDING
  purpose: "Python cohort, second pass (owner, 2026-09-06 07:45; section 28.12 revision; section 31). The ten dispositioned Python repositories re-run against everything that landed since 03:05, with the two blockers the first pass recorded removed: (1) prompt changes no longer cost a seal - dependency evaluation routes a prompt, template or model-route change to VALID_UPDATE_AVAILABLE (ESM G2 work item 2), so a sealed bundle stays current and counted and its re-seal is G5-W02's; edit the composition prompts the dispositions of BarCode, Email and Note name, with the re-ask and rejection rates measured (27.10); (2) fact coverage: measure the vendored surface reader (G4-W09 facade) against the native Python reader on BarCode, Cells and PDF - public symbols found, and whether each identifier a rejected unit named appears; where the facade finds what the native reader missed, Python reads surface through the facade and parity becomes a recorded measurement. Then every failure class the re-run exposes is fixed in the same iteration it is found (loop-prompt section 6 rule 4 limits mechanism churn, not the number of deterministic fixes with a mutation test each). Yield order: Words, PDF, Cells, Note, Email, BarCode, Font, HTML, TeX, Page. Time box 3 hours from promotion; at the box, seal what passes, dispositions with the new failure class for the rest, accept. Acceptance: second-pass cohort report in the G3 gate manifest; status prints the sealed count; every sealed bundle zero-call proven; no check weakened; hosted CI green."
- id: G6-W05
  status: PENDING
  purpose: "Write-path reviewer findings, remainder (docs/DEFECT_INDEX.md REV-V1-01 to REV-V1-08). Merged and verified on GitHub: REV-V1-01, 02, 04, 08 in #241, REV-V1-03 in #229, REV-V1-06 in #240, the filing half of REV-V1-07 in #237; REV-V1-05 is partial (the App id is attested on the PR only after the first write). Depends on: OWNER-11 for the live proof. Merged: #257 (issue-close gate, filing token provenance; REV-V1-07 FIXED). Open: a pre-write proof that the token is an App token, if GitHub ever exposes one (REV-V1-05). Exit predicate: #257 merged; every REV-V1 entry independently reverified before it leaves the Open section; the disposable-target proof of G6-W02 shows the registry, authorization, token and PR-history gates refuse what they should."
- id: G3-W06
  status: PENDING
  purpose: "README contract enforcement against plans/idea.md (REV-V2-01, 04, 05, 06, 07, 08, 09). Merged: REV-V2-05, 06, 07 in #246 (derived link ceilings, Enterprise anchor, verified badge row), REV-V2-01 and 04 in #251 (no generated edition substitute, BC-06 case-insensitive, BC-12 canonical name). Depends on: #249 (heading case, abbreviations, fences and spacing, visible sections, BC-07 version 8) merged; a typed second-reviewer trigger replaces the hard-coded set (OWNER-15 decided; REV-V2-10). Open: search-intent keyword lineage per title (REV-V2-09), recorded in #249 as a finding and not built; the typed second-reviewer trigger replacing the hard-coded MAJORITY_VOTE_REPOSITORIES (review/independent/review.py:325). Exit predicate: every rule has a negative control; sealed bundles re-check to VALID_UPDATE_AVAILABLE and are never blanket-invalidated; keyword lineage is either built with a check or ruled out by the owner. 2026-10-11 (owner decision D2, docs/DECISION_LOG.md): docs/README_CONTRACT.md is under revision; G3-W10 rewrites it from the survey of the 36 live READMEs, and until that merges no section or blocking check is added to it. Status stays PENDING."
- id: G3-W07
  status: PENDING
  purpose: "Code freeze and portfolio re-seal. Version-bumping changes make every sealed bundle stale: on origin/main 9a862f5b none is independently accepted on current code, 24 of 29 READY_FOR_PROPOSAL bundles carry readme-contract-v1-draft, and 17 sealed READMEs still contain 'commercial edition'. Depends on: #250, #248, #249 merged in that order (#257, #258, #260, #261 and #262 are merged) (each bumps shared version constants and re-derives from main), then no further version-bumping change. Work: compute the pinned version literals from one source so a bump cannot be missed or duplicated; freeze; re-seal the portfolio on the frozen code, preferably through the unattended hosted workflow; OWNER-13 decides whether READY_FOR_PROPOSAL requires an acceptance score. Exit predicate: every READY_FOR_PROPOSAL bundle is current on the frozen code (status --stale reports none); no sealed README contains a forbidden edition name; the contract version is not a draft; independently accepted count and the reason it is not larger are recorded."
- id: G5-W08
  status: PENDING
  purpose: "Seal routing, status counts, durable state and registry coverage (REV-V2-11, REV-V3-04, REV-V3-06, REV-V3-10, REV-V4-10). Merged: REV-V2-11 in #254 (typed invalidation scopes), REV-V3-04 in #243 (seven separated counts), the generic NON_PROCESSABLE producer of REV-V3-06 in #216. Depends on: OWNER-14 (resolved as a per-class deferral registry; the per-class rules are fix/deferral-policy-1007, pending) and OWNER-19 (the two disabled PSD entries). Open: six registry entries with no current candidate (3D-TypeScript, GIS-.NET, PDF-TypeScript, TeX-Python, PSD-.NET, PSD-Python); durable state used only by present (monitor and propose do not use it); three states never assigned to a real candidate. Exit predicate: every registry entry ends in a counted state or a typed disposition with a resume predicate; monitor and propose read and write the durable record; each state is reached by a test and by one real candidate; the DEFER_UNRESOLVED rule the owner chose is enforced by validation, not only by prose."
- id: G5-W09
  status: PENDING
  purpose: "Measured zero-call no-op proof (REV-V3-08). Depends on: #250 merged (it counts the second invocation's provider calls from the ledger, derives fresh_process, retains unconsumed calls and reconciles ledger totals at verify time). Exit predicate: a soft exit, a literal fresh_process or an unreconciled total fails verify-noop-proof; present.yml runs it on a hosted rerun and the run ID is recorded in the gate manifest."
- id: G7-W07
  status: PENDING
  purpose: "Autonomy chain and operations safeguards (REV-V3-01, 02, 07, 09). Merged: REV-V3-01 wiring in #242 (sealing-scheduled.yml), REV-V3-02 in #228 (missing App installation is a notice), the dead-man check for present.yml in #239, propose.yml concurrency in #229. Depends on: OWNER-04 (App on aspose-html-foss), OWNER-12 (gateway outage policy). 2026-10-07 full-history audit (docs/DEFECT_INDEX.md REG-20): the 'it has never run' wording is stale - sealing-scheduled.yml has now run six times (2026-10-05 through 2026-10-07, two schedule-fired, four workflow_dispatch) and never once sealed a repository; the hosted-success half of this item's own open point is tracked, with its exact predicate, as its own item G7-W13 below, not restated here. Open: a schedule-fired monitor run after #228; drift beyond the head SHA (README-content and protected-content drift, bundle-bytes verification - landed since, #274, judged live in the 2026-10-07 audit's own run evidence); concurrency groups on monitor, present and sealing workflows; a cost budget cap beyond the three-repositories-per-run cap; wiring renew_lease (core/state/cas.py:168, no production caller) into long runs; a dead-man check for monitor.yml. Exit predicate: each open point has a test and, for a workflow claim, a run ID on main in the gate manifest."
- id: G4-W18
  status: PENDING
  purpose: "Discovery into src and unused inventory (REV-V3-05, REV-V4-01, REV-V4-10, REV-V3-03). Nothing started. Gate C0 discovery (tools/discovery/portfolio_discovery.py) lists public repositories only, has no observation taxonomy, has no importer under src and is wired to no workflow; FileInventory.community_paths has no reader. Depends on: OWNER-16 (RegistryRevisionV1 and the PR_ELIGIBLE and PORTFOLIO_* names: retire them in plans/idea.md or implement). Exit predicate: discovery runs through the official entry point and a workflow with new repositories disabled and read-only; community_paths is consumed or removed; the OWNER-16 ruling is recorded before the code it governs."
- id: G4-W19
  status: PENDING
  purpose: "Product-evidence surfaces, priority 2 (REV-V4-02, REV-V4-03). Nothing started: no GitHub Releases audit, no GitHub-generated statistics observation, no product-agent ingest contract (ProductFactsV2), no visual assets or social preview. Depends on: OWNER-17 (scope; visuals are deferrable by plans/idea.md). Exit predicate: each surface the owner admits has a read-only observation with a typed record in facts.json and a test; each deferred surface is recorded as deferred with its reason."
- id: G7-W08
  status: PENDING
  purpose: "Hygiene and prompt registry governance (REV-V4-04, REV-V4-05, REV-V4-06, REV-V4-07). Merged in #235: REV-V4-06, REV-V4-07 (docs paths) and the dated test debt and Go and .NET negative controls of REV-V4-05. Depends on: G3-W07 (the three stale-bundle entries clear only on re-seal). Open: Java and TypeScript negative controls; prompt owner and dependency-hash fields and an inline-prompt scan (REV-V4-04, a prompt-manifest schema change through a named item). Exit predicate: each open point has a test; the prompt-manifest schema changes only through this item with a section 31 entry."
- id: G7-W09
  status: PENDING
  purpose: "Documentation and cursor claim corrections (REV-V4-09, REV-V2-02 documentation half). The register PR corrected the plan's stale scorer row. Still stale: project/state.yaml G3-W02 text (line 111) and the G5-W04, G5-W05 and G7-W05 claims REV-V4-09 names, which only the cursor owner edits, and the plans/idea.md body naming data/products.json (OWNER-18). Depends on: OWNER-10 (push policy, cursor says NEVER while AGENTS.md permits a push after ci_check), OWNER-18. Exit predicate: no document claims the scorer is absent or a gate is accepted that is not; the cursor and AGENTS.md agree on the control-repository push policy; tests/test_register_integrity.py stays green."
- id: G7-W10
  status: PENDING
  purpose: "Cursor-staleness guard (2026-10-07 four-reviewer finding, re-verified directly: updated_at was still 2026-10-05T10:45:00+05:00 at this session's start, 2d380177/#281 and every merge since #271 landed with no refresh - a recurring process defect, not a one-time slip). Depends on: none. Add a lightweight test under tests/ that fails when project/state.yaml's updated_at is older than the most recent merge commit touching src/ by more than N days (N=3 proposed, tunable); this register PR's own updated_at bump is the first proof the check would currently pass. Exit predicate: the test exists, fails on a synthetic stale fixture, passes on the live cursor; AGENTS.md's 'update the cursor in the same commit' rule has a mechanical backstop instead of relying on a session noticing."
- id: G7-W11
  status: PENDING
  purpose: "Sealing-loop failure memory (2026-10-07 four-reviewer finding): a candidate that fails sealing is retried identically on the next scheduled pass with no recorded history of the prior failure's cause, so a genuinely stuck candidate (e.g. an unresolved upstream defect) burns a fresh attempt every cycle rather than backing off or surfacing as a repeat. 2026-10-07 correction (full-history audit): the fix this item describes has since landed for real - PR #285 (feat/sealing-failure-memory-1009, merged 2026-10-07T12:34:06Z), adding core/sealing_plan.py's SealingAttempt/cooldown mechanism with its own unit tests. Status stays PENDING, not COMPLETE: #285 merged after every sealing-scheduled.yml run this audit found (the last was 2026-10-07T11:57 UTC, headSha 169ab46a, before #285), so no hosted run has yet exercised this mechanism live - that hosted proof is G7-W13's own exit predicate, not restated here. Depends on: nothing further in code - only a hosted run after #285. Exit predicate: a repeated-failure record exists per candidate (cause, count, last-attempt revision) - met by #285's own tests; a hosted sealing-scheduled.yml run after #285 shows a previously-failing repository actually skipped by cooldown (or, if none is within cooldown, that the mechanism is at least live and silent) - not yet observed."
- id: G7-W12
  status: PENDING
  purpose: "Cells-Go UNCLASSIFIED deferral gap (2026-10-07 four-reviewer finding): validation/deferrals.py's UNCLASSIFIED fallback (no registered class matches the cause) fires on aspose-cells-foss' Go candidate with no class yet registered for its real cause. Depends on: a root-cause investigation was named as already in flight on this; re-checked this session and no branch, worktree or open PR matching the description was found - this item registers the gap, stated as unconfirmed cause, without asserting a cause itself. Exit predicate: a named cause, a registered DEFERRAL_CLASSES entry (or an explicit BLOCK ruling) covering it, and a test against the Go candidate's real finding. 2026-10-07 full-history audit: re-confirmed reproducing live, unchanged, in hosted run 37461500634 (aspose-cells-foss/Aspose.Cells-FOSS-for-Go leg) - 'BC-05 failed at EXTRACTING: inherited_unit:063.paragraph is deferred as UNCLASSIFIED'. Not fixed by this PR."
- id: G7-W13
  status: PENDING
  purpose: "Unattended sealing hosted proof. The production promise of autonomous unattended sealing (AGENTS.md Mission; plans/idea.md Operating Model) has zero confirmed end-to-end successes: every run of sealing-scheduled.yml since #242 wired it - six total, 2026-10-05 through 2026-10-07, run ids 37310360790, 37348251358, 37361313253, 37411705333, 37461500634, 37617610823 - either failed closed at the plan stage (a missing/malformed drift contract, pre-#267/#270; a newly-enabled owner, aspose-psd-foss, with no drift evidence yet, #282/#284) or failed at present for every one of the three repositories it planned (aspose-cells-foss/Go, aspose-note-foss/Python, aspose-pdf-foss/Go), nine present-stage failures in all, no two for the same reason: BC-10 REJECT_PRESENTATION, a hallucinated fact_id in source_reconciliation, an input/output format contradiction, two separate uncited-unit rejections (class fixed by #286), two separate coherence-drop rejections (class fixed by #289), and the BC-05 UNCLASSIFIED deferral G7-W12 tracks (still open). Every content-authoring fix this audit could find (#285, #286, #287, #289, #290) merged to main on 2026-10-07 AFTER the last of the six runs (11:57 UTC, headSha 169ab46a) - none has yet been exercised by a hosted sealing-scheduled.yml run. core/sealing_plan.py selects only DRIFTED registry entries, by design (Gate B, plans/idea.md: 'reopen only drifted repositories'); this is not itself a defect to fix by widening to every enabled repository (that would contradict the invalidation discipline AGENTS.md and G2 already require), but it does mean the only repositories currently eligible for a scheduled run are these same three hard cases plus whichever next owner's enablement races the monitor's six-hour cadence (REG-20) - no easy-win repository is available to prove the loop until one of them clears or a different repository drifts. Depends on: none - this is a verification gap, not a code gap, for every cause this audit could classify. Exit predicate: unambiguous and checkable, per AGENTS.md's own production-shaped-proof discipline - at least one scheduled or manually-dispatched sealing-scheduled.yml run, on an unmodified frozen main, completes present through to READY_FOR_PROPOSAL (or the no-op-proven/accepted funnel stage) for at least one repository, with the run id and repository recorded as evidence here. A merged fix alone never satisfies this. 2026-10-08 update (hosted-sealing durability audit): SATISFIED. Hosted run 37712681751 (dispatched on main after #285-#291 merged) carried aspose-cells-foss/Aspose.Cells-FOSS-for-Go through present --durable-state to READY_FOR_PROPOSAL, review ACCEPT with zero findings, and a genuine fresh-process no-op proof (zero provider calls, byte-identical) - durable-state transaction id f7ac3f73da1b4c7090ed11f26e8bb267, sealed candidate-revision hash 99c789e9175f2b12ad82bafeeba148ddcc1367fb (both confirmed directly: the former from the durable-state ref refs/repository-presenter-state/records/aspose-cells-foss__Aspose.Cells-FOSS-for-Go's own record.json, state_version 24; the latter from the run's own downloaded sealed-aspose-cells-foss__Aspose.Cells-FOSS-for-Go workflow artifact). The run id and repository are recorded here as the predicate's own required evidence. The portfolio-currency question this success does NOT answer - does a hosted success alone keep the committed candidates/ bundle current - is split out as its own item, G7-W14, never folded back into this item's own acceptance. 2026-10-11 (owner decision D5, docs/DECISION_LOG.md): production sealing now targets a self-hosted runner on the owner machine (OWNER-21); the 2026-10-08 hosted proof stands as the proof that the pipeline works on a hosted runner and is not repeated for the self-hosted label by this item, which G7-W06 re-scopes."
- id: G6-W06
  status: PENDING
  purpose: "Write-scope expansion gate (EXECUTION_STATE_MACHINE.md G6 Work item 4, principle 25). core/registry/write_gate.py's require_write_permitted (actual path: src/repository_presenter/core/registry/write_gate.py) refuses any write effect unless the registry entry is listed, active and mode full; propose.yml's write job additionally requires REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED=1, a GH_PROPOSAL_WRITE_TOKEN, and a merged ops/proposal-authorizations/<repo>__<hash>.json record (core/authorization/proposal.py) whose bound fields (repository, candidate_hash, source_revision, branch, policy_version, window) are rechecked against the live candidate and a freshly rechecked source revision before any write. Flipping registry.json's mode field alone grants none of this and must never be done by an agent unilaterally. Depends on: OWNER-20. Exit predicate: for EACH repository moved from dry_run to full - (a) the owner's explicit per-repository authorization is recorded in docs/DECISION_LOG.md with a date; (b) a committed authorization record exists under ops/proposal-authorizations/ for that repository; (c) that repository's candidate is current-code reproducible, independently accepted, and no-op-proven (not stale, not VALID_UPDATE_AVAILABLE) at the time of the mode change. All three, every time - never a blanket 'make every entry full'."
- id: G7-W14
  status: PENDING
  purpose: "Hosted portfolio-currency durability (2026-10-08 hosted-sealing durability audit): open. G7-W13's success is ephemeral beyond its durable-state ref receipt - present.yml exports the sealed bundle only as a 7-day-retention workflow artifact (sealed-<owner>__<name>) and commits nothing; confirmed directly (git ls-remote origin: no branch, no PR, no commit anywhere carries this run's candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Go/ bundle - only the small state-ref receipt exists) and by reading present.yml, propose.yml and sealing-scheduled.yml source end to end: no step in any of the three ever runs git commit or git push against this control repository's own candidates/ tree, for any registry mode, dry_run or full alike (propose.yml's own header: candidate_artifact 'replaces candidates/<slug> on each job's checkout wholesale', never the committed CURRENT). The committed candidates/<slug>/ tree repository-presenter status reads is refreshed today only by a human or agent session opening a PR by hand (the pattern used for aspose-font-foss/Aspose.Font-FOSS-for-Python, #259); this is not documented anywhere as an intentional design choice (docs/STATE_MACHINE.md, docs/EXECUTION_STATE_MACHINE.md and AGENTS.md are all silent on it), so it is registered as an open gap, not an accepted gap. Depends on: an owner ruling on which of two resolutions applies - (a) a new mechanism (e.g. a present.yml or sealing-scheduled.yml step that commits the sealed candidates/<slug> bundle to a review branch and opens a PR against this control repository automatically, gated by the same owner pause/authorization variables sealing-scheduled.yml already reads) is built and proven hosted; or (b) the owner rules dry_run (and/or full) entries must never auto-commit by design and a human/agent step stays required, recorded as a dated decision in docs/DECISION_LOG.md, not left implicit. Exit predicate: either an observed hosted run whose own commit or PR (authored by the workflow, not an agent session) updates this repository's committed candidates/<slug>/ bundle for at least one dry_run entry, with the run ID and the commit/PR it produced recorded as evidence; or a dated owner decision in docs/DECISION_LOG.md stating plainly that this gap is accepted by design, after which this item is OWNER status instead. 2026-10-09 update (owner chose 'build it', not 'accept by design'): the mechanism is built, still PENDING, not SATISFIED - a new components/candidates_publish/effect.py (git_ops.py's real git plumbing plus the existing core/github/client.py PR functions reused unmodified, pointed at this repository instead of an external target), a new candidates-publish.yml reusable workflow (workflow_dispatch and workflow_call, a read-only plan job plus a write job gated on REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED, a distinct GH_CANDIDATES_WRITE_TOKEN, and the new core/github/token_provenance.py::verify_repository_token), and a new publish-candidates job in sealing-scheduled.yml (matrix over every planned repository, dry_run and full alike, never only the full-mode subset propose uses). Idempotent by construction, proven against a real disposable local git repository (tests/components/candidates_publish/test_git_ops.py), not only fakes. Full reasoning in docs/DECISION_LOG.md, 2026-10-09. Deliberately NOT exercised hosted this session: this session's own task explicitly warned that a parallel agent was reseal-ing the exact candidates/ path this mechanism writes to, and the only way to produce this predicate's required hosted evidence is to run the mechanism for real against some repository's candidates/<slug> tree - exercising it this session risked exactly that collision, so no dispatch of sealing-scheduled.yml or candidates-publish.yml was made and candidates/ was not touched. Resume predicate: once the parallel reseal work is clear of candidates/, dispatch either workflow with the owner variable set, observe a real commit and PR, and record the run id and PR here and in docs/EXECUTION_STATE_MACHINE.md's own exit-predicate bullet - only then does this item's status change. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G7-W15
  status: PENDING
  purpose: "Third-sighted must-carry packet-bundling gap in section_authoring (S6), settled priority per AGENTS.md's three-sighting rule. Live evidence, read directly from the stored transaction (not taken on a report's word alone): aspose-slides-foss/Aspose.Slides-FOSS-for-Java, revision 620a2614418854b4a18966a361e6907ddc88c7cb, call ba6a89dbe1f2 (runs/transactions/.../calls/ba6a89dbe1f2.rejected-1.json, .rejected-2.json, calls.jsonl) fails closed on both attempts, each rejected for the identical five must-carry superseded units in one packet across three sections - inherited_unit:081.paragraph, 083.paragraph, 085.paragraph (scope_limitations), 089.paragraph (enterprise_relationship), 095.paragraph (development_testing) - with #281, #286, #287, #289 and #290 already on main. Widens docs/DEFECT_INDEX.md's composition.authoring.superseded_unit_not_carried entry (prior sightings: the original 092-094; the 084 2026-10-07 sighting, fixed by #289) to a third occurrence on this exact repository, surviving every landed fix - meaning the fix pattern so far (granting a section's citable set the must-carry ids; re-asking with substance) does not cover a packet bundling many cross-section obligations into one call. A secondary, unresolved discrepancy found in the same evidence: attempt 2's raw output did add all five units to an omitted array with reasons, yet the logged rejection (calls.jsonl, outcome: response_invalid) is byte-identical to attempt 1's, naming the same five as still missing - either the object actually validated differed from what rejected-2.json's content field shows, or a stricter check than the inspected carried_unit_errors (composition/authoring.py:1971) fired; not yet explained. Likely direction, not implemented: the S6 packet may need a smaller-batch or per-section re-ask for must-carry obligations (in the spirit of reconciliation_batches' own fixed-size-batch precedent), but this needs its own investigation - it is not the same mechanism as the separate, still in-flight oversized-list-split fix for extraction-time list sizing, and must not be copy-pasted from it. Depends on: none - this is a live-draw defect, not blocked on any owner decision. Exit predicate: a root cause for both the packet-bundling failure and the attempt-2 omitted/rejection discrepancy, a scoped fix (batching or another mechanism) with a mutation test reproducing this exact five-unit/three-section shape, and a fresh live draw of this exact repository/revision clearing S6 without exhausting the reask budget."
- id: G7-W16
  status: PENDING
  purpose: "Coherence-revision silent public_symbol-citation drop in section_authoring/coherence (S8), docs/DEFECT_INDEX.md's composition.coherence.cited_symbol_silent_drop (single sighting, aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript, 2026-10-08). The existing coherence_content_loss_errors check (G3-W05, built for the inherited-Mermaid-diagram shape) correctly fires on a different content shape: scope_limitations/limitation:2's coherence revision drops all four previously-cited public_symbol:workbook.to{csv,html,json,markdown} fact_ids with none of their own prose text (e.g. Workbook.toCsv) surviving in the revised sentence, and a targeted_repair round restores the fact_ids without restoring the prose, so the job fails closed on both attempts rather than silently losing the citations. The check itself is proven working, twice; what stays open is upstream - why the coherence-revision model step drops cited prose content in the first place, which neither this entry nor inherited_diagram_content_loss has root-caused. Depends on: none yet named - a second independent sighting (same or a different repository) would cross AGENTS.md's three-sighting threshold with one more, or a root-cause investigation can proceed without waiting on one. Exit predicate: either a second independent sighting of this exact shape, corroborating the pattern per AGENTS.md's rule, or a root-cause fix for why S8 coherence's revision step drops cited prose content, with a mutation test reproducing this exact shape and a fresh live draw of this repository/revision clearing S8 without the finding recurring."
- id: G7-W20
  status: PENDING
  purpose: "Acceptance profile ratification (closes OWNER-13; REV-V2-02, REV-V4-08, REG-03). Owner decision 2026-10-09, confirming the 2026-10-06 weights table and sub-decisions: ratify now. review/acceptance/profile.py gains integer points on all 26 criteria summing to TOTAL_POINTS 30 - C01, C02, C21 and C24 weigh 2, every other criterion weighs 1 - and RATIFIED becomes True with ACCEPTANCE_PROFILE_VERSION bumped, in one reviewed change that records the decision in docs/DECISION_LOG.md. Standing sub-decisions: a not-applicable criterion (no notices file, no examples, no H1) is credited as met; a banner link to an Aspose destination above the opening paragraph fails C01 (strict reading); D14 (mechanical template filling) is evaluated by the deterministic checker landed in #279 rather than left unevaluated. The ratified score feeds the funnel publication-eligible count (a candidate counts only at 30/30 with zero disqualifiers triggered); whether it also gates READY_FOR_PROPOSAL stays an explicit documented choice, never implicit, and the change must not silently reset the current-code-reproducible count - measure repository-presenter status before and after, and stop and report if the version bump alone stales sealed bundles. Regression across every sealed bundle: re-score all 30 and record the distribution (how many reach 30/30, which criteria fail most) in docs/DECISION_LOG.md. Depends on: none, the owner decision is made (OWNER-13). Exit predicate: RATIFIED is True with every points value set and summing to 30; a test shows a below-30 candidate is not publication-eligible and a 30/30 one is; docs that say unratified or advisory are corrected; the before and after status counts and the 30-bundle score distribution are recorded."
- id: G7-W22
  status: PENDING
  purpose: "Candidate currency freeze and re-seal batching policy (breaks the enhance, invalidate, re-seal loop; owner directive 2026-10-10). Policy, effective when this entry merges: (1) One cut. The in-flight batch (G7-W20 profile ratification, the S6 must-carry fix G7-W15 and G7-W18, the G7-W12 UNCLASSIFIED deferral fix, the candidates-publish CI fix) lands together; after it lands there is exactly one portfolio re-seal. (2) After the cut, no governed-version bump (NORMALISATION_VERSION, REVIEWER_LOGIC_VERSION, RENDERER_VERSION, VALIDATOR_VERSION, per-check versions, CONTRACT_VERSION, ACCEPTANCE_PROFILE_VERSION) until the first push wave completes, unless the change fixes a safety or factual-accuracy defect (an unsupported public claim, a leaked secret, a wrong authorization) or the owner approves it. (3) A non-blocking defect found after the cut is logged in docs/DEFECT_INDEX.md with evidence and left unfixed; the three-sighting settled-priority rule is deferred until the first push wave completes, except for safety or factual-accuracy defects. (4) AGENTS.md already forbids blanket invalidation: a candidate is invalidated only through an input it consumed, and validator or reviewer changes re-check and may yield VALID_UPDATE_AVAILABLE. A measurement agent reports what each recent version bump actually cost (which bundles failed re-verification, which only went stale) and proposes a change so a stale-but-intact READY_FOR_PROPOSAL bundle is reported separately from a re-sealed one; no invalidation or counting behavior changes until the owner has seen that report. Depends on: none (policy); the in-flight batch it names. Exit predicate: the cut is recorded with the commit it names; the portfolio re-seal runs once after it; the status counts before and after are recorded; the measurement report and its proposal are recorded; any post-cut version bump names the safety or owner-approval ground. 2026-10-11 status (docs/DECISION_LOG.md, this date): the cut was declared by the TC-CUT-02 rule, the slice in on a 0 against 0 authorizable tie; cut 1 is 013aa79e and cut 2 is the one second release, each governed constant moved once for it (EXTRACTOR_VERSION 2, RENDERER_VERSION 31, NORMALISATION_VERSION 33, VALIDATOR_VERSION 20, BC-05 5, INHERITED_UNITS_VERSION 4, REVIEWER_LOGIC_VERSION 19) on the ground of factual accuracy and the owner's 2026-10-10 plan-review answers. Cut 2 is on integration/cut2c (f69f75c7), pull request pending (consolidated pull request #329), nothing on main. Status counts so far: wave 1 on cut 1 sealed 1 of 36, the cut-2 sample sealed 1 of 23, wave 3 on f69f75c7 is in progress and no count is claimed. The measurement report is recorded (docs/investigations/13-bump-cost-and-recheck-design.md) and its first slice is implemented under G7-W25; the owner's approval of the counting change is not recorded, and the portfolio re-seal has not completed, so the exit predicate is not met and the item stays PENDING. 2026-10-11 (later): correction to the cut 2 sentence above: pull request 329 merged into main as 862625bf and carries cut 1 (013aa79e) only; cut 2 (f69f75c7) is not on main and is part of integration/cut3 (a3b6bbf6), which moves each governed constant once more for cut 3: NORMALISATION_VERSION 34, VALIDATOR_VERSION 21, BC-02 5, BC-04 4, BC-05 6, BC-14 2, RENDERER_VERSION 32, EXTRACTOR_VERSION 3 (REVIEWER_LOGIC_VERSION 19 and INHERITED_UNITS_VERSION 4 unchanged), on the factual-accuracy ground of clause 2. The structure gates (G3-W10, TC-STD-04) and the idempotence fix (G3-W11, TC-IDM-02) are governed changes for a declared later cut on the owner D2 and D1 grounds, not cut 3. The counts the exit predicate records are authorizable (D4) as well as sealed. 2026-10-11 (latest, docs/DECISION_LOG.md): pull request #330 merged cut 2 and cut 3 into main (904aa756, hosted CI green on the exact head and on main), so the correction above that put cut 2 only on integration/cut3 is itself out of date: main carries cut 1 (013aa79e, via #329), cut 2 (f69f75c7) and cut 3 (NORMALISATION_VERSION 34, VALIDATOR_VERSION 21, BC-02 5, BC-04 4, BC-05 6, BC-14 2, RENDERER_VERSION 32, EXTRACTOR_VERSION 3). Cut 4 is declared on the factual-accuracy ground of clause 2 and the owner's README-standard rulings R1 to R7, and sits on integration/cut4 (e407503a, pull request pending): NORMALISATION_VERSION 35, VALIDATOR_VERSION 22 with BC-03 3, BC-04 5, BC-05 7, BC-07 11, BC-12 2 and BC-14 3, RENDERER_VERSION 33, REVIEWER_LOGIC_VERSION 20 and EXTRACTOR_VERSION 4, each moved once; the later wave-4 repairs ride those constants without a further bump because cut 4 is unreleased. Counts so far, authorizable (D4) beside sealed: authorizable 0 of 44; wave 1 sealed 1 of 36, the cut-2 sample 1 of 23, wave 3 sealed 8 of 36 (0 of the 8 authorizable on the acceptance review), wave 4 sealed 4 of 44; wave 5 is running on e407503a and no count is claimed. The portfolio reseal has not completed and the owner's approval of the counting change is not recorded, so the exit predicate is not met and the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G7-W23
  status: PENDING
  purpose: "S6 dotted file name in prose: an authored unit that spells a repository file name or path the upstream README itself names (CONTRIBUTING.md, SECURITY.md, basic.rs, examples_test.go, main.go) was refused by authoring.unit_checks ('identifiers that are not accepted fact values') because no fact recorded the file, although the pinned tree contains it. Live, the 2026-10-09 re-seal transactions: aspose-slides-foss/Aspose.Slides-FOSS-for-.NET (revision 86c441b5, CONTRIBUTING.md and SECURITY.md on both S6 attempts, sighted again in the G7-W12 live run of 2026-10-10), aspose-cells-foss/Aspose.Cells-FOSS-for-Rust (thirteen samples/*.rs names), aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (examples_test.go, main.go); aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript's AGENTS.md is the case-difference sibling (the tree holds agents.md). Fixed at the extractor, not the rule: evidence/facts/repository_files.py checks every file-like token an inherited unit spells against the pinned tree inventory (exact and case-sensitive, a path must match on a directory boundary, a URL contributes nothing) and the inherited_unit fact records the hits in attributes['repository_files']; composition/authoring.py::allowed_identifiers, the one set the guard, the renderer's code spans and BC-04 share, admits those names from SUPPORTED facts. A name the tree lacks, an invented name, a name differing in case and a CONTRADICTED fact's record all stay refused. INHERITED_UNITS_VERSION 2 to 3 and NORMALISATION_VERSION 31 to 32; no other governed constant moves. Mutation-tested: tests/components/readme/evidence/facts/test_repository_files.py (the real strings, plus an invented name, a name only in the README, a case difference, a directory-boundary miss, a climbing path), test_extract.py (the tree reaches the units end to end) and tests/components/readme/composition/test_authoring.py (the real Slides-.NET sentence passes with the record, fails without it). One more narrow admission rides the same NORMALISATION_VERSION bump: a cited inherited unit's own sibling shorthand (`EciHelper.normalize`/`.validate`) also spells EciHelper.validate (BarCode-Python), tested with the real paragraph and negative controls. Classified and deliberately not fixed here: a standard-library type inferred from a symbol name with no evidence in any cited fact (ArrayList beside ArrayListAdapter, 3D-Java) stays refused - it is an unevidenced claim, not an extraction gap; a file name that is external knowledge, not in the tree (winmail.dat, Email-.NET) stays refused and the re-ask drops it; a snake_case field or enum member the source defines but the surface extractor never records (allow_check_digit_input, eci_assignment_number, gs1_enabled, ValidationType.List) is a surface-extraction gap with a wide blast radius, logged in docs/DEFECT_INDEX.md as its own mechanism; a case variant (AGENTS.md against agents.md), a test package (coverlet.collector), standard-library modules, enum members of a foreign type and XML elements are other classes. Depends on: none - a scoped extraction and allowed-set change, not blocked on any owner decision. Exit predicate: a root cause naming the real rejected strings and their classification (met), the extractor record with tests from those strings and negative controls for an invented name, a name only in the README text, a case difference and a directory-boundary miss (met), and a fresh qwen3-next-only live draw of aspose-slides-foss/Aspose.Slides-FOSS-for-.NET clearing the S6 unit check without the CONTRIBUTING.md and SECURITY.md rejection (the observed result is in this item's owner note)."
- id: G3-W08
  status: PENDING
  purpose: "Candidate content gate and coverage (Track C-1 and C-2 of plans/archive/reseal-and-refresh/PLAN.md section 10; owner plan review 2026-10-10). Four reviews of the 30 sealed candidates against the live upstream READMEs found none pushable: a returned REJECT is demoted to ACCEPT by deterministic fold code, valuable verified content is dropped as redundant or unsupported, version and publication claims lack a supporting fact, and the clones hold information (docs/*.md, changelog, community files, CLI entry points, framework matrices) that no fact kind carries. Scope: TC-COV-01, the read-only coverage inventory of clone information (may start now, no src/ change); the cut-1 slice TC-REV-01, TC-CLM-01 and a thin TC-COV-02, only if each is green and merged by Sunday 2026-10-11 22:00 (the TC-CUT-02 go/no-go); and the second-cut cards TC-DSP-01, TC-DSP-02, TC-COV-02, TC-COV-03, TC-EXT-01, TC-BND-01, TC-CTR-01, TC-VER-01 and TC-VER-02, which land only after wave 1's reseal so that reseal runs on one fixed code. Every governed card names its G7-W22 ground (factual accuracy) and rests on the owner's recorded 2026-10-10 plan-review answers (TC-R2-00, docs/DECISION_LOG.md 2026-10-10); each governed constant moves exactly once per cut. Depends on: G7-W22 (the cut is declared first; this item is the post-cut change vehicle) and G7-W20. Exit predicate: the coverage inventory is recorded for all 36 registry entries; a returned reviewer REJECT stands unless it carries a recorded deterministic refutation, proven by replaying the sealed review.json files; disposition-truth, live-README-floor and claim-support checks reject the negative controls drawn from the four reviews; new fact kinds and their placement inside the 10-section template land with fixtures from real repositories and never as mechanical template filling; the known extractor defects have failing-then-passing fixtures; each governed constant moves once per cut with tests/test_version_bump_discipline.py green; the second portfolio reseal (TC-R2-02) is recorded with counts before and after. 2026-10-11 status: cut 1 (013aa79e) landed TC-REV-01 (a returned REJECT stands unless deterministically refuted), TC-CLM-01 (package:published_version and BC-14) and TC-DSP-01 with its BC-05 advisory class. Cut 2 is on integration/cut2c (f69f75c7), pull request pending, nothing on main: six extractor defects found from real fixtures (TC-EXT-01), lossy renderer output, a lead-in carried with its payload and a kept list stating every item, five model-output rejection classes repaired at their earliest stage, the BC-05 notices and own-licence, dependency and install-snippet deferral classes, the independent_review v12 and section_authoring v20 prompts, and the NuGet source-URL fix; the defect classes and their status are in docs/DEFECT_INDEX.md (sprint 2026-10-11). The registry ownership rule is kept (docs/DECISION_LOG.md, this date). Waves so far: cut 1 sealed 1 of 36, the cut-2 sample 1 of 23, wave 3 in progress. TC-COV-02, TC-COV-03, TC-BND-01, TC-CTR-01, TC-VER-01 and TC-VER-02 are not claimed by this note, and the second portfolio reseal is not recorded with counts before and after, so the exit predicate is not met and the item stays PENDING. 2026-10-11 (later, docs/DECISION_LOG.md): pull request 329 merged into main as 862625bf and carries cut 1 (013aa79e) only; cut 2 (f69f75c7) and the cut-3 lane work are on integration/cut3 (a3b6bbf6), no pull request yet, with one bump per governed constant for cut 3 (NORMALISATION_VERSION 34, VALIDATOR_VERSION 21, BC-02 5, BC-04 4, BC-05 6, BC-14 2, RENDERER_VERSION 32, EXTRACTOR_VERSION 3). Wave 3 (f69f75c7) is allowed to finish (owner decision D3) and its counts are appended to the log when it ends. Progress is now counted in authorizable candidates (D4), so the sealed counts above are reported beside it, not as progress. The README standard that the second-cut content cards (TC-DSP-02, TC-COV-03, TC-CTR-01) implement is under revision (G3-W10, D2): their README_CONTRACT.md edits wait for the rewrite. The item stays PENDING. 2026-10-11 (latest, docs/DECISION_LOG.md): main carries cut 1, cut 2 and cut 3 since pull request #330 (904aa756, hosted CI green on the exact head and on main), so the earlier phrases that cut 2 is on integration/cut2c with a pull request pending, and that cut 2 and the cut-3 lane work are on integration/cut3 with no pull request yet, are out of date. On main (cut 2 and cut 3): the extractor, rejection-class, BC-05, reviewer-prompt and consumed-scope repairs of cut 2, and for cut 3 the TC-COV-02 command and CI facts, the TC-API-01 and audience guards and the LST-01 list check, under NORMALISATION_VERSION 34, VALIDATOR_VERSION 21 (BC-02 5, BC-04 4, BC-05 6, BC-14 2), RENDERER_VERSION 32 and EXTRACTOR_VERSION 3. On integration/cut4 (e407503a, pull request pending, nothing of it on main): the cut-4 constants (NORMALISATION_VERSION 35, VALIDATOR_VERSION 22 with BC-03 3, BC-04 5, BC-05 7, BC-07 11, BC-12 2 and BC-14 3, RENDERER_VERSION 33, REVIEWER_LOGIC_VERSION 20, EXTRACTOR_VERSION 4), the wave-3 universal fixes (the re-ask names every violation, preserve-first placement and the C++ renderer, TypeScript members, silent deferrals, moved tables, printed usings, text hygiene), the horizontal render-verified At a Glance diagram, the JMAP admission, the Node.js plugin, the Development and Testing renderer repairs (TC-COV-02, a6183ec5) and the three wave-4 repairs (TC-Q1-01 list items judged by content, TC-Q2-01 S4 destinations, TC-Q3-01 refuted name denials), which ride the cut-4 constants. Measured: wave 3 (f69f75c7) sealed 8 of 36 and the acceptance review judged 0 of the 8 authorizable; wave 4 (8c48f4d2) sealed 4 of 44 and its triage found the stricter gates correct (5 of the 8 wave-3 seals carried true defects) with 8 regressions, 7 of which the wave-4 repairs address (docs/DEFECT_INDEX.md REG-26 keeps the JMAP-Cpp hygiene-cap case open); wave 5 is running on e407503a and no count is claimed. The second portfolio reseal is not recorded with counts before and after, so the exit predicate is not met and the item stays PENDING. Cards: TC-ADM-01, TC-NOD-01, TC-Q1-01, TC-Q2-01, TC-Q3-01. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G6-W07
  status: PENDING
  purpose: "Issue-system operations (Track B of plans/archive/reseal-and-refresh/PLAN.md section 9; owner plan review 2026-10-10): make the landed harvest and issue-readiness tooling (G6-W01, #314) produce filed, tracked upstream issues. Of the 15 CONFIRMED handoffs only 3 pass the automatic recheck (the redetector is PyPI-only, registered gap issues.redetect_only_pypi_and_unparseable), only BC-02 is auto-drafted, and filing needs registry mode full, which also arms pull-request eligibility. Scope: redetector registry per package registry (npm, NuGet, Maven Central, crates.io, Go proxy) and NOT_PROCESSABLE re-detection beyond .py; a detector class registry for the defect classes the reviews found (license, build, unparseable source, own example, metadata placeholder) instead of an if/elif chain; an issue-body quality gate and templates; decoupling issue filing from pull-request mode through an issues_mode field (off, dry_run, file) on registry entries with a back-compatible default derived from mode; per-organization issues:write proof for the GitHub App without any token value in a log or artifact; safeguards and visibility. Two additive schema changes are admitted by this item (docs/DECISION_LOG.md 2026-10-10): the issues_mode field on registry entries and a defect_class field on the upstream-defect handoff schema; they change only through this item, landed with their code and tests. Depends on: G6-W01 (harvest and issue-readiness landed) and G6-W06 (registry mode full stays owner-gated); no governed-version file is touched, so G7-W22 does not constrain it. Exit predicate: each registry has a redetector with a resolved-versus-persists test pair and the issue-readiness replay_gap count falls to the genuinely unreplayable, measured before and after; each defect class has a detector, a redetector, a template and a negative control; no issue passes the body-quality gate unless its deterministic checks pass; a negative control shows issues_mode file with mode dry_run files issues while propose is refused; per-organization issues:write proof is recorded or a BLOCKED_EXTERNAL record names the owner action; at least one owner-approved issue is filed and tracked, or the approval list is submitted and the item records BLOCKED_EXTERNAL. No outbound issue, comment or label is written without the owner's approval of the exact list. 2026-10-11 status: no G6-W07 code has landed on the sprint branches. The registry-ownership decision (docs/DECISION_LOG.md, this date) puts the 3D-Python and Page-Python PyPI ownership defects (a dead url=; absent project URLs) on this item's issue list as drafts, and the redetector for each registry must read ownership: the NuGet adapter now reads the catalog leaf's repository url (f69f75c7, on integration/cut2c, pull request pending), the PyPI rule is unchanged. Nothing is filed and no schema change is made. 2026-10-11 (latest, docs/DECISION_LOG.md): correction to the status above, which said no G6-W07 code had landed. On main since cut 1, cut 2 and cut 3 (pull requests #329 and #330) are the issues_mode field on registry entries (c25242e5, TC-ISS-05), the defect-class registry with its deterministic detectors for licence, manifest and README defects, wired into every present run (4617ba33 and 2e5e8d4f, TC-ISS-03), the NuGet adapter reading the catalog leaf's repository url (f69f75c7) and the bounded, reconciled batch filing with the issue lifecycle and funnel (4de2a682, TC-ISS-09 to TC-ISS-11). Nothing for this item is on integration/cut4. Not claimed by this note: a redetector for each package registry with a resolved-versus-persists pair, the issue-body quality gate, the per-organization issues:write proof and the replay_gap measurement. Nothing is filed; TC-ISS-12 (the final issue list for the owner's approval of the exact list) is READY, so the exit predicate is not met and the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G7-W25
  status: PENDING
  purpose: "Consumed-scope recheck and candidate currency states (Track C-2 of plans/archive/reseal-and-refresh/PLAN.md section 10; docs/investigations/13-bump-cost-and-recheck-design.md). Doc 13 measured that of 39 governed-version bump commits since 2026-09-24 only 7 changed a candidate's outcome, 25 changed nothing a candidate consumed and 7 are not replayable, yet every bump read all sealed candidates as stale. This item implements the design: a bundle records the fact ids it consumed and is reopened only through them (AGENTS.md: invalidate a candidate only through an input it consumed), volatile web observations (HTTP status, redirects, timings) leave hashed evidence and live in the probe record, environment.* versions stop routing bundles to INVALIDATED, and a stale-but-intact bundle is reported separately from a stale-and-failing one. Owner-gated: G7-W22 clause 4 reserves any change to invalidation or counting behavior until the owner has read doc 13 (decision D-OWN-4 in docs/DECISION_LOG.md 2026-10-10), so nothing here starts before that record. Depends on: G7-W22 (the cut and its clause 4), G3-W08 (the new fact kinds the consumed-scope record must cover). Exit predicate: dependencies.json records consumed fact ids additively and evaluate() compares only those, with negative controls in both directions; a changed HTTP status with the same verdict invalidates nothing while a broken link still fails BC-06; the doc 13 section 6.6 tests are present; the day-one status numbers equal doc 13 section 4 (2 current, 2 rerender_only, 26 recompose); environment.* version changes no longer route bundles to INVALIDATED; the owner's recorded approval of the counting change is named in the item. 2026-10-11 status: the first slice is on integration/cut2c, pull request pending, nothing on main. dependencies.json records consumed_fact_ids additively and evaluate() compares only those, with the whole-map comparison kept for a record without the field (f4bce0f4, TC-INV-01); link and product-page evidence is the verdict word only and the HTTP detail moved to the unhashed probes.json (TC-INV-02); an environment.extractor_version or inherited_units_version difference reopens EXTRACTING as VALID_UPDATE_AVAILABLE and no longer routes a bundle to INVALIDATED (ea65ff64, TC-CUR-01), and `repository-presenter recheck` reports CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL, UPDATE_REQUIRED (rerender_only or recompose) and UNVERIFIED, with `status` splitting update_available into update_required and update_unverified. Dry run over the 30 committed bundles: 30 VALID_UPDATE_AVAILABLE, 0 INVALIDATED; recheck counted 1 of 30 (RECHECKED_CURRENT 1, UPDATE_REQUIRED 29: rerender_only 2, recompose 27), which differs from doc 13 section 4 (2 current, 2 rerender_only, 26 recompose) because REVIEWER_LOGIC_VERSION 19 changes the replayed verdict on bundles that keep raw reads. Not done: the warn-only CI bump-impact preview, the G7-W14 receipt refresh, recheck-aware hosted counts, and a dedicated extraction scope (a schema change that needs a section 31 proposal and owner admission). The owner's recorded approval of the counting change is still not named, so the exit predicate is not met and the item stays PENDING. 2026-10-11 (latest, docs/DECISION_LOG.md): the first slice described above is on main since pull request #330 (904aa756): TC-INV-01 and TC-INV-02 (f4bce0f4) and TC-CUR-01 (ea65ff64). Nothing for this item is on integration/cut4 beyond EXTRACTOR_VERSION 4, whose difference reopens EXTRACTING as VALID_UPDATE_AVAILABLE and never routes a bundle to INVALIDATED. Not repeated on cut 4: the dry run over the 30 committed bundles (30 VALID_UPDATE_AVAILABLE, 0 INVALIDATED) was taken on cut 2 and has not been run against the cut-4 constants. The owner's recorded approval of the counting change is still not named, so the exit predicate is not met and the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md"
- id: G3-W09
  status: PENDING
  purpose: "Live-first correction lane (Lane L of the two-lane product shape; owner decision D1, 2026-10-11, docs/DECISION_LOG.md). Lane L starts from the live upstream README at the pinned revision and changes it only by verified corrections (a claim the facts contradict: a wrong command, a dead link, a wrong package name or version, a false capability) and verified missing information (a fact the clone holds and the README omits: install and test commands, supported frameworks, published version, community files), each change citing accepted fact ids; every other live unit is preserved byte for byte. The model proposes a typed corrections.json (kind, unit id or insertion point, replacement or addition text, fact ids); deterministic code validates it against facts.json, applies it, runs the blocking checks that apply and the independent acceptance review, and measures not worse than the live README by the rule TC-LIV-03 fixes (no live unit lost without a recorded disposition, no new unsupported claim, acceptance score not below the live README's; D4). Entry point: python -m tools.live_first correct-readme --repo OWNER/NAME; the push gate is a propose kind of correction beside the regeneration kind (components/propose). Scope: all 36 registry entries have a correction candidate or a typed terminal state (NON_PROCESSABLE, insufficient_evidence, NOT_READY) before Monday 2026-10-12 (D7: correction pull requests first, regeneration in parallel). The only push is a sandbox canary on babar-raza/presenter-sandbox (D6); real product repositories stay paused until the owner approves the exact list (OWNER-20). The lane lives in a new package outside src/ and writes no governed file, so no governed version moves (TC-LIV-01 to TC-LIV-04 are no_bump). Depends on: G7-W20 (acceptance profile), G6-W02 (the propose effect and OWNER-11's sandbox), and the cut-3 facts and extractors it reads. Exit predicate: the correct-readme entry point runs on the canary and then on all 36, each with a corrections.json the schema accepts and a recorded authorizable verdict; a second run on the canary is byte-identical with zero provider calls; the sandbox canary pull request is opened through the propose gate under the recorded exact owner authorization; the cursor reports authorizable and sealed counts side by side. 2026-10-11 (latest, docs/DECISION_LOG.md): correction of the placement named above. The lane is built as src/repository_presenter/components/readme_correction/ with the entry point repository-presenter correct-readme --repo OWNER/NAME (and propose --correction-bundle through the typed gate in gate.py), not as the tools/live_first package and python -m tools.live_first entry point this entry names; the At a Glance builder is components/readme_diagram/. It makes no model call and edits no governed file, and it is on integration/cut4 (e407503a, pull request pending), nothing of it on main. Result at 4e2da176 over all 44 registry entries: 39 corrected (34 diagram-only, 5 with a content correction), 4 no detector fired, 1 no live README (GIS-.Net). Every bundle is confined to its listed edits, deterministic, idempotent and zero-call. add_dev_commands and add_doc_links report only, because an independent review of all 44 bundles found every failing hunk in them; the re-enable conditions are recorded (docs/DEFECT_INDEX.md REG-25). The 4e2da176 bundles are not independently re-reviewed and the TC-LIV-03 comparison is not recorded against them, so authorizable_candidates stays 0 of 44, reported beside 29 sealed bundles on disk. The sandbox canary on babar-raza/presenter-sandbox is not opened (OWNER-11, OWNER-20; TC-CAN-01 is READY and waits for the exact owner authorization). The exit predicate is not met and the item stays PENDING. Cards: TC-LIV-06, TC-CAN-01. Taskcards: plans/archive/reseal-and-refresh/PLAN.md (TC-LIV-01 to TC-LIV-05)"
- id: G3-W10
  status: PENDING
  purpose: "README structure, composition, link and tone standard from the live READMEs (owner decision D2, 2026-10-11, docs/DECISION_LOG.md). docs/README_CONTRACT.md as written is no longer the standard and is under revision: the standard is what the live upstream READMEs do, as a common schema (sections and their order, link and badge conventions, tone) plus a product-wise-differences schema (what varies by ecosystem and product family), derived from a survey of all 36 live READMEs; every iteration of either lane must do better than live against it. This item surveys, writes both schemas as data validated by a JSON Schema, rewrites README_CONTRACT.md from them (keeping the blocking-check cap and the contract tests green), and adds conformance and better-than-live gates. The survey, the schemas and the rewrite change no governed file; the gates are a governed change that lands only in a declared later cut with the owner's D2 decision as its ground (G7-W22 clause 2), never inside cut 3. Depends on: G3-W06 (the contract text it rewrites), G7-W22 (the cut that carries the gates), G3-W09 (the better-than-live comparison). Exit predicate: the survey covers all 36 live READMEs with the revision and blob id of each; both schemas validate every surveyed README or record the exception with a reason; README_CONTRACT.md is rewritten from them and says so in its header; the conformance gates reject negative controls drawn from live READMEs and pass the survey's exemplars; conformance counts before and after the next reseal are recorded. 2026-10-11 status (owner rulings R1 to R7, docs/DECISION_LOG.md, this date): docs/README_STANDARD.md now owns a README's structure and composition (a fixed core plus inherited additions retained in place), links and tone, and its data and validator pass (python -m tools.readme_standard.check_profiles); plans/idea.md was corrected at the owner's explicit request (the banner above the opening is not promotion, the Enterprise anchor reads Aspose.<Family> for <Platform> - Enterprise Edition, Enterprise Edition is the only name of the aspose.com product, each live README owns its tone and structure, the structure has two kinds, and At a Glance is never clipped and runs left to right); the code gates that still encode the replaced rules (the BC-06 anchor prefix, promotion_after_product, the capabilities range, the visible budget, SEMANTIC_SHELL, the flowchart TD emitter and its BC-07 check) are owner-ruled, pending the next governed cut (docs/README_STANDARD.md section 6.2, items 1 to 15). The At a Glance rule adds cards TC-MMD-01 to TC-MMD-03 (a diagram builder in a new package, render-verified golden tests, and the renderer and gate migration, governed and for the next cut with the other structure gates). The exit predicate is unchanged and not met, so the item stays PENDING. 2026-10-11 (latest, docs/DECISION_LOG.md): on integration/cut4 (e407503a, pull request pending), nothing of it on main: the survey and assignments cover all 44 registry entries (the eight JMAP libraries added, defect classes DEF-27 and DEF-28), the owner rulings R1 to R7 and the corrected plans/idea.md are committed there, and the At a Glance migration (item 15, TC-MMD-03) is in the cut-4 commits (components/readme_diagram, RENDERER_VERSION 33, BC-07 11; 40 of 40 live diagrams were vertical and clipped in a real render), its marker in docs/README_STANDARD.md section 6.2 not yet updated. The SEMANTIC_SHELL, BC-06 anchor-prefix, promotion_after_product and capabilities-range migrations of section 6.2 are not among the cut-4 commits (BC-06 stays at version 7) and wait for a later governed cut. Item 12 of section 6.2 is done: docs/EXECUTION_STATE_MACHINE.md, README.md, project/loop-prompt.md, tools/reviewer/procedure.md and docs/README_CONTRACT.md now name docs/README_STANDARD.md as the owner of a README's structure and composition, and the contract as the legacy encoding of assembly and blocking checks until the gates migrate. The exit predicate (conformance gates, conformance counts before and after the next reseal) is not met and the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md (TC-STD-01 to TC-STD-04, TC-MMD-01 to TC-MMD-03)"
- id: G3-W11
  status: PENDING
  purpose: "Regeneration idempotence (Lane R: regeneration from scratch continues, the owner values it more; owner decision D1, 2026-10-11, docs/DECISION_LOG.md). Regenerating from a README that already conforms to the standard must reach a fixed point: a second regeneration is byte-identical to the first and, from a conformant source with no fact delta, changes nothing and makes zero provider calls. Today it does not: the same facts and a conformant source yield a different README on a later pass. A second first-principles analysis of the root cause is running and is the input of TC-IDM-01; the fix is a production-grade design change at the earliest causal stage (reconciliation and composition: a conformant source unit with no fact delta keeps its text and composition returns it without a provider call), not a downstream check that hides the drift. Depends on: G3-W10 (its standard defines conformant), G7-W22 (the fix is a governed change for a declared later cut, with D1 as the owner ground). Exit predicate: the root cause is recorded with a reproduction under docs/investigations; a property test shows generate(generate(x)) equals generate(x) for the canary and a sampled set, with zero provider calls on the second pass; the fix lands with negative controls and one bump per governed constant; the portfolio fixed-point rate (second pass byte-identical) is recorded before and after. 2026-10-11 (latest, docs/DECISION_LOG.md): the second first-principles analysis is finished and its findings are recorded in the log. Replay holds but regeneration is not a fixed point, from three independent sources: the design (a README's wording reaches the output only through units reconciliation keeps and placement does not drop, and the reconciliation prompt supersedes the lists the generator itself wrote), the gateway (17 of 18 byte-identical requests returned different responses at temperature 0) and a measurement that tests only replay. A sealed candidate keeps 33 percent of live sentences verbatim with a median of 49 hunks against a median of 1 edit the standard requires. The minimum design it names (the live README as the document, a deterministic audit, an edit script over the live units with copy-through by default, about 90 to 125 engineer-hours) is not adopted: this item decides, and TC-IDM-01 commits the report under docs/investigations with its reproduction. Nothing for this item is on main or on integration/cut4. The exit predicate is not met and the item stays PENDING. Taskcards: plans/archive/reseal-and-refresh/PLAN.md (TC-IDM-01 to TC-IDM-03, TC-VER-03)"
```

### 27.10 Composition variance and the D3 question (2026-09-04, evening)

**Measurement (the loop's, during G2-W12).** Four successive compositions of the canary at the
same revision, while the per-call schemas cut re-asks from 20% to 15% (first-attempt acceptance
80% → 85.3%), produced 10 advisories, then 7, then 0, then a blocking BC-07 failure
(`abbreviation 'glb' is not in its canonical form GLB`, which the repair loop declared
unrepairable), then 7. Re-ask rate and composition quality are close to independent; the second
decides whether a candidate seals. The loop stopped and asked whether D3 (anchored plans, G5-W01)
should move back ahead of the cohorts, and why a casing repair came back unrepairable.

**Decisions (owner, 2026-09-04).**

1. **D3 stays in G5.** Anchoring binds a plan to the *previous accepted plan of the same
   repository*; a first candidate has none, so D3 cannot reduce first-candidate variance — the
   thing the cohorts spend budget on. D3's canonical-ordering half reduces render variance for
   semantically equal plans, which is not the variance observed.
2. **The observed variance has three sources, each with an owner already in the queue.**
   (a) Model sampling across identical requests — temperature 0 with no `seed` (§27.2 RC4).
   → **G2-W19**, a small slice of D4 pulled forward: probe the gateway for `seed`, adopt it if
   honoured, and record advisory count and blocking failures per composition in the manifest so
   variance is measured, never sampled by accident. (b) Reviewer variance in advisory counts →
   **D5 / G2-W16**: acceptance decided by content makes the reviewer's mood irrelevant to sealing.
   (c) Deterministic prose faults the model produces and the repair loop cannot route — the
   casing slip is the worked example: BC-07's detail carries no `section:` prefix, so
   `targeted.py`'s `_DETAIL_SECTION` regex finds no section and the router answers "the failing
   detail names no LLM-owned section" (§27.2 RC8, §29.2 F-notes). → **W12, now**: the code owns
   `_ABBREVIATIONS`, so casing is normalised constructively in the renderer's prose path with the
   check retained; the same treatment for URLs and hostnames in sentences, commands in sentences,
   and the edition named twice — the four prose families the re-sealed ledger names. Structured
   routing fields replace the regex in **W16**.
3. **Land the reconciliation per-call schema now, with the casing normalisation.** The re-seal it
   needs is W12's own acceptance; a seal blocked by a fault the code can normalise is not a reason
   to hold verified work.
4. **"Re-run until it seals" stays forbidden** (loop-prompt §5). The answer to variance is fewer
   causes of variance and a deterministic seal, never more samples.

**What this does not settle.** Whether `qwen3-next` honours `seed` is unknown until G2-W19 probes
it. If it does not, first-candidate variance remains bounded only by (b) and (c), and the cohort
items must budget for it honestly: a composition that fails a blocking check is a disposition with
its cause, not a retry.

**Follow-up, measured (2026-09-04, late).** W12 accepted at `53960a5` with its predicates rewritten
to what the gateway allows: 91.7% first-attempt acceptance and 8.3% re-ask (from 80/20); three of
four structural families schema-impossible with tests; casing and the repeated edition name
normalised constructively; the reconciliation enum at 100%. The gateway answers **HTTP 400 for a
strict `json_schema` carrying `pattern`** — §27.7's anticipated fallback, now measured — so the URL
and command families stayed post-validated. `seed` is **accepted** by `qwen3-next` (HTTP 200,
recorded in `runs/preflight/catalog.json`); whether it is honoured is W19's identical-content test.
Three gaps the loop named, now owned: (1) URLs and commands become *referential* — fact IDs from a
per-call enum, rendered deterministically — which needs no `pattern` (**G2-W20**); (2) a
normalisation that changes rendered bytes is not a recorded dependency, so the invalidation matrix
is blind to it — the gate's own promise, so it stays in G2 (**G2-W21**), not G5; (3) the reviewer
truncated at its 6,000-token budget and the code correctly refused to retry — bounded review output
is added to **G2-W16**.

**Follow-up 3 (2026-09-04, 21:00) — thresholds and what "honoured" means.** With `seed` adopted the
next composition measured 87.5% (3 of 24 rejected) against 91.7% (2 of 24) before it: one rejection
is four points at this sample size. The loop's correction is accepted as the rule from here:

1. **A threshold is never fitted to one sample.** A predicate or regression floor is set from at
   least three sealed compositions — at the observed minimum less one rejection's worth — and
   restated when the data moves, never tightened to a lucky run. The regression control holds 85%
   now; W12's accepted record (91.7/8.3) stands as the measurement it was, not as a gate. G2's
   exit-rate predicate is judged after G2-W20 lands, over the last three sealed compositions.
2. **"Honoured" is measured by the probe, not by compositions.** Extend the preflight seed probe
   to send the *same* bounded completion twice with the same seed, bypassing the store, and compare
   content bytes: identical → `honoured`; different → `accepted, non-deterministic`. Two calls, one
   answer, no composition sampled for a kinder result (which stays forbidden). W19 accepts on the
   wording the probe supports. If the answer is non-deterministic, `seed` stays — declared,
   versioned, harmless — and first-candidate variance rests on D5 (W16), referential units (W20),
   and content-only acceptance, budgeted honestly in the cohorts.
3. **Ownership of measured findings.** The loop may append a dated, facts-only paragraph to the
   RESEARCH section its work item names (this one for W19; §29 for G4 items) — measurements,
   never decisions or rewrites of the owner's text. A measurement that lives only in a commit
   message is a measurement the next iteration cannot read.

**Measured (the loop, 2026-09-04, G2-W19).** The seed probe now sends the same bounded completion
twice with the same seed and compares content bytes, per follow-up 3. Against `qwen3-next`, the
one model all six manifests route to: the request is accepted (HTTP 200) and the two replies are
byte-identical, so the probe records `honoured`. Conditions, because they bound the reading:
`temperature` 0, `max_tokens` 24, the same single-message request both times, the call store
bypassed. Identical content under `temperature` 0 is also what `temperature` 0 alone would tend to
produce, so this measures that seed is accepted and that repeated identical requests agree; it
does not isolate seed's contribution from greedy decoding. `runs/preflight/catalog.json` carries
the result per routed model. The composition after `seed` was adopted measured 24 calls with 3
rejected (87.5%), against 24 with 2 (91.7%) before it; both are single compositions and neither
is a threshold.

**Probe and measurement (the loop, 2026-09-05, G2-W20; §18.4's discovery pattern).** The gateway
was asked whether it honours `prefixItems` in a strict `json_schema`, the keyword that can give
each array position its own constraint where uniform `items` cannot. Two bounded structured calls
per shape, `temperature` 0, `seed` 1, the store bypassed. Both shapes returned HTTP 200 and both
replies validated, so acceptance alone settles nothing; the discriminating call instructed the
model to cite the wrong fact. Under uniform `items` it obeyed the instruction and cited `fact:b`
for slot `alpha`; under `prefixItems` it cited `fact:a` anyway, for that position only. The
keyword is therefore honoured **and enforced**, unlike `pattern`, which this gateway answers with
HTTP 400. Authoring adopted it: one entry per slot, in the task's order, pinning the slot and the
fact IDs the plan assigned it. On the canary that removed the family outright - `section_authoring`
went from 16 of 18 first-attempt with two rejections (one of them `cites facts outside its slot's
planned set`) to **15 of 16 (93.8%)** with one, the identifier family (`test_obj_importer`,
`tests.test_obj_importer`, named from the command block the renderer prints). The 97% this item
asks for means zero rejections in sixteen calls, so that family is what remains. Separately, the
same run failed closed: the reviewer quoted the At a Glance node `c2` by its label without the
quotation marks Mermaid wraps it in, `quote_located` found nothing, and two rejections ended the
transaction on a `JobError` rather than a verdict. A label's quotation marks are the diagram's
syntax, so the normaliser now drops them, and the review returned a verdict on the next run. Both
reruns are identical with zero provider calls at every stage.

**Measurement (the loop's, during G3-W01, 2026-09-06).** Seven cohort compositions ran in three
lanes after the facts-only preflight; none sealed, and the seven failures fall into three classes.
Five of seven — TeX, BarCode, Note, Email and Slides — ended at `section_authoring` after both
attempts on the *same* token: `TeX`, `BarCode`, `OneNote`, `EmailMessage`, `PowerPoint`, each an
`identifiers that are not accepted fact values` rejection. `identifier_tokens` cannot separate a
product or format name from a class name by shape, and its all-capital carve-out (U3D, 3MF) does
not reach a CamelCase one; the re-ask cannot help, because the sentence needs the word. Over all
twelve extracted repositories, admitting a capitalised token the source README spells in running
prose — outside every fenced block, code span, link destination, URL and tag — and the product
name's own segments, minus everything the facts already license as an identifier, adds **1 to 13
tokens per repository** (median 4): `OpenType`, `TrueType`, `PostScript`, `OpenDocument`,
`SpreadsheetML`, `PowerPoint`, `LaTeX`, `MiKTeX`, `HarfBuzz`, `QuickJS`, `ReportLab`, the WHATWG
interface names Aspose.HTML implements, and the PDF and DOC structure names (`AcroForm`,
`ExtGState`, `PlcSpaMom`). Requiring every dotted segment to be capitalised and no underscore
keeps `ws.tables`, `io.BytesIO`, `class_list`, `app.xml` and `CHANGELOG.md` identifiers. TeX's
other two strays, `TeXJob` and `TeXJob.messages`, stay rejected — all ten of its examples are
`CONTRADICTED`, so no fact records the class — which is the check working. The other two classes
are one each: Cells reached validation and failed BC-07 on `abbreviation 'xlsx' is not in its
canonical form XLSX`, unrepairable — the `glb` defect of 2026-09-04 above, recurring; and Page
ended at `source_reconciliation` after two rejections of `inherited_unit:011.heading`, whose
section renders nothing at this revision. The `xlsx` was written by Aspose.Cells' own docstring,
lifted into an API Reference row: the one prose path decision 2(c) did not reach, since a
docstring belongs to no LLM-owned section and no repair can rewrite it. `_symbol_description`
now normalises what it returns, exactly as the authored-prose path does, with BC-07 retained.
After both fixes, TeX and Email cleared the opening and failed further in — `TeXJob` (whose ten
examples are all `CONTRADICTED`) and `email.message`, a lowercase module path the noun rule
deliberately excludes. Under §28.12 rule (4) each is a disposition, not a third attempt.

**Measurement (the loop's, G3-W01, 2026-09-06, later).** Recomposed against the two fixes, Cells
and Note each advanced a stage and stopped on a different cause. Cells reached `independent_review`
and failed closed twice: both rejected findings were quotes that **trail off** — `subgraph
StartingPoints["Starting Points"]...` and `Open an existing \`input.xlsx\` workbook...` — whose
single normalised fragment is exact candidate text (verified against the rendered README: 43 and
39 characters, present in the 35,942-character normalised haystack). `quote_located` handled an
ellipsis only *between* two fragments, and the eighty-character anchor cannot reach a quote this
short, so a reviewer abbreviating one line ended the transaction on a `JobError` rather than a
verdict — the third instance of that failure mode after the Mermaid label quotes and the
flattened fence. A single fragment now counts when the quote really carried an ellipsis. Note
stopped at `section_authoring` on `capability:4`, titled "Export pages to PDF" while
`format:output.pdf` is `UNRESOLVED`: the check is right — the title claims what the repository
does not prove — but it fires at S6, where the plan is already fixed and a re-ask can only
rewrite prose. `plan_checks` now asks the same question at S5, beside the rule that already
governs the At a Glance formats, where the model can choose another title.

**Measurement (the loop's, G3-W01, 2026-09-06, the two-reader rule).** With the quote fix, Cells
and Slides both reached a verdict and both stopped at BC-10 `REJECT_PRESENTATION`. Cells repaired
four findings and Slides two, escalating one; what stood was **four findings on Cells and three
on Slides, every one of them `criterion: presentation` at `causal_stage: S6`** — key capabilities
"omits critical details from the original", the Detailed Member Reference, a scope limitation's
wording, the opening's example list. The repair loop's own reasons are `no failing check names an
LLM-owned section` and `section structure is deterministic; its blocks change only when facts
change`: nothing the loop can act on, which is §26's definition of a prose judgment. That is the
class §27.8's two-reader rule names, on the required rows where an advisory left standing blocks,
and it is now the dominant sealing risk exactly as the owner predicted — two of two repositories
that reached review. The rule landed here: a presentation finding on a required row is read a
second time under a different seed (the same prompt, so the prompt hash and every recorded
dependency are unchanged), and blocks only if the second read raises a finding of the same class
— same section, same stage, same criterion. Otherwise it is recorded `single_reader_advisory`,
which neither blocks nor counts as an advisory left standing, and the candidate seals. The second
read costs one call and can only remove a finding from the blocking set: a read that fails its
own checks corroborates nothing, so corroboration can never turn a sealing candidate into a
failed transaction.

**Measurement (the loop's, G3-W01, 2026-09-06, what two readers agree on).** Recomposed under the
rule, Cells and Slides both read twice. The rule acted — Cells' `opening` finding and Slides'
`scope_limitations` finding became `single_reader_advisory` — and the second reader **corroborated
the rest**: three classes on Cells (`key_capabilities`, `api_reference`, `scope_limitations`),
two on Slides (`additional_examples`, `structure`). Both candidates still fail BC-10, and that is
the rule working, not failing: two independent reads agree. Reading the five texts, every one is
an **absence claim carrying an empty `absent` list** — "omits critical details from the original",
"omits the Markdown export example entirely", "omits the 'Links' section entirely" — and every one
also carries `fact_ids: []`. §6's rule from G2-W17 already says an absence claim states what is
missing as text the code can look for; these state it only in prose, so `absence_defect` has
nothing to check and the finding stands on assertion alone. Two of the five are refutable on
existing precedent without touching that rule: Slides' `structure` finding asks for a "Links"
section the semantic shell does not define, which is the same case `presentation_defect` already
makes for a deterministic section (the repair loop prints exactly this: *section structure is
deterministic; its blocks change only when facts change*); and Cells' `api_reference` finding
quotes `#### Detailed Member Reference`, a heading the renderer emits because contract row 14
requires it, which is the case `rendered_defect` already makes for a renderer-written sentence.
Both are recorded in §31 rather than landed here: this iteration has already changed the review
twice, and loop-prompt §6 rule 4 says stop.

**Measurement (the loop's, G3-W01, 2026-09-06, the cold-run determinism question folded in from
G2-W23).** The canary's `runs/transactions/` and `runs/clones/` were deleted and `present` run once
from cold at the same source revision `65b1f577`, then compared byte for byte with the sealed
bundle. **It does not reproduce it, and it does not seal.** Every one of the thirteen shared
artifacts differs — `facts.json` included — and `dependencies.json` and `manifest.json` are absent
because the run never reached a seal: validation ends 9 pass, 1 fail, 1 pending, the failure being
BC-10 `REJECT_PRESENTATION` after two repair rounds that repaired nothing. The cold reviewer raised
two findings the second reader corroborated: `key_capabilities`, that the Triangulate polygons
capability attributes the implementation to the wrong type, and `development_testing`, that the
section omits the AGENTS.md reference and the publish workflow link. Six classes were corroborated
in all. **The differing stage is S2 onward — there is no single one.** Two consequences follow.
G5-W02's bundle seeding is *not* demoted to a fallback: a sealed bundle is the only copy of its own
composition, and the zero-call proof rests on the stored calls, not on reproducibility. And the
two-reader rule is not a rubber stamp — on a fresh composition of the very repository that is
already sealed, two independent readers agreed six times.

## 28. The delivery process as a production problem: fastest path to every candidate without losing quality (2026-09-04)

§27 diagnosed the README pipeline. This section diagnoses the *delivery process* — the gate plan,
the work-item cadence, and where the owner's tokens and hours go — because at the measured cadence
the plan reaches 34/34 in eight to fourteen days of continuous running, and the owner has neither
the tokens nor the time. Evidence: the ESM gate sections, `project/state.yaml`, the cadence measured
in §27.1, the registry, the frozen legacy tree under `runs/legacy/`, and aspose.org's extraction
package at `D:\onedrive\Documents\GitHub\aspose.org\scripts\pipeline\extraction` (HEAD `b3ad363a`).
Estimates below are estimates; the mechanisms are cited.

### 28.1 Symptoms

- 1 of 34 candidates after three days of green, disciplined iteration.
- ~30 minutes per iteration, ~4 iterations per work item, ~40–60 items between here and 34/34 on
  the current plan: roughly 200 iterations, each re-reading governance, running a ~7-minute suite,
  and watching CI. The owner's spend scales with iterations, not with candidates.
- The registry is 13 Python, 7 .NET, 4 Java, 4 C++, 3 TypeScript, 2 Go, 1 Rust; the reachable
  ceiling is the enabled-entry count in `data/registry.json`, never a number restated here (a
  hardcoded "31" stood on this line for five days after item 31 re-enabled PDF-TS; corrected
  2026-09-11, PHASE1/F3) — plus 34 dispositions.

### 28.2 Root causes

- **RC-A Work is organised by mechanism, not by candidate.** G2 stabilises, G3 builds seven
  plugins, G4 builds the durable runtime and hosted workflows *and then* processes the portfolio,
  G5–G7 publish and certify. Candidates — the only unit of progress §0 recognises — arrive last.
  §27.9 repeated the pattern by queuing eight mechanism items ahead of the second candidate.
- **RC-B Six ecosystems are planned as six bespoke plugins, each with its own surface extractor.**
  That is the single largest remaining cost. Two proven alternatives exist in trees this project
  already controls: aspose.org's tree-sitter extraction engine (`lang/{csharp,java,cpp,go,rust,
  typescript,python}.py`, `api_surface.py`, `formats.py`, `format_signals.py`; 10,328 lines; twelve
  extraction test modules; grammars via `tree_sitter_language_pack`) — the code that produced the
  API tables of the 32 live READMEs this project measures itself against (§24); and the legacy's
  ADAPT_AS_PLUGIN ecosystem modules (thin manifest parsers plus toolchain-backed example verifiers
  for .NET 353 lines, C++ 122, Rust 82, calling `dotnet`, `javac`/`mvn`, `go`, `cargo`, `cmake`,
  `tsc`). §18's registry already names tree-sitter as the first choice for exactly this.
- **RC-C Hosted autonomy is bundled with the portfolio.** G4's CAS, leases, recovery, `monitor.yml`
  and `present.yml` are needed for unattended operation, not for producing 31 candidates locally.
- **RC-D Per-iteration ceremony is fixed cost.** Seven minutes of tests (W11 fixes), three of CI
  watch, governance reading; ~35% of an item's wall clock is ceremony rather than change.
- **RC-E Rerun-durability work is scheduled before first candidates.** D3 (anchoring) and D4
  (portable proof) protect reruns over time and hosted runs; they do not change what the first
  candidate of a repository says. D1, D2, D5, D6 do.

### 28.3 Structural weakness

The plan optimises for architectural certainty in gate order (transaction → boundary → runtime →
portfolio) while the owner's constraint is candidates per token. Both are legitimate; the plan
never states which wins when they conflict, so the loop — correctly following the plan — spends its
budget on mechanisms. The fix is to make *candidates per token* the ordering principle for the rest
of the local portfolio, and to move everything that only matters for reruns or unattended hosted
operation behind 31/31.

### 28.4 Preserve

Every quality gate stays: the eleven blocking checks, independent review, the fresh-process
zero-call proof, D1 (cuts the 20% re-ask share and the fail-closed risk before running 30 more
repositories), D2 (title binding), D5 (content-only acceptance — without it, 31 READMEs would ship
with demoted-advisory defects), D6 (coverage ledger — the family-specific fixture work happens per
cohort, honestly). Every verifier keeps its negative control. The plugin protocol, the reuse-manifest
pull discipline (one file record, its tests, its import closure), the serial coordinator.

### 28.5 The restructured plan

Order by candidates per token. Gates keep their IDs and the eight-gate budget; G3–G7 content moves.

- **G2 (now)**: W08 → W11 → W12 D1 → W13 D2 → W16 D5 → W17 D6 → W09 freeze v1 → W10 second
  ecosystem (2/34). D3, D4, and W18 leave G2 (they return in G5).
- **G3 — Python cohort and freeze**: one cohort item runs the 12 remaining Python repositories
  through the existing pipeline: seal what passes, record an evidence-bound disposition for what
  does not, fix causes by failure class (one fix unblocks many), never per repository by hand.
  Up to 13/34. Contract v1 freezes after the cohort, when thirteen products have sealed against it.
- **G4 — Multi-language cohorts, local**: (1) pull aspose.org's extraction engine as the shared
  tree-sitter surface extractor behind `PlatformPlugin`, with its tests, from a pinned revision
  recorded as a second manifest source; the prohibition on a *runtime* dependency on the sibling
  system stays — files are copied with records, never imported from it. (2) Six thin ecosystem
  plugins — manifest parser, toolchain verifier with a negative control, format signals — each item
  running its cohort: .NET (6), Java (4), C++ (4), TypeScript (2), Go (2), Rust (1). 31/31 READMEs,
  34/34 dispositions, all local. This is the old G4 step 5 without steps 1–4.
- **G5 — Rerun durability and hosted operation**: D3, D4, W18, then the durable runtime and the
  hosted workflows (old G4 steps 1–4), with the old G4 exit predicates.
- **G6 — Proposal effect proof** (old G5, unchanged). **G7 — Production readiness and continuous
  operation** (old G6 and G7 merged; nothing dropped).

### 28.6 Cost, honestly estimated

| Path | Items to 31 READMEs | Loop time | Owner tokens |
|---|---|---|---|
| Current plan | ~40–60 | 8–14 days continuous | scales with ~200 iterations |
| Restructured | ~16 (5 in G2, 2 in G3, 8 in G4) | 2–3 days continuous | roughly one third |

The tool's own time (31 compositions at 3–9 minutes, re-sealed once after D3/D4 land) costs
gateway tokens, not owner tokens, and runs while the agent waits.

### 28.7 Validation and regression controls added by this plan

1. **Cohort report** per gate: sealed / disposition-recorded / failed, by failure class, in the gate
   evidence manifest; a class fixed once must not recur in a later cohort (test per class).
2. **Extractor parity**: for every G4 representative, the pulled extractor's verified public-type
   count is compared with the live README's API row count (§24 census); a shortfall is a coverage
   finding routed to EXTRACTING, never silently accepted.
3. **Negative control per verifier** (unchanged): each toolchain verifier rejects one realistic
   invalid example.
4. **Portfolio-level §27.6 controls**: rejection telemetry and coverage ratios become per-cohort
   predicates, which is what turns them from single-repository claims into evidence.
5. **Re-seal after D3/D4**: every candidate re-seals byte-identically or records the delta with its
   cause; that is the fresh-state proof's first real test.

### 28.8 Trade-offs, risks, limits

- Adapting aspose.org's extractor is the biggest bet and the biggest saving. Its output model
  (classes, claims, coverage) is not this project's fact model; a per-plugin adapter maps it onto
  `public_symbol`, `format`, and `package` facts with file-and-line evidence. Its known behaviours on
  these exact repositories are an asset; its defects, if any, are inherited and must be caught by
  the parity control and row-14 uniqueness. Unverified until the first pull.
- Toolchains: everything present on this machine except Rust (`winget install Rustlang.Rustup`).
  Compiled-example verification will fail on real repositories for real reasons (the Email .NET
  `CS1929` seed in G7); those are honest dispositions, not defects of this plan.
- Deferring D3/D4 means the first 31 candidates are proven only in fresh-process terms. They must
  be re-sealed after D3/D4 before any hosted or unattended run — G5 exists to make that explicit.
- Deferring the hosted runtime means refreshes are owner-triggered until G5. Acceptable now.
- The restructure changes the plan the recovery direction approved. Gate IDs and count are kept;
  content moves. The decision is the owner's and is recorded in `project/state.yaml` when taken.
- Cohort items are heavier than the size rule likes (~1,000 characters, a handful of iterations). A
  cohort splits by *failure class*, never by repository, when it runs long.

### 28.9 Queue proposal — not auto-merged

The owner said go on 2026-09-04. The entries below were moved into §27.9 (the only block
loop-prompt §2 merges), the G2 items D3, D4, and fan-out became G5-W01 to G5-W03, and the ESM
G2–G7 sections were rewritten in the same commit; this block stays as the proposal as recorded.

```yaml
# G3 - inserted when G3 opens, before any ecosystem representative
- id: G3-W01
  status: PENDING
  purpose: "Python cohort (section 28.5): run the twelve remaining Python registry repositories through the existing pipeline in registry order, one transaction each, sealing every candidate that passes all eleven checks and recording an evidence-bound disposition with its resume predicate for every one that does not. Fix causes by failure class, never per repository: a class fixed once carries a test that a later cohort cannot regress. Family-specific format declarations and fixtures (section 27.5 D6) are added only where a repository's coverage ledger demands them. Acceptance: status prints the sealed count; the gate evidence manifest carries the cohort report (sealed, disposition, failure class per repository); every sealed bundle is fresh-process zero-call proven; hosted CI green."
- id: G3-W02
  status: PENDING
  purpose: "Freeze acceptance contract v1 after the Python cohort has sealed against it: the 30-point criterion-specific profile with hard disqualifiers, the blocking checks, and the advisory set, each with a version identifier recorded in every bundle's dependencies.json; a candidate built against another version reopens VALIDATING (section 28.5)."
# G4 - inserted when G4 opens
- id: G4-W01
  status: PENDING
  purpose: "Shared multi-language surface extractor (section 28.5, RC-B): pull aspose.org's tree-sitter extraction engine (scripts/pipeline/extraction: api_surface.py, tree_helpers.py, lang/*.py, formats.py, format_signals.py, and their tests) from the pinned revision recorded as a second reuse-manifest source, one file record each with SHA-256, ported tests, and cut import closure; no runtime import of the sibling repository. Adapt its classes and claims to public_symbol, format, and package facts with file-and-line evidence behind PlatformPlugin. Acceptance: the Python plugin's facts for the canary are unchanged or every difference is explained by a test; the extractor parses one fixture per language with a passing ported test; ruff, mypy, pytest green; hosted CI green."
- id: G4-W02
  status: PENDING
  purpose: ".NET plugin and cohort (section 28.5): manifest facts from csproj and nuspec, public surface through the shared extractor, examples compiled with dotnet build in the isolated workspace, a negative control that rejects one realistic invalid example, format signals through the shared engine; then the six active .NET repositories as a cohort with fixes by failure class and evidence-bound dispositions for failures (the Email .NET CS1929 build failure is a disposition, not a defect of the plugin). Acceptance: cohort report in the gate manifest; every sealed bundle zero-call proven; parity control (section 28.7 item 2) recorded per repository; hosted CI green."
- id: G4-W03
  status: PENDING
  purpose: "Java plugin and cohort (section 28.5): pom.xml facts, public surface through the shared extractor with the internal and impl package exclusion, examples compiled with javac or mvn -q compile, a negative control, format signals; then the four Java repositories as a cohort (two are registry mode full and are the first publication cohort in G6). Acceptance: cohort report; zero-call proofs; parity control per repository; hosted CI green."
- id: G4-W04
  status: PENDING
  purpose: "C++ plugin and cohort (section 28.5): CMake facts, public surface from headers through the shared extractor with internal-visibility handling, examples configured and built with cmake and the installed Build Tools, a negative control, format signals; then the four C++ repositories as a cohort. Acceptance: cohort report; zero-call proofs; parity control; hosted CI green."
- id: G4-W05
  status: PENDING
  purpose: "TypeScript plugin and cohort (section 28.5): package.json facts including exports and ESM/CJS shape, public surface through the shared extractor, examples type-checked with tsc --noEmit via npx, a negative control, format signals; then the two active TypeScript repositories as a cohort. Acceptance: cohort report; zero-call proofs; parity control; hosted CI green."
- id: G4-W06
  status: PENDING
  purpose: "Go plugin and cohort (section 28.5): go.mod facts, exported surface through the shared extractor with interface and struct-embedding handling, examples built with go build and vetted, a negative control, format signals; then the two Go repositories as a cohort. Acceptance: cohort report; zero-call proofs; parity control; hosted CI green."
- id: G4-W07
  status: PENDING
  purpose: "Rust plugin and cohort (section 28.5): Cargo.toml facts including edition and MSRV, pub surface and re-exports through the shared extractor, examples checked with cargo check, a negative control, format signals; then the one Rust repository. The toolchain (rustup) must be present; if absent the item is BLOCKED_EXTERNAL with the install command as its resume predicate. Acceptance: cohort report; zero-call proof; parity control; status prints 31 sealed candidates and 34 dispositions; hosted CI green."
```

### 28.10 Python cohort census (owner, 2026-09-05, static; read-only shallow clones outside the repository)

Prepared so G3-W01's preflight confirms failure classes against a known picture instead of finding
them one repository at a time. Nothing here is a fix: each class is confirmed or refuted by the
preflight before any code changes (§30 A7 — measured over anticipated), then fixed once by class.

| Family | Manifest / layout | Python | Third-party deps | `.py` | README lines | Fences reading a file | Fixture files in tree | CI wf | PyPI |
|---|---|---|---|---|---|---|---|---|---|
| PDF | pyproject / src | ≥3.11 | cryptography, asn1crypto | 367 | 926 | 13 of 13 | 18 | 4 | not published |
| BarCode | pyproject / src | ≥3.12 | Pillow | 130 | 262 | 0 of 6 | 0 | 0 | not published |
| Cells | pyproject / flat | ≥3.7 | pycryptodome, olefile | 87 | 397 | 6 of 6 | 4 (no `.xlsx`) | 0 | 26.7.0 |
| Email | pyproject / flat | ≥3.10 | none | 18 | 411 | 5 of 6 | 4 | 2 | 26.3 |
| Font | pyproject + setup.py / src | ≥3.10 | none | 102 | 486 | 8 of 8 | 142 | 0 | not published |
| HTML | pyproject / src | ≥3.10 | skia-python | 302 | 609 | 0 of 7 | 4 | 0 | not published |
| Note | pyproject / src | ≥3.10 | none | 32 | 528 | 12 of 12 | 38 | 2 | 26.3.2 |
| Page | pyproject + setup.py / src | ≥3.10 | none | 134 | 576 | 5 of 8 | 2268 | 0 | not published |
| PSD | none | – | – | 0 | 2 | – | 0 | 0 | – (NON_PROCESSABLE) |
| Slides | pyproject / flat | ≥3.10 | lxml | 624 | 456 | 15 of 15 | 13 | 2 | 26.8.0 |
| TeX | pyproject / src | ≥3.10 | none | 119 | 368 | 1 of 10 | 30 | 0 | not published |
| Words | pyproject / flat | ≥3.10 | olefile, fpdf2 | 115 | 655 | 11 of 12 | 16 | 0 | 26.7.0 |

No native binaries; every third-party dependency has a cp313/win_amd64 or pure wheel; every README
carries 3–7 images to preserve. G3 can therefore seal at most 12 of 34 (the canary plus eleven).

Anticipated failure classes, by repositories affected: **(1) fixtures for file-reading examples** —
9 repositories, 6 of them entirely; `stage_fixtures` already takes a same-suffix tree file or an
earlier example's output, so the likely gaps are Cells (no `.xlsx` in the tree: a create-then-save
example must run before its readers) and directory-qualified literals. **(2) Unpublished packages**
— 6 of 12; check 2, row 8's "not yet published" sentence and the badge floor (licence plus the
Python-floor badge) have never run, the canary being published; seven repositories carry no CI
workflow. **(3) Format declarations** — the declarations extractor is 3D-specific (`FileFormat.py`,
`register_plugin`); five repositories carry a Save/Load format enum in another shape. At a Glance is
conditional so nothing blocks, and executed examples' load/save literals still yield formats — class
1 drives class 3. **(4) Large READMEs** (926, 655, 609, 576 lines) — the reviewer's output was
bounded in W16; the reconciler's one-disposition-per-unit output may not be. **(5) Layouts** — four
flat packages, seven `src/`, two with both `setup.py` and `pyproject`; BarCode's `>=3.12` floor.
**(6) The gateway's rate limit under lanes** — unknown until measured; 429 handling is G5-W03's, so
the loop scales lanes from the first lane's evidence.

### 28.11 Portfolio census, non-Python (owner, 2026-09-05 23:55; static; read-only shallow clones outside the repository)

Same method as §28.10 for the 21 remaining registry rows; machine-readable copy with per-repository
detail, the toolchain probe, and a digest of aspose.org's per-product `upstream-issues.md` in
`project/portfolio-census.json` (owner planning data, never a runtime input).

| Repository | Eco | Manifest / identity | Floor | Deps | Src/Hdr | README ln | Fences (lang) | File-literal fences | Img | Tests | CI | Lic | Fixtures | Registry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3D .NET | net | 3 csproj · Aspose.3D.Converter | netcoreapp3.1…net10.0 | 4 | 298/0 | 629 | csharp 7, bash 3 | 4 | 4 | y | 0 | y | 2 | NuGet not found |
| 3D Java | java | pom · org.aspose:aspose-3d-foss | java 21 | 1 | 273 | 457 | java 10, xml 1 | 4 | 5 | y | 1 | y | 1 | Maven Central |
| 3D TypeScript | ts | package.json + tsconfig · @aspose/3d | ts ^5.8 | 1 | 176 | 523 | typescript 9, bash 4 | 6 | 3 | y | 0 | **none** | 0 | npm not found |
| Cells .NET | net | 1 csproj + sln · Aspose.Cells.FOSS | net8.0, netstandard2.0 | 1 | 287 | 535 | csharp 9, bash 4 | 9 | 5 | **n** | 0 | n | 119 | NuGet |
| Cells C++ | cpp | 4 CMakeLists · aspose_cells_foss_cpp | C++17 | 0 | 157/129 | 598 | cpp 7, cmake 2 | 2 | 5 | y | 0 | n | 4 | source build |
| Cells Go | go | go.mod · …/Aspose.Cells-FOSS-for-Go/**v26** | go 1.24.5 | 0 | 30 | 507 | go 10, bash 4 | 9 | 5 | y | 0 | y | 0 | proxy lists versions |
| Cells Java | java | pom · org.aspose:aspose-cells-foss | java 17 | 2 | 206 | 515 | java 3, bash 2 | 3 | 5 | y | 1 | n | 105 | Maven Central |
| Cells Rust | rust | Cargo.toml · aspose-cells-foss-rust | edition 2021 | 7 | 249 | 717 | rust 7, toml 2 | 1 | 3 | n | 2 | y | 2 | crates.io not found |
| Cells TypeScript | ts | package.json + tsconfig · **excel-cells** (not Aspose-branded; zip fetch, 44 files) | ts ^5.9 | 3 | 37 | 343 | typescript 3, bash 2 | 3 | 3 | **n** | 0 | **none** | 0 | npm not found |
| Email .NET | net | 5 csproj · Aspose.Email.Foss | net8.0 | 4 | 60 | 320 | csharp 4, bash 3 | 4 | 4 | y | 0 | y | 0 | NuGet |
| Email C++ | cpp | 3 CMakeLists · AsposeEmailFoss | C++17 | 0 | 29/35 | 476 | cpp 4, **powershell 3** | 3 | 3 | y | 0 | y | 3 | source build |
| PDF Go | go | go.mod · …/aspose-pdf-foss-for-go | go 1.24 | 0 | 271 | 913 | go 6, bash 2 | 2 | 7 | y | 2 | y | 69 | proxy lists versions |
| PDF .NET | net | 2 csproj + sln · Aspose.PDF.FOSS | net8.0 | 6 | 1205 | **1724** | csharp 12, xml 1 | 12 | 5 | y | 1 | y | 4 | NuGet |
| PDF C++ | cpp | 2 CMakeLists · Aspose_PDF_FOSS | C++20 | 2 | 381/301 | 899 | cpp 11, bash 2 | 8 | 5 | y | 1 | y | 173 | source build |
| PDF Java | java | pom · org.aspose:aspose-pdf-foss | java 11 | 1 | 1106 | **1666** | java 9, bash 2 | 4 | 5 | y | 2 | y | 1 | Maven Central |
| PDF TypeScript | ts | `disabled` — clone failed twice; disposition only | | | | | | | | | | | | |
| PSD .NET | net | **no manifest, 1 file, 2-line README** → NON_PROCESSABLE | | | | | | | | | | | | |
| Slides .NET | net | 2 csproj + sln · Aspose.Slides.FOSS | net8.0, net10.0 | 5 | 408 | 539 | csharp 9, bash 2 | 7 | 4 | y | 2 | y | 7 | NuGet not found |
| Slides C++ | cpp | 2 CMakeLists + **conanfile** · AsposeSlidesFoss | none stated | 8 | 220/264 | 601 | cpp 10, bash 5 | 10 | 4 | y | 1 | y | 5 | source build |
| Slides Java | java | pom · org.aspose:aspose-slides-foss | java 21 | 5 | 362 | 488 | java 8 | 8 | 4 | y | 2 | y | 4 | Maven Central |
| Words .NET | net | **11 csproj** + sln (identity to confirm; census picked Aspose.Foundation) | net462, net8.0, netstandard2.0 | 19 | 3373 | 961 | csharp 5, bash 3 | 5 | 1 | y | 0 | y | 5794 | NuGet not found |

**Machine (verified 2026-09-05 23:55).** dotnet 10.0.204 · JDK 21.0.11 · Maven 3.9.16 and npx 11.8
present **as `.cmd` shims** — `subprocess` without the extension reports them absent, so every
verifier resolves tools with `shutil.which(name) or shutil.which(name + ".cmd")` and calls the
resolved path · cmake 4.4.1; cl.exe/MSBuild absent, so **OWNER-06 was met on 2026-09-06 01:50 with a
workspace-local GCC 16.2 (WinLibs, MinGW-w64 UCRT) and Ninja 1.13.2 under `C:\tools\rp-toolchains`**
(`TOOLCHAIN_PATHS.txt` names the binaries; prepend the g++ and ninja directories to the *subprocess*
PATH, never the user's; a cmake `-G Ninja` C++20 probe configured, built and ran) · node 24.13 ·
go 1.26.4 · gradle, cargo, rustup absent (Rust provisions workspace-locally, LANE-B-00 / W16).

**What the table says the cohorts will meet.** .NET: three of six unpublished (3D, Slides, Words);
Words is a 11-project solution with a net462 target (a .NET Framework reference assembly pack the
SDK restores from NuGet — usually fine offline-free, to be measured) and 5,794 fixture-like files;
Cells .NET has no tests. Java: all four on Maven Central, floors 11/17/21 under JDK 21, one pom each
— the cheapest cohort after Python. C++: GCC 16.2 + Ninja per OWNER-06 (MSVC absent, so an MSVC-only construct in a repository becomes a disposition); Slides C++ carries a conanfile
(8 deps — conan is not installed; `cmake` with FetchContent would be the fallback, else disposition);
Email C++'s README fences are PowerShell. TypeScript: 3D has no licence file (badge floor is
licence-based — the floor cannot be met; row 2 records that honestly); Cells TypeScript has no
licence and no tests either, and its package name is `excel-cells`; both TypeScript `git clone`s
failed twice with `fetch-pack: invalid index-pack output` (Cells then fetched as a zip; PDF-TS is
`disabled` and its zip hit the Windows path limit — disposition only) — the loop's pinned clone will
show whether the repositories themselves are at fault.
Go: Cells Go's module path carries a `/v26` major suffix (install line and `go get` must use it);
neither has fixture files, but few examples read files. Rust: unpublished on crates.io; 7 deps.

**aspose.org's per-product `upstream-issues.md` (32 files, gitignored there, read-only).** Its
composing agent recorded every example that failed to run and every product bug it hit; the digest
is in the census JSON. Read a repository's file (≤ 240 lines) before composing it: those examples
will fail verification here too and belong in dispositions or omission, not in a second attempt.

### 28.12 Deadline plan (owner, 2026-09-05 23:30): candidates before Monday

**Facts.** The owner's deadline is 2026-09-07 00:00 +05:00 — about 24.5 hours from this writing.
Measured rate over the last 24 hours: 6.0 hours per accepted item; queue 15 items, of which 7 produce
candidates (G3-W01, G4-W11 to G4-W16). Toolchains on this machine: dotnet 10.0.204; JDK 21 with Maven
3.9.16 (no gradle); cmake 4.4.1 with a workspace-local GCC 16.2 + Ninja under `C:\tools\rp-toolchains`
(OWNER-06 met 2026-09-06 01:50 without admin; MSVC absent); node 24 (tsc through `npx typescript`);
go; no cargo/rustup (LANE-B-00 provisions workspace-locally).

**Arithmetic.** At 6 h/item the seven candidate-producing items alone need ~42 h. Two things must be
true at once: the rate roughly halves (xdist, three lanes, no CI waiting, W03 deferred — §30.9 expected
this), and nothing that does not produce candidates runs before the deadline unless a cohort item
needs it. Each cohort item therefore carries a **time box** in §27.9: fix by failure class inside it;
at the box, seal what passes, give every other repository an evidence-bound disposition naming its
failure class and resume predicate, accept, move on. That is the honest shape of "done by Monday" —
a disposition is a truthful record, a rushed README is not.

**Order and boxes (the loop's yardstick; local time, Sunday 2026-09-06).**
1. W17 closes and G2 accepts — by 01:00.
2. G3-W01 Python cohort (11): preflight by 02:00; compositions in three lanes; box 6 h → by 08:00.
3. G4-W10 spec layer, then G4-W09 vendored extractor with the second-source records (G4-W08 folded
   in): together the minimum the .NET cohort needs; box 4 h → by 12:00. §29's reuse audit is what
   makes this box possible — pull, do not write.
4. G4-W11 .NET (5): box 5 h → 17:00. 5. G4-W12 Java (4): box 3 h → 20:00.
6. G4-W14 TypeScript (2) and G4-W15 Go (2): box 2 h each → 24:00.
7. Spill, after the deadline, in this order: G4-W13 C++ (consumes OWNER-06), G4-W16 Rust, G3-W02
   freeze v1 (after every cohort — freezing against 13 products before 31 exist was never the point),
   G3-W03 cache (only on the preflight's measurement), G5-W01 to G5-W03, G6, G7.

**Cut order when behind the yardstick** — (a) the facts cache; (b) the freeze; (c) E6 corroborations
and parity beyond one repository per ecosystem; (d) a fixture or format fix whose class affects one
repository (disposition instead); (e) C++ until the compiler lands. **Never cut:** the eleven blocking
checks, the honesty of every disposition, the zero-call proof, the vendor boundary, one full suite
before each commit.

**Lane B (owner, 2026-09-06 01:20).** A second loop takes the small ecosystem cohorts — G4-W14
TypeScript, G4-W15 Go, G4-W16 Rust, then G4-W13 C++ — in its own git worktree on branch `lane-b`,
under `project/loop-prompt-lane-b.md`, with `project/lanes/lane-b.yaml` as its cursor (the four
entries moved there verbatim from §27.9; one source each), `docs/RESEARCH_LANE_B.md` as its log,
disjoint owned paths (its four platform modules and tests, its repositories' bundles, its lane
evidence), and PRs merged after green CI. It starts with `LANE-B-00` (toolchains: verify the
workspace-local GCC/Ninja, provision rustup under `C:\tools\rp-toolchains`) and waits for G4-W10 and
G4-W09 on `main` before its first cohort. The reviewer spawns it (Opus subagent, worktree isolation),
supervises it through the same check, messages it with `Reviewer:` corrections, and re-spawns it if it
ends early. Gain: TypeScript, Go, Rust and C++ inside the deadline instead of the spill; the primary's
track (Python, .NET, Java) is unchanged. Risks: the account's usage cap arrives sooner with two Opus
loops (lane B pauses first); a shared-file need in a lane cohort becomes a `PROPOSAL` plus a
disposition, never a patch outside the lane's paths.

**Revision at 07:45 Sunday (owner) — what the first seven hours showed and what changes.** Measured
00:50–07:36 from the transcript: 37 iterations averaging 11 minutes, 41 commits, tool wall-clock only
23% (the suite 61 min of it, still 2.4 full runs per commit) — the loop is no longer tool-bound; it
is bound by *iterations per sealed candidate*. G3-W01 accepted at 03:05 at its box with **one seal
(Slides) and ten dispositions**; G4-W10 and G4-W09 accepted by 04:33; the .NET cohort has fixed
eight failure classes since 04:40 without a seal yet. Three causes, in order of weight: (1) **the
loop froze every prompt edit** after reasoning that a prompt change "costs a sealed candidate that
cannot be re-earned" (§31 09:40) — that reading is wrong under the ESM: G2 work item 2 routes a
prompt, template or model-route change to `VALID_UPDATE_AVAILABLE`, the sealed bundle stays current
and counted, and the re-seal is G5-W02's; three Python dispositions (BarCode, Email, Note) name a
prompt change as their resume predicate and were parked behind G5 for nothing; (2) **fact coverage**
— the .NET surface emitted no namespace symbols, Python's native reader misses identifiers the
authored prose legitimately needs, and every such gap becomes a deterministic rejection, two repairs,
and a disposition; the vendored reader is in and unmeasured for Python; (3) **one or two fixes per
iteration** — the loop reads §6 rule 4 as "stop after two changes to the review this iteration",
so a composition round that exposes six classes costs four iterations. Decisions: prompts are edited
freely for the cohorts (re-seal is G5's); **G3-W04**, a three-hour Python second pass, runs after the
.NET box and before Java, re-running the ten dispositioned repositories with the prompt fixes and the
façade-vs-native surface measurement; every class a composition round exposes is fixed in that
iteration (rule 4 limits mechanism churn, not fix count); the full suite runs once per commit
(third reading). **Forecast, honest:** with lane B on TypeScript from 07:40 and these changes, the
achievable range by 00:00 Monday is roughly 8–15 sealed candidates, not 31; the portfolio completes
on Monday. What would have made Sunday different: the prompt freeze and the coverage gap should have
been caught by the reviewer at 04:00 — its hourly wake did not fire between 22:56 and 07:36 (the
owner's session sat in plan mode), and lane B waited three hours for the spawn it was owed at 04:33.

**Lanes C and D (owner, 2026-09-06 08:00).** The shared layer is in, so the remaining ecosystem work
splits by disjoint platform modules: **lane C** takes G4-W12 Java (`project/lanes/lane-c.yaml`),
**lane D** takes G4-W15 Go then G4-W16 Rust (`lane-d.yaml`), lane B keeps G4-W14 TypeScript then
G4-W13 C++. One generic prompt, `project/loop-prompt-lane.md`, parameterised by lane name; branches
`<lane>/<ITEM>`, PR labels `lane-b/c/d`. What a lane may not touch is exactly what every cohort will
need touched sooner or later — `composition/`, `review/`, `repair/`, the renderer, `prompts/`,
`core/`, the façades — so each such defect is a **`PROPOSAL`** in the lane's log plus a disposition,
and the primary carries **G4-W17**, a standing shared-code fix service after G3-W04 that lands the
proposals in arrival order (every class in the same iteration, a test each); the reviewer re-spawns
the lane whose dispositions the landing unblocks. Lanes write fresh verifiers on the base with the
legacy as a read-only reference and never write the reuse manifest, `pyproject.toml` or the lock.
Cost and limit: four Opus workers reach the account's usage cap sooner; if it trips, every worker
stops until the reset — lanes stop first, the primary last. Machine: four concurrent `pytest -n auto`
runs share 32 cores and slow each other; the gateway's rate limit under four composers is unmeasured
(429s are recorded; a lane that meets them scales to one composition at a time).

**How the loop uses the census (§28.10, §28.11).** (1) Inside a cohort, run repositories in yield
order — published package, no native dependency, fixture files present, tests present — so the first
seals come early and the failure classes surface on the cheapest repositories. (2) Facts-only preflight
over the whole cohort before any composition. (3) Fix the biggest failure class first; one class, one
fix, one test. (4) A repository whose blocker is a toolchain, or an unknown class after one attempt,
gets a disposition — never a second bespoke attempt (§5's two-attempt rule). (5) Read the cohort
report and the census row, never a bundle. (6) Provision toolchains before the cohort item that needs
them, workspace-locally, while an earlier item's compositions run in their lanes.

## 29. Ecosystem extraction: what the queued G4 items would really do, and the durable plugin design (2026-09-04)

Two read-only audits: aspose.org's `scripts/pipeline/extraction` at `b3ad363aaf69ce4d00d9aa02ecc59616b9705814`
(the tree that produced the API tables of the 32 live READMEs, §24), and this project's plugin
boundary, shared code, reuse machinery, and the frozen legacy's ecosystem modules and verifiers.
Every claim below is cited; line estimates are estimates.

### 29.1 The question

Six ecosystems are queued as six plugins. Would the loop write them from scratch, and what would it
cost to reuse proven code instead — aspose.org's engine, the legacy's verifiers, battle-tested tools
— or to build them in parallel?

### 29.2 What the loop would do with G4-W01 to G4-W07 as written

- **F1 Authority conflict.** `plans/idea.md` lines 361–363: the sibling pipeline's extraction modules
  are "a development-only reference. Any lesson must be reimplemented behind this project's
  contracts." G4-W01 says "pull." §0 ranks `state.yaml` above `idea.md`, but a careful agent flags
  the contradiction, and the first-principles review that §0 mandates after fifteen minutes without
  narrowing would most likely resolve toward reimplementation — the slow path — or stall.
- **F2 Schema wall.** `schemas/reuse-manifest.schema.json` allows exactly one `source` (object,
  `additionalProperties: false`, `runtime_dependency_allowed: {const: false}`), no `sources`, no
  per-record source. "A second reuse-manifest source" is not expressible; the loop must change the
  schema and `tests/test_schemas.py` first.
- **F3 The wrong copy is the easy copy.** The legacy vendors an older aspose.org extraction
  (`runs/legacy/.../vendored_asposeorg/scripts/pipeline/extraction`, 8,760 lines, disposition
  `FIXTURE_OR_ORACLE_ONLY`) — a single-source pull with no schema change, but it lacks `lang/` and
  `format_signals.py`; every file differs from the live tree.
- **F4 Typing tax.** `mypy` is `strict`; the minimal closure is 17 files / ~10,500 untyped lines.
  Without a sanctioned vendor boundary the loop spends its budget annotating a fork.
- **F5 Importer rule.** "A module with no production importer is a defect" — the extractor cannot
  land alone; its first consumer must land in the same item.
- **F6 Shared-code leaks the plugins cannot fix from their own file** (loop-prompt §3: a platform
  module imports only `core/` and itself): fence language is `entry.ecosystem` (`renderer.py:590,
  628, 634`; `validation/registry.py:438, 848` — a .NET README would get ```` ```net ````); the badge
  row and Installation are hard-coded to `install_command:pip` and `package:python_*`
  (`renderer.py:157–183, 425–490`); `REGISTRY_NAMES` is keyed `dotnet`/`node` while the registry
  says `net`/`typescript` and has no `cpp` (`composition/components/ecosystems.py:12–19`);
  `_LANGUAGE_ALIASES` knows only Python (`extractors/examples/selection.py:8–10`); `PLATFORM_SLUGS`
  lacks `typescript`; `bounded_records` bounds symbol depth by counting dots (`core/facts.py:161`),
  meaningless for `::`. Each plugin item would trip these in turn.
- **F7 Verifiers.** The legacy's .NET, Java, Go, and TypeScript verifiers run in Docker on pinned
  SDK images with pydantic schemas and a snapshot closure (~1,500 lines; Java drags `env`, the
  `CPL-07` module) — not pullable here. Only `example_verifiers/{common,cpp,rust}.py` (240 lines)
  and the six `ecosystems/*.py` manifest readers (356 lines, zero third-party imports) are.
- **F8 Slugs.** `fact_id` slugs accept `^[a-z0-9]+([._-][a-z0-9]+)*$`; `Aspose::ThreeD::Scene` and
  C# nested `Outer+Inner` must be mapped, not passed through.

### 29.3 Root causes

- **RC-E1 The authority text conflates runtime independence with code provenance.** The recovery
  direction rightly banned reading sibling assets at runtime (idea.md 109, 112; manifest 577–578)
  and, in the same breath, banned reuse of the code. The legacy's bulk vendoring (23,574 lines, §10)
  was a failure of *discipline*, not of provenance; the cure was records, tests, and closure — the
  pull discipline this project already has — not reimplementation.
- **RC-E2 Single-source reuse machinery** designed for one migration.
- **RC-E3 A monolithic plugin protocol.** `PlatformPlugin` has seven methods and one implementation,
  1,697 source lines; nothing separates the pure static surface (deterministic), the manifest reader
  (pure), the registry probe (a network observation), and the toolchain verifier (environment-
  dependent). "Add an ecosystem" therefore means "write all four," six times.
- **RC-E4 Python assumptions baked into shared code** (F6).
- **RC-E5 Strictness without a vendor boundary** (F4, F5).
- **RC-E6 No verifier design for compiled ecosystems** in this project's execution model
  (subprocess with an allow-listed environment, 300-second ceiling) — the legacy's answer was
  Docker.

### 29.4 Structural weaknesses

W1 plugin = monolith with mixed determinism classes; W2 governance has one category for all
external code; W3 the renderer is Python-shaped; W4 "reimplement lessons" is the wrong invariant —
the right one is "no runtime import, every pulled line under a record, a test, and a typed façade."

### 29.5 Preserve

The registry-of-entries shape ("ecosystems are added as entries, never as new call sites"); the
closed fact model (kinds, slug IDs, evidence required); the pull discipline; no runtime import of
sibling trees; negative controls per verifier; the execution boundary; the extractor-parity control
(§28.7); the polarity mapping `EXECUTED/COMPILED → SUPPORTED`, `FAILED/TIMED_OUT → CONTRADICTED`,
`NEEDS_INPUT/NOT_VERIFIED/BLOCKED_TOOLCHAIN → UNRESOLVED`.

### 29.6 The durable design

- **E1 Formal second reuse source.** Amend idea.md 361–363 to: the sibling pipeline's extraction
  modules and their tests are a reuse source under the same pull discipline as the legacy — pinned
  revision, one file record each, ported tests, cut closure — and runtime independence is unchanged.
  Extend the manifest schema with `sources` (each with the legacy source's fields; the sibling's
  `working_tree_at_freeze` recorded as `DIRTY`, honestly, like OWNER-03) and a per-record
  `source_id`.
- **E2 A vendored, typed boundary.** The engine lands under
  `extractors/surface/_vendor/aspose_extraction/` at the pin, with its ~15 absolute imports
  rewritten, `mypy` and `ruff` per-path overrides confined to that directory, and every production
  access through a typed `SurfaceExtractor` façade with its own tests. Recorded patches only:
  sort the package-root pick (`package_root.py:44–53`) and the `.csproj` pick (`:58`,
  `package_manifest.py:104`); case-sensitive suffix matching instead of `rglob` (Windows matches
  `.PY`); `MAX_FILES` a constant, not an environment variable; family vocabularies as parameters.
  The façade normalises raw grammar node types to this project's `symbol_kind` enum, maps
  `::`/`+`/generics to slug-safe values, and emits `defined_at` from the member's true declaring
  file and line — the engine already carries both for every type and member.
- **E3 Layered plugins.** `PlatformPlugin` becomes a declarative composition: `EcosystemSpec`
  (ecosystem, tree-sitter language, manifest globs, source suffixes, fence aliases, registry
  template, badge templates, install-command template, symbol separator) plus one
  `ExampleVerifier`. The shared `SurfaceExtractor` serves `surface_facts`, `format_claims`, and
  `format_declarations`; the shared `RegistryProbe` (legacy `ecosystems/registry_request.py`, 61
  pure lines with every URL template, Go-proxy escaping, NuGet lowercasing, plus the load-bearing
  lessons in `resolver.py`: Maven via `repo1.maven.org` never `search.maven.org`; crates.io needs a
  named User-Agent; C++ has no registry) serves `registry_facts`; `ManifestReader` per ecosystem is
  the legacy's ~50–90-line module. Adding an ecosystem is one spec, one verifier, one negative-
  control test — exactly G7's rule.
- **E4 Ecosystem-generic shared code.** Fence language, badges, Installation, `REGISTRY_NAMES`,
  aliases, slugs, symbol depth all read from the spec. One item, before the first non-Python cohort.
- **E5 Verifier design for compiled ecosystems.** Fresh, thin verifiers on `core/execution.py`:
  disposable profile environment (the legacy `common.py` idea — HOME, APPDATA, CARGO_HOME, NuGet
  config redirected to the workspace), per-ecosystem timeouts up to the ceiling, `--locked`/
  `--no-restore`/lockfiles where the repository provides them, resolved dependency versions captured
  into the receipt (the environment class of §27.5 D4). A toolchain this machine lacks is
  provisioned by the verifier base workspace-locally with a pinned version under `runs/toolchains/`
  — as the 3.11 and 3.12 interpreters already are under `runs/verify/` — never system-wide, never a
  PATH or profile edit, the version recorded in the receipt; the same function serves G5's hosted
  runners. `BLOCKED_TOOLCHAIN` means provisioning itself failed — UNRESOLVED, never CONTRADICTED. Pull `example_verifiers/{common,cpp,rust}.py` with a
  small cut; write .NET, Java, Go, TypeScript fresh (~100 lines each).
- **E6 Compiler-emitted corroboration, admitted just-in-time.** Where the toolchain already runs,
  a second independent surface is cheap: `javap -public` after `javac`, a reflection stub after
  `dotnet build`, `go doc -all`, `tsc --declaration`. Agreement with tree-sitter confirms; a
  disagreement is a parity finding routed to EXTRACTING. Admit per ecosystem only when the parity
  control (§28.7 item 2) fails — the engine returns "reachability unknown" for Java, C++, and Go.
- **E7 Machine toolchain version drift, and when the registry should outrank PATH (G4-W17,
  2026-09-25).** Every `extractors/platforms/*_examples.py` resolver (`cpp_compiler`,
  `cmake_executable`, `cargo_executable`, `typescript_compiler`'s own prior shape) tries `PATH`
  before the machine-local registry (`TOOLCHAIN_PATHS.txt`, OWNER-06) — correct exactly when a
  `PATH` tool is at least as capable as whatever the registry separately provisioned (any
  GCC/Clang on `PATH` compiles the same C++; a hosted runner's own CMake has a real certificate
  bundle the winlibs one lacks). Recognize the *other* shape — a machine-toolchain-version-drift
  defect — by its signature: a `BLOCKED_TOOLCHAIN` outcome whose detail names a compiler/tool
  refusing a specific option or flag (not a source-level diagnostic), where a direct
  `probe_compiler`-style check against the *registry's own* recorded tool clears cleanly. That
  signature means `PATH` now offers a version newer than what the repository's own config was
  written for, and the newer version dropped or changed a feature the config still declares — the
  opposite of E5's assumption, so `PATH`-first silently regresses a repository's own declared
  config instead of merely picking a less-provisioned tool. Measured case: `typescript_compiler()`
  resolved a global npm `tsc@7.0.2` (which removed the `moduleResolution: "node"`/`node10` alias
  entirely, `TS5108`) ahead of an already-provisioned, already-probe-proven-compatible registry
  `tsc@5.9.3`, blocking `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at BC-02 for its full
  history (docs/DECISION_LOG.md 2026-09-24 13:53 UTC, 2026-09-25 entry). The fix is a narrow,
  per-function precedence flip scoped to the one resolver with this shape: check the registry
  first, fall back to `PATH` only when the registry has nothing for that tool, so a hosted runner
  with no registry file resolves unchanged. Never a blanket "registry always wins" rule across the
  file — that would regress `cpp_compiler`/`cmake_executable`, where `PATH`-first is the
  documented, deliberate default for the opposite reason.

### 29.7 Validation and regression controls

1. Extractor parity per repository against the live README's API rows (§28.7 item 2).
2. Ported golden tests (≈19 of 25 modules unchanged, 5 with a one-line import swap).
3. Determinism: extract twice and on a shuffled file order — identical facts; a case-sensitivity
   test that passes on Windows and Linux.
4. Kind normalisation: every raw node type maps to the enum; unknown → UNRESOLVED, never dropped.
5. Slug safety for `::`, `+`, generics; every fact carries file-and-line evidence (adapter test).
6. Vendor boundary: a grep-enforced test that nothing outside the façade imports `_vendor`, and
   nothing imports a sibling path.
7. Verifier controls per ecosystem: the negative control; toolchain absent → BLOCKED_TOOLCHAIN →
   UNRESOLVED; network off → registry UNRESOLVED, never CONTRADICTED; timeout → TIMED_OUT recorded.
8. Grammar pinning: exact `tree-sitter` and one exact per-language wheel (`tree-sitter-c-sharp`,
   `-cpp`, `-go`, `-java`, `-python`, `-rust`, `-typescript`) in the lock, loaded by `core/grammars.py`,
   and a parse-probe test per language that fails loudly on a node-type change. No grammar is ever
   downloaded at run time: `tree-sitter-language-pack` fetched each parser from a GitHub release on
   first use and was removed after a release-host 500 failed a CI leg (2026-10-05).

### 29.8 Parallel building, assessed

Governance: one `active_work_item` (schema: a single object), `shared_code_items_in_progress`
(`const: 1`), `parallel_repository_work_allowed: false`, and idea.md 229–233: at most three
disjoint repository workers after isolation proof, serial coordinator, delegation only when
measured throughput improves. G4-W01 is shared code and must be serial and first; every plugin item
also runs its cohort (repository work). Parallel agents would need schema changes, the flag flipped,
an isolation proof, and would touch the legacy's failure mode (agent hierarchies, §12). The saving
is small: with E3, authoring a plugin is roughly one iteration, six in series ≈ 3–5 hours; the
cohort compositions (19 repositories × 3–9 minutes) are tool time and run in the background across
iterations; the real cost is failure-class fixes, which parallelism does not reduce. Decision: no
parallel agents for plugins; the tool runs cohorts in the background; the three-worker allowance is
spent on G5 lanes as idea.md intended.

### 29.9 Trade-offs, risks, limits

- A vendored fork of ~10,500 lines: pinned, patched only by record, re-synced deliberately. The
  upstream keeps evolving; we do not track it. The `lang/` layer there is a seam, not the locus —
  `api_surface.py` (3,765 lines) still holds ~20 inline language branches; we inherit that shape.
- The `mypy` relaxation is real but confined to `_vendor/`; the façade is strict.
- Format detection is regex-over-identifiers with hand-curated denylists and an exemption for a
  heuristic its maintainers chose not to fix; treat `formats` as a signal. Our contract already
  requires a second independent corroboration before a format is SUPPORTED.
- Reachability is unknown for Java, C++, Go in the engine (`export_surface` returns `None`); E6 is
  the fallback, admitted per ecosystem on evidence.
- Java's `internal`/`impl` exclusion is on by default and can drop real API — a spec parameter,
  checked by parity.
- C++ has no registry: `install_command` stays UNRESOLVED and Installation renders the contract's
  source-build fallback.
- Compiled verification depends on network restores and machine state; E5 records what it can and
  says UNRESOLVED when it cannot. Windows here, Ubuntu in CI: tests must not depend on either.
- Estimates: G4-W01 as two items (source amendment and schema; vendor, façade, adapter, first
  consumer) ≈ 4–6 hours; E4 ≈ 2 hours; six plugins ≈ 3–5 hours authoring plus cohorts ≈ 2–3 hours
  tool time plus failure-class fixes ≈ 4–8 hours. G4 ≈ 16–24 hours against 25–40 from scratch, and
  parity with the oracle's extraction by construction rather than by convergence.

### 29.10 Decision required

E1 amends `plans/idea.md`, the plan's authority. The owner decides whether aspose.org becomes a
formal second reuse source under the pull discipline. On a go, the owner applies the amendment,
the schema seed, and the revised G4 queue below through §27.9 at a clean checkpoint. Until then
G4-W01 as queued still says "pull," and the loop would meet F1–F8 in order.

### 29.11 Revised G4 queue (the owner said go on 2026-09-04; merged through §27.9)

The §28 drafts G4-W01 to G4-W07 are superseded and listed as moved in §27.9; IDs are never reused.

- **G4-W08** Second reuse source and schema: idea.md 361–363 amended (done, with the loop-prompt §0
  and §3 rules); `sources[]` and per-record `source_id` in the manifest schema and tests; aspose.org
  pinned at `b3ad363a…` with its dirty working tree recorded; disposition seeds for
  `scripts/pipeline/extraction/**` (EXTRACT_AND_REFACTOR → `extractors/surface/_vendor/`) and its
  tests; `extractors/surface/_vendor/` named in `REPOSITORY_LAYOUT.md`.
- **G4-W10** Ecosystem-generic shared code (E4) plus `EcosystemSpec`, `RegistryProbe` (legacy
  `registry_request.py` ported nearly intact on `httpx`), verifier base with the disposable profile.
- **G4-W09** Shared surface extractor: vendor the 17-file closure with records, rewritten imports,
  the recorded determinism patches, `mypy`/`ruff` overrides confined to `_vendor/`; the typed
  `SurfaceExtractor` façade with kind normalisation, slug mapping, `defined_at`; ~19 ported tests;
  the parity control; first production consumer = the .NET spec's `surface_facts` (no cohort yet).
- **G4-W11…W16** .NET, Java, C++, TypeScript, Go, Rust: one spec, one manifest reader (legacy
  `ecosystems/*.py` pulled), one verifier (cpp/rust pulled with a small cut; the rest fresh), one
  negative control, then the cohort with fixes by failure class and honest dispositions. Parity and
  E6 corroboration per ecosystem when parity fails.

### 29.12 Reuse audit, second pass (owner, 2026-09-06 00:10; aspose.org checkout at HEAD `16d75e95d4`, 509 dirty files)

**What `/readme-refresh` is**, read in its own operational reference (`docs/readme-refresh/`): an
agent-composed README system over a factpack (~20 verified detector fields plus old-README unit
inventories), a deterministic battery of ~103–122 `check_*` gates (about 64 hard), a disposition per
unit, a candidate store of 32 READMEs with an `upstream-issues.md` per product — and **example
verification that is real for Python only** (`python_verification_runner_v2`); every other language
is an "honest BLOCKED-WITH-REASON stub" (its open item TC-HARDEN-01, P1). Its "30/30 clean" is
deterministic gates plus human-accepted stubs, not compiled examples. Our check 3 therefore still
needs per-ecosystem verifiers, and there is nothing to pull for them there (the legacy has cpp and
rust; the rest are short commands on the verifier base).

**What is real, portfolio-wide, and fits behind our facades** — pulled as file records at
`16d75e95d4`, vendor boundary, recorded patches only:

| aspose.org module | Lines | Serves our | Fit |
|---|---|---|---|
| `extraction/api_surface.py`, `tree_helpers.py`, `lang/{csharp,java,cpp,typescript,go,rust,python}.py` | 3765 + 1009 + ~1500 | public-symbol facts | planned (29.2, W09) |
| `extraction/formats.py` + `format_signals.py` | 2047 + 337 | format facts for all seven languages (I/O methods, exporter dicts, ctor imports, save dispatch, enum cross-reference) — replaces our 3D-specific declarations module | W09: in the closure already; the facade names it |
| `extraction/package_manifest.py` | 417 | manifest identity and floor for python/dotnet/java/js/go/rust/cpp — pure functions, no Scout dependency | W09 → ManifestReader facade; W11–W16 stop pulling the legacy readers |
| `commands/foss/dependency_extract.py` | 1114 | contract row 9's dependency snapshot: required / optional / native-system / development per ecosystem with versions (csproj shortest-path pick, nuspec, Maven, go.mod, npm, CMake FetchContent runtime heuristic) and `cross_reference_dependency_claims` | W09 → dependency facts; self-contained by its own design (stdlib; its overrides file is aspose.org data we do not pull) |
| `lib/publication_probe.py` + `lib/package_registries.py` | 264 + registry adapters | live registry fact for PyPI, NuGet, Maven Central, npm, Go proxy, crates.io with metadata findings | W10/W09 → the shared RegistryProbe, replacing the legacy `registry_request.py` port |
| `extraction/snippets.py` | 1061 | tiered snippet discovery (README fences, tests, examples) with continuation chains | optional: when every README example of a repository fails verification, a test-derived snippet gives Quick Start a verified example — pull only when a cohort needs it |
| `commands/foss/readme_refresh_checks.py` (~120 checks) | part of 21k | reference implementations for rules our contract already states (At a Glance shape, licence template, API Reference collapsed, dependency subheadings, narration leaks, enterprise link once, no bridges or forum links) | read when writing a check we own; never pulled wholesale (§6 rules 13–15) |
| `evidence/*`, `verification/*` (token verification against its knowledge model), `knowledge/`, `data/*.json` | — | not facts from the snapshot | read-only reference; `diagram_archetypes.json` and the `upstream-issues.md` files inform the census (§28.11) and dispositions |

**Consequences, applied to §27.9 tonight.** W09 pulls `package_manifest`, `dependency_extract`,
`publication_probe` (+ `package_registries`) alongside the extraction closure and re-pins to
`16d75e95d4` (`b3ad363a` was 2026-09-04's HEAD; the working tree is dirty — 509 files — recorded
honestly; committed content only). W11–W16 take identity, floor, dependencies and registry facts
from those facades and pull a legacy reader only for a field they lack; their verifiers stay
(`dotnet build`, `mvn -q compile` or `javac`, `npx tsc --noEmit`, `go build` + `go vet`, `cargo
check`, `cmake`) and each resolves its tool with `shutil.which(name) or shutil.which(name + ".cmd")`
and calls the resolved path — Maven and npx are `.cmd` shims on this machine (§28.11). aspose.org
notes that cells/cpp ships a NuGet package: the vendored probe decides from the manifest, so "C++
has no registry" is a per-repository fact, not a rule.

**Risks and limits.** Dirty upstream tree (pull committed HEAD only). The modules assume
`scripts/pipeline` on `sys.path` (`from extraction.tree_helpers import …`) — the facade fixes imports
by recorded patch. Three tree-sitter packages pinned exactly (29.x). `dependency_extract` reads an
overrides file we do not carry — pass none, record it. `snippets.py` walks test directories — our
example policy (README fences first, processability first) is unchanged. None of this verifies an
example: the verifiers and the toolchains (OWNER-06 for C++) remain the cohorts' critical path.

## 30. Autonomous execution: what stops the loop, and the design that keeps it running (2026-09-05)

§27 fixed the pipeline, §28 the plan, §29 the ecosystems. This section is about the machine that
executes them: the loop, the human it waits on, and the computer it runs on. Evidence: the loop's own
session transcript (timestamps, `ScheduleWakeup` calls, re-arm prompts), `git log`, the ledgers, and
this machine's power and sync configuration.

### 30.1 Symptoms

- **Eleven of the last forty-eight hours were lost to stops the loop's own rules do not sanction.**
  At 17:53 on 09-04 it called `ScheduleWakeup {stop: true}` to ask whether D3 should move ("I'd
  rather you steer than have me pick"); resumed 18:17. At 20:56 it paused for the owner's read on
  W19's wording; resumed 21:36. At 00:38 on 09-05 it stopped "at a clean checkpoint" with W16 in
  progress and one predicate closed; nothing ran until a re-arm at 09:50 — nine hours.
- The night before (09-04 00:07–09:26) it ran fourteen iterations unattended under the prompt
  "Follow project/loop-prompt.md exactly for one bounded iteration, then schedule the next wakeup
  per its own section 7." The system can run all night; something about the day made it stop.
- Cadence when running: 25–40 minutes per iteration, 4–9 iterations per item, 16 G2 items accepted
  in ~30 running hours.

### 30.2 Root causes

- **RC-L1 The owner is a synchronous dependency.** Governance assigns thresholds, wording, plan
  order, and contract changes to the owner; when the loop meets one it has two honest options —
  stop, or decide and risk overreach — and it chose to stop (17:53, 20:56). Both stops were good
  judgment under the rules as written; the rules were the defect.
- **RC-L2 Task-shaped re-arm prompts.** The 00:03 re-arm read "Resume G2-W16 (READY): …" — a task.
  The loop completed the task and closed out; §7's "stop only when" did not override a prompt that
  framed the whole engagement as one bounded job. The neutral prompt the night before did not have
  this shape. The owner (this session) wrote those resume texts.
- **RC-L3 No channel for a provisional decision.** §0 allowed the loop to append facts, not
  decisions; a decision it needed had nowhere to go but a stop.
- **RC-L4 The owner's own cadence.** Sixteen governance pushes in a day cancelled the loop's CI runs
  and changed files mid-iteration; each cost re-orientation. The manual `state.yaml` scripts depended
  on this session being alive.
- **RC-L5 Reading load.** §0 made the loop read §27 (463 lines) and §29 (202) before most changes;
  ~800 lines per iteration across the reading list.

**Ruled out (measured):** the machine (AC sleep and hibernate both never); the gateway (0 non-200
responses in 816 ledger rows); OneDrive (no account registered in HKCU; the folder name is a legacy
path); Windows file locks (the `PermissionError` hits are the code's own `rmtree` handling).

### 30.3 Structural weakness

A human sits inside an asynchronous system as a synchronous dependency. Every question the loop
could not answer alone became idle time equal to the owner's absence.

### 30.4 Preserve

Fail-closed stops for safety, credentials, effects, and unmet owner items; the loop's habit of
measuring rather than guessing and reporting what it did not do; the honest "I need a read" — now
written down instead of blocking.

### 30.5 Design

- **A1 Decision protocol** (loop-prompt §5). Provisional-and-recorded for thresholds from data,
  wording, intra-gate order, measured fallbacks, restated predicates, and anything §27–§29 already
  sanction — a dated `PROVISIONAL` paragraph in the item's RESEARCH section, with the alternative
  not taken; the owner reviews at the next check-in and may reverse. Scope growth is queued, never
  done. **Revised the same day (owner, 2026-09-05):** there is no stop-and-ask class at all. The
  owner's words: the goal is absolute, the agent must not ask questions, and the human was only an
  intermediary relaying the loop's concerns to the steering session — a bottleneck by construction.
  Contract sentences a sealed defect or the live oracle demands, and interpretations of
  `plans/idea.md` where it is silent, are decided and recorded too (§31, §27.8). What remains are
  prohibitions (never write a product repository, widen a credential, publish, or weaken a check)
  and owner items for actions only a human can physically perform — recorded, skipped around,
  never waited on. The first-principles order the loop decides by is in loop-prompt §5.
- **A2 Canonical re-arm text** (loop-prompt §9): one line, no checkpoint facts in the prompt.
- **A3 Hardened §7**: `stop: true` only under the enumerated conditions; a clean checkpoint, the end
  of a slice, the hour, and the owner's absence are named as non-reasons.
- **A4 Single-source queue** (loop-prompt §2): §27.9 governs queued item text; the loop reconciles
  purposes for non-active items, so the owner's scripts are no longer load-bearing.
- **A5 Reading load**: §27.0 (this file) is the every-iteration read; subsections by citation; whole
  sections only when diagnosing.
- **A6 Owner cadence** (this session's rule for itself): batch governance pushes into at most two
  windows a day unless the loop is blocked; never edit a file the active item names mid-iteration.
- **A7 Cohort preflight** (G3-W01): a facts-only pass over all twelve Python repositories before any
  composition — every failure class known with zero provider calls, fixed by class, then compose.
- **A8 Cold-run determinism measurement** (G2-W23): with `seed` honoured, does a cold run reproduce
  the sealed bytes? If yes, D4's bundle-seeding is a fallback and RC4 is largely closed by `seed`
  alone; if no, the differing stage is named. One composition of tool time, high information.

### 30.6 Validation and regression controls

1. Unsanctioned `stop: true` events per day: 0 (the loop's report names any stop and its §7 clause).
2. Iterations per 24 hours: ≥30 running unattended, against 14–20 today.
3. Provisional decisions: listed in §27.0 at each owner check-in, each reversed or confirmed.
4. §27.9 ↔ `state.yaml` parity test (G2-W23) — a drift is a failing test, not a manual script.
5. Time from a loop question to its answer: measured in the transcript; the target is zero blocking
   questions outside the owner-only class.

### 30.7 Trade-offs, risks, limits

- Provisional decisions will sometimes be wrong. Every one is dated, recorded with the road not
  taken, and reversible in git; the owner-only class is narrow and explicit. The alternative — nine
  idle hours per question — is measured.
- The loop may still pause on a genuine owner-only question; that is correct, and rarer.
- A3 cannot prevent a stop the harness itself causes (context limit, a crash); the canonical
  re-arm text makes recovery one line.
- The cohorts' per-repository surprises remain the largest unknown for the calendar; A7 moves their
  discovery to tool time but does not remove the fixes.
- Estimate, with A1–A3 in force and the machine on AC: G2's five remaining items ≈ 12–15 running
  hours; G3 ≈ 10–12; G4 ≈ 20–28. Roughly 45–55 running hours ≈ 2–2.5 unattended days to 31/31,
  against ≈ 4 days at today's effective 14 running hours per day. The unattended day is the lever.

### 30.8 Autonomy without the legacy's growth (owner, 2026-09-05)

**The question.** With no human in the path, what stops a loop that may decide anything from
becoming the legacy — 619 commits, validators on validators, no tangible outcome? A bad decision is
a reversal; a bad decision *loop* is the failure this project exists to escape.

**Symptoms already visible here, honestly.** Fourteen G2 items accepted while the candidate count
stayed at 1/34 since G1 — the legacy's numerical shape, even though every item traces to a measured
defect on the one sealed candidate and each landed green. Blocking checks 11, a twelfth queued.
`RESEARCH_AND_GUIDELINES.md` grew ~1,500 lines in three days, almost all of it the owner's. The
differences from the legacy are real (defect-traced, measured rates, one ordered queue, honest
records) but they are differences of discipline, not of structure — nothing *mechanical* yet stops
the shape from continuing.

**Root cause.** The legacy's engine was self-authorized scope: the agent that found a gap was the
agent that admitted the work to fix it, so every defect became machinery and machinery found more
defects. Yesterday's autonomy rules gave this loop the same power in one sentence ("scope growth is
queued") without saying who admits the queue. Cleverness of either model is not the variable —
both will add machinery if the rules reward closing items; §6 rule 9 says closed items are not
progress, but nothing measured it.

**Structural weakness.** No separation between *executing* scope and *admitting* scope, and no
ceiling coupled to the outcome unit (candidates).

**Preserve.** Defect-traced additions; §6's prohibitions; the document budgets; the §26 rule that a
check exists only for a sealed defect; the loop's demonstrated restraint so far (its first two §31
entries are measured and small).

**Controls (design).**
- **C1 Admission gate.** Autonomy covers *how* to close queued items, never *what* to add. The loop
  proposes new work in §31 in §27.9 shape; only the owner admits it (moves it into §27.9 /
  `state.yaml`). Meanwhile the loop continues the queue — it is full through 31/31 — restating a
  blocked predicate to what is proven rather than widening.
- **C2 Outcome tripwire.** Every report carries "items accepted since the candidate count last
  rose". From G3 on, at 3 the next item must raise the count (a composition or cohort item) or a
  §31 entry says why not, and no new check is admitted until it does. G2 is exempt only for its
  frozen queue (W22, W17, W20, W23); no new G2 items, by the owner's rule as much as the loop's.
- **C3 Check ceiling and admission criteria.** A new blocking check needs a sealed candidate's
  measured defect, a mutation test, and a subsumption review against the existing checks; blocking
  checks stay ≤ 15 without an owner decision recorded in §27.9; **no meta-checks** — a check whose
  subject is another check's record rather than the candidate is the legacy's signature and is
  forbidden outright.
- **C4 Precedent and oscillation.** Decisions follow §31 precedent unless the evidence differs and
  the entry says how; a subject reversed twice is frozen until the owner rules.
- **C5 Governance freeze for the loop.** The loop writes measurements and §31 entries (≤ 6 lines),
  never new sections or rules. Governance growth is the owner's, budgeted: `RESEARCH_AND_GUIDELINES.md`
  is consolidated after G2 closes and does not exceed 2,700 lines before then.
- **C6 Review cadence without a human relay.** The owner's steering session reviews §31 and
  proposals asynchronously. A live message channel from the loop to that session was considered and
  declined: it would make the loop wait on whether the steering session is awake — the dependency
  §30 removed. If review latency itself becomes the bottleneck, the steering session can run as a
  reviewer loop on a slow cadence (a cheap check of §31 for new entries; a full review only when
  there are some) — an owner choice with a token cost, not a loop dependency.

**Validation and regression controls.** The report's metric block each iteration (items since the
count last rose; blocking checks; §31 entries today; re-ask share; iterations on the active item);
a test that the blocking-check count is ≤ 15; the §27.9/state parity test (G2-W23); the owner's
review confirming or reversing each §31 entry; a gate cannot accept more items than its ESM Work
list plus the owner-admitted queue.

**Trade-offs and limits.** C1 delays genuinely needed new work by the owner's review latency — hours,
not the legacy's months — and the loop is never idle meanwhile. C2 may force a composition before a
check the loop believes it needs; that is the intended pressure, and the check can still be
proposed. C3's ceiling is a judgment (15), chosen so that the twelve contract checks plus a small
margin fit; it is revisited only by the owner. None of this makes a wrong decision impossible; it
makes a wrong *direction* visible within three items instead of three months.

### 30.9 Throughput, measured (owner, 2026-09-05 21:40)

The owner rejected the "stops cost the day" account, correctly: only ~2 hours were caps and stops,
yet G2's exit slipped more than twelve. The loop's transcript from 09:50 to 21:37 (11.8 hours)
answers where the time went: **tool wall-clock 7.7 hours (65%)**, of which **pytest 3.8 hours (33%,
209 invocations, the full suite ~7 minutes)**, **canary compositions 1.8 hours (15%, 116 runs, 8–10
minutes when composition reopens)**, other shell chains 1.6 hours, CI watching 0.4. Model thinking,
reading and writing: ~4.1 hours (35%). Iterations averaged 44 minutes; 15 ran.

**What went wrong.** G2-W11 was accepted "against a predicate rewritten to what the measurement
proves" — the suite stayed at ~7 minutes, and every estimate since assumed the sub-3-minute suite
W11 was queued to deliver. The loop also ran the full suite several times per iteration and a canary
composition after most edits, both permitted by the rules as written. This machine has 32 cores and
`pytest-xdist` was never installed.

**Decisions (owner).** (1) `pytest -n auto`; the full local CI-equivalent runs once, immediately
before the commit; focused tests while changing; a test that cannot run in parallel is fixed, not
exempted. (2) `present` on the canary only when a predicate that names the candidate closes, and
at acceptance. (3) Push and continue; red CI is the next Orient's first work. (4) G2-W17 accepts
when the coverage ledger, receipt sealing, volatile-observation sealing, and the proxy/CA environment
hold; fixtures for file-reading examples move to G3-W01 as failure-class fixes driven by real cohort
repositories. (5) G2-W23 is folded into G3-W01 (cold-run measurement in the preflight; parity test);
its floor fix landed at `9e5f780`. (6) G3-W01 composes in up to three repository lanes — the
concurrency `plans/idea.md` admits once the transaction is stable, which G2 proves.

**Expected.** Iterations ~20–25 minutes (pytest −6 minutes × ~3 runs, one fewer composition, no CI
wait); roughly twice the items per running hour. G2 exits within one or two iterations of these
rules landing; the cohort's twelve compositions take ~40 minutes of lanes instead of ~1.6 hours
serial. **Controls.** The report's metric line gains: full-suite seconds and canary runs this
iteration; the reviewer wake checks both against these ceilings (suite ≤ 120 s, ≤ 1 canary run per
predicate closed). **Limits.** Parallel tests may expose shared-state assumptions (temp dirs,
ports) — fixing them is real work, bounded; the model's ~35% is the thinking and is not cut.

**Second pass, everywhere (owner, 2026-09-05 22:10).** The suite was one cause; the rest, measured:

- **B. The facts stage has no cache.** Every `present` — including the byte-identical no-op rerun and
  every re-composition where no fact changed — recreates the venv, runs `pip install` from source
  with PEP 517 build isolation (fetching `setuptools`/`wheel` from PyPI each time; no wheel cache,
  no `--no-build-isolation`), executes every example, and probes **76** HTTP targets. Receipts
  carry no timings and the CLI prints none, so the cost was invisible; it is plausibly one to two
  minutes of every one of the 116 canary runs. Decision: **G3-W03**, before the cohort — a facts
  cache keyed by source tree hash, extractor version, and environment fingerprint (the RC7 record),
  a per-revision wheel cache, and per-stage wall-clock in the CLI output and the sealed manifest.
  The no-op rerun should then take seconds.
- **C. One predicate per iteration was a rule** (loop-prompt §2). A five-predicate item cost five
  full ceremonies by construction. Decision: close as many predicates as the 90-minute budget
  allows, one commit per predicate, the suite once per commit.
- **D. The CLI tests copy the whole canary upstream per test** (`shutil.copytree` in
  `tests/test_cli.py:220`); the session fixture builds it once and every test copies it again — that
  copy is the 30 seconds G2-W11 was meant to remove. Direction for the xdist change: a hardlinked
  local clone (`git clone --local`) or a shared read-only source with per-test transaction dirs.
- **E. Reading and writing volume.** ~312k tokens of tool output read per day (824k characters of
  file reads); 29 commits with 6,528 body words (225 per commit); the loop prompt grew from 179 to
  308 lines under the owner's hand and is read in full every iteration. Decisions: grep or Read
  with offsets before any whole-file read; commit bodies at most 120 words (§31 and the RESEARCH
  measurement carry the detail); the owner trims the loop prompt to rules plus pointers, history
  moved here — done the same evening: 316 → 280 lines with every rule verified by anchor; the 220
  target was not reachable without cutting rules, and 280 is the honest number.
- **F. Antivirus.** Defender's management interface is unavailable on this machine (0x800106ba —
  another product or the service is off); whether real-time scanning covers `.venv/` and `runs/`
  (thousands of files created per suite run) is unknown. Owner action to check; excluded if it is.
- **Not a cause:** OneDrive (no account registered), the gateway (0 non-200), the machine's power
  settings (never sleeps), the model's own output volume (50k characters a day — small).

**Third pass — the order of G3 and the gate it must pass (owner, 2026-09-05 23:05).** (7) The
cohort preflight runs first, the cache second and only on evidence: a cache keyed on tree hash and
fingerprint pays back on re-runs of one repository at one revision; the cohort's first pass is cold
for every repository whatever the order, pip already keeps its wheel cache, and W03's cheap half
(per-stage timings) belongs in the preflight — which then decides W03 by measurement (median facts
stage above 90 s per repository admits it before step two; otherwise it is deferred behind G3-W02).
(8) G2's exit predicates were restated to what the rules allow: "a blocking coverage check"
contradicted §6 rule 14; "≥95% and re-ask ≤5% per job" was a one-composition number against
§27.10's three-composition rule (section_authoring measures 91.7%); "pytest under three minutes" is
a control in this section, not a gate. The 85 floor, zero blocking findings and zero required-row
advisories stay. Without the restatement the loop would have reached W17's acceptance with a gate
it could neither pass nor honestly accept — loop-prompt §2 advances a gate only when every exit
predicate passes. (9) `parallel_repository_work_allowed` is set true for decision (6) — owner
approval 2026-09-05 22:50: "Parallel work approved, however you need to be more careful than before
to avoid, catch and fix any problems in time." The census behind (7) is §28.10. **Controls.** The
reviewer wake now runs a deterministic check every two hours — liveness, iteration accounting, rule
compliance (full-suite runs per commit, canary runs, CI watching, commit-body length, read volume),
queue-versus-§27.9 agreement, gate-exit satisfiability, growth signals (new modules without an
importer, new check definitions, deferral language in evidence), new §31 entries — and an event
monitor on the loop's transcript reports a stop, a cap, or silence within a minute.

## 31. Provisional decision log - moved to `docs/DECISION_LOG.md`

Moved on 2026-09-08 (43% of this file's bytes, the only section still growing every
session, and the only one with zero `src/`/`tests/`/`prompts/` citations to break).
Numbering is unchanged, so every bare `§31` reference elsewhere in the project still
resolves correctly. Append new entries to `docs/DECISION_LOG.md`, not here.
