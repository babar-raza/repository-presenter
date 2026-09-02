"""The coherence pass: one call over the document, every unit back, each held to its section."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.composition.authoring import SectionTask
from repository_presenter.components.readme.composition.coherence import (
    apply_coherence,
    coherence_checks,
    coherence_packet,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry

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
        "unit opening: text contains a code span or fence ('`')",
        "unit capability:1: cites facts outside this section's set: format:output.glb",
    ]
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
