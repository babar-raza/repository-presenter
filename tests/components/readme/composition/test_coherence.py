"""The coherence pass: one call over the document, every unit back, each held to its section."""

from __future__ import annotations

import copy
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.authoring import SectionTask
from repository_presenter.components.readme.composition.coherence import (
    _COHERENCE_BATCH_UNITS,
    apply_coherence,
    coherence_batch_units,
    coherence_batches,
    coherence_checks,
    coherence_citable_ids,
    coherence_packet,
    coherence_schema,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
NAME = "Aspose.3D FOSS for Python"
FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),
        Fact(
            "public_symbol:aspose.threed.scene",
            "public_symbol",
            "aspose.threed.Scene",
            (Evidence("x", "line 1; class; public by name"),),
        ),
        Fact("format:output.glb", "format", ".glb", (Evidence("x"),)),
        Fact("format:input.obj", "format", ".obj", (Evidence("x"),), polarity="UNRESOLVED"),
    ),
)
TASKS = [
    SectionTask(
        "opening", {}, frozenset({"identity:repository", "format:output.glb"}), ("opening",)
    ),
    SectionTask(
        "key_capabilities",
        {},
        frozenset({"identity:repository", "public_symbol:aspose.threed.scene"}),
        ("capability:1",),
    ),
]
UNITS: dict[str, Any] = {
    "schema_version": 1,
    "units": [
        {
            "section": "opening",
            "slot": "opening",
            "text": "It writes GLB.",
            "fact_ids": ["format:output.glb"],
        },
        {
            "section": "key_capabilities",
            "slot": "capability:1",
            "text": "Scene builds scenes.",
            "fact_ids": ["public_symbol:aspose.threed.scene"],
        },
    ],
    "omitted": [],
}


def test_the_packet_carries_the_document_every_unit_and_the_union_of_facts() -> None:
    packet = coherence_packet(ENTRY, "# Doc\n", UNITS, TASKS, FACTS)
    assert packet["mode"] == "coherence" and packet["section_id"] == "all"
    assert packet["rendered_document"] == "# Doc\n"
    assert packet["existing_units"] == UNITS["units"]
    assert [f["id"] for f in packet["accepted_facts"]] == [
        "format:output.glb",
        "identity:repository",
        "public_symbol:aspose.threed.scene",
    ]
    assert "opening/opening, key_capabilities/capability:1" in packet["objective"]
    assert "aspose.threed.Scene, Scene" in packet["objective"]
    assert [f["id"] for f in packet["do_not_claim"]] == ["format:input.obj"]
    assert packet["product_name"] == NAME


def test_checks_hold_every_returned_unit_to_its_sections_rules() -> None:
    assert coherence_checks(UNITS, TASKS, FACTS, NAME) == []
    bad = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "See `GLB`",
                "fact_ids": ["format:output.glb"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Scene builds scenes.",
                "fact_ids": ["format:output.glb"],
            },
            {"section": "license", "slot": "prose", "text": "x", "fact_ids": []},
        ],
        "omitted": [],
    }
    errors = coherence_checks(bad, TASKS, FACTS, NAME)
    assert errors == [
        "units name a section the plan did not author: license",
        "unit capability:1: cites facts outside this section's set: format:output.glb",
    ]
    assert bad["units"][0]["text"] == "See GLB"  # the span is dropped; the renderer owns spans
    missing = {"units": UNITS["units"][:1], "omitted": []}
    assert coherence_checks(missing, TASKS, FACTS, NAME) == [
        "units must fill exactly these slots once each: capability:1; got "
    ]


def test_apply_records_which_units_changed_and_keeps_the_rest() -> None:
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "It writes GLB files.",
                "fact_ids": ["format:output.glb"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Scene builds scenes.",
                "fact_ids": ["public_symbol:aspose.threed.scene"],
            },
        ],
        "omitted": [],
    }
    document, revised = apply_coherence(UNITS, output)
    assert revised == ["opening/opening"]
    assert document["units"][0]["text"] == "It writes GLB files."
    assert document["units"][1] == UNITS["units"][1]
    assert document["coherence"] == {"applied": True, "revised": ["opening/opening"]}
    unchanged, none = apply_coherence(UNITS, {"units": UNITS["units"], "omitted": []})
    assert none == [] and unchanged["units"] == UNITS["units"]


def test_the_schema_binds_the_call_to_exactly_the_units_it_was_given() -> None:
    # G4-W17 arrival item 75 (lane F F23, lane B LANE-B-W14R2-F1): the coherence call returns
    # every LLM-owned unit in the document at once - the largest single section_authoring reply
    # by construction - and had no maxItems of its own, unlike a per-task authoring call
    # (authoring_schema already binds those to the plan's own slot count). A schema-valid reply
    # can no longer drop, duplicate, or invent a unit; the manifest's own text/omitted length
    # bounds (item 75's other half) come along unchanged since this deep-copies the same schema.
    loaded = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
    schema = coherence_schema(loaded, UNITS["units"], TASKS)
    units = schema["properties"]["units"]
    assert units["minItems"] == units["maxItems"] == 2
    assert units["items"]["properties"]["text"]["maxLength"] == 2200

    validator = Draft202012Validator(schema)
    assert validator.is_valid({"units": UNITS["units"], "omitted": []})
    one_only = {"units": UNITS["units"][:1], "omitted": []}
    assert not validator.is_valid(one_only)
    too_long = {
        "units": [{**UNITS["units"][0], "text": "x" * 2201}, UNITS["units"][1]],
        "omitted": [],
    }
    assert not validator.is_valid(too_long)

    # An empty document (nothing to revise) leaves the manifest's own minItems: 1 alone rather
    # than asking for a schema no reply could ever satisfy.
    empty_schema = coherence_schema(loaded, [], TASKS)
    assert empty_schema["properties"]["units"]["minItems"] == 1
    assert "maxItems" not in empty_schema["properties"]["units"]


def test_coherence_citable_ids_is_the_union_of_every_non_batch_tasks_accepted_ids() -> None:
    batch = SectionTask(
        "api_reference",
        {},
        frozenset({"public_symbol:aspose.threed.scene"}),
        ("type:public_symbol:aspose.threed.scene",),
        key="api_reference#types-1",
    )
    assert coherence_citable_ids([*TASKS, batch]) == [
        "format:output.glb",
        "identity:repository",
        "public_symbol:aspose.threed.scene",
    ]


def test_the_schema_bounds_fact_ids_to_what_any_returned_unit_could_legitimately_cite() -> None:
    # G4-W17 arrival item 123: item 75 bounded the units array to an exact count, but left every
    # unit's own fact_ids wholly unbounded - the one section_authoring call site (of the five
    # shapes: S3, S4's per-entry calls, S5, S6's per-task calls) that never got the per-kind bound
    # treatment authoring_schema/reconciliation_schema already apply, and structurally the single
    # largest section_authoring reply in the pipeline. Mirrors reconciliation_schema's own shared,
    # per-call enum (dispositions.citable_fact_ids): one enum covering everything any of this
    # call's many different units could legitimately cite, not a maxItems count alone - a count
    # bound without a citable-ID enum still lets a runaway completion spend its budget on
    # well-formed but wrong IDs (item 121's own reasoning).
    loaded = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
    schema = coherence_schema(loaded, UNITS["units"], TASKS)
    items = schema["properties"]["units"]["items"]["properties"]["fact_ids"]["items"]
    assert items == {
        "type": "string",
        "enum": ["format:output.glb", "identity:repository", "public_symbol:aspose.threed.scene"],
    }
    # The manifest itself is untouched: the specialisation is per call, never a shared mutation.
    assert loaded.manifest.output.schema_["properties"]["units"]["items"]["properties"][
        "fact_ids"
    ] == {"type": "array", "minItems": 1, "items": {"type": "string"}}

    validator = Draft202012Validator(schema)
    valid = {"units": UNITS["units"], "omitted": []}
    assert validator.is_valid(valid)

    def _with_fact_ids(*fact_ids: str) -> dict[str, Any]:
        return {
            "units": [
                {**UNITS["units"][0], "fact_ids": list(fact_ids)},
                UNITS["units"][1],
            ],
            "omitted": [],
        }

    # RED (pre-fix behaviour, still true of the manifest's own bare schema): an invented ID that
    # names no fact at all, and an excessive number of well-formed-but-uncitable repeats, both
    # validated against the unbounded fact_ids the manifest alone provides.
    bare_schema = copy.deepcopy(loaded.manifest.output.schema_)
    bare_validator = Draft202012Validator(bare_schema)
    invented = _with_fact_ids("public_symbol:does_not_exist")
    runaway = _with_fact_ids(*(["public_symbol:"] * 50))
    assert bare_validator.is_valid(invented)
    assert bare_validator.is_valid(runaway)

    # GREEN (this fix): the same two replies are now rejected against coherence_schema's own
    # specialised output.
    assert not validator.is_valid(invented)
    assert not validator.is_valid(runaway)
    assert [error.json_path for error in validator.iter_errors(invented)] == [
        "$.units[0].fact_ids[0]"
    ]
    assert [error.json_path for error in validator.iter_errors(runaway)] == [
        f"$.units[0].fact_ids[{i}]" for i in range(50)
    ]


def test_a_call_with_nothing_citable_pins_fact_ids_empty_rather_than_an_empty_enum() -> None:
    loaded = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
    schema = coherence_schema(loaded, [], [])
    fact_ids = schema["properties"]["units"]["items"]["properties"]["fact_ids"]
    assert fact_ids == {"type": "array", "maxItems": 0}


# PDFPY-03 (docs/DECISION_LOG.md 2026-09-17 09:18 UTC, corroborated 2026-09-24 14:20 UTC): a single
# coherence call asking for every LLM-owned unit back at once has no bound on its own completion
# size and truncates at the shared max_output_tokens=8000 cap once a document carries enough units
# (measured live: 47 on PDF-Python, more on Font-Python) - the whole transaction aborts before any
# README or validation is produced. The tests below cover coherence_batches/coherence_batch_units,
# the fix: a document this small still gets exactly the old one-call shape (no regression), while a
# document large enough to have truncated the old way now splits into several calls, each one's own
# schema-forced reply bounded well under the cap regardless of the document's total size.


def _big_task(number: int, slot_count: int) -> SectionTask:
    slots = tuple(f"slot:{i}" for i in range(slot_count))
    return SectionTask(f"section{number}", {}, frozenset({"identity:repository"}), slots)


# Six sections, slot counts 3/4/2/4/3/4 = 20 units total - comfortably past _COHERENCE_BATCH_UNITS
# (16), the same order of magnitude as the 47-unit document that actually truncated in production.
BIG_TASKS = [_big_task(number, count) for number, count in enumerate([3, 4, 2, 4, 3, 4], start=1)]
BIG_UNITS: dict[str, Any] = {
    "schema_version": 1,
    "units": [
        {
            "section": task.section_id,
            "slot": slot,
            # Plain prose only - no colon-shaped tokens that unit_checks' identifier guard would
            # mistake for an unaccepted API name.
            "text": "The package behaves as documented here.",
            "fact_ids": ["identity:repository"],
        }
        for task in BIG_TASKS
        for slot in task.slots
    ],
    "omitted": [],
}
BIG_FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),),
)


def test_a_small_document_still_gets_exactly_one_batch_no_regression() -> None:
    """The existing small TASKS fixture (2 units) must keep the pre-PDFPY-03 shape exactly: one
    batch, carrying every task, so a normal-sized candidate makes the same single coherence call
    it always did."""
    batches = coherence_batches(TASKS)
    assert batches == [("coherence#1", TASKS)]


def test_a_large_document_splits_into_several_batches_never_splitting_one_sections_own_slots() -> (
    None
):
    batches = coherence_batches(BIG_TASKS)
    # Greedy accumulation: 3+4+2+4+3 = 16 (exactly at the cap, still one batch), then +4 would be
    # 20 > 16, so section6 starts a new batch.
    assert [batch_id for batch_id, _ in batches] == ["coherence#1", "coherence#2"]
    first_tasks, second_tasks = (group for _, group in batches)
    assert first_tasks == BIG_TASKS[:5]
    assert second_tasks == BIG_TASKS[5:]
    # No batch's own total slot count ever exceeds the cap - the mechanism that keeps every
    # single call's reply within budget regardless of how large the whole document grows.
    for _, group in batches:
        assert sum(len(task.slots) for task in group) <= _COHERENCE_BATCH_UNITS
    # Every task appears in exactly one batch, document order preserved, nothing dropped.
    assert [task for _, group in batches for task in group] == BIG_TASKS


def test_a_batchs_own_call_still_sees_the_whole_document_for_cross_batch_context() -> None:
    """Cross-batch consistency must not be silently dropped: a later batch's own packet still
    carries every current unit and the full rendered document, even though its schema-forced
    reply is narrowed to its own batch."""
    _, second_batch_tasks = coherence_batches(BIG_TASKS)[1]
    packet = coherence_packet(ENTRY, "# Doc\n", BIG_UNITS, second_batch_tasks, BIG_FACTS)
    # Full-document context: every one of the 20 units, not just section6's own 4.
    assert len(packet["existing_units"]) == len(BIG_UNITS["units"]) == 20
    assert packet["rendered_document"] == "# Doc\n"
    # But the schema-forced reply this call must return is narrowed to section6's own slots only.
    assert (
        "Units to return, each exactly once: section6/slot:0, section6/slot:1"
        in (packet["objective"])
    )
    assert "section1/slot:0" not in packet["objective"]
    return_units = coherence_batch_units(packet["existing_units"], second_batch_tasks)
    assert {(u["section"], u["slot"]) for u in return_units} == {
        ("section6", slot) for slot in second_batch_tasks[0].slots
    }
    # The schema this call actually gets bounds the reply to those 4 units, not all 20 - unlike
    # the pre-fix single-call design, which would have demanded all 20 back in this one reply.
    loaded = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
    schema = coherence_schema(loaded, return_units, second_batch_tasks)
    units_schema = schema["properties"]["units"]
    assert units_schema["minItems"] == units_schema["maxItems"] == 4


def test_a_document_too_large_for_one_call_completes_via_several_bounded_calls() -> None:
    """End-to-end (offline, no provider call): drive coherence_batches/coherence_packet/
    coherence_schema/coherence_checks/apply_coherence the same sequential way repair/rounds.py's
    own loop does, over BIG_TASKS/BIG_UNITS - a document this size (20 units) would have been sent
    as one 20-unit reply under the pre-PDFPY-03 design; here every call's own schema-validated
    reply is confirmed small, and the final merged document still carries every unit, correctly
    revised, with nothing lost or duplicated across batches."""
    units = BIG_UNITS
    readme = "# Doc\n"
    revised: list[str] = []
    calls = 0
    loaded = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
    for batch_id, batch_tasks in coherence_batches(BIG_TASKS):
        calls += 1
        packet = coherence_packet(ENTRY, readme, units, batch_tasks, BIG_FACTS)
        return_units = coherence_batch_units(packet["existing_units"], batch_tasks)
        schema = coherence_schema(loaded, return_units, batch_tasks)
        # This call's own reply may never ask for more than the batch's own units - the exact
        # property that keeps the reply's completion size bounded no matter how large the whole
        # document is.
        assert schema["properties"]["units"]["maxItems"] <= _COHERENCE_BATCH_UNITS
        # A genuine revision, scoped to exactly this batch's own units - proving the model could
        # legitimately revise its own section without ever seeing (or needing to return) another
        # batch's units in this same reply.
        output = {
            "units": [{**unit, "text": unit["text"] + " REVISED"} for unit in return_units],
            "omitted": [],
        }
        validator = Draft202012Validator(schema)
        assert validator.is_valid(output), (
            f"{batch_id} reply invalid: {list(validator.iter_errors(output))}"
        )
        errors = coherence_checks(output, batch_tasks, BIG_FACTS, NAME)
        assert errors == []
        units, batch_revised = apply_coherence(units, output)
        revised.extend(batch_revised)
    assert calls == 2  # confirms this document genuinely needed more than the old one call
    assert len(revised) == 20
    assert all(unit["text"].endswith(" REVISED") for unit in units["units"])
    assert {(u["section"], u["slot"]) for u in units["units"]} == {
        (task.section_id, slot) for task in BIG_TASKS for slot in task.slots
    }
