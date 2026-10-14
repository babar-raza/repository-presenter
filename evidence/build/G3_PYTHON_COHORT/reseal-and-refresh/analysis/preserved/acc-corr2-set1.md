authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-set1: independent review of the live-first correction bundles, registry entries 1-14

Reviewer: independent (Sonnet 5.5), read-only. Method: acceptance protocol v1.1 (`git show wt/lacc-acc01:evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/acceptance-protocol.md`) adapted to a patch. Per-repo records: `acc-corr2-<name>.md` in this directory (3d-net, 3d-java, 3d-python, 3d-typescript, barcode-python, cells-net, cells-cpp, cells-go, cells-java, cells-python, cells-rust, cells-typescript, email-net, email-cpp).

Important provenance note. The owner table I was given describes the earlier lane run (`wt/lfix-fix01` @ `6d4bcdcf`). While I was reviewing, the lane regenerated every bundle in `scratchpad/lfix/out` (19:06 to 19:09 PST, code `e576d7ce`, registry now 44). I took a copy of my 14 regenerated bundles (`scratchpad/acccorr2/snap2`, byte-identical to `lfix/out` when I finished) and reviewed that copy; the first-pass results on the older run were identical for 13 of 14 repos. Only difference: Email-Cpp, listed in the table as `no_detector_fired`, is now redrawn (1 edit).

How each step was done (all repos):
- (a) Replay confinement: replayed only the enumerated edits from `corrections.json` onto the live README (fresh `git clone --depth 1` at the live head; `README.original.md` equals the live blob; head equals `manifest.revision` for all 14, `git ls-remote` re-checked at the end, no drift). The replay equals `README.md` byte for byte in 13 of 13 non-empty bundles; stripping the edit spans from both sides leaves equal text; `README.patch` applies with `git apply` (autocrlf off) and yields the corrected README; manifest hashes verify; no CRLF. Cells-Python has an empty patch.
- (b) Edit claims verified against clone, registry and manifest: Maven Central (3D-Java 26.5.0, Cells-Java 26.7.0, latest = release, pom 200), NuGet nuspec of Aspose.Cells.FOSS 26.9.0 and SkiaSharp 2.88.8, csproj/CMake/go.mod facts, CI workflow commands, `python -m build` run in a throw-away venv, crates.io 404 for the Rust package, GitHub Releases for Cells-Python.
- (c) Diagrams: rendered before and after with the lane's `measure.mjs` and its pinned mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge, native plus five stress fonts; viewed the PNGs (all 13 changed diagrams plus before images for 3D-Java, Rust, Email-Cpp). Label/edge equality checked by parsing both Mermaid bodies. Rendered text of all 193 node and cluster labels equals the source text (no truncation); reading order c1..cN is preserved in every diagram; 0 clipped in 5 fonts x 4 releases for every diagram except the Rust entity finding.
- (d) Markdown render (markdown-it + html5lib), heading anchors against Navigation, relative links against the clone, duplicate H2, unclosed `<details>`, mech.py (protocol Appendix A) before versus after (normalised for line shifts), narration scan of all inserted prose.

## Verdicts

| # | Repo | Verdict | minor/major | Why |
|---|---|---|---|---|
| 1 | 3D-.NET | PUSHABLE (diagram only) | none for the patch | Faithful redraw, confined. Inherited MAJOR defect NOT fixed: diagram still claims U3D/RVM/AMF/HTML5, which `IOService.cs` L56-88 does not support (dispatch is OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS). Owner may prefer to hold |
| 2 | 3D-Java | FIX_REQUIRED | MINOR | Diagram OK. `mvn dependency:get` block repeats coordinates already shown three ways (true: Central 26.5.0); `mvn package` repeats `mvn clean package` + `mvn test` (L616-617) and is appended after `</details>`. Drop edits 2 and 3 |
| 3 | 3D-Python | FIX_REQUIRED | MINOR | Diagram OK. `python -m build` is CI-backed but fails on a clean venv (`No module named build`, reproduced); needs `pip install build` or drop |
| 4 | 3D-TypeScript | PUSHABLE | none | Diagram only, confined, clean |
| 5 | BarCode-Python | PUSHABLE | none | Diagram only, confined, clean |
| 6 | Cells-.NET | FIX_REQUIRED | MINOR | Navigation, diagram, Dependencies (SkiaSharp 2.88.8, TFMs) all verified. Dev edit repeats the existing `dotnet build ...csproj` (L511) and sits after `</details>`; drop it. Advisory: "pure managed code" sentence next to a SkiaSharp native dependency |
| 7 | Cells-Cpp | PUSHABLE | none (advisories) | Navigation fixed; CMake 3.16, C++17, no third-party deps verified. Advisory: GoogleTest 1.14.0 omitted from Dependencies; "C++ `17`" wording |
| 8 | Cells-Go | PUSHABLE | none | Diagram + second H1 + `</details>`: all verified; License/Constraints/Detailed Documentation were hidden inside the unclosed details, now top level |
| 9 | Cells-Java | FIX_REQUIRED | MINOR | Same pattern as 3D-Java: redundant `mvn dependency:get` (true: Central 26.7.0) and `mvn package` (README already has `mvn test/compile/clean package`). Drop edits 2 and 3 |
| 10 | Cells-Python | DO_NOT_PUSH (empty patch) | none | Nothing to push. Live lacks At a Glance and Navigation, and has a dead `RELEASE_NOTES.md` link (GitHub Releases exist); regeneration-lane work |
| 11 | Cells-Rust | FIX_REQUIRED | MINOR | Diagram label `Vec<u8>` written as `Vec#lt;u8#gt;`: shows `Vec<u8>` on mermaid 11.17.2/12.1.0 but literal `Vec&lt;u8&gt;` on 11.4.1 and 11.12.0 (rendered). Use plain wording |
| 12 | Cells-TypeScript | PUSHABLE | none | Diagram only, confined, clean |
| 13 | Email-.Net | PUSHABLE | none | Diagram only, confined, clean |
| 14 | Email-Cpp | PUSHABLE (owner ack) | none | Diagram only. Redraw takes visible lines from 299 to 303 (BC-07 budget 300), recorded as `allowed` under OD-06/R7 (both rulings found in DECISION_LOG L5867-5868). Owner must accept the allowance |

Tally: 8 PUSHABLE (3D-TS, BarCode, Cells-Cpp, Cells-Go, Cells-TS, Email-.Net, plus 3D-.NET with its caveat and Email-Cpp with owner acknowledgement), 5 FIX_REQUIRED (3D-Java, 3D-Python, Cells-.NET, Cells-Java, Cells-Rust; all MINOR), 1 empty (Cells-Python), 0 DO_NOT_PUSH for cause.

## Universal detector and generator defects (lane-wide, not one repo)

1. add_dev_commands and add_install_forms are not redundancy-aware: they compare the exact fact string and fence language, not equivalent content already in the section. Hits in my set: 3D-Java (`mvn package` vs existing `mvn clean package`), Cells-Java (`mvn package` vs four Maven commands), Cells-.NET (sln build vs existing csproj build), 3D-Java and Cells-Java install (`mvn dependency:get` vs XML and Gradle snippets with the same coordinates). They also append after the last `</details>` or release paragraph, detached from the commands. This is the same class as the earlier review's "no redundancy gate" (Cells-Python) and likely recurs in the other bundles (the owner table lists the same detectors for JMAP, Imaging, Slides, PSD, Note, PDF, Words, Font).
2. Install preconditions are dropped: `python -m build` is emitted without `pip install build` (3D-Python); CI-derived commands need their setup line.
3. Mermaid entity encoding is not portable: `#lt;`/`#gt;` (and the numeric `#60;`) render as literal `&lt;`/`&gt;` text on mermaid 11.4.1 and 11.12.0 with htmlLabels off. The lane's render gate measured only the default package; a literal-entity scan across `PACKAGES` is needed. A grep of all 43 bundles shows Cells-Rust is the only one that contains an entity today.
4. The redraw is real-render verified only on local Chrome/Edge with local mermaid releases; I could not verify what github.com's bundled Mermaid release does with `%%{init}%%`, `htmlLabels:false`, `<br/>` and `~~~` (all four local releases agree on layout, so the risk is low but unmeasured).
5. Detector blind spot, confirmed again: 3D-.NET's verified-false format labels survive in the redrawn diagram (the redraw touches those exact lines); a registered-format fact kind is still missing.
6. Diagram cosmetics: capability columns are laid out on shared rows with ~75 css px gaps (rankSpacing 26 is not what drives it) and columns are top-misaligned; large capability lists (Cells-Java, 15) give a tall diagram (1133x1269). Not a defect against the owner's standard (no clipping, horizontal), only wasted height.
7. Bundles are not immutable while reviewers read them: `lfix/out` was rewritten under me (one directory was empty for a minute). A review should be given a sealed copy plus its sha256s (the manifest has them, which is what let me detect and pin the regenerated run).
8. Owner table staleness: the table row for Email-Cpp ("no_detector_fired") no longer matches the regenerated run; Cells-Java and 3D-Java rows ("medium: a toolchain-standard command no CI step or script names") understate that the insertions are duplicates.

## Could not verify
- Hosted rendering on github.com (see item 4).
- Builds: `mvn package` (3D-Java, Cells-Java) and `dotnet build Aspose.Cells_FOSS.sln` (Cells-.NET) were not run (they are duplicates; verdicts do not depend on them). `python -m build` was run (3D-Python).
- The lane's determinism/idempotence claim (re-run to identical bytes): not re-run by me; the two lane batches I observed produced identical edits for 13 of 14 repos.
