authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-imaging-net: aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET (registry entry 27)

---
repository: aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET
bundle: lfix/out/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET (snapshot copy acc2s2/bundles/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET)
bundle_manifest_sha256: 01786c34bb5641bc9b41066deabc9d9d78f5163619c07c3acc1c9b09e79ddbae
corrected_readme_sha256: 1d45438369395c666be65590f7c0e2d94d20d5d4eaf406b1d97549792a402da6
original_readme_sha256: 30f377be8f7ef7462f932fb9b5c32dbac7c69e5140eea49176d22cf89221670f
source_revision: 6ebb2091ad016a46489bef65eaad0f1eb9843e1a
live_head: 6ebb2091ad016a46489bef65eaad0f1eb9843e1a
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: better
claims_checked: 7
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MINOR, section: Development and Testing, summary: drop or reword the CI-matrix sentence and the duplicate dotnet test block}
blocking_findings:
  - {id: B1, category: other, section: Development and Testing, evidence: live dotnet test line vs inserted block, summary: duplicated command, raw matrix key in prose}
could_not_verify:
  - dotnet test of the sln (no net9.0 runtime installed)
  - hosted github.com Mermaid rendering
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 31), ('MISSING_INFO', 'add_dev_commands', 295)], patch 2003 bytes (+22/-11 lines).
- Live head 6ebb2091 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 15 HTML foreignObject labels, clipped in fonts {'Arial': 4, 'Verdana': 11, 'Tahoma': 1, 'Georgia': 7} (lane's own `check_entry`: 33 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.Imaging-FOSS-for-.NET.live.0.png` and `acc2s2/png/Aspose.Imaging-FOSS-for-.NET.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L31) | same labels/edges, horizontal, not clipped | own parser; rendered 4 releases x 5 fonts; PNG viewed | PASS |
| 2 | add_dev_commands L295: `The [ci workflow](.github/workflows/ci.yml) runs across os (ubuntu-latest, windows-latest).` | CI matrix | `ci.yml` job `build-and-test`, `matrix.os: [ ubuntu-latest, windows-latest ]`; recent runs on 6ebb2091 green | PASS (true) |
| 3 | `dotnet build Aspose.Imaging.Foss.sln` | command works | `Aspose.Imaging.Foss.sln` lists both projects; ran it in a throw-away copy with SDK 10.0.401: 0 errors, 65 warnings | PASS |
| 4 | `dotnet test Aspose.Imaging.Foss.sln` | command works | tests target net9.0, only runtimes 8.0.21 and 10.0.x installed here | COULD_NOT_VERIFY (CI runs `dotnet test` on the same projects: green) |
| 5 | redundancy / placement | already documented? | live section already has `dotnet test tests/Aspose.Imaging.Foss.Tests/...csproj` and the `release.yml` sentence; the new block follows the contributor paragraph ("Adding a new format ...") and repeats the test command | FAIL (duplicate, detached; wording "runs across os (...)" is a raw matrix key) |

## 5. Live comparison

- ADDS: horizontal diagram (better); a true CI-matrix sentence (new fact: Windows is tested); a build+test block that partly repeats the live test command.
- DROPS: none. CHANGES: Mermaid body only.
- NET: better overall; the dev hunk is the weakest part.

## 6. Verdict

FIX_REQUIRED, MINOR (low severity). Diagram hunk PUSHABLE alone. Either drop the command block or reword to "CI builds and tests on Ubuntu and Windows" and keep only the sentence; as generated, the duplicate test command and raw `os (...)` wording read as machine text next to the maintainers' prose.
