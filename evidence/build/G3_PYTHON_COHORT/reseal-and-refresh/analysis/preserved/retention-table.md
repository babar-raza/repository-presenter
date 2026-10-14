authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Retention table: wave 7, wave 3 and the committed candidates against the live READMEs

Produced 2026-10-12 01:54 UTC by `python -X utf8 -m tools.idempotence report` (TC-IDM-01, `tools/idempotence/report.py`)
from the sealed bundles and pipeline drafts of `G:/rp-w7` (wave 7, bundles made at or after
2026-10-11T23:00Z), `G:/rp-w3` (wave 3, at or after 2026-10-11T05:00Z) and the 38 committed
`candidates/` of origin/main `7299f628`. Each candidate `README.md` is compared with the live README
at the same revision, recovered from the bundle's `README.patch` (reverse-applied and proven by
re-diffing; every row below says `live from = patch`). Wave 7 was still producing drafts when this was
run: re-run the commands at the foot for the final figures.

## How to read the columns

- **prose verbatim / kept**: of the live README's sentences and list items of at least four words, the
  share that appears in the candidate with the same words (case, emphasis, backticks and link syntax
  folded), and the share that appears in any form (verbatim, reworded: at least 60% of its content
  words in one candidate atom, or scattered: at least 85% over several). The second analysis's
  thresholds; "kept" is generous and "lost" can include an equivalent restatement.
- **lines kept**: of the live README's non-blank lines outside the Mermaid diagram, the share still a
  candidate line in the same order. The strict figure the live-first lane is gated to 100% on.
- **links / images / code / headings**: kept over live (distinct link and image targets; fenced code
  blocks kept verbatim or as a near-copy; headings by words).
- **introduced (llm)**: share of the candidate's prose atoms with no source in the live README (as a
  sentence or reworded) and none in the facts (85% of its content words in the facts' vocabulary); in
  brackets, the share that sits in an authored (model-written) content unit of the bundle.
- **hunks (runs)**: unified-diff hunks with three lines of context, as `README.patch` shows them, and
  separate runs of changed lines (the unit the second analysis called a hunk; median 42.5 over the
  committed 38 there, 42.5 here).
- Kind: `sealed` has a `manifest.json` (a sealed candidate); `draft` is a pipeline transaction that
  was not sealed. A row with prose `-` has no live README (Aspose.GIS.FOSS-for-.Net has none, so
  there is nothing to retain and everything it says is introduced).

Atoms are cut slightly differently from the analysis scripts (a list item is one atom here, a
sentence split there), so a figure can differ from `first-principles-2-idempotence.md` by a few
points; the committed 38 give 13% verbatim / 37% kept / 32% of lines here against 13.4% / 35.7% / 32%
there.

## Pooled

| set | bundles | live prose atoms | prose verbatim | prose kept (any form) | non-diagram lines kept | links | images | code | headings | introduced (in authored units) | median hunks | median runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| committed sealed (38, pre-wave baseline) | 38 | 2761 | 13% | 37% | 32% | 398/599 (66%) | 80/174 (46%) | 321/502 (64%) | 784/1262 (62%) | 36% (20%) | 8 | 42.5 |
| wave 3, sealed only | 8 | 595 | 27% | 55% | 40% | 87/117 (74%) | 23/36 (64%) | 105/112 (94%) | 161/254 (63%) | 50% (12%) | 11 | 53.5 |
| wave 3, sealed + drafts | 28 | 2054 | 26% | 52% | 35% | 318/416 (76%) | 65/120 (54%) | 292/359 (81%) | 579/934 (62%) | 34% (12%) | 9.5 | 44.5 |
| wave 7, sealed only | 8 | 617 | 41% | 72% | 39% | 134/152 (88%) | 23/39 (59%) | 109/122 (89%) | 224/354 (63%) | 23% (16%) | 14 | 54.5 |
| wave 7, sealed + drafts | 37 | 3278 | 43% | 74% | 32% | 419/514 (82%) | 78/150 (52%) | 332/548 (61%) | 753/1200 (63%) | 20% (15%) | 8 | 41 |

## Same repository and revision, committed vs wave 3 vs wave 7

Cells are prose verbatim % / prose kept % / non-diagram lines kept %, then (s) sealed or (d) draft.
`-` means that set holds no bundle for the revision. A committed bundle is the seal that is in
origin/main now, which for several repositories is a later seal than the one wave 3 started from.

| repository | rev | committed verbatim/kept/lines | wave 3 | wave 7 | wave 7 hunks (committed) |
|---|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | 52b0f00e | 15/50/19 (s) | 19/67/20 (s) | 19/71/22 (s) | 8 (7) |
| Aspose.3D-FOSS-for-Java | 3d2ed6be | 49/70/42 (s) | 24/52/51 (s) | 25/62/50 (s) | 12 (9) |
| Aspose.3D-FOSS-for-Python | 65b1f577 | 12/42/35 (s) | 33/62/35 (d) | 35/71/31 (d) | 11 (11) |
| Aspose.3D-FOSS-for-TypeScript | 66cb26df | - | 12/42/26 (s) | 34/70/28 (d) | 8 (-) |
| Aspose.Cells-FOSS-for-.NET | 941814fd | 49/74/56 (s) | 51/78/76 (s) | 46/72/79 (s) | 16 (14) |
| Aspose.Cells-FOSS-for-Cpp | 9f852d0f | 4/29/12 (s) | 46/68/18 (d) | 56/72/27 (d) | 4 (2) |
| Aspose.Cells-FOSS-for-Go | 99c789e9 | - | 19/72/61 (d) | 24/81/61 (s) | 11 (-) |
| Aspose.Cells-FOSS-for-Java | c65329e7 | 14/45/46 (s) | 16/61/33 (s) | 24/78/34 (d) | 9 (6) |
| Aspose.Cells-FOSS-for-Python | 952317ca | - | 15/79/40 (d) | 33/79/41 (d) | 5 (-) |
| Aspose.Cells-FOSS-for-Rust | 1a6004af | 6/43/16 (s) | 8/38/17 (d) | 28/70/9 (d) | 5 (7) |
| Aspose.Cells-FOSS-for-TypeScript | fc186507 | 23/57/34 (s) | 17/60/33 (d) | 20/54/30 (d) | 7 (8) |
| Aspose.Email-FOSS-for-.Net | 59125b47 | 7/35/38 (s) | 35/63/47 (d) | 42/72/54 (d) | 10 (7) |
| Aspose.JMAP-FOSS-for-.NET | 0d5cf17e | - | - | 41/74/38 (d) | 6 (-) |
| Aspose.JMAP-FOSS-for-Cpp | 559c9620 | - | - | 46/88/33 (d) | 6 (-) |
| Aspose.JMAP-FOSS-for-Go | 327dda39 | - | - | 35/73/31 (d) | 4 (-) |
| Aspose.JMAP-FOSS-for-Java | f0d6ba73 | - | - | 36/72/28 (d) | 4 (-) |
| Aspose.JMAP-FOSS-for-Node.js | 93f22fb5 | - | - | 38/62/49 (d) | 6 (-) |
| Aspose.JMAP-FOSS-for-Python | f2137fa6 | - | - | 42/74/35 (d) | 5 (-) |
| Aspose.JMAP-FOSS-for-Rust | d7286100 | - | - | 37/61/27 (d) | 5 (-) |
| Aspose.JMAP-FOSS-for-TypeScript | d8fdf9e8 | - | - | 46/78/41 (d) | 5 (-) |
| Aspose.GIS.FOSS-for-.Net | b9b8c9c7 | - | - | - | 1 (-) |
| Aspose.HTML-FOSS-for-Python | bf0f1e7a | 17/55/21 (s) | 30/64/24 (d) | 38/72/21 (d) | 7 (8) |
| Aspose.Imaging-FOSS-for-.NET | 6ebb2091 | - | 11/46/21 (d) | 32/75/34 (d) | 7 (-) |
| Aspose.Note-FOSS-for-Python | 0fd1cf7b | - | 52/75/59 (s) | 59/82/61 (s) | 17 (-) |
| Aspose.Page-FOSS-for-Python | 43cef367 | 16/43/27 (s) | 25/57/38 (d) | 36/72/47 (d) | 12 (8) |
| Aspose-PDF-FOSS-for-Go | cdf43df1 | - | 13/37/38 (d) | 32/53/49 (d) | 26 (-) |
| Aspose-PDF-FOSS-for-Python | 8f0edbe6 | - | - | 34/57/22 (d) | 17 (-) |
| Aspose.PDF-FOSS-for-.NET | 10a36383 | - | 26/42/29 (d) | 42/68/27 (s) | 26 (-) |
| Aspose.PDF-FOSS-for-Cpp | 4b83c9fe | - | - | 53/72/18 (d) | 10 (-) |
| Aspose.PDF-FOSS-for-Java | 736cedaa | - | 17/39/41 (d) | 51/82/45 (s) | 29 (-) |
| Aspose.PDF-FOSS-for-TypeScript | c672b391 | - | - | 52/89/16 (d) | 36 (-) |
| Aspose.PSD-FOSS-for-.NET | 85ed7eec | - | 3/17/29 (d) | 38/51/43 (d) | 7 (-) |
| Aspose.PSD-FOSS-for-Python | dbc90f46 | - | 22/46/19 (d) | 29/56/20 (d) | 5 (-) |
| Aspose.Slides-FOSS-for-.NET | 86c441b5 | 0/9/2 (s) | 18/29/30 (s) | 41/57/44 (d) | 14 (1) |
| Aspose.Slides-FOSS-for-Cpp | 469ce77a | - | 20/39/13 (d) | 43/60/13 (s) | 7 (-) |
| Aspose.Slides-FOSS-for-Java | 620a2614 | 20/29/54 (s) | 40/58/59 (d) | 51/67/65 (d) | 28 (25) |
| Aspose.Slides-FOSS-for-Python | 4e63447b | - | 12/41/32 (s) | 52/67/48 (d) | 18 (-) |
| Aspose.TeX-FOSS-for-Python | 181015d2 | - | - | 20/63/18 (d) | 4 (-) |


## Wave 7 (every bundle)

| repository | rev | kind | live from | prose verbatim | prose kept | lines kept | links | images | code | headings | introduced (llm) | hunks (runs) | +/- lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | 52b0f00e | sealed | patch | 19% | 71% | 22% | 11/12 | 3/4 | 10/11 | 19/25 | 25% (13%) | 8 (43) | +430/-453 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | 3d2ed6be | sealed | patch | 25% | 62% | 50% | 13/19 | 3/5 | 10/12 | 21/31 | 21% (17%) | 12 (99) | +268/-301 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 65b1f577 | draft | patch | 35% | 71% | 31% | 16/19 | 3/5 | 14/18 | 21/28 | 31% (26%) | 11 (66) | +434/-500 |
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | 66cb26df | draft | patch | 34% | 70% | 28% | 7/8 | 1/3 | 7/8 | 17/33 | 45% (37%) | 8 (28) | +228/-304 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | 941814fd | sealed | patch | 46% | 72% | 79% | 11/12 | 3/5 | 12/15 | 18/28 | 39% (19%) | 16 (64) | +202/-127 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | 9f852d0f | draft | patch | 56% | 72% | 27% | 10/12 | 2/5 | 5/14 | 14/22 | 30% (22%) | 4 (45) | +288/-400 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | 99c789e9 | sealed | patch | 24% | 81% | 61% | 11/12 | 3/5 | 14/16 | 17/27 | 28% (25%) | 11 (33) | +224/-201 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | c65329e7 | draft | patch | 24% | 78% | 34% | 11/13 | 3/5 | 8/9 | 18/20 | 35% (23%) | 9 (28) | +285/-328 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | 952317ca | draft | patch | 33% | 79% | 41% | 9/10 | 3/5 | 9/9 | 8/16 | 10% (8%) | 5 (21) | +593/-89 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | 1a6004af | draft | patch | 28% | 70% | 9% | 11/14 | 2/3 | 4/13 | 16/33 | 12% (5%) | 5 (8) | +689/-650 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | fc186507 | draft | patch | 20% | 54% | 30% | 9/10 | 2/3 | 5/6 | 16/18 | 54% (46%) | 7 (24) | +113/-210 |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | 59125b47 | draft | patch | 42% | 72% | 54% | 13/13 | 3/4 | 8/9 | 19/25 | 32% (26%) | 10 (44) | +119/-132 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-.NET | 0d5cf17e | draft | patch | 41% | 74% | 38% | 5/8 | 1/2 | 4/7 | 14/17 | 39% (18%) | 6 (27) | +233/-126 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Cpp | 559c9620 | draft | patch | 46% | 88% | 33% | 5/9 | 1/3 | 2/6 | 13/17 | 51% (40%) | 6 (15) | +161/-135 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Go | 327dda39 | draft | patch | 35% | 73% | 31% | 5/9 | 1/3 | 2/6 | 13/17 | 48% (40%) | 4 (23) | +142/-119 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Java | f0d6ba73 | draft | patch | 36% | 72% | 28% | 5/8 | 1/2 | 1/6 | 14/17 | 43% (32%) | 4 (16) | +134/-148 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js | 93f22fb5 | draft | patch | 38% | 62% | 49% | 3/8 | 1/2 | 5/6 | 15/17 | 43% (32%) | 6 (23) | +186/-92 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Python | f2137fa6 | draft | patch | 42% | 74% | 35% | 5/8 | 1/2 | 1/6 | 14/17 | 44% (33%) | 5 (31) | +176/-113 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Rust | d7286100 | draft | patch | 37% | 61% | 27% | 3/8 | 1/2 | 1/6 | 13/17 | 28% (18%) | 5 (25) | +237/-137 |
| aspose-email-foss/Aspose.JMAP-FOSS-for-TypeScript | d8fdf9e8 | draft | patch | 46% | 78% | 41% | 5/8 | 1/2 | 4/6 | 15/17 | 26% (20%) | 5 (28) | +239/-106 |
| aspose-gis-foss/Aspose.GIS.FOSS-for-.Net | b9b8c9c7 | draft | patch | - | - | - | - | - | - | - | 92% (58%) | 1 (1) | +165/-0 |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | bf0f1e7a | draft | patch | 38% | 72% | 21% | 13/13 | 2/3 | 11/12 | 28/41 | 30% (25%) | 7 (43) | +461/-435 |
| aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | 6ebb2091 | draft | patch | 32% | 75% | 34% | 10/10 | 2/4 | 6/8 | 15/20 | 30% (18%) | 7 (24) | +109/-190 |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | 0fd1cf7b | sealed | patch | 59% | 82% | 61% | 16/16 | 4/5 | 20/20 | 29/38 | 26% (21%) | 17 (45) | +229/-196 |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | 43cef367 | draft | patch | 36% | 72% | 47% | 8/11 | 3/8 | 12/14 | 27/36 | 21% (14%) | 12 (72) | +203/-297 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | cdf43df1 | draft | patch | 32% | 53% | 49% | 14/20 | 2/7 | 7/9 | 22/40 | 7% (5%) | 26 (83) | +358/-530 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | 8f0edbe6 | draft | patch | 34% | 57% | 22% | 16/17 | 2/4 | 16/24 | 26/49 | 9% (6%) | 17 (46) | +765/-915 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | 10a36383 | sealed | patch | 42% | 68% | 27% | 25/26 | 2/5 | 16/16 | 68/107 | 13% (7%) | 26 (113) | +1028/-1361 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | 4b83c9fe | draft | patch | 53% | 72% | 18% | 17/22 | 1/5 | 11/18 | 29/50 | 33% (27%) | 10 (47) | +466/-727 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | 736cedaa | sealed | patch | 51% | 82% | 45% | 32/34 | 2/5 | 13/14 | 34/61 | 24% (20%) | 29 (146) | +964/-920 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | c672b391 | draft | patch | 52% | 89% | 16% | 11/14 | 2/4 | 18/123 | 28/91 | 2% (2%) | 36 (157) | +1228/-3769 |
| aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | 85ed7eec | draft | patch | 38% | 51% | 43% | 10/10 | 1/3 | 5/6 | 14/22 | 30% (25%) | 7 (41) | +107/-218 |
| aspose-psd-foss/Aspose.PSD-FOSS-for-Python | dbc90f46 | draft | patch | 29% | 56% | 20% | 7/7 | 1/3 | 5/7 | 12/27 | 15% (12%) | 5 (32) | +226/-348 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | 86c441b5 | draft | patch | 41% | 57% | 44% | 12/18 | 3/4 | 14/18 | 8/27 | 40% (26%) | 14 (59) | +440/-278 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | 469ce77a | sealed | patch | 43% | 60% | 13% | 15/21 | 3/5 | 14/18 | 18/37 | 13% (10%) | 7 (22) | +494/-752 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | 620a2614 | draft | patch | 51% | 67% | 65% | 22/27 | 3/6 | 16/18 | 29/32 | 16% (13%) | 28 (86) | +267/-287 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | 4e63447b | draft | patch | 52% | 67% | 48% | 15/19 | 3/5 | 17/19 | 33/52 | 15% (13%) | 18 (97) | +706/-518 |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | 181015d2 | draft | patch | 20% | 63% | 18% | 8/9 | 3/4 | 5/15 | 18/28 | 32% (28%) | 4 (13) | +126/-296 |

Pooled over 38 bundles: live prose 3278 atoms, 43% verbatim, 74% kept in any form; live non-diagram lines kept 32%; candidate prose 4656 atoms, 21% introduced (15% in authored units); unified-diff hunks median 7.5 (min 1, max 36), separate runs of changed lines median 37.


## Wave 3 (every bundle)

| repository | rev | kind | live from | prose verbatim | prose kept | lines kept | links | images | code | headings | introduced (llm) | hunks (runs) | +/- lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | 52b0f00e | sealed | patch | 19% | 67% | 20% | 12/12 | 3/4 | 11/11 | 19/25 | 40% (10%) | 7 (34) | +482/-452 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | 3d2ed6be | sealed | patch | 24% | 52% | 51% | 11/19 | 3/5 | 11/12 | 21/31 | 18% (12%) | 12 (93) | +209/-290 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 65b1f577 | draft | patch | 33% | 62% | 35% | 16/19 | 3/5 | 15/18 | 19/28 | 20% (18%) | 13 (60) | +443/-461 |
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | 66cb26df | sealed | patch | 12% | 42% | 26% | 7/8 | 1/3 | 8/8 | 18/33 | 93% (7%) | 7 (24) | +531/-302 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | 941814fd | sealed | patch | 51% | 78% | 76% | 11/12 | 3/5 | 13/15 | 18/28 | 34% (11%) | 16 (59) | +261/-136 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | 9f852d0f | draft | patch | 46% | 68% | 18% | 8/12 | 2/5 | 3/14 | 13/22 | 73% (10%) | 4 (44) | +501/-448 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | 99c789e9 | draft | patch | 19% | 72% | 61% | 10/12 | 3/5 | 15/16 | 19/27 | 45% (15%) | 11 (32) | +222/-197 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | c65329e7 | sealed | patch | 16% | 61% | 33% | 11/13 | 3/5 | 8/9 | 18/20 | 42% (29%) | 9 (27) | +258/-327 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | 952317ca | draft | patch | 15% | 79% | 40% | 8/10 | 3/5 | 9/9 | 8/16 | 9% (8%) | 6 (27) | +626/-83 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | 1a6004af | draft | patch | 8% | 38% | 17% | 10/14 | 2/3 | 5/13 | 17/33 | 11% (5%) | 7 (40) | +681/-549 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | fc186507 | draft | patch | 17% | 60% | 33% | 9/10 | 2/3 | 5/6 | 17/18 | 85% (11%) | 7 (23) | +376/-199 |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | 59125b47 | draft | patch | 35% | 63% | 47% | 11/13 | 3/4 | 8/9 | 21/25 | 28% (21%) | 8 (41) | +121/-153 |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | c844a467 | draft | patch | 51% | 82% | 37% | 10/15 | 2/3 | 5/9 | 17/27 | 19% (15%) | 11 (45) | +109/-281 |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | adf4885a | draft | patch | 10% | 12% | 29% | 2/3 | 0/1 | 17/22 | 4/29 | 24% (13%) | 11 (42) | +539/-375 |
| aspose-gis-foss/Aspose.GIS.FOSS-for-.Net | b9b8c9c7 | draft | patch | - | - | - | - | - | - | - | 100% (72%) | 1 (1) | +170/-0 |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | bf0f1e7a | draft | patch | 30% | 64% | 24% | 13/13 | 2/3 | 12/12 | 31/41 | 33% (28%) | 9 (59) | +405/-388 |
| aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | 6ebb2091 | draft | patch | 11% | 46% | 21% | 10/10 | 2/4 | 6/8 | 15/20 | 38% (24%) | 5 (25) | +61/-212 |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | 0fd1cf7b | sealed | patch | 52% | 75% | 59% | 13/16 | 4/5 | 20/20 | 27/38 | 31% (17%) | 18 (49) | +194/-190 |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | 43cef367 | draft | patch | 25% | 57% | 38% | 8/11 | 3/8 | 11/14 | 26/36 | 37% (29%) | 8 (65) | +216/-337 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | cdf43df1 | draft | patch | 13% | 37% | 38% | 12/20 | 2/7 | 7/9 | 21/40 | 13% (11%) | 21 (86) | +384/-614 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | 10a36383 | draft | patch | 26% | 42% | 29% | 25/26 | 2/5 | 15/16 | 69/107 | 13% (5%) | 27 (116) | +983/-1326 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | 736cedaa | draft | patch | 17% | 39% | 41% | 31/34 | 2/5 | 13/14 | 38/61 | 34% (29%) | 24 (134) | +900/-968 |
| aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | 85ed7eec | draft | patch | 3% | 17% | 29% | 7/10 | 1/3 | 4/6 | 14/22 | 65% (56%) | 5 (31) | +85/-270 |
| aspose-psd-foss/Aspose.PSD-FOSS-for-Python | dbc90f46 | draft | patch | 22% | 46% | 19% | 7/7 | 1/3 | 5/7 | 12/27 | 16% (13%) | 4 (32) | +241/-353 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | 86c441b5 | sealed | patch | 18% | 29% | 30% | 6/18 | 3/4 | 16/18 | 8/27 | 58% (39%) | 10 (58) | +408/-325 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | 469ce77a | draft | patch | 20% | 39% | 13% | 14/21 | 3/5 | 12/18 | 18/37 | 27% (21%) | 6 (33) | +345/-735 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | 620a2614 | draft | patch | 40% | 58% | 59% | 12/27 | 3/6 | 17/18 | 25/32 | 12% (7%) | 24 (71) | +196/-331 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | 4e63447b | sealed | patch | 12% | 41% | 32% | 16/19 | 3/5 | 18/19 | 32/52 | 11% (10%) | 14 (76) | +732/-638 |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET | 0d3f1add | draft | patch | 47% | 63% | 44% | 8/12 | 1/1 | 3/9 | 14/32 | 11% (4%) | 11 (110) | +805/-545 |

Pooled over 29 bundles: live prose 2054 atoms, 26% verbatim, 52% kept in any form; live non-diagram lines kept 35%; candidate prose 4577 atoms, 34% introduced (12% in authored units); unified-diff hunks median 9 (min 1, max 27), separate runs of changed lines median 44.


## Committed candidates, origin/main 7299f628 (the baseline)

| repository | rev | kind | live from | prose verbatim | prose kept | lines kept | links | images | code | headings | introduced (llm) | hunks (runs) | +/- lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | 52b0f00e | sealed | patch | 15% | 50% | 19% | 12/12 | 3/4 | 10/11 | 18/25 | 43% (30%) | 7 (35) | +403/-464 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | 3d2ed6be | sealed | patch | 49% | 70% | 42% | 17/19 | 2/5 | 3/12 | 17/31 | 22% (19%) | 9 (93) | +201/-358 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | e308de58 | sealed | patch | 10% | 42% | 30% | 16/21 | 2/5 | 13/14 | 19/30 | 54% (43%) | 11 (30) | +366/-288 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 65b1f577 | sealed | patch | 12% | 42% | 35% | 10/19 | 4/5 | 15/18 | 23/28 | 27% (26%) | 11 (60) | +446/-465 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | d9f3bfe5 | sealed | patch | 64% | 78% | 60% | 6/8 | 2/3 | 7/11 | 10/24 | 19% (18%) | 12 (32) | +61/-190 |
| aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | 06eca5c0 | sealed | patch | 17% | 61% | 40% | 9/10 | 2/3 | 9/9 | 17/19 | 62% (49%) | 8 (25) | +138/-129 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | 941814fd | sealed | patch | 49% | 74% | 56% | 10/12 | 3/5 | 8/15 | 15/28 | 32% (13%) | 14 (40) | +252/-240 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | 9f852d0f | sealed | patch | 4% | 29% | 12% | 8/12 | 2/5 | 3/14 | 13/22 | 82% (12%) | 2 (32) | +495/-482 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | 9f0a4033 | sealed | patch | 19% | 58% | 61% | 9/12 | 3/5 | 14/16 | 15/21 | 69% (39%) | 12 (36) | +138/-181 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | fa4e890e | sealed | patch | 27% | 76% | 61% | 10/12 | 3/5 | 14/16 | 18/24 | 59% (20%) | 13 (37) | +195/-180 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | 779c9640 | sealed | patch | 20% | 55% | 46% | 11/13 | 2/5 | 4/9 | 14/16 | 52% (43%) | 5 (73) | +181/-258 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | c65329e7 | sealed | patch | 14% | 45% | 46% | 10/13 | 2/5 | 4/9 | 18/20 | 64% (57%) | 6 (72) | +169/-270 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | 4f6768a7 | sealed | patch | 19% | 56% | 49% | 10/11 | 3/5 | 9/9 | 20/21 | 11% (10%) | 10 (44) | +374/-178 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | 1a6004af | sealed | patch | 6% | 43% | 16% | 11/14 | 2/3 | 6/13 | 17/33 | 8% (7%) | 7 (41) | +728/-551 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | fc186507 | sealed | patch | 23% | 57% | 34% | 9/10 | 2/3 | 5/6 | 17/18 | 85% (12%) | 8 (25) | +353/-192 |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | 59125b47 | sealed | patch | 7% | 35% | 38% | 11/13 | 3/4 | 7/9 | 20/25 | 56% (47%) | 7 (34) | +95/-172 |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | c844a467 | sealed | patch | 7% | 36% | 17% | 9/15 | 2/3 | 4/9 | 17/27 | 43% (35%) | 6 (35) | +79/-355 |
| aspose-email-foss/Aspose.Email-FOSS-for-Python | 10a906b4 | sealed | patch | 6% | 52% | 33% | 12/19 | 3/6 | 7/10 | 21/29 | 35% (27%) | 8 (42) | +180/-232 |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | c520e3eb | sealed | patch | 7% | 9% | 37% | 1/2 | 0/5 | 9/20 | 7/20 | 32% (20%) | 4 (31) | +493/-288 |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | bf0f1e7a | sealed | patch | 17% | 55% | 21% | 10/13 | 2/3 | 9/12 | 31/41 | 43% (36%) | 8 (59) | +389/-404 |
| aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | a7c7314b | sealed | patch | 0% | 18% | 6% | 2/4 | 1/3 | 0/2 | 3/7 | 87% (52%) | 1 (15) | +100/-73 |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | 41de2e8a | sealed | patch | 8% | 35% | 34% | 10/16 | 3/5 | 16/20 | 29/38 | 43% (26%) | 13 (55) | +225/-281 |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | 43cef367 | sealed | patch | 16% | 43% | 27% | 9/11 | 4/8 | 10/14 | 25/36 | 55% (47%) | 8 (39) | +244/-392 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | 286484d2 | sealed | patch | 6% | 21% | 33% | 10/19 | 2/7 | 7/9 | 21/40 | 12% (11%) | 16 (94) | +429/-635 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | 6784921e | sealed | patch | 4% | 23% | 36% | 10/19 | 2/7 | 7/9 | 19/40 | 13% (11%) | 16 (84) | +371/-591 |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | 580935ba | sealed | patch | 17% | 41% | 16% | 11/17 | 2/4 | 11/18 | 26/44 | 18% (13%) | 11 (38) | +590/-769 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | d10e2c82 | sealed | patch | 9% | 43% | 27% | 25/27 | 3/4 | 15/17 | 66/108 | 21% (10%) | 24 (111) | +977/-1270 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | 888700a8 | sealed | patch | 6% | 30% | 13% | 10/19 | 1/5 | 5/16 | 29/46 | 81% (26%) | 7 (44) | +413/-731 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | 099e70a8 | sealed | patch | 7% | 41% | 38% | 8/23 | 1/5 | 11/14 | 36/60 | 34% (29%) | 25 (115) | +832/-1015 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | 5a49de5d | sealed | patch | 11% | 25% | 36% | 8/34 | 1/5 | 10/14 | 35/61 | 32% (27%) | 22 (123) | +849/-1054 |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | db2d3f06 | sealed | patch | 11% | 33% | 37% | 30/34 | 1/5 | 10/14 | 34/61 | 50% (47%) | 24 (119) | +844/-1032 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | 86c441b5 | sealed | patch | 0% | 9% | 2% | 9/18 | 2/4 | 4/18 | 5/27 | 90% (62%) | 1 (43) | +345/-484 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | c41f8ddd | sealed | patch | 3% | 10% | 9% | 11/21 | 2/5 | 8/18 | 18/37 | 76% (66%) | 4 (36) | +291/-752 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | 620a2614 | sealed | patch | 20% | 29% | 54% | 11/27 | 1/6 | 16/18 | 29/32 | 43% (36%) | 25 (61) | +169/-371 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | a03b119a | sealed | patch | 0% | 9% | 30% | 8/17 | 1/4 | 9/14 | 10/26 | 87% (59%) | 9 (45) | +365/-314 |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | becd199a | sealed | patch | 14% | 29% | 29% | 9/10 | 2/4 | 17/18 | 16/23 | 21% (14%) | 6 (37) | +942/-288 |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET | 0d3f1add | sealed | patch | 3% | 17% | 39% | 8/12 | 1/1 | 1/9 | 13/32 | 24% (13%) | 8 (94) | +531/-589 |
| aspose-words-foss/Aspose.Words-FOSS-for-Python | 2d2efee2 | sealed | patch | 8% | 32% | 17% | 8/11 | 3/5 | 4/18 | 23/42 | 39% (34%) | 4 (59) | +250/-513 |

Pooled over 38 bundles: live prose 2761 atoms, 13% verbatim, 37% kept in any form; live non-diagram lines kept 32%; candidate prose 4585 atoms, 36% introduced (20% in authored units); unified-diff hunks median 8 (min 1, max 25), separate runs of changed lines median 42.5.


## Reproduce

```
export PYTHONPATH=$PWD/src:$PWD
python -X utf8 -m tools.idempotence report /g/rp-w7/* --since 2026-10-11T23:00:00Z --out w7.md --json w7.json
python -X utf8 -m tools.idempotence report /g/rp-w3/* --since 2026-10-11T05:00:00Z --out w3.md --json w3.json
python -X utf8 -m tools.idempotence report candidates --out committed.md --json committed.json
```

`--json` keeps, for every bundle, each lost atom with its line and section, so a review can open the
live README at the line.
