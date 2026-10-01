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
    coherence_content_loss_errors,
    coherence_packet,
    coherence_schema,
    recover_coherence_content_loss,
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


# G3-W05 (docs/DEFECT_INDEX.md composition.coherence.inherited_diagram_content_loss): S8 coherence
# had no recover= at all, and no deterministic check existed for a coherence revision silently
# dropping a named capability/structure/input-output detail the pre-coherence unit carried - only
# whichever draw's independent-review sample happened to notice it. The two tests below reproduce
# the exact shape each of the two corroborated 2026-09-27 sightings hit, at the one level S8
# coherence can actually touch (a unit's own text/fact_ids, pre- vs post-revision) - never a
# comparison against the original upstream README itself, which this stage has no access to.

SLIDES_JAVA_FACTS = FactsDocument(
    "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
    "a" * 40,
    (
        Fact(
            "identity:repository",
            "identity",
            "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
            (Evidence("x"),),
        ),
        Fact("format:output.xml", "format", ".xml", (Evidence("x"),)),
        Fact("format:output.pptx", "format", ".pptx", (Evidence("x"),)),
    ),
)
SLIDES_JAVA_EXISTING: list[dict[str, Any]] = [
    {
        "section": "key_capabilities",
        "slot": "capability:1",
        "text": "Convert slides to PPTX or export the whole structure to XML for round-tripping.",
        "fact_ids": ["format:output.pptx", "format:output.xml"],
    }
]


def test_sighting_slides_java_f02_diagram_shaped_loss_of_an_xml_output_reference() -> None:
    """docs/DECISION_LOG.md 2026-09-27 05:14 UTC entry / docs/DEFECT_INDEX.md row 1
    (aspose-slides-foss/Aspose.Slides-FOSS-for-Java): independent review's F02 found the
    candidate's own at_a_glance-adjacent capability content "omits specific capabilities and the
    input/output structure the original's diagram carried." Reproduced at the unit level coherence
    can actually touch: the pre-coherence unit names both the PPTX and XML output structure; the
    post-coherence "simplification" keeps PPTX but drops XML and its own citation entirely, with
    no trace of it anywhere in the revised text."""
    revised = [
        {
            "section": "key_capabilities",
            "slot": "capability:1",
            "text": "Convert slides to PPTX for sharing with other presentation tools.",
            "fact_ids": ["format:output.pptx"],
        }
    ]
    errors = coherence_content_loss_errors(revised, SLIDES_JAVA_EXISTING, SLIDES_JAVA_FACTS)
    assert errors == [
        "key_capabilities/capability:1: coherence revision drops the previously-cited format "
        "'format:output.xml' and none of its own content ('.xml') remains in the revised text - "
        "a named capability, format, or structural detail the prior version carried must not be "
        "silently dropped during coherence"
    ]
    corrected = recover_coherence_content_loss(
        {"units": [dict(unit) for unit in revised]},
        existing_units=SLIDES_JAVA_EXISTING,
        facts=SLIDES_JAVA_FACTS,
    )
    assert corrected is not None
    assert corrected["units"][0]["text"] == SLIDES_JAVA_EXISTING[0]["text"]
    assert corrected["units"][0]["fact_ids"] == SLIDES_JAVA_EXISTING[0]["fact_ids"]
    # The recovered output is clean of this exact check - run_job's own re-validation would accept
    # it (never accepted on recover='s own say-so, per core/llm/jobs.py's own contract).
    assert (
        coherence_content_loss_errors(corrected["units"], SLIDES_JAVA_EXISTING, SLIDES_JAVA_FACTS)
        == []
    )


SLIDES_NET_FACTS = FactsDocument(
    "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET",
    "b" * 40,
    (
        Fact(
            "identity:repository",
            "identity",
            "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET",
            (Evidence("x"),),
        ),
        Fact(
            "public_symbol:aspose.slides.ithreedformat",
            "public_symbol",
            "ThreeDFormat",
            (Evidence("x", "line 1; class; public by name"),),
        ),
        Fact(
            "public_symbol:aspose.slides.idocumentproperties",
            "public_symbol",
            "DocumentProperties",
            (Evidence("x", "line 2; class; public by name"),),
        ),
    ),
)
SLIDES_NET_EXISTING: list[dict[str, Any]] = [
    {
        "section": "key_capabilities",
        "slot": "capability:2",
        "text": (
            "Adjust 3D properties with ThreeDFormat and edit document properties through "
            "DocumentProperties."
        ),
        "fact_ids": [
            "public_symbol:aspose.slides.ithreedformat",
            "public_symbol:aspose.slides.idocumentproperties",
        ],
    }
]


def test_sighting_slides_net_f03_capability_list_drops_document_properties() -> None:
    """docs/DECISION_LOG.md 2026-09-27 05:33 UTC entry, draw 4 / docs/DEFECT_INDEX.md row 2
    (aspose-slides-foss/Aspose.Slides-FOSS-for-.NET): independent review's F03 found the candidate
    "omits 3D-properties and document-properties capabilities the original README's 'What it can
    do' list names." Reproduced at the unit level: the pre-coherence unit names both; the
    post-coherence revision keeps 3D properties but silently drops document properties and its own
    citation, with no trace of "document" or "DocumentProperties" left anywhere in the text."""
    revised = [
        {
            "section": "key_capabilities",
            "slot": "capability:2",
            "text": "Adjust 3D properties on any shape with ThreeDFormat.",
            "fact_ids": ["public_symbol:aspose.slides.ithreedformat"],
        }
    ]
    errors = coherence_content_loss_errors(revised, SLIDES_NET_EXISTING, SLIDES_NET_FACTS)
    assert errors == [
        "key_capabilities/capability:2: coherence revision drops the previously-cited "
        "public_symbol 'public_symbol:aspose.slides.idocumentproperties' and none of its own "
        "content ('DocumentProperties') remains in the revised text - a named capability, format, "
        "or structural detail the prior version carried must not be silently dropped during "
        "coherence"
    ]
    corrected = recover_coherence_content_loss(
        {"units": [dict(unit) for unit in revised]},
        existing_units=SLIDES_NET_EXISTING,
        facts=SLIDES_NET_FACTS,
    )
    assert corrected is not None
    assert corrected["units"][0]["text"] == SLIDES_NET_EXISTING[0]["text"]
    assert corrected["units"][0]["fact_ids"] == SLIDES_NET_EXISTING[0]["fact_ids"]
    assert (
        coherence_content_loss_errors(corrected["units"], SLIDES_NET_EXISTING, SLIDES_NET_FACTS)
        == []
    )


def test_a_dropped_citation_whose_value_still_reads_in_the_text_is_not_flagged() -> None:
    """Content that survives - re-cited differently in the same unit, or restated in different
    words that still carry the fact's own distinctive tokens - must never be flagged; only silent,
    untraceable loss is this check's target (never a blanket "fact_ids must never shrink" rule)."""
    existing = [
        {
            "section": "opening",
            "slot": "opening",
            "text": "Aspose.3D for Python writes GLB files for interchange.",
            "fact_ids": ["format:output.glb"],
        }
    ]
    revised = [
        {
            "section": "opening",
            "slot": "opening",
            "text": "Aspose.3D for Python supports glb output for interchange.",
            "fact_ids": [],
        }
    ]
    assert coherence_content_loss_errors(revised, existing, FACTS) == []
    assert (
        recover_coherence_content_loss(
            {"units": [dict(unit) for unit in revised]}, existing_units=existing, facts=FACTS
        )
        is None
    )


def test_a_dropped_identity_or_package_citation_is_never_flagged() -> None:
    """Live verification, aspose-slides-foss/Aspose.Slides-FOSS-for-Java (docs/DECISION_LOG.md,
    this item): a first version of this check with no kind exclusion fired on every
    documentation_resources link unit - the model had correctly shortened several repeated
    "org.aspose:aspose-slides-foss version 26.8.0 for Java 21" sentences (coherence's own "no
    repetition" objective), dropping only the identity/package provenance citations that
    boilerplate existed to justify, never a named capability or format. Reproduced here with the
    exact live shape (five link units each dropping the same five identity/package facts down to
    one shared sentence): none of it is flagged, and recover has nothing to do."""
    existing = [
        {
            "section": "documentation_resources",
            "slot": "link:link_target:029",
            "text": (
                "The getting started guide walks through installing the library and creating "
                "your first presentation using Aspose.Slides FOSS for Java, a Java library for "
                "slides presentations distributed as org.aspose:aspose-slides-foss version "
                "26.8.0 for Java 21."
            ),
            "fact_ids": [
                "link_target:029",
                "identity:ecosystem",
                "identity:family",
                "identity:platform",
                "identity:repository",
                "identity:revision",
                "package:java_release",
                "package:name",
                "package:version",
            ],
        }
    ]
    revised = [
        {
            "section": "documentation_resources",
            "slot": "link:link_target:029",
            "text": (
                "The getting started guide walks through installing the library and creating "
                "your first presentation."
            ),
            "fact_ids": ["link_target:029"],
        }
    ]
    facts = FactsDocument(
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "a" * 40,
        (
            Fact("identity:ecosystem", "identity", "java", (Evidence("x"),)),
            Fact("identity:family", "identity", "slides", (Evidence("x"),)),
            Fact("identity:platform", "identity", "java", (Evidence("x"),)),
            Fact(
                "identity:repository",
                "identity",
                "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
                (Evidence("x"),),
            ),
            Fact("identity:revision", "identity", "a" * 40, (Evidence("x"),)),
            Fact("package:java_release", "package", "21", (Evidence("x"),)),
            Fact("package:name", "package", "org.aspose:aspose-slides-foss", (Evidence("x"),)),
            Fact("package:version", "package", "26.8.0", (Evidence("x"),)),
            Fact("link_target:029", "link_target", "https://example.test/start", (Evidence("x"),)),
        ),
    )
    assert coherence_content_loss_errors(revised, existing, facts) == []
    assert (
        recover_coherence_content_loss(
            {"units": [dict(unit) for unit in revised]}, existing_units=existing, facts=facts
        )
        is None
    )


def test_coherence_checks_includes_content_loss_errors_only_when_existing_units_is_given() -> None:
    """Backward compatible by default (every call site/test above omits ``existing_units`` and
    sees exactly its old behaviour) - the new check only runs when a caller actually has a
    pre-coherence version to compare against."""
    existing = [
        {
            "section": "key_capabilities",
            "slot": "capability:1",
            "text": "Scene builds scenes from aspose.threed.Scene and writes GLB files.",
            "fact_ids": ["public_symbol:aspose.threed.scene", "format:output.glb"],
        }
    ]
    bad = {
        "units": [
            UNITS["units"][0],
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Scene builds scenes.",
                "fact_ids": ["public_symbol:aspose.threed.scene"],
            },
        ],
        "omitted": [],
    }
    # Pre-G3-W05 shape: no existing_units given, so the silently-dropped format:output.glb
    # citation is invisible - exactly the gap docs/DEFECT_INDEX.md recorded.
    assert coherence_checks(bad, TASKS, FACTS, NAME) == []
    # G3-W05: given the pre-coherence units, the same drop is caught.
    errors = coherence_checks(bad, TASKS, FACTS, NAME, existing_units=existing)
    assert len(errors) == 1
    assert "format:output.glb" in errors[0]
