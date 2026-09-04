"""Planning: conditions evaluated from facts, a bounded packet, a guard on every selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.planning import (
    plan_checks,
    planning_packet,
    planning_schema,
    section_conditions,
    summarize_plan,
    write_plan,
)
from repository_presenter.components.readme.composition.policy import PlanningPolicy
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "org/Aspose.Widget-FOSS-for-Python",
        "family": "widget",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
MANIFEST = load_manifests(REPO_ROOT / "prompts")["presentation_planning"].manifest


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("format:input.obj", "format", ".obj", "UNRESOLVED"),
        _fact("format:output.stl", "format", ".stl"),
        _fact("example:001", "example", "print(1)"),
        _fact("example:002", "example", "print(2)"),
        _fact("example:003", "example", "boom", "CONTRADICTED"),
        _fact("public_symbol:widget.scene", "public_symbol", "widget.Scene"),
        _fact("link_target:001", "link_target", "LICENSE"),
        _fact("link_target:002", "link_target", "https://docs.aspose.org/widget"),
        _fact("link_target:003", "link_target", "https://example.com/gone", "CONTRADICTED"),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
        _fact("inherited_unit:001.paragraph", "inherited_unit", "A limitation."),
    ),
)
ALL_SECTIONS = [
    "identity",
    "badges",
    "banner",
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
EXCLUDED = {"banner", "enterprise_relationship", "third_party_notices"}


def _plan(**overrides: Any) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "sections": [
            {"section_id": s, "include": s not in EXCLUDED, "reason": "facts"} for s in ALL_SECTIONS
        ],
        "core_capabilities": [
            {"title": "Build scenes", "fact_ids": ["public_symbol:widget.scene"]},
            {"title": "Export STL", "fact_ids": ["format:output.stl"]},
            {"title": "Run examples", "fact_ids": ["example:001"]},
        ],
        "at_a_glance": {
            "input_format_ids": [],
            "output_format_ids": ["format:output.stl"],
            "capability_titles": ["Build scenes", "Export STL", "Run examples"],
        },
        "quick_start_example_id": "example:001",
        "additional_example_ids": ["example:002"],
        "api_hubs": [{"symbol_fact_id": "public_symbol:widget.scene", "fact_ids": ["example:001"]}],
        "material_limitations": [{"fact_ids": [], "unit_ids": ["inherited_unit:001.paragraph"]}],
        "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
        "deviations": [],
    }
    plan.update(overrides)
    return plan


def test_conditions_are_evaluated_from_the_facts() -> None:
    conditions = section_conditions(FACTS)
    assert conditions["identity"] is True and conditions["license"] is True
    assert conditions["at_a_glance"] is True  # row 6: the plan always carries three
    assert conditions["dependencies"] is True
    assert conditions["additional_examples"] is True
    assert conditions["api_reference"] is True  # row 14: Required
    assert conditions["documentation_resources"] is True
    assert conditions["development_testing"] is True
    assert conditions["enterprise_relationship"] is False
    assert conditions["third_party_notices"] is False


def test_the_packet_carries_conditions_policy_and_supported_facts_only() -> None:
    packet = planning_packet(ENTRY, FACTS, {"i": 1}, {"d": 2}, MANIFEST)
    assert packet["repository"] == ENTRY.repository
    by_id = {section["id"]: section for section in packet["shell"]}
    assert by_id["at_a_glance"]["condition_holds"] is True
    assert by_id["banner"]["condition_holds"] is False  # no verified illustration
    assert by_id["api_reference"]["condition_holds"] is True  # row 14: Required
    assert by_id["license"]["condition_holds"] is True
    assert packet["policy"]["capabilities_max"] == 8 and packet["policy"]["version"] == "1"
    ids = {record["id"] for record in packet["facts"]}
    assert "format:input.obj" not in ids and "example:003" not in ids
    assert {"inherited_unit:001.paragraph", "link_target:002", "example:002"} <= ids
    assert (packet["investigation"], packet["dispositions"]) == ({"i": 1}, {"d": 2})


def test_a_plan_within_the_rules_passes_and_each_violation_is_named() -> None:
    assert plan_checks(_plan(), FACTS) == []
    assert summarize_plan(_plan()) == (
        "sections 15/18, capabilities 3, hubs 1, examples 1+1, links 1, limitations 1"
    )

    # The shell's decisions are composed, not asked for: a plan that omits a required section
    # or excludes one whose condition holds is overwritten rather than rejected, so those three
    # rejection paths no longer exist (RESEARCH_AND_GUIDELINES.md section 27.5 D1).
    sections = [dict(entry) for entry in _plan()["sections"]]
    sections[0]["include"] = False  # identity
    sections[5]["include"] = False  # at_a_glance
    sections[10]["include"] = False  # additional_examples
    disagreeing = _plan(sections=sections)
    assert plan_checks(disagreeing, FACTS) == []
    composed = {entry["section_id"]: entry for entry in disagreeing["sections"]}
    assert composed["identity"] == {
        "section_id": "identity",
        "include": True,
        "reason": "the shell requires it",
    }
    assert composed["at_a_glance"]["include"] is True
    assert composed["additional_examples"]["include"] is True
    assert composed["third_party_notices"] == {
        "section_id": "third_party_notices",
        "include": False,
        "reason": "its condition does not hold",
    }

    omitted = _plan(at_a_glance=None)
    assert "at_a_glance is included, so its formats and capabilities are given" in plan_checks(
        omitted, FACTS
    )

    errors = plan_checks(
        _plan(
            core_capabilities=[{"title": "Only one", "fact_ids": ["example:001"]}],
            quick_start_example_id="example:003",
            additional_example_ids=["example:002", "example:002"],
            api_hubs=[{"symbol_fact_id": "public_symbol:nope", "fact_ids": ["example:001"]}],
            links=[
                {"link_fact_id": "link_target:003", "section_id": "documentation_resources"},
                {"link_fact_id": "link_target:002", "section_id": "third_party_notices"},
            ],
            deviations=[{"section_id": "changelog", "text": "x", "fact_ids": ["example:001"]}],
            material_limitations=[{"fact_ids": [], "unit_ids": []}],
        ),
        FACTS,
    )
    assert errors == [
        "core_capabilities must number 3 to 8; got 1",
        "at_a_glance capabilities are not core capabilities: "
        "['Build scenes', 'Export STL', 'Run examples']",
        "quick_start_example_id must be a SUPPORTED example; got 'example:003'",
        "additional_example_ids must be distinct and exclude the quick start",
        "api_hubs must be distinct public_symbol facts",
        "a material limitation cites at least one fact or inherited unit",
        "link 'link_target:003' is not a verified link target",
        "link 'link_target:002' is assigned to a section that is not included: "
        "'third_party_notices'",
        "deviation names an unknown section 'changelog'",
    ]

    ceiling = PlanningPolicy(aspose_links_max=0)
    assert plan_checks(_plan(), FACTS, ceiling) == ["Aspose links exceed the ceiling of 0: 1"]


def test_the_artifact_is_deterministic_json(tmp_path: Path) -> None:
    path = tmp_path / "t" / "plan.json"
    digest = write_plan(_plan(), path)
    raw = path.read_bytes()
    assert raw.startswith(b'{\n  "additional_example_ids": [\n    "example:002"\n  ],')
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert json.loads(raw) == _plan()
    assert write_plan(_plan(), path) == digest


def test_a_second_quick_start_example_is_supported_distinct_and_kept_out_of_additional() -> None:
    assert plan_checks(_plan(second_quick_start_example_id=None), FACTS) == []
    twice = plan_checks(_plan(second_quick_start_example_id="example:001"), FACTS)
    assert twice == [
        "second_quick_start_example_id must be a SUPPORTED example other than the first; "
        "got 'example:001'"
    ]
    plan = _plan(second_quick_start_example_id="example:002", additional_example_ids=[])
    for entry in plan["sections"]:
        if entry["section_id"] == "additional_examples":
            entry["include"] = False  # both verified examples are quick starts now
    assert plan_checks(plan, FACTS) == []
    assert "example:002" not in plan["additional_example_ids"]


def test_the_enterprise_condition_follows_the_live_target_fact() -> None:
    assert section_conditions(FACTS)["enterprise_relationship"] is False
    with_target = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            Fact(
                "link_target:product.enterprise",
                "link_target",
                "https://products.aspose.com/3d/python/",
                (
                    Evidence(
                        "https://products.aspose.com/3d/python/", "HTTP 200; enterprise target"
                    ),
                ),
                attributes={"role": "enterprise", "level": "platform"},
            ),
        ),
    )
    assert section_conditions(with_target)["enterprise_relationship"] is True


def _product_fact(fact_id: str, url: str) -> Fact:
    return Fact(fact_id, "link_target", url, (Evidence(url, "HTTP 200"),), attributes={"role": "x"})


def test_the_banner_condition_needs_both_verified_product_facts() -> None:
    # README_CONTRACT.md row 3: a verified illustration and a verified homepage, never one alone.
    image = _product_fact(
        "link_target:product.banner",
        "https://products.aspose.org/media/widget/python/banner-readme.png",
    )
    homepage = _product_fact(
        "link_target:product.homepage", "https://products.aspose.org/widget/python/"
    )
    assert section_conditions(FACTS)["banner"] is False
    only_image = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, image))
    assert section_conditions(only_image)["banner"] is False
    both = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, image, homepage))
    assert section_conditions(both)["banner"] is True


def test_at_a_glance_labels_are_geometry_safe_and_number_three_to_eight() -> None:
    # README_CONTRACT.md section 2.1: a longer title is shortened at planning, never clipped.
    short = _plan(
        at_a_glance={
            "input_format_ids": [],
            "output_format_ids": [],
            "capability_titles": ["Build scenes", "Export STL"],
        }
    )
    assert "at_a_glance needs at least three capability titles" in plan_checks(short, FACTS)
    long_token = "Build " + "x" * 29
    wide = _plan(
        core_capabilities=[
            {"title": long_token, "fact_ids": ["public_symbol:widget.scene"]},
            {"title": "Export STL", "fact_ids": ["format:output.stl"]},
            {"title": "Run examples", "fact_ids": ["example:001"]},
        ],
        at_a_glance={
            "input_format_ids": [],
            "output_format_ids": ["format:output.stl"],
            "capability_titles": [long_token, "Export STL", "Run examples"],
        },
    )
    assert any("unbroken token over 28 characters" in error for error in plan_checks(wide, FACTS))


def test_the_shell_decisions_are_composed_by_code_never_asked_of_the_plan() -> None:
    # Deterministic code already evaluates every shell condition from the facts, so the plan is
    # not asked for the decision list and cannot get it wrong: whatever it carries is replaced by
    # one decision per shell section, in shell order (section 27.2 RC1, section 27.5 D1).
    plan = _plan()
    del plan["sections"]
    assert plan_checks(plan, FACTS) == []
    assert [entry["section_id"] for entry in plan["sections"]] == ALL_SECTIONS

    duplicated = _plan()
    duplicated["sections"] = [dict(duplicated["sections"][0])] * 3
    assert plan_checks(duplicated, FACTS) == []
    assert [entry["section_id"] for entry in duplicated["sections"]] == ALL_SECTIONS


def test_the_flagship_is_one_of_the_additional_examples_or_null() -> None:
    # README_CONTRACT.md row 12: the flagship is one further example shown visibly.
    assert plan_checks(_plan(flagship_example_id=None), FACTS) == []
    assert plan_checks(_plan(flagship_example_id="example:002"), FACTS) == []
    assert plan_checks(_plan(flagship_example_id="example:001"), FACTS) == [
        "flagship_example_id must be one of additional_example_ids; got 'example:001'"
    ]


def test_the_verified_examples_travel_as_an_enum_so_a_valid_reply_cannot_name_another() -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.5 D1: the canary's planner was rejected twice for
    # naming a CONTRADICTED example, which no packet wording prevents. The code emits the
    # allowed IDs, so the rejection family cannot be produced by a schema-valid reply.
    loaded = load_manifests(REPO_ROOT / "prompts")["presentation_planning"]
    schema = planning_schema(loaded, FACTS)
    properties = schema["properties"]
    assert properties["quick_start_example_id"]["enum"] == ["example:001", "example:002"]
    assert properties["additional_example_ids"]["items"]["enum"] == ["example:001", "example:002"]
    assert properties["second_quick_start_example_id"]["enum"] == [
        "example:001",
        "example:002",
        None,
    ]
    assert properties["flagship_example_id"]["enum"] == ["example:001", "example:002", None]
    # The manifest's own schema is untouched: the specialisation is per call.
    assert "enum" not in loaded.manifest.output.schema_["properties"]["quick_start_example_id"]

    validator = Draft202012Validator(schema)
    contradicted = _plan(quick_start_example_id="example:003")
    assert [
        error.message
        for error in validator.iter_errors(contradicted)
        if error.json_path == "$.quick_start_example_id"
    ] == ["'example:003' is not one of ['example:001', 'example:002']"]
