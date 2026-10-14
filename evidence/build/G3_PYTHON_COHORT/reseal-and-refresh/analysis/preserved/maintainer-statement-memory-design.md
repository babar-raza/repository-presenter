authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# Maintainer statements that no fact can verify: policy and system-side memory (design only)

Status: DESIGN PROPOSAL, nothing implemented, no tracked file edited. Read-only lane, 2026-10-12.
Read at origin/main `7299f628` (exported with `git archive` to the scratchpad; the local checkout is
still at `460607fa`, 13 commits behind, and differs in dispositions.py, deferrals.py, review.py,
placement.py, claims.py). Line numbers below are origin/main. Measurements on committed bundles were
taken from the working-tree `candidates/` (older revisions) with PowerShell because neither python
nor node is on this shell's PATH; they are indicative, not exact.

"S2 investigation" in the request is read as S3 `repository_investigation`; stage numbers follow
README_CONTRACT section 3 (S2 Facts, S3 Investigation, S4 Reconciliation).

---------------------------------------------------------------------------------------------------

## 0. Answer in brief

1. **Keep them, and keep them verbatim.** A maintainer statement that no fact verifies and no fact
   contradicts is kept exactly as written. That is already what the standard says
   (`README_STANDARD.md` 5.3: "uncertainty the evidence cannot resolve ... is preserved as written
   and flagged"; PRC-05; STR-16) and what `plans/idea.md` L338-346 and L470 say. The code does not do
   it: it loses or flaps these statements in five places, L1 to L5 (section 1).
2. **Attribute in the system, not the README, with a sidecar, not a new fact kind.** One sealed
   bundle artifact `maintainer_statements.json` (the receipt) records, per statement, origin,
   content hash, anchor, source blob and a verification status
   `UNVERIFIED_MAINTAINER_STATEMENT`. Validators and the reviewer read it. The README carries no
   marker, no hedge, no HTML comment.
3. **Memory = the chain of sealed receipts**, read from the bundle `CURRENT` names. That needs no
   new mutable store, no publish-path change, and cannot invalidate anything it did not touch. A
   mutable per-repository ledger (owner edits, audit results between seals) is a later, optional
   layer and has a real hazard with `candidates_publish` (section 6.3).
4. **Sequencing that matters more than the design:** the baseline is pristine today (no
   presenter PR is merged into any registry repository's README: `ops/` holds no proposal
   authorization, and the owner's standing rule is to hold all writes to Aspose repositories; the only
   permitted target is the sandbox canary). The first sealed receipts therefore get origin = MAINTAINER for free. After the first
   merge our own sentences are in the live README and the analysis clone is `--depth 1`
   (`core/git_safety/clone.py:123`), so origin can no longer be proven from git. **Seed before the
   first merge; the carry-forward reader must land before the first refresh after a merge.**
5. **Recommended for Monday 2026-10-19:** Stage 0 + Stage 1 below, about 26-34 engineer-hours.
   Stage 0 alone (about 6-8 h) removes the reviewer flapping that currently un-seals 3D-TypeScript
   and PDF-.NET. The clean design is about 75-95 h in total over four stages.

---------------------------------------------------------------------------------------------------

## 1. What happens today to a maintainer statement with no supporting fact

Take one statement M in the live README, e.g. "`PdfViewer` prints through an installed printer on
Windows only" or "OBJ export only writes geometry attached at the very top of the scene graph".

| Stage | What the code does with M | Where M can be lost or become "ours" |
|---|---|---|
| S2 facts | M becomes an `inherited_unit:NNN.<kind>` fact: value = exact source lines, evidence = README line range, `attributes.section` = heading path (`evidence/facts/inherited.py`, docstring). Polarity SUPPORTED means "this text exists", nothing more. **IDs are ordinals** and shift when anything above M changes; a list is one unit with many bullets. | Nothing is lost here, but the identity is unstable: any key for M must be content-addressed, never the unit id. |
| S3 investigation | `prompts/repository_investigation.yaml:113-116`: "A claim the inherited README makes that no fact supports goes into `uncertainties` as a question, not into a statement." | **L1.** `uncertainties` is a required field of the investigation output (`repository_investigation.yaml:53`), but nothing in `src/` reads it (grep finds no consumer); S4 and S5 receive `investigation.json` as context only. The "preserve the uncertainty" channel binds nothing. |
| S4 reconciliation | The model returns exactly one of eight dispositions (`dispositions.py:216-225`). The prompt (`source_reconciliation.yaml:103`) defines `DEFER_UNRESOLVED` as "the facts neither support nor contradict; listed for the owner and never rendered". There is **no code check that a `VERIFIED_PRESERVE` is actually supported**: `placement_errors` (`dispositions.py:2416`) only requires a placeable destination. An uncited `OMIT_UNSUPPORTED` on prose is refused once, then `recover_uncited_prose_omits` (`dispositions.py:2753`) turns it into `DEFER_UNRESOLVED` with `RECOVERED_OMIT_RATIONALE` ("held as unresolved for the owner"). | **L2: silent deletion.** A deferred unit is never placed (`placement.py:98`, `PLACED` = PRESERVE/MOVE). Its class is `NO_EVIDENCE_EITHER_WAY` (`deferrals.py:725`), ADVISORY, and unlike three sibling classes it is **not** in `ESCALATIONS` (`deferrals.py:869`), so even when the README states nothing of it, nothing fails. "Listed for the owner" means one line in `validation.json` `advisory` (`registry.py:2368`) and the review packet; the regeneration PR body is "headings and counts only" (`propose/pull_request.py:13`). It reaches no human. |
| S4 -> S6 | The model may instead `SUPERSEDE_REDUNDANT` / `VERIFIED_REWRITE` M into `scope_limitations`; S6 then re-authors it as `limitation:N` citing `public_symbol` facts (the plan hands units via `material_limitations.unit_ids`, `presentation_planning.yaml:201`). BC-04 (`authoring.unit_checks`) checks identifiers and citations, not the behavioural claim. | **L3: our paraphrase of an unverifiable claim is a claim of ours**, checked by names only. Evidence that BC-04 does not reach behaviour: the PDF-.NET candidate sealed with a Scope opener claiming PDF-to-PostScript output that the code rejects (acc-w7-pdf-net B1). |
| S7 placement | Kept units print as written, but a unit is dropped when the destination "states all of it" by word/stem coverage (`placement.py:633-760`, `coverage.uncovered`). | A paraphrase that overlaps by symbol facts can replace M. |
| S9 BC-05/BC-08 | BC-05 checks one disposition per unit, deferral classes, placed-unit presence. BC-08 protects commands and code blocks, "prose, links, badges and limitations not" (`README_STANDARD.md` 6.2 item 6). | Nothing blocks the loss of a true limitation. PRC-03's floor is "Verified claims preserved ... must not fall" (`README_STANDARD.md:785`): an unverified statement is not a verified claim, so by the letter its loss does not count. |
| S10 BC-10 | A kept unit is evidence for itself only: `factuality_defect` (`review.py:604`) returns `FACTUALITY_UNCHECKABLE` / `FACTUALITY_INHERITED_ONLY` when the finding names no product fact. Both are in `JUDGMENT_RULES` (`review.py:531-545`), which annotate but never refute. `_Scope.apply` (`review.py:2645+`) sets `withhold` when the quote is carried by a kept unit, so the finding is routed to S4 and **stays blocking**. | **L4: flapping.** Repair returns "matches the causal stage's own output unchanged" (wave-6 triage: 4 no-op rejections across the four repositories with kept-text failures, 3D-TypeScript among them) so the finding is unrepairable and the row fails: 3D-TypeScript sealed in waves 4 and 5, failed in wave 6 (F09-F14, all `fact_ids: []`); PDF-.NET failed wave 6 (F09-F15) and sealed wave 7 "variance of the reviewer read rather than a fix". AGENTS.md says an unrepairable finding is advisory. |
| refresh at a new revision | `present` computes `bundle_directory(candidates, entry, clone.revision)` (`cli.py:4322`): bundles are per (repository, revision). A new revision has no sealed bundle, so `evaluation` is "no sealed bundle for this revision; every stage runs" and the call store is not seeded (`cli.py:4378` only seeds from that same revision's bundle). | **L5: no memory across revisions.** S4 re-decides every unit with a fresh sample (temperature 0 but the request hash changes with any fact in the batch). The same statement can be kept at revision A and deferred at B. Nothing records "this was kept last time, source unchanged". |

What the correction (live-first) lane does: `components/readme_correction/__init__.py` keeps every
byte except a claim a fact positively contradicts, a missing section, a broken link; `model.py`
`Finding`: "an unverifiable claim is not 'corrected'". Unverifiable statements are preserved by
construction there, and the span-level edit list already records what is ours. **The memory problem
exists only in the regeneration lane**, where kept text and authored text are interleaved in one
rendered file.

Evidence that the statements matter and that they are not all true (this is the honest base rate):

- True and lost or blocked: PDF-.NET wave 7 acceptance (`acc-w7-pdf-net.md`): the seven kept
  maintainer limitation bullets were 4 PASS and 2 COULD_NOT_VERIFY (XFA, System.Drawing on
  Linux), and four live limitations the candidate dropped were each TRUE (text-based comparison,
  PostScript interpreter gaps, PdfViewer printing, LTV note). 3D-TypeScript wave 3: "six verified
  live limitations lost". TeX-Python wave 7: "TRUE loss of specific limitations". Slides-Java F03 and
  3D-TypeScript F07/F08 have `fact_ids: []`.
- False and kept: 3D-.NET `NurbsSurface.ToMesh throws NotImplementedException` (code returns a
  placeholder mesh), 3D-Java `FileFormat.STLASCII` writes binary, Cells-Go "CalculateFormula supports
  only SUM, AVERAGE, MAX, MIN" (22 functions exist). `README_STANDARD.md` DEF-06: 4 of 43 live
  READMEs carry a contradicted capability or limitation claim; `data/correction_holds.json` holds 3D-.NET
  for advertised formats the code rejects.
- Scale (29 committed bundles, working tree): 268 kept prose units, 32 deferred prose units,
  108 omitted prose units. A receipt is on the order of 10-30 statements per repository.

So the policy has two edges and the design must serve both: preserve what cannot be checked, and
make "this is the maintainers' own text" a machine-readable fact so a contradicted one can be routed
to the upstream-issue path (`components/issues`) instead of being silently printed "as verified".

---------------------------------------------------------------------------------------------------

## 2. Why keeping is defensible, and where the line is

- `plans/idea.md` L343: each unit is validated "against accepted repository/package evidence **or an
  authoritative owner**"; L344-346 "unresolved content is omitted or carried as explicit uncertainty
  for owner resolution"; L470: "preserve the uncertainty and flag the gap for review rather than
  inventing, assuming, or presenting the claim as fact". AGENTS.md: README content is "valuable
  evidence, not automatic truth"; "Preserve uncertainty when evidence cannot resolve it".
- The asymmetry: the statement is **already live under the maintainers' name**. Keeping it creates no
  new exposure; deleting a true one is our editorial loss and breaks PRC-05; keeping a false one equals
  the status quo and is caught by the contradiction path and the audit.
- The line: a kept statement is evidence of what the maintainers state, never evidence that it is
  true, and **never citable as support for anything else**. That is why the wave-6 "option A" (a new
  fact kind `maintainer_statement`) is rejected as framed: a fact is citable by every plan item, unit
  and investigation statement, so it would launder an unverified sentence into support for new claims,
  would need a `facts.schema.json` change (owner admission) and an extractor bump (facts scope,
  INVALIDATED for all bundles).
- One owner decision is unavoidable: idea.md L470 says "flag the gap". The owner has now said not in
  the README. The design flags it system-side (receipt, review advisory, optional PR sentence, issue
  on contradiction). Needs an explicit ruling (section 10, Q1).

---------------------------------------------------------------------------------------------------

## 3. Options evaluated

| Option | Verdict | Reason |
|---|---|---|
| (a) per-candidate sidecar (`origin: maintainer`, blob sha, lines, text hash, `UNVERIFIED_MAINTAINER_STATEMENT`) | **Adopt**, as a separate bundle file, not as fields inside `dispositions.json` | `DispositionsV1` is closed and part of every S4 request digest; `content_units.json` is authored-only. `seal.py:142` `OPTIONAL_ARTIFACTS` takes a new file with no change to `schemas/candidate-bundle.schema.json` (its `files` map allows extra keys); `invalidation.py:177` `ARTIFACT_SCOPES` needs one row. |
| (b) repository-scoped committed ledger | **Adopt in two steps.** Step 1: the receipt chain (read the receipt of the bundle `CURRENT` names). Step 2, only if the owner wants edit/retire or audit between seals: a mutable ledger under `data/maintainer_statements/`, not under `candidates/<slug>/` | `git_ops.overlay_bundle` (`candidates_publish/git_ops.py:108`) does `rmtree` + `copytree` of `candidates/<slug>/`, and the effect stages only the revision directory and `CURRENT` (`effect.py:182`). A sibling `statements.json` is deleted or never published unless the export artifact carries it. The receipt in the revision directory travels with the bundle for free. |
| (c) provenance in the PR description | **Adopt as a complement, owner decision (Q3)**, never as memory | It is the only channel that reaches the authoritative owner, but the composer is deterministic and "headings and counts only"; listing text changes its leak contract. One neutral sentence and a count is enough. A merge is not verification. |
| (d) periodic statement audit | **Reframe.** Re-admission on every refresh already re-tries deterministic verification for free (a new fact flips the status). The LLM `claim_audit` (quoted-line evidence, DEF-06) is a separate lane (live-first Phase 3, 6-8 days) | Hook the status transitions now, build the auditor elsewhere. |
| (e) derive origin from git history / blame | Reject for v1 | `--depth 1` clone; moves and squashes defeat blame. A v2 origin proof could read the target's PR history (`propose/effect.py` already reads every PR state and recognizes its own by `candidate_hash:`). |
| (f) in-README markers (HTML comments, anchors, hedging words) | Reject | Owner: README clean. The maintainers see the raw diff. |
| (g) new fact kind `maintainer_statement` | Reject | Section 2. |
| (h) new disposition value | Reject | `VERIFIED_PRESERVE` appears in 10 files (28 uses in dispositions.py alone); a value outside the S4 enum is a prompt-schema/digest question. Keep the disposition, annotate it. |
| (i) leave it to a second corroborating read | Reject | Stochastic; the rejected shape is unrepairable by construction. |

---------------------------------------------------------------------------------------------------

## 4. Recommended design

### 4.1 Vocabulary

- **Statement**: the smallest unit the system prints verbatim: a paragraph, a blockquote, or one
  top-level list item (`composition/list_coverage.list_items` already defines items).
- **Admitted statement**: a statement from the live README that the system keeps as written without
  a supporting fact, under rule MS-ADMIT below. Status `UNVERIFIED_MAINTAINER_STATEMENT`.
- **Receipt**: `maintainer_statements.json`, sealed in the bundle.
- **Statement id**: `ms-` + first 16 hex of `text_sha256`, where
  `text_sha256 = sha256( " ".join(text.split()) )` after removing a leading list marker; no case
  folding, no markdown stripping (a changed link target is a changed statement). Never the unit id.

### 4.2 Data flow (all deterministic, no new LLM call, no clock)

```
S1/S2  live README -> inherited_unit facts (unchanged)
S3     unchanged
S4     model -> dispositions (unchanged request, so no digest change) -> normalize (unchanged)
NEW    admit_maintainer_statements(dispositions, facts, previous_receipt) -> dispositions', receipt
S5/S6  planning/authoring: admitted units are not citable in material_limitations.unit_ids
       (planning.py:479 citable_unit_ids filters them) and not owed by authoring.carried_units
S7     placement: an admitted unit prints verbatim and is exempt from the fact-overlap and stem-coverage
       drop (placement.py:633+), unless the destination contains it byte for byte
S9     BC-05 sub-rules MS-V1..V4 recompute the receipt and compare; BC-07 narration scan covers markers
S10    reviewer: dispositions + receipt in the packet; deterministic demotion rule
S12    seal: receipt is an OPTIONAL_ARTIFACT; dependencies.json records consumed_maintainer_statements
refresh  previous_receipt = receipt of the bundle CURRENT names (verify_bundle first)
```

### 4.3 MS-ADMIT: when a statement may be kept without a fact (registry-driven, not if/elif)

All must hold; each is a row in a small registry so a new ecosystem or topic is a row, not a branch.

- A1 kind: paragraph, blockquote, or list item. Never heading, badge row, code block, HTML block,
  table, link-only unit.
- A2 topic: the unit's source topic (`composition/source_topics.py:56`, topic `limits`:
  limit, supported, compatib, known, restrictions, caveats, status, roadmap, notes) or an inherited
  addition heading (OD-09: History, an MCP server section, and similar). Marketing and "other
  platforms" prose stays `OMIT_UNSUPPORTED`.
- A3 S4 state: the model (or a deterministic fold) left it as `DEFER_UNRESOLVED` with class
  `NO_EVIDENCE_EITHER_WAY`, or as a recovered uncited omission (`RECOVERED_OMIT_RATIONALE`) with
  `_no_evidence` true; or it is already `VERIFIED_PRESERVE`/`MOVE` whose cited facts are
  `NAME_ONLY` (kinds in `review._NAME_ONLY_KINDS` plus `inherited_unit`, `package`, `identity`),
  in which case it is only **recorded**, not folded.
- A4 no contradiction: no cited fact is CONTRADICTED; unit not in `contradicted_code_units`; no
  contradicted embedded link (`dispositions.py:755-790`); `validation/claims.py` finds no
  version/install/publication contradiction in its text.
- A5 not a claim shape that has a deterministic owner (install, publication, version, command, count,
  edition naming, format direction, link target). Those stay under BC-02/03/06/08/12/14 and are
  deferred or corrected exactly as today.
- A6 origin proof (4.5).
- A7 bounds: at most 600 characters per statement; more than 40 admitted per repository is an
  advisory in `validation.json`, not a block.

Effect on `dispositions`: A3-fold sets `disposition = VERIFIED_PRESERVE`, `destination_section` =
`destinations.nearest_holdable(...)` (the existing "recover to keep" helper, `dispositions.py`
`_recovered_home`), `fact_ids` = the symbol facts the text spells (existing
`inherited_unit_named_symbols`), `rationale` = "Kept as written: maintainer statement, no fact either
way." The disposition's honest status is in the receipt, not in its name.

### 4.4 Carry-forward (receipt chain)

At refresh, for each statement of the current live README compute `text_sha256` and match against the
previous receipt, in this order:

1. same hash, same anchor -> `CARRIED` (keep without re-deciding; status carried);
2. same hash, different anchor -> `CARRIED_MOVED` (anchor updated);
3. no hash match but an unmatched previous entry in the same anchor with similarity >= 0.8 ->
   previous entry `EXPIRED_EDITED`, the new text is a **new** statement that starts UNVERIFIED and goes
   through MS-ADMIT again (verification never inherits across an edit);
4. previous entry with no match anywhere -> `REMOVED_UPSTREAM`: dropped from the new receipt and never
   re-added. **The receipt never injects text; it only annotates units present in the current live
   README.**

The receipt of revision B lists its predecessor (`carried_from.revision`, `record_sha256`), so the
chain is auditable offline. A failed or unsealed attempt does not move `CURRENT`, so the chain skips
it. An INVALIDATED `CURRENT` is still readable.

### 4.5 Origin proof (the anti-laundering rule)

After a merge, our own authored sentences sit in the live README and look maintainer-written. Rule
for a statement not found in the previous receipt:

- It is `origin.authority = MAINTAINER` iff its hash occurs in no README we ever proposed, **other
  than as a receipt-listed maintainer statement**. Concretely
  `system_texts = hashes(README.md of every bundle under candidates/<slug>/ and every correction
  bundle for the slug) - hashes(all receipt statements)`. A hash in `system_texts` is
  `origin SYSTEM` and is never admitted: it must be supported by facts now, or it is corrected or
  omitted like any other unsupported sentence.
- This needs the receipt to list **every** kept maintainer prose item (corroboration
  `BEHAVIOURAL`, `NAME_ONLY`, `NONE`), not only the unverified ones; otherwise a verified-then-
  unverifiable maintainer sentence would classify as ours and be dropped (fail-closed, but lossy).
- First ever run for a slug (no previous receipt, no earlier bundle README): origin MAINTAINER with
  `basis = BASELINE_UPSTREAM_README`, and the receipt records the README blob id
  (`manifest.upstream_blobs` already holds README path -> blob id, `core/candidates.py:44`).
- If the origin cannot be established (unreadable bundle history), admit nothing new and say so in
  `refused[]` with reason `ORIGIN_UNPROVABLE`. Fail closed.

### 4.6 Lifecycle of a statement

```
          admitted                     text edited upstream
  (new) ------------> ACTIVE ------------------------------> EXPIRED_EDITED (new statement starts)
                        |  ^                                   
                        |  | carried each refresh              removed upstream
                        |  +-----------------------------------> REMOVED_UPSTREAM (never re-added)
                        |
                        | new SUPPORTED behavioural fact appears -> verification VERIFIED (kept; leaves the unverified set)
                        | quoted-line evidence contradicts       -> verification CONTRADICTED -> not kept
                        |                                           (CORRECT_WITH_EVIDENCE or omit + issue handoff)
                        | owner retires (Stage 3 only)           -> RETIRED_BY_OWNER
```

### 4.7 Invariants

- I1 Never publish an unverified claim of ours. Admitted statements print byte for byte from the
  inherited unit; any paraphrase, merge or reword changes the hash and loses admission.
- I2 Contradicted is never preserved. Admission is refused on any contradicting fact or deterministic
  claim detector; `verification.status = CONTRADICTED` can never be `keep`.
- I3 Upstream edit or removal updates the memory (4.4). The receipt cannot resurrect removed text.
- I4 Not a defect of the candidate: the reviewer demotes an "unsupported" finding against an admitted
  statement to a visible advisory. A finding that cites a CONTRADICTING product fact, or alleges the
  candidate **altered** the statement, still blocks.
- I5 Determinism: admission is a pure function of (facts, normalized dispositions, previous receipt).
  No clock, no LLM, no randomness; receipt bytes are identical on replay; BC-11 (fresh process, zero
  calls, byte-identical) holds. History timestamps, if any, live outside sealed bytes.
- I6 Narrow invalidation: only entries a candidate admitted or carried are recorded as consumed. With
  the receipt chain there is no shared mutable store at all.
- I7 README clean: no id, comment, anchor, hedge or attribution word in the README; BC-05/BC-07
  assert it, and authored-text packets never receive the receipt, so the composer cannot mention it.
- I8 Not citable: no plan item, content unit or investigation statement may cite a statement id (the
  fact-id enums exclude it by construction). Statements are annotations, not facts.
- I9 Scope: prose only; shapes with a deterministic owner stay with it (A5).
- I10 Fail closed on unprovable origin (4.5).
- I11 Untrusted data: statement text is passed to the reviewer under the existing "untrusted"
  preface and is never an instruction.

### 4.8 Validators (BC-05 sub-rules, no new check id)

BC-05 `_check_dispositions` (`validation/registry.py:1422`) gains, and `advisory_notes` (:2368) reports
the count of unverified statements:

- MS-V1 every receipt statement's unit is `VERIFIED_PRESERVE`/`MOVE` and its normalized text occurs
  verbatim in the destination section (same `_normalized(placement.text) in _normalized(haystack)`
  test already used for placed units). Stage COMPOSING or RECONCILING by cause.
- MS-V2 no receipt statement is CONTRADICTED; nothing in `refused[]` appears in the README.
- MS-V3 README contains no `ms-` id, no HTML comment carrying one, no phrase from a closed
  attribution list ("according to the maintainers", "the maintainers state", "as stated by",
  "unverified", "claimed by"): extend `text_checks._NARRATION` (`review/acceptance/text_checks.py:51`)
  and BC-07's narration vocabulary. This is a backstop only; the real guard is that no authored
  prompt packet carries the receipt.
- MS-V4 recompute the expected receipt from facts + dispositions + the previous receipt and require
  equality with the sealed one (determinism and tamper check).

### 4.9 Reviewer rule (`review.py`)

New rule `MAINTAINER_STATEMENT_ADMITTED`, a **demotion**, not a refutation (it must stay visible in
`review.json` advisory with its reason; the acceptance score still counts it):

Fires when all hold: the finding's criterion is factuality or limitations; its quote is carried by an
admitted statement's text (`_carried_by_units`, `review.py:1910`, over receipt texts); the rulings
include `FACTUALITY_UNCHECKABLE`, `FACTUALITY_INHERITED_ONLY` or `CITED_SYMBOL_NAMED`; it cites no
CONTRADICTED product fact (`factuality_defect` already returns None for that case); it alleges no
absence or omission. Record
`demoted: {rule, section, stage: "S4", owner: "maintainer", reason, evidence: {statement_id,
text_sha256, verification}}`. Clean design also adds a `maintainer_statements` field to
`review_packet` (`review.py:335`) and a paragraph to `prompts/independent_review.yaml`: "Statements
listed in `maintainer_statements` are the maintainers' own text printed as written, not a claim of the
candidate; report one only when a supplied fact contradicts it."

Governance argument that stands without the ledger: these findings are unrepairable by construction
(kept text prints as written; the repair returns a no-op). AGENTS.md: a finding that names no stage
repair can act on is advisory. Stage 0 uses exactly this argument.

### 4.10 Invalidation and recheck

- `dependencies.json` gains `consumed_maintainer_statements: {statement_id: record_sha256}` where
  `record_sha256 = canonical_hash({text_sha256, origin.authority, verification.status,
  evidence_sha256})`. Same pattern as `consumed_fact_ids` (`seal.py:361`, `evaluation.py:105-110`).
  Absent in every existing bundle, read as empty: **the field by itself invalidates nothing** (the
  version bumps of 6.2 are the usual `VALID_UPDATE_AVAILABLE` cascade, not an `INVALIDATED` one).
- `evaluation.evaluate` compares only the consumed ids: a change is
  `maintainer_statements` -> scope `reconciliation`, `VALID_UPDATE_AVAILABLE`, re-enters RECONCILING;
  a consumed entry that became CONTRADICTED is `maintainer_statements.contradicted` -> scope `facts`,
  `INVALIDATED` (a factual defect, AGENTS.md and STATE_MACHINE section 9). Two rows in
  `DEPENDENCY_SCOPES` (`invalidation.py:136`); the manifest scope enum is untouched (no schema change).
- `ARTIFACT_SCOPES` (`invalidation.py:177`): `maintainer_statements.json` -> `reconciliation`.
- `bundle/recheck.py`: new row, re-run the admission fold over the sealed dispositions with the current
  receipt and require the sealed receipt (a pure offline read, like the other rechecks).
- `STATE_MACHINE.md` section 9 table gains the row.

---------------------------------------------------------------------------------------------------

## 5. Exact schemas

### 5.1 Bundle receipt `candidates/<owner>__<name>/<revision>/maintainer_statements.json` (sealed, no clock)

```json
{
  "schema_version": 1,
  "repository": "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET",
  "source_revision": "10a363830fea952c29df20fdb37d35ad3a881433",
  "carried_from": {"revision": "<prior CURRENT revision or null>", "manifest_sha256": "<64 hex or null>"},
  "statements": [
    {
      "id": "ms-3f9c1d7a2b4e6081",
      "text_sha256": "<64 hex>",
      "text": "`PdfViewer` prints through an installed printer on Windows only.",
      "unit_id": "inherited_unit:226.list",
      "item": 4,
      "unit_kind": "list_item",
      "category": "LIMITATION",
      "anchor": {"headings": ["Aspose.PDF FOSS for .NET", "Scope and Limitations"], "ordinal": 4},
      "destination_section": "scope_limitations",
      "disposition": "VERIFIED_PRESERVE",
      "admitted_by": "MS-ADMIT-1",
      "s4_before_admission": {"disposition": "DEFER_UNRESOLVED", "deferral_class": "NO_EVIDENCE_EITHER_WAY"},
      "origin": {
        "authority": "MAINTAINER",
        "basis": "BASELINE_UPSTREAM_README",
        "readme_path": "README.md",
        "readme_blob": "<40 hex git blob id>",
        "lines": [1712, 1712]
      },
      "verification": {
        "status": "UNVERIFIED_MAINTAINER_STATEMENT",
        "corroboration": "NAME_ONLY",
        "corroborating_fact_ids": ["public_symbol:aspose.pdf.facades.pdfviewer"],
        "method": null,
        "evidence": null,
        "checked_revision": "10a363830fea952c29df20fdb37d35ad3a881433"
      },
      "carry": {"state": "NEW", "previous_id": null, "previous_record_sha256": null}
    }
  ],
  "refused": [
    {"unit_id": "inherited_unit:230.paragraph", "text_sha256": "<64 hex>",
     "reason": "CONTRADICTED_BY_FACT", "fact_ids": ["install_command:dotnet"]}
  ]
}
```

Closed sets: `category` LIMITATION | CAVEAT | NARRATIVE | STATUS | OTHER; `origin.authority`
MAINTAINER (SYSTEM is never written to a receipt); `origin.basis` BASELINE_UPSTREAM_README |
CARRIED | NOT_IN_ANY_PROPOSED_README | OWNER_RULING; `verification.status`
UNVERIFIED_MAINTAINER_STATEMENT | VERIFIED | CONTRADICTED; `corroboration` BEHAVIOURAL | NAME_ONLY | NONE;
`carry.state` NEW | CARRIED | CARRIED_MOVED; `reason` CONTRADICTED_BY_FACT | CLAIM_SHAPE_HAS_OWNER |
TOPIC_NOT_ADMISSIBLE | ORIGIN_UNPROVABLE | ORIGIN_SYSTEM | TOO_LONG. When `verification.status` is VERIFIED or
CONTRADICTED, `method` is e.g. FACT | CLAIM_AUDIT and `evidence` is `{path, quote, revision}` where the
quote must occur in the file at that path (the DEF-06 rule).

Receipt lists **every** kept maintainer prose item, with `corroboration` BEHAVIOURAL for supported
ones, because 4.5 needs the complement.

### 5.2 `dependencies.json` addition

```json
"consumed_maintainer_statements": {"ms-3f9c1d7a2b4e6081": "<record_sha256>"}
```

### 5.3 Optional mutable ledger (Stage 3 only) `data/maintainer_statements/<owner>__<name>.json`

Same entry shape as 5.1 plus: `state` ACTIVE | EXPIRED_EDITED | REMOVED_UPSTREAM | RETIRED_BY_OWNER;
`first_seen` and `last_seen` `{revision, readme_blob, lines, anchor}`; `decision`
`{"keep": true, "rule": "MS-ADMIT-1" | "OWNER", "by": "RULE" | "<owner>", "ruling": "<DECISION_LOG ref>"}`;
`history` as an ordered list of `{event, revision}` (no timestamps; git history of the file carries
time). Strict loader like `readme_correction/send.py:load_holds` (a missing key is a data defect, not a
silent default). Owner edits may retire or annotate; **nothing may force-add text**, and a loader check
proves every entry's text occurs in the README at `first_seen.revision` (recoverable offline from that
revision's bundle by reverse-applying `README.patch`, as `recheck.py` already does).

---------------------------------------------------------------------------------------------------

## 6. Minimal versus clean, effort, governed files

All hours are focused engineer-hours including focused tests, my estimate, not measured. The README
standard sizes comparable items in days (reconciliation default 4 d, BC-05/BC-08 floor 3 d, reviewer
3 d).

### 6.1 Stages

| Stage | Content | Hours | Lands |
|---|---|---|---|
| 0 Reviewer valve | `_Scope.apply`: demote the unverifiable-shape judgment findings whose quote is carried by a kept unit (`self.kept`, `_carried_by_units`) when no CONTRADICTED product fact is cited; record rule; tests with negative controls (contradicting fact still blocks; altered text still blocks). No ledger. | 6-8 | cut 6 |
| 1 Admission + receipt | `reconciliation/statements.py` (normalize, hash, eligibility registry, fold, receipt writer), call site in `repair/rounds.py` after S4, planning/authoring/placement exemptions, seal as OPTIONAL_ARTIFACT, `consumed_maintainer_statements`, evaluation/invalidation rows, BC-05 MS-V1/V2/V4, reviewer rule (replaces Stage 0's broader rule with the receipt-keyed one), docs, production-shaped proof on 3D-TypeScript, PDF-.NET, Slides-Java, canary | 20-26 | cut 6 |
| 2 Memory | previous-receipt reader, matching (4.4), origin proof (4.5), lifecycle, MS-V3 README-clean scan, `recheck.py` row, PR-body sentence if the owner agrees, tests for edit/remove/move/launder | 22-28 | **before the first merge** into any upstream README |
| 3 Audit and ledger | deterministic limitation extractors (SupportedOSPlatform, NotImplementedException grep) or `claim_audit` hook that sets VERIFIED/CONTRADICTED with quoted evidence, issue handoff for CONTRADICTED, optional `data/` ledger + `statements show/seed/retire` CLI, reviewer prompt v15 + packet field | 25-35 (mostly a separate lane: live-first Phase 3 is 6-8 d on its own) | after Stage 2 |

**Monday-next-week:** Stage 0 + Stage 1 = 26-34 h, one lane, needs the single shared-code slot
(`execution_limits.shared_code_items_in_progress` = 1) and a named work item. Stage 0 alone is the
emergency valve if the slot is not available. The 29 existing bundles need no backfill: they are stale
and will be re-sealed on final code, and the receipt appears at that re-seal. (An optional offline
backfill from sealed dispositions + facts is a zero-call command if a pre-merge snapshot is wanted.)

### 6.2 Governed files and constants touched (Stage 0+1; later stages in brackets)

| File | Change | Constant |
|---|---|---|
| `components/readme/reconciliation/statements.py` (new) | admission, receipt | rides `NORMALISATION_VERSION` 36 -> 37 (precedent: arrival item 110 bumped it for a fold called from `dispositions.normalize`); or its own `components.statements` row in `COMPONENT_SCOPES` -> `reconciliation` |
| `repair/rounds.py` | call after S4 acceptance | none |
| `composition/planning.py` (:479) | `citable_unit_ids` excludes admitted units | with NORMALISATION |
| `composition/placement.py` (:633) | exempt admitted statements from overlap/stem drop | `RENDERER_VERSION` 34 -> 35 only if sealed bytes move (`tests/test_sealed_bytes.py`) |
| `validation/registry.py` BC-05 (:1422) | MS-V1, V2, V4 [V3] | BC-05 8 -> 9, `VALIDATOR_VERSION` 23 -> 24 |
| `review/independent/review.py` (:2645) | demotion rule [packet field] | `REVIEWER_LOGIC_VERSION` 21 -> 22 |
| `prompts/independent_review.yaml` [Stage 3] | packet field + paragraph | prompt v14 -> v15 (reviewer scope, provenance) |
| `bundle/seal.py` (:142, :384) | optional artifact, consumed field | none |
| `bundle/evaluation.py`, `bundle/invalidation.py` (:136, :177) | compare, 2 + 1 rows | none |
| `bundle/recheck.py` [Stage 2] | recheck row | `RECHECK_VERSION` |
| `components/propose/pull_request.py` [Stage 2, owner Q3] | one neutral sentence + count | none |
| docs | `README_CONTRACT.md` 3 (kept units), 5 (rows 5, 8), 7 (bundle layout); `STATE_MACHINE.md` 9 (table); `README_STANDARD.md` 5.1 row 4 ("Verified claims **and admitted maintainer statements** preserved"), PRC-05 detector cell, 6.2 item 6; `REPOSITORY_LAYOUT.md` (new module, and `data/maintainer_statements/` if Stage 3); `DECISION_LOG.md` (owner ruling); owner may amend `plans/idea.md` L470 | n/a |
| `schemas/` | **none for Stage 0-2** (optional bundle artifact, strict code loader). A `schemas/maintainer-statements.schema.json` is optional and needs owner admission (section 31) | n/a |

Version cascade: all of these move the `reconciliation`/`authoring`/`validator`/`reviewer` scopes, i.e.
`VALID_UPDATE_AVAILABLE`, never `INVALIDATED`, and should ride one governed cut with one bump per
constant (README_STANDARD 6.2 sequencing; `tests/test_version_bump_discipline.py`).

### 6.3 The publish-path hazard (why not a ledger under `candidates/<slug>/`)

`candidates_publish/git_ops.py:108` `overlay_bundle` removes `candidates/<slug>` and copies the
downloaded artifact over it; `effect.py:182` stages only the revision directory and `CURRENT`. A
`candidates/<slug>/statements.json` (or `rechecks/<rev>.json`) not present in the exported artifact is
deleted on the hosted publish. The receipt chain avoids this because the receipt is inside the
revision directory. The investigation-13 `rechecks/` cache has the same exposure (not mine to fix;
noting it).

---------------------------------------------------------------------------------------------------

## 7. Risks

| Risk | Mitigation |
|---|---|
| **Staleness**: a kept statement stays unverified forever and is wrong. | Re-admission every refresh against new facts; hash-bound to the upstream text; contradicted -> not kept; Stage 3 audit; metric "unverified maintainer statements per repository" in `status`; optional PR sentence asks the maintainers to confirm. |
| **Hidden bad claims** (a false statement printed as part of a "verified" README). 3D-.NET, 3D-Java and Cells-Go already do this. | Status quo is no worse (PRC-03: not worse than live); the receipt makes the exposure countable and routable to `components/issues`; the acceptance reviewer still samples (`acc-w7`). Do not hide the count from the owner. |
| **Admission as an escape hatch** for S4 hallucinated defers (marketing text kept). | A2 topic registry, A5 claim-shape exclusion, A7 bounds, full blocking-check suite still runs on the kept text; promotional prose stays omitted. |
| **Laundering** our sentence into "maintainer". | 4.5 origin proof, fail closed; receipt lists every kept item so the complement is exact; ledger/receipt cannot create text. |
| **Silencing the reviewer** wrongly. | Demotion (visible), contradicting fact or altered text still blocks, I4. |
| **Privacy / long-term memory**: statement text is public README text, no secrets, but a control-repo copy outlives a maintainer deleting a sentence. | Keep `text` only while the statement is ACTIVE; on `REMOVED_UPSTREAM` keep `text_sha256` and metadata; BC-09 secret scan runs on the bundle already; statements are data to the reviewer, never prompts for authoring; no cross-repository memory. |
| **Determinism**: a clock or ordering leaks into sealed bytes. | I5; sorted keys; no timestamps; MS-V4 recompute; BC-11 test. |
| **Placement regression**: exempting admitted units from the overlap drop reprints a duplicate. | Exempt only when the destination does not contain the statement byte for byte; BC-05 `_dropped_list_failures` and coverage tests extended. |
| **Granularity**: a bundled list unit (one fact id shared by many bullets drops a whole unit, README_STANDARD 6.2 item 4). | Item-level entries; `uncovered_missing_items` already exists; do not rely on unit-level coverage for admitted items. |

---------------------------------------------------------------------------------------------------

## 8. Test plan (negative controls required by AGENTS.md)

- Admission: DEFER/NO_EVIDENCE_EITHER_WAY limitation is kept verbatim; a CONTRADICTED one, a
  version/install claim, a promotional paragraph, a code block, an over-long statement, an
  ineligible topic are each refused with the typed reason.
- Edit/move/remove/launder: edited statement expires and restarts UNVERIFIED; moved statement carries;
  removed statement is not re-added; a sentence in `system_texts` is refused `ORIGIN_SYSTEM`; unreadable
  history is `ORIGIN_UNPROVABLE`.
- Determinism: two runs and a fresh process give byte-identical receipts and a zero-call replay; a
  receipt with a clock or reordered keys fails MS-V4.
- Invalidation: ledger/receipt change for an unconsumed id changes nothing; a consumed id edit gives
  `VALID_UPDATE_AVAILABLE`/`reconciliation`; a consumed id flipping to CONTRADICTED gives `INVALIDATED`/`facts`;
  existing bundles without the field stay as they are.
- Reviewer: an unsupported-shape finding against an admitted statement is demoted and visible; the same
  finding with a CONTRADICTED fact blocks; a finding that quotes an authored paraphrase is not demoted;
  mutating the rule flips these (mutation test).
- README clean: id, comment, anchor, hedge word each fail MS-V3; the receipt never reaches an authoring
  packet (packet-content test).
- Production-shaped proof: official `present` on the canary, then 3D-TypeScript, PDF-.NET and
  Slides-Java (live gateway, 30-50 min each); BC-11 fresh-process no-op; then a second `present` at a
  perturbed revision (a one-line README edit in the sandbox repository) to prove carry-forward.

---------------------------------------------------------------------------------------------------

## 9. Rollout sequence

1. Owner rulings Q1-Q3 (section 10). 2. Stage 0 as a stop-gap if the slot is unavailable.
3. Stage 1 and Stage 2 in the next governed cut, before the first non-sandbox merge. 4. Re-seal on final
code (receipts appear). 5. Stage 3 with the live-first Phase 3 claim audit. The live-first (correction)
lane needs nothing: it already preserves bytes and its edit ledger is the span-level record of what is ours (PRC-09).

---------------------------------------------------------------------------------------------------

## 10. Open questions for the owner

1. **Wording of the standing constraint.** idea.md L470 says "preserve the uncertainty and flag the gap
   for review rather than ... presenting the claim as fact", L344-346 "carried as explicit uncertainty
   for owner resolution". Do you accept that "flag" means system-side only (receipt, review advisory,
   optional PR sentence, issue on contradiction), with the maintainers' sentence printed unhedged? If
   yes, the sentence should be amended so the code and the authority agree.
2. **Scope of "maintainer statement".** My proposal: limitations, caveats, notes and status prose, plus
   inherited additions (History, MCP). Positive capability or format claims are excluded (they need
   facts; the observed false claims are mostly capability/limitation specifics, and positive claims
   mislead more). Agree?
3. **Tell the maintainers?** One neutral sentence in the PR body ("N statements in Scope and Limitations
   are kept exactly as written; we could not check them against the code") closes the loop with the
   only authoritative owner. Is a PR body "public attribution" in your sense? If no, skip it.
4. **Does a merge or approval upgrade a statement?** My recommendation: no, never.
5. **Who may change memory?** Owner-only retire or annotate; no force-add under any circumstance. OK?
6. **Cap and ratio.** I propose an advisory above 40 admitted statements per repository or above ~20% of
   visible lines. Your number?
7. **Retention.** Keep statement text while ACTIVE, hash only after removal upstream. OK?
8. **What counts toward `authorizable_candidates`?** By TC-LIV-03 ("not worse than live") a candidate
   whose only unverified content is kept maintainer text is authorizable. Confirm that an independent
   acceptance reviewer should sample-probe these statements but not fail the candidate for
   COULD_NOT_VERIFY ones.
9. **Contradicted statements.** The standard (DEF-06) says correct the sentence to what the code does
   with a quoted line; the regeneration lane has `CORRECT_WITH_EVIDENCE` but no claim auditor. Until one
   exists, do you want a contradicted maintainer sentence omitted and an issue drafted, or kept and
   flagged?
10. **Slot and cut.** Which item yields the shared-code slot, and is Stage 1+2 in cut 6 acceptable
    given the version-bump treadmill measured in investigation 13?

---------------------------------------------------------------------------------------------------

## 11. What I did not verify

- I ran no pipeline stage and no test; behaviour is read from source at origin/main `7299f628`.
- The 3D-TypeScript and PDF-.NET wave 6/7 bundles are not committed (they live under `G:\rp-w7` and
  `runs/`); their evidence comes from the scratchpad triage and acceptance files.
- The counts in section 1 come from the working-tree bundles at `460607fa`, not origin/main.
- Hours are judgement. The 40-item and 600-character bounds, the 0.8 similarity and the 20% ratio are
  proposals to be measured on the 29 bundles before they become constants.
- I did not check `tests/` that enumerate the children of `candidates/<slug>/`, nor
  `tests/test_sealed_bytes.py` expectations after a placement exemption.
- Whether `ops/proposal-authorizations/` is absent because nothing was ever authorized, or because
  records are kept elsewhere, was inferred from the empty `ops/` tree and the owner's "hold all writes".

---------------------------------------------------------------------------------------------------

## 12. Evidence index (origin/main 7299f628)

- Authorities: `AGENTS.md` L135-143 (README content is evidence not truth; preserve uncertainty);
  `plans/idea.md` L110, L338-346, L470; `docs/README_STANDARD.md` PRC-03 (:114), PRC-05 (:116), STR-16
  (:424), DEF-06 (:817), 5.1 row 4 (:785), 5.3 (:852), 6.2 item 6 (:968), item 13 (:975);
  `docs/README_CONTRACT.md` 3 (S1-S12, kept units, placement exclusivity), 5 (BC rows), 7;
  `docs/STATE_MACHINE.md` 9; `docs/investigations/13-bump-cost-and-recheck-design.md` 6.
- Prompts: `prompts/source_reconciliation.yaml:103`; `prompts/repository_investigation.yaml:113-116`;
  `prompts/presentation_planning.yaml:201`; `prompts/independent_review.yaml` (v14, packet `dispositions`).
- Code: `reconciliation/dispositions.py` :216-225 (enum), :2416 (`placement_errors`), :2571-2582 and
  :2753 (recovery); `validation/deferrals.py` :538 (`_no_evidence`), :725 (class), :869 (`ESCALATIONS`);
  `validation/registry.py` :1422 (BC-05), :2368 (`advisory_notes`); `review/independent/review.py`
  :335, :531-545, :604, :1910, :2557, :2631, :2645; `composition/placement.py` :98, :633;
  `composition/planning.py` :479; `composition/source_topics.py` :56; `evidence/facts/inherited.py`
  (ordinal ids, `INHERITED_UNITS_VERSION` :111); `bundle/seal.py` :142, :361, :384;
  `bundle/evaluation.py` :105-110; `bundle/invalidation.py` :136, :152, :177;
  `bundle/recheck.py` (scopes); `cli.py` :4322, :4378; `core/candidates.py` :44, :220, :264;
  `core/git_safety/clone.py` :123; `candidates_publish/git_ops.py` :108, `effect.py` :182;
  `components/propose/pull_request.py` :13; `components/readme_correction/__init__.py`, `model.py`
  (`Finding`); `readme_correction/send.py` (`load_holds`, strict-loader precedent).
- Scratchpad: `wave6-triage.md` (DECISION NEEDED, options A-C, W6-5), `wave7-triage.md` rows 9, 36, 42,
  `acc-w7-pdf-net.md` (claim rows 23-29, dropped limitations), `acc-w7-3d-net.md` (B2, F5),
  `acc-w7-3d-java.md` (rows 11, 13), `acc-w7-cells-go.md` (F2), `acc-w3-3d-typescript.md` (F2, B4).
