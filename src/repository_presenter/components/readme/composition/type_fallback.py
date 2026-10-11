"""The last resort for one API Reference type description the guard refuses and no re-ask fixes.

``section_authoring`` writes the API Reference's per-type descriptions in bounded batches, one call
for up to forty types, so one refused unit fails all forty. README_CONTRACT.md row 14 already says
what a type with no verifiable description gets: "its verified signature summary, never an invented
sentence". When the only thing wrong with a ``type:`` unit is an identifier no fact carries, the
description is the unverifiable part, so on the final attempt it is replaced by that summary and
the batch survives.

Baseline reseal of 7c5acbf7 (2026-10-10), aspose-3d-foss/Aspose.3D-FOSS-for-Java: "ArrayListAdapter
provides a wrapper around Java's ArrayList ..." was refused twice for ``ArrayList``, a standard
library type inferred from the symbol's name that no fact carries; the re-ask reproduced it byte for
byte and the other thirty-nine descriptions went down with it. The guard is right to refuse the
sentence (it is an unevidenced claim); losing the batch for it is the defect.

This module sits beside ``authoring.py`` rather than inside it so the change moves no governed
constant; ``repair/rounds.py`` composes it after ``recover_section_authoring_output``. The same
composition also deletes, in the opening, an audience claim no accepted fact states
(``audience.strip_audience_units``), because this is the one initial-draft ``recover=`` every
section's authoring call passes.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

from repository_presenter.components.readme.composition.audience import (
    strip_audience_units,
    support_texts,
)
from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    recover_section_authoring_output,
    unit_checks,
)
from repository_presenter.core.facts import Fact, FactsDocument

_TYPE_SLOT = "type:"
_STRAY_IDENTIFIERS = "identifiers that are not accepted fact values"


def _alone(task: SectionTask, slot: str) -> SectionTask:
    """``task`` narrowed to the one ``slot``, so a single unit can be judged by itself."""
    return dataclasses.replace(
        task,
        slots=(slot,),
        slot_facts={slot: task.slot_facts[slot]} if slot in task.slot_facts else {},
        slot_titles={},
        slot_render_lines={},
        must_carry=frozenset(),
        must_carry_text={},
    )


def _only_stray_identifiers(
    unit: dict[str, Any], task: SectionTask, facts: FactsDocument, name: str
) -> bool:
    """Whether judging ``unit`` alone yields refusals for stray identifiers and nothing else."""
    slot = str(unit.get("slot"))
    errors = unit_checks(
        {"units": [copy.deepcopy(unit)], "omitted": []}, _alone(task, slot), facts, name
    )
    prefix = f"unit {slot}: {_STRAY_IDENTIFIERS}"
    return bool(errors) and all(error.startswith(prefix) for error in errors)


def _summary_candidates(fact: Fact) -> list[str]:
    """The verified summary for a type, most informative first: its signature when it has one,
    else what the symbol is. Both are the renderer's own fallbacks for a type with no unit."""
    attributes = fact.attributes or {}
    candidates: list[str] = []
    signature = str(attributes.get("signature") or "").replace("|", "/").replace("`", "").strip()
    if signature:
        candidates.append(f"Defined as {signature}.")
    candidates.append(f"Public {attributes.get('symbol_kind') or 'symbol'}.")
    return candidates


def recover_unevidenced_type_descriptions(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument, name: str
) -> dict[str, Any] | None:
    """Replace, in place, the description of each API Reference ``type:`` unit whose only refusal
    is an unevidenced identifier by that type's verified summary; ``None`` when nothing changed.

    Only the ``type:`` slots of an ``api_reference`` task, only a unit refused for stray
    identifiers and nothing else (a unit with another defect is left for the job to fail on), and
    only a replacement ``unit_checks`` itself accepts. The unit keeps its section, slot and
    ``fact_ids``; no sentence is invented, since the summary is the symbol's own kind or signature.
    """
    if task.section_id != "api_reference":
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    by_id = {fact.id: fact for fact in facts.facts}
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not str(unit.get("slot", "")).startswith(_TYPE_SLOT):
            continue
        fact = by_id.get(str(unit["slot"])[len(_TYPE_SLOT) :])
        if fact is None or fact.polarity != "SUPPORTED":
            continue
        if not _only_stray_identifiers(unit, task, facts, name):
            continue
        for summary in _summary_candidates(fact):
            replacement = {**unit, "text": summary}
            slot = str(unit["slot"])
            if not unit_checks(
                {"units": [replacement], "omitted": []}, _alone(task, slot), facts, name
            ):
                unit["text"] = summary
                changed = True
                break
    return output if changed else None


def recover_section_authoring_with_type_fallback(
    output: dict[str, Any],
    *,
    slot_titles: Any,
    task: SectionTask,
    facts: FactsDocument,
    name: str,
) -> dict[str, Any] | None:
    """``section_authoring``'s initial-draft ``recover=``: every correction
    ``recover_section_authoring_output`` makes, then the type-description fallback above on
    whatever those left, then the deletion of an audience claim no accepted fact states
    (``audience.strip_audience_units``; the opening only). ``None`` only when none changed
    anything."""
    changed = recover_section_authoring_output(output, slot_titles=slot_titles) is not None
    if recover_unevidenced_type_descriptions(output, task=task, facts=facts, name=name) is not None:
        changed = True
    support = support_texts(task.accepted_ids, facts)
    if strip_audience_units(output, support, task.section_id) is not None:
        changed = True
    return output if changed else None
