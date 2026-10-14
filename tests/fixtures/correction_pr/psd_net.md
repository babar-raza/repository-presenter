TITLE: docs(readme): add the dotnet build command and lay out the At a Glance diagram left to right

The development section shows how to run the tests but not how to build. We add `dotnet build Aspose.PSD-FOSS-for-.NET.sln`. It exited 0 on a clean clone of revision `aaaaaaaaaaaa` (Windows 11 AMD64); it needs no steps first.

The At a Glance diagram (README.md line 6) is drawn top-down (`flowchart TD`), so on GitHub the blocks stack vertically and its labels sit in fixed-size boxes that a wider font can clip. This redraws the same diagram left to right with boxes sized by their text. Mermaid body only; no prose is touched.

### What changes
- added to the README at line 45: `To build from a clone, run:` (+3 more line(s))
  - why: the README shows how to test but not how to build; `Aspose.PSD-FOSS-for-.NET.sln` marks a .NET solution, so `dotnet build Aspose.PSD-FOSS-for-.NET.sln` applies, and it exited 0 on a clean clone of this revision (Windows 11 AMD64)
  - evidence: build command `dotnet build Aspose.PSD-FOSS-for-.NET.sln` (the standard command for a .NET solution, `Aspose.PSD-FOSS-for-.NET.sln`), which ran to success with every step exiting 0 on a clean clone (Windows 11 AMD64)
- **At a Glance diagram** (README.md line 6): drawn left to right so the labels fit their boxes. All 9 labels, the 3 group titles and the chain Starting Points -> the product -> Core Capabilities -> Outputs are unchanged (compared by script). Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).
  - evidence: README.md line 6 (the diagram as it is today)

