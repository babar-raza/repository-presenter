authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Wave 5 triage (cut e407503a = integration/cut4, results runs/reseal/e407503a/results.jsonl): FINAL, 44 of 44 rows

Superseded by wave 6 (cut 8fbf2166). Wave 5 is invalid for the 7 rows that crashed with `TypeError: reconciliation_narrowing.<locals>.ask() takes 3 positional arguments but 4 were given` (BarCode-Python, Font-Python, Imaging-.NET, PDF-TypeScript, PSD-.NET, Slides-Python, Words-.NET); its other 37 rows are valid evidence of the cut.

Result: SEALED 3 (3D-TypeScript, Cells-Python, Note-Python; reviews acc-w5-*.md, all FIX_REQUIRED MAJOR), NOT_READY 1 (PDF-Python: examples.json timestamps), FAILED 40: BC-10 7, model_output 8, BC-02 7, unknown (the TypeError) 7, BC-05 3, BC-14 2, BC-07 2, BC-06 2, BC-08 1, BC-03 1.

Root cause of the crash (reported as an early alert): L-q1 `caf4ada6` widened `Narrowing.ask` to four arguments (added `repeated`) and updated `authoring_retry.authoring_narrowing` and the `jobs._narrowing` wrapper, not `reconciliation/dispositions.py:reconciliation_narrowing.<locals>.ask(unit_ids, content, rejection)`. Fixed in 8fbf2166.

Per-row causes of the other rows are in wave6-triage.md: rows 1-44 (the same repositories) and section 6 (wave-5-only rows: PDF-.NET, PSD-Python, Words-Python, Slides-Java, GIS-.Net, HTML-Python, PDF-Java, Slides-.NET, Page-Python, PDF-Cpp). Wave-5-only observations: Slides-.NET BC-06 (4 aspose.com links over a ceiling of 2) and BC-07 (kept paragraphs refer to a deleted 'What it cannot do' section, 301 visible lines of 747); PDF-Java BC-14 (stale Gradle snippet at 26.6.0 vs 26.9.0); PDF-Go BC-05 UNCLASSIFIED banner row.
