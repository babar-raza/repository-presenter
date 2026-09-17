# Investigation 06: The Words-.NET redraw pattern

Status: investigation only, no implementation, no redraw attempted by this session. Written
2026-09-17. Commissioned directly by the owner after `aspose-words-foss/Aspose.Words-FOSS-for-.NET`
was drawn at least three times this session (`words-net/LANE-F-02`, `words-net/LANE-F-03`, and
`wnet/LANE-F-05` in progress as this was written) and hit a new, different blocker on almost every
draw. Question asked: is this a deeper, systemic problem with this one repository, or an
unusually large/complex repository that legitimately needs more iteration than others?

**Update, same day, while this document was being pushed:** `wnet/LANE-F-05` (PR #107, commit
`f82dc90`) landed on `origin/main` mid-write. It confirms this document's central prediction
directly rather than merely by inference: item 89's fix is a live ancestor of `main` and closes
its class on this repository outright (zero NuGet/badge failures, BC-02 clean); BC-06 still FAILS
with exactly one failure, causal stage EXTRACTING, textually identical to the original
measurement — `inherited_unit:068.paragraph` (`VERIFIED_PRESERVE`, `scope_limitations`) still
embeds the CONTRADICTED `link_target:020` (`../../issues`) next to a SUPPORTED absolute link,
independently corroborating item 90's own diagnosis rather than assuming it. No new, fourth
blocker surfaced on this particular redraw — the repository stays `BLOCKED_VALIDATION (BC-06)` on
item 90 alone, for now. §5's estimate of "at least one more redraw needed even after item 90 lands"
stands: this redraw used up the "confirm 89, corroborate 90" cycle without yet testing what lies
past BC-06 (S10 review, the no-op proof) — see §4's reasoning, which this event does not change.

Primary evidence: `docs/DECISION_LOG.md` §31 entries (2026-09-16, words-net/LANE-F-02 and
words-net/LANE-F-03), `docs/RESEARCH_LANE_F.md` (the whole `LANE-F-01` .NET-cohort narrative,
sections F1-F29), `git log`/`gh pr list` against `origin/main`, and the current source tree
(`src/repository_presenter/components/readme/reconciliation/dispositions.py`,
`.../validation/registry.py`). Before writing anything, `git fetch origin main` and `git worktree
list` were used to confirm no new commit had landed and that `wnet/LANE-F-05`'s own worktree
(`C:/w/wnet3`) was clean and idle at the time of writing — no redraw was in flight to duplicate or
interrupt.

## 1. The timeline, run by run

| When (UTC) | Run | Stage reached | What blocked it | Cause |
|---|---|---|---|---|
| 2026-09-16 14:26 | `words-net/LANE-F-02` (PR #71) | S5 `presentation_planning` | Run aborts closed at exactly 6,000 completion tokens, `TruncatedOutput`, no retry. | **Arrival item 85** (with item 77): `presentation_planning`'s `material_limitations`/`links`/`deviations`/`additional_example_ids` outer arrays, and `material_limitations.unit_ids`, had no `maxItems`/enum bound at all. First repository in the portfolio big enough to hit the ceiling before hitting any content limit. |
| — | fix lands | — | — | Commit `23485bf`, **2026-09-16 15:35 UTC** (`20:35:32 +0500`), landed ~70 minutes after LANE-F-02's PR merged. |
| 2026-09-16 16:52 | `words-net/LANE-F-03` (PR #76) | S9 `validation` (BC-06), **for the first time ever on this repository** | Two *independent* BC-06 failures found in the same run. | **Arrival items 89 and 90**, admitted together (commit `a0baf05`) from this one run: <br>89 — `_renderer_owned` special-cased `pypi.org`/`github.com` link exemptions but never NuGet's registry page, so the .NET version badge's href had never actually been verified for *any* NuGet-based .NET candidate — PDF/3D/Cells-.NET had only ever passed "by coincidence" (their own upstream READMEs already carried the scraped badge URL as a fact; Words' upstream README did not, because it predates the package's NuGet listing). <br>90 — a `VERIFIED_PRESERVE` disposition renders its unit's raw markdown verbatim, embedded links included, with no check of those links' own `link_target` facts — so a CONTRADICTED link already known to `dispositions.py` can still reach the sealed README inside an otherwise-true preserved paragraph. |
| — | item 89 fix lands | — | — | Commit `e184973`, `2026-09-17 10:07:48 +0500` — `_renderer_owned` now reads a registry's click-through target generically off `EcosystemSpec.badge`. |
| — | item 90 | — | **Still open** | No landing commit found anywhere in `origin/main`'s history (checked by commit-message grep, `-S` content search on `VERIFIED_PRESERVE`/"embedded link", and a direct read of the current `dispositions.py`/`review` code paths). Admitted alongside item 89 in the same commit, but only 89 has landed. |
| now | `wnet/LANE-F-05` | not yet drawn | — | Branch cut from `origin/main` at `47735e2`; worktree `C:/w/wnet3` clean, zero commits ahead of main at the time of this investigation. This is very likely the run the owner means by "in progress right now" — it has not yet produced a finding. **Not touched by this investigation.** |

Two corrections to the framing in the task prompt, found while building this table: item 85's own
commit message covers items 77 *and* 85 together (77 was Email-.NET's version of the same
`unit_ids`-enum gap; 85 extended it to the four unbounded outer arrays and is Words-.NET's own
citation). And items 89 and 90 were **not** found on two separate draws — they were both found in
the *same* `LANE-F-03` run, the first time this repository ever reached S9. So the accurate count
is: **two real draws so far** (LANE-F-02, LANE-F-03), not three — the third is in progress and has
not reported a finding yet.

## 2. Scale, measured, against the repositories that did seal

| Repository | Total facts | `public_symbol` facts | Outcome | Runs/attempts to seal |
|---|---|---|---|---|
| Note-Python (cross-ecosystem control) | 352 | — | Sealed | 1 fix (item 104), 1 draw |
| Email-.NET | 341 | — | Sealed | Cohort's cleanest repo; still needed 3 runs across the lane before its own review-stage blocker (F18/F22) cleared |
| Slides-.NET | 2,734 | — | **Not yet sealed** | 5 runs so far (F16, F28/F29 — a second, sibling placement gap found on run 5) |
| 3D-.NET | — | 3,812 | Sealed, no-op proven | 3 runs (`LANE-F-01`, `-R2`, `-R3`) |
| **Words-.NET** | 6,790 | 6,638 | **Not yet sealed** | 2 draws so far + 1 in progress |
| PDF-.NET | 12,580 | 12,270 | Sealed, no-op proven | 1 full composition attempt (after 4 lane-runs' worth of *other* repositories being drawn first) |

The portfolio's largest S5 surface claim (item 85's own text) is accurate **as of the moment it was
measured** — Words-.NET had the largest fact count of any repository that had reached a live
`presentation_planning` call *so far*. It is not the largest surface in the .NET cohort overall:
PDF-.NET is very nearly double Words-.NET's size (12,270 vs 6,638 public symbols) and sealed
**without ever hitting the S5 array-truncation bug at all** — its own composition attempt ran
before item 85 landed (13:00-13:47 UTC vs the fix at 15:35 UTC) and its `presentation_planning`
call never truncated.

That is an important, non-obvious nuance: **raw symbol count is a strong correlate of hitting these
bugs, but not the direct trigger.** The trigger is how many *distinct entries* a specific
repository's content causes the model to want to write into an unbounded array
(`links`, `deviations`, `material_limitations.unit_ids`, and — separately, still unfixed — a
disposition's own `fact_ids` list at S4, see §4 below), which is a property of the repository's
actual README/API content shape, not of its symbol count alone. Words-.NET was the first
repository whose *plan* tried to write enough distinct citations into those fields to hit the
fixed 6,000-token ceiling; it happened to be reached (drawn) before the even-bigger PDF-.NET was.
Being big made it likely; the lane's own draw order decided which large repository would be first
to actually trip it.

## 3. Is this repository special, or a general defect surfacing here first?

Read the actual PROPOSAL text for all three defects, not just the headline:

- **Item 85** (`presentation_planning` unbounded arrays): a schema-level omission in shared code
  (`prompts/presentation_planning.yaml`, `composition/planning.py`) that applies to *every*
  repository processed by this stage — Words-.NET is simply the first one whose plan output was
  large enough to exceed the fixed token budget before hitting any content limit.
- **Item 89** (NuGet badge unverified): the decision-log entry says outright that "the badge has
  passed BC-06 by coincidence three times running, not by a real guarantee" for PDF/3D/Cells-.NET —
  i.e. this defect was **already live and already a false pass** for every sealed NuGet-based .NET
  candidate before Words-.NET; Words-.NET is simply the first repository whose own upstream README
  did not carry the badge URL as a pre-scraped fact (its README predates the package's own NuGet
  listing), so it is the first repository for which the coincidence didn't cover for the gap. The
  same entry names the identical gap as "latent" for Go, Rust and TypeScript too — the fix (landed,
  item 89) explicitly reads the registry link generically off `EcosystemSpec` rather than adding a
  fourth per-host carve-out, precisely because it is a portfolio-wide gap, not a Words-.NET-specific
  one.
- **Item 90** (`VERIFIED_PRESERVE` embedded links unchecked): the PROPOSAL text is explicit that
  this is a `RECONCILING`-stage (S4) gap in shared disposition logic — any repository whose upstream
  README has a preserved paragraph containing a link that `dispositions.py` already knows is
  CONTRADICTED would hit this. Nothing about the finding is Words-.NET-repository-specific; Words'
  upstream content simply happens to contain such a paragraph.

**None of the three confirmed blockers are a defect in the Words-.NET *repository itself*** (its
upstream README, manifest, or package metadata). All three are gaps in this codebase's own shared
composition/validation logic that any sufficiently large, sufficiently old, or sufficiently
link-rich .NET repository could have surfaced. Words-.NET is the unlucky/lucky combination of
"large enough to be drawn early at scale" + "old enough README to lack the NuGet badge fact" +
"content shaped in a way that exercises a preserved-link path." Every fix genuinely helps the whole
portfolio, exactly as the decision-log's own "Cost and unlocks" sections state for each item.

## 4. Is there a fourth blocker already sitting there, undiscovered only because no one has reached it yet?

Yes — and it is not speculation, it is already measured and written down, just not yet connected
to Words-.NET.

`docs/RESEARCH_LANE_F.md` §F27 (PDF-.NET run 4, 2026-09-16): `source_reconciliation`'s own
`fact_ids` array (`reconciliation/dispositions.py`, S4 — a stage *earlier* in the pipeline than
`presentation_planning`) still has no `maxItems`, structurally the same shape as item 85's own
defect one stage earlier. It was measured live: on PDF-.NET's own S4 batch 3 of 6, one call
returned exactly 32,000 completion tokens (`source_reconciliation`'s own ceiling) and truncated;
21 minutes later, an identical-digest retry (same `request_sha256`, same `prompt_tokens`) returned
3,016 tokens and completed cleanly. **PDF-.NET sealed only because the retry got lucky.** Read
directly against the current tree, this is still true today:

```python
# src/repository_presenter/components/readme/reconciliation/dispositions.py:238-247
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

The `items.enum` bounds *which* fact IDs a disposition may cite, but nothing bounds *how many* it
may cite in one array. This is the exact same class item 85 fixed for S5 — an unbounded array under
a fixed, no-retry token budget — one pipeline stage earlier, in a different job, and it is
confirmed **not yet fixed** anywhere in the current codebase. Words-.NET's own S4 call passed
cleanly on both real draws so far (LANE-F-02's own evidence: "S3/S4 succeed, 4 calls, all HTTP
200"), so this specific bug has not yet bitten Words-.NET — but the decision log separately records
(§I in the sibling autonomy investigation, and directly in F24/F27) that the *same* request digest
at `temperature 0, seed 1` has now been observed to return two very different completion-token
counts on two different jobs, on two different repositories, on two separate occasions. That is a
measured nondeterminism, not merely a theoretical risk: a clean S4 pass on one draw is not a
guarantee of a clean S4 pass on the next one.

So the honest answer to "is there a way to estimate how many more blockers are hidden": yes, at
least one specific, already-diagnosed, already-proposed, not-yet-landed defect (F27) sits directly
in Words-.NET's own execution path and has already caused one near-miss on a bigger sibling
repository. Beyond that, the rate observed so far is not "one new blocker per redraw" — it's closer
to "the first time a repository reaches a not-yet-fully-exercised pipeline stage at real scale, that
stage tends to reveal more than one latent defect at once" (LANE-F-03 found two BC-06 defects
simultaneously, the moment S9 was reached for the first time). Words-.NET has, across its two real
draws, only ever reached as far as S9/BC-06. It has **never yet reached S10 (independent review) or
the S11 no-op proof at its own real scale** — and every other large .NET repository in this cohort
that got that far found something new there too: PDF-.NET's own BC-07 pass was "the first .NET
repository in this lane to clear [it] against a real 34-of-899 collision rate" only on its fourth
lane-run; Slides-.NET found a *second*, sibling placement gap on its fifth run, after its first
placement gap had already been fixed. Given that pattern, it would be a genuine surprise, not an
exception, if Words-.NET cleared S10 and the no-op proof on the very first attempt once item 90
lands.

## 5. Honest recommendation

**Do not expect Words-.NET to seal immediately once item 90 lands.** Expect at least one more
redraw to be needed, and treat two as the realistic middle case, for two concrete, evidenced
reasons rather than a vague "big repos take longer": (1) F27's own defect is real, already
diagnosed, sits earlier in Words-.NET's own pipeline than anything fixed so far, and has already
caused one near-miss on a bigger sibling; it has not been ruled out for Words-.NET, only not yet
observed, and the provider-side nondeterminism means a past clean pass doesn't guarantee a future
one. (2) S10 review and the S11 no-op proof have never been exercised on this repository at its
real scale, and every comparable large .NET repository that reached those stages found something
new there.

This is not a reason to treat Words-.NET as broken or cursed — it is the largest-scale repository
being pushed furthest through a pipeline whose shared-code array-bounding work is still, visibly,
in progress (item 85 fixed S5's version of this bug; F27 shows S4's sibling version is still open).
Every other large repository in this cohort (PDF-.NET, Slides-.NET) needed 3-5 lane-runs and found
more than one new defect along the way; Words-.NET is currently at draw 3, which is squarely inside
that same range, not an outlier within the cohort. The owner's frustration at seeing it "loop in and
out" is legitimate as an experience — but it is the correct, working operation of the arrival-item
mechanism (find one real defect per stage reached, land it, redraw), not evidence that something is
wrong with either the mechanism or the repository.

**One concrete process gap, found while building the timeline, worth flagging on its own:** item 90
was admitted in the same commit as item 89 (`a0baf05`, 2026-09-16 ~17:31 UTC) and the project's own
stated rule is to land arrival items "in arrival order," with every item either landed-with-test or
declined-with-a-reason in §31. Item 89 landed the next morning; items 91 through at least 119 (from
other lanes' unrelated repositories) have since landed; item 90 has neither landed nor been
declined anywhere in the log. It has not sat open unusually long in absolute terms (under a day),
but it has been passed over by more than two dozen later-numbered items, with no recorded reason.
Whether that is a deliberate deprioritization (item 90's own fix is more invasive — it needs
`RECONCILING`'s disposition step to gain real link-checking logic, not a one-line schema bound like
item 89) or simply an oversight in an arrival-order rule that has many hands landing items
concurrently, the owner may want to have someone confirm which, since the rule as written does not
currently have a "this one's harder, deliberately deferred" escape valve distinct from silence.

**A more efficient way to attack this specific repository exists, and is worth doing before the
next real redraw:** the current pattern is one fix landed, one lane-redraw spent to discover the
*next* blocker, repeat — each redraw costs a full composition run (dozens of provider calls,
20-40+ minutes) just to re-confirm stages that already passed and surface one more thing. Given
that F27's fix is already fully diagnosed and specified (a `maxItems` on `fact_ids` sized from the
batch's own measured ceiling, "beside the existing `.items` assignment," per the PROPOSAL's own
text) and item 90's shape is already scoped (check a preserved unit's embedded links against their
`link_target` facts at RECONCILING), landing **both** before the next words-net draw — rather than
waiting for the draw to prove item 90 alone was sufficient and only then separately discovering
F27 on some future run — tests both fixes in one pass instead of two. More generally: before
spending the next real redraw's provider-call budget, a cheap, zero-cost dry run against Words-.NET's
already-cached facts (facts-only preflight, no provider calls, as LANE-F-02/F12 already did) with
every currently-admitted-but-unlanded proposal for this repository's own code paths applied locally
in a throwaway worktree would surface whether the *next* stage (S10 review) has its own already-
known-elsewhere defects waiting, before committing a real draw's cost to finding out one at a time.
