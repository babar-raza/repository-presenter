"""The three placement rules of README_CONTRACT.md section 3, decided once for renderer and
validator: exclusive on fact-ID overlap, section visibility inherited, excluded never silent."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.composition.placement import (
    api_reference_covered_fact_ids,
    api_reference_hub_methods,
    placed_texts,
    placements,
    planned_fact_ids,
    renderer_fact_ids,
    renders_verbatim,
)
from repository_presenter.components.readme.composition.planning import plan_checks
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    REPOSITORY,
    "a" * 40,
    (
        _fact("identity:repository", "identity", REPOSITORY),
        _fact("format:input.obj", "format", ".obj", "UNRESOLVED"),
        _fact("public_symbol:aspose.threed.scene", "public_symbol", "aspose.threed.Scene"),
        _fact("example:001", "example", "print(1)"),
        _fact("example:002", "example", "print(2)"),
        _fact("example:003", "example", "boom", "CONTRADICTED"),
        _fact("link_target:002", "link_target", "https://docs.example.com/3d"),
        _fact("inherited_unit:010.paragraph", "inherited_unit", "OBJ import is not verified."),
        _fact("inherited_unit:011.paragraph", "inherited_unit", "A note nothing else covers."),
        _fact("inherited_unit:012.paragraph", "inherited_unit", "Docs live at the site."),
        _fact("inherited_unit:013.code_block", "inherited_unit", "```python\nprint(2)\n```"),
        _fact("inherited_unit:014.paragraph", "inherited_unit", "Old glance prose."),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
        _fact("inherited_unit:074.paragraph", "inherited_unit", "The suite covers 33 files."),
        _fact(
            "inherited_unit:071.code_block",
            "inherited_unit",
            "```bash" + chr(10) + "pytest" + chr(10) + "```",
        ),
    ),
)


def _plan(**overrides: Any) -> dict[str, Any]:
    included = {
        "identity",
        "badges",
        "opening",
        "navigation",
        "key_capabilities",
        "installation",
        "dependencies",
        "development_testing",
        "quick_start",
        "additional_examples",
        "api_reference",
        "documentation_resources",
        "scope_limitations",
        "license",
    }
    plan: dict[str, Any] = {
        "sections": [
            {"section_id": s, "include": s in included, "reason": "r"}
            for s in [
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
        ],
        "core_capabilities": [
            {"title": "Build scenes", "fact_ids": ["public_symbol:aspose.threed.scene"]},
            {"title": "Save", "fact_ids": ["identity:repository"]},
            {"title": "Load", "fact_ids": ["example:001"]},
        ],
        # At a Glance is included by the shell condition, so the plan always carries it.
        "at_a_glance": {
            "input_format_ids": [],
            "output_format_ids": [],
            "capability_titles": ["Build scenes", "Save", "Load"],
        },
        "quick_start_example_id": "example:001",
        "additional_example_ids": ["example:002"],
        "api_hubs": [{"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": []}],
        "material_limitations": [
            {"fact_ids": ["format:input.obj"], "unit_ids": ["inherited_unit:010.paragraph"]}
        ],
        "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
        "deviations": [],
    }
    plan.update(overrides)
    return plan


def _entry(unit: str, destination: str, *fact_ids: str) -> dict[str, Any]:
    return {
        "unit_id": unit,
        "disposition": "VERIFIED_PRESERVE",
        "destination_section": destination,
        "fact_ids": list(fact_ids),
        "rationale": "r",
    }


DISPOSITIONS = {
    "dispositions": [
        _entry("inherited_unit:010.paragraph", "scope_limitations", "format:input.obj"),
        _entry("inherited_unit:011.paragraph", "scope_limitations", "identity:repository"),
        _entry("inherited_unit:012.paragraph", "documentation_resources", "link_target:002"),
        _entry("inherited_unit:013.code_block", "additional_examples", "example:002"),
        _entry("inherited_unit:014.paragraph", "at_a_glance"),
    ]
}


def test_planned_fact_ids_name_each_sections_own_content() -> None:
    plan = _plan()
    assert planned_fact_ids(plan, "scope_limitations") == {
        "format:input.obj",
        "inherited_unit:010.paragraph",
    }
    assert planned_fact_ids(plan, "documentation_resources") == {"link_target:002"}
    assert planned_fact_ids(plan, "key_capabilities") == {
        "public_symbol:aspose.threed.scene",
        "identity:repository",
        "example:001",
    }
    assert planned_fact_ids(plan, "quick_start") == {"example:001"}
    assert planned_fact_ids(plan, "additional_examples") == {"example:002"}
    # RC-02: kept, not replaced - renderer_fact_ids adds to this, tested separately below.
    assert planned_fact_ids(plan, "api_reference") == {"public_symbol:aspose.threed.scene"}
    assert planned_fact_ids(plan, "opening") == frozenset()


def test_api_reference_coverage_is_renderer_derived_not_hub_only() -> None:
    """RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08: the Core API table lists
    every verified class/enum unconditionally, but the coverage model used to know only the
    plan's chosen hub symbols - narrower than what actually renders. A preserved unit citing a
    non-hub class the table already covers used to place beside a duplicate of itself ("placed");
    it must now be caught as "overlap".
    """
    hub_class = Fact(
        "public_symbol:aspose.threed.scene",
        "public_symbol",
        "aspose.threed.Scene",
        (Evidence("x"),),
        attributes={"symbol_kind": "class"},
    )
    non_hub_class = Fact(
        "public_symbol:aspose.threed.node",
        "public_symbol",
        "aspose.threed.Node",
        (Evidence("x"),),
        attributes={"symbol_kind": "class"},
    )
    facts = FactsDocument(
        REPOSITORY,
        "a" * 40,
        (
            _fact("identity:repository", "identity", REPOSITORY),
            hub_class,
            non_hub_class,
            _fact(
                "inherited_unit:090.list", "inherited_unit", "- `Node.parent`\n- `Node.children`"
            ),
        ),
    )
    plan = _plan()
    dispositions = {
        "dispositions": [
            _entry(
                "inherited_unit:090.list",
                "api_reference",
                "public_symbol:aspose.threed.node",
            )
        ]
    }
    decisions = {p.unit_id: p for p in placements(plan, dispositions, facts, "python")}
    # The old, hub-only model treated this as "placed" - a duplicate the reviewer had to catch
    # by hand every time (the exact shape behind RC-04's F08/api_reference incidents). The
    # renderer-derived model catches it mechanically instead.
    assert decisions["inherited_unit:090.list"].outcome == "overlap"
    assert decisions["inherited_unit:090.list"].overlap == ("public_symbol:aspose.threed.node",)


def test_api_reference_hub_methods_and_covered_fact_ids_agree_with_the_renderer() -> None:
    """The two functions `renderer.py`'s ``_api_reference`` and this module's coverage check
    both read - proven to actually agree here, not merely both individually plausible."""
    hub_class = Fact(
        "public_symbol:aspose.threed.scene",
        "public_symbol",
        "aspose.threed.Scene",
        (Evidence("x"),),
        attributes={"symbol_kind": "class"},
    )
    hub_method = Fact(
        "public_symbol:aspose.threed.scene.save",
        "public_symbol",
        "aspose.threed.Scene.save",
        (Evidence("x"),),
        attributes={"symbol_kind": "method"},
    )
    non_hub_class = Fact(
        "public_symbol:aspose.threed.node",
        "public_symbol",
        "aspose.threed.Node",
        (Evidence("x"),),
        attributes={"symbol_kind": "class"},
    )
    non_hub_method = Fact(
        "public_symbol:aspose.threed.node.detach",
        "public_symbol",
        "aspose.threed.Node.detach",
        (Evidence("x"),),
        attributes={"symbol_kind": "method"},
    )
    facts = FactsDocument(
        REPOSITORY, "a" * 40, (hub_class, hub_method, non_hub_class, non_hub_method)
    )
    plan = _plan()
    hub_methods = api_reference_hub_methods(plan, facts)
    assert hub_methods == {"aspose.threed.Scene": [hub_method]}
    covered = api_reference_covered_fact_ids(plan, facts)
    # Every class/enum, hub or not (the table lists all of them); only the hub's own method.
    assert covered == {
        "public_symbol:aspose.threed.scene",
        "public_symbol:aspose.threed.node",
        "public_symbol:aspose.threed.scene.save",
    }
    assert "public_symbol:aspose.threed.node.detach" not in covered


def test_documentation_resources_coverage_includes_the_renderers_own_issues_line() -> None:
    """RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08: `_documentation_resources`
    always appends its own "Open an issue" line from `identity:repository` when it is SUPPORTED,
    whether or not any plan link names it - a preserved unit citing only that fact for an issues
    mention duplicates a line the renderer produces, not the plan. The section's *link* coverage
    itself was already accurate via `planned_fact_ids`'s own generic per-section links loop; this
    is the one small additional gap.
    """
    facts = FactsDocument(
        REPOSITORY,
        "a" * 40,
        (_fact("identity:repository", "identity", REPOSITORY),),
    )
    assert renderer_fact_ids("documentation_resources", facts, {}) == {"identity:repository"}
    unresolved = FactsDocument(
        REPOSITORY,
        "a" * 40,
        (_fact("identity:repository", "identity", REPOSITORY, "UNRESOLVED"),),
    )
    assert renderer_fact_ids("documentation_resources", unresolved, {}) == frozenset()

    plan = _plan()
    dispositions = {
        "dispositions": [
            _entry("inherited_unit:095.paragraph", "documentation_resources", "identity:repository")
        ]
    }
    doc_facts = FactsDocument(
        REPOSITORY,
        "a" * 40,
        (
            _fact("identity:repository", "identity", REPOSITORY),
            _fact(
                "inherited_unit:095.paragraph",
                "inherited_unit",
                "File issues at the project's own tracker.",
            ),
        ),
    )
    decisions = {p.unit_id: p for p in placements(plan, dispositions, doc_facts, "python")}
    assert decisions["inherited_unit:095.paragraph"].outcome == "overlap"
    assert decisions["inherited_unit:095.paragraph"].overlap == ("identity:repository",)


def test_placement_is_exclusive_on_overlap_and_never_silent_when_excluded() -> None:
    decisions = {p.unit_id: p for p in placements(_plan(), DISPOSITIONS, FACTS, "python")}
    assert decisions["inherited_unit:010.paragraph"].outcome == "overlap"
    assert decisions["inherited_unit:010.paragraph"].overlap == ("format:input.obj",)
    assert decisions["inherited_unit:011.paragraph"].outcome == "placed"
    assert decisions["inherited_unit:012.paragraph"].outcome == "overlap"
    assert decisions["inherited_unit:013.code_block"].outcome == "owned_elsewhere"
    assert decisions["inherited_unit:014.paragraph"].outcome == "excluded"
    assert placed_texts(list(decisions.values())) == {
        "scope_limitations": ["A note nothing else covers."]
    }
    # A python fence is not this ecosystem's own example either, so it renders verbatim -
    # renders_verbatim reads the spec's fence vocabulary (net's is csharp/cs/c#), never the
    # literal ecosystem name, which only ever coincided for Python.
    assert renders_verbatim("inherited_unit:013.code_block", "```python\nprint(2)\n```", "net")


def test_a_csharp_example_is_owned_by_the_plan_not_placed_beside_it() -> None:
    """Measured 2026-09-06 on Aspose.3D for .NET: a ```csharp block never equals the literal
    string "net", so every VERIFIED_PRESERVE example rendered as ordinary content beside the
    plan's own rendering of the same example, and Additional Examples printed every code block
    twice - the defect two independent reviewer reads agreed on (BC-10)."""
    example = _fact("example:009", "example", "using Widget;\nnew Widget().Save();")
    block = _fact(
        "inherited_unit:080.code_block",
        "inherited_unit",
        "```csharp\nusing Widget;\nnew Widget().Save();\n```",
    )
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, example, block))
    placed = _entry("inherited_unit:080.code_block", "additional_examples", "example:009")
    dispositions = {"dispositions": [placed]}
    plan = _plan(additional_example_ids=["example:002", "example:009"])
    decisions = {p.unit_id: p for p in placements(plan, dispositions, facts, "net")}
    assert decisions["inherited_unit:080.code_block"].outcome == "owned_elsewhere"
    assert placed_texts(list(decisions.values())) == {}


def test_planning_includes_every_verified_example_and_refuses_an_excluded_destination() -> None:
    plan = _plan(additional_example_ids=[])
    errors = plan_checks(plan, FACTS, dispositions=DISPOSITIONS, ecosystem="python")
    assert plan["additional_example_ids"] == ["example:002"]  # the contradicted one stays out
    # At a Glance's condition holds, so code includes it whatever the plan said and the
    # placement stands; only a destination the facts exclude is a defect.
    assert errors == []
    excluded = {"dispositions": [_entry("inherited_unit:014.paragraph", "enterprise_relationship")]}
    assert plan_checks(_plan(), FACTS, dispositions=excluded, ecosystem="python") == [
        "section enterprise_relationship is excluded at this revision but the reconciliation "
        "placed inherited_unit:014.paragraph there; place the unit in an included section or "
        "defer it, or the transaction fails closed naming it"
    ]
    omitted = _plan(additional_example_ids=[])
    for entry in omitted["sections"]:
        if entry["section_id"] == "additional_examples":
            entry["include"] = False
    plan_checks(omitted, FACTS)
    decision = next(e for e in omitted["sections"] if e["section_id"] == "additional_examples")
    assert decision["include"] is True and omitted["additional_example_ids"] == ["example:002"]


def test_a_command_block_is_never_dropped_for_overlap_but_restating_prose_is() -> None:
    dispositions = {
        "dispositions": [
            _entry("inherited_unit:074.paragraph", "development_testing", "build_test_asset:tests"),
            _entry(
                "inherited_unit:071.code_block", "development_testing", "build_test_asset:tests"
            ),
        ]
    }
    decisions = {p.unit_id: p for p in placements(_plan(), dispositions, FACTS, "python")}
    assert decisions["inherited_unit:074.paragraph"].outcome == "overlap"
    assert decisions["inherited_unit:074.paragraph"].overlap == ("build_test_asset:tests",)
    assert decisions["inherited_unit:071.code_block"].outcome == "placed"
