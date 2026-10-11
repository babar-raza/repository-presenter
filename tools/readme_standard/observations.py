"""Count an observation over the survey: a tiny, closed predicate language over feature records.

Every frequency docs/README_STANDARD.md quotes is an *observation*: a filter (``among``) that
selects the population, a filter (``where``) that selects the matching members, and the two counts
recomputed from ``data/readme_standard/survey.json``. A condition is a feature name (dotted for
nested values) mapped to a literal, which means equality, or to a mapping of operators:
``gte`` ``lte`` ``gt`` ``lt`` ``contains`` ``startswith`` ``nonempty`` ``in`` ``not``. Keys
combine with AND.
Nothing here evaluates text, so a data file can never run code.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

OPERATORS = ("gte", "lte", "gt", "lt", "contains", "startswith", "nonempty", "in", "not")


def lookup(row: Mapping[str, Any], path: str) -> Any:
    """The value at a dotted ``path`` in ``row``, or ``None`` when any step is missing."""
    current: Any = row
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def _holds(value: Any, operator: str, argument: Any) -> bool:
    if operator == "nonempty":
        return bool(value) == bool(argument)
    if operator == "not":
        return bool(value != argument)
    if value is None:
        return False
    if operator == "gte":
        return bool(value >= argument)
    if operator == "lte":
        return bool(value <= argument)
    if operator == "gt":
        return bool(value > argument)
    if operator == "lt":
        return bool(value < argument)
    if operator == "contains":
        return argument in value
    if operator == "startswith":
        return str(value).startswith(argument)
    if operator == "in":
        return value in argument
    raise ValueError(f"unknown operator {operator!r}")


def condition_holds(value: Any, condition: Any) -> bool:
    """One feature value against a literal or an operator mapping."""
    if isinstance(condition, Mapping):
        return all(_holds(value, op, arg) for op, arg in condition.items())
    return bool(value == condition)


def matches(row: Mapping[str, Any], where: Mapping[str, Any]) -> bool:
    """True when every condition in ``where`` holds for ``row``."""
    return all(condition_holds(lookup(row, key), cond) for key, cond in where.items())


STATISTICS = ("count", "min", "max", "median", "mean")


def compute_statistic(
    rows: Mapping[str, Mapping[str, Any]],
    feature: str,
    statistic: str,
    among: Mapping[str, Any] | None = None,
) -> float | None:
    """min, max, median or mean (one decimal) of a numeric feature over the selected READMEs."""
    values = [
        lookup(row, feature)
        for row in rows.values()
        if row.get("readme") and matches(row, among or {})
    ]
    numbers = sorted(
        float(v) for v in values if isinstance(v, int | float) and not isinstance(v, bool)
    )
    if not numbers:
        return None
    if statistic == "count":
        return float(len(numbers))
    if statistic == "min":
        return round(numbers[0], 1)
    if statistic == "max":
        return round(numbers[-1], 1)
    if statistic == "median":
        middle = len(numbers) // 2
        if len(numbers) % 2:
            return round(numbers[middle], 1)
        return round((numbers[middle - 1] + numbers[middle]) / 2, 1)
    if statistic == "mean":
        return round(sum(numbers) / len(numbers), 1)
    raise ValueError(f"unknown statistic {statistic!r}")


def count_observation(
    rows: Mapping[str, Mapping[str, Any]],
    where: Mapping[str, Any],
    among: Mapping[str, Any] | None = None,
) -> tuple[int, int]:
    """(members matching ``where``, population selected by ``among``), README-bearing rows only."""
    population = [row for row in rows.values() if row.get("readme") and matches(row, among or {})]
    return sum(1 for row in population if matches(row, where)), len(population)
