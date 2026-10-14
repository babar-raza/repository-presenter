authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.HTML-FOSS-for-Python (aspose-html-foss/Aspose.HTML-FOSS-for-Python @ bf0f1e7a)

Verdict: **FIX_REQUIRED** (PR text, one sentence). Patch 2143 bytes (+20/-16), diagram only, order 2.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## The sentence
`... All 11 labels, the 3 group titles and the chain Starting Points -> product -> Core Capabilities -> Outputs are unchanged (compared by script).`

False for this README: the first group is titled "Inputs and formats", not "Starting Points" (the node id is `StartingPoints`, the title is the maintainers' own). The counts are right.

Fix: as for BarCode-Python (build the chain from `glance.titles`). Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
