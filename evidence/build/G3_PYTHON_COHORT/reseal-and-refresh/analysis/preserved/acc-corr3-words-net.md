authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.Words-FOSS-for-.NET

Verdict: **PUSHABLE** | minor_major: **minor advisory** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-words-foss/Aspose.Words-FOSS-for-.NET | live head 0d3f1add (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2444 bytes (+22/-17) | edits: add_version_badge, at_a_glance_diagram

## Why this verdict
Patch verified clean; diagram label and edge identical, horizontal, 0 clipped on 4 releases, no mid-word break on 12.1.0.

## Edits
- `add_version_badge` (MISSING_INFO) L5: the README shows no published-version badge; the registry's leads its badge row (the package badge is first in the stable order)
- `at_a_glance_diagram` (DIAGRAM_FIX) L10: the At a Glance diagram on line 10 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `0d3f1add`; applying ONLY the 2 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: add_version_badge, at_a_glance_diagram. No add_dev_commands or add_doc_links edit survives (report-only: add_dev_commands:ALREADY_SHOWN; add_dev_commands:ALREADY_SHOWN).
- Diff outside the Mermaid fence: exactly the content edits listed below (no narration, no first-person or process wording).
- Diagram identity (own parse): node ids equal; 14 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 9 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 3 to 3 of 5 fonts, never in the native font. I viewed the PNG; evidence `scratchpad/acccorr3/after_png/Aspose.Words-FOSS-for-.NET.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 reversed (the known 12.x column-heuristic reversal that `check_entry` documents; advisory).
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 4 node(s) drawn with more lines than the `<br/>` breaks ask for; **0 node(s) split a word mid-token** (none). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.84, redraw 0.76 (x0.90); drawn height 889 px to 416 px.
- Links and structure, live vs corrected (own checker): links 38 -> 39 | broken before 3 after 3 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 15 15 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

### Content edits (re-verified against the registry)
- `add_version_badge` L5: adds the NuGet badge `[![NuGet](https://img.shields.io/nuget/v/Aspose.Words.FOSS.svg)](https://www.nuget.org/packages/Aspose.Words.FOSS/)` before the License badge. TRUE: nuget.org lists Aspose.Words.FOSS 26.2.0 and 26.3.0; the shields badge returns 200 and its title reads `nuget: v26.3.0`; the package page returns 200; the README already says "Install from NuGet" (L94).
- Advisory (not introduced): L957 still says "The NuGet package and new formats are landing soon." right below a badge that now shows the live package; `stale_phrase` only reports it. Worth a one-line mention in the PR, since the badge makes the contradiction visible.

## PR value
Content PR: an uncontroversial factual fix; send it as its own PR, separate from the diagram. Diagram benefit: weak (text not meaningfully larger; the gain is the shorter, horizontal shape) (text x0.90 at README width).
