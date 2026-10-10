"""Bounds on the length of a section_authoring reply, applied to the schema it is decoded under.

The defect (Aspose.Cells-FOSS-for-Rust, 2026-10-10): a ``section_authoring`` call returned a
``hub:public_symbol:workbookmodel`` unit whose ``fact_ids`` repeated the four facts the slot may
cite until ``finish_reason length`` at 8,000 tokens, which fails the transaction with no re-ask
(``core/llm/jobs.py`` fails closed on truncation). The per-slot ``enum`` bounds what an entry may
be, not how many entries there are, and the decoder cannot enforce uniqueness (the gateway answers
HTTP 400 to ``uniqueItems``). A unit cannot legitimately cite more distinct facts than its slot may
cite, so that count is the array's ``maxItems``; likewise ``omitted`` lists each fact at most once.

This is a decoder constraint, never a judgment: a stored output is re-judged under the manifest's
static schema and the checks (``core/llm/jobs.py``), so no sealed output and no governed version
is touched. It lives beside ``authoring.py`` rather than in it only because that file is a
governed source and nothing here changes what it accepts.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import Any

from repository_presenter.components.readme.composition.authoring import SectionTask, citable


def omittable_count(tasks: Iterable[SectionTask]) -> int:
    """How many distinct facts a reply over ``tasks`` could list in ``omitted`` (each once)."""
    ids: set[str] = set()
    for task in tasks:
        ids |= set(task.accepted_ids) | set(task.must_carry)
        for facts in task.slot_facts.values():
            ids |= set(facts)
    return len(ids)


def largest_slot_citation_count(tasks: Iterable[SectionTask]) -> int:
    """The most distinct facts any one unit of ``tasks`` may cite: its slot's own set."""
    return max((len(citable(task, slot)) for task in tasks for slot in task.slots), default=1)


def bound_authoring_citations(schema: dict[str, Any], task: SectionTask) -> dict[str, Any]:
    """``schema`` (``authoring_schema``'s output for ``task``) with every unit's ``fact_ids`` and
    the ``omitted`` list capped at the number of distinct facts they can legitimately hold."""
    bounded = copy.deepcopy(schema)
    properties = bounded["properties"]
    positional = properties["units"].get("prefixItems")
    if positional is not None:
        for slot, item in zip(task.slots, positional, strict=True):
            item["properties"]["fact_ids"]["maxItems"] = max(len(citable(task, slot)), 1)
    if "omitted" in properties:
        properties["omitted"]["maxItems"] = omittable_count([task])
    return bounded
