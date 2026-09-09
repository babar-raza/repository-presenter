"""Planning: conditions evaluated from facts, a bounded packet, a guard on every selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition import planning
from repository_presenter.components.readme.composition.components.shell import section_ids
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
    assert packet["investigation"] == {"i": 1}
    # A disposition may cite a fact the plan's own binding forbids - that is why it omits or
    # defers its unit - so the planner is shown only the citations a valid plan may carry
    # (RESEARCH_AND_GUIDELINES.md section 27.2 RC1); destinations and unit IDs are untouched.
    omission = {
        "unit_id": "inherited_unit:001.paragraph",
        "disposition": "OMIT_UNSUPPORTED",
        "destination_section": None,
        "fact_ids": ["example:003", "example:002"],
        "rationale": "the example failed",
    }
    filtered = planning_packet(
        ENTRY, FACTS, {"i": 1}, {"d": 2, "dispositions": [omission]}, MANIFEST
    )
    assert filtered["dispositions"] == {
        "d": 2,
        "dispositions": [{**omission, "fact_ids": ["example:002"]}],
    }


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
        "api_hubs must each be a supported public_symbol fact",
        "a material limitation cites at least one fact or inherited unit",
        "link 'link_target:003' is not a verified link target",
        "link 'link_target:002' is assigned to a section that is not included: "
        "'third_party_notices'",
        "deviation names an unknown section 'changelog'",
    ]

    # G4-W17 arrival item 16: an Aspose link beyond the ceiling is trimmed, in plan order, rather
    # than failing the whole plan - with the ceiling at 0 the plan's own single Aspose link is
    # dropped and nothing is left to complain about.
    ceiling = PlanningPolicy(aspose_links_max=0)
    trimmed = _plan()
    assert plan_checks(trimmed, FACTS, ceiling) == []
    assert trimmed["links"] == []


def test_a_repeated_hub_and_an_over_ceiling_aspose_link_are_trimmed_not_rejected() -> None:
    """G4-W17 arrival item 16 (lane C PROPOSAL E). Measured 2026-09-06 on aspose-3d-foss/
    Aspose.3D-FOSS-for-Java: a duplicate hub and an Aspose link ceiling breach both come from the
    same plan, on two separate attempts, and both are trimmable - the first occurrence of a
    repeated hub already says everything a duplicate would, and the links beyond the ceiling can
    be dropped in the plan's own order. Neither should cost the whole plan a rejection and a
    second call for what a fixed rule already knows how to fix."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact("link_target:004", "link_target", "https://products.aspose.org/widget/2"),
            _fact("link_target:005", "link_target", "https://products.aspose.org/widget/3"),
        ),
    )
    plan = _plan(
        api_hubs=[
            {"symbol_fact_id": "public_symbol:widget.scene", "fact_ids": ["example:001"]},
            {"symbol_fact_id": "public_symbol:widget.scene", "fact_ids": ["example:002"]},
        ],
        links=[
            {"link_fact_id": "link_target:002", "section_id": "documentation_resources"},
            {"link_fact_id": "link_target:004", "section_id": "documentation_resources"},
            {"link_fact_id": "link_target:005", "section_id": "documentation_resources"},
        ],
    )
    ceiling = PlanningPolicy(aspose_links_max=2)
    assert plan_checks(plan, facts, ceiling) == []
    assert plan["api_hubs"] == [
        {"symbol_fact_id": "public_symbol:widget.scene", "fact_ids": ["example:001"]}
    ]
    assert [link["link_fact_id"] for link in plan["links"]] == [
        "link_target:002",
        "link_target:004",
    ]


def test_a_preserved_units_own_aspose_link_reserves_headroom_in_the_plans_trim() -> None:
    """G4-W17 arrival item 32. Measured 2026-09-06 on aspose-3d-foss/Aspose.3D-FOSS-for-Java: a
    VERIFIED_MOVE unit renders its own Aspose link verbatim - reconciliation's decision, not the
    plan's - so BC-06's ceiling on the whole rendered document could be exceeded with nothing
    left in the plan's own links list to trim, and a repair re-ask of planning alone returned a
    byte-identical list every time, since planning genuinely had nothing left to change. Counting
    a placed unit's own Aspose links here reserves headroom so the plan's own trim closes the gap
    instead of leaving it for a stage with no lever to pull."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:002.paragraph",
                "inherited_unit",
                "See the [full guide](https://docs.aspose.org/widget/full).",
            ),
        ),
    )
    dispositions = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:002.paragraph",
                "disposition": "VERIFIED_MOVE",
                "destination_section": "documentation_resources",
                "fact_ids": [],
                "rationale": "kept verbatim",
            }
        ]
    }
    plan = _plan()  # carries one Aspose link of its own: link_target:002
    ceiling = PlanningPolicy(aspose_links_max=1)
    assert plan_checks(plan, facts, ceiling, dispositions=dispositions, ecosystem="python") == []
    # The preserved unit's own link already fills the ceiling of 1, so the plan's own link -
    # which planning could still trim, unlike the preserved one - is dropped to leave it room.
    assert plan["links"] == []

    # Without a preserved Aspose link, the same ceiling leaves the plan's own link untouched.
    bare_plan = _plan()
    assert plan_checks(bare_plan, FACTS, ceiling) == []
    assert bare_plan["links"] == [
        {"link_fact_id": "link_target:002", "section_id": "documentation_resources"}
    ]


def test_a_verified_rewrite_disposition_names_link_targets_the_plan_must_carry() -> None:
    """Third external review, 2026-09-07, measured on aspose-email-foss/Aspose.Email-FOSS-for-
    Python: a VERIFIED_REWRITE disposition against an inherited list unit named eight link_target
    facts for documentation_resources, the plan's own links list carried three, and the missing
    five - all real, verified links (PUBLIC_API.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md,
    CHANGELOG.md) - never reached authoring or the renderer, which both build only what the plan
    hands them. Review correctly rejected the composed candidate for it every time; a repair
    re-ask of authoring alone could not fix a gap that was already committed one stage earlier."""
    dispositions = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:003.list",
                "disposition": "VERIFIED_REWRITE",
                "destination_section": "documentation_resources",
                "fact_ids": ["link_target:001"],
                "rationale": "supported by facts, re-authored to the section's own format",
            }
        ]
    }
    plan = _plan()  # already carries link_target:002 of its own
    assert plan_checks(plan, FACTS, dispositions=dispositions, ecosystem="python") == []
    assert plan["links"] == [
        {"link_fact_id": "link_target:002", "section_id": "documentation_resources"},
        {"link_fact_id": "link_target:001", "section_id": "documentation_resources"},
    ]

    # Already planned: no duplicate is appended.
    already_planned = _plan(
        links=[
            {"link_fact_id": "link_target:001", "section_id": "documentation_resources"},
            {"link_fact_id": "link_target:002", "section_id": "documentation_resources"},
        ]
    )
    assert plan_checks(already_planned, FACTS, dispositions=dispositions, ecosystem="python") == []
    assert len(already_planned["links"]) == 2

    # VERIFIED_PRESERVE renders its unit verbatim elsewhere (placement.py), never through the
    # plan's own links, so it names no completeness obligation here.
    preserved = {
        "dispositions": [{**dispositions["dispositions"][0], "disposition": "VERIFIED_PRESERVE"}]
    }
    untouched = _plan()
    assert plan_checks(untouched, FACTS, dispositions=preserved, ecosystem="python") == []
    assert untouched["links"] == [
        {"link_fact_id": "link_target:002", "section_id": "documentation_resources"}
    ]


def test_a_further_verified_example_is_appended_to_additional_examples() -> None:
    """RC-01, RESEARCH_AND_GUIDELINES.md 27.2 RC1/SW1, 2026-09-08: no existing test actually
    exercised the append branch of this backstop (the shared fixtures always already carried
    every verified example) - added directly as part of the table refactor so the behavior this
    taskcard's own refactor must preserve byte-identically is actually pinned, not merely assumed
    unchanged because the surrounding tests still pass."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (*FACTS.facts, _fact("example:004", "example", "print(4)")),
    )
    # example:002 is already the plan's own additional example; example:004 is verified but
    # named nowhere in the plan yet, so only it is missing and gets appended after it.
    plan = _plan()
    assert plan_checks(plan, facts) == []
    assert plan["additional_example_ids"] == ["example:002", "example:004"]

    # Already carried: nothing is appended twice.
    already = _plan(additional_example_ids=["example:002", "example:004"])
    assert plan_checks(already, facts) == []
    assert already["additional_example_ids"] == ["example:002", "example:004"]


def test_plan_checks_backstop_table_applies_a_third_synthetic_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves the table-driven mechanism is generic - a third, synthetic backstop entry is
    applied without touching the two existing ones, not merely that the two known cases still
    pass (which a hard-coded pair of if-blocks disguised as a "table" could also satisfy)."""

    def _required(
        output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
    ) -> list[str]:
        return [] if output.get("synthetic_marker") else ["synthetic:value"]

    def _apply(output: dict[str, Any], missing: list[Any]) -> None:
        output["synthetic_marker"] = missing

    monkeypatch.setattr(
        planning,
        "_BACKSTOPS",
        (*planning._BACKSTOPS, ("synthetic_marker", _required, _apply)),
    )
    plan = _plan()
    assert plan_checks(plan, FACTS) == []
    assert plan["synthetic_marker"] == ["synthetic:value"]
    # The two real backstops are unaffected by the third entry's presence.
    assert plan["additional_example_ids"] == ["example:002"]
    assert plan["links"] == [
        {"link_fact_id": "link_target:002", "section_id": "documentation_resources"}
    ]


def test_every_backstop_field_name_names_a_real_planning_schema_property() -> None:
    """A typo'd field name in `_BACKSTOPS` must fail loudly here, not silently no-op forever
    (a table row naming a field the schema does not have would apply its append to a key the
    schema-validated output never checks, so a typo would never be caught any other way)."""
    loaded = load_manifests(REPO_ROOT / "prompts")["presentation_planning"]
    schema = planning_schema(loaded, FACTS)
    field_names = {field for field, _, _ in planning._BACKSTOPS}
    assert field_names and field_names <= set(schema["properties"])


def test_a_shell_rendered_link_is_never_a_plans_own_assignment() -> None:
    """README_CONTRACT.md rows 3 and 18: the banner and the closing Enterprise sentence render
    deterministically from these exact IDs, in their own fixed place.

    Measured 2026-09-06 on Aspose.Cells for .NET: the plan assigned `product.homepage` to
    `identity` - a section links are never assigned to at all - and reached five Aspose links
    against a ceiling of four with only four genuinely link-worthy targets, because the shell's
    own homepage link was double-counted as if it were a fifth.
    """
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact("link_target:product.homepage", "link_target", "https://products.aspose.com/w"),
            _fact("link_target:product.enterprise", "link_target", "https://products.aspose.com/w"),
        ),
    )
    plan = _plan(
        links=[
            {"link_fact_id": "link_target:product.homepage", "section_id": "identity"},
            {"link_fact_id": "link_target:002", "section_id": "documentation_resources"},
        ]
    )
    assert plan_checks(plan, facts) == [
        "link 'link_target:product.homepage' renders on its own (the banner or the closing "
        "Enterprise sentence); the same URL has its own numbered link_target fact if a section "
        "needs to reference it directly"
    ]
    # It never reaches the Aspose count either - not one more genuine link, uncounted.
    ceiling = PlanningPolicy(aspose_links_max=1)
    assert plan_checks(plan, facts, ceiling) == [
        "link 'link_target:product.homepage' renders on its own (the banner or the closing "
        "Enterprise sentence); the same URL has its own numbered link_target fact if a section "
        "needs to reference it directly"
    ]


def test_which_capability_facts_are_shared_is_composed_from_the_citations() -> None:
    """Section 27.2 RC2 asks that the rest of each set discriminate, and RC1 says a decision the
    citations already carry is composed, never restated and then rejected for being restated
    wrongly.

    Measured 2026-09-06: `shared_fact_ids` unstated by one of the citing capabilities rejected
    `presentation_planning` twice on Aspose.3D, Cells, Email and Words for .NET - four of six -
    each time naming a fact the model had already declared shared everywhere else.
    """
    overlapping = [
        {"title": "Build scenes", "fact_ids": ["public_symbol:widget.scene", "example:001"]},
        {"title": "Export STL", "fact_ids": ["format:output.stl", "example:001"]},
        {"title": "Run examples", "fact_ids": ["example:002"]},
    ]
    plan = _plan(core_capabilities=overlapping)
    assert plan_checks(plan, FACTS) == []
    declared = [item.get("shared_fact_ids") for item in plan["core_capabilities"]]
    # Composed where there is something to compose; a capability sharing nothing keeps the shape
    # the model wrote, with no empty key added to it.
    assert declared == [["example:001"], ["example:001"], None]

    # The rule has always offered two equal arms - own facts *or* a declaration - so declaring was
    # always sufficient and distinctness was never demanded. Two capabilities resting on the same
    # facts are declared and pass, exactly as they did when the model declared them by hand.
    indistinct = [
        {"title": "Build scenes", "fact_ids": ["public_symbol:widget.scene", "example:001"]},
        {"title": "Export STL", "fact_ids": ["public_symbol:widget.scene", "example:001"]},
        {"title": "Run examples", "fact_ids": ["example:002"]},
    ]
    plan = _plan(core_capabilities=indistinct)
    assert plan_checks(plan, FACTS) == []
    assert [item.get("shared_fact_ids") for item in plan["core_capabilities"]] == [
        ["example:001", "public_symbol:widget.scene"],
        ["example:001", "public_symbol:widget.scene"],
        None,
    ]

    # A fact may only be declared shared by a capability that cites it.
    stray = [dict(item) for item in overlapping]
    stray[2]["shared_fact_ids"] = ["example:001"]
    assert plan_checks(_plan(core_capabilities=stray), FACTS) == [
        "capability 3 declares shared facts it does not cite: example:001; shared_fact_ids is a "
        "subset of that capability's fact_ids"
    ]


def test_a_capability_title_names_only_a_format_the_facts_verify() -> None:
    """Asked at planning, where a re-ask can change the title; at S6 nothing can.

    Aspose.Note titled a capability "Export pages to PDF" while format:output.pdf is UNRESOLVED,
    and section_authoring rejected it twice on the same title, ending the transaction (measured
    2026-09-06). The same rule already governs the At a Glance formats.
    """
    unverified = [
        {"title": "Import OBJ meshes", "fact_ids": ["public_symbol:widget.scene"]},
        {"title": "Export STL", "fact_ids": ["format:output.stl"]},
        {"title": "Run examples", "fact_ids": ["example:001"]},
    ]
    glance = {
        "input_format_ids": [],
        "output_format_ids": ["format:output.stl"],
        "capability_titles": [item["title"] for item in unverified],
    }
    assert plan_checks(_plan(core_capabilities=unverified, at_a_glance=glance), FACTS) == [
        "core_capabilities 1 is titled 'Import OBJ meshes', which names .obj; no fact verifies "
        "that format, so the title claims what the repository does not prove - title the "
        "capability by what is verified"
    ]
    # A verified format is free to name, and prose that matches no format fact is just prose.
    assert plan_checks(_plan(), FACTS) == []


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


def test_a_deviation_may_only_name_a_shell_section() -> None:
    # The canary's planner was rejected for "deviation names an unknown section 'links'", which
    # the code can state outright (RESEARCH_AND_GUIDELINES.md section 27.5 D1).
    loaded = load_manifests(REPO_ROOT / "prompts")["presentation_planning"]
    schema = planning_schema(loaded, FACTS)
    section_id = schema["properties"]["deviations"]["items"]["properties"]["section_id"]
    assert section_id["enum"] == list(section_ids())
    assert "links" not in section_id["enum"] and "opening" in section_id["enum"]

    validator = Draft202012Validator(schema)
    plan = _plan(deviations=[{"section_id": "links", "reason": "r"}])
    assert [
        error.message
        for error in validator.iter_errors(plan)
        if error.json_path == "$.deviations[0].section_id"
    ] == [f"'links' is not one of {list(section_ids())!r}"]


def test_a_link_target_the_shell_already_renders_cannot_be_written_at_all() -> None:
    """A rejection message asks the model to notice its own mistake; an enum makes the mistake
    impossible to write in the first place - the same reason a contradicted example is never
    left to a rejection message either.

    Measured 2026-09-06 on Aspose.Email for .NET: the prompt's own instruction not to assign
    `product.enterprise` as a link was not enough - the model made the identical choice on three
    independent attempts across two composition runs, at temperature zero.
    """
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact("link_target:product.enterprise", "link_target", "https://products.aspose.com/w"),
        ),
    )
    loaded = load_manifests(REPO_ROOT / "prompts")["presentation_planning"]
    schema = planning_schema(loaded, facts)
    link_fact_id = schema["properties"]["links"]["items"]["properties"]["link_fact_id"]
    assert link_fact_id["enum"] == ["link_target:001", "link_target:002"]
    assert "link_target:product.enterprise" not in link_fact_id["enum"]

    validator = Draft202012Validator(schema)
    plan = _plan(
        links=[{"link_fact_id": "link_target:product.enterprise", "section_id": "opening"}]
    )
    assert [
        error.message
        for error in validator.iter_errors(plan)
        if error.json_path == "$.links[0].link_fact_id"
    ] == [f"'link_target:product.enterprise' is not one of {link_fact_id['enum']!r}"]
