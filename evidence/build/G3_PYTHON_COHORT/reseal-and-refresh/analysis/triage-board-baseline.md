authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
card: TC-TRI-01 (children TC-TRI-01-01 classify, TC-TRI-01-02 close the board)

# Triage board: baseline reseal of all 36 repositories (TC-TRI-01)

Inputs: `runs/reseal/7c5acbf7/results.jsonl` (36 rows, current origin/main `7c5acbf7`, run 2026-10-10), the per-repository archive under `E:\rp-archive\<family>-<platform>\` (logs, `calls/*.rejected-*.json`, `validation.json`, `review.json`, `repairs.json`, `dispositions.json`, `examples.json`, `facts.json`), `docs/DEFECT_INDEX.md`, `docs/DECISION_LOG.md`, `evidence/upstream-defects/`, the slice pilot `runs/reseal/e38cabc2/results.jsonl` and the acceptance findings `acc-baseline-vs-slice.md`. The exact messages, co-failures, resume predicates and fix files for every row are also in `triage-board-baseline.csv`.

Read-only: no `present`, no gateway call, no GitHub write, no change to `src/`, `candidates/` or `docs/`. Two local scratch reproductions (a `dotnet build` of the GIS-.NET clone and a `cmake -S . -B build` configure of the PDF-C++ clone) ran in the session scratchpad on copies; the cmake run attempted one GET of a googletest archive from github.com and wrote nothing to GitHub.

## Verdict

- **10 of 36 SEALED, 26 FAILED** (27.8 percent sealed; 986 provider calls and 559 process-minutes in the first invocation of each; zero-call no-op proof VERIFIED for all 10 seals).
- **All 10 seals were REJECT first and were converted to ACCEPT** by `reviewer_scope_defect` demotions (`review.json verdict_as_returned`): 8 REJECT_PRESENTATION, 2 REJECT_FACTUAL (3D-TypeScript, Cells-Cpp). Cells-Rust's run-1 bundle was converted the same way. So SEALED here does not mean reviewed good: the independent acceptance review of the 5 sealed bundles it covered (BarCode-Python, Cells-Python, Cells-Java, Cells-Go, 3D-Python) returned DO_NOT_PROPOSE for 5 of 5, and the slice pilot (REJECT stands) failed 4 of those 5 at BC-10.
- Typed terminal state of the 36: SEALED 10, FAILED_INTERNAL 20, BLOCKED_UPSTREAM 3 (GIS-.NET, PSD-Python, TeX-Python), DEFERRED(MACHINE_TOOLCHAIN) 3 (Cells-Rust, PDF-Cpp, Words-Python), NON_PROCESSABLE 0 (GIS-.NET is the expected NON_PROCESSABLE; no producer exists yet).
- Of the 26 failures: **7 need no governed change to clear the current stop (MINOR)** and **19 need a code change in a governed file (MAJOR)**. Of the 10 seals, 5 are already judged DO_NOT_PROPOSE (MAJOR) and 5 are unreviewed (UNREVIEWED); see the owner's test below.
- Variance is large and visible: the two repositories that were drawn twice failed twice with different causes (Slides-.NET: BC-05 UNCLASSIFIED then S6 superseded-unit; Words-Python: S6 identifier then BC-05 no-Quick-Start).

## Definitions used

- **Classes:** UPSTREAM_DEFECT, OUR_UNIVERSAL_DEFECT (a mechanism in our pipeline, counted across repositories), SAMPLING_VARIANCE (the same code could plausibly pass on a redraw; evidence cited per row), MACHINE_TOOLCHAIN, DATA/REGISTRY (none found). A row may carry a primary class and a parenthesised secondary.
- **MINOR** = clearing the current stop needs no governed file change: a redraw, a machine or data change, or an upstream fix. **MAJOR** = a code change in a governed file, a new fact kind or a new gate. MINOR does not mean the repository then seals; it means the *current* stop is not our code.
- **Counts** per mechanism are given three ways because they answer different questions: *stops* (the mechanism ended the run), *co* (it also failed in the same validation but was not the first stop) and *seen* (it appeared in a rejected call anywhere in the run, including those the re-ask recovered). The project's settled-priority threshold is three independent sightings (AGENTS.md).
- **Baseline vs integration:** the baseline is origin/main `7c5acbf7`. `integration/verified-1011` is ahead (TC-REV-01 `e482390b`, TC-CLM-01 `6b6393e4`, TC-DSP-01 `a9877f96` and its companion `e3a0026b`); none of those ran in this reseal. Where a landed integration change is relevant it is named, with the evidence for whether it covers the row.

## Board: one row per repository

| # | Repository | Outcome / terminal | Stopped at (stage, check) and exact message | Class | Mechanism | Change |
|---|---|---|---|---|---|---|
| 1 | Aspose.3D-FOSS-for-Java | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit type:public_symbol:com.aspose.threed.arraylistadapter: identifiers that are not accepted fact values: ArrayList (nearest accepted: ArrayListAdapter, ArrayListAdapter.add, ArrayListAdapter.get, ArrayListAdapter.set) | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | IDENT | MAJOR |
| 2 | Aspose.3D-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **RECONCILING, BC-05**: repository-presenter: validation: BC-05 failed at RECONCILING: inherited_unit:066.paragraph is deferred as UNCLASSIFIED: No deferral class matches this cause. It blocks until a class is registered in validation/deferrals.py.; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | UNCL,BC12 | MAJOR |
| 3 | Aspose.3D-FOSS-for-Python | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01,PRES | MAJOR |
| 4 | Aspose.BarCode-FOSS-for-Python | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01,PRES | MAJOR |
| 5 | Aspose.3D-FOSS-for-TypeScript | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01 | UNREVIEWED |
| 6 | Aspose.Cells-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **COMPOSING, BC-10**: repository-presenter: validation: BC-10 failed at COMPOSING: REJECT_PRESENTATION; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | PRES | MAJOR |
| 7 | Aspose.Cells-FOSS-for-Go | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01,PRES | MAJOR |
| 8 | Aspose.Cells-FOSS-for-Cpp | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01 | UNREVIEWED |
| 9 | Aspose.Cells-FOSS-for-Java | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01,PRES,BC12 | MAJOR |
| 10 | Aspose.Cells-FOSS-for-Python | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01,PRES | MAJOR |
| 11 | Aspose.Email-FOSS-for-.Net | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit context: identifiers that are not accepted fact values: winmail.dat | OUR_UNIVERSAL_DEFECT | IDENT | MAJOR |
| 12 | Aspose.Cells-FOSS-for-TypeScript | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01 | UNREVIEWED |
| 13 | Aspose.Email-FOSS-for-Cpp | FAILED / FAILED_INTERNAL | **RECONCILING, BC-05**: repository-presenter: validation: BC-05 failed at RECONCILING: inherited_unit:032.paragraph is deferred as UNCLASSIFIED: No deferral class matches this cause. It blocks until a class is registered in validation/deferrals.py.; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | UNCL | MAJOR |
| 14 | Aspose.Email-FOSS-for-Python | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01 | UNREVIEWED |
| 15 | Aspose.Font-FOSS-for-Python | FAILED / FAILED_INTERNAL | **S3 (repository_investigation), job:repository_investigation**: repository-presenter: repository_investigation: output truncated at the manifest's max_output_tokens (3000); raise the budget or bound the output, never retry | SAMPLING_VARIANCE (+budget borderline) | TRUNC | MINOR |
| 16 | Aspose.GIS.FOSS-for-.Net | FAILED / BLOCKED_UPSTREAM | **EXTRACTING, BC-02**: repository-presenter: validation: BC-02 failed at EXTRACTING: install_command:dotnet is CONTRADICTED: package registry: distribution not found on nuget; after one repair attempt the equivalent failure stands | UPSTREAM_DEFECT | UPSTREAM | MINOR |
| 17 | Aspose.Cells-FOSS-for-Rust | FAILED / DEFERRED(MACHINE_TOOLCHAIN) | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output truncated at the manifest's max_output_tokens (8000); raise the budget or bound the output, never retry | MACHINE_TOOLCHAIN (+SAMPLING_VARIANCE) | TOOL,TRUNC | MINOR |
| 18 | Aspose.Note-FOSS-for-Python | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit limitation:1: identifiers that are not accepted fact values: python_requires | OUR_UNIVERSAL_DEFECT | IDENT | MAJOR |
| 19 | Aspose.Imaging-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **S4 (source_reconciliation), job:source_reconciliation**: repository-presenter: source_reconciliation: output truncated at the manifest's max_output_tokens (32000); raise the budget or bound the output, never retry | SAMPLING_VARIANCE | TRUNC | MINOR |
| 20 | Aspose.HTML-FOSS-for-Python | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit summary: identifiers that are not accepted fact values: pytest.importorskip, test_css, test_cssom, test_dom, test_html, test_js (nearest accepted: test_file_io.py), test_layout, test_render, test_serialiser, test_tree, test_url | OUR_UNIVERSAL_DEFECT | IDENT,HTML | MAJOR |
| 21 | Aspose-PDF-FOSS-for-Go | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit summary: text contains HTML ('<') | OUR_UNIVERSAL_DEFECT | HTML,IDENT | MAJOR |
| 22 | Aspose.Page-FOSS-for-Python | FAILED / FAILED_INTERNAL | **RECONCILING, BC-05**: repository-presenter: validation: BC-05 failed at RECONCILING: inherited_unit:014.paragraph is deferred as UNCLASSIFIED: No deferral class matches this cause. It blocks until a class is registered in validation/deferrals.py.; no repair could act on it | OUR_UNIVERSAL_DEFECT | UNCL | MAJOR |
| 23 | Aspose-PDF-FOSS-for-Python | FAILED / FAILED_INTERNAL | **COMPOSING, BC-10**: repository-presenter: validation: BC-10 failed at COMPOSING: REJECT_PRESENTATION; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | PRES | MAJOR |
| 24 | Aspose.PDF-FOSS-for-Cpp | FAILED / DEFERRED(MACHINE_TOOLCHAIN) | **EXTRACTING, BC-02**: repository-presenter: validation: BC-02 failed at EXTRACTING: install_command:cmake is UNRESOLVED: package registry: none could not be read; no repair could act on it | MACHINE_TOOLCHAIN (+UPSTREAM_DEFECT in README examples) | TOOL | MINOR |
| 25 | Aspose.PDF-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **COMPOSING, BC-12**: repository-presenter: validation: BC-12 failed at COMPOSING: product name 'Aspose.Pdf.Foss' is not the canonical name 'Aspose.PDF FOSS for .NET'; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | BC12 | MAJOR |
| 26 | Aspose.PSD-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **EXTRACTING, BC-05**: repository-presenter: validation: BC-05 failed at EXTRACTING: inherited_unit:059.heading is deferred as NOTICES_WITHOUT_RECORD: The upstream documents licensing or third-party notices for bundled material, but no third_party_notices fact was recorded, so the attribution cannot render. Dropping attribution is a licensing risk: fix notice extraction first.; no repair could act on it | OUR_UNIVERSAL_DEFECT (+UPSTREAM_DEFECT: no LICENSE file) | NOTICE | MAJOR |
| 27 | Aspose.PDF-FOSS-for-Java | SEALED / SEALED | sealed: validation 11 pass, 1 pending (BC-11), no-op VERIFIED | OUR_UNIVERSAL_DEFECT | REV01 | UNREVIEWED |
| 28 | Aspose.PDF-FOSS-for-TypeScript | FAILED / FAILED_INTERNAL | **S4 (source_reconciliation), job:source_reconciliation**: repository-presenter: source_reconciliation: output rejected twice; last rejection: inherited_unit:353.paragraph: uncited_prose_omit: OMIT_UNSUPPORTED on a paragraph needs at least one fact ID that shows the claim unsupported, or the unit must be placed in a section the shell can hold; the unit's exact text is "Bytes are `FlateDecode`-compressed by default; pass `compress: false` to store\nthem raw. `AddFileAttachmen ... (full text in the CSV) | OUR_UNIVERSAL_DEFECT | S4OMIT | MAJOR |
| 29 | Aspose.PSD-FOSS-for-Python | FAILED / BLOCKED_UPSTREAM | **EXTRACTING, BC-02**: repository-presenter: validation: BC-02 failed at EXTRACTING: no install command fact; the source install is not verified at this revision; no repair could act on it | UPSTREAM_DEFECT (+OUR_UNIVERSAL_DEFECT x3) | UPSTREAM,UNCL,NOTICE,BC12 | MAJOR |
| 30 | Aspose.Slides-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: inherited_unit:068.paragraph: superseded into this section by reconciliation, so a unit must cite it and state its substance, or omitted must list it with a reason. Substance to carry: The three that are written are three genuinely different packages, each with its own main-part content type: | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | SUPERSEDED,IDENT,HTML,UNCL | MAJOR |
| 31 | Aspose.Slides-FOSS-for-Java | FAILED / FAILED_INTERNAL | **S6 (section_authoring), job:section_authoring**: repository-presenter: section_authoring: output rejected twice; last rejection: unit capability:7: restates its own title 'Embed images'; the title is printed immediately before the unit, so its text adds what the title does not already say; unit capability:8: restates its own title 'Apply visual effects'; the title is printed immediately before the unit, so its text adds what the title does not already say | OUR_UNIVERSAL_DEFECT | TITLE | MAJOR |
| 32 | Aspose.Slides-FOSS-for-Cpp | FAILED / FAILED_INTERNAL | **COMPOSING, BC-03**: repository-presenter: validation: BC-03 failed at COMPOSING: a cpp code block is not a planned verified example: 'pres.save("report.pdf", SaveFormat::PDF);  // throws std::in'; after one repair attempt the equivalent failure stands | OUR_UNIVERSAL_DEFECT | BC03NEG,BC12 | MAJOR |
| 33 | Aspose.Words-FOSS-for-.NET | FAILED / FAILED_INTERNAL | **S4 (source_reconciliation), job:source_reconciliation**: repository-presenter: source_reconciliation: output rejected twice; last rejection: inherited_unit:018.paragraph: uncited_prose_omit: OMIT_UNSUPPORTED on a paragraph needs at least one fact ID that shows the claim unsupported, or the unit must be placed in a section the shell can hold; the unit's exact text is "Or build from source:". Cite the supporting fact IDs or place the unit; do not omit it without a cited reas ... (full text in the CSV) | OUR_UNIVERSAL_DEFECT (+MACHINE_TOOLCHAIN: LFS) | S4OMIT,TOOL | MAJOR |
| 34 | Aspose.TeX-FOSS-for-Python | FAILED / BLOCKED_UPSTREAM | **EXTRACTING, BC-05**: repository-presenter: validation: BC-05 failed at EXTRACTING: inherited_unit:079.paragraph is deferred as NOTICES_WITHOUT_RECORD: The upstream documents licensing or third-party notices for bundled material, but no third_party_notices fact was recorded, so the attribution cannot render. Dropping attribution is a licensing risk: fix notice extraction first.; no repair could act on it | UPSTREAM_DEFECT (+OUR_UNIVERSAL_DEFECT) | UPSTREAM,NOTICE | MINOR |
| 35 | Aspose.Slides-FOSS-for-Python | FAILED / FAILED_INTERNAL | **COMPOSING, BC-10**: repository-presenter: validation: BC-10 failed at COMPOSING: REJECT_PRESENTATION; no repair could act on it | OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE) | PRES | MAJOR |
| 36 | Aspose.Words-FOSS-for-Python | FAILED / DEFERRED(MACHINE_TOOLCHAIN) | **EXTRACTING, BC-05**: repository-presenter: validation: BC-05 failed at EXTRACTING: inherited_unit:029.code_block is deferred as NO_VERIFIED_QUICK_START: Every usage example the upstream documents is unverified at this revision, so the candidate would publish with no Quick Start. An extraction failure, not a content decision: fix example verification before shipping.; no repair could act on it | MACHINE_TOOLCHAIN | TOOL,IDENT | MINOR |

## Row detail

### 1. aspose-3d-foss/Aspose.3D-FOSS-for-Java (FAILED_INTERNAL)

- Revision `3d2ed6be91f5`; attempts 1; 16 provider calls, 8.3 min.
- Co-failures and context: none reached (stops at S6 before validation).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): IDENT; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (unit_checks identifier rule, recover_section_authoring_output); repair/rounds.py (recover= wiring).
- Resume predicate: api_reference section_authoring call completes: a deterministic recover strips or rewrites an unevidenced JDK name, or a draw that never writes one.
- Upstream handoff: none.
- Would a redraw differ? low odds: attempt 1 and attempt 2 rejected the same unit for the same name 'ArrayList' (the 40-unit api_reference batch fails as a whole on one unit; the repository has 5,366 public symbols, so many such batches exist); G7-W23 note records 'ArrayList beside ArrayListAdapter, 3D-Java' as left unfixed by design.
- Evidence: calls/d4499ff1de77.rejected-1/2.json. One unit in a 40-unit api_reference batch; a title-restatement rejection in call 9d72309090c6 was recovered.

### 2. aspose-3d-foss/Aspose.3D-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `52b0f00ebf28`; attempts 1; 33 provider calls, 14.0 min.
- Co-failures and context: BC-12 FAIL scope_limitations: product name 'Aspose.3D FOSS' is not the canonical name 'Aspose.3D FOSS for .NET' (3 repairs, re-raised); BC-10/BC-11 pending.
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): UNCL,BC12; change size **MAJOR**.
- Fix belongs in: validation/deferrals.py + reconciliation/dispositions.py (model free-text DEFER_UNRESOLVED); validation/registry.py BC-12 + composition/authoring.py recover.
- Resume predicate: BC-05 and BC-12 pass on a draw (the unit 066 deferral is draw-dependent: see the redraw note).
- Upstream handoff: evidence/upstream-defects/aspose-3d-foss__Aspose.3D-FOSS-for-.NET/ad94a06d...json (BC-03 README example does not compile; not the cause).
- Would a redraw differ? plausible: DEFECT_INDEX REG-18 records this repository READY_FOR_PROPOSAL with a zero-call no-op in the G7-W12 session (code of that session, not proven identical to the baseline); unit 066 ('The console converter tool builds separately...') was deferred with the free-text rationale 'public use is uncertain per uncertainties'.
- Evidence: validation.json BC-05 (1 failure) + BC-12; dispositions.json inherited_unit:066.paragraph.

### 3. aspose-3d-foss/Aspose.3D-FOSS-for-Python (SEALED)

- Revision `65b1f577c0f1`; attempts 1; 29 provider calls, 17.1 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 17 advisories, all carry reviewer_scope_defect).
- Independent review: DO_NOT_PROPOSE (baseline; acceptance file section 5): 5 introduced false or misleading claims (PolygonBuilder triangulates, COLLADA/FBX write, textured crate, 34 test files, type counts), 2 dangling lead-ins, duplicated docs list.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01,PRES; change size **MAJOR**.
- Fix belongs in: review/independent/review.py (demotion); composition/authoring.py (carry of lead-ins and counts); validation/claims.py (capability claims).
- Resume predicate: TC-ACC-01 comparison on the cut's candidate passes; REJECT stands (REV-01) so the demoted findings are repaired, not shipped.
- Upstream handoff: evidence/upstream-defects/aspose-3d-foss__Aspose.3D-FOSS-for-Python/094c4163...json (BC-03, README example fails; not the cause).
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). Slice pilot e38cabc2 re-sealed it but the independent review still says DO_NOT_PROPOSE (false .dae export).

### 4. aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python (SEALED)

- Revision `06eca5c01e13`; attempts 1; 14 provider calls, 11.4 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 9 advisories, 7 with reviewer_scope_defect).
- Independent review: DO_NOT_PROPOSE (acceptance file section 1): garbled 'member AUTO, member H', false 'QrErrorCorrectionLevel supports AUTO and H', '48 test files' counts non-tests, Enterprise paragraph and pytest/ruff commands dropped.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01,PRES; change size **MAJOR**.
- Fix belongs in: review/independent/review.py; composition/authoring.py and renderer (member-list garble); reconciliation/dispositions.py (Enterprise row, TC-DSP-01).
- Resume predicate: independent comparison passes on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). Slice pilot: FAILED BC-10 (REJECT now stands).

### 5. aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (SEALED)

- Revision `66cb26df3b03`; attempts 1; 33 provider calls, 19.6 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_FACTUAL; 32 advisories, 30 factuality, all carry reviewer_scope_defect).
- Independent review: not yet reviewed (TC-ACC-01 pending). Known risk: the opening states 'The package @aspose/3d version 24.12.0' although handoff a6f52c1a says the package is not on npm under its declared name (unsupported public claim; TC-CLM-01 BC-14).
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01; change size **UNREVIEWED**.
- Fix belongs in: validation/claims.py (BC-14 published-version); review/independent/review.py.
- Resume predicate: TC-ACC-01 record; the version claim removed or evidenced.
- Upstream handoff: evidence/upstream-defects/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript/9264bf05...json (BC-03) and a6f52c1a...json (BC-02, npm 404).
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). First seal of an entry G5-W08 lists as having no candidate.

### 6. aspose-cells-foss/Aspose.Cells-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `941814fd138d`; attempts 1; 43 provider calls, 21.2 min.
- Co-failures and context: BC-11 pending.
- Review: REJECT_PRESENTATION (stands, not demoted; 2 findings).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): PRES; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (development_testing carries the build_test_asset:examples units); reconciliation/dispositions.py (TC-DSP-01, on integration); repair/targeted.py.
- Resume predicate: BC-10 ACCEPT on a draw whose Development and Testing keeps 'Run a sample from the repository root' and 'PDF export sample'.
- Upstream handoff: evidence/upstream-defects/aspose-cells-foss__Aspose.Cells-FOSS-for-.NET/7e755ed8...json (BC-03; not the cause).
- Would a redraw differ? plausible: reviewer found only 2 findings (F05, F06), both TRUE omissions of the upstream's sample commands; 2 of 3 repairs landed (F03, F06) and re-raised; 1 misrouted.
- Evidence: review.json verdict_as_returned REJECT_PRESENTATION, second reader not triggered; repairs.json.

### 7. aspose-cells-foss/Aspose.Cells-FOSS-for-Go (SEALED)

- Revision `99c789e9175f`; attempts 1; 21 provider calls, 15.4 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 16 advisories, 15 with reviewer_scope_defect).
- Independent review: DO_NOT_PROPOSE (acceptance file section 4): dangling 'Run every bundled example program:', garbled 'Cell.Ref and Cell.XMLName', Enterprise paragraph, go test commands, Picture dropped.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01,PRES; change size **MAJOR**.
- Fix belongs in: review/independent/review.py; composition/authoring.py (lead-in without block); reconciliation/dispositions.py.
- Resume predicate: independent comparison passes on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). Slice pilot: FAILED BC-10.

### 8. aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp (SEALED)

- Revision `9f852d0ff1cf`; attempts 1; 39 provider calls, 23.6 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_FACTUAL; 15 factuality advisories, all with reviewer_scope_defect, F01 targets the 'verified source build' install claim).
- Independent review: not yet reviewed (TC-ACC-01 pending).
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01; change size **UNREVIEWED**.
- Fix belongs in: review/independent/review.py.
- Resume predicate: TC-ACC-01 record on the cut candidate; the install claim rests on the private toolchain registry's vcvarsall (MSVC fallback), so it holds only on this machine class.
- Upstream handoff: evidence/upstream-defects/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/3f1b3176...json and b3df5761...json (BC-02 upstream build failures, CONFIRMED; not the cause).
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun).

### 9. aspose-cells-foss/Aspose.Cells-FOSS-for-Java (SEALED)

- Revision `c65329e7257b`; attempts 1; 29 provider calls, 12.3 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 19 advisories, all with reviewer_scope_defect).
- Independent review: DO_NOT_PROPOSE (acceptance file section 3): empty API table yet claims the full 183-type surface, invented audience, pom/Gradle install replaced by 'mvn dependency:get'.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01,PRES,BC12; change size **MAJOR**.
- Fix belongs in: review/independent/review.py; composition/authoring.py and renderer (API table); validation/registry.py.
- Resume predicate: independent comparison passes on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). BC-12 fired once and was repaired. Slice pilot: FAILED BC-10.

### 10. aspose-cells-foss/Aspose.Cells-FOSS-for-Python (SEALED)

- Revision `4f6768a7b349`; attempts 1; 17 provider calls, 10.8 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 15 advisories, all with reviewer_scope_defect).
- Independent review: DO_NOT_PROPOSE (acceptance file section 2): CSV described as export-only (load_csv exists), diagram and opening drop JSON/Markdown/AutoFilter/charts, Enterprise paragraph dropped, filler member lines.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01,PRES; change size **MAJOR**.
- Fix belongs in: review/independent/review.py; composition/authoring.py; reconciliation/dispositions.py.
- Resume predicate: independent comparison passes on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun). Slice pilot: FAILED BC-10.

### 11. aspose-email-foss/Aspose.Email-FOSS-for-.Net (FAILED_INTERNAL)

- Revision `59125b4732df`; attempts 1; 21 provider calls, 8.5 min.
- Co-failures and context: none reached.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): IDENT; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (identifier rule admits a name quoted by a cited, SUPPORTED inherited unit even when absent from the tree, or recover drops the clause).
- Resume predicate: enterprise_relationship / scope_limitations call passes S6.
- Upstream handoff: none.
- Would a redraw differ? low odds: 'winmail.dat' is in the upstream README twice (lines 285, 292) and in three separate S6 calls; G7-W23 records 'winmail.dat (Email-.NET; the re-ask drops it)' as left unfixed, and here the re-ask did not drop it.
- Evidence: calls/0bc4856a6613.rejected-1/2.json and 708352d207aa.rejected-1.json. Also an S4 uncited_prose_omit rejection (call dab7c483fc4d) that the re-ask recovered.

### 12. aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript (SEALED)

- Revision `fc186507e5b7`; attempts 1; 24 provider calls, 13.0 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 8 advisories, all with reviewer_scope_defect; second reader not triggered).
- Independent review: not yet reviewed (TC-ACC-01 pending). Known risk: opening states 'version 1.0.0'.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01; change size **UNREVIEWED**.
- Fix belongs in: review/independent/review.py; validation/claims.py.
- Resume predicate: TC-ACC-01 record on the cut candidate.
- Upstream handoff: evidence/upstream-defects/aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript/c04f74bf...json (BC-02; not the cause).
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun).

### 13. aspose-email-foss/Aspose.Email-FOSS-for-Cpp (FAILED_INTERNAL)

- Revision `c844a467cf7f`; attempts 1; 31 provider calls, 13.0 min.
- Co-failures and context: BC-10/BC-11 pending (BC-02 passes: MSVC fallback proves the build).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): UNCL; change size **MAJOR**.
- Fix belongs in: validation/deferrals.py; reconciliation/dispositions.py (a unit with 2 cited link facts and 'no section is available to place it').
- Resume predicate: BC-05 passes: units 032/069 placed or classified.
- Upstream handoff: evidence/upstream-defects/aspose-email-foss__Aspose.Email-FOSS-for-Cpp/7f0f3388...json (BC-02 upstream build failure; not the cause).
- Would a redraw differ? plausible: unit 032 and 069 describe the same examples/ directory; 069 was placed (VERIFIED_PRESERVE), 032 deferred; one BC-05 repair landed, two UNCLASSIFIED remain.
- Evidence: validation.json BC-05 (2 failures); dispositions.json.

### 14. aspose-email-foss/Aspose.Email-FOSS-for-Python (SEALED)

- Revision `10a906b48c0c`; attempts 1; 26 provider calls, 12.4 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 9 advisories, 8 with reviewer_scope_defect).
- Independent review: not yet reviewed (TC-ACC-01 pending).
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01; change size **UNREVIEWED**.
- Fix belongs in: review/independent/review.py.
- Resume predicate: TC-ACC-01 record on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun).

### 15. aspose-font-foss/Aspose.Font-FOSS-for-Python (FAILED_INTERNAL)

- Revision `adf4885a3a5d`; attempts 1; 2 provider calls, 2.5 min.
- Co-failures and context: none reached (stops at S3).
- Class: SAMPLING_VARIANCE (+budget borderline); mechanism(s): TRUNC; change size **MINOR**.
- Fix belongs in: redraw first; if it repeats: prompts/repository_investigation.yaml max_output_tokens (3000) and core/llm/jobs.py (TruncatedOutput gets one re-ask).
- Resume predicate: repository_investigation returns a complete reply inside 3000 tokens.
- Upstream handoff: 4 handoffs exist (BC-06 0dcf9304, BC-03 52ba0e1d and dc90b681, BC-02 a241746e); none is the cause.
- Would a redraw differ? plausible: the rejected body is 13,074 characters of valid JSON cut at the 3000-token cap (a long list of 18 UNRESOLVED facts); the same request length varies by sample (RESEARCH_LANE_F F24: 8000, truncation and 431 tokens for one request hash).
- Evidence: calls/ba605653fa64.rejected-1.json. Font was sealed in #259 on older code.

### 16. aspose-gis-foss/Aspose.GIS.FOSS-for-.Net (BLOCKED_UPSTREAM)

- Revision `b9b8c9c760bf`; attempts 1; 24 provider calls, 4.3 min.
- Co-failures and context: BC-12 FAIL api_reference and development_testing ('Aspose.GIS.FOSS' vs 'Aspose.GIS.FOSS for .Net'); BC-10/BC-11 pending.
- Class: UPSTREAM_DEFECT; mechanism(s): UPSTREAM; change size **MINOR**.
- Fix belongs in: no code: upstream. Expected typed class NON_PROCESSABLE (README_MISSING + build fails) has no producer yet (plan SOURCE_UNPARSEABLE / README_MISSING card).
- Resume predicate: upstream commit where `dotnet build Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj` exits 0 and a README and LICENSE exist; or the README_MISSING producer lands and types the entry NON_PROCESSABLE.
- Upstream handoff: NONE EXISTS: draft needed (BC-02/NOT_PROCESSABLE). Re-verified here: pinned revision b9b8c9c7 ('Second part') builds with 369 errors (CS0246, missing types Unit, Projection, Axis, PointsSequence, Identifier), no README, no LICENSE, no NuGet package.
- Would a redraw differ? no: deterministic (build fails, registry says not found).
- Evidence: facts.json install_command:dotnet CONTRADICTED; present-1.out 'readme absent', 'build: failed'; my read-only `dotnet build` of a scratch copy reproduced the exit 1.

### 17. aspose-cells-foss/Aspose.Cells-FOSS-for-Rust (DEFERRED(MACHINE_TOOLCHAIN))

- Revision `1a6004af47b1`; attempts 1; 38 provider calls, 32.3 min.
- Co-failures and context: run 1 produced a complete bundle: validation 11 pass, review ACCEPT (converted from REJECT_PRESENTATION), state INVALIDATED awaiting the zero-call rerun.
- Review: ACCEPT in run 1 (converted from REJECT_PRESENTATION).
- Class: MACHINE_TOOLCHAIN (+SAMPLING_VARIANCE); mechanism(s): TOOL,TRUNC; change size **MINOR**.
- Fix belongs in: machine: make cargo example verification deterministic across processes (link.exe or a gnu toolchain on the subprocess PATH; examples.json shows 'failed to run custom build command for num-traits v0.2.19'); then redraw. Durable: core/llm/jobs.py truncation re-ask.
- Resume predicate: a run whose zero-call rerun adopts the waiting update (facts digest identical in both processes).
- Upstream handoff: none.
- Would a redraw differ? yes: run 1 'examples: executed 1, not_verified 6'; run 2 'not_verified 7' (facts digest 0a6a2af6... vs 917b51e3...), so the update was not reproducible, the rerun re-entered at EXTRACTING and the S6 api_reference intro ran away repeating fact ids to 8000 tokens (33,604 characters).
- Evidence: reseal-logs present-1.out/present-2.out; calls/1c3187b2c77a.rejected-1.json. Cargo registry in a machine with parallel builds may race; cause of the one executed example not established.

### 18. aspose-note-foss/Aspose.Note-FOSS-for-Python (FAILED_INTERNAL)

- Revision `17b5d7fe2002`; attempts 1; 26 provider calls, 13.9 min.
- Co-failures and context: none reached.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): IDENT; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (identifier rule and recover; packaging-metadata keys); evidence/facts for unrecorded members (Style.IsHyperlink is surface.members_*).
- Resume predicate: limitation call passes S6.
- Upstream handoff: none.
- Would a redraw differ? moderate: three different S6 calls each rejected on different names (python_requires, pdf_golden_failures, Path.mkdir, Style.HyperlinkAddress, Style.IsHyperlink) and one on a missing example slot; final stop 'python_requires' is a packaging key the model wrote from background knowledge.
- Evidence: calls/097393d943fa.rejected-1/2.json, 9b207ba7aa78, b6504ce97f3d.

### 19. aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `6ebb2091ad01`; attempts 1; 8 provider calls, 16.0 min.
- Co-failures and context: none reached (stops at S4).
- Class: SAMPLING_VARIANCE; mechanism(s): TRUNC; change size **MINOR**.
- Fix belongs in: redraw; durable: core/llm/jobs.py (re-ask on TruncatedOutput; PROPOSAL T) and prompts/source_reconciliation.yaml output bound.
- Resume predicate: source_reconciliation completes on a draw.
- Upstream handoff: evidence/upstream-defects/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET/2c99dc76...json (BC-02; not the cause).
- Would a redraw differ? yes: attempt 2 emitted 18 valid dispositions then 51,743 characters of whitespace to the 32000-token cap (degenerate decode, not a long answer); attempt 1 was an uncited_prose_omit rejection that the re-ask would normally fix.
- Evidence: calls/53d5e87abd54.rejected-1/2.json. Sighting 4 of s4_reconciliation.output_runaway_past_budget.

### 20. aspose-html-foss/Aspose.HTML-FOSS-for-Python (FAILED_INTERNAL)

- Revision `bf0f1e7a6d29`; attempts 1; 37 provider calls, 23.9 min.
- Co-failures and context: none reached.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): IDENT,HTML; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (identifier rule for directory names test_html/ ... and pytest.importorskip; HTML-element names in api_reference; recover); evidence/facts/repository_files.py (directory tokens).
- Resume predicate: development_testing call passes S6 (superseded units 096/097 carried without unevidenced names).
- Upstream handoff: evidence/upstream-defects/aspose-html-foss__Aspose.HTML-FOSS-for-Python/ae9f06b9...json (BC-02 pip install; not the cause).
- Would a redraw differ? moderate: six separate S6 rejections across calls (HTMLAddressElement '<address>' prose x2 calls, document.querySelector, test_* dirs); the final stop is a carried inherited unit naming test directories.
- Evidence: calls/c2a4e73e7887.rejected-2.json, 22122970627c, d304031a8927. G7-W23 admits file-like tokens only, not bare directory names.

### 21. aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (FAILED_INTERNAL)

- Revision `cdf43df10c8c`; attempts 1; 29 provider calls, 12.6 min.
- Co-failures and context: none reached.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): HTML,IDENT; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (_bare_angle_bracket: recover wraps a placeholder path in a code span).
- Resume predicate: development_testing call passes S6.
- Upstream handoff: none.
- Would a redraw differ? plausible: the model dropped the backticks around `_examples/<name>/main.go` on both attempts; earlier calls also tripped io.Writer identifiers and coherence drops (recovered).
- Evidence: calls/09a519cad704.rejected-1/2.json. G4-W17 item 46 exempted code spans only.

### 22. aspose-page-foss/Aspose.Page-FOSS-for-Python (FAILED_INTERNAL)

- Revision `43cef367cd0b`; attempts 1; 34 provider calls, 16.1 min.
- Co-failures and context: BC-10/BC-11 pending.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): UNCL; change size **MAJOR**.
- Fix belongs in: validation/deferrals.py; evidence/facts/assets.py (package.py build and wheel workflow recorded as build_test_asset).
- Resume predicate: BC-05 passes: units 014, 016, 038, 040 classified or placed.
- Upstream handoff: none.
- Would a redraw differ? low: the four units are README build/publish steps ('python package.py publish-test') and PS/XPS conversion lead-ins with no supporting fact; the model defers them deterministically with free text.
- Evidence: validation.json BC-05 (4 failures); dispositions.json. REG-18 notes Page-Python 015 folded live then BC-10 REJECT_FACTUAL in an earlier session.

### 23. aspose-pdf-foss/Aspose-PDF-FOSS-for-Python (FAILED_INTERNAL)

- Revision `8f0edbe6930f`; attempts 1; 31 provider calls, 23.0 min.
- Co-failures and context: BC-11 pending.
- Review: REJECT_PRESENTATION (second reader; 1 finding).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): PRES; change size **MAJOR**.
- Fix belongs in: composition/authoring.py + reconciliation/dispositions.py (scope_limitations keeps JPEG 2000, SVG polylines, RSA-only encryption limits); repair/targeted.py.
- Resume predicate: BC-10 ACCEPT with those limits present.
- Upstream handoff: none.
- Would a redraw differ? plausible: first reader returned ACCEPT, the 3-reader second pass REJECT_PRESENTATION; F06 is a TRUE omission of three limitations the original README states.
- Evidence: review.json verdict ACCEPT-as-returned then REJECT_PRESENTATION by second reader; repairs.json F06 repaired and re-raised.

### 24. aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp (DEFERRED(MACHINE_TOOLCHAIN))

- Revision `4b83c9fec1e3`; attempts 1; 33 provider calls, 20.1 min.
- Co-failures and context: BC-10/BC-11 pending.
- Class: MACHINE_TOOLCHAIN (+UPSTREAM_DEFECT in README examples); mechanism(s): TOOL; change size **MINOR**.
- Fix belongs in: machine: give the winlibs cmake a CA bundle (CMAKE_TLS_CAINFO) or use the MSVC cmake; if the runner's sanitized env cannot carry it, extractors/platforms/cpp_examples.py must try MSVC after a configure failure, not only after a build failure.
- Resume predicate: `cmake -S . -B build -G Ninja` configures on this machine so the build is verified and install_command becomes SUPPORTED.
- Upstream handoff: none for the README examples: 2 examples FAIL with 'incomplete type Aspose::Pdf::Paragraphs / PageCollection' (missing includes); draft a BC-03 handoff.
- Would a redraw differ? no: deterministic.
- Reproduced in a scratch copy: FetchContent googletest download fails with 'SSL ... no trust anchors configured' (status_code 60) under winlibs cmake 4.4.2. examples.json: 'the library's own CMake build configure failed'. Cells-Cpp's library configure fetches nothing (FetchContent is only in its Tests subproject) and its build fell back to MSVC.

### 25. aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `10a363830fea`; attempts 1; 48 provider calls, 32.2 min.
- Co-failures and context: none other: every other check passes; BC-10/BC-11 pending (never judged).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): BC12; change size **MAJOR**.
- Fix belongs in: validation/registry.py BC-12 (exempt a namespace/package identifier written as a symbol) and composition/authoring.py recover (deterministic canonical-name rewrite).
- Resume predicate: BC-12 passes on a draw or deterministically; then BC-10 decides.
- Upstream handoff: none.
- Would a redraw differ? plausible: one BC-12 repair landed and one re-raised; the name 'Aspose.Pdf.Foss' is the namespace (a SUPPORTED public_symbol) used as a subject in development_testing.
- Evidence: validation.json BC-12 section development_testing; repairs.json. Sole blocker.

### 26. aspose-psd-foss/Aspose.PSD-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `85ed7eec7c80`; attempts 1; 23 provider calls, 9.2 min.
- Co-failures and context: BC-10/BC-11 pending.
- Class: OUR_UNIVERSAL_DEFECT (+UPSTREAM_DEFECT: no LICENSE file); mechanism(s): NOTICE; change size **MAJOR**.
- Fix belongs in: validation/deferrals.py (_NOTICES must not match a plain License heading or MIT paragraph); a LICENSE file upstream so a license fact exists (facts.json has no license kind).
- Resume predicate: BC-05 passes for inherited_unit:059.heading '## License' and 060 (MIT paragraph).
- Upstream handoff: none: draft optional (README License section, no LICENSE file in the tree).
- Would a redraw differ? no: the matcher fires on text, not on a sample; G7-W12 also left PSD-.NET 034 open.
- Evidence: validation.json BC-05; dispositions.json rationale 'superseded by the License section'.

### 27. aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (SEALED)

- Revision `736cedaa2922`; attempts 1; 40 provider calls, 28.3 min.
- Review verdict as sealed: ACCEPT (converted from REJECT_PRESENTATION; 6 advisories, all with reviewer_scope_defect; second reader not triggered).
- Independent review: not yet reviewed (TC-ACC-01 pending).
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): REV01; change size **UNREVIEWED**.
- Fix belongs in: review/independent/review.py.
- Resume predicate: TC-ACC-01 record on the cut candidate.
- Upstream handoff: none.
- Evidence: noop proof VERIFIED (zero-call byte-identical rerun).

### 28. aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript (FAILED_INTERNAL)

- Revision `c672b3918318`; attempts 1; 29 provider calls, 23.4 min.
- Co-failures and context: none reached; also 104 of 117 README example fences FAIL (unbound names) which will meet BC-03/BC-05 next.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): S4OMIT; change size **MAJOR**.
- Fix belongs in: reconciliation/dispositions.py (recover_uncited_prose_omits: partial recovery, and do not treat the brand word or a class named like an English noun as a spelled SUPPORTED symbol).
- Resume predicate: source_reconciliation passes both attempts or recover applies.
- Upstream handoff: evidence/upstream-defects/aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript/ef667e7d...json (BC-02 npm 404; separate).
- Would a redraw differ? low: attempt 2 still rejected 19 units; 117 examples and 541 inherited units make a clean sample unlikely.
- Evidence: calls/ed358f8428e6.rejected-1/2.json (e.g. public_symbol:attachment). Without a clean draw recover returns None (all-or-nothing).

### 29. aspose-psd-foss/Aspose.PSD-FOSS-for-Python (BLOCKED_UPSTREAM)

- Revision `dbc90f46f7ef`; attempts 1; 27 provider calls, 11.8 min.
- Co-failures and context: BC-05 FAIL (10 failures: UNCLASSIFIED headings 'Dependencies', NOTICES_WITHOUT_RECORD), BC-12 FAIL api_reference ('Aspose.PSD FOSS' vs '... for Python'); BC-10/BC-11 pending.
- Class: UPSTREAM_DEFECT (+OUR_UNIVERSAL_DEFECT x3); mechanism(s): UPSTREAM,UNCL,NOTICE,BC12; change size **MAJOR**.
- Fix belongs in: no code for BC-02: the tree has only README.md, aspose_psd_foss/, aspose_psd_foss_test/ (no pyproject, setup, LICENSE); the README documents a PYTHONPATH install from a clone. Code: validation/deferrals.py, validation/registry.py BC-12.
- Resume predicate: upstream adds packaging metadata and a LICENSE (or the extractor admits the README-documented PYTHONPATH source install), and the three co-failing mechanisms are fixed.
- Upstream handoff: NONE EXISTS: draft needed (BC-02 install unverifiable; no LICENSE).
- Would a redraw differ? no.
- Evidence: facts.json has no install_command, license or package kind; present-1.out 'examples: 4 candidates; executed 2, failed 2'. README grew from 2 lines (preflight 664446b9) to 372 lines at dbc90f46 (upstream pushed 2026-10-10).

### 30. aspose-slides-foss/Aspose.Slides-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `86c441b5d81e`; attempts 2; 23 provider calls, 10.9 min.
- Co-failures and context: attempt 1 (16:37Z) stopped at BC-05 UNCLASSIFIED (6 units: 014, 015, 018, 019 ...); attempt 2 (19:35Z, this row) at S6.
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): SUPERSEDED,IDENT,HTML,UNCL; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (carried_unit_errors; section_selections for superseded units into every placeable section; identifier and HTML recover); validation/deferrals.py.
- Resume predicate: limitation call carries units 068/074/076 or omits them with reasons, and passes S6.
- Upstream handoff: none.
- Would a redraw differ? False.
- Evidence: calls/0206e4205674.rejected-1/2.json (slides-net-2 archive); slides-net archive for attempt 1. REG-22 family (Slides-Java).

### 31. aspose-slides-foss/Aspose.Slides-FOSS-for-Java (FAILED_INTERNAL)

- Revision `620a26144188`; attempts 1; 28 provider calls, 11.9 min.
- Co-failures and context: none reached.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): TITLE; change size **MAJOR**.
- Fix belongs in: composition/authoring.py (recover_title_verbatim_opening / recover_section_authoring_output must cover capability slots whose text restates a verb-object title).
- Resume predicate: key_capabilities call passes S6 (capability:7 'Embed images', capability:8 'Apply visual effects').
- Upstream handoff: none.
- Would a redraw differ? low: both attempts and two separate calls (e8a829c1dc81, df1d40795f8f) rejected the same two slots; this is sighting 5+ of the index entry.
- Evidence: calls/df1d40795f8f.rejected-1/2.json. Index says all three sub-shapes are fixed; the recurrence says the title-restatement fix does not cover this slot shape.

### 32. aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp (FAILED_INTERNAL)

- Revision `469ce77a07b9`; attempts 1; 34 provider calls, 19.7 min.
- Co-failures and context: BC-12 FAIL api_reference ('Aspose.Slides.Foss' vs 'Aspose.Slides FOSS for Cpp'; one repair landed, re-raised); BC-10/BC-11 pending.
- Class: OUR_UNIVERSAL_DEFECT; mechanism(s): BC03NEG,BC12; change size **MAJOR**.
- Fix belongs in: validation/registry.py BC-03 (do not treat a fence inside a verbatim-preserved inherited unit as a rendered example); repair/rounds.py (a defect with no LLM-owned section must route to the placing stage).
- Resume predicate: BC-03 passes: inherited_unit:102.list keeps its counter-example without an unverified-example verdict.
- Upstream handoff: none.
- Would a redraw differ? no: unit 102.list is VERBATIM preserved; repair reports 'no failing check names an LLM-owned section'.
- Evidence: README.md line 436 `pres.save("report.pdf", SaveFormat::PDF);  // throws std::invalid_argument`; repairs.json.

### 33. aspose-words-foss/Aspose.Words-FOSS-for-.NET (FAILED_INTERNAL)

- Revision `0d3f1add920f`; attempts 1; 5 provider calls, 6.3 min.
- Co-failures and context: none reached; next stop would be the build: `dotnet build Aspose.Words/Aspose.Words.csproj` exits 1 (5 of 5 examples FAILED, CS0234 Aspose.JavaAttributes) because the plain clone holds 6,634 git-LFS pointer files (packages/Aspose.JavaAttributes/lib/net2.0/Aspose.JavaAttributes.dll).
- Class: OUR_UNIVERSAL_DEFECT (+MACHINE_TOOLCHAIN: LFS); mechanism(s): S4OMIT,TOOL; change size **MAJOR**.
- Fix belongs in: reconciliation/dispositions.py (recover_uncited_prose_omits declines because the units spell public_symbol:aspose, the brand word); runner: fetch LFS objects (git lfs pull) in the plain clone.
- Resume predicate: source_reconciliation passes and the LFS build succeeds.
- Upstream handoff: none.
- Would a redraw differ? low: attempts 1 and 2 both rejected install-step lead-ins ('Or build from source:') that spell the brand word.
- Evidence: calls/cc6158eda3eb.rejected-1/2.json; examples.json; git lfs ls-files in the clone.

### 34. aspose-tex-foss/Aspose.TeX-FOSS-for-Python (BLOCKED_UPSTREAM)

- Revision `181015d2eee3`; attempts 1; 25 provider calls, 7.6 min.
- Co-failures and context: BC-10/BC-11 pending.
- Class: UPSTREAM_DEFECT (+OUR_UNIVERSAL_DEFECT); mechanism(s): UPSTREAM,NOTICE; change size **MINOR**.
- Fix belongs in: no code needed for the typed outcome. For a seal: upstream parse fixes; evidence/facts (record LICENSE-FONTS as third_party_notices).
- Resume predicate: upstream fixes the 35 of 45 src/aspose_tex files that do not parse (handoff c00f9615), or the NOT_PROCESSABLE producer types it.
- Upstream handoff: evidence/upstream-defects/aspose-tex-foss__Aspose.TeX-FOSS-for-Python/c00f9615...json (NOT_PROCESSABLE, HANDOFF_PENDING).
- Would a redraw differ? no.
- Evidence: validation.json BC-05 NOTICES_WITHOUT_RECORD on 079.paragraph ('Bundled Computer Modern fonts ... font license file'); facts.json has license but no third_party_notices though LICENSE-FONTS exists in the tree. preflight: 1 of 10 examples executed, 9 IndentationError.

### 35. aspose-slides-foss/Aspose.Slides-FOSS-for-Python (FAILED_INTERNAL)

- Revision `4e63447ba79d`; attempts 1; 40 provider calls, 19.9 min.
- Co-failures and context: BC-11 pending.
- Review: REJECT_PRESENTATION (stands; 1 finding, 3 readers).
- Class: OUR_UNIVERSAL_DEFECT (+SAMPLING_VARIANCE); mechanism(s): PRES; change size **MAJOR**.
- Fix belongs in: validation/claims.py (BC-14: an overclaim such as 'the full presentation object model'); composition/planning.py (plan-level repair).
- Resume predicate: BC-10 ACCEPT without the overclaim.
- Upstream handoff: none.
- Would a redraw differ? plausible: single finding F08 (S7 scope) is TRUE; 3 readers agreed; plan-level repair escalated but 'no repair could act'.
- Evidence: review.json F08; repairs.json F08 escalated and unrepairable.

### 36. aspose-words-foss/Aspose.Words-FOSS-for-Python (DEFERRED(MACHINE_TOOLCHAIN))

- Revision `2d2efee2787c`; attempts 2; 26 provider calls, 12.1 min.
- Co-failures and context: attempt 1 (16:37Z) stopped at S6 on 'OoxmlCompliance.ISO29500_2008_STRICT' (an enum member no fact records); attempt 2 (20:03Z, this row) at BC-05.
- Class: MACHINE_TOOLCHAIN; mechanism(s): TOOL,IDENT; change size **MINOR**.
- Fix belongs in: machine: a Python 3.10 to 3.12 interpreter in the pinned toolchain registry (requires-python '>=3.10,<3.13'; this machine has only 3.13.2).
- Resume predicate: 12 README examples verify, so a Quick Start exists and NO_VERIFIED_QUICK_START clears; expect the surface.members_* mechanism to meet attempt-1 style rejections next.
- Upstream handoff: none.
- Would a redraw differ? no for BC-05: identical in the slice pilot e38cabc2 and in the TC-PRE-01 facts-only reading (12 of 12 NOT_VERIFIED).
- Evidence: examples.json 12/12 NOT_VERIFIED 'no interpreter satisfies requires-python'; validation.json BC-05. Preflight predicted it.

## Ranked mechanism table

Ranked by repositories carrying evidence of the mechanism in this run. `stops / co / seen` as defined above. Three or more is settled priority.

| Rank | Mechanism (DEFECT_INDEX status) | Repositories | stops / co / seen | Change | Fix location | Settled (>=3) |
|---|---|---|---|---|---|---|
| 1 | `REV01`: PROPOSED review.reject_demoted_to_accept_by_scope_defect_label; fixed on integration by e482390b (TC-REV-01), not in baseline - a returned REJECT is converted to ACCEPT by reviewer_scope_defect labels, so SEALED does not mean reviewed-good | Cells-Cpp, Cells-Go, Cells-Java, Cells-Python, Cells-TypeScript, Cells-Rust (run 1), 3D-Python, 3D-TypeScript, BarCode-Python, Email-Python, PDF-Java | 0 / 0 / 11 (11 of 11 REJECT-first bundles converted) | MAJOR (landed on integration, e482390b) | review/independent/review.py (demotion rule) | yes |
| 2 | `PRES`: PROPOSED composition.inherited_valuable_content_dropped_repair_cannot_restore (related composition.coherence.inherited_diagram_content_loss, composition.authoring.superseded_unit_not_carried); TC-DSP-01 a9877f96 on integration, not in baseline - valuable inherited upstream content (test/sample commands, limitation detail, Enterprise paragraph) is superseded or dropped and one repair round cannot restore it | BarCode-Python, Cells-Python, Cells-Java, Cells-Go, 3D-Python (acceptance: dropped_live_content); Cells-.NET, PDF-Python (BC-10 stops, true omissions) | 2 / 0 / 7 (+ Slides-Python overclaim) | MAJOR (TC-DSP-01 on integration, partial) | reconciliation/dispositions.py; composition/authoring.py (development_testing, scope_limitations); repair/targeted.py | yes |
| 3 | `IDENT`: PROPOSED section_authoring.identifier_refusal_exhausts_both_attempts (related readme.dotted_file_name_in_prose_not_a_recorded_fact G7-W23, surface.members_the_source_defines_are_not_recorded_as_facts, section_authoring.rejection_no_recover) - the identifier rule refuses a name that is not a fact value (stdlib or JDK type, external file, packaging key, unrecorded member); the re-ask repeats it; no deterministic recover; the whole section call fails | 3D-Java (ArrayList), Email-.NET (winmail.dat), HTML-Python (test_* dirs, pytest.importorskip), Note-Python (python_requires), Words-Python attempt 1 (OoxmlCompliance enum member) | 4 / 0 / 19 repositories rejected at least once | MAJOR | composition/authoring.py (unit_checks, recover_section_authoring_output); repair/rounds.py; evidence/facts (members, directory tokens) | yes |
| 4 | `S4OMIT`: PROPOSED reconciliation.recover_uncited_prose_omits_declines_on_brand_word_symbol (REG-18 follow-up, G7-W12) - S4 uncited_prose_omit survives the re-ask; recover_uncited_prose_omits declines all-or-nothing because a unit spells a SUPPORTED symbol that is only the brand word (public_symbol:aspose.*) | Words-.NET, PDF-TypeScript (stops); PSD-.NET (G7-W12 session) | 2 / 0 / 27 repositories rejected at least once | MAJOR | reconciliation/dispositions.py::recover_uncited_prose_omits (all-or-nothing decline on a brand-word symbol) | yes (2 here + 1 earlier) |
| 5 | `UNCL`: REG-18 / G7-W12 (existing, PENDING) - BC-05 UNCLASSIFIED: a model-authored DEFER_UNRESOLVED with free-text rationale matches no registered deferral class (the #328 class matches only the typed recovery prefix) | 3D-.NET, Email-Cpp, Page-Python (stops); Slides-.NET attempt 1; PSD-Python (co) | 3 / 1 / 5 | MAJOR (not covered by #328: free-text rationales, not the typed prefix) | validation/deferrals.py; reconciliation/dispositions.py | yes (REG-18 open) |
| 6 | `BC12`: readme.canonical_name_enforced_only_in_renderer_slots (REV-V2-04, fixed #251; recurrence) - BC-12 canonical-name check: authored prose uses the short product or namespace name; repair rewrites do not converge (re-raised after repair) | PDF-.NET (stop); 3D-.NET, GIS-.NET, PSD-Python, Slides-Cpp (co); Cells-Java (repaired) | 1 / 4 / 6 | MAJOR (small) | validation/registry.py BC-12; composition/authoring.py recover | yes |
| 7 | `TRUNC`: s4_reconciliation.output_runaway_past_budget (existing; Imaging-.NET is sighting 4) plus PROPOSED S6/S3 sibling (RESEARCH_LANE_F F23, F24) - a single sample runs to max_output_tokens (degenerate repetition or a legitimately long reply); TruncatedOutput is never retried, so one sample ends the run | Font-Python (S3, 3000 tokens), Imaging-.NET (S4, whitespace runaway), Cells-Rust (S6, fact-id repetition) | 3 / 0 / 3 | MINOR (redraw); MAJOR for the durable re-ask (PROPOSAL T) | core/llm/jobs.py; prompts/repository_investigation.yaml; prompts/source_reconciliation.yaml | yes |
| 8 | `NOTICE`: PROPOSED validation.notices_without_record_matches_plain_license_text (REG-18 cause 3 family) - NOTICES_WITHOUT_RECORD fires on any deferred unit whose text matches licen[cs]e|notice (a plain License heading or MIT paragraph), and TeX's LICENSE-FONTS is never recorded as a third_party_notices fact | PSD-.NET, TeX-Python (stops); PSD-Python (co) | 2 / 1 / 3 | MAJOR | validation/deferrals.py::_NOTICES; evidence/facts (third_party_notices from LICENSE-FONTS) | yes |
| 9 | `TOOL`: none (machine data, no governed file) - toolchain or environment of this machine | Words-Python (no Python 3.10-3.12), PDF-Cpp (cmake TLS trust anchors), Cells-Rust (cargo nondeterminism), Words-.NET (git-LFS objects absent) | 3 / 1 / 4 | MINOR (machine data / runner) | D:\tools\rp-toolchains registry; tools/reviewer/reseal_wave/reseal_wave.py | n/a (machine) |
| 10 | `UPSTREAM`: evidence/upstream-defects (handoff) - defect in the upstream repository | GIS-.NET (does not build, no README, no LICENSE), TeX-Python (unparseable source), PSD-Python (no packaging, no LICENSE), PSD-.NET (no LICENSE) | 3 / 1 / 4 | MINOR (upstream) / handoffs to draft | evidence/upstream-defects (TC-ISS) | n/a (upstream) |
| 11 | `HTML`: PROPOSED section_authoring.bare_angle_bracket_guard_no_recover (related G4-W17 item 46 / DECISION_LOG 2026-09-11) - the bare '<' guard rejects a placeholder path or an HTML element name written outside a code span; no recover wraps it | PDF-Go (stop); HTML-Python, Slides-.NET, TeX-Python (seen) | 1 / 0 / 4 | MAJOR (small) | composition/authoring.py::_bare_angle_bracket recover | yes (4 seen) |
| 12 | `TITLE`: section_authoring.rejection_no_recover, title-restatement sub-shape (existing; recurrence after the 2026-09-27 fix) - capability units that restate their own title are rejected on both attempts; the title-restatement recovery did not rescue them | Slides-Java (stop); 3D-Java, PDF-Java, PSD-.NET, PSD-Python, Slides-.NET (seen, recovered) | 1 / 0 / 6 | MAJOR (small) | composition/authoring.py recover_title_verbatim_opening | yes (index entry reopened) |
| 13 | `SUPERSEDED`: composition.authoring.superseded_unit_not_carried (existing; REG-22) - a unit superseded into a section by reconciliation is not cited or omitted by the section's authoring call, rejected twice | Slides-.NET (attempt 2 stop); HTML-Python (seen) | 1 / 0 / 2 | MAJOR | composition/authoring.py::carried_unit_errors, section_selections (REG-22) | no (2) |
| 14 | `BC03NEG`: PROPOSED validation.bc03_flags_negative_example_fence_in_preserved_unit - BC-03 flags a fenced counter-example inside a verbatim-preserved inherited unit as an unverified example; no LLM-owned section exists, so no repair can act | Slides-Cpp | 1 / 0 / 1 | MAJOR (small) | validation/registry.py BC-03; repair/rounds.py routing | no (1) |

Also recoverable-but-costly, seen everywhere: Enterprise-Edition-name rejections in 21 of 36 repositories and coherence-drop rejections in 11 of 36 (both recovered in every case; they cost calls, not seals).

## Answer to the owner's test

The test: how many of 36 would need only minor changes, how many major ones.

- **MINOR only (7 of 36):** Aspose.Font-FOSS-for-Python, Aspose.GIS.FOSS-for-.Net, Aspose.Cells-FOSS-for-Rust, Aspose.Imaging-FOSS-for-.NET, Aspose.PDF-FOSS-for-Cpp, Aspose.TeX-FOSS-for-Python, Aspose.Words-FOSS-for-Python. Their current stop is a redraw (Font-Python, Imaging-.NET, Cells-Rust after the cargo fix), a machine fix (Words-Python needs a Python 3.10-3.12; PDF-Cpp needs a CA bundle for the winlibs cmake) or an upstream fix (GIS-.NET, TeX-Python). Only 5 of the 7 could become a candidate (Font, Imaging, Cells-Rust, Words-Python, PDF-Cpp); GIS-.NET and TeX-Python are typed BLOCKED_UPSTREAM outcomes. None of the 5 is known to be clean past its stop: Words-Python, for instance, is expected to meet the unrecorded-enum-member rejection next.
- **MAJOR (19 of 36 failures):** Aspose.3D-FOSS-for-Java, Aspose.3D-FOSS-for-.NET, Aspose.Cells-FOSS-for-.NET, Aspose.Email-FOSS-for-.Net, Aspose.Email-FOSS-for-Cpp, Aspose.Note-FOSS-for-Python, Aspose.HTML-FOSS-for-Python, Aspose-PDF-FOSS-for-Go, Aspose.Page-FOSS-for-Python, Aspose-PDF-FOSS-for-Python, Aspose.PDF-FOSS-for-.NET, Aspose.PSD-FOSS-for-.NET, Aspose.PDF-FOSS-for-TypeScript, Aspose.PSD-FOSS-for-Python, Aspose.Slides-FOSS-for-.NET, Aspose.Slides-FOSS-for-Java, Aspose.Slides-FOSS-for-Cpp, Aspose.Words-FOSS-for-.NET, Aspose.Slides-FOSS-for-Python. Each needs a governed-code change (identifier recover, S4 recover, deferral classification, BC-12, BC-03, preservation, notices matcher).
- **The 10 seals do not count as minor.** 0 of the 5 independently reviewed are authorizable; the other 5 are unreviewed. 3D-TypeScript states 'The package @aspose/3d version 24.12.0' although handoff a6f52c1a records that the package is not on npm under its declared name (TC-CLM-01), and Cells-TypeScript states 'version 1.0.0' without a registry check on record. Treating the unreviewed five as pending, the best case without a major change is 5 (unreviewed seals) + 5 (minor-fixable failures) = 10 of 36 *candidates*, and the evidence so far (0 of 5 reviewed pass; 4 of 5 fail BC-10 once REJECT stands) says to expect fewer.
- **Net on the baseline code:** 7 need only a minor change (5 of them candidate-producing); **at least 24 of 36 need a major change** (19 failures + the 5 seals already judged DO_NOT_PROPOSE); 5 seals are unreviewed. The "handles a large part of the portfolio without major changes" hypothesis is not supported by the baseline. The strongest part of the case for it: 6 of the 19 MAJOR rows (3D-.NET, Email-Cpp, PDF-.NET, Cells-.NET, PDF-Python, Slides-Python) stopped on a check whose outcome depends on the draw, and DEFECT_INDEX REG-18 records 3D-.NET READY_FOR_PROPOSAL in the G7-W12 session, so a redraw lottery could move up to 6 more rows past their current stop without code, at the price of landing them in the same unreviewed-quality state as the 10 seals.

## TC-TRI-01-02: partition check against project/state.yaml G5-W08

`data/registry.json` has 36 entries (34 `dry_run`, 2 `full`); `results.jsonl` has 36 rows; the two sets are identical. Each entry appears in exactly one terminal bucket above (SEALED 10, FAILED_INTERNAL 20, BLOCKED_UPSTREAM 3, DEFERRED 3, NON_PROCESSABLE 0 = 36). G5-W08's exit predicate ("every registry entry ends in a counted state or a typed disposition with a resume predicate") is met on paper: every row carries a resume predicate.

Discrepancies with the G5-W08 text ("six registry entries with no current candidate: 3D-TypeScript, GIS-.NET, PDF-TypeScript, TeX-Python, PSD-.NET, PSD-Python"):

1. 3D-TypeScript now has a SEALED bundle (READY_FOR_PROPOSAL, no-op VERIFIED) but it is REJECT_FACTUAL converted to ACCEPT and unreviewed; the cursor line is stale in one direction, and the seal is weak in the other.
2. Four of the six remain without a candidate and none is NON_PROCESSABLE yet: GIS-.NET and TeX-Python have no typed-outcome producer, so `present` ends them FAILED_INTERNAL-shaped; PSD-.NET stops on our matcher, PDF-TypeScript on S4. PSD-Python is the sixth (BC-02).
3. PSD-Python's upstream moved on 2026-10-10 (README 2 lines to 372 lines, revision 664446b9 to dbc90f46) after the TC-PRE-01 preflight classed it "thin evidence"; the preflight's expected class PROCESSABLE stands, the stop is BC-02 (no packaging) plus three of our mechanisms.
4. No bucket for "processable but machine-blocked" exists in the seven counts; DEFERRED(MACHINE_TOOLCHAIN) is used for Cells-Rust, PDF-Cpp and Words-Python and should be confirmed as an accepted typed disposition by L-gov.

## Proposed DEFECT_INDEX records (not applied: `docs/` is L-gov's path; the card says log, do not fix)

- `REV01`: PROPOSED review.reject_demoted_to_accept_by_scope_defect_label; fixed on integration by e482390b (TC-REV-01), not in baseline. a returned REJECT is converted to ACCEPT by reviewer_scope_defect labels, so SEALED does not mean reviewed-good.
- `PRES`: PROPOSED composition.inherited_valuable_content_dropped_repair_cannot_restore (related composition.coherence.inherited_diagram_content_loss, composition.authoring.superseded_unit_not_carried); TC-DSP-01 a9877f96 on integration, not in baseline. valuable inherited upstream content (test/sample commands, limitation detail, Enterprise paragraph) is superseded or dropped and one repair round cannot restore it.
- `IDENT`: PROPOSED section_authoring.identifier_refusal_exhausts_both_attempts (related readme.dotted_file_name_in_prose_not_a_recorded_fact G7-W23, surface.members_the_source_defines_are_not_recorded_as_facts, section_authoring.rejection_no_recover). the identifier rule refuses a name that is not a fact value (stdlib or JDK type, external file, packaging key, unrecorded member); the re-ask repeats it; no deterministic recover; the whole section call fails.
- `S4OMIT`: PROPOSED reconciliation.recover_uncited_prose_omits_declines_on_brand_word_symbol (REG-18 follow-up, G7-W12). S4 uncited_prose_omit survives the re-ask; recover_uncited_prose_omits declines all-or-nothing because a unit spells a SUPPORTED symbol that is only the brand word (public_symbol:aspose.*).
- `NOTICE`: PROPOSED validation.notices_without_record_matches_plain_license_text (REG-18 cause 3 family). NOTICES_WITHOUT_RECORD fires on any deferred unit whose text matches licen[cs]e|notice (a plain License heading or MIT paragraph), and TeX's LICENSE-FONTS is never recorded as a third_party_notices fact.
- `HTML`: PROPOSED section_authoring.bare_angle_bracket_guard_no_recover (related G4-W17 item 46 / DECISION_LOG 2026-09-11). the bare '<' guard rejects a placeholder path or an HTML element name written outside a code span; no recover wraps it.
- `BC03NEG`: PROPOSED validation.bc03_flags_negative_example_fence_in_preserved_unit. BC-03 flags a fenced counter-example inside a verbatim-preserved inherited unit as an unverified example; no LLM-owned section exists, so no repair can act.
- Add sightings to existing entries: `s4_reconciliation.output_runaway_past_budget` (Imaging-.NET, 4th), `section_authoring.rejection_no_recover` title-restatement (Slides-Java, recurrence after fix), `composition.authoring.superseded_unit_not_carried` (Slides-.NET), REG-18 (3D-.NET, Email-Cpp, Page-Python, Slides-.NET attempt 1, PSD-Python), `readme.canonical_name_enforced_only_in_renderer_slots` (5 stops or co-failures), `readme.dotted_file_name_in_prose_not_a_recorded_fact` (HTML-Python directory tokens), `surface.members_the_source_defines_are_not_recorded_as_facts` (Words-Python, Note-Python).

## Three unowned mechanisms: proposed DEFECT_INDEX ids and sightings

Proposed text for L-gov; none is in `docs/DEFECT_INDEX.md` yet. Sightings are from this run's archive; the cited call and validation files are under `E:p-archive\<repo>uns	ransactions\`.

### `reconciliation.uncited_prose_omit_recover_declines_on_brand_word_symbol` (3 sightings: settled)

`recover_uncited_prose_omits` (the `recover=` of `source_reconciliation`) declines all-or-nothing when any rejected unit spells a SUPPORTED fact (`uncited_omit_candidates`). The only fact a unit such as `Or build from source:` or `Then add a project reference to Aspose.Words/Aspose.Words.csproj` spells is `public_symbol:aspose`, i.e. the brand word, so the whole recovery returns None and the S4 job fails closed after two attempts.

| # | Repository | Evidence |
|---|---|---|
| 1 | Aspose.Words-FOSS-for-.NET | `calls/cc6158eda3eb.rejected-1/2.json`: units 013, 017, 018, 020 uncited; hint `spells these SUPPORTED facts: public_symbol:aspose`; run stops at S4 |
| 2 | Aspose.PDF-FOSS-for-TypeScript | `calls/ed358f8428e6.rejected-1/2.json`: 23 then 19 rejected units; hints name `public_symbol:attachment`, `unsupportedfeatureerror`, `markuptype` etc.; run stops at S4 |
| 3 | Aspose.PSD-FOSS-for-.NET (G7-W12 session, REG-18) | unit `034.paragraph` spells `public_symbol:aspose.psd` (the commercial package); recover declines |

Context: the S4 uncited_prose_omit rejection itself appeared in 27 of 36 repositories (recovered by the re-ask in 25). Fix location: `reconciliation/dispositions.py` (`recover_uncited_prose_omits`, `uncited_omit_candidates`): recover per unit, and do not count a brand-word or namespace-root symbol as evidence. Change size MAJOR (governed file, `NORMALISATION_VERSION`).

### `validation.deferral_unclassified_free_text_defer_unresolved` (5 sightings in this run: settled; extends REG-18)

A model-authored `DEFER_UNRESOLVED` whose free-text rationale matches no `DEFERRAL_CLASSES` entry blocks BC-05 as UNCLASSIFIED. The class added for #328 (`NOT_CARRIED_BY_NAMED_SECTION`) matches only the typed `RECOVERED_COVERAGE_RATIONALE` prefix, so it does not cover these rationales.

| # | Repository | Units and rationale |
|---|---|---|
| 1 | Aspose.3D-FOSS-for-.NET | 066.paragraph: 'public use is uncertain per uncertainties' |
| 2 | Aspose.Email-FOSS-for-Cpp | 032.paragraph, 069.paragraph: 'no section is available to place it' (unit 069 describes the same examples/ directory and was placed as VERIFIED_PRESERVE in the same run) |
| 3 | Aspose.Page-FOSS-for-Python | 014, 016, 038, 040: 'unsupported by facts; the claim is material and cannot be placed or omitted' (package.py build and publish steps) |
| 4 | Aspose.Slides-FOSS-for-.NET (attempt 1) | 6 units, e.g. 014, 015, 018, 019: 'not covered by the installation section' |
| 5 | Aspose.PSD-FOSS-for-Python (co-failure) | 017, 018 headings: 'rendered by deterministic code for the dependencies section' |

Fix location: `validation/deferrals.py` (a class for 'section cannot place it' and 'heading rendered by the shell'), `reconciliation/dispositions.py` (fold or place instead of DEFER). Change size MAJOR.

### `validation.bc12_canonical_name_repair_does_not_converge` (6 sightings: settled; recurrence of REV-V2-04 after #251)

BC-12 rejects authored prose that uses a short product name or the namespace (`Aspose.Pdf.Foss`, `Aspose.Slides.Foss`) in place of the canonical `<Product> FOSS for <Platform>`; the targeted repair rewrites some sentences and BC-12 re-raises on the rest, so the failure stands after one repair attempt.

| # | Repository | Section | Result |
|---|---|---|---|
| 1 | Aspose.PDF-FOSS-for-.NET | development_testing | sole blocker; 1 repaired, 1 re-raised |
| 2 | Aspose.3D-FOSS-for-.NET | scope_limitations | 3 repaired, re-raised; co-failure with BC-05 |
| 3 | Aspose.GIS.FOSS-for-.Net | api_reference, development_testing | 3 repaired, 1 unrepairable; co-failure |
| 4 | Aspose.PSD-FOSS-for-Python | api_reference | unrepairable; co-failure |
| 5 | Aspose.Slides-FOSS-for-Cpp | api_reference | 1 repaired (garbled 'The Aspose.Slides FOSS for Cpp public symbol'), re-raised; co-failure with BC-03 |
| 6 | Aspose.Cells-FOSS-for-Java | documentation_resources | repaired (the one convergence) |

Fix location: `validation/registry.py` BC-12 (a namespace or package identifier used as a SUPPORTED symbol is not a product name) and `composition/authoring.py` (a deterministic canonical-name rewrite as the `recover=` backstop). Change size MAJOR, small.

## Handoffs to draft under TC-ISS (upstream, not yet in `evidence/upstream-defects/`)

- GIS-.NET: pinned revision b9b8c9c7 does not build (369 CS0246 errors), no README, no LICENSE, no package; reproduced.
- PSD-Python: no packaging metadata and no LICENSE at dbc90f46; PSD-.NET: no LICENSE at 85ed7eec.
- PDF-Cpp: README examples example_003 and example_006 fail with incomplete types (missing includes); the library's own build is blocked on this machine by the TLS trust-anchor issue, so only the README examples are attributable to upstream.

## Limits of this board

- No redraw was run (the card allows two per variance case; this lane may not run `present`). `redraw_candidate` is a judgement from the rejected call bodies, not a measurement.
- Cells-Rust: the cause of the one example that executed in run 1 and not in run 2 is not established; the cargo linker explanation is a candidate.
- PDF-Cpp: the TLS failure was reproduced with the winlibs cmake on a scratch copy and a minimal PATH; the runner's sanitized environment was not replayed, so a CA bundle is the candidate fix, not a verified one.
- 'Settled' counts use only this run plus sightings already in DEFECT_INDEX; earlier sessions' draws were not re-read.
- The independent review covers 5 of the 10 seals; the other 5 verdicts are the pipeline's own.
- Whether TC-DSP-01 (#328) fixes PRES and UNCL on the same inputs is unverified; it changes reconciliation upstream, and its companion matches only the typed recovery prefix, not the free-text rationales seen here.

- scripts/ci_check.sh on this tree: lockdrift, sbom, lint, format, typecheck, entrypoint passed; pytest 4215 passed, 2 failed (tests/core/llm/test_jobs.py, two cases that saw max_output_tokens 10500 instead of 3000 under 10 concurrent CI runs). Rerun alone, all 29 tests in that file pass; the files in this commit do not touch src/, prompts/ or tests/.
