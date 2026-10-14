authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-summary: independent review of the live-first correction lane (branch wt/lfix-fix01)

Reviewer: independent (Sonnet 5.5), read-only. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to patches: fresh `git clone --depth 1` at the live head (all six heads equal the bundles' `source_revision`, no drift), registry GETs (PyPI, NuGet, Maven Central, Go proxy, crates.io), own replay of `corrections.json` edits over `README.original.md`, own difflib, own markdown-it+html5lib render of before/after, `mech.py` (protocol Appendix A) on live and corrected files, throw-away venvs for install commands. Per-repo records: `acc-corr-cells-net.md`, `acc-corr-cells-cpp.md`, `acc-corr-cells-python.md`, `acc-corr-font-python.md`, `acc-corr-cells-go.md`, `acc-corr-pdf-java.md` (this directory).

## 1. Verdicts

| Repo | Edit | Verdict | minor/major | Why |
|---|---|---|---|---|
| Cells-.NET | + Dependencies | FIX_REQUIRED | MINOR | SkiaSharp 2.88.8 correct and complete (csproj, published nuspec). Navigation not updated (introduced); `TargetFramework` should be `TargetFrameworks`, net8.0 dropped (fact truncated to first TFM); intro "pure managed code" now sits next to a SkiaSharp native dependency |
| Cells-Cpp | + Dependencies | FIX_REQUIRED | MINOR | "no third-party deps", C++17 verified (std headers only). Navigation not updated; sentence is a machine evidence citation; omits CMake 3.16 (fact exists) and GoogleTest 1.14.0 (README itself mentions it) |
| Cells-Python | + Dependencies | FIX_REQUIRED (low value) | MINOR | Versions match pyproject and PyPI. Duplicates Installation L35-36 verbatim; omits the optional `skia-python` the README and requirements.txt document; cites `python_requires` where the key is `requires-python` |
| Font-Python | + Installation, + Dependencies | FIX_REQUIRED | MAJOR | Facts verified (aspose-font 404 on PyPI; `pip install .`, `import aspose_font`, CLI work in a clean venv; deps/extras correct). But: "verified against this revision" narration; and L539 `pip install "aspose-font[mcp]"` is left in place, now contradicting the new "not published" text (and failing today). Needs a new detector or hand edit |
| Cells-Go | second H1 -> H2; + `</details>` | PUSHABLE | none | Exactly two hunks, both real defects. Render check: License, Constraints, Detailed Documentation were inside the collapsed details before, top level after. Optional: sentence-as-heading remains |
| PDF-Java | 26.6.0 -> 26.9.0 (2 lines) | PUSHABLE | none | Maven Central latest/release 26.9.0, pom+jar 200, pom.xml head = 26.9.0. 26.6.0 is still published, so call it a stale pin |

Confinement (all six): `README.original.md` equals the live blob; replaying only the enumerated edits reproduces the corrected README byte for byte; difflib shows no other change; no maintainer text altered or lost; no mixed line endings; no duplicate headings; no unclosed fence; inserted text carries no links. The lane's `confinement.verified` is true in every case.

## 2. Universal detector/generator defects (apply to the lane, not one repo)
1. Section insertion does not update `## Navigation` (Cells-.NET, Cells-Cpp; every sibling README that has Navigation lists Dependencies).
2. Evidence-citation phrasing leaks into public prose: "verified against this revision" (Font), "no dependency is on the library target's public link interface" (Cpp), "in `pyproject.toml`, no `project.dependencies` is declared". Add a text gate on inserted prose (no verification/revision/evidence narration; protocol 5.1).
3. Wrong key quoted: `python_requires` for pyproject's `requires-python` (Cells-Python, Font); `TargetFramework` for `TargetFrameworks` (Cells-.NET).
4. Extractor gaps surface as incomplete sections: `package:target_framework` keeps only the first TFM; no dev-dependency fact from the C++ Tests CMake (GoogleTest `FetchContent`); `package:cmake_minimum` exists but is unused; README-documented optional dependencies (skia-python) are not facts.
5. No cross-reference reconciliation after insertion: an inserted "not published" statement must be checked against every `pip/npm/dotnet install <name>` already in the README (Font L539). Needs an `unpublished_install_command` detector (registry 404 -> rewrite or block).
6. No redundancy gate: Cells-Python's Dependencies repeats what Installation already says; a covered section should get a disposition, not an insertion.
7. `broken_link` false positive: `../../issues` (Words-.NET) resolves on GitHub to the repository issues page; the lane reports it as a dead link.
8. No build/test-command detector (the lane acknowledges it): see Page-Python below.
9. Unreported contradictions that the new sections expose are not surfaced in `unapplied_findings` (Font L539, Cells-.NET "pure managed code").

## 3. Grading the claim "29 nothing to correct"

Grade: overstated, not dishonest. The report discloses its reported-not-edited findings and scopes the claim to "the closed detector set can decide", but the headline and several per-repo lines ("Result: nothing to correct; no PR would be opened (the live README already matches the verified facts)", incl. Words-Python with a 146 vs 198 type-count finding) read as "these READMEs are fine".

Counts from the lane's own table: of the 29 `no_corrections` rows only 8 have zero findings (3D-Java, BarCode-Python, Cells-Java, Cells-Rust, Cells-TS, Email-.Net, PSD-.NET, Slides-Java); 21 carry reported findings, 16 of them failing README examples.

Spot check of 6 of the 29 (live heads, own clones in `scratchpad/acccorr/spot/`):

| Repo (lane row) | What I found the closed detectors cannot see | Evidence | Clean? |
|---|---|---|---|
| 3D-.NET (row 1; lane reported only a failing example) | Verified-false capability claims: README L83-84 / At a Glance / Key Capabilities claim read+write of U3D, RVM, AMF, HTML5 "with full round-trip fidelity"; L382 and L598 say "core RVM import/export works". Dispatch has only OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS (3DS is not mentioned). L592 says `NurbsSurface.ToMesh` throws: it returns a placeholder z=0 grid mesh. L576 says `RenderFactory` throws: its virtual methods return null | `src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/IOService.cs` L56-90 (`CreateImporter/CreateExporter` switch, default `NotSupportedException`); `Entities/NurbsSurface.cs` L45-90; `Render/RenderFactory.cs` L1-50 | NO: major |
| Cells-Rust (row 11; zero findings) | Stale sentence L105-106 "Once the repository is live at its real GitHub location": it is live (the cloned URL is the one in the snippet). "Not yet published to crates.io" is true (crates.io 404 for `aspose-cells-foss-rust` and `aspose-cells-foss`); "0 tests" is true (no `#[test]`) | `curl crates.io/api/v1/crates/...` 404; clone | minor |
| Page-Python (row 21; lane saw one ImportError example) | Documented source build fails on a clean clone: `python package.py build` and `make sync` read `local/Version.txt` (README L102), but `local/` is git-ignored and absent. Reproduced: `pip wheel ./clone` -> `FileNotFoundError: ...\local\Version.txt` from `setup.py` L35. README never says to create it. `pip install aspose-page-foss` is fine (PyPI 26.9.0) | `.gitignore` (`local/`), `setup.py` L35, `package.py` L45; own `pip wheel` run | NO: major (a documented command fails) |
| Slides-Java (row 32; zero findings) | Nothing: README pins 26.7.0 (Maven Central latest, `26.7.0` pom 200), says 26.8.0 is unreleased (`26.8.0` pom 404; pom.xml is 26.8.0), JDK 21 matches `maven.compiler.release` | maven-metadata.xml | YES |
| TeX-Python (row 34; 9 reported IndentationError examples) | The library cannot be imported: 35 of 45 `src/**/*.py` fail `ast.parse` (flattened indentation, e.g. `_input/catcode.py` L65-66; present since Release 26.5, HEAD commit only touches README). README says "install from source ... `pip install -e .`" (installs, then `import aspose_tex` raises IndentationError) and the HEAD commit message claims "verified examples". The failing-example findings are the symptom; this is an upstream code defect no README PR can fix | `python -I` AST scan of the clone; `gh api repos/.../commits/181015d2` (1 file: README.md); catcode.py at 2f4bfab3 identical | NO: blocker, should be a typed terminal state plus an issue draft |
| Words-.NET (row 35; flagged `../../issues`) | L952 "The NuGet package and new formats are landing soon" is stale and contradicts L89 "Install from NuGet": Aspose.Words.FOSS 26.2.0 and 26.3.0 are published (`api.nuget.org/v3-flatcontainer/aspose.words.foss/index.json`). The lane's dead-link finding for `../../issues` is a false positive. `System.Text.Encoding.CodePages 7.0.0` is listed as required but is not in the published nuspec dependencies (could be merged by ILRepack: unverified) | nuspec of 26.3.0 | minor |

5 of 6 sampled "nothing to correct" READMEs have a verified defect (2 major: 3D-.NET false capabilities, Page-Python failing documented build; 1 upstream blocker: TeX; 2 minor) that the detectors cannot see; 1 of 6 is clean. Extrapolating is unsafe with n=6, but the "29" is clearly an upper bound on READMEs that are accurate and complete, not a count of them.

## 4. What an "improvement over live" candidate should add for the spot-checked six
- 3D-.NET: rewrite the format claims to the `IOService` dispatch table (add 3DS; demote U3D/RVM/AMF/HTML5 to "options types only, no reader/writer"), fix the diagram nodes, RvmFormat row and Scope bullets, correct the `ToMesh` and `RenderFactory` statements. Needs a new fact kind: registered importer/exporter formats (the pipeline has none, which is why a regenerated candidate repeats the false claims).
- Cells-Rust: replace the "once the repository is live" sentence; keep everything else.
- Page-Python: add the `local/Version.txt` precondition (or the source route that works) to Installation and Development; needs a build/test-command fact verified on a clean clone.
- Slides-Java: leave untouched (no PR); this is the model for "accurate, do not regenerate".
- TeX-Python: no README candidate; record BLOCKED_EXTERNAL (upstream source unparsable) with the resume predicate "import aspose_tex succeeds on a fresh clone"; draft the upstream issue as text.
- Words-.NET: fix the stale "landing soon" sentence; keep the maintainers' voice (story, star request) which a template fill would destroy; drop the `../../issues` finding; verify the CodePages dependency.

## 5. Other honesty notes on the lane report
- Accurate: edit confinement, determinism/idempotence flags, the self-disclosed demotion of public-type counts and the stale-pin wording for PDF-Java, "zero validation regressions" (I read Font's `validation_delta.json`: introduced [], BC-02 resolved).
- Understated: it presents the six corrected repos as ready ("worth a PR") without noting items 1, 2 and 5 of section 2; two of the four Dependencies/Installation patches (Cells-.NET, Cells-Cpp) are not PR-ready as generated, Font is not safe, Cells-Python is redundant.
- Not re-run by me (no toolchain or out of scope): C++/Go/Java/.NET example builds, Linux behaviour of SkiaSharp PDF export, the lane's `claim_public_types` recounts.
