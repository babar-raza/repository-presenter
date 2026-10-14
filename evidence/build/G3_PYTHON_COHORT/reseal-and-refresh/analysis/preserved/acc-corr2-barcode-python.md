authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.BarCode-FOSS-for-Python

Verdict: **PUSHABLE**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python  |  live head 06eca5c0

## Edits
1. `at_a_glance_diagram` L31: redraw. Nothing else.

## Findings
- 8 labels, the 2 group titles and the 2 visible edges (product to Core Capabilities, Core to Outputs) are identical; the live diagram has no Starting Points block and none was invented. Five capabilities stay in one column (one column up to five). Order c1..c5 preserved. Live render was 1586x500 (wide row inside a vertical stack); after 675x624, product | Core | Outputs left to right. 0 clipped.
- Links 22/22, 0 broken, Navigation consistent, no other text changed. Lane found 0 unapplied findings.

## Verdict
PUSHABLE.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- before 1586x500 (vertical stack of blocks) to after 675x624 horizontal; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python`). README.md sha256 `a4181f1abe8644a6a3fbcd3df3c73330ff7648cd673f62f2d3c0f3d52339fd6b`.
- Fresh `git clone --depth 1` of the live head: `06eca5c0` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
