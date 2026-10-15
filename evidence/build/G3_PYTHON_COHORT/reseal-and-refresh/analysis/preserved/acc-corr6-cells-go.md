authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-cells-go: aspose-cells-foss/Aspose.Cells-FOSS-for-Go (run 20261012-90a5a934) FIX_REQUIRED (PR text only; patch verified)

Owner-approved for the first wave. Patch 2956 bytes (+30/-17), head 99c789e9 (live today), `README.original.md` equals the live blob, patch applies and gives `README.md` byte for byte, edit replay and confinement exact, idempotent (second run: 0 edits), deterministic. Four edits: diagram redraw (line 46), `#` -> `##` (line 105), `go build ./...` block (line 500), `</details>` (line 529). The patch is what the predecessor reviewed plus the new build block; it is right. The generated PR text is not.

## What I verified on the patch

- `go build ./...` and `go test ./...` on a fresh clone at 99c789e9 (`git init` + shallow fetch of the sha), Go 1.26.4 from `D:\Program Files\Go` via `core/toolchains.py` (`resolve_tool("go")`): both exit 0; and in a Linux container (`golang:1`, Go 1.27.2, no network, `git archive` export): BUILD_OK, `tests` package ok. `go.mod` is `go 1.24.5`; there is no CI workflow in the repository, so `go.mod` plus the receipt is the only evidence.
- The README did not show `go build`; it shows `go test ./...` (line 499 original), which the correction rightly did not add again. Whole-file grep: `go build ./...` appears once (the added block). The block sits in `## Development and Testing`, before the `<details>`, at depth 0, outside a fence.
- `</details>`: original has 3 `<details>` and 2 `</details>`; corrected 3 and 3. The unclosed block opens at 501 ("More Test and Example Commands"); the closing lands after its last paragraph and before `## Detailed Documentation` (529). Reasonable and the PR says it is an inference.
- `#` -> `##` on line 105 (`# Requires **Go 1.24.5+** (see go.mod). ...`): README H1 count 2 -> 1. No anchor breaks (28 internal links before, 28 after, all resolve both times).
- Diagram: 12 labels, 3 titles, same edges and group membership (own parser, 0 differences). Rendered on Mermaid 11.4.1 and 12.1.0 (also 11.12.0 and 11.17.2 by the harness): horizontal, 0 clipped in 5 wider fonts, 0 word splits. PNGs inspected on 11.4.1 and 12.1.0. On 12.1.0 the second capability column (CSV, Streaming, Password) is drawn left of the first (known, carried over).
- Delta: live 129, corrected 129; resolved BC-07 -1; revealed BC-04 +1 (`code span 'v26' is not a fact value`); introduced none.

## Defects in the generated PR text (title and body as in `pr_text/aspose-cells-foss__Aspose.Cells-FOSS-for-Go.md`)

1. Lead: "Rendering problems in README.md; no wording changes." False for this PR: it adds a sentence ("To build from a clone, run:") and a code block. The sentence is the fixed text for the `structure` category and is printed whenever one is present, regardless of other categories (`pull_request.py` `_lead`, branch `name == "structure"`).
2. Lead and why: "The README's development section does not show how to build and test the project. We add the commands below, run in this order ... with the install steps they need first." The README already shows `go test ./...`; one command is added (`go build ./...`), there are no install steps, and in the README the order is now test, then build. The corrected text says "commands", "in this order" and "install steps". The `report_only` record of this very bundle holds `go test ./...` as `ALREADY_SHOWN`.
3. Why, first edit: "the project's own files (`go.mod`) name them". `go.mod` names no command; it marks the module. The truthful evidence is the receipt.
4. Title: "docs(readme): 4 verified corrections" (the generator falls back to a count when the sentence would pass 140 characters). True but tells the maintainer nothing.
5. Checks bullet: "Closing the broken markup makes text visible that the checks could not read before; they now report 1 issue(s) there (for example the code span `v26`)". The `v26` span is on line 109 (original), directly under the promoted heading, not under the unclosed block; the code comment in `check.py` says the cause is the heading promotion re-segmenting the README. Say "Changing the heading level".
6. Navigation (patch-level nit, cosmetic): the contents list is a nested list built from heading levels; the entry for the demoted heading (`- [Requires **Go 1.24.5+** ...](#requires-...)`, line 20) stays at the top level (indent 0) while the sections around it are at indent 2. The anchor still resolves. One more edit (indent by 2) would make it consistent; or say it in the PR.

## Fix and suggested text

Generator only (`components/readme_correction/pull_request.py`), no bundle change: the `structure` lead must say "no wording changes" only when no other non-diagram category is present; the `dev` lead and why must name the commands actually added (not those with `ALREADY_SHOWN`) and drop "with the install steps they need first" when there are none; `_commands_source` must not say "name them" for a standard toolchain command without a CI step or script (say "the receipt"); add a test with the Cells-Go bundle for each.

Or hand-edit at send time. Suggested text:

- Title (113 characters): `docs(readme): fix two markup problems, add the go build command and lay out the At a Glance diagram left to right`
- Lead: "Two markup problems in README.md (a second top-level heading and a `<details>` block that is never closed), a build command the development section lacks, and the At a Glance diagram layout. Each is listed below with its line."
- Build paragraph: "The development section shows `go test ./...` but not how to build. We add `go build ./...` after it. It exited 0 on a clean clone of revision `99c789e9175f` (Windows 11 and a Linux container); it needs no steps first."
- Why (build edit): "the README shows how to test but not how to build; `go.mod` marks a Go module, so `go build ./...` applies, and it exited 0 on a clean clone of this revision"
- Checks, second bullet: "Changing the heading level changes how our checks split the README into sections, so they now judge a code span (`v26`, line 109) that they skipped before. That text is yours and is unchanged."

After that: PUSHABLE (nothing else found). The Navigation indent is optional.
