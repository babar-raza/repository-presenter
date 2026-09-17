"""The bounded fact dossier the repository_investigation job receives, and its artifact.

Bounding is deterministic and recorded in code, not in the prompt: only SUPPORTED facts of the
kinds the manifest admits enter, public symbols bounded as core/facts.py documents; inherited
units enter as headings, paragraphs, and lists only, capped in document order. Nothing here
reads prose or decides what the product is.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

INVESTIGATION_FILENAME = "investigation.json"
# The same shape as core/facts.py's SYMBOL_CAP (G4-W17 arrival item 27), found while checking
# whether it was also silently truncating: capped in document order, so a long original README's
# later headings, paragraphs and lists never reach investigation at all. Measured 2026-09-06:
# aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript carries 272 of these three types, and
# aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp already exceeded the old 80 at 83 - the smallest
# overflow measured this session, not the largest. Raised with headroom over the observed
# maximum, the same threshold rule (section 27.10 follow-up 3) item 27 already applied.
UNIT_CAP = 400
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


def investigation_schema(loaded: LoadedManifest, facts: FactsDocument) -> dict[str, Any]:
    """The investigation schema specialised for this repository: every ``fact_ids`` array a
    statement, workflow, or capability writes is pinned to an enum of the packet's own
    ``fact_dossier`` - the same IDs ``investigation_packet`` shows, computed the same way.

    G4-W17 arrival item 105 (E22): ``repository_investigation`` (S3) was the one fact-citing job
    with no ``call_schema`` at all, unlike ``source_reconciliation``/``presentation_planning``/
    ``section_authoring``, which all pin their ``fact_ids`` arrays via ``_pin_fact_id_arrays`` -
    so a hallucinated fact ID cost a live provider call before ``core/llm/binding.py``'s post-hoc
    ``binding_errors`` ever caught it, spending the job's one re-ask budget before anything
    narrower could help. Measured on Words-Python: two live calls against a byte-identical
    request (temperature 0, seed 1) produced two different hallucinations, both real evidenced
    claims cited under the wrong exact ID.

    S3 is the first fact-citing job: there is no investigation or dispositions output yet to
    build a narrower ``citable_fact_ids``-style set from (``planning_schema``'s own set widens
    with exactly those two), so the enum here is the packet's own ``fact_dossier`` -
    ``bounded_records`` bounded the same way ``investigation_packet`` already bounds it, nothing
    wider.

    ``product_summary``, ``audience``, every ``problems_solved`` item, and every ``limitations``
    item all share the one ``$defs.statement`` schema via ``$ref``, so pinning it once pins all
    four; ``workflows`` and ``capabilities`` each carry their own inline ``fact_ids`` field and
    are pinned directly, the same shape ``_pin_fact_id_arrays`` already uses for a top-level
    array of objects.
    """
    schema = copy.deepcopy(loaded.manifest.output.schema_)
    dossier_ids = sorted(
        record["id"] for record in bounded_records(facts, loaded.manifest.packet.fact_kinds)
    )
    defs = schema.setdefault("$defs", {})
    if dossier_ids:
        defs["citable_fact_id"] = {"type": "string", "enum": dossier_ids}

    def _pin(field_properties: dict[str, Any]) -> None:
        if "fact_ids" not in field_properties:
            return
        if dossier_ids:
            field_properties["fact_ids"]["items"] = {"$ref": "#/$defs/citable_fact_id"}
            field_properties["fact_ids"]["maxItems"] = len(dossier_ids)
        else:
            field_properties["fact_ids"] = {"type": "array", "maxItems": 0}

    _pin(defs.get("statement", {}).get("properties", {}))
    properties = schema["properties"]
    _pin(properties.get("workflows", {}).get("items", {}).get("properties", {}))
    _pin(properties.get("capabilities", {}).get("items", {}).get("properties", {}))
    return schema


def write_investigation(output: dict[str, Any], path: Path) -> str:
    """Write the accepted output as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
