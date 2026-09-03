"""Defects route to the stage a repair may revise, once per fingerprint, and a repair is held to
the causal stage's own contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.repair.targeted import (
    EVIDENCE_REASON,
    Defect,
    RepairLedger,
    defect_fingerprint,
    repair_checks,
    repair_packet,
    review_defects,
    validation_defects,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
MANIFESTS = load_manifests(REPO_ROOT / "prompts")
FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),
        Fact("format:output.glb", "format", ".glb", (Evidence("x"),)),
        Fact("format:input.obj", "format", ".obj", (Evidence("x"),), polarity="UNRESOLVED"),
        Fact("inherited_unit:001.paragraph", "inherited_unit", "Old.", (Evidence("x"),)),
    ),
)
LLM_SECTIONS = {"opening", "key_capabilities", "scope_limitations"}


def _finding(label: str, section: str, stage: str, *fact_ids: str) -> dict[str, Any]:
    return {
        "id": label,
        "section_id": section,
        "causal_stage": stage,
        "criterion": "factuality",
        "text": "t",
        "quote": "",
        "fact_ids": list(fact_ids),
        "repair": "r",
    }


def test_review_findings_route_to_the_stage_a_repair_may_revise() -> None:
    review = {
        "findings": [
            _finding("F01", "opening", "S6"),
            _finding("F02", "opening", "S8"),
            _finding("F03", "opening", "S2", "identity:repository"),
            _finding("F04", "opening", "S2", "format:input.obj"),
            _finding("F05", "opening", "S2"),
            _finding("F06", "installation", "S7"),
            _finding("F07", "scope_limitations", "S4"),
            _finding("F08", "key_capabilities", "S5"),
            _finding("F09", "opening", "S3"),
        ]
    }
    defects = {d.label: d for d in review_defects(review, FACTS, LLM_SECTIONS)}
    assert defects["F01"].stage == "S6" and defects["F01"].repairable
    assert defects["F02"].stage == "S6"
    assert defects["F03"].stage == "S6" and defects["F03"].reason is None
    assert defects["F04"].stage is None and defects["F04"].reason == EVIDENCE_REASON
    assert defects["F05"].stage is None and defects["F05"].reason == EVIDENCE_REASON
    assert defects["F06"].stage is None and "deterministic" in str(defects["F06"].reason)
    assert defects["F07"].stage == "S4" and defects["F08"].stage == "S5"
    assert defects["F09"].stage == "S3"
    # Equivalent targets share a fingerprint; the label and the named stage do not matter.
    assert defects["F01"].fingerprint == defects["F02"].fingerprint == defects["F03"].fingerprint
    assert defects["F01"].fingerprint != defects["F07"].fingerprint
    assert defects["F01"].fingerprint == defect_fingerprint("review", "opening", "S6", "factuality")


def test_validation_failures_route_by_causal_state_and_named_section() -> None:
    validation = {
        "checks": [
            {"id": "BC-01", "verdict": "PASS", "causal_stage": None, "details": []},
            {"id": "BC-02", "verdict": "FAIL", "causal_stage": "EXTRACTING", "details": ["x"]},
            {
                "id": "BC-04",
                "verdict": "FAIL",
                "causal_stage": "COMPOSING",
                "details": ["opening/opening cites unknown fact f", "other"],
            },
            {"id": "BC-05", "verdict": "FAIL", "causal_stage": "RECONCILING", "details": ["u"]},
            {"id": "BC-07", "verdict": "FAIL", "causal_stage": "COMPOSING", "details": ["h1"]},
            {"id": "BC-09", "verdict": "FAIL", "causal_stage": None, "details": ["secret"]},
        ]
    }
    defects = {d.label: d for d in validation_defects(validation, LLM_SECTIONS)}
    assert set(defects) == {"BC-02", "BC-04", "BC-05", "BC-07", "BC-09"}
    assert defects["BC-02"].stage is None and "EXTRACTING" in str(defects["BC-02"].reason)
    assert defects["BC-04"].stage == "S6" and defects["BC-04"].section_id == "opening"
    assert defects["BC-05"].stage == "S4" and defects["BC-05"].section_id is None
    assert defects["BC-07"].stage is None and "names no LLM-owned section" in str(
        defects["BC-07"].reason
    )
    assert defects["BC-09"].stage is None and "the bundle" in str(defects["BC-09"].reason)
    assert defects["BC-04"].record["details"] == ["opening/opening cites unknown fact f", "other"]


def test_the_ledger_records_each_fingerprint_once_and_survives_reload(tmp_path: Path) -> None:
    ledger = RepairLedger(tmp_path / "repairs.json")
    defect = Defect("abc", "review", "F01", "opening", "S6", {"id": "F01"})
    assert not ledger.attempted("abc")
    ledger.record(defect, "repaired", "r" * 64, [{"id": "R01"}])
    ledger.record(Defect("def", "review", "F02", "installation", None, {}, "why"), "unrepairable")
    reloaded = RepairLedger(tmp_path / "repairs.json")
    assert reloaded.attempted("abc") and reloaded.attempted("def")
    assert reloaded.attempts["abc"]["changes"] == [{"id": "R01"}]
    assert reloaded.attempts["def"] == {
        "source": "review",
        "label": "F02",
        "section_id": "installation",
        "stage": None,
        "outcome": "unrepairable",
        "reason": "why",
        "request_sha256": None,
        "changes": [],
    }
    assert reloaded.summary() == "1 repaired (F01 S6 opening), 1 unrepairable recorded advisory"
    data = (tmp_path / "repairs.json").read_bytes()
    assert data.endswith(b"}\n") and list(json.loads(data)) == ["attempts", "schema_version"]


def test_the_packet_matches_the_manifest_and_a_repair_is_held_to_the_causal_contract() -> None:
    authoring = MANIFESTS["section_authoring"]
    defect = Defect(
        defect_fingerprint("review", "opening", "S6", "factuality"),
        "review",
        "F01",
        "opening",
        "S6",
        _finding("F01", "opening", "S6"),
    )
    stage_output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "Old.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    packet = repair_packet(
        ENTRY, defect, stage_output, FACTS, ["the H1"], authoring.manifest.output.schema_
    )
    assert set(packet) == MANIFESTS["targeted_repair"].manifest.packet.names
    assert packet["defect"]["fingerprint"] == defect.fingerprint
    assert [r["id"] for r in packet["facts"]] == ["identity:repository", "format:output.glb"]
    assert packet["causal_stage"] == "S6" and packet["preserve"] == ["the H1"]

    def stage_checks(output: dict[str, Any]) -> list[str]:
        return ["slot missing"] if not output["units"] else []

    good = {
        "fingerprint": defect.fingerprint,
        "causal_stage": "S6",
        "revised_output": {
            "units": [
                {
                    "section": "opening",
                    "slot": "opening",
                    "text": "New.",
                    "fact_ids": ["identity:repository"],
                }
            ],
            "omitted": [],
        },
        "changes": [
            {
                "id": "R01",
                "path": "$.units[0].text",
                "before": "Old.",
                "after": "New.",
                "fact_ids": [],
            }
        ],
    }
    contract = authoring.manifest.output.schema_
    assert repair_checks(good, defect, contract, "fact_ids", FACTS, stage_checks) == []
    bad = {
        **good,
        "causal_stage": "S5",
        "fingerprint": "other",
        "revised_output": {
            "units": [
                {
                    "section": "opening",
                    "slot": "opening",
                    "text": "x",
                    "fact_ids": ["format:input.obj"],
                }
            ]
        },
    }
    assert repair_checks(bad, defect, contract, "fact_ids", FACTS, stage_checks) == [
        "causal_stage must be S6; got 'S5'",
        f"fingerprint must be the defect's own ({defect.fingerprint})",
        "revised_output: 'omitted' is a required property",
        "revised_output: fact format:input.obj is UNRESOLVED, not SUPPORTED",
    ]
    empty = {**good, "revised_output": {"units": [], "omitted": []}}
    errors = repair_checks(empty, defect, contract, "fact_ids", FACTS, stage_checks)
    assert errors == ["revised_output.units: [] should be non-empty"]
    assert repair_checks({**good, "revised_output": "x"}, defect, contract, "fact_ids", FACTS) == [
        "revised_output must be the causal stage's output object"
    ]
