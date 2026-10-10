"""section_authoring replies are bounded in length by the schema they are decoded under.

The defect (Aspose.Cells-FOSS-for-Rust, 2026-10-10, call 1c3187b2c77a): a unit's ``fact_ids`` array
repeated the four facts its slot may cite 212 times until ``finish_reason length`` at 8,000 tokens,
which fails the transaction with no re-ask. The per-slot ``enum`` bounded what an entry may be, not
how many there are, and the decoder cannot enforce uniqueness (HTTP 400 to ``uniqueItems``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    authoring_schema,
)
from repository_presenter.components.readme.composition.coherence import coherence_schema
from repository_presenter.components.readme.composition.output_bounds import (
    bound_authoring_citations,
)
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

LOADED = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
HUB = "hub:public_symbol:workbookmodel"
HUB_FACTS = frozenset(
    {
        "public_symbol:workbookmodel",
        "public_symbol:workbook",
        "public_symbol:workbook.new",
        "public_symbol:workbook.load_xlsx",
    }
)
TASK = SectionTask(
    "api_reference",
    {},
    HUB_FACTS | {"identity:repository", "public_symbol:worksheetmodel", "public_symbol:worksheet"},
    ("intro", HUB),
    slot_facts={
        "intro": frozenset(
            {
                "public_symbol:workbookmodel",
                "public_symbol:workbook",
                "public_symbol:worksheetmodel",
                "public_symbol:worksheet",
            }
        ),
        HUB: HUB_FACTS,
    },
)


def _truncated_reply() -> dict[str, Any]:
    """The retained Cells-Rust reply, trimmed (fixtures/1c3187b2c77a.rejected-1.json): the first
    unit and the hub unit with its repetition cut after twelve entries."""
    path = Path(__file__).parent / "fixtures" / "1c3187b2c77a.rejected-1.json"
    reply = json.loads(json.loads(path.read_text(encoding="utf-8"))["content"])
    assert isinstance(reply, dict)
    return reply


def _runaway(copies: int) -> dict[str, Any]:
    """The real shape at the scale it ran to: the hub unit's four facts, ``copies`` times over."""
    reply = _truncated_reply()
    cycle = list(dict.fromkeys(reply["units"][1]["fact_ids"]))
    assert set(cycle) == HUB_FACTS
    reply["units"][1]["fact_ids"] = cycle * copies
    return reply


def _legitimate() -> dict[str, Any]:
    reply = _truncated_reply()
    reply["units"][1]["fact_ids"] = sorted(HUB_FACTS)
    return reply


def test_the_unbounded_schema_admits_the_runaway_reply() -> None:
    """RED, the defect as it stood: every entry is a member of the slot's enum, so the reply was
    schema-valid at any length and nothing but the token budget ended it."""
    schema = authoring_schema(LOADED, TASK)
    assert Draft202012Validator(schema).is_valid(_runaway(212))


def test_a_unit_cannot_cite_more_facts_than_its_slot_may() -> None:
    schema = bound_authoring_citations(authoring_schema(LOADED, TASK), TASK)
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(_truncated_reply())  # twelve entries, four distinct facts
    assert not validator.is_valid(_runaway(212))
    assert validator.is_valid(_legitimate())


def test_each_slot_is_capped_at_its_own_citable_set() -> None:
    schema = bound_authoring_citations(authoring_schema(LOADED, TASK), TASK)
    caps = [
        entry["properties"]["fact_ids"]["maxItems"]
        for entry in schema["properties"]["units"]["prefixItems"]
    ]
    # intro: its four facts plus the neutral identity fact every unit may rest on; hub: the same.
    assert caps == [5, 5]


def test_a_legitimate_unit_that_cites_many_facts_is_not_cut_short() -> None:
    """The largest sealed unit cites 76 facts (an ``opening``); a slot that may cite them all keeps
    room for all of them."""
    ids = frozenset(f"public_symbol:thing{index:03}" for index in range(76))
    task = SectionTask("opening", {}, ids, ("opening",))
    schema = bound_authoring_citations(authoring_schema(LOADED, task), task)
    reply = {
        "units": [{"section": "opening", "slot": "opening", "text": "t", "fact_ids": sorted(ids)}],
        "omitted": [],
    }
    validator = Draft202012Validator(schema)
    assert validator.is_valid(reply)
    reply["units"][0]["fact_ids"] = [*sorted(ids), "public_symbol:thing000"]
    assert not validator.is_valid(reply)


def test_omitted_lists_each_fact_at_most_once() -> None:
    schema = bound_authoring_citations(authoring_schema(LOADED, TASK), TASK)
    validator = Draft202012Validator(schema)
    reason = {"fact_id": "public_symbol:worksheet", "reason": "Not needed by any unit."}
    base = _legitimate()
    assert validator.is_valid({**base, "omitted": [reason]})
    assert not validator.is_valid({**base, "omitted": [reason] * 40})


def test_bounding_never_mutates_the_schema_it_is_given_or_the_manifest() -> None:
    schema = authoring_schema(LOADED, TASK)
    snapshot = copy.deepcopy(schema)
    bound_authoring_citations(schema, TASK)
    assert schema == snapshot
    assert "maxItems" not in LOADED.manifest.output.schema_["properties"]["omitted"]


def test_a_task_without_slots_keeps_the_manifests_own_schema() -> None:
    task = SectionTask("opening", {}, frozenset({"identity:repository"}), ())
    schema = authoring_schema(LOADED, task)
    assert (
        bound_authoring_citations(schema, task)["properties"]["units"]
        == (schema["properties"]["units"])
    )


# --- the coherence call: one reply over every LLM-owned unit ---------------------------------


def test_the_coherence_call_caps_each_units_citations_at_its_largest_slots_set() -> None:
    units = [
        {"section": "api_reference", "slot": slot, "text": "t", "fact_ids": ["identity:repository"]}
        for slot in TASK.slots
    ]
    schema = coherence_schema(LOADED, units, [TASK])
    validator = Draft202012Validator(schema)
    properties = schema["properties"]["units"]["items"]["properties"]
    assert properties["fact_ids"]["maxItems"] == 5
    assert validator.is_valid({"units": units, "omitted": []})
    runaway = copy.deepcopy(units)
    runaway[1]["fact_ids"] = sorted(HUB_FACTS) * 50
    assert not validator.is_valid({"units": runaway, "omitted": []})
    reason = {"fact_id": "public_symbol:worksheet", "reason": "Not needed."}
    assert schema["properties"]["omitted"]["maxItems"] == len(TASK.accepted_ids)
    assert not validator.is_valid({"units": units, "omitted": [reason] * 40})
