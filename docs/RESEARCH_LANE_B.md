# Lane B decision log (append-only; entries in RESEARCH_AND_GUIDELINES.md section 31 shape; the owner merges)

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
- **2026-09-06 · G4-W13 · DISPOSITION · `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp` at
  `733de4b` - `BLOCKED_RECONCILIATION`.** 518 tree entries, 2999 facts (2845 public symbols after
  401 from `_internal/` are dropped), 10 examples of which 9 compile and the tenth is a
  continuation fragment naming a `pres` from an earlier block. `pugixml` is the one required
  dependency, read from the library target's PUBLIC link interface; miniz, GTest and googletest
  are development. The `conanfile.py` under `packaging/conan/` is not on the build path - the root
  `CMakeLists.txt` fetches pugixml and miniz with `FetchContent` when `find_package` finds none,
  so conan was never needed and nothing was installed. Worth recording against the census: the
  three examples `aspose_org_upstream_issues` lists as not compiling (Notes, Table, Comments) all
  compile at this revision, and the Table example's own comment now documents that
  `Cell::text_frame()` returns a pointer. Preflight: required rows without evidence, none. S4
  rejected on `inherited_unit:043.heading` and `:044.code_block` placed into `installation`, the
  same class as Cells and Email. Resume predicate: the queued `source_reconciliation` fix, then
  BC-02 above.
