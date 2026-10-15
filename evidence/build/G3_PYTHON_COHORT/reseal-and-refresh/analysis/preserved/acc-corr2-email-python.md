authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-email-python: aspose-email-foss/Aspose.Email-FOSS-for-Python (registry entry 15)

---
repository: aspose-email-foss/Aspose.Email-FOSS-for-Python
bundle: lfix/out/aspose-email-foss__Aspose.Email-FOSS-for-Python (snapshot copy acc2s2/bundles/aspose-email-foss__Aspose.Email-FOSS-for-Python)
bundle_manifest_sha256: 9694d8c93d44b759dfc2196649ebd73dac247e5ed27c91a7d4643aef0b18b57e
corrected_readme_sha256: 115c8b54b721d3416a2513b5b613d36a97afe484e181cb3483ec7a8dfcf7fe9c
original_readme_sha256: 5c81ffa6954ec89f6b6872dd6d6429e13dbe45aafe1b8717eda332629ad7dfad
source_revision: 10a906b48c0c11005c4d93b524e4431901c9717c
live_head: 10a906b48c0c11005c4d93b524e4431901c9717c
reviewed_at: 2026-10-11 (PST, lane code e576d7ce)
verdict: FIX_REQUIRED
minor_major: MINOR
net_vs_live: better (diagram) / neutral (sentence)
claims_checked: 6
claims_failed: 1
reviewer: independent read-only reviewer (Sonnet 5.5); did not author the bundle
fixes:
  - {id: F1, kind: code_change, severity: MINOR, section: Development and Testing, summary: drop the duplicate CI-matrix sentence (live L402-403 already states it)}
blocking_findings:
  - {id: B1, category: other, section: Development and Testing, evidence: live README L402-403 vs inserted L411, summary: inserted sentence duplicates existing prose}
could_not_verify:
  - hosted github.com Mermaid rendering of the init directive (local render only)
---

## 1. Bundle facts

- kind=correction, state CORRECTION_READY, edits: [('DIAGRAM_FIX', 'at_a_glance_diagram', 31), ('MISSING_INFO', 'add_dev_commands', 406)], patch 2431 bytes (+18/-12 lines).
- Live head 10a906b4 equals `manifest.revision`.

## 2. Method and mechanical results

- Replay confinement: `README.original.md` equals the live blob at the head (bytes); replaying only the edits enumerated in `corrections.json` (offset replay, own script `acc2s2/verify.py`) reproduces `README.md` byte for byte; `README.patch` applied with `git apply` to the live blob also reproduces it; every line-diff hunk lies inside an enumerated edit span; no CRLF; manifest sha256 of all files verify.
- Live head: `git ls-remote` equals the clone HEAD equals `manifest.revision` (no drift).
- Markdown render (markdown-it + html5lib): heading and `<details>` structure before/after identical except as stated; no duplicate heading; `mech.py` (protocol Appendix A) before/after normalised for line shifts: no new forbidden wording, forum link, dangling lead-in, anchor or relative-link problem.
- Validation delta (`validation_delta.json`): introduced = [], judge `validate_candidate`.

## 3. Diagram (before/after render)

- Live diagram (before): vertical, 18 HTML foreignObject labels, clipped in fonts {'Arial': 1, 'Verdana': 7, 'Georgia': 4} (lane's own `check_entry`: 64 problems).
- Corrected diagram (after): horizontal, 0 foreignObject, 0 native spills, 0 clipped in Arial/Verdana/Tahoma/Segoe UI/Georgia, 0 problems; same result with all four mermaid packages (11.17.2, 11.4.1, 11.12.0, 12.1.0) in Edge 155 (my own run of the lane's `measure.mjs`).
- PNGs viewed: `acc2s2/png/Aspose.Email-FOSS-for-Python.live.0.png` and `acc2s2/png/Aspose.Email-FOSS-for-Python.corr.0.png`.
- Node ids, normalised labels (`<br/>` read as a space), subgraph titles and the chain `StartingPoints --> PRODUCT --> Capabilities --> Outputs` are equal before and after (own parser, `verify.py`); only the init line, `flowchart LR`, `<br/>` wraps and invisible `~~~` column links are new.


## 4. Edits and claim checks

| # | Edit | Claim | How checked | Result |
|---|---|---|---|---|
| 1 | At a Glance redraw (L31) | same labels/edges, horizontal, not clipped | own parser; rendered 4 releases x 5 fonts; PNG viewed | PASS |
| 2 | add_dev_commands L406: `The [ci workflow](.github/workflows/ci.yml) runs across python-version (3.10, 3.11, 3.12, 3.13).` | CI matrix is Python 3.10-3.13 | `.github/workflows/ci.yml` job `tests`, `matrix.python-version` = 3.10, 3.11, 3.12, 3.13 | PASS (true) |
| 3 | link `.github/workflows/ci.yml` | resolves | exists in the clone | PASS |
| 4 | live README already says the same | redundancy | live L402-403: `CI runs the test suite on Python 3.10 through 3.13 and validates packaging on every push and pull request to master` (three lines above the insertion) | FAIL (duplicate, introduced) |

## 5. Live comparison

- ADDS: horizontal diagram (better); a sentence that repeats live L402-403 and names the raw matrix key `python-version` in prose ("runs across python-version (...)").
- DROPS: none. CHANGES: Mermaid body only.
- NET: better for the diagram, neutral-to-slightly-worse for the sentence (duplicate, machine voice, no new fact except the link).
- Inherited, untouched (lane reports it): the live README's example 5 (`from aspose.email_foss import msg`, L174) raises NameError per the lane's example verifier; not changed by this bundle.

## 6. Verdict

FIX_REQUIRED, MINOR. The diagram hunk is PUSHABLE on its own. Drop the `add_dev_commands` hunk (duplicate of live L402-403). Fix kind: `code_change` for the generator (redundancy gate must compare the fact against prose, not just command lines), but for this PR a hand-drop of one hunk suffices.
