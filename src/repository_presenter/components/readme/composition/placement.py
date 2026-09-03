"""Placement of inherited units at render: the decision the renderer and the validator share.

docs/README_CONTRACT.md section 3 places every VERIFIED_PRESERVE and VERIFIED_MOVE unit in its
destination section under three rules, each a confirmed G1 defect. Placement is exclusive, never
additive, on fact-ID overlap: a unit whose cited facts intersect the destination's own plan-driven
content is dropped, because the planned, freshly authored content already covers that material
and passed the evidence-bound checks. A placed unit inherits its section's visibility: in a
collapsible section it renders inside the details block, never appended outside it. A placed
unit whose destination the plan excludes is never dropped silently: planning fails closed naming
the unit (planning.plan_checks), and here it is recorded as excluded so the validator can see it.

A code block the plan or the renderer already owns - an ecosystem example or a Mermaid block -
renders through them, not verbatim; any other unit renders as written.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from repository_presenter.core.facts import FactsDocument

PLACED = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
_RENDERED_ELSEWHERE = frozenset({"heading", "badge_row"})
Outcome = Literal["placed", "overlap", "owned_elsewhere", "excluded"]


@dataclass(frozen=True)
class Placement:
    unit_id: str
    destination: str
    text: str
    outcome: Outcome
    overlap: tuple[str, ...] = ()


def renders_verbatim(unit_id: str, value: str, ecosystem: str) -> bool:
    """Whether a placed inherited unit is rendered verbatim in its destination.

    Prose is. The shell owns every heading and badge row, the plan owns every example, and the
    renderer owns the diagram, so a preserved heading, badge row, ecosystem code block, or
    Mermaid block would only duplicate what those already render; any other code block (a
    command sequence, say) carries content nothing else renders and appears as written.
    """
    unit_type = unit_id.rsplit(".", 1)[-1]
    if unit_type != "code_block":
        return unit_type not in _RENDERED_ELSEWHERE
    first = value.splitlines()[0].strip() if value.strip() else ""
    language = first[3:].strip().lower() if first.startswith("```") else ""
    return language not in {ecosystem, "mermaid"}


def planned_fact_ids(plan: dict[str, Any], section: str) -> frozenset[str]:
    """The fact and unit IDs the plan's own content for ``section`` rests on."""
    ids: set[str] = set()
    if section == "key_capabilities":
        for item in plan.get("core_capabilities", []):
            ids.update(item.get("fact_ids", []))
    elif section == "scope_limitations":
        for item in plan.get("material_limitations", []):
            ids.update(item.get("fact_ids", []))
            ids.update(item.get("unit_ids", []))
    elif section == "api_reference":
        for hub in plan.get("api_hubs", []):
            ids.add(str(hub.get("symbol_fact_id", "")))
            ids.update(hub.get("fact_ids", []))
    elif section == "quick_start":
        ids.add(str(plan.get("quick_start_example_id") or ""))
    elif section == "additional_examples":
        ids.update(plan.get("additional_example_ids", []))
    elif section == "at_a_glance":
        glance = plan.get("at_a_glance") or {}
        ids.update(glance.get("input_format_ids", []))
        ids.update(glance.get("output_format_ids", []))
    for link in plan.get("links", []):
        if link.get("section_id") == section:
            ids.add(str(link.get("link_fact_id", "")))
    return frozenset(i for i in ids if i)


_RENDERER_OWNED_ASSETS = ("build_test_asset:tests", "build_test_asset:ci")


def renderer_fact_ids(section: str, facts: FactsDocument) -> frozenset[str]:
    """The facts a mixed section's own deterministic sentences rest on: Development and
    Testing states the suite size and links the release workflow from the build assets."""
    if section != "development_testing":
        return frozenset()
    return frozenset(
        fact.id
        for fact in facts.by_kind("build_test_asset")
        if fact.id in _RENDERER_OWNED_ASSETS and fact.polarity == "SUPPORTED"
    )


def placements(
    plan: dict[str, Any], dispositions: dict[str, Any], facts: FactsDocument, ecosystem: str
) -> list[Placement]:
    """Every preserved or moved unit with the outcome the three rules give it."""
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    result: list[Placement] = []
    for entry in dispositions.get("dispositions", []):
        unit_id = str(entry.get("unit_id", ""))
        destination = entry.get("destination_section")
        if entry.get("disposition") not in PLACED or not destination:
            continue
        unit = by_id.get(unit_id)
        if unit is None:
            continue
        if not renders_verbatim(unit_id, unit.value, ecosystem):
            result.append(Placement(unit_id, destination, unit.value, "owned_elsewhere"))
            continue
        if destination not in included:
            result.append(Placement(unit_id, destination, unit.value, "excluded"))
            continue
        covered = planned_fact_ids(plan, destination) | renderer_fact_ids(destination, facts)
        overlap = (
            ()
            if unit_id.endswith(".code_block")  # a command block is content nothing else renders
            else tuple(sorted(set(entry.get("fact_ids") or []) & covered))
        )
        outcome: Outcome = "overlap" if overlap else "placed"
        result.append(Placement(unit_id, destination, unit.value, outcome, overlap))
    return result


def placed_texts(decisions: list[Placement]) -> dict[str, list[str]]:
    """The verbatim texts each section renders, in disposition order."""
    texts: dict[str, list[str]] = {}
    for placement in decisions:
        if placement.outcome == "placed":
            texts.setdefault(placement.destination, []).append(placement.text)
    return texts
