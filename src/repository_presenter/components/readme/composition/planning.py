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
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    prose_nouns,
    supporting_fact_ids,
    title_terms,
)
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    Section,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.link_budget import (
    SlotCounter,
    plan_time_budget,
    slot_violations,
)
from repository_presenter.components.readme.composition.placement import PLACED, placements
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
    policy_packet,
)
from repository_presenter.components.readme.evidence.facts.assets import CI_BADGE_FACT_ID
from repository_presenter.components.readme.evidence.facts.links import extract_links
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
from repository_presenter.components.readme.investigation.dossier import UNIT_CAP
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
_SHELL_OWNED_LINKS = frozenset(
    {BANNER_FACT_ID, HOMEPAGE_FACT_ID, ENTERPRISE_FACT_ID, CI_BADGE_FACT_ID}
)


def _supported(facts: FactsDocument, kind: str) -> list[str]:
    return [fact.id for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def _product_name(facts: FactsDocument) -> str:
    """The product's own display name, read the same way ``identity.product_name`` reads it from
    a ``RegistryEntry`` (``owner/Name-With-Dashes`` -> ``"Name With Dashes"``) - derived from
    ``facts.repository`` instead of a ``RegistryEntry`` parameter, since ``evidence/facts/
    extract.py`` always sets it to ``entry.repository`` and ``plan_checks`` has no registry
    entry of its own to take one from (G4-W17 arrival item 82)."""
    slug = facts.repository.rsplit("/", 1)[-1]
    return " ".join(part for part in slug.split("-") if part)


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
    # A relevant target is one a plan may assign: a shell-owned target renders at its own fixed
    # place and is refused as an assignment (plan_checks), so it cannot be the evidence that makes
    # documentation_resources hold (README_CONTRACT.md row 15, Conditional on verified relevant
    # targets). Aspose.GIS's three shell-owned targets made this section hold with nothing to list.
    links = [
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED"
        and fact.id not in _SHELL_OWNED_LINKS
        and fact.value.startswith(("http://", "https://"))
    ]
    evaluated: dict[str, bool | None] = {
        "banner": banner_target(facts.facts) is not None,  # README_CONTRACT.md row 3
        # README_CONTRACT.md row 6: a valid plan carries at least three verified core
        # capabilities (the policy minimum), so the diagram always appears; Starting Points
        # follow the verified input formats and are absent without one.
        "at_a_glance": True,
        "dependencies": bool(_supported(facts, "dependency")),
        # README_CONTRACT.md row 10 (G4-W17 arrival item 54): Quick Start holds when at least one
        # example executed or compiled at this revision; a repository whose every README example
        # is CONTRADICTED omits the row rather than filling it with anything unverified.
        "quick_start": bool(_supported(facts, "example")),
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


def _admitted_inherited_unit_ids(facts: FactsDocument) -> frozenset[str]:
    """The SUPPORTED ``inherited_unit`` fact IDs presentation_planning's packet may show at all,
    in document order, capped at ``UNIT_CAP`` (``investigation/dossier.py``) - the one combined
    budget both the packet's ``facts`` field (``_capped_facts``) and its sibling ``dispositions``
    field (``_selectable_dispositions``) are trimmed against.

    ``bounded_records`` already caps ``public_symbol``, ``link_target`` and ``example`` per kind
    (``core/facts.py``); ``inherited_unit`` was the one kind it left uncapped, so a repository
    with many inherited units built an S5 packet unbounded in this field regardless of section
    count (G4-W17 arrival item 120). A narrow fix scoped to ``facts`` alone would leave
    ``dispositions`` - one entry per inherited unit, no cap of its own - fully exposed to the
    identical failure (item 122); both fields are trimmed against this one set rather than each
    being capped at ``UNIT_CAP`` independently, which would double the combined budget item 122
    warns against. Measured on PDF-TypeScript (437 inherited units): the packet was 694,205
    characters and a real ``ContextWindowExceededError`` (298,865 tokens against a 262,144
    limit); ``dispositions`` alone was roughly 132,511 of those characters, about 19 percent.
    """
    ordered = bounded_records(facts, {"inherited_unit"})
    return frozenset(record["id"] for record in ordered[:UNIT_CAP])


# 2026-09-26 04:38 UTC, docs/DECISION_LOG.md: the UNIT_CAP fix above (items 120/122) genuinely
# shrank PDF-TypeScript's packet (298,865 -> 283,065 input tokens), but the repository still
# overflows the 262,144-token ceiling because ``public_symbol`` is large on a second, independent
# axis that fix never touched. ``bounded_records()``'s own ``SYMBOL_CAP`` (core/facts.py, 6000) is
# a real, working per-kind cap - proven live by
# test_the_symbol_enum_size_grows_sub_linearly_not_proportionally - but it is calibrated for
# *every* job's own packet (S3 investigation, S4 reconciliation, S6 authoring, S10 review), most
# of which carry no sibling ``inherited_unit``/``dispositions`` payload anywhere near S5's own.
# 6000 has never bound on this repository's own count (2,688, all admitted at SYMBOL_MAX_DEPTH):
# it is simply not the right number for *this* packet's own, much tighter combined budget, the
# same gap ``inherited_unit`` had before ``UNIT_CAP`` existed. ``PLANNING_SYMBOL_CAP`` is the
# analogous second, planning-specific admission - mirroring ``_admitted_inherited_unit_ids``'s own
# shape exactly - scoped to this module alone, so S3/S4/S6/S10's own use of the shared
# ``SYMBOL_CAP`` is untouched. Measured directly against this repository's own live facts
# (2,688 admitted ``public_symbol`` facts, 272,758 packet characters - the packet's second-largest
# contributor after ``inherited_unit``, and the schema's own ``citable_fact_id``/``symbol_fact_id``
# enums shrink by the same proportion): 1200, with headroom, both clears the measured overflow and
# leaves comfortable room for a modestly larger repository, without cutting so far that a
# hub-selection call is starved of real candidates the way a single-digit depth-filtered count
# would be.
PLANNING_SYMBOL_CAP = 1200


def _admitted_public_symbol_ids(facts: FactsDocument) -> frozenset[str]:
    """The SUPPORTED ``public_symbol`` fact IDs presentation_planning's packet, ``symbol_fact_id``
    enum, and ``citable_fact_id`` enum may show at all, in document order, capped at
    ``PLANNING_SYMBOL_CAP`` - the planning-specific budget above and beyond ``bounded_records()``'s
    own ``SYMBOL_CAP``, exactly the shape ``_admitted_inherited_unit_ids`` already gives
    ``inherited_unit``."""
    ordered = bounded_records(facts, {"public_symbol"})
    return frozenset(record["id"] for record in ordered[:PLANNING_SYMBOL_CAP])


def _capped_facts(facts: FactsDocument, kinds: Iterable[str]) -> list[dict[str, str]]:
    """``bounded_records(facts, kinds)``, with any ``inherited_unit``/``public_symbol`` entries
    further trimmed to ``_admitted_inherited_unit_ids``/``_admitted_public_symbol_ids`` - the two
    kinds whose own per-job cap (``UNIT_CAP``/``SYMBOL_CAP``) is not, by itself, tight enough for
    this specific packet's own combined budget (G4-W17 arrival item 120; 2026-09-26 04:38 UTC)."""
    admitted_units = _admitted_inherited_unit_ids(facts)
    admitted_symbols = _admitted_public_symbol_ids(facts)
    return [
        record
        for record in bounded_records(facts, kinds)
        if (record["kind"] != "inherited_unit" or record["id"] in admitted_units)
        and (record["kind"] != "public_symbol" or record["id"] in admitted_symbols)
    ]


def _selectable_dispositions(dispositions: dict[str, Any], facts: FactsDocument) -> dict[str, Any]:
    """The dispositions as the planner may act on them: only the fact IDs a plan may cite, and
    only entries for an inherited unit ``_admitted_inherited_unit_ids`` admits (G4-W17 arrival
    item 122 - the same combined budget ``_capped_facts`` trims the packet's ``facts`` field
    against, so a unit missing from one field is never dangled in the other).

    A disposition legitimately cites a CONTRADICTED or UNRESOLVED fact - that is why it omits or
    defers its unit - while the plan's own binding admits SUPPORTED facts only. Showing the
    planner an ID its reply may not carry is cause RC1 in docs/RESEARCH_AND_GUIDELINES.md
    section 27.2: the canary's planner copied example:008 from here and was rejected twice, and
    the transaction failed closed. The destinations and unit IDs are untouched; only the
    citations a plan may not reuse are dropped from ``fact_ids`` and redacted from the one
    free-text field, ``rationale`` (``_uncitable_redaction``; the canary's fix left that field
    alone and Aspose.HTML's planner read the ID there instead). The stored dispositions are
    untouched, and plan_checks still sees the whole document - the cap here narrows only what
    this packet shows, never what ``placements()``/``_missing_links`` act on afterward.
    """
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    admitted_units = _admitted_inherited_unit_ids(facts)
    redact = _uncitable_redaction(facts)
    entries = []
    for entry in dispositions.get("dispositions", []):
        if str(entry.get("unit_id")) not in admitted_units:
            continue
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
        "facts": _capped_facts(facts, kinds),
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
# G4-W17 arrival item 77 (lane F PROPOSAL F22, Email-.NET): ``material_limitations.unit_ids``
# sits beside ``material_limitations.fact_ids`` in the same object and holds the same shape of
# ID (an inherited_unit fact's own id, one of ``citable_fact_ids``' kinds), but item 59 enumerated
# only the ``fact_ids``-named paths - measured live, a well-formed *fact* id written into
# ``unit_ids`` cost Email-.NET a wasted S5 attempt before the binding caught it. Sharing the one
# ``citable_fact_id`` enum (rather than a second, unit-only ``$defs`` branch) keeps
# ``_pin_fact_id_arrays`` a single mechanism; the field name alone tells a reader which kind of ID
# belongs there, exactly as it already does for a human reading ``fact_ids``/``shared_fact_ids``.
_FACT_ID_ARRAYS = (
    ("core_capabilities", "fact_ids"),
    ("core_capabilities", "shared_fact_ids"),
    ("api_hubs", "fact_ids"),
    ("material_limitations", "fact_ids"),
    ("material_limitations", "unit_ids"),
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
    shown = {record["id"] for record in _capped_facts(facts, kinds)}
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
    ``shared_fact_ids``, the ``fact_ids`` of ``api_hubs``, ``material_limitations`` and
    ``deviations``, and ``material_limitations``' own ``unit_ids``) is pinned to
    ``citable_fact_ids`` - the IDs this packet shows - through one ``$defs`` enum
    (``_pin_fact_id_arrays``; G4-W17 arrival item 59, extended to ``unit_ids`` by item 77), so an
    ID naming no fact is refused at decode rather than by the binding after the call is spent.
    This also gives every one of those arrays a real ``maxItems`` (``len(citable)``) where the
    static schema had none - the four outer list counts with no citable-set bound of their own
    (``material_limitations``, ``links``, ``deviations``, ``additional_example_ids``) get an
    explicit ``maxItems`` in the manifest itself instead (G4-W17 arrival item 85: on the
    portfolio's largest S5 surface measured so far, Aspose.Words for .NET's 6638 ``public_symbol``
    facts, an unbounded array had no terminating condition under constrained decoding and the
    plan call truncated at the manifest's own token budget with no retry possible - the identical
    class item 75 already fixed for ``section_authoring``).
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
    # With nothing assignable, the list itself is pinned empty (maxItems 0) rather than given an
    # empty enum: no value satisfies an empty enum, so a strict json_schema request carrying one
    # cannot be decoded (the S5 HTTP 500/502 on Aspose.GIS, 2026-10-04). The contract's own
    # disposition follows: documentation_resources is omitted by its condition (section_conditions),
    # and the one completeness obligation a link can carry - a VERIFIED_REWRITE target - is
    # appended by the _missing_links backstop, never written by the model.
    link_properties = properties.get("links", {}).get("items", {}).get("properties", {})
    if "link_fact_id" in link_properties:
        assignable = sorted(
            record["id"]
            for record in bounded_records(facts, {"link_target"})
            if record["id"] not in _SHELL_OWNED_LINKS
        )
        if assignable:
            link_properties["link_fact_id"] = {"type": "string", "enum": assignable}
        else:
            properties["links"] = {"type": "array", "maxItems": 0}
    hub_properties = properties.get("api_hubs", {}).get("items", {}).get("properties", {})
    if "symbol_fact_id" in hub_properties:
        mis_hubbed = _mis_hubbed_symbol_ids(facts)
        # Never wider than _capped_facts's own "facts" field (H's own rule, above): a symbol this
        # packet's PLANNING_SYMBOL_CAP already excluded must never appear as a choosable hub either.
        visible_symbol_ids = _admitted_public_symbol_ids(facts)
        hubbable = sorted(visible_symbol_ids - mis_hubbed)
        if hubbable:
            hub_properties["symbol_fact_id"] = {"type": "string", "enum": hubbable}
        else:
            # The same empty-enum defect as links above: no hub can be named, so none may be.
            properties["api_hubs"] = {"type": "array", "maxItems": 0}
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
        # G4-W17 arrival item 54: with nothing verified the Quick Start row is omitted, so the
        # decoder is pinned to the only honest reply - null ids and an empty list - rather than
        # a well-formed example id that names nothing.
        properties["quick_start_example_id"] = {"type": "null"}
        properties["second_quick_start_example_id"] = {"type": "null"}
        properties["flagship_example_id"] = {"type": "null"}
        properties["additional_example_ids"] = {"type": "array", "maxItems": 0}
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


def _required_link_sections(dispositions: dict[str, Any] | None) -> dict[str, str]:
    """Every ``link_target`` fact a ``VERIFIED_REWRITE`` disposition names, mapped to its
    destination section - the plan's own completeness obligation (RC-01), regardless of whether
    the model's own free choice already carries a given target or ``_missing_links`` below still
    has to append it.

    Item 125: this full set - not just what one particular plan happens to be missing - is what
    ``plan_checks``' own Aspose-link ceiling trim needs to tell a disposition-required link apart
    from the model's own free-choice ones; both used to land in ``output['links']`` in the
    disposition's own arbitrary ``fact_ids`` order with no distinction, so a plan naming five
    required Aspose links against a ceiling of four (Slides-.NET, RESEARCH_AND_GUIDELINES.md
    section 29 item 125) silently lost whichever one sorted last, however it got into the list.
    """
    if dispositions is None:
        return {}
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
    return rewritten_link_sections


def _missing_links(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[dict[str, str]]:
    rewritten_link_sections = _required_link_sections(dispositions)
    planned_link_ids = {str(link.get("link_fact_id")) for link in output.get("links", [])}
    return [
        {"link_fact_id": fact_id, "section_id": section}
        for fact_id, section in rewritten_link_sections.items()
        if fact_id not in planned_link_ids
    ]


def _apply_links(output: dict[str, Any], missing: list[Any]) -> None:
    output["links"] = [*output.get("links", []), *missing]


def _placed_into(dispositions: dict[str, Any] | None, section: str) -> bool:
    """Whether reconciliation preserves or moves an inherited unit into ``section``."""
    if dispositions is None:
        return False
    return any(
        entry.get("disposition") in PLACED and entry.get("destination_section") == section
        for entry in dispositions.get("dispositions", [])
    )


def _documentation_resources_holds(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> bool:
    """README_CONTRACT.md row 15: the section has content only when this plan assigns it a
    SUPPORTED, non-shell link target, or reconciliation places a unit in it."""
    verified = {
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED" and fact.id not in _SHELL_OWNED_LINKS
    }
    return _placed_into(dispositions, "documentation_resources") or any(
        link.get("section_id") == "documentation_resources" and link.get("link_fact_id") in verified
        for link in output.get("links", [])
    )


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
    (section 27.5 D1). Beyond that, a small, explicit table of backstops normalises: a placed
    inherited unit whose destination this plan excludes is never dropped silently (section 3) -
    it is deferred (``DEFER_UNRESOLVED``, the same fold ``dispositions.normalize`` already applies
    to a placement into a section absent at reconciliation time), because ``additional_examples``'s
    condition just above is recomputed from this exact plan's own quick starts, which the
    reconciliation could not have known when it placed the unit: a plan that spends every verified
    example on its quick starts (Aspose.Email for C++, exactly two) excludes the destination no
    matter what the plan writes, so failing the transaction closed on it rejected the same,
    unfixable plan forever (G4-W17 arrival item 25, lane B, `BLOCKED_PLANNING`). And every field
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
    # README_CONTRACT.md row 15 (Conditional on verified relevant targets): the section holds only
    # when this plan gives it a verified target or a preserved/moved unit. The facts can hold a
    # target while the plan places every one in another section (Aspose.Font for Python,
    # 2026-10-04: links 001-007 went to identity, additional_examples and license); then
    # section_authoring had no slot to fill and cited the UNRESOLVED link_target:product.banner.
    # Recomputed from this plan's own links and placements after the backstop, exactly as
    # additional_examples is recomputed from its own quick starts above.
    conditions["documentation_resources"] = _documentation_resources_holds(
        output, facts, dispositions
    )
    output["sections"] = [_decision(section, conditions[section.id]) for section in SEMANTIC_SHELL]
    decisions = {entry["section_id"]: entry for entry in output["sections"]}
    included = {section for section, entry in decisions.items() if entry["include"]}
    # G4-W17 arrival item 32. A VERIFIED_MOVE/VERIFIED_PRESERVE unit renders its own Aspose
    # links verbatim - reconciliation's decision, not this plan's - so BC-06's ceiling on the
    # whole rendered document can be exceeded with nothing left in the plan's own links list to
    # trim; a repair re-ask of planning alone then returns a byte-identical list (measured
    # 2026-09-06, Aspose.3D for Java, only blocker). Counting them here lets the trim below
    # reserve headroom for what is already committed to render, the only lever planning has.
    preserved_hrefs: list[str] = []
    if dispositions is not None:
        by_unit_id = {
            str(entry.get("unit_id")): entry for entry in dispositions.get("dispositions", [])
        }
        for placement in placements(output, dispositions, facts, ecosystem):
            if placement.outcome == "excluded":
                # G4-W17 arrival item 25 (lane B, Email C++, BLOCKED_PLANNING): this placement
                # was valid when the reconciliation made it; only this plan's own recomputation
                # of additional_examples (from its own quick starts, above) excludes the
                # destination, so no plan can honour it and none can withdraw it either - failing
                # closed here rejected the same, unfixable plan on every re-ask. Deferred exactly
                # as dispositions.normalize folds the identical shape (a placement into a section
                # absent at reconciliation time) to DEFER_UNRESOLVED, in place, on the same
                # dispositions object the caller holds.
                entry = by_unit_id.get(placement.unit_id)
                if entry is not None:
                    entry["disposition"] = "DEFER_UNRESOLVED"
                    entry["destination_section"] = None
            elif placement.outcome == "placed":
                preserved_hrefs.extend(
                    target.href
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
    # README_CONTRACT.md check 4: a capability title is supported by the facts its own capability
    # cites. This used to judge a title's format terms against every format fact in the whole
    # document, while authoring.py's unit_checks (~1099-1118) judges the very same title against
    # only that slot's own planned fact_ids - the narrower, correct standard, which applied
    # second, after the plan was fixed and S6 could no longer retitle or add a fact. Proven
    # jointly unsatisfiable on Page-Python (G4-W17 arrival item 82, lane E E15): citing the
    # plan's set failed the title rule, adding any supporting fact failed the slot-set rule, and
    # there was no third option. Applying unit_checks' own standard here instead, while the
    # planner can still retitle or add the fact, closes the gap without relaxing either rule -
    # the same lineage as item 42's original fix (Aspose.Note titled a capability "Export pages
    # to PDF" while format:output.pdf is UNRESOLVED, and section_authoring failed twice on it,
    # measured 2026-09-06).
    name = _product_name(facts)
    nouns = prose_nouns(facts, name)
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    for index, item in enumerate(capabilities, start=1):
        title = str(item.get("title", ""))
        cited = " ".join(values.get(i, "") for i in item.get("fact_ids", [])).lower()
        unsupported = sorted(
            term
            for term in title_terms(title, facts)
            if term not in nouns
            and term.lstrip(".").lower() not in cited
            and term.lstrip(".").lower() not in common
        )
        if unsupported:
            # G4-W17 arrival item 95: name a few real candidate fact IDs per unsupported term,
            # not just what is missing - core/llm/jobs.py budgets one universal re-ask per job,
            # and a model searching hundreds of facts for a citation spends it less reliably than
            # one retitling a capability by the escape this rejection already offers.
            candidates = {term: supporting_fact_ids(term, facts) for term in unsupported}
            suggestions = "; ".join(
                f"{term!r} is carried by {', '.join(ids)}"
                if ids
                else f"{term!r} by no SUPPORTED fact"
                for term, ids in candidates.items()
            )
            errors.append(
                f"core_capabilities {index} is titled {item.get('title')!r}, which names "
                f"{', '.join(unsupported)}, which the facts it cites do not carry ({suggestions}); "
                "cite one of the named facts that supports this title, or title the capability by "
                "what it cites"
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
    # README_CONTRACT.md row 10 (G4-W17 arrival item 54): the id is given exactly when the
    # conditional Quick Start row is included, and null when its condition does not hold.
    if "quick_start" in included:
        if quick not in examples:
            errors.append(f"quick_start_example_id must be a SUPPORTED example; got {quick!r}")
    elif quick is not None:
        errors.append(f"quick_start_example_id is null when quick_start is omitted; got {quick!r}")
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
    # Item 125: every link_target a VERIFIED_REWRITE disposition names is a completeness
    # obligation _missing_links' own backstop enforces (RC-01), not a free choice the ceiling
    # trim below may judge the same way it judges the model's own optional links - both used to
    # land in output['links'] in the disposition's own arbitrary fact_ids order with no
    # distinction, which is how a plan with five required Aspose links against a ceiling of four
    # silently lost whichever one sorted last (Slides-.NET, RESEARCH_AND_GUIDELINES.md section 29
    # item 125). Computed from dispositions directly, independent of this plan's own links, so a
    # required target is recognised whether the model already carried it or the backstop above
    # had to append it.
    required_link_sections = _required_link_sections(dispositions)
    # An Aspose link beyond the ceiling is trimmable in the plan's own order - a plan that placed
    # five ahead of a ceiling of four still named the right four first - so it is dropped here
    # rather than failing the whole plan for a count a fixed rule already knows how to enforce.
    # A shell-owned target is never touched here: it is invalid for a different reason (it
    # renders on its own) and stays a hard error below regardless of the count. A disposition-
    # required target (above) is never touched here either: it is not the model's free choice to
    # trim away.
    raw_links = output.get("links", [])
    kept_links: list[dict[str, Any]] = []
    optional_hrefs: list[str] = []
    # G4-W17 arrival item 32: a preserved unit's own Aspose links already count against BC-06's
    # ceiling on the whole document, so the plan's own share is trimmed to what is left over.
    # Item 125: a disposition-required Aspose link reserves the same kind of headroom - it is
    # going to render in output['links'] itself, unlike a preserved unit's own verbatim link, but
    # it is equally outside the model's own free choice.
    # The plan stage cannot know the rendered README's size, so it trims to the largest ceilings
    # the policy admits for any document; BC-06 judges the rendered document against its own,
    # exact per-slot ceilings (link_budget.py) and names any overage with the numbers.
    budget = plan_time_budget(policy.link_allocation, policy.aspose_links_max)
    counter = SlotCounter(budget)
    for href in preserved_hrefs:
        counter.add(href)
    for target in required_link_sections:
        if (
            target not in _SHELL_OWNED_LINKS
            and link_facts.get(target) is not None
            and any(domain in link_facts[target] for domain in _ASPOSE_DOMAINS)
        ):
            counter.add(link_facts[target])
    for link in raw_links:
        target = link.get("link_fact_id")
        value = link_facts.get(target)
        is_aspose = (
            target not in _SHELL_OWNED_LINKS
            and value is not None
            and any(domain in value for domain in _ASPOSE_DOMAINS)
        )
        if is_aspose and value is not None and target not in required_link_sections:
            if not counter.would_fit(value):
                continue
            counter.add(value)
            optional_hrefs.append(value)
        kept_links.append(link)
    if len(kept_links) != len(raw_links):
        output["links"] = kept_links
    if "documentation_resources" in included and not _documentation_resources_holds(
        output, facts, dispositions
    ):
        # The ceiling trim above can remove the section's only link after its condition was
        # decided. Nothing else is placed there (the condition counts placements), so the section
        # is omitted by its own condition. The trim's own rule is to drop, never to reject the plan
        # (G4-W17 arrival item 16). The checks above that read `included` concern other sections.
        conditions["documentation_resources"] = False
        output["sections"] = [
            _decision(section, conditions[section.id]) for section in SEMANTIC_SHELL
        ]
        included = {entry["section_id"] for entry in output["sections"] if entry["include"]}
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
        if section not in included:
            errors.append(
                f"link {target!r} is assigned to a section that is not included: {section!r}"
            )
    errors.extend(f"Aspose links: {problem}" for problem in slot_violations(budget, optional_hrefs))
    for deviation in output.get("deviations", []):
        if deviation.get("section_id") not in section_ids():
            errors.append(f"deviation names an unknown section {deviation.get('section_id')!r}")
    return errors


def recover_uncited_capability_titles(
    output: dict[str, Any], facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``run_job``'s final rejected attempt only (``recover=``,
    ``core/llm/jobs.py``) - never called on a first attempt, so the model's own one universal
    re-ask is always tried first exactly as before; a capability that plan_checks would still
    reject for an unrelated reason is unaffected, since ``run_job`` re-validates the corrected
    output through the real ``plan_checks`` before ever accepting it.

    G4-W17 arrival item 111 (PGPY-04): item 95's own ``supporting_fact_ids`` hint above already
    names real, on-topic candidate facts in the rejection message, but ``core/llm/jobs.py``'s one
    universal re-ask per job cannot tell an informed rejection (a citation to add) from a blind
    one - measured on Page-Python, two independent live re-asks each retitled the capability
    instead of citing one of the three facts already named, exhausting the budget without curing
    the defect. When a still-rejected final reply's capability has at least one unsupported term
    AND every one of its unsupported terms already has a real named candidate, the fix is
    unambiguous: the first (sorted, deterministic) candidate per term is spliced into that
    capability's own ``fact_ids``. A capability with no unsupported term, or with one no
    ``SUPPORTED`` fact carries at all (the title genuinely needs a rename, not a citation, exactly
    as ``supporting_fact_ids``' own docstring says), is left untouched.

    Returns ``None`` when nothing was spliced (nothing to try), never a no-op copy of ``output``.
    """
    capabilities = output.get("core_capabilities")
    if not isinstance(capabilities, list):
        return None
    name = _product_name(facts)
    nouns = prose_nouns(facts, name)
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    changed = False
    for item in capabilities:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", ""))
        cited_ids = list(item.get("fact_ids", []))
        cited = " ".join(values.get(i, "") for i in cited_ids).lower()
        unsupported = sorted(
            term
            for term in title_terms(title, facts)
            if term not in nouns
            and term.lstrip(".").lower() not in cited
            and term.lstrip(".").lower() not in common
        )
        if not unsupported:
            continue
        candidates = [supporting_fact_ids(term, facts) for term in unsupported]
        if not all(candidates):
            continue  # at least one term has no real fact to cite; a citation cannot fix this
        item["fact_ids"] = sorted({*cited_ids, *(ids[0] for ids in candidates)})
        changed = True
    return output if changed else None


def recover_duplicate_link_assignments(output: dict[str, Any]) -> dict[str, Any] | None:
    """Last-resort correction for ``run_job``'s final rejected attempt only (``recover=``,
    ``core/llm/jobs.py``) - never called on a first attempt, so the model's own one universal
    re-ask is always tried first exactly as before. Symmetric to
    ``recover_uncited_capability_titles`` above: ``plan_checks``' rule that a link target is never
    placed twice is never weakened, and ``run_job`` re-validates the corrected output through the
    real schema, binding and ``plan_checks`` before ever accepting it.

    The only deterministic correction that keeps the plan's own meaning is to keep the FIRST
    assignment the model wrote for each target and drop every later repeat: the first placement is
    the model's first choice, and nothing is invented, re-sectioned or added. A repeat the first
    assignment cannot make valid (an excluded section, an unverified target) still fails closed.

    Measured on aspose-font-foss/Aspose.Font-FOSS-for-Python (presentation_planning, S5): the model
    assigned ``link_target:001`` to many sections; the one re-ask repeated the same output, so the
    job failed with no deterministic last resort (docs/RESEARCH_AND_GUIDELINES.md section 27.2).

    Returns ``None`` when no target repeats, never a no-op copy of ``output``.
    """
    links = output.get("links")
    if not isinstance(links, list):
        return None
    seen: set[str] = set()
    kept: list[Any] = []
    for link in links:
        target = link.get("link_fact_id") if isinstance(link, dict) else None
        if isinstance(target, str):
            if target in seen:
                continue
            seen.add(target)
        kept.append(link)
    if len(kept) == len(links):
        return None
    return {**output, "links": kept}


def recover_planning_output(output: dict[str, Any], facts: FactsDocument) -> dict[str, Any] | None:
    """The single ``recover=`` ``repair/rounds.py`` passes to presentation_planning's ``run_job``:
    both deterministic last resorts, in order, each applied only when it changes something -
    duplicate link assignments first, then uncited capability titles. ``run_job`` re-validates
    whatever this returns through the real checks, so a correction that clears only one defect
    changes nothing it did not earn.

    Returns ``None`` when neither applies.
    """
    deduplicated = recover_duplicate_link_assignments(output)
    base = output if deduplicated is None else deduplicated
    retitled = recover_uncited_capability_titles(base, facts)
    if retitled is not None:
        return retitled
    return deduplicated


def recover_visible_line_overage(
    output: dict[str, Any], *, levers: Mapping[str, int]
) -> dict[str, Any] | None:
    """Last-resort correction for a ``targeted_repair`` job's own final rejected attempt only
    (``recover=``, ``core/llm/jobs.py``) - never called on a first attempt, so the model's own one
    universal re-ask is always tried first exactly as before; a revision ``plan_checks`` or
    ``repair/rounds.py``'s own visible-line-budget rejection would still reject for an unrelated
    reason is unaffected, since ``run_job`` re-validates the corrected output through the real
    checks before ever accepting it.

    G4-W17 (docs/DECISION_LOG.md 2026-09-17 10:24 UTC, 2026-09-27 05:14 UTC): mirrors
    ``recover_title_verbatim_opening``'s own shape and discipline, for a BC-07 visible-line-budget
    repair whose final reply still leaves every named lever field set (``repair/rounds.py``'s own
    ``_reject_insufficient_visible_line_overage`` only ever rejects for exactly this reason).
    ``levers`` is ``visible_line_budget_hint``'s own
    ``optional_plan_fields_and_their_visible_line_cost_if_cleared`` - the fields this repair's own
    packet already told the model it could clear. Clearing one never deletes or invents anything:
    the same verified example stays fully present in its section's own collapsed block (or is
    simply not duplicated a second time in Quick Start) - README_CONTRACT.md rows 10 and 12 make
    both fields optional by contract. A truthful ``changes[]`` entry is recorded for each field
    actually cleared, so the ledger never again shows a self-reported no-op while the real overage
    sits uncorrected.

    Returns ``None`` when nothing was cleared (nothing to try), never a no-op copy of ``output``.
    """
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return None
    cleared: list[tuple[str, Any]] = []
    for field_name in levers:
        if revised.get(field_name) is not None:
            cleared.append((field_name, revised[field_name]))
            revised[field_name] = None
    if not cleared:
        return None
    corrected = {**output, "revised_output": revised}
    corrected["changes"] = [
        {
            "id": f"R{index:02d}",
            "path": field_name,
            "before": str(before),
            "after": "null",
            "fact_ids": [],
        }
        for index, (field_name, before) in enumerate(cleared, start=1)
    ]
    return corrected


# The lever formula (repair/targeted.py::visible_line_budget_hint) prices a cleared example at its
# own block's visible lines, but two rendering edges sit outside it: a cleared example re-homed into
# an Additional Examples section that does not exist yet opens that section (heading, lead-in,
# blank lines), and one moved into an existing details block can leave the blank line before the
# block behind. A deterministic clear is taken only when its exact saving clears the overage with
# this margin to spare; anything closer is left to the targeted repair, which re-measures the
# rendered document.
VISIBLE_LINE_RENDER_MARGIN = 4


def bound_visible_line_overage(
    output: Mapping[str, Any], *, overage: int, levers: Mapping[str, int]
) -> dict[str, Any] | None:
    """The deterministic bound on a BC-07 visible-line overage: a targeted_repair-shaped correction
    (``revised_output`` plus truthful ``changes``) that clears every named optional example lever,
    when the exact saving of those levers clears ``overage`` with ``VISIBLE_LINE_RENDER_MARGIN``
    to spare; ``None`` otherwise, so the causal stage's own repair runs as before.

    ``repair/rounds.py`` tries this before the targeted repair call. Measured on the recorded
    aspose-font-foss/Aspose.Font-FOSS-for-Python draws (docs/DECISION_LOG.md, 2026-09-17 to
    2026-09-28): overages of 5 to 77 visible lines, a flagship alone worth 127, and the model's own
    repair attempt cleared neither lever on any recorded draw, so the same overage re-raised. Code
    clears what the arithmetic proves is enough; the model is asked only when it is not.
    """
    if overage <= 0 or not levers:
        return None
    if sum(levers.values()) - VISIBLE_LINE_RENDER_MARGIN < overage:
        return None
    return recover_visible_line_overage(
        {"revised_output": copy.deepcopy(dict(output)), "changes": []}, levers=levers
    )


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
