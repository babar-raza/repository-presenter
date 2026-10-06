"""A failed second-reader job must never be mistaken for a completed, corroborating one.

Also covers `_refuse_noop` / `_stage_target`'s no-op refusal (RESEARCH_LANE_E.md E16, arrival
item 84): a repair reply proven identical to the causal stage's own output must never clear the
checks a genuine revision would have to pass.
"""

from __future__ import annotations

import functools
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from repository_presenter.components.readme.bundle.seal import seed_additional_calls
from repository_presenter.components.readme.composition.authoring import (
    RAW_CALLS_FILENAME,
    write_raw_calls,
)
from repository_presenter.components.readme.repair.rounds import (
    Round,
    _read_review,
    _refuse_noop,
    _reject_insufficient_visible_line_overage,
    _round_raw_calls,
    _second_opinion,
    _stage_target,
    _third_opinion,
    _with_carried_units,
    repair_defect,
)
from repository_presenter.components.readme.repair.targeted import Defect
from repository_presenter.components.readme.review.independent.review import (
    review_document,
)
from repository_presenter.core.errors import JobError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import CallStore, JobResult
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


def _judged_review(
    first: dict[str, Any], deferrals: list[str], second: JobResult | None, third: JobResult | None
) -> tuple[dict[str, Any], list[str]]:
    """Runs `_read_review` with stub reads, recording which reads were requested."""
    calls: list[str] = []
    document = functools.partial(review_document, first, LOADED, LOADED, "d" * 64)

    def run_second() -> JobResult | None:
        calls.append("second")
        return second

    def run_third() -> JobResult | None:
        calls.append("third")
        return third

    review, _decision, _second, _third = _read_review(document, deferrals, run_second, run_third)
    return review, calls


_CLEAN = {"verdict": "ACCEPT", "findings": [], "preserve": []}
_BLOCKING = {
    "id": "F01",
    "section_id": "key_capabilities",
    "causal_stage": "S6",
    "criterion": "factuality",
    "text": "A claim is unsupported.",
    "quote": "",
    "fact_ids": [],
    "absent": [],
    "omission": None,
    "repair": "Drop the claim.",
}


def test_a_clean_accept_with_no_trigger_makes_no_second_call() -> None:
    """The unconditional second read on every ACCEPT is gone: a clean first ACCEPT whose trigger
    does not fire is one read, and the record says so."""
    review, calls = _judged_review(_CLEAN, [], second=_stub_job_result(_CLEAN), third=None)
    assert calls == []
    assert review["second_reader"]["read"] == 1
    assert review["second_reader"]["trigger"] == {"triggered": False, "reasons": []}


def test_a_blocking_deferral_alone_makes_no_second_call() -> None:
    _review, calls = _judged_review(_CLEAN, ["BLOCK"], second=_stub_job_result(_CLEAN), third=None)
    assert calls == []


def test_an_advisory_deferral_requests_one_second_read_and_records_the_reason() -> None:
    review, calls = _judged_review(
        _CLEAN, ["ADVISORY"], second=_stub_job_result(_CLEAN), third=None
    )
    assert calls == ["second"]
    assert review["second_reader"]["read"] == 2
    assert review["second_reader"]["trigger"] == {
        "triggered": True,
        "reasons": ["ADVISORY_DEFERRAL"],
    }


def test_a_prose_judgment_on_a_required_row_requests_the_second_read() -> None:
    judgment = {
        **_BLOCKING,
        "criterion": "presentation",
        "fact_ids": [],
        "section_id": "key_capabilities",
    }
    review, calls = _judged_review(
        {"verdict": "REJECT_PRESENTATION", "findings": [judgment], "preserve": []},
        [],
        second=_stub_job_result(_CLEAN),
        third=None,
    )
    assert calls == ["second"]
    assert review["second_reader"]["trigger"]["reasons"] == ["PROSE_JUDGMENT_ON_REQUIRED_ROW"]


def test_a_triggered_second_read_that_fails_leaves_the_trigger_unsatisfied() -> None:
    """A failed triggered read is None, never {}: the first reader's review stands, one read, with
    the trigger recorded as fired, so check 10 fails it (losing verification never raises
    assurance)."""
    review, calls = _judged_review(_CLEAN, ["ADVISORY"], second=None, third=None)
    assert calls == ["second"]
    assert review["second_reader"]["read"] == 1
    assert review["second_reader"]["trigger"]["triggered"] is True


def test_a_second_read_disagreeing_with_a_clean_first_read_requests_the_third() -> None:
    disagreeing = {"verdict": "REJECT_FACTUAL", "findings": [_BLOCKING], "preserve": []}
    review, calls = _judged_review(
        _CLEAN,
        ["ADVISORY"],
        second=_stub_job_result(disagreeing),
        third=_stub_job_result(disagreeing),
    )
    assert calls == ["second", "third"]
    assert review["second_reader"]["read"] == 3
    assert review["verdict"] == "REJECT_FACTUAL"


def test_a_single_dissenting_extra_reader_is_tolerated_by_the_two_of_three_vote() -> None:
    disagreeing = {"verdict": "REJECT_FACTUAL", "findings": [_BLOCKING], "preserve": []}
    review, calls = _judged_review(
        _CLEAN, ["ADVISORY"], second=_stub_job_result(disagreeing), third=_stub_job_result(_CLEAN)
    )
    assert calls == ["second", "third"]
    assert review["verdict"] == "ACCEPT"


def test_a_failed_third_read_falls_back_to_the_single_confirming_rule() -> None:
    """Negative control: when the third read cannot complete, the second read's dissent blocks
    exactly as the single-confirming-read rule always did - never a looser outcome."""
    disagreeing = {"verdict": "REJECT_FACTUAL", "findings": [_BLOCKING], "preserve": []}
    review, calls = _judged_review(
        _CLEAN, ["ADVISORY"], second=_stub_job_result(disagreeing), third=None
    )
    assert calls == ["second", "third"]
    assert review["verdict"] == "REJECT_FACTUAL"
    assert review["second_reader"]["read"] == 2


def test_the_review_decision_cannot_depend_on_the_repository_identity() -> None:
    """Restores the property the removed MAJORITY_VOTE_REPOSITORIES membership check enforced: no
    repository is escalated by identity. The second read, the third read and the vote are decided
    by the candidate's typed facts alone. `_read_review` takes no repository, entry or
    repository-keyed set, so reintroducing an identity gate (a repository parameter) fails here;
    a clean, untriggered accept makes no call for any repository, including the three repositories
    the removed set named and the canary."""
    import inspect

    names = set(inspect.signature(_read_review).parameters)
    assert not {n for n in names if "repo" in n or "entry" in n or "majority" in n}
    for repository in (
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    ):
        review, calls = _judged_review(_CLEAN, [], second=_stub_job_result(_CLEAN), third=None)
        assert calls == [] and review["second_reader"]["read"] == 1, repository


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
        current,
        defect,
        facts,
        "Product",
        "python",
        MANIFESTS,
    )

    assert target is current.planned
    assert allowed is None
    assert slot_facts is None
    assert stage_facts is facts

    errors = stage_checks(current.planned.output)
    assert any("no-op" in error and "unchanged" in error for error in errors)


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


def _batch_result(request_sha256: str, dispositions: list[dict[str, Any]]) -> JobResult:
    return JobResult(
        job="source_reconciliation",
        output={"dispositions": dispositions},
        request_sha256=request_sha256,
        attempts=1,
        provider_calls=1,
        cache_reused=False,
        model_served="qwen3-next",
        total_tokens=100,
    )


def test_every_reconciliation_batch_is_sealed_so_a_fresh_clone_replays_it_with_zero_calls(
    tmp_path: Path,
) -> None:
    """A multi-batch source_reconciliation round (Aspose.Slides-FOSS-for-.NET, 95 units) made 3
    dispositions calls on a fresh hosted runner: dispositions.json holds only the merged document,
    and seed_call_store never seeds a job with more than one successful attempt, so no sealed
    artifact answered those batches. Each batch's own accepted output must seal in raw_calls.json
    under its own request hash, so seed_additional_calls answers the same request a fresh process
    would compute, byte for byte."""
    first = _batch_result("b" * 64, [{"unit": "u1"}])
    second = _batch_result("c" * 64, [{"unit": "u2"}, {"unit": "u3"}])
    raw_calls = _round_raw_calls(
        {"reconciliation#1": first, "reconciliation#2": second}, {}, {}, []
    )
    assert raw_calls == {
        "b" * 64: {"job": "source_reconciliation", "output": first.output},
        "c" * 64: {"job": "source_reconciliation", "output": second.output},
    }
    write_raw_calls(raw_calls, tmp_path / RAW_CALLS_FILENAME)
    store = CallStore(tmp_path / "calls")
    assert seed_additional_calls(tmp_path, store) == ["source_reconciliation"]
    assert store.get("b" * 64) == first.output
    assert store.get("c" * 64) == second.output


def test_a_repair_recovery_records_an_uncarried_superseded_unit_inside_revised_output() -> None:
    """Aspose.Slides for Java, development_testing (BC-10 F08): the S6 repair's last-resort
    recovery must also cover the must-carry units, and only on the revised_output shape a
    targeted_repair reply uses. With nothing to carry the recovery is returned unchanged, so no
    other section's repair behaves differently."""
    must_carry = frozenset({"inherited_unit:092.paragraph"})

    def no_title_fix(output: dict[str, Any]) -> dict[str, Any] | None:
        return None

    assert _with_carried_units(no_title_fix, frozenset()) is no_title_fix
    recover = _with_carried_units(no_title_fix, must_carry)
    reply: dict[str, Any] = {
        "revised_output": {
            "units": [{"section": "development_testing", "slot": "summary", "text": "x"}],
            "omitted": [],
        }
    }
    recovered = recover(reply)
    assert recovered is reply
    assert [item["fact_id"] for item in reply["revised_output"]["omitted"]] == [
        "inherited_unit:092.paragraph"
    ]
    # Mutation control: a reply already carrying the unit is left alone.
    settled: dict[str, Any] = {
        "revised_output": {
            "units": [
                {
                    "section": "development_testing",
                    "slot": "summary",
                    "text": "x",
                    "fact_ids": ["inherited_unit:092.paragraph"],
                }
            ],
            "omitted": [],
        }
    }
    assert recover(settled) is None


class _RecordingStore:
    def __init__(self) -> None:
        self.puts: list[tuple[str, str, Any, dict[str, Any]]] = []

    def put(self, request_sha256: str, job: str, model: Any, output: dict[str, Any]) -> None:
        self.puts.append((request_sha256, job, model, output))


class _RecordingLedger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str | None, list[dict[str, Any]]]] = []

    def record(
        self,
        defect: Defect,
        outcome: str,
        request_sha256: str | None = None,
        changes: Any = (),
    ) -> None:
        self.records.append((outcome, request_sha256, list(changes)))


def _bc07_repair_inputs(
    plan: dict[str, Any], overage: int, levers: dict[str, int]
) -> tuple[SimpleNamespace, Round, Defect, _RecordingStore, _RecordingLedger, dict[str, Any]]:
    current = replace(_minimal_round(plan), readme="line\n" * 400)
    defect = Defect(
        fingerprint="f" * 24,
        source="validation",
        label="BC-07",
        section_id=None,
        stage="S5",
        record={},
    )
    store = _RecordingStore()
    ledger = _RecordingLedger()
    tx = SimpleNamespace(
        prompts={
            "presentation_planning": SimpleNamespace(
                manifest=SimpleNamespace(output=SimpleNamespace(schema_={}, binding=None))
            ),
            "targeted_repair": object(),
        },
        facts=FactsDocument("aspose-font-foss/Aspose.Font-FOSS-for-Python", "rev", ()),
        entry=SimpleNamespace(
            repository="aspose-font-foss/Aspose.Font-FOSS-for-Python", ecosystem="python"
        ),
        store=store,
        config=None,
        ledger=None,
        context=None,
    )
    hint = {
        "visible_lines_over_budget": overage,
        "optional_plan_fields_and_their_visible_line_cost_if_cleared": levers,
    }
    return tx, current, defect, store, ledger, hint


def test_a_bc07_overage_the_levers_provably_close_is_bounded_without_a_model_call() -> None:
    """Measured shape, aspose-font-foss/Aspose.Font-FOSS-for-Python (docs/DECISION_LOG.md
    2026-09-27/28): the model's targeted repair was asked to clear a lever and never did, though
    a 127-line flagship alone clears a 5-line overage. ``repair_defect`` now clears it in code
    first: the model is not called, the cleared plan is stored under the causal call's own request
    hash (the same place a model reply would be), and the repair is recorded truthfully."""
    plan = {
        "flagship_example_id": "example:008",
        "second_quick_start_example_id": None,
        "additional_example_ids": ["example:008"],
    }
    tx, current, defect, store, ledger, hint = _bc07_repair_inputs(
        plan, 5, {"flagship_example_id": 127}
    )
    with (
        patch(
            "repository_presenter.components.readme.repair.rounds.product_name", return_value="x"
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds._stage_target",
            return_value=(current.planned, lambda revised: [], None, None, None),
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds.visible_line_budget_hint",
            return_value=hint,
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds.run_job",
            side_effect=AssertionError("the model must not be called for a provable clear"),
        ),
    ):
        repair_defect(tx, current, defect, ledger)
    assert len(store.puts) == 1
    request_sha256, job, _model, cleared = store.puts[0]
    assert request_sha256 == current.planned.request_sha256 and job == "presentation_planning"
    assert cleared["flagship_example_id"] is None
    assert cleared["additional_example_ids"] == ["example:008"]
    assert ledger.records[0][0] == "repaired"
    assert [change["path"] for change in ledger.records[0][2]] == ["flagship_example_id"]


def test_a_bc07_overage_the_levers_cannot_provably_close_still_goes_to_the_model() -> None:
    """Mutation control: an overage larger than the lever saving (even before the render margin)
    is not bounded in code. The targeted repair is called exactly as before, and nothing is
    stored by the bound."""
    plan = {
        "flagship_example_id": "example:008",
        "second_quick_start_example_id": None,
        "additional_example_ids": ["example:008"],
    }
    tx, current, defect, store, ledger, hint = _bc07_repair_inputs(
        plan, 200, {"flagship_example_id": 127}
    )
    model = Mock(side_effect=JobError("model reached"))
    with (
        patch(
            "repository_presenter.components.readme.repair.rounds.product_name", return_value="x"
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds._stage_target",
            return_value=(current.planned, lambda revised: [], None, None, None),
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds.visible_line_budget_hint",
            return_value=hint,
        ),
        patch("repository_presenter.components.readme.repair.rounds.run_job", model),
        patch(
            "repository_presenter.components.readme.repair.rounds.repair_packet", return_value={}
        ),
        patch(
            "repository_presenter.components.readme.repair.rounds.repair_schema", return_value={}
        ),
    ):
        repair_defect(tx, current, defect, ledger)
    assert model.call_count == 1
    assert store.puts == []
    assert ledger.records[0][0] == "unrepairable"
