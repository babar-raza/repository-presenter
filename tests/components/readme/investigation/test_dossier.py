"""The investigation packet is bounded deterministically and its artifact is stable."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.investigation.dossier import (
    investigation_packet,
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
MANIFEST = load_manifests(REPO_ROOT / "prompts")["repository_investigation"].manifest


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
