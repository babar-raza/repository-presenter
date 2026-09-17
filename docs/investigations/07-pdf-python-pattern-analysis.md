# Investigation 07: The PDF-Python redraw pattern

Status: investigation only, no implementation, no redraw attempted by this session. Written
2026-09-17. Commissioned directly by the owner after `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`
was redrawn repeatedly this sprint, each time clearing one blocker only to hit a new one. Question
asked: is there a deeper systemic pattern to this one repository's own redraws, or a string of
unrelated coincidences? Modeled on `docs/investigations/06-words-net-pattern-analysis.md`
(Words-.NET), read in full before writing this one.

**Headline finding, stated first because it changes what "current blocker" means:** the fix for
the most recent measured blocker (item 119/PDFPY-02) **has already landed** on `origin/main`
(`0ced0a5`, 2026-09-17 08:09:07 UTC) — but **no redraw has run against it yet**. `git worktree list`
and a scan of `C:\w\`'s own log files (checked before writing anything below, per this project's own
"verify no redraw is in flight" discipline) show a `pdfpy2` worktree whose logs stop at 07:12 UTC,
before the fix landed, and no `pdfpy3` or equivalent has started since. The repository's own next
actionable step is simply: run the redraw. Everything else below is diagnosis of the pattern behind
four prior blockers and two additional latent risks of the identical shape, found by reading the
current source directly.

Primary evidence: `docs/DECISION_LOG.md` (§31-shaped entries, 2026-09-11 through 2026-09-17),
`docs/RESEARCH_LANE_E.md` (lane E's own narrative, `LANE-E-01` runs 1-2 and the `pdfpy` worker's
`LANE-E-08`/`LANE-E-09` entries cross-referenced from `DECISION_LOG.md`), `git log`/`git show`
against `origin/main`, and the current source tree (`composition/authoring.py`,
`composition/planning.py`, `composition/coherence.py`, `investigation/dossier.py`,
`reconciliation/dispositions.py`, `repair/targeted.py`, `review/independent/review.py`,
`prompts/section_authoring.yaml`). Before writing anything, `git fetch origin main` confirmed the
tip (`e5efae1`) and `git worktree list` was read in full: `C:/w/pdfts1` (`pdfts/investigate`) is a
PDF-**TypeScript** redraw, unrelated; `C:/w/e05r5` (`lane-e/LANE-E-05-R5`) is a Words-**Python**
redraw, unrelated; none of the ten `D:\...\worktrees\agent-*` checkouts is on a PDF-Python-named
branch. No concurrent PDF-Python work was found in flight.

## 1. The timeline, run by run

| When (UTC) | Run / commit | Stage reached | What blocked it | Cause |
|---|---|---|---|---|
| 2026-09-07 | G3 second pass, revision `109e26a1` | S4 `source_reconciliation` | `RECONCILIATION_EMITS_A_SCHEMA_KEY_AS_A_FACT_ID` | Pre-existing S4 schema gap (`fact_ids` had no enum), later item 40's own target |
| 2026-09-11 08:25 | `LANE-E-01` run 1, revision `bc527450` | S4 (in flight) | Run stopped mid-call by a supervisor `Reviewer:` message: S4 was blocked for **every** Python repository pending item 40's fix, so no disposition was recorded for this repository specifically | same S4 schema gap, item 40 |
| — 01:50 | fix `e2a1a83` lands | — | — | item 40 v1 ("symbol-kind-bound public symbols and a `fact_ids` shape") |
| — 08:50 | fix `352fd35` lands | — | — | item 40 v2/S4-REGRESSION ("`fact_ids` decode from an enum of the packet's own IDs, never a bare kind prefix") |
| 2026-09-11 09:49 | `LANE-E-01` run 2, revision `bc527450` | S9 `COMPOSING` (BC-07) | S4 confirmed genuinely fixed live (the 689-value `fact_ids` enum did **not** trip an HTTP 400 — the run's own proposal E3 predicted it might and was refuted by measurement). New finding: BC-07's canonical-abbreviation judge correctly rejected the bare word `pdf` inside this repository's own slug (`aspose-pdf-foss-for-python`) in running prose, but never set `Failure.section`, so `repair/targeted.py` could never route it to a repairable stage — a permanent, unrepairable finding | new, proposed as `E4`/item 78 |
| — 2026-09-16 16:13 | fix `609207e` lands | — | — | item 78/`E4` ("BC-07's abbreviation failure now names the LLM-owned section it belongs to") — landed **5 days** after being proposed; see §3's supervision-latency finding |
| 2026-09-16 18:01 | `pdfpy/LANE-E-08`, revision `7c472f37` | S10 review (BC-10) — first time this repository ever reached S10 | Item 78/`609207e` confirmed closing BC-07 live (version 4 PASS, first clean pass ever on this repository). New finding: `review.py`'s `factuality_defect` CONTRADICTED-stands gate read a finding's own self-reported `fact_ids` rather than the reviewed unit's own citations (`unit_fact_ids`), so a reviewer-added CONTRADICTED fact — cited only as unrelated context, never by the unit itself — permanently blocked an otherwise SUPPORTED, verbatim-correct claim | new, proposed as `PDFPY-01` |
| — 2026-09-17 05:34 | fix `14cb4d3` lands (bundled with item 71) | — | — | item 91/`PDFPY-01` ("review: widen a link's own target and scope a CONTRADICTED gate to the reviewed unit") |
| 2026-09-17 06:36 | `pdfpy/LANE-E-09`, same revision `7c472f37` | S6 `section_authoring` | Item 91/`14cb4d3` confirmed landed and correct **by reading the code** (this repository never reached S10 this run, so the fix could not be re-exercised live). New finding: two independent `present` attempts both aborted identically at S6 with `TruncatedOutput`, `completion_tokens` exactly 8000 both times — `_type_batches` built each undocumented-type `SectionTask` with no `slot_facts` binding, so `citable()` fell back to the **whole 32-type batch's** `accepted_ids` as every slot's schema enum instead of that type's own single fact: an O(n²) schema (66,130 characters for one batch, 4.6× larger than scoped) | new, proposed as `PDFPY-02` |
| — 07:52 | item 119 admitted (`ac4633e`) | — | — | item 119/`PDFPY-02` |
| — 08:09 | fix `0ced0a5` lands | — | — | item 119/`PDFPY-02` ("scope `_type_batches` slots to their own fact") |
| **now** | **no redraw yet** | — | **Nothing has run against `0ced0a5`.** `pdfpy2`'s own logs (`C:\w\pdfpy2-*.log`) stop at 07:12 UTC — before both `ac4633e` and `0ced0a5` landed — and no successor worktree exists. | — |

Four real, distinct blockers found across the repository's redraw history, each one closed before
the next was discoverable (S4 can't be diagnosed while the pipeline never leaves S4; BC-07 can't be
diagnosed while every repository is stuck at S4; S10's factuality gate can't be diagnosed while
BC-07 never lets a run reach S10; S6's batch-schema gap can't be diagnosed while S10's gate blocks
every run before repair ever tries a second `present` that would reach S6 with a large enough
batch). This is exactly the "one real defect per stage reached, land it, redraw" mechanism
investigation 06 already described for Words-.NET, not a coincidence unique to this repository.

## 2. Scale, measured

PDF-Python is not the portfolio's largest repository by symbol count — `Aspose.PDF-FOSS-for-Java`
(24,830 `public_symbol` facts) and `Aspose.Words-FOSS-for-.NET` (6,638) both dwarf it — but it is
large enough that two of its four blockers (item 78/E4's routable-abbreviation gap, triggered by its
own hyphenated slug; item 119/PDFPY-02's batch-schema gap, triggered by its own undocumented-type
count) are specifically **content-shape-triggered**, not size-triggered in the way Words-.NET's
item 85 was:

| Repository | Facts measured | S4 citable set (`reconciliation_schema`'s own enum) | Outcome as of this investigation |
|---|---|---|---|
| Page-Python | 735 records (570 `public_symbol`) | — | `NOT_SEALED`, S5 reject-loop (PGPY-04/05 chain) |
| **PDF-Python** | **1,583 records (1,376 `public_symbol`)**, revision `bc527450` | **689 values / 34,409 characters** (601 `public_symbol` at `DECLARED_SYMBOL_KINDS` granularity), measured live on `bc527450` | `NOT_SEALED`, awaiting the redraw against `0ced0a5` |
| Words-.NET | 6,790 records (6,638 `public_symbol`) | — | `NOT_SEALED` (item 90, BC-06) |
| PDF-.NET | 12,580 records (12,270 `public_symbol`) | 73,860 prompt tokens on its own largest S4 batch (F27, below) | Sealed, no-op proven |
| PDF-Java | 24,830 `public_symbol` facts alone | — | Sealed |

689 is comfortably inside `core/facts.py`'s `SYMBOL_CAP = 6000` — the S4 packet's own hard ceiling —
so PDF-Python's S4 calls have passed cleanly on every draw so far (LANE-E-01 run 2's own measurement:
"115 dispositions for 115 `inherited_unit` facts, citing 118 distinct fact IDs... All three S4 calls
returned HTTP 200 on attempt 1"). That this specific stage has not yet bitten PDF-Python is a
property of what has been *drawn* so far, not proof the mechanism is safe at this repository's own
scale — see §4.

## 3. Is this repository special, or a general defect surfacing here first?

Read each finding's own PROPOSAL text, not just its headline, exactly as investigation 06 did for
Words-.NET:

- **Item 40** (S4 `fact_ids` decode as a bare kind prefix): a shared-code schema gap in
  `reconciliation/dispositions.py::reconciliation_schema`, live and blocking **every** Python
  repository simultaneously (the supervisor stopped `LANE-E-01` run 1 for exactly this reason) and
  independently corroborated by lane C (Java) and lane D (Go) on the same class. Nothing about
  PDF-Python's own content caused this; PDF-Python was simply queued early enough in the Python
  cohort to be the repository lane E's own run measured it against.
- **Item 78/`E4`** (BC-07's unroutable abbreviation failure): general shared code in
  `validation/registry.py` — the canonical-abbreviation judge never sets `Failure.section` for
  *any* repository. PDF-Python is the repository whose own bare slug (`aspose-pdf-foss-for-python`)
  happened to spell the lowercase abbreviation `pdf` in running prose first, exposing a routing gap
  that is entirely general: any other lowercase-abbreviation-bearing slug or sentence hits the
  identical unrepairable dead end.
- **Item 91/`PDFPY-01`** (`review.py`'s CONTRADICTED-stands gate not scoped to the reviewed unit's
  own citations): general shared code in `review/independent/review.py`. The fix note states
  plainly that "every case items 39/63/83 measured had the CONTRADICTED fact among the unit's own
  citations" — PDF-Python is simply the first repository whose reviewer cited a CONTRADICTED fact
  as unrelated context rather than as part of the unit's own grounding, a shape any repository's
  review pass could produce.
- **Item 119/`PDFPY-02`** (`_type_batches`'s missing `slot_facts` binding): general shared code in
  `composition/authoring.py`, applicable to any repository whose `undocumented_types()` count is
  large enough to batch. PDF-Python's own batch happened to be big enough (66,130 characters, ~5×
  every other section's packet+schema combined) to trip the 8000-token completion cap first.

**None of the four confirmed blockers is a defect in the PDF-Python repository itself** (its
upstream README, manifest, or package metadata) — all four are shared composition/validation/review
gaps that PDF-Python's own scale and content shape happened to trigger before another repository
did. This is the identical conclusion investigation 06 reached for Words-.NET, generalized: the
"redraw, hit a new blocker" pattern is the arrival-item mechanism doing its job on two different,
independently-large repositories in the same sprint, not evidence that either repository is special.

**A second, independently-documented systemic cause, not repository-specific either.** A supervisor
entry dated 2026-09-16 12:45 UTC (`docs/DECISION_LOG.md`) records that lane E's own `E4` proposal
(PDF-Python, BC-07 routing) sat **unadmitted to the arrival list for five days** (2026-09-11 to
2026-09-16) — not because it was wrong ("each reproduced unchanged when lane E replayed it against
today's code, zero provider calls"), but because "nothing in the loop or supervisor cadence
guarantees a written PROPOSAL gets read and admitted." The entry names PDF-Python directly: "PDF-Python
and BarCode-Python stood the whole time on fixes nobody could land." Comparing the timeline above:
item 78 was proposed 2026-09-11 09:49 and landed 2026-09-16 16:13 — nearly five of PDF-Python's own
elapsed days were pure admission latency, not diagnosis time, and this cause is fully independent of
the repository's own content or scale. The three most recent blockers (items 91 and 119) did not
repeat this pattern — each landed same-day or next-day — so the admission-cadence gap looks like a
transient, already-self-diagnosed process failure (its own §31 entry proposes a periodic
`RESEARCH_LANE_*.md` sweep as the durable fix) rather than a standing tax on this repository.

## 4. Is there a further blocker already sitting there, undiscovered only because no one has reached it yet?

Yes, twice — one already diagnosed elsewhere and reconfirmed still open by reading today's source,
one new, found by reading every dynamic-schema-building function in the S3-S8 pipeline for the same
shape as item 119.

### 4a. F27 (already flagged by a different repository's own draw, PDF-.NET) — still unfixed, and PDF-Python's own S4 packet already exercises the exact same code path

`docs/RESEARCH_LANE_F.md` §F27 (PDF-.NET run 4, 2026-09-16, also cited in investigation 06 §4):
`reconciliation/dispositions.py::reconciliation_schema` pins each disposition's `fact_ids` *entries*
to an enum of citable IDs, but sets no `maxItems` on the `fact_ids` *array itself* — confirmed
unchanged in the current tree:

```python
# src/repository_presenter/components/readme/reconciliation/dispositions.py:247-256
schema = copy.deepcopy(manifest.manifest.output.schema_)
dispositions = schema["properties"]["dispositions"]
citable = citable_fact_ids(facts, manifest.manifest, batch_units, investigation)
if citable:
    dispositions["items"]["properties"]["fact_ids"]["items"] = {
        "type": "string",
        "enum": citable,
    }
    # <- no maxItems on the fact_ids array itself in this branch
else:
    dispositions["items"]["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
```

This is the *same file, same function* that item 40 already fixed once (the enum itself) — but the
sibling mechanisms in `composition/planning.py::_pin_fact_id_arrays` (`item_properties[field]["maxItems"]
= len(citable)`) and `investigation/dossier.py::investigation_schema` (`field_properties["fact_ids"]["maxItems"]
= len(dossier_ids)`) both set this exact bound, and `reconciliation_schema` alone omits it. PDF-Python's
own S4 packet already carries a citable set of 689 values (§2) — small relative to `SYMBOL_CAP`'s
6000-value ceiling, but real: nothing stops a future batch's `citable_fact_ids()` result from growing
toward that ceiling as this repository's own facts change, and F27's own measurement on PDF-.NET
(a 32,000-token truncation on batch 3 of 6, recovered only because an identical-digest retry happened
to return 3,016 tokens 21 minutes later) is a live demonstration of exactly this failure mode landing
on a same-family PDF repository already. This is not a new finding — it is a second, independent
confirmation (via PDF-Python's own measured exposure to the identical code path) that F27 remains
unfixed and still worth landing before, not after, a future draw trips it live.

### 4b. New: S8 `coherence_schema` has no `fact_ids` bound at all — worse than item 119's shape, and never mentioned in any RESEARCH file

`composition/coherence.py::coherence_schema` is the schema for S8's **single coherence pass** — one
call that returns *every* LLM-owned unit in the whole document at once, which its own docstring
already calls "the largest single `section_authoring` reply by construction." Item 75
(`docs/DECISION_LOG.md`, 2026-09-16 14:33 UTC) specifically targeted this call site and bounded the
**unit count**:

```python
# src/repository_presenter/components/readme/composition/coherence.py:87-107
def coherence_schema(
    manifest: LoadedManifest, existing_units: list[dict[str, Any]]
) -> dict[str, Any]:
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    count = len(existing_units)
    if count:
        units = schema["properties"]["units"]
        units["minItems"] = count
        units["maxItems"] = count
    return schema
```

That is the *entire* function. Unlike `authoring_schema` (S6's per-task calls), it never touches
`units["items"]["properties"]["fact_ids"]` at all — and `coherence_schema` is called with only
`(manifest, existing_units)` (`repair/rounds.py:281`: `call_schema=coherence_schema(loaded,
coherence_task_packet["existing_units"])`), so it structurally cannot thread a per-slot citable set
through even if it wanted to; it never receives `facts` or any `SectionTask.slot_facts` at all. Every
returned unit's `fact_ids` field therefore falls through to the **base manifest schema**, which
carries no enum and no ceiling of its own:

```yaml
# prompts/section_authoring.yaml:79
fact_ids: { type: array, minItems: 1, items: { type: string } }
```

So a coherence reply's own `fact_ids` array is unbounded both in *which* strings it may contain (any
string is schema-valid, not just a real fact ID — `authoring_schema`'s per-slot `enum` protection is
entirely absent here) and in *how many* it may contain, for **every one of potentially dozens of
units returned in the single largest call in the pipeline**. `unit_checks` (via `coherence_checks`)
does eventually catch a bad citation — but only after the call has already spent tokens writing it,
exactly the wasted-attempt shape item 105/E22 already fixed for S3's `investigation_schema`
("a hallucinated fact ID cost a live provider call before `binding_errors` ever caught it, spending
the job's one re-ask budget before anything narrower could help"). Every other fact-citing job in the
pipeline (S3 investigation, S4 reconciliation's `unit_id`/`fact_ids` *entries*, S5 planning, S6
authoring's per-task calls) now has this exact protection; S8 coherence is the one call site that
received item 75's *count* bound but never the *citation* bound its four siblings all carry. This was
not found in any `RESEARCH_LANE_*.md` file or `DECISION_LOG.md` entry searched (`coherence_schema`
occurs only in item 75's own entry, which does not mention `fact_ids`).

This sits directly in PDF-Python's own near-term path: its own S6 measured 75 units across 8 sections
on its one completed draw (`LANE-E-01` run 2) — every one of those units' `fact_ids` will pass through
this exact unbounded field the next time this repository reaches S8, which is one stage past where
`PDFPY-02`'s own fix (S6) now lets it proceed once redrawn.

## 5. Current status and honest recommendation

**The repository's own next step is unambiguous: redraw now.** Item 119/`PDFPY-02`'s fix (`0ced0a5`)
landed at 08:09:07 UTC today and no redraw has run against it — this is not a diagnosis gap, it is
simply the next action, verified not already in flight (§ intro). A redraw should confirm S6 clears
and report however far the pipeline gets past it.

**Do not expect an immediate seal even if S6 clears cleanly**, for the same reasons investigation 06
gave for Words-.NET: PDF-Python has, across its history, reached S10 exactly once (`pdfpy/LANE-E-08`)
and never reached S8 coherence or S11's no-op proof at this repository's own real scale with today's
code. §4 names two already-diagnosed, not-yet-landed defects sitting directly in that unexercised
path — F27 one stage before S6 (S4, confirmed still open, independently corroborated by two
repositories now), and the new S8 `coherence_schema` gap one stage after it. Both are narrow,
evidence-fitted fixes with a direct precedent already in the same files (`_pin_fact_id_arrays` for
F27, `authoring_schema`'s own `citable()`/`prefixItems` mechanism — or a schema-level `maxItems` at
minimum — for S8). Landing either or both before spending the next real redraw's provider-call budget
would test them in the same pass this repository's own redraw already has to make, rather than
discovering each separately on a future run exactly as items 78, 91, and 119 were each discovered one
redraw at a time.

**Answering the owner's question directly:** this is a systemic pattern, not a string of unrelated
coincidences, but the system it reflects is working as designed, not broken. Every one of PDF-Python's
four confirmed blockers is a shared-code gap general to the whole portfolio (§3) that this
repository's own scale or content shape happened to trigger first; one additional stretch of elapsed
time (five days on item 78) was a separate, already self-diagnosed admission-cadence gap, not a
technical one; and two further defects of the identical "unbounded array under constrained decoding"
shape sit in this repository's own immediate forward path, found by direct comparison against the
four sibling mechanisms (S3, S4-entries, S5, S6-per-task) that already received this exact treatment.
