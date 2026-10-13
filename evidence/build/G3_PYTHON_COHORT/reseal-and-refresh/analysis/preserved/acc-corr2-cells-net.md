authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2: Aspose.Cells-FOSS-for-.NET

Verdict: **FIX_REQUIRED**  |  minor_major: **MINOR**  |  reviewer: independent (Sonnet 5.5), read-only, patch-adapted acceptance protocol v1.1

Repository: aspose-cells-foss/Aspose.Cells-FOSS-for-.NET  |  live head 941814fd

## Edits
1. `missing_sections` L14: Navigation gains `- [Dependencies](#dependencies)`.
2. `at_a_glance_diagram` L25: redraw.
3. `missing_sections` L80: new `## Dependencies` (Required Package Dependencies: `SkiaSharp 2.88.8`; Native and System Requirements: `Requires .NET netstandard2.0;net8.0.`).
4. `add_dev_commands` L532: appends "To build from a clone, run:" + `dotnet build Aspose.Cells_FOSS.sln` after the `</details>` at the end of Development and Testing.

## Findings
- Edit 1 PASS: the earlier review's universal defect (section insertion did not update Navigation) is fixed: Navigation 10 to 11 items, `#dependencies` resolves, every H2 is listed.
- Edit 2 PASS: 11 labels, titles, 3 edges identical; order c1..c6; vertical 1041x1101 to horizontal 1128x518; 0 clipped.
- Edit 3 PASS (true): `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj` L53 `PackageReference Include="SkiaSharp" Version="2.88.8"` (L52 comment: powers the XLSX-to-PDF renderer); the NuGet nuspec of published Aspose.Cells.FOSS 26.9.0 lists SkiaSharp 2.88.8 under both net8.0 and .NETStandard2.0 (`api.nuget.org/v3-flatcontainer/aspose.cells.foss/26.9.0/aspose.cells.foss.nuspec`); csproj L3 `TargetFrameworks` = `netstandard2.0;net8.0`. Section style matches sibling READMEs. Advisory: the raw `netstandard2.0;net8.0` property syntax in backticks reads oddly.
- Edit 4 REDUNDANT and MISPLACED (minor, introduced): the section already opens with "Build the library from the repository root: `dotnet build src\Aspose.Cells_FOSS\Aspose.Cells_FOSS.csproj -c Debug`" (L511); the added solution build repeats it after the details block. (`Aspose.Cells_FOSS.sln` does exist in the clone root; I did not run the build.)
- Advisory (inherited sentence, now contradicted next to the new section): intro L7 says "pure managed code ... runs on Windows, Linux, and macOS" while SkiaSharp 2.88.8 depends on `SkiaSharp.NativeAssets.Win32` and `.macOS` (nuget.org nuspec of SkiaSharp 2.88.8; Linux needs a separate asset package). Not introduced by the patch; a maintainer-voice sentence, so leave and report.
- Links 24 to 25 (the new nav item), 0 broken, no duplicate H2, no narration.

## Fix
Drop edit 4 (keep 1-3).

## Verdict
FIX_REQUIRED, MINOR.
## Diagram check (before and after, real render)
Renderer: the lane's own `measure.mjs` with the pinned mermaid packages (Edge 155), run by me on the snapshot's fence bodies; PNGs in `scratchpad/acccorr2/png_before` and `png_after` (I viewed them). Native render plus five stress fonts (Arial, Verdana, Tahoma, Segoe UI, Georgia), mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0.
- vertical 1041x1101 to horizontal 1128x518; 0 bad nodes.

## Method and confinement (all steps run by me, read-only)
- Bundle snapshot taken from `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-.NET` at about 19:10 PST on 2026-10-11 (the lane regenerated every bundle between 19:06 and 19:09 with code `wt/lfix-fix01` @ `e576d7ce`; I reviewed that regenerated bundle, copied to `scratchpad/acccorr2/snap2/aspose-cells-foss__Aspose.Cells-FOSS-for-.NET`). README.md sha256 `0dce09972294ee10127a9ef5383e9831f109b1edf0c61bafb39905b042791194`.
- Fresh `git clone --depth 1` of the live head: `941814fd` equals `manifest.revision` (no upstream drift; `git ls-remote` re-checked at the end).
- `README.original.md` is byte-equal to the live `README.md` blob at that head: yes.
- Replay confinement: applying ONLY the 4 enumerated edit(s) in `corrections.json` (character spans, each `original` span matched, no overlap) to the live README reproduces `README.md` byte for byte: yes. Removing every edit span from both sides leaves identical text (nothing else changed). `README.patch` applies cleanly to the live README with `git apply` and yields the corrected README byte for byte. All manifest file hashes verify. No CRLF in either file.
- validation_delta.json: introduced = 0; no allowances and nothing revealed.
