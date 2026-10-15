authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-set3: independent review of correction bundles for registry entries 30-43 (branch wt/lfix-fix01)

Reviewer: independent (Sonnet 5.5), read-only. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. For each of the 14 repositories: fresh `git clone --depth 1` at the live head (all 14 heads equal the bundles' `source_revision`, no drift); own replay of `corrections.json` over the live blob; `git apply README.patch` onto the live blob; own regex parse of the before/after Mermaid bodies (labels, titles, edges, per-group order); own render of the bundle's own `README.original.md` / `README.md` fences (not the lane's PNGs, which predate the final bundles) with the lane's pinned mermaid package and headless Edge, viewed as PNG, and repeated under mermaid 11.4.1 / 11.12.0 / 11.17.2 / 12.1.0 with five stress fonts; `mech.py` (protocol Appendix A, with link GETs) on live and corrected files; registry GETs (Maven Central, NuGet, PyPI); build runs where a toolchain exists (`dotnet build` of PSD-.NET and PDF-.NET solutions, `dotnet test` of PSD-.NET). Per-repo records: `acc-corr2-<slug>.md` in this directory. Evidence files: `scratchpad/acc2/` (clones, png, mmd, mech, logs, `frozen/` bundle copies).

Note on bundle stability: the lane regenerated entries 30-32 (and began 33) at 19:30-19:37 while I was reviewing. For 30-32 the new README.md has the same sha256 as the one reviewed (only `validation_delta.json` changed: BC-07 now `resolved`, no R7 allowance). The `lfix/out` directory of entry 33 (PDF-Java) was empty at the end of my review; I reviewed its 18:45 bundle (corrected sha256 prefix 14ed921dd613). Entries 34-43 were still the 18:4x-18:52 bundles when frozen.

## 1. Verdicts

| # | Repo | Edits | Verdict | minor/major | Why |
|---|---|---|---|---|---|
| 30 | PDF-Python | diagram | PUSHABLE | none | label/edge/order-identical redraw; horizontal; 0/5 fonts clipped in 4 mermaid releases |
| 31 | PDF-.NET | add_dev_commands | DO_NOT_PUSH | MINOR | sole edit duplicates the section's own `dotnet test` block and Installation's `dotnet build`; commands work (build succeeded) but nothing of value remains; no PR |
| 32 | PDF-Cpp | diagram, add_dev_commands | FIX_REQUIRED | MAJOR (detector) | diagram good; the command pair is stitched from release.yml's Debug build and the package-test `ctest --test-dir build-pkgtest`, a directory that does not exist on a clean clone; sentence leaks the matrix key ("across os (...)") |
| 33 | PDF-Java | 2x version | PUSHABLE | MINOR | 26.6.0 -> 26.9.0 verified (Maven Central latest/release 26.9.0, pom 200, pom.xml 26.9.0); At a Glance still live vertical diagram, clipped 5/5 (BC-07 budget), owner ruling pending |
| 34 | PDF-TypeScript | diagram | PUSHABLE | none | identical labels/edges/order; horizontal; 0/5 clipped |
| 35 | PSD-.NET | diagram, add_dev_commands | FIX_REQUIRED | MINOR | diagram good; added `dotnet build/test sln` is TRUE (built, 77 tests pass) but duplicates the live "Run the test suite" block; drop that hunk |
| 36 | PSD-Python | diagram | PUSHABLE | none | clean |
| 37 | Slides-.NET | diagram, add_doc_links | FIX_REQUIRED | MAJOR (detector) | diagram good; `docs/` holds only banner.png, nuget icon and nuget README: "documentation kept in this repository" is false; bullet lands after the section's `---` rule; section already has a Documentation entry |
| 38 | Slides-Cpp | diagram, add_doc_links, add_dev_commands | FIX_REQUIRED | MAJOR (detector) | diagram good; same false `docs/` bullet; `cmake --build build-asan` / `ctest --test-dir build-asan` omit the sanitizer configure step and fail on a clean clone; live already has the full route |
| 39 | Slides-Java | diagram, add_dev_commands | FIX_REQUIRED | MINOR | diagram good; added `clean package -DskipTests` + `mvn test` duplicates and contradicts the live "that one command" (`mvn verify -Dgpg.skip=true`) |
| 40 | Slides-Python | diagram | PUSHABLE | none | clean; the diagram's inherited "74 chart types" and "24 flavor dialects" re-verified true |
| 41 | TeX-Python | diagram | PUSHABLE | none | patch clean; owner may hold on the BLOCKED_EXTERNAL policy: 35 of 45 source files do not parse (re-confirmed) |
| 42 | Words-.NET | badge, diagram, add_dev_commands | FIX_REQUIRED | MINOR | badge verified (NuGet 26.2.0, 26.3.0) and diagram good; added `dotnet test Aspose.Words.sln` duplicates the two commands directly above it and runs a wider suite than documented |
| 43 | Words-Python | diagram | PUSHABLE | none | clean |

Totals: PUSHABLE 7 (30, 33, 34, 36, 40, 41, 43), FIX_REQUIRED 6 (32, 35, 37, 38, 39, 42), DO_NOT_PUSH 1 (31). In every FIX_REQUIRED row the diagram/badge hunks are good: dropping the named non-diagram hunk by hand leaves a pushable patch. Operationally that is a MINOR repair (the "MAJOR" rows are MAJOR because the detector, not the repository, must change before a reseal stops reproducing the defect).

Confinement (all 14): `README.original.md` equals the live blob; replaying only the enumerated edits reproduces the corrected README byte for byte; `README.patch` applies and reproduces it byte for byte; no maintainer text altered or lost; LF only; no duplicate H1, no new duplicate H2, no unclosed fence, Navigation anchors all resolve; `mech.py` shows no new forbidden wording, dangling lead-in or link failure; validation_delta `introduced: []` in all 14.

Diagram result (12 redrawn diagrams; PDF-.NET has an image instead, PDF-Java was not redrawn): all 12 redraws are horizontal with the three mother blocks left to right, capabilities split into one or two columns, boxes sized by text, no clipped text visible in the PNGs, 0 of 5 fonts clipped in each of four mermaid releases (live: vertical, clipped in 3-5 of 5 fonts). Labels, subgraph titles, edges and per-group order are identical to live in all 12 (own parse). PDF-Java stays vertical, clipped in 5 of 5 fonts (4 of 5 under 12.1.0).

## 2. Universal defects (detector or generator, not one repo)

1. **add_dev_commands has no redundancy gate.** Its rationale ("'Development and Testing' lacks the clone's verified build and test information") is false in all 6 of its edits in this set (PDF-.NET, PDF-Cpp, PSD-.NET, Slides-Cpp, Slides-Java, Words-.NET): every one of those sections already carries a fenced build/test command. Result: 4 duplicates (PDF-.NET, PSD-.NET, Slides-Java, Words-.NET) and 2 non-functional blocks (PDF-Cpp, Slides-Cpp). A covered section needs a disposition, not an insertion (same class as the "no redundancy gate" finding of the first correction review).
2. **add_dev_commands assembles commands from unrelated CI steps.** PDF-Cpp takes a Debug build step and a package-consumer ctest from release.yml; Slides-Cpp takes the AddressSanitizer job's build/test lines without its configure line; Slides-Java takes the reproducibility step. Required: one job's configure -> build -> test chain whose directories exist, and the primary (non-sanitizer, non-release) job. "SUPPORTED" on each fact id shows the fact exists, not that the sequence runs.
3. **add_doc_links treats any `docs/` directory as documentation.** In Slides-.NET and Slides-Cpp it holds only `media/banner-readme.png`, `nuget/icon.png` and `nuget/README.md` (package assets). It must require markdown documentation content beyond media/package assets, must insert inside the existing list (Slides-.NET landed after the closing `---`), and must skip when the section already has a Documentation entry (both do).
4. **Machine-phrased prose from CI facts**: "runs across os (ubuntu-latest, windows-latest)" leaks the matrix key and drops the real toolchain matrix (gcc-13, clang-16, MSVC).
5. **The validators cannot judge these edits.** `introduced: []` and "zero regressions" hold for all 14, including the 2 broken command blocks and the 2 false `docs/` bullets. The bundle statement of risk ("a toolchain-standard command no CI step or script names") mislabels PDF-Cpp and Slides-Cpp, whose commands are named by CI steps, from the wrong job. A command-fitness gate (exists, ordered, directories created earlier in the block or in the live README) is missing.
6. **Diagram detector is sound** on this set (12 of 12 redraws verified); the one open item is PDF-Java, left vertical because of BC-07's visible-line budget (299 of 300). The lane's 19:30 regeneration shows BC-07 `resolved` instead of `allowed` for entries 30-32, so the owner ruling may already be implemented; PDF-Java should be redrawn once its bundle is back.
7. `stale_phrase` is reported but not edited: Words-.NET still says "The NuGet package and new formats are landing soon" next to the newly added NuGet badge and "Install from NuGet". Minor, not introduced.

## 3. What I could not verify
- Rendering on github.com itself (headless Edge, four pinned mermaid releases, five stress fonts only).
- `cmake`/`ctest` and `mvn` are not installed here: the C++ and Java findings rest on the workflows and CMake files, not on a run; `dotnet test` of the PDF-.NET and Words-.NET solutions was not run.
- PDF-Java regenerated bundle (directory empty when I finished).
