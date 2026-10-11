"""A finding the repair loop cannot act on is demoted to advisory, recorded and never silent.

AGENTS.md: "Make reviewer findings repairable: each names a section and a causal stage, or it is
advisory." README_CONTRACT section 6: a finding demotes "when a deterministic check ... shows the
section it names is outside repair's scope". Wave 6 (cut 8fbf2166, 2026-10-12): 11 of the 13 BC-10
rows carried a finding that blamed a composition stage (S6) for text the composer does not write -
the Installation and Dependencies blocks, the At a Glance diagram, the API Reference's own table and
member rows - and the repair loop answered "section X is deterministic; its blocks change only when
facts change" or spent its one attempt on units that do not carry the quote.

The payloads are the reviewer's own, copied from those transactions (G:\\rp-w6, review reads kept in
raw_calls.json). The negative controls are the same reviews' findings that are about text the
composer writes - a hallucinated limitation, an opening sentence, kept maintainer text - and a
finding that names the stage that owns a wrong fact (S2): all of those still block.

A demotion is not a refutation. The reviewer may be right about renderer text (the wave-6 "verified
against this revision" narration is real), so the finding stays on the record under ``demoted``,
``reviewer_scope_defect`` and ``refuted_by`` are never set for it, and the acceptance scorer still
counts it. Routing never reads prose (tests/test_routing_fields.py): the rule reads the section and
stage the finding names, its typed ``omission``/``absent`` claims, and the quote against the units.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from repository_presenter.components.readme.repair.targeted import (
    _COMPOSITION_STAGES as LOOP_COMPOSITION_STAGES,
)
from repository_presenter.components.readme.repair.targeted import review_defects
from repository_presenter.components.readme.review.acceptance.scorer import _review_status
from repository_presenter.components.readme.review.independent import review as review_module
from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    BASIS_DEMOTED,
    BASIS_REFUTED,
    DEMOTED_QUOTE,
    DEMOTED_SECTION,
    DEMOTION_RULES,
    NAME_DENIAL_RULE,
    kept_texts,
    review_document,
    scope_rulings,
    second_read_decision,
)
from repository_presenter.components.readme.validation.registry import (
    deferred_on_required_rows,
    record_review_verdict,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

MANIFESTS = load_manifests(REPO_ROOT / "prompts")
REVIEWER = MANIFESTS["independent_review"]
AUTHORING = MANIFESTS["section_authoring"]


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


def _symbol(value: str) -> Fact:
    return _fact(f"public_symbol:{value.lower()}", "public_symbol", value)


def _finding(label: str, section: str, quote: str, text: str, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": label,
        "section_id": section,
        "causal_stage": "S6",
        "criterion": "factuality",
        "text": text,
        "quote": quote,
        "fact_ids": [],
        "absent": [],
        "omission": None,
        "repair": "Repair it.",
    }
    return {**base, **extra}


def _review(
    findings: list[dict[str, Any]],
    candidate: str,
    facts: FactsDocument,
    *,
    units: list[dict[str, Any]] | None = None,
    dispositions: dict[str, Any] | None = None,
    verdict: str = "REJECT_FACTUAL",
    second: dict[str, Any] | None = None,
    original: str = "The original README.\n",
    **extra: Any,
) -> dict[str, Any]:
    return review_document(
        {"verdict": verdict, "findings": findings, "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=candidate,
        facts=facts,
        original_readme=original,
        units={"units": units or []},
        dispositions=dispositions,
        second=second,
        **extra,
    )


# --- Aspose.Cells-FOSS-for-.NET (wave 6): the API Reference's own rows --------------------------

_FONT_ROW = "| `FontSetting` | Represents a range of characters within a cell's rich text. |"
_MEMBER_ROW = (
    "- `Properties`: Gets workbook metadata and view settings exposed by the supported API."
)
_CELLS_NET_CANDIDATE = (
    "# Aspose.Cells FOSS for .NET\n\n## API Reference\n\n"
    "Aspose.Cells FOSS for .NET provides the Workbook class as the entry point.\n\n"
    f"| Type | Description |\n| --- | --- |\n{_FONT_ROW}\n\n"
    f"### FontSetting\n\n### Workbook\n\n{_MEMBER_ROW}\n"
)
_CELLS_NET_UNITS = [
    {
        "section": "api_reference",
        "slot": "intro",
        "text": "Aspose.Cells FOSS for .NET provides the Workbook class as the entry point.",
        "fact_ids": [],
    }
]
CELLS_NET_F03 = _finding(
    "F03",
    "api_reference",
    _FONT_ROW,
    "The candidate includes 'FontSetting' in the API reference table, but the facts do not "
    "support its presence in the public surface.",
    fact_ids=["public_symbol:aspose.cells_foss.fontsetting"],
)
CELLS_NET_F04 = _finding(
    "F04",
    "api_reference",
    "### FontSetting",
    "The candidate's detailed member reference section includes 'FontSetting' members, but no "
    "facts support these members.",
)
CELLS_NET_F05 = _finding(
    "F05",
    "api_reference",
    _MEMBER_ROW,
    "The candidate's detailed member reference section includes 'Workbook' members that are not "
    "supported by the facts, such as 'Properties' and 'DocumentProperties'.",
)
CELLS_NET_FACTS = FactsDocument(
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "a" * 40,
    (
        _symbol("Aspose.Cells_FOSS.FontSetting"),
        _symbol("Aspose.Cells_FOSS.Workbook"),
        _symbol("Aspose.Cells_FOSS.Workbook.Properties"),
    ),
)


def _cells_net(findings: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return _review(
        findings, _CELLS_NET_CANDIDATE, CELLS_NET_FACTS, units=_CELLS_NET_UNITS, **kwargs
    )


def test_the_wave6_cells_net_api_rows_are_demoted_and_the_rejection_stands_down() -> None:
    """F03-F05 call rows the renderer prints from SUPPORTED public_symbol facts unsupported. No
    content unit carries them, so S6 has nothing to revise; the sealed run spent a repair on F03
    ("repaired", nothing changed) and the row failed BC-10."""
    document = _cells_net([CELLS_NET_F03, CELLS_NET_F04, CELLS_NET_F05])
    assert document["findings"] == []
    assert document["verdict"] == ACCEPT
    assert document["verdict_as_returned"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == BASIS_DEMOTED
    assert [f["id"] for f in document["advisory"]] == ["F03", "F04", "F05"]
    for record in document["advisory"]:
        assert record["demoted"]["rule"] == DEMOTED_QUOTE
        assert (record["demoted"]["section"], record["demoted"]["stage"]) == ("api_reference", "S6")
        assert record["demoted"]["owner"] == "renderer" and record["demoted"]["reason"]
        assert record["causal_state"] is None
        # Not a refutation: the reviewer is not called wrong.
        assert "refuted_by" not in record and "reviewer_scope_defect" not in record
    # The honest record survives a JSON round trip.
    assert (
        json.loads(json.dumps(document))["advisory"][0]["demoted"]
        == (document["advisory"][0]["demoted"])
    )


def test_a_denial_that_lists_its_names_is_refuted_not_demoted() -> None:
    """With the typed ``unsupported_names`` (prompt v14) the same F03 is refuted by the fact it
    cites: a refutation is the stronger record and is taken first."""
    typed = {**CELLS_NET_F03, "unsupported_names": ["FontSetting"]}
    document = _cells_net([typed])
    (record,) = document["advisory"]
    assert record["refuted_by"]["rule"] == NAME_DENIAL_RULE
    assert "demoted" not in record
    assert document["verdict_basis"] == BASIS_REFUTED


def test_a_row_carried_by_a_content_unit_is_not_the_renderers_and_still_blocks() -> None:
    """Negative control: the intro sentence is a unit's; a finding about it names a stage that can
    act, so it blocks even though it names a verified symbol in the same section."""
    sentence = "Aspose.Cells FOSS for .NET provides the Workbook class as the entry point."
    finding = _finding(
        "F02", "api_reference", sentence, "The Workbook class is not the entry point."
    )
    document = _cells_net([finding])
    assert [f["id"] for f in document["findings"]] == ["F02"]
    assert (
        document["verdict"] == "REJECT_FACTUAL" and document["verdict_basis"] == "rejection_stands"
    )
    assert "demoted" not in document["findings"][0]


def test_a_row_inside_kept_maintainer_text_is_not_demoted() -> None:
    """Kept text (VERIFIED_PRESERVE/MOVE) is printed by the renderer and no unit wrote it, but
    the repair loop routes a finding whose quote a placed unit carries to S4 (RC-04): a stage can
    act."""
    kept_id = "inherited_unit:031.list"
    facts = FactsDocument(
        CELLS_NET_FACTS.repository,
        CELLS_NET_FACTS.source_revision,
        (*CELLS_NET_FACTS.facts, _fact(kept_id, "inherited_unit", f"{_MEMBER_ROW}\n")),
    )
    dispositions = {
        "dispositions": [
            {
                "unit_id": kept_id,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "api_reference",
            }
        ]
    }
    by_id = {fact.id: fact for fact in facts.facts}
    assert kept_texts(dispositions, by_id) == [f"{_MEMBER_ROW}\n"]
    document = _review(
        [CELLS_NET_F05],
        _CELLS_NET_CANDIDATE,
        facts,
        units=_CELLS_NET_UNITS,
        dispositions=dispositions,
    )
    assert [f["id"] for f in document["findings"]] == ["F05"]
    assert document["verdict"] == "REJECT_FACTUAL"


def test_a_quote_with_no_text_to_measure_is_not_demoted() -> None:
    """A one-line fence normalizes to nothing, so "no unit carries it" proves nothing about it."""
    fence = _finding(
        "F01",
        "api_reference",
        "```csharp var wb = new Workbook(); ```",
        "The example is unsupported.",
        fact_ids=["public_symbol:aspose.cells_foss.workbook"],
    )
    candidate = _CELLS_NET_CANDIDATE + "\n```csharp\nvar wb = new Workbook();\n```\n"
    document = _review([fence], candidate, CELLS_NET_FACTS, units=_CELLS_NET_UNITS)
    assert [f["id"] for f in document["findings"]] == ["F01"]


# --- Aspose.Cells-FOSS-for-TypeScript (wave 6): a renderer sentence and a hallucinated limitation


_TS_INSTALL = (
    "`excel-cells` is not yet published on npm; build it from a source checkout instead, "
    "verified against this revision:"
)
_TS_LIMIT = (
    "The package does not implement any import functionality to load data from text formats "
    "back into a `Workbook`."
)
_TS_CANDIDATE = (
    "# Aspose.Cells FOSS for TypeScript\n\n## Installation\n\n"
    f"{_TS_INSTALL}\n\n```bash\nnpm install\n```\n\n## Scope and Limitations\n\n{_TS_LIMIT}\n"
)
TS_F01 = _finding(
    "F01",
    "installation",
    _TS_INSTALL,
    "The candidate incorrectly states that the npm package name is 'excel-cells', but the facts "
    "show the package name is not 'excel-cells' and the original README does not mention this "
    "name.",
    fact_ids=["package:name"],
)
TS_F04 = _finding(
    "F04",
    "scope_limitations",
    _TS_LIMIT,
    "The candidate states 'The package does not implement any import functionality to load data "
    "from text formats back into a Workbook', but the facts do not support this claim and the "
    "original README does not make this specific statement.",
)
TS_FACTS = FactsDocument(
    "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
    "a" * 40,
    (_fact("package:name", "package", "excel-cells"), _symbol("Workbook")),
)
TS_UNITS = [{"section": "scope_limitations", "slot": "limitation:1", "text": _TS_LIMIT}]


def test_the_wave6_cells_ts_installation_finding_is_demoted_and_the_real_one_still_blocks() -> None:
    """F01 denies the package name and cites the SUPPORTED fact that is it, about a sentence only
    the renderer prints. F04 is a limitation the facts and the original README never state - a real
    composer defect. The rejection stands on F04 alone."""
    document = _review([TS_F01, TS_F04], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS)
    assert [f["id"] for f in document["findings"]] == ["F04"]
    assert (
        document["verdict"] == "REJECT_FACTUAL" and document["verdict_basis"] == "rejection_stands"
    )
    (record,) = document["advisory"]
    assert record["id"] == "F01"
    assert record["demoted"]["rule"] == DEMOTED_SECTION
    assert (record["demoted"]["section"], record["demoted"]["stage"]) == ("installation", "S6")
    # F04 is the one the reviewer got right: composer-owned prose, blocking, routed to S6.
    (standing,) = document["findings"]
    assert standing["causal_state"] == "COMPOSING" and "demoted" not in standing


def test_the_same_installation_finding_with_its_typed_names_is_refuted() -> None:
    typed = {**TS_F01, "unsupported_names": ["excel-cells"]}
    document = _review([typed], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS)
    (record,) = document["advisory"]
    assert record["refuted_by"]["rule"] == NAME_DENIAL_RULE and "demoted" not in record


@pytest.mark.parametrize("stage", ["S2", "S3", "S4", "S5"])
def test_an_upstream_stage_on_a_deterministic_section_still_blocks(stage: str) -> None:
    """The prompt tells the reviewer to name S2 for a wrong fact ("a factual error in one is a
    finding against the fact that rendered it"). Only a mis-staged composition stage is demoted."""
    staged = {**TS_F01, "causal_stage": stage}
    document = _review([staged], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS)
    assert [f["id"] for f in document["findings"]] == ["F01"]
    assert document["verdict"] == "REJECT_FACTUAL"
    assert "demoted" not in document["findings"][0]


@pytest.mark.parametrize("stage", ["S6", "S7", "S8"])
def test_every_composition_stage_is_demoted_the_way_the_loop_reopens_it(stage: str) -> None:
    document = _review([{**TS_F01, "causal_stage": stage}], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS)
    assert document["findings"] == []
    assert document["advisory"][0]["demoted"]["stage"] == stage


def test_the_composition_stages_are_the_ones_the_repair_loop_reopens_as_s6() -> None:
    assert review_module._COMPOSITION_STAGES == LOOP_COMPOSITION_STAGES


def test_the_rule_is_the_loops_own_answer_for_every_renderer_owned_section() -> None:
    """The demotion and ``review_defects`` must agree on what is deterministic: for each section
    the rule owns, the loop reports the finding unrepairable (stage None, "deterministic")."""
    llm_sections = {"opening", "key_capabilities", "scope_limitations", "api_reference"}
    for section in sorted(review_module._DETERMINISTIC_SECTIONS):
        finding = _finding("F01", section, "x", "y")
        defects = review_defects(
            {"findings": [{**finding, "causal_state": "COMPOSING"}]}, TS_FACTS, llm_sections
        )
        assert defects[0].stage is None and "deterministic" in str(defects[0].reason), section
        demotion = review_module.unrepairable_demotion(finding, [])
        assert demotion is not None and demotion.rule == DEMOTED_SECTION, section
    # And a section the loop does revise is never demoted by it.
    for section in sorted(llm_sections - {"api_reference"}):
        assert review_module.unrepairable_demotion(_finding("F01", section, "x", "y"), []) is None


def test_removing_the_rule_restores_the_standing_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation control: without the demotion the wave-6 payloads block exactly as the sealed
    reviews did (the loop then answered "unrepairable" and the row failed BC-10)."""
    monkeypatch.setattr(review_module, "unrepairable_demotion", lambda *a, **k: None)
    ts = _review([TS_F01], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS)
    assert [f["id"] for f in ts["findings"]] == ["F01"] and ts["verdict"] == "REJECT_FACTUAL"
    net = _cells_net([CELLS_NET_F03])
    assert [f["id"] for f in net["findings"]] == ["F03"] and net["verdict"] == "REJECT_FACTUAL"


# --- Aspose.JMAP-FOSS-for-Node.js (wave 6): the reviewer is right, and it is still not the loop's


_JMAP_NARRATION = (
    "`aspose-jmap-foss` is not yet published on npm; build it from a source checkout instead, "
    "verified against this revision:"
)
_JMAP_CANDIDATE = (
    "# Aspose.JMAP FOSS for Node.js\n\n## At a Glance\n\n"
    "```mermaid\nflowchart LR\n  a --> b\n```\n\n"
    f"## Installation\n\n{_JMAP_NARRATION}\n\n```bash\nnpm install\n```\n"
)
JMAP_F02 = _finding(
    "F02",
    "at_a_glance",
    "```mermaid",
    "The Mermaid diagram in the At a Glance section is a different flowchart from the original.",
    criterion="presentation",
    omission={
        "kind": "omission",
        "section_id": "at_a_glance",
        "missing_ids": [],
        "missing_quotes": ["flowchart TD", "subgraph StartingPoints["],
    },
)
JMAP_F03 = _finding(
    "F03",
    "installation",
    _JMAP_NARRATION,
    "The candidate states 'build it from a source checkout instead, verified against this "
    "revision' but no fact supports that the installation is verified against a specific "
    "revision.",
    fact_ids=["install_command:npm"],
)
JMAP_FACTS = FactsDocument(
    "aspose-jmap-foss/Aspose.JMAP-FOSS-for-Node.js",
    "a" * 40,
    (_fact("install_command:npm", "install_command", "npm install", "CONTRADICTED"),),
)


def test_the_reviewer_being_right_about_renderer_narration_is_kept_on_the_record() -> None:
    """U-NARRATION: "verified against this revision" is renderer-printed assurance narration, so
    the reviewer is right and the loop cannot change it (the renderer lane fixes it). The finding
    leaves the blocking set but stays visible and unrefuted; the acceptance scorer does not count
    it as deferred repair work, since no revision could do it."""
    document = _review(
        [JMAP_F03], _JMAP_CANDIDATE, JMAP_FACTS, original="# Aspose.JMAP FOSS for Node.js\n"
    )
    assert document["findings"] == [] and document["verdict"] == ACCEPT
    (record,) = document["advisory"]
    assert record["demoted"]["rule"] == DEMOTED_SECTION and "refuted_by" not in record
    assert record["text"] == JMAP_F03["text"]
    status, _evidence = _review_status(["installation"], document)
    assert status == "MET"


@pytest.mark.parametrize("criterion", ["completeness", "specificity", "preservation", "links"])
def test_a_scope_or_completeness_finding_on_a_deterministic_section_keeps_its_route(
    criterion: str,
) -> None:
    """Content missing from a deterministic section is a claim about the fact set it renders from,
    which S2 can reopen (``renderer_owned_rulings``); only the two criteria a reviewer uses for
    text it is reading are renderer wording."""
    finding = {**JMAP_F03, "criterion": criterion, "fact_ids": []}
    document = _review([finding], _JMAP_CANDIDATE, JMAP_FACTS)
    assert [f["id"] for f in document["findings"]] == ["F03"]
    assert document["verdict"] == "REJECT_FACTUAL"


def test_a_standing_omission_claim_on_a_deterministic_section_is_not_demoted() -> None:
    """JMAP F02 says the section lacks text the original has (a claim about what the section
    renders from, which S2 can reopen); the existing RENDERER_OWNED_OMISSION_STANDS keeps it."""
    document = _review(
        [JMAP_F02],
        _JMAP_CANDIDATE,
        JMAP_FACTS,
        verdict="REJECT_PRESENTATION",
        original="```mermaid\nflowchart TD\n  subgraph StartingPoints[Start]\n  end\n```\n",
    )
    assert [f["id"] for f in document["findings"]] == ["F02"]
    assert document["verdict"] == "REJECT_PRESENTATION"
    assert "demoted" not in document["findings"][0]


# --- the composer-owned negative controls and the honesty record ---------------------------------

_EMAIL_OPENING = (
    "Aspose.Email FOSS for .Net reads and writes MSG and EML formats. It converts EML messages to "
    "MSG and back, preserving message content and attachments."
)
EMAIL_F01 = _finding(
    "F01",
    "opening",
    _EMAIL_OPENING,
    "The candidate's opening paragraph overstates the formats supported by the library.",
    fact_ids=["package:name"],
)


def test_a_finding_about_composer_owned_prose_blocks_even_beside_demoted_ones() -> None:
    facts = FactsDocument(
        "aspose-email-foss/Aspose.Email-FOSS-for-.Net",
        "a" * 40,
        (_fact("package:name", "package", "Aspose.Email.FOSS"),),
    )
    candidate = f"# Aspose.Email FOSS\n\n{_EMAIL_OPENING}\n\n## Installation\n\n{_TS_INSTALL}\n"
    units = [{"section": "opening", "slot": "opening", "text": _EMAIL_OPENING, "fact_ids": []}]
    document = _review([EMAIL_F01, {**TS_F01, "fact_ids": []}], candidate, facts, units=units)
    assert [f["id"] for f in document["findings"]] == ["F01"]
    assert [f["id"] for f in document["advisory"]] == ["F01"]
    assert document["advisory"][0]["section_id"] == "installation"
    assert document["verdict"] == "REJECT_FACTUAL"
    assert document["verdict_as_returned"] == "REJECT_FACTUAL"


def test_a_returned_accept_is_untouched_and_a_demotion_never_flips_a_rejection_alone() -> None:
    accepted = _cells_net([CELLS_NET_F03], verdict=ACCEPT)
    assert accepted["verdict"] == ACCEPT and accepted["verdict_basis"] == "accepted_as_returned"
    # A demoted finding beside a finding that names no section: the rejection stands.
    nameless = _finding("F09", "", "x", "y")
    mixed = _cells_net([CELLS_NET_F03, nameless])
    assert mixed["verdict"] == "REJECT_FACTUAL" and mixed["verdict_basis"] == "rejection_stands"
    assert [r["id"] for r in mixed["advisory"] if "demoted" in r] == ["F03"]
    # A rejection returned with no finding at all still has nothing to demote.
    empty = _cells_net([])
    assert empty["verdict"] == "REJECT_FACTUAL" and empty["verdict_basis"] == "rejection_stands"


def test_the_basis_says_whether_anything_was_refuted() -> None:
    """Demotions alone read ``rejection_findings_demoted``; one refutation among them keeps the
    ``rejection_refuted_deterministically`` basis, and with it the REJECTION_REFUTED second read."""
    refuted = {**CELLS_NET_F03, "unsupported_names": ["FontSetting"]}
    only = _cells_net([CELLS_NET_F04])
    mixed = _cells_net([refuted, CELLS_NET_F04])
    assert only["verdict_basis"] == BASIS_DEMOTED
    assert mixed["verdict_basis"] == BASIS_REFUTED
    assert not second_read_decision(only, []).triggered
    decision = second_read_decision(mixed, [])
    assert decision.triggered and "REJECTION_REFUTED" in decision.reasons


def test_a_second_read_finding_is_folded_by_the_same_rule() -> None:
    """The accept path is symmetric: the second read's own renderer-owned finding is demoted and
    does not survive; its composer-owned one does."""
    clean = _cells_net([CELLS_NET_F04])
    assert clean["verdict"] == ACCEPT
    second = {
        "verdict": "REJECT_FACTUAL",
        "findings": [TS_F01, {**CELLS_NET_F05, "id": "F02"}],
        "preserve": [],
    }
    document = _cells_net([CELLS_NET_F04], second=second)
    assert [(f["id"], f["reader"]) for f in document["advisory"] if f.get("reader") == 2] == [
        ("F01", 2),
        ("F02", 2),
    ]
    assert all("demoted" in f for f in document["advisory"] if f.get("reader") == 2), document[
        "advisory"
    ]
    assert document["findings"] == [] and document["verdict"] == ACCEPT
    assert document["second_reader"]["read"] == 2


def test_check_10_passes_a_demoted_accept_and_blocks_on_a_composer_finding() -> None:
    """A demoted advisory on a required row is no deferred repair work (README_CONTRACT section 6:
    "no revision could act on it"), so check 10 reads the clean review as an ACCEPT whose trigger
    did not fire. A finding that blocks still fails it."""
    trigger = {"triggered": False, "reasons": []}
    clean = _cells_net([CELLS_NET_F03, CELLS_NET_F04], trigger=trigger)
    assert deferred_on_required_rows(clean) == []
    shell = {"checks": [{"id": "BC-10", "verdict": "PENDING"}]}
    assert record_review_verdict(shell, clean)["checks"][0]["verdict"] == "PASS"
    blocked = _review([TS_F01, TS_F04], _TS_CANDIDATE, TS_FACTS, units=TS_UNITS, trigger=trigger)
    assert record_review_verdict(shell, blocked)["checks"][0]["verdict"] == "FAIL"
    # An advisory that is neither refuted nor demoted still defers repair work on a required row.
    stray = {**clean, "advisory": [{**clean["advisory"][0], "demoted": None}]}
    assert deferred_on_required_rows(stray) != []


def test_only_the_registered_rules_demote() -> None:
    assert {DEMOTED_SECTION, DEMOTED_QUOTE} == DEMOTION_RULES
    for document in (_cells_net([CELLS_NET_F03]), _review([TS_F01], _TS_CANDIDATE, TS_FACTS)):
        for record in document["advisory"]:
            assert record["demoted"]["rule"] in DEMOTION_RULES


def test_the_judgment_rulings_are_kept_beside_the_demotion() -> None:
    """The rule reads the scope rulings; it does not replace them. Both are in the record."""
    by_id = {fact.id: fact for fact in CELLS_NET_FACTS.facts}
    texts = [str(unit["text"]) for unit in _CELLS_NET_UNITS]
    rules = {
        r.rule for r in scope_rulings(CELLS_NET_F03, _CELLS_NET_CANDIDATE, by_id, "", (), texts)
    }
    assert "RENDERER_UNWRITTEN_FACT_FACTUAL" in rules
    document = _cells_net([CELLS_NET_F03])
    (record,) = document["advisory"]
    assert "RENDERER_UNWRITTEN_FACT_FACTUAL" in {r["rule"] for r in record["unrefuted_scope_rules"]}
    assert record["demoted"]["evidence"]["fact"] == "public_symbol:aspose.cells_foss.fontsetting"
