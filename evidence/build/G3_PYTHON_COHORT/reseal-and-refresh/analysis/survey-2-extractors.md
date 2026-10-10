authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
note: survey/review agent output; claims are AGENT-class evidence; BarCode-Python and Cells-Python reviews predate PR #305

# Survey 2: `src/repository_presenter/components/readme/extractors/`

Read-only survey, 2026-10-10. All paths below are relative to
`E:\Users\prora\OneDrive\Documents\GitHub\repository-presenter\src\repository_presenter\components\readme\extractors\`
unless prefixed `src/` (then relative to `src/repository_presenter/`). "Verified by run" means I executed the
vendored `package_manifest.parse_manifest` / the comma-join expression in isolation (stdlib only, no bytecode written); everything else is
verified by reading code.

## 0. Shape of the slice

The directory contains NO extractor for identity, license, README units, links, formats-as-facts, or asset facts. Those live outside it in
`src/.../components/readme/evidence/facts/*` (extract.py, inherited.py, links.py, license.py, assets.py, formats.py, product_pages.py). The slice owns exactly:

1. The per-ecosystem **platform plugins** (`platforms/`): manifest facts, public-symbol facts, registry reading, example verification.
2. A typed **facade over a vendored engine** from aspose.org (`surface/`), used by 6 of 7 plugins.
3. README **example candidate selection** and **example fact construction** (`examples/`).

Pipeline order (src/cli.py:2618-2700 and evidence/facts/extract.py `extract_facts`):
`plugin_for(ecosystem)` -> `plugin.detect_manifest` -> `assess_processability` -> `select_examples` (README fences) ->
`plugin.verify_examples` -> `verify_build` -> `extract_facts` (identity, `example_facts`, `format_facts`, `plugin.manifest_facts`, `plugin.registry_facts`,
`_source_build_fact` rewrite, `plugin.surface_facts`, license, assets, ci badge, product pages, inherited units, links).

Clone: fresh `git clone --depth 1` each run into `runs/clones/<owner>__<name>` (core/git_safety/clone.py:107-157). `tree_paths` = `git ls-tree -r HEAD` (core/snapshot/capture.py:164),
but plugins also read the working tree directly with `rglob`.

## 1. File-by-file inventory

Legend: IMPORTERS = production importers under `src/` (outside this directory unless stated). "dyn" = loaded by name via `importlib` (platforms/registry.py:65-70).

### `__init__.py` (1 line), `examples/__init__.py`, `platforms/__init__.py`, `surface/__init__.py`
Docstring-only package markers. Not orphans (package roots).

### `examples/selection.py` (84)
- Purpose: pick the README's fenced code blocks whose info-string language is in the ecosystem's `example_fences` as verification candidates, de-duplicated by whitespace-normalised body.
- Public: `select_examples(readme_path, readme_bytes, ecosystem) -> list[ExampleCandidate]` (:45). Private `_fence_parts`, `_normalized_body`.
- Facts emitted: none directly; carries `unit_id="inherited_unit:NNN.code_block"` (:81) so `example` facts link to inherited units.
- IMPORTERS: `src/cli.py:157,2640`. Imports downstream `evidence.facts.inherited.inventory_units` (:5) while `evidence/facts/extract.py` imports this package: a bidirectional dependency between "extractors" and "evidence/facts" (contradicts the AGENTS rule that an extractor never imports a downstream stage's module).
- Versions: none.

### `examples/verify.py` (60)
- Purpose: turn `ExampleReceipt`s into `example` facts, polarity mapped EXECUTED->SUPPORTED, FAILED/TIMED_OUT->CONTRADICTED, NEEDS_INPUT/NOT_VERIFIED->UNRESOLVED (:10-16).
- Public: `example_facts(candidates, receipts, receipts_path)` (:19). Emits `example:NNN` (:51-58); fact `value` is the example source code; evidence = README line range + receipt detail (+ fixture bindings).
- IMPORTERS: `evidence/facts/extract.py:18,127`. Versions: none.

### `platforms/registry.py` (119)
- Purpose: the plugin registry. `PlatformPlugin` Protocol (:24-58), `known_ecosystems()` (:73), `plugin_for()` (:91), `verify_build()` (:105; capability-checked via `getattr(plugin,"verify_build")`).
- Mechanism: a plugin is any module in `platforms/` exposing `PLUGIN`; discovered by `pkgutil.iter_modules`, imported with `import_module`. `_module_for` swallows ImportError (:67-70) (see section 5).
- IMPORTERS: `src/cli.py:158-162,1317,1534,2618,2669`; `bundle/reproducibility.py:20,76`; `evidence/facts/extract.py:19`; `evidence/processability.py:15`.

### Platform plugins (dyn-loaded, each exposes `PLUGIN`; ecosystems: python, typescript, go, java, net, rust, cpp)

| file | lines | purpose | manifest read |
|---|---|---|---|
| `python.py` | 391 | Python plugin | `pyproject.toml` (PEP 621 only), else `setup.cfg`, else `setup.py` (AST literal) - repo ROOT only (:236-241) |
| `typescript.py` | 475 | TS plugin | best-ranked `package.json` anywhere (:260-289) |
| `go.py` | 444 | Go plugin | shallowest `go.mod` (:220-239) |
| `java.py` | 590 | Java plugin | best-ranked `pom.xml` (:340-367); Gradle only via vendored reader fallback |
| `net.py` | 409 | .NET plugin | best-ranked `.csproj/.fsproj` or `Directory.Build.props` (:215-257) |
| `rust.py` | 458 | Rust plugin | shallowest `Cargo.toml` (:237-255) |
| `cpp.py` | 581 | C++ plugin | best-ranked `CMakeLists.txt` (:337-369), regex over text, comments not stripped |

Each plugin exposes: `ecosystem`, `manifest_globs`, `source_suffixes`, `detect_manifest`, `manifest_facts`, `surface_facts`, `registry_facts`, `verify_examples`, `format_claims`, `format_declarations`, and (TS and .NET only) `verify_build`.
Fact kinds each emits (all via `core.facts.fact_id`):

- **package** ids: python `package:name|version|python_requires|python_versions|license` (python.py:320-324); ts `name|version|node_engine` (typescript.py:296-340); go `name|go_version` (go.py:246-299); java `name|version|java_release` (java.py:376-440); net `name|version|target_framework` (net.py:264-310); rust `name|version|rust_edition|rust_version` (rust.py:262-328); cpp `name|version|cxx_standard|cmake_minimum` (cpp.py:398-451).
- **install_command** ids: `install_command:pip|npm|go|maven|dotnet|cargo|cmake`, always initial polarity UNRESOLVED (conf 0.5), later re-issued by `registry_facts` and possibly rewritten to a source-install by `evidence/facts/extract.py:_source_build_fact`.
- **import_path**: python (package dirs or declared packages, python.py:370-385); ts (= package name, typescript.py:315-321); go (module path + discovered subdir, go.py:271-289); rust (`canonical_package`, rust.py:281-299); cpp (the first `add_library` target, cpp.py:452-461). Java and .NET emit NO import_path.
- **dependency**: python (required/optional/development buckets; `dependency:none` sentinel) python.py:325-356; ts `dependencies`/`peerDependencies` required, `optionalDependencies`, `devDependencies` (typescript.py:96-148); go `require` lines (go.py:174-210); java POM `<dependencies>` with scope buckets (java.py:189-232); net PackageReference with PrivateAssets bucket (net.py:160-205); rust `[dependencies]`, dev/build (rust.py:181-227); cpp `find_package`/`FetchContent_Declare` split by public link interface (cpp.py:268-327).
- **public_symbol**: python via first-party AST (`python_surface.py`), the other 6 via the vendored tree-sitter engine through `surface/extractor.py`. Attributes: `symbol_kind`, `signature`, `docstring` (+ python `defined_at`, `public_paths`, `shadowed_by`).
- No plugin emits `identity`, `license` (except `package:license` from python manifest only), `capability` (nobody emits it, see section 2), `format` (see below).

Per-plugin helper modules (all imported only by their plugin):

- `python_surface.py` (534): `inspect_public_surface`, `public_symbol_facts`. AST-only public surface (name rule, literal `__all__`, `__init__` re-exports, re-export chain following, shadowing, case-collision suffixes). `PublicSurface.unresolved` (star imports, syntax errors) is computed (:79-80, :367-370) and never consumed.
- `python_setup_py.py` (176): `parse_setup_py`, `literal_setup_keywords`. Proven-setuptools-call literal reader. The ONLY source of `python_classifier_versions` (:157-159).
- `python_registry.py` (115): `observe_pypi`, `fetch_project_json`; httpx GET with retry; registers `register_observer("python", observe_pypi)` (:115) consumed by `src/components/issues/redetect.py` via `core/package_registry.py`. Constants `PYPI_PROJECT_URL`, `REQUEST_TIMEOUT_SECONDS=15`, `USER_AGENT`.
- `python_formats.py` (147): `format_claims(code)` - AST read of extension literals near load/save verbs with a dead-code exclusion (`if False`, unreferenced function).
- `python_format_declarations.py` (233): `format_declarations(root, tree_paths)` - hard-coded to Aspose's `FileFormat.py` (:128) + `register_plugin(...)` + `get_file_format`/`importer*`/`exporter*` attributes (:160-205).
- `python_examples.py` (703): `verify_python_examples` - venv + `pip install <clone>` (falls back to PYTHONPATH of source roots when the build fails, :471-515), runs each example as a process, stages fixtures from repository files (NEEDS_INPUT retry), retries FAILED `ModuleNotFoundError` after installing the matching declared extra; selects interpreter by `requires-python`, pinned toolchains under `runs/verify` or `RP_PYTHON_TOOLCHAINS`.
- `typescript_barrel.py` (267): `entry_barrel`, `reexported_bindings`, `read_json`, `compiler_options`, `IGNORED_DIRECTORIES`; the "what the entry point re-exports" closure by regex over `export ... from`. `reexported_names` (:265) is DEAD (no caller in `src/` or `tests/`).
- `typescript_examples.py` (572): `verify_typescript_examples` (`tsc --noEmit` against sources), `verify_typescript_build` (`npm install` [+ `npm run build` if declared]) in a copy of the checkout, `typescript_compiler()` (registry-first), `npm_executable()`.
- `go_examples.py` (369): `verify_go_examples` - wraps snippet in a module with a `replace` directive, `go build ./...` then `go vet` (`GOFLAGS=-mod=mod`); imports completed from `undefined:` diagnostics + a stdlib table.
- `java_examples.py` (541): `verify_java_examples` - `javac` of product tree once, per-example classpath compile; refuses (NOT_VERIFIED) if the POM declares required deps.
- `net_examples.py` (375): `verify_net_examples` (console wrapper with ProjectReference, `dotnet build`), `verify_net_build`, `build_product` (copy + `dotnet build <project>`).
- `rust_examples.py` (331): `verify_rust_examples` - copies crate, `cargo check`, writes each fence as an `examples/` target, `cargo check --example`.
- `cpp_examples.py` (587): `verify_cpp_examples` - CMake configure/build (Ninja, FetchContent = network), optional MSVC retry, then `-fsyntax-only` per example.

`format_claims` / `format_declarations`: real only in python. ts/go/java/net/rust/cpp return `[]` ("Not yet built", e.g. typescript.py:466-472). So `format:` facts can only ever be produced for Python.

IMPORTERS for plugin modules: `platforms/registry.py` by name (dyn); helper modules by their plugin. `python_registry` is also reached through `core/package_registry.OBSERVERS` by `components/issues/redetect.py`. No static production importer of any plugin module (not orphans).

Version constants owned in the directory:
- `EXTRACTOR_VERSION = "1"` - `surface/extractor.py:30`. One global scalar. Fed to `src/components/readme/bundle/seal.py:271` (`environment_dependencies()["extractor_version"]`) and `:285` (`code_dependencies()`), thus `dependencies.json -> environment.extractor_version`. Never bumped since introduction in 3635efdb (git `-G` search shows a single commit), despite ~79 commits touching this directory; no test enforces a bump (only `tests/.../bundle/test_evaluation.py` uses the literal).
- Per-ecosystem `EcosystemSpec` timeouts (`example_timeout_seconds`, `install_timeout_seconds`) and fence aliases (typescript.py:52, go.py:50, java.py:41, rust.py:54, cpp.py:48; python/net specs live in `src/core/ecosystems.py:198,229`) - not versioned: changing them changes verdicts with no dependency record.
- Vendored pin: "aspose.org at 16d75e95d4" in `surface/_vendor/aspose_extraction/__init__.py`.
- Behavioural constants: TS barrel `_MAX_FILES=400` (typescript_barrel.py:52); vendored `MAX_FILES = int(os.environ.get("SCOUT_MAX_FILES", 8000))` (tree_helpers.py:47); `_MAX_IMPORT_PATH_DEPTH=2` (python.py:56).

### `surface/extractor.py` (273)
- Facade over `api_surface.extract_api_surface`. `surface_symbols(parser, language, package_root, repository_root, family) -> list[SurfaceSymbol]` (:144), `slug_safe`, `symbol_kind`, `SurfaceSymbol`, `EXTRACTOR_VERSION`.
- Keeps only: name, kind, file, line, first-sentence doc, method signature; drops anything with `visibility=="internal"` (:174); adds one `module` symbol per namespace prefix (`_namespaces`); de-duplicates by value (first wins) and numbers slug collisions (`_disambiguate`, :254).
- Discards from the engine: `reachable`, `deprecated`, `bases`, `is_static`, enum members/constants, `claims`, `scout_report` (`types, *_ =` at :162). Grep confirms no consumer of `reachable` outside `_vendor` (see section 5: Rust docstring claims otherwise).
- IMPORTERS: plugins ts/go/java/net/rust/cpp; `bundle/seal.py:78`.

### `surface/manifest.py` (81)
- `read_identity(repository_root, platform, manifest=None) -> PackageIdentity` (:47): runs the vendored `package_manifest.parse_manifest` on `manifest.parent` and `package_root.detect_package_root`. `PackageIdentity` has name/version/floor/package_root/manifest_path/raw.
- IMPORTERS: plugins ts/go/java/net/rust/cpp and `evidence/facts/extract.py:20,257` (called for ANY ecosystem incl. python, to get the declared license).

### `surface/registry.py` (183)
- `observe(ecosystem, package_name, *, repository_url, fetch, offline, sleep) -> RegistryObservation` (:125), `REGISTRY_TYPES` (:36; python->pypi, net->nuget, java->maven, typescript->npm, go->go_modules, rust->cargo; cpp deliberately absent), `TRANSIENT_STATUSES`. Retries transient answers under `RETRY_POLICIES["package_registry"]`.
- Has its own `RegistryObservation` dataclass; `core/package_registry.py` has a different class of the same name used by Python.
- IMPORTERS: plugins ts/go/java/net/rust/cpp (`observe`), `python_registry.py:21` (TRANSIENT_STATUSES), `evidence/facts/extract.py:21,92` (`REGISTRY_TYPES` membership decides "registry-less" => cpp).

### `surface/_vendor/aspose_extraction/` (vendored; header says "unmodified except the import rewrite" - not exactly: `tree_helpers.get_parser` was rewritten to delegate to `core.grammars` (tree_helpers.py:196-208))
- `api_surface.py` (3768): `extract_api_surface(parser, language, pkg_root, repo, family, *, excluded_package_segments=None)` (:2727) - per-language tree-sitter walk (classes, methods, properties, enums, Go/Rust impl association, inheritance flattening, preprocessor-branch exclusion, doc extraction). The Python branches (`_extract_python_*`, `_python_top_level_exports`, ~1,000+ lines) are not reachable in production (no plugin calls `surface_symbols` with `"python"`); they are exercised only by `tests/.../surface/test_parity.py`, the "parity control".
- `tree_helpers.py` (1006): node-type tables, `_collect_source_files` (sorted, capped at `MAX_FILES`, excludes `tests/test/examples/docs/scripts/tools/build/dist/...` anywhere under the package root, :462-470), `is_public`, `visibility_tier`. Only `.ts` (not `.tsx`) for TypeScript and `.cpp/.h/.hpp` for C++ (:165-178), although the C++ plugin declares `.hxx/.cc/.cxx` as source suffixes.
- `package_manifest.py` (420): regex/TOML manifest readers per platform (python, dotnet, java, js, go, rust, cpp).
- `package_root.py` (170): source-root detection per platform.
- `publication_probe.py` (267): `probe_publication` (adapters + Maven metadata + PyPI details + repo-URL corroboration + metadata findings). Only `probe_publication` and `default_fetch` are used; `format_publication_line`, `default_resolve_url` (reachable only if `repository_url` is passed, which no caller does), `_metadata_findings` output are discarded.
- `package_registries/{__init__,cargo,go,npm,nuget,pypi}.py`: `check_published` adapters used; `search()` (cargo/npm/nuget/pypi), `apply_debounce`, `is_corroborated_match`, `REQUIRED_CONSECUTIVE_CHECKS` are DEAD in this repository (no caller; grep).
- `lang/{__init__,cpp,csharp,go,java,python,rust,typescript}.py`: per-language adapters. Only `export_surface`/`resolve_entry_point` for python, rust, typescript are called by `api_surface` (:2805-2823); `parse_doc`, `doc_anchor` (Go only wired), `export_groups`, `declaration_kinds`, csharp `internal_names` are unused. `lru_cache(maxsize=64)` memoises export scans by path for the life of the process (lang/python.py:121, rust.py:107, typescript.py:314/455, csharp.py:124).
- Vendored files carry mojibake (UTF-8 em-dashes decoded as cp1252, e.g. "extraction/api_surface.py â€”").
- IMPORTERS: only `surface/extractor.py`, `surface/manifest.py`, `surface/registry.py` (a boundary that is respected).

## 2. Q1 - Complete fact-kind list and the clone files each derives from

`FactKind` (src/core/facts.py:19-34) has 14 kinds. Derivation (exact clone inputs):

| kind | producer | derived from |
|---|---|---|
| identity (`identity:repository|revision|family|platform|ecosystem`) | evidence/facts/extract.py:42-54 | NOT the clone: `data/registry.json` entry + pinned revision from `source/snapshot.json` |
| package | platform `manifest_facts` | python: `pyproject.toml` / `setup.cfg` / `setup.py` (root only); ts: `package.json` (`name,version,engines.node`); go: `go.mod` (`module`,`go` directive); java: `pom.xml` (groupId/artifactId via vendored regex, version, `maven.compiler.*`); net: `.csproj` (+ MSBuild default name = file stem); rust: `Cargo.toml`; cpp: `CMakeLists.txt` regexes |
| install_command | `manifest_facts` + `registry_facts` + `_source_build_fact` | package name from manifest, polarity from a LIVE registry read (PyPI JSON, NuGet, npm, crates.io, Go proxy, repo1.maven.org), value rewritten to a clone-and-build command when the registry says absent/none and a build/example proves it |
| import_path | `manifest_facts` | python: `tool.setuptools.packages` or git-tracked `__init__.py` dirs (depth <= 2); ts: `package.json name`; go: module path + subdir containing declarations; rust: `[lib] name` or crate name; cpp: first `add_library`; (java/net: none) |
| dependency | `manifest_facts` | the same manifest as above (python extras/setup.cfg/setup.py literals; `go.mod require`; pom `<dependencies>`; csproj `PackageReference`; Cargo dependency tables; CMake `find_package`/`FetchContent_Declare`) |
| public_symbol | `surface_facts` | python: `*.py` under git-tracked package dirs via `ast`; ts: `.ts` files under the entry barrel dir, filtered by regex re-export closure; go/java/net/rust/cpp: tree-sitter over `.go`/`.java`/`.cs`/`.rs`/`.h|.hpp|.cpp` (Java: `src/main/java`; C++: `include/`) |
| example | `examples/verify.py` | fenced code blocks of the README only (`select_examples`); polarity from running/compiling them against the clone |
| format | `evidence/facts/formats.py` | python only: extension literals in README example code + `FileFormat.py` / `register_plugin` AST scan; other ecosystems yield none |
| capability | NOBODY | declared in FactKind (core/facts.py:27) but no producer anywhere in `src/` (grep for `"capability"` finds only authoring slot labels `capability:N`, composition/authoring.py:575 etc.). Dead kind |
| license | evidence/facts/license.py | root `LICENSE*`/`COPYING` (text regex into 7 SPDX ids, else `UNCLASSIFIED`/UNRESOLVED) or manifest license field when no file |
| third_party_notices | license.py:69-80 | root `NOTICE*`/`THIRD-PARTY-NOTICES*` file path only (content never read) |
| build_test_asset (`tests|ci|docs|examples`) | evidence/facts/assets.py:179-187 | existence of tracked paths with the prefixes `tests/`, `.github/workflows/`, `docs/`, `examples/` (first 5 paths as evidence; contents never read) |
| link_target | links.py; assets.py `ci_badge_fact`; product_pages.py | every link/image in the README (liveness HTTP GET for external, tree lookup for relative, heading-slug for anchors); the one push-triggered build workflow in `.github/workflows` (YAML parsed); banner/enterprise product-page URLs from registry entry (live HTTP) |
| inherited_unit | evidence/facts/inherited.py | the README (markdown-it blocks; member-reference lists split per bullet) |

(Kinds not in this directory are summarised only to answer the question; I read their docstrings and key bodies, not exhaustively.)

## 3. Q2 - What the clone offers that is NOT a fact

| item | status | evidence |
|---|---|---|
| docs/ or other markdown guides | **partially / not read**: only `build_test_asset:docs` (existence + up to 5 paths) | assets.py:182-185; no module reads any `.md` except the one README (`snapshot.readme_path`, core/snapshot/inventory.py:14) |
| CHANGELOG / release notes | **not extracted** | no match for changelog/release in extractors, evidence, snapshot |
| CONTRIBUTING / SECURITY / CODE_OF_CONDUCT / SUPPORT | **detected then dropped**: `inventory.scan` finds them (inventory.py:35-45,79) but `RepositorySnapshot` (capture.py:47-50) keeps only readme/license/notices, so no fact; (`components/metadata` handles them separately, outside this survey) | |
| tests as usage examples | **not extracted**: README fences are the only example source (selection.py:45-84); `build_test_asset:tests` is presence only | |
| CLI `--help` / entry-point commands | **not extracted**: no read of `[project.scripts]`, `console_scripts`, package.json `bin`/`scripts` (scripts.build is read only to drive a build, typescript_examples.py:435), Cargo `[[bin]]`, Go `main` packages (vendored reader even skips `package main`, package_manifest.py:246); nothing ever runs a `--help` | |
| configuration options / env vars | **not extracted** | no fact kind for them |
| directory layout / architecture | **partially**: `import_path` from package dirs, `build_test_asset` presence, namespace `module` public_symbols | python.py:215-226; extractor.py:221 |
| supported versions matrix | **partially**: python `requires-python` + classifier versions (classifiers only from `setup.py`, never from pyproject: python_setup_py.py:157 vs parse_pyproject :120-166), Node `engines.node`, Go `go` directive, Java release/target/source, .NET only the LOWEST target framework (net.py:152-157 while `raw.target_frameworks` holds all), Rust edition/rust-version, C++ standard/cmake_minimum. No per-OS, per-runtime matrix, no CI matrix | |
| supported formats | **python only** (README example literals + FileFormat/register_plugin heuristics specific to Aspose); other six: empty | python_format_declarations.py:128,160; typescript.py:466-472 etc. |
| screenshots / images | **partially**: README image targets become `link_target` (existence/HTTP only). No image inventory, no `docs/images`, no alt-text/figure fact | links.py:130-197 |
| GitHub workflows | **partially**: one push-triggered build-ish workflow becomes a badge `link_target` (YAML parsed for `on: push` and a build/test `run` step); `build_test_asset:ci` is presence; no job matrix, versions, OS, release/publish workflows | assets.py:117-176 |
| issue / PR templates, CODEOWNERS, dependabot | **not extracted** | |
| LICENSE | **extracted** (7 classifiers; others become `UNCLASSIFIED`, UNRESOLVED) | license.py:14-22,105-113 |
| Subdirectory / monorepo packages | **not extracted**: Python plugin reads only root manifests; others pick ONE manifest by ranking | python.py:236 |
| Python Poetry/Flit/PDM (`[tool.poetry]`) | **not extracted**: manifest requires `[project]`; dynamic dependencies are mis-reported as verified zero (section 5) | |
| Public API docstrings beyond first sentence; deprecation; inheritance; enum members; constants | **dropped by the facade** (engine computes them) | extractor.py:162 |

## 4. Q3 - Ecosystem registry, example verification

Registration: file-name discovery. `platforms/registry.py:73-88` lists every sibling module exposing `PLUGIN`; `plugin_for` caches (:91-102). Specs (`EcosystemSpec`) are a second registry: python and net in `src/core/ecosystems.py:198,229`; the other five declare their own spec in the plugin module and `SPECS.setdefault(...)` at import (typescript.py:82, go.py:91, java.py:78, rust.py:104, cpp.py:86). Consequence: `spec_for("go")` fails until the plugin has been imported (ordering coupling; cli calls `plugin_for` first). Registry-probing is a third table, `surface/registry.py:36 REGISTRY_TYPES`, and a fourth, `core/package_registry.OBSERVERS` (only python registers).

Supported: **python, typescript, go, java, net, rust, cpp** (7).

| ecosystem | verification method | toolchain | network |
|---|---|---|---|
| python | venv (`--without-pip`) + `pip install <clone>` into `--target`, then RUN each example as a process; fixtures staged from repo files; source-tree PYTHONPATH fallback if the build fails | presenter's Python or pinned uv venvs under `runs/verify` / `RP_PYTHON_TOOLCHAINS`; pip | YES: pip resolves dependencies from PyPI |
| typescript | `tsc --noEmit` type-check (NOT run); also `npm install` (+`npm run build`) in a copy to prove a source install | `tsc` (toolchain registry first, then PATH), `npm`, `node` | YES: `npm install` |
| go | `go build ./...` + `go vet` in a wrapper module with `replace` to the clone (compile + vet, NOT run) | `go` | YES: `GOFLAGS=-mod=mod` fetches dependencies via module proxy |
| java | `javac` compile of product sources once + per-example compile (NOT run); NOT_VERIFIED if POM declares required deps | `javac` (installed JDK before PATH) | no (by design) |
| net | wrapper console project with ProjectReference, `dotnet build` (compile only); also `dotnet build <project>` on a copy as the source-install proof | `dotnet` SDK | YES: NuGet restore |
| rust | `cargo check` on a crate copy, then each fence as `cargo check --example` (type-check only) | `cargo` (+`RUSTUP_HOME`) | YES: crates.io |
| cpp | CMake configure/build (Ninja; MSVC fallback), then `g++ -fsyntax-only` per example (NOT linked/run) | gxx, cmake, ninja, optional vcvarsall | YES if the project uses `FetchContent` (cpp_examples.py:93) |

All verifiers: missing toolchain -> `NOT_VERIFIED` (-> fact UNRESOLVED, never CONTRADICTED). Execution is via `core.execution.execute` with a secret-free environment and caches redirected into the workspace (`profile_environment`), i.e. credentials are stripped but there is no network sandbox; repository code (Python examples, build scripts, cmake, npm install scripts, cargo build.rs) runs with the host network. Receipts use outcome `EXECUTED` even when only compiled/type-checked (go_examples.py:364, rust_examples.py:322, typescript_examples.py:554, net_examples.py:350): `EXECUTED` => `example` fact SUPPORTED means "compiles" for 6 of 7 ecosystems.

Registry probes (live HTTP) for `install_command`: PyPI (python_registry.py, httpx, own retry), others via vendored `urllib` + `probe_publication` (npm, NuGet, crates.io, proxy.golang.org, repo1.maven.org). cpp: no registry, `observe` returns inconclusive without network (surface/registry.py:159-162).

## 5. Q4 - What reopens when an extractor changes

Mechanism (src/components/readme/bundle):
- `seal.py:259-292`: `dependencies.json` records `environment` = {python_version, os, **extractor_version**, inherited_units_version, presenter_site_manifest (hash of the presenter's pip set), toolchains{tool: version|absent}} and, under `facts`, a map `{fact_id: canonical_hash(asdict(fact))}` (seal.py:... `upstream_dependencies`) for EVERY fact.
- `evaluation.py:78-113`: each differing `environment.*` sub-field is a change; any difference in the `facts` map (added/removed/altered ids) is ONE `facts` change.
- `invalidation.py:68-75,167-169`: `source`, `facts`, and every `environment.*` map to the `facts` scope -> re-enter EXTRACTING and state **INVALIDATED** (the only scope that invalidates; all others yield VALID_UPDATE_AVAILABLE).

Answers:
1. Bumping `EXTRACTOR_VERSION` (surface/extractor.py:30) reopens EXTRACTING and INVALIDATES every sealed candidate of every ecosystem (one global scalar; the comment at extractor.py:26-29 states this intent). Editing a plugin file WITHOUT bumping it records nothing: plugin source is not hashed. The change surfaces only if a later re-extraction produces different facts. The bump is manual and unenforced; it has never been bumped (single `-G` hit in history; no test).
2. A new fact kind (or new fact ids in an existing kind): existing candidates' on-disk `facts.json` do not change until they are re-extracted. On the next extraction/evaluation of any repo that now yields extra facts, `facts` map keys differ ("N fact records added"), so that candidate is INVALIDATED at EXTRACTING even if no prompt consumed the new facts: the facts dependency is the whole map, not "the facts this candidate consumed" (evaluation.py:102-113 compares entire dicts). If the new kind can appear for every repository (e.g. a CHANGELOG/CLI fact), that is every candidate. Additionally the kind needs a `core/facts.py` `FactKind` Literal change (not registry-based).
3. Toolchain availability/version changes (core/toolchains.toolchain_fingerprint, flattened to `environment.toolchains.<tool>`), Python version, OS, presenter pip set all reopen EXTRACTING/INVALIDATED for all candidates.
4. Volatile data inside hashed facts also reopens: external `link_target` evidence includes `HTTP <status>` / `unreachable: <exception text>` (links.py:300-304, product_pages.py:49-69), and install-command evidence includes registry presence (`package registry: found on pypi`); a link going 200->404 upstream flips `facts` and INVALIDATES with no repository change. Registry volatile data (latest version, timing) is correctly kept in `ProbeRecord`s; link liveness is not (despite links.py:350-353 claiming RC7 compliance).
5. Ordinal-keyed IDs (`link_target:NNN`, `inherited_unit:NNN.*`, `example:NNN`) shift for all later facts when a README gains an early item.

## 6. Q5 - Dead code, duplicated authority, hidden fallbacks, determinism hazards

### Confirmed defects (by run or by reading)
1. **Python dependency corruption** (verified by run of the join/split expression; python.py:139 `",".join(...)` then :328 `.split(",")`): a requirement such as `numpy>=1.20,<2` becomes two facts: `numpy>=1.20` and `<2` (id `dependency:2`). Same join for setup.cfg (:185) and setup.py (python_setup_py.py:164).
2. **Maven identity taken from `<parent>` block** (verified by run): vendored `_parse_java_manifest` uses first-match regex `<artifactId>`/`<groupId>` (package_manifest.py:176-181); for a POM with a `<parent>` it returned `{'group_id':'org.parent','artifact_id':'parent-pom','version':'9'}`. `java.py:_coordinate` uses these (:235-241), so `package:name`, the `mvn dependency:get` command and the Maven Central probe address the PARENT. (`_dependencies`/`_properties` use ElementTree and are right, so the two disagree within one plugin.)
3. **Dynamic/other Python dependency declarations reported as verified zero**: if `[project]` has a name and no `dependencies` key, python.py:338-345 emits `dependency:none` ("no `project.dependencies` is declared"). `dynamic = ["dependencies"]` (setuptools `file=requirements.txt`) is not checked; setup.py is not consulted when pyproject has a name (python.py:208-211).
4. **Python `package:python_versions` never emitted for pyproject-based repos** (classifiers read only in setup.py path).
5. **src-layout import path**: `package_directories` (python.py:215-226) treats `src/pkg/__init__.py` as dotted `src.pkg` (only `tests, test, docs, examples, pyi, scripts, build` are excluded, :55). `surface_facts` then reads the surface relative to `src` (correct names), so `import_path:src.pkg` contradicts the `pkg.*` symbols. Test coverage is a namespace-layout fixture only (test_python.py:117-118). (Reading-based; not run.)
6. **Absolute-path component exclusion**: ts/java/net/cpp `detect_manifest` filter on `path.parts` of an ABSOLUTE rglob result (typescript.py:273; java.py:354; net.py:236; cpp.py:354; typescript_barrel.py:170-171), while go and rust correctly use `path.relative_to(root).parts`. A work tree under any ancestor directory named `build`, `out`, `target`, `lib`, `dist`, `bin`, `obj`, `packages`, `vendor`, `external` (or, for the TS barrel fallback, `test`, `docs`, `examples`, `demo`, ...) makes every manifest "ignored": silently no manifest, package, install or dependency facts. Environment-dependent output.
7. **Rust "reachable from crate root" is not enforced**: rust.py:332-340 and the module docstring say the facade decides what is public "`pub` reachable from the crate root, re-exports included". The engine computes `reachable` (api_surface.py:3464) but the facade ignores it (extractor.py:174 filters only `visibility=="internal"`; grep finds no other `reachable` consumer). Unreachable `pub` items are published as `public_symbol`s.
8. **Registry presence is treated as ownership**: `registry_facts` marks `SUPPORTED` when the NAME exists on the registry. The vendored corroboration rule (`is_corroborated_match`, repo-URL match, "foss" name rule) exists but is dead; callers never pass `repository_url` (e.g. typescript.py:402 `observe(self.ecosystem, name.value)`), and `metadata_findings`/`repo_url_corroborated` are discarded. Python's `observe_pypi` also ignores `project_urls`. An unrelated package with the same name verifies the install claim.
9. **Stale/incorrect message in Java**: java.py:517-522 (inconclusive branch) states "the shared probe takes a package name, and maven-metadata.xml is addressed by group and artifact id" - false since `observe` splits group:artifact (registry.py:152-156). Any transient failure is reported with this wrong cause.
10. **Python `public_symbol` `unresolved` list discarded**: syntax errors, star imports and unresolvable relative imports are collected (python_surface.py:147,187,357) then never emitted; a module with a syntax error silently yields no symbols and no marker.

### Determinism / environment hazards
- `SCOUT_MAX_FILES` env var changes the engine's file cap (tree_helpers.py:47); beyond the cap files are silently dropped (logged only; `scout_report` discarded) => API surface depends on env and truncates quietly. Cap order is sorted, so deterministic for a fixed value.
- Absolute-path filtering (above).
- Toolchain/receipt text carries tool versions (`javac X`, `SDK X`, `Go X`, `cargo X`, `tsc X`, `Python X (label)`) into `example` fact evidence: facts differ per machine toolchain (tracked in `environment.toolchains`, so intentional, but means sealed facts are not portable across machines).
- Receipt `stdout`/`stderr` of Python examples are sealed in `examples.json` (ARTIFACT_SCOPES => facts); an example that prints a timestamp/random value makes that artifact vary (python_examples.py:558-559).
- Live network readings inside hashed facts: link_target and product-page status (see Q4 #4).
- `lang/*` `lru_cache` keyed by path persists for the process; a long-lived process that re-clones the same path at a new revision would read stale exports (CLI processes are short-lived; hazard only for library use).
- `package_manifest._parse_dotnet_manifest` takes `list(repo.rglob("*.csproj"))[:20]` unsorted then a depth-stable sort (:107-111): ties depend on OS directory order; also it ignores the `manifest` the .NET plugin chose and picks the shallowest csproj under `manifest.parent`. `_detect_python_root` takes `pkgs[0]` from unsorted `iterdir()` (package_root.py:41-58; value unused for python today). `_detect_go_package_subpath` scans `rglob("*")` including `vendor`, `internal`, `testdata`, `.git` (package_manifest.py:292).
- Build side effects before extraction: `.NET` examples reference the clone's project directly (net_examples.py:324-330) so `dotnet build` writes `bin/obj` into the clone BEFORE `surface_facts` runs; the vendored collector does not exclude `obj`/`bin` (tree_helpers.py:462-470). `pip install <clone>` builds in-tree (creates `build/`, `*.egg-info`). Mostly harmless today (generated C# has no public types; python surface uses git-tracked dirs) but extraction order is not hermetic.
- Probe records: `registry_facts` of ts/go/java/net/rust/cpp build `ProbeRecord(status=None, elapsed_ms=0, outcome=<polarity>)` (e.g. typescript.py:421-429), so the "status/timing/volatile reading" that RC7 says belongs there is lost, and outcome vocabulary differs from python's `FOUND/NOT_FOUND/UNREACHABLE` (core/package_registry.py:49-63).
- Dependency fact IDs inconsistent: python IDs embed the full requirement string (`dependency:numpy-1.20`), every other ecosystem keys by name with version in the value, so a python version-bound bump is remove+add, not "altered".

### Dead code
- `typescript_barrel.reexported_names` (:265).
- Vendored: `package_registries/{cargo,npm,nuget,pypi}.search`, `apply_debounce`, `is_corroborated_match`, `REQUIRED_CONSECUTIVE_CHECKS`, `publication_probe.format_publication_line`, `lang/*.parse_doc`, `lang/typescript.export_groups`, `lang/csharp.export_surface`, `lang/{python}` and ~1,000 lines of Python branches in `api_surface.py` (parity-test only), vendored `pypi.check_published` (python uses `python_registry.py`; `REGISTRY_TYPES["python"]` is consulted only for the "registry-less" check in extract.py:92).
- FactKind `capability` (no producer).
- Duplicated Python license authority: `package:license` from python.py:324 and the license `declared` value from vendored `_parse_python_manifest` via `read_identity` (extract.py:257) are two readers of the same field.

### Duplicated authority / structure
- Six near-identical `registry_facts` bodies (ts, go, java, net, rust, cpp) and seven copies each of `_fresh_workspace`, `_clip`, `_blocked`, `_scrub` across `*_examples.py` (python_examples.py:54-56 admits the duplication is deliberate under §7.4). All should be in core.
- Three ecosystem tables (platforms, `SPECS`, `REGISTRY_TYPES`) + `OBSERVERS`; python/net specs in core, others in plugins.
- Two `RegistryObservation` classes (core/package_registry.py:19, surface/registry.py:52).
- Platform plugin `python_format_declarations.py` encodes Aspose-only conventions (`FileFormat.py`, `register_plugin`) in a "generic" Python plugin.

### Hidden fallbacks
- `platforms/registry.py:65-70`: `except ImportError: return None` turns any ImportError raised INSIDE a plugin module (e.g. missing `httpx`/`tenacity`/tree-sitter wheel) into "no platform plugin registered for ecosystem ... (known: ...)" and silently drops it from `known_ecosystems()`. (Reproduced symptom: in this shell importing python.py fails with `ModuleNotFoundError: tenacity`; through the registry that would read as an unknown ecosystem.)
- TypeScript entry point: if no declared specifier resolves to a barrel, falls back to the shallowest `index.ts` that re-exports, else to a non-barrel declared file (typescript_barrel.py:150-178); if none, `surface_facts` returns `[]` silently (typescript.py:354-355).
- Python build failure -> examples run against the source tree with `build_verified=False` (python_examples.py:471-515), by design but yields EXECUTED receipts for a non-installable package; interpreter choice by `requires-python` falls to the presenter's own Python if the specifier is unparsable (:388-389).
- `_source_build_fact` (evidence/facts/extract.py) rewrites a CONTRADICTED/UNRESOLVED install command into a source-install SUPPORTED fact; cpp's UNRESOLVED install is likewise promoted.
- C++: `-fsyntax-only` proves headers; EXECUTED receipts set `build_verified` only if CMake built (cpp_examples.py:549-557).
- C++/CMake regexes run on raw text including `#` comments; `library_target`/`cxx_standard`/`find_package` match commented-out lines (cpp.py:108-127).
- TS `_sources_for` uses `str.lstrip("./")` (character-set strip, not prefix) (typescript_barrel.py:119,122-123).
- Layering: `examples/selection.py` imports `evidence.facts.inherited` (downstream), while `evidence/facts/extract.py` imports `extractors`.
