"""Reconcile the existing README with the facts: one disposition per inherited unit.

The job receives every inherited unit, the SUPPORTED and CONTRADICTED facts (bounded), the
accepted investigation, and the shell's sections. Beyond the schema and the unit-ID binding, the
rules here run before the output is used. Deterministic sections (identity, badges, navigation,
installation, dependencies, third_party_notices, license) render from facts, so a unit the job
routes to one of them is normalised into SUPERSEDE_REDUNDANT citing the facts that section
renders - the job decided the unit is verified and where its substance belongs; deterministic
code decides that deterministic content is rendered, never copied. A placing disposition
otherwise needs a placeable destination, a correction cites its evidence, a supersession names
its section or cites facts, and a code block whose example is CONTRADICTED is never placed. A
violation is quoted back once; a second one fails the transaction closed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    placeable_section_ids,
    section_ids,
    shell_packet,
)
from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

DISPOSITIONS_FILENAME = "dispositions.json"
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
RENDERING_FACT_KINDS: dict[str, tuple[str, ...]] = {
    "identity": ("identity", "package"),
    "badges": ("link_target",),
    "navigation": ("identity",),
    "installation": ("install_command",),
    "dependencies": ("dependency",),
    "third_party_notices": ("third_party_notices",),
    "license": ("license",),
}
_UNIT_REFERENCE = re.compile(r"unit (inherited_unit:[0-9]+\.[a-z_]+)")


def reconciliation_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    manifest: PromptManifest,
) -> dict[str, Any]:
    units = [
        {"id": fact.id, "type": fact.id.rsplit(".", 1)[-1], "text": fact.value}
        for fact in facts.by_kind("inherited_unit")
    ]
    kinds = [kind for kind in manifest.packet.fact_kinds if kind != "inherited_unit"]
    return {
        "repository": entry.repository,
        "inherited_units": units,
        "facts": bounded_records(facts, kinds, ("SUPPORTED", "CONTRADICTED")),
        "investigation": investigation,
        "sections": shell_packet(),
    }


def contradicted_code_units(facts: FactsDocument) -> frozenset[str]:
    """Inherited code blocks whose example fact is CONTRADICTED, read from the example evidence."""
    units: set[str] = set()
    for fact in facts.by_kind("example"):
        if fact.polarity != "CONTRADICTED":
            continue
        for evidence in fact.evidence:
            match = _UNIT_REFERENCE.search(evidence.detail or "")
            if match:
                units.add(match.group(1))
    return frozenset(units)


def rendering_fact_ids(section: str, facts: FactsDocument) -> list[str]:
    """The SUPPORTED facts a deterministic section renders for this repository, by ID."""
    kinds = RENDERING_FACT_KINDS.get(section, ())
    return sorted(
        fact.id for fact in facts.facts if fact.kind in kinds and fact.polarity == "SUPPORTED"
    )


def normalize(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """Fold placements into deterministic sections into supersessions, in place.

    Returns the units that cannot be folded because the section renders nothing here.
    """
    deterministic = set(section_ids()) - placeable_section_ids()
    errors: list[str] = []
    for entry in output.get("dispositions", []):
        destination = entry.get("destination_section")
        if destination not in deterministic:
            continue
        ids = rendering_fact_ids(destination, facts)
        if not ids:
            errors.append(
                f"{entry.get('unit_id', '?')}: section {destination} renders nothing for this "
                "repository; choose OMIT_UNSUPPORTED or DEFER_UNRESOLVED"
            )
            continue
        entry["disposition"] = "SUPERSEDE_REDUNDANT"
        entry["fact_ids"] = sorted(set(entry.get("fact_ids") or []) | set(ids))
    return errors


def placement_errors(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """Why the dispositions may not be used, beyond schema and binding; empty when they hold."""
    placeable = placeable_section_ids()
    contradicted = contradicted_code_units(facts)
    errors: list[str] = []
    for entry in output.get("dispositions", []):
        unit = entry.get("unit_id", "?")
        disposition = entry.get("disposition")
        destination = entry.get("destination_section")
        cited = entry.get("fact_ids") or []
        if disposition in PLACING:
            if destination not in placeable:
                errors.append(
                    f"{unit}: {disposition} needs a destination the shell can hold "
                    f"({', '.join(sorted(placeable))}); got {destination!r}"
                )
            if unit in contradicted:
                errors.append(f"{unit}: its example is CONTRADICTED and cannot be placed")
        elif disposition == "SUPERSEDE_REDUNDANT":
            if destination is not None and destination in placeable:
                errors.append(
                    f"{unit}: SUPERSEDE_REDUNDANT names the deterministic section that renders "
                    f"the unit, never {destination!r}"
                )
            if not cited:
                errors.append(
                    f"{unit}: SUPERSEDE_REDUNDANT needs the deterministic section that renders "
                    "the unit in destination_section or at least one fact ID"
                )
        elif destination is not None:
            errors.append(f"{unit}: {disposition} takes no destination; got {destination!r}")
        if disposition == "CORRECT_WITH_EVIDENCE" and not cited:
            errors.append(f"{unit}: CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence")
    return errors


def reconcile_checks(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """The job's own checks for the runner: normalise, then judge what remains."""
    return normalize(output, facts) + placement_errors(output, facts)


def summarize(output: dict[str, Any]) -> Counter[str]:
    return Counter(entry["disposition"] for entry in output.get("dispositions", []))


def write_dispositions(output: dict[str, Any], path: Path) -> str:
    """Write the accepted dispositions as deterministic JSON; returns the SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
