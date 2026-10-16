Title: docs(readme): lay out the At a Glance diagram left to right

The At a Glance diagram (README.md line 30) is drawn top-down (`flowchart TD`), so on GitHub the blocks stack vertically and its labels sit in fixed-size boxes that a wider font can clip. This redraws the same diagram left to right with boxes sized by their text. Mermaid body only; no prose is touched.

### What changes
- **At a Glance diagram** (README.md line 30): drawn left to right so the labels fit their boxes. All 13 labels, the 3 group titles and the chain Starting Points -> the product -> Core Capabilities -> Outputs are unchanged (compared by script). Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).
  - evidence: README.md line 30 (the diagram as it is today)

### How this was checked
- Only `README.md` changes, and only at the places listed: with the edits removed, the corrected README and yours are identical.
- We ran repository-presenter's README checks (install commands, examples, links, version and edition claims) on your README and on the corrected one. They report 6 failure(s) on yours and 6 on the corrected one: it removes none and adds none.
- Running the correction again on the corrected README makes no further edit (idempotent: yes); the same inputs give the same bytes (deterministic: yes). No model wrote any of this text (model calls: 0).

### How to review
Open **Files changed**: each hunk is one change listed above, and nothing else in README.md differs.

### How to decline
Close this pull request without merging. It will not be reopened or recreated for this proposal; a new pull request appears only after someone explicitly authorizes a new proposal for this repository.

---
Proposed by repository-presenter, a tool that compares each Aspose FOSS README with its repository. Provenance:
- candidate_hash: 9344a37e29fe692ae5420bfb5647cadec54b19bb9b6ed1596617e0ea88fbaa26
- source_revision: fc186507e5b7124f4664aa6035f25cfd3112367d
- policy_version: 1
- kind: correction
