"""Every sealed candidate still renders to the bytes it was sealed with.

A candidate's README is a pure function of its facts, plan, units and dispositions, so any change
to the renderer can be held to the documents already on disk without a clone, a provider call, or
a toolchain. This is the regression control a refactor of shared composition code answers to:
G4-W10 moved every ecosystem-specific spelling into `EcosystemSpec`, and the proof that it moved
nothing else is that the sealed bytes did not move (`RESEARCH_AND_GUIDELINES.md` §29.6 E4).

It is deliberately stronger than re-running the canary: it covers every sealed candidate, and it
cannot be satisfied by a stored reply, because nothing here calls a provider.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

CANDIDATES = REPO_ROOT / "candidates"
REGISTRY = REPO_ROOT / "data" / "registry.json"
# TB-07 part 3, external review D7, 2026-09-08: core/ecosystems.py's SPECS starts with only
# python and net; every other ecosystem's EcosystemSpec registers as a side effect of its own
# platforms/<ecosystem>.py module being imported somewhere, which normally happens via
# plugin_for() during a real `present` run. This file renders every sealed candidate directly,
# spanning every ecosystem in the portfolio, without going through `present` - run standalone
# (not as part of the full suite, which happens to import every platform module via some other
# test first), render_readme's own spec_for() calls failed closed with "no ecosystem spec
# registered" for anything beyond python/net. known_ecosystems() discovers every ecosystem by
# importing each platforms/*.py module (RESEARCH_AND_GUIDELINES.md section 29.6 E3's own
# discovery mechanism) - calling it once here registers every spec deterministically, with no
# ecosystem name hardcoded to go stale as the portfolio grows.
known_ecosystems()


def sealed_bundles() -> list[Path]:
    """Every bundle directory a CURRENT file points at."""
    bundles = []
    for current in sorted(CANDIDATES.glob("*/CURRENT")):
        revision = current.read_text("utf-8").strip()
        bundle = current.parent / revision
        if (bundle / "README.md").is_file():
            bundles.append(bundle)
    return bundles


def load_facts(path: Path) -> FactsDocument:
    """facts.json as the document the renderer takes; the seal wrote it, so it round-trips."""
    payload = json.loads(path.read_text("utf-8"))
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**entry) for entry in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(facts),
    )


def entry_for(repository: str) -> RegistryEntry:
    entries = json.loads(REGISTRY.read_text("utf-8"))["entries"]
    row = next(item for item in entries if item["repository"] == repository)
    return RegistryEntry.model_validate(row)


def read(bundle: Path, name: str) -> dict[str, Any]:
    loaded = json.loads((bundle / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_there_is_at_least_one_sealed_bundle_to_hold_the_renderer_to() -> None:
    assert sealed_bundles(), "no sealed candidate on disk; the control would pass vacuously"


# aspose-email-foss's real, correctly-triggered BC-10 rejection (duplicate class table + list,
# finding F03, docs/RECONCILIATION_COVERAGE_ASSESSMENT.md) blocked re-sealing it to current bytes.
# RC-06 (extraction-time unit-granularity redesign, plans/healing/production-consistency-
# reassessment.md) landed 2026-09-10 and was live-validated against this exact candidate: the
# original F03-shaped duplication is confirmed GONE from a real present run (no repeated table +
# list content, real method bullets under every hub including the mis-hubbed MapiMessage - see
# docs/DECISION_LOG.md). A later redraw (2026-09-23) confirms the next-surfaced blocker, F07
# ("the Development and Testing section omits the CI run details ... and release tagging
# convention ... present in the original"), is ALSO now fixed - the current content unit carries
# the CI/release detail F07 asked for. The candidate still cannot be sealed, but for a third,
# newly-surfaced, unrelated reason: F08 (scope_limitations) - see the ledger entry below and
# docs/DECISION_LOG.md's 2026-09-23 09:59 UTC entry for the full mechanical diagnosis.
# `strict=True` so an accidental future fix shows as XPASS (a failure) instead of silently
# staying invisible under an outdated xfail.
# G4-W17 arrival item 44 (docs/DECISION_LOG.md, 2026-09-11) is a renderer-affecting fix:
# allowed_identifiers() now also extracts identifiers from a
# SUPPORTED fact's own shell-command fence (command_block_tokens), not from an executed example
# alone. Aspose.Cells for C++'s sealed bundle already carries "nuget install
# Aspose.Cells.Cpp.FOSS" in a real, SUPPORTED inherited_unit code block (the package's own
# upstream README), so the package name is now a recognized identifier and one authored limitation
# sentence - "...published on NuGet as Aspose.Cells.Cpp.FOSS and requires..." - wraps it in
# backticks, matching how the upstream README's own inherited prose already spells the identical
# name elsewhere in this same candidate. One line changed (diff checked directly, not assumed);
# no other content moved. A real, deliberate, correct rendering-behavior change, not a regression -
# the candidate needs a real re-seal (through `present`, not a bare re-render) to pick it up, since
# validation/review were judged against the old bytes; that re-seal is separate follow-up work, not
# this fix's own scope. `strict=True` for the same reason as the entry above.
# G4-W17 arrival item 65 (lane C PROPOSAL AA, docs/DECISION_LOG.md section 31 2026-09-11) is a
# placement fix: placements() now covers every example the plan renders in any included section
# (placement.rendered_example_ids), not only the unit's own destination's content. Aspose.Cells for
# .NET's sealed bundle sent inherited_unit:018.paragraph ("Load a workbook with recovery
# diagnostics:") to Additional Examples citing example:002, which the plan renders as the second
# Quick Start example; the destination-only check placed it, and the sealed README carries the
# sentence at line 155 with no code block after it - a real, already-shipped content defect. Under
# the fix the unit is overlap and that line (with its blank line) is the only change to the
# re-rendered bytes (diff checked directly, not assumed). The bundle is deliberately NOT re-sealed
# or edited during the sprint (grandfathering ruling, section 31 2026-09-11 21:52 +05:00);
# re-verification is recorded post-sprint debt. `strict=True` as above.
# Each record carries the debt's reason AND the reference owning its repayment (a work item,
# taskcard, arrival item, or dated DECISION_LOG section 31 entry) - tests/test_debt_ledger.py
# (PHASE1/F7) enforces both, so no entry can defer a re-seal to nobody again.
# Each record also carries "since" (the date the bytes were first known to diverge) and "expires"
# (an ISO date). The xfail applies only up to and
# including "expires": the day after, the entry stops excusing the candidate and its test fails as
# a plain assertion, so the debt has to be repaid by a real re-seal (through `present`) or
# re-dated in a reviewed commit with the blocker re-checked - it can no longer age silently.
# Re-checked 2026-10-05 against the current sealed bundles: all three still render different
# bytes than they sealed with, so the blocker still holds.
KNOWN_BLOCKED_STALE = {
    "aspose-cells-foss__Aspose.Cells-FOSS-for-.NET": {
        "since": "2026-09-11",
        "expires": "2026-10-19",
        "reason": (
            "G4-W17 item 65's placement fix drops the orphaned lead-in 'Load a workbook with "
            "recovery diagnostics:' (inherited_unit:018.paragraph, sealed README line 155) whose "
            "example:002 the plan renders under Quick Start; the sealed bytes still carry the "
            "orphan - a shipped content defect the fix corrects, not re-sealed during the sprint "
            "- see comment above"
        ),
        "ref": (
            "G4-W17 arrival item 65 (lane C PROPOSAL AA); grandfathering ruling "
            "docs/DECISION_LOG.md section 31 2026-09-11 21:52 +05:00 - CURRENT keeps counting, "
            "re-verification of this one bundle is post-sprint debt"
        ),
    },
    # aspose-email-foss__Aspose.Email-FOSS-for-Python's entry here (F08, the _cited_paraphrase
    # whole-fact-denominator dilution - a faithful paraphrase of one bullet of a bundled
    # multi-item inherited_unit list fact scored below _PARAPHRASE_MIN_OVERLAP because the ratio
    # was computed against the fact's WHOLE value, not the bullet the quote restates) is removed
    # as of the shared-defect investigation fix (REVIEWER_LOGIC_VERSION 11 -> 12, new
    # _value_segments in review/independent/review.py, docs/DECISION_LOG.md section 31): this
    # candidate re-sealed READY_FOR_PROPOSAL with a fresh no-op proof, `review.json` verdict
    # ACCEPT, findings 0 - F08 does not recur. Leaving the entry would XPASS(strict) forever,
    # the same reasoning the PDF-.NET/PDF-Java removals below already establish.
    # aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp's entry here (G4-W17 item 44's
    # command_block_tokens rendering change) is removed as of the 2026-10-01 real re-seal
    # (docs/DECISION_LOG.md): the trigraph blocker that had kept this candidate from a real
    # re-seal since 2026-09-23 (BC-02/install_command:cmake UNRESOLVED under GCC/Clang) is closed
    # via a second, real toolchain (MSVC, cpp_examples.py::build_product/msvc_toolchain) built
    # without touching the target's own CMakeLists.txt/toolchain-detect.cmake; this candidate
    # re-sealed READY_FOR_PROPOSAL with a fresh, genuine no-op proof (zero provider calls,
    # byte-identical across two independent draws). Leaving the entry would XPASS(strict) forever,
    # the same reasoning the PDF-.NET/PDF-Java/Email-Python removals already establish.
    # G4-W17 arrival item 69 (docs/DECISION_LOG.md 2026-09-16 20:26 UTC) is a renderer-affecting
    # fix, the same class item 44 above already is: cited_inherited_identifiers lets a
    # scope_limitations unit spell an identifier its own cited SUPPORTED inherited_unit fact
    # spells verbatim, and renderer.prose now wraps exactly those tokens too, not only fact
    # values and verified members. Seven sealed candidates cite a broad inherited limitations
    # list for their own scope_limitations content and that list also spells (usually inside its
    # own backticks) a standard-library exception name or a product/format proper noun the
    # candidate's authored prose already used bare - each diff checked directly (not assumed):
    # exactly one or more identifiers gain a matching pair of backticks, nothing else in the
    # document moves. A real, deliberate, correct rendering-behavior change, not a regression -
    # each candidate needs a real re-seal (through `present`, not a bare re-render) to pick it up,
    # since validation/review were judged against the old bytes; that re-seal is separate
    # follow-up work, not this fix's own scope. `strict=True` for the same reason as above.
    # aspose-3d-foss__Aspose.3D-FOSS-for-Java's entry here (item 69's
    # `UnsupportedOperationException` wrapping, the same class as the siblings above) is removed
    # as of 2026-09-25: this candidate
    # re-sealed READY_FOR_PROPOSAL through a real `present` run (not a bare re-render) against
    # current component versions (normalisation, renderer, shell, and validators BC-02/03/04/06/
    # 07/08/10 all moved), reaching a genuinely new upstream revision
    # (3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3) with a fresh no-op proof (byte_identical true,
    # fresh_process true, provider_calls 0) and review verdict ACCEPT, 0 findings. The stored bytes
    # now come from current code, so a fresh render matches them again; leaving the entry would
    # XPASS(strict) forever, the same signal this file's own docstring says to act on.
    "aspose-3d-foss__Aspose.3D-FOSS-for-Python": {
        "since": "2026-09-16",
        "expires": "2026-10-19",
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `NotImplementedError` (four "
            "occurrences, scope_limitations, citing an inherited limitations list that spells "
            "it) - see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    # aspose-cells-foss__Aspose.Cells-FOSS-for-Java's entry here (item 69's `ChartEx` wrapping,
    # the same class as the siblings above) is removed as of 2026-09-24: this candidate drew a
    # genuinely new upstream revision (c65329e7..., which also carries the Maven Central publish
    # this repository was previously blocked on) and re-sealed READY_FOR_PROPOSAL with a fresh
    # no-op proof, past the Cells-Java authoring-hint duplication fix (docs/DECISION_LOG.md
    # 2026-09-24). The old revision's item-69 diff is moot for the new bundle; leaving the entry
    # would XPASS(strict) forever, since `sealed_bundles()` now follows CURRENT to the new
    # revision.
    # aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET's entry here (item 69's backtick-wrapping, the
    # same class as the siblings above) is removed as of 2026-09-23: this candidate had a real
    # re-seal (through `present`, not a bare re-render, exactly as the comment above requires),
    # landed READY_FOR_PROPOSAL with a fresh no-op proof - docs/DECISION_LOG.md section 31
    # 2026-09-23 11:45 UTC. The stored bytes now include item 69's fix, so a fresh render matches
    # them again; leaving the entry would XPASS(strict) forever, which is exactly the signal this
    # file's own docstring says to act on rather than silence.
    # aspose-pdf-foss__Aspose.PDF-FOSS-for-Java's entry here is removed as of 2026-09-23: this
    # candidate drew a genuinely new upstream revision (5a49de5d..., an upstream
    # /readme-refresh commit dated 2026-09-12, confirmed live via `gh api .../commits/<sha>` -
    # not merely the old revision replayed under new code) and sealed READY_FOR_PROPOSAL with a
    # fresh no-op proof - docs/DECISION_LOG.md section 31 2026-09-23 entry. The old revision's
    # item-69 diff is moot for the new bundle; leaving the entry would XPASS(strict) forever,
    # since `sealed_bundles()` now follows CURRENT to the new revision.
    "aspose-slides-foss__Aspose.Slides-FOSS-for-Python": {
        "since": "2026-09-16",
        "expires": "2026-10-19",
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `PowerPoint`, `ValueError`, "
            "`SmartArt`, and `AttributeError` (scope_limitations scope, citing eight inherited "
            "facts spelling the old README's own limitations section, which spell all four) - "
            "see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    # aspose-cells-foss__Aspose.Cells-FOSS-for-Go's entry here (item 113's Go module-path
    # wrapping, RESEARCH_AND_GUIDELINES.md section 29 lane D PROPOSAL P26) is removed as of
    # 2026-09-25: this candidate had a real re-seal (through `present`, not a bare re-render,
    # exactly as the comment previously here required), drawing the current upstream revision
    # (fa4e890e46c509efd22d09b97411202c2b0b8a67) and landing READY_FOR_PROPOSAL with a fresh
    # no-op proof (byte-identical, zero provider calls) and review verdict ACCEPT. The stored
    # bytes now include item 113's fix, so a fresh render matches them again; leaving the entry
    # would XPASS(strict) forever, exactly the signal this file's own docstring says to act on.
}


# Verification V2 items 8 and 9 (docs/DECISION_LOG.md section 31 2026-10-05): the template now
# title-cases an additional example's task heading (to_title_case) and collapses any run of empty
# lines outside a fence (collapse_document_blank_runs), so each candidate below - sealed with a
# sentence-case task heading, a repeated empty-line run, or both - re-renders to bytes that differ
# from its sealed README in exactly those lines (diff checked directly: heading lines only, and one
# empty line, nothing else moves). BC-07 v8 judges the same two rules, so the sealed bytes would
# newly fail it; re-rendering from the sealed artifacts passes it with zero provider calls. A real
# re-seal (through `present`) picks the change up; that is separate, owner-sequenced work. The three
# candidates that already carry an entry above stay as recorded: their earlier causes persist.
#
# aspose-cells-foss__Aspose.Cells-FOSS-for-Python's entry here is removed as of 2026-10-08: this
# candidate had a real re-seal (through `present`, not a bare re-render), landing READY_FOR_PROPOSAL
# with a fresh no-op proof (byte-identical, zero provider calls) and review verdict ACCEPT, 0
# findings. The stored bytes now include the V2 items 8/9 fix, so a fresh render matches them
# again; leaving the entry would XPASS(strict) forever, exactly the signal this file's own
# docstring says to act on.
def _merge_ledger(name: str, *, since: str, expires: str, reason: str, ref: str) -> None:
    """Record one bundle's block. Two blocks on the same bundle merge into one record: the later
    `since` and `expires` win, and both reasons and both references are kept, so no entry is
    dropped and no earlier cause is lost."""
    old = KNOWN_BLOCKED_STALE.get(name)
    if old is None:
        KNOWN_BLOCKED_STALE[name] = {
            "since": since,
            "expires": expires,
            "reason": reason,
            "ref": ref,
        }
        return
    KNOWN_BLOCKED_STALE[name] = {
        "since": max(str(old.get("since", "")), since),
        "expires": max(str(old.get("expires", "")), expires),
        "reason": f"{old['reason']}; {reason}",
        "ref": f"{old['ref']}; {ref}",
    }


_V2_ITEM_8_9_REASON = (
    "the template now title-cases the additional-examples task heading and collapses an empty-line "
    "run outside a fence (V2 items 8 and 9, BC-07 v8): the sealed bytes carry a sentence-case task "
    "heading and/or a repeated empty-line run; a re-render differs in those lines only - see "
    "comment above"
)
_V2_ITEM_8_9_NAMES = (
    "aspose-font-foss__Aspose.Font-FOSS-for-Python",
    "aspose-3d-foss__Aspose.3D-FOSS-for-.NET",
    "aspose-3d-foss__Aspose.3D-FOSS-for-Java",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Go",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Java",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Rust",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript",
    "aspose-email-foss__Aspose.Email-FOSS-for-.Net",
    "aspose-email-foss__Aspose.Email-FOSS-for-Python",
    "aspose-html-foss__Aspose.HTML-FOSS-for-Python",
    "aspose-note-foss__Aspose.Note-FOSS-for-Python",
    "aspose-page-foss__Aspose.Page-FOSS-for-Python",
    "aspose-pdf-foss__Aspose-PDF-FOSS-for-Go",
    "aspose-pdf-foss__Aspose-PDF-FOSS-for-Python",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Java",
    "aspose-slides-foss__Aspose.Slides-FOSS-for-Java",
)
_V2_ITEM_8_9_REF = "docs/DECISION_LOG.md section 31 2026-10-05 (verification V2 items 8 and 9)"
for _name in _V2_ITEM_8_9_NAMES:
    _merge_ledger(
        _name,
        since="2026-10-05",
        expires="2026-11-04",
        reason=_V2_ITEM_8_9_REASON,
        ref=_V2_ITEM_8_9_REF,
    )
# plans/idea.md links, anchor, and badge rules (docs/DECISION_LOG.md section 31 2026-10-05, renderer
# 27): the badge row is derived from verified facts per ecosystem in the stable order (a runtime
# badge for .NET/Java/Go/C++/Rust/Node floors, not Python alone; the contributors badge only when
# the source README's own target resolved; a build-status badge only for a verified workflow), and
# the Enterprise Edition anchor reads "full-featured <product> - Enterprise Edition". Each bundle
# below differs from a fresh render in exactly those spans (diff checked per bundle, not assumed).
# A real, deliberate, correct rendering-behavior change; each needs a real re-seal through `present`
# to pick it up, since validation/review were judged against the old bytes. `strict=True` as above.
_LINKS_ANCHOR_BADGES_STALE = (
    "aspose-3d-foss__Aspose.3D-FOSS-for-.NET",
    "aspose-3d-foss__Aspose.3D-FOSS-for-Java",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Go",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Java",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Rust",
    "aspose-cells-foss__Aspose.Cells-FOSS-for-TypeScript",
    "aspose-email-foss__Aspose.Email-FOSS-for-.Net",
    "aspose-email-foss__Aspose.Email-FOSS-for-Cpp",
    "aspose-email-foss__Aspose.Email-FOSS-for-Python",
    "aspose-html-foss__Aspose.HTML-FOSS-for-Python",
    "aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET",
    "aspose-note-foss__Aspose.Note-FOSS-for-Python",
    "aspose-page-foss__Aspose.Page-FOSS-for-Python",
    "aspose-pdf-foss__Aspose-PDF-FOSS-for-Go",
    "aspose-pdf-foss__Aspose-PDF-FOSS-for-Python",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp",
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Java",
    "aspose-slides-foss__Aspose.Slides-FOSS-for-.NET",
    "aspose-slides-foss__Aspose.Slides-FOSS-for-Cpp",
    "aspose-slides-foss__Aspose.Slides-FOSS-for-Java",
    "aspose-words-foss__Aspose.Words-FOSS-for-.NET",
    "aspose-words-foss__Aspose.Words-FOSS-for-Python",
)
for _name in _LINKS_ANCHOR_BADGES_STALE:
    _merge_ledger(
        _name,
        since="2026-10-05",
        expires="2026-11-04",
        reason=(
            "renderer 27: the badge row derives per ecosystem from verified facts in the stable "
            "order (runtime badge, contributors only when verified) and the Enterprise Edition "
            "anchor opens 'full-featured' - see comment above"
        ),
        ref="G4-W17 links, anchor and badges rules; docs/DECISION_LOG.md section 31 2026-10-05",
    )


def block_is_live(record: dict[str, str], today: dt.date) -> bool:
    """Whether a ledger record still excuses its candidate: true through its `expires` date."""
    return today <= dt.date.fromisoformat(record["expires"])


def _bundle_param(bundle: Path) -> Any:
    name = bundle.parent.name
    record = KNOWN_BLOCKED_STALE.get(name)
    marks = (
        [
            pytest.mark.xfail(
                reason=f"{record['reason']} [{record['ref']}] (blocked since {record['since']}, "
                f"expires {record['expires']})",
                strict=True,
            )
        ]
        if record and block_is_live(record, dt.date.today())
        else []
    )
    return pytest.param(bundle, marks=marks, id=name)


@pytest.mark.parametrize("bundle", [_bundle_param(bundle) for bundle in sealed_bundles()])
def test_a_sealed_candidate_renders_to_its_own_bytes(bundle: Path) -> None:
    facts = load_facts(bundle / "facts.json")
    rendered = render_readme(
        entry_for(facts.repository),
        facts,
        read(bundle, "plan.json"),
        read(bundle, "content_units.json"),
        read(bundle, "dispositions.json"),
    )
    stored = (bundle / "README.md").read_text("utf-8")
    assert rendered == stored, f"{bundle.parent.name} no longer renders the bytes it sealed with"


def test_every_blocked_entry_carries_a_bounded_dated_expiry() -> None:
    """A recorded block names when it began and when it stops excusing the candidate."""
    for name, record in KNOWN_BLOCKED_STALE.items():
        since = dt.date.fromisoformat(record["since"])
        expires = dt.date.fromisoformat(record["expires"])
        assert since < expires <= since + dt.timedelta(days=60), (
            f"{name}: expiry {expires} must fall after since {since} and within 60 days of it"
        )


def test_a_block_stops_excusing_its_candidate_the_day_after_it_expires() -> None:
    record = {"expires": "2026-10-19"}
    assert block_is_live(record, dt.date(2026, 10, 19))
    assert not block_is_live(record, dt.date(2026, 10, 20))
