authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.Cells-FOSS-for-Go

Verdict: **FIX_REQUIRED** | minor_major: **MINOR** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Go | live head 99c789e9 (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2764 bytes (+24/-17) | edits: at_a_glance_diagram, second_h1, unclosed_details

## Why this verdict
The redrawn diagram splits words mid-token on Mermaid 12.1.0 (3 node(s): i1, c3, o1); a one-token generator fix is validated below. Everything else (replay, label/edge identity, 11.x renders, content edits) is correct.

## Edits
- `at_a_glance_diagram` (DIAGRAM_FIX) L46: the At a Glance diagram on line 46 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la
- `second_h1` (STRUCTURE_FIX) L105: line 105 is a second H1 ('# Requires **Go 1.24.5+** (see `go.mod`). Depends only on th'); the template has exactly one, the product title on line 1
- `unclosed_details` (STRUCTURE_FIX) L529: the <details> opened on line 501 is never closed, so everything after it renders collapsed; it ends before the next H2, line 529

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `99c789e9`; applying ONLY the 3 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram, second_h1, unclosed_details. No add_dev_commands or add_doc_links edit survives (report-only: none).
- Diff outside the Mermaid fence: exactly the content edits listed below (no narration, no first-person or process wording).
- Diagram identity (own parse): node ids equal; 12 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 7 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 3 to 5 of 5 fonts, never in the native font. I viewed the PNG; evidence `scratchpad/acccorr3/after_png/Aspose.Cells-FOSS-for-Go.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 reversed (the known 12.x column-heuristic reversal that `check_entry` documents; advisory).
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 4 node(s) drawn with more lines than the `<br/>` breaks ask for; **3 node(s) split a word mid-token** (i1, c3, o1). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.65, redraw 0.74 (x1.13); drawn height 767 px to 525 px.
- Links and structure, live vs corrected (own checker): links 42 -> 42 | broken before 0 after 0 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 1 0 | nav items before/after 27 27 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 1. no_op proof byte_identical/idempotent True/True, provider calls 0.

### Content edits (re-verified against the live README)
- `unclosed_details` (insert `</details>` before `## Detailed Documentation`, L529): CONFIRMED defect. The `<details>` at L501 ("More Test and Example Commands") is never closed in the live README; in my structure check the H2s Detailed Documentation, Constraints and License sit inside the open `<details>` before, and outside it after (details opened minus closed: 1 before, 0 after). The closing point is inferred (end of the test-commands text, before the next H2); plausible and the only sensible place.
- `second_h1` (L105 `#` to `##`): the live README has two H1s (the title and `# Requires **Go 1.24.5+** (see go.mod). Depends only on the Go standard library ...`). The fix is directionally right and minimal but half-way: the sentence is still a heading (now H2), and the hand-made Navigation list keeps it unindented, so its indentation no longer matches the heading level (minor, cosmetic; the link still resolves). The line looks like a shell comment that fell out of the Installation code block; dropping the `#` (plain text) would be the better fix. `validation_delta` reveals one pre-existing BC-04 failure (`v26` code span) that the collapsed `<details>` used to hide; it is not introduced.
- No wording changed.

## Fix
One generator token: add `"wrappingWidth": 400` to the `flowchart` object of the redraw's init line. I re-rendered this diagram's after-body with it: 0 stray wraps and 0 mid-word breaks on 12.1.0, identical lines on 11.4.1, 11.12.0, 11.17.2, still horizontal with 0 clipped fonts on all 4 (all 39 diagrams re-measured). If the owner confirms that github.com runs Mermaid below 12 (paste a fenced `mermaid` block containing only the word `info` into any README preview; it prints the version), this patch is PUSHABLE as it stands.

## PR value
Content PR: an uncontroversial factual fix; send it as its own PR, separate from the diagram. Diagram benefit: moderate (text x1.13 at README width).
