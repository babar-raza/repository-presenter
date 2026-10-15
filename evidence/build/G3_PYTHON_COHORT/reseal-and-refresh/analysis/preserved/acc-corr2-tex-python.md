authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-tex-python: aspose-tex-foss/Aspose.TeX-FOSS-for-Python (registry entry 41, live head 181015d2)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-tex-foss__Aspose.TeX-FOSS-for-Python/` (code branch wt/lfix-fix01).

**Verdict: PUSHABLE** | minor_major: none | Single DIAGRAM_FIX, clean; a hold is advisable only on owner policy because the library cannot be imported (upstream defect).

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`, HEAD `181015d2eee3e19f8af3d84e4a932ac84ad47c7c` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `635d14cc378d531caf2add69298cf125285602b59e969f288918c1a58f2dc226` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L29 | At a Glance redrawn LR | Labels (9), titles, edges, order identical. PNG viewed: clean. | PASS |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.TeX-FOSS-for-Python.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 4 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).
- Upstream defect re-confirmed at head 181015d2: `ast.parse` fails on 35 of 45 `src/**/*.py` files (for example `_engine/box_builder.py` L63, 'expected an indented block after for statement'); the diagram's capabilities describe code that cannot run at this head. That is the maintainers' defect, not a README edit; the patch adds no claim and removes none.

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 162 vs corrected failures 165 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
No fixes required.

## 6. Inherited from the live README (not introduced, not edited by the patch)
- The issue handoff for the unparsable sources stays a lane item (not a README change).

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
