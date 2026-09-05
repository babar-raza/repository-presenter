"""The independent review: a bounded packet, findings held to the candidate, a separate identity,
and check 10 judged from the verdict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    CAUSAL_STATES,
    absence_defect,
    claim_evidence,
    quote_located,
    review_checks,
    review_document,
    review_packet,
    scope_defect,
    summarize_review,
    write_review,
)
from repository_presenter.components.readme.validation.registry import (
    deferred_on_required_rows,
    record_review_verdict,
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
        "absent": [],
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


def test_a_mermaid_label_locates_without_the_diagrams_quotation_marks() -> None:
    """A reviewer reads the label, not the syntax that carries it.

    Measured 2026-09-05: the At a Glance node c2 carrying the label Export to interchange
    formats was quoted without its quotation marks, located nothing, and failed the review
    twice - the transaction ended on a JobError rather than a verdict (section 27.2).
    """
    label = "```mermaid\nflowchart TD\n"
    label += '  c2["Export to interchange formats"]\n```\n'
    assert quote_located("c2[Export to interchange formats]", label)
    assert quote_located('c2["Export to interchange formats"]', label)
    # A label the diagram does not carry is still invented, and a quotation mark in ordinary
    # prose is still the reader's text.
    assert not quote_located("c9[Animation retargeting]", label)
    prose = 'It writes "glb" files.\n'
    assert quote_located(prose.strip(), prose)


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
    # A finding re-raised after its one repair attempt is no longer this module's concern: it
    # never demotes on that account alone (docs/RESEARCH_AND_GUIDELINES.md section 27.5 D5), so
    # review_document has nothing special to do with it - the transaction that re-raised it
    # reports the outcome (repair/rounds.py, repair/test_targeted.py).
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


def test_a_required_row_admits_no_advisory_left_standing() -> None:
    # README_CONTRACT.md section 6: an advisory is deferred repair work, not accepted work, so a
    # finding nothing contradicted, against a section every candidate must have, blocks
    # (RESEARCH_AND_GUIDELINES.md section 27.5 D5). This one is advisory because S9 is not a
    # stage the repair loop can reopen, and no check refutes it: the work is real and deferred.
    standing = _finding("F01", "api_reference", "S9")
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [standing], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert [f["id"] for f in document["advisory"]] == ["F01"]
    assert "reviewer_scope_defect" not in document["advisory"][0]
    judged = record_review_verdict(VALIDATION, document)
    assert judged["checks"][1]["verdict"] == "FAIL"
    assert judged["checks"][1]["details"] == [
        "ACCEPT",
        "F01 api_reference: a required row admits no advisory left standing: "
        "A claim is unsupported.",
    ]
    # The row it sits on is a field, and no stage is named: the finding named none the loop can
    # reopen, so it is reported rather than routed (section 27.2 RC8).
    assert judged["checks"][1]["failures"][1]["section_id"] == "api_reference"
    assert judged["checks"][1]["causal_stage"] is None
    assert deferred_on_required_rows(document)[0]["id"] == "F01"

    # A finding a deterministic check refuted is not deferred work - there is nothing to defer
    # and no revision could act on it - so the same required row carries it without blocking.
    refuted = {
        **_finding("F01", "installation", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
    }
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [refuted], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    # The finding is the reviewer's own defect, so it does not block as a finding - and the
    # verdict follows the blocking findings that remain, which is none.
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"].startswith("section installation")
    assert deferred_on_required_rows(document) == []
    assert record_review_verdict(VALIDATION, document)["checks"][1]["verdict"] == "PASS"

    # An optional row may carry one; the bundle records the count either way.
    on_optional = _finding("F01", "at_a_glance", "S9")
    optional = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [on_optional], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert [f["id"] for f in optional["advisory"]] == ["F01"]
    assert deferred_on_required_rows(optional) == []
    assert record_review_verdict(VALIDATION, optional)["checks"][1]["verdict"] == "PASS"


def test_an_absence_the_candidate_disproves_is_the_reviewers_own_defect() -> None:
    """The reviewer states what it claims is missing; the code looks for it (section 27.2 RC6).

    Measured on the canary at 65b1f577 on 2026-09-05: four of six blocking findings alleged an
    omission or a substitution the candidate's own bytes contradicted - the API-reference classes,
    the COLLADA export note, and the editable install command were all in the document.
    """
    omission = {
        **_finding("F01", "api_reference", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
        "absent": ["ObjSaveOptions", "`.glb`"],
        "text": "The API reference omits ObjSaveOptions and the GLB output format.",
    }
    reason = scope_defect(omission, CANDIDATE, {fact.id: fact for fact in FACTS.facts})
    # Only the string the candidate actually contains is named, under the candidate's spelling.
    assert reason == (
        "the finding claims the candidate does not contain '`.glb`', which the candidate contains"
    )
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [omission], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"] == reason
    assert deferred_on_required_rows(document) == []

    # An absence the candidate really does lack stands, whatever the criterion, and blocks.
    real = {**omission, "absent": ["ObjSaveOptions"]}
    stands = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [real], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert [f["id"] for f in stands["findings"]] == ["F01"]
    # A finding that alleges no absence is untouched by the rule.
    assert absence_defect(_finding("F02", "opening", "S6"), CANDIDATE) is None
    # An empty or blank claim is not a claim: it never refutes a finding by locating nothing.
    assert absence_defect({"absent": ["", "   "]}, CANDIDATE) is None


def test_an_absence_that_occurs_nowhere_in_the_evidence_is_the_reviewers_own_defect() -> None:
    """Asking for text neither the original README nor any fact holds asks for what nobody wrote.

    Measured on the canary on 2026-09-05: a quick-start finding required the "verified example"
    to read `Box(10, 20, 30)`, a string in no fact value, not in the original README, and not in
    the candidate; `example:002` is keyword-argument code and it is what the candidate renders.
    """
    original = "# Old\n\nIt writes `.glb` files and reads `pkg.Sym1`.\n"
    evidence = claim_evidence(original, FACTS)
    invented = {
        **_finding("F01", "api_reference", "S6", "It writes `.glb` files."),
        "claim": "absence",
        "absent": ["pkg.Sym404(1, 2, 3)"],
    }
    by_id = {fact.id: fact for fact in FACTS.facts}
    assert scope_defect(invented, CANDIDATE, by_id, evidence) == (
        "the finding asks for 'pkg.Sym404(1, 2, 3)', which occurs in no fact value and nowhere "
        "in the original README: there is nothing to restore"
    )
    # A string a fact value holds is real text the candidate could have carried: the finding stands.
    real = {**invented, "absent": ["pkg.Sym99"]}
    assert scope_defect(real, CANDIDATE, by_id, evidence) is None
    # So is one the original README holds and the candidate does not.
    inherited = {**invented, "absent": ["reads `pkg.Sym1`"]}
    assert scope_defect(inherited, CANDIDATE, by_id, evidence) is None
    # Without the evidence the rule stays silent rather than guessing.
    assert scope_defect(invented, CANDIDATE, by_id) is None
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [invented], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        original_readme=original,
    )
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"].startswith("the finding asks for")


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


def test_a_synthetic_oversized_review_is_bounded_by_its_own_schema() -> None:
    # G2-W12 measured a real review truncated at the 6000-token budget: an unbounded findings
    # array and unbounded prose let one reply grow past it. The schema now caps both, so the
    # gateway's own structured-output generation cannot produce what would need truncating
    # (RESEARCH_AND_GUIDELINES.md section 27.2 RC8; section 27.10's pattern exception is the one
    # keyword this gateway will not honour in a strict schema, not maxItems or maxLength).
    schema = REVIEWER.manifest.output.schema_
    validator = Draft202012Validator(schema)
    at_cap = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [_finding(f"F{i:02d}", "opening", "S6") for i in range(16)],
        "preserve": [],
    }
    validator.validate(at_cap)  # sixteen findings is the cap, not yet oversized
    over_cap = {**at_cap, "findings": [*at_cap["findings"], _finding("F16", "opening", "S6")]}
    errors = list(validator.iter_errors(over_cap))
    assert any(error.validator == "maxItems" and error.validator_value == 16 for error in errors)
    # A finding's own prose is bounded the same way: one paragraph, not a whole section.
    oversized_quote = {**_finding("F01", "opening", "S6"), "quote": "x" * 501}
    errors = list(validator.iter_errors({**at_cap, "findings": [oversized_quote]}))
    assert any(error.validator == "maxLength" for error in errors)
    oversized_text = {**_finding("F01", "opening", "S6"), "text": "x" * 601}
    errors = list(validator.iter_errors({**at_cap, "findings": [oversized_text]}))
    assert any(error.validator == "maxLength" for error in errors)
    oversized_repair = {**_finding("F01", "opening", "S6"), "repair": "x" * 401}
    errors = list(validator.iter_errors({**at_cap, "findings": [oversized_repair]}))
    assert any(error.validator == "maxLength" for error in errors)


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
