"""The existing gates as M6 baseline detectors: BC-04 and BC-14, run on a pinned bundle.

This is the one module of the harness that imports the validation layer, because these detectors
ARE the gates whose corpus catch rate is the M6 baseline. It calls the gates' own check functions
(``_check_units``, ``_check_claims``) read-only on a ``Candidate`` assembled from the pinned bundle
files, with no write and no network. Metrics M1 to M5 never import it.

Catch is differential: a case is caught by a gate when the injected text produces a failure the
clean twin does not, because the sealed bundles already fail several checks unmodified.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from repository_presenter.components.readme.bundle.recheck import _tree_approximation
from repository_presenter.components.readme.composition.authoring import authoring_tasks
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems
from repository_presenter.components.readme.validation import registry as validation
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.loader import find_entry, load_registry

from .corpus import Case, Outcome
from .detectors import CLASSES, Detector, Subject, register
from .pinned import REPO_ROOT, PinnedBundle

REGISTRY_PATH = REPO_ROOT / "data" / "registry.json"


def facts_document(bundle: PinnedBundle) -> FactsDocument:
    payload = bundle.sealed.facts or {}
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**entry) for entry in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(facts),
    )


@lru_cache(maxsize=1)
def _registry() -> Any:
    return load_registry(REGISTRY_PATH)


def candidate_for(
    bundle: PinnedBundle,
    *,
    readme: str | None = None,
    units: Mapping[str, Any] | None = None,
) -> validation.Candidate:
    """The validator's input for a pinned bundle, optionally with another README or unit list."""
    known_ecosystems()  # registers the platform specs the renderer context needs
    facts = facts_document(bundle)
    entry = find_entry(_registry(), bundle.repository)
    if entry is None:
        raise LookupError(f"{bundle.repository} is not in data/registry.json")
    text = bundle.readme if readme is None else readme
    plan = bundle.plan or {}
    dispositions = bundle.sealed.dispositions or {}
    tasks = authoring_tasks(entry, facts, bundle.investigation or {}, dispositions, plan)
    return validation.Candidate(
        entry,
        facts,
        plan,
        dict(units) if units is not None else (bundle.content_units or {}),
        dispositions,
        text,
        None,
        facts.source_revision,
        None,
        _tree_approximation(text, facts),
        tasks,
    )


def gate_failures(candidate: validation.Candidate) -> dict[str, list[str]]:
    """The failure details of BC-04 and BC-14 for one candidate."""
    return {
        "BC-04": [f.detail for f in validation._check_units(candidate)],
        "BC-14": [f.detail for f in validation._check_claims(candidate)],
    }


def with_unit_text(bundle: PinnedBundle, section: str, slot: str, text: str) -> dict[str, Any]:
    """The bundle's content units with one unit's text replaced (a deep copy)."""
    units = copy.deepcopy(bundle.content_units or {})
    for unit in units.get("units", []):
        if unit.get("section") == section and unit.get("slot") == slot:
            unit["text"] = text
            return units
    raise LookupError(f"{bundle.repository} has no unit {section}/{slot}")


def differential(
    bundle: PinnedBundle,
    *,
    section: str | None,
    slot: str | None,
    clean_text: str,
    injected_text: str,
    readme_edit: tuple[str, str] | None = None,
) -> dict[str, list[str]]:
    """Per gate, the failure details the injected text adds over the clean twin.

    ``readme_edit`` is (snippet of the sealed README, its injected form): BC-14 reads the README,
    BC-04 the content unit (``section`` and ``slot`` None: a README-level case, units untouched).
    The clean twin is the sealed README with the clean unit text.
    """
    injected_readme = bundle.readme
    if readme_edit is not None:
        old, new = readme_edit
        if old not in bundle.readme:
            raise LookupError(f"{bundle.repository}: the README does not contain {old[:60]!r}")
        injected_readme = bundle.readme.replace(old, new, 1)
    clean_units = injected_units = None
    if section is not None and slot is not None:
        clean_units = with_unit_text(bundle, section, slot, clean_text)
        injected_units = with_unit_text(bundle, section, slot, injected_text)
    clean = gate_failures(candidate_for(bundle, units=clean_units))
    injected = gate_failures(candidate_for(bundle, readme=injected_readme, units=injected_units))
    return {gate: [d for d in injected[gate] if d not in clean[gate]] for gate in injected}


def _no_text_run(subject: Subject) -> list[str]:
    return []


GATES = ("BC-04", "BC-14")
for _gate in GATES:
    register(Detector(_gate, tuple(CLASSES), _no_text_run, gate=True))
# The reviewer is a live detector (a model call): registered so the interface lists it, never run
# by the harness, never in CI, never ratcheted (M6r is run by a committed command, three times).
register(Detector("reviewer", tuple(CLASSES), _no_text_run, gate=True, deterministic=False))


def gate_outcomes(case: Case, bundle: PinnedBundle) -> dict[str, Outcome]:
    """BC-04 and BC-14 on a case: caught when the injected text adds a failure over the twin."""
    if case.level == "ledger":
        return {}
    readme_edit = case.readme_edit
    if readme_edit is None and case.level == "unit" and case.clean in bundle.readme:
        readme_edit = (case.clean, case.injected)
    unit = case.level == "unit"
    added = differential(
        bundle,
        section=case.section if unit else None,
        slot=case.slot if unit else None,
        clean_text=case.clean,
        injected_text=case.injected,
        readme_edit=readme_edit,
    )
    return {gate: Outcome(bool(found), False, tuple(found[:2])) for gate, found in added.items()}
