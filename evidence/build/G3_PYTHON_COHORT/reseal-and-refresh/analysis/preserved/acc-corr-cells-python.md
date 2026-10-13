authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-cells-python: Aspose.Cells-FOSS-for-Python (live head 952317ca)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-cells-foss__Aspose.Cells-FOSS-for-Python/`.
Clone: `scratchpad/acccorr/clones/Aspose.Cells-FOSS-for-Python`, HEAD 952317ca == bundle `source_revision`.

**Verdict: FIX_REQUIRED, minor_major MINOR. Value is low: the patch mostly duplicates information the README already states; push only after the skia-python omission is fixed, or skip this repo.**

## 1. Edit confinement
- `README.original.md` == live blob (21bf0e40...); corrected sha matches `corrections.json`.
- Replay of the one `MISSING_SECTION` edit reproduces `README.md`; difflib: one insert hunk (15 lines), 0 deletions. No maintainer text altered or lost. LF-only.
- Placement: after the whole Installation section including its `### PDF support` subsection, before `## Quick start`. Correct (not spliced into the subsection).

## 2. Claim checks
| # | Claim | Check | Result |
|---|---|---|---|
| 1 | No Dependencies section | headings: Features, Installation, Quick start, Supported formats, Scope, Examples and API, Development, License | PASS |
| 2 | Required: `olefile>=0.46`, `pycryptodome>=3.15.0` | `pyproject.toml` `dependencies`; PyPI `aspose-cells-foss` 26.10.0 `requires_dist` (`https://pypi.org/pypi/aspose-cells-foss/json`) identical | PASS |
| 3 | Dev extra: `pytest>=7.0.0`, `pytest-cov>=4.0.0` | `pyproject.toml [project.optional-dependencies] dev`; PyPI requires_dist `extra == "dev"` | PASS |
| 4 | Python 3.10+ cited as `` `python_requires=">=3.10"` in `pyproject.toml` `` | pyproject.toml L10 is `requires-python = ">=3.10"`; `python_requires` appears nowhere in the repo's pyproject (it is the setup.py keyword) | FAIL-minor (wrong key quoted) |
| 5 | Completeness: optional PDF renderer | README L37-45 ("PDF support uses `skia-python`, not installed by the core package"), Scope bullet ("optional `skia-python` renderer"), `requirements.txt` L5 `skia-python>=144.0.post2,<145` | OMITTED: the new section has no Optional Dependencies, so a reader of Dependencies never learns of skia-python; siblings (Font-Python patch, template) have an Optional subsection |
| 6 | Redundancy | Installation L35-36 already states "requires Python 3.10 or later. Its core runtime dependencies are `pycryptodome>=3.15.0` and `olefile>=0.46`" | The new Required and "Native and System Requirements" sub-sections repeat this verbatim; only Development Dependencies is new information (and the Development section already says `pip install -e ".[dev]"`) |
| 7 | Navigation | README has no Navigation section | n/a |

## 3. Render and style
- One H1, no duplicate headings, fences closed, no links inserted.
- This README deliberately uses its own compact shape (Features, Installation, Quick start, Supported formats, Scope ...), not the ten-section template. A template-shaped three-subsection Dependencies block with an almost empty "Native and System Requirements" (a Python version only) would read to this maintainer as redundant noise. Tone is otherwise consistent.

## 4. Fixes
| id | kind | severity | fix |
|---|---|---|---|
| F1 | code_change (extractor) | MINOR | Python extractor: surface documented-but-undeclared optional dependencies (skia-python in README + `requirements.txt`) as `dependency:optional.*` facts so the generated section has an "Optional Dependencies" subsection |
| F2 | redraw/template | MINOR | Cite `requires-python` (the key that exists) instead of `python_requires` |
| F3 | policy | MINOR | Redundancy gate: when the live Installation already carries the same dependency facts, record the Dependencies section as covered (disposition) and do not insert a duplicate. This repo is the clearest case |

could_not_verify: nothing in the patch is unverifiable; the lane's other findings (RELEASE_NOTES.md link, failing example 5) were not reviewed here.
confidence: high.
