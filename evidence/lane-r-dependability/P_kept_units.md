# P - why 384 of 773 kept (VERIFIED_PRESERVE/MOVE) inherited units are not printed (2026-10-16)

Method: loaded the 30 CURRENT bundles, reproduced judge `_kept_text_present` (judge.py:494): 773 kept, 384 missing (matches).
Re-ran `placement.placements()` (placement.py:633) on each sealed plan/dispositions/facts for each unit's outcome, and re-ran
the current BC-05 on every sealed README. A normalised-substring test (links, entities, emphasis stripped) found 0 false
positives among paragraphs and lists: the misses are real text absence, not normalisation (cause e = 0).

## Cause table (sums to 384)
| # | Cause (placement outcome) | n | kinds |
|---|---|---|---|
| 1 | Kept HEADING never printed by design: `_RENDERED_ELSEWHERE` placement.py:102, `renders_verbatim` :126, outcome owned_elsewhere (:679) | 191 | heading |
| 1a | API Reference sub-headings (### Math, ### Exceptions) replaced by generated Core API + Detailed Member Reference (renderer.py:932-975) | 95 | |
| 1b | Additional Examples headings: 56 replaced by LLM-authored `workflow:<id>` title (renderer.py:1317-1327, slot authoring.py:904); 17 example not in plan; 13 grouping headings with no code; 2 example went to quick_start | 88 | |
| 1c | Section-level headings (shell retitles/merges, or plan excludes the section) | 8 | |
| 2 | Image-only paragraph typed `badge_row` (inherited.py:286) so owned_elsewhere: 5 Font-Python figures + 1 PDF-Go preview lost; 4 html_block are `<details>` wrappers (benign) | 10 | badge 6, html 4 |
| 3 | OVERLAP: destination "already states it" (placement.py:735-757; coverage.py 0.7 stem share) | 143 | list 87, para 55, table 1 |
| 4 | Outcome `placed` under current code but absent from the sealed README | 38 | list 13, para 25 |
| 5 | Outcome `excluded`: unit targets additional_examples, plan omits it (Email-Cpp 030, 069) | 2 | para |

## Examples
1a  PDF-Java 075.heading `### Facades` (PRESERVE to api_reference): README has `### Core API` + `### <hub class>` only.
    3D-Java 064.heading `### Math` + 065.001/002.list (`Vector2`, `Matrix4`...): README has generated tables only.
1b  3D-Python 047.heading `### Build a Mesh and Export It to STL` -> README `### Build a Triangle Mesh and Export to ASCII STL Format`
    (authored unit "Build a triangle mesh and export to ASCII STL format."). Cells-Go 028 `### Formulas and the Calculation Engine`
    -> README `### Create a Workbook, Populate Sales Data, Add SUM and AVERAGE Formulas, and Evaluate Them`.
1c  Slides-Python 049 `## Limitations`, 059 `## Links` (shell: "Scope and Limitations", "Documentation & Resources");
    Cells-.NET 066, Cells-Cpp 058, Words-.NET 070 `## Development and Testing`: plan.json include=false for that section.
2   Font-Python 031/035/039/044/048 `![Family review board](./website/generated/roboto-family-review-board.png)` (MOVE): not in README.
3   Cells-.NET 020.paragraph `Export a worksheet to PDF:` (cites example:003): README has the authored lead-in. (26 examples + 14
    quick_start lead-ins, all word recall 1.0.) Words-.NET 062.002.list `- ChartSeries - Add(xValue, yValue), Insert(...), Remove(index)...`:
    Detailed Member Reference lists only members with a docstring (renderer.py:966-970, has_member_summary); identifier recall of the
    65 API lists averages 0.44, 37 below 0.5, so real signature information is lost. Cells-.NET 064.list `- **Load format scope.** ...`
    (plan hands the unit to a limitation slot, placement.py ~705): the LLM restates it as limitation bullets. Docs lists (11), table (1):
    renderer prints its own link list (renderer.py:629); links present, wording differs.
    Word-recall buckets: lists 87 = 22 (>=0.9) / 32 (0.7-0.9) / 33 (<0.7); paragraphs 55 = 28 / 15 / 12.
4   34 of 38 are stale seals: 28 of 29 bundles carry validator_version 3 or 4 (current 23). Current BC-05 on the sealed README
    reports exactly these 34 ("placed in X but the candidate does not render it"), e.g. 3D-Java 072.list and 078.paragraph,
    3D-Python 029, 057, 065, 067. A re-render under current code prints them (placed_texts, renderer.py:270). The other 4
    (Note-Python 010/015/091/101): renderer prints only the uncovered REMAINDER (coverage.uncovered); judge tests the whole unit.
5   Email-Cpp 030.paragraph `For a full command-line workflow, see examples/create_msg_and_eml.cpp...`; BC-05 now says
    "placed in additional_examples, which the plan omits".

## Candidate causes tested
(a) title-case/abbreviation: REJECTED. `to_title_case` is idempotent on 190 of 191 missing headings (only "What's not included
    (and where to get it)" changes); judge heading_key lowercases anyway.
(b) LLM paraphrases a preserved unit: NOT for placed units; the renderer prints placed text verbatim (renderer.py:1439-1455).
    TRUE only where the plan substitutes an authored slot for the kept unit: example titles (56), lead-ins (40), limitation slots (11).
(c) placement dedup: dominant for paragraphs and lists (143).
(d) moved into a section that renders other content: API Reference (95 headings + 65 lists + 5 paras), Docs Resources (14).
(e) judge false positive: none from normalisation. Only "false" in the sense of stated-in-other-words (3), remainder-only (4 units),
    `<details>` wrappers (4).

## Why BC-05 passes while J4 fails (registry.py:1422-1481)
BC-05 checks: one disposition per unit; deferral causes; for outcome `placed`, that the text is in its section; for outcome
`overlap`, ONLY lists of 2+ items in `_LIST_OBLIGED` = scope_limitations, development_testing, documentation_resources
(registry.py:1356, list_coverage.py:75), by subject-word stems, not text. It never examines owned_elsewhere (headings, badge rows,
html, ecosystem code), overlap paragraphs or tables, nor api_reference/key_capabilities lists. J4 demands verbatim text for every
kept unit. They encode different contracts (stated in other words vs printed as written).

## Deterministic fixes (render the kept unit verbatim from the ledger)
1b (88): YES, mostly. In `_example_entry` take the live heading unit at ordinal(code block)-1 (`_example_code_block_ordinals`,
    placement.py ~250), title-cased (idempotent, BC-07 safe); authored title only as fallback; drop the `workflow:` slot
    (authoring.py:904/952). Touches renderer, authoring, planning slot binding, placement.renders_verbatim, tests, reseal of
    example sections. The 17 orphan + 13 grouping headings need a disposition change (SUPERSEDE_REDUNDANT), not a render change.
1a (95 + 70 overlap units): PARTLY. Printing the live grouped overview above Core API duplicates generated tables and lists members
    lacking docstrings (claims then need BC-04/14 coverage). Cleaner: reconciler marks them SUPERSEDE_REDUNDANT and J4 stops
    expecting them. Product decision.
1c (8): reorder placement so `excluded` precedes `owned_elsewhere` (placement.py:679/682); reconciler supersedes section-title
    headings; judge may accept shell heading synonyms.
2 (6 figures): YES. Type image-only paragraphs outside the lead as prose (inherited.py:286) so renders_verbatim prints them.
    Touches extractor, facts, placement; unit ids/facts change, so affected repos reseal.
3 lead-ins (40): YES. Print the live lead-in (unit at ordinal-1 of the example block) instead of authored `lead_in`/`preview`
    (renderer.py:1380-1395, authoring slots).
3 scope/docs/api lists (109): printing verbatim re-creates the duplication the overlap rule was written to stop (coverage.py
    header); only a decision to prefer the live list over authored bullets would do it.
4: no code needed for the 34 (recheck/re-render under current code); the 4 remainders need J4 to compare `Placement.text`.
5: planning defect (a kept unit targets a section the plan omits); fix in planning.plan_checks, not render.
