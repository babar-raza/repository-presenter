authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-email-cpp: aspose-email-foss/Aspose.Email-FOSS-for-Cpp (run 20261012-0f6828d3) FIX_REQUIRED (text only)

Patch final: 1863 bytes (+17/-13), head c844a467 (live today), `README.original.md` equals the live blob, patch applies byte for byte, byte-identical to the run reviewed last time. Diagram-only PR, order 2. Title: `docs(readme): lay out the At a Glance diagram left to right`.

What is right now: the "owner ruling(s) OD-06, R7" sentence is gone; the Length bullet is in words (303 lines outside collapsed blocks, over the 300-line limit the checks apply, yours was within it; the redraw adds 4 lines). Chain "Starting Points -> the product -> Core Capabilities -> Outputs", 12 labels, 3 group titles match the diagram.

Defect: checks bullet 1 says "The corrected README has no failure that yours does not already have, and has 1 fewer failure(s) than yours." `validation_delta.json`: resolved BC-07 -1, `allowed` BC-07/visible +1; live total 188, corrected 188, so the net is 0, and the Length bullet says the corrected README is over a limit yours was within. The first sentence is false as written.

Fix (generator only, shared with Cells-Go and PDF-Java): when `allowed` or `revealed` is set write "Apart from the length point below, ..." and drop or qualify "N fewer".
