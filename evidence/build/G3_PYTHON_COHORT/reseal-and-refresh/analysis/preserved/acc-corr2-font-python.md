authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-font-python: aspose-font-foss/Aspose.Font-FOSS-for-Python (registry entry 24)

---
repository: aspose-font-foss/Aspose.Font-FOSS-for-Python
bundle: lfix/out/aspose-font-foss__Aspose.Font-FOSS-for-Python (snapshot copy acc2s2/bundles/aspose-font-foss__Aspose.Font-FOSS-for-Python)
bundle_manifest_sha256: 4dc30f505b49166da0d8aae77a180297fe98493653bcf76cba282930b834ce68
corrected_readme_sha256: 12711ea71d57276aca24fe48b500f4f6a91777a8acf271d1d14db0f5dc4a4335
original_readme_sha256: cbb4329cfb36178f19daa781fb6227f52c87c4644664cf41d6618bbc37fe3a47
source_revision: adf4885a3a5d4ddb7e30e737e83e72a44ee8dec6
live_head: adf4885a3a5d4ddb7e30e737e83e72a44ee8dec6
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: better (hunk 1) / neutral (hunk 2)
claims_checked: 9
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MINOR, section: Development, summary: drop the make build/test block (duplicates the uv commands already shown); keep Documentation & Resources}
blocking_findings:
  - {id: B1, category: other, section: Development, evidence: live Development block vs inserted block, summary: duplicate commands}
could_not_verify:
  - make build / make test not run (uv/make toolchain not installed; Makefile read instead)
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('MISSING_SECTION', 'missing_sections', 547), ('MISSING_INFO', 'add_dev_commands', 556)], patch 608 bytes (+12/-0 lines).
- Live head adf4885a equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

No At a Glance diagram in this README.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | MISSING_SECTION L547: `## Documentation & Resources` with `**[Changelog](CHANGELOG.md)** — release history.` and `**[Security policy](SECURITY.md)** — how to report a vulnerability.` | both files exist and are what the link text says | `CHANGELOG.md` (Keep-a-changelog style, "All notable public changes ... are recorded here"), `SECURITY.md` ("Reporting a Vulnerability", support@aspose.com) read in the clone; live README had no link to either (grep) | PASS (true, valuable) |
| 2 | heading placement | between `## MCP Server` and `## Development`; README has no `## Navigation` (live neither), so nothing to update | headings listed, rendered | PASS |
| 3 | MISSING_INFO L556: `To build and run the tests from a clone, run:` + `make build` / `make test` | Makefile targets exist | Makefile: `test:` runs `uv run python -m pytest tests/ -v`; `build:` runs `UV_CACHE_DIR=... uv run --with build python -m build` | PASS (true) |
| 4 | redundancy of hunk 3 | already documented? | live `## Development` (four lines above) already shows `uv run python -m pytest tests/ -q` and `uv run --with build python -m build`, the same two operations | FAIL (duplicate, introduced; also appended after the paragraph, `make` is not a default on Windows) |
| 5 | relative links CHANGELOG.md, SECURITY.md | resolve | files in the clone tree | PASS |

## 5. Live comparison

- ADDS: Documentation & Resources section (2 true links, valuable); make-based command block (true, duplicate).
- DROPS: none. CHANGES: none.
- NET: better (hunk 1) / neutral (hunk 2).
- Inherited and unchanged (lane reports them, none introduced): L539 `pip install "aspose-font[mcp]"` while PyPI `aspose-font` returns 404 (`curl https://pypi.org/pypi/aspose-font/json` -> 404); `docs/one_command_web_optimizer.md` (L518) is missing in the clone; three fences without a language. The earlier bundle's contradiction (new "not published" text next to the install line) is gone: this bundle no longer adds an Installation section.

## 6. Verdict

FIX_REQUIRED, MINOR. Hunk 1 is PUSHABLE as is. Drop hunk 2 (duplicate of the Development block above it).
