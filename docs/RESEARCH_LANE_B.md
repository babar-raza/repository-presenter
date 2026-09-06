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
