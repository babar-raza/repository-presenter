"""The acceptance profile is internally consistent, ratified with the owner's 2026-10-10 weights
(G7-W20, OWNER-13), and cites plans/idea.md."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

import pytest

from repository_presenter.components.readme.bundle.seal import ACCEPTANCE_PROFILE_VERSION
from repository_presenter.components.readme.review.acceptance import profile as acceptance
from repository_presenter.components.readme.review.acceptance.scorer import (
    ProfileError,
    validate_profile,
)
from support import REPO_ROOT

IDEA = REPO_ROOT / "plans" / "idea.md"
_REF = re.compile(r"^L(\d+)(?:-(\d+))?$")


def _idea_line_count() -> int:
    return len(IDEA.read_text(encoding="utf-8").splitlines())


def test_the_production_profile_is_internally_valid() -> None:
    validate_profile(acceptance.PROFILE)


# docs/DECISION_LOG.md, 2026-10-10: four criteria carry two points, the other twenty-two one.
RATIFIED_WEIGHTS = {"C01": 2, "C02": 2, "C21": 2, "C24": 2}


def test_it_is_ratified_with_the_owners_weights() -> None:
    assert acceptance.RATIFIED is True
    assert acceptance.PROFILE.ratified is True
    assert len(acceptance.CRITERIA) == 26
    for criterion in acceptance.CRITERIA:
        assert criterion.points == RATIFIED_WEIGHTS.get(criterion.id, 1), criterion.id


def test_the_ratified_points_sum_to_the_stated_thirty() -> None:
    assert sum(criterion.points or 0 for criterion in acceptance.CRITERIA) == 30
    assert acceptance.TOTAL_POINTS == 30


def test_d14_is_judged_by_the_template_checker_not_left_unevaluated() -> None:
    d14 = next(d for d in acceptance.DISQUALIFIERS if d.id == "D14")
    assert d14.evaluator.kind == "template"
    assert all(d.evaluator.kind != "unevaluated" for d in acceptance.DISQUALIFIERS)


@pytest.mark.parametrize(
    "points",
    [
        [None, *([1] * 25)],  # a missing weight
        [*([1] * 25), 3],  # sums to 28
        [*([1] * 25), 6],  # sums to 31
        [-1, *([1] * 24), 7],  # a negative weight that still totals 30
    ],
)
def test_a_ratified_profile_with_missing_or_wrong_points_fails_loudly(
    points: list[int | None],
) -> None:
    criteria = tuple(
        replace(criterion, points=weight)
        for criterion, weight in zip(acceptance.CRITERIA, points, strict=True)
    )
    with pytest.raises(acceptance.ProfileError):
        replace(acceptance.PROFILE, criteria=criteria, ratified=True)


def test_an_unratified_profile_may_still_be_a_draft_without_points() -> None:
    draft = replace(
        acceptance.PROFILE,
        criteria=tuple(replace(c, points=None) for c in acceptance.CRITERIA),
        ratified=False,
    )
    validate_profile(draft)


def test_the_total_is_the_thirty_points_the_source_states() -> None:
    assert acceptance.TOTAL_POINTS == 30
    assert acceptance.PROFILE.total_points == 30


def test_every_source_reference_points_at_real_idea_md_lines() -> None:
    limit = _idea_line_count()
    entries = [*acceptance.CRITERIA, *acceptance.DISQUALIFIERS]
    assert entries, "the profile must not be empty"
    for entry in entries:
        assert entry.source, f"{entry.id} cites no source"
        for ref in entry.source:
            match = _REF.match(ref)
            assert match, f"{entry.id}: malformed reference {ref!r}"
            first = int(match.group(1))
            last = int(match.group(2) or first)
            assert 1 <= first <= last <= limit, f"{entry.id}: {ref} is outside idea.md"


def test_identifiers_are_unique_across_criteria_and_disqualifiers() -> None:
    ids = [entry.id for entry in (*acceptance.CRITERIA, *acceptance.DISQUALIFIERS)]
    assert len(ids) == len(set(ids))


def test_the_profile_version_moved_at_ratification() -> None:
    assert acceptance.PROFILE_VERSION == "2"


def test_ratification_did_not_move_the_version_a_sealed_review_consumed() -> None:
    """dependencies.json records the profile a bundle's review consumed. Ratification changes only
    the funnel's live score, so moving this value would mark every sealed candidate stale
    (REVIEWING re-entry) and drop the current ones from the headline count for no change in
    content (G7-W20). Move it only with a change to what the independent review reads or decides."""
    assert ACCEPTANCE_PROFILE_VERSION == "1"
    assert ACCEPTANCE_PROFILE_VERSION != acceptance.PROFILE_VERSION


def _with_weights(weights: list[int | None]) -> acceptance.Profile:
    criteria = tuple(
        replace(criterion, points=weight)
        for criterion, weight in zip(acceptance.CRITERIA, weights, strict=True)
    )
    return replace(acceptance.PROFILE, criteria=criteria, ratified=False)


def _weights(total: int) -> list[int | None]:
    """A weighting that sums to ``total`` - a test fixture, never a ratified weighting."""
    count = len(acceptance.CRITERIA)
    weights: list[int | None] = [1] * count
    weights[0] = total - (count - 1)
    return weights


@pytest.mark.parametrize(
    ("label", "build"),
    [
        ("sum below the stated total", lambda: _with_weights(_weights(29))),
        (
            "partial weights",
            lambda: _with_weights([1, None, *([1] * (len(acceptance.CRITERIA) - 2))]),
        ),
        (
            "ratified without every weight",
            lambda: replace(
                acceptance.PROFILE,
                criteria=tuple(replace(c, points=None) for c in acceptance.CRITERIA),
            ),
        ),
        (
            "template evaluator carrying a reference",
            lambda: replace(
                acceptance.PROFILE,
                disqualifiers=(
                    *acceptance.DISQUALIFIERS[:-1],
                    replace(
                        acceptance.DISQUALIFIERS[-1],
                        evaluator=acceptance.Evaluator("template", ("x",)),
                    ),
                ),
            ),
        ),
        ("total not 30", lambda: replace(acceptance.PROFILE, total_points=29)),
        (
            "duplicate id",
            lambda: replace(
                acceptance.PROFILE,
                criteria=(acceptance.CRITERIA[0], acceptance.CRITERIA[0], *acceptance.CRITERIA[2:]),
            ),
        ),
        (
            "unknown blocking check",
            lambda: replace(
                acceptance.PROFILE,
                criteria=(
                    replace(
                        acceptance.CRITERIA[0], evaluator=acceptance.Evaluator("check", ("BC-99",))
                    ),
                    *acceptance.CRITERIA[1:],
                ),
            ),
        ),
        (
            "unknown text predicate",
            lambda: replace(
                acceptance.PROFILE,
                disqualifiers=(
                    replace(
                        acceptance.DISQUALIFIERS[0],
                        evaluator=acceptance.Evaluator("text", ("no_such",)),
                    ),
                    *acceptance.DISQUALIFIERS[1:],
                ),
            ),
        ),
        (
            "review evaluator carrying a reference",
            lambda: replace(
                acceptance.PROFILE,
                criteria=(
                    replace(
                        acceptance.CRITERIA[1], evaluator=acceptance.Evaluator("review", ("BC-07",))
                    ),
                    *(c for c in acceptance.CRITERIA if c is not acceptance.CRITERIA[1]),
                ),
            ),
        ),
        (
            "unknown section",
            lambda: replace(
                acceptance.PROFILE,
                criteria=(
                    replace(acceptance.CRITERIA[1], sections=("no_such_section",)),
                    *acceptance.CRITERIA[2:],
                ),
            ),
        ),
        (
            "malformed source reference",
            lambda: replace(
                acceptance.PROFILE,
                criteria=(
                    replace(acceptance.CRITERIA[0], source=("line 37",)),
                    *acceptance.CRITERIA[1:],
                ),
            ),
        ),
    ],
)
def test_an_inconsistent_profile_fails_closed(
    label: str, build: Callable[[], acceptance.Profile]
) -> None:
    with pytest.raises(ProfileError):
        validate_profile(build())
