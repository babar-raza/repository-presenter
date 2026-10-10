authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
---
repository: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python
bundle_hash: 7699b13a21e7c82576183897bbe2d5102e39302a15696c112ae587c06c155e87
readme_sha256: a6ade8608345fcf90c056316c99e5970aec9d8a88a9c3667bba632ad3cca3ea2
source_revision: 06eca5c01e13ed6d59a640f1cf330c1c5a57d151
live_head: 06eca5c01e13ed6d59a640f1cf330c1c5a57d151
reviewed_at: 2026-10-10T15:45:00Z
verdict: DO_NOT_PROPOSE
minor_major: MAJOR
net_vs_live: worse
confidence: high
reviewer: claude-sonnet-5-5, lane L-verifier (did not author, reseal or repair the candidate)
claims_checked: 17
claims_failed: 4
forbidden_wording_hits: 0
could_not_verify:
  - "full test suite (646 tests per an earlier review): started, 55% passed with no failure, then stalled and was stopped; not completed here"
  - "custom Renderer subclass behaviour beyond Barcode.render(renderer) accepting a Renderer instance"
  - "Enterprise product page python-net is the right product for the barcode library (vendor-asserted by live README)"
fixes:
  - {id: F1, kind: code_change, severity: MAJOR, section: "Key Capabilities / At a Glance / Installation / Development and Testing", summary: "the live-README floor: dropped verified live content (code sets, modulo-43, allow_check_digit_input, Outputs subgraph, pytest/ruff dev dependencies and the install-and-test commands, py.typed) must not be superseded; a reseal on current code reproduces the loss (REQ-DSP-02)"}
  - {id: F2, kind: code_change, severity: MAJOR, section: "API Reference", summary: "the public-surface table lists the same type under up to three names (aspose_barcode_foss.X, options.X, renderers.X) and reports 51 types for 26 exported classes; dedupe by canonical defining location (contract row 14 already requires it)"}
  - {id: F3, kind: redraw, severity: MINOR, section: "Development and Testing / Documentation & Resources", summary: "garbled prose ('member AUTO', 'member data', 'classes like AUTO, H') and a test-file count that includes fixtures; redraw"}
  - {id: F4, kind: data_change, severity: MINOR, section: "Scope and Limitations", summary: "restore the Enterprise Edition paragraph and link (live has products.aspose.com/barcode/python-net/, HTTP 200); the pipeline deferred it as ENTERPRISE_NO_VERIFIED_TARGET because the platform target is ambiguous"}
blocking_findings:
  - {id: B1, category: dropped_live_content, section: "Installation / Development and Testing", evidence: "diff -u live-README.md candidate README.md", summary: "live Development Dependencies (pytest>=8.0, ruff>=0.15.7) and the 'pip install -e . pytest ruff && pytest' block are gone; the section now says the suite 'verifies that the package behaves as expected' with no command"}
  - {id: B2, category: dropped_live_content, section: "Scope and Limitations", evidence: "live README lines 'For PDF rendering and additional symbologies, see [Aspose.BarCode for Python - Enterprise Edition](https://products.aspose.com/barcode/python-net/)'; curl -> 200", summary: "Enterprise Edition relationship paragraph and link dropped"}
  - {id: B3, category: dropped_live_content, section: "At a Glance / Key Capabilities", evidence: "review.json advisory F01/F02 (S6 and S7), diff -u", summary: "diagram lost the specific symbologies and the Outputs subgraph; capabilities lost Code Set A/B/C switching, Code128Options.encode_mode, the modulo-43 check, code39ext(), allow_check_digit_input; demoted reviewer findings F01, F02, F05, F06 are all TRUE"}
  - {id: B4, category: false_claim, section: "API Reference / Documentation & Resources", evidence: "python: len([n for n in aspose_barcode_foss.__all__ if inspect.isclass(getattr(m,n))]) -> 26; README says 'verified public surface has 51 types' twice", summary: "51 types is inflated by listing options.X / exceptions.X / renderers.X aliases of the same classes"}
  - {id: B5, category: false_claim, section: "Documentation & Resources", evidence: "enum members live in QrErrorCorrectionLevel / QrEncodeMode; 'data' is an attribute of the artifact", summary: "'classes like AUTO, H, and methods such as data, render' is wrong: AUTO and H are enum members"}
  - {id: B6, category: dangling_prose, section: "Development and Testing", evidence: "mech.py garble member: 'member AUTO, member H, member data, member render, member to_png, member to_svg'", summary: "garbled sentence from a dropped list"}
  - {id: B7, category: false_claim, section: "Development and Testing", evidence: "git ls-files tests | wc -l -> 48; of which test_*.py -> 37; the rest are __init__.py, conftest.py and encoding/vectors/*.py", summary: "'The suite covers 48 test files under tests/' is misleading (37 test files)"}
---

# 1 Bundle facts

- Bundle `candidates/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/06eca5c0.../`.
  manifest state READY_FOR_PROPOSAL; blocking_failures empty; `adopted.classification` factual,
  adopted 2026-10-09T14:57:27Z (PR #305 re-seal). README sha256 equals the manifest value
  (hash check passed). No-op proof recorded: byte_identical, fresh_process, 0 provider calls.
- validation.json: BC-01..BC-12 all PASS. Two advisories: ENTERPRISE_NO_VERIFIED_TARGET (the
  Enterprise paragraph deferred) and "the rewrite no longer names Barcode.render(),
  Code128Options.encode_mode, allow_check_digit_input, code39ext(), generate(symbology, data)".
- review.json: `verdict` ACCEPT, `verdict_as_returned` REJECT_PRESENTATION, zero `findings`,
  nine `advisory` entries (the demoted findings). Ruling on each:
  - F01 (S6 and S7) At a Glance lost the specific diagram nodes and the Outputs subgraph: TRUE
    (live diagram has them).
  - F02 (S6, S7) Key Capabilities lost code-set switching, modulo-43, code39ext, allow_check_digit_input: TRUE.
  - F04 (S6) ECI/GS1 limitation bullets lost `EciHelper`/`Gs1Helper` names: TRUE but minor (the
    helpers are internal; the bullet is still correct).
  - F05 (S6, S7) Development and Testing lost the clone-and-test commands: TRUE.
  - F06 (S7) '48 test files' and 'member AUTO ...': TRUE (see B6, B7).
  - F04 (S7) Detailed Member Reference stubs for six functions: low value, no false statement.
- examples.json: 6 receipts, all EXECUTED, `build_verified: true`.
- Exported API (clone, installed in a clean venv): 35 names in `__all__`: 26 classes, 9 functions.

# 2 Live comparison

Live README (262 lines, upstream head equal to the sealed revision) is already a complete
template README (Navigation, At a Glance, ..., Development and Testing, License; one mermaid fence).

ADDS (candidate only):
- Python 3.12+ badge: TRUE (pyproject classifiers 3.12 and 3.13, `requires-python >=3.12`).
- Installation line "The package declares python_requires as >=3.12": TRUE.
- Examples promoted: the RenderOptions example is the flagship Additional Example (all six
  snippets run): fine.
- "Support custom renderers" capability: TRUE (`Barcode.render(renderer, options=...)`).
- A duplicated alias API table: FALSE/inflated (B4).

DROPS (live only), valuable unless stated:
- Factual opening (pure-Python, deterministic, standards-compliant, no system dependencies
  beyond Pillow): valuable; replaced by a generic paragraph.
- At a Glance specifics and Outputs subgraph: valuable.
- Key Capabilities specifics (Code Sets A/B/C, modulo-43, `code39ext()`, `allow_check_digit_input`,
  QR error-correction/encoding-mode types, RenderOptions detail incl. quiet zone, colors,
  transparent background): valuable.
- Installation: the distribution/import name line and the `py.typed` statement: valuable.
- Development Dependencies (pytest >=8.0, ruff >=0.15.7) and the install-and-test commands: valuable.
- Enterprise Edition paragraph and link: valuable, required by the contract whenever a target resolves.
- Core API vs Internal table split and per-class one-line explanations with member names
  (`encode_mode`, `add_check_digit`, `allow_check_digit_input`): valuable; candidate has
  generic descriptions.
CHANGES: Installation block kept (`pip install .`), wording reworded ("verified against this
revision" is internal narration; see 4). Scope bullets repeat "PDF rendering is not
implemented" in three of four bullets (duplication).

NET: worse. Every drop above is verified, valuable content; the additions are small.

# 3 Claim checks

| # | Claim (README line) | How checked | Result |
|---|---|---|---|
| 1 | Install from a source checkout with `pip install .` (L51-55) | clean venv `pip install ./clone`; `import aspose_barcode_foss` | PASS |
| 2 | "not yet published on PyPI" (L49) | `curl https://pypi.org/pypi/aspose-barcode-foss/json` -> 404 | PASS |
| 3 | `python_requires >=3.12`, badge 3.12+ (L3, L57, L67) | pyproject.toml | PASS |
| 4 | Only runtime dependency Pillow>=10.1.0 (L63) | pyproject.toml `dependencies` | PASS |
| 5 | Quick Start and all 5 further snippets (L71-145) | extracted and run in the venv, 6 of 6 exit 0 | PASS |
| 6 | PDF rendering not implemented, raises NotImplementedError (L257) | `code128('x').to_pdf()` -> NotImplementedError | PASS |
| 7 | ECI normalization/validation and GS1 parsing not implemented, `EncodeOptions` exposes fields (L259) | `_internal/standards/eci.py`, `gs1.py` raise NotImplementedError; `eci_assignment_number`, `gs1_enabled` in `_internal/models/options.py` | PASS |
| 8 | QR versions 1-40 (L41) | `qr('hi', encode=QrOptions(version=v))`: 1 and 40 ok, 41 InvalidInputError | PASS |
| 9 | Exception types BarcodeError, EncodingError, RenderingError, SymbologyNotFoundError (L45) | `__all__` | PASS |
| 10 | MIT license, root LICENSE (L271) | `gh api repos/...` `.license.spdx_id` MIT; LICENSE at root | PASS |
| 11 | External and relative links (26) | mech.py --net: all external 200; `examples/`, `LICENSE`, `examples/README.md` exist | PASS |
| 12 | `Barcode.render(renderer, options=...)` accepts a Renderer (L40) | signature and example 6 | PASS |
| 13 | "The verified public surface has 51 types" (L153, L251) | 26 exported classes; the table has `options.X`, `exceptions.X`, `renderers.X` duplicates | FAIL (introduced) |
| 14 | "classes like AUTO, H, and methods such as data, render" (L251) | `QrErrorCorrectionLevel.H`, `QrEncodeMode.AUTO` are enum members | FAIL (introduced) |
| 15 | "The suite covers 48 test files under tests/" (L267) | 48 tracked files; 37 `test_*.py` | MISLEADING (introduced) |
| 16 | "member AUTO, member H, member data, member render ..." (L265) | mech.py garble; no sense in context | FAIL (introduced, prose) |
| 17 | Quick Start comment `# -> str` / `# -> bytes` | `to_svg()` str, `to_png()` bytes | PASS |

Four FAIL or MISLEADING (13-16), all introduced; item 13 appears in two places.

# 4 Mechanical and wording results

mech.py: one H1; all 12 standard sections, in order, no extra; one mermaid fence and At a Glance
contains only it; no fence without a language; no forbidden wording ("commercial edition",
"paid version", bridge phrases, forum.aspose.com: none); `Enterprise Edition` occurs 0 times
(the live README links it); garble hits as in B5, B6; duplicate link targets only
`#api-reference` and `LICENSE`. Narration: "verified against this revision" in Installation
is internal narration the contract bans ("source revisions ... isolated-build conditions").
The prose rewrite contains no dangling lead-in, but Development and Testing ends without any
command.

# 5 Omitted information in the clone

- `py.typed` marker and "Typing :: Typed" classifier (live README mentions it).
- `code39ext()` helper, `allow_check_digit_input`, QR `version`/`mask`, `Code128EncodeMode` members.
- How to run ruff and pytest (dev group in pyproject) (live carries it).
- `examples/README.md` table (still linked).
- No `docs/`, CHANGELOG, CONTRIBUTING or SECURITY in the repository; no GitHub releases
  (`gh api .../releases` -> 0); no CLI.

# 6 Drafted upstream issues (text only, nothing filed)

None worth filing: install works, the six README examples run, license is detected as MIT.
Only a cosmetic point: `[project.urls]` use the casing `Aspose.Barcode-FOSS-for-Python` while
the repository is `Aspose.BarCode-FOSS-for-Python`; GitHub is case-insensitive, so low value.
Possible, unreproduced: none.

# 7 Verdict and reasons

DO_NOT_PROPOSE, confidence high. The live README is already template-conformant and richer; the
candidate has four introduced false or misleading statements (51 types, enum members called
classes, the 48-file count, garbled "member" prose), drops the Enterprise Edition paragraph and
the development commands, and four demoted reviewer findings that were true. Merging it would
make the repository worse. The structural cause is the pipeline: a reseal on today's code
reproduces the content loss (fix F1 and F2 need a code change), so this is MAJOR. What would let
it be reconsidered: a live-README content floor that stops valuable verified units from being
superseded, an API-surface dedupe by canonical defining location, an enterprise-target data
entry for this repository, then a reseal; and the acceptance protocol re-run.

Not verified: see `could_not_verify`.
