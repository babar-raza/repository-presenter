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
