# Lane B decision log (append-only; entries in DECISION_LOG.md section 31 shape; the owner merges)

Lane: `lane-b` (project/lanes/lane-b.yaml). Prompt: project/loop-prompt-lane-b.md.

- **2026-09-06 · LANE-B-00 · the lane's Rust toolchain lives under `C:\tools\rp-toolchains\rustup`,
  not `runs/toolchains/`.** `RUSTUP_HOME` is `...\rustup\rustup-home`, `CARGO_HOME` is
  `...\rustup\cargo-home`, cargo is called by absolute path, and `rustup-init` ran
  `-y --profile minimal --no-modify-path --default-toolchain stable`, so no PATH or profile changed.
  Alternative rejected: `runs/toolchains/`, as G4-W16's parenthetical says. Evidence: `runs/` is
  gitignored disposable run state, so any clean re-downloads the toolchain inside W16's 2-hour box,
  and OWNER-06's GCC/Ninja already sit under `C:\tools\rp-toolchains` with `TOOLCHAIN_PATHS.txt` as
  the machine's toolchain registry; LANE-B-00's text (2026-09-06) names this root and is the later of
  the two. Reversal: repoint both variables at `runs/toolchains/` and re-run `rustup-init`; only the
  LANE-B-00 receipt records the path.
- **2026-09-06 · LANE-B-00 · OWNER-06's resume predicate is reproduced independently, not taken on
  trust.** The owner marked it `SATISFIED` in `state.yaml` at 81a10ac on the reviewer session's own
  probe; LANE-B-00 rebuilt the probe from scratch — `cmake 4.4.1 -G Ninja` configuring, building and
  running C++20 with `g++.exe` 16.2.0 and `ninja` 1.13.2 from `TOOLCHAIN_PATHS.txt`, three steps at
  exit 0, the binary printing `cxx202002 total=12`. Alternative rejected: read the file's `verified`
  line and move on. Evidence: LANE-B-00's own text says "verify", and a probe that uses
  `std::integral` and `std::views::filter` makes C++20 a compile requirement, not a claim. Reversal:
  none needed; G4-W13's remaining wait is G4-W10 and G4-W09.
- **2026-09-06 · LANE-B-00 · `pytest -n auto` is nondeterministic on a developer machine that has
  real `GPT_OSS_*` credentials, and the hosted matrix is the honest verdict.** Six local runs of the
  same tree gave 503 passed; 501 passed + 2 errors; 500 passed + 3 errors + 1 failed; 500 passed +
  2 errors — a *different* subset of `tests/test_cli.py` each time, every one an LLM output
  rejection at fixture setup ("output rejected twice ... fact format:output.glb is UNRESOLVED"),
  never an assertion about this item. Diagnosis: `GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY` are set in
  this machine's process environment, so those fixtures compose against the real gateway; `ci.yml`
  sets neither, so hosted CI takes the deterministic path and PR #1 passed 3.11, 3.12 and 3.13.
  Alternative rejected: repair the fixtures — the cause is in `composition/` or `prompts/`, which
  the lane must never edit, and this item adds no Python. Reversal: the primary loop owns it; a
  cheap fix would be to unset both variables for the suite, or gate those fixtures on the fake
  gateway, so the local run measures the code rather than the model. Control: with both variables
  unset the suite passed 503/503 first attempt, which is what identifies the gateway as the cause.
- **2026-09-06 · LANE-B-00 · the lane's `tsc` is warmed now, into a disposable npm profile under
  `C:\tools\rp-toolchains\npm`.** `npm_config_prefix` and `npm_config_cache` point there, so nothing
  lands in the user profile and no PATH is edited; G4-W14's verifier calls `tsc` by absolute path or
  `npx.cmd` against that prefix. Alternative rejected: let `npx typescript` download inside G4-W14's
  2-hour box. Evidence: RESEARCH section 28.12 point 6 says provision toolchains before the cohort
  item that needs them, never inside its box. Reversal: delete the directory; `npx typescript` still
  works, at the cost of a download in the box.
- **2026-09-06 · G4-W14 · the TypeScript spec registers itself from its own plugin module; the lane
  never edits `core/ecosystems.py`.** `platforms/typescript.py` builds `TYPESCRIPT` and calls
  `SPECS.setdefault("typescript", TYPESCRIPT)` at import; `plugin_for(ecosystem)` (`cli.py:345`)
  imports that module before `select_examples` or the renderer ever calls `spec_for`, so the
  vocabulary is registered by the time anything asks for it. Alternative rejected: add the spec to
  the `SPECS` literal the way .NET's was added at G4-W11 - `core/` is outside the lane's owned paths
  (loop-prompt-lane-b section 3) and a pull request touching it would touch a path the lane does not
  own. Evidence: `SPECS` is annotated `dict[str, EcosystemSpec]` and deliberately not `Final`, unlike
  `PYTHON` and `NET` beside it, and `ecosystems.py`'s own docstring says "Adding an ecosystem is a
  spec, a verifier, and a negative-control test - never an edit to a shared file", which a literal
  dictionary cannot honour. Reversal: move the one line into the literal; nothing else changes.
  **PROPOSAL (primary loop, `core/ecosystems.py`):** let `spec_for` discover a `SPEC` attribute on
  `platforms/<ecosystem>.py` the way `registry.py` discovers `PLUGIN`, so registration does not
  depend on import order. Until then a consumer that renders a TypeScript entry without going
  through `plugin_for` first would raise `ConfigError`; no such path exists today.
- **2026-09-06 · G4-W14 · a TypeScript symbol is public only if the package's entry point re-exports
  it.** `typescript_barrel.reexported_names` walks the barrel graph (`export { A } from`,
  `export * from`, local declarations) and `typescript.py` keeps only symbols whose own name is in
  that closure, renaming them to the name a consumer writes. Measured: Aspose.3D for TypeScript
  extracts 153 types from 151 files and re-exports 81 names, which becomes 1034 public-symbol facts
  (types and their members); Aspose.Cells re-exports 43 and yields 353. Alternative rejected:
  publish every `export`, as C# publishes every `public`. Evidence: TypeScript has no visibility at
  module scope - a file says `export` so a *sibling* can import it - so the unreached types are
  internals a consumer cannot name, and an API Reference listing them would be wrong in the
  direction the contract cares about. Reversal: drop the filter in `surface_facts`; the extractor
  call is unchanged.
- **2026-09-06 · G4-W14 · the declared entry point is mapped through `outDir`/`rootDir` back to
  source, and an entry point that re-exports nothing is not one.** Aspose.3D declares
  `main: dist/index.js` and `types: dist/index.d.ts` and ships neither (`dist/` is build output);
  `tsconfig.json` declares `rootDir: ./src` and `outDir: ./dist`, so the barrel resolves to
  `src/aspose/threed/index.ts`. Aspose.Cells declares `main: index.ts`, which is a demo script that
  constructs a workbook and logs - its barrel is `aspose_cells/index.ts`. Alternative rejected: the
  vendored `_detect_js_root`, which returns `repo/src` for 3D (no barrel there) and the repository
  root for Cells (tests, examples and the demo included). Evidence: both measured 2026-09-06 on the
  pinned clones; the `aspose_org_upstream_issues` digest already records 3D's "declared `main`/
  `types` entry point is never produced by the real build" as a defect of the repository. Reversal:
  call `package_root.detect_package_root` instead and accept both regressions.
- **2026-09-06 · G4-W14 · an example's verdict is read from the diagnostics in its own file, and the
  host surface it assumes is supplied rather than counted against it.** `tsc --noEmit` runs with the
  package's own `target` and `moduleResolution`, an ES module (a README may `await` at top level),
  `DOM` appended to its `lib`, and a generated `rp_host_environment.d.ts` declaring Node's globals
  and built-in modules as shorthand ambient modules. Measured before the fix: of 3D's nine examples,
  three failed on `TS2584: Cannot find name 'console'` (the package declares `lib: ["ES2020"]`) and
  one on `TS2307: Cannot find module 'fs'` (no `@types/node` in the check); after it, 8 of 9 pass
  and the one failure is real - example 2 is `scene.save('model.stl', 'stl')` with no `scene` in
  scope, a README fragment presented as an example. Alternatives rejected: `npm install` the
  repository's dependencies inside the box (RESEARCH 28.12 point 6 forbids it), and letting a
  library-side diagnostic condemn an example (45 such on Cells, none in an example). Evidence: the
  shim declares only the *host*; no assertion in it can make a package member appear, so a false
  claim about the package still fails - the negative control in
  `test_typescript_examples.py` proves it. Reversal: drop `_HOST_SOURCE` and the `DOM` lib.
- **2026-09-06 · G4-W14 · the TypeScript runtime floor is `engines.node`, not the `typescript`
  devDependency.** Neither cohort repository declares `engines`, so neither renders a Native and
  System Requirements line. Alternative rejected: report the `typescript` devDependency range as the
  floor, which is what `project/portfolio-census.json` recorded ("ts ^5.8.3", "ts ^5.9.3"). Evidence:
  `typescript` is a build tool the *repository* uses; a consumer of a published npm package installs
  no compiler, so rendering it as a requirement would be false. It still appears, truthfully, under
  Development Dependencies. Reversal: point `floor_fact_id` at a `package:typescript` fact and emit
  it from `devDependencies`.
- **2026-09-06 · G4-W14 · PROPOSAL (primary loop, `extractors/surface/extractor.py`): `_KINDS` has
  no entry for `abstract_class_declaration`, so an abstract class is `unknown`.** Aspose.3D for
  TypeScript declares 8 and 2 of them are in the public surface; the renderer's `_public_type_count`
  counts only `class` and `enum`, so its public-type count understates the reference by 2. The lane
  cannot fix it: `_KINDS` is the shared façade, and the raw node type is gone by the time a
  `SurfaceSymbol` reaches a plugin. Resume predicate: `_KINDS` maps `abstract_class_declaration` to
  `class`; then re-run the two TypeScript repositories.
- **2026-09-06 · G4-W14 · PROPOSAL (primary loop, `composition/renderer.py`): `_IMPORT` is
  Python-shaped, so no TypeScript example ever matches an `import_path` fact and the Installation
  section renders no "Verify the install" block.** The pattern is
  `^\s*(?:import|from)\s+{module}\b`; TypeScript writes `import { Scene } from '@aspose/3d'`, where
  the module follows `from`, in quotes. The plugin emits the `import_path` fact regardless, because
  the module specifier is true about the package. Resume predicate: `_IMPORT` also matches a quoted
  specifier after `from`; then the block renders for any ecosystem whose examples import that way.
- **2026-09-06 · G4-W14 · `tests/.../platforms/test_registry.py` is the one file outside the lane's
  `owned_paths` this item changes, and the change is the assertion about the lane's own
  registration.** Two lines read `known_ecosystems() == ("net", "python")`; discovery is by module
  name, so the moment `platforms/typescript.py` exists they are false. Alternative rejected: a
  PROPOSAL and a disposition for the whole cohort - the item's acceptance requires hosted CI green,
  and no TypeScript module can ever be green while a shared test enumerates the ecosystems
  exhaustively, so that reading would make the lane's own charter unsatisfiable. Evidence: the
  comment on line 16 records ".NET joined at G4-W11" in the same place, so the primary loop treats
  this literal as the registering item's to update. Nothing else in the file moved, and no shared
  behaviour changed. A second assertion was added, that `typescript_barrel` is not an ecosystem, to
  keep the file's own point (a helper module beside a plugin exposes no `PLUGIN`) true for the two
  helper modules this item adds. Owner: fold this line into `owned_paths` or say the lane must ask.
- **2026-09-06 · G4-W14 · the hosted runner's `tsc` is 7.0.2, and it caught a rule that would have
  passed every example silently.** The first hosted run failed both real-compiler tests: GitHub's
  image has `tsc` on `PATH` (this machine has none, so the registry path is used), and on
  TypeScript 7 a `tsconfig.json` beside a file named on the command line is `error TS5112` - the
  run exits 1 having checked nothing, and the diagnostic carries no file. The verdict rule read
  only *filed* diagnostics, so it saw none in the example and called the negative control a pass.
  Two fixes, one each: the repository's configuration file is no longer staged (its options are
  read from the clone and passed as flags), and a non-zero exit with no filed diagnostic at all is
  `NOT_VERIFIED` - a compiler that refused checked nothing, and nothing checked is not a pass
  (section 29.6 E5). Alternative rejected: pin the assertion to `tsc 5`, which would have hidden
  the rule's gap behind a version. Evidence: the failing hosted job, and the new test that stages a
  configuration file deliberately and asserts the outcome is never `EXECUTED`. Reversal: none
  wanted; the local run (5.9.3) and the hosted run (7.0.2) now agree.
- **2026-09-06 · G4-W14 · a compiler is qualified by driving it, not by reading its version.**
  Removing the staged `tsconfig.json` was not enough: tsc 7.0.2 still refused the verifier's
  options and still exited non-zero with no filed diagnostic, so every example on the hosted runner
  came back `NOT_VERIFIED` and the three tests that assert a real verdict failed. The verifier now
  drives the compiler once per run on a file that cannot fail, with exactly the flags the examples
  will use (`probe_compiler`): a refusal blocks every candidate with what the compiler said, which
  is the honest answer for a compiler this lane has not qualified. The tests that need a *working*
  compiler skip on a refusal, and one test that runs wherever any `tsc` exists asserts the
  behaviour in both directions - `EXECUTED` when it checked, `NOT_VERIFIED` naming the refusal when
  it could not, never `EXECUTED` because a refusal was silent. Alternative rejected: chase tsc 7's
  option surface inside the box - the lane qualified 5.9.3 in LANE-B-00 and the receipt says so;
  guessing at a compiler nothing has measured would put an unmeasured claim in a sealed candidate.
  Resume predicate for TypeScript 7: run `probe_compiler` against it, read the refusal it prints,
  and adjust `_flags`; the receipt will name the option.
- **2026-09-06 · G4-W14 · DISPOSITION · `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at
  `7b95970` - `BLOCKED_RECONCILIATION`.** Everything up to S3 holds: 190 tree entries, 1178 facts
  (1034 public symbols, 11 dependencies), 9 examples of which 8 type-check and the ninth is a real
  README fragment. S4 `source_reconciliation` rejected its own output twice and the transaction
  reported rather than sealing: five inherited units are placed into `installation` and `license`,
  and `rendering_fact_ids` finds nothing for either - `install_command:npm` is CONTRADICTED because
  npm has no `@aspose/3d`, and the repository ships no licence file at all (the preflight's
  "required rows without evidence: license"). Both are true statements about the repository, and
  both are conditions the .NET cohort meets the same way. The failure class is the job's, not the
  ecosystem's: the model must answer `OMIT_UNSUPPORTED` or `DEFER_UNRESOLVED` for a unit whose
  section cannot render, and it answered with a placement twice. Resume predicate: the
  `source_reconciliation` prompt makes the empty-section rule answerable in one attempt (a
  `prompts/` change the lane must never make), or the repository publishes to npm and adds a
  licence file; then re-run `present --repo aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`.
  **PROPOSAL (primary loop, `prompts/source_reconciliation.yaml`):** the rejection text already
  names the only two admissible dispositions; giving the job the set of sections that render
  nothing *before* it answers would close this in one round for every ecosystem.
- **2026-09-06 · G4-W14 · DISPOSITION · `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` at
  `fc18650` - `BLOCKED_ENVIRONMENT (Windows MAX_PATH)`.** Facts and examples are complete and
  clean: 451 facts, 353 public symbols, 3 of 3 examples type-check, and no required contract row is
  without evidence. The transaction then dies in `core/llm/jobs.py:113`, writing
  `runs/transactions/aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript/<revision>/calls/<sha24>.rejected-1.json`
  - measured at **261** characters from this lane's worktree, one over Windows' 260-character
  limit, so `mkdir` succeeds and `write_bytes` raises `FileNotFoundError`. The census's note that
  this repository's clone failed twice with `invalid index-pack output` did **not** reproduce: it
  cloned cleanly at `fc18650` on the first attempt, twice. Workaround attempted and rejected:
  `subst`-ing the worktree to `W:` shortened the path but the editable install resolves the root
  back to its real `D:\...` location, so the same 261-character path was written. Resume predicate:
  run the transaction from a checkout whose path leaves room for that name (the primary checkout's
  root is 58 characters shorter than this worktree's), or enable Windows long paths. **PROPOSAL
  (primary loop, `core/llm/jobs.py`):** `CallStore.reject` is the only writer whose name carries a
  `.rejected-<n>` suffix; a shorter name, or opening through an extended-length path, removes a
  whole class of Windows-only transaction deaths that has nothing to do with any repository.
- **2026-09-06 · G4-W14 · DISPOSITION · `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` -
  `DISABLED_UPSTREAM`.** `data/registry.json` records `mode: disabled` and
  `project/portfolio-census.json` records `status: NOT CLONED`; the lane file's own repository list
  says "disposition only". No clone was attempted and no fact was read. Resume predicate: the
  registry entry's mode becomes `dry_run` and the repository clones; the plugin and verifier this
  item lands need no change to take it.
- **2026-09-06 · G4-W13 · C++'s install command is the source build the verifier itself drives, and
  it stays UNRESOLVED.** `install_command:cmake` carries
  `cmake -S <the manifest's directory> -B build` and `cmake --build build`, evidenced by the
  manifest and by the `RegistryProbe`'s own reading; `registry_facts` calls `observe("cpp", name)`,
  which makes no network call at all because `REGISTRY_TYPES` has no `cpp` entry, and re-issues
  the fact UNRESOLVED with that reading appended. `CPP.registry` is the phrase "any package
  registry" so the only sentence the renderer builds from it - "could not be confirmed on any
  package registry at this revision" - reads correctly; `version_badge` is empty, so no badge can
  render. Alternative rejected, and measured first: writing no `install_command` fact at all,
  which is what the first pass did. Evidence: with no such fact, `rendering_fact_ids` finds
  nothing for `installation`, and `source_reconciliation` rejected its own output twice on both
  Cells and Email with "section installation renders nothing for this repository" - the plugin was
  contributing to a failure whose cause is elsewhere. The UNRESOLVED fact does not fix that (the
  section still needs a **SUPPORTED** install command), but it states what is true and puts the
  real commands in the document. Reversal: drop the fact and the `observe` call.
- **2026-09-06 · G4-W13 · a C++ symbol is public only if a consumer may include the header it is
  declared in.** `cpp.public_symbols` drops every symbol whose evidence path has a directory
  segment named `internal`, `_internal`, `detail`, `details` or `impl`, and keeps a namespace only
  while something public is still declared inside it, re-evidenced at the first such declaration.
  Measured: Aspose.PDF for C++ extracts 2044 symbols of which 393 come from `include/internal/`
  (they surface as a `foundation.*` namespace no consumer can name), and Aspose.Slides 3243 of
  which 401 come from `include/Aspose/Slides/Foss/_internal/`; after the filter, 1651 and 2845.
  Alternative rejected: rely on the vendored engine, which already has a C++-only `internal`
  segment rule. Evidence: that rule computes a `visibility` field the shared façade
  `surface/extractor.py` never reads, and upstream lists `_internal` in `_EXEMPT_PRIVATE_DIRS`, so
  neither tree was filtered at all. Reversal: drop the call in `surface_facts`.
  **PROPOSAL (primary loop, `extractors/surface/extractor.py`):** `surface_symbols` discards the
  `visibility` key `api_surface.extract_api_surface` returns, so every ecosystem publishes what the
  engine already marked internal. Carrying it on `SurfaceSymbol` would let each plugin decide once,
  and would make this lane's path filter redundant rather than parallel.
- **2026-09-06 · G4-W13 · a README C++ body is given a `main`, and CMake is what supplies a
  third party's headers.** C++ has no top-level statements, and six of Aspose.Cells' seven examples,
  eight of Aspose.PDF's eleven and nine of Aspose.Slides' ten are bodies rather than programs:
  `wrap_example` keeps the preprocessor lines, comments, `using` declarations and namespace aliases
  at file scope and puts the rest in `main`. Separately, Aspose.Slides' public
  `shape_collection.h` opens with `#include <pugixml.hpp>`; before the verifier added the configure
  step's `_deps/<name>-src/{include,src}` directories to the include path, all ten of its examples
  stopped at that line with a fatal error and none was checked, and after it nine compile and the
  tenth fails for a real reason (`'pres' was not declared`, a continuation fragment).
  Alternatives rejected: compiling each snippet as a translation unit as written, which fails every
  body; and installing pugixml, which RESEARCH 28.12 point 6 forbids inside the box. Reversal:
  drop `fetched_includes` and accept ten unchecked examples.
- **2026-09-06 · G4-W13 · CMake is resolved from the machine before the lane's own toolchain
  directory, and the compiler the other way round.** `shutil.which("cmake")` finds
  `C:\Program Files\CMake\bin\cmake.exe`; the winlibs GCC bundle also ships a `cmake.exe`, and
  Aspose.PDF for C++, whose configure fetches GoogleTest over HTTPS, dies in the bundled one with
  "SSL certificate verification failed: certificate signer not trusted" and configures and builds
  in 95 seconds under the machine's. `g++` is on no PATH here at all, so it comes from
  `TOOLCHAIN_PATHS.txt`; its directory and Ninja's are prepended to the *subprocess* PATH only.
  Alternative rejected: prepend the toolchain directory and let `which` pick the bundled CMake,
  which is what the first probe did. Evidence: both runs are in this item's receipt. Reversal:
  record `cmake` in `TOOLCHAIN_PATHS.txt` and the registry lookup wins again.
- **2026-09-06 · G4-W13 · an example the compiler never reached is `NOT_VERIFIED`, and the
  library's own build never decides an example's verdict.** The syntax check's verdict is read from
  where the errors were raised: in the example's own file it is `FAILED`, and with no error in the
  example at all - a header it includes stopped the compiler first - it is `NOT_VERIFIED`, because
  "we could not check" is not "we checked and it is false" (§29.6 E5). Measured: two of
  Aspose.PDF's eleven examples include `facades/facade.hpp`, which holds a
  `unique_ptr<Document>` with a defaulted destructor over an incomplete type, and stop there.
  Separately, Aspose.Cells for C++ does not build with GCC 16.2 - `XlsxWorkbookSerializerCommon.cpp`
  uses `std::numeric_limits` without including `<limits>` and `NumberFormat.cpp` trips
  `-Werror=trigraphs` - and its first example still type-checks, which is why the CMake build's
  outcome is carried in the receipt as a phrase and never used as a gate. Alternative rejected: the
  legacy `example_verifiers/cpp.py` shape, where a failed build is `BUILD_FAILED` for every
  example. Evidence: that rule would have produced zero verdicts for two of the four repositories
  for reasons that are facts about the library's portability, not about its README. Reversal:
  return `_blocked(...)` when `build_product` does not say "succeeded".
- **2026-09-06 · G4-W13 · PROPOSAL (primary loop, `validation/registry.py` `_check_install`, BC-02
  and `docs/README_CONTRACT.md` §5): an install command is only ever `SUPPORTED` when a package
  registry says the package is published, so no unpublished repository in this portfolio can pass
  BC-02.** The check fails closed twice over - "no install command fact" when a plugin writes none,
  and "`{id}` is UNRESOLVED" when it writes an honest one - and C++ is the sharpest case because
  there is no registry to ask at all (`surface/registry.py`: "C++ has no registry"). All four C++
  repositories and both TypeScript ones are in this position; the two sealed Python candidates are
  published on PyPI, which is why the gap has not been seen before. Resume predicate: BC-02 admits
  a *verified source build* as an install - the command the examples stage itself ran, exiting 0
  at this revision - as evidence equal to a registry reading; then re-run the four C++
  repositories. This is downstream of the reconciliation defect below and would block them even
  after it is fixed.
- **2026-09-06 · G4-W13 · PROPOSAL (primary loop, `composition/renderer.py` `_installation`): the
  source-checkout block is hardcoded to `pip install .` for every ecosystem.** Lines 521-533 render
  "To work from a source checkout instead, install the clone with pip:" and a bash block of
  `git clone ... && cd ... && pip install .` whenever `context.supported("example")` is non-empty
  and `identity:repository` exists - neither condition mentions the ecosystem. Aspose.Slides for
  C++ has 9 supported examples and Aspose.PDF 4, so the block would render a command no C++ reader
  can run; .NET is in the same position and neither of its repositories has reached rendering yet.
  `core/ecosystems.py`'s `EcosystemSpec` docstring already names a `source_install` template
  "over `{package}` and `{repository}` and `{name}`" that the dataclass has no field for. Resume
  predicate: `EcosystemSpec` carries `source_install` and `_installation` renders it, empty meaning
  no block; C++'s is the two `cmake` lines its `install_command:cmake` fact already carries.
- **2026-09-06 · G4-W13 · PROPOSAL (primary loop, `composition/authoring.py` `_FORBIDDEN`): the
  Markdown-list check matches `"- "` anywhere in a unit, so a suspended hyphen in ordinary prose
  is rejected as a list.** Measured on Aspose.Cells for C++, which reached S6 and then lost the
  whole transaction to two rejections of the same unit: `capability:7` read "Attach hyperlinks to
  cells with HyperlinkCollection and manage **workbook-** or sheet-scoped named ranges via
  DefinedNameCollection...", and `("- ", "a Markdown list")` fired on `workbook- or`. The job was
  told to fix a defect it had not committed, so it could not, and the second attempt produced the
  same sentence. A list marker is only a list at the start of a line, and `("\n", "a line break; a
  unit is one paragraph")` already forbids a unit from having a second line - so anchoring the
  `"- "` and `"* "` entries to the start of the text loses nothing and stops a whole class of
  false rejections. Resume predicate: the two entries anchor to the start of the text; then
  re-run `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`.
- **2026-09-06 · G4-W13 · DISPOSITION · `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` at
  `9f852d0` - `BLOCKED_AUTHORING`.** Everything up to S6 holds: 401 tree entries, 2058 facts
  (1943 public symbols, a verified-zero dependency marker, C++17 and CMake 3.16 from the library's
  own `Aspose.Cells.Foss.Cpp/CMakeLists.txt`), 7 examples of which 1 compiles and 6 fail for real
  reasons - example 2 calls `WorksheetCollection::operator[]` with a string, which the class does
  not declare, and four more are continuation fragments naming a `sheet` or a `workbook` from an
  earlier block. Preflight: required rows without evidence, none. Investigation, reconciliation and
  planning all closed; `section_authoring` then rejected its own output twice on `capability:7`
  for the false positive above. Resume predicate: the `_FORBIDDEN` anchoring above; behind it, the
  queued `source_reconciliation` fix and BC-02, which the run before this one hit at S4 with
  `inherited_unit:011.heading`, `:012.paragraph` and `:013.code_block` placed into `installation`.
  Separately measured and not a blocker: the library does not build with GCC 16.2 -
  `src/aspose/cells_foss/XlsxWorkbookSerializerCommon.cpp:965` uses `std::numeric_limits` without
  including `<limits>`, and `NumberFormat.cpp:30` trips `-Werror=trigraphs`; MSVC accepts both.
- **2026-09-06 · G4-W13 · DISPOSITION · `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at
  `fef9c93` - `BLOCKED_RECONCILIATION`.** 75 tree entries, 348 facts (225 public symbols), 4
  examples of which 2 compile; example 3 names a `read_option` nothing declares and example 4 uses
  `std::cerr` while including only `<fstream>`, which GCC does not pull it in through. The library
  configures and builds cleanly in 15 seconds. Preflight: required rows without evidence, none. S4
  rejected twice on `inherited_unit:012.paragraph` and `:013.code_block` placed into
  `installation`. Resume predicate: as above.
- **2026-09-06 · G4-W13 · DISPOSITION · `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` -
  `BLOCKED_RECONCILIATION`.** 1521 tree entries, 1839 facts (1651 public symbols after 393 from
  `include/internal/` are dropped), 11 examples of which 4 compile, 5 fail and 2 are NOT_VERIFIED
  because `include/aspose/pdf/facades/facade.hpp` holds a `unique_ptr<Document>` with a defaulted
  destructor over an incomplete type and stops the compiler before either example's own calls are
  reached - a real defect in a public header, and the honest verdict for the example is "not
  checked". The library configures and builds in 95 seconds under the machine's CMake. Preflight:
  required rows without evidence, none. S4 rejected twice, here for a different reason than Cells
  and Email: `unknown fact ID api_reference` - the job cited section IDs (`navigation`,
  `at_a_glance`, `key_capabilities`, `installation`, ... thirteen of them) in `fact_ids`, which is
  the reconciliation job's own confusion between a destination and a citation. Resume predicate:
  the queued `source_reconciliation` fix, then BC-02 above.
- **2026-09-06 · G4-W13 · PROPOSAL (primary loop, `prompts/repository_investigation.yaml` and the
  planning stage): a planned limitation whose only vocabulary is non-public is unauthorable, and
  the rejection loop retries authoring rather than the stage that chose it.** Measured on
  Aspose.Slides for C++, which reached S6 with everything green and then lost the transaction to
  two rejections of `limitation:3` ("identifiers that are not accepted fact values:
  get_inherited_xfrm, get_inherited_xfrm()") and `limitation:4` (`xml_node`). Both identifiers are
  real, and both are declared under `include/Aspose/Slides/Foss/_internal/`, which this plugin
  withholds from the public surface for the reason recorded above - so the investigation read them
  from the tree, the plan asked for a limitation about them, and no authoring attempt could cite a
  fact that does not exist. Resume predicate: the investigation and the plan are constrained to
  the public fact set, or an authoring rejection naming an unknown identifier reopens planning
  rather than authoring (`docs/STATE_MACHINE.md` §8's routing); then re-run the repository.
- **2026-09-06 · G4-W13 · DISPOSITION · `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp` at
  `733de4b` - `BLOCKED_AUTHORING`.** 518 tree entries, 2999 facts (2845 public symbols after
  401 from `_internal/` are dropped), 10 examples of which 9 compile and the tenth is a
  continuation fragment naming a `pres` from an earlier block. `pugixml` is the one required
  dependency, read from the library target's PUBLIC link interface; miniz, GTest and googletest
  are development. The `conanfile.py` under `packaging/conan/` is not on the build path - the root
  `CMakeLists.txt` fetches pugixml and miniz with `FetchContent` when `find_package` finds none,
  so conan was never needed and nothing was installed. Worth recording against the census: the
  three examples `aspose_org_upstream_issues` lists as not compiling (Notes, Table, Comments) all
  compile at this revision, and the Table example's own comment now documents that
  `Cell::text_frame()` returns a pointer. Preflight: required rows without evidence, none. S4
  rejected once on `inherited_unit:043.heading` and `:044.code_block` placed into `installation`
  and then passed; planning closed after one rejection of its own ("Aspose links exceed the
  ceiling of 4: 5"); `section_authoring` then rejected `limitation:3` and `:4` twice for the
  reason above. Resume predicate: the PROPOSAL above; behind it, the queued
  `source_reconciliation` fix and BC-02.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · the four C++ dispositions re-run against
  `origin/main` at `4e1157f`: every one of them moved, none of them sealed, and all four now
  converge on a single check.** The re-run was asked for because two G4-W17 arrival items had
  landed. Measured, one repository at a time, from a fresh worktree at `C:\w\b13b` with its own
  `.venv`, `g++` 16.2.0 and `gcc` 16.2.0 from `TOOLCHAIN_PATHS.txt`, `ninja` 1.13.2 and `cmake`
  4.4.1 resolved by `shutil.which` first (`cpp_examples.toolchain_path` puts their directories on
  the subprocess `PATH` only; `os.environ` is never written):

  | repository | G4-W13 class | this run | stage reached |
  | --- | --- | --- | --- |
  | Email C++ | `BLOCKED_RECONCILIATION` (S4) | `BLOCKED_PLANNING` (S5) | S5 |
  | PDF C++ | `BLOCKED_RECONCILIATION` (S4) | `BLOCKED_VALIDATION` (BC-02) | rendered, validated |
  | Cells C++ | `BLOCKED_AUTHORING` (S6) | `BLOCKED_VALIDATION` (BC-02) | rendered, validated |
  | Slides C++ | `BLOCKED_AUTHORING` (S6) | `BLOCKED_VALIDATION` (BC-02, BC-08) | rendered, validated |

  Three of the four now render a complete README and reach validation - PDF 184 visible lines of
  685, Cells 143 of 691, Slides 202 of 629 - where none of them previously reached rendering at
  all. `repository-presenter status` still reads `candidates: 3/34`: nothing sealed, so the lane's
  `sealed_by_lane` stays 0 and its four dispositions are restated, not added to.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · which G4-W17 item actually cleared the S4
  refusals: neither of the two named.** Item 0 (12:30, a verified source build admits an
  unpublished install fact as SUPPORTED) cannot engage for C++ at all, for two independent
  reasons measured here, not inferred: `evidence/facts/extract.py`'s `_source_build_fact` returns
  the fact untouched unless `fact.polarity == "CONTRADICTED"`, and C++'s `install_command:cmake`
  is `UNRESOLVED` - `REGISTRY_TYPES` has no `cpp` entry, so there is no registry to contradict it
  and the reading is "package registry: none could not be read"; and `spec_for("cpp")
  .clone_and_build(...)` returns `''`, because `EcosystemSpec`'s own docstring records the empty
  template as deliberate ("A spec that needs none leaves them empty and the renderer prints
  nothing, which is what a registry-less ecosystem (C++) requires"). Item 1 (12:37) was declined
  as a prompt change and landed only a mutation test, so it changed no behaviour for anyone.
  What did clear S4 is `7ea433e` (G4-W11, 07:47) - `source_reconciliation` v5's output budget
  raised 16000 to 32000 and a placement into a section whose condition is false deferred rather
  than failed closed. That commit reached the lane only in the 09:59 merge, *after* the runs that
  produced the four dispositions, which is why the lane recorded refusals its own tree had already
  been fixed for. Evidence: PDF's `source_reconciliation` was accepted on the first attempt this
  run (117 units dispositioned, no `.rejected-` record) where it previously died twice on
  `unknown fact ID api_reference` - the shape a reply truncated at 16000 tokens produces. Item 2
  (12:52, `CallStore`'s hash prefix 24 to 12) is confirmed working incidentally: every
  `.rejected-N.json` written this run carries a 12-character prefix and no transaction died on
  Windows' MAX_PATH.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · PROPOSAL (owner decision, then primary loop -
  `evidence/facts/extract.py` `_source_build_fact` with `validation/registry.py` `_check_install`
  and `core/ecosystems.py`): a registry-less ecosystem is structurally excluded from BC-02 by two
  decisions that are each locally right.** This is the single check now blocking all four C++
  repositories, and it is the same PROPOSAL G4-W13 already filed, refined by what item 0 actually
  landed. BC-02's downstream half is ready: `_check_install` accepts `"verified source build"`
  beside `"package registry"` as manifest evidence (item 0's own change), so the moment the fact
  is SUPPORTED the check passes. The upstream half never fires for C++: the polarity gate admits
  only `CONTRADICTED`, and the empty `source_install` is documented as what a registry-less
  ecosystem requires. Neither half is wrong on its own - a registry that says "not published" is
  genuinely different evidence from no registry at all, and C++ genuinely has no `pip install`
  line to print. But the composition of the two is that no C++ repository in this portfolio can
  ever pass BC-02, while its install command is in fact the *most* verified of any ecosystem's:
  `cmake -S . -B build` / `cmake --build build` is the command `cpp_examples` itself drives to
  configure and build each library before compiling its examples, and it succeeded for all four
  (Email in 15 s, PDF in 95 s). The fact is UNRESOLVED because "there is no registry" is recorded
  as an inconclusive reading, not because anything about the build is unverified. Fix, smallest
  first: extend the polarity gate to `{"CONTRADICTED", "UNRESOLVED"}` and give C++ a
  `source_install` that is the cmake pair the fact already carries. Alternative rejected: lane B
  landing the C++ half alone, which is its own path - it would seal nothing while the shared gate
  discards the fact, and `EcosystemSpec`'s docstring names the empty template as intended, so
  changing it is an owner call, not a lane's. Reversal: revert both; the four dispositions stand
  as they are today. Resume predicate: `install_command:cmake` is SUPPORTED with source-build
  evidence; then re-run `present` for all four.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · PROPOSAL (primary loop,
  `composition/planning.py` `plan_checks`): `7ea433e` deferred the impossible placement at S4 and
  left the identical failure standing at S5, for the one condition planning recomputes.**
  Measured on Aspose.Email for C++, the only repository of the four that still dies before
  rendering. `dispositions.normalize` reads `additional_examples`' condition from
  `section_conditions`, where it is `len(SUPPORTED examples) >= 2`; Email has exactly two, so the
  section is not in `absent` and a placement into it is correctly left alone. `plan_checks` then
  *overwrites* that same key - `conditions["additional_examples"] = bool(set(verified_examples) -
  starts)` - because the plan's quick starts consume examples; the plan took both, the set went
  empty, the condition flipped True to False, and `inherited_unit:032.paragraph` became a
  placement into an excluded section. `presentation_planning` was rejected twice with "section
  additional_examples is excluded at this revision but the reconciliation placed
  inherited_unit:032.paragraph there" and the transaction failed closed. The planner cannot
  answer that rejection: it did not make the placement and cannot withdraw it, and the inclusion
  list is composed deterministically, not asked for. `7ea433e`'s own commit message states the
  principle - "no re-ask can honour a placement no plan may include" - and applied it in
  `normalize`; the same reasoning applies verbatim here, where planning's own recomputation is
  what excludes the section. Fix: on `placement.outcome == "excluded"`, defer the unit as
  `normalize` does rather than appending an error. Alternative rejected: making reconciliation
  conservative (treat `additional_examples` as absent whenever `<= 2` examples exist) - it would
  defer units for repositories whose plans leave an example over, losing real content to a
  condition that does hold. Reversal: revert; Email returns to this disposition. Resume
  predicate: the deferral lands; then re-run `present --repo
  aspose-email-foss/Aspose.Email-FOSS-for-Cpp`.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · PROPOSAL (primary loop,
  `validation/registry.py` `_COMMAND` and `_PLACING`): a third party's package name in prose is
  read as a command, and `VERIFIED_REWRITE` is then required to preserve it verbatim.** Measured
  on Aspose.Slides for C++, the only repository carrying a second failure. BC-08 reports
  "`inherited_unit:078.list`: VERIFIED_REWRITE keeps the command `'python-pptx'` but the candidate
  does not render it". The unit is a Markdown list in the upstream README describing the CI
  suite, and the span it protects is `` `python-pptx` `` - the name of a third-party Python reader
  the conformance test opens files with, named in prose, never invoked. `_COMMAND` matches it
  because its `python3?` alternative is followed by `\b`, and the boundary between `python` and
  `-pptx` is a word boundary; the same false positive is waiting for `python-docx`, and for any
  hyphenated name beginning `go-`, `git-`, `make-` or `cargo-`. Independently, `_PLACING` includes
  `VERIFIED_REWRITE` in a check that demands the fragment appear verbatim in the rendered
  candidate - but a rewrite is precisely the disposition that re-authors rather than preserves, so
  the demand contradicts the disposition's own meaning (the reconciler's rationale here reads "its
  substance is re-authored in Development and Testing", which is exactly what it did). Either fix
  alone clears Slides: require a whitespace or end-of-span boundary after the interpreter name,
  or drop `VERIFIED_REWRITE` from `_PLACING` for the `command` category. Both are worth landing;
  they are different defects that happened to meet on one unit. Alternative rejected: adding
  `python-pptx` to a word list - the pattern is wrong for a family of names, not for this one.
  Reversal: revert; Slides returns to this disposition.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · not re-proposed: G4-W17 items 20 and 21 did not
  land, and neither failure recurred - which is not the same as fixed.** Item 20 (anchoring
  `composition/authoring.py`'s `_FORBIDDEN` Markdown-list entries to the start of a unit) and item
  21 (an authoring rejection naming an unknown identifier reopens planning rather than authoring)
  are both still queued and unlanded; `_FORBIDDEN` still carries a bare `("- ", "a Markdown
  list")` and the stray-identifier branch still only appends an error for the same stage to
  retry. Cells nevertheless cleared `section_authoring` this run (three rejections raised, all
  three recovered on the retry, none of them the hyphen) and Slides cleared it too (its plan chose
  five limitations, none naming an `_internal/` identifier - `get_inherited_xfrm` and `xml_node`
  were not selected this time). Both classes are latent, not closed: the code that produced them
  is byte-identical. Recorded here so the queue is not read as shorter than it is, and not
  re-proposed, per the instruction that already-queued items are not re-filed.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · DISPOSITION (revised) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93` - `BLOCKED_PLANNING`.** Was
  `BLOCKED_RECONCILIATION`. 75 tree entries, 348 facts (225 public symbols), 4 examples of which 2
  are EXECUTED and 2 FAILED - unchanged from G4-W13, as is the library's clean 15-second configure
  and build. S4 `source_reconciliation` now closes after one recovered rejection where it
  previously died on placements into `installation`. S5 `presentation_planning` is rejected twice
  and the transaction reports: `section additional_examples is excluded at this revision but the
  reconciliation placed inherited_unit:032.paragraph there`. Preflight: required rows without
  evidence, none. Resume predicate: the `plan_checks` deferral PROPOSAL above; behind it, BC-02,
  which this repository has not yet reached.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · DISPOSITION (revised) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_VALIDATION (BC-02)`.** Was
  `BLOCKED_RECONCILIATION`. 1521 tree entries, 1839 facts (1651 public symbols after 393 from
  `include/internal/` are dropped), 11 examples - 4 EXECUTED, 5 FAILED, 2 NOT_VERIFIED for the
  incomplete-type defect in `facades/facade.hpp` recorded at G4-W13. The `unknown fact ID
  api_reference` refusal is gone: S4 accepted on the first attempt, 117 units (58
  VERIFIED_PRESERVE, 28 SUPERSEDE_REDUNDANT, 24 OMIT_UNSUPPORTED, 6 DEFER_UNRESOLVED, 1
  VERIFIED_REWRITE). Planning closed after one recovered rejection, 18 of 18 sections; authoring
  wrote 287 units across 9 sections through 17 provider calls with one recovered rejection;
  coherence revised 0 of 287; the renderer produced 184 visible lines of 685. Validation: 8 PASS,
  1 FAIL, 2 PENDING - the single failure is BC-02, `install_command:cmake is UNRESOLVED: package
  registry: none could not be read`, and `targeted_repair` correctly recorded it unrepairable
  (no repair can make a registry exist). Resume predicate: the BC-02 PROPOSAL above; then re-run.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · DISPOSITION (revised) ·
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` at `9f852d0` - `BLOCKED_VALIDATION (BC-02)`.**
  Was `BLOCKED_AUTHORING`. 401 tree entries, 2058 facts (1943 public symbols), 7 examples of which
  1 is EXECUTED and 6 FAILED - example 2's `WorksheetCollection::operator[]` with a string is
  still a real README defect, and the library still does not build with GCC 16.2 (missing
  `<limits>`, `-Werror=trigraphs`), neither of which changed a verdict. The `- ` false positive
  did not recur (see the entry above; the code is unchanged). S4 accepted first attempt, 65 units;
  planning closed after one recovered rejection at 15 of 18 sections; authoring wrote 227 units
  across 7 sections through 15 calls, three rejections all recovered; coherence revised 1 of 227;
  143 visible lines of 691. Validation: 8 PASS, 1 FAIL, 2 PENDING - BC-02 alone, the same detail
  as PDF. Resume predicate: the BC-02 PROPOSAL above; then re-run.

- **2026-09-06 14:29 (`date` checked) · G4-W13 · DISPOSITION (revised) ·
  `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp` at `733de4b` -
  `BLOCKED_VALIDATION (BC-02, BC-08)`.** Was `BLOCKED_AUTHORING`. 518 tree entries, 2999 facts
  (2845 public symbols after 401 from `_internal/` are dropped), 10 examples of which 9 are
  EXECUTED and the tenth is the continuation fragment naming a `pres`. The unauthorable-limitation
  refusal did not recur (see above; the code is unchanged). S4 closed, 88 units; planning closed
  at 18 of 18 sections with 5 limitations; authoring wrote 271 units across 9 sections through 17
  calls; coherence revised 2 of 271; 202 visible lines of 629. Validation: 7 PASS, 2 FAIL, 2
  PENDING - BC-02 as above, plus BC-08 on `inherited_unit:078.list`, the `python-pptx` false
  positive the PROPOSAL above names. This is the only one of the four carrying a second blocking
  failure. Resume predicate: both PROPOSALs above; then re-run.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · neither G4-W17 item named in the re-run
  request cleared 3D TypeScript; `d583d07` (G4-W11, 08:39) did, fourteen minutes after this item
  was accepted.** Both TypeScript dispositions were re-run against `origin/main` at `2b88ea4` from
  a fresh worktree at `C:\w\b14b` with its own `.venv`; branch `lane-b/rerun-typescript` is cut
  from it. Item (1) is `7c0e7e6` (12:42), a test-only commit that *declined* the prompt change
  ("zero production change needed") because `dispositions.normalize` already folded any owner-D
  section rendering nothing; item (2) is `c0071d1` (12:53). Reading the tree this item actually
  ran against - `7ea433e`, its own recorded `control_revision` - that fold did **not** exist:
  `git show 7ea433e:.../reconciliation/dispositions.py` line 300 still reads
  `errors.append(f"{unit}: section {destination} renders nothing for this repository; choose
  OMIT_UNSUPPORTED or DEFER_UNRESOLVED")`, which is verbatim the refusal this lane recorded. The
  `errors.append` became `entry["disposition"] = "DEFER_UNRESOLVED"` in `d583d07` (G4-W11,
  08:39) - measured there on Aspose.Slides for .NET, not on anything of this lane's. So the
  12:42 entry's reading ("the fold already exists, unconditional") was true when it was written
  and false when this lane measured; item (1) is correctly declined, but the credit for
  unblocking 3D TypeScript belongs to G4-W11, exactly as this lane's C++ re-run found for its own
  S4 refusals. Alternative rejected: recording item (1) as the cause because the re-run request
  named it. Evidence: the three commits above; `dispositions.json` for this run folds the same
  five units (`023.heading`, `024.paragraph`, `025.code_block`, `088.heading`, `089.paragraph`)
  to `DEFER_UNRESOLVED` with `destination_section: null`, and S4 accepted first attempt. Reversal:
  none; this is a reading of history, not a change.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · item (2) cleared Cells TypeScript, and the
  arithmetic separates it from this run's shorter root.** The re-run wrote
  `C:\w\b14b\runs\transactions\aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript\<revision>\
  calls\eaa447337377.rejected-1.json` and `.rejected-2.json` - **155** characters, the exact file
  whose `write_bytes` raised `FileNotFoundError` before - and the transaction ran to validation.
  This run's root is 94 characters shorter than the worktree that measured 261, so the run alone
  does not isolate the cause; the name does. The suffix below any root is 158 characters with the
  old 24-character hash and 146 with `c0071d1`'s 12, so the same name from the original root is
  **261 - 12 = 249**, under Windows' 260. Item (2) alone clears it, from that root, without a
  short checkout. Alternative rejected: claiming the re-run proved it. Evidence: the two rejected
  files above at 155 characters; `git show c0071d1 -- src/repository_presenter/core/llm/jobs.py`.
  Reversal: none.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · a re-export binds a name *and* a module,
  and a top-level function is the one symbol the façade hands back unqualified.** Two defects in
  this lane's own files, both exposed by the re-run and both fixed here with a mutation test each
  (`src/.../platforms/typescript_barrel.py`, `typescript.py`,
  `tests/.../platforms/test_typescript.py`). (a) `reexported_names` returned a flat set of names
  and `_public_name` matched on the name alone, so a *second* declaration of an exported name
  anywhere under the entry point was published as though the package exported it twice. Measured:
  Aspose.3D declares `BoundingBoxExtent` at `utilities/BoundingBox.ts:188` while its barrel
  re-exports only `BoundingBox` from that file and takes `BoundingBoxExtent` from its own module,
  and Aspose.Cells binds `CellCoordinates`, `CellRange` and `Comment` from `./types` and
  `./comment` while `util.ts` and `types.ts` declare rivals of all three - 1 duplicate type on 3D
  and **40** duplicate symbols on Cells, which is what BC-07 refused ("verified public type
  BoundingBoxExtent is recorded 2 times; one fact per canonical defining location"). New
  `reexported_bindings` carries the resolved module per name; `_binds` disqualifies a symbol only
  when its file holds a *rival declaration* of the name, because the façade reports an inherited
  member under the derived type with the base's file as evidence
  (`AssetInfo.AssetInfo.toString` from `A3DObject.ts`) - checking the module alone dropped 255
  genuine members of Aspose.3D, measured before the rule was narrowed. (b) `_public_name`
  required a dotted value, and the façade returns a top-level function unqualified
  (`colToIndex`, not `aspose_cells.util.colToIndex`), so every function a TypeScript package
  exports was silently absent: Aspose.Cells re-exports eight from `./util` and its surface held
  only `class`, `method` and `enum` facts. Measured effect: 3D 1034 -> 1028 public symbols
  (BC-07 now PASSES, validation 6 pass/3 fail -> 7 pass/2 fail); Cells 353 -> 321 with the eight
  functions gained and all 40 duplicates gone. Alternative rejected: deduplicating by name at the
  fact layer, which would have kept whichever declaration was read first and still published a
  class no consumer can reach. Tests:
  `test_a_rival_declaration_of_an_exported_name_is_not_published_twice`,
  `test_an_inherited_member_is_published_though_its_base_declares_it`,
  `test_an_exported_top_level_function_is_published`. Deliberately not built (loop-prompt section
  6 rule 1): following a named re-export through an *intermediate* barrel to the declaring file -
  neither cohort repository does that, both name the declaring module directly and use `export *`
  for directories, and the limitation is stated in `_binds`'s own docstring. Reversal: revert the
  two modules; `reexported_names` is kept as a wrapper so nothing else moves.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · PROPOSAL (primary loop,
  `composition/renderer.py`): Navigation links a section `render_readme` has already dropped.**
  `render_readme` skips a section whose body renders nothing (`if not any(line.strip() for line
  in body): continue`), but `_navigation` is built from `context.included`, which still holds it,
  and Navigation is emitted before the later bodies are known. Aspose.3D for TypeScript ships no
  licence file, so `license` renders nothing and the document still carries
  `- [License](#license)` with no `## License` heading: `BC-06 failed at COMPOSING: #license: no
  heading #license`, recorded unrepairable both attempts (no `section_id`, so
  `repair/targeted.py` cannot route it). `docs/README_CONTRACT.md`'s own `navigation` row says
  "in-page links to the visible headed sections **actually present**", so the renderer
  contradicts the row it implements. General, not this repository's: `installation` renders
  nothing for every unpublished package in the portfolio and is the same shape one section
  earlier. Fix: render every section's body first, then build Navigation from the sections that
  survived the empty-body skip. Disposition below names this as a resume predicate.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · PROPOSAL (primary loop,
  `evidence/facts/extract.py`): G4-W17 item (0)'s "an EXECUTED example proves the source
  compiles" is unsound for TypeScript, and this lane must not paper over it with a
  `source_install` string.** `_source_build_fact` opens for both TypeScript repositories - the
  npm probe answers conclusively, so `install_command:npm` is `CONTRADICTED` (not C++'s
  `UNRESOLVED`, so item (24)'s carve-out is irrelevant here), and both have EXECUTED receipts -
  and then returns the fact untouched because `TYPESCRIPT` declares no `source_install`. The
  obvious lane-side fix is wrong on measurement, not on principle: TypeScript's verifier reads
  diagnostics only from the example's own file by design (`typescript_examples.py`: "a diagnostic
  in the library's sources is a fact about the library's build environment"), so an EXECUTED
  TypeScript receipt says nothing about whether the library builds. Measured today against the
  two clones, with the lane's own npm profile: Aspose.Cells has **3 of 3** examples EXECUTED, yet
  `npm install` (exit 0, 16.3 s) followed by `npx tsc --noEmit` exits **2** with three real
  errors in its own sources (`aspose_cells/chartLoader.ts(210,11) TS2345`,
  `html/htmlDocument.ts(92,54) TS7006`, `workbook.ts(482,63) TS2345`) and its manifest declares no
  `build` script at all (only `start: tsx index.ts`); Aspose.3D declares `build: tsc` and both
  `npm install` (exit 0, 58.1 s) and `npm run build` (exit 0, 6.9 s) succeed. So no single
  ecosystem-wide command is verified by the receipts item (0) consults - one repository builds,
  the other has nothing to build and does not compile - and writing item (0)'s evidence sentence
  ("verified source build: an example executed against this revision, proving the source
  compiles") for Aspose.Cells would be a fabricated claim (loop-prompt section 6 rule 12).
  Alternative rejected: `source_install="…npm install"`, which renders under the renderer's own
  "build it from a source checkout instead, verified against this revision" lead for a step that
  builds nothing. Fix: item (0)'s gate consults a receipt for the *command it names*, per
  repository, rather than an example receipt - a plugin that can drive the manifest's own build
  records that receipt and the fact becomes SUPPORTED for the repository that earns it, while a
  repository whose sources do not compile keeps BC-02 honestly failing. This is the single
  blocker between Aspose.Cells for TypeScript and a seal (8 pass, 1 fail, 2 pending) and one of
  two for Aspose.3D.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · PROPOSAL (primary loop,
  `composition/renderer.py`): a `function` public symbol renders nowhere.** `_api_reference`
  groups `public_symbol` facts by `symbol_kind` and builds the Core API table from `class` and
  `enum` only, with `method` facts feeding the Detailed Member Reference; a `function` fact is
  read by no branch. With the fix above, Aspose.Cells for TypeScript now records its eight
  exported helpers (`colToIndex`, `indexToCol`, `cellRef`, `parseCellRef`, `parseRange`,
  `escapeXml`, `unescapeXml`, `generateUuid`) as facts that appear in no section, so the
  collapsed reference is still not the complete public surface (loop-prompt section 6 rule 8).
  Not blocking today - no check requires it, and the facts are honest - but the same gap awaits
  Go and Rust, whose packages export free functions as a matter of course, and it is the
  rendering half of the G4-W17 items (9) and (11) family. Fix: the Core API table gains a
  Functions subsection beside Enumerations, keyed on the `function` kind the façade already sets.

- **2026-09-06 19:28 (`date` checked) · G4-W14 re-run · latent, not re-proposed: a plan naming a
  fact ID that does not exist rejects the whole reply.** On the first draw of this re-run
  Aspose.Cells died at S5 with `presentation_planning: output rejected twice; last rejection:
  unknown fact ID public_symbol:ImageInfo; unknown fact ID public_symbol:ShapeInfo; unknown fact
  ID public_symbol:HtmlSaveOptions` - `core/llm/binding.py::binding_errors` fails the reply whole
  on any unknown cited ID, the same shape G4-W17 item (16) folded for a repeated hub and an
  over-ceiling link and item (17) folded for a repeated disposition. All three names are real
  types of the repository that its own README describes and its barrel does not re-export
  (`ImageInfo` and `ShapeInfo` are `export interface` in `types.ts`; `HtmlSaveOptions` is
  exported by `aspose_cells/html/index.ts`, which the main barrel never reaches), so the surface
  was right and the plan was wrong. It did **not** recur on the second draw after the surface fix
  above changed the packet: the plan closed in 2 calls with 8 hubs. Two draws is not evidence of
  a fix, so the class is recorded here as latent rather than proposed as landed work; if it
  recurs, the fold is item (16)'s, one list further in.

- **2026-09-06 19:28 (`date` checked) · G4-W14 · DISPOSITION (revised) ·
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at `7b95970` -
  `BLOCKED_VALIDATION (BC-02, BC-06)`.** Was `BLOCKED_RECONCILIATION`. The S4 refusal is gone
  (`d583d07`, above) and the transaction now runs end to end where it previously reached no
  rendering at all: 190 tree entries, 1172 facts (1028 public symbols after the duplicate fix),
  9 examples of which 8 are EXECUTED; S4 accepted first attempt, 89 units with the same five
  deferred; planning closed at 17 of 18 sections with 12 hubs; authoring wrote 122 units across
  9 sections; coherence revised 0 of 122; **190 visible lines of 765**. Validation: 7 PASS, 2
  FAIL, 2 PENDING - BC-02 (`install_command:npm is CONTRADICTED: package registry: distribution
  not found on npm`) and BC-06 (`#license: no heading #license`), both recorded unrepairable,
  plus three advisories, all "the rewrite no longer names …" on inherited units. Resume
  predicate: both PROPOSALs above (the item (0) gate and the Navigation fix); then re-run
  `present --repo aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`.

- **2026-09-06 19:28 (`date` checked) · G4-W14 · DISPOSITION (revised) ·
  `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` at `fc18650` -
  `BLOCKED_VALIDATION (BC-02)`.** Was `BLOCKED_ENVIRONMENT (Windows MAX_PATH)`. The path death is
  gone (`c0071d1`, above) and this repository now reaches validation with **one** blocking
  failure: 44 tree entries, 419 facts (321 public symbols - 40 duplicates removed and 8 exported
  functions gained), 3 of 3 examples EXECUTED, no required contract row without evidence; S4
  accepted first attempt, 49 units; planning closed at 17 of 18 sections with 8 hubs; authoring
  wrote 60 units across 9 sections through 10 calls; coherence revised 1 of 60; **179 visible
  lines of 434**. Validation: 8 PASS, 1 FAIL, 2 PENDING - BC-02 alone, the same detail as every
  unpublished repository in the portfolio - with one advisory. This is the closest any lane B
  repository has come to sealing. Resume predicate: the item (0) PROPOSAL above; then re-run
  `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript`.

- **2026-09-06 19:28 (`date` checked) · G4-W14 · DISPOSITION (unchanged) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` - `DISABLED_UPSTREAM`.** `data/registry.json`
  still records `mode: disabled`; the re-run request said not to touch it and no clone was
  attempted. Resume predicate unchanged.
- **2026-09-11 13:23 (`date` checked) · G4-W13-RERUN2 · FINDING (third independent lane) · arrival
  item 40's `fact_ids` pattern anchors a prefix and never requires a local part, so the bare kind
  prefix is a legal fact ID at decode time and an unknown one at binding time.** Lanes C and D
  measured this hour (`852047a`, `3bc7999`); lane B met it on its own draw and adds the mechanical
  proof and a second failure branch. `reconciliation/dispositions.py::reconciliation_schema` sets
  `fact_ids.items` to `{"type": "string", "pattern": "^(<kinds>):"}`; built from the production
  manifest (`load_manifests(Path("prompts"))["source_reconciliation"]`) the pattern is
  `^(build_test_asset|dependency|example|format|identity|import_path|inherited_unit|install_command|license|link_target|package|public_symbol|third_party_notices):`
  and `re.match` accepts `license:`, `package:`, `example:`, `link_target:`, `identity:`,
  `install_command:`, `dependency:` and `public_symbol:` - every string that then rejected the
  transaction. The docstring's own claim for the change is "the pattern refuses them at decode time
  rather than after the whole transaction is spent"; measured here the transaction is spent anyway,
  because `core/llm/binding.py::binding_errors` is the only thing that knows an ID must *name* a
  fact. Measured on `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93`: S4
  `source_reconciliation` rejected twice - attempt 1, 15 of 40 disposition records carrying a bare
  prefix across 8 distinct kinds, attempt 2, 12 of 40 across 7 - and the transaction died at S4.
  Two points lane B can add. (a) The model is not confused about the ID; it is filling a slot. Its
  own rationales name the right fact in the same record - `inherited_unit:026.paragraph` cites
  `fact_ids: ["example:"]` with rationale "supported by example:001 ... used placeholder",
  `003.badge_row` cites `link_target:` with "supported by link_target:product.banner",
  `022.paragraph` cites `dependency:` with "supported by dependency:none", `024.list` cites
  `package:` with "supported by package:cmake_minimum and package:cxx_standard". Every one of those
  rationale-named IDs is a real record of the packet. (b) This is the "names no fact" branch, not
  the 32000-token runaway, and it is not confined to a large surface: Email C++'s packet is 357
  facts and 225 public symbols, the smallest C++ repository in the lane. So the cap is one symptom
  and the empty local part is another, and a fix that only raises or batches the cap leaves this
  draw failing. The strictly-correct fix mirrors what this same function already does two lines
  later for `unit_id` (`{"type": "string", "enum": units}`): the packet's fact IDs are known exactly
  at schema-build time, and `binding_errors` already refuses anything outside `facts.facts`, so an
  enum over those IDs is exactly co-extensive with what the next stage will accept and admits no
  bare prefix at all. If an enum of 1651 IDs (PDF C++) is judged too large for the decoder, the
  minimal correction is a non-empty local part in the pattern. Lane B states the measurement and
  the two options; the choice is the owner's and the primary is landing the fix. Regression, not a
  standing condition: this same repository, same prompt text, closed S4 on 2026-09-06 after one
  recovered rejection (entry of 2026-09-06 14:29 below), and item 40 landed 2026-09-11 06:50
  (`e2a1a83`). No disposition is written against it - per the reviewer's instruction this hour, a
  stage known to be broken portfolio-wide does not earn a per-repository verdict. Evidence:
  `runs/transactions/aspose-email-foss__Aspose.Email-FOSS-for-Cpp/fef9c934.../calls/6ed66cf282d1.rejected-1.json`
  and `.rejected-2.json`. Reversal: none; this is a measurement.

- **2026-09-11 13:23 (`date` checked) · G4-W13-RERUN2 · FINDING · TB-01 ground truth for the two
  C++ re-run repositories: both libraries genuinely build with the available GCC, so their
  `install_command` is honestly SUPPORTED and neither needs a weakened check.** The sprint plan
  flags "PDF-Cpp (24; TB-01 risk)" and the re-run request asks the question directly, so it is
  answered here from receipts rather than left to the next run. Measured with the recorded
  `C:\tools\rp-toolchains\winlibs\mingw64\bin\g++.exe` 16.2.0 (MinGW-W64 x86_64-ucrt-posix-seh,
  r1), resolved from `TOOLCHAIN_PATHS.txt` key `gxx`, nothing on the user or system PATH.
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a`: every one of the 11 receipts carries
  `build_verified: true`, and the EXECUTED detail reads verbatim "... -std=c++20 -fsyntax-only; the
  library's own CMake build **succeeded**" - which is the clause `cpp_examples.py` writes only when
  the real CMake build returned success, since `build_verified = product == "succeeded"`. 11
  candidates: 4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED. 1846 facts (1651 public symbols), 1839
  SUPPORTED, 5 UNRESOLVED, 2 CONTRADICTED, required contract rows without evidence: none.
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93`: the same clause at `-std=c++17`, 4
  candidates - 2 EXECUTED, 2 FAILED; 357 facts (225 public symbols), 355 SUPPORTED, **0
  UNRESOLVED**, 2 CONTRADICTED, no required row without evidence. The consequence both re-runs
  existed to test: `install_command:cmake` is now **SUPPORTED** for both, carrying the evidence line
  "verified source build: an example executed against this revision, proving the source compiles
  even though the registry does not yet list the package". Email's preflight read 0 unresolved where
  the 2026-09-06 run had this fact UNRESOLVED - arrival item (24) opened for C++ exactly as it was
  written to, and TB-01's gate let it through on merit. So BC-02 is no longer PDF C++'s blocker on
  honest evidence, and the answer to "is that candidate sealable at all this sprint" is yes on the
  build question - it is blocked only by S4, upstream and shared. The contrast that makes this a
  real measurement rather than a restatement: TB-01's own worked example,
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, is the repository whose CMake build *fails* with
  this same compiler (missing `<limits>`, `-Werror=trigraphs`, recorded 2026-09-06), so the honesty
  rule bites there and correctly does not bite here; the two outcomes come from one unchanged code
  path. Alternative rejected: recording PDF C++'s BC-02 as a disposition with a build caveat - the
  receipts say the build succeeded, and writing a weaker claim than the evidence supports is as much
  a fabrication as writing a stronger one. Evidence: `examples.json` and `facts.json` under each
  repository's transaction directory at the revisions above. Reversal: none; this is a measurement.

- **2026-09-11 13:23 (`date` checked) · G4-W13-RERUN2 · no dispositions this run, and the box was
  closed early on the reviewer's instruction rather than at its own clock.** The reviewer's message
  this hour ("stop before spending another provider call on a candidate - the pipeline is blocked at
  S4 for every repository") arrived while the PDF C++ composition was in flight; it was stopped
  after **one** provider call (S3 `repository_investigation`, accepted first attempt - the single
  file in that transaction's `calls/`), so PDF C++ has facts and an investigation for this revision
  and never reached S4. Email C++ spent three calls: one accepted investigation and the two rejected
  S4 attempts above. The four standing C++ dispositions of 2026-09-06 are left exactly as they are -
  not revised, not re-dated, not re-scoped - because a verdict taken against a stage known to be
  broken portfolio-wide would record the wrong cause for the next reader, which is the failure mode
  the entry of 2026-09-06 14:29 already had to correct once by hand. `sealed_by_lane` stays 0.
  Alternative rejected: converting Email C++'s disposition from `BLOCKED_PLANNING` (S5) to a new
  `BLOCKED_RECONCILIATION` (S4) - true of this draw, but it would read as the repository regressing
  on its own merits when the cause is one shared commit landed six hours earlier and already being
  reverted-forward by the primary. Reversal: the supervisor re-spawns this item when the S4 fix
  lands; both repositories re-run from their current facts.
- **2026-09-11 13:45 (`date` checked) · G4-W13-RERUN2 · FINDING (infrastructure, not this lane's
  code, and already on `main`) · the repository-level git identity was overwritten with the test
  fixtures' `Test <test@example.com>`, and two commits already merged to `origin/main` carry it.**
  Observed, not inferred. While this run's own commit was being pushed, `git log` in this worktree
  showed HEAD at a commit named `placeholder` over five named `seed` and one named `initial`, whose
  whole tree is `LICENSE` plus `README.md` - the shape `tests/support.py::init_git_repository`
  builds, which writes `README.md` as `# test\n`. This lane's own commit was intact one step down
  the reflog and was recovered from there. Three facts worth recording beyond the recovery. (a) The
  damage is not confined to this worktree or this session: `git config --local` in the *shared*
  `.git/config` (one file, common to the primary checkout and every lane worktree) read
  `user.name=Test` / `user.email=test@example.com`, and `origin/main` already carries `b712790`
  authored `Test <test@example.com>` (13:10) and `18e26e5` authored `Babar Raza
  <test@example.com>` (13:19) - neither this lane's, both landed before this run's first commit.
  This lane's own first two commit objects were authored `Test <test@example.com>` for the same
  reason and were re-authored by `--reset-author` before the PR; the local override is now unset,
  so the identity falls through to the correct global one. (b) The standing hazard is that the git
  fixtures are unfenced. `init_git_repository` runs `git config user.email test@example.com` and
  `git config user.name Test` with no `--file`, no `GIT_CONFIG_GLOBAL`, and no `GIT_DIR`; it relies
  entirely on `cwd` having landed inside a directory `git init` just created. `commit_all` relies on
  `cwd` alone in the same way, and `core/git_safety/git.py::run_git` adds only
  `GIT_TERMINAL_PROMPT`/`GCM_INTERACTIVE` and three `-c` determinism flags - no
  `GIT_CEILING_DIRECTORIES`, no `GIT_DIR`, no `GIT_CONFIG_*` fence. So any such call whose `cwd`
  does not land inside a fixture repository operates on whatever repository git discovers by
  walking up from the process working directory, which under pytest is the checkout itself, and a
  `git config` there writes the shared file rather than a disposable one. (c) **What this lane
  could not reproduce, stated as plainly as what it could:** a full `pytest -n auto` run in this
  worktree, immediately after the recovery, did *not* reproduce any of it - 1006 passed, 10 xfailed
  in 141.50s, and `HEAD`, the branch ref and `git config --local user.name`/`user.email` were all
  byte-identical before and after (`e2fc2c5…` / `e2fc2c5…` / unset / unset), with a clean
  `git status`. So the plain suite is not the trigger and this entry does not claim it is; the
  fixtures being unfenced is a real defect independently of what tripped it, and the most probable
  trigger given the timing is two sessions' suites interleaving in one shared git directory - lanes
  E and F opened at 13:10 (`b712790`), the same minute the first mis-authored commit landed. Naming
  the exact race would need an instrumented concurrent run, which is outside this run's box and
  outside this lane's owned paths. PROPOSAL, for whoever owns `tests/`: fence every fixture call -
  `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` pointed at a temp file, `GIT_CEILING_DIRECTORIES` at the
  fixture root, and `git -C <path>` with an explicit `GIT_DIR` - so that a fixture can never resolve
  to the real checkout even when `cwd` is wrong. Worth doing ahead of the arrival queue: a wrong
  author is silent, is already in merged history, and no check in the suite looks at it. Alternative
  rejected: this lane editing `tests/support.py` - not an owned path, and a shared-code fix from a
  lane is exactly what section 28.12 forbids. Evidence: the reflog of this branch; `git log
  --format='%an <%ae>' origin/main`; the before/after triple above. Reversal: none; a measurement
  plus a recovery.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · the S4 fix works, both C++ repositories ran
  end to end for the first time, and neither sealed - one on a shared-code defect and one on the
  review verdict alone.** Measured against `origin/main` at `08307b9` from a fresh worktree at
  `C:\w\b02`. `352fd35`'s enum of the packet's own fact IDs closed the blocker this lane's own
  run-1 finding recommended closing, and closed it at both surface sizes: Email C++ dispositioned
  **80 of 80** units across two batches, both accepted first attempt, with **zero** bare kind
  prefixes where the 13:23 run on the identical packet produced 15 of 40 on attempt 1 and 12 of 40
  on attempt 2; PDF C++ dispositioned **124 of 124** across four. Neither repository was refused at
  S4 again in any of the three compositions run this session. Alternative rejected: none. Evidence:
  `dispositions.json` for each; the per-batch call records. Reversal: none; a measurement.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · TB-01 and arrival item (24) are settled in
  production, not just in receipts: BC-02 PASSES for `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` on
  both independent draws.** Run 1's finding LANE-B-RERUN2-F2 predicted this from `examples.json`
  alone; it is now observed twice at the check itself. Draw 1: 10 PASS, 0 FAIL, 1 PENDING. Draw 2:
  BC-01 through BC-09 all PASS - BC-02 among them - with BC-10 the only failure. So the sprint
  plan's "PDF-Cpp (24; TB-01 risk)" is answered: the risk did not materialise, the honesty rule was
  not bent, and the install command is SUPPORTED because the library's own CMake build genuinely
  succeeded with the recorded `g++` 16.2.0. Evidence: both runs' `validation.json`. Reversal: none.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · a defect in this lane's own file, found by
  the suite on the candidate's first seal: a plugin's fact emission order must be the order its own
  IDs sort in, or the sealed candidate cannot re-render its own bytes.** PDF C++ sealed on draw 1
  (state `ACCEPTED`, 30 provider calls, 174 visible lines of 599) and
  `tests/test_sealed_bytes.py::test_a_sealed_candidate_renders_to_its_own_bytes` immediately failed
  on it, with a twelve-line diff whose whole content is two swapped list items: Development
  Dependencies read `Python3` then `googletest` in the sealed README and `googletest` then
  `Python3` when re-rendered from the bundle's own `facts.json`. Cause, read from the code and
  confirmed by the bytes: `cpp.declared_dependencies` returned `sorted(found.items())`, keyed on the
  name the manifest spells, while `fact_id` lower-cases every part (`slug`) and
  `FactsDocument.to_json` writes the document sorted by ID - so `"Python3" < "googletest"` ('P' is
  ASCII 80, 'g' is 103) but `dependency:development.googletest < dependency:development.python3`.
  The live render saw emission order and the re-render saw ID order. `renderer._dependencies` takes
  `dependency` facts in document order by design and partitions them into required, optional and
  development, keeping document order inside each, so making that order canonical is the plugin's
  job. Fixed here in one line - `sorted(found.items(), key=lambda item: (slug(item[0]), item[0]))` -
  with a mutation test, `test_dependency_facts_are_emitted_in_the_order_their_own_ids_sort_in`,
  which pins the property that actually matters (every partition is already in ID order, since the
  global list interleaves the `dependency:<name>` and `dependency:development.<name>` namespaces)
  and which the old sort fails: reverted deliberately, red at the partition assertion; restored,
  green. Alternative rejected: adding the bundle to `test_sealed_bytes.py`'s `KNOWN_BLOCKED_STALE`.
  That file is not an owned path, and its two existing entries are bundles sealed *before* a
  deliberate rendering change - a brand-new seal that never rendered its own bytes is a defect to
  fix, not debt to record, and recording it would be weakening a check to protect a seal. The draw-1
  bundle was therefore removed rather than landed: its stored README does not match its own facts
  under any code, a bare re-render would leave validation and review judged against bytes that no
  longer exist (`test_sealed_bytes`'s own comment for Cells C++ makes exactly this point), and a
  real re-seal was the only honest route. Reversal: restore the raw-name sort; the candidate must
  then be re-sealed again. **PROPOSAL (primary loop, `core/facts.py` or
  `composition/renderer.py`):** every plugin is one case-sensitive name pair away from this, and
  nothing catches it until a candidate has already been sealed and paid for - 30 provider calls
  here. Either `FactsDocument` canonicalises its own order at construction the way `to_json` does at
  write time, or `_dependencies` sorts each partition by fact ID before rendering. Lane B fixed its
  own file because section 2 requires that of a class exposed in its own paths; the general guard is
  shared code and worth more than the one plugin.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · what the re-seal then measured, and it is
  the most important number this run produced: two draws of the same repository, differing only in
  the order of two dependency facts, agree on every deterministic check and disagree on the review
  verdict.** Draw 1: S4 124 units (VERIFIED_MOVE 45, SUPERSEDE_REDUNDANT 44, VERIFIED_PRESERVE 15,
  OMIT_UNSUPPORTED 11, DEFER_UNRESOLVED 5, NON_CONTENT 3, VERIFIED_REWRITE 1); plan 18/18 sections,
  12 hubs, examples 1+3, 5 links; 287 authored units; coherence revised 1; 174 visible lines of 599;
  validation 10 PASS / 0 FAIL / 1 PENDING; `independent_review` returned `REJECT_PRESENTATION`,
  PHASE1/F6's second reader corroborated 5 findings at seed+2, the verdict folded to `ACCEPT` with
  `second_reader.read = 2`, and the candidate sealed. Draw 2, with the one-line ordering fix and
  nothing else changed: S4 124 units but a materially different split (VERIFIED_REWRITE **9**,
  VERIFIED_MOVE 39, SUPERSEDE_REDUNDANT 47, OMIT_UNSUPPORTED 5, VERIFIED_PRESERVE 16); plan 18/18
  sections, 12 hubs, examples 1+**2**, **7** links; 285 authored units; coherence revised 0; 196
  visible lines of 588; BC-01 through BC-09 **all PASS**, BC-11 PENDING, and **BC-10 FAIL** -
  `REJECT_PRESENTATION`, 2 findings, one `targeted_repair` round which repaired F04 and re-raised an
  equivalent failure, `second_reader.read` with 10 corroborated findings. So the deterministic half
  of the pipeline is stable across the perturbation and the reviewer is not. Worth recording about
  the two findings themselves, because it bears on whether they are code-caused (loop-prompt
  section 5): F05 quotes the candidate's own sentence, "The second example reads and updates the
  document's title and author metadata...", and then faults the candidate for "incorrectly
  labelling the second example as" that same sentence - the quote and the complaint are the same
  text. F06 demands the candidate state "12 runnable examples", which is not a fact of this
  repository at any polarity: `facts.json` records **11** example candidates, 4 EXECUTED. Writing
  either repair as asked would put an unsupported claim in a public candidate, which rule 12
  forbids. Alternative rejected: a third composition. The packet is now cached, so a third run would
  re-roll only the batches the `cache_stale` defect forces live - which is precisely re-rolling
  until the reviewer says yes, and both the sprint plan's W-card rule ("real rejection ->
  disposition + move on (stop-don't-force)") and loop-prompt section 5 forbid it. Reversal: none;
  this is a measurement, and the disposition below is what it supports.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · PROPOSAL (primary loop, PORTFOLIO-WIDE,
  `core/llm/jobs.py::run_job` with `reconciliation/dispositions.py::citable_fact_ids` and
  `normalize`): the S4 enum makes every stored reply `normalize` touched permanently unreusable, so
  no candidate sealed since `352fd35` can pass a no-op proof.** `run_job` re-judges a stored output
  against the **same** `call_schema` before reusing it; for S4 that schema's `fact_ids` is the enum
  `citable_fact_ids()` builds, which is co-extensive with what the *model* may cite. But what is
  stored is the output the checks **accepted** - post-`normalize` - and `normalize` writes fact IDs
  by code that the packet never showed: `entry["fact_ids"] = sorted(cited | set(ids))` over
  `ids = rendering_fact_ids(destination, facts)`. Those code-written IDs sit outside the enum, the
  stored reply is schema-invalid on re-judge, `run_job` records `cache_stale`, and it makes a fresh
  live call - which is not zero provider calls, however deterministic the product is. Measured
  offline with zero provider calls by re-running `_parse` over each stored S4 record: PDF C++ batch
  1 REJECTED (3 of 40 entries cite `identity:revision`, which `bounded_records` excludes by name)
  and batch 2 REJECTED (5 of 40 cite `example:007`..`example:011`, 6 of 11 example facts shown),
  batches 3 and 4 reusable; Email C++ batch 1 REJECTED on `identity:revision` in 3 of 40, batch 2
  reusable. The same class at a 122-value enum as at a 361-value one, so it is not size-dependent.
  Observed live twice: the draw-1 no-op rerun recorded `repository_investigation` `cache_reuse`,
  then `source_reconciliation` `cache_stale` on request `fbf29a9da6e3` - **the same
  `request_sha256` the sealing run stored under**, so the key matched byte for byte and only the
  re-judgement refused it - then a live re-call of that identical request, rejected at `output
  truncated at the manifest's max_output_tokens (32000)`; and the draw-2 repair round hit
  `cache_stale` on two more batches while every `section_authoring` call around it reused cleanly.
  Fix, smallest first: re-judge a stored output against the **manifest's** own schema
  (`call_schema=None`) in the cache-reuse branch - the enum exists to constrain the decoder, not to
  re-adjudicate an output the checks already accepted and normalised, and `binding_errors` still
  refuses any ID naming no fact. Alternative: widen `citable_fact_ids` to admit every ID `normalize`
  may write, at the cost of showing the model IDs the packet did not, which is the RC1 risk its own
  docstring set out to avoid. Either needs a mutation test on a stored, normalised S4 reply: red
  before (`cache_stale`), green after (`cache_reuse`, zero provider calls). Alternative rejected:
  re-running until a draw happens to store only in-enum IDs - a lottery, not a fix, because
  `normalize` writes `identity:revision` whenever a unit folds into a section whose rendering facts
  include it, which is most repositories. Reversal: revert the fix; nothing else moves.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · second defect the same rerun exposed: the
  32,000-token S4 runaway is not closed in general, it is now provider-nondeterministic on an
  unchanged request.** The identical request `fbf29a9da6e3` returned **6,352** completion tokens on
  its first draw and **32,000** on its second. The enum bounds what the decoder may emit *per entry*
  and `maxItems` pins only the `dispositions` array to the batch size; neither bounds how long a
  rationale the decoder writes. So `S4-REGRESSION` is closed for its bare-prefix cause and open as a
  class. Recorded rather than proposed as separate work, because the fix above removes the re-call
  that exposed it. Worth noting for whoever picks it up: arrival item (56) - store a truncated
  reply's body - would have made this readable without a hand replay; here the body is gone, which
  is exactly the gap item 56 names.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · MEASUREMENT for lane E's PROPOSAL E3: the
  landed enum does not trip the gateway at 361 values, and E3 is not thereby closed.** Ten live S4
  calls across two repositories and three compositions, zero HTTP 400 of any kind. Measured offline
  before the first call, from `facts.json` through the production functions: Email C++ 357 facts ->
  82 packet fact records -> enum **122** values, 3,356 enum characters, 5,649-character schema,
  34,024-character packet, 80 units in 2 batches - essentially lane D's own validated 123, and the
  small-surface control E3 asked for. PDF C++ 1,846 facts (1,651 public symbols) -> 321 packet fact
  records -> enum **361** values, 13,730 enum characters, 16,732-character schema, 69,980-character
  packet, 124 units in 4 batches - 2.9x lane D's point. Why 361 and not 1,651: `bounded_records()`
  already caps the packet per kind, so the surface reaches the enum as 256 `public_symbol` records
  and 6 of 11 `example` records. The enum is therefore bounded today by construction, exactly as E3
  read the code to say; what was open was how large the bound gets and whether that size is safe,
  and 3x is now measured safe. What this does **not** close: PDF for Python at 689 and PDF for
  Java's far larger surface are still unmeasured, and one transient `http_error` did occur at S4
  (draw 1, batch 4, retried once and accepted with 375 completion tokens), so a size-related refusal
  is still distinguishable from noise only by its body - which item (56) would preserve. Lane E's own
  PDF-Python run remains the cheapest next point. Alternative rejected: reporting E3 refuted on two
  data points, which is what section 27.10 follow-up 3 prohibits. Reversal: none; a measurement.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · PROPOSAL (primary loop,
  `composition/planning.py::plan_checks`): arrival item (25) has **not** landed, and it is now the
  only thing between Email C++ and rendering.** The re-run request's premise was that item 25's
  class had landed; the code is the authority and says otherwise. `plan_checks` still reads
  `errors.append(...)` on `placement.outcome == "excluded"`;
  `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` holds five rows (36, 22, 32, 33, 23)
  and none is 25; and no commit in `planning.py`'s history carries the change. The sharper statement
  this draw permits: `reconciliation/dispositions.py::normalize` **already has the exact fold**,
  three files away - on `disposition in PLACING and destination in absent` it sets
  `DEFER_UNRESOLVED` with `destination_section: None`, under a comment saying no re-ask can honour a
  placement no plan may include - and it computes `absent` from `section_conditions(facts, policy)`,
  where `additional_examples` is `len(SUPPORTED examples) >= 2`. `plan_checks` then **overwrites
  that same key**, `conditions["additional_examples"] = bool(set(verified_examples) - starts)`,
  because the plan's quick starts consume examples, and appends an error instead of applying the
  identical fold. Measured: Email C++ has exactly 2 SUPPORTED examples (`example:001`, `:002`;
  `:003` and `:004` are CONTRADICTED on real diagnostics in their own code), the plan took both as
  `quick_start` and `second_quick_start`, the section flipped included -> excluded between S4 and
  S5, and 3 of the 7 units S4 placed there - `inherited_unit:028.paragraph`, `:030.paragraph`,
  `:032.paragraph` - became errors where the 2026-09-06 draw produced 1. The other 4 are a
  `code_block` and headings `renders_verbatim` already excludes. The planner did not make the
  placement, cannot withdraw it, and the rejection text ("place the unit in an included section or
  defer it") names no action the planner owns. Fix: defer on `outcome == "excluded"`, three lines,
  mirroring a branch already written and commented. Alternative rejected: making reconciliation
  conservative about `additional_examples`, which would lose real content for repositories whose
  plans leave an example over. Reversal: revert; Email C++ returns to this disposition.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · corroboration, not re-proposed: arrival item
  (42) on a third ecosystem.** Email C++'s S5 attempt 1 was rejected with `unknown fact ID
  format:msg; unknown fact ID format:eml; unknown fact ID format:cfb`. The repository has no
  `format` fact of any kind, so the planned capability titles named three formats with no verified
  fact behind them - item (42)'s class verbatim, previously measured on Python Note only. It
  recovered on attempt 2 and is not this repository's blocker, so it is recorded rather than
  re-filed, per the standing instruction that a queued item is not re-proposed. `352fd35` parked
  items 41 and 42 as strict xfails; this is a second ecosystem's evidence for 42 whenever they are
  unparked.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · the lane venv is built from
  `requirements-lock.txt`, not from the lane prompt's former literal `pip install -e .[dev]`, and
  the difference would have silently poisoned every seal this run produced.** Caught before the
  first provider call, on the reviewer's instruction and independently of lane F's own measurement.
  The bare extras install resolved **five** distributions past the lock - `anyio` 4.15.1 for 4.14.2,
  `ast_serialize` 0.11.1 for 0.8.0, `openai` 3.13.0 for 3.7.0, `ruff` 0.16.7 for 0.16.5,
  `types-PyYAML` 20260906 for 20260815 - and omitted `uv` entirely, giving 49 distributions and
  `_presenter_site_manifest_hash()` = `613b742b...`. The primary checkout and all 8 sealed bundles
  read `f4406f1b...` over 50. That value is in the *environment* dependency class, so a bundle
  sealed under `613b742b` reopens `EXTRACTING` the moment any other worker evaluates it and is
  reproducible by nobody. Rebuilt as `pip install -r requirements-lock.txt`, then `uv==0.12.9`, then
  `pip install -e . --no-deps`; `f4406f1b04d81ecdf2ea4e421776ef2be7f8cdc27090f395a815277a561fd411`
  confirmed before any candidate work and re-confirmed after the rebase. Alternative rejected:
  sealing first and re-sealing later - the bundle's own `dependencies.json` would have carried the
  wrong hash into merged history. Evidence: the two hashes and the five-line `diff` of the
  distribution lists. Reversal: none; `08307b9` has since fixed the lane prompt's own text.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · DISPOSITION (revised) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_REVIEW (BC-10)`.** Was
  `BLOCKED_VALIDATION (BC-02)`; BC-02 now passes on both draws and is no longer this candidate's
  blocker, which is the question the sprint plan's "PDF-Cpp (24; TB-01 risk)" asked. 1,521 tree
  entries, 1,846 facts (1,651 public symbols, 1,839 SUPPORTED, 5 UNRESOLVED, 2 CONTRADICTED),
  required contract rows without evidence: none; 11 examples - 4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED
  on the incomplete-type defect in `facades/facade.hpp` recorded 2026-09-06. S3 accepted first
  attempt; S4 all four batches accepted, 124 of 124 units; S5 accepted, 18 of 18 sections; S6 wrote
  285 units across 9 sections; 196 visible lines of 588. Validation: **BC-01 through BC-09 PASS**,
  BC-11 PENDING, **BC-10 FAIL** on `REJECT_PRESENTATION` with the two findings analysed above, one
  `targeted_repair` round, equivalent failure re-raised. The candidate sealed on the immediately
  preceding draw with 10 PASS and a folded `ACCEPT`, so the cause is review nondeterminism, not
  anything about this repository or its facts - a deliberate stop rather than a forced seal, per the
  W-card rule. Resume predicate: a re-run once either the reviewer-side guard for a
  self-quoting/unsupported-repair finding lands (the class the recent `3784b06` and `a8ac6d4`
  commits are already chasing) or the primary decides this candidate is sealable on the strength of
  BC-01..BC-09 plus a corroborated second read; behind that, the `cache_stale` PROPOSAL above must
  land before *any* draw of it can pass a no-op proof and count toward N/34.

- **2026-09-11 16:04 (`date` checked) · G4-W13-RERUN2 · DISPOSITION (restated) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93` - `BLOCKED_PLANNING` (S5).** Unchanged
  in class from 2026-09-06 14:29, widened in blast radius from 1 unit to 3, and this time earned
  against working upstream stages rather than recorded in the shadow of a portfolio-wide outage: 75
  tree entries, 357 facts (225 public symbols, 355 SUPPORTED, **0 UNRESOLVED**, 2 CONTRADICTED), no
  required contract row without evidence, 4 examples of which 2 are EXECUTED and 2 FAILED, S3
  accepted first attempt, **S4 both batches accepted first attempt** with 80 of 80 units and no bare
  prefix. S5 rejected twice - attempt 1 on item (42)'s unverified formats, attempt 2 on the three
  excluded-section placements - and the transaction failed closed. Nothing else stands in the way;
  its `install_command:cmake` is SUPPORTED. Resume predicate: arrival item (25) lands (the
  `plan_checks` deferral above); then re-run `present --repo
  aspose-email-foss/Aspose.Email-FOSS-for-Cpp`.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · the lane's own headline PROPOSAL is closed
  by measurement: `22c2e45` removes the `cache_stale` class, and it removes it on the repository
  that diagnosed it.** Measured against `origin/main` at `22c2e45` from a fresh worktree at
  `C:\w\b03` with nothing carried over from run 2 - no call store, no clone, no bundle, so every
  reuse below was written by this run's own process. `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`'s
  ledger holds **79 rows: 44 `cache_reuse`, 33 completed provider calls, 2 output rejections, and
  zero `cache_stale` of any kind** - S6 32, S4 8, S3 2, S5 2. S4 is exactly the class run 2 measured
  as permanently unreusable here (2 of 4 stored batches, `identity:revision` and
  `example:007`..`:011` written by `normalize` outside the decoder's enum); all 8 S4 reuses were
  accepted this run. The reuse is also what made the run affordable: 33 calls carried a pipeline
  that re-ran S3 through S6 four times across three repair rounds. What this does **not** prove: a
  no-op proof still needs a sealed bundle to re-open, and this run sealed nothing, so
  `RENDERER_VERSION` 19 and this lane's own `40f2e9d` ordering fix remain untested against sealed
  bytes - the re-run request's expectation that PDF C++'s dependency order is "doubly correct" is
  not asserted here, because no sealed README exists to compare. Alternative rejected: none.
  Evidence: `calls.jsonl`, dispositions `Counter({'cache_reuse': 44, 'provider_call': 35})`.
  Reversal: none; a measurement.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · PROPOSAL (primary loop,
  `review/independent/review.py`): a presentation finding that calls a claim unsupported while
  citing a SUPPORTED fact whose value stands verbatim in its own quote is the reviewer's own
  defect - and this one made the repair stage delete a true, fact-backed sentence from the
  candidate.** The draw's first review blocked on one finding, F08: criterion `presentation`,
  section `quick_start`, quote `using Aspose_PDF_FOSS version 1.0.0.`, `fact_ids`
  `['example:001', 'package:version']`, text "the facts do not support a versioned claim", repair
  "Remove 'version 1.0.0'". `facts.json` records `package:name` = `Aspose_PDF_FOSS` and
  `package:version` = `1.0.0`, both **SUPPORTED**, and the S3 investigation's own `product_summary`
  cites `package:version` as its evidence. The finding names, as its own evidence, the fact that
  verifies the sentence it calls unverified. Nothing folded it: `factuality_defect` judges
  criterion `factuality` only, `absence_defect` needs an `absent` list and F08's is empty, and
  `a8ac6d4`'s `_quoted_verified_fact` folds a quote referencing a SUPPORTED **`public_symbol`** -
  `package` is a different kind. `targeted_repair` then obeyed it: `repairs.json` attempt
  `65d25781` rewrote the unit from "...at 150 DPI using Aspose_PDF_FOSS version 1.0.0." to
  "...using Aspose_PDF_FOSS.". A verified detail left a public candidate because a finding
  contradicted its own citation. Fix, mirroring `a8ac6d4` exactly one kind wider: a finding whose
  quote contains the literal value of a SUPPORTED fact it itself cites is a reviewer scope defect.
  Mutation test: this finding against these facts - red (blocks, repair fires) before, green
  (advisory) after. Alternative rejected: widening `_quoted_verified_fact` to match every fact kind
  by suffix, which reintroduces the coincidental-word-overlap collision `a8ac6d4` was written to
  stop. Reversal: revert; the finding blocks again.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · PROPOSAL (primary loop, `absence_defect` in
  `review/independent/review.py`, with `repair/targeted.py` as the consumer): a finding whose
  *refuted* claims are the ones its repair instruction names is unactionable, and here the reviewer
  faulted the candidate for omitting the exact sentence the previous repair round had just inserted
  at BC-08's demand.** The order inside one transaction, from the ledger and `repairs.json`: (1)
  BC-08 **FAIL** - `inherited_unit:019.paragraph` is VERIFIED_PRESERVE and keeps the command
  `cmake --preset windows-msvc-debug`, which the candidate did not render; (2) `targeted_repair`
  attempt `1c50ad99` appended "The build instructions include the command cmake --preset
  windows-msvc-debug." to the `development_testing` unit; (3) the final review raised F10 on that
  same section - "omits the CMake preset instructions and the test suite coverage details", repair
  "Restore the CMake preset instructions..." - and **its quote is that repaired sentence, character
  for character**. Replayed offline through the production functions: of F10's five `absent`
  claims, three (`cmake --preset windows-msvc-debug`, `976 test files`, `foundation primitives`)
  are located in its own section slice and two (`src/public/`, `src/internal/`) are genuinely
  absent and present in the evidence, so `absence_defect` returns `None` and the finding blocks -
  correctly, under the 2026-09-07 rule that one unrefuted claim leaves a real remainder. The defect
  is not that rule. It is that the finding's prose, quote and repair instruction all name the
  refuted claims while the remainder is two strings none of them mentions, so a repair round is
  handed work already done and the equivalent failure re-raises. Fix: narrow rather than dismiss -
  record the refuted claims on the finding and hand `targeted_repair` only the survivors, so the
  repair asks for `src/public/` and `src/internal/` or the finding carries no actionable claim at
  all. Mutation test: this finding and this candidate - red (repair told to restore text that is
  present) before, green after. Alternative rejected: whole-finding dismissal, which the 2026-09-07
  external review already proved loses real gaps. Reversal: revert; F10 blocks again.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · three draws of one repository at one
  revision: every deterministic check agrees, and the reviewer's blocking set does not repeat
  once.** Same repository, same revision `888700a`, byte-identical extraction all three times
  (1,846 facts, 1,651 public symbols, 11 examples - 4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED). Draw 1:
  10 PASS, 0 FAIL, review folded to `ACCEPT` with `second_reader.read` 2, sealed. Draw 2:
  BC-01..BC-09 PASS, BC-10 FAIL on F05 (self-quoting) and F06 (a 12-vs-11 example miscount). Draw
  3, this run: BC-01..BC-09 PASS (BC-08 after one repair), BC-11 PENDING, BC-10 FAIL on F06 (a
  prose judgment, corroborated by the second read, that `quick_start` names no project structure or
  build command) and F10 (the repair-then-fault loop above). **No blocking finding recurs between
  draws 2 and 3.** The S4 split moved again too - this draw SUPERSEDE_REDUNDANT 50,
  OMIT_UNSUPPORTED 29, VERIFIED_PRESERVE 27, VERIFIED_MOVE 8, DEFER_UNRESOLVED 5, VERIFIED_REWRITE
  3, NON_CONTENT 2, against draw 2's MOVE 39 / SUPERSEDE 47 / OMIT 5 / PRESERVE 16 / REWRITE 9 -
  while the checks that read the result agree. Worth recording beside it: the fold stack is working
  hard, not idle. Of 15 findings in the final review, **13 folded to advisory as reviewer scope
  defects** (four on `a8ac6d4`'s symbol rule, three on renderer-owned sections, two on
  contract-required headings, three on a CONTRADICTED example, one on an absence the candidate
  contains); the guards are not why this candidate did not seal, they are why only two findings had
  to be judged. Alternative rejected: reading draw 3 as evidence the reviewer is simply strict - it
  cannot be, since draw 1 accepted the same document class outright. Reversal: none; a measurement.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · DECISION · PDF C++ is not drawn a fourth
  time.** Draws 2 and 3 are two genuine BC-10 rejections of the same candidate, and loop-prompt
  section 5 prohibits a third equivalent attempt; the sprint's W-card rule says a real rejection
  earns a disposition and a move on. Everything that could change the outcome is shared code this
  lane may not edit - the two PROPOSALs above. Alternative rejected: a fourth draw. The packet is
  cached and reuse now works, so a fourth draw would re-roll only the review, which is re-rolling
  until the reviewer says yes - the exact thing the W-card forbids, and cheaper to do now than ever
  before, which is why the rule matters more, not less. Evidence: this run's `review.json`,
  verdict `REJECT_PRESENTATION`, reported literally. Reversal: the resume predicate in the
  disposition below.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · corroboration, not re-proposed: arrival
  item (42) on a second C++ repository.** PDF C++'s `presentation_planning` attempt 1 was refused
  by the binding with `unknown fact ID format:pdf; format:png; format:jpeg; format:bmp;
  format:tiff; format:text`. The repository has no fact of kind `format` at any polarity, and
  `planning.py` reads `at_a_glance`'s `input_format_ids`/`output_format_ids` against IDs starting
  `format:input.`/`format:output.`. Attempt 2 was accepted, so this is not PDF C++'s blocker. Run 2
  recorded the identical class on Email C++ (`format:msg`, `:eml`, `:cfb`) and lane E on Python
  Note; this is the third repository. Recorded rather than re-filed: item (42) is queued and a
  queued item is not re-proposed. Reversal: none.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · arrival item (25) is still not landed,
  re-verified two ways, so Email C++ was not run at all.** (1) `composition/planning.py:385` still
  reads `errors.append(...)` on `placement.outcome == "excluded"`. (2)
  `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` now holds thirteen rows - 36, 22, 32,
  33, 23, 55, 39, 40, 44, 45, 46, 60, 61 - and none is 25. Measured today on the repository's own
  freshly extracted facts (`facts-only` preflight, zero provider calls, 357 records, 355 SUPPORTED,
  0 UNRESOLVED, 2 CONTRADICTED, no required contract row without evidence) and replayed through the
  production functions: exactly 2 SUPPORTED examples (`example:001`, `example:002`);
  `section_conditions(facts, DEFAULT_POLICY)["additional_examples"]` is `True`, which is the value
  reconciliation computes `absent` from at S4; `plan_checks`'s own
  `bool(set(verified_examples) - starts)` is `True` with zero or one quick start and **`False` with
  two**, which is what the plan takes. The flip is still mechanical, not a draw. Alternative
  rejected: running it anyway to "see" - a stage known to be broken for this repository does not
  earn a fresh verdict, and it would have cost provider calls to restate a disposition already
  earned against working upstream stages on 2026-09-11 16:04. Evidence: the two checks above and
  the offline replay. Reversal: item (25) lands; then re-run it.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · DISPOSITION (restated) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_REVIEW (BC-10)`.** Unchanged in
  class from 2026-09-11 16:04 and earned a second time on cleared ground: the S4 blocker is gone,
  the cache blocker is gone, BC-01 through BC-09 all PASS. 1,846 facts (1,651 public symbols, 1,839
  SUPPORTED, 5 UNRESOLVED, 2 CONTRADICTED), no required contract row without evidence, 11 examples
  (4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED). S3 accepted first attempt; S4 all four batches accepted
  first attempt, 124 of 124 units; S5 refused once on `format:` IDs and accepted on attempt 2, 18
  of 18 sections, 12 hubs, examples 1+2, 9 links; S6 287 units across 9 sections, coherence revised
  0 of 287; **197 visible lines of 594**. First validation 8 PASS / 1 FAIL (BC-08) / 2 PENDING;
  after two repair rounds 9 PASS / 1 FAIL / 1 PENDING. Review: **`REJECT_PRESENTATION`**, 2
  blocking findings, 13 advisory, `second_reader.read` 2 with 10 corroborated classes; `repairs.json`
  2 repaired, 0 unrepairable, 3 rounds. 33 provider calls, 44 cache reuses, 0 `cache_stale`, 68,128
  completion tokens. Resume predicate: re-run once **either** PROPOSAL above lands - the first alone
  would have left this draw's first review with no blocking finding, the second would have stopped
  the repair loop from manufacturing F10 - or once the primary rules the candidate sealable on
  BC-01..BC-09 plus a corroborated second read. Not before: draws 2 and 3 are already two genuine
  BC-10 rejections.

- **2026-09-11 17:50 (`date` checked) · G4-W13-RERUN3 · DISPOSITION (restated, no run) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93` - `BLOCKED_PLANNING` (S5).** Unchanged
  from 2026-09-11 16:04; its sole resume predicate, arrival item (25), is measurably unmet at
  `22c2e45` (entry above), so no provider call was spent on it. Today's facts-only preflight
  reproduces the repository exactly as run 2 recorded it: 75 tree entries, 357 facts (225 public
  symbols, 355 SUPPORTED, 0 UNRESOLVED, 2 CONTRADICTED), 4 examples of which 2 EXECUTED and 2
  FAILED, no required contract row without evidence, `install_command:cmake` SUPPORTED. Resume
  predicate: arrival item (25) lands (three lines in `composition/planning.py`, mirroring the fold
  `reconciliation/dispositions.py::normalize` already applies); then re-run `present --repo
  aspose-email-foss/Aspose.Email-FOSS-for-Cpp`.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · the run's own question is unanswered, and
  that is the finding: PDF C++ failed closed at BC-08 two stages before the review, so arrival
  items 63 and 64 were never exercised on it.** Drawn from a fresh worktree at `C:\w\b04` cut from
  `origin/main` at `23a8905` (which carries `2d4875d`, item 63, this lane's own `LANE-B-R3-F2`),
  then rebased mid-run onto `846eaaf` (item 64, this lane's own `LANE-B-R3-F3`) on the reviewer's
  instruction. Environment confirmed at `f4406f1b…` before the first provider call and again after
  the rebase. The transaction failed closed at **BC-08 `Protected content preserved`,
  causal stage COMPOSING**: 8 PASS, 1 FAIL, 2 PENDING, unchanged by the repair round. The call
  ledger holds **zero `S10` rows** across both draws and there is no `review.json`; **BC-10 is
  `PENDING`, not a verdict**, and is reported as such rather than as any kind of rejection. Nothing
  sealed; `sealed_by_lane` stays 0 and `repository-presenter status` reads 9/34, unchanged.
  Alternative rejected: describing this as a BC-10 outcome of any sign, which would be a claim
  about a stage that did not run. Reversal: none; a measurement.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · PROPOSAL (primary loop,
  `repair/targeted.py::validation_defects`): a blocking check that fails in two LLM-owned sections
  is repaired in only the first of them, and the second is never attempted at all.** BC-08 raised
  three failures this draw, all of the same command: `inherited_unit:026.paragraph` and
  `inherited_unit:028.paragraph` (both `VERIFIED_REWRITE`) in `additional_examples`, and
  `inherited_unit:111.code_block` (`CORRECT_WITH_EVIDENCE`) in `development_testing` - each
  "keeps the command `cmake --build build` but the candidate does not render it".
  `validation_defects` builds one `Defect` per failing check and sets its section to
  `named[0] if named else None` (lines 204-212), so the whole check routes to `additional_examples`
  and `repair_packet` hands the model that section's `stage_output` alone. No revision of
  `additional_examples` can make `development_testing` render anything, so the third failure is
  unrepairable by construction; the next validation sees the equivalent failure standing and the
  transaction fails closed. Replayed mechanically through the production function on this run's own
  artifacts: `llm_sections` is the nine authored sections including `development_testing`,
  `validation_defects` returns exactly **1** defect, `section_id` `additional_examples`, carrying
  all three failures in its record but able to revise one section. Fix: one repairable defect per
  failing *(check, LLM-owned section)* pair, each with its own fingerprint and its own attempt.
  Mutation test: this `validation.json` and these nine sections - red (one defect,
  `development_testing` never attempted) before, green (two defects) after. Alternative rejected:
  widening the one packet to carry every named section's output, which asks a single reply to
  revise several stages' artifacts and loses `repair_checks`' per-section binding - the RC1
  rejection family the packet's narrowing exists to stop. Reversal: revert; the second section goes
  unattempted again.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · PROPOSAL (primary loop,
  `repair/targeted.py::repair_packet`): a BC-08 protected-content repair is asked to restore text
  whose only SUPPORTED fact is an `inherited_unit` - the one kind the packet strips out.** BC-08's
  entire subject is a protected `inherited_unit`'s own text, and `repair_packet` builds its records
  as `kinds = [kind for kind in FACT_KINDS if kind != "inherited_unit"]` (line 376), so the packet
  for a BC-08 repair carries every kind except the one the defect is about. Measured here: exactly
  **four** facts contain the string `cmake --build build` and **all four are `inherited_unit`**
  (`018.code_block` `SUPERSEDE_REDUNDANT`, `026.paragraph`, `028.paragraph`, `111.code_block`),
  while `install_command:cmake`'s own value stops at `cmake -S . -B build` - the configure step,
  which is exactly what the candidate does render (README line 67). BC-04 requires every content
  unit to cite existing SUPPORTED facts, so the repair is asked for a command it has no citable
  fact for. The model's answer was the same both times: the targeted unit returned unchanged
  (`before` == `after` == "Encrypt a document using AES-256 with user and owner passwords."),
  outcome `repaired`, BC-08 re-raised. That is a **no-op measured twice, under two prompts and two
  request hashes** - `a533743c` under `targeted_repair` 8 and `85353fed` under `targeted_repair` 9,
  each a live call - so it is a property of the packet, not of one reply. Fix: a BC-08 packet
  carries the protected `inherited_unit` records its own defect names; the exclusion exists to stop
  a repair citing a corpus it was not authoring, not to withhold the evidence the defect is about.
  Mutation test: this defect and these facts - red (no fact in the packet carries
  `cmake --build build`) before, green after. Alternative rejected: letting BC-08 accept an
  uncited paraphrase, which weakens a blocking check and is prohibited. Reversal: revert; the
  packet is silent about the defect's own facts again.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · a prompt-version bump isolated to a single
  call: the same transaction replayed across a code rebase for one provider call and
  byte-identical bytes.** Draw A on `23a8905` (`REVIEWER_LOGIC_VERSION` 4, `targeted_repair`
  prompt 8): 49 ledger rows, 26 provider calls, 23 cache reuses, 1 `response_invalid`, 52,980
  completion tokens. The worktree was then rebased onto `846eaaf`, and the identical `present`
  invocation produced 47 further rows of which **46 were `cache_reuse` and exactly one was live** -
  the `targeted_repair` under prompt 9, 1,469 tokens - because the prompt change moved that one
  request's hash and nothing else's. Every digest was unchanged: source `d2b6a656…`, facts
  `bd8f4a98…`, dispositions `db09fe4a…`, plan `e035dee1…`, units `33c62e26…`, README `5fa7f2ee…`,
  validation `e6c39d54…`. Two consequences: the store's reuse is exact and prompt-addressed (96
  rows, **zero `cache_stale`**, on a transaction independent of run 3's, corroborating the lane's
  closed headline PROPOSAL a second time), and the repair no-op above survives a prompt revision,
  which is what makes it a packet property. Alternative rejected: none. Reversal: none; a
  measurement.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · four draws of one repository at one
  revision: the blocking check has now moved three times while the facts never moved once.**
  Byte-identical extraction in all four (1,846 facts, 1,651 public symbols, 11 examples - 4
  EXECUTED, 2 FAILED, 5 NOT_VERIFIED). Draw 1: 10 PASS, 0 FAIL, `ACCEPT`, sealed and then withdrawn
  over this lane's own dependency-ordering defect. Draw 2: BC-01..BC-09 PASS, BC-10 FAIL (F05,
  F06). Draw 3: BC-01..BC-09 PASS after one BC-08 repair, BC-10 FAIL (F06, F10). Draw 4: **BC-08
  FAIL, BC-10 never judged**. BC-08 was raised in draws 3 and 4 alike and repaired in draw 3 only;
  the difference is not in the facts, the checks or the code but in where the S6 composition placed
  a protected command - 285 units against 287, `VERIFIED_PRESERVE` 45 against 27,
  `OMIT_UNSUPPORTED` 12 against 29. The honest reading is that this candidate's blocker is not one
  defect but a sequence of drawn ones: BC-02, then BC-10 twice, now BC-08. Alternative rejected:
  reading draw 4 as a regression from the fixes that landed between draws 3 and 4 - it cannot be,
  since both landed in `review/`, which this draw never reached. Reversal: none; a measurement.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · DECISION · PDF C++ is not drawn a fifth
  time in this box, and the candidate is not forced.** The transaction is byte-reproducible from
  its own call store, so a re-run cannot change the outcome; the only route to a different draw is
  to clear the store and re-roll the composition. Draw 3's decision entry already ruled that
  re-rolling until a check says yes is what the W-card's stop-don't-force forbids, and reuse having
  made a re-roll cheap is a reason the rule matters more, not less. Both causes are named
  mechanically above and both are shared code this lane may not edit. Nothing here weakens BC-08:
  the check is **right** - the candidate genuinely omits a build command that three protected
  inherited units keep and the upstream README carries, which is a real gap under loop-prompt rule
  8, not a false positive. Alternative rejected: deleting `runs/transactions/…/calls` and drawing
  again, spending ~26 live calls on a coin flip whose odds the four-draw record above puts at one
  in two. Evidence: this run's `validation.json`, BC-08 FAIL and BC-10 PENDING, reported literally.
  Reversal: the resume predicate in the disposition below.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · DISPOSITION (moved) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_COMPOSING (BC-08)`.** Moved
  rather than restated: draws 2 and 3 were `BLOCKED_REVIEW (BC-10)` and this draw never reached
  review. 1,846 facts, no required contract row without evidence, 11 examples (4 EXECUTED, 2
  FAILED, 5 NOT_VERIFIED). S3 8 capabilities / 5 workflows / 4 limitations; S4 124 of 124 units;
  S5 18 of 18 sections, 12 hubs, examples 1+2, 7 links; S6 285 units across 9 sections, coherence
  revised 0 of 285; **180 visible lines of 583**. Validation 8 PASS / 1 FAIL / 2 PENDING before and
  after the repair round - BC-01..BC-07 and BC-09 PASS, BC-08 FAIL at COMPOSING on three failures,
  BC-10 and BC-11 PENDING. 27 provider calls, 1 output rejection, 69 cache reuses, 0 `cache_stale`,
  54,449 completion tokens across both draws. Resume predicate: re-run once **either** PROPOSAL
  `LANE-B-R4-F1` (one repairable defect per failing check-and-section pair) or `LANE-B-R4-F2` (a
  BC-08 packet carries the `inherited_unit` records its defect names) lands. Until one does, BC-08
  is decided by where the composition happens to place a protected command, and arrival items 63
  and 64 stay untested on this repository.

- **2026-09-11 21:30 (`date` checked) · G4-W13-RERUN4 · DISPOSITION (restated, no run, no call) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93` - `BLOCKED_PLANNING` (S5).** Outside
  this run's named scope, and its sole predicate is still unmet at `846eaaf`:
  `composition/planning.py` still appends an error on `placement.outcome == "excluded"` where
  `reconciliation/dispositions.py::normalize` defers, and
  `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` now holds fifteen rows - 36, 22, 32,
  33, 23, 55, 39, 40, 44, 45, 46, 60, 61, 62, 63 - and none is 25. Resume predicate: arrival item
  (25) lands; then re-run `present --repo aspose-email-foss/Aspose.Email-FOSS-for-Cpp`.
- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · FINDING (lane-owned, fixed here) · a
  configure that does not complete threw away every dependency header it had already fetched, and
  that cost Aspose.Slides for C++ a required contract row.** `cpp_examples.build_product` returned
  `("configure failed", [])` on a non-zero configure, discarding `fetched_includes(build)` — the
  directories that same step had already written. Slides' public `shape_collection.h` opens with
  `#include <pugixml.hpp>`, so all ten examples stopped in a header with no diagnostic of their own
  and were honestly recorded `NOT_VERIFIED`; `quick_start`'s only evidence kind is `example`, so
  preflight read `required rows without evidence: quick_start`. Measured: the run's own workspace
  `runs/verify/dd476f154c80/cmake-build/_deps` held `pugixml-{src,build,subbuild}` and nothing else —
  cut off after pugixml, before miniz and GoogleTest — while `_deps/pugixml-src/src/pugixml.hpp`, the
  exact directory `fetched_includes` returns, was on disk throughout. Before: `not_verified 10`,
  `3000 supported, 11 unresolved`, `without evidence: quick_start`. After the one-line fix, same
  revision, same machine: `executed 9, not_verified 1`, `3010 supported, 1 unresolved`, `without
  evidence: none`. Alternative rejected: raising the ceiling alone — no ceiling this side of
  `core.execution.MAX_TIMEOUT_SECONDS` can outrun a slow enough link. Reversal: restore the early
  `[]`; `test_a_configure_cut_off_still_hands_back_what_it_already_fetched` then fails.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · FINDING (lane-owned, fixed here) · the
  configure ceiling sat below the measured spread of the step it bounds, and a receipt called a step
  that was cut off "failed".** `_TIMEOUT_CONFIGURE` was 180 s for the one network-bound step in the
  C++ verifier: `FetchContent` downloads one archive per `find_package` that finds nothing, and this
  repository fetches three (pugixml v1.14, miniz 3.0.2, GoogleTest v1.15.2). Measured 2026-09-16,
  three cold configures of one revision on one machine: `Configuring done` at 57.8 s, 71.7 s and
  141.7 s — a 2.4x spread — with the run that produced this transaction's first receipts past 180 s.
  Raised to 300 s, which is `MAX_TIMEOUT_SECONDS` itself; 600.0 was refused outright with `ValueError:
  example timeout must be within (0, 300] seconds`, which is how the cap was found. The receipt phrase
  now separates `configure timed out` from `configure failed` — saying a step failed when it was cut
  off is not true — and neither is `succeeded`, so `build_verified` stays false either way and TB-01 is
  not loosened. Alternative rejected: fitting the number to the 141.7 s sample (§3 forbids a threshold
  from one measurement). Reversal: the constant and
  `test_the_configure_ceiling_clears_the_measured_download_spread`.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · PROPOSAL `LANE-B-R5-F3` (shared code) ·
  `review/independent/review.py`, `scope_defect`: a presentation finding is never asked whether its
  own quote lies in the section it names.** F09 is the only one of nine findings to survive the fold
  stack, and it blocks BC-10. It sets `section_id: enterprise_relationship`, cites
  `link_target:product.enterprise`, says the candidate's "Enterprise Relationship section is
  promotional … while the original README does not contain such a section", and asks to remove it.
  Three mechanical refutations. (1) `docs/README_CONTRACT.md` row 18 gives that slot the heading
  **`none` (closing paragraph of Scope and Limitations)**; the candidate emits no such heading, and the
  slot's single unit renders at line 634 as row 18's prescribed sentence, `These limitations don't
  apply to [Aspose.Slides for Cpp — Enterprise Edition](https://products.aspose.com/slides/cpp/)`.
  (2) The finding's own quote — `There is no API for these. The member named is the one that does not
  exist, so a call to it is a` — is rendered at line 605 under `## Scope and Limitations` (line 594),
  and `_carried_by_units` reports no content unit wrote it. (3) The cited fact is what makes the
  paragraph mandatory: `link_target:product.enterprise` is SUPPORTED with evidence `HTTP 200;
  enterprise target; platform level; slug cpp`, exactly row 18's condition. Why every fold returns
  None, replayed through the production functions on this run's artifacts: `_STRUCTURAL_SECTIONS` is
  `{document, structure}`; `_DETERMINISTIC_SECTIONS` is nine sections, not this one; `_SECTION_HEADINGS`
  is built only from shell sections that *have* a heading, so the one slot the contract gives heading
  `none` can never match `_quoted_heading`; `_quoted_chrome` is None; and `cited_fact_defect` (arrival
  item 63, this lane's own run-3 PROPOSAL) folds only when the quote contains a cited fact's literal
  value — here a URL the quote does not contain. The rule that would have caught it on its merits,
  `renderer_owned_defect`'s "judging against the original README as the standard of support" (lane D
  P16), is gated behind `_quoted_verified_fact`, scoped to `public_symbol` alone, so a `link_target`
  citation cannot reach it. Proposed: before the criterion switch, refute a finding whose quote is
  rendered in a section other than the one its own `section_id` names. Evidence: `absence_defect`,
  `excluded_evidence_defect`, `rendered_defect` and `renderer_owned_defect` each returned None on F09
  with this run's real `content_units.json` and `README.md`; production agrees, having recorded F09
  blocking rather than advisory. Reversal: the proposal's own mutation test.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · PROPOSAL `LANE-B-R5-F4` (shared code) · a
  finding whose repair instruction is "remove this slot" is routed to a stage that can only rewrite a
  unit.** This is the mechanical proof that F09 is not repairable content work rather than an opinion
  about it. `repairs.json` holds exactly one attempt — label F09, `section_id enterprise_relationship`,
  stage S6, outcome `unrepairable`, `re_raised [F09]` — with reason `targeted_repair: output rejected
  twice; last rejection: revised_output.units[0].fact_ids: [] should be non-empty;
  revised_output.units[0].text: '' should be non-empty`. The repair understood the instruction and
  tried: the only expression of "remove this" available to a unit revision is an empty unit, and a unit
  must cite facts and carry text. Whether a slot is composed at all is S5's decision and the shell's at
  render time, never a unit's. Proposed: route a removal-of-a-section finding to the stage that owns
  that decision, or refuse it as unactionable at routing, rather than spending four live calls proving
  a schema forbids the only reply. Evidence: the ledger's S11 rows — 4 provider calls, 0 cache reuses,
  all four `response_invalid` on the same rejection. Reversal: none; a measurement plus a proposal.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · PROPOSAL `LANE-B-R5-P2` (shared code, low
  priority, not blocking) · one ceiling bounds both a compile-bound step and a network-bound one.**
  `core/execution.py`'s `MAX_TIMEOUT_SECONDS` is 300 and `execute()` refuses any larger
  `timeout_seconds`, so no platform module can give a dependency download more headroom than a build.
  Recorded rather than pressed, because the finding above removes the consequence: a configure that
  runs out of time now keeps the headers it fetched, so the examples are still verified and only
  `build_verified` is honestly withheld. Alternative rejected: proposing it as a blocker — it is not
  one any more. Reversal: none needed.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · MEASUREMENT · the largest surface any lane B
  draw has carried produced no HTTP 400 and no `cache_stale`.** Lane E's PROPOSAL E3 anticipated a
  large `fact_ids` enum being refused by the provider. Run 2 measured 122 enum values for Email C++
  (357 facts) and 361 for PDF C++ (1,846 facts), against lane D's validated 123, with no 400. Slides
  C++ is **3,011 facts and 2,845 public symbols**, 1.6x PDF C++, and all 31 of its provider calls
  returned HTTP 200. Separately, run 2's headline PROPOSAL — no candidate sealed since `352fd35` could
  pass a no-op proof — stays closed on a third independent repository: 54 ledger rows, 23
  `cache_reuse`, **zero** `cache_stale`. Alternative rejected: none. Reversal: none; a measurement.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · DECISION · Slides C++ is not drawn a second
  time in this box, and the candidate is not forced.** BC-01..BC-09 all PASS and `second_reader.read`
  is already 2 with five corroborated ids, so the only thing between this candidate and a seal is one
  finding whose every refutation is named mechanically above and whose repair the schema forbids. The
  transaction is reproducible from its own call store (zero `cache_stale` across 54 rows), so a re-run
  cannot change the outcome; the only route to a different draw is to clear the store and re-roll,
  which draws 3 and 4 of this lane already ruled is what the W-card's stop-don't-force forbids, and
  reuse having made a re-roll cheap is a reason the rule matters more, not less. Nothing here weakens
  BC-10: the *check* is right and the *verdict* is reported literally; what is wrong is one finding,
  and the fix for it is shared code this lane may not edit. Alternative rejected: deleting the call
  store and drawing again on a first draw. Reversal: the resume predicate below.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · DISPOSITION (moved) ·
  `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp` at `1e347e8` — `BLOCKED_REVIEW (BC-10)`.** Moved,
  not restated: the standing disposition was `BLOCKED_AUTHORING` at S6 `section_authoring`
  (2026-09-06), and that day's 14:29 re-run added BC-02 and BC-08 at validation. All three are gone —
  **arrival item 26 delivered exactly what `unblocked.jsonl` says it unlocks: BC-08 PASSES**, and BC-02
  PASSES besides, because the library's own CMake build genuinely succeeds with the recorded g++ 16.2.0
  so TB-01's `build_verified` is earned rather than defaulted. 3,011 facts (2,845 public symbols), no
  required contract row without evidence, 10 examples (9 EXECUTED, 1 NOT_VERIFIED — the documented
  unbound-fence class). S3 8 capabilities / 6 workflows / 6 limitations; S4 **95 of 95 units, first
  attempt, zero bare kind prefixes**; S5 18 of 18 sections; S6 269 units across 9 sections, coherence
  revised 0 of 269; **243 visible lines of 662**, against 202 of 629 on 2026-09-06. Validation 9 PASS /
  1 FAIL / 1 PENDING: BC-01..BC-09 PASS, BC-10 FAIL at COMPOSING on `REJECT_PRESENTATION`, BC-11 PENDING
  (S12 never reached). 31 provider calls, 23 cache reuses, 0 `cache_stale`, 4 output rejections, 45,763
  completion tokens. Resume predicate: re-run once PROPOSAL `LANE-B-R5-F3` lands, or once the primary
  rules it sealable on BC-01..BC-09 plus a corroborated second read — it already has both.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · DISPOSITION (restated, no run, no call) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `fef9c93` — `BLOCKED_PLANNING` (S5).** Outside this
  run's named scope, and its sole predicate is still unmet at `471a43a`:
  `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` now holds 25 rows — 36, 22, 32, 33, 23,
  55, 39, 40, 44, 45, 46, 60, 61, 62, 63, 64, 41, 42, 57, 58, 65, 59, 43, 26, 47 — and none is 25.
  Resume predicate: arrival item (25) lands; then re-run `present --repo
  aspose-email-foss/Aspose.Email-FOSS-for-Cpp`.

- **2026-09-16 15:48 (`date` checked) · G4-W13-RERUN5 · NOT DRAWN · Cells TypeScript and 3D
  TypeScript stay admission-gated.** The spawn instruction made them conditional on arrival items 50
  (BC-02 per-repo receipt) and 51 (license-from-spdx) having landed; `plans/sprint/PHASE1-SPRINT-PLAN.md`
  §11 lists them together as "Admission-gated (5): Cells-TS + 3D-TS (50/51)". Neither 50 nor 51 is in
  `unblocked.jsonl` at `471a43a` (the 25 rows above), so neither was drawn and neither disposition
  moves. Reversal: when 50 and 51 land, a new lane item draws both.

- **2026-09-16 15:56 (`date` checked) · G4-W13-RERUN5 · MEASUREMENT · the draw was re-invoked on the
  rebased tree rather than having its verdict carried forward, and cost zero provider calls.**
  G4-W17 arrival item 50 landed at `44b4690` while the draw was running, rewriting
  `_source_build_fact` and bumping **BC-02 from check version 1 to 2** — "refuses a rendered command
  that ends with steps its receipt did not prove". This run's headline claim is that BC-02 PASSES, so
  carrying the pre-rebase verdict forward would have been a claim about code that is not the code
  being landed (rule 12). Re-invoked: `facts.json 359daa81`, `plan.json a06f41e7`,
  `content_units.json 4cc7cbb7`, `README.md 136b7a75` (243 visible lines of 662), `README.patch
  904f621e` and `review.json f384d8e7` all byte-identical; `validation.json` alone moves
  (`64dcfd2e` → `99139c19`) and for one reason, BC-02 now recorded at version 2. The table is
  unchanged: 9 PASS / 1 FAIL / 1 PENDING. BC-02 PASSES at v2 because C++ receipts carry no
  `build_command`, so the new `elif proved and …` branch is skipped and the template path admits
  `{'install_kind': 'source'}` as before — observed, not reasoned. Cost: the ledger went 54 → 77 rows,
  all 23 new ones `cache_reuse`, **zero provider calls and still zero `cache_stale`** — a cleaner
  control than run 4's one-call-in-47 because the shared-code change touched this very check.
  Alternative rejected: reporting the 4cd0219 verdict and noting the rebase. Reversal: none; a
  measurement.

- **2026-09-16 15:56 (`date` checked) · G4-W13-RERUN5 · NOT DRAWN (updated) · Cells TypeScript is
  unblocked as of `44b4690` and is the next lane item's, not this one's.** Arrival item 50 was absent
  from `unblocked.jsonl` when this run selected its work and landed at 15:41, after the C++ draw
  finished; the ledger now holds 26 rows ending 26, 47, **50**. Item 51 (license-from-spdx) is still
  absent, so 3D-TS stays gated and the sprint plan's pair "Cells-TS + 3D-TS (50/51)" is half open.
  Item 50's own commit already records live `build_product` measurements on Cells-TS (fc18650, `npm
  install` exit 0, no build script), so the draw is ready to be taken. Alternative rejected: opening it
  at the end of a spent box — a lane subagent works one item per run (loop-prompt-lane §5), and a draw
  started without its own box is how a candidate gets forced. Reversal: the next lane item draws it.

- **2026-09-16 17:09 (`date` checked) · G4-W14-RERUN2 · FINDING `LANE-B-W14R2-F1` (shared code, the
  lane may not edit) · `prompts/section_authoring.yaml`'s `max_output_tokens: 8000`, combined with
  `composition/authoring.py`'s `_type_batches` (`_TYPE_BATCH = 40`), truncates a 31-type batch and
  aborts the whole transaction with no retry.** First full draw of
  `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` since arrival items 50 and 51 landed
  (`44b4690`, `49ac70d`), against `origin/main` at `32c7d28` from a fresh worktree `C:\w\b06`. Facts,
  examples and preflight were all clean — 419 facts (321 public symbols), 3 of 3 examples EXECUTED,
  0 unresolved, 0 contradicted, no required contract row without evidence; `install_command:npm` is
  SUPPORTED by a verified source build (item 50's own fix, measured here on the repository item 50's
  commit named: `npm install` exit 0, no build script) and `license:spdx`/`license:file` are both
  SUPPORTED from a real `License/LICENSE.txt` (item 51 was not even needed for this repository).
  Investigation (5 capabilities, 5 workflows, 3 limitations) and reconciliation (49 units — 28
  SUPERSEDE_REDUNDANT, 16 OMIT_UNSUPPORTED, 3 VERIFIED_PRESERVE, 2 VERIFIED_MOVE, first attempt) and
  planning (12 api_hubs, 18 sections, 17 included) all closed on the first call. `section_authoring`
  then authored 11 of 12 dispatched tasks cleanly (one retry recovered a stray `AGENTS.md` identifier
  in `documentation_resources`) before the `api_reference` undocumented-type batch — 31 types
  (`class` 29, `enum` 2) of the repository's 321 public symbols carry no docstring, under
  `_TYPE_BATCH`'s cap of 40, so one call — generated exactly 8000 completion tokens in 168 s and hit
  `finish_reason == "length"`. `core/llm/jobs.py:473-483` treats a length-truncated reply as
  unrepairable by design ("a re-ask under the same budget cannot help") and raises `JobError`
  immediately: `section_authoring: output truncated at the manifest's max_output_tokens (8000); raise
  the budget or bound the output, never retry`. The whole transaction fails closed; no `content_units`,
  no render, no validation. What the raw completion actually said cannot be recovered — the code never
  persists a length-truncated reply, by the same design — so this finding states only what is
  measured: 31 short one-sentence-per-type units, well inside precedent for other ecosystems' batches
  at the same cap, needed more than 8000 completion tokens for Cells-TS specifically. Proposed, either
  or both (the lane cannot land either — `prompts/` and `composition/authoring.py` are both outside
  `owned_paths`): raise `section_authoring`'s `max_output_tokens` past 8000, the same shape of fix
  `7ea433e` already applied to `source_reconciliation` (16000 → 32000) for an analogous truncation: or
  lower `_TYPE_BATCH` below 40 so a batch this repository's types produce fits the existing budget.
  Alternative rejected: retrying verbatim — `section_authoring.yaml` pins `temperature: 0.0` and
  `seed: 1`, so an unmodified re-ask reproduces the identical 8000-token truncation, which is why this
  is reported as a fresh finding rather than redrawn a second time in this box (the W-card's
  stop-don't-force applies here too: a deterministic cause does not get a second, equivalent attempt).
  Evidence: `calls.jsonl` row `0f7c4a7ecb4faf7b-01-success-...-0017` (`completion_tokens: 8000`,
  `latency_ms: 168153`) followed by row `...-0018` (`outcome: response_invalid`,
  `error_class: TruncatedOutput`); `runs/transactions/aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript/fc186507e5b7124f4664aa6035f25cfd3112367d/`
  (`plan.json`, `dispositions.json`, `investigation.json`, `calls.jsonl`); full detail in
  `evidence/build/lanes/lane-b/G4-W14-RERUN2.json`. Reversal: none; a measurement plus a proposal.

- **2026-09-16 17:09 (`date` checked) · G4-W14-RERUN2 · DECISION · Cells TypeScript is not redrawn in
  this box.** The cause is deterministic (`temperature: 0.0`, `seed: 1` on `section_authoring`) and
  named mechanically above; an unmodified re-ask reproduces the identical truncation, so a second draw
  would not be a new attempt, it would be the same attempt with extra ledger rows. The fix is shared
  code the lane may not land (`LANE-B-W14R2-F1`). Nothing here weakens any check: the transaction
  failed closed exactly as `core/llm/jobs.py` requires on a truncated reply, and no candidate is
  forced past it. Reversal: the resume predicate in the disposition below.

- **2026-09-16 17:09 (`date` checked) · G4-W14-RERUN2 · DISPOSITION ·
  `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` at `fc18650` — `BLOCKED_COMPOSING` (S6
  `section_authoring`, `TruncatedOutput`).** First draw since arrival items 50/51 landed; previously
  `BLOCKED_ENVIRONMENT` (Windows MAX_PATH, resolved at G4-W14) then, on the 2026-09-06 19:28 re-run,
  `BLOCKED_VALIDATION (BC-02)` — both of those are gone (`install_command:npm` SUPPORTED, license
  SUPPORTED with a real file), and the repository now reaches one stage further before stopping. 419
  facts (321 public symbols), no required contract row without evidence, 3 of 3 examples EXECUTED. S3
  5 capabilities / 5 workflows / 3 limitations; S4 49 of 49 units, first attempt; S5 12 api_hubs / 18
  sections (17 included); S6 11 of 12 dispatched authoring tasks completed (one recovered rejection)
  before the api_reference type-batch of 31 undocumented types truncated at the 8000-token cap and the
  transaction failed closed — no `content_units.json`, no render, no validation record. 18 provider
  calls, all HTTP 200, 0 cache_reuse (first draw of this revision), 2 `response_invalid` (1 recovered,
  1 fatal), 23,867 completion tokens. Resume predicate: re-run once `LANE-B-W14R2-F1` lands (either
  half — a raised `section_authoring` budget or a smaller `_TYPE_BATCH` — clears this specific
  repository, since it is short by less than one call's worth of headroom). Full detail:
  `evidence/build/lanes/lane-b/G4-W14-RERUN2.json`.

- **2026-09-16 17:09 (`date` checked) · G4-W14-RERUN2 · NOT DRAWN · Aspose.3D for TypeScript is
  attempted next in this same session, box allowing (spawn instruction), rather than being folded into
  this item.** Both its gating arrival items are now landed (50 at `44b4690`, 51 at `49ac70d`,
  confirmed in `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` at `origin/main` `32c7d28`),
  so the sprint plan's "Cells-TS + 3D-TS (50/51)" pair is now fully open. Recorded here rather than
  assumed: a draw of 3D-TS is a separate transaction, on its own branch, and gets its own item and
  evidence record if the box allows it this run.

- **2026-09-16 17:59 (`date` checked) · G4-W14-RERUN3 · MEASUREMENT · both arrival items 50 and 51
  confirmed working on `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, and the section_authoring
  truncation `LANE-B-W14R2-F1` found on Cells-TS did NOT reproduce here despite a larger batch.**
  First draw of 3D-TS since 2026-09-06. `install_command:npm` is SUPPORTED (item 50): value
  `git clone ... && npm install && npm run build`, evidence "verified source build: the verifier
  ran `npm install` and `npm run build` against this revision, every step exiting 0". `license:spdx`
  is SUPPORTED (item 51, the repository this fix was written for): value `MIT`, evidence "license
  declared by the manifest; no license file at this revision" - exactly item 51's mechanism, and its
  first corroboration on a real draw since landing. Facts: 1190 records (1028 public symbols), 1188
  SUPPORTED, 0 UNRESOLVED, 2 CONTRADICTED (`example:002` - the known `scene.save('model.stl', 'stl')`
  README fragment recorded at G4-W14; `link_target:021`), no required contract row without evidence.
  81 undocumented types (77 class, 4 enum) split into three `_TYPE_BATCH` calls of 40/40/1 - more
  than double Cells-TS's 31-type single batch - and none of the three hit the 8000-completion-token
  cap; `section_authoring` made 28 calls total across all its tasks with zero `TruncatedOutput`. This
  does not close `LANE-B-W14R2-F1` (a batch's actual token cost is data-dependent - how verbose the
  model's per-type prose runs for a given repository's identifiers and signatures - not purely a
  function of batch size, so a 40-type batch can fit comfortably here while a 31-type one didn't for
  Cells-TS), but it does mean the defect is not "every large TypeScript surface truncates," which
  matters for how the shared-code owner prioritises the fix. Evidence: `facts.json`, `calls.jsonl`
  (`by_job: section_authoring 28`, zero `TruncatedOutput` in `outcome`); full detail in
  `evidence/build/lanes/lane-b/G4-W14-RERUN3.json`.

- **2026-09-16 17:59 (`date` checked) · G4-W14-RERUN3 · FINDING `LANE-B-W14R3-F1` (shared code, the
  lane may not edit) · `review/independent/review.py`'s `cited_fact_defect` structurally excludes
  every `inherited_unit` fact from ever refuting a factuality finding, even when the unit under
  review cites one whose own text states the claim almost verbatim.** 3D-TS reached S9/S10/S11 in
  full - 9 PASS / 1 FAIL (BC-10) / 1 PENDING (BC-11), two repair rounds, `verdict REJECT_FACTUAL`,
  `second_reader.read = 1`. The one finding that survives repair, F04 (`scope_limitations`,
  `causal_stage COMPOSING`), reads: "The candidate claims 'Binary glTF export (binaryMode: true)
  currently fails for any non-empty mesh' but the facts do not verify this limitation; `example:007`
  shows `binaryMode = false` working, but no fact confirms `binaryMode = true` fails for all
  non-empty meshes." F04 cites only `example:007` as its own `fact_ids`. But the content unit under
  review (`content_units.json`, section `scope_limitations`, slot `limitation:2`) cites two facts,
  `example:007` and `inherited_unit:046.paragraph` - and the second is SUPPORTED, sourced from the
  original repository's own upstream README (lines 261-264), and its value is: "Binary glTF (`.glb`,
  `binaryMode = true`) currently throws a `RangeError` for any non-empty mesh - see [Scope and
  limitations](#scope-and-limitations). Use the JSON/ASCII form (`binaryMode = false`, the default)
  shown above until that is fixed upstream." That is the library's own author documenting the exact
  bug the unit restates, softened by an earlier repair round (R02, this run's own `repairs.json`)
  from "throws a RangeError" to "fails", still citing `inherited_unit:046.paragraph` throughout. F04
  faults the unit for a claim its own second citation already proves true as the source's own
  words. Read mechanically against production: `cited_fact_defect` (review.py:301-333) builds
  `product = [fact for fact in cited if fact.kind != "inherited_unit"]` from the finding's own
  `fact_ids` before checking whether the quote is one of those facts' literal values - so even had
  F04 cited `inherited_unit:046.paragraph` itself, this function would still discard it before the
  literal-value check ever ran, because it excludes every `inherited_unit`-kind fact by construction.
  Nothing in the function's docstring explains why an `inherited_unit` fact - a real, SUPPORTED fact
  kind that IS this project's own protected/preserved original-README content, which a content unit
  is fully entitled to cite as its evidentiary basis (as this very unit does) - can never satisfy a
  factuality citation. `absence_defect`, `rendered_defect`, `renderer_owned_defect` and `scope_defect`
  were also checked against this finding and none engages the unit's second citation at all; none
  is scoped to ask "does any fact this UNIT (not just this finding) cites already support the quote."
  Proposed, smallest first (the lane cannot land either): drop the `fact.kind != "inherited_unit"`
  filter in `cited_fact_defect` so a finding citing an `inherited_unit` whose literal text matches the
  quote is refuted the same way a `public_symbol` or `package` citation already is; or, more broadly,
  a new refutation checks the reviewed unit's full `fact_ids` (not only the finding's) for a
  SUPPORTED `inherited_unit` whose value contains the quote's substance, since a factuality finding
  that never looks at what the candidate actually cited cannot be a defect in the candidate. Evidence:
  `runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript/7b959706f2ad976db929f26ec079f43a07d578e1/`
  (`review.json` F04, `content_units.json` the `limitation:2` unit, `facts.json`
  `inherited_unit:046.paragraph` and `example:007`, `repairs.json` R02); full detail in
  `evidence/build/lanes/lane-b/G4-W14-RERUN3.json`. Reversal: none; a measurement plus a proposal.

- **2026-09-16 17:59 (`date` checked) · G4-W14-RERUN3 · DECISION · 3D TypeScript is not redrawn in
  this box.** The verdict is reported literally: `REJECT_FACTUAL`, one finding surviving two repair
  rounds, `second_reader.read = 1` (below the `>= 2` corroboration guard in any case, so ACCEPT was
  never reachable here regardless of the finding's merits). The transaction is a genuine first draw
  with a real, reproducible cause named mechanically above; redrawing without a code change would not
  be a new attempt. The fix is shared code the lane may not land (`LANE-B-W14R3-F1`). Nothing here
  weakens any check: BC-10 failed exactly as the check requires, and no candidate is forced past it.
  Reversal: the resume predicate in the disposition below.

- **2026-09-16 17:59 (`date` checked) · G4-W14-RERUN3 · DISPOSITION ·
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at `7b95970` - `BLOCKED_REVIEW` (BC-10,
  `REJECT_FACTUAL`).** First draw since 2026-09-06, when it reached no rendering at all
  (`BLOCKED_RECONCILIATION`). Both gating arrival items delivered: `install_command:npm` and
  `license:spdx` are both SUPPORTED (items 50 and 51). 1190 facts (1028 public symbols), no required
  contract row without evidence, 9 examples (8 EXECUTED, 1 CONTRADICTED - the documented `scene.save`
  README-fragment class from G4-W14). S3 6 capabilities / 6 workflows / 4 limitations; S4 106 of 106
  units, first attempt (53 SUPERSEDE_REDUNDANT, 18 OMIT_UNSUPPORTED, 25 VERIFIED_PRESERVE, 5
  NON_CONTENT, 3 VERIFIED_MOVE, 2 CORRECT_WITH_EVIDENCE); S5 12 api_hubs, 17 of 18 sections; S6 122
  units across 9 sections, coherence revised 0 of 122; 175 visible lines of 728. Validation 9 PASS /
  1 FAIL / 1 PENDING: BC-01 through BC-09 all PASS (including BC-02 and BC-06, the two checks items
  50/51 unlock), BC-10 FAIL at COMPOSING on `REJECT_FACTUAL`, BC-11 PENDING (S12 never reached).
  Review: 2 rounds, 2 findings repaired (F04+F05+F06 combined, F07), 1 re-raised after repair
  (relabelled F04 on the second read), 4 advisory. 42 ledger rows (25 provider calls, all HTTP 200,
  17 cache_reuse, 1 response_invalid), 42,230 completion tokens. Resume predicate: re-run once
  PROPOSAL `LANE-B-W14R3-F1` lands (a factuality finding refuted by a cited `inherited_unit` fact's
  literal text, the same way a `public_symbol` or `package` citation already refutes one), or once
  the primary rules it sealable on BC-01..BC-09 plus a corroborated second read - it does not yet
  have either (`second_reader.read = 1`). Full detail: `evidence/build/lanes/lane-b/G4-W14-RERUN3.json`.

- **2026-09-16 19:31 (`date` checked) · G4-W13-RERUN6 · DECISION · the spawn instruction's premise
  for this item ("PDF-Cpp has never been attempted by any lane this sprint; no disposition on record
  for it in your own lane file or any other") is false, checked against this file before acting on
  it.** `project/lanes/lane-b.yaml` itself carries three prior draws of exactly this repository -
  `G4-W13-RERUN2` (13:23, S4 blocker), `G4-W13-RERUN3` (17:50, `BLOCKED_REVIEW` BC-10) and
  `G4-W13-RERUN4` (21:30, `BLOCKED_COMPOSING` BC-08), all 2026-09-11 - and its standing disposition
  going into this run was `BLOCKED_COMPOSING (BC-08)`, resume predicate PROPOSAL `LANE-B-R4-F1` or
  `LANE-B-R4-F2` landing. Neither had: `repair/targeted.py`'s `repair_packet` (line ~376) still reads
  `kinds = [kind for kind in FACT_KINDS if kind != "inherited_unit"]` verbatim at `origin/main`
  `6f2161f`, and `validation_defects`'s `section = named[0] if named else None` (line 210) is
  likewise unchanged - both read directly off the checked-out tree before the draw, not assumed from
  the 2026-09-11 note. Only the "no SEALED bundle" half of the premise holds (`candidates/` has no
  `aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp` entry, confirmed by directory listing). Two readings
  were available: decline the draw as a redraw of an already-blocked repository (which the spawn
  instruction's own stated principle - "rather than redraw a blocked repository" - would forbid), or
  draw it anyway since the instruction explicitly anticipated exactly this uncertainty ("go in with
  no assumptions about its blocker; measure and report literally") and five days and roughly a dozen
  arrival items (50-65, F9-F12) have landed in shared code since the last draw, any of which could
  plausibly have shifted this repository's behaviour even without clearing its named blocker. Decided
  the second way: drawn as `G4-W13-RERUN6`, reported literally below, premise correction recorded
  here rather than silently substituted or silently obeyed. Alternative rejected: picking a different
  lane-b repository unilaterally (e.g. `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, last drawn
  2026-09-06) instead of the one named - rejected because the instruction's factual premise being
  wrong is not the same as its target being wrong, and the target is explicitly within this lane's
  owned repository list. Reversal: none; a correction plus a decision, both dated.

- **2026-09-16 19:31 (`date` checked) · G4-W13-RERUN6 · a fifth draw, same revision, genuinely fresh
  composition rather than a cache replay: BC-08 fails again on a different specific fact, with the
  repair engaging (partially) for the first time.** Same repository, same revision `888700a` as
  draws 2-4 (`facts.json` still 1,846 records, same per-kind breakdown, same 11 examples at 4
  EXECUTED / 2 FAILED / 5 NOT_VERIFIED) - but NOT a byte-identical replay: `facts.json` digest is
  `7396982d...` against draw 4's `bd8f4a98...`, S4 disposed the same 124 units into a materially
  different distribution (`VERIFIED_MOVE` 49 against 18, `VERIFIED_PRESERVE` 25 against 45,
  `VERIFIED_REWRITE` 1 against 7), and S6 authoring produced 286 units against 285 and 185 visible
  lines of 665 against 180 of 583. 29 provider calls (0 `cache_stale` of 51 ledger rows) confirm this
  draw made genuinely live S3-S6 calls rather than reusing draw 4's store, which is why the surface
  differs while the input facts do not - `runs/` is gitignored and this worktree (`C:\w\b09`) never
  held draw 4's store to reuse from, so `--fresh` was not needed to get a live draw. BC-08 failed on a
  single fact this time - `inherited_unit:019.paragraph`, "VERIFIED_PRESERVE keeps the command
  `cmake --preset windows-msvc-debug` but the candidate does not render it", section
  `development_testing` - where draw 4 failed on three facts across two sections at once. The one
  repair round this draw got (S6, `development_testing`) is `outcome: "repaired"` in `repairs.json`,
  not the flat no-op draw 4 recorded twice: it patched `units.0.fact_ids` to add
  `inherited_unit:019.paragraph`, but never touched `units.0.text`, so the rendered command stayed
  absent and the CLI's own summary says it plainly - "after one repair attempt the equivalent failure
  stands". This is exactly `LANE-B-R4-F2`'s mechanism, not a new defect: `repair_packet` still
  excludes `inherited_unit` from the records it offers the model to cite, so the model can name the
  fact ID (visible to it via `preserve`) but cannot see or reproduce its text. `LANE-B-R4-F1` is not
  independently exercised here - only one section failed this time, so `named[0]` routing had nothing
  to misroute. Validation: 8 PASS / 1 FAIL / 2 PENDING (BC-01..BC-07, BC-09 PASS; BC-08 FAIL at
  COMPOSING; BC-10, BC-11 PENDING, S10 never reached). Alternative rejected: treating the reduced
  failure count (1 against 3) as evidence the blocker is clearing - rejected because the causal code
  is read unchanged above, and one fact failing for the identical structural reason is not progress
  toward zero, it is the same defect landing on a smaller target this draw's own composition
  happened to produce. Reversal: none; a measurement.

- **2026-09-16 19:31 (`date` checked) · G4-W13-RERUN6 · DISPOSITION (restated) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_COMPOSING (BC-08)`.** Restated,
  not moved: draw 4's disposition was already `BLOCKED_COMPOSING (BC-08)` and this draw lands on the
  same check and causal stage, on a different specific fact. 1,846 facts, no required contract row
  without evidence, 11 examples (4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED). S3 8 capabilities / 5
  workflows / 4 limitations; S4 124 of 124 units (SUPERSEDE_REDUNDANT 37, VERIFIED_MOVE 49,
  VERIFIED_PRESERVE 25, OMIT_UNSUPPORTED 5, DEFER_UNRESOLVED 5, NON_CONTENT 2, VERIFIED_REWRITE 1);
  S5 18 of 18 sections, 8 capabilities, 12 hubs, examples 1+3, 4 links, 1 limitation; S6 286 units
  across 9 sections, coherence revised 0 of 286 (1 provider call); 185 visible lines of 665.
  Validation 8 PASS / 1 FAIL / 2 PENDING: BC-01..BC-07 and BC-09 PASS, BC-08 FAIL at COMPOSING on
  `inherited_unit:019.paragraph` ("cmake --preset windows-msvc-debug" not rendered), BC-10 and BC-11
  PENDING (S10 never reached). Repair: 1 attempt (BC-08, S6, `development_testing`), outcome
  `repaired` (added the fact ID, not the text), re-raised; rounds 2. 51 ledger rows, 29 provider
  calls (all HTTP 200), 22 cache_reuse, 0 cache_stale, 2 response_invalid, 52,505 completion tokens.
  Resume predicate unchanged from draw 4: re-run once either PROPOSAL `LANE-B-R4-F1` (one repairable
  defect per failing check-and-section pair) or `LANE-B-R4-F2` (a BC-08 packet carries the
  `inherited_unit` records its defect names) lands, or once the primary rules it sealable on
  BC-01..BC-09 plus a corroborated second read. Full detail:
  `evidence/build/lanes/lane-b/G4-W13-RERUN6.json`.

- **2026-09-16 20:36 (`date` checked) · G4-W14-RERUN4 · DECISION · a second correction: PDF-TS was
  attempted once before, by the primary loop, not "never".** Following the same box's second target
  (`aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`), checked against `docs/DECISION_LOG.md` before
  drawing rather than trusted from the spawn instruction: the primary loop drew it once, 2026-09-06
  21:11, right after arrival item 31 re-enabled it (`data/registry.json` `mode: disabled` ->
  `dry_run`). That draw admitted and extracted cleanly (2,922 facts) but died on
  `RetryableOperationError: timeout` inside S4 `source_reconciliation`, twice, against the then
  `DEFAULT_TIMEOUT_SECONDS` of 360s (`core/config.py`), and named a PROPOSAL to raise it. Checked
  directly against `origin/main` before this draw: `b6b0232` (2026-09-06 22:39, PR #16, "set the
  gateway timeout from measured call duration, not a guess") already raised it to 900s - the exact
  proposed fix, landed roughly ninety minutes after the primary's attempt and never re-drawn since.
  So the repository is genuinely untested against its own named blocker's fix, which is close
  enough to "never attempted under conditions that could succeed" to draw it, while the literal
  "never attempted" claim is corrected here rather than repeated. `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript
  (disabled: disposition only)` in `project/lanes/lane-b.yaml`'s `repositories:` list is now stale
  documentation, superseded by item 31; left as-is here since correcting stale prose outside an
  active item's own predicate is not this item's scope. Reversal: none; a correction plus a
  decision.

- **2026-09-16 20:36 (`date` checked) · G4-W14-RERUN4 · three lane-owned defects, one composition
  round: a config `.` stripped to nothing, a compiler flag pairing tsc itself refuses, and a
  self-import no `exports` field can satisfy - all in `typescript_examples.py`, all fixed with a
  mutation test each.** Facts-only against `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` at
  `09e3d13` (3,133 facts, 437 inherited units, 2,544 public symbols, 96 examples) first read `96
  candidates; not_verified 96`, every one `BLOCKED_TOOLCHAIN: error TS5110: Option 'module' must be
  set to 'NodeNext' when option 'moduleResolution' is set to 'NodeNext'.` **F1 (TS5110):**
  `_flags`'s `_BUNDLER_MODULES = frozenset({"bundler", "node16", "nodenext"})` treated all three
  resolutions alike and always emitted `--module esnext`; measured directly against this machine's
  tsc (5.9.3): `--module esnext --moduleResolution bundler` raises nothing, but the same pairing
  under `nodenext` or `node16` raises exactly TS5110 - only `bundler` has no companion-module
  constraint. Fixed: `node16`/`nodenext` now get `module` set to their own resolution value
  verbatim; `bundler` is unchanged. Mutation tests
  `test_node_paired_resolution_gets_a_matching_module` (4 params) and
  `test_node_paired_flags_actually_compile` (2 params, real tsc) - red (TS5110, both parametrizations)
  before, green after; `test_bundler_resolution_keeps_the_es_module_default` guards the unaffected
  case. **F2 (self-import, no `exports`):** with F1 fixed, all 96 still failed, now `error TS2307:
  Cannot find module '@asposefoss/pdf'` - every one of this repository's examples imports the
  package by its own published name, not a relative path (the only style `stage_sources`'s docstring
  names, from Cells/3D), and Node's self-referencing-by-name resolution requires an `exports` field
  in `package.json` that this manifest does not declare (only `main`/`types`). Fixed: a
  `node_modules/<name>` entry staged from the build output, mirroring what `npm install` gives a
  real consumer rather than depending on a Node feature the package opted out of. Mutation tests
  `test_the_packages_own_name_resolves_like_a_real_consumers_install` and
  `test_an_example_importing_the_package_by_its_own_name_type_checks` (real tsc) - red (TS2307)
  before, green after. **F3 (`rootDir: "."` and the wrong config file):** with F1+F2 alone, `dist/`
  was never staged at all - `str.lstrip("./")` strips a *character set*, not a prefix, so PDF-TS's
  own `rootDir: "."` (its `tsconfig.json`, used only by its `typecheck` script) was reduced to `""`
  and read as "no rootDir", silently skipping the whole `dist` staging step; separately, the
  authoritative mapping for what `dist/` actually contains is a *different* file,
  `tsconfig.build.json` (`rootDir: "src"`, what `package.json`'s `build` script actually runs via
  `tsc -p tsconfig.build.json`), which `stage_sources` never read. Fixed both: `_staging_options`
  prefers `tsconfig.build.json` when it declares its own `rootDir`/`outDir`, falling back to
  `tsconfig.json` with `"."` now correctly read as "the workspace itself" rather than "absent" (the
  fallback path a repository with only one config would hit). Mutation tests
  `test_a_narrower_build_config_wins_over_a_whole_tree_typecheck_config` and
  `test_a_bare_dot_root_dir_stages_the_whole_workspace` - red (no `dist/index.ts` staged, or staged
  one level too deep under `dist/src/`) before, green after. Combined effect on the real repository:
  `96 candidates; failed 96` (every one a real per-example diagnostic now, not a configuration
  refusal) moved to **`96 candidates; executed 9, failed 87`** - `required rows without evidence:
  none` throughout. Full ruff/mypy/pytest (`-n auto`, 1,180 passed, 16 xfailed) green after all
  three. Alternative rejected for F3: reading only `tsconfig.build.json` unconditionally - rejected
  because a repository with no separate build config (Cells, 3D) has nothing there, and the
  fallback to `tsconfig.json` must still work correctly for them, which is what the mutation test
  for the bare `"."` case guards. Reversal: revert `typescript_examples.py`'s three edits and their
  tests; `_flags`, `stage_sources` and the module-level constants return to their prior form.

- **2026-09-16 20:36 (`date` checked) · G4-W14-RERUN4 · DISPOSITION · `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`
  at `09e3d13` - `BLOCKED_INVESTIGATION` (S3).** First draw past facts extraction for this
  repository since the 2026-09-06 21:11 S4-timeout attempt, and the first ever by lane-b. With all
  three verifier fixes above in place, the full transaction (`present`, no `--facts-only`) ran S3
  `repository_investigation` and failed closed there: `output rejected twice; last rejection: fact
  example:008 is CONTRADICTED, not SUPPORTED; fact example:009 is CONTRADICTED, not SUPPORTED; fact
  example:010 is CONTRADICTED, not SUPPORTED`. Both attempts (identical rejection both times, per
  `calls.jsonl`) cited the same three CONTRADICTED examples as evidence for one workflow claim,
  "Parse HTML or Markdown text into a structured document model and render it into a PDF flow or
  page" (`calls/907ca9e172c9.rejected-1.json`, `workflows[3]`). The three examples' own failures are
  real, not verifier artifacts: `example:009` is `error TS2339: Property 'OpenFile' does not exist
  on type '{ new (): Document; ...}'` (a genuine API-name mismatch, `OpenFile` vs whatever this
  revision actually exports); `example:008` and `example:010` are `error TS2304: Cannot find name
  'doc'`/`'page'` - the documented cross-block-fragment class this project has already named
  elsewhere (3D-TS's `scene.save`, Slides-C++'s incomplete fence): README code blocks that flow
  from one to the next, each individually unresolvable in isolation though the workflow they
  together document is real. `core/llm/binding.py`'s SUPPORTED-only citation rule
  (`errors.append(f"fact {fact_id} is {fact.polarity}, not SUPPORTED")`) is doing exactly its job -
  refusing a claim's only cited evidence when that evidence did not itself verify - and is not
  weakened here. What it exposes is shared code this lane may not edit: `core/llm/binding.py`
  (the SUPPORTED-only rule itself) and `prompts/repository_investigation.yaml` (the packet gives
  the model no way to express "this workflow is real across these blocks together, even though no
  single block verifies alone" other than citing blocks that individually fail the rule). Not a new
  discovery in kind - the identical structural tension is already named for 3D-TS and Slides-C++ -
  so recorded as a corroborating measurement rather than a fresh PROPOSAL: three more repositories
  now show the same shape (`example:xxx` cross-referencing another block) tripping the same
  citation rule at three different stages (S3 investigation here; S6 authoring/S9 validation on the
  other two). sealed_by_lane stays 0, dispositions_by_lane rises 9 to 10. Resume predicate: re-run
  once shared code lets a multi-block workflow cite its own supporting facts without every
  individual block independently verifying, or once the primary rules a narrower fix sufficient.
  Full detail: `evidence/build/lanes/lane-b/G4-W14-RERUN4.json`.

- **2026-09-16 21:33 (`date` checked) · G4-W14-RERUN5 · SEAL ·
  `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` at `fc186507e5` - `READY_FOR_PROPOSAL`.**
  Genuine changed-input retry of `G4-W14-RERUN2`'s `BLOCKED_COMPOSING` disposition, drawn only after
  checking the spawn instruction's framing directly against the code rather than accepting it at
  face value: `git show ef7138c` read in full before the draw, confirming its own commit message
  ("Arrival item 75, double-corroborated (lane F: Email-.NET/Slides-.NET; lane B independently:
  Cells-TS)") names this exact repository, and `prompts/section_authoring.yaml` carries the new
  `maxLength: 2200` (unit text) / `maxLength: 500` (`omitted.reason`) bound that RERUN2's finding
  `LANE-B-W14R2-F1` asked for. Same revision as RERUN2, same 419-fact digest
  (`0078f1968b6188466fc33bc68421154a9cc749a7df0c7c9f3314644e9e3f75ca`) - a controlled retest of the
  composition fix alone, nothing else about the input changed. The api_reference 31-type batch that
  truncated at exactly 8000 completion tokens on RERUN2 completed cleanly this time (S6: 65 content
  units across 9 sections, 0 coherence revisions), and the transaction ran the whole way through for
  the first time on this repository: S9 validation `BC-01`..`BC-09` all PASS; S10 independent review
  verdict `ACCEPT` (`verdict_as_returned` was `REJECT_FACTUAL` on the first read, reversed on
  corroboration - `second_reader.read=2`, 5 corroborated finding ids, 0 findings surviving, 14
  advisory - exactly the shape `BC-10`'s own predicate names, not a weakened check); S12 fresh-process
  rerun byte-identical with zero provider calls (`BC-11` PASS). `manifest.json`: `state
  READY_FOR_PROPOSAL`, `no_op_proof {byte_identical: true, fresh_process: true, provider_calls: 0}`.
  This is the lane's first seal on this repository across five attempts (Windows `MAX_PATH`, then
  `BC-02`, then two composing-stage truncations before this one) and the lane's first seal, period -
  `sealed_by_lane` rises 0 to 1.

  Mid-run, `origin/main` advanced to `609207e` (the primary loop's own `BC-07` canonical-abbreviation
  section-routing fix, `Check` version 3 to 4 - unrelated to this repository's own facts). Rebased
  onto it and **re-invoked the transaction rather than assumed the seal still held**, per the
  `RE-RUN5` precedent this file already recorded for `BC-02`'s v1-to-v2 bump: the sealed bundle's own
  files stayed byte-identical except `manifest.json`'s own bookkeeping (README.md, content_units.json,
  dispositions.json, plan.json, investigation.json, facts.json, dependencies.json, examples.json,
  review.json and validation.json inside `candidates/` all unchanged), and `repository-presenter
  status` read `14/34` both before and after the rebase. Rule 2's own shape held exactly as written -
  a candidate is invalidated only through an input listed in its own `dependencies.json`, never a
  global control-plane hash - and the CLI's own report named it directly: "valid update available
  (presentation): dependencies.json, validation.json changed at VALIDATING; the proven candidate
  stays valid and the update waits in the transaction."

  `project/state.yaml`'s `progress.current_candidates` is edited 13 to 14 in the same commit as this
  seal, by the one narrow method this lane may use (loop-prompt-lane section 0): `git fetch origin
  && git rebase origin/main` first, then the field set to `repository-presenter status`'s own fresh
  count against that just-rebased tree - never incremented by hand from the previously-read 13. This
  closed the one pytest failure the seal itself caused
  (`test_status_reports_this_repository_cursor`, cursor 13 vs disk 14 before the edit), confirmed by
  a second full local CI-equivalent run after the edit (`ruff check .` all passed, `ruff format
  --check .` 236 files formatted, `mypy src` clean, `pytest -n auto` 1192 passed, 16 xfailed, 126s).
  `sealed_by_lane` rises 0 to 1; `dispositions_by_lane` falls 10 to 9 (Cells-TS moves out of the
  disposition column into a real seal, not lost - no other repository's disposition changed).
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` was not redrawn: its own `G4-W14-RERUN3` disposition
  is a factuality-citation defect (an inherited_unit fact refuting a finding), a different shared-code
  class than item 75 touches, so it is unaffected by this fix. Full detail:
  `evidence/build/lanes/lane-b/G4-W14-RERUN5.json`.

- **2026-09-16 23:12 (`date` checked) · G4-W13-RERUN7 · DECISION · resume predicate verified landed
  before drawing.** Spawn instruction: PDF-Cpp's standing disposition entering this item was
  `BLOCKED_COMPOSING (BC-08)` (RERUN6), resume predicate PROPOSAL `LANE-B-R4-F1` or `LANE-B-R4-F2`
  landing in `repair/targeted.py`. Checked directly against `origin/main` before drawing rather than
  trusted: `git log --oneline` and `git show --stat 8b10f59` confirm both landed in commit `8b10f59`
  ("latch slot conflicts, split multi-section validation defects, carry named protected units, bound
  repair changes[]"), an ancestor of `origin/main` (`git merge-base --is-ancestor 8b10f59 origin/main`
  confirms). Read the worktree's own checked-out source, not assumed from the commit message:
  `validation_defects` (line ~213) now returns one `Defect` per `(check, section)` pair with narrowed
  `failures`, and `repair_packet` (line ~401) now calls a new `_named_inherited_units(defect, facts)`
  helper that adds back exactly the `inherited_unit` records a defect's own `details`/`failures` name -
  both exactly as item 87/88 describe, neither the stale text draw 6 read at `6f2161f`. A genuine
  changed-input retry, not a redraw of unchanged ground. Worktree `C:\w\b12`, branch
  `lane-b/G4-W13-RERUN7`, cut from `origin/main` at `1a0173a` (a0baf05 landed docs-only, mid-session,
  after the worktree was cut; rebased before landing, see below). Reversal: none; a verification.

- **2026-09-16 23:12 (`date` checked) · G4-W13-RERUN7 · a sixth draw: BC-08 genuinely clears for the
  first time; the transaction reaches BC-10 for the first time on this repository since draw 3.**
  Same repository revision as every draw since `G4-W13` (`888700a`), same 1,846-record facts.json
  (digest `bd8f4a98...`, matching draw 4's exactly - a deterministic facts stage on unchanged source
  and unchanged extractor). `examples: 11 candidates; executed 4, failed 2, not_verified 5`; no
  required contract row without evidence. **BC-08 (protected content) now PASSES** - validation reads
  `pass 9, fail 1, pending 1` (BC-01 through BC-09 all PASS; BC-10 FAIL; BC-11 PENDING because S12's
  fresh-process rerun only runs after a seal) - against draws 4 and 6's `8 PASS / 1 FAIL(BC-08) / 2
  PENDING`. This is the resume predicate's own proof: items 87/88 are what moved the check, not
  incidental drift, since nothing else in the repair path changed between draw 6 and this draw except
  those two commits (confirmed above). The transaction ran S10 independent review for the first time
  since draw 3 (2026-09-11) and returned `REJECT_PRESENTATION`: 1 finding (`F05`, `additional_examples`,
  criterion presentation) survived corroboration out of many raised (`second_reader.read=2`, `F05`'s own
  id is in the 7-entry `corroborated` list; 14 entries folded to advisory - `review.json`). `F05`'s text:
  "The candidate duplicates the 'Additional Examples' lead-in paragraph and the '12_create_features'
  description, creating redundancy and a cluttered structure," repair instruction "Remove the
  duplicated lead-in and description to avoid redundancy and keep the section concise." Root cause read
  directly from `dispositions.json`: `inherited_unit:026.paragraph` ("The Additional Examples lead-in
  is supported by the examples directory and README") and `inherited_unit:029.paragraph` ("The
  12_create_features example description is supported by the example and link target") were both
  disposed `VERIFIED_MOVE` to `additional_examples` at S4 - each individually true and fact-backed, but
  together redundant once placed in the same section. `source_reconciliation` judges each unit's own
  disposition independently of its neighbours by design (`reconciliation/dispositions.py`'s own
  docstring), so this class of cross-unit redundancy is exactly what S10's presentation check exists to
  catch - not itself a defect. Reversal: none; a measurement.

- **2026-09-16 23:12 (`date` checked) · G4-W13-RERUN7 · PROPOSAL LANE-B-R7-F1 (shared code:
  `repair/rounds.py`'s `_stage_target` S4 branch and `repair/targeted.py`'s `repair_checks` /
  `core/llm/binding.py`'s `binding_errors`) · a mechanically correct S4 repair reply is rejected twice
  and marked unrepairable because the binding check demands a disposition for every unit in the causal
  reconciliation batch, not only the units the fix actually changes.** Evidence, read directly from the
  transaction's own call files, not inferred: `repairs.json`'s `a28bcc6fec261472c863c78e` attempt,
  `misrouted: true` (RC-04 correctly retargeted F05 from the reviewer's guessed `S7` to `S4`, since its
  quote is placed text `source_reconciliation` itself produced), `outcome: "unrepairable"`, `reason`
  quoting `core/llm/binding.py:175`'s own message verbatim: `"no disposition for inherited units:
  inherited_unit:001.heading, ... inherited_unit:040.heading"` (35 unit IDs, all inside reconciliation
  batch 1, `reconciliation_batches()`'s own 40-unit-per-batch split).
  `calls/ffa627155822.rejected-1.json` and `.rejected-2.json` (both attempts) show the model twice
  correctly identifying and fixing the ONE real defect - `revised_output.dispositions` carrying
  `inherited_unit:026.paragraph -> OMIT_UNSUPPORTED` ("duplicates the section heading and is
  unsupported") and `inherited_unit:029.paragraph -> OMIT_UNSUPPORTED` ("duplicates the section
  lead-in and is unsupported") on attempt 1, `026` alone on attempt 2 - verbatim the two units named
  above and verbatim the reviewer's own repair instruction - yet both replies are rejected outright
  because `binding_errors` (`core/llm/binding.py:165-177`, `binding == "unit_ids"`) requires
  `cited.unit_ids` to cover every one of `stage_facts.by_kind("inherited_unit")`, and `_stage_target`'s
  S4 branch (`repair/rounds.py:452-481`, `PHASE0/G`) already scopes `stage_facts` down to one
  40-unit reconciliation batch (a prior, already-landed fix for the same shape of bug at a coarser
  grain - full-corpus scoping - found live against Cells-Rust) but still requires the *whole batch*
  re-declared, not just the units a targeted revision changes. The two repair mechanisms this codebase
  already has for a narrower-than-full-redeclaration fix don't reach S4: S6's `repair_packet` narrows
  the *evidence* a reply may cite (`allowed`) but still requires the full `units` array for the one
  assigned section, which is small enough in practice to redeclare; S4's batch is 40 units, and this
  defect's own two-attempt, two-identical-shape evidence says a model naturally returns only the
  delta when only 2 of 40 units are wrong, so the full-batch contract turns a real, correctly-diagnosed
  fix into an exhausted, unrepairable one. Cost and unlocks: no check weakened (BC-08 and BC-10 both
  still block on real defects); blocks this repository's own resume, corroborated by three prior BC-10
  rejections' worth of precedent (draws 2, 3) that S4/S10 boundary findings are a recurring shape here.
  Needs arrival-list admission before it can land; not landed by this session. Reverse by: superseded
  once an S4 repair reply may declare only the units its own `changes[]` names, merged onto the causal
  stage's stored output the way a delta is applied elsewhere, rather than judged for 100% batch
  coverage; until then this entry stands as `G4-W13-RERUN7`'s resume predicate.

- **2026-09-16 23:12 (`date` checked) · G4-W13-RERUN7 · DISPOSITION (moved) ·
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_REVIEW (BC-10)`.** Moved, not
  restated: draw 6's disposition was `BLOCKED_COMPOSING (BC-08)`; this draw clears BC-08 (now PASS)
  and reaches one stage further, S10 independent review, where it fails closed on a real, corroborated
  finding a structural repair-mechanism gap (`LANE-B-R7-F1`, shared code) prevents fixing. 1,846 facts,
  no required contract row without evidence, 11 examples (4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED). S3 8
  capabilities / 6 workflows / 4 limitations (0 calls, stored output reused); S4 124 of 124 units
  (SUPERSEDE_REDUNDANT 52, VERIFIED_MOVE 47, VERIFIED_PRESERVE 12, DEFER_UNRESOLVED 5,
  OMIT_UNSUPPORTED 5, NON_CONTENT 2, VERIFIED_REWRITE 1); S5 18 of 18 sections, 8 capabilities, 12
  hubs, examples 1+3, 6 links, 1 limitation; S6 287 units across 9 sections, 0 of 287 revised; 182
  visible lines of 638. Validation 9 PASS / 1 FAIL / 1 PENDING: BC-01 through BC-09 PASS, **BC-08
  PASS** (cleared by items 87/88), BC-10 FAIL at COMPOSING on `REJECT_PRESENTATION` (finding F05,
  corroborated, `second_reader.read=2`), BC-11 PENDING (no seal, so S12 never runs). Repair: 3 rounds -
  1 repaired (F04, S6, quick_start: added a one-sentence page-indexing clarification to
  `example:001`'s unit text), 1 unrepairable-and-misrouted (F05, retargeted S7->S4, two rejections,
  `LANE-B-R7-F1`'s own evidence); F05 re-raised, BC-10 stands. 83 ledger rows, 32 live completed calls
  (0 HTTP failures), 47 cache_reuse, **0 cache_stale** (a sixth independent non-materialisation of
  lane E's PROPOSAL E3, this repository's fourth), 4 response_invalid (the two F05 rejections plus two
  earlier in-composition retries), 72,233 completion tokens. sealed_by_lane stays 1 (unchanged from
  Cells-TS's seal); dispositions_by_lane stays 9 (this repository moves check/stage, not a new
  disposition). Resume predicate: re-run once PROPOSAL `LANE-B-R7-F1` lands (an S4 repair may declare
  only the units its revision actually changes), or once the primary rules a narrower fix sufficient,
  or rules the corroborated F05 finding itself unblocking on some other ground - not on BC-01..BC-09
  passing alone, since BC-10 is precisely what failed this time, on a real finding. Full detail:
  `evidence/build/lanes/lane-b/G4-W13-RERUN7.json`.

- **2026-09-17 01:34 (`date` checked) · G4-W13-RERUN8 · resume predicate verified, not assumed, before
  drawing: `LANE-B-R7-F1` is landed and demonstrably functioning.** `git log` on a fresh worktree cut
  from `origin/main` at `25aae12` shows `ce3a38a` ("an S4 repair reply may declare only the unit its
  own change touched") three commits back, and `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl`
  names arrival item 94 landed `2026-09-16T19:37:06Z`, unlocking exactly `lane-b,
  aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`. Read the diff itself, not the commit message alone:
  `repair/rounds.py` now threads `original=target.output` into `repair_checks`; `repair/targeted.py`'s
  `repair_checks` calls the new `merge_partial_units(revised, original)` before validation whenever
  `binding == "unit_ids"`. The draw below is the functioning proof, not a restatement: `repairs.json`
  records one real S4-adjacent repair (`package:cxx_standard`, C++17 to C++20, `scope_limitations`)
  applied and accepted without any full-batch redeclaration. `LANE-B-R7-F1` is CLOSED.

- **2026-09-17 01:34 (`date` checked) · G4-W13-RERUN8 · PROPOSAL LANE-B-R8-F1 (shared code:
  `review/independent/review.py`'s `_RENDERED_CHROME` / `_quoted_chrome`, lines ~697-706, and the
  `renderer_owned_defect` chrome branch, lines ~657-661) · a presentation finding quoting the bare
  `<details>` wrapper tag itself, rather than its `<summary>` line, evades the existing
  renderer-owned-chrome exemption and blocks on content no unit wrote and no repair can remove.**
  `composition/renderer.py` emits the collapsible wrapper as two separate literal lines at each of its
  two call sites - `lines += ["", "<details>", f"<summary>{API_SURFACE_SUMMARY}</summary>", ""]`
  (line 519) and `lines.append("<details>")` / `lines.append(f"<summary>{ADDITIONAL_EXAMPLES_SUMMARY}
  </summary>")` (lines 815-816), each later closed by a bare `lines += ["", "</details>"]` /
  `lines.append("</details>")` (lines 545, 820). `review.py`'s own exemption for this class
  (`_RENDERED_CHROME = frozenset({ADDITIONAL_EXAMPLES_SUMMARY, API_SURFACE_SUMMARY})`, matched by
  `_quoted_chrome`) recognizes only the `<summary>...</summary>` text, never the `<details>`/
  `</details>` tag lines the same renderer call sites emit right beside it. Measured on this draw's own
  `review.json`: finding `F08` (`reader: 2`, corroborated), `section_id: "additional_examples"`,
  `criterion: "presentation"`, `fact_ids: []`, quote exactly `"<details>"`, text "The candidate includes
  an unsupported HTML details block that is not supported by any fact and should be omitted." Mechanically
  confirmed no content unit wrote it: `content_units.json`'s 287 units contain zero occurrences of the
  substring "details" (checked programmatically, not by inspection). `renderer_owned_defect` therefore
  falls through every branch that would exempt it - `_quoted_chrome` fails (tag, not summary text),
  `_quoted_heading` fails (no leading `#`), the verified-fact check fails (`<details>` names no fact),
  and the final `section not in _DETERMINISTIC_SECTIONS` fallback also fails because `additional_examples`
  is a mixed-owned section (`owner` other than `"D"` in `SEMANTIC_SHELL`), the same "never wholesale
  exempted" section this exact guard already documents for the chrome case it does catch. Proof the
  repair mechanism cannot satisfy it either, not merely that it didn't: the one `targeted_repair` call
  routed at this finding's final recurrence returned `response_invalid`, rejection `"revised_output:
  matches the causal stage's own output unchanged; a no-op cannot repair a defect this stage's content
  did not change"` (`calls.jsonl`) - the model had nothing in any content unit's own text to revise, so
  it echoed the input back, and was correctly rejected for the no-op rather than credited with a fix
  that fixes nothing. Cost and unlocks: no check weakened (BC-10 still blocks on what looks, from the
  binding's point of view, like a real unrefuted finding); blocks this repository's resume alone so far,
  but the same renderer call sites are shared by every ecosystem's additional-examples/api-reference
  collapsible section, so any repository whose collapsed block draws a reviewer's literal-tag quote
  rather than a summary-text quote is equally exposed. Reverse by: superseded once `_quoted_chrome` (or
  `renderer_owned_defect` directly) also recognizes a quote equal to `"<details>"` or `"</details>"` as
  renderer-owned chrome, with a mutation test proving a finding quoting either tag folds to advisory;
  until then this entry stands as `G4-W13-RERUN8`'s resume predicate.

- **2026-09-17 01:34 (`date` checked) · G4-W13-RERUN8 · DISPOSITION (restated, check unchanged; finding
  changed) · `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` at `888700a` - `BLOCKED_REVIEW (BC-10)`.**
  Restated at the same check and stage as draw 7, but not the same cause: draw 7's blocking finding
  (`F05`, a genuine cross-unit redundancy) is gone from this draw entirely - the S4 disposition split
  differs materially from draw 7's on the same 124 units and same input facts (`VERIFIED_PRESERVE` 12
  to 46, `VERIFIED_MOVE` 47 to 22, `SUPERSEDE_REDUNDANT` 52 to 39, `OMIT_UNSUPPORTED` 5 to 9), the same
  live-call non-determinism draw 6 already measured at this same stage. 1,846 facts, digest
  `bd8f4a98...` unchanged from every prior draw (deterministic facts stage); 1,839 SUPPORTED, 5
  UNRESOLVED, 2 CONTRADICTED; no required contract row without evidence. 11 examples (4 EXECUTED, 2
  FAILED, 5 NOT_VERIFIED). S3 8 capabilities / 6 workflows / 4 limitations (0 calls, stored output
  reused); S4 124 of 124 units, live-recomputed (12 `source_reconciliation` ledger rows, not a cache
  hit); S5 18/18 sections; S6 287 units across 9 sections, 189 visible lines of 669. Validation 9 PASS /
  1 FAIL / 1 PENDING: BC-01 through BC-09 PASS - **BC-08 PASS again, `LANE-B-R7-F1`'s own fix confirmed
  functioning this draw** (see the verification entry above) - BC-10 FAIL at COMPOSING on
  `REJECT_PRESENTATION` (finding `F08`, `additional_examples`, corroborated `second_reader.read=2`),
  BC-11 PENDING (no seal). Repair: 3 rounds, 2 repaired (a real `package:cxx_standard` C++17-to-C++20
  fix in `scope_limitations`; an `additional_examples` omission that did not address the wrapper), 1
  rejected no-op recorded `response_invalid` rather than `unrepairable` (`LANE-B-R8-F1`'s own evidence);
  `F08` re-raised, BC-10 stands. 87 ledger rows: 35 live completed (HTTP 200), 47 cache_reuse, 0
  cache_stale (a seventh independent non-materialisation of lane E's PROPOSAL E3, this repository's
  fifth), 5 response_invalid, 71,077 completion tokens; by job section_authoring 57,
  source_reconciliation 12, independent_review 6, repository_investigation 5, targeted_repair 4,
  presentation_planning 3. sealed_by_lane stays 1 (unchanged); dispositions_by_lane stays 9 (restated,
  not a new repository). `repository-presenter status` from this worktree (already at `origin/main`'s
  head, no rebase needed): 15/34 - the rise is another lane's seal, not this draw's; recorded rather
  than assumed. Resume predicate: re-run once PROPOSAL `LANE-B-R8-F1` lands (`_quoted_chrome` also
  recognizes the bare `<details>`/`</details>` tags as renderer chrome), or once the primary rules a
  narrower fix sufficient, or rules the corroborated F08 finding itself unblocking on some other
  ground - not on BC-01..BC-09 passing alone, since BC-10 is again precisely what failed, on a real
  finding, now a different one than draw 7's. Full detail: `evidence/build/lanes/lane-b/G4-W13-RERUN8.json`.

- **2026-09-17 05:41 (`date` checked) · G4-W13-RERUN9 · resume predicate verified, not assumed, before
  drawing: `LANE-B-R8-F1` is landed.** `git show fd65028` read in full against `origin/main` at `9cbd522`
  confirms `_RENDERED_CHROME` now carries the two literal tag strings `"<details>"`/`"</details>"` beside
  `ADDITIONAL_EXAMPLES_SUMMARY`/`API_SURFACE_SUMMARY`, `REVIEWER_LOGIC_VERSION` 8 to 9, with a new mutation
  test (`test_a_finding_quoting_the_bare_details_tag_is_the_reviewers_defect`) and two updated pins. Also
  read directly: five more shared-code commits landed since draw 8's `25aae12` (`912aa62` a duplicate-subject
  reconciliation guard, `54fed24` domain checks run regardless of binding-error state, `4df1b08` a unit never
  restates its own slot's rendered title, `c83d2c4` `WORD_EXTENSIONS` admits `.one`, `9cbd522` BC-07 admits a
  subsystem noun and a hyphen-continued name) - none named as this repository's own resume predicate, but a
  genuine changed-input retry draws against whatever shared code stands on `origin/main`, not only the one
  named commit.

- **2026-09-17 05:41 (`date` checked) · G4-W13-RERUN9 · PROPOSAL LANE-B-R9-F1 (shared code:
  `composition/authoring.py`'s `unit_checks` title-restatement guard, lines ~1190-1197, added by arrival item
  99/E19 at `4df1b08`; and possibly `composition/planning.py`'s `core_capabilities` title selection in S5
  presentation_planning) · a single-purpose capability's plan-assigned title can be the only accurate short
  description of its own facts, giving the model no compliant way to open the unit's text without echoing it
  - measured on PDF-Cpp, four independent live samples, two independent draws, one recurring failure.**
  `plan.json`'s `core_capabilities[2]` (S5 output, unchanged and `cache_reuse`d across both of this run's
  draws) assigns `capability:3` the title `"Render pages to raster images"` from facts `example:001` and
  `public_symbol:aspose.pdf.devices` - a device set (`PngDevice`, `JpegDevice`, `BmpDevice`, `TiffDevice`)
  that does exactly and only that. `composition/authoring.py`'s packet already carries the correct
  `title_rule` sentence ("the unit never restates it... it adds what the title does not say"), and the
  one-shot re-ask quotes the exact violation back verbatim - yet in every one of four independent live
  `section_authoring` completions measured (draw 1 attempts 1 and 2; draw 2 attempts 1 and 2; four distinct
  `response_sha256` values, so four genuinely different samples, not a cache artifact), `capability:3`'s
  unit opened with `"Render pages to raster images through PngDevice, JpegDevice, and BmpDevice..."` -
  the title, verbatim, as its own first clause. `unit_checks`' guard (an unqualified, case-insensitive
  substring match) correctly rejects this every time, `core/llm/jobs.py` raises
  `JobError("section_authoring: output rejected twice; ...")` after the manifest's own one-retry budget is
  spent, and the whole transaction aborts before S9 validation or S10 review ever run - `LANE-B-R8-F1`'s own
  fix (the very reason this repository was redrawn) was never exercised either time. Full evidence:
  `runs/transactions/aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp/888700a8e361d32df21d0810c2eb939345e0603e/calls.jsonl`
  (four `section_authoring` `response_invalid` rows, 2026-09-17T00:32:34, 00:33:11, 00:38:14, 00:38:57Z, all
  four citing the capability:3 title restatement; the two attempt-1 rejections additionally cite an
  unrelated, non-recurring identifier defect, `adbe.pkcs7.detached`, that the correction resolved both
  times) and `.../calls/ffa0718357e7.rejected-1.json` / `.rejected-2.json` (draw 1's two full rejected
  texts). Per loop-prompt section 5 ("two equivalent failed attempts... prohibit a third equivalent
  attempt"), a third draw was not run: the cause is narrowed to this specific title/facts pairing, not to
  bad luck, and re-drawing a third time with nothing changed would be exactly the prohibited re-roll. Not a
  dispute of `4df1b08`'s own design - it correctly closed a real coherence-revert defect on Words-Python -
  but an edge case its author had not measured: a capability this narrowly scoped admits no accurate
  alternative topic sentence. No check weakened; the lane may not edit `composition/`. Reverse by: the
  guard gains tolerance for a title that is itself the only accurate short description of its slot's facts
  (e.g. permitting the restatement when the unit's remaining text, after removing the title-matching prefix,
  still adds member-level or format-level detail the title does not name), or S5's title selection is
  revised for a single-purpose capability to something the body can elaborate on without echoing, with a
  mutation test proving either fix lets a real single-purpose capability's unit pass while the Words-Python
  coherence-revert case `4df1b08` fixed still fails.

- **2026-09-17 05:41 (`date` checked) · G4-W13-RERUN9 · DISPOSITION (MOVED) · `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`
  at `888700a8e361d32df21d0810c2eb939345e0603e` - `BLOCKED_COMPOSING (S6)`.** Moves from draw 8's
  `BLOCKED_REVIEW (BC-10)`: a stage regression, not a restatement - draw 8 reached S10 independent review and
  failed there; this draw never reaches S9 validation at all, because arrival item 99/E19 (`4df1b08`), landed
  in shared code after draw 8's revision, now blocks `section_authoring` itself on a title-restatement defect
  this repository never faced before. 1,846 facts, digest `bd8f4a983c791ea927ae01b7b0b848a8f88b1005863a5930e32560f8377965bb`
  unchanged from every prior draw (deterministic facts stage); 1,839 SUPPORTED, 5 UNRESOLVED, 2 CONTRADICTED;
  11 examples (4 EXECUTED, 2 FAILED, 5 NOT_VERIFIED) - all unchanged. S3/S4/S5 ran once live in draw 1 (1
  `repository_investigation`, 4 `source_reconciliation`, 1 `presentation_planning` call, all accepted) and
  were `cache_reuse`d unchanged in draw 2; S6 hard-failed in both draws after exactly two attempts each, the
  manifest's own one-retry shape - no `content_units.json`, `validation.json`, or `review.json` in either
  draw's transaction directory. 22 ledger rows across both draws: 11 live completions (all HTTP 200), 7
  `cache_reuse`, 4 `response_invalid`, 0 `cache_stale` (an eighth independent non-materialisation of lane E's
  PROPOSAL E3 at this repository, its sixth). Validation, review and repair: NOT REACHED - the failure is a
  generation-time `JobError`, before either stage runs. `repository-presenter status` from this worktree
  (already at `origin/main`'s head, no rebase needed): 15/34, unchanged by this draw. sealed_by_lane stays 1;
  dispositions_by_lane stays 9 (moved, not a new repository). Resume predicate: re-run once PROPOSAL
  `LANE-B-R9-F1` lands, or once the primary rules a narrower fix or an exception sufficient - not on
  `LANE-B-R8-F1` alone, since this draw never reached the stage `LANE-B-R8-F1` fixes. Full detail:
  `evidence/build/lanes/lane-b/G4-W13-RERUN9.json`, the live source.

- **2026-09-17 07:51 (`date` checked) · G4-W13-RERUN10 · SEAL · `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`
  at `888700a8e361d32df21d0810c2eb939345e0603e` - `READY_FOR_PROPOSAL`.** Genuine changed-input retry,
  drawn once item 106 (`43bdb91`, `LANE-B-R9-F1`, "title-restatement guard tolerates real added detail")
  was confirmed landed via `git show` against `origin/main` and named in
  `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl`'s last row as unlocking exactly this
  repository. Facts unchanged (1,846 records, digest `bd8f4a983c791ea927ae01b7b0b848a8f88b1005863a5930e32560f8377965bb`,
  same as every draw since 2026-09-11). The transaction reached S9 validation (10 PASS/0 FAIL/1 PENDING),
  S10 independent review (verdict `ACCEPT`; `verdict_as_returned REJECT_PRESENTATION` on the first read,
  reversed on corroboration - `second_reader.read=2`, 8 corroborated ids, 0 surviving findings, 15
  advisory), one repair round (F04, S6 `quick_start`, repaired), and sealed on the first draw - 31 live
  provider calls, 0 `cache_stale`. A second fresh-process invocation (no `--fresh`) reused every stage
  with zero provider calls but found `examples.json` and `probes.json` bytes had shifted since the
  initial seal (10195 to 10107 bytes on `examples.json`); the seal mechanism correctly treated this as
  an unconfirmed proof and re-sealed rather than trusting the mismatch, exactly as designed. A third
  fresh-process invocation reproduced the second byte-for-byte on every content file (`README.md`,
  `content_units.json`, `dependencies.json`, `dispositions.json`, `examples.json`, `facts.json`,
  `investigation.json`, `plan.json`, `repairs.json`, `review.json`) with zero provider calls;
  `validation.json`'s only remaining difference was BC-11 itself moving `PENDING` to `PASS` (the no-op
  proof's own record) and `probes.json`'s only difference was registry-probe `elapsed_ms` timing
  telemetry, confirmed by a byte-for-byte diff to be the only changed field on every line. Final state:
  `candidates/aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp/888700a8e361d32df21d0810c2eb939345e0603e`,
  `READY_FOR_PROPOSAL`, `no_op_proof {byte_identical: true, fresh_process: true, provider_calls: 0}`.
  Reported literally rather than claimed as more than it is: the one `response_invalid` row this draw
  (job `section_authoring`, an `api_reference` unit citing `FitH, FitV` as identifiers outside its
  accepted fact values) is unrelated to item 106's fix, and this draw's own S5 `presentation_planning`
  output places the raster-image device facts into `capability:2` merged with text-extraction rather
  than as draw 9's standalone `capability:3` - a materially different split, so the exact single-purpose-
  capability scenario item 106 was written for did not recur here. This seal closes draw 9's resume
  predicate by producing a seal; it does not itself corroborate item 106's guard-tolerance branch, which
  went uncalled this draw. `sealed_by_lane` rises 1 to 2; `dispositions_by_lane` falls 9 to 8. One
  observation recorded, not a defect: `LANE-B-R10-OBS1` (lane-owned `cpp_examples.py` - a one-time,
  self-correcting byte drift between the first and second local build of the same revision in the same
  fresh worktree, root cause not conclusively isolated in this item's box; not re-proposed since the
  proof mechanism designed to catch exactly this kind of drift caught it, and the final sealed bytes are
  independently reproducible across two further fresh-process runs). `repository-presenter status` from
  this worktree after rebasing onto `origin/main` `1ed2416` (an unrelated bcpy seal landed mid-draw):
  18/34, risen by this draw's own seal and the concurrent unrelated one. `project/state.yaml`'s
  `progress.current_candidates` is edited from 17 to 18 in this same commit, by the one narrow method
  this lane may use: computed fresh from `repository-presenter status` against the just-rebased tree,
  confirmed by a second full local CI-equivalent run after the edit (1242 passed, 23 xfailed, 91s;
  the one failure before the edit, `test_status_reports_this_repository_cursor`, resolved). Full detail:
  `evidence/build/lanes/lane-b/G4-W13-RERUN10.json`, the live source.

- **2026-09-17 08:21 (`date` checked) · G4-W14-RERUN6 · resume predicate verified, not assumed, before
  drawing: `LANE-B-W14R3-F1` (arrival item 83) is landed.** `git show 7ea9c38` read in full against
  `origin/main` at `bec76ba` confirms `cited_fact_defect`/`factuality_defect` now also read the reviewed
  unit's own `inherited_unit` citations via new `_reviewed_unit_fact_ids`, `REVIEWER_LOGIC_VERSION` 5 to 6
  at landing (now 9 on current `origin/main`, per its own version-history comment: "7"/item 86 adds
  `excluded_disposition_defect` for an inherited_unit S4 marked `OMIT_UNSUPPORTED`; "8"/items 79+96 fold
  a groundless presentation finding the same way item 39 already folds a groundless factuality one; "9"/
  item 101 (`LANE-B-R8-F1`) recognizes the bare `<details>`/`</details>` tag as renderer chrome). A
  genuine changed-input retry against whatever shared code stands now, not a re-roll of `RERUN3`'s own
  transaction.

- **2026-09-17 08:21 · G4-W14-RERUN6 · `LANE-B-W14R3-F1` CLOSED, confirmed by measurement, not merely by
  the commit landing.** Redrew `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` end to end from a fresh
  worktree (`C:\w\b16`, branch `lane-b/G4-W14-RERUN6`) against `origin/main` at `bec76ba`. Same revision
  (`7b959706f2ad976db929f26ec079f43a07d578e1`), same 1190-fact digest (`2257a892ca080c6e76c7f13201efef0a6be9311fc4d37219cdad018d2770a5c4`)
  as `G4-W14-RERUN3`'s draw - same facts, but NOT a pure cache replay: this draw's ledger holds 45 rows,
  23 live provider calls (all HTTP 200) and 19 `cache_reuse` across S3-S6 and S10 (`repository_investigation`
  1 live/1 reused, `source_reconciliation` 3 live/3 reused, `presentation_planning` 1 live/1 reused,
  `section_authoring` 15 live/13 reused/2 `response_invalid`, `independent_review` 1 live/1 reused,
  `targeted_repair` 2 live/1 `response_invalid`), 0 `cache_stale` (a further non-materialisation of lane
  E's PROPOSAL E3 at this repository). Genuinely re-run, not assumed identical to RERUN3.
  `RERUN3`'s surviving finding (F04: the binary glTF `binaryMode: true` claim, refuted only by the
  reviewed unit's own SUPPORTED `inherited_unit:046.paragraph` citation, the case item 83's own commit
  message names by this repository) no longer appears anywhere in this draw's `review.json` - not
  blocking, not even advisory. The fix functions exactly as measured at landing time. `LANE-B-W14R3-F1`
  is CLOSED.

- **2026-09-17 08:21 · G4-W14-RERUN6 · did not seal: a second, distinct, genuine finding blocks.**
  Validation is 9 PASS / 1 FAIL / 1 PENDING (unchanged shape from RERUN3): BC-01 through BC-09 PASS,
  BC-10 FAILs at COMPOSING on REJECT_FACTUAL after 2 repair rounds (1 repaired, 1 re-raised - the
  equivalent failure stands), BC-11 PENDING (S12 never reached). The one surviving finding, F05
  (`second_reader.read = 1`), says `scope_limitations` omits that `Scene.render`, `Node.selectSingleObject`
  and `Node.selectObjects` "throw not implemented errors", citing `public_symbol:scene.render`,
  `public_symbol:node.selectsingleobject`, `public_symbol:node.selectobjects` (all SUPPORTED) plus
  matching `absent` strings. This is real, not a repeat of `LANE-B-W14R3-F1`'s class:
  `inherited_unit:077.list` (SUPPORTED, verbatim, lines 470-487 of the upstream README) names ALL of
  these methods in the very same sentence as the ones the candidate DID keep (`Mesh.union`/`difference`/
  `intersect`, `Watermark.encodeWatermark`/`decodeWatermark`) - "path-based scene queries
  (`Node.selectSingleObject()`/`Node.selectObjects()`), `Scene.render()`" - plus three more never even
  raised by review (`Mesh.doBoolean()`, `Mesh.optimize()`, `Mesh.isManifold()`, also named in the same
  sentence). `dispositions.json`'s own S4 record for `inherited_unit:077.list` (`VERIFIED_PRESERVE`)
  cites only 7 fact_ids as its evidence, none of the six symbols above; S6 authoring wrote a separate
  limitation bullet for `FileSystem` (citing `public_symbol:filesystem` alongside the same inherited
  unit) but never one for `Scene.render`/`selectSingleObject`/`selectObjects` despite equally-available
  SUPPORTED facts for all three - the same mechanism that produced the `FileSystem` bullet was available
  and unused. The one repair attempt (`b0e43fe2abafc344b9b794eb`, label F05, request
  `69ebe76749371f67515ed39504a80dc9f6088158b529e3254d190ef9e8cbd2ad`) touched `revised_output.omitted`
  rather than the `scope_limitations` unit's own text, and the re-review re-raised the identical finding.

- **2026-09-17 08:21 · G4-W14-RERUN6 · PROPOSAL `LANE-B-W14R6-F1` (shared code: reconciliation's S4
  disposition record for a single `inherited_unit` fact that enumerates many symbols in one sentence,
  and/or `composition/authoring.py`'s S6 use of that citation set when splitting the sentence into
  separate limitation bullets; secondarily `repair/targeted.py`'s repair for this finding shape) · an
  inherited unit naming N symbols in one sentence gets a citation set covering only some of them, so the
  rest have no path into the composed candidate even though they are equally SUPPORTED, equally named in
  the same verbatim sentence, and equally available at S6 - measured on 3D-TS: one finding raised (3 of
  roughly 9 omitted symbols named) and two more genuinely missing that review never even flagged
  (`Mesh.doBoolean`, `Mesh.optimize`, `Mesh.isManifold`).** The `FileSystem` bullet, cited from the same
  source sentence in a separate limitation slot, proves the mechanism to surface an individually-named
  symbol from this inherited unit exists and works; it simply was not applied to every symbol the
  sentence names. Full mechanical detail (fact IDs, the disposition record, the repair attempt) in
  `evidence/build/lanes/lane-b/G4-W14-RERUN6.json`, the live source. No check weakened; the lane may not
  edit `reconciliation/`, `composition/`, or `repair/`.

- **2026-09-17 08:21 · G4-W14-RERUN6 · DISPOSITION (RESTATED, cause changed) ·
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at `7b959706f2ad976db929f26ec079f43a07d578e1` -
  `BLOCKED_REVIEW (BC-10, REJECT_FACTUAL)`.** Same check and stage as `RERUN3`, different cause:
  `LANE-B-W14R3-F1` is CLOSED (see above); the standing finding is now `LANE-B-W14R6-F1`'s class. 1190
  facts unchanged (digest `2257a892...`); examples unchanged (8 EXECUTED, 1 CONTRADICTED, example:002).
  45 ledger rows this draw: 23 live provider calls, 19 `cache_reuse`, 3 `response_invalid`, 0
  `cache_stale`, 34,243 completion tokens; by job, `repository_investigation` 1 live/1 reused,
  `source_reconciliation` 3 live/3 reused, `presentation_planning` 1 live/1 reused, `section_authoring`
  15 live/13 reused/2 invalid, `independent_review` 1 live/1 reused, `targeted_repair` 2 live/1 invalid -
  a genuine re-run mixing fresh samples with reuse, not a byte-identical replay of RERUN3. All 10 review
  findings (1 blocking F05, 9 advisory F01-F04/F06-F10) are read fresh from this draw's own
  `review.json`; the deterministic fold logic (current on `origin/main`) decided which stand.
  `repository-presenter status` from this worktree measured 17/34 before rebasing; after rebasing onto
  `origin/main`'s new head (`8bacc16`, which carries `G4-W13-RERUN10`'s own concurrent PDF-Cpp seal,
  immediately above), the observed count is 18/34 - risen by that concurrent seal, not by this draw,
  recorded as observed in the just-rebased tree rather than assumed. `lane-b.yaml`'s own
  `sealed_by_lane`/`dispositions_by_lane` counters move 1/9 to 2/8 for the same reason (PDF-Cpp moving
  from disposition to seal) - not this draw's doing, and 3D-TS's own disposition is still one of the 8,
  restated rather than a new repository. Resume predicate: re-run once PROPOSAL
  `LANE-B-W14R6-F1` lands, or once the primary rules a narrower fix or an exception sufficient - not on
  `LANE-B-W14R3-F1` alone, since that class no longer appears in this transaction at all. Full detail:
  `evidence/build/lanes/lane-b/G4-W14-RERUN6.json`, the live source.

- **2026-09-17 11:31 · G4-W14-RERUN7 · did not seal: `LANE-B-W14R6-F1` is CLOSED, a new, distinct
  finding blocks.** Genuine changed-input retry of `G4-W14-RERUN6`'s `BLOCKED_REVIEW` (BC-10)
  disposition, verified against the checked-out source before drawing: `git show af795f3` confirms
  commit `af795f3` (arrival item 110, `LANE-B-W14R6-F1`) adds
  `inherited_unit_named_symbols()` to `composition/authoring.py` and calls it from
  `reconciliation/dispositions.py`'s `normalize()`, `NORMALISATION_VERSION` 7 to 8, and the commit's
  own text names item 110/`LANE-B-W14R6-F1`/3D-TS. Redrew
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` end to end (same revision
  `7b959706f2ad976db929f26ec079f43a07d578e1` and 1190-fact digest `2257a892...` as `RERUN6`, not a
  cache replay - 41 ledger rows, 25 live provider calls, 15 `cache_reuse`, 1 `response_invalid`, 0
  `cache_stale`). `LANE-B-W14R6-F1` is CLOSED, confirmed by measurement: `RERUN6`'s surviving finding
  (F05, `Scene.render`/`Node.selectSingleObject`/`Node.selectObjects` omitted from
  `scope_limitations`) does not appear anywhere in this draw's `review.json`, blocking or advisory -
  `content_units.json`'s `scope_limitations` unit `limitation:1` now carries all nine symbols
  `inherited_unit:077.list`'s sentence names (`Mesh.union`/`difference`/`intersect`/`doBoolean`/
  `optimize`/`isManifold`, `Watermark.encodeWatermark`/`decodeWatermark`,
  `Node.selectSingleObject`/`selectObjects`, `Scene.render`, `FileSystem.createZipFileSystem`), the
  fix functioning exactly as measured at landing. It did not seal: validation is again 9 PASS / 1
  FAIL / 1 PENDING, BC-10 FAILs at COMPOSING on `REJECT_FACTUAL` after one repair round, on a third,
  distinct, genuine finding (F03: `scope_limitations`'s `limitation:2` unit, citing
  `inherited_unit:046.paragraph` (SUPPORTED, the upstream README's own verbatim workaround text for
  the binary glTF `RangeError` bug) among its own `fact_ids`, paraphrases that fact rather than
  quoting it, and the reviewer's `absent`/factuality fold cannot recognize the paraphrase as
  grounded). Root-caused to shared review code - new PROPOSAL `LANE-B-W14R7-F1`, the lane may not
  edit it. Disposition RESTATED (same check, cause changed): `BLOCKED_REVIEW` (BC-10). Full
  mechanical detail in `evidence/build/lanes/lane-b/G4-W14-RERUN7.json`, the live source.

- **2026-09-17 11:31 · G4-W14-RERUN7 · PROPOSAL `LANE-B-W14R7-F1` (shared code:
  `review/independent/review.py`'s `factuality_defect`/`cited_fact_defect` literal-value refutation,
  `_cited_literal`; secondarily `absence_defect`'s section-slice text lookup) · a composed unit that
  faithfully paraphrases a SUPPORTED `inherited_unit` fact its own `fact_ids` cite - rather than
  quoting that fact verbatim - gets no refutation from either fold path, so a factuality/absence
  finding that misreads the paraphrase as unsupported or missing survives every check and blocks,
  even though the exact right fact is genuinely among the unit's own citations.** Measured on 3D-TS:
  `content_units.json`'s `scope_limitations` unit at `slot: "limitation:2"` (`fact_ids`:
  `example:007`, `inherited_unit:046.paragraph`, `public_symbol:globaltransform`) reads "Binary glTF
  export using binaryMode: true currently fails and throws a RangeError for any non-empty mesh, so
  only JSON/ASCII glTF export (the default, binaryMode: false) is supported." -
  `inherited_unit:046.paragraph` (SUPPORTED) is the upstream README's own verbatim text: "Binary
  glTF (`.glb`, `binaryMode = true`) currently throws a `RangeError` for any non-empty mesh ... Use
  the JSON/ASCII form (`binaryMode = false`, the default) shown above until that is fixed upstream."
  - the same fact, correctly cited, faithfully paraphrased. Independent review's F03 calls "JSON/ASCII
  glTF export (the default) is unaffected" `absent` and cites `example:007` (SUPPORTED - the very
  example that runs this exact code path with `binaryMode = false`) for its factuality claim; its own
  text admits "which the candidate correctly notes but fails to emphasize as the recommended
  workaround" - not a missing fact, a de-emphasis complaint riding under the `factuality` criterion.
  Traced mechanically against `scope_defect`'s fold stack: `absence_defect` requires the claimed-absent
  string to occur (under the same spelling rules that locate a quote) inside the candidate's own
  section slice - the candidate's paraphrase does not contain the string "is unaffected" - so it
  returns `None` (a "real remainder" by its own literal-text rule) and falls through to
  `factuality_defect`. There, `unit_fact_ids` correctly locates the unit and its citations (item 83's
  own widening), `reviewed` correctly includes `inherited_unit:046.paragraph`, but `_cited_literal`
  requires the **quote to contain the fact's literal value as a substring** - the candidate's sentence
  and the fact's sentence share the same meaning and cite the same evidence but not one contiguous
  matching run of text, so `_cited_literal` returns `None` and the finding is never folded.
  `repairs.json` confirms this is not a fixable phrasing gap: the one repair attempt (label
  `F03+F04`) revised the neighboring `limitation:4` unit for F04 but left `limitation:2`'s text
  unchanged for F03 - the model had nothing to correct, since the statement is already accurate - and
  the re-review re-raised F03 identically. Item 83 (`LANE-B-W14R3-F1`) closed the case where a
  reviewed unit's own inherited_unit citation is never checked at all; this is the same shape one
  level further - the citation is checked, but only by literal substring, which a legitimate paraphrase
  never satisfies. Proposed, smallest first: widen `_cited_literal` (or add a sibling check reachable
  from both `absence_defect` and `factuality_defect`/`cited_fact_defect`) to treat a cited SUPPORTED
  fact as grounding a claim it substantially restates - e.g. a normalized token-overlap or
  key-phrase test, not only contiguous substring containment - scoped exactly as `_cited_literal`
  already is, to the finding's own and the reviewed unit's own citations, never the whole fact set.
  Full detail: `evidence/build/lanes/lane-b/G4-W14-RERUN7.json`.

- **2026-09-17 11:31 · G4-W14-RERUN7 · DISPOSITION (RESTATED, cause changed) ·
  `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` at `7b959706f2ad976db929f26ec079f43a07d578e1` -
  `BLOCKED_REVIEW (BC-10, REJECT_FACTUAL)`.** Same check and stage as `RERUN6`, different cause:
  `LANE-B-W14R6-F1` is CLOSED (see above); the standing finding is now `LANE-B-W14R7-F1`'s class. 1190
  facts unchanged (digest `2257a892...`); examples unchanged (8 EXECUTED, 1 CONTRADICTED, example:002).
  41 ledger rows this draw: 25 live provider calls, 15 `cache_reuse`, 1 `response_invalid`, 0
  `cache_stale`, 49,747 completion tokens; by job, `repository_investigation` 1 live/1 reused,
  `source_reconciliation` 3 live/3 reused, `presentation_planning` 2 live, `section_authoring` 16
  live/11 reused/1 invalid, `independent_review` 2 live, `targeted_repair` 1 live - a genuine re-run,
  not a byte-identical replay of `RERUN6`. All 5 review findings (1 blocking F03, 4 advisory
  F01/F02/F04/F05) are read fresh from this draw's own `review.json`; the deterministic fold logic
  (current on `origin/main`) decided which stand. Rebased onto `origin/main`'s new head (`5e5db67`,
  two docs-only commits unrelated to this repository's own facts) before landing;
  `repository-presenter status` reads 18/34 in the just-rebased tree - unchanged by this draw, the
  rise since `RERUN9`'s 15/34 is `RERUN10`'s own concurrent PDF-Cpp seal, recorded as observed rather
  than assumed. `lane-b.yaml`'s own `sealed_by_lane`/`dispositions_by_lane` counters (2/8, set by
  `RERUN10`) are unchanged by this draw - 3D-TS's disposition is restated, not a new repository, and
  nothing sealed. Resume predicate: re-run once PROPOSAL `LANE-B-W14R7-F1` lands, or once the primary
  rules a narrower fix or an exception sufficient - not on `LANE-B-W14R6-F1` alone, since that class
  no longer appears in this transaction at all. Full detail:
  `evidence/build/lanes/lane-b/G4-W14-RERUN7.json`, the live source.

- **2026-09-17 13:17 · G4-W13-RERUN11 · DISPOSITION (SEALED) ·
  `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` at `c844a467cf7f2503819b655f4d6ceaef91056c40` -
  `READY_FOR_PROPOSAL`.** Task instruction 2026-09-17: Email C++'s blocker (arrival item 25,
  `BLOCKED_PLANNING`/S5 since `G4-W13-RERUN3`, 2026-09-16 15:48) landed as commit `fb0306e`,
  "defer a placement only this plan's own recomputation excludes"; verified directly against
  `origin/main` before drawing (`fb0306e` confirmed an ancestor of `origin/main`; its diff in
  `planning.py` mutates a disposition to `DEFER_UNRESOLVED` in place, mirroring
  `dispositions.normalize`, exactly as its own commit message and this file's prior entry
  describe). First draw of this repository since `RERUN3`. Two things changed at once, not one:
  besides item 25, the pinned upstream clone moved from `fef9c934c3ad7a207c97cc24546176e678f577af`
  (every prior draw) to `c844a467cf7f2503819b655f4d6ceaef91056c40` - a genuinely new revision, not a
  stale cache artifact (this transaction directory had never been touched before this run). Facts
  stayed byte-for-byte equal in shape despite the revision move (357 records, identical per-kind
  breakdown - `public_symbol` 225, `inherited_unit` 80, `link_target` 32, `example` 4, `identity` 5,
  `package` 4, `build_test_asset` 2, `license` 2, `dependency` 1, `import_path` 1, `install_command`
  1; 355 SUPPORTED, 0 UNRESOLVED, 2 CONTRADICTED), and the same two examples verify (`example:001`,
  `example:002`; 2 EXECUTED, 2 FAILED of 4 candidates) - so the upstream commit touched something
  outside every fact this extractor reads. First top-level invocation (draw A) hard-failed before
  any disposition: `independent_review` sent the same deterministic request twice (hash `e4396330`)
  and got invalid output both times ("unknown fact ID deviations:at_a_glance"), exhausting the job's
  two-attempt budget and raising `JobError` - a technical job failure with no `review.json` written,
  never a review verdict, so the W-card's no-reroll rule (which binds a genuine `BC-10` rejection)
  does not apply to it. Second top-level invocation (draw B, a fresh live call on the identical
  upstream stages) reached a real verdict: `independent_review` read `REJECT_PRESENTATION` on its
  first read and reversed to ACCEPT on corroboration (`second_reader.read=2`, 8 corroborated ids, 0
  findings surviving, 17 advisory) after one more rejected sample on the way. Validation 10 PASS / 0
  FAIL / 1 PENDING (`BC-11`, the no-op proof, not yet run); the repository sealed on this first
  completed draw: `candidates/aspose-email-foss__Aspose.Email-FOSS-for-Cpp/c844a467cf7f2503819b655f4d6ceaef91056c40`,
  4 provider calls in the bundle's own accounting. A third, independent fresh-process invocation (the
  no-op proof) reproduced every artifact byte-for-byte with zero provider calls (`facts.json`
  `c9fa6504...`, `investigation.json` `910383a5...`, `dispositions.json` `dacce0f8...`, `plan.json`
  `14b5c515...`, `content_units.json` `1f94db3f...`, `README.md` `bdeba3c3...`, `README.patch`
  `e34f5548...`, `validation.json` `d8f1eea6...`, `review.json` `16699bd9...` unchanged) - `state:
  READY_FOR_PROPOSAL`, `no_op_proof: {byte_identical: true, fresh_process: true, provider_calls: 0}`,
  another non-materialisation of lane E's PROPOSAL E3, this time at 55 ledger rows (32 `cache_reuse`,
  20 live, 3 `response_invalid`, 0 `cache_stale`) across all three invocations combined. **Item 25's
  own mechanism (deferring an `excluded` placement to `DEFER_UNRESOLVED` instead of failing closed)
  was NOT directly exercised**: `plan.json` for this draw records `quick_start_example_id:
  "example:001"`, `second_quick_start_example_id: null`, `additional_example_ids: ["example:002"]` -
  a single quick start, not the two that emptied `additional_examples` in every prior draw where the
  S5 model's own non-determinism produced the disposition record. `dispositions.json`'s summary
  (`OMIT_UNSUPPORTED` 24, `SUPERSEDE_REDUNDANT` 28, `VERIFIED_PRESERVE` 27, `VERIFIED_REWRITE` 1 = 80)
  carries no `DEFER_UNRESOLVED` row. The repository's real disposition changed because this draw's
  live S5 call happened to produce a plan the old bug's precondition never applies to, not because
  the fix's own new branch ran and defused it - recorded literally, per the standing rule against
  claiming a mechanism proven when it was not observed running; this mirrors `G4-W13-RERUN10`'s
  identical finding for item 106 on PDF C++. `sealed_by_lane` rises 2 to 3; `dispositions_by_lane`
  falls 8 to 7 (Email C++ moves out of disposition into a real seal, not lost).
  `repository-presenter status` reads 19/34 against `origin/main` at `0ced0a5` (rebased from
  `47735e2` mid-run, an unrelated PDFPY-02 fix); `project/state.yaml`'s `progress.current_candidates`
  is edited from 18 to 19 in the same commit as this entry, by the lane's one narrow method -
  computed fresh from `repository-presenter status` against the just-rebased tree, not incremented by
  hand. **Tooling hazard found and worked around, not silently absorbed:** the `Edit`/`Write` tool
  calls used for this item's own record-keeping (this file, the evidence file, the lane file, and
  `state.yaml`'s one permitted field) silently failed to persist to the real filesystem when targeted
  at this short-path worktree (`C:\w\b18`, outside the harness's declared primary working
  directory) - each reported success and read back correctly within the same tool-call context, but
  every targeted file's on-disk mtime stayed pinned at the worktree's original checkout time and
  every edit was invisible to a fresh `Bash` read, to `git status`, and to `pytest`. Confirmed by a
  direct comparison: a plain `Bash` append to the same file persisted immediately and stayed present
  across subsequent calls, while the prior `Edit`-tool appends never appeared on disk at all. Worked
  around by performing every edit in this item (this entry included) through a Python script invoked
  via `Bash` instead of the `Edit`/`Write` tools, for every path under this worktree. Full detail:
  `evidence/build/lanes/lane-b/G4-W13-RERUN11.json`, the live source.
