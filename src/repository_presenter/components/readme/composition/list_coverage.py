"""A list kept as written states every item: the section-authoring guard for partial preservation.

Cut-2 BC-10 triage, cause 5 (aspose-pdf-foss/Aspose.PDF-FOSS-for-Java 131.list: six limitation
bullets dropped; Cells-Java 048.list: three of five rendered; 3D-Java 072.list: two of its items
absent). Reconciliation marked the whole list ``VERIFIED_PRESERVE`` - facts support every claim in
it - and Scope and Limitations authors one slot per unit, so the composer condensed the list and
silently lost items. Every unit-level check passed (the unit *is* cited); only independent review
read the section against the source, and its repair was then blocked by BC-04 because a dropped
item names an identifier that is not a fact value.

This module is the earlier, deterministic answer: after ``section_authoring`` returns, every item
of each ``VERIFIED_PRESERVE``/``VERIFIED_MOVE`` list unit the section was handed must be stated by
the units that cite that list, or the reply is refused with the missing items named (the one
re-ask can act on them). Presence is judged on the subject words of an item's lead (its bold
phrase, else its first words), not on its exact text: the composer rewrites items from facts, so
an item restated in other words is present, and one described without an identifier BC-04 would
refuse is still present.

It sits beside ``authoring.py`` rather than inside it so the change moves no governed constant;
``repair/rounds.py`` layers it onto ``unit_checks`` for the initial draft and for an S6 repair.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from repository_presenter.components.readme.composition.authoring import SectionTask
from repository_presenter.core.facts import FactsDocument

LIST_ITEM_MISSING = "list_item_missing"
# The dispositions that keep a unit as written. A rewrite or a supersession is the composer's to
# condense; only a list the reconciler said stands as written owes every item.
_AS_WRITTEN = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+(.*)$")
_BOLD_LEAD = re.compile(r"^\s*(?:\*\*|__)(.+?)(?:\*\*|__)")
_LEAD_BREAK = re.compile(r"\s(?:-{1,2}|\u2013|\u2014)\s|:\s|\.\s|\(")
_LEAD_WORDS = 6
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")
_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "that", "this", "are", "not", "but", "its", "can", "has"}
    | {"was", "were", "any", "all", "use", "uses", "used", "from", "into", "than", "yet", "via"}
)
_STEM = 5
_PRESENT_SHARE = 0.5
_QUOTE_LIMIT = 160
_MIN_ITEMS = 2


def list_items(text: str) -> list[str]:
    """The top-level bullets of a Markdown list, each with its wrapped and nested lines."""
    items: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _BULLET.match(line)
        if match is not None:
            items.append([match.group(1).strip()])
        elif items:
            items[-1].append(line.strip())
    return [" ".join(parts) for parts in items]


def _lead(item: str) -> str:
    """What the item is about: its bold phrase, else its words up to the first dash or colon."""
    bold = _BOLD_LEAD.match(item)
    if bold is not None:
        return bold.group(1)
    head = _LEAD_BREAK.split(item, maxsplit=1)[0]
    return " ".join(head.split()[:_LEAD_WORDS])


def _stems(text: str) -> set[str]:
    """Lower-case word stems of ``text``: identifiers split at case changes, dots and slashes, so
    ``PdfFileSecurity.setAllowExceptions`` and 'set allow exceptions' read alike."""
    words: set[str] = set()
    for chunk in _NON_WORD.split(text):
        for word in _CAMEL.split(chunk):
            token = word.lower()
            if token in _STOPWORDS or not (len(token) >= 3 or any(c.isdigit() for c in token)):
                continue
            words.add(token[:_STEM])
    return words


def missing_items(unit_text: str, destination_text: str) -> list[str]:
    """The items of ``unit_text`` whose subject the destination text never states."""
    destination = _stems(destination_text)
    missing: list[str] = []
    for item in list_items(unit_text):
        subject = _stems(_lead(item)) or _stems(item)
        if not subject:
            continue
        if len(subject & destination) < max(1, math.ceil(len(subject) * _PRESENT_SHARE)):
            missing.append(item)
    return missing


def _quote(item: str) -> str:
    plain = " ".join(item.replace("**", "").split())
    return plain if len(plain) <= _QUOTE_LIMIT else plain[:_QUOTE_LIMIT].rstrip() + "..."


def kept_list_units(
    dispositions: Mapping[str, Any], task: SectionTask, facts: FactsDocument
) -> dict[str, str]:
    """The list units kept as written in ``task``'s section that the plan handed it to author:
    ``unit id -> the unit's inherited text``. A list no slot of the section carries is printed by
    placement as written, so no authored unit stands in for it."""
    handed = set().union(*task.slot_facts.values()) if task.slot_facts else set()
    texts = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    return {
        unit: texts[unit]
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") in _AS_WRITTEN
        and entry.get("destination_section") == task.section_id
        and (unit := str(entry.get("unit_id", ""))).endswith(".list")
        and unit in handed
        and unit in texts
        and len(list_items(texts[unit])) >= _MIN_ITEMS
    }


def list_coverage_errors(
    output: Mapping[str, Any],
    task: SectionTask,
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
) -> list[str]:
    """One repairable refusal per kept list whose items the authored units do not all state."""
    errors: list[str] = []
    units = [unit for unit in output.get("units", []) if isinstance(unit, dict)]
    for unit_id, text in kept_list_units(dispositions, task, facts).items():
        citing = [unit for unit in units if unit_id in (unit.get("fact_ids") or [])]
        if not citing:
            continue  # carried_unit_errors and the slot checks own an uncited unit
        # The section's whole authored text, not only the units citing the list: the plan
        # cites a limitation's facts, not always the list unit its wording came from.
        stated = " ".join(str(unit.get("text", "")) for unit in units)
        missing = missing_items(text, stated)
        if not missing:
            continue
        slots = ", ".join(str(unit.get("slot")) for unit in citing)
        errors.append(
            f"{unit_id}: {LIST_ITEM_MISSING}: this list was kept as written, so every one of its "
            f"{len(list_items(text))} items must be stated by the units that cite it; "
            f"{len(missing)} not stated: "
            + "; ".join(f'"{_quote(item)}"' for item in missing)
            + f". Fold each into a unit citing {unit_id} ({slots}); an item that names an "
            "identifier that is not an accepted fact value is described in plain words instead"
        )
    return errors
