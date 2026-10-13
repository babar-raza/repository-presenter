authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-psd-net: aspose-psd-foss/Aspose.PSD-FOSS-for-.NET (run 20261012-90a5a934) FIX_REQUIRED (PR text only; patch verified)

Not in the owner's first wave. Patch 1245 bytes (+12/-5), head 85ed7eec (live today), `README.original.md` equals the live blob, patch applies byte for byte, replay and confinement exact, idempotent, deterministic. Two edits: diagram redraw (line 30) and a build block at the end of `## Development and Testing` (line 402).

## Patch: verified

- `dotnet build Aspose.PSD-FOSS-for-.NET.sln` on a `git archive` export of 85ed7eec, .NET SDK 10.0.401 (`resolve_tool("dotnet")`): exit 0, 0 warnings, 0 errors, all projects built. The README targets `net10.0`.
- The README did not show a solution build (only `dotnet pack ...csproj` in Installation, `dotnet test ...csproj` in the dev section); no duplicate. The block is at the end of the section, outside any `<details>` or fence.
- Diagram: 6 labels, 3 titles, same edges; replaces the maintainers' own `%%{init: {"flowchart": {"useMaxWidth": true}}}%%` line with the redraw's init line (one init line in the result). Rendered on 11.4.1 and 12.1.0: horizontal, 0 clipped, 0 splits.
- Delta: live 118, corrected 117, introduced none.

## Defect in the generated text (same class as Cells-Go)

Title: "add the build and test commands, with the steps they need first and lay out ..."; lead: "The README's development section does not show how to build and test the project. We add the commands below, run in this order ... with the install steps they need first."; why: "the project's own files (`Aspose.PSD-FOSS-for-.NET.sln`) name them". Reality: the README shows `dotnet test` already (the bundle's `report_only` holds `dotnet test Aspose.PSD-FOSS-for-.NET.sln` as `ALREADY_SHOWN`); one command is added; there are no install steps; a solution file does not "name" a command.

Fix: the same generator change as in `acc-corr6-cells-go.md` (name only the commands added; no "install steps" when none). Suggested title (92 characters): `docs(readme): add the dotnet build command and lay out the At a Glance diagram left to right`; lead: "The development section shows how to run the tests but not how to build. We add `dotnet build Aspose.PSD-FOSS-for-.NET.sln`, which exited 0 on a clean clone of revision `85ed7eec7c80`."
