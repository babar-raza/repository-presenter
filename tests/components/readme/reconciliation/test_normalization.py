"""Placements deterministic code cannot honour fold into the disposition it can."""

from __future__ import annotations

from repository_presenter.components.readme.composition.policy import PlanningPolicy
from repository_presenter.components.readme.reconciliation.dispositions import (
    code_units_by_polarity,
    normalize,
    placement_errors,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument


def _fact(
    fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", detail: str = ""
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", detail or None),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/Aspose.Widget-FOSS-for-Python",
    "a" * 40,
    (
        _fact("identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Python"),
        _fact("format:output.glb", "format", ".glb"),
        _fact(
            "example:001",
            "example",
            "open('in.obj')",
            "UNRESOLVED",
            "lines 5-7; python fence; unit inherited_unit:003.code_block",
        ),
        _fact("link_target:001", "link_target", "https://products.aspose.com/widget/python/"),
        _fact("inherited_unit:002.paragraph", "inherited_unit", "See the Enterprise Edition."),
        _fact("inherited_unit:003.code_block", "inherited_unit", "```python\nopen('in.obj')\n```"),
        _fact("inherited_unit:005.code_block", "inherited_unit", "```mermaid\ngraph LR\n```"),
        _fact("inherited_unit:006.code_block", "inherited_unit", "```mermaid\ngraph TD\n```"),
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


def test_unrenderable_placements_are_deferred_or_superseded() -> None:
    assert code_units_by_polarity(FACTS, "UNRESOLVED") == {
        "inherited_unit:003.code_block": "example:001"
    }
    output = {
        "dispositions": [
            _entry("inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start"),
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "enterprise_relationship",
                "link_target:001",
            ),
            _entry(
                "inherited_unit:005.code_block",
                "VERIFIED_PRESERVE",
                "at_a_glance",
                "format:output.glb",
            ),
            _entry("inherited_unit:006.code_block", "VERIFIED_PRESERVE", "at_a_glance"),
        ]
    }
    assert normalize(output, FACTS) == []
    folded = {entry["unit_id"]: entry for entry in output["dispositions"]}
    assert folded["inherited_unit:003.code_block"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:003.code_block"]["destination_section"] is None
    assert folded["inherited_unit:003.code_block"]["fact_ids"] == ["example:001"]
    assert folded["inherited_unit:002.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:002.paragraph"]["destination_section"] is None
    assert folded["inherited_unit:002.paragraph"]["fact_ids"] == ["link_target:001"]
    assert folded["inherited_unit:005.code_block"]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert folded["inherited_unit:005.code_block"]["destination_section"] is None
    assert folded["inherited_unit:006.code_block"]["disposition"] == "DEFER_UNRESOLVED"
    assert placement_errors(output, FACTS) == []


def test_an_enterprise_placement_stands_once_the_policy_carries_a_target() -> None:
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "enterprise_relationship",
                "link_target:001",
            )
        ]
    }
    policy = PlanningPolicy(enterprise_target_url="https://products.aspose.com/widget/python/")
    assert normalize(output, FACTS, policy) == []
    assert output["dispositions"][0]["disposition"] == "VERIFIED_MOVE"
    assert output["dispositions"][0]["destination_section"] == "enterprise_relationship"


def test_a_verbatim_placement_into_an_absent_section_is_sent_back_for_re_routing() -> None:
    # No verified input format, so At a Glance cannot appear at this revision: a paragraph placed
    # there is re-routed by the reconciler (README_CONTRACT.md section 3), while a heading, which
    # the shell owns and never renders verbatim, needs no re-routing.
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "at_a_glance"),
            _entry("inherited_unit:007.heading", "VERIFIED_PRESERVE", "at_a_glance"),
        ]
    }
    assert normalize(output, FACTS) == [
        "inherited_unit:002.paragraph: section at_a_glance does not appear in this candidate "
        "(its condition does not hold at this revision); place the unit in another section or "
        "choose DEFER_UNRESOLVED"
    ]
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"
