# 14 - Lane R dependability: forensics, root causes, design (2026-10-16)

One named question: why can Lane R not be trusted to produce a README a human can publish, and what
change makes it dependable. History and analysis, never a cursor or a task list: the work is the
cards G3-W12 to G3-W19 (`docs/EXECUTION_STATE_MACHINE.md` G3; `project/state.yaml`). Evidence and checksums:
`evidence/lane-r-dependability/` (P kept units, Q claims, R determinism and review, S restore
experiment, T research; `ledger_baseline.json` is re-derivable from `candidates/`). The plan record:
`docs/DECISION_LOG.md` 2026-10-16 (D8), which is a plan answering the owner's request to investigate and plan, not an authorization to run the cards beyond the measurement card. Agent-written reports are approximate where they say so; the
ledger baseline was re-run against the committed bundles.

## 1. Symptom

Over 30 sealed bundles (control revision `4a7baf11`): `authorizable` 0/30. Hand triage of 34 candidates
found about 22 factual errors in 14 sealed bundles, every one of which the pipeline had ACCEPTed.
Agent repair of the 15 best candidates converged on the live README (the repair mostly restored live text).

## 2. Findings (F, with severity)

| ID | Sev | Finding | Evidence |
|---|---|---|---|
| F1 | Critical | Keep decisions are not honoured: 389 of 746 PRESERVE/MOVE units (52%) are not printed. | `ledger_baseline.json`; P |
| F2 | Critical | A claim is checked for a citation, not for truth. BC-04 tests that a cited fact id exists and is SUPPORTED (`validation/registry.py:1267-1281`) and backtick spans against a global whitelist (`:1337-1349`); words, numbers, versions, "supports / not functional" are not checked. | Q (10 traced cases) |
| F3 | Critical | The reviewer is overruled: the model returned REJECT on 26 of 30 candidates (22 presentation, 4 factual; one source counted 27 by including a re-read); the fold stack overturned every one; 30 of 30 sealed ACCEPT, none with a blocking finding. | R, Q; `review/independent/review.py` |
| F4 | High | "Unsupported" is used as "false": 316 of 338 OMIT_UNSUPPORTED cite no fact (93%); examples are a maintainer's null-return note, "Or build from source:", a Contributing heading. | ledger baseline; sampled |
| F5 | High | "Redundant" is an unverified rationale string: 1,514 SUPERSEDE_REDUNDANT (55%); exact text still present: tables 0/205, lists 14/273, paragraphs 28/266. | ledger baseline |
| F6 | High | The ledger has no position or grouping, so verbatim printing onto generated text produces a pile (J6 passes 2 of 26; 72% of insertions are guessed positions; 116 of 146 inserted headings have no body). | S |
| F7 | High | Reruns are memoized, not stable: 8 request hashes were called twice, all 8 answers differed. Replay proves memoization only. | R |
| F8 | High | The reviewer shares the author's model (qwen3-next, 608 of 608 calls); second and third reads are the same prompt with another seed. gpt-oss is the only other chat model and is barred from sealing by the 2026-10-04 owner decision. | R |
| F9 | Medium | Staleness: 14 of 34 candidates drifted after seal (`pip install aspose-note` was right at the seal and wrong after a rename); one of 30 bundles holds a registry-version fact, so BC-14 cannot fire. | Q |
| F10 | Medium | Formatting junk reaches candidates (dangling "...:", garbled badge, split PEP 508 spec, scraped XML-doc fragments as API rows): a deterministic lint exists nowhere. | Q (F, G classes) |

## 3. Root causes (drilled to the stable cause)

- **Symptom: invented or wrong claims reach candidates.** Local: BC-04 is a citation check. Systemic: no stage
  verifies entailment. Machinery: the validator layer was built to be cheap and green (a citation is
  cheap). Governance: principle 22 ("anything else is advisory and never blocks twice") let a REJECT be
  demoted by scope rules. Workflow: nobody measured the defect escape rate, so a green check meant "the check ran".
- **Symptom: content loss.** Local: `placement.py:102` marks heading, badge_row and html_block as "rendered
  elsewhere", and an overlap rule (`:735-757`) drops units. Systemic: Lane R *rewrites* the document and treats
  the live README as input to a ledger instead of as the skeleton. Machinery: BC-05 (`registry.py:1422-1481`)
  never inspects headings, badge rows, html, overlap paragraphs, tables or API lists. Governance: ESM principle 8
  ("preserve ... or explicitly omit") accepts an omission with no evidence code.
- **Symptom: unstable reruns.** Local: regeneration is stochastic at pipeline-sized prompts. Systemic: "no-op"
  was defined as a replayed cache. Governance: principle 11 and G1.8 do not distinguish memoization from a fixed point.
- **Symptom: the plan reports progress without dependability.** G3 exit predicates are bump-immunity, a judge
  verdict and one propose; none measures defect escape, reviewer catch rate or rerun stability. The plan could
  go green while Lane R shipped wrong claims.

## 4. Plan-to-reality mismatches found in the active plan (healed in the same change)

1. ESM section 1 defines Lane R as "composes from scratch" while D1 and `README_STANDARD.md` say the live README is the standard and the
   skeleton; healed: Lane R is live-anchored where a usable README exists (G3-W15, C4).
2. Principle 22 permitted the reviewer demotion in F3; replaced.
3. The G7 section carried about 25 lines of dated history (items 5-11 and their predicates) inside a document capped at 520 lines;
   the verbatim text moves to `docs/investigations/15-esm-g7-history-2026-10-16.md` and the plan keeps one line each.
4. A queued item exists in three places that tests keep verbatim-equal (ESM, `project/state.yaml`, `RESEARCH_AND_GUIDELINES.md` 27.9); a new item costs three
   edits. Recorded as risk R3; collapsing it is a G7-W08 hygiene candidate, not done here.
5. Stale dated figures remain in the plan ("0/34" in G0, "34 entries" in section 12); they are marked dated observations, not changed.

## 5. Design the evidence supports (what G3-W12 to G3-W19 build)

1. Measure first (C1): freeze the holdout, turn the real defects into an injection corpus, publish baseline numbers, ratchet them in CI.
2. Deterministic claim gate (C2): every identifier, number, version, package, format and framework in prose equals a value of a cited non-identity fact; mandatory published-version fact and rename check; junk lint; head re-resolved.
3. Honest ledger (C3): only CONTRADICTED content may be deleted; a supersession needs a deterministic coverage proof; a kept unit must render; BC-05 covers every unit kind.
4. Live-anchored patch engine (C4): the live README is the skeleton; the model emits operations on stable unit ids (KEEP default, REPLACE, INSERT, DELETE with evidence); a deterministic applier copies kept bytes; reusing Lane L's apply and confinement ideas only (its Edit is a line fragment of at most 200 characters with no delete or heading insertion, so the operation type is new; G3-W15).
5. Fact-rendered sections (C5): API rows, dependencies, install, versions, counts, Navigation, At a Glance come from facts only.
6. A reviewer that can say no (C6): a REJECT stands unless a registered byte-level rule refutes it; cross-family blind review if the owner admits it (OWNER-23); catch rate measured on the C1 corpus.
7. Fixed point (C7): per-section memoization (G3-W18), honestly named: only sections whose input facts changed call the model; verdicts stored per candidate hash; human-approved golden files.
8. Pilot and exit (C8): ten repositories, blind human review, numbers against the C1 baseline, default switched only on evidence.
Support: aider's measured 3x drop in lazy elision for unified diffs; ALCE and Liu et al. (about half of cited answers not fully supported); PoLL and self-preference work on judge independence; Thinking Machines on batch-variance nondeterminism (T has the sources and what was not found).

## 6. Ruled out

- Print the kept units onto the regenerated README (S): tautological J4, pile for a reader.
- More same-model review reads (R): the same model's REJECT is already overruled.
- Title-case as the cause of missing headings: rejected, 190 of 191 are unchanged by it (P).
- Judge false positives from normalisation: zero (P).

## 7. Risk register

| Risk | Mitigation | Owner of decision |
|---|---|---|
| R1 The claim gate over-fires on live-authored text | run it on the clean set and report the flagged share of the 30 stored candidates separately (G3-W13); document the false-positive rate; scope to identifiers, numbers, versions, packages, formats | executor, C2 |
| R2 Governed version bumps invalidate candidates (the loop that cost the project weeks) | bumps only with a DECISION_LOG necessity entry; `bundle/recheck.py` scoped invalidation; no reseal wave before C8 | the G3-W12 bump rule (G7-W22 clause 2) |
| R3 Three-copy queue drifts | the same-commit edit of all three and the existing tests | executor |
| R4 The patch protocol is untested; S disproved only the append approach | C4 pilot on Cells compared with legacy R on M1-M9 before any default changes; legacy route kept until C8 | C8 gate |
| R5 gpt-oss needs a larger reasoning budget and is barred from sealing | OWNER-23; if declined, the claim gate plus entailment check on prose substitute, and the C1 catch rate decides | owner |
| R6 Counts here are approximate for agent-read classes | the C1 harness replaces them with measured numbers | C1 |
| R7 Disk and runner capacity (E: was full; a clone may be 1 GB) | clone to a bounded cache, delete after each repository | operations |

## 8. Readiness

READY WITH CONDITIONS, each checkable: (1) the owner's go (OWNER-27), a line `Owner go: <date, words>` in the D8 entry of `docs/DECISION_LOG.md` in a commit the owner authored, before G3-W13 to G3-W19, and a `Start G3-W12` line for the measurement card; (2) the `tools/` exception is recorded (`docs/REPOSITORY_LAYOUT.md`, `tools/README.md`, `project/loop-prompt.md`) and is dormant until G3-W12 creates `tools/lane_r_audit/`; if the owner does not start G3-W12 it is reverted; (3) OWNER-24 before G3-W14's first bump; (4) OWNER-25 before G3-W19; (5) OWNER-26 before G3-W14's mapping field, G3-W15 and G3-W18; (6) OWNER-23 only for G3-W17's cross-family route; (7) G3-W18's M7 is the memoization proof only; the fresh-process proof stays G5-W02's. G3-W12 (measurement, no product change) is the only item that may start now.

## 9. Audit round 1 (three independent adversarial audits of commit 1aafd9dc; reports in `evidence/lane-r-dependability/plan-audit-1/`)

Counts: governance and executability 22 findings (2 Critical, 8 High), feasibility and measurement 17 (2 Critical, 8 High), adversarial 28 (3 Critical, 11 High). All three read the committed text and ran the repository's tests; none of the findings was visible to the existing tests. What changed because of them:

- **Authority.** D8 had been written as an owner decision; the owner asked to investigate and plan. It is now a plan: only the measurement item may start, the rest wait for an explicit `Owner go`, and the 2026-10-14 directive stands. The AGENTS.md necessity test I had cited does not exist; the rule is G7-W22 clause (2) and is now stated that way.
- **Metrics that could not fail.** M1 counted only the units the model chose to keep (so moving a unit to DEFER gave 100 percent) and M4 to M5 were identities of the gates being built. M1 is now over all live units with computed evidence, DEFER counts as not accounted, M1 to M5 are implemented outside the gates, a yield metric M9 was added, floors are numbers, and catch rate is differential on a dev/test split with synthetic mutants and clean twins.
- **Reproducibility.** `present` clones the current upstream head, so re-running the 30 inputs measures moved inputs, and a scratch root that tracks `candidates/` is overwritten in place. Validation is now an offline replay of the deterministic stages over pinned inputs, a scratch-root script refuses to run near a tracked `candidates/` or on a nearly full disk, and the pilot uses a pinned-revision option.
- **Rollback claim.** My claim that a reverted bump never invalidates was false for any bump that adds or alters fact records (none of the 30 bundles carries `consumed_fact_ids`). The rule now says which bumps are safe to revert, which are not, and requires a bump-and-revert test on the stored bundles.
- **Deletion and fallback.** CONTRADICTED is computed by code and never asserted by the model; a malformed patch operation keeps the unit (the earlier fallback was a rewrite).
- **Wrong premises about reuse.** Lane L's `Edit` is a line fragment of at most 200 characters with no delete or heading insertion, unit ids are ordinal, `present` has no mode, and a second unit inventory would break J4 and BC-05; the C4 card now says so and lists the real owned paths, the schema proposal, and the bundle mapping.
- **Completion tests.** C8 could complete at a 0 percent accept rate; it now has numeric thresholds, a named blind protocol and verdict files committed by the owner, and the judge is frozen for the pilot. The rung 7 proposal path that could publish a legacy candidate is closed until the claim gate is complete, and the propose gate now refuses a stale bundle.
- **Structure.** One 28,000-character queue entry became eight queued items (G3-W12 to G3-W19), each with its own status, and each owner item names the item that consumes it, so only that card is ever blocked. Card acceptance reuses the existing rule that ties COMPLETE to a gate-manifest record, so no new status test was needed. The ship loop gained a promotion rung (5a), and stale text in `project/loop-prompt.md`, `DEFECT_INDEX.md` and this document was corrected.

Residual risks, stated plainly: the live-anchored patch engine is untested and the legacy route stays the default until the pilot; the false-positive rate of the claim gate is unknown until G3-W13 measures it; the human review depends on the owner's time (OWNER-25); the numeric floors are proposals; the extractor bump needed by the published-version fact leaves candidates UNVERIFIED and conflicts with the first G3 exit bullet, so it needs its own entry; AGENTS.md line 137 still says "regeneration from scratch" (flagged for the owner, not edited). A second audit round is the next step before any card beyond G3-W12 starts.

## 10. Audit round 2 (reports in `evidence/lane-r-dependability/plan-audit-2/`)

A fresh auditor checked closure of the 34 Critical and High findings of round 1 against the committed revision 2: 17 resolved, 16 partial, 0 open, 1 accepted as risk (recall of the capability lexicon, measured at G3-W13). It found no new Critical, 9 High, 18 Medium and 4 Low issues, all in the text of the plan rather than its structure: the owner's go had no machine form (now OWNER-27), the judge hash pinned by the pilot would have been invalidated by a later card (the hash is now recorded by G3-W17, the last card that may edit it), the first card's validation could not match its own baseline (a v2 baseline file is now part of it), M6's reviewer part is nondeterministic (split into a ratcheted deterministic part and a live reviewer part), the disk guard could never pass on this machine, the ratchet needed CI wiring no card owned, the exit predicate measured the ledger floors on the legacy route where they cannot be met, and the memoization proof depended on a G5 item. Revision 3 integrates all of them. Accepted as stated risks and not changed: the card text is long (about 30,000 characters across eight items); C7 may belong inside C4; the schedule estimate is seven to ten calendar weeks of agent work before any owner wait; the single largest cost risk is a void of the pilot by a late version bump, mitigated by freezing governed versions when G3-W18 closes and running the pilot once. Verdict: G3-W12 READY WITH CONDITIONS (the owner's start order); G3-W13 to G3-W19 NOT READY until the owner's go.
