"""Every recorded debt names the work item that owns paying it down.

Two ledgers defer real re-seal work: ``KNOWN_BLOCKED_STALE`` in ``test_sealed_bytes.py`` (a
sealed candidate that no longer renders its own bytes, xfailed for a recorded reason) and a
manifest sitting at ``VALID_UPDATE_AVAILABLE`` (a factual update recorded but not yet adopted,
docs/STATE_MACHINE.md sections 5 and 9). Debt with a reason but no owner silently ages - the
Email-Python F07 gap sat "not yet investigated, needs its own taskcard" in a test comment until a
Phase 0 row picked it up by hand. PHASE1/F7's rule, mechanical: every such entry carries a
work-item, taskcard, arrival-item, or dated DECISION_LOG section 31 reference, so nothing is
deferred to nobody (the sprint plan's own rollback row: a broken re-seal becomes a
``KNOWN_BLOCKED_STALE`` entry WITH a card ref - this test is what enforces the WITH).

The seal transaction owns manifest bytes and F7 owns ``tests/`` alone, so the update-available
ledger lives here: a bundle moved to ``VALID_UPDATE_AVAILABLE`` fails this suite until whoever
moved it records the owning item in ``VALID_UPDATE_AVAILABLE_REFS``, exactly as a new xfail entry
fails until its record carries a ref.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from test_sealed_bytes import KNOWN_BLOCKED_STALE, read, sealed_bundles

# The reference forms the repository's own governance records use: a work item (G4-W17), a
# phase taskcard (PHASE0/EMAIL-PYTHON-F07, PHASE1/F7), an arrival item from section 29's G4-W17
# list ("arrival item 44"), or a dated DECISION_LOG section 31 entry.
REFERENCE = re.compile(
    r"(G\d+-W\d+|PHASE\d+/[A-Z0-9-]+|arrival item \d+|section 31 \d{4}-\d{2}-\d{2})"
)

# One row per bundle whose manifest state is VALID_UPDATE_AVAILABLE: bundle directory name -> the
# reference owning the update's resolution or adoption. Empty today: no sealed bundle is at that
# state (the sweep below verifies this against the manifests on disk, so the emptiness is
# re-checked every run, never assumed).
VALID_UPDATE_AVAILABLE_REFS: dict[str, str] = {}


def unreferenced(states: Mapping[str, str], refs: Mapping[str, str]) -> list[str]:
    """The VALID_UPDATE_AVAILABLE bundles that no valid work-item reference covers."""
    return sorted(
        name
        for name, state in states.items()
        if state == "VALID_UPDATE_AVAILABLE" and not REFERENCE.search(refs.get(name, ""))
    )


def bundle_states() -> dict[str, str]:
    """Each sealed candidate's manifest state, read from disk."""
    return {
        bundle.parent.name: str(read(bundle, "manifest.json").get("state"))
        for bundle in sealed_bundles()
    }


def test_every_known_blocked_stale_entry_names_its_owning_item() -> None:
    for name, record in KNOWN_BLOCKED_STALE.items():
        assert record["reason"].strip(), f"{name}: its ledger record carries no reason"
        assert REFERENCE.search(record["ref"]), (
            f"{name}: its ref names no work item, taskcard, arrival item, or dated section 31"
            f" entry: {record['ref']!r}"
        )


def test_every_ledger_row_names_a_sealed_candidate() -> None:
    """A row for a candidate that is not sealed on disk is a record referring to nothing."""
    sealed = {bundle.parent.name for bundle in sealed_bundles()}
    for ledger in (KNOWN_BLOCKED_STALE, VALID_UPDATE_AVAILABLE_REFS):
        stray = sorted(set(ledger) - sealed)
        assert stray == [], f"ledger rows name no sealed candidate on disk: {stray}"


def test_every_update_available_bundle_carries_a_work_item_reference() -> None:
    assert unreferenced(bundle_states(), VALID_UPDATE_AVAILABLE_REFS) == []


def test_no_update_ledger_row_outlives_its_update() -> None:
    """A resolved or adopted update's row comes out of the ledger with it."""
    states = bundle_states()
    outlived = sorted(
        name for name in VALID_UPDATE_AVAILABLE_REFS if states.get(name) != "VALID_UPDATE_AVAILABLE"
    )
    assert outlived == [], f"update ledger rows for bundles no longer at that state: {outlived}"


def test_an_update_available_bundle_with_no_reference_is_flagged() -> None:
    """The sweep is verified against a synthetic ledger: red without a ref, green with one."""
    states = {"repo__X": "VALID_UPDATE_AVAILABLE", "repo__Y": "READY_FOR_PROPOSAL"}
    assert unreferenced(states, {}) == ["repo__X"]
    assert unreferenced(states, {"repo__X": "G4-W17 arrival item 44"}) == []
    assert unreferenced(states, {"repo__X": "no owner named"}) == ["repo__X"]
