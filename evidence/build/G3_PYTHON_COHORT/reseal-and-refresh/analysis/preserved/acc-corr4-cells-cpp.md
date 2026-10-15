authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4: Aspose.Cells-FOSS-for-Cpp (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp @ 9f852d0f)

Verdict: **FIX_REQUIRED** (PR text). Patch 2799 bytes (+32/-17), content + diagram, order 1.

Patch verified by me (acc-corr4-summary section 2): replay byte-equal, `git apply` byte-equal, idempotent with zero edits, validation delta reproduced (introduced 0), live head and README blob unchanged, 4 Mermaid releases x 2 browsers: 0 split words, 0 clipped, horizontal, labels, titles and edges identical to live.

## Content re-verified (fresh clone at 9f852d0f)
`Aspose.Cells.Foss.Cpp/CMakeLists.txt`: `cmake_minimum_required(VERSION 3.16)`, `CMAKE_CXX_STANDARD 17`; the library sources include standard headers only (no third-party header, no `find_package`, no `FetchContent` outside the test project, which fetches GTest). The inserted section (placed after Installation, before Quick Start; Navigation item in the same position) says "No required third-party package dependencies", C++ 17, CMake 3.16. TRUE.

## Sentences I would not sign
1. `why: the README has no Dependencies section; the template's is rendered from the cited facts alone`: no noun, internal.
2. `evidence: `dependency:none` (SUPPORTED): none; `package:cxx_standard` (SUPPORTED): 17; `package:cmake_minimum` (SUPPORTED): 3.16`: fact ids and a literal "none" as evidence; cite `Aspose.Cells.Foss.Cpp/CMakeLists.txt` lines for 3.16 and 17 and say the library includes only standard headers.
3. Advisory U-1 to U-4. Generator fixes live in `src/repository_presenter/components/readme_correction/`; bundles do not change (the text is composed at send time).
