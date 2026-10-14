authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-set2: independent review of the live-first correction bundles, registry entries 15-29

Reviewer: independent (Sonnet 5.5), read-only. Method: acceptance protocol v1.1 (`git show wt/lacc-acc01:evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/acceptance-protocol.md`) adapted to a patch. Per-repo records: `acc-corr2-<name>.md` in this directory (email-python, jmap-net, jmap-cpp, jmap-go, jmap-java, jmap-nodejs, jmap-python, jmap-rust, jmap-typescript, font-python, gis-net, html-python, imaging-net, note-python, page-python, pdf-go). Work files: `scratchpad/acc2s2/` (bundle snapshots, fresh clones, `verify.py`, `render.py`, PNGs in `png/`).

## Provenance and scope

- The owner table (43 entries, lane commit `6d4bcdcf`) is superseded: the lane's registry now holds 44 entries (code `e576d7ce`; `Aspose.JMAP-FOSS-for-Node.js` was added between JMAP-Java and JMAP-Python). Under the current `data/registry.json` order, entries 15-29 are Email-Python, JMAP .NET/Cpp/Go/Java/Node.js/Python/Rust/TypeScript, Font, GIS, HTML, Imaging, Note, Page. `Aspose-PDF-FOSS-for-Go` (owner-table #29) is now #30; I reviewed it as well so that nothing in either numbering is left uncovered. 16 records.
- The lane regenerated every bundle in `scratchpad/lfix/out` while I reviewed (19:07-19:35 PST; Font, Page and GIS directories were briefly absent). I took snapshot copies; at the end all 15 README-bearing bundles (and the GIS `status.json`) matched `lfix/out` byte for byte (`cmp`), and patch sizes equal the owner table.
- No live drift: `git ls-remote` HEAD equals the clone HEAD equals `manifest.revision` for all 16 repositories.

## How each step was done

- (a) Replay confinement: fresh `git clone --depth 1` of every live head; `README.original.md` equals the live blob; my own offset replay of only the enumerated `corrections.json` edits reproduces `README.md` byte for byte in 15 of 15 (and `README.patch` applied with `git apply` to the live blob does too); every line-diff hunk lies inside an edit span; no CRLF; manifest hashes verify; `validation_delta` introduced = [] everywhere.
- (b) Edit claims against the clone and registries: `.github/workflows/*.yml` of every repo, Makefile, pom.xml, package.json, pyproject, sln; PyPI/NuGet/npm/crates.io/Maven/Go proxy GETs; GitHub releases and Actions runs (GET); `dotnet build` of the Imaging sln in a throw-away copy; `python -m build` in a clean venv (fails; passes after `pip install build`).
- (c) Diagrams: rendered before and after with the lane's `measure.mjs` in Edge 155 for all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0), native plus five stress fonts; viewed the PNGs (10 corrected diagrams: Email-Python, PDF-Go, HTML, Imaging, Note, Page and JMAP .NET/Cpp/Java/Node.js, plus the before images for Email-Python, PDF-Go, JMAP-Cpp; the other four JMAP diagrams have the same 9-node shape and identical measured results). Own Mermaid parser: node ids, normalised labels (`<br/>` as a space), subgraph titles and edges equal before/after in 14 of 14 changed diagrams. Result: 14 of 14 horizontal (Starting Points, product, Core Capabilities, Outputs left to right), 0 foreignObject, 0 spills, 0 clipped in 5 fonts x 4 releases; boxes sized by their text.
- (d) markdown-it + html5lib render: heading and `<details>` structure identical before/after (Font gains one H2); no duplicate section; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem. No internal narration in any inserted prose.

## Verdicts

| # | Repo | Verdict | minor/major | Why |
|---|---|---|---|---|
| 15 | Email-Python | FIX_REQUIRED | MINOR | Diagram OK. Dev sentence `ci workflow runs across python-version (3.10..3.13)` is true but repeats live L402-403 ("CI runs the test suite on Python 3.10 through 3.13") and quotes a raw matrix key. Drop hunk 2 |
| 16 | JMAP-.NET | FIX_REQUIRED | MINOR (PR) | Diagram OK. `Releases run through the [ci workflow]` is FALSE: ci.yml = secret-scan + test only, no release/publish step, nothing published (registries 404). Drop hunk 2 |
| 17 | JMAP-Cpp | FIX_REQUIRED | MINOR (PR) | Same false release sentence; diagram OK |
| 18 | JMAP-Go | FIX_REQUIRED | MINOR (PR) | Same false release sentence; diagram OK |
| 19 | JMAP-Java | FIX_REQUIRED | MINOR (PR) | Same false sentence; plus redundant `mvn package` (live already has `mvn compile`/`mvn test`) |
| 20 | JMAP-Node.js (new entry) | FIX_REQUIRED | MINOR (PR) | Same false sentence; diagram OK |
| 21 | JMAP-Python | FIX_REQUIRED | MINOR (PR) | Same false sentence; plus duplicate `python -m pytest -q` (live has `pytest`) |
| 22 | JMAP-Rust | FIX_REQUIRED | MINOR (PR) | Same false release sentence; diagram OK |
| 23 | JMAP-TypeScript | FIX_REQUIRED | MINOR (PR) | Same false sentence; plus redundant `npm run build` (`npm test` runs tsc) |
| 24 | Font-Python | FIX_REQUIRED | MINOR | Documentation & Resources (CHANGELOG.md, SECURITY.md exist and match) is PUSHABLE; `make build`/`make test` block duplicates the uv commands four lines above. Drop hunk 2 |
| 25 | GIS-.NET | DO_NOT_PUSH (nothing to push) | none | No README at the live head (GitHub API 404, tree has none): lane status `no_live_readme` is correct. Real library (114 files), so a README must come from the regeneration lane |
| 26 | HTML-Python | PUSHABLE | none | Diagram only, confined, clean (BC-07 +6 recorded `allowed`, R7) |
| 27 | Imaging-.NET | FIX_REQUIRED | MINOR (low) | Diagram OK. CI-matrix sentence true; `dotnet build sln` verified, but the block repeats the live `dotnet test` and sits after the contributor paragraph; raw `os (...)` wording |
| 28 | Note-Python | FIX_REQUIRED | MINOR | Diagram OK. `python -m build` fails on a clean venv (`No module named build`, reproduced); `build` is a release-only extra per the README; add `pip install build` or drop |
| 29 | Page-Python | PUSHABLE | none | Diagram only, confined, clean. Inherited (not introduced): documented source build needs git-ignored `local/Version.txt` |
| 30 (table #29) | PDF-Go | FIX_REQUIRED | MINOR (PR) | Diagram OK. OS-matrix sentence true; `Releases run through the [lint workflow]` FALSE (lint.yml = golangci-lint; releases are manual). Delete that sentence |

Tally: 2 PUSHABLE as generated (HTML, Page), 13 FIX_REQUIRED (all MINOR for the PR: one hunk to drop; 9 of them carry a verified FALSE introduced sentence), 1 nothing to push (GIS). Every FIX_REQUIRED repo is PUSHABLE as a diagram-only patch once its `add_dev_commands` hunk is removed (Font: keep the Documentation & Resources hunk).

## Universal defects (lane-wide)

1. FALSE release claim generated from nothing (MAJOR for the lane, 9 of 16 here): `renderer.py` L704-708, `_development_sentences`: `chosen = release[0] if release else workflows[0]` then `Releases run through the [<stem> workflow]`. When no workflow name contains publish/release it falls back to the first workflow and asserts a release path. The fact `build_test_asset:ci` only holds the directory `.github/workflows/`; no validator checks the sentence. Hits: 8 JMAP (ci.yml has no release job, nothing published) and PDF-Go (lint.yml). Remove the fallback (emit only when a workflow actually has a tag/release trigger or a publish step) and grep all 43 bundles for `Releases run through` and re-check each linked workflow.
2. Redundancy gate compares exact command lines only (`_placed_command_lines`), not equivalent commands or prose: Email-Python (CI matrix already stated in prose), Font (`make` vs `uv run`), Imaging (`dotnet test` vs sln), JMAP Java/Python/TypeScript. Same class as set 1 item 1.
3. A CI-derived command is emitted without its setup line: Note `python -m build` (no `pip install build`); same as set 1's 3D-Python.
4. Raw matrix keys in public prose (`runs across python-version (...)`, `runs across os (...)`): render as human wording (`on Python 3.10 to 3.13`, `on Ubuntu and Windows`).
5. Inserted blocks are appended at the end of the section, detached from related text (after `</details>` in Note, after the contributor paragraph in Imaging).
6. R7 allowance is visible in 4 of my bundles: BC-07 failures rise under the old rule (HTML 19 to 25, Note 13 to 18, Page 11 to 18, PDF-Go 23 to 29) because it counts `<br/>`-joined words as over-long tokens and still names `flowchart TD`; owner should confirm the allowance (the contract-based judge passes). Migration of BC-07 to `readme_diagram.contract` remains open.
7. Bundles are not immutable while reviewed (`lfix/out` rewritten during review; one directory empty for minutes); hand reviewers a sealed copy with sha256s. The owner table also no longer matches the registry (44 entries, Node.js JMAP missing from it).
8. Rendered size: natural widths are 1450-1830 px, so on an 830 px README column the corrected diagrams scale to about 0.45-0.57; for Imaging (0.57 vs live 0.65), Note (0.50 vs 0.52) and Page (0.45 vs 0.52) the text is not larger than the live diagram's, only unclipped and much shorter. Not a defect against the standard; PDF-Go is large (24 boxes, 1685 x 1641).
9. Detector blind spots confirmed again: Page-Python's documented build fails on a clean clone and Font-Python's `pip install "aspose-font[mcp]"` contradicts PyPI 404 (both inherited, reported or invisible to the closed detector set); GIS has real source but no README.

## Could not verify

- Hosted github.com Mermaid rendering of `%%{init}%%`, `htmlLabels: false`, `<br/>` and `~~~` (local Edge with four mermaid releases agree; GitHub's bundled release unmeasured).
- `dotnet test` of the Imaging sln (no net9.0 runtime here), `make build`/`make test` (Font), Java/Go/Rust/C++/TypeScript build commands (no toolchain run; verdicts do not depend on them).
- The inherited diagram claims (capability labels) were not re-verified against source; the redraw keeps them verbatim.
