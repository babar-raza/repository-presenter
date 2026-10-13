authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-note-python: aspose-note-foss/Aspose.Note-FOSS-for-Python (registry entry 28)

---
repository: aspose-note-foss/Aspose.Note-FOSS-for-Python
bundle: lfix/out/aspose-note-foss__Aspose.Note-FOSS-for-Python (snapshot copy acc2s2/bundles/aspose-note-foss__Aspose.Note-FOSS-for-Python)
bundle_manifest_sha256: 3e9959a83ff7c43a99d8e0a3cc0ed18c6d7badcc9226ea3928d9075a34e14539
corrected_readme_sha256: 38dd13156e488484ec0075427828d181f3daa9438a59aef9b17a21611e990d8b
original_readme_sha256: 1ca057674c1642628145d08f31d3db4e47a71800f256e99b65bdf1623851d48a
source_revision: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
live_head: 0fd1cf7bcadb279a6dd73ddcba3d5241376badd3
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: mixed
claims_checked: 8
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MINOR, section: Development and Testing, summary: python -m build needs pip install build (or .[dev]); drop the hunk or add the install line}
blocking_findings:
  - {id: B1, category: false_claim (misleading), section: Development and Testing, evidence: clean venv: No module named build, summary: documented command fails as written}
could_not_verify:
  - hosted github.com Mermaid rendering
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 28), ('MISSING_INFO', 'add_dev_commands', 521)], patch 1660 bytes (+22/-13 lines).
- Live head 0fd1cf7b equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 17 HTML foreignObject labels, clipped in fonts {'Arial': 2, 'Verdana': 5, 'Georgia': 4} (lane's own `check_entry`: 49 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.Note-FOSS-for-Python.live.0.png` and `acc2s2/png/Aspose.Note-FOSS-for-Python.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L28) | same labels/edges, horizontal, not clipped | own parser; rendered 4 releases x 5 fonts; PNG viewed | PASS |
| 2 | add_dev_commands L521: `To build from a clone, run:` + `python -m build` | the command works from a clone | throw-away venv (`python -m venv`, no packages): `python -m build` -> `No module named build` (reproduced). After `pip install build`, `python -m build` in a copy of the clone built sdist and wheel 26.9.0 | FAIL (precondition missing, introduced) |
| 3 | where `build` is declared | README prerequisites | the install line is `python -m pip install -e ".[pdf,test-pdf]"`; `build`/`twine` are in pyproject extra `dev` and README L98 says they are "not needed to use or test the library" | MISLEADING as a bare command |
| 4 | placement | after the last `</details>` | the preceding text (inside details) already says `publish-pypi.yml` shows the exact release-time commands; the new block sits detached at top level, before License | minor (detached) |

## 5. Live comparison

- ADDS: horizontal diagram (better); a build command that fails on a clean environment as written.
- DROPS: none. CHANGES: Mermaid body only.
- NET: mixed (diagram better; dev hunk worse for a first-time reader).
- Governance note: `allowed` BC-07 +5 under R7 (live 13 -> 18). `commercial product` hit at L454 is inherited from live (License/Metered no-op note).

## 6. Verdict

FIX_REQUIRED, MINOR. Diagram hunk PUSHABLE alone. Drop the build hunk or prefix `python -m pip install build` (or `.[dev]`). Same generator defect as set 1's 3D-Python (CI-derived command without its setup line).
