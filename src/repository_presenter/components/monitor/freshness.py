"""The 30-day freshness check (G7-W06, TC-REF-01-02): re-read the package registry and compare it
with what the sealed README's facts recorded. Zero provider calls: a registry GET through the
existing probe (``extractors/surface/registry.py::observe``), never a model.

A README can go stale with no upstream commit at all: the package is published, withdrawn or
released again on the registry. The head-change classification (``relevance.py``) cannot see that,
so a bundle older than ``FRESHNESS_MAX_AGE`` is re-checked here:

- a sealed ``package:published_version`` fact differing from the registry's current stable release
  is ``RELEVANT_CHANGE`` when the README consumes that fact (or the bundle does not say which facts
  it consumes), and ``IRRELEVANT_CHANGE`` when it does not;
- with no sealed version fact (every bundle sealed before it existed), the check compares only the
  published/not-found reading the sealed install evidence recorded; it never turns the mere absence
  of a recorded version into a change;
- a registry that cannot be read conclusively is ``UNKNOWN``, never a change.

Links are re-resolved by the validators at seal time, not here: a link probe is a different cost
class and this check stays one cheap, bounded read per package.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from repository_presenter.components.monitor.relevance import ChangeClass
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

FRESHNESS_MAX_AGE = timedelta(days=30)
PACKAGE_NAME_FACT_ID = "package:name"
_FOUND = "package registry: found"
_NOT_FOUND = "package registry: distribution not found"

Observe = Callable[..., Any]


@dataclass(frozen=True)
class FreshnessResult:
    change: ChangeClass
    detail: str | None = None
    # The check is a registry read, never a model call; recorded so the ledger can assert it.
    provider_calls: int = 0


def freshness_due(sealed_at: object, *, now: datetime | None = None) -> bool:
    """Whether a bundle sealed at ``sealed_at`` is past ``FRESHNESS_MAX_AGE``. An unreadable stamp
    is due (the check is a cheap registry read, so erring toward checking costs nothing)."""
    clock = now if now is not None else datetime.now(UTC)
    try:
        stamp = datetime.fromisoformat(str(sealed_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if stamp.tzinfo is None:
        return True
    return clock - stamp >= FRESHNESS_MAX_AGE


def _install_readings(facts: list[dict[str, Any]]) -> set[str]:
    readings: set[str] = set()
    for fact in facts:
        if not str(fact.get("id", "")).startswith("install_command:"):
            continue
        for evidence in fact.get("evidence") or ():
            detail = evidence.get("detail") if isinstance(evidence, dict) else None
            if isinstance(detail, str):
                if detail.startswith(_FOUND):
                    readings.add("found")
                elif detail.startswith(_NOT_FOUND):
                    readings.add("not_found")
    return readings


def _consumes(consumed_fact_ids: Collection[str] | None, fact_id: str) -> bool:
    return consumed_fact_ids is None or fact_id in consumed_fact_ids


def freshness_check(
    ecosystem: str,
    facts: list[dict[str, Any]],
    *,
    observe: Observe,
    consumed_fact_ids: Collection[str] | None = None,
) -> FreshnessResult:
    """Re-resolve the registry for the sealed package and compare it with the sealed facts."""
    by_id = {str(f.get("id")): f for f in facts}
    name_fact = by_id.get(PACKAGE_NAME_FACT_ID)
    if name_fact is None or name_fact.get("polarity") != "SUPPORTED":
        return FreshnessResult("NO_CHANGE", "no registry-backed package fact to re-check")
    name = str(name_fact.get("value"))
    try:
        reading = observe(ecosystem, name)
    except Exception as exc:  # a registry failure is a reading, never an abort
        return FreshnessResult("UNKNOWN", f"registry read failed: {type(exc).__name__}")
    if not getattr(reading, "conclusive", False):
        return FreshnessResult("UNKNOWN", f"{name}: the registry could not be read conclusively")
    sealed_version_fact = by_id.get(PUBLISHED_VERSION_FACT_ID)
    if sealed_version_fact is not None:
        sealed_version = str(sealed_version_fact.get("value"))
        if not reading.published:
            return FreshnessResult(
                "RELEVANT_CHANGE",
                f"{name} was published at {sealed_version}; the registry no longer lists it",
            )
        live_version = getattr(reading, "latest_version", None)
        if not live_version:
            return FreshnessResult("UNKNOWN", f"{name}: the registry named no stable release")
        if live_version == sealed_version:
            return FreshnessResult("NO_CHANGE")
        consumed = _consumes(consumed_fact_ids, PUBLISHED_VERSION_FACT_ID)
        return FreshnessResult(
            "RELEVANT_CHANGE" if consumed else "IRRELEVANT_CHANGE",
            f"{name}: registry release {sealed_version} -> {live_version}"
            + ("" if consumed else " (the README does not consume the published version)"),
        )
    sealed = _install_readings(facts)
    if "found" in sealed and not reading.published:
        return FreshnessResult(
            "RELEVANT_CHANGE", f"{name} was found on the registry; it is no longer listed"
        )
    if "not_found" in sealed and reading.published:
        return FreshnessResult(
            "RELEVANT_CHANGE", f"{name} was not on the registry; it is now published"
        )
    return FreshnessResult("NO_CHANGE")
