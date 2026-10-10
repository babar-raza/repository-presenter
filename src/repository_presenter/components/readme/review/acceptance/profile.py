"""The acceptance profile of a candidate README: criteria, points, and hard disqualifiers.

RATIFIED (G7-W20, OWNER-13, 2026-10-10). The owner ratified the 26 criteria, their point weights,
and the 14 disqualifiers: C01, C02, C21 and C24 carry two points and every other criterion one,
which makes the stated 30 (``docs/DECISION_LOG.md``, 2026-10-10). Three sub-decisions were
confirmed with the weights: a criterion whose condition does not apply (no third-party notices
file, no examples, no H1) is credited as met; a banner link to an Aspose destination above the
opening paragraph fails C01; and D14 is judged by ``template_check.py``.

What the score gates. A candidate is publication-eligible only when it scores the full
``TOTAL_POINTS`` with no disqualifier triggered and none left unevaluated (the portfolio funnel,
``bundle/portfolio.py``). The score does NOT gate ``READY_FOR_PROPOSAL``, which stays blocking
checks BC-01..BC-11 plus no-op proof; whether it should is the part of OWNER-13 the owner has not
answered. Constructing a ratified ``Profile`` whose points are missing or do not total
``TOTAL_POINTS`` raises ``ProfileError``, so a broken ratification fails at import.

Source: ``plans/idea.md`` (cited as ``L<first>-<last>``, 1-based lines of that file). The file
states the 30-point rubric and the hard-disqualifier requirement only in aggregate:

- ``L19``: the 30-point rubric is reimplemented behind this project's typed contracts.
- ``L118``: candidates must pass "native 30-point acceptance".
- ``L177``: the first milestone needs "criterion-specific evidence for all 30 rubric points with
  zero hard disqualifiers".
- ``L318``: every processable repository must remain "30/30".

It does not list the criteria or label any requirement a hard disqualifier. Each entry below is a
normative sentence of ``plans/idea.md`` restated as a checkable entry, cited beside it; the
grouping into criteria is this module's own, ratified with the weights.

Evaluator kinds:

- ``check``: judged by the named blocking checks in ``validation.json`` (read, never changed).
- ``text``: a deterministic predicate over the README text, in ``text_checks.py``.
- ``review``: judged from ``review.json`` findings naming the criterion's sections.
- ``template``: the deterministic D14 checker in ``template_check.py``, which needs the
  repository's evidence and a corpus of other repositories' READMEs; without them it is
  unevaluated and can never count as passed.
- ``unevaluated``: no evaluator exists. The entry stays unevaluated, so it can never pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PROFILE_VERSION = "2"  # "1" was the unratified, unweighted draft.
SOURCE_DOCUMENT = "plans/idea.md"
TOTAL_POINTS = 30  # plans/idea.md L177 and L318: "30 rubric points", "30/30".
RATIFIED = True

EvaluatorKind = Literal["check", "text", "review", "template", "unevaluated"]


class ProfileError(ValueError):
    """The acceptance profile is internally inconsistent; the scorer refuses to run on it."""


@dataclass(frozen=True)
class Evaluator:
    """How an entry is judged. ``ref`` holds blocking-check IDs (``check``) or a text predicate
    name (``text``); it is empty for ``review`` and ``unevaluated``."""

    kind: EvaluatorKind
    ref: tuple[str, ...] = ()


@dataclass(frozen=True)
class Criterion:
    """A point-bearing criterion. ``points`` is ``None`` only in an unratified profile."""

    id: str
    title: str
    statement: str
    source: tuple[str, ...]
    evaluator: Evaluator
    sections: tuple[str, ...]
    points: int | None = None


@dataclass(frozen=True)
class Disqualifier:
    """A hard disqualifier: when triggered, the candidate fails whatever its points are."""

    id: str
    title: str
    statement: str
    source: tuple[str, ...]
    evaluator: Evaluator


@dataclass(frozen=True)
class Profile:
    version: str
    criteria: tuple[Criterion, ...]
    disqualifiers: tuple[Disqualifier, ...]
    total_points: int = TOTAL_POINTS
    ratified: bool = RATIFIED

    def __post_init__(self) -> None:
        """A ratified profile states every point and they total ``total_points``; anything else
        is a broken ratification and fails loudly where the profile is built."""
        if not self.ratified:
            return
        weights = [criterion.points for criterion in self.criteria]
        if any(weight is None for weight in weights):
            raise ProfileError("a ratified profile must carry a point weight on every criterion")
        if any(not isinstance(weight, int) or weight < 0 for weight in weights):
            raise ProfileError("a ratified profile's point weights must be non-negative integers")
        total = sum(weight for weight in weights if weight is not None)
        if total != self.total_points or self.total_points != TOTAL_POINTS:
            raise ProfileError(
                f"a ratified profile's points total {total}, not the stated {TOTAL_POINTS}"
            )


CRITERIA: tuple[Criterion, ...] = (
    # idea.md L37-43 ("product should come first") and L78-79 ("the opening explains the FOSS
    # product before any Aspose promotional destination"). Owner ruling 2026-10-10: the banner's
    # link to products.aspose.org stays and is not a destination; a link to aspose.com (or any
    # other Aspose destination) above the opening paragraph still counts as one and fails C01.
    Criterion(
        id="C01",
        title="Product explained before promotion",
        statement="The opening explains the FOSS product before any Aspose destination appears.",
        source=("L37-43", "L78-79"),
        evaluator=Evaluator("text", ("promotion_after_product",)),
        sections=("opening",),
        points=2,
    ),
    # idea.md L42-48: what it does, problems it solves, features and formats, install and use,
    # and whether it is actively maintained.
    Criterion(
        id="C02",
        title="Visitor orientation",
        statement="A visitor learns what it does, what it solves, its features and formats, how to "
        "install and use it, and whether it is maintained.",
        source=("L42-48",),
        evaluator=Evaluator("review"),
        sections=("opening", "key_capabilities", "installation", "badges"),
        points=2,
    ),
    # idea.md L75-78: one factual H1 and one compact badge row, not duplicated, split, or
    # fabricated. Validated by BC-07, which owns structure.
    Criterion(
        id="C03",
        title="One H1 and one badge row",
        statement="Exactly one factual H1 and one compact badge row.",
        source=("L75-78",),
        evaluator=Evaluator("check", ("BC-07",)),
        sections=("identity", "badges"),
        points=1,
    ),
    # idea.md L81-85: the complete canonical product name at every product-identity position.
    Criterion(
        id="C04",
        title="Canonical product name",
        statement="Every visitor-facing identity position uses the complete canonical "
        "product name.",
        source=("L81-85",),
        evaluator=Evaluator("review"),
        sections=("identity", "opening", "at_a_glance", "enterprise_relationship"),
        points=1,
    ),
    # idea.md L87-89: the common visitor journey, including compact list-based navigation.
    Criterion(
        id="C05",
        title="Common visitor journey",
        statement="The document follows the common visitor journey in its stated order.",
        source=("L87-89",),
        evaluator=Evaluator("review"),
        sections=("navigation", "structure"),
        points=1,
    ),
    # idea.md L92-94: a prose license declaration with practical permissions and the notice
    # condition; the license is never a bare link.
    Criterion(
        id="C06",
        title="License as prose",
        statement="The license is a prose declaration, never a bare link.",
        source=("L92-94",),
        evaluator=Evaluator("text", ("license_prose",)),
        sections=("license",),
        points=1,
    ),
    # idea.md L90-92: a third-party notices file gets its own heading and a repository-relative
    # link with normal link text. Applies only when the file exists.
    Criterion(
        id="C07",
        title="Third-party notices link",
        statement="A third-party notices heading links the file with normal link text.",
        source=("L90-92",),
        evaluator=Evaluator("text", ("third_party_notices",)),
        sections=("third_party_notices",),
        points=1,
    ),
    # idea.md L98: title-case headings and canonical technical abbreviations. BC-07 owns both.
    Criterion(
        id="C08",
        title="Title case and canonical abbreviations",
        statement="Headings use title case; technical abbreviations use canonical casing.",
        source=("L98",),
        evaluator=Evaluator("check", ("BC-07",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L99: At a Glance as a typed semantic graph with topology and column rules. BC-07.
    Criterion(
        id="C09",
        title="At a Glance topology",
        statement="At a Glance is a semantic capability graph with the required topology.",
        source=("L99",),
        evaluator=Evaluator("check", ("BC-07",)),
        sections=("at_a_glance",),
        points=1,
    ),
    # idea.md L107: action-led, fact-grounded key-capability titles, without keyword stuffing.
    Criterion(
        id="C10",
        title="Capability titles",
        statement="Key-capability titles are natural action-led phrases grounded in facts.",
        source=("L107",),
        evaluator=Evaluator("review"),
        sections=("key_capabilities",),
        points=1,
    ),
    # idea.md L101-106: installation, the minimal example, core capabilities, material
    # limitations, and the development and testing summary stay visible. Only secondary material
    # may be collapsed. The text predicate checks the four named headings.
    Criterion(
        id="C11",
        title="Core sections stay visible",
        statement="Installation, core capabilities, limitations, and development and testing are "
        "never collapsed.",
        source=("L101-106",),
        evaluator=Evaluator("text", ("visible_core_sections",)),
        sections=("installation", "key_capabilities", "scope_limitations", "development_testing"),
        points=1,
    ),
    # idea.md L107: additional-example headings name tasks, and their preview prose exposes no
    # internal inventory, source-revision, syntax-check, static-API-check, or non-execution text.
    Criterion(
        id="C12",
        title="Task-named additional examples",
        statement="Additional examples have meaningful task names and no verification commentary.",
        source=("L107",),
        evaluator=Evaluator("text", ("example_headings",)),
        sections=("additional_examples",),
        points=1,
    ),
    # idea.md L107: source fences carry a language identifier, use normalized spacing, and have no
    # repeated empty-line runs. The predicate checks presence and runs, not language validity.
    Criterion(
        id="C13",
        title="Fence languages and spacing",
        statement="Every fence has a language identifier and there are no repeated "
        "empty-line runs.",
        source=("L107",),
        evaluator=Evaluator("text", ("fences_and_spacing",)),
        sections=("quick_start", "additional_examples", "installation"),
        points=1,
    ),
    # idea.md L103-104: representative assets shown openly, with a complete-inventory link when
    # items are omitted.
    Criterion(
        id="C14",
        title="Development and testing inventory",
        statement="Representative assets are shown openly; a complete-inventory link covers "
        "omissions.",
        source=("L103-104",),
        evaluator=Evaluator("review"),
        sections=("development_testing",),
        points=1,
    ),
    # idea.md L108: no redundant "Other platforms" or promotional section. The repeated-inventory
    # half of L109 is judged by the reviewer only and is not measured here.
    Criterion(
        id="C15",
        title="No Other Platforms section",
        statement="No redundant 'Other platforms' or promotional section appears.",
        source=("L108",),
        evaluator=Evaluator("text", ("other_platforms_section",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L109: internal assurance narration never appears in the public README.
    Criterion(
        id="C16",
        title="No assurance narration",
        statement="Internal assurance narration never appears in the public README.",
        source=("L109",),
        evaluator=Evaluator("text", ("assurance_narration",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L51-53 (the only edition name is Enterprise Edition) and L109 (the anchor).
    Criterion(
        id="C17",
        title="Enterprise Edition name",
        statement="Aspose.com products are named Enterprise Edition, the only edition name.",
        source=("L51-53", "L109"),
        evaluator=Evaluator("text", ("edition_name",)),
        sections=("enterprise_relationship", "documentation_resources"),
        points=1,
    ),
    # idea.md L56-58 and L60-66: contextual Aspose links, within ceilings, never a generic
    # substitute for an exact article. L489-490: relevant, naturally placed, not overly promotional.
    Criterion(
        id="C18",
        title="Contextual Aspose links",
        statement="Aspose links are contextual, relevant, and not overly promotional.",
        source=("L56-58", "L60-66", "L489-490"),
        evaluator=Evaluator("review"),
        sections=("documentation_resources", "enterprise_relationship"),
        points=1,
    ),
    # idea.md L110: every material source README unit maps exactly once to a destination, an
    # evidence-backed correction, or a justified omission. BC-05 owns that.
    Criterion(
        id="C19",
        title="Every source unit dispositioned",
        statement="Each material source README unit has exactly one explicit disposition.",
        source=("L110",),
        evaluator=Evaluator("check", ("BC-05",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L110 and L331-340: valuable maintainer content is preserved or improved in its
    # canonical section. BC-08 owns protected content.
    Criterion(
        id="C20",
        title="Valuable inherited content preserved",
        statement="Valuable maintainer content is preserved or improved in its canonical section.",
        source=("L110", "L331-340"),
        evaluator=Evaluator("check", ("BC-08",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L175-178 (independent factual review and the evidence-bound milestone) and
    # L455-464 (unsupported content is corrected or removed, never invented). BC-01 and BC-04.
    Criterion(
        id="C21",
        title="Public claims map to evidence",
        statement="Every public claim maps to accepted evidence; unresolved content is "
        "never invented.",
        source=("L175-178", "L455-464"),
        evaluator=Evaluator("check", ("BC-01", "BC-04")),
        sections=("structure",),
        points=2,
    ),
    # idea.md L361-368: examples and capability claims rest on the proven public consumer surface.
    Criterion(
        id="C22",
        title="Proven public consumer surface",
        statement="Examples and capability claims rest on the package's proven public surface.",
        source=("L361-368",),
        evaluator=Evaluator("review"),
        sections=("api_reference", "key_capabilities"),
        points=1,
    ),
    # idea.md L120-122: the composer's journey includes "acquisition, executed example".
    # BC-03 owns example execution.
    Criterion(
        id="C23",
        title="Executed example",
        statement="Every rendered example was executed or compiled in isolation at this revision.",
        source=("L120-122",),
        evaluator=Evaluator("check", ("BC-03",)),
        sections=("quick_start", "additional_examples"),
        points=1,
    ),
    # idea.md L47 (how to install) and L120-122 (acquisition). BC-02 owns install verification.
    Criterion(
        id="C24",
        title="Verified installation",
        statement="Installation instructions are verified against package and source evidence.",
        source=("L47", "L120-122"),
        evaluator=Evaluator("check", ("BC-02",)),
        sections=("installation",),
        points=2,
    ),
    # idea.md L175-177: "independent factual and visitor review". BC-10 owns the verdict.
    Criterion(
        id="C25",
        title="Independent review accepts",
        statement="An independent, non-authoring factual and visitor review accepts the candidate.",
        source=("L175-177",),
        evaluator=Evaluator("check", ("BC-10",)),
        sections=("structure",),
        points=1,
    ),
    # idea.md L120-122: a coherent developer journey, not a fact inventory; review rejects
    # unhelpful presentation.
    Criterion(
        id="C26",
        title="Coherent developer journey",
        statement="The document reads as a coherent developer journey, not a fact inventory.",
        source=("L120-122",),
        evaluator=Evaluator("review"),
        sections=("structure",),
        points=1,
    ),
)


DISQUALIFIERS: tuple[Disqualifier, ...] = (
    # idea.md L109: internal assurance narration never appears in the public README.
    Disqualifier(
        id="D01",
        title="Assurance narration in the public README",
        statement="Source revisions, isolated-build conditions, network policy, registry receipts, "
        "provider calls, evidence collectors, or validation status appear in the README.",
        source=("L109",),
        evaluator=Evaluator("text", ("assurance_narration",)),
    ),
    # idea.md L110: a generic implementation label such as "Preserved repository details".
    Disqualifier(
        id="D02",
        title="Generic implementation label",
        statement="A generic implementation label such as 'Preserved repository details' appears.",
        source=("L110",),
        evaluator=Evaluator("text", ("implementation_label",)),
    ),
    # idea.md L51-53: no non-canonical edition name for an Aspose.com product.
    Disqualifier(
        id="D03",
        title="Non-canonical edition name",
        statement="An Aspose.com product is called a commercial, paid, full, or On-Premise "
        "edition.",
        source=("L51-53",),
        evaluator=Evaluator("text", ("edition_name",)),
    ),
    # idea.md L108: no "Other platforms" or promotional section.
    Disqualifier(
        id="D04",
        title="Other platforms or promotional section",
        statement="An 'Other platforms' or promotional section appears.",
        source=("L108",),
        evaluator=Evaluator("text", ("other_platforms_section",)),
    ),
    # idea.md L75-76: "Every README has exactly one factual H1."
    Disqualifier(
        id="D05",
        title="Not exactly one H1",
        statement="The document does not have exactly one H1 heading.",
        source=("L75-76",),
        evaluator=Evaluator("text", ("single_h1",)),
    ),
    # idea.md L77-78: the badge row may not be duplicated or split across multiple header rows.
    # Fabrication is not measured here; BC-07 judges the badge row.
    Disqualifier(
        id="D06",
        title="Badge row duplicated or split",
        statement="The badge row is duplicated, or split across more than one header row.",
        source=("L77-78",),
        evaluator=Evaluator("text", ("single_badge_row",)),
    ),
    # idea.md L455-464: unsupported statements are corrected or removed, never presented as fact.
    Disqualifier(
        id="D07",
        title="Public claim without accepted evidence",
        statement="A public claim has no accepted evidence.",
        source=("L455-464",),
        evaluator=Evaluator("check", ("BC-04",)),
    ),
    # idea.md L110: every material source unit maps to exactly one disposition; a unit with no
    # safe destination fails closed.
    Disqualifier(
        id="D08",
        title="Source unit without one disposition",
        statement="A material source README unit lacks exactly one disposition or a safe "
        "destination.",
        source=("L110",),
        evaluator=Evaluator("check", ("BC-05",)),
    ),
    # idea.md L120-122 ("executed example") and L175-178 (the evidence-bound milestone).
    Disqualifier(
        id="D09",
        title="Unverified example or install command",
        statement="A rendered example or install command was not executed or verified at "
        "this revision.",
        source=("L120-122", "L175-178"),
        evaluator=Evaluator("check", ("BC-02", "BC-03")),
    ),
    # idea.md L339-340: regeneration convenience is never a reason to discard valuable content.
    Disqualifier(
        id="D10",
        title="Valuable inherited content discarded",
        statement="Valuable maintainer content is discarded without a justified disposition.",
        source=("L339-340",),
        evaluator=Evaluator("check", ("BC-08",)),
    ),
    # idea.md L56-58: a generic page is not a contextual substitute; with no verified target, the
    # natural result is no link.
    Disqualifier(
        id="D11",
        title="Unverified or substitute link",
        statement="A link targets an unverified destination or a generic page stands in for "
        "an article.",
        source=("L56-58",),
        evaluator=Evaluator("check", ("BC-06",)),
    ),
    # idea.md L175-177: the milestone requires independent factual and visitor review.
    Disqualifier(
        id="D12",
        title="Independent review not accepted",
        statement="The independent factual or visitor review does not accept the candidate.",
        source=("L175-177",),
        evaluator=Evaluator("check", ("BC-10",)),
    ),
    # idea.md L419-420: credentials never appear in evidence or artifacts.
    Disqualifier(
        id="D13",
        title="Secret in the candidate bundle",
        statement="A configured secret value appears in the candidate bundle.",
        source=("L419-420",),
        evaluator=Evaluator("check", ("BC-09",)),
    ),
    # idea.md L344-346: phrase-matching or template-filling alone does not satisfy the standard.
    # Judged by template_check.py against the other repositories' READMEs; with no evidence or no
    # corpus it is unevaluated, so a score never passes it silently.
    Disqualifier(
        id="D14",
        title="Mechanical template filling",
        statement="The candidate is produced by phrase-matching or template-filling, with no "
        "interpretive reasoning behind it.",
        source=("L344-346",),
        evaluator=Evaluator("template"),
    ),
)


PROFILE = Profile(
    version=PROFILE_VERSION,
    criteria=CRITERIA,
    disqualifiers=DISQUALIFIERS,
)
