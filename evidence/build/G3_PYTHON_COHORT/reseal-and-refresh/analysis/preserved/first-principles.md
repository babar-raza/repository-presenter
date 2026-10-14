authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Why sealed is not authorizable: first-principles analysis

Date 2026-10-11. Read-only lane. Code under test: `integration/cut2c` (`f69f75c7`, worktree `runs/wt/int-cut2c`). Evidence: the five wave-3 sealed bundles (`G:\rp-w3\<name>\candidates\...`), the six baseline bundles (`E:\rp`, `E:\rp-slice`), the 11 acceptance records, protocol TC-ACC-01 v1.1 (`wt/lacc-acc01`), and my own offline replays (scripts in `scratchpad\fp\`, section 8). No provider call, no network, no write to any bundle, tracked file or Aspose repository.

## 0. Answer in ten lines

1. The pipeline and the acceptance protocol measure different things. The gates (BC-01..BC-14 plus an LLM reviewer) check **mechanics and references**: ids exist, commands match facts, links resolve, structure matches the shell. The protocol checks **the rendered text against the live README, the clone and the registries**. 31 of the 33 wave-3 blocking findings sit in the three protocol conditions that no gate measures (live content kept, claims true, prose not garbled); only 2 sit in conditions the gates do measure.
2. It is not model noise. 25 of 33 findings (76%) are decidable deterministically from data the pipeline already holds (candidate text, facts, dispositions, live README, clone, registry). Only 1 needs a semantic judge; 7 are free-written prose (invented audience, description from a name alone). A prototype of two new blocking checks flips **5 of 5** wave-3 bundles and **6 of 6** held-out baseline bundles to failing through the repo's own `recheck` machinery, and raises no false positive on 7 of the 11 detector classes (hole, fragment, duplicate, near-duplicate, filler, audience, exclusivity) over the 11 live READMEs.
3. The sealed count is the wrong metric. `project/state.yaml` reports 29 of 36 "current candidates"; the acceptance outcome on the reviewed sample is 0 of 11. `DEFECT_INDEX.md` REV-V2-02 records the deliberate reason: gating `READY_FOR_PROPOSAL` on the acceptance score is "OWNER-13 part two, unanswered; gating would drop every sealed bundle".
4. Regeneration is net-negative by construction. 30 of the 32 false-claim findings are **introduced** (absent from the live README); only 2 are inherited. The live READMEs are already structurally conformant (28 of 35 distinct repos pass a 7/7 section + mermaid test) and richer; regeneration keeps only about half of their substantive sentences (pooled upper bound 52%).
5. The code makes the loss invisible: `placements()` drops a whole preserved unit when **any one** fact id overlaps planned content; BC-05 then skips it ("dropped for fact-ID overlap") and BC-08 skips every prose unit (`category == "unit"`). 34 units were dropped that way across the five bundles; 15 keep under 80% of their substance.
6. The reviewer cannot see what acceptance sees: same model for every stage (`qwen3-next`, T=0, seed 1), told the original "is evidence, not the standard", told renderer-owned text (API tables, install, diagram) is out of scope, and bound to the facts as "the only source of truth". All five bundles came back ACCEPT with zero findings.
7. Gates are an enumerated catalogue (103 distinct "arrival item" patches in `src/`; BC-07's own comment calls its list "hand-curated, fitted-to-observed-cases"). The failure space is open, so each wave finds new classes.
8. Recommendation: (B) now, as a gate and a deterministic fill; (A) as deterministic parity checks plus a regression corpus, with the LLM second reader demoted to a narrow adjudicator; (C) as the production shape: **live README first, gaps authored, claims verified, otherwise no change** (this is what `plans/idea.md` L319-321 already prescribes as the "fast path").
9. Honest odds (section 7): regeneration plus fixes reaches about 2-4 of 36 authorizable by Oct 16 and 5-9 by Oct 23; the patch-first shape about 14-20 by Oct 16 and 20-27 by Oct 23. Neither is likely on Monday itself.
10. Do not run another reseal wave on unchanged code: it produces sealed candidates, not authorizable ones.

## 1. What "authorizable" requires, and what the gates check

Protocol section 8, all seven required for `AUTHORIZABLE`:

| # | Protocol condition | Pipeline coverage (evidence) | Blocking findings that fall here (of 33) |
|---|---|---|---|
| 1 | NET versus live is better or equal; no valuable live content missing (also binds `idea.md` L339-340 and profile disqualifier D10) | None for prose, links, badges, limitations, capabilities. BC-05 counts dispositions; BC-08 protects only command lines and ecosystem code blocks; BC-10 is told the original is not the standard | 9 |
| 2 | Zero false or misleading claims in at least 10 spot checks, introduced or inherited, plus zero true demoted findings | BC-02/03/14 cover install, examples, version. BC-04 checks that cited fact ids exist and are SUPPORTED, not that the sentence is entailed. Counts, capabilities, audience, API descriptions, scope claims are uncovered | 15 |
| 3 | Zero forbidden wording, zero forum links | BC-06/07/12 plus fitted phrase lists. Covered except new phrasings ("higher-tier", "swap to the commercial package") | 1 |
| 4 | Template conformance | BC-07 plus renderer. Covered except the verbatim-fence exemption | 1 |
| 5 | No dangling, garbled or duplicated prose | A narration list only. No detector for holes, fragments, duplicates, filler, dangling references | 7 |
| 6 | Candidate revision equals live head | BC-01 plus the drift monitor | 0 |
| 7 | State READY_FOR_PROPOSAL, nothing failed | By definition | 0 |

So the gates are sound on the mechanical conditions (3, 4, 6, 7) and silent on the content conditions (1, 2, 5). That is the structural relationship: **the pipeline's "accept" is a conjunction of reference checks; the protocol's "accept" is a conjunction of content checks, and the two sets barely intersect.** The 30-point profile does not bridge them: 8 of its 26 criteria (9 points) are `review` evaluators credited "reviewer ACCEPT; no finding names these sections" (`review.json acceptance_profile`), 9 delegate to the same BC checks, and the score does not gate READY (profile.py docstring). The bundles scored 28/30 and 27/30; the two misses are a banner-link cosmetic (C01) and one fence (C13).

## 2. Classification of every finding

Rule: **(a)** a deterministic validator over candidate text, facts, dispositions, live README, clone or registry can decide it; **(b)** only an LLM or heavy semantic reading can; **(c)** the composer free-wrote prose or an inventory (closed by removing the freedom, detected by a novelty gate).

Wave-3, 33 blocking findings: **(a) 25 (76%), (b) 1 (3%), (c) 7 (21%).**

| Candidate | (a) deterministic | (b) semantic | (c) generation policy |
|---|---|---|---|
| 3D-.NET | B1 `dotnet build` fails from stated cwd; B2 "18 test files"; B3 14+ API holes; B5 "ToMesh throws" false (AST); B6 limitations dropped; B7 dev deps dropped | B4 U3D/RVM/AMF/HTML5 read/write (needs importer registry reading) | none (opening clean) |
| 3D-Java | B4 five doc links dropped; B5 limitations dropped; B6 badge, Kotlin, family sentence dropped; B7 "higher-tier", "swap to the commercial package" | none | B1 invented audience; B2 "other 3D formats" vs STL-only Scope; B3 package called a class plus stale "listed below by module" |
| Cells-.NET | B1 split code spans; B2 Scope list twice; B3 ". it adds" fragment; B4 "table below" with no table plus raw dump; B6 capabilities, notes, badge dropped | none | B5 invented audience |
| 3D-TypeScript | B2 "33 test files"; B4 3MF and six limitations dropped; B5 "saving to OBJ" vs format direction facts; B6 AGENTS.md, diagram sources dropped; B7 "81 types" vs 140 exports | none | B1 StepMode described from its name; B3 invented audience |
| Cells-Java | B1 "sole published version" vs registry list; B2 fence without language; B3 ". it adds"; B5 "38 test files"; B6 capabilities dropped | none | B4 invented audience |

By protocol category over all 75 blocking findings (33 wave-3 plus 42 baseline): false or misleading 32, dropped live content 19, dangling or garbled 12, template 3, demoted-finding-true 4, other 5. Of the 32 false-claim findings, **30 are tagged `introduced`, 2 `inherited`**. Every one of the 17 MAJOR fixes in the wave-3 records is `code_change`; none is repairable by a redraw.

Prototype recall on these 33, measured (section 5): 24 detected (73%); 21 with text, facts and dispositions only; 3 more with a clone count. The nine misses: 3D-.NET B1 (needs execution), B4, B5, B7 (soft match too lenient); 3D-Java B2, B3; TS B1, B5, B7.

## 3. Structural root causes, each verified

### RC-1. The unit of progress and the READY gate exclude the outcome

- `AGENTS.md`: "Count progress in one unit only: current reviewable no-op-proven candidates, N/34." `project/state.yaml`: `current_candidates: 29`, `denominator: 36`.
- `review/acceptance/profile.py` docstring: the score "does NOT gate `READY_FOR_PROPOSAL`, which stays blocking checks BC-01..BC-11 plus no-op proof".
- `docs/DEFECT_INDEX.md` REV-V2-02: "Still open, deliberately: no blocking check reads the score before READY_FOR_PROPOSAL (OWNER-13 part two, unanswered; gating would drop every sealed bundle)". REV-V2-09: the text predicates (`text_checks.py`) "feed only the advisory scorer, never `validation/registry.py`".
- Consequence: every incentive points at sealing. The BC-10 triage (`bc10-triage.md`) classed 31 of 60 reviewer findings as "reviewer error / over-strict / renderer-owned", and the follow-up fixes are scope rules that demote more findings (`wave3-triage.md` U8 proposes another); the baseline acceptance reviews then found the demoted findings "mostly TRUE" (`acc-baseline-vs-slice.md`).

### RC-2. The product shape discards the best evidence, and the code hides the loss

- Regeneration: the live README becomes `inherited_unit` facts with one disposition each; `SUPERSEDE_REDUNDANT` is a promissory note ("it will be re-authored", 3D-.NET unit 004) that nothing checks.
- `composition/placement.py:placements`: `overlap = tuple(sorted(set(entry.get("fact_ids") or []) & covered))`; `outcome = "overlap" if overlap else "placed"`. **One shared fact id drops the whole unit.** README_CONTRACT §3 states "the planned, freshly-authored content wins".
- `validation/registry.py:_check_dispositions`: `if placement.outcome != "placed": continue  # ... or dropped for fact-ID overlap`. BC-05 never looks.
- `validation/registry.py:_check_protected`: `if disposition not in _PLACING or category == "unit": continue`. `protected_fragments` only protects command lines and ecosystem code blocks. No prose, link, badge, limitation or capability is protected, so profile disqualifier D10 ("valuable inherited content discarded", delegated to BC-08) cannot fire.
- Worked example, 3D-Java: `dispositions.json` says unit `070.list` is `VERIFIED_PRESERVE` ("All links in the list are verified"); `plan.json` links cover 4 of its 8 targets; the overlap rule drops the unit; PUBLISHING.md, api-diff, directory-structures, progress notes never render; BC-05 and BC-08 pass.
- Measured with the real `placements()` on the five bundles (`fp\placed.py`): 34 placing units dropped as `overlap`; 15 of them keep under 80% of their token content in the README (3D-.NET 061.list limitations 67%, 3D-Java 070.list links 68% and 072.list limitations 69%, TS 074.list limitations 65%, Cells-Java 048.list 67%).
- The live README is better than the source: `Deformer.cs` itself reads `/// Base class for  and` (the hole is **upstream**), while the live README row reads "Base class for `SkinDeformer` and `MorphTargetDeformer`." The pipeline treated the docstring as authority and the repaired maintainer text as superseded.
- Retention versus the live README (`fp\floor.py`, upper bounds, pooled over 11): 79% of link targets, 52% of substantive sentences (range 35%-73%).
- Treatment is also unequal: verbatim-kept share of live units ranges 23% (TypeScript) to 54% (3D-Java) on near-identical template READMEs, because PRESERVE versus SUPERSEDE is a per-unit LLM choice. This is the direct answer to "why not alike".
- Inherited-versus-introduced: regeneration adds errors the maintainers did not have (30 introduced false claims) and removes verified content (19 findings).

### RC-3. Claims are validated by reference, and the spec mandates the invention

- `validation/registry.py:_check_units` (BC-04): fact ids exist and are SUPPORTED; every code span in prose is a fact value; lines in `renderer_lines` (API rows, deterministic sections) are skipped entirely.
- The sealed openings cite 13-17 facts each (`content_units.json`), so a sentence is "supported" by citation spray. Cells-.NET `investigation.json`: the audience statement ("Windows, Linux, or macOS ... serverless ... without requiring Microsoft Excel") cites `identity:platform`, `package:target_framework`, `install_command:dotnet`, none of which says that.
- `prompts/repository_investigation.yaml`: `audience` and `problems_solved` are `required`, `problems_solved minItems: 1`, every statement `fact_ids minItems: 1`. README_CONTRACT row 4 requires the opening to say "who uses it". `prompts/section_authoring.yaml` says "Invent nothing ... audience ...". The spec contradicts itself; invented audience is the schema-forced result: 4 of 4 free-form openings in wave 3, and my lexical check flags 10 of 11 reviewed candidates (0 of 11 live READMEs).

### RC-4. The reviewer is structurally unable to find these defects

- Every stage uses one model: `prompts/*.yaml` all `model_route: qwen3-next`, `temperature: 0.0`, `seed: 1`; `manifest.models_used = {'qwen3-next': 'qwen3-next'}`. `identity_separate: True` is a prompt identity, not a model.
- `prompts/independent_review.yaml`: "a difference from the original README is not a defect: the original is evidence, not the standard"; renderer-owned text "the banner, badges, identity row, navigation, installation, dependencies, At-a-Glance diagram ... API reference tables ... do not criticize"; "a finding against one is ... your own defect"; "Facts (the only source of truth)". So content that never became a fact, and everything the renderer prints, is out of its universe. The acceptance reviews found their defects exactly there.
- Precedent for silencing a correct reviewer: `composition/renderer.py:renderer_sentences` docstring: on the canary the reviewer "twice preferred the original README's stale counts - 305 public types, 33 test files - over the 337 and 34 the renderer computed". The acceptance review later ruled "34 test files" MISLEADING (33 real) and the 337/305 mismatch a false claim. The fix was to exempt the renderer's sentences from review.
- Profile criteria evaluated by `review` are met by silence. Second reader is conditional (`second_reader.triggered false` on Cells-.NET). All five wave-3 reviews returned ACCEPT, zero findings.

### RC-5. Renderer-owned text carries defects the contract mandates or no check owns

| Defect | Where | Why nothing catches it |
|---|---|---|
| "N test files" counts every file | `evidence/facts/assets.py:_directory_fact` stores `len(matches)` "files; test suite"; `renderer.py:_development_sentences` prints "The suite covers N test files" | 6 of 11 candidates (csproj, test.log, setup.ts, helpers, `__init__.py`); clone check: 18 files, 16 declare tests; 33/32; 38/23 |
| "Defined as <signature>." and "Public method." filler | `renderer.py:_symbol_description` | README_CONTRACT row 14 allows "verified signature summary"; API rows are exempt from BC-04; reviewer barred. 312 bullets in TypeScript, 50-64 elsewhere |
| ". it adds ..." | `renderer.py:_enterprise_paragraph`: `f"{sentence} {adds}"` with a model unit that starts lowercase | Contract wording is ", which adds"; renderer joins after a full stop |
| "dotnet build" at repo root | `core/ecosystems.py:EcosystemSpec.clone_and_build` template, printed by `_installation` | BC-02 judges `install_command` facts only; this command is not a fact, though contract row 8 says "Never an unverified command" |
| Fence without language | `validation/registry.py:_fence_and_spacing_failures` exempts "a placed inherited code block" | BC-07 (blocking) is more lenient than profile C13 (advisory) |
| Inverted headings `####` then `###` | README_CONTRACT row 14 prescribes it | contract-conformant, protocol-minor |
| Wall of code spans, 15-project paragraph | units are "plain prose, no lists" plus BC-04 identifier rule | maintainers' bullet list cannot be reproduced |

### RC-6. Enumerative gates against an open failure space

- 103 distinct "arrival item" references in `src/` (`grep -rhoE "arrival item [0-9]+" src | sort -u | wc -l`); the `_NARRATION` comment in `validation/registry.py` (the list BC-07 uses): "This list stays a hand-curated, fitted-to-observed-cases catalog, not a general detector".
- `composition/list_coverage.py` was added after cut-2 to stop partial list preservation, yet 5 of 5 wave-3 bundles still lose list items: it guards only authored `scope_limitations` units (`repair/rounds.py:906`), not overlap-dropped units, not document links, and judges presence by a 50% subject-word share.
- `wave3-triage.md`: 12 failed rows had 10 distinct universal causes; each wave finds new ones. Two cohorts, 0 of 11 authorizable.

What is **not** the cause: sampling or model capability. 76% of findings reproduce deterministically from sealed artifacts, and classes recur across waves (test counts, invented audience, dropped content, filler, dangling lead-ins).

## 4. Why the system "does not work alike" for all candidates

1. Behaviour on maintainers' text depends on a per-unit LLM disposition (23%-54% kept verbatim across near-identical READMEs), then on whether the plan happens to overlap a fact id.
2. Extractor idiosyncrasies are per ecosystem (test counting, docstring holes, TS nested-literal members, constants-derived formats).
3. Free prose varies per draw: 3D-.NET's opening is clean, the other four invent an audience.
4. The gates are identical and uniformly blind, so they report uniform success. Uniformity of outcome needs a uniform rule: **keep the maintainers' text unless a machine-checkable cause says otherwise.** Regeneration cannot offer that; a floor can.

## 5. Offline experiment (reproducible, scripts in `scratchpad\fp\`)

Two prototype blocking checks, injected by monkeypatch (no repo file touched) and run through the repo's own `bundle.recheck.recheck_bundle` on copies of the sealed bundles:

- **BC-13 live floor**: every item of a `VERIFIED_PRESERVE`/`VERIFIED_MOVE` list unit must render at item granularity; every SUPPORTED live link target must still be linked.
- **BC-15 text hygiene**: holes, lower-case sentence start after a full stop, fence without language (no exemption), duplicate content, tautological filler, dangling references and lead-ins, split code spans, opening audience lexicon, non-canonical edition words, exclusivity claims.

| Wave-3 bundle | Before (cut2c code) | After (+BC-13, +BC-15) | Representative failing lines |
|---|---|---|---|
| 3D-.NET | CURRENT | UPDATE_REQUIRED (recompose) | 061.list 3 of 8 limitation items not rendered; 20 hole hits (`Base class for  and`); 50 `Defined as` bullets |
| 3D-Java | CURRENT | UPDATE_REQUIRED | 070.list 4 of 8 links not rendered; 072.list 3 of 9 limitations; "higher-tier", "swap to the commercial"; audience lexicon x4 |
| Cells-.NET | CURRENT | UPDATE_REQUIRED | ". it adds"; Scope bullets duplicated x4; 3 split spans; "table below" with no table; audience |
| 3D-TypeScript | CURRENT | UPDATE_REQUIRED | 074.list 9 of 12 limitations; AGENTS.md link; 312 filler bullets; `Node`.js split |
| Cells-Java | CURRENT | UPDATE_REQUIRED | ". it adds"; fence without language; "sole published version"; 048.list 2 of 5; audience |

Hold-out (tuned on wave 3, applied to the six baseline bundles from a different code version): **6 of 6 fail**, with hits matching the earlier reviews (dropped Enterprise Edition link in BarCode, Cells-Python, Cells-Go; dangling lead-ins in 3D-Python and Cells-Go; 6 of 10 scope items lost in 3D-Python; filler in four). Undetected there: the "member AUTO" garble, "textured crate", COLLADA export claims (semantic or registry classes).

Control (the same detectors on the 11 **live** READMEs): hole 0, fragment 0, duplicate 0, near-duplicate paragraph 0, filler 0, audience 0, exclusivity 0 (no false positive in seven classes); dangling 1 (a true inherited leftover, Cells-.NET "table below"); fence-language 3 and edition-word 3 (true inherited defects a patch should fix); split-span 3 false positives (needs a renderer fix for path wrapping, not a lexical rule); one edition false positive in a candidate ("full commercial rendering pipeline", 3D-.NET).

Clone-adjudicated: "N test files" claims were 18 vs 16, 33 vs 32, 38 vs 23 real, with 3D-Java correct at 11 vs 11 (`fp\clone_checks.py`). Lost verified relative links: 3D-Java FILE_FORMATS.md, PUBLISHING.md, api-diff, directory-structures, progress notes; TS AGENTS.md.

Novelty probe (`fp\novelty.py`): flag LLM-owned sentences with 30% or more content tokens absent from the live README plus non-inherited fact values. It flags 16 of 130 sentences across the five bundles: all four invented-audience or promotional openings (novelty .45-.64; Cells-Java has two such sentences) and 11 benign generic ones (issues page, development boilerplate), with no semantic model involved. It does not flag "other 3D formats" or StepMode, whose words are all known.

Limits: regex prototypes tuned on five bundles; precision measured on 11 live READMEs; recall on unseen classes unknown. The Sonnet reviewers are not ground truth either: they missed audience sentences my detector flags in baseline candidates (3D-Python, BarCode), so the bar itself is noisy and should be calibrated.

## 6. Ranked changes (smallest set that makes pipeline accept ⇒ protocol accept)

Goal is **soundness** (pipeline-AUTHORIZABLE implies protocol-AUTHORIZABLE on the corpus), not equivalence with an agent that clones and curls. Shared-code rule: one shared-code item at a time per path, so renderer/placement/registry work is serialized by lane (hours below are engineer hours).

| Rank | Change | Stage | Mechanism | Det/LLM | Effort | Closes (of 33 wave-3) | Verification (offline) | Governed impact |
|---|---|---|---|---|---|---|---|---|
| 1 | **Owner: redefine the unit and the gate** | governance | Progress unit = AUTHORIZABLE (plus NO_CHANGE_VERIFIED); READY requires BC-13 and BC-15 (answers OWNER-13 part two). Replace the AGENTS.md sentence, do not add one | n/a | 2 h | enables all | `status` prints the new count; sealed bundles show UPDATE_REQUIRED | docs; VALIDATOR bump |
| 2 | **BC-13 live floor + preserve-first placement** | S7/S9 | `placements`: split list units, drop only covered items, place the rest verbatim (live wins ties); BC-05 flags an `overlap` unit with uncovered items; BC-13 checks item presence and live link/badge targets with machine-verifiable exceptions only | Det | 16-22 h | 9 (+ 10 baseline) | `recheck`: presentation scope re-renders each sealed bundle with no provider call; BC-13 flips FAIL to PASS because the renderer fills the missing items; negative control: a dropped item must fail | RENDERER, BC-05 v6, new BC-13 |
| 3 | **BC-15 text hygiene + fix the generators it exposes** | S7/S9 | Hole, fragment, duplicate, dangling, filler, fence (normalise inherited fences to `text`, drop the exemption), edition lexicon. Renderer: `_enterprise_paragraph` normalises case or uses ", which adds"; `_symbol_description` drops `Defined as`/`Public x.` (omit the bullet; prefer the live row when the docstring is absent or holed, which also repairs the StepMode class); wrap paths as one span | Det | 14-18 h | 8-9 | Corpus replay: 5 wave-3 and 6 baseline FAIL before, re-rendered PASS after; 11 live READMEs pass except whitelisted inherited defects | RENDERER, VALIDATOR, new BC-15 |
| 4 | **Novelty gate + remove mandatory audience** | S3/S6/S9 | `audience`/`problems_solved` optional unless the live README or a fact states them; opening objective loses "who uses it" (contract row 4 amended); novelty check on LLM-owned sentences with deterministic delete-or-re-ask | Det + 1 LLM re-ask | 6-8 h | 4 | Probe: all 4 audience openings fail before; delete-and-re-render offline passes; live READMEs pass | NORMALISATION; prompts are provenance only |
| 5 | **Claim semantics against clone and registry** | S2/S9 | Count claims use files that declare tests (or print "N files under tests/"); registry versions list for "sole/only"; format-direction lint for "save/export to X"; print only verified source-build commands (discover project path) | Det | 12-14 h | 6 | Clone replay of the five; count 18/16, 33/32, 38/23 flips; build command run from stated cwd | EXTRACTOR, RENDERER, BC-02/14 |
| 6 | **Calibration corpus in CI** | tests | Store the 11 reviews as fixtures (finding id to expected check); CI asserts bundle FAIL pre-fix, live controls pass | Det | 6-8 h | prevents regression | The `recheck` harness itself | tests |
| 7 | Acceptance-rubric diff adjudicator (second reader) | S10 | Separate job: input = deterministic ADDS/DROPS/CHANGES lists plus grep evidence snippets; output typed findings with the existing `quote`/`absent`/`omission` mechanical checks; different prompt and rubric (protocol §3-5) | LLM, narrow | 12-16 h | 3-4 leftovers (StepMode, contradictions) | Replay on the 5; recall on B-leftovers | REVIEWER_LOGIC; no sealed invalidation |
| 8 | Inherited-claim verifiers (AST "throws", importer registry, export counts) | S2 | Per-ecosystem facts; verify live claims instead of trusting references | Det, heavy | 20-30 h | 3 | per-claim fixtures | EXTRACTOR |
| 9 | Patch-first / merge composer (section 7C) | S4-S7 | see below | Det + LLM gaps | 24-40 h | structural | acceptance review of output | contract + RENDERER |

Ranks 2-5 total about 48-62 h and address 28 of 33 (85%); rank 6 keeps them honest. Rank 7 is a safety net for the open failure space, not a primary lever: a tool-less LLM on the same two-model catalogue cannot clone or curl, so most of the protocol must be deterministic. Rank 8 has the lowest yield per hour; patch mode (7C) removes most of the need by keeping unverified inherited text only when it passes the existing verifiers.

### 6.1 Evaluation of the three options asked about

**(A) Acceptance parity gate.** Deterministic half: ranks 3-5 plus the corpus; measured recall 24/33 (73%) and 6/6 hold-out, zero false positives on five hygiene classes over live READMEs. LLM half: a second reader with the acceptance rubric against the live README is worth building only as the narrow adjudicator in rank 7; its independence is limited because the gateway lists two models and one is unreliable at JSON, so independence must come from different inputs and a different rubric, not a different seed. Verdict: build the deterministic half now; defer the LLM half.

**(B) Live-README floor (BC-13).** The highest yield per hour and the most direct enforcement of `idea.md` L339-340 ("regeneration convenience is never a reason to discard valuable curated information"). By itself it cannot fix inherited falsehoods (U3D, `ToMesh`, non-compiling examples), because a floor preserves them; it needs a "machine-verifiable cause" exception list (failed example receipt, 404 link, contradicted fact) so the floor never forces a known-false item back in.

**(C) Correction patch over the live README.** Two variants:
- **C1, pure patch** (no LLM prose): start from live text; operations are delete (failed example receipt, dead link, contradicted fact), replace (verified version, count, command), insert a deterministic section the shell owns (Navigation, Dependencies, Third-Party Notices, License prose, Enterprise paragraph), normalise (fence language, heading case, product-name spelling). Output is monotone: never worse than live by construction (condition 1), and every hunk has a machine-checkable reason for the reviewer.
- **C2, preserve-first merge**: the same, plus LLM-authored units only for sections or items missing from the live README, under the novelty gate. It reuses S1-S12, S4 dispositions and the renderer; it inverts one precedence rule (preserved beats planned).

How many of the 36: the 35 retrievable live README snapshots (`fp\conform.py`) give 28 distinct repos fully conformant (H1=1, 7 of 7 required sections, one mermaid), 4 near-conformant (a missing Dependencies section, a second H1, no mermaid), 3 weak (Font-Python 1/7, Slides-.NET 2/7, Words-.NET 4/7). About 80% are C1 candidates, 11% need small additions, 9% need C2. 14 of 37 snapshots match the edition lexicon (some false positives) and C1 must fix the true ones; 3 of the 5 wave-3 live READMEs contain non-compiling examples (3 of the 5 wave-3 live READMEs), which the existing example receipts already detect. The idea.md fast path ("A strong existing README may take a fast path ... an empty-patch candidate") is this design.

Residual risk of C: inherited false claims that no verifier flags still block `AUTHORIZABLE` (protocol §4: inherited blocks too). Expect about 0.7 residual findings per live README versus about 2.0 after the regeneration fixes (6.8 average blocking findings per candidate now, 70-85% caught).

## 7. Recommendation and honest probabilities

For **Monday 2026-10-12**:
1. Decide the metric: report AUTHORIZABLE and NO_CHANGE_VERIFIED; stop reporting sealed N/36 as progress (rank 1). The "29 of 36" and "0 of 11 reviewed" must not sit side by side unexplained.
2. Approve the production shape: live README first, gaps authored, claims verified, otherwise no change (C2 then C1).
3. Freeze reseal waves on unchanged code; spend lane time on ranks 2-6 instead. One lane per disjoint path: placement/BC-05/BC-13; renderer batch; registry BC-15; prompts and investigation schema; fixtures.
4. Propose none of the 11 reviewed candidates.
5. Keep the owner's acceptance protocol as the calibration oracle; turn it into the fixtures of rank 6.

Probabilities (my judgment from a per-candidate residual-defect model: 6.8 blocking findings per candidate now; a fix set catching 70-85% leaves 1.0-2.0; Poisson chance of zero is 13%-37%; about half of rows seal):

| Outcome | Regeneration + ranks 2-6 | Patch-first (C1+C2) + ranks 2-6 |
|---|---|---|
| Any of the five reviewed sealed bundles AUTHORIZABLE on Mon Oct 12 | 5-10% | n/a |
| At least 2 patch-mode outputs among the 11 reviewed READMEs rated AUTHORIZABLE on Mon Oct 12 (scripted from sealed dispositions plus a small op set) | n/a | 35-45% |
| Authorizable (or no-change verified) of 36 by Fri Oct 16 | 2-4 expected; P(at least 5) about 25% | 14-20 expected; P(at least 10) about 65% |
| By Fri Oct 23 | 5-9 expected; P(at least 18) about 5% | 20-27 expected; P(at least 18) about 60% |

Why patch-first is more likely: the starting text is already conformant and curated (28 of 35), the only introduced defects are the ones you choose to add, and the deterministic spine (facts, examples, links, registry, shell) already exists. Why it can still miss: inherited false claims need verifiers; acceptance reviewers vary; weak READMEs (about 9%) still need generation; new machinery of 24-40 h must pass the shared-code and governed-version discipline.

What would change my mind: if the rank 2-5 fixes applied to the five bundles (offline re-render plus single-section re-draws) produced three or more AUTHORIZABLE reviews, regeneration would be viable for the weak 9% and for new products; if the patch prototype's reviews find new inherited-claim classes at more than 1.5 per README, rank 8 moves up.

## 8. Reproduce

All in `C:\Users\babar\AppData\Local\Temp\claude\e--Users-prora-OneDrive-Documents-GitHub-repository-presenter\01db89e6-ba90-479a-befa-bff20834c024\scratchpad\fp\` (the main `.venv` Python with `runs\wt\int-cut2c\src` on `sys.path`; plain Python for text-only scripts):

- `ds\<name>\{cand,live}.md`: candidate and live README for 11 bundles; live recovered by `patch -R` of the bundle's `README.patch` (byte-equal to a fresh clone's README for all five wave-3 repos).
- `floor.py` (retention), `detect.py` (hygiene detectors on candidate and live), `conform.py` (live conformance, 37 snapshots in `corpus\`), `clone_checks.py` (test counts, lost links/limitations), `novelty.py`, `placed.py` (real `placements()` outcomes), `superseded.py`.
- `parity.py` (prototype BC-13/BC-15), `parity_replay.py before|after` (offline `recheck_bundle` on bundle copies in `replay_*`; before: 5 of 5 CURRENT, after: 5 of 5 UPDATE_REQUIRED/recompose), `base_bc13.py` (hold-out), `full_lines.py` (complete hit lists).

Not done: no live LLM call, no new clone, no execution of upstream build commands (B1 rests on the acceptance record), no edit to tracked files.
