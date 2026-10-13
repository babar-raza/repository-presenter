authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-slides-python: aspose-slides-foss/Aspose.Slides-FOSS-for-Python (registry entry 40, live head 4e63447b)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-slides-foss__Aspose.Slides-FOSS-for-Python/` (code branch wt/lfix-fix01).

**Verdict: PUSHABLE** | minor_major: none | Single DIAGRAM_FIX; label-identical, horizontal, no clipping; two inherited counts carried by the diagram verified true.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-slides-foss/Aspose.Slides-FOSS-for-Python`, HEAD `4e63447ba79d1c27a5192844847d9f872c5b92ad` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `399eb9dcd7fbdc7859ca1cb3e107fc9e98952f09568d917285ebd80e16d9e428` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L29 | At a Glance redrawn LR | Labels (16), titles, edges, order identical. PNG viewed: 6 + 6 capability columns, two outputs; clean. Spot-checked two inherited numbers the diagram carries: `aspose/slides_foss/charts/ChartType.py` has 74 members ('74 chart types' PASS); `aspose/slides_foss/export/Flavor.py` has 24 members ('24 flavor dialects' PASS). | PASS |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.Slides-FOSS-for-Python.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 319 vs corrected failures 324 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
No fixes required.

## 6. Inherited from the live README (not introduced, not edited by the patch)
- PyPI aspose-slides-foss latest is 26.8.0, matching the live README's 'pip install gets 26.8.0' paragraph (L134).

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
