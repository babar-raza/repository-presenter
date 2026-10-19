Title: docs(readme): close an unclosed <details> block, demote a stray second H1 and lay out the At a Glance diagram left to right

Rendering problems in README.md. The only existing line that changes is line 105, and only its heading level; no word changes. Each is explained in the list below, with the line it sits on.

The At a Glance diagram (README.md line 46) is drawn top-down (`flowchart TD`), so on GitHub the blocks stack vertically and its labels sit in fixed-size boxes that a wider font can clip. This redraws the same diagram left to right with boxes sized by their text. Mermaid body only; no prose is touched.

### What changes
- README.md line 105: `#` -> `##`
  - why: line 105 is a second top-level heading, and a README has one: its title, on line 1. We made it a second-level heading (`##`); if the line was meant as a note, deleting the `#` instead may read better
  - evidence: README.md line 105
- inserted `</details>` before line 529
  - why: the `<details>` block opened on line 501 is never closed, so everything after it renders collapsed. We close it before the next section heading (line 529); that is our reading of where it should end, so tell us if it should end elsewhere
  - evidence: README.md line 501; README.md line 529
- **At a Glance diagram** (README.md line 46): drawn left to right so the labels fit their boxes in the Mermaid versions tested (11.4 to 12.1). All 12 labels, the 3 group titles and the chain Starting Points -> the product -> Core Capabilities -> Outputs are unchanged (compared by script). Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).
  - evidence: README.md line 46 (the diagram as it is today)

### How this was checked
- Only `README.md` changes, and only at the places listed: with the edits removed, the corrected README and yours are identical.
- We ran repository-presenter's README checks (install commands, examples, links, version and edition claims) on your README and on the corrected one. They report 13 failure(s) on yours and 13 on the corrected one: it removes none and adds none.
- Separately, our other checks (section layout, line length and wording rules for the READMEs this tool writes, which yours is not held to) find 1 new item(s) after the change; each is explained below.
- Changing the heading level changes how our checks split the README into sections, so they now judge a code span (`v26`, line 109) that they skipped before. That text is yours and is unchanged.
- Running the correction again on the corrected README makes no further edit (idempotent: yes); the same inputs give the same bytes (deterministic: yes). No model wrote any of this text (model calls: 0).
- The redrawn diagram was drawn in a headless browser on Mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0, natively and in 5 wider fonts: horizontal on every release, 0 clipped labels, 0 words split across lines, 0 other problems.

### How to review
Open **Files changed**: each hunk is one change listed above, and nothing else in README.md differs.

### How to decline
Close this pull request without merging. It will not be reopened or recreated for this proposal; a new pull request appears only after someone explicitly authorizes a new proposal for this repository.

---
Proposed by repository-presenter, a tool that compares each Aspose FOSS README with its repository. Provenance:
- candidate_hash: 6fd1d9e7fe5f89e0548581ef11acc48007b5b2d2d2052ff5a641816c14319ad3
- source_revision: 99c789e9175f2b12ad82bafeeba148ddcc1367fb
- policy_version: 1
- kind: correction
