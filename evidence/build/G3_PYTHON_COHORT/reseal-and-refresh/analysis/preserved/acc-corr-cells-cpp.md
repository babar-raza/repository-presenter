authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-cells-cpp: Aspose.Cells-FOSS-for-Cpp (live head 9f852d0f)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/`.
Clone: `scratchpad/acccorr/clones/Aspose.Cells-FOSS-for-Cpp`, HEAD 9f852d0f == bundle `source_revision`.

**Verdict: FIX_REQUIRED, minor_major MINOR** (Navigation not updated; clumsy evidence-citation sentence; section incomplete against the repo and sibling READMEs).

## 1. Edit confinement
- `README.original.md` == `git show HEAD:README.md` (a811deae...); corrected sha matches `corrections.json`.
- Replay of the one enumerated `MISSING_SECTION` edit over the original reproduces `README.md` exactly; difflib: one insert hunk (9 lines), 0 deletions. Nothing of the maintainers' text altered or lost. LF-only.
- Placement after the Installation section (after the `add_subdirectory` fence), before Quick Start: template order.

## 2. Claim checks
| # | Claim | Check | Result |
|---|---|---|---|
| 1 | no Dependencies section in live README | headings (grep) | PASS |
| 2 | "No required third-party package dependencies" | `Aspose.Cells.Foss.Cpp/CMakeLists.txt` (full read): no `find_package`, `FetchContent`, or `target_link_libraries` to external libs; `grep '#include <'` over `src/` and `include/` shows only standard headers (`<string>`, `<vector>`, `<variant>`, `<charconv>`, `<fstream>`, ...) | PASS |
| 3 | "Requires C++ `17` (`CMAKE_CXX_STANDARD` in CMakeLists.txt)" | CMakeLists L5 `set(CMAKE_CXX_STANDARD 17)` | PASS |
| 4 | Sentence: "in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`, no dependency is on the library target's public link interface, so a consumer links nothing beyond the library itself" | true but reads as a machine evidence citation; compare siblings (Cells-Java: "builds from `pom.xml`, which declares no dependencies outside `test` scope") | MISLEADING-minor wording |
| 5 | Completeness: CMake minimum | `cmake_minimum_required(VERSION 3.16)`; extractor already holds fact `package:cmake_minimum`=3.16 | OMITTED (Slides-Cpp sibling states "CMake 3.20+") |
| 6 | Completeness: development dependencies | `Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt`: GoogleTest v1.14.0 via `FetchContent` (or system GTest with `ASPOSE_CELLS_FOSS_TESTS_USE_SYSTEM_GTEST`); the README itself says so at "Development and Testing" | OMITTED (PDF-Cpp sibling lists `googletest (1.14.0)` under Development Dependencies) |
| 7 | New section in Navigation | live README L13-24 lists all H2s except the new one | FAIL (introduced) |
| 8 | Windows-only prebuilt NuGet libs caveat | already in Installation (L93-96); not repeated | n/a |
| 9 | NuGet pin `Aspose.Cells.Cpp.FOSS 26.4.1` (inherited, unchanged) | `api.nuget.org/v3-flatcontainer/aspose.cells.cpp.foss/index.json` = 26.4.0, 26.4.1 | PASS (still current) |

## 3. Render and style
- One H1, no duplicate headings, fences closed, no links inserted. Heading structure same as sibling READMEs.
- Tone: acceptable apart from item 4. A maintainer would accept the Dependencies content but likely rewrite the first sentence and ask for the Nav entry.

## 4. Fixes
| id | kind | severity | fix |
|---|---|---|---|
| F1 | code_change (small, generic) | MINOR | Insert the Navigation entry when a Navigation list exists (same defect as Cells-.NET) |
| F2 | redraw / template | MINOR | Replace the evidence-citation sentence with "No required third-party package dependencies; the library builds from `Aspose.Cells.Foss.Cpp/CMakeLists.txt` using only the C++ standard library." |
| F3 | code_change (extractor) | MINOR | C++ extractor: read `FetchContent_Declare`/`find_package(GTest)` from the Tests CMake into `dependency:development.*` facts; use the existing `package:cmake_minimum` fact in "Native and System Requirements" |

could_not_verify: nothing built (no cmake/g++ on this host); the lane's failing example 2 (missing `#include`) was not re-run.
confidence: high.
