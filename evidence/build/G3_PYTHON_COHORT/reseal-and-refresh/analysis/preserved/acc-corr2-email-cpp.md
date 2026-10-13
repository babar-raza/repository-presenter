authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Email-FOSS-for-Cpp

Verdict: **PUSHABLE (owner acknowledgement of the BC-07 allowance)**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-email-foss/Aspose.Email-FOSS-for-Cpp  |  live head c844a467

## Edits
1. `at_a_glance_diagram` L31: redraw. Nothing else. (The owner table I was given says this repo is `no_detector_fired` / not redrawn because of the BC-07 visible budget; the lane's regenerated bundle, code `e576d7ce`, now redraws it.)

## Findings
- 12 labels, titles, 3 edges identical; five capabilities in one column, order c1..c5; the live diagram is a vertical stack with HTML labels (I rendered it: 18 node/font clippings on mermaid 11.17.2 and 15 on 12.1.0 across the stress fonts); after: 929x607 horizontal, 0 clipped on all four releases.
- Policy note (not a content defect): redrawing adds the init line and invisible column links, so the README goes from 299 visible lines (lane's figure for the live file) to 303 against BC-07's 300-line budget. `validation_delta.json` records it under `allowed` (BC-07/visible, rulings OD-06 and R7); `introduced` is empty. I confirmed both rulings exist: `docs/DECISION_LOG.md` L5867 (OD-06: visible length may not grow except to add a required element) and L5868 (R7: horizontal, non-clipped At a Glance). Whether a visible-length budget overrun is acceptable for a required element is the owner's call; the allowance is narrowly worded (only what the redraw adds).
- Links 34/34, 0 broken, Navigation consistent, no other text changed. The lane left 2 failing_example findings unapplied (reported).

## Verdict
PUSHABLE, provided the owner accepts the recorded BC-07/visible allowance.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1569x703 to horizontal 929x607; 0 bad nodes on all four releases.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-email-foss__Aspose.Email-FOSS-for-Cpp` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-email-foss__Aspose.Email-FOSS-for-Cpp`). README.md sha256 `8e1440182490acc4abb8f548cd5da87e8b9d6bdc3c62b4dc4d0c8f0af3cd7c71`.
- Fresh `git clone --depth 1` of the live head: `c844a467` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; allowed: BC-07/visible 303 visible lines of 479 exceed the visible budget 300 (OD-06, R7).
