authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-jmap-nodejs: aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js (registry entry 20)

---
repository: aspose-email-foss/Aspose.JMAP-FOSS-for-Node.js
bundle: lfix/out/aspose-email-foss__Aspose.JMAP-FOSS-for-Node.js (snapshot copy acc2s2/bundles/aspose-email-foss__Aspose.JMAP-FOSS-for-Node.js)
bundle_manifest_sha256: da332fdc1d81e1aa39239fb45df501a313baecd90087c64dd20de610a2dc0493
corrected_readme_sha256: 2ec53f835009ff5747c789439cda92fa92eeebd9123eb6252b658e3c179932b3
original_readme_sha256: 55438cb1efca00addae9f627557d8286be8d6846440bd6e7a3bfdb0be53fa540
source_revision: 93f22fb57ba83484d14af5af2017590a0f5bf55f
live_head: 93f22fb57ba83484d14af5af2017590a0f5bf55f
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
  - build/test commands not run for Node.js (no toolchain needed for the verdict)
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 34), ('MISSING_INFO', 'add_dev_commands', 192)], patch 2038 bytes (+16/-10 lines).
- Live head 93f22fb5 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 15 HTML foreignObject labels, clipped in fonts {'Verdana': 4, 'Georgia': 2} (lane's own `check_entry`: 51 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.JMAP-FOSS-for-Node.js.live.0.png` and `acc2s2/png/Aspose.JMAP-FOSS-for-Node.js.corr.0.png`.
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

- Note: this entry exists in the lane's current registry (44 entries) and is not in the owner table (43); reviewed so that no entry of the 15-29 window under the current registry is left unreviewed. `package.json` has only the script `test` = `node --test test/`; CI runs `npm test` only.

## 7. Verdict

FIX_REQUIRED, MINOR for this repository (drop the `add_dev_commands` hunk; the remaining diagram-only patch is PUSHABLE). The defect is generator-wide (renderer fallback), so the same hunk must not be pushed for any entry; fix kind `code_change` (MAJOR for the lane, one-hunk drop for the PR).
