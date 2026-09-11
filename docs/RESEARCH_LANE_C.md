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

## Sixth re-run, Cells Java then Slides Java (2026-09-11 12:52, after items 39 and 44 landed)

- **2026-09-11 12:52 (`date` checked) · G4-W12 sixth re-run · both halves of Cells Java's resume
  predicate are closed and neither is reached: a new deterministic blocker stands at S4, two stages
  before the earlier one, and Slides Java hits the identical blocker.** Measured on `origin/main` at
  `1fb995d`. Outcome: `DISPOSITION BLOCKED_RECONCILIATION` for both repositories. Evidence:
  `evidence/build/lanes/lane-c/G4-W12-RERUN6.json`. Cells Java (`779c9640`): S1–S3 clean (3 files,
  364 tree entries, 3 of 3 examples executed, 2,829 facts, investigation accepted first attempt),
  then `source_reconciliation` batch `reconciliation#1` — 40 of its 50 inherited units — returns
  `finish_reason: length` at `max_output_tokens=32000` (prompt 25,166 tokens, completion 32,000,
  550,721 ms) and the transaction ends. Slides Java (`a03b119a`) reproduces it exactly: 85 units,
  batches 40/40/5, batch 1 prompt 25,247 tokens, completion 32,000, 567,467 ms, same message.
- **Items 44 and 39 are both CLOSED, measured deterministically with zero provider calls.** Item 44
  (PROPOSAL R): `command_block_tokens` extracts `index.html` and `javadoc:javadoc` from the SUPPORTED
  carrier `inherited_unit:047.code_block`; `index.html` is in the allowed set and
  `identifier_allowed` returns `True`. The fifth re-run's own twice-rejected sentence — *…generate
  API documentation with mvn javadoc:javadoc which outputs to docs/apidocs/index.html* — yields
  exactly the two tokens above and **no token the guard now refuses**. Item 39 (PROPOSAL Q): the
  three blocking findings recorded verbatim in `G4-W12-RERUN4.json`, replayed through `1fb995d`'s own
  guards against this run's facts, are all reviewer-scope defects now — F01 and F03 by
  `renderer_owned_defect` (item 37, already closed), F07 by `factuality_defect` returning *a
  factuality finding names neither a product fact_id to contradict the quote nor an absent claim of
  missing text*. Neither was exercised in place: the run stops five stages before the first of them
  acts, so this measures the rules' reach over recorded findings, not a fresh review.
- **PROPOSAL 2026-09-11 S · `fact_ids` is bounded neither in element content nor in count, so the
  decoder can satisfy it with strings that name no fact and a sampled reply has an unbounded sink to
  run into.** Files:
  `src/repository_presenter/components/readme/reconciliation/dispositions.py::reconciliation_schema`
  (the `fact_ids.items` pattern, added by G4-W17 arrival item 40) and
  `prompts/source_reconciliation.yaml` (`output.schema…properties.fact_ids`, an array with no
  `maxItems`). Defect: the pattern `^(build_test_asset|…|third_party_notices):` constrains the
  prefix and nothing after it, so under strict guided decoding the cheapest legal string is the bare
  kind prefix; and the array has no upper bound, so nothing but `max_output_tokens` limits how many
  of them a reply may contain. Repositories and finding: Cells Java and Slides Java, both at S4,
  both at batch 1 of 40 units. **Measured by rebuilding Cells Java's own batch-1 request from its
  transaction through the same functions `run_round` calls and sending it — nothing written into the
  transaction, no tracked file edited:** at `max_tokens=32000` with an identical prompt token count
  of 25,166, one sample returns `finish_reason: stop` after **2,770** completion tokens and a
  complete 40-record reply — so 32,000 is a property of one sample, not of the request, and
  `jobs.py`'s *a re-ask under the same budget cannot help* is false for this job. That completed
  reply is rejected anyway: **all 27** of its `fact_ids` strings are bare `<kind>:` prefixes
  (`identity:`, `package:`, `link_target:`, `license:`, `example:`, `public_symbol:`,
  `install_command:`, `dependency:`) and `binding_errors` raises 8 *unknown fact ID* errors against
  it; a second sample at `max_tokens=8000` also completed, with 67 of 107 strings bare. Fix,
  **live-validated in the same way, with the schema mutated in memory only**: append `.+` to the
  pattern and give the array `maxItems`. That sample returned `finish_reason: stop`, 3,921 completion
  tokens, 40 records, **133 fact IDs and zero bare prefixes**, `binding_errors` down from 8 to 1 —
  the one remaining being a real citation of `inherited_unit:041.list`, a unit in batch 2, which is
  the ordinary shape the single permitted re-ask exists for — and `reconcile_checks` clean.
  `maxItems` rests on the fact_ids distribution of all nine sealed bundles on disk: mean 3.25 entries
  per record, maximum **72** in one record, maximum 2,792 characters of IDs in one record; 72 is the
  observed portfolio maximum, not a value fitted to this repository. Alternative rejected: lowering
  `_RECONCILIATION_BATCH` from 40 — the same 40-unit batch completes in 2,770 tokens on a fresh
  sample, so the batch is not what overflowed; shrinking it would lower the frequency of the failure
  without touching its cause and would cost an extra call per repository for nothing. Second
  alternative rejected: raising `max_output_tokens` above 32,000 — it moves the ceiling without
  bounding the only unbounded array in the reply, and the class returns at the next widening. Mutation
  test: a `fact_ids` entry of exactly `"<kind>:"` must be refused at decode time, an array longer than
  the cap must be refused, and a real ID must still pass. Reversal: drop `.+` and `maxItems`.
- **What this run does not claim.** The 32,000-token body itself was never read — the pipeline
  discards it (PROPOSAL T) — so *what* the runaway sample spent its tokens on is inferred from the
  three sampled replies above, not read from the failing one. The packet did also grow under item 40:
  measured across every sealed bundle plus this transaction, the S4 packet's citable `public_symbol`
  records go from 3 to 190 for Cells Java (9,788 → 41,625 characters), 5 to 248 for Slides Java, 3 to
  1,240 for the already-sealed PDF Java (11,419 → 222,612), while **shrinking** Cells-Rust's from
  2,084 to 219 — and Cells-Rust is the one repository `_RECONCILIATION_BATCH = 40` was calibrated and
  live-validated against (`docs/DECISION_LOG.md`, PHASE0/G, before item 40 landed). That is a real,
  measured calibration gap worth recording, but it is not offered as the cause: the replay shows the
  request completes comfortably, so the growth alone does not explain the ceiling.
- **PROPOSAL 2026-09-11 T · a `TruncatedOutput` discards the body every other rejection keeps.**
  File: `src/repository_presenter/core/llm/jobs.py` (the `finish_reason == "length"` branch). Defect:
  the `OutputRejected` path immediately below it calls
  `store.reject(request_sha256, ask, job, reply.content, rejection)` and keeps the rejected text; the
  truncation path records a ledger row and raises `JobError` without storing anything, so the one
  rejection class whose body is the whole diagnosis is the only one that throws it away. Evidence:
  Cells Java and Slides Java each produced 32,000 completion tokens at S4 this run and retained none
  of them; `calls/` holds only the accepted investigation call and the `TruncatedOutput` ledger row
  carries null token counts. The cause could only be measured by replaying the request by hand
  outside the pipeline, which this run did and should not have had to. Fix: call `store.reject` on
  the truncation path too. Reversal: drop the call. Blocks nothing by itself; it is what makes the
  next occurrence measurable instead of replayable-only.
- **PROPOSAL 2026-09-11 U · a test fixture's "disposable local repository" can silently be the
  repository the suite is running in, and it commits into it.** File:
  `tests/support.py::init_git_repository` and `::commit_all`. Defect: `init_git_repository` runs
  `git init` in `path` and asserts only on the exit status; when git resolves a *different*
  repository for that path, `git init` is a no-op re-init that still exits 0 (it prints
  `warning: re-init: ignored --initial-branch=main`), and the `git add .` / `git commit` that follow
  land on the surrounding repository's own HEAD while their asserts pass. Nothing in either helper
  checks that the directory it just initialised is the repository it then commits to. Observed twice
  in this run, in this worktree: during two full-suite runs, eight commits authored
  `Test <test@example.com>` with subjects `initial`, `seed` (x6) and `placeholder` were chained
  straight onto this lane's own commit `852047a`, moving `lane-c/G4-W12-RERUN6` to a fixture tree —
  `b96920b` deletes every tracked file of this repository, `8160636` carries `setup.py` and
  `aspose/example/__init__.py`, `6b97c65` carries the `README.md`/`LICENSE` pair
  `tests/test_cli.py::readme_only_upstream` (line 537) copies and commits under exactly that
  `placeholder` message. The branch was recovered with `git reset --hard 852047a`; nothing was lost
  and nothing was pushed in that state. **Mechanism proved in a controlled two-repository
  experiment, no test involved**: with `GIT_DIR` pointing at an outer repository, `git init -q -b
  main` inside a fresh directory returns 0 with that re-init warning, and the following
  `git add . && git commit` writes a commit on the *outer* repository's HEAD whose diff deletes the
  outer tree and adds the fixture's file — the exact shape of `b96920b`. What is **not** established
  here: which test, or which earlier test's leftover state, puts the suite into that condition.
  Running the three modules that call `commit_all` directly, and `tests/test_cli.py` whole, does not
  reproduce it; only a full-suite run did, and no `GIT_DIR`, `GIT_WORK_TREE` or `os.chdir` appears
  anywhere in `src/`, `tests/` or `scripts/`. The consequence is real either way and is not confined
  to a lane: `.githooks/pre-push` runs `scripts/ci_check.sh`, which runs the suite, so a push is the
  most likely moment for it to happen. It also made this run's own pre-push check red on its own
  account — the eight `tests/test_version_bump_discipline.py` failures of the serial run are all
  downstream of a hijacked `HEAD`, since that test reads `HEAD~1..HEAD` and the working tree against
  it. Fix: assert in `init_git_repository` that `git rev-parse --absolute-git-dir` under `path`
  resolves inside `path`, and re-assert it in `commit_all` before either commits — a guard, not a
  redesign; and scrub `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and `GIT_PREFIX` from the
  environment in `core/git_safety/git.py::run_git`, whose own docstring already promises the ambient
  configuration never leaks in. Mutation test: with `GIT_DIR` set to another repository,
  `init_git_repository(tmp)` must fail loudly rather than commit into it. Reversal: drop both
  guards. Raised as a lane PROPOSAL because `tests/` and `core/git_safety/` are not this lane's to
  edit.
- **Java cohort, state after this run.** 2 of 4 sealed — PDF (`099e70a8`) and 3D (`e308de58`);
  `repository-presenter status` reads **8/34**, unchanged before and after, `candidates/` holds no
  directory for either repository run here, and `project/state.yaml` was not opened. Cells Java and
  Slides Java are both dispositioned `BLOCKED_RECONCILIATION` with resume predicate **PROPOSAL S** —
  the first blocker this cohort has ever shared, and the reason it is recorded as a class rather than
  as one repository's accident. Slides Java's older blocker (item 33 / PROPOSAL L) was not reached
  and is neither confirmed nor refuted.

## Seventh re-run, Cells Java then Slides Java (2026-09-11 15:01, after the S4 enum landed at `352fd35`)

- **2026-09-11 15:01 (`date` checked) · G4-W12 seventh re-run · PROPOSAL S is CLOSED and Cells Java
  sealed at `ACCEPTED` for the first time — and the same commit that closed it made every
  repository's S4 unreproducible, so the seal cannot be no-op proven.** Measured on `origin/main` at
  `08307b9`, worktree `C:\w\c127`, environment hash `f4406f1b04d81ecdf2ea4e421776ef2be7f8cdc27090f395a815277a561fd411`
  confirmed identical to the primary's before any candidate work. Evidence:
  `evidence/build/lanes/lane-c/G4-W12-RERUN7.json`.
- **PROPOSAL S is CLOSED, live, at the stage it blocked.** Cells Java's `source_reconciliation`
  batch 1 — the identical 40-unit batch that returned `finish_reason: length` at 32,000 completion
  tokens and 550,721 ms in the sixth re-run — now returns `http 200`, `success`, **3,325 completion
  tokens in 64,411 ms**, and batch 2 completes in 942 tokens. The enum costs prompt tokens and buys
  the ceiling back: prompt 25,166 → **29,265** (+4,099 for 281 enum values), completion 32,000 →
  3,325. The repository ran to the end for the first time in its history: 50 dispositions
  (`OMIT_UNSUPPORTED` 12, `SUPERSEDE_REDUNDANT` 26, `VERIFIED_MOVE` 1, `VERIFIED_PRESERVE` 11), 17 of
  18 sections planned, 30 content units across 9 sections, README 241 visible lines of 452.
- **Cells Java: BC-01 … BC-10 all PASS, review `ACCEPT` with 0 blocking findings and 11 presentation
  advisories, bundle `candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Java/779c9640ee38ed9e80c53e8db1e850f6be24372f`
  state `ACCEPTED`, 14 files, 32 provider calls.** BC-10 is met on its v4 terms, not waived:
  `review.json`'s `second_reader` records `read: 2` with five corroborated finding IDs (PHASE1/F6).
  **BC-11 is `PENDING` and stays there** — *Fresh-process rerun is byte-identical with zero provider
  calls* is the one check the candidate does not meet, so `no_op_proof` is `null` and
  `repository-presenter status` counts it exactly as it should: *9 ever sealed, 9 integrity-valid,
  6 current-code reproducible* with the headline unchanged at **8/34**. Nothing was forced.
- **PROPOSAL 2026-09-11 V · `normalize()` writes a fact ID the S4 enum forbids, so every stored S4
  output is rejected on reuse and no repository's reconciliation is reproducible.** Files:
  `src/repository_presenter/components/readme/reconciliation/dispositions.py` —
  `citable_fact_ids()` (the enum, added by `352fd35`) against `normalize()`'s
  `entry["fact_ids"] = sorted(cited | set(rendering_fact_ids(destination, facts)))`. Defect:
  `citable_fact_ids` builds the enum through `bounded_records()`, which honours
  `core/facts.py::_EXCLUDED_FROM_PACKETS = {"identity:revision"}`; `rendering_fact_ids()` reads
  `facts.facts` directly and so returns `identity:revision` for the two deterministic sections whose
  `RENDERING_FACT_KINDS` include `identity` — `identity` (8 IDs) and `navigation` (5 IDs). `_parse`
  validates the **raw** reply against the enum (jobs.py line 359) and only then runs `checks`, which
  is `reconcile_checks` → `normalize`, mutating `output` in place (line 368); `run_job` stores the
  **normalised** output. So the live path accepts and the reuse path — `_parse` again, on the stored
  normalised output — rejects. Repositories and finding: Cells Java, `cache_stale OutputRejected` on
  batch 1 of every rerun, three times in this run's own ledger; batch 2, which places nothing into
  either section, reuses cleanly all three times.
- **Measured, zero provider calls, nothing written into the transaction and no tracked file edited:**
  the stored batch-1 output cites 49 distinct fact IDs, of which exactly one —
  `identity:revision` — is outside the 280-value enum, in three entries
  (`inherited_unit:001.heading` → `identity`; `inherited_unit:005.heading` and
  `inherited_unit:006.list` → `navigation`). Re-parsing it against the three schemas, in memory only:
  **(A)** the enum as shipped → rejected, 3 errors, all *`'identity:revision'` is not one of […]*;
  **(B)** the pre-`352fd35` `pattern` `^(build_test_asset|…|third_party_notices):`, which
  `identity:revision` matches → **accepted, 0 errors**, which is what makes this a regression of
  `352fd35` and not a pre-existing defect; **(C)** the same enum with `identity:revision` added, 280
  → 281 values → **accepted, 0 errors**.
- **It is a portfolio-wide class, not this repository's accident.** Every sealed bundle on disk cites
  `identity:revision` in its own `dispositions.json` — **10 of 10**, three entries each for nine of
  them and one for Aspose.Slides for Python — so every one of them would take the same
  `cache_stale` on its next re-seal, across four ecosystems and five families. Fix: `citable_fact_ids`
  must admit every ID `normalize()` can itself write — union in `rendering_fact_ids()` over the
  deterministic sections (equivalently today, the `_EXCLUDED_FROM_PACKETS` members the renderer
  cites). This weakens nothing the enum was built for: the runaway `352fd35` cured was bare `<kind>:`
  prefixes naming no fact, and `identity:revision` is a real, SUPPORTED fact the renderer reads
  directly. Alternative rejected: reverting to the `pattern`, which re-opens the 32,000-token S4
  truncation for the whole portfolio — the enum is right and is one value short. Second alternative
  rejected: dropping `identity:revision` inside `normalize`, which would make a supersession cite
  fewer facts than the section actually renders and weakens BC-05's own subject. Mutation test: a
  stored S4 output citing `identity:revision` must re-parse clean, and a bare `<kind>:` prefix must
  still be refused. Reversal: drop the union.
- **PROPOSAL 2026-09-11 Y · a candidate renders from the facts in extraction order and seals them in
  ID order, so a repository whose two orders differ can never re-render to its own sealed bytes.**
  Files: `src/repository_presenter/core/facts.py::FactsDocument.to_json` (which writes
  `sorted(self.facts, key=lambda f: f.id)`) against the rendering path, which takes the in-memory
  `FactsDocument` in the order extraction built it. Defect: the two orders are independent, and a
  rendered list follows whichever one it is handed. Repository and finding: Cells Java — the sealed
  `README.md` lists *Development Dependencies* as `` `org.junit.jupiter:junit-jupiter 5.10.2` ``
  then `` `org.apache.poi:poi-ooxml 5.3.0` ``, which is `pom.xml`'s own declaration order (lines 57
  and 65); `facts.json`, in the bundle and in the transaction alike, holds
  `dependency:development.org.apache.poi-poi-ooxml` before
  `dependency:development.org.junit.jupiter-junit-jupiter`, which is ID order. **Measured, zero
  provider calls:** re-rendering the sealed bundle through `tests/test_sealed_bytes.py`'s own
  `render_readme(entry, facts, plan, units, dispositions)` from the bundle's own artifacts produces a
  12-line unified diff that is exactly those two lines transposed, and nothing else in 27,000
  characters; the re-render is stable at ID order under `PYTHONHASHSEED` 0–4, so this is an ordering
  mismatch between two deterministic paths, not hash randomisation. This is why
  `tests/test_sealed_bytes.py::test_a_sealed_candidate_renders_to_its_own_bytes[aspose-cells-foss__Aspose.Cells-FOSS-for-Java]`
  fails, and it is independent of PROPOSAL V: V re-calls S4, Y transposes two lines with no call at
  all. Every other sealed bundle passes the same test because its extraction order and ID order
  happen to coincide; Cells Java is the portfolio's first repository where they do not. Fix: render
  from the facts in the order the seal writes them — sort once, at the boundary, so the bytes a
  candidate seals are the bytes its own artifacts render. Alternative rejected: writing `facts.json`
  in extraction order, which would make the sealed file's ordering an accident of the extractor and
  break every existing bundle's digest. Mutation test: a repository whose extraction order differs
  from its ID order must re-render to its own sealed bytes. Reversal: drop the sort at the render
  boundary.
- **Decision: the Cells Java bundle was NOT committed.** It is real, it sealed at `ACCEPTED`, and
  every measurement above is taken from it — but committing it would land a PR whose own suite is red
  on PROPOSAL Y, and both the renderer and `tests/test_sealed_bytes.py`'s `KNOWN_BLOCKED_STALE`
  registry are shared paths this lane does not own (§3). Loop-prompt-lane §2 is explicit for exactly
  this case: a failure class whose cause is in shared code is a `PROPOSAL` plus a disposition naming
  it as the repository's resume predicate — never a patch around it and never a widened path. So the
  bundle stays out of the commit and dies with the worktree; the transaction's own call store makes
  the re-seal cheap once V and Y land, and nothing about the seal was forced or faked to keep it.
  Alternative rejected: committing it and adding a `KNOWN_BLOCKED_STALE` xfail entry — that is an
  edit to `tests/` outside this lane's owned paths, and it would record a shared-code defect as this
  repository's known-stale accident.
- **PROPOSAL 2026-09-11 W · a `cache_stale` ledger row records `rejection: []`, so the one event that
  silently re-calls the provider says nothing about why.** File:
  `src/repository_presenter/core/llm/jobs.py` (lines 441–450). Defect: `_parse` returns
  `(None, rejection)` and the `cache_stale` row is written from `replace(reuse, …)` without the
  rejection list the `response_invalid` rows carry. PROPOSAL V above cost a by-hand replay to name a
  one-line cause the runner already held in a local variable. Evidence: this run's `calls.jsonl`, all
  three `cache_stale` rows, `"rejection": []`. Fix: carry `rejection` onto the row. Blocks nothing by
  itself; it is what makes the next reproducibility loss readable instead of replayable-only. Sibling
  of PROPOSAL T, and the same shape.
- **Lane E's PROPOSAL E3 did not materialise here, and this run adds two points to its table.** The
  S4 enum measured on these repositories' own `facts.json` through the same functions `run_round`
  calls: **Cells Java 281 values / 13,382 characters / a 15,398-character schema**, **Slides Java 337
  values / 15,970 characters / 18,009 characters**. Both are above lane D's validated 123 and below
  PDF for Python's 689, and both S4 calls returned `http 200` — no HTTP 400 naming the schema or the
  request size, at any batch. E3's open question is narrowed, not closed: the largest surfaces
  (PDF Java) remain unmeasured live.
- **Slides Java also clears PROPOSAL S and stops five stages later, on a new deterministic blocker.**
  `DISPOSITION BLOCKED_COMPOSING`. All three S4 batches return `http 200` — batch 1 prompt 29,717 /
  completion 3,208 / 63,848 ms, batch 2 29,861 / 3,546, batch 3 25,072 / 401 — against the sixth
  re-run's `finish_reason: length` at 32,000 and 567,467 ms on batch 1 alone. 85 dispositions
  (`VERIFIED_PRESERVE` 30, `SUPERSEDE_REDUNDANT` 22, `OMIT_UNSUPPORTED` 21, `VERIFIED_MOVE` 10,
  `VERIFIED_REWRITE` 1, `DEFER_UNRESOLVED` 1), 17 of 18 sections planned, 34 content units, README
  230 visible lines of 553, three repair rounds. Validation: **pass 8, fail 1, pending 2** — BC-01…05
  and BC-07…09 PASS, **BC-06 FAIL** at `COMPOSING`, and BC-10/BC-11 never judged. So **items 33, 37
  and 45 are again not reached**: BC-10 is `PENDING`, and this run neither confirms nor refutes
  PROPOSAL L for the third re-run running.
- **PROPOSAL 2026-09-11 X · a `VERIFIED_PRESERVE`d unit carries an intra-document anchor into a
  document that does not have the heading, and nothing before BC-06 can see it.** Defect: the
  candidate's section set is not the upstream README's, so an inherited unit preserved verbatim can
  name an anchor no candidate heading mints. Nothing at S4 or at rendering compares a preserved
  unit's own `#…` anchors against the headings the candidate will actually render, so the first stage
  that notices is BC-06 at S9, where it is a blocking failure with no repair path rather than a
  disposition the reconciler could have chosen. Repository and finding: Slides Java, BC-06
  `#building-from-source: no heading #building-from-source`. **Measured on this run's own artifacts,
  zero provider calls:** `inherited_unit:014.paragraph` is SUPPORTED, dispositioned
  `VERIFIED_PRESERVE` into `scope_limitations`, and its value ends *…control, [build from
  source](#building-from-source) rather than depending on `26.7.0`* — the anchor resolves in the
  upstream README, whose line 424 is `## Building from source`, and the candidate's own headings
  (rendered README lines 1–551) contain no such heading; its build-and-test section is `## Development
  and Testing`. `inherited_unit:015.paragraph` is preserved into the same section from the same
  passage and is clean. Fix: at S4, a unit whose text carries an intra-document anchor to a heading
  the plan will not render cannot be `VERIFIED_PRESERVE` — the disposition class that fits already
  exists and this repository already uses it once (`VERIFIED_REWRITE`); the anchor set is knowable
  deterministically from `section_ids()` plus the plan. Alternative rejected: rewriting the anchor at
  render time to the nearest candidate heading — it would silently re-point the maintainers' own
  sentence at a section they did not mean, which is a factuality risk BC-06 exists to stop, and it
  cannot be true in general (a candidate may render no equivalent section at all). Second alternative
  rejected: dropping the link and keeping the text, which changes a preserved unit's bytes without
  routing it through the rewrite path that exists precisely to record that. Mutation test: a
  preserved unit citing an anchor absent from the plan's heading set must not survive S4 as
  `VERIFIED_PRESERVE`. Reversal: drop the S4 guard. Not this lane's to write —
  `reconciliation/`/`composition/` are shared.
- **The lane prompt's own venv recipe does not reproduce the environment hash it requires.**
  §1.3 says install `requirements-lock.txt` plus `uv==0.12.9`, then `pip install --no-deps -e .`, and
  then confirm `f4406f1b…`. Done exactly, that yields a different hash: `requirements-lock.txt` —
  generated by `uv pip compile pyproject.toml --extra dev` — contains **no `pytest-xdist` and no
  `execnet`**, though `pyproject.toml`'s `dev` extra requires `pytest-xdist>=3.6` and §4 requires
  `pytest -n auto`. Installing `pytest-xdist==3.8.0` and `execnet==2.1.2` (and leaving the venv's own
  `pip==24.3.1` alone) reproduces `f4406f1b…` exactly. Recorded as a measurement for the owner, not a
  lane edit: `requirements-lock.txt` and the loop prompts are not this lane's to change.

## Eighth re-run, Cells Java then Slides Java (2026-09-11 17:41, after items 60 and 61 landed at `22c2e45`)

- **2026-09-11 17:41 (`date` checked) · G4-W12 eighth re-run · PROPOSAL V and PROPOSAL Y are both
  CLOSED, proven live on both repositories — and nothing sealed, because the shortcut that was meant
  to make the re-seal cheap could not restore the verdict it was meant to restore.** Worktree
  `C:\w\c128` off `origin/main` at `22c2e45`, which is items 60 and 61 themselves. Environment hash
  `f4406f1b…` confirmed before any candidate work, and the amended §1.3 recipe (`54417f9`)
  reproduces it first time, which closes this lane's own seventh-re-run finding about the recipe.
  Evidence `evidence/build/lanes/lane-c/G4-W12-RERUN8.json`.
- **PROPOSAL V is CLOSED, and the proof is the whole of what BC-11 asks for.** Not one `cache_stale`
  row exists among this run's own ledger rows: **58 `cache_reuse` rows and 0 `cache_stale` rows**
  across four invocations (Cells Java 13 + 16 + 15, Slides Java 14) — the five `cache_stale` rows
  the two copied ledgers carry are all the seventh re-run's, every one before `12:17Z`, and none
  after. Under `352fd35` the same S4 batch-1
  request took `cache_stale` on *every* reuse. The decisive measurement is the immediate
  fresh-process rerun of the first Cells Java run: **zero provider calls — 16 of 16 ledger rows
  `cache_reuse` — and a byte-identical document.** The entire diff of the two runs' stdout is two
  phrases, `provider calls 1` → `provider calls 0, model stored output reused`, at coherence and at
  review; every artifact digest matches, including `README.md` `63f14cf4…`, `validation.json`
  `647451d6…` and `review.json` `2a00a413…`. That is BC-11, obtained end to end through S11 on a
  document that simply does not pass BC-10. **The reproducibility defect is gone; this repository is
  now held by a different gate.**
- **PROPOSAL Y is CLOSED.** `render_readme` takes `facts.canonical()`, so the rendered order is the
  order the seal writes: Cells Java's *Development Dependencies* now render
  `` `org.apache.poi:poi-ooxml 5.3.0` `` before `` `org.junit.jupiter:junit-jupiter 5.10.2` `` —
  fact-ID order, matching `facts.json` — in both documents composed this run (replayed README lines
  79–80, fresh README lines 75–76), against the seventh re-run's sealed README, which had them in
  `pom.xml` declaration order. Proven for the rendering path; unproven for a *bundle* until the next
  Cells Java seal, because nothing sealed and `tests/test_sealed_bytes.py` has no bundle of this
  repository to exercise.
- **Item 61 costs exactly one fresh provider call per repository, once.** The coherence pass is one
  `section_authoring` call that "sees the rendered document"
  (`composition/coherence.py` line 3), so `RENDERER_VERSION` 19's canonical fact order moves its
  request digest a single time — Cells 54,649 ms, Slides 89,756 ms — and it reuses with 0 calls from
  the next run on. Measured, not inferred: the Cells rerun's coherence row is `cache_reuse`.
- **PROPOSAL U is CLOSED by `b63b949`.** `git rev-parse HEAD` recorded before and after both
  full-suite runs in this worktree: `22c2e45…` every time. The seventh re-run's fixture hijack did
  not recur.
- **The preserved call store cannot restore a seal, and PROPOSAL V is what destroyed this one.**
  `core/llm/jobs.py::CallStore.put` writes `calls/<request_sha256[:12]>.json` unconditionally — one
  body per request digest, last write wins; the ledger keeps every attempt's row, only the last
  attempt's body survives. **Measured on the preserved ledger itself, zero provider calls:** row 1,
  `09:36:51Z`, `source_reconciliation` batch 1, request `ff701248a1f0`, response `1aaaedf70f14`,
  3,325 completion tokens — the reply the seventh re-run's `ACCEPT` and its seal were built from.
  Rows 20/21, 39/40 and 59/60 are three `cache_stale` → `provider_call` cycles under the *identical*
  request digest, the last at `09:54:01Z` with response `1cdd5314fb51`. Every one of those three
  re-calls happened only because of PROPOSAL V. So replaying the preserved store on `22c2e45`
  reproduces row 60's sample, not row 1's: 50 dispositions of a different mix (`VERIFIED_PRESERVE`
  19 against the seal's 11, `SUPERSEDE_REDUNDANT` 17 against 26), a 466-line README instead of 452,
  and **BC-10 `REJECT_PRESENTATION` instead of `ACCEPT` with 0 blocking findings**.
  `bundle/seal.py::seed_call_store` does not cover the gap either: it seeds three jobs only, and
  only where the sealed ledger holds exactly one successful attempt for that job — which a
  repository that went through repair rounds never does. Recorded as a **measurement, not a
  proposal**: last-write-wins is defensible for a store whose purpose is to hold the reply the
  current rules accept, and the overwrite is only reachable through a defect like V. The operational
  conclusion is what matters to the sprint — **a preserved store guarantees a cheap deterministic
  replay, never the previous verdict.**
- **Cells Java: `DISPOSITION BLOCKED_VALIDATION` at S10, after two attempts and no third.** Run A
  replayed the preserved store (3 provider calls — the coherence pass and two reviewer reads, one
  before and one after repair) and stopped at BC-10 `REJECT_PRESENTATION` on F06,
  `presentation`/`development_testing`. Run B was its no-op proof. Run C discarded the store and
  composed fresh (18 provider calls, 2 rounds, the equivalent of `present --fresh`) and stopped at
  BC-10 `REJECT_FACTUAL` on F05, `factuality`/`api_reference`. **BC-01 through BC-09 PASS on both
  documents, as they did on the seventh re-run's**, so no third composition was attempted
  (loop-prompt §5) and the mechanism was changed instead — the two entries below.
- **BC-10 is now the only non-deterministic gate left on this repository, and it has returned a
  different verdict on each of the three documents ever composed for it.** README 241 visible of 452
  → `ACCEPT`, 0 blocking, 11 advisories, `second_reader.read` 2; 243 of 466 → `REJECT_PRESENTATION`,
  1 blocking, 7 advisories, read 2; 238 of 441 → `REJECT_FACTUAL`, 1 blocking, 6 advisories, read 1.
  **F06's subject is byte-identical in the document the same prompt accepted:** *"Build and test the
  project using Maven with JDK 17 or higher; run the test suite with mvn test, compile with mvn
  compile, package with mvn clean package, and generate API documentation with mvn
  `javadoc:javadoc`."* is line 446 of run A's README and line 436 of the seventh re-run's **sealed**
  README. One sample called it redundant against the renderer's own command blocks below it; the
  other did not raise it at all. Recorded as a measurement, not a proposal: whether a stochastic
  single-sample gate in front of every seal is acceptable is the owner's to decide. This lane's
  finding is narrower and checkable — it is now the *only* thing in the way, and this repository's
  deterministic evidence is clean.
- **PROPOSAL 2026-09-11 Z · a `factuality` finding may quote a deterministic table row that no
  content unit wrote, and no refutation covers it — the "the quote names a SUPPORTED fact BC-04
  already verifies" exemption is gated to `criterion == "presentation"`.** File:
  `src/repository_presenter/components/readme/review/independent/review.py`,
  `renderer_owned_defect`, at `verified = _quoted_verified_fact(finding, by_id) if presentation else
  None`. Repository and finding: Cells Java, F05, `factuality`/`api_reference`, quoting
  *`cells_foss.DiagnosticSeverity` | Represents the severity level of a diagnostic message. …
  `core.DiagnosticSeverity` | Represents the severity of a diagnostic entry.* and claiming *"the
  facts show they are internal and distinct from the public API enum"*. **Measured on this run's own
  artifacts, zero provider calls:** (a) both cells are facts —
  `public_symbol:org.aspose.cells_foss.diagnosticseverity` and
  `public_symbol:org.aspose.cells_foss.core.diagnosticseverity`, both `SUPPORTED`, confidence 1.0,
  evidenced at `src/main/java/org/aspose/cells_foss/DiagnosticSeverity.java` line 6 and
  `…/cells_foss/core/DiagnosticSeverity.java` line 6, *"enum; public by declaration"*, and README
  lines 363 and 383 render each name with that fact's own `docstring` attribute verbatim; neither
  package carries an `internal` or `impl` segment, so neither is excluded by the Java spec
  (`platforms/java.py::surface_facts`, §29.9). (b) The finding's own `absent` list names
  `DiagnosticSeverity-core`, which occurs **0 times** in the candidate and is not a fact ID, and
  `DiagnosticSeverity`, which is not a fact ID either. (c) **No unit wrote the quoted text**:
  `content_units.json` holds 25 units, `api_reference` has exactly two — slots `intro` and
  `hub:public_symbol:org.aspose.cells_foss` — and neither docstring appears anywhere in the file.
  (d) **The repair proved it**: attempt `2e839150456afaa024c3a134` routed F05 to
  `units[1].text` and the re-ask returned the same 157 characters byte for byte, because the
  sentence is not in that unit; it was recorded `repaired`, the finding re-raised, and the run
  stopped at `rounds 2` — the same shape as this lane's PROPOSAL N. (e) **Every refutation returns
  `None`** when replayed through this revision's own functions: `absence_defect`,
  `excluded_evidence_defect`, `rendered_defect`, `renderer_owned_defect`, `factuality_defect`.
  `api_reference` is not in `_DETERMINISTIC_SECTIONS` (`at_a_glance`, `badges`, `banner`,
  `dependencies`, `identity`, `installation`, `license`, `navigation`, `third_party_notices`), and
  `_quoted_verified_fact` is reached only for a `presentation` criterion. (f) **No new matching
  logic is needed — the existing matcher already resolves this quote; measured, zero provider
  calls:**
  called directly on F05, `_quoted_verified_fact(finding, by_id)` returns
  `public_symbol:org.aspose.cells_foss.core.diagnosticseverity`, polarity `SUPPORTED`, value
  `org.aspose.cells_foss.core.DiagnosticSeverity`, docstring *"Represents the severity of a
  diagnostic entry."*, and that docstring appears in no content unit. The only thing standing
  between that answer and a refutation is `if presentation`. **The gate is deliberate and it is
  right as far as it goes**, and the fix must not simply remove it: the function's own docstring
  justifies it with *"`ExportToCSV` writes JSON, not CSV"* — a real factuality defect in a unit's
  own prose that merely happens to name a verified symbol — and that must keep blocking. What the
  criterion does not distinguish is **where the quoted text lives**. The `ExportToCSV` case quotes a
  sentence a content unit wrote and can rewrite; F05 quotes a table row no content unit wrote and
  none can. Fix: give `renderer_owned_defect` the content units and reach `_quoted_verified_fact`
  for a factuality finding as well, **but only when no content unit carries the quoted text** — a
  deterministic test against `content_units.json`, which is exactly measurement (c) above and is
  the discriminator the criterion was standing in for. Alternative rejected: adding `core` to the Java spec's package exclusions so the second enum never
  becomes a fact — it is public by declaration, loop-prompt.md rule 8 requires the complete verified
  surface inside the collapsed reference, and trimming a true fact to satisfy a reviewer is
  weakening a check. Second alternative rejected: leaving it to `targeted_repair`, which is measured
  above returning the unit byte-identically. Mutation test: a factuality finding quoting a
  deterministic table row whose cells are a SUPPORTED fact's value and its own docstring, and which
  no content unit carries, must not block BC-10; a factuality finding against a unit's own prose
  that merely names a verified symbol must still block. Reversal: drop the criterion widening. Not
  this lane's to write — `review/` is shared.
- **Slides Java: `DISPOSITION BLOCKED_COMPOSING`, unchanged, and now confirmed at `22c2e45`.** One
  provider call (the coherence pass); 14 of 15 ledger rows `cache_reuse`, **including all three S4
  batches**, the first of which took `cache_stale` under `352fd35`. 85 dispositions in the same mix
  as the seventh re-run (`VERIFIED_PRESERVE` 30, `SUPERSEDE_REDUNDANT` 22, `OMIT_UNSUPPORTED` 21,
  `VERIFIED_MOVE` 10, `VERIFIED_REWRITE` 1, `DEFER_UNRESOLVED` 1), 17 of 18 sections, 34 units,
  README 230 visible lines of 553 (`151e55bc…`), validation **pass 8, fail 1, pending 2** — BC-06
  `FAIL` at `COMPOSING`, `#building-from-source: no heading #building-from-source`, the identical
  blocker at the identical stage. **PROPOSAL X is neither closed nor superseded by `22c2e45`** and
  remains this repository's single recorded resume predicate; items 33, 37 and 45 are not reached
  for the fourth re-run running, so PROPOSAL L is again neither confirmed nor refuted.
- **Java cohort, state after this run.** 2 of 4 landed — PDF (`099e70a8`) and 3D (`e308de58`).
  `repository-presenter status` reads **8/34** before and after (*9 ever sealed, 9 integrity-valid,
  6 current-code reproducible, 0 independently accepted*), `candidates/` holds no directory for
  either repository run here, and `project/state.yaml` was not opened. Cells Java is
  `BLOCKED_VALIDATION` on **PROPOSAL Z**; Slides Java is `BLOCKED_COMPOSING` on **PROPOSAL X**.
