authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-page-python: aspose-page-foss/Aspose.Page-FOSS-for-Python (registry entry 29)

---
repository: aspose-page-foss/Aspose.Page-FOSS-for-Python
bundle: lfix/out/aspose-page-foss__Aspose.Page-FOSS-for-Python (snapshot copy acc2s2/bundles/aspose-page-foss__Aspose.Page-FOSS-for-Python)
bundle_manifest_sha256: d875b0990c1cb427797e404939c8b895f0d701f6987b85639405836ba4508739
corrected_readme_sha256: 29f6dc718420731e74a66cead4d799ddcdc2d71b8538960d06f5de3326fa669f
original_readme_sha256: 2018a53f745f96370b49ac41f56afd062c07834693623dafe0997c47875bb81e
source_revision: 43cef367cd0b2cf00cc03064ca9d29d1ff507967
live_head: 43cef367cd0b2cf00cc03064ca9d29d1ff507967
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: PUSHABLE
minor_major: NONE
net_vs_live: better
claims_checked: 5
claims_failed: 0
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - none
blocking_findings:
  - none
could_not_verify:
  - hosted github.com Mermaid rendering
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 31)], patch 2005 bytes (+21/-16 lines).
- Live head 43cef367 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 19 HTML foreignObject labels, clipped in fonts {'Arial': 1, 'Verdana': 5, 'Segoe UI': 1, 'Georgia': 3} (lane's own `check_entry`: 67 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.Page-FOSS-for-Python.live.0.png` and `acc2s2/png/Aspose.Page-FOSS-for-Python.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L31) | same labels/edges, horizontal, not clipped | own parser (11 nodes, 5 subgraphs, two capability columns); rendered 4 releases x 5 fonts; PNG viewed (2005-byte patch, same as the owner table) | PASS |
| 2 | no other change | confinement | replay, `git apply` | PASS |

## 5. Live comparison

- ADDS: horizontal redrawn diagram only (title text kept, "Nothing — authored from scratch" starting point kept). DROPS: none. CHANGES: Mermaid body only.
- NET: better. Natural width 1826 px (about 0.45 scale in an 830 px column; the live vertical one was 0.52 but clipped in 5 fonts, so text size is similar, not a regression).
- Governance note: `allowed` BC-07 +7 under R7 (live 11 -> 18).
- Inherited, untouched and NOT introduced: the documented source build fails on a clean clone. README L98-104 uses `python package.py build` / `make sync` and says the wheel version comes from `local/Version.txt`; `local/` is git-ignored (`.gitignore` L9) and absent in the clone (`ls clones/.../local` -> not found). An earlier reviewer reproduced the failure; I confirmed the precondition is still absent. `pip install aspose-page-foss` from PyPI is unaffected. Upstream issue material, not a README edit in this bundle.
- Bundle currency: the lane's second pass rewrote `lfix/out` during my review (the Page directory was briefly absent while it cloned the 1.1 GB repository); the regenerated Page `README.md` is byte-identical to the copy I reviewed (`cmp`), as are the other fifteen of my bundles.

## 6. Verdict

PUSHABLE (diagram only).
