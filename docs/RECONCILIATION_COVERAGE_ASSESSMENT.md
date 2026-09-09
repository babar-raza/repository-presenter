# Reconciliation-time API-reference coverage — a production assessment (2026-09-09)

## Context

CS-02's Email-Python re-seal attempt genuinely rejected (`BC-10`/`REJECT_PRESENTATION`, finding
F03: the composed candidate's API reference carries the Core API table *and* a duplicate
list-format rendering of the same classes). Per this pass's own rule, it was not forced through.
This document is the required deep-dive before touching any code, triggered directly by the
owner's own standard: *"go deeper than the previous analysis... distinguish what should be
preserved from what must be redesigned... do not exaggerate confidence where evidence is weak."*

## 1. Symptom

`present` for Email-Python fails at COMPOSING with a real, correct reviewer finding: five
`inherited_unit:0NN.list` units (053, 055, 057, 059, 061), each listing a group of classes or
enums, render as prose lists *alongside* the renderer's own deterministic Core API table that
already lists every one of those same classes. A repair round attempted to fix the composed text
and the equivalent finding recurred - repair could not resolve it.

## 2. Root cause, traced to exact code and exact data (not inferred)

`reconciliation/dispositions.py` already has a deterministic normalization pass for `api_reference`
- but it is narrower than it looks:

```python
if disposition in PLACING and destination == "api_reference" and unit.endswith(".table"):
    # README_CONTRACT.md row 14: the Core API table is deterministic from the verified
    # symbol facts, so an inherited API table placed here is covered by it, never
    # rendered beside it (the re-asked reconciler placed two such tables on the canary).
    entry["disposition"] = "SUPERSEDE_REDUNDANT"
```

This rule only fires for a unit whose *shape* is a markdown table (`.table` suffix). It has never
covered a `.list`-suffixed unit enumerating the same symbols in prose-bullet form - a shape the
2026-09-09 healing pass's own RC-02 fix (`placement.py`'s `api_reference_covered_fact_ids`) taught
the *renderer/placement* layer to recognize as redundant, but never taught this *reconciliation*
normalization pass to recognize.

**Confirmed against Email-Python's real, current data**, not assumed:

| Unit | Disposition | Cited symbols' `symbol_kind` |
|---|---|---|
| `053.list` | `VERIFIED_PRESERVE` | 4× `class`, 1× **`module`** (`mapi_message`) |
| `055.list` | `VERIFIED_PRESERVE` | 6× `class` |
| `057.list` | `VERIFIED_PRESERVE` | 5× `class` |
| `059.list` | `VERIFIED_PRESERVE` | 6× `enum` |
| `061.list` | `VERIFIED_PRESERVE` | 2× `class` |

Every one of these units' cited symbols (bar one) already appears in a **separate `.table` unit
that the existing rule already superseded** (e.g. `053.list`'s four class citations are a subset
of `048.table`'s already-`SUPERSEDE_REDUNDANT` citations). The gap is exactly, narrowly: the
existing rule checks the unit's *shape*, not its *content overlap* - so a `.table` duplicate of
covered content is always caught, and a `.list` duplicate of the identical content never is.

## 3. Why this is not simply "reuse `api_reference_covered_fact_ids`" (a real sequencing constraint)

RC-02's own coverage function needs a `plan` argument - `api_hubs`, chosen during **PLANNING**.
Reconciliation runs **before** planning in the pipeline (EXTRACTING → INVESTIGATING → RECONCILING
→ PLANNING → COMPOSING). `dispositions.py` cannot call a function that needs data that does not
exist yet at the point it runs. This is not a wiring inconvenience - it is why the existing
`.table` rule works the way it does: `renderer.py`'s own Core API table (`_api_reference`,
lines 455-461) is built from `context.supported("public_symbol")` filtered to
`attributes.symbol_kind in {"class", "enum"}` alone - **no `plan` input at all**. Only the
*Detailed Member Reference* (hub-grouped methods, RC-02's own plan-dependent
`api_reference_hub_methods`) needs the plan. The Core API table's own coverage is fully
plan-independent, decidable from `facts.json` alone - exactly what reconciliation already has.

This means the fix is not "reuse RC-02's function" (impossible, wrong stage) but "extract the
already-plan-independent half of what that function computes, as its own small function
reconciliation can call directly against `facts` alone."

## 4. The one honest wrinkle, found empirically, not assumed away

`053.list` cites `public_symbol:email_foss.msg.mapi_message` with `symbol_kind: "module"` - not
`class`. A strict "every cited symbol must be a covered class/enum" rule (the safer, more
conservative design, matching this pass's "prefer under-triggering when uncertain" discipline
throughout) would **not** fire for this one unit, leaving it un-normalized. The other four units'
citations are 100% class/enum, so a strict rule closes 4 of 5 real duplicates, not all 5.

Whether `053.list`'s `module`-kind citation is a genuine, separate concern (the paragraph really is
partly about the `msg` module, not only its classes) or an extraction misclassification is not
established here - checking it would mean reading the real README prose and the extractor's own
symbol-kind assignment logic, out of scope for a same-turn implementation decision. Flagging this
plainly rather than loosening the rule to "mostly covered" to force a clean sweep - a looser rule
risks superseding genuinely non-redundant content on some *other* candidate this pass has not
checked, which is a worse failure mode than leaving one unit under-normalized.

## 5. What to preserve

- The existing `.table` rule and its whole surrounding normalization pass in `dispositions.py` -
  correct, precedented, not touched.
- RC-02's `api_reference_hub_methods`/`api_reference_covered_fact_ids` - correct for their own,
  later (COMPOSING-time) purpose; not modified, only where a genuinely new, smaller, plan-independent
  function is extracted alongside them.
- The pipeline's own stage ordering (reconciliation before planning) - not violated by making
  reconciliation depend on plan data, which this design deliberately avoids.

## 6. What must be added (narrow, not a new validator class)

One new, small, plan-independent function - e.g. `covered_class_enum_symbol_ids(facts) ->
frozenset[str]` in `placement.py` (beside its plan-dependent siblings, so the "what does the Core
API table cover" logic has one home, not two that can drift) - and one new branch in
`dispositions.py`'s existing normalization loop:

```python
if (
    disposition in PLACING
    and destination == "api_reference"
    and not unit.endswith(".table")
    and cited
    and cited <= covered_class_enum_symbol_ids(facts)
):
    entry["disposition"] = "SUPERSEDE_REDUNDANT"
```

This is additive to the existing rule (the `.table` branch keeps firing for tables; this new
branch catches the same redundancy for any other shape), reuses the exact `PLACING`/`cited`
variables already in scope, and needs no new schema, no new disposition value, no new prompt
change - a reconciliation output that used to need this normalization will get it the same way a
`.table` unit already does, without the LLM's own reconciliation prompt needing to change at all
(the normalization runs on its *output*, after the call, exactly like every other rule in this
function).

## 7. What this does NOT fix, and should not be asked to

- **`053.list`'s residual duplication** (the `module`-kind citation) - stays `VERIFIED_PRESERVE`
  under this design. If the review still rejects Email-Python after this lands, that is the
  expected, honest remainder - not a sign the fix is wrong.
- **Any candidate this design has not been checked against.** Verification step 8.2 below is
  required before trusting this beyond Email-Python.
- **`evaluate()`'s own invalidation-stage mapping** (`components.*` uniformly reopening
  `COMPOSING`, never `RECONCILING`) - a separate, real finding (`docs/CI_AND_STALENESS_ASSESSMENT.md`
  and CS-04's note in `docs/STATE_MACHINE.md` section 9) that this fix does not need to resolve:
  the new function lives in deterministic reconciliation-normalization code that always runs on
  every `present` invocation regardless of `evaluate()`'s own stage bookkeeping - it needs no
  invalidation trigger of its own, since reconciliation reruns whenever anything upstream of it
  changes for an unrelated reason, or a fresh `present` is explicitly requested (as this taskcard's
  own re-seal is). Conflating the two would be scope creep; noted for completeness, not folded in.

## 8. Validation steps and regression controls

1. **Before landing**: run the new function against Email-Python's real `facts.json` directly
   (not through the full pipeline) and confirm it returns exactly the covered symbol set the Core
   API table would render - cross-check against `renderer.py`'s own `_api_reference` output for
   the same candidate, byte-for-byte on the class/enum names.
2. **Portfolio check, not assumed**: run the new normalization branch against every one of the 8
   real sealed candidates' current `dispositions.json`/`facts.json` (not just Email-Python) and
   diff the resulting dispositions before/after - confirm no currently-`VERIFIED_PRESERVE` unit on
   any OTHER candidate flips to `SUPERSEDE_REDUNDANT` incorrectly (a false positive would be a real
   regression: dropping content a reader should see). This is the direct application of this
   session's own established discipline ("verify against real data before trusting a design"),
   which caught RC-02's own union-vs-replace bug and TB-02/RC-03's over-eager heuristics before
   they shipped.
3. **Regression tests**: a mutation test (a synthetic `.list` unit citing only covered class/enum
   symbols → normalized; the same unit citing one non-covered or module-kind symbol → left alone,
   reproducing the `053.list` wrinkle exactly as a named, honest test case, not hidden); a no-op
   case (a `.list` unit under a *different* section is untouched).
4. **Re-attempt Email-Python's `present` after landing**: confirm the finding count drops (4 of 5
   duplicates resolved) even if the transaction does not fully accept - report the real outcome,
   do not claim full resolution if `053.list`'s residual duplicate still triggers a finding.
5. **Full suite once**, then the standard commit/push/`gh run watch` cycle.

## 8a. Verified against the full portfolio, and found unsafe as designed — not shipped

Section 8's own validation step 2 was carried out before committing anything, and it changed the
conclusion. Running the proposed rule (implemented, then reverted before any commit -
`git checkout --` on both touched files, matching this pass's own established discipline for a
design found wanting) against all 8 real sealed candidates:

| Candidate | Units flipped |
|---|---|
| 6 of 8 candidates | 0 |
| Aspose.Email FOSS for Python | 5 |
| **Aspose.Cells FOSS for Rust** | **22** |

Cells Rust's 22 flips include `inherited_unit:044.heading` (`"## Project Structure"`) and
`045.paragraph` (a paragraph about `src/Aspose.Cells_FOSS/`'s module layout) - content with
**nothing to do with the API reference**, caught only because it happens to cite class-symbol
facts as incidental supporting evidence while describing something else entirely. Restricting the
rule to `.list`-suffixed units only (dropping the over-broad "any non-`.table` shape" match) still
left real, non-trivial risk: Cells Rust's own genuine `.list` units (e.g. `059.list`,
`061.list`) enumerate class names **and their method signatures**
(`` `Workbook` ``: `new() -> Workbook`, `load_xlsx(path)`, ...) - the disposition's own `fact_ids`
cite only the class-level symbol, so the strict-subset check still fires, but the unit's actual
*content* carries method-signature detail the Core API table does not show and the Detailed
Member Reference will only show if planning happens to pick that exact class as a hub. Superseding
it risks real content loss, not merely a harmless duplicate removal - this is exactly the "member
reference list" granularity question `production-consistency-reassessment.md`'s own **RC-06**
already flagged as high-risk, prototype-first, not something to fold into a same-turn fix.

**Decision: not shipped.** The implementation (the `covered_class_enum_symbol_ids` extraction in
`placement.py`, the new `dispositions.py` branch, and its test) was reverted before any commit,
the same reversal path RC-03's own prototype took. Sections 1-8 above remain an accurate,
verified diagnosis of Email-Python's specific rejection and are kept as the record of what was
checked and why the obvious-looking fix does not generalize safely - not as a description of
something now landed. Closing this properly needs RC-06's own prototype-first process (checking
the true information content of a flagged unit, not just whether its citations happen to be a
symbol-ID subset) before any version of this rule ships, on any candidate.

## 9. Tradeoffs, risks, and honest limits

- **This may not fully unblock Email-Python.** Said plainly per the owner's own instruction not to
  overclaim: if `053.list`'s module-kind citation alone is enough to trip BC-10 again, Email-Python
  stays unsealed after this lands, and that is the correct, honest outcome to report - not a
  reason to loosen the matching rule reactively without checking its effect on the rest of the
  portfolio first.
- **The strict-subset rule is deliberately conservative** and will under-fire on any unit that
  mixes a covered symbol with an uncovered or misclassified one. The alternative (a looser,
  majority-overlap rule) would resolve `053.list` too, but was not chosen without checking its
  false-positive rate against the other 7 candidates first - exactly the corner this pass has cut
  before (RC-03, TB-02 part 2) and paid for. Loosening it is a legitimate follow-up, not a
  default.
- **A genuinely different, larger question this document does not answer**: is `mapi_message`'s
  `module` classification itself correct? If it should be `class`, the *real* fix is upstream in
  extraction, not in this normalization rule at all - flagged, not investigated further here.
