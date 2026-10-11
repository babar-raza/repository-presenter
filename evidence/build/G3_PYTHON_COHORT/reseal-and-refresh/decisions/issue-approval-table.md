authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Upstream issue approval table (TC-ISS-07-01, G6-W01)

Prepared 2026-10-11 by lane L-approvals for the owner. Nothing was filed, no approval record was
written, and no repository outside this checkout was written to. Inputs: `issue-readiness --json` run on
`wt/lapp-iss07` (integration/verified-1011 merged with the TC-ISS-01 inventory and TC-ISS-05 `issues_mode`
branches); read-only `gh api` GETs of each target's HEAD, issues, pull requests, README history and a few raw
files on 2026-10-11; and the handoffs under `evidence/upstream-defects/`.

**Result: 12 FILE, 2 HOLD, 10 DROP** of 24 handoffs on record.

## Read this first: six handoffs describe our own README mistakes

The ledger comes from the presenter's own checks, which run against READMEs. Before recommending any
README-example issue I traced who wrote the failing text (`gh api commits?path=README.md`, then the README at
each commit). For six handoffs the failing example was written, or reshaped into its failing form, by our own
merged README pull requests (the `babar-raza` PRs), not by the maintainers: 3D-.NET `FromFile` (ad94a06d),
3D-TS `controlPoints` (9264bf05), Cells-Cpp `Load an Existing Workbook` (74b4b0a3), PDF-Cpp x2 (a1a661ef,
f49213f4) and Slides `slide.h` (8b8b2cae, where we removed includes the maintainers had). Filing those upstream
would blame the maintainers for our edit. The right fix is a corrected README in the next presenter pull request,
and these ledger entries should be closed as superseded, not approved. Library-level bugs that our examples merely
exposed (3D-Py OBJ export, 3D-.NET FBX save) stay FILE because the defect is in the library.

## 1. Approval table

Columns: id = first 8 hex of the handoff fingerprint (full ids in section 3). Live head now = the default-branch
head compared with the revision the tool re-verified (`gh api repos/<r>/commits/HEAD`, 2026-10-11). Tool blockers
are the readiness tool's own list; all 23 pending handoffs are registry `dry_run` and none has an approval record,
so every pending row carries `registry` and `approval`. Severity: High = the library cannot be built, installed or
imported; Medium = a documented example or feature fails at runtime; Low = documentation or verification accuracy.

| id | repository | class / check | proposed issue title (exact) | sev | evidence | reproduced at | live head now | quality gate | tool blockers | recommendation |
|---|---|---|---|---|---|---|---|---|---|---|
| c00f9615 | aspose-tex-foss/Aspose.TeX-FOSS-for-Python | NOT_PROCESSABLE | Aspose.TeX FOSS for Python: 102 of 119 .py files fail to parse (IndentationError) and 'import aspose_tex' fails | High | ast.parse over all .py files at the live head: 102 of 119 raise IndentationError (src/aspose_tex 35 of 45); `PYTHONPATH=src python -I -c 'import aspose_tex'` fails at _input/catcode.py:66. Raw blob of catcode.py re-read 2026-10-11: one-space indentation, a `for` body at the same level as the `for`. | 181015d2 (2026-10-10) | same | passes | registry, approval | **FILE**: The package cannot be imported. A maintainer needs this. |
| 094c4163 | aspose-3d-foss/Aspose.3D-FOSS-for-Python | BC-03 | Aspose.3D FOSS for Python: Scene.save() to an .obj path raises TypeError (a bytes-like object is required, not 'str') | High | README.md:274-286 verbatim after `pip install -e .`: TypeError at ObjExporter.py:50 (file opened 'wb', then write(str)); any scene saved to .obj fails. OBJ export is advertised in README lines 8-9 and 61-65. | 65b1f577 (2026-10-09) | same | passes | registry, approval | **FILE**: Library bug, not an example slip. The README example text was added by our own PR (see the DROP note above), but the body is a repro of Scene.save with file:line causes, so it reads honestly. |
| 3f1b3176 | aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | BC-02 | Aspose.Cells FOSS for Cpp: XlsxWorkbookSerializerCommon.cpp uses std::numeric_limits without including <limits> | High | XlsxWorkbookSerializerCommon.cpp:965-968 use std::numeric_limits; include list (lines 29-37) has no <limits>. cmake build on gcc 13.5/14.4/15.3 and clang 22.1.8: 'numeric_limits is not a member of std' (12 errors). | 9f852d0f (2026-10-09) | same | passes | registry, approval | **FILE**: Hard compile error, one-line fix, nothing to argue with. Best first filing (section 4). |
| 7f0f3388 | aspose-email-foss/Aspose.Email-FOSS-for-Cpp | BC-02 | Aspose.Email FOSS for Cpp: cfb_reader::header() 'changes meaning of header', the library fails on GCC 12-15 | High | cfb_reader.hpp:28 `const header& header() const`: -Wchanges-meaning error, 9 translation units fail on g++ 12/13/14/15 (clang 18/22 accept). Default cmake build. | c844a467 (2026-10-09) | same | passes | registry, approval | **FILE**: Real portability break on the mainstream Linux compiler; exact cause and location. |
| ae9f06b9 | aspose-html-foss/Aspose.HTML-FOSS-for-Python | BC-02 | Aspose.HTML FOSS for Python: pip install . fails, the build-backend setuptools.backends.legacy:build does not exist | High | pyproject.toml:3 `build-backend = "setuptools.backends.legacy:build"` (re-read 2026-10-11, still there); `pip install .` fails with BackendUnavailable. The module exists in no setuptools release. | bf0f1e7a (2026-10-09) | same | passes | registry, approval | **FILE**: The project cannot be installed from source; one-line fix (setuptools.build_meta). |
| b3df5761 | aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | BC-02 | Aspose.Cells FOSS for Cpp: the library build uses -Werror and fails on warnings with GCC 13-15 and Clang 22 | Medium | cmake/toolchain-detect.cmake:4 `-Wall -Wextra -Werror` for non-MSVC; first error NumberFormat.cpp:30:17 (trigraph `??/` in the literal "# ??/??"); 3 translation units fail on gcc 13-15, 5 on clang 22. Body cross-references the separate numeric_limits issue. | 9f852d0f (2026-10-09) | same | passes | registry, approval | **FILE**: Real: committed code trips its own -Werror on current compilers, and the trigraph literal is a latent bug. -Werror is partly policy, so file after 3f1b3176. This is the owner-named handoff. |
| 52ba0e1d | aspose-font-foss/Aspose.Font-FOSS-for-Python | BC-03 | Aspose.Font FOSS for Python: README web-optimizer example raises KeyError 'subset' (manifest lacks the keys) | Medium | README.md:295-418 verbatim: KeyError 'subset' at line 390; probe: 'subset' in package.manifest False, in package.bundle.manifest True (web.py:761 vs ~2544-2573). README is the maintainers' (Release 26.10.2, 2026-10-09). | adf4885a (2026-10-09) | same | passes | registry, approval | **FILE**: Maintainer-authored example crashes; clear cause. |
| dc90b681 | aspose-font-foss/Aspose.Font-FOSS-for-Python | BC-03 | Aspose.Font FOSS for Python: README example calls VariableInstanceBuilder.build_package with unaccepted arguments | Medium | README.md:128-141 verbatim: TypeError unexpected keyword 'instance_names'; instances.py:136 `build_package(self, names=None, *, ...)` has no output_dir. README is the maintainers' (Release 26.10.2). | adf4885a (2026-10-09) | same | passes | registry, approval | **FILE**: Maintainer-authored example; exact signature mismatch. |
| 0dcf9304 | aspose-font-foss/Aspose.Font-FOSS-for-Python | BC-06 | Aspose.Font FOSS for Python: README links to docs/one_command_web_optimizer.md, which does not exist | Low | README.md:518 links docs/one_command_web_optimizer.md; `gh api .../contents/docs` is 404; the repository root (re-listed 2026-10-11) has no docs directory. | adf4885a (2026-10-09) | same | passes | registry, approval | **FILE**: Small but unambiguous. File it last so a one-day-old release is not met by three issues at once. |
| 6532670d | aspose-note-foss/Aspose.Note-FOSS-for-Python | BC-03 | Aspose.Note FOSS for Python: README Quick Start crashes because page.Title is None for pages without a title | Medium | README Quick Start (lines 104-111, maintainers' text since 2026-01-12): `print(page.Title.TitleText.Text)` raises AttributeError on the repo's own testfiles/SimpleTable.one (page.Title is None). The README's own API lines 361/365 declare Title and TitleText as `\| None`. | 17b5d7fe (2026-10-10) | 0fd1cf7b: two commits (a9cf4d5a and its revert), compare shows 0 changed files, so content is identical | passes | registry, approval | **FILE**: Maintainers answer quickly here (closed Title issue #1 with a fix). The reproduction is still valid because the tree is unchanged. |
| c04f74bf | aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | BC-02 | Aspose.Cells FOSS for TypeScript: the documented `npx tsc --noEmit` reports 3 type errors | Low | README.md:329-334 (maintainers' text since 2026-05-25) tells readers to run `npm install` then `npx tsc --noEmit`; node:22, TypeScript 5.9.3: 3 errors (chartLoader.ts:210 TS2345, html/htmlDocument.ts:92 TS7006, workbook.ts:482 TS2345), exit 2. | fc186507 (2026-10-09) | same | passes | registry, approval | **FILE**: The documented verification command fails; precise errors. |
| af8da760 | aspose-3d-foss/Aspose.3D-FOSS-for-.NET | BC-03 | Aspose.3D FOSS for .NET: README Quick Start throws NotImplementedException in Scene.Save(path, FBX7400Binary) | Medium | dotnet run of the Quick Start (README.md:130-143): NotImplementedException 'Save options not implemented for .fbx' from FileFormat.CreateSaveOptions (FileFormat.cs:349) via Scene.Save(string, FileFormat) (Scene.cs:427); `scene.Save("output.fbx")` works (2185 bytes). | 52b0f00e (2026-10-10) | same | passes | registry, approval | **FILE**: Library bug: a public FileFormat constant whose Save throws. The README line is ours (PR 042a1e5f), but the body leads with the library behaviour and offers a library fix first. We should also correct our README. |
| a241746e | aspose-font-foss/Aspose.Font-FOSS-for-Python | BC-02 | Aspose.Font FOSS for Python: README says to run pip install "aspose-font[mcp]" but no such distribution exists on PyPI | Medium | README.md:539 `pip install "aspose-font[mcp]"`; pyproject name aspose-font; pypi.org/pypi/aspose-font/json is 404 and so is aspose-font-foss (re-checked 2026-10-11). | adf4885a (2026-10-09) | same | passes | registry, approval | **HOLD**: The release is one day old; the distribution may be about to be published. Re-check PyPI in a few days; file only if still 404. |
| 7e755ed8 | aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | BC-03 | Aspose.Cells FOSS for .NET: README 'Create a Chart' example assigns the read-only Chart.Name (CS0200) | Low | README.md:254 `chart.Name = "Revenue";` does not compile (CS0200; Chart.cs:47 is get-only). Maintainers' text (first in their V26.9.0, 2026-09-01). | 941814fd (2026-10-09) | same | passes | registry, approval | **HOLD**: Our own open PR #3 (created 2026-09-19, one file) already deletes that line. Nudge or merge-ping that PR instead; file only if it is closed unmerged. A duplicate issue next to a waiting fix is noise. |
| ad94a06d | aspose-3d-foss/Aspose.3D-FOSS-for-.NET | BC-03 | Aspose.3D FOSS for .NET: README example Scene.FromFile(string, FileFormat) has no matching overload (CS1503) | Low | README.md:168 `Scene.FromFile("input.fbx", FileFormat.FBX7400Binary)` does not compile (CS1503); no such overload (Scene.cs:314-344). | 52b0f00e (2026-10-09) | same | passes | registry, approval | **DROP**: Our own error: line 168 first appears in our PR 042a1e5f (2026-08-19); the maintainers' README never had it. Correct our README. |
| 9264bf05 | aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | BC-03 | Aspose.3D FOSS for TypeScript: README example fails to type-check, no 'controlPoints' on type 'Entity' (TS2339) | Low | README.md:143-155 reads node.entity.controlPoints -> TS2339 (Node.entity is Entity \| undefined). | 66cb26df (2026-10-09) | same | passes | registry, approval | **DROP**: Our own error: the pattern first appears in our PR 66cb26df (2026-09-18). Fix the example in our README. |
| a6f52c1a | aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | BC-02 | install_command:npm is CONTRADICTED at 66cb26df3b03 | n/a | npm @aspose/3d is 404. Tool re-verification: NOT_A_DEFECT. | 66cb26df | same | FAILS | reverification NOT_A_DEFECT, quality gate, registry, approval | **DROP**: Already disclosed: the README states 'there is no published package to import by name yet'. Quality gate fails (6 findings); not a defect. |
| 74b4b0a3 | aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | BC-03 | Aspose.Cells FOSS for Cpp: README 'Load an Existing Workbook' example does not compile, missing WorksheetCollection.h | Low | README.md:174-187 `GetWorksheets()["Products"]` needs WorksheetCollection.h; g++ 13.5 'no match for operator[]'. | 9f852d0f (2026-10-10) | same | passes | registry, approval | **DROP**: Our own error: the example first appears in our PR 9f852d0f (2026-08-13). Fix in our README. |
| a1a661ef | aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | BC-03 | Aspose.PDF FOSS for Cpp: README create-from-scratch example does not compile, missing Paragraphs/Artifact headers | Low | README.md:252-299 create-from-scratch block lacks the Paragraphs/Artifact headers; g++ 13.5 incomplete type. | 4b83c9fe (2026-10-10) | same | passes | registry, approval | **DROP**: The block descends from a maintainer fragment (3fd322b1) that our README refresh (c559fc3d) made stand-alone; headers were never listed in either. A fix on our side, not an upstream bug. |
| f49213f4 | aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | BC-03 | Aspose.PDF FOSS for Cpp: README TIFF example does not compile, page_collection.hpp is not included | Low | README.md:359-378 TIFF block: incomplete type PageCollection without page_collection.hpp. | 4b83c9fe (2026-10-10) | same | passes | registry, approval | **DROP**: The original block (3fd322b1) continued earlier snippets whose includes it relied on; our refresh made it stand-alone. Fix in our README. |
| ef667e7d | aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript | BC-02 | install_command:npm is CONTRADICTED at a8661f8bc557 | n/a | npm @asposefoss/pdf is 404. Tool re-verification: NOT_A_DEFECT at c672b391. | c672b391 | same | FAILS | reverification NOT_A_DEFECT, quality gate, registry, approval | **DROP**: Already disclosed: the README documents the source install. Quality gate fails (6 findings). |
| 8b8b2cae | aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | BC-03 | Aspose.Slides FOSS for Cpp: README C++ examples do not compile, <Aspose/Slides/Foss/slide.h> is not included | Low | Six README blocks use pres.slides()[0] without slide.h (invalid use of incomplete type 'Slide', g++ 13.5). | 469ce77a (2026-10-10) | same | passes | registry, approval | **DROP**: Regression introduced by our PR 6ed44d59 (2026-09-19): the maintainers' README before it (1ac4a532) listed slide.h in nine places, the current one in one. Restore the includes in our README. |
| 2c99dc76 | aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET | BC-02 | README install command and NuGet badge reference Aspose.Imaging.Foss, which does not exist on nuget.org | n/a | README install command and NuGet badge named Aspose.Imaging.Foss. | a7c7314b | 6ebb2091: two README-only commits (ours, merged 2026-10-10); README no longer has `dotnet add` or a nuget link | FAILS | reverification FIXED_OR_CHANGED, quality gate, registry, approval | **DROP**: Already fixed; tool verdict FIXED_OR_CHANGED; quality gate fails (3 findings). |
| b7bf37c2 | babar-raza/repository-presenter | BC-02 | [G6-W01 live proof] synthetic filing-path test - not a product defect | n/a | Synthetic G6-W01 filing-path test record. | b7715aa5 | n/a | FAILS | status FILED, reverification UNVERIFIED (no entry in reverification.json), quality gate, registry, approval | **DROP**: Status FILED, never re-filed, not a product defect, not in the registry. |

### Readiness detail

The tool reports every FILE and HOLD row as `approvable: YES`, recheck replayable, re-verification CONFIRMED at the
live head, quality gate passing; the only blockers are `registry` (dry_run) and `approval` (none). Rows the tool
already marks not approvable: a6f52c1a, ef667e7d (NOT_A_DEFECT, quality gate), 2c99dc76 (FIXED_OR_CHANGED, quality
gate), b7bf37c2 (FILED, UNVERIFIED, quality gate). The other six DROP rows are tool-approvable but should not be
approved, for the reasons given.

Target state checked for every FILE row: issues enabled, repository not archived, and no existing issue that
duplicates a handoff (Note-Python has an unrelated open #4; Slides #4 and Cells-.NET #1 are unrelated). The
Cells-Cpp, Email-Cpp, HTML-Python and TeX-Python repositories have no CI workflows, so none can already be tracking
these failures.

## 2. Owner-action lists

### (a) Registry entries (`data/registry.json`) that need `issues_mode: file` for the FILE rows

All 9 are `mode: dry_run` today with no `issues_mode`. Setting `"issues_mode": "file"` (an owner act, separate
from the README wave's `mode` flip; `docs/PROPOSAL_WAVE_RUNBOOK.md` section 8) opens the issue write gate only;
README proposals stay refused. The readiness tool's blocker text still says `dry_run, not full`; it is the same gate,
now reading `issues_mode`.

| registry entry | FILE handoffs | issues_mode needed |
|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | af8da760 | `file` |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 094c4163 | `file` |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | 3f1b3176, b3df5761 | `file` |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | c04f74bf | `file` |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | 7f0f3388 | `file` |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | 52ba0e1d, dc90b681, 0dcf9304 | `file` |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | ae9f06b9 | `file` |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | 6532670d | `file` |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | c00f9615 | `file` |

The Font entry also carries HOLD row a241746e; do not approve that one yet.

### (b) Organizations that must grant the GitHub App Issues: write

| organization | repositories with FILE rows |
|---|---|
| aspose-3d-foss | Aspose.3D-FOSS-for-.NET, Aspose.3D-FOSS-for-Python |
| aspose-cells-foss | Aspose.Cells-FOSS-for-Cpp, Aspose.Cells-FOSS-for-TypeScript |
| aspose-email-foss | Aspose.Email-FOSS-for-Cpp |
| aspose-font-foss | Aspose.Font-FOSS-for-Python |
| aspose-html-foss | Aspose.HTML-FOSS-for-Python |
| aspose-note-foss | Aspose.Note-FOSS-for-Python |
| aspose-tex-foss | Aspose.TeX-FOSS-for-Python |

Click path (runbook section 1, item 1), repeated per organization: open
`https://github.com/organizations/<org>/settings/installations`, then **Configure** on repository-presenter.
Repository access must be "All repositories" (or list the target repository). The permissions panel must show
Contents: write, Pull requests: write, **Issues: write**, Metadata: read; accept any pending permission update.
Then dispatch `audit-app-installations.yml`. That audit proves metadata:read only and cannot show Issues: write,
so the first filing in each organization is the real test (section 4). Only the organization holding the first
filing needs the grant before it; the others can follow once that issue lands.

### (c) Commands the operator would run after approval -- NOT RUN

Mechanics, read from `src/repository_presenter/components/issues/readiness.py` and `ops/issue_approvals/README.md`:
`issue-readiness --emit-approvals` only writes record files into a scratch directory (it refuses a path inside
`ops/`), verifies each record with `verify_approval` before writing it, pins it to the evidence digest when
`@sha256:...` is given, and defaults to a 7-day window (`--valid-days`, at most 30). The owner then commits the
files under `ops/issue_approvals/` through a reviewed pull request. This lane executed none of the commands below.

```sh
# 1. Registry: set issues_mode to file on the entries in (a) -- reviewed PR to data/registry.json.
# 2. Emit the records for the approved rows only, into a scratch directory outside the repository.
#    The approver is a person's login, never a bot. First-filing-only variant: pass just 3f1b3176.
repository-presenter issue-readiness --emit-approvals ../issue-approvals-scratch \
    --approver <owner-github-login> --valid-days 7 \
    --handoff-id aspose-tex-foss__Aspose.TeX-FOSS-for-Python__c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188@sha256:085fcb7e351f42e50d9d6b04fe002cef46eda71f0451af87172745ba5dda2a27 \
    --handoff-id aspose-3d-foss__Aspose.3D-FOSS-for-Python__094c41630d8b8ea6ca8d886b2e354d5e6f84767ace53daf43142bf7bb068aca8@sha256:95b17abef070b5d4cbd3b0acfb48d7b258b15a3f70827ccbc9a11d9467e9bcd0 \
    --handoff-id aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__3f1b3176a85aff35f608c19c67a1aee801783b540debcb14f445ed3c4890d119@sha256:d0b98ad7b94167e9f20405e58183725868299dcaec32ece3b69092e923050907 \
    --handoff-id aspose-email-foss__Aspose.Email-FOSS-for-Cpp__7f0f338845c043416a7a18a79c32d3d99d03378e63d02874a06777674c8031bf@sha256:ad947123b9047cdfea304b8b79f2cb7928d40b57d60317d6e4f53c34b693abef \
    --handoff-id aspose-html-foss__Aspose.HTML-FOSS-for-Python__ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a@sha256:56c7cf2bee1c3f8afc89c659104740d637c768e14442f02d68d97c3950fb5839 \
    --handoff-id aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365@sha256:b01bfc931bff8bccfb57d02c80cc4aac3f0e46a3aecfd89c506b2d5f9ae769f2 \
    --handoff-id aspose-font-foss__Aspose.Font-FOSS-for-Python__52ba0e1d48408fc60df34aac9ca19022a6ebb684f8df28370d4dc27ed859f555@sha256:9972521d1d9b0ea7e55018321be6914c82eff4a69f659b236d47cc79096b41dd \
    --handoff-id aspose-font-foss__Aspose.Font-FOSS-for-Python__dc90b68174c5172f097bdf4902f3e72b964ca2c0810fe4e395f91d3a871e40ad@sha256:524ac181d0313f42e48ed1894cf90f08b20552dec77b851a21d2cc58e99ee17f \
    --handoff-id aspose-font-foss__Aspose.Font-FOSS-for-Python__0dcf93042da33a32bf454f3be75f82733b2595926f376f4f0d987a8e3d2c3ec1@sha256:735acd2448cbeb57f018d50afceea58abcee7b4b4cbcc7d941128d99a567f5b5 \
    --handoff-id aspose-note-foss__Aspose.Note-FOSS-for-Python__6532670d5efd3bebe8be1dae3dfc04c1fd93552edaf757bb49b06c0ae0bcf33f@sha256:0520756651ee322ec2aebf49806f69b54b41320ea5c46bdd1e0e422438a785ad \
    --handoff-id aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript__c04f74bf0b3610a0f3c6d4b25a5c9c2fb9c3501df52aba71f356b6ccf2f0b55c@sha256:bb7f29c1ef939fbc27aca330662cd46d4a5bc91b0550d3b4330a647109017f87 \
    --handoff-id aspose-3d-foss__Aspose.3D-FOSS-for-.NET__af8da7604bac416b51bcc33b5afd7292d30a36f1bec4dcb6cd06d5fdae21b7d0@sha256:e42195757447ec5f1bcdd889de8f0bbb23b0498bb4e1d59524645ba0512c9740
# 3. Read each file, then commit them under ops/issue_approvals/ in a human-authored, reviewed pull request.
# 4. Re-run the dry run per repository; each approved handoff must read WOULD-FILE:
repository-presenter file-upstream-defects --repo <owner>/<name>
# 5. Only then set the kill-switch variable and dispatch the workflow:
#      Settings > Secrets and variables > Actions > Variables > REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED = 1
#      dispatch issues-scheduled.yml
# Recommended: approve and file the first handoff alone (section 4), watch it, then the rest.
```

The ids include the `@sha256:` digests from this run's listing; if a handoff changes before the owner emits, the
tool refuses it as a stale evidence digest rather than approving something unseen. Note the scheduled workflow
files every approved handoff it finds once the variable is `1`, so approve only the rows you mean to file.

## 3. Full handoff ids and digests for the FILE and HOLD rows

| id | handoff id | evidence digest |
|---|---|---|
| c00f9615 | `aspose-tex-foss__Aspose.TeX-FOSS-for-Python__c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188` | `sha256:085fcb7e351f42e50d9d6b04fe002cef46eda71f0451af87172745ba5dda2a27` |
| 094c4163 | `aspose-3d-foss__Aspose.3D-FOSS-for-Python__094c41630d8b8ea6ca8d886b2e354d5e6f84767ace53daf43142bf7bb068aca8` | `sha256:95b17abef070b5d4cbd3b0acfb48d7b258b15a3f70827ccbc9a11d9467e9bcd0` |
| 3f1b3176 | `aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__3f1b3176a85aff35f608c19c67a1aee801783b540debcb14f445ed3c4890d119` | `sha256:d0b98ad7b94167e9f20405e58183725868299dcaec32ece3b69092e923050907` |
| 7f0f3388 | `aspose-email-foss__Aspose.Email-FOSS-for-Cpp__7f0f338845c043416a7a18a79c32d3d99d03378e63d02874a06777674c8031bf` | `sha256:ad947123b9047cdfea304b8b79f2cb7928d40b57d60317d6e4f53c34b693abef` |
| ae9f06b9 | `aspose-html-foss__Aspose.HTML-FOSS-for-Python__ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a` | `sha256:56c7cf2bee1c3f8afc89c659104740d637c768e14442f02d68d97c3950fb5839` |
| b3df5761 | `aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365` | `sha256:b01bfc931bff8bccfb57d02c80cc4aac3f0e46a3aecfd89c506b2d5f9ae769f2` |
| 52ba0e1d | `aspose-font-foss__Aspose.Font-FOSS-for-Python__52ba0e1d48408fc60df34aac9ca19022a6ebb684f8df28370d4dc27ed859f555` | `sha256:9972521d1d9b0ea7e55018321be6914c82eff4a69f659b236d47cc79096b41dd` |
| dc90b681 | `aspose-font-foss__Aspose.Font-FOSS-for-Python__dc90b68174c5172f097bdf4902f3e72b964ca2c0810fe4e395f91d3a871e40ad` | `sha256:524ac181d0313f42e48ed1894cf90f08b20552dec77b851a21d2cc58e99ee17f` |
| 0dcf9304 | `aspose-font-foss__Aspose.Font-FOSS-for-Python__0dcf93042da33a32bf454f3be75f82733b2595926f376f4f0d987a8e3d2c3ec1` | `sha256:735acd2448cbeb57f018d50afceea58abcee7b4b4cbcc7d941128d99a567f5b5` |
| 6532670d | `aspose-note-foss__Aspose.Note-FOSS-for-Python__6532670d5efd3bebe8be1dae3dfc04c1fd93552edaf757bb49b06c0ae0bcf33f` | `sha256:0520756651ee322ec2aebf49806f69b54b41320ea5c46bdd1e0e422438a785ad` |
| c04f74bf | `aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript__c04f74bf0b3610a0f3c6d4b25a5c9c2fb9c3501df52aba71f356b6ccf2f0b55c` | `sha256:bb7f29c1ef939fbc27aca330662cd46d4a5bc91b0550d3b4330a647109017f87` |
| af8da760 | `aspose-3d-foss__Aspose.3D-FOSS-for-.NET__af8da7604bac416b51bcc33b5afd7292d30a36f1bec4dcb6cd06d5fdae21b7d0` | `sha256:e42195757447ec5f1bcdd889de8f0bbb23b0498bb4e1d59524645ba0512c9740` |
| a241746e | `aspose-font-foss__Aspose.Font-FOSS-for-Python__a241746e33239b027fb534be6ce8d6fb164a985028d3223bae1e467dc4d8f995` | `sha256:7363394e14ed471bb356295c7ba9749655aa84d7419b3112c8bb3e63e9318d6a` |
| 7e755ed8 | `aspose-cells-foss__Aspose.Cells-FOSS-for-.NET__7e755ed823c912f7f789979f5c3c28e9927b3fd266c402684fdad4944645dbe0` | `sha256:64f7c9f0b8275ff72bc8994b5da53377a1357b2da970d2b926b7e971195fcfe4` |

## 4. First live filing candidate (text only)

The owner named `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, the trigraph handoff, on 2026-10-04. That is
handoff b3df5761 ("the library build uses -Werror and fails on warnings with GCC 13-15 and Clang 22"; the first error
is the trigraph at NumberFormat.cpp:30:17).

It is a sound first issue on the dimensions that matter for a first live write: head unchanged since 2026-08-13,
reproduced on four compilers by a documented docker command, no CI and no existing issues in the repository, quality
gate passing, a precise file:line body without overreach, and the same organization holds the second handoff.
It is not the best first issue. It is the less certain of the two Cells-Cpp build issues: `-Werror` is partly a
policy choice, so a maintainer can reasonably answer "works as intended, use another compiler", and the first live
exercise should be one nobody can argue with. Recommendation: file **3f1b3176** (`std::numeric_limits` used without
`<limits>`: a hard compile error on every tested compiler, one-line fix) first and alone; if it lands well, file
b3df5761 next, which already cross-references it ("reported in its own issue"). Both are in the same repository
and organization, so one registry change and one Issues: write grant cover either order. If the owner wants the
named handoff first regardless, nothing blocks it and its content is sound.
