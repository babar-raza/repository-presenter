# Investigation 03 — Issue-Tracking Component (Upstream Defect Reporting)

Written 2026-09-17, research only, no implementation at the time. **Status as of 2026-09-26: the
read/handoff half this report designed is now built and wired into the main pipeline; only the
GitHub-write half (`gh issue create`/`close`) remains deliberately unbuilt, pending `OWNER-04`.**
See "Current status (2026-09-26)" below for what actually exists today and where to look. The
rest of this document is left as written 2026-09-17 (research, not yet a record of what shipped)
except where a status note says otherwise.

Originally answered the investigation `docs/PRODUCTION_ROADMAP.md` assigns to workstream 3
("Issue-tracking component — file confirmed upstream defects, dedupe, close stale ones", anchored
to `plans/idea.md`'s "Upstream Defect Reporting" section). Nothing in the 2026-09-17 text below
authorized a taskcard by itself; that reconciliation pass has since happened (`docs/DECISION_LOG.md`
2026-09-17 15:40 UTC ruling) and the component was built.

## Current status (2026-09-26) — where are upstream issues being logged?

**Short answer: `evidence/upstream-defects/<owner>__<name>/<fingerprint>.json`, one artifact per
distinct defect, committed to this repository (not gitignored `runs/`) so it survives even for a
repository that never produces a `candidates/` bundle at all.**

- **Dedup key**: `{repository, defect_fingerprint}` — `defect_fingerprint` is a stable sha256 of
  `{repository, triggering_check.id, a primary-evidence signature}` (`components/issues/draft.py`),
  independent of prose wording, so an unrelated edit to a fact's evidence text never mints a second
  handoff for the same underlying defect. `components/issues/ledger.py::load_ledger`/`lookup` is
  the read layer over these artifacts (no second on-disk format), and fails closed
  (`LedgerError`) if two artifacts ever claimed the same key.
- **Lifecycle** (`schemas/upstream-defect-handoff.schema.json`, `components/issues/model.py`):
  `HANDOFF_PENDING` (drafted, nothing filed yet) → `HANDOFF_ACKNOWLEDGED` (owner has seen it) →
  `FILED` (issue number known, once GitHub-write creation is authorized) → `RESOLVED_UPSTREAM`
  (this system's own later re-check shows the same `triggering_check` no longer firing — only ever
  for a handoff this system itself filed, never a pre-existing upstream issue it merely tracks).
- **How an artifact gets created — two paths, both real code, never a hand-written JSON file:**
  1. **Automatically**, as of commit `6fa11ad` (2026-09-25, this same work item): `cli.py::run_present`
     calls `components/issues/draft.py::record_handoff_if_new` at the exact point it already calls
     `invalidate_bundle` on a blocking validation failure. It drafts a `HANDOFF_PENDING` artifact
     only when the failing check is genuinely (1) at `causal_stage EXTRACTING` — the one mechanical
     signal this codebase already has for "about the target repository, not repository-presenter's
     own composition" (`repair/targeted.py`'s `STATE_STAGES` maps only
     `INVESTIGATING`/`RECONCILING`/`PLANNING`/`COMPOSING` to a revisable stage), **and** (2) `BC-02`
     specifically — the one check shape `redetect.py` can already re-evaluate later — **and** (3)
     backed by a real, non-`SUPPORTED` `install_command` fact in that exact run's own `facts.json`,
     never a synthetic or unrelated failure. Every other check shape fails closed and drafts
     nothing; widening this set is deliberately conservative (see the PROPOSAL in
     `docs/DECISION_LOG.md`, 2026-09-26, for `BC-03`/example-compile failures as the next
     candidate, not yet landed).
  2. **Manually re-evaluated**, via the standalone CLI subcommand
     `repository-presenter redetect-upstream-defects [--root PATH] [--repo OWNER/NAME] [--apply]`
     (`cli.py::run_redetect_upstream_defects`, landed 2026-09-17): replays the handoff's own
     `triggering_check` against the repository's *current* state (`components/issues/redetect.py`,
     registered per check id — `BC-02` re-probes the package registry and manifest,
     `NOT_PROCESSABLE` re-runs `ast.parse` on the named source files) and proposes
     `RESOLVED_UPSTREAM` only for a handoff this system itself filed. `--apply` is the only path
     that ever calls `write_handoff`.
- **What exists on disk today (2026-09-26)**: three artifacts —
  `aspose-html-foss__Aspose.HTML-FOSS-for-Python` (`BC-02`, unpublished PyPI distribution + invalid
  `build-backend`), `aspose-tex-foss__Aspose.TeX-FOSS-for-Python` (`NOT_PROCESSABLE`, unparseable
  source), and `aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp` (`BC-02`, a GCC/Clang
  `-Werror=trigraphs` build failure on the repository's own correct Excel format-code literal,
  backfilled 2026-09-26 after an audit found the automatic hook postdated the finding — see
  `docs/DECISION_LOG.md` 2026-09-26 for the full trace). All three are still `HANDOFF_PENDING`:
  nothing has been filed to GitHub yet.
- **What is still not built, deliberately**: no `gh issue create`/`close` call exists anywhere in
  `src/`. `suggested_issue_title`/`suggested_issue_body` are literal text a human pastes by hand
  today. This stays gated on `OWNER-04` (a GitHub App with an Issues:Write scope) per
  `docs/EXECUTION_STATE_MACHINE.md` G7 and the original ruling below — filing itself was never
  meant to ship ahead of that authorization.

The remainder of this document is the original 2026-09-17 investigation. §1's opening claim ("No
filing, tracking, or GitHub-issue-API mechanism exists today — not even read access to issues.")
describes the state *before* the above was built and is now superseded by this status section;
left in place below as the historical record the later sections' reasoning builds on.

`plans/idea.md`'s own bar (§"Upstream Defect Reporting"): filing fires only after **independent confirmation**, not suspicion; it is **deduplicated** against issues the agent already filed or that already exist upstream; it never fabricates severity or claims an unverified fix. The seed example is Aspose.Email FOSS for .NET's `CS1929` build failure. A **bounded interim fallback** — "a precise, evidence-backed handoff describing the confirmed defect for a human to file" — is acceptable until direct issue creation is authorized and automated. The architecture already anticipates this: `docs/EXECUTION_STATE_MACHINE.md` G7 item 2 names "Upstream-defect handoff for a confirmed product defect (seed: Email .NET `CS1929`), evidence-backed and deduplicated, never a fabricated severity or unverified fix; later automated behind its own authorization and deduplication ledger" — placed *after* G1–G6 (portfolio sealing, rerun durability, proposal-effect proof), consistent with the roadmap treating this as investigation-only, parallel to sealing, not sequenced work.

## 1. Does the pipeline already surface genuine upstream defects anywhere?

**No filing, tracking, or GitHub-issue-API mechanism exists today — not even read access to issues.** The only GitHub interaction in `src/` is a pinned, push-disabled clone: `cli.py:413-421` calls `pinned_read_only_clone(..., token=os.environ.get("GH_TOKEN"))` and prints `"push disabled, verified"`. `core/secrets.py:18` recognizes exactly two secret variables (`GPT_OSS_API_KEY`, `GH_TOKEN`); neither implies an issues-write scope. There is no `github` API client module anywhere under `src/repository_presenter/` — grepping for `api.github.com` matches only the git-clone auth helpers (`core/git_safety/clone.py`, `core/git_safety/git.py`), not an Issues client. This matches the roadmap's honest "not started" status.

**But the pipeline already routinely produces the exact class of evidence this component would need to act on**, in two forms that already exist and are already load-bearing elsewhere in the contract:

- **Fact-level**: a fact's `Polarity` (`core/facts.py:35`: `Literal["SUPPORTED", "CONTRADICTED", "UNRESOLVED"]`) goes `CONTRADICTED` against repository/registry evidence, and the blocking check built on it fails with a `causal_stage` the repair loop cannot revise by editing prose (see §3).
- **Repository-level**: a whole-repository disposition of `NOT_PROCESSABLE` — "Terminal for revision... Immutable tree inventory, typed reason, resume predicate" (`docs/STATE_MACHINE.md:127`) — for a defect that blocks the entire candidate, not one fact.

Both are already used for genuine upstream defects this sprint, cataloged next.

## 2. Confirmed-upstream-defect findings already on record this sprint

Three named in the task prompt; a fourth (idea.md's own seed example) turned up a real gap worth flagging rather than assuming settled.

### HTML for Python — unpublished distribution + invalid `build-backend` (strongest example: independently reproduced three times)

`aspose-html-foss/Aspose.HTML-FOSS-for-Python`. `install_command:pip` is `CONTRADICTED` (`"pip install aspose-html-foss"`, evidence `"package registry: distribution not found"`). First measured and reproduced **outside the pipeline, twice**, per `docs/RESEARCH_LANE_E.md:2083-2092` (LANE-E-06, 2026-09-16 22:58 UTC):

1. `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/aspose-html-foss/json` → **404**.
2. `pip install --target <dir> <the pinned clone root>` fails with `BackendUnavailable: ModuleNotFoundError: No module named 'setuptools.backends'` — the repository's own `pyproject.toml` line 3 declares `build-backend = "setuptools.backends.legacy:build"`, not a real setuptools entry point (correct name: `setuptools.build_meta`). "The package cannot be built by any standard tool, not only ours" (RESEARCH_LANE_E.md:2091-2092).

Independently corroborated a first time at `docs/DECISION_LOG.md:2240-2242` (G3-W04, 2026-09-07: "`aspose-html-foss/Aspose.HTML-FOSS-for-Python` declares `build-backend = "setuptools.backends.legacy:build"`, a module in no setuptools release, so `pip install .` raises `ModuleNotFoundError` for everyone"), and a third time at `docs/DECISION_LOG.md:3411` (2026-09-17: "`BC-02` is the target repository's own upstream defect (unpublished PyPI distribution plus a non-existent build-backend), independently confirmed identical to LANE-E-06's and LANE-E-14's own prior measurements"). Disposition: `NOT_SEALED`, blocked at validation stage S9 with `BC-02` `FAIL` (`RESEARCH_LANE_E.md:2220`); four other sealed Python candidates carry `install_command:pip` `SUPPORTED` against genuinely published distributions of the same shape, ruling out a systemic extractor bug (`RESEARCH_LANE_E.md:2095-2100`).

### TeX for Python — 35 of 45 source files fail to parse

`aspose-tex-foss/Aspose.TeX-FOSS-for-Python`. `docs/DECISION_LOG.md:2232-2239` (G3-W04, 2026-09-07 12:20, "verified against the live oracle, not the clone"): source indentation is collapsed to one space per level; 35 of 45 Python files do not parse, including `src/aspose_tex/presentation/__init__.py` — the module the repository's own docstring calls the user-facing entry point. Confirmed via `gh api` against the pinned revision, where `ast.parse` raises `IndentationError` at line 108. "The library cannot be imported at all... No other cohort repository has a single unparseable file." Disposition: `NOT_PROCESSABLE` (`docs/RESEARCH_LANE_E.md:1233-1235`).

### Aspose.Email FOSS for .NET `CS1929` — idea.md's seed example, **not independently reproduced by this sprint's own record**

`plans/idea.md:494-500` states this as settled fact ("an isolated build of the exact source it claims to publish fails with genuine `CS1929` compiler errors"), and `docs/EXECUTION_STATE_MACHINE.md:353,421` and `docs/RESEARCH_AND_GUIDELINES.md:2211,2555,2585` all cite it as the anchor example for the .NET cohort's "evidence-bound dispositions." But the currently **sealed** candidate contradicts a live reproduction at the current pinned revision: `candidates/aspose-email-foss__Aspose.Email-FOSS-for-.Net/59125b4732df0eedbc4d4c2ab978698ed4348eb7/examples.json` records all 4 compiled examples `"outcome": "EXECUTED"`, `"build_verified": true`, `"return_code": 0`, `stdout: "Build succeeded.\n    0 Warning(s)\n    0 Error(s)"` (SDK 10.0.204). Nothing in this sprint's `DECISION_LOG.md` or `RESEARCH_LANE_*.md` records an independent `dotnet build`/compiler reproduction of `CS1929` against a current revision the way HTML-Python and TeX-Python both have. This does not mean the underlying claim is false — the four compiled examples may simply never call `MultipartParser.SequenceEqualAscii`, and idea.md does not date-stamp when `CS1929` was observed — but it means **this sprint has not itself met its own "independently confirmed, not suspected" bar for its own seed example**. See open question in §8.

### A boundary case worth naming: not every blocked repository is a product defect

`aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript` is recorded `BLOCKED_INVESTIGATION` (S3) because "there is genuinely no combination of evidence" supporting an inherited workflow claim (`docs/DECISION_LOG.md:3273`) — that is a reconciliation/claim-accountability problem (a README says something the repository doesn't support), not a defect in the target product's own code. Likewise the sprint's `AUD-001`–`AUD-005` findings (`docs/DECISION_LOG.md:2260-2265`) are all bugs in **repository-presenter's own** renderer/reviewer/state, never in a target repository. This component's filing bar (`plans/idea.md:493`: "a genuine defect in the product itself—not a presentation gap") needs to keep that line sharp: only HTML-Python's and TeX-Python's class — a fact CONTRADICTED against the target repository's own manifest/source, independent of anything repository-presenter authored — is in scope; unsupported-claim and BLOCKED_INVESTIGATION dispositions generally are not, by themselves.

## 3. The verification bar, grounded in this codebase's own data structures

This codebase already has a mechanical way to distinguish "our composition is wrong" from "their code/manifest is wrong," and it is exactly the signal this component should hook into.

- `validation/registry.py:97-99` types `CausalStage = Literal["EXTRACTING", "INVESTIGATING", "RECONCILING", "PLANNING", "COMPOSING"]`. `Failure("EXTRACTING", ...)` is raised for: an unpinned/altered source revision (`registry.py:515-529`), a fact with no evidence (`:533`), an install-command fact whose polarity isn't `SUPPORTED` or that lacks manifest+registry-or-source-build corroboration (`_check_install`, `:537-583`, exactly the branch HTML-Python hit), an example fact "not executed or compiled at this revision" (`_check_examples`, `:604-620` — this is the mechanical analog of a `CS1929`-shaped compile failure specifically), and a link target whose fact is not `SUPPORTED` (`:838-848`).
- The repair loop's own routing (`repair/targeted.py:45-50`) maps only `INVESTIGATING→S3`, `RECONCILING→S4`, `PLANNING→S5`, `COMPOSING→S6` to a revisable stage; `STATE_STAGES.get("EXTRACTING")` returns `None`, so `validation_defects()` (`targeted.py:213-260`) marks it `"{state} is not repairable by revision"` (`:251-252`). **A `Failure`/check whose `causal_stage` resolves to `None` via `STATE_STAGES` is, by this codebase's own design, structurally about the target repository, not the candidate's prose** — the repair loop already refuses to touch it. That is the natural, already-instrumented trigger signal for this component: any `EXTRACTING`-stage blocking-check failure (`BC-01`, `BC-02`, `BC-03`, `BC-06` are the ones observed to raise it) whose failure text names a target-repository fact (an install command, a compiled example, a source file) rather than a rendering artifact is a candidate upstream-defect finding.
- What "independently confirmed, not merely suspected" means **in this codebase's own practice** (not just idea.md's prose): both real examples above were reproduced by a command run **outside repository-presenter's own pipeline** against the pinned revision — `curl`/`pip install`/`ast.parse`/`gh api` — not merely inferred from the pipeline's own `facts.json`. `RESEARCH_LANE_E.md:2083`: "Measured independently, twice, outside the pipeline entirely, not inferred from its output." An automated filer should hold itself to the same bar: treat a single `EXTRACTING`-stage FAIL as *filing-eligible only if* the underlying evidence itself (not just the pipeline's polarity label) is directly checkable and was checked — e.g., replaying the exact registry/build probe the fact already recorded, or reusing the receipt if it already embeds a literal, checkable external observation (`registry.py:548`: `details = " ".join(evidence.detail ... )` — the evidence entries already carry this).
- The severity/fix-claim discipline already exists in code for a narrower case and should be the template: `_check_install`'s `elif proved and not (...)` branch (`registry.py:566-578`) exists precisely because "a rendered `npm run build` nobody measured is the fabricated compile claim lane B refused to write" — i.e., the codebase already refuses to state more than a receipt proves. An issue body generator must inherit that discipline: state only the literal command/output/error/revision a receipt proves, never an inferred severity word, never "this fixes it" unless a fix was itself compiled and verified.
- Repository-level parallel: `NOT_PROCESSABLE` (`STATE_MACHINE.md:127`) already carries "Immutable tree inventory, typed reason, resume predicate" — the repo-level equivalent of a fact's evidence, and the natural trigger for a whole-repository handoff (TeX-Python's shape) rather than a single-fact one (HTML-Python's shape).

## 4. GitHub API/CLI capabilities (verified locally: `gh version 2.83.2`)

- **`gh issue create`**: `--title`, `--body`/`--body-file` (`-` for stdin), `--label`, `--assignee`, `--milestone`, `-R OWNER/REPO`. No built-in dedup — the caller is entirely responsible.
- **`gh issue list`**: `--search QUERY` (GitHub's issue search syntax, e.g. `in:title,body`), `--state {open|closed|all}`, `--author`, `--label`, `--json fields` (includes `id, number, title, body, state, stateReason, labels, author, createdAt, url`). This is the dedup lookup primitive: e.g. `gh issue list --search "in:body <fingerprint>" --state all --json number,title,state,url,body`.
- **`gh issue close {number|url}`**: `--reason {completed|not planned}`, `--comment`. The two reasons map cleanly onto this component's two close cases (§6): `completed` for "the maintainers fixed it," `not planned` for "no longer applicable / was a false positive."
- **Underlying REST/GraphQL**: `POST /repos/{owner}/{repo}/issues` (create), `GET /repos/{owner}/{repo}/issues` (list, filterable by `labels`, `state`, `creator`, `since`), `PATCH /repos/{owner}/{repo}/issues/{number}` (update/close, `state_reason` field), `GET /search/issues?q=...` (full-text search across title+body — the real dedup primitive, more flexible than `issue list --search`). `gh` wraps all of this; nothing here requires a bespoke HTTP client beyond what `gh` (already the "battle-tested tool" idea.md's Implementation Principles prefer) exposes.

**What deduplication concretely requires**, beyond what `gh`/the API hands you for free:

1. **A stable fingerprint per defect** (e.g., a hash of `{repository, triggering check id, primary evidence signature}` — for HTML-Python: `install_command CONTRADICTED: distribution-not-found + invalid-build-backend`), embedded invisibly in the filed issue body (an HTML comment marker, e.g. `<!-- repository-presenter-defect: sha256:... -->`) or carried as a dedicated label (`repository-presenter:filed`) — title/body text alone is too fragile to match reliably across maintainer edits.
2. **Searching existing OPEN (and ideally all) issues before filing** — for issues this system already filed, the fingerprint marker makes this exact; for **pre-existing upstream issues it never filed**, only best-effort keyword search (`gh issue list --search`) is available, which is inherently fuzzy. That asymmetry means the pre-existing-issue half of dedup cannot be made as reliable as the self-filed half by API means alone — a plausible search hit should route to human adjudication (the interim handoff, or a flagged review) rather than silently either duplicate-filing or silently skipping.
3. **A durable local ledger of which issues this system filed** — GitHub search at file-time is not sufficient on its own (rate limits, eventual consistency, and the fuzzy-match problem above). This needs its own record, independent of GitHub, mapping `{repository, defect fingerprint} → {issue number/URL, filed_at revision, last-observed state}` — the natural analog of the per-item receipts this codebase already keeps at `evidence/build/lanes/<lane>/<ITEM>.json` (`docs/REPOSITORY_LAYOUT.md:83`).

## 5. The interim fallback: an evidence-backed handoff artifact

`plans/idea.md` uses the identical phrase — "a precise handoff" — for both the issue-filing interim (§"Upstream Defect Reporting") and the visual-asset interim (§"Visual Assets and Social Preview": "a validated asset and a precise handoff when no safe, supported automation mechanism is available"). This is a recurring shape in the product authority, not a one-off; the concrete artifact sketched below is scoped to issue-tracking only, but a future pass may find it shares a schema family with the visual-asset handoff.

Modeled directly on this pipeline's own existing evidence conventions (`facts.json`'s per-fact `{id, kind, value, polarity, evidence: [{detail, path}], attributes}` shape, `validation.json`'s per-check `{id, version, causal_stage, verdict, failures, sections}` shape, and the `schemas/*.schema.json` governance pattern):

- **Location**: a new `evidence/upstream-defects/<owner>__<name>/<fingerprint>.json`, committed (not under gitignored `runs/`) — this needs to be durably reviewable like every other `evidence/` artifact, and critically must be able to exist for a repository that **never produces a candidate bundle at all** (TeX-Python has no `candidates/` entry — a candidate-bundle-scoped location would have nowhere to put its finding).
- **Suggested fields**, each traceable to an existing structure:
  - `repository`, `source_revision` — identical identity fields every candidate `manifest.json` already carries.
  - `defect_fingerprint` — the stable dedup key from §3.
  - `triggering_check`: `{id, version, causal_stage}` — literally `validation.json`'s own check-record shape (e.g. `{"BC-02", "2", "EXTRACTING"}`), so the handoff stays traceable back to the exact check and version that fired.
  - `evidence`: a list of `{detail, path}` records — the same shape `Fact.evidence` already uses — but populated with the **outside-the-pipeline** reproduction this codebase's own practice demands (the literal `curl`/`pip install`/`ast.parse`/`gh api` command and its literal output), not merely a restatement of the pipeline's own polarity label.
  - `claim`: one plain factual sentence, no severity adjective, no fix claim — modeled on idea.md's own seed-example prose style ("the published NuGet package is registry-verified, but an isolated build... fails with genuine `CS1929` compiler errors").
  - `suggested_issue_title` / `suggested_issue_body`: literal drafted text a human can paste unmodified into `gh issue create --title ... --body-file ...` — this is what makes the handoff "precise" rather than merely structured data someone still has to write prose from.
  - `status`: an enum in the same naming register as `NOT_PROCESSABLE`/`BLOCKED_*` — e.g. `HANDOFF_PENDING` (nothing filed), `HANDOFF_ACKNOWLEDGED` (owner has seen it), `FILED` (issue number known, once creation is authorized), `RESOLVED_UPSTREAM` (§6) — each carrying its own typed reason/resume predicate, the same convention `STATE_MACHINE.md:127` already uses for `NOT_PROCESSABLE`.
  - `issue_ref`: `{number, url}` once filed, `null` until then.
- **Governance**: a `schemas/upstream-defect-handoff.schema.json` alongside the existing five schema files, so this artifact is governed the same way `facts.schema.json` governs facts — not an ungoverned ad hoc format.
- This entire interim shape stays inside the **read-only** Gate A/B boundary — it needs no new GitHub write scope at all, matching idea.md's explicit permission to defer "direct issue creation" specifically while still producing the confirmed finding now.

## 6. The closing side

Two distinct close reasons, matching `gh issue close --reason`'s own two values:

- **`completed`** — the defect was fixed upstream. Mechanically: on a later drift-triggered re-run (`STATE_MACHINE.md:119,127`: `NON_PROCESSABLE`/`OBSERVED` already reopen "after source drift or policy change"; Gate B's own refetch-and-reopen cycle, `plans/idea.md` Gate B), the same `triggering_check` is re-evaluated at the new pinned revision. If it now returns `PASS` (or the underlying fact flips back to `SUPPORTED`), that is the close signal — no new machinery needed beyond re-running the check the handoff already points to and comparing verdicts.
- **`not planned`** — the finding was a false positive, or a later check-version change altered what counts as `SUPPORTED`/`PASS` for reasons unrelated to the target repository (e.g. `BC-02` bumping from version "1" to "2" per `registry.py:126-135`'s own recorded history). This should never be inferred silently; it needs the same evidence discipline as filing (§4's severity/fix-claim rule applies symmetrically to closing: never close without citing the new revision and the specific check/fact that flipped).

**Scope limit worth flagging explicitly**: the ledger in §4.3 lets this system reliably know which issues *it* filed, so *auto-closing* is only safe for entries whose `issue_ref` this system itself set. For a **pre-existing** upstream issue this system is merely tracking (not one it filed), idea.md's "deduplicated against... issues that already exist upstream" language is about *not re-filing*, not about *closing on the maintainers' behalf* — closing someone else's issue is a materially different, more sensitive action idea.md never actually authorizes. Recorded as an open question below rather than assumed either way.

## 7. Concrete next steps (for whoever writes the taskcard — not authorized by this report alone)

1. Reconcile this report with `plans/idea.md` and get an owner ruling on the open questions in §8 before any schema or code is written (per the roadmap's own standing rule).
2. Design `schemas/upstream-defect-handoff.schema.json` and the `evidence/upstream-defects/` layout as a pure read-only-boundary addition — provable without any GitHub write scope, so it can land and be exercised (on HTML-Python and TeX-Python, which already have the evidence) well before G6/G7's write-authorization machinery exists.
3. Backfill two real handoff artifacts against the confirmed findings in §2 (HTML-Python's `BC-02`, TeX-Python's parse failure) as the first proof this shape is sufficient for a human to actually file from, before generalizing the extraction logic.
4. Independently re-verify `CS1929` (the open question in §2/§8) before this component is ever exercised against idea.md's own named seed example — do not assume idea.md's narrative is still current at today's pinned revision.
5. Only after the above: design the dedup ledger and the `gh issue create`/`list`/`close` wrapper, explicitly behind its own authorization gate (analogous to Gate C's separate proposal-PR authorization payload, `EXECUTION_STATE_MACHINE.md` G6), never sharing the existing read-only clone token.

## 8. Open questions for the owner

- **Is `CS1929` still reproducible today?** This sprint's own sealed `aspose-email-foss__Aspose.Email-FOSS-for-.Net` candidate shows all 4 compiled examples building cleanly (0 errors) at the current pinned revision (`candidates/aspose-email-foss__Aspose.Email-FOSS-for-.Net/59125b4732df0eedbc4d4c2ab978698ed4348eb7/examples.json`). Before this component is ever pointed at idea.md's own seed example, someone should independently re-check it (outside the pipeline, per this codebase's own established practice) rather than assume it. **Re-checked 2026-09-26 (`docs/DECISION_LOG.md`, this date): still not independently reproduced anywhere in this sprint's own record. Still open; no handoff drafted for it, correctly — see "Current status" above.**
- **Does dedup ever authorize closing a pre-existing (not self-filed) upstream issue** once this system's own re-check shows the defect gone, or is that always a human-only act? idea.md's Upstream Defect Reporting section only discusses filing and dedup against existing issues, never closing one this system didn't create.
- **Where should the handoff artifact live** — a new `evidence/upstream-defects/` subtree (this report's recommendation, needed because `NOT_PROCESSABLE` repositories like TeX-Python never produce a `candidates/` bundle at all), or folded into the existing per-candidate bundle for repositories that do seal?
- **What credential/authorization boundary should issue-write use?** The existing `GH_TOKEN`/App path is explicitly read-only (clone-only, "push disabled" enforced at `cli.py:413-421`); this needs its own separately authorized write scope. Should it reuse Gate C's proposal-PR authorization machinery once built, or does it need an independent authorization path since a genuine product defect can surface (and matter) long before the Java proposal cohort (Gate C) is reached?
- **Should a filed issue ever be auto-updated** (not just closed) if the defect's observed details drift slightly across upstream commits without disappearing? idea.md addresses create/dedupe/close only.

## Reverse by

`git revert` — this is a pure documentation addition (one new file under `docs/investigations/`), no code, schema, or check coupling. Removing it returns the project to the state `docs/PRODUCTION_ROADMAP.md` already recorded ("pending").

**2026-09-26 update note**: the "Current status" section prepended above, and the `CS1929` re-check note in §8, are also pure documentation; reverting them by `git revert` of that commit alone restores this file to its 2026-09-17 text with no code, schema, or check coupling either. They do not change any conclusion this file originally drew — they record that the design was since built and that its open questions (`CS1929` reproducibility, the closing-a-pre-existing-issue question) remain genuinely open, not resolved by construction.
