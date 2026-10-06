"""The deferral policy: what each DEFER_UNRESOLVED unit does to a candidate, by its cause.

A deferred unit is never placed, so it can never reach the public README (``composition/
placement.py`` places only PLACED dispositions). What a deferral can still do is fail the
candidate: a class marked BLOCK makes BC-05 fail, so the candidate cannot be proposed until the
cause is fixed; a class marked ADVISORY is recorded in ``validation.json``'s ``advisory`` list,
where the reviewer sees it, and never blocks. A unit that matches no class blocks, so a new
cause fails closed until it is registered here.

The classes below were derived from the 93 DEFER_UNRESOLVED units in the sealed bundles under
``candidates/`` (19 bundles, 2026-10-05). The fold that defers a unit does not record which of
its branches fired, so each class is matched from what the bundle does keep: the post-fold
entry, the facts (UNRESOLVED examples, command blocks, which sections' conditions hold), the
plan, the unit's own text, and the model's recorded rationale. Adding a class means adding one
``DeferralClass`` to ``DEFERRAL_CLASSES``; no caller changes.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from repository_presenter.components.readme.composition.planning import section_conditions
from repository_presenter.components.readme.evidence.facts.product_pages import enterprise_target
from repository_presenter.components.readme.reconciliation.dispositions import (
    code_units_by_polarity,
    command_block_units,
)
from repository_presenter.core.facts import Fact, FactsDocument

Decision = Literal["BLOCK", "ADVISORY"]
Stage = Literal["EXTRACTING", "RECONCILING"]
UNCLASSIFIED = "UNCLASSIFIED"
# The rationale and text patterns below are matched case-insensitively where noted.
_INTERNAL_FILE = re.compile(r"AGENTS\.md|CLAUDE\.md")
_NOTICES = re.compile(r"third[ _-]?party|licen[cs]e|\bfonts?\b|SPDX|\bnotices?\b", re.IGNORECASE)
_ENTERPRISE = re.compile(r"enterprise", re.IGNORECASE)
_EXAMPLES = re.compile(r"\bexamples?\b|\bbelow\b", re.IGNORECASE)
_DEVELOPMENT = re.compile(r"development|testing|\btests?\b|\bbuild|\bsamples?\b", re.IGNORECASE)


@dataclass(frozen=True)
class DeferralContext:
    """What a class may match on, computed once per candidate from its own bundle records."""

    units: Mapping[str, Fact]
    entries: Mapping[str, Mapping[str, Any]]
    unresolved: frozenset[str]
    commands: frozenset[str]
    absent: frozenset[str]
    enterprise: bool
    notices: bool
    examples_consumed: bool

    @classmethod
    def build(
        cls,
        dispositions: Mapping[str, Any],
        facts: FactsDocument,
        plan: Mapping[str, Any] | None = None,
    ) -> DeferralContext:
        conditions = section_conditions(facts)
        verified = {fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"}
        starts = set()
        if plan is not None:
            starts = {
                plan.get("quick_start_example_id"),
                plan.get("second_quick_start_example_id"),
            } - {None}
        return cls(
            units={fact.id: fact for fact in facts.by_kind("inherited_unit")},
            entries={
                str(entry.get("unit_id", "")): entry
                for entry in dispositions.get("dispositions", [])
            },
            unresolved=frozenset(code_units_by_polarity(facts, "UNRESOLVED")),
            commands=frozenset(command_block_units(facts)),
            absent=frozenset(section for section, holds in conditions.items() if holds is False),
            enterprise=enterprise_target(facts.facts) is not None,
            notices=bool(facts.by_kind("third_party_notices")),
            examples_consumed=plan is not None and bool(verified) and not (verified - starts),
        )

    def text(self, unit_id: str) -> str:
        fact = self.units.get(unit_id)
        return fact.value if fact is not None else ""

    def neighbor_dropped(self, unit_id: str) -> bool:
        """The next block in document order is withheld: OMIT_UNSUPPORTED or DEFER_UNRESOLVED."""
        match = re.match(r"^inherited_unit:(\d{3})(?:\.\d{3})?\.[a-z_]+$", unit_id)
        if match is None:
            return False
        neighbor = self.entries.get(f"inherited_unit:{int(match.group(1)) + 1:03d}.code_block")
        return neighbor is not None and neighbor.get("disposition") in {
            "OMIT_UNSUPPORTED",
            "DEFER_UNRESOLVED",
        }


Matcher = Callable[[str, Mapping[str, Any], DeferralContext], bool]


@dataclass(frozen=True)
class DeferralClass:
    """One cause of deferral: how it is recognised, what it does, and why."""

    id: str
    decision: Decision
    stage: Stage | None  # causal stage of the BC-05 failure a BLOCK class raises
    reason: str
    matches: Matcher


def _kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _rationale(entry: Mapping[str, Any]) -> str:
    return str(entry.get("rationale") or "").lower()


def _no_quick_start(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return unit_id in ctx.unresolved and "quick_start" in ctx.absent


def _internal(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return bool(_INTERNAL_FILE.search(ctx.text(unit_id)))


def _build_path(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return "development_testing" in ctx.absent and (
        unit_id in ctx.commands or bool(_DEVELOPMENT.search(_rationale(entry)))
    )


def _notices(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return not ctx.notices and bool(_NOTICES.search(ctx.text(unit_id)))


def _unverified(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return unit_id in ctx.unresolved


def _enterprise_missing(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return not ctx.enterprise and bool(_ENTERPRISE.search(ctx.text(unit_id)))


def _enterprise_non_prose(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return (
        ctx.enterprise
        and _kind(unit_id) in {"table", "list"}
        and bool(_ENTERPRISE.search(_rationale(entry)))
    )


def _excluded_by_plan(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return ctx.examples_consumed and "additional" in _rationale(entry)


def _section_absent(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    rationale = _rationale(entry)
    return any(
        section.replace("_", " ") in rationale or section in rationale for section in ctx.absent
    )


def _lead_in(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    if _kind(unit_id) not in {"paragraph", "list"}:
        return False
    if ctx.text(unit_id).rstrip().endswith(":") and ctx.neighbor_dropped(unit_id):
        return True
    examples_absent = bool({"quick_start", "additional_examples"} & ctx.absent)
    return examples_absent and bool(_EXAMPLES.search(f"{ctx.text(unit_id)} {_rationale(entry)}"))


# Precedence: the first matching class decides. Blocking causes that name a specific fix come
# first; a lead-in comes last because its own withholding follows from its neighbor's class.
DEFERRAL_CLASSES: tuple[DeferralClass, ...] = (
    DeferralClass(
        "NO_VERIFIED_QUICK_START",
        "BLOCK",
        "EXTRACTING",
        "Every usage example the upstream documents is unverified at this revision, so the "
        "candidate would publish with no Quick Start. An extraction failure, not a content "
        "decision: fix example verification before shipping.",
        _no_quick_start,
    ),
    DeferralClass(
        "INTERNAL_DETAIL",
        "ADVISORY",
        None,
        "The unit names a repository-internal governance file (AGENTS.md or CLAUDE.md), which is "
        "not public documentation. It is never published.",
        _internal,
    ),
    DeferralClass(
        "BUILD_TEST_PATH_UNRECORDED",
        "BLOCK",
        "EXTRACTING",
        "The upstream documents a build, test or sample path, but no build_test_asset fact was "
        "recorded, so Development and Testing cannot render. An extractor gap, not an editorial "
        "choice: fix the build_test_asset extraction rather than ship without the contributor "
        "path.",
        _build_path,
    ),
    DeferralClass(
        "NOTICES_WITHOUT_RECORD",
        "BLOCK",
        "EXTRACTING",
        "The upstream documents licensing or third-party notices for bundled material, but no "
        "third_party_notices fact was recorded, so the attribution cannot render. Dropping "
        "attribution is a licensing risk: fix notice extraction first.",
        _notices,
    ),
    DeferralClass(
        "UNVERIFIED_EXAMPLE",
        "ADVISORY",
        None,
        "The code block's example did not execute or compile at this revision (UNRESOLVED). "
        "BC-03 forbids showing it, and withholding an unexecuted example is the truth-safe result.",
        _unverified,
    ),
    DeferralClass(
        "ENTERPRISE_NO_VERIFIED_TARGET",
        "ADVISORY",
        None,
        "The unit is Enterprise Edition relationship text, but no verified enterprise product "
        "target exists at this revision, so the relationship row cannot render and its link "
        "cannot be verified.",
        _enterprise_missing,
    ),
    DeferralClass(
        "ENTERPRISE_NON_PROSE",
        "ADVISORY",
        None,
        "The enterprise relationship row renders one verified prose sentence. A table or list "
        "placed there has no row, so it is withheld.",
        _enterprise_non_prose,
    ),
    DeferralClass(
        "EXCLUDED_BY_PLAN",
        "ADVISORY",
        None,
        "The plan's quick starts already consume every verified example, so Additional Examples "
        "is excluded at this plan. The examples themselves are shown in Quick Start.",
        _excluded_by_plan,
    ),
    DeferralClass(
        "SECTION_ABSENT",
        "ADVISORY",
        None,
        "The section the unit was placed in does not exist at this revision, so it has no public "
        "home. Its facts are supported; the reviewer sees the deferral on the bundle.",
        _section_absent,
    ),
    DeferralClass(
        "LEADIN_OF_WITHHELD_CONTENT",
        "ADVISORY",
        None,
        "A lead-in promises content that does not render: the colon-ending sentence's own block "
        "was withheld, or the examples it introduces are absent. It is withheld with them rather "
        "than promise what the candidate does not carry.",
        _lead_in,
    ),
)

_UNCLASSIFIED_REASON = (
    "No deferral class matches this cause. It blocks until a class is registered in "
    "validation/deferrals.py."
)


@dataclass(frozen=True)
class DeferralFinding:
    """One deferred unit, its class, and what that class does to the candidate."""

    unit_id: str
    class_id: str
    decision: Decision
    stage: Stage | None
    reason: str


def _check_registry() -> None:
    ids = [cls.id for cls in DEFERRAL_CLASSES]
    if len(set(ids)) != len(ids) or UNCLASSIFIED in ids:
        raise ValueError("deferral class IDs must be unique and must not be UNCLASSIFIED")
    for cls in DEFERRAL_CLASSES:
        if cls.decision == "BLOCK" and cls.stage is None:
            raise ValueError(f"blocking deferral class {cls.id} needs a causal stage")


_check_registry()


def review_deferrals(
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
    plan: Mapping[str, Any] | None = None,
) -> list[DeferralFinding]:
    """Every DEFER_UNRESOLVED unit classified; an unmatched one is a BLOCK finding."""
    ctx = DeferralContext.build(dispositions, facts, plan)
    findings: list[DeferralFinding] = []
    for entry in dispositions.get("dispositions", []):
        if entry.get("disposition") != "DEFER_UNRESOLVED":
            continue
        unit_id = str(entry.get("unit_id", ""))
        cls = next((c for c in DEFERRAL_CLASSES if c.matches(unit_id, entry, ctx)), None)
        if cls is None:
            findings.append(
                DeferralFinding(unit_id, UNCLASSIFIED, "BLOCK", "RECONCILING", _UNCLASSIFIED_REASON)
            )
        else:
            findings.append(DeferralFinding(unit_id, cls.id, cls.decision, cls.stage, cls.reason))
    return findings
