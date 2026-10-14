authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-note-foss/Aspose.Note-FOSS-for-Python
bundle_hash: 28ff48f29afc865c2beb6bc9bba38e9f7d44aee8e5f741ee1c6e56e9bf44d83d
readme_sha256: ef942b8869bb00af249d421e415e5117c63c4807bcf259be33911ef4c22cd287
source_revision: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
live_head: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
reviewed_at: 2026-10-11T19:25:00Z
verdict: FIX_REQUIRED
minor_major: MAJOR
net_vs_live: mixed
confidence: medium
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run e407503a (wave 5), sealed bundle G:\rp-w5\note-python
claims_checked: 14
claims_failed: 2
forbidden_wording_hits: 0
could_not_verify: ["Quick Start / examples not re-run (receipts only)", "'39 public types' (live number) vs 37 table rows", "Enterprise Edition target page"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Quick Start", summary: "four preserved paragraphs/bullet lists of the live Dependencies section (Python floor, 'No required third-party package dependencies', reportlab/pypdf/Pillow/PyMuPDF and build/twine bullets) are printed at the end of Quick Start after the [pdf] block (preserve placement by topic fallback)"}
  - {id: F2, kind: redraw, severity: MINOR, section: "Scope and Limitations", summary: "bullet 4 says Document.GetPageHistory is 'present only for API-shape compatibility' (false: it returns the real page history, and Key Capabilities say it works); bullets 1/2/3/4 are restated by the closing 'The following are not implemented' bullet"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Documentation & Resources", summary: "'all 39 public types. It covers all 37 verified public types' contradicts itself (live number retained, composer count added); 37 rows in the table"}
  - {id: F4, kind: redraw, severity: MINOR, section: "Key Capabilities / Opening", summary: "garbled code spans ('`Title`, Author, `CreationTime`, and Level', 'Bytes', 'Accept methods'); opening 'reads .one files and writes .pdf files' (live: read-only, PDF export) and invented-sounding 'supporting no dependency on Microsoft OneNote'"}
blocking_findings:
  - {id: B1, category: dangling_prose, section: "Quick Start", evidence: "cand README L130-141: after the [pdf] block, 'Requires Python 3.10 or later. The PyPI distribution is named ...', 'No required third-party package dependencies.', reportlab/pypdf/build bullets", summary: "orphan preserved fragments in the wrong section"}
  - {id: B2, category: false_claim, section: "Scope and Limitations", evidence: "src/aspose/note/model.py L1292 'def GetPageHistory(self, page) -> PageHistory: return self._page_histories.get(...)'; live L451-452 lists only License/Metered/DetectLayoutChanges as compatibility stubs", summary: "INTRODUCED: GetPageHistory declared a compatibility stub"}
  - {id: B3, category: dangling_prose, section: "Documentation & Resources", evidence: "cand README L486: 39 vs 37", summary: "self-contradicting type count (introduced by combining live text and composer count)"}
  - {id: B4, category: dangling_prose, section: "Scope and Limitations", evidence: "cand README L491-498", summary: "same limitations stated twice (bullets 1-5 and the closing 'not implemented' bullet)"}
---

# 1 Bundle facts
READY_FOR_PROPOSAL; revision == live head; README sha256 == manifest; no-op VERIFIED; validation all PASS; review ACCEPT (as returned ACCEPT), no demoted findings. This is the wave-3 repository whose [pdf] extra was dropped: the extra is now carried (Quick Start and Dependencies). Wave-3 acceptance had 7 failed claims; this candidate has 2.

# 2 Live comparison
ADDS (true): Optional Dependencies split (reportlab>=3.6 extra pdf; Pillow, PyMuPDF, pypdf test-pdf; build/twine dev: all equal PyPI requires_dist), PyPI version 26.9.0 (PASS), source install `pip install .`, `python -c "import aspose.note"`, "12 test files" (12 test_*.py modules), ci matrix 3.10/3.11/3.12 (PASS), links to workflows.
DROPS: a few capability sentences (lost 9 of 31 sentences, 23 of 108 list items; table keys 40 of 42 kept); live lead-ins; the Mermaid in the live README is vertical with 3 clipped fonts, the candidate's is horizontal and unclipped (improvement).
CHANGES: Key Capabilities rewritten as long sentences; Scope adds the false GetPageHistory clause; Dependencies are better structured than live.
NET: mixed (better Dependencies/Installation and diagram, worse Scope and Quick Start).

# 3 Claim checks
| # | Claim | How checked | Result |
|---|---|---|---|
| 1 | PyPI aspose-note-foss 26.9.0 | pypi.org JSON | PASS |
| 2 | requires Python >=3.10 | PyPI requires_python | PASS |
| 3 | extra pdf = reportlab>=3.6 | PyPI requires_dist | PASS |
| 4 | extras test-pdf and dev packages and bounds | PyPI requires_dist | PASS |
| 5 | `pip install "aspose-note-foss[pdf]"` | extra exists | PASS |
| 6 | No required third-party dependencies | PyPI requires_dist has only extras | PASS |
| 7 | SaveFormat declares only Pdf | enums.py L6-7 | PASS |
| 8 | SetLicense/Metered no-ops | model.py L118-119 | PASS |
| 9 | Document.GetPageHistory is a compatibility stub | model.py L1292 real implementation | FAIL (introduced) |
| 10 | "12 test files under tests/" | 12 test_*.py (15 .py with helpers) | PASS |
| 11 | ci runs Python 3.10, 3.11, 3.12 | ci.yml matrix | PASS |
| 12 | "39 public types ... 37 verified" | live says 39; table has 37 rows | MISLEADING (introduced) |
| 13 | links (36) | mech.py --net: none non-200; 4 duplicate targets | PASS |
| 14 | MIT, LICENSE present | clone LICENSE | PASS |

# 4 Mechanical and wording
mech.py: sections in order, required present, Third-Party Notices extra (fine), one mermaid fence; zero forbidden wording; one suspect hit L495 "API-shape compatibility with the commercial product ... no-ops in this edition" (inherited from the live README, names no edition; ruling: not a forbidden label, but "this edition" is edition-adjacent: advisory). Mermaid: `flowchart LR`, Starting Points (existing ONE file) -> product -> two columns of capabilities -> Outputs (PDF), horizontal, zero clipped fonts (rendered). Dangling lead-ins: none flagged by mech, but B1 is a block of orphan dependency prose.

# 5 Omitted information in the clone
CHANGELOG-type files: none; `examples/` carried in the live; `tools/regenerate_pdf_goldens.py` carried; language-agnostic-plan and legacy dirs (internal).

# 6 Drafted upstream issues (TEXT ONLY)
None.

# 7 Verdict
FIX_REQUIRED, MAJOR: facts mostly verified and the previously dropped [pdf] extra is carried, but two introduced false/misleading statements and the Quick Start orphan block need a redraw plus a placement code change (F1). Not DO_NOT_PROPOSE: fewer than three introduced FAIL/MISLEADING claims and the candidate is better than the live README on Dependencies and the diagram.
