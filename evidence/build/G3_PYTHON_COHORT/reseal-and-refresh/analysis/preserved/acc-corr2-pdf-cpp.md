authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-cpp: aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp (registry entry 32, live head 4b83c9fe)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MAJOR | Diagram redraw is good; the add_dev_commands block is a broken command pair stitched from two different workflow steps.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp`, HEAD `4b83c9fec1e37fd205156770161f6843bac00ceb` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `e89fc645a85ac8478d5ebb19745e750577c451e4bfe03bd2fc48fae64326de8d` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L36 | At a Glance redrawn LR | Labels (16), titles, edges (3), group order identical. PNG viewed: 2 start points stacked, two capability columns, three outputs; no clipped text. | PASS |
| MISSING_INFO add_dev_commands L913 | appends one sentence on CI/release workflows + `cmake --build build --config Debug --target aspose_pdf_foss --parallel 4` / `ctest --test-dir build-pkgtest --output-on-failure` after 'To build and run the tests from a clone, run:' | FAIL. The two lines come from different places: line 1 is the Windows Debug build step of `.github/workflows/release.yml` (L143); line 2 is the package-consumer smoke test of release.yml (L183-192), whose directory `build-pkgtest` exists only after `cmake -S .github/package-test -B build-pkgtest -DCMAKE_PREFIX_PATH=<install-prefix>` (also `.github/package-test/CMakeLists.txt` L6-8). On a clean clone there is no `build-pkgtest`, and line 1 has no configure step before it (the live Build From Source gives `cmake -S . -B build` first), so the pair does not build what it tests and `ctest --test-dir build-pkgtest` fails. (cmake is not installed on this machine: established from the workflows and CMake files, not from a run.) The live section already carries the correct `cmake --build build` / `cd build && ctest`. The sentence 'runs across os (ubuntu-latest, windows-latest)' is a leaked matrix key and omits the real compiler matrix (gcc-13, clang-16, MSVC) in `ci.yml`; 'Releases run through the release workflow' is accurate (tag push builds, packages, drafts a GitHub release). | FAIL (introduced) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.PDF-FOSS-for-Cpp.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).
- Links added by the edit (`.github/workflows/ci.yml`, `release.yml`) resolve in the clone.

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 246 vs corrected failures 245 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MAJOR | Development and Testing | add_dev_commands must not combine steps from different jobs/workflows: require a configure -> build -> test chain from one job whose directories exist, and skip when the section already has a build/test command; until then drop the edit (the diagram hunk alone is pushable) |
| F2 | redraw | MINOR | Development and Testing | CI sentence: do not leak matrix keys ('across os (...)'); name the toolchains |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Live uses 'commercial Aspose.PDF' and 'FOSS edition' wording (intro and Scope and Limitations); inherited, not introduced.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
