# R1 Candidate Re-Seal Operations

## Context

This tracks the operational (non-mechanism) remaining work from the R1 re-seal sweep launched
after `planning.py`'s link-completeness fix (`29ebb7c`, 2026-09-08): re-verifying every candidate
whose sealed `plan.json`/`dispositions.json` predates that fix. It is deliberately separate from
`production-consistency-reassessment.md` (the RC-01..07 taskcards) — those fix the underlying
mechanism; this file tracks the concrete, per-candidate operational sequence and one outstanding
environment-restoration item, both real, both currently open or paused.

**This plan file was written during a plan-only phase** (instruction received 2026-09-08): no
further `present` invocations, commits, or file changes outside `plans/healing/` were made while
authoring this file, even though PDF-Java's first `present` run (already in flight before the
plan-only instruction arrived) completed with a result recorded below. Continuing OPS-01's runbook
is explicitly deferred until the plan-only restriction is lifted.

## Gap table

| Gap ID | Description | Taskcard ID |
|---|---|---|
| OPS-G1 | R1 re-seal sweep incomplete: Cells-Cpp done; 3D-Java correctly left unsealed (real defect, see RC-04); PDF-Java's first run done and clean, second confirmatory run not yet attempted; 3D-Python not yet attempted | OPS-01 |
| OPS-G2 | The primary interactive session's G5-W02 work-in-progress has been sitting in `git stash` (`stash@{0}`) since before the R1 sweep began, not yet restored or reverified | OPS-02 |
| OPS-G3 | Two candidates (`aspose-email-foss/Aspose.Email-FOSS-for-Python`, `aspose-3d-foss/Aspose.3D-FOSS-for-Java`) are correctly unsealed pending a real mechanism fix, not an operational retry | OPS-03 |

## Taskcards

### OPS-01 — Complete the R1 re-seal sweep (PDF-Java confirmatory run, 3D-Python)

- **Status:** In Progress
  - `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`: **Done** — sealed, proven byte-identical with
    zero provider calls, `test_sealed_bytes` green, committed (`06ae1f7`), pushed.
  - `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`: **In Progress, paused** — first `present` run
    completed 2026-09-08 with `verdict: ACCEPT`, `findings: 0`, and a pending update recorded on
    the manifest (`valid update available (factual)`, 26 provider calls). The confirmatory second
    run (needed for `seal.py`'s `_adopt_update` zero-provider-call proof) has **not** been executed
    — paused by this file's own plan-only authoring constraint, not by any blocker.
  - `aspose-3d-foss/Aspose.3D-FOSS-for-Java`: **Blocked**, correctly — see OPS-03; not part of this
    taskcard's remaining scope, tracked separately since its blocker is mechanism-level, not
    operational.
  - `aspose-email-foss/Aspose.Email-FOSS-for-Python`: **Blocked**, correctly — see OPS-03; same note.
  - 3D-Python (exact registry name to confirm at execution time, e.g.
    `aspose-3d-foss/Aspose.3D-FOSS-for-Python`): **Not Started**.
- **Gap linkage:** OPS-G1
- **Role:** Senior engineer / release operator. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Not a code fix — this is an operational runbook. Complete the sequential
    `present` → (if pending update) `present` again → full-suite verify → commit → push cycle for
    PDF-Java and 3D-Python, using the exact record-then-adopt pattern already proven on Cells-Cpp.
  - **Allowed paths:** `candidates/aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/**`,
    `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/**` (only the specific revision directory
    each `present` run touches) — **and nothing else**. No source, test, prompt, or schema file may
    change under this taskcard; if `present` surfaces a genuine new mechanism defect (as it did for
    3D-Java), that defect gets recorded per OPS-03's shape and handed to the matching RC-0N taskcard
    in `production-consistency-reassessment.md`, never patched inline here.
  - **Forbidden:** any `src/`, `tests/`, `prompts/`, `schemas/`, `plans/` (other than this file's own
    status updates), or `docs/` path; any other candidate's directory; running two `present`
    invocations concurrently (this project's own established discipline — a `state.yaml`
    candidate-counter race was found and is avoided by strict sequencing).
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter present --repo aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` (second run)
    reports `provider calls 0` and `update adopted`, not `valid update available`; same shape for
    3D-Python's two runs.
  - UI/Web/API: N/A.
  - Tests: `pytest tests/ -q --tb=no` (full suite, never `test_sealed_bytes.py` alone — isolation
    causes false ecosystem-registration `ConfigError`s, observed directly this session) shows only
    the pre-existing known failures after each candidate lands, and one fewer once that candidate's
    own `test_sealed_bytes` parametrization turns green.
  - Config respected end-to-end: the `dry_run`/`full` mode each registry entry specifies is
    respected automatically by `present`; no manual override.
  - No mock data in production paths: N/A — `present` always runs against the real pinned revision's
    clone; no mock mode exists for this stage.
- **Deliverables:**
  - Full file replacements: none new — the candidate bundle files (`README.md`, `plan.json`, etc.)
    are machinery output, not hand-authored deliverables.
  - New/updated tests: none new required — `test_sealed_bytes.py`'s existing parametrization over
    `candidates/*/*/` automatically covers each newly-adopted candidate.
  - Migration: N/A.
- **Hard rules:** never force a seal past a genuine review rejection; never hand-edit
  `dispositions.json`/`plan.json` to work around a finding (this project's own explicit, repeated
  rule this session — "fix the machinery, not the candidate"); strictly sequential `present` runs.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: N/A for this taskcard specifically — operational, not a mechanism change; 5/5
    here means *zero* shortcuts taken to reach a green state.
  - Test coverage: 5/5 = each landed candidate's `test_sealed_bytes` parametrization passes; full
    suite shows one fewer pre-existing-known-failure entry per candidate landed.
  - No regressions: 5/5 = no other candidate's files change as a side effect of this taskcard.
  - Determinism/reproducibility: 5/5 = the adoption proof itself (`byte_identical: true`,
    `provider_calls: 0`) is the determinism evidence, recorded on each candidate's own manifest.
  - Documentation/traceability: 5/5 = each candidate's commit message follows the established shape
    (what changed, root cause if any, proof it reproduces) matching the Cells-Cpp commit `06ae1f7`.
- **Now (runbook):**
  1. **Wait for this file's plan-only phase to end** before executing any step below.
  2. `git stash list` — confirm `stash@{0}` (the primary's WIP) is still present and untouched; do
     not let this taskcard's `git add`/`git commit` steps accidentally include stashed content —
     stage only the specific candidate directory each step names.
  3. PDF-Java: `./.venv/Scripts/repository-presenter.exe present --repo aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`
     (second, confirmatory run). Confirm `provider calls 0` and `update adopted` in the output.
  4. `git status --short candidates/aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/` — confirm the
     expected file set changed, nothing else.
  5. `pytest tests/ -q --tb=no` — confirm only pre-existing known failures remain (PDF-Java's own
     `test_sealed_bytes` entry now passing).
  6. Commit PDF-Java's candidate directory alone (matching commit `06ae1f7`'s shape); `git fetch`,
     confirm no divergence, push.
  7. Repeat steps 3–6 for 3D-Python, substituting its exact registry name and revision.
  8. If either repository's first `present` run (not yet executed for 3D-Python) instead returns
     `REJECT_PRESENTATION` with repair unable to resolve it: **do not proceed to a second run
     seeking adoption** (there is nothing pending to adopt) — instead follow OPS-03's shape to
     record it honestly, and hand the underlying defect to whichever RC-0N taskcard matches its
     root cause (trace it the same way 3D-Java's F08 was traced before assuming it is novel).

### OPS-02 — Restore and reverify the primary's stashed G5-W02 work

- **Status:** Not Started
- **Gap linkage:** OPS-G2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** `git stash pop` the primary interactive session's G5-W02 work-in-progress (stashed
    before the R1 re-seal sweep began, to get a clean tree for "official proof" runs, per this
    project's own rule against running proof in a checkout another process is modifying), then
    verify it is intact and its own tests still pass.
  - **Allowed paths:** whatever the stash itself touches — unknown until popped; this taskcard's
    job is to restore exactly that diff, not to editorialize it. If the pop conflicts with anything
    landed by RC-01 through RC-07 or OPS-01 in the meantime, resolve the conflict in favor of
    preserving both sides' intent (this project's established technique: temporarily remove the
    conflicting hunk, commit the other side, restore the stashed hunk exactly, verify).
  - **Forbidden:** discarding any part of the stashed work without the primary session's own
    confirmation; force-applying over a conflict without resolving it properly.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A unless the stashed work itself is CLI-facing (unknown until popped).
  - UI/Web/API: N/A.
  - Tests: whatever test file(s) the stashed diff touches must pass after the pop; if unknown,
    run the full suite (`pytest tests/ -q --tb=no`) and confirm no new failures beyond the
    pre-existing known set.
  - Config respected end-to-end: N/A unless the stash touches config.
  - No mock data in production paths: N/A.
- **Deliverables:**
  - N/A as a fixed list — the deliverable is "the stash is popped, clean, and verified," not a new
    file. If the pop is clean (no conflicts), this is a one-command taskcard.
- **Hard rules:** never `git stash drop` without confirming the pop succeeded and tests pass first;
  never resolve a conflict by silently preferring one side without checking both sides' intent.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: N/A — this is restoration, not a fix.
  - Test coverage: 5/5 = whatever the stash touches has its own passing tests post-pop.
  - No regressions: 5/5 = `git stash list` is empty afterward and `git status` shows exactly the
    restored diff, nothing extra, nothing missing.
  - Determinism/reproducibility: N/A.
  - Documentation/traceability: 5/5 = a short note (chat or `DECISION_LOG.md`, owner's preference)
    confirms what was restored and that it was verified, so this stash entry stops being an
    implicit, easy-to-forget liability.
- **Now (runbook):**
  1. Confirm OPS-01's candidate work for this pass is fully committed and pushed first (never pop a
     stash into a dirty tree — this project's own explicit rule).
  2. `git stash list` — confirm exactly one relevant entry (`stash@{0}`, "primary G5-W02 WIP").
  3. `git status` — confirm clean tree.
  4. `git stash pop`.
  5. If conflicts: resolve using the remove-hunk/commit/restore-hunk technique above; if clean:
     proceed directly.
  6. Run whichever tests the restored diff touches (or the full suite if unclear).
  7. Confirm with the primary session (or the owner) that the restored state matches what they
     expect before considering this closed.

### OPS-03 — Track candidates correctly left unsealed pending a mechanism fix

- **Status:** Blocked (by design — depends on RC-04 at minimum; possibly RC-02/RC-03/RC-06 for a
  fully clean resolution)
- **Gap linkage:** OPS-G3
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Not a fix — this taskcard exists to make explicit that
    `aspose-email-foss/Aspose.Email-FOSS-for-Python` and `aspose-3d-foss/Aspose.3D-FOSS-for-Java`
    remaining unsealed is the **correct, deliberate outcome** given the current state of the
    machinery, not an oversight or a stalled task. Both are already recorded in `docs/DECISION_LOG.md`
    (entries dated 2026-09-08). This taskcard's only "work" is re-attempting `present` for both once
    RC-04 (and, if RC-04 alone doesn't fully resolve them, RC-02/RC-03/RC-06 as diagnosed) lands.
  - **Allowed paths:** none until its dependency taskcard(s) land; then the same shape as OPS-01
    (only the two named candidates' own directories).
  - **Forbidden:** hand-editing either candidate's `dispositions.json`/`plan.json` to force a pass;
    re-running `present` speculatively hoping for a different non-deterministic roll (explicitly
    rejected this session as "manufacture acceptance by retrying until lucky" — re-running only
    makes sense once a mechanism fix genuinely changes the deterministic behavior involved).
- **Acceptance checks (customized for this repo):**
  - CLI: re-running `present` for each, after its dependency lands, shows either `verdict: ACCEPT`
    (proceed through OPS-01's shape to seal) or an honest, still-unresolved rejection with a newly
    or differently diagnosed cause (loop back to whichever RC-0N taskcard matches).
  - Tests: `test_sealed_bytes` for each turns green only once actually sealed — do not mark this
    taskcard "Done" based on a clean review verdict alone; require the full record-then-adopt proof.
  - Config respected end-to-end / No mock data: N/A.
- **Deliverables:** an updated `DECISION_LOG.md` entry for each candidate once re-attempted,
  recording the outcome either way (this mirrors SR-01's own precedent of keeping records current
  rather than letting them go stale).
- **Hard rules:** same as OPS-01 — never force, never hand-patch, strictly sequential.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the candidate seals because the actual mechanism defect is fixed, not
    because of a lucky non-deterministic roll or a workaround.
  - Test coverage / No regressions / Determinism: same bar as OPS-01 once re-attempted.
  - Documentation/traceability: 5/5 = both `DECISION_LOG.md` entries are updated, not left stating
    a now-stale "stays unsealed" as if it were still current.
- **Now (runbook):**
  1. Do nothing until RC-04 (`production-consistency-reassessment.md`) reaches "Done" and has been
     verified against these exact two candidates per RC-04's own runbook step 5–6 (which already
     covers re-running `present` for both — this taskcard's "runbook" is intentionally that one,
     not a duplicate).
  2. If RC-04 alone resolves both: proceed through OPS-01's seal/verify/commit/push shape.
  3. If either still fails: trace the new/remaining cause precisely (do not assume it's the same
     class without checking — Cells-Cpp proved the same *symptom* shape does not always share the
     same review outcome); file it against the matching RC-0N taskcard, or add a new one to
     `production-consistency-reassessment.md` if it's genuinely novel.
  4. Update both `DECISION_LOG.md` entries with the final outcome.
