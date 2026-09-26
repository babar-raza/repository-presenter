"""Stage S8: the coherence pass - revise LLM-owned units only, once, then re-render.

The pass is one or more section_authoring calls in coherence mode: each call sees the rendered
document and every authored unit for context, and returns exactly one batch's own units with their
section and slot unchanged and their text possibly revised. The guard holds each returned unit to
its own section's rules (slots exactly once, citations inside the section's set, no Markdown,
identifiers that are fact values), so the pass can only change prose the LLM already owned.
Deterministic blocks are untouched by construction: the renderer is a pure function and only unit
texts change.

PDFPY-03 (docs/DECISION_LOG.md 2026-09-17 09:18 UTC, corroborated 2026-09-24 14:20 UTC on a second
repository): a single call asking for every LLM-owned unit back at once has no bound on its own
completion size - unlike authoring.py's own per-task ``section_authoring`` calls, which are always
scoped to one section's (or one type-batch's) own slots. Once a document carries enough units (47
on PDF-Python, more on Font-Python), the reply alone exceeds the shared ``max_output_tokens=8000``
cap and the whole transaction aborts with ``finish_reason: length`` before any README or validation
is produced - PDF-Python and Font-Python have both been blocked on exactly this.
``coherence_batches`` splits the pass into fixed-size batches, mirroring the precedent
``authoring.py::_type_batches`` and
``reconciliation/dispositions.py::reconciliation_batches`` already set for the identical class of
problem: several bounded calls instead of one unbounded one, never splitting one section's own
slots across two calls (a section's own internal coherence is still judged in one call).

Cross-batch consistency is not silently dropped: every batch call still receives the *entire*
current rendered document and *every* current LLM-owned unit (``coherence_packet``'s own
``existing_units``/``rendered_document`` fields are unscoped, independent of which tasks are
passed) - only the schema-forced *reply* is narrowed to the batch's own units. The caller
(``repair/rounds.py``) also re-renders the document after each batch and feeds the updated
document into the next batch's packet, so a later batch judges its own section's coherence against
a document that already reflects every earlier batch's revisions, not the stale pre-pass text.
"""

from __future__ import annotations

import copy
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    section_spellings,
    slot_records,
    unit_checks,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import LoadedManifest
from repository_presenter.core.registry.models import RegistryEntry

COHERENCE_SECTION = "all"
_SPELLING_CAP = 120
# PDFPY-03: units per coherence-batch call. The manifest's own ``text`` field comment (item 75,
# prompts/section_authoring.yaml) records the longest unit ever measured across every sealed
# bundle at 972 characters (~250 tokens with its ``fact_ids``/JSON overhead) against a maxLength
# ceiling of 2200 set well above it for headroom, not as a realistic average. Sizing the batch off
# the real measured maximum rather than the abstract schema ceiling: 16 units x ~250 tokens worst
# case =~ 4000, half the shared 8000-token completion cap, with room to spare even if every unit in
# a batch happened to hit the longest length ever recorded at once. Large enough that the project's
# own small/typical candidates (on the order of 10-20 LLM-owned units) still complete in one
# coherence call exactly as before; small enough that a document the size of the ones that actually
# truncated (47+ units, PDF-Python and Font-Python) still splits into several bounded calls.
_COHERENCE_BATCH_UNITS = 16


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
    accepted_ids = coherence_citable_ids(tasks)
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
        "slots": [
            record
            for task in tasks
            for record in slot_records(task.slots, task.slot_facts, task.slot_titles)
        ],
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


def coherence_citable_ids(tasks: list[SectionTask]) -> list[str]:
    """Every fact ID any unit the coherence call returns may legitimately cite: the union of
    every authored section task's own accepted set - exactly the ids ``coherence_packet`` already
    shows the job as ``accepted_facts`` - batch/type tasks excluded as they carry no coherence
    unit at all.

    G4-W17 arrival item 123: this is the shared, per-call enum ``reconciliation_schema``'s own
    ``citable_fact_ids`` already builds for its per-batch ``fact_ids``, not a per-unit
    ``prefixItems`` restriction like ``authoring_schema``'s - the coherence call, like a
    reconciliation batch, returns many different units in one reply, so one decoder constraint
    covering everything any of them could legitimately cite is what bounds the runaway risk;
    each unit's own narrower, section-scoped set is still enforced post-hoc by
    ``coherence_checks``' per-section ``unit_checks`` call, exactly as it already was.
    """
    tasks = [task for task in tasks if not task.is_batch]
    ids: list[str] = []
    for task in tasks:
        ids.extend(fact_id for fact_id in sorted(task.accepted_ids))
    return list(dict.fromkeys(ids))


def coherence_batches(tasks: list[SectionTask]) -> list[tuple[str, list[SectionTask]]]:
    """Every LLM-owned section, grouped into fixed-size coherence batches in document (task) order
    - one ``(batch_id, group)`` pair per coherence call this round makes (PDFPY-03).

    Greedy accumulation, never splitting one task's own slots across two batches: a section's
    coherence is judged as a whole in one call, exactly as ``coherence_checks``' per-task
    ``unit_checks`` already expects. A single task whose own slot count alone exceeds
    ``_COHERENCE_BATCH_UNITS`` still gets its own, larger batch rather than being split - no
    section on record carries anywhere near that many slots (the portfolio's own largest,
    ``key_capabilities``, is bounded well under it), so this is a safety fallback, not the normal
    case. Batch/type tasks are excluded - they carry no coherence unit at all, same as
    ``coherence_citable_ids``.
    """
    tasks = [task for task in tasks if not task.is_batch]
    batches: list[list[SectionTask]] = []
    current: list[SectionTask] = []
    current_units = 0
    for task in tasks:
        if current and current_units + len(task.slots) > _COHERENCE_BATCH_UNITS:
            batches.append(current)
            current = []
            current_units = 0
        current.append(task)
        current_units += len(task.slots)
    if current:
        batches.append(current)
    return [(f"coherence#{index + 1}", group) for index, group in enumerate(batches)]


def coherence_batch_units(
    existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> list[dict[str, Any]]:
    """The subset of ``existing_units`` one batch's own ``tasks`` own - exactly the units that
    batch's own coherence call must return, once ``coherence_batches`` splits the pass into
    several calls. Matched by (section, slot), the same key ``apply_coherence`` already uses."""
    slots = {(task.section_id, slot) for task in tasks for slot in task.slots}
    return [unit for unit in existing_units if (unit.get("section"), unit.get("slot")) in slots]


def coherence_schema(
    manifest: LoadedManifest, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any]:
    """The section_authoring schema specialised for the one coherence call: exactly as many units
    back as were given, and each unit's own ``fact_ids`` limited to what any of them could
    legitimately cite.

    G4-W17 arrival item 75 (lane F F23, Email-.NET; lane B LANE-B-W14R2-F1, Cells-TS):
    section_authoring's per-task calls already get an exact ``units`` count from
    ``authoring_schema`` (the plan's own slot count), but the coherence call - one call returning
    every LLM-owned unit in the document at once, the largest single section_authoring reply by
    construction - used the bare manifest schema with no bound of its own beyond ``minItems: 1``.
    Nothing here changes ``text``'s or ``omitted``'s bounds; those come from the manifest schema
    this deep-copies, so the same ``maxLength`` fix covers this call too.

    G4-W17 arrival item 123: the units count bound above says nothing about any unit's own
    ``fact_ids`` - the one call site among section_authoring's five shapes (S3, S4's per-entry
    calls, S5, S6's per-task calls) that never got the per-kind bound treatment
    ``authoring_schema``/``reconciliation_schema`` already apply, and structurally the single
    largest section_authoring reply in the pipeline (every LLM-owned unit in the document, one
    call). A count bound alone still lets a runaway completion spend its whole budget on
    well-formed but wrong IDs (item 121's own reasoning), so ``fact_ids`` now carries the same
    enum-of-citable-IDs treatment the other two functions apply, via ``coherence_citable_ids``.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    units = schema["properties"]["units"]
    citable = coherence_citable_ids(tasks)
    if citable:
        units["items"]["properties"]["fact_ids"]["items"] = {"type": "string", "enum": citable}
    else:
        units["items"]["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
    count = len(existing_units)
    if count:
        units["minItems"] = count
        units["maxItems"] = count
    return schema


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
