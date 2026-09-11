"""Reconciliation: a bounded packet in, placement rules checked before use, a stable artifact."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.reconciliation.dispositions import (
    contradicted_code_units,
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


def test_the_artifact_is_deterministic_json(tmp_path: Path) -> None:
    output = {"dispositions": [_entry("inherited_unit:001.heading", "NON_CONTENT", None)]}
    path = tmp_path / "t" / "dispositions.json"
    digest = write_dispositions(output, path)
    raw = path.read_bytes()
    assert raw.startswith(b'{\n  "dispositions": [\n    {\n      "destination_section": null,')
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert json.loads(raw) == output
    assert write_dispositions(output, path) == digest
