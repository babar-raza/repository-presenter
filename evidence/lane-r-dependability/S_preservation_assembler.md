# S: deterministic preservation assembler, feasibility experiment (2026-10-16)

Scripts and outputs: `S_experiment/` (`assembler.py`, `run.py`, `results.json`, `out/<mode>/<repo>.README.md`). No product file was touched; judge runs were on copies in `S_experiment/scratch/` (deleted afterwards). All 30 bundles at their `CURRENT` (Note-FOSS is the untracked `0fd1cf7`).

## Method
1. Kept unit = disposition `VERIFIED_PRESERVE|MOVE`. "Missing" = J4's own test (squeezed text not in README), but headings use J6's stricter exact `heading_key` test (7 extra headings that J4 accepts only because the live text is a *prefix* of the generated heading, e.g. `### Extract Attached Files` inside `### Extract Attached Files to Disk Using ...`).
2. Placement, in order: child of an already restored parent heading; else under the README heading that matches the unit's source parent (if inside the destination section); else the `destination_section` heading (non-heading units at the section lead, restored headings at the section end, level raised to parent+1 if needed); else a new heading before Third-Party Notices/License.
3. Retitle detection (prefix, or >=2 shared stemmed tokens at >=60% overlap, same level, README heading not itself a source heading): 52 of 198 missing headings are present under another title. Mode `insert` adds them anyway; mode `rename` renames the generated heading to the live one (no standard-required heading was hit).
4. Mode `extended` (beyond the brief): also restores the unit carrying every live heading/code/link/command that J6 still sees lost, plus that heading's children.
5. Judge: README.md replaced, README.patch regenerated against the live README, `validation.json` readme_sha256 patched. BC-01..14 were NOT re-run; J1-J3, J5 stay PASS only because their recorded verdicts are reused.

## Results (all 30 bundles)
- J4: FAIL on 29 -> PASS on 30 in every mode. This is a tautology (the text is printed verbatim), not evidence of quality.
- J6 (applicable on 26): `rename` PASS on 2 of 26 (TypeScript, Email-.NET). Losses fall 493 -> 257 (236 were kept units, now 0). The 257 left are Lane R bookkeeping, not missing prints: 196 `SUPERSEDE/REWRITE/OMIT` rows with empty `fact_ids` or rationale (so `_accounts` is False) and 61 `DEFER_UNRESOLVED`. `extended` PASS on 26 of 26 (losses 0) by restoring those too.
- Missing units: 391 (198 headings, 100 lists, 82 paragraphs, 6 badge rows, 4 html blocks, 1 table). `extended` restores 953 units (358 headings).

| bundle | J4-gap units | J4 b>a | J6 b>rename>ext | J6 losses b>r>e | dup/partial rename \| ext | empty new sections r \| e | lines added r \| e |
|---|---|---|---|---|---|---|---|
| Note/Python | 20 (9h) | FAIL>PASS | FAIL>FAIL>PASS | 17>8>0 | 7/1 \| 7/2 | 4 \| 6 | 59 \| 106 |
| Cells/Rust | 27 (16h) | FAIL>PASS | FAIL>FAIL>PASS | 23>6>0 | 1/1 \| 2/3 | 9 \| 0 | 128 \| 414 |
| Words/.NET | 33 (12h) | FAIL>PASS | N/A (live not standard) | 24>12>0 | 0/5 \| 1/6 | 6 \| 0 | 81 \| 238 |
| Slides/Python | 24 (14h) | FAIL>PASS | FAIL>FAIL>PASS | 16>2>0 | 1/1 \| 1/1 | 7 \| 7 | 66 \| 93 |
| Email/Cpp | 22 (5h) | FAIL>PASS | FAIL>FAIL>PASS | 13>6>0 | 3/2 \| 3/2 | 2 \| 0 | 95 \| 277 |
| 3D/Python | 21 (9h) | FAIL>PASS | FAIL>FAIL>PASS | 21>4>0 | 0/3 \| 1/5 | 4 \| 1 | 89 \| 137 |
| PDF/Go | 18 (14h) | FAIL>PASS | FAIL>FAIL>PASS | 19>4>0 | 0/0 \| 0/0 | 10 \| 0 | 77 \| 294 |
| HTML/Python | 16 (11h) | FAIL>PASS | FAIL>FAIL>PASS | 20>6>0 | 0/2 \| 0/5 | 9 \| 3 | 42 \| 139 |

(dup = >=60% of the unit's word 3-grams already in the README, partial = 30-60%; Cells-Rust, PDF-Go: deltas are mostly orphan headings.) Totals: rename 30 dup + 27 partial of 193 non-heading units; 116 of 146 inserted headings have no body; `extended` 72 dup + 64 partial, 44 empty, 20 new headings fail title case, 13 `<details>` blocks added (BC-07 forbids collapsed visible sections).

## Honest quality reading
Placement is reliable for only 93 of 339 routed units (restored/renamed/source parent); 246 (72%) went to "end of destination section", i.e. a guess. Sample of Note (20 units, `rename`): 6 clean (4 retitled headings renamed, an API intro paragraph, a limitations list); 3 near-duplicates of generated text (Key Capabilities bullets pasted a second time, the "Requires Python 3.10" sentence twice, the Documentation & Resources bullets twice with different wording); 5 empty headings (`### Content`, `### Licensing` ...); 6 misplaced or dangling (enum bullets after a table, a MIT licence paragraph inside Scope and Limitations, a paragraph ending in "instead:" whose code block was superseded).

Excerpt, Note README, Documentation & Resources (after `rename`):
```
- **[Getting started guide](...)** — The getting started guide covers installation, walkthroughs, ...   <- generated
- Found a bug or have a feature request? [Open an issue](...).
- **[Getting started guide](...)** — installation, walkthroughs, and feature guides ...                <- restored, same link
- Found a bug or have a feature request? [Open an issue](...) on GitHub.                                <- restored
```
Excerpt, Slides/Python (`extended`), after the Additional Examples details block:
```
### Text Formatting
### Hyperlinks
Assigning `None` removes the link and the relationship it owns.
### Table
### Connector   ...   (nine headings, eight with no body)
```

## Verdict
A ledger-driven renderer cannot be the core of a dependable Lane R as the ledger stands. It makes J4 pass trivially and, with the extended rule, J6 too, but it produces a pile: duplicates of text the writer already paraphrased, empty headings, mis-ordered fragments, un-verified live claims bypassing BC-04/BC-07 (not re-run here), and collapsed sections.
Main obstacles:
1. The ledger is unit-granular but not position-granular: no anchor, order or group ties a kept unit to the generated text it overlaps. Without it, "verbatim" and "no duplication" cannot both hold.
2. Kept and superseded rows contradict each other: a kept heading often sits over superseded body units (116 of 146 inserted headings empty) and a kept paragraph often duplicates a superseded or regenerated one.
3. J6 losses are 52% ledger bookkeeping (empty `fact_ids`, DEFER); these are Lane R decision defects a printer would only mask.
4. J4 itself is gameable (substring/prefix heading match) and does not measure coherence; passing it says nothing about the reader's view.
5. Verbatim live text bypasses fact support; it would need BC-04/06/07/14 re-validation.
Viable narrower use: a deterministic *in-place* path (Lane L): keep the live README as the base document and apply only ledger-approved edits, so preservation is by construction and duplicates cannot arise. The assembler idea works there, not as an append-onto-generated step.
