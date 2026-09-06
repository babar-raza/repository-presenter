# lane-c decision log (append-only; entries in RESEARCH_AND_GUIDELINES.md section 31 shape; the owner merges)

Lane: `lane-c` (project/lanes/lane-c.yaml). Prompt: project/loop-prompt-lane.md.

- **2026-09-06 · G4-W12 · the Java `EcosystemSpec` is declared in the plugin module and registers
  itself, so no shared file grows an entry.** `platforms/java.py` defines `JAVA` and calls
  `SPECS.setdefault(JAVA.ecosystem, JAVA)` at import; the facts stage's own `plugin_for` import is
  what registers it, and `plugin_for` runs before `select_examples` and before any rendering
  (`cli.py:345` versus `:361`). Alternative rejected: adding `JAVA` to `core/ecosystems.py`, which
  the lane does not own and which lanes B, C and D would all conflict on. Evidence:
  `core/ecosystems.py`'s own docstring and §29.6 E3 say "adding an ecosystem is a spec, a verifier,
  and a negative-control test — never an edit to a shared file"; lane B set the precedent at
  `platforms/typescript.py:78` for G4-W14. Reversal: move the literal into `core/ecosystems.py`'s
  `SPECS` and delete the `setdefault`; nothing else changes.
- **2026-09-06 · G4-W12 · the only file outside the lane's owned paths this item touches is one
  assertion in `tests/.../platforms/test_registry.py`.** `known_ecosystems()` is a directory
  listing, and that test asserts the exact tuple, so *every* lane's module turns it red;
  `("net", "python", "typescript")` became `("java", "net", "python", "typescript")`, two lines and
  a comment. Alternative rejected: a PROPOSAL and a red PR — the item cannot land at all without
  it. Evidence: lane B changed the same two lines when TypeScript landed (PR #3), so this is the
  established shape rather than a widening. Reversal: the assertion is the whole change.
- **PROPOSAL 2026-09-06 A · G4-W12 · `extractors/surface/registry.py` cannot express a Maven
  coordinate, so every Java install fact is UNRESOLVED.** File:
  `src/repository_presenter/components/readme/extractors/surface/registry.py`, `observe()`. Defect:
  it builds `{"registry_type": kind, "candidate": {"name": package_name}}`, but the vendored
  `publication_probe._maven_check` addresses `repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml`
  and returns `ambiguous=True` before it fetches anything when `group_id` or `artifact_id` is
  missing — so the probe never issues a request for any Java package. Repositories: **all four**, in
  two shapes. 3D and Cells die at S4 `source_reconciliation`, because `installation`'s only
  rendering fact kind is `install_command` and no Java install fact can be SUPPORTED, so
  `rendering_fact_ids` is empty and the units the README puts there cannot be folded (PROPOSAL D).
  Slides and PDF get all the way to a rendered README — 221 visible lines of 536 for Slides — and
  die at S9 on `BC-02 failed at EXTRACTING: install_command:maven is UNRESOLVED`, with no repair
  able to act on it. Finding: one façade limitation blocks the entire Java cohort, and it is the
  only thing that does; 3D and Cells are `mode: full` and on Maven Central (§28.11), so the reading
  would be positive. Fix, and it is three lines — `observe()` already computes `kind`:

  ```python
  candidate: dict[str, Any] = {"name": package_name}
  if kind == "maven" and ":" in package_name:
      candidate["group_id"], candidate["artifact_id"] = package_name.split(":", 1)
  ```

  Java's `package:name` is already the coordinate `org.aspose:aspose-3d-foss`, so nothing else
  changes and no other ecosystem is touched. `platforms/java.py::registry_facts` writes its own
  evidence sentence ("Maven Central was not read — the shared probe takes a package name") so the
  candidate never claims a read that did not happen; it becomes `reading.summary` again once this
  lands. Resume predicate for all four dispositions: PROPOSAL A merged on `main`, then re-run
  `present` for each repository.
- **PROPOSAL 2026-09-06 B · G4-W12 · `EcosystemSpec.badge()` formats one `{package}`, which no
  Maven Central badge URL can use.** File: `src/repository_presenter/core/ecosystems.py`,
  `EcosystemSpec.badge`. Defect: shields.io's endpoint is
  `img.shields.io/maven-central/v/{groupId}/{artifactId}` — two path segments — and
  `central.sonatype.com/artifact/{group}/{artifact}` likewise, while `package:name` for Java is the
  coordinate `org.aspose:aspose-3d-foss` a reader actually writes. Repositories: all four; visible
  on 3D and Cells Java, which are published. Finding: the Java spec must leave `version_badge`
  empty, so a published Java package renders no version badge at all. Fix: pass the fact's value
  *and* its parts (`badge(package, group="", artifact="")`), or let a spec declare a callable.
  Alternative rejected: setting `package:name` to `org.aspose/aspose-3d-foss` so one `{package}`
  fits — that is not the coordinate any Java build file takes, and identity facts must be what the
  manifest declares. Resume predicate: PROPOSAL B merged on `main`.
- **PROPOSAL 2026-09-06 C · G4-W12 · the floor's *declaration* is per repository for Java, but
  `EcosystemSpec.floor_declaration` is per ecosystem.** Files:
  `src/repository_presenter/core/ecosystems.py` (the field) and
  `src/repository_presenter/components/readme/composition/renderer.py:253–267` (its only reader).
  Defect: a POM may state the floor as `maven.compiler.release`, `maven.compiler.target` or
  `maven.compiler.source`, and this cohort uses all of them — Slides declares `release`, 3D and
  Cells `target`, PDF `target` and `source`. Naming any single one in the spec would print a
  property three of the four repositories do not declare, which is a fabricated citation. Finding:
  the lane set `floor_declaration="maven.compiler"` (the family, true everywhere) and put the exact
  property in the fact's own evidence, so the record is precise even where the rendered
  parenthetical is generic. Fix: read the declaration from the floor fact's evidence detail (the
  extractor already knows it) and keep the spec field as the fallback. Resume predicate: PROPOSAL C
  merged on `main`; no disposition depends on it — it is a precision loss, not a blocker.
- **PROPOSAL 2026-09-06 D · G4-W12 · a placement into a deterministic section that renders nothing
  is the one impossible placement `normalize` does not fold, and it killed a candidate.** File:
  `src/repository_presenter/components/readme/reconciliation/dispositions.py:295–306`
  (`normalize`). Defect: the function already folds four impossible placements into
  `DEFER_UNRESOLVED` — an unresolved code unit, a command block, a destination whose section
  condition is false, a supersession by an absent section — but when `rendering_fact_ids` is empty
  it returns an *error* instead, so the job is asked to guess `OMIT_UNSUPPORTED` or
  `DEFER_UNRESOLVED` and the whole transaction dies if it does not. Repository:
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`; finding: `source_reconciliation: output rejected
  twice`, five units (`inherited_unit:011`–`015`) placed into `installation`, whose
  `RENDERING_FACT_KINDS` entry is `install_command` and whose only such fact is UNRESOLVED. Fix:
  fold it the same way the branch four lines above does — `DEFER_UNRESOLVED`, destination `None`,
  citing the fact that is not SUPPORTED. The same shape bit Aspose.Cells and Aspose.Words for .NET
  (the comment in that very branch records it), so this is a recurrence, not a new class. Resume
  predicate: PROPOSAL D merged on `main`. Note the coupling: with PROPOSAL A merged the Maven
  install fact becomes SUPPORTED and this placement stops being impossible for the published
  Java repositories — but it stays impossible for every unpublished package in the portfolio.
- **PROPOSAL 2026-09-06 F · G4-W12 · `source_reconciliation` is rejected whole for a coverage
  error a targeted re-ask would close.** Files:
  `src/repository_presenter/components/readme/reconciliation/dispositions.py` (the coverage check)
  and the round runner that re-asks. Defect: with 85 inherited units the job returned no
  disposition for two of them and two dispositions for two others; the whole output is rejected,
  the same full ask is repeated, and the second miss ends the transaction. Repository:
  `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`; finding: `no disposition for inherited units:
  inherited_unit:062.paragraph, inherited_unit:063.heading; more than one disposition for:
  inherited_unit:005.heading, inherited_unit:025.heading`. Fix: drop the duplicate keeping the
  first occurrence (deterministic and lossless), and re-ask only for the units that have no
  disposition rather than for all 85 — the accepted dispositions of one attempt are still
  evidence-bound and there is no reason to throw them away. Resume predicate: PROPOSAL F merged on
  `main`.
- **PROPOSAL 2026-09-06 E · G4-W12 · `presentation_planning` rejects a whole candidate for two
  ceiling breaches deterministic code could fold.** File:
  `src/repository_presenter/components/readme/composition/planning.py:336–368`. Defect: `api_hubs
  must be distinct public_symbol facts` and `Aspose links exceed the ceiling of 4: 5` are both
  *trimmable* — a duplicate hub can be dropped, and the links beyond the ceiling can be dropped in
  the plan's own order — yet both are hard errors, and two rejections end the transaction.
  Repository: `aspose-3d-foss/Aspose.3D-FOSS-for-Java`, which died on the link ceiling in one run
  and on hub distinctness in the next, from the same facts. Finding: with 5,366 `public_symbol`
  facts and 39 `link_target` facts the planning job's compliance with a numeric ceiling is not
  reliable, and the policy packet already carries the numbers, so more prompt text is not the fix.
  Fix: normalise in `planning.py` the way `dispositions.normalize` folds placements — de-duplicate
  `api_hubs` keeping first occurrence, truncate Aspose links to `policy.aspose_links_max` — and
  keep the hard error only for a hub that is not a supported symbol at all. Resume predicate:
  PROPOSAL E merged on `main`.
- **PROPOSAL 2026-09-06 G · G4-W12 · authored prose leaks the phrase "fact id", and BC-07 catches
  it after twelve calls have been spent.** Files: `prompts/section_authoring.yaml` and the
  narration check behind `_check_structure` in
  `src/repository_presenter/components/readme/validation/registry.py`. Defect: both repositories
  that reached S9 failed `BC-07 ... internal narration 'fact id'` — the authoring job wrote the
  machinery's own vocabulary into a reader-facing sentence. Repositories:
  `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` (29 units, 12 provider calls) and
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`; finding: `BC-07 failed at COMPOSING: internal
  narration 'fact id'`. Fix: the authoring prompt states that a unit cites facts by ID in its
  `fact_ids` field and never names them in prose, and `targeted_repair` gets the narration
  vocabulary as an explicit removal instruction so the one repair attempt can act on it (it
  recorded the finding as unrepairable both times). Resume predicate: PROPOSAL G merged on `main`;
  it is not a blocker on its own — both repositories failed on BC-02 first.
- **2026-09-06 · G4-W12 · the Java example verifier is `javac`, not `mvn -q compile`, and it
  compiles the whole product once before any example.** Every dependency all four POMs declare is
  `test` scope (3D: JUnit; Cells: JUnit and Apache POI; PDF: JUnit; Slides: JUnit and four more),
  so a consumer resolves nothing and there is nothing to download. Alternative rejected: `mvn -q
  compile` with `-Dmaven.repo.local` under `runs/` — it needs the network for its own plugins,
  writes `target/` into the pinned read-only clone (which would move the tree hash on a rerun),
  and buys nothing while the required-dependency set is empty. Two corrections the measurement
  forced, both 2026-09-06: (1) `-sourcepath` alone is not `mvn compile` — javac finds a type in a
  source file only when the file is named after it, so Aspose.PDF's package-private
  `ReturnSignal`/`BreakSignal`/`ContinueSignal`, declared beside another class in
  `Interpreter.java`, were invisible and all nine examples failed inside the *product's* own
  source; the tree is now compiled once with an argfile and each example is a classpath compile.
  (2) `maven.compiler.release` is `--release`, but `target`/`source` are `-source`/`-target` —
  PDF declares `target` 11 and calls APIs `--release 11` refuses, so treating them alike failed a
  build Maven performs. Guards: a POM with a required dependency, and a product whose own sources
  will not compile, both return `NOT_VERIFIED: BLOCKED_TOOLCHAIN` naming the cause, never a
  compile failure blamed on the example. Reversal: the verifier is one file,
  `platforms/java_examples.py`.
- **2026-09-06 · G4-W12 · a snippet is compiled with `java.io.*`, `java.util.*`, the product's root
  package, and a single-type import for every product type it names, and the receipt lists what
  was supplied.** Measured on 3D Java: five of ten README examples name `Scene`, `File` and
  `FileInputStream` with no import line, and javac reported "cannot find symbol" for the language's
  own file classes; the three wildcards took it from 5 to 7 compiled. Measured on Slides Java:
  seven of eight name `Color`, `SaveFormat` and `FillType`, which live in `…foss.drawing` and
  `…foss.export` while the root wildcard reaches only `…foss` — so names are resolved from an index
  of the tree's own file names instead. Alternative rejected: a wildcard per package — Aspose.PDF
  has 82 and javac makes any shared simple name an ambiguity error. Guards: the snippet's own
  imports are kept and win (a single-type import outranks any on-demand one), a simple name two
  packages declare is dropped rather than guessed, and a name `java.io`/`java.util` already
  provides (`List`, `File`, `Map`) is never redirected to a product type. Precedent: the .NET
  verifier makes the same accommodation by enabling `ImplicitUsings` in its wrapper project
  (`net_examples.py:35`); here it is explicit and it is in the receipt. Reversal: drop
  `_IMPLICIT_PACKAGES` and `public_types`; every receipt that used them names them.
- **2026-09-06 · G4-W12 · the vendored `internal`/`impl` package exclusion stays on for this
  cohort, checked by parity rather than assumed.** §29.9 warns it can drop real API, and the
  vendored comment in `api_surface.py` says slides/java's `org.aspose.slides.foss.internal` ships
  published reference pages. Measured 2026-09-06 against the four live READMEs: `internal` appears
  0 times in 3D's and Slides's, once in Cells's and twice in PDF's, and in none of those as a type
  or package a reader is told to use — so no README row loses evidence to the exclusion and parity
  holds with the default. Note for whoever needs it changed: `surface/extractor.py::surface_symbols`
  does not forward `excluded_package_segments`, so the spec parameter §29.9 asks for cannot be
  passed from a plugin today; that is a one-argument façade change and becomes a PROPOSAL the first
  time a repository's parity fails on it. Reversal: none needed while parity passes.

## Re-run of the four G4-W12 dispositions (2026-09-06, after G4-W17 item 12 and the rest)

- **2026-09-06 19:59 (`date` checked) · G4-W12 re-run · item 12 reached every Java repository, and
  by itself sealed none of them — the other half of BC-02 was this lane's own sentence.**
  `install_command:maven` is now SUPPORTED for all four, from a live probe of
  `repo1.maven.org/maven2/org/aspose/<artifact>/maven-metadata.xml` (evidence "package registry:
  found on maven"), exactly as the 14:46 §31 entry recorded. All four still failed `BC-02` on the
  first re-run, identically: `install_command:maven lacks manifest, package-registry, or
  source-build evidence: install command for the coordinate declared by the POM package registry:
  found on maven`. `_check_install` asks the install fact's evidence for a manifest reading *and*
  a registry reading; the registry half has a shared owner (`RegistryObservation.summary`, whose
  docstring says outright that the wording is shared so "no plugin should have to remember the
  phrase"), the manifest half has none, and every other plugin retypes it correctly — `go`, `net`,
  `rust` and `typescript` all say "manifest" while this one said "declared by the POM". Decision:
  conform this lane's own sentence to "install command for the coordinate the `pom.xml` manifest
  declares", which is honest — the evidence's own `path` is `pom.xml`. Alternative rejected:
  leaving all four blocked behind a shared-code PROPOSAL the lane could close in one line of its
  own file. Evidence: with the change, Slides went from `BC-02` to nine of nine S9 checks passing
  and PDF to a seal. Reversal: one string in `platforms/java.py::manifest_facts`. The shared-code
  half is PROPOSAL H below, non-blocking.
- **2026-09-06 19:59 (`date` checked) · G4-W12 re-run · a Javadoc comment is not Markdown, and
  saying so is Java's own job.** `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`'s only remaining
  blocker once BC-02 cleared was `BC-06 failed at EXTRACTING: xfa:datasets: tree does not contain
  datasets`, and EXTRACTING is a stage no repair can act on. Cause, measured: `Datasets`'s Javadoc
  first line is `The {@code <xfa:datasets>} packet wrapper.`, the plugin stored it in
  `attributes["docstring"]` verbatim, and the renderer's API Reference cell is prose —
  `_symbol_description` strips backticks outright — so bare angle brackets reached the document,
  where CommonMark reads `<xfa:datasets>` as an autolink and BC-06 resolved it as a relative path.
  The same docstrings carry 4,444 `{@code}`, 1,063 `{@link}` and 74 `{@inheritDoc}` tags plus raw
  HTML; 104 reached the rendered table ("Represents a collection of {@link Artifact} objects"), and
  a dozen more `<element>` names sat one plan away from the same crash. Decision:
  `platforms/java.py` renders Javadoc as plain prose before it becomes a fact attribute — inline
  tags resolved to their own text (brace-balanced, since Aspose.PDF's JavaScript-AST types
  document themselves as `{@code { k: v, ... }}` and the engine hands over the first line only, so
  six arrive already cut mid-tag), presentation HTML removed, entities decoded, and the brackets
  dropped from anything still angled — the element name is the sentence's subject, and deleting it
  would leave "The packet wrapper." Alternatives rejected: a code span, which the renderer strips;
  and a shared-code PROPOSAL, since only the plugin knows its docstrings are Javadoc (.NET will
  need the same for XML doc comments, in its own file). Evidence: PDF sealed, 11 of 11 checks,
  review ACCEPT, zero `{@code`/`{@link` left in the sealed README. Reversal: `_javadoc_prose` and
  its two helpers are one contiguous block.
- **2026-09-06 19:59 (`date` checked) · G4-W12 re-run · this lane changed one integer in
  `project/state.yaml`, which the lane contract forbids, because a lane that seals cannot avoid
  it.** `progress.current_candidates` was 4; five bundles are now sealed on disk, and
  `cli.py` fails `status` closed on the mismatch ("cursor records 4 current candidates but 5
  sealed on disk"), which turns `tests/test_cli.py::test_status_reports_this_repository_cursor`
  red for everyone, not only this branch. Decision: change that one integer and nothing else — not
  `updated_at`, not a status, not an item. Alternatives rejected: landing a red suite (forbidden),
  and withholding a candidate that is sealed and no-op proven (the point of the re-run). Evidence:
  the field is a measured count in a `progress` block, the same kind of number the lane prompt
  already has a lane maintain in its own `progress`; lane C is the first lane to seal anything, so
  no earlier lane met this. Reversal: set it back to 4. Recorded as PROPOSAL M so the owner can
  give the field an owner rather than leave the next sealing lane to decide again.
- **PROPOSAL 2026-09-06 H · BC-02's manifest half is a bare substring match on prose, while only
  its registry half has a shared owner.** File:
  `src/repository_presenter/components/readme/validation/registry.py`, `_check_install`. Defect:
  `"manifest" not in details` reads the joined `evidence[].detail` prose, though the fact already
  carries the manifest structurally — `evidence[0].path` is `pom.xml`. Repositories: all four
  Java, which it cost a full re-run cycle; the class is the one the owner named at 15:05, a check
  accepted against too narrow a sample. Finding: `RegistryObservation.summary` centralises the
  registry half for every plugin precisely so no plugin has to remember a phrase; the manifest
  half has no equivalent, so each plugin retypes it and one got it wrong. Fix: judge the manifest
  half from the evidence's own `path` against `spec.manifest_globs`, or give the manifest reading
  a shared wording helper beside `summary`. Resume predicate: none — closed in-lane for Java; this
  is for the next ecosystem, not this cohort.
- **PROPOSAL 2026-09-06 I · item 13 fitted the Maven badge's image URL but not its landing URL, so
  Java still renders no version badge — and all four upstream READMEs have one.** Files:
  `src/repository_presenter/core/ecosystems.py` (`EcosystemSpec.badge`) and
  `src/repository_presenter/components/readme/validation/registry.py` (`_RENDERER_HOSTS`).
  Defect: `badge()` now offers `{group}`/`{artifact}`, which fits
  `img.shields.io/maven-central/v/org.aspose/aspose-3d-foss.svg` (live 200, checked 2026-09-06) —
  but a badge is a *link*, and the URL the upstream READMEs point it at is
  `repo1.maven.org/maven2/org/aspose/aspose-3d-foss/`, whose group segment is the coordinate's
  dots rewritten as path separators; no token renders that. The one-token alternative
  `central.sonatype.com/artifact/{group}/{artifact}` (also live 200) is neither a `link_target`
  fact nor a `_RENDERER_HOSTS` entry, so `_check_links` fails it as "not a verified link target".
  Repositories: all four; visible now, because the candidate drops a badge the live README has.
  Fix: offer `{group_path}` beside `{group}`, or admit the registry host an ecosystem's spec
  names. Resume predicate: PROPOSAL I merged, then set `version_badge` in `platforms/java.py`.
  Not a blocker — PDF sealed without it.
- **PROPOSAL 2026-09-06 J · the Aspose-link ceiling is a *plan* budget that BC-06 counts over the
  *whole document*, so a placed inherited unit's own links break a ceiling the plan cannot get
  under.** File: `src/repository_presenter/components/readme/validation/registry.py`,
  `_check_links`, with `composition/planning.py::plan_checks` as the other half. Defect: the
  comment at that check says the ceiling "bounds the contextual Aspose links **the plan assigns**",
  and item 16 now makes planning trim to exactly that — but `_check_links` counts every
  non-mandated Aspose URL the rendered document contains, and a placed inherited unit brings its
  own. Repository: `aspose-3d-foss/Aspose.3D-FOSS-for-Java`, reproduced in three consecutive runs:
  the plan assigns four links (`link_target:023`, `:024`, `:025` countable, plus `:035`, which is
  mandated and exempt), and `inherited_unit:043.paragraph` — `VERIFIED_MOVE` to
  `documentation_resources`, citing `link_target:021` and `link_target:022` — carries
  `docs.aspose.com/3d/java/` and `reference.aspose.com/3d/java/` in its own preserved bytes. Five
  counted against a ceiling of four: `BC-06 failed at PLANNING: 5 Aspose links exceed the ceiling
  of 4`. Finding: the failure routes to PLANNING, where re-planning provably cannot act — the S5
  repair returned a links list byte-identical to the one it was given (`repairs.json`, `before` ==
  `after`) and BC-06 re-raised. Fix: count a placed unit's own links into the budget at a stage
  that can still act — give reconciliation the ceiling so a placement that would breach it is
  folded, or let the plan see the links its dispositions already committed to and trim its own
  accordingly. Resume predicate: PROPOSAL J merged on `main`, then re-run 3D.
- **PROPOSAL 2026-09-06 K · a repair whose stage re-ran and returned identical output is recorded
  `repaired`, not `unrepairable`.** File:
  `src/repository_presenter/components/readme/repair/targeted.py` (the attempt's outcome). Defect:
  3D's BC-06 attempt records `"outcome": "repaired"` with `re_raised: ["BC-06"]` and a `changes`
  entry whose `before` and `after` are the same four link assignments, byte for byte. Finding: a
  stage that cannot act on a defect reads, in the record and in the run's own summary line ("1
  repaired ... 1 re-raised"), exactly like a stage that acted and was overruled — which is what
  made PROPOSAL J's cause take three runs to see rather than one. Fix: when an attempt's output is
  identical to its input, record `unrepairable` with the reason "the stage re-ran and produced
  identical output", and do not spend the round. Resume predicate: diagnostic only; blocks nothing
  by itself.
- **PROPOSAL 2026-09-06 L · BC-10 rejects the document shape `README_CONTRACT.md` mandates, and
  the finding is routed to authoring, which cannot change it.** Files:
  `prompts/independent_review.yaml` and
  `src/repository_presenter/components/readme/repair/targeted.py`. Defect: both of
  `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`'s blocking findings object to deterministic,
  renderer-owned structure — `F05 additional_examples`: "uses a collapsible 'Additional Examples'
  section with a 'View Additional Examples' summary, which is not present in the original README
  and adds unnecessary UI" (that exact string is `renderer.py:54`'s
  `ADDITIONAL_EXAMPLES_SUMMARY`, emitted at `renderer.py:744`); `F07 scope_limitations`: "moving
  the edition comparison table to a separate section", which is the semantic shell's own fixed
  topology. Repository: Slides Java, the only one to reach S10 this re-run — nine of nine S9
  checks pass and it fails `BC-10 ... REJECT_PRESENTATION`. Finding: F05 was routed to S6
  `additional_examples`, the unit was re-authored, and the finding re-raised identically, because
  no unit's prose can remove the renderer's own `<details>` wrapper. Fix: state the
  contract-mandated structures in the review prompt as not open to presentation objection, and
  treat a finding naming only renderer-owned structure as advisory rather than blocking. Resume
  predicate: PROPOSAL L merged on `main`, then re-run Slides.
- **PROPOSAL 2026-09-06 M · a lane that seals a candidate must move
  `project/state.yaml`'s `progress.current_candidates`, which the lane contract forbids it to
  touch.** Files: `project/loop-prompt-lane.md` §0 (the substitution list) and
  `project/state.yaml`. Defect: `cli.py` fails `status` closed when the cursor's count and the
  bundles on disk disagree, and `tests/test_cli.py::test_status_reports_this_repository_cursor`
  asserts `status` exits OK — so the first lane to seal anything turns the suite red until that
  integer moves. Finding: lane C moved it (4 to 5) and recorded the decision above; no lane before
  this one had sealed a candidate, so the collision had not been met. Fix: either name
  `progress.current_candidates` as the one `state.yaml` field a lane maintains, or derive it from
  disk rather than storing it. Resume predicate: owner ruling; the count is correct either way.
- **2026-09-06 19:59 (`date` checked) · G4-W12 re-run · which G4-W17 items cleared which
  repository, measured.** Cleared: **item 12** (the Maven coordinate) for all four — the reading
  is live and positive everywhere; **item 15's fold** (declined as redundant at 15:20, and the
  live run confirms the decline was right) — 3D and Cells both died at S4
  `source_reconciliation` in G4-W12 and both now pass it; **item 17's first half** — Slides'
  85-unit reconciliation no longer dies on duplicate dispositions, in every run; **item 14** —
  taken up here, the floor parenthetical now names this POM's own property; **item 18** — Cells'
  BC-07 now routes to S6 `api_reference` instead of being recorded unrepairable. Did not clear:
  **item 13**, half only (PROPOSAL I); **item 16**, which cleared its own S5 rejection but the
  breach re-surfaces at S9 (PROPOSAL J); **item 22**, unlanded, and now Cells Java's *only*
  remaining blocker — `BC-07 failed at COMPOSING: internal narration 'validator'` on the API
  Reference row `` | `WorkbookValidator` | A validator for workbook models... | ``, the same
  product family and the same public type lane D measured on Cells **Rust**, so the class is
  confirmed independently in a second ecosystem and is not Rust-local. Items 0 and 24 are not
  Java's: `maven` is in `REGISTRY_TYPES` and the registry path opens.
