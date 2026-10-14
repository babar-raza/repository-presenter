authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Cells-FOSS-for-Java

Verdict: **FIX_REQUIRED**  |  minor_major: **MINOR**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Java  |  live head c65329e7

## Edits
1. `at_a_glance_diagram` L33: redraw (15 capabilities).
2. `add_install_forms` L130: appends `mvn dependency:get -Dartifact=org.aspose:aspose-cells-foss:26.7.0` after the Installation text.
3. `add_dev_commands` L532: appends "To build from a clone, run:" + `mvn package` after the release paragraph.

## Findings
- Edit 1 PASS: 18 labels, titles, 3 edges identical; order c1..c15 (left c1-c8, right c9-c15); live render 2438x1064, after 1133x1269, horizontal at block level, 0 clipped. It is tall (about 1.1:1) because the maintainers' own diagram has 15 capabilities (above the 8-label content ceiling the lane documents as kept); text scales to roughly 78% in a README column.
- Edit 2 TRUE but REDUNDANT (minor, introduced): Maven Central latest = release = 26.7.0 (`maven-metadata.xml`), pom `26.7.0` returns 200; but the README already shows the same coordinates as Maven XML (around L120-126) and Gradle Groovy.
- Edit 3 REDUNDANT and MISPLACED (minor, introduced): the section already lists `mvn test`, `mvn compile`, `mvn clean package` and `mvn javadoc:javadoc` (L529-537); `mvn package` is a strict subset of `mvn clean package` and is appended after the Releases paragraph.
- Links 28/28, 0 broken, Navigation unchanged and consistent, no narration.

## Fix
Drop edits 2 and 3.

## Verdict
FIX_REQUIRED, MINOR.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- before 2438x1064 to after 1133x1269; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Java` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-cells-foss__Aspose.Cells-FOSS-for-Java`). README.md sha256 `25b3e552da7b450e6402c5de76ee111895f0d053cd6b36d3c8e970cfd0c1f1ba`.
- Fresh `git clone --depth 1` of the live head: `c65329e7` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 3 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
