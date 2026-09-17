# Investigation 05: Full Production Autonomy

Status: investigation only, no implementation. Written 2026-09-17 per
`docs/PRODUCTION_ROADMAP.md` workstream 5 ("Full production autonomy — the system runs without
routine human intervention"). Authority: `plans/idea.md`'s "Production-Readiness Standard" and
"Operating Model" sections govern what "autonomous" means here; nothing in this document
overrides them. Primary evidence source: this sprint's own `docs/DECISION_LOG.md` §31 entries
from 2026-09-16 and 2026-09-17, cross-checked against `docs/SUPERVISION.md`,
`tools/reviewer/procedure.md`, `.github/workflows/liveness.yml`, and `.githooks/pre-push`.

This is real operational history, not a theoretical hazard list: every failure class below is
named with the exact log entry (or entries) it comes from, and counts are honest, approximate
tallies from one read-through, not a claim of completeness.

## 1. Failure-class inventory (2026-09-16 / 2026-09-17, with older founding incidents noted where they are the direct ancestor of a rule still load-bearing today)

| # | Failure class | Where measured | Rough count this session |
|---|---|---|---|
| A | **Push race under concurrent commits to one shared checkout.** A push is built against a tree that a second concurrent agent edits mid-run; the pre-push hook (`.githooks/pre-push`, which runs the full local CI-equivalent against the *live working tree*, not the commit) or CI sees a stale cached import versus a freshly-written file and fails spuriously (`test_extraction_agrees_with_the_running_constants` twice by name). | `docs/DECISION_LOG.md` 2026-09-11 17:36/17:58 UTC (items 59/65, the entry that also caused failure class D below); 2026-09-17 entry at line 3457 (items 71/91, "one push attempt raced a concurrent commit's own working-tree edit mid-run... failed spuriously; re-verified clean on a settled tree"). | 3 distinct sightings across the sprint; 1 squarely inside the 09-16/17 window. |
| B | **An unscoped `git stash` sweeps multiple concurrent agents' uncommitted work into one entry.** A bare `git stash` (not scoped to one path) silently removed one session's uncommitted changes together with unrelated concurrent agents' WIP on `prompts/targeted_repair.yaml`, `composition/placement.py`, `repair/targeted.py`, `test_placement.py`. Recovered by hand: `git show stash@{0}:<path>` for exactly the affected session's own files, written back without touching the stash entry or any path the session doesn't own. | `docs/DECISION_LOG.md` 2026-09-16 (line 3135, "Working-condition note"). | 1 near-miss incident, requiring manual surgical recovery. |
| B′ | **The mitigation for B in continuous use**: agents scope every stash to `git stash push -- <file>`, verify red/green in isolation, then restore — explicitly never a bare `git stash`/`git stash pop`, and explicitly leaving a concurrent session's own unrelated stashed work untouched. | Same log, repeated verification-section boilerplate at (at least) lines 3287, 3311, 3317, 3324, 3360, 3432, 3439, 3457. | ~8 disciplined uses in the 09-16/17 window alone — i.e., every single verification in this window that touched a shared file had to actively defend against class B. |
| C | **File-ownership contention among concurrently live agents.** Two items (79 and 86) both needed to edit `repair/rounds.py`, which "the coordinator's own steer" had assigned to a different concurrently-running agent for the rest of the session. Both items landed only as inert/half-wired code (new function built and tested, but the one call site that activates it is left unedited) rather than a live fix, explicitly deferred to whichever session owns that file next. | `docs/DECISION_LOG.md` 2026-09-16 17:53 UTC (item 79, lines 3137-3143) and 18:31 UTC (item 86, lines 3144-3150). | 2 items blocked/half-landed this way in one afternoon. |
| D | **`git worktree remove --force` recursing through a `.venv` junction and gutting a shared checkout's virtual environment.** A push worktree junctioned `.venv` to the main checkout's; `git worktree remove --force` on the *dead* worktree removed the junction's *target* contents (`pyvenv.cfg`, `site-packages`) through the link, breaking the shared environment for every other live agent until rebuilt from the lock file. | `docs/DECISION_LOG.md` 2026-09-11 17:58 UTC (lines 3046-3049) — one incident, but its working-practice fix ("unlink the junction first, then `git worktree remove`; never `--force` a worktree holding a junction") is exactly the rule every subsequent 09-16/17 push-worktree operation had to keep following, since nothing enforces it mechanically. This is the closest match in the whole log to the task's own example phrasing. | 1 incident, whose prevention is still convention-only through 09-17. |
| E | **`GIT_*` environment-variable leakage from a test hook/fixture into the live checkout.** `run_git` forwarded `os.environ` wholesale into throwaway test fixtures; `GIT_DIR` (exported by git into every hook's environment, and outranking both cwd and `-C`) redirected fixture commits onto two real lane branches and overwrote the checkout's committer identity, landing two mis-authored commits on `main`. | `docs/DECISION_LOG.md` 2026-09-11 13:52 +05:00 (three consecutive entries: the leak itself, the two corrupted-authorship commits left as a permanent record rather than rewritten, and a `core.bare`-verification probe after the fix). | 1 major incident; fixed deterministically (see §2) and never recurred in the 09-16/17 window. |
| F | **The dead-man's own scheduler going silent under load.** GitHub's `schedule:` cron trigger for `liveness.yml` was observed to go quiet for 3h54m under heavy Actions traffic (dozens of CI/mirror runs per hour) despite the workflow being active and unmodified — a documented GitHub behavior, not a bug in this repo's YAML. | `.github/workflows/liveness.yml` header comment (dated to the PHASE1 era, the direct ancestor of the concurrency load this sprint has sustained). | 1 documented incident; mitigated by adding a second, `workflow_run`-chained trigger off CI completion. |
| G | **A lane-liveness field with no expiry reads as "live" forever.** `reviewer_state.json`'s `lanes.<lane>.live_run` is a bare timestamp; after a session/machine restart it kept reading as "live" indefinitely, so the newly-landed F13 concurrency-floor check reported `active roles 6/4` (floor "met") when real live capacity was `1/4` — exactly the "idle gaps to 9h" failure mode F13 was built to catch, reproduced by the very mechanism meant to fix it. | `docs/DECISION_LOG.md` 2026-09-17 (PHASE1/F13 landing at 02:42 UTC, and its same-day follow-up fix requiring PR corroboration, lines 3393-3406). | 1 incident, caught and fixed same day. |
| H | **Written findings sit unadmitted to the shared work queue for days, with no mechanical sweep.** Three lane-E findings (E4, E8, E13) were correctly recorded as PROPOSALs in `docs/RESEARCH_LANE_E.md` on 2026-09-11 but did not reach the shared arrival list (`RESEARCH_AND_GUIDELINES.md` §29) until this session's 09-16 admission pass — five days later — because nothing sweeps the per-lane research logs on a schedule; admission depended entirely on a lane happening to restate an open finding in a report a live supervisor happened to read. | `docs/DECISION_LOG.md` 2026-09-16 12:45 UTC (lines 3158-3162, explicitly named "a real supervision gap"). | 1 documented gap, covering 3 findings held 5 days; flagged for a future fix, not yet built. |
| I | **LLM provider-side output nondeterminism at `temperature: 0`, `seed: 1`.** The identical request digest (`request_sha256`) returned three different completions on one job and, independently, two different completions on a different job — contradicting the standing `seed_support: deterministic: true` assumption several checks and caching decisions lean on. Both times a same-digest retry happened to recover cleanly; neither has been root-caused. | `docs/DECISION_LOG.md` 2026-09-16 12:29 UTC and 14:23 UTC (lines 3152-3168); precedent already on record 2026-09-11 13:52 +05:00 ("the recorded seed_support claim is narrower than it reads"). | 2 corroborating sightings this window, on two different jobs and two different repositories; flagged, not fixed, not blocking (both self-recovered). |
| J | **A loop/lane session ends its turn believing a background signal will wake it, when the harness will not deliver one on its own.** `docs/SUPERVISION.md`'s "Wakeup policy" section and `tools/reviewer/procedure.md`'s correction-ladder "Stopped / stalled" row exist specifically because of this pattern ("five recorded occurrences, all recovered" as of 2026-09-11; the standing rule is that a missed self-wake must be independently detectable and the monitor's re-arm message is "standing procedure," not an exception). | `docs/SUPERVISION.md` "Wakeup policy" (lines 117-124); `tools/reviewer/procedure.md` §2 correction-ladder, "Stopped (stop:true) / capped / stalled" row. | Named as a recurring, previously-measured class in the architecture's own design rationale; I found no fresh line-by-line 09-16/17 log citation for a *new* instance distinct from A–I above — flagged here because the mechanism that exists to catch it (`stop_monitor.py`) is a permanent fixture of every wake, which is itself evidence the class is expected to keep recurring, not evidence it recurred again this window. Treat this row's count as "mechanism kept active," not "N new incidents," pending direct confirmation. |

## 2. Automatable vs judgment-call, per class

The task's own framing is the right test: could a deterministic script or rule have prevented
this *entirely*, or does it inherently need an agent/human to weigh something? Being honest about
which is which is more useful than claiming everything is fixable in code.

- **A (push races) — automatable, not yet automated.** The log itself names the mechanism twice:
  "the pre-push hook judges the live working tree... two agents in one checkout make that race
  structural." A deterministic fetch→rebase/merge→retry wrapper, or (better) simply never running
  two write-capable agents against the *same* checkout, removes this without any judgment call.
  No wrapper exists in `tools/` today — `git log`/`find` confirm nothing like it has been built.
- **B / B′ (unscoped stash) — automatable by prohibition.** "Never bare `git stash` / `git stash
  pop`; always scope, always capture and verify" is already a hard rule this session's own
  environment carries and that a past session recorded independently in personal memory
  (`concurrent-owner-session-in-same-checkout.md`). Prevention is a pure discipline rule with zero
  judgment content — the discipline itself could be enforced by a wrapper script that refuses a
  bare `git stash` invocation outright. What remains judgment-requiring is *recovery* after a
  violation (which stash entries belong to which agent) — but that only exists because prevention
  isn't yet mechanically enforced.
- **C (file-ownership contention) — partially automatable.** *Detecting* a collision (two live
  agents about to touch the same shared-code path) is mechanical: a small claims registry each
  agent checks before editing a governed file would catch this deterministically. *Deciding* who
  gets the file, in what order, and whether a change should land wired-live or inert-until-wired
  is a judgment call about priority and risk that a lock file cannot make on its own.
- **D (`.venv` junction / `git worktree remove --force`) — fully automatable.** The exact rule is
  already known and written down ("unlink the junction target first, then `git worktree remove`;
  never `--force` a worktree holding a junction"). This is precisely the kind of fix the task
  names as its own example: a thin wrapper around `git worktree remove` that checks for and
  unlinks a `.venv` junction first would prevent every future recurrence with no judgment call at
  all. It does not exist yet — the fix that landed was a repair, not a preventer.
- **E (`GIT_*` leakage) — already fixed deterministically, and it stuck.** `run_git`
  (`src/repository_presenter/core/git_safety/git.py`) now scrubs `GIT_DIR`/`GIT_WORK_TREE`/etc.
  from both `os.environ` and any caller-supplied `env`, `.githooks/pre-push` does the same as
  defence in depth, and `tests/core/git_safety/test_git.py` pins the behavior in CI. This is the
  one class in this table that is a completed proof of the task's own thesis: a real, damaging,
  concurrency-adjacent incident that a purely deterministic code change closed for good, with no
  residual judgment call.
- **F (dead-man cron silencing) — already mitigated deterministically.** A second,
  `workflow_run`-chained trigger removed the single point of failure without needing any human
  judgment; `schedule:` remains as a fallback for genuine silence.
- **G (stale `live_run`) — already fixed deterministically, same day.** Requiring PR corroboration
  before trusting a bare timestamp is a pure code fix with a clear acceptance test; no judgment
  call was needed once the mechanism (not just the symptom) was correctly diagnosed.
- **H (unadmitted PROPOSALs) — detection is automatable; admission is not.** A periodic grep of
  `docs/RESEARCH_LANE_*.md` for `PROPOSAL` headings not yet cross-referenced in §29 (explicitly
  named in the log as the shape of the fix, "the same shape as F1's unblock-ledger fix," but not
  yet built) would close the "sat unnoticed" failure mode mechanically. Whether a given PROPOSAL
  is *correct* and where it should be queued is unavoidably a judgment call requiring the same
  read-the-evidence reasoning a human or reviewing agent does today — a sweep can guarantee
  visibility, never guarantee correct disposition.
- **I (LLM sampling nondeterminism) — not automatable away; a genuine judgment/product-risk
  question.** This is inherent to the provider, not a bug in this codebase. Code can bound the
  *damage* (schema-pinned decode, cache reuse, fail-closed on a cap boundary — several G4-W17
  items already do exactly this) but cannot make the underlying completion deterministic. The
  honest answer here is that this is a standing operating condition to be accepted, monitored, and
  bounded, not eliminated.
- **J (false "wait for a notification") — mostly automatable, partly already automated.**
  Detection already exists and runs every wake (`stop_monitor.py`, the "stalled" row). What is
  *not* yet automated is the correction itself: today a human/supervisor session must notice the
  monitor's event and type the exact re-arm `SendMessage`. Since that message is a fixed template
  keyed off a fixed event class, this is one of the more clearly automatable-with-no-judgment-call
  items in this table — a scripted responder could send it as reliably as a human does, without
  waiting for a human to be awake and reading the transcript.

## 3. How far the current supervision architecture actually gets

`docs/SUPERVISION.md` plus `.github/workflows/liveness.yml` plus `tools/reviewer/procedure.md`
together are this project's real, working answer to "who watches the system when no one is
watching" — and they get further than a naive read of the task might expect.

**What it demonstrably handles without a human in real time:**

- **The dead-man is a genuine, session-independent backstop.** `.github/workflows/liveness.yml`
  runs on a GitHub Actions schedule (with a `workflow_run`-off-CI fallback added after class F's
  own near-failure), needs no chat session alive, and checks three concrete, evidence-backed
  conditions every run: any open PR older than 30 minutes with no `hold` label (the exact PR #29/
  #30 shape that sat unmerged for 3 days 18 hours in the founding incident), any remote branch
  ahead of `origin/main` and untouched for 12+ hours, and `origin/main` inactivity beyond 4 hours
  during a declared sprint. It is read-only by design ("no write permission, no repo mutation,
  ever") and "fails loudly on stranded artifacts" — this is real and running, not aspirational.
- **The concurrency floor (F13, landed and then hardened same-day, class G above) is a concrete,
  mechanically-checked rule**, not a prose aspiration: `reviewer_check.py`'s
  `concurrency_floor_flag` is a pure function with acceptance tests, wired into the existing
  hourly heartbeat, and its very first production reading exposed and led to fixing its own
  stale-liveness bug within the same day — a real example of the architecture catching a defect
  in itself.
- **Governance rules that must survive a dead supervisor already live in `tests/`, not just in
  prose** — `test_governance_consistency.py`, `test_queue_agreement.py`, `test_bundle_audits.py`
  run in CI on every push regardless of whether any chat session exists, per
  `docs/SUPERVISION.md`'s own explicit "Enforcement placement" rule ("A check that must survive
  the supervisor lives in `tests/`... or in `liveness.yml`... A check that reads a live session's
  transcript stays in `tools/reviewer/` and accepts that it is mortal").
- **The executor's own continuation is self-scheduled and self-detectable**, not dependent on the
  supervisor's liveness — `docs/SUPERVISION.md`'s "Wakeup policy" states this was a deliberate
  design correction after the opposite (externally-triggered continuation) was tried and reversed
  within a day, specifically because it "makes the executor's liveness depend on the supervisor's
  — the exact coupling that stranded the lanes."

**Where it still structurally assumes a human is watching and acting** — and this session's own
transcript, per the task's framing, is the direct evidence:

- **Detection and remediation are architecturally split, and only detection is automated.**
  `liveness.yml`'s own header comment says this plainly: "It DETECTS and fails loudly; it repairs
  nothing — recovery is a new supervisor session running `tools/reviewer/procedure.md` section 0."
  Every failure class in §1 above that got *fixed* (D, E, F, G) was fixed by an agent session
  narrating a decision that a human "reviews asynchronously" — never by a script reacting to the
  dead-man's own alert. There is no code path today in which a red `liveness.yml` run causes
  anything to happen other than a human noticing a red GitHub Actions run.
- **The correction ladder is a human-addressed channel by construction.** `procedure.md` §2's
  entire mechanism is "SendMessage to the loop session... at most one message per wake" — it
  assumes an interactive supervisor session exists to read `reviewer_check.py`'s flags and choose
  what to say. Nothing sends that message except a person (or an agent standing in for one) typing
  it after reading the report.
- **File-ownership coordination among concurrent agents (class C) is entirely session-memory-
  resident** — "the coordinator's own steer," not a durable, machine-readable claim any future
  session could read back. If the coordinating session ended mid-sprint, the next session would
  have no record of which file was whose.
- **Admission of proposed fixes into the work queue is a policy-level human gate, not merely an
  unautomated one** — §31's own rules state "proposals, not admissions... only the owner moves it
  into §27.9 or `state.yaml`." This is by design, not a gap to close — but it does mean a category
  of decisions is permanently routed to a human/owner ruling, which the operating model needs to
  count honestly rather than assume away.
- **This sprint ran with several concurrently live, human/supervisor-coordinated agents sharing
  one physical checkout** (the repeated stash-scoping discipline in §1's class B′ only exists
  because of this), which is itself a topology choice a human is actively managing turn by turn,
  not a self-organizing property of the system.

## 4. Bounded/acceptable vs hard blocker (my own judgment)

`plans/idea.md` explicitly allows "a small number of known, bounded, non-critical issues,"
provided they are documented and "do not prevent autonomous, reliable, safe, and idempotent
operation." Applying that test to the classes above:

**Plausibly bounded / acceptable to defer, if the owner agrees and it is documented as such:**

- **Class I (LLM sampling nondeterminism).** It is provider-inherent, already fails closed rather
  than silently corrupting output (every sighting so far self-recovered on retry, and no sealed
  candidate's bytes have ever moved because of it), and is already the subject of active,
  evidence-gated investigation rather than being ignored. This matches idea.md's bar almost
  exactly: known, documented, and — so far — non-critical.
- **A low, monitored rate of dead-man alerts requiring a human to adopt or close a stranded PR/
  branch.** `plans/idea.md`'s Operating Model explicitly wants "passive oversight," not zero human
  involvement ever. If the *rate* of `liveness.yml` alerts stays low and each is a quick,
  low-judgment adoption/close action, this is closer to the passive-oversight model the document
  actually asks for than to "routine manual intervention" — the distinction is frequency and
  effort, not presence/absence of any human action at all.
- **Owner rulings on admitted PROPOSALs (§31's "proposals, not admissions" rule).** idea.md itself
  says "Human content review is optional and never blocks candidate readiness," and the mechanism
  here explicitly does not block unrelated work while a ruling is pending. A trickle of async
  judgment calls is compatible with the standard as written.

**Harder to justify as "bounded" — closer to a real blocker on calling this autonomous today:**

- **Classes A, B, D (push races, unscoped-stash near-misses, worktree/`.venv` corruption) are not
  judgment calls at all — they are pure git-mechanics accidents currently prevented only by
  convention agents must remember to follow every single time**, not by anything the system
  enforces. Class B's near-miss shows exactly what happens when that convention slips even once:
  another agent's uncommitted work was silently swept up, and the recovery was a human-supervised
  surgical `git show` extraction. `plans/idea.md`'s Production-Readiness Standard names precisely
  this shape of thing as disqualifying: "a system that works only through routine manual
  intervention does not meet this standard." A convention that has already had one documented
  near-miss and needed active, repeated, per-verification defensive discipline roughly a dozen
  times in two days is not yet "small number... bounded" — it is a live, recurring structural
  risk with a known, unbuilt, deterministic fix.
- **The detection/remediation split (§3) is a structural gap, not a bounded issue.** `liveness.yml`
  says outright that its own recovery path is "a new supervisor session" — i.e., a human. As long
  as that is true, the system cannot run "at regular intervals or triggers... without routine
  human intervention" (idea.md's own Operating Model language) whenever something the dead-man
  catches actually happens, because catching it and fixing it are two different steps and only the
  first is automated.
- **Class C's file-ownership coordination living only in a human coordinator's working memory** is
  a single point of failure for exactly the kind of continuity idea.md's Operating Model requires
  ("maintains the caches, persistent state, and idempotency controls required for reliable
  operation"). It currently is not durable state at all.

## 5. Highest-leverage next step

By recurrence, the single largest category in §1 is not any one bug but a standing condition:
**multiple write-capable agents sharing one mutable git checkout.** It is the named root cause of
class A ("two agents in one checkout make that race structural" — stated twice, in two different
incidents, a week apart) and class D, and it is the reason class B′'s defensive stash-scoping
discipline had to be exercised roughly a dozen times in this window alone to avoid a repeat of
class B's near-miss. No other failure class in this table recurred as pervasively or required as
much continuous, session-by-session defensive effort to avoid.

**Recommended highest-leverage change:** extend the isolation pattern the project already trusts
for lanes (`isolation: worktree` in the Agent tool — the exact mechanism this investigation itself
ran under) to *every* concurrently-live write-capable role, not only lanes, and pair it with a
small deterministic push wrapper (fetch → rebase/merge → retry N times against `origin/main`,
never against a shared local branch another live agent might be editing) for the moment an
isolated worktree's branch needs to land. This is a pure infrastructure/process-topology change —
no judgment call is needed to decide it, because the log itself already states the mechanism that
makes the alternative structurally unsafe. It would mechanically close classes A, B, and D at
their shared root, rather than patching each symptom (a push-retry script alone would still leave
the shared-checkout stash and `.venv`-junction hazards live; worktree-isolation-by-default removes
the precondition all three depend on).

Second, cheaper, complementary step: make `liveness.yml`'s failure path do something other than
wait for a human to notice a red Actions run — even a bounded action like auto-spawning a fresh
supervisor session on a stranded-PR/branch alert, or the "stalled" monitor auto-sending its own
fixed re-arm message (class J) instead of waiting for a human to type it — would directly narrow
the detection/remediation split named in §3 as the architecture's clearest remaining gap, without
requiring any new judgment-call machinery.

## 6. Open questions for the owner

1. Is running several concurrently-live, human/supervisor-coordinated agents against one shared
   checkout an intentional scaling choice for this sprint specifically, or something that should
   stop once lanes/worktree-isolation can cover the same throughput? Given the class-B near-miss,
   should this continue past the current sprint into anything called "production"?
2. Should a `liveness.yml` failure ever trigger an automated remediation action (auto-spawning a
   fresh supervisor session, for instance), or is a human always meant to be the one who reacts to
   it — and if so, does that satisfy idea.md's "no routine manual intervention" bar, or does it
   need to be explicitly re-classified as the "passive oversight" idea.md separately allows?
3. Is the LLM sampling-nondeterminism finding (class I: identical `request_sha256`, different
   completions, twice, on two different jobs) something the owner is willing to formally accept as
   a bounded, documented, non-critical issue under idea.md's own allowance — or does the standing
   `seed_support: deterministic: true` assumption in `RESEARCH_AND_GUIDELINES.md` §27.1 need
   correcting now, before more workstreams build on top of jobs that assume it holds?
4. Is a durable, machine-readable file-claims registry (replacing "the coordinator's own steer"
   for class C) in scope for a future workstream, or is ad hoc human/coordinator file assignment
   considered acceptable indefinitely for a project of this size?
5. Should the periodic PROPOSAL-sweep named as class H's own fix (grep `RESEARCH_LANE_*.md` for
   un-admitted `PROPOSAL` headings on a schedule, the same shape as the existing unblock-ledger
   mechanism) be admitted as a taskcard now that this investigation has independently corroborated
   the gap it would close, or does it still need its own dedicated measurement first per this
   project's own "no rule from one observation" discipline?
