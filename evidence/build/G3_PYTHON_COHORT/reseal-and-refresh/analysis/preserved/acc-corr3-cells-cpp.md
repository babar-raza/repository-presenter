authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.Cells-FOSS-for-Cpp

Verdict: **PUSHABLE** | minor_major: **minor advisory** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | live head 9f852d0f (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2777 bytes (+32/-17) | edits: at_a_glance_diagram, missing_sections

## Why this verdict
Patch verified clean; diagram label and edge identical, horizontal, 0 clipped on 4 releases, no mid-word break on 12.1.0.

## Edits
- `missing_sections` (MISSING_INFO) L18: the README's contents list gains the Dependencies item beside line 18, so the inserted section is reachable from it
- `at_a_glance_diagram` (DIAGRAM_FIX) L29: the At a Glance diagram on line 29 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la
- `missing_sections` (MISSING_SECTION) L125: the README has no Dependencies section; the template's is rendered from the cited facts alone

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `9f852d0f`; applying ONLY the 3 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram, missing_sections. No add_dev_commands or add_doc_links edit survives (report-only: none).
- Diff outside the Mermaid fence: exactly the content edits listed below (no narration, no first-person or process wording).
- Diagram identity (own parse): node ids equal; 12 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 7 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 2 to 5 of 5 fonts, never in the native font. I viewed the PNG; evidence `scratchpad/acccorr3/after_png/Aspose.Cells-FOSS-for-Cpp.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 reversed (the known 12.x column-heuristic reversal that `check_entry` documents; advisory).
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 3 node(s) drawn with more lines than the `<br/>` breaks ask for; **0 node(s) split a word mid-token** (none). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.53, redraw 0.78 (x1.47); drawn height 573 px to 661 px.
- Links and structure, live vs corrected (own checker): links 28 -> 29 | broken before 4 after 4 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 10 11 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

### Content edits (re-verified against the live clone)
- `missing_sections` L18 Navigation item and L125 new `## Dependencies` ("No required third-party package dependencies"; "Requires C++ `17`"; "Requires CMake 3.16 or later"). TRUE: `Aspose.Cells.Foss.Cpp/CMakeLists.txt` L1 `cmake_minimum_required(VERSION 3.16)`, L4 `CMAKE_CXX_STANDARD 17`; the library target has no `find_package`, `FetchContent` or third-party include (my include census: only the C++ standard library; no zlib, xml, openssl or minizip anywhere); GoogleTest is fetched only by `Aspose.Cells.Foss.Cpp.Tests`. The README's own intro already says "dependency-free ... no external runtime dependencies", so the section agrees with it.
- Navigation anchor resolves; the 4 pre-existing "broken" relative targets my checker lists (L507-523, `cellName`/`index`) are code text, not links, and are unchanged by the patch.

## PR value
Content PR: an uncontroversial factual fix; send it as its own PR, separate from the diagram. Diagram benefit: strong (text x1.47 at README width).
