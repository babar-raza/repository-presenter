"""A failed second-reader job must never be mistaken for a completed, corroborating one.

Also covers `_refuse_noop` / `_stage_target`'s no-op refusal (RESEARCH_LANE_E.md E16, arrival
item 84): a repair reply proven identical to the causal stage's own output must never clear the
checks a genuine revision would have to pass.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from repository_presenter.components.readme.repair.rounds import (
    Round,
    _refuse_noop,
    _second_opinion,
    _stage_target,
    _third_opinion,
)
from repository_presenter.components.readme.repair.targeted import Defect
from repository_presenter.components.readme.review.independent.review import (
    MAJORITY_VOTE_REPOSITORIES,
)
from repository_presenter.core.errors import JobError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import JobResult
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

MANIFESTS = load_manifests(REPO_ROOT / "prompts")
LOADED = MANIFESTS["independent_review"]
PACKET: dict[str, Any] = {}
COMMON: dict[str, Any] = {}


def test_a_failed_second_reader_job_returns_none_not_an_empty_dict() -> None:
    """TB-04, external review D4: review_document reads `second={}` as a *completed* reading
    that corroborated nothing, silently demoting a real blocking finding to advisory and
    flipping REJECT_PRESENTATION to ACCEPT. `_second_opinion` must return None on JobError -
    the caller (rounds.py's run_round) then leaves the first reader's review untouched, exactly
    as if no second reading had ever been attempted."""
    with patch(
        "repository_presenter.components.readme.repair.rounds.run_job",
        side_effect=JobError("gateway unavailable"),
    ):
        assert _second_opinion(LOADED, PACKET, None, COMMON) is None


def test_a_successful_second_reader_job_returns_its_output() -> None:
    result = JobResult(
        job="independent_review",
        output={"findings": [], "verdict": "ACCEPT", "preserve": []},
        request_sha256="a" * 64,
        attempts=1,
        provider_calls=1,
        cache_reused=False,
        model_served="qwen3-next",
        total_tokens=100,
    )
    with patch("repository_presenter.components.readme.repair.rounds.run_job", return_value=result):
        assert _second_opinion(LOADED, PACKET, None, COMMON) == result.output


def test_a_failed_third_reader_job_returns_none_not_an_empty_dict() -> None:
    """Section 5.6's 2-of-3 escalation mirrors `_second_opinion` exactly: a failed third read
    (JobError) must return None, never `{}`, so `review_document` never mistakes it for a
    completed reading that corroborated nothing (the same TB-04 rule the second reader has)."""
    with patch(
        "repository_presenter.components.readme.repair.rounds.run_job",
        side_effect=JobError("gateway unavailable"),
    ):
        assert _third_opinion(LOADED, PACKET, None, COMMON) is None


def test_a_successful_third_reader_job_returns_its_output() -> None:
    result = JobResult(
        job="independent_review",
        output={"findings": [], "verdict": "ACCEPT", "preserve": []},
        request_sha256="a" * 64,
        attempts=1,
        provider_calls=1,
        cache_reused=False,
        model_served="qwen3-next",
        total_tokens=100,
    )
    with patch("repository_presenter.components.readme.repair.rounds.run_job", return_value=result):
        assert _third_opinion(LOADED, PACKET, None, COMMON) == result.output


def test_the_escalation_set_is_exactly_the_three_documented_repositories() -> None:
    """`run_round` gates the 2-of-3 escalation on `tx.entry.repository in
    MAJORITY_VOTE_REPOSITORIES` alone (section 5.6) - a repository not named here takes the
    unchanged single-confirming-read path no matter how this test module's own fixtures are set
    up, since nothing else in `run_round` can trigger the third read."""
    assert {
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    } == MAJORITY_VOTE_REPOSITORIES
    assert "aspose-3d-foss/Aspose.3D-FOSS-for-Python" not in MAJORITY_VOTE_REPOSITORIES


def _stub_job_result(output: dict[str, Any]) -> JobResult:
    return JobResult(
        job="x",
        output=output,
        request_sha256="a" * 64,
        attempts=1,
        provider_calls=1,
        cache_reused=False,
        model_served=None,
        total_tokens=0,
    )


def _minimal_round(planned_output: dict[str, Any]) -> Round:
    return Round(
        investigation=_stub_job_result({}),
        reconciled={},
        dispositions={},
        planned=_stub_job_result(planned_output),
        authored={},
        tasks=[],
        units={},
        coherent={"coherence#1": _stub_job_result({})},
        revised=[],
        readme="",
        validation={},
    )


def test__refuse_noop_rejects_a_revision_identical_to_the_original_before_delegating() -> None:
    """Before this fix, nothing compared a repair's `revised_output` to the causal stage's own
    output it was meant to revise - a no-op cleared every check and was recorded "repaired"
    (measured on Font for Python's BC-07 length-budget defect, RESEARCH_LANE_E.md E16). The
    wrapped checks must refuse the no-op before the stage's own checks even run, and must still
    delegate normally to a genuine revision."""
    original = {"api_hubs": ["a", "b"]}
    calls: list[dict[str, Any]] = []

    def inner(revised: dict[str, Any]) -> list[str]:
        calls.append(revised)
        return ["some other stage-specific error"]

    guarded = _refuse_noop(original, inner)

    errors = guarded({"api_hubs": ["a", "b"]})  # equal by value, a fresh object
    assert errors and all("stage-specific" not in error for error in errors)
    assert any("no-op" in error and "unchanged" in error for error in errors)
    assert calls == []  # the inner checks never ran - the no-op was caught first

    different = {"api_hubs": ["a"]}
    assert guarded(different) == ["some other stage-specific error"]
    assert calls == [different]


def test__refuse_noop_with_no_inner_checks_still_refuses_a_no_op() -> None:
    """S3 (`repository_investigation`) carries no stage-specific checks at all -
    `_stage_target` passes `_refuse_noop` a bare `None`. A no-op must still be refused, and a
    genuine revision must still pass through with no errors."""
    original = {"summary": "x"}
    guarded = _refuse_noop(original, None)
    assert guarded(dict(original)) != []
    assert guarded({"summary": "y"}) == []


def test__stage_target_s5_refuses_a_revision_identical_to_the_plan_it_would_repair() -> None:
    """The exact measured case: a repair asked to shrink an already schema-maximal plan
    (`composition/policy.py`'s `capabilities_max`/`api_hubs_max`) returned the same plan back.
    Before this fix, `_stage_target`'s S5 branch handed the repair `plan_checks` alone, which has
    no visibility into whether anything changed. Red before this fix (the returned checks were
    bare `plan_checks`, which never mentions "no-op" or "unchanged" for a self-consistent plan),
    green after (the wrapped checks refuse the identical reply before `plan_checks` runs)."""
    facts = FactsDocument("owner/repo", "r" * 40, ())
    plan = {"api_hubs": [{"symbol_fact_id": "public_symbol:x"}], "core_capabilities": []}
    current = _minimal_round(plan)
    defect = Defect("fp", "validation", "BC-07", None, "S5", {})

    target, stage_checks, allowed, slot_facts, stage_facts = _stage_target(
        current, defect, facts, "Product", "python"
    )

    assert target is current.planned
    assert allowed is None
    assert slot_facts is None
    assert stage_facts is facts

    errors = stage_checks(current.planned.output)
    assert any("no-op" in error and "unchanged" in error for error in errors)
