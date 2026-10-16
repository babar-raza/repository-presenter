# 14 - Lane R dependability: forensics, root causes, design (2026-10-16)

One named question: why can Lane R not be trusted to produce a README a human can publish, and what
change makes it dependable. History and analysis, never a cursor or a task list: the work is the
cards of G3-W12 (`docs/EXECUTION_STATE_MACHINE.md` G3; `project/state.yaml`). Evidence and checksums:
`evidence/lane-r-dependability/` (P kept units, Q claims, R determinism and review, S restore
experiment, T research; `ledger_baseline.json` is re-derivable from `candidates/`). Owner direction:
`docs/DECISION_LOG.md` 2026-10-16 (D8). Agent-written reports are approximate where they say so; the
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
| F3 | Critical | The reviewer is overruled: the model returned REJECT on 26-27 of 30 candidates (4 factual); the fold stack overturned every one; 30 of 30 sealed ACCEPT, none with a blocking finding. | R, Q; `review/independent/review.py` |
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
   skeleton; healed: Lane R is live-anchored where a usable README exists (G3-W12 C4).
2. Principle 22 permitted the reviewer demotion in F3; replaced.
3. The G7 section carried about 25 lines of dated history (items 5-11 and their predicates) inside a document capped at 520 lines;
   the verbatim text moves to `docs/DECISION_LOG.md` (2026-10-16 archive entry) and the plan keeps one line each.
4. A queued item exists in three places that tests keep verbatim-equal (ESM, `project/state.yaml`, `RESEARCH_AND_GUIDELINES.md` 27.9); a new item costs three
   edits. Recorded as risk R3; collapsing it is a G7-W08 hygiene candidate, not done here.
5. Stale dated figures remain in the plan ("0/34" in G0, "34 entries" in section 12); they are marked dated observations, not changed.

## 5. Design the evidence supports (what G3-W12 builds)

1. Measure first (C1): freeze the holdout, turn the real defects into an injection corpus, publish baseline numbers, ratchet them in CI.
2. Deterministic claim gate (C2): every identifier, number, version, package, format and framework in prose equals a value of a cited non-identity fact; mandatory published-version fact and rename check; junk lint; head re-resolved.
3. Honest ledger (C3): only CONTRADICTED content may be deleted; a supersession needs a deterministic coverage proof; a kept unit must render; BC-05 covers every unit kind.
4. Live-anchored patch engine (C4): the live README is the skeleton; the model emits operations on stable unit ids (KEEP default, REPLACE, INSERT, DELETE with evidence); a deterministic applier copies kept bytes; built on the Lane L engine.
5. Fact-rendered sections (C5): API rows, dependencies, install, versions, counts, Navigation, At a Glance come from facts only.
6. A reviewer that can say no (C6): a REJECT stands unless a registered byte-level rule refutes it; cross-family blind review if the owner admits it (OWNER-23); catch rate measured on the C1 corpus.
7. Fixed point (C7): copy-through; only units whose input facts changed call the model; verdicts stored per candidate hash; human-approved golden files.
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
| R1 The claim gate over-fires on live-authored text | run it on the 30 live READMEs as a negative control; document the false-positive rate; scope to identifiers, numbers, versions, packages, formats | executor, C2 |
| R2 Governed version bumps invalidate candidates (the loop that cost the project weeks) | bumps only with a DECISION_LOG necessity entry; `bundle/recheck.py` scoped invalidation; no reseal wave before C8 | AGENTS necessity test |
| R3 Three-copy queue drifts | the same-commit edit of all three and the existing tests | executor |
| R4 The patch protocol is untested; S disproved only the append approach | C4 pilot on Cells compared with legacy R on M1-M8 before any default changes; legacy route kept until C8 | C8 gate |
| R5 gpt-oss needs a larger reasoning budget and is barred from sealing | OWNER-23; if declined, the claim gate plus entailment check on prose substitute, and the C1 catch rate decides | owner |
| R6 Counts here are approximate for agent-read classes | the C1 harness replaces them with measured numbers | C1 |
| R7 Disk and runner capacity (E: was full; a clone may be 1 GB) | clone to a bounded cache, delete after each repository | operations |

## 8. Readiness

Plan updated and verified (section C of the handoff in the change). Verdict recorded in `docs/DECISION_LOG.md` D8: READY WITH CONDITIONS - no
card has started; C1 is READY, the rest are gated on their prerequisites and OWNER-23.
