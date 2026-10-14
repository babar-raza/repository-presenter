authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr3-summary: independent review of the FINAL live-first correction run (all 44 registry entries)

Reviewer: independent (Sonnet 5.5), read-only. I did not author the run. Run: `scratchpad/lfix/runs/20261011-4e2da176` (CURRENT points at it; code branch `wt/lfix-fix01` tip 4e2da176, an ancestor of `integration/cut4`). Per-repo records: `acc-corr3-<name>.md` (44 files, this directory). Evidence: `scratchpad/acccorr3/` (own snapshot of the run, fresh shallow clones of all 44 live heads, own renders, scripts).

## 1. Result

| Verdict | Count | Meaning |
|---|---|---|
| PUSHABLE | 20 | patch verified; 42129 patch bytes in all |
| FIX_REQUIRED (MINOR) | 19 | correct patch, but the redrawn diagram splits words mid-token on Mermaid 12.1.0; one generator token fixes it (section 3); 35063 patch bytes |
| DO_NOT_PUSH | 5 | 4 no-edit entries (Cells-Python, Cells-Rust, Font-Python, PDF-.NET: "no detector fired") and GIS (no README): there is nothing to push |

What held for all 39 corrected bundles (own runs, not the lane's records):
- Run directory: `sha256sum -c SHA256SUMS` 353 of 353 OK, re-run at the end; my copy is byte-identical; CURRENT unchanged.
- Live heads: `git ls-remote` of all 44 equals each bundle's revision, at the start and at the end (no drift). Fresh `git clone --depth 1` of all 44; `README.original.md` equals the live blob in all 43 bundles that have one.
- Replay confinement: applying only the enumerated edits to the live README reproduces `README.md` byte for byte in 39 of 39 (edits matched, no overlap, removing the edit spans leaves identical text); `README.patch` applies with `git apply` and reproduces it in 39 of 39; LF only.
- No add_dev_commands or add_doc_links edit survives anywhere (detectors present: at_a_glance_diagram 39, missing_sections 2 bundles, claim_version, add_version_badge, second_h1, unclosed_details; report-only items all carry a typed reason). Outside the Mermaid fence the 34 diagram-only patches change not one line; the 5 content patches change exactly the lines listed in their records; no narration or process wording.
- Diagram identity by my own parse: 39 of 39 keep every node id and label (after `<br/>` normalisation), every subgraph title, every visible edge and every parent; per-group order unchanged (only the two capability columns are listed in swapped source order, on purpose). No label holds `&`, `<`, `>` or an entity reference (the one live diagram that does, Cells-Rust `Vec<u8>`, is rightly withheld).
- Real render by me (the repo's `render_check` with the lane's pinned tools, headless Edge 155, native font plus Arial, Verdana, Tahoma, Segoe UI, Georgia) on mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0, all 39 redrawn diagrams: horizontal on 4 of 4, 0 clipped fonts, no native spill, no node overlap, blocks left to right, ids top to bottom. The live diagrams, same renderer: vertical in 39 of 39, clipped in at least one font in 39 of 39 (Verdana 39, Georgia 39, Arial 32, Tahoma 22, Segoe UI 20) but in the native font in none. I viewed 13 PNGs including all 5 content-edit repos.
- Links and structure: no new broken link, no new duplicate H2, no H2 left out of Navigation, Navigation anchors resolve; Cells-.NET and Cells-Cpp gain a Navigation item that resolves; Cells-Go's unclosed `<details>` is fixed (its H2s leave the collapsed block).
- `validation_delta`: introduced = 0 in all 43 bundles that have one; two recorded allowances (BC-07/visible: Email-Cpp, PDF-Java); one revealed pre-existing failure (Cells-Go BC-04 `v26`). no_op proof byte-identical and idempotent, 0 provider calls.

## 2. Content edits re-verified against clone and registry (5 repos)

| Repo | Edit | Verified against | Result |
|---|---|---|---|
| Cells-.NET | + Dependencies (SkiaSharp 2.88.8, TFMs) and Navigation item | csproj L53 (only PackageReference), L3 TFMs; nuspec of published 26.9.0 | TRUE; advisory: SkiaSharp 2.88.8 ships Win32 and macOS native assets only, the intro still says "pure managed ... Linux" |
| Cells-Cpp | + Dependencies (none, C++17, CMake 3.16) | CMakeLists L1, L4; include census: standard library only | TRUE |
| Cells-Go | `</details>` before `## Detailed Documentation`; L105 `#` to `##` | live README (details 1 opened / 0 closed; two H1) | CONFIRMED defects; the H1 fix is half-way (sentence stays a heading, Navigation indentation no longer matches); dropping the `#` would be better |
| PDF-Java | 26.6.0 to 26.9.0 at L121 and L128 | Maven Central metadata latest/release 26.9.0 (2026-10-07), `.pom` and `.jar` 200, pom.xml 26.9.0 | TRUE; no other `26.x.y` left |
| Words-.NET | + NuGet badge | nuget.org 26.2.0 and 26.3.0, badge reads `v26.3.0` | TRUE; advisory: L957 still says "NuGet package ... landing soon" |

## 3. Universal findings (generator, not a repo)

1. **Mermaid 12.x breaks the redraw's labels (new, not covered by the lane's `check_entry`).** On 12.1.0, SVG-text labels are auto-wrapped at about 15 characters on top of the hard `<br/>` breaks: 200 nodes in all 39 diagrams get extra lines, and in 19 diagrams 59 nodes split a word mid-token: "password-protec / ted)", "username/passw / ord", "(jmap.JmapClie / nt)", "Request/Respon / se", "Aspose.PSD.FOS / S". 11.4.1, 11.12.0 and 11.17.2: 0. `check_entry` only fails when a label has fewer lines than the model, so the lane's "0 problems on 4 releases" is true by its metric and false to a reader. **Validated fix: add `"wrappingWidth": 400` to the `flowchart` object of the init line.** I re-rendered all 39 after-bodies with it: 0 stray wraps and 0 mid-word breaks on 12.1.0, lines unchanged on the three 11.x releases, still horizontal with 0 clipped fonts on all 4. Whether github.com runs 12.x is unverified: the owner can find out in ten seconds by pasting a fenced `mermaid` block holding only `info` into any README preview (it prints the version). If GitHub is below 12, the 19 FIX_REQUIRED become PUSHABLE as they stand; if 12.x, regenerate with the token and re-review.
2. **Known and accepted: on 12.1.0 the two capability columns are reversed in 19 of 22 two-column diagrams** (first half drawn on the right); forward on all three 11.x releases. `check_entry` documents this; advisory only.
3. **Diagram labels are the maintainers' own and unverified.** The patch republishes them verbatim. Two matter: 3D-.NET (diagram advertises U3D, RVM, AMF, HTML5; `IOService` switches only on OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS and throws otherwise) and TeX-Python (102 of 119 `.py` files do not parse at head 181015d2). Neither blocks the patch; both argue for an issue first.
4. **The PR composer is not correction-aware** (section 5): it cannot be fed a correction bundle without producing a misleading body.
5. Two real broken links the closed detector set cannot fix, in no-edit repos: Cells-Python `RELEASE_NOTES.md` (L164) and Font-Python `docs/one_command_web_optimizer.md` (L518); both targets are absent from the clones. Issues, not patches.

## 4. Is a diagram-only PR worth a maintainer's attention?

Honest answer: marginal on its own, worth sending only as a small, well-evidenced pilot.
- The change is presentation: every label, title and edge is preserved (machine-compared). The measured benefit is shape, not content: median drawn height 573 px to 502 px at a 896 px README column, and median text scale x1.29 (estimate from the render sizes). It is not uniform: for 9 of 39 the text is slightly smaller after (x0.88 to x0.96) even though the drawing is 45 to 60 percent shorter (Note Python, 3D Java, PSD Python, PSD .NET, Imaging .NET, Cells .NET, 3D TypeScript, Words .NET, Page Python).
- The "clipping" defect is conditional. Live diagrams clip in 0 of 39 with the renderer's native font and in 20 to 39 of 39 under a wider font; whether github.com's font stack triggers it is not something I could verify here. A maintainer who opens their README and sees nothing wrong has no reason to merge a change to a diagram they wrote.
- The redrawn source is harder to maintain: labels carry hard `<br/>` breaks, there are invisible `~~~` links and an init line.
- Strong cases (text x1.4 or more at README width): Cells Java x2.13, PDF Go x1.94, BarCode Python x1.80, Slides Python x1.74, Email Cpp x1.67, Email Python x1.66, Words Python x1.62, PDF Python x1.56, PDF Java x1.54, Cells Cpp x1.47.
Recommendation: (1) send the 5 content PRs first, each as its own PR and with the diagram split off (a declined diagram must not sink a factual fix); (2) pilot the diagram on 3 to 5 repos with the biggest gain, with before and after rendered live in the PR body (GitHub renders ```mermaid blocks in PR descriptions), and wait for a response before the other ~30; (3) do not open 34 near-identical PRs at once; (4) first fix finding 3.1 or confirm the GitHub version.

## 5. Pull request descriptions: generator output, critique, proposal

I ran `compose_pull_request` (components/propose/pull_request.py, as in wt/lfix) on the corrected and live READMEs of PDF-Java, Cells-Go and 3D-Python (and Words-.NET). Raw outputs are in `scratchpad/acccorr3/pr/`. Example, 3D-Python:

```
docs(readme): refresh Aspose.3D FOSS for Python README (1 section updated)

Refreshes the README of **Aspose.3D FOSS for Python** from the repository as it stands at revision `65b1f577c0f1`. Only `README.md` changes.
### What changed
- Rewritten sections (1): **At a Glance**
- Size of the change: 20 lines added, 17 removed.
### What was verified
- No verification counts were recorded for this proposal.
### How to review
Open **Files changed** ... Every statement in the new text was checked against this repository at the revision above, and your existing README was reconciled section by section.
### How to decline ...
```
Cells-Go came out as "(4 sections updated)" with "Rewritten sections (3): At a Glance, Installation, Development and Testing" and "New sections (1): **Requires Go 1.24.5+ (see go.mod). Depends only on the Go standard library - no third-party modules.**"; Words-.NET as "Rewritten sections (2): Introduction, At a Glance"; PDF-Java as "At a Glance, Installation".

Critique:
1. **Overclaim.** "Every statement in the new text was checked ... your existing README was reconciled section by section" is false for a correction (a diagram-only PR has no new statements; a content PR checked specific ones). A maintainer who tests it once stops trusting the rest. Replace with the exact per-edit checks.
2. **"No verification counts were recorded for this proposal."** advertises the absence of proof. The composer reads `validation.json` and example receipts; a correction bundle has neither (it has `validation_delta.json`, `corrections.json` evidence, replay and render records), so every correction PR would say this.
3. **"What changed" is a heading diff, not the edits.** It lists Installation as rewritten (really `#` to `##`), Development and Testing (really a closing tag), a "new section" that is a whole sentence, "Introduction" for a badge row. The reason and the line numbers are in `corrections.json` (`kind`, `line`, `rationale`, `evidence`) and unused.
4. **No why, no benefit.** The title ("refresh ... README (N sections updated)") is identical for every PR and suggests a content rewrite. A diagram PR needs "lay out the At a Glance diagram left to right" and visible proof.
5. **Bundles taste with fact.** Content and diagram land in one PR (Cells-Go, PDF-Java, Words-.NET, both Cells variants). Split them.
6. **Who is this?** "Proposed by repository-presenter" has no owner, contact or reason this repo was chosen; unknown-bot PRs get ignored.
7. Good and worth keeping: "Only `README.md` changes", the decline paragraph (closed means not reopened), the provenance footer the effect reads back. Recommendation: a correction-aware composer fed by `corrections.json`.

### Proposed PR 1: Aspose.PDF-FOSS-for-Java (content only; diagram in a second PR)
Title: `docs(readme): show the current release (26.9.0) in the Maven and Gradle snippets`
```
The Installation section still pins org.aspose:aspose-pdf-foss at 26.6.0 (README.md lines 121 and 128). Maven Central lists 26.9.0 as the latest release (26.6.0, 26.8.0 and 26.9.0 exist) and pom.xml on main is already 26.9.0, so a reader who copies the snippet gets a release two versions behind.

What changes: README.md L121 (Maven) and L128 (Gradle), 26.6.0 -> 26.9.0. Two strings; nothing else in this PR.

How it was checked
- repo1.maven.org/maven2/org/aspose/aspose-pdf-foss/maven-metadata.xml: <latest> and <release> are 26.9.0.
- The 26.9.0 .pom and .jar exist on Maven Central.
- pom.xml at 736cedaa: <version>26.9.0</version>.
- No other 26.x.y remains in the README.

Not in this PR: the At a Glance diagram redraw (separate PR, take it or leave it).
Decline: close it; it will not be reopened. Sent by repository-presenter for <owner>, contact <address>.
---
Provenance: candidate_hash, source_revision 736cedaa..., policy_version
```
### Proposed PR 2: Aspose.Cells-FOSS-for-Go (structure fixes only)
Title: `docs(readme): close the unclosed <details> block and demote a stray second H1`
```
Two rendering problems in README.md, no wording changed (diff +3/-1):
1. The <details> at L501 ("More Test and Example Commands") is never closed, so on GitHub everything after it - Detailed Documentation, Constraints, License - renders collapsed inside it. This adds </details> before "## Detailed Documentation" (L529), where we think it was meant to end; tell us if not.
2. L105 starts with "# Requires **Go 1.24.5+** ...", a second top-level heading under the title. Changed to "##". If it was meant as a comment in the install block above, delete the "#" or move it into the fence instead; we did not guess.
Checked: before, <details> opened 1 / closed 0 and two H1; after, 1 / 1 and one H1; every Navigation anchor and relative link still resolves; no other line changes.
Note: Navigation still lists the L105 line unindented; regenerate it if you keep it as a heading.
Not in this PR: the diagram redraw (separate).
Decline: close it; it will not be reopened. Sent by repository-presenter for <owner>.
```
### Proposed PR 3: Aspose.3D-FOSS-for-Python (diagram only)
Title: `docs(readme): lay out the At a Glance diagram left to right`
```
The At a Glance diagram (README.md L29) is "flowchart TD", so on GitHub the three blocks stack vertically and the 11 labels sit in HTML boxes that a wider font can clip (the current diagram clips in 3 to 5 of the 5 stress fonts I tried, depending on the Mermaid release). This redraws the same diagram left to right. Mermaid body only; no prose touched.

Identical: all 11 labels, the 5 group titles, the 3 edges and the order of capabilities (compared by script).
Changed: layout hints only - flowchart LR, hard <br/> line breaks, invisible ~~~ links that keep columns in order, and one %%{init}%% line that switches to SVG text so a font cannot clip it.

Before (collapsed) and after, rendered live by GitHub:  [before block] [after block]

Measured (headless Edge; Mermaid 11.4.1, 11.12.0, 11.17.2, 12.1.0): horizontal on all four, 0 labels clipped in 6 fonts. At README width the text is about 20 percent larger (0.65x -> 0.80x) and the drawing about 100 px shorter. Trade-off: labels now carry <br/> breaks, so editing a label means re-breaking its lines.
Decline: close it; it will not be reopened. Sent by repository-presenter for <owner>.
```
(3D-Python is not one of the 19 with a 12.1.0 mid-word break; for the other 19, add the wrappingWidth token before sending.)

## 6. Final owner-ready list

### A. PUSHABLE now (20 repos, 42129 patch bytes)
| Repo | Patch bytes | What changes | Note |
|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | 2379 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else | pair with an upstream-defect issue: the diagram advertises U3D/RVM/AMF/HTML5 the code rejects |
| Aspose.3D-FOSS-for-Java | 1676 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.3D-FOSS-for-Python | 1968 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.3D-FOSS-for-TypeScript | 2014 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Cells-FOSS-for-.NET | 2566 | Dependencies section + Navigation item (SkiaSharp 2.88.8, TFMs) and the diagram |  |
| Aspose.Cells-FOSS-for-Cpp | 2777 | Dependencies section + Navigation item (no third-party deps, C++17, CMake 3.16) and the diagram |  |
| Aspose.Cells-FOSS-for-TypeScript | 2060 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Email-FOSS-for-.Net | 1564 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Email-FOSS-for-Cpp | 1841 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Imaging-FOSS-for-.NET | 1482 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose-PDF-FOSS-for-Go | 2998 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose-PDF-FOSS-for-Python | 2012 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.PDF-FOSS-for-Java | 2519 | Maven and Gradle version 26.6.0 -> 26.9.0 (2 strings) and the diagram |  |
| Aspose.Slides-FOSS-for-.NET | 1944 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Slides-FOSS-for-Cpp | 2005 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Slides-FOSS-for-Java | 2025 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.Slides-FOSS-for-Python | 2429 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |
| Aspose.TeX-FOSS-for-Python | 1598 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else | HOLD recommended: upstream source does not parse (102 of 119 .py files) |
| Aspose.Words-FOSS-for-.NET | 2444 | NuGet version badge (26.3.0 live) and the diagram |  |
| Aspose.Words-FOSS-for-Python | 1828 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |  |

Order of sending: the content changes first, each as its own PR separate from the diagram (Cells-.NET, Cells-Cpp, PDF-Java, Words-.NET, plus Cells-Go's two structure hunks from list B); then a diagram pilot from the strong cases (PDF-Go, Slides-Python, Email-Cpp, Words-Python, PDF-Python); hold TeX-Python; open the 3D-.NET issue with its PR.

### B. FIX_REQUIRED (MINOR, one generator token), 19 repos, 35063 patch bytes
Add `"wrappingWidth": 400` to the redraw's init line and regenerate (or confirm GitHub renders Mermaid below 12). Cells-Go's content hunks (second_h1 and unclosed_details, +3/-1) are good now and can go as a content-only PR.
| Repo | Patch bytes | What changes |
|---|---|---|
| Aspose.BarCode-FOSS-for-Python | 1231 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.Cells-FOSS-for-Go | 2764 | closes the unclosed <details>, demotes the 2nd H1 (+3/-1), and the diagram |
| Aspose.Cells-FOSS-for-Java | 2684 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.Email-FOSS-for-Python | 2019 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-.NET | 1734 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Cpp | 1800 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Go | 1740 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Java | 1734 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Node.js | 1740 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Python | 1738 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-Rust | 1734 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.JMAP-FOSS-for-TypeScript | 1750 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.HTML-FOSS-for-Python | 2121 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.Note-FOSS-for-Python | 1447 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.Page-FOSS-for-Python | 2005 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.PDF-FOSS-for-Cpp | 2495 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.PDF-FOSS-for-TypeScript | 2527 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.PSD-FOSS-for-.NET | 898 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |
| Aspose.PSD-FOSS-for-Python | 902 | At a Glance diagram redrawn left to right; same labels, titles and edges, nothing else |

### C. DO_NOT_PUSH (5): Cells-Python, Cells-Rust, Font-Python, PDF-.NET (nothing to push), GIS-.NET (no README).

## 7. Verdict table (44 rows)
| Repo | Record | Status | Edits | Patch bytes | Verdict | minor/major |
|---|---|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | `acc-corr3-3d-net.md` | corrected | at_a_glance_diagram | 2379 | **PUSHABLE** | minor advisory |
| Aspose.3D-FOSS-for-Java | `acc-corr3-3d-java.md` | corrected | at_a_glance_diagram | 1676 | **PUSHABLE** | none |
| Aspose.3D-FOSS-for-Python | `acc-corr3-3d-python.md` | corrected | at_a_glance_diagram | 1968 | **PUSHABLE** | none |
| Aspose.3D-FOSS-for-TypeScript | `acc-corr3-3d-typescript.md` | corrected | at_a_glance_diagram | 2014 | **PUSHABLE** | none |
| Aspose.BarCode-FOSS-for-Python | `acc-corr3-barcode-python.md` | corrected | at_a_glance_diagram | 1231 | **FIX_REQUIRED** | MINOR |
| Aspose.Cells-FOSS-for-.NET | `acc-corr3-cells-net.md` | corrected | at_a_glance_diagram, missing_sections | 2566 | **PUSHABLE** | minor advisory |
| Aspose.Cells-FOSS-for-Cpp | `acc-corr3-cells-cpp.md` | corrected | at_a_glance_diagram, missing_sections | 2777 | **PUSHABLE** | minor advisory |
| Aspose.Cells-FOSS-for-Go | `acc-corr3-cells-go.md` | corrected | at_a_glance_diagram, second_h1, unclosed_details | 2764 | **FIX_REQUIRED** | MINOR |
| Aspose.Cells-FOSS-for-Java | `acc-corr3-cells-java.md` | corrected | at_a_glance_diagram | 2684 | **FIX_REQUIRED** | MINOR |
| Aspose.Cells-FOSS-for-Python | `acc-corr3-cells-python.md` | no_detector_fired | - | 0 | **DO_NOT_PUSH** | n/a |
| Aspose.Cells-FOSS-for-Rust | `acc-corr3-cells-rust.md` | no_detector_fired | - | 0 | **DO_NOT_PUSH** | n/a |
| Aspose.Cells-FOSS-for-TypeScript | `acc-corr3-cells-typescript.md` | corrected | at_a_glance_diagram | 2060 | **PUSHABLE** | none |
| Aspose.Email-FOSS-for-.Net | `acc-corr3-email-net.md` | corrected | at_a_glance_diagram | 1564 | **PUSHABLE** | none |
| Aspose.Email-FOSS-for-Cpp | `acc-corr3-email-cpp.md` | corrected | at_a_glance_diagram | 1841 | **PUSHABLE** | none |
| Aspose.Email-FOSS-for-Python | `acc-corr3-email-python.md` | corrected | at_a_glance_diagram | 2019 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-.NET | `acc-corr3-jmap-net.md` | corrected | at_a_glance_diagram | 1734 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Cpp | `acc-corr3-jmap-cpp.md` | corrected | at_a_glance_diagram | 1800 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Go | `acc-corr3-jmap-go.md` | corrected | at_a_glance_diagram | 1740 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Java | `acc-corr3-jmap-java.md` | corrected | at_a_glance_diagram | 1734 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Node.js | `acc-corr3-jmap-nodejs.md` | corrected | at_a_glance_diagram | 1740 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Python | `acc-corr3-jmap-python.md` | corrected | at_a_glance_diagram | 1738 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-Rust | `acc-corr3-jmap-rust.md` | corrected | at_a_glance_diagram | 1734 | **FIX_REQUIRED** | MINOR |
| Aspose.JMAP-FOSS-for-TypeScript | `acc-corr3-jmap-typescript.md` | corrected | at_a_glance_diagram | 1750 | **FIX_REQUIRED** | MINOR |
| Aspose.Font-FOSS-for-Python | `acc-corr3-font-python.md` | no_detector_fired | - | 0 | **DO_NOT_PUSH** | n/a |
| Aspose.GIS.FOSS-for-.Net | `acc-corr3-gis-net.md` | no README | - | 0 | **DO_NOT_PUSH** | n/a |
| Aspose.HTML-FOSS-for-Python | `acc-corr3-html-python.md` | corrected | at_a_glance_diagram | 2121 | **FIX_REQUIRED** | MINOR |
| Aspose.Imaging-FOSS-for-.NET | `acc-corr3-imaging-net.md` | corrected | at_a_glance_diagram | 1482 | **PUSHABLE** | none |
| Aspose.Note-FOSS-for-Python | `acc-corr3-note-python.md` | corrected | at_a_glance_diagram | 1447 | **FIX_REQUIRED** | MINOR |
| Aspose.Page-FOSS-for-Python | `acc-corr3-page-python.md` | corrected | at_a_glance_diagram | 2005 | **FIX_REQUIRED** | MINOR |
| Aspose-PDF-FOSS-for-Go | `acc-corr3-pdf-go.md` | corrected | at_a_glance_diagram | 2998 | **PUSHABLE** | none |
| Aspose-PDF-FOSS-for-Python | `acc-corr3-pdf-python.md` | corrected | at_a_glance_diagram | 2012 | **PUSHABLE** | none |
| Aspose.PDF-FOSS-for-.NET | `acc-corr3-pdf-net.md` | no_detector_fired | - | 0 | **DO_NOT_PUSH** | n/a |
| Aspose.PDF-FOSS-for-Cpp | `acc-corr3-pdf-cpp.md` | corrected | at_a_glance_diagram | 2495 | **FIX_REQUIRED** | MINOR |
| Aspose.PDF-FOSS-for-Java | `acc-corr3-pdf-java.md` | corrected | at_a_glance_diagram, claim_version | 2519 | **PUSHABLE** | minor advisory |
| Aspose.PDF-FOSS-for-TypeScript | `acc-corr3-pdf-typescript.md` | corrected | at_a_glance_diagram | 2527 | **FIX_REQUIRED** | MINOR |
| Aspose.PSD-FOSS-for-.NET | `acc-corr3-psd-net.md` | corrected | at_a_glance_diagram | 898 | **FIX_REQUIRED** | MINOR |
| Aspose.PSD-FOSS-for-Python | `acc-corr3-psd-python.md` | corrected | at_a_glance_diagram | 902 | **FIX_REQUIRED** | MINOR |
| Aspose.Slides-FOSS-for-.NET | `acc-corr3-slides-net.md` | corrected | at_a_glance_diagram | 1944 | **PUSHABLE** | none |
| Aspose.Slides-FOSS-for-Cpp | `acc-corr3-slides-cpp.md` | corrected | at_a_glance_diagram | 2005 | **PUSHABLE** | none |
| Aspose.Slides-FOSS-for-Java | `acc-corr3-slides-java.md` | corrected | at_a_glance_diagram | 2025 | **PUSHABLE** | none |
| Aspose.Slides-FOSS-for-Python | `acc-corr3-slides-python.md` | corrected | at_a_glance_diagram | 2429 | **PUSHABLE** | none |
| Aspose.TeX-FOSS-for-Python | `acc-corr3-tex-python.md` | corrected | at_a_glance_diagram | 1598 | **PUSHABLE** | minor advisory (HOLD recommended) |
| Aspose.Words-FOSS-for-.NET | `acc-corr3-words-net.md` | corrected | add_version_badge, at_a_glance_diagram | 2444 | **PUSHABLE** | minor advisory |
| Aspose.Words-FOSS-for-Python | `acc-corr3-words-python.md` | corrected | at_a_glance_diagram | 1828 | **PUSHABLE** | none |

## 8. What I could not verify
- Rendering on github.com itself (its Mermaid version, fonts and iframe sizing): all renders are headless Edge 155 with four pinned mermaid releases. The `info` diagram test above settles the version.
- The text-scale and height figures are estimates from render pixel sizes at a 896 px column.
- The truth of the maintainers' diagram labels (only the two noted repos were spot-checked); build and test of the libraries (no toolchains run; the content edits rest on manifests, CMake files, registries).
- Idempotence: I confirmed replay and patch reproduction and the recorded proof, but did not re-run `correct-readme` itself.
