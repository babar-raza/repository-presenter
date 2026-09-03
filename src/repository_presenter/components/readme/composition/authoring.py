"""Stage S6: the section_authoring job wiring - one packet per LLM-owned section, one guard.

For every section the plan includes whose content the LLM owns or shares, deterministic code
assembles the closed set of facts that section may cite (the plan's own selections, the accepted
investigation's citations, and the inherited units placed there), the slots the section needs,
its objective, and its length budget, and runs the job once per section. The guard rejects a
unit before render when it cites a fact outside the section's set, when its text carries Markdown,
a URL, a command, or code, or when it names an identifier that is not a fact value. Accepted
units from every section merge into content_units.json in shell order.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.ecosystems import (
    REGISTRY_NAMES,
)
from repository_presenter.components.readme.composition.components.identity import (
    product_name,
    product_name_tokens,
)
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    section_ids,
)
from repository_presenter.core.facts import Fact, FactsDocument, bounded_records
from repository_presenter.core.registry.models import RegistryEntry

CONTENT_UNITS_FILENAME = "content_units.json"
AUTHORED_SECTIONS: tuple[str, ...] = tuple(
    section.id for section in SEMANTIC_SHELL if section.owner != "D" and section.id != "at_a_glance"
)
_DOTTED = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
_SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")
_CALL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\(\)")
_MEMBER_CAP = 60
_TYPE_BATCH = 40  # types described per authoring call: within the manifest's output budget
_TYPE_OBJECTIVE = (
    "One sentence per public type in this batch, from its verified signature (its bases) and "
    "its name: what it represents or does for a visitor. Never mechanical filler such as a "
    "member count or 'extends X', never a count, never a claim the signature does not carry."
)
_EXCEPTION_SUFFIXES = ("Error", "Exception", "Warning")
_FORBIDDEN = (
    ("```", "a code fence"),
    ("http://", "a URL"),
    ("https://", "a URL"),
    ("www.", "a URL"),
    ("](", "a Markdown link"),
    ("# ", "a Markdown heading"),
    ("* ", "a Markdown list"),
    ("- ", "a Markdown list"),
    ("|", "a Markdown table"),
    ("<", "HTML"),
    ("\n", "a line break; a unit is one paragraph"),
    ("pip install", "a command"),
    ("$ ", "a command"),
)
_OBJECTIVES: dict[str, tuple[str, str]] = {
    "opening": (
        "Two to four sentences: what the product does, the problems it solves, who uses it.",
        "one unit of two to four sentences",
    ),
    "key_capabilities": (
        "One sentence per core capability that adds concrete visitor detail beyond its title.",
        "one unit per capability, one sentence each",
    ),
    "quick_start": (
        "One lead-in sentence per minimal example the renderer shows next: the first opens an "
        "existing input when the product reads files, a second builds from scratch when the "
        "plan selected one.",
        "one unit of one sentence per example",
    ),
    "additional_examples": (
        "A short preview naming the workflows, then one meaningful task name per example.",
        "one preview unit of one or two sentences, then one unit of at most eight words per "
        "example",
    ),
    "api_reference": (
        "One or two intro sentences naming the real entry-point classes and how they relate "
        "(never a count, which the renderer states), then one evidence-backed sentence per "
        "hub API a visitor starts from.",
        "one intro unit of one or two sentences, then one unit per hub, one sentence each",
    ),
    "documentation_resources": (
        "One sentence per verified target on what it covers, in the reader's terms; never a "
        "count of types or members, which the renderer states from the facts.",
        "one unit per link, one sentence each",
    ),
    "scope_limitations": (
        "One honest scope statement, then one sentence per material limitation.",
        "one scope unit, then one unit per limitation, one sentence each",
    ),
    "development_testing": (
        "One or two sentences on how to build and test from the repository's own assets; never "
        "a file count or a release statement, which the renderer states from the facts.",
        "one unit of one or two sentences",
    ),
    "enterprise_relationship": (
        "One or two sentences relating the FOSS scope to the Enterprise Edition.",
        "one unit of one or two sentences",
    ),
}


@dataclass(frozen=True)
class SectionTask:
    """Everything one authoring call needs and everything its guard checks."""

    section_id: str
    packet: dict[str, Any]
    accepted_ids: frozenset[str]
    slots: tuple[str, ...]
    key: str = ""  # distinguishes a bounded batch task from its section's main task

    @property
    def label(self) -> str:
        return self.key or self.section_id

    @property
    def is_batch(self) -> bool:
        return bool(self.key) and self.key != self.section_id


def _cited(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        found: list[str] = []
        for key, value in payload.items():
            if key == "fact_ids" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(_cited(value))
        return found
    if isinstance(payload, list):
        return [item for element in payload for item in _cited(element)]
    return []


def _placed_units(dispositions: dict[str, Any], section: str) -> list[str]:
    return [
        entry["unit_id"]
        for entry in dispositions.get("dispositions", [])
        if entry.get("destination_section") == section
        and entry.get("disposition") in {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE"}
    ]


def section_selections(
    section: str,
    plan: dict[str, Any],
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    facts: FactsDocument,
) -> tuple[list[str], tuple[str, ...]]:
    """The fact IDs a section may cite and the slots it must fill, from the plan."""
    ids: list[str] = [fact.id for fact in facts.facts if fact.kind in {"identity", "package"}]
    slots: list[str] = []
    if section == "opening":
        for key in ("product_summary", "audience", "problems_solved"):
            ids.extend(_cited(investigation.get(key)))
        ids.extend(_cited(plan.get("core_capabilities")))
        ids.extend(fact.id for fact in facts.by_kind("format"))
        slots = ["opening"]
    elif section == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            ids.extend(item.get("fact_ids", []))
            slots.append(f"capability:{index}")
    elif section == "quick_start":
        ids.append(plan.get("quick_start_example_id", ""))
        slots = ["lead_in"]
        second = plan.get("second_quick_start_example_id")
        if second:
            ids.append(second)
            slots.append("lead_in:2")
    elif section == "additional_examples":
        additional = plan.get("additional_example_ids", [])
        ids.extend(additional)
        slots = ["preview", *(f"workflow:{example}" for example in additional)]
    elif section == "api_reference":
        slots = ["intro"]
        for hub in plan.get("api_hubs", []):
            ids.append(hub.get("symbol_fact_id", ""))
            ids.extend(hub.get("fact_ids", []))
            slots.append(f"hub:{hub.get('symbol_fact_id', '')}")
    elif section == "documentation_resources":
        for link in plan.get("links", []):
            if link.get("section_id") == section:
                ids.append(link.get("link_fact_id", ""))
                slots.append(f"link:{link.get('link_fact_id', '')}")
    elif section == "scope_limitations":
        # One bullet per limitation (README_CONTRACT.md section 2 row 16): the plan's material
        # limitations and every limitation the investigation found each get their own slot,
        # so a precise mechanism is never crammed into one bullet.
        slots = ["scope"]
        material = plan.get("material_limitations", [])
        for item in material:
            ids.extend(item.get("fact_ids", []))
            ids.extend(item.get("unit_ids", []))
        found = investigation.get("limitations") or []
        count = max(len(material), len(found) if isinstance(found, list) else 0)
        slots.extend(f"limitation:{index}" for index in range(1, count + 1))
        ids.extend(_cited(investigation.get("limitations")))
    elif section == "development_testing":
        ids.extend(fact.id for fact in facts.by_kind("build_test_asset"))
        slots = ["summary"]
    elif section == "enterprise_relationship":
        slots = ["context"]
    ids.extend(_placed_units(dispositions, section))
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    ordered = [fact_id for fact_id in dict.fromkeys(ids) if fact_id in supported]
    return ordered, tuple(slots)


def undocumented_types(facts: FactsDocument) -> list[Fact]:
    """SUPPORTED public types (classes and enums) whose source carries no docstring, in
    value order: the types whose description must be authored from their signature."""
    return sorted(
        (
            fact
            for fact in facts.by_kind("public_symbol")
            if fact.polarity == "SUPPORTED"
            and (fact.attributes or {}).get("symbol_kind") in {"class", "enum"}
            and not (fact.attributes or {}).get("docstring")
        ),
        key=lambda fact: fact.value,
    )


def _type_batches(
    entry: RegistryEntry, facts: FactsDocument, do_not_claim: list[dict[str, str]]
) -> list[SectionTask]:
    """One bounded task per batch of undocumented types (README_CONTRACT.md row 14): the
    descriptions are authored from the signature evidence, never in one oversized call."""
    types = undocumented_types(facts)
    name = product_name(entry)
    tasks: list[SectionTask] = []
    for index in range(0, len(types), _TYPE_BATCH):
        batch = types[index : index + _TYPE_BATCH]
        ids = [fact.id for fact in batch]
        slots = tuple(f"type:{fact.id}" for fact in batch)
        accepted = [
            {
                "id": fact.id,
                "kind": fact.kind,
                "value": fact.value,
                **(
                    {"signature": (fact.attributes or {})["signature"]}
                    if (fact.attributes or {}).get("signature")
                    else {}
                ),
            }
            for fact in batch
        ]
        spellings = section_spellings(ids, facts)
        packet = {
            "repository": entry.repository,
            "product_name": name,
            "mode": "author",
            "section_id": "api_reference",
            "objective": (
                f"{_TYPE_OBJECTIVE} Slots to fill, each exactly once: {', '.join(slots)}. "
                f"Identifiers the prose may spell, exactly as written: {', '.join(spellings)}; "
                "any other API name, member, attribute, or parameter is rejected."
            ),
            "accepted_facts": accepted,
            "do_not_claim": do_not_claim,
            "length_budget": "one unit per type, one sentence each",
            "rendered_document": "",
            "existing_units": [],
        }
        number = index // _TYPE_BATCH + 1
        tasks.append(
            SectionTask(
                "api_reference", packet, frozenset(ids), slots, key=f"api_reference#types-{number}"
            )
        )
    return tasks


def authoring_tasks(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    plan: dict[str, Any],
) -> list[SectionTask]:
    """One task per included section the LLM authors, in shell order."""
    included = {item["section_id"] for item in plan.get("sections", []) if item.get("include")}
    name = product_name(entry)
    by_id = {fact.id: fact for fact in facts.facts}
    do_not_claim = bounded_records(
        facts,
        ["format", "install_command", "link_target", "example"],
        ("CONTRADICTED", "UNRESOLVED"),
    )
    tasks: list[SectionTask] = []
    for section in AUTHORED_SECTIONS:
        if section not in included:
            continue
        ids, slots = section_selections(section, plan, investigation, dispositions, facts)
        objective, budget = _OBJECTIVES[section]
        accepted = [
            {"id": fact_id, "kind": by_id[fact_id].kind, "value": by_id[fact_id].value}
            for fact_id in ids
        ]
        spellings = section_spellings(ids, facts)
        packet = {
            "repository": entry.repository,
            "product_name": name,
            "mode": "author",
            "section_id": section,
            "objective": (
                f"{objective} Slots to fill, each exactly once: {', '.join(slots)}. "
                f"Identifiers the prose may spell, exactly as written: {', '.join(spellings)}; "
                "any other API name, member, attribute, or parameter is rejected."
            ),
            "accepted_facts": accepted,
            "do_not_claim": do_not_claim,
            "length_budget": budget,
            "rendered_document": "",
            "existing_units": [],
        }
        tasks.append(SectionTask(section, packet, frozenset(ids), slots))
        if section == "api_reference":
            tasks.extend(_type_batches(entry, facts, do_not_claim))
    return tasks


def verified_members(facts: FactsDocument) -> frozenset[str]:
    """Attribute names a SUPPORTED example calls or reads, from its syntax tree; execution is
    their evidence, and a name inside a string literal never counts."""
    members: set[str] = set()
    for fact in facts.by_kind("example"):
        if fact.polarity != "SUPPORTED":
            continue
        try:
            tree = ast.parse(fact.value)
        except SyntaxError:
            continue
        members.update(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))
    return frozenset(members)


def surface_members(facts: FactsDocument) -> dict[str, frozenset[str]]:
    """Public methods per class, from the surface facts recorded as ``module.Class.method``."""
    members: dict[str, set[str]] = {}
    for fact in facts.by_kind("public_symbol"):
        detail = fact.evidence[0].detail or "" if fact.evidence else ""
        if fact.polarity != "SUPPORTED" or "; method;" not in detail:
            continue
        parts = fact.value.split(".")
        if len(parts) >= 3:
            members.setdefault(parts[-2], set()).add(parts[-1])
    return {name: frozenset(found) for name, found in members.items()}


def section_spellings(accepted_ids: list[str], facts: FactsDocument) -> list[str]:
    """The identifiers a section may spell, told to the job: its facts' symbols, the public
    methods of its classes as Class.method, then the member names verified examples use."""
    by_id = {fact.id: fact for fact in facts.facts}
    methods = surface_members(facts)
    spellings: list[str] = []
    class_methods: list[str] = []
    for fact_id in accepted_ids:
        fact = by_id.get(fact_id)
        if fact is None or fact.kind not in {"public_symbol", "import_path", "package", "format"}:
            continue
        spellings.append(fact.value)
        if fact.kind in {"public_symbol", "import_path"} and "." in fact.value:
            last = fact.value.rsplit(".", 1)[-1]
            spellings.append(last)
            class_methods.extend(f"{last}.{method}" for method in sorted(methods.get(last, ())))
    verified = sorted(verified_members(facts))
    listed = list(dict.fromkeys(spellings)) + list(dict.fromkeys(class_methods))[:_MEMBER_CAP]
    return listed + [f"member {name}" for name in verified[:_MEMBER_CAP]]


def identifier_allowed(
    token: str,
    allowed: frozenset[str],
    members: frozenset[str],
    methods: dict[str, frozenset[str]] | None = None,
) -> bool:
    """A token is allowed as a fact value, a call of one, a verified member, a public method
    (bare, or as Class.method), or Class.member for a member a verified example uses."""
    methods = methods or {}
    every_method = frozenset(name for found in methods.values() for name in found)
    bare = token[:-2] if token.endswith("()") else token
    if token in allowed or bare in allowed or bare in members or bare in every_method:
        return True
    if "." in bare:
        head, tail = bare.rsplit(".", 1)
        return head in allowed and (tail in members or tail in methods.get(head, frozenset()))
    return False


def identifier_tokens(text: str) -> set[str]:
    """Tokens the renderer would have to wrap in a code span: dotted, snake, CamelCase, calls."""
    found: set[str] = set()
    for pattern in (_DOTTED, _SNAKE, _CAMEL, _CALL):
        found.update(match.group(0) for match in pattern.finditer(text))
    # An all-capital token with digits (U3D, A3DW, 3MF) is a format acronym, spelled in prose
    # as the contract's canonical abbreviations are, never an identifier.
    return {token for token in found if not (token.isupper() and token.isalnum())}


def allowed_identifiers(facts: FactsDocument, name: str) -> frozenset[str]:
    """Identifiers the prose may spell: every SUPPORTED fact value, each dotted suffix of a
    symbol or import path (``Scene.open`` for ``aspose.threed.Scene.open``), its call form, and
    the product name's tokens. Citations stay restricted to the section's set; identifiers may
    name any fact, as the contract requires, because the renderer wraps them in code spans.
    """
    allowed: set[str] = set(product_name_tokens(name))
    allowed.update(REGISTRY_NAMES.values())  # package registries are proper nouns, not APIs
    for fact in facts.facts:
        if fact.polarity != "SUPPORTED":
            continue
        allowed.add(fact.value)
        if fact.kind == "example":
            # Executed code proves every name it uses, a standard-library stream type included.
            allowed.update(identifier_tokens(fact.value))
        if fact.kind in {"public_symbol", "import_path"}:
            spellings = [fact.value]
            attributes = fact.attributes or {}
            spellings.extend(
                path.strip()
                for key in ("defined_at", "public_paths")
                for path in attributes.get(key, "").split(",")
                if path.strip()
            )
            for spelling in spellings:
                parts = spelling.split(".")
                for start in range(len(parts)):
                    allowed.add(".".join(parts[start:]))
                allowed.add(parts[-1] + "()")
                allowed.add(spelling + "()")
    return frozenset(allowed)


def merge_repeated_slots(output: dict[str, Any]) -> list[str]:
    """Fold units that repeat one slot into a single unit, in place: the plan allots each slot
    once, and a job that split its prose across several units of the same slot wrote one unit's
    worth of content in pieces. Texts join in order; citations keep their first appearance.
    Returns the slots that were folded."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    folded: list[str] = []
    for unit in output.get("units", []):
        key = (str(unit.get("section", "")), str(unit.get("slot", "")))
        first = merged.get(key)
        if first is None:
            merged[key] = unit
            continue
        first["text"] = f"{first.get('text', '')} {unit.get('text', '')}".strip()
        first["fact_ids"] = list(
            dict.fromkeys([*first.get("fact_ids", []), *unit.get("fact_ids", [])])
        )
        if key[1] not in folded:
            folded.append(key[1])
    output["units"] = list(merged.values())
    return folded


def unit_checks(
    output: dict[str, Any], task: SectionTask, facts: FactsDocument, name: str
) -> list[str]:
    """Why the section's units may not be used, beyond schema and binding; empty when they hold."""
    errors: list[str] = []
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    merge_repeated_slots(output)
    slots_seen = [unit.get("slot") for unit in output.get("units", [])]
    expected = list(task.slots)
    if sorted(slots_seen) != sorted(expected):
        errors.append(
            f"units must fill exactly these slots once each: {', '.join(expected)}; "
            f"got {', '.join(str(slot) for slot in slots_seen)}"
        )
    # An exception class name is written only when a fact this section may cite records it
    # verbatim (README_CONTRACT.md section 2 row 16: the precise mechanism a fact records).
    recorded = " ".join(
        fact.value
        for fact in facts.facts
        if fact.id in task.accepted_ids and fact.polarity == "SUPPORTED"
    )
    for unit in output.get("units", []):
        slot = unit.get("slot", "?")
        if unit.get("section") != task.section_id:
            errors.append(f"unit {slot}: section must be {task.section_id}")
        text = str(unit.get("text", ""))
        if "`" in text and "```" not in text:
            # The renderer owns every code span: a span the job wrote is dropped in place and
            # the identifier it wrapped is judged like any other token.
            text = text.replace("`", "")
            unit["text"] = text
        for marker, meaning in _FORBIDDEN:
            if marker in text:
                errors.append(f"unit {slot}: text contains {meaning} ({marker.strip()!r})")
                break
        strays = sorted(
            token
            for token in identifier_tokens(text)
            if not identifier_allowed(token, allowed, members, methods)
            and not (token.endswith(_EXCEPTION_SUFFIXES) and token in recorded)
        )
        if strays:
            errors.append(
                f"unit {slot}: identifiers that are not accepted fact values: {', '.join(strays)}"
            )
        outside = sorted(set(unit.get("fact_ids", [])) - task.accepted_ids)
        if outside:
            errors.append(
                f"unit {slot}: cites facts outside this section's set: {', '.join(outside)}"
            )
    return errors


def merge_units(
    outputs: list[tuple[str, dict[str, Any]]] | dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Every accepted task output merged in shell order into one document; a section's batch
    outputs follow its main output in task order. A mapping keyed by section is one output
    per section."""
    pairs = list(outputs.items()) if isinstance(outputs, dict) else list(outputs)
    order = {section: index for index, section in enumerate(section_ids())}
    units: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for section, output in sorted(pairs, key=lambda pair: order.get(pair[0], len(order))):
        units.extend(output.get("units", []))
        omitted.extend({"section": section, **item} for item in output.get("omitted", []))
    return {"schema_version": 1, "units": units, "omitted": omitted}


def write_content_units(document: dict[str, Any], path: Path) -> str:
    data = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
