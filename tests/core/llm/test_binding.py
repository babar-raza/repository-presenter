"""The binding guard is structural: it reads ID keys, never prose."""

from __future__ import annotations

from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.binding import binding_errors, collect_ids, resolve_symbol_ids


def _fact(fact_id: str, kind: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, "value", (Evidence("README.md"),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        _fact("identity:repository", "identity"),
        _fact("example:001", "example"),
        _fact("example:002", "example", "CONTRADICTED"),
        _fact("format:input.obj", "format", "UNRESOLVED"),
        _fact("inherited_unit:001.heading", "inherited_unit"),
        _fact("inherited_unit:002.paragraph", "inherited_unit"),
    ),
)


def test_ids_are_collected_from_every_id_key_in_document_order() -> None:
    payload = {
        "summary": {"text": "x", "fact_ids": ["identity:repository"]},
        "plan": [
            {"quick_start_example_id": "example:001", "unit_ids": ["inherited_unit:001.heading"]},
            {"api_hubs": [{"symbol_fact_id": "public_symbol:x", "fact_ids": ["example:001"]}]},
            {"at_a_glance": {"input_format_ids": ["format:input.obj"]}},
        ],
        "dispositions": [{"unit_id": "inherited_unit:002.paragraph", "text": "not an id key"}],
    }
    cited = collect_ids(payload)
    assert cited.fact_ids == (
        "identity:repository",
        "example:001",
        "public_symbol:x",
        "example:001",
        "format:input.obj",
    )
    assert cited.unit_ids == ("inherited_unit:001.heading", "inherited_unit:002.paragraph")


def test_fact_bindings_require_known_supported_facts() -> None:
    good = {"units": [{"text": "x", "fact_ids": ["identity:repository", "example:001"]}]}
    assert binding_errors(good, FACTS, "fact_ids") == []
    bad = {
        "units": [
            {"fact_ids": ["identity:repository", "example:002", "format:input.obj", "nope:1"]},
            {"unit_id": "inherited_unit:999.list"},
        ]
    }
    assert binding_errors(bad, FACTS, "fact_ids") == [
        "fact example:002 is CONTRADICTED, not SUPPORTED",
        "fact format:input.obj is UNRESOLVED, not SUPPORTED",
        "unknown fact ID nope:1",
        "unknown inherited unit inherited_unit:999.list",
    ]
    assert (
        binding_errors(bad, FACTS, "selection_ids")[:2]
        == binding_errors(bad, FACTS, "fact_ids")[:2]
    )


def test_findings_may_cite_contradicted_facts_but_never_unknown_ones() -> None:
    findings = {"findings": [{"fact_ids": ["example:002"]}, {"fact_ids": ["missing:1"]}]}
    assert binding_errors(findings, FACTS, "finding_ids") == ["unknown fact ID missing:1"]


def test_unit_bindings_name_every_inherited_unit_exactly_once() -> None:
    complete = {
        "dispositions": [
            {"unit_id": "inherited_unit:001.heading"},
            {"unit_id": "inherited_unit:002.paragraph"},
        ]
    }
    assert binding_errors(complete, FACTS, "unit_ids") == []
    partial = {"dispositions": [{"unit_id": "inherited_unit:001.heading"}] * 2}
    assert binding_errors(partial, FACTS, "unit_ids") == [
        "no disposition for inherited units: inherited_unit:002.paragraph",
        "more than one disposition for: inherited_unit:001.heading",
    ]


def test_a_symbol_cited_by_its_read_path_binds_to_the_shortest_supported_fact() -> None:
    facts = FactsDocument(
        "org/repo",
        "a" * 40,
        (
            _fact("public_symbol:aspose.threed.shading.lambertmaterial", "public_symbol"),
            _fact(
                "public_symbol:aspose.threed.shading.lambertmaterial.lambertmaterial",
                "public_symbol",
            ),
            _fact("public_symbol:aspose.threed.scene", "public_symbol", "CONTRADICTED"),
        ),
    )
    payload = {
        "api_hubs": [{"symbol_fact_id": "public_symbol:aspose.threed.lambertmaterial"}],
        "core_capabilities": [
            {
                "fact_ids": [
                    "public_symbol:aspose.threed.lambertmaterial",
                    "public_symbol:aspose.threed.nothing",
                ]
            }
        ],
    }
    rewrites = resolve_symbol_ids(payload, facts)
    assert rewrites == [
        (
            "public_symbol:aspose.threed.lambertmaterial",
            "public_symbol:aspose.threed.shading.lambertmaterial",
        )
    ]
    assert (
        payload["api_hubs"][0]["symbol_fact_id"]
        == "public_symbol:aspose.threed.shading.lambertmaterial"
    )
    assert binding_errors(payload, facts, "selection_ids") == [
        "unknown fact ID public_symbol:aspose.threed.nothing"
    ]
    # A contradicted symbol is never a resolution target, and a known ID is left alone.
    scene = {"fact_ids": ["public_symbol:aspose.threed.scene", "public_symbol:x.scene"]}
    assert resolve_symbol_ids(scene, facts) == []


def test_a_repair_binds_its_own_changes_and_leaves_the_revised_output_to_its_stage() -> None:
    # revision_ids: the repair's change citations must be SUPPORTED; the revised output is the
    # causal stage's object and is bound by that stage's rules in the repair checks, so a
    # reconciliation repair may keep an omission that cites a CONTRADICTED example.
    repair = {
        "fingerprint": "f" * 64,
        "causal_stage": "S4",
        "revised_output": {
            "dispositions": [
                {"unit_id": "inherited_unit:001.heading", "fact_ids": ["example:002"]},
                {"unit_id": "inherited_unit:002.paragraph", "fact_ids": ["identity:repository"]},
            ]
        },
        "changes": [{"id": "R01", "fact_ids": ["identity:repository"]}],
    }
    assert binding_errors(repair, FACTS, "revision_ids") == []
    repair["changes"][0]["fact_ids"] = ["example:002", "nope:1"]
    assert binding_errors(repair, FACTS, "revision_ids") == [
        "fact example:002 is CONTRADICTED, not SUPPORTED",
        "unknown fact ID nope:1",
    ]
