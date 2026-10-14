authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python
bundle_hash: 53e3b6893d0349d9e27dba116d4fa7290184080b66849a5d0349df8d00f33507
readme_sha256: baed95caad17be581f6b02880125b33fcf567bbd53f369f7a6c5cd512cf906ba
source_revision: 8f0edbe6930f300088fc72f64711be3265a723d1
live_head: 8f0edbe6930f300088fc72f64711be3265a723d1
reviewed_at: 2026-10-12T00:55:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run 8fbf2166 (wave 6) row NOT_READY (bundle state ACCEPTED, BC-11 pending), G:\rp-w6\pdf-python
claims_checked: 15
claims_failed: 1
forbidden_wording_hits: 1
could_not_verify: ["examples not re-run (9 EXECUTED, 9 FAILED, 2 NEEDS_INPUT receipts)", "'360 verified public types' vs the live 265", "Enterprise Edition target (links to the python-net page)"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "H1 / opening / all prose / Enterprise anchor", summary: "product name 'Aspose PDF FOSS for Python' (identity.py:product_name splits the hyphenated repository name 'Aspose-PDF-FOSS-for-Python' and loses the dot); the live name and the real product are 'Aspose.PDF FOSS for Python'"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Key Capabilities / Quick Start", summary: "five live feature lists (010.001-010.005, hundreds of verified API names and behaviours) VERIFIED_REWRITEd into eight generic bullets; the rewrite check logged 'no longer names ...' advisories; orphan preserved bullets (Merger/Splitter/..., FileDataSource, PluginOptions) after the list; Quick Start prints a second install block, a Python-floor sentence, an 'Optional extras add:' lead-in and three extras bullets (preserved Installation/Dependencies units misplaced)"}
  - {id: F3, kind: code_change, severity: MAJOR, section: "At a Glance / API Reference", summary: "diagram omits the live capability list; API Reference loses 32 of 284 live row keys and the live per-area sections (34 H3 in live, 17 in candidate)"}
  - {id: F4, kind: code_change, severity: MAJOR, section: "Installation", summary: "renderer sentence 'build it from a source checkout instead, verified against this revision:' (assurance narration, renderer.py L1113/1129/1144/1146)"}
  - {id: F5, kind: code_change, severity: MAJOR, section: "run-level", summary: "BC-11 PENDING: examples.json is rewritten with wall-clock log timestamps by every fresh process, so the no-op proof is withdrawn (third wave)"}
  - {id: F6, kind: redraw, severity: MINOR, section: "Opening / Scope", summary: "restore the live opening (open-source, MIT, creates/reads/edits/renders/validates PDF, depends on cryptography and asn1crypto, alpha status) and the two live code-block-backed capabilities lost; the opening names only html/md/svg/png outputs"}
blocking_findings:
  - {id: B1, category: false_claim, section: "H1 and prose", evidence: "live-README L1 '# Aspose.PDF FOSS for Python'; cand README L1 '# Aspose PDF FOSS for Python'", summary: "canonical product name truncated (introduced); reviewer advisory F01 says the same"}
  - {id: B2, category: dropped_live_content, section: "Key Capabilities / Opening / Additional Examples", evidence: "retention.py: CORE 44% verbatim, 54% lost: 98 of 140 live sentences, 74 of 151 live list items, 12 of 24 code blocks lost; live opening and alpha status dropped", summary: "far less verified information than the live README"}
  - {id: B3, category: demoted_finding_true, section: "Key Capabilities", evidence: "validation.json advisory: 010.001-010.005 'the rewrite no longer names ...' (5 lists); review.json advisory F01, F03, F04, F05, F06 are true", summary: "five true advisories demoted"}
  - {id: B4, category: forbidden_wording, section: "Installation", evidence: "cand README L81 'verified against this revision'", summary: "assurance narration"}
  - {id: B5, category: dangling_prose, section: "Quick Start / Key Capabilities", evidence: "cand README L66-76 (orphan bullets), L147-166 (second install block, 'Optional extras add:')", summary: "orphan preserved fragments in the wrong sections"}
---

# 1 Bundle facts
Bundle state ACCEPTED, not READY_FOR_PROPOSAL: BC-01..BC-14 all PASS except BC-11 PENDING; review ACCEPT (as returned ACCEPT) with 7 advisory presentation findings; second read triggered by ADVISORY_DEFERRAL; no-op VERIFIED in the first run but present-2 reports "re-sealed: examples.json changed since the last seal; proof withdrawn". Revision equals live head. Examples: 9 EXECUTED, 9 FAILED, 2 NEEDS_INPUT. Rulings on the advisories: F01 (truncated name, alpha status) TRUE; F02 (diagram omits the live capability list; the live diagram is vertical with 3 clipped fonts, the candidate's is horizontal) mixed: content point true; F03 TRUE; F04 TRUE in part (the virtual-environment install is in Quick Start); F05 TRUE; F06 (360 vs 265 types) not reconcilable; F07 not borne out (the candidate does carry the JPEG 2000 and export limitations). Validation advisories 010.001-010.005 ("the rewrite no longer names ...") are TRUE and large: hundreds of verified API names and behaviours of the live feature lists are gone.

# 2 Live comparison
The live README is already template-conformant (Navigation, At a Glance, ... License), 1213 lines, 34 H3 sections, 24 code blocks, 284 API-table rows.
ADDS (true): Dependencies split into required/optional/native/dev with versions (matches pyproject), `python_requires >=3.11`, the source-checkout install and import smoke test, 328 test files (verified), CI matrix 3.11/3.12/3.13 (verified), links to supported-features.md, SECURITY.md, CHANGELOG.md, AGENTS.md (exist), a lowcode capability list (the classes exist).
DROPS (valuable): the opening; alpha status; the page-size/colour/text/font/ facade/redaction/export capability lists; 12 of 24 code blocks (many examples FAILED receipts here, so some drops are correct); 98 prose sentences; Python 3.11 floor stated in prose; the live Mermaid.
CHANGES: product name misspelled; Scope rebuilt from preserved fragments, partly as bare bullets after a blank line.
NET: worse.

# 3 Claim checks
| # | Claim | How checked | Result |
|---|---|---|---|
| 1 | "not yet published on PyPI" | pypi.org JSON for aspose-pdf-foss-for-python and aspose-pdf-foss: 404 | PASS |
| 2 | python_requires >=3.11 | pyproject L9 | PASS |
| 3 | required deps cryptography>=50, asn1crypto>=1.5 | pyproject L18-19 | PASS |
| 4 | optional extras images/woff2/text-layout/fuzz | pyproject | PASS |
| 5 | "328 test files under tests/" | find tests -name 'test_*.py' = 328 | PASS |
| 6 | ci runs 3.11, 3.12, 3.13 | ci.yml L45 | PASS |
| 7 | Document.save_as_html/markdown/svg, save_page_as_image, validate_pdfa/pdfua, auto_tag, convert_to_pdfa, redact_text | grep in src/aspose_pdf (11 defs) | PASS |
| 8 | PdfLoadLimits, PdfResourceLimitException | load_limits.py L14, exceptions.py L63 | PASS |
| 9 | lowcode Merger/Splitter/Optimizer/TextExtractor are PdfPlugin subclasses | lowcode.py L501-560 | PASS |
| 10 | supported-features.md, SECURITY.md, CHANGELOG.md, AGENTS.md, scripts/check.sh, build.sh exist | ls | PASS |
| 11 | MIT, LICENSE | clone | PASS |
| 12 | product name "Aspose PDF FOSS for Python" | live README L1 and real product 'Aspose.PDF' | FAIL (introduced) |
| 13 | Quick Start example runs | receipts: example 3 EXECUTED; the Quick Start's `document.info`/`page_count` not re-run | COULD_NOT_VERIFY |
| 14 | links (35) | mech.py --net: none non-200; 4 duplicate targets | PASS |
| 15 | "360 verified public types" | not reconcilable with the live 265 | COULD_NOT_VERIFY |

# 4 Mechanical and wording
mech.py: sections in order, required present, one mermaid fence, no forum link, Enterprise anchor shape ok (anchor text uses the truncated name "full-featured Aspose PDF for Python"), 8 wording hits all in API-table class descriptions ("wrapper", "backed by": ruling: class docstrings, not an implementation bridge between platforms) except none blocking; by reading: L81 "verified against this revision" (assurance narration, blocking). Mermaid: `flowchart LR` with Starting Points, product, Capabilities, Outputs; horizontal, zero clipped fonts (rendered), though it names fewer capabilities than the live diagram.

# 5 Omitted information in the clone
The live README's own feature lists, many examples (several FAILED receipts), docs pages (supported-features.md is linked).

# 6 Drafted upstream issues (TEXT ONLY)
1. Several README examples fail on a clean checkout at this revision (9 of 20 receipts FAILED: e.g. examples 1, 2, 7, 8, 10, 11 raise at `document.save`/signing; stderr is in examples.json). Severity medium. Reproduce: run each fenced example in a venv after `pip install .`. Not reproduced by me independently: possible, unreproduced.
2. pyproject says `Development Status :: 4 - Beta` while the README says "currently in alpha". Severity low.

# 7 Verdict
DO_NOT_PROPOSE (MAJOR): the live README is already conformant, longer and richer; the candidate keeps 44% of its verified content, drops the alpha notice and five feature lists, misnames the product and prints assurance narration. Everything that would repair it is a code change (name derivation, preserved-unit placement, rewrite-loss gate promoted from advisory to blocking, renderer wording). It also cannot seal yet (BC-11, timestamp normalisation).
