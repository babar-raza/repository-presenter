authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3: Aspose.PDF-FOSS-for-Java

Verdict: **PUSHABLE** | minor_major: **minor advisory** | reviewer: independent (Sonnet 5.5), read-only

Repository: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | live head 736cedaa (equals `manifest.revision`; `git ls-remote` re-checked at the end: no drift) | patch 2519 bytes (+26/-21) | edits: at_a_glance_diagram, claim_version

## Why this verdict
Patch verified clean; diagram label and edge identical, horizontal, 0 clipped on 4 releases, no mid-word break on 12.1.0.

## Edits
- `at_a_glance_diagram` (DIAGRAM_FIX) L29: the At a Glance diagram on line 29 is drawn with CLIP_AUTO_WRAP, CLIP_HTML_LABELS, COLUMN_ORDER, GROUP_LAID_AS_ROW, ORDER_UNPINNED, ORIENTATION_VERTICAL; the same labels, titles and chain are redrawn left to right with SVG text la
- `claim_version` (FALSE_CLAIM_FIX) L121: org.aspose:aspose-pdf-foss is shown at version 26.6.0, but the registry's current stable release is 26.9.0
- `claim_version` (FALSE_CLAIM_FIX) L128: org.aspose:aspose-pdf-foss is shown at version 26.6.0, but the registry's current stable release is 26.9.0

## Checks (all run by me)
- Run directory: `sha256sum -c SHA256SUMS` 353/353 OK (re-run at the end; my snapshot is byte-identical).
- Replay confinement: `README.original.md` equals the live blob at `736cedaa`; applying ONLY the 3 enumerated edit(s) of `corrections.json` (each `original` span matched, no overlap) reproduces `README.md` byte for byte; removing the edit spans from both sides leaves identical text; `README.patch` applies with `git apply` and reproduces `README.md` byte for byte; LF only. Detectors present: at_a_glance_diagram, claim_version. No add_dev_commands or add_doc_links edit survives (report-only: add_dev_commands:ALREADY_SHOWN; add_dev_commands:RE_ENABLE_CONDITION_UNMET).
- Diff outside the Mermaid fence: exactly the content edits listed below (no narration, no first-person or process wording).
- Diagram identity (own parse): node ids equal; 20 labels identical after `<br/>` normalisation; 5 subgraph titles identical; visible edges identical; parents identical; per-group order unchanged (the two capability columns are listed in swapped source order on purpose); 15 invisible `~~~` links; no label holds `&`, `<`, `>` (outside `<br/>`) or an entity reference; the init line is the only extra directive.
- Real render by me (repo `render_check` with the lane's pinned tools, headless Edge 155, native font plus five stress fonts) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0: redrawn diagram horizontal on all 4, clipped fonts 0 of 5 on all 4, no native spill: **PASS**. The live diagram, same renderer: vertical on all 4, clipped in 4 to 5 of 5 fonts, never in the native font. I viewed the PNG; evidence `scratchpad/acccorr3/after_png/Aspose.PDF-FOSS-for-Java.png`.
- Reading order (node positions, all 4 releases): Starting Points, product, Capabilities, Outputs left to right; inside every group the ids run top to bottom; two capability columns: first half left on 11.4.1, 11.12.0, 11.17.2; on 12.1.0 reversed (the known 12.x column-heuristic reversal that `check_entry` documents; advisory).
- Mermaid 12.1.0 label wrapping (a check the lane's `check_entry` does not make): 2 node(s) drawn with more lines than the `<br/>` breaks ask for; **0 node(s) split a word mid-token** (none). On 11.4.1, 11.12.0, 11.17.2: 0.
- Text scale at a 896 px README column (estimate from the render sizes): live 0.53, redraw 0.82 (x1.54); drawn height 522 px to 666 px.
- Links and structure, live vs corrected (own checker): links 47 -> 47 | broken before 0 after 0 | introduced [] | resolved [] | dup H2 before/after [] [] | unclosed details before/after 0 0 | nav items before/after 11 11 | H2 not in nav (after): [] | H2 not in nav (before): []
- `validation_delta`: introduced 0; allowed BC-07/visible; resolved [('BC-07', 1), ('BC-14', 2)]; revealed 0. no_op proof byte_identical/idempotent True/True, provider calls 0.

### Content edits (re-verified against the registry and the live clone)
- `claim_version` L121 (Maven) and L128 (Gradle) `26.6.0` to `26.9.0`. TRUE: Maven Central `maven-metadata.xml` for `org/aspose/aspose-pdf-foss` lists `latest` and `release` 26.9.0 (lastUpdated 2026-10-07; versions 26.6.0, 26.8.0, 26.9.0); the 26.9.0 `.pom` and `.jar` return 200; `pom.xml` at the live head says `<version>26.9.0</version>`. No other `26.x.y` string remains in the corrected README. `validation_delta`: BC-14 resolved by 2 (the two stale versions), BC-07 resolved by 1 plus one recorded allowance (`BC-07/visible`, rulings OD-06 and R7; not an introduced failure).

## PR value
Content PR: an uncontroversial factual fix; send it as its own PR, separate from the diagram. Diagram benefit: strong (text x1.54 at README width).
