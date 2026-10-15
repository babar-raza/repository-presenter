authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-pdf-java: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (run 20261012-0f6828d3) FIX_REQUIRED (text only)

Patch final: 2541 bytes (+26/-21), head 736cedaa (live today), `README.original.md` equals the live blob, patch applies byte for byte, byte-identical to the run reviewed last time. Content PR, order 1.

Title: `docs(readme): show the current release (26.9.0) in the install snippets and lay out the At a Glance diagram left to right`

What is right now: the version claim. Maven Central `maven-metadata.xml` today: latest and release 26.9.0, versions 26.6.0, 26.8.0, 26.9.0; lines 121 (`<version>26.6.0</version>`) and 128 (`implementation 'org.aspose:aspose-pdf-foss:26.6.0'`) carry the old value. The unexplained "owner ruling OD-06, R7" is gone; the Length bullet now reads in words (304 lines outside collapsed blocks, over the 300-line limit the checks apply, yours was within it); the redraw adds 5 lines to a README that had 299.

Defect: checks bullet 1 says "The corrected README has no failure that yours does not already have, and has 3 fewer failure(s) than yours." `validation_delta.json`: resolved BC-07 -1 and BC-14 -2, but `allowed` BC-07/visible +1 (304 visible lines of 1680 over the budget 300); live total 238, corrected 236, so the net is 2 fewer, and a failure the maintainer's README lacked exists, which the Length bullet two lines below states ("yours was within it"). The first sentence contradicts it.

Fix (generator only, `pull_request.py` `_delta_lines`): when `allowed` or `revealed` is set write "Apart from the length point below, ..." and drop or qualify "N fewer". Add a test that the sentence matches the delta's net count.
