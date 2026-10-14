authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-jmap-typescript: aspose-email-foss/Aspose.JMAP-FOSS-for-TypeScript (registry entry 23)

---
repository: aspose-email-foss/Aspose.JMAP-FOSS-for-TypeScript
bundle: lfix/out/aspose-email-foss__Aspose.JMAP-FOSS-for-TypeScript (snapshot copy acc2s2/bundles/aspose-email-foss__Aspose.JMAP-FOSS-for-TypeScript)
bundle_manifest_sha256: 6d41d6f947382683d3177188aec778bb0d14dcc4df0e80590435c86e5493f89e
corrected_readme_sha256: d62e9d5d68871ba81c5a74332410e144dcbd89b41ad201a58733394494e303da
original_readme_sha256: e2e680259027223004ce1b2c0caf9d00f174b2bbfb6dd9bb1b7df7f1b7d4bf38
source_revision: d8fdf9e8f3367424c3a900271eb3bd0b99c6195e
live_head: d8fdf9e8f3367424c3a900271eb3bd0b99c6195e
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: mixed
claims_checked: 7
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MAJOR(lane)/MINOR(PR), section: Development and Testing, summary: drop the false sentence 'Releases run through the ci workflow'; renderer.py L704-708 fallback must not assert a release workflow without a publish/release step}
blocking_findings:
  - {id: B1, category: false_claim, section: Development and Testing, evidence: .github/workflows/ci.yml (no release/publish step); registry 404; renderer.py L704-708, summary: introduced false release claim}
could_not_verify:
  - hosted github.com Mermaid rendering of the init directive (local render only)
  - build/test commands not run for TypeScript (no toolchain needed for the verdict)
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 34), ('MISSING_INFO', 'add_dev_commands', 200)], patch 2111 bytes (+22/-10 lines).
- Live head d8fdf9e8 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 15 HTML foreignObject labels, clipped in fonts {'Verdana': 4, 'Georgia': 2} (lane's own `check_entry`: 52 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.JMAP-FOSS-for-TypeScript.live.0.png` and `acc2s2/png/Aspose.JMAP-FOSS-for-TypeScript.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw | same labels/edges, horizontal, not clipped | own parser + rendered 4 mermaid releases x 5 fonts, PNG viewed | PASS |
| 2 | add_dev_commands: `Releases run through the [ci workflow](.github/workflows/ci.yml).` | releases run through the CI workflow | read `.github/workflows/ci.yml` in the clone; grep for release/publish/deploy; registry GETs (404); GitHub releases GET | FAIL (introduced, false) |
| 3 | link target `.github/workflows/ci.yml` | resolves | exists in the clone | PASS |
| 4 | no other text changed | confinement | replay + `git apply` | PASS |

## 5. Live comparison

- ADDS: a horizontal diagram (better than live: live vertical, clipped in wider fonts); one FALSE sentence about releases.
- DROPS: none.
- CHANGES: Mermaid body only.
- NET: mixed (diagram better; hunk 2 worse because it is false and the live README had no release claim).

## 6. Findings

- The inserted sentence `Releases run through the [ci workflow](.github/workflows/ci.yml).` is FALSE. `.github/workflows/` holds only `ci.yml` (name CI; triggers: push to main, pull_request, workflow_dispatch, no tag trigger; jobs `secret-scan` and `test`); no step releases, publishes, packs or deploys (grep for release, publish, deploy, upload, twine, `nuget push`, `cargo publish`, `npm publish` returns nothing). The registries list no package: NuGet `Aspose.JMAP.FOSS`, PyPI `aspose-jmap-foss`, crates.io `aspose-jmap-foss`, npm `aspose-jmap-foss` and `aspose-jmap-foss-ts`, Maven Central `com.aspose:aspose-jmap-foss`: HTTP 404 each (Go proxy: pseudo-version only, no tagged version). The repository's single GitHub release (tag v26.09, created 2026-09-26 13:50 by the account vs-aspose, in all eight JMAP repositories within four seconds) was not created by a workflow. Root cause: `components/readme/composition/renderer.py` L704-708, `chosen = release[0] if release else workflows[0]` falls back to the first workflow when no workflow file name contains `publish` or `release`, then states that releases run through it; the fact `build_test_asset:ci` only records the directory `.github/workflows/`. No validator sees it (`validate_candidate` introduced = []).

- Hunk 2 also adds `To build from a clone, run:` + `npm run build`: valid (`package.json` script `build` = `tsc`), but `npm test` already runs `tsc && node --test dist/test`; redundant.

## 7. Verdict

FIX_REQUIRED, MINOR for this repository (drop the `add_dev_commands` hunk; the remaining diagram-only patch is PUSHABLE). The defect is generator-wide (renderer fallback), so the same hunk must not be pushed for any entry; fix kind `code_change` (MAJOR for the lane, one-hunk drop for the PR).
