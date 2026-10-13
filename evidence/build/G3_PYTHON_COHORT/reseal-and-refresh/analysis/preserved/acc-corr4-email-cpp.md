authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.Email-FOSS-for-Cpp (aspose-email-foss/Aspose.Email-FOSS-for-Cpp @ c844a467)

Verdict: **FIX_REQUIRED** (PR text, one sentence). Patch 1863 bytes (+17/-13), diagram only, order 2.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## The sentence
`- The project's validators (`validate_candidate`, checks BC-01 to BC-14) fail no check more often on the corrected README than on yours: 0 introduced failure(s), 1 fewer failure(s) than before; 1 recorded under owner ruling(s) OD-06, R7.`

True to the record (validation_delta.json `allowed`: BC-07/visible, "303 visible lines of 479 exceed the visible budget 300", caused by the init line and the `~~~` links the redraw adds) but unreadable to a maintainer: two internal identifiers, and "owner ruling" reads as the repository owner's ruling. An honest reading is: "the README is now 303 lines long, three over the length limit the project applies to its own READMEs, because the redraw adds an init line and column links".

Fix (`pull_request.py` `_delta_lines`, the `allowed` branch): say that in words and drop the ruling ids. Same advisory U-1 to U-3 as every PR. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
Pilot note: text gain x1.69; wait for the fix.
