authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-python: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python (registry entry 30, live head 8f0edbe6)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose-PDF-FOSS-for-Python/` (code branch wt/lfix-fix01).

**Verdict: PUSHABLE** | minor_major: none | Single DIAGRAM_FIX; label-identical redraw, horizontal, no clipping.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`, HEAD `8f0edbe6930f300088fc72f64711be3265a723d1` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `3c933cf1495d18166e3bc7ea70e59129caa5ea0cdc698d0625bf604cc9316a1d` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L30 | At a Glance redrawn LR | Labels (15), subgraph titles (4), edges (3) and per-group order identical to live (own regex parse, `cmpdiag.py`, `cmpord.py`). PNG viewed: three mother blocks left to right, capability block split into two columns (document/text/page on the left, forms/annotations/security on the right), boxes sized by their text, no clipped text. | PASS |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose-PDF-FOSS-for-Python.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 3 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).
- Cosmetic only: the two capability columns are very tall with wide vertical gaps between boxes (rank spacing from the `~~~` chain); readable, not clipped.

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 366 vs corrected failures 365 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
No fixes required.

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Live README carries 8 'wrapper' / 'backed by' hits in API-table class descriptions (judged not an implementation bridge); `#api-reference` and `LICENSE` link targets appear twice. Inherited, unchanged.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
