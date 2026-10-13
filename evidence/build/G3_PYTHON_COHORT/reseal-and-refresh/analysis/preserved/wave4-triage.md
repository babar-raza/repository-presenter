authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Wave 4 triage (cut 8c48f4d2 = integration/cut4, results runs/reseal/8c48f4d2/results.jsonl)

Read-only triage. Evidence: results.jsonl (44 of 44 rows, final), clones G:\rp-w4\<name> (calls/*.rejected-N.json, validation.json, review.json, repairs.json, dispositions.json, facts.json, examples.json), wave 3 clones G:\rp-w3\<name>, the executed code at 8c48f4d2 (G:\rp-w4\<name>\src, identical to `git show 8c48f4d2:...`). Last refresh: 44 of 44 rows.

## 1. Result (final)

SEALED 4 (3D-TypeScript, Cells-.NET, Cells-Python, Slides-Python), NOT_READY 1 (PDF-Python), FAILED 39.
Recorded class: model_output 17, BC-05 9, BC-02 7, BC-10 4, unknown 2 (both are truncated model output), NOT_READY 1.

Wave 3 had 8 SEALED of 36. The 44 rows of wave 4 are the 36 wave-3 repositories plus the 8 new JMAP libraries:

| | wave 3 | wave 4, same 36 repos | wave 4, 8 new JMAP |
|---|---|---|---|
| SEALED | 8 | 4 (3 kept, Cells-Python gained, 5 lost) | 0 |
| model_output | 9 | 11 | 6 |
| BC-05 | 1 | 9 | 0 |
| BC-02 | 5 | 6 | 1 |
| BC-10 | 8 | 3 | 1 |
| BC-08 / BC-12 / BC-04 | 3 / 1 / 1 | 0 / 0 / 0 | 0 |
| unknown (truncation) / NOT_READY | 0 | 2 / 1 | 0 |

Transitions (wave 3 -> wave 4): SEALED->SEALED 3 (3D-TS, Cells-.NET, Slides-Python); SEALED->BC-05 3 (3D-Java, Note-Python, Slides-.NET); SEALED->model_output 2 (3D-.NET, Cells-Java); BC-05->SEALED 1 (Cells-Python: the L-r4 U2/U3 fix works); BC-08->{BC-10, model_output, unknown} 3 (the placement fix works: BC-08 is no longer the primary blocker anywhere); BC-12/BC-04 -> model_output 2 (U4/U11 fixed, rows now die later); BC-10->BC-05 3 (Email-Cpp, Font-Python, Words-.NET); model_output->BC-05 3 (BarCode-Python and Email-Python and Words-Python got past S4 and S6 and now meet BC-05).

## 2. Why it is worse than wave 3 (answer first)

1. The headline is partly a denominator effect: 8 new JMAP repositories, 0 sealed; 5 of the 8 die on one defective new gate (LST-01 below). On the 36 common repositories the real change is 8 sealed -> 4 sealed.
2. The 5 lost seals were not clean. I re-ran the wave-4 `list_coverage.missing_items` over the wave-3 SEALED READMEs: 3D-.NET lost the `Microsoft3MFFormat` item of 061.list, 3D-Java lost the `PbrSpecularMaterial` item of 072.list, Cells-Java lost the XML-mapper item of 048.list (all VERIFIED_PRESERVE lists stated incompletely). 3D-Java (Gradle snippet), Note-Python (`[pdf]` extra), Slides-.NET (csproj/nuget.config blocks) had silently deferred content that BC-05 v7 now blocks. So 5 of 8 "wave 3 seals" were true-defect seals; the cut-3/cut-4 gates (LST-01, BC-05 v7 escalations, BC-07 v11, hygiene) correctly refuse them. That is expected.
3. But the generation side cannot yet satisfy those gates, and two of the new gates are defective themselves:
   - LST-01 `list_item_missing` judges a list item by the stems of its bold label, not its content, and deadlocks with the identifier gate. It is in the failure chain of 10 of 17 model_output rows.
   - The cut-4 convergence lane (L-r1, narrowed third ask) does not converge: of 15 narrowed asks, 1 succeeded (PDF-Java scope_limitations); in 6 of 14 failures the third reply was byte-identical to the second for the slots asked.
   - The BC-05 repair path cannot place a unit whose natural home is a renderer-owned section (installation, dependencies), so recover-time deferrals (`recover_uncited_prose_omits`) become terminal BC-05 failures: 8 of 9 BC-05 rows had at least one recovered reconciliation batch.
4. What cut-4 fixed (measured): BC-08 3 -> 0 primary (L-r3 placement: Cells-Go, PDF-Go, PDF-.NET moved on), BC-12 and BC-04 gone as primary (PDF-Cpp still shows a secondary BC-12 `Aspose.PDF FOSS`), Cells-Python sealed (U2/U3), C++ repositories now get past composition (Email-Cpp reaches BC-05, PDF-Cpp reaches BC-02; Slides-Cpp and Cells-Cpp still die in authoring), BC-10 8 -> 4, the silent-unit tail (BarCode-Python) passes S4. No wave-4 failure traces to the audience guard (zero audience rejections in 44 runs), the Mermaid renderer (zero diagram failures; JMAP-.NET F01 is a reviewer complaint) or the BC-02 ownership rule (the 4 repeated BC-02 rows are identical to wave 3).

## 3. Regression vs stricter-gate split (40 non-sealed rows)

| class | rows | repositories |
|---|---|---|
| (a) REGRESSION: defect in a cut-3/cut-4 change itself | 8 | JMAP-Go, JMAP-Node, JMAP-TS, JMAP-Rust, PSD-.NET (LST-01 label false positive); Email-.NET, Imaging-.NET (LST-01 x identifier-gate deadlock); JMAP-Cpp (1500-char hygiene cap x coherence) |
| (b) NEW stricter gate, TRUE defect, generation must change | 10 | 3D-.NET, PDF-.NET, PDF-Java (LST-01 true omissions); 3D-Java, BarCode-Python, Email-Python, Font-Python, Note-Python, Slides-.NET, Words-.NET (BC-05 v7 lost content) |
| (c) MODEL VARIANCE / degeneration | 7 | Cells-Cpp, Cells-Java, JMAP-Java, PDF-Go, PDF-TS, Slides-Cpp, TeX-Python |
| (d) UPSTREAM / ENVIRONMENT | 7 | 3D-Python, GIS-.Net, Page-Python (registry ownership), Cells-Rust (crates.io unreadable + getrandom build script), JMAP-Python (unpublished, examples need a live server), PDF-Cpp (upstream CMake configure fails), Words-Python (no Python 3.10-3.12 on the runner) |
| (e) CARRY-OVER (wave-3 cause not fixed) or new latent defect | 8 | Cells-Go, Cells-TS, HTML-Python, JMAP-.NET (reviewer, U8); Email-Cpp (UNCLASSIFIED fold, U12); PSD-Python (U13); Slides-Java (title test, bug below); PDF-Python NOT_READY (non-deterministic examples.json) |

Short version: regressions 8, stricter-gate true defects 10, variance 7, upstream/env 7, carry-over 8.

## 4. Per-row table (44)

Legend W3 -> W4 with class. LST = list_item_missing (cut-3 ebc79449 LST-01). Details in section 5.

| repository | W3 | W4 | cause (evidence) | class |
|---|---|---|---|---|
| 3D-.NET | SEALED | model_output | 061.list 8 items, 7 slots: a1 and a2 each drop 2 different items (the narrowed ask folds them, then a stray `Scene.Open/Scene.Save` slash-pair is refused) | (b) |
| 3D-Java | SEALED | BC-05 | 016.code_block Gradle Kotlin snippet DEFER (same deferral in wave 3, which BC-05 v6 let pass); S4 repair "unrepairable": proposes destination `installation` | (b) |
| 3D-Python | BC-02 | BC-02 | registry project URL points at another repository; +BC-07 v11 (GLTF heading, dangling "below") | (d) |
| 3D-TypeScript | SEALED | SEALED | | |
| BarCode-Python | model_output | BC-05 | 014.paragraph `py.typed` sentence deferred; S4 repair proposes `dependencies` twice | (b) |
| Cells-.NET | SEALED | SEALED | | |
| Cells-Cpp | BC-02 | model_output | S8 coherence drops 34 cited symbols, then hub cites a fact outside its slot (also 68 drops in wave 3) | (c) |
| Cells-Go | BC-08 | BC-10 | 12 reviewer findings: "none of which are supported by public_symbol facts" about Chart, VBAProject, FormulaError... all SUPPORTED public_symbol facts the finding itself cites | (e) |
| Cells-Java | SEALED | model_output | stray `org.aspose/cells_foss` (model wrote `src/test/java/org.aspose/cells_foss/`) in all 3 attempts | (c) |
| Cells-Python | BC-05 | SEALED | | gain |
| Cells-Rust | BC-10 | BC-02 | `cargo could not be read` and `failed to run custom build command for getrandom v0.3.4`: 7 examples NOT_VERIFIED (wave 3: crates.io read fine, example 1 COMPILED). +BC-05 NO_VERIFIED_QUICK_START x7, +BC-07 v11 | (d) rerun |
| Cells-TS | BC-10 | BC-10 | F01 and F02 say `excel-cells` unsupported while `package:name` SUPPORTED = excel-cells (reviewer error); F03 is real (authored "excel-cells format at version 1.0.0") | (e) |
| Email-.NET | BC-10 | model_output | dev_testing summary: owed list 023.list item names `Microsoft.NET.Test.Sdk`, `xunit.runner.visualstudio`; naming them = stray identifier, describing them in words = LST | (a) |
| Email-Cpp | BC-10 | BC-05 | 069.paragraph VERIFIED_PRESERVE into `additional_examples` (plan excludes it now that quick_start holds) folds to DEFER -> UNCLASSIFIED | (e) |
| Email-Python | model_output | BC-05 | 011.list API list deferred (11 pieces); S4 targeted_repair output truncated at 8000 tokens | (b) |
| Font-Python | BC-10 | BC-05 | 055.paragraph "Use these `@font-face` best practices:" DEFER while its block 056 is OMIT_UNSUPPORTED -> LEADIN_OF_WITHHELD_CONTENT | (b) |
| GIS-.Net | BC-02 | BC-02 | upstream: no README/LICENSE, NuGet absent | (d) |
| HTML-Python | BC-10 | BC-10 | 8 findings on deterministic API tables ("not under a separate Core API category", `aspose_html.dom.html` unsupported though SUPPORTED) | (e) |
| Imaging-.NET | BC-12 | model_output | same deadlock as Email-.NET, oscillating a1 stray -> a2 LST -> a3 stray | (a) |
| JMAP-Cpp | new | model_output | coherence drops 23 symbols; the re-ask puts them in the opening: 1534 characters > MAX_UNIT_CHARS 1500 (text_hygiene.py) | (a) |
| JMAP-Go | new | model_output | LST label false positive ("Out of scope for v1") | (a) |
| JMAP-Java | new | model_output | method names `createMailbox()` are not facts -> reply rewrites in words -> all 8 capabilities "restate own title" -> narrowed ask leaves capability:5 "Email submission" | (c) |
| JMAP-.NET | new | BC-10 | REJECT_PRESENTATION: asks to restore the original diagram's Starting Points/Outputs groups and an unpublished NuGet name (renderer-owned, withheld on purpose) | (e) |
| JMAP-Node.js | new | model_output | LST label false positive ("Protocol", "Out of scope for v1") | (a) |
| JMAP-Python | new | BC-02 | PyPI project absent; the only examples need a JMAP server (`JmapNetworkError`), so no source-install receipt; +BC-08 | (d) |
| JMAP-Rust | new | model_output | LST label false positive | (a) |
| JMAP-TypeScript | new | model_output | LST label false positive | (a) |
| Note-Python | SEALED | BC-05 | 013/014 `[pdf]` extra deferred (wave 3 superseded 014 into dependencies citing dependency facts); S4 repair proposes `dependencies` -> rejected | (b) |
| Page-Python | BC-02 | BC-02 | registry lists no source repo; +BC-07 v11 ("PS/EPS-to-image conversion:" colon, nothing follows) | (d) |
| PDF-Cpp | model_output | BC-02 | upstream CMake configure fails; +BC-07 v11 x2, +BC-12 `Aspose.PDF FOSS` | (d) |
| PDF-Go | BC-08 | unknown | api_reference intro: model emits an `omitted` entry for every public symbol, truncated at 8000 tokens | (c) |
| PDF-Java | model_output | model_output | LST recovered at the narrowed ask (the one success), then S8 coherence rejects: strays `Document.validate/Document.convert`, `maven.compiler.source/target`, dropped `build_test_asset:tests` | (b)/(c) |
| PDF-.NET | BC-08 | model_output | 225.list has 16 items for 7 slots; a1 7 missing, a2 and a3 3 missing | (b) |
| PDF-Python | model_output | NOT_READY | ACCEPT, noop VERIFIED, BC-11 pending: fresh process "examples.json changed since the last seal" (captured stdout holds library log timestamps) | (e) |
| PDF-TypeScript | model_output | unknown | S4 batch (541 units) reply degenerates into whitespace until 32000 tokens (819 s) | (c) |
| PSD-.NET | BC-04 | model_output | LST label false positive: 052.list item "No full Photoshop feature set. No text, vector, effects..." stated in substance, label stems {full, photo, featu, set} only 1 of 4 present | (a) |
| PSD-Python | BC-02 | BC-02 | no install fact: manifest-less tree (U13 not implemented); +BC-07 v11 | (e) |
| Slides-Cpp | BC-10 | model_output | stray `sections()` kept in a2 and a3 | (c) |
| Slides-Java | model_output | model_output | capability:5 "Document properties": identical text in 3 attempts; test bug below | (e) |
| Slides-.NET | SEALED | BC-05 | 7 deferrals (3 -> 27 DEFER_UNRESOLVED on the same plan): LEADIN x2, NOT_CARRIED x4, UNCLASSIFIED x1 | (b) |
| Slides-Python | SEALED | SEALED | S4 BC-05 repair succeeded (017.code_block re-placed) | |
| TeX-Python | model_output | model_output | stray `extra_format_paths`: 3 -> 2 -> 1 violations, narrowed ask leaves 1 | (c) |
| Words-.NET | BC-10 | BC-05 | 010.paragraph "placed in dependencies" -> DEFER; S4 repair rejected; +BC-06, +BC-07 v11 | (b) |
| Words-Python | model_output | BC-05 | `BLOCKED_TOOLCHAIN: no interpreter satisfies requires-python '>=3.10,<3.13' ... machine's installed interpreters are 3.13` -> all 12 examples NOT_VERIFIED -> NO_VERIFIED_QUICK_START | (d) |

## 5. Ranked causes (rows whose failure chain contains the rule)

| rank | rule | rows | share |
|---|---|---|---|
| 1 | LST-01 `list_item_missing` (+ its identifier deadlock) | 10: 3D-.NET, Email-.NET, Imaging-.NET, JMAP-Go, JMAP-Node, JMAP-TS, JMAP-Rust, PDF-.NET, PSD-.NET, PDF-Java | 25% of non-sealed, 59% of model_output |
| 2 | BC-05 v7 content-presence escalation (NOT_CARRIED_BY_NAMED_SECTION, LEADIN_OF_WITHHELD_CONTENT, UNCLASSIFIED) | 9 (plus Cells-Rust as secondary) | |
| 3 | BC-02 | 7 | |
| 4 | Stray identifier gate (BC-04 mirror in `unit_checks`) | 6 in chain (Cells-Java, TeX, Slides-Cpp primary; 3D-.NET, PDF-Java, Imaging) | |
| 5 | Reviewer false findings on renderer-owned text (BC-10) | 4 | |
| 6 | BC-07 v11 dangling reference ("table below"/colon with nothing after) | 6 secondary (3D-Py, Cells-Rust, Page-Py, PDF-Cpp, PSD-Py, Words-.NET); will surface as soon as the primary blocker is cleared | |
| 7 | S8 coherence "drops the previously-cited ..." | 3 (Cells-Cpp, JMAP-Cpp, PDF-Java) | |
| 8 | "restates its own title" | 2 (Slides-Java, JMAP-Java) | |
| 9 | Truncated or degenerate model output | 2 (PDF-Go, PDF-TS) | |
| 10 | Non-deterministic examples.json (BC-11) | 1 (PDF-Python) | |

Authoring-job level (section_authoring jobs with no accepted reply, from the archived rejected-N files): wave 3 7 jobs (stray 2, LST 2, title 1, restated command 1, slot-set/silent 1); wave 4 18 jobs: LST 7, stray 6, title 2, other 3 (coherence outside-slot, 1534-char hygiene cap, truncation). Narrowed (third) asks in wave 4: 15 issued (calls.jsonl), 1 accepted.

### Cause 1 - LST-01 `list_item_missing` (10 rows)

Message (3D-.NET a1): `inherited_unit:061.list: list_item_missing: this list was kept as written, so every one of its 8 items must be stated by the units that cite it; 2 not stated: "Text watermarking is not currently functional in this FOSS build."; "License and trial-management APIs ..."  Fold each into a unit citing inherited_unit:061.list (scope, limitation:1 ... limitation:6); an item that names an identifier that is not an accepted fact value is described in plain words instead`.

Where: `composition/list_coverage.py:list_coverage_errors` -> `missing_items` -> `_lead` / `_stems`; wired in by `repair/rounds.py:_reject_unlisted_items` (S6 draft and S6 repair), `composition/authoring.py:authoring_tasks` (`owed_lists`, carry_rule "Lists kept as written, every item of which your units must state"), `composition/planning.py` (hands each kept list to the limitation slots); introduced in cut-3 commit ebc79449 (LST-01), extended by 9fbb17dd (L-r1 narrowing names the slots).

Three distinct defects behind one message:

1. Label false positive (5 rows: JMAP-Go, JMAP-Node, JMAP-TS, JMAP-Rust, PSD-.NET). `_lead(item)` returns the bold label ("Out of scope for v1", "Protocol", "No full Photoshop feature set"); presence needs >= 50% of the label's 5-letter stems in the whole section text. JMAP-Go limitation:1 states every sub-item ("Push EventSource streaming is a stub ..., JMAP for Calendars and Contacts is not implemented, and Date UTCDate values remain raw RFC 3339 strings ...") but never the words "out of scope" -> flagged in 3 identical attempts. JMAP-Node scope states the whole Protocol item verbatim minus the word "protocol". The check is wrong (too strict, judges the label, not the content); the model cannot know why. All 7 JMAP libraries share this README structure, so this alone costs up to 4-5 JMAP rows. Fix: in `missing_items` count an item present when >= 50% of the stems of its lead OR >= 50% of the stems of its whole text are in the destination (L-r3's `coverage.uncovered` shares this test, so placement benefits too). Effort S (hours, one function + test). Replayed offline on the archived rejected replies with the cut-4 `list_coverage` module and that rule: JMAP-Go, JMAP-Node, JMAP-TS, JMAP-Rust and PSD-.NET go from 1-2 missing to 0 at their final attempt (JMAP rows also at attempt 1), while PDF-.NET still reports its 3 genuinely absent items (Dynamic XFA, Colour management, pixel-identical rendering) and 3D-.NET attempt 1 still reports the watermark/licence item: true omissions stay caught (script: scratchpad fixtest.py).
2. Capacity (3D-.NET, PDF-.NET, PDF-Java): 3D-.NET list 8 items / 7 slots; PDF-.NET list 16 items / 6 limitation slots + scope. The model fixes the 2 named items by overwriting two others (whack-a-mole). The check is right (wave-3 seals lost items) but a plan that gives fewer slots than items cannot be satisfied. Fix: do not reject at authoring at all. Since cut-4 L-r3, `composition/placement.py:placements(..., destinations=)` + `composition/coverage.py:uncovered` carry any item the destination does not state as written, and BC-05 re-checks the finished README (`validation/registry.py`); downgrade `_reject_unlisted_items` to a prompt hint (or drop `owed_lists`). Verify first by replaying a failed candidate (e.g. PDF-.NET) through render with the guard off and checking BC-05. Effort S-M.
3. Deadlock with the identifier gate (Email-.NET, Imaging-.NET; JMAP-.NET dev_testing shows `xunit.runner.visualstudio` strays too): the owed development_testing list item is "`Microsoft.NET.Test.Sdk` 17.8.0, `xunit` 2.5.3, and `xunit.runner.visualstudio` 2.5.3 - the xUnit test host ...". Naming the packages -> `unit_checks` strays `coverlet.collector, xunit.runner.visualstudio`; describing them in words -> LST item missing. The exemption `cited_inherited_identifiers(...)` in `authoring.py:unit_checks` is scoped to `scope_limitations` or `task.must_carry`; an owed list (`task.owed_lists`) is neither. Imaging-.NET oscillated stray -> LST -> stray. Fix: add `task.owed_lists` (and kept lists handed to slots) to that exemption. Effort S (one line + test).

### Cause 2 - BC-05 v7 content presence (9 rows)

Messages: `inherited_unit:016.code_block is deferred as NOT_CARRIED_BY_NAMED_SECTION: the README does not state 1 piece(s) of it (implementation("org.aspose:aspose-3d-foss:26.5.0")), so deferring it loses content: keep it where a reader will find it, restate it, or omit it citing the fact that contradicts it.` / `... LEADIN_OF_WITHHELD_CONTENT: the code block it introduces (inherited_unit:018.code_block) was withheld and the README states none of it (...)` / `... UNCLASSIFIED: No deferral class matches this cause. It blocks until a class is registered in validation/deferrals.py.`

Where: `validation/deferrals.py:review_deferrals` + `ESCALATIONS` (`_lost_content`, `_lost_leadin`) using `validation/content_presence.py:unstated` (BC-05 v7, L-r5 c00d5b2d). The deferrals are produced by `reconciliation/dispositions.py:recover_uncited_prose_omits` / `_recover_uncovered` (typed prefix `RECOVERED_COVERAGE_RATIONALE`, "Not provably carried by the section named; held for the owner.") after S4 is rejected twice.

Chain, identical in 8 of 9 rows: S4 attempt 1 and 2 are rejected with `VERIFIED_MOVE needs a destination the shell can hold (additional_examples, api_reference, ... scope_limitations); got 'dependencies'` / `got 'installation'` + `uncovered_supersession` -> last-resort recover defers -> BC-05 v7 finds the content absent -> `targeted_repair` (S4) is rejected the same way ("output rejected twice", "change R02 claims 'dispositions.15.disposition' changed ... but the causal stage's own input and this revision hold the identical value", or "output truncated at max_output_tokens (8000)") -> `repairs.json` outcome unrepairable (BarCode, 3D-Java, Email-Python, Font-Python, Words-.NET). The repair converged only in Slides-Python (sealed); in Note-Python, Email-Cpp, Slides-.NET and Cells-Go a BC-05 S4 repair was accepted but the same defect was re-raised.
Why the generation fails: `reconciliation/dispositions.py:reconciliation_schema` types `destination_section` as the enum of ALL shell sections (`section_ids()`), including renderer-owned `installation`, `dependencies`, while `placement_errors` refuses them for any placing disposition. The content that has no holdable home is exactly the installation-adjacent material: Gradle snippet (3D-Java), `pip install "pkg[pdf]"` (Note-Python), `pip install git+...` (Words-Python 015), csproj ProjectReference and nuget.config (Slides-.NET 018/021), SkiaSharp packages (Words-.NET 010). Disposition variance multiplies it (Slides-.NET 3 DEFER in wave 3, 27 in wave 4; Note-Python 014 was SUPERSEDE_REDUNDANT in wave 3).
The check is right (the content is genuinely absent; the wave-3 acceptance review found these). The generation must change:
- Fix A (S): constrain the placing dispositions' `destination_section` to holdable sections in the schema/packet (or fold a placing disposition aimed at a renderer-owned section to the nearest holdable one in `normalize`), so attempt 1 cannot choose `dependencies`/`installation`.
- Fix B (M): in `_recover_uncovered` prefer `VERIFIED_PRESERVE` into a holdable section (`development_testing`/`quick_start`) over DEFER when the unit's literals are SUPPORTED (install coordinates, package extras), so recover does not manufacture a BC-05 block; or let the Installation renderer print preserved alternate package-manager blocks.
- Fix C (M-L): make S4 `targeted_repair` a per-unit patch (return only the units at fault; derive the `changes` bookkeeping in code) instead of the full 155-unit `revised_output`, which truncates (Email-Python) and mis-claims changes (3D-Java, Font-Python).
- Lead-in coordination (Font-Python): extend `reconciliation/dispositions.py:coordinate_neighbor_promises` so a DEFER lead-in follows an OMIT block (S).
- UNCLASSIFIED (Email-Cpp 069, Slides-.NET 081, Words-Python 038): `deferrals.py:_excluded_by_plan` requires `examples_consumed`; add the fold-into-plan-excluded-section signature (disposition folded, destination cleared, source section an examples/building section) (S).

### Cause 3 - BC-02 (7 rows)

Messages: `install_command:pip is UNRESOLVED: package registry: a distribution of this name exists, but ownership not confirmed: the registry's project URLs point at another repository` (3D-Python), `... the registry lists no source repository to compare with this one` (Page-Python), `install_command:dotnet is CONTRADICTED: package registry: distribution not found on nuget` (GIS), `no install command fact; the source install is not verified at this revision` (PSD-Python), `install_command:cargo is UNRESOLVED: package registry: cargo could not be read` (Cells-Rust), `install_command:cmake is UNRESOLVED: package registry: none could not be read` (PDF-Cpp: `source_checkout_unverified: no build exited 0: configure failed`), `install_command:pip is CONTRADICTED: package registry: distribution not found` (JMAP-Python).
Check is right in all. Not regressions: 4 of 7 repeat wave 3 exactly. (d) upstream metadata: 3D-Python, Page-Python, GIS (issue handoffs exist). (d) env: Cells-Rust (rerun; wave-3 same revision COMPILED), PDF-Cpp (CMake configure), Words-Python (BLOCKED_TOOLCHAIN: install Python 3.12 into the pinned toolchains; `core/toolchains.py installed_pythons` found only 3.13). Design gaps: PSD-Python (U13: `extractors/platforms/python.py` emits `install_command:pip` only when a name is declared; effort M), JMAP-Python (all examples need a live JMAP server, so no EXECUTED receipt for `_source_build_fact`; accept `build_verified` + import smoke-test as the source-install receipt when examples need external services; effort M; likely applies to all network-client libraries).

### Cause 4 - stray identifier gate (6 rows in chain)

Message: `unit limitation:2: identifiers that are not accepted fact values: Scene.Open/Scene.Save` (also `NurbsCurve.Evaluate/EvaluateAt`, `Document.validate/Document.convert`, `maven.compiler.source/target`, `aspose_html.dom.Node/aspose_html.dom.Element`, `org.aspose/cells_foss`, `sections()`, `extra_format_paths`, `coverlet.collector`).
Where: `composition/authoring.py:unit_checks` (strays) with `identifier_tokens` and `_MODULE_PATH` (unchanged since wave 3).
- `_MODULE_PATH = [A-Za-z_]\w*(\.\w+)+(/[A-Za-z0-9_.-]+)+` reads the prose shorthand `Scene.Open/Scene.Save` (both halves accepted) as one path token; wave 3 hit it twice (3D-.NET, 3D-TS), wave 4 five times (3D-.NET, Cells-Java, HTML-Python, PDF-Java x2). Check too strict (confirmed by calling the cut-4 `identifier_tokens` on the sentence: it returns `Scene.Open`, `Scene.Save` AND `Scene.Open/Scene.Save`; `identifier_allowed` is True for the parts and False for the pair). Fix: drop a `_MODULE_PATH` token from the stray list when each `/`-part is allowed (S).
- Whack-a-mole: TeX-Python 3 -> 2 -> 1, Slides-Cpp 4 -> 1 -> 1; the narrowed ask returns the same text. `composition/authoring_retry.py:recover_restating_sentences` deliberately does not touch strays. Removing the sentence that names a still-stray identifier cannot launder a claim (it only deletes); add it as a second last-resort (S-M).

### Cause 5 - BC-10 reviewer on renderer-owned text (4 rows)

Cells-Go (12 findings), HTML-Python (8), Cells-TS (3, one real), JMAP-.NET (5 presentation). Examples: `The candidate's API reference table includes Chart, ChartAnchor, ... none of which are supported by public_symbol facts.` with `fact_ids` listing `public_symbol:chart` etc. (SUPPORTED, in the reviewer packet; SYMBOL_CAP 6000 is not the limit). Check is wrong: the finding contradicts the facts it cites. L-r2's `RENDERER_SENTENCE`/`OMISSION_SETTLED`/`ABSENCE_SETTLED` rules do fire on other findings (advisories) but none covers "claims unsupported while every cited fact is SUPPORTED". Fix (S-M): in `review/independent/review.py` add a refutation rule: a factuality finding whose claim denies support and whose quote or names are the values of SUPPORTED facts it cites (Cells-TS F01, F02: `package:name` = excel-cells) folds to advisory. For JMAP-.NET/HTML-Python: findings that ask for renderer-owned sections (`at_a_glance`, `installation`, `api_reference` tables) already carry `reviewer_scope_defect`; widen `excluded_disposition_defect` to REJECT_PRESENTATION on those sections.

## 6. Smaller defects found (each with evidence)

- `restates_own_title` false positive (Slides-Java, JMAP-Java; identical reply 3 times): `composition/authoring.py:title_terms` -> `identifier_tokens` -> `_CAMEL = \b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b` does not see `IDocumentProperties` (I-prefixed) or `setCustomPropertyValue` (lowerCamel Java methods), so a unit that adds both looks like a pure restatement (verified by calling `title_terms` on the actual unit: `[]`). The same blind spot means the stray gate never checks lowerCamel Java/TS member names. Also `title.lower() in text.lower()` matches "email submission" inside "email submissions". Fix: broaden the camel pattern (stray gate impact to be measured) or, minimal, make `restates_own_title` count any CamelCase or lowerCamel token. Effort S.
- JMAP-Cpp: S8 coherence reply puts every dropped symbol into the opening (1534 chars > `text_hygiene.MAX_UNIT_CHARS` 1500). The coherence rule ("drops the previously-cited public_symbol") and the new hygiene cap contradict for symbol-rich C++ hubs. Fix: split the dropped symbols across the hub units or exempt coherence output from the cap (S).
- PDF-Go: `prompts/section_authoring.yaml` line 150 ("Every accepted fact is either cited by a unit or listed in omitted with a concrete reason") on an api_reference intro task with hundreds of `public_symbol:ai.*` facts -> the reply lists each in `omitted` until 8000 tokens. Fix: exempt hub symbols from the omitted rule and set `maxItems` on `omitted` (S).
- PDF-TS: S4 batch reply (`448cecb38222`) is one disposition followed by 96,000 characters of tabs and spaces (32000 tokens, 819 s). The message says "never retry"; a different request is not a retry: halve the batch (`reconciliation/dispositions.py:reconciliation_narrowing` exists) and stop on a whitespace run (S-M).
- PDF-Python NOT_READY: the sealed row is ACCEPT, noop VERIFIED, but `present-2` logs `re-sealed: examples.json changed since the last seal; proof withdrawn`: the captured stdout of several examples contains library log lines with wall-clock timestamps (`2026-10-11 19:42:01,023 [INFO] aspose_pdf: Document resources released.`), so two fresh processes never produce byte-identical receipts and BC-11 stays PENDING. Fix: normalise timestamps (and pids) in stored example stdout/stderr in the receipt writer (`core/examples.py`, next to the `<workspace>` normalisation). S. (Hypothesis from the final examples.json; the first run's receipt was overwritten, so confirm with a double run.)
- Email-Cpp: C++ examples now verify (quick_start included, additional_examples excluded); the reconciler's VERIFIED_PRESERVE into `additional_examples` is folded to DEFER and not classified (see Cause 2).

## 7. Fix order (rows unblocked per effort)

1. LST-01 (Cause 1): label-or-content test, owed-list identifier exemption, and drop the authoring-time rejection in favour of placement's uncovered remainder. S, up to 10 rows (the JMAP libraries shed their main blocker).
2. Stray gate (Cause 4): slash-pair split, camel/lowerCamel blind spot, delete-the-sentence recover. S, up to 7 rows (Cells-Java, TeX, Slides-Cpp, 3D-.NET, PDF-Java, Slides-Java, JMAP-Java).
3. S4 destination enum + recover-prefers-preserve + per-unit targeted repair (Cause 2). M-L, 7 of 9 BC-05 rows (Words-Python needs Python 3.12 first).
4. BC-07 v11 referent coordination (6 secondary rows): when a kept paragraph says "below"/ends with a colon and its referent is superseded or deferred, supersede the paragraph with it (`coordinate_neighbor_promises`). S-M.
5. Reviewer self-contradiction rule (Cause 5). S-M, 2-3 rows.
6. Ops: rerun Cells-Rust; install Python 3.12 (Words-Python); file upstream issues for 3D-Python, Page-Python, GIS; PDF-Cpp configure; PDF-Python double-run after the receipt fix.
7. PDF-Go omitted bound, PDF-TS batch halving, JMAP-Cpp hygiene/coherence.

Do not do: loosening BC-05 v7 or LST-01 as gates (they caught real losses in 5 of the 8 wave-3 seals); the fixes above are on the generation side or in the two gates' heuristics.

## 8. Method notes

- Rule counts come from `calls/*.rejected-N.json` of every wave-4 clone (rule classified from the message), final-attempt rejections per failed job, and `validation.json` of the last round (for sealed or repaired rows the transaction `validation.json` can be an earlier round; `failure_detail` in results.jsonl is authoritative).
- Wave-3 comparison used G:\rp-w3 (same revisions in most clones; `dispositions.json`, `README.md`, `examples.json` per row).
- Scripts are in the scratchpad (rulekey.py, showrej.py, listmiss.py, disp.py, valfail.py, allfails.py, finalrej.py).
