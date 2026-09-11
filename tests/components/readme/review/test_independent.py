"""The independent review: a bounded packet, findings held to the candidate, a separate identity,
and check 10 judged from the verdict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.composition.renderer import (
    ADDITIONAL_EXAMPLES_SUMMARY,
)
from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    CAUSAL_STATES,
    absence_defect,
    claim_evidence,
    finding_class,
    prose_judgment,
    quote_located,
    review_checks,
    review_document,
    review_packet,
    scope_defect,
    second_reader,
    summarize_review,
    unit_texts,
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


def _judgment(label: str, section: str, quote: str = "It writes `.glb` files.") -> dict[str, Any]:
    """A prose judgment: the presentation criterion, on a section the shell requires."""
    return {**_finding(label, section, "S6", quote), "criterion": "presentation", "fact_ids": []}


def test_a_prose_judgment_on_a_required_row_blocks_only_when_a_second_reader_agrees() -> None:
    """The owner's two-reader rule (2026-09-06 00:15, section 31; section 27.8).

    A required row admits zero advisories left standing, so one reader's taste could hold a
    candidate unsealed indefinitely - measured on Aspose.Cells and Aspose.Slides, whose only
    remaining blockers were four and three presentation findings after repair (2026-09-06).
    """
    output = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [_judgment("F01", "opening"), _judgment("F02", "key_capabilities")],
        "preserve": [],
    }
    common: dict[str, Any] = {
        "candidate_readme": CANDIDATE,
        "facts": FACTS,
        "original_readme": "Old prose.",
    }
    # One reader alone: both findings become advisory, marked, and the candidate seals.
    alone = review_document(output, REVIEWER, AUTHORING, "d" * 64, second={}, **common)
    assert alone["verdict"] == ACCEPT and alone["findings"] == []
    assert [f["id"] for f in alone["advisory"]] == ["F01", "F02"]
    assert all(f["single_reader_advisory"] for f in alone["advisory"])
    # `read` counts completed reads (PHASE1/F6): an empty-but-real second reading is read 2.
    assert alone["second_reader"] == {"read": 2, "corroborated": []}

    # A second reader raising the same class on one of them keeps that one blocking; the other
    # is still one reader's judgment. Equivalence is the class, never the wording.
    agreed = {**_judgment("X9", "opening"), "text": "Different words, same defect."}
    both = review_document(
        output, REVIEWER, AUTHORING, "d" * 64, second={"findings": [agreed]}, **common
    )
    assert [f["id"] for f in both["findings"]] == ["F01"]
    assert [f["id"] for f in both["advisory"]] == ["F02"]
    assert both["verdict"] == "REJECT_PRESENTATION"
    assert both["second_reader"]["corroborated"] == [finding_class(agreed)]

    # Without a second read nothing is demoted, and a finding a deterministic check can express
    # is never a prose judgment: it blocks on one reader, as it always did.
    assert len(review_document(output, REVIEWER, AUTHORING, "d" * 64, **common)["findings"]) == 2
    factual = {**output, "findings": [_finding("F01", "opening", "S6", "It writes `.glb` files.")]}
    unmoved = review_document(factual, REVIEWER, AUTHORING, "d" * 64, second={}, **common)
    assert [f["id"] for f in unmoved["findings"]] == ["F01"]


def test_the_second_read_changes_the_seed_and_nothing_else() -> None:
    """The prompt file and its hash are untouched, so the candidate's dependencies do not move."""
    second = second_reader(REVIEWER)
    assert second.sha256 == REVIEWER.sha256 and second.path == REVIEWER.path
    assert second.manifest.sampling.seed != REVIEWER.manifest.sampling.seed
    assert (
        second.manifest.model_copy(update={"sampling": REVIEWER.manifest.sampling})
        == REVIEWER.manifest
    )
    # A prose judgment is the presentation criterion on a row the shell requires, nothing else.
    assert prose_judgment(_judgment("F01", "opening"))
    assert not prose_judgment(_finding("F01", "opening", "S6"))
    assert not prose_judgment(_judgment("F01", "enterprise_relationship"))


def test_the_packet_is_bounded_and_carries_validation_as_context() -> None:
    packet = review_packet(ENTRY, FACTS, "# Old\n", CANDIDATE, {"p": 1}, {"d": 1}, VALIDATION)
    assert packet["candidate_readme"] == CANDIDATE and packet["original_readme"] == "# Old\n"
    kinds = {record["kind"] for record in packet["facts"]}
    assert "inherited_unit" not in kinds and "format" in kinds
    # G4-W17 arrival item 27: SYMBOL_CAP raised well above every measured portfolio surface, so
    # this fixture's 160 symbols - deliberately more than the old 150 cap - now all pass through
    # uncapped; the cap's own boundary behavior is `test_dossier.py`'s to prove.
    assert sum(1 for r in packet["facts"] if r["kind"] == "public_symbol") == 160
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


def test_a_fence_flattened_into_a_quote_locates_the_candidates_own_block() -> None:
    """A reviewer quotes what it reads, on one line; the candidate carries it on four.

    Measured 2026-09-05: the reviewer quoted the install verification as one string, the
    fence's language tag survived where the candidate's own fence line dropped it, and the
    review failed closed after two rejections rather than returning a verdict (section 27.2).
    """
    candidate = "Verify the install:\n```bash\n"
    candidate += "python -c 'import aspose.threed'\n```\n"
    flattened = "Verify the install: ```bash python -c 'import aspose.threed'"
    assert quote_located(flattened, candidate)
    # A fence with no language, and the candidate's own spelling, locate as they did before.
    assert quote_located("```python -c 'import aspose.threed'", candidate)
    assert quote_located("Verify the install:", candidate)
    # Text the candidate does not carry is still invented.
    assert not quote_located("Verify the install: ```bash pip install x", candidate)


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
    # The quote check itself is unweakened: this reply's only finding locates nothing, so there is
    # no trustworthy remainder to fold it out of and the whole review is still unusable.
    assert review_checks(respelled, "It writes `.glb` files, always.") == [
        "finding F01: quote is not the candidate's text: 'It writes  .glb\\nfiles.'"
    ]
    assert [f["id"] for f in respelled["findings"]] == ["F01"]
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
    # G4-W17 arrival item 39: naming neither a fact_id nor an absent claim used to stand
    # unconditionally ("cites nothing, by definition"); it is now the reviewer's own defect,
    # since nothing about it is checkable either - see test_a_factuality_finding_naming_no_
    # fact_and_no_absence_is_the_reviewers_defect for the full case.
    assert scope_defect(nothing_cited, CANDIDATE, by_id) is not None
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
    # The first finding's quote locates nothing, so it is folded out; the second survives the
    # quote check and its own two defects are still named, and the folded finding's ID still
    # counts, so the repeat it caused is reported exactly as before.
    assert review_checks(bad, CANDIDATE) == [
        "finding F01: its ID repeats an earlier finding",
        "finding F01: section_id must be a shell section or 'structure'; got 'nowhere'",
    ]
    assert [f["section_id"] for f in bad["findings"]] == ["nowhere"]


def test_one_unlocatable_quote_is_folded_out_and_the_other_findings_are_kept() -> None:
    """G4-W17 arrival item 28 (lane D PROPOSAL). Same shape as items 16 and 17, ``d707693``.

    The reviewer's own packet carries the *upstream* README beside the candidate and its job is to
    compare them, so quoting the original where it meant the candidate is a natural slip - and it
    used to cost every other finding in the same reply. Measured 2026-09-06 on
    ``aspose-pdf-foss/Aspose-PDF-FOSS-for-Go``: one such quote among eight findings discarded 7
    usable ones and left BC-10 unjudged. The unusable finding is dropped, never repaired into a
    valid one, and the rest are used normally.
    """
    original_only = "This SDK also rasterises DWG drawings."
    assert not quote_located(original_only, CANDIDATE)
    output = {
        "verdict": "REJECT_FACTUAL",
        "findings": [
            _finding("F01", "opening", "S6", "It writes `.glb` files."),
            _finding("F02", "key_capabilities", "S5", original_only),
            _finding("F03", "opening", "S6", "It writes  .glb\nfiles."),
            _finding("F04", "key_capabilities", "S4", "Aspose.3D FOSS for Python"),
        ],
        "preserve": ["the H1"],
    }
    assert review_checks(output, CANDIDATE, FACTS) == []
    assert [f["id"] for f in output["findings"]] == ["F01", "F03", "F04"]
    # Folding drops, it never fabricates: each kept finding is the reviewer's own words, unchanged.
    assert all(f["text"] == "A claim is unsupported." for f in output["findings"])
    assert all(f["causal_stage"] in CAUSAL_STATES for f in output["findings"])
    # The kept findings then block as they always did - this is the value the whole review lost.
    document = review_document(
        output, REVIEWER, AUTHORING, "d" * 64, candidate_readme=CANDIDATE, facts=FACTS
    )
    assert document["verdict"] == "REJECT_FACTUAL"
    assert [f["id"] for f in document["findings"]] == ["F01", "F03", "F04"]

    # A reply whose every quote is unlocatable keeps no trustworthy remainder, so it is still
    # rejected whole and re-asked; nothing is folded and no verdict is invented from it.
    invented = {
        "verdict": "REJECT_FACTUAL",
        "findings": [
            _finding("F01", "opening", "S6", original_only),
            _finding("F02", "key_capabilities", "S5", "It exports to USDZ."),
        ],
        "preserve": [],
    }
    assert review_checks(invented, CANDIDATE, FACTS) == [
        "finding F01: quote is not the candidate's text: 'This SDK also rasterises DWG drawings.'",
        "finding F02: quote is not the candidate's text: 'It exports to USDZ.'",
    ]
    assert [f["id"] for f in invented["findings"]] == ["F01", "F02"]


def test_a_quote_true_of_another_section_does_not_locate_a_finding_naming_this_one() -> None:
    """PA-02, REC-005 (remainder): the exact AUD-002 shape `absence_defect` already fixed via
    `_section_slice`, reproduced for `quote_located`'s other call site in `review_checks`. A
    quote that is real candidate text, but under a *different* heading than the finding names,
    must not locate the finding - text present somewhere in a large README does not disprove, or
    here confirm, a claim about one specific section (external audit, 2026-09-07)."""
    sectioned = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Key Capabilities\n\n"
        "Build scenes in memory.\n\n"
        "## Installation\n\n"
        "It writes `.glb` files.\n"
    )
    quote = "It writes `.glb` files."
    # The quote is Installation's own text: naming Installation locates it, same as before.
    own_section = {
        "verdict": "REJECT_FACTUAL",
        "findings": [_finding("F01", "installation", "S6", quote)],
        "preserve": [],
    }
    assert review_checks(own_section, sectioned) == []

    # The identical quote exists in the document, but under Key Capabilities, not the section
    # this finding names - it must not be treated as located there.
    wrong_section = {
        "verdict": "REJECT_FACTUAL",
        "findings": [_finding("F01", "key_capabilities", "S6", quote)],
        "preserve": [],
    }
    assert review_checks(wrong_section, sectioned) == [
        "finding F01: quote is not the candidate's text: 'It writes `.glb` files.'"
    ]

    # No-regression case: a section with no heading of its own (`opening`) keeps the existing
    # whole-document fallback exactly as before this fix.
    no_heading = {
        "verdict": "REJECT_FACTUAL",
        "findings": [_finding("F01", "opening", "S6", quote)],
        "preserve": [],
    }
    assert review_checks(no_heading, sectioned) == []


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
    # Corroborated by a second read (PHASE1/F6): two independent ACCEPTs are the accept path.
    accepted = review_document(
        {"verdict": "ACCEPT", "findings": [], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        second={"verdict": "ACCEPT", "findings": [], "preserve": []},
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


def test_a_folded_accept_from_a_single_read_no_longer_passes_check_ten() -> None:
    """PHASE1/F6: the acceptance-side guard. Eight of the nine sealed reviews returned a
    REJECT_* verdict whose every finding folded to advisory, so the candidate sealed as ACCEPT
    on one read - an accept was the one verdict no second reader ever corroborated, while a
    surviving prose finding always earned a second read (the asymmetry the sprint diagnosis
    lists as F). Check 10 now passes only an accept a second independent read backs:
    ``second_reader.read`` counts completed reads, and a legacy boolean counts as at most one,
    so a pre-F6 review document never satisfies the new predicate by accident."""
    refuted = {
        **_finding("F01", "opening", "S6", "It writes `.glb` files."),
        "fact_ids": ["format:output.glb"],
    }
    folded = {"verdict": "REJECT_FACTUAL", "findings": [refuted], "preserve": []}
    common: dict[str, Any] = {"candidate_readme": CANDIDATE, "facts": FACTS}
    single = review_document(folded, REVIEWER, AUTHORING, "d" * 64, **common)
    assert single["verdict"] == ACCEPT and single["findings"] == []
    assert single["second_reader"]["read"] == 1
    judged = record_review_verdict(VALIDATION, single)
    assert judged["checks"][1]["verdict"] == "FAIL"
    assert judged["checks"][1]["details"] == [
        "ACCEPT with a single read: an accept verdict requires a corroborating second read "
        "(second_reader.read >= 2)"
    ]
    assert judged["checks"][1]["causal_stage"] is None
    # Two independent ACCEPTs accept: the corroborated document passes check 10 unchanged.
    second = {"verdict": "ACCEPT", "findings": [], "preserve": []}
    both = review_document(folded, REVIEWER, AUTHORING, "d" * 64, second=second, **common)
    assert both["verdict"] == ACCEPT and both["findings"] == []
    assert both["second_reader"]["read"] == 2
    assert record_review_verdict(VALIDATION, both)["checks"][1]["verdict"] == "PASS"


def test_a_disagreeing_second_read_routes_its_findings_through_the_fold_stack() -> None:
    """PHASE1/F6: on the accept path the second read is corroboration, not a formality - its
    findings go through the same deterministic fold stack as the first read's. A survivor
    blocks with its causal state and the disagreement repairs normally; a refuted one is the
    reviewer's own defect exactly as on the first read; a prose judgment only one of the two
    readers raised stays one reader's judgment (section 27.8, made symmetric)."""
    accept = {"verdict": "ACCEPT", "findings": [], "preserve": []}
    common: dict[str, Any] = {"candidate_readme": CANDIDATE, "facts": FACTS}
    # A second-read finding the stack cannot refute blocks, and the disagreement's verdict is
    # the second read's own returned one; the first read's stays on verdict_as_returned.
    standing = _finding("F02", "key_capabilities", "S6", "It writes `.glb` files.")
    disagreeing = {"verdict": "REJECT_FACTUAL", "findings": [standing], "preserve": []}
    disputed = review_document(accept, REVIEWER, AUTHORING, "d" * 64, second=disagreeing, **common)
    assert disputed["verdict"] == "REJECT_FACTUAL"
    assert disputed["verdict_as_returned"] == "ACCEPT"
    assert [f["id"] for f in disputed["findings"]] == ["F02"]
    assert disputed["findings"][0]["causal_state"] == "COMPOSING"
    assert disputed["findings"][0]["reader"] == 2
    assert disputed["second_reader"]["read"] == 2
    assert record_review_verdict(VALIDATION, disputed)["checks"][1]["verdict"] == "FAIL"
    # A refuted second-read finding folds to advisory with its reason: the two reads agree.
    refuted = {
        **_finding("F03", "opening", "S6", "It writes `.glb` files."),
        "fact_ids": ["format:output.glb"],
    }
    agreeing = {"verdict": "REJECT_FACTUAL", "findings": [refuted], "preserve": []}
    agreed = review_document(accept, REVIEWER, AUTHORING, "d" * 64, second=agreeing, **common)
    assert agreed["verdict"] == ACCEPT and agreed["findings"] == []
    assert agreed["advisory"][0]["reader"] == 2
    assert agreed["advisory"][0]["reviewer_scope_defect"].startswith("the quote contains")
    assert record_review_verdict(VALIDATION, agreed)["checks"][1]["verdict"] == "PASS"
    # A prose judgment only the second reader raised is single_reader_advisory, symmetrically.
    lone = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [_judgment("F04", "opening")],
        "preserve": [],
    }
    still = review_document(accept, REVIEWER, AUTHORING, "d" * 64, second=lone, **common)
    assert still["verdict"] == ACCEPT and still["findings"] == []
    assert still["advisory"][0]["single_reader_advisory"] is True
    assert record_review_verdict(VALIDATION, still)["checks"][1]["verdict"] == "PASS"


def test_a_required_row_admits_no_advisory_left_standing() -> None:
    # README_CONTRACT.md section 6: an advisory is deferred repair work, not accepted work, so a
    # finding nothing contradicted, against a section every candidate must have, blocks
    # (RESEARCH_AND_GUIDELINES.md section 27.5 D5). This one is advisory because S9 is not a
    # stage the repair loop can reopen, and no check refutes it: the work is real and deferred.
    standing = _finding("F01", "api_reference", "S9")
    # The second read is given (PHASE1/F6) so check 10's judgment below isolates the deferred-
    # advisory rule, not the separate corroboration requirement the accept path now carries.
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [standing], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        second={"verdict": "ACCEPT", "findings": [], "preserve": []},
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
        second={"verdict": "ACCEPT", "findings": [], "preserve": []},
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
        second={"verdict": "ACCEPT", "findings": [], "preserve": []},
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
    fully_refuted = {
        **_finding("F01", "api_reference", "S6", "It writes `.glb` files."),
        "criterion": "presentation",
        "fact_ids": [],  # this rule reads absent/candidate, never fact_ids
        "absent": ["`.glb`"],
        "text": "The API reference omits the GLB output format.",
    }
    reason = scope_defect(fully_refuted, CANDIDATE, {fact.id: fact for fact in FACTS.facts})
    assert reason == (
        "the finding claims the candidate does not contain '`.glb`', which the candidate contains"
    )
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [fully_refuted], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"] == reason
    assert deferred_on_required_rows(document) == []

    # External review, 2026-09-07: a finding bundling one refuted claim with one genuine one must
    # not dismiss in full - the candidate's own gap must not survive only because a reviewer
    # happened to bundle it beside a false claim. Every claim must be accounted for before
    # dismissal; one true, unrefuted remainder leaves the finding standing, and blocking.
    mixed = {**fully_refuted, "absent": ["ObjSaveOptions", "`.glb`"], "id": "F02"}
    assert scope_defect(mixed, CANDIDATE, {fact.id: fact for fact in FACTS.facts}) is None
    stands_mixed = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [mixed], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
    )
    assert [f["id"] for f in stands_mixed["findings"]] == ["F02"]

    # An absence the candidate really does lack stands, whatever the criterion, and blocks.
    real = {**fully_refuted, "absent": ["ObjSaveOptions"]}
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


def test_an_absence_check_is_scoped_to_the_findings_own_section() -> None:
    """External audit, 2026-09-07, measured on a real sealed candidate: a finding about the
    Installation section was wrongly refuted because the claimed-absent text existed 760 lines
    later in Development and Testing - present somewhere is not present where the finding says
    it is missing."""
    two_sections = (
        "# Product\n\n"
        "## Installation\n\n"
        "Install the published package:\n\n```bash\npip install product\n```\n\n"
        "## Development and Testing\n\n"
        "Install in editable mode:\n\n```bash\npython3 -m pip install -e .\n```\n"
    )
    finding = {
        **_finding("F02", "installation", "S6"),
        "absent": ["python3 -m pip install -e ."],
    }
    # The text is real, but it lives in a different section - it does not disprove a real gap in
    # Installation, so the finding is not the reviewer's defect and survives to block.
    assert absence_defect(finding, two_sections) is None
    # The same claim, genuinely present within Installation itself, is correctly refuted.
    within_section = {
        **_finding("F02", "installation", "S6"),
        "absent": ["pip install product"],
    }
    reason = absence_defect(within_section, two_sections)
    assert reason is not None and "which the candidate contains" in reason
    # A section_id with no matching heading in the document falls back to the whole document,
    # never narrowing to nothing - the pre-existing, unscoped behavior, preserved as a fallback.
    unscoped = {**finding, "section_id": "no-such-section"}
    reason = absence_defect(unscoped, two_sections)
    assert reason is not None and "which the candidate contains" in reason


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
        "fact_ids": [],  # this rule reads absent/evidence, never fact_ids
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
    # External review, 2026-09-07: a mix of one invented claim and one genuine claim (real text
    # missing from the candidate) must not dismiss in full either - the same "every claim must be
    # accounted for" rule as the present/missing mix, now for the invented/genuine mix.
    mixed = {**invented, "absent": ["pkg.Sym404(1, 2, 3)", "pkg.Sym99"], "id": "F03"}
    assert scope_defect(mixed, CANDIDATE, by_id, evidence) is None
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


def test_a_finding_against_a_sentence_the_renderer_wrote_is_out_of_scope() -> None:
    """The renderer writes counts from the facts into sections an LLM otherwise owns.

    Measured on the canary 2026-09-05: the reviewer twice preferred the original README's
    stale counts - 305 public types, 33 test files - over the 337 and 34 the renderer
    computed from the facts, and the repair loop spent an attempt on prose no unit owns.
    """
    rendered = (
        "The suite covers 34 test files under `tests/`.",
        "It covers all 337 verified public types; the [API Reference]"
        "(#api-reference) section above covers the essentials.",
    )
    counted = {
        **_finding(
            "F01",
            "development_testing",
            "S6",
            "The suite covers 34 test files",
        ),
        "criterion": "presentation",
    }
    by_id = {fact.id: fact for fact in FACTS.facts}
    assert scope_defect(counted, CANDIDATE, by_id, "", rendered) == (
        "the quoted sentence is the renderer's own, written from the facts beside a "
        "unit that did not write it; no revision of that unit can change it"
    )
    # The same finding without the renderer's sentences in hand still stands: the rule is
    # what the renderer wrote, never a guess about the wording.
    assert scope_defect(counted, CANDIDATE, by_id) is None
    # A finding against the unit beside it is untouched.
    authored = {
        **_finding(
            "F02",
            "development_testing",
            "S6",
            "It writes `.glb` files.",
        ),
        "criterion": "presentation",
    }
    assert scope_defect(authored, CANDIDATE, by_id, "", rendered) is None


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
    # A quote trails off at either end too. Both of Aspose.Cells' rejected findings were this
    # shape and each was under 80 characters, so the anchor could not reach them and the review
    # ended the transaction on a JobError (measured 2026-09-06).
    assert quote_located("Key Capabilities - **Load formats.**...", candidate)
    assert quote_located("...Read OBJ and STL files.", candidate)
    assert not quote_located("Key Capabilities - **Load fonts.**...", candidate)


def test_a_presentation_finding_against_the_documents_own_shape_is_the_reviewers_defect() -> None:
    """The shell owns which sections exist and what they are called; no unit can change either.

    Measured 2026-09-06: Aspose.Slides was held unsealed by a finding asking for a "Links"
    section the shell does not define, Aspose.Cells by one calling the Detailed Member Reference
    block - required by contract row 14 - too verbose. Two independent readers raised each, so
    the two-reader rule cannot answer them; only their scope can.
    """
    by_id = {fact.id: fact for fact in FACTS.facts}
    shape = {
        **_finding("F07", "structure", "S6", "## Documentation & Resources"),
        "criterion": "presentation",
    }
    assert scope_defect(shape, CANDIDATE, by_id) == (
        "the semantic shell owns which sections exist, in what order, and under which headings; "
        "it is evaluated from the facts, so no stage the loop can reopen would add or remove one"
    )
    heading = {
        **_finding("F05", "api_reference", "S6", "#### Detailed Member Reference"),
        "criterion": "presentation",
    }
    assert scope_defect(heading, CANDIDATE, by_id) == (
        "the quote is the heading 'Detailed Member Reference', which the renderer emits because "
        "the contract's shell requires it; no unit wrote it and none can change it"
    )
    # Mutation: the same section with prose the units own still stands, and a finding that only
    # mentions a heading in its text rather than quoting one is untouched.
    prose = {
        **_finding("F05", "api_reference", "S6", "The intro names three entry points."),
        "criterion": "presentation",
    }
    assert scope_defect(prose, CANDIDATE, by_id) is None
    invented = {
        **_finding("F09", "api_reference", "S6", "### Frequently Asked Questions"),
        "criterion": "presentation",
    }
    assert scope_defect(invented, CANDIDATE, by_id) is None
    # A structural finding that is not a presentation judgment keeps its own route.
    factual = _finding("F10", "structure", "S6", "It writes `.glb` files.")
    assert scope_defect(factual, CANDIDATE, by_id) is None


def test_a_presentation_finding_against_a_collapsible_sections_chrome_is_the_reviewers_defect() -> (
    None
):
    """G4-W17 arrival item 33. `additional_examples` and `api_reference` are mixed-owned (an `M`
    section), so they are never wholesale exempted like a `D` section - but the `<details>`/
    `<summary>` wrapper the renderer puts around them is exactly as deterministic as a heading.

    Measured 2026-09-06 on Aspose.Slides for Java: a finding quoted `ADDITIONAL_EXAMPLES_SUMMARY`
    ("View Additional Examples") exactly, calling the collapsible structure "unnecessary UI" not
    present in the original README. Routed to authoring's `additional_examples` unit (the only
    LLM-owned content in that section), the re-ask rewrote the unit's own prose and left the
    renderer's wrapper - and the finding - unchanged, the same shape as the heading and structural
    cases above.
    """
    by_id = {fact.id: fact for fact in FACTS.facts}
    chrome = {
        **_finding("F05", "additional_examples", "S6", ADDITIONAL_EXAMPLES_SUMMARY),
        "criterion": "presentation",
    }
    assert scope_defect(chrome, CANDIDATE, by_id) == (
        f"the quote is {ADDITIONAL_EXAMPLES_SUMMARY!r}, the renderer's own collapsible-summary "
        "text; no unit wrote it and none can change it"
    )
    # Mutation: the unit's own prose in the same section still stands.
    prose = {
        **_finding("F06", "additional_examples", "S6", "Shows how to merge two documents."),
        "criterion": "presentation",
    }
    assert scope_defect(prose, CANDIDATE, by_id) is None


def test_a_presentation_finding_against_verified_surface_is_the_reviewers_defect() -> None:
    """Lane D PROPOSAL P16. Measured 2026-09-06 on Aspose.Cells for Go: a finding quoted
    `ExportToCSV`, a SUPPORTED `public_symbol` fact BC-04 had already passed, and asked for it to
    be deleted as "unsupported" because the upstream README lacked it - judging the candidate
    against the original README rather than its own fact set, the same shape as the heading and
    chrome cases, one level lower still (the finding names real content, not renderer chrome)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact(
                "public_symbol:cells.exportocsv",
                "public_symbol",
                "cells.ExportToCSV",
                (Evidence("x"),),
            ),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    deletion_request = {
        **_finding(
            "F06",
            "api_reference",
            "S6",
            "- `ExportToCSV`: ExportToCSV writes the worksheet at sheetIndex to a CSV file "
            "using the given delimiter",
        ),
        "criterion": "presentation",
    }
    assert scope_defect(deletion_request, CANDIDATE, by_id) == (
        "the quote names public_symbol:cells.exportocsv, a SUPPORTED fact BC-04 already "
        "verifies; the candidate's own fact set is the standard of support, not the upstream "
        "README, and loop-prompt.md rule 8 requires the complete verified surface - absence "
        "from the original is never itself a presentation defect for content BC-04 already "
        "verified"
    )
    # Mutation: an unverified symbol - not in the fact set at all - is untouched, and a factuality
    # finding (not presentation) keeps its own route even when it names the same member.
    unverified = {
        **_finding("F08", "api_reference", "S6", "- `DeleteWorkbook`: removes the file."),
        "criterion": "presentation",
    }
    assert scope_defect(unverified, CANDIDATE, by_id) is None
    factual = _finding(
        "F09", "api_reference", "S6", "- `ExportToCSV`: ExportToCSV writes to JSON, not CSV."
    )
    assert scope_defect(factual, CANDIDATE, by_id) is None


def test_a_presentation_findings_quote_must_actually_reference_the_symbol() -> None:
    """G4-W17 arrival item 45, urgent - a soundness gap in P16's own exemption above, already
    shipped. Measured live on the sealed Aspose.Cells-FOSS-for-Rust candidate (2,084 symbols):
    common short identifiers that are also ordinary English or legitimate Rust idioms - new,
    from, fmt, cells - matched two of that seal's seven review findings by coincidental
    lowercase word overlap alone, via a bare case-insensitive match against the *normalized*
    quote, which strips backticks entirely so code-span-ness was never even checked - folding
    real findings out before BC-10 could weigh them. A real reference is backticked, spelled in
    its own qualified/`::` form, or spelled in its own non-lowercase case; ordinary prose
    containing the same short token by coincidence is none of those."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact("public_symbol:workbook.new", "public_symbol", "Workbook::new", (Evidence("x"),)),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    # The collision, reproduced: ordinary prose that happens to contain "new" as an English
    # word - no backticks, no qualified form, no distinguishing case - is not a reference.
    coincidental = {
        **_finding("F10", "key_capabilities", "S6", "Create a new workbook and add a sheet."),
        "criterion": "presentation",
    }
    assert scope_defect(coincidental, CANDIDATE, by_id) is None
    # A real reference, backticked: the exemption still fires as P16 intended.
    backticked = {
        **_finding("F11", "key_capabilities", "S6", "Calling `new` twice leaks a handle."),
        "criterion": "presentation",
    }
    assert scope_defect(backticked, CANDIDATE, by_id) is not None
    # A real reference, qualified/`::` form, no backticks needed.
    qualified = {
        **_finding("F12", "key_capabilities", "S6", "Workbook::new should validate its path."),
        "criterion": "presentation",
    }
    assert scope_defect(qualified, CANDIDATE, by_id) is not None


def test_a_factuality_finding_against_a_verified_row_no_unit_wrote_is_the_reviewers_defect() -> (
    None
):
    """G4-W17 arrival item 62 (lane C PROPOSAL Z). The BC-04 exemption above was gated on the
    `presentation` label, standing in for the question the label cannot answer - where the quoted
    text lives. Measured 2026-09-11 on Aspose.Cells for Java, F05 (`factuality`, `api_reference`):
    the quote was two verified enums' own table rows, each a SUPPORTED `public_symbol`'s name and
    docstring the renderer prints verbatim; `content_units.json` held 25 units and none carried
    either row; the repair re-asked the section's intro unit and got the same 157 bytes back; the
    finding re-raised and every refutation returned None, although `_quoted_verified_fact` already
    resolved the quote. Two independent draws reached BC-10 on exactly this shape. With the
    round's units in hand, a quote no unit wrote is the renderer's whatever the label says; a quote
    any unit carries - even partly - keeps its route to that unit; with no units supplied the gate
    stays presentation-only, because "no unit carries it" is a measurement, never a default."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact(
                "public_symbol:org.aspose.cells_foss",
                "public_symbol",
                "org.aspose.cells_foss",
                (Evidence("x"),),
            ),
            Fact(
                "public_symbol:org.aspose.cells_foss.core.diagnosticseverity",
                "public_symbol",
                "org.aspose.cells_foss.core.DiagnosticSeverity",
                (Evidence("x"),),
                attributes={"docstring": "Represents the severity of a diagnostic entry."},
            ),
            Fact(
                "public_symbol:org.aspose.cells_foss.diagnosticseverity",
                "public_symbol",
                "org.aspose.cells_foss.DiagnosticSeverity",
                (Evidence("x"),),
                attributes={"docstring": "Represents the severity level of a diagnostic message."},
            ),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    intro = (
        "The library exposes its core functionality through the `org.aspose.cells_foss` package."
    )
    candidate = (
        "# Aspose.Cells FOSS for Java\n\nIt writes `.glb` files.\n\n## API Reference\n\n"
        f"{intro}\n\n| Type | Summary |\n|---|---|\n"
        "| `cells_foss.DiagnosticSeverity` | Represents the severity level of a diagnostic "
        "message. |\n| `core.DiagnosticSeverity` | Represents the severity of a diagnostic "
        "entry. |\n"
    )
    units = {
        "schema_version": 1,
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": intro.replace("`", ""),
                "fact_ids": ["public_symbol:org.aspose.cells_foss"],
            }
        ],
        "omitted": [],
    }
    row = (
        "cells_foss.DiagnosticSeverity | Represents the severity level of a diagnostic message. "
        "... core.DiagnosticSeverity | Represents the severity of a diagnostic entry."
    )
    # The real record, field for field. Its own `absent` list did not save it: one claim the
    # section contains, one the original README happens to carry, so it is neither present nor
    # invented - a real remainder under the 2026-09-07 rule, and absence_defect stands aside.
    f05 = {
        **_finding("F05", "api_reference", "S6", row),
        "fact_ids": ["public_symbol:org.aspose.cells_foss"],
        "absent": ["DiagnosticSeverity-core", "DiagnosticSeverity"],
    }
    original = "# Old\n\nSee DiagnosticSeverity-core for the enum.\n"
    evidence = claim_evidence(original, facts)
    assert review_checks({"findings": [f05]}, candidate, facts) == []
    assert absence_defect(f05, candidate, evidence) is None
    # Units unknown: exactly the pre-item-62 answer - the label gates, and the finding stands.
    assert unit_texts(None) is None
    assert scope_defect(f05, candidate, by_id, evidence) is None
    # Units in hand and none carries either row: the exemption reaches the finding.
    reason = scope_defect(f05, candidate, by_id, evidence, (), unit_texts(units))
    assert reason == (
        "the quote names public_symbol:org.aspose.cells_foss.core.diagnosticseverity, a SUPPORTED "
        "fact BC-04 already verifies, and no content unit carries the quoted text: it is the "
        "renderer's own rendering of that verified fact, which no unit wrote and no stage the loop "
        "can reopen would rewrite"
    )
    # Mutation controls. A unit that wrote the quoted sentence keeps the finding - the
    # "ExportToCSV writes JSON, not CSV" shape, a real defect in a unit's own prose that names a
    # verified symbol - and so does a quote that is only partly a unit's sentence, the unit's
    # prose beside the rendered row it disputes.
    sentence = "core.DiagnosticSeverity ranks warnings above errors."
    wrote_it = {"units": [{**units["units"][0], "text": sentence}]}
    describes = {**f05, "quote": sentence, "absent": []}
    assert scope_defect(describes, candidate, by_id, "", (), unit_texts(wrote_it)) is None
    mixed = {**f05, "quote": f"{sentence} ... {row.split(' ... ')[1]}", "absent": []}
    assert scope_defect(mixed, candidate, by_id, "", (), unit_texts(wrote_it)) is None
    # An empty unit list is a measurement too (nothing wrote it), unlike None (unknown).
    assert scope_defect({**f05, "absent": []}, candidate, by_id, "", (), []) == reason
    # A factuality finding whose quote references no verified symbol keeps its own route.
    plain = _finding("F06", "api_reference", "S6", "It writes `.glb` files.")
    assert scope_defect(plain, candidate, by_id, "", (), []) is None
    # The document: with the units, the rejection has nothing left to act on and BC-10 no longer
    # holds the candidate on this required row; without them it blocks exactly as before.
    output = {"verdict": "REJECT_FACTUAL", "findings": [f05], "preserve": []}
    common: dict[str, Any] = {
        "candidate_readme": candidate,
        "facts": facts,
        "original_readme": original,
    }
    document = review_document(output, REVIEWER, AUTHORING, "d" * 64, units=units, **common)
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"] == reason
    assert deferred_on_required_rows(document) == []
    blocked = review_document(output, REVIEWER, AUTHORING, "d" * 64, **common)
    assert [f["id"] for f in blocked["findings"]] == ["F05"]


def test_a_presentation_finding_contradicting_its_own_cited_fact_is_the_reviewers_defect() -> None:
    """G4-W17 arrival item 63 (lane B LANE-B-R3-F2). `factuality_defect`'s literal-value rule -
    the prompt's own "a quote that contains the literal value of a SUPPORTED fact you cite is
    supported by definition" - ran only for a finding labelled `factuality`. Measured 2026-09-11
    on Aspose.PDF for C++, F08 (`presentation`, `quick_start`): quote `using Aspose_PDF_FOSS
    version 1.0.0.`, `fact_ids` `example:001` and `package:version` (SUPPORTED, `1.0.0`), text
    "the facts do not support a versioned claim" - and `targeted_repair` obeyed it, rewriting the
    unit to end "...using Aspose_PDF_FOSS." A true, fact-backed detail left a public candidate
    because the finding said the opposite of its own citation. The same repository's 2026-09-06
    draw had already lost `1.0.0` twice the same way (repairs.json F07 and F10, each citing
    `package:version`). Scoped to the facts the finding itself cites - never a verbatim scan of
    every SUPPORTED value, which would refold quotes by coincidence (`dependency:none` is `none`),
    the collision item 45 closed."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact("package:name", "package", "Aspose_PDF_FOSS", (Evidence("x"),)),
            Fact("package:version", "package", "1.0.0", (Evidence("x"),)),
            Fact(
                "example:001",
                "example",
                "#include <aspose/pdf/document.hpp>\nint main() { return 0; }",
                (Evidence("x"),),
            ),
            Fact("example:009", "example", "boom()", (Evidence("x"),), polarity="CONTRADICTED"),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    f08 = {
        **_finding("F08", "quick_start", "S6", "using Aspose_PDF_FOSS version 1.0.0."),
        "criterion": "presentation",
        "fact_ids": ["example:001", "package:version"],
        "text": "The candidate adds 'version 1.0.0' to the Quick Start description but the facts "
        "do not support a versioned claim",
        "repair": "Remove 'version 1.0.0'",
    }
    reason = (
        "the quote contains the literal value of SUPPORTED fact package:version ('1.0.0'), which "
        "the finding itself cites as its evidence; literal fact text is supported whatever "
        "criterion the finding files itself under"
    )
    assert scope_defect(f08, CANDIDATE, by_id) == reason
    # The 2026-09-06 draw's F07: the same class with a whole sentence quoted.
    f07 = {
        **f08,
        "id": "F07",
        "quote": "The first example opens an existing PDF file, counts its pages, extracts all "
        "text, and renders the first page to a PNG image at 150 DPI using Aspose_PDF_FOSS 1.0.0.",
        "fact_ids": ["package:version"],
    }
    assert scope_defect(f07, CANDIDATE, by_id) == reason
    # Its factuality-labelled twin still answers through factuality_defect, word for word.
    assert scope_defect({**f08, "criterion": "factuality"}, CANDIDATE, by_id) == (
        "the quote contains the literal value of SUPPORTED fact package:version ('1.0.0'); "
        "literal fact text is supported"
    )
    # Mutation controls: the cited value must be in the quote; a cited CONTRADICTED fact is a
    # real finding (the reviewer names a fact that disproves the quote); citing nothing is one
    # reader's prose judgment and the two-reader rule's to answer; inherited units are not
    # evidence; and an uncited fact whose value the quote happens to carry (package:name here)
    # is never read - the scope is the finding's own citation, nothing wider.
    assert (
        scope_defect({**f08, "quote": "using Aspose_PDF_FOSS version 2.0.0."}, CANDIDATE, by_id)
        is None
    )
    assert (
        scope_defect({**f08, "fact_ids": ["package:version", "example:009"]}, CANDIDATE, by_id)
        is None
    )
    assert scope_defect({**f08, "fact_ids": []}, CANDIDATE, by_id) is None
    maintainer = {
        **f08,
        "quote": "Old prose. using Aspose_PDF_FOSS version 1.0.0.",
        "fact_ids": ["inherited_unit:001.paragraph"],
    }
    assert scope_defect(maintainer, CANDIDATE, by_id) is None
    assert scope_defect({**f08, "fact_ids": ["example:001"]}, CANDIDATE, by_id) is None
    # The document: the finding folds to advisory with its reason, so no repair is ever asked to
    # delete the sentence, and the candidate's true detail stays.
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [f08], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=facts,
    )
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"] == reason
    assert "single_reader_advisory" not in document["advisory"][0]


def test_a_finding_quoting_evidence_the_facts_exclude_is_the_reviewers_defect() -> None:
    """Asking for an example that did not execute asks the contract to break its own check 3.

    Measured 2026-09-06: Aspose.Slides was held unsealed by "the candidate omits the Markdown
    export example entirely", quoting example:015 - CONTRADICTED, the one example of fifteen the
    plan could not carry. The reviewer left `absent` empty, so absence_defect had nothing to
    look up; the quote it did fill says the same thing.
    """
    broken = "from aspose.slides_foss.export import SaveFormat, MarkdownSaveOptions, NewLineType"
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact("example:015", "example", broken, (Evidence("x"),), polarity="CONTRADICTED"),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    asks_for_it = {
        **_finding("F04", "additional_examples", "S6", broken),
        "criterion": "presentation",
        "fact_ids": [],
    }
    assert scope_defect(asks_for_it, CANDIDATE, by_id) == (
        "the quote is example:015, which is CONTRADICTED: the contract admits it only once the "
        "evidence supports it, so no stage the loop can reopen would write it"
    )
    # Mutation: the same quote against a SUPPORTED fact stands, a short quote is never matched
    # this way, and a finding quoting the candidate's own prose is untouched.
    supported = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (*FACTS.facts, Fact("example:015", "example", broken, (Evidence("x"),))),
    )
    assert scope_defect(asks_for_it, CANDIDATE, {f.id: f for f in supported.facts}) is None
    brief = {**asks_for_it, "quote": broken[:20]}
    assert scope_defect(brief, CANDIDATE, by_id) is None
    own = {**asks_for_it, "quote": "It writes `.glb` files."}
    assert scope_defect(own, CANDIDATE, by_id) is None


def test_an_omission_finding_naming_excluded_evidence_is_the_reviewers_defect_too() -> None:
    """The same excluded-evidence rule, read from `fact_ids` rather than a matching quote.

    Measured 2026-09-06 on Aspose.3D for .NET: the finding quoted the section's ordinary lead-in
    - not `example:003`'s own value - and named the omission through `absent` and `fact_ids`
    instead. `example:003` is CONTRADICTED (its heading was genuinely written by the maintainer,
    so `absence_defect` finds it in evidence and lets the finding stand); the omission is
    correct, and no stage would restore an example that did not execute.
    """
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact("example:003", "example", "boom()", (Evidence("x"),), polarity="CONTRADICTED"),
        ),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    omission = {
        **_finding("F03", "additional_examples", "S7", "Additional examples cover the basics."),
        "criterion": "presentation",
        "fact_ids": ["example:003"],
        "absent": ["Enumerate a Scene's Node Hierarchy"],
    }
    assert scope_defect(omission, CANDIDATE, by_id) == (
        "the omission it names is backed by example:003, which is CONTRADICTED: the contract "
        "admits it only once the evidence supports it, so no stage the loop can reopen would "
        "write it"
    )
    # Mutation: a SUPPORTED backing fact stands, and a factuality finding with no absence claim
    # - the ordinary way a contradicted fact disproves existing text - is untouched.
    supported = {
        f.id: f
        for f in FactsDocument(
            ENTRY.repository,
            "a" * 40,
            (*FACTS.facts, Fact("example:003", "example", "boom()", (Evidence("x"),))),
        ).facts
    }
    assert scope_defect(omission, CANDIDATE, supported) is None
    factuality = {
        **_finding("F10", "structure", "S6", "It writes `.glb` files."),
        "fact_ids": ["example:003"],
    }
    assert scope_defect(factuality, CANDIDATE, by_id) is None


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


def test_a_factuality_labelled_finding_against_renderer_owned_text_is_the_reviewers_defect() -> (
    None
):
    """G4-W17 arrival item 37. The exemption for content the renderer owns used to be gated on
    the finding's own `criterion`, so the identical finding against the identical text was the
    reviewer's defect when it labelled itself presentation and blocked when it labelled itself
    factuality - while `absence_defect` beside it has always judged whatever the label says.

    Measured 2026-09-06 on Aspose.Cells for Java, whose BC-10 REJECT_FACTUAL rested on three
    findings, two of them this shape: F01 quoted the LLM-owned opening section's own prose but
    named the deterministic `identity` row, so the repair loop trusted the label and abandoned it;
    F03 quoted the renderer's own rendering of a SUPPORTED `dependency:none` fact, calling it
    contradicted by the Development Dependencies list the renderer prints nine lines below from
    the same fact set. Neither reached the rule, and neither could be repaired by any unit.
    """
    candidate = (
        "# Aspose.Cells FOSS for Java\n\nIt writes `.glb` files.\n\n## Dependencies\n\n"
        "This library has no required package dependencies.\n\n"
        "#### Development Dependencies\n\n- `junit`\n\n"
        f"## Additional Examples\n\n{ADDITIONAL_EXAMPLES_SUMMARY}\n"
    )
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (*FACTS.facts, Fact("dependency:none", "dependency", "none", (Evidence("x"),))),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    dependencies = (
        "section dependencies renders from facts under the contract's own checks; its "
        "presentation is the renderer's, and a factual error there is a factuality finding"
    )
    # F03: the renderer's own rendering of a SUPPORTED fact, called false. The candidate really
    # carries it, so the quote check has nothing to say and only the scope rule can answer.
    rendered_fact = _finding(
        "F03", "dependencies", "S6", "This library has no required package dependencies."
    )
    assert review_checks({"findings": [rendered_fact]}, candidate, facts) == []
    assert scope_defect(rendered_fact, candidate, by_id) == dependencies
    # Its presentation-labelled twin, which already held, answers identically: the label is no
    # longer what decides.
    assert scope_defect({**rendered_fact, "criterion": "presentation"}, candidate, by_id) == (
        dependencies
    )
    # F01: a deterministic row named by a finding whose quote is a unit's prose. The row is still
    # the renderer's, so no revision the loop can ask for would change what the finding names.
    mislabelled = _finding("F01", "identity", "S6", "It writes `.glb` files.")
    assert scope_defect(mislabelled, candidate, by_id) == (
        "section identity renders from facts under the contract's own checks; its presentation "
        "is the renderer's, and a factual error there is a factuality finding"
    )
    # The heading and collapsible-summary exemptions are label-independent for the same reason:
    # the quote is the renderer's exact text, in a section units otherwise own.
    heading = _finding("F04", "api_reference", "S6", "#### Detailed Member Reference")
    assert scope_defect(heading, candidate, by_id) == (
        "the quote is the heading 'Detailed Member Reference', which the renderer emits because "
        "the contract's shell requires it; no unit wrote it and none can change it"
    )
    chrome = _finding("F05", "additional_examples", "S6", ADDITIONAL_EXAMPLES_SUMMARY)
    assert scope_defect(chrome, candidate, by_id) == (
        f"the quote is {ADDITIONAL_EXAMPLES_SUMMARY!r}, the renderer's own collapsible-summary "
        "text; no unit wrote it and none can change it"
    )
    # The unblock this buys: a rejection whose findings are all the reviewer's own defect has
    # nothing the loop can act on, so BC-10 no longer holds the candidate on a required row.
    document = review_document(
        {"verdict": "REJECT_FACTUAL", "findings": [rendered_fact], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=candidate,
        facts=facts,
    )
    assert document["verdict"] == ACCEPT and document["findings"] == []
    assert document["advisory"][0]["reviewer_scope_defect"] == dependencies
    assert document["advisory"][0]["causal_stage"] == "S6"
    assert deferred_on_required_rows(document) == []


def test_a_factuality_finding_against_a_units_own_prose_is_never_exempted() -> None:
    """The mutation control for G4-W17 arrival item 37: label independence exempts content the
    renderer wrote, never more content than before.

    Three things the label still decides. Two exemptions stay presentation-only, because a
    factuality claim about the same text is a claim about the facts and may be true: `structure`
    is the label a reviewer reaches for when a finding belongs to no section, so a false claim
    anywhere in the document arrives under it; and BC-04 verifies that an identifier a unit names
    is a real fact value, never that the sentence around it is accurate. And a criterion outside
    the two a reviewer uses for text it is reading keeps its own route entirely: a completeness
    finding against a deterministic section says the fact set that section renders from is short,
    which S2 can reopen - `test_present_records_an_unrepairable_finding_as_advisory_and_stops`
    measures that route end to end.
    """
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (*FACTS.facts, Fact("dependency:none", "dependency", "none", (Evidence("x"),))),
    )
    by_id = {fact.id: fact for fact in facts.facts}
    # A section a unit owns, quoting the unit's own prose: the finding stands, as it always did.
    authored = _finding("F06", "key_capabilities", "S6", "It writes `.glb` files.")
    assert scope_defect(authored, CANDIDATE, by_id) is None
    # The document-shape exemption is not extended: this is a real claim under a catch-all label.
    on_structure = _finding("F07", "structure", "S6", "It writes `.glb` files.")
    assert scope_defect(on_structure, CANDIDATE, by_id) is None
    assert scope_defect({**on_structure, "criterion": "presentation"}, CANDIDATE, by_id) is not None
    # Nor is the BC-04 exemption: "Sym7 writes JSON" is wrong about a symbol BC-04 only proved
    # exists, and a factuality finding is the one route left for saying so.
    describes = _finding("F08", "api_reference", "S6", "- `pkg.Sym7`: Sym7 writes JSON, not GLB.")
    assert scope_defect(describes, CANDIDATE, by_id) is None
    assert scope_defect({**describes, "criterion": "presentation"}, CANDIDATE, by_id) is not None
    # A factuality finding citing a contradicting fact still routes through factuality_defect.
    cited = {**authored, "fact_ids": ["inherited_unit:001.paragraph"]}
    assert scope_defect(cited, CANDIDATE, by_id) is not None
    # A completeness finding against a deterministic section reports that the fact set is short,
    # not that the renderer's wording is wrong, so it keeps the S2 route it always had.
    short = {
        **_finding("F09", "installation", "S2", "pip install aspose-3d-foss"),
        "criterion": "completeness",
        "fact_ids": [],
    }
    assert scope_defect(short, CANDIDATE, by_id) is None


def test_a_factuality_finding_naming_no_fact_and_no_absence_is_the_reviewers_defect() -> None:
    """G4-W17 arrival item 39. `factuality_defect` stood unconditionally whenever a finding
    cited no product fact_ids, on the reasoning that "no fact supports this claim" cites
    nothing to check - true when the finding names its omission through `absent` instead, which
    `absence_defect` already judges before `factuality_defect` is ever reached. But a factuality
    finding naming NEITHER cites nothing for any deterministic check in `scope_defect` to measure
    it against, so it passed every one of them by construction and could block a candidate on an
    assertion nothing could ever disprove or fix. Measured 2026-09-07, Aspose.Cells for Java,
    finding F07: its own quote WAS the sentence it called missing, empty `fact_ids`, empty
    `absent` - byte-identical on re-ask, repair recorded it repaired and it re-raised identically.
    """
    by_id = {fact.id: fact for fact in FACTS.facts}
    ungrounded = {
        **_finding("F07", "key_capabilities", "S6", "It writes `.glb` files."),
        "fact_ids": [],
        "absent": [],
    }
    assert scope_defect(ungrounded, CANDIDATE, by_id) == (
        "a factuality finding names neither a product fact_id to contradict the quote nor an "
        "absent claim of missing text: nothing in evidence supports judging it"
    )
    # Mutation control: naming either one still routes to its own existing check, not this new
    # one - the fix must not swallow a real, checkable finding either way.
    with_fact_id = {**ungrounded, "fact_ids": ["format:input.obj"]}
    assert scope_defect(with_fact_id, CANDIDATE, by_id) is None  # UNRESOLVED, not CONTRADICTED
    with_absent = {**ungrounded, "absent": ["It writes `.glb` files."]}
    assert scope_defect(with_absent, CANDIDATE, by_id) is not None  # absence_defect's own route:
    # the candidate contains exactly what the finding claims is missing.


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
#
# Deliberately reads the real, current canary bundle off disk, the same way
# tests/test_sealed_bytes.py does (CS-05, plans/healing/ci-staleness-followup.md, 2026-09-09):
# this checks real, evolving content (the real advisories a real sealed review currently
# carries), not a structural shape a frozen fixture could stand in for.
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
