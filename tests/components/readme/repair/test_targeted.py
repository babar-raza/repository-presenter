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
    merge_equivalent,
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
            _finding("F10", "installation", "S2"),
        ]
    }
    defects = {d.label: d for d in review_defects(review, FACTS, LLM_SECTIONS)}
    assert defects["F01"].stage == "S6" and defects["F01"].repairable
    assert defects["F02"].stage == "S6"
    # An evidence finding in an authored section is an authoring matter either way.
    assert defects["F03"].stage == "S6" and defects["F03"].reason is None
    assert defects["F04"].stage == "S6" and defects["F05"].stage == "S6"
    assert defects["F10"].stage is None and defects["F10"].reason == EVIDENCE_REASON
    assert defects["F06"].stage is None and "deterministic" in str(defects["F06"].reason)
    assert defects["F07"].stage == "S4" and defects["F08"].stage == "S5"
    assert defects["F09"].stage == "S3"
    # Equivalent targets share a fingerprint; the label and the named stage do not matter.
    assert defects["F01"].fingerprint == defects["F02"].fingerprint == defects["F03"].fingerprint
    assert defects["F01"].fingerprint != defects["F07"].fingerprint
    assert defects["F01"].fingerprint == defect_fingerprint(
        "review", "opening", "S6", "factuality", "|"
    )
    # A changed reviewer prompt is a changed mechanism: the same target may be attempted again.
    rejudged = review_defects(
        {**review, "reviewer": {"prompt_sha256": "x" * 64}}, FACTS, LLM_SECTIONS
    )
    assert rejudged[0].fingerprint != defects["F01"].fingerprint
    assert rejudged[0].fingerprint == defect_fingerprint(
        "review", "opening", "S6", "factuality", "x" * 64 + "|"
    )
    # So is a changed repair prompt.
    repaired_differently = review_defects(review, FACTS, LLM_SECTIONS, repairer="r" * 64)
    assert repaired_differently[0].fingerprint == defect_fingerprint(
        "review", "opening", "S6", "factuality", "|" + "r" * 64
    )
    # Equivalent defects of one round fold into one repair that sees every finding.
    folded = {d.fingerprint: d for d in merge_equivalent(list(defects.values()))}
    opening = folded[defects["F01"].fingerprint]
    assert opening.label == "F01+F02+F03+F04+F05"
    assert [f["id"] for f in opening.record["equivalent_findings"]] == ["F02", "F03", "F04", "F05"]
    assert (
        opening.record["id"] == "F01" and defects["F01"].record.get("equivalent_findings") is None
    )
    assert len(folded) == len({d.fingerprint for d in defects.values()})


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
                # The section is a field the validator set, not a prefix of the detail prose
                # (RESEARCH_AND_GUIDELINES.md section 27.2 RC8, 27.5 D5).
                "failures": [
                    {
                        "section_id": "opening",
                        "causal_stage": "COMPOSING",
                        "detail": "opening/opening cites unknown fact f",
                    },
                    {"section_id": None, "causal_stage": "COMPOSING", "detail": "other"},
                ],
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
    # BC-07's failures name no LLM-owned section, so no revision could reach it.
    assert defects["BC-07"].stage is None and "no failing check names an LLM-owned section" in str(
        defects["BC-07"].reason
    )
    assert defects["BC-09"].stage is None and "the bundle" in str(defects["BC-09"].reason)
    assert defects["BC-04"].record["details"] == ["opening/opening cites unknown fact f", "other"]


def test_detail_prose_that_looks_like_a_section_prefix_routes_nothing() -> None:
    # The retired shape read the section off the front of the first detail string, so rewording a
    # message moved the defect (RESEARCH_AND_GUIDELINES.md section 27.2 RC8). Only the field
    # routes now: prose that reads exactly like the old prefix reaches no stage.
    validation = {
        "checks": [
            {
                "id": "BC-04",
                "verdict": "FAIL",
                "causal_stage": "COMPOSING",
                "details": ["opening/opening cites unknown fact f"],
                "failures": [
                    {
                        "section_id": None,
                        "causal_stage": "COMPOSING",
                        "detail": "opening/opening cites unknown fact f",
                    }
                ],
            }
        ]
    }
    defect = validation_defects(validation, LLM_SECTIONS)[0]
    assert defect.stage is None and defect.section_id is None
    assert defect.reason == "no failing check names an LLM-owned section"


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
    reloaded.note_re_raised(Defect("abc", "review", "F03", "opening", "S6", {"id": "F03"}))
    reloaded.note_re_raised(Defect("abc", "review", "F03", "opening", "S6", {"id": "F03"}))
    assert RepairLedger(tmp_path / "repairs.json").attempts["abc"]["re_raised"] == ["F03"]
    # Never "recorded advisory": a re-raised defect blocks, whether it came from validation or
    # review (RESEARCH_AND_GUIDELINES.md section 27.5 D5).
    assert reloaded.summary() == (
        "1 repaired (F01 S6 opening), 1 unrepairable recorded advisory, "
        "1 re-raised after repair; the equivalent failure stands"
    )
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

    # A repair of an authored section is judged by that section's checks, so the packet carries
    # that section's fact set and nothing else: the canary's rejected replies show the repair
    # citing facts outside it, which is RESEARCH_AND_GUIDELINES.md section 27.2 RC1 measured at
    # 69 of 76 repair rejections. The upstream stages are judged against the whole corpus and
    # pass None, which leaves the packet as it was.
    bounded = repair_packet(
        ENTRY,
        defect,
        stage_output,
        FACTS,
        ["the H1"],
        authoring.manifest.output.schema_,
        {"identity:repository"},
    )
    assert [r["id"] for r in bounded["facts"]] == ["identity:repository"]
    assert set(bounded) == set(packet)

    # A repaired unit is judged against its own slot's planned set, not the section's, so the
    # packet names that set per slot: the clean composition still showed "unit capability:6
    # cites facts outside its slot's planned set" once the section bound alone was in place.
    per_slot = repair_packet(
        ENTRY,
        defect,
        stage_output,
        FACTS,
        ["the H1"],
        authoring.manifest.output.schema_,
        {"identity:repository", "format:output.glb"},
        {"capability:2": {"format:output.glb"}, "capability:1": {"identity:repository"}},
    )
    assert per_slot["slot_facts"] == {
        "capability:1": ["identity:repository"],
        "capability:2": ["format:output.glb"],
    }
    assert packet["slot_facts"] == {}

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
