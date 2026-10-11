"""A list kept as written states every item: the section-authoring guard for partial preservation.

Cut-2 BC-10 triage, cause 5 (aspose-pdf-foss/Aspose.PDF-FOSS-for-Java 131.list: six limitation
bullets dropped; Cells-Java 048.list: three of five rendered; 3D-Java 072.list: two of its items
absent). Reconciliation marked the whole list ``VERIFIED_PRESERVE`` - facts support every claim in
it - and Scope and Limitations authors one slot per unit, so the composer condensed the list and
silently lost items. Every unit-level check passed (the unit *is* cited); only independent review
read the section against the source, and its repair was then blocked by BC-04 because a dropped
item names an identifier that is not a fact value.

This module is the earlier, deterministic answer: after ``section_authoring`` returns, every item
of each ``VERIFIED_PRESERVE``/``VERIFIED_MOVE`` list unit the section owes must be stated by the
section's units, or the reply is refused with the missing items named (the one re-ask can act on
them). Presence is judged on the subject words of an item's lead (its bold phrase, else its first
words), not on its exact text: the composer rewrites items from facts, so an item restated in other
words is present, and one described without an identifier BC-04 would refuse is still present.

It sits beside ``authoring.py`` rather than inside it so the change moves no governed constant;
``repair/rounds.py`` layers it onto ``unit_checks`` for the initial draft and for an S6 repair.

Wave-3 acceptance review (reseal f69f75c7, LST-01): the guard above still let the defect through
in five of five candidates, for three reasons it did not cover.

1. A list was checked only when the plan handed it to a slot, and the plan handed none of 3D Java's,
   3D TypeScript's, Cells Java's or 3D .NET's - while ``placement.placements`` dropped each as
   "overlap" because ONE of the facts it cites is covered by another limitation slot. The list was
   then neither authored nor printed, and the premise ("a list no slot carries is printed by
   placement as written") was false. ``planning.plan_checks`` now hands every such list to the
   limitation slots (and its links to the documentation slots), so the premise holds again.
2. A list was checked only when a unit cited it, so a composer that stated half of it without
   citing it passed; the check now binds a list the section owes whether or not anyone cites it.
3. A section whose slots the plan does not bind (Development and Testing) never had a list owed at
   all; ``SectionTask.owed_lists`` names the lists placement dropped there.

Documentation and Resources prints one authored line per link, so its items are links:
``missing_items(..., by_link=True)`` judges them by the link they carry (validation BC-05).
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Any

from repository_presenter.core.facts import FactsDocument

if TYPE_CHECKING:  # authoring imports this module; the task type is only a hint here
    from repository_presenter.components.readme.composition.authoring import SectionTask

LIST_ITEM_MISSING = "list_item_missing"
# The dispositions that keep a unit as written. A rewrite or a supersession is the composer's to
# condense; only a list the reconciler said stands as written owes every item.
_AS_WRITTEN = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+(.*)$")
_BOLD_LEAD = re.compile(r"^\s*(?:\*\*|__)(.+?)(?:\*\*|__)")
_LEAD_BREAK = re.compile(r"\s(?:-{1,2}|\u2013|\u2014)\s|:\s|\.\s|\(")
_LEAD_WORDS = 6
_CODE_LEAD_WORDS = 3
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
# A Markdown link destination; an in-page anchor names a heading, not a document.
_LINK_DESTINATION = re.compile(r"\]\(\s*<?([^)\s>]+)")
# The sections whose authored text owes every item of a list placement dropped from them: the
# limitation slots of Scope and Limitations (the plan hands the list to them) and Development and
# Testing's one unbound summary slot. Key Capabilities and API Reference slots are bound to one
# capability or hub each, so no unit could state a list's items; Documentation and Resources is
# judged by the link each item carries (validation BC-05).
OWED_SECTIONS = frozenset({"scope_limitations", "development_testing"})


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
    # An item that opens with a code span is about that identifier ("`NurbsCurve` exposes its full
    # data model, but sampling is not implemented"): its subject is the identifier and the words
    # right after it, not the whole clause, which no paraphrase repeats.
    limit = _CODE_LEAD_WORDS if head.lstrip().startswith("`") else _LEAD_WORDS
    return " ".join(head.split()[:limit])


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


def stems(text: str) -> set[str]:
    """The word stems this module compares text by (``composition/coverage.py`` reads the same
    test for a kept paragraph's sentences that BC-05 reads for a kept list's items, and
    ``validation/content_presence.py`` judges a deferred unit against the finished README)."""
    return _stems(text)


def item_links(item: str) -> list[str]:
    """The document links an item carries: its Markdown destinations other than in-page anchors."""
    return [dest for dest in _LINK_DESTINATION.findall(item) if not dest.startswith("#")]


def missing_items(
    unit_text: str,
    destination_text: str,
    *,
    by_link: bool = False,
    document_text: str = "",
) -> list[str]:
    """The items of ``unit_text`` whose subject the destination text never states.

    ``by_link`` judges an item that carries a document link by that link alone (it is stated when
    one of its destinations appears in ``document_text``): Documentation and Resources prints each
    link itself, from the fact, and an item's lead words are too common ("guide", "notes") to tell
    one link from another. An item with no such link falls back to its subject words.
    """
    destination = _stems(destination_text)
    missing: list[str] = []
    for item in list_items(unit_text):
        links = item_links(item) if by_link else []
        if links:
            if not any(link in document_text for link in links):
                missing.append(item)
            continue
        subject = _stems(_lead(item)) or _stems(item)
        if not subject:
            continue
        if len(subject & destination) < max(1, math.ceil(len(subject) * _PRESENT_SHARE)):
            missing.append(item)
    return missing


def _quote(item: str) -> str:
    plain = " ".join(item.replace("**", "").split())
    return plain if len(plain) <= _QUOTE_LIMIT else plain[:_QUOTE_LIMIT].rstrip() + "..."


def kept_lists(
    dispositions: Mapping[str, Any],
    section_id: str,
    owed: Collection[str],
    facts: FactsDocument,
) -> dict[str, str]:
    """The list units kept as written in ``section_id`` that its authored units owe in full:
    ``unit id -> the unit's inherited text``, restricted to ``owed`` - the lists the plan handed
    to one of the section's slots and the lists placement dropped from an unbound section."""
    texts = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    return {
        unit: texts[unit]
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") in _AS_WRITTEN
        and entry.get("destination_section") == section_id
        and (unit := str(entry.get("unit_id", ""))).endswith(".list")
        and unit in owed
        and unit in texts
        and len(list_items(texts[unit])) >= _MIN_ITEMS
    }


def handed_units(task: SectionTask) -> set[str]:
    """Every fact and unit ID the plan bound to one of ``task``'s slots."""
    return set().union(*task.slot_facts.values()) if task.slot_facts else set()


def kept_list_units(
    dispositions: Mapping[str, Any], task: SectionTask, facts: FactsDocument
) -> dict[str, str]:
    """The list units kept as written in ``task``'s section that its authored units owe in full:
    the lists the plan handed to a slot of the section, and the lists placement dropped from the
    section (``task.owed_lists``). A list neither is printed by placement as written, so no
    authored unit stands in for it."""
    return kept_lists(
        dispositions, task.section_id, handed_units(task) | set(task.owed_lists), facts
    )


def list_coverage_errors(
    output: Mapping[str, Any],
    task: SectionTask,
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
) -> list[str]:
    """One repairable refusal per kept list whose items the authored units do not all state."""
    errors: list[str] = []
    units = [unit for unit in output.get("units", []) if isinstance(unit, dict)]
    # The section's whole authored text, not only the units citing a list: the plan cites a
    # limitation's facts, not always the list unit its wording came from, and a composer that
    # states half a list without citing it still owes the other half.
    stated = " ".join(str(unit.get("text", "")) for unit in units)
    for unit_id, text in kept_list_units(dispositions, task, facts).items():
        missing = missing_items(text, stated)
        if not missing:
            continue
        citing = [
            str(unit.get("slot")) for unit in units if unit_id in (unit.get("fact_ids") or [])
        ]
        bound = [slot for slot, facts_of in task.slot_facts.items() if unit_id in facts_of]
        slots = ", ".join(citing or bound or list(task.slots))
        errors.append(
            f"{unit_id}: {LIST_ITEM_MISSING}: this list was kept as written, so every one of its "
            f"{len(list_items(text))} items must be stated by the units that cite it; "
            f"{len(missing)} not stated: "
            + "; ".join(f'"{_quote(item)}"' for item in missing)
            + f". Fold each into a unit citing {unit_id} ({slots}); an item that names an "
            "identifier that is not an accepted fact value is described in plain words instead"
        )
    return errors
