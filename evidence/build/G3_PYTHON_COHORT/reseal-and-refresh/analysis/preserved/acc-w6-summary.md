authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Acceptance review, reseal run 8fbf2166 (wave 6, integration/cut4b): summary

Protocol: TC-ACC-01 v1.1 (wt/lacc-acc01), reviewer independent and read-only (shallow clone of the live head, mech.py with link GETs, retention.py, the repository's Edge/mermaid check for orientation and clipped fonts, registry GETs, source greps). The standard applied is the one asked for: follow the LIVE README's structure, retention of live content, Mermaid horizontal and unclipped. Last refresh: 44 of 44 rows (final): SEALED 1, NOT_READY 1, TIMEOUT 1, FAILED 41.

Result: 1 SEALED row (Slides-Python), 1 NOT_READY row reviewed as a would-be candidate (PDF-Python). 0 AUTHORIZABLE, 1 FIX_REQUIRED (MAJOR), 1 DO_NOT_PROPOSE (would-be). Wave 5 (e407503a): 3 sealed rows, all FIX_REQUIRED MAJOR (acc-w5-summary.md).

| # | Candidate | Verdict | minor_major | NET vs live | Claims checked / failed | CORE retention (verbatim) | Headline blocking findings |
|---|---|---|---|---|---|---|---|
| 1 | Slides Python (SEALED) | FIX_REQUIRED | MAJOR | mixed | 14 / 1 | 54% | diagram Starting Points "An existing PNG file" (live: .pptx presentation) and Outputs without Markdown; Scope carries non-limitations (Python floor, CI matrix duplicated in Development) as extra bullet groups; Documentation & Resources ends with a stray paragraph repeating agents.md and CONTRIBUTING.md with a raw URL; Markdown export (24 flavors) absent from opening/capabilities/diagram; the live Markdown example dropped because its receipt FAILED on a one-slide fixture. Facts all verified (PyPI 26.8.0, extras, 44 test files, CI 15 jobs, ChartType 74, SaveFormat behaviour); wave-3 defects (cut-off bullet, version-skew, Enterprise paragraph) fixed |
| 2 | PDF Python (NOT_READY, would-be) | DO_NOT_PROPOSE | MAJOR | worse | 15 / 1 | 44% | product name "Aspose PDF FOSS" (live and product: Aspose.PDF); five live feature lists rewritten away (hundreds of verified names, validation advisory "the rewrite no longer names ..."); alpha notice and 12 of 24 code blocks dropped; "verified against this revision" narration; orphan Installation/Dependencies fragments in Quick Start and Key Capabilities; cannot seal yet (BC-11, timestamps in examples.json) |

Records (this directory): acc-w6-slides-python.md, acc-w6-pdf-python.md. Wave-5 records: acc-w5-3d-typescript.md, acc-w5-cells-python.md, acc-w5-note-python.md.

## Verdict distribution across all reviewed bundles of waves 3, 5, 6

| wave | sealed | AUTHORIZABLE | FIX_REQUIRED | DO_NOT_PROPOSE |
|---|---|---|---|---|
| 3 (f69f75c7) | 8 | 0 | 0 | 8 |
| 5 (e407503a) | 3 | 0 | 3 | 0 |
| 6 (8fbf2166) | 1 (+1 NOT_READY) | 0 | 1 | 0 (+1 would-be) |

Direction is right (the wave-3 bundles failed on false claims, cut-off prose, dropped sections; the wave-5/6 bundles have verified facts and mostly clean mechanics) but the two defects below appear in every bundle and keep the count of AUTHORIZABLE at zero.

## Universal defects, by causal stage (all reviewed bundles)

1. U-PLACEMENT (every bundle): kept inherited units land in the wrong section or are printed beside text that restates them: dependency bullets in Documentation & Resources (3D-TS), Dependencies paragraphs in Quick Start (Note-Python, PDF-Python), a lead-in split from its block (Cells-Python), the licence paragraph in Scope (3D-TS, Cells-Python), CI matrix and Python floor in Scope (Slides-Python), duplicate agents.md/CONTRIBUTING.md paragraph (Slides-Python). Stage: S4 destination choice, `reconciliation/destinations.py:_HOMES["install"]` (non-code pool starts with scope_limitations), lead-in/payload coordination, and version-insensitive `coverage.uncovered`. Single biggest lever for AUTHORIZABLE.
2. U-NARRATION (3D-TS, PDF-Python; HTML-Python and JMAP failures show it on unpublished libraries): `composition/renderer.py` L1113/1129/1144/1146 print "build it from a source checkout instead, verified against this revision:" in the public README; C16 and mech.py do not flag it. Stage: renderer wording + C16/BC-07 phrase list.
3. U-DIAGRAM-CONTENT (Slides-Python, 3D-TS, PDF-Python): the deterministic diagram drops the live README's Starting Points/Outputs or replaces them with a different input (PNG), while geometry is now right (horizontal, unclipped, all candidates). Stage: diagram derivation from input/output facts (`readme_diagram/build.py`).
4. U-RETENTION (every bundle): VERIFIED_REWRITE collapses live feature lists into 8 generic bullets; the loss is logged as non-blocking "the rewrite no longer names ..." advisories (PDF-Python: five lists, hundreds of names). Stage: S4/S6; gate: promote that advisory to a blocking check when more than a bound of verified names disappear.
5. U-NAME (PDF-Python, PDF-Go): `identity.py:product_name` loses the dot for hyphenated repository names ("Aspose PDF FOSS"). Stage: identity component + BC-12.
6. U-CONTRADICTION (Note-Python w5, Cells-Python w5): counts and stub claims contradict other sections. Stage: S8 coherence.
7. U-EXAMPLE-HARNESS (Slides-Python): a valid live example is dropped because the fixture is too small (FAILED rather than NEEDS_INPUT). Stage: example verification (`extractors/platforms/python_examples.py`).

## Positive observations

- All five bundles' Mermaid diagrams render horizontal (flowchart LR) with zero clipped fonts, where the live READMEs' own diagrams are vertical with 3-5 clipped fonts or absent.
- Registry and source facts are accurate in every spot-check that could be run (PyPI versions, extras, npm 404 for unpublished packages, test-file counts, CI matrices, enum sizes).
- The wave-3 universal defects U-AUDIENCE, U-COUNT, U-TRUNCATION-LANG, U-VERSION-SKEW, U-LICENSE-ID, the Enterprise Edition paragraph and the `[pdf]` extra drop are not seen in any wave-5/6 bundle.
- Zero-call no-op proofs are present for every sealed bundle.
