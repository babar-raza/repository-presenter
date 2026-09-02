"""Bind a job's output to the facts it cites: an unknown or contradicted ID rejects the output.

The guard is structural. It walks the output for every key that carries fact or unit IDs and
checks each against the facts document; it never reads prose. What each binding class requires:
``fact_ids``, ``selection_ids``, and ``revision_ids`` cite only SUPPORTED facts; ``finding_ids``
cite facts that exist (a finding may point at a contradicted fact as its evidence); ``unit_ids``
name every inherited unit exactly once.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from repository_presenter.core.facts import FactsDocument

Binding = str
_FACT_KEY_SUFFIXES = ("_fact_id", "_fact_ids", "_example_id", "_example_ids", "_format_ids")


@dataclass(frozen=True)
class CitedIds:
    fact_ids: tuple[str, ...]
    unit_ids: tuple[str, ...]


def _walk(payload: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk(item)


def _is_fact_key(key: str) -> bool:
    return key == "fact_ids" or key.endswith(_FACT_KEY_SUFFIXES)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def collect_ids(payload: Any) -> CitedIds:
    """Every fact ID and unit ID the output cites, in document order, duplicates kept."""
    fact_ids: list[str] = []
    unit_ids: list[str] = []
    for key, value in _walk(payload):
        if _is_fact_key(key):
            fact_ids.extend(_strings(value))
        elif key in {"unit_id", "unit_ids"}:
            unit_ids.extend(_strings(value))
    return CitedIds(tuple(fact_ids), tuple(unit_ids))


def binding_errors(payload: Any, facts: FactsDocument, binding: Binding) -> list[str]:
    """Why the output may not be used, or an empty list when every citation holds."""
    known = {fact.id: fact for fact in facts.facts}
    cited = collect_ids(payload)
    errors: list[str] = []
    require_supported = binding in {"fact_ids", "selection_ids", "revision_ids"}
    for fact_id in dict.fromkeys(cited.fact_ids):
        fact = known.get(fact_id)
        if fact is None:
            errors.append(f"unknown fact ID {fact_id}")
        elif require_supported and fact.polarity != "SUPPORTED":
            errors.append(f"fact {fact_id} is {fact.polarity}, not SUPPORTED")
    for unit_id in dict.fromkeys(cited.unit_ids):
        unit = known.get(unit_id)
        if unit is None or unit.kind != "inherited_unit":
            errors.append(f"unknown inherited unit {unit_id}")
    if binding == "unit_ids":
        expected = [fact.id for fact in facts.by_kind("inherited_unit")]
        counts = {unit_id: cited.unit_ids.count(unit_id) for unit_id in expected}
        missing = [unit_id for unit_id, count in counts.items() if count == 0]
        duplicated = [unit_id for unit_id, count in counts.items() if count > 1]
        if missing:
            errors.append(f"no disposition for inherited units: {', '.join(missing)}")
        if duplicated:
            errors.append(f"more than one disposition for: {', '.join(duplicated)}")
    return errors
