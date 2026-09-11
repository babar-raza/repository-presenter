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
