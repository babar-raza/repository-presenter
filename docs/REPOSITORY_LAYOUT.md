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
    grammars.py             tree-sitter parsers built from pinned per-language wheels; a missing grammar is a typed refusal, never a download
    facts.py                typed fact records and the facts.json writer (the extraction boundary)
    examples.py             shared example-verification types and the receipts writer
    package_registry.py     the registry-reading type and per-ecosystem observer lookup that stages after facts use without importing an extractor
    probes.py               what a live read observed - status, timing, volatile reading - kept out of the hashed facts
    noop_proof.py           the no-op proof, measured: process identity, the rerun's provider calls counted from its own ledger, and bundle-totals-versus-ledger reconciliation (the `verify-noop-proof` gate)
    execution.py            bounded secret-free execution of repository examples
    toolchains.py           machine toolchain resolution (registry, install search, per-tool PATH precedence) and the environment toolchain fingerprint
    config.py               gateway configuration from the process environment (a subpackage once G4 adds GitHub App configuration)
    git_safety/              push-neutered clone, safety checks
    snapshot/                immutable repository snapshot capture
    github/                  read and write GitHub API clients
      client.py               read-only GET /repos/{owner}/{repo} (workstream 2 Phase 0); no write call anywhere yet
      token_provenance.py     refuses a write token that is not an installation token scoped to exactly the target repository, and a pull request not performed by the Repository Presenter App (id 5092474) - the write path's credential check
      read_client.py          read-only file/tree/default-branch-head reads (workstream 3 redetection); no write call anywhere yet
    preflight.py            fail-closed LLM gateway check recording the model catalog (the GitHub check joins it at G4)
    llm/                     transport, ledger, call schema, prompt registry, prompt hygiene
      fallback.py              model fallback chains: the one FALLBACK_CHAINS table, per-run availability probes, one fixed effective model per route (owner directive, 2026-10-04)
    state/                   repository/proposal records, backend, migrations
    evidence/                evidence writer and manifest schema
    registry/                registry loader, revision store
      write_gate.py            the one write gate every write path calls: listed, active and mode `full`, else a typed refusal; yields the WritePermit the effect requires
    authorization/           effect-authorization contracts
      proposal.py              the persisted README-proposal authorization record (G6-W02): repository, candidate hash, source revision, base and presenter branch, approver, window, explicit re-proposal list; loaded from `ops/proposal-authorizations/` and re-validated against the candidate, never agent-produced
      record_provenance.py     proves a record was merged to origin/main before the commit the consuming run was triggered at, so a run cannot authorize itself
      refusals.py              the typed refusal codes (and WriteRefusedError) every write path reports
    candidates.py            sealed-bundle counting (already built); ready_revision() is the one proposal-time question: is CURRENT a verified READY_FOR_PROPOSAL bundle
    sealing_plan.py          the unattended sealing run's plan (G7-W06 work item 3): DRIFTED-only, enabled, registry-listed selection, cap 3, sorted; qwen3-next-only guard; reads the drift monitor's output through its file contract alone
    secrets.py               secret-canary scanning (already built)
  components/issues/         workstream 3 (docs/investigations/03-issue-tracking.md); tracks confirmed upstream defects and, per PRODUCTION_ROADMAP.md's WS2 ruling, missing community/contribution/licensing/security files as findings; never README-specific; read+local-JSON only except file.py's own gated write
    model.py                  the typed shape of one handoff artifact
    ledger.py                  the dedup ledger: a read layer over the handoff artifacts committed under evidence/upstream-defects/
    redetect.py                re-detection pass: re-evaluate a handoff's triggering_check at the repository's current revision
    draft.py                    auto-drafts a HANDOFF_PENDING artifact the moment cli.py::run_present proves a genuine EXTRACTING-stage defect
    file.py                     Phase 3 gated write: files a HANDOFF_PENDING handoff as a real GitHub issue, only past the kill switch, a write token, a per-handoff owner approval record and a fresh recheck
    readiness.py                 filing readiness per handoff and the owner's batch approval: lists every handoff's blockers (registry gate, replayable recheck, re-verification, approval) and emits approval record files to a scratch directory only (cli.py issue-readiness)
    approval.py                 per-handoff owner approval: record format, evidence digest, and the git-ref store that verifies it (file.py refuses without it)
  components/readme/         README-specific behavior only
    extractors/
      platforms/              one plugin per ecosystem (python.py first)
        python_format_declarations.py  static format declarations and plugin registrations, read from syntax trees (RESEARCH §22.1, §26)
      examples/                example verification
    investigation/            repository_investigation job wiring
    reconciliation/           source_reconciliation job wiring, dispositions
    composition/               presentation_planning, section_authoring, renderer
      placement.py             where each inherited unit renders, under the three placement rules
      policy.py                the planning policy: capability, hub, line, and Aspose-link ceilings
      link_budget.py           Aspose-link ceilings derived per document, domain, and surface slot (plans/idea.md), or configured; the plan trim and BC-06 both read it
    components/                 semantic-shell template components (README_CONTRACT.md §2)
      ecosystems.py            per-ecosystem presentation knowledge: package registry names
      terminology.py           the governed technical-terminology registry and heading-case grammar: the one owner of canonical abbreviations (PS, PDF, glTF, npm) and title case
      glance.py                the At a Glance label-geometry policy: one common wrap width, at most three lines
    validation/
      registry.py              versioned check registry
      links/                   link resolution
        rules.py                the pure rules BC-06 and BC-07 call: derived link ceilings, the Enterprise Edition anchor, the badge row's order and support
    review/
      independent/             independent_review job wiring
      acceptance/               30-point criterion profile (G2)
    repair/
      targeted.py              targeted_repair job wiring: defects, fingerprints, repairs.json
      rounds.py                one composition round (S3 to S10) and the bounded repair loop
    bundle/
      seal.py                  the sealed bundle, dependencies.json, and the no-op proof (S12)
      evaluation.py            dependency evaluation: changed inputs and the stage they reopen
      invalidation.py          typed invalidation scopes: scope -> stage and state tables, and the routing (STATE_MACHINE.md §9)
      dry_run.py               read-only dry run: every CURRENT bundle's routing under the running code, and held updates
      portfolio.py             plans/idea.md's seven separated portfolio counts and the one-bucket-per-entry partition `status` prints (pure read; predicates defined in its docstring)
    evidence/
      facts/                    fact extraction (README_CONTRACT.md §3 S2)
        product_pages.py        live product-page facts: Enterprise target, homepage, banner (RESEARCH §20)
        assets.py               build and test assets from the tree, and the build-status badge target (a push-triggered build or test workflow read from the clone)
  components/metadata/       workstream 2 (docs/investigations/02-repo-metadata-community-files.md §5); never README-specific
    capture.py                Phase 0: read GitHub's observed description/homepage/topics via core/github, write the typed evidence artifact
    proposal.py                Phase 1: derive description/topics/homepage from already-verified facts (identity/license/link_target), diff against Phase 0's observation
    preservation.py          deterministic keep-vs-replace rules for maintainer-authored description/homepage and the topic merge (no LLM); proposal.py and apply.py consume it
    apply.py                  Phase 2: PATCH/PUT that diff to GitHub - gated behind an explicit owner-controlled authorization signal plus a write-scoped token distinct from the read-only GH_TOKEN; unset in this project's own environment today, so built and tested, never fired (docs/DECISION_LOG.md)
  components/propose/        G6-W02 (docs/EXECUTION_STATE_MACHINE.md G6; docs/STATE_MACHINE.md §§11-12); the README-proposal PR effect, never README-content-specific itself (the candidate text is only an input)
    effect.py                  the gated write: create/update the one stable presenter branch and its one open PR - gated behind an owner-controlled authorization signal, a write-scoped GH_PROPOSAL_WRITE_TOKEN distinct from GH_TOKEN/GH_METADATA_WRITE_TOKEN/GH_ISSUES_WRITE_TOKEN, core/authorization/proposal.py's own payload re-validation, and a source-revision recheck immediately before the write; unset in this project's own environment today, so built and tested, never fired (docs/DECISION_LOG.md)
  components/candidates_publish/  G7-W14 (docs/EXECUTION_STATE_MACHINE.md G7 work item 14); keeps this control repository's own committed candidates/<slug>/ tree current after a hosted present.yml run re-seals a repository, never README-content-specific itself
    effect.py                  the gated write: commit the sealed bundle to a dedicated branch and open/update the one pull request that carries it - gated behind REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED, a write-scoped GH_CANDIDATES_WRITE_TOKEN (this job's own ambient GITHUB_TOKEN under a distinct name - no App installation token, since the write target is this repository itself), and core/github/token_provenance.py's verify_repository_token; idempotent by construction (the target branch's own currently-committed revision is read before anything is written)
    git_ops.py                 the real local git plumbing (branch fetch/checkout, stage-and-commit, push) the effect above composes, built on core/git_safety/git.py's run_git/github_https_auth_env

  components/monitor/        G7-W06 (docs/EXECUTION_STATE_MACHINE.md G7 work item 3); scheduled read-only drift observation: each enabled registry repository's upstream default-branch head against its CURRENT sealed bundle's revision (CURRENT/DRIFTED/NO_BUNDLE/UNREACHABLE); never README-specific; no provider call, no write
    drift.py                  the observation and its evidence document (runs/monitor/drift.json); the `repository-presenter monitor` command (cli.py) is its only caller

prompts/                     one governed manifest per job (README_CONTRACT.md §3), flat, six files at G1
schemas/                     JSON Schemas for the cursor, manifest, candidate bundle, prompt manifests
data/                        registry, link, family, and priority data pulled per migration/reuse-manifest.yaml
profiles/                    per-repository and per-family policy overlays (ADAPT_AS_PLUGIN)
docs/                        authority documents (this tree's siblings); DECISION_LOG.md is the project-wide append-only decision log (RESEARCH_AND_GUIDELINES.md §31, split out 2026-09-08); RESEARCH_<LANE>.md (RESEARCH_LANE_B.md, _C, _D) is a lane's own append-only decision log in the same shape (RESEARCH §28.12); CREDENTIAL_ROTATION_RUNBOOK.md is the per-secret rotation/rollback/App-permission-audit runbook (G7-W04)
plans/                       plans/idea.md, the human product authority
project/                     state.yaml, loop-prompt.md; loop-prompt-lane.md (the generic lane prompt; loop-prompt-lane-b.md is a pointer to it) and lanes/<lane>.yaml (each lane's cursor, RESEARCH §28.12); portfolio-census.json (owner planning data, RESEARCH §28.11 — never a runtime input)
migration/                   reuse-manifest.yaml
evidence/build/<gate-id>/    one manifest.json per accepted gate (EXECUTION_STATE_MACHINE.md §10)
evidence/build/lanes/<lane>/ one <ITEM>.json per item a parallel lane accepts (the work-item record shape)
evidence/upstream-defects/<owner>__<name>/<fingerprint>.json  one evidence-backed handoff per confirmed upstream defect (docs/investigations/03-issue-tracking.md §5), read-only boundary - no GitHub write capability; exists for a repository with no candidates/ bundle at all
evidence/upstream-defects/reverification.json  the independent live-head re-verification of each handoff (verdict CONFIRMED / NOT_A_DEFECT / FIXED_OR_CHANGED / NOT_VERIFIABLE, bound to the handoff's evidence digest); flags a handoff without rewriting its claim; read by components/issues/readiness.py, which refuses to emit an approval for anything not CONFIRMED and unchanged since
ops/issue_approvals/<handoff-id>.json  one owner approval per upstream-defect handoff the scheduled workflow may file as an issue (components/issues/approval.py); committed by the owner only, never by a workflow; README.md there explains the owner step
ops/issue_close_approvals/<handoff-id>.json  one owner approval per filed upstream issue the scheduled workflow may close: the exact issue number, the close reason, an expiry (components/issues/close_approval.py); committed by the owner only, never by a workflow, and never interchangeable with a filing approval; README.md there explains the owner step
evidence/sbom/requirements-lock.cdx.json  committed CycloneDX SBOM for this project's own resolved runtime+dev environment (requirements-lock.txt), regenerated by `pip-audit -r requirements-lock.txt -f cyclonedx-json` (G7-W02); CI regenerates and uploads a fresh copy as a workflow artifact on every run (the committed copy is a point-in-time snapshot, not re-verified for drift against the lock on every push - only its own component list, which `pip-audit` derives deterministically from the lock's pinned versions, matters)
evidence/g6-w02/proof-readme-v1.md  the disposable-target README input (G6-W02 live proof) passed to `repository-presenter propose --readme-file` in propose.yml's own dispatch; a fixed proof fixture for the write path, never a product candidate, and never read by any product stage. Its redacted run record lives beside it as evidence/g6-w02/LIVE_PROOF.md
candidates/<owner>__<name>/<revision>/   sealed candidate bundles (README_CONTRACT.md §7)
candidates/<owner>__<name>/CURRENT       pointer file naming the current revision
ops/proposal-authorizations/  one reviewed JSON record per authorized README proposal (`repository-presenter draft-proposal-authorization` writes it; a person merges it through a pull request before the propose run is triggered); `propose --propose` refuses without one (docs/DECISION_LOG.md 2026-10-05)
tests/                       mirrors src/repository_presenter/ package for package (see §3)
  fixtures/oracles/           development-only fixtures and oracles (FIXTURE_OR_ORACLE_ONLY)
  fixtures/readme_only/      README-only placeholder repository (the non-processable negative control)
.github/workflows/           ci.yml now; monitor.yml, present.yml, propose.yml from G4
scripts/                     ci_check.sh (the local CI-equivalent; see its own header for exactly which ci.yml steps it mirrors and which it deliberately omits), ci_output_dir.sh (sourced by ci_check.sh: a private mktemp -d output directory per invocation, removed by an EXIT trap, so concurrent runs sharing one tools venv never overwrite each other's SBOM/audit files), check_import_root.py (ci_check.sh's preflight: fails when `import repository_presenter` resolves outside this checkout's src/, e.g. a worktree sharing a venv), check_lock_drift.sh (G7-W02: regenerates requirements-lock.txt in a scratch copy and diffs against the committed one, CI-only - needs network the same way ci.yml's own "Install from the lock" step does), sync_main.sh (fast-forwards local main to origin/main only when safe; typed refusals), new_worktree.sh (the one way to start work: a worktree under runs/wt from a freshly fetched origin/main, shared .venv linked), check_staleness.sh (ci_check.sh's warn-only preflight: HEAD more than 20 commits behind origin/main); all three are described in section 6, and tests/test_worktree_scripts.py drives them against temporary git repositories
tools/                        owner/reviewer tooling (tools/README.md) - supervises the loop and lanes from outside; never imported by src/, never touched by the loop or a lane, never read for an acceptance predicate
  reviewer/                   reviewer_check.py, stop_monitor.py, timestamp_monitor.py, unblock_monitor.py, research_edit.py (reusable governance-edit helpers), procedure.md; .local/ gitignored (state, never portfolio content)
  census/                     portfolio_census.py (planning-time only); .local/ gitignored (clone scratch space)
  discovery/                  portfolio_discovery.py (read-only aspose-<family>-foss org/repo scan vs. data/registry.json, report-only, never writes the registry) and its tests
  research_sweep/             proposal_sweep.py (read-only sweep of docs/RESEARCH_LANE_*.md for PROPOSAL findings not yet cross-referenced in docs/DECISION_LOG.md; docs/investigations/05-production-autonomy.md class H, docs/PRODUCTION_ROADMAP.md WS5's queued sweep item) and its tests
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

## 6. Branching and worktrees

`origin/main` on GitHub is the only moving main: pushes and PR merges never update a local `main`,
and the shared `.venv`'s editable install points at the main checkout's `src/`. Anything branched
from a stale local `main`, or importing from the main checkout, runs stale code (observed
2026-10-05: false version-mismatch test failures in a worktree). The workflow that prevents it:

1. **Fetch first, branch from `origin/main`.** Start every piece of work with
   `scripts/new_worktree.sh <name> <branch>`: it runs `git fetch origin`, then
   `git worktree add -b <branch> runs/wt/<name> origin/main`, links the shared `.venv` (a directory
   junction on Windows, a symlink elsewhere), and prints the three settings the shell needs:
   `PYTHONPATH=<worktree>/src` (without it the shared venv imports the main checkout), `CI_TOOLS_VENV`
   and Git for Windows' `bash` first on `PATH` (the WSL `bash.exe` in System32 fails here). It refuses
   an existing branch, a taken path, an odd name, and a checkout on `C:` (override only for tests:
   `NEW_WORKTREE_FORBIDDEN_DRIVES`).
2. **Never work in the main checkout.** It exists to be fast-forwarded and to own `.git`; commits,
   edits and test runs happen in a worktree. Remove a worktree's `.venv` junction with `rmdir`
   before `git worktree remove`, never a recursive delete through it.
3. **Keep local `main` current with `scripts/sync_main.sh`** (`--check` only reports). It runs
   `git fetch origin --prune`, reports behind/ahead, and fast-forwards with `git merge --ff-only`
   (`git fetch origin main:main` when main is checked out nowhere) only when safe. It refuses, with a
   typed one-line reason and no change, on uncommitted tracked changes (`DIRTY`), local commits not
   on `origin/main` (`DIVERGED`), a merge/rebase/cherry-pick/revert/bisect in progress
   (`OP_IN_PROGRESS`) and untracked files the update would overwrite (`UNTRACKED_CLASH`). It cannot see
   other processes: do not run it while something tests from the main checkout.
4. **A stale base is warned about where every push passes.** `scripts/ci_check.sh` runs
   `scripts/check_staleness.sh`, which prints a warning (never a failure) when `HEAD` is more than 20
   commits behind `origin/main` (`RP_STALE_COMMITS` overrides; main took 59 commits on the busiest
   recent day, so 20 is about a working session of other people's merges, and a lower bar would warn
   on every long-lived branch). `scripts/check_import_root.py` still fails the run when the import
   itself resolves outside the checkout.

On Windows run the scripts with Git for Windows' bash, e.g.
`& "C:\Program Files\Git\bin\bash.exe" scripts/new_worktree.sh <name> <branch>`; no PowerShell wrapper
exists because a wrapper could only repeat that line.
