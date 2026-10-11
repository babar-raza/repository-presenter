authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Upstream issue approval table, final (lane iss3b, G6-W01)

Prepared 2026-10-11 for the owner. **Nothing was filed, no comment was posted, no approval record was written, and
no repository other than this checkout was written to.** Every upstream read was a `git clone --depth 1`, a
`gh api` GET, a package-registry GET or a local build or test run; the GET token was used in-process and never
printed. The earlier table (`issue-approval-table.md`, 24 handoffs: 12 FILE, 2 HOLD, 10 DROP) is superseded by this
one; every decision in it still holds.

## 1. Result

89 candidate rows were re-verified by command at the live default-branch head today, 42 of them as upstream-defect
handoffs on record (26 before this lane, 16 added), the rest as text drafts the handoff model cannot carry.

| action | rows | of which a handoff the tool can approve and file | meaning |
|---|---|---|---|
| FILE | 39 | 30 | real, reproduced at the live head, not a duplicate, quality gate passing. Wave 1a is 1, 1b is 7, 2 is 11, 3 is 11; the other 9 have verified text but need a defect class the registry does not have |
| HOLD | 26 | 2 | real but not worth an issue yet, or waiting on a stated resume predicate |
| README-CORRECTION | 11 | 6 | the failing text is in a README the presenter's own merged pull requests wrote: the correction lane fixes it, no issue |
| DROP | 13 | 4 | disclosed upstream, already fixed, a duplicate of an issue the owner already filed, or not a defect |

Headline findings from today's re-run (they change what the owner would have approved):

1. **3D-.NET `af8da760` was too narrow and partly wrong.** The README Quick Start does not compile as written
   (`Vector3` lives in `Aspose.ThreeD.Utilities`, which the fence does not import), and the first report said it was
   "verbatim". The runtime failure is general: `Scene.Save(path, FileFormat)` throws `NotImplementedException` for 44
   of the 45 public `FileFormat` constants (only `Discreet3DS` works) while `Scene.Save(path)` writes nine formats by
   extension. The handoff text was re-drafted around that library defect; digest and re-verification refreshed.
2. **Cells-Python moved today** (three maintainer commits on 2026-10-11 ending at `952317ca` "Update Readme"; the Python
   floor went from 3.7 to 3.10 and the wheel is now 26.10.0). Drafts U14, U16, U17 still reproduce; U15 changed (one
   failing example test, not two); the licence finding still holds at the new head. The repository is being edited
   right now, so re-run `issue-readiness` before approving anything for it.
3. **PSD-.NET and PSD-Python moved on 2026-10-10** (the presenter's README pull requests #7 and #5 merged). The PSD-Python
   README is no longer a placeholder, so half of old draft U11 is obsolete. The two licence findings duplicate the
   owner's own open issues #5 and #4, so they are DROP, not FILE.
4. **PDF-Cpp "CMake configure fails" does not reproduce**: configure, build and `ctest` succeed on gcc 14.4 with CMake
   3.31.6 (1 of 1 tests pass). That wave-4 note was the presenter's own runner.
5. **The JMAP repositories have no upstream defect**: all eight READMEs say no package is published, the registries
   agree (404), and CI is green in all eight.
6. **Provenance moved four README-based drafts to README-CORRECTION**: Cells-Go formula text (`9f0a4033`),
   Cells-Rust "once the repository is live" (`1a6004af`), Cells-TS placeholder API rows (`fc186507`) and the 3D-.NET
   diagram's U3D/RVM/AMF/HTML5 labels (`042a1e5f`, `158183d2`) are all the presenter's own text
   (`raw-logs/iss3b-provenance.txt`).
7. **Disclosed upstream, so DROP**: 3D-Java jar stubs (README.md:587), Slides-Java 26.7.0 only (SECURITY.md:11),
   Slides-Python PyPI lag (README.md:134), Cells-Rust not on crates.io (README.md:105).

## 2. How it was verified

- Heads and open and closed issues: `gh api` GET for all 44 registry repositories
  (`raw-logs/iss3b-open-issues-and-heads.txt`, `iss3b-closed-issues.txt`, `iss3b-ci-runs.txt`). Fresh shallow clones
  at those heads (Page-Python and Words-.NET blobless). Every handoff's `source_revision` equals today's head except
  Imaging-.NET and PDF-TypeScript (both DROP) and Note-Python (two commits, a change and its revert: the tree is
  identical, which the filer's recheck accepts).
- Builds and tests: Docker `gcc:13/14/15`, `silkeh/clang:latest`, `ubuntu:24.04` (g++ 12/13/14, clang 18), `node:22`,
  `rust:1`, `python:3.12`; native .NET SDK 10.0.401 and Python 3.13.15 (one venv per repository). Each log's header
  names the repository, the head, the UTC time and the command; exit codes are in the log.
- Provenance of every README claim that decides FILE versus README-CORRECTION: the commit history of the file
  (`raw-logs/iss3b-provenance.txt`).
- Drafting: the 7 library, build, install and test handoffs went through `Handoff` and `issue_quality_findings`
  (`make_handoffs.py` and `revise_3dnet.py`, committed as `.txt` under `analysis/scripts/iss3b/`); the 9 licence, README and placeholder-manifest
  handoffs are the output of the defect-class detectors (`classes.detect_all` and `draft.draft_class_handoff`) run over
  today's clones. All 42 handoffs read `recheck: replayable`; 38 pass the quality gate (the 4 that fail are the
  DROP rows: jargon text or synthetic).
- Re-verification record: `evidence/upstream-defects/reverification.json` now holds 41 entries (every handoff but the
  synthetic one), each with today's time, head, recomputed digest, method and the raw log. The six README-CORRECTION
  handoffs are recorded `NOT_A_DEFECT` so that `issue-readiness` refuses to approve them.
- Not re-run: nothing on the FILE or HOLD lists. Text-only rows U33/U46/U47 were checked by registry GETs and README
  greps (they are disclosed, not builds). crates.io could not be reached from this host (TLS error), so the Rust crate
  status rests on the README's own statement.

## 3. FILE: handoffs the tool can approve and file (30)

Order matters: file wave 1a alone first, watch it, then 1b, then 2, then 3. Per repository the system files at most
3 issues a UTC day and stops at 5 open issues of its own. Severity is the lane's judgement (High: cannot be built,
installed, imported or called as documented; Medium: a documented path or the test suite fails; Low: metadata,
licence layout or documentation).


### Wave 1a: the first live filing (alone)

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| 3f1b3176 | Aspose.Cells-FOSS-for-Cpp (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.Cells FOSS for Cpp: XlsxWorkbookSerializerCommon.cpp uses std::numeric_limits without including <limits> | High | iss3b-docker-cellscpp_gcc_13.txt; iss3b-docker-cellscpp_gcc_14.txt; iss3b-docker-cellscpp_gcc_15.txt; iss3b-docker-cellscpp_silkeh_clang_latest.txt | yes: gcc 13.5/14.4/15.3 and clang 22.1.8, 12 errors | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1a |

### Wave 1b: library, build and install defects that stop use

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| af8da760 | Aspose.3D-FOSS-for-.NET (dry_run) | EXAMPLE_FAILS (library) | Aspose.3D FOSS for .NET: Scene.Save(path, FileFormat) throws NotImplementedException for 44 of 45 FileFormat constants | High | iss3b-quickstart-3D-NET.txt; iss3b-formats-probe-3D-NET.txt | yes, and wider than the first report: 44 of 45 FileFormat constants throw on Save(path, format) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| 094c4163 | Aspose.3D-FOSS-for-Python (dry_run) | EXAMPLE_FAILS (library) | Aspose.3D FOSS for Python: Scene.save() to an .obj path raises TypeError (a bytes-like object is required, not 'str') | High | iss3b-repro-3D-Python-obj.txt | yes: TypeError at ObjExporter.py:50; the README example is the presenter's but the defect is in the library | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| 7f0f3388 | Aspose.Email-FOSS-for-Cpp (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.Email FOSS for Cpp: cfb_reader::header() 'changes meaning of header', the library fails on GCC 12-15 | High | iss3b-docker-emailcpp_ubuntu24.txt; iss3b-docker-emailcpp_gcc_14.txt; iss3b-docker-emailcpp_gcc_15.txt; iss3b-docker-emailcpp_silkeh_clang_latest.txt | yes: g++ 12.4/13.3/14.2 (ubuntu 24.04), gcc 14.4, gcc 15; 9 translation units; clang 18 and 22 accept | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| cd17e99e | Aspose.GIS.FOSS-for-.Net (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.GIS.FOSS for .Net: the library project does not compile (369 build errors, 41 referenced types not declared) | High | iss3b-build-GIS-NET.txt | yes: 369 errors, 45 warnings, 41 of 57 unresolved type names declared nowhere | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| ae9f06b9 | Aspose.HTML-FOSS-for-Python (dry_run) | INSTALL_FAILS | Aspose.HTML FOSS for Python: pip install . fails, the build-backend setuptools.backends.legacy:build does not exist | High | iss3b-w3c-fixture-HTML-Python.txt | yes: pip install . raises BackendUnavailable (Cannot import 'setuptools.backends.legacy') | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| 48692986 | Aspose.Page-FOSS-for-Python (dry_run) | INSTALL_FAILS | Aspose.Page FOSS for Python: pip install . fails on a fresh clone because local/Version.txt is not in the repository | Medium | iss3b-version-txt-Page-Python.txt | yes: pip install . FileNotFoundError local/Version.txt (git-ignored) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |
| c00f9615 | Aspose.TeX-FOSS-for-Python (dry_run) | SOURCE_UNPARSEABLE | Aspose.TeX FOSS for Python: 102 of 119 .py files fail to parse (IndentationError) and 'import aspose_tex' fails | High | iss3b-ast-TeX-Python.txt | yes: 102 of 119 .py files (src/aspose_tex 35 of 45); import aspose_tex fails at _input/catcode.py:66 | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 1b |

### Wave 2: Medium and Low severity examples, tests and the repository with no licence at all

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| 49f081e6 | Aspose.3D-FOSS-for-.NET (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.3D FOSS for .NET: 53 of 183 tests fail on a clean checkout because testdata/ is not tracked | Medium | iss3b-testdata-3D-NET.txt | yes: 53 of 183 tests fail, 47 FileNotFoundException | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| 18934ab2 | Aspose.3D-FOSS-for-Python (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.3D FOSS for Python: unittest discover tests/ gives 5 errors because its fixtures are in git-ignored examples/ | Low | iss3b-unittest-3D-Python.txt | yes: Ran 123, errors=5, skipped=5 | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| cd25aa80 | Aspose.3D-FOSS-for-TypeScript (dry_run) | LICENSE_MISSING_ROOT | Aspose.3D FOSS for TypeScript: no license file at the repository root | Medium | iss3b-license-3D-TS.txt | yes: no license file anywhere; package.json declares MIT; GitHub reports license null | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| ee780fd3 | Aspose.3D-FOSS-for-TypeScript (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.3D FOSS for TypeScript: npx jest reports 4 failing tests out of 97 at the default branch head | Medium | iss3b-docker-threedts_detail.txt; iss3b-docker-threedts_jest.txt | yes: 4 of 97 fail (causes read from the jest output) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| b3df5761 | Aspose.Cells-FOSS-for-Cpp (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.Cells FOSS for Cpp: the library build uses -Werror and fails on warnings with GCC 13-15 and Clang 22 | Medium | iss3b-docker-cellscpp_gcc_13.txt; iss3b-docker-cellscpp_gcc_14.txt; iss3b-docker-cellscpp_gcc_15.txt; iss3b-docker-cellscpp_silkeh_clang_latest.txt | yes: -Werror stops 3 files on gcc 13-15 and 5 on clang 22 (trigraph in NumberFormat.cpp:30); file after 3f1b3176 (partly a policy choice) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| c04f74bf | Aspose.Cells-FOSS-for-TypeScript (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.Cells FOSS for TypeScript: the documented `npx tsc --noEmit` reports 3 type errors | Low | iss3b-docker-cellsts_tsc.txt | yes: 3 errors, exit 2 (the README's own verification command) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| 52ba0e1d | Aspose.Font-FOSS-for-Python (dry_run) | EXAMPLE_FAILS | Aspose.Font FOSS for Python: README web-optimizer example raises KeyError 'subset' (manifest lacks the keys) | Medium | iss3b-repro-Font-Python.txt | yes: KeyError 'subset' (README is the maintainers', Release 26.10.2) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| dc90b681 | Aspose.Font-FOSS-for-Python (dry_run) | EXAMPLE_FAILS | Aspose.Font FOSS for Python: README example calls VariableInstanceBuilder.build_package with unaccepted arguments | Medium | iss3b-repro-Font-Python.txt | yes: TypeError unexpected keyword argument 'instance_names' (maintainers' README) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| b1d0d16b | Aspose.HTML-FOSS-for-Python (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.HTML FOSS for Python: pytest stops at collection because tests/test_css/w3c is not in the repository | Low | iss3b-w3c-fixture-HTML-Python.txt | yes: collection error, 12296 collected, session interrupted | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| 6532670d | Aspose.Note-FOSS-for-Python (dry_run) | EXAMPLE_FAILS | Aspose.Note FOSS for Python: README Quick Start crashes because page.Title is None for pages without a title | Medium | iss3b-quickstart-Note-Python.txt | yes: AttributeError on page.Title (maintainers' README since 2026-01-12) | closed #1 'Titles are empty' is a different defect (fixed in 26.3) | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |
| bb3b52f4 | Aspose.Words-FOSS-for-Python (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.Words FOSS for Python: the dev extra lacks pdfplumber, so one ApiExamples test fails | Low | iss3b-docker-wordspy_py312.txt; iss3b-pdfplumber-Words-Python.txt | yes: python:3.12, 1 failed 26 passed | open #3 (Chinese text lost) is unrelated | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 2 |

### Wave 3: Low-severity metadata, licence layout and documentation

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| 52d17222 | Aspose.3D-FOSS-for-Python (dry_run) | STALE_METADATA | Aspose.3D FOSS for Python: setup.py url points to a repository that returns 404 | Low | iss3b-seturl-3D-Python.txt | yes: setup.py:15 url 404; PyPI 26.1.0 Homepage is the same address | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| cf626176 | Aspose.Cells-FOSS-for-.NET (dry_run) | LICENSE_MISSING_ROOT | Aspose.Cells FOSS for .NET: the license file is only in License/, not at the repository root | Low | iss3b-license-Cells-NET.txt | yes: License/ only; GitHub license null | open #1 (NuGet unavailable) and PR #3 (presenter) are unrelated | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 9bc5df82 | Aspose.Cells-FOSS-for-Cpp (dry_run) | LICENSE_MISSING_ROOT | Aspose.Cells FOSS for Cpp: the license file is only in License/, not at the repository root | Low | iss3b-license-Cells-Cpp.txt | yes: License/LICENSE.txt only; GitHub license null | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 83a93576 | Aspose.Cells-FOSS-for-Java (full) | LICENSE_MISSING_ROOT | Aspose.Cells FOSS for Java: the license file is only in License/, not at the repository root | Low | iss3b-license-Cells-Java.txt | yes: License/LICENSE.txt only; GitHub license null | none: no open issue in the repository | approval (no record) | **FILE** wave 3 |
| a2e2612a | Aspose.Cells-FOSS-for-Python (dry_run) | LICENSE_MISSING_ROOT | Aspose.Cells FOSS for Python: the license file is only in License/, not at the repository root | Low | iss3b-license-Cells-Python.txt | yes at head 952317ca (moved today, still License/ only) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 5dc560bf | Aspose.Cells-FOSS-for-TypeScript (dry_run) | LICENSE_MISSING_ROOT | Aspose.Cells FOSS for TypeScript: the license file is only in License/, not at the repository root | Low | iss3b-license-Cells-TS.txt | yes: License/LICENSE.txt only; GitHub license null | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 0dcf9304 | Aspose.Font-FOSS-for-Python (dry_run) | BROKEN_LINK | Aspose.Font FOSS for Python: README links to docs/one_command_web_optimizer.md, which does not exist | Low | iss3b-link-Font-Python.txt | yes: docs/ does not exist (API 404) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 9cdfad3e | Aspose.GIS.FOSS-for-.Net (dry_run) | LICENSE_MISSING_ROOT | Aspose.GIS.FOSS for .Net: no license file at the repository root | Low | iss3b-license-GIS.txt | yes: no license file anywhere | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| d0228692 | Aspose.GIS.FOSS-for-.Net (dry_run) | README_MISSING_OR_PLACEHOLDER | Aspose.GIS.FOSS for .Net: the repository has no README | Low | iss3b-license-GIS.txt; iss3b-hygiene-GIS.txt | yes: no README (API 404, 114 tracked files) | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 94ba0b5f | Aspose.Page-FOSS-for-Python (dry_run) | STALE_METADATA | Aspose.Page FOSS for Python: published package metadata names no project URL | Low | iss3b-metadata-url-Page-Python.txt | yes: no [project.urls]; PyPI 26.9.0 home_page None | none: no open issue in the repository | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |
| 0f1273fb | Aspose.PSD-FOSS-for-.NET (dry_run) | MANIFEST_PLACEHOLDER_METADATA | Aspose.PSD FOSS for .NET: Aspose.PSD.FOSS.csproj contains placeholder metadata | Low | iss3b-placeholders-PSD-NET.txt | yes: Authors SID, yourorg URLs (404); head moved to 85ed7eec, csproj unchanged | open #5 asks for a LICENSE only (different defect) | registry (dry_run: needs issues_mode file), approval (no record) | **FILE** wave 3 |


Wave 1a is `3f1b3176` (Cells-Cpp `std::numeric_limits` without `<limits>`): a hard compile error on every tested
compiler with a one-line fix, nothing to argue with. The owner named the `-Werror` handoff `b3df5761` as the first
live filing on 2026-10-04; its content is sound and it cross-references `3f1b3176`, but `-Werror` is partly policy, so
it is in wave 2 and should follow once the first issue has landed well. Both are in the same repository and
organization, so one registry change and one App grant cover either order.

## 4. FILE: verified text, but no handoff yet (9)

These are real and reproduced today. Their issue text is written in the handoff shape and passes
`issue_quality_findings`; it is in `decisions/issue-texts-not-yet-fileable.md` (the older, longer drafts are in
`analysis/issue-drafts-unrepresentable.md` with an addendum for today). The handoff model cannot carry them: `defect_class` has no entry for a runtime error, packaging fault,
documentation contradiction or library side effect, and a new class needs a schema and registry change through a
named work item. Until then they can only be filed by hand. Re-verification logs are the same raw logs.

| id | repository | defect class | proposed title | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| U31 | Aspose.3D-FOSS-for-Java (full) | NO_CI_TESTS | Aspose.3D FOSS for Java: no workflow runs the tests, every Maven build step passes -DskipTests | Medium | iss3b-fileformats-3D-Java.txt | yes: .github/workflows holds only maven-central-release.yml; every mvn build step passes -DskipTests | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U06 | Aspose.3D-FOSS-for-TypeScript (dry_run) | PACKAGING_BROKEN | Aspose.3D FOSS for TypeScript: package.json main and types point at dist/index.js, which the build does not produce | Medium | iss3b-packaging-3D-TS.txt; iss3b-docker-threedts_detail.txt | yes: Error: Cannot find module '/w/dist/index.js' (main and types, package.json lines 5-6; src/ has no index.ts) | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U06b | Aspose.3D-FOSS-for-TypeScript (dry_run) | PACKAGING_BROKEN | Aspose.3D FOSS for TypeScript: adm-zip is required at run time for 3MF but is only listed in devDependencies | Medium | iss3b-packaging-3D-TS.txt; iss3b-docker-threedts_detail.txt | yes: devDependencies lists adm-zip (package.json:31) and dependencies only xmldom; required at ThreeMfExporter.ts:162 and ThreeMfImporter.ts:53 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U14 | Aspose.Cells-FOSS-for-Python (dry_run) | LOCALE_DEPENDENT_BEHAVIOUR | Aspose.Cells FOSS for Python: save_as_csv uses the locale encoding by default and raises UnicodeEncodeError for CJK text | Medium | iss3b-csv-encoding-Cells-Python.txt | yes at head 952317ca: UnicodeEncodeError under a cp1252 locale (PYTHONUTF8=0), works under UTF-8 mode | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U16 | Aspose.Cells-FOSS-for-Python (dry_run) | PACKAGING_BROKEN | Aspose.Cells FOSS for Python: the wheel installs a top-level examples package next to aspose | Medium | iss3b-wheel-Cells-Python.txt | yes: wheel 26.10.0 has top-level aspose (73), examples (33) and the dist-info | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U19 | Aspose.Cells-FOSS-for-Rust (dry_run) | NO_TESTS | Aspose.Cells FOSS for Rust: cargo test --all-targets runs 0 tests because the crate has no tests | Medium | iss3b-notests-Cells-Rust.txt; iss3b-docker-cargo_rust.txt | yes: 15 targets, each 'running 0 tests'; tests/ has 0 tracked files, no #[test] | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U38 | Aspose.Page-FOSS-for-Python (dry_run) | RUNTIME_ERROR | Aspose.Page FOSS for Python: aspose.page.mcp.server.run() raises TypeError, host and port reach the stdio transport | Medium | iss3b-mcp-run-Page-Python.txt | yes (fastmcp 4.1.0): TypeError TransportMixin.run_stdio_async() got an unexpected keyword argument 'host'; the README 'Run the MCP Server' example (the presenter's, ca4fb3d7) calls server.run(host=..., port=...) directly and needs its own correction | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U44 | Aspose-PDF-FOSS-for-Python (dry_run) | LIBRARY_SIDE_EFFECT | Aspose.PDF FOSS for Python: the library adds an INFO StreamHandler on stdout when it is imported | Medium | iss3b-stdout-logging-PDF-Python.txt | yes: stdout receives '[INFO] aspose_pdf: Document resources released.'; stderr empty | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |
| U43 | Aspose.PDF-FOSS-for-Java (dry_run) | DOC_CONTRADICTION | Aspose.PDF FOSS for Java: limitations.md lists XLSX and Markdown conversion as unsupported, conversion.md says it works | Medium | iss3b-limitations-PDF-Java.txt | yes: docs/limitations.md:16 (maintainers, 2026-08-19) vs docs/conversion.md:3 (2026-10-05), SaveFormat.java Xlsx/Excel/Markdown, CHANGELOG 121/146. The README lines 1608-1611 repeat it and are the presenter's (ea62b381): fix those in the README lane | open #6 (flaky test, filed by babar-raza) is unrelated | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **FILE** |

## 5. HOLD (26)

Two handoffs and 24 text drafts. The 24 are low-value hygiene, metadata and documentation findings; a maintainer
who receives many one-line hygiene issues at once is less likely to act on the important ones. Recommended: hold them,
and offer them as one courtesy batch per repository once the wave-1 issues have been answered. Resume predicate for
the two handoffs is in the duplicate column.

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| 7e755ed8 | Aspose.Cells-FOSS-for-.NET (dry_run) | EXAMPLE_FAILS | Aspose.Cells FOSS for .NET: README 'Create a Chart' example assigns the read-only Chart.Name (CS0200) | Low | iss3b-chartname-Cells-NET.txt | yes: CS0200 (maintainers' README, first in V26.9.0) | The presenter's own open PR #3 (2026-09-19) deletes that line. Resume predicate: file only if PR #3 is closed unmerged. | registry (dry_run: needs issues_mode file), approval (no record) | **HOLD** |
| a241746e | Aspose.Font-FOSS-for-Python (dry_run) | INSTALL_FAILS | Aspose.Font FOSS for Python: README says to run pip install "aspose-font[mcp]" but no such distribution exists on PyPI | Medium | iss3b-pypi-Font-Python.txt | yes: PyPI aspose-font and aspose-font-foss are 404 | Held: Release 26.10.2 is two days old, so the distribution may still be published. Resume predicate: re-check PyPI after 2026-10-16; file only if still 404. | registry (dry_run: needs issues_mode file), approval (no record) | **HOLD** |

| id | repository | defect class | proposed title | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| U28 | Aspose.3D-FOSS-for-.NET (dry_run) | REPO_HYGIENE | Aspose.3D FOSS for .NET: build.log, test.log and FileFormat.cs.bak are committed | Low | iss3b-hygiene-3D-NET.txt | yes: 3 tracked files, no .gitignore rule | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U29 | Aspose.3D-FOSS-for-.NET (dry_run) | VERSION_MISMATCH | Aspose.3D FOSS for .NET: csproj and NuGet are at 26.1.0 while AGENTS.md and docs describe 26.2.0 | Low | iss3b-hygiene-3D-NET.txt | yes: csproj 26.1.0, NuGet [26.1.0], docs say 26.2.0 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U30 | Aspose.3D-FOSS-for-Java (full) | DOC_CONTRADICTION | Aspose.3D FOSS for Java: FILE_FORMATS.md has duplicate glTF and FBX sections with opposite status | Low | iss3b-fileformats-3D-Java.txt | yes: headings at lines 32/48 and 39/53 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U32 | Aspose.3D-FOSS-for-Java (full) | DOC_BROKEN_REFERENCE | Aspose.3D FOSS for Java: the README refers to an 'Upstream Issues' section that does not exist | Low | iss3b-fileformats-3D-Java.txt | yes: README.md:587 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U07 | Aspose.3D-FOSS-for-TypeScript (dry_run) | TOOLING_BROKEN | Aspose.3D FOSS for TypeScript: npm run lint fails, ESLint finds no configuration file | Low | iss3b-docker-threedts_build.txt | yes: ESLint couldn't find a configuration file | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U50 | Aspose.Cells-FOSS-for-.NET (dry_run) | DOC_BROKEN_REFERENCE | Aspose.Cells FOSS for .NET: agents.md names RELEASE_NOTES_V26.5.0.md, which does not exist | Low | iss3b-cells-net-agents.txt | yes: agents.md:18 and :119; csproj is at 26.9.0.0 | no overlap with open #1 Aspose.Cells.FOSS Unavailable on nuget.org | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U23 | Aspose.Cells-FOSS-for-Cpp (dry_run) | DOC_COMMAND_BROKEN | Aspose.Cells FOSS for Cpp: Aspose.Cells.Foss.Cpp.Tests/README.md uses a workspace/ directory that does not exist | Low | iss3b-paths-Cells-Cpp-tests-readme.txt | yes: lines 8, 9, 15, 19 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U42 | Aspose.Cells-FOSS-for-Go (dry_run) | REPO_HYGIENE | Aspose.Cells FOSS for Go: generated CSV files under examples/outputfiles are committed | Low | iss3b-stale-Cells-Go.txt | yes: employees.csv and exported.csv tracked; .gitignore covers only *.xlsx | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U21 | Aspose.Cells-FOSS-for-Java (full) | STALE_GENERATED_DOC | Aspose.Cells FOSS for Java: docs/apidocs documents the removed com.aspose.cells_foss package | Low | iss3b-javadoc-Cells-Java.txt | yes: title 'cells-foss 1.0.0 API', 112 tracked files for the old package | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U22 | Aspose.Cells-FOSS-for-Java (full) | ENCODING | Aspose.Cells FOSS for Java: pom.xml and Agents.md contain mis-encoded characters | Low | iss3b-javadoc-Cells-Java.txt | yes: pom.xml:62, Agents.md:46 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U15 | Aspose.Cells-FOSS-for-Python (dry_run) | TESTS_FAIL | Aspose.Cells FOSS for Python: examples/test_xlsx_to_markdown.py fails on a clean checkout because input/ is not tracked | Low | iss3b-tests-input-dir-Cells-Python.txt | yes at 952317ca: 1 failed, 16 passed (the earlier JSON-test failure is gone) | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U17 | Aspose.Cells-FOSS-for-Python (dry_run) | STALE_METADATA | Aspose.Cells FOSS for Python: project.urls use the old repository name | Low | iss3b-urls-Cells-Python.txt | yes: old URL redirects (200) to the current repository | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U48a | Aspose.Cells-FOSS-for-TypeScript (dry_run) | PLACEHOLDER_METADATA | Aspose.Cells FOSS for TypeScript: package.json has no license, description, repository or engines field | Low | iss3b-static-Cells-TS.txt | yes: none of the four keys present | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U25 | Aspose.Email-FOSS-for-.Net (dry_run) | DOC_COMMAND_BROKEN | Aspose.Email FOSS for .Net: examples/README.md run commands use a csharp/ directory that does not exist | Low | iss3b-paths-Email-NET.txt | yes: lines 30, 45, 61 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U26 | Aspose.Email-FOSS-for-.Net (dry_run) | VERSION_MISMATCH | Aspose.Email FOSS for .Net: project version 0.1.0 and CHANGELOG disagree with the published package 26.7.0 | Low | iss3b-nuget-Email-NET.txt | yes: csproj 0.1.0, CHANGELOG [0.1.0] 2026-03-18, NuGet 26.7.0 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U24 | Aspose.Email-FOSS-for-Cpp (dry_run) | DOC_COMMAND_BROKEN | Aspose.Email FOSS for Cpp: examples/README.md build commands use a cpp/ directory that does not exist | Low | iss3b-paths-Email-Cpp.txt | yes: lines 30, 31, 46, 62 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U49 | Aspose.Font-FOSS-for-Python (dry_run) | VERSION_MISMATCH | Aspose.Font FOSS for Python: pyproject version is 1.0.0 but the repository is tagged 26.x | Low | iss3b-tags-Font-Python.txt | yes: version = "1.0.0", newest tags 26.9.1-26.9.4 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U09 | Aspose.GIS.FOSS-for-.Net (dry_run) | REPO_HYGIENE | Aspose.GIS.FOSS for .Net: 14 files under obj/ are committed and .gitignore has no obj/ or bin/ rule | Low | iss3b-hygiene-GIS.txt | yes: 14 tracked | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U45 | Aspose.Imaging-FOSS-for-.NET (dry_run) | STALE_METADATA | Aspose.Imaging FOSS for .NET: RepositoryUrl and PackageProjectUrl use the old repository name | Low | iss3b-imaging-recheck.txt | yes: lines 19-20; redirect still answers 200 | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U39 | Aspose.Page-FOSS-for-Python (dry_run) | TESTS_FAIL | Aspose.Page FOSS for Python: two tests import a top-level tools package that is not in the repository | Low | iss3b-tools-package-Page-Python.txt | yes: ImportError cannot import name 'codex_hook_post_metrics' from 'tools'; Makefile runs tools/metrics_api_v1.py | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U11 | Aspose.PSD-FOSS-for-Python (dry_run) | NOT_INSTALLABLE | Aspose.PSD FOSS for Python: no pyproject.toml or setup.py, so the package cannot be installed; __init__.py is empty | Low | iss3b-psdpy-structure.txt | yes at dbc90f46; the README is no longer a placeholder (the presenter's PR #5 merged 2026-10-10), so that half of the old draft is obsolete | owner already filed #4 ('Add a LICENSE file and merge real source to main') | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U12 | Aspose.PSD-FOSS-for-Python (dry_run) | REPO_HYGIENE | Aspose.PSD FOSS for Python: generated MSBuild obj/ files are committed as Python modules | Low | iss3b-psdpy-structure.txt | yes: 4 files | open #4 (license) and #1 (timeline) are unrelated | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U13 | Aspose.PSD-FOSS-for-Python (dry_run) | TESTS_NOT_DISCOVERED | Aspose.PSD FOSS for Python: plain pytest runs no tests, the modules are named *tests.py | Low | iss3b-pytest-PSD-Python.txt | yes: no tests ran; 11 *tests.py modules, 0 test_*.py | owner already filed #4 (pre-release repository) | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |
| U40 | Aspose.Words-FOSS-for-.NET (dry_run) | STALE_DOC | Aspose.Words FOSS for .NET: the README says the NuGet package is landing soon although it is published | Low | iss3b-nuget-Words-NET.txt | yes: README.md:952 (maintainers, 2026-09-01), NuGet 26.2.0 and 26.3.0; the 615-vs-617 counts: the 617 line is the presenter's (68d56fda), so only the sentence is upstream's | none: no open issue in the repository | no handoff (needs a defect class the registry does not have); text gate-checked in issue-texts-not-yet-fileable.md | **HOLD** |

## 6. README-CORRECTION (11): do not file, fix the README

Each failing text was written, or reshaped into its failing form, by one of the owner's merged README pull requests
(`babar-raza`), found by walking the file's history. The six with handoffs are recorded `NOT_A_DEFECT` in `reverification.json`; `issue-readiness` marks
them not approvable. The correction lane should fix: 3D-.NET (`FromFile` overload, `Vector3` using, `Save` call,
U3D/RVM/AMF/HTML5 labels), 3D-TypeScript (`controlPoints`), Cells-Cpp (`WorksheetCollection.h`), PDF-Cpp (headers for
the create-from-scratch and TIFF blocks), Slides-Cpp (`slide.h`), Cells-Go (formula list, missing APIs, heading),
Cells-Rust (pre-publication sentence), Cells-TypeScript (placeholder API rows), PDF-Java README lines 1608-1611 and
Page-Python's "Run the MCP Server" example.

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| ad94a06d | Aspose.3D-FOSS-for-.NET (dry_run) | EXAMPLE_FAILS | Aspose.3D FOSS for .NET: README example Scene.FromFile(string, FileFormat) has no matching overload (CS1503) | Low | iss3b-fromfile-3D-NET.txt; iss3b-provenance.txt | yes: CS1503, but README.md:168 first appears in the presenter's commit 042a1e5f (2026-08-19) | none: no open issue in the repository | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |
| 9264bf05 | Aspose.3D-FOSS-for-TypeScript (dry_run) | EXAMPLE_FAILS | Aspose.3D FOSS for TypeScript: README example fails to type-check, no 'controlPoints' on type 'Entity' (TS2339) | Low | iss3b-docker-threedts_readme_tsc.txt; iss3b-provenance.txt | yes: TS2339, but the example first appears in the presenter's commit 66cb26df (2026-09-18) | none: no open issue in the repository | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |
| 74b4b0a3 | Aspose.Cells-FOSS-for-Cpp (dry_run) | EXAMPLE_FAILS | Aspose.Cells FOSS for Cpp: README 'Load an Existing Workbook' example does not compile, missing WorksheetCollection.h | Low | iss3b-docker-snippet_cellscpp.txt; iss3b-provenance.txt | yes: no match for operator[]; the example first appears in the presenter's commit 9f852d0f (2026-08-13); adding WorksheetCollection.h fixes it | none: no open issue in the repository | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |
| a1a661ef | Aspose.PDF-FOSS-for-Cpp (dry_run) | EXAMPLE_FAILS | Aspose.PDF FOSS for Cpp: README create-from-scratch example does not compile, missing Paragraphs/Artifact headers | Low | iss3b-docker-snippet_pdfcpp.txt; iss3b-provenance.txt | yes: incomplete type Paragraphs/ArtifactCollection; made stand-alone by the presenter's refresh c559fc3d | none: no open issue in the repository | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |
| f49213f4 | Aspose.PDF-FOSS-for-Cpp (dry_run) | EXAMPLE_FAILS | Aspose.PDF FOSS for Cpp: README TIFF example does not compile, page_collection.hpp is not included | Low | iss3b-docker-snippet_pdfcpp.txt; iss3b-provenance.txt | yes: incomplete type PageCollection; same history | none: no open issue in the repository | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |
| 8b8b2cae | Aspose.Slides-FOSS-for-Cpp (dry_run) | EXAMPLE_FAILS | Aspose.Slides FOSS for Cpp: README C++ examples do not compile, <Aspose/Slides/Foss/slide.h> is not included | Low | iss3b-docker-snippet_slidescpp.txt; iss3b-provenance.txt | yes: 6 of 10 blocks lack slide.h; regression from the presenter's PR 6ed44d59 | no overlap with open #4 Table cell portion formatting is discarded on save | re-verification NOT_A_DEFECT, registry (dry_run: needs issues_mode file), approval (no record) | **README-CORRECTION** |

| id | repository | defect class | proposed title | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| RC-3DNET-FORMATS | Aspose.3D-FOSS-for-.NET (dry_run) | README_CLAIM (ours) | Aspose.3D FOSS for .NET README diagram lists U3D, RVM, AMF and HTML5, which IOService.cs does not read or write | Medium | iss3b-provenance.txt | yes: IOService.cs dispatch is OBJ, STL, glTF, FBX, 3MF, COLLADA, PLY, 3DS only; the labels are the presenter's (RVM since 158183d2, U3D since 042a1e5f) | none: no open issue in the repository | - | **README-CORRECTION** |
| RC-3DJAVA-EDITION | Aspose.3D-FOSS-for-Java (full) | README_CLAIM (policy) | Aspose.3D FOSS for Java README uses a non-canonical edition name ('commercial-edition') | Low | iss3b-provenance.txt | yes: README.md:589 says 'commercial-edition' (a non-canonical edition name); the sentence is the presenter's own (0f77c8a3, 2026-09-12), so it is a README correction, not a defect in the library | none: no open issue in the repository | - | **README-CORRECTION** |
| U41 | Aspose.Cells-FOSS-for-Go (dry_run) | README_CLAIM (ours) | Aspose.Cells FOSS for Go README lists four formula functions (22 exist), omits chart, pivot, conditional-format and VBA APIs, and has a stray heading | Low | iss3b-stale-Cells-Go.txt; iss3b-provenance.txt | yes, but the README text is the presenter's (9f0a4033, 2026-08-13) | none: no open issue in the repository | - | **README-CORRECTION** |
| U20 | Aspose.Cells-FOSS-for-Rust (dry_run) | README_CLAIM (ours) | Aspose.Cells FOSS for Rust README: 'Once the repository is live at its real GitHub location' is a pre-publication leftover | Low | iss3b-notests-Cells-Rust.txt; iss3b-provenance.txt | yes, but the text is the presenter's (1a6004af, 2026-08-14) | none: no open issue in the repository | - | **README-CORRECTION** |
| U48b | Aspose.Cells-FOSS-for-TypeScript (dry_run) | README_CLAIM (ours) | Aspose.Cells FOSS for TypeScript README: 24 API-table rows read 'Class in the Cells TYPESCRIPT API.' | Low | iss3b-static-Cells-TS.txt; iss3b-provenance.txt | yes, but the rows are the presenter's (fc186507, 2026-08-14) | none: no open issue in the repository | - | **README-CORRECTION** |

## 7. DROP (13)

| id | repository | defect class | proposed title (exact) | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| a6f52c1a | Aspose.3D-FOSS-for-TypeScript (dry_run) | INSTALL_FAILS | install_command:npm is CONTRADICTED at 66cb26df3b03 | n/a | iss3b-npm-registry-3D-TS.txt | yes (npm 404) but disclosed in the README ('there is no published package to import by name yet'); text fails the quality gate | none: no open issue in the repository | re-verification NOT_A_DEFECT, quality gate, registry (dry_run: needs issues_mode file), approval (no record) | **DROP** |
| 2c99dc76 | Aspose.Imaging-FOSS-for-.NET (dry_run) | INSTALL_FAILS | README install command and NuGet badge reference Aspose.Imaging.Foss, which does not exist on nuget.org | n/a | iss3b-imaging-readme-Imaging-NET.txt | no: the README no longer has the install command or the badge (head 6ebb2091) | none: no open issue in the repository | re-verification FIXED_OR_CHANGED, quality gate, registry (dry_run: needs issues_mode file), approval (no record) | **DROP** |
| ef667e7d | Aspose.PDF-FOSS-for-TypeScript (dry_run) | INSTALL_FAILS | install_command:npm is CONTRADICTED at a8661f8bc557 | n/a | iss3b-npm-registry-PDF-TS.txt | yes (npm 404) but the README documents the source install; text fails the quality gate | none: no open issue in the repository | re-verification NOT_A_DEFECT, quality gate, registry (dry_run: needs issues_mode file), approval (no record) | **DROP** |
| b7bf37c2 | repository-presenter (not listed) | synthetic | [G6-W01 live proof] synthetic filing-path test - not a product defect | n/a | - | n/a: the G6-W01 filing-path test record (issue #189), already FILED | none: no open issue in the repository | status FILED, re-verification UNVERIFIED (no entry in reverification.json), quality gate, registry (dry_run: needs issues_mode file), approval (no record) | **DROP** |

| id | repository | defect class | proposed title | sev | evidence (raw-logs) | reproduced 2026-10-11 | duplicate check | readiness blockers | action |
|---|---|---|---|---|---|---|---|---|---|
| U33 | Aspose.3D-FOSS-for-Java (full) | PUBLISHED_ARTIFACT_STALE | Publish a release built from HEAD: the 26.5.0 jar ships OBJ, glTF and FBX loader/saver stubs | Low | iss3b-disclosed-3D-Java-jar.txt | yes, but disclosed: README.md:587 warns that the published artifact ships a stub; Central still has only 26.5.0 | none: no open issue in the repository | - | **DROP** |
| RUST-CRATES | Aspose.Cells-FOSS-for-Rust (dry_run) | PUBLISHED_ARTIFACT_STALE | Aspose.Cells FOSS for Rust: the crate is not on crates.io | n/a | iss3b-crates-Cells-Rust.txt | not a defect: the README states it is not yet published (README.md:105, :674) | none: no open issue in the repository | - | **DROP** |
| EMAIL-PY-EXCERPT | Aspose.Email-FOSS-for-Python (dry_run) | DOC_EXCERPT | Aspose.Email FOSS for Python README: the 'Inspect Low-Level MSG' excerpt uses an undefined msg_path | Low | iss3b-email-python-excerpt.txt | yes, but it is a labelled excerpt of examples/msg_reader.py, not a runnable block | none: no open issue in the repository | - | **DROP** |
| JMAP-x8 | Aspose.JMAP-FOSS-for-{.NET,Cpp,Go,Java,Node.js,Python,Rust,TypeScript} (-) | none | Aspose.JMAP FOSS (eight repositories): packages are not published and examples need a live server | n/a | iss3b-jmap-disclosure.txt; iss3b-ci-runs.txt | no defect: every README says no package is published, the registries agree, CI is green in all eight | - | - | **DROP** |
| PDFCPP-CONFIGURE | Aspose.PDF-FOSS-for-Cpp (dry_run) | BUILD_OR_TESTS_FAIL | Aspose.PDF FOSS for Cpp: CMake configure fails (wave-4 note) | n/a | iss3b-docker-pdfcpp_build.txt | no: cmake -S . -B build, build and ctest succeed on gcc 14.4 / CMake 3.31.6 (1 of 1 tests pass); the wave-4 failure was the presenter's own runner | none: no open issue in the repository | - | **DROP** |
| LIC-PSD-NET | Aspose.PSD-FOSS-for-.NET (dry_run) | LICENSE_MISSING_ROOT | Aspose.PSD FOSS for .NET: no license file at the repository root | Medium | iss3b-license-PSD-NET.txt | yes: no license file; GitHub license null | DUPLICATE of open #5 'Add a LICENSE file and merge real source to main' (babar-raza, 2026-09-25) | - | **DROP** |
| LIC-PSD-PY | Aspose.PSD-FOSS-for-Python (dry_run) | LICENSE_MISSING_ROOT | Aspose.PSD FOSS for Python: no license file at the repository root | Medium | iss3b-license-PSD-Py.txt | yes: no license file; GitHub license null | DUPLICATE of open #4 'Add a LICENSE file and merge real source to main' (babar-raza, 2026-09-25) | - | **DROP** |
| U46 | Aspose.Slides-FOSS-for-Java (dry_run) | PUBLISHED_ARTIFACT_STALE | Publish 26.8.0: Maven Central still serves only 26.7.0 | Low | iss3b-maven-Slides-Java.txt | yes, but disclosed in SECURITY.md:11 and README.md:95 | none: no open issue in the repository | - | **DROP** |
| U47 | Aspose.Slides-FOSS-for-Python (dry_run) | PUBLISHED_ARTIFACT_STALE | Publish a release: aspose-slides-foss 26.8.0 on PyPI lacks Hyperlink | Low | iss3b-pypi-Slides-Python.txt | yes (ImportError cannot import name 'Hyperlink'), but disclosed in README.md:134 | none: no open issue in the repository | - | **DROP** |


## 8. What the owner must do to enable filing

Nothing below was done by this lane.

### 8.1 Registry modes today

`data/registry.json` has 44 entries. **Registry mode `full` (2):** Aspose.3D-FOSS-for-Java, Aspose.Cells-FOSS-for-Java.
**Registry mode `dry_run` (42):** every other entry; none is `disabled`, none sets `issues_mode`. An entry with no
`issues_mode` derives it from `mode`, so the two `full` repositories are already issue-eligible; the 42 `dry_run` ones
refuse issue filing until `issues_mode` is `file`.

### 8.2 Registry: `"issues_mode": "file"` for the repositories that carry a FILE handoff

Setting it arms issue filing for that entry only and leaves its README pull request refused (`docs/PROPOSAL_WAVE_RUNBOOK.md`
section 8). Reviewed pull request to `data/registry.json`. Arm only the repositories of the wave being filed:

| wave | repositories that need `issues_mode: file` |
|---|---|
| 1a | Aspose.Cells-FOSS-for-Cpp |
| 1b | Aspose.3D-FOSS-for-.NET, Aspose.3D-FOSS-for-Python, Aspose.Email-FOSS-for-Cpp, Aspose.GIS.FOSS-for-.Net, Aspose.HTML-FOSS-for-Python, Aspose.Page-FOSS-for-Python, Aspose.TeX-FOSS-for-Python |
| 2 | Aspose.3D-FOSS-for-.NET, Aspose.3D-FOSS-for-Python, Aspose.3D-FOSS-for-TypeScript, Aspose.Cells-FOSS-for-Cpp, Aspose.Cells-FOSS-for-TypeScript, Aspose.Font-FOSS-for-Python, Aspose.HTML-FOSS-for-Python, Aspose.Note-FOSS-for-Python, Aspose.Words-FOSS-for-Python |
| 3 | Aspose.3D-FOSS-for-Python, Aspose.Cells-FOSS-for-.NET, Aspose.Cells-FOSS-for-Cpp, Aspose.Cells-FOSS-for-Python, Aspose.Cells-FOSS-for-TypeScript, Aspose.Font-FOSS-for-Python, Aspose.GIS.FOSS-for-.Net, Aspose.Page-FOSS-for-Python, Aspose.PSD-FOSS-for-.NET |

Already issue-eligible (`mode: full`): Aspose.Cells-FOSS-for-Java (its wave-3 licence handoff needs only an approval).
All together 16 `dry_run` entries need the field: Aspose.3D-FOSS-for-.NET, Aspose.3D-FOSS-for-Python, Aspose.3D-FOSS-for-TypeScript, Aspose.Cells-FOSS-for-.NET, Aspose.Cells-FOSS-for-Cpp, Aspose.Cells-FOSS-for-Python, Aspose.Cells-FOSS-for-TypeScript, Aspose.Email-FOSS-for-Cpp, Aspose.Font-FOSS-for-Python, Aspose.GIS.FOSS-for-.Net, Aspose.HTML-FOSS-for-Python, Aspose.Note-FOSS-for-Python, Aspose.Page-FOSS-for-Python, Aspose.PSD-FOSS-for-.NET, Aspose.TeX-FOSS-for-Python, Aspose.Words-FOSS-for-Python.

### 8.3 GitHub App: Issues: write, per organization

The App must hold Contents: write, Pull requests: write, **Issues: write** and Metadata: read on each organization
that owns a FILE repository. Click path (`docs/PROPOSAL_WAVE_RUNBOOK.md` section 1, item 1): open
`https://github.com/organizations/<org>/settings/installations`, **Configure** on repository-presenter, repository access
"All repositories" (or the target repository), accept the pending permission update. `audit-app-installations.yml`
proves Metadata: read only, so the first filing in each organization is the real test of the write grant. The organizations
holding FILE handoffs (11): aspose-3d-foss, aspose-cells-foss, aspose-email-foss, aspose-font-foss, aspose-gis-foss, aspose-html-foss, aspose-note-foss, aspose-page-foss, aspose-psd-foss, aspose-tex-foss, aspose-words-foss. Only the organization holding the wave being filed needs the grant
first (wave 1a needs only `aspose-cells-foss`). The text-only FILE rows would add `aspose-pdf-foss`. No new secret is needed: the workflow mints an issues-write installation
token from the existing App secrets (`GH_APP_ID`, `GH_APP_PRIVATE_KEY`), which this lane could not inspect.

### 8.4 Approval records (human-authored, reviewed pull request)

For each wave, from a checkout of this branch, emit the records into a scratch directory outside the repository (the
command refuses `ops/`), read each one, and commit them under `ops/issue_approvals/` in a pull request you author and
merge. Records expire (7 days by default, at most 30); a handoff that changes after the digest was shown is refused as
stale. The id files in this directory were checked against the emitter today (1, 7, 11 and 11 records; scratch output
deleted):

```sh
repository-presenter issue-readiness --emit-approvals ../issue-approvals-scratch \
    --approver <owner-github-login> --valid-days 7 \
    --handoff-ids-file evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/decisions/issue-approval-ids-wave-1a-first-filing.txt
# then wave-1b, wave-2, wave-3 in turn, each only after the previous wave has been answered
repository-presenter file-upstream-defects --repo <owner>/<name>   # each approved handoff must read WOULD-FILE
```

### 8.5 Kill switch and run

Repository variable `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` = `1` (Settings > Secrets and variables > Actions >
Variables), then dispatch `issues-scheduled.yml` (it also runs daily at 03:41 UTC). The variable can only stop filing; it
never authorizes one, so with it on the scheduled workflow files **every** approved handoff it finds, subject to the caps
(3 a day and 5 open per repository, 10 seconds between writes). Approve only the rows you mean to file. Commenting on
filed issues is a separate variable (`REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED`) and is not needed to file.

### 8.6 Before each wave

Upstream heads move (Cells-Python, PSD-.NET and PSD-Python moved in the last two days). Re-run
`repository-presenter issue-readiness` the day you approve: a moved head makes the recheck inconclusive and the filer
refuses it.

## 9. Changes made to the handoff record today

- 16 handoffs added under `evidence/upstream-defects/`: 7 drafted from verified reproductions (GIS build, Page install,
  3D-.NET tests, 3D-TS jest, HTML collection, 3D-Python unittest, Words-Python pdfplumber) and 9 emitted by the
  defect-class detectors (7 licence, 1 README, 1 placeholder manifest).
- `af8da760` (3D-.NET) re-drafted as described in section 1, same fingerprint.
- `reverification.json`: all 41 entries refreshed; six set to `NOT_A_DEFECT` (README-CORRECTION).
- `tests/components/issues/test_ledger.py`: the corpus count 26 to 42. `tests/components/issues/test_classes.py`: the
  test that required every committed handoff to lack `defect_class` now checks both shapes.
- `decisions/issue-texts-not-yet-fileable.md`: the 9 text-only FILE issues, each held to `issue_quality_findings` (all pass).
- 88 sanitized raw logs under `analysis/raw-logs/iss3b-*`, the scripts under `analysis/scripts/iss3b/`, this table
  (`issue-approval-table-final.md` and `.csv`) and the four wave id files.
