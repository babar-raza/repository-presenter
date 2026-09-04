"""The independent review: a bounded packet, findings held to the candidate, a separate identity,
and check 10 judged from the verdict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    CAUSAL_STATES,
    demote_findings,
    quote_located,
    review_checks,
    review_document,
    review_packet,
    scope_defect,
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
    # A quote locates text as a reader would: spans, dashes, and spacing do not have to match.
    respelled = {
        "verdict": "REJECT_FACTUAL",
        "findings": [_finding("F01", "opening", "S6", "It writes  .glb\nfiles.")],
        "preserve": [],
    }
    assert review_checks(respelled, CANDIDATE) == []
    assert review_checks(respelled, "Note — It writes `.glb`  files.") == []
    assert review_checks(respelled, "It writes `.glb` files, always.") != []
    # Factuality is checked against the cited facts once they are given.
    literal = {**_finding("F01", "opening", "S6", "It writes `.glb` files."), "fact_ids": []}
    literal["fact_ids"] = ["format:output.glb"]
    contradicted = {**literal, "fact_ids": ["format:input.obj"]}
    maintainer_only = {**literal, "fact_ids": ["inherited_unit:001.paragraph"]}
    unsupported = {**literal, "quote": "It writes", "fact_ids": ["format:output.glb"]}
    completeness = {**literal, "criterion": "completeness"}
    nothing_cited = {**literal, "quote": "It writes", "fact_ids": []}
    findings = (literal, contradicted, maintainer_only, unsupported, completeness, nothing_cited)
    for finding in findings:
        output = {"verdict": "REJECT_FACTUAL", "findings": [finding], "preserve": []}
        assert review_checks(output, CANDIDATE, FACTS) == []
    # review_checks judges validity only; it never rewrites the reviewer's words, so every
    # finding is left exactly as it arrived (RESEARCH_AND_GUIDELINES.md section 27.2 RC8).
    assert all(f["text"] == "A claim is unsupported." for f in findings)
    assert all(f["causal_stage"] == "S6" for f in findings)
    # The evidence refutes two of them, and the reason is a value the caller reads, not a mark.
    by_id = {fact.id: fact for fact in FACTS.facts}
    assert scope_defect(literal, CANDIDATE, by_id) == (
        "the quote contains the literal value of SUPPORTED fact format:output.glb ('.glb'); "
        "literal fact text is supported"
    )
    assert scope_defect(maintainer_only, CANDIDATE, by_id) is not None
    assert scope_defect(contradicted, CANDIDATE, by_id) is None
    assert scope_defect(unsupported, CANDIDATE, by_id) is None
    assert scope_defect(completeness, CANDIDATE, by_id) is None
    assert scope_defect(nothing_cited, CANDIDATE, by_id) is None  # cites nothing, by definition
    # The answer is a pure function of the finding, the facts and the rule: it lifts by itself
    # when the facts change, because nothing was written into the finding to undo.
    refuting = {
        **by_id,
        "format:output.glb": Fact(
            "format:output.glb",
            "format",
            ".glb",
            by_id["format:output.glb"].evidence,
            polarity="CONTRADICTED",
        ),
    }
    assert scope_defect(literal, CANDIDATE, refuting) is None
    bad = {
        "verdict": "REJECT_FACTUAL",
        "findings": [
            _finding("F01", "opening", "unclear", "It writes PDF files."),
            _finding("F01", "nowhere", "S9"),
        ],
        "preserve": [],
    }
    assert review_checks(bad, CANDIDATE) == [
        "finding F01: quote is not the candidate's text: 'It writes PDF files.'",
        "finding F01: its ID repeats an earlier finding",
        "finding F01: section_id must be a shell section or 'structure'; got 'nowhere'",
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
    assert document["verdict_as_returned"] == "REJECT_PRESENTATION"
    assert [f["id"] for f in document["findings"]] == ["F01"]
    # A rejection whose findings are all advisory has nothing to act on and does not block.
    unfounded = review_document(
        {**output, "findings": output["findings"][1:]}, REVIEWER, AUTHORING, "d" * 64
    )
    assert unfounded["verdict"] == "ACCEPT"
    assert unfounded["verdict_as_returned"] == "REJECT_PRESENTATION"
    assert [f["id"] for f in unfounded["advisory"]] == ["F02", "F03"]
    # A blocking finding re-raised after its one repair attempt is demoted the same way.
    demoted = demote_findings(document, ["F01"])
    assert demoted["verdict"] == "ACCEPT" and demoted["findings"] == []
    assert [f["id"] for f in demoted["advisory"]] == ["F02", "F03", "F01"]
    # The demoted finding keeps the stage the reviewer named and its own words; why it no
    # longer blocks is a field (section 27.5 D5).
    assert demoted["advisory"][2]["causal_stage"] == "S4"
    assert demoted["advisory"][2]["causal_state"] is None
    assert demoted["advisory"][2]["text"] == "A claim is unsupported."
    assert demoted["advisory"][2]["reviewer_scope_defect"] == (
        "re-raised after the one repair attempt its fingerprint allows"
    )
    assert demote_findings(document, ["F09"]) == document
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
        # The reviewer's verdict is a field, so whether a failure invalidates an accepted
        # candidate is never decided by reading details[0] (section 27.2 RC8).
        "review_verdict": "ACCEPT",
        "failures": [],
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


def test_a_presentation_finding_against_a_deterministic_section_is_the_reviewers_defect() -> None:
    renderer_owned = {
        **_finding("F01", "installation", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
    }
    authored = {
        **_finding("F02", "key_capabilities", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
    }
    output = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [renderer_owned, authored],
        "preserve": [],
    }
    assert review_checks(output, CANDIDATE, FACTS) == []
    by_id = {fact.id: fact for fact in FACTS.facts}
    assert scope_defect(renderer_owned, CANDIDATE, by_id) == (
        "section installation renders from facts under the contract's own checks; its "
        "presentation is the renderer's, and a factual error there is a factuality finding"
    )
    assert scope_defect(authored, CANDIDATE, by_id) is None
    # The document records the reason as a field and keeps the stage the reviewer named.
    document = review_document(
        output, REVIEWER, AUTHORING, "d" * 64, candidate_readme=CANDIDATE, facts=FACTS
    )
    assert [f["id"] for f in document["findings"]] == ["F02"]
    advisory = document["advisory"][0]
    assert advisory["id"] == "F01" and advisory["causal_stage"] == "S6"
    assert advisory["causal_state"] is None
    assert advisory["reviewer_scope_defect"].startswith("section installation renders from facts")
    assert advisory["text"] == "A claim is unsupported."


def test_a_quote_locates_text_through_markdown_syntax_a_reader_does_not_see() -> None:
    candidate = (
        '## Installation\n\nVerify the install:\n\n```bash\npython -c "import aspose.threed"\n'
        "```\n\n- **Construct meshes.** Inspect mesh geometry by accessing `Mesh` members.\n\n"
        "<details>\n<summary>Hub APIs</summary>\n\n- `aspose.threed.Scene`: holds the graph.\n"
        "</details>\n"
    )
    assert quote_located('Verify the install:\n\npython -c "import aspose.threed"', candidate)
    assert quote_located("Construct meshes. Inspect mesh geometry by accessing Mesh", candidate)
    assert quote_located("Hub APIs\n\n- aspose.threed.Scene: holds the graph.", candidate)
    assert quote_located("Installation Verify the install", candidate)
    assert not quote_located("Verify the install: pip install", candidate)


def test_a_long_quote_anchors_by_its_opening() -> None:
    candidate = "## API Reference\n\n" + "The scene graph holds nodes and entities. " * 6 + "\n"
    opening = (
        "API Reference\n\nThe scene graph holds nodes and entities. The scene graph holds nodes "
    )
    drifted = opening + "and entities. " + "Something the reviewer paraphrased badly. " * 3
    assert len(drifted) > 80 and quote_located(drifted, candidate)
    assert not quote_located("Something the reviewer paraphrased badly. " * 3, candidate)
    assert not quote_located("API Reference invented", candidate)


def test_an_ellipsis_in_a_quote_abbreviates_between_exact_fragments() -> None:
    candidate = (
        "## Key Capabilities - **Load formats.** Read OBJ and STL files. - **Save.** Write glTF."
    )
    assert quote_located("Key Capabilities - **Load formats.** ... Write glTF.", candidate)
    assert quote_located("Load formats. … Save.", candidate)
    assert not quote_located("Load formats. ... Write PDF.", candidate)
    assert not quote_located("...", candidate)


def test_a_presentation_finding_against_at_a_glance_is_the_reviewers_defect() -> None:
    # README_CONTRACT.md section 2.1: the renderer owns every node, edge, and label of the
    # diagram, so a reviewer asking for a group the facts do not verify is out of scope.
    diagram = {
        **_finding("F01", "at_a_glance", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
    }
    output = {"verdict": "REJECT_PRESENTATION", "findings": [diagram]}
    assert review_checks(output, CANDIDATE, FACTS) == []
    by_id = {fact.id: fact for fact in FACTS.facts}
    reason = scope_defect(diagram, CANDIDATE, by_id)
    assert reason is not None and reason.startswith(
        "section at_a_glance renders from facts under the contract's own checks; its "
        "presentation is the renderer's"
    )


# The sealed canary's advisories, adjudicated against the bundle rather than against the
# reviewer's wording (project/loop-prompt.md section 5): a finding is code-caused when a
# deterministic check can express it, whatever prose the reviewer chose.
SEALED_CANARY = (
    REPO_ROOT
    / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "65b1f577c0f16d0d9112bb6c1153d3024543ac02"
)


def _sealed(name: str) -> Any:
    return json.loads((SEALED_CANARY / name).read_text("utf-8"))


def test_the_sealed_canarys_advisories_are_each_adjudicated_against_the_bundle() -> None:
    review = _sealed("review.json")
    candidate = (SEALED_CANARY / "README.md").read_text("utf-8")
    assert review["verdict"] == ACCEPT and review["findings"] == []
    advisory = review["advisory"]

    # Every advisory is adjudicated against the bundle rather than the reviewer's wording
    # (project/loop-prompt.md section 5). Re-raised decides first: a finding raised again after
    # the one repair attempt its fingerprint allows is code-caused, never a prose judgment call
    # (RESEARCH_AND_GUIDELINES.md section 26), even where its own repair rewrote the quoted text.
    # A finding whose quote the candidate does not carry reports a defect the document does not
    # have, so no deterministic check could express it. What remains is a prose judgment call.
    code_caused = [
        f["id"] for f in advisory if "re-raised after the one repair attempt" in f["text"]
    ]
    reviewer_error = [
        f["id"] for f in advisory if f["id"] not in code_caused and f["quote"] not in candidate
    ]
    prose = [
        f["id"] for f in advisory if f["id"] not in code_caused and f["id"] not in reviewer_error
    ]
    assert len(code_caused) + len(reviewer_error) + len(prose) == len(advisory)
    # Zero advisories is the outcome this gate works toward, and it is reached here: the
    # adjudication then has nothing to classify, which is a pass, not a vacuous one - the
    # blocking checks and the verdict above still hold the candidate.

    # The deterministic coverage advisory reports every identifier a rewritten inherited list
    # drops. It is empty when the rewrites keep them, which is the outcome this item worked
    # toward; when it is not, each line names the unit it belongs to.
    dispositions = {
        entry["unit_id"]: entry for entry in _sealed("dispositions.json")["dispositions"]
    }
    for line in _sealed("validation.json")["advisory"]:
        unit = line.split(": ", 1)[0]
        assert dispositions[unit]["disposition"] == "VERIFIED_REWRITE"
    # The paragraph the reconciler superseded into the opening is covered by the authored one,
    # never rendered beside it (README_CONTRACT.md row 4).
    assert dispositions["inherited_unit:004.paragraph"]["disposition"] == "SUPERSEDE_REDUNDANT"
