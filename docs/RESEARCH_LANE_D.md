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
