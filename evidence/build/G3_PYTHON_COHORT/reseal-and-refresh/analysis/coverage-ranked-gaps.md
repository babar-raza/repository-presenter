# Clone-information coverage: ranked gaps (TC-COV-01)

Measured 2026-10-10 by `tools/reviewer/coverage_inventory/` (read-only, no provider call). Inputs: a shallow clone of each of the 36 `data/registry.json` repositories at its live default-branch head; the repository's CURRENT sealed bundle (`candidates/<r>/CURRENT` -> `facts.json`, `README.md`); the live upstream README; `gh api repos/<r>/releases/latest` (GET). Per-unit rows: `coverage-unit-table.csv`; per repository x unit type: `coverage-gap-table.csv`.

## Population

- 36 repositories; **30 have a CURRENT sealed bundle** (19 sealed at the live head, 11 sealed at an older revision, `source_moved`); **6 have no bundle** (Aspose.3D-FOSS-for-TypeScript, Aspose.GIS.FOSS-for-.Net, Aspose.PDF-FOSS-for-TypeScript, Aspose.PSD-FOSS-for-.NET, Aspose.PSD-FOSS-for-Python, Aspose.TeX-FOSS-for-Python). Ranking counts the 30 bundled repositories; the no-bundle repositories are shown separately because there is no sealed README to compare.
- A unit is **delivered** when the sealed README carries it (`PRESENT_IN_README`), **facts only** when the pipeline ingested it but the README does not (`PRESENT_IN_FACTS`: a composition or disposition loss), **missing** when neither (`MISSING`: an extractor gap). Every match records its method (`path`, `basename`, `name`, `command`, `pattern`, `values`, `heading`, `heading+overlap`, `content_overlap`, `dir_pointer`); `dir_pointer` and `heading` are the weak ones.

## Ranked gap types (by number of repositories affected)

`affected` = bundled repositories with at least one undelivered (missing or facts-only) unit of the type, out of those that have any unit of it. `current` = the same count restricted to the 19 bundles sealed at the live head (so the gap is not just age).

| rank | gap type | repos affected | of which current-head bundles | repos with a hard MISSING | units undelivered / total | facts-only | missing |
|---|---|---|---|---|---|---|---|
| 1 | `readme_unit` | 29 / 30 | 18 | 4 | 278 / 995 | 257 | 21 |
| 2 | `test_command` | 16 / 25 | 9 | 16 | 19 / 31 | 0 | 19 |
| 3 | `build_command` | 15 / 22 | 7 | 15 | 17 / 26 | 0 | 17 |
| 4 | `github_release` | 14 / 17 | 6 | 14 | 14 / 17 | 0 | 14 |
| 5 | `test_suite` | 12 / 26 | 8 | 12 | 21 / 41 | 0 | 21 |
| 6 | `ci_matrix` | 11 / 12 | 4 | 11 | 15 / 18 | 0 | 15 |
| 7 | `target_framework` | 7 / 30 | 5 | 7 | 13 / 42 | 0 | 13 |
| 8 | `example_file` | 6 / 15 | 3 | 0 | 35 / 117 | 35 | 0 |
| 9 | `changelog` | 6 / 13 | 3 | 2 | 6 / 13 | 4 | 2 |
| 10 | `security_policy` | 6 / 9 | 4 | 1 | 6 / 9 | 5 | 1 |
| 11 | `contributing` | 5 / 8 | 4 | 0 | 5 / 8 | 5 | 0 |
| 12 | `root_doc` | 5 / 14 | 3 | 4 | 5 / 16 | 1 | 4 |
| 13 | `doc_page` | 3 / 10 | 1 | 0 | 50 / 94 | 50 | 0 |
| 14 | `cli_entry` | 3 / 4 | 1 | 3 | 3 / 4 | 0 | 3 |
| 15 | `code_of_conduct` | 3 / 4 | 2 | 0 | 3 / 4 | 3 | 0 |
| 16 | `license_notice` | 0 / 30 | 0 | 0 | 0 / 36 | 0 | 0 |

## Top 6: could an existing template section render it?

Rows refer to `docs/README_CONTRACT.md` section 2. "Template change" means a new section id, heading or ordering (a governed RENDERER/shell change). A new fact kind, an executed example or a disposition fix is not a template change.

| rank | gap type | fits an existing section without a template change? | which section | still needed (not a template change) |
|---|---|---|---|---|
| 1 | `readme_unit` (29 repos) | **depends** | the section the unit belongs to (identity, installation, quick_start, additional_examples, ...) | not a template gap: the shell has a home for each; the unit is dropped by its disposition (OMIT_UNSUPPORTED, SUPERSEDE_REDUNDANT) or by composition. Fix is in verification (toolchain) and reconciliation, not the shell. |
| 2 | `test_command` (16 repos) | **yes** | development_testing (row 17: fenced commands from the build files and CI, single-target run) | a command fact (kind or attributes of build_test_asset) read from CI `run:` steps and manifests |
| 3 | `build_command` (15 repos) | **yes** | development_testing (row 17) and installation source-build fallback (row 8) | the same command fact; commands are renderer-emitted, never LLM-typed |
| 4 | `github_release` (14 repos) | **links-only** | documentation_resources (row 15: a verified releases link) and the release sentence in development_testing (row 17) | a link_target fact for the releases page. The release BODY (highlights) has no row: rendering it is a template change |
| 5 | `test_suite` (12 repos) | **yes** | development_testing (row 17: sentence sizing the suite when a test-file count is verified) | build_test_asset already exists; only the per-root count and the paths to name |
| 6 | `ci_matrix` (11 repos) | **yes** | development_testing (row 17: build files and CI) as one sentence; installation (row 8) for supported runtimes | a matrix fact per workflow axis (os, runtime versions) |

Remaining gap types (same judgement):

- `target_framework` (7 repos): **yes**; installation (row 8: one sentence on supported runtimes from manifest facts) and the badges runtime floor (row 2).
- `example_file` (6 repos): **yes**; additional_examples (row 12: task-named ### headings, collapsible).
- `changelog` (6 repos): **links-only**; documentation_resources (row 15).
- `security_policy` (6 repos): **links-only**; documentation_resources (row 15: repository-relative links to verified tracked docs).
- `contributing` (5 repos): **links-only**; documentation_resources (row 15: a contributor guide).
- `root_doc` (5 repos): **links-only**; documentation_resources (row 15: a publishing or contributor guide, implementation notes).
- `doc_page` (3 repos): **links-only**; documentation_resources (row 15: repository-relative links to verified tracked docs).
- `cli_entry` (3 repos): **partial**; installation verify line (row 8) and additional_examples (row 12) for a CLI example.
- `code_of_conduct` (3 repos): **links-only**; documentation_resources (row 15).

## Cut-1 thin slice

Gap types an existing section can already render (`yes` or `links-only`): `test_command`, `build_command`, `github_release`, `test_suite`, `ci_matrix`, `target_framework`, `example_file`, `changelog`, `security_policy`, `contributing`, `root_doc`, `doc_page`, `code_of_conduct`. Greedy cover of the bundled repositories (each step adds the type touching the most not-yet-covered repositories):

| step | add gap type | repos it touches | cumulative repos touched |
|---|---|---|---|
| 1 | `test_command` | 16 | 16 / 30 |
| 2 | `build_command` | 15 | 21 / 30 |
| 3 | `github_release` | 14 | 25 / 30 |
| 4 | `example_file` | 6 | 27 / 30 |
| 5 | `test_suite` | 12 | 28 / 30 |
| 6 | `target_framework` | 7 | 29 / 30 |

- Needs only a renderer/plan change (the facts already exist, the README just does not carry them): `example_file`, `contributing`, `doc_page`, `code_of_conduct`.
- Needs an extractor fact first (at least one unit is not in `facts.json` at all), still no template change: `test_command`, `build_command`, `github_release`, `test_suite`, `ci_matrix`, `target_framework`, `changelog`, `security_policy`, `root_doc`.
- Left for cut 2 (needs a template change, or a verified example the renderer cannot yet produce): release-note BODY and doc-page CONTENT (no section) and a dedicated CLI Usage section (only a plan `deviation` today). `readme_unit` losses are a verification/reconciliation matter, not a shell matter.

## Facts-only rows: the loss is after extraction

Types where the pipeline already holds the information in `facts.json` but the README does not carry it (a renderer/plan fix, no extractor work): `readme_unit` (257 units), `example_file` (35 units), `changelog` (4 units), `security_policy` (5 units), `contributing` (5 units), `root_doc` (1 units), `doc_page` (50 units), `code_of_conduct` (3 units).

## Repositories without a bundle (information in the clone that the live README does not carry either)

| gap type | no-bundle repos with a unit absent from the live README | units absent / total |
|---|---|---|
| `readme_unit` | 0 / 6 | 0 / 156 |
| `test_command` | 2 / 6 | 2 / 5 |
| `build_command` | 2 / 6 | 2 / 4 |
| `test_suite` | 6 / 6 | 6 / 6 |
| `target_framework` | 3 / 6 | 3 / 6 |
| `example_file` | 1 / 6 | 9 / 37 |
| `changelog` | 0 / 6 | 0 / 1 |
| `doc_page` | 1 / 6 | 57 / 301 |
| `license_notice` | 1 / 6 | 1 / 4 |

## Sanity check against the four review reports

| repository | unit type | unit | status in this measurement | what the reviews reported |
|---|---|---|---|---|
| Font-FOSS-for-Python | cli_entry | aspose-font | PRESENT_IN_README (name) | CLI added in 26.10.2: the sealed (older) README already runs `aspose-font` in examples, so only the CLI Usage section is lost |
| Font-FOSS-for-Python | readme_unit | CLI Usage | MISSING (-) | same CLI, live README section |
| PDF-FOSS-for-.NET | target_framework | target framework net10.0 | MISSING (-) | PDF .NET framework matrix |
| PDF-FOSS-for-.NET | target_framework | target framework net9.0 | MISSING (-) | PDF .NET framework matrix |
| Slides-FOSS-for-.NET | target_framework | target framework net10.0 | MISSING (-) | review: runs on net8.0 only, csproj has net8.0;net10.0 |
| Slides-FOSS-for-.NET | contributing | CONTRIBUTING.md | PRESENT_IN_FACTS (path) | review: Contributing/CHANGELOG/CoC/SECURITY links dropped |
| Slides-FOSS-for-.NET | security_policy | SECURITY.md | PRESENT_IN_FACTS (path) | review: Contributing/CHANGELOG/CoC/SECURITY links dropped |
| Slides-FOSS-for-Java | security_policy | SECURITY.md | PRESENT_IN_FACTS (path) | review: SECURITY.md route and unpublished-version warning dropped |
| Slides-FOSS-for-Java | ci_matrix | java: 21, 25 | PRESENT_IN_README (values) | review: build.yml Java 21/25 matrix omitted |
| Slides-FOSS-for-Java | changelog | CHANGELOG.md | PRESENT_IN_FACTS (path) | review: CHANGELOG link omitted |
| Cells-FOSS-for-Rust | github_release | release V26.7.0 | MISSING (-) | Releases |
| Slides-FOSS-for-Python | github_release | release 26.8.0 | MISSING (-) | Releases |

## Caveats

- Matching is lexical and approximate (see the method column); a `MISSING` can be an LLM paraphrase the matcher cannot see, a `PRESENT_IN_README` by `heading` or `dir_pointer` can be a pointer without the information. Counts rank prevalence; they are not a quality score.
- A bundle sealed at an older revision (`source_moved`) is compared with the live head: part of its gap is age, which a reseal closes; the `current` column isolates the gaps that remain on a head-current bundle.
- Sample programs (`sample_*`, `examples/`, `_examples/`), test runners and benchmarks are excluded from `cli_entry`; build and test commands are reduced to tool + verb, including commands implied by a manifest (marked `convention` in the detail column).

