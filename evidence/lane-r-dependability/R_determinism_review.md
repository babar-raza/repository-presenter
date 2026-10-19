# Lane R: determinism and reviewer independence (read-only, 2026-10-16)

Method: 30 sealed bundles under candidates/*/CURRENT (read calls.jsonl, manifest.json, review.json), the
prompts/*.yaml routing, core/llm/*, review/independent/review.py, DECISION_LOG, and 6 small gateway calls.

## 1. Models and routes
| Fact | Evidence |
|---|---|
| Every job routes to one model, qwen3-next (investigate S3, reconcile S4, plan S5, author S6, review S10, repair S11) | `model_route: qwen3-next` in all 6 prompts/*.yaml (line 5); runs/preflight/catalog.json |
| 1,584 ledger rows across 30 bundles: 1,584 `model_route` = qwen3-next; the 608 real provider calls all `model_served` = qwen3-next | calls.jsonl, counted |
| Reviewer is on the author's model. Independence is "by prompt and ledger attribution, not by model" | prompts/independent_review.yaml `route_rationale` |
| Second and third review reads are the same prompt and model with seed +2 / +3 | review.py:456-493 `second_reader`, `third_reader` |
| Catalog has gpt-oss (+ Qwen2.5-VL-7B, experimental, recommended, embedding, SD3.5): only gpt-oss is a chat alternative | catalog.json |
| gpt-oss answers: my plain 400-token JSON call returned valid content. The pipeline's strict probe (`max_tokens=16`) returned HTTP 200 with no content, so it would be refused today | transport.py:155,168; my probe call |
| Fallback to gpt-oss existed and was removed by owner decision 2026-10-04: "no substitute models... no gpt-oss result can be sealed"; a gpt-oss request profile (bigger budget, reasoning effort) was drafted and withdrawn | DECISION_LOG.md:5035,5052; fallback.py:5, `FALLBACK_CHAINS = {}` |

To review on gpt-oss: (a) set `model_route: gpt-oss` in prompts/independent_review.yaml and bump its version (14 to 15), which changes its prompt sha256 and the reviewer's request hashes, so every review re-runs (re-check, `VALID_UPDATE_AVAILABLE`, not invalidation of authoring); (b) a per-model request profile (reasoning budget well above the 6000 max_output_tokens, larger probe budget); (c) an owner decision lifting the 2026-10-04 rule for a reviewer-only route, plus `REVIEWER_LOGIC_VERSION` (21) bump if fold rules change. `FALLBACK_CHAINS` is a governed constant but need not change: the route is per prompt. Gateway also has `GPT_OSS_MODEL` override env (config.py:24); not a safe lever (it renames the route model for all jobs).

## 2. Review behaviour across the 30 sealed bundles
| Measure | Count |
|---|---|
| Final verdict ACCEPT | 30 of 30 |
| Verdict as returned by the model | 4 ACCEPT, 22 REJECT_PRESENTATION, 4 REJECT_FACTUAL (26 rejections, all overturned) |
| Findings that blocked (review.json `findings`) | 0 in all 30 |
| Advisory (folded) findings | 313 (259 presentation, 54 factuality); 308 carry `reviewer_scope_defect`, 5 are single-reader |
| Reads recorded | 25 bundles 2 reads, 1 bundle 3 reads (Words-.NET), 4 bundles no second read (3D-Python, Cells-.NET, Cells-Rust, Slides-Python) |
| Repairs ran (repairs.json present) | 14 bundles; targeted_repair is 10 of 608 provider calls |

Mechanism (review.py): a rejection survives only if some finding is not folded. Folds: DETERMINISTIC_RULES refute from bytes (quote absent, name denial, literal fact value; 496-560), prose/scope rules annotate, and "unrepairable" findings are demoted to advisory (2531-2532, 2860-2880). `returned == REJECT` and every finding folded => ACCEPT (line 2877). Second read runs only on a typed trigger (PROSE_JUDGMENT_ON_REQUIRED_ROW, ADVISORY_DEFERRAL, REJECTION_REFUTED; 410-436); a third read only when a triggered second disagrees with a clean first; 2-of-3 on `finding_class` (section+stage+criterion) decides (2882-2915). A single reader's prose judgment can never block (SINGLE_READER_PROSE). Net effect: REJECT is overturned wherever the finding quotes renderer text, a heading, or text the code judges "reviewer scope".

Two true defects were folded for wrong reasons (review.json advisory, bundle at CURRENT):
- HTML-Python F01 (factuality: dependency `<145` split from `skia-python>=87.0`): folded because "the quote is the heading 'Required Package Dependencies', which the renderer emits".
- Words-.NET F03 (factuality: RTF/HTML conversion claimed, upstream says unsupported): folded because "the finding claims the candidate does not contain 'HTML','RTF', which the candidate contains" (the finding said the claim was false, not absent).

Hand triage (review-packets/R/*/TRIAGE.md covers all 30, not 15: 1 PUBLISH_AFTER_HUMAN_REVIEW, 14 NEEDS_FIXES, 15 KEEP_LIVE). Factual errors found by hand (false/invented/stale/garbled claims, not omissions), against 30 of 30 reviewer ACCEPTs:
| Repo | Hand-found factual errors |
|---|---|
| Imaging-.NET | 3 (invented transformation, custom loaders/savers, per-layer manipulation; live is detection-only) |
| PDF-Cpp, Slides-Cpp | 2 each (falsely "not published on any registry"; wrong dependency split) |
| HTML-Python | 2 (mangled skia-python spec; "no build or install succeeds") |
| PDF-.NET, Cells-Python | 2 each, but upstream moved after the seal (stale version/TFM, Python 3.7+ vs 3.10+) |
| Note-Python, Page-Python, Slides-Java, Slides-.NET, Words-.NET, Words-Python, BarCode-Python, PDF-Go | 1 each (wrong package `aspose-note`; invented "Model-View-Presenter"; unreleased 26.8.0 as on Maven Central; net8.0 only; RTF/HTML support; garbled badge; garbled Dev/Test prose; DOCX/EPUB overreach, unverified) |
| Email-.NET | 1 unresolved (0.1.0 vs live 26.7.0) |
Total: 14 bundles (about 22 errors, 15 with Email-.NET) accepted with a factual error; 2 of the 4 returned REJECT_FACTUAL (HTML, Words-.NET) were right and were folded. Counter-sample: Cells-TS and PDF-Java returned REJECT_FACTUAL and the hand reviewer found no invented claims, so the signal is noisy in both directions. (Note-Python CURRENT in this worktree is modified/uncommitted; the table uses its triage verdict.)

## 3. Determinism
- DECISION_LOG.md:5911 (2026-10-11, G3-W11/TC-IDM-01): "17 of 18 byte-identical requests returned different responses at temperature 0, seed 1; two independent sealings of one revision share 0 to 4 percent of their model-written sentences." Earlier: wrong choice repeated at temperature 0 (line 806); two identical rejections at temp 0 seed 1 (1458).
- Sealed ledgers, this worktree: 543 successful provider-call request hashes; 8 were requested more than once, and all 8 returned different responses (0 identical): 5 section_authoring, 2 repository_investigation, 1 independent_review. (manifest `call_variance` groups by job, so its larger counts mix different requests; not used.)
- My own experiment, 6 calls: 4 identical requests to qwen3-next (temperature 0, seed 1, short JSON extraction with a free-text summary, max 200 tokens) gave 4 of 4 byte-identical outputs (sha 8 prefix bd56f3a3). gpt-oss: 1 call, valid JSON, different wording ("open OneNote files and convert"). So small, short requests are stable; the instability is on the real pipeline's long prompts (6k+ prompt tokens, long outputs; gateway batching or numerics). I did not reproduce 17/18 with a pipeline-sized prompt (budget).
- What reruns rely on: `CallStore` keyed by `logical_call_id` = canonical_hash(prompt_sha256 + payload) (jobs.py:448-475, 150-180); `seed_call_store`/`seed_additional_calls` (seal.py:691-790) re-load a bundle's one-attempt successes (reconcile, plan, investigate; plus raw_calls) so a clean clone replays with 0 provider calls; manifest `no_op_proof` (byte_identical, fresh_process, provider_calls 0). Proves: same input, same code, same stored responses give the same bytes (memoization). Does not prove: a re-generation gives the same answer, that P(P(x)) = P(x), or any robustness to a changed input (any packet/prompt change misses the cache and re-rolls the whole stage). Cause A in DECISION_LOG:5052 shows a toolchain-dependent fact changing one request hash and breaking zero-call replay. Jobs with several attempts (repair rounds) are deliberately not seeded.

## 4. Which LLM jobs need an LLM (share of 608 provider calls)
| Job | Calls | Could be deterministic? |
|---|---|---|
| S6 section_authoring (opening, capability titles/descriptions, lead-ins, limitations, resources, dev summary, Enterprise text; coherence pass) | 378 (62%) | Mostly. Of 18 shell sections 3 are LLM-owned (opening, key_capabilities, scope_limitations), 8 mixed, 7 deterministic (components/shell.py); lead-ins, resource lines, Enterprise paragraph, dev summary are template-from-facts or verbatim live text. Judgment is needed only for opening, capability descriptions, limitation prose. |
| S4 source_reconciliation (KEEP/MOVE/OMIT per inherited unit) | 79 (13%) | Mostly. Lane L default is verbatim copy; fact-check of each unit against facts is code. LLM only for semantic equivalence. |
| S10 independent_review | 64 (11%) | No, but its factual half is already deterministic (fold stack and BC checks); LLM adds visitor judgment. |
| S5 presentation_planning (pick 3-8 capabilities, examples, links by fact ID) | 46 (8%) | Largely: examples and links come from verified inventories; live README's own list can seed capabilities. |
| S3 repository_investigation (what the product is) | 31 (5%) | Partly: name/language/ecosystem are facts; audience and problem framing need language. |
| S11 targeted_repair | 10 (2%) | No (semantic repair), but small. |
About 83% of calls (S6, S4, S5) are in jobs whose output a live-first edit-script design could mostly copy or template; real language judgment is roughly 20-30% of today's calls (opening, capability prose, limitation prose, review, repair). Estimate from call counts, not from a per-unit audit.

## Conclusion
- Review independence: today it is a same-model, same-prompt second read; seed offset does not decorrelate at long prompts and the fold stack overturned 26 of 26 rejections, 14 of 30 ACCEPTs carry hand-found factual errors, and 2 true factual findings were folded on a misparse. Independence with the available models is partly possible: gpt-oss is the only second chat route (a reasoning model needing a larger token budget and a request profile, plus an owner decision reversing the 2026-10-04 rule); Qwen2.5-VL-7B is a 7B vision model and not a credible reviewer. A different model plus unfold-by-default (a REJECT stands unless a deterministic byte-level rule refutes it, and refutations must be tested for the quote-is-a-heading and misparsed-absence cases) is the minimum.
- Fixed point for reruns: because the gateway is not deterministic on pipeline-sized prompts, a fixed point cannot come from regeneration. It must come from (1) copy-through of live units by default so unchanged input yields unchanged output without a model call, (2) model calls only for units whose input facts changed, each memoized by input hash and replay-seeded, (3) deterministic edits and review of those edits against facts, so an unchanged README maps to zero edits, and (4) reviewer verdicts stored by candidate hash and not re-sampled. Without that, P(P(x)) = P(x) will keep failing.
