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

``api_reference``'s coverage (what counts as "the destination's own plan-driven content" for the
overlap check above) additionally includes what the renderer itself actually displays, on top of
the plan's own per-hub citations: ``api_reference_covered_fact_ids`` computes exactly what
`renderer.py`'s ``_api_reference`` shows - every verified class/enum, not only the plan's chosen
hubs - closing a real gap without discarding the plan's own signal, which several real
candidates' dispositions turned out to depend on even though it is itself only an approximation
(RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact, FactsDocument

PLACED = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
_RENDERED_ELSEWHERE = frozenset({"heading", "badge_row", "html_block"})
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

    Prose is. The shell owns every heading, badge row, and HTML structure block (a details or
    summary tag, an alignment wrapper), the plan owns every example, and the renderer owns
    the diagram, so a preserved heading, badge row, HTML block, ecosystem code block, or
    Mermaid block would only duplicate what those already render; any other code block (a
    command sequence, say) carries content nothing else renders and appears as written.

    An ecosystem's own example is judged by its fence vocabulary (section 29.2 F6), not by
    comparing the fence word to the ecosystem's name - true only for Python, where both happen
    to spell "python". Measured 2026-09-06 on Aspose.3D for .NET: a ```csharp block never equals
    the literal string "net", so every VERIFIED_PRESERVE example was placed as ordinary content
    beside the plan's own rendering of the same example, and Additional Examples printed every
    code block twice - the defect two independent reviewer reads agreed on (BC-10).
    """
    unit_type = unit_id.rsplit(".", 1)[-1]
    if unit_type != "code_block":
        return unit_type not in _RENDERED_ELSEWHERE
    first = value.splitlines()[0].strip() if value.strip() else ""
    language = first[3:].strip().lower() if first.startswith("```") else ""
    return language not in ({"mermaid"} | spec_for(ecosystem).example_fences)


def planned_fact_ids(plan: dict[str, Any], section: str) -> frozenset[str]:
    """The fact and unit IDs the plan's own content for ``section`` rests on.

    ``api_reference``'s own per-hub ``symbol_fact_id``/``fact_ids`` stay modeled here - kept, not
    replaced: a disposition frequently cites a coarse, namespace-level fact (``public_symbol:org.
    aspose.pdf``, say) rather than the individual class facts the plan's hub actually names, and
    for several real candidates that coarse citation only ever intersected the plan's own
    per-hub ``fact_ids`` (empirically confirmed - removing this branch in favor of
    ``renderer_fact_ids`` alone silently un-placed and re-included four real candidates'
    already-correctly-excluded duplicate content, caught by `test_sealed_bytes.py` before this
    landed). ``renderer_fact_ids`` (RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08)
    adds the renderer's own, more complete class/enum/hub-method coverage on top of this, via the
    union `placements()` already takes - additive, not a replacement.
    """
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
        ids.add(str(plan.get("second_quick_start_example_id") or ""))
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


def api_reference_hub_methods(
    plan: Mapping[str, Any], facts: FactsDocument
) -> dict[str, list[Fact]]:
    """Every verified method ``public_symbol`` grouped by the hub symbol's own display value it
    belongs to - the exact computation `renderer.py`'s ``_api_reference`` uses to build its
    Detailed Member Reference bullets, shared here so the renderer and this module's coverage
    model read one answer to "which methods does this hub own", not two that can drift apart
    (RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08).
    """
    methods = [
        fact
        for fact in facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED" and (fact.attributes or {}).get("symbol_kind") == "method"
    ]
    by_owner: dict[str, list[Fact]] = {}
    for fact in methods:
        by_owner.setdefault(fact.value.rsplit(".", 1)[0], []).append(fact)
    by_id = {fact.id: fact for fact in facts.facts}
    owned: dict[str, list[Fact]] = {}
    for hub in plan.get("api_hubs", []):
        symbol = by_id.get(str(hub.get("symbol_fact_id", "")))
        if symbol is not None:
            owned[symbol.value] = by_owner.get(symbol.value, [])
    return owned


def api_reference_covered_fact_ids(plan: Mapping[str, Any], facts: FactsDocument) -> frozenset[str]:
    """Every fact ID `renderer.py`'s ``_api_reference`` actually displays: every verified
    class/enum ``public_symbol`` (the Core API table always lists all of them, regardless of the
    plan's chosen hubs) plus every verified method owned by a hub (Detailed Member Reference).

    The single source of truth this module's overlap check now reads, replacing a narrower,
    independently hand-modeled approximation that only ever knew the plan's own per-hub
    ``fact_ids`` list - the exact drift that let a preserved member-reference list's overlap with
    the Core API table go undetected (RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2,
    2026-09-08).
    """
    symbols = [fact for fact in facts.by_kind("public_symbol") if fact.polarity == "SUPPORTED"]
    kinds: dict[str, list[Fact]] = {}
    for fact in symbols:
        kinds.setdefault((fact.attributes or {}).get("symbol_kind", ""), []).append(fact)
    covered = {fact.id for fact in (*kinds.get("class", []), *kinds.get("enum", []))}
    for methods in api_reference_hub_methods(plan, facts).values():
        covered.update(fact.id for fact in methods)
    return frozenset(covered)


def _documentation_resources_issues_fact_id(facts: FactsDocument) -> frozenset[str]:
    """``renderer.py``'s ``_documentation_resources`` always appends its own "Open an issue" line
    from ``identity:repository`` when it is SUPPORTED, whether or not any plan link names it - so
    a preserved unit citing only that fact for an issues/bug-report mention still duplicates a
    line the renderer, not the plan, produces (RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2,
    2026-09-08). The section's *link* coverage itself was already accurate before this taskcard -
    ``planned_fact_ids``'s own generic per-section ``plan["links"]`` loop already names exactly
    what `_documentation_resources` iterates; this fills the one small gap around it, additively.
    """
    identity = next((f for f in facts.by_kind("identity") if f.id == "identity:repository"), None)
    if identity is not None and identity.polarity == "SUPPORTED":
        return frozenset({"identity:repository"})
    return frozenset()


def renderer_fact_ids(
    section: str, facts: FactsDocument, plan: Mapping[str, Any] | None = None
) -> frozenset[str]:
    """The facts a mixed section's own deterministic content rests on: Development and Testing
    states the suite size and links the release workflow from the build assets; Documentation and
    Resources always appends its own Issues line from ``identity:repository``; API Reference's
    Core API table and Detailed Member Reference cover every verified class/enum and every
    hub-owned method (``api_reference_covered_fact_ids``, which needs ``plan`` too - additive,
    optional, so an existing caller that only asks about a plan-independent section is
    unaffected).
    """
    if section == "api_reference":
        return api_reference_covered_fact_ids(plan or {}, facts)
    if section == "documentation_resources":
        return _documentation_resources_issues_fact_id(facts)
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
        covered = planned_fact_ids(plan, destination) | renderer_fact_ids(destination, facts, plan)
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
