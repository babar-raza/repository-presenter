"""Reconciliation: a bounded packet in, placement rules checked before use, a stable artifact."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.reconciliation.dispositions import (
    contradicted_code_units,
    normalize,
    placement_errors,
    reconcile_checks,
    reconciliation_packet,
    rendering_fact_ids,
    summarize,
    write_dispositions,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
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
MANIFEST = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"].manifest


def _fact(
    fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", detail: str = ""
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", detail or None),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("format:input.obj", "format", ".obj", "UNRESOLVED"),
        _fact("install_command:pip", "install_command", "pip install widget", "CONTRADICTED"),
        _fact(
            "example:001",
            "example",
            "print(1)",
            detail="lines 5-7; python fence; unit inherited_unit:003.code_block",
        ),
        _fact(
            "example:002",
            "example",
            "boom",
            "CONTRADICTED",
            "lines 9-11; python fence; unit inherited_unit:004.code_block",
        ),
        _fact("inherited_unit:001.heading", "inherited_unit", "# Widget"),
        _fact("inherited_unit:002.paragraph", "inherited_unit", "Prose."),
        _fact("inherited_unit:003.code_block", "inherited_unit", "```python\nprint(1)\n```"),
        _fact("inherited_unit:004.code_block", "inherited_unit", "```python\nboom\n```"),
    ),
)


def _entry(
    unit: str, disposition: str, destination: str | None, *fact_ids: str
) -> dict[str, object]:
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": list(fact_ids),
        "rationale": "because",
    }


def test_the_packet_carries_every_unit_the_polar_facts_and_the_shell() -> None:
    packet = reconciliation_packet(ENTRY, FACTS, {"product_summary": {}}, MANIFEST)
    assert packet["repository"] == ENTRY.repository
    assert [unit["id"] for unit in packet["inherited_units"]] == [
        "inherited_unit:001.heading",
        "inherited_unit:002.paragraph",
        "inherited_unit:003.code_block",
        "inherited_unit:004.code_block",
    ]
    assert packet["inherited_units"][2]["type"] == "code_block"
    by_id = {record["id"]: record for record in packet["facts"]}
    assert set(by_id) == {
        "identity:repository",
        "install_command:pip",
        "example:001",
        "example:002",
    }
    assert by_id["install_command:pip"]["polarity"] == "CONTRADICTED"
    assert "inherited_unit:001.heading" not in by_id
    assert packet["investigation"] == {"product_summary": {}}
    assert [section["id"] for section in packet["sections"]][:2] == ["identity", "badges"]
    assert reconciliation_packet(ENTRY, FACTS, {"product_summary": {}}, MANIFEST) == packet


def test_placements_into_deterministic_sections_fold_into_supersessions() -> None:
    assert rendering_fact_ids("installation", FACTS) == []
    assert rendering_fact_ids("identity", FACTS) == ["identity:repository"]
    output = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "VERIFIED_PRESERVE", "identity"),
            _entry("inherited_unit:002.paragraph", "SUPERSEDE_REDUNDANT", "identity"),
            _entry("inherited_unit:003.code_block", "CORRECT_WITH_EVIDENCE", "installation"),
            _entry("inherited_unit:004.code_block", "SUPERSEDE_REDUNDANT", None),
        ]
    }
    errors = normalize(output, FACTS)
    assert errors == [
        "inherited_unit:003.code_block: section installation renders nothing for this "
        "repository; choose OMIT_UNSUPPORTED or DEFER_UNRESOLVED"
    ]
    folded = output["dispositions"]
    assert folded[0]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert folded[0]["fact_ids"] == ["identity:repository"]
    assert folded[0]["destination_section"] == "identity"
    assert folded[1]["fact_ids"] == ["identity:repository"]
    assert folded[2]["disposition"] == "CORRECT_WITH_EVIDENCE"
    remaining = placement_errors(output, FACTS)
    assert remaining == [
        "inherited_unit:003.code_block: CORRECT_WITH_EVIDENCE needs a destination the shell can "
        "hold (additional_examples, api_reference, at_a_glance, development_testing, "
        "documentation_resources, enterprise_relationship, key_capabilities, opening, "
        "quick_start, scope_limitations); got 'installation'",
        "inherited_unit:003.code_block: CORRECT_WITH_EVIDENCE needs at least one fact ID as "
        "evidence",
        "inherited_unit:004.code_block: SUPERSEDE_REDUNDANT needs the deterministic section that "
        "renders the unit in destination_section or at least one fact ID",
    ]
    assert reconcile_checks(output, FACTS) == errors + remaining


def test_placement_rules_are_checked_before_use() -> None:
    assert contradicted_code_units(FACTS) == {"inherited_unit:004.code_block"}
    good = {
        "dispositions": [
            _entry(
                "inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", None, "identity:repository"
            ),
            _entry("inherited_unit:002.paragraph", "VERIFIED_REWRITE", "opening"),
            _entry(
                "inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start", "example:001"
            ),
            _entry("inherited_unit:004.code_block", "OMIT_UNSUPPORTED", None, "example:002"),
        ]
    }
    assert placement_errors(good, FACTS) == []
    bad = {
        "dispositions": [
            _entry("inherited_unit:001.heading", "SUPERSEDE_REDUNDANT", None),
            _entry("inherited_unit:002.paragraph", "VERIFIED_MOVE", "installation"),
            _entry("inherited_unit:003.code_block", "DEFER_UNRESOLVED", "quick_start"),
            _entry("inherited_unit:004.code_block", "VERIFIED_PRESERVE", "quick_start"),
        ]
    }
    errors = placement_errors(bad, FACTS)
    assert errors[0] == (
        "inherited_unit:001.heading: SUPERSEDE_REDUNDANT needs the deterministic section that "
        "renders the unit in destination_section or at least one fact ID"
    )
    assert errors[1].startswith(
        "inherited_unit:002.paragraph: VERIFIED_MOVE needs a destination the shell can hold ("
    )
    assert errors[1].endswith("); got 'installation'")
    assert (
        errors[2]
        == "inherited_unit:003.code_block: DEFER_UNRESOLVED takes no destination; got 'quick_start'"
    )
    assert (
        errors[3]
        == "inherited_unit:004.code_block: its example is CONTRADICTED and cannot be placed"
    )
    assert dict(summarize(good)) == {
        "SUPERSEDE_REDUNDANT": 1,
        "VERIFIED_REWRITE": 1,
        "VERIFIED_PRESERVE": 1,
        "OMIT_UNSUPPORTED": 1,
    }


def test_the_artifact_is_deterministic_json(tmp_path: Path) -> None:
    output = {"dispositions": [_entry("inherited_unit:001.heading", "NON_CONTENT", None)]}
    path = tmp_path / "t" / "dispositions.json"
    digest = write_dispositions(output, path)
    raw = path.read_bytes()
    assert raw.startswith(b'{\n  "dispositions": [\n    {\n      "destination_section": null,')
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert json.loads(raw) == output
    assert write_dispositions(output, path) == digest
