authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Cells-FOSS-for-Go

Verdict: **PUSHABLE**  |  minor_major: **none**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Go  |  live head 99c789e9

## Edits
1. `at_a_glance_diagram` L46: redraw.
2. `second_h1` L105: `# Requires **Go 1.24.5+** ...` becomes `## Requires **Go 1.24.5+** ...`.
3. `unclosed_details` L529: inserts `</details>` immediately before `## Detailed Documentation`.

## Findings
- Edit 1 PASS: 12 labels, titles, 3 edges identical; order c1..c7; vertical 1351x1149 to horizontal 1194x685; 0 clipped.
- Edit 2 PASS: the live README had two H1s; now one H1. The maintainer's generated Navigation links to that heading's slug; `mech.py` no longer reports "in-page anchor not found". The sentence-as-heading remains (optional improvement, not required).
- Edit 3 PASS: `<details>` at L506 ("More Test and Example Commands") was never closed. markdown-it + html5lib render: before, H2 `Detailed Documentation`, `Constraints` and `License` were inside the collapsed details; after, all three are top level (heading depth 0). The inserted close is where the details content ends (after the docs/usage.md sentence, before the next H2). `go.mod`: module `.../v26`, `go 1.24.5`, no `require` block, so the README's "Go 1.24.5+, standard library only" is true.
- Validation: introduced 0; revealed 1 (BC-04: code span `v26` is not a fact value), a check that was not visible before and is not caused by the edits.
- Links 42/42, 0 broken, Navigation unchanged (27 items), no duplicate H2, no narration. The lane left 10 failing_example findings unapplied (reported, not edits).

## Verdict
PUSHABLE: three confined hunks, each a verified real defect or a faithful redraw.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1351x1149 to horizontal 1194x685; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Go` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-cells-foss__Aspose.Cells-FOSS-for-Go`). README.md sha256 `df33f25357cf1bc16d76da31f329e37d0f1c59ae1b7778ee4cdae8aa230306b0`.
- Fresh `git clone --depth 1` of the live head: `99c789e9` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 3 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; revealed: [{"check": "BC-04", "details": ["code span 'v26' is not a fact value"], "extra": 1}].
