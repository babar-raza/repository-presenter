"""A failed second-reader job must never be mistaken for a completed, corroborating one.

Also covers `_refuse_noop` / `_stage_target`'s no-op refusal (RESEARCH_LANE_E.md E16, arrival
item 84): a repair reply proven identical to the causal stage's own output must never clear the
checks a genuine revision would have to pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from repository_presenter.components.readme.repair.rounds import (
    Round,
    _refuse_noop,
    _reject_insufficient_visible_line_overage,
    _second_opinion,
    _stage_target,
    _third_opinion,
    repair_defect,
)
from repository_presenter.components.readme.repair.targeted import Defect, RepairLedger
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


def test_a_successful_second_reader_job_returns_its_own_job_result() -> None:
    """G5-W02: `_second_opinion` returns the whole `JobResult`, not merely `.output` - the caller
    needs `.request_sha256` too, to seal this read's own raw output under its own key in
    raw_calls.json (`review.json` alone cannot always answer for a second read verbatim)."""
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
        assert _second_opinion(LOADED, PACKET, None, COMMON) == result


def test_a_failed_third_reader_job_returns_none_not_an_empty_dict() -> None:
    """Section 5.6's 2-of-3 escalation mirrors `_second_opinion` exactly: a failed third read
    (JobError) must return None, never `{}`, so `review_document` never mistakes it for a
    completed reading that corroborated nothing (the same TB-04 rule the second reader has)."""
    with patch(
        "repository_presenter.components.readme.repair.rounds.run_job",
        side_effect=JobError("gateway unavailable"),
    ):
        assert _third_opinion(LOADED, PACKET, None, COMMON) is None


def test_a_successful_third_reader_job_returns_its_own_job_result() -> None:
    """Mirrors `test_a_successful_second_reader_job_returns_its_own_job_result` (G5-W02)."""
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
        assert _third_opinion(LOADED, PACKET, None, COMMON) == result


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


# BC-10 F06 on Aspose.3D for TypeScript (2026-10-04): the scope_limitations units as authored.
F06_UNITS: dict[str, Any] = {
    "omitted": [],
    "units": [
        {
            "slot": "limitation:1",
            "section": "scope_limitations",
            "text": "The package is installed by cloning the repository.",
            "fact_ids": ["identity:repository"],
        },
        {
            "slot": "limitation:2",
            "section": "scope_limitations",
            "text": "Rendering is not functional in this FOSS build.",
            "fact_ids": ["example:001"],
        },
    ],
}


def _f06_reply_moving_only_citations() -> dict[str, Any]:
    """Five of F06's repairs (2026-10-04) returned every unit's text unchanged, each change claimed
    before == after, and moved only fact_ids and the omitted list. That is the shape tested here."""
    return {
        "omitted": [{"fact_id": "inherited_unit:074.list", "reason": "not used"}],
        "units": [
            {**F06_UNITS["units"][0], "fact_ids": ["identity:repository", "package:name"]},
            {**F06_UNITS["units"][1], "fact_ids": ["example:001", "example:003"]},
        ],
    }


def test_a_review_repair_that_reprints_the_same_text_is_a_noop_whatever_it_cites() -> None:
    """Before this fix, `_refuse_noop` compared whole objects, so a reply that re-cited the same
    printed text (different fact_ids, a different omitted list) was a "different" output, cleared
    the stage's checks, and was recorded "repaired" - five times on F06, which then re-raised
    unchanged. A review finding is a judgement about printed prose; a reply that prints what its
    input printed cannot resolve it, however it cites that text. The stage's own checks never run
    on it, and a genuine change to the printed text still reaches them."""
    seen: list[dict[str, Any]] = []

    def inner(revised: dict[str, Any]) -> list[str]:
        seen.append(revised)
        return []

    reply = _f06_reply_moving_only_citations()
    errors = _refuse_noop(F06_UNITS, inner, prose=True)(reply)
    assert errors and "no-op" in errors[0] and "unchanged" in errors[0]
    assert seen == []

    edited = _f06_reply_moving_only_citations()
    edited["units"][1]["text"] = "Rendering, 3MF import and export, and text watermarking are off."
    assert _refuse_noop(F06_UNITS, inner, prose=True)(edited) == []
    assert seen == [edited]


def test_a_review_plan_recital_is_refused_but_a_validation_citation_is_not() -> None:
    """Through `_stage_target` (the real seam), for a plan (S5) defect: a review finding's reply
    that moves only the plan's fact_ids is refused as a no-op. The same citation-only reply for a
    validation defect is not: a fact citation can be the whole repair a validation check asks for,
    and that check re-judges it."""
    facts = FactsDocument("owner/repo", "r" * 40, ())
    plan = {
        "api_hubs": [{"symbol_fact_id": "public_symbol:x", "fact_ids": ["public_symbol:x"]}],
        "core_capabilities": [],
    }
    current = _minimal_round(plan)
    recited = {
        "api_hubs": [
            {
                "symbol_fact_id": "public_symbol:x",
                "fact_ids": ["public_symbol:x", "identity:repository"],
            }
        ],
        "core_capabilities": [],
    }

    review = Defect("fp-review", "review", "F05", None, "S5", {})
    _, review_checks, *_ = _stage_target(current, review, facts, "Product", "python")
    assert any("no-op" in error and "unchanged" in error for error in review_checks(recited))

    validation = Defect("fp-check", "validation", "BC-04", None, "S5", {})
    _, check_checks, *_ = _stage_target(current, validation, facts, "Product", "python")
    assert not any("no-op" in error for error in check_checks(recited))


def test_a_prose_noop_is_judged_by_printed_text_and_a_validation_one_still_by_identity() -> None:
    """The helper's own contract: provenance keys are dropped at every depth, a review finding's
    no-op is decided on what is printed, and a validation defect's is decided by the whole object
    (so its fact-citation repairs are never mistaken for a no-op)."""
    from repository_presenter.components.readme.repair.rounds import (
        printed_content,
        prose_repair_is_noop,
    )

    nested = {"text": "a", "fact_ids": ["x"], "more": {"fact_ids": [], "k": 2}}
    assert printed_content({"omitted": [1], "units": [nested]}) == {
        "units": [{"text": "a", "more": {"k": 2}}]
    }
    review = Defect("fp", "review", "F06", "scope_limitations", "S6", {})
    validation = Defect("fp2", "validation", "BC-04", "scope_limitations", "S6", {})
    reply = _f06_reply_moving_only_citations()
    assert prose_repair_is_noop(review, reply, F06_UNITS)
    assert not prose_repair_is_noop(validation, reply, F06_UNITS)


def test_repair_defect_never_records_a_review_reply_that_printed_nothing_new_as_repaired(
    tmp_path: Path,
) -> None:
    """The record itself, through `repair_defect`: a review finding whose printed text is unchanged
    is recorded unrepairable with the reason, so it is never reported resolved; the same reply for
    a validation defect is still recorded repaired (its check re-judges it)."""
    facts = FactsDocument("owner/repo", "r" * 40, ())
    changes = [
        {
            "id": "R01",
            "path": "revised_output.units[0].text",
            "before": "x",
            "after": "x",
        }
    ]
    for source, expected in (("review", "unrepairable"), ("validation", "repaired")):
        defect = Defect(f"fp-{source}", source, "F06", None, "S5", {})
        target = _stub_job_result(F06_UNITS)
        reply = {"revised_output": _f06_reply_moving_only_citations(), "changes": changes}
        repairs = RepairLedger(tmp_path / f"{source}.json", composition="c")
        with (
            patch(
                "repository_presenter.components.readme.repair.rounds.product_name",
                return_value="Product",
            ),
            patch(
                "repository_presenter.components.readme.repair.rounds._stage_target",
                return_value=(target, None, None, None, facts),
            ),
            patch(
                "repository_presenter.components.readme.repair.rounds.run_job",
                return_value=_stub_job_result(reply),
            ),
            patch("repository_presenter.components.readme.repair.rounds.repair_packet"),
            patch("repository_presenter.components.readme.repair.rounds.repair_schema"),
        ):
            repair_defect(MagicMock(), MagicMock(), defect, repairs)
        attempt = repairs.attempts[defect.fingerprint]
        assert attempt["outcome"] == expected
        if expected == "unrepairable":
            assert "unchanged" in attempt["reason"] and "no-op" in attempt["reason"]


def test_reject_insufficient_visible_line_overage_rejects_only_when_every_lever_is_untouched() -> (
    None
):
    """G4-W17 (docs/DECISION_LOG.md 2026-09-17 10:24 UTC, 2026-09-27 05:14 UTC): measured live on
    aspose-font-foss/Aspose.Font-FOSS-for-Python, a repair packet naming the exact lever cost was
    not, on its own, enough - two independent live draws each made an unrelated, self-reported
    no-op edit instead. This check gives the job's one universal re-ask something concrete to
    react to: a reply that leaves every named lever field exactly as the causal stage's own output
    had it is rejected; clearing even one is accepted (the model's own choice of which, or how
    many, is never second-guessed)."""
    hint = {
        "visible_lines_over_budget": 12,
        "optional_plan_fields_and_their_visible_line_cost_if_cleared": {
            "flagship_example_id": 125,
            "second_quick_start_example_id": 7,
        },
    }
    guarded = _reject_insufficient_visible_line_overage(None, hint)
    untouched = {
        "flagship_example_id": "example:008",
        "second_quick_start_example_id": "example:001",
    }
    errors = guarded(untouched)
    assert (
        len(errors) == 1 and "12 visible lines" in errors[0] and "flagship_example_id" in errors[0]
    )
    # Clearing even one of the two named levers is accepted - never rejected for using "only one".
    assert guarded({**untouched, "flagship_example_id": None}) == []
    assert guarded({**untouched, "second_quick_start_example_id": None}) == []
    # A field the hint never named is irrelevant to this check either way.
    assert guarded({**untouched, "quick_start_example_id": "example:003"}) != []


def test_reject_insufficient_visible_line_overage_composes_with_the_stages_own_checks() -> None:
    """This wrapper layers onto whatever stage_checks the causal stage already carries - an
    unrelated plan_checks failure still surfaces even when a lever was correctly cleared, and both
    errors appear together when neither is satisfied."""
    hint = {
        "visible_lines_over_budget": 5,
        "optional_plan_fields_and_their_visible_line_cost_if_cleared": {"flagship_example_id": 60},
    }

    def inner(revised: dict[str, Any]) -> list[str]:
        return ["an unrelated plan_checks failure"]

    guarded = _reject_insufficient_visible_line_overage(inner, hint)
    cleared = guarded({"flagship_example_id": None})
    assert cleared == ["an unrelated plan_checks failure"]
    both = guarded({"flagship_example_id": "example:008"})
    assert "an unrelated plan_checks failure" in both
    assert any("visible lines" in error for error in both)
