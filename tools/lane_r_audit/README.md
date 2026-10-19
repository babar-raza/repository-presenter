# tools/lane_r_audit

The Lane R dependability harness (G3-W12 card C1). It measures; it decides nothing for the product.
Written by the loop under the recorded `tools/` exception, imports `src/` read-only, makes no model
call, no network call and no GitHub write. `python -m tools.lane_r_audit pin|measure|baseline`.

| Module | What it owns |
|---|---|
| `pinned.py` | the pinned reader: the 30 sealed bundles as git blobs at control revision `4a7baf11`, checked against `data/lane_r_corpus/pins.json` (repository, revision, manifest sha256, live README sha256, survey sha256). A missing revision or a changed byte raises `PinnedInputError`; nothing skips. |
| `ledger.py` | M1, M2, M3 and the v1 reproduction, through the judge's clause readers (read-only). |
| `claims_ref.py` | M4: independent reference checker (identifiers, numbers, versions, packages, format names in LLM-owned prose against the cited non-identity facts). |
| `lint.py` | M5: junk lint (dangling colon, split spec, scraped XML-doc residue, badge syntax). |
| `detectors.py` | the detector registry for M4 to M6: a `Detector` reads a `Subject`; the gates BC-04, BC-14 and the reviewer are registered beside the reference detectors. |
| `baseline_gates.py` | BC-04 and BC-14 run on a pinned bundle (the only module importing `validation/`). |
| `corpus.py` | cases, the dev/test split (a fixed hash of the repository name), differential catch, exact binomial lower bounds. |
| `mutator.py` | the seeded mutator that writes the synthetic mutants. |
| `build_corpus.py` | the hand specs (traced T1 to T10, hand-found) and the builders (ledger, mutants, clean negatives); `corpus build` writes and `corpus check` proves `data/lane_r_corpus/cases/` is its output. |
| `corpus_report.py` | corpus catch rates per class and half; the gate half (BC-04, BC-14) runs in worker processes. |
| `ratchet.py` | the best value of M1 to M5, M6d, M9 (`data/lane_r_corpus/ratchet.json`), regressions, waivers (at most 14 days). |
| `control_rerun.py` | today's S9 blocking checks over the 30 pinned bundles, beside the validator version each was sealed under (`control-rerun`). |
| `sampler.py` | the M8 claim sampler with its committed seed. |

`ledger.py`, `claims_ref.py` and `lint.py` import nothing from `validation/`, `reconciliation/` or
`composition/` (`tests/test_lane_r_audit.py` checks the imports), so a gate never grades itself.

## Metrics and where they come from

| Metric | Definition (frozen in `data/lane_r_corpus/ledger_baseline_v2.json`) |
|---|---|
| M1 | accounted / all live units, NON_CONTENT aside; accounted = byte-identical in the candidate, or removed with computed CONTRADICTED evidence, or superseded with an M3 coverage proof; DEFER_UNRESOLVED is not accounted |
| M2 | OMIT_UNSUPPORTED rows with no CONTRADICTED cited fact (baseline 318 of 338) |
| M3 | SUPERSEDE_REDUNDANT rows whose destination section carries under 0.8 of the unit's identifier and word tokens (threshold provisional, frozen in the baseline file) |
| M4 | claim escapes: version, number, identifier, package or format tokens in an LLM-owned unit that no cited non-identity fact supports |
| M5 | junk-lint hits in the sealed README |
| M6 | differential catch on the corpus test split, per class: M6d the deterministic gates (BC-04, BC-14; CI, ratcheted), M6r the reviewer (live, three runs, never in CI) |
| M9 | judge-authorizable candidates over the 30 pinned inputs, printed beside every other metric |

## M7 procedure (rerun behaviour)

1. Regression half (already measured here as `m7_regression.J5_pass`, 30 of 30): each manifest
   records a byte-identical rerun with zero provider calls. This proves memoization only.
2. Behavioural half (C7, G3-W18): with a counting fake provider, rerun `present` over a fixture
   repository whose sections are unchanged and assert zero provider calls and byte-identical
   output; then change one fact and assert that only the sections whose digest includes that fact
   are re-rendered (calls equal the number of affected sections). The fresh-process, empty-runs/
   proof is G5-W02's acceptance, not a G3 predicate.

## M8 procedure (claim-level blind audit)

`sampler.py` documents and implements it: build the claim universe from the pilot's candidates,
draw 200 claims with the committed seed, give the auditor the blind form, accept at zero
unsupported or contradicted claims and report the exact upper bound beside it. The pilot (C8)
draws the sample, not C1.

## M6r procedure (reviewer catch, live)

Run the committed command at least three times over the test-split cases with the live reviewer
(owner-run, a provider call per case); report the per-case catch fraction and its lower bound.
It is never run in CI, never ratcheted and never mixed into M6d.
