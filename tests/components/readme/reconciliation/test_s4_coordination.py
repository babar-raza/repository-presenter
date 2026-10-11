"""The S4 coordination gaps of wave 6, replayed from the archived dispositions (cut 8fbf2166).

Every case below is a slice of a wave-6 transaction: the inherited units' own text and the
dispositions ``dispositions.json`` held after ``coordinate_neighbor_promises``, verbatim
(``fixtures/wave6_s4_coordination.json``; the facts are the run's own ``facts.json`` trimmed to the
slice, ``fixtures/wave6_<case>.facts.json``). The first test of each group proves the archived
state really fails the gate that blocked the row; the rest prove the fix and its negative
controls.

* lead-in and payload (BC-05 ``LEADIN_OF_WITHHELD_CONTENT``: JMAP-.NET, Imaging-.NET,
  Font-Python; BC-07: PSD-.NET) - ``coordinate_neighbor_promises`` keeps one fate for the pair;
* forward pointers (BC-07 v11: Words-.NET, Slides-Java, PDF-Go) - refused at S4 by
  ``placement_errors`` and folded to a rewrite on the last attempt;
* the renderer-owned banner row (BC-05 UNCLASSIFIED: PDF-Go);
* the S4 mirrors of BC-08 (JMAP-TypeScript), BC-06 (3D-Java) and BC-03 (Slides-C++).
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.reconciliation import dispositions as d
from repository_presenter.components.readme.validation.deferrals import review_deferrals
from repository_presenter.core.facts import FactsDocument, read_facts

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads((FIXTURES / "wave6_s4_coordination.json").read_text(encoding="utf-8"))
# A finished README that states none of the withheld blocks: BC-05 holds a deferral to what the
# README carries, so this is the worst case the archived rows were judged against.
BARE_README = "# Product\n\nAn opening.\n"


def _case(name: str) -> tuple[FactsDocument, dict[str, Any]]:
    facts = read_facts(FIXTURES / f"wave6_{name}.facts.json")
    return facts, {"dispositions": copy.deepcopy(CASES[name]["dispositions"])}


def _by_unit(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in document["dispositions"]}


def _blocks(document: dict[str, Any], facts: FactsDocument) -> list[tuple[str, str]]:
    return [
        (finding.unit_id, finding.class_id)
        for finding in review_deferrals(document, facts, None, BARE_README)
        if finding.decision == "BLOCK"
    ]


# ---- lead-in beside a withheld block (BC-05 v7) -------------------------------------------

OMITTED_PAIRS = [
    ("jmap_net", "inherited_unit:014.paragraph", "inherited_unit:015.code_block"),
    ("imaging_net", "inherited_unit:017.paragraph", "inherited_unit:018.code_block"),
    ("font_python", "inherited_unit:055.paragraph", "inherited_unit:056.code_block"),
]


@pytest.mark.parametrize(("case", "lead", "block"), OMITTED_PAIRS)
def test_the_archived_pair_is_the_contradiction_bc05_blocks(
    case: str, lead: str, block: str
) -> None:
    """RED precondition: the model deferred the lead-in beside an OMIT_UNSUPPORTED block, the
    coordinator left it, and BC-05 v7 names exactly that pair LEADIN_OF_WITHHELD_CONTENT."""
    facts, document = _case(case)
    entries = _by_unit(document)
    assert entries[lead]["disposition"] == "DEFER_UNRESOLVED"
    assert entries[block]["disposition"] == "OMIT_UNSUPPORTED"
    assert (lead, "LEADIN_OF_WITHHELD_CONTENT") in _blocks(document, facts)


@pytest.mark.parametrize(("case", "lead", "block"), OMITTED_PAIRS)
def test_a_lead_in_the_model_deferred_beside_an_omitted_block_is_omitted_with_it(
    case: str, lead: str, block: str
) -> None:
    facts, document = _case(case)
    d.coordinate_neighbor_promises(document, facts)
    entries = _by_unit(document)
    assert entries[block]["disposition"] == "OMIT_UNSUPPORTED"  # the block is untouched
    folded = entries[lead]
    assert (folded["disposition"], folded["destination_section"]) == ("OMIT_UNSUPPORTED", None)
    # an omission names what shows the claim unsupported (placement_errors' own rule): the
    # block's citations, or the block itself when it cited none
    assert folded["fact_ids"] and set(folded["fact_ids"]) <= {
        *entries[block]["fact_ids"],
        block,
    }
    assert folded["rationale"].isascii()
    assert _blocks(document, facts) == []


def test_the_model_s_own_cjk_rationale_does_not_survive_the_fold() -> None:
    """Font-Python 055: the model's rationale carried a non-Latin word ("allowing the后续例")."""
    facts, document = _case("font_python")
    assert not _by_unit(document)["inherited_unit:055.paragraph"]["rationale"].isascii()
    d.coordinate_neighbor_promises(document, facts)
    assert _by_unit(document)["inherited_unit:055.paragraph"]["rationale"].isascii()


def test_a_placed_lead_in_beside_an_omitted_block_is_omitted_not_deferred() -> None:
    """The coordinator used to defer it, which is the shape BC-05 blocks: an omitted block
    cannot be kept, so the only coherent outcome for its lead-in is the omission."""
    facts, document = _case("jmap_net")
    entries = _by_unit(document)
    entries["inherited_unit:014.paragraph"].update(
        disposition="VERIFIED_PRESERVE", destination_section="quick_start"
    )
    d.coordinate_neighbor_promises(document, facts)
    assert _by_unit(document)["inherited_unit:014.paragraph"]["disposition"] == "OMIT_UNSUPPORTED"
    assert _blocks(document, facts) == []


def test_a_lead_in_beside_a_deferred_block_is_deferred_with_it() -> None:
    """A deferred block is held for the owner, so its lead-in is held with it (unchanged)."""
    facts, document = _case("jmap_net")
    entries = _by_unit(document)
    entries["inherited_unit:015.code_block"].update(disposition="DEFER_UNRESOLVED")
    entries["inherited_unit:014.paragraph"].update(
        disposition="VERIFIED_PRESERVE", destination_section="quick_start"
    )
    d.coordinate_neighbor_promises(document, facts)
    assert _by_unit(document)["inherited_unit:014.paragraph"]["disposition"] == "DEFER_UNRESOLVED"


def test_a_lead_in_whose_block_is_untouched_stays_where_it_is() -> None:
    """Negative control: nothing here is withheld, so nothing is folded."""
    facts, document = _case("jmap_net")
    entries = _by_unit(document)
    entries["inherited_unit:015.code_block"].update(
        disposition="VERIFIED_PRESERVE", destination_section="quick_start"
    )
    entries["inherited_unit:014.paragraph"].update(
        disposition="VERIFIED_PRESERVE", destination_section="quick_start"
    )
    before = copy.deepcopy(document)
    d.coordinate_neighbor_promises(document, facts)
    assert document == before


def test_a_colonless_unit_beside_an_omitted_block_is_not_a_lead_in() -> None:
    facts, document = _case("jmap_net")
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            dataclasses.replace(fact, value="Or add it directly to a project file.")
            if fact.id == "inherited_unit:014.paragraph"
            else fact
            for fact in facts.facts
        ),
    )
    before = copy.deepcopy(document)
    d.coordinate_neighbor_promises(document, facts)
    assert document == before


def test_the_omission_fold_is_idempotent() -> None:
    facts, document = _case("imaging_net")
    d.coordinate_neighbor_promises(document, facts)
    once = json.dumps(document, sort_keys=True)
    d.coordinate_neighbor_promises(document, facts)
    assert json.dumps(document, sort_keys=True) == once


# ---- lead-in and payload placed in different sections (BC-07 v11, PSD-.NET) ---------------

SPLIT_PAIRS = [
    ("psd_net", "inherited_unit:012.paragraph", "inherited_unit:013.code_block"),
    ("imaging_net", "inherited_unit:015.paragraph", "inherited_unit:016.code_block"),
]


@pytest.mark.parametrize(("case", "lead", "block"), SPLIT_PAIRS)
def test_a_lead_in_follows_its_placed_payload_into_the_payload_s_section(
    case: str, lead: str, block: str
) -> None:
    facts, document = _case(case)
    entries = _by_unit(document)
    # RED precondition: the archived pair is parted (quick_start vs development_testing)
    assert entries[lead]["destination_section"] != entries[block]["destination_section"]
    kept = entries[lead]["disposition"]
    d.coordinate_neighbor_promises(document, facts)
    entries = _by_unit(document)
    assert entries[lead]["destination_section"] == entries[block]["destination_section"]
    assert entries[lead]["disposition"] == kept  # still a placement of the same kind
    assert entries[block]["destination_section"] == "development_testing"  # the block does not move


def test_a_split_pair_whose_lead_in_is_superseded_is_left_alone() -> None:
    """Negative control: a lead-in something else already covers is not dragged to the block."""
    facts, document = _case("psd_net")
    entries = _by_unit(document)
    entries["inherited_unit:012.paragraph"].update(
        disposition="SUPERSEDE_REDUNDANT", destination_section="installation"
    )
    before = copy.deepcopy(entries["inherited_unit:012.paragraph"])
    d.coordinate_neighbor_promises(document, facts)
    assert _by_unit(document)["inherited_unit:012.paragraph"] == before


# ---- a lead-in the model withheld beside a block that is kept -----------------------------


def test_a_bare_lead_in_the_model_deferred_goes_with_its_placed_block() -> None:
    """Page-Python 094: "Run only the MCP-focused checks:" was deferred for want of a fact while
    the command it introduces is kept in development_testing: the block would stand headless."""
    facts, document = _case("page_python")
    entries = _by_unit(document)
    assert entries["inherited_unit:094.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    assert entries["inherited_unit:095.code_block"]["disposition"] == "VERIFIED_PRESERVE"
    d.coordinate_neighbor_promises(document, facts)
    lead = _by_unit(document)["inherited_unit:094.paragraph"]
    assert (lead["disposition"], lead["destination_section"]) == (
        "VERIFIED_PRESERVE",
        "development_testing",
    )


@pytest.mark.parametrize(
    ("case", "lead"),
    [
        # claims of its own: a registry, a version, a code span - the model's deferral stands
        ("3d_python", "inherited_unit:012.paragraph"),
        ("page_python", "inherited_unit:012.paragraph"),
    ],
)
def test_a_lead_in_that_makes_a_claim_stays_deferred_beside_a_placed_block(
    case: str, lead: str
) -> None:
    """A deferral is an unresolved claim; the block being kept does not resolve it."""
    facts, document = _case(case)
    assert _by_unit(document)[lead]["disposition"] == "DEFER_UNRESOLVED"
    before = copy.deepcopy(_by_unit(document)[lead])
    d.coordinate_neighbor_promises(document, facts)
    assert _by_unit(document)[lead] == before


def test_a_lead_in_the_model_deferred_beside_a_superseded_example_goes_with_it() -> None:
    """PSD-Python 014/015: the plan renders the verified example under its own lead-in, so the
    inherited sentence that introduced it is covered wherever the block went."""
    facts, document = _case("psd_python")
    d.coordinate_neighbor_promises(document, facts)
    lead = _by_unit(document)["inherited_unit:014.paragraph"]
    assert (lead["disposition"], lead["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "quick_start",
    )


# ---- forward pointers (BC-07 v11: Words-.NET, Slides-Java, PDF-Go) -------------------------

POINTERS = [
    ("words_net", "inherited_unit:046.paragraph", "api_reference", "'table below'"),
    ("slides_java", "inherited_unit:037.paragraph", "additional_examples", "'example below'"),
    (
        "pdf_go",
        "inherited_unit:025.paragraph",
        "additional_examples",
        "'Encryption and Signing below' section",
    ),
]


def _pointer_errors(document: dict[str, Any], facts: FactsDocument) -> list[str]:
    # placement_errors, not reconcile_checks: normalize folds on the slice's own section
    # conditions (a trimmed fixture has fewer examples than the run), which is not what is judged
    return [e for e in d.placement_errors(document, facts) if f": {d.DANGLING_POINTER}:" in e]


@pytest.mark.parametrize(("case", "unit", "destination", "fragment"), POINTERS)
def test_a_kept_unit_whose_pointer_nothing_answers_is_refused_at_s4(
    case: str, unit: str, destination: str, fragment: str
) -> None:
    """The archived dispositions pass every S4 check today and fail BC-07 four stages later, with
    a repair that cannot act ("no repair could act on it"): only reconciliation can undo it."""
    facts, document = _case(case)
    entry = _by_unit(document)[unit]
    assert (entry["disposition"], entry["destination_section"]) == (
        "VERIFIED_PRESERVE",
        destination,
    )
    (error,) = [e for e in _pointer_errors(document, facts) if e.startswith(unit)]
    assert fragment in error and "VERIFIED_REWRITE" in error


@pytest.mark.parametrize(("case", "unit", "destination", "fragment"), POINTERS)
def test_the_last_attempt_restates_the_unit_instead_of_failing_the_stage(
    case: str, unit: str, destination: str, fragment: str
) -> None:
    facts, document = _case(case)
    recovered = d.recover_uncited_prose_omits(document, facts)
    assert recovered is not None
    folded = _by_unit(recovered)[unit]
    assert (folded["disposition"], folded["destination_section"]) == (
        "VERIFIED_REWRITE",
        destination,
    )
    assert _pointer_errors(recovered, facts) == []  # what run_job re-validates the copy by
    assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"  # the reply is not edited


def test_a_pointer_the_next_kept_unit_answers_is_not_refused() -> None:
    """Negative control: the table the sentence points at is kept right after it."""
    facts, document = _case("words_net")
    table = dataclasses.replace(
        next(f for f in facts.facts if f.id == "inherited_unit:047.html_block"),
        id="inherited_unit:047.table",
        value="| Class | Description |\n| --- | --- |\n| `Document` | A document. |",
    )
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(table if f.id == "inherited_unit:047.html_block" else f for f in facts.facts),
    )
    for entry in document["dispositions"]:
        if entry["unit_id"] == "inherited_unit:047.html_block":
            entry.update(
                unit_id="inherited_unit:047.table",
                disposition="VERIFIED_PRESERVE",
                destination_section="api_reference",
            )
    assert d.dangling_pointers(document, facts) == []


def test_a_pointer_in_a_unit_that_is_not_kept_as_written_is_not_judged() -> None:
    facts, document = _case("slides_java")
    for disposition in ("VERIFIED_REWRITE", "SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED"):
        _by_unit(document)["inherited_unit:037.paragraph"]["disposition"] = disposition
        assert d.dangling_pointers(document, facts) == []


def test_the_last_units_of_a_batch_are_not_judged_because_their_answer_may_be_in_the_next() -> None:
    facts, document = _case("slides_java")
    tail = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(f for f in facts.facts if f.kind != "inherited_unit" or f.id <= "inherited_unit:037"),
    )
    kept = {
        "dispositions": [
            e for e in document["dispositions"] if e["unit_id"] <= "inherited_unit:037"
        ]
    }
    assert d.dangling_pointers(kept, tail) == []  # 037 is now among the batch's last three


def test_an_open_colon_is_the_coordinators_not_the_pointer_check() -> None:
    """PSD-.NET 012 ends in a colon with nothing after it in quick_start: the pair is settled by
    coordinate_neighbor_promises (the lead-in follows its block), never by a refusal."""
    facts, document = _case("psd_net")
    assert d.dangling_pointers(document, facts) == []


# ---- the S4 mirrors of BC-06, BC-03 and BC-08 (3D-Java, Slides-C++, JMAP-TypeScript) -----------


def _with_text(facts: FactsDocument, unit: str, value: str) -> FactsDocument:
    return FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(dataclasses.replace(f, value=value) if f.id == unit else f for f in facts.facts),
    )


def _unit_text(facts: FactsDocument, unit: str) -> str:
    return next(f.value for f in facts.facts if f.id == unit)


def test_a_kept_list_that_names_a_forbidden_edition_is_restated_at_s4() -> None:
    """3D-Java 072.list: "... is a commercial-edition feature; see the closing note below." was
    VERIFIED_PRESERVE'd; BC-06 fails the finished README on the hyphenated label and the repair
    cannot touch a kept unit. The substance stays; the wording is re-authored without the label."""
    facts, document = _case("3d_java")
    unit = "inherited_unit:072.list"
    assert d.edition_labels(_unit_text(facts, unit)) == ["commercial-edition"]
    assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"
    d.normalize(document, facts)
    folded = _by_unit(document)[unit]
    assert (folded["disposition"], folded["destination_section"]) == (
        "VERIFIED_REWRITE",
        "scope_limitations",
    )
    assert folded["rationale"].startswith(d.RECOVERED_LABEL_RATIONALE.strip())
    assert len(folded["rationale"]) <= 160


@pytest.mark.parametrize(
    "text",
    [
        "These limitations don't apply to Aspose.3D for Java Enterprise Edition.",
        "Run `commercial edition` to see the label as a code span.",
        "STL is the only format that is fully functional in the published package.",
    ],
)
def test_text_that_names_no_forbidden_edition_is_kept_as_written(text: str) -> None:
    """Negative control: Enterprise Edition is the one edition name; a code span is not prose."""
    facts, document = _case("3d_java")
    unit = "inherited_unit:072.list"
    facts = _with_text(facts, unit, "- " + text)
    assert d.edition_labels(_unit_text(facts, unit)) == []
    d.normalize(document, facts)
    assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"


def test_a_kept_list_that_embeds_an_unverified_code_example_is_restated_at_s4() -> None:
    """Slides-C++ 102.list: an indented ```cpp fence inside a limitation item. BC-03 holds every
    fence in the ecosystem's example languages to a verified example, so the finished README
    fails, and "no failing check names an LLM-owned section" for the repair to act on."""
    facts, document = _case("slides_cpp")
    unit = "inherited_unit:102.list"
    assert d.example_fences(_unit_text(facts, unit), {"cpp", "c++", "cxx"}) == ["cpp"]
    assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"
    d.normalize(document, facts)
    folded = _by_unit(document)[unit]
    assert (folded["disposition"], folded["destination_section"]) == (
        "VERIFIED_REWRITE",
        "scope_limitations",
    )
    assert folded["rationale"].startswith(d.RECOVERED_FENCE_RATIONALE.strip())


def test_a_fence_that_is_not_an_example_language_or_not_there_is_kept_as_written() -> None:
    """Negative control: a plain-text fence, or the same list without its fence, is printable."""
    facts, document = _case("slides_cpp")
    unit = "inherited_unit:102.list"
    original = _unit_text(facts, unit)
    for text in (
        original.replace("```cpp", "```text"),
        original.replace("  ```cpp\n", "").replace("  ```\n", ""),
    ):
        assert d.example_fences(text, {"cpp", "c++", "cxx"}) == []
        document = _case("slides_cpp")[1]
        d.normalize(document, _with_text(facts, unit, text))
        assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"


def _unprinted(document: dict[str, Any], facts: FactsDocument) -> list[str]:
    return [e for e in d.placement_errors(document, facts) if f": {d.UNPRINTED_COMMAND}:" in e]


def test_a_corrected_install_block_that_nothing_prints_is_refused_at_s4() -> None:
    """JMAP-TypeScript 013: "corrected to remove the unsupported npm install command", yet the
    disposition prints nothing and BC-08 holds `npm install aspose-jmap-foss-ts` to the README."""
    facts, document = _case("jmap_typescript")
    unit = "inherited_unit:013.code_block"
    assert _by_unit(document)[unit]["disposition"] == "CORRECT_WITH_EVIDENCE"
    (error,) = _unprinted(document, facts)
    assert error.startswith(unit) and "npm install aspose-jmap-foss-ts" in error
    assert "VERIFIED_PRESERVE" in error


def test_a_rewritten_block_is_refused_the_same_way() -> None:
    facts, document = _case("jmap_typescript")
    _by_unit(document)["inherited_unit:013.code_block"]["disposition"] = "VERIFIED_REWRITE"
    assert len(_unprinted(document, facts)) == 1


def test_a_block_kept_as_written_or_whose_commands_are_printed_is_not_refused() -> None:
    """Negative controls: kept verbatim it is printed; a correction whose every command is one
    the repository records (here the test command Development and Testing prints) is printed too."""
    facts, document = _case("jmap_typescript")
    unit = "inherited_unit:013.code_block"
    _by_unit(document)[unit]["disposition"] = "VERIFIED_PRESERVE"
    assert _unprinted(document, facts) == []
    _by_unit(document)[unit]["disposition"] = "CORRECT_WITH_EVIDENCE"
    printed = _with_text(facts, unit, "```bash\nnpm test\n```")
    assert _unprinted(document, printed) == []


def _slides_net_wave5() -> tuple[FactsDocument, dict[str, Any]]:
    """Slides-.NET, wave 5 (cut e407503a): the opening kept "the things it cannot do are listed in
    full under [What it cannot do](#what-it-cannot-do)", a section of the old README the shell
    does not print, so placement drops the link and BC-07 reads "refers to a 'What it cannot do'
    section this README does not have" four stages later."""
    facts = read_facts(FIXTURES / "wave5_slides_net.facts.json")
    return facts, {"dispositions": copy.deepcopy(CASES["slides_net_w5"]["dispositions"])}


def test_a_pointer_to_a_top_level_section_the_shell_does_not_print_is_refused() -> None:
    facts, document = _slides_net_wave5()
    unit = "inherited_unit:004.paragraph"
    assert _by_unit(document)[unit]["disposition"] == "VERIFIED_PRESERVE"
    (error,) = [e for e in _pointer_errors(document, facts) if e.startswith(unit)]
    assert "'What it cannot do' section" in error


def test_a_pointer_to_a_section_the_shell_prints_is_not_refused() -> None:
    """Negative control: the same sentence naming Installation, which the shell does print."""
    facts, document = _slides_net_wave5()
    unit = "inherited_unit:004.paragraph"
    text = _unit_text(facts, unit).replace("What it cannot do", "Installation")
    text = text.replace("#what-it-cannot-do", "#installation")
    assert d.dangling_pointers(document, _with_text(facts, unit, text)) == []
