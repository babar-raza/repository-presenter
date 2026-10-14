authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-cells-go: Aspose.Cells-FOSS-for-Go (live head 99c789e9)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Go/`.
Clone: `scratchpad/acccorr/clones/Aspose.Cells-FOSS-for-Go`, HEAD 99c789e9 == bundle `source_revision`.

**Verdict: PUSHABLE (minor note only).** Two exact, tiny, mechanical markdown repairs; both defects are real and visible to every visitor.

## 1. Edit confinement
- `README.original.md` == live blob (e55fbe1e...); corrected sha matches `corrections.json`.
- Replay of the two `STRUCTURE_FIX` edits reproduces `README.md`. difflib: exactly two hunks: (a) L105 `#` -> `##` (one character; heading text and anchor unchanged), (b) insert `</details>\n\n` before `## Detailed Documentation` (L529). Nothing else changed; no maintainer text lost. LF-only; the em dash in L105 is preserved byte for byte.

## 2. Defect verification (before true, after fixed)
| # | Claim | Check | Result |
|---|---|---|---|
| 1 | README has a second H1 | `grep -n '^#'`: L1 `# Aspose.Cells FOSS for Go`, L105 `# Requires **Go 1.24.5+** (see go.mod). Depends only on...` (a sentence used as an H1 inside Installation) | PASS (real) |
| 2 | `<details>` opened at L501 is never closed | tag scan: `<details>` L223/L436/L501, `</details>` L380/L458 only | PASS (real) |
| 3 | Consequence: Detailed Documentation, Constraints and License render collapsed inside the "More Test and Example Commands" disclosure | rendered both versions with markdown-it (commonmark, html on) and parsed with html5lib: BEFORE `h2 (in <details>)`: Detailed Documentation, Constraints, License; AFTER all three at top level, `h1` count 1 | PASS: fixed |
| 4 | Navigation anchors still resolve | heading text unchanged so the anchor `#requires-go-1245-see-gomod-...` is unchanged; Nav entry L20 still points at it | PASS |
| 5 | Inherited claims untouched: `go get github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26/aspose/cells_foss`, Go 1.24.5 | `go.mod`: `module .../v26`, `go 1.24.5`; `proxy.golang.org/.../v26/@v/list` = v26.7.0, v26.7.1 | PASS |

## 3. Render and style
- One H1 after the fix; no duplicate headings; all four fences/details balanced (3 `<details>`, 3 `</details>` after the fix).
- The `</details>` placement (after "For a complete usage walkthrough ... docs/usage.md", before `## Detailed Documentation`) is the natural end of the disclosure; a maintainer could prefer one paragraph earlier but cannot object to it.
- Minor: the demoted line is still a full sentence rendered as a section heading (`## Requires **Go 1.24.5+** ... no third-party modules.`), immediately followed by a paragraph and a `## Dependencies` section that say the same. The better fix (paragraph, plus removing the Nav entry) is what the lane documented as a deliberate non-edit; the demotion is the safest minimal step and an improvement over a second H1. A maintainer would accept it.

## 4. Findings the PR does not address (not blockers for this PR)
- `claim_public_types` L467: README says 14 public types, facts hold 28 (the README matches release v26.7.1, not `main`); 9 README examples reported "build failed" (no Go toolchain here: not re-run, treat as unverified); both left to a separate content PR.

## 5. Fixes (optional)
| id | kind | severity | fix |
|---|---|---|---|
| F1 | redraw | MINOR (optional) | Convert L105 to a plain paragraph and drop its Navigation entry |

confidence: high.
