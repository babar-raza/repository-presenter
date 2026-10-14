authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.Words-FOSS-for-.NET (aspose-words-foss/Aspose.Words-FOSS-for-.NET @ 0d3f1add)

Verdict: **FIX_REQUIRED** (PR text: garbled sentences). Patch 2466 bytes (+22/-17), content + diagram, order 1.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## Content re-verified
nuget.org lists Aspose.Words.FOSS 26.2.0 and 26.3.0; the README already says "Install from NuGet: dotnet add package Aspose.Words.FOSS". The added badge (`https://img.shields.io/nuget/v/Aspose.Words.FOSS.svg`, linking nuget.org/packages/Aspose.Words.FOSS/) leads the badge row at L5. TRUE.

## Sentences I would not sign
1. `The README lacks published-version badge, which the repository at revision `0d3f1add920f` verifies (evidence listed below).` (`pull_request.py` `_lead`, "info"): clumsy and without the article; name the package and the registry instead ("The README has no NuGet version badge; Aspose.Words.FOSS is published on nuget.org (26.3.0)").
2. `why: the README shows no published-version badge; the registry's leads its badge row (the package badge is first in the stable order)` (`detectors/additions.py:630`): a broken sentence; "the registry's" has lost its noun and "the stable order" is internal.
3. Evidence is fact ids with `(SUPPORTED)`; cite nuget.org.
4. Advisory: L952 still says "The NuGet package and new formats are landing soon." right under the new badge. `stale_phrase` reports it; the PR could say "noticed, not changed". Advisory U-1 to U-4. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
