"""S4 output budget: a reply the schema admits must fit the manifest's max_output_tokens.

The defect (PDF-TypeScript, 2026-10-04): one 40-unit source_reconciliation reply reached
finish_reason length at 32,000 tokens. The same request later answered 4,666 tokens, so the
runaway is degenerate decoding, and the schema is what let it run: a disposition's fact_ids array
was bounded only by the batch's citable set (739 IDs there, more on other repositories), and
nothing bounded the batch's total. The same class ran away on Aspose.Cells for Go (2026-09-11,
1,047 repeated IDs in one array) and on Aspose.PDF for .NET (F27). The bound is structural: a
per-disposition citation cap, a destination enum, and a batch size derived from the worst reply
the schema admits at the budget's characters-per-token floor.
"""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.composition.components.shell import section_ids
from repository_presenter.components.readme.reconciliation import dispositions
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

REPOSITORY = "org/Aspose.Widget-FOSS-for-Python"
LOADED = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
BUDGET = LOADED.manifest.sampling.max_output_tokens
CITATION_CAP = 16  # the per-disposition cap the prompt states and the schema enforces


def _units(count: int) -> list[Fact]:
    return [
        Fact(
            f"inherited_unit:{index:05}.paragraph",
            "inherited_unit",
            f"Paragraph {index}.",
            (Evidence("README.md", None),),
        )
        for index in range(count)
    ]


def _long_citable_facts(units: int, symbols: int, name_chars: int = 40) -> FactsDocument:
    """The worst case a reply can meet: many citable facts behind many units. ``name_chars`` pads
    the member name, so a test can reach identifiers longer than any real repository's (the
    longest PDF-TypeScript fact ID is 55 characters)."""
    member = ("Member" * (name_chars // 6 + 1))[:name_chars]
    long_symbols = [
        Fact(
            f"public_symbol:aspose.document.namespace{index:04d}.{member.lower()}",
            "public_symbol",
            f"Aspose.Document.Namespace{index:04d}.{member}",
            (Evidence("src/x.py", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class"},
        )
        for index in range(symbols)
    ]
    return FactsDocument(REPOSITORY, "a" * 40, tuple(_units(units) + long_symbols))


def _forty_unit_schema(facts: FactsDocument) -> dict[str, Any]:
    """The schema for a 40-unit packet: the largest batch the S4 rule has ever made."""
    batch = list(facts.by_kind("inherited_unit"))[:40]
    return dispositions.reconciliation_schema(
        LOADED, batch, dispositions.reconciliation_batch_facts(facts, batch), {}
    )


def test_a_disposition_cites_a_bounded_number_of_facts_not_the_whole_citable_set() -> None:
    """Before: fact_ids.maxItems was the batch's citable-set size (700+ here), so a repeating
    citation list could run to the whole budget. After: a fixed per-disposition cap."""
    schema = _forty_unit_schema(_long_citable_facts(units=40, symbols=700))
    fact_ids = schema["properties"]["dispositions"]["items"]["properties"]["fact_ids"]
    assert len(fact_ids["items"]["enum"]) > CITATION_CAP
    assert fact_ids["maxItems"] <= CITATION_CAP


def test_destination_section_is_an_enum_of_the_shell_sections_or_null() -> None:
    """Before: destination_section was an unbounded string. After: the shell's own section IDs
    or null, the same enum treatment unit_id and fact_ids already have."""
    schema = _forty_unit_schema(_long_citable_facts(units=40, symbols=10))
    destination = schema["properties"]["dispositions"]["items"]["properties"]["destination_section"]
    options = destination["oneOf"]
    assert {"type": "null"} in options
    (string_option,) = [option for option in options if option != {"type": "null"}]
    assert string_option["enum"] == list(section_ids())


def test_a_full_batch_reply_the_schema_admits_fits_the_budget_at_the_floor_rate() -> None:
    """The expected output bound of a packet with N units: the longest reply the schema admits,
    serialized, divided by the conservative characters-per-token floor, fits max_output_tokens."""
    schema = _forty_unit_schema(_long_citable_facts(units=40, symbols=700))
    chars = dispositions.output_chars_bound(schema)
    assert chars is not None  # no field the schema leaves open makes the bound infinite
    assert chars / dispositions.OUTPUT_CHARS_PER_TOKEN_FLOOR <= BUDGET


def test_batch_size_shrinks_so_every_batch_reply_fits_the_budget_for_long_identifiers() -> None:
    """Before: every batch held 40 units whatever their identifiers cost. After: the batch size
    comes from the worst reply at the budget, so long identifiers mean smaller batches, and no
    unit is ever dropped (coverage stays exact and in document order)."""
    facts = _long_citable_facts(units=400, symbols=700, name_chars=140)
    batches = dispositions.reconciliation_batches(facts, BUDGET)
    assert sum(len(units) for _, units in batches) == 400
    assert [fact.id for _, units in batches for fact in units] == [
        fact.id for fact in facts.by_kind("inherited_unit")
    ]
    assert max(len(units) for _, units in batches) < 40
    for _, batch in batches:
        schema = dispositions.reconciliation_schema(
            LOADED, batch, dispositions.reconciliation_batch_facts(facts, batch), {}
        )
        chars = dispositions.output_chars_bound(schema)
        assert chars is not None
        assert chars / dispositions.OUTPUT_CHARS_PER_TOKEN_FLOOR <= BUDGET


def test_the_prompt_states_the_citation_cap_the_schema_enforces() -> None:
    """The prompt and the schema must agree: the prompt names the limit the reply is decoded
    under, so the job never has to learn it from a truncated reply."""
    assert f"at most {CITATION_CAP} fact IDs" in LOADED.manifest.system


def test_the_bound_constants_are_the_manifests_own_rationale_and_disposition_limits() -> None:
    """The batch size is computed from constants that name the manifest's own limits; this holds
    them to the manifest, so a manifest edit the bound does not follow fails here, not live."""
    properties = LOADED.manifest.output.schema_["properties"]["dispositions"]["items"]["properties"]
    assert properties["rationale"]["maxLength"] == dispositions._RATIONALE_MAX_CHARS
    assert list(properties["disposition"]["enum"]) == list(dispositions._DISPOSITIONS)


def test_a_unit_whose_longest_reply_cannot_fit_is_refused_before_any_call() -> None:
    """A budget no single unit's reply can meet is a configuration error, raised before a call is
    made: a batch that cannot fit is never sent to be truncated."""
    with pytest.raises(ConfigError, match="exceeds the source_reconciliation budget"):
        dispositions.reconciliation_batches(_long_citable_facts(units=3, symbols=5), 40)
