authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr4-summary: independent review of the live-first correction run 20261011-4b724575 (PR texts by 807ad30f)

Reviewer: independent (Sonnet 5.5), read-only; I did not author the run. Reviewed copy: `scratchpad/acccorr4/run` (byte copy of `scratchpad/lfix/runs/20261011-4b724575`; `sha256sum -c SHA256SUMS` 392 of 392 OK on the original and on the copy, and the list covers every file in the run). Code: `git archive 807ad30f` of `wt/lfix-fix01` into `scratchpad/acccorr4/code`. My scripts and raw renders: `scratchpad/acccorr4/{scripts,render,mmd,mmd_neg,png,clones}`. Records for every non-PUSHABLE repo: `acc-corr4-<name>.md` (15 files, this directory).

## 1. Result

| Verdict | Repos | Patch bytes | Meaning |
|---|---|---|---|
| PUSHABLE | 29 | 55590 | patch verified; PR text true, readable, no false or garbled sentence (generator wording advisories U-1 to U-4 below) |
| FIX_REQUIRED (text only) | 8 | 18439 | patch verified and final; the generated PR text holds a sentence I would not sign (false, garbled or unexplained). All five content PRs are here. One generator edit per sentence; bundles do not change |
| HOLD (owner-recorded, confirmed) | 2 | 4021 | 3D-.NET and TeX-Python: hold reasons are true; do not send without the paired fix |
| DO_NOT_PUSH (nothing to push) | 5 | 0 | Cells-Python, Font-Python, PDF-.NET (no detector fired), Cells-Rust (only change is the unportable diagram), GIS-.NET (no README) |

All 39 patches are correct. What stands between the owner and sending is PR text, not the diff.

## 2. What I re-ran myself (and what it showed)

1. Render (own runs of the project's `measure.mjs`, my own analysis, then the project's `check_entry` on top). Corrected diagrams, 39 of 39, on Mermaid 11.17.2, 11.4.1, 11.12.0 and 12.1.0, in Edge 155.0.4283.45 and in Chrome 154.0.8037.99 (8 runs): 0 words split across lines; 0 extra wraps (the drawn lines of every node equal its source `<br/>` lines exactly); 0 labels clipped natively and in Arial, Verdana, Tahoma, Segoe UI, Georgia; the three blocks left to right in 39 of 39 (BarCode has no Starting Points block: product, Capabilities, Outputs left to right); 0 HTML foreignObject boxes; 0 node overlaps; drawn text equals the label text. `check_entry` (807ad30f code): 0 problems in 39 of 39 on all four releases in Edge and Chrome. I viewed 5 PNGs on 12.1.0 and 11.4.1 (Cells-Go, JMAP-Python, Words-.NET, Cells-Java, PSD-.NET): no clipping, no stray lines.
   - Negative control: the same 39 sources with only `"wrappingWidth": 400` removed, on 12.1.0: my analysis finds 59 split words in 19 diagrams plus 141 further wraps ("password-protec / ted)", "Extended/Full-A / SCII)"); `check_entry` fails the same 19 diagrams with 59 split failures; on 11.4.1, 11.12.0 and 11.17.2: 0. So the token is the fix and the new check sees the defect.
   - The live diagrams on the same renderer: vertical 39 of 39; clipped in Verdana 39, Georgia 39, Arial 32, Tahoma 22, Segoe UI 20 (11.4.1; 12.1.0 similar); clipped natively in none. 733 HTML label boxes.
   - Labels and edges identical to live: my own parser compares live and redrawn source for 39 of 39: same id to label map (after `<br/>` to space), same group titles, same visible edges, same group membership, no `&`, `<` or `>` in a label, invisible `~~~` links only inside one group. Per-group order is unchanged (only the capability columns are listed in swapped source order, on purpose).
   - Advisory carried over: on 12.1.0 the second half of the capabilities is drawn on the left in 20 of 22 two-column diagrams (forward in 22 of 22 on every 11.x). Whether github.com runs 12.x is still unverified.
2. Replay confinement, 39 of 39, own script: every edit's offsets and original text match the live bytes; edits do not overlap; applying only the enumerated edits to `README.original.md` gives `README.md` byte for byte; the text outside the spans is identical; `git apply` of `README.patch` (autocrlf off) gives it byte for byte; the patch names only README.md; LF only; sha256 equals corrections.json. The 34 diagram-only patches change nothing outside the Mermaid fence; the 5 content patches change exactly: Cells-.NET and Cells-Cpp a Navigation item plus a Dependencies section; Cells-Go `#` to `##` at L105 and `</details>` before L529; PDF-Java 26.6.0 to 26.9.0 at L121 and L128; Words-.NET one NuGet badge at L5. Patch bytes and +/- per repo equal the owner table (78050 in all).
3. Idempotence and determinism, 39 of 39, own run with the 807ad30f code, each bundle's `facts.json`, `tree.txt` and the registry at the tip: the correction run on the corrected README makes zero edits; run on the original it gives the same edit list and the same bytes; the validation delta (introduced, allowed, resolved, revealed, both failure maps) reproduces exactly; introduced = 0 everywhere. The bundles come from 4b724575 and the code is 807ad30f: they agree, so the PR-text commit did not move a byte of any bundle.
4. Live drift: `gh api` today, all 44 heads equal the bundle revisions; `README.original.md` equals the live blob in all 43 bundles that have one; GIS-.NET has no README (404) at b9b8c9c7.
5. Content facts re-checked against fresh shallow clones at the pinned revisions and the registries: Cells-.NET csproj has one PackageReference (SkiaSharp 2.88.8) and `TargetFrameworks netstandard2.0;net8.0`, the published 26.9.0 nuspec lists the same; Cells-Cpp `cmake_minimum_required 3.16`, `CMAKE_CXX_STANDARD 17`, library includes standard headers only (GTest is fetched only by the test project); PDF-Java Maven Central metadata `latest` and `release` are 26.9.0 (versions 26.6.0, 26.8.0, 26.9.0), the 26.9.0 `.pom` answers 200, only the two edited strings carried 26.6.0; Words-.NET nuget.org lists 26.2.0 and 26.3.0 under the id `Aspose.Words.FOSS`; Cells-Go: the `<details>` is opened at L501 and never closed and L105 is a second H1 (live README read).
6. Secrets and paths: no token, key, credential or e-mail in any PR text; no local path in any PR text. The only `Authorization: Bearer <token>` hits are placeholders inside the upstream JMAP READMEs.

## 3. The 39 pull request texts

I read all 39 (the 34 diagram-only texts are one template with numbers). Every number was checked by script against corrections.json and validation_delta.json: diagram line, label and group-title counts (against my own parse), introduced and fewer failures, the allowance and the revealed-text clauses, the render line (releases, 5 wider fonts, 0 clipped, 0 splits, 0 problems), model calls 0, idempotent and deterministic yes, candidate_hash and source_revision: 0 mismatches in 39. How to review and How to decline are in 39 of 39. "Only README.md changes" and "with the edits removed, the corrected README and yours are identical" are true (section 2, item 2). The real send replaces `policy_version: (set when sent)` (cli.py composes with `CURRENT_POLICY_VERSION`); the placeholder is only in the rehearsal files.

### Sentences I would not sign (the 8 FIX_REQUIRED)

| Repo | Sentence (generator source) | Why |
|---|---|---|
| BarCode-Python | "...and the chain Starting Points -> product -> Core Capabilities -> Outputs are unchanged (compared by script)" (`pull_request.py` `_bullet`, hard-coded) | false for this README: its diagram has no Starting Points block (the chain is product -> Core Capabilities -> Outputs) |
| HTML-Python | the same sentence | false: its first group is titled "Inputs and formats" |
| Email-Cpp, PDF-Java | "1 recorded under owner ruling(s) OD-06, R7" (`_delta_lines`) | unexplained internal identifiers; "owner" reads as the repository owner. The recorded fact is "the redraw adds its init line and column links, so the README's visible length is 303 lines (PDF-Java 304) against the project's own limit of 300" |
| Words-.NET | "The README lacks published-version badge, which the repository ... verifies" and "the registry's leads its badge row (the package badge is first in the stable order)" (`additions.py:630`, `_lead`) | garbled; a maintainer cannot read it |
| Cells-.NET, Cells-Cpp | "the README has no Dependencies section; the template's is rendered from the cited facts alone" (`sections.py:376`) and evidence `dependency:skiasharp (SUPPORTED)` ... | "the template's" is not a sentence a maintainer can read; the evidence names fact ids, not the file and line that holds SkiaSharp 2.88.8 (csproj) or CMake 3.16 and C++17 (`CMakeLists.txt`), so the claim cannot be checked from the PR |
| Cells-Go | "the template has exactly one [H1]" (`structure.py:46`), "it ends before the next H2, line 529" (`structure.py:107`) | jargon as the reason; and an inferred closing point stated as fact (the owner table itself calls it inferred). Also the first clause "fail no check more often" is literally false for BC-04 (23 against 22), disclosed only in the same sentence |

### Advisories in all or most texts (non-blocking, one generator edit each)

- U-1, all 39: "The project's validators (`validate_candidate`, checks BC-01 to BC-14) ..." names internal identifiers, and "the project's" is ambiguous to a maintainer. This is the owner's own "no internal artifact names" criterion; I did not block on it alone because the sentence is true and only opaque. If the owner wants the criterion literal, all 39 move to FIX_REQUIRED and the same single edit clears them. Suggested: "The repository's own README checks report no new failure on the corrected README (0 introduced, N fewer)."
- U-2, all 39: the bullet says "redrawn left to right so text no longer clips". The live diagrams clip in no native font (0 of 39) and only in a wider one (20 to 39 of 39); the lead says "a wider font can clip" but the bullet reads as a present defect. Suggested: "so a wider font cannot clip it".
- U-3, all 39: "Proposed by repository-presenter." has no contact and no reason this repository was chosen (carried over from review 3). The effect needs the provenance block; a human line above it would cost one sentence.
- U-4, five content PRs: the diagram redraw rides in the same PR as the factual fix (the 5 content PRs are one bundle each). A maintainer who dislikes the diagram has to decline the fix too (How to decline closes the whole PR). Review 3 asked for a split; it is not done.
- Cells-.NET: the new Dependencies section lists SkiaSharp, which ships native assets for Windows and macOS only (SkiaSharp 2.88.8 nuspec), while the intro still says "pure managed ... Linux" and the new heading is "Native and System Requirements" listing only the target frameworks. True as written, incomplete by omission; worth one sentence in the PR.
- Words-.NET: L952 still says "The NuGet package ... landing soon" next to the new badge; the PR does not mention it (`stale_phrase` reports it).
- Cells-Go: `##` on a sentence leaves a sentence as a heading and the Navigation item unindented; deleting the `#` would read better.
- Titles read as sentences; the content titles are 95 to 123 characters.

## 4. Order and holds

- `pr_order`: exactly the five content repos carry 1 (Cells-.NET, Cells-Cpp, Cells-Go, PDF-Java, Words-.NET), 34 carry 2, the five no-push entries carry none. Sensible. The owner table lists the 34 diagram PRs alphabetically and says "send a handful with the biggest gain" without naming them. By my own estimate at a 896 px column (drawn text scale after over before; median x1.29, 9 of 39 below 1): PDF-Go x1.96, Slides-Python x1.75, Email-Python x1.68, Words-Python x1.63, PDF-Python x1.57 are PUSHABLE now and make a clean pilot. (Cells-Java x2.15 is the biggest gain but the drawing grows from about 395 px to about 1000 px tall; BarCode-Python x1.77 and Email-Cpp x1.69 wait for their text fix.)
- 3D-.NET hold confirmed: `IOService.cs` (L57-67, L78-88) dispatches OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS and throws `NotSupportedException` otherwise; the diagram labels U3D, RVM, AMF, HTML5. The README's last commits are the owner's own refreshes, so this is a README correction (remove the labels) as much as an issue. The bundle republishes the labels verbatim.
- TeX-Python hold confirmed: `ast.parse` fails on 102 of 119 `.py` files (36 of 46 non-test files), all "expected an indented block". The pairing issue exists in the issue approval table (c00f9615, "FILE wave 1b"); `upstream-defect-drafts` holds no draft for either held repo.
- Five no-push reasons confirmed (acc-corr4 records).

## 5. Final owner-ready list

### A. PUSHABLE now: 29 diagram-only repos, 55590 patch bytes, one title for all: `docs(readme): lay out the At a Glance diagram left to right`

| Repo | Patch bytes (+/-) |
|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | 1698 (+17/-14) |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 1990 (+20/-17) |
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | 2036 (+22/-17) |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | 2706 (+27/-22) |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | 2082 (+22/-17) |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | 1586 (+14/-10) |
| aspose-email-foss/Aspose.Email-FOSS-for-Python | 2041 (+16/-12) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-.NET | 1756 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Cpp | 1822 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Go | 1762 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Java | 1756 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js | 1762 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Python | 1760 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-Rust | 1756 (+14/-10) |
| aspose-email-foss/Aspose.JMAP-FOSS-for-TypeScript | 1772 (+14/-10) |
| aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | 1504 (+13/-11) |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | 1469 (+16/-13) |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | 2027 (+21/-16) |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | 3020 (+30/-25) |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | 2034 (+21/-17) |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | 2517 (+25/-20) |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | 2549 (+26/-21) |
| aspose-psd-foss/Aspose.PSD-FOSS-for-.NET | 920 (+6/-5) |
| aspose-psd-foss/Aspose.PSD-FOSS-for-Python | 924 (+6/-5) |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | 1966 (+19/-16) |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | 2027 (+21/-17) |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | 2047 (+21/-17) |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | 2451 (+24/-20) |
| aspose-words-foss/Aspose.Words-FOSS-for-Python | 1850 (+15/-11) |

Send a pilot first (section 4), not all 29 at once.

### B. FIX_REQUIRED (text only), 8 repos, 18439 patch bytes: the patch is final, change the generated text, then send

| Repo | PR title as generated | Patch bytes (+/-) | Records |
|---|---|---|---|
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET (content, order 1) | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2588 (+31/-15) | `acc-corr4-cells-net.md` |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp (content, order 1) | docs(readme): add the Dependencies section and its Navigation item and lay out the At a Glance diagram left to right | 2799 (+32/-17) | `acc-corr4-cells-cpp.md` |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go (content, order 1) | docs(readme): demote a stray second H1, close an unclosed <details> block and lay out the At a Glance diagram left to right | 2786 (+24/-17) | `acc-corr4-cells-go.md` |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (content, order 1) | docs(readme): show the current release (26.9.0) in the install snippets and lay out the At a Glance diagram left to right | 2541 (+26/-21) | `acc-corr4-pdf-java.md` |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET (content, order 1) | docs(readme): add the published-version badge and lay out the At a Glance diagram left to right | 2466 (+22/-17) | `acc-corr4-words-net.md` |
| aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | docs(readme): lay out the At a Glance diagram left to right | 1253 (+10/-7) | `acc-corr4-barcode-python.md` |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | docs(readme): lay out the At a Glance diagram left to right | 1863 (+17/-13) | `acc-corr4-email-cpp.md` |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | docs(readme): lay out the At a Glance diagram left to right | 2143 (+20/-16) | `acc-corr4-html-python.md` |

Generator edits that clear all eight (and U-1 to U-3 for everyone), all in `src/repository_presenter/components/readme_correction/`: (1) `pull_request.py` `_bullet`: build the chain from `glance.titles` instead of the fixed four names; (2) `pull_request.py` `_delta_lines`: state the visible-length fact in words, drop "owner ruling(s)"; (3) `additions.py:630` and `pull_request.py` `_lead` ("info"): rewrite the badge sentences; (4) `detectors/sections.py:376` and `_evidence`: say what the section states and cite file and line, not "the template's" and fact ids; (5) `detectors/structure.py:46,107`: plain reason, mark the closing point as our reading; (6) U-1, U-2, U-3 as above. None of this touches a bundle, because the text is composed at send time from the bundle.

### C. HOLD, 2 repos, 4021 patch bytes: Aspose.3D-FOSS-for-.NET (2401, +24/-19), Aspose.TeX-FOSS-for-Python (1620, +13/-10). Records `acc-corr4-3d-net.md`, `acc-corr4-tex-python.md`.

### D. DO_NOT_PUSH, 5: Aspose.Cells-FOSS-for-Python, Aspose.Cells-FOSS-for-Rust, Aspose.Font-FOSS-for-Python, Aspose.PDF-FOSS-for-.NET, Aspose.GIS.FOSS-for-.Net. Records `acc-corr4-cells-python.md`, `acc-corr4-cells-rust.md`, `acc-corr4-font-python.md`, `acc-corr4-pdf-net.md`, `acc-corr4-gis-net.md`.

## 6. What I could not verify

- Rendering on github.com itself (its Mermaid version and fonts). Paste a fenced `mermaid` block holding only `info` into any README preview to read the version; with `wrappingWidth: 400` the redraw holds on 11.4.1 to 12.1.0 either way, and on 12.x the capability columns read in reverse order (advisory).
- The truth of the maintainers' own diagram labels, apart from 3D-.NET (the hold) and the five content repos; the redraw republishes them verbatim.
- The no-detector-fired READMEs (Cells-Python, Font-Python, PDF-.NET): I confirm there is no patch, not that those READMEs are accurate.
- Library builds and tests (no toolchain run); content edits rest on manifests, CMake files and registries.
