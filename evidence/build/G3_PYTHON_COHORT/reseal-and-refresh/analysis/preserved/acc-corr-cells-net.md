authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-cells-net: Aspose.Cells-FOSS-for-.NET (live head 941814fd)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-.NET/`.
Clone: `scratchpad/acccorr/clones/Aspose.Cells-FOSS-for-.NET` (`git clone --depth 1`, HEAD = bundle `source_revision` 941814fd, no drift).

**Verdict: FIX_REQUIRED, minor_major MINOR** (one mechanical consistency defect introduced by the patch, two wording inaccuracies, one omission).

## 1. Edit confinement (independent replay)
- `README.original.md` is byte-identical to `git show HEAD:README.md` (sha256 2c6abdab...); corrected sha matches `corrections.json`.
- I replayed the single enumerated edit (`MISSING_SECTION`, insert at offset 5464) over the original: result == `README.md` exactly. difflib shows exactly one `insert` hunk, 9 lines, zero deletions, zero replacements. No maintainer text altered or lost. LF-only before and after (no mixed line endings).
- Patch placement: after the Installation paragraph, before Quick Start: matches template order.

## 2. Claim checks
| # | Claim (new text) | Check | Result |
|---|---|---|---|
| 1 | README had no Dependencies section | headings of live README (grep `^#`): none | PASS |
| 2 | `SkiaSharp 2.88.8` is the required package dependency | `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj` L53 `PackageReference SkiaSharp 2.88.8` (only reference); published nuspec `https://api.nuget.org/v3-flatcontainer/aspose.cells.foss/26.9.0/aspose.cells.foss.nuspec` lists SkiaSharp 2.88.8 in both `net8.0` and `.NETStandard2.0` groups | PASS (complete: nothing else is referenced; no test project exists) |
| 3 | "Requires .NET `netstandard2.0` (`TargetFramework` in ...csproj)" | csproj property is `TargetFrameworks` = `netstandard2.0;net8.0`; README L78 itself says it multi-targets both | MISLEADING-minor: wrong property name, drops net8.0, "netstandard2.0" is not a ".NET" version |
| 4 | New section listed in the README's Navigation | live README L9-20 lists every H2 except the new one | FAIL (introduced): Navigation omits `Dependencies`; sibling READMEs (Cells-Java L20, Cells-Rust L22, Slides-Java L23) all list it |
| 5 | Section is consistent with the rest of the README | intro L7 says "The library is pure managed code ... runs on Windows, Linux, and macOS"; SkiaSharp is a native-binary package | INHERITED misleading claim, now visible next to the new section; not fixed |
| 6 | Linux caveat | SkiaSharp 2.88.8 nuspec: `.NETStandard2.0`/`net6.0` groups pull only `SkiaSharp.NativeAssets.Win32` + `.macOS`; no Linux assets (`curl .../skiasharp/2.88.8/skiasharp.nuspec`) | COULD_NOT_VERIFY at runtime (Windows host); registry evidence says PDF export on Linux needs an extra package. Not mentioned in new text (sibling Words-.NET documents exactly this) |
| 7 | install command `dotnet add package Aspose.Cells.FOSS` / `Version="26.9.0.0"` (unchanged) | NuGet versions 26.5.0, 26.6.0, 26.7.0, 26.9.0 | PASS |

## 3. Render and style
- Headings: one H1, no duplicate headings, all fences closed (`mech.py` and own fence scan). Inserted block has no links. Fence languages unaffected.
- Tone: heading pair `Required Package Dependencies` / `Native and System Requirements` is the same template the sibling Aspose READMEs use; consistent. Bullet formatting `` `SkiaSharp 2.88.8` `` (name and version in one code span) differs from siblings (name in code, version outside) but is fine.
- Would a maintainer accept? Content true and welcome (the README never mentioned SkiaSharp). They would ask for the Navigation entry and probably the netstandard/net8.0 wording.

## 4. Fixes
| id | kind | severity | fix |
|---|---|---|---|
| F1 | code_change (small, generic) | MINOR | When the live README has a `## Navigation` list, insert `- [Dependencies](#dependencies)` at the matching position (between Installation and Quick Start). Universal: same defect in Cells-Cpp |
| F2 | code_change (extractor) | MINOR | `package:target_framework` fact is truncated to the first TFM (`netstandard2.0`; csproj has `netstandard2.0;net8.0`); emit the full list and cite `TargetFrameworks` |
| F3 | redraw | MINOR | Bullet text: "Targets `netstandard2.0` and `net8.0` (`TargetFrameworks` in ...)" |
| F4 | advisory | - | Mention SkiaSharp is a native package (Linux needs `SkiaSharp.NativeAssets.Linux` for PDF export) and reconcile "pure managed code" (inherited misleading claim) |

could_not_verify: Linux runtime behaviour of PDF export; the lane's 6 reported failing examples (CS0246 "Workbook not found" on Additional Examples snippets that omit `using Aspose.Cells_FOSS;`) were not re-run; out of scope for this patch review.
confidence: high on edit confinement and registry facts; medium on the Linux point.
