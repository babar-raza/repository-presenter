"""Placement of inherited units at render: the decision the renderer and the validator share.

docs/README_CONTRACT.md section 3 places every VERIFIED_PRESERVE and VERIFIED_MOVE unit in its
destination section under three rules, each a confirmed G1 defect. Placement is exclusive, never
additive, on fact-ID overlap: a unit whose cited facts intersect the destination's own plan-driven
content is dropped, because the planned, freshly authored content already covers that material
and passed the evidence-bound checks. An example the plan renders is covered wherever the unit
adjacent to the example's own code block was sent, not only in the unit's own destination: the
example renders exactly once, where the plan put it, so an inherited sentence introducing it
duplicates that section's own lead-in from any section (``rendered_example_ids``, G4-W17 arrival
item 65). That coverage is scoped to the one shape it was ever measured on - the citing unit sits
immediately beside the example's own code block in the source document
(``_adjacent_rendered_examples``, G4-W17 arrival item 76, lane F F17): unscoped, it dropped a
distant unit on Slides-.NET that cited a rendered example only as evidence, never as its lead-in.
A placed unit inherits its section's visibility: in a collapsible section it renders inside the
details block, never appended outside it. A placed
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

A unit that is actually placed also has its own intra-document anchors resolved here, against the
plan's own section inclusion (``planned_heading_slugs``, ``resolve_intra_document_anchors``): an
anchor to a heading this candidate will render is kept, one to a heading it will not (almost
always the old README's own heading, since a preserved ``heading`` unit never renders - it is
always ``owned_elsewhere``) is dropped to plain text (item 114, RESEARCH_AND_GUIDELINES.md section
29, lane D PROPOSAL P30). This is the only stage a preserved unit is ever rewritten at all: repair
may edit only authored units, so an anchor left unresolved here can never be fixed later.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import unquote

from repository_presenter.components.readme.composition.components.shell import SEMANTIC_SHELL
from repository_presenter.components.readme.evidence.facts.links import heading_slug
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


def rendered_example_ids(plan: Mapping[str, Any]) -> dict[str, str]:
    """Every example the plan renders, mapped to the included section that prints it.

    An example renders exactly once, where the plan puts it - ``quick_start_example_id`` and
    ``second_quick_start_example_id`` under Quick Start, ``additional_example_ids`` under
    Additional Examples - each introduced by that section's own authored lead-in
    (README_CONTRACT.md section 2 rows 10 and 12). The inherited code block behind the example is
    ``owned_elsewhere`` and never placed, so an inherited sentence introducing it duplicates that
    lead-in wherever the reconciliation sent the sentence: the plan, not the disposition's
    ``destination_section``, decides where the pair renders, and ``placements()`` reads this on
    top of the destination's own coverage. Measured 2026-09-11 (G4-W17 arrival item 65, lane C
    PROPOSAL AA): Aspose.Cells for .NET's sealed bundle sent ``inherited_unit:018.paragraph``
    ("Load a workbook with recovery diagnostics:") to Additional Examples citing ``example:002``,
    which the plan renders as the second Quick Start example; the destination-only check compared
    against ``{example:003}``, placed the sentence, and the sealed README carries it with no code
    block after it (line 155). Cells for Java met the same class at BC-10 on every draw. A section
    the plan excludes renders nothing, so its examples are not counted here.
    """
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    where: dict[str, str] = {}
    if "quick_start" in included:
        for key in ("quick_start_example_id", "second_quick_start_example_id"):
            example_id = plan.get(key)
            if example_id:
                where[str(example_id)] = "quick_start"
    if "additional_examples" in included:
        for example_id in plan.get("additional_example_ids", []):
            where.setdefault(str(example_id), "additional_examples")
    return where


_UNIT_ORDINAL = re.compile(r"^inherited_unit:(\d+)")
_EXAMPLE_UNIT = re.compile(r"unit (inherited_unit:\S+)")


def _unit_ordinal(unit_id: str) -> int | None:
    """The block-ordinal ``inherited.py`` gave this unit's source block, parsed from its own ID
    (``NNN`` in ``inherited_unit:NNN...``) - shared by every bullet a member-reference list was
    split into from the same block (RC-06), so two split bullets of one block read as the same
    position, which is correct: neither is "adjacent" to the other, both sit at the block itself.
    """
    match = _UNIT_ORDINAL.match(unit_id)
    return int(match.group(1)) if match else None


def _example_code_block_ordinals(facts: FactsDocument) -> dict[str, int]:
    """Each example fact's own code-block ordinal, read back from its own evidence.

    ``extractors/examples/verify.py`` always names the inherited unit an example candidate came
    from in its first evidence entry's detail (``"...; unit inherited_unit:NNN.code_block"``,
    the exact string ``selection.py``'s own ``unit_id=f"inherited_unit:{unit.ordinal:03d}.
    code_block"`` writes); this reads that back rather than inventing a second source for the
    same fact (G4-W17 arrival item 76, lane F F17).
    """
    ordinals: dict[str, int] = {}
    for fact in facts.by_kind("example"):
        detail = fact.evidence[0].detail if fact.evidence else None
        match = _EXAMPLE_UNIT.search(detail or "")
        if match is None:
            continue
        ordinal = _unit_ordinal(match.group(1))
        if ordinal is not None:
            ordinals[fact.id] = ordinal
    return ordinals


def _adjacent_rendered_examples(
    unit_id: str, rendered: frozenset[str], example_ordinals: Mapping[str, int]
) -> frozenset[str]:
    """The rendered example IDs whose own code block sits immediately beside ``unit_id`` in the
    source document - the one shape item 65's fix was ever measured on (Aspose.Cells for .NET's
    lead-in paragraph one ordinal before its example's own code block).

    G4-W17 arrival item 76 (lane F F17): the unscoped version covered a rendered example's fact
    ID for any preserved unit anywhere in the document, so three units on Aspose.Slides for .NET
    that cited ``example:009`` as *evidence* (a 46-part round-trip fidelity table three headings
    and 110 lines from the example's own code block) were dropped as if they were its lead-in.
    Scoping to adjacency keeps item 65's fix - a unit one ordinal from its example's block - and
    releases a distant citation, which is never a duplicate lead-in.
    """
    ordinal = _unit_ordinal(unit_id)
    if ordinal is None:
        return frozenset()
    return frozenset(
        example_id
        for example_id in rendered
        if example_id in example_ordinals and abs(example_ordinals[example_id] - ordinal) == 1
    )


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


def planned_heading_slugs(plan: Mapping[str, Any]) -> frozenset[str]:
    """The anchor slugs of every semantic-shell heading this candidate will actually render,
    known from the plan's own section inclusion alone - at S4/S5, before the document exists.

    Item 114 (RESEARCH_AND_GUIDELINES.md section 29, lane D PROPOSAL P30, PHASE1
    supervisor-admitted 2026-09-17): a preserved unit's intra-document anchor almost never names
    one of these. The heading it names was itself an inherited ``heading`` unit in the source
    document, and ``renders_verbatim`` already routes every preserved heading to
    ``owned_elsewhere`` - a preserved unit never renders a heading, only the shell does - so the
    old heading the anchor points at is never reproduced verbatim by this candidate. This set is
    deliberately the narrow, exactly-known one: it does not predict a conditional subsection
    (Core API, Required Package Dependencies, ...) that composition or the renderer may or may not
    emit later, because a false "resolved" here would carry an actually-broken anchor forward with
    no repair route (the item 114 defect itself) while a false "unresolved" only drops a link to
    its own plain text - safe, and never a broken link.
    """
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    return frozenset(
        heading_slug(section.heading)
        for section in SEMANTIC_SHELL
        if section.id in included and section.heading
    )


_INTRA_DOC_ANCHOR = re.compile(r"\[([^\]]+)\]\(#([^)\s]+)\)")


def resolve_intra_document_anchors(text: str, planned_slugs: frozenset[str]) -> str:
    """``text`` with every intra-document anchor resolved against ``planned_slugs``: kept exactly
    as written when its slug survives, dropped to its own plain link text otherwise.

    Item 114: ``targeted_repair`` is handed only a section's authored units, never a preserved
    one, so an anchor that resolves to no rendered heading could not be fixed at S9 and the repair
    round recorded ``repaired`` on byte-identical text with an immediate re-raise (measured on
    PDF-Go: ``inherited_unit:025.paragraph``, ``VERIFIED_PRESERVE``'d into ``additional_examples``,
    carried ``"[Encryption and Signing](#encryption-and-signing)"`` forward with no heading of
    that name anywhere in the candidate). Resolving here, at placement, is the only stage a
    preserved unit's own copy is ever touched at all - deterministic, no provider call, and the
    one rewrite ``renders_verbatim`` already proves is safe for this unit's shape (prose, not a
    code block the renderer or plan owns).
    """

    def resolve(match: re.Match[str]) -> str:
        label, slug = match.group(1), unquote(match.group(2)).lower()
        return match.group(0) if slug in planned_slugs else label

    return _INTRA_DOC_ANCHOR.sub(resolve, text)


def placements(
    plan: dict[str, Any], dispositions: dict[str, Any], facts: FactsDocument, ecosystem: str
) -> list[Placement]:
    """Every preserved or moved unit with the outcome the three rules give it."""
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    planned_slugs = planned_heading_slugs(plan)
    by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    # Where the plan actually renders each example - the paired code block's real destination,
    # whatever section the reconciliation named for the sentence introducing it (arrival item 65).
    rendered_examples = frozenset(rendered_example_ids(plan))
    # Each rendered example's own code-block ordinal, so coverage below can be scoped to the one
    # unit actually adjacent to it rather than any unit anywhere that cites the same ID
    # (arrival item 76).
    example_ordinals = _example_code_block_ordinals(facts)
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
        covered = (
            planned_fact_ids(plan, destination)
            | renderer_fact_ids(destination, facts, plan)
            | _adjacent_rendered_examples(unit_id, rendered_examples, example_ordinals)
        )
        overlap = (
            ()
            if unit_id.endswith(".code_block")  # a command block is content nothing else renders
            else tuple(sorted(set(entry.get("fact_ids") or []) & covered))
        )
        outcome: Outcome = "overlap" if overlap else "placed"
        text = unit.value
        # Item 114: resolved only for the text this candidate actually copies verbatim into the
        # document, never a code block - a fenced example's own bytes are content, not prose, and
        # "[...](#...)" inside one is source the unit must reproduce exactly, not a cross-reference
        # to rewrite.
        if outcome == "placed" and not unit_id.endswith(".code_block"):
            text = resolve_intra_document_anchors(text, planned_slugs)
        result.append(Placement(unit_id, destination, text, outcome, overlap))
    return result


def placed_texts(decisions: list[Placement]) -> dict[str, list[str]]:
    """The verbatim texts each section renders, in disposition order."""
    texts: dict[str, list[str]] = {}
    for placement in decisions:
        if placement.outcome == "placed":
            texts.setdefault(placement.destination, []).append(placement.text)
    return texts
