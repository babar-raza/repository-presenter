# Self-Review Remediation — Documentation Split & Tooling Discipline

## Context

On 2026-09-08 the owner/reviewer split `docs/RESEARCH_AND_GUIDELINES.md` (5,599 lines / 524KB) by
moving its append-only §31 decision log to a new `docs/DECISION_LOG.md`, and closed a governance
tooling gap (ten near-identical scratchpad throwaway scripts for the "append a dated entry" shape)
by adding `append_entry()` to `tools/reviewer/research_edit.py`. A subsequent self-review of that
work (same day) found two real follow-up gaps, both since fixed, and confirmed one item explicitly
deferred by owner choice. This file converts that self-review into tracked taskcards so nothing
found during the review is only recorded in chat history.

Source of truth for the underlying facts: `docs/DECISION_LOG.md` entries dated 2026-09-08 (Cells-Cpp,
3D-Java) and commits `103cb51`, `a2a39b8`, `fcc8fcd`, `0343c2c`.

No `self_review:` YAML block exists for this work; this plan parses the prose record above and the
commit history directly.

## Gap table

| Gap ID | Description | Taskcard ID |
|---|---|---|
| SR-G1 | `DECISION_LOG.md` was undiscoverable from `RESEARCH_AND_GUIDELINES.md` §1/§15's own reading-order lists and from `AGENTS.md`'s session-start reading order | SR-01 |
| SR-G2 | `tools/reviewer/research_edit.py` gained `append_entry()` but no test file of its own exists under `tools/` to guard it against regression | SR-02 |
| SR-G3 | `RESEARCH_AND_GUIDELINES.md` still carries §1–30 (~301KB); a further split (§22–30 → a new file) was proposed and explicitly deferred by owner choice ("Phase 1 only") | SR-03 |

## Taskcards

### SR-01 — Restore `DECISION_LOG.md` discoverability in every reading-order list

- **Status:** Done (commit `0343c2c`)
- **Gap linkage:** SR-G1
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Add `docs/DECISION_LOG.md` to every governance reading-order list that described "the
    project's document set" without mentioning it, so a new agent following the list exactly as
    written does not miss the decision history that moved out of `RESEARCH_AND_GUIDELINES.md`.
  - **Allowed paths:** `docs/RESEARCH_AND_GUIDELINES.md`, `AGENTS.md`
  - **Forbidden:** any other file/path — no `src/`, `tests/`, `prompts/`, `schemas/`, or other
    `docs/*.md` files.
- **Acceptance checks (customized for this repo):**
  - CLI: N/A — no CLI surface reads this prose.
  - UI/Web/API: N/A — repository-presenter has no UI, web, or API surface; it is a CLI tool.
  - Tests: `tests/test_queue_agreement.py` and `tests/test_grammar_pins.py` (the two tests that
    parse `RESEARCH_AND_GUIDELINES.md`'s structure) pass unchanged.
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A — no runtime code touched.
- **Deliverables:**
  - Full file replacements: N/A by design — these are targeted prose insertions (one bullet in §1,
    one line in §15, one line in `AGENTS.md`), not whole-file rewrites; a full replacement of a
    5,600-line document for a 3-line change would itself be the kind of unreviewable diff this
    project's own commit discipline rejects.
  - New/updated tests: none required — this is a discoverability fix in prose, not behavior; no
    test should assert reading-order-list prose content verbatim (that would make the list rigid
    for no safety benefit).
  - Migration: N/A — no schema/contract change.
- **Hard rules:** Only "keep code/docs/tests in sync" applies, and is exactly what this closes.
  All other hard rules (signatures, network, entrypoint parity, mock/live, determinism, new deps)
  are N/A — no code changed.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the reading-order lists themselves name the new file, not a changelog
    entry that merely claims they do (verified by re-reading both files after the edit, not by
    trusting the diff summary).
  - Test coverage: 5/5 = N/A for new tests; 5/5 for regression = the two structural tests above
    both re-run green post-edit.
  - No regressions: 5/5 = full existing suite unaffected (only two files touched, both prose).
  - Determinism/reproducibility: N/A — no runtime behavior.
  - Documentation/traceability: 5/5 = the commit message states the exact gap and why it matters;
    this taskcard is the second, durable record of the same fact.
- **Now (runbook):**
  1. `git show 0343c2c --stat` — confirm exactly `docs/RESEARCH_AND_GUIDELINES.md` and `AGENTS.md`
     changed, nothing else.
  2. `grep -n "DECISION_LOG" docs/RESEARCH_AND_GUIDELINES.md AGENTS.md` — confirm both files
     mention it.
  3. `./.venv/Scripts/python.exe -m pytest tests/test_queue_agreement.py tests/test_grammar_pins.py -q`
     — confirm green.
  4. Done. No further action; this taskcard exists for traceability, not remaining work.

### SR-02 — Add regression tests for `research_edit.py`'s `append_entry`

- **Status:** In Progress — the helper itself is done and live-verified; a committed test file is
  the missing deliverable this taskcard closes.
- **Gap linkage:** SR-G2
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Add `tools/reviewer/test_research_edit.py` covering `append_entry`, `safe_replace`,
    and `load_yaml_block` against `tmp_path` fixtures (never the real `docs/*.md` files), so a
    future edit to this tool cannot silently break the blank-line-separator or `newline="\n"`
    behavior without a test failing.
  - **Allowed paths:** `tools/reviewer/test_research_edit.py` (new)
  - **Forbidden:** `tools/reviewer/research_edit.py` itself (already correct and live-verified;
    this taskcard adds a test harness around it, it does not change its behavior), and everything
    outside `tools/reviewer/`.
- **Acceptance checks (customized for this repo):**
  - CLI: `python tools/reviewer/test_research_edit.py` is not how tests run in this repo; use
    `pytest tools/reviewer/test_research_edit.py -q` directly (this file lives outside `tests/` by
    design — `tools/` is owner/reviewer tooling per `tools/README.md`'s boundary, never imported
    by `src/` or collected by the project's main CI test run unless explicitly pointed at it).
  - UI/Web/API: N/A.
  - Tests: the new file itself is the acceptance check — it must include (a) a happy-path append
    onto an existing multi-entry file, (b) a regression case for a file with no trailing newline,
    (c) a failure-path case for `safe_replace` when the anchor count does not match
    `expected_count` (asserts `AssertionError`, not a silent no-op), (d) a failure-path case for
    `load_yaml_block` when the YAML block is malformed (asserts it raises before anything is
    written — the tool's own known write-before-validate risk, see `research_edit.py`'s
    `safe_replace` docstring).
  - Config respected end-to-end: N/A.
  - No mock data in production paths: N/A — this tool is never in a production path.
- **Deliverables:**
  - Full file replacement: `tools/reviewer/test_research_edit.py` (new, complete, no stubs).
  - New/updated tests: this taskcard's entire deliverable *is* the new tests; at minimum 4 cases
    (see above), each independent and running against `tmp_path`, never `docs/RESEARCH_AND_GUIDELINES.md`
    or `docs/DECISION_LOG.md` directly (a test that mutates the real governance docs is itself a bug).
  - Migration: N/A.
- **Hard rules:** no new deps (use `pytest`, already a dependency); no network; determinism is
  automatic (pure file I/O against `tmp_path`, no ordering sensitivity).
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = the specific write-before-validate risk named in the tool's own docstring
    has an explicit regression test, not just a comment warning about it.
  - Test coverage: 5/5 = all four cases above present and each fails without the corresponding
    correct behavior (verify by temporarily reverting `research_edit.py` and confirming the new
    tests fail, then restoring it).
  - No regressions: 5/5 = full suite (`pytest tests/ -q`) still shows only the pre-existing known
    failures; the new test file is additive.
  - Determinism/reproducibility: 5/5 = tests pass identically on repeated runs, no ordering or
    timing dependency.
  - Documentation/traceability: 5/5 = `tools/README.md`'s `research_edit.py` entry gains one line
    noting the test file exists and what it guards.
- **Now (runbook):**
  1. Write `tools/reviewer/test_research_edit.py` with the four cases above.
  2. `./.venv/Scripts/python.exe -m pytest tools/reviewer/test_research_edit.py -q` — confirm green.
  3. Temporarily comment out the `newline="\n"` argument in `append_entry`; re-run step 2; confirm
     the relevant test fails (proves the test actually guards the behavior); revert.
  4. `./.venv/Scripts/python.exe -m ruff check tools/reviewer/test_research_edit.py` — clean.
  5. Add the one-line mention to `tools/README.md`.
  6. `./.venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — confirm no new failures in the main
     suite (this file lives outside `tests/`, so it should not be collected by that run at all;
     confirm that too).
  7. Commit only the two files above; push.

### SR-03 — `RESEARCH_AND_GUIDELINES.md` Phase 2 split (§22–30) — deferred, optional

- **Status:** Not Started — explicitly deferred by owner decision on 2026-09-08 ("Phase 1 only").
  Tracked here so it is not forgotten, not because it is currently blocking anything.
- **Gap linkage:** SR-G3
- **Role:** Senior engineer. Drop-in, production-ready.
- **Scope (only this):**
  - **Fix:** Move §22–30 (~220KB, the point-in-time production-era design write-ups) out of
    `RESEARCH_AND_GUIDELINES.md` into a new `docs/PRODUCTION_HISTORY.md`, section numbers
    unchanged, and mechanically rewrite every `RESEARCH_AND_GUIDELINES.md section N` (N in 22–30)
    citation across the codebase to name the new file instead. Text moves byte-identical; this is
    a location change, never a content rewrite.
  - **Allowed paths:** `docs/RESEARCH_AND_GUIDELINES.md`, `docs/PRODUCTION_HISTORY.md` (new),
    `docs/REPOSITORY_LAYOUT.md`, every `src/`, `tests/`, `tools/`, `prompts/` file whose docstring
    or comment cites §22–§30 by filename (~90 files per the 2026-09-08 grep census — regenerate the
    exact list at execution time with
    `grep -rlE "RESEARCH_AND_GUIDELINES\.md.{0,20}section (2[2-9]|30)" src tests tools prompts`
    rather than trusting a stale hand-enumerated list).
  - **Forbidden:** changing any moved section's actual wording while relocating it; changing
    section numbers 22–30 (every bare `§27.2`-style reference across the ~90 files must keep
    resolving without being touched, exactly as the §31 split preserved bare `§31` references).
- **Acceptance checks (customized for this repo):**
  - CLI: `repository-presenter status` unaffected (no functional read of this file).
  - UI/Web/API: N/A.
  - Tests: `pytest tests/ -q` green with only the pre-existing known failures (3D-Python, Email-
    Python, PDF-Java `test_sealed_bytes` — see `production-consistency-reassessment.md`);
    `tests/test_queue_agreement.py` and `tests/test_grammar_pins.py` specifically re-verified since
    they parse this file's structure directly.
  - Config respected end-to-end: N/A.
  - No mock data: N/A.
- **Deliverables:**
  - A rewrite script under `tools/` (not a scratchpad throwaway — writing one to the OS scratchpad
    for this would repeat exactly the SR-G2 pattern) that (a) finds every citation, (b) rewrites
    the filename only, (c) prints every file it touched for review before commit. This script may
    be a one-shot migration kept afterward as a record (precedent: `tools/census/portfolio_census.py`
    is documented as "one-shot planning data-gathering, not ongoing supervision" and stays).
  - New/updated tests: none new required beyond the existing structural tests re-passing; this is
    a pure relocation.
  - Migration: N/A (no schema/contract).
- **Hard rules:** no content loss — diff the concatenation of (new `RESEARCH_AND_GUIDELINES.md` §1–21)
  + (new `docs/PRODUCTION_HISTORY.md` §22–30 body) against the original file's §1–30 and confirm
  byte-identical modulo the relocation boundary and forwarding pointers.
- **Review dimensions (5/5 = ):**
  - Root-cause fix: 5/5 = `RESEARCH_AND_GUIDELINES.md` measurably shrinks (~301KB → ~75KB) with
    zero citations broken.
  - Test coverage: 5/5 = the rewrite script's own dry-run output is reviewed before any commit;
    the full suite is the regression gate.
  - No regressions: 5/5 = only the pre-existing known `test_sealed_bytes` failures remain.
  - Determinism/reproducibility: 5/5 = re-running the rewrite script on an already-migrated tree is
    a no-op (idempotent).
  - Documentation/traceability: 5/5 = `docs/REPOSITORY_LAYOUT.md` and a `DECISION_LOG.md` entry
    both record the split, mirroring the §31 split's own record.
- **Now (runbook):**
  1. **Do not start without an explicit owner go-ahead** — this item is deferred by choice, not
     blocked by a dependency; re-litigating that choice is the owner's call, not a default action.
  2. If approved: `grep -rlE "RESEARCH_AND_GUIDELINES\.md.{0,20}section (2[2-9]|30)" src tests tools prompts > /tmp/sr03_touchlist.txt` and review the count against the 2026-09-08 census (~130 citations, ~90 files) before proceeding — a large drift from that number means the codebase changed enough that the plan should be re-costed, not blindly executed.
  3. Write and dry-run the rewrite script; review its printed touch-list.
  4. Apply; `pytest tests/ -q --tb=no`; confirm only the known failures remain.
  5. Update `docs/REPOSITORY_LAYOUT.md`; append a `DECISION_LOG.md` entry.
  6. Commit in the same two-commit shape as the §31 split (content move, then any tooling script)
     for reviewability; push.
