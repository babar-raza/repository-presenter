authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# BC-10 triage, reseal cut 1 (013aa79e) and cut 2 (ca69dad4, 16 of ? rows at read time)

Method: for every row with failure_class BC-10 I read the failed transaction under `<clone>/runs/transactions/<repo>/<rev>/`
(review.json final findings, repairs.json, validation.json BC-10, README.md candidate, source/README.md original,
facts.json, dispositions.json, calls/*.json). Digest scripts: scratchpad `dig.py`, outputs `dig1.txt`, `dig2.txt`.
Note: `<clone>/candidates/...` holds OLD committed bundles from main (some ACCEPT); the failed run is only in `runs/transactions`.
Note: repairs.json labels (F01...) are first-round review labels; review.json findings are the second (final) read.

Scope: 17 BC-10 failures = 10 in cut 1 (of 35 failures; the other 25 are model_output/BC-02..07/BC-14), 7 in cut 2 (no new BC-10 between first and last read; 16 rows).
60 final findings total (html-python alone 14). Verdicts: 11 REJECT_PRESENTATION, 6 REJECT_FACTUAL.
Classes: (a) true candidate defect, (b) reviewer error / over-strict / renderer-owned text, (c) upstream-caused (facts / extraction).
Totals: a = 25, b = 31 (17 excluding html), c = 4.
Repos whose BC-10 failure is entirely (b)/(c), i.e. no real candidate defect: html-python, email-net (cut 1), note-python, pdf-net, slides-net = 5 of 17.

Repair loop facts (74 repair attempts across the 17): 45 repaired, 13 "section X is deterministic; its blocks change only when facts change"
(installation 7, at_a_glance 5, identity 1) = unrepairable by design, 6 misrouted (all lead-in/duplicate-example defects: the
repair is sent to RECONCILING and its "change claims X changed" is rejected twice), 4 "matches the stage's own output unchanged; a no-op cannot repair",
5 escalated to S5 and not resolved, 2 blocked by BC-04 "identifiers that are not accepted fact values" (pdf-java, barcode).

## Per-finding table (final round)

| Repo | Finding (section) | Class | Causal stage | Generic mechanism / universal fix idea |
|---|---|---|---|---|
| barcode-py | F01 at_a_glance diagram lost symbology names/outputs | b (renderer-owned; repair impossible) | PLANNING (capability titles) | Reviewer compares a deterministic diagram to the original; scope-exclude renderer-owned sections |
| barcode-py | F03 scope_limitations: PDF limitation stated 3x | a | COMPOSING/PLANNING | Same limitation assigned to several limitation:N slots (to_pdf, PdfRenderer, scope); dedupe per fact across slots |
| barcode-py | F05 doc_resources: "classes like AUTO, H, methods data, render..." | a | COMPOSING | Link-description slot padded with enum-member/method names the model never read; link slot text must be original link text only |
| 3d-java | F01 installation lacks Maven/Gradle snippets | a | PLANNING/COMPOSING + renderer | Original install alternatives were moved into additional_examples (after the last example, inside `<details>`); renderer installation emits only one command |
| 3d-java | F02 additional_examples holds Maven/Gradle dependency blocks | a | same | same root cause as F01 |
| 3d-java | F04 scope_limitations less specific (OBJ stub, silent failures dropped) | a | RECONCILING | list unit 072 marked VERIFIED_PRESERVE, 2 of its items silently absent; opening also overclaims "STL, OBJ, U3D" (advisory) |
| cells-net | F02 quick_start trailing "Create a workbook, write and format cells, and save it:" | a | RECONCILING->COMPOSING | Lead-in paragraph (unit 016/025) VERIFIED_PRESERVE'd while its code fence is superseded by the verified example; lead-in lands after the example, no payload |
| cells-net | F05 scope section duplicated | a | PLANNING/RECONCILING | Authored limitation slots AND the preserved inherited list both render; no dedupe between authored and preserved units |
| cells-net | F07 additional_examples orphan "Load a workbook with recovery diagnostics:" / "Export a worksheet to PDF:" | a | RECONCILING->COMPOSING | Same lead-in decoupling |
| cells-java | F01 opening "solves problems..., Users include Java developers" | b (borderline) | PLANNING | Text derives from investigation audience/problems_solved (by design); reviewer compares to original. Prompt reconciliation needed |
| cells-java | F07 scope omits "public XML-mapper classes are unimplemented skeleton code" | a | RECONCILING | 5-item list unit 048 VERIFIED_PRESERVE'd with only 3 items rendered |
| email-net c1 | F02 deps "No required third-party package dependencies; in `...csproj`, no `PackageReference`..." | b | renderer-owned | Reviewer asks to reword deterministic text (also ugly: fact evidence string pasted as prose) |
| email-net c1 | F04 "does not support IMAP, SMTP, or POP3..." | b | -- | Claim is in the original; reviewer repair is tautological ("does not support IMAP support") ; tool tagged none |
| email-net c1 | F05 TNEF | b | -- | tool tag FACTUALITY_UNCHECKABLE; claim verbatim from original |
| email-net c1 | F06 calendar | b | -- | same |
| email-python | F01 opening says reads `.eml`/writes `.msg` | a | EXTRACTING/COMPOSING | format:input.eml is derived from an example, but original says direct EML parsing is not implemented (goes through Python `email`); plus invented "It solves..., Users include" |
| email-python | F02 at_a_glance only EML/MSG in, MSG out | c | EXTRACTING (format facts) | format facts omit CFB in/out and EML out; diagram is deterministic (unrepairable) |
| email-python | F03 key_capabilities lacks CFB capability | a | PLANNING | core_capabilities omitted a headline capability present in the original and in facts |
| page-py | F01 opening "solves the problem ... without requiring a full commercial suite" | a | COMPOSING | Invented promotional claim, no fact |
| page-py | F02 at_a_glance misses "from scratch" start and Outputs | c | PLANNING (input/output ids) | deterministic diagram, unrepairable |
| page-py | F05 scope: "minimal Model-View-Presenter server ... via the MCP protocol" | a | COMPOSING | Acronym MCP (Model Context Protocol) expanded wrongly; no check on expansions |
| page-py | F06 dev/testing "repeats make commands" | b | -- | The two blocks differ (make sync/test vs make build); reviewer misread |
| html-py | F03-F16 (14, api_reference): "`aspose_html.DOMParser` / `dom.HTMLAddressElement` not supported; use lowercase `aspose_html.dom.htmladdresselement`" | b (14) | -- | Reviewer confused lowercase fact IDs with symbol values: `public_symbol:aspose_html.domparser` (value `aspose_html.DOMParser`) exists, SUPPORTED. Real but only advisory: renderer split `skia-python>=87.0,<145` on the comma into two bullets (`<145`) |
| slides-net | F01 .NET badge says net8.0 only, CI badge missing | c (+b) | EXTRACTING | package:target_framework = "lowest target framework the project declares" collapses `net8.0;net10.0`; the CI badge exists (as "Build Status"), so that half is reviewer error |
| slides-net | F02 CI badge omitted | b | -- | present in candidate under a different label |
| slides-net | F03 net10.0 missing | c | EXTRACTING | same TFM collapse |
| slides-py | F03 "after installing the package from the repository" | b | -- | Original says install from repo for the MD behaviour; candidate is right |
| slides-py | F06 scope: "API members are not implemented and absent: BENT_CONNECTOR3, CIRCLE, ... add_chart, save, slides ..." (58 names) | a | RECONCILING->COMPOSING | Lead-in "The following are not implemented...:" (unit 114) split from its list (unit 115 merged into limitation:2); composer invented a payload from fact-value identifiers (passes BC-04), directly contradicting public API facts |
| slides-py | F07 "conversion not implemented" vs MD export | b | -- | Verbatim original, pedantic |
| slides-py | F08 dev/testing lacks `pip install -e .[test]` | b | -- | advisory-grade preference |
| pdf-java | F02 installation lacks Maven XML snippet | a (reviewer calls it factual; it is omission) | renderer / PLANNING | renderer prints `mvn dependency:get` only; same as 3d-java |
| pdf-java | F05-F10 scope omits 6 original limitations (setAllowExceptions, text replacement, resource optimization, tagged PDF, PDF/X, public-key PDFs) | a (6) | RECONCILING | list unit 131 VERIFIED_PRESERVE with most items dropped; the repair was rejected twice by BC-04 ("Document.validate/Document.convert, PdfFormat.pdfX1a2001 are not accepted fact values") |
| cells-ts | F01 opening omits "free, open-source", HTML | b | -- | marginal preference, SINGLE_READER_PROSE |
| cells-ts | F02 key_capabilities omits pictures/shapes | b | -- | same |
| cells-ts | F04 scope: "does not provide methods to add new shapes or images" | a (c: stale upstream README) | RECONCILING | Negative claim preserved verbatim although `Worksheet.addShape/addImage` are SUPPORTED symbols; BC-04 cannot see negation vs symbol contradiction |
| pdf-net | F02 key_capabilities too condensed (PDF/UA, comparison) | b | PLANNING | 8 bullets for a 1,300-symbol product; subjective |
| 3d-py | F02 trailing "Build a scene from scratch and export it to glTF:" + "More real, verified snippets..." | a | RECONCILING->COMPOSING | lead-in decoupling |
| note-py | F03 "Encrypted OneNote files are not supported; password raises ..." | b | -- | identical to original; reviewer's finding contradicts itself |
| note-py | F04 "Writing back to .one is not implemented" | b | -- | same |
| email-net c2 | F03 dependencies (same deterministic text) | b | renderer-owned | as email-net c1 F02 |
| email-net c2 | F04 "email processing for MSG, EML, and MHT formats" | a | COMPOSING | "MHT" appears in neither facts nor source README; scope-intro slot hallucination |
| cells-rust | F02 "Create a workbook, write typed values ... load it back:" after the code block | a | RECONCILING->COMPOSING | lead-in decoupling (unit 025 VERIFIED_PRESERVE after example) |

(email-net first-round also had a real renderer defect: Installation says "version 0.1.0" (package:version from csproj) while
package:published_version = 26.7.0; it is unrepairable and recurs in both cuts. It no longer appears in the final findings because the
second read keyed on other items, but the text is still in both READMEs.)

## Ranked generic causes

1. Reviewer error / over-strictness (b): 31 of 60 findings, 11 of 17 repos; sole reason for 4 failures (html-python 14 findings from
   case-folded fact IDs, email-net c1, note-python, pdf-net). Sub-patterns: (i) finding contradicts the facts or restates the candidate
   (note-python F03/F04, html), (ii) finding on renderer-owned text the candidate cannot change (at_a_glance, installation, dependencies, identity,
   badges: 13 of 74 repair attempts die as "deterministic"), (iii) reviewer demands original wording/preferences (cells-ts F01/F02, pdf-net F02).
   The tool already tags many of these (`RENDERER_UNWRITTEN_FACT_FACTUAL`, `FACTUALITY_UNCHECKABLE`, `VERIFIED_SYMBOL_NAMED`, `SINGLE_READER_PROSE`)
   in `unrefuted_scope_rules`, yet a corroborating second read still sustains them.
   Example: html-python F10 "aspose_html.dom.HTMLArticleElement ... not supported; supported is aspose_html.dom.htmlarticleelement" (lowercase id).
2. Renderer-owned / extraction-owned content that is lossy and unrepairable (a/c): 8 final findings, 7 repos (3d-java, pdf-java, barcode, email-python, page,
   slides-net, email-net). Maven/Gradle alternatives never reach Installation; at_a_glance diagrams generic; multi-TFM collapsed to the lowest;
   published version vs csproj version; dependency specifier split on comma.
   Example: slides-net badge `net8.0` while source says `net8.0` and `net10.0` (fact value: "lowest target framework the project declares").
3. Invented or unsupported prose from the author model (a): 6 final findings, 5 repos (barcode, page x2, email-python, email-net, cells-ts) plus the
   cells-java opening and the 3d-java opening overclaim "STL, OBJ, U3D" (advisory). 13 of 17 openings use the "It solves... / Users include..." shape.
   Example: page-python "Model-View-Presenter server" for MCP; email-net "MSG, EML, and MHT".
4. Lead-in / payload decoupling (a): 5 final findings, 4 repos (cells-net x2, cells-rust, 3d-python, slides-python), latent in page-python (`PS/EPS-to-image conversion:` before `</details>`).
   A preserved lead-in paragraph ends in ":" but its code fence/list was superseded or merged; the composer either leaves it dangling or invents a payload.
   The repair loop cannot fix it (6 misrouted attempts rejected twice).
   Example: cells-rust README line 126 "Create a workbook, write typed values and a formula with a cached result, save it as XLSX, and load it back:" directly before `## API Reference`.
5. Partial preservation of multi-item inherited lists (a): 8 final findings, 3 repos (pdf-java 6, cells-java 1, 3d-java 1) plus barcode ECI/GS1 (advisory).
   Unit-level VERIFIED_PRESERVE passes BC-05/BC-08 while individual items vanish; restoring them is blocked by BC-04 when the item names an identifier that is not a fact value.
   Example: pdf-java unit 131 (7 limitation bullets) rendered with one item.
   Runner-up: duplicated content (authored slots + preserved unit): barcode F03, cells-net F05.

## Fixability without a governed-version bump
(GOVERNED = renderer.py, composition/authoring.py, review/independent/review.py, validation/registry.py per tests/test_version_bump_discipline.py;
prompts/*.yaml, reconciliation/dispositions.py, planning.py, jobs.py, evidence/facts/* are not.)
1. Reviewer errors: partly data. `prompts/independent_review.yaml` can say: fact IDs are lowercase-normalised, match on `value`; judge only against the facts, not
   the original wording; do not raise findings on renderer-owned sections. A deterministic downgrade of the already-tagged scope rules is `review.py` = REVIEWER_LOGIC_VERSION bump
   (only yields VALID_UPDATE_AVAILABLE, never blanket invalidation).
2. Renderer/extraction: renderer fixes (Installation alternatives, published-version precedence, comma-safe specifiers) are governed (RENDERER_VERSION). Multi-TFM
   extraction and format facts (evidence/facts/*) are not governed. at_a_glance titles/format ids are plan data (presentation_planning prompt).
3. Invented prose: `prompts/section_authoring.yaml` (no acronym expansion unless a fact states it; link slots echo original link text; no format names outside facts)
   needs no bump; a deterministic guard for expansions/format tokens would go in the validator (governed per-check bump).
4. Lead-in decoupling: the cheapest correct fix is in `reconciliation/dispositions.py` (lead-in paragraph travels with, or is superseded together with, its fence): not governed.
   A normalisation backstop (drop a trailing ":" paragraph without payload) is `authoring.py` = NORMALISATION_VERSION bump.
5. Partial list preservation: item-level coverage in `dispositions.py` / reconciliation prompt: no bump; a validator check (BC-08 item coverage) = per-check bump.
