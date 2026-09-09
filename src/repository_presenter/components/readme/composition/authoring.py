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
import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from repository_presenter.components.readme.composition.components.ecosystems import (
    REGISTRY_NAMES,
    host_names,
)
from repository_presenter.components.readme.composition.components.identity import (
    product_name,
    product_name_tokens,
)
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    section_ids,
)
from repository_presenter.components.readme.evidence.facts.links import link_text
from repository_presenter.core.facts import Fact, FactsDocument, bounded_records
from repository_presenter.core.llm.ledger import canonical_hash
from repository_presenter.core.llm.prompts import LoadedManifest
from repository_presenter.core.registry.models import RegistryEntry

CONTENT_UNITS_FILENAME = "content_units.json"
AUTHORED_SECTIONS: tuple[str, ...] = tuple(
    section.id for section in SEMANTIC_SHELL if section.owner != "D" and section.id != "at_a_glance"
)
_DOTTED = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
_SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")
_CALL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\(\)")
# A package coordinate ("org.aspose:aspose-pdf-foss") is one token, not a dotted prefix that
# happens to sit next to a colon. External audit, 2026-09-07: without this, _DOTTED alone
# matched "org.aspose" and the renderer wrapped only that, leaving ":aspose-PDF-foss" as bare
# text right after the code span - measured in PDF Java's very first paragraph, the one sealed
# candidate whose review never even reopened.
_COORDINATE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z0-9_.-]+\b")
# Where a Markdown source keeps code rather than prose: a word inside any of these is not a word
# the source wrote, so it never licenses a spelling (prose_nouns).
_NOT_PROSE = (
    re.compile(r"```.*?```", re.DOTALL),
    re.compile(r"`[^`]*`"),
    re.compile(r"\]\([^)]*\)"),
    re.compile(r"<?https?://\S+"),
    re.compile(r"<[^>]+>"),
)
# The inverse of _NOT_PROSE's own single-backtick entry: what it strips, this captures. Applied
# only after _NOT_PROSE's fence pattern has already removed ```...``` blocks, so a triple-fenced
# example's own code is never read as a code-span noun candidate.
_CODE_SPAN = re.compile(r"`([^`\n]*)`")
_MEMBER_CAP = 60
_TYPE_BATCH = 40  # types described per authoring call: within the manifest's output budget
_TYPE_OBJECTIVE = (
    "One sentence per public type in this batch, from its verified signature (its bases) and "
    "its name: what it represents or does for a visitor. Never mechanical filler such as a "
    "member count or 'extends X', never a count, never a claim the signature does not carry."
)
# The normalisation this package owns - canonical_abbreviations, which the renderer applies to
# prose, and the rewrites unit_checks makes before judging - decides rendered bytes, so it is a
# component dependencies.json records and a change to it reopens COMPOSING, exactly as the shell
# and the renderer do (the gap recorded at d147b4a; docs/STATE_MACHINE.md section 9).
NORMALISATION_VERSION = "2"
_EXCEPTION_SUFFIXES = ("Error", "Exception", "Warning")
# "the Enterprise Edition" reads as "the commercial edition"; a bare mention loses only the
# proper name the shell already carries.
_EDITION = re.compile(r"\bEnterprise Edition\b")
# The words of a capability title, extensions included, so the concrete things a title names
# can be looked for among the formats the facts record.
_TITLE_WORD = re.compile(r"[A-Za-z0-9.]+")
# Abbreviations the document always spells one way. The renderer normalises prose to these forms
# and BC-07 judges the rendered document against the same set, so the two cannot drift
# (docs/RESEARCH_AND_GUIDELINES.md section 27.10).
ABBREVIATIONS = frozenset(
    {
        "PDF",
        "XLSX",
        "HTML",
        "EPS",
        "XPS",
        "API",
        "JSON",
        "XML",
        "CSV",
        "SVG",
        "URL",
        "HTTP",
        "SDK",
        "CLI",
    }
)
# Format extensions that are also ordinary words are never judged as abbreviations.
WORD_EXTENSIONS = frozenset({"max", "ply", "dat", "raw", "bin", "log", "map", "mat", "tag", "ini"})
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
# A genuine Markdown list marker opens the paragraph; the same two characters followed by a
# space also occur mid-sentence in ordinary prose (a hyphenated compound split across a line,
# "workbook- or sheet-scoped"). Measured 2026-09-06 on Aspose.Cells for C++: that exact phrase
# rejected an otherwise-clean limitation twice. A unit is one paragraph (no "\n" above), so
# "only at line start" is exactly "only at the start of the string".
_ANCHORED_ONLY = frozenset({"- ", "* "})
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
        "One lead-in sentence per minimal example the renderer shows next, each about the "
        "example its own slot's `renders` prints directly beneath it - what that code does and "
        "why a visitor runs it first - and never about the other slot's example.",
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
        "At most one sentence on what the commercial edition adds beyond this package, only "
        "from the accepted facts (the existing README's own statements); never the words "
        "Enterprise Edition, which the renderer names exactly once; empty when no fact says.",
        "one unit of at most one sentence",
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
    # The fact set the plan assigned to each slot that has one (README_CONTRACT.md check 4): a
    # unit cites only its own slot's facts, never another slot's.
    slot_facts: Mapping[str, frozenset[str]] = field(default_factory=dict)
    # The subject the plan gave a slot - a capability's title - so the unit filling it is held to
    # describing that subject (README_CONTRACT.md check 4, section 27.5 D2).
    slot_titles: Mapping[str, str] = field(default_factory=dict)

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


def capability_titles(plan: dict[str, Any]) -> dict[str, str]:
    """The title the plan gave each capability slot: the subject that slot's unit is about."""
    return {
        f"capability:{index}": title
        for index, item in enumerate(plan.get("core_capabilities", []), start=1)
        if (title := str(item.get("title", "")).strip())
    }


def slot_records(
    slots: Sequence[str],
    slot_facts: Mapping[str, frozenset[str]],
    titles: Mapping[str, str],
    renders: Mapping[str, str] = MappingProxyType({}),
) -> list[dict[str, Any]]:
    """Each slot as the author is shown it: its id, the subject the plan gave it, the only facts
    its unit may cite, and what the deterministic renderer already prints around it. The title
    travels here and in ``SectionTask.slot_titles``, so the packet and the guard name one
    subject (docs/RESEARCH_AND_GUIDELINES.md section 27.5 D2)."""
    records: list[dict[str, Any]] = []
    for slot in slots:
        record: dict[str, Any] = {"slot": slot}
        if titles.get(slot):
            record["title"] = titles[slot]
        if slot_facts.get(slot):
            record["fact_ids"] = sorted(slot_facts[slot])
        if renders.get(slot):
            record["renders"] = renders[slot]
        records.append(record)
    return records


def slot_rendering(
    section: str,
    slots: Sequence[str],
    facts: FactsDocument,
    dispositions: dict[str, Any],
    slot_facts: Mapping[str, frozenset[str]] = MappingProxyType({}),
) -> dict[str, str]:
    """What the renderer prints around a slot's unit, verbatim, for the slots that have such a
    neighbour.

    A unit that restates its neighbour is the same defect as one that restates its title
    (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC1, D2): measured on the canary on
    2026-09-05, the three documentation units each opened by repeating the link label the
    renderer had just printed and wrote its URL as text, and the development summary wrote the
    install and test commands the renderer prints as blocks below it. Both were rejections. The
    facts are the same ones the slot already cites, so nothing new is disclosed - only where the
    renderer will put them.
    """
    by_id = {fact.id: fact for fact in facts.facts}
    rendered: dict[str, str] = {}
    if section == "documentation_resources":
        for slot in slots:
            target = by_id.get(slot.removeprefix("link:"))
            if slot.startswith("link:") and target is not None:
                rendered[slot] = (
                    f"- **[{link_text(target)}]({target.value})** - before your sentence"
                )
    elif section == "quick_start":
        # README_CONTRACT.md row 10 names two example kinds - opening an existing input, and
        # building from scratch - but which one fills which lead-in slot is the plan's choice,
        # not a fixed order. Each lead-in is shown the example ``slot_fact_sets`` bound to that
        # slot, which is the one the renderer prints directly beneath it, so the prose is about
        # that example and never its sibling (RESEARCH_AND_GUIDELINES.md section 27.9 G4-W17
        # item 29). Measured on Aspose.PDF for Go, where the packet's declared order put a
        # LoadWorkbook lead-in directly above a NewWorkbook() fence and BC-04, which checks only
        # fact-ID membership, passed it silently.
        for slot in slots:
            bound = sorted(slot_facts.get(slot, frozenset()))
            example = by_id.get(bound[0]) if bound else None
            if example is not None:
                code = " ".join(example.value.split())
                rendered[slot] = f"as a fenced code block after your sentence: {code}"
    elif section == "development_testing":
        blocks = [
            by_id[unit_id].value
            for unit_id in _placed_units(dispositions, section)
            if unit_id.endswith(".code_block") and unit_id in by_id
        ]
        if blocks and slots:
            joined = "; ".join(" ".join(block.split()) for block in blocks)
            rendered[slots[0]] = f"as fenced blocks after your sentence: {joined}"
    return rendered


def title_terms(title: str, facts: FactsDocument) -> set[str]:
    """The concrete things a capability title names: identifiers, and this repository's own
    format names. The rest of a title is ordinary prose, which no fact needs to carry."""
    terms = identifier_tokens(title)
    formats = {fact.value.lstrip(".").lower(): fact.value for fact in facts.by_kind("format")}
    for word in _TITLE_WORD.findall(title):
        recorded = formats.get(word.lstrip(".").lower())
        if recorded:
            terms.add(recorded)
    return terms


def slot_fact_sets(section: str, plan: dict[str, Any]) -> dict[str, frozenset[str]]:
    """The fact set the plan assigned to each slot of the section that has one: a capability
    its title's facts, a hub its symbol and justifying facts, a link its target, a workflow its
    example, a quick-start lead-in its example, a material limitation its facts and units."""
    bound: dict[str, frozenset[str]] = {}
    if section == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            bound[f"capability:{index}"] = frozenset(item.get("fact_ids", []))
    elif section == "quick_start":
        quick = plan.get("quick_start_example_id")
        if quick:
            bound["lead_in"] = frozenset({quick})
        second = plan.get("second_quick_start_example_id")
        if second:
            bound["lead_in:2"] = frozenset({second})
    elif section == "additional_examples":
        for example in plan.get("additional_example_ids", []):
            bound[f"workflow:{example}"] = frozenset({example})
    elif section == "api_reference":
        for hub in plan.get("api_hubs", []):
            symbol = hub.get("symbol_fact_id", "")
            bound[f"hub:{symbol}"] = frozenset({symbol, *hub.get("fact_ids", [])})
    elif section == "documentation_resources":
        for link in plan.get("links", []):
            if link.get("section_id") == section:
                target = link.get("link_fact_id", "")
                bound[f"link:{target}"] = frozenset({target})
    elif section == "scope_limitations":
        for index, item in enumerate(plan.get("material_limitations", []), start=1):
            bound[f"limitation:{index}"] = frozenset(
                [*item.get("fact_ids", []), *item.get("unit_ids", [])]
            )
    return bound


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
            "slots": slot_records(slots, {}, {}),
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


def authoring_schema(manifest: LoadedManifest, task: SectionTask) -> dict[str, Any]:
    """The authoring schema specialised for one task: its section and exactly its slots.

    The code knows which section this call writes and which slots it must fill, so it says so
    rather than asking the model to restate it and rejecting it for restating it wrongly
    (RESEARCH_AND_GUIDELINES.md section 27.5 D1; cause RC1 in 27.2). The canary's rejected
    replies show the shape this ends: seven slots required, six returned. Citations stay with
    the binding and unit_checks, and prose stays the model's.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    if not task.slots:
        return schema
    units = schema["properties"]["units"]
    units["minItems"] = len(task.slots)
    units["maxItems"] = len(task.slots)
    item = units["items"]
    # One entry per slot, in the task's order: the slot it fills and the only facts its unit may
    # cite. Both are the code's to state - the plan assigned them - so a reply that fills the
    # wrong slot or cites another slot's fact is unrepresentable rather than rejected, which is
    # the largest rejection family the canary recorded (RESEARCH_AND_GUIDELINES.md section 27.1;
    # D1 in 27.5). The gateway answers HTTP 400 for a pattern in a strict schema, but honours an
    # enum and enforces prefixItems by position: told to cite the wrong fact under this shape it
    # cited the right one anyway (probe, 2026-09-05, section 27.10).
    units["prefixItems"] = [
        {
            **item,
            "properties": {
                **item["properties"],
                "section": {"const": task.section_id},
                "slot": {"const": slot},
                "fact_ids": {
                    **item["properties"]["fact_ids"],
                    "items": {"type": "string", "enum": citable(task, slot)},
                },
            },
        }
        for slot in task.slots
    ]
    del units["items"]
    return schema


def citable(task: SectionTask, slot: str) -> list[str]:
    """The fact IDs a slot's unit may cite: the set the plan assigned it, or the section's own
    when the plan assigned none, plus the neutral facts every unit may rest on.

    ``unit_checks`` judges the same three sets, so the schema and the guard cannot disagree
    (docs/README_CONTRACT.md check 4). A fact ID is ``<kind>:<slug>`` by construction, so the
    neutral kinds are read from the ID itself rather than looked up.
    """
    bound = task.slot_facts.get(slot)
    allowed = set(task.accepted_ids if bound is None else bound)
    allowed.update(i for i in task.accepted_ids if i.startswith(_NEUTRAL_KINDS))
    return sorted(allowed)


# identity and package facts belong to no slot and may support any unit (unit_checks).
_NEUTRAL_KINDS = ("identity:", "package:")


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
        slot_facts = slot_fact_sets(section, plan)
        titles = capability_titles(plan) if section == "key_capabilities" else {}
        renders = slot_rendering(section, slots, facts, dispositions, slot_facts)
        records = slot_records(slots, slot_facts, titles, renders)
        # The renderer prints links, commands, and code blocks itself. A unit that repeats one
        # of them is rejected for writing a URL or a command, which is how the canary lost two
        # authoring calls on 2026-09-05; saying what is already printed removes the reason to.
        renders_rule = (
            "A slot's `renders` is what the renderer prints there from the same facts; write "
            "only what it does not already say, and never repeat its link, label, or command. "
            "It is shown so you do not repeat it, never as a source of spellings: an identifier "
            "that appears only there, such as a module inside a command, is not yours to write. "
            if any(record.get("renders") for record in records)
            else ""
        )
        bound_rule = (
            "Each slot below gives the subject its unit is about and the only facts that unit "
            "may cite; a unit describes its own slot, never another's. "
            if any(len(record) > 1 for record in records)
            else ""
        )
        # A slot's title is rendered immediately before its unit, so a unit that opens by
        # restating the title reads as a stutter: measured on the canary the first time the
        # title travelled, where all seven capabilities began with their own heading.
        title_rule = (
            "A slot's title is printed immediately before its unit, so the unit never restates "
            "it and never opens with the product name; it adds what the title does not say. "
            if any(record.get("title") for record in records)
            else ""
        )
        packet = {
            "repository": entry.repository,
            "product_name": name,
            "mode": "author",
            "section_id": section,
            "objective": (
                f"{objective} Slots to fill, each exactly once: {', '.join(slots)}. "
                f"{bound_rule}{title_rule}{renders_rule}"
                f"Identifiers the prose may spell, exactly as written: {', '.join(spellings)}; "
                "any other API name, member, attribute, or parameter is rejected."
            ),
            "slots": records,
            "accepted_facts": accepted,
            "do_not_claim": do_not_claim,
            "length_budget": budget,
            "rendered_document": "",
            "existing_units": [],
        }
        tasks.append(
            SectionTask(
                section,
                packet,
                frozenset(ids),
                slots,
                slot_facts=slot_facts,
                slot_titles=titles,
            )
        )
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
    (bare, or as Class.method), or Class.member for a member a verified example uses.

    Exact spelling only - a package coordinate is not matched case-insensitively. An earlier
    version of this function did (2026-09-07), to work around ``canonical()`` altering a known
    abbreviation's casing inside a coordinate before this ever ran; external review, the same
    day, named that a contract violation in the making (README_CONTRACT.md section 2: exact
    package names keep their source spelling verbatim). The casing corruption is fixed at its
    own source instead (``_LOWER_WORD``'s hyphen/colon exclusion, renderer.py) - the token this
    function sees now already carries the fact's own exact spelling, so it needs no laundering.
    """
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
    """Tokens the renderer would have to wrap in a code span: dotted, snake, CamelCase, calls,
    package coordinates."""
    found: set[str] = set()
    for pattern in (_DOTTED, _SNAKE, _CAMEL, _CALL, _COORDINATE):
        found.update(match.group(0) for match in pattern.finditer(text))
    # An all-capital token with digits (U3D, A3DW, 3MF) is a format acronym, spelled in prose
    # as the contract's canonical abbreviations are, never an identifier.
    return {token for token in found if not (token.isupper() and token.isalnum())}


def source_prose(text: str) -> str:
    """The running prose of a source unit: no fenced block, code span, link target, URL, or tag."""
    for pattern in _NOT_PROSE:
        text = pattern.sub(" ", text)
    return text


def proper_noun(token: str) -> bool:
    """A name, not a path: every dotted segment capitalised, no underscore, no call parentheses."""
    return (
        "_" not in token
        and "(" not in token
        and all(part[:1].isupper() for part in token.split("."))
    )


def prose_nouns(facts: FactsDocument, name: str) -> frozenset[str]:
    """Proper nouns this document may spell in plain text, beyond the identifiers it may cite.

    ``identifier_tokens`` cannot tell ``OneNote`` from ``Document`` by shape, so a file format, a
    standard, or another product reads as an unsupported identifier and the sentence cannot be
    written at all: measured 2026-09-06 over the Python cohort, where ``TeX``, ``BarCode``,
    ``OneNote`` and ``EmailMessage`` each failed ``section_authoring`` twice on the same token.
    The all-capital carve-out in ``identifier_tokens`` already draws this line for acronyms
    (U3D, 3MF); this draws it for the capitalised names the source itself uses.

    A noun is admitted when the source README spells it in running prose - outside every fenced
    block, code span, link destination, URL and tag, where code lives - when it is a segment of
    the product's own name, or when it appears only inside a code span and no `public_symbol`
    fact spells it at all, bare or as any dotted suffix (RESEARCH_AND_GUIDELINES.md section 28.12
    G4-W17 arrival item 36). That last case is a standard, format or font name the upstream author
    happened to backtick rather than a rule about typography: `ZapfDingbats`, a PDF Standard-14
    font name, appears only inside code spans in Aspose.PDF for Go's own README and no public
    symbol spells it, so `source_prose` alone stripped it and the limitation naming it could not
    be written at all. Anything the facts already license as an identifier is still excluded here
    exactly as for a running-prose noun, so a real symbol - `Document`, backticked deliberately -
    keeps its code span and its verification; a noun is never wrapped and never carries a claim,
    exactly as a registry or hosting name does not.
    """
    candidates = {part for token in name.split(" ") for part in token.split(".") if part}
    for fact in facts.by_kind("inherited_unit"):
        if fact.polarity == "SUPPORTED":
            candidates.update(identifier_tokens(source_prose(fact.value)))
            without_fences = _NOT_PROSE[0].sub(" ", fact.value)
            for span in _CODE_SPAN.finditer(without_fences):
                candidates.update(identifier_tokens(span.group(1)))
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    return frozenset(
        token
        for token in candidates
        if proper_noun(token) and not identifier_allowed(token, allowed, members, methods)
    )


def canonical_abbreviations(facts: FactsDocument) -> dict[str, str]:
    """Lowercase spelling to canonical form, for every abbreviation this document owns.

    The fixed set plus every format extension the facts record that is not an ordinary word, so a
    repository whose formats are OBJ and GLB gets those too.
    """
    forms = {abbreviation.lower(): abbreviation for abbreviation in ABBREVIATIONS}
    for fact in facts.by_kind("format"):
        extension = fact.value.lstrip(".").lower()
        if len(extension) >= 3 and extension.isalpha() and extension not in WORD_EXTENSIONS:
            forms[extension] = extension.upper()
    return forms


def forbidden_text_pattern(extra: Sequence[str] = ()) -> str:
    """A regular expression for a unit's text: none of the fragments a unit may not contain.

    Built from the same table unit_checks judges by. It is NOT put in the per-call schema: the
    gateway answers HTTP 400 for a strict ``json_schema`` carrying ``pattern``, measured on
    qwen3-next during G2-W12, which is the fallback docs/RESEARCH_AND_GUIDELINES.md section 27.7
    anticipated and section 27.10 allows. The URL, command and edition families therefore stay
    post-validated by unit_checks until a normalisation owns them.
    """
    anywhere = [fragment for fragment, _ in _FORBIDDEN if fragment not in _ANCHORED_ONLY]
    anywhere += list(extra)
    anywhere_alternation = "|".join(re.escape(fragment) for fragment in anywhere)
    anchored_alternation = "|".join(re.escape(fragment) for fragment in _ANCHORED_ONLY)
    return f"^(?!(?:{anchored_alternation}))(?!(?:.|\\n)*(?:{anywhere_alternation}))(?:.|\\n)*$"


def allowed_identifiers(facts: FactsDocument, name: str) -> frozenset[str]:
    """Identifiers the prose may spell: every SUPPORTED fact value, each dotted suffix of a
    symbol or import path (``Scene.open`` for ``aspose.threed.Scene.open``), its call form, and
    the product name's tokens. Citations stay restricted to the section's set; identifiers may
    name any fact, as the contract requires, because the renderer wraps them in code spans.
    """
    allowed: set[str] = set(product_name_tokens(name))
    allowed.update(REGISTRY_NAMES.values())  # package registries are proper nouns, not APIs
    # So is the hosting site a verified link points at: prose names it, the renderer leaves it
    # in plain text, and no fact records it as a value.
    allowed.update(host_names(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED"))
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


# A prose direction word beside a format extension, mirroring evidence/facts/formats.py's own
# input/output vocabulary but for English sentences, not Python identifiers - a distinct task
# (classifying prose, not code), so this is not a duplicate of that module's vocabulary, and
# `core/` layering forbids importing an extractor's own word lists here regardless
# (docs/REPOSITORY_LAYOUT.md section 2.1).
_PROSE_EXTENSION = re.compile(r"(?<![\w.])\.[A-Za-z]{2,5}\b")
_PROSE_WORD = re.compile(r"[A-Za-z]+")
_PROSE_INPUT_WORDS = frozenset(
    {
        "read",
        "reads",
        "reading",
        "load",
        "loads",
        "loading",
        "open",
        "opens",
        "opening",
        "import",
        "imports",
        "importing",
        "parse",
        "parses",
        "parsing",
    }
)
_PROSE_OUTPUT_WORDS = frozenset(
    {"write", "writes", "writing", "save", "saves", "saving", "export", "exports", "exporting"}
)


def _prose_direction(text: str) -> str | None:
    """ "input", "output", or None when the text names both or neither direction - an unambiguous
    bag-of-words read, never a sentence-level parse (TB-09, D9)."""
    words = {word.lower() for word in _PROSE_WORD.findall(text)}
    is_input = bool(words & _PROSE_INPUT_WORDS)
    is_output = bool(words & _PROSE_OUTPUT_WORDS)
    if is_input == is_output:
        return None
    return "input" if is_input else "output"


def _example_format_claims(facts: FactsDocument, ordinal: str) -> dict[str, frozenset[str]]:
    """The (direction -> extensions) one example already claims for itself, read straight from
    the evidence `evidence/facts/formats.py` already recorded for it (its own
    ``f"example {ordinal}: {direction} {extension}"`` wording) - no new extraction, only data
    already on hand (TB-09, D9)."""
    marker = f"example {ordinal}:"
    by_direction: dict[str, set[str]] = {"input": set(), "output": set()}
    for fact in facts.by_kind("format"):
        direction = fact.id.split(":", 1)[-1].split(".", 1)[0]
        if direction not in by_direction:
            continue
        if any(marker in (item.detail or "") for item in fact.evidence):
            by_direction[direction].add(fact.value.lower())
    return {direction: frozenset(values) for direction, values in by_direction.items()}


def unit_example_action_mismatches(unit: Mapping[str, Any], facts: FactsDocument) -> list[str]:
    """A unit's prose about a specific cited example, checked against that example's own recorded
    format claims (TB-09, external review D9, 2026-09-08: the reviewer once caught a lead-in
    naming one action for an example whose recorded code said a different one - the original
    instance is no longer reproducible against current data, but the shape recurs by construction
    whenever authoring paraphrases an example instead of only describing what it already proved).

    Only a direction word (reads/opens/... vs writes/exports/...) paired with an extension the
    cited example's own evidence *disputes* - claims in the opposite direction - is a defect. An
    extension the example makes no claim for at all is not one: the example may do something
    `format_claims` does not (yet) recognize (TB-02's own, still-open verb-vocabulary gap), and
    guessing from silence would be exactly the general NLP verifier this taskcard forbids
    building. Never a new controller: this reads facts already computed, nothing else.
    """
    direction = _prose_direction(str(unit.get("text", "")))
    if direction is None:
        return []
    opposite = "output" if direction == "input" else "input"
    extensions = {ext.lower() for ext in _PROSE_EXTENSION.findall(str(unit.get("text", "")))}
    if not extensions:
        return []
    errors: list[str] = []
    for fact_id in unit.get("fact_ids", []):
        if not str(fact_id).startswith("example:"):
            continue
        # The fact ID's ordinal is zero-padded ("example:001"); the evidence
        # evidence/facts/formats.py already wrote for it names the same example by its plain int
        # ordinal ("example 1: ..."), since it comes straight from `ExampleCandidate.ordinal`.
        digits = str(fact_id).split(":", 1)[-1]
        if not digits.isdigit():
            continue
        ordinal = str(int(digits))
        claims = _example_format_claims(facts, ordinal)
        for extension in sorted(extensions & claims[opposite] - claims[direction]):
            errors.append(
                f"names {extension} as {direction}, but example {ordinal}'s own recorded "
                f"format claims say {opposite}"
            )
    return errors


def unit_checks(
    output: dict[str, Any], task: SectionTask, facts: FactsDocument, name: str
) -> list[str]:
    """Why the section's units may not be used, beyond schema and binding; empty when they hold."""
    errors: list[str] = []
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    nouns = prose_nouns(facts, name)
    merge_repeated_slots(output)
    expected = list(task.slots)
    # The plan owns the slot set: a unit for a slot the task never asked for (a repair adding
    # a limitation the plan does not carry, twice on the canary) is dropped rather than
    # rejected, while a missing or repeated slot still fails.
    output["units"] = [unit for unit in output.get("units", []) if unit.get("slot") in expected]
    slots_seen = [unit.get("slot") for unit in output.get("units", [])]
    if sorted(slots_seen) != sorted(expected):
        errors.append(
            f"units must fill exactly these slots once each: {', '.join(expected)}; "
            f"got {', '.join(str(slot) for slot in slots_seen)}"
        )
    # README_CONTRACT.md row 18: the shell's closing sentence names the Enterprise Edition
    # exactly once, so the authored context sentence never repeats the name. The code owns that
    # canonical form, so it normalises the repeat away rather than re-asking the model and
    # rejecting the reply (docs/RESEARCH_AND_GUIDELINES.md section 27.10); the check stays and
    # still fails for a name the normalisation cannot reach.
    if task.section_id == "enterprise_relationship":
        for unit in output.get("units", []):
            unit["text"] = _EDITION.sub("commercial edition", str(unit.get("text", "")))
    for unit in output.get("units", []):
        if task.section_id == "enterprise_relationship" and "Enterprise Edition" in str(
            unit.get("text", "")
        ):
            errors.append(
                f"unit {unit.get('slot')}: names the Enterprise Edition; the shell's closing "
                "sentence names it exactly once"
            )
    # README_CONTRACT.md check 4: a unit's facts lie within the set the plan assigned to its
    # slot; identity and package facts belong to no slot and may support any unit.
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    for unit in output.get("units", []):
        bound = task.slot_facts.get(str(unit.get("slot")))
        if bound is None:
            continue
        outside = [i for i in unit.get("fact_ids", []) if i not in bound and i not in neutral]
        if outside:
            errors.append(
                f"unit {unit.get('slot')}: cites facts outside its slot's planned set "
                f"({', '.join(outside)}); a unit describes its own slot's facts, never "
                "another slot's"
            )
    # README_CONTRACT.md check 4: the capability's title is supported by the facts its unit
    # cites. Slot fact sets overlap by design - one example can serve two capabilities - so a
    # fact-ID subset check cannot separate two capabilities even in principle (section 27.2 RC2).
    # The title is what separates them, so every identifier and format name it spells appears in
    # the values of the facts the unit actually cites.
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    for unit in output.get("units", []):
        title = task.slot_titles.get(str(unit.get("slot")), "")
        if not title:
            continue
        cited = " ".join(values.get(i, "") for i in unit.get("fact_ids", [])).lower()
        unsupported = sorted(
            term
            for term in title_terms(title, facts)
            # A title names a format or a product the same way its prose does: "Parse OneNote
            # .one files" asks nothing of the facts for OneNote, and everything for .one.
            if term not in nouns
            and term.lstrip(".").lower() not in cited
            and term.lstrip(".").lower() not in common
        )
        if unsupported:
            errors.append(
                f"unit {unit.get('slot')}: its title {title!r} names "
                f"{', '.join(unsupported)}, which the facts it cites do not carry; cite the facts "
                "that support this slot's title, or the sentence belongs to another slot"
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
            matched = text.startswith(marker) if marker in _ANCHORED_ONLY else marker in text
            if matched:
                errors.append(f"unit {slot}: text contains {meaning} ({marker.strip()!r})")
                break
        strays = sorted(
            token
            for token in identifier_tokens(text)
            if not identifier_allowed(token, allowed, members, methods)
            and token not in nouns
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
        errors.extend(
            f"unit {slot}: {mismatch}" for mismatch in unit_example_action_mismatches(unit, facts)
        )
    return errors


def _reconstruction_lineage_holds(
    bundle: Path, fact_ids: set[str], facts: FactsDocument, prompt_sha256: str
) -> bool:
    """Whether a sealed bundle's own record of what it consumed still matches now (R5, external
    review, 2026-09-08).

    Matching a reconstructed unit to a task by section+slot name is not proof the unit was ever
    produced by a request resembling this task's own current one - the facts behind it, or the
    ``section_authoring`` prompt itself, may have changed since the bundle was sealed. The sealed
    bundle's own ``dependencies.json`` already records exactly this, at the same precision the
    rest of the system trusts it for (``bundle/evaluation.py``'s own reopening decision): a
    ``canonical_hash`` of every consumed fact's full content, and every consumed prompt's own
    sha256. A reconstruction is trusted only when both are still bit-identical to what is sealed -
    not merely present, not merely equal in value - for every fact ID a reconstructed unit cites,
    and for the current ``section_authoring`` prompt itself. Anything else is a stale
    reconstruction, seeded under a hash a fresh call would otherwise correctly recompute, and
    ``reconstructed_task_output`` returns ``None`` so the caller makes that real call instead.
    """
    dependencies_path = bundle / "dependencies.json"
    if not dependencies_path.is_file():
        return False
    sealed = json.loads(dependencies_path.read_text(encoding="utf-8"))
    sealed_prompt = sealed.get("prompts", {}).get("section_authoring", {})
    if sealed_prompt.get("sha256") != prompt_sha256:
        return False
    sealed_facts: dict[str, str] = sealed.get("facts", {})
    current_by_id = {fact.id: fact for fact in facts.facts}
    for fact_id in fact_ids:
        current_fact = current_by_id.get(fact_id)
        if current_fact is None:
            return False
        if sealed_facts.get(fact_id) != canonical_hash(asdict(current_fact)):
            return False
    return True


def reconstructed_task_output(
    bundle: Path, task: SectionTask, facts: FactsDocument, prompt_sha256: str
) -> dict[str, Any] | None:
    """One task's own accepted output, rebuilt from a sealed bundle's merged
    ``content_units.json`` - never a new committed bytes for it (G5-W02, 27.2 RC4).

    A unit already carries its own ``section`` and ``slot`` (the model's own output schema
    requires both), so a task's exact contribution is recoverable by filtering on both - not
    section alone, which a batched section (``task.is_batch``) would blur across its several
    tasks with no way to tell them apart again. A batched task is never reconstructed for that
    reason: ``merge_units`` flattens every batch's own ``omitted`` list under their shared
    section with nothing left distinguishing which batch it came from, so a batched task's own
    omitted facts cannot be told apart once merged, and a caller must not guess. Returns None
    when the bundle carries no such artifact, the task is a batch, the reconstruction would be
    incomplete (a slot's unit is missing), or the facts/prompt behind it have since changed
    (``_reconstruction_lineage_holds``, R5) - a caller falls back to a real call either way.
    """
    if task.is_batch:
        return None
    path = bundle / CONTENT_UNITS_FILENAME
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    units = [
        unit
        for unit in document.get("units", [])
        if unit.get("section") == task.section_id and unit.get("slot") in task.slots
    ]
    if {unit.get("slot") for unit in units} != set(task.slots):
        return None
    cited_fact_ids = {fact_id for unit in units for fact_id in unit.get("fact_ids", [])}
    if not _reconstruction_lineage_holds(bundle, cited_fact_ids, facts, prompt_sha256):
        return None
    omitted = [
        {key: value for key, value in item.items() if key != "section"}
        for item in document.get("omitted", [])
        if item.get("section") == task.section_id
    ]
    return {"units": units, "omitted": omitted}


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
