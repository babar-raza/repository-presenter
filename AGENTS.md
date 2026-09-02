# Repository Presenter Agent Governance

This file governs coding agents building Repository Presenter. Keep governance small: detailed
product, runtime, research, and implementation requirements belong in their authoritative project
documents, not here.

## Mission

Build a production-running Repository Presenter, beginning with an autonomous README component
that monitors authorized upstream repositories, uses a configurable custom LLM for real product
interpretation and editorial judgment, validates every factual claim, preserves valuable inherited
content, proves unchanged no-op behavior, and safely opens or updates authorized pull requests.

Deliver working repository outcomes. Code volume, plans, tests, evidence, abstractions, and state
transitions are supporting work—not substitutes for a completed README transaction.

## Read Before Acting

Read in this order at the start of every session:

1. `project/state.yaml` — the only live implementation cursor.
2. The current gate in `docs/EXECUTION_STATE_MACHINE.md`.
3. Relevant behavior in `docs/STATE_MACHINE.md`, and `docs/README_CONTRACT.md` whenever the work
   item touches facts, composition, validation, or review.
4. Relevant context in `docs/RESEARCH_AND_GUIDELINES.md`.
5. `plans/idea.md` — the human product authority, for the outcome standard and standing
   constraints; never a cursor or task list.
6. Only legacy files named by the active reuse-manifest record.

Authority by subject:

- `plans/idea.md` owns the product outcome and standing constraints. Its references to legacy
  authorities resolve through the authority note at its top; they never reintroduce retired
  machinery.
- `AGENTS.md` owns agent conduct and safety.
- `docs/EXECUTION_STATE_MACHINE.md` owns build order and gate acceptance.
- `docs/STATE_MACHINE.md` owns production runtime behavior.
- `docs/README_CONTRACT.md` owns the candidate README's shape, assembly, agentic decisions, and
  blocking checks. `docs/REPOSITORY_LAYOUT.md` owns where a file lives.
- `project/state.yaml` owns current implementation status.
- `migration/reuse-manifest.yaml` owns legacy-code disposition after its audit.
- Accepted schemas and tests own implemented interfaces.

Never create a competing plan, roadmap, mission graph, task graph, or status authority.

## Work Loop

1. Read the current gate and active work item.
2. Confirm prerequisites; inspect affected code, tests, history, and evidence.
3. Select the smallest coherent change that closes a gate predicate.
4. Implement code and focused tests together.
5. Run focused checks, followed by the broader checks required by the gate.
6. Run production-shaped proof when claiming live gateway, GitHub runner, real repository,
   toolchain, recovery, or remote-effect behavior.
7. Record redacted, checksum-valid evidence.
8. Update the cursor only when evidence proves the transition.
9. Commit implementation, tests, evidence metadata, and cursor change coherently.
10. Continue with the next ready item while safe, in-scope work remains.

Only one shared-code item may be active. Parallel work is allowed only for disjoint paths after the
execution plan permits it. No two agents edit the same file or durable state concurrently.

## Implementation Discipline

- Preserve unrelated user work; never use destructive reset/clean commands for convenience.
- Research a battle-tested library or standard facility before writing a custom mechanism, per
  `plans/idea.md`'s Prefer Battle-Tested Solutions and `RESEARCH_AND_GUIDELINES.md` §18's registry
  — a legacy module is not exempt for having run in production. Departing from the registry's
  first choice needs a documented reason naming the alternative, in the commit or the file record.
- Port legacy behavior only through a reuse-manifest entry with source revision, destination,
  retained behavior, removed coupling, provenance, tests, and acceptance.
- Keep orchestration small; domain behavior belongs behind public component/plugin interfaces.
- Add ecosystems and families through registries, not a central `if/elif` chain; one ecosystem's
  extractor never imports another's or a downstream stage's module (`RESEARCH_AND_GUIDELINES.md` §7.4).
- Pull a legacy profile, policy file, or catalog record only for the repository or family in
  progress, never in bulk; verify what it claims still holds before writing its file record
  (`RESEARCH_AND_GUIDELINES.md` §7.2.1).
- Place every file where `docs/REPOSITORY_LAYOUT.md` puts it: README-specific work under
  `components/readme`, reusable capabilities under `core`, tests mirroring `src/` path for path.
  Record a genuinely new location there in the same commit; never leave a file "to organize later".
- Treat templates as presentation assets—not sources of facts, package names, commands,
  capabilities, formats, APIs, or limitations.
- Keep one central composer responsible for whole-document coherence.
- Keep independent review separate from candidate authorship.
- Route defects to their earliest causal stage; never weaken a downstream check to hide an upstream
  defect.
- Reuse accepted unaffected work when one dependency changes.
- End every work item with a run of the official entry point on the canary. A module with no
  production importer is a defect, not a deliverable.
- Count progress in one unit only: current reviewable no-op-proven candidates, N/34.
- Invalidate a candidate only through an input it consumed. Never add a global control-plane hash;
  validator and reviewer changes re-check and may yield `VALID_UPDATE_AVAILABLE`, never blanket
  invalidation.
- Make reviewer findings repairable: each names a section and a causal stage, or it is advisory.
- Keep governance within budget: this file at most 200 lines, the build plan at most 500 lines,
  at most eight gates. Replace a rule before adding one.

Two equivalent failed attempts, or 15 minutes without materially narrowing the cause, prohibit a
third equivalent attempt. Record a concise first-principles diagnosis and change the evidence,
prompt, model, component, stage, boundary, or mechanism.

## Agentic and Deterministic Boundary

Use the custom LLM for:

- product and audience interpretation;
- evidence-gap identification;
- inherited-content reconciliation;
- presentation planning;
- editorial composition;
- independent factual and visitor review; and
- targeted semantic repair.

Use deterministic code for:

- registry admission and processability;
- immutable snapshots, facts, provenance, hashes, and state;
- commands, verified examples, links, badges, and diagram topology;
- validation, transitions, invalidation, caching, leases, and recovery;
- authorization, GitHub effects, and effect reconciliation; and
- provider-call accounting and zero-call no-op proof.

An LLM proposes typed outputs. It never advances durable state, grants authorization, asserts a
deterministic gate result, or directly mutates a repository.

## Truth and README Content

- The exact immutable upstream revision is factual authority.
- Existing README and product-agent content are valuable evidence, not automatic truth.
- Aspose.org, external documentation, prior candidates, and imported corpora are development
  oracles; none can solely support a factual public claim.
- Every public claim maps to accepted evidence.
- Every material source README unit receives exactly one explicit disposition.
- Preserve uncertainty when evidence cannot resolve it; never invent a resolution.
- README/license-only placeholders return `insufficient_evidence`; never fabricate a candidate.
- A standard semantic shell does not permit mechanical template filling. Every processable
  repository still requires agentic interpretation and planning.

## Security and Effects

- Check the hard allow-list before repository-specific network work; analysis uses repository-scoped
  read-only credentials.
- Write credentials exist only in a separate effect job and are short-lived and target-scoped.
- Never log, commit, cache, or persist credentials or unredacted secret-bearing values.
- Work clones are push-disabled and verified before analysis.
- Initial publication is pull-request-only; never push directly to a target default branch.
- This control repository may be pushed to its own `origin` after the full local CI-equivalent
  passes, under `publication.control_repository` in `project/state.yaml`: directly to `main` while
  unprotected, by branch and PR with auto-merge once protected. Never force, never a product repo.
- Candidate acceptance never implies publication authorization.
- Recheck upstream revision immediately before an effect; reconcile uncertain remote effects before
  retrying.
- Do not perform a target write unless the current execution gate and exact authorization permit it.

## Testing and Evidence

Every behavior change includes focused tests. Include negative controls where applicable:

- hallucinated, unsupported, malformed, or contradictory model output;
- illegal state transitions; stale or corrupt evidence; secret leakage;
- duplicate triggers or effects; stale leases and fencing tokens;
- source drift before publication;
- invalid examples, public APIs, packages, links, or template facts; and
- non-processable placeholder repositories.

Unit tests do not prove hosted workflows, live LLM behavior, real toolchains, durable recovery, or
GitHub effects. Run the production-shaped proof required by the active gate.

Evidence is redacted, revision-bound, checksum-valid, and attributable. Evidence supports delivery;
creating evidence alone is not delivery.

## Git and Commits

- Keep commits coherent and scoped to the current gate/work item; never mix in unrelated
  cleanup, rewrite shared history, or discard uncommitted work.
- Review the complete diff and run required checks before committing; the index can already hold
  another session's staged work, so confirm `git diff --cached --stat` names only your own paths.
- Update the cursor in the same commit that establishes its claimed state.
- Identify the gate/work item in implementation commit messages or bodies.
- AI-authored commits include an appropriate `Co-Authored-By` trailer.
- After pushing, watch hosted CI to completion. A red run is fixed immediately, in the same work
  session — never left for a later iteration to discover.

## Blocking and Completion

Classify blockers:

- `BLOCKED_EXTERNAL`: missing credential/permission, provider outage, external infrastructure, or
  a factual decision only an authorized owner can make. Record the exact resume predicate and
  continue other safe work.
- `FAILED_INTERNAL`: code, wiring, schema, prompt, validation, or state defect. Diagnose, repair,
  verify, and resume. It is never acceptable completion.

Ask the user only when progress genuinely requires unavailable authority, credentials, a manual UI
action, or a material product-policy decision. Do not use the user as a substitute for repository
investigation or ordinary engineering judgment.

A work item closes only when implementation, tests, required production-shaped proof, evidence, and
cursor state agree. A gate advances only when every exit predicate passes. The project closes only
at the definition of done in `docs/EXECUTION_STATE_MACHINE.md`.
