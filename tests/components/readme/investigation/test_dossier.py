"""The investigation packet is bounded deterministically and its artifact is stable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.investigation.dossier import (
    UNIT_CAP,
    investigation_packet,
    investigation_schema,
    write_investigation,
)
from repository_presenter.core.facts import SYMBOL_CAP, Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "org/Aspose.Widget-FOSS-for-Python",
        "family": "widget",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
LOADED = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
MANIFEST = LOADED.manifest


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


def test_packet_admits_only_supported_facts_of_listed_kinds_bounded_as_documented() -> None:
    symbols = [
        _fact(f"public_symbol:pkg.mod.class{i}", "public_symbol", f"pkg.mod.Class{i}")
        for i in range(SYMBOL_CAP + 5)
    ]
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            _fact("identity:repository", "identity", ENTRY.repository),
            _fact("example:001", "example", "print(1)"),
            _fact("example:002", "example", "boom", "CONTRADICTED"),
            _fact("link_target:001", "link_target", "https://x"),
            _fact("public_symbol:pkg.mod.class.method", "public_symbol", "pkg.mod.Class.method"),
            *symbols,
            _fact("inherited_unit:001.heading", "inherited_unit", "# Title"),
            _fact("inherited_unit:002.code_block", "inherited_unit", "```py\n```"),
            _fact("inherited_unit:003.paragraph", "inherited_unit", "Prose."),
        ),
    )
    packet = investigation_packet(ENTRY, facts, MANIFEST)
    assert packet["repository"] == ENTRY.repository and packet["ecosystem"] == "python"
    ids = [entry["id"] for entry in packet["fact_dossier"]]
    assert ids[:2] == ["identity:repository", "example:001"]
    assert "example:002" not in ids and "link_target:001" not in ids
    assert "public_symbol:pkg.mod.class.method" not in ids
    assert sum(1 for i in ids if i.startswith("public_symbol:")) == SYMBOL_CAP
    assert packet["inherited_units"] == [
        {"id": "inherited_unit:001.heading", "type": "heading", "text": "# Title"},
        {"id": "inherited_unit:003.paragraph", "type": "paragraph", "text": "Prose."},
    ]
    assert investigation_packet(ENTRY, facts, MANIFEST) == packet


def test_inherited_units_are_bounded_at_a_value_larger_repositories_actually_need() -> None:
    """G4-W17 arrival item 27's own follow-up check. Found while confirming SYMBOL_CAP's shape
    was not repeated here: it was. Measured 2026-09-06, aspose-pdf-foss/Aspose.PDF-FOSS-for-
    TypeScript carries 272 headings, paragraphs and lists - `UNIT_CAP` was 80."""
    units = [
        _fact(f"inherited_unit:{i:03d}.paragraph", "inherited_unit", f"Paragraph {i}.")
        for i in range(UNIT_CAP + 5)
    ]
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (_fact("identity:repository", "identity", ENTRY.repository), *units),
    )
    packet = investigation_packet(ENTRY, facts, MANIFEST)
    assert len(packet["inherited_units"]) == UNIT_CAP
    assert packet["inherited_units"][0]["id"] == "inherited_unit:000.paragraph"


def test_the_artifact_is_deterministic_json(tmp_path: Path) -> None:
    output = {"b": 1, "a": {"text": "é", "fact_ids": ["identity:repository"]}}
    path = tmp_path / "t" / "investigation.json"
    digest = write_investigation(output, path)
    raw = path.read_bytes()
    expected = (
        b'{\n  "a": {\n    "fact_ids": [\n      "identity:repository"\n    ],\n'
        b'    "text": "\xc3\xa9"\n  },\n  "b": 1\n}\n'
    )
    assert raw == expected
    assert json.loads(raw) == output
    assert write_investigation(output, path) == digest


def test_investigation_schema_pins_every_fact_ids_array_to_the_packets_own_dossier() -> None:
    """G4-W17 arrival item 105 (E22). ``repository_investigation`` (S3) was the one fact-citing
    job with no ``call_schema`` at all, unlike ``source_reconciliation``/``presentation_planning``/
    ``section_authoring``, which all pin their ``fact_ids`` arrays via ``_pin_fact_id_arrays`` -
    so a hallucinated fact ID cost a live provider call before ``core/llm/binding.py``'s post-hoc
    ``binding_errors`` ever caught it. Measured on Words-Python: two live calls against a
    byte-identical request (temperature 0, seed 1) produced two different hallucinations. This
    proves the schema itself now refuses one at decode time, at all four sites -
    ``product_summary``/``audience``/``problems_solved``/``limitations`` share the one
    ``$defs.statement``, and ``workflows``/``capabilities`` carry their own inline field."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            _fact("identity:repository", "identity", ENTRY.repository),
            _fact("example:001", "example", "print(1)"),
        ),
    )
    schema = investigation_schema(LOADED, facts)
    assert set(schema["$defs"]["citable_fact_id"]["enum"]) == {
        "identity:repository",
        "example:001",
    }
    validator = Draft202012Validator(schema)

    def _output(fact_ids: list[str]) -> dict[str, Any]:
        statement = {"text": "t", "fact_ids": fact_ids}
        return {
            "product_summary": statement,
            "audience": statement,
            "problems_solved": [statement],
            "workflows": [{"name": "n", "text": "t", "fact_ids": fact_ids}],
            "capabilities": [{"title": "t", "text": "t", "fact_ids": fact_ids} for _ in range(3)],
            "limitations": [],
            "uncertainties": [],
        }

    # A real, dossier-carried ID: valid everywhere it is cited.
    assert list(validator.iter_errors(_output(["identity:repository"]))) == []
    # A well-formed fact ID this packet never showed (a sibling repository's own ID, the exact
    # measured Words-Python shape): refused at every one of the four sites, not silently accepted
    # until a live call was already spent.
    paths = {tuple(error.path) for error in validator.iter_errors(_output(["identity:revision"]))}
    assert ("product_summary", "fact_ids", 0) in paths
    assert ("audience", "fact_ids", 0) in paths
    assert ("problems_solved", 0, "fact_ids", 0) in paths
    assert ("workflows", 0, "fact_ids", 0) in paths
    assert ("capabilities", 0, "fact_ids", 0) in paths
    # Nothing citable pins every array empty, as S4/S5 already do, with no enum left to reference.
    empty = investigation_schema(LOADED, FactsDocument(ENTRY.repository, "a" * 40, ()))
    assert "citable_fact_id" not in empty.get("$defs", {})
    assert empty["$defs"]["statement"]["properties"]["fact_ids"] == {
        "type": "array",
        "maxItems": 0,
    }
    assert empty["properties"]["workflows"]["items"]["properties"]["fact_ids"] == {
        "type": "array",
        "maxItems": 0,
    }
    assert empty["properties"]["capabilities"]["items"]["properties"]["fact_ids"] == {
        "type": "array",
        "maxItems": 0,
    }
