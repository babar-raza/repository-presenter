"""Where a kept inherited unit can go (wave 4, BC-05 v7 content loss, nine repositories).

S4 offered every section of the shell as a destination for a kept unit. Four of them print from
facts and cannot hold a unit (Installation, Dependencies, the identity and badge rows, Navigation,
Third-Party Notices, License), At a Glance holds one diagram, and a section whose condition fails
is not in the document at all. A model that met a Gradle snippet under "Installation" put it in
``installation`` three times running, the placement was refused each time, and the last-resort
correction deferred the unit - content gone from the README, which BC-05 (v7) now blocks.

The cases below are the retained rejected replies of 3D-Java and Note-Python (wave 4, cut 4,
``fixtures/wave4_s4_content_loss.json``; the facts are the runs' own ``facts.json`` trimmed to the
units of the slice): the model's entries are verbatim.
"""

from __future__ import annotations

import copy
import functools
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.components.shell import (
    placeable_section_ids,
    section_ids,
)
from repository_presenter.components.readme.composition.placement import placed_texts, placements
from repository_presenter.components.readme.extractors.platforms import java, python  # noqa: F401
from repository_presenter.components.readme.reconciliation import dispositions as d
from repository_presenter.components.readme.reconciliation.destinations import (
    PLACING_DISPOSITIONS,
    disposition_variants,
    holdable_sections,
    nearest_for_units,
    nearest_holdable,
    root_heading,
    source_heading,
)
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, read_facts
from repository_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    JobResult,
    run_job,
    schema_error_lines,
)
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT, mock_gateway

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads((FIXTURES / "wave4_s4_content_loss.json").read_text(encoding="utf-8"))
LOADED = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
DETERMINISTIC = set(section_ids()) - placeable_section_ids()

JAVA_ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "family": "3d",
        "platform": "java",
        "ecosystem": "java",
        "mode": "dry_run",
        "policy_profile": "3d",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
NOTE_ENTRY = JAVA_ENTRY.model_copy(
    update={
        "repository": "aspose-note-foss/Aspose.Note-FOSS-for-Python",
        "family": "note",
        "platform": "python",
        "ecosystem": "python",
        "policy_profile": "note",
    }
)


def _batch(facts_file: str, unit_ids: list[str]) -> tuple[FactsDocument, list[Fact], FactsDocument]:
    """The slice's facts, its units, and the facts narrowed to exactly those units (a batch)."""
    facts = read_facts(FIXTURES / facts_file)
    units = [fact for fact in facts.by_kind("inherited_unit") if fact.id in set(unit_ids)]
    assert [unit.id for unit in units] == unit_ids
    return facts, units, d.reconciliation_batch_facts(facts, units)


def _java() -> tuple[FactsDocument, list[Fact], FactsDocument]:
    return _batch("wave4_3d_java.facts.json", CASES["3d_java"]["install_units"])


def _note() -> tuple[FactsDocument, list[Fact], FactsDocument]:
    return _batch("wave4_note_python.facts.json", CASES["note_python"]["units"])


def _reply(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"dispositions": copy.deepcopy(entries)}


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


def _validator(facts: FactsDocument, units: list[Fact]) -> Draft202012Validator:
    return Draft202012Validator(d.reconciliation_schema(LOADED, units, facts, {}))


# ---- (a) the decoder's destination enum ---------------------------------------------------------


def test_the_real_second_reply_cannot_be_written_under_the_destination_enum() -> None:
    """3D-Java, the retained re-ask: 014/016/018 are VERIFIED_PRESERVE into ``installation``. A
    decoder honouring the schema cannot emit that; a supersession into it still can (the first
    reply's shape), and so can every reply that holds a unit in a section that can hold it."""
    _, units, facts = _java()
    validator = _validator(facts, units)
    second = _reply(CASES["3d_java"]["install_reply_2"])
    assert not validator.is_valid(second)
    refused = [
        line for error in validator.iter_errors(second) for line in schema_error_lines(error)
    ]
    assert any("014.code_block" in line or "dispositions[3]" in line for line in refused), refused
    first = _reply(CASES["3d_java"]["install_reply_1"])
    assert validator.is_valid(first)  # supersede into installation, omit with a null destination


def test_a_refused_destination_is_named_in_the_re_ask_not_reported_as_a_union_failure() -> None:
    _, units, facts = _java()
    lines = [
        line
        for error in _validator(facts, units).iter_errors(
            _reply(CASES["3d_java"]["install_reply_2"])
        )
        for line in schema_error_lines(error)
    ]
    assert lines and all("not valid under any of the given schemas" not in line for line in lines)
    assert any("'installation' is not one of [" in line for line in lines)


def test_the_placing_enum_is_exactly_the_sections_that_can_hold_a_unit_here() -> None:
    _, _, facts = _java()
    holdable = set(holdable_sections(facts))
    assert holdable.isdisjoint(DETERMINISTIC)
    assert "at_a_glance" not in holdable  # one diagram and nothing else
    assert {"scope_limitations", "api_reference", "development_testing"} <= holdable
    placing, other = d.reconciliation_schema(LOADED, _java()[1], facts, {})["properties"][
        "dispositions"
    ]["items"]["anyOf"]
    assert list(placing["properties"]["destination_section"]["enum"]) == [
        section for section in section_ids() if section in holdable
    ]
    assert placing["properties"]["disposition"]["enum"] == list(PLACING_DISPOSITIONS)
    # Every other disposition keeps the open destination: a supersession names the renderer-owned
    # section that prints the unit's substance, and an omission or deferral names none.
    options = other["properties"]["destination_section"]["oneOf"]
    assert {"type": "null"} in options
    assert [o["enum"] for o in options if "enum" in o] == [list(section_ids())]
    assert "SUPERSEDE_REDUNDANT" in other["properties"]["disposition"]["enum"]


def test_a_section_whose_condition_fails_is_not_offered_to_a_placing_disposition() -> None:
    """Development and Testing needs a build or test asset; without one a unit placed there is
    deferred by normalize (the section is not in the document), so it must not be on offer."""
    _, units, facts = _java()
    bare = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(fact for fact in facts.facts if fact.kind != "build_test_asset"),
    )
    assert "development_testing" in holdable_sections(facts)
    assert "development_testing" not in holdable_sections(bare)
    placing = d.reconciliation_schema(LOADED, units, bare, {})["properties"]["dispositions"][
        "items"
    ]["anyOf"][0]
    assert "development_testing" not in placing["properties"]["destination_section"]["enum"]


def test_no_holdable_section_leaves_only_the_shape_that_cannot_place() -> None:
    """Negative control for the schema: with nothing holdable the placing shape is dropped, so no
    placement can be written at all (an empty enum is not a shape a decoder takes)."""
    base = LOADED.manifest.output.schema_["properties"]["dispositions"]["items"]
    assert len(disposition_variants(base, ("scope_limitations",))) == 2
    variants = disposition_variants(base, ())
    assert len(variants) == 1
    assert "VERIFIED_PRESERVE" not in variants[0]["properties"]["disposition"]["enum"]


def test_the_packet_says_what_the_decoder_enforces() -> None:
    """``placeable`` in the packet is the schema's own set; a section the shell lets the LLM write
    but that cannot hold a kept unit here says why, so the two never disagree."""
    _, units, facts = _java()
    packet = d.reconciliation_packet(JAVA_ENTRY, facts, {}, LOADED.manifest, units)
    sections = {record["id"]: record for record in packet["sections"]}
    holdable = set(holdable_sections(facts))
    assert {section for section, record in sections.items() if record["placeable"]} == holdable
    assert sections["installation"]["placeable"] is False
    assert "unavailable" not in sections["installation"]  # it renders from facts: owner D
    assert "diagram" in sections["at_a_glance"]["unavailable"]
    bare = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(fact for fact in facts.facts if fact.kind != "build_test_asset"),
    )
    rebuilt = d.reconciliation_packet(JAVA_ENTRY, bare, {}, LOADED.manifest, units)
    testing = next(r for r in rebuilt["sections"] if r["id"] == "development_testing")
    assert testing["placeable"] is False and "condition" in testing["unavailable"]


def test_the_refusal_names_this_repositorys_sections_and_the_nearest_one() -> None:
    _, _, facts = _java()
    errors = d.placement_errors(_reply(CASES["3d_java"]["install_reply_2"]), facts)
    placed = [e for e in errors if "needs a destination the shell can hold" in e]
    assert placed and all(e.endswith("); got 'installation'") for e in placed)
    assert all("at_a_glance" not in e.split("(")[1] for e in placed)
    typed = [
        e for e in errors if e.startswith("inherited_unit:016.code_block: uncovered_supersession")
    ]
    assert len(typed) == 1
    assert "The nearest section that can hold it is development_testing." in typed[0]
    assert "at_a_glance" not in typed[0].split("can hold it (")[1].split(")")[0]


# ---- the nearest holdable section ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("unit", "heading", "expected"),
    [
        # install material the Installation row does not print: with the commands a maintainer runs
        (
            "inherited_unit:016.code_block",
            "Aspose.3D FOSS for Java > Installation",
            "development_testing",
        ),
        (
            "inherited_unit:014.code_block",
            "Aspose.Note FOSS for Python > Installation",
            "development_testing",
        ),
        # ... or, when it is prose, with the requirements a reader must meet
        (
            "inherited_unit:015.paragraph",
            "Aspose.Note FOSS for Python > Installation",
            "scope_limitations",
        ),
        (
            "inherited_unit:020.list",
            "Product > Dependencies > Optional Dependencies",
            "scope_limitations",
        ),
        ("inherited_unit:040.code_block", "Product > Examples", "additional_examples"),
        ("inherited_unit:050.paragraph", "Product > Known Limitations", "scope_limitations"),
        ("inherited_unit:060.list", "Product > Features", "key_capabilities"),
        ("inherited_unit:070.paragraph", "Product > Links", "documentation_resources"),
        ("inherited_unit:080.table", "Product > API Reference", "api_reference"),
        # under no known topic: by kind
        ("inherited_unit:090.code_block", "Product > Zebra", "development_testing"),
        ("inherited_unit:091.paragraph", "Product > Zebra", "scope_limitations"),
        ("inherited_unit:092.paragraph", None, "scope_limitations"),
    ],
)
def test_the_nearest_holdable_section_is_read_from_the_source_heading_and_kind(
    unit: str, heading: str | None, expected: str
) -> None:
    everything = holdable_sections(_java()[2])
    assert nearest_holdable(unit, heading, everything) == expected


def test_the_nearest_section_is_one_that_is_holdable_and_prints_the_kind() -> None:
    # Without Development and Testing an install code block falls to the next home.
    without = tuple(s for s in holdable_sections(_java()[2]) if s != "development_testing")
    assert (
        nearest_holdable("inherited_unit:016.code_block", "P > Installation", without)
        == "quick_start"
    )
    # A section that cannot print the kind is skipped (a code block is not a limitation) ...
    assert (
        nearest_holdable("inherited_unit:016.code_block", "P > Limits", ("scope_limitations",))
        is None
    )
    # ... and a unit the shell owns (a heading) has no home at all.
    assert (
        nearest_holdable("inherited_unit:011.heading", "P > Installation", ("scope_limitations",))
        is None
    )
    assert nearest_holdable("inherited_unit:016.code_block", "P > Installation", ()) is None


# ---- (b) the last-resort correction keeps content -----------------------------------------------


def test_recover_keeps_the_gradle_snippet_where_it_can_be_held_instead_of_deferring_it() -> None:
    """3D-Java, the retained re-ask reply as it stood when recover= ran. Before: 014/016/018 were
    deferred ("Not provably carried by the section named; held for the owner") and BC-05 v7 found
    the Kotlin DSL line absent from the README. After: the Maven and Groovy blocks are what the
    Installation row prints (so they stay a supersession by it) and the Kotlin one, which no
    deterministic section prints, stays in the document - with the label that introduces it."""
    _, _, facts = _java()
    raw = _reply(CASES["3d_java"]["install_reply_2"])
    recovered = d.recover_uncited_prose_omits(raw, facts)
    assert recovered is not None
    entries = _by_unit(recovered)
    kotlin = entries["inherited_unit:016.code_block"]
    label = entries["inherited_unit:015.paragraph"]
    assert (kotlin["disposition"], kotlin["destination_section"]) == (
        "VERIFIED_PRESERVE",
        "development_testing",
    )
    assert (label["disposition"], label["destination_section"]) == (
        "VERIFIED_MOVE",
        "development_testing",
    )
    assert kotlin["rationale"].startswith("Kept in development_testing: ")
    assert "DEFER_UNRESOLVED" not in {entry["disposition"] for entry in entries.values()}
    # Judged by the same checks as any reply: nothing is accepted on recover's say-so.
    assert d.reconcile_checks(copy.deepcopy(recovered), facts) == []


def test_recover_keeps_the_pip_extra_with_its_label_and_not_in_dependencies() -> None:
    """Note-Python, the retained re-ask reply: 013/014/015 are VERIFIED_MOVE into ``dependencies``
    (the section the extra is read under). The ``[pdf]`` install line is content no deterministic
    section prints; it stays, with the sentence that introduces it, and the Python floor
    sentence is kept as a requirement."""
    _, _, facts = _note()
    recovered = d.recover_uncited_prose_omits(_reply(CASES["note_python"]["reply_2"]), facts)
    assert recovered is not None
    entries = _by_unit(recovered)
    where = {
        unit: (entry["disposition"], entry["destination_section"])
        for unit, entry in entries.items()
        if unit.split(":")[1][:3] in {"013", "014", "015"}
    }
    assert where == {
        "inherited_unit:013.paragraph": ("VERIFIED_MOVE", "development_testing"),
        "inherited_unit:014.code_block": ("VERIFIED_MOVE", "development_testing"),
        "inherited_unit:015.paragraph": ("VERIFIED_MOVE", "scope_limitations"),
    }
    assert d.reconcile_checks(copy.deepcopy(recovered), facts) == []


def test_a_recovered_unit_is_placed_once_and_never_in_a_renderer_owned_section() -> None:
    """Negative control: the unit is neither dropped, nor doubled, nor left in the section that
    cannot hold it - one disposition per unit, and render places it exactly once."""
    _, _, facts = _java()
    recovered = d.recover_uncited_prose_omits(_reply(CASES["3d_java"]["install_reply_2"]), facts)
    assert recovered is not None
    units = [entry["unit_id"] for entry in recovered["dispositions"]]
    assert len(units) == len(set(units)) == 9
    kept = [e for e in recovered["dispositions"] if e["rationale"].startswith("Kept in ")]
    assert kept and all(e["destination_section"] not in DETERMINISTIC for e in kept)
    plan = {"sections": [{"section_id": "development_testing", "include": True}]}
    decisions = placements(plan, d.merge_dispositions([copy.deepcopy(recovered)]), facts, "java")
    kotlin = [p for p in decisions if p.unit_id == "inherited_unit:016.code_block"]
    assert [(p.destination, p.outcome) for p in kotlin] == [("development_testing", "placed")]
    texts = placed_texts(decisions)["development_testing"]
    assert sum('implementation("org.aspose:aspose-3d-foss:26.5.0")' in t for t in texts) == 1


def test_a_unit_no_section_can_hold_is_deferred_with_the_typed_rationale() -> None:
    """Negative control: with only the limitations section holdable, the snippet (a code block,
    which a limitation does not print) has no home and is withheld exactly as before - typed, so
    BC-05 reads the cause - while the prose beside it is kept."""
    _, _, facts = _java()
    recovered = d.recover_uncited_prose_omits(
        _reply(CASES["3d_java"]["install_reply_2"]), facts, holdable=("scope_limitations",)
    )
    assert recovered is not None
    entries = _by_unit(recovered)
    snippet = entries["inherited_unit:016.code_block"]
    assert (snippet["disposition"], snippet["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert snippet["rationale"].startswith(d.RECOVERED_COVERAGE_RATIONALE)
    assert d.reconcile_checks(copy.deepcopy(recovered), facts) == []


def test_a_repository_with_no_build_asset_and_no_example_has_no_home_for_a_snippet() -> None:
    """Negative control on real facts: Development and Testing needs a build asset and the example
    rows a verified example. Without them nothing that prints code is on offer, so the Kotlin line
    is withheld as before (typed, listed for the owner) while its label, a sentence, is kept as a
    requirement - and nothing is put in the API Reference to make a home for it."""
    _, _, facts = _java()
    bare = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(f for f in facts.facts if f.kind not in {"build_test_asset", "example"}),
    )
    assert {"development_testing", "quick_start", "additional_examples"}.isdisjoint(
        holdable_sections(bare)
    )
    recovered = d.recover_uncited_prose_omits(_reply(CASES["3d_java"]["install_reply_2"]), bare)
    assert recovered is not None
    entries = _by_unit(recovered)
    snippet = entries["inherited_unit:016.code_block"]
    assert (snippet["disposition"], snippet["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert snippet["rationale"].startswith(d.RECOVERED_COVERAGE_RATIONALE)
    assert "api_reference" not in {e["destination_section"] for e in entries.values()}
    assert d.reconcile_checks(copy.deepcopy(recovered), bare) == []


def test_a_claim_about_support_is_still_withheld_not_published() -> None:
    """Only a unit its destination cannot *print* is kept. An omission the facts do not back, or
    an example never run, is not turned into a placement: that would publish what the reply
    called unsupported."""
    _, _, facts = _java()
    first = _reply(CASES["3d_java"]["install_reply_1"])
    recovered = d.recover_uncited_prose_omits(first, facts)
    assert recovered is not None
    entries = _by_unit(recovered)
    # 019 was an uncited omission of a paragraph: still the typed deferral, never a placement.
    assert entries["inherited_unit:019.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    # 014 and 018 are what the Installation row prints: they stay superseded, not placed twice.
    for unit in ("inherited_unit:014.code_block", "inherited_unit:018.code_block"):
        assert (entries[unit]["disposition"], entries[unit]["destination_section"]) == (
            "SUPERSEDE_REDUNDANT",
            "installation",
        )


def test_the_installation_row_is_known_to_print_the_alternatives_it_prints() -> None:
    """The Maven POM entry and the Gradle line are rendered under a registry install
    (``renderer._installation``); the coverage test now knows it, and the Kotlin DSL line, which is
    not rendered, is still a gap."""
    _, _, facts = _java()
    first = _reply(CASES["3d_java"]["install_reply_1"])
    gaps = {gap.unit_id: gap.reason for gap in d.coverage_findings(first, facts)}
    assert gaps == {"inherited_unit:016.code_block": d.UNRENDERED_COMMAND}
    # With the install a source build, the row prints no alternative: the Maven block is a gap.
    source = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            Fact(
                f.id,
                f.kind,
                f.value,
                f.evidence,
                f.polarity,
                f.confidence,
                {"install_kind": "source"},
            )
            if f.kind == "install_command"
            else f
            for f in facts.facts
        ),
    )
    assert "inherited_unit:014.code_block" in {
        gap.unit_id for gap in d.coverage_findings(first, source)
    }


# ---- (c) the narrowed ask -----------------------------------------------------------------------


def _completion(content: dict[str, Any]) -> httpx.Response:
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


def _run_java(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *replies: dict[str, Any],
    seen: list[dict[str, Any]] | None = None,
) -> JobResult:
    """The production S4 call for the 3D-Java install slice, wired as rounds.py wires it."""
    seen = [] if seen is None else seen

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return _completion(replies[len(seen) - 1])

    mock_gateway(monkeypatch, handler)
    _, units, facts = _java()
    return run_job(
        LOADED,
        d.reconciliation_packet(JAVA_ENTRY, facts, {}, LOADED.manifest, units),
        config=GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789"),
        facts=facts,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext(JAVA_ENTRY.repository, facts.source_revision),
        checks=functools.partial(d.reconcile_checks, facts=facts),
        call_schema=d.reconciliation_schema(LOADED, units, facts, {}),
        recover=functools.partial(
            d.recover_uncited_prose_omits,
            facts=facts,
            citable=frozenset(d.citable_fact_ids(facts, LOADED.manifest, units, {})),
        ),
        narrow=d.reconciliation_narrowing(JAVA_ENTRY, facts, {}, LOADED, units),
    )


# The units the first reply left refused: four paragraphs omitted with no cited reason and the
# Kotlin DSL snippet, which the Installation row does not print. (The Maven and Groovy blocks are
# printed by it, so superseding them is right.)
REFUSED = [
    "inherited_unit:013.paragraph",
    "inherited_unit:015.paragraph",
    "inherited_unit:016.code_block",
    "inherited_unit:017.paragraph",
    "inherited_unit:019.paragraph",
]


def _corrected_for_the_narrowed_ask() -> dict[str, Any]:
    """What a model asked again for the units still refused, shown where each can be kept, would
    answer: the snippet and its label kept with the commands, the closing sentence a requirement."""
    return {
        "dispositions": [
            {
                "unit_id": unit,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": (
                    "scope_limitations" if unit.endswith("019.paragraph") else "development_testing"
                ),
                "fact_ids": ["install_command:maven"] if unit.endswith("code_block") else [],
                "rationale": "Kept where a reader will find it.",
            }
            for unit in REFUSED
        ]
    }


def test_the_refused_units_get_one_narrowed_ask_with_their_reasons_and_exact_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two replies that both leave units refused (a byte-identical second reply is what wave 4
    recorded in 6 of 14 failures) used to end in the deterministic correction. Now the units are
    asked once more, alone: the packet carries each unit's earlier answer, why it was refused and
    the nearest section that can hold it, and the schema admits a placing disposition only into a
    section that can."""
    seen: list[dict[str, Any]] = []
    first = _reply(CASES["3d_java"]["install_reply_1"])
    third = _corrected_for_the_narrowed_ask()
    result = _run_java(tmp_path, monkeypatch, first, first, third, seen=seen)
    assert result.attempts == result.provider_calls == 3
    asked = seen[2]
    assert [m["role"] for m in asked["messages"]] == ["system", "user"]
    user = asked["messages"][1]["content"]
    assert "inherited_unit:016.code_block" in user and "inherited_unit:011.heading" not in user
    assert "refused_because" in user and "earlier_answer" in user
    assert '"nearest_section_that_can_hold_it": "development_testing"' in user
    schema = asked["response_format"]["json_schema"]["schema"]["properties"]["dispositions"]
    assert schema["maxItems"] == len(REFUSED) == 5
    placing, _other = schema["items"]["anyOf"]
    assert placing["properties"]["unit_id"]["enum"] == REFUSED
    assert "installation" not in placing["properties"]["destination_section"]["enum"]
    # the accepted reply keeps the answers the earlier replies settled, untouched
    entries = _by_unit(result.output)
    assert entries["inherited_unit:012.paragraph"]["destination_section"] == "installation"
    assert entries["inherited_unit:016.code_block"]["destination_section"] == "development_testing"
    assert "DEFER_UNRESOLVED" not in {e["disposition"] for e in entries.values()}
    # the third request is a re-ask of the logical call: same logical id, attempt 3
    records = [
        json.loads(line)
        for line in (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    calls = [
        r for r in records if r["disposition"] == "provider_call" and r["outcome"] == "success"
    ]
    assert [r["attempt"] for r in calls] == [1, 2, 3]
    assert calls[2]["derived_via_reask"] is True


def test_a_narrowed_ask_that_repeats_the_refused_answer_ends_in_a_kept_unit_not_a_deferral(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for the narrowed ask: the model answers the refused units the same way a
    third time. Nothing is accepted on its word - the merged reply is judged by the full checks -
    and the last resort (recover) keeps the one unit nothing prints, where it can be held."""
    seen: list[dict[str, Any]] = []
    first = _reply(CASES["3d_java"]["install_reply_1"])
    again = {
        "dispositions": [e for e in first["dispositions"] if e["unit_id"] >= "inherited_unit:013"]
    }
    result = _run_java(tmp_path, monkeypatch, first, first, again, seen=seen)
    assert len(seen) == 3
    kotlin = _by_unit(result.output)["inherited_unit:016.code_block"]
    assert (kotlin["disposition"], kotlin["destination_section"]) == (
        "VERIFIED_PRESERVE",
        "development_testing",
    )
    repairs = sorted((tmp_path / "calls").glob("*.repaired-*.json"))
    assert repairs, "what recover changed is recorded beside the call"
    recorded = json.loads(repairs[0].read_text(encoding="utf-8"))
    assert recorded["source"] == "recover"
    assert any(change["path"].endswith(".destination_section") for change in recorded["changes"])


def test_pending_units_are_the_silent_and_the_refused_in_batch_order() -> None:
    _, units, facts = _java()
    narrowing = d.reconciliation_narrowing(JAVA_ENTRY, facts, {}, LOADED, units)
    first = _reply(CASES["3d_java"]["install_reply_1"])
    rejection = [
        "inherited_unit:018.code_block: uncovered_supersession: ...",
        "inherited_unit:014.code_block: uncovered_supersession: ...",
        "$.dispositions[3].destination_section: 'installation' is not one of [...]",
    ]
    assert narrowing.pending(json.dumps(first), rejection) == [
        "inherited_unit:014.code_block",
        "inherited_unit:018.code_block",
    ]
    short = {"dispositions": first["dispositions"][:7]}  # 018 and 019 never answered
    assert narrowing.pending(json.dumps(short), rejection[:1]) == [
        "inherited_unit:018.code_block",
        "inherited_unit:019.paragraph",
    ]
    # a rejection that names no unit (a schema error) and no silence asks for nothing
    assert narrowing.pending(json.dumps(first), rejection[2:]) == []
    assert narrowing.pending("not json", rejection) == []


def test_the_merge_replaces_only_the_units_asked_for() -> None:
    _, units, facts = _java()
    narrowing = d.reconciliation_narrowing(JAVA_ENTRY, facts, {}, LOADED, units)
    base = _reply(CASES["3d_java"]["install_reply_1"])
    narrowed = {
        "dispositions": [
            {
                **base["dispositions"][5],
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "development_testing",
            },
            {**base["dispositions"][0], "disposition": "OMIT_UNSUPPORTED"},  # not asked for
        ]
    }
    merged = json.loads(
        narrowing.merge(json.dumps(base), json.dumps(narrowed), ["inherited_unit:016.code_block"])
    )
    assert [e["unit_id"] for e in merged["dispositions"]] == [
        e["unit_id"] for e in base["dispositions"]
    ]  # document order holds
    changed = [
        e["unit_id"]
        for e, was in zip(merged["dispositions"], base["dispositions"], strict=True)
        if e != was
    ]
    assert changed == ["inherited_unit:016.code_block"]
    # a reply that is not an object leaves the earlier answers as they were
    unchanged = narrowing.merge(json.dumps(base), "[]", ["inherited_unit:016.code_block"])
    assert json.loads(unchanged) == base


# ---- units that have no home ----------------------------------------------------------------


def _unit(ordinal: int, kind: str, section: str | None) -> Fact:
    return Fact(
        f"inherited_unit:{ordinal:03}.{kind}",
        "inherited_unit",
        "Text.",
        (Evidence("README.md", None),),
        attributes={"section": section} if section else None,
    )


def test_the_title_is_read_from_the_units_heading_paths_not_taken_for_a_topic() -> None:
    """``Aspose.Note FOSS`` names a product, not a note: the first part of every unit's path is the
    README's title and is never read as a topic."""
    units = [
        _unit(2, "paragraph", "Aspose.Note FOSS for Python"),
        _unit(3, "paragraph", "Aspose.Note FOSS for Python > Installation"),
        _unit(4, "code_block", "Aspose.Note FOSS for Python > Installation"),
    ]
    root = root_heading(units)
    assert root == "aspose note foss for python"
    holdable = ("scope_limitations", "development_testing")
    # directly under the title: the product introduction, which the opening is written from
    assert nearest_holdable(units[0].id, source_heading(units[0]), holdable, root) is None
    assert nearest_holdable(units[2].id, source_heading(units[2]), holdable, root) == (
        "development_testing"
    )
    # a README with no title has no root: its first part is a section, read as one
    assert (
        root_heading([_unit(2, "paragraph", "Installation"), _unit(3, "paragraph", "Usage")])
        is None
    )
    assert nearest_holdable("inherited_unit:003.paragraph", "Installation", holdable) == (
        "scope_limitations"
    )


def test_a_subset_of_one_sections_units_does_not_make_that_section_the_title() -> None:
    """A README with no title: its sections are first parts. A patch asking about the units of one
    of them would read that section as the title (every path starts with it) and call its units
    the introduction; the title is read from the whole batch they came from."""
    batch = [
        _unit(2, "paragraph", "Installation"),
        _unit(3, "code_block", "Usage"),
        _unit(4, "code_block", "Usage"),
        _unit(5, "paragraph", "Limits"),
    ]
    holdable = ("scope_limitations", "additional_examples", "development_testing")
    alone = nearest_for_units(batch[1:3], holdable)
    assert alone[batch[1].id] is None  # misread: "usage" taken for the title
    with_context = nearest_for_units(batch[1:3], holdable, batch)
    assert with_context[batch[1].id] == "additional_examples"
    assert root_heading(batch) is None


@pytest.mark.parametrize(
    "heading", ["Product > License", "Product > Third-Party Notices", "Product > Navigation"]
)
def test_what_the_shell_prints_itself_has_no_home_elsewhere(heading: str) -> None:
    """The licence statement, the notices link and the Navigation list are the renderer's: a unit
    under them is superseded or withheld, never carried into another section."""
    holdable = ("scope_limitations", "development_testing", "key_capabilities")
    assert nearest_holdable("inherited_unit:040.paragraph", heading, holdable, "product") is None
    assert nearest_holdable("inherited_unit:041.code_block", heading, holdable, "product") is None
