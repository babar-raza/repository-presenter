authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.3D-FOSS-for-.NET (aspose-3d-foss/Aspose.3D-FOSS-for-.NET @ 52b0f00e)

Verdict: **HOLD** (owner-recorded; confirmed). Patch 2401 bytes (+24/-19), diagram only, order 2, `hold_reason` README_ADVERTISES_UNSUPPORTED_FORMATS.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live. The PR text is the standard diagram text and has no mismatch with the bundle.

## Hold re-verified (fresh clone at 52b0f00e)
`src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/IOService.cs` L57-67 (importers) and L78-88 (exporters) dispatch OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS and `throw new NotSupportedException` otherwise; the diagram labels U3D, RVM, AMF and HTML5 (and the PR republishes them verbatim). TRUE.

## Notes
- The README's recent commits are the owner's own refreshes (158183d2, 042a1e5f, 52b0f00e by Babar Raza), so this is a README correction (drop the unsupported labels) as much as an issue. The pairing in the hold ("an issue naming the formats the code rejects") is not the only vehicle; the issue-approval table lists it as RC-3DNET-FORMATS, README-CORRECTION (ours).
- No detector can remove a label; the redraw alone is the diagram PR. Send this PR only together with the fix of the labels or the issue.
