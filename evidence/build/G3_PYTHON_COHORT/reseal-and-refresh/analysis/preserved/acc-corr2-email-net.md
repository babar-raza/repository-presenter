authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Email-FOSS-for-.Net

Verdict: **PUSHABLE**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-email-foss/Aspose.Email-FOSS-for-.Net  |  live head 59125b47

## Edits
1. `at_a_glance_diagram` L31: redraw. Nothing else.

## Findings
- 9 labels, 3 group titles, 3 edges identical; four capabilities stay in one column (c1..c4 in order); vertical 1276x703 to horizontal 917x499; 0 clipped (5 fonts x 4 releases).
- Links 27/27, 0 broken, Navigation consistent, no narration, the lane left 0 unapplied findings.

## Verdict
PUSHABLE.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1276x703 to horizontal 917x499; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-email-foss__Aspose.Email-FOSS-for-.Net` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-email-foss__Aspose.Email-FOSS-for-.Net`). README.md sha256 `6bd789aa5a5a1a4d951b763b261caaf1b322013eefb8c1eed27f814d9abebd1d`.
- Fresh `git clone --depth 1` of the live head: `59125b47` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
