authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-pdf-go: aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (registry entry 30 (owner-table #29))

---
repository: aspose-pdf-foss/Aspose-PDF-FOSS-for-Go
bundle: lfix/out/aspose-pdf-foss__Aspose-PDF-FOSS-for-Go (snapshot copy acc2s2/bundles/aspose-pdf-foss__Aspose-PDF-FOSS-for-Go)
bundle_manifest_sha256: b1636d66502d7a5e5865abd3564fd9972051bfdc9464444b3eeb346a7209dd5c
corrected_readme_sha256: a2caba87a3ca840ff69060f157ba2ae6753a186377f9bea60e25dc1d1ccb46ba
original_readme_sha256: ce344171403525e4256048c0248bd7ea036c1b679ed02786095a71badb85ce90
source_revision: cdf43df10c8c565ecaa978428b1fe66ad6685f8d
live_head: cdf43df10c8c565ecaa978428b1fe66ad6685f8d
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: mixed
claims_checked: 7
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MAJOR(lane)/MINOR(PR), section: Development and Testing, summary: delete 'Releases run through the lint workflow'; fix renderer.py L704-708 fallback}
blocking_findings:
  - {id: B1, category: false_claim, section: Development and Testing, evidence: .github/workflows/lint.yml (golangci-lint only); GitHub releases authored by a person, summary: introduced false release claim}
could_not_verify:
  - hosted github.com Mermaid rendering
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 40), ('MISSING_INFO', 'add_dev_commands', 1024)], patch 3513 bytes (+32/-25 lines).
- Live head cdf43df1 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 32 HTML foreignObject labels, clipped in fonts {'Arial': 4, 'Verdana': 16, 'Tahoma': 2, 'Segoe UI': 3, 'Georgia': 8} (lane's own `check_entry`: 132 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose-PDF-FOSS-for-Go.live.0.png` and `acc2s2/png/Aspose-PDF-FOSS-for-Go.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L40) | same labels/edges, horizontal, not clipped | own parser (24 nodes, 5 subgraphs: two capability columns of 7); rendered 4 releases x 5 fonts; PNG viewed | PASS |
| 2 | add_dev_commands L1024, sentence A: `The [test workflow](.github/workflows/test.yml) runs across os (ubuntu-latest, windows-latest, macos-latest).` | CI matrix | `test.yml` job `test`, `matrix.os: [ubuntu-latest, windows-latest, macos-latest]` | PASS (true; the live README already links the workflow through its badge) |
| 3 | sentence B: `Releases run through the [lint workflow](.github/workflows/lint.yml).` | releases run through lint.yml | `.github/workflows/` = `lint.yml` (golangci-lint on push/PR) and `test.yml` only; no release job anywhere; the 3 GitHub releases (v0.8.0, v0.8.1, v0.9.0) were created by a person (author `kaferi`), and neither workflow has a release or tag trigger | FAIL (introduced, false) |
| 4 | links `test.yml`, `lint.yml` | resolve | exist in the clone | PASS |

Root cause of sentence B: `renderer.py` L704-708 falls back to `workflows[0]` (here `lint.yml`, the first workflow in the fact's evidence list) when no workflow file name contains `publish`/`release`, and asserts a release path.

## 5. Live comparison

- ADDS: horizontal diagram (better, the live one was 3269 px wide, clipped in 5 fonts); a true CI OS-matrix sentence; one FALSE sentence.
- DROPS: none. CHANGES: Mermaid body only.
- NET: mixed.
- Diagram note: two capability columns, 24 boxes, natural size 1685 x 1641 px; readable (0.49 scale in an 830 px column, live was 0.25). Column order c1.. left to right matches the live reading order by declaring the right column first (mermaid reverses sibling clusters; 12.1.0 may swap them: cosmetic).
- Governance note: `allowed` BC-07 +6 under R7 (live 23 -> 29).
- Inherited, untouched: `#encryption-and-signing` anchor not found (L313 live), `wrapper around a native library` negation (L19).

## 6. Verdict

FIX_REQUIRED, MINOR for the PR (delete the second sentence; the first is optional). Diagram hunk PUSHABLE alone. Generator-wide defect: see the JMAP records.
