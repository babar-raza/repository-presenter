# lane-d decision log (append-only; entries in RESEARCH_AND_GUIDELINES.md section 31 shape; the owner merges)

Lane: `lane-d` (project/lanes/lane-d.yaml). Prompt: project/loop-prompt-lane.md.

The lane appends here in `RESEARCH_AND_GUIDELINES.md` §31's shape — date, item, decision,
alternative rejected, evidence, reversal path. The owner reviews asynchronously and merges what
belongs in §31. A `PROPOSAL` names a defect whose cause is outside lane D's owned paths
(`composition/`, `review/`, `repair/`, the renderer, `prompts/`, `core/`, the shared façades); the
primary lands those through G4-W17 in arrival order (§28.12, "Lanes C and D", owner 2026-09-06
08:00). Lane D never patches around one.

## 2026-09-06 — G4-W15, Go spec and cohort

### D1 The Go ecosystem spec is declared by the plugin module, not added to a shared file

**Decision.** `platforms/go.py` declares `GO = EcosystemSpec(...)` and registers it with
`SPECS.setdefault(GO.ecosystem, GO)` at import, exactly as lane B's `platforms/typescript.py`
declares `TYPESCRIPT` (branch `lane-b/G4-W14`, PR #3). §29.6 E3 says adding an ecosystem is one
spec, one verifier and one negative-control test; the registry resolves a plugin by module name
and `plugin_for` runs before any stage asks `spec_for` for the vocabulary, so the registration
needs no list and no edit to `core/ecosystems.py`.

**Alternative rejected.** Adding `GO` to `core/ecosystems.py`'s `SPECS` literal. `core/` is a
path a lane may not touch, three lanes would append at the same place, and the rebase rule
("a conflict in a file you do not own takes origin's version") would silently delete the spec and
leave `spec_for("go")` raising `ConfigError` at the renderer.

**Evidence.** `tests/.../test_go.py::test_the_plugin_is_discovered_by_module_name_and_registers_its_spec`;
`known_ecosystems() == ("go", "net", "python")` with no registration line anywhere.

**Reversal path.** Move the four constants into `core/ecosystems.py` and delete the `setdefault`;
nothing else reads the spec by any other route.

### D2 A Go file the go command will not let a consumer import is not part of the surface

**Decision.** `go.py` drops every symbol the shared extractor returns from a `_test.go` file, from
a path under `internal/`, `testdata/` or `vendor/`, and from any directory whose name starts with
`_` or `.` — Go's own build rules, not a naming convention.

**Alternative rejected.** Taking the extractor's output whole. Measured 2026-09-06 on
Aspose.PDF for Go: 3,056 symbols before the filter, 1,467 after — 1,589 of them declared in
`_test.go` files (`table_test.go` alone contributes 68) and one under `_examples/`. Publishing a
package's test helpers in an API reference the contract calls complete would be worse than
publishing nothing.

**Evidence.** `test_go.py::test_an_unimportable_file_is_no_part_of_the_surface` and
`::test_surface_facts_come_from_the_shared_extractor_and_skip_test_files`; the two preflight
records under `evidence/build/lanes/lane-d/G4-W15.json`.

**Reversal path.** Delete `go.importable` and the guard in `surface_facts`.

### D3 The imports a README fragment needs are asked of the compiler, never guessed

**Decision.** `go_examples.py` completes a fence into a package (a whole file as written, a run of
declarations under a `package main` clause, loose statements inside `func main`), builds it once
with no import block, and reads the missing packages off the compiler's own
`undefined: <name>` diagnostics: a name the snippet uses as a qualifier and that the
standard-library table knows becomes that import, the single remaining qualifier is the product at
the import path the manifest declares, and anything else leaves the example `NOT_VERIFIED`.

**Alternative rejected.** Deriving imports from the snippet's text. A regular expression cannot
separate a package qualifier from a local variable — `wb.Save(…)`, `ws.Cells()` and
`cells_foss.NewWorkbook()` are the same shape — and a wrong import compiles the example against a
package its author did not mean. The compiler already knows which names are undefined, and a name
the snippet declares itself never appears in that list.

**Evidence.** Measured 2026-09-06 across the cohort's 16 Go fences: Cells 8 EXECUTED, 1 FAILED
(`undefined: generateSmallPNG`, a helper the README never defines — a real defect in the example),
1 NOT_VERIFIED (an import-only fence); PDF 5 EXECUTED, 1 NOT_VERIFIED (the signing example aliases
`crypto/rand` as `cryptorand` and names six packages this verifier will not guess between).

**Reversal path.** `resolve_imports` and `completed_source` are pure functions with their own
tests; deleting the second build reduces the verifier to whole files only.

### D4 An import-only fence is not verified, never contradicted

**Decision.** A fence whose entire content is an import declaration gets `NOT_VERIFIED` with
"there is nothing to compile". Aspose.Cells for Go's README opens with a lone
`import cells_foss "…/aspose/cells_foss"`.

**Alternative rejected.** Building it anyway. Wrapped in `func main` it is
`syntax error: unexpected keyword import`; declared at file scope it is an unused import. Either
way `go build` fails and the fact would read CONTRADICTED — "we checked and the example is false"
about a statement that is true.

**Evidence.** `test_go_examples.py::test_an_import_only_fence_has_nothing_to_compile`; the first
Cells fence moved from FAILED to NOT_VERIFIED when the guard landed.

### D5 A declaration is only top-level when the snippet starts with one

**Decision.** `completed_source` matches `func`/`type` at the snippet's first token, never
anywhere inside it.

**Alternative rejected.** Searching the snippet for a declaration. A README writes a function body
unindented, so Aspose.PDF for Go's encryption and signing examples carry `var buf bytes.Buffer` at
column 0 in the middle of a run of statements; searching called both of them top-level
declarations and every statement above became
`syntax error: non-declaration statement outside function body` — two of six fences reported
FAILED for a defect the examples do not have.

**Evidence.** `test_go_examples.py::test_an_unindented_declaration_inside_a_body_is_not_a_top_level_declaration`;
PDF Go went from 4 EXECUTED / 2 FAILED to 5 EXECUTED / 1 NOT_VERIFIED with no other change.

### PROPOSAL P1 — the shared extractor's kind table does not know Go's node types

**File.** `src/repository_presenter/components/readme/extractors/surface/extractor.py`, `_KINDS`.

**Defect.** The vendored engine names a Go type `type_spec` and a Go top-level function by the
literal string `function`; neither is a key in `_KINDS`, so `symbol_kind()` returns `unknown` for
every one of them. The renderer's Core API table lists `class` and `enum` only
(`composition/renderer.py::_api_reference`), so a Go candidate's API Reference would say
"The verified public surface has 0 types" and render an empty table, while `_public_type_count`
and `validation/registry.py`'s row-14 check both see nothing. §29.7 control 4 says every raw node
type maps to the enum.

**Fix.** `"type_spec": "class"` and `"type_declaration": "class"`, and `"function": "function"`
(the engine's own literal, set in `api_surface.py` for top-level functions of every language, not
a tree-sitter node type).

**Repositories and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` at
`9f0a4033b59e9127afec7662ec9079b500af8032` — 109 public symbols, 30 of them `unknown`, 0 `class`.
`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at `2306eeb06216be4d9cb663adcb85155594572c11` — 1,467
public symbols, 352 `unknown`, 0 `class`. The lane passes the façade's kind through unchanged
(as `net.py` does) rather than deciding Go's kinds behind the façade's back.

### PROPOSAL P2 — the shared registry façade never probes the Go module proxy

**File.** `src/repository_presenter/components/readme/extractors/surface/registry.py`,
`REGISTRY_TYPES` and `observe`.

**Defect.** Two of them, in one call path. `REGISTRY_TYPES["go"]` is `"goproxy"`, but the vendored
probe's adapter table (`_vendor/aspose_extraction/publication_probe.py::_ADAPTERS`) is keyed
`"go_modules"`, so `probe_publication` takes its "unknown registry" branch and returns
`published: None, ambiguous: True` without a request. And when that key is corrected the Go
adapter reads `candidate["module_path"]` (`package_registries/go.py::check_published`) while
`observe` passes `{"name": package_name}` — an uncaught `KeyError` that would take the facts stage
down. Both must land together.

**Fix.** `"go": "go_modules"`, and `observe` supplies `module_path` alongside `name` for the Go
registry (the adapter already escapes the module path's upper-case letters for the proxy, which is
what Cells Go's `/v26` path needs).

**Repositories and finding.** Both Go repositories. `install_command:go` stays `UNRESOLVED` with
the evidence "package registry: goproxy could not be read", and BC-02 (`_check_install`) fails
every install fact whose polarity is not `SUPPORTED` — so no Go candidate can pass validation at
all, whatever else is right. The census records that the proxy does list versions for both
modules, so the honest reading is available and simply is not asked for.

### PROPOSAL P3 — the Installation section offers `pip install .` to every ecosystem

**File.** `src/repository_presenter/components/readme/composition/renderer.py::_installation`.

**Defect.** When a repository has any executed example the renderer appends a hard-coded
`git clone … && cd … && pip install .` block. `EcosystemSpec`'s own docstring names a
`source_install` template ("``version_badge`` and ``source_install`` are templates over
``{package}``…") but the dataclass has no such field, so §29.6 E4's rule — Installation reads from
the spec — is unmet for every non-Python ecosystem.

**Fix.** Add `source_install` to `EcosystemSpec` and render it; Go's is
`git clone https://github.com/{repository}.git` then `cd {name}` then `go build ./...`, and a spec
that declares none renders no block.

**Repositories and finding.** Both Go repositories reach this branch — Cells has 8 executed
examples and PDF 5 — and would tell a Go reader to install the clone with pip.

### PROPOSAL P4 — the verify-install block recognises only Python-shaped imports

**File.** `src/repository_presenter/components/readme/composition/renderer.py`, `_IMPORT`.

**Defect.** `_IMPORT = r"(?m)^\s*(?:import|from)\s+{module}\b"` requires the module to follow the
keyword bare. Go writes `import cells_foss "github.com/…/cells_foss"` (quoted, usually aliased,
usually inside a parenthesised block), so no import path ever matches and
`spec.verify_command` — `go list -m {module}` — never renders, although eight of Cells Go's
examples import exactly that path. C# `using X;` is in the same position.

**Fix.** Match the module inside the ecosystem's own import syntax; the spec is the place that
knowledge belongs (§29.6 E4).

**Repositories and finding.** Both Go repositories: `import_path` is SUPPORTED and cited by
executed examples, and the Verify-the-install block is still absent.

## 2026-09-06 — G4-W16, Rust spec and cohort

### D6 The Rust floor the renderer reads is the edition, because that is what the manifest declares

**Decision.** `platforms/rust.py` emits `package:rust_edition` from `Cargo.toml`'s `edition`
always, and `package:rust_version` from the optional `rust-version` when a crate declares one;
`RUST.floor_fact_id` points at the edition. The Dependencies section renders "Requires Rust
edition `2021` (`edition` in `Cargo.toml`)".

**Alternative rejected.** Pointing the spec at `package:rust_version`, the way the .NET spec
points at `package:target_framework`. Aspose.Cells for Rust declares no `rust-version` at all
(measured 2026-09-06: `[package]` carries name, version, edition, license, description, keywords
and categories only), so the Native and System Requirements subsection would have told a reader
nothing about which compiler the crate needs. Rejected too: reporting the edition under the label
"Rust", which renders "Requires Rust `2021`" - true of nothing, since 2021 is an edition and not
a compiler version. §29.12 keeps the platform's own vocabulary rather than flattening it.

**Evidence.** `test_rust.py::test_the_declared_floor_is_the_edition_when_no_compiler_version_is_declared`,
which asserts both facts once `rust-version` is added and only the edition before.

**Reversal path.** Move `floor_fact_id` to `package:rust_version`; both facts are already emitted.

### D7 The surface is read from the crate's source root, never from the manifest's directory

**Decision.** `surface_facts` passes `root / identity.package_root` - the `src/` the vendored
reader resolves (§29.12) - to the shared extractor, not `manifest.parent`.

**Alternative rejected.** The manifest's own directory, which is what the Go plugin passes because
a Go module's package root *is* the module directory. The vendored engine derives a Rust symbol's
module path from its file's location relative to the root it is given, so the manifest directory
made every symbol `src::widget::Widget` - `src` is not a Rust module and no consumer can write
that path. Measured on a two-module fixture 2026-09-06; the defect is invisible on Cells for Rust
itself, whose sources sit under `src/Aspose.Cells_FOSS/`, a segment that is not a valid Rust
identifier, so the engine already falls back to the bare crate-root name for every type.

**Evidence.** `test_rust.py::test_surface_facts_come_from_the_shared_extractor_and_skip_separate_targets`
asserts `widget.Widget` and that no value begins with `src`.

**Reversal path.** Pass `manifest.parent`; nothing else reads the package root.

### D8 A fence that opens on a binding it never declares is an excerpt, not a falsehood

**Decision.** `rust_examples.py` wraps a fence that declares no `fn main` in one
`fn main() -> Result<(), Box<dyn Error>>` with `#![allow(unused)]` and a glob `use <crate>::*`,
checks it as a Cargo example target, and reports `NOT_VERIFIED` when *every* error the compiler
raised is `E0425: cannot find value`. Any other error - a type the crate does not export, a method
that does not exist - is `FAILED`.

**Alternative rejected.** Reporting those fences `FAILED`, which is what the first cohort run did:
six of Aspose.Cells for Rust's seven Rust fences came back CONTRADICTED on `sheet`, `workbook`,
`valid_path` and `links_sheet` - bindings the README's own prose establishes in the section above
each fence, under a heading that says the complete programs are in `samples/`. "We checked and the
example is false" about an excerpt would be the worst kind of wrong. Also rejected: synthesizing
the missing bindings, which would be writing the example rather than checking it.

**Evidence.** Measured 2026-09-06 across the seven fences: 1 EXECUTED (the Quick Start, a whole
`fn main` program, compiled against the crate at `1a6004af`), 6 NOT_VERIFIED, 0 FAILED. The glob
import is what makes the distinction meaningful - it resolves `LoadOptions`, `ChartType`,
`CellArea`, `FormatConditionType`, `ValidationType`, `TableStyleType` and `TotalsCalculation`
from the crate root, leaving the unbound values as the only diagnostic.

**Reversal path.** `completed_source` and `unbound_values` are pure functions with their own
tests; deleting the `unbound_values` branch restores FAILED.

### D9 Cargo's closing summary is not a diagnostic

**Decision.** `unbound_values` drops `error: could not compile … due to N previous errors` and
`error: aborting due to …` before deciding whether every error was `E0425`.

**Alternative rejected.** Counting every line that starts with `error`. Cargo restates the failure
after the diagnostics with no error code, so a pure excerpt read as "one E0425 and one uncoded
error" and every excerpt in the cohort would have been reported FAILED - the exact defect D8
exists to prevent, reintroduced by the parser. Caught against the first run's captured output
before the second run.

**Evidence.** `test_rust_examples.py::test_cargos_closing_summary_is_not_counted_as_a_second_error`,
built from the literal output of `cargo check --example rp_example_006` on this crate.

### D10 The crate is checked once, in a copy, and every fence after it is checked `--locked`

**Decision.** The verifier copies the crate into one run workspace (without `.git` or `target`),
runs `cargo check` there once, then writes each fence into that copy's `examples/` directory and
runs `cargo check --locked --example <name>`. `--locked` is used on the crate's own check only
when the repository ships a `Cargo.lock`.

**Alternative rejected.** The legacy `example_verifiers/rust.py`'s shape, which writes examples
into the checkout itself and passes `--locked` only when a lock file is already there. Aspose.Cells
for Rust ships no `Cargo.lock`, so `--locked` on the first check fails outright ("the lock file
needs to be updated but --locked was passed"); and writing into the pinned clone would put build
output inside the snapshot the transaction verifies. The copy costs 259 files and buys both.
The cost that mattered is the toolchain's: a cold `cargo check` with a disposable `CARGO_HOME`
resolves seven requirements and compiles two native build scripts in 253 seconds, four seconds
under `core.execution`'s 300-second ceiling, while each fence after it returns in about half a
second against the shared target directory. One check per composition is the only affordable
shape.

**Evidence.** `test_rust_examples.py::test_every_example_is_checked_against_the_lock_the_crate_check_resolved`
and `::test_a_crate_that_does_not_check_condemns_no_example`; the timings in
`evidence/build/lanes/lane-d/G4-W16.json`.

**Reversal path.** Drop the copy and run in the clone; `--locked` is one flag.

### D11 `RUSTUP_HOME` is named explicitly, because the disposable profile moves the real one

**Decision.** The verifier resolves `cargo` by `which`, then by the `cargo` key of the
machine-local toolchain registry, and sets `RUSTUP_HOME` in the subprocess environment from the
ambient value, then the registry's `rustup_home`, then the home beside the proxy's own
`cargo-home`. Nothing is added to the user's `PATH`.

**Alternative rejected.** Letting the proxy find its own home. `core.execution.profile_environment`
redirects `USERPROFILE` and `HOME` into the run directory, which is exactly where `.rustup` is
*not*, so every check would have failed with "no default toolchain configured" - a toolchain
failure reported as an example that does not compile.

**Evidence.** `test_rust_examples.py::test_the_rustup_home_is_named_explicitly_because_the_profile_moves_the_real_one`
and `::test_the_toolchain_registry_resolves_a_tool_that_is_not_on_path`; the resolved paths and
versions in the receipt (rustup 1.29.1, cargo 1.98.1, rustc 1.98.1, stable-x86_64-pc-windows-msvc).

### PROPOSAL P5 — G4-W17 item (0) corroborated by Rust, with one refinement its fix needs

**File.** `src/repository_presenter/components/readme/validation/registry.py`, `_check_install`,
and `composition/renderer.py::_installation` alongside it.

**Not a new arrival.** The reviewer recorded this class as G4-W17 item (0) at 10:07 on 2026-09-06
("BC-02's publication-only SUPPORTED path is the portfolio's highest-leverage blocker"), from lane
B's four C++ repositories and the unpublished Python and TypeScript ones. Rust is the fifth
ecosystem to hit it, on the only Rust repository in the portfolio, and this entry exists to give
item (0) that repository's exact reading and one thing its fix has to decide.

**Defect, as Rust meets it.** `_check_install` fails every install fact whose polarity is not
`SUPPORTED`, at `EXTRACTING`. There is no honest way out from inside a plugin: emitting no install
fact fails the same check's first clause ("no install command fact"), and an install fact the
registry conclusively contradicts fails its second. Meanwhile `README_CONTRACT.md` §2 row 8 says in
as many words: "State plainly when the package-registry observation shows the package is not yet
published, rather than presenting an unqualified install command the registry itself contradicts",
and `renderer.py::_installation` already implements exactly that - its second branch renders "The
package `X` is not yet published on crates.io (…)" and no `bash` fence. That branch is unreachable
today, because no candidate carrying a non-SUPPORTED install fact ever gets composed.

**The refinement item (0) needs.** Item (0) admits "a verified source build (clone, configure,
build or compile succeeding)" as an alternate SUPPORTED path. Rust has one - `cargo check` on the
crate at this revision, which the example verifier already runs and records. But making
`install_command:cargo` SUPPORTED on that evidence would render `_installation`'s *first* branch:
"Install the published package from crates.io (`aspose-cells-foss-rust`, version 26.7.0)" followed
by `cargo add aspose-cells-foss-rust` - a command that fails for the reader, on a registry that
does not carry the crate. So the source-build path must support a *source* install fact (the git
or clone-and-build form), not the registry command, and the renderer must choose its branch from
which path supported the fact rather than from polarity alone. Otherwise item (0) converts a
disposition into a sealed README that tells a Rust reader to install a crate that is not there.

**Repositories and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at
`1a6004af47b1ef15385f9d36d381a8172428cc7e`. `install_command:cargo` = `cargo add
aspose-cells-foss-rust`, polarity `CONTRADICTED`, evidence
`https://crates.io/api/v1/crates/aspose-cells-foss-rust` → "package registry: distribution not
found on cargo" (HTTP 404, conclusive, method `crates-io-api`). The census records the same
reading ("crates.io not found"), and the repository's own upstream-issues digest names "Crate is
not yet published to crates.io" as a known, deliberate state. Everything else about the candidate
is complete: 2,224 facts, no required contract row without evidence, 2,084 public symbols of which
178 are types and 35 enums, 7 requirements with versions, and the Quick Start example compiled
against the crate at this revision.

### Observations that are not proposals

- **The shared kind table already knows Rust.** `_KINDS` carries `struct_item`, `enum_item`,
  `trait_item`, `impl_item` and `function_item`, so 2,078 of the crate's 2,084 public symbols
  carry a real kind and the Core API table would render. The 6 that come back `unknown` are
  top-level free functions the vendored engine labels with the literal string `function`
  (`parse_a1_range`, `parse_cell_ref_a1`, `default`, `fmt`, `eq`, `hash`) - the same missing key
  G4-W17 item (9) already carries for Go. Rust corroborates half of that item and needs nothing
  added to it.
- **The registry façade already reaches crates.io.** `REGISTRY_TYPES["rust"]` is `"cargo"`, the
  vendored adapter table is keyed `"cargo"`, and `cargo.check_published` reads
  `candidate["name"]` - exactly what `observe` passes. Rust has none of the Go mismatch that
  G4-W17 item (8) fixes; the probe returned a conclusive reading on the first attempt.
- **G4-W17 items (10) and (11) bite Rust exactly as they bite Go.** The Installation section
  would append `git clone … && cd … && pip install .` to a Rust README (the crate has an executed
  example), and `_IMPORT` never matches `use aspose_cells_foss_rust::…`, so the Verify-the-install
  block is absent. One thing to add when (11) lands: the block must be skipped when a spec
  declares no `verify_command`, or an ecosystem without an idiomatic verify line renders an empty
  `bash` fence. Rust's own `verify_command` is `cargo check`, a template with no `{module}`
  placeholder, so it is safe either way.
- **`https://crates.io/` is reported MISSING and the reading is literally right.** The link prober
  gets HTTP 404 from crates.io's root by HEAD *and* by GET, with the project's User-Agent and with
  a browser's (measured 2026-09-06): the site is client-routed and its server does not render `/`.
  The fact is CONTRADICTED, no composed README would render the link, and no check fails on a link
  the document does not carry. Recorded rather than proposed: distinguishing this from a genuinely
  dead URL needs a rendering client, which is a larger decision than a lane should take.

## 2026-09-06 — G4-W16 re-run, after G4-W17 items (0), (5) and (11)

G4-W16 was accepted at its box with one disposition: `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`,
`BLOCKED_SHARED_CODE`, class `BC02_PUBLICATION_ONLY_SUPPORTED_PATH`, whose resume predicate was
"G4-W17 item (0) is landed on main with PROPOSAL P5's refinement … then rerun `present`". Item (0)
landed at 12:30 and items (5) and (11) together at 13:29 (`RESEARCH_AND_GUIDELINES.md` §31). Both
landed the *mechanism* only and left one spec field each to the ecosystem — and an ecosystem's spec
lives in a lane-owned `platforms/<ecosystem>.py`. So the re-run is these two decisions in lane D's
own paths, then the composition; no shared file is touched.

### D12 Rust's source-checkout install is the repository's own three commands, measured

**Decision.** `RUST.source_install` is
`git clone https://github.com/{repository}.git` / `cd {name}` / `cargo build`, with
`source_install_lead` "build the clone with cargo build". `evidence/facts/extract.py::_source_build_fact`
(G4-W17 item 0) promotes `install_command:cargo` from `CONTRADICTED` to `SUPPORTED` with
`install_kind: source` only for an ecosystem whose spec names such a command, and rewrites the
fact's value to it — so the promotion is exactly what PROPOSAL P5 asked for: a *source* install
fact, never `cargo add aspose-cells-foss-rust` against a registry that answers 404.

**Alternative rejected.** `cargo add --git https://github.com/{repository}.git`, the idiomatic way
to consume an unpublished crate. It is one line and it is what a reader wants, but it is not a
command this lane has run against this revision, and the renderer's own sentence asserts "verified
against this revision"; a guessed syntax is worse than an honest absence (loop-prompt's standard,
and G4-W17 item 5's own reasoning). Also rejected: `cargo check`, literally what the example
verifier runs — exactly measured, but not an install: it produces no artifact and no reader would
call it one. Rather than choose between "measured" and "idiomatic", `cargo build` was *made*
measured (below). Also rejected: leaving `source_install` empty, which is what `main` inherited —
honest, but it leaves `_check_install` failing this candidate closed forever, which is the
disposition this re-run exists to clear.

**Evidence.** The upstream README names these three commands itself ("To build the library directly
from a clone", `README.md` lines 127–131 at `1a6004af`), so the rendered block is the repository's
own instruction rather than one invented for it. Run against a clone of that revision with the
lane's toolchain (`cargo 1.98.1`, `RUSTUP_HOME` and `CARGO_HOME` under
`C:/tools/rp-toolchains/rustup`, nothing on `PATH`): `cargo build` exits 0,
`Finished dev profile [unoptimized + debuginfo] target(s) in 38.93s`.
`test_rust.py::test_the_source_checkout_commands_are_cargos_own_and_never_pips` pins the rendering,
and pins that it is neither `pip install .` (G4-W17 item 10's defect) nor `cargo add`.

**Reversal path.** Clear `source_install` and `source_install_lead` on `RUST`; `_source_build_fact`
returns the fact untouched and the candidate returns to its
`BC02_PUBLICATION_ONLY_SUPPORTED_PATH` disposition with nothing else changed.

### D13 Rust's Verify-the-install match is `use`, and it is the spec's own field

**Decision.** `RUST.import_pattern` is `(?m)^\s*(?:pub\s+)?(?:use|extern\s+crate)\s+{module}\b`.
G4-W17 items (5) and (11) removed the renderer's module-level `_IMPORT` constant and made the
pattern `EcosystemSpec.import_pattern`, defaulting to Python's own shape so no sealed byte moved;
that item's entry says each ecosystem's pattern "is each lane's own field to set in its own
`platforms/<ecosystem>.py` spec construction". This is Rust's, and Rust is the first ecosystem to
set one.

**Alternative rejected.** The bare `(?m)^\s*use\s+{module}\b`. A fence may open on a re-export
(`pub use …`) or on the 2015-edition `extern crate …`, and both are the same claim: the example
names this crate. Rejected too: matching `{module}` anywhere in the fence, which would count
`aspose_cells_foss_rust::Workbook::new()` in the body of a snippet that never imports the crate,
and a `[dependencies]` entry in a `toml` fence.

**Evidence.** `test_rust.py::test_the_import_pattern_is_rusts_use_and_not_pythons_import`, built on
this crate's own Quick Start opening line (`use aspose_cells_foss_rust::{CellValue, Workbook};`,
`README.md` line 155 at `1a6004af`): the pattern matches it, the inherited Python-shaped default
does not — the bug reproduced directly — `pub use` and `extern crate` match, and
`aspose_cells_foss_rust_extra` and a bare call expression do not.

**Reversal path.** Delete the field from `RUST`; the spec falls back to the shared default and the
Verify-the-install block disappears again, changing nothing else.

### Outcome of the re-run — `BC02_PUBLICATION_ONLY_SUPPORTED_PATH` is cleared; not sealed

**Measured 2026-09-06 13:50–14:03** (`repository-presenter present --repo
aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`, worktree `C:\w\d16b` off `origin/main` at `4e1157f`,
cargo 1.98.1 resolved by absolute path with `RUSTUP_HOME` in the subprocess environment only).
The candidate composed end to end for the first time: 2,224 facts, 7 example candidates (1
EXECUTED, 6 NOT_VERIFIED, 0 FAILED), 81 units dispositioned, a 16-of-18 section plan, 134 content
units across 8 sections, 18 provider calls, a 167-visible-line README. **`BC-02` PASS** —
"Install command verified against the manifest and the package-registry observation" — together
with `BC-01`, `BC-03`, `BC-04`, `BC-05`, `BC-06` and `BC-09`. The disposition's resume predicate is
therefore met and its failure class is closed: the Installation section renders

> `aspose-cells-foss-rust` is not yet published on crates.io; build it from a source checkout
> instead, verified against this revision:

followed by the D12 fence, then "Verify the install:" and `cargo check` (D13 — the first
Verify-the-install block any Rust candidate has rendered), and the badge row carries only License
and Contributors, no crates.io version badge.

**Not sealed.** Two blocking checks failed, both `COMPOSING`, both recorded `unrepairable`
("no failing check names an LLM-owned section"), neither in a path lane D owns. They are
PROPOSAL P6 and PROPOSAL P7 below and they become the repository's new disposition; the
`BC02_PUBLICATION_ONLY_SUPPORTED_PATH` class is not re-raised and should not be reported as
still blocking.

### PROPOSAL P6 — the narration guard reads a public symbol's own name as internal narration

**File.** `src/repository_presenter/components/readme/validation/registry.py`, the module constant
`_NARRATION` (line 249) and `_check_structure`'s loop over it (line 849).

**Defect.** `_check_structure` lowercases the README's prose outside fences and fails `BC-07` when
any `_NARRATION` phrase appears as a *substring* anywhere in it. One of the nine phrases is the
bare word `"validator"`. Aspose.Cells for Rust exports a public type named `WorkbookValidator`
(and `WorkbookValidator.validate_for_save`), so `README_CONTRACT.md` §2 row 14's API Reference
table renders exactly one line containing it —
`| `WorkbookValidator` | WorkbookValidator performs validation checks on a workbook and collects
any issues found. |` — and the check reads the repository's own API as machinery narration. There
is no composition that can pass: the only way to remove the string is to drop a `pub` type from a
required contract row, which is a lie about the surface, and the repair loop declined the finding
anyway. The guard's intent (a sentence about *our* validator leaking into a reader-facing
document) is right; matching a substring with no word boundary and no exemption for a value that
is itself a `public_symbol` fact is what is wrong.

**Fix, as this lane reads it.** Match `_NARRATION` on word boundaries, and exempt an occurrence
that is part of a `SUPPORTED` `public_symbol` fact value (the candidate already carries them all)
or that sits inside a code span. `"validator"` and `"fact id"` are the two phrases short enough to
collide with real API vocabulary; the other seven are multi-word and unlikely to.

**Corroborates.** Lane C's PROPOSAL G (2026-09-06, `RESEARCH_LANE_C.md`) reports the *other* cause
of the same check firing — the authoring job writing `fact id` into prose — and reports the same
`targeted_repair` behaviour. P6 is not that: nothing the model wrote is at fault here, so P6's fix
is needed even after G's prompt change lands.

**Repository and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at
`1a6004af47b1ef15385f9d36d381a8172428cc7e`;
`validation: BC-07 failed at COMPOSING: internal narration 'validator'; no repair could act on it`.

### PROPOSAL P7 — a VERIFIED_REWRITE that drops a command fails a check no repair is offered

**Files.** `prompts/section_authoring.yaml` (the authoring job for an owner-`M` section) and
`src/repository_presenter/components/readme/repair/` — the routing that turned both findings into
`unrepairable`.

**Defect.** `_check_protected` (BC-08) protects every backticked span of an inherited unit that
matches `_COMMAND` once that unit's disposition places it. `inherited_unit:079.paragraph`, the
upstream CI paragraph, names `cargo bench` and `cargo doc --no-deps --open`; reconciliation
dispositioned it `VERIFIED_REWRITE` into `development_testing` (contract row 17, owner `M`), and
the authored section kept eight cargo commands but not those two. The check is right — the
rewrite lost content the reader had — but nothing acts on it: `repairs.json` records both
findings as `outcome: unrepairable`, `reason: "no failing check names an LLM-owned section"`,
because `_check_protected`'s `Failure` carries `section_id: None` even though the disposition it
reads names `destination_section: development_testing`, an owner-`M` row the repair loop is
allowed to re-author.

**Fix, as this lane reads it.** Two independent halves. (1) A protected-content failure carries
the `destination_section` of the disposition that placed the unit, so the repair loop can target
the section that dropped the command. (2) The authoring prompt states that when a unit is placed
by `VERIFIED_REWRITE`, every command the unit names is carried into the authored text — the same
class of instruction the section already gets for identifiers.

**Repository and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at
`1a6004af47b1ef15385f9d36d381a8172428cc7e`; `BC-08` twice —
`inherited_unit:079.paragraph: VERIFIED_REWRITE keeps the command 'cargo bench' but the candidate
does not render it`, and the same for `'cargo doc --no-deps --open'`.

### The disposition this re-run leaves

`aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at `1a6004af47b1ef15385f9d36d381a8172428cc7e`,
`BLOCKED_SHARED_CODE`, failure class `BC07_PUBLIC_SYMBOL_READ_AS_NARRATION` with
`BC08_REWRITE_DROPS_A_PROTECTED_COMMAND` beside it. Resume predicate: PROPOSAL P6 landed on `main`
(P7 with it, or the candidate will seal on the next check instead), then rerun
`repository-presenter present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` from a fresh
lane-d branch. Everything upstream of validation is now proven for this repository, so the next
run is a composition and a seal, not an investigation.
