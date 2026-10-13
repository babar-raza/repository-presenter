authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Why regeneration is not idempotent: first-principles analysis 2

Date 2026-10-11. Read-only lane. Code under test: `integration/cut3` (`a3b6bbf6`, worktree `runs/wt/int-cut3`). This document does not repeat `first-principles.md`; it takes its facts as given (gates check mechanics, 30 of 32 false claims introduced, 28 of 35 live READMEs conformant, about half of the sentences retained) and answers the follow-up question: **why is the result not idempotent, exactly, and what is the smallest design that makes it one.**

Evidence: 57 pipeline drafts that each carry the exact live README (`source/README.md`) plus dispositions, content units, facts, plan and ledger (26 wave-3 drafts of which 7 sealed, 25 baseline `E:\rp`, 6 slice `E:\rp-slice`; snapshot taken 2026-10-11, new drafts were still arriving); the 38 committed sealed bundles (live README recovered by reverse-applying `README.patch`); 3,356 provider-ledger rows; 37 live-README snapshots. No gateway call, no network, no write to any tracked file or Aspose repository. Scripts and raw JSON: `scratchpad\idem\` (section 9).

## 0. Answer in twelve lines

1. **Definition.** Let `P(x)` be the pipeline output when `x` is the existing README. The system is idempotent only if `P(P(x)) = P(x)` and, for a conformant `x`, `P(x) = x` plus verified corrections. Today only a weaker property holds: *replay* (`same x`, same code, same cache gives the same bytes with zero provider calls). Replay is memoization, not a fixed point.
2. **P is not a fixed-point map on its own output, by construction.** `P(x)` is built from scratch by `render_readme` over an 18-section shell (8 deterministic, 3 LLM, 7 mixed). The README's *wording* reaches the output through one narrow channel: a unit the LLM dispositions `VERIFIED_PRESERVE/MOVE` **and** that is not dropped by the placement overlap rule. Everything else is a function of the facts (the revision), not of `x`'s wording.
3. **Measured on conformant live READMEs** (29 of 37 snapshots have one H1, all 7 required sections and a Mermaid diagram, i.e. the shell's structure): sealed wave-3 candidates keep 33% of live sentences verbatim (57% in any form), 42% of live lines, with a median 49 diff hunks (24 to 94); all 57 drafts: median 44 hunks, 19% verbatim, 32% of lines. The edits that the shell and the hygiene rules actually require are a median **1** per live README (16 of 37 need zero, 33 of 37 need 3 or fewer); BC-14 finds 0.29 verified corrections per live README.
4. **Three independent sources, not one.** (A) structural: the design replaces or re-authors maintainer text even when the model is perfect (the reconciler's own "keep" decisions are dropped 33% of the time by `placements()`); (B) stochastic: the gateway is not deterministic at temperature 0, seed 1 (17 of 18 byte-identical requests returned different responses; two independent sealings of the same revision share 0 to 4% of their LLM sentences); (C) measurement: the no-op proof, the seed probe and the sealed count all test memoized replay, so nothing in the gates can see the defect.
5. **The reconciliation prompt instructs non-idempotence.** `prompts/source_reconciliation.yaml` v9: a capability list "re-authored under key_capabilities", a limitations list "re-authored under scope_limitations", a resource list "re-authored under documentation_resources" are `SUPERSEDE_REDUNDANT`. So on the second pass the generator supersedes and re-samples exactly the prose it wrote on the first.
6. **The prose it re-samples is most of the document.** 65% of non-API candidate sentences are LLM-authored. The chance an LLM output is reproduced is about 11% for a byte-identical request (2 of 18 parsed-identical, one of them byte-identical) and 0 to 4% for the sentences of two independent sealings. Estimated upper bound on non-API text stable under self-application: about 40% (derived, not measured).
7. **Inherent versus design.** Only the stochastic component (B) is inherent to "an LLM writes the text". It matters only where an LLM is called. (A) and (C) are design choices, and (A) alone guarantees `P(x) != x` for any hand-written `x`.
8. **Minimum fix.** Invert precedence: the live README is the document, a deterministic audit produces findings with machine-checkable causes, and the output is an **edit script over the live units** (copy-through by default; deterministic fill of empty or false deterministic slots; LLM only for new units and flagged units). This is the `idea.md` L319-321 fast path generalised, and it reuses `inherited.py` units (exact source lines), BC-14/02/03/06/07/12 verifiers, the renderer's section functions and `bundle/recheck`.
9. **Invariants that define the fixed point:** zero findings means identical bytes and zero provider calls; every hunk has a reason code; applying an op must clear its finding and introduce none (convergence); nothing is removed without a machine-checkable cause.
10. **Harness:** an idempotence corpus of the live READMEs with frozen facts, offline and LLM-free for the default path, plus mutation tests (inject one defect, expect exactly one op). CI gate: `P(x) = x` or hunks <= findings, `P(P(x)) = P(x)`, unexplained hunks = 0.
11. **Effort:** roughly 90 to 125 engineer-hours (12 to 16 days one lane, 5 to 8 calendar days on three disjoint lanes). The Monday live-first lane should be built as phase 1 of this, not as a throwaway.
12. **Not measured:** `P(P(x))` itself (needs the gateway), pure model variance for reconciliation and planning, strict semantic equivalence (section 8).

## 1. What "idempotent" must mean here

Notation. `x` is the existing README at upstream revision `r`. `F = E(r) + U(x)` are the facts: `E(r)` the facts extracted from the repository, `U(x)` the `inherited_unit` facts and example candidates derived from `x`. The pipeline is

```
inv   = L3(F)                      S3 investigation   (LLM)
disp  = L4(U(x), F, inv)           S4 reconciliation  (LLM, one disposition per unit)
plan  = L5(F, inv, disp)           S5 planning        (LLM)
units = L6(F, plan, disp)          S6 authoring + S8 coherence (LLM)
P(x)  = R(shell, F, plan, units, disp)   S7 render (deterministic)
```

A graded definition, because "no-op" in `docs/STATE_MACHINE.md` §10 is only the first rung:

| Level | Property | Meaning | Status today (measured) |
|---|---|---|---|
| I0 replay | same `x`, same code, same call store gives same bytes, zero provider calls | memoization, keyed by `canonical_hash({prompt_sha256, payload})` (`core/llm/jobs.py`) | holds (by construction) |
| I1 reproducibility | two fresh runs on the same `x` give the same bytes | stochastic stability of the stages | **fails**: 2 of 18 identical requests gave the same parsed output; 0 to 4% of LLM sentences and 9 to 53% of non-API lines shared between two sealings of one revision |
| I2 fixed point on conformant input | `P(x) = x` plus verified corrections | the mission wording "proves unchanged no-op behavior" and "preserves valuable inherited content" | **fails**: 33% of live sentences verbatim (sealed), median 44 to 49 hunks vs median 1 needed |
| I3 self-application | `P(P(x)) = P(x)` | what happens after the first PR merges (STATE_MACHINE §11.1: a merged PR "does not automatically prove the next transaction's no-op") | **fails by mechanism** (section 3, M6); not measured end to end |
| I4 convergence | `findings(P(x))` is empty | a re-audit of the output finds nothing to change | not defined today (no audit exists on the output class that gates it) |

I0 is the only rung the gates test. The cache key is the exact request, so the moment the input changes (the live README is now `P(x)`, so every `inherited_unit` fact differs) the key misses and the stages sample again.

## 2. Measurements

### 2.1 Method

- Atomisation with `markdown-it-py` (the parser `inherited.py` already uses). Live and candidate are cut into prose atoms (sentences and list items of at least 4 words, tables excluded), table rows, fenced code blocks, headings, link targets, image targets.
- A live atom is **verbatim** if its normalised text (case, emphasis, backticks, whitespace folded) equals a candidate atom; **reworded** if at least 60% of its content tokens sit in one candidate atom; **scattered** if at least 85% sit anywhere in the candidate; otherwise **dropped**. These thresholds make "kept" generous: the verbatim figure is a ceiling for byte retention, and "dropped" may include semantically equivalent restatements.
- Stage attribution joins each live atom to its inherited unit and that unit's disposition, then checks whether the unit text appears in the candidate. The real `placements()` from `integration/cut3` was run on all 26 wave-3 drafts to cross-check the inferred drops (section 2.3).
- Candidate provenance: a candidate atom is LLM-owned if at least 80% of its tokens sit in one authored content-unit sentence, otherwise renderer or placed text.

### 2.2 (a) What survives of the live README, and where it is lost

Live prose atoms (sentence or list item):

| Set | Drafts | Atoms | Verbatim | Reworded | Scattered | Dropped | Link targets kept | Live lines surviving unchanged | Diff hunks vs live (median) |
|---|---|---|---|---|---|---|---|---|---|
| Wave-3 SEALED | 7 | 507 | 32.7% | 21.3% | 3.2% | 42.8% | 71/98 (72%) | 42% | 49 (24-94) |
| Wave-3 all | 26 | 2,037 | 25.7% | 19.4% | 4.3% | 50.4% | 294/385 (76%) | 35% | 43 (21-134) |
| Baseline 7c5acbf7 | 25 | 2,001 | 12.1% | 19.7% | 5.8% | 62.2% | 280/372 (75%) | 29% | - |
| Slice | 6 | 335 | 17.0% | 30.1% | 5.4% | 46.9% | 65/76 (86%) | 37% | - |
| 38 committed sealed bundles | 38 | 2,991 | 13.4% | 17.2% | 5.1% | 64.2% | 398/599 (66%) | 32% | 42.5 (15-123) |
| All 57 drafts | 57 | 4,373 | 18.8% | 20.4% | 5.1% | 55.5% | 639/833 (77%) | 32% | 44 |

The sealed per-bundle spread shows the unequal treatment of near-identical, conformant READMEs: verbatim share 3D-Java 28%, 3D-.NET 29%, 3D-TypeScript 16%, Cells-Java 17%, Cells-.NET 55%, Note-Python 53%, Slides-.NET 17%. Code blocks fare better (75 of 93 verbatim in the sealed seven) because examples are facts the renderer reprints; images 20 of 31 (sealed), 65 of 120 (wave-3 all).

**Where the sentences are lost** (stage attribution; wave-3 SEALED, n = 507 live sentences):

| Outcome | Wave-3 sealed | Wave-3 all (2,037) | 38 committed (2,991) | Stage |
|---|---|---|---|---|
| Kept verbatim | 32.7% | 25.7% | 13.4% | - |
| S4 said PRESERVE/MOVE, **not rendered** | 24.9% | 22.4% | 12.3% | S7 `placements()` overlap drop |
| S4 said PRESERVE/MOVE, reworded or scattered in the render | 12.6% | 11.0% | 7.5% | S7 (anchor rewrite, plan restates the same facts) |
| SUPERSEDE_REDUNDANT, substance **lost** | 11.6% | 13.4% | 39.3% | S4 promissory note, S6 did not carry it |
| SUPERSEDE_REDUNDANT, re-expressed | 7.5% | 6.2% | 10.6% | S6 paraphrase or renderer |
| DEFER_UNRESOLVED (never rendered) | 3.2% | 8.9% | 1.5% | S4 |
| OMIT_UNSUPPORTED | 3.4% | 1.7% | 8.0% | S4 |
| REWRITE/CORRECT (lost or kept) | 1.6% / 1.4% | 5.8% / 3.9% | 4.0% / 2.4% | S6 |

The decisive row is the second. Of the prose units S4 explicitly marked "keep as written", the render keeps only a fraction verbatim:

| Set | Prose units S4 marked PRESERVE/MOVE | Rendered verbatim | Not verbatim but substance >= 80% present | **Lossy drop** |
|---|---|---|---|---|
| Wave-3 sealed | 128 | 57 (45%) | 22 (17%) | **49 (38%)** |
| Wave-3 all | 400 | 205 (51%) | 62 (16%) | **133 (33%)** |
| Baseline | 211 | 69 (33%) | 82 (39%) | 60 (28%) |
| 38 committed | 323 | 106 (33%) | 109 (34%) | 108 (33%) |

Stable at roughly one third across four code generations, so it is a property of the code, not of the model. The real `placements()` on the 26 wave-3 drafts: 198 of 912 placing decisions are `overlap` (dropped), 193 of them prose units, and 127 of those (66%) keep under 80% of their content in the document (98,895 of 127,604 characters).

**By live section** (wave-3 all drafts; live lines of at least 20 characters; identical anywhere in the candidate / not identical but at least 80% of the words present / lost):

| Live section | Lines | Identical | Substance only | Lost | Owner in the shell |
|---|---|---|---|---|---|
| Navigation | 104 | 86% | 7% | 8% | D |
| Project Structure | 70 | 97% | 3% | 0% | (plan deviation) |
| Quick Start | 496 | 73% | 12% | 16% | M |
| Additional Examples | 1,481 | 65% | 14% | 21% | M |
| API Reference | 6,469 | 59% | 21% | 20% | M (deterministic table) |
| Installation | 296 | 24% | 33% | 43% | D |
| Dependencies | 225 | 30% | 27% | 43% | D |
| Documentation & Resources | 228 | 12% | 61% | 28% | M |
| License | 72 | 7% | 75% | 18% | D |
| **Key Capabilities** | 760 | **3%** | 62% | 35% | L |
| **Scope and Limitations** | 642 | **3%** | 46% | **51%** | L |
| At a Glance | 380 | 16% | 46% | 39% | M |

Pattern: maintainer text survives where the renderer reprints facts verbatim (examples, navigation, code) and is rewritten or lost exactly in the D and L sections, which are the sections where a conformant live README is already right. The H2 skeleton is stable (622 of 696 live H2 headings, 89%, reappear; 75 of 84 in the sealed seven): structure is not the problem, content inside the structure is.

Capability lists: of 52 live Key Capabilities bullets in the six sealed bundles that have one, **0** survive as a plan capability title and 0 are identical; the plan's titles ("Scene graph construction", "Math utilities") replace bullets that name the classes ("Build a 3D scene graph with `Scene`, `Node` ...").

### 2.3 (b) What the candidate contains that has no source in the live README

Candidate sentences outside the API Reference (wave-3 sealed, 353 sentences):

| Origin | Share | Stage that produced it |
|---|---|---|
| Verbatim from the live README | 25% | S7 placed units |
| Re-expressed from live (reworded or scattered) | 37% | S6 paraphrase of SUPERSEDE/REWRITE units; renderer restating facts |
| **No live source, LLM-authored** | **27%** (96) | S3/S6: openings, capability descriptions, lead-ins, limitation prose, development summary |
| **No live source, renderer-authored** | 10% (37) | `_installation`, `_dependencies`, `_development_sentences`, license template |

(Wave-3 all: 22 / 40 / 30 / 9; all 57: 20 / 38 / 33 / 9.) LLM-owned text is 65% of the non-API prose (229 of 353), 66% in wave-3 all. Inside the API Reference, 560 of 695 sealed sentences are renderer-authored from docstrings and signatures (deterministic, verified, but not the maintainers' words: the live reference rows survive identically only 59% of the time).

Where the unsourced text sits (sealed seven, sentences with no live source; LLM / renderer): opening 21 / 0; Quick Start 12 / 0 (all lead-ins); Key Capabilities 20 / 1; Scope and Limitations 16 / 2; Development and Testing 17 / 8; Additional Examples 7 / 0; Installation 0 / 12; Dependencies 0 / 7. Representative lines (source: `scratchpad\idem\examples.py`):

- Opening, Cells-Java live: "pure-Java spreadsheet library ... Apache POI is used only in `test` scope for compatibility checks, never at runtime"; candidate: "enabling developers to create, modify, and inspect spreadsheet content without requiring a commercial license. It supports Java 17 and has no external dependencies, making it suitable for developers building lightweight, self-contained applications." The authoring prompt forbids exactly this phrasing; 7 of 7 sealed openings and 55 of 57 drafts contain at least one of "enabling developers", "developers use", "without requiring", "suitable for", "ideal for"; none of the seven live openings do.
- TypeScript: "Tests ... verify the functionality of the @aspose/3d package at version 24.12.0."; "The suite covers 33 test files" (renderer, counts every file).
- Quick Start lead-ins are 12 of 12 LLM-new because the live README has different or no lead-ins.

So the introduced text has two producers with different failure signatures: free LLM prose invents (benefit and audience claims, rationale), the renderer template re-states (counts, install variants) and is wrong only when its fact is.

### 2.4 (c) Sensitivity to the model

**Identical request, different answer.** The ledger's `request_sha256` covers model, messages, temperature (0.0), `max_tokens`, response format and `seed` (1) (`core/llm/jobs.py:request_payload`). Across the 3 ledger roots, 18 requests were executed by at least two independent invocations (different `invocation_id`, minutes to hours apart):

| Result | Count |
|---|---|
| Byte-different response | 17 of 18 |
| Parsed JSON different | 16 of 17 compared |
| `section_authoring` text similarity (difflib), identical requests | mean 0.87, range 0.65 to 1.00 (n = 11) |
| `repository_investigation` similarity | mean 0.72, range 0.63 to 0.78 (n = 5) |
| Completion-token counts for the same request | e.g. 2,516 vs 2,098; 3,483 vs 2,149 |

So `temperature: 0.0, seed: 1` does not give determinism on this gateway at production lengths. The preflight catalog nevertheless records `seed_support: honoured, deterministic: true` (`runs/preflight/catalog.json`) because `core/llm/transport.py:probe_seed` compares two completions of at most **24 tokens** (`_PROBE_MAX_TOKENS = 24`). The measurement that backs the claim is too short to see the divergence; the project had seen the symptom already (`docs/DECISION_LOG.md` ~L2321, "source_reconciliation is genuinely non-deterministic run to run"; ~L3541 `call_variance`) and answered by not re-running, not by changing the design.

**Cascade.** Reconciliation, planning, authoring and review requests embed upstream outputs, so a single different investigation changes every later request hash: in the Cells-TypeScript wave-3 replicate (same code, same revision, 2 attempts), the investigation request was identical, its response differed, and then 0 of 3 reconciliation requests, 0 of 1 planning requests and only 4 of 11 to 17 authoring requests were shared. Variance is not additive noise on one stage; it compounds along a five-stage chain. Cost of the chain: 19% of 2,317 provider calls were rejected as invalid (reconciliation 35%, repair 37%, planning 16%, authoring 13% in wave 3), each retried with a different prompt, so even the path is non-reproducible.

**Two independent sealings of one revision** (committed bundle vs wave-3 bundle, same repository and revision, same model `qwen3-next`; the code differed between cuts, so this mixes code and model drift):

| Repository | LLM sentences identical | Capability titles identical | Non-API line Jaccard | Dispositions equal |
|---|---|---|---|---|
| 3D-.NET 52b0f00e | 1 of 160 (1%) | 0 of 14 | 38% | 58% |
| 3D-Java 3d2ed6be | 6 of 273 (2%) | 0 of 13 | 16% | 66% |
| Cells-.NET 941814fd | 3 of 82 (4%) | 2 of 12 | 28% | 37% |
| Cells-Java c65329e7 | 0 of 62 (0%) | 1 of 13 | 53% | 51% |
| Slides-.NET 86c441b5 | 0 of 72 (0%) | 1 of 15 | 9% | 19% |

27 draft pairs on the same revision (any code version): keep/drop verdict for live sentences agrees 78% on average, kept-set Jaccard 63%, non-API line Jaccard 50%, **H2 skeleton Jaccard about 100%**. 47 pairs of disposition files: 64.5% of units get the same disposition, keep-set Jaccard 44%. The structure replays, the words do not.

### 2.5 Edits made versus edits needed

| | Regeneration (measured) | Minimal edits for the same READMEs (measured) |
|---|---|---|
| Diff hunks per README | median 44 (min 21, max 134) | structural and hygiene edits (missing required section, missing mermaid, second H1, fence without language, edition word): median **1**, mean 1.5, max 10; 16 of 37 zero, 33 of 37 at most 3 |
| Verified corrections | - | BC-14 (`validation/claims.py:claim_findings`) run directly on the live README with the draft's facts: **8 findings in 7 of 28** wave-3 live READMEs (stale version 26.6.0 vs 26.9.0, "not published" now false, install near-miss, `26.9.0.0` vs `26.9.0`); the regenerated candidates contain 1 |
| Prose units changed for a cause a fact states | 37 of 1,879 prose units (2%): CORRECT_WITH_EVIDENCE 3, OMIT_UNSUPPORTED 34. A further 1,453 (77%) were removed, re-authored or lost with no contradicting fact | - |

The edit set is almost entirely design, not correction: 77% of prose units are changed or lost without a contradicting fact, 2% with one. A patch design pays about 2 to 3 hunks per README where regeneration pays 44.

## 3. Mechanisms (code evidence), inherent versus design

### M1. The output is built from scratch; the live README is never the document (design)

`composition/renderer.py:render_readme` (L1212-1234) builds `blocks` section by section through `_section_body` from `shell x plan x units x facts x dispositions`. There is no base document. `x` enters `P(x)` through exactly three channels: (1) verbatim: dispositions `VERIFIED_PRESERVE` or `VERIFIED_MOVE` placed by `placement.py:placements` (`PLACED`, L62); (2) paraphrase: `SUPERSEDE_REDUNDANT` into a carry section, `VERIFIED_REWRITE`, `CORRECT_WITH_EVIDENCE` re-authored by S6 (`authoring.py:_CARRY_SECTIONS`, `carried_units`); (3) evidence: `U(x)` becomes facts and the renderer prints its own form of the same example, link or symbol. Everything else is `f(r)`.

### M2. Deterministic sections overwrite hand-written text by rule (design)

`composition/components/shell.py` docstring: "An inherited unit can be placed only into an `L` or `M` section; a `D` section renders from facts and supersedes the unit." The shell has 18 sections: D = identity, badges, banner, navigation, installation, dependencies, third_party_notices, license (8); L = opening, key_capabilities, scope_limitations (3); M = at_a_glance, quick_start, additional_examples, api_reference, documentation_resources, development_testing, enterprise_relationship (7). For a D section the question "is the live text already correct" is never asked: it is replaced even when equal in facts. Measured: Installation 24% and License 7% of live lines identical, Dependencies 30%.

### M3. The L sections cannot keep the maintainers' words (design)

Key Capabilities and Scope and Limitations are authored from facts only (`prompts/section_authoring.yaml`: "Invent nothing", closed `accepted_facts`); the live text reaches S6 only as a must-carry obligation (`authoring.py:carried_units`, `list_coverage.py`: "state their substance", every list item) which is a paraphrase obligation. Measured: 3% identical lines in both sections, 35% and 51% lost.

### M4. Reconciliation decides before the plan exists, and the plan wins ties (design; the largest deterministic loss)

README_CONTRACT §3: "Reconciliation (S4) decides a unit's disposition before planning (S5) exists ... the planned, freshly-authored content wins." `placement.py:placements` (L469-530): `overlap = set(entry.fact_ids) & covered`; one shared fact id drops the whole unit; `PLACED` excludes REWRITE and CORRECT; headings, badge rows, HTML blocks, ecosystem examples and Mermaid are `owned_elsewhere`. Measured: one third of the units S4 marked "keep as written" are lost (section 2.2); BC-05 and BC-08 skip them (`validation/registry.py`, `_check_dispositions`: `if placement.outcome != "placed": continue`; `_check_protected`: `category == "unit"`), so nothing downstream sees the loss.

### M5. The reconciliation prompt tells the model to supersede the high-value prose (design)

`prompts/source_reconciliation.yaml` v9, system text: SUPERSEDE_REDUNDANT covers "a capability list re-authored under key_capabilities, a limitations list re-authored under scope_limitations, a resource list re-authored under documentation_resources" and "A unit that merely repeats a capability inventory rendered elsewhere is SUPERSEDE_REDUNDANT"; `VERIFIED_REWRITE` is "keeps its substance but the wording will be re-authored from facts". Prose units: SUPERSEDE 45% (D-destined 20%, M 19%, L 6%), PRESERVE 26% + MOVE 9%, DEFER 13%, REWRITE 5%, OMIT 2%, CORRECT 0.2% (1,876 prose units). The DEFER class (13%, "never rendered") is an unverifiable-equals-removed policy: unverifiable is not false.

### M6. The generator does not trust its own prose (design; this is the self-application failure)

On the second pass, P(x)'s LLM-authored capability bullets, limitation bullets, resource items and openings are inherited units of exactly the kind M5 tells S4 to supersede, S6 re-authors them from the same facts, and the new draw differs (section 2.4). Deterministic parts (D sections, API tables, examples) would reproduce byte for byte. Hence the bound: at most the non-LLM 35% of non-API sentences (the deterministic and placed share) is stable under self-application; the LLM-owned 65% is re-sampled with a measured reproduction rate of about 11% at a byte-identical request and 0 to 4% for sentences across sealings (the input changes on the second pass, so the lower rate is the relevant one), so the stable share is at most about 40% (derived upper bound, not measured; placed live sentences themselves survive only about half the time, so the true figure is lower).

### M7. Plan from facts, not from the live skeleton (design)

`presentation_planning` chooses sections and 3 to 8 capabilities from facts and investigation; the live H2 skeleton is a hint at most. 0 of 52 live capability titles survive; live-only H2 headings that disappear: Additional Examples (15 of 57 drafts), Project Structure (9), License (4), Quick Start (3). Identical live and shell sections still end up with different content because content is decided per slot, not per section.

### M8. Stochastic chain (inherent, amplified by design)

17 of 18 identical requests returned different bytes (section 2.4). Inherent: sampling or batch-dependent numerics in the served model; we cannot fix it. Design amplifiers: five conditioning stages (variance compounds), per-unit LLM disposition of hundreds of units (reconciliation is a 35%-invalid job), a coherence pass (S8) that revises LLM-owned units (57 revised units over 5,225 units in 58 drafts, 32 drafts with at least one), repair rounds. Mitigation lives in architecture, not in sampling parameters: call the model fewer times, on smaller inputs, and accept its output only if a deterministic check of the result passes.

### M9. The gates certify replay, so the defect is invisible (design/process)

STATE_MACHINE §10 and `core/noop_proof.py`: no-op proof = same artifacts, same candidate bytes, zero provider calls, replayed from the call store. §5 lists conditions (prompt hashes, versions, source revision) under which `UNCHANGED` holds; §11.1 concedes a merged PR "does not automatically prove the next transaction's no-op". `project/state.yaml` counts sealed bundles. The seed probe says "honoured". No gate asks `P(P(x)) = P(x)` or `diff(x, P(x))` small. This is why the same defect class (UNIVERSAL loss and variance causes) reappears every wave.

### Which are inherent

| Source | Inherent to "LLM writes text"? | Fix |
|---|---|---|
| Gateway nondeterminism at T=0 | Yes (observed, cause not diagnosed) | Limit LLM calls to units that need text; content-addressed cache; accept only checked output |
| D-section overwrite, M3 L-section re-authoring, M4 overlap drop, M5 prompt, M7 plan | **No: design** | Invert precedence (section 4) |
| Chain of five conditioning stages | No: design | Audit by rule; LLM per flagged unit |
| Memoization masking (M9) | No: process | Idempotence corpus gate (section 5) |

Even a perfectly deterministic model would leave `P(x) != x`: the sealed bundle is itself one replay-stable draw and still keeps only 33% of sentences verbatim. A perfectly faithful S4 (keep everything) would still lose one third of the keeps at S7 and 20% of prose units to D-destined supersession. The ceiling of the current design on conformant input is roughly 60 to 70% verbatim (estimate), never 100%.

## 4. The minimum production-grade change: edit script over the live README

### 4.1 Principle

Move from "generate a document and diff it against the old one" to "**audit the old one and emit a minimal verified edit script**". The shell stops being a template that overwrites and becomes a schema that the live document is checked against. Default for every live unit is KEEP; text changes only with a machine-checkable cause. This is the `plans/idea.md` L319-321 fast path ("verified inherited claims, deterministic assessment, an empty-patch candidate") and L339-340 ("regeneration convenience is never a reason to discard valuable curated information") made the main path. It is consistent with AGENTS.md: the LLM still proposes typed outputs; deterministic code owns state, validation and the diff.

### 4.2 Pipeline (what changes per stage)

| Stage | Today | Proposed | LLM? |
|---|---|---|---|
| S1 snapshot, S2 facts | unchanged | unchanged, plus a per-unit claim index (identifiers, commands, versions, counts, links named by each live unit) | no |
| **S2b audit (new)** | - | run the verifiers over the **live** README: BC-14 `claim_findings`, BC-02/03 install and example receipts, link-target polarity, BC-12 canonical name, edition and forum wording (BC-06/07 lists), fence language, shell conformance (H1, required sections, Mermaid, Navigation), count claims vs facts, BC-15-style holes, duplicates and dangling lead-ins (first analysis, rank 3). Output: findings `{unit_id or section, code, severity, fact_ids, op_template}` | no |
| S3 investigation | always | only when the audit lists a MISSING prose slot or an ambiguous product claim; content-addressed cache | yes, rarely |
| S4 reconciliation | LLM disposition per unit, default SUPERSEDE or PRESERVE per prompt | **rule**: KEEP unless a finding; classes `KEEP_VERIFIED` (positively confirmed by a verifier), `KEEP_UNCONTRADICTED` (no fact contradicts it; recorded in the uncertainty ledger, not in the README), `FIX`, `DELETE`, and `REPLACE`; LLM judge only for units a detector flags as ambiguous | no (default) |
| S5 planning | LLM chooses sections from facts | **plan = diff**: skeleton from the live headings; the shell's conditions evaluated on facts decide required sections; MISSING required sections become INSERT ops; extra live sections are preserved and recorded as plan deviations automatically | only to choose among candidate inserts |
| S6 authoring | all L and M slots | only INSERT units and FIX rewrites; packet is one unit plus its contradicting fact; output limited by edit distance and verified spans (identifiers, links) | yes, bounded |
| S7 render | from scratch | **splice**: apply ops onto the live unit lines (`inherited.py` keeps exact source line ranges); a D slot is filled only if empty or false: compute the facts the renderer would state (install command, versions, dependency set, license SPDX and file), compare with the facts the live section states; equal means keep live bytes; live subset means insert the missing lines; contradicted means replace those lines | no |
| S8 coherence | whole document | only over inserted units | yes, bounded |
| S9 validation | BC-01..BC-14 | unchanged, run on the result, **plus the convergence check**: re-run S2b on the result, require zero findings and zero new ones | no |
| S10 review | whole document, same model | the **diff** (hunks with reason codes) and the full README read-only; a finding without a deterministic cause is advisory | yes |
| S12 no-op | replay | replay **and** content: `audit(result) = empty` and `apply(empty) = identity` | no |

### 4.3 Invariants (the fixed-point contract)

1. **Empty-patch fixed point.** `findings(x) = empty` implies `P(x) = x` byte for byte, zero provider calls.
2. **Convergence.** `findings(P(x)) = empty`; hence `P(P(x)) = P(x)`. An op that does not clear its finding or creates a new one is rejected before commit.
3. **Locality and cause.** Every hunk belongs to an op with a reason code in {FALSE_CLAIM, STALE_VALUE, DEAD_LINK, POLICY_WORDING, MISSING_SECTION, FORMAT, UNSUPPORTED_ID}; a hunk without an op is a defect.
4. **Monotonicity.** Nothing in `x` (sentence, list item, link, image, code block, badge) is removed without a machine-checkable cause. This is the generalisation of the first analysis's BC-13.
5. **Determinism of the default path.** The LLM-free path is a pure function of `(x, F)`. LLM ops are content-addressed `(unit hash, finding code, relevant fact hashes, prompt hash)`, so an identical situation reuses an identical answer.
6. **Provenance.** Every inserted or rewritten claim maps to facts (BC-04 unchanged).

### 4.4 Rejected alternatives

- Fix the overlap rule, list-item granularity, prompt (first-analysis rank 2): worth doing as an interim step; it moves sealed verbatim from about 33% to roughly 60 to 70% (recovering the 25% S7 drop and part of the 12.6% reworded) but D overwrite, L re-authoring and S4 variance remain, so no fixed point.
- Majority vote or ensemble: N-times cost, still re-writes.
- More caching: masks I1; breaks on `P(P(x))` because the key includes the input.
- Different model or stricter decoding: the gateway already uses `json_schema` constrained output and a seed.

### 4.5 Open owner decisions (small, product-policy)

1. `KEEP_UNCONTRADICTED`: carry unverifiable-but-uncontradicted maintainer prose (today DEFER, 13% of prose units, never rendered). `idea.md` allows "carried as explicit uncertainty".
2. Invert README_CONTRACT §3: "live wins unless the live unit has a finding; planned content fills gaps". D sections become verified slots, not templates.
3. Progress unit: add the idempotence gate to the definition of "no-op-proven" (AGENTS.md "Count progress in one unit only").

## 5. Verification harness

**Corpus.** The 37 live-README snapshots with their frozen facts (`facts.json` from the sealed or draft bundle; link-target polarity and example receipts are already facts, so verification needs no network). `facts.json` is about 3 MB per bundle: keep a trimmed fixture (identity, package, install_command, import_path, link_target, example, license, dependency, build_test_asset, a `public_symbol` subset) in the repository and the full set outside it with a checksum manifest, as `evidence/` does. The provider client in the corpus tests raises if called.

| Test | Assertion | Notes |
|---|---|---|
| T1 fixed point | for each corpus entry with `findings(x) = empty`: `P(x) = x`, provider calls = 0 | expected today (measured structural and hygiene need) 16 of 37 zero |
| T2 edit budget | `hunks(x, P(x)) <= findings(x)`, every hunk carries a reason code, unexplained hunks = 0 | 33 of 37 need at most 3 |
| T3 convergence | `P(P(x)) = P(x)` and `findings(P(x)) = empty` | the I3/I4 rungs, offline |
| T4 no loss | every live link target, image, code block, list item, badge survives unless an op with a machine cause covers it | replaces the sentence heuristics used here |
| T5 determinism | two cold runs produce the same bytes (LLM ops from recorded fixtures); LLM calls <= findings that need text | catches the stochastic chain returning |
| T6 mutation (metamorphic) | start from a conformant README, inject one defect (stale version, dead link, drop a required section, add an edition word, break a fence, change a count); expect exactly one op, everything else byte-identical | the strongest idempotence regression test |
| T7 drift | change an unrelated fact (new test count): only the dependent unit changes | guards "invalidate only through an input it consumed" |

**CI gate.** T1 to T6 in `scripts/ci_check.sh` on the corpus; any unexplained hunk fails the build. **Production-shaped proof** (AGENTS.md requires it for live claims): nightly on three real repositories with the gateway, run twice; second run must report zero ops and zero provider calls (`audit(result) = empty`). **Report** (`tools/idempotence_report.py`, productised from `scratchpad\idem\measure.py`): per repository verbatim %, lines surviving, hunks, unexplained hunks; this replaces the sealed count as the progress unit.

## 6. Effort and ordering

Judgment, not measurement; hours are engineer-hours.

| Phase | Content | Hours | Paths (disjoint) |
|---|---|---|---|
| 0 | Baseline report from the scripts here; fix budgets N from the corpus; owner decisions 4.5 | 4-6 | `tools/`, docs |
| 1 | Audit adapters (unit-scoped BC-14/02/03/06/07/12, fence, edition, shell conformance, counts) and the splice applier with diff-budget and reason codes, deterministic only; T1-T3 | 40-52 | new `components/readme/patching/`, `validation/` adapters |
| 2 | D-slot "fill if empty or false" via facts-equivalence over the renderer's section functions; T4-T7 and mutation corpus; reviewer on the diff | 24-32 | `composition/renderer.py` read-only reuse, `review/`, `tests/` |
| 3 | LLM ops: INSERT authoring, FIX rewrite with edit-distance and verified-span limits, content-addressed cache; bootstrap of the 3 weak READMEs (Font-Python 1/7 sections, Slides-.NET 2/7, Words-.NET 4/7) through the existing from-scratch pipeline | 16-24 | `prompts/`, `composition/authoring.py` |
| 4 | Contract and state-machine updates, DECISION_LOG §31 proposal, governed-version bumps, nightly proof | 8-12 | docs, `project/state.yaml` |
| Total | | about 90-125 | 12-16 working days one lane; 5-8 calendar days on three lanes |

Ordering. **Monday 2026-10-12 (live-first lane):** build phase 0 and the front of phase 1 as the production code, not a script: audit plus splice with deterministic ops over the 5 reviewed READMEs, target zero or few unexplained hunks; the first prototype result is the T1/T2 numbers on those five. **Tuesday to Friday:** phase 1 complete on all 37 with the CI gate; verifier adapters for install and example receipts and links. **Week of 19 October:** phases 2 and 3, reviewer on the diff, two-run production proof on three repositories. **Week of 26 October:** retire regenerate-by-default for conformant inputs (keep the pipeline as the bootstrap for weak READMEs and new products), after which `P(P(x)) = P(x)` holds from the second run on. The interim fixes (overlap rule, BC-13/15) from the first analysis are not wasted: the audit reuses BC-13/15 as verifiers.

## 7. Why this is the smallest change that works

It removes the three sources, not the symptoms. (A) Structural loss disappears because KEEP is the default and a D slot is filled only when empty or false. (B) Stochastic loss is confined to units that need text and every accepted op is re-audited. (C) The gate moves from replay to content, so `P(P(x)) = P(x)` becomes a test instead of a hope. Components that stay: S1/S2 extraction, example receipts, link verification, BC checks, the renderer's section functions, bundle seal and recheck, the proposal and effect machinery. Components that become optional or bootstrap-only: S4 LLM dispositions, S5 whole-document planning, S8 whole-document coherence.

## 8. What I could not measure

1. **`P(P(x))` end to end.** It needs the gateway, clones and toolchains; not run. The conclusion rests on the mechanism (M5/M6) and the stage-level numbers. The 40% stability bound is derived from measured pieces (non-LLM share, reproduction rates), not observed.
2. **Pure model variance for reconciliation, planning and review.** Only investigation and authoring requests recur with identical hashes (18 requests, mostly Cells-TypeScript, 3D-Python, Words-Python); the other jobs embed upstream outputs. Similarity is character-based.
3. **Semantic equivalence.** Retention uses lexical normalisation and token containment (0.6 and 0.85). "Dropped" can include equivalent restatements (an install paragraph replaced by a verified command); "verbatim" ignores case, emphasis and backticks, so it is a ceiling. Sensitivity to the thresholds was not swept.
4. **Confounded pair comparisons.** Baseline, slice, wave-3 and committed bundles come from different code versions, and the wave-3 failed drafts are the state at failure (before or after repair unknown). The sealed-only rows are reported separately; the pure same-code replicates are few (Cells-TypeScript, Email-Cpp, Cells-Rust).
5. **Provenance of the live READMEs.** 29 of 37 already carry the contract's standard section titles in the contract's order with a Mermaid diagram, which suggests an earlier generator of the same template produced them; I did not verify it. If true, `P` is not even a fixed point on the output class of its own predecessor.
6. **Verified-correction workload.** Only BC-14 was run on live text. Install and example receipts, link liveness, count claims and semantic false claims were not run; "median 1 structural edit" is a lower bound for the patch design. The first analysis's estimate (about 0.7 residual findings per live README) stands unrefined.
7. **Effort and phase boundaries** are judgment; the quality of bounded rewrite jobs (edit distance, verified spans) needs a prototype.
8. **Production behaviour** of merge-then-rerun loops and PR churn was not observed (no remote effects exercised).
9. **Cause of gateway nondeterminism** (batching, kernels, routing) was observed, not diagnosed.
10. Reverse-patched live READMEs for the committed bundles differ from the true source by a few bytes (checked on 29 of 57 cross-checkable drafts: 4 to 8 bytes, whitespace); not material to the metrics.

## 9. Reproduce

All in `C:\Users\babar\AppData\Local\Temp\claude\e--Users-prora-OneDrive-Documents-GitHub-repository-presenter\01db89e6-ba90-479a-befa-bff20834c024\scratchpad\idem\` (run with the repo `.venv` Python; `runs\wt\int-cut3\src` on `sys.path`):

- `lib.py`, `data.py`: markdown atomiser (markdown-it-py), dataset loaders (`tx_dirs`, `committed_dirs`), reverse patch.
- `measure.py [committed]` -> `measure.json`, `measure_committed.json`; `report1.py` .. `report4.py` (retention tables, stage attribution, provenance by section).
- `placed2.py` (real `placements()` on wave-3 drafts), `sections.py` (per-live-section retention), `kc.py` (capability titles), `links.py` (lost links by stage), `bc14.py` (BC-14 on live), `coh.py` (coherence and call validity), `opening.py`.
- `nondet.py`, `nondet2.py`, `nondet3.py` (identical-request replicate pairs from the ledgers and call files), `variance.py`, `variance2.py`, `pair_committed.py`.
- First-analysis helpers reused: `fp\conform.py`, `fp\detect.py`.

Not done: no gateway call, no network, no edit to a tracked file, no write to any Aspose repository, no bundle modified.
