"""The acceptance profile is internally consistent, unratified, and cites plans/idea.md."""

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


def test_it_is_unratified_and_carries_no_point_weight() -> None:
    assert acceptance.RATIFIED is False
    assert acceptance.PROFILE.ratified is False
    assert all(criterion.points is None for criterion in acceptance.CRITERIA)


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


def test_the_recorded_profile_version_is_the_frozen_value() -> None:
    assert acceptance.PROFILE_VERSION == "1"
    assert ACCEPTANCE_PROFILE_VERSION == acceptance.PROFILE_VERSION


def _with_weights(weights: list[int | None]) -> acceptance.Profile:
    criteria = tuple(
        replace(criterion, points=weight)
        for criterion, weight in zip(acceptance.CRITERIA, weights, strict=True)
    )
    return replace(acceptance.PROFILE, criteria=criteria)


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
            lambda: replace(acceptance.PROFILE, ratified=True),
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
