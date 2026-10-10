"""The scorer: disqualifiers fail a candidate whatever its points, a clean candidate scores
by its criteria, and every unjudged entry stays unjudged rather than passing."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from repository_presenter.components.readme.review.acceptance import profile as acceptance
from repository_presenter.components.readme.review.acceptance.scorer import (
    DISQUALIFIED,
    FAIL,
    INCOMPLETE,
    MET,
    NOT_APPLICABLE,
    NOT_EVALUATED,
    NOT_MET,
    NOT_TRIGGERED,
    PASS,
    TRIGGERED,
    UNEVALUATED,
    UNSCORED,
    score_candidate,
)
from repository_presenter.components.readme.review.acceptance.template_check import (
    Evidence,
    ReferenceSection,
    TemplateInputs,
)
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS

CLEAN_README = """# Aspose.Demo FOSS for Python

![Py](https://img.shields.io/badge/py-3) [![MIT](https://img.shields.io/badge/MIT)](LICENSE)

Aspose.Demo FOSS for Python reads and writes demo files in Python applications.
It solves the problem of producing demo files without a commercial runtime, and it
serves data engineers who build reporting pipelines.

## Navigation

- [Installation](#installation)
- [Scope and Limitations](#scope-and-limitations)

## Key Capabilities

- **Write demo files**: builds a demo document from `Document` objects.

## Installation

```bash
pip install aspose-demo
```

## Scope and Limitations

- Unsupported formats raise `NotImplementedError`.

The full-featured version is available as [Aspose.Demo for Python — Enterprise Edition](https://products.aspose.com/demo/python).

## License

This project is licensed under the [MIT](LICENSE) license, which permits use and
distribution with the notice retained.
"""

# A synthetic weighting for tests that pin the scorer's arithmetic apart from the ratified table:
# the first four criteria carry two points, the rest one, so the weights sum to the stated 30. The
# production weighting is asserted in test_profile.py.
_WEIGHTS = [2 if index < 4 else 1 for index in range(len(acceptance.CRITERIA))]
WEIGHT = {
    criterion.id: weight for criterion, weight in zip(acceptance.CRITERIA, _WEIGHTS, strict=True)
}
assert sum(_WEIGHTS) == 30


def _weighted(*, with_unevaluated: bool) -> acceptance.Profile:
    criteria = tuple(
        replace(criterion, points=weight)
        for criterion, weight in zip(acceptance.CRITERIA, _WEIGHTS, strict=True)
    )
    disqualifiers = (
        acceptance.DISQUALIFIERS
        if with_unevaluated
        else tuple(d for d in acceptance.DISQUALIFIERS if d.id != "D14")
    )
    return replace(
        acceptance.PROFILE, criteria=criteria, disqualifiers=disqualifiers, ratified=True
    )


WEIGHTED_FULL = _weighted(with_unevaluated=True)
WEIGHTED_JUDGEABLE = _weighted(with_unevaluated=False)


def _validation(**overrides: str) -> dict[str, Any]:
    checks = [{"id": check.id, "verdict": "PASS"} for check in BLOCKING_CHECKS]
    for check in checks:
        if check["id"] in overrides:
            check["verdict"] = overrides[check["id"]]
    return {"checks": checks}


def _review(**overrides: Any) -> dict[str, Any]:
    review: dict[str, Any] = {"verdict": "ACCEPT", "findings": [], "advisory": []}
    review.update(overrides)
    return review


def _row(record: dict[str, Any], entry_id: str) -> dict[str, Any]:
    rows = [*record["criteria"], *record["disqualifiers"]]
    return next(row for row in rows if row["id"] == entry_id)


def _score(
    readme: str = CLEAN_README,
    validation: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    profile: acceptance.Profile = WEIGHTED_JUDGEABLE,
) -> dict[str, Any]:
    return score_candidate(
        readme,
        validation if validation is not None else _validation(),
        review if review is not None else _review(),
        profile,
    )


def test_a_clean_candidate_passes_by_its_criteria_when_weights_are_ratified() -> None:
    record = _score()
    assert record["outcome"] == PASS
    assert record["points_possible"] == 30
    assert record["points_earned"] == 30
    assert record["triggered_disqualifiers"] == []


def test_a_failing_criterion_costs_exactly_its_weight_and_triggers_no_disqualifier() -> None:
    # BC-07 owns C03, C08, and C09 and no disqualifier reads BC-07.
    record = _score(validation=_validation(**{"BC-07": "FAIL"}))
    expected = 30 - WEIGHT["C03"] - WEIGHT["C08"] - WEIGHT["C09"]
    assert record["points_earned"] == expected
    assert record["triggered_disqualifiers"] == []
    assert record["outcome"] == FAIL
    for entry_id in ("C03", "C08", "C09"):
        assert _row(record, entry_id)["status"] == NOT_MET


def test_a_not_applicable_criterion_is_credited_and_says_so() -> None:
    record = _score()
    third_party = _row(record, "C07")
    assert third_party["status"] == NOT_APPLICABLE
    assert record["applicability_ratified"] is True
    assert record["points_earned"] == 30


def _with_h1(readme: str) -> str:
    return readme + "\n# A Second Title\n"


def _with_narration(readme: str) -> str:
    return readme + "\nThe source revision is pinned for every build.\n"


def _with_label(readme: str) -> str:
    return readme + "\n### Preserved repository details\n"


def _with_edition(readme: str) -> str:
    return readme + "\nA commercial edition is also available.\n"


def _with_other_platforms(readme: str) -> str:
    return readme + "\n## Other platforms\n\nSee more.\n"


def _with_split_badges(readme: str) -> str:
    return readme.replace(
        "\n\n## Navigation",
        "\n\n![Extra](https://img.shields.io/badge/x-1.svg)\n\n## Navigation",
        1,
    )


DISQUALIFIER_CASES: list[tuple[str, Callable[[str], str], dict[str, str]]] = [
    ("D01", _with_narration, {}),
    ("D02", _with_label, {}),
    ("D03", _with_edition, {}),
    ("D04", _with_other_platforms, {}),
    ("D05", _with_h1, {}),
    ("D06", _with_split_badges, {}),
    ("D07", lambda r: r, {"BC-04": "FAIL"}),
    ("D08", lambda r: r, {"BC-05": "FAIL"}),
    ("D09", lambda r: r, {"BC-03": "FAIL"}),
    ("D09", lambda r: r, {"BC-02": "FAIL"}),
    ("D10", lambda r: r, {"BC-08": "FAIL"}),
    ("D11", lambda r: r, {"BC-06": "FAIL"}),
    ("D12", lambda r: r, {"BC-10": "FAIL"}),
    ("D13", lambda r: r, {"BC-09": "FAIL"}),
]


@pytest.mark.parametrize(("entry_id", "edit", "checks"), DISQUALIFIER_CASES)
def test_each_hard_disqualifier_fails_the_candidate(
    entry_id: str, edit: Callable[[str], str], checks: dict[str, str]
) -> None:
    record = _score(readme=edit(CLEAN_README), validation=_validation(**checks))
    assert entry_id in record["triggered_disqualifiers"]
    assert record["outcome"] == DISQUALIFIED


def test_a_disqualifier_fails_the_candidate_even_at_full_points() -> None:
    # A second H1 reads no criterion, so the candidate still earns every point.
    record = _score(readme=_with_h1(CLEAN_README))
    assert record["points_earned"] == 30
    assert record["points_possible"] == 30
    assert "D05" in record["triggered_disqualifiers"]
    assert record["outcome"] == DISQUALIFIED


def test_a_disqualifier_is_unrelated_to_the_points_it_would_otherwise_score() -> None:
    record = _score(readme=_with_label(CLEAN_README), profile=WEIGHTED_JUDGEABLE)
    assert record["outcome"] == DISQUALIFIED


def _unratified() -> acceptance.Profile:
    return replace(
        acceptance.PROFILE,
        criteria=tuple(replace(c, points=None) for c in acceptance.CRITERIA),
        ratified=False,
    )


def test_an_unratified_profile_claims_no_point_total() -> None:
    record = _score(profile=_unratified())
    assert record["ratified"] is False
    assert record["applicability_ratified"] is False
    assert record["points_possible"] is None
    assert record["points_earned"] is None
    assert record["outcome"] == UNSCORED
    assert _row(record, "C01")["status"] == MET
    assert _row(record, "D14")["status"] == UNEVALUATED


# --- the ratified production profile ---------------------------------------------------------

DEMO = Evidence("Aspose.Demo FOSS for Python", "1.0", frozenset({"aspose-demo", "Document"}))
UNRELATED = ReferenceSection(
    "Key Capabilities",
    "A different product that converts spreadsheets between several formats for analysts.",
    "Other Tool",
    "9.9",
)
TEMPLATED_BODY = (
    "{name} reads and writes documents with the standard settings that every product of this "
    "kind uses, and it follows the usual conventions for your platform."
)


def _template(*corpus: ReferenceSection, evidence: Evidence = DEMO) -> TemplateInputs:
    return TemplateInputs(evidence, corpus)


def _production(
    readme: str = CLEAN_README,
    *,
    template: TemplateInputs | None,
    validation: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return score_candidate(
        readme,
        validation if validation is not None else _validation(),
        review if review is not None else _review(),
        acceptance.PROFILE,
        template,
    )


def test_the_production_profile_scores_the_full_thirty_with_d14_judged() -> None:
    record = _production(template=_template(UNRELATED))
    assert record["ratified"] is True
    assert record["points_possible"] == 30
    assert record["points_earned"] == 30
    assert record["triggered_disqualifiers"] == []
    assert record["unevaluated"] == {"criteria": [], "disqualifiers": []}
    assert _row(record, "D14")["status"] == NOT_TRIGGERED
    assert record["outcome"] == PASS


def test_without_template_inputs_d14_is_unevaluated_and_the_outcome_cannot_pass() -> None:
    record = _production(template=None)
    assert _row(record, "D14")["status"] == UNEVALUATED
    assert record["unevaluated"]["disqualifiers"] == ["D14"]
    assert record["points_earned"] == 30
    assert record["outcome"] == INCOMPLETE


def test_an_empty_reference_corpus_leaves_d14_unevaluated_not_passed() -> None:
    record = _production(template=_template())
    assert _row(record, "D14")["status"] == UNEVALUATED
    assert record["outcome"] == INCOMPLETE


def test_the_d14_checker_is_consulted_and_a_templated_section_disqualifies() -> None:
    section = TEMPLATED_BODY.format(name="Aspose.Demo FOSS for Python")
    bullet = "- **Write demo files**: builds a demo document from `Document` objects."
    assert bullet in CLEAN_README
    readme = CLEAN_README.replace(bullet, section)
    reference = ReferenceSection(
        "Key Capabilities", TEMPLATED_BODY.format(name="Other Tool"), "Other Tool", "9.9"
    )
    record = _production(readme, template=_template(reference))
    assert "D14" in record["triggered_disqualifiers"]
    assert _row(record, "D14")["status"] == TRIGGERED
    assert "Key Capabilities" in " ".join(_row(record, "D14")["evidence"])
    assert record["outcome"] == DISQUALIFIED


def test_a_candidate_below_the_full_score_does_not_pass_even_with_nothing_disqualifying() -> None:
    # BC-07 owns C03, C08 and C09, one point each.
    record = _production(template=_template(UNRELATED), validation=_validation(**{"BC-07": "FAIL"}))
    assert record["points_earned"] == 27
    assert record["triggered_disqualifiers"] == []
    assert record["outcome"] == FAIL


def test_a_banner_link_to_an_aspose_destination_above_the_opening_fails_c01_for_two_points() -> (
    None
):
    banner = "[![Aspose.Demo](https://products.aspose.org/media/demo/banner.png)](https://products.aspose.org/demo/python/)\n\n"
    readme = CLEAN_README.replace(
        "Aspose.Demo FOSS for Python reads", banner + "Aspose.Demo FOSS for Python reads", 1
    )
    record = _production(readme, template=_template(UNRELATED))
    assert _row(record, "C01")["status"] == NOT_MET
    assert record["points_earned"] == 28
    assert record["outcome"] == FAIL


def test_not_applicable_criteria_are_credited_as_met_at_the_ratified_weights() -> None:
    record = _production(template=_template(UNRELATED))
    credited = {row["id"] for row in record["criteria"] if row["status"] == NOT_APPLICABLE}
    assert {"C07", "C12"} <= credited  # no notices file, no additional examples
    assert record["points_earned"] == record["points_possible"] == 30


def test_a_readme_with_no_h1_credits_c01_as_not_applicable_but_still_fails_d05() -> None:
    record = _production("Just prose with no heading at all.\n", template=_template(UNRELATED))
    assert _row(record, "C01")["status"] == NOT_APPLICABLE
    assert "D05" in record["triggered_disqualifiers"]
    assert record["outcome"] == DISQUALIFIED


def test_an_unevaluated_disqualifier_is_incomplete_never_a_pass() -> None:
    record = _score(profile=WEIGHTED_FULL)
    assert record["outcome"] == INCOMPLETE
    assert record["unevaluated"]["disqualifiers"] == ["D14"]


def test_a_pending_check_is_unevaluated_not_passed() -> None:
    record = _score(validation=_validation(**{"BC-04": "PENDING"}))
    assert _row(record, "C21")["status"] == NOT_EVALUATED
    assert _row(record, "D07")["status"] == UNEVALUATED
    assert "D07" not in record["triggered_disqualifiers"]
    assert record["outcome"] == INCOMPLETE


def test_a_check_missing_from_validation_is_unevaluated_not_passed() -> None:
    record = score_candidate(CLEAN_README, {"checks": []}, _review(), WEIGHTED_JUDGEABLE)
    assert _row(record, "C24")["status"] == NOT_EVALUATED
    assert record["outcome"] == INCOMPLETE


def test_a_blocking_reviewer_finding_on_a_criterion_section_fails_that_criterion() -> None:
    finding = {
        "id": "F1",
        "section_id": "key_capabilities",
        "criterion": "presentation",
        "causal_stage": "S6",
        "causal_state": "REPAIRABLE",
    }
    record = _score(review=_review(verdict="REJECT_PRESENTATION", findings=[finding]))
    row = _row(record, "C10")
    assert row["status"] == NOT_MET
    assert "blocking" in row["evidence"][0]


def test_an_advisory_reviewer_finding_on_a_criterion_section_also_counts() -> None:
    advisory = {
        "id": "F2",
        "section_id": "key_capabilities",
        "criterion": "presentation",
        "causal_stage": "S6",
    }
    record = _score(review=_review(advisory=[advisory]))
    assert _row(record, "C10")["status"] == NOT_MET


def test_a_finding_the_reviewer_flags_as_its_own_defect_does_not_count() -> None:
    own_defect = {
        "id": "F3",
        "section_id": "key_capabilities",
        "criterion": "presentation",
        "causal_stage": "S6",
        "reviewer_scope_defect": "quotes the reviewer's label",
    }
    record = _score(review=_review(advisory=[own_defect]))
    assert _row(record, "C10")["status"] == MET


def test_a_rejection_on_other_sections_leaves_an_unrelated_review_criterion_unevaluated() -> None:
    finding = {
        "id": "F4",
        "section_id": "installation",
        "criterion": "factuality",
        "causal_stage": "S6",
    }
    record = _score(review=_review(verdict="REJECT_FACTUAL", findings=[finding]))
    assert _row(record, "C14")["status"] == NOT_EVALUATED
    assert _row(record, "C14")["evidence"] == [
        "reviewer verdict REJECT_FACTUAL; no finding names these sections"
    ]


def test_the_record_is_deterministic() -> None:
    first = _score(readme=_with_h1(CLEAN_README))
    second = _score(readme=_with_h1(CLEAN_README))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_the_record_declares_it_ratified_and_not_a_ready_gate() -> None:
    record = _score(profile=acceptance.PROFILE)
    assert record["advisory"] is True  # never gates READY_FOR_PROPOSAL
    assert record["ratified"] is True
    assert record["applicability_ratified"] is True
    assert record["profile_version"] == acceptance.PROFILE_VERSION == "2"
    assert record["scorer_version"] == "2"
    assert record["source"] == "plans/idea.md"


def test_scoring_does_not_mutate_its_inputs() -> None:
    validation = _validation()
    review = _review()
    before = (copy.deepcopy(validation), copy.deepcopy(review))
    score_candidate(CLEAN_README, validation, review, WEIGHTED_JUDGEABLE)
    assert (validation, review) == before


def _bare_license(readme: str) -> str:
    return readme.split("## License")[0] + "## License\n\n[MIT](LICENSE)\n"


def _collapse_installation(readme: str) -> str:
    opened = readme.replace("## Installation", "<details>\n\n## Installation", 1)
    return opened.replace("## Scope and Limitations", "</details>\n\n## Scope and Limitations", 1)


def _unlabelled_fence(readme: str) -> str:
    return readme + "\n```\nx = 1\n```\n"


def _numbered_example(readme: str) -> str:
    return readme + "\n## Additional Examples\n\n### Example 2\n\nRuns.\n"


@pytest.mark.parametrize(
    ("entry_id", "edit"),
    [
        ("C06", _bare_license),
        ("C11", _collapse_installation),
        ("C12", _numbered_example),
        ("C13", _unlabelled_fence),
    ],
)
def test_a_failing_text_criterion_costs_its_weight_and_no_disqualifier_fires(
    entry_id: str, edit: Callable[[str], str]
) -> None:
    # None of these criteria shares a predicate with a disqualifier, so the criterion alone decides.
    record = _score(readme=edit(CLEAN_README))
    assert _row(record, entry_id)["status"] == NOT_MET
    assert record["triggered_disqualifiers"] == []
    assert record["points_earned"] == 30 - WEIGHT[entry_id]
    assert record["outcome"] == FAIL
