authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.Cells-FOSS-for-.NET (aspose-cells-foss/Aspose.Cells-FOSS-for-.NET @ 941814fd)

Verdict: **FIX_REQUIRED** (PR text). Patch 2588 bytes (+31/-15), content + diagram, order 1.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## Content re-verified (fresh clone at 941814fd and nuget.org)
- `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj`: one `PackageReference` (SkiaSharp 2.88.8) and `TargetFrameworks netstandard2.0;net8.0`; the published 26.9.0 nuspec lists SkiaSharp 2.88.8 for both targets. The inserted section and the Navigation item (between Installation and Quick Start, outside any fence or details) say exactly that. TRUE.

## Sentences I would not sign
1. `why: the README has no Dependencies section; the template's is rendered from the cited facts alone` (`detectors/sections.py:376`): "the template's" has no noun and no meaning to a maintainer.
2. `evidence: `dependency:skiasharp` (SUPPORTED): SkiaSharp 2.88.8; `package:target_framework` (SUPPORTED): netstandard2.0;net8.0` (and the lead "it is rendered from facts verified against the repository at revision ..."): internal fact ids and statuses; the file and line that hold the facts are not named, so the maintainer cannot check the claim from the PR. Cite `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj` (PackageReference, TargetFrameworks).
3. Advisory: the new section sits beside an intro that says "pure managed code ... Windows, Linux, and macOS" while SkiaSharp 2.88.8 ships native assets for Windows and macOS only; the new heading "Native and System Requirements" lists only the target frameworks. True, incomplete. One sentence in the PR would let the maintainer decide.
4. Advisory U-1 to U-4 (the redraw rides in this PR). Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
