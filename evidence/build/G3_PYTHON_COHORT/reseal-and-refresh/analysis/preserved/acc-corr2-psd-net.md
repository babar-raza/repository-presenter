authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-psd-net: aspose-psd-foss/Aspose.PSD-FOSS-for-.NET (registry entry 35, live head 85ed7eec)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-psd-foss__Aspose.PSD-FOSS-for-.NET/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MINOR | Diagram redraw is good; the added build/test block is true but duplicates the section's own test command.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`, HEAD `85ed7eec7c801d8b5c97aa099f018d3b98df2981` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `2549072307f1aff03b4e06c184d1840080342870cde2147dc5baafabb6adb94d` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L30 | At a Glance redrawn LR | Labels (6), titles, edges, order identical. PNG viewed: single capability column of three boxes; clean. | PASS |
| MISSING_INFO add_dev_commands L402 | appends 'To build and run the tests from a clone, run:' + `dotnet build Aspose.PSD-FOSS-for-.NET.sln` / `dotnet test Aspose.PSD-FOSS-for-.NET.sln` | Run in a scratch clone (SDK 10.0.401): build Succeeded 0 warnings / 0 errors; `dotnet test sln --no-build`: Passed 77, Failed 0 (`psd_net_build.log`, `psd_net_test.log`); the sln lists the library, the test project and eight sample projects. The commands are therefore TRUE. But the live section already says 'Run the test suite from the repository root:' with `dotnet test src/Aspose.PSD.FOSS.Test/Aspose.PSD.FOSS.Test.csproj` (L389-393), so the section now carries two lead-ins and two test commands for the same suite. | MISLEADING-by-duplication (redundant, not false) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.PSD-FOSS-for-.NET.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 118 vs corrected failures 119 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MINOR | Development and Testing | drop the add_dev_commands edit (duplicate of the section's own 'Run the test suite' block); keep the diagram hunk |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Repository has no CI workflow, so no CI statement could be added; the README never says the package is on NuGet (aspose.psd.foss is 404 on api.nuget.org), consistent.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
