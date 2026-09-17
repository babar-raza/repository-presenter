# Investigation 11 — `plans/idea.md` Gap Analysis

Written 2026-09-17, owner-directed ("check plans/idea.md deeply and then map everything from the
state machine, decision logs and everything else on this repo against it. goal is to find the
gaps"). Research only, no implementation, no ruling — this document identifies gaps; it does not
resolve them. Produced by four parallel read-only research passes cross-referencing `plans/idea.md`
(539 lines, read in full) against `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md`,
`project/state.yaml`, `docs/DECISION_LOG.md` (~3670 lines), `docs/RESEARCH_AND_GUIDELINES.md`
(~3310 lines), and the actual `src/repository_presenter/` implementation. Each finding below cites
its source file/line; nothing here is inferred without a citation.

## Severity A — confirmed conflicts with `idea.md`'s literal text (not just "unbuilt")

1. **Aspose-link density ceiling is a hardcoded constant, not the deterministic derivation
   `idea.md` requires.** `idea.md:60-61`: "the system derives conservative maxima deterministically
   from the README's visible content size and verified code examples." Actual: `PlanningPolicy.
   aspose_links_max` is a fixed `4` (`composition/policy.py:21`), applied identically regardless of
   README size or example count (`composition/planning.py:914,964-965`; `validation/registry.py:
   868`). The per-slot maxima (`aspose.org`/`aspose.com`, `products`/`docs`/`kb`/`blog`/`reference`)
   `idea.md` also describes don't exist — one flat field, not per-domain ceilings.

2. **Second-reviewer scope was broadened beyond `idea.md`'s explicit limit, with no reconciling
   entry against that text.** `idea.md:305-308`: "A second reviewer runs only for a typed risk
   trigger proven by the regression corpus." The original 2026-09-06 landing matched this exactly
   (scoped to `criterion: presentation`, evidenced against a real regression corpus, §27.10). A
   2026-09-11 07:12 UTC sprint taskcard (`PHASE1/F6`) made a corroborating second read mandatory
   for *every* ACCEPT verdict, unconditionally (`review/independent/review.py:48`, `validation/
   registry.py:1444`) — justified as "the TB-04 principle, symmetric," not as a new typed trigger
   tied to the regression corpus `idea.md` requires. No entry in either decision doc cites `idea.md`'s
   "only" when making this change; it was decided at sprint-taskcard level, not product-authority
   level. Real operating-cost change (doubles reviewer cost on every accept) that arguably contradicts
   the literal word "only."

3. **`idea.md`'s own CS1929/Aspose.Email seed example appears stale, and nobody has re-verified it.**
   `idea.md:493-500` names this as *the* seed example for Upstream Defect Reporting. The currently
   sealed candidate's own evidence (`candidates/aspose-email-foss__Aspose.Email-FOSS-for-.Net/
   59125b4732df0eedbc4d4c2ab978698ed4348eb7/examples.json`) shows all 4 compiled examples `EXECUTED`,
   `build_verified: true`, `0 Warning(s) 0 Error(s)` at the current pinned revision — the opposite of
   what `idea.md` cites. `docs/investigations/03-issue-tracking.md` §2/§8 already flags this as an
   open question; it has not been independently re-checked outside the pipeline by anyone.

4. **The 31/31 baseline is confirmed stale, deliberately left uncorrected, and `idea.md`'s own body
   text now contradicts its own top-of-file authority note.** `idea.md:154-158` states "31/31
   processable READMEs" pinned to commit `df864ffd`. `DECISION_LOG.md` 2026-09-07 15:17 UTC (AUD-003,
   "CONFIRMED, critical") found the registry actually has 34 entries at that commit (PDF-TypeScript
   admitted 2026-08-26, never reconciled into the body text), and separately that TeX-Python's
   non-processable status means the achievable ceiling is 31 "for a different reason than what is
   written." Explicitly not corrected — "`plans/idea.md` is owner-owned... the owner has the exact
   denominator language to correct at their discretion." A governance test now exists
   (`tests/test_governance_consistency.py`, landed via `PHASE1/F8`) that actively prevents this stale
   figure from being *restated* elsewhere in project prose — but it cannot and does not touch
   `idea.md` itself, which still carries the stale figure ten days later.

5. **Gate C0 (discovery/intake) is built after Gate A (README) work, the opposite order `idea.md`
   requires.** `idea.md:280-281`: "a later gate never starts before the gate it depends on is
   actually accepted." `idea.md`'s own ladder places Common Gate C0 (full-registry discovery/intake)
   *before* Gate A. The actual build order does README-candidate work at G1-G3 (`current_gate:
   G3_PYTHON_COHORT`, `project/state.yaml:23`) while full-visibility discovery/intake is scheduled
   later, at G5 (`docs/EXECUTION_STATE_MACHINE.md:378-379`). A partial, ad hoc discovery scan did
   happen outside any formal gate on 2026-09-17 (`docs/investigations/10-portfolio-discovery.md`),
   producing one still-open owner item (`OWNER-08`), but this doesn't resolve the structural
   sequencing inversion.

## Severity B — named states/mechanisms that exist only as prose

6. **`PORTFOLIO_AGENT_ACCEPTED`, `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION`, and
   `PR_ELIGIBLE` exist nowhere outside `idea.md`** (grep-confirmed across the full tree — zero
   matches in any schema, code constant, test, or `state.yaml` field). Same for the phrases "first
   verified README," "cross-ecosystem canary gate," and "portfolio README proof." `docs/
   EXECUTION_STATE_MACHINE.md` §12 maps `idea.md`'s *obligations* (individual sentences) to G-gates
   at the content level reasonably well, but never uses `idea.md`'s own gate names (C0/A/B/C) or
   terminal-state vocabulary anywhere — a reader has to infer the correspondence themselves; it is
   not machine-checkable. Functionally, the nearest analogs are `READY_FOR_PROPOSAL`/`AWAITING_
   AUTHORIZATION` (`docs/STATE_MACHINE.md:140-141`) and portfolio-level `HEALTHY`
   (`docs/STATE_MACHINE.md:58-68`) — but these are differently scoped (per-repository, or a weaker
   portfolio bar) than what `idea.md` actually specifies for Gate B's exit.

7. **`data/products.json`, `idea.md`'s own named "hard execution allow-list" (`idea.md:148`), does
   not exist.** The actual live allow-list is `data/registry.json` — a stale filename reference
   inside `idea.md`'s body, distinct from the authority-note table at the top (which correctly
   doesn't make this claim).

8. **`idea.md`'s own Agile-operating-model steps 1-2 reference retired machinery.** `idea.md:179-180`
   describes mission `evaluate`/`status` selecting "one typed immediate goal... from the earliest
   dependency-ready or regressed boundary." `idea.md`'s own top-of-file authority note (`idea.md:15`)
   already retires this exact machinery: "Level-8 mission graph, mission `evaluate`/`status`...
   Retired. `project/state.yaml` is the only build cursor." The CLI's actual `status` command
   (`cli.py:161-166,215-216,294-295`) does a materially narrower thing than steps 1-2 describe, and
   no `evaluate` command exists at all. The body of `idea.md` was never reconciled with its own
   authority note after that note was added.

9. **No frozen `RegistryRevisionV1` exists yet.** Confirmed still-open by `project/state.yaml:
   149-158` itself (`status: REVALIDATE_DURING_G1_THROUGH_G3_FREEZE_AT_G4`) — consistent with
   `idea.md`'s own caveat that this is a "dated observation," not a discrepancy between documents,
   just genuinely unfinished work.

## Severity C — real, currently-unbuilt gaps (mix of explicitly-deferred and not)

10. **No CI/build-status badge** despite being one of the four fixed badge-row slots `idea.md:72-73`
    specifies (package, platform/runtime, **build status**, license). `_badges()`
    (`composition/renderer.py:236-277`) renders package/runtime/license/contributors only. A
    `.github/workflows/` directory is detected as a fact (`evidence/facts/assets.py:29`) but never
    turned into a badge.
11. **Canonical product name is only enforced in renderer-owned slots**, not in LLM-authored prose
    (opening, relationship prose) — no check catches a package/namespace shorthand substituting for
    the full name there. BC-04 validates fact-ID citation and code-span identifiers, not name-form
    usage.
12. **Keyword/SEO output-lineage tracking doesn't exist.** `docs/README_CONTRACT.md:247` itself
    already marks this "Advisory at G1, candidates for v1 blocking at G2" — known and explicitly
    deferred, not a surprise, but zero code (even advisory) implements it yet.
13. **No copyright-line policy toggle exists** — `idea.md` describes one ("a portfolio policy may
    enable it only when... applied consistently"); `PlanningPolicy` has no copyright-related field
    at all. The default-omitted behavior holds trivially since no code path ever emits one, but the
    configurability itself is simply absent.
14. **Repeated-blank-line normalization inside example code blocks isn't enforced** — example fact
    values are emitted verbatim with no blank-line-run check.
15. **`FileInventory.community_paths` is dead code.** `core/snapshot/inventory.py::scan()` detects
    CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT presence, but the result is consumed nowhere else
    in `src/` (grep-confirmed, only the defining file matches). "Checking" community files per
    `idea.md`'s Central Agent bullet 3 is detection-only, never content reconciliation — matches
    `docs/investigations/02-repo-metadata-community-files.md`'s own finding, now independently
    corroborated by direct code search rather than that investigation's own claim alone.
16. **Central Agent responsibility bullets 1 (repo description), 2 (website/topics/visuals/social-
    preview), and 7 (auditing GitHub-generated metadata: stars/forks/contributors/languages/
    activity) have zero code surface anywhere in `src/`.** Bullets 2 and (per `idea.md`'s own text)
    the visual-asset half of this scope are explicitly allowed to be incomplete during the initial
    pilot; bullets 1 and 7 carry no such explicit allowance in `idea.md`'s text, though they are the
    least product-risk items on the list.
17. **Upstream Defect Reporting's interim handoff fallback is real** (schema + 2 backfilled
    artifacts, landed 2026-09-17), **but the filing/dedup/close mechanism itself does not exist in
    code** — consistent with, and already tracked by, this session's own WS3 rulings
    (`docs/PRODUCTION_ROADMAP.md`, `docs/DECISION_LOG.md` 2026-09-17 entries); not a new finding, a
    corroboration that the existing tracking is accurate.

## Confirmed clean — no gap found

Independent agentic review mechanism (`docs/STATE_MACHINE.md` §4.1/§7.5, ESM G1 exit predicate) —
**MET**. LLM call-attribution ledger (`core/llm/ledger.py:37-64`) — **MET**, a superset of every
field `idea.md` lists. Prompt-registry governance — **MET**, mechanically enforced by a real,
running CI test (`tests/core/llm/test_prompt_hygiene.py`). Product/platform auto-detection — **MET**.
Ecosystem-truth public-consumer-surface extraction — **MET for all three named ecosystems** (Python,
TypeScript, Rust), each with real negative-control tests. Battle-tested-vs-custom documented
discipline — **MET**, a real, actively-used table in `docs/RESEARCH_AND_GUIDELINES.md:1059-1064`.
Trust/reconciliation discipline (existing README as evidence) — **MET**
(`reconciliation/dispositions.py`). Section order, title-case/abbreviations, At-a-Glance graph
topology, `<details>` visibility rules, internal-narration leak-check, and maintainer-README
"exactly once" disposition accounting — all **ENFORCED** with real, cited tests. Aspose-link
relevance/naturalness enforcement mechanism itself exists (only the numeric ceiling is the gap, see
Severity A.1). Protected-content mechanism (preventing automated updates from overwriting strong
content with generic text) — **MET**. No genuine check-weakening was found anywhere in the decision
log's history; every `REVERSES`-marked entry is a narrow, self-certified, non-weakening correction.

## Post-publication corrections (owner re-check, 2026-09-17, same day)

The owner directly challenged three findings from the standing-constraints research pass. Two were
incomplete, not wrong; re-verified with direct evidence below.

**"Ecosystem-truth extraction MET for Python, TypeScript, Rust" was too narrow.** `idea.md:358-360`
does only name those three ecosystems for its specific "public consumer surface" sentence, so the
original verdict was textually accurate to that one sentence — but the codebase's actual surface
extraction is not limited to three ecosystems. `_vendor/aspose_extraction/lang/` has a real,
language-specific module for **all seven** registry ecosystems (`python.py`, `typescript.py`,
`rust.py`, `java.py`, `go.py`, `csharp.py`, `cpp.py`), each with genuine per-language handling
(confirmed by reading `api_surface.py`: C++'s `internal/` private-header exclusion gated strictly
to `language == "cpp"`; C#'s `Outer+Inner` nested-type separator mapping; Rust's `pub mod`
visibility walk). Package-registry publication probing (`extractors/surface/registry.py::
REGISTRY_TYPES`) covers six of seven — `python`→pypi, `net`→nuget, `java`→maven,
`typescript`→npm, `go`→go_modules, `rust`→cargo — **`cpp` has no entry**, a real, structural
asymmetry (C++ has no single canonical package registry the way the others do, not an oversight to
silently fix). Test-coverage *depth* is genuinely uneven: Python has a dedicated cross-check against
a trusted AST reader (`test_parity.py`) plus the largest test surface by far; TypeScript has its own
dedicated re-export-semantics test; C#/C++ get generic extractor-mechanics tests
(`test_extractor.py`); no dedicated per-language test file was found for Java, Go, or Rust surface
extraction specifically in this pass (their vendored modules exist and are exercised by the shared
`test_determinism.py`/`test_manifest.py` machinery, but not by a language-specific test the way
Python/TypeScript have). Corrected verdict: **extraction code exists and is real for all 7
ecosystems; test-coverage depth is not equal across them, and cpp is structurally excluded from
one specific check (registry publication) for a legitimate reason.**

**"Product Agents: no code, as expected" was incomplete.** The original grep was scoped to `src/`
and `schemas/` only. `docs/RESEARCH_AND_GUIDELINES.md:1216` has a real, load-bearing "D —
product-agent owned" row in the surface-ownership classification table ("releases, packages:
Audit/handoff only, no writer, ever") — i.e., "product agent output" *is* represented in this
project's governance model, as the class of content the maintainer/product team already owns and
that this system may only audit, never author. The core verdict stands (no `ProductAgent` class or
component needs to exist — idea.md describes an external human process, and `reconciliation/
dispositions.py` already treats existing README/release/package content exactly as idea.md's
"Trust and Repository-Grounded Reconciliation" section requires), but the original finding
undersold how deliberately this is already modeled, not absent.

**CS1929 seed example, independently re-verified live (not inferred from sealed-candidate evidence
alone):** fetched `src/Aspose.Email.Foss/Msg/Mime/MultipartParser.cs` directly from
`aspose-email-foss/Aspose.Email-FOSS-for-.Net`'s current default branch via the GitHub Contents
API. `SequenceEqualAscii` is now defined as a `private static bool SequenceEqualAscii(this
ReadOnlySpan<byte> value, string text)` extension method, and every call site
(`line.SequenceEqualAscii(...)`) is type-consistent with it — the receiver-type mismatch (`byte[]`
vs `ReadOnlySpan<byte>`) `idea.md:497-500` describes no longer exists. Confirmed fixed upstream, not
merely "the pipeline didn't happen to hit it." `plans/idea.md`'s own authority-note table now
carries this correction (new row, 2026-09-17) rather than rewriting the seed example's illustrative
prose.

## Scope caveats (honest, not hedged)

The decision-log archaeology pass was grep-anchored and sampled across ~6,980 combined lines, not
an exhaustive read of `DECISION_LOG.md`/`RESEARCH_AND_GUIDELINES.md` — high confidence on findings
2-4 above (directly verified against cited line numbers and code), but it did not verify whether
`EXECUTION_STATE_MACHINE.md` §12's obligation-mapping has drifted against the six workstreams added
this session (flagged as its own open question, not resolved here). The presentation-contract pass
covered the specific rules asked about, not every clause of `idea.md`'s "Portfolio README
Presentation Contract" section verbatim. Registry-intake code (how `RegistryRevisionV1`/
`data/registry.json` entries actually get populated at admission time) was not traced in this pass.

## Reverse by

`git revert` — pure documentation addition under `docs/investigations/`, no code or check coupling.
