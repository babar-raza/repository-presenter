"""The build receipt and how its findings reach the facts the typed gate re-derives from."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction.chain import (
    CHAIN_ATTRIBUTE,
    CI_CONTIGUOUS_ATTRIBUTE,
    CI_JOB,
    EXCLUDED_ATTRIBUTE,
    PROJECT_FILES,
    RECEIPT_ATTRIBUTE,
    RECEIPT_FAILURE_ATTRIBUTE,
    RECEIPT_PLATFORM_ATTRIBUTE,
    ChainPlan,
    Exclusion,
    Step,
)
from repository_presenter.components.readme_correction.receipts import (
    EXECUTED,
    FAILED,
    NOT_VERIFIED,
    Receipt,
    StepResult,
    apply_plan,
    load_receipt,
    receipt_path,
    store_receipt,
)
from repository_presenter.core.facts import Fact, FactsDocument

REPOSITORY = "o/r"
REVISION = "b" * 40


def plan_of(kind: str = CI_JOB, *, excluded: tuple[Exclusion, ...] = ()) -> ChainPlan:
    return ChainPlan(
        kind,
        ".github/workflows/ci.yml job test",
        (
            Step("setup", "npm install"),
            Step("build", "npm run build", "build_test_asset:build-command"),
            Step("test", "npm test", "build_test_asset:test-command"),
        ),
        excluded,
    )


def receipt_for(
    plan: ChainPlan,
    outcome: str = EXECUTED,
    *,
    seconds: float = 1.5,
    tail: str = "ok",
    detail: str = "every step exited 0",
) -> Receipt:
    steps = tuple(
        StepResult(s.command, outcome, 0 if outcome == EXECUTED else 1, seconds, tail)
        for s in plan.steps
    )
    return Receipt(
        REPOSITORY,
        REVISION,
        plan.digest(),
        outcome,
        detail,
        steps,
        {"node": "v20.1.0"},
        "Linux (docker container)",
    )


def facts(make_fact: Any) -> FactsDocument:
    return FactsDocument(
        REPOSITORY,
        REVISION,
        (
            make_fact(
                "build_test_asset:build-command",
                "npm run build",
                evidence=((".github/workflows/ci.yml", "job test runs `npm run build`"),),
                attributes={"role": "build command", "source": "ci workflow"},
            ),
            make_fact(
                "build_test_asset:test-command",
                "npm test",
                evidence=((".github/workflows/ci.yml", "job test runs `npm test`"),),
                attributes={"role": "test command", "source": "ci workflow", "precondition": "x"},
            ),
            make_fact("license:spdx", "MIT", evidence=(("LICENSE", None),)),
        ),
    )


def by_id(document: FactsDocument) -> dict[str, Fact]:
    return {fact.id: fact for fact in document.facts}


def test_the_digest_covers_what_a_rerun_must_reproduce_not_how_long_it_took() -> None:
    plan = plan_of()
    first = receipt_for(plan, seconds=1.0, tail="a")
    again = receipt_for(plan, seconds=99.0, tail="b")
    assert first.stable_digest() == again.stable_digest()
    other = receipt_for(plan_of(PROJECT_FILES))
    assert other.stable_digest() != first.stable_digest()  # another chain is another receipt
    moved = Receipt(**{**first.__dict__, "revision": "c" * 40})
    assert moved.stable_digest() != first.stable_digest()
    failed = receipt_for(plan, FAILED, detail="`npm test` exited 1")
    assert failed.stable_digest() != first.stable_digest()


def test_a_stored_receipt_is_reused_only_for_its_revision_and_its_chain(tmp_path: Path) -> None:
    plan = plan_of()
    path = receipt_path(tmp_path, REPOSITORY, REVISION, plan)
    store_receipt(path, receipt_for(plan))
    loaded = load_receipt(path, REPOSITORY, REVISION, plan)
    assert (
        loaded is not None
        and loaded.outcome == EXECUTED
        and loaded.steps[0].command == "npm install"
    )
    assert load_receipt(path, REPOSITORY, "c" * 40, plan) is None
    assert load_receipt(path, REPOSITORY, REVISION, plan_of(PROJECT_FILES)) is None
    assert load_receipt(tmp_path / "missing.json", REPOSITORY, REVISION, plan) is None
    path.write_text("not json", encoding="utf-8")
    assert load_receipt(path, REPOSITORY, REVISION, plan) is None


def test_a_passing_receipt_puts_the_two_attributes_the_detector_reads_on_the_command_facts(
    make_fact: Any,
) -> None:
    plan = plan_of()
    updated = by_id(apply_plan(facts(make_fact), plan, receipt_for(plan)))
    for fact_id in ("build_test_asset:build-command", "build_test_asset:test-command"):
        attributes = updated[fact_id].attributes or {}
        assert attributes[CHAIN_ATTRIBUTE] == CI_JOB
        assert attributes[CI_CONTIGUOUS_ATTRIBUTE] == "true"
        assert len(attributes[RECEIPT_ATTRIBUTE]) == 64
        assert attributes[RECEIPT_PLATFORM_ATTRIBUTE] == "Linux (docker container)"
        assert attributes["precondition"] == "npm install"  # the setup the chain ran first
        assert "every step exited 0" in (updated[fact_id].evidence[-1].detail or "")
        assert updated[fact_id].evidence[-1].path == ".github/workflows/ci.yml"
        assert updated[fact_id].polarity == "SUPPORTED"
    assert (
        by_id(apply_plan(facts(make_fact), plan, receipt_for(plan)))["license:spdx"].attributes
        is None
    )


def test_a_project_file_chain_is_not_called_ci_contiguous(make_fact: Any) -> None:
    plan = plan_of(PROJECT_FILES)
    updated = by_id(apply_plan(facts(make_fact), plan, receipt_for(plan)))
    attributes = updated["build_test_asset:test-command"].attributes or {}
    assert (
        attributes[CHAIN_ATTRIBUTE] == PROJECT_FILES and CI_CONTIGUOUS_ATTRIBUTE not in attributes
    )


def test_a_receipt_that_did_not_pass_leaves_its_reason_and_no_receipt(make_fact: Any) -> None:
    plan = plan_of()
    failed = receipt_for(plan, FAILED, detail="`npm test` exited 1: boom")
    attributes = (
        by_id(apply_plan(facts(make_fact), plan, failed))[
            "build_test_asset:test-command"
        ].attributes
        or {}
    )
    assert RECEIPT_ATTRIBUTE not in attributes
    assert attributes[RECEIPT_FAILURE_ATTRIBUTE] == "FAILED: `npm test` exited 1: boom"
    unverified = receipt_for(plan, NOT_VERIFIED, detail="make is not available")
    text = (
        by_id(apply_plan(facts(make_fact), plan, unverified))[
            "build_test_asset:test-command"
        ].attributes
        or {}
    )[RECEIPT_FAILURE_ATTRIBUTE]
    assert text.startswith("NOT_VERIFIED: ")
    none = by_id(apply_plan(facts(make_fact), plan, None))["build_test_asset:test-command"]
    assert (none.attributes or {})[RECEIPT_FAILURE_ATTRIBUTE].startswith("NOT_RUN: ")


def test_a_command_the_chain_leaves_out_carries_the_reason(make_fact: Any) -> None:
    plan = ChainPlan(
        CI_JOB,
        "w job test",
        (Step("test", "npm test", "build_test_asset:test-command"),),
        (Exclusion("build_test_asset:build-command", "it is not a step of the CI job"),),
    )
    updated = by_id(apply_plan(facts(make_fact), plan, receipt_for(plan)))
    left_out = updated["build_test_asset:build-command"].attributes or {}
    assert left_out[EXCLUDED_ATTRIBUTE] == "it is not a step of the CI job"
    assert RECEIPT_ATTRIBUTE not in left_out and CHAIN_ATTRIBUTE not in left_out
