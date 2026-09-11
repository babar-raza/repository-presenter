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
