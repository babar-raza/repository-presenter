authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.3D-FOSS-for-Java

Verdict: **FIX_REQUIRED**  |  minor_major: **MINOR**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-3d-foss/Aspose.3D-FOSS-for-Java  |  live head 3d2ed6be

## Edits
1. `at_a_glance_diagram` L33: redraw (verified, see below).
2. `add_install_forms` L102: appends a `mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0` block at the end of Installation.
3. `add_dev_commands` L626: appends "To build from a clone, run:" + `mvn package` after the closing `</details>` of Development and Testing.

## Findings
- Edit 1 PASS: 9 labels, titles and 3 edges identical; order c1..c6 preserved; vertical 1015x1002 to horizontal 1074x535; no clipping, 4 mermaid releases.
- Edit 2 TRUE but REDUNDANT (minor, introduced). Maven Central: `maven-metadata.xml` latest = release = 26.5.0 and `.../26.5.0/aspose-3d-foss-26.5.0.pom` returns 200 (curl GET). But the README already gives the same coordinates three ways (Maven XML L82-88, Gradle Kotlin L92-94, Gradle Groovy L98-100, prose L77 "published to Maven Central as `org.aspose:aspose-3d-foss`"). The detector only counted `bash` fences, so a fourth form is added that no visitor lacks.
- Edit 3 REDUNDANT and MISPLACED (minor, introduced). The same section already shows `mvn clean package` and `mvn test` (L616-617). `mvn package` adds nothing, and it lands after the `<details>` block at the very end of the section, detached from the real commands. Not "verified missing"; it violates the owner's "change only what is false or missing".
- Links/anchors: 37 links before and after, 0 broken, Navigation (11 items) unchanged and consistent, no duplicate H2, no unclosed details. No narration in inserted prose.

## Fix
Drop edits 2 and 3 (keep edit 1). Lane-side cause: the detectors compare the exact fact string (`mvn package`) and the fence language, not equivalent commands already present.

## Verdict
FIX_REQUIRED, MINOR (cheap and local: drop two edits).
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1015x1002 to horizontal 1074x535; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-3d-foss__Aspose.3D-FOSS-for-Java` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-3d-foss__Aspose.3D-FOSS-for-Java`). README.md sha256 `1833f25f7b85592232c562907634823281cc7637e446387893dd4e8cc8e23013`.
- Fresh `git clone --depth 1` of the live head: `3d2ed6be` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 3 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
