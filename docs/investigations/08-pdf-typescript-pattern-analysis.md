# Investigation 08: The PDF-TypeScript redraw pattern

Status: investigation only, no implementation, no redraw attempted by this session. Written
2026-09-17 (~10:10 UTC / 15:10 +0500). Commissioned directly by the owner after
`aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` was drawn or dispositioned repeatedly this sprint
and, each time a blocker cleared, the pipeline reached a new, deeper stage and hit a different one.
Question asked, same shape as investigation 06 (Words-.NET): is this a systemic problem with this
one repository, or the largest-surface repository in its cohort legitimately surfacing shared-code
gaps in order, one stage at a time? Two specific waypoints were handed to this session as
"known" and marked explicitly for verification, not assumption; §1 below reports what checking
them against the primary sources actually found, because one of the two does not hold as stated.

Primary evidence: `docs/DECISION_LOG.md` (full-text search for "PDF-TypeScript"/"PDF-TS"/"PDFTS"/
the repository slug), `docs/RESEARCH_LANE_B.md` (the `G4-W14-RERUN4` entries, 2026-09-16), `git log`
against every relevant commit SHA named below, and the current source tree (`core/facts.py`,
`investigation/dossier.py`, `composition/planning.py`, `reconciliation/dispositions.py`,
`composition/authoring.py`, `composition/coherence.py`, and the four job prompt manifests under
`prompts/`). `docs/RESEARCH_AND_GUIDELINES.md` §29 was checked directly and contains no
PDF-TypeScript-specific material at all - it is the 2026-09-04 ecosystem-plugin design essay; the
"Currency note" at its own §27.0 (line 1547) states plainly that arrival-item rulings from item 0
onward live in `DECISION_LOG.md`, not §29, which this investigation's own search confirmed. Before
writing anything: `git fetch origin main` showed `origin/main` unchanged at `e5efae1`; `git worktree
list` was read in full and one worktree, `C:/w/pdfts1` on branch `pdfts/investigate`, was found
holding real, relevant, already-complete but unpushed diagnostic work (commit `e3af3ef`, then 1
commit ahead of `origin/main`, 14 behind). That worktree's own `git status` was clean and idle -
no redraw was in flight to duplicate or interrupt - but its one unpushed commit was, at that point,
the freshest, most detailed evidence this repository had. **A second `git fetch origin main`, run
immediately before committing this report, found `origin/main` had moved** to `542bfe0`
(`docs(research): admit arrival item 120, PDF-TypeScript's uncapped S5 packet finding`,
`2026-09-17 14:37:58 +0500`) - someone else formally admitted the same finding, with the same
measured numbers (437 units, 694,205 chars, 298,865/262,144 tokens) pdfts1's own unpushed commit
already carried, into `RESEARCH_AND_GUIDELINES.md` §27.9's queue text while this investigation was
being written. This worktree was fast-forwarded onto that commit before finishing; §1's and §6's
treatment of "item 120" is written against that now-landed reality, not the earlier snapshot.

## 1. Checking the task's own two waypoints against the primary sources

**Waypoint "item 105" holds exactly as described.** `docs/DECISION_LOG.md`'s 2026-09-17 02:42 UTC
entry (commit `bec76ba`, `2026-09-17 07:49:01 +0500`) is **G4-W17 arrival item 105 (LANDED, E22)**:
`repair/rounds.py`'s S3 `repository_investigation` call was the one fact-citing job with no
`call_schema` pinning `fact_ids` to a citable enum, unlike S4/S5/S6; the fix, `investigation_schema()`
in `investigation/dossier.py`, was motivated by a **Words-Python** nondeterminism finding (two live
S3 calls against a byte-identical request produced two different hallucinated fact IDs), not by
anything about PDF-TypeScript. The PDFTS-REDRAW entry (§2 below) independently confirms this
general, unrelated fix closed PDF-TS's own specific S3 blocker as a side effect - the task's framing
of item 105 as "a possible side-effect fix from an unrelated item" is accurate and is confirmed,
not assumed, in §2.

**Waypoint "item 97" does not describe item 97.** The task named item 97 as "an investigation-stage
blocker on `investigation/dossier.py`'s `facts.investigation` `UNIT_CAP=80` - a 3.4x overflow."
Checked directly: the real, numbered **item 97** is `docs/DECISION_LOG.md`'s 2026-09-16 20:16 UTC
entry (ruling commit `b6f9cb6`, `2026-09-17 02:45:28 +0500`), titled *"the cross-block-fragment
README class ... is a third sighting of an already-understood upstream-content shape, not a new
defect"* - a **RULED, no-shared-code-fix** disposition of PDF-TypeScript's S3 rejection (its one
workflow claim cited only three CONTRADICTED examples). It has nothing to do with `UNIT_CAP`. The
`UNIT_CAP=80` overflow the task describes is real and did happen on this exact repository, but it is
a **separate, much earlier, unnumbered finding**: `docs/DECISION_LOG.md`'s 2026-09-06 21:36 entry
(commit `bc24208`, `2026-09-06 21:36:57 +0500`), which frames itself explicitly as *"a second,
confirmed instance of **item 27's** own shape"* (item 27 is `SYMBOL_CAP`, a different cap on a
different fact kind, found the same evening) - not as its own arrival item, and not as item 97,
which did not yet exist (item 97 was admitted ten days later). The source code's own comment
(`investigation/dossier.py` lines 22-28) confirms the same attribution: it cites "item 27" by name
for `UNIT_CAP`'s own precedent and cites "item 105" separately for `investigation_schema()`; it
never mentions item 97 at all. This correction matters for the timeline in §2: the UNIT_CAP fix was
never a live blocker this repository failed *on* - it was found by a proactive code audit and fixed
the same day, before the draw that hit the S4 timeout even finished, and item 97 is a wholly
different, later defect at the same pipeline stage (S3) but a different mechanism (citation
rejection, not truncation).

## 2. The timeline, run by run

| When | Commit / run | Stage reached | What happened |
|---|---|---|---|
| 2026-09-06 20:05 (`date` checked) | owner directive | — | Reviewer had wrongly counted PDF-TypeScript among permanently non-processable repositories; the actual cause was a stale `disabled` flag in `data/registry.json`, not a content defect - confirmed independently by `aspose.org`'s own `verify-examples --typescript-runner` regen run. Four standing rules promoted to `project/loop-prompt.md` §6 rule 16 the same day. |
| 2026-09-06 20:29-20:30 | **item 31** landed, `10f4b5d` | — | `data/registry.json`'s `mode` field flipped `disabled` → `dry_run`. `tests/core/registry/test_loader.py`'s enabled-count assertion 31 → 32. |
| 2026-09-06 21:11 (`date` checked) | first real draw attempt (primary loop) | **S4** `source_reconciliation` | Admitted, cloned (1,848 tree entries), extracted 2,922 facts cleanly; the entry itself does not say S3's own output, only that the transaction reached S4. Since S4 runs after S3, S3 evidently completed - under the then-current `UNIT_CAP=80` (25 minutes before the 21:36 fix), so at most 80 of the 272 inherited units this repository actually carried were visible to that S3 call, an inference from stage order and the constant's own unchanged value, not a figure the entry states directly. S4 then raised `RetryableOperationError: timeout` twice, identically, against the then-`DEFAULT_TIMEOUT_SECONDS=360s` ceiling. PROPOSAL opened, not landed in this entry. |
| 2026-09-06 21:36 | UNIT_CAP fix, `bc24208` | (proactive audit, not a live failure) | Reviewer's own code audit found `investigation/dossier.py`'s `UNIT_CAP=80` admits only 80 of PDF-TypeScript's 272 `heading`/`paragraph`/`list` inherited units - a 3.4x overflow, the same shape as item 27's `SYMBOL_CAP`. Raised to 400 same day, mutation-tested. See §1: **not item 97.** |
| 2026-09-06 22:39 | **item 35** landed, `b6b0232` (PR #16) | — | `DEFAULT_TIMEOUT_SECONDS` raised from a guess (360s) to a value fit from 783 real call latencies (900s) - the S4-timeout proposal's actual fix, landed ~90 minutes after the 21:11 attempt, never re-drawn against until ten days later. |
| 2026-09-06 → 2026-09-16 | *(10-day gap)* | — | No further draw of this repository by anyone, by direct grep of both research logs. |
| 2026-09-16 ~20:36-20:39 | `G4-W14-RERUN4`, `f6bb788`/PR #74 (lane B) | **S3** `repository_investigation` | Lane B's first-ever draw of this repository. Facts-only run first found and fixed three real `typescript_examples.py` verifier defects, each with its own mutation test: **F1** `--module`/`--moduleResolution` mismatch (TS5110) for `node16`/`nodenext`; **F2** the package's self-import-by-name needs a staged `node_modules/<name>` entry Node's `exports`-less resolution otherwise refuses; **F3** `rootDir: "."` was string-`lstrip`'d to `""` (a character-set strip, not a prefix strip) and the wrong `tsconfig.json` was read instead of the repository's own `tsconfig.build.json`. Combined effect: 96 examples went from `failed 96` (all `BLOCKED_TOOLCHAIN`) to `executed 9, failed 87` (every one a real diagnostic). The full `present` transaction then ran for the first time past facts extraction and failed closed at **S3**: `output rejected twice`, one workflow claim ("parse HTML/Markdown ... render to PDF") cited only three CONTRADICTED examples (`example:008`/`:009`/`:010`). Two of the three are the cross-block-fragment shape already seen twice before (3D-TS's `scene.save`, Slides-C++'s incomplete fence). Disposition: `BLOCKED_INVESTIGATION` (S3). This is item 97's raw material. |
| 2026-09-16 20:16 UTC (entry date) / `b6f9cb6`, `2026-09-17 02:45 +0500` (commit) | **item 97** RULED | S3 | No shared-code fix: `core/llm/binding.py`'s SUPPORTED-only citation rule is doing its job, and every alternative considered (letting a workflow cite CONTRADICTED evidence directly, or stitching README fragments into one synthetic example at extraction) reopens a real integrity guarantee for one repository's benefit. Disposition unchanged (`BLOCKED_INVESTIGATION`, S3); resume predicate narrowed to "other real evidence, or the upstream README's fragment structure changes." |
| 2026-09-17 02:42 UTC / `bec76ba`, `07:49 +0500` | **item 105** (E22) LANDED | S3 (general fix) | `investigation_schema()` added to `investigation/dossier.py`, wired into `repair/rounds.py`'s S3 `run_job` call: every `fact_ids` array S3 may write is now pinned to an enum of the packet's own citable IDs. Motivated by Words-Python's nondeterminism, not by PDF-TS; not yet re-drawn against this repository at landing time. |
| 2026-09-17 13:59-14:04 (worktree `C:/w/pdfts1`, branch `pdfts/investigate`, commit `e3af3ef`, **still not on `origin/main`**) | PDFTS-REDRAW | **S5** `presentation_planning` | Verified item 105's `investigation_schema()` is actually wired into `repair/rounds.py`'s S3 call before drawing. Redrew at unchanged revision `09e3d13` (3,133 facts, 437 inherited units, 2,544 public symbols, digest `d6b39088...`, identical to every prior facts-only read). **S3 passed on the first attempt**: `investigation.json` carries 6 workflows, none citing the three CONTRADICTED examples item 97 named - the model found other SUPPORTED evidence instead, exactly as an enum-with-no-`minItems` shape predicts. This directly confirms item 105 closed item 97's specific rejection as a side effect. **S4 also passed** (11 live calls, all HTTP 200). **S5 failed closed at the gateway transport layer**, not the binding layer: `APIStatusError` HTTP 400, `litellm.ContextWindowExceededError`: this model's maximum context length is 262,144 tokens; the request carried 298,865 input tokens. Reproduced directly (not assumed) by rebuilding the exact production packet/schema from the on-disk `facts.json`/`investigation.json`/`dispositions.json` and sending it to the live gateway. Disposition: `BLOCKED_INVESTIGATION` → `BLOCKED_PLANNING` - forward movement, not a repeat, not a seal. Recorded there only as a PROPOSAL. |
| 2026-09-17 14:37:58 +0500, `542bfe0` (`origin/main`, landed **during this investigation**) | **item 120** admitted | S5 (queue only) | `RESEARCH_AND_GUIDELINES.md` §27.9's G4-W17 queue text gains a formal entry for the identical finding, same numbers, same file. `src/` untouched by this commit - it is an admission (the finding now has a real arrival-item number and a place in the queue), not yet a fix. `docs/DECISION_LOG.md` is not touched either; `pdfts1`'s own fuller measurement entry (`e3af3ef`) remains the more detailed source and remains unpushed. |

Corrections found while building this table, in the template report's own tradition of stating them
plainly rather than silently absorbing them: the task's own framing listed item 97 as the `UNIT_CAP`
finding (§1 above - it is not); and, at the time this investigation began, the task's phrase
"arrival item 120" did not exist verbatim anywhere in the record - the PDFTS-REDRAW entry matching
every one of the task's cited numbers (437 units, 694,205 characters, 298,865 input tokens,
262,144-token limit, `ContextWindowExceededError`) carried no arrival-item number of its own and was
not part of `origin/main`'s history. **That changed while this document was being written:**
`origin/main` advanced to `542bfe0` mid-session, formally admitting this exact finding as **arrival
item 120** into `RESEARCH_AND_GUIDELINES.md` §27.9's G4-W17 queue text (see the header's evidence
note). Item 120 is now real and numbered - the task's own framing was accurate as a prediction of
where this was going, not as a description of the record at hand when it was written. What item 120
still is **not**, as of `542bfe0`: a code fix. That commit's own diff is one line inside a queue
purpose string in a docs file; `src/` is untouched, and `pdfts1`'s own detailed DECISION_LOG.md
entry (`e3af3ef`, with the S3/S4/S5 measurement trail §2 draws on) is **still** not part of
`origin/main` - only a summary of its finding is. §6 returns to this.

## 3. Corroborating the root cause directly against the current source tree

Read independently, not taken on the strength of the log entry alone (`core/facts.py`,
`investigation/dossier.py`, `composition/planning.py`, `reconciliation/dispositions.py`,
`composition/authoring.py`, `composition/coherence.py`, and every job's `prompts/*.yaml`, all at
`origin/main`'s current HEAD `e5efae1` - the same revision `pdfts1`'s own PROPOSAL was written
against, confirmed unchanged by the two `git fetch` checks in the header):

- **`core/facts.py::bounded_records`** (lines 234-279) bounds `public_symbol` (`SYMBOL_CAP=6000`,
  item 27), `link_target` (`LINK_CAP=100`) and `example` (`EXAMPLE_CAP=30`, both PHASE0/J2) by an
  explicit `elif fact.kind == "..."` branch each. **There is no branch for `inherited_unit` at all**
  - it falls through every `elif` and is admitted unconditionally, subject only to the caller's
    `kinds`/`polarities` filter. The function's own docstring claims a packet "stays bounded however
  large the repository's own surface, link count, or example count is" - `inherited_unit` is the one
  kind the claim does not cover, and the docstring does not name it as an exception.
- **`prompts/repository_investigation.yaml`** (S3) declares an explicit `fact_kinds:` list (lines
  31-41) that **excludes** `inherited_unit` entirely. `investigation/dossier.py::investigation_packet`
  handles inherited units through a wholly separate mechanism: its own `UNIT_CAP=400`-bounded loop
  (lines 33-48), never through `bounded_records`. S3 was built with a dedicated, capped path for this
  fact kind from very early on (item 27's own precedent, 2026-09-06).
- **`prompts/source_reconciliation.yaml`** (S4) declares its own explicit `fact_kinds:` list (lines
  38-51) that **includes** `inherited_unit` (line 39) - but `reconciliation/dispositions.py::_packet_fact_records` (lines
  176-182) strips it back out (`kinds = [k for k in manifest.packet.fact_kinds if k != "inherited_unit"]`)
  before calling `bounded_records`, and `reconciliation_packet` (lines 266-295) supplies inherited
  units through its own, separately batched mechanism: `reconciliation_batches` (lines 117-134,
  `_RECONCILIATION_BATCH=40`) splits every inherited unit into fixed 40-unit batches, one
  `source_reconciliation` call per batch, so no single S4 call ever sees more than 40 at once. S4's
  *input* side is safe by construction.
- **`prompts/presentation_planning.yaml`** (S5) declares **no `fact_kinds` key at all** - the only one
  of the four fact-citing job manifests with none. `composition/planning.py::planning_packet` (line
  253) reads `kinds = manifest.packet.fact_kinds or FACT_KINDS`, so with no override it falls back to
  `FACT_KINDS` - literally every fact kind the schema recognises, `inherited_unit` included - and
  passes the whole set into `bounded_records(facts, kinds)` (line 256) for the packet's `"facts"`
  field, unbatched, in one call. This is the exact mechanism the PDFTS-REDRAW entry names, confirmed
  directly against the current tree rather than only against the entry's own quote of it.
- **`composition/authoring.py`** (S6) never calls `bounded_records` with `manifest.packet.fact_kinds`
  at all (confirmed by a direct grep - zero matches). `authoring_tasks` (lines 683-770) builds each
  section's `accepted_facts` from `ids`, a set `section_selections` already narrowed to that
  section's own plan-assigned slots; `do_not_claim` (lines 694-698) is a `bounded_records` call with
  an explicit four-kind list that does not include `inherited_unit`. S6's own `api_reference` batching
  (`_type_batches`, `_TYPE_BATCH=40`) mirrors S4's batch size for the same reason. S6 is safe by a
  different route: it was never given the whole document to filter in the first place.
- **`composition/coherence.py::coherence_packet`** (S8, lines 31-84) caps its own `spellings` list at
  `_SPELLING_CAP=120` explicitly, and sources `accepted_facts` from the same plan-scoped `tasks` S6
  already narrowed (batch tasks excluded). Also safe.

**S5 `presentation_planning` is the only stage in the whole composition pipeline that both (a) asks
`bounded_records` for every fact kind by falling back to `FACT_KINDS`, and (b) has no batching or
per-kind cap of its own layered on top, for the one kind `bounded_records` itself does not bound.**

## 4. Is there a real, structural reason S5 never got S3's treatment, or was it simply never exercised?

Both, and they are the same fact seen from two directions, not two separate explanations competing
for credit. Structurally: when `inherited_unit` bounding was first needed (item 27's evening, S3's
own `UNIT_CAP`), the fix was built as a **bespoke, S3-local mechanism** - a second field
(`"inherited_units"`) with its own cap, sitting beside `bounded_records`'s output rather than inside
it - not as a change to `bounded_records` itself. Because the fix never touched the shared function,
it could not propagate to any other caller by construction; every other stage had to independently
either (i) exclude `inherited_unit` from what it asks `bounded_records` for (S3, S6), or (ii) build
its own separate batching path for it (S4, and S6's `api_reference` sub-batches), or inherit no
protection at all. S5 is the one stage that did neither: `presentation_planning.yaml` is the only
job manifest with no `fact_kinds` override, so its packet builder defaults to asking for everything,
and nothing downstream of that default ever narrows or batches the result.

Exercise-wise: PDF-TypeScript is the only repository in the current record whose measured
inherited-unit count (437, confirmed twice - the original facts-only read and the unchanged
`09e3d13` digest in the PDFTS-REDRAW draw) is large enough to push this specific field over a
262,144-token context ceiling, and it is also the only repository that was blocked *earlier* in the
pipeline (S3, then the S4 timeout) for the ten days between item 31 and item 97's draw - meaning no
draw of this repository had a live chance to reach S5 at all until today. Both are true at once: the
gap has been sitting in `bounded_records` since before item 27 even landed (nothing added an
`inherited_unit` branch to it, ever, on any repository), and no repository both large enough and
far enough through the pipeline to trip it existed until PDF-TypeScript cleared S3 and S4 in the
same draw, today.

## 5. A second, unfixed instance of the identical class, in the same packet

Not speculative - read directly against the current tree, same file, same job, same 437-unit driver.
`composition/planning.py::_selectable_dispositions` (lines 170-196), the function that builds
`planning_packet`'s own **`"dispositions"`** field (line 260, right next to the `"facts"` field the
PROPOSAL above targets):

```python
# src/repository_presenter/components/readme/composition/planning.py:183-196
supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
redact = _uncitable_redaction(facts)
entries = []
for entry in dispositions.get("dispositions", []):
    shown: dict[str, Any] = {}
    for key, value in entry.items():
        if key == "fact_ids":
            shown[key] = [i for i in value if i in supported]
        elif key == "rationale" and isinstance(value, str):
            shown[key] = redact(value)
        else:
            shown[key] = value
    entries.append(shown)
return {**dispositions, "dispositions": entries}
```

This iterates **every** entry in `dispositions["dispositions"]` - one per inherited unit, since S4
writes exactly one disposition per unit (confirmed by `reconciliation_schema`'s own `minItems`/
`maxItems` = the batch's unit count, lines 260-262 of `dispositions.py`) - with no length limit
anywhere in the function. It only ever narrows *within* an entry (`fact_ids` filtered to SUPPORTED,
`rationale` redacted); it never drops an entry. On PDF-TypeScript this field is exactly as large as
the driver that broke `"facts"`: the PDFTS-REDRAW entry's own measurement puts it at 132,511
characters, roughly 19% of the packet's 694,205-character total, scaling 1:1 with the same 437-unit
count. **If the PROPOSAL in §2/§3 lands narrowly - an `inherited_unit` cap inside `bounded_records`,
or a declared, capped `fact_kinds` for `presentation_planning.yaml` - neither change touches
`_selectable_dispositions`, which reads straight from the `dispositions` argument `planning_packet`
receives, not from `bounded_records` at all.** A repository whose disposition count alone (without
even needing a comparably large `"facts"` field) crosses the remaining token budget would trip the
identical `ContextWindowExceededError` a second time, on the very next stage past a narrow fix -
precisely the "one fix, one redraw, repeat" cost the Words-.NET report (investigation 06, §5) already
named and recommended landing paired fixes to avoid.

A second, related-but-distinct latent risk, already known and re-confirmed live rather than newly
found here: investigation 06 §4 (this project's own prior report) documented that
`reconciliation/dispositions.py::reconciliation_schema` (lines 247-256) pins *which* fact IDs a
disposition's own `fact_ids` array may cite (`dispositions["items"]["properties"]["fact_ids"]["items"]
= {"enum": citable}`) but sets no `maxItems` on that array itself - only the outer `dispositions`
array is bounded to the batch's own unit count (lines 260-262). Read again here against the current
tree: **still true, unchanged.** This is a different failure shape from §3/§5 above (an unbounded
*count of citations inside one disposition*, not an unbounded *count of facts or dispositions in a
packet*) and was found on Aspose.PDF for .NET, not PDF-TypeScript - but it sits in the same job (S4)
this repository's own 437-unit, 3,133-fact surface would exercise at real scale, and is recorded here
as a standing, already-diagnosed, not-yet-landed risk this repository's own history has not
independently triggered only because S4 has so far always completed cleanly for it (11/11 calls,
HTTP 200, per the PDFTS-REDRAW entry).

Checked and found **not** similarly vulnerable, for the reasons in §3: S6's per-task packets
(plan-scoped by construction), S6's `api_reference` batching, and S8's `coherence_packet`
(explicit `_SPELLING_CAP` plus plan-scoped `accepted_facts`). The extractors themselves (facts and
evidence extraction, before any job packet exists) do not build LLM packets at all and are not
exposed to this class of defect.

## 6. Honest recommendation

**The repository's current, precise blocker is `BLOCKED_PLANNING` at S5 `presentation_planning`:
HTTP 400, `litellm.ContextWindowExceededError`, 298,865 input tokens against a 262,144-token model
limit, root-caused to `composition/planning.py::planning_packet`'s `"facts"` field admitting every
`inherited_unit` fact uncapped via `bounded_records`'s missing branch for that kind.** As of
`origin/main`'s current tip (`542bfe0`, landed mid-investigation - see the header), this finding is
now a real, numbered arrival item - **item 120** - formally admitted into `RESEARCH_AND_GUIDELINES.md`
§27.9's queue. It is **not yet a landed fix**: `542bfe0` touches one line of one docs file, `src/`
is untouched, `bounded_records` still has no `inherited_unit` branch (confirmed directly against
this worktree's own now-current tree), and the repository's disposition is still `BLOCKED_PLANNING`
in every artifact that records it. The fuller, more detailed measurement trail - the actual S3/S4
pass and the reproduced 400/298,865 figure - lives only in `docs/DECISION_LOG.md` inside worktree
`C:/w/pdfts1` (branch `pdfts/investigate`, commit `e3af3ef`), which **remains unpushed**: 1 commit
ahead of, and now considerably further behind, `origin/main`. Whoever lands item 120's actual fix
should pull that entry's own measurement detail into the shared record at the same time, rather than
working from the one-paragraph queue summary alone.

Two concrete recommendations follow directly from §5, not as a hedge but as the same lesson
investigation 06 already drew from this codebase's own history: **do not land a fix for `"facts"`
alone and spend a fourth real redraw finding `"dispositions"` independently.** Both fields are driven
by the identical 437-unit surface, sit in the identical packet, and a narrow fix to one leaves the
other exactly as exposed as it is today. Landing an `inherited_unit`-shaped cap for both fields in
the same change - and, ideally, deciding at the same time whether `reconciliation_schema`'s own
per-disposition `fact_ids` count (§5, second paragraph) needs the same treatment before this
repository's own 3,133-fact surface reaches it at S4 on some future draw - is the one-round fix
`RESEARCH_AND_GUIDELINES.md`'s own threshold rule and loop-prompt.md §6 rule 4 already argue for.
Separately, and not a code-fix recommendation: `pdfts1`'s own unpushed commit is real, unclaimed
diagnostic work sitting in a worktree `git worktree list` does not mark `locked` (unlike this
session's own worktree and its siblings) - nothing currently prevents it from being reused or
removed out from under its one unpushed commit. Whoever picks up the PROPOSAL should push that
commit (or supersede it with a better-evidenced entry) before it goes stale the way investigation 06
found item 90 had.
