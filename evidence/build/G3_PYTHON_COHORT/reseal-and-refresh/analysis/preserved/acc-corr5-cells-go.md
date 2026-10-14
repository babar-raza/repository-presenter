authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-cells-go: aspose-cells-foss/Aspose.Cells-FOSS-for-Go (run 20261012-0f6828d3) FIX_REQUIRED (text only)

Patch final: 2786 bytes (+24/-17), head 99c789e9 (live today), `README.original.md` equals the live blob, patch applies and gives `README.md` byte for byte, byte-identical to the run reviewed last time. Content PR, order 1.

Title: `docs(readme): demote a stray second H1, close an unclosed <details> block and lay out the At a Glance diagram left to right`

What is right now: the reasons are in plain words; the `#` bullet offers "deleting the `#` instead may read better"; the `<details>` bullet says "that is our reading of where it should end, so tell us if it should end elsewhere". Lines 105 (`# Requires **Go 1.24.5+** ...`), 501 (`<details>`) and 529 (`## Detailed Documentation`) checked in the original. No internal identifier.

Defect: checks bullet 1 says "The corrected README has no failure that yours does not already have, and has 1 fewer failure(s) than yours." `validation_delta.json`: resolved BC-07 -1 (16 to 15), revealed BC-04 +1 (22 to 23, "code span 'v26' is not a fact value"); live total 129, corrected total 129, so the net drop is 0, not 1. Bullet 2 then says "they now report 1 issue(s) there (for example the code span `v26`)". Substance defensible (the text is the maintainer's, newly readable), but the sentence is not exact and "1 issue(s) there" does not say what the issue is.

Fix (generator only, `pull_request.py` `_delta_lines`; no bundle change): when `revealed` is set write "Apart from the point described next, ..." and drop or qualify "N fewer"; say what the check found ("it flags the code span `v26` as not tied to a fact in the repository"). Mild; the owner may decide to send as is after reading this.
