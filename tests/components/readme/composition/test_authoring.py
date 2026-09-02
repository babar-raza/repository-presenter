"""Authoring: one closed packet per LLM-owned section, and a guard on every unit before render."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    AUTHORED_SECTIONS,
    SectionTask,
    allowed_identifiers,
    authoring_tasks,
    identifier_allowed,
    identifier_tokens,
    merge_units,
    section_spellings,
    unit_checks,
    verified_members,
    write_content_units,
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


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("package:name", "package", "aspose-3d-foss"),
        _fact("public_symbol:aspose.threed.scene", "public_symbol", "aspose.threed.Scene"),
        _fact(
            "public_symbol:aspose.threed.scene.save", "public_symbol", "aspose.threed.Scene.save"
        ),
        _fact("import_path:aspose.threed", "import_path", "aspose.threed"),
        _fact("format:output.glb", "format", ".glb"),
        _fact("format:input.obj", "format", ".obj", "UNRESOLVED"),
        _fact("example:001", "example", "print(1)"),
        _fact("example:002", "example", "print(2)"),
        _fact("link_target:002", "link_target", "https://docs.example.com/3d"),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
        _fact("inherited_unit:002.paragraph", "inherited_unit", "Original prose."),
        _fact("inherited_unit:055.paragraph", "inherited_unit", "A limitation."),
    ),
)
PLAN: dict[str, Any] = {
    "sections": [
        {"section_id": s, "include": s not in {"enterprise_relationship"}, "reason": "r"}
        for s in [
            "identity",
            "badges",
            "opening",
            "navigation",
            "at_a_glance",
            "key_capabilities",
            "installation",
            "dependencies",
            "quick_start",
            "additional_examples",
            "api_reference",
            "documentation_resources",
            "scope_limitations",
            "development_testing",
            "enterprise_relationship",
            "third_party_notices",
            "license",
        ]
    ],
    "core_capabilities": [
        {"title": "Build scenes", "fact_ids": ["public_symbol:aspose.threed.scene"]},
        {"title": "Save GLB", "fact_ids": ["format:output.glb"]},
        {"title": "Import the package", "fact_ids": ["import_path:aspose.threed"]},
    ],
    "at_a_glance": None,
    "quick_start_example_id": "example:001",
    "additional_example_ids": ["example:002"],
    "api_hubs": [
        {"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": ["example:001"]}
    ],
    "material_limitations": [{"fact_ids": ["inherited_unit:055.paragraph"], "unit_ids": []}],
    "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
    "deviations": [],
}
INVESTIGATION = {
    "product_summary": {"text": "x", "fact_ids": ["package:name"]},
    "audience": {"text": "x", "fact_ids": ["identity:repository"]},
    "problems_solved": [{"text": "x", "fact_ids": ["format:output.glb"]}],
    "limitations": [{"text": "x", "fact_ids": ["inherited_unit:055.paragraph"]}],
}
DISPOSITIONS = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:002.paragraph",
            "disposition": "VERIFIED_REWRITE",
            "destination_section": "opening",
            "fact_ids": [],
            "rationale": "r",
        }
    ]
}


def test_tasks_cover_the_included_authored_sections_with_closed_fact_sets() -> None:
    tasks = authoring_tasks(ENTRY, FACTS, INVESTIGATION, DISPOSITIONS, PLAN)
    assert [task.section_id for task in tasks] == [
        "opening",
        "key_capabilities",
        "quick_start",
        "additional_examples",
        "api_reference",
        "documentation_resources",
        "scope_limitations",
        "development_testing",
    ]
    assert AUTHORED_SECTIONS[-1] == "enterprise_relationship"
    by_section = {task.section_id: task for task in tasks}
    opening = by_section["opening"]
    assert opening.slots == ("opening",)
    assert opening.accepted_ids == {
        "identity:repository",
        "package:name",
        "format:output.glb",
        "public_symbol:aspose.threed.scene",
        "import_path:aspose.threed",
        "inherited_unit:002.paragraph",
    }
    assert opening.packet["product_name"] == NAME and opening.packet["mode"] == "author"
    assert opening.packet["section_id"] == "opening"
    assert "Slots to fill, each exactly once: opening." in opening.packet["objective"]
    assert [f["id"] for f in opening.packet["do_not_claim"]] == ["format:input.obj"]
    assert by_section["key_capabilities"].slots == ("capability:1", "capability:2", "capability:3")
    assert by_section["quick_start"].accepted_ids >= {"example:001"}
    assert by_section["additional_examples"].slots == ("preview", "workflow:example:002")
    assert by_section["api_reference"].slots == ("hub:public_symbol:aspose.threed.scene",)
    assert by_section["documentation_resources"].accepted_ids >= {"link_target:002"}
    assert by_section["scope_limitations"].slots == ("scope", "limitation:1")
    assert by_section["development_testing"].accepted_ids >= {"build_test_asset:tests"}
    assert "format:input.obj" not in by_section["opening"].accepted_ids


def test_identifier_tokens_and_the_allowed_set() -> None:
    text = "Use aspose.threed.Scene, control_points, PbrMaterial and save() with Scene."
    assert identifier_tokens(text) == {
        "aspose.threed.Scene",
        "control_points",
        "PbrMaterial",
        "save()",
    }
    allowed = allowed_identifiers(FACTS, NAME)
    assert {
        "aspose.threed.Scene",
        "threed.Scene",
        "Scene",
        "Scene()",
        "Scene.save",
        "save()",
        "aspose.threed",
        "Aspose.3D",
        ".glb",
        "aspose-3d-foss",
    } <= allowed
    assert ".obj" not in allowed and "PbrMaterial" not in allowed


def test_members_that_verified_examples_call_may_be_spelled_with_their_class() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            _fact("public_symbol:aspose.threed.scene", "public_symbol", "aspose.threed.Scene"),
            _fact("example:001", "example", "s = Scene()\ns.save('a.glb')\ns.root_node.name"),
            _fact("example:002", "example", "s.open('x.obj')", "CONTRADICTED"),
        ),
    )
    members = verified_members(facts)
    assert members == {"save", "root_node", "name"}
    allowed = allowed_identifiers(facts, NAME)
    assert identifier_allowed("Scene.save", allowed, members)
    assert identifier_allowed("Scene.save()", allowed, members)
    assert identifier_allowed("root_node", allowed, members)
    assert not identifier_allowed("Scene.open", allowed, members)
    assert not identifier_allowed("Mesh.save", allowed, members)
    spellings = section_spellings(["public_symbol:aspose.threed.scene"], facts)
    assert spellings == [
        "aspose.threed.Scene",
        "Scene",
        "member name",
        "member root_node",
        "member save",
    ]


def test_unit_checks_reject_markdown_urls_commands_stray_identifiers_and_outside_facts() -> None:
    task = SectionTask(
        "key_capabilities",
        {},
        frozenset({"public_symbol:aspose.threed.scene", "format:output.glb"}),
        ("capability:1", "capability:2"),
    )
    good = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Scene objects hold a scene graph.",
                "fact_ids": ["public_symbol:aspose.threed.scene"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:2",
                "text": "Scenes save as GLB files.",
                "fact_ids": ["format:output.glb"],
            },
        ],
        "omitted": [],
    }
    assert unit_checks(good, task, FACTS, NAME) == []
    bad = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "See `Scene` at https://x.y",
                "fact_ids": ["public_symbol:aspose.threed.scene"],
            },
            {
                "section": "opening",
                "slot": "capability:1",
                "text": "Call PbrMaterial.apply() on control_points.",
                "fact_ids": ["example:001"],
            },
        ],
        "omitted": [{"fact_id": "example:002", "reason": "r"}],
    }
    errors = unit_checks(bad, task, FACTS, NAME)
    assert errors == [
        "units must fill exactly these slots once each: capability:1, capability:2; "
        "got capability:1, capability:1",
        "unit capability:1: text contains a code span or fence ('`')",
        "unit capability:1: identifiers that are not accepted fact values: x.y",
        "unit capability:1: section must be key_capabilities",
        "unit capability:1: identifiers that are not accepted fact values: PbrMaterial, "
        "PbrMaterial.apply, apply(), control_points",
        "unit capability:1: cites facts outside this section's set: example:001",
    ]


def test_units_merge_in_shell_order_and_write_deterministically(tmp_path: Path) -> None:
    outputs = {
        "quick_start": {
            "units": [{"section": "quick_start", "slot": "lead_in", "text": "x", "fact_ids": []}],
            "omitted": [],
        },
        "opening": {
            "units": [{"section": "opening", "slot": "opening", "text": "y", "fact_ids": []}],
            "omitted": [{"fact_id": "package:name", "reason": "r"}],
        },
    }
    document = merge_units(outputs)
    assert [unit["section"] for unit in document["units"]] == ["opening", "quick_start"]
    assert document["omitted"] == [{"section": "opening", "fact_id": "package:name", "reason": "r"}]
    path = tmp_path / "t" / "content_units.json"
    digest = write_content_units(document, path)
    raw = path.read_bytes()
    assert raw.endswith(b"}\n") and b"\r\n" not in raw and json.loads(raw) == document
    assert write_content_units(document, path) == digest
