authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Mermaid At a Glance: clipped text and vertical blocks (lane L-mmd, 2026-10-11)

Owner report: text is clipped in the smaller boxes of some live At a Glance diagrams, and the
Starting Points, Core and Outputs "mother blocks" may be vertical; they should be horizontal, split
by key capability even under Core, with boxes that grow with their text, permanently.

## 1. Answer

* **Both defects are real and are in all 32 live diagrams.** Every live diagram is `flowchart TD`, so
  the three blocks are stacked (32 of 32 vertical), and every one clips as soon as the browser draws
  its labels in a font wider than the one that measured them (32 of 32 clip in at least three of five
  stress fonts; 4 to 16 labels each in the worst font).
* **Cause of vertical blocks:** `flowchart TD` plus the one chain edge between the three subgraphs,
  and `direction` lines that do the opposite of what their author meant: over unlinked nodes
  `direction TB` lays them in a *row* and `direction LR` in a *column* (dagre puts unlinked nodes on
  one rank). The generator wrote `TB` for "a column" and `LR` for "side by side", so every group
  is drawn at right angles to its intent.
* **Cause of clipping:** Mermaid's default HTML labels are `foreignObject` boxes whose size is
  measured once, in the font present at render time, with zero slack; a wider font afterwards makes
  the text overflow the box and the browser clips it. Labels longer than Mermaid's 200 px wrap width
  are re-wrapped by the browser at draw time, so the extra line is clipped vertically.
  GitHub's own page shows it: the aspose.org commit `ee05c1b` records "Outputs and accessible c..."
  and "Keyframe an..." cut off on the live page (title and a node, exactly the zero-slack
  `foreignObject` signature). That commit changed the topology only; the form it produced clips 32
  of 32 here.
* **Fix (deterministic, permanent):** `components/readme_diagram` draws the same content with
  `flowchart LR`, three blocks left to right, each multi-node group a pinned top-to-bottom column,
  two capability columns side by side, SVG text labels (`htmlLabels: false`, which has no clip box
  and grows the node with the text) wrapped into `<br/>` lines by a character-width model whose
  envelope covers five fonts. Verified by rendering: **vertical 32 -> 0, clipped under font swap
  32 -> 0**, on Mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0, every label and group title preserved.

## 2. Method and tools (nothing outside D:\tools\mermaid and the scratchpad was written)

* Corpus: the 35 live clones in `scratchpad\survey-live`; 32 carry a Mermaid fence (`Aspose.PDF-FOSS
  for .NET` uses a PNG, `Aspose.Font` and `Aspose.Cells for Python` have no diagram). Fences are
  in `mermaid\fences\`; history (`git fetch --depth=300`, read-only) gave 58 distinct diagram revisions in
  `mermaid\history\`.
* Renderer: Node 22.23.3 (zip sha256 `2b0ff57b...ed71`, equal to nodejs.org's SHASUMS256) extracted
  to `D:\tools\mermaid\node-extract`; `D:\tools\mermaid\tools` = `npm ci --ignore-scripts` of
  `components/readme_diagram/render/package.json`: mermaid 11.17.2 (the primary), 11.4.1, 11.12.0,
  12.1.0, puppeteer-core 25.13.0; an extra `D:\tools\mermaid\bisect` held 11.13.0 to 11.16.1 for the
  entity-text bisect. Browser: the installed Edge 155.0.4283.45, headless. Fonts present: Verdana,
  Arial, Tahoma, Segoe UI, Georgia, Trebuchet MS (Mermaid's own first choice).
* Measurement (`render/measure.mjs`): render each source with `securityLevel: 'strict'`, default
  theme; record every node/cluster box and label box; then force the page into each stress font
  (`Arial, Verdana, Tahoma, Segoe UI, Georgia`) *after* measuring, which is how a hosted renderer
  ends up with a box sized for one font and text drawn in another; a label is clipped when its text
  exceeds its box (foreignObject: beyond the clip box; SVG: beyond the node rect) by more than 1 px.
* Images: `mermaid\png_before\<repo>.png` (live drawing), `mermaid\png_after\<repo>.png` (rebuilt),
  `mermaid\png_history\*.png`; raw measurements `m_before.json`, `m_after.json`, `m_history.json`,
  `mx_<package>.json`.

## 3. The 32 live diagrams, classified and rendered (Mermaid 11.17.2)

Orientation = where the three mother clusters sit. "Clipped natively" = browser measured and drew in
the same font (0 everywhere, which is why the aspose.org "independent re-render" saw nothing).
"Clipped after font swap" = fonts of the five in which at least one label exceeds its box, and the
worst count of labels in one font.

| repo | root | groups / nested | direction stmts | labels | longest label | longest word | `<br/>` | init | orientation | vertical mother blocks | clipped natively | clipped after font swap (fonts of 5, worst labels) | after: orientation | after: clipped | size before -> after |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Aspose-PDF-FOSS-for-Go | TD | 2 nested | LR,TB | 27 | 53 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 16) | horizontal | 0/5 fonts | 2155x1149 -> 1098x1066 |
| Aspose-PDF-FOSS-for-Python | TD | 2 nested | LR,TB | 18 | 42 | 14 | 0 | - | vertical | yes | 0 | 3/5 (max 9) | horizontal | 0/5 fonts | 1652x1002 -> 1053x783 |
| Aspose.3D-FOSS-for-.NET | TD | 2 nested | LR,TB | 17 | 59 | 12 | 0 | - | vertical | yes | 0 | 4/5 (max 10) | horizontal | 0/5 fonts | 1219x1026 -> 1106x535 |
| Aspose.3D-FOSS-for-Java | TD | 2 nested | LR,TB | 12 | 53 | 13 | 0 | - | vertical | yes | 0 | 4/5 (max 7) | horizontal | 0/5 fonts | 1015x1002 -> 1074x535 |
| Aspose.3D-FOSS-for-Python | TD | 2 nested | LR,TB | 14 | 56 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 11) | horizontal | 0/5 fonts | 1345x997 -> 1100x685 |
| Aspose.3D-FOSS-for-TypeScript | TD | 2 nested | LR,TB | 16 | 49 | 16 | 0 | - | vertical | yes | 0 | 3/5 (max 7) | horizontal | 0/5 fonts | 1041x1050 -> 1134x535 |
| Aspose.BarCode-FOSS-for-Python | TD | none | TB | 10 | 63 | 20 | 0 | - | vertical | yes | 0 | 4/5 (max 6) | horizontal | 0/5 fonts | 1586x500 -> 675x624 |
| Aspose.Cells-FOSS-for-.NET | TD | 2 nested | LR,TB | 14 | 54 | 12 | 0 | - | vertical | yes | 0 | 5/5 (max 9) | horizontal | 0/5 fonts | 1041x1101 -> 1128x518 |
| Aspose.Cells-FOSS-for-Cpp | TD | 2 nested | LR,TB | 15 | 58 | 12 | 0 | - | vertical | yes | 0 | 5/5 (max 4) | horizontal | 0/5 fonts | 1661x1050 -> 1122x818 |
| Aspose.Cells-FOSS-for-Go | TD | 2 nested | LR,TB | 15 | 56 | 19 | 0 | - | vertical | yes | 0 | 3/5 (max 9) | horizontal | 0/5 fonts | 1351x1149 -> 1194x685 |
| Aspose.Cells-FOSS-for-Java | TD | 2 nested | LR,TB | 21 | 73 | 18 | 0 | - | vertical | yes | 0 | 5/5 (max 13) | horizontal | 0/5 fonts | 2438x1064 -> 1133x1269 |
| Aspose.Cells-FOSS-for-Rust | TD | 2 nested | LR,TB | 16 | 63 | 13 | 0 | - | vertical | yes | 0 | 4/5 (max 9) | horizontal | 0/5 fonts | 1637x1002 -> 1064x800 |
| Aspose.Cells-FOSS-for-TypeScript | TD | 2 nested | LR,TB | 16 | 68 | 12 | 0 | - | vertical | yes | 0 | 5/5 (max 8) | horizontal | 0/5 fonts | 1351x1026 -> 1135x721 |
| Aspose.PDF-FOSS-for-Cpp | TD | 2 nested | LR,TB | 19 | 58 | 20 | 0 | - | vertical | yes | 0 | 5/5 (max 8) | horizontal | 0/5 fonts | 1661x1149 -> 1138x871 |
| Aspose.PDF-FOSS-for-Java | TD | 2 nested | LR,TB | 23 | 40 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 15) | horizontal | 0/5 fonts | 1661x954 -> 1068x783 |
| Aspose.PDF-FOSS-for-TypeScript | TD | 2 nested | LR,TB | 19 | 58 | 16 | 0 | - | vertical | yes | 0 | 5/5 (max 10) | horizontal | 0/5 fonts | 1661x1253 -> 1176x818 |
| Aspose.PSD-FOSS-for-.NET | TD | none | TB | 9 | 45 | 15 | 6 | init | vertical | yes | 0 | 5/5 (max 9) | horizontal | 0/5 fonts | 752x703 -> 939x321 |
| Aspose.PSD-FOSS-for-Python | TD | none | TB | 9 | 45 | 15 | 6 | init | vertical | yes | 0 | 5/5 (max 8) | horizontal | 0/5 fonts | 752x727 -> 939x321 |
| Aspose.Slides-FOSS-for-.NET | TD | 2 nested | LR,TB | 14 | 58 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 5) | horizontal | 0/5 fonts | 1351x1026 -> 1107x703 |
| Aspose.Slides-FOSS-for-Cpp | TD | 2 nested | LR,TB | 15 | 58 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 7) | horizontal | 0/5 fonts | 1351x1002 -> 1091x685 |
| Aspose.Slides-FOSS-for-Java | TD | 2 nested | LR,TB | 15 | 58 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 7) | horizontal | 0/5 fonts | 1351x1002 -> 1090x685 |
| Aspose.Slides-FOSS-for-Python | TD | 2 nested | LR,TB | 19 | 54 | 13 | 0 | - | vertical | yes | 0 | 5/5 (max 8) | horizontal | 0/5 fonts | 1960x1050 -> 1119x986 |
| Aspose.TeX-FOSS-for-Python | TD | none | TB | 12 | 71 | 12 | 0 | - | vertical | yes | 0 | 4/5 (max 6) | horizontal | 0/5 fonts | 1276x727 -> 960x446 |
| Aspose.Words-FOSS-for-.NET | TD | 2 nested | LR,TB | 17 | 46 | 15 | 0 | - | vertical | yes | 0 | 3/5 (max 11) | horizontal | 0/5 fonts | 1037x1026 -> 1152x518 |
| Aspose.Words-FOSS-for-Python | TD | none | TB | 17 | 65 | 12 | 0 | - | vertical | yes | 0 | 5/5 (max 12) | horizontal | 0/5 fonts | 1537x703 -> 941x554 |
| aspose-email-foss_Aspose.Email-FOSS-for-.Net | TD | none | TB | 12 | 61 | 14 | 0 | - | vertical | yes | 0 | 3/5 (max 6) | horizontal | 0/5 fonts | 1276x703 -> 917x499 |
| aspose-email-foss_Aspose.Email-FOSS-for-Cpp | TD | none | TB | 15 | 55 | 16 | 0 | - | vertical | yes | 0 | 5/5 (max 8) | horizontal | 0/5 fonts | 1569x703 -> 929x607 |
| aspose-email-foss_Aspose.Email-FOSS-for-Python | TD | none | LR,TB | 15 | 71 | 20 | 0 | - | vertical | yes | 0 | 3/5 (max 7) | horizontal | 0/5 fonts | 1586x1002 -> 942x748 |
| aspose-html-foss_Aspose.HTML-FOSS-for-Python | TD | 2 nested | LR,TB | 14 | 58 | 18 | 0 | - | vertical | yes | 0 | 3/5 (max 8) | horizontal | 0/5 fonts | 1351x1074 -> 1132x721 |
| aspose-imaging-foss_Aspose.Imaging-FOSS-for-.NET | TD | none | TB | 12 | 39 | 14 | 15 | init | vertical | yes | 0 | 4/5 (max 11) | horizontal | 0/5 fonts | 826x775 -> 949x446 |
| aspose-note-foss_Aspose.Note-FOSS-for-Python | TD | 2 nested | LR,TB | 12 | 42 | 21 | 0 | - | vertical | yes | 0 | 3/5 (max 5) | horizontal | 0/5 fonts | 1041x1026 -> 1082x500 |
| aspose-page-foss_Aspose.Page-FOSS-for-Python | TD | 2 nested | LR,TB | 14 | 60 | 20 | 0 | - | vertical | yes | 0 | 4/5 (max 5) | horizontal | 0/5 fonts | 1041x1221 -> 1192x535 |

* vertical: 32 of 32 | clipped natively: 0 | clipped after font swap: 32 | after horizontal: 32 | after clipped: 0
* mean width before/after: 1392 1059 max: 2438 1194

Shape facts (all measured on the fences): root `flowchart TD` 32; `direction` lines present in
every one (`LR` on Starting Points/Core, `TB` on the columns and Outputs); 23 have the two
`capl`/`capr` capability columns; 1 has no Starting Points; 1 titles the first group "Inputs and
formats"; 3 carry the `<br/>`-wrapped, `%%{init: {"flowchart": {"useMaxWidth": true}}}%%` form
(the PSD and Imaging repositories: their `<br/>` wraps do not prevent the clip); none uses
`classDef`/`style`; the longest label is 73 characters and the longest unbroken word 21; one label
(`Aspose.Cells for Rust`, `Vec<u8>`) already loses text because Mermaid drops `<u8>` as an HTML tag.

Examples of what clips under Verdana (3D for Python): `Polygon triangulation` by 18 px,
`OBJ, STL, glTF, or 3MF file` by 11 px, the titles `Starting Points` (14 px), `Core Capabilities`
(13 px), `Outputs` (7 px) - the narrow single-line boxes lose width, the 200 px-wrapped ones
(`Lambert, Phong, and PBR material assignment`, `Scene-graph construction and traversal`) lose a
whole line (24 px). Cells for Go: `CSV import and export` by 22 px, `Aspose.Cells FOSS for Go` by 22 px.

## 4. History: the older revisions and the best reference design

58 distinct diagram revisions across the 32 repositories that carry one (`mermaid\history`; 57 render, one - the Cells for .NET merge commit `ee20ac6` - is not valid Mermaid: it was committed with `<<<<<<< HEAD` conflict markers inside the diagram):

| repo | commit | date | root | orientation | clipped natively | clipped after font swap (of 5 fonts) | subject |
|---|---|---|---|---|---|---|---|
| aspose-email-foss_Aspose.Email-FOSS-for-.Net | 59125b4 | 2026-08-15 | TD | vertical | 0 | 3/5 | docs: refresh README with verified content, struct |
| aspose-email-foss_Aspose.Email-FOSS-for-Cpp | fef9c93 | 2026-08-15 | TD | vertical | 0 | 5/5 | docs: refresh README with verified content, struct |
| aspose-email-foss_Aspose.Email-FOSS-for-Python | 10a906b | 2026-08-15 | TD | vertical | 0 | 3/5 | docs: refresh README with verified content, struct |
| aspose-html-foss_Aspose.HTML-FOSS-for-Python | 912f0ae | 2026-08-16 | TD | vertical | 0 | 3/5 | fix(readme): production-grade README refresh (#2) |
| aspose-imaging-foss_Aspose.Imaging-FOSS-for-.NET | 5872b4a | 2026-10-10 | TD | vertical | 0 | 4/5 | Refresh README: verified examples and documentatio |
| aspose-imaging-foss_Aspose.Imaging-FOSS-for-.NET | 6ebb209 | 2026-10-10 | TD | vertical | 0 | 4/5 | Refresh README: verified examples and documentatio |
| aspose-note-foss_Aspose.Note-FOSS-for-Python | 41de2e8 | 2026-08-16 | TD | vertical | 0 | 3/5 | Refresh README: verified examples and documentatio |
| aspose-page-foss_Aspose.Page-FOSS-for-Python | ca4fb3d | 2026-08-16 | TD | vertical | 0 | 4/5 | content(page/python): restore Example Results scre |
| aspose-page-foss_Aspose.Page-FOSS-for-Python | 43cef36 | 2026-09-19 | TD | vertical | 0 | 4/5 | Refresh README: verified examples and documentatio |
| Aspose-PDF-FOSS-for-Go | 2306eeb | 2026-08-18 | TD | vertical | 0 | 5/5 | docs: comprehensive README refresh — verified feat |
| Aspose-PDF-FOSS-for-Go | ab212bd | 2026-09-10 | TD | vertical | 0 | 5/5 | feat: PDF portfolios — /Collection over the embedd |
| Aspose-PDF-FOSS-for-Python | 3c0e7ad | 2026-08-18 | TD | vertical | 0 | 3/5 | docs: comprehensive README refresh — verified feat |
| Aspose-PDF-FOSS-for-Python | 4f6c263 | 2026-10-08 | TD | vertical | 0 | 3/5 | feat(pdfx): check and write the five PDF/X levels  |
| Aspose.3D-FOSS-for-.NET | 158183d | 2026-08-04 | LR | horizontal | 0 | 4/5 | docs: refresh README with verified examples and do |
| Aspose.3D-FOSS-for-.NET | 70933ab | 2026-08-14 | TD | vertical | 0 | 4/5 | fix: eliminate Mermaid node-text clipping in the A |
| Aspose.3D-FOSS-for-.NET | 042a1e5 | 2026-08-19 | TD | vertical | 0 | 4/5 | docs: refresh README with verified capabilities an |
| Aspose.3D-FOSS-for-Java | d2cbb55 | 2026-08-04 | LR | horizontal | 0 | 4/5 | docs: refresh README with verified examples and do |
| Aspose.3D-FOSS-for-Java | 8c5998b | 2026-08-11 | TD | vertical | 0 | 4/5 | Refresh README: verified API accuracy, simplified  |
| Aspose.3D-FOSS-for-Java | 0f77c8a | 2026-09-12 | TD | vertical | 0 | 4/5 | Refresh README: verified examples and documentatio |
| Aspose.3D-FOSS-for-Python | 9fad456 | 2026-08-04 | LR | horizontal | 0 | 5/5 | docs: refresh README with verified examples and do |
| Aspose.3D-FOSS-for-Python | ca44249 | 2026-08-04 | LR | horizontal | 0 | 5/5 | docs: restore Animation capability category to Key |
| Aspose.3D-FOSS-for-Python | ee05c1b | 2026-08-14 | TD | vertical | 0 | 5/5 | fix: eliminate Mermaid node-text clipping in the A |
| Aspose.3D-FOSS-for-Python | 65b1f57 | 2026-09-03 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.3D-FOSS-for-TypeScript | 098184f | 2026-08-04 | LR | horizontal | 0 | 3/5 | docs: refresh README with verified examples and do |
| Aspose.3D-FOSS-for-TypeScript | 7b95970 | 2026-08-11 | TD | vertical | 0 | 3/5 | Refresh README: verified API accuracy, simplified  |
| Aspose.3D-FOSS-for-TypeScript | 66cb26d | 2026-09-18 | TD | vertical | 0 | 3/5 | Refresh README: verified examples and documentatio |
| Aspose.BarCode-FOSS-for-Python | 06eca5c | 2026-08-15 | TD | vertical | 0 | 4/5 | docs: refresh README with verified content, struct |
| Aspose.Cells-FOSS-for-.NET | 6ee32c0 | 2026-08-14 | TD | vertical | 0 | 5/5 | docs: refresh README with verified content and cur |
| Aspose.Cells-FOSS-for-.NET | 666f894 | 2026-09-01 | TD | vertical | 0 | 5/5 | V26.9.0 |
| Aspose.Cells-FOSS-for-.NET | ee20ac6 | 2026-09-01 | TD | render error | | | Merge branch 'master' of https://github.com/aspose |
| Aspose.Cells-FOSS-for-.NET | 941814f | 2026-09-01 | TD | vertical | 0 | 5/5 | Update Readme |
| Aspose.Cells-FOSS-for-Cpp | 9f852d0 | 2026-08-13 | TD | vertical | 0 | 5/5 | docs: refresh README with verified capabilities, e |
| Aspose.Cells-FOSS-for-Go | 9f0a403 | 2026-08-13 | TD | vertical | 0 | 3/5 | docs: refresh README with restored Project Structu |
| Aspose.Cells-FOSS-for-Java | 779c964 | 2026-08-13 | TD | vertical | 0 | 5/5 | docs: refresh repository presentation |
| Aspose.Cells-FOSS-for-Python | 26c3bd1 | 2026-08-14 | TD | vertical | 0 | 3/5 | docs: refresh README with verified capabilities, e |
| Aspose.Cells-FOSS-for-Rust | 1a6004a | 2026-08-14 | TD | vertical | 0 | 4/5 | docs: refresh repository presentation (#1) |
| Aspose.Cells-FOSS-for-TypeScript | fc18650 | 2026-08-14 | TD | vertical | 0 | 5/5 | docs: refresh README with verified content, diagra |
| Aspose.PDF-FOSS-for-.NET | d10e2c8 | 2026-09-12 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.PDF-FOSS-for-Cpp | 888700a | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: refresh README with fuller capability covera |
| Aspose.PDF-FOSS-for-Cpp | c559fc3 | 2026-09-18 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.PDF-FOSS-for-Java | ea62b38 | 2026-08-18 | TD | vertical | 0 | 5/5 | docs: comprehensive README refresh — verified feat |
| Aspose.PDF-FOSS-for-TypeScript | a450978 | 2026-09-04 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.PSD-FOSS-for-.NET | 85ed7ee | 2026-10-10 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.PSD-FOSS-for-Python | dbc90f4 | 2026-10-10 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.Slides-FOSS-for-.NET | 6c650e9 | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: correct README Key Capabilities accuracy and |
| Aspose.Slides-FOSS-for-.NET | dcc48b8 | 2026-08-28 | TD | vertical | 0 | 5/5 | Merge main and reconcile the README |
| Aspose.Slides-FOSS-for-Cpp | ecc2baf | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: correct and expand README Key Capabilities a |
| Aspose.Slides-FOSS-for-Cpp | f9176f6 | 2026-08-28 | TD | vertical | 0 | 5/5 | Merge main and reconcile README capability and dia |
| Aspose.Slides-FOSS-for-Cpp | 6ed44d5 | 2026-09-19 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.Slides-FOSS-for-Java | 5d76f44 | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: correct README Key Capabilities accuracy and |
| Aspose.Slides-FOSS-for-Java | 4435e6b | 2026-08-28 | TD | vertical | 0 | 3/5 | Merge main; reconcile README and add a corrected a |
| Aspose.Slides-FOSS-for-Java | 5850ec8 | 2026-09-18 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.Slides-FOSS-for-Python | 62f3011 | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: correct README accuracy, restore missing cap |
| Aspose.Slides-FOSS-for-Python | 98a87b4 | 2026-08-28 | TD | vertical | 0 | 5/5 | Merge main and reconcile the README |
| Aspose.Slides-FOSS-for-Python | a944320 | 2026-09-18 | TD | vertical | 0 | 5/5 | Refresh README: verified examples and documentatio |
| Aspose.TeX-FOSS-for-Python | 181015d | 2026-09-02 | TD | vertical | 0 | 4/5 | Refresh README: verified examples and documentatio |
| Aspose.Words-FOSS-for-.NET | 68d56fd | 2026-08-17 | TD | vertical | 0 | 3/5 | docs: refresh README with verified content, depend |
| Aspose.Words-FOSS-for-Python | 2d2efee | 2026-08-17 | TD | vertical | 0 | 5/5 | docs: refresh README with verified content, images |

* The only horizontal revisions are the five of 2026-08-04: `flowchart LR` with `Inputs and formats`,
  `Core capabilities`, `Outputs and accessible content` subgraphs and one edge per node
  (`I1 --- PRODUCT`, `PRODUCT --- C1`, `C1 --- O1`): each block a column of one box per capability,
  split by key capability, the product in the middle, blocks left to right. **That is the reference
  design** (`png_history\Aspose.3D-FOSS-for-Python.ca44249.2026-08-04.png`). It was abandoned
  because its crossing edges drew cut-off text on GitHub (commit `ee05c1b`); but the clip is the
  HTML-label zero-slack defect, not the edges (the LR revisions clip under font swap too, 3 to 5 of
  5 fonts), and the contract (README_CONTRACT 2.1) forbids per-node edges. The new drawing keeps
  its block order and one-box-per-capability columns, keeps the contract's single chain edge, and
  removes the clip cause.
* Every revision from 2026-08-11 on is `flowchart TD`: vertical in all 52 that render, clipped in all.

## 5. Cause analysis, with the evidence

1. **Orientation is the root direction.** `flowchart TD` plus
   `StartingPoints --> PRODUCT --> Capabilities --> Outputs` ranks the blocks top to bottom. Changing
   only the first line to `LR` puts them left to right (`mermaid\var2\h4.mmd` is the TD form,
   `h1.mmd` the LR form; their renders are in `mermaid\var2_mermaid`).
2. **`direction` is honoured here, and means the opposite of the intent.** The chain edge joins
   subgraph *ids*, not nodes inside them, so no group is "linked to the outside" in Mermaid's sense
   (the known rule that a subgraph whose own nodes link outward ignores its `direction` does not
   apply; making `c4 ~~~ c5` cross the columns *does* trigger it and scrambles the layout, seen in an early
   variant run that was not kept). So `direction LR` over the unlinked `Starting Points` nodes puts them on one rank in a
   column, `direction TB` over the unlinked capability nodes lays them in a row, and the two
   capability clusters under `Core ... direction LR` stack vertically. Observed in
   `png_before\Aspose.3D-FOSS-for-Python.0.png`: Core is two stacked rows, not two columns.
3. **Sibling clusters are drawn in reverse declaration order** on every 11.x release measured (the
   first-declared column lands on the right), so even the intended side-by-side reads
   `c5..c8` before `c1..c4`. Mermaid 12.1 orders them by its own heuristic (20 of 23 reversed).
4. **Clipping is a font mismatch against a zero-slack box.** With HTML labels each `foreignObject`
   width and height equal the measured label; I forced each of five wider fonts after measuring:
   32 of 32 diagrams clip, 4 to 16 labels each in Verdana. `flowchart.wrappingWidth` is 200 px, so
   long labels are wrapped by the browser at draw time and the extra line is cut off vertically.
   `flowchart.htmlLabels: false` alone is not enough: 11.17 draws the titles as HTML anyway; the
   root `htmlLabels: false` alone is not enough on 11.4 to 11.12; both are needed (measured).
   `useMaxWidth` is not a factor.
5. **Text Mermaid eats.** `<u8>` in a label is read as an HTML tag and dropped on every release; with
   SVG labels, `&`, `<` and `>` are drawn as entity text (`&amp;`) on 11.4 to 11.13 (fixed in 11.14,
   bisected); `#lt;`/`#gt;` entities draw correctly from 11.14.
6. **The old rules cannot express the fix.** BC-07's `_topology_failures` requires the first line to
   be `flowchart TD`, exactly one edge line (so `~~~` pins fail), and treats `Scene-graph<br/>construction`
   as a 36-character token (so any hand-wrapped label fails): measured by forcing the new drawing
   through the correction gate, four BC-07 failures are introduced.

## 6. The fix

`src/repository_presenter/components/readme_diagram/` (recorded in docs/REPOSITORY_LAYOUT.md):

| module | what it does |
|---|---|
| `geometry.py` | per-character width table = envelope of Verdana/Arial/Trebuchet/Segoe UI/Tahoma at 16 px (+4%); `wrap_label` breaks between words into the fewest lines that fit a pixel budget, then evens them |
| `parse.py`, `model.py` | read the closed At a Glance shape (live TD form and canonical form) into a `Glance`; anything else is refused and left alone |
| `build.py` | `flowchart LR`; init line with `htmlLabels:false` at both keys, `nodeSpacing 22`, `rankSpacing 26`, `padding 10`; Starting Points / Core / Outputs left to right; each multi-node group `direction TB` with `a ~~~ b ~~~ c` pins; two capability columns declared right-to-left; labels wrapped to 200 px (one column) or 160 px (two); `<`/`>` as entities |
| `lint.py` | the deterministic model: ORIENTATION_VERTICAL, CLIP_HTML_LABELS, CLIP_AUTO_WRAP, GROUP_LAID_AS_ROW, ORDER_UNPINNED, COLUMN_ORDER, LABEL_MARKUP_LOST (+ advisories LABEL_TOKEN_WIDE, LABEL_ENTITY_RISK) |
| `rebuild.py` | rewrites only the lines between a README's fence markers; every other byte and the line endings are returned unchanged; a rebuild is proved to keep every label, title and edge |
| `contract.py` | README_CONTRACT 2.1 as a pure function (`topology_failures`, `title_failure`) for BC-07 and planning to delegate to |
| `render_check.py` + `render/measure.mjs` | the real-render check: no label exceeds its box natively or in five fonts; blocks left to right; node order; label text intact and drawn on the modelled lines; model envelope; width <= 1600 px |
| `__main__.py` | `python -m repository_presenter.components.readme_diagram lint | rebuild [--write] | render-check README...` |

Result over the 32 live diagrams (Mermaid 11.17.2, Edge): orientation vertical 32 -> 0 (horizontal 32),
clipped natively 0 -> 0, clipped under font swap 32 -> 0, mean drawing width 1392 -> 1059 px (max
2438 -> 1194), labels and titles identical (parse before == parse after, 32 of 32). The same 32
diagrams on 11.4.1, 11.12.0 and 11.17.2 pass `check_entry` completely; on 12.1.0 they pass except
that the first capability column is drawn left of the second in only 3 of the 23 two-column
diagrams (side by side in all; `columns_in_order=False` for 12.x). Layout quirks the design relies
on, each pinned by a test: declare the right column first (11.x), never set `wrappingWidth` (12.1
reverses the columns if it is present), set both `htmlLabels` keys, pin every group with `~~~`.

Known limits: labels containing `&`, `<`, `>` show entity text on Mermaid before 11.14 (one live
label: Cells for Rust, which already loses `<u8>` today); one word wider than 200 px (`Document/Page/
Outline`, `SUM/AVERAGE/MAX/MIN`) cannot be wrapped, the box grows to it.

## 7. What the governed cut must change (not done here; prototype patch applied to a throwaway
worktree: `lmmd-governed-cut-prototype.patch`)

* `components/readme/composition/renderer.py::_at_a_glance` (and its docstring): build a
  `readme_diagram.Glance` (product `_label(context.name)`, starting point `An existing <formats> file`,
  `balanced_columns(titles)`, output `<formats> file`) and return `build_block(glance)`; delete the
  inline subgraph/edge emission. `_label`, `_or_list`, `format_name` stay. Bump `RENDERER_VERSION`.
* `components/readme/validation/registry.py`: replace `_topology_failures` (and delete
  `_column_size`, `_CAPABILITY_NODE`, `_GLANCE_LABEL`, `_GLANCE_DIRECTIVE`, the `glance` import) with
  a delegation to `readme_diagram.contract.topology_failures`; the call site is
  `_check_structure` (`for body in graphs`). Bump the BC-07 `Check` version and `VALIDATOR_VERSION`.
  Sealed candidates then show `VALID_UPDATE_AVAILABLE` / `UPDATE_REQUIRED` through recheck (policy
  call: the old diagram is the defect, so UPDATE_REQUIRED is honest).
* `components/readme/composition/planning.py` (capability-title geometry in the at_a_glance plan
  validation, imports at the top): call `readme_diagram.contract.title_failure(title, len(titles))`.
* `components/readme/composition/components/glance.py` and `tests/.../components/test_glance.py`:
  superseded by `readme_diagram.geometry`; delete or keep as a shim.
* `docs/README_CONTRACT.md` 2.1 and the BC-07 row (7): the drawing is `flowchart LR` after one
  `%%{init}%%` line, blocks left to right, capability columns side by side, labels wrapped by the
  width model (no label past four lines at the line budget), no styling directive; planning
  recommendation: keep `&`, `<`, `>` out of diagram labels (the renderer may write "and").
* Tests that pin the old drawing (all fail under the prototype): `test_renderer.py`
  (`test_at_a_glance_is_the_one_chain_of_section_2_1`,
  `test_at_a_glance_drops_absent_groups_and_balances_six_or_more_capabilities`), `test_planning.py`
  (`test_at_a_glance_labels_are_geometry_safe_and_number_three_to_eight`,
  `test_an_at_a_glance_title_that_wraps_past_three_lines_is_shortened_at_planning`),
  `validation/test_registry.py` (`test_every_failure_names_its_causal_stage`,
  `test_an_at_a_glance_label_that_wraps_past_three_lines_fails`), and three in
  `bundle/test_recheck.py` whose sealed fixture carries the old diagram. The rest of
  composition/validation/review/bundle/repair passed under the prototype.
* CI: the real-render tests skip without `RP_MERMAID_TOOLS`; to run them hosted, `npm ci
  --ignore-scripts` in `components/readme_diagram/render` (PUPPETEER_SKIP_DOWNLOAD=1), export
  `RP_MERMAID_TOOLS` to that directory, a Chrome is on the runner. Nothing they do uses the network.

## 8. Live-first correction path

`wt/lmmd-reg01` (off `wt/lfix-fix01`): the package merged plus one detector, `at_a_glance_diagram`,
registered by name (the pinned name list in `test_engine.py` gains it). It cannot edit yet, for two
reasons it reports as a Finding: (a) the Edit model has no kind for a whole-diagram body
(`STRUCTURE_FIX` and the claim kinds are one line, <= 200 characters): needs `DIAGRAM_FIX` in
`model.py`, `gate.py` and `pull_request.py` (patch: `lmmd-lfix-diagram-fix.patch`; with it the three
edit-path tests pass and the whole correction suite is green); (b) BC-07 refuses the new drawing (above). The detector asks the
running BC-07 directly and fails closed, so it starts editing in the same build that teaches BC-07
the horizontal contract. Measured with (a) applied and BC-07 forced: the corrected README introduces
four BC-07 failures (`flowchart TD`, one chain, two 28-character token findings).

## 9. Text for the state machine (for the lanes that own those files)

* DEFECT_INDEX candidate class `GLANCE_DIAGRAM_DRAWING`: At a Glance diagram drawn `flowchart TD`
  (blocks stacked) with HTML labels (clips under a font mismatch); 32 of 32 live READMEs, 2026-10-11;
  repaired by `components/readme_diagram` (earliest causal stage: composing/renderer).
* DECISION_LOG candidate: At a Glance is drawn horizontally with SVG labels; the diagram builder is
  one module shared by the renderer and the correction path; the real-render check is optional
  tooling (`RP_MERMAID_TOOLS`) and its tests skip without it; BC-07 and the renderer adopt it in the
  next governed cut, the correction kind `DIAGRAM_FIX` in the next correction-path change.
