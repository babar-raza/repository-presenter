# lane-e decision log (append-only; entries in DECISION_LOG.md section 31 shape; the owner merges)

Lane: `lane-e` (project/lanes/lane-e.yaml). Prompt: project/loop-prompt-lane.md.

The lane appends here in `DECISION_LOG.md` §31's shape — date, item, decision, alternative
rejected, evidence, reversal path. The owner reviews asynchronously and merges what belongs in §31.

Lane E differs from lanes B, C and D in one respect that shapes every entry below: it owns **no
platform module**. The Python extractor is shared and mature, so every defect this lane can find in
extraction, composition, review, repair, the renderer, `prompts/` or `core/` is a `PROPOSAL` for the
primary to land through G4-W17 — never an edit in this lane's paths. This lane's own output is
candidate bundles, dispositions, its evidence file and this log.

## 2026-09-11 08:25 UTC (`date` checked) — LANE-E-01, lane E's first run, sprint wave W-PY1

Lane opened at `b712790`. Branch `lane-e/LANE-E-01`, worktree `C:\w\e01`, rebased onto `origin/main`
at `83f8380` (the run itself was made at `692f57c`; `git diff --stat 692f57c 83f8380 -- src prompts`
is empty). Receipt: `evidence/build/lanes/lane-e/LANE-E-01.json`. Scope as the item's purpose
gives it, in order: Aspose.PDF, Aspose.Page and Aspose.Cells for Python.

### The run was stopped at S4 by the supervisor, and no disposition is written

A `Reviewer:` message reached this run mid-flight: stop before spending another provider call on a
candidate, because the pipeline is blocked at S4 `source_reconciliation` for **every** repository
and no Python run can reach a seal until the fix lands; record what is already measured, and write
no disposition against a known-broken stage, since a disposition recorded now would name a false
failure class for a repository whose real class is several stages further on. Applied in this run:
`LANE-E-01` stays `IN_PROGRESS`, all three repositories keep exactly the classes the G3 second pass
recorded, and nothing below is offered as a verdict on any of them.

### E1 — what lane E measured before the stop: PDF for Python is healthy through S3, at a new revision

`aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`, one `present` run, `origin/main` at `692f57c`.

- **The source revision moved.** The G3 second pass ran `109e26a10e37541528afb5e3ae6b04516c1c0359`
  on 2026-09-07; today's read-only clone pins `bc52745063841d454053d4e7780c0e4ed1f05ed5` (*fix
  (streaming): give a lazily opened document its text and its deletions*). The recorded resume
  predicate will therefore be judged against a different tree than the one that produced it. The
  clone is depth-1, so the distance between the two revisions was not measured here.
- **Examples: 13 candidates, 8 `EXECUTED`, 5 `FAILED`** — the identical split the second pass
  measured at the older revision. The first pass's class
  `QUICK_START_WITHOUT_EXECUTED_EXAMPLE` stays closed at this revision too, and `required rows
  without evidence` is not reopened by the move.
- **Facts: 1,583 records** (`public_symbol` 1,376, `inherited_unit` 115, `link_target` 35,
  `dependency` 20, `example` 13, `format` 9, `identity` 5, `package` 4, `build_test_asset` 2,
  `license` 2, `import_path` 1, `install_command` 1); 1,527 at confidence 1.0 and 56 at 0.5. The
  second pass measured 1,555 at the older revision.
- **S3 `repository_investigation` accepted on attempt 1** — HTTP 200, 50,945 ms, 34,276 prompt and
  2,273 completion tokens, model `qwen3-next`, no rejection.
- **S4 was never recorded.** S3's call closed at `08:16:11Z`; the process was gone by `08:22:49Z`
  (the mtime of its own redirected log), 6 min 38 s into the first `source_reconciliation` call,
  with exit status 127 and its block-buffered stdout lost. **No S4 call record was ever written, so
  lane E has no measurement of the S4 failure itself** — only that the call had not returned inside
  a window where lanes C and D measured theirs at 550.7 s / 567.5 s (Java) and 552.9 s / 571.8 s
  (Go). Nothing here is offered as independent corroboration of that cause; the measurement is
  theirs (`852047a`, `3bc7999`).

### E2 `PROPOSAL` — item 40's `pattern` was already prohibited, and the recorded reason for the prohibition is now wrong

A zero-provider-call reading, recorded while the primary is still choosing between two proposed
fixes for the same defect.

**The standing rule.** `RESEARCH_AND_GUIDELINES.md` §27.0 D1, from §27.10's measured follow-up of
2026-09-04: *"The gateway answers HTTP 400 for `pattern` in strict `json_schema`: **never use
`pattern`; use enums, `minItems`/`maxItems`, `maxLength`**."* §27.9's G2-W20 purpose line carries
the same reason for the same gateway: URLs and commands became referential *"because the gateway
answers HTTP 400 for a pattern in strict json_schema"*.

**What item 40 did.** `components/readme/reconciliation/dispositions.py::reconciliation_schema`
(`e2a1a83`, 2026-09-11 06:50 +05:00) sets `fact_ids.items` to
`{"type": "string", "pattern": "^(<kind>|…):"}` — a `pattern` inside a strict `json_schema`, which
that rule forbids outright. No lane finding to date cites the rule.

**Why nobody caught it.** The rule's recorded *symptom* no longer holds. The gateway does not answer
400; lanes C and D both measured replies returned under that schema with the pattern enforced as a
decoding grammar. That is strictly worse than the 400 the rule anticipated: a 400 fails in under a
second and is unmissable, a grammar spends about nine minutes and 32,000 completion tokens per
repository and surfaces as *output truncated at the manifest's max_output_tokens*, which reads like
a prompt-size or batch-size problem — and both lanes spent a run measuring batch size out before
reaching the schema. So the prohibition stands and the sentence justifying it is stale, in both
places it appears.

**Consequence for the fix being landed now.** The two lanes proposed different repairs, and only one
conforms to the rule:

| proposal | shape | conforms to D1 | an ID that names no fact |
| --- | --- | --- | --- |
| lane C (`852047a`) | append `.+` to the pattern, add `maxItems: 72` | no — still a `pattern` | still decodable; caught after the call by `binding_errors` (measured 8 → 1) |
| lane D (`3bc7999`) | pin `fact_ids.items` to an `enum` of the packet's own fact IDs | yes — "use enums" | impossible to emit |

Lane E's reading, on D1 and on the function's own precedent — `unit_id` in that very function is
pinned with an `enum`, for exactly the argument its docstring already spells out — is that the
**enum** is the fix and `maxItems` beside it is defence in depth, as lane D says. If the pattern
form is kept anyway, D1 and the G2-W20 purpose line should be restated in the same commit to say
why a `pattern` is now allowed; otherwise the next schema author reads a prohibition the code
contradicts and the class returns.

**Alternative rejected.** Saying nothing and letting the primary pick. Both lanes validated their
own fix live and neither cited the standing rule, and the two fixes differ in precisely the property
that rule governs; one paragraph before the fix lands is worth more than a correction after.

**Evidence.** §27.0 D1's last sentence (`RESEARCH_AND_GUIDELINES.md`); §27.10 follow-up 2026-09-04;
§27.9 G2-W20 purpose; `e2a1a83`'s `reconciliation_schema` docstring and body; lane C's and lane D's
measurements in `852047a` and `3bc7999`.

**Reversal path.** Lane E owns no code and proposes no edit of its own: this is a reading of a
standing rule against a landed commit. It is refuted by one measurement showing this gateway decodes
a bounded `pattern` safely — in which case D1's sentence, not item 40, is what needs the edit.

### E3 `PROPOSAL` — the enum fix is right, and its size has only been validated at 123 values; PDF for Python would carry 689

Also zero provider calls: measured on this run's own `facts.json` through the same functions
`run_round` calls, nothing written, no tracked file touched.

**Why it matters.** This project already has one *confirmed* HTTP 400 from exactly this shape at a
sibling site. `DECISION_LOG.md`, 2026-09-10 11:19 UTC, Taskcard H: `planning_schema()`'s three
unbounded enum sites were closing the gateway with a 400 on
`aspose-pdf-foss/Aspose.PDF-FOSS-for-Java`, and the fix was to route them through
`bounded_records()`. An enum is the right *kind* of constraint for `fact_ids` and it must be
bounded the same way — which, happily, it already is: `reconciliation_packet()` builds its `facts`
list through `bounded_records(..., symbol_kinds=DECLARED_SYMBOL_KINDS)`, so the enum's size is
whatever that bound yields for the repository in hand. The open question is not *whether* to bound
it but *how large the bounded list actually gets*, and that is repository-dependent and has been
measured at one point only.

**Measured, per repository, at the S4 packet:**

| repository | citable fact records in the S4 packet | measured by |
| --- | --- | --- |
| `Aspose.Cells-FOSS-for-Go` | 123 — the one value lane D's enum replay was validated against | lane D, `3bc7999` |
| `Aspose-PDF-FOSS-for-Python` | **689** (601 `public_symbol`, 34 `link_target`, 20 `dependency`, 13 `example`, 7 `format`, 4 `identity`, 4 `package`, 2 `build_test_asset`, 2 `license`, 1 `import_path`, 1 `install_command`); 31,653 characters of IDs; the packet is 115,067 characters before any inherited unit is added | **this run**, on `bc527450` |
| `Aspose.PDF-FOSS-for-Java` | 1,240 `public_symbol` records alone under item 40, against 3 before it | lane C, `852047a` |

So the enum lane D validated is 5.6× smaller than the one PDF for Python would carry — and PDF for
Python is not the portfolio's largest surface either. `Aspose.PDF-FOSS-for-Java` is, at 24,830
`public_symbol` facts (`DECISION_LOG.md`, 2026-09-10), and that is the repository the one confirmed
400 was raised on.

**Proposal.** Land the enum, and treat the class as closed only after one live S4 call on a
large-surface repository, not on the 123-value case alone. PDF for Python at 689 values is the
cheapest such check and lane E is already positioned to make it on its next run — the first
repository of `LANE-E-01` is exactly that repository. If the large enum does trip a 400, the answer
is the same one Taskcard H reached: tighten `bounded_records`' own cap for this packet, never widen
the schema back to a `pattern`.

**Alternative rejected.** Assuming 123 generalises. That assumption is what §27.10 follow-up 3
prohibits in so many words — a threshold or a shape is never fitted to one sample — and the
project's own worked counter-example, Taskcard H, landed yesterday.

**Evidence.** This run's own transaction `facts.json` for `bc527450` (under this lane's gitignored
`runs/transactions/`), read through `reconciliation_packet()`; `DECISION_LOG.md` 2026-09-10 11:19
UTC (Taskcard H); lane C `852047a`; lane D `3bc7999`.

**Reversal path.** Nothing to reverse — lane E proposes no edit. The measurement is reproducible
from the transaction in this lane's own `runs/` (gitignored) or from any fresh facts run of the
same revision.

### Which of lane E's first three repositories are S4-class

Asked directly by the reviewer; answered from `evidence/build/G3_PYTHON_COHORT/manifest.json`,
`second_pass.report`, with no run of any kind.

| repository | second-pass outcome | stage | recorded failure class | S4-class |
| --- | --- | --- | --- | --- |
| `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python` | `NOT_SEALED` | S4 `source_reconciliation` | `RECONCILIATION_EMITS_A_SCHEMA_KEY_AS_A_FACT_ID` | **yes** — item 40's own target |
| `aspose-page-foss/Aspose.Page-FOSS-for-Python` | `NOT_SEALED` | S4 `source_reconciliation` | `RECONCILIATION_CITES_A_FACT_ID_THAT_DOES_NOT_EXIST` | **yes** — item 40's own target |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` | `NOT_RERUN_IN_THIS_BOX` | S10 review, BC-10 | `CORROBORATED_PRESENTATION_JUDGMENT` (first pass, unchanged) | no — later stage |

Both S4 rows are named by item 40 itself, not only by this lane's cursor: the commit body
(`e2a1a83`) cites *"Aspose.PDF for Python rejected twice on its own packet's investigation keys"*
for the `fact_ids` half, and `reconciliation_packet()`'s own docstring cites *"Aspose.Page for
Python, whose root is `aspose.page`: about seven namespace strings of its 570 public symbols
reached this packet, and the job — rejected twice — cited `public_symbol:aspose.page.common`"* for
the `symbol_kinds` half.

Two of the three are exactly the repositories arrival item 40 was landed for, and neither can be
judged on its own class until S4 decodes again. The third's class is six stages later, but that does
not make it runnable: every composition traverses S4, so Cells for Python cannot reach BC-10 either.
All three wait on the same landing, and their unlocks — item 40 for PDF and Page, the
28/33/37/39/45 + F6 fold stack for Cells — remain untested by this lane.

### What this run does not claim

- No candidate was rendered and no bundle sealed. No check BC-01 to BC-11 was judged for any of the
  three repositories. `repository-presenter status` reads **8/34** before and after this run, and
  `project/state.yaml` was not opened.
- Page for Python and Cells for Python were never launched; not one provider call was spent on
  either, and their recorded classes are the G3 second pass's, not this run's.
- Lane E did not measure the S4 truncation. The 6 min 38 s without a returned call is consistent
  with what lanes C and D measured and is not evidence of it.

### One housekeeping line for whoever owns `docs/REPOSITORY_LAYOUT.md`

Its `docs/` row names the pattern `RESEARCH_<LANE>.md` and then enumerates *"(RESEARCH_LANE_B.md,
_C, _D)"*. That list is now short by this file, and lane F's when it writes one. The pattern itself
already covers both paths, and `evidence/build/lanes/<lane>/` is already generic, so nothing was
created outside what the layout names — but the parenthetical is stale. Not edited here:
`REPOSITORY_LAYOUT.md` is not a lane-owned path.

## 2026-09-11 09:49 UTC (`date` checked) — LANE-E-01 resumed, run 2, sprint wave W-PY1

Branch `lane-e/LANE-E-01-R2` (single-use; `lane-e/LANE-E-01` merged), worktree `C:\w\e02`, off
`origin/main` at `2b9d191`. Receipt: `evidence/build/lanes/lane-e/LANE-E-01.json`. The resume
predicate recorded by run 1 was satisfied: the S4 `fact_ids` fix landed as `352fd35`.

### E3 is refuted by measurement: the unbounded enum did **not** trip a 400 at 689 values

Run 1 proposed E3 — the landed enum is unbounded and had been validated at 123 values only, while
Taskcard H (`DECISION_LOG.md` 2026-09-10) is a confirmed HTTP 400 from an unbounded enum at the
sibling `planning_schema` site on a large-surface repository. This run is the live test E3 asked
for, and **E3 does not materialise.**

- The enum carried **689 values / 34,409 characters** of JSON array, measured offline from this
  run's own `facts.json` before the call, through `_packet_fact_records()` — the same function
  `reconciliation_schema()` uses. Identical to run 1's count at the same revision `bc527450`.
- **All three S4 `source_reconciliation` calls returned HTTP 200 on attempt 1**: 92,219 ms /
  54,929 prompt / 4,726 completion; 54,924 ms / 57,746 / 2,975; 58,583 ms / 54,240 / 3,113. No
  `finish_reason: length`, no rejection, no retry. Against the pre-fix runaway of 32,000 completion
  tokens per call, completion fell by roughly 85-90%.
- **The output is correct, not merely well-formed**: 115 dispositions for 115 `inherited_unit`
  facts, citing **118 distinct fact IDs, of which zero are bare kind prefixes** — the exact defect
  `352fd35` was landed against.

So the size bound E3 asked for is **not** needed at 689, and lane E withdraws the recommendation to
gate the class on it. What remains true from E3 is narrower and worth keeping: the largest surface
in the portfolio is not 689 — lane C measured PDF for Java at 1,240 `public_symbol` records alone —
so 689 is now the highest *confirmed-good* value, not a proof for every repository. A 400 at some
larger size would still be answered Taskcard H's way (tighten `bounded_records`' own cap for this
packet), never by widening the schema back to a `pattern`.

**Reversal path.** One HTTP 400 naming the schema or request size at a larger enum reopens E3 with
that repository's measured value; this entry records only that 689 is proven safe.

### E4 `PROPOSAL` — BC-07's canonical-abbreviation judge drops the section, so its own repair can never run

**Decision.** Lane E writes no code. `src/repository_presenter/components/readme/validation/registry.py`
lines 874-883 are shared code and the defect is the primary's to land. PDF for Python takes a
disposition naming this proposal as its resume predicate, not a forced seal.

**The defect.** The judge builds its failure without the one field that routes it:

```python
for word in sorted(set(_LOWER_WORD.findall(prose))):
    if word in lower_forms:
        failures.append(
            Failure(
                "COMPOSING", f"abbreviation {word!r} is not in its canonical form {word.upper()}"
            )
        )
```

`Failure.section` is documented in the same file (`registry.py:200-211`) as *"the shell section the
failure is about, set by the judge that knows it… a field rather than a prefix parsed back out of
`detail` because routing a defect to its causal stage must not depend on prose"*. This judge never
sets it. `COMPOSING` maps to `S6`, which `repair/targeted.py:192-200` treats as repairable **only**
when some failure names an LLM-owned section; with `section_id: None` it rewrites the stage to
`None` and records `"no failing check names an LLM-owned section"`. The check is therefore
structurally unrepairable — not because the content resists revision, but because the judge withheld
the routing field. That is a permanent unrepairable finding blocking a candidate, which
`project/loop-prompt.md` §6 rule 5 prohibits outright.

**That the section is knowable is proven by this run's own README.** The offending word is `pdf`,
inside the bare repository slug `aspose-pdf-foss-for-python` (`_LOWER_WORD`'s lookbehind `(?<![.\w])`
stops at the hyphen, so a hyphenated slug spells an abbreviation in lowercase). `_section_texts()` —
already called four times in the same function, ten lines above — places it exactly:

- `installation`: `` `aspose-pdf-foss-for-python` is not yet published on PyPI… `` — backticked,
  stripped by `_SPAN`, does not fire.
- `additional_examples`: `The following workflows demonstrate converting, rendering, extracting,
  merging, and protecting PDF documents using aspose-pdf-foss-for-python.` — bare, fires.

One section is LLM-owned and one occurrence is the whole failure. The same run repaired **BC-08** on
attempt 1 (`development_testing`, two changes, `outcome: repaired`) precisely because its judge did
set `section`. Same round, same repairer, same candidate: the only difference is the missing field.

**The content defect underneath is real too, and is not the blocker.** An identifier written as bare
prose rather than a code span is a genuine S6 presentation defect, and BC-07 is right to refuse it.
Nothing here asks for the check to be weakened or for the abbreviation rule to be relaxed. The
proposal is one field: give the failure the section `_section_texts()` already knows, so the repair
the pipeline is designed to attempt actually gets attempted.

**Alternative rejected.** Widening `_LOWER_WORD`'s lookbehind to `(?<![-.\w])` so a hyphenated slug
never fires. It suppresses the symptom, leaves the same routing hole for every other abbreviation,
and would have silently admitted a README that spells an identifier as prose. §27.10's rule against
fitting a shape to one sample applies: one repository's slug is not the class.

**Evidence.** `runs/transactions/aspose-pdf-foss__Aspose-PDF-FOSS-for-Python/bc527450…/validation.json`
(BC-07 `FAIL`, `causal_stage: COMPOSING`, `failures[0].section_id: null`); `repairs.json`
(`e2f68cfcd311…`: BC-07, `outcome: unrepairable`, `reason: "no failing check names an LLM-owned
section"`, `changes: []`; `1c50ad993488…`: BC-08, `outcome: repaired`, `section_id:
development_testing`); `registry.py:200-211, 874-883`; `repair/targeted.py:192-200`.

**Reversal path.** If the owner rules that BC-07's structure failures are deliberately unroutable —
that structure is the renderer's and never the author's — then the abbreviation sub-check is in the
wrong check, and the reversal is to move it to an S6-judged check rather than to add the field.
Either way the candidate stops being permanently blocked.

### What this run measured end to end

`aspose-pdf-foss/Aspose-PDF-FOSS-for-Python` at `bc52745063841d454053d4e7780c0e4ed1f05ed5`, the same
revision run 1 pinned, so run 1's facts findings carry over unchanged (1,583 records; examples 13
candidates, 8 executed, 5 failed). The pipeline ran to completion for the first time in this lane:

| stage | outcome |
| --- | --- |
| S3 `repository_investigation` | reused run 1's stored output, 0 provider calls |
| S4 `source_reconciliation` | **passed**, 3 calls, 115 dispositions |
| S5 `presentation_planning` | 16/18 sections, 2 calls (1 `response_invalid`, accepted on attempt 2) |
| S6 `section_authoring` | 75 units across 8 sections |
| coherence | 0 of 75 units revised |
| render | 206 visible lines of 751 |
| S9 validation | **pass 8, fail 1 (BC-07), pending 2** |
| repair | BC-08 repaired; BC-07 unrepairable; 2 rounds |
| seal | **not sealed** |

The first-pass and second-pass classes for this repository are both closed at this revision:
`QUICK_START_WITHOUT_EXECUTED_EXAMPLE` (8 examples execute) and
`RECONCILIATION_EMITS_A_SCHEMA_KEY_AS_A_FACT_ID` (zero bare prefixes cited). The repository now
fails at a **new, later, and genuinely different** class, recorded as its disposition.

### What this run does not claim

- PDF for Python is **not sealed**; `repository-presenter status` reads **8/34** before and after,
  and `project/state.yaml` was not opened (§0's narrow exception applies only to a seal).
- The BC-07 content defect was not judged for severity beyond the check's own verdict; no
  independent review (S10/BC-10) ran, because the candidate never reached it.
- Nothing is claimed about whether attaching the section would in fact repair this candidate — only
  that the repair is currently never attempted. That is the proposal's whole subject.

### The lane venv had to be rebuilt before any of the above counted

A `Reviewer:` message reached this run before the first candidate call: verify the worktree venv's
`presenter_site_manifest` hash against the primary's. It did not match. Lane F had already recorded
the cause and the fix (`docs/RESEARCH_LANE_F.md` F3); this run reproduced both, independently.

`project/loop-prompt-lane.md` §1.3's literal `pip install -e .[dev]` resolved **five** distributions
past `requirements-lock.txt` — `anyio 4.15.1` (lock 4.14.2), `ast-serialize 0.11.1` (0.8.0),
`openai 3.13.0` (3.7.0), `ruff 0.16.7` (0.16.5), `types-PyYAML …20260906` (…20260815) — and produced
`613b742b997a5a87…` against the primary's and all eight sealed bundles'
`f4406f1b04d81ecdf2ea4e421776ef2be7f8cdc27090f395a815277a561fd411`. Rebuilt as F3 prescribes
(`pip install --no-deps -r requirements-lock.txt`, then `--no-deps -e .`, then `--no-deps
uv==0.12.9`) the hash is **`f4406f1b…`, identical**, and the two distribution sets are now equal at
50 entries with no diff. Every measurement above was taken after the rebuild.

This is a second independent reproduction of F3 on a second lane, which makes it a property of the
lane prompt rather than of one worktree: **§1.3's install line is wrong for any lane that intends to
seal.** Lane E cannot fix it — `project/loop-prompt-lane.md` is not a lane-owned path — so it is
recorded here for the owner alongside lane F's entry.

### Aspose.Cells for Python **sealed** — and its no-op proof then failed, for a cause in shared code

`aspose-cells-foss/Aspose.Cells-FOSS-for-Python` at `26c3bd1633e84b91c0f6fad1fd353662fd61fb54`.
The first-pass class `CORROBORATED_PRESENTATION_JUDGMENT` (S10/BC-10) — the one that had never been
re-run in the G3 second-pass box — **is closed**. The 28/33/37/39/45 fold stack plus F6 acceptance
corroboration did what the item hoped.

| stage | outcome |
| --- | --- |
| examples | 6 candidates, **6 executed, 0 failed** |
| facts | 1,092 records (`public_symbol` 987, `inherited_unit` 47, `link_target` 29) |
| S4 `source_reconciliation` | 47 units, 2 calls |
| S9 validation | **pass 10, fail 0**, pending 1 |
| S10 `independent_review` | **verdict ACCEPT**, findings 0, advisory 22 |
| repair | 0 repaired, 0 unrepairable; 1 round |
| bundle | `candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Python/26c3bd16…`, state `ACCEPTED`, 13 files, 18 provider calls |

`second_reader.read` is **2** (`corroborated: 3c3b7985b1f0977c7f120bba, 5a7b3d4f0db5c30bca2069e8`),
so PHASE1/F6's `>= 2` holds, and the bundle's `dependencies.json` carries
`presenter_site_manifest: f4406f1b04d81ecdf2ea…` — the same environment class as the primary and the
other eight bundles (see the venv entry below; this is why that rebuild had to come first).

**The immediate rerun in a fresh process was not a no-op, and the candidate it produced was
rejected.** Same revision, `evaluation: earliest affected stage NONE; 0 changes` — nothing about the
repository moved — yet:

| | first run | rerun |
| --- | --- | --- |
| S4 dispositions | `OMIT_UNSUPPORTED 2, SUPERSEDE_REDUNDANT 16, VERIFIED_PRESERVE 24, …` | `SUPERSEDE_REDUNDANT 25, VERIFIED_MOVE 14, VERIFIED_REWRITE 3, …` |
| README digest | `d196088242173118…` | `671e525aee56dcfc…` |
| visible lines | 192 of 651 | 192 of 646 |
| S9 validation | pass 10, fail 0 | pass 9, **fail 1** (BC-10) |
| S10 review | **ACCEPT** | **REJECT_PRESENTATION**, findings 1 |

So Cells for Python composed and was accepted, but it is **not no-op-proven**. While the bundle was
on disk `repository-presenter status` read `9 ever sealed, 9 integrity-valid` with `current-code
reproducible` still **6** and the headline still **8/34**.

**And then the full local CI-equivalent refused the bundle outright, so it is not landed at all.**
`tests/test_sealed_bytes.py::test_a_sealed_candidate_renders_to_its_own_bytes` — an existing
blocking check, not one this lane invented — fails for it. That is E7 below, and it is the reason
this PR carries no `candidates/` directory. The bundle was removed from the tree and
`repository-presenter status` is back to **8/34, 8 ever sealed**. Lane E therefore claims **no
seal**: an accepted composition that CI refuses is a disposition, not a seal, and forcing it in
would have landed a red `main`.

### E5 `PROPOSAL` — `seed_call_store` cannot seed a batched job, so no multi-batch repository can ever prove its no-op

**Decision.** Shared code (`src/repository_presenter/components/readme/bundle/seal.py:452-509`),
so lane E writes no fix. Cells for Python's disposition names this proposal as its resume predicate
for the no-op proof; the seal itself stands.

**The defect.** `seed_call_store` seeds a job only when its sealed `calls.jsonl` holds exactly one
successful attempt:

```python
for job, filename in _SEEDABLE_JOBS.items():
    attempts = successes.get(job, [])
    artifact = bundle / filename
    if len(attempts) != 1 or not artifact.is_file():
        continue
```

`_SEEDABLE_JOBS` maps `source_reconciliation` to `dispositions.json`. But S4 is **batched by
design** — `reconciliation_batches()` splits the inherited units and `run_round` makes one call per
batch, all in the same round, and `merge_dispositions()` merges them into the single
`dispositions.json` the bundle seals. N batches therefore produce N successful attempts as the
*normal* shape, not as evidence of anything wrong.

The docstring's stated reason for the `!= 1` rule is a different case entirely: *"a repository whose
composition reopened this stage through a repair round left two or more successful attempts under
the same job name, each against a different packet, and only the last one's output matches what the
sealed artifact holds"*. That reasoning is sound for a **re-ask**, where only the last attempt is
genuine. It is simply false for a **batch**, where every attempt is genuine and the artifact is
their merge. The rule cannot tell the two apart, so it treats the normal case as the pathological
one.

**Measured consequence, this run.** Cells' sealed ledger holds
`{repository_investigation: 1, source_reconciliation: 2, presentation_planning: 1,
section_authoring: 11, independent_review: 2}` successful attempts. The rerun printed
`seeded from sealed bundle: presentation_planning, repository_investigation` — S4 absent — and then
`dispositions: … provider calls 1`. A live call to a non-deterministic model returned different
dispositions; that changed the planning packet, so even the *seeded* `presentation_planning` key
missed (`plan: … provider calls 1`); and the divergence carried through authoring to a
`REJECT_PRESENTATION`. One unseeded call at S4 is sufficient to lose the whole no-op property.

**This is not specific to Cells.** Any repository whose reconciliation needs more than one batch is
affected. This run measured PDF for Python at **3** S4 calls and Cells at **2**; only a
single-batch repository can seed S4 today. That is consistent with `status` reporting `6
current-code reproducible` against `9 ever sealed` — the gap is not attributed here, but the
mechanism is now measured and would produce exactly that shape.

**Alternative rejected.** Relaxing the rule to "seed from the last successful attempt". It restores
the exact lie the docstring guards against for genuine re-asks, and it is still wrong for batches,
where no single attempt's output equals the merged artifact. The honest fix keys each batch's own
`logical_call_id` to that batch's own output — which means the bundle must carry per-batch
reconciliation outputs, not only their merge. That is a bundle-format change and squarely the
primary's to design.

**Evidence.** `seal.py:452-509`; Cells' sealed `calls.jsonl` (counts above); the two run logs'
`seeded from sealed bundle` and `provider calls` lines; `reconciliation_batches` /
`merge_dispositions` in `reconciliation/dispositions.py`; `status` before `8 ever sealed / 6
reproducible` and after `9 ever sealed / 6 reproducible`.

**Reversal path.** If the owner rules that S4 is not meant to be seedable at all, the reversal is to
remove `source_reconciliation` from `_SEEDABLE_JOBS` and restate loop-prompt §3's "byte-identical
with zero provider calls" to the number of batch calls a no-op legitimately costs — the property
being proven then changes, and should change explicitly rather than by silent failure.

**A second, different no-op mechanism was reported the same day, and E5 does not subsume it.**
`40f2e9d`'s portfolio-wide proposal reads: *"no candidate sealed since `352fd35` can pass a no-op
proof — `run_job` re-judges a stored S4 reply against the decoder's enum while `normalize` writes
IDs the packet never showed."* That is a distinct failure from E5's: E5 says a batched S4 is never
*seeded*, so a live call is made; lane B's says that even a **stored** reply is re-judged and
refused. Both were measured, on different repositories, and they compound — a job that cleared E5
by having exactly one batch would still meet lane B's. Lane E does not claim lane B's mechanism and
has not measured it; whoever fixes the no-op proof should read the two entries together, because
fixing either alone will not restore it.

### E7 `PROPOSAL` — the seal sorts facts by ID, the renderer does not sort at all, so a sealed README can be unrenderable from its own sealed facts

**Decision.** Shared code (`src/repository_presenter/core/facts.py:136` and
`src/repository_presenter/components/readme/composition/renderer.py:263`), so lane E writes no fix.
This is the blocker that stopped Cells for Python being landed, and it outranks E5: E5 costs the
no-op proof, E7 costs the commit.

**The defect, in two lines that disagree.** The seal writes facts in ID order:

```python
"facts": [asdict(fact) for fact in sorted(self.facts, key=lambda f: f.id)],
```

The renderer emits the dependency bullets in whatever order the document hands it, with no sort:

```python
lines.extend(f"- `{fact.value}`" for fact in required)
```

The live pipeline renders from the in-memory `FactsDocument`, which is in **extraction** order.
The replay renders from `facts.json`, which is in **ID** order. Wherever those two orders differ
for any two facts in the same rendered list, the sealed bytes cannot be reproduced from the sealed
facts — by construction, on the first try, with nothing else wrong.

**Measured.** `tests/test_sealed_bytes.py::test_a_sealed_candidate_renders_to_its_own_bytes
[aspose-cells-foss__Aspose.Cells-FOSS-for-Python]` failed in the full local CI-equivalent. The
complete diff between the sealed README and the replayed render is two lines, transposed:

```
@@ -93,6 +93,6 @@
 ### Required Package Dependencies

+- `olefile>=0.46`
 - `pycryptodome>=3.15.0`
-- `olefile>=0.46`
```

The sealed `facts.json` holds `dependency:olefile-0.46` before `dependency:pycryptodome-3.15.0`
(ID order); the sealed README lists `pycryptodome` first (the order `pyproject.toml` declares them).
Nothing else in 36,933 bytes differs.

**It is not hash randomisation, and that was tested rather than assumed.** Re-rendering under
`PYTHONHASHSEED` 0, 1, 2, 3 and 42 gives `olefile` then `pycryptodome` every time. The renderer is
deterministic; it is *order-preserving*, and the order it was given at seal time is not the order
the seal preserved. Nor did the later rejected rerun corrupt the bundle: every one of its 14 files
carries the same 15:36:42-43 seal timestamp.

**Scope.** Data-dependent, which is why eight bundles pass this test and the ninth does not: it
bites only when extraction order and ID order disagree within one rendered list. Any repository
whose manifest declares dependencies in non-alphabetical order is a candidate for it, and the
dependency bullets are only the list this run happened to hit — the same asymmetry applies to every
unsorted `lines.extend(... for fact in ...)` in the renderer.

**Alternative rejected.** Sorting the dependency bullets in the renderer. It fixes this list and
leaves the general asymmetry, and it silently changes the presentation order of every existing
candidate — a manifest's own declaration order is arguably the better reading order anyway. The
narrower fix is to make the seal preserve the document order the render actually consumed, so that
replay and render see the same sequence; whichever direction the owner picks, the two sites must be
made to agree deliberately rather than by coincidence.

**Evidence.** `core/facts.py:136`; `composition/renderer.py:248-263`; the CI run's `pytest` step
(`1 failed, 1012 passed, 13 xfailed in 427.92s`) and its named parametrisation; the unified diff
above; the five-seed determinism check; the bundle's uniform file timestamps.

**Reversal path.** If the owner rules that `test_sealed_bytes` is too strict — that a sealed bundle
need only be semantically, not byte-, reproducible — then the check is what changes, and this entry
becomes an argument for that ruling rather than for a code fix. It should not simply be left as is:
today it silently converts an accepted candidate into an unlandable one.

**Independent corroboration, and the precedent for the fix (`40f2e9d`, landed while this run was
composing).** Lane B hit the identical class on the same day, from the other side of the codebase:
*"test_sealed_bytes caught this lane's own defect: declared_dependencies sorted by the manifest's
spelling while fact IDs are slugged, so the sealed README listed Python3 before googletest and a
re-render listed them the other way"* — the same test, the same section, the same two-line
transposition, and the same "manifest order versus ID order" cause. Lane B could fix it directly
because the offending order was produced by **its own C++ plugin**, which it owns, and it did so
with a mutation test.

That is the precedent, and it sharpens this proposal rather than duplicating it. The Python
cohort's instance has the same shape — the extractor emits `dependency:pycryptodome-3.15.0` before
`dependency:olefile-0.46` because `pyproject.toml` declares them that way, while the IDs sort the
other way — but the Python extractor is **shared and mature**, so lane E may not edit it (this
lane's opening paragraph). Hence a proposal rather than a commit. The owner therefore has a
measured choice the two lanes have now framed together: fix each producer's order one ecosystem at
a time, as `40f2e9d` did for C++, or make the two shared sites (`core/facts.py:136` and
`renderer.py:263`) agree once so no future plugin can reintroduce it. Lane E has no standing to
pick between them and records the evidence for both.

### Aspose.Page for Python: a clone timeout that was contention, not size

The first attempt never reached a provider call: `clone of … failed after 3 attempts: transient
clone failure: git clone --depth 1 --no-tags … timed out after 600.0s`. Root cause investigated
before any retry, per loop-prompt §5's prohibition on a third equivalent attempt.

The repository is genuinely huge — `gh api` reports **418,348 KB (≈409 MB)** against PDF for
Python's 5,523 KB and Cells for Python's 1,389 KB, i.e. 75× and 300× — so "too big for the budget"
was the obvious hypothesis. **It is wrong.** The identical command, run alone and timed, completed
in **316 s** (`RC=0`, 1.1 GB on disk, 2,430 files), comfortably inside
`CLONE_TIMEOUT_SECONDS = 600.0` (`core/git_safety/clone.py:30`). The three failures happened while
five other lane workers and this lane's own PDF run were competing for the same link, in the window
that ended with the account-wide session-limit reset.

So the tool's classification was right: this was a transient failure, correctly retried. Lane E
records **no proposal to raise the timeout** — the evidence does not support one, and §27.10's rule
against fitting a threshold to one sample cuts against changing a constant on the strength of a
contended window. What is worth the owner's attention is cheaper and different: three attempts at
600 s each spend **30 minutes** before reporting, and a timeout is the one "transient" marker whose
retry cost is the full budget every time. That is an observation, not a proposal; lane E has one
measurement and will not build a rule from it (`MEMORY`: never a rule from one observation).

### E6 `PROPOSAL` — the S4 `fact_ids` fix was not applied to its four sibling sites at S5, and that is Page for Python's live blocker

**Decision.** Shared code (`prompts/presentation_planning.yaml` and
`src/repository_presenter/components/readme/composition/planning.py::planning_schema`), so lane E
writes no fix. Page for Python takes a disposition naming this proposal as its resume predicate.

**The defect.** `352fd35` fixed `reconciliation_schema`'s `fact_ids` by pinning it to an enum of the
packet's own IDs. The **identical field name, in the identical role, at the sibling S5 site, was not
fixed** — at four places. Every `fact_ids` in the planning manifest's schema is a bare string array,
and `planning_schema()` rewrites none of them:

| field | schema as shipped |
| --- | --- |
| `core_capabilities.items.fact_ids` | `{"type": "array", "minItems": 1, "items": {"type": "string"}}` |
| `api_hubs.items.fact_ids` | `{"type": "array", "minItems": 1, "items": {"type": "string"}}` |
| `material_limitations.items.fact_ids` | `{"type": "array", "items": {"type": "string"}}` |
| `deviations.items.fact_ids` | `{"type": "array", "minItems": 1, "items": {"type": "string"}}` |

The contrast is inside one object: `planning_schema()` *does* replace `api_hubs.items.symbol_fact_id`
with `{"type": "string", "enum": hubbable}` (`planning.py:212-214`), and leaves `fact_ids` — its
immediate sibling in the same `items.properties` — accepting any string at all.

**Measured, this run.** Page for Python was rejected twice at S5 and the run ended:
`presentation_planning: output rejected twice; last rejection: unknown fact ID
public_symbol:aspose.page.xps.renderer`. The invented ID sits at exactly
`api_hubs[2].fact_ids[5]` in the rejected payload
(`calls/910e76cb940e.rejected-2.json`). `aspose.page.xps.renderer` is a plausible namespace the
model composed, not a fact it was shown — the same invention the G3 second pass recorded for this
repository as `RECONCILIATION_CITES_A_FACT_ID_THAT_DOES_NOT_EXIST` with
`public_symbol:aspose.page.common`.

**So Page's recorded class did not survive item 40 — it moved.** The class was never an S4-only
class; it was a `fact_ids`-shaped hole that existed at both stages. Item 40 and `352fd35` closed the
S4 half, and this run proves the S4 half is closed for this very repository (3 `source_reconciliation`
calls, all HTTP 200 on attempt 1, no rejection). The S5 half is untouched and now blocks alone.
The lane file's expectation that "item 40 other half (symbol_kinds bounding) cites it by name" is
therefore not sufficient for Page: `symbol_fact_id` bounding is already in place and is not what
failed.

**The fix has a working model to copy.** `citable_fact_ids()` already computes the exact set a
disposition may cite, from `bounded_records()`, and `planning_schema()` already uses
`bounded_records()` for its other enums under Taskcard H's cap. The same list applied to these four
fields makes the invention impossible to emit rather than detected afterwards by `binding_errors`.

**On the size objection.** This run answers it with three live measurements rather than a guess: an
enum of the packet's own citable IDs held at **689 values / 34,409 characters** (PDF), **360 /
17,119** (Page) and **252 / 12,590** (Cells), across **8 S4 calls in total, every one HTTP 200 on
attempt 1**. Taskcard H's confirmed 400 was at ~24,830 symbols with no `bounded_records` cap at all;
these are the capped sizes, and they are two orders of magnitude smaller.

**Alternative rejected.** Leaving the four fields free and relying on the existing `binding_errors`
rejection plus a prompt sentence. That is exactly what is in place now, and it is what the G3 second
pass already tried to fix by prompt wording; it costs two full S5 calls and a dead run per
repository, and `RESEARCH_AND_GUIDELINES.md` §27.5 D1's whole point is that the schema should make
the mistake unrepresentable rather than ask the model to notice it.

**Evidence.** `prompts/presentation_planning.yaml` (`output.schema.properties.*.fact_ids`, four
sites, quoted above); `planning.py:189-220`; Page's run log
(`presentation_planning: output rejected twice`); `calls/910e76cb940e.rejected-1.json` and
`.rejected-2.json`; `calls.jsonl` (`presentation_planning: 2 success, 2 response_invalid`;
`source_reconciliation: 3 success`).

**Reversal path.** If a bounded enum at these four sites trips an HTTP 400 on a larger-surface
repository, the answer is Taskcard H's — tighten `bounded_records`' cap for this packet — never a
return to a free string array.

### Aspose.Page for Python, measured

Second attempt, after the clone cause was settled. Clone succeeded; the repository is at
`ca4fb3d76f9a3bdac34fc0f96801efd1cd31eb9e` (**2,430 tree entries**, matching the timed probe).

- **Examples: 8 candidates, 6 executed, 2 failed.**
- **Facts: 735 records** (`public_symbol` 570, `inherited_unit` 104, `link_target` 31, `example` 8,
  `identity` 5, `format` 5, `dependency` 4, `package` 3, `license` 2, and one each of
  `build_test_asset`, `import_path`, `install_command`). The G3 second pass measured 728 records
  with the same 570 `public_symbol`.
- **S3** accepted on attempt 1. **S4 passed: 3 calls, all HTTP 200 on attempt 1** — the recorded
  blocker for this repository is closed at S4.
- **S5 rejected twice**, run ended. No candidate rendered, no bundle sealed.

### Dispositions written this run

Each is a real rejection with its failure class and resume predicate — none is a forced seal.

| repository | outcome | class | resume predicate |
| --- | --- | --- | --- |
| `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python` | NOT_SEALED | `ABBREVIATION_FAILURE_IS_UNROUTABLE_SO_REPAIR_NEVER_RUNS` (BC-07, S9/COMPOSING) | E4 lands: BC-07's canonical-abbreviation judge sets `Failure.section`; re-run `present --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Python` |
| `aspose-page-foss/Aspose.Page-FOSS-for-Python` | NOT_SEALED | `PLANNING_CITES_A_FACT_ID_THAT_DOES_NOT_EXIST` (S5, `api_hubs[].fact_ids`) | E6 lands: the four `fact_ids` sites in the planning schema take an enum of the packet's own citable IDs; re-run `present --repo aspose-page-foss/Aspose.Page-FOSS-for-Python` |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` | NOT_LANDED (composed and accepted) | `SEALED_BYTES_DO_NOT_RENDER_FROM_THE_SEALED_FACTS` (E7, blocking) and `SEALED_BUNDLE_CANNOT_REPLAY_A_BATCHED_S4` (E5, the no-op) | E7 lands first — the seal and the renderer agree on fact order, so `test_sealed_bytes` passes — then E5 for the no-op proof. The composition itself needs nothing: validation 10/0, review ACCEPT, `second_reader.read` 2. |

`LANE-E-01` stays `IN_PROGRESS`. **No seal is claimed and the counted unit does not move: 8/34
before and after.** All three repositories are accounted for with a real failure class and a resume
predicate, every one of which is a shared-code proposal for the primary; none can advance from
inside this lane.

The honest summary of Cells is worth stating plainly, because it is the run's most easily
overstated result: the pipeline produced an accepted candidate for it — 6 of 6 examples executed,
validation `pass 10, fail 0`, review `ACCEPT` with zero findings and two corroborating reads — and
the repository's own recorded blocker is genuinely closed. It is still not a candidate this project
can count, because the bundle it sealed cannot be re-rendered from the facts it sealed, and the
suite says so. That gap is E7's, not the candidate's.

## 2026-09-11 12:30 UTC (`date` checked) — LANE-E-01, run 3, sprint wave W-PY1

Branch `lane-e/LANE-E-01-R3`, worktree `C:\w\e03`, off `origin/main` at `22c2e45`. Receipt:
`evidence/build/lanes/lane-e/LANE-E-01.json`. Scope, as the supervisor set it: re-attempt
`aspose-cells-foss/Aspose.Cells-FOSS-for-Python` alone and test whether arrival item 61 closed E7 —
verify it, do not assume it, and do not force a seal if the cause turns out to be something else.
The environment was confirmed before any candidate work and matched on the first attempt this time
(`presenter_site_manifest f4406f1b04d8…`), because `54417f9` landed the exact recipe two lanes had
to reconstruct; no rebuild was needed.

**Result in one line: E7 is closed, the no-op property is restored, and Cells for Python still does
not seal — for a third, different, shared-code cause, which is E8 below.**

### E7 is CLOSED by arrival item 61, verified two independent ways

Item 61 (`22c2e45`) makes `FactsDocument.canonical()` the one fact order both sides use:
`to_json` writes it and `render_readme` now reads `facts.canonical()`. That is exactly the two lines
E7 named, so E7 needed no Python-specific change and lane E proposes none.

**Verification 1, offline, zero provider calls, whole portfolio.** Every one of the nine sealed
bundles on disk was rendered twice from its own committed artifacts — once from `facts.json` in the
order it is stored, once from the same facts shuffled under a fixed seed — and `render_readme`
returned identical bytes for all nine. Before item 61 that was false by construction; E7's whole
mechanism was that the two orders could differ. Seven of the nine also still equal their own sealed
README; the two that do not are `tests/test_sealed_bytes.py`'s two declared `strict` xfails
(Email-Python F07, Cells-C++ item 44's pending re-seal), neither of which is about fact order.

**Verification 2, live.** The run below composed a complete candidate through S9 with `BC-01`
through `BC-09` all `PASS`, and nothing in it reordered. This is weaker evidence than verification 1
and is not offered as the proof: because no bundle sealed, `tests/test_sealed_bytes.py` was never
exercised against a *new* Cells-Python bundle. The class-level proof is verification 1, and it is
stronger than one repository's seal would have been — it holds the renderer to nine documents across
six ecosystems rather than one.

**What this means for the lane's own record.** E7 is closed and needs no further work. It was the
blocker that made lane E claim no seal in run 2, and it is gone.

### E5 is NOT what broke Cells' no-op, and this run refutes that attribution with zero provider calls

Run 2 recorded that Cells for Python's immediate rerun diverged at S4 and attributed it to E5 —
`seed_call_store` cannot seed a batched job. **That attribution was wrong, and this entry corrects
it as its own record rather than as a clause inside E5** (§31: a correction to a standing fact gets
its own entry, or every reader of the corrected record misses it).

This run's immediate rerun, same process-fresh invocation, same revision, was a **true no-op**:

| | run 1 (live) | immediate rerun |
| --- | --- | --- |
| README digest | `8411d049d6e3dfef…` | `8411d049d6e3dfef…` (identical) |
| facts / dispositions / plan / units / validation / review digests | — | all identical |
| provider calls | 17 `success` | **0 `success`, 16 `cache_reuse`** |
| `source_reconciliation` | 2 live calls (batched) | **2 `cache_reuse`, 0 live** |

Both of S4's batched calls were served from the local `CallStore` with no live call. So a batched S4
replays byte-identically today. The real cause of run 2's divergence was arrival item 60 — `run_job`
re-judged a *stored* reply under `call_schema`, forced `cache_stale`, and made a fresh S4 call —
landed in the same commit `22c2e45`. Lane B measured that mechanism on other repositories and run 2's
own entry already noted the two "compound"; what run 2 got wrong was which of them was actually
firing on Cells.

**E5's own claim is untouched and still unproven either way.** E5 is about seeding from a *sealed
bundle*'s committed artifacts on a machine with no prior run; there is no sealed Cells bundle on
disk, so nothing here exercised `seed_call_store` at all. E5 should be read as a fresh-clone /
hosted-runner claim only, and it is no longer Cells for Python's resume predicate.

### E8 `PROPOSAL` — item 39's guard is scoped to one criterion, so the identical false finding still blocks under the other

**Decision.** Shared code
(`src/repository_presenter/components/readme/review/independent/review.py:730`), so lane E writes no
fix. This is now Cells for Python's only blocker: `BC-01`…`BC-09` all `PASS`, `BC-10` `FAIL`,
`BC-11` `PENDING`.

**The defect.** Finding `F07`, `criterion: presentation`, `section_id: scope_limitations`,
`fact_ids: []`, `absent: []`, text *"The Scope and Limitations section omits the crucial
clarification about Standard encryption not being supported for reading, which is explicitly stated
in the original README"*, quote *"Password-protected workbooks are supported only with Agile
encryption (ECMA-376 Part 2, Section 4); Standard encryption (Section 3) is not supported for
reading."*

That sentence is present, verbatim, at line 542 of the candidate README — inside
`## Scope and Limitations` (lines 537–544), the exact section the finding names — and
`review.json`'s `readme_sha256` equals the digest of those very bytes
(`8411d049d6e3dfef05cfe304ebdf14d653903ab33be6da04c1619d720cb5f84f`). The original README states it
at lines 374–375. **The candidate does not omit it. The finding is false on its own terms**, and
`second_reader.read: 2` corroborated it, so this is the prompt's shape, not one seed's slip.

`scope_defect` already holds the principle that settles this, in its own docstring: *"An absence the
candidate disproves is judged first, whatever the criterion … no reading of its criterion changes
that."* Arrival item 39 made exactly this shape a reviewer defect — *"its own quote WAS the sentence
it called missing, empty `fact_ids`, empty `absent`, byte-identical on re-ask, repair recorded it
repaired and it re-raised identically"*, measured on Aspose.Cells for **Java**. Cells for **Python**
has produced the identical shape, one criterion over, and item 39's guard does not reach it, because
line 730 reads `if finding.get("criterion") == "factuality"`.

**Measured, by running the module against the real finding** (`scope_defect`, the real README, the
real facts, the real `claim_evidence`):

| the same finding, one field changed | `scope_defect` verdict |
| --- | --- |
| as the reviewer returned it (`presentation`, `absent: []`) | `None` — **it blocks** |
| identical, claim stated in `absent[]` | *"the finding claims the candidate does not contain '…', which the candidate contains"* |
| identical, relabelled `criterion: factuality` | *"a factuality finding names neither a product fact_id to contradict the quote nor an absent claim of missing text"* |

So a candidate that passes nine of ten blocking checks is held back solely by which of two labels the
reviewer chose and whether it filled one field — not by anything about the candidate. That is
precisely the label dependence item 37 set out to remove.

**And the repair round cannot rescue it.** `repairs.json` records `outcome: "repaired"` for an
attempt whose single change has `before` byte-equal to `after` — nothing changed, because there was
nothing to change — and `rounds.py:522` records `"repaired"` unconditionally on any schema-valid
revision. The identical finding then re-raised, and `run_transaction`'s re-raise rule
(`rounds.py:595-606`, correctly: a re-raised defect never demotes) broke the loop. Two rounds, one
wasted `targeted_repair` call, `REJECT_PRESENTATION`.

**The fix is the primary's to choose, and lane E does not choose it.** The narrow one matching item
39's precedent is to judge this shape before the criterion switch rather than inside it. The bare
rule "a presentation finding whose quote is present may not stand" is **not** safe and lane E
explicitly does not propose it — a legitimate presentation finding quotes present text it wants
rewritten, and dismissing those would weaken a real check. The discriminator that separates the two
is that this finding alleges a *gap* while stating none: `absent` empty, `fact_ids` empty, and its
own quote already in the section it names, which one `targeted_repair` attempt then left byte-
identical. Whether that is expressed in `scope_defect` (label-independent, item 37's principle),
in `rounds.py` (a revision identical to its input did not repair anything), or in
`prompts/independent_review.yaml` (an omission claim must populate `absent` — item 39's own message
notes lines 141-157 already ask for this and that item 39 chose to enforce it in code rather than
trust compliance) is a design call that belongs with whoever owns all three.

**Evidence.** `review.py:730` and `scope_defect`'s docstring; `rounds.py:522`, `595-606`;
`review.json` (`verdict REJECT_PRESENTATION`, findings 1, advisory 6, `readme_sha256` as above,
`second_reader.read 2`); `repairs.json` attempt `96818ce46bf1833cdaa6279c` (`before == after`,
`re_raised: ["F07"]`); `validation.json` (`pass 9, fail 1, pending 1`); candidate README line 542;
original README lines 374-375; the three-row table above, produced by calling `scope_defect`
directly. Commit `3784b06` is item 39's landing.

**Reversal path.** If the owner rules that a presentation finding is a prose judgment call that no
deterministic check may dismiss (§26), then Cells for Python's disposition class is permanent for
this composition and the repository needs a different composition, not a reviewer change — and item
39 should be re-read in that light too, since it made the same call for factuality.

### Aspose.Cells for Python, measured

`26c3bd1633e84b91c0f6fad1fd353662fd61fb54`, the same revision run 2 composed.

| stage | outcome |
| --- | --- |
| examples | 6 candidates, **6 executed, 0 failed** |
| facts | 1,092 records (`public_symbol` 987, `inherited_unit` 47, `link_target` 29); digest `062f5f09…` |
| S3 `repository_investigation` | 1 call, capabilities 8, workflows 6, limitations 3 |
| S4 `source_reconciliation` | **passed, 2 calls**, 47 units (`SUPERSEDE_REDUNDANT` 26, `VERIFIED_PRESERVE` 11, `VERIFIED_REWRITE` 5, `NON_CONTENT` 4, `DEFER_UNRESOLVED` 1) |
| S5 `presentation_planning` | accepted attempt 1; sections 16/18, hubs 10 |
| S6 `section_authoring` | 40 units across 8 sections, 10 calls; coherence 0 of 40 revised |
| render | 192 visible lines of 551; digest `8411d049…` |
| S9 validation | **pass 9, fail 1 (BC-10), pending 1 (BC-11)** — `BC-01`…`BC-09` all `PASS` |
| S10 `independent_review` | `REJECT_PRESENTATION`, findings 1 (`F07`), advisory 6, `second_reader.read` 2 |
| repair | 1 recorded "repaired" with `before == after`, re-raised; rounds 2 |
| bundle | **none sealed** |

The composition is not the one run 2 produced — S4 is non-deterministic and returned different
dispositions (551 rendered lines against run 2's 651) — so run 2's `ACCEPT` and this run's
`REJECT_PRESENTATION` are two draws, not a regression. Lane E did not re-draw. Re-running until a
composition happens to escape a false finding is selecting for a seal, which is forcing one; the
finding is demonstrably false and belongs in code, not in a better roll.

### Disposition written this run

| repository | outcome | class | resume predicate |
| --- | --- | --- | --- |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` | NOT_SEALED | `FALSE_OMISSION_FINDING_BLOCKS_UNDER_THE_UNGUARDED_CRITERION` (E8, S10/BC-10) | E8 lands on `main`: the "alleges a gap, states none, quotes text the named section contains" shape is a reviewer defect whatever the criterion; then re-run `present --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Python`. E7 and the no-op are no longer predicates — both are closed. |

`LANE-E-01` stays `IN_PROGRESS`. **No seal is claimed and the counted unit does not move:
`repository-presenter status` reads 8/34 before and after, and this PR adds no `candidates/`
directory.** `project/state.yaml` was not opened: this PR seals nothing, so §0's narrow exception
does not apply.

The three repositories of this item now stand at: PDF for Python on E4, Page for Python on E6, Cells
for Python on E8. E7 and E3 are closed, E5 is re-scoped to the fresh-clone case and blocks nobody in
this lane. Every remaining predicate is still shared code the primary owns.

## 2026-09-11 17:13 UTC (`date` checked) — LANE-E-02, sprint wave W-PY2

Branch `lane-e/LANE-E-02`, worktree `C:\w\e04`, off `origin/main` at `c0da8e1` (arrival items
41+42). Receipt: `evidence/build/lanes/lane-e/LANE-E-02.json`. Scope as the item's purpose gives
it: `aspose-html-foss/Aspose.HTML-FOSS-for-Python`, then
`aspose-note-foss/Aspose.Note-FOSS-for-Python`, then
`aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` if the box allowed. Venv matched
`f4406f1b…` on the first attempt.

### E9 — HTML for Python: item 41 closed its recorded class, and the run stopped two stages later

**The gate this item waited on is closed, and the closure is measured, not assumed.** The G3
second pass recorded `PLAN_PICKS_A_CONTRADICTED_EXAMPLE_FOR_THE_QUICK_START` at S5: with six
executed examples to choose from, `presentation_planning` twice chose `example:006`, the one that
failed. This run's plan chose `example:001`, and `facts.json` records `example:001` as
`SUPPORTED` and `example:006` as `CONTRADICTED` — the only `CONTRADICTED` example in the set.
`presentation_planning` made **one** call and it succeeded on **attempt 1**, against two
rejections in the second pass. Item 41 did what it was admitted to do.

**It then stopped at S6 `section_authoring`, rejected twice, on a class no arrival item covers.**
The fatal rejections, from `calls.jsonl`:

- attempt 1: `unit limitation:3: identifiers that are not accepted fact values:
  HTMLImageElement.decode` and `unit limitation:4: … CSSRule.css_text, CSSRule.type, css_text`
- attempt 2: `unit limitation:4: … css_text`

The unit attempt 2 was rejected for reads, verbatim from the stored call body:

> "CSSOM base-rule stubs such as type and css_text are not implemented; concrete rule subclasses
> expose their own real properties instead." — `fact_ids: ["inherited_unit:089.list"]`

**Every one of those identifiers is spelled verbatim inside the SUPPORTED fact the unit itself
cites.** `inherited_unit:089.list` is the repository's own README limitations list, and its second
bullet reads "`CSSRule.type` and `CSSRule.css_text` (the CSSOM base-rule stubs) are not
implemented"; its third names "`HTMLImageElement.decode()`". Measured by calling the real
functions on the real facts:

- `identifier_tokens(inherited_unit:089.list.value)` returns 11 tokens and **all four rejected
  identifiers are among them** (`CSSRule.css_text`, `CSSRule.type`, `HTMLImageElement.decode`,
  `css_text`).
- `command_block_tokens` on the same value returns **0** tokens.
- `allowed_identifiers(facts, …)` holds 1,785 tokens; `CSSRule`, `HTMLImageElement`, `BoxNode`,
  `JSContext`, `ModuleRegistry`, `FragmentRoot`, `CSSStyleRule` and `CSSMediaRule` are all in it —
  only the **member** spellings are refused.
- No fact can ever supply them: the Python extractor records 338 `public_symbol` facts for this
  repository with `symbol_kind` class 302, function 16, module 14, **method 4**, enum 1, unknown 1.
  There is no `css_text` and no `decode` symbol at any spelling.

So this is the **inline-code-span half of arrival item 44**. Item 44 fixed the sibling half — a
token inside a fact's *shell-command fence* — and `command_block_tokens`' own docstring records
that the scoping to fences was deliberate: "Tokens of a fact's running prose, of a code span, and
of a source-language fence stay out: an upstream README that merely mentions a symbol the surface
no longer carries must not thereby license prose to spell it in a code span." That reasoning is
sound for a *capability* claim and lane E does not propose reversing it.

**What it does not cover is a limitation.** The `scope_limitations` section exists to state what
is *not* implemented, its only honest source is the repository's own limitations list, and naming
the member is the whole content of the claim. Every spelling was refused: attempt 2 even dropped
the `CSSRule.` head and wrote bare `type` and `css_text`, and `css_text` still tripped the guard
as a snake token. No content revision can satisfy it — dropping the claim loses a true statement
the original README carries, which is the same detail-loss BC-10 rejects candidates for. Two
attempts, both refused, and the run ended.

`PROPOSAL E9`, for the primary: `composition/authoring.py::allowed_identifiers` (lines 890-900) —
an identifier spelled verbatim inside a SUPPORTED fact is refused unless that fact is an `example`
or the spelling sits in a command fence, so a limitation unit cannot name the member it is about.
Lane E proposes **no specific fix** and explicitly does not propose "admit every token of every
SUPPORTED fact", which is the risk item 44 named. Two discriminators the measurement supports, the
choice between them (and the module that expresses it) the primary's: (a) scope by citation — a
token spelled verbatim inside a SUPPORTED fact **this unit cites** is spellable, which is stricter
than item 44's fence rule since the fence rule needs no citation at all; or (b) scope by section —
`scope_limitations` units may spell a member of an allowed symbol when the exact spelling appears
in a cited SUPPORTED fact, since a negative claim cannot mis-advertise a surface. Whichever lands,
`allowed_identifiers` feeds `unit_checks`, `renderer.prose` and BC-04 from one set, so fixing the
guard alone would only move the rejection to BC-04 — its own docstring says so.

E9 is the third measurement in one family, which is the argument for taking it as a card rather
than a one-repository curiosity: item 44 (a token inside an inherited command fence is refused at
authoring) and arrival item 68, admitted hours ago in `0fecf88` (`repair/targeted.py::repair_packet`
strips `inherited_unit` entirely, so repair has nothing citable), are the same underlying
mis-handling of `inherited_unit` — the fact kind that carries the repository's own README text —
at two other sites. E9 is the authoring-time, inline-code-span site.

**Disposition for `aspose-html-foss/Aspose.HTML-FOSS-for-Python`:** NOT_SEALED, failure class
`LIMITATION_UNIT_CANNOT_NAME_THE_MEMBER_IT_LIMITS` at S6 `section_authoring`. Resume predicate:
PROPOSAL E9 lands, then re-run `present --repo aspose-html-foss/Aspose.HTML-FOSS-for-Python`. The
first-pass and second-pass classes are both closed and the closures are measured.

### E10 — the `<` guard costs this repository four extra rounds, and recovers every time

Not a blocker and not a proposal — recorded because the repository is the worst case for the guard
and the measurement is cheap. Four of the six `section_authoring` rejections this run were `text
contains HTML ('<')`, one on `capability:6`, one on a hub unit and two batches covering 32 `type:`
units for `HTMLDivElement`, `HTMLFormElement` and their siblings. For an HTML DOM library the
natural description of `HTMLDivElement` spells `<div>`. **Every one recovered on the next
attempt** — the job re-wrote the token inside backticks, which `dd7dc73` (arrival item 46) admits —
so the fold-not-reject behaviour is working as designed and no change is proposed. `section_authoring`
made 26 calls in all: 20 successes and 6 rejections, 4 of them this guard.

### E12 — Note for Python: item 42 half-worked, and the real cause is one uninstalled extra

**This item's second gate did NOT close, and the assumption that it would is refuted.** Item 42
was admitted for this repository by name. The rejection this run is, to the word, the rejection
the G3 second pass recorded:

> `presentation_planning: output rejected twice; last rejection: core_capabilities 6 is titled
> 'Export to PDF', which names .pdf; no fact verifies that format, so the title claims what the
> repository does not prove`

**One half of item 42 did work and should not be reverted.** The second pass recorded Note
"wrote a public_symbol into output_format_ids"; this run's two rejected plans both carry
`"output_format_ids": []`, correctly empty. The new enum plus `maxItems 0` holds. Measured on the
real facts before the run, `_verified_formats` returns `{"input": [{"id": "format:input.one",
"value": ".one"}], "output": []}` — so the planner was told, explicitly and correctly, that no
output format is verified. **It named PDF anyway, twice, at temperature 0.** Item 42 treated this
as a packet-information defect; it is not one.

**The planner is not hallucinating — it is right, and the format fact is the weak link.** The
capability it insisted on cites `public_symbol:aspose.note.saveformat` among others, and the fact
set carries five SUPPORTED public symbols that evidence PDF export: `aspose.note.SaveFormat`
(enum), `aspose.note.model.PdfSaveOptions` (class), `aspose.note.saving.pdf_writer` (module),
`aspose.note.saving.pdf_writer.write_pdf` (function) and `aspose.note.Document.Save` (method).
`plan_checks` (planning.py:525) builds its verdict from `facts.by_kind("format")` alone, so the
message "no fact verifies that format" is true only of format-kind facts.

**Why `format:output.pdf` is UNRESOLVED, traced to the end.** The fact carries exactly four
evidence lines and every one is a failure: `README.md` line 119 (example 2) and line 235 (example
10), each paired with `examples.json | example N: FAILED; RuntimeError`. `formats.py` marks a
format SUPPORTED by one of two routes and both are shut:

- **The executed route.** Examples 2 and 10 are the only two that write a `.pdf`, and both failed
  for one identical reason: `File "…/aspose/note/saving/pdf_writer.py", line 1745, in write_pdf /
  from reportlab.lib.utils import ImageReader / ModuleNotFoundError: No module named 'reportlab'`.
  **`reportlab>=3.6` is a declared dependency of this repository** — `pyproject.toml` line 29-30,
  `[project.optional-dependencies] pdf = ["reportlab>=3.6"]`. All 12 examples record
  `build_verified: true`, so the real wheel installed and the source fallback never ran; the wheel
  was installed without extras, and `_declared_dependencies` (python_examples.py:322-333) reads
  `project.dependencies` only — `project.optional-dependencies` is read by neither path. Note's
  base `dependencies` list is literally `[]`, so the PDF writer could not import on any route.
- **The static-corroboration route.** Ran the extractor directly against the pinned clone:
  `format_declarations(root, 46 py files)` returns **0**. `python_format_declarations.py` is shaped
  for one architecture — `_declarations` skips every file whose name is not literally
  `FileFormat.py` (line 128), and `_registrations` needs a `register_plugin(...)` call (line 162).
  Note has neither: `find -name FileFormat.py` is empty and `grep -rn register_plugin` is empty.
  Yet both of §22.1's independent static sources are plainly in its source — the declaration at
  `src/aspose/note/enums.py:6-7` (`class SaveFormat(Enum): Pdf = "pdf"`) and a 1,828-line,
  emphatically non-stub exporter at `src/aspose/note/saving/pdf_writer.py`.

`PROPOSAL E12`, for the primary, in the order lane E would take them. **(1) The cheap one, and
lane E's recommendation:** the example runner installs the extras the manifest declares, or — the
narrower and better-precedented form — an example that FAILS with `ModuleNotFoundError: No module
named 'X'` is retried once with the declared extra that provides `X`, the same fold-not-reject
retry `verify_python_examples` already runs for `NEEDS_INPUT` and the same shape the G3 second
pass's own Font predicate proposes ("the example's own failure … fed back as a second staging
attempt"). Installing *every* extra is not proposed: this manifest's other extras are `test-pdf`
and `dev`, neither of which any example needs. If examples 2 and 10 execute, `format:output.pdf`
becomes SUPPORTED by the executed route, the title check passes on its own terms and nothing is
weakened. **(2) The deeper one:** `python_format_declarations.py` can only see the Aspose.3D
plugin architecture, so for every Python repository not built that way a format is reachable only
through an executed example. Lane E proposes no specific widening and does **not** propose
relaxing §22.1's two-independent-source rule — Note satisfies that rule on its own source; the
extractor cannot see it.

Lane E proposes **no** change to `plan_checks`. The check is correct and catching a real gap.

One content nuance the run never got to test, recorded for whoever re-runs it: PDF export here is
behind an optional extra, so the honest capability title may need to say so, and the extra is
itself a fact the candidate should carry.

**Disposition for `aspose-note-foss/Aspose.Note-FOSS-for-Python`:** NOT_SEALED, failure class
`VERIFIED_FORMAT_UNREACHABLE_BECAUSE_ITS_EXAMPLES_LACK_A_DECLARED_EXTRA` at S5
`presentation_planning` — a re-diagnosis of, and a replacement for, the second pass's
`PLANNED_CAPABILITY_TITLE_NAMES_AN_UNVERIFIED_FORMAT`, which named the symptom. Resume predicate:
PROPOSAL E12 (1) lands, then re-run `present --repo aspose-note-foss/Aspose.Note-FOSS-for-Python`.
Item 42 is **not** this repository's resume predicate and never was; its at_a_glance half is kept.

### E11 — BarCode for Python was not run: its gate is still shut

The spawn instruction stated that BarCode's blocker, arrival item 43, "has ALSO landed separately
today (dd7dc73 pre-sprint)", and asked for the current disposition to be checked rather than
assumed. **Checked, and it has not landed.** `dd7dc73` is arrival item **46** ("a protected
command's own placeholder bracket is not HTML"), whose own unblock-ledger line reads `{"item": 46,
… "unlocks": [["lane-d", "Aspose-PDF-FOSS-for-Go"]]}` — a different item and a different lane.
Three independent readings agree:

- `evidence/build/G4_MULTI_LANGUAGE_COHORTS/unblocked.jsonl` has lines for items 36, 22, 32, 33,
  23, 55, 39, 40, 44, 45, 46, 60, 61, 62, 63, 64, 41 and 42. **There is no line for item 43.**
- The primary's own sprint ledger entry for the 41+42 commit says it in words: "Unblocks lane E's
  W-PY2 gate for HTML-Python and Note-Python (**BarCode waits on item 43**)… 43 is otherwise next
  in the 06:25Z slot order."
- The code is unchanged. BC-07's heading rule is `validation/registry.py:862-873`; `git log -L
  862,873` on that file returns `9661e49` (G2-W03, 2026-09-03) as its newest touch — eight days
  old, and older than every arrival item in this sprint's list.
  The one exemption there — `if level == 3 and line in api_lines and text in topics` — reads
  `topics` as `fact.value.rsplit(".", 1)[-1]`, so for the recorded failing heading `###
  renderers.Renderer` it holds `Renderer`, not `renderers.Renderer`, and does not fire.

Its disposition is therefore **unchanged from the G3 second pass**:
`API_REFERENCE_HEADING_JUDGED_AS_PROSE` at S9/BC-07, resume predicate arrival item 43. Note that
arrival item **58** (lane F PROPOSAL F8, admitted 2026-09-11) is the same defect measured a third
time and states the fix more precisely — "align BC-07's heading model to the renderer's own" — so
43 and 58 look like one card, not two. No provider call was spent on BarCode: running it would
have bought a re-measurement of a class already recorded twice and a third instance of a heading
the renderer itself generates.
