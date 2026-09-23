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
KNOWN_BLOCKED_STALE = {
    "aspose-cells-foss__Aspose.Cells-FOSS-for-.NET": {
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
    "aspose-email-foss__Aspose.Email-FOSS-for-Python": {
        "reason": (
            "F07 (development_testing content gap) CONFIRMED FIXED by a fresh redraw, "
            "2026-09-23 - genuine BC-10 rejection now stands on a different finding, F08 "
            "(scope_limitations): a faithful paraphrase of one bullet of a bundled "
            "multi-item inherited_unit list fact that _cited_paraphrase cannot refute "
            "because its overlap ratio is computed against the fact's whole value, not the "
            "bullet the quote restates - the same mechanism already recorded for "
            "Aspose.Words-FOSS-for-.NET's F05; see comment above and docs/DECISION_LOG.md"
        ),
        "ref": (
            "docs/DECISION_LOG.md section 31 2026-09-23 09:59 UTC (this repository's own "
            "F08 reproduction) and section 31 2026-09-17 10:32 UTC (the first recorded "
            "instance, Aspose.Words-FOSS-for-.NET F05) - both share one resume predicate: "
            "a _cited_paraphrase fix scoped to the specific bullet a quote restates"
        ),
    },
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp": {
        "reason": (
            "G4-W17 item 44's command_block_tokens landing correctly wraps Aspose.Cells.Cpp.FOSS "
            "in backticks in one authored sentence (real identifier, spelled in a SUPPORTED "
            "command block); needs a real re-seal, not a code fix - see comment above"
        ),
        "ref": (
            "G4-W17 arrival item 44 (the rendering change); re-seal policy "
            "docs/DECISION_LOG.md section 31 2026-09-11 11:19 +05:00 - CURRENT keeps counting, "
            "one honest re-seal attempt Sunday only if it passes BC-02"
        ),
    },
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
    "aspose-3d-foss__Aspose.3D-FOSS-for-Java": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `UnsupportedOperationException` "
            "(scope_limitations, citing an inherited limitations list that spells it) - see "
            "comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    "aspose-3d-foss__Aspose.3D-FOSS-for-Python": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `NotImplementedError` (four "
            "occurrences, scope_limitations, citing an inherited limitations list that spells "
            "it) - see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Java": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `ChartEx` (scope_limitations "
            "limitation:2, citing inherited_unit:041.list, which spells it) - see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `LowCode`, "
            "`PlatformNotSupportedException`, `AcroForm`, and `NotImplementedException` "
            "(scope_limitations limitation:5, citing inherited_unit:227.list, which spells all "
            "four) - see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Java": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `LaTeX` and "
            "`UnsupportedOperationException` (scope_limitations limitation:1, citing "
            "inherited_unit:126.paragraph/127.list, which spell them) - see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    "aspose-slides-foss__Aspose.Slides-FOSS-for-Python": {
        "reason": (
            "item 69's cited_inherited_identifiers now wraps `PowerPoint`, `ValueError`, "
            "`SmartArt`, and `AttributeError` (scope_limitations scope, citing eight inherited "
            "facts spelling the old README's own limitations section, which spell all four) - "
            "see comment above"
        ),
        "ref": "G4-W17 arrival item 69; docs/DECISION_LOG.md section 31 2026-09-16 20:26 UTC",
    },
    # G4-W17 arrival item 113 (RESEARCH_AND_GUIDELINES.md section 29, lane D PROPOSAL P26) is the
    # same renderer-affecting class item 44/69 above already are: identifier_tokens gained a
    # slash-delimited module-path pattern, so a Go module path spelled bare in prose is one token,
    # not a dotted host next to a path. Aspose.Cells for Go's sealed bundle carries exactly the
    # measured shape in its documentation_resources line: "...available in the `github.com`/
    # aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26 package." (README.md line 418) now renders as
    # "...in the `github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26` package." - the split
    # identifier loop-prompt.md section 6 rule 8 names a defect closes; diff checked directly, one
    # code span moves, nothing else. A real, deliberate, correct rendering-behavior change, not a
    # regression - the candidate needs a real re-seal (through `present`, not a bare re-render) to
    # pick it up, since validation/review were judged against the old bytes; that re-seal is
    # separate follow-up work, not this fix's own scope. `strict=True` for the same reason as above.
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Go": {
        "reason": (
            "item 113's identifier_tokens now wraps the whole Go module path "
            "`github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26` as one code span "
            "(documentation_resources, README.md line 418) instead of splitting `github.com` "
            "from the rest of the path - see comment above"
        ),
        "ref": "G4-W17 arrival item 113; RESEARCH_AND_GUIDELINES.md section 29 lane D PROPOSAL P26",
    },
}


def _bundle_param(bundle: Path) -> Any:
    name = bundle.parent.name
    record = KNOWN_BLOCKED_STALE.get(name)
    marks = (
        [pytest.mark.xfail(reason=f"{record['reason']} [{record['ref']}]", strict=True)]
        if record
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
