"""The item test for a list kept as written: which of its items a destination section states.

Cut-2 BC-10 triage, cause 5 (aspose-pdf-foss/Aspose.PDF-FOSS-for-Java 131.list: six limitation
bullets dropped; Cells-Java 048.list: three of five rendered; 3D-Java 072.list: two of its items
absent). Reconciliation marked the whole list ``VERIFIED_PRESERVE`` - facts support every claim in
it - and Scope and Limitations authors one slot per unit, so the composer condensed the list and
silently lost items; wave-3 LST-01 found the placement rule that dropped it on one shared fact.

Presence is judged on the subject words of an item's lead (its bold phrase, else its first
words) or on the words only that item says, not on its exact text: the composer rewrites items
from facts, so an item restated in other words is present, and one described without an
identifier BC-04 would refuse is still present. The second test is what spares a bold label the
composer folds into its sentences without repeating ("Out of scope for v1", "Protocol"): judged by
the label alone, five restated lists of the wave-4 run were refused (triage, cause 1). It counts
only the words the item does not share with its siblings - "throw Error not implemented in this
FOSS build" repeats down a whole limitations list and proves nothing about any one item - and over
every archived reply the restated lists keep 0.61-0.92 of them where the items really dropped keep
0.00-0.32.

Three callers read the one test, so they cannot disagree about what "states an item" means:

* ``composition/coverage.py`` - placement drops a kept list only for the items its destination
  states, and prints the rest as written (wave-4 cut 4, L-r3), so no item reaches nowhere;
* validation BC-05 - the independent check that the finished section states every item of a list
  placement dropped (``missing_items(..., by_link=True)`` judges Documentation and Resources by the
  link each item carries);
* ``composition/authoring.py`` - the objective names the lists a section's units may fold into
  their own words (``kept_lists``).

Authoring no longer refuses a reply that leaves an item unstated (wave-4 triage, cause 1): placement
already prints what the units do not state, so the refusal only turned a list longer than its slots
(3D .NET, PDF .NET: 8 and 16 items for seven slots) and an item naming an identifier that is not a
fact value (Email .NET, Imaging .NET: `Microsoft.NET.Test.Sdk`) into a deadlock with the identifier
gate - naming the package is a stray identifier, describing it in words is a missing item. Replayed
through the real renderer on the last archived reply of eleven repositories with the refusal removed
(3D .NET, 3D Java, PDF .NET, PDF Java, Email .NET, Imaging .NET, PSD .NET and the four JMAP
libraries of this README structure), placement printed every item the units left unstated (PDF
.NET: three of sixteen) and BC-05 found none missing in any of them.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Collection, Mapping
from typing import Any

from repository_presenter.core.facts import FactsDocument

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
_MIN_ITEMS = 2
# A Markdown link destination; an in-page anchor names a heading, not a document.
_LINK_DESTINATION = re.compile(r"\]\(\s*<?([^)\s>]+)")
# The sections whose authored text is told of the lists placement dropped from them, to fold their
# items in: the limitation slots of Scope and Limitations (the plan hands the list to them) and
# Development and Testing's one unbound summary slot. Key Capabilities and API Reference slots are
# bound to one capability or hub each, so no unit could state a list's items; Documentation and
# Resources is judged by the link each item carries (validation BC-05).
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
    items = list_items(unit_text)
    said_by = Counter(stem for item in items for stem in _stems(item))
    missing: list[str] = []
    for item in items:
        links = item_links(item) if by_link else []
        if links:
            if not any(link in document_text for link in links):
                missing.append(item)
            continue
        lead, whole = _stems(_lead(item)), _stems(item)
        if not (lead or whole):
            continue
        # What only this item says: a word every item of the list repeats ("not implemented",
        # the product's name) shows nothing about this one.
        own = {stem for stem in whole if said_by[stem] == 1} or whole
        if not (_shares(lead, destination) or _shares(own, destination)):
            missing.append(item)
    return missing


def _shares(subject: set[str], destination: set[str]) -> bool:
    """Whether the destination holds at least ``_PRESENT_SHARE`` of ``subject``'s stems."""
    return bool(subject) and len(subject & destination) >= max(
        1, math.ceil(len(subject) * _PRESENT_SHARE)
    )


def kept_lists(
    dispositions: Mapping[str, Any],
    section_id: str,
    owed: Collection[str],
    facts: FactsDocument,
) -> dict[str, str]:
    """The list units kept as written in ``section_id`` that its authored units may fold into their
    own words: ``unit id -> the unit's inherited text``, restricted to ``owed`` - the lists the plan
    handed to one of the section's slots and the lists placement dropped from an unbound section."""
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
