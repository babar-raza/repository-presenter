authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-net: aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET (registry entry 31, live head 10a36383)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET/` (code branch wt/lfix-fix01).

**Verdict: DO_NOT_PUSH** | minor_major: MINOR | Sole edit is a redundant second build/test block; nothing of value remains after dropping it.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`, HEAD `10a363830fea952c29df20fdb37d35ad3a881433` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `9f6221be6aa4777cf31718ee68bb1ce8bcf94b1d8dab1880132574cf422e181e` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| MISSING_INFO add_dev_commands L1884 | appends `To build and run the tests from a clone, run:` + `dotnet build Aspose.Pdf.Foss.sln` / `dotnet test Aspose.Pdf.Foss.sln` at the end of Development and Testing | Commands are real and work: `dotnet build Aspose.Pdf.Foss.sln` in a scratch clone with SDK 10.0.401 -> Build succeeded, 0 warnings, 0 errors, 34 s (log `pdf_net_build.log`); the sln contains exactly `src/Aspose.Pdf.Foss.csproj` and `tests/Aspose.Pdf.Foss.Tests.csproj`. `dotnet test sln` was not run. But the section already opens with a fenced `dotnet test tests/Aspose.Pdf.Foss.Tests.csproj` block (live L1873-1875) and Installation already has `dotnet build src/Aspose.Pdf.Foss.csproj -c Release` (L150). The addition repeats the same instruction a second time with a near-identical lead-in, after the sentence that describes CI; CI itself runs `dotnet restore` / `dotnet build sln -c Release` / `dotnet test tests/...csproj` (`.github/workflows/build.yml`), not `dotnet test <sln>`. | MISLEADING-by-duplication (redundant, not false) |

## 3. At a Glance render
No Mermaid fence in the live README (At a Glance is an image); nothing to render.
- Live At a Glance is an image (`docs/media/at-a-glance.png`), not Mermaid; the lane correctly made no diagram edit. The horizontal-diagram standard cannot be applied without replacing the maintainer's image (outside a correction).

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 328 vs corrected failures 328 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MINOR | Development and Testing | drop the add_dev_commands edit (duplicate of the section's own `dotnet test` block); the bundle is then empty, so no PR |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- Navigation omits `## Dependencies` (live has the section at L156); inherited.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high
