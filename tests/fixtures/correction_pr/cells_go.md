TITLE: docs(readme): fix two markup problems, add the go build command and lay out the At a Glance diagram left to right

Two markup problems in README.md (a second top-level heading and a `<details>` block that is never closed), a build command the development section lacks, and the At a Glance diagram layout. Each is listed below with its line.

The development section shows `go test ./...` but not how to build. We add `go build ./...` after it. It exited 0 on a clean clone of revision `aaaaaaaaaaaa` (Windows 11 AMD64); it needs no steps first.

The At a Glance diagram (README.md line 6) is drawn top-down (`flowchart TD`), so on GitHub the blocks stack vertically and its labels sit in fixed-size boxes that a wider font can clip. This redraws the same diagram left to right with boxes sized by their text. Mermaid body only; no prose is touched.

### What changes
- README.md line 40: `#` -> `##`
  - why: line 40 is a second top-level heading, and a README has one: its title, on line 1. We made it a second-level heading (`##`); if the line was meant as a note, deleting the `#` instead may read better
  - evidence: README.md line 40
- added to the README at line 49: `To build from a clone, run:` (+3 more line(s))
  - why: the README shows how to test but not how to build; `go.mod` marks a Go module, so `go build ./...` applies, and it exited 0 on a clean clone of this revision (Windows 11 AMD64)
  - evidence: build command `go build ./...` (the standard command for a Go module, `go.mod`), which ran to success with every step exiting 0 on a clean clone (Windows 11 AMD64)
- inserted `</details>` before line 57
  - why: the `<details>` block opened on line 50 is never closed, so everything after it renders collapsed. We close it before the next section heading (line 57); that is our reading of where it should end, so tell us if it should end elsewhere
  - evidence: README.md line 50; README.md line 57
- **At a Glance diagram** (README.md line 6): drawn left to right so the labels fit their boxes. All 9 labels, the 3 group titles and the chain Starting Points -> the product -> Core Capabilities -> Outputs are unchanged (compared by script). Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).
  - evidence: README.md line 6 (the diagram as it is today)

