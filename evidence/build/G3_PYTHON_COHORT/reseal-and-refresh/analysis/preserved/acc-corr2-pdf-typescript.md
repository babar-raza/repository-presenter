authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-typescript: aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript (registry entry 34, live head c672b391)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript/` (code branch wt/lfix-fix01).

**Verdict: PUSHABLE** | minor_major: none | Single DIAGRAM_FIX; label-identical, horizontal, no clipping.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`, HEAD `c672b3918318ccd0c13bc9dc619620cac2674c9e` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `125aa80ad4b7d2b85462cf571a97fd738f3d04f28d8c37f7f51674298da0a4f1` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L32 | At a Glance redrawn LR | Labels (16), titles, edges, per-group order identical. PNG viewed: three start points, two capability columns (5 + 4), three outputs; all text inside its box. | PASS |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.PDF-FOSS-for-TypeScript.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 2462 vs corrected failures 2465 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
No fixes required.

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Link/anchor noise in a 4,600-line README, none touched by the patch: shields badge `Node.js->=22%2B` returns 400; anchors `#forms`, `#markdown`, `#redaction`, `#annotations`, `#set-viewer-preferences`, `#convert-an-xfa-form-to-an-acroform` do not exist.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
