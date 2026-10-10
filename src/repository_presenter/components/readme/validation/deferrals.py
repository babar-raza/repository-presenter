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

G7-W12 (REG-18) added five classes (and a second signal for ENTERPRISE_NON_PROSE) from the
2026-10-09 re-seal pass's UNCLASSIFIED units. Two mechanisms made them unclassifiable, and both
are why a class here matches on the unit's own source section, the facts and the sibling
dispositions rather than on the rationale alone:

* The deterministic folds in ``reconciliation/dispositions.py`` (a placement into an Installation
  row that renders nothing, into At a Glance with no citation, into the Enterprise row as a table)
  rewrite the disposition to DEFER_UNRESOLVED and clear the destination but keep the model's
  rationale, which still describes the placement it proposed ("placed in the installation
  section"). The route is gone; the unit's source section and the facts are not.
* The re-ask template tells the model to answer DEFER_UNRESOLVED when it cannot cite a fact, and
  the model applies that to units the rejection never named (a build command it first omitted, a
  list its sibling batch superseded into api_reference). The rationale there IS the model's
  statement of cause, so a class may read it, but only as an attestation the facts must not
  contradict (``NO_EVIDENCE_EITHER_WAY``).

TC-DSP-01 (G3-W08) stopped the reconciler from calling a unit "superseded" unless its destination
provably carries it; on the last attempt it defers such a unit instead, with a typed rationale
prefix (``RECOVERED_COVERAGE_RATIONALE``). ``NOT_CARRIED_BY_NAMED_SECTION`` classifies that one
cause ADVISORY (OWNER-14: a deferred unit is never public, and blocks only in specific classes),
matched on the typed prefix and never on free text, and last in precedence so every BLOCK class
above still decides first.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from repository_presenter.components.readme.composition.planning import section_conditions
from repository_presenter.components.readme.evidence.facts.product_pages import (
    ENTERPRISE_FACT_ID,
    enterprise_target,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    RECOVERED_COVERAGE_RATIONALE,
    code_units_by_polarity,
    command_block_units,
    contradicted_code_units,
)
from repository_presenter.core.facts import Fact, FactsDocument

Decision = Literal["BLOCK", "ADVISORY"]
Stage = Literal["EXTRACTING", "RECONCILING"]
UNCLASSIFIED = "UNCLASSIFIED"
# The rationale and text patterns below are matched case-insensitively where noted.
_INTERNAL_FILE = re.compile(r"AGENTS\.md|CLAUDE\.md")
# Licensing or attribution language. A bare "font" is not: it names a Mermaid label, an examples
# row or an API member (``FontScheme``) as often as bundled font files, so a font counts only
# when it is bundled, embedded or redistributed (G7-W12: three real units blocked on it wrongly).
_NOTICES = re.compile(
    r"third[ _-]?party|licen[cs]e|SPDX|\bnotices?\b"
    r"|\b(?:bundled|embedded|redistributed|included)\s+fonts?\b",
    re.IGNORECASE,
)
_ENTERPRISE = re.compile(r"enterprise", re.IGNORECASE)
_EXAMPLES = re.compile(r"\bexamples?\b|\bbelow\b", re.IGNORECASE)
_DEVELOPMENT = re.compile(r"development|testing|\btests?\b|\bbuild|\bsamples?\b", re.IGNORECASE)
_AT_A_GLANCE = re.compile(r"\bat a glance\b")
_INSTALLATION = re.compile(r"^install")
_API_SECTION = re.compile(r"\bapi\b")
# The model's own statement that it searched the facts and found nothing either way; the wording
# the re-ask template ("Where you cannot find such a record, empty the array and choose
# DEFER_UNRESOLVED") and the prompt's definition of DEFER_UNRESOLVED ("the facts neither support
# nor contradict") produce.
_NO_EVIDENCE = re.compile(
    r"\bno fact\b|\bany fact\b|\bnot (?:supported|contradicted|verified)\b"
    r"|lacks? supporting evidence|neither support",
    re.IGNORECASE,
)
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_DOTTED_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_MIN_SYMBOL_TAIL = 4


def _section_parts(raw: str | None) -> tuple[str, ...]:
    """A heading path ("Product > Installation > Requirements") as normalised lowercase parts."""
    if not raw:
        return ()
    parts = (re.sub(r"[^a-z0-9]+", " ", part.lower()).strip() for part in raw.split(">"))
    return tuple(part for part in parts if part)


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
    sections: Mapping[str, tuple[str, ...]]
    install_verified: bool
    build_or_install: bool
    symbols: frozenset[str]
    symbol_tails: frozenset[str]
    enterprise_sections: frozenset[tuple[str, ...]]
    contradicted: frozenset[str]

    @classmethod
    def build(
        cls,
        dispositions: Mapping[str, Any],
        facts: FactsDocument,
        plan: Mapping[str, Any] | None = None,
    ) -> DeferralContext:
        conditions = section_conditions(facts)
        verified = {fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"}
        entries = {
            str(entry.get("unit_id", "")): entry for entry in dispositions.get("dispositions", [])
        }
        sections = {
            fact.id: _section_parts((fact.attributes or {}).get("section"))
            for fact in facts.by_kind("inherited_unit")
        }
        symbols = frozenset(
            fact.value
            for fact in (*facts.by_kind("public_symbol"), *facts.by_kind("import_path"))
            if fact.polarity == "SUPPORTED"
        )
        starts = set()
        if plan is not None:
            starts = {
                plan.get("quick_start_example_id"),
                plan.get("second_quick_start_example_id"),
            } - {None}
        return cls(
            units={fact.id: fact for fact in facts.by_kind("inherited_unit")},
            entries=entries,
            unresolved=frozenset(code_units_by_polarity(facts, "UNRESOLVED")),
            commands=frozenset(command_block_units(facts)),
            absent=frozenset(section for section, holds in conditions.items() if holds is False),
            enterprise=enterprise_target(facts.facts) is not None,
            notices=bool(facts.by_kind("third_party_notices")),
            examples_consumed=plan is not None and bool(verified) and not (verified - starts),
            sections=sections,
            install_verified=any(
                fact.polarity == "SUPPORTED" for fact in facts.by_kind("install_command")
            ),
            build_or_install=any(
                fact.polarity == "SUPPORTED"
                for kind in ("install_command", "build_test_asset")
                for fact in facts.by_kind(kind)
            ),
            symbols=symbols,
            symbol_tails=frozenset(value.rsplit(".", 1)[-1] for value in symbols),
            enterprise_sections=frozenset(
                sections[unit_id]
                for unit_id, entry in entries.items()
                if entry.get("disposition") == "SUPERSEDE_REDUNDANT"
                and ENTERPRISE_FACT_ID in (entry.get("fact_ids") or [])
                and not unit_id.endswith(".heading")
                and sections.get(unit_id)
            ),
            contradicted=contradicted_code_units(facts),
        )

    def text(self, unit_id: str) -> str:
        fact = self.units.get(unit_id)
        return fact.value if fact is not None else ""

    def parts(self, unit_id: str) -> tuple[str, ...]:
        """The unit's source heading path; a heading unit's own title counts as its last part
        (the extractor records a heading's section as its parent's)."""
        parts = self.sections.get(unit_id, ())
        if _kind(unit_id) == "heading":
            return (*parts, *_section_parts(self.text(unit_id).lstrip("# ").strip()))
        return parts

    def names_verified_symbol(self, unit_id: str, *, shape: str = "prose") -> bool:
        """The unit's own code spans spell a SUPPORTED public symbol or import path.

        ``shape`` says how much a spelling proves. A ``listing`` (a list or table of API members)
        is about its first span, so a class-like tail of that one name (``Chart`` for
        ``slides_foss.charts.Chart``) is evidence the facts hold what it lists. ``prose`` makes
        a claim around its names, so only a whole symbol or import path (``widget.Scene``)
        counts: a bare class name inside a sentence about slide-size constants verifies nothing
        about the constants (Slides-.NET inherited_unit:028 mentions `Presentation`). A tail
        counts only when it reads as a type or member name (capitalised, or snake_case) of at
        least ``_MIN_SYMBOL_TAIL`` characters, so ordinary words in a code span never do."""
        listing = shape == "listing"
        spans = _CODE_SPAN.findall(self.text(unit_id))
        for span in spans[:1] if listing else spans:
            names = _DOTTED_NAME.findall(span)
            for name in names[:1] if listing else names:
                if name in self.symbols:
                    return True
                tail = name.rsplit(".", 1)[-1]
                typed = tail[:1].isupper() or "_" in tail
                if (
                    listing
                    and len(tail) >= _MIN_SYMBOL_TAIL
                    and typed
                    and tail in self.symbol_tails
                ):
                    return True
        return False

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
    """The upstream documents a build, test or sample path: a shell command, a rationale that
    says so, or a unit under the upstream's own Development/Testing/Samples section (the
    rationale of a unit a fold deferred often says only "retained as written")."""
    return "development_testing" in ctx.absent and (
        unit_id in ctx.commands
        or bool(_DEVELOPMENT.search(_rationale(entry)))
        or any(_DEVELOPMENT.search(part) for part in ctx.parts(unit_id)[1:])
    )


def _notices(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return not ctx.notices and bool(_NOTICES.search(ctx.text(unit_id)))


def _unverified(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return unit_id in ctx.unresolved


def _enterprise_missing(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return not ctx.enterprise and bool(_ENTERPRISE.search(ctx.text(unit_id)))


def _enterprise_non_prose(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    """A table or list bound for the Enterprise row: the model said so, or its own neighbours in
    the same source section were folded into that row (they cite the enterprise fact). The second
    signal is what the fold leaves behind when the rationale talks about "editions"."""
    if not ctx.enterprise or _kind(unit_id) not in {"table", "list"}:
        return False
    sibling = bool(ctx.sections.get(unit_id)) and ctx.sections[unit_id] in ctx.enterprise_sections
    return sibling or bool(_ENTERPRISE.search(_rationale(entry)))


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


def _uncited(entry: Mapping[str, Any]) -> bool:
    return not entry.get("fact_ids")


def _at_a_glance(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return any(_AT_A_GLANCE.search(part) for part in ctx.parts(unit_id)[1:])


def _install_steps(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return not ctx.install_verified and any(
        _INSTALLATION.match(part) for part in ctx.parts(unit_id)[1:]
    )


def _withheld_command(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return unit_id in ctx.commands and _uncited(entry) and ctx.build_or_install


def _api_listing(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return (
        _kind(unit_id) in {"list", "table"}
        and _uncited(entry)
        and any(_API_SECTION.search(part) for part in ctx.sections.get(unit_id, ())[1:])
        and ctx.names_verified_symbol(unit_id, shape="listing")
    )


def _not_carried(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    """The reconciler's own last-attempt deferral of a disposition that claimed more than the
    stage could prove (``dispositions._recover_uncovered``), read from the typed prefix it
    writes: ``RECOVERED_COVERAGE_RATIONALE``, a constant the model's reply never carries because
    the recovery runs after the reply and prepends it. A contradicted code block is excluded: it
    belongs to the omission rule (OMIT_UNSUPPORTED on CONTRADICTED), so a deferral of it is not
    this cause and stays unclassified."""
    return unit_id not in ctx.contradicted and str(entry.get("rationale") or "").startswith(
        RECOVERED_COVERAGE_RATIONALE.rstrip()
    )


def _no_evidence(unit_id: str, entry: Mapping[str, Any], ctx: DeferralContext) -> bool:
    return (
        _uncited(entry)
        and bool(_NO_EVIDENCE.search(str(entry.get("rationale") or "")))
        and not ctx.names_verified_symbol(
            unit_id, shape="listing" if _kind(unit_id) in {"list", "table"} else "prose"
        )
    )


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
        "AT_A_GLANCE_COVERED_BY_DIAGRAM",
        "ADVISORY",
        None,
        "The unit came from the upstream's At a Glance section. The candidate's At a Glance is "
        "exactly one Mermaid diagram the renderer draws from verified facts (README_CONTRACT.md "
        "row 6), so a caption or inherited prose has no place in it and is withheld rather than "
        "published beside it.",
        _at_a_glance,
    ),
    DeferralClass(
        "INSTALL_STEPS_UNVERIFIED",
        "ADVISORY",
        None,
        "The unit is installation guidance, but no install_command is SUPPORTED at this "
        "revision (the registry could not confirm it, or contradicted it), so the Installation "
        "row states what is and is not verified and the upstream's own steps cannot be shown "
        "as verified. They are withheld, never published; the reviewer sees the deferral.",
        _install_steps,
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
    DeferralClass(
        "COMMAND_BLOCK_WITHHELD",
        "BLOCK",
        "RECONCILING",
        "A shell command block was deferred with no citation while the repository has a verified "
        "install command or build and test asset. The maintainers' own command is kept where it "
        "was or superseded by the Installation row, never withheld (the same rule that refuses "
        "OMIT_UNSUPPORTED on it); reconciliation must fold an uncited DEFER_UNRESOLVED on a "
        "command block like the omission it restates.",
        _withheld_command,
    ),
    DeferralClass(
        "API_LISTING_COVERED_BY_CORE_API",
        "ADVISORY",
        None,
        "An inherited API listing under the upstream's API reference, naming symbols the facts "
        "verify. The Core API section renders from the verified symbol facts (README_CONTRACT.md "
        "row 14), so the listing is covered by it and is withheld rather than placed beside it.",
        _api_listing,
    ),
    DeferralClass(
        "NO_EVIDENCE_EITHER_WAY",
        "ADVISORY",
        None,
        "The facts neither support nor contradict the unit's claim: the model searched them, "
        "cited none and said so, and the unit spells no verified symbol that would falsify that. "
        "This is DEFER_UNRESOLVED's own meaning: a claim withheld, listed for the owner, and "
        "never published; public content must map to accepted evidence.",
        _no_evidence,
    ),
    DeferralClass(
        "NOT_CARRIED_BY_NAMED_SECTION",
        "ADVISORY",
        None,
        "The reconciler named a section as carrying this unit, but that section does not provably "
        "render it (TC-DSP-01), so on the last attempt the supersession was withdrawn and the unit "
        "deferred. Nothing is lost: the unit is listed for the owner and never published, and "
        "its cited facts stay in the evidence. Last in precedence, so any cause that names a "
        "specific fix (a missing Quick Start, an unrecorded build path) still decides first.",
        _not_carried,
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
