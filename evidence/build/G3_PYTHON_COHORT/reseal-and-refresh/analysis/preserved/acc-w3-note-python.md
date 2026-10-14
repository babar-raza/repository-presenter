authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-note-foss/Aspose.Note-FOSS-for-Python
bundle_hash: 220f2254e06492647d9bb34bb20ad4415bf52197093cc7127fc43384e1cb1efd
readme_sha256: 622c0c03dd981c9a413fa028ebd96f532b3b3f25f277b6d5dc52eb2b956fe45c
source_revision: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
live_head: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
reviewed_at: 2026-10-11T10:00:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author
claims_checked: 21
claims_failed: 7
forbidden_wording_hits: 1
could_not_verify: ["golden-PDF and remaining unittest modules not run (3 of 8 CI modules run: 16 tests OK)", "reference.aspose.org '39 public types' claim not fetchable as a count"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Installation", summary: "the optional pdf extra install (pip install \"aspose-note-foss[pdf]\") is dropped although the first Quick Start example needs it; a deferred 'NOT_CARRIED_BY_NAMED_SECTION' advisory hid the loss (partial-preserve defect)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "API Reference", summary: "Detailed Member Reference is garbled: headingless pasted live fragments, a SaveFormat heading with no members followed by a duplicated lead paragraph, orphan 'All inherit from AsposeNoteError' with one exception, tautological 'Defined as def ...' bullets, '/' used for unions, enum members and 5 exceptions lost"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "Development and Testing", summary: "'29 test files' counts json/pdf fixtures and helpers (12 test modules); prose paragraph replaces the live bullet/commands with a broken code span 'tools/`regenerate_pdf_goldens.py`' and a wrong-case path 'tests/goldens/PDF'"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Scope and Limitations", summary: "states 'distributed under the LicenseRef-Aspose-Split license' (pyproject metadata id) while LICENSE and the License section say MIT: an unexplained, contradictory licence claim"}
  - {id: F5, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities / Documentation", summary: "remove invented audience sentence and 'full commercial suite'; stop repeating each capability title as the first sentence of its body; fix '39 public types ... covers all 37' contradiction; restore page metadata/revision history capability; IncorrectPasswordException description (raised for any password)"}
blocking_findings:
  - {id: B1, category: false_claim, section: "Installation / Quick Start", evidence: "venv: pip install aspose-note-foss; python qs1.py -> RuntimeError: PDF export requires reportlab (Document.Save pdf_writer.py L1748); live README says pip install \"aspose-note-foss[pdf]\"", summary: "INTRODUCED: documented install does not make the first Quick Start example work; the live README's pdf-extra instruction was dropped"}
  - {id: B2, category: false_claim, section: "Development and Testing", evidence: "find tests -name 'test_*.py' = 12; find tests -type f = 29 (13 json, 1 pdf, 15 py incl. __init__/_bootstrap/_pdf_goldens)", summary: "INTRODUCED: '29 test files' is MISLEADING"}
  - {id: B3, category: false_claim, section: "Scope and Limitations", evidence: "clone LICENSE = MIT License; pyproject license = \"LicenseRef-Aspose-Split\"; README License section says MIT", summary: "INTRODUCED: README says two different licences"}
  - {id: B4, category: dangling_prose, section: "API Reference", evidence: "README.md L322-465", summary: "INTRODUCED: garbled/duplicated reference (headingless live fragments, orphan sentence 'All inherit from AsposeNoteError.', empty SaveFormat section, duplicated lead paragraph L268 vs L383)"}
  - {id: B5, category: false_claim, section: "Opening", evidence: "no README/doc text supports 'Developers use it to build Python applications ... for reporting, migration, or integration purposes'; 'without requiring a full commercial suite' names a commercial product tier", summary: "INTRODUCED: invented audience; edition-adjacent wording"}
  - {id: B6, category: dropped_live_content, section: "Installation / Key Capabilities / Dev / API", evidence: "retention.py (below)", summary: "drops pdf-extra install, import-package sentence, page-metadata and PageHistory capability, enum member values, five exception descriptions, ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS and failure-artifact notes, examples/README link, ReportLab licence note"}
  - {id: B7, category: demoted_finding_true, section: "Installation / Key Capabilities", evidence: "validation.json advisories: inherited_unit:013 (pdf extra) NOT_CARRIED_BY_NAMED_SECTION; inherited_unit:010 (rewrite no longer names Page.Author, Document.GetPageHistory ...)", summary: "both deferrals/advisories are TRUE losses; they were published as 'advisory, never published' and did not block"}
---

# 1 Bundle facts

- manifest.state READY_FOR_PROPOSAL; revision 0fd1cf7b == live head (git clone --depth 1, `rev-parse HEAD`); README sha256 equals manifest.files["README.md"].sha256; review ACCEPT (as returned ACCEPT, second_reader read 2, trigger ADVISORY_DEFERRAL, findings []); validation BC-01..BC-12 and BC-14 PASS; no-op proof VERIFIED, 0 provider calls on rerun, byte identical.
- Profile: C01 NOT_MET (Aspose destination before the explanation: [5]); D14 UNEVALUATED ("no template evidence").
- Dispositions of note: OMIT_UNSUPPORTED for the live Quick Start (example 001 FAILED with AttributeError - correct, the live example crashes), OMIT of the live mermaid and `<details>` block; DEFER_UNRESOLVED for inherited_unit:013 (pdf extra and ReportLab), 015 (Python/import path) and 101 (licence paragraph).
- Advisories ruled: 013 TRUE loss (see B1/B7); 015 minor loss (the import path appears only in `python -c "import aspose.note"`); 101 acceptable (a Third-Party Notices section replaces it); "rewrite no longer names ..." (unit 010) TRUE loss (the Key Capabilities no longer say page metadata or revision history are readable).

# 2 Live comparison

ADDS (TRUE unless noted): explicit `python_requires >=3.10`; source-checkout install `pip install .` (TRUE: venv install + import OK); `python -c "import aspose.note"` check (TRUE); Quick Start example 2 (binary stream; TRUE, runs); Third-Party Notices section (TRUE: file exists); Dependencies list with exact specifiers (TRUE: pyproject); build/twine as `dev` extra (TRUE); at-a-glance rewrite (TRUE); static `python-3.10+` badge (TRUE) replacing the dynamic PyPI pyversions badge (dropped); "29 test files" (MISLEADING); "LicenseRef-Aspose-Split license" (MISLEADING); invented audience sentence and "full commercial suite" (UNSUPPORTED).
DROPS (valuable): `pip install "aspose-note-foss[pdf]"` and the reportlab link (first Quick Start example now fails); "distribution is aspose-note-foss; import package is aspose.note" sentence; Key Capability "read page metadata (Title, Author, CreationTime, Level) and revision history"; `Page` metadata / `FileFormat` "always reports OneNote2010" caveat in capabilities; enum member values (`FileFormat: Unknown, OneNote2010, ...`, `HorizontalAlignment`, `TagStatus`, `NodeType`); Exceptions section (five of six); Outline member list; CI-matched runs wording (`ci.yml` link); `ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=1` note; `tests/out/pdf_golden_failures/` note and PyMuPDF/pdftoppm fallback sentence; `examples/README.md` link; ReportLab BSD-3-Clause statement; PyPI-versions badge; the live per-class API descriptions (replaced by one-line generic "Represents a ... in a OneNote document").
DROPS (justified): the live Quick Start page-walk example (crashes: `page.Title` is None for SimpleTable.one, AttributeError, reproduced).
CHANGES: opening worse (generic + invented use case); Key Capabilities worse (each bullet repeats its own title); API tables worse (generic descriptions, exceptions described by name only); Dev section worse (prose paragraph plus broken span); License section equal.
NET: worse. The live README is already fully conformant (11 of 11 standard sections, Dependencies present) and richer.

Retention of live content in the candidate (retention.py; "verbatim" = whitespace-collapsed exact substring; "reworded" = similarity >= 0.80; items below 0.80 are "lost"):

| kind | live | verbatim | % | reworded | lost |
|---|---|---|---|---|---|
| sentences | 31 | 11 | 35% | 1 | 19 |
| list items | 108 | 79 | 73% | 4 | 25 |
| links (unique targets) | 31 | 27 | 87% | 0 | 4 |
| code blocks | 20 | 17 | 85% | 2 | 1 (the crashing Quick Start) |
| CORE (four kinds) | 190 | 134 | 71% | 7 | 49 (26%) |
| table rows (supplemental) | 42 | 3 | 7% | 1 | 38 (descriptions rewritten; 40 of 42 row keys kept) |

Lost links: `.github/workflows/ci.yml`, `examples/README.md`, the pyversions badge, `pypi.org/project/reportlab`. Lost sentences/items: the whole pdf-extra instruction and ReportLab dependency description; the capability bullets for page metadata/history, tables, tags; the enum member lists; five exception descriptions; the PDF-golden environment/diagnostic sentences; the opening sentences (rewritten); the ReportLab licence sentence.

# 3 Claim checks

| # | Claim (line) | How checked | Result |
|---|---|---|---|
| 1 | PyPI `aspose-note-foss`, version 26.9.0 (L66) | pypi.org/pypi/aspose-note-foss/json: info.version 26.9.0, releases ['26.9.0']; pyproject 26.9.0 | PASS |
| 2 | `pip install aspose-note-foss` (L69) | pip install in fresh venv: 26.9.0 | PASS |
| 3 | `python_requires >=3.10` (L86, L103) | PyPI requires_python '>=3.10'; pyproject | PASS |
| 4 | source checkout `pip install .` (L77) | fresh venv `pip install ./clone`; import OK | PASS |
| 5 | `python -c "import aspose.note"` (L83) | run | PASS |
| 6 | Optional deps reportlab>=3.6 (pdf), Pillow>=10.0/PyMuPDF>=1.25/pypdf>=5.3 (test-pdf), build>=1.2/twine>=5.0 (dev) (L96-108) | pyproject [project.optional-dependencies]; PyPI requires_dist | PASS |
| 7 | Quick Start example 1, PDF export (L114-119) after the documented install | venv with only `pip install aspose-note-foss`, run | FAIL (RuntimeError: PDF export requires reportlab) - introduced |
| 8 | Quick Start example 2, binary stream (L123-128) | run: prints `None 1` | PASS |
| 9 | All 11 Python blocks (L114-258) run | all 11 executed with the `[pdf]` extra installed (3 needed UTF-8 stdout on Windows) | PASS |
| 10 | "The suite covers 29 test files under `tests/`" (L490) | `find tests -name 'test_*.py'` = 12; `find tests -type f` = 29 | FAIL (MISLEADING) - introduced |
| 11 | "distributed under the LicenseRef-Aspose-Split license" (L476) | clone LICENSE is the MIT text; pyproject `license = "LicenseRef-Aspose-Split"`; README L532 says MIT | FAIL (MISLEADING, contradictory) - introduced |
| 12 | "The verified public surface has 37 types" (L270) vs "all 39 public types ... covers all 37" (L471) | `__all__` 33 + CompositeNode, AsposeNoteError, SaveOptions, PdfSaveOptions = 37 | PASS for 37; FAIL for the L471 sentence ("39 ... it covers all 37") - self-contradicting, inherited text plus introduced rewrite |
| 13 | `IncorrectPasswordException` "when an incorrect password is provided" (L285) | model.py L1269: raised when any `DocumentPassword` is given | FAIL (MISLEADING) - introduced (live was accurate) |
| 14 | Class bases in the API table (Image/Outline/Page/Table... "inherits from CompositeNode"; RichText/Title/AttachedFile "inherits from Node") | model.py class statements | PASS |
| 15 | Image members FilePath/Format/OriginalWidth/OriginalHeight/Alignment/Replace/Tags; RichText AppendFront/Clear/GetEnumerator/Is* | model.py | PASS |
| 16 | "tests/goldens/PDF" (L488) | `ls tests/goldens` = `pdf` | FAIL (wrong case; breaks on Linux) - introduced |
| 17 | CI unittest module list (L499-506) | ci.yml L38-45 identical; ran 3 of 8 modules, 16 tests OK | PASS |
| 18 | MIT licence sentence (L532) | LICENSE text | PASS |
| 19 | Limitations (write not implemented, Save only PDF, password unsupported, stubs) (L478-482) | model.py, exceptions tests, unittest | PASS (inherited) |
| 20 | 32 links (L3-532) | mech.py --net: no non-200; relative links (LICENSE, THIRD_PARTY_NOTICES.md, examples/, workflow files) exist | PASS |
| 21 | "Developers use it to build Python applications that inspect, transform, or export OneNote data for reporting, migration, or integration purposes" (L7) | grep README/docs/examples in the clone for any audience statement | FAIL (unsupported, invented) - introduced |

# 4 Mechanical and wording

- mech.py: 1 H1; standard sections in order; required present; Third-Party Notices extra (legitimate); one mermaid fence; every fence has a language; Enterprise Edition anchor shape OK; no forum links; duplicate targets `#api-reference`, `LICENSE`.
- Wording: "without requiring a full commercial suite" (L7) is an edition-adjacent descriptor in the opening (BLOCKING by judgement, introduced; the live README has no such phrase); "the commercial product" (L482) is inherited from the live text (borderline, reported).
- Dangling/garbled (introduced): L322-465 as B4; L335 "it exposes Text, `TextRuns`" (mixed code spans); L360 "with `FileName`, Bytes, and alignment"; L488 `tools/\`regenerate_pdf_goldens.py\``; L471 "complete ... all 39 ... It covers all 37"; Key Capabilities bullets that repeat their own title as the first sentence (all six); Scope opening paragraph repeats the opening and adds the licence contradiction; `LoadOptions`.DocumentPassword (broken span, L479).
- Duplicates: API lead paragraph (L268 and L383-387); live detailed reference interleaved with the generated one.
- Signatures print unions with "/" (`str / Path / BinaryIO`, `HorizontalAlignment / None`) - a renderer defect, and properties are written `def Alignment(self) -> ...`.

# 5 Omitted information in the clone

- `.github/workflows/ci.yml` runs on Python 3.10, 3.11, 3.12 (supported matrix; neither README states it) - advisory.
- `examples/` (extract_text.py, save_images.py, export_pdf.py + README): live linked `examples/README.md`; candidate links only `examples/` - live loss.
- `testfiles/*.one` (12 sample documents) used by every example: not mentioned by either README - advisory.
- `tools/regenerate_pdf_goldens.py`: kept. `language-agnostic-plan/`, `legacy/`, MS-ONE/ONESTORE PDFs: marginal.
- GitHub releases / CHANGELOG: none in the clone.

# 6 Drafted upstream issues (TEXT ONLY, not filed)

1. Title: README Quick Start example raises AttributeError for SimpleTable.one. Where: README.md L102-111 (`print(page.Title.TitleText.Text)`). Repro: `pip install aspose-note-foss==26.9.0`, copy testfiles/SimpleTable.one, run the snippet -> `AttributeError: 'NoneType' object has no attribute 'TitleText'` (Python 3.13). Fix: guard for `page.Title is None` or use a document whose pages have titles. Severity: low. Proof: reproduced in scratch venv.
2. Title: licence metadata contradicts the LICENSE file. Where: pyproject.toml `license = "LicenseRef-Aspose-Split"` versus LICENSE (MIT) and README. Suggested fix: use `license = "MIT"` (SPDX) or explain/ship the LicenseRef text. Severity: medium (consumer licence scanners). Proof: `grep -n license pyproject.toml; head -3 LICENSE`.

# 7 Verdict and reasons

DO_NOT_PROPOSE (MAJOR). Seven independent introduced FAIL/MISLEADING results (B1-B3, B5, the IncorrectPasswordException description, the 39/37 contradiction, the wrong-case path) exceed the three-result threshold; the most serious is that the documented install leaves the first Quick Start example crashing. The live README is already conformant and richer, and the candidate degrades Installation, Development, API Reference and Key Capabilities.

Needed before reconsideration (code): item-level preservation check for deferred inherited units (BC-05/TC-DSP-01) so a DEFER on the pdf-extra paragraph cannot publish; count extractor must count test modules only; the licence field must prefer the LICENSE file over the pyproject LicenseRef; API reference renderer must not emit headingless pasted fragments next to generated members; opening must not state an audience.

Universal defects (routing): U-PARTIAL-PRESERVE (deferred unit lost, advisory-only); U-COUNT (29 = all files); U-AUDIENCE (opening); U-DETAILED-REFERENCE (tautological "Defined as", '/' unions, orphan fragments); U-TITLE-ECHO (every capability bullet repeats its title; NEW); U-LICENSE-ID (pyproject licence identifier surfaced contrary to LICENSE; NEW); U-CODE-SPAN-SPLIT (identifier/path spans split, as Cells-.NET).

Confidence high: every blocking item reproduced from the registry, the clone or a fresh venv. Could not verify: see front matter.
