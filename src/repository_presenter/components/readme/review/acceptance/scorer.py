"""The acceptance scorer: a candidate against the ratified 30-point acceptance profile.

``score_candidate`` reads the README text, ``validation.json``'s checks, and ``review.json``. It
never changes a blocking check, a verdict, or a state, so it cannot move a candidate to or from
``READY_FOR_PROPOSAL``; the score gates publication eligibility only (``bundle/portfolio.py``
computes it from the sealed bundle, not from a stored record). The repair round also writes the
record into ``review.json`` under ``acceptance_profile``. It has no portfolio corpus, so its D14 is
unevaluated and its outcome ``INCOMPLETE``; the portfolio funnel supplies ``template`` inputs.

Outcome, in precedence order:

- ``DISQUALIFIED``: a hard disqualifier is triggered. The points do not matter.
- ``UNSCORED``: the profile is not ratified, so no point total is claimed. The criterion and
  disqualifier evidence is still recorded.
- ``INCOMPLETE``: a criterion or disqualifier could not be judged. Nothing unevaluated passes.
- ``PASS``: every criterion is met or not applicable, and the points total the stated 30.
- ``FAIL``: otherwise.

A criterion whose condition does not apply (for example, a third-party notices heading absent)
is ``NOT_APPLICABLE`` and is credited as satisfied, so a candidate with nothing to fail can still
reach the full 30. The owner ratified that policy with the weights (2026-10-10); the record states
it with ``applicability_ratified``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from repository_presenter.components.readme.composition.components.shell import section_ids
from repository_presenter.components.readme.review.acceptance.profile import (
    PROFILE,
    SOURCE_DOCUMENT,
    TOTAL_POINTS,
    Criterion,
    Disqualifier,
    Evaluator,
    Profile,
    ProfileError,
)
from repository_presenter.components.readme.review.acceptance.template_check import (
    TemplateInputs,
    Verdict,
    check_template_filling,
)
from repository_presenter.components.readme.review.acceptance.text_checks import (
    TEXT_PREDICATES,
    Line,
    Outcome,
    scan,
)
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS

__all__ = ["ProfileError", "score_candidate", "validate_profile"]

SCORER_VERSION = "2"
SCHEMA_VERSION = 1

MET = "MET"
NOT_MET = "NOT_MET"
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_EVALUATED = "NOT_EVALUATED"
TRIGGERED = "TRIGGERED"
NOT_TRIGGERED = "NOT_TRIGGERED"
UNEVALUATED = "UNEVALUATED"

DISQUALIFIED = "DISQUALIFIED"
UNSCORED = "UNSCORED"
INCOMPLETE = "INCOMPLETE"
PASS = "PASS"
FAIL = "FAIL"

_SOURCE_REF = re.compile(r"^L\d+(?:-\d+)?$")
_STRUCTURAL_SECTIONS = frozenset({"structure", "document", "all"})


def validate_profile(profile: Profile) -> None:
    """Fail closed on an inconsistent profile: duplicate IDs, unresolvable evaluators, malformed
    source references, or point weights that do not state the total."""
    errors: list[str] = []
    entries: list[Criterion | Disqualifier] = [*profile.criteria, *profile.disqualifiers]
    ids = [entry.id for entry in entries]
    duplicates = sorted({entry_id for entry_id in ids if ids.count(entry_id) > 1})
    if duplicates:
        errors.append(f"duplicate ids {duplicates}")
    if profile.total_points != TOTAL_POINTS:
        errors.append(f"total_points must be {TOTAL_POINTS} (plans/idea.md L177, L318)")
    weights = [criterion.points for criterion in profile.criteria]
    set_weights = [w for w in weights if w is not None]
    if set_weights:
        if len(set_weights) != len(weights):
            errors.append("point weights are partial: set every criterion or none")
        elif any(w < 0 for w in set_weights):
            errors.append("point weights must not be negative")
        elif sum(set_weights) != profile.total_points:
            errors.append(f"point weights sum to {sum(set_weights)}, not {profile.total_points}")
    if profile.ratified and len(set_weights) != len(weights):
        errors.append("a ratified profile must carry every point weight")
    check_ids = {check.id for check in BLOCKING_CHECKS}
    known_sections = set(section_ids()) | _STRUCTURAL_SECTIONS
    for entry in entries:
        if not entry.source or not all(_SOURCE_REF.match(ref) for ref in entry.source):
            errors.append(f"{entry.id}: source references must look like L37-43")
        errors.extend(_evaluator_errors(entry.id, entry.evaluator, check_ids))
    for criterion in profile.criteria:
        if criterion.evaluator.kind == "review" and not criterion.sections:
            errors.append(f"{criterion.id}: a review criterion must name its sections")
        unknown = [s for s in criterion.sections if s not in known_sections]
        if unknown:
            errors.append(f"{criterion.id}: unknown sections {unknown}")
    if errors:
        raise ProfileError("; ".join(errors))


def _evaluator_errors(entry_id: str, evaluator: Evaluator, check_ids: set[str]) -> list[str]:
    if evaluator.kind == "check":
        unknown = [ref for ref in evaluator.ref if ref not in check_ids]
        if not evaluator.ref or unknown:
            return [f"{entry_id}: check evaluator names unknown or no checks {unknown}"]
    elif evaluator.kind == "text":
        if len(evaluator.ref) != 1 or evaluator.ref[0] not in TEXT_PREDICATES:
            return [f"{entry_id}: text evaluator {evaluator.ref} is not a known predicate"]
    elif evaluator.kind in ("review", "template"):
        if evaluator.ref:
            return [f"{entry_id}: a {evaluator.kind} evaluator takes no reference"]
    return []


def score_candidate(
    readme: str,
    validation: Mapping[str, Any],
    review: Mapping[str, Any],
    profile: Profile = PROFILE,
    template: TemplateInputs | None = None,
) -> dict[str, Any]:
    """The acceptance record for one candidate. Deterministic: the same inputs always produce the
    same record, so a replay reproduces it byte for byte. ``template`` carries D14's evidence and
    corpus; without it D14 is unevaluated and the outcome cannot be ``PASS``."""
    validate_profile(profile)
    lines = scan(readme)
    verdicts = {
        str(check.get("id")): check.get("verdict") for check in validation.get("checks", [])
    }
    criteria = [_criterion_row(c, lines, verdicts, review) for c in profile.criteria]
    disqualifiers = [
        _disqualifier_row(d, readme, lines, verdicts, template) for d in profile.disqualifiers
    ]
    possible, earned = _points(profile, criteria)
    triggered = [row["id"] for row in disqualifiers if row["status"] == TRIGGERED]
    unevaluated = {
        "criteria": [row["id"] for row in criteria if row["status"] == NOT_EVALUATED],
        "disqualifiers": [row["id"] for row in disqualifiers if row["status"] == UNEVALUATED],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "scorer_version": SCORER_VERSION,
        "profile_version": profile.version,
        "source": SOURCE_DOCUMENT,
        "advisory": True,  # never gates READY_FOR_PROPOSAL; the portfolio funnel reads the score
        "ratified": profile.ratified,
        "applicability_ratified": profile.ratified,
        "total_points": profile.total_points,
        "points_possible": possible,
        "points_earned": earned,
        "outcome": _outcome(profile, criteria, triggered, unevaluated, possible, earned),
        "triggered_disqualifiers": triggered,
        "unevaluated": unevaluated,
        "criteria": criteria,
        "disqualifiers": disqualifiers,
    }


def _points(
    profile: Profile, criteria: Sequence[Mapping[str, Any]]
) -> tuple[int | None, int | None]:
    weights = [criterion.points for criterion in profile.criteria]
    if any(weight is None for weight in weights):
        return None, None
    possible = sum(int(weight) for weight in weights if weight is not None)
    credited = {MET, NOT_APPLICABLE}
    earned = sum(
        int(row["points"])
        for row in criteria
        if row["status"] in credited and row["points"] is not None
    )
    return possible, earned


def _outcome(
    profile: Profile,
    criteria: Sequence[Mapping[str, Any]],
    triggered: Sequence[str],
    unevaluated: Mapping[str, Sequence[str]],
    possible: int | None,
    earned: int | None,
) -> str:
    if triggered:
        return DISQUALIFIED
    if not profile.ratified or possible is None:
        return UNSCORED
    if unevaluated["criteria"] or unevaluated["disqualifiers"]:
        return INCOMPLETE
    all_credited = all(row["status"] in (MET, NOT_APPLICABLE) for row in criteria)
    if all_credited and earned == possible == profile.total_points:
        return PASS
    return FAIL


def _criterion_row(
    criterion: Criterion,
    lines: Sequence[Line],
    verdicts: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    evaluator = criterion.evaluator
    if evaluator.kind == "text":
        result = TEXT_PREDICATES[evaluator.ref[0]](lines)
        status = {
            Outcome.PASS: MET,
            Outcome.FAIL: NOT_MET,
            Outcome.NOT_APPLICABLE: NOT_APPLICABLE,
        }[result.outcome]
        evidence: tuple[str, ...] = result.evidence
    elif evaluator.kind == "check":
        reading, evidence = _check_reading(evaluator.ref, verdicts)
        status = {"FAIL": NOT_MET, "PASS": MET, "UNKNOWN": NOT_EVALUATED}[reading]
    elif evaluator.kind == "review":
        status, evidence = _review_status(criterion.sections, review)
    else:
        status, evidence = NOT_EVALUATED, ("no deterministic evaluator is ratified",)
    return {
        "id": criterion.id,
        "title": criterion.title,
        "status": status,
        "points": criterion.points,
        "evidence": list(evidence),
    }


def _disqualifier_row(
    disqualifier: Disqualifier,
    readme: str,
    lines: Sequence[Line],
    verdicts: Mapping[str, Any],
    template: TemplateInputs | None,
) -> dict[str, Any]:
    evaluator = disqualifier.evaluator
    evidence: tuple[str, ...]
    if evaluator.kind == "template":
        if template is None:
            status = UNEVALUATED
            evidence = ("no template evidence or reference corpus was supplied",)
        else:
            judged = check_template_filling(readme, template.evidence, template.corpus)
            status = {
                Verdict.DISQUALIFIED: TRIGGERED,
                Verdict.PASS: NOT_TRIGGERED,
                Verdict.UNEVALUATED: UNEVALUATED,
            }[judged.verdict]
            evidence = judged.evidence
    elif evaluator.kind == "text":
        result = TEXT_PREDICATES[evaluator.ref[0]](lines)
        status = TRIGGERED if result.outcome == Outcome.FAIL else NOT_TRIGGERED
        evidence = result.evidence
    elif evaluator.kind == "check":
        reading, evidence = _check_reading(evaluator.ref, verdicts)
        status = {"FAIL": TRIGGERED, "PASS": NOT_TRIGGERED, "UNKNOWN": UNEVALUATED}[reading]
    else:
        status, evidence = UNEVALUATED, ("no deterministic evaluator is ratified",)
    return {
        "id": disqualifier.id,
        "title": disqualifier.title,
        "status": status,
        "evidence": list(evidence),
    }


def _check_reading(refs: Sequence[str], verdicts: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    """Read the named blocking checks' verdicts: FAIL if any failed, PASS if all passed, and
    UNKNOWN otherwise. A missing or PENDING verdict is never read as a pass."""
    evidence = tuple(f"{ref} {verdicts.get(ref, 'ABSENT')}" for ref in refs)
    if any(verdicts.get(ref) == "FAIL" for ref in refs):
        return "FAIL", evidence
    if all(verdicts.get(ref) == "PASS" for ref in refs):
        return "PASS", evidence
    return "UNKNOWN", evidence


def _review_status(
    sections: Sequence[str], review: Mapping[str, Any]
) -> tuple[str, tuple[str, ...]]:
    """A finding the reviewer raised on one of the criterion's sections counts against it,
    blocking or advisory. A finding the reviewer itself flagged as its own defect does not."""
    raised: list[str] = []
    for kind, records in (
        ("blocking", review.get("findings", [])),
        ("advisory", review.get("advisory", [])),
    ):
        for record in records:
            if record.get("reviewer_scope_defect"):
                continue
            if record.get("section_id") in sections:
                raised.append(
                    f"{kind} {record.get('criterion')} finding on {record.get('section_id')} "
                    f"(causal stage {record.get('causal_stage')})"
                )
    if raised:
        return NOT_MET, tuple(raised)
    verdict = review.get("verdict")
    if verdict == "ACCEPT":
        return MET, ("reviewer ACCEPT; no finding names these sections",)
    return NOT_EVALUATED, (f"reviewer verdict {verdict}; no finding names these sections",)
