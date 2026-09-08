# Repository Layout

Status: normative for file placement. Consolidates the destination paths already scattered across
`migration/reuse-manifest.yaml`'s `expected_area_dispositions` and `docs/README_CONTRACT.md` §7
into one place, so a work item never has to reverse-engineer where a new file belongs from dozens
of manifest entries, and never invents a path those entries did not already imply.  
Owns: the target directory tree, one-concern-one-location rules, naming, and the test-mirroring
rule. Does not own build sequencing (`EXECUTION_STATE_MACHINE.md`) or legacy disposition
(`migration/reuse-manifest.yaml`), which this document follows, not sets.

## 1. Rule

Before creating a file or a new directory, check three places in this order: an existing sibling
module doing the same kind of work, this document's tree, and the `destination_area` of the
relevant `migration/reuse-manifest.yaml` entry if the work pulls legacy behavior. If none names the
path, add it to §2 in the same commit that creates it — a new top-level directory or `core`/
`components` subpackage is never introduced silently. Never leave a file at a temporary or
personal location "to organize later"; place it correctly the first time.

## 2. Target tree

```
src/repository_presenter/
  cli.py                    CLI entry point (one file; subcommands stay small, delegate to core/components)
  cursor.py                 reads project/state.yaml
  core/                     capabilities usable by any future surface, not README-specific
    identity.py             shared repository/revision identity types
    hashing.py               canonical text hashing
    errors.py               typed failure hierarchy mapped to CLI exit codes
    retry.py                bounded retry policies on tenacity
    facts.py                typed fact records and the facts.json writer (the extraction boundary)
    examples.py             shared example-verification types and the receipts writer
    probes.py               what a live read observed - status, timing, volatile reading - kept out of the hashed facts
    execution.py            bounded secret-free execution of repository examples
    config.py               gateway configuration from the process environment (a subpackage once G4 adds GitHub App configuration)
    git_safety/              push-neutered clone, safety checks
    snapshot/                immutable repository snapshot capture
    github/                  read and write GitHub API clients
    preflight.py            fail-closed LLM gateway check recording the model catalog (the GitHub check joins it at G4)
    llm/                     transport, ledger, call schema, prompt registry, prompt hygiene
    state/                   repository/proposal records, backend, migrations
    evidence/                evidence writer and manifest schema
    registry/                registry loader, revision store
    authorization/           effect-authorization contracts
    candidates.py            sealed-bundle counting (already built)
    secrets.py               secret-canary scanning (already built)
  components/readme/         README-specific behavior only
    extractors/
      platforms/              one plugin per ecosystem (python.py first)
        python_format_declarations.py  static format declarations and plugin registrations, read from syntax trees (RESEARCH §22.1, §26)
      examples/                example verification
    investigation/            repository_investigation job wiring
    reconciliation/           source_reconciliation job wiring, dispositions
    composition/               presentation_planning, section_authoring, renderer
      placement.py             where each inherited unit renders, under the three placement rules
    components/                 semantic-shell template components (README_CONTRACT.md §2)
      ecosystems.py            per-ecosystem presentation knowledge: package registry names
    validation/
      registry.py              versioned check registry
      links/                   link resolution
    review/
      independent/             independent_review job wiring
      acceptance/               30-point criterion profile (G2)
    repair/
      targeted.py              targeted_repair job wiring: defects, fingerprints, repairs.json
      rounds.py                one composition round (S3 to S10) and the bounded repair loop
    bundle/
      seal.py                  the sealed bundle, dependencies.json, and the no-op proof (S12)
      evaluation.py            dependency evaluation: changed inputs and the stage they reopen
    evidence/
      facts/                    fact extraction (README_CONTRACT.md §3 S2)
        product_pages.py        live product-page facts: Enterprise target, homepage, banner (RESEARCH §20)

prompts/                     one governed manifest per job (README_CONTRACT.md §3), flat, six files at G1
schemas/                     JSON Schemas for the cursor, manifest, candidate bundle, prompt manifests
data/                        registry, link, family, and priority data pulled per migration/reuse-manifest.yaml
profiles/                    per-repository and per-family policy overlays (ADAPT_AS_PLUGIN)
docs/                        authority documents (this tree's siblings); DECISION_LOG.md is the project-wide append-only decision log (RESEARCH_AND_GUIDELINES.md §31, split out 2026-09-08); RESEARCH_<LANE>.md (RESEARCH_LANE_B.md, _C, _D) is a lane's own append-only decision log in the same shape (RESEARCH §28.12)
plans/                       plans/idea.md, the human product authority
project/                     state.yaml, loop-prompt.md; loop-prompt-lane.md (the generic lane prompt; loop-prompt-lane-b.md is a pointer to it) and lanes/<lane>.yaml (each lane's cursor, RESEARCH §28.12); portfolio-census.json (owner planning data, RESEARCH §28.11 — never a runtime input)
migration/                   reuse-manifest.yaml
evidence/build/<gate-id>/    one manifest.json per accepted gate (EXECUTION_STATE_MACHINE.md §10)
evidence/build/lanes/<lane>/ one <ITEM>.json per item a parallel lane accepts (the work-item record shape)
candidates/<owner>__<name>/<revision>/   sealed candidate bundles (README_CONTRACT.md §7)
candidates/<owner>__<name>/CURRENT       pointer file naming the current revision
tests/                       mirrors src/repository_presenter/ package for package (see §3)
  fixtures/oracles/           development-only fixtures and oracles (FIXTURE_OR_ORACLE_ONLY)
  fixtures/readme_only/      README-only placeholder repository (the non-processable negative control)
.github/workflows/           ci.yml now; monitor.yml, present.yml, propose.yml from G4
tools/                        owner/reviewer tooling (tools/README.md) - supervises the loop and lanes from outside; never imported by src/, never touched by the loop or a lane, never read for an acceptance predicate
  reviewer/                   reviewer_check.py, stop_monitor.py, timestamp_monitor.py, unblock_monitor.py, research_edit.py (reusable governance-edit helpers), procedure.md; .local/ gitignored (state, never portfolio content)
  census/                     portfolio_census.py (planning-time only); .local/ gitignored (clone scratch space)
runs/                        disposable clones and run output (gitignored, never committed)
```

A concern gets a flat module (`core/identity.py`) when it is one cohesive file, and a subpackage
(`core/llm/`) when a gate's work item will add more than one file to it. Do not create a subpackage
for a single file, and do not let a flat module grow past what one work item's scope justifies —
split it into a subpackage instead of letting it become a god-module.

### 2.1 Extraction and platform independence

`extractors/platforms/<ecosystem>.py` depends only on `core/` and its own module; it never imports
another ecosystem's module or anything under `investigation/`, `reconciliation/`, `composition/`, or
`review/`. `extractors/platforms/registry.py` is the only file allowed to import more than one
ecosystem module, and only to register them; an unregistered ecosystem fails closed. Every stage
after facts consumes `facts.json` only — no later stage imports an extractor module directly. Each
platform module's tests live and pass in isolation from every other platform's; adding a new
ecosystem changes only its own file and its own test — registration is discovered by module name
from G4-W10 on (`platforms/<ecosystem>.py` exposes `PLUGIN`; until then, one registration line).
`RESEARCH_AND_GUIDELINES.md`
§7.4 records why, including what the legacy `ecosystems/registry.py` already got right.

Code pulled from a reuse source that stays close to its origin lives under
`extractors/surface/_vendor/<source>/`, reached only through a typed façade beside it and changed
only by a patch its file record names (§29.6 E2). `mypy` and `ruff` overrides are confined to that
directory, nothing outside it imports a vendored module directly, and no sibling checkout is ever
imported at runtime — the vendored copy is the only copy this repository runs.

## 3. Tests mirror source

`tests/<path>/test_<module>.py` mirrors `src/repository_presenter/<path>/<module>.py` exactly, so
any module's tests are found by mirroring its path, never by searching. `tests/fixtures/oracles/`
holds `FIXTURE_OR_ORACLE_ONLY` assets only, named after their manifest `destination_area`. Shared
test helpers stay in `tests/conftest.py` and `tests/support.py`, already established at G0; do not
create a second helper module doing the same job under a different name. A repository-wide
invariant that belongs to no single module lives in a flat `tests/test_<invariant>.py`
(`test_path_budget.py`, `test_schemas.py`, `test_cursor.py`, `test_control_plane.py`,
`test_routing_fields.py`); that is the
only exception to mirroring, and it holds the whole tree to one rule.

## 4. Naming

`snake_case` modules and packages, matching the manifest's `destination_area` spelling exactly when
a file is pulled. No file is named `utils.py`, `helpers.py`, `common.py`, or `misc.py`; a module
name states what it does. One class of responsibility per file: a work item that finds itself
adding an unrelated second concern to an existing file splits it out instead.

## 5. What never appears

No file at the repository root beyond what G0 already established
(`AGENTS.md`, `README.md`, `LICENSE`, `pyproject.toml`, `requirements-lock.txt`, `.gitignore`,
`.gitattributes`, `.env.example`). No duplicate module solving one concern twice under different
names (the CPL-03 finding in `migration/reuse-manifest.yaml` is the legacy example of this). No
scratch, draft, backup, or dated file anywhere in `src/`, `tests/`, `docs/`, or `schemas/`; a
superseded document is replaced in place, its history is Git's job. No tracked cache, build, or
virtual-environment artifact — `.gitignore` already covers `__pycache__/`, `.pytest_cache/`,
`.mypy_cache/`, `.ruff_cache/`, `.venv/`, `/build/`, `/dist/`, and `/runs/`; extend it in the same
commit that introduces a new tool producing local artifacts, before those artifacts are ever staged.
