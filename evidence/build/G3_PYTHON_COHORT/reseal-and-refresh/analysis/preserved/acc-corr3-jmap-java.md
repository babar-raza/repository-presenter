authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.JMAP-FOSS-for-Java

Verdict: **FIX_REQUIRED** | minor_major: **MINOR** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-email-foss/Aspose.JMAP-FOSS-for-Java | live head f0d6ba73 (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 1734 bytes (+14/-10) | edits: at_a_glance_diagram

## Why this verdict
The redrawn diagram splits words mid-token on Mermaid 12.1.0 (5 node(s): i1, i2, c3, c4, o2); a one-token generator fix is validated below. Everything else (replay, label/edge identity, 11.x renders, content edits) is correct.

## Edits
- `at_a_glance_diagram` (DIAGRAM_FIX) L34: the At a Glance diagram on line 34 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text labels

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `f0d6ba73`; applying ONLY the 1 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram. No add_dev_commands or add_doc_links edit survives (report-only: add_dev_commands:ALREADY_SHOWN; add_dev_commands:RE_ENABLE_CONDITION_UNMET).
- Diff outside the Mermaid fence: empty: not one line outside the Mermaid fence changed, so no narration or stray text is possible.
- Diagram identity (own parse): node ids equal; 9 labels identical after `<br/>` normalisation; 3 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged; 5 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 2 to 3 of 5 fonts, never in the native font. checked programmatically (block order left to right, column reading order, no node overlap) rather than by eye; evidence `scratchpad/acccorr3/after_png/Aspose.JMAP-FOSS-for-Java.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; no two-column capability layout in this diagram.
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 9 node(s) drawn with more lines than the `<br/>` breaks ask for; **5 node(s) split a word mid-token** (i1, i2, c3, c4, o2). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.69, redraw 0.89 (x1.29); drawn height 554 px to 470 px.
- Links and structure, live vs corrected (own checker): links 24 -> 24 | broken before 0 after 0 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 11 11 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

## Fix
One generator token: add `"wrappingWidth": 400` to the `flowchart` object of the redraw's init line. I re-rendered this diagram's after-body with it: 0 stray wraps and 0 mid-word breaks on 12.1.0, identical lines on 11.4.1, 11.12.0, 11.17.2, still horizontal with 0 clipped fonts on all 4 (all 39 diagrams re-measured). If the owner confirms that github.com runs Mermaid below 12 (paste a fenced `mermaid` block containing only the word `info` into any README preview; it prints the version), this patch is PUSHABLE as it stands.

## PR value
Diagram-only PR. Diagram benefit: moderate (text x1.29 at README width).
