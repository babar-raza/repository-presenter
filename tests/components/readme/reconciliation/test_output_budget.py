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

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.components.shell import section_ids
from repository_presenter.components.readme.reconciliation import dispositions
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.binding import binding_errors
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


# --- a reply that stops early must be able to close (Imaging-.NET, 2026-10-10) ----------------


def _imaging_fixture() -> str:
    path = Path(__file__).parent / "fixtures" / "53d5e87abd54.rejected-2.json"
    return str(json.loads(path.read_text(encoding="utf-8"))["content"])


def _imaging_batch() -> tuple[FactsDocument, list[Fact], dict[str, Any]]:
    """The 20-unit batch (inherited_unit:041-060) the retained re-ask reply answered, with every
    fact that reply cites present in the packet."""
    content = _imaging_fixture()
    cited = sorted(set(re.findall(r'"((?:[a-z_]+):[A-Za-z0-9_.]+)"\s*[,\]]', content)))
    cited = [fact_id for fact_id in cited if not fact_id.startswith("inherited_unit:")]
    kinds = {fact_id: fact_id.split(":", 1)[0] for fact_id in cited}
    units = [
        Fact(
            f"inherited_unit:{ordinal:03}.{suffix}",
            "inherited_unit",
            f"Unit {ordinal}.",
            (Evidence("README.md", None),),
        )
        for ordinal, suffix in zip(
            range(41, 61),
            [
                "code_block",
                "html_block",
                "heading",
                "paragraph",
                "html_block",
                "heading",
                "list",
                "html_block",
                "heading",
                "list",
                "heading",
                "list",
                "paragraph",
                "heading",
                "paragraph",
                "code_block",
                "paragraph",
                "paragraph",
                "heading",
                "paragraph",
            ],
            strict=True,
        )
    ]
    symbols = [Fact(fact_id, kinds[fact_id], "v", (Evidence("x"),)) for fact_id in cited]
    facts = FactsDocument(REPOSITORY, "a" * 40, tuple(units + symbols))
    batch = list(facts.by_kind("inherited_unit"))
    schema = dispositions.reconciliation_schema(
        LOADED, batch, dispositions.reconciliation_batch_facts(facts, batch), {}
    )
    return facts, batch, schema


def _imaging_reply() -> dict[str, Any]:
    """The 18 dispositions the model wrote before the whitespace, closed as a decoder allowed to
    stop would have closed them."""
    content = _imaging_fixture()
    head = content[: re.search(r"\s{100,}\Z", content).start()].rstrip()  # type: ignore[union-attr]
    reply = json.loads(head + "\n  ]\n}")
    assert isinstance(reply, dict)
    return reply


def test_the_retained_runaway_is_whitespace_after_a_complete_array_of_records() -> None:
    """The shape of the defect: not a repeating list but 45,000 characters of whitespace, because
    the array could not close at 18 of 20."""
    content = _imaging_fixture()
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)
    assert re.search(r"\s{100,}\Z", content)
    assert len(_imaging_reply()["dispositions"]) == 18


def test_a_batch_schema_has_no_floor_that_forbids_a_short_reply_from_closing() -> None:
    """Before: minItems equalled the batch size, so after 18 of 20 records the only continuation
    the grammar allowed besides a new record was whitespace, which it allows without end. After: the
    array may close, and the unit binding refuses the short reply by name."""
    _, batch, schema = _imaging_batch()
    reply = _imaging_reply()
    stale = copy.deepcopy(schema)
    stale["properties"]["dispositions"]["minItems"] = len(batch)  # the former schema
    assert not Draft202012Validator(stale).is_valid(reply)
    validator = Draft202012Validator(schema)
    assert validator.is_valid(reply)
    assert schema["properties"]["dispositions"]["maxItems"] == len(batch) == 20


def test_a_short_reply_is_refused_by_the_unit_binding_naming_what_is_missing() -> None:
    facts, batch, _ = _imaging_batch()
    batch_facts = dispositions.reconciliation_batch_facts(facts, batch)
    errors = binding_errors(_imaging_reply(), batch_facts, "unit_ids")
    assert len(errors) == 1
    assert "no disposition for inherited units" in errors[0]
    assert "inherited_unit:059.heading" in errors[0] and "inherited_unit:060.paragraph" in errors[0]


def test_a_reply_longer_than_the_batch_is_still_unrepresentable() -> None:
    """Negative control: dropping the floor kept the ceiling and the per-disposition caps."""
    _, _, schema = _imaging_batch()
    reply = _imaging_reply()
    reply["dispositions"] = [*reply["dispositions"], *reply["dispositions"]][:21]
    assert not Draft202012Validator(schema).is_valid(reply)
    props = schema["properties"]["dispositions"]["items"]["properties"]
    assert props["fact_ids"]["maxItems"] <= CITATION_CAP


def test_the_re_ask_asks_for_the_complete_object() -> None:
    template = LOADED.manifest.rejection_template
    assert "complete: a disposition for every unit of the original request" in template
