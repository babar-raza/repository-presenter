authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Cells-FOSS-for-Cpp

Verdict: **PUSHABLE (minor advisories)**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp  |  live head 9f852d0f

## Edits
1. `missing_sections` L18: Navigation gains `- [Dependencies](#dependencies)`.
2. `at_a_glance_diagram` L29: redraw.
3. `missing_sections` L125: new `## Dependencies` ("No required third-party package dependencies."; "Requires C++ `17`."; "Requires CMake 3.16 or later.").

## Findings
- Both defects found when the first bundle of this repo was reviewed are fixed: Navigation now lists Dependencies (10 to 11 items); the section no longer cites machine evidence and now includes CMake 3.16.
- Claims verified in the clone: `Aspose.Cells.Foss.Cpp/CMakeLists.txt` L1 `cmake_minimum_required(VERSION 3.16)`, L4-5 `CMAKE_CXX_STANDARD 17` and `..._REQUIRED ON`; the Tests and samples projects also declare 3.16; README L11 itself says "no external runtime dependencies" and the library includes only standard headers. No registry claim exists for C++ (README names none).
- Diagram PASS: 12 labels, titles, 3 edges identical; order c1..c9 (left c1-c5, right c6-c9); vertical 1661x1050 to horizontal 1122x818; 0 clipped.
- Advisory (minor, no fix needed to push): the section omits the GoogleTest v1.14.0 test dependency that the README's own Development section documents (L583), and "Requires C++ `17`." has stray backticks. The README's `ctest --test-dir` (Development) needs CMake 3.20, so "CMake 3.16 or later" is the declared minimum, not what the documented test run needs.
- Links 28 to 29; the 4 "broken" relative links my checker flags (`cellName`, `index`) are table-cell text, not links (identical in the live README). No narration.

## Verdict
PUSHABLE.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1661x1050 to horizontal 1122x818; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp`). README.md sha256 `446dc58ea8746557908818786161ae2c0109a0d552c0bac6c1b99286e8a527e2`.
- Fresh `git clone --depth 1` of the live head: `9f852d0f` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 3 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
