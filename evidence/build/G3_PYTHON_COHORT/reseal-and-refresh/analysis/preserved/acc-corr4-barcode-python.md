authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.BarCode-FOSS-for-Python (aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python @ 06eca5c0)

Verdict: **FIX_REQUIRED** (PR text, one sentence). Patch 1253 bytes (+10/-7), diagram only, order 2.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live. Render: the three blocks are product, Core Capabilities, Outputs left to right (no Starting Points block in this README), 5 capabilities in one column, 2 outputs.

## The sentence
`... All 8 labels, the 2 group titles and the chain Starting Points -> product -> Core Capabilities -> Outputs are unchanged (compared by script).`

False for this README: its diagram has no Starting Points group; the chain is `PRODUCT --> Capabilities --> Outputs`. The number 8 and 2 are right (my parse). A maintainer who has no such block will read the claim as proof the tool did not look.

Fix (`pull_request.py` `_bullet`, DIAGRAM_FIX): derive the chain from the diagram's own titles (`glance.titles`), e.g. "the chain product -> Core Capabilities -> Outputs".

## Also (all PRs, advisory U-1 to U-3)
`validate_candidate` / `BC-01 to BC-14`; "so text no longer clips"; no sender contact. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).

Pilot note: text gain x1.77 at a 896 px column (drawing 282 px to 624 px tall); a good pilot candidate once the sentence is fixed.
