authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Python
bundle_hash: 1fd908ee4c6bba7544b344961cf9af7a706f981318ff272347b460092171ad12
readme_sha256: 8ad70ce87657a7c88847f891923067fc3dd8a1a666d321028b2c57230123bf82
source_revision: 4f6768a7b349a1309644f456eb43bc35f70c16d7
live_head: 4f6768a7b349a1309644f456eb43bc35f70c16d7
reviewed_at: 2026-10-10T16:00:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: claude-sonnet-5-5, lane L-verifier (did not author, reseal or repair the candidate)
claims_checked: 18
claims_failed: 5
forbidden_wording_hits: 0
could_not_verify:
  - "'Standard encryption is not yet supported for reading' (needs a Standard-encrypted sample workbook; inherited unchanged from live)"
  - "Enterprise Edition feature list in live (formula engine, Standard encryption, more formats): vendor assertion"
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Opening / At a Glance / Key Capabilities", summary: "live-README content floor (REQ-DSP-02): the candidate drops 16 chart types, page setup and panes, merged cells, defined names, hyperlinks, comments, pictures, sparklines, workbook/sheet protection, the CSV-import start node and JSON/Markdown output nodes, and the 'pure-Python, no Excel' opening; a reseal on current code is not shown to keep them"}
  - {id: F2, kind: data_change, severity: MINOR, section: "Scope and Limitations", summary: "restore the Enterprise Edition paragraph and link (live: products.aspose.com/cells/python-net/, HTTP 200); pipeline deferred it as ENTERPRISE_NO_VERIFIED_TARGET (ambiguous python / python-net / python-java targets)"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities", summary: "name the real API: Workbook.save(password=...) and Workbook(path, password=...), the ConditionalFormatCollection class and Worksheet.conditional_formats instead of the 'conditional_format' and 'xlsx_encryptor' modules; say CSV can also be imported"}
  - {id: F4, kind: redraw, severity: MINOR, section: "API Reference", summary: "delete the orphan duplicate paragraph at the end of the details block (L576-578), and drop the 'organized into one module' claim"}
blocking_findings:
  - {id: B1, category: dropped_live_content, section: "Opening / At a Glance / Key Capabilities", evidence: "diff -u live-README.md candidate README.md; live L7-12, L36-52, L62-100", summary: "valuable verified live content dropped: see F1"}
  - {id: B2, category: dropped_live_content, section: "Scope and Limitations", evidence: "live paragraph 'These limitations don't apply to [Aspose.Cells for Python - Enterprise Edition](https://products.aspose.com/cells/python-net/)'; curl -> 200", summary: "Enterprise Edition paragraph and link dropped"}
  - {id: B3, category: false_claim, section: "Key Capabilities", evidence: "python: aspose.cells_foss.conditional_format and .xlsx_encryptor are modules (type(...) -> module); the classes are ConditionalFormat, ConditionalFormatCollection, XLSXEncryptor; the user path is Workbook.save(password=...)", summary: "'using the DataValidationCollection and conditional_format APIs' and 'using xlsx_encryptor ... with AgileEncryptionParameters' name modules as APIs and omit the real call (misleading, introduced)"}
  - {id: B4, category: false_claim, section: "Opening", evidence: "Workbook.load_csv exists and the README's own Scope bullet says CSV can be imported", summary: "opening says input is '.xlsx files' and output is '.xlsx and .csv' (JSON and Markdown export and CSV import omitted); contradicts Scope (misleading, introduced)"}
  - {id: B5, category: false_claim, section: "API Reference", evidence: "python: classes in aspose.cells_foss.__all__ -> 56 (63 names); of 130 table names, 56 resolve at the package top level, e.g. from aspose.cells_foss import FormulaEvaluator fails", summary: "'130 public types organized into one module' and the entry-point sentence imply they import from aspose.cells_foss; 74 do not (inherited unchanged from live)"}
  - {id: B6, category: dangling_prose, section: "API Reference", evidence: "README L576-578 repeats the L206 intro after the member reference", summary: "orphan duplicate paragraph inside the details block"}
---

# 1 Bundle facts

- `candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Python/4f6768a7.../`. manifest state
  READY_FOR_PROPOSAL; blocking_failures empty; sealed 2026-10-09T15:27:35Z (PR #305). README
  sha256 equals the manifest value (hash check passed).
- validation.json: BC-01..BC-12 PASS; one advisory: ENTERPRISE_NO_VERIFIED_TARGET.
- review.json: `verdict` ACCEPT and `verdict_as_returned` ACCEPT (no demotion, zero findings,
  zero advisories), reviewer route qwen3-next, identity_separate true. Nothing to rule on; the
  clean reviewer verdict did not catch B1-B6, which confirms that it cannot replace this review.
- examples.json: 6 receipts, all EXECUTED, `build_verified: true`.
- Installed from the clone in a clean venv: `aspose.cells_foss` imports; `__version__` 26.7.0.

# 2 Live comparison

Live README: 416 lines, upstream head equals the sealed revision; template-conformant with a
20-node At a Glance (14 capability nodes), 12 capability bullets and an Enterprise Edition paragraph.

ADDS (candidate only):
- Source-checkout install route and the verify command `python -c "import aspose.cells_foss"`: TRUE (clean-venv install).
- `Detailed Member Reference` for Workbook, Worksheet, Cell, Style, ChartCollection,
  DataValidationCollection, TableCollection and six functions: member names TRUE (every listed
  member exists on the class, checked programmatically); noisy ("Defined as `def ...`", 14
  "PascalCase alias" lines) but not false.
- Qualified rows `cfb_handler.CFBWriter` and `cfb_writer.CFBWriter`: TRUE (two classes with the same name).
- Hard-coded 3.7+ Python badge instead of the dynamic `pyversions` one: TRUE value, less
  informative (PyPI classifiers list 3.7 to 3.12).

DROPS (live only), valuable unless stated:
- Opening: "pure-Python ... without requiring Microsoft Excel ... depends only on pycryptodome and
  olefile": valuable.
- At a Glance: CSV start node, JSON and Markdown output nodes, 14 capability nodes (candidate
  has 8 and one "CSV or XLSX file" output): valuable.
- Key Capabilities: page setup, panes, merged cells, defined names, hyperlinks, comments,
  pictures, sparklines, "all 16 ChartType values" (checked: `len(ChartType)` 16), workbook and
  sheet protection, `load_csv`: valuable.
- Dependencies: the purpose of pycryptodome and olefile and the Development Dependencies
  descriptions: marginal.
- Enterprise Edition paragraph and link: valuable (contract row 18).
- Dynamic Python-versions badge: marginal.
CHANGES: Installation is better (adds the source route, keeps the PyPI route); Scope bullets
equal; Development and Testing equal.

NET: worse (mixed gains are small; the loss of verified capability detail is large).

# 3 Claim checks

| # | Claim (README line) | How checked | Result |
|---|---|---|---|
| 1 | `aspose-cells-foss` version 26.7.0 published (L69) | `curl https://pypi.org/pypi/aspose-cells-foss/json`: `info.version` 26.7.0, releases include 26.7.0; clone `pyproject` version agrees | PASS |
| 2 | `pip install aspose-cells-foss` and `pip install .` (L71, L77-81) | clean venv `pip install ./clone`, import works | PASS |
| 3 | Python >=3.7 and badge 3.7+ (L3, L89, L100) | PyPI `requires_python` >=3.7; classifiers 3.7 to 3.12 | PASS |
| 4 | Runtime deps olefile>=0.46, pycryptodome>=3.15.0 (L95-96) | PyPI `requires_dist` and pyproject | PASS |
| 5 | Dev extras pytest>=7.0.0, pytest-cov>=4.0.0 (L104-105) | PyPI `requires_dist` `extra == "dev"` | PASS |
| 6 | All six Python snippets (L113-199) | extracted and run in the venv in a scratch directory (input.xlsx created by example 1): 6 of 6 exit 0 | PASS |
| 7 | `save_as_csv`, `save_as_json`, `save_as_markdown` on Workbook (L7, L65) | `hasattr(Workbook, ...)` | PASS |
| 8 | Detailed Member Reference members (L350-563) | programmatic check of every listed member against the class | PASS |
| 9 | `AgileEncryptionParameters`, `ChartCollection`, `ShapeCollection`, `TableCollection`, `HorizontalPageBreakCollection`, `VerticalPageBreakCollection`, `Style`, `Font`, `NumberFormat` exported (L59-66) | `hasattr(aspose.cells_foss, name)` | PASS |
| 10 | `formula_evaluator` component (L59) | `aspose.cells_foss.formula_evaluator` module with `FormulaEvaluator` | PASS |
| 11 | Only Agile encryption supported for reading and writing; Standard not yet supported for reading (L596) | no Standard-encrypted sample available | COULD_NOT_VERIFY (inherited) |
| 12 | "using the `DataValidationCollection` and `conditional_format` APIs" (L61) | `conditional_format` is a module; class is `ConditionalFormatCollection`, reached by `Worksheet.conditional_formats` | MISLEADING (introduced) |
| 13 | "protect workbooks with password encryption using `xlsx_encryptor` and decrypt ... `decrypt_xlsx`" (L64) | `xlsx_encryptor` is a module; real path `Workbook.save(password=)` (example 6 runs) | MISLEADING (introduced) |
| 14 | "supports reading `.xlsx` files as input and writing `.xlsx` and `.csv` files as output" (L7) | `Workbook.load_csv`, `save_as_json`, `save_as_markdown` exist; Scope L594 says CSV import | MISLEADING (introduced) |
| 15 | "130 public types organized into one module" (L208, L577-578) | 56 classes at `aspose.cells_foss` top level; 74 table names do not import from it | MISLEADING (inherited) |
| 16 | "without licensing restrictions" (L7) | MIT license requires the notice be kept | MISLEADING (introduced, wording; not counted toward the 'several' threshold) |
| 17 | External and relative links (28) | mech.py --net: all external 200; `License/LICENSE.txt`, `AGENTS.md`, `examples` exist | PASS |
| 18 | `pip install -e ".[dev]"` then `pytest` (L605-608) | runs; result 291 passed, 4 failed, 1 skipped on Windows, Python 3.13.15, cp1252 locale (upstream defects, issues 1 and 2 below) | PASS (command works; failures are upstream) |

Failed or misleading: 12, 13, 14, 15, 16 (five; three introduced and counted: 12, 13, 14).

# 4 Mechanical and wording results

mech.py: one H1; all 12 standard sections in order, no extras; one mermaid fence and At a Glance
holds only it; no fence without a language; forbidden wording: none ("commercial edition",
"paid version", "forum.aspose.com", "via X" absent); one hit on "wrapper" in the API table
description of `SheetProtectionDictWrapper` ("Dictionary-like wrapper around SheetProtection"),
judged NOT an implementation bridge (an internal compatibility class), but that class is
internal and not exported (it should not be in a public API table); `Enterprise Edition` occurs
0 times. No dangling lead-in sentences (the Development section now has its command block).
Duplicates: `#api-reference`, `License/LICENSE.txt` link targets; orphan paragraph B6.

# 5 Omitted information in the clone

- `llms.md` (278 lines, LLM-oriented reference) and `requirements.txt`: not in either README.
- GitHub releases V26.7.0, V26.3.1, V26.3.0 (`gh api .../releases`): no release/changelog link.
- `examples/` has 34 files (30 are `test_*.py` used as usage examples; the README links the folder).
- Hyperlinks, merged cells, defined names, comments, pictures, sparklines, 16 chart types: in
  live, missing here (B1).

# 6 Drafted upstream issues (text only, nothing filed)

1. Title: `save_as_csv and the CSV tests default to the OS locale encoding; CJK text raises UnicodeEncodeError on Windows`
   Body: `CSVSaveOptions.encoding and CSVLoadOptions.encoding default to locale.getpreferredencoding(False). On Windows (cp1252) examples/test_csv_import_export.py::TestCSVUnicodeAndInternationalization::test_chinese_characters and ::test_japanese_characters fail with UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-1. Reproduce: git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python; python -m venv v; v\Scripts\pip install -e ".[dev]"; v\Scripts\python -m pytest -q (Python 3.13.15, Windows 11, locale cp1252): 4 failed, 291 passed, 1 skipped. Suggested: default to utf-8 (or utf-8-sig) explicitly.` Severity: medium. Proof: the pytest command above.
2. Title: `examples/test_xlsx_to_json.py and test_xlsx_to_markdown.py fail on a clean checkout: input/ directory is not in the repository`
   Body: `test_sales_report_to_json fails with "Input file .../input/sales_report_comprehensive.xlsx does not exist"; test_convert_all_xlsx_to_markdown fails with "No XLSX files found in input directory". The repository root has no input/ directory. Commit the fixtures, generate them in a fixture, or skip when absent.` Severity: low-medium. Proof: same pytest run (the other two failures of the four).
3. Title: `License is only in License/LICENSE.txt, so GitHub reports no license`
   Body: `gh api repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Python --jq .license returns null; the MIT text lives only under License/. Add LICENSE at the repository root.` Severity: low. Proof: that command.
4. Possible, unreproduced: `[project.urls]` in pyproject.toml point to the former repository name `aspose-cells-foss/aspose-cells-python` (redirects today).

# 7 Verdict and reasons

DO_NOT_PROPOSE, confidence high (medium-high on the "several" threshold, which is the protocol's
rule, not a hard fact). This is the closest of the two reviewed candidates to acceptable:
every example runs, install and version claims are true, nothing is dangling, no forbidden
wording. But the live README is already template-conformant and clearly richer, the candidate
drops its Enterprise Edition paragraph and most of its capability detail, and it introduces
three misleading API-naming statements. A PR would reduce what the repository tells visitors.
The reviewer's own clean ACCEPT did not see any of this.

What would let it be reconsidered (fix sizes): F2 data entry MINOR; F3 and F4 redraw MINOR; F1,
the live-content floor, is a code change and therefore MAJOR: without it a reseal is not shown
to keep the dropped units, so this candidate is a test of the planned DSP gate.
