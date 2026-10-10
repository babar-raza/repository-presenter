"""Reconciliation: a bounded packet in, placement rules checked before use, a stable artifact."""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts.product_pages import BANNER_FACT_ID
from repository_presenter.components.readme.reconciliation.dispositions import (
    contradicted_code_units,
    contradicted_embedded_links,
    contradicted_link_hrefs,
    coordinate_neighbor_promises,
    merge_dispositions,
    normalize,
    placement_errors,
    reconcile_checks,
    reconciliation_batch_facts,
    reconciliation_batches,
    reconciliation_packet,
    reconciliation_schema,
    recover_uncited_prose_omits,
    rendering_fact_ids,
    summarize,
    uncited_omit_candidates,
    write_dispositions,
)
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import JobError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.binding import binding_errors
from repository_presenter.core.llm.jobs import CallStore, JobContext, JobResult, run_job, schema_for
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT, mock_gateway

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
MANIFEST = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"].manifest


def _fact(
    fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", detail: str = ""
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", detail or None),), polarity=polarity)  # type: ignore[arg-type]


def _symbol(path: str, symbol_kind: str) -> Fact:
    return Fact(
        f"public_symbol:{path.lower()}",
        "public_symbol",
        path,
        (Evidence("src/x.py", f"line 1; {symbol_kind}; public by name"),),
        attributes={"symbol_kind": symbol_kind},
    )


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("format:input.obj", "format", ".obj", "UNRESOLVED"),
        _fact("install_command:pip", "install_command", "pip install widget", "CONTRADICTED"),
        _fact(
            "example:001",
            "example",
            "print(1)",
            detail="lines 5-7; python fence; unit inherited_unit:003.code_block",
        ),
        _fact(
            "example:002",
            "example",
            "boom",
            "CONTRADICTED",
            "lines 9-11; python fence; unit inherited_unit:004.code_block",
        ),
        _fact("inherited_unit:001.heading", "inherited_unit", "# Widget"),
        _fact("inherited_unit:002.paragraph", "inherited_unit", "Prose."),
        _fact("inherited_unit:003.code_block", "inherited_unit", "```python\nprint(1)\n```"),
        _fact("inherited_unit:004.code_block", "inherited_unit", "```python\nboom\n```"),
    ),
)


def _entry(
    unit: str, disposition: str, destination: str | None, *fact_ids: str
) -> dict[str, object]:
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": list(fact_ids),
        "rationale": "because",
    }


def test_the_packet_carries_every_unit_the_polar_facts_and_the_shell() -> None:
    batch = list(FACTS.by_kind("inherited_unit"))
    packet = reconciliation_packet(ENTRY, FACTS, {"product_summary": {}}, MANIFEST, batch)
    assert packet["repository"] == ENTRY.repository
    assert [unit["id"] for unit in packet["inherited_units"]] == [
        "inherited_unit:001.heading",
        "inherited_unit:002.paragraph",
        "inherited_unit:003.code_block",
        "inherited_unit:004.code_block",
    ]
    assert packet["inherited_units"][2]["type"] == "code_block"
    by_id = {record["id"]: record for record in packet["facts"]}
    assert set(by_id) == {
        "identity:repository",
        "install_command:pip",
        "example:001",
        "example:002",
    }
    assert by_id["install_command:pip"]["polarity"] == "CONTRADICTED"
    assert "inherited_unit:001.heading" not in by_id
    assert packet["investigation"] == {"product_summary": {}}
    assert [section["id"] for section in packet["sections"]][:2] == ["identity", "badges"]
    assert reconciliation_packet(ENTRY, FACTS, {"product_summary": {}}, MANIFEST, batch) == packet


def test_a_batch_packet_carries_only_its_own_units_not_every_inherited_unit() -> None:
    """PHASE0/G: batch_units scopes the packet to one reconciliation call's own units - the other
    units in the document (here, the first two) never enter this batch's own packet at all."""
    batch = list(FACTS.by_kind("inherited_unit"))[2:]
    packet = reconciliation_packet(ENTRY, FACTS, {}, MANIFEST, batch)
    assert [unit["id"] for unit in packet["inherited_units"]] == [
        "inherited_unit:003.code_block",
        "inherited_unit:004.code_block",
    ]


def test_the_packet_carries_a_deeply_rooted_repositorys_own_types() -> None:
    """G4-W17 arrival item 40. The packet bounded public symbols by dotted depth, which is shaped
    by the package root, so Aspose.Page for Python (root `aspose.page`) reached S4 with about
    seven namespace strings of its 570 symbols and the job - twice - cited
    `public_symbol:aspose.page.common`, a real directory of that repository
    (`src/aspose/page/common/` at the pinned revision) of exactly the shape of the only symbols
    it had been shown. Bounding by the kind the extractor records puts the types back."""
    document = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _symbol("aspose.page.ps", "module"),
            _symbol("aspose.page.ps.PsDocument", "class"),
            _symbol("aspose.page.ps.PsDocument.save", "method"),
            _symbol("aspose.page.common.RenderModel", "class"),
        ),
    )
    batch = list(document.by_kind("inherited_unit"))
    values = {
        record["value"]
        for record in reconciliation_packet(ENTRY, document, {}, MANIFEST, batch)["facts"]
        if record["kind"] == "public_symbol"
    }
    assert values == {
        "aspose.page.ps",
        "aspose.page.ps.PsDocument",
        "aspose.page.common.RenderModel",
    }
    # A member of a type is still out: the kind bound replaces the depth proxy, it does not lift
    # it, so the packet stays bounded for a large surface exactly as before.
    assert "aspose.page.ps.PsDocument.save" not in values


def _inherited_units_facts(count: int) -> FactsDocument:
    # A minimal document of exactly `count` inherited_unit facts - FACTS's own small, fixed
    # baseline set would otherwise skew a 10x ratio comparison at these small counts.
    return FactsDocument(
        ENTRY.repository,
        "a" * 40,
        tuple(
            _fact(f"inherited_unit:{i:05}.paragraph", "inherited_unit", f"Paragraph {i}.")
            for i in range(count)
        ),
    )


def test_reconciliation_batches_bounds_each_batchs_own_size_not_the_batch_count() -> None:
    """PHASE0/G: the real fix for J1/G1a's own finding ('reconciliation_packet()'s inherited_units
    field lists every inherited_unit fact directly, no cap') is not a cap on the total - every
    unit still needs a disposition - it is a cap on each individual call's own batch size. A
    10x larger repository gets roughly 10x more batches, each still bounded to
    _RECONCILIATION_BATCH units - proven directly against reconciliation_batches() rather than
    against reconciliation_packet()/reconciliation_schema() (the previous xfail's own target),
    since those two now require an explicit, already-bounded batch and can no longer even be
    called in a way that would grow unboundedly - the growth question has moved to the
    function that decides how many batches there are, which this test now covers instead."""
    base = reconciliation_batches(_inherited_units_facts(200), MANIFEST.sampling.max_output_tokens)
    tenx = reconciliation_batches(_inherited_units_facts(2000), MANIFEST.sampling.max_output_tokens)
    assert all(len(units) <= 40 for _, units in base)
    assert all(len(units) <= 40 for _, units in tenx)
    # Total coverage is preserved exactly - batching never drops a unit.
    assert sum(len(units) for _, units in base) == 200
    assert sum(len(units) for _, units in tenx) == 2000
    # Batch *count* correctly grows in proportion to total units (every unit still needs its own
    # disposition somewhere - unlike SYMBOL_CAP/LINK_CAP/EXAMPLE_CAP, there is no "drop the
    # rest" option here) - what stays bounded is each batch's own size, asserted above.
    assert len(base) == 5 and len(tenx) == 50


def test_reconciliation_batches_covers_every_unit_exactly_once_in_document_order() -> None:
    facts = _inherited_units_facts(85)
    batches = reconciliation_batches(facts, MANIFEST.sampling.max_output_tokens)
    assert [batch_id for batch_id, _ in batches] == [
        "reconciliation#1",
        "reconciliation#2",
        "reconciliation#3",
    ]
    all_ids = [fact.id for _, units in batches for fact in units]
    assert all_ids == [fact.id for fact in facts.by_kind("inherited_unit")]
    assert len(all_ids) == len(set(all_ids)) == 85


def test_reconciliation_batch_facts_narrows_inherited_units_only() -> None:
    facts = _inherited_units_facts(85)
    batches = reconciliation_batches(facts, MANIFEST.sampling.max_output_tokens)
    _, batch_units = batches[1]  # the middle batch: units 40-79 (0-indexed 40:80)
    batch_facts = reconciliation_batch_facts(facts, batch_units)
    assert [fact.id for fact in batch_facts.by_kind("inherited_unit")] == [
        fact.id for fact in batch_units
    ]
    assert len(batch_facts.by_kind("inherited_unit")) == 40
    # repository/source_revision/schema_version travel through unchanged - only the one kind
    # this exists to narrow is touched.
    assert batch_facts.repository == facts.repository
    assert batch_facts.source_revision == facts.source_revision
    assert batch_facts.schema_version == facts.schema_version


def test_a_batchs_own_dispositions_satisfy_binding_errors_against_its_own_batch_facts() -> None:
    """PHASE0/G: the real bug found live against Cells-Rust, reproduced here without a live call.

    core/llm/binding.py's binding_errors recomputes "every inherited unit expected" from
    whatever FactsDocument it is given - before reconciliation_batch_facts() existed, every
    batch's own call was judged against the WHOLE repository's inherited_unit facts, so any
    batch but the last was always rejected for "missing" units outside its own 40. A batch's own
    dispositions (covering only its own units) must satisfy binding_errors when judged against
    that SAME batch's own scoped facts - not the whole document."""
    facts = _inherited_units_facts(85)
    batches = reconciliation_batches(facts, MANIFEST.sampling.max_output_tokens)
    for _, batch_units in batches:
        batch_facts = reconciliation_batch_facts(facts, batch_units)
        payload = {
            "dispositions": [_entry(fact.id, "OMIT_UNSUPPORTED", None) for fact in batch_units]
        }
        assert binding_errors(payload, batch_facts, "unit_ids") == []


def test_a_batchs_own_dispositions_do_not_satisfy_binding_errors_against_the_whole_document() -> (
    None
):
    """The inverse of the test above: proves the bug would still be caught if
    reconciliation_batch_facts() were ever accidentally skipped at a real call site - a batch's
    own dispositions alone can never satisfy the unscoped, whole-document expectation."""
    facts = _inherited_units_facts(85)
    _, first_batch_units = reconciliation_batches(facts, MANIFEST.sampling.max_output_tokens)[0]
    payload = {
        "dispositions": [_entry(fact.id, "OMIT_UNSUPPORTED", None) for fact in first_batch_units]
    }
    errors = binding_errors(payload, facts, "unit_ids")
    assert errors and "no disposition for inherited units" in errors[0]


def test_merge_dispositions_concatenates_every_batchs_output_in_batch_order() -> None:
    outputs = [
        {"dispositions": [_entry("inherited_unit:001.heading", "VERIFIED_PRESERVE", "license")]},
        {"dispositions": [_entry("inherited_unit:040.paragraph", "OMIT_UNSUPPORTED", None)]},
    ]
    merged = merge_dispositions(outputs)
    assert [entry["unit_id"] for entry in merged["dispositions"]] == [
        "inherited_unit:001.heading",
        "inherited_unit:040.paragraph",
    ]


def test_merge_dispositions_of_no_batches_is_an_empty_list() -> None:
    assert merge_dispositions([]) == {"dispositions": []}


def test_placements_into_deterministic_sections_fold_into_supersessions() -> None:
    assert rendering_fact_ids("installation", FACTS) == []
    assert rendering_fact_ids("identity", FACTS) == ["identity:repository"]
    output = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "VERIFIED_PRESERVE", "identity"),
            _entry("inherited_unit:002.paragraph", "SUPERSEDE_REDUNDANT", "identity"),
            _entry("inherited_unit:003.code_block", "CORRECT_WITH_EVIDENCE", "installation"),
            _entry("inherited_unit:004.code_block", "SUPERSEDE_REDUNDANT", None),
        ]
    }
    errors = normalize(output, FACTS)
    # A required section (owner "D") is never excluded, but "required" means it always appears,
    # not that it always has content: FACTS carries no SUPPORTED install fact, so installation
    # renders nothing here. Measured 2026-09-06 on Aspose.Slides for .NET, genuinely unpublished:
    # the same placement survived one re-ask unchanged, so it is deferred rather than re-asked
    # again - the model cannot invent evidence a section lacks.
    assert errors == []
    folded = output["dispositions"]
    assert folded[0]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert folded[0]["fact_ids"] == ["identity:repository"]
    assert folded[0]["destination_section"] == "identity"
    assert folded[1]["fact_ids"] == ["identity:repository"]
    assert folded[2]["disposition"] == "DEFER_UNRESOLVED"
    assert folded[2]["destination_section"] is None
    remaining = placement_errors(output, FACTS)
    assert remaining == [
        "inherited_unit:004.code_block: SUPERSEDE_REDUNDANT names the section whose content "
        "renders or covers the unit in destination_section, or cites at least one fact ID",
    ]
    assert reconcile_checks(output, FACTS) == errors + remaining


def test_two_deterministic_sections_rendering_nothing_both_fold_in_one_pass() -> None:
    """G4-W17 arrival item 1. Lane B's Aspose.3D for TypeScript disposition: no npm package
    (install_command:pip here stands in, CONTRADICTED) and no licence file at all, so both
    `installation` and `license` render nothing - the reported failure was two placements
    rejected together, not one. `rendering_fact_ids` already reads a `FACTS` fixture with no
    license fact of any kind, exactly that repository's shape; the fold in `normalize` is
    generic over every owner-D section, not installation-specific, so both units fold to
    DEFER_UNRESOLVED with zero remaining errors and no re-ask - the prompt needs nothing added
    to tell the model what already never reaches it as a live choice."""
    assert rendering_fact_ids("license", FACTS) == []
    output = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "CORRECT_WITH_EVIDENCE", "installation"),
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "license"),
        ]
    }
    assert reconcile_checks(output, FACTS) == []
    assert [d["disposition"] for d in output["dispositions"]] == [
        "DEFER_UNRESOLVED",
        "DEFER_UNRESOLVED",
    ]
    assert [d["destination_section"] for d in output["dispositions"]] == [None, None]


def test_a_duplicate_subject_placed_into_the_same_section_twice_is_superseded_by_the_first() -> (
    None
):
    """G4-W17 arrival item 98 (BCPY-02). Measured on BarCode-Python after items 79/96 confirmed
    fixed: two adjacent sentences both pointed the reader at the same examples/ directory, one
    correctly VERIFIED_PRESERVE'd in additional_examples and one VERIFIED_MOVE'd there from a
    separate Development-and-Testing section, both citing the same build_test_asset fact -
    repair has no path to a VERIFIED_MOVE/VERIFIED_PRESERVE disposition at all (neither
    repair/rounds.py nor repair/targeted.py reads either value), so composing both would have
    produced a permanent, repair-unreachable duplication.
    """
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact("build_test_asset:examples", "build_test_asset", "examples/"),
            # additional_examples' own condition needs 2+ SUPPORTED examples; FACTS carries
            # exactly one (example:001) plus one CONTRADICTED - a second SUPPORTED example is
            # added purely to keep the section present, unrelated to what this test measures.
            _fact("example:003", "example", "print(3)"),
        ),
    )
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:001.paragraph",
                "VERIFIED_PRESERVE",
                "additional_examples",
                "build_test_asset:examples",
            ),
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "additional_examples",
                "build_test_asset:examples",
            ),
        ]
    }
    assert normalize(output, facts) == []
    folded = output["dispositions"]
    # The first claim on (additional_examples, build_test_asset:examples) stands untouched.
    assert folded[0]["disposition"] == "VERIFIED_PRESERVE"
    assert folded[0]["destination_section"] == "additional_examples"
    # The second, sharing the identical non-trivial citation, is superseded by the first rather
    # than composed again.
    assert folded[1]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert folded[1]["destination_section"] == "additional_examples"
    assert placement_errors(output, facts) == []


def test_the_duplicate_subject_guard_ignores_identity_citations_and_different_sections() -> None:
    """Mutation controls for item 98's guard: an identity/package citation is too common to be
    evidence of real subject overlap (composition/authoring.py's own ``unit_checks`` treats the
    same two kinds as neutral, for the identical reason), and two units placed into different
    sections are never in competition even when they happen to share a citation."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact("build_test_asset:examples", "build_test_asset", "examples/"),
            # additional_examples' own condition needs 2+ SUPPORTED examples; FACTS carries
            # exactly one (example:001) plus one CONTRADICTED - a second SUPPORTED example is
            # added purely to keep the section present, unrelated to what this test measures.
            _fact("example:003", "example", "print(3)"),
        ),
    )
    # Two units sharing only identity:repository, both placed in additional_examples: neither
    # is downgraded - a citation every unit could plausibly carry proves nothing about overlap.
    trivial = {
        "dispositions": [
            _entry(
                "inherited_unit:001.paragraph",
                "VERIFIED_PRESERVE",
                "additional_examples",
                "identity:repository",
            ),
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "additional_examples",
                "identity:repository",
            ),
        ]
    }
    assert normalize(trivial, facts) == []
    assert [d["disposition"] for d in trivial["dispositions"]] == [
        "VERIFIED_PRESERVE",
        "VERIFIED_MOVE",
    ]
    # The identical non-trivial fact, but two different destination sections: no overlap to
    # guard against - each section covers its own subject.
    different_sections = {
        "dispositions": [
            _entry(
                "inherited_unit:001.paragraph",
                "VERIFIED_PRESERVE",
                "additional_examples",
                "build_test_asset:examples",
            ),
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "scope_limitations",
                "build_test_asset:examples",
            ),
        ]
    }
    assert normalize(different_sections, facts) == []
    assert [d["disposition"] for d in different_sections["dispositions"]] == [
        "VERIFIED_PRESERVE",
        "VERIFIED_MOVE",
    ]


def test_a_placed_dispositions_fact_ids_gain_every_symbol_its_own_sentence_names() -> None:
    """G4-W17 arrival item 110 (LANE-B-W14R6-F1). Measured on Aspose.3D for TypeScript:
    inherited_unit:077.list named a dozen not-implemented symbols in one verbatim sentence, but
    the S4 job's own sampled fact_ids cited only some of them, leaving the rest with no path into
    S6's own citation set even though S6's split mechanism (the sentence's own FileSystem bullet)
    is proven to work once offered a symbol. normalize() now adds every SUPPORTED
    public_symbol/import_path fact the unit's own text spells, not only the sampled subset."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:005.list",
                "inherited_unit",
                "Widget.render(), Widget.save(), and Widget.optimize() all throw not "
                "implemented errors.",
            ),
            _symbol("Widget.render", "method"),
            _symbol("Widget.save", "method"),
            # Named in the identical sentence but UNRESOLVED: never added - only a fact already
            # SUPPORTED corroborates anything.
            _fact(
                "public_symbol:widget.optimize", "public_symbol", "Widget.optimize", "UNRESOLVED"
            ),
            # SUPPORTED but never spelled in this sentence: never added - scoped to this unit's
            # own text, exactly as cited_inherited_identifiers is scoped to a unit's own citation.
            _symbol("Widget.unused", "method"),
        ),
    )
    output = {
        "dispositions": [
            # The S4 job's own sample cited only Widget.render - Widget.save is equally SUPPORTED
            # and equally named in the identical sentence, but was never sampled.
            _entry(
                "inherited_unit:005.list",
                "VERIFIED_PRESERVE",
                "scope_limitations",
                "public_symbol:widget.render",
            )
        ]
    }
    assert normalize(output, facts) == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert set(entry["fact_ids"]) == {"public_symbol:widget.render", "public_symbol:widget.save"}


def test_the_symbol_widening_pass_never_touches_a_disposition_that_will_not_be_composed() -> None:
    """Mutation control: an OMIT_UNSUPPORTED unit (never composed) is left exactly as the job
    wrote it - widening its fact_ids would only clutter a record nothing ever reads."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:005.list",
                "inherited_unit",
                "Widget.render() throws a not implemented error.",
            ),
            _symbol("Widget.render", "method"),
        ),
    )
    output = {
        "dispositions": [
            _entry("inherited_unit:005.list", "OMIT_UNSUPPORTED", None),
        ]
    }
    assert normalize(output, facts) == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "OMIT_UNSUPPORTED"
    assert entry["fact_ids"] == []


def test_placement_rules_are_checked_before_use() -> None:
    assert contradicted_code_units(FACTS) == {"inherited_unit:004.code_block"}
    good = {
        "dispositions": [
            _entry(
                "inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", None, "identity:repository"
            ),
            _entry("inherited_unit:002.paragraph", "VERIFIED_REWRITE", "opening"),
            _entry(
                "inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start", "example:001"
            ),
            _entry("inherited_unit:004.code_block", "OMIT_UNSUPPORTED", None, "example:002"),
        ]
    }
    assert placement_errors(good, FACTS) == []
    bad = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", None),
            _entry("inherited_unit:002.paragraph", "VERIFIED_MOVE", "installation"),
            _entry("inherited_unit:003.code_block", "DEFER_UNRESOLVED", "quick_start"),
            _entry("inherited_unit:004.code_block", "VERIFIED_PRESERVE", "quick_start"),
        ]
    }
    errors = placement_errors(bad, FACTS)
    assert errors[0] == (
        "inherited_unit:001.heading: SUPERSEDE_REDUNDANT names the section whose content "
        "renders or covers the unit in destination_section, or cites at least one fact ID"
    )
    assert errors[1].startswith(
        "inherited_unit:002.paragraph: VERIFIED_MOVE needs a destination the shell can hold ("
    )
    assert errors[1].endswith("); got 'installation'")
    assert (
        errors[2]
        == "inherited_unit:003.code_block: DEFER_UNRESOLVED takes no destination; got 'quick_start'"
    )
    assert (
        errors[3]
        == "inherited_unit:004.code_block: its example is CONTRADICTED and cannot be placed"
    )
    assert dict(summarize(good)) == {
        "SUPERSEDE_REDUNDANT": 1,
        "VERIFIED_REWRITE": 1,
        "VERIFIED_PRESERVE": 1,
        "OMIT_UNSUPPORTED": 1,
    }


def test_a_preserved_units_own_contradicted_link_folds_to_rewrite() -> None:
    """Item 90. Measured on Words-.NET: inherited_unit:068.paragraph preserved a broken relative
    ../../issues link verbatim - VERIFIED_PRESERVE renders a unit's raw markdown as written, so
    reconciliation's own knowledge that the link is CONTRADICTED never reached the sealed README,
    with no repair path three stages later. normalize() now folds the placement to
    VERIFIED_REWRITE, so S6 re-authors the wording from facts instead of copying the dead link
    through - but never cites the broken link itself, since composition/planning.py's own
    _missing_links backstop would otherwise treat any such VERIFIED_REWRITE citation as a real,
    renderable link and add it back into the plan (and then reject the plan outright, since that
    backstop only ever adds a SUPPORTED link_facts target)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:010.paragraph",
                "inherited_unit",
                "See our [issue tracker](../../issues) for open bugs.",
            ),
            _fact(
                "link_target:001",
                "link_target",
                "../../issues",
                "CONTRADICTED",
                "line 1; relative; text 'issue tracker'",
            ),
        ),
    )
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:010.paragraph",
                "VERIFIED_PRESERVE",
                "scope_limitations",
                "identity:repository",
            ),
        ]
    }
    assert normalize(output, facts) == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_REWRITE"
    assert entry["destination_section"] == "scope_limitations"
    assert "link_target:001" not in entry["fact_ids"]
    assert entry["fact_ids"] == ["identity:repository"]


def test_a_moved_units_own_contradicted_link_also_folds_to_rewrite() -> None:
    """Item 90 covers VERIFIED_MOVE identically to VERIFIED_PRESERVE - both render the unit's raw
    markdown verbatim in a different section, so both carry the identical repair gap."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:010.paragraph",
                "inherited_unit",
                "See our [issue tracker](../../issues) for open bugs.",
            ),
            _fact(
                "link_target:001",
                "link_target",
                "../../issues",
                "CONTRADICTED",
                "line 1; relative; text 'issue tracker'",
            ),
        ),
    )
    output = {
        "dispositions": [
            _entry("inherited_unit:010.paragraph", "VERIFIED_MOVE", "scope_limitations"),
        ]
    }
    assert normalize(output, facts) == []
    assert output["dispositions"][0]["disposition"] == "VERIFIED_REWRITE"


def test_a_preserved_unit_with_no_contradicted_link_is_left_alone() -> None:
    """Mutation control: a VERIFIED_PRESERVE unit whose only embedded link is SUPPORTED is not
    touched by the item 90 fold - proves the fold fires on the CONTRADICTED link, not on the mere
    presence of a link."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:010.paragraph",
                "inherited_unit",
                "See our [issue tracker](../../issues) for open bugs.",
            ),
            _fact(
                "link_target:001",
                "link_target",
                "../../issues",
                "SUPPORTED",
                "line 1; relative; text 'issue tracker'",
            ),
        ),
    )
    output = {
        "dispositions": [
            _entry("inherited_unit:010.paragraph", "VERIFIED_PRESERVE", "scope_limitations"),
        ]
    }
    assert normalize(output, facts) == []
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_badge_row_units_own_contradicted_link_is_not_folded() -> None:
    """The shell owns badge_row/heading units entirely (_SHELL_OWNED); item 90's fold is scoped
    to ordinary preserved/moved prose, never shell-owned chrome the banner fold below already
    owns."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:011.badge_row",
                "inherited_unit",
                "[![Build](../../broken.svg)](../../broken)",
            ),
            _fact(
                "link_target:002",
                "link_target",
                "../../broken",
                "CONTRADICTED",
                "line 1; relative; text ''",
            ),
        ),
    )
    output = {
        "dispositions": [
            _entry("inherited_unit:011.badge_row", "VERIFIED_PRESERVE", "scope_limitations"),
        ]
    }
    normalize(output, facts)
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_renderer_owned_contradicted_link_is_excluded_from_the_fold() -> None:
    """Item 90's "non-renderer-owned" qualifier: the banner/homepage/enterprise link_target facts
    are the renderer's own live lookups (composition/planning.py's identical _SHELL_OWNED_LINKS
    exclusion), never CONTRADICTED in practice, but excluded by fact ID here too so a future
    change to product_pages.py could never make this fold fire on one of them - contradicted_
    link_hrefs() (not normalize() directly, since the three IDs are never really CONTRADICTED)
    proves the exclusion itself."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(BANNER_FACT_ID, "link_target", "https://x/banner.png", "CONTRADICTED"),
        ),
    )
    assert contradicted_link_hrefs(facts) == {}
    assert contradicted_embedded_links(
        "See ![banner](https://x/banner.png) here.",
        {"https://x/banner.png": BANNER_FACT_ID},
    ) == {BANNER_FACT_ID}


def test_a_colon_ending_units_promise_is_deferred_when_its_neighbor_code_block_is_dropped() -> None:
    """BC-10 coherence-gap, aspose-slides-foss/Aspose.Slides-FOSS-for-.NET (docs/DECISION_LOG.md
    2026-09-17 14:14 UTC, corroborated 2026-09-24 10:14 UTC): inherited_unit:033.paragraph
    ("Three namespaces cover every sample on this page, and each sample below assumes all
    three:") was VERIFIED_PRESERVE'd while inherited_unit:034.code_block (the sample the colon
    promises) fell to OMIT_UNSUPPORTED - each independently correct on its own narrow grounds,
    but the preserved sentence then survived alone, promising content the candidate never
    delivers. Reproduced here with the exact unit shape (a colon-ending paragraph immediately
    followed, in document order, by the code block it introduces)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:033.paragraph",
                "inherited_unit",
                "Three namespaces cover every sample on this page, and each sample below "
                "assumes all three:",
            ),
            _fact("inherited_unit:034.code_block", "inherited_unit", "```csharp\nusing X;\n```"),
        ),
    )
    dispositions = {
        "dispositions": [
            _entry("inherited_unit:033.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
            _entry("inherited_unit:034.code_block", "OMIT_UNSUPPORTED", None),
        ]
    }
    result = coordinate_neighbor_promises(dispositions, facts)
    assert result is dispositions
    folded = {entry["unit_id"]: entry for entry in dispositions["dispositions"]}
    assert folded["inherited_unit:033.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:033.paragraph"]["destination_section"] is None
    # The dropped neighbor itself is untouched - this fold only ever revisits the *promising*
    # unit, never the one already correctly disposed on its own narrow grounds.
    assert folded["inherited_unit:034.code_block"]["disposition"] == "OMIT_UNSUPPORTED"


def test_the_defect_survives_per_batch_checks_until_the_merged_document_is_coordinated() -> None:
    """The root cause, reproduced end to end: reconcile_checks (normalize()) judges each batch's
    own dispositions independently, by design, so two separate batches - each individually
    correct and each passing its own reconcile_checks - can still merge into an incoherent
    document. coordinate_neighbor_promises is the one pass that sees the merged whole."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            # additional_examples' own condition needs 2+ SUPPORTED examples; FACTS carries
            # exactly one (example:001) plus one CONTRADICTED - a second SUPPORTED example is
            # added so unit 033's VERIFIED_PRESERVE genuinely survives normalize()'s own absent-
            # section fold, isolating what this test measures to the neighbor-coordination gap.
            _fact("example:003", "example", "print(3)"),
            _fact(
                "inherited_unit:033.paragraph",
                "inherited_unit",
                "Three namespaces cover every sample on this page, and each sample below "
                "assumes all three:",
            ),
            _fact("inherited_unit:034.code_block", "inherited_unit", "```csharp\nusing X;\n```"),
        ),
    )
    # Batch 1 reconciles unit 033 alone; batch 2 (a different source_reconciliation call)
    # reconciles unit 034 alone - neither batch's own reconcile_checks call can see the other's
    # output, exactly as reconciliation_batches()/run_round() split real repositories.
    batch_1 = {
        "dispositions": [
            _entry("inherited_unit:033.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
        ]
    }
    batch_2 = {"dispositions": [_entry("inherited_unit:034.code_block", "OMIT_UNSUPPORTED", None)]}
    assert normalize(batch_1, facts) == []
    assert placement_errors(batch_1, facts) == []
    assert normalize(batch_2, facts) == []
    assert placement_errors(batch_2, facts) == []
    # Each batch, checked alone, is accepted with the incoherent shape still standing.
    assert batch_1["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"
    assert batch_2["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"
    merged = merge_dispositions([batch_1, batch_2])
    coordinate_neighbor_promises(merged, facts)
    folded = {entry["unit_id"]: entry for entry in merged["dispositions"]}
    assert folded["inherited_unit:033.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:034.code_block"]["disposition"] == "OMIT_UNSUPPORTED"


def test_a_colon_ending_units_promise_is_kept_when_its_neighbor_code_block_survives() -> None:
    """Mutation control: the neighbor's own disposition still renders content (any PLACING
    outcome, or SUPERSEDE_REDUNDANT - covered elsewhere, e.g. by a deterministic section), so the
    colon's promise holds and the preserved sentence is left exactly as reconciled."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:033.paragraph",
                "inherited_unit",
                "Three namespaces cover every sample on this page, and each sample below "
                "assumes all three:",
            ),
            _fact("inherited_unit:034.code_block", "inherited_unit", "```csharp\nusing X;\n```"),
        ),
    )
    for surviving_disposition in ("VERIFIED_PRESERVE", "SUPERSEDE_REDUNDANT"):
        dispositions = {
            "dispositions": [
                _entry("inherited_unit:033.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
                _entry(
                    "inherited_unit:034.code_block", surviving_disposition, "additional_examples"
                ),
            ]
        }
        coordinate_neighbor_promises(dispositions, facts)
        assert dispositions["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_unit_with_no_trailing_colon_makes_no_promise_to_coordinate() -> None:
    """Mutation control: the detection is the literal trailing colon, never the mere fact that a
    paragraph precedes a dropped code block - a unit that makes no forward reference is left
    alone even when its neighbor is dropped."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:033.paragraph",
                "inherited_unit",
                "Three namespaces cover every sample on this page.",
            ),
            _fact("inherited_unit:034.code_block", "inherited_unit", "```csharp\nusing X;\n```"),
        ),
    )
    dispositions = {
        "dispositions": [
            _entry("inherited_unit:033.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
            _entry("inherited_unit:034.code_block", "OMIT_UNSUPPORTED", None),
        ]
    }
    coordinate_neighbor_promises(dispositions, facts)
    assert dispositions["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_non_adjacent_dropped_unit_is_not_coordinated() -> None:
    """Mutation control: only the immediately-following ordinal is a promise target - a dropped
    unit two or more ordinals away is not this fix's scope (docs/DECISION_LOG.md's own 2026-09-24
    10:14 UTC entry names this harder, non-adjacent case as a separate, unresolved gap)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:033.paragraph",
                "inherited_unit",
                "Three namespaces cover every sample on this page, and each sample below "
                "assumes all three:",
            ),
            _fact("inherited_unit:034.paragraph", "inherited_unit", "An unrelated aside."),
            _fact("inherited_unit:035.code_block", "inherited_unit", "```csharp\nusing X;\n```"),
        ),
    )
    dispositions = {
        "dispositions": [
            _entry("inherited_unit:033.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
            _entry("inherited_unit:034.paragraph", "VERIFIED_PRESERVE", "additional_examples"),
            _entry("inherited_unit:035.code_block", "OMIT_UNSUPPORTED", None),
        ]
    }
    coordinate_neighbor_promises(dispositions, facts)
    assert dispositions["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_the_artifact_is_deterministic_json(tmp_path: Path) -> None:
    output = {"dispositions": [_entry("inherited_unit:001.heading", "NON_CONTENT", None)]}
    path = tmp_path / "t" / "dispositions.json"
    digest = write_dispositions(output, path)
    raw = path.read_bytes()
    assert raw.startswith(b'{\n  "dispositions": [\n    {\n      "destination_section": null,')
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert json.loads(raw) == output
    assert write_dispositions(output, path) == digest


def _prose_omit_facts() -> FactsDocument:
    """FACTS, plus a second prose paragraph and an html block, for the uncited-omission rules."""
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact("inherited_unit:005.paragraph", "inherited_unit", "Second prose unit."),
            _fact("inherited_unit:006.html_block", "inherited_unit", "<p>wrapper</p>"),
        ),
    )


def test_an_uncited_prose_omit_is_refused_with_its_typed_reason() -> None:
    facts = _prose_omit_facts()
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "OMIT_UNSUPPORTED", None),
            _entry("inherited_unit:005.paragraph", "OMIT_UNSUPPORTED", None),
        ]
    }
    errors = placement_errors(output, facts)
    assert len(errors) == 2
    assert errors[0].startswith("inherited_unit:002.paragraph: uncited_prose_omit: ")
    assert errors[1].startswith("inherited_unit:005.paragraph: uncited_prose_omit: ")
    # the repair message quotes the unit's exact text and asks for a citation or a placement
    assert 'the unit\'s exact text is "Prose."' in errors[0]
    assert "Cite the supporting fact IDs or place the unit" in errors[0]
    # No fact's identifier is spelled in "Prose.": the candidate-surfacing clause is absent, and
    # the re-ask stays the plain, candidate-free form (#1008 repair round, no-overlap case).
    assert "already spells these SUPPORTED facts" not in errors[0]


def _pdf_typescript_omit_facts() -> FactsDocument:
    """Reproduces the PDF-TypeScript diagnosis (#1008 repair round): two inherited units
    (``014.list``, ``016.list``) each naming several public symbols verbatim in their own text,
    every one of them SUPPORTED, that the sealed candidate's S4 run omitted with no citation at
    all - the gap this round closes is that the re-ask never pointed back at this unused
    evidence. Matches the diagnosis's own fact-ID list exactly: ``parsecontentstream``,
    ``document.save``, ``savedocxfile``, ``parsehtml``, ``parsemarkdown``, and
    ``saveoptions.compressed``/``encrypt``/``incremental``/``linearized``/``streamfilter``
    (``_symbol()``'s own lowercasing of each path)."""
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:014.list",
                "inherited_unit",
                "Parse a document with ParseContentStream, then Document.Save, SaveDocxFile, "
                "ParseHtml, and ParseMarkdown write it back out.",
            ),
            _fact(
                "inherited_unit:016.list",
                "inherited_unit",
                "SaveOptions.Compressed, SaveOptions.Encrypt, SaveOptions.Incremental, "
                "SaveOptions.Linearized, and SaveOptions.StreamFilter control how the document "
                "is saved.",
            ),
            _symbol("ParseContentStream", "function"),
            _symbol("Document.Save", "method"),
            _symbol("SaveDocxFile", "function"),
            _symbol("ParseHtml", "function"),
            _symbol("ParseMarkdown", "function"),
            _symbol("SaveOptions.Compressed", "property"),
            _symbol("SaveOptions.Encrypt", "property"),
            _symbol("SaveOptions.Incremental", "property"),
            _symbol("SaveOptions.Linearized", "property"),
            _symbol("SaveOptions.StreamFilter", "property"),
        ),
    )


_PDFTS_CANDIDATES = [
    "public_symbol:document.save",
    "public_symbol:parsecontentstream",
    "public_symbol:parsehtml",
    "public_symbol:parsemarkdown",
    "public_symbol:savedocxfile",
]
_PDFTS_CANDIDATES_016 = [
    "public_symbol:saveoptions.compressed",
    "public_symbol:saveoptions.encrypt",
    "public_symbol:saveoptions.incremental",
    "public_symbol:saveoptions.linearized",
    "public_symbol:saveoptions.streamfilter",
]


def test_uncited_omit_candidates_finds_the_pdf_typescript_units_own_unused_evidence() -> None:
    """Direct test of the matching function: a mutation removing or weakening the candidate
    match (e.g. restricting it further, or returning nothing) fails this assertion directly,
    since it pins the exact sorted fact-ID set each unit's own text already spells."""
    facts = _pdf_typescript_omit_facts()
    text_014 = (
        "Parse a document with ParseContentStream, then Document.Save, SaveDocxFile, "
        "ParseHtml, and ParseMarkdown write it back out."
    )
    text_016 = (
        "SaveOptions.Compressed, SaveOptions.Encrypt, SaveOptions.Incremental, "
        "SaveOptions.Linearized, and SaveOptions.StreamFilter control how the document is saved."
    )
    assert uncited_omit_candidates(text_014, facts) == _PDFTS_CANDIDATES
    assert uncited_omit_candidates(text_016, facts) == _PDFTS_CANDIDATES_016


def test_an_uncited_prose_omit_surfaces_the_units_own_textually_overlapping_facts() -> None:
    """The re-ask for an uncited OMIT_UNSUPPORTED on PDF-TypeScript's own 014.list/016.list now
    names the SUPPORTED facts the unit's text already spells, so the model has somewhere
    concrete to look instead of only being told to try again (#1008 repair round). Removing the
    candidate-surfacing call in ``placement_errors`` breaks this test: the sorted fact IDs below
    would no longer appear in the message at all."""
    facts = _pdf_typescript_omit_facts()
    output = {
        "dispositions": [
            _entry("inherited_unit:014.list", "OMIT_UNSUPPORTED", None),
            _entry("inherited_unit:016.list", "OMIT_UNSUPPORTED", None),
        ]
    }
    errors = placement_errors(output, facts)
    assert len(errors) == 2
    assert errors[0].startswith("inherited_unit:014.list: uncited_prose_omit: ")
    assert "already spells these SUPPORTED facts" in errors[0]
    for candidate in _PDFTS_CANDIDATES:
        assert candidate in errors[0]
    assert "SUPERSEDE_REDUNDANT or CORRECT_WITH_EVIDENCE" in errors[0]
    assert "OMIT_UNSUPPORTED with a cited reason if none of them truly apply" in errors[0]
    for candidate in _PDFTS_CANDIDATES_016:
        assert candidate in errors[1]
    # Never auto-assigned: the disposition on both units is still exactly what the model gave,
    # OMIT_UNSUPPORTED - the candidate list is only named in the refusal text, never applied.
    assert output["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"
    assert output["dispositions"][1]["disposition"] == "OMIT_UNSUPPORTED"


def test_an_uncited_prose_omit_with_no_textual_overlap_gets_the_plain_reask() -> None:
    """Mutation control for the no-overlap case: a unit whose text spells no fact's identifier
    gets an empty candidate list and the unchanged, candidate-free re-ask - the new mechanism
    does not invent a candidate where the diagnosis's own matching approach finds none."""
    facts = _prose_omit_facts()
    assert uncited_omit_candidates("Second prose unit.", facts) == []
    output = {"dispositions": [_entry("inherited_unit:005.paragraph", "OMIT_UNSUPPORTED", None)]}
    errors = placement_errors(output, facts)
    assert len(errors) == 1
    assert "already spells these SUPPORTED facts" not in errors[0]
    assert errors[0].endswith(
        'the unit\'s exact text is "Second prose unit.". Cite the supporting fact IDs or place '
        "the unit; do not omit it without a cited reason"
    )


def test_a_cited_prose_omit_passes() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "OMIT_UNSUPPORTED", None, "identity:repository"),
        ]
    }
    assert placement_errors(output, _prose_omit_facts()) == []


def test_an_uncited_heading_or_html_block_omit_is_not_refused_by_this_check() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "OMIT_UNSUPPORTED", None),
            _entry("inherited_unit:006.html_block", "OMIT_UNSUPPORTED", None),
        ]
    }
    assert placement_errors(output, _prose_omit_facts()) == []


def test_a_prose_omit_is_judged_on_the_folded_output_through_reconcile_checks() -> None:
    """The repair path's checks are ``reconcile_checks``; the refusal reaches them unchanged."""
    output = {"dispositions": [_entry("inherited_unit:002.paragraph", "OMIT_UNSUPPORTED", None)]}
    errors = reconcile_checks(output, _prose_omit_facts())
    assert errors and errors[0].startswith("inherited_unit:002.paragraph: uncited_prose_omit: ")


def _reply(content: dict[str, object]) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "qwen3-next",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(content)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    return httpx.Response(200, json=body)


def _s4_output(paragraph: dict[str, object]) -> dict[str, object]:
    """A full batch reply covering every unit of _prose_omit_facts once; the caller supplies the
    disposition of the paragraph under test (002), the rest are fixed and valid."""
    return {
        "dispositions": [
            _entry(
                "inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", None, "identity:repository"
            ),
            {**paragraph, "unit_id": "inherited_unit:002.paragraph", "rationale": "because"},
            _entry(
                "inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start", "example:001"
            ),
            _entry("inherited_unit:004.code_block", "OMIT_UNSUPPORTED", None, "example:002"),
            _entry(
                "inherited_unit:005.paragraph", "VERIFIED_REWRITE", "opening", "identity:repository"
            ),
            _entry("inherited_unit:006.html_block", "OMIT_UNSUPPORTED", None),
        ]
    }


def _run_s4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *replies: httpx.Response
) -> tuple[JobResult, list[dict[str, Any]]]:
    """The production S4 call: this batch's packet and schema, checked by reconcile_checks."""
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return replies[len(seen) - 1]

    mock_gateway(monkeypatch, handler)
    facts = _prose_omit_facts()
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    units = facts.by_kind("inherited_unit")
    result = run_job(
        loaded,
        reconciliation_packet(ENTRY, facts, {}, loaded.manifest, units),
        config=GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789"),
        facts=facts,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext(ENTRY.repository, facts.source_revision),
        checks=functools.partial(reconcile_checks, facts=facts),
        call_schema=reconciliation_schema(loaded, units, facts, {}),
    )
    return result, seen


def test_a_repair_re_asks_the_unit_once_and_accepts_its_cited_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uncited = {
        "disposition": "OMIT_UNSUPPORTED",
        "destination_section": None,
        "fact_ids": [],
        "rationale": "because",
    }
    cited = {
        "disposition": "OMIT_UNSUPPORTED",
        "destination_section": None,
        "fact_ids": ["identity:repository"],
        "rationale": "because",
    }
    result, seen = _run_s4(
        tmp_path,
        monkeypatch,
        _reply(_s4_output(uncited)),
        _reply(_s4_output(cited)),
    )
    assert result.attempts == 2
    re_ask = json.dumps(seen[1], ensure_ascii=False)
    assert "uncited_prose_omit" in re_ask
    assert 'exact text is \\"Prose.\\"' in re_ask


def test_a_second_uncited_prose_omit_fails_the_job_closed_naming_the_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uncited = {
        "disposition": "OMIT_UNSUPPORTED",
        "destination_section": None,
        "fact_ids": [],
        "rationale": "because",
    }
    with pytest.raises(JobError) as caught:
        _run_s4(tmp_path, monkeypatch, _reply(_s4_output(uncited)), _reply(_s4_output(uncited)))
    message = str(caught.value)
    assert "output rejected twice" in message
    assert "inherited_unit:002.paragraph: uncited_prose_omit:" in message


def test_a_sealed_shaped_dispositions_file_still_validates_under_the_static_schema() -> None:
    """Replay of a sealed file is unchanged: the schema is not touched, so a sealed shape still
    passes it, including a heading omitted with no citation (which this check never refuses)."""
    sealed = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "OMIT_UNSUPPORTED", None),
            _entry(
                "inherited_unit:002.paragraph", "VERIFIED_REWRITE", "opening", "identity:repository"
            ),
            _entry(
                "inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start", "example:001"
            ),
            _entry("inherited_unit:004.code_block", "OMIT_UNSUPPORTED", None, "example:002"),
        ]
    }
    validator = Draft202012Validator(
        schema_for(load_manifests(REPO_ROOT / "prompts")["source_reconciliation"], None)
    )
    assert list(validator.iter_errors(sealed)) == []
    assert placement_errors(sealed, _prose_omit_facts()) == []


# G7-W12 follow-up (b): the last-resort recover= for source_reconciliation. Real shape: Aspose.PSD
# FOSS for .NET inherited_unit:018.paragraph, "... is not published to NuGet yet", which the model
# omitted with no citation on both attempts of the 2026-10-10 live run, so the transaction failed
# closed at S4 before BC-05 could classify anything.
_PSD_TEXT = (
    "The package metadata is defined in this repository, but `Aspose.PSD.FOSS` is not "
    "published to NuGet yet."
)


def _psd_facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *_prose_omit_facts().facts,
            _fact("inherited_unit:018.paragraph", "inherited_unit", _PSD_TEXT),
            *extra,
        ),
    )


def _psd_reply(unit_018: dict[str, object]) -> dict[str, object]:
    """A full reply over _psd_facts(): every other unit validly disposed, 018 as supplied."""
    reply = _s4_output(
        {
            "disposition": "VERIFIED_REWRITE",
            "destination_section": "opening",
            "fact_ids": ["identity:repository"],
        }
    )
    reply["dispositions"].append({**unit_018, "unit_id": "inherited_unit:018.paragraph"})  # type: ignore[union-attr]
    return reply


_UNCITED_OMIT = {
    "disposition": "OMIT_UNSUPPORTED",
    "destination_section": None,
    "fact_ids": [],
    "rationale": "The package is not published to NuGet yet.",
}


def test_recover_folds_an_uncited_prose_omit_into_an_explicit_deferral() -> None:
    reply = _psd_reply(_UNCITED_OMIT)
    before = json.dumps(reply)
    recovered = recover_uncited_prose_omits(reply, _psd_facts())
    assert recovered is not None
    assert json.dumps(reply) == before  # the model's own reply is never edited in place
    folded = next(e for e in recovered["dispositions"] if e["unit_id"].endswith("018.paragraph"))
    assert (folded["disposition"], folded["destination_section"], folded["fact_ids"]) == (
        "DEFER_UNRESOLVED",
        None,
        [],
    )
    # the model's own reason survives, after a statement that the omission cited nothing
    assert folded["rationale"].startswith("No fact cited for this omission")
    assert "not published to NuGet yet" in folded["rationale"]
    assert len(folded["rationale"]) <= 160
    others = [e for e in recovered["dispositions"] if e is not folded]
    assert others == [
        e for e in reply["dispositions"] if not e["unit_id"].endswith("018.paragraph")
    ]


def test_recover_truncates_a_long_reason_inside_the_rationale_limit() -> None:
    long_reason = {**_UNCITED_OMIT, "rationale": "x" * 160}
    recovered = recover_uncited_prose_omits(_psd_reply(long_reason), _psd_facts())
    assert recovered is not None
    folded = recovered["dispositions"][-1]
    assert len(folded["rationale"]) == 160 and folded["rationale"].endswith("...")


def test_recover_declines_when_the_units_own_text_spells_a_verified_symbol() -> None:
    """The unit is not unresolved: a verified fact is already in its sentence, so deferring it
    would hide evidence the omission should have cited. It fails closed as it always did."""
    spelled = _psd_facts(_symbol("Aspose.PSD.FOSS", "namespace"))
    assert recover_uncited_prose_omits(_psd_reply(_UNCITED_OMIT), spelled) is None


def test_recover_declines_when_any_uncited_omit_is_unsafe_even_if_another_is_safe() -> None:
    """All or nothing: a partial fix would be accepted only to fail the same checks."""
    facts = _psd_facts(_symbol("Aspose.PSD.FOSS", "namespace"))
    reply = _psd_reply(_UNCITED_OMIT)
    reply["dispositions"][1] = _entry("inherited_unit:002.paragraph", "OMIT_UNSUPPORTED", None)
    assert recover_uncited_prose_omits(reply, facts) is None


def test_recover_leaves_cited_omits_and_non_prose_omits_alone() -> None:
    reply = _psd_reply({**_UNCITED_OMIT, "fact_ids": ["identity:repository"]})
    assert recover_uncited_prose_omits(reply, _psd_facts()) is None  # nothing to fold
    reply = _psd_reply({**_UNCITED_OMIT, "disposition": "DEFER_UNRESOLVED"})
    assert recover_uncited_prose_omits(reply, _psd_facts()) is None


def test_recover_declines_a_unit_the_facts_do_not_hold() -> None:
    reply = _psd_reply(_UNCITED_OMIT)
    reply["dispositions"][-1]["unit_id"] = "inherited_unit:099.paragraph"
    assert recover_uncited_prose_omits(reply, _psd_facts()) is None


def _run_s4_psd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *replies: httpx.Response,
    facts: FactsDocument | None = None,
) -> JobResult:
    """The production S4 call, with the recover= rounds.py passes."""
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return replies[len(seen) - 1]

    mock_gateway(monkeypatch, handler)
    facts = facts or _psd_facts()
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    units = facts.by_kind("inherited_unit")
    return run_job(
        loaded,
        reconciliation_packet(ENTRY, facts, {}, loaded.manifest, units),
        config=GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789"),
        facts=facts,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext(ENTRY.repository, facts.source_revision),
        checks=functools.partial(reconcile_checks, facts=facts),
        call_schema=reconciliation_schema(loaded, units, facts, {}),
        recover=functools.partial(recover_uncited_prose_omits, facts=facts),
    )


def test_two_uncited_omits_are_recovered_once_and_the_deferral_is_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repository_presenter.components.readme.validation.deferrals import review_deferrals

    reply = _reply(_psd_reply(_UNCITED_OMIT))
    result = _run_s4_psd(tmp_path, monkeypatch, reply, reply)
    assert result.attempts == 2  # the model's own re-ask ran first; recover is the last resort
    folded = next(
        e for e in result.output["dispositions"] if e["unit_id"].endswith("018.paragraph")
    )
    assert folded["disposition"] == "DEFER_UNRESOLVED"
    findings = review_deferrals(result.output, _psd_facts())
    assert [(f.unit_id, f.class_id, f.decision) for f in findings] == [
        ("inherited_unit:018.paragraph", "NO_EVIDENCE_EITHER_WAY", "ADVISORY")
    ]


def test_a_recovered_reply_is_judged_by_the_real_checks_and_fails_closed_when_it_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The correction passes through the same schema, binding and checks as any reply: a reply that
    also has a placement violation is not rescued by folding the omit."""
    bad = _psd_reply(_UNCITED_OMIT)
    bad["dispositions"][2] = _entry("inherited_unit:003.code_block", "VERIFIED_PRESERVE", "heading")
    reply = _reply(bad)
    with pytest.raises(JobError) as caught:
        _run_s4_psd(tmp_path, monkeypatch, reply, reply)
    assert "recover's correction was rejected too" in str(caught.value)


def test_a_spelled_symbol_omit_still_fails_the_job_closed_after_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reply = _reply(_psd_reply(_UNCITED_OMIT))
    with pytest.raises(JobError) as caught:
        _run_s4_psd(
            tmp_path,
            monkeypatch,
            reply,
            reply,
            facts=_psd_facts(_symbol("Aspose.PSD.FOSS", "namespace")),
        )
    message = str(caught.value)
    assert "output rejected twice" in message
    assert "inherited_unit:018.paragraph: uncited_prose_omit:" in message
    assert "recover's correction" not in message  # declined, not attempted
