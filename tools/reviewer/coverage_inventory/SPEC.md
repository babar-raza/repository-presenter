# Clone-information coverage inventory (TC-COV-01)

Owner goal: all useful information in a cloned repository reaches the one README. This tool measures
how far each CURRENT sealed bundle is from that, per repository and per information type. Read-only:
no provider call, no write to any repository, the only network use is `gh api repos/<r>/releases/latest`
(GET) and the shallow clones made beforehand.

## Usage

```
git clone --depth 1 https://github.com/<r>.git runs/clones/<owner>__<name>      # one per registry entry
python -X utf8 tools/reviewer/coverage_inventory/run.py --clones runs/clones --releases runs/releases \
    --out evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis --control-revision <sha>
python -m pytest tools/reviewer/coverage_inventory/test_matching.py
```

## Information units (what "material" means) and where each ecosystem declares it

| unit type | source in the clone | matched by |
|---|---|---|
| `readme_unit` | each README section (heading + body) with material content | heading + word overlap, else word overlap |
| `doc_page` | `docs/**/*.{md,mdx,rst}` (headings, size) | path, basename, `docs/` pointer, overlap |
| `root_doc` | other root-level `*.md` (PUBLISHING.md, PUBLIC_API.md, ...), not agent files | path, basename |
| `changelog` | CHANGELOG*, CHANGES*, HISTORY*, NEWS*, RELEASE*, RELEASE_NOTES* (root, docs/, .github/) | path, basename, a changelog/releases heading |
| `github_release` | body of `releases/latest` | a `/releases` link, a changelog heading, body overlap |
| `contributing`, `security_policy`, `code_of_conduct` | CONTRIBUTING*, SECURITY*, CODE_OF_CONDUCT* (root, docs/, .github/) | path, basename, same-named heading |
| `cli_entry` | Python `[project.scripts]`/`gui-scripts`/poetry scripts/`console_scripts`/`__main__.py`; `package.json` `bin`; `.csproj` `OutputType` Exe; Go `package main` + `func main`; Cargo `[[bin]]`, `src/main.rs`, `src/bin/*`; CMake `add_executable`; `pom.xml` `mainClass`/`Main-Class`; Gradle `mainClass` (sample, demo, example, benchmark and test programs excluded) | command used inside a code span/block |
| `target_framework` | `.csproj`/`Directory.Build.props` TargetFramework(s); `pom.xml` compiler release/source/target, `java.version`; Gradle toolchain; `tsconfig*.json` target; `package.json` engines.node; `Cargo.toml` edition and rust-version; `go.mod` go; `pyproject`/`setup` requires-python; CMake C++ standard | per-kind regex ('net8.0' also as '.NET 8', 'java 21') |
| `ci_matrix` | `.github/workflows/*.yml` `strategy.matrix` axes naming a platform or runtime (os, runtime versions, compilers) | every value present (OS names accept Linux/macOS), or first and last of a version range |
| `example_file` | files under `examples/`, `samples/`, `demo/`, `cookbook/`, `tutorials/` (leading `_` ignored) | path, basename, word overlap, `examples/` pointer |
| `test_suite` | test directories with their test-file counts (tests/, test/, src/test, *Tests, *.spec.*, ...) | `<dir>/` pointer |
| `license_notice` | LICENSE*, COPYING*, NOTICE*, THIRD-PARTY* | path, basename, license name, a licence/notices heading |
| `build_command`, `test_command` | CI `run:` lines, `package.json` scripts, Makefile targets, and conventions implied by `go.mod`, `Cargo.toml`, `.sln/.csproj`, `pom.xml`, CMake, pytest config; reduced to tool + verb | tool and verb in order on one line |

## Status of a unit against a bundle

`PRESENT_IN_README` (the sealed README carries it) > `PRESENT_IN_FACTS` (ingested into `facts.json` but not carried) >
`MISSING`. A repository without a bundle gets `NO_BUNDLE`, and `in_live_readme` says whether the upstream README carries
the unit. Every row records `matched_in` and the match `method`; `readme_unit` rows that are not delivered also carry the
dispositions the pipeline gave the inherited README units of that section.
