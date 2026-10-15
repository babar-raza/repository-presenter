authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.Cells-FOSS-for-Go (aspose-cells-foss/Aspose.Cells-FOSS-for-Go @ 99c789e9)

Verdict: **FIX_REQUIRED** (PR text). Patch 2786 bytes (+24/-17), structure + diagram, order 1.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## Content re-verified (live README read)
`<details>` opened at L501 ("More Test and Example Commands") and never closed; L105 `# Requires **Go 1.24.5+** ...` is a second H1 after the Installation code block. The patch changes `#` to `##` and inserts `</details>` before `## Detailed Documentation` (L529), nothing else. Introduced failures 0; BC-04 sees one more failure (`v26` code span, 23 against 22) in text the unclosed block had hidden.

## Sentences I would not sign
1. `why: line 105 is a second H1 (...); the template has exactly one, the product title on line 1` (`detectors/structure.py:46`): "the template" is internal; the reason a maintainer understands is "a README has one top-level heading, the title".
2. `why: the <details> opened on line 501 is never closed, so everything after it renders collapsed; it ends before the next H2, line 529` (`structure.py:107`): the closing point is our reading (the owner table calls it inferred), stated as fact. Say "we closed it before the next H2 (L529); tell us if it should end elsewhere".
3. `fail no check more often on the corrected README than on yours: 0 introduced failure(s), 1 fewer failure(s) than before; 1 check(s) now judge text that was hidden inside the broken markup`: the first clause is literally false for BC-04 (23 against 22); the disclosure is in the same sentence, but the opening claim should not be made. Name the check and the text.
4. Advisory: `##` on a sentence leaves a sentence as a heading and the Navigation item unindented; deleting the `#` reads better. Advisory U-1 to U-4. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
