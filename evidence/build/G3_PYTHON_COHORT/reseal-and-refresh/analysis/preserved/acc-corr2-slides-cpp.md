authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-slides-cpp: aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp (registry entry 38, live head 469ce77a)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-slides-foss__Aspose.Slides-FOSS-for-Cpp/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MAJOR | Diagram redraw is good; both non-diagram edits are defective (false docs claim; build/test commands that fail on a clean clone).

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp`, HEAD `469ce77a07b988c49deb930632b8276c89ec6b66` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `684e64bb5fa063da3ffba364e98b8d968a50ae8f9873a1205b75649222dd3883` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L26 | At a Glance redrawn LR | Labels (12), titles, edges, order identical. PNG viewed: clean. | PASS |
| MISSING_INFO add_doc_links L752 | appends `- **[Documentation](docs/)** — documentation kept in this repository.` | FAIL. `docs/` contains only `docs/media/banner-readme.png`, `docs/nuget/icon.png`, `docs/nuget/README.md`; not documentation. The live 'Documentation & Resources' list already links the real docs (docs.aspose.org, kb, reference.aspose.org, PUBLISHING.md). The bullet is also separated from the list by a blank line. | FAIL (introduced) |
| MISSING_INFO add_dev_commands L879 | appends 'To build and run the tests from a clone, run:' + `cmake --build build-asan --parallel 4` / `ctest --test-dir build-asan --output-on-failure --no-tests=error --parallel 4` | FAIL. These are the AddressSanitizer job's build/test lines (`.github/workflows/ci.yml` L264, L271). `build-asan` exists only after `cmake -S . -B build-asan -DASPOSE_SLIDES_FOSS_SANITIZE_ADDRESS=ON ...` (ci.yml L258; `CMakeLists.txt` L63-64; `CONTRIBUTING.md` L139), which the block omits; on a clean clone `cmake --build build-asan` has nothing to build. (cmake absent on this machine: established from the workflow and CMake files, not a run.) The live section already gives the complete `cmake -B build ...; cmake --build build; ctest --test-dir build --output-on-failure` (live Development and Testing, fenced block). The new block also sits after the SECURITY / CODE_OF_CONDUCT sentences, directly above `## License`. | FAIL (introduced) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.Slides-FOSS-for-Cpp.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 281 vs corrected failures 286 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MAJOR | Documentation & Resources, Development and Testing | drop both non-diagram edits; fix add_doc_links (see Slides-.NET F1) and add_dev_commands (see PDF-Cpp F1: configure step missing, job-specific sanitizer variant offered as the general route) |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Relative link `index` (Additional Examples area) is not a file in the clone (inherited); `Install-Package Aspose.Slides.Cpp.FOSS` is correct (NuGet 26.9.0).

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
