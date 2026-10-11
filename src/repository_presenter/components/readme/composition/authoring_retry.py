"""What section_authoring does once the model's universal re-ask has not converged.

Wave 3 (cut f69f75c7): nine of thirty-six repositories failed with ``section_authoring: output
rejected twice``. Read from the archived ``rejected-*.json`` of each, the causes were these, and
none was a section the model could not write:

* a rejection named the first of several violations of one kind (TeX-Python restated two commands
  and was told about one), so the re-ask fixed what it was told and kept the rest;
* a reply fixed the stray identifier it was told about and, in doing so, restated its slot's title
  (PDF-Cpp) or left one list item unstated (Slides-Java), faults the first message had no reason to
  name - and the single re-ask was spent;
* the re-ask returned the same reply byte for byte (Words-Python, Email-Python), because it was
  asked the same question.

``authoring.unit_checks`` now names every violation of every unit in one rejection. This module is
the rest of the unit-level remedy:

* :func:`authoring_narrowing` - one further ask, after the two the job already makes, for only the
  slots still failing. It is a different request (the same prompt, packet and schema narrowed to
  those slots, with the complete defect list and the unit each one replaces), so it is not a third
  equivalent attempt, and the accepted units are kept exactly as the second reply gave them.
  Whatever the merged reply gets wrong is judged by the ordinary checks; a rejection that names no
  slot (a must-carry unit nobody cited) cannot be narrowed and fails as before.
* :func:`recover_restating_sentences` - the deterministic last resort that removes a sentence only
  when it restates something the page already prints (the slot's title; a command the renderer
  prints verbatim beside the unit). It never rewrites a word and never touches a unit that does
  not restate. A stray identifier is deliberately NOT rewritten into words: that would launder an
  unevidenced claim, which is the check's whole purpose, not remove it.

It sits beside ``authoring.py`` rather than inside it so the change moves no governed constant.
"""

from __future__ import annotations

import dataclasses
import json
import re
import string
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    authoring_schema,
    restated_command_lines,
    restates_own_title,
    slots_clause,
)
from repository_presenter.components.readme.composition.output_bounds import (
    bound_authoring_citations,
)
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import Narrowing
from repository_presenter.core.llm.prompts import LoadedManifest

_SLOT_SET_ERROR = "units must fill exactly these slots once each"
# list_coverage names the slots that owe a kept list's items:
# "Fold each into a unit citing X (a, b)".
_LIST_SLOTS = re.compile(r"Fold each into a unit citing \S+ \((?P<slots>[^)]*)\)")
# Accepted units are shown to the narrowed ask so it does not repeat them; a long section shows
# the first of them only, which is all a sentence-level repeat needs.
_ACCEPTED_SHOWN_CHARS = 6000
# A sentence ends at ``.``/``!``/``?`` that follows a word and precedes a capital, a digit, a quote
# or an opening bracket. A full stop standing alone ("ruff check . to lint") or followed by a
# lower-case word ("e.g. the") ends nothing: cutting there would leave half a sentence behind.
_SENTENCE_BREAK = re.compile(r"(?<=\S[.!?])(\s+)(?=[A-Z0-9\"'(\[`])")


def _slots_of(task: SectionTask, error: str) -> list[str] | None:
    """The slots one rejection concerns: a unit's own refusal names it, a kept list names the units
    that owe it. ``None`` when the rejection names no slot (a must-carry unit nobody cited, a
    schema error), which no narrowed ask can address."""
    for slot in sorted(task.slots, key=len, reverse=True):
        if error.startswith(f"unit {slot}: "):
            return [slot]
    listed = _LIST_SLOTS.search(error)
    if listed is not None:
        named = [name.strip() for name in listed.group("slots").split(",")]
        owed = [slot for slot in named if slot in task.slots]
        return owed or None
    return None


def _units(content: str) -> list[dict[str, Any]] | None:
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return None
    units = document.get("units") if isinstance(document, dict) else None
    if not isinstance(units, list):
        return None
    return [unit for unit in units if isinstance(unit, dict)]


def failing_slots(task: SectionTask, content: str, rejection: Sequence[str]) -> list[str]:
    """The slots of ``task``, in its order, that the rejection of ``content`` is about; empty when
    the rejection is about anything else too (then nothing is narrowed and the job fails as it
    always did), or when ``content`` is not a reply to this task."""
    units = _units(content)
    if units is None or not rejection:
        return []
    produced = Counter(str(unit.get("slot")) for unit in units)
    failing: set[str] = set()
    for error in rejection:
        if error.startswith(_SLOT_SET_ERROR):
            failing.update(slot for slot in task.slots if produced[slot] != 1)
            continue
        owned = _slots_of(task, error)
        if owned is None:
            return []
        failing.update(owned)
    return [slot for slot in task.slots if slot in failing]


def _defects(
    task: SectionTask, rejection: Sequence[str], slots: Sequence[str], content: str
) -> list[str]:
    """The rejection lines that concern ``slots``, whole, plus one line per slot the reply did not
    return exactly once (the slot-set rule's own line names every slot of the section, which would
    mislead a narrowed ask)."""
    produced = Counter(str(unit.get("slot")) for unit in _units(content) or [])
    lines: list[str] = []
    for error in rejection:
        if error.startswith(_SLOT_SET_ERROR):
            continue
        owned = _slots_of(task, error) or []
        if set(owned) & set(slots):
            lines.append(error)
    for slot in slots:
        if produced[slot] == 0:
            lines.append(f"unit {slot}: no unit was returned for this slot")
        elif produced[slot] > 1:
            lines.append(f"unit {slot}: returned {produced[slot]} times; return it exactly once")
    return lines


def _listing(units: Sequence[Mapping[str, Any]], limit: int) -> str:
    shown: list[str] = []
    used = 0
    for unit in units:
        line = f"- {unit.get('slot')}: {unit.get('text')}"
        if used + len(line) > limit:
            shown.append(f"- (and {len(units) - len(shown)} more accepted slots)")
            break
        shown.append(line)
        used += len(line)
    return "\n".join(shown)


def _objective(
    task: SectionTask,
    manifest: LoadedManifest,
    slots: Sequence[str],
    content: str,
    rejection: Sequence[str],
) -> str:
    """The task's objective, re-stated for ``slots`` alone and followed by the correction: the
    complete defect list, the unit each slot is to replace, and the units already accepted."""
    base = str(task.packet.get("objective", ""))
    objective = base.replace(slots_clause(task.slots), slots_clause(slots), 1)
    if objective == base and len(slots) != len(task.slots):
        objective = f"{base} {slots_clause(slots)}"
    previous = {str(unit.get("slot")): unit for unit in _units(content) or []}
    template = string.Template(manifest.manifest.rejection_template)
    reasons = template.substitute(
        errors="\n- ".join(_defects(task, rejection, slots, content))
    ).strip()
    again = "\n".join(
        f"- {slot}: {previous[slot].get('text')}"
        if slot in previous
        else f"- {slot}: (none returned)"
        for slot in slots
    )
    earlier = (
        "was accepted for every other slot of this section; only the slots named above are asked "
        "for again"
        if len(slots) < len(task.slots)
        else "was rejected"
    )
    parts = [
        objective,
        f"Correction: an earlier reply to this request {earlier}, and each unit you write "
        "replaces its earlier one entirely, so it keeps everything that unit already said "
        "correctly.",
        f"Earlier text of each slot asked for again:\n{again}",
    ]
    accepted = [unit for slot, unit in previous.items() if slot not in set(slots)]
    if accepted and not task.is_batch:
        parts.append(
            "Already accepted, shown so that you do not repeat it:\n"
            + _listing(accepted, _ACCEPTED_SHOWN_CHARS)
        )
    parts.append(reasons)
    return "\n\n".join(parts)


def _narrowed_task(
    task: SectionTask,
    manifest: LoadedManifest,
    slots: Sequence[str],
    content: str,
    rejection: Sequence[str],
) -> SectionTask:
    wanted = tuple(slot for slot in task.slots if slot in set(slots))
    packet = dict(task.packet)
    packet["slots"] = [
        record
        for record in task.packet.get("slots", [])
        if isinstance(record, dict) and record.get("slot") in set(wanted)
    ]
    packet["objective"] = _objective(task, manifest, wanted, content, rejection)
    return dataclasses.replace(task, packet=packet, slots=wanted)


def _merge(task: SectionTask, merged: str, narrowed: str, slots: Sequence[str]) -> str:
    """``merged`` with the units of ``slots`` taken from the ``narrowed`` reply and every other
    unit exactly as it was. A narrowed reply that is not exactly the slots asked for is returned
    as it stands, to be refused by the ordinary slot-set rule rather than quietly repaired."""
    try:
        base, extra = json.loads(merged), json.loads(narrowed)
    except json.JSONDecodeError:
        return narrowed
    if not (isinstance(base, dict) and isinstance(extra, dict)):
        return narrowed
    asked = set(slots)
    replaced = [unit for unit in extra.get("units", []) if isinstance(unit, dict)]
    if sorted(str(unit.get("slot")) for unit in replaced) != sorted(asked):
        return narrowed
    kept = [
        unit
        for unit in base.get("units", [])
        if isinstance(unit, dict) and str(unit.get("slot")) not in asked
    ]
    order = {slot: index for index, slot in enumerate(task.slots)}
    units = sorted(
        [*kept, *replaced], key=lambda unit: order.get(str(unit.get("slot")), len(order))
    )
    omitted: dict[str, Any] = {}
    for source in (base, extra):
        for item in source.get("omitted", []):
            if isinstance(item, dict) and "fact_id" in item:
                omitted[str(item["fact_id"])] = item
    return json.dumps({"units": units, "omitted": list(omitted.values())})


def authoring_narrowing(task: SectionTask, manifest: LoadedManifest) -> Narrowing:
    """The ``narrow`` argument of ``run_job`` for one section_authoring task: after the job's two
    asks, one more for only the slots whose units are still refused (see the module docstring)."""

    def ask(
        slots: Sequence[str], content: str, rejection: Sequence[str]
    ) -> tuple[Mapping[str, Any], dict[str, Any]]:
        narrowed = _narrowed_task(task, manifest, slots, content, rejection)
        return narrowed.packet, bound_authoring_citations(
            authoring_schema(manifest, narrowed), narrowed
        )

    return Narrowing(
        pending=lambda content, rejection: failing_slots(task, content, rejection),
        ask=ask,
        merge=lambda merged, narrowed, slots: _merge(task, merged, narrowed, slots),
        subject="the units still failing",
    )


def _without_sentences_naming(text: str, phrases: Sequence[str]) -> str | None:
    """``text`` without each sentence that spells one of ``phrases`` (case-insensitive), the other
    sentences exactly as written; ``None`` when no sentence names one or nothing would be left."""
    pieces = _SENTENCE_BREAK.split(text)
    sentences, separators = pieces[0::2], pieces[1::2]
    lowered = [phrase.lower() for phrase in phrases]
    keep = [
        index
        for index, sentence in enumerate(sentences)
        if not any(phrase in sentence.lower() for phrase in lowered)
    ]
    if not keep or len(keep) == len(sentences):
        return None
    rebuilt = ""
    for position, index in enumerate(keep):
        rebuilt += sentences[index]
        if position < len(keep) - 1:
            rebuilt += separators[index] if index < len(separators) else " "
    return rebuilt.strip()


def recover_restating_sentences(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``section_authoring``'s own ``run_job`` call (``recover=``,
    composed in ``type_fallback``): a unit that restates what the page already prints loses the
    sentences that do, when others remain.

    Two restatements only, each the exact test ``unit_checks`` refuses it by: the slot's own title,
    which is printed immediately before the unit (``restates_own_title``), and a command line the
    renderer prints verbatim in a fenced block right after it (``restated_command_lines``). Both
    are text the reader sees anyway, so dropping the sentence that repeats it loses no claim the
    page does not make, and no word of what remains is changed. A unit that is nothing but the
    restatement is left alone (the job fails as before rather than ship an empty unit), and so is
    a unit that restates neither. ``run_job`` re-validates the result through the real checks.

    Returns ``None`` when nothing was removed, never a no-op copy of ``output``.
    """
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        slot, text = str(unit.get("slot")), unit["text"]
        phrases: list[str] = []
        title = task.slot_titles.get(slot)
        if title and restates_own_title(text, title, facts):
            phrases.append(title)
        phrases.extend(restated_command_lines(text, task.slot_render_lines.get(slot, ())))
        if not phrases:
            continue
        kept = _without_sentences_naming(text, phrases)
        if kept is not None:
            unit["text"] = kept
            changed = True
    return output if changed else None
