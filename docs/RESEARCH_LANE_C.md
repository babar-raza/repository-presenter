# lane-c decision log (append-only; entries in DECISION_LOG.md section 31 shape; the owner merges)

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

  **Demonstrated within the hour, on `main`.** PR #12 (`cd0bdfb`) and the primary's own
  `0089b6e` (Aspose.Cells for C++, item 24's second candidate) were both cut from a tree where
  `progress.current_candidates` was 4, and both set it to 5. Squash-merging them one after the
  other left one `5` and six bundles on disk, and `main` went red on
  `tests/test_cli.py::test_status_reports_this_repository_cursor` - a lost update on a
  hand-maintained counter, not a merge conflict, so nothing warned either author. Set to 6 here.
  This is the argument for deriving the count from disk rather than storing it: two producers
  incrementing the same integer will keep doing this every time two candidates land in one box.
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

## Second re-run of Cells Java alone (2026-09-06 23:06, after G4-W17 item 22 landed at `638a7ac`)

- **2026-09-06 23:06 (`date` checked) · G4-W12 second re-run · item 22 landed, is live, and does
  not clear Aspose.Cells for Java — the matched text is not the symbol name.** Measured on
  `origin/main` at `638a7ac` (`_NARRATION_PATTERNS` word-boundary matching plus the
  SUPPORTED-`public_symbol` last-segment exemption, both present and exercised): the transaction
  still ends `BC-07 failed at COMPOSING: internal narration 'validator'`; 8 of 9 blocking checks
  PASS, BC-10 and BC-11 PENDING, one repair round routed to S6 `api_reference` and the equivalent
  failure re-raised. The previous re-run's diagnosis (this log, 19:59) named the symbol name
  `WorkbookValidator` as the matched text; that half is genuinely fixed — `validator` is one
  continuous word inside `workbookvalidator` and no longer matches, and the backticked name is
  stripped by `_prose`'s code-span rule in any case. What actually matches is the *other* half of
  the same row: the standalone English word in `A validator for workbook models that produces
  validation messages.` — the repository's own Javadoc, verbatim from
  `src/main/java/org/aspose/cells_foss/validation/WorkbookValidator.java` line 9, carried as the
  `docstring` attribute of `public_symbol:org.aspose.cells_foss.validation.workbookvalidator` and
  rendered deterministically into the collapsed API Reference table at README line 350 (inside
  `<details>`, depth 1). `validator` occurs exactly once in the whole 452-line document, there.
  The last-segment exemption cannot reach it: it compares the phrase to symbol *names*, and no
  symbol is named `Validator`.
- **PROPOSAL 2026-09-06 N · a narration phrase that is the repository's own documented text,
  rendered deterministically from a fact, is not narration, and no repair can remove it.** File:
  `src/repository_presenter/components/readme/validation/registry.py`, the `matched` comprehension
  at ~line 869 (the `phrase not in symbol_names` exemption item 22 added). Defect: the exemption
  is anchored to a SUPPORTED `public_symbol` fact's *name* only; the same fact's `docstring`
  attribute is rendered verbatim by the renderer into the collapsed API Reference and is then
  scanned as if it were authored prose. Finding:
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` at `779c9640`, BC-07 `internal narration
  'validator'`, section `api_reference`; the phrase occurs in no content unit at all
  (`content_units.json` holds no occurrence of `validator`), so `targeted_repair` has nothing to
  revise and re-raises byte-identically — structurally unrepairable, the shape loop-prompt §3
  calls real repair work rather than a prose judgement call. Fix: extend that exemption from the
  symbol's name to the symbol's own documented text — a phrase whose only word-boundary
  occurrences fall inside the value of a SUPPORTED `public_symbol` fact's `docstring` attribute is
  the repository's vocabulary, not the pipeline's. Anchoring to the fact rather than to the API
  Reference *region* keeps the check at full strength: narration invented anywhere, that table
  included, still blocks, because invented text is in no fact. Mutation test: the same document
  with `this readme was generated by` injected into an API Reference row still fails BC-07.
  Alternative rejected: exempting the `api_reference` section wholesale (precedent exists two
  blocks above — the `line in api_lines and text in topics` heading exemption) — simpler, but it
  blinds the check to that section's authored intro prose. Second alternative rejected: rewording
  the Javadoc in `platforms/java.py`'s `_javadoc_prose`, which is in this lane's own paths and
  would have sealed the candidate inside the box — it falsifies the repository's own
  documentation to satisfy a check, which is patching around the defect (§2) and would degrade
  every Java candidate. Resume predicate: PROPOSAL N merged on `main`, then re-run `present` for
  Cells Java. Reversal path: drop the `docstring` clause and the exemption is item 22's again.

## Third re-run, 3D Java alone (2026-09-06 23:29, after G4-W17 item 32 landed at `63fbc2d`)

- **2026-09-06 23:29 (`date` checked) · G4-W12 third re-run · PROPOSAL J is closed: item 32 is the
  whole of what Aspose.3D for Java needed, and the candidate seals on the first pass.**
  `aspose-3d-foss/Aspose.3D-FOSS-for-Java` at `e308de58` is **SEALED and no-op proven** — 10 of 10
  blocking checks PASS with BC-06 among them, independent review `ACCEPT` with 0 findings and 7
  presentation advisories, repair rounds 1 with nothing to repair, `README.md` 187 visible lines of
  535, bundle state `READY_FOR_PROPOSAL`, 13 files. The immediate rerun in a fresh process
  reproduced the README digest `da0302d3…`, the validation digest `e850a885…` and the review
  digest `fdd39ae6…` byte for byte with **0 provider calls** (the sealing run made 28), and check
  11 is judged. Lane C's second seal; the portfolio's second Java candidate; `repository-presenter
  status` reads **7/34**.
- **Why it cleared, checked against item 32's own claim rather than assumed.** BC-06 counts Aspose
  links over the whole *rendered document*; item 16 had bounded only the plan's own `links` list.
  `inherited_unit:043.paragraph` is a VERIFIED_MOVE placed into `documentation_resources` and
  renders its own `docs.aspose.com/3d/` links verbatim — reconciliation's decision, which no
  re-ask of planning can withdraw — so the plan could sit at its ceiling of 4 and the document
  still count 5, with nothing left for a repair to trim. That was PROPOSAL J exactly. Item 32
  (`composition/planning.py`, `plan_checks`) now sums the Aspose links inside every placement whose
  outcome is `placed` and trims the plan's own list to `aspose_links_max` minus that count, so the
  plan reserves headroom for what is already committed to render. Measured result: BC-06 PASS with
  zero repair rounds spent on it, not a repair that finally succeeded.
- **2026-09-06 23:29 · `project/state.yaml`'s `progress.current_candidates` 6 → 7, by recount.**
  The narrow exception in `project/loop-prompt-lane.md` §0: `git fetch origin && git rebase
  origin/main` first — the branch moved from `63fbc2d` to `8b93070`, picking up two lane-d records
  landed meanwhile — then a fresh count of sealed bundles in that rebased tree (`status` reads
  `7/34`; `candidates/` holds 7 directories). Never read-and-increment, which is the lost update
  PROPOSAL M records. No other field or byte of `state.yaml` was touched.
- **Java cohort, final state for this lane.** 2 of 4 sealed — PDF (`099e70a8`) and 3D
  (`e308de58`). 2 dispositioned, each on exactly one named blocker: Cells on PROPOSAL N (BC-07
  matching the repository's own Javadoc), Slides on item 33 / PROPOSAL L (BC-10 rejecting
  renderer-owned structure). Both are one landed shared-code change away, and both predicates are
  now precisely diagnosed rather than merely named.

## Fourth re-run, Cells Java alone (2026-09-07 12:04, after PROPOSAL N landed at `94abe74`)

- **2026-09-07 12:04 (`date` checked) · G4-W12 fourth re-run · PROPOSAL N is closed: the docstring
  exemption is the whole of what BC-07 needed, and `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`
  clears it on the first pass.** Measured on `origin/main` at `869fcc7` (the unlock is `94abe74`,
  three commits back). The transaction that has ended `BC-07 failed at COMPOSING: internal
  narration 'validator'` in every earlier run now records **BC-01 through BC-09 all PASS** — pass 9,
  fail 1, pending 1 — with zero repair rounds spent on BC-07. `validator` still occurs exactly once
  in the 442-line document, in the collapsed API Reference row for
  `org.aspose.cells_foss.validation.WorkbookValidator`, whose description is the repository's own
  Javadoc carried as that fact's `docstring` attribute; it is now part of the joined
  `docstring_prose` the guard exempts. Item 22's third exemption source works exactly as its commit
  message claims. The repository reaches **S10, the independent review, for the first time**, and
  stops there: `BC-10 REJECT_FACTUAL`, 3 blocking findings, 5 advisory, repair rounds 2, no bundle
  sealed. Evidence: `evidence/build/lanes/lane-c/G4-W12-RERUN4.json`.
- **The three findings that survived, and why none of them is refutable by the code as written.**
  The reviewer raised 8; the reviewer-scope-defect machinery caught 5 of them — F02 (`the quote
  contains the literal value of SUPPORTED fact package:version`), F04 and F08 (`rendered_defect`),
  F05 and F06 (`absence_defect`, `which the candidate contains`). Re-running `origin/main`'s own
  `scope_defect`, `absence_defect` and `factuality_defect` against the three that blocked returns
  `None` for every one:
  **F01** `identity`/factuality, quote `The library is dependency-free and distributed under the MIT
  license.`, `fact_ids ['dependency:none']`, `absent []`. The sentence is the last of **content unit
  0, section `opening`, slot `opening`** — LLM-owned — not the `identity` section at all; repair read
  the reviewer's label, found `identity` in `_DETERMINISTIC_SECTIONS`, recorded *section identity is
  deterministic; its blocks change only when facts change*, and never re-asked the unit that holds
  the sentence.
  **F03** `dependencies`/factuality, quote `No required third-party package dependencies; in
  `pom.xml`, every `<dependency>` the POM declares is `test`, `provided` or optional.` — README line
  71, the deterministic renderer's rendering of SUPPORTED fact `dependency:none` and its own
  evidence detail. The alleged omission is contradicted nine lines below, at README lines 77–80:
  `### Development Dependencies`, `- `org.junit.jupiter:junit-jupiter 5.10.2``,
  `- `org.apache.poi:poi-ooxml 5.3.0``. Repair: *section dependencies is deterministic*.
  **F07** `scope_limitations`/factuality, `fact_ids []`, `absent []`. Its own `quote` is the sentence
  it says is omitted — content unit 25, slot `limitation:4`, `inherited_unit:041.list`, README line
  420. The repair routed correctly to S6, and the re-ask returned **byte-identical** text
  (`repairs.json` attempt `293af9f6…`, change `R01` on `units.4.text`, `before` == `after`), was
  recorded `repaired`, spent the round, and F07 re-raised. That is PROPOSAL K's symptom again.
- **PROPOSAL 2026-09-07 O · a *factuality* finding against a deterministic section is as
  unactionable as a presentation one, and is not recorded as the reviewer's own defect.** File:
  `src/repository_presenter/components/readme/review/independent/review.py`. Defect:
  `presentation_defect` — the rule that a deterministic section renders from facts and that no stage
  the loop can reopen would change it — returns `None` at its first line when
  `criterion != "presentation"` (line 333), so `dependencies` and `identity` are only protected
  against one of the nine criteria the schema allows. `rendered_defect` does not cover the gap
  either: `renderer_sentences` is scoped by construction to sentences the renderer writes *inside a
  section an LLM otherwise owns*. Repository and finding: Cells Java at `779c9640`, F03 above; the
  repair loop's own answer for it is *section dependencies is deterministic; its blocks change only
  when facts change*, which is the same sentence `presentation_defect` was written to encode. Fix:
  apply the deterministic-section rule before the criterion switch, as `absence_defect` and
  `excluded_evidence_defect` are already applied *whatever the criterion* (`scope_defect` lines
  568–576). Alternative rejected: leaving factuality out because "a factual error there is a
  factuality finding against the fact" (`presentation_defect`'s own docstring) — true, and F03 is not
  that: it cites two SUPPORTED facts and contradicts neither, asking for extra qualification of a
  fact's own rendering. Mutation test: a factuality finding against `dependencies` whose cited fact
  is `CONTRADICTED` must still block. Reversal: restore the criterion guard.
- **PROPOSAL 2026-09-07 P · a finding is routed to repair by the reviewer's `section_id` label, so a
  mislabelled but genuinely repairable finding is abandoned.** Files:
  `src/repository_presenter/components/readme/repair/targeted.py` and `repair/rounds.py`. Defect:
  when `section_id` names a deterministic section the repair stops, without asking whether the
  finding's `quote` — which `review_checks` has already located in the candidate character for
  character — falls inside an LLM-owned content unit. Repository and finding: Cells Java at
  `779c9640`, F01 above: labelled `identity`, quoted from unit 0 of `opening`. Fix: route by the
  quote's own unit when the quote locates in one, and fall back to the label only when it does not;
  the located quote is already a hard precondition of the reply being used at all. Alternative
  rejected: treating a label/quote mismatch as a reviewer-scope defect so the finding is recorded
  advisory — cheaper, but it discards a finding a repair could actually act on, and F01's substance
  (an unscoped absolute `dependency-free` in LLM-owned prose, which
  `prompts/independent_review.yaml` line 126 names verbatim as a REJECT_FACTUAL trigger) is worth
  one repair round. Reversal: drop the quote lookup and the label decides again.
- **PROPOSAL 2026-09-07 Q · a factuality finding that cites no fact and names no absent string
  passes every deterministic refutation by construction and blocks on the reviewer's prose alone.**
  File: `src/repository_presenter/components/readme/review/independent/review.py`; the unenforced
  instruction is `prompts/independent_review.yaml` lines 149–157. Defect: `factuality_defect`
  rejects a finding whose citations are all `inherited_unit` — *a factuality finding cites at least
  one product fact that contradicts the quote or should have supported it* — but returns `None` for
  a finding that cites **nothing at all** (line 224, `"no fact supports this claim" cites nothing,
  by definition`), which is strictly weaker than the case it rejects; and `absence_defect` reads only
  the `absent` array, so an omission asserted in `text`/`repair` prose with `absent []` is never
  checked. Repository and finding: Cells Java at `779c9640`, F07 above, `fact_ids []` and
  `absent []`, whose own quote is the sentence it calls missing. The same reviewer reply filled
  `absent` for F05 and F06 and both were refuted at once; the field the prompt requires is the only
  thing separating a caught defect from a permanent block. Fix: a factuality finding with empty
  `fact_ids` and empty `absent` rests on nothing the code can check and is recorded as the
  reviewer's own defect. Alternative rejected: detecting *lacks/omits/drops/replaces* in the
  finding's `text` and requiring `absent` — it would catch F03 as well, but reading the finding's
  prose to decide its scope is exactly what §27.2 RC8 forbids and what `absence_defect`'s docstring
  says nothing here does. Mutation test: a factuality finding citing one `CONTRADICTED` product fact
  must still block. Reversal: drop the empty-and-empty clause.
- **Java cohort, state after this run.** 2 of 4 sealed — PDF (`099e70a8`) and 3D (`e308de58`);
  `repository-presenter status` reads 7/34, unchanged, and `project/state.yaml` was not opened.
  Cells Java advanced from S9 to S10 and is dispositioned `BLOCKED_VALIDATION` on PROPOSALs O, P and
  Q together — all three findings must go for BC-10 to pass. Slides Java was **not run** and is
  unchanged on item 33 / PROPOSAL L; its F07 half still has no grounded quote. Cells' F07 above is a
  different finding that merely shares the rubric row (the schema constrains a finding id to
  `^F[0-9]{2}$` and both repositories' `scope_limitations` finding came back as `F07`): Slides' is the
  Enterprise cross-reference sentence, Cells' is the XML-mapper skeleton-class limitation. They are
  not evidence for each other.

## Fifth re-run, Cells Java alone (2026-09-07 12:54, after item 37 landed at `e81ffce`)

- **2026-09-07 12:54 (`date` checked) · G4-W12 fifth re-run · PROPOSAL O is closed: item 37 clears
  F01 and F03 exactly as written, and F07 still blocks — but the repository never reached the review
  to be judged there, because a new deterministic blocker stands four stages earlier at S6.**
  Measured on `origin/main` at `e81ffce`, which is item 37 itself (PR #25). Outcome:
  `DISPOSITION BLOCKED_AUTHORING`, not the `BLOCKED_VALIDATION` the fourth re-run recorded. S1–S5
  are clean (3 files, 3 of 3 examples executed, 2,829 facts, 18 sections planned) and **nine of ten
  S6 section-authoring jobs are accepted on their first attempt**; the tenth,
  `development_testing`/`summary`, is rejected twice and the run stops. Evidence:
  `evidence/build/lanes/lane-c/G4-W12-RERUN5.json`.
- **Item 37's reach, replayed against the three findings it was landed for.** The blocking findings
  recorded verbatim in `G4-W12-RERUN4.json` were run back through `e81ffce`'s own
  `renderer_owned_defect` and `factuality_defect` with this transaction's fact set — same repository,
  same revision `779c9640`, no provider call. **F01** (`identity`/factuality) and **F03**
  (`dependencies`/factuality) both now return *section … renders from facts under the contract's own
  checks*, so both are recorded advisory and neither blocks. **F07**
  (`scope_limitations`/factuality, `fact_ids []`, `absent []`) returns `None` from both: the section
  is not in `_DETERMINISTIC_SECTIONS`, the quote is neither a rendered heading nor collapsible
  chrome, and `factuality_defect` returns `None` for empty `fact_ids`. Item 37 is **necessary and not
  sufficient**: it is two thirds of what BC-10 needed here, and item 39 / PROPOSAL Q is the rest.
  This measures the rule's reach over the recorded findings; it is not a fresh reviewer read, which
  only a run that reaches S10 can give.
- **PROPOSAL P is off this repository's critical path, and that is worth recording rather than
  celebrating.** Item 37 clears F01 by *exempting* it — `identity` is a deterministic section, so the
  reviewer's own mislabel now buys the finding an advisory record — not by routing it to the unit
  that actually holds the sentence. The substance stands: `prompts/independent_review.yaml` line 126
  names *"dependency-free"* verbatim as a REJECT_FACTUAL trigger, the phrase is in content unit 0 of
  the LLM-owned `opening` section, and after item 37 no repair round will ever be spent on it. That
  is the right trade for a candidate that must not be blocked forever by a mislabel, and it is still
  a sentence the reviewer objects to surviving into a sealed README. Item 38 remains worth landing on
  its own merits; it is no longer a resume predicate for Cells Java.
- **PROPOSAL 2026-09-07 R · an identifier spelled verbatim inside a SUPPORTED fact the unit cites is
  not admitted, because `allowed_identifiers` adds a fact's whole value but its tokens only for kind
  `example`.** File: `src/repository_presenter/components/readme/composition/authoring.py::allowed_identifiers`
  (lines 814–820). Defect: the loop adds `fact.value` for every SUPPORTED fact and
  `identifier_tokens(fact.value)` only when `fact.kind == "example"`. For an `inherited_unit` the
  whole multi-line code block enters the allowed set — a string no prose can ever match — while the
  identifiers spelled inside it never do. Repository and finding: Cells Java at `779c9640`, S6
  `development_testing`/`summary`. The job wrote *…generate API documentation with mvn
  javadoc:javadoc which outputs to docs/apidocs/index.html*, citing `inherited_unit:044.paragraph`,
  `045.code_block` and `047.code_block`; `047`'s own SUPPORTED value is
  ```` ```bash / mvn compile / mvn clean package / mvn javadoc:javadoc   # generates docs/apidocs/index.html / ``` ````.
  Measured directly against this transaction's `facts.json`, no provider call: the carrier spells
  `index.html` verbatim → `True`; `whole carrier value in allowed` → `True`; `'index.html' in allowed`
  → `False`; `identifier_allowed('index.html', …)` → `False`; tokens of the carrier value
  `allowed_identifiers` never adds → `['index.html']`. The re-ask cannot pass, because the packet's
  evidence keeps spelling the token: four fresh samples of that one job across two invocations all
  returned it and all were rejected identically. Fix: admit `identifier_tokens(fact.value)` for a
  cited SUPPORTED fact whatever its kind, as `example` already gets — the same function feeds
  `renderer.py` line 110 and `validation/registry.py` line 514 (BC-04), so one change keeps authoring,
  rendering and BC-04 consistent and a fix in authoring alone would only move the rejection to BC-04.
  Alternative rejected: adding `index.html` to the common-noun set — it fits one sample and the class
  plainly continues (`docs/apidocs`, `target/classes`, every output path any upstream README's build
  block names), the shape items (20)/(22)/(26)/(36) each already paid for once. Second alternative,
  worth naming because it is the real risk: admitting *every* token of *every* SUPPORTED fact would
  also admit a stale symbol an upstream README mentions but the surface no longer carries — so scope
  the admission to the facts the unit actually **cites**, not the whole document's fact set. Mutation
  test: a token spelled in no fact at all, and a token spelled only in a fact the unit did not cite,
  must both still be rejected. Reversal: restore the `kind == "example"` guard.
- **What this run does not claim.** The fourth re-run reached S10 on this same repository at
  `869fcc7`, so the S6 rejection is new since that measurement, but no cause is claimed here. The one
  commit in `869fcc7..e81ffce` that shapes a job packet is `4cd1cff` (G5-W02, excluding
  `identity:revision` from every packet), which frees room in a bounded packet and could plausibly be
  what brought `inherited_unit:047.code_block` into this section's accepted set — untested, because
  the fourth re-run's transaction artifacts went with its worktree (`C:\w\c12r4` is gone) and the two
  packets cannot be compared. PROPOSAL R does not rest on that question: it is true of the code as
  written at `e81ffce` whatever put the fact in the set. Honest qualification on the reproduction
  too: the second invocation reused the cached S3, S4, S5 and the nine accepted S6 replies, so the
  packet the four samples answered was identical by construction rather than independently
  re-derived.
- **No third attempt.** Two invocations failed the same way for the same reason and the cause was
  narrowed to one line of shared code, so loop-prompt §5's prohibition applies and a third equivalent
  run was not made. Nor would a fresh full re-plan have paid: even past S6, F07 is proved above to
  still block BC-10 at this revision, so no seal was reachable this run by any path. The two
  measurements a run could still yield — PROPOSAL O closed, PROPOSAL R located — were both taken
  deterministically instead.
- **Java cohort, state after this run.** 2 of 4 sealed — PDF (`099e70a8`) and 3D (`e308de58`);
  `repository-presenter status` reads **7/34**, unchanged, `candidates/` holds no
  `aspose-cells-foss__Aspose.Cells-FOSS-for-Java` directory, and `project/state.yaml` was not opened.
  Cells Java is dispositioned `BLOCKED_AUTHORING` with resume predicate **PROPOSAL R and item 39 /
  PROPOSAL Q together** — R to leave S6 at all, Q for BC-10; naming either alone would be a resume
  predicate that cannot seal. Slides Java was **not run** and is unchanged on item 33 / PROPOSAL L.
