"""The binding guard is structural: it reads ID keys, never prose."""

from __future__ import annotations

from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.binding import binding_errors, collect_ids


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
