authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-slides-foss/Aspose.Slides-FOSS-for-Python
bundle_hash: 0f19b6e1fb68879d5d176db196da3aa3ca3dddcf0d1a1c5de27f9325c89528f6
readme_sha256: 7bb717c2a29618bdfce90447840c0eead4d9db02e98794fffac5099cfaa646d6
source_revision: 4e63447ba79d1c27a5192844847d9f872c5b92ad
live_head: 4e63447ba79d1c27a5192844847d9f872c5b92ad
reviewed_at: 2026-10-12T01:55:00Z
verdict: FIX_REQUIRED
minor_major: MAJOR
net_vs_live: mixed
confidence: medium
reviewer: independent acceptance reviewer (Sonnet 5.5), not the candidate's author; run 8fbf2166 (wave 6) SEALED row, G:\rp-w6\slides-python
claims_checked: 14
claims_failed: 1
forbidden_wording_hits: 0
could_not_verify: ["'SmartArt, OLE objects and mathematical text raise NotImplementedError' (inherited, not reproduced)", "'516 verified public types' count", "Quick Start executed only via receipts (14 EXECUTED, 1 FAILED)", "Enterprise Edition target page"]
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "At a Glance", summary: "diagram Starting Points reads 'An existing PNG file' (live: 'An existing .pptx presentation') and Outputs only 'PPTX file' (live: .pptx presentation and Markdown text); Core Capabilities shows 8 of the live 12 nodes (animations, theming, 3D styling, document properties, Markdown export dropped)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "Scope and Limitations / Documentation & Resources", summary: "preserved inherited fragments printed as extra bullet groups in the wrong section: Scope carries the Python floor and the 15-job CI matrix (also stated in Development and Testing), three separate unlabeled bullet groups; Documentation & Resources ends with a stray paragraph repeating agents.md and CONTRIBUTING.md with a raw URL in parentheses (both already listed above)"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Opening / Key Capabilities", summary: "Markdown export (SaveFormat.MD, 24 flavors) is stated only in Scope; the opening, capabilities and diagram omit it; also dropped: hyperlinks, themes, 3D formatting, document properties, animation sequences, the 'always use a context manager' advice and the live opening"}
  - {id: F4, kind: data_change, severity: MINOR, section: "Additional Examples", summary: "the live Markdown export example is dropped because its receipt FAILED (ValueError: slides [2, 1] not present): the verification harness gave a one-slide input.pptx, while the example is valid for a deck of two or more slides; classify as NEEDS_INPUT or give the harness a two-slide fixture"}
blocking_findings:
  - {id: B1, category: false_claim, section: "At a Glance", evidence: "cand README L26-57 vs live L29-62: Starting Points 'An existing PNG file'; Outputs 'PPTX file' only", summary: "MISLEADING (introduced): the diagram misstates what the library starts from and what it writes"}
  - {id: B2, category: dangling_prose, section: "Scope and Limitations", evidence: "cand README L1001-1020 (bullet groups after a blank line: Python floor, CI matrix)", summary: "non-limitations and duplicate statements printed as limitations"}
  - {id: B3, category: dangling_prose, section: "Documentation & Resources", evidence: "cand README L977-981 (stray 'See agents.md ... and CONTRIBUTING.md (https://...)' paragraph; duplicate targets agents.md and CONTRIBUTING.md)", summary: "orphan preserved fragment duplicating two list items"}
  - {id: B4, category: dropped_live_content, section: "Opening / Key Capabilities / Additional Examples", evidence: "retention.py: CORE 54% verbatim, 45% lost: 47 of 73 live sentences, 73 of 151 list items (most rewritten as 8 capabilities); Markdown export example lost", summary: "valuable live capability (Markdown export) missing from the visitor-facing summary"}
---

# 1 Bundle facts
READY_FOR_PROPOSAL, revision == live head, README sha256 == manifest, no-op VERIFIED (33 provider calls in run 1, 0 in the fresh-process rerun), validation BC-01..BC-12 and BC-14 PASS (12 pass, 0 fail, 1 pending before the proof), review ACCEPT (as returned ACCEPT), 0 findings, second read triggered by ADVISORY_DEFERRAL (read 2, nothing corroborated). 28 coverage advisories, all API_LISTING_COVERED_BY_CORE_API (ruling: true; the API tables carry 267 of 267 live row keys). Examples: 14 EXECUTED, 1 FAILED. This is the wave-3 sealed repository that failed on a 2,254-character cut-off bullet, missing version-skew warning and a missing Enterprise paragraph: all three are fixed here.

# 2 Live comparison
The live README is template-conformant (Navigation ... License), 1013 lines. Candidate: 1039 lines, same sections in the same order.
ADDS (true): Dependencies section with versions (lxml>=4.9; extras test: pytest>=7, python-pptx>=1.0; python_requires >=3.10; all equal pyproject), source-checkout install and import smoke test, the PyPI-predates-source warning and git+https install (TRUE: CHANGELOG [Unreleased] says none of the changes are in 26.8.0), the namespace-package warning (kept from live), 44 test files, CI matrix 15 jobs (verified), Enterprise Edition paragraph (anchor shape correct), links to repository documents.
DROPS: see B4; also the live opening (official, open-source, models PowerPoint's object model, no Microsoft Office), "use `with` so the package is disposed", the live Mermaid's .pptx starting point and Markdown output.
CHANGES: Key Capabilities now eight action-led bullets with symbol names (better to read than the live 14-item list but loses items); API tables identical in keys (better: 267/267 kept).
NET: mixed (better Dependencies/Installation/diagram geometry; worse diagram content, Scope structure and capability coverage).

# 3 Claim checks
| # | Claim | How checked | Result |
|---|---|---|---|
| 1 | PyPI aspose-slides-foss 26.8.0 | pypi.org JSON info.version | PASS |
| 2 | python_requires >=3.10 | PyPI and pyproject L16 | PASS |
| 3 | lxml>=4.9 required; extras test pytest>=7, python-pptx>=1.0 | PyPI requires_dist, pyproject L49-61 | PASS |
| 4 | "44 test files under tests/" | find tests -name 'test_*.py' = 44 | PASS |
| 5 | CI on Ubuntu/Windows/macOS x 3.10-3.14 = fifteen jobs | ci.yml L39-40 | PASS |
| 6 | PyPI release predates the source tree; none of the [Unreleased] changes in 26.8.0 | CHANGELOG L8-11 | PASS |
| 7 | ChartType has 74 types | ChartType.py enum members = 74 | PASS |
| 8 | SaveFormat declares Ppt, Pdf, Xps, Tiff, Odp, Html, Swf, Otp ...; other formats raise ValueError naming the supported ones | SaveFormat.py; Presentation.py L507-512 | PASS |
| 9 | TextAnimation.add_effect stubbed, raises NotImplementedError | TextAnimation.py L255 | PASS |
| 10 | Presentation.sections does not exist | no `sections` in Presentation.py | PASS |
| 11 | Quick Start imports (`aspose.slides_foss.export.SaveFormat`) and flow | SaveFormat.py in export/; example receipts EXECUTED (the Quick Start is among the 14) | PASS |
| 12 | diagram Starting Points "An existing PNG file", Outputs "PPTX file" | live README diagram: ".pptx presentation" in; ".pptx" and "Markdown text" out | MISLEADING (introduced) |
| 13 | MIT, LICENSE | clone LICENSE | PASS |
| 14 | links (43) | mech.py --net: none non-200; 6 duplicate targets (#api-reference, agents.md, CONTRIBUTING.md, ci.yml, publish.yml, LICENSE) | PASS |

# 4 Mechanical and wording
mech.py: sections in order, required present, one mermaid fence (the whole At a Glance), every fence has a language, no forum link, Enterprise Edition anchor shape ok, three "backed by" hits in API-table type descriptions (`DoubleChartValue`: "a double value backed by a workbook cell"): ruling not a platform bridge. "commercial `aspose` package" in the namespace warning (inherited from the live README): names a product, not an edition: borderline, not a forbidden label. The 'assurance narration' phrase "verified against this revision" is absent (the published package makes the renderer print the plain install). Mermaid: `flowchart LR`; Starting Points -> product -> Core Capabilities (two columns of four) -> Outputs; rendered with the repository's Edge/mermaid check: horizontal, zero clipped fonts (live diagram: vertical, 5 clipped fonts). The only defect is content (B1).

# 5 Omitted information in the clone
CHANGELOG [Unreleased] entry (linked and summarised in Quick Start), CONTRIBUTING, SECURITY, CODE_OF_CONDUCT (all linked), type-hint marker not applicable, `tests/` conformance suite using python-pptx (mentioned only as a dev extra).

# 6 Drafted upstream issues (TEXT ONLY)
1. README Markdown example fails with a one-slide input: `prs.save("subset.md", [2, 1], SaveFormat.MD, options)` raises `ValueError: 'slides' array contains 2 slide position, which is not present in the presentation.` Severity low (documentation clarity). Fix: say "for a deck with at least two slides". Reproduce: run the example against a one-slide deck (receipt in examples.json ordinal 15).

# 7 Verdict
FIX_REQUIRED, MAJOR. This is the best-quality sealed candidate reviewed so far: facts verified (13 of 14 checks pass), previously blocking wave-3 defects are gone, mechanics clean. What keeps it from AUTHORIZABLE: the diagram's Starting Points/Outputs contradict the live README (PNG instead of .pptx; no Markdown), Scope and Documentation & Resources carry preserved fragments that do not belong there (F2: a placement code change shared with every other bundle), and the visitor-facing capabilities omit Markdown export. A redraw fixes F3; F1 and F2 need code changes (diagram input/output derivation and preserved-unit placement). Compared with the live README it is not worse on any verified command or version.
