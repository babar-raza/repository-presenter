authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.PDF-FOSS-for-Java (aspose-pdf-foss/Aspose.PDF-FOSS-for-Java @ 736cedaa)

Verdict: **FIX_REQUIRED** (PR text, one sentence). Patch 2541 bytes (+26/-21), content + diagram, order 1.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## Content re-verified
Maven Central `maven-metadata.xml` for org.aspose:aspose-pdf-foss: `latest` and `release` are 26.9.0 (versions 26.6.0, 26.8.0, 26.9.0), the 26.9.0 `.pom` answers 200; the README held `26.6.0` only at L121 (Maven) and L128 (Gradle), both changed, no other `26.x.y` left. TRUE. (The PR says "the package registry" without naming it; naming Maven Central and the metadata URL would let the maintainer check in one click.)

## The sentence
`... 0 introduced failure(s), 3 fewer failure(s) than before; 1 recorded under owner ruling(s) OD-06, R7.`

The record is BC-07/visible: "304 visible lines of 1680 exceed the visible budget 300", caused by the init line and column links of the redraw. Unreadable as written (internal ids, "owner" misleads). Fix in `_delta_lines` as for Email-Cpp. Advisory U-1 to U-4. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
