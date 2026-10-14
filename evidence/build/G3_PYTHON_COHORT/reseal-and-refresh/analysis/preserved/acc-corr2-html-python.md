authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-html-python: aspose-html-foss/Aspose.HTML-FOSS-for-Python (registry entry 26)

---
repository: aspose-html-foss/Aspose.HTML-FOSS-for-Python
bundle: lfix/out/aspose-html-foss__Aspose.HTML-FOSS-for-Python (snapshot copy acc2s2/bundles/aspose-html-foss__Aspose.HTML-FOSS-for-Python)
bundle_manifest_sha256: 8fb14ccfe2dc23bdc2d289ab5f182783d5b9e9cbaa14b1a99eb71d858d1dc5fe
corrected_readme_sha256: 67857d2da1fec909946493a38d3bede267455419293196126fc8bb9bdde096c7
original_readme_sha256: a5faac70e76cbeac20a4c110a1ce7a692411639a7c44ef2ab2679e4657144f00
source_revision: bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11
live_head: bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11
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
  - hosted github.com Mermaid rendering of the init directive (local render only)
  - diagram claims themselves (inherited from live) not re-verified against source
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 26)], patch 2121 bytes (+20/-16 lines).
- Live head bf0f1e7a equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 19 HTML foreignObject labels, clipped in fonts {'Arial': 1, 'Verdana': 8, 'Georgia': 3} (lane's own `check_entry`: 73 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.HTML-FOSS-for-Python.live.0.png` and `acc2s2/png/Aspose.HTML-FOSS-for-Python.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L26) | same labels/edges, horizontal, not clipped | own parser (11 nodes, 5 subgraphs incl. two capability columns); rendered 4 releases x 5 fonts; PNGs viewed | PASS |
| 2 | no other change | confinement | replay, `git apply`, hunks inside span | PASS |

## 5. Live comparison

- ADDS: horizontal redrawn diagram only. DROPS: none. CHANGES: Mermaid body only (title `Inputs and formats` kept).
- NET: better. The live diagram was vertical with 19 foreignObject labels and clipped in Arial/Verdana/Georgia.
- Governance note: `validation_delta.json` records `allowed` BC-07 +6 failures under R7 (live 19 -> corrected 25): the old BC-07 rule counts `<br/>`-joined words as over-long tokens and still names `flowchart TD`. The owner should know that a run of the old BC-07 over this README reports 6 more At a Glance failures.
- Inherited, untouched: the table rows `HTMLDetailsElement` etc. are fine; `wrapper`/`backed by` hits are API-table descriptions of classes (not implementation bridges), same as live.

## 6. Verdict

PUSHABLE (diagram only), no minor/major findings in the patch.
