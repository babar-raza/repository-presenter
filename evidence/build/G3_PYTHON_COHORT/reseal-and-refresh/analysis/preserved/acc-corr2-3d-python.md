authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.3D-FOSS-for-Python

Verdict: **FIX_REQUIRED**  |  minor_major: **MINOR**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-3d-foss/Aspose.3D-FOSS-for-Python  |  live head 65b1f577

## Edits
1. `at_a_glance_diagram` L29: redraw.
2. `add_dev_commands` L788: appends "To build from a clone, run:" + `python -m build` after the Releases paragraph at the end of Development and Testing.

## Findings
- Edit 1 PASS: 11 labels, titles, 3 edges identical; order c1..c8 preserved (left c1-c4, right c5-c8); vertical 1345x997 to horizontal 1100x685; 0 clipping.
- Edit 2 TRUE in CI, WRONG as printed (minor, introduced). `.github/workflows/publish.yml` L21-22 runs `python -m pip install --upgrade pip build` then `python -m build`, so the command is CI-backed, and in a throw-away copy of the clone I installed `build` and got `aspose_3d_foss-26.1.0-py3-none-any.whl` and the sdist. But the README line says only `python -m build`; in a clean venv without the `build` package it prints `No module named build` (reproduced with `python -I -m build`). A documented command that fails on a clean environment. It is also placed after the release-process paragraph rather than beside the install/test commands (L773-781).
- Links/anchors: 34 links, 0 broken, Navigation unchanged and consistent, no duplicate sections.
- Unapplied (inherited, reported by the lane): failing_example L274, claim_public_types L712, report_gaps.

## Fix
Either drop edit 2 or precede it with `python -m pip install build` (and place it in the build/test block). Lane cause: the extractor takes the CI command but not its install precondition (`pip install build`).

## Verdict
FIX_REQUIRED, MINOR.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1345x997 to horizontal 1100x685; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-3d-foss__Aspose.3D-FOSS-for-Python` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-3d-foss__Aspose.3D-FOSS-for-Python`). README.md sha256 `e547949e14596ca8bd33b966dde556d130f43e31ec28ac9507b86bee7d67e754`.
- Fresh `git clone --depth 1` of the live head: `65b1f577` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 2 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
