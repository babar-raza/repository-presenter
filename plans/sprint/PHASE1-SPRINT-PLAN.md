# PHASE1-SPRINT — every sealable candidate by Mon 2026-09-15, taskcard-driven

The sprint reference. The executor reads this in full every Orient (`project/loop-prompt-sprint.md`
§1.2); live card status is in `plans/sprint/loop-status.jsonl`, never restated here; supervisor
steering is in `plans/sprint/loop-instructions.jsonl`, which overrides a card's text for that card.
Authoritative copy: this file, edited only by the supervisor, each edit recorded in the channel.

## 0. Context & goal

- Thu 2026-09-11 → Mon 09-15 08:00 (+05). 8/34 sealed at open; target: every sealable candidate =
  the G4 predicate (every enabled `data/registry.json` entry sealed + 34 dispositions). 23
  sealable remained at open — zero margin; TeX-Python's upstream is confirmed unchanged (F10,
  2026-09-11: no source commit since the broken 26.5 release), so no margin arrives.
- Scale: full multi-lane (primary + lanes B/C/D + supervisor). Fallback on a missed Sunday
  checkpoint: maximize count. Supervisor never patches `src/` or `tests/`.
- Human dependence: none except machine uptime and usage caps. RC-03/PA-05/item-54 rulings are
  §31-delegated (2026-09-11); OWNER-01 branch protection stays OPEN deliberately (would break
  lane self-merge).

## 1. Diagnosis (condensed; the three 2026-09-11 audit reports are the full record)

Symptoms: 0 seals in 4.8 d; PRs #29/#30 stranded 3 d 18 h; 3D-.NET un-sealed; ITEM_UNLOCKS frozen
33/49; 2 bundles couldn't re-render; idle gaps to 9 h.

Root causes: (A) supervision in-band and mortal — reviewer dark 09-06→09-11, all monitors died
with it, no out-of-band re-arm; (B) supervision fitted to conventions — label-scoped PR queries,
no age checks, §31 parsers reading a moved section, hardcoded dead session id, unblock
silent-drop; (C) prose copies with no reader — wrong G4 exit predicate (31 vs derived), stale
cursor fields, budget violation, corrections buried in unrelated records, reversals with no
write-set; (D) enforcement split — cross-file checks living only in mortal tools/; (E) the no-op
proof certifies a warm machine-local cache (`earliest_affected_stage` gates nothing;
`fresh_process` hardcoded; 3/6 jobs seedable; cold proofs ever: 0; provider genuinely
packet-nondeterministic); (F) review acceptance unguarded — 8/9 sealed reviews were REJECT folded
to ACCEPT; hallucinations stably reproducible at temp 0; (G) dependency records mutated without
migration — all 8 bundles reopen EXTRACTING by `evaluate()` while `--stale` reads 3/10 classes;
the tool's own venv hash is a dependency of every candidate; (H) version bumps and landing
discipline conventional; (I) toolchain/HTTP noise inside compared artifacts; (J) plans redrawn in
model order (G5-W01).

What breaks rerun consistency: packet perturbation → cache miss → a different deterministic
answer (including stable fabrications) with nothing gating which stage may re-run; a machine-local
cache; environment noise inside hashed artifacts; schema mutations making old records permanently
unmatchable; unversioned meaning changes; supervision gaps compounding all of it for days.

## 2. Preserve — never weaken (each has success evidence)

pre-push hook + hooksPath · CI independent steps + Summary · test_sealed_bytes byte control +
strict-xfail pattern · two-file jsonl channels (single writer each) · unblocked.jsonl ledger ·
commit-only signal reading · one-item-per-run lane spawns + self-merge (≈3 min norm) ·
stop_monitor alarm arithmetic · the 12 finding-side fold guards · second-reader mechanism · TB-01
build_verified · CURRENT-counting semantics · pointer pattern · derived-from-code tests ·
EXIT_INCONSISTENT · loop §1.1 killed-process recovery.

## 3. Scaffolding (F5)

`plans/sprint/` (this file, the two channels, ACTIVE marker) + `project/loop-prompt-sprint.md`.
The ACTIVE marker arms liveness.yml's main-inactivity alarm; Z1 removes it.

## 4. Taskcards

F-card ladder: `started → pilot_proof → self_review → done`; executor cards report transitions in
loop-status.jsonl; supervisor cards (F1–F5, F10) are recorded in loop-instructions.jsonl (single
writer per channel). W-cards close per candidate: bundle at `READY_FOR_PROPOSAL` verified on
disk + hosted CI green + count recomputed from disk.

| ID | Owner | Files | Gate | Work & acceptance | Rollback |
|---|---|---|---|---|---|
| F1 | supervisor | tools/reviewer/* | GATE-0 | Transcript resolution (transcript_path.py) replacing the dead hardcoded id; §31 parse → DECISION_LOG; ledger-driven unlocks, ITEM_UNLOCKS retired, silent-drop fixed; label-independent PR age flag (>30 min, `hold` exempt); worktree orphan check; procedure §2c. Accept: §31 count >0; age flag on synthetic ref; zero functional ITEM_UNLOCKS refs. | git revert; tools/ never imported by src/ |
| F2 | supervisor | .github/workflows/liveness.yml | GATE-0 | Scheduled (:13/:43) read-only dead-man: open PR >30 min without `hold`; branch ahead of main untouched 12 h+; main inactive 4 h+ while ACTIVE exists. Detection only. Accept: dispatch green; kill-test red run; cleanup. | delete workflow file |
| F3 | supervisor | docs/SUPERVISION.md (new), ESM, RESEARCH, AGENTS.md, procedure.md, loop-prompt.md, loop-prompt-lane.md, state.yaml, G4 manifest | GATE-0 | Supervision doc + authority line; ESM ceiling → derived (fixes wrong G4 exit predicate) within 500; AGENTS ≤200 + schema-evolution route; RESEARCH:2448 + §27.0 currency note; state.yaml :37 pointer + registry_modes removed; G4 manifest 3D-.NET reversal amended; procedure §0 startup checklist; loop-prompt Orient PR/worktree sweeps + §1.1 pushed-but-unmerged + §31 REVERSES convention; lane prompt label/branch confirmation. Accept: ci_check green; budgets met. | revert commits; docs-only |
| F4 | supervisor | DECISION_LOG §31; §29 arrival list; both channels | GATE-0 | Eight §31 rulings (sprint DIRECTIVE; 49 declined; RC-03+PA-05 deferred; items 50–54 admitted; Cells-Cpp re-seal policy; venv freeze; wakeup REVERSES; executor-death record); standing executor instruction (self-schedule; ledger discipline + 39/40/44/45/46 backfill; slot order). Accept: entries committed, timestamps from `date`. | §31 correcting entry, never an edit |
| F5 | supervisor | plans/sprint/*, project/loop-prompt-sprint.md | GATE-0 | This file + mission prompt + channels + ACTIVE. Accept: woken primary selects F6 and appends `started` within 15 min (V1). | remove ACTIVE; channel fallback instruction |
| F6 | primary | review/independent/review.py, repair/rounds.py, validation/registry.py, tests | GATE-A | Acceptance-side guard: ACCEPT on a new seal requires a corroborating second read at seed+2 (guard-10 made symmetric); disagreement routes the second read's findings through the normal stack; BC-10 `Check.version` bump (meaning change). Disclosed side effect: `--stale` lists all 8, PA-03's 4th count may drop — cosmetic, count-neutral. Pilot_proof: next live seal shows ACCEPT + `second_reader.read` ≥ 2. Red-before/green-after on a synthetic folded-ACCEPT packet. | revert restores prior BC-10 semantics; bytes unaffected |
| F7 | primary | tests/ | GATE-A | Version-bump test (renderer/validator/normalisation/reviewer-logic source moved in HEAD~1..HEAD without its constant → fail; skip without git context — the CI_AND_STALENESS §4.2 proposal); debt-ledger test (every KNOWN_BLOCKED_STALE xfail and VALID_UPDATE_AVAILABLE carries a card/arrival ref). Pilot_proof: synthetic unbumped renderer edit goes red on a scratch branch. | revert; tests-only |
| F8 | primary | tests/test_governance_consistency.py | after F3 | Port reviewer_check's deterministic repo_checks (queue order/purpose, budgets, limits-vs-decisions, gate-purpose-vs-ESM) + promote audit_second_reader_ledger + `test_gate_evidence_matches_disk` (a manifest SEALED row ⇒ live `candidates/<slug>/CURRENT`) + ceiling-absence test. tests/→tools/ import is sanctioned (test_bundle_audits precedent). Strict-xfail any residue. | revert test file |
| F9 | primary | schemas/state.schema.json, tests/test_queue_agreement.py | GATE-A | Add COMPLETE to next_ready_items' status enum; accepted_work_items() reads nested second_pass → G3-W04 unpinned. Authorized via this card (AGENTS.md schema route). | revert; schema+test only |
| F10 | supervisor | — (read-only) | GATE-0 | TeX-Python upstream check. RESULT 2026-09-11: no source commit since the broken 26.5 release — NOT recoverable; stays NOT_PROCESSABLE; zero margin stands. | n/a |
| W-* | lanes/primary | candidates/, runs/ | GATE-B | Waves per §11; per-candidate acceptance above; real rejection → disposition + move on (stop-don't-force); fold-don't-code for content classes (DIRECTIVE rule 16). | failed seal leaves no bundle; broken re-seal → KNOWN_BLOCKED_STALE + card ref |
| Z1 | supervisor | evidence/build/PHASE1_SPRINT/ | GATE-Z | Evidence bundle: manifest.json (card statuses + evidence, gate verdicts, checkpoint counts, CI + liveness run ids, final `status --stale` output, PA-03 four-count), kill-test outputs, channel copies. Remove ACTIVE. Final report names the bundle's absolute path. | n/a |

**Shared-code slot order (primary):** F6 → F7 → 41+42 (batch) → 43 → 26 → 47 → F8 → F9 → 50 →
51 → 53 → 52 → 54 → 48. Item 34 deferred unless a Java rerun flags it; 49 declined; 45/46
landed pre-sprint; 38 superseded.

## 5. Gates

- **GATE-0 (Thu):** preflight (fetch, HEAD re-check, CI green, `status` consistent), then F1–F5 +
  F10. Exit = setup-completeness checklist, verified not assumed: (1) this file committed; (2)
  mission prompt written; (3) channels + channel_init committed; (4) ACTIVE present; (5) F1
  proven on a live `reviewer_check --record` run (§31 >0, no false-OK, transcript path correct);
  (6) all 3 monitors re-armed on the live executor transcript; (7) liveness.yml green + kill-test
  evidence (V3); (8) §31 rulings + items 50–54 admitted; (9) ITEM_UNLOCKS retired, ledger firing
  confirmed; (10) lane yamls carry PENDING rerun rows; (11) reviewer_state.lanes reconciled; (12)
  F3 landed with CI green; (13) heartbeat scheduled + first wake recorded (V4); (14) TeX verdict
  recorded (done). Only then GATE-A/B.
- **GATE-A:** primary lands F6 (F7 in-slot after). Waves may open before F7–F9 complete.
- **GATE-B:** lanes spawn (C: Cells-Java→Slides-Java; D: Cells-Go; B Fri: Email/PDF-Cpp) per §12;
  PENDING rerun rows appended between runs only; spawns recorded in reviewer_state.
- **Checkpoints (+05), mechanical:** at each — recount from disk (`status`; EXIT_INCONSISTENT =
  stop and reconcile first), compare, apply the row, append one channel line, change nothing
  else.

| Checkpoint | Count ≥ | Below-threshold action (execute, don't deliberate) |
|---|---|---|
| Fri 08:00 | 11 | halt landings; first-principles review of the item-40 premise against the failed candidates' actual classes; then resume |
| Fri 20:00 | 17 | §28.12 cut-order surgery (drop lowest-likelihood candidates); notify owner |
| Sat 20:00 | 24 | reorder Sunday most-likely-first; changed-mechanism retries only; freeze admissions except 54 |
| Sun 20:00 | all | fallback = maximize count; stop opening new failure investigations |

- **GATE-Z (Mon 08:00):** G4 manifest assembly (cohort reports, census, per-repo parity, derived
  predicate), CI green, Z1, stop; liveness.yml stays.

## 6. Ownership / overlap

| Writer | Paths | Overlap control |
|---|---|---|
| Supervisor | tools/, docs/, plans/, .github/workflows/, §27.9/§31, state.yaml (clean checkpoints), lane yamls (between runs), G4 manifest | never src/ or tests/; own hunks only; HEAD re-checked |
| Primary | src/, tests/, schemas/ (F9), prompts/, evidence/build/<gate>/, state.yaml | one shared-code card in progress; sprint cards via mission prompt |
| Lanes B/C/D | own worktree, own candidates/, evidence/build/lanes/<lane>/, own lane yaml, current_candidates carve-out | disjoint repos; label+branch confirmed; never two agents on one candidate |
| liveness.yml | nothing (read-only) | — |

## 7. Verification commands

Local: `bash scripts/ci_check.sh` · `.venv/Scripts/repository-presenter status --stale` ·
`.venv/Scripts/python -m pytest tests/test_sealed_bytes.py -n auto` after rendering-adjacent
landings. Hosted: `gh run list --limit 3`; `gh run list --workflow liveness.yml --limit 3` each
supervisor wake. Supervision: `python tools/reviewer/reviewer_check.py --record` every wake, every
FLAG acted on (procedure §2); `gh pr list --state open --json number,createdAt,labels`;
`git worktree list`. Per seal: read the bundle manifest directly (state, BC-01..11, review
verdict + second_reader.read ≥ 2 post-F6, no-op proof) — never the loop's claim.

## 8. Rollback, recovery, failure handling

Any F-card: single-commit revert (per-card column); loop cards revert through the loop under the
same card id. CI bricked by a new test: revert that commit (never loosen an existing check), §31
REVERSES, re-land fixed. Sealed-bytes regression: KNOWN_BLOCKED_STALE entry WITH card ref (F7
enforces); never weaken a check to match bytes. Supervisor death: liveness.yml reddens within
30–60 min; recovery = fresh session runs procedure §0; durable state = this table + channels +
reviewer_state; resume from first non-done card. Primary/lane death: loop-prompt §1.1 (incl.
pushed-but-unmerged); supervisor adopts or closes within one wake; `git worktree prune` + fresh
spawn. Wave failure: disposition + next candidate; two equivalent failures → first-principles;
a third equivalent attempt is prohibited. Usage caps: lane B pauses first, then D; primary never;
owner notified. Checkpoint miss: the table row executes automatically.

## 9. Tradeoffs & limits (honest)

Foundation-first cost ≈1 candidate off Friday. Bands: base 19–23, good 26–29, perfect = all.
Zero margin — one genuine content gap (item-54 revision failing live validation, Cells-Go BC-10,
PDF-Cpp TB-01) caps the total; visible by Saturday. F6 may newly reject marginal candidates —
that is it working; the 8 pre-sprint seals are grandfathered with their folded-REJECT history
already disclosed in PA-03's four-count; re-adjudication is recorded post-sprint debt. Monday's
count certifies warm-machine reproducibility — cold determinism (G2-W23/G5-W03), plan
canonicalization (G5-W01), dependency backfill, arrival-list relocation, PA-05, and the
site-manifest rescope are recorded post-sprint debt, each with a §31 trail. liveness.yml detects,
never repairs. "Re-run-only" classifications are verified-plausible, not guaranteed — every fresh
provider call can surface a new deterministic failure. Executor model stays pinned for the
sprint.

## 10. NEW items

Admitted 2026-09-11 as arrival items (50)–(54) in §29's G4-W17 list (the single source — this
plan references the numbers): 50 = BC-02 per-repository receipt (Cells-TS, 3D-TS) · 51 =
license-from-spdx-alone (3D-TS BC-06) · 52 = requires-python interpreter selection (Words-Py) ·
53 = FileNotFoundError-fed fixture staging (Font-Py) · 54 = quick_start conditional on
verified_examples (Words-.NET; contract revision protocol; zero-sealed-byte-movement proof).

## 11. Waves & candidate-by-blocker

Re-run-only (14): PDF-Py, Page-Py (item 40) · Cells-Py (BC-10 rerun) · Email-Py re-seal (39) ·
3D-.NET (re-seal after the 09-06 un-seal) · Email-.NET (28+PA-02) · PDF-.NET (SYMBOL_CAP) ·
Slides-.NET (source_install BC-02 path) · Cells-Java + Slides-Java (33/37/39/44/45; zero open
items) · Email-Cpp (25) · PDF-Cpp (24; TB-01 risk) · Cells-Go (28/29/45) · PDF-TS (31 + batching
+ 35; primary runs it, never a lane).
Single-item (5): HTML-Py + Note-Py (41+42) · BarCode-Py (43) · Slides-Cpp (26) · PDF-Go (47; 46
landed dd7dc73).
Admission-gated (5): Cells-TS + 3D-TS (50/51) · Font-Py (53) · Words-Py (52) · Words-.NET (54).
Not sealable: PSD-.NET, PSD-Py (disabled), TeX-Py (F10: upstream unchanged).

Waves: W-PY1 (Thu night, primary): PDF/Page/Cells-Py + Email-Py re-seal → W-JAVA (lane C, Thu):
Cells→Slides-Java → W-GO (lane D, Thu): Cells-Go → W-NET (Fri, primary): 3D/Email/Slides/PDF-.NET
→ W-PY2 (Fri): HTML/Note/BarCode → W-CPP (lane B, Fri): Email/PDF-Cpp; Sat: Slides-Cpp → W-TS
(lane B, Sat): Cells/3D-TS; PDF-TS primary; PDF-Go lane D → W-SUN: Font-Py, Words-Py, Words-.NET,
Cells-Cpp re-seal attempt (policy: §31 2026-09-11), sweep 2 over the remainder.

## 12. Lane spawn recipe (procedure §2b)

Between runs only: append `- id: G4-W1x-RERUNn, status: PENDING` naming target repos +
unlocks-under-test to the lane yaml; spawn Agent (general-purpose, model opus, isolation
worktree, background): "Read project/loop-prompt-lane.md in full and follow it; your lane is
<lane>. Work ONE item this run — <ITEM> — land it by PR (branch <lane>/<ITEM>, label <lane>,
squash-merge when CI green), then end with the report." Record the agent id in
reviewer_state.lanes. One live run per lane; never edit a lane-owned file while live; mid-run
corrections only by `Reviewer:` SendMessage to the recorded agent id.

## 13. Control plane

Supervisor cadence: event notifications (lane completions, monitor lines) + hourly heartbeat
(first act: `reviewer_check.py --record` + liveness poll) + the dead-man under both + the dated
checkpoints as scheduled wakes. Channels, roles, lane liveness contract, wakeup policy,
enforcement placement: `docs/SUPERVISION.md` (authoritative). Precedence: loop-prompt.md §0/§6
always win; this plan replaces only selection/cadence; the instructions channel overrides a
card's text for that card.
