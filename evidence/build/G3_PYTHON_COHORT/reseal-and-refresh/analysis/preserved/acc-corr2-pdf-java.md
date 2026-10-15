authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-java: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (registry entry 33, live head 736cedaa)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/` (code branch wt/lfix-fix01).

**Verdict: PUSHABLE** | minor_major: MINOR | Two-line version bump, verified; the At a Glance diagram is still the live vertical one (not redrawn).

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`, HEAD `736cedaa2922e4952f429364bdb9a4bbb1d97863` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `14ed921dd613 (prefix recorded at review time; directory empty when this record was written)` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| FALSE_CLAIM_FIX L121 | `<version>26.6.0</version>` -> `26.9.0` | Maven Central `maven-metadata.xml`: latest = release = 26.9.0, versions 26.6.0, 26.8.0, 26.9.0; `.../26.9.0/aspose-pdf-foss-26.9.0.pom` HTTP 200; clone `pom.xml` L6 `<version>26.9.0</version>`, HEAD 736cedaa 'chore: release 26.9.0'. 26.6.0 is still published (pom 200), so the old pin is stale, not non-existent. | PASS |
| FALSE_CLAIM_FIX L128 | `implementation 'org.aspose:aspose-pdf-foss:26.6.0'` -> `26.9.0` | Same evidence. A grep for version strings finds no other `26.x.y` in the live README. | PASS |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.PDF-FOSS-for-Java.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = vertical, clipped in 5 of 5 fonts (diagram unchanged by the bundle). For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).
- At a Glance: the live diagram is unchanged (vertical, clipped in 5 of 5 fonts, 4 of 5 under mermaid 12.1.0). The lane left it deliberately: the redraw would exceed BC-07's visible-line budget (live sits at 299 of 300). The owner's standard (horizontal, no clipping) is therefore not met for this repo.

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 7 vs corrected failures 6 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MINOR | At a Glance | owner ruling needed on the BC-07 visible-line budget so this diagram can be redrawn; not a blocker for pushing the version bump |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Maven Central badge target `search.maven.org/artifact/...` returns 403 to a scripted GET (bot block); inherited.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
