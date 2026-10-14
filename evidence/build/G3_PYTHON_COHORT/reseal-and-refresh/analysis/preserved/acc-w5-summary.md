authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Acceptance review, reseal run e407503a (wave 5, integration/cut4 head): summary of the 3 sealed rows

Protocol: TC-ACC-01 v1.1 (wt/lacc-acc01). Reviewer: independent, read-only (tools: shallow clone of the live head, mech.py, retention.py, Edge/mermaid renderer check, registry GETs, source greps). Wave 5 is invalid for the 7 rows that hit the `Narrowing.ask` TypeError (BarCode-Python, Font-Python, Imaging-.NET, PDF-TypeScript, PSD-.NET, Slides-Python, Words-.NET); its 3 sealed rows did not need a third reconciliation ask and are valid sealed bundles of the cut. Final tally of the run: 44 rows, SEALED 3, NOT_READY 1 (PDF-Python), FAILED 40.

Result: 0 AUTHORIZABLE, 3 FIX_REQUIRED (all MAJOR), 0 DO_NOT_PROPOSE. All three bundles are READY_FOR_PROPOSAL, review ACCEPT (as returned ACCEPT), BC-01..BC-14 PASS, no-op VERIFIED with 0 provider calls, revision == live head. Factual spot-checks mostly pass (claims checked / failed: 3D-TypeScript 14 / 1, Cells-Python 15 / 1, Note-Python 14 / 2; the failures are 1 MISLEADING, 1 MISLEADING and 1 FAIL + 1 MISLEADING). What blocks them is document quality, not truth: preserved inherited units printed in sections that do not own their topic, duplicate and fused statements, lead-ins without payloads, dropped live capabilities, and renderer-owned assurance narration. Compared with wave 3 (8 DO_NOT_PROPOSE, 4-8 failed claims each) these are clearly closer to publishable.

| # | Candidate | Verdict | minor_major | NET vs live | Claims checked / failed | CORE retention (verbatim) | Headline blocking findings |
|---|---|---|---|---|---|---|---|
| 1 | 3D TypeScript | FIX_REQUIRED | MAJOR | worse | 14 / 1 | 62% | orphan dependency bullets and a build paragraph under Documentation & Resources; Starting Points/Outputs dropped from the diagram; Format I/O says read glTF/OBJ only (STL/FBX/COLLADA/3MF importers exist); licence paragraph in Scope and in License; "verified against this revision" narration; 3MF and 33 of 97 live API rows dropped |
| 2 | Cells Python | FIX_REQUIRED | MAJOR | mixed | 15 / 1 | 63% | "Install the package from PyPI:" and "Install the renderer separately:" lead-ins with no payload (block moved to Development and Testing); fused/repeated Scope bullet; Third-Party/License notices duplicated; `pdf_exporter` called a function; live capabilities (merged cells, hyperlinks, page setup, auto-filters, comments, TSV) dropped. Better than live on structure and dependency facts |
| 3 | Note Python | FIX_REQUIRED | MAJOR | mixed | 14 / 2 | 78% | orphan Dependencies paragraphs and bullets at the end of Quick Start; Scope says `Document.GetPageHistory` is a compatibility stub (it returns real history); "all 39 public types. It covers all 37 verified public types"; the previously dropped `[pdf]` extra IS carried now |

Per-candidate records (this directory): acc-w5-3d-typescript.md, acc-w5-cells-python.md, acc-w5-note-python.md.

## Universal defects seen in all three (with causal stage)

1. U-PLACEMENT (3 of 3): kept inherited units are placed by topic into the nearest section that can hold them, not into the section that owns the topic: dependency lists in Documentation & Resources (3D-TS), a Dependencies paragraph block in Quick Start (Note-Python), an "Install the renderer separately:" lead-in split from its block (Cells-Python), the licence paragraph in Scope (3D-TS, Cells-Python). Stage: S4/S5 placement, `reconciliation/destinations.py:_HOMES["install"]` (non-code pool starts with scope_limitations) plus lead-in/payload coordination (`coordinate_neighbor_promises` handles only OMIT/DEFER payloads, a verified example's section and same-section lists).
2. U-NARRATION (1 of 3 seen, any source-checkout README): `composition/renderer.py` L1113/1129/1144/1146 print "verified against this revision" in the public Installation text; the C16 text check and mech.py do not flag it. Stage: renderer wording + C16.
3. U-DUP (3 of 3): authored text restates preserved units beside them (Scope in Cells-Python and Note-Python; licence in Scope and License). Stage: S6 authoring `carried_units` plus `coverage.uncovered` stem coverage.
4. U-CONTRADICTION (2 of 3): Note-Python 39 vs 37 types and the GetPageHistory clause; Cells-Python "functions" for a module. Stage: S6/S8 coherence and the type-count composer (`documentation_resources` mixes the live number with the composer's count).
5. U-RETENTION (3 of 3): live opening and several live capabilities dropped (3D-TS opening, 3MF; Cells-Python opening, 7 capabilities; Note-Python 9 sentences). Stage: S4 VERIFIED_REWRITE of list units into generic bullets (`validation.json` advisory "the rewrite no longer names ..." is non-blocking).

## Positive observations

- Every bundle's Mermaid diagram (rendered with the repository's Edge/mermaid check) is horizontal (`flowchart LR`) with zero clipped fonts, where the live README's own diagram is vertical with 3 clipped fonts (3D-TS, Note-Python) or absent (Cells-Python).
- Registry facts are right: PyPI versions 26.10.0 and 26.9.0 and extras verified, npm 404 for the unpublished `@aspose/3d` verified, test-file counts exact (32, 12), CI matrices exact.
- The Note-Python `[pdf]` extra defect of wave 3 is fixed; the dropped non-compiling live examples are correctly dropped.
- Zero-call no-op proofs are present for all three.
