"""Bind a job's output to the facts it cites: an unknown or contradicted ID rejects the output.

The guard is structural. It walks the output for every key that carries fact or unit IDs and
checks each against the facts document; it never reads prose. What each binding class requires:
``fact_ids`` and ``selection_ids`` cite only SUPPORTED facts; ``revision_ids`` cite only SUPPORTED
facts in the repair's own changes, while its ``revised_output`` is bound by the causal stage's own
binding (a reconciliation repair may cite a contradicted fact for an omission exactly as a fresh
reply may); ``finding_ids`` cite facts that exist (a finding may point at a contradicted fact as
its evidence); ``unit_ids`` name every inherited unit exactly once.
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


def resolve_symbol_ids(payload: Any, facts: FactsDocument) -> list[tuple[str, str]]:
    """Rewrite, in place, a cited public_symbol ID the facts do not carry to the shortest
    SUPPORTED public_symbol ID with the same final name segment, and return the rewrites.

    A job names a symbol by the path it reads (``aspose.threed.LambertMaterial``) while the
    facts record it where it is defined (``aspose.threed.shading.LambertMaterial``) and again
    at each re-export; the shortest ID is the package-level export. A name no fact carries
    stays as cited and rejects the output as before.
    """
    known = {fact.id for fact in facts.facts}
    by_name: dict[str, list[str]] = {}
    for fact in facts.by_kind("public_symbol"):
        if fact.polarity == "SUPPORTED":
            by_name.setdefault(fact.id.rsplit(".", 1)[-1], []).append(fact.id)
    rewrites: dict[str, str] = {}

    def resolve(value: str) -> str:
        if value in known or not value.startswith("public_symbol:"):
            return value
        candidates = by_name.get(value.rsplit(".", 1)[-1], [])
        if not candidates:
            return value
        target = min(candidates, key=lambda i: (len(i), i))
        rewrites[value] = target
        return target

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if _is_fact_key(key) and isinstance(value, str):
                    node[key] = resolve(value)
                elif _is_fact_key(key) and isinstance(value, list):
                    node[key] = [resolve(v) if isinstance(v, str) else v for v in value]
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return sorted(rewrites.items())


def binding_errors(payload: Any, facts: FactsDocument, binding: Binding) -> list[str]:
    """Why the output may not be used, or an empty list when every citation holds."""
    known = {fact.id: fact for fact in facts.facts}
    if binding == "revision_ids" and isinstance(payload, dict):
        # The revised output is the causal stage's object and is bound by that stage's
        # binding in the repair checks; here only the repair's own citations are judged.
        payload = {key: value for key, value in payload.items() if key != "revised_output"}
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
