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

## 2026-09-06 — G4-W15 re-run, after G4-W17 items (8) and (9)

G4-W15 was accepted at its box with two dispositions — `aspose-cells-foss/Aspose.Cells-FOSS-for-Go`
and `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`, both `BLOCKED_SHARED_CODE`, class
`GO_REGISTRY_NEVER_PROBED_SO_BC02_FAILS` — whose resume predicate was "PROPOSAL P1 and PROPOSAL P2
are landed on main (G4-W17); then rerun `present`". Both landed together at 14:46 as arrival items
(8) and (9) (`RESEARCH_AND_GUIDELINES.md` §31; commit `08137a0`, present in this worktree's log).
This is the re-run. Worktree `C:\w\d15b`, detached off `origin/main` at `2b88ea4`, fresh `.venv`
from `C:\Python313`; `go` resolved with `shutil.which("go")` to `C:\Program Files\Go\bin\go.EXE`,
`go1.26.4 windows/amd64`, with `GOPATH`, `GOMODCACHE` and `GOCACHE` under `runs/` only.

### The resume predicate is met and the class is closed, for both repositories

**Measured at the facts stage, no provider call** (`present --facts-only`). Items (8) and (9) each
did exactly what the dispositions said they would:

| | Cells Go | Aspose.PDF Go |
| --- | --- | --- |
| `install_command:go` | `SUPPORTED` | `SUPPORTED` |
| registry evidence | `package registry: found on go_modules`, live probe of `proxy.golang.org/github.com/aspose-cells-foss/!aspose.!cells-!f!o!s!s-for-!go/v26/@v/list` | same, `proxy.golang.org/github.com/aspose-pdf-foss/aspose-pdf-foss-for-go/@v/list` |
| symbol kinds (was: every Go type `unknown`) | `class` 14, `method` 79, `function` 16 — zero unknown | `class` 213, `method` 1,114, `function` 139, `module` 1 — zero unknown |
| supported facts | 228 of 231 (was 227) | 1,619 of 1,620 |

`BC-02` then **PASSED** for Cells Go in both composition rounds below, alongside `BC-01`, `BC-03`
to `BC-09`. `GO_REGISTRY_NEVER_PROBED_SO_BC02_FAILS` is closed and must not be reported as still
blocking either repository. Neither sealed; each is blocked further down the pipeline on a class
that had never been reachable before, because no Go candidate had ever been composed at all.

### D14 Go's Verify-the-install match is the quoted import path, and it is the spec's own field

**Decision.** `GO.import_pattern` is `(?m)^\s*(?:import\s+)?(?:[\w.]+\s+)?"{module}"`.

G4-W17 items (5) and (11) made the renderer's match `EcosystemSpec.import_pattern`, mechanism only,
each ecosystem's pattern its own spec's to set — lane D proposed item (11) from Go (PROPOSAL P4) and
then set the field for Rust first (D13) without ever setting Go's. This sets it.

**Alternative rejected.** The inherited Python-shaped default, kept on the ground that Go's
Verify-the-install block is optional. It is not honest: `README_CONTRACT.md` §2 row 8 asks for the
verify line "when the ecosystem has an idiomatic one", and Go has one. Also rejected: matching the
module path anywhere in the fence, which counts a prose mention or a `go.mod` `require` line as an
import; and `^\s*import\s+"{module}"` alone, which misses both spellings the cohort actually uses.

**Evidence.** Measured against the executed example facts of both repositories at this revision:
the default matches **0 of 8** Cells fences and **0 of 5** Aspose.PDF fences; the pattern above
matches exactly the one fence in each that imports the module — Cells writes the aliased single-line
form `import cells_foss "github.com/…/v26/aspose/cells_foss"` (README line 104), Aspose.PDF the
block form with `pdf "github.com/aspose-pdf-foss/aspose-pdf-foss-for-go"` indented inside
`import ( … )`, the keyword an earlier line entirely.
`test_go.py::test_the_import_pattern_is_gos_quoted_path_and_not_pythons_import` pins both
spellings, reproduces the default's blindness directly, and rejects a prose mention, a bare call,
and a longer path that merely starts with this one. The Installation section of the Cells candidate
now renders the first Verify-the-install block any Go candidate has produced.

**Reversal path.** Delete the field from `GO`; the spec falls back to the shared default, the block
disappears again, and nothing else changes.

### D15 Go's verify command is `go list`, not `go list -m`, because the renderer feeds it a package

**Decision.** `GO.verify_command` becomes `go list {module}` (it was `go list -m {module}`).

**Evidence.** `renderer.py::_installation` fills `{module}` from an `import_path` fact — the module
path *plus the subdirectory the package is declared in* — not from `package:name`. Measured
2026-09-06 in a disposable consumer module (`go mod init`, then `go get`, with `GOPATH`,
`GOMODCACHE` and `GOCACHE` under `runs/`): `go list -m …/v26/aspose/cells_foss` exits **1**,
`module …: not a known dependency`, while `go list …/v26/aspose/cells_foss` exits **0** and prints
the import path back. Aspose.PDF declares its package at the module root, so both forms happen to
work there — `go list` is the one form correct for both. The `-m` spelling had never been rendered
(D14 is why), so this was a latent defect that D14 would have published: a command the README
asserts is verified against this revision, and which fails on the first repository that runs it.
`test_go.py::test_the_verify_command_takes_the_import_path_so_it_is_go_list_not_go_list_m` pins it.

**Alternative rejected.** `go doc {module}`, measured exit 0 and arguably friendlier — it prints the
package synopsis. Rejected because it prints a screen of output for a yes/no question, and because
`go list` echoing the import path back is the narrower claim: this package resolves in this module.
Also rejected: keeping `-m` and feeding the renderer `package:name` instead, which is a renderer
change in a path this lane does not own, for no gain.

**Reversal path.** Restore `go list -m {module}`; with D14 in place the block then renders a command
that fails for Cells, which is why the two decisions land together.

### Outcome — Cells Go: nine of eleven checks pass; blocked at the review, not at BC-02

Two full compositions, `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Go`, the second after
D14 and D15:

- **Run 1, 18:54–19:11** (before D14/D15). 231 facts; 8 of 10 fences executed; 66 units
  dispositioned; plan 16 of 18 sections; 42 content units across 8 sections; README 218 visible
  lines of 497. Validation **pass 9, fail 1, pending 1**: `BC-01`–`BC-09` all PASS, `BC-10`
  `REJECT_PRESENTATION`, `BC-11` never reached. Repair: 0 repaired, 1 unrepairable, 1 re-raised.
- **Run 2, 19:35–19:44** (after D14/D15). The same nine PASS; the Installation section now carries
  `Verify the install:` and `go list …/aspose/cells_foss`. The review's round 1 again returned
  `REJECT_PRESENTATION`; the repair loop **closed both findings** in round 2; and the round-2 review
  was then rejected at the binder — `independent_review: output rejected twice; finding F07: quote
  is not the candidate's text: 'Run `go run main.go` to produce `hello.xlsx`'` — so `BC-10` could
  not be judged at all and the run ended with `BC-10` PENDING. Not sealed.

Both runs' blocking finding was the same one, PROPOSAL P8. The run-2 abort is PROPOSAL P11.

### Outcome — Aspose.PDF Go: blocked at S3, the first stage that reads the surface

`present --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` never reached composition:

> `repository_investigation: output rejected twice; last rejection: unknown fact ID
> public_symbol:savemarkdown; unknown fact ID public_symbol:savehtml; … public_symbol:fontrepository`
> (24 IDs)

Twenty-one of the twenty-four exist — as `public_symbol:document.savehtml`,
`public_symbol:document.split`, `public_symbol:page.drawline` and so on. The model cited them
unqualified because it was never shown the qualified ones. PROPOSAL P10.

### PROPOSAL P8 — a Quick Start lead-in is written about the sibling slot's example

**File.** `src/repository_presenter/components/readme/composition/authoring.py`, `_SECTIONS`
`"quick_start"` (line 131).

**Defect.** The authoring instruction reads "One lead-in sentence per minimal example the renderer
shows next: **the first opens an existing input when the product reads files**, a second builds from
scratch when the plan selected one." That is `README_CONTRACT.md` §2 row 10's *ordering* rule, and it
is handed to the wrong stage: by the time authoring runs, the slots are already bound to specific
examples — `_bound` (line 309) binds `lead_in` to `plan["quick_start_example_id"]` and `lead_in:2`
to `plan["second_quick_start_example_id"]`. Here the plan chose `example:002`, the from-scratch
fence, as the first. The author obeyed the instruction rather than the binding and wrote, above a
fence that calls `NewWorkbook()` and saves `hello.xlsx`:

> To read an existing Excel file and inspect or modify its contents, load the workbook with
> `LoadWorkbook`, access the first worksheet, read a cell value, update it, and save the changes to
> a new file.

and the create-from-scratch sentence above the `LoadWorkbook("input.xlsx")` fence. Each unit cites
its own slot's fact ID, so `BC-04` — which compares fact IDs, not whether the prose is about the
example beside it — passes a document that tells the reader the opposite of what the code does. Only
the independent review caught it, as `F03`, in both runs.

**Fix, as this lane reads it.** Two halves, either of which alone leaves the two stages disagreeing.
(1) The `quick_start` instruction says to describe *this slot's own example*, and stops restating an
ordering rule the author cannot act on. (2) The ordering rule stays with the stage that can honour
it — `presentation_planning`, which chooses `quick_start_example_id` — so a product that reads files
gets the read example bound to the first slot rather than a sentence pretending it is there.

**Repository and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` at
`9f0a4033b59e9127afec7662ec9079b500af8032`; review `F03`, `section_id: quick_start`,
`causal_stage: S7`, raised in two consecutive runs.

**Not one of G4-W17's items (0)–(26).** The nearest is (21), which is also "a stage re-asks
authoring for something planning chose", but it is about an unauthorable limitation in
`scope_limitations`; nothing in the list touches the quick-start slot binding, and no existing item
would fix this.

### PROPOSAL P9 — the repair loop must be told the citations are fixed and only the prose may move

**Files.** `src/repository_presenter/components/readme/repair/` (the `targeted_repair` packet) and
its revised-output check.

**Defect.** Repairing P8 means swapping two sentences while each keeps its slot's fact ID. Round 1's
repair swapped the citations too and was rejected twice —
`revised_output: unit lead_in:2: cites facts outside its slot's planned set (example:002)` — so the
finding was recorded `unrepairable` and re-raised. Round 2 got it right and both findings were
`repaired`. So this is a cost, not a wall: one wasted round and one false `unrepairable` record per
occurrence. The packet never states that a slot's fact set is fixed by the plan and that only the
prose may move between slots.

**Fix, as this lane reads it.** One sentence in the repair packet saying so. Small; recorded because
the false `unrepairable` is what a reader of `repairs.json` would otherwise take for a hard blocker,
exactly as this lane nearly did.

**Repository and finding.** As P8; `repairs.json` attempt `47a1574d268114e2990f8b5b`.

### PROPOSAL P10 — the investigation packet truncates a large public surface alphabetically

**File.** `src/repository_presenter/core/facts.py::bounded_records` (line 145), `SYMBOL_CAP = 150`
(line 142), reached from `investigation/dossier.py` line 38.

**Defect.** `bounded_records` admits public symbols "in document order" until `symbol_cap`. Document
order is the fact ID, which is alphabetical. Aspose.PDF for Go has **1,467** public symbols, so the
packet's 150 are exhausted **inside the letter b** — the last symbol the investigation ever sees is
`public_symbol:bmpdevice.process`. `Document`, the type the entire library is about, and every one
of its methods (`SaveHTML`, `Split`, `Append`, `Optimize`, `Rotate`, `Sign`, `ValidatePDFA`, …) are
invisible to the job. The model reads the inherited README, which describes exactly those
operations, and cites the only IDs it can form — `public_symbol:savehtml` — which do not exist. The
binding check rejects the output, twice, and the candidate dies at S3 with no investigation at all.
The bound is right; the *selection* is what is wrong.

**Fix, as this lane reads it.** Choose the bounded sample by relevance rather than by ID order:
admit every top-level type first (213 here — the `class` and `enum` kinds, which are what a
capability statement names), then members of the types the inherited units and the executed examples
actually mention, until the cap. Alternatively raise the cap for this one job; that is weaker,
because at 1,467 symbols any fixed cap taken alphabetically still ends in the b's or the c's.

**Corroborated inside this one cohort, with the surface size as the only variable.** Cells Go has
109 public symbols — under the cap — so every symbol entered its packet and its investigation
succeeded on the first attempt. Same ecosystem, same plugin, same shared code, same prompt. Every
large-surface repository in the portfolio is exposed to this, not Go alone.

**Repository and finding.** `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at
`2306eeb06216be4d9cb663adcb85155594572c11`; `repository_investigation: output rejected twice`, 24
unknown fact IDs, 21 of which exist qualified.

**Not one of G4-W17's items (0)–(26).** Item (19) also concerns which symbols are published — it
drops symbols the vendored engine already tagged internal — but it is a `surface_symbols` change
that would not move `Document` into the first 150 alphabetically, and nothing in the list mentions
the packet cap.

### PROPOSAL P11 — one unlocatable quote rejects the whole review, and the run with it

**File.** `src/repository_presenter/components/readme/review/independent/review.py::review_checks`
(line 356; the quote test at line 376).

**Defect.** `review_checks` appends an error for any finding whose `quote` is not located in the
candidate, and a non-empty error list rejects the entire review output. The reviewer's job is to
compare the candidate against the inherited README, so quoting the *inherited* text when reporting
something the candidate dropped is its most natural mistake. Run 2's reviewer produced eight
findings; seven were usable and one quoted the upstream README's own line
``Run `go run main.go` to produce `hello.xlsx` ``. Two samples, both with one such quote, and the
stage failed: no `review.json` for that round, `BC-10` left `PENDING`, the run over. The review
already has the right machinery for a reviewer that misreads the candidate — six findings in the
same output were demoted to advisory with `reviewer_scope_defect: "the finding claims the candidate
does not contain X, which the candidate contains"` — but the binder's rejection runs first and
pre-empts it.

**Fix, as this lane reads it.** Drop the individual finding, or demote it to advisory with a
`reviewer_scope_defect` naming the unlocatable quote, and keep the rest of the review. This is the
shape G4-W17 has already fixed twice elsewhere — item (16) (`planning.py` rejected a whole candidate
for a trimmable ceiling breach; landed as `d707693`, "folded, not rejected") and item (17) — applied
to the one stage that still rejects wholesale. Neither of those items covers this file.

**Repository and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` at
`9f0a4033b59e9127afec7662ec9079b500af8032`; `independent_review: output rejected twice; last
rejection: finding F07: quote is not the candidate's text`.

### The dispositions this re-run leaves

`aspose-cells-foss/Aspose.Cells-FOSS-for-Go` at `9f0a4033b59e9127afec7662ec9079b500af8032`,
`BLOCKED_SHARED_CODE`, failure class `BC10_REVIEW_REJECTED_WHOLE_FOR_ONE_UNLOCATABLE_QUOTE` with
`QUICKSTART_LEADIN_BOUND_TO_THE_SIBLING_EXAMPLE` beside it. Supersedes
`GO_REGISTRY_NEVER_PROBED_SO_BC02_FAILS`, which items (8) and (9) cleared — `BC-02` PASS, measured
against a live Go proxy probe, not assumed. Resume predicate: PROPOSAL P11 landed on `main` (P8 with
it, or the repair loop will keep paying a round per run to undo what authoring wrote), then rerun
`present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Go` from a fresh lane-d branch. Everything
upstream of the review is proven for this repository: nine of eleven checks pass and the two content
findings the reviewer raised were both repaired.

`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at `2306eeb06216be4d9cb663adcb85155594572c11`,
`BLOCKED_SHARED_CODE`, failure class `INVESTIGATION_PACKET_TRUNCATES_A_LARGE_SURFACE`. Supersedes
`GO_REGISTRY_NEVER_PROBED_SO_BC02_FAILS`, cleared the same way — its `install_command:go` is
`SUPPORTED` from a live probe and all 1,467 of its symbols now carry a kind. Resume predicate:
PROPOSAL P10 landed on `main`, then rerun `present --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`
from a fresh lane-d branch. This repository has never been composed past S3, so its next run is an
investigation, not a seal.

## 2026-09-06 22:05 — G4-W15 second re-run, Aspose.PDF for Go, after G4-W17 item 27

Item 27 landed on `main` at `0d8767f` (21:27): `core/facts.py`'s `SYMBOL_CAP` raised from 150 to
6000. That is the exact resume predicate PROPOSAL P10 named for
`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`, so this run re-ran only that repository, from a fresh
worktree `C:\w\d15b` on branch `lane-d/rerun-go-2` off `origin/main` at `ffdf4c7`. No lane-owned
code changed; nothing in this run is a code change at all.

### The resume predicate is met and `INVESTIGATION_PACKET_TRUNCATES_A_LARGE_SURFACE` is closed

`repository_investigation` had been rejected twice on every previous attempt, with 24 unknown fact
IDs, because the packet's 150 admissions ran out inside the letter `b` and `Document` was never
shown. This run:

- `S3 repository_investigation` **succeeded**, on the second attempt, and produced the first
  investigation this repository has ever had: 8 capabilities, 6 workflows, 4 problems solved, 6
  limitations, 0 uncertainties. Its one rejected attempt cited `public_symbol:document.validate` —
  the model was now *reading* `Document` and mis-spelled one member of it, rather than being blind
  to the type entirely. That is the class closing, measured, not assumed.
- `S4 source_reconciliation` succeeded on the first attempt.
- `S5 presentation_planning` succeeded on the second attempt; an 18-section plan.
- `S6 section_authoring` authored **seven of its eight sections on the first attempt**, clean.

Facts at this revision are unchanged from the previous run and confirm the surface is intact: 1,620
records — `public_symbol` 1,467, `inherited_unit` 90, `link_target` 43, `example` 6, `identity` 5,
`license` 2, `package` 2, `build_test_asset` 2, `dependency` 1, `import_path` 1, `install_command`
1; digest `403bdbf1e2d1e193aa0494bd0d3203eeb38ee085e19e2daa82000e5a826c7d51`. Examples: 6 candidates,
5 executed, 1 not verified.

### The run still did not seal — it now fails at S6 on a single token

`section_authoring: output rejected twice; last rejection: unit limitation:3: identifiers that are
not accepted fact values: ZapfDingbats`. One unit, one token, both attempts, and the whole run ends
with no candidate. This is a **new** class, reached only because item 27 cleared the old one.

### PROPOSAL P12 — a standard's name the source spells only inside a code span is unwritable

**File.** `src/repository_presenter/components/readme/composition/authoring.py::prose_nouns`
(line 713), through `unit_checks`' stray-identifier test (line 932) and `source_prose` (line 697)
with `_NOT_PROSE` (line 52).

**Defect.** `prose_nouns` admits a proper noun "only when the source README spells it in running
prose — outside every fenced block, code span, link destination, URL and tag, where code lives".
That rule is right for an *identifier*: a backticked `Document` should be checked against the
surface, not waved through. It is wrong for a token the surface has never heard of. Aspose.PDF for
Go's README states its own PDF/A limitation as

> `ConvertToPDFA` auto-embeds non-embedded Standard-14 fonts but does not auto-fix
> `Symbol`/`ZapfDingbats`, composite (Type0/CJK) fonts, or PDF/A-1 transparency

`ZapfDingbats` is a PDF Standard-14 **font name** — a standard's name, exactly the class
`prose_nouns` exists to admit — and this README's only two spellings of it are inside code spans, so
`source_prose` strips both and the noun is never admitted. `section_authoring` wrote the limitation
faithfully, citing `inherited_unit:081.list`, the very fact that carries the sentence, and was
rejected; the retry wrote the same true sentence again, because the limitation cannot be stated
without naming the font. Two rejections end the stage and the run.

**The controlled comparison is inside this one repository.** 36 nouns were admitted for it, among
them `TrueType`, `OpenType`, `Type1C`, `DeviceCMYK`, `DeviceGray`, `DeviceRGB`, `DeviceN` and
`PostScript` — the same class of thing as `ZapfDingbats`, admitted only because this README happens
to spell *those* outside backticks. `Type0`, from the same sentence, is rejected for the same reason
`ZapfDingbats` is. Sharper still: `Symbol`, named in the same breath as `ZapfDingbats` in the same
sentence, passes — not as a font, but by the accident that an unrelated annotation type has a field
`CaretAnnotation.Symbol`. A rule whose verdict on two adjacent font names differs by an unrelated
coincidence is not tracking the property it means to track.

**Fix, as this lane reads it.** In `prose_nouns`, also admit a proper-noun token spelled inside a
code span of a `SUPPORTED` `inherited_unit` **when no `public_symbol` fact spells that token at
all**, bare or as any dotted suffix. A token the extracted surface has never heard of is not an API
identifier, whatever typography the upstream author chose for it; and the admission is safe by
`prose_nouns`' own stated reasoning — "a noun is never wrapped and never carries a claim, exactly as
a registry or hosting name does not". The renderer leaves nouns in plain text, so nothing asserts
that `ZapfDingbats` is part of this library's API. Verified against this repository's facts: 0 of
1,467 `public_symbol` values spell `ZapfDingbats`.

**Rejected alternative.** Matching a standard-name shape (a capitalised word ending in a digit, a
known font list) — a rule fitted to one sample, and it would still miss the next format name. Also
rejected: leaving it to the prompt, which cannot work, since the sentence is true and the model is
right to write it.

**Portfolio-wide, not Go-specific.** Any repository whose README backticks the name of a format,
standard, font or codec is exposed the moment a unit needs to state a limitation about it.

**Repository and finding.** `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at
`2306eeb06216be4d9cb663adcb85155594572c11`; `section_authoring: output rejected twice; last
rejection: unit limitation:3: identifiers that are not accepted fact values: ZapfDingbats`;
rejected unit text, both attempts, citing `inherited_unit:081.list`: "ConvertToPDFA auto-embeds
Standard-14 fonts but does not auto-fix Symbol, ZapfDingbats, composite fonts, or PDF/A-1
transparency, requiring validation with a dedicated tool such as veraPDF."

### PROPOSAL P13 — one unwritable unit ends the run, where folding it would not

**Subordinate to P12; recorded because it is what turned a one-token defect into a dead candidate.**

**File.** `src/repository_presenter/components/readme/composition/authoring.py::unit_checks`
(line 932), whose non-empty error list rejects a section's whole output.

**Defect.** Seven of eight sections were authored clean on the first attempt. The eighth carried
four limitation units, three of them faultless, and one stray token in the fourth discarded the
section twice and ended the transaction. This is the shape G4-W17 has already fixed twice — item
(16), `planning.py` rejecting a whole candidate for a trimmable ceiling breach (landed `d707693`,
"folded, not rejected"), and item (17) — and once more in PROPOSAL P11 for the independent review.
`unit_checks` is a third site with the same wholesale behaviour.

**Fix, as this lane reads it.** Drop the single offending unit and keep the section, exactly as
`merge_repeated_slots` (line 809) already repairs a malformed output in place, when the remaining
units still satisfy the section's own contract requirements. Fixing P12 removes this occurrence;
fixing P13 removes the class of one-unit-kills-the-run. P12 is the better fix and should land first.

### The disposition this second re-run leaves

`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at `2306eeb06216be4d9cb663adcb85155594572c11`,
`BLOCKED_SHARED_CODE`, failure class `SOURCE_CODE_SPAN_NOUN_IS_UNWRITABLE`. Supersedes
`INVESTIGATION_PACKET_TRUNCATES_A_LARGE_SURFACE`, which item 27 closed — S3 succeeded and produced a
real investigation, measured, and S4, S5 and seven eighths of S6 followed it. Resume predicate:
PROPOSAL P12 landed on `main` (P13 with it, or beside it), then rerun `present --repo
aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` from a fresh lane-d branch.

**What is not claimed.** The run ends at S6, so S7 through S11 — repair, validation, the independent
review, the seal — are still unmeasured for this repository. Three of the four stages it has now
passed it had never reached before; nothing here says the remaining five will pass.

## 2026-09-06 22:51 — G4-W15 third re-run, Aspose.PDF for Go, after G4-W17 item 36

Item 36 landed on `main` at `3e6c6b2` (22:31): `composition/authoring.py::prose_nouns` now also
harvests identifier-shaped tokens from inline code spans and admits one when no `public_symbol` fact
spells it. That is the exact resume predicate PROPOSAL P12 named, so this run re-ran that repository
from a fresh worktree `C:\w\d15r3` on branch `lane-d/G4-W15-r3` off `origin/main` at `3e6c6b2`. No
lane-owned code changed; nothing in this run is a code change at all.

### The resume predicate is met and `SOURCE_CODE_SPAN_NOUN_IS_UNWRITABLE` is closed

Measured directly against this run's own `facts.json`, calling the landed `prose_nouns` on the 1,620
extracted facts: `ZapfDingbats` **is now admitted**, and the admitted-noun set grew from 36 to 53.

`section_authoring` then made **nine calls and every one succeeded on its first attempt**, including
the `scope_limitations` section whose `limitation:3` unit was rejected twice in both previous runs
for that single token. Stage tally for the whole run: `repository_investigation` success on attempt 2
(one rejection, `public_symbol:page.adddrawing`), `source_reconciliation` success on attempt 1,
`presentation_planning` success on attempt 2 (one rejection, `format:*` IDs this repository has none
of), `section_authoring` 9 of 9 clean. 16 provider calls in total.

For the first time this repository rendered a candidate and was judged: a 17-of-18-section plan, 32
content units across 9 sections, `README.md` at **209 visible lines of 760**, and `README.patch`.
Coherence revised 0 of 32 units. Dispositions over 90 inherited units: VERIFIED_PRESERVE 45,
SUPERSEDE_REDUNDANT 30, VERIFIED_REWRITE 5, NON_CONTENT 4, DEFER_UNRESOLVED 3, VERIFIED_MOVE 2,
OMIT_UNSUPPORTED 1.

### It did not seal — validation is 7 pass, 2 fail, 2 pending

**PASS: BC-01, BC-02, BC-03, BC-04, BC-05, BC-06, BC-09.** BC-04 in particular now passes over
`opening, key_capabilities, scope_limitations, api_reference, documentation_resources,
enterprise_relationship` — the stray-identifier family that item 36 addressed. BC-10 and BC-11 are
`PENDING` (judged at S10/S12) and were never reached, so the independent review and the no-op proof
remain unmeasured for this repository.

**FAIL BC-07** — `internal narration 'validator'`, causal stage COMPOSING, section `api_reference`.
**FAIL BC-08** — two `VERIFIED_REWRITE` units keep a command the candidate does not render.

### PROPOSAL P14 — the narration guard rejects the repository's own inherited vocabulary

**File.** `src/repository_presenter/components/readme/validation/registry.py`, `_NARRATION` (line
249, the bare entry `"validator"`) and its use at line 850.

**Defect, and why G4-W17 item 22 as written does not cover it.** Item 22 (lane D's own PROPOSAL P6,
from Cells Rust) diagnosed `_NARRATION` matching its nine phrases as a bare substring with no word
boundary, and proposed word-boundary matching plus an exemption for a value that is itself a
`public_symbol` fact — right for `WorkbookValidator`, where the guarded word is a *substring of a
public type*. Aspose.PDF for Go fails the same check for a different reason and **none of item 22's
three remedies would clear it**:

- it is not a substring — the candidate's prose reads "confirm full conformance with a dedicated
  validator such as veraPDF", so `validator` is already a standalone word and a word boundary
  changes nothing;
- it is not a public symbol — **0 of 1,467** `public_symbol` values contain `validator`, so the
  public-symbol exemption never fires;
- it is not in a code span, so the code-span exemption never fires either.

It is the **repository's own English**. `validator` appears verbatim in two SUPPORTED
`inherited_unit` facts, `066.list` and `081.list`, in the identical phrase "conformance with a
dedicated validator such as veraPDF". The candidate is faithfully restating the upstream README's own
PDF/A caveat, and a check meant to catch this tool narrating about itself is firing on the subject
matter of a PDF library, which legitimately talks about conformance validators.

**Fix, as this lane reads it.** Land item 22's word-boundary change, and add a fourth exemption of
the same kind as the others: a guarded phrase is not narration when the source README itself uses it,
i.e. when the phrase occurs in a SUPPORTED `inherited_unit` fact's value. That is the principle
`prose_nouns` already applies to nouns — inherited vocabulary is the repository's, not ours. The
alternative and narrower fix: replace the bare `"validator"` entry with the narration it actually
means to catch (`"validator version"`, the field this pipeline writes into `validation.json`), since
no self-narrating sentence this guard exists to block says the bare word alone.

**Rejected alternative.** Re-asking authoring to avoid the word: measured this run and it does not
work — see below. Also rejected: dropping the entry, which would stop catching genuine narration.

**Corroboration for item 34's repair finding.** The repair loop did route this failure (item 22's own
section-location code at line 857 worked: the failure carried `section_id: api_reference`). S7 then
recorded **1 repaired** — but every change it wrote back is byte-identical, `before` equal to `after`
for `R01`, `R02` and `R03`; the model returned the same prose because the sentence is true and its
own source says it. The round is nonetheless recorded as a repair, and the failure re-raised. That is
exactly lane C's item (34) second half — "a repair that made no change is recorded repaired rather
than unchanged" — now corroborated in a second lane and a second ecosystem.

**Repository and finding.** `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at
`2306eeb06216be4d9cb663adcb85155594572c11`; `BC-07 failed at COMPOSING: internal narration
'validator'; after one repair attempt the equivalent failure stands`.

### PROPOSAL P15 — P7/item 23 confirmed in a second ecosystem, unchanged and still unrepairable

**File.** `validation/registry.py`'s BC-08, and `repair/targeted.py`'s `validation_defects`.

BC-08 fails with two failures, both `section_id: null`:

- `inherited_unit:025.paragraph: VERIFIED_REWRITE keeps the command 'go run ./_examples/feature_showcase' but the candidate does not render it`
- `inherited_unit:085.paragraph: VERIFIED_REWRITE keeps the command 'go run ./_examples/<name>' but the candidate does not render it`

S7's response is verbatim `"outcome": "unrepairable", "reason": "no failing check names an
LLM-owned section"`. This is PROPOSAL P7 (G4-W17 item 23), recorded from Cells **Rust** on
2026-09-06 14:05 and still open, reproducing without variation on Go — a second ecosystem, a second
family, the same null `section_id` and the same wording. The disposition record already names a
`destination_section` the repair loop may re-author; carrying that id into the `Failure` is the whole
fix. The advisory list shows the same shape twice more (`022.paragraph`, `042.paragraph`), so four of
this repository's five `VERIFIED_REWRITE` units dropped protected content.

### The disposition this third re-run leaves

`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` at `2306eeb06216be4d9cb663adcb85155594572c11`,
`BLOCKED_SHARED_CODE`, failure class `BC07_INHERITED_VOCABULARY_READ_AS_NARRATION` with
`BC08_REWRITE_DROPS_A_PROTECTED_COMMAND` beside it. Supersedes
`SOURCE_CODE_SPAN_NOUN_IS_UNWRITABLE`, which item 36 closed — measured, not assumed: `ZapfDingbats`
admitted, and 9 of 9 authoring calls clean where the same section was rejected twice before. Resume
predicate: G4-W17 item 22 **plus PROPOSAL P14's fourth exemption** (word boundaries and the
public-symbol exemption alone are proven insufficient here) and item 23 / PROPOSAL P15 landed on
`main`, then rerun `present --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` from a fresh lane-d branch.

**What is not claimed.** The run ends at S9 with two failures. BC-10 (the independent review) and
BC-11 (the byte-identical no-op rerun) are `PENDING`, never judged; nothing here says they would
pass.

## 2026-09-06 23:06 — G4-W15 re-run, Aspose.Cells for Go, after G4-W17 items 28 and 29

Items 28 (`8d23190`) and 29 (`c9951b1`) landed on `main`, the two resume predicates PROPOSAL P11 and
PROPOSAL P8 named for `aspose-cells-foss/Aspose.Cells-FOSS-for-Go`. The repository was run twice, in
worktree `C:\w\d15c` on branch `lane-d/G4-W15-cells`: first at `8d23190` (item 28 only), then again
after rebasing to `638a7ac` (items 29 and 22 as well). No lane-owned code changed in either run.

### P11's class is closed — the review returns a verdict instead of collapsing

Both previous runs ended with the independent review's output **rejected twice** because one of its
eight findings quoted the inherited README rather than the candidate, taking the seven usable
findings and the whole run with it. At `8d23190` the review returned `REJECT_PRESENTATION` with **3
findings and 5 advisory**, and the five it folded out are exactly the unlocatable ones — `##
Dependencies`, `### Required Package Dependencies`, `### Native and System Requirements`, `####
Detailed Member Reference`, `  PRODUCT[`. Fold-not-reject did precisely what the proposal said.

### P8's class is closed too — the quick-start finding is gone from the blocking set

At `8d23190` the blocking set still held `F04`, "Reorder the Quick Start examples to match the
original README" — the sibling-slot lead-in. After the rebase to `638a7ac` that finding is no longer
raised as blocking; the equivalent observation survives only as advisory `F03`. Blocking findings fell
from 3 to 2 and advisory rose from 5 to 6 across the two runs of the same revision.

### The run reached S9 clean and S10 rejected it — 9 pass, 1 fail, 1 pending

`231` facts (109 public symbols, 66 inherited units), 10 example candidates with 8 executed, 1
failed, 1 not verified; a 16-of-18-section plan, 39 units across 8 sections, `README.md` at **224
visible lines of 495**. **BC-01 through BC-09 all PASS** — every deterministic check, BC-07 among
them. Only BC-10 fails and BC-11 is `PENDING` (S12, never reached). Repair ran 2 rounds, 4 repaired,
3 re-raised; the equivalent failure stands.

### PROPOSAL P16 — the reviewer treats the contract's required API surface as unsupported detail

**File.** `prompts/` for the independent review's `presentation` criterion, and
`review/independent/review.py` where its findings become BC-10 failures.

**Defect.** Both remaining blocking findings ask for verified content to be **deleted because the
upstream README did not have it**:

- `F06`, `api_reference`: quote "`- \`ExportToCSV\`: ExportToCSV writes the worksheet at sheetIndex
  to a CSV file using the given delimiter…`", repair "Remove the unsupported member details that are
  not in the original README and stick to the verified public symbols."
- `F07`, `development_testing`: repair "Remove the unsupported specific commands and guidance, and
  stick to the verified test commands from the original README."

`ExportToCSV` is a verified `public_symbol` fact of this repository's 109-symbol surface, and
**BC-04 passed on this very candidate** — every identifier in prose is a fact value in a code span.
The reviewer's word for it is "unsupported"; the deterministic check that owns support says
otherwise. Worse, the collapsed API reference is not optional decoration: `loop-prompt.md` §6 rule 8
and `README_CONTRACT.md` require the complete public API surface inside the collapsed reference
precisely because most FOSS repositories have no other reference. Obeying `F06` would breach the
contract; ignoring it fails BC-10. No repair can satisfy both, which is why four repairs produced
three re-raises.

**This is lane C's item (33) generalised.** Item (33) records BC-10 rejecting the renderer's own
mandated `ADDITIONAL_EXAMPLES_SUMMARY` structure and routing the repair to authoring, which cannot
change renderer-owned structure. Here the same check rejects contract-mandated *content* and routes
the repair to authoring, which cannot delete verified surface without breaching the contract. Both
are the review criterion judging against the inherited README as the standard of support rather than
against the facts.

**Fix, as this lane reads it.** State in the review packet that the candidate's fact set, not the
upstream README, is the standard of support, and that the collapsed API reference is contract-required
and complete by design — so "not in the original README" is never on its own a defect for a claim
BC-04 has already verified. Land it with item (33), which needs the same sentence.

**Rejected alternative.** Making BC-10 advisory for `presentation` findings: that would hide genuine
presentation defects, and rule 5 forbids leaving a finding permanently unresolved. Also rejected:
trimming the API reference to the upstream README's members, which breaches rule 8 outright.

**Routing note, corroborating P15.** Both BC-10 failures carry `section_id: null` even though each
failure's own `detail` names its section (`F06 api_reference`, `F07 development_testing`). The
finding objects do carry `section_id`; the `Failure` does not. Same shape as P15/item 23.

### The disposition this re-run leaves

`aspose-cells-foss/Aspose.Cells-FOSS-for-Go` at `9f0a4033b59e9127afec7662ec9079b500af8032`,
`BLOCKED_SHARED_CODE`, failure class `BC10_REVIEW_REJECTS_CONTRACT_REQUIRED_SURFACE`. Supersedes
`BC10_WHOLE_REVIEW_REJECTED_ON_ONE_UNLOCATABLE_QUOTE` (item 28, closed and measured) and the
quick-start lead-in class (item 29, closed and measured). Resume predicate: PROPOSAL P16 landed on
`main`, with or beside lane C's item (33), then rerun `present --repo
aspose-cells-foss/Aspose.Cells-FOSS-for-Go` from a fresh lane-d branch.

**What is not claimed.** BC-11, the byte-identical zero-call rerun, is `PENDING` and was never
judged. This candidate is one check from sealing, not sealed.

## 2026-09-06 23:17 — G4-W16 second re-run, Cells for Rust, after G4-W17 item 22

Item 22 landed on `main` at `638a7ac`: `validation/registry.py`'s narration guard now matches at a
word boundary and exempts a repository's own symbols. That is the exact resume predicate PROPOSAL P6
named, so this run re-ran the one Rust repository from a fresh worktree `C:\w\d16r` on branch
`lane-d/G4-W16-r2` off `origin/main` at `638a7ac`. No lane-owned code changed.

### The resume predicate is met and `BC07_PUBLIC_SYMBOL_READ_AS_NARRATION` is closed

**BC-07 PASSES.** In the 14:05 re-run it failed on the bare word `validator`, matched inside this
crate's own public type `WorkbookValidator`. Item 22's word boundary plus symbol exemption is exactly
what P6 asked for and it is measured working here: same repository, same surface, check green.

The run reached S9 with **7 pass, 2 fail, 2 pending**: BC-01, BC-03, BC-04, BC-05, BC-06, **BC-07**
and BC-09 pass; BC-10 and BC-11 were never judged. 2,224 facts (2,084 public symbols, 81 inherited
units), a 16-of-18-section plan, 140 units across 8 sections, `README.md` at 173 visible lines of
1,068.

### It did not seal — and BC-02, which passed at 14:05, now fails

`BC-02 failed at EXTRACTING: install_command:cargo is UNRESOLVED: package registry: cargo could not
be read`. The install fact carries polarity `UNRESOLVED`, confidence 0.5, and evidence
`https://crates.io/api/v1/crates/aspose-cells-foss-rust` — "package registry: cargo could not be
read". Repair's answer: `"EXTRACTING is not repairable by revision"`, unrepairable.

**This is a change in the registry's behaviour, not in the candidate.** At the 14:05 re-run
crates.io answered *conclusively* — a 404 on the crate — the fact read `CONTRADICTED`, item (0)'s
source-build path fired on a measured `cargo build` (exit 0), and BC-02 **passed**. This run the
registry could not be read at all, so the fact stops at `UNRESOLVED`, and G4-W17 item (24)'s
`_source_build_fact` admits `UNRESOLVED` **only when the ecosystem is not in `REGISTRY_TYPES`**.
Rust is in it (`cargo`), so the source-build path is deliberately skipped and BC-02 fails closed —
by item (24)'s own design and its own mutation test.

Corroborating evidence that the read, not the crate, is what changed: this run's `probes.json`
records `https://crates.io/` itself returning **HTTP 404 after 17.5 s**, where every other probed
host answered 200 in about a second. A 404 on the crates.io root is not a real answer about a crate.

### PROPOSAL P17 — "the registry said no" and "the registry did not answer" are the same fact

**File.** `extractors/.../extract.py::_source_build_fact` (item (24)'s gate) and
`validation/registry.py::_check_install` (BC-02); the probe itself in the vendored `RegistryProbe`.

**Defect.** A registry-having ecosystem has exactly two ways to end up `UNRESOLVED`, and the fact
record does not distinguish them: the registry was reached and had nothing conclusive to say, or the
registry could not be reached at all. Item (24) fails closed on both, correctly refusing to mask the
first. The consequence is that this candidate's BC-02 verdict — and so whether it can ever seal —
depends on whether crates.io answers on the day, even though the source-build evidence that item (0)
admits is identical in both runs and was measured green in both.

**Fix, as this lane reads it, smallest first.**

1. Harden the probe: crates.io requires a named `User-Agent` (`RESEARCH_AND_GUIDELINES.md` §29) and a
   404 on `https://crates.io/` root suggests the request is being refused rather than answered. Fix
   the request and the conclusive 404-on-crate reading returns, and with it the 14:05 pass. This
   costs nothing in check strength and is the honest first move.
2. Only if that is not enough: record *why* a fact is `UNRESOLVED` as a distinguishable value —
   "registry unreachable" versus "registry inconclusive" — and let item (24)'s gate admit a verified
   source build for the unreachable case, still failing closed on the inconclusive one. This keeps
   item (24)'s mutation test literally true (a registry-having ecosystem's *transient* `UNRESOLVED`
   must not flip to `SUPPORTED`) while removing the network-luck dependency.

**Rejected alternative.** Widening item (24)'s gate to all `UNRESOLVED` install facts for
registry-having ecosystems: that is precisely what item (24) forbids and its mutation test blocks,
and it would let a genuinely transient failure publish an unverified install claim.

**Repository and finding.** `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at
`1a6004af47b1ef15385f9d36d381a8172428cc7e`; `BC-02 failed at EXTRACTING: install_command:cargo is
UNRESOLVED: package registry: cargo could not be read; no repair could act on it`.

### PROPOSAL P18 — P7/item 23 confirmed a third time, and wider than its own wording

BC-08 fails on the same two commands as the 14:05 run:

- `inherited_unit:079.paragraph: VERIFIED_PRESERVE keeps the command 'cargo bench' but the candidate does not render it`
- `inherited_unit:079.paragraph: VERIFIED_PRESERVE keeps the command 'cargo doc --no-deps --open' but the candidate does not render it`

Both carry `section_id: null`; repair records `"unrepairable"`, `"no failing check names an
LLM-owned section"`. Two things are new. First, this is the **third** repository to hit it — Cells
Rust (14:05), PDF Go (22:51, P15), Cells Rust again — across two ecosystems. Second, the disposition
kind here is **`VERIFIED_PRESERVE`**, not `VERIFIED_REWRITE`: item 23 is written about "a
VERIFIED_REWRITE placement's dropped protected command", and the same defect reaches a preserved unit
too. The fix must carry the destination section id into the `Failure` for **every** disposition kind
that names one, not for rewrites alone.

### The disposition this second re-run leaves

`aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` at `1a6004af47b1ef15385f9d36d381a8172428cc7e`,
`BLOCKED_SHARED_CODE`, failure class `BC02_REGISTRY_UNREADABLE_FAILS_CLOSED` with
`BC08_REWRITE_DROPS_A_PROTECTED_COMMAND` beside it. Supersedes
`BC07_PUBLIC_SYMBOL_READ_AS_NARRATION`, which item 22 closed — measured, BC-07 green on the same
crate whose `WorkbookValidator` failed it before. Resume predicate: PROPOSAL P17 (step 1 alone may
suffice) and item 23 as widened by PROPOSAL P18 landed on `main`, then rerun `present --repo
aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` from a fresh lane-d branch.

**Observation, not a proposal.** Example verification came back 1 executed of 7 candidates, where the
14:05 run type-checked its Quick Start; the plan carries `examples 1+0`. Not investigated, and not
the blocker — BC-03 passed on what was rendered. Worth a look before this repository's next attempt.

**What is not claimed.** BC-10 and BC-11 are `PENDING` and were never judged; nothing here says the
independent review or the no-op proof would pass.
