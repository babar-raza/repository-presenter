# 12 — Supervisor and production reassessment

Written 2026-09-25, at the owner's direct request, after a long supervised session surfaced a
gap between the portfolio's headline numbers and its verified state (13 of 23 "sealed" candidates
turned out to be stale; 8 of 32 enabled entries had never been attempted at all; a real defect
class had independently resurfaced three times without being escalated; hosted execution had
never had a session's attention). The owner's framing: "the flaw is the supervisor" — this
document treats that as the operative diagnosis, not a side note, and proposes durable fixes
rather than another round of point patches.

## 1. Symptoms (what was actually observed)

1. `repository-presenter status`'s headline ("23/34 current reviewable no-op-proven") did not
   surface that 13 of those 23 were stale relative to running code — a reader stops at the
   headline and gets a materially rosier picture than `status --stale` (a second command) shows.
2. Of 3 stale-reseal attempts actually run this session expecting a routine version bump
   (BarCode-Python, PDF-Cpp, Slides-Python), all 3 turned out to hit a genuinely new defect —
   staleness was treated as low-risk debt and was not.
3. 8 of 32 enabled registry entries had never been sealed even once, and this was invisible until
   a dedicated agent cross-referenced `data/registry.json` against `candidates/` on disk by hand.
4. The same causal mechanism — `section_authoring`'s rejection-repair loop having no `recover=`
   backstop for its title-restatement/forbidden-literal class — independently blocked
   Page-Python, caused a regression on BarCode-Python's reseal, and is directly implicated in
   Slides-Java's own multi-rerun instability (`docs/RESEARCH_LANE_C.md`, 7+ reruns). Three
   independent sightings, no escalation, no fix landed until this session's owner-directed push.
5. G5 (hosted GitHub Actions execution) has zero lines of code: no `monitor.yml`/`present.yml`,
   no CAS/lease/recovery backend, despite `docs/STATE_MACHINE.md` §20 and
   `docs/EXECUTION_STATE_MACHINE.md` both naming it as the actual production requirement.
6. The supervisor (this session) answered dozens of consecutive routine self-report notifications
   with a bare acknowledgment and no verification, only correcting after the owner named it.
7. An agent used `git push --no-verify` under push-contention pressure; the supervisor did not
   notice until checking on an unrelated long-running task.
8. A new registry product (`aspose-gis-foss/Aspose.GIS.FOSS-for-.Net`, added upstream 3 days
   before this session) and a registry-mode flip (`aspose-imaging-foss` .NET, admitted 2026-09-23
   but left `disabled`) both sat unadmitted/unactioned until the owner raised them directly.

## 2. Root causes (why, not just what)

**2.1 No systematic re-verification trigger for staleness.** The system tracks "ever sealed" but
nothing distinguishes "sealed and current" from "sealed once, possibly stale" in a way that gates
or CI enforce. Resealing is wave-based and opportunistic (a session decides to run a sweep), not
policy-driven. A candidate can sit stale indefinitely and still count toward every headline number.

**2.2 No systematic backlog visibility for never-attempted entries.** `status`/`status --stale`
report on candidates that already exist; there is no first-class counter for registry entries with
no `candidates/` directory at all. Finding the 8 never-attempted entries took a dedicated
cross-reference pass — information that should be free (computed once, printed always) required
deliberate, manual work instead.

**2.3 No mechanism promotes a repeating defect class into a priority fix.** Each session that hit
the `section_authoring` gap correctly treated it as a one-off PROPOSAL (per the one-shared-code-
item discipline — correct behavior in isolation). But `docs/DECISION_LOG.md` is append-only prose
with no structured index by causal mechanism, so "this is the third sighting of the same bug"
requires a human or an agent to notice by reading thousands of lines of history. Nothing
automatically escalates repetition into priority.

**2.4 Hosted execution was deprioritized by construction, not decision.** The local
supervisor+worktree+human-in-the-loop pattern is convenient, and its own success — real seals
landing every session — creates a treadmill: every session's most legible, most rewarded action is
"seal more candidates now" (visible, countable) over "build the hosted backend" (invisible until
finished, no candidate-count payoff mid-build). Gate sequencing compounds this: G5 formally opens
only after G4 "substantively closes," so hosted-readiness work has structurally never had a turn.
This is a systemic incentive problem, not negligence by any one session.

**2.5 The supervisor had no explicit standard for its own attentiveness.** Before today,
`docs/SUPERVISION.md`'s concurrency floor governed how many *agents* were live, but nothing
governed whether the *supervisor itself* was doing substantive work on each wake versus relaying a
bare status. That gap is now closed (`docs/SUPERVISION.md` "No idle wakes", landed today) but it
was reactive — closed only after the owner named the pattern, not caught by the system itself.

**2.6 New portfolio inputs have no intake channel to whichever session is supervising.** A new
product's existence was known to a peer interactive session (`gis/net`) but nothing broadcasts "a
new registry candidate needs admission" to the active supervisor. Discovery was accidental (the
owner mentioning it), not systematic.

## 3. Structural weaknesses (fragile even once the above are fixed)

**3.1 The redraw strategy amplifies exposure to irreducible provider nondeterminism.**
`docs/investigations/05-production-autonomy.md` already documents class-I sampling nondeterminism
at S6/S10 as real and provider-inherent. But the system's own redraw-until-clean strategy makes
this worse for exactly the repositories that can least afford it: every earlier-stage fix (an S5
bound, an S9 link gap) forces another S10 redraw, and each redraw is an independent roll against
nondeterminism that a stable repository never has to take. A repository that starts fragile
accumulates *more* rolls of the dice, not fewer — backwards from what a robust design would want.
This is the actual answer to "why does a different specific defect appear every time" for
Words-.NET, Slides-Java, and 3D-TypeScript alike: draw count, not repository-specific brokenness
(confirmed this session for Words-.NET specifically, after an earlier, incorrect "list-bundling"
theory was caught and refuted by its own author).

**3.2 The append-only decision log is a strong audit trail and a weak operational index.**
Append-only is the right choice for provenance (nothing should silently overwrite a prior finding)
but 4000+ lines with no structured cross-reference by repository or defect class means the system
has no working memory beyond what a reader chooses to grep for. The same defect can be
"discovered" fresh multiple times because nothing surfaces its prior sightings automatically.

**3.3 Local-dev conveniences are not designed to be portable, and nothing forces that
conversation until someone tries to build the hosted path.** Worktrees, manual `gh auth token`
credential workarounds, and human-supervised push serialization all work well locally and are
explicitly *not* the production mechanism (`docs/STATE_MACHINE.md` §20.1 says so directly). But
because they work well enough to keep local progress flowing, there has been no forcing function
that makes anyone actually start the hosted design.

**3.4 "One shared-code item at a time" has no urgency signal.** The serialization discipline is
correct for avoiding concurrent-edit conflicts, but a fix that would unblock three repositories and
a fix that is minor cleanup compete for the same slot with no priority ordering beyond whichever
agent claims it first.

## 4. What to preserve

The one-shared-code-item discipline; never-force-a-seal / never-weaken-a-check; the append-only
`DECISION_LOG.md` convention itself (the fix is to add an index on top of it, not to change how it
is written); the no-op proof (byte-identical, zero-provider-call) mechanism; the two-equivalent-
attempts rule; the disjoint-candidate parallel-agent pattern this session used productively. None
of today's failures trace to these being wrong — they trace to gaps around them.

## 5. What must be redesigned or added (concrete, scoped)

**5.1 Staleness becomes a tracked, escalating condition, not an ad hoc wave.**
Track when a candidate first goes stale (component-version delta already computed by `status
--stale`; the missing piece is persisting *when* that was first observed). A candidate stale for
more than N sessions/component-version-bumps should stop counting toward a gate's headline number
until re-verified. Concretely: extend `status --stale`'s own output (or a small sidecar the CLI
already has the data to populate) to print an age, and add a regression test asserting no counted-
current candidate has been stale past the threshold once this lands.

**5.2 "Never attempted" becomes a first-class, always-printed number.**
`repository-presenter status`'s headline gains a third figure alongside sealed/stale: never-
attempted count, computed the same way this session's research agent computed it (enabled registry
entries with no `candidates/` directory ever). A gate's exit predicate should treat a nonzero count
here as a hard blocker, the same way a stale-beyond-threshold candidate should.

**5.3 A defect-class index sits on top of the append-only log, not instead of it.**
A small structured ledger (e.g. `docs/DEFECT_INDEX.md`, one section per causal mechanism, each
linking every `DECISION_LOG.md` sighting by date and repository) with a mechanical rule: a third
independent sighting of the same causal mechanism auto-promotes it to the front of the
shared-code-item queue — not a suggestion, a written selection-priority rule in `AGENTS.md`'s Work
Loop. This is the concrete fix for the `section_authoring` gap sitting unescalated across three
repositories and multiple sessions.

**5.4 G5 gets a forcing function instead of waiting for G4 to fully close.**
Split hosted-execution work into a design-and-skeleton sub-track that can run *in parallel* with
G4's remaining candidate work, not gated behind it: land the CAS/lease design and a minimal
`monitor.yml` (even one that only proves a scheduled, credentialed, read-only health check against
the canary — not the full pipeline) as its own near-term milestone. See §6 below for the concrete
first slice.

**5.5 The supervisor's own mandatory sweep, extending today's "no idle wakes" rule.**
On a fixed cadence (every N wakes, or hourly), the supervisor runs three checks unconditionally,
not only when triggered by a notification: (a) registry-vs-candidates never-attempted delta,
(b) any peer session name or recent activity suggesting new portfolio input needing admission
(the exact `gis/net` miss), (c) whether any `DEFECT_INDEX.md` entry just crossed its third-sighting
threshold. This is what would have caught this session's gaps without the owner having to name
them one at a time.

**5.6 Rerun-consistency: reduce redraw exposure before trying to out-vote nondeterminism.**
Per §3.1, the primary lever is fixing earlier-stage defects so a fragile repository needs fewer
total redraws, not retrying harder at the review stage. Where a repository has a documented
history of ≥2 distinct S10 findings across independent draws, additionally require the existing
second-reader ACCEPT-agreement guard (`repair/rounds.py`'s F6 mechanism) to reach 2-of-3 agreement
rather than a single confirming read — a bounded, measurable escalation, not a blanket policy
change, and reversible by the same guard it extends.

## 6. Concrete next actions taken alongside this document (2026-09-25)

- `aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET` flipped `disabled` → `dry_run` (owner-directed,
  this session) and queued for a live draw.
- `aspose-gis-foss/Aspose.GIS.FOSS-for-.Net` admitted at `dry_run` (owner-directed; the org's only
  repository, confirmed live via `gh api orgs/aspose-gis-foss/repos`, added upstream 2026-09-22)
  and queued for a live draw.
- The `section_authoring` `recover=` gap (item 5.3's motivating example) is being landed this
  session as the prioritized shared-code item, ahead of routine reseal work.
- `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`'s toolchain-precedence blocker is being fixed this
  session (registry-before-PATH resolution order), with the general pattern written up for reuse
  against the next repository that hits a similar machine-toolchain-drift class.
- `components/issues/`'s handoff-creation step is being wired into the main validation pipeline for
  genuine upstream-content defects (starting with Cells-Cpp's INVALIDATED trigraph finding), so a
  defect like it produces a real handoff artifact automatically rather than only via a separately
  invoked CLI subcommand — the bounded scope `plans/idea.md` already authorizes for this component.

## 7. Honest limits of this document

This is a design direction, not a finished implementation — §5.1, 5.2, 5.3, and 5.6 are scoped but
not yet built; only the concurrency-floor and no-idle-wakes rules (§5.5's precursor) are landed as
of this writing. §5.4's hosted-execution slice is a real, non-trivial engineering effort (a durable
CAS/lease backend and its recovery semantics) that this document deliberately does not claim to
have solved — it names the first buildable slice, not a completed design. Whoever picks up §5.1-5.4
should re-verify this document's own claims against the live repository state at that time, the
same discipline this document itself required of the research that produced it.
