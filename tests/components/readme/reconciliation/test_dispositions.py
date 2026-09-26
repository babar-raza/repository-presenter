"""Reconciliation: a bounded packet in, placement rules checked before use, a stable artifact."""

from __future__ import annotations

import json
from pathlib import Path

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
    rendering_fact_ids,
    summarize,
    write_dispositions,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.binding import binding_errors
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
    base = reconciliation_batches(_inherited_units_facts(200))
    tenx = reconciliation_batches(_inherited_units_facts(2000))
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
    batches = reconciliation_batches(facts)
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
    batches = reconciliation_batches(facts)
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
    batches = reconciliation_batches(facts)
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
    _, first_batch_units = reconciliation_batches(facts)[0]
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
