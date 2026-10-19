# Plan audit A - governance and executability of G3-W12 (commit 1aafd9dc, branch wt/laner-plan)

Auditor lens: an autonomous executor starts tomorrow, reads AGENTS.md "Read Before Acting", then runs `project/loop-prompt-ship.md`.
Read-only audit. Paths are relative to the worktree `runs/wt/laner-plan`. Line numbers are at 1aafd9dc.
Edits to a queue entry's `purpose` must be applied byte-identically to `project/state.yaml` (G3-W12 entry, line 73-76) AND `docs/RESEARCH_AND_GUIDELINES.md` section 27.9 (the YAML block after line 2211); `tests/test_queue_agreement.py::test_every_queued_item_carries_section_27_9s_text_verbatim` enforces it.

## 0. Test and tool results

| Check | Result |
|---|---|
| `pytest tests/test_governance_consistency.py tests/test_queue_agreement.py tests/test_register_integrity.py tests/test_schemas.py tests/test_cursor.py tests/test_path_budget.py tests/test_plan_lint.py tests/test_version_bump_discipline.py tests/test_no_bump_check.py tests/test_routing_fields.py -q` | all pass (4 xfail-style marks, 0 failures) |
| `pytest ... tests/test_cli.py` (the full 8-file set the brief named) | exit 0, all pass |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 826 files already formatted |
| Line budgets | AGENTS.md 207/210; ESM 510/520 (10 spare); 8 gates (`grep -c "^## G[0-9]"` = 8) |
| Mirror of purpose text | state.yaml and 27.9 byte-equal (test green) |

Conclusion: the repository's own tests do not see any finding below. All of them are semantic or procedural, so none is caught by CI.

## 1. Findings

Severity counts: Critical 2, High 8, Medium 9, Low 3 (22 findings).

| ID | Sev | Finding (short) |
|---|---|---|
| A01 | Critical | G3-W12 has no activation path and the G3-W11 / G3-W12 / ship-loop chain is circular |
| A02 | Critical | Card C3's governed bumps are barred by G7-W22 and by C3's own bump rule, yet `test_version_bump_discipline` forces them |
| A03 | High | C1 is placed in `tools/`, which the loop may never touch or read for a predicate |
| A04 | High | C1 cannot implement M4 to M8 "from bundle files" before C2/C6/C7 exist; ratchet scope undefined |
| A05 | High | D8 is recorded as an owner decision beyond the owner message; the 2026-10-15 direction it supersedes is not in the repo |
| A06 | High | OWNER-23 `consumed_by: G3-W12` makes the whole item BLOCKED_EXTERNAL under loop-prompt s2 |
| A07 | High | C7 "call-store seeding in core/llm/" duplicates G5-W02 (PENDING, priority 1) |
| A08 | High | No card owns `schemas/` or the prompt manifest; bundle schema is `additionalProperties:false` |
| A09 | High | Exit predicate and C8 need a human reviewer and a "fixed sample" no one defines; no owner item |
| A10 | High | Ship-loop rungs 5 and 7 contradict G3-W12 (frozen base, reseal, legacy-route proposal before C2/C6) |
| A11 | Medium | Queue `purpose` is 9,816 chars (loop rule: about 1,000); card status lives in prose with no machine tie |
| A12 | Medium | Cursor `current_gate.purpose` Exit omits the G3-W12 predicate; M1 defined differently in card and exit |
| A13 | Medium | Dangling references after the G7 history move (DEFECT_INDEX 802, 873; doc 14 s4.3, s8) |
| A14 | Medium | "READY WITH CONDITIONS": the conditions are never listed, and the one named (OWNER-23) is not a condition |
| A15 | Medium | The "necessity test in AGENTS.md" cited by ship loop and D8 does not exist in AGENTS.md |
| A16 | Medium | Principles 8 and 11 named as root causes but left unhealed; README_CONTRACT revision not named by any card |
| A17 | Medium | C1 corpus cannot be sourced from the committed evidence; REJECT count disagrees (26 / 27 / 26-27) |
| A18 | Medium | Rollback claim "returns candidates to VALID_UPDATE_AVAILABLE" is false for the extractor bump (C2) |
| A19 | Medium | C8 edits the judge (a G3-W11-owned progress authority) with no owned path |
| A20 | Low | Per-card field gaps (prerequisites, evidence, owned test paths) |
| A21 | Low | ESM has 10 spare lines; the next card-status or exit edit breaks the cap |
| A22 | Low | `loop-prompt.md` s0 still says "N/36" and forbids "investigation" documents; ship loop line 4 says Lane R is "from scratch" |

### A01 - Critical - no activation path; circular dependency

Evidence:
- `project/state.yaml:63-68` active item is G3-W11 `IN_PROGRESS`; its purpose (line ~67) lists "ladder rungs 3 to 5 and 7 ... the first Lane R proposal".
- `project/state.yaml:73-75` G3-W12 owner: "after G3-W11; C1 first". `docs/RESEARCH_AND_GUIDELINES.md:2204`: "It runs after G3-W11 closes or on the owner's order".
- `project/loop-prompt-ship.md:14-18` "Your queue is section 2, in order. Not `next_ready_items`". Section 2 never names G3-W12 as a rung; the only mention is the parenthesis in rung 5 (line 70).
- `project/loop-prompt.md:84-85` "If `active_work_item` is `READY` or `IN_PROGRESS`, continue it".
- Rung 7 / the first proposal needs a candidate the judge authorizes. Measured: 29 of 30 fail J4 and 26 of 30 fail J6 (`docs/DECISION_LOG.md:5992-5997`); a legacy-route candidate cannot pass until C3 to C8 land. G3-W12 starts "after G3-W11 closes"; G3-W11's purpose contains the proposal; the proposal needs G3-W12. (G3-W11's four `acceptance` bullets do not contain the proposal, so the text is ambiguous rather than provably deadlocked, which is the failure: an executor cannot tell.)
- Nothing says who flips G3-W11 to ACCEPTED, who moves G3-W12 to `active_work_item`, or when. C1 touches no shared code (tools, data, evidence), and AGENTS.md "parallel work is allowed only for disjoint paths" would let it run now, but the owner field forbids it.

Why it breaks execution: the executor following the ship loop never reaches a G3-W12 card; the one following AGENTS.md reads ESM G3 work item 4, sees an item the cursor does not make active, and cannot start it.

Replacement text:
1. `project/loop-prompt-ship.md`, insert after the end of rung 5 (after the line `repository has a judge verdict, counts in the log.`):
   new string:
   ```
   5a. **Lane R dependable rebuild (G3-W12, owner D8).** Entered when rungs 3 and 4 are done and rung 5's verdict
      table exists (G3-W11 acceptance bullets 1 to 3 hold). Commit `chore(state)`: G3-W11 to ACCEPTED with each
      acceptance bullet quoted next to its evidence; G3-W12 into `active_work_item` (IN_PROGRESS), removed from
      `next_ready_items`. Then take the first card of G3-W12 whose status in its `purpose` is READY, one shared-code
      card at a time, C1 first. C1 touches no shared code and may start beside G3-W11 (disjoint paths). A card is
      done when its Complete line holds by the command in its Validation; record `lane-r/<card>.json`.
   ```
2. `project/state.yaml` G3-W12 `owner:` (line 75), old: `shared-code, one card at a time after G3-W11; C1 first"`; new: `shared-code, one card at a time; promoted to active by loop-prompt-ship rung 5a when G3-W11 is ACCEPTED or on the owner's order; C1 (tools, data, evidence only) may start beside G3-W11"`.
3. `docs/RESEARCH_AND_GUIDELINES.md:2204`, old: `It runs after G3-W11 closes or on the owner's order; the cursor's active item is unchanged by this entry.`; new: `It is promoted to the active item by project/loop-prompt-ship.md rung 5a when G3-W11 is ACCEPTED, or on the owner's order; C1 touches no shared code and may start beside G3-W11. The cursor's active item is unchanged by this entry.`
4. `project/state.yaml` active_work_item purpose, old: `rungs 3 to 5 and 7 (proving the`; new: `rungs 3 to 5 (proving the`; and old: `the first Lane R proposal). The LLM reviewer`; new: `the first Lane R proposal is the G3 exit predicate and waits for G3-W12 C8). The LLM reviewer`. (Line breaks in the YAML scalar differ; match on the two substrings.)

### A02 - Critical - C3 (and so C4..C8) is deadlocked between three rules

Evidence:
- `project/state.yaml:76` (G3-W12 purpose) common rule: "a governed version bumps only behind a docs/DECISION_LOG.md necessity entry naming the C1 metric that proves a false claim or unsafe effect". C3 `Governed: NORMALISATION_VERSION, INHERITED_UNITS_VERSION, VALIDATOR_VERSION`; its metrics are M1 (ledger completeness), M2 (uncited omissions), M3 (supersession proof): content loss, not "a false claim or unsafe effect".
- G7-W22 clause (2) (`project/state.yaml`, G7-W22 purpose): after the cut "no governed-version bump ... until the first push wave completes, unless the change fixes a safety or factual-accuracy defect (an unsupported public claim, a leaked secret, a wrong authorization) or the owner approves it." No push wave has run (0 product PRs).
- `tests/test_version_bump_discipline.py:51-69` GOVERNED lists renderer.py, authoring.py, review.py, validation/registry.py; "any other [AST] code change does [demand a bump]". C3 edits BC-05 in `validation/registry.py`; C2 and C6 likewise; the commit cannot pass the pre-push hook without a bump.
- C4 `needs C2 and C3`; C5 `needs C4`; C7 `needs C4`; C8 `needs C2 to C7`. One refused bump stalls five cards.

Why it breaks execution: C3 either violates its own bump rule and G7-W22, or cannot land because the discipline test fails. The executor will stall (AGENTS.md "two equivalent failed attempts") or invent a justification.

Replacement text (both copies of the purpose):
- old: `a governed version bumps only behind a docs/DECISION_LOG.md necessity entry naming the C1 metric that proves a false claim or unsafe effect;`
- new: `a governed version bumps only behind a docs/DECISION_LOG.md entry that names the C1 metric proving the ground and the G7-W22 clause relied on: a factual-accuracy or safety defect (C2, C5, C6: M4, M5, M6 or M8) needs no further approval; a content-loss ground (C3: M1, M2, M3) needs the owner's approval, OWNER-24, answered before C3's first bump;`
- add to `owner_items` in `project/state.yaml` after OWNER-23:
  ```
    - id: OWNER-24
      status: OPEN
      summary: "Whether the C3 governed-version bumps (NORMALISATION, INHERITED_UNITS, VALIDATOR) are approved under G7-W22 clause (2), the ground being inherited-content loss (M1 to M3), not a factual-accuracy defect."
      resume_predicate: "The owner answers in docs/DECISION_LOG.md. Only G3-W12 card C3 consumes it; C1, C2 and C6 proceed without it."
      consumed_by: ["NONE"]
      recorded_at: "2026-10-16T19:00:00+05:00"
  ```
  (`NONE` is allowed by `schemas/state.schema.json:141` so the owner item does not block the whole item; see A06.)

### A03 - High - C1 lives where the loop is forbidden to work

Evidence:
- `docs/REPOSITORY_LAYOUT.md:220`: `tools/` is "never imported by src/, never touched by the loop or a lane, never read for an acceptance predicate".
- `project/loop-prompt.md:19-21` and `tools/README.md` "the loop and every lane never read, write, or import anything under `tools/`".
- C1 (`project/state.yaml:76`): owned paths `tools/lane_r_audit/`, `tests/tools/lane_r_audit/`; the audit supplies the G3-W12 exit numbers (ESM line 327) and "a CI ratchet". That is a tools directory written by the loop and read for an acceptance predicate.
- `tests/tools/` does not exist and is not a mirror of `src/` (layout section 3, `tests/<path>/test_<module>.py` mirrors `src/`); precedent for tools tests is a flat `tests/test_<invariant>.py` (`tests/test_reseal_wave.py`, `tests/test_plan_lint.py`).

Why it breaks: the executor must either break a hard rule or stop; the layout commit rule ("never leave a file to organize later") means C1's first commit is non-compliant either way.

Replacement text:
- `docs/REPOSITORY_LAYOUT.md:220`, old: `never imported by src/, never touched by the loop or a lane, never read for an acceptance predicate;`; new: `never imported by src/, never touched by the loop or a lane, never read for an acceptance predicate, except tools/lane_r_audit/ (G3-W12 card C1: written by the loop, imports src/ read-only, exercised by tests/test_lane_r_audit.py and the CI ratchet, the source of the G3-W12 exit numbers);`
- `project/loop-prompt.md` section 0 and `tools/README.md` boundary paragraph: add the same exception clause (one sentence each).
- both copies of the purpose, old: `tests/tools/lane_r_audit/,`; new: `tests/test_lane_r_audit.py and tests/test_lane_r_ratchet.py (flat invariant tests, layout section 3),`.

### A04 - High - C1 is not completable as written

Evidence:
- C1 Steps: "implement M1 to M8 from bundle files and judge helpers only". M4 (claim escapes) and M5 (junk lint) are the rules C2 builds ("deterministic lint ..." is a C2 step); M6 is "catch rate ... per detector" before the detectors exist; M7 needs reruns with the gateway (provider calls); M8 is a "blind hand audit".
- C1 "no product change" and "read-only on candidates/" cannot hold for M7.
- Validation "two runs give identical numbers and match ledger_baseline.json": `evidence/lane-r-dependability/ledger_baseline.json` totals hold only units, kept, kept_not_printed, omit_unsupported(_without_fact), supersede_redundant (M1 to M3). No baseline exists for M4 to M8.
- "CI ratchet (a baseline file; CI fails when a metric worsens)": CI cannot compute M7 or M8.
- `ledger_baseline.json` method uses private judge helpers (`judge._Bundle.load`, `judge._kept_text_present`, `src/.../acceptance/judge.py:184,494`); G3-W11 owns that file.

Replacement text (both copies):
- old: `implement M1 to M8 from bundle files and judge helpers only;`
- new: `implement M1 to M3 from bundle files through a public function added to acceptance/judge.py by G3-W11's owner or, if absent, a thin read-only wrapper that cites the judge's private helpers by name in its docstring; define M4, M5 and M6 as interfaces over a detector registry, with the existing BC-04, BC-14 and reviewer as the registered baseline detectors (their catch rate on the corpus is the M6 baseline), and C2, C6 register theirs; define M7 and M8 as procedures with a committed sample list (M7 on the three pilot candidates, M8 on the A09 sample), not CI metrics;`
- old: `Validation: two runs give identical numbers and match ledger_baseline.json.`
- new: `Validation: two runs give identical M1 to M6 numbers; M1 to M3 match ledger_baseline.json; the ratchet covers M1 to M6 only.`

### A05 - High - D8's owner chain

Evidence:
- The cited owner message (2026-10-16): "Investigate and plan how to permanently, and robustly fix the Lane R". `docs/DECISION_LOG.md:5998-5999` records it as "D8, owner: fix Lane R permanently ... The owner asked for a permanent, robust fix". An instruction to investigate and plan is not an authorization to start eight shared-code cards, redefine Lane R (ESM line 30-31, previously D1 "composes from scratch"), extend the G3 exit predicate, or approve bumps.
- D8 "supersedes the 2026-10-15 'no Lane R fix cycle' direction": that direction appears nowhere in the repository (`grep -rn "fix cycle\|no Lane R fix" docs project AGENTS.md plans/idea.md` finds only D8). The in-repo standing directive is `docs/DECISION_LOG.md:5971` (2026-10-14): "Lane R locally on frozen governed versions with no bump unless necessary". D8 does not mention or reconcile it, and `loop-prompt-ship.md:14-16` records the owner's verdict on added plan cards ("You messed up the whole project" for adding sections, charters, long entries, `DECISION_LOG.md:5969`).
- `project/state.yaml:75` `owner: "D8 (owner, 2026-10-16): fix Lane R permanently"`: the executor reads this as authority to proceed.
- Principle 25 / AGENTS.md "Ask the owner ... a material product-policy decision": redefining Lane R's method is such a decision.

Why: the executor will build a lot on an authorization the log does not support, and a later owner reading D8 sees an owner decision the owner did not make.

Replacement text, `docs/DECISION_LOG.md`, D8 `What` bullet:
- old: `The owner asked for a permanent, robust fix of Lane R after the 2026-10-16 investigation (` ... `This supersedes the 2026-10-15 "no Lane R fix cycle" direction.`
- new (keep the rest of the bullet): `The owner's message of 2026-10-16 was: "Investigate and plan how to permanently, and robustly fix the Lane R". This entry records the plan that answers it (docs/investigations/14-lane-r-dependability.md), the admission of G3-W12 as a queued item, and the plan-text changes. It is not an owner authorization to start any card, to change Lane R's method, or to move a governed version; those follow from the owner's go on this plan, recorded below by a line "Owner go: <date, words>". Until that line exists, cards C2 to C8 stay BLOCKED_BY_GATE and C1 (measurement only, no product change) is the only card that may start. The 2026-10-14 directive (docs/DECISION_LOG.md, "reset to shipping": Lane R on frozen governed versions, no bump unless necessary) stands and is relaxed only by the bump rule in G3-W12's common rules.`
- `project/state.yaml:75`, old: `"D8 (owner, 2026-10-16): fix Lane R permanently; shared-code ...`; new: `"D8 (2026-10-16): plan answering the owner's request to investigate and plan a permanent Lane R fix; C1 may start, C2 to C8 wait for the owner go recorded in docs/DECISION_LOG.md; shared-code ...` Also the G3-W12 status of C2 to C8 is then `BLOCKED_BY_GATE` (existing state vocabulary).
- Also fix ESM line 318 `(owner D8, 2026-10-16;` -> `(plan of 2026-10-16, D8;`, and `loop-prompt-ship.md:16` `except the G3-W12 cards (owner D8, 2026-10-16)` -> `except the G3-W12 cards (plan of 2026-10-16, D8)`.

### A06 - High - OWNER-23 blocks the whole work item

Evidence: `project/state.yaml:385-391`: `consumed_by: ["G3-W12"]`, while its own `resume_predicate` says "Only G3-W12 card C6 consumes it; C6 proceeds without it ... nothing else waits". `project/loop-prompt.md:99-100` and ESM line 135-138: "A work item is `BLOCKED_EXTERNAL` only if it itself consumes an `OPEN` owner item"; the consumption is at item granularity (schema pattern `^(G[0-7]_...|G[0-7]-W[0-9]{2}|NONE)$`, no card ids).

Why: on promotion the executor must mark G3-W12 BLOCKED_EXTERNAL, then "take the next item", never starting C1.

Replacement (`project/state.yaml`, OWNER-23): old `consumed_by: ["G3-W12"]`; new `consumed_by: ["NONE"]`, and in `note` append `Consumed by G3-W12 card C6's cross-family route only; the item as a whole never waits on it.`

### A07 - High - C7 overlaps G5-W02

Evidence: C7 owned paths "the call-store seeding in core/llm/". G5-W02 (`project/state.yaml` G5-W02 purpose; PENDING, "PRIORITY 1 of 20") already: "seed the call store from the sealed bundle's accepted artifacts by recomputed request hash so a fresh clone replays with zero provider calls". AGENTS.md: "Only one shared-code item may be active ... never the same file or durable state concurrently". Two PENDING items own one mechanism with different semantics (G5-W02 replay; C7 per-unit digest fixed point).

Replacement: add to C7 text (both copies), after `Owned paths:` clause for C7, old `the call-store seeding in core/llm/, tests.`; new `tests; the call-store seeding in core/llm/ is G5-W02's and is imported, not edited (if G5-W02 is not ACCEPTED when C7 starts, C7 records the per-unit digest in the bundle only and leaves core/llm/ unchanged).`

### A08 - High - schema and prompt-manifest ownership missing

Evidence: `schemas/candidate-bundle.schema.json` has `additionalProperties: false` at 16 object levels; `schemas/prompt-manifest.schema.json` and `tests/core/llm/test_prompts.py` cover prompts. AGENTS.md: "`schemas/` changes only through a named work item (section 31 proposal, owner admission), landed with its code and tests". C2 (published-version fact, "no new BC id"), C3 (evidence codes, coverage proof), C4 (operation schema; new `prompts/section_patch.yaml`), C7 (verdict per candidate hash) each add data. No card lists `schemas/` or names a section 31 proposal; D8 is not one.

Replacement: add to the common rules (both copies), after `evidence at evidence/build/G3_PYTHON_COHORT/lane-r/<card>.json (redacted, checksum-valid, revision-bound);` the text: ` a card that adds a bundle field, a fact kind or a prompt first lands a docs/DECISION_LOG.md section 31 proposal naming the schema file and version, and the owner admits it there, because schemas/ changes only through a named work item;`

### A09 - High - human-dependent exit with no owner item

Evidence: ESM line 327 exit predicate: "zero unflagged factual errors in a blind hand audit of a fixed sample; ... ten pilot repositories reviewed blind by a human". C8 Complete: "the human accept rate is recorded" (no threshold). The earlier "hand triage" was agent-run (`evidence/lane-r-dependability/Q_claims.md` "Sources: review-packets/R/*/TRIAGE.md", written by agents). No owner item names the human, the sample, or an accept threshold; AGENTS.md BLOCKED_EXTERNAL requires a recorded resume predicate. M8 is defined in C1 as "escapes found by a blind hand audit of a fixed sample" with no sample.

Replacement:
- ESM line 327, old: `zero unflagged factual errors in a blind hand audit of a fixed sample;`; new: `zero unflagged factual errors in a blind hand audit (OWNER-25 names the auditor and the committed sample list under data/lane_r_corpus/);`
- ESM line 327, old: `ten pilot repositories reviewed blind by a human, results beside the C1 baseline.`; new: `ten pilot repositories reviewed blind by the human OWNER-25 names, the accept rate recorded beside the C1 baseline and not below the threshold OWNER-25 states.`
- add `OWNER-25` to `owner_items`: `summary: "Who performs the G3-W12 blind human review and hand audit (M8), the sample list, and the accept-rate threshold for the default switch."`, `resume_predicate: "The owner names the reviewer, approves the sample list committed by C1, and states the threshold in docs/DECISION_LOG.md."`, `consumed_by: ["G3-W12"]` is wrong for the same reason as A06; use `["NONE"]` with note "Consumed by card C8 and the exit predicate only; C1 to C7 proceed".
- C8 Complete (both copies), old: `and the human accept rate is recorded.`; new: `and the human accept rate is recorded against OWNER-25's threshold.`

### A10 - High - the ladder contradicts G3-W12

Evidence:
- Rung 5 (`loop-prompt-ship.md:70-75`) "Record the freeze commit. Run `tools/reviewer/reseal_wave` on repositories without a standard live README ..." versus doc 14 risk R2 (`docs/investigations/14-lane-r-dependability.md:84`): "no reseal wave before C8", and G3-W12 changes governed code after the freeze, so the "frozen base" ends at C2.
- Rung 7 "R proposes: the first rung-5 repository with a passing verdict goes through the rung-6 path" proposes to a real repository a legacy-route candidate, produced before C2 (claim gate) and C6 (a reviewer that can say no) existed, though the plan's own evidence is "about 22 factual errors in 14 sealed bundles, all ACCEPTed" and the judge's J3 is BC-04, the citation-only check that D8 calls inadequate.
- `project/loop-prompt-ship.md:4` "Lane R (a README from scratch, for any repository)" and `AGENTS.md:137` "regeneration from scratch" versus ESM line 30 "live-anchored where a usable README exists" (this one matches `docs/README_STANDARD.md` PRC-07 "Only a repository with no README may be authored from scratch", so the ESM edit is right and the other two are stale).

Replacement:
- `project/loop-prompt-ship.md` rung 5, old: `Record the freeze commit. Run \`tools/reviewer/reseal_wave\``; new: `Record the freeze commit; the freeze ends when G3-W12 C2 lands. Run \`tools/reviewer/reseal_wave\``, and the same rung: add after the line ending `counts in the log.`: ` This rung seals only repositories without a usable live README (from scratch is correct there, README_STANDARD PRC-07); it is not a reseal wave of the 30 existing bundles, which doc 14 risk R2 bars before C8.`
- rung 7, old: `7. **R proposes.** The first rung-5 repository with a passing verdict goes through the rung-6 path.`; new: `7. **R proposes.** Only after G3-W12 C2 and C6 are ACCEPTED: the first repository whose candidate the judge authorizes and the C1 harness shows with zero M4 escapes goes through the rung-6 path.`
- `project/loop-prompt-ship.md:4`, old: `Lane R (a README from scratch, for any repository)`; new: `Lane R (a README regenerated for any repository: live-anchored where a usable README exists, from scratch where none does)`.
- `AGENTS.md:137` is within the 210-line cap (207); same-line edit: old `regeneration from scratch.` ... leave AGENTS.md to the owner and record the stale phrase in the next DECISION_LOG entry, since AGENTS.md owns conduct and is governed.

### A11 - Medium - queue entry size and card tracking

Evidence: `purpose` of G3-W12 is 9,816 characters (python len on the YAML load); next largest queue entry 6,238. `project/loop-prompt.md:39-42`: "A work item's purpose stays under about a thousand characters ... When an item's scope grows past that ... split it". Cards C1..C8 are inline substrings with status tags `[READY]`, `[BACKLOG, needs C1]`; the cursor schema offers no card id, `schemas/state.schema.json:115` queued statuses are PENDING / BLOCKED_BY_GATE / COMPLETE; nothing ties a card status to `lane-r/<card>.json`. When G3-W12 becomes active, "the active item's text is the owner's to edit" (loop-prompt 113-115), so 27.9 and the cursor diverge and the card statuses are edited inside a 9.8k string by hand.

Replacement: add one sentence to the common rules (both copies): ` This item is exempt from the thousand-character rule by the owner's plan (D8); the card status tags in this text are edited only in the same commit that writes lane-r/<card>.json, and the next editor of this text splits each card into its own queued item G3-W12a to G3-W12h if any card is reworked.` And add a test (not text): `tests/test_queue_agreement.py` assertion that for each `[ACCEPTED]` card tag a `lane-r/<card>.json` exists.

### A12 - Medium - cursor gate and metric definition mismatch

Evidence:
- `project/state.yaml` `current_gate.purpose` Exit lists the four G3 clauses only; ESM G3 Exit has a second bullet (G3-W12). The 2026-10-14 entry (`DECISION_LOG.md:5977`) states `current_gate.purpose` matches the ESM. After the gate's last item the loop accepts per "every gate exit predicate passes", and AGENTS.md says ESM owns acceptance, but the cursor copy would let a session close G3 early.
- M1 "ledger completeness (kept units printed over kept units)" (card) vs exit "ledger completeness 100 percent (every live unit byte-identical or removed with an evidence code)" (ESM 327): different denominators (746 kept of 2,761 units vs all live units).

Replacement:
- `project/state.yaml` `current_gate.purpose`, old: `one passing Lane R candidate reaches propose through the sandbox-proven write path.`; new: `one passing Lane R candidate reaches propose through the sandbox-proven write path; and the G3-W12 dependability predicate in docs/EXECUTION_STATE_MACHINE.md G3 holds.`
- ESM line 327, old: `ledger completeness 100 percent (every live unit byte-identical or removed with an evidence code);`; new: `ledger completeness M1 100 percent (every kept unit printed) and M2 zero (every removed unit carries an evidence code and a cited fact);`

### A13 - Medium - dangling references after the move

Evidence:
- `docs/DEFECT_INDEX.md:802` "`docs/EXECUTION_STATE_MACHINE.md` G7 Work item 9" and `:873` "G7 Work item 8": ESM G7 Work now has items 1 to 5 only (`sed -n 424,436p`).
- `docs/investigations/14-lane-r-dependability.md:55` says the history moved "to `docs/DECISION_LOG.md` (2026-10-16 archive entry)"; it moved to `docs/investigations/15-esm-g7-history-2026-10-16.md` (D8 and the commit say so). Verified by diff: all 17 removed G7 lines appear verbatim in doc 15.
- doc 14 line 93: "Plan updated and verified (section C of the handoff in the change)": no such file is in the commit.

Replacement:
- `docs/DEFECT_INDEX.md:802`, old `G7 Work item 9)`; new `G7 Work item 5, moved to docs/investigations/15-esm-g7-history-2026-10-16.md, item 9)`. Same at `:873` with `item 8`.
- doc 14 line 55: old `the verbatim text moves to \`docs/DECISION_LOG.md\` (2026-10-16 archive entry)`; new `the verbatim text moves to \`docs/investigations/15-esm-g7-history-2026-10-16.md\``; and `the plan keeps one line each` -> `the plan keeps one summary line`.
- doc 14 line 93, old `Plan updated and verified (section C of the handoff in the change).`; new `Plan updated; checked by this audit set (review-packets/plan-audit, not committed).`

### A14 - Medium - "READY WITH CONDITIONS" has no conditions

Evidence: `DECISION_LOG.md:6001` "Readiness: READY WITH CONDITIONS (C1 is READY)"; doc 14 line 94 "the rest are gated on their prerequisites and OWNER-23". No numbered conditions exist anywhere. OWNER-23 gates only C6's cross-family option. "C1 is READY" but C1's own header says nothing about the A03 tools blocker.

Replacement, `docs/DECISION_LOG.md` D8 `Not done` bullet, old `Readiness: READY WITH CONDITIONS (C1 is READY).`; new `Readiness: READY WITH CONDITIONS, each checkable: (1) the owner go line in this entry before C2 to C8 (A05); (2) C1's tools/ exception recorded in docs/REPOSITORY_LAYOUT.md in C1's first commit; (3) OWNER-24 answered before C3's first bump; (4) OWNER-25 answered before C8; (5) OWNER-23 answered only for C6's cross-family route; (6) G5-W02 ACCEPTED or untouched before C7 edits core/llm/. C1 is READY.` Apply the same list to doc 14 section 8.

### A15 - Medium - "necessity test in AGENTS.md" does not exist

Evidence: `grep -in necessity AGENTS.md` returns nothing. Cited at `project/loop-prompt-ship.md:18,61,73` ("the necessity test in `AGENTS.md`") and `DECISION_LOG.md:6000` ("**Necessity (AGENTS.md).**"). The only definition is G3-W12's own rule (A02) and the 2026-10-15 log entry.

Replacement: `project/loop-prompt-ship.md:18`, old `without the necessity test in \`AGENTS.md\`.`; new `without the necessity test: a docs/DECISION_LOG.md entry naming the measured defect, the metric and the G7-W22 clause (G3-W12 common rules).` Same substitution at lines 61 and 73 (`the necessity test` stays; drop `in \`AGENTS.md\``). D8 bullet header, old `**Necessity (AGENTS.md).**`; new `**Necessity (G7-W22 clause 2).**`.

### A16 - Medium - principles and README_CONTRACT not healed for C2/C3/C6

Evidence:
- Doc 14 section 3 names ESM principle 8 ("preserve, improve, correct, or explicitly omit every material unit") and principle 11 / G1.8 as governance root causes; the commit healed 22 and 26 only. C3 ("only CONTRADICTED content may be deleted") contradicts principle 8's "explicitly omit". C7's M7 ("a changed fact re-renders only its units") qualifies principle 11 "An accepted unchanged transaction makes zero new provider calls".
- `project/loop-prompt.md:36-39`: "`docs/README_CONTRACT.md` changes only through a work item that names the revision, with its defect recorded". C2 changes BC-04/BC-14, C3 changes BC-05, C6 changes BC-10/review semantics (README_CONTRACT s6 encodes blocking checks; `docs/STATE_MACHINE.md` owns runtime). No card names a contract revision; ESM G3 says README_CONTRACT is "the legacy encoding" under revision (G3-W10).

Replacement:
- ESM principle 8, old `validate, preserve, improve, correct, or explicitly omit every material unit.`; new `validate, preserve, improve, correct, or omit every material unit, an omission only on CONTRADICTED evidence (G3-W12 C3); everything else is kept and flagged.`
- Common rules (both copies), after `evidence ... revision-bound);` add: ` a card that changes a blocking check's meaning names the docs/README_CONTRACT.md and docs/STATE_MACHINE.md revision it lands in the same commit;`

### A17 - Medium - corpus source and inconsistent counts

Evidence:
- C1: "a corpus of at least 40 labeled cases (the hand-found factual errors in evidence/lane-r-dependability/Q_claims.md and at least 20 ledger cases)". `Q_claims.md` section 2 traces ten cases T1 to T10 and gives nine class counts; "about 22 errors in 14 bundles" appears only in `R_determinism_review.md:44` and cites `review-packets/` which the manifest says is "not committed" (`manifest.json` `window`). The executor cannot reach 20 hand-found cases from committed evidence.
- REJECT count: Q says 27/30 (`Q_claims.md` s2 "REJECT in 27/30"), R says 26 ("4 ACCEPT, 22 REJECT_PRESENTATION, 4 REJECT_FACTUAL"), doc 14 F3 says "26-27", the card and D8 say 26. Manifest SHA-256 values verified equal to the files.

Replacement: C1 (both copies), old `(the hand-found factual errors in evidence/lane-r-dependability/Q_claims.md and at least 20 ledger cases)`; new `(the ten traced cases T1 to T10 in evidence/lane-r-dependability/Q_claims.md, at least 10 further hand-found errors the executor re-derives and labels from the 30 sealed bundles with the sentence, the cited facts and the live text, and at least 20 ledger cases)`. Doc 14 F3 and Q: standardize on `26 of 30 rejections overturned` (R's table) and note Q's 27 as the count including one REJECT_PRESENTATION reread.

### A18 - Medium - extractor-bump rollback is stated wrongly

Evidence: common rule `rollback ... a reverted bump returns candidates to VALID_UPDATE_AVAILABLE and never INVALIDATED`. C2 `Governed: VALIDATOR_VERSION and the extractor version`. `DECISION_LOG.md:5981-5985` and ship loop rung 3 (`:61`): an EXTRACTOR_VERSION bump leaves a bundle `UNVERIFIED`, "the one bump that always needs the necessity test"; `status` shows `recheck ... UNVERIFIED 30` today.

Replacement (both copies): old `a reverted bump returns candidates to VALID_UPDATE_AVAILABLE and never INVALIDATED;`; new `a reverted bump returns candidates to VALID_UPDATE_AVAILABLE (validator, renderer, normalisation, reviewer) or UNVERIFIED pending a pinned-clone re-extraction (extractor), never INVALIDATED;`

### A19 - Medium - C8 edits the judge with no owned path

Evidence: C8 Steps "align the judge's J4 and J6 definitions with C3 only where they disagree" and "a status line printing M1 to M4"; C8 lists no `Owned paths`. The judge (`components/readme/acceptance/judge.py`) is the owner's progress authority (D4) and G3-W11 owned path; `cli.py` status is G3-W11 owned. A pilot card changing what counts as authorizable also changes N/44.

Replacement: C8 (both copies) insert before `Steps:` for C8: `Owned paths: components/readme/acceptance/ (judge J4 and J6 definitions, only after G3-W11 is ACCEPTED), cli.py (status line only), tests, evidence/build/G3_PYTHON_COHORT/lane-r/; a change to J4 or J6 needs a DECISION_LOG entry stating the N/44 before and after.`

### A20 - Low - per-card field completeness

Required fields: objective, ownership (owned paths), prerequisites, dependencies, steps, validation, evidence, rollback, completion. Common rules supply evidence path and rollback shape; dependencies are only in the bracket tag.

| Card | Missing or weak |
|---|---|
| C1 | Dependencies none stated beyond "Prerequisites: none"; ownership conflicts with `tools/` (A03); ratchet file path unnamed; M8 sample undefined |
| C2 | Prerequisites not stated as a field (only "needs C1"); owned test path "tests" unspecified; Evidence field absent (common rule only); no schema/fact-kind note (A08) |
| C3 | Prerequisites field absent ("needs C2: same validation file"); tests unspecified; the "re-run into a scratch directory (not committed)" needs a gateway and spend limit, none stated |
| C4 | Prerequisites field absent; no Governed line though it adds a prompt and a CLI mode (prompt hash); pilot output location not given; "present --mode live-anchored" requires a CLI contract not in layout |
| C5 | Prerequisites absent; "Validation" does not name the dataset; no Evidence |
| C6 | Prerequisites absent; re-running 30 stored reviews calls the gateway: no cost or credential statement; Evidence absent |
| C7 | Prerequisites absent; no Governed line though it touches `bundle/` (seal logic) and verdict storage; G5-W02 overlap (A07) |
| C8 | Owned paths absent (A19); human reviewer undefined (A09); Evidence absent |

### A21 - Low - cap headroom

`wc -l docs/EXECUTION_STATE_MACHINE.md` = 510. The first card-status edit or any A01/A09/A12 text above adds lines; the cap test (principle 24) would fail on 521. Put the A09/A12 edits within existing lines, or move another block to a doc 15-style archive in the same commit.

### A22 - Low - stale loop text

`project/loop-prompt.md:42-43` still says "N/36" (the registry is 44); `:31` "Never create a plan ... investigation" while the commit adds docs/investigations/14 and 15 (authorized only by the ship loop's G3-W12 exception, which reaches the plan text but not this file). Replacement: `N/36` -> `N/44` (`:42`); at `:31` append `, except what the ship loop names`.

## 2. What I checked that held

- ESM 510 lines (cap 520), AGENTS.md 207 (cap 210), exactly 8 `## G` gates.
- `project/state.yaml` validates against `schemas/state.schema.json` (test_schemas green); G3-W12 status `PENDING` is a legal queued status; OWNER-23 has all required fields; `updated_at` 2026-10-16T18:30 precedes the commit time (19:22), so the cursor-staleness guard is satisfied.
- State and 27.9 purpose strings are byte-equal; the 27.9 block is exactly one YAML block; the entry was inserted in the right section (`test_queue_agreement`, `test_register_integrity`, `test_governance_consistency` green).
- The G7 history move is truly verbatim: every removed G7 line (17 of 20 removed lines; the other 3 are the intended Lane R and principle 22 rewrites) is present in `docs/investigations/15-esm-g7-history-2026-10-16.md`; exit predicates for W13 and W15 were condensed and the originals are in doc 15.
- `evidence/lane-r-dependability/manifest.json` SHA-256 values equal the six files; `ledger_baseline.json` has 30 bundles and totals 2761 / 746 / 389 / 338 / 316 / 1514, matching the numbers quoted in the card and D8 (389 of 746, 316 of 338, 1514); control revision 4a7baf11 exists and `candidates/` is unchanged since it (`git diff --stat 4a7baf11 HEAD -- candidates` empty); judge helpers named in the baseline `method` exist (`judge.py` lines 184, 196, 212, 223, 494, 719).
- The paths G3-W12 reads or edits exist: `placement.py`, `renderer.py`, `reconciliation/`, `review/independent/`, `bundle/`, `readme_correction/`, `core/facts.py`, `core/llm/`, `prompts/independent_review.yaml`, `validation/`, `tools/reviewer/{reseal_wave,bump_proof}`. New by design (missing today, each created by a named card): `tools/lane_r_audit`, `data/lane_r_corpus`, `evidence/build/G3_PYTHON_COHORT/lane-r`, `components/readme/composition/patch`, `prompts/section_patch.yaml`; only C1 records its paths in REPOSITORY_LAYOUT (the layout entry for `evidence/lane-r-dependability/` mentions `tools/lane_r_audit/`).
- BLOCKING_CHECKS has 13 entries, so "at most fifteen" in C2 has room; VALIDATOR_VERSION 23.
- Principle 22 and 26 text does not contradict AGENTS.md ("each finding names a section and a causal stage, or it is advisory"); Lane R's new definition agrees with `README_STANDARD.md` PRC-07.
- `ruff check .` and `ruff format --check .` pass; `status` prints `authorizable 0/44`, consistent with the cursor.
- Principle 25 (write-scope gate) and the product-repo write rule are not violated: no card writes to a product repository; C8 pilots read only.
- Cards C2, C3, C5, C6 declare `Governed:` for the governed sources they edit (renderer, validator, reviewer, normalisation), consistent with `tests/test_version_bump_discipline.py` GOVERNED list (but see A02 for the rule behind the bump).
