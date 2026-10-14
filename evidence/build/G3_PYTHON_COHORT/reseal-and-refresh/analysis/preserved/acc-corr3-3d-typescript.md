authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.3D-FOSS-for-TypeScript

Verdict: **PUSHABLE** | minor_major: **none** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | live head 66cb26df (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2014 bytes (+22/-17) | edits: at_a_glance_diagram

## Why this verdict
Patch verified clean; diagram label and edge identical, horizontal, 0 clipped on 4 releases, no mid-word break on 12.1.0.

## Edits
- `at_a_glance_diagram` (DIAGRAM_FIX) L31: the At a Glance diagram on line 31 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `66cb26df`; applying ONLY the 1 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram. No add_dev_commands or add_doc_links edit survives (report-only: add_dev_commands:ALREADY_SHOWN; add_dev_commands:ALREADY_SHOWN).
- Diff outside the Mermaid fence: empty: not one line outside the Mermaid fence changed, so no narration or stray text is possible.
- Diagram identity (own parse): node ids equal; 13 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 8 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 3 to 4 of 5 fonts, never in the native font. checked programmatically (block order left to right, column reading order, no node overlap) rather than by eye; evidence `scratchpad/acccorr3/after_png/Aspose.3D-FOSS-for-TypeScript.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 reversed (the known 12.x column-heuristic reversal that `check_entry` documents; advisory).
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 2 node(s) drawn with more lines than the `<br/>` breaks ask for; **0 node(s) split a word mid-token** (none). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.84, redraw 0.77 (x0.92); drawn height 907 px to 436 px.
- Links and structure, live vs corrected (own checker): links 20 -> 20 | broken before 0 after 0 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 11 11 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

## PR value
Diagram-only PR. Diagram benefit: weak (text not meaningfully larger; the gain is the shorter, horizontal shape) (text x0.92 at README width).
