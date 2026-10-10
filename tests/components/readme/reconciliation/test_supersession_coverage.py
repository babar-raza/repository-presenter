"""TC-DSP-01 / G3-W08: a unit is dropped only when something true takes its place.

Focused cases first - each rule with the negative control that keeps it honest - then the replay:
every CURRENT sealed bundle's ``dispositions.json`` and ``facts.json`` judged under the rule, with
the per-repository table the work item's proof asks for.
"""

from __future__ import annotations

import copy
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.reconciliation.dispositions import (
    API_MEMBERS,
    EXAMPLE_NOT_VERIFIED,
    NOT_AN_API_LISTING,
    NOT_LEAD_PARAGRAPH,
    OMIT_NAMES_SUPPORTED,
    OMIT_UNRESOLVED_EXAMPLE,
    OMIT_VERIFIED_EXAMPLE,
    PLAN_DEPENDENT,
    UNRENDERED_COMMAND,
    UNRENDERED_FACTS,
    _recover_uncovered,
    coverage_findings,
    normalize,
    placement_errors,
    reconcile_checks,
    recover_uncited_prose_omits,
)
from repository_presenter.components.readme.validation.deferrals import review_deferrals
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, read_facts
from support import REPO_ROOT

REPOSITORY = "org/Aspose.Widget-FOSS-for-Python"
_UNIT_DETAIL = "lines 1-3; {kind}; unit {unit}"


def _fact(
    fact_id: str,
    kind: str,
    value: str,
    polarity: str = "SUPPORTED",
    detail: str = "",
    attributes: dict[str, str] | None = None,
) -> Fact:
    return Fact(
        fact_id,
        kind,  # type: ignore[arg-type]
        value,
        (Evidence("README.md", detail or None),),
        polarity=polarity,  # type: ignore[arg-type]
        attributes=attributes,
    )


def _symbol(path: str, symbol_kind: str) -> Fact:
    return _fact(
        f"public_symbol:{path.lower()}",
        "public_symbol",
        path,
        attributes={"symbol_kind": symbol_kind},
    )


def _unit(number: int, kind: str, text: str, section: str | None = "Widget > Usage") -> Fact:
    return _fact(
        f"inherited_unit:{number:03d}.{kind}",
        "inherited_unit",
        text,
        attributes={"section": section} if section else None,
    )


def _example(number: int, unit: str, polarity: str) -> Fact:
    return _fact(
        f"example:{number:03d}",
        "example",
        "widget.render()",
        polarity,
        _UNIT_DETAIL.format(kind="python fence", unit=unit),
    )


FACTS = FactsDocument(
    REPOSITORY,
    "a" * 40,
    (
        _fact("identity:repository", "identity", REPOSITORY),
        _fact("identity:ecosystem", "identity", "python"),
        _fact("package:name", "package", "widget"),
        _fact("install_command:pip", "install_command", "pip install widget"),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
        _fact("dependency:none", "dependency", "none"),
        _symbol("widget", "module"),
        _symbol("widget.Widget", "class"),
        _symbol("widget.Mode", "enum"),
        _symbol("widget.Widget.render", "method"),
        _example(1, "inherited_unit:020.code_block", "SUPPORTED"),
        _example(2, "inherited_unit:021.code_block", "UNRESOLVED"),
        _example(3, "inherited_unit:022.code_block", "CONTRADICTED"),
        _unit(1, "heading", "# Widget", None),
        _unit(2, "paragraph", "Widget renders things for servers.", "Widget"),
        _unit(3, "paragraph", "It is meant for build pipelines and servers.", "Widget"),
        _unit(
            4,
            "table",
            "| Class | Description |\n|---|---|\n| `Widget` | Renders. |\n| `Mode` | Modes. |",
        ),
        _unit(5, "list", "- `Widget`\n- `Mode`"),
        _unit(6, "list", "- `Widget`\n  - `render(path)` / `save()`"),
        _unit(7, "table", "| Member | Description |\n|---|---|\n| `render` | Renders. |"),
        _unit(8, "table", "| Class | Description |\n|---|---|\n| `Ghost` | Not verified. |"),
        _unit(9, "code_block", "```bash\npip install widget\n```", "Widget > Installation"),
        _unit(
            10,
            "code_block",
            "```bash\ngit clone https://example.test/widget.git\ncd widget\npip install -e .\n```",
            "Widget > Installation",
        ),
        _unit(
            11,
            "code_block",
            "```xml\n<dependency><artifactId>widget</artifactId></dependency>\n```",
            "Widget > Installation",
        ),
        _unit(12, "list", "- Render a widget\n- Choose a mode", "Widget > Features"),
        _unit(13, "paragraph", "Run the suite with `pytest` before sending a change.", "Widget"),
        _unit(14, "table", "| Version | Status |\n|---|---|\n| 1.x | supported |"),
        _unit(15, "paragraph", "The `Widget` class renders a widget.", "Widget > Reference"),
        _unit(16, "paragraph", "Where the sources live: `src/widget/`.", "Widget > Layout"),
        _unit(17, "list", "- `src/widget/` holds the sources", "Widget > Layout"),
        _unit(20, "code_block", "```python\nimport widget\nwidget.render()\n```", "Widget > Usage"),
        _unit(21, "code_block", "```python\nwidget.slow()\n```", "Widget > Usage"),
        _unit(22, "code_block", "```python\nwidget.boom()\n```", "Widget > Usage"),
        _unit(23, "code_block", "```mermaid\ngraph LR\n```", "Widget > At a Glance"),
        _unit(24, "paragraph", "Nothing here is checkable.", "Widget > Notes"),
        _unit(25, "code_block", "```text\nwidget.render and Widget.render in one block\n```"),
        _unit(26, "table", "| Class | Description |\n|---|---|\n| `widget.Widget` | Renders. |"),
        _unit(27, "list", "- `Widget.render`"),
    ),
)
WIDGET = "public_symbol:widget.widget"
MODE = "public_symbol:widget.mode"
RENDER = "public_symbol:widget.widget.render"
MODULE = "public_symbol:widget"


def _entry(unit: str, disposition: str, destination: str | None, *fact_ids: str) -> dict[str, Any]:
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": list(fact_ids),
        "rationale": "because",
    }


def _only(unit: str, disposition: str, destination: str | None, *fact_ids: str) -> dict[str, Any]:
    return {"dispositions": [_entry(unit, disposition, destination, *fact_ids)]}


def _reasons(output: dict[str, Any], facts: FactsDocument = FACTS) -> dict[str, str]:
    return {gap.unit_id: gap.reason for gap in coverage_findings(output, facts)}


# --- a supersession stands only where the destination provably carries the unit -------------


def test_a_table_of_verified_classes_is_still_superseded_by_the_core_api_table() -> None:
    """The Email-Python case: an inherited class table placed into the reference is covered by
    the Core API table, which prints every verified class and enum."""
    output = {
        "dispositions": [
            _entry("inherited_unit:004.table", "VERIFIED_PRESERVE", "api_reference", WIDGET),
            _entry("inherited_unit:005.list", "VERIFIED_PRESERVE", "api_reference", WIDGET, MODE),
        ]
    }
    assert normalize(output, FACTS) == []
    table, listing = output["dispositions"]
    assert (table["disposition"], table["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "api_reference",
    )
    # A list that names classes and enums only is the same duplicate in another shape.
    assert listing["disposition"] == "VERIFIED_PRESERVE"
    superseded = {
        "dispositions": [
            _entry("inherited_unit:005.list", "SUPERSEDE_REDUNDANT", "api_reference", WIDGET, MODE)
        ]
    }
    assert coverage_findings(superseded, FACTS) == []
    assert normalize(superseded, FACTS) == []
    assert superseded["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_listing_that_spells_a_verified_member_is_not_covered_by_the_core_api_table() -> None:
    """Negative control: the table prints classes and enums, not what a class can do. The members
    list (Email-Python's Detailed Member Reference, RC-06) carries verified content the table
    does not, so calling it a duplicate drops it."""
    for unit in ("inherited_unit:006.list", "inherited_unit:007.table"):
        output = {"dispositions": [_entry(unit, "VERIFIED_PRESERVE", "api_reference", WIDGET)]}
        assert normalize(output, FACTS) == []
        assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE", unit
    raw = _only("inherited_unit:006.list", "SUPERSEDE_REDUNDANT", "api_reference", WIDGET)
    assert _reasons(raw) == {"inherited_unit:006.list": NOT_AN_API_LISTING}
    named = _only("inherited_unit:027.list", "SUPERSEDE_REDUNDANT", "api_reference", WIDGET)
    assert _reasons(named) == {"inherited_unit:027.list": API_MEMBERS}
    assert normalize(raw, FACTS) == []
    assert raw["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_class_table_naming_an_unverified_class_is_still_superseded() -> None:
    """Dropping a name no fact verifies publishes nothing unverified, so the Core API table
    (which lists every verified class) still stands in for the table."""
    output = _only("inherited_unit:008.table", "VERIFIED_PRESERVE", "api_reference")
    assert normalize(output, FACTS) == []
    assert output["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_an_api_reference_paragraph_or_code_block_is_never_covered_by_the_class_table() -> None:
    for unit in ("inherited_unit:015.paragraph", "inherited_unit:025.code_block"):
        raw = _only(unit, "SUPERSEDE_REDUNDANT", "api_reference", WIDGET)
        assert coverage_findings(raw, FACTS), unit
        assert normalize(raw, FACTS) == []
        assert raw["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE", unit


def test_only_the_lead_paragraph_is_replaced_by_the_opening() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "opening"),
            _entry("inherited_unit:003.paragraph", "VERIFIED_PRESERVE", "opening"),
        ]
    }
    assert normalize(output, FACTS) == []
    lead, second = output["dispositions"]
    assert lead["disposition"] == "SUPERSEDE_REDUNDANT"
    # Slides-.NET 004: who the library is for. Another paragraph states claims of its own.
    assert second["disposition"] == "VERIFIED_PRESERVE"
    raw = _only("inherited_unit:003.paragraph", "SUPERSEDE_REDUNDANT", "opening")
    assert _reasons(raw) == {"inherited_unit:003.paragraph": NOT_LEAD_PARAGRAPH}
    assert normalize(raw, FACTS) == []
    assert raw["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_an_install_block_is_superseded_only_when_the_row_prints_its_commands() -> None:
    covered = _only(
        "inherited_unit:009.code_block",
        "SUPERSEDE_REDUNDANT",
        "installation",
        "install_command:pip",
    )
    assert coverage_findings(covered, FACTS) == []
    for unit, reason in (
        ("inherited_unit:010.code_block", UNRENDERED_COMMAND),  # a build from a clone
        ("inherited_unit:011.code_block", UNRENDERED_COMMAND),  # a second package manager
    ):
        raw = _only(unit, "SUPERSEDE_REDUNDANT", "installation", "install_command:pip")
        assert _reasons(raw) == {unit: reason}
        assert normalize(raw, FACTS) == []
        # The section is not one the shell can place into, so the reply is refused with the
        # reason and the unit's exact text, for the one re-ask.
        [error] = placement_errors(raw, FACTS)
        assert error.startswith(f"{unit}: uncovered_supersession: ")
        assert "installation prints the verified install command" in error
        assert "pip install -e ." in error or "artifactId" in error


def test_a_paragraph_resting_on_facts_the_section_does_not_render_is_not_superseded() -> None:
    covered = _only(
        "inherited_unit:013.paragraph", "SUPERSEDE_REDUNDANT", "installation", "install_command:pip"
    )
    assert _reasons(covered) == {}
    uncovered = _only(
        "inherited_unit:013.paragraph",
        "SUPERSEDE_REDUNDANT",
        "installation",
        "install_command:pip",
        "build_test_asset:tests",
    )
    assert _reasons(uncovered) == {"inherited_unit:013.paragraph": UNRENDERED_FACTS}


def test_a_section_that_renders_from_facts_prints_only_the_kinds_it_renders() -> None:
    table = _only("inherited_unit:014.table", "SUPERSEDE_REDUNDANT", "dependencies")
    assert _reasons(table) == {}
    paragraph = _only("inherited_unit:003.paragraph", "SUPERSEDE_REDUNDANT", "identity")
    assert list(_reasons(paragraph).values()) == ["section_renders_other_kinds"]
    assert normalize(paragraph, FACTS) == []
    assert paragraph["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert paragraph["dispositions"][0]["fact_ids"] == []  # no rendered fact is borrowed for it
    assert placement_errors(paragraph, FACTS)


def test_a_supersession_into_a_section_the_plan_fills_stays_a_placement() -> None:
    """The prompt tells the reconciler to supersede a capability list "re-authored under
    key_capabilities", but what that section carries is the plan's choice, made after this stage.
    Nothing here proves the list is carried, so it stays placed and placement, which holds the
    plan, decides whether it overlaps. It is folded rather than refused: the reply is the one the
    prompt asks for."""
    for unit, destination in (
        ("inherited_unit:012.list", "key_capabilities"),
        ("inherited_unit:010.code_block", "development_testing"),
        ("inherited_unit:013.paragraph", "quick_start"),
        ("inherited_unit:014.table", "scope_limitations"),
    ):
        output = _only(unit, "SUPERSEDE_REDUNDANT", destination, WIDGET)
        assert list(_reasons(output).values()) == [PLAN_DEPENDENT], (unit, destination)
        assert normalize(output, FACTS) == []
        entry = output["dispositions"][0]
        assert (entry["disposition"], entry["destination_section"]) == (
            "VERIFIED_PRESERVE",
            destination,
        )
        assert placement_errors(output, FACTS) == []


def test_a_section_that_must_carry_a_superseded_unit_keeps_the_supersession() -> None:
    """authoring.carried_units makes development_testing, scope_limitations and
    enterprise_relationship cite or explicitly omit every prose unit superseded into them, so for
    prose the supersession is provable."""
    for destination in ("development_testing", "scope_limitations"):
        for unit in ("inherited_unit:013.paragraph", "inherited_unit:012.list"):
            output = _only(unit, "SUPERSEDE_REDUNDANT", destination, "build_test_asset:tests")
            assert coverage_findings(output, FACTS) == [], (unit, destination)
            assert normalize(output, FACTS) == []
            assert output["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_supersession_by_the_diagram_needs_a_diagram() -> None:
    """At a Glance is one Mermaid fence: a diagram placed there is covered by the renderer's,
    a paragraph is not carried by any diagram and is deferred, not called redundant."""
    prose = _only("inherited_unit:013.paragraph", "SUPERSEDE_REDUNDANT", "at_a_glance", WIDGET)
    assert normalize(prose, FACTS) == []
    entry = prose["dispositions"][0]
    assert (entry["disposition"], entry["destination_section"]) == ("DEFER_UNRESOLVED", None)
    diagram = _only("inherited_unit:023.code_block", "SUPERSEDE_REDUNDANT", "at_a_glance", WIDGET)
    assert normalize(diagram, FACTS) == []
    assert diagram["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_shell_owned_unit_is_superseded_wherever_it_is_sent() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", "key_capabilities"),
            _entry("inherited_unit:023.code_block", "SUPERSEDE_REDUNDANT", None, WIDGET),
        ]
    }
    assert coverage_findings(output, FACTS) == []
    assert normalize(output, FACTS) == []
    assert [d["disposition"] for d in output["dispositions"]] == ["SUPERSEDE_REDUNDANT"] * 2


# --- examples: the plan owns verified ones, an unverified one is withheld --------------------


def test_a_verified_example_superseded_into_an_example_section_is_the_plans_to_render() -> None:
    output = _only("inherited_unit:020.code_block", "SUPERSEDE_REDUNDANT", "quick_start")
    assert coverage_findings(output, FACTS) == []
    elsewhere = _only("inherited_unit:020.code_block", "SUPERSEDE_REDUNDANT", "installation")
    assert coverage_findings(elsewhere, FACTS)


def test_a_superseded_example_that_never_verified_is_withheld_not_called_redundant() -> None:
    unresolved = _only(
        "inherited_unit:021.code_block", "SUPERSEDE_REDUNDANT", "additional_examples"
    )
    assert _reasons(unresolved) == {"inherited_unit:021.code_block": EXAMPLE_NOT_VERIFIED}
    assert normalize(unresolved, FACTS) == []
    entry = unresolved["dispositions"][0]
    assert (entry["disposition"], entry["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert entry["fact_ids"] == ["example:002"]
    contradicted = _only("inherited_unit:022.code_block", "SUPERSEDE_REDUNDANT", "quick_start")
    assert normalize(contradicted, FACTS) == []
    entry = contradicted["dispositions"][0]
    assert (entry["disposition"], entry["fact_ids"]) == ("OMIT_UNSUPPORTED", ["example:003"])


# --- an omission needs a failed support lookup ------------------------------------------------


def test_omitting_an_unresolved_example_is_a_deferral() -> None:
    """Words-Python Quick Start: four examples NOT_VERIFIED, all four omitted as "not supported
    by facts". The facts neither support nor contradict them; that is DEFER_UNRESOLVED, which
    BC-05 then judges by cause (here: no verified Quick Start at all) instead of passing."""
    output = _only("inherited_unit:021.code_block", "OMIT_UNSUPPORTED", None)
    assert _reasons(output) == {"inherited_unit:021.code_block": OMIT_UNRESOLVED_EXAMPLE}
    assert normalize(output, FACTS) == []
    entry = output["dispositions"][0]
    assert (entry["disposition"], entry["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert entry["fact_ids"] == ["example:002"]
    assert placement_errors(output, FACTS) == []


def test_omitting_a_verified_example_is_refused_and_recovered_into_the_plans_examples() -> None:
    output = _only("inherited_unit:020.code_block", "OMIT_UNSUPPORTED", None)
    assert _reasons(output) == {"inherited_unit:020.code_block": OMIT_VERIFIED_EXAMPLE}
    assert normalize(output, FACTS) == []
    [error] = placement_errors(output, FACTS)
    assert error.startswith("inherited_unit:020.code_block: supported_omission: ")
    assert "its example example:001 is verified" in error
    assert "widget.render()" in error  # the unit's exact text is quoted back
    recovered = recover_uncited_prose_omits(output, FACTS)
    assert recovered is not None
    entry = recovered["dispositions"][0]
    assert (entry["disposition"], entry["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "additional_examples",
    )
    assert entry["fact_ids"] == ["example:001"]
    assert reconcile_checks(recovered, FACTS) == []
    assert output["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"  # the reply is untouched


def test_an_uncited_omission_of_a_block_that_spells_a_supported_fact_is_refused() -> None:
    omitted = _only("inherited_unit:026.table", "OMIT_UNSUPPORTED", None)
    assert _reasons(omitted) == {"inherited_unit:026.table": OMIT_NAMES_SUPPORTED}
    assert [e.split(":")[2].strip() for e in placement_errors(omitted, FACTS)] == [
        "supported_omission"
    ]
    # Negative controls: a cited reason stands, so does a heading (the shell's) and a block that
    # spells no SUPPORTED fact; an uncited prose omission is the existing rule's, reported once.
    cited = _only("inherited_unit:026.table", "OMIT_UNSUPPORTED", None, WIDGET)
    assert coverage_findings(cited, FACTS) == []
    heading = _only("inherited_unit:001.heading", "OMIT_UNSUPPORTED", None)
    assert coverage_findings(heading, FACTS) == []
    plain = _only("inherited_unit:011.code_block", "OMIT_UNSUPPORTED", None)
    assert coverage_findings(plain, FACTS) == []
    prose = _only("inherited_unit:015.paragraph", "OMIT_UNSUPPORTED", None)
    assert coverage_findings(prose, FACTS) == []
    assert [e.split(":")[2].strip() for e in placement_errors(prose, FACTS)] == [
        "uncited_prose_omit"
    ]


def test_a_contradicted_example_may_still_be_omitted() -> None:
    output = _only("inherited_unit:022.code_block", "OMIT_UNSUPPORTED", None, "example:003")
    assert coverage_findings(output, FACTS) == []
    uncited = _only("inherited_unit:022.code_block", "OMIT_UNSUPPORTED", None)
    assert coverage_findings(uncited, FACTS) == []


# --- the citation that would make placement discard a unit ------------------------------------


def test_class_citations_a_unit_does_not_state_are_dropped_so_it_is_not_discarded_as_covered() -> (
    None
):
    """Cells-Rust Project Structure: placed into api_reference with five class symbols cited that
    its text never names. Placement drops a placed unit whose citations intersect what the section
    renders, so the unit was discarded as "covered" while the Core API table said nothing about
    it. A table the Core API table does cover keeps its citations (and is still dropped)."""
    output = {
        "dispositions": [
            _entry("inherited_unit:016.paragraph", "VERIFIED_PRESERVE", "api_reference", WIDGET),
            _entry("inherited_unit:006.list", "VERIFIED_PRESERVE", "api_reference", WIDGET),
            _entry("inherited_unit:017.list", "VERIFIED_PRESERVE", "api_reference", WIDGET, MODE),
            _entry("inherited_unit:005.list", "VERIFIED_PRESERVE", "api_reference", WIDGET, MODE),
        ]
    }
    assert normalize(output, FACTS) == []
    structure, members, tree, classes = output["dispositions"]
    assert WIDGET not in structure["fact_ids"]
    assert members["fact_ids"] == []  # it spells a method, which the class table does not print
    assert not {WIDGET, MODE} & set(tree["fact_ids"])
    assert set(classes["fact_ids"]) == {MODE, WIDGET}


# --- malformed and stale output --------------------------------------------------------------


def test_malformed_model_output_never_raises_and_is_never_dropped() -> None:
    output = {
        "dispositions": [
            {"unit_id": "inherited_unit:002.paragraph", "disposition": "SUPERSEDE_REDUNDANT"},
            {
                "unit_id": "inherited_unit:999.paragraph",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "key_capabilities",
                "fact_ids": None,
            },
            {
                "unit_id": "inherited_unit:011.code_block",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": ["public_symbol:does.not.exist"],
            },
            {"unit_id": "inherited_unit:012.list", "disposition": "NOT_A_DISPOSITION"},
            {"disposition": "SUPERSEDE_REDUNDANT", "destination_section": "installation"},
        ]
    }
    before = copy.deepcopy(output)
    normalize(output, FACTS)
    placement_errors(output, FACTS)
    coverage_findings(output, FACTS)
    recover_uncited_prose_omits(output, FACTS)
    assert len(output["dispositions"]) == len(before["dispositions"])
    assert output["dispositions"][3] == before["dispositions"][3]
    assert recover_uncited_prose_omits({"dispositions": "not a list"}, FACTS) is None


def test_normalising_twice_changes_nothing_more() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:004.table", "VERIFIED_PRESERVE", "api_reference", WIDGET),
            _entry("inherited_unit:006.list", "SUPERSEDE_REDUNDANT", "api_reference", WIDGET),
            _entry("inherited_unit:012.list", "SUPERSEDE_REDUNDANT", "key_capabilities", WIDGET),
            _entry("inherited_unit:021.code_block", "OMIT_UNSUPPORTED", None),
            _entry("inherited_unit:003.paragraph", "VERIFIED_PRESERVE", "opening"),
            _entry("inherited_unit:016.paragraph", "VERIFIED_PRESERVE", "api_reference", WIDGET),
        ]
    }
    normalize(output, FACTS)
    once = copy.deepcopy(output)
    normalize(output, FACTS)
    assert output == once


def test_the_recovered_reply_still_has_to_pass_the_checks() -> None:
    """recover= is a last attempt, not a way round the checks: a section that renders from facts
    cannot carry the unit, so the last attempt withdraws the claim - deferred, listed, never
    rendered - and the result passes the same checks any reply does."""
    raw = _only("inherited_unit:011.code_block", "SUPERSEDE_REDUNDANT", "installation")
    assert normalize(raw, FACTS) == []
    assert placement_errors(raw, FACTS)
    recovered = recover_uncited_prose_omits(raw, FACTS)
    assert recovered is not None
    entry = recovered["dispositions"][0]
    assert (entry["disposition"], entry["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert entry["rationale"].startswith("Not provably carried by the section named")
    assert len(entry["rationale"]) <= 160
    assert reconcile_checks(recovered, FACTS) == []


# --- the replay: every CURRENT sealed bundle under the rule ----------------------------------

CANDIDATES = REPO_ROOT / "candidates"
_SEALED = {
    "Words-Python": ("aspose-words-foss__Aspose.Words-FOSS-for-Python", "2d2efee2"),
    "Slides-.NET": ("aspose-slides-foss__Aspose.Slides-FOSS-for-.NET", "86c441b5"),
    "Cells-Rust": ("aspose-cells-foss__Aspose.Cells-FOSS-for-Rust", "1a6004af"),
}
_ALLOWED_FOLDS = {
    ("SUPERSEDE_REDUNDANT", "VERIFIED_PRESERVE"),
    # A preserved unit still meets the placement rules: a contradicted link makes it a rewrite.
    ("SUPERSEDE_REDUNDANT", "VERIFIED_REWRITE"),
    ("SUPERSEDE_REDUNDANT", "DEFER_UNRESOLVED"),
    ("SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED"),
    ("OMIT_UNSUPPORTED", "DEFER_UNRESOLVED"),
}


@dataclass
class ReplayRow:
    repository: str
    revision: str
    supersede: int = 0
    omit: int = 0
    not_standing: Counter[str] = field(default_factory=Counter)
    omit_not_standing: Counter[str] = field(default_factory=Counter)
    uncited_prose_omit: int = 0
    folds: Counter[tuple[str, str]] = field(default_factory=Counter)
    pruned: int = 0
    refused: int = 0
    blocks_before: int = 0
    blocks_after: int = 0
    findings: list[Any] = field(default_factory=list)
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    final: dict[str, Any] = field(default_factory=dict)
    facts: FactsDocument | None = None


def _current_bundles() -> list[tuple[str, Path]]:
    if not CANDIDATES.is_dir():
        return []
    found = []
    for slug in sorted(CANDIDATES.iterdir()):
        marker = slug / "CURRENT"
        if marker.is_file():
            bundle = slug / marker.read_text(encoding="utf-8").strip()
            if (bundle / "dispositions.json").is_file() and (bundle / "facts.json").is_file():
                found.append((slug.name.split("__", 1)[-1], bundle))
    return found


def replay(name: str, bundle: Path) -> ReplayRow:
    """One sealed bundle's dispositions judged under the rule, and folded by ``normalize``."""
    facts = read_facts(bundle / "facts.json")
    before = json.loads((bundle / "dispositions.json").read_text(encoding="utf-8"))
    plan_path = bundle / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.is_file() else None
    row = ReplayRow(name, bundle.name, before=before, facts=facts)
    entries = before["dispositions"]
    row.supersede = sum(e["disposition"] == "SUPERSEDE_REDUNDANT" for e in entries)
    row.omit = sum(e["disposition"] == "OMIT_UNSUPPORTED" for e in entries)
    row.findings = coverage_findings(before, facts)
    for gap in row.findings:
        target = (
            row.omit_not_standing if gap.disposition == "OMIT_UNSUPPORTED" else row.not_standing
        )
        target[gap.reason] += 1
    row.uncited_prose_omit = sum(
        1 for error in placement_errors(before, facts) if "uncited_prose_omit" in error
    )
    after = copy.deepcopy(before)
    normalize(after, facts)
    row.after = after
    for old, new in zip(entries, after["dispositions"], strict=True):
        if old["disposition"] != new["disposition"]:
            row.folds[(old["disposition"], new["disposition"])] += 1
        elif old.get("fact_ids") != new.get("fact_ids") and new["disposition"] in {
            "VERIFIED_PRESERVE",
            "VERIFIED_MOVE",
        }:
            row.pruned += 1
    new_refusals = (
        error
        for error in placement_errors(after, facts)
        if "uncovered_supersession" in error or "supported_omission" in error
    )
    row.refused = sum(1 for _ in new_refusals)
    # What the last attempt leaves if the one re-ask changed nothing: the claim withdrawn.
    last = copy.deepcopy(after)
    _recover_uncovered(last, facts)
    row.final = last

    def blocks(document: dict[str, Any]) -> int:
        return sum(f.decision == "BLOCK" for f in review_deferrals(document, facts, plan))

    row.blocks_before, row.blocks_after = blocks(before), blocks(last)
    return row


def replay_table(rows: list[ReplayRow]) -> str:
    """The per-repository table: dispositions that would no longer stand, and why."""
    lines = [
        "| repository | SUPERSEDE | no longer stands | OMIT | no longer stands | "
        "prose omit already refused | folded | citations pruned | new re-asks | BC-05 blocks |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    total = ReplayRow("total", "")
    for row in rows:
        folds = ", ".join(
            f"{count} {old.split('_')[0].lower()}->{new.split('_')[-1].lower()}"
            for (old, new), count in sorted(row.folds.items())
        )
        lines.append(
            f"| {row.repository} | {row.supersede} | {sum(row.not_standing.values())} "
            f"({_counts(row.not_standing)}) | {row.omit} | {sum(row.omit_not_standing.values())} "
            f"({_counts(row.omit_not_standing)}) | {row.uncited_prose_omit} | {folds or '-'} | "
            f"{row.pruned} | {row.refused} | {row.blocks_before}->{row.blocks_after} |"
        )
        total.supersede += row.supersede
        total.omit += row.omit
        total.not_standing.update(row.not_standing)
        total.omit_not_standing.update(row.omit_not_standing)
        total.uncited_prose_omit += row.uncited_prose_omit
        total.folds.update(row.folds)
        total.pruned += row.pruned
        total.refused += row.refused
        total.blocks_before += row.blocks_before
        total.blocks_after += row.blocks_after
    lines.append(
        f"| **{len(rows)} repositories** | {total.supersede} | "
        f"{sum(total.not_standing.values())} ({_counts(total.not_standing)}) | {total.omit} | "
        f"{sum(total.omit_not_standing.values())} ({_counts(total.omit_not_standing)}) | "
        f"{total.uncited_prose_omit} | {sum(total.folds.values())} | {total.pruned} | "
        f"{total.refused} | {total.blocks_before}->{total.blocks_after} |"
    )
    return "\n".join(lines)


def _counts(counter: Counter[str]) -> str:
    return ", ".join(f"{n} {reason}" for reason, n in sorted(counter.items())) or "-"


needs_candidates = pytest.mark.skipif(not _current_bundles(), reason="no sealed candidates")


@needs_candidates
def test_the_replay_over_every_current_bundle_only_folds_and_never_drops() -> None:
    rows = [replay(name, bundle) for name, bundle in _current_bundles()]
    assert rows
    for row in rows:
        # Nothing is dropped: the same units in the same order, and every change is a fold the
        # rule allows (a supersession becomes a placement or a deferral, an omission a deferral).
        assert [e["unit_id"] for e in row.after["dispositions"]] == [
            e["unit_id"] for e in row.before["dispositions"]
        ], row.repository
        assert set(row.folds) <= _ALLOWED_FOLDS, (row.repository, row.folds)
        # Idempotent: the folded output is what the store keeps and re-judges on reuse.
        again = copy.deepcopy(row.after)
        assert row.facts is not None
        normalize(again, row.facts)
        assert again == row.after, row.repository
        # And after the last attempt's recovery nothing is left that claims more than the stage
        # can prove: the transaction never fails closed on this rule.
        assert coverage_findings(row.final, row.facts) == [], row.repository
    table = replay_table(rows)
    destination = os.environ.get("REPLAY_TABLE_OUT")
    if destination:
        Path(destination).write_text(table + "\n", encoding="utf-8")
    assert table.count("\n") == len(rows) + 2


def _sealed(label: str) -> ReplayRow:
    slug, revision = _SEALED[label]
    bundle = next(
        (b for name, b in _current_bundles() if name == slug.split("__", 1)[-1]),
        None,
    )
    if bundle is None or not bundle.name.startswith(revision):
        pytest.skip(f"{label} has been resealed since {revision}")
    return replay(label, bundle)


@needs_candidates
def test_words_python_quick_start_no_longer_stands_on_its_sealed_inputs() -> None:
    """Review A: Quick Start and Additional Examples gone. The sealed dispositions omit all four
    examples as "not supported by facts" while their example facts are UNRESOLVED (no interpreter
    satisfies requires-python), and the Quick Start paragraphs around them uncited."""
    row = _sealed("Words-Python")
    by_unit = {g.unit_id: g.reason for g in row.findings}
    for unit in (29, 31, 36, 40):
        assert by_unit[f"inherited_unit:{unit:03d}.code_block"] == OMIT_UNRESOLVED_EXAMPLE
    assert row.uncited_prose_omit >= 2  # 028 and 030, the lead-ins, were refused already
    assert row.omit_not_standing[OMIT_UNRESOLVED_EXAMPLE] == 4
    folded = {e["unit_id"]: e for e in row.after["dispositions"]}
    for unit, example in ((29, "example:001"), (31, "example:002")):
        entry = folded[f"inherited_unit:{unit:03d}.code_block"]
        assert entry["disposition"] == "DEFER_UNRESOLVED"
        assert example in entry["fact_ids"]
    assert row.blocks_after > row.blocks_before  # BC-05 now sees the missing Quick Start


@needs_candidates
def test_slides_dotnet_sealed_inputs_lose_nothing_under_a_false_label() -> None:
    row = _sealed("Slides-.NET")
    by_unit = {g.unit_id: g.reason for g in row.findings}
    assert by_unit["inherited_unit:004.paragraph"] == NOT_LEAD_PARAGRAPH  # who it is for
    assert by_unit["inherited_unit:013.paragraph"] == UNRENDERED_FACTS  # net8.0 and net10.0
    assert by_unit["inherited_unit:016.code_block"] == UNRENDERED_COMMAND  # build from source
    assert by_unit["inherited_unit:034.code_block"] == OMIT_UNRESOLVED_EXAMPLE  # the usings
    assert by_unit["inherited_unit:060.list"] == PLAN_DEPENDENT  # What it can do
    # The Quick Start example itself (025) was already deferred, correctly, as unverified.
    entries = {e["unit_id"]: e for e in row.before["dispositions"]}
    assert entries["inherited_unit:025.code_block"]["disposition"] == "DEFER_UNRESOLVED"


@needs_candidates
def test_cells_rust_project_structure_is_no_longer_discarded_as_covered() -> None:
    row = _sealed("Cells-Rust")
    assert row.facts is not None
    from repository_presenter.components.readme.composition.placement import renderer_fact_ids

    covered = renderer_fact_ids("api_reference", row.facts)
    before = {e["unit_id"]: e for e in row.before["dispositions"]}
    after = {e["unit_id"]: e for e in row.after["dispositions"]}
    paragraph = "inherited_unit:045.paragraph"  # "The library source lives under src/..."
    assert before[paragraph]["disposition"] == "VERIFIED_PRESERVE"
    assert set(before[paragraph]["fact_ids"]) & covered  # placement would discard it
    assert after[paragraph]["disposition"] == "VERIFIED_PRESERVE"
    assert not set(after[paragraph]["fact_ids"]) & covered
    # The installation alternatives the Installation row never prints are no longer redundant.
    reasons = {g.unit_id: g.reason for g in row.findings}
    assert reasons["inherited_unit:013.code_block"] == UNRENDERED_COMMAND
    assert reasons["inherited_unit:015.code_block"] == UNRENDERED_COMMAND
    # Additional Examples was lost to UNRESOLVED examples (no cargo at sealing), which is a
    # deferral and stays one: not a disposition defect, and not flagged.
    assert before["inherited_unit:034.code_block"]["disposition"] == "DEFER_UNRESOLVED"
    assert "inherited_unit:034.code_block" not in reasons
