authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.Cells-FOSS-for-.NET

Verdict: **PUSHABLE** | minor_major: **minor advisory** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | live head 941814fd (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2566 bytes (+31/-15) | edits: at_a_glance_diagram, missing_sections

## Why this verdict
Patch verified clean; diagram label and edge identical, horizontal, 0 clipped on 4 releases, no mid-word break on 12.1.0.

## Edits
- `missing_sections` (MISSING_INFO) L14: the README's contents list gains the Dependencies item beside line 14, so the inserted section is reachable from it
- `at_a_glance_diagram` (DIAGRAM_FIX) L25: the At a Glance diagram on line 25 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la
- `missing_sections` (MISSING_SECTION) L80: the README has no Dependencies section; the template's is rendered from the cited facts alone

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `941814fd`; applying ONLY the 3 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram, missing_sections. No add_dev_commands or add_doc_links edit survives (report-only: add_dev_commands:ALREADY_SHOWN).
- Diff outside the Mermaid fence: exactly the content edits listed below (no narration, no first-person or process wording).
- Diagram identity (own parse): node ids equal; 11 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 6 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 3 to 5 of 5 fonts, never in the native font. I viewed the PNG; evidence `scratchpad/acccorr3/after_png/Aspose.Cells-FOSS-for-.NET.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 forward.
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 2 node(s) drawn with more lines than the `<br/>` breaks ask for; **0 node(s) split a word mid-token** (none). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.84, redraw 0.78 (x0.92); drawn height 950 px to 425 px.
- Links and structure, live vs corrected (own checker): links 24 -> 25 | broken before 0 after 0 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 10 11 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; no allowance used; resolved [('BC-07', 1)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

### Content edits (re-verified against the live clone and the registry)
- `missing_sections` L14, Navigation gains `- [Dependencies](#dependencies)`: the anchor resolves to the new H2 (my link check: 24 to 25 links, 0 broken, every H2 reachable).
- `missing_sections` L80, new `## Dependencies` (`SkiaSharp 2.88.8`; "Requires .NET `netstandard2.0;net8.0`"). TRUE: `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj` L53 `PackageReference Include="SkiaSharp" Version="2.88.8"` (L52 comment: powers the XLSX-to-PDF renderer), L3 `TargetFrameworks` = `netstandard2.0;net8.0`; it is the only PackageReference; the nuspec of the published Aspose.Cells.FOSS 26.9.0 on nuget.org lists SkiaSharp 2.88.8 under net8.0 and .NETStandard2.0 (NuGet versions 26.5.0, 26.6.0, 26.7.0, 26.9.0).
- Advisory (minor, not introduced): the intro (L7) says "pure managed code ... runs on Windows, Linux, and macOS", while SkiaSharp 2.88.8 depends on `SkiaSharp.NativeAssets.Win32` and `.macOS` only (Linux needs a separate native-assets package; nuget.org nuspec). The new section is true but sits beside a sentence it softens; a maintainer may want a Linux note. "Requires .NET `netstandard2.0;net8.0`" is a target-framework property list, not a system requirement, and reads oddly.

## PR value
Content PR: an uncontroversial factual fix; send it as its own PR, separate from the diagram. Diagram benefit: weak (text not meaningfully larger; the gain is the shorter, horizontal shape) (text x0.92 at README width).
