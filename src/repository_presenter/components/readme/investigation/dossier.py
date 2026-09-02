"""The bounded fact dossier the repository_investigation job receives, and its artifact.

Bounding is deterministic and recorded in code, not in the prompt: only SUPPORTED facts of the
kinds the manifest admits enter, public symbols bounded as core/facts.py documents; inherited
units enter as headings, paragraphs, and lists only, capped in document order. Nothing here
reads prose or decides what the product is.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

INVESTIGATION_FILENAME = "investigation.json"
UNIT_CAP = 80
_UNIT_TYPES = ("heading", "paragraph", "list")


def investigation_packet(
    entry: RegistryEntry, facts: FactsDocument, manifest: PromptManifest
) -> dict[str, Any]:
    """The packet for one repository: dossier and inherited units bounded as documented."""
    units: list[dict[str, str]] = []
    for fact in facts.by_kind("inherited_unit"):
        unit_type = fact.id.rsplit(".", 1)[-1]
        if unit_type not in _UNIT_TYPES or len(units) >= UNIT_CAP:
            continue
        units.append({"id": fact.id, "type": unit_type, "text": fact.value})
    return {
        "repository": entry.repository,
        "ecosystem": entry.ecosystem,
        "fact_dossier": bounded_records(facts, manifest.packet.fact_kinds),
        "inherited_units": units,
    }


def write_investigation(output: dict[str, Any], path: Path) -> str:
    """Write the accepted output as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
