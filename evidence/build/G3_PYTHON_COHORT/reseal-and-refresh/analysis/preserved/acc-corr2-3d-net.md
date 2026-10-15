authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.3D-FOSS-for-.NET

Verdict: **PUSHABLE (diagram only; inherited false claims remain, see finding)**  |  minor_major: **none for the patch; MAJOR inherited defect outside it**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-3d-foss/Aspose.3D-FOSS-for-.NET  |  live head 52b0f00e

## Edits
1. `at_a_glance_diagram` L31: Mermaid body redrawn (flowchart TD to LR). Nothing else.

## Findings
- Patch itself: faithful. 14 node labels, 5 group titles and the 3 visible edges are identical before and after (whitespace-normalised, `<br/>` ignored); rendered text of all 193 node/cluster labels across my 13 diagrams equals the source text (no truncation). Reading order c1..c6 is preserved (left column c1-c3, right column c4-c6). Before: vertical 1219x1026; after: horizontal 1106x535, Starting Points | product | Core Capabilities (two columns) | Outputs; no label wider than its box in any of 5 fonts x 4 mermaid releases.
- INHERITED, not introduced, NOT FIXED (MAJOR for the owner to know, outside this patch): the diagram carries verified-false capability labels. `src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/IOService.cs` L56-88: importer and exporter dispatch is only OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS; the default arm throws `NotSupportedException`. The diagram still says U3D (Starting Points i1 and Outputs o1), RVM (i3, o3) and AMF/HTML5 (o4). The redraw re-states these nodes unchanged, so the PR improves layout but does not make the README truer. Needs a registered-format fact kind (the lane already lists this).
- Unapplied findings reported by the lane (not edits): report_gaps, claim_publication L104, failing_example L165.
- Cosmetic (minor, universal): the two capability columns are top-misaligned and the vertical gap between boxes (about 75 css px) is far larger than the configured `rankSpacing` 26; harmless, makes the diagram taller than needed.

## Verdict
PUSHABLE as a diagram-only PR: strictly better layout, equal content, confined. The owner may prefer to hold it until the false format labels are corrected, because the PR touches exactly those lines.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1219x1026 (before) to horizontal 1106x535 (after); 0 bad nodes in all 20 font/release combinations.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-3d-foss__Aspose.3D-FOSS-for-.NET` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-3d-foss__Aspose.3D-FOSS-for-.NET`). README.md sha256 `b9aabc33bcfc983d8976fbe44bcd0b900c4ddc734465dcd960ab63a2b868d85b`.
- Fresh `git clone --depth 1` of the live head: `52b0f00e` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
