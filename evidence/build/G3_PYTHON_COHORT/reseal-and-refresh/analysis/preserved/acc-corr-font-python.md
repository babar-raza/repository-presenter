authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-font-python: Aspose.Font-FOSS-for-Python (live head adf4885a)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-font-foss__Aspose.Font-FOSS-for-Python/`.
Clone: `scratchpad/acccorr/clones/Aspose.Font-FOSS-for-Python`, HEAD adf4885a == bundle `source_revision` (GitHub "Release 26.10.2").

**Verdict: FIX_REQUIRED, minor_major MAJOR (the patch leaves the README self-contradictory; fixing that needs a new detector or a hand edit). Do not push as is.** The inserted facts are right; the surrounding README is not reconciled with them.

## 1. Edit confinement
- `README.original.md` == live blob (cbb4329c...); corrected sha matches `corrections.json`.
- Replay of the two `MISSING_SECTION` edits (both at line 33) reproduces `README.md`; difflib: one contiguous insert hunk (37 lines), 0 deletions. No maintainer text altered or lost. LF-only.
- Placement: after the "Who Is This For?" table, before "Quick Start: Three Buyer Workflows". Reasonable for this off-template README.

## 2. Claim checks
| # | Claim | Check | Result |
|---|---|---|---|
| 1 | No Installation/Dependencies section in live README | headings; only install text anywhere is L539 `pip install "aspose-font[mcp]"` | PASS |
| 2 | "`aspose-font` is not yet published on PyPI" | `https://pypi.org/pypi/aspose-font/json` 404; `https://pypi.org/pypi/aspose-font-foss/json` 404; `https://pypi.org/simple/aspose-font/` 404. (Sibling Aspose.TeX README says the same of itself.) GitHub has Releases 26.10.2... but with zero assets | PASS |
| 3 | `git clone ... && cd ... && pip install .` works | fresh venv, `pip install ./copy-of-clone`: succeeded; `python -I -c "import aspose_font"` OK; console script `aspose-font --help` prints usage | PASS |
| 4 | "verified against this revision" | internal narration (source revision/verification) in public prose; the acceptance protocol treats this as blocking wording | FAIL (introduced) |
| 5 | Consistency with the rest of the README | L539 (MCP Server): `pip install "aspose-font[mcp]"` + `python -m aspose_font.mcp`. With the package not on PyPI that command fails today, and it now directly contradicts the inserted Installation text | FAIL: inherited false command, plus a new contradiction created by the patch; not fixed, not even reported in `unapplied_findings` |
| 6 | Python floor: `` `python_requires` as `>=3.10` `` / `` `python_requires=">=3.10"` in `pyproject.toml` `` | pyproject L23 is `requires-python = ">=3.10"`; neither pyproject nor setup.py contains `python_requires` | FAIL-minor (wrong key) |
| 7 | "No required third-party package dependencies; no `project.dependencies` declared" | pyproject has no `dependencies` key; AST scan of all `src/**/*.py` imports: only non-stdlib import is `mcp` (in `src/aspose_font/mcp.py`) | PASS |
| 8 | Optional: `mcp>=1.0` (extra `mcp`) | pyproject `[project.optional-dependencies] mcp` | PASS |
| 9 | Dev: `build>=1.2`, `pytest>=7.4`, `ruff>=0.4` (extra `dev`) | pyproject `dev` extra (note `[dependency-groups] dev` has `pytest>=9.0.2`, which the README Development section's `uv run` actually uses; not mentioned) | PASS (incomplete nuance) |
| 10 | Completeness | `src/aspose_font/_brotli/vendor/brotlihaxe.py` is vendored third-party code (package-data licence file); no mention | advisory |

## 3. Render and style
- One H1, no duplicate headings, fences closed, bash fences have a language.
- Tone: structure matches template headings; phrase "in `pyproject.toml`, no `project.dependencies` is declared" is evidence-citation style but acceptable (siblings use similar). The phrase in item 4 is not acceptable.
- Would a maintainer accept? Probably after reading, they would say: why does the PR say "verified against this revision", and why does the MCP section still tell people to `pip install` from PyPI? Also some owners will not want to publish "not yet published on PyPI" - a policy point for the authorization step, not a defect.

## 4. Reported-not-edited findings I confirmed
- Broken link `docs/one_command_web_optimizer.md` (L518 area): the clone has no `docs/` directory. Confirmed. Left in the PR; a respectful PR could at least note it.
- Example L128-141 (`VariableInstanceBuilder.build_package(... instance_names=...)`): reproduced `TypeError: unexpected keyword argument 'instance_names'` in a throwaway venv with the testdata path. Example L295-418: reproduced `KeyError: 'subset'`. Examples L40-52, L85-99, L260-276 run. (Bare `Roboto-VariableFont...ttf` file names in the snippets are placeholders; the lane's results hold once the path is supplied.)

## 5. Fixes
| id | kind | severity | fix |
|---|---|---|---|
| F1 | code_change | MAJOR | New deterministic detector `unpublished_install_command`: when the registry returns 404 for a package the README tells readers to `pip install`, rewrite that command to the verified source route (`pip install ".[mcp]"` from a checkout) or report it as a blocking finding for the same PR. Needed so inserting "not published" never coexists with an install-from-PyPI command (L539) |
| F2 | redraw/template | MINOR | Remove "verified against this revision" (and generally forbid verification narration in inserted text) |
| F3 | redraw/template | MINOR | Quote `requires-python` / say "Requires Python 3.10 or later" |
| F4 | advisory | - | Mention vendored Brotli (third-party notice), the `[dependency-groups]` vs extras split |

could_not_verify: whether the owners are about to publish to PyPI (the statement is true today).
confidence: high.
