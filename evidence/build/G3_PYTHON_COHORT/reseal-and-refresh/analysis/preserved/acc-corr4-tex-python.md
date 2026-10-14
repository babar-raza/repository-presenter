authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.TeX-FOSS-for-Python (aspose-tex-foss/Aspose.TeX-FOSS-for-Python @ 181015d2)

Verdict: **HOLD** (owner-recorded; confirmed). Patch 1620 bytes (+13/-10), diagram only, order 2, `hold_reason` UPSTREAM_SOURCE_DOES_NOT_PARSE.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live. The PR text is the standard diagram text and has no mismatch with the bundle.

## Hold re-verified (fresh clone at 181015d2; `python -I`, `ast.parse` only, nothing imported)
102 of 119 `.py` files do not parse (36 of 46 non-test files), all 102 with "expected an indented block"; 17 parse. The library cannot be imported. The recorded counts (35 of 45 source files; independent review 102 of 119) agree.

## Notes
- The paired issue exists in the issue approval table (c00f9615, SOURCE_UNPARSEABLE, "FILE wave 1b", no approval record); `scratchpad/lfix/upstream-defect-drafts` holds no draft for this repo. Polishing the diagram of a library that cannot be imported is the owner's call; the hold is sensible.
