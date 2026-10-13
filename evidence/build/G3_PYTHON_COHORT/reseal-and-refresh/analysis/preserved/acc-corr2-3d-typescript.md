authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.3D-FOSS-for-TypeScript

Verdict: **PUSHABLE**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript  |  live head 66cb26df

## Edits
1. `at_a_glance_diagram` L31: redraw. Nothing else.

## Findings
- 13 labels, 5 group titles, 3 edges identical; order c1..c6 preserved; vertical 1041x1050 to horizontal 1134x535; boxes grow with text; 0 clipped (5 fonts x 4 releases).
- Links 20/20 unchanged, 0 broken, Navigation consistent, no narration, no new text outside the Mermaid body.
- Lane left 1 report_gaps finding unapplied (not an edit).
- Cosmetic (minor, universal): wide empty vertical gaps between capability boxes; columns not top-aligned.

## Verdict
PUSHABLE. Content unchanged, layout better than live, confined.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1041x1050 to horizontal 1134x535; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript`). README.md sha256 `9db5b4359f5d3924841532990cd0d2ba6fd8ad26c05f4f6b79334c95fa53a53b`.
- Fresh `git clone --depth 1` of the live head: `66cb26df` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
