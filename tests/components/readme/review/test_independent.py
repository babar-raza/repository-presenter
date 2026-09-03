"""The independent review: a bounded packet, findings held to the candidate, a separate identity,
and check 10 judged from the verdict."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.review.independent.review import (
    CAUSAL_STATES,
    review_checks,
    review_document,
    review_packet,
    summarize_review,
    write_review,
)
from repository_presenter.components.readme.validation.registry import record_review_verdict
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
REVIEWER = MANIFESTS["independent_review"]
AUTHORING = MANIFESTS["section_authoring"]
FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),
        Fact("format:output.glb", "format", ".glb", (Evidence("x"),)),
        Fact("format:input.obj", "format", ".obj", (Evidence("x"),), polarity="UNRESOLVED"),
        Fact("inherited_unit:001.paragraph", "inherited_unit", "Old prose.", (Evidence("x"),)),
        *(
            Fact(f"public_symbol:s{i}", "public_symbol", f"pkg.Sym{i}", (Evidence("x"),))
            for i in range(160)
        ),
    ),
)
CANDIDATE = "# Aspose.3D FOSS for Python\n\nIt writes `.glb` files.\n"
VALIDATION: dict[str, Any] = {
    "checks": [
        {"id": "BC-01", "verdict": "PASS", "causal_stage": None, "details": [], "name": "n"},
        {"id": "BC-10", "verdict": "PENDING", "causal_stage": None, "details": ["judged at S10"]},
    ],
    "advisory": ["note"],
    "summary": {"pass": 1, "fail": 0, "pending": 1},
}


def _finding(label: str, section: str, stage: str, quote: str = "") -> dict[str, Any]:
    return {
        "id": label,
        "section_id": section,
        "causal_stage": stage,
        "criterion": "factuality",
        "text": "A claim is unsupported.",
        "quote": quote,
        "fact_ids": ["format:input.obj"],
        "repair": "Drop the claim.",
    }


def test_the_packet_is_bounded_and_carries_validation_as_context() -> None:
    packet = review_packet(ENTRY, FACTS, "# Old\n", CANDIDATE, {"p": 1}, {"d": 1}, VALIDATION)
    assert packet["candidate_readme"] == CANDIDATE and packet["original_readme"] == "# Old\n"
    kinds = {record["kind"] for record in packet["facts"]}
    assert "inherited_unit" not in kinds and "format" in kinds
    assert sum(1 for r in packet["facts"] if r["kind"] == "public_symbol") == 150
    assert {r["id"]: r["polarity"] for r in packet["facts"]}["format:input.obj"] == "UNRESOLVED"
    assert packet["validation"] == {
        "checks": [
            {"id": "BC-01", "verdict": "PASS", "causal_stage": None, "details": []},
            {
                "id": "BC-10",
                "verdict": "PENDING",
                "causal_stage": None,
                "details": ["judged at S10"],
            },
        ],
        "advisory": ["note"],
    }
    assert set(packet) == REVIEWER.manifest.packet.names


def test_findings_are_held_to_the_candidate_and_a_rejection_needs_a_blocking_finding() -> None:
    accept = {"verdict": "ACCEPT", "findings": [], "preserve": []}
    assert review_checks(accept, CANDIDATE) == []
    sound = {
        "verdict": "REJECT_FACTUAL",
        "findings": [_finding("F01", "opening", "S6", "It writes `.glb` files.")],
        "preserve": ["the H1"],
    }
    assert review_checks(sound, CANDIDATE) == []
    bad = {
        "verdict": "REJECT_FACTUAL",
        "findings": [
            _finding("F01", "opening", "unclear", "It writes PDF files."),
            _finding("F01", "nowhere", "S9"),
        ],
        "preserve": [],
    }
    assert review_checks(bad, CANDIDATE) == [
        "finding F01: quote is not the candidate's text verbatim: 'It writes PDF files.'",
        "finding F01: its ID repeats an earlier finding",
        "finding F01: section_id must be a shell section or 'structure'; got 'nowhere'",
        "verdict REJECT_FACTUAL needs at least one finding that names a section and a causal "
        "stage from S2 to S8; otherwise the candidate is accepted",
    ]


def test_the_document_splits_advisory_findings_and_records_both_identities(
    tmp_path: Path,
) -> None:
    output = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [
            _finding("F01", "opening", "S4"),
            _finding("F02", "structure", "unclear"),
            _finding("F03", "key_capabilities", "S9"),
        ],
        "preserve": ["the quick start"],
    }
    document = review_document(output, REVIEWER, AUTHORING, "d" * 64)
    assert document["verdict"] == "REJECT_PRESENTATION"
    assert [f["id"] for f in document["findings"]] == ["F01"]
    assert document["findings"][0]["causal_state"] == "RECONCILING"
    assert [f["id"] for f in document["advisory"]] == ["F02", "F03"]
    assert document["reviewer"]["job"] == "independent_review"
    assert document["reviewer"]["stage"] == "S10"
    assert document["authoring"]["job"] == "section_authoring"
    assert document["identity_separate"] is True
    assert document["reviewer"]["prompt_sha256"] != document["authoring"]["prompt_sha256"]
    assert summarize_review(document) == (
        "verdict REJECT_PRESENTATION, findings 1, advisory 2, preserve 1"
    )
    digest = write_review(document, tmp_path / "review.json")
    assert write_review(document, tmp_path / "review.json") == digest
    assert CAUSAL_STATES["S7"] == "COMPOSING" and "S9" not in CAUSAL_STATES


def test_check_ten_is_judged_from_the_verdict_and_the_identity() -> None:
    accepted = review_document(
        {"verdict": "ACCEPT", "findings": [], "preserve": []}, REVIEWER, AUTHORING, "d" * 64
    )
    judged = record_review_verdict(VALIDATION, accepted)
    assert judged["checks"][1] == {
        "id": "BC-10",
        "verdict": "PASS",
        "causal_stage": None,
        "details": [],
    }
    assert judged["summary"] == {"pass": 2, "fail": 0, "pending": 0}

    rejected = review_document(
        {
            "verdict": "REJECT_FACTUAL",
            "findings": [_finding("F01", "opening", "S6"), _finding("F02", "opening", "S3")],
            "preserve": [],
        },
        REVIEWER,
        AUTHORING,
        "d" * 64,
    )
    judged = record_review_verdict(VALIDATION, rejected)
    assert judged["checks"][1]["verdict"] == "FAIL"
    assert judged["checks"][1]["causal_stage"] == "INVESTIGATING"
    assert judged["checks"][1]["details"] == [
        "REJECT_FACTUAL",
        "F01 opening (COMPOSING): A claim is unsupported.",
        "F02 opening (INVESTIGATING): A claim is unsupported.",
    ]
    assert judged["summary"] == {"pass": 1, "fail": 1, "pending": 0}

    same_identity = review_document(
        {"verdict": "ACCEPT", "findings": [], "preserve": []}, AUTHORING, AUTHORING, "d" * 64
    )
    judged = record_review_verdict(VALIDATION, same_identity)
    assert judged["checks"][1]["verdict"] == "FAIL"
    assert judged["checks"][1]["details"] == [
        "the reviewer identity is not separate from authoring"
    ]
