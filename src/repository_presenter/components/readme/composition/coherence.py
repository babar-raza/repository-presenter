"""Stage S8: the single coherence pass - revise LLM-owned units only, once, then re-render.

The pass is one section_authoring call in coherence mode: the job sees the rendered document and
every authored unit, and returns every unit with its section and slot unchanged and its text
possibly revised. The guard holds each returned unit to its own section's rules (slots exactly
once, citations inside the section's set, no Markdown, identifiers that are fact values), so the
pass can only change prose the LLM already owned. Deterministic blocks are untouched by
construction: the renderer is a pure function and only unit texts change.
"""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    section_spellings,
    unit_checks,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.registry.models import RegistryEntry

COHERENCE_SECTION = "all"
_SPELLING_CAP = 120


def coherence_packet(
    entry: RegistryEntry,
    readme: str,
    units_document: dict[str, Any],
    tasks: list[SectionTask],
    facts: FactsDocument,
) -> dict[str, Any]:
    """The packet for the one coherence call: the document, the units, and their closed facts."""
    by_id = {fact.id: fact for fact in facts.facts}
    # Batch-authored type descriptions are per-type sentences, not narrative: the coherence
    # pass neither receives nor returns them, so its output stays within the budget.
    tasks = [task for task in tasks if not task.is_batch]
    accepted_ids: list[str] = []
    for task in tasks:
        accepted_ids.extend(fact_id for fact_id in sorted(task.accepted_ids))
    accepted_ids = list(dict.fromkeys(accepted_ids))
    slots = [f"{task.section_id}/{slot}" for task in tasks for slot in task.slots]
    spellings = section_spellings(accepted_ids, facts)[:_SPELLING_CAP]
    return {
        "repository": entry.repository,
        "product_name": product_name(entry),
        "mode": "coherence",
        "section_id": COHERENCE_SECTION,
        "objective": (
            "Revise the LLM-owned units, once, so the whole document reads as one coherent "
            "developer journey: no repetition across sections, one voice, each unit still true to "
            "its facts. Return every unit with its section and slot exactly as given, revised or "
            f"not. Units to return, each exactly once: {', '.join(slots)}. Identifiers the prose "
            f"may spell, exactly as written: {', '.join(spellings)}; any other API name, member, "
            "attribute, or parameter is rejected."
        ),
        "accepted_facts": [
            {"id": fact_id, "kind": by_id[fact_id].kind, "value": by_id[fact_id].value}
            for fact_id in accepted_ids
            if fact_id in by_id
        ],
        "do_not_claim": bounded_records(
            facts,
            ["format", "install_command", "link_target", "example"],
            ("CONTRADICTED", "UNRESOLVED"),
        ),
        "length_budget": "each unit within its own section's budget; never longer than before",
        "rendered_document": readme,
        "existing_units": [
            unit
            for unit in units_document.get("units", [])
            if not str(unit.get("slot", "")).startswith("type:")
        ],
    }


def coherence_checks(
    output: dict[str, Any], tasks: list[SectionTask], facts: FactsDocument, name: str
) -> list[str]:
    """Every section's rules, applied to the units the pass returned for that section."""
    errors: list[str] = []
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in output.get("units", []):
        by_section.setdefault(str(unit.get("section", "")), []).append(unit)
    tasks = [task for task in tasks if not task.is_batch]
    known = {task.section_id for task in tasks}
    for section in sorted(set(by_section) - known):
        errors.append(f"units name a section the plan did not author: {section}")
    for task in tasks:
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        errors.extend(unit_checks({"units": owned, "omitted": []}, task, facts, name))
    return errors


def apply_coherence(
    units_document: dict[str, Any], output: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """The units document with revised texts, and the section/slot names whose text changed."""
    revised_text = {
        (unit["section"], unit["slot"]): unit["text"] for unit in output.get("units", [])
    }
    revised: list[str] = []
    units: list[dict[str, Any]] = []
    for unit in units_document.get("units", []):
        key = (unit["section"], unit["slot"])
        text = revised_text.get(key, unit["text"])
        fact_ids = next(
            (
                item.get("fact_ids", unit["fact_ids"])
                for item in output.get("units", [])
                if (item.get("section"), item.get("slot")) == key
            ),
            unit["fact_ids"],
        )
        if text != unit["text"]:
            revised.append(f"{key[0]}/{key[1]}")
        units.append({**unit, "text": text, "fact_ids": fact_ids})
    document = {
        **units_document,
        "units": units,
        "coherence": {"applied": True, "revised": revised},
    }
    return document, revised
