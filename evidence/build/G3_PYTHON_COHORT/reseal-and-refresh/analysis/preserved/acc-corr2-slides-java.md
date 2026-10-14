authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-slides-java: aspose-slides-foss/Aspose.Slides-FOSS-for-Java (registry entry 39, live head 620a2614)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MINOR | Diagram redraw is good; the added build/test block duplicates, and half contradicts, the section's own one-command route.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`, HEAD `620a2614418854b4a18966a361e6907ddc88c7cb` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `917e87af28bd7e496991f18b535ccb655703db2f7815b7c1913676c2a6378f62` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L35 | At a Glance redrawn LR | Labels (12), titles, edges, order identical. PNG viewed: clean. | PASS |
| MISSING_INFO add_dev_commands L848 | appends 'To build and run the tests from a clone, run:' + `mvn -B --no-transfer-progress clean package -DskipTests -Dgpg.skip=true` / `mvn test` | The commands exist (`.github/workflows/build.yml` L78 runs `clean verify`; the `clean package -DskipTests -Dgpg.skip=true` line is the build-twice reproducibility step, L125/L127). But the live section opens with `git clone ...; cd ...; mvn verify -Dgpg.skip=true` and says 'That one command runs the whole test suite', so the new block offers a second, different route (skip tests, then test) to the same end, and lands after the SECURITY.md sentence at the end of the section. `mvn` is not installed here; not run. | MISLEADING-by-duplication (redundant, not false) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.Slides-FOSS-for-Java.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 314 vs corrected failures 319 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MINOR | Development and Testing | drop the add_dev_commands edit (duplicate of, and inconsistent with, the `mvn verify -Dgpg.skip=true` 'one command'); keep the diagram hunk |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Version pin 26.7.0 equals Maven Central latest (maven-metadata.xml latest = 26.7.0); the live README is otherwise accurate on versions.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
