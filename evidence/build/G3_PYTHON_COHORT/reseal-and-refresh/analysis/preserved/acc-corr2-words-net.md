authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-words-net: aspose-words-foss/Aspose.Words-FOSS-for-.NET (registry entry 42, live head 0d3f1add)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-words-foss__Aspose.Words-FOSS-for-.NET/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MINOR | NuGet badge and diagram redraw are good; the added `dotnet test Aspose.Words.sln` duplicates the command two lines above it.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-words-foss/Aspose.Words-FOSS-for-.NET`, HEAD `0d3f1add920f5294d726b4f286c2d6ba7c3ae22c` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `3440dcd2fc86f997f3c28b0fff5ac08cc8a8b2ca8a57d640243d098a2bb21be5` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| MISSING_INFO add_version_badge L5 | adds `[![NuGet](https://img.shields.io/nuget/v/Aspose.Words.FOSS.svg)](https://www.nuget.org/packages/Aspose.Words.FOSS/)` to the badge row | api.nuget.org flat-container: `aspose.words.foss` versions 26.2.0, 26.3.0; package page and shields badge both HTTP 200; the README's own `dotnet add package Aspose.Words.FOSS` (L92) matches. Placed on the existing single badge row, one space before the License badge; no second badge row. | PASS |
| DIAGRAM_FIX L10 | At a Glance redrawn LR | Labels (14), titles, edges, order identical. PNG viewed: 3 + 3 capability columns, three start points, four outputs; clean. The diagram sits near the top (before Navigation) in the live skeleton, which the lane kept. | PASS |
| MISSING_INFO add_dev_commands L927 | appends 'To run the tests from a clone, run:' + `dotnet test Aspose.Words.sln` | The live section already has `dotnet build Aspose.Words.sln -c Release` and `dotnet test Aspose.Words.Tests/Aspose.Words.Tests.csproj` immediately above (L921-924). The added command is also wider than the documented one: the sln contains `Aspose.Foundation.Tests`, `Aspose.Words.Tests` and `Aspose.JavaMs.Tests`, so it runs more suites than the README names. Not run (large suite); outcome could not be verified. | MISLEADING-by-duplication (redundant, not false) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.Words-FOSS-for-.NET.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 3 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 178 vs corrected failures 181 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MINOR | Development and Testing | drop the add_dev_commands edit (duplicate of the two commands directly above it); keep the badge and diagram hunks |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- L952 still says 'The NuGet package and new formats are landing soon', which now sits beside the new NuGet badge and contradicts the README's own 'Install from NuGet' (L89); the lane reports `stale_phrase` but does not edit. Minor omission, not introduced. `../../issues` links are flagged by mech.py as missing in the clone; GitHub resolves them to the issues page (false positive).

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
