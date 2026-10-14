authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Registry ownership rule: measured impact on the 36 registry repositories

Measured 2026-10-11. OLD = integration/cut2-1011 (f2d5a529), NEW = integration/cut2b (cd48fae9). Facts only, no model/gateway
call, no write to any target. Same upstream revision per repository for both sides (resolved once with `git ls-remote HEAD`, each
side cloned at that sha). Registries were read live once per side, within minutes of each other.

## Method and one deviation

Official path first: `repository-presenter present --facts-only --repo aspose-page-foss/Aspose.Page-FOSS-for-Python` ran on both
trees (throwaway shared clones of each commit under G:/rp-facts, venv linked, RP_TOOLCHAIN_REGISTRY = private copy, RP_VENV and
CI_TOOLS_VENV exported). It takes 5-11 minutes per side because it pip-installs the repo to verify README examples and runs the
measured build. Neither feeds the registry-derived install reading (the source-build fallback `_source_build_fact` only admits a
fact whose polarity is CONTRADICTED, or UNRESOLVED on a registry-less ecosystem), so for the 36-repo sweep I ran the same
`cli._run_present` code path up to `extract_facts` with example verification and the measured build skipped (harness
`own_harness.py`, driver `own_drv2.py`, in this scratchpad). Check: on Aspose.Page-FOSS-for-Python the harness and the official
path give identical value and polarity for every fact except the 13 `example:*` / `format:*` facts the harness does not produce.
"Install status" below is therefore the registry-derived status BEFORE any source-build admission; for the 12 CONTRADICTED
repositories the source-build fallback applies identically on both sides, so they are unchanged.

## Result

36 repositories. OLD: 19 SUPPORTED, 12 CONTRADICTED (registry 404), 4 UNRESOLVED (C++, no registry), 1 with no install fact
(PSD-FOSS-for-Python has no manifest at this revision). NEW: 15 SUPPORTED, 4 flipped SUPPORTED -> UNRESOLVED, the rest unchanged.
No repository changed in any other direction.

Flipped (4): Aspose.3D-FOSS-for-.NET, Aspose.Email-FOSS-for-.Net, Aspose.3D-FOSS-for-Python, Aspose.Page-FOSS-for-Python.
For each, `package:published_version` also disappears (it requires an owned reading), and the install fact reads
"a distribution of this name exists, but ownership not confirmed".

Consequence per the validators: BC-02 (`_check_install`) fails any install fact whose polarity is not SUPPORTED, causal stage
EXTRACTING, and the source-build rescue cannot fire because it admits only CONTRADICTED (or UNRESOLVED on a registry-less
ecosystem). So all four are BC-02 blocked under NEW (derived by reading `validation/registry.py::_check_install`, not by running a
candidate through the validator); under OLD all four passed BC-02. BC-14: with no `package:published_version` the check judges
versions against the manifest only and records the "BC-14 pending" note, not a failure.
Unrelated change seen in the same diff (other lane, not ownership): Aspose.Slides-FOSS-for-Java install command version pinned
26.8.0 -> 26.7.0 (the registry's release; manifest says 26.8.0), still SUPPORTED.

## Table (all 36)

| repo | eco | old install | new install | ownership reason (field that decided) |
|---|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | net | SUPPORTED | UNRESOLVED | **FLIPPED**: NuGet registration catalogEntry projectUrl, else licenseUrl -> https://www.nuget.org/packages/Aspose.3D.FOSS/26.1.0/license; matched=False |
| Aspose.3D-FOSS-for-Java | java | SUPPORTED | SUPPORTED | matched=True via POM <url>/<scm> -> https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java |
| Aspose.3D-FOSS-for-Python | python | SUPPORTED | UNRESOLVED | **FLIPPED**: PyPI project_urls (Repository > Homepage > Source > Source Code > first value, else home_page) -> https://github.com/aspose-3d/Aspose.3D-for-Python; matched=False |
| Aspose.3D-FOSS-for-TypeScript | typescript | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.BarCode-FOSS-for-Python | python | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Cells-FOSS-for-.NET | net | SUPPORTED | SUPPORTED | matched=True via NuGet registration catalogEntry projectUrl, else licenseUrl -> https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET |
| Aspose.Cells-FOSS-for-Cpp | cpp | UNRESOLVED | UNRESOLVED | n/a: C++ has no registry (UNRESOLVED registry-less; unchanged) |
| Aspose.Cells-FOSS-for-Go | go | SUPPORTED | SUPPORTED | matched=True via module path -> https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26 |
| Aspose.Cells-FOSS-for-Java | java | SUPPORTED | SUPPORTED | matched=True via POM <url>/<scm> -> https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java |
| Aspose.Cells-FOSS-for-Python | python | SUPPORTED | SUPPORTED | matched=True via PyPI project_urls -> https://github.com/aspose-cells-foss/aspose-cells-python.git |
| Aspose.Cells-FOSS-for-Rust | rust | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Cells-FOSS-for-TypeScript | typescript | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Email-FOSS-for-.Net | net | SUPPORTED | UNRESOLVED | **FLIPPED**: NuGet registration catalogEntry projectUrl, else licenseUrl -> https://www.nuget.org/packages/Aspose.Email.Foss/26.7.0/license; matched=False |
| Aspose.Email-FOSS-for-Cpp | cpp | UNRESOLVED | UNRESOLVED | n/a: C++ has no registry (UNRESOLVED registry-less; unchanged) |
| Aspose.Email-FOSS-for-Python | python | SUPPORTED | SUPPORTED | matched=True via PyPI project_urls -> https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Python |
| Aspose.Font-FOSS-for-Python | python | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.GIS.FOSS-for-.Net | net | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.HTML-FOSS-for-Python | python | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Imaging-FOSS-for-.NET | net | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Note-FOSS-for-Python | python | SUPPORTED | SUPPORTED | matched=True via PyPI project_urls -> https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python |
| Aspose.Page-FOSS-for-Python | python | SUPPORTED | UNRESOLVED | **FLIPPED**: PyPI project_urls (Repository > Homepage > Source > Source Code > first value, else home_page) -> (none); matched=None |
| Aspose-PDF-FOSS-for-Go | go | SUPPORTED | SUPPORTED | matched=True via module path -> https://github.com/aspose-pdf-foss/aspose-pdf-foss-for-go |
| Aspose-PDF-FOSS-for-Python | python | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.PDF-FOSS-for-.NET | net | SUPPORTED | SUPPORTED | matched=True via NuGet registration catalogEntry projectUrl, else licenseUrl -> https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET |
| Aspose.PDF-FOSS-for-Cpp | cpp | UNRESOLVED | UNRESOLVED | n/a: C++ has no registry (UNRESOLVED registry-less; unchanged) |
| Aspose.PDF-FOSS-for-Java | java | SUPPORTED | SUPPORTED | matched=True via POM <url>/<scm> -> https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java |
| Aspose.PDF-FOSS-for-TypeScript | typescript | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.PSD-FOSS-for-.NET | net | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.PSD-FOSS-for-Python | python | no install fact | no install fact | n/a: no manifest/package identity at this revision (same under both) |
| Aspose.Slides-FOSS-for-.NET | net | SUPPORTED | SUPPORTED | matched=True via NuGet registration catalogEntry projectUrl, else licenseUrl -> https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET |
| Aspose.Slides-FOSS-for-Cpp | cpp | UNRESOLVED | UNRESOLVED | n/a: C++ has no registry (UNRESOLVED registry-less; unchanged) |
| Aspose.Slides-FOSS-for-Java | java | SUPPORTED | SUPPORTED | matched=True via POM <url>/<scm> -> https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java |
| Aspose.Slides-FOSS-for-Python | python | SUPPORTED | SUPPORTED | matched=True via PyPI project_urls -> https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python |
| Aspose.TeX-FOSS-for-Python | python | CONTRADICTED | CONTRADICTED | n/a: registry 404 (package absent); ownership never read; source-build fallback applies identically |
| Aspose.Words-FOSS-for-.NET | net | SUPPORTED | SUPPORTED | matched=True via NuGet registration catalogEntry projectUrl, else licenseUrl -> https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET |
| Aspose.Words-FOSS-for-Python | python | SUPPORTED | SUPPORTED | matched=True via PyPI project_urls -> https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-Python |

(SUPPORTED matches: PyPI uses the single URL the vendored adapter selects; Maven reads the artifact's POM; Cells-FOSS-for-Python
matched only because the registry URL `aspose-cells-python.git` is followed through GitHub's rename redirect once.)

## The four flips: real registry/upstream defect, or rule too strict?

### 1. Aspose.3D-FOSS-for-.NET and 2. Aspose.Email-FOSS-for-.Net (NuGet): rule too strict, an adapter gap

NuGet's registration `catalogEntry.projectUrl` is empty for both packages, so the vendored adapter
(`_vendor/aspose_extraction/package_registries/nuget.py`: `entry.get("projectUrl") or entry.get("licenseUrl")`) falls back to
`licenseUrl`: `https://www.nuget.org/packages/Aspose.3D.FOSS/26.1.0/license` (and `.../Aspose.Email.Foss/26.7.0/license`).
That is not a repository URL, and the evidence text "project URLs point at another repository" is misleading: the registry names no
project URL at all. Both packages do declare their source in the nuspec / catalog leaf `<repository>` element, which the adapter
never reads, and it is exact and commit-pinned:

- Aspose.3D.FOSS 26.1.0: `<repository type="git" url="https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET" commit="71581fddee6e661b330b3e4f45824b6cb7a561fa" />` (the commit exists in the repo, dated 2026-06-22, the day NuGet published).
- Aspose.Email.Foss 26.7.0: `<repository type="git" url="https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-.NET" branch="refs/heads/main" commit="a8999e259143a9ffc660086b34a7f39516da29f5" />` (the commit exists in the repo).

The four NuGet repos that stayed SUPPORTED (Cells, PDF, Slides, Words) carry a `projectUrl` as well as `<repository>`.
Not an upstream defect, no issue needed. The fix is in the adapter: read the catalog leaf (`catalogEntry["@id"]`, field
`repository.url`, and `repository.commit` for a stronger check) or the flatcontainer `.nuspec`, and stop treating `licenseUrl` as a
project URL. Both would then be SUPPORTED with strong ownership (git URL plus a commit that exists in this repository).

### 3. Aspose.3D-FOSS-for-Python (PyPI): genuine upstream metadata defect (dead homepage), weakly corroborated

PyPI `aspose-3d-foss` 26.1.0 (only upload, 2026-08-29, author "Aspose"): `project_urls = {'Homepage':
'https://github.com/aspose-3d/Aspose.3D-for-Python'}`, `home_page` the same. That GitHub repository returns 404 (the org
`github.com/aspose-3d` exists; there is no rename redirect). The value is copied from this repository's own `setup.py`
(`url="https://github.com/aspose-3d/Aspose.3D-for-Python"`), so the defect is in the repo's manifest: it names a repository that
does not exist. Candidate upstream issue: "setup.py `url` points to the non-existent aspose-3d/Aspose.3D-for-Python; set it to
https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python and republish". The rule is right to refuse a URL naming another
repository, but the registry record is otherwise identical to the manifest (name, version 26.1.0, description, author "Aspose",
python_requires, the URL string), so a "registry metadata equals the manifest at HEAD" corroboration would hold.

### 4. Aspose.Page-FOSS-for-Python (PyPI): genuine upstream metadata gap, weakly corroborated

PyPI `aspose-page-foss` 26.9.0 (one wheel, uploaded 2026-09-18; repo created 2026-05-19): `project_urls = null`, `home_page = null`,
author null, no classifiers. `pyproject.toml` has no `[project.urls]`. Nothing in the registry points anywhere, so ownership is
"no corroboration", not a mismatch. Candidate upstream issue: add `[project.urls] Repository/Homepage` and republish. Weak
corroborators that hold: registry `summary` "Aspose.Page FOSS for Python" equals the pyproject description; `requires_python
>=3.10` equals the manifest; `requires_dist` (`skia-python` plus the three test extras) equals the manifest dependencies; the name
is the `-foss` name of this repo's organisation; the first upload is after the repository's creation. (The code comment that
motivated the rule names PyPI `aspose-page`, a different commercial project; `aspose-page-foss` is a different name.)

## Other observations on the rule's implementation

- `observe()` compares only the single `project_url` the vendored adapter picked (PyPI: Repository, else Homepage, Source, Source
  Code, else the first value, else `home_page`); the vendored probe's own corroboration checks every URL. No cohort repository is
  affected today (all six matched PyPI repos expose Repository or Homepage = the repo), but a package whose Homepage is a docs site and
  whose `Source` is the repo would be refused.
- Maven records do have a source URL (POM `<url>`/`<scm>`); all five Java repositories matched. "Maven without source URL" did not
  materialise here.
- Aspose.Cells-FOSS-for-Python is SUPPORTED only through a live GitHub rename redirect (`aspose-cells-python.git` ->
  Aspose.Cells-FOSS-for-Python); GitHub unreachable at run time would flip it to UNRESOLVED and BC-02 blocked. Worth recording the
  redirect target as a probe record.
- Go matches are structural (the module path is the repo path), so they cannot fail.

## Recommendation

1. Keep the rule (it correctly refuses a name another project could own) but fix the evidence it reads. Highest value, no policy
   weakening: make the NuGet adapter read the catalog-leaf/nuspec `repository.url` and ignore `licenseUrl`. Restores
   Aspose.3D-FOSS-for-.NET and Aspose.Email-FOSS-for-.Net to SUPPORTED with commit-pinned proof (2 of 4 flips) and corrects the
   misleading "point at another repository" wording to "lists no URL".
2. For the two PyPI repos, do not relax to "URL absent is enough". Option: a `SUPPORTED_WEAK` tier admitted only when no registry
   URL names another existing repository OR the registry URL equals the URL the manifest itself declares, AND manifest name equals
   registry name, AND the registry's metadata equals the manifest at the revision (version or description, plus
   requires_python/dependencies), AND the first registry upload is after the repository's creation. Page-Python passes every
   condition (no URL; description, requires_python, deps equal; 2026-09-18 > 2026-05-19). 3D-Python passes through "registry URL ==
   manifest-declared URL" (name, version, description, author, python_requires equal; 2026-08-29 > 2026-01-20) despite the dead
   link. If SUPPORTED_WEAK is not wanted, leave both blocked.
3. Either way file two upstream issues: 3D-Python dead `url=`; Page-Python no project URLs. The NuGet pair needs none.
4. Add a regression fixture for the licenseUrl fallback (3D .NET): a missing projectUrl is "no URL", not a mismatch.

Affected: adapter fix = Aspose.3D-FOSS-for-.NET, Aspose.Email-FOSS-for-.Net; weak tier or upstream issues =
Aspose.3D-FOSS-for-Python, Aspose.Page-FOSS-for-Python. The other 32 are unchanged.

Raw data (not committed): G:/rp-facts/out2/ (facts per side, rows.json, observe.json, summary.jsonl, table.md).
