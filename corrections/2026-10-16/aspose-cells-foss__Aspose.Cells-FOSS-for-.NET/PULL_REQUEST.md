Title: docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right

The README has no `Dependencies` section. We added one that states what the repository's own files declare (cited below), with an item for it in the contents list.

The At a Glance diagram (README.md line 25) is drawn top-down (`flowchart TD`), so on GitHub the blocks stack vertically and its labels sit in fixed-size boxes that a wider font can clip. This redraws the same diagram left to right with boxes sized by their text. Mermaid body only; no prose is touched.

### What changes
- added to the contents list at line 14: `- [Dependencies](#dependencies)`
  - why: so the new section can be reached from the contents list
  - evidence: dependency `SkiaSharp 2.88.8` (in `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj`); target frameworks `netstandard2.0;net8.0` (in `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj`); README.md line 14
- inserted `## Dependencies` before line 80
  - why: the README has no Dependencies section; this one states what the repository's own files declare
  - evidence: dependency `SkiaSharp 2.88.8` (in `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj`); target frameworks `netstandard2.0;net8.0` (in `src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj`)
- **At a Glance diagram** (README.md line 25): drawn left to right so the labels fit their boxes. All 11 labels, the 3 group titles and the chain Starting Points -> the product -> Core Capabilities -> Outputs are unchanged (compared by script). Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).
  - evidence: README.md line 25 (the diagram as it is today)

### How this was checked
- Only `README.md` changes, and only at the places listed: with the edits removed, the corrected README and yours are identical.
- We ran repository-presenter's README checks (install commands, examples, links, version and edition claims) on your README and on the corrected one. They report 10 failure(s) on yours and 10 on the corrected one: it removes none and adds none.
- Running the correction again on the corrected README makes no further edit (idempotent: yes); the same inputs give the same bytes (deterministic: yes). No model wrote any of this text (model calls: 0).

### How to review
Open **Files changed**: each hunk is one change listed above, and nothing else in README.md differs.

### How to decline
Close this pull request without merging. It will not be reopened or recreated for this proposal; a new pull request appears only after someone explicitly authorizes a new proposal for this repository.

---
Proposed by repository-presenter, a tool that compares each Aspose FOSS README with its repository. Provenance:
- candidate_hash: fa4a4f68a6d620a0b323ca774a7d57fa6eb88cf210215d37f4f2d18f1658d4ad
- source_revision: 941814fd138dc28cf47123d48194f329f283498d
- policy_version: 1
- kind: correction
