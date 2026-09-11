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
# docs/DECISION_LOG.md). The candidate still cannot be sealed, but for a different, newly-surfaced,
# unrelated reason: F07, "the Development and Testing section omits the CI run details ... and
# release tagging convention ... present in the original" - not yet investigated, not RC-06's
# scope, needs its own taskcard. `strict=True` so an accidental future fix shows as XPASS (a
# failure) instead of silently staying invisible under an outdated xfail.
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
# Each record carries the debt's reason AND the reference owning its repayment (a work item,
# taskcard, arrival item, or dated DECISION_LOG section 31 entry) - tests/test_debt_ledger.py
# (PHASE1/F7) enforces both, so no entry can defer a re-seal to nobody again.
KNOWN_BLOCKED_STALE = {
    "aspose-email-foss__Aspose.Email-FOSS-for-Python": {
        "reason": (
            "genuine BC-10 rejection (F07, development_testing content gap) - unrelated to the "
            "original RC-06-targeted duplication, which is confirmed fixed; see comment above"
        ),
        "ref": (
            "PHASE0/EMAIL-PYTHON-F07 - the F07 content-gap record: diagnosed as an "
            "authoring-stage content-compression choice, docs/DECISION_LOG.md section 31 "
            "2026-09-10 12:23 UTC; re-seal queued in the sprint plan's re-run wave"
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
