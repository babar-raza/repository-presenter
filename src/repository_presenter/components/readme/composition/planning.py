"""Stage S5: the presentation_planning job wiring - packet, deterministic guard, and plan.json.

Deterministic code evaluates every shell condition it can from the facts (a verified input
format, dependencies, further verified examples, verified links, build assets, a notices file,
an Enterprise Edition target in policy) and tells the job the result; the job decides only what
a fixed rule cannot: which capabilities are core, which example is minimal, which APIs are hubs,
which limitations are material, which links help which section, and whether the API reference
is useful. The guard then checks every selection against the facts and the policy ceilings
before the plan is used.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import title_terms
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    Section,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.placement import placements
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
    policy_packet,
)
from repository_presenter.components.readme.evidence.facts.links import extract_links
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
from repository_presenter.core.facts import (
    FACT_KINDS,
    POLARITIES,
    FactsDocument,
    bounded_records,
)
from repository_presenter.core.llm.binding import collect_ids
from repository_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

PLAN_FILENAME = "plan.json"
_ASPOSE_DOMAINS = ("aspose.com", "aspose.org")
# Rendered deterministically at their own fixed place (README_CONTRACT.md rows 3 and 18); never
# a plan's own link assignment.
_SHELL_OWNED_LINKS = frozenset({BANNER_FACT_ID, HOMEPAGE_FACT_ID, ENTERPRISE_FACT_ID})


def _supported(facts: FactsDocument, kind: str) -> list[str]:
    return [fact.id for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def _simple_symbol_name(value: str) -> str:
    return value.rsplit(".", 1)[-1].lower().replace("_", "")


def _mis_hubbed_symbol_ids(facts: FactsDocument) -> frozenset[str]:
    """SUPPORTED public_symbol IDs that are module/package-kind but have an available,
    same-named class/enum sibling one path segment deeper (a module fact `mapi_message` when the
    sibling class fact `MapiMessage` also exists) - the real, narrow defect shape, not every
    module-kind symbol: many (a crate's own top-level module, `cfb`/`msg` on the real
    aspose-email-foss/Aspose.Email-FOSS-for-Python candidate) are genuinely whole-module concepts
    with no better substitute, and flagging those too made every attempt at picking a hub for
    them unsatisfiable - caught live, 2026-09-10, docs/DECISION_LOG.md."""
    supported = [f for f in facts.by_kind("public_symbol") if f.polarity == "SUPPORTED"]
    class_enum_names = {
        _simple_symbol_name(f.value)
        for f in supported
        if (f.attributes or {}).get("symbol_kind") in ("class", "enum")
    }
    return frozenset(
        f.id
        for f in supported
        if (f.attributes or {}).get("symbol_kind") not in ("class", "enum")
        and _simple_symbol_name(f.value) in class_enum_names
    )


def section_conditions(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> dict[str, bool | None]:
    """Whether each section's condition holds: True, False, or None when the plan decides."""
    links = [
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED" and fact.value.startswith(("http://", "https://"))
    ]
    evaluated: dict[str, bool | None] = {
        "banner": banner_target(facts.facts) is not None,  # README_CONTRACT.md row 3
        # README_CONTRACT.md row 6: a valid plan carries at least three verified core
        # capabilities (the policy minimum), so the diagram always appears; Starting Points
        # follow the verified input formats and are absent without one.
        "at_a_glance": True,
        "dependencies": bool(_supported(facts, "dependency")),
        "additional_examples": len(_supported(facts, "example")) >= 2,
        "api_reference": True,  # README_CONTRACT.md row 14: Required
        "documentation_resources": bool(links),
        "development_testing": bool(facts.by_kind("build_test_asset")),
        "enterprise_relationship": enterprise_target(facts.facts) is not None,
        "third_party_notices": bool(facts.by_kind("third_party_notices")),
    }
    return {
        section.id: True if section.required else evaluated[section.id]
        for section in SEMANTIC_SHELL
    }


# The characters a fact ID is spelled from (``<kind>:<slug>``, slugs dotted, underscored or
# hyphenated). A match must not be preceded by one, and must not continue into one - or into a
# dotted continuation - so ``example:003`` never matches inside ``example:0031`` or
# ``example:003.paragraph`` while ``example:003.`` at a sentence's end still does.
_ID_CHARS = r"A-Za-z0-9_.:\-"


def _uncitable_redaction(facts: FactsDocument) -> Callable[[str], str]:
    """Replace every uncitable fact ID in free text with its polarity and kind, never the ID.

    G4-W17 arrival item 41, measured 2026-09-07 on aspose-html-foss/Aspose.HTML-FOSS-for-Python's
    second pass (two rejected plans at temperature zero): the quick-start enum held, and the plan
    still cited the CONTRADICTED ``example:006`` in a deviation after reading it in a
    reconciliation *rationale* - "...contradicted by the example:006 CONTRADICTED fact". The
    polarity label standing right beside the ID did not stop the citation, twice, so the ID is
    not shown at all (RESEARCH_AND_GUIDELINES.md section 27.2 RC1): the planner reads
    ``[CONTRADICTED example, not citable]`` where the stored rationale names the ID. Longest ID
    first, so an uncitable ID that is a prefix of another is matched whole.
    """
    labels = {
        fact.id: f"[{fact.polarity} {fact.kind}, not citable]"
        for fact in facts.facts
        if fact.polarity != "SUPPORTED"
    }
    if not labels:
        return lambda text: text
    alternation = "|".join(re.escape(i) for i in sorted(labels, key=len, reverse=True))
    pattern = re.compile(
        rf"(?<![{_ID_CHARS}])(?:{alternation})(?![A-Za-z0-9_\-])(?!\.[A-Za-z0-9_])"
    )
    return lambda text: pattern.sub(lambda match: labels[match.group(0)], text)


def _selectable_dispositions(dispositions: dict[str, Any], facts: FactsDocument) -> dict[str, Any]:
    """The dispositions as the planner may act on them: only the fact IDs a plan may cite.

    A disposition legitimately cites a CONTRADICTED or UNRESOLVED fact - that is why it omits or
    defers its unit - while the plan's own binding admits SUPPORTED facts only. Showing the
    planner an ID its reply may not carry is cause RC1 in docs/RESEARCH_AND_GUIDELINES.md
    section 27.2: the canary's planner copied example:008 from here and was rejected twice, and
    the transaction failed closed. The destinations and unit IDs are untouched; only the
    citations a plan may not reuse are dropped from ``fact_ids`` and redacted from the one
    free-text field, ``rationale`` (``_uncitable_redaction``; the canary's fix left that field
    alone and Aspose.HTML's planner read the ID there instead). The stored dispositions are
    untouched, and plan_checks still sees the whole document.
    """
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    redact = _uncitable_redaction(facts)
    entries = []
    for entry in dispositions.get("dispositions", []):
        shown: dict[str, Any] = {}
        for key, value in entry.items():
            if key == "fact_ids":
                shown[key] = [i for i in value if i in supported]
            elif key == "rationale" and isinstance(value, str):
                shown[key] = redact(value)
            else:
                shown[key] = value
        entries.append(shown)
    return {**dispositions, "dispositions": entries}


_FORMAT_DIRECTIONS = ("input", "output")


def _verified_formats(facts: FactsDocument) -> dict[str, list[dict[str, str]]]:
    """The SUPPORTED format facts by direction as ``{id, value}`` records.

    One function feeds both the packet's ``formats`` field and ``at_a_glance``'s enums in
    ``planning_schema``, so what the planner is shown and what a valid plan may carry cannot
    drift apart (the treatment S4's ``fact_ids`` enum already has). Direction is the ID's own
    ``format:input.`` / ``format:output.`` prefix, the reading ``plan_checks`` uses.
    """
    by_direction: dict[str, list[dict[str, str]]] = {d: [] for d in _FORMAT_DIRECTIONS}
    for record in sorted(bounded_records(facts, {"format"}), key=lambda r: r["id"]):
        for direction in _FORMAT_DIRECTIONS:
            if record["id"].startswith(f"format:{direction}."):
                by_direction[direction].append({"id": record["id"], "value": record["value"]})
    return by_direction


def _examples_summary(facts: FactsDocument) -> dict[str, Any]:
    """Which examples a plan may select, and how many were withheld and why - as counts.

    Before this the packet said which examples exist only by listing the SUPPORTED ones, so a
    numbering gap was the only trace of a failed example. Polarity now travels explicitly, but
    an uncitable ID is never shown (section 27.2 RC1) - a count carries the fact without the
    handle. ``verified_ids`` is the same bounded list the schema's example enums are built from.
    """
    withheld = {polarity: 0 for polarity in POLARITIES if polarity != "SUPPORTED"}
    for fact in facts.by_kind("example"):
        if fact.polarity != "SUPPORTED":
            withheld[fact.polarity] += 1
    return {
        "verified_ids": sorted(record["id"] for record in bounded_records(facts, {"example"})),
        "withheld": withheld,
    }


def planning_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    manifest: PromptManifest,
    policy: PlanningPolicy = DEFAULT_POLICY,
) -> dict[str, Any]:
    """The planner's bounded view: SUPPORTED facts, the dispositions as it may act on them, the
    shell with its composed decisions, the policy ceilings - and, explicitly, which examples
    it may select with what was withheld (``examples``) and which formats a title or At a Glance
    may name (``formats``; G4-W17 arrival items 41 and 42). A packet field the template never
    renders is invisible to the job, so both are named in the manifest's user template."""
    conditions = section_conditions(facts, policy)
    shell = [
        {**section, "condition_holds": conditions[section["id"]]} for section in shell_packet()
    ]
    kinds = manifest.packet.fact_kinds or FACT_KINDS
    return {
        "repository": entry.repository,
        "facts": bounded_records(facts, kinds),
        "examples": _examples_summary(facts),
        "formats": _verified_formats(facts),
        "investigation": investigation,
        "dispositions": _selectable_dispositions(dispositions, facts),
        "shell": shell,
        "policy": policy_packet(policy),
    }


def _decision(section: Section, holds: bool | None) -> dict[str, Any]:
    """One inclusion decision, composed by code from the shell and the evaluated condition."""
    if section.required:
        return {"section_id": section.id, "include": True, "reason": "the shell requires it"}
    return {
        "section_id": section.id,
        "include": bool(holds),
        "reason": "its condition " + ("holds" if holds else "does not hold"),
    }


# The fact-ID arrays a plan writes, as (plan property, item property) paths into the schema.
_FACT_ID_ARRAYS = (
    ("core_capabilities", "fact_ids"),
    ("core_capabilities", "shared_fact_ids"),
    ("api_hubs", "fact_ids"),
    ("material_limitations", "fact_ids"),
    ("deviations", "fact_ids"),
)


def citable_fact_ids(
    facts: FactsDocument,
    investigation: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    manifest: PromptManifest,
) -> list[str]:
    """Every fact ID a plan may write, sorted: the packet's own ``facts`` records, the example
    and format IDs it lists, the fact IDs its shown dispositions carry, and the SUPPORTED IDs
    the accepted investigation cites - each an ID the planner can see in its packet, none it
    cannot (RESEARCH_AND_GUIDELINES.md section 27.2 RC1; the plan's binding admits SUPPORTED
    facts only). S4's ``reconciliation_schema`` already has this shape
    (``dispositions.citable_fact_ids``); this is the same enum one stage later.

    G4-W17 arrival item 59 (lane F PROPOSAL F10): the four ``fact_ids`` arrays and
    ``shared_fact_ids`` were typed ``{"type": "string"}`` with no enum, so a planner facing a
    repository with zero ``format`` facts wrote ``format:msg``, ``format:eml``, ``format:cfb`` -
    well-formed IDs naming no fact, rejected by the binding only after the call was spent: one
    wasted S5 attempt on Aspose.3D for .NET, the whole run on Aspose.Email for .NET (the retry
    budget is two). A kind-prefix pattern would have admitted them (``format`` is a real kind);
    only the packet's own IDs refuse them. Replayed 2026-09-11 over the nine sealed bundles:
    every accepted plan's citations lie inside this set, and Aspose.Slides for Python's
    ``public_symbol:slides_foss.charts.axis.title`` only through the investigation pool, which
    is why that pool is here.
    """
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    kinds = manifest.packet.fact_kinds or FACT_KINDS
    shown = {record["id"] for record in bounded_records(facts, kinds)}
    shown.update(_examples_summary(facts)["verified_ids"])
    shown.update(r["id"] for records in _verified_formats(facts).values() for r in records)
    shown.update(
        fact_id
        for entry in _selectable_dispositions(dict(dispositions), facts)["dispositions"]
        for fact_id in entry.get("fact_ids", [])
    )
    cited = {fact_id for fact_id in collect_ids(investigation).fact_ids if fact_id in supported}
    return sorted(shown | cited)


def _pin_fact_id_arrays(schema: dict[str, Any], citable: list[str]) -> None:
    """Pin every fact-ID array a plan writes to ``citable``: one ``$defs`` enum referenced from
    each array, never a copy per array. The set is the packet's own size - 2,217 IDs and 98 KB
    on Aspose.Cells for Rust, 1,816 and 96 KB on Aspose.Slides for Python (measured 2026-09-11
    over the sealed bundles) - so five copies would multiply the call schema, which is rendered
    into the prompt as well as sent as ``response_format``, fivefold; ``$defs``/``$ref`` is the
    shape ``repository_investigation``'s own schema already decodes through. ``maxItems`` is the
    set's size, the bound a duplicate-free citation list cannot exceed. With nothing citable an
    array is pinned empty, as S4 does."""
    if citable:
        schema.setdefault("$defs", {})["citable_fact_id"] = {"type": "string", "enum": citable}
    for property_name, field in _FACT_ID_ARRAYS:
        items = schema["properties"].get(property_name, {}).get("items", {})
        item_properties = items.get("properties", {})
        if field not in item_properties:
            continue
        if citable:
            item_properties[field]["items"] = {"$ref": "#/$defs/citable_fact_id"}
            item_properties[field]["maxItems"] = len(citable)
        else:
            item_properties[field] = {"type": "array", "maxItems": 0}


def planning_schema(
    manifest: LoadedManifest,
    facts: FactsDocument,
    investigation: Mapping[str, Any],
    dispositions: Mapping[str, Any],
) -> dict[str, Any]:
    """The planning schema specialised for this repository: the example selections carry the
    verified example IDs as an enum, so a schema-valid plan cannot name a contradicted or
    unresolved example (RESEARCH_AND_GUIDELINES.md section 27.5 D1; the canary was rejected
    twice for naming a CONTRADICTED example, which is cause RC1 in section 27.2).

    A link's target carries the same treatment, excluding the three IDs the shell renders at
    its own fixed place. Measured 2026-09-06 on Aspose.Email for .NET: the prompt's own
    instruction not to assign `product.enterprise` as a link was not enough - the model made the
    identical choice on three independent attempts across two composition runs, at temperature
    zero. A rejection message asks the model to notice its own mistake; an enum makes the mistake
    impossible to write in the first place, which is the same reason a contradicted example was
    never left to a rejection message either.

    An api_hub's own symbol carries the same treatment for the identical reason, excluding a
    module/package symbol only when an available, same-named class/enum sibling exists
    (`_mis_hubbed_symbol_ids`) - live-validated 2026-09-10 on the real, currently-sealed
    aspose-email-foss/Aspose.Email-FOSS-for-Python candidate: a `plan_checks` rejection message
    alone was not enough here either - the model named the same module fact twice in a row across
    two attempts at the identical, unmodified planning packet.

    ``at_a_glance``'s format ID lists carry the verified format IDs by direction as enums for
    the same reason (G4-W17 arrival item 42: aspose-note-foss/Aspose.Note-FOSS-for-Python's first
    attempt wrote a ``public_symbol`` into ``output_format_ids``); with no verified format in a
    direction the list is pinned empty (``maxItems`` 0) rather than given an empty enum, which
    no value could satisfy while the plan must still carry the key.

    Every fact-ID array a plan writes (``core_capabilities``' ``fact_ids`` and
    ``shared_fact_ids``, and the ``fact_ids`` of ``api_hubs``, ``material_limitations`` and
    ``deviations``) is pinned to ``citable_fact_ids`` - the IDs this packet shows - through one
    ``$defs`` enum (``_pin_fact_id_arrays``; G4-W17 arrival item 59), so an ID naming no fact is
    refused at decode rather than by the binding after the call is spent.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    # H: every enum below names the fact IDs a plan may choose, so it must never grow larger
    # than the packet the model actually sees - bounded_records() is that same bound
    # (planning_packet's own "facts" field, above). Built directly from facts.by_kind() instead,
    # symbol_fact_id's enum grew unbounded with the repository's own symbol count: confirmed on
    # aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (24,830 symbols, ~460,256 estimated enum tokens,
    # a real HTTP 400) since c575035 first added this field's exclusion logic without a cap.
    verified = sorted(record["id"] for record in bounded_records(facts, {"example"}))
    properties = schema["properties"]
    deviations = properties.get("deviations", {}).get("items", {}).get("properties", {})
    if "section_id" in deviations:
        # The canary's planner named a deviation against 'links', which is not a shell section.
        deviations["section_id"] = {"type": "string", "enum": list(section_ids())}
    link_properties = properties.get("links", {}).get("items", {}).get("properties", {})
    if "link_fact_id" in link_properties:
        assignable = sorted(
            record["id"]
            for record in bounded_records(facts, {"link_target"})
            if record["id"] not in _SHELL_OWNED_LINKS
        )
        link_properties["link_fact_id"] = {"type": "string", "enum": assignable}
    hub_properties = properties.get("api_hubs", {}).get("items", {}).get("properties", {})
    if "symbol_fact_id" in hub_properties:
        mis_hubbed = _mis_hubbed_symbol_ids(facts)
        visible_symbol_ids = {record["id"] for record in bounded_records(facts, {"public_symbol"})}
        hubbable = sorted(visible_symbol_ids - mis_hubbed)
        hub_properties["symbol_fact_id"] = {"type": "string", "enum": hubbable}
    formats = _verified_formats(facts)
    for variant in properties.get("at_a_glance", {}).get("oneOf", []):
        if variant.get("type") != "object":
            continue
        glance_properties = variant.get("properties", {})
        for direction, records in formats.items():
            field = f"{direction}_format_ids"
            if field not in glance_properties:
                continue
            format_ids = [record["id"] for record in records]
            glance_properties[field] = (
                {"type": "array", "items": {"type": "string", "enum": format_ids}}
                if format_ids
                else {"type": "array", "maxItems": 0}
            )
    _pin_fact_id_arrays(
        schema, citable_fact_ids(facts, investigation, dispositions, manifest.manifest)
    )
    if not verified:
        return schema
    properties["quick_start_example_id"]["enum"] = verified
    properties["additional_example_ids"]["items"]["enum"] = verified
    for field in ("second_quick_start_example_id", "flagship_example_id"):
        properties[field]["enum"] = [*verified, None]
    return schema


def _capability_facts_apart(capabilities: list[dict[str, Any]]) -> list[str]:
    """Why two capabilities may not rest on the same facts, with the bookkeeping composed here.

    Overlapping fact sets are why a subset check cannot separate one capability's prose from
    another's even in principle (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC2). What matters
    is that the rest of each set still discriminates (section 27.5 D2) - and *which* facts are
    shared is derivable from the citations themselves, so it is composed rather than asked for.
    Asking the model to restate a decision and then rejecting it for restating it wrongly is
    RC1, the same reason the shell's inclusion decisions are composed below.

    Measured 2026-09-06: `shared_fact_ids` unstated by one of the citing capabilities rejected
    `presentation_planning` twice on Aspose.3D, Cells, Email and Words for .NET - four of the six
    - each naming a fact the model had already declared shared everywhere else.

    The rule has always offered two equal arms - give each capability its own facts, *or* declare
    the sharing - so declaring was always sufficient and distinctness was never demanded. The
    fold supplies the declaration and always supplies it correctly; nothing the rule enforced is
    lost. Requiring a discriminating fact as well was tried the same day and rejected the first
    .NET candidate on three capabilities at once, which is a bar the rule never set.
    """
    errors: list[str] = []
    holders: dict[str, set[int]] = {}
    for index, item in enumerate(capabilities, start=1):
        cited = set(item.get("fact_ids", []))
        stray = sorted(set(item.get("shared_fact_ids") or []) - cited)
        if stray:
            errors.append(
                f"capability {index} declares shared facts it does not cite: {', '.join(stray)}; "
                "shared_fact_ids is a subset of that capability's fact_ids"
            )
        for fact_id in cited:
            holders.setdefault(fact_id, set()).add(index)
    shared = {fact_id for fact_id, holding in holders.items() if len(holding) > 1}
    for item in capabilities:
        cited = set(item.get("fact_ids", []))
        declared = sorted(cited & shared)
        # Composed only where there is something to compose or something to correct: a plan whose
        # capabilities share nothing keeps the shape the model wrote.
        if declared or item.get("shared_fact_ids"):
            item["shared_fact_ids"] = declared
    return errors


# RC-01, RESEARCH_AND_GUIDELINES.md 27.2 RC1/SW1, 2026-09-08: a free-form plan field that must
# contain everything a deterministic source (facts, dispositions) says it must was fixed twice as
# two separately-written, bespoke backstops (additional_example_ids, then links, landed 29ebb7c)
# - the next instance of this same shape was going to be a third bespoke diff discovered by
# incident, not a table row. Each entry pairs what a field is missing with how to append it; the
# two functions still own their own field's logic (they differ too much - one field's shape is a
# list of bare IDs excluded by quick-start membership, the other a list of {link_fact_id,
# section_id} objects gated on VERIFIED_REWRITE dispositions - to force a single computation), but
# adding a class like these is now one new tuple row plus two small functions, never a new call
# site or a new place `plan_checks` itself has to know about.
_BackstopRequired = Callable[[dict[str, Any], FactsDocument, "dict[str, Any] | None"], list[Any]]
_BackstopApply = Callable[[dict[str, Any], list[Any]], None]


def _missing_additional_examples(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[str]:
    verified_examples = sorted(
        fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"
    )
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    additional = [i for i in output.get("additional_example_ids", []) if i not in starts]
    return [i for i in verified_examples if i not in starts and i not in additional]


def _apply_additional_examples(output: dict[str, Any], missing: list[Any]) -> None:
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    additional = [i for i in output.get("additional_example_ids", []) if i not in starts]
    output["additional_example_ids"] = additional + missing


def _missing_links(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[dict[str, str]]:
    if dispositions is None:
        return []
    rewritten_link_sections: dict[str, str] = {}
    for entry in dispositions.get("dispositions", []):
        if entry.get("disposition") != "VERIFIED_REWRITE":
            continue
        destination = entry.get("destination_section")
        if not destination:
            continue
        for fact_id in entry.get("fact_ids") or []:
            fact_id = str(fact_id)
            if fact_id.startswith("link_target:") and fact_id not in _SHELL_OWNED_LINKS:
                rewritten_link_sections[fact_id] = str(destination)
    planned_link_ids = {str(link.get("link_fact_id")) for link in output.get("links", [])}
    return [
        {"link_fact_id": fact_id, "section_id": section}
        for fact_id, section in rewritten_link_sections.items()
        if fact_id not in planned_link_ids
    ]


def _apply_links(output: dict[str, Any], missing: list[Any]) -> None:
    output["links"] = [*output.get("links", []), *missing]


_BACKSTOPS: tuple[tuple[str, _BackstopRequired, _BackstopApply], ...] = (
    ("additional_example_ids", _missing_additional_examples, _apply_additional_examples),
    ("links", _missing_links, _apply_links),
)


def plan_checks(
    output: dict[str, Any],
    facts: FactsDocument,
    policy: PlanningPolicy = DEFAULT_POLICY,
    dispositions: dict[str, Any] | None = None,
    ecosystem: str = "",
) -> list[str]:
    """Why the plan may not be used, beyond schema and binding; empty when every rule holds.

    The shell's inclusion decisions are composed here, not asked for: deterministic code already
    evaluates every condition from the facts, so asking the model to restate the decision list and
    then rejecting it for restating it wrongly is RESEARCH_AND_GUIDELINES.md section 27.2's RC1
    (section 27.5 D1). Beyond that, one rule fails closed and a small, explicit table of backstops
    normalises: a placed inherited unit whose destination is excluded at this revision is never
    dropped silently (section 3), so the transaction fails closed naming the unit; and every field
    named in ``_BACKSTOPS`` (RC-01, RESEARCH_AND_GUIDELINES.md 27.2 RC1/SW1, 2026-09-08) gets
    whatever a deterministic source says it must carry appended when the plan omitted it - today,
    every further verified example belonging in Additional Examples (README_CONTRACT.md section 2
    row 12), and every link_target fact a VERIFIED_REWRITE disposition names appended to the
    plan's own links (third external review, 2026-09-07: a disposition named eight link_target
    facts for Aspose.Email Python's documentation_resources list, the plan's own links carried
    three, and review correctly rejected the other five as silently dropped verified content -
    authoring and the renderer already build every link the plan hands them; the gap was always
    here, one stage upstream of either).
    """
    errors: list[str] = []
    conditions = section_conditions(facts, policy)
    verified_examples = sorted(
        fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"
    )
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    # The facts-only condition counts every verified example; the plan's quick starts consume
    # some, so Additional Examples holds only when a further example remains.
    conditions["additional_examples"] = bool(set(verified_examples) - starts)
    for _field_name, required, apply in _BACKSTOPS:
        missing = required(output, facts, dispositions)
        if missing:
            apply(output, missing)
    output["sections"] = [_decision(section, conditions[section.id]) for section in SEMANTIC_SHELL]
    decisions = {entry["section_id"]: entry for entry in output["sections"]}
    included = {section for section, entry in decisions.items() if entry["include"]}
    # G4-W17 arrival item 32. A VERIFIED_MOVE/VERIFIED_PRESERVE unit renders its own Aspose
    # links verbatim - reconciliation's decision, not this plan's - so BC-06's ceiling on the
    # whole rendered document can be exceeded with nothing left in the plan's own links list to
    # trim; a repair re-ask of planning alone then returns a byte-identical list (measured
    # 2026-09-06, Aspose.3D for Java, only blocker). Counting them here lets the trim below
    # reserve headroom for what is already committed to render, the only lever planning has.
    preserved_aspose = 0
    if dispositions is not None:
        for placement in placements(output, dispositions, facts, ecosystem):
            if placement.outcome == "excluded":
                errors.append(
                    f"section {placement.destination} is excluded at this revision but the "
                    f"reconciliation placed {placement.unit_id} there; place the unit in an "
                    "included section or defer it, or the transaction fails closed naming it"
                )
            elif placement.outcome == "placed":
                preserved_aspose += sum(
                    1
                    for target in extract_links(placement.text)
                    if target.kind == "external"
                    and any(domain in target.href for domain in _ASPOSE_DOMAINS)
                )
    capabilities = output.get("core_capabilities", [])
    if not policy.capabilities_min <= len(capabilities) <= policy.capabilities_max:
        errors.append(
            f"core_capabilities must number {policy.capabilities_min} to "
            f"{policy.capabilities_max}; got {len(capabilities)}"
        )
    titles = [item.get("title", "").strip().lower() for item in capabilities]
    if len(set(titles)) != len(titles):
        errors.append("core_capabilities titles must be distinct")
    errors.extend(_capability_facts_apart(capabilities))
    # A capability title names only formats the facts verify. S6 judges the same titles by the
    # same rule (README_CONTRACT.md check 4), but by then the plan is fixed and the re-ask can
    # only rewrite prose, so the transaction dies: Aspose.Note titled a capability "Export pages
    # to PDF" while format:output.pdf is UNRESOLVED, and section_authoring failed twice on it
    # (measured 2026-09-06). Asked here, the model can choose another title.
    recorded = {fact.value: fact.polarity for fact in facts.by_kind("format")}
    for index, item in enumerate(capabilities, start=1):
        unverified = sorted(
            term
            for term in title_terms(str(item.get("title", "")), facts)
            if recorded.get(term, "SUPPORTED") != "SUPPORTED"
        )
        if unverified:
            errors.append(
                f"core_capabilities {index} is titled {item.get('title')!r}, which names "
                f"{', '.join(unverified)}; no fact verifies that format, so the title claims "
                "what the repository does not prove - title the capability by what is verified"
            )

    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    input_formats = {i for i in supported if i.startswith("format:input.")}
    output_formats = {i for i in supported if i.startswith("format:output.")}
    glance = output.get("at_a_glance")
    if "at_a_glance" in included:
        if glance is None:
            errors.append("at_a_glance is included, so its formats and capabilities are given")
        else:
            bad_inputs = set(glance.get("input_format_ids", [])) - input_formats
            bad_outputs = set(glance.get("output_format_ids", [])) - output_formats
            bad_titles = set(glance.get("capability_titles", [])) - {
                item.get("title", "") for item in capabilities
            }
            if bad_inputs:
                errors.append(
                    f"at_a_glance inputs are not verified input formats: {sorted(bad_inputs)}"
                )
            if bad_outputs:
                errors.append(
                    f"at_a_glance outputs are not verified output formats: {sorted(bad_outputs)}"
                )
            if bad_titles:
                errors.append(
                    f"at_a_glance capabilities are not core capabilities: {sorted(bad_titles)}"
                )
    elif glance is not None:
        errors.append("at_a_glance is omitted, so it is null")
    if glance is not None:
        titles = glance.get("capability_titles", [])
        if len(titles) < 3:
            errors.append("at_a_glance needs at least three capability titles")
        for title in titles:
            # Geometry-safe labels (README_CONTRACT.md section 2.1): a longer title is
            # shortened here at planning, never clipped at render.
            for token in title.split():
                if len(token) > 28:
                    errors.append(
                        "at_a_glance capability title carries an unbroken token over 28 "
                        f"characters: {token!r}; shorten the title"
                    )

    examples = {i for i in supported if i.startswith("example:")}
    quick = output.get("quick_start_example_id")
    if quick not in examples:
        errors.append(f"quick_start_example_id must be a SUPPORTED example; got {quick!r}")
    second = output.get("second_quick_start_example_id")
    if second is not None and (second not in examples or second == quick):
        errors.append(
            "second_quick_start_example_id must be a SUPPORTED example other than the first; "
            f"got {second!r}"
        )
    additional = output.get("additional_example_ids", [])
    if quick in additional or second in additional or len(set(additional)) != len(additional):
        errors.append("additional_example_ids must be distinct and exclude the quick start")
    if ("additional_examples" in included) != bool(additional):
        errors.append(
            "additional_example_ids are given exactly when additional_examples is included"
        )
    flagship = output.get("flagship_example_id")
    if flagship is not None and flagship not in additional:
        # README_CONTRACT.md row 12: the flagship is one further example shown visibly.
        errors.append(
            f"flagship_example_id must be one of additional_example_ids; got {flagship!r}"
        )

    # G4-W17 arrival item 16 (lane C PROPOSAL E). A repeated hub is trimmable - the first
    # occurrence already says everything a duplicate would - so it is folded here, the same way
    # dispositions.normalize folds an impossible placement, rather than failing the whole plan
    # and costing a second call for a single dropped repeat. Measured 2026-09-06 on
    # aspose-3d-foss/Aspose.3D-FOSS-for-Java (5,366 public_symbol facts): the job's own compliance
    # with a numeric ceiling was not reliable across two consecutive attempts, dying once on this
    # and once on the Aspose link ceiling below, from the same input.
    raw_hubs = output.get("api_hubs", [])
    seen_hub_ids: set[Any] = set()
    hubs = []
    for hub in raw_hubs:
        hub_id = hub.get("symbol_fact_id")
        if hub_id in seen_hub_ids:
            continue
        seen_hub_ids.add(hub_id)
        hubs.append(hub)
    if len(hubs) != len(raw_hubs):
        output["api_hubs"] = hubs
    symbols = {i for i in supported if i.startswith("public_symbol:")}
    hub_ids = [hub.get("symbol_fact_id") for hub in hubs]
    if len(hubs) > policy.api_hubs_max:
        errors.append(f"api_hubs exceed the ceiling of {policy.api_hubs_max}")
    if any(hub not in symbols for hub in hub_ids):
        errors.append("api_hubs must each be a supported public_symbol fact")
    # Defense in depth behind planning_schema's own enum (the primary defense - excludes these
    # IDs from what the model may even write): catches a hub that reaches here some other way,
    # the same layering quick_start_example_id/link_fact_id already use below and above.
    mis_hubbed = sorted(hub for hub in hub_ids if hub in _mis_hubbed_symbol_ids(facts))
    if mis_hubbed:
        errors.append(
            "api_hubs name a module/package fact with a same-named class or enum sibling "
            f"available instead: {mis_hubbed}"
        )
    if ("api_reference" in included) != bool(hubs):
        errors.append("api_hubs are given exactly when api_reference is included")

    for item in output.get("material_limitations", []):
        if not item.get("fact_ids") and not item.get("unit_ids"):
            errors.append("a material limitation cites at least one fact or inherited unit")

    link_facts = {
        fact.id: fact.value for fact in facts.by_kind("link_target") if fact.polarity == "SUPPORTED"
    }
    # An Aspose link beyond the ceiling is trimmable in the plan's own order - a plan that placed
    # five ahead of a ceiling of four still named the right four first - so it is dropped here
    # rather than failing the whole plan for a count a fixed rule already knows how to enforce.
    # A shell-owned target is never touched here: it is invalid for a different reason (it
    # renders on its own) and stays a hard error below regardless of the count.
    raw_links = output.get("links", [])
    kept_links: list[dict[str, Any]] = []
    aspose_kept = 0
    # G4-W17 arrival item 32: a preserved unit's own Aspose links already count against BC-06's
    # ceiling on the whole document, so the plan's own share is trimmed to what is left over.
    trim_ceiling = max(policy.aspose_links_max - preserved_aspose, 0)
    for link in raw_links:
        target = link.get("link_fact_id")
        value = link_facts.get(target)
        is_aspose = (
            target not in _SHELL_OWNED_LINKS
            and value is not None
            and any(domain in value for domain in _ASPOSE_DOMAINS)
        )
        if is_aspose:
            if aspose_kept >= trim_ceiling:
                continue
            aspose_kept += 1
        kept_links.append(link)
    if len(kept_links) != len(raw_links):
        output["links"] = kept_links
    aspose = 0
    targets = [link.get("link_fact_id") for link in output.get("links", [])]
    for target in sorted({t for t in targets if targets.count(t) > 1}):
        errors.append(f"link {target!r} is assigned more than once; never the same target twice")
    for link in output.get("links", []):
        target = link.get("link_fact_id")
        section = link.get("section_id")
        if target in _SHELL_OWNED_LINKS:
            # README_CONTRACT.md rows 3 and 18: the banner and the closing Enterprise sentence
            # render deterministically from these exact IDs, in their own fixed place. Placing
            # one as a link duplicates what the shell already renders and, uncounted against
            # nothing, only inflates the Aspose count: measured 2026-09-06 on Aspose.Cells for
            # .NET, whose plan assigned product.homepage to identity - a section links are never
            # assigned to at all - and reached five Aspose links against a ceiling of four with
            # only four genuinely link-worthy targets. The same URL is available under its own
            # numbered link_target fact for a section that wants to reference it directly.
            errors.append(
                f"link {target!r} renders on its own (the banner or the closing Enterprise "
                "sentence); the same URL has its own numbered link_target fact if a section "
                "needs to reference it directly"
            )
            continue
        if target not in link_facts:
            errors.append(f"link {target!r} is not a verified link target")
        elif any(domain in link_facts[target] for domain in _ASPOSE_DOMAINS):
            aspose += 1
        if section not in included:
            errors.append(
                f"link {target!r} is assigned to a section that is not included: {section!r}"
            )
    if aspose > policy.aspose_links_max:
        errors.append(f"Aspose links exceed the ceiling of {policy.aspose_links_max}: {aspose}")
    for deviation in output.get("deviations", []):
        if deviation.get("section_id") not in section_ids():
            errors.append(f"deviation names an unknown section {deviation.get('section_id')!r}")
    return errors


def summarize_plan(output: dict[str, Any]) -> str:
    included = [entry["section_id"] for entry in output.get("sections", []) if entry.get("include")]
    return (
        f"sections {len(included)}/{len(section_ids())}, "
        f"capabilities {len(output.get('core_capabilities', []))}, "
        f"hubs {len(output.get('api_hubs', []))}, "
        f"examples 1+{len(output.get('additional_example_ids', []))}, "
        f"links {len(output.get('links', []))}, "
        f"limitations {len(output.get('material_limitations', []))}"
    )


def write_plan(output: dict[str, Any], path: Path) -> str:
    """Write the accepted plan as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
