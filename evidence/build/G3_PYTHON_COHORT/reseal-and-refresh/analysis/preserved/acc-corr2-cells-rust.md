authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Cells-FOSS-for-Rust

Verdict: **FIX_REQUIRED**  |  minor_major: **MINOR**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Rust  |  live head 1a6004af

## Edits
1. `at_a_glance_diagram` L35: redraw. Nothing else.

## Findings
- Structure PASS: 13 labels, titles, 3 edges identical except one label's encoding; order c1..c10 (left c1-c5, right c6-c10); vertical 1637x1002 to horizontal 1064x800; 0 clipped on 4 mermaid releases.
- DEFECT (minor, introduced, version-dependent): the output node was `.xlsx workbook (file path, binary stream, or in-memory Vec<u8>)`; the redraw writes it as `Vec#lt;u8#gt;`. Rendered with htmlLabels off: mermaid 11.17.2 and 12.1.0 show `Vec<u8>` (an improvement: the live diagram drops `<u8>` and shows "in-memory Vec)"), but mermaid 11.4.1 and 11.12.0 draw the literal text `Vec&lt;u8&gt;` in the box (I rendered it: `scratchpad/acccorr2/vtest/png114/rust_lt.png`; the numeric form `#60;`/`#62;` fails the same way). The Mermaid release bundled by github.com is unknown to me, so on hosted READMEs this label may show visible entity text, worse than live. The lane's render verdict used only the default package (11.17.2).
- Inherited, not edited (advisory): README L106 "Once the repository is live at its real GitHub location" is stale; crates.io `aspose-cells-foss-rust` returns 404, so "not yet published to crates.io" is true; Cargo.toml name `aspose-cells-foss-rust`, version 26.7.0. `claim_public_types` (213 stated vs 115 verified) is also reported.
- Links 33/33, 0 broken, Navigation consistent.

## Fix
Replace the entity with plain wording that renders on every release (for example `in-memory byte vector` or `in-memory Vec`), and add an entity-literal check across all mermaid releases to the render gate.

## Verdict
FIX_REQUIRED, MINOR.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1637x1002 to horizontal 1064x800; 0 clipped; literal entity text in 11.4.1 and 11.12.0 for node o1 (see finding).

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust`). README.md sha256 `347e95af41b3c2b922b73721f7034943657ffba8105c7837ed207bea4dc4bcd2`.
- Fresh `git clone --depth 1` of the live head: `1a6004af` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 1 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
