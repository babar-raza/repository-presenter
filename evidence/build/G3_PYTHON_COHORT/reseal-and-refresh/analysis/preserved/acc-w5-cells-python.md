authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Python
bundle_hash: 5440c62af9606ddd2d21f1d5e22ce204ff7f804693e94eca704d777861693db2
readme_sha256: e79d73a560d3ace87c21b3a4c5b273ef999d71032d2bf84d118339f88e21ff19
source_revision: 952317cad8db1880ed85be9814c24e9303930d49
live_head: 952317cad8db1880ed85be9814c24e9303930d49
reviewed_at: 2026-10-11T19:05:00Z
verdict: FIX_REQUIRED
minor_major: MAJOR
net_vs_live: mixed
confidence: medium
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run e407503a (wave 5), sealed bundle G:\rp-w5\cells-python
claims_checked: 15
claims_failed: 1
forbidden_wording_hits: 0
could_not_verify: ["'160 types' count", "example 5 receipt FAILED (RuntimeError, example dropped: correct)", "skia-python install not run"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Quick Start / Additional Examples / Development and Testing", summary: "preserved lead-ins and their blocks separated: 'Install the package from PyPI:' (Quick Start) has no block and is followed by the dependency sentence; 'Install the renderer separately:' (Additional Examples) is followed by the CSV sentence while its pip install block sits in Development and Testing (placement of preserved units by topic, destinations.py _HOMES, plus lead-in coordination)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations / License / Third-Party Notices", summary: "first Scope bullet fuses Python 3.10 with the calculation-engine disclaimer and repeats it (3 statements of 'not a full Excel calculation engine'); licence/third-party-notice sentences appear in Scope, License and Third-Party Notices (duplicate-section content)"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Key Capabilities", summary: "'protects workbooks ... using the `aspose.cells_foss.workbook` class' (lower-case garble) and '`aspose.cells_foss.pdf_exporter` functions' (pdf_exporter is a module holding PdfExporter); two orphan preserved bullets after the list (9 items vs 3-8)"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities", summary: "restore live capabilities dropped: free/open-source/pure-Python/no Microsoft Excel opening, merged cells, hyperlinks, page setup and page breaks, auto-filters, comments, TSV export"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Quick Start / Additional Examples", evidence: "cand README L141 'Install the package from PyPI:' then prose; L200 'Install the renderer separately:' then 'CSV import is available ...'", summary: "lead-ins with no payload (mech.py flagged both)"}
  - {id: B2, category: dangling_prose, section: "Scope and Limitations", evidence: "cand README L668 bullet 1", summary: "fused and repeated statements"}
  - {id: B3, category: false_claim, section: "Key Capabilities", evidence: "aspose/cells_foss/__init__.py L66 'from .pdf_exporter import PdfExporter' (a module/class, no function pdf_exporter)", summary: "MISLEADING: pdf_exporter listed among functions"}
  - {id: B4, category: dropped_live_content, section: "Opening / Key Capabilities", evidence: "retention.py: live opening lost; 5 of 14 live sentences, 10 of 19 live list items lost", summary: "valuable live capabilities missing"}
  - {id: B5, category: template, section: "Third-Party Notices", evidence: "cand README L691-697: Third-Party Notices section plus License repeating the same links", summary: "duplicated notices/licence links (3 duplicate targets)"}
---

# 1 Bundle facts
READY_FOR_PROPOSAL, revision equals live head, README sha256 equals manifest, no-op VERIFIED; validation all PASS; review ACCEPT (as returned ACCEPT); second read triggered by ADVISORY_DEFERRAL, read 2, corroborated none. Two advisory deferrals: 024.paragraph ("The output format is inferred from the file extension:", a lead-in to the live Export example, deferred as LEADIN_OF_WITHHELD_CONTENT) and 038.paragraph ("Generated workbooks are written below examples/outputfiles/ and are not intended for source control", NO_EVIDENCE_EITHER_WAY). Rulings: both are true statements of the live README that the candidate drops: the file-extension inference is useful to a reader (Export example and its explanation lost), 038 is marginal. Neither makes the candidate false, so neither blocks by itself, but 024 is part of the missing export example (B4). Examples: 5 EXECUTED, 1 FAILED (RuntimeError; dropped from the README, correct).

# 2 Live comparison
The live README is NOT template-conformant (Features, Installation, Quick start, no Navigation, no At a Glance, no API Reference). The candidate adds the template (Navigation, diagram, Dependencies, API Reference of 160 types, Documentation & Resources, Scope, Development, License), which is an improvement in structure, plus the deterministic Dependencies list (verified) and PyPI version (26.10.0, verified).
DROPS: the live opening; capabilities: merged cells, hyperlinks, page setup, page breaks, auto-filters, comments, TSV, cell/worksheet protection (partially); "PDF output depends on locally available fonts" (live L157); the live Export example and its file-extension sentence; a section heading "PDF support" (its block now in Development and Testing); live example sections for styling, validation, protection are present as examples (kept).
CHANGES: Key Capabilities are generic restatements with fully qualified names; Scope/Development prose partly garbled.
NET: mixed (better structure and verified dependency facts; dropped capabilities and dangling prose).

# 3 Claim checks
| # | Claim | How checked | Result |
|---|---|---|---|
| 1 | PyPI aspose-cells-foss 26.10.0 | pypi.org JSON info.version | PASS |
| 2 | requires Python >=3.10 | PyPI requires_python | PASS |
| 3 | olefile>=0.46, pycryptodome>=3.15.0 | PyPI requires_dist | PASS |
| 4 | dev extras pytest>=7.0.0, pytest-cov>=4.0.0 | PyPI requires_dist extras | PASS |
| 5 | pip install aspose-cells-foss | package exists | PASS |
| 6 | source install `pip install .` | pyproject at clone root | PASS |
| 7 | Quick Start / password example APIs | Workbook(file, password=) L97; save(..., password=) L405; examples EXECUTED | PASS |
| 8 | data_validations.add("A1:A10") + DataValidationType.LIST | worksheet.py L364, data_validation.py L740 | PASS |
| 9 | save_workbook_as_csv/json/markdown are module-level functions | csv_handler.py L658, json_handler.py L181, markdown_handler.py L570 | PASS |
| 10 | pdf_exporter listed as a function | __init__.py: module/class PdfExporter | MISLEADING (introduced) |
| 11 | XML import/export via aspose.cells_foss.xml_loader / xml_saver | modules exist, imported by workbook.py | PASS |
| 12 | SkiaPdfRenderer and optional skia-python | __init__.py L67; live README says the same | PASS |
| 13 | MIT, License/LICENSE.txt, ThirdPartyNotices.txt | files present, MIT text | PASS |
| 14 | links (29) | mech.py --net: none non-200; 3 duplicate targets | PASS |
| 15 | "160 types" | not reconcilable | COULD_NOT_VERIFY |

# 4 Mechanical and wording
mech.py: one H1, required sections in order, extra Third-Party Notices (conditional, fine), one mermaid fence (the whole At a Glance), no fence without language, forbidden-wording hit only the API-table word "wrapper" in `SheetProtectionDictWrapper` (a class-description, not an implementation bridge: ruling no hit), no Enterprise Edition paragraph and none required (live links only the banner), dangling lead-ins L141 and L200 (B1). Mermaid: `flowchart LR`, Starting Points (existing XLSX file) -> product -> Core Capabilities (two columns of seven) -> Outputs (XLSX file); horizontal, zero clipped fonts (renderer check). The Outputs/Starting Points groups name only XLSX although the product exports CSV/JSON/Markdown/PDF (output group under-reports; advisory).

# 5 Omitted information in the clone
examples/ (test-style examples, linked), AGENTS.md (linked), License files (linked). Fine.

# 6 Drafted upstream issues (TEXT ONLY)
None reproduced.

# 7 Verdict
FIX_REQUIRED, MAJOR: the facts are accurate (14 of 15 checks pass, PyPI version/deps verified), but the document has dangling preserved lead-ins, repeated and fused Scope statements, duplicated licence/notice sections and dropped live capabilities. F1 and F2 need code changes (preserved-unit placement by topic and lead-in/payload coordination; duplicate-content check between preserved and authored units), so a redraw alone reproduces them. Closer to publishable than any wave-3 bundle.
