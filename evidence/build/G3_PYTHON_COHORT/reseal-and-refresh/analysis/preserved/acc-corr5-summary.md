authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-summary: final independent check of the live-first correction run 20261012-0f6828d3

Reviewer: independent (Sonnet 5.5), read-only; I did not author the run. Reviewed copy: `scratchpad/acc5/0f6828d3` (byte copy of `scratchpad/lfix/runs/20261012-0f6828d3`; `sha256sum -c SHA256SUMS` 393 of 393 OK, and the list covers every file). Code: `git archive wt/lfix-fix01` (tip 0f6828d3, confirmed) into `scratchpad/acc5/code`. My scripts: `scratchpad/acc5/scripts/` (`check_pr.py`, `regen.py`). Records for every non-PUSHABLE repo: `acc-corr5-<name>.md` (10 files, this directory).

## 1. Result

| Verdict | Repos | Patch bytes | Meaning |
|---|---|---|---|
| PUSHABLE | 34 | 66839 | patch verified (byte-identical to the run reviewed last time); PR text true, readable, no overclaim |
| FIX_REQUIRED (text only) | 3 | 7190 | patch final; one sentence in the generated text contradicts the text two lines below it (Cells-Go, PDF-Java, Email-Cpp) |
| HOLD (owner-recorded, re-confirmed) | 2 | 4021 | 3D-.NET and TeX-Python: hold reasons still true at the same head |
| DO_NOT_PUSH (nothing to push) | 5 | 0 | Cells-Python, Cells-Rust, Font-Python, PDF-.NET, GIS-.NET |

39 patches, 78050 bytes in all (equals the owner table). All 8 PR texts the last review rejected are fixed. One new, smaller defect class appeared in the reworded checks line (section 3).

## 2. Step 1: the patches are unchanged

- Run `20261011-4b724575` against this run: all 345 files under `out/` (README.md, README.original.md, README.patch, corrections.json, validation_delta.json, facts.json, manifest.json, tree.txt) are byte-identical, 44 of 44 directories. `defect_recheck.json`, `idempotence.json`, `render_verdicts.json` are identical. The only differences in the run: `pr_text/` (39 of 39 files changed, the intended edit), `correction-owner-table.md` (line 5, the code reference only), the timing and log lines in `results_*.json`, and the new `pr_text_scan.txt`.
- `git diff 807ad30f..0f6828d3` touches four files: `pull_request.py` and its three test files. No bundle code moved, so identical bundles are expected, and the byte comparison confirms it.
- My own checks on this copy: `git apply` of `README.patch` to `README.original.md` (autocrlf off) gives `README.md` byte for byte, 39 of 39; sha256 of both files equals `corrections.json`, 43 of 43; no CR in any patch; patch bytes sum 78050.
- Semantic check of every redrawn diagram against its original (own parser): same id to label map (`<br/>` read as a space), same group titles, same visible edges, same group membership, 39 of 39, 0 differences.
- Live drift today (`gh api`, read-only): all 44 heads equal the bundle revisions; `README.original.md` equals the live blob at that revision in 43 of 43; GIS-.NET has no README (404).
- Not re-run this round: the headless-browser render and the idempotence run. The render, idempotence and defect-recheck records are byte-identical to the run the last review re-ran itself (39 of 39 clean on 4 Mermaid releases, Edge and Chrome).

## 3. Step 2: the 39 PR texts

I read all 39. With numbers, chain and hashes masked, the 39 texts fall into 7 variants: one template shared by 33 files (I read 3D-Java in full, and BarCode and HTML, whose chains differ, separately) and six single files (Cells-.NET, Cells-Cpp, Cells-Go, Email-Cpp, PDF-Java, Words-.NET), each of which I read in full. Five of the six singles are content PRs; the sixth, Email-Cpp, differs by its Length bullet.

Checked by script against `corrections.json`, `validation_delta.json` and the original READMEs, 39 of 39, 0 mismatches: diagram line number, label count, group-title count, the chain (compared with the actual `-->` edges of each diagram), render line (releases, fonts, clipped, splits, problems), model calls, idempotent, deterministic, `candidate_hash` (= `corrected_sha256`), `source_revision`, the "no failure" and "N fewer" sentences against the delta (see below), the revealed-text clause, and every length figure. How to review and How to decline are in 39 of 39. I also regenerated all 39 texts with the tip code (`compose_correction_pull_request`): byte-identical to `pr_text/`, so the files are what the code produces. The real send fills `policy_version` from `CURRENT_POLICY_VERSION` (cli.py:3100); the placeholder is only in the rehearsal files.

### The eight rejected texts, one by one

| Repo | Last time | Now |
|---|---|---|
| BarCode-Python | chain "Starting Points -> product -> ..." false | "the product -> Core Capabilities -> Outputs", 2 group titles; matches the diagram's edges. Fixed |
| HTML-Python | same | "Inputs and formats -> the product -> Core Capabilities -> Outputs"; matches. Fixed |
| Email-Cpp | "owner ruling(s) OD-06, R7" | plain: "the redraw adds a few lines (its init line and the links that keep columns in order), so the README now has 303 lines outside collapsed blocks, over the 300-line limit the checks apply (yours was within it)". 303 = delta; patch adds 4 lines. Explained; but see the new defect below |
| PDF-Java | same (304) | same wording, 304; patch adds 5 lines. Explained; same new defect |
| Words-.NET | garbled badge sentences | "The README has no version badge for the published package (Aspose.Words.FOSS on NuGet, current release 26.3.0); we added it at the front of the badge row." NuGet flat container lists 26.2.0 and 26.3.0 today; the README's badge row held one badge (License) on line 5. Fixed. The stale "landing soon" phrase (line 952, text matches) is now listed under "Noticed, not changed". Fixed |
| Cells-.NET | "the template's", fact ids | "states what the repository's own files declare"; evidence `dependency SkiaSharp 2.88.8 (in src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj)`, `target frameworks netstandard2.0;net8.0 (in the same file)`. Checked in the clone at 941814fd: one `PackageReference` SkiaSharp 2.88.8, `TargetFrameworks netstandard2.0;net8.0`. Fixed |
| Cells-Cpp | same | evidence `no third-party dependencies are declared`, `C++ standard 17`, `minimum CMake version 3.16`, all `(in Aspose.Cells.Foss.Cpp/CMakeLists.txt)`; clone at 9f852d0f: `cmake_minimum_required(VERSION 3.16)`, `CMAKE_CXX_STANDARD 17`. Fixed |
| Cells-Go | jargon, inferred closing point stated as fact, "fail no check more often" false | reasons in plain words; "deleting the `#` instead may read better"; "that is our reading of where it should end, so tell us if it should end elsewhere"; lines 105, 501, 529 checked in the original (a `#` sentence; `<details>`; `## Detailed Documentation`). Mostly fixed; see the new defect below |

Advisories U-1 to U-3 of the last review: no internal identifier remains. My grep of all 39 for `BC-\d+`, `OD-\d+`, `R\d`, `validate_candidate`, allowance(s), `DIAGRAM_FIX` and other kinds, `package:`/`dependency:` fact ids, `corrections.json`, `validation_delta`, run ids, "owner", "ruling", "template", "detector", local paths and tokens finds nothing outside backticked quotations of the maintainer's own text (hits are only the word "structure" and the URL `.../index.json`). The generator now refuses to emit a text that matches its own `internal_identifiers` list. "so text no longer clips" is gone: the lead says a wider font *can* clip, and the bullet says the labels fit "in the Mermaid versions tested (11.4 to 12.1)". "Proposed by repository-presenter, a tool that compares each Aspose FOSS README with its repository." now says what the tool is. Tone: respectful, "we" not "you must", every change has a line, a reason and where the evidence is, How to decline says closing is enough and nothing will be recreated. The texts are plain ASCII, no emoji.

### New defect (FIX_REQUIRED for three repos, one generator edit)

The reworded first checks bullet says "The corrected README has no failure that yours does not already have, and has N fewer failure(s) than yours." In 36 of 39 texts this is exact: introduced = 0 and N equals the whole drop (live total minus corrected total, from `validation_delta.json`). In three it is not:

| Repo | Sentence says | `validation_delta.json` | Next bullet says |
|---|---|---|---|
| Email-Cpp | no new failure; 1 fewer | `allowed` BC-07/visible +1; live 188, corrected 188 | "now has 303 lines ... over the 300-line limit ... (yours was within it)" |
| PDF-Java | no new failure; 3 fewer | `allowed` BC-07/visible +1; live 238, corrected 236 | "now has 304 lines ... over the 300-line limit ... (yours was within it)" |
| Cells-Go | no new failure; 1 fewer | `revealed` BC-04 +1; live 129, corrected 129 | "they now report 1 issue(s) there (for example the code span `v26`)" |

For Email-Cpp and PDF-Java the first sentence is false as written: the redraw does produce a failure yours lacks, and the Length bullet says so. A maintainer reads "no failure that yours does not already have" and, two lines later, "over the limit (yours was within it)". "N fewer" overstates the net by the extra failure (net 0, 2 and 0). For Cells-Go the substance is defensible (the issue sits in the maintainer's own text, newly readable), but the same sentence is not exact and the revealed-text bullet is cryptic ("1 issue(s) there" does not say what the issue is). It is the same defect class as the last review's Cells-Go finding, which I held to FIX_REQUIRED, so I hold these three to the same line.

Fix, `components/readme_correction/pull_request.py` `_delta_lines` only (text is composed at send time; no bundle changes): when `allowed` or `revealed` is non-empty, write "Apart from the point described next, the corrected README has no failure that yours does not already have" and either drop the "N fewer" clause or write it as "N fewer in one check and 1 more in another (next bullet)"; for the revealed bullet say what the check found ("it flags the code span `v26` as not tied to a fact in the repository"). Add a test that the first sentence matches the delta's net count when `allowed` or `revealed` is set.

### Advisories (all 39 or most; none blocks)

- A-1, all 39 diagram bullets: "Layout hints only: `flowchart LR`, `<br/>` line breaks, invisible `~~~` links ..., and one `%%{init}%%` line" is true in meaning (0 semantic differences, section 2) but not the full list of what the diff shows: `direction LR` becomes `direction TB` inside groups (23 diagrams) and the two capability column blocks are listed in swapped order (22 diagrams). A maintainer comparing the hunk finds two more kinds of line change than listed. Suggested: "...and the order and direction of the column blocks".
- A-2, Cells-.NET: the new Dependencies section lists SkiaSharp 2.88.8 under "Required Package Dependencies"; the README intro still says "pure managed code ... Windows, Linux, and macOS". True as written and carried over from the last review; one sentence in the PR would pre-empt the question (SkiaSharp ships native assets).
- A-3, all 39: the provenance block names `candidate_hash`, `policy_version`, `kind: correction`. It is below a divider and is what the shared effect reads back; by design, but not maintainer language.
- A-4, five content PRs: the diagram redraw rides in the same PR as the fix, so declining one declines both (last review U-4; not split).
- A-5, all 39: no human contact and no reason why this repository was chosen.
- A-6, cosmetic: "failure(s)", "issue(s)"; "(install commands, version claims, links, structure, length)" is not the whole list the checks cover; "each hunk is one change listed above" is not exact for Words-.NET (badge and diagram share one hunk) and for PDF-Python and Words-Python (one change in two hunks).
- A-7, owner table (not published): line 5 still describes the code as differing "only in how that text is ordered and titled"; the commit is the plain-words/identifier change.
- Carried over, unchanged: on Mermaid 12.1.0 the second half of the capabilities is drawn on the left in 20 of 22 two-column diagrams (forward on every 11.x); whether github.com runs 12.x is unverified.

## 4. Order and holds

- `pr_order`: 1 for the five content repos (Cells-.NET, Cells-Cpp, Cells-Go, PDF-Java, Words-.NET), 2 for the diagram-only repos, none for the five no-push entries. With the three FIX_REQUIRED waiting, send the three clean content PRs (Cells-.NET, Cells-Cpp, Words-.NET) first, then a pilot of diagram PRs.
- Pilot suggestion unchanged (the last review's drawn-text scale estimates at a 896 px column): PDF-Go (x1.96), Slides-Python (x1.75), Email-Python (x1.68), Words-Python (x1.63), PDF-Python (x1.57) are PUSHABLE and show the largest clean gain; BarCode-Python (x1.77) is now PUSHABLE too.
- 3D-.NET hold re-confirmed: head still 52b0f00e; `IOService.cs` lines 67 and 88 throw `NotSupportedException` otherwise; the README diagram (lines 34, 36, 56, 58, 59) labels U3D, RVM, AMF and HTML5. Pair the diagram PR with a README or issue correction.
- TeX-Python hold re-confirmed: head still 181015d2; `ast.parse` fails on 102 of 119 `.py` files. (The recorded `hold_reason` text says "35 of 45 source files" next to "102 of 119 .py files"; the PR text carries neither.)
- No-push reasons: Cells-Python and Font-Python and PDF-.NET `NO_DETECTOR_FIRED`; Cells-Rust `ONLY_CHANGE_UNPORTABLE_DIAGRAM`; GIS-.NET no README (404 today).

## 5. Final owner-ready list

### A. PUSHABLE now: 34 repos, 66839 patch bytes

Order: send the three content PRs first (order 1), then the diagram PRs (a pilot of five first, section 4). Diagram-only title for all 31: `docs(readme): lay out the At a Glance diagram left to right`.

| Order | Repo | PR title | Patch bytes (+/-) |
|---|---|---|---|
| 1 | aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2588 (+31/-15) |
| 1 | aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2799 (+32/-17) |
| 1 | aspose-words-foss/Aspose.Words-FOSS-for-.NET | docs(readme): add the published-version badge and lay out the At a Glance diagram left to right | 2466 (+22/-17) |
| 2 | aspose-3d-foss/Aspose.3D-FOSS-for-Java | (diagram-only title) | 1698 (+17/-14) |
| 2 | aspose-3d-foss/Aspose.3D-FOSS-for-Python | (diagram-only title) | 1990 (+20/-17) |
| 2 | aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | (diagram-only title) | 2036 (+22/-17) |
| 2 | aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | (diagram-only title) | 1253 (+10/-7) |
| 2 | aspose-cells-foss/Aspose.Cells-FOSS-for-Java | (diagram-only title) | 2706 (+27/-22) |
| 2 | aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | (diagram-only title) | 2082 (+22/-17) |
| 2 | aspose-email-foss/Aspose.Email-FOSS-for-.Net | (diagram-only title) | 1586 (+14/-10) |
| 2 | aspose-email-foss/Aspose.Email-FOSS-for-Python | (diagram-only title) | 2041 (+16/-12) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-.NET | (diagram-only title) | 1756 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Cpp | (diagram-only title) | 1822 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Go | (diagram-only title) | 1762 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Java | (diagram-only title) | 1756 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js | (diagram-only title) | 1762 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Python | (diagram-only title) | 1760 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-Rust | (diagram-only title) | 1756 (+14/-10) |
| 2 | aspose-email-foss/Aspose.JMAP-FOSS-for-TypeScript | (diagram-only title) | 1772 (+14/-10) |
| 2 | aspose-html-foss/Aspose.HTML-FOSS-for-Python | (diagram-only title) | 2143 (+20/-16) |
| 2 | aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | (diagram-only title) | 1504 (+13/-11) |
| 2 | aspose-note-foss/Aspose.Note-FOSS-for-Python | (diagram-only title) | 1469 (+16/-13) |
| 2 | aspose-page-foss/Aspose.Page-FOSS-for-Python | (diagram-only title) | 2027 (+21/-16) |
| 2 | aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | (diagram-only title) | 3020 (+30/-25) |
| 2 | aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | (diagram-only title) | 2034 (+21/-17) |
| 2 | aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | (diagram-only title) | 2517 (+25/-20) |
| 2 | aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | (diagram-only title) | 2549 (+26/-21) |
| 2 | aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | (diagram-only title) | 920 (+6/-5) |
| 2 | aspose-psd-foss/Aspose.PSD-FOSS-for-Python | (diagram-only title) | 924 (+6/-5) |
| 2 | aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | (diagram-only title) | 1966 (+19/-16) |
| 2 | aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | (diagram-only title) | 2027 (+21/-17) |
| 2 | aspose-slides-foss/Aspose.Slides-FOSS-for-Java | (diagram-only title) | 2047 (+21/-17) |
| 2 | aspose-slides-foss/Aspose.Slides-FOSS-for-Python | (diagram-only title) | 2451 (+24/-20) |
| 2 | aspose-words-foss/Aspose.Words-FOSS-for-Python | (diagram-only title) | 1850 (+15/-11) |

### B. FIX_REQUIRED (text only), 3 repos, 7190 patch bytes: change one sentence in the generator, then send

| Repo | PR title as generated | Patch bytes (+/-) | Record |
|---|---|---|---|
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go (order 1) | docs(readme): demote a stray second H1, close an unclosed <details> block and lay out the At a Glance diagram left to right | 2786 (+24/-17) | `acc-corr5-cells-go.md` |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (order 1) | docs(readme): show the current release (26.9.0) in the install snippets and lay out the At a Glance diagram left to right | 2541 (+26/-21) | `acc-corr5-pdf-java.md` |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp (order 2) | docs(readme): lay out the At a Glance diagram left to right | 1863 (+17/-13) | `acc-corr5-email-cpp.md` |

### C. HOLD, 2 repos, 4021 patch bytes: Aspose.3D-FOSS-for-.NET (2401, +24/-19), Aspose.TeX-FOSS-for-Python (1620, +13/-10). Records `acc-corr5-3d-net.md`, `acc-corr5-tex-python.md`.

### D. DO_NOT_PUSH, 5: Aspose.Cells-FOSS-for-Python, Aspose.Cells-FOSS-for-Rust, Aspose.Font-FOSS-for-Python, Aspose.PDF-FOSS-for-.NET, Aspose.GIS.FOSS-for-.Net. Records `acc-corr5-cells-python.md`, `acc-corr5-cells-rust.md`, `acc-corr5-font-python.md`, `acc-corr5-pdf-net.md`, `acc-corr5-gis-net.md`.

## 6. What I could not verify

- Rendering on github.com itself (its Mermaid version and fonts); the render was not re-run this round (bundles and render records are byte-identical to the run the last review re-rendered).
- The truth of the maintainers' own diagram labels, apart from 3D-.NET (the hold) and the five content repos; the redraw republishes them verbatim.
- The no-detector READMEs (Cells-Python, Font-Python, PDF-.NET): I confirm there is no patch, not that those READMEs are accurate.
- Library builds and tests (no toolchain run); content edits rest on manifests, CMake files and registries.
