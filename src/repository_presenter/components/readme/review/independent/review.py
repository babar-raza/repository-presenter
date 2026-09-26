"""Stage S10: the independent review - one verdict and typed findings, under its own identity.

The reviewer is a separate governed job (prompts/independent_review.yaml) from authoring: a
different prompt, purpose, and rejection template, receiving the original README, the candidate,
the bounded facts, the plan, the dispositions, and the deterministic validation result as context
only. It never receives authoring instructions. Its output is one verdict from the contract's set
and findings that each name a section and a causal stage; a finding that names neither, or blames
a stage the repair loop cannot reopen, is recorded as advisory and cannot block. review.json also
records the reviewer's and the authoring job's prompt identities so check 10 can see they differ.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    SUBSECTION_HEADINGS,
    section_ids,
)
from repository_presenter.components.readme.composition.renderer import (
    ADDITIONAL_EXAMPLES_SUMMARY,
    API_SURFACE_SUMMARY,
)
from repository_presenter.components.readme.repair.targeted import defect_fingerprint
from repository_presenter.core.facts import FACT_KINDS, Fact, FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import LoadedManifest
from repository_presenter.core.registry.models import RegistryEntry

REVIEW_FILENAME = "review.json"
ACCEPT = "ACCEPT"
# The deterministic judgment this module owns - scope_defect and everything it calls
# (absence_defect, excluded_evidence_defect, rendered_defect, renderer_owned_defect,
# factuality_defect), plus quote_located and review_checks - decides which findings block a
# candidate, so it is a component dependencies.json records and a change to it reopens REVIEWING,
# the same way renderer.py/authoring.py/registry.py's own constants do (docs/STATE_MACHINE.md
# section 9). Only the *prompt's* hash/version was tracked before this (CS-04,
# docs/CI_AND_STALENESS_ASSESSMENT.md, 2026-09-09: this asymmetry meant a real logic change here -
# PA-02's quote_located section-scoping - had nothing to bump, unlike RENDERER_VERSION/BC-03/
# NORMALISATION_VERSION's own confirmed-missed-then-corrected bumps the same day). Starts at "2",
# not "1": retroactively credited for PA-02's already-landed change, which predates this constant.
# "3" (PHASE1/F6): review_document's accept path made symmetric - an ACCEPT is corroborated by a
# second independent read whose findings pass the same fold stack, a which-findings-block change.
# "4" (G4-W17 arrival items 62 and 63): two more findings fold as the reviewer's own defect - a
# factuality finding quoting a verified symbol's rendered row that no content unit wrote, and a
# presentation finding whose quote carries the literal value of a SUPPORTED fact it itself cites.
# "5" (G4-W17 arrival item 64): a standing absence finding records which of its claims the
# candidate already refuted and which remain, so the repair is handed only the remainder - a
# change to what review.json carries and what a repair round is asked to do.
# "6" (G4-W17 arrival item 83): factuality_defect and cited_fact_defect's literal-value
# refutation now also reads the one reviewed unit's own inherited_unit citations, not only the
# finding's self-reported fact_ids - a finding can be refuted by evidence its own unit cited even
# when the finding's own reply omitted it. The "cites at least one product fact" grounding gate
# item 39 established is untouched.
# "7" (G4-W17 arrival item 86): a new excluded_disposition_defect, beside excluded_evidence_defect,
# folds a finding demanding restoration of an inherited_unit S4 marked OMIT_UNSUPPORTED - now live,
# repair/rounds.py's own review_document call threads dispositions through as of this version.
# "8" (G4-W17 arrival items 79/96): cited_fact_defect now also folds a presentation-criterion
# finding that names neither a fact_id nor an absent claim, when the reviewed unit's own product
# fact citations literally back the quote - the same "nothing checkable" shape factuality_defect
# already closed for criterion=='factuality', narrowed here to the unit's own bounded evidence so
# a genuine style complaint citing nothing (the two-reader rule's own reason to exist) still stands.
# "9" (G4-W17 arrival item 101, LANE-B-R8-F1): _quoted_chrome now also recognizes the bare
# `<details>`/`</details>` tag lines the same renderer call sites emit beside the `<summary>` text
# it already covered - a finding quoting the literal tag was falling through every exemption
# branch and blocking on content no unit wrote and no repair could remove.
# "10" (G4-W17 arrival items 71/PROPOSAL AF and 91/PDFPY-01, landed together - both narrow
# _cited_literal/factuality_defect's own existing refutation paths, no shared mechanism between
# them beyond the file): (a) new _normalized_with_targets lets _cited_literal also match a cited
# link_target fact's own value against a quote that embeds a Markdown link's raw target, which
# _normalized alone always discards; (b) factuality_defect's CONTRADICTED-stands gate is scoped to
# unit_fact_ids (the reviewed unit's own citations), so a CONTRADICTED fact the finding's own
# self-report merely lists as unrelated context can no longer keep an otherwise unit-grounded,
# SUPPORTED-backed, verbatim-correct claim blocking.
# "11" (G4-W17 arrival items 116/LANE-B-W14R7-F1 and 118/PROPOSAL AG, landed together - both
# widen a grounding lookup with no shared mechanism between them beyond the file): (a) new
# _cited_paraphrase/_cited_grounding let factuality_defect and cited_fact_defect recognize a cited
# SUPPORTED fact as grounding a claim its own quote substantially restates in different words, not
# only one it quotes as a contiguous substring - scoped exactly as _cited_literal already was, to
# the finding's own and the reviewed unit's own citations; (b) new _closing_anchor_carries lets
# _carried_by_units/_reviewed_unit_fact_ids locate the content unit whose own sentence a quote
# carries even when the renderer's own chrome is prefixed onto it in the quote - a closing anchor
# symmetric to quote_located's existing opening one, scoped to exactly these two functions;
# quote_located's own general contract (absence_defect, review_checks) is untouched by either.
# "12" (shared-defect investigation, two-repository corroboration: Aspose.Words-FOSS-for-.NET F05,
# 2026-09-17 10:32 UTC, and Aspose.Email-FOSS-for-Python F08, 2026-09-23 09:59 UTC):
# _cited_paraphrase's overlap ratio was computed against a cited fact's WHOLE value, so a quote
# that faithfully and completely restates only one bullet of a multi-bullet inherited_unit:*.list
# fact (an ordinary prose scope/limitations list - RC-06 only splits a "member reference list" into
# per-bullet facts, never this shape) had its ratio diluted by the OTHER bullets' unrelated tokens
# and fell under _PARAPHRASE_MIN_OVERLAP even though the paraphrase itself was complete and true -
# a reviewer false positive with no repair lever (repair cannot alter text that is already
# faithful, so the finding re-raised identically every round). New _value_segments splits such a
# fact's value into its own top-level bullets; _cited_paraphrase now also scores each bullet on its
# own (its own token count as the denominator), alongside the whole value as before - neither
# _PARAPHRASE_MIN_TOKENS nor _PARAPHRASE_MIN_OVERLAP changed, and a quote that does not
# substantially restate any single bullet (or the whole fact) still fails exactly as before.
# G4-W17 (docs/investigations/12-supervisor-and-production-reassessment.md section 5.6): the
# accept path's fold logic now branches on whether a third independent read was supplied - a
# genuine meaning change to what `review_document` can end up accepting for a repository named in
# MAJORITY_VOTE_REPOSITORIES (a finding there now needs 2 of 3 reads to agree, not one confirming
# read), even though every other repository's own fold stack is byte-for-byte unchanged. Bumped so
# a sealed candidate re-checks against the new code rather than reading as still current.
REVIEWER_LOGIC_VERSION = "13"
# The manifest's stage vocabulary mapped to the state the repair loop reopens
# (docs/STATE_MACHINE.md section 7.5); a stage with no entry cannot be acted on.
CAUSAL_STATES: dict[str, str] = {
    "S2": "EXTRACTING",
    "S3": "INVESTIGATING",
    "S4": "RECONCILING",
    "S5": "PLANNING",
    "S6": "COMPOSING",
    "S7": "COMPOSING",
    "S8": "COMPOSING",
}
_STRUCTURAL_SECTIONS = frozenset({"structure", "document"})
# Em dash, en dash, figure dash, non-breaking hyphen, no-break space, and curly quotes: the
# typography a model or a maintainer may spell differently from the candidate.
_TYPOGRAPHY = str.maketrans(
    {
        "\u2014": "-",
        "\u2013": "-",
        "\u2012": "-",
        "\u2011": "-",
        "\u00a0": " ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)


_MARKUP = (
    re.compile(r"(?m)^\s*```[^\n]*$"),  # fence lines, with their language
    # The same fence flattened into one quote: a reviewer copies "Verify the install:" and
    # the block after it as a single line, and the language tag then survives where the
    # candidate's own line dropped it, so the quote could never locate (measured 2026-09-05,
    # the review failed closed twice on it).
    re.compile(r"```[A-Za-z0-9_+-]*"),
    re.compile(r"<[^>\n]+>"),  # HTML tags such as details and summary
    re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+"),  # list markers
    re.compile(r"(?m)^\s*#{1,6}\s+"),  # heading marks
    re.compile(r"\*\*|__|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)"),  # emphasis
    # A Mermaid node label's quotation marks are the diagram's syntax, not the reader's text:
    # a reviewer reads c2["Export to interchange formats"] and quotes it without them, and the
    # quote then located nothing and failed the review twice (measured 2026-09-05, section 27.2).
    re.compile(r'(?<=\[)"|"(?=\])'),
)


# A link reads as its text: the candidate carries [text](url) and a reviewer quotes the words
# it clicked, so the destination is ours, like a code span's backticks. The third asymmetry of
# this kind measured on 2026-09-05, after the Mermaid label and the fence.
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _normalized(text: str) -> str:
    """Text as a reader compares it: no code spans or Markdown syntax, plain dashes and
    quotes, single spaces. A reviewer quotes what it reads; the syntax around it is ours."""
    plain = _LINK.sub(r"\1", text.translate(_TYPOGRAPHY))
    for pattern in _MARKUP:  # fence lines first, while their backticks still mark them
        plain = pattern.sub("", plain)
    return re.sub(r"\s+", " ", plain.replace("`", "")).strip().lower()


def _normalized_with_targets(text: str) -> str:
    """Like ``_normalized``, but a Markdown link's own target survives beside its visible text
    (G4-W17 arrival item 71, PROPOSAL AF, lane C): ``_normalized`` drops a link down to
    ``\\1`` (the label alone), so a cited ``link_target`` fact's own value - a URL or filename,
    never the label - can never literal-match a quote through that path at all, whatever the
    quote actually contains. Measured on Slides-Java: a finding quoted the candidate's own
    rendered line ``[Code of Conduct](CODE_OF_CONDUCT.md)`` verbatim, embedding the link's raw
    Markdown syntax and its target in the same string the reviewer copied, and cited exactly the
    SUPPORTED ``link_target`` fact whose value is that target - but ``_normalized`` had already
    thrown the target away before ``_cited_literal`` ever compared anything, so a quote that
    plainly carries the fact's own value could not be recognised as carrying it. This is not a
    general widening of what a quote may spell: ``_LINK``'s substitution is simply skipped here,
    so the brackets and parenthesis stay exactly as authored, and only an exact substring match on
    the fact's own (already-normalized) value can ever succeed against it.
    """
    plain = text.translate(_TYPOGRAPHY)
    for pattern in _MARKUP:
        plain = pattern.sub("", plain)
    return re.sub(r"\s+", " ", plain.replace("`", "")).strip().lower()


_ANCHOR_LENGTH = 80
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|\u2026)\s*")


def quote_located(quote: str, candidate_readme: str) -> bool:
    """A quote locates candidate text when its normalized form occurs in the candidate; a quote
    that exists nowhere in any spelling is invented and rejects the finding.

    A long quote anchors by its opening: a reviewer that copies a whole block and drifts in
    its tail still points at real text, so the first eighty normalized characters locate it.
    """
    wanted = _normalized(quote)
    haystack = _normalized(candidate_readme)
    if not wanted or wanted in haystack:
        return True
    # An ellipsis abbreviates: every fragment around it is exact candidate text. It abbreviates
    # at either end too - a reviewer quoting one short line writes "subgraph StartingPoints[...]"
    # and trails off - so a single fragment counts, provided the quote really carried an ellipsis
    # (measured 2026-09-06: both of Aspose.Cells' rejected findings were quotes of exactly this
    # shape, each 43 characters or fewer, so the eighty-character anchor below could not reach
    # them and the review ended the transaction on a JobError instead of a verdict).
    fragments = [part.strip() for part in _ELLIPSIS.split(wanted) if part.strip()]
    if _ELLIPSIS.search(wanted) and fragments and all(part in haystack for part in fragments):
        return True
    return len(wanted) > _ANCHOR_LENGTH and wanted[:_ANCHOR_LENGTH] in haystack


def review_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    original_readme: str,
    candidate_readme: str,
    plan: dict[str, Any],
    dispositions: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """The packet for the one review call; inherited units travel as the original README."""
    kinds = [kind for kind in FACT_KINDS if kind != "inherited_unit"]
    return {
        "repository": entry.repository,
        "candidate_readme": candidate_readme,
        "original_readme": original_readme,
        "facts": bounded_records(facts, kinds, ("SUPPORTED", "CONTRADICTED", "UNRESOLVED")),
        "plan": plan,
        "dispositions": dispositions,
        "validation": {
            "checks": [
                {
                    "id": check.get("id"),
                    "verdict": check.get("verdict"),
                    "causal_stage": check.get("causal_stage"),
                    "details": check.get("details", []),
                }
                for check in validation.get("checks", [])
            ],
            "advisory": validation.get("advisory", []),
        },
    }


def blocking(finding: dict[str, Any]) -> bool:
    """A finding blocks when it names a candidate section and a stage the loop can reopen."""
    return bool(finding.get("section_id")) and finding.get("causal_stage") in CAUSAL_STATES


# A required row admits zero advisories left standing, so on those rows one reader's taste can
# hold a candidate unsealed indefinitely. The owner's two-reader rule (2026-09-06 00:15, §31;
# RESEARCH_AND_GUIDELINES.md §27.8) makes such a finding block only when a second independent
# read under a different seed raises an equivalent one. Only the presentation criterion is a
# prose judgment: factuality, scope and absence findings are refuted deterministically above.
REQUIRED_SECTIONS = frozenset(section.id for section in SEMANTIC_SHELL if section.required)
PROSE_JUDGMENT = "presentation"
SECOND_READER_SEED = 2
THIRD_READER_SEED = 3

# docs/investigations/12-supervisor-and-production-reassessment.md section 5.6: a repository whose
# own draw history already shows two or more distinct S10/review findings across independent,
# non-repeating draws needs its ACCEPT path to survive a 2-of-3 majority vote among three
# independent reads, not just one confirming read - a single noisy extra reader on top of an
# already-fragile repository can sink an otherwise-clean draw, the exact class-I provider sampling
# nondeterminism docs/investigations/05-production-autonomy.md (class I) already documents as
# provider-inherent and unfixable in this codebase. These three are the corroborated instances on
# record (docs/DECISION_LOG.md, the 2026-09-24 "list-bundling hypothesis is REFUTED" correction
# entry and the histories it cites): aspose-words-foss/Aspose.Words-FOSS-for-.NET (F05/F06, then
# F03, then F04/F05 across three independent draws), aspose-slides-foss/Aspose.Slides-FOSS-for-Java
# (docs/RESEARCH_LANE_C.md G4-W12-RERUN7 through RERUN13, a different finding nearly every rerun),
# and aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (docs/RESEARCH_LANE_B.md RERUN2 through RERUN11).
# Every repository not named here keeps the single-confirming-read path exactly as it was (PHASE1/
# F6, the 2026-09-06 guard) - this is a bounded, reversible escalation of that existing mechanism,
# never a new one and never a change to what a review criterion itself judges: edit this set, never
# the fold logic, to add or remove a repository once its own history warrants it.
MAJORITY_VOTE_REPOSITORIES = frozenset(
    {
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    }
)


def prose_judgment(finding: Mapping[str, Any]) -> bool:
    """A finding on a required row that no deterministic check expresses (§26)."""
    return (
        finding.get("criterion") == PROSE_JUDGMENT
        and str(finding.get("section_id")) in REQUIRED_SECTIONS
    )


def finding_class(finding: Mapping[str, Any]) -> str:
    """What two readers must agree on: the same section, stage and criterion."""
    return defect_fingerprint(
        "review",
        finding.get("section_id"),
        finding.get("causal_stage"),
        str(finding.get("criterion", "")),
    )


def second_reader(manifest: LoadedManifest) -> LoadedManifest:
    """The same reviewer prompt, read again under a different seed.

    The prompt file and its hash are untouched, so the candidate's dependencies are unchanged and
    this is corroboration, never a retry. On a rejection the second read can only take a finding
    out of the blocking set; on an accept (PHASE1/F6) its findings pass the same fold stack as
    the first read's and a survivor blocks, so an accept is corroborated, never assumed.
    """
    sampling = manifest.manifest.sampling
    seed = SECOND_READER_SEED if sampling.seed is None else sampling.seed + SECOND_READER_SEED
    return replace(
        manifest,
        manifest=manifest.manifest.model_copy(
            update={"sampling": sampling.model_copy(update={"seed": seed})}
        ),
    )


def third_reader(manifest: LoadedManifest) -> LoadedManifest:
    """The same reviewer prompt, read a third time under a third, distinct seed.

    Used only for a repository in ``MAJORITY_VOTE_REPOSITORIES`` (section 5.6): the prompt file
    and its hash are untouched here too, so this stays corroboration under the existing mechanism,
    never a third retry with different criteria. Mirrors ``second_reader`` exactly, offset by
    ``THIRD_READER_SEED`` instead of ``SECOND_READER_SEED`` so the three reads are three distinct
    seeds, never the same request repeated.
    """
    sampling = manifest.manifest.sampling
    seed = THIRD_READER_SEED if sampling.seed is None else sampling.seed + THIRD_READER_SEED
    return replace(
        manifest,
        manifest=manifest.manifest.model_copy(
            update={"sampling": sampling.model_copy(update={"seed": seed})}
        ),
    )


REVIEWER_SCOPE_DEFECT = "reviewer-scope defect"


def factuality_defect(
    finding: Mapping[str, Any],
    quote: str,
    by_id: Mapping[str, Fact],
    unit_fact_ids: Collection[str] = (),
) -> str | None:
    """Why a factuality finding is the reviewer's own defect, or None when it may stand.

    A factuality finding cites a product fact that contradicts the quote or should have
    supported it; inherited README units are maintainer text, not evidence. A quote containing
    the literal value of a cited SUPPORTED fact is supported by definition.

    G4-W17 arrival item 39: a finding naming no product fact_ids used to stand unconditionally
    here, on the reasoning that "no fact supports this claim" cites nothing to check by
    construction - true when the finding names its omission through ``absent`` instead (that
    shape is ``absence_defect``'s to judge, called before this in ``scope_defect``, never this
    function's). But a factuality finding naming NEITHER cites nothing for any deterministic
    check anywhere in ``scope_defect`` to measure, so it passed every one of them by construction
    and could block a candidate on an assertion nothing could ever disprove or fix. Measured
    2026-09-07, Aspose.Cells for Java, finding F07: its own quote WAS the sentence it called
    missing, empty ``fact_ids``, empty ``absent`` - byte-identical on re-ask, repair recorded it
    repaired and it re-raised identically, because there was never anything about it a repair
    could change. The prompt already asks for one or the other
    (prompts/independent_review.yaml lines 141-157); this enforces it deterministically rather
    than trusting compliance.

    ``unit_fact_ids`` (G4-W17 arrival item 83, LANE-B-W14R3-F1): the reviewed content unit's own
    ``fact_ids`` - not the finding's - as ``_reviewed_unit_fact_ids`` locates them. This widens
    only the literal-value refutation below, never the "cites at least one product fact" gate
    above: item 39's rule about what makes a factuality finding grounded enough to judge at all is
    untouched, and a bare inherited_unit citation still does not, by itself, grant that grounding.
    Once a finding clears that gate, though, its unit's own ``inherited_unit`` citations are a
    real refutation source the finding itself may simply not have repeated - measured on 3D-TS,
    Aspose.3D-FOSS-for-TypeScript's own upstream README already states, almost verbatim, the exact
    limitation a surviving finding called unverified. The same ``unit_fact_ids`` also narrows the
    CONTRADICTED-stands gate below (G4-W17 arrival item 91, PDFPY-01): a CONTRADICTED fact
    genuinely among the reviewed unit's own citations is real grounding, but one the finding's own
    self-report merely lists beside a real, unit-grounded, SUPPORTED-backed claim is not.
    """
    cited = [by_id[i] for i in finding.get("fact_ids", []) if i in by_id]
    if not cited:
        if not _claimed_absent(finding):
            return (
                "a factuality finding names neither a product fact_id to contradict the quote "
                "nor an absent claim of missing text: nothing in evidence supports judging it"
            )
        return None  # named as an absence instead; absence_defect already judges that shape
    product = [fact for fact in cited if fact.kind != "inherited_unit"]
    if not product:
        return (
            "a factuality finding cites at least one product fact that contradicts the quote "
            "or should have supported it; inherited README units are maintainer text, not "
            "evidence"
        )
    # G4-W17 arrival item 91 (PDFPY-01): scoped to unit_fact_ids, the same source the
    # SUPPORTED-literal path two lines below already reads (item 83) - a CONTRADICTED fact the
    # reviewed unit genuinely cited as its own evidence is real grounding for the finding, but a
    # CONTRADICTED fact the finding's own self-report merely lists as unrelated context is not:
    # measured on PDF-Python (F05), a verbatim, unit-grounded, SUPPORTED-backed claim was kept
    # permanently blocking because its finding also named a CONTRADICTED fact the reviewed unit
    # never cited at all. Every prior case this branch closed (items 39/63/83) had its CONTRADICTED
    # fact among the unit's own citations, so this scoping changes nothing for them.
    if any(fact.polarity == "CONTRADICTED" and fact.id in unit_fact_ids for fact in product):
        return None
    reviewed = [by_id[i] for i in unit_fact_ids if i in by_id and by_id[i].kind == "inherited_unit"]
    grounded = _cited_grounding([*product, *reviewed], quote)
    if grounded is not None:
        fact, literal = grounded
        if literal:
            return (
                f"the quote contains the literal value of SUPPORTED fact {fact.id} "
                f"({fact.value!r}); literal fact text is supported"
            )
        return (
            f"the quote substantially restates SUPPORTED fact {fact.id} ({fact.value!r}) in "
            "different words; a faithful paraphrase of cited evidence is supported exactly as "
            "a literal quote is (G4-W17 item 116)"
        )
    return None


# A fact value shorter than this is too little text to say a quote carries it on purpose.
_LITERAL_VALUE_LENGTH = 3


def _cited_literal(product: Sequence[Fact], quote: str) -> Fact | None:
    """The first cited SUPPORTED product fact whose literal value the quote contains, or None.

    Shared by ``factuality_defect`` and ``cited_fact_defect``: the prompt's own rule - "a quote
    that contains the literal value of a SUPPORTED fact you cite is supported by definition"
    (prompts/independent_review.yaml) - measured the same way whichever criterion files it.

    Checked against both ``_normalized``'s reader-facing form and ``_normalized_with_targets``'s
    link-preserving form (G4-W17 arrival item 71, PROPOSAL AF): most cited facts are prose a
    reader would visibly read, but a ``link_target`` fact's own value is the destination behind a
    link, not its label - the one shape ``_normalized`` alone can never match, since it exists
    expressly to discard that destination. A quote that embeds the raw Markdown (as a reviewer's
    own copy of the candidate's rendered line can) still carries it either way.
    """
    wanted = _normalized(quote)
    wanted_with_targets = _normalized_with_targets(quote)
    for fact in product:
        if fact.polarity != "SUPPORTED":
            continue
        value = _normalized(fact.value)
        if len(value) < _LITERAL_VALUE_LENGTH:
            continue
        if value in wanted or value in wanted_with_targets:
            return fact
    return None


# A restated fact must contribute at least this many of its own distinctive tokens before a
# quote's overlap with it counts as a paraphrase - a fact with fewer is too little text to say a
# quote restates it on purpose, the same reasoning _LITERAL_VALUE_LENGTH already applies to a
# literal substring.
_PARAPHRASE_MIN_TOKENS = 4
# The share of the fact's own distinctive tokens that must also occur in the quote. Set from the
# one measured case (3D-TS, 14 of 18 tokens shared, ratio 0.78) with headroom - one composition is
# a measurement, not a gate.
_PARAPHRASE_MIN_OVERLAP = 0.6
_TOKEN = re.compile(r"[a-z0-9]{3,}")
# Ordinary connective words common enough that sharing them proves nothing about whether a quote
# restates a fact's own distinctive content - excluded so the overlap ratio measures shared
# subject matter, not shared grammar.
_PARAPHRASE_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "this",
        "that",
        "with",
        "from",
        "into",
        "than",
        "then",
        "when",
        "where",
        "while",
        "via",
        "per",
        "own",
        "one",
        "two",
        "three",
        "first",
        "second",
        "third",
        "new",
        "any",
        "all",
        "its",
        "was",
        "were",
        "use",
        "using",
        "used",
        "shown",
        "above",
        "until",
        "only",
        "also",
        "may",
        "can",
        "will",
        "has",
        "have",
        "had",
        "does",
        "did",
        "such",
        "each",
        "both",
        "other",
        "another",
        "same",
        "these",
        "those",
        "here",
        "there",
        "currently",
    }
)


def _content_tokens(normalized_text: str) -> frozenset[str]:
    """The distinctive (non-stopword, three-plus character) words in an already-normalized text."""
    return frozenset(
        token for token in _TOKEN.findall(normalized_text) if token not in _PARAPHRASE_STOPWORDS
    )


# A top-level Markdown bullet marker opening a line: "- ", "* ", "+ ", or "1. "/"1) " followed by
# real content. Deliberately simple (line-anchored, no nested-indent handling) - it only needs to
# separate an inherited_unit:*.list fact's own top-level bullets from each other, the same
# granularity evidence/facts/inherited.py's RC-06 split already reasons about for a *different*
# purpose (which bullets qualify for their own fact record, not how one bundled fact's value reads).
_BULLET_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+\S")


def _value_segments(value: str) -> tuple[str, ...]:
    """``value``'s own top-level Markdown bullets, when it has at least two; ``()`` otherwise.

    G4-W17 arrival items F05 (Words-.NET) and F08 (Email-Python), 2026-09-17/2026-09-23: a
    multi-bullet ``inherited_unit:*.list`` fact bundles several distinct upstream sentences into
    one fact record (evidence/facts/inherited.py only splits a "member reference list" whose every
    bullet opens on a known class/enum identifier, RC-06 - an ordinary prose limitations/scope list
    stays one fact). A composed quote that faithfully and completely paraphrases just ONE of those
    bullets still has its ``_cited_paraphrase`` overlap ratio computed against every OTHER bullet's
    tokens too, diluting a genuine, complete restatement below ``_PARAPHRASE_MIN_OVERLAP`` for no
    reason connected to whether the quote is actually supported. Measured twice, independently:
    Words-.NET's ``inherited_unit:067.list`` (three bullets; a quote restating only the first
    scored 16/41 = 0.39) and Email-Python's ``inherited_unit:066.list`` (four bullets; a quote
    restating only the first scored 7/56 = 0.125) - both well below 0.6 despite each quote being a
    complete, faithful restatement of the one bullet it actually paraphrases.

    A continuation line (wrapped prose, or a nested sub-bullet) is folded into the bullet above it
    rather than starting its own segment, since it is part of that bullet's own content, not a
    sibling claim.
    """
    lines = value.splitlines()
    segments: list[str] = []
    current: list[str] = []
    for line in lines:
        if _BULLET_MARKER.match(line):
            if current:
                segments.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        segments.append("\n".join(current))
    return tuple(segments) if len(segments) >= 2 else ()


def _cited_paraphrase(product: Sequence[Fact], quote: str) -> Fact | None:
    """The first cited SUPPORTED product fact the quote substantially restates in different
    words, or None.

    G4-W17 arrival item 116 (LANE-B-W14R7-F1): ``_cited_literal`` only recognizes a quote that
    contains a cited fact's own value as a contiguous substring, so a unit that faithfully
    paraphrases - never quotes verbatim - a SUPPORTED fact its own ``fact_ids`` correctly cite
    gets no refutation from either fold path, even though the right evidence is genuinely among
    its citations. Measured on 3D-TS: ``content_units.json``'s ``scope_limitations`` unit ("Binary
    glTF export using binaryMode: true currently fails and throws a RangeError for any non-empty
    mesh, so only JSON/ASCII glTF export (the default, binaryMode: false) is supported.")
    faithfully restates ``inherited_unit:046.paragraph``'s own upstream sentence ("Binary glTF
    (.glb, binaryMode = true) currently throws a RangeError for any non-empty mesh ... Use the
    JSON/ASCII form (binaryMode = false, the default) shown above until that is fixed
    upstream.") - the same fact, correctly cited, sharing every distinctive technical term, but
    not one contiguous run of text.

    Scoped identically to ``_cited_literal``: only the facts already passed in (the finding's own
    and the reviewed unit's own citations, per each caller's own scoping), never the whole fact set
    (item 45's collision). To avoid folding a coincidental overlap of ordinary words rather than a
    genuine restatement, a fact only grounds a quote when a strong majority of the fact's OWN
    distinctive tokens also occur in the quote, and there are enough of them that the overlap could
    not be chance (``_PARAPHRASE_MIN_TOKENS``/``_PARAPHRASE_MIN_OVERLAP``).

    G4-W17 arrival items F05/F08 (this version): a fact's whole value is always tried first (a
    quote may genuinely restate an entire multi-bullet fact at once), but when the value is a
    multi-bullet list (``_value_segments``), each bullet is ALSO tried on its own - both the
    denominator (the bullet's own distinctive-token count) and the overlap are scoped to that one
    bullet, so a complete, faithful paraphrase of a single bullet is no longer diluted by its
    siblings' unrelated tokens. A quote that only weakly echoes one bullet, or borrows a few
    ordinary words from several without substantially restating any one of them, still fails every
    candidate exactly as before - this widens which TEXT the ratio is measured against, never the
    ratio or token-count thresholds themselves.
    """
    wanted = _content_tokens(_normalized(quote))
    wanted_with_targets = _content_tokens(_normalized_with_targets(quote))
    for fact in product:
        if fact.polarity != "SUPPORTED":
            continue
        for candidate_text in (fact.value, *_value_segments(fact.value)):
            value_tokens = _content_tokens(_normalized(candidate_text))
            if len(value_tokens) < _PARAPHRASE_MIN_TOKENS:
                continue
            overlap = max(len(value_tokens & wanted), len(value_tokens & wanted_with_targets))
            if overlap / len(value_tokens) >= _PARAPHRASE_MIN_OVERLAP:
                return fact
    return None


def _cited_grounding(product: Sequence[Fact], quote: str) -> tuple[Fact, bool] | None:
    """The first cited SUPPORTED fact that grounds ``quote``, and whether that grounding is a
    literal quote (``True``) or a faithful paraphrase (``False``, G4-W17 item 116) - or ``None``.

    A thin dispatcher over ``_cited_literal`` and ``_cited_paraphrase`` so both of
    ``factuality_defect``'s and ``cited_fact_defect``'s call sites share one place that tries the
    stronger (literal) claim first and only falls back to the paraphrase test when no fact's
    literal value is present - keeping each caller's own reason text honest about which is true.
    """
    literal = _cited_literal(product, quote)
    if literal is not None:
        return literal, True
    paraphrase = _cited_paraphrase(product, quote)
    if paraphrase is not None:
        return paraphrase, False
    return None


def cited_fact_defect(
    finding: Mapping[str, Any],
    quote: str,
    by_id: Mapping[str, Fact],
    unit_fact_ids: Collection[str] = (),
) -> str | None:
    """Why a presentation finding whose own citation verifies its quote is the reviewer's defect.

    G4-W17 arrival item 63 (lane B LANE-B-R3-F2, Aspose.PDF for C++). The literal-value rule
    above ran only for a finding labelled ``factuality``, so the identical finding labelled
    ``presentation`` had no refutation at all: F08 quoted ``using Aspose_PDF_FOSS version
    1.0.0.``, cited ``package:version`` (SUPPORTED, value ``1.0.0``) as its own evidence, called
    the sentence unverified, and ``targeted_repair`` obeyed - a true, fact-backed detail left a
    public candidate because a finding said the opposite of its own citation. The same
    repository's 2026-09-06 draw had already lost ``1.0.0`` twice the same way (its
    ``repairs.json`` attempts F07 and F10, each citing ``package:version``), so this is a class,
    measured three times, not one draw.

    Scoped to the facts the finding itself cites, never the whole fact set: a verbatim scan of
    every SUPPORTED value would refold quotes by coincidence (``dependency:none``'s value is
    ``none``; a ``format``'s is a bare extension) - the collision item 45 was written to stop.
    A cited CONTRADICTED fact leaves the finding standing, exactly as in ``factuality_defect``:
    the reviewer then names a fact that disproves the quote, which is a real finding.

    ``unit_fact_ids`` (G4-W17 arrival item 83) widens the literal-value check once a finding
    already clears the gate below with a product fact of its own, and for the identical reason
    ``factuality_defect`` above is widened: the reviewed unit's own ``inherited_unit`` citations,
    not only the finding's self-reported ones. Still bounded to one unit's own small citation
    set, never the whole fact set item 45's own collision measured.

    G4-W17 arrival items 79/96 (lane E E8, Cells-Python; lane E bcpy LANE-E-07, BarCode-Python):
    a finding naming NEITHER a fact_id NOR an absent claim is exactly item 39's own "nothing
    checkable" shape, one criterion over - ``factuality_defect`` above already folds that shape
    unconditionally, but doing the identical thing here unconditionally would refold a genuine,
    corroborated presentation judgment that legitimately cites nothing
    (``test_a_prose_judgment_on_a_required_row_blocks_only_when_a_second_reader_agrees`` - the
    owner's own two-reader rule exists precisely because a real style complaint need not cite
    evidence). The safe, narrower version below: only when the REVIEWED UNIT's own *product*-fact
    citations (never the whole fact set, and never merely its inherited_unit ones - those alone
    proved nothing above either) literally back the quote is such a finding refuted. Measured on
    BarCode-Python (F06): a false "this is missing" claim filed under presentation with neither
    field populated, whose own quote was the reviewed unit's own fact-bound text verbatim - a
    real style complaint has no reviewed-unit product fact to coincide with its quote by
    definition, since it is not making a factual claim at all.
    """
    cited = [by_id[i] for i in finding.get("fact_ids", []) if i in by_id]
    product = [fact for fact in cited if fact.kind != "inherited_unit"]
    if any(fact.polarity == "CONTRADICTED" for fact in product):
        return None
    reviewed_cited = [by_id[i] for i in unit_fact_ids if i in by_id]
    reviewed = [fact for fact in reviewed_cited if fact.kind == "inherited_unit"]
    if not product:
        if finding.get("fact_ids") or _claimed_absent(finding):
            return None  # cites only an inherited_unit, or claims an absence: not this shape
        reviewed_product = [fact for fact in reviewed_cited if fact.kind != "inherited_unit"]
        grounded = _cited_grounding(reviewed_product, quote)
        if grounded is None:
            return None
        fact, literal = grounded
        contains = "contains the literal value of" if literal else "substantially restates"
        return (
            "the finding names neither a fact_id nor an absent claim, and the quote "
            f"{contains} SUPPORTED fact {fact.id} ({fact.value!r}) which the "
            "reviewed unit cites as its own evidence: nothing in evidence supports judging it, "
            "and what evidence exists contradicts it"
        )
    grounded = _cited_grounding([*product, *reviewed], quote)
    if grounded is None:
        return None
    fact, literal = grounded
    if fact.id in finding.get("fact_ids", []):
        source = "which the finding itself cites as its evidence"
    else:
        source = "which the reviewed unit cites as its own evidence"  # item 83
    contains = "contains the literal value of" if literal else "substantially restates"
    supported = "literal fact text" if literal else "a faithful paraphrase (G4-W17 item 116)"
    return (
        f"the quote {contains} SUPPORTED fact {fact.id} "
        f"({fact.value!r}), {source}; {supported} is supported whatever criterion the "
        "finding files itself under"
    )


_ABSENCE_REPORTED = 3

_SECTION_HEADINGS: dict[str, str] = {
    section.id: section.heading for section in SEMANTIC_SHELL if section.heading
}


def _claimed_absent(finding: Mapping[str, Any]) -> list[str]:
    """The non-blank strings a finding says the candidate does not contain."""
    return [text for text in (str(entry).strip() for entry in finding.get("absent", [])) if text]


def _section_slice(section_id: str, candidate_readme: str) -> str:
    """The candidate's own text for one top-level section, from its heading to the next one.

    External audit, 2026-09-07: `absence_defect` searched the whole document, so a finding about
    the Installation section was wrongly refuted by a string that only existed 760 lines later in
    Development and Testing - text present somewhere is not text present where the finding says
    it is missing. Falls back to the whole document (never to nothing) when the section's heading
    cannot be located - a missing boundary is a reason to search everywhere, not nowhere, so this
    can only narrow a search, never cause one to miss real candidate text.

    `review_checks`'s own `quote_located` call (PA-02, REC-005, 2026-09-09) scopes to this same
    slice, for the identical reason: a finding's quote is checked against its own named section,
    not the whole document.
    """
    heading = _SECTION_HEADINGS.get(section_id)
    if not heading:
        return candidate_readme
    marker = f"## {heading}"
    start = candidate_readme.find(marker)
    if start < 0:
        return candidate_readme
    body_start = start + len(marker)
    next_heading = re.search(r"\n## ", candidate_readme[body_start:])
    end = body_start + next_heading.start() if next_heading else len(candidate_readme)
    return candidate_readme[start:end]


def absence_defect(
    finding: Mapping[str, Any], candidate_readme: str, evidence: str = ""
) -> str | None:
    """Why a finding that alleges an absence is the reviewer's own defect, or None.

    An omission claim is checkable, so the reviewer states what it claims is missing as strings
    in ``absent`` rather than asserting it in prose; the code looks each one up under the same
    spelling rules that locate a quote. A string the candidate's own named section contains
    disproves that one claim by the candidate's own bytes - scoped to that section, not the whole
    document (see ``_section_slice``), because a finding names one section and a coincidental
    match somewhere else in a large README does not disprove a real gap in that section. A string
    that occurs nowhere in the evidence the candidate draws from - the original README and the
    fact values - is text nobody wrote, so there is nothing to restore.

    A finding may bundle several claims. Every one must be accounted for - refuted by the
    candidate's own bytes, or proven invented - before the whole finding dismisses; one true,
    unrefuted, non-invented claim leaves a real remainder, and the finding stands (external
    review, 2026-09-07: a three-claim finding was previously dismissed in full because two of its
    three claims were refuted, silently discarding the one that was genuinely true - a candidate's
    own gap survived only because it was bundled beside two false ones). Nothing here reads the
    finding's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC8; docs/README_CONTRACT.md
    section 6).

    A finding that stands on a remainder is narrowed, never dismissed (G4-W17 arrival item 64,
    lane B LANE-B-R3-F3): ``review_document`` records the refuted and invented claims beside the
    ones that remain (``absence_partition``), so the repair round is handed the remainder alone.
    Measured 2026-09-11 on Aspose.PDF for C++: a repair had just appended the sentence BC-08
    demanded, the next review's F10 quoted that very sentence as evidence the section omitted it,
    three of its five ``absent`` claims sat in its own section slice and two were genuinely
    missing - this rule correctly let it stand, but its text, quote and repair all named the
    three settled claims, so the repair was handed work already done and the equivalent failure
    re-raised.
    """
    claims = _claimed_absent(finding)
    if not claims:
        return None
    present, invented, remaining = absence_partition(finding, candidate_readme, evidence)
    if remaining:
        return None  # at least one claim is neither refuted nor invented: a real remainder
    parts = []
    if present:
        parts.append(
            f"the finding claims the candidate does not contain {_named(present)}, "
            "which the candidate contains"
        )
    if invented:
        parts.append(
            f"the finding asks for {_named(invented)}, which occurs in no fact value and "
            "nowhere in the original README: there is nothing to restore"
        )
    return "; ".join(parts)


def absence_partition(
    finding: Mapping[str, Any], candidate_readme: str, evidence: str = ""
) -> tuple[list[str], list[str], list[str]]:
    """A finding's ``absent`` claims sorted three ways: ``present`` (the candidate's own named
    section contains them), ``invented`` (nowhere in the evidence, so there is nothing to
    restore), and ``remaining`` (neither - the claims that still stand, in the order claimed).

    ``absence_defect`` dismisses a finding whose remainder is empty; ``review_document`` records
    the other two lists on a standing finding so ``repair/targeted.py`` hands the repair only the
    remainder (G4-W17 arrival item 64). Without ``evidence`` nothing is judged invented, exactly
    as before.
    """
    claims = _claimed_absent(finding)
    section_id = str(finding.get("section_id") or "")
    haystack = _section_slice(section_id, candidate_readme)
    present = sorted({claim for claim in claims if quote_located(claim, haystack)})
    invented = (
        sorted(
            {
                claim
                for claim in claims
                if claim not in present and not quote_located(claim, evidence)
            }
        )
        if evidence
        else []
    )
    settled = {*present, *invented}
    remaining = [claim for claim in dict.fromkeys(claims) if claim not in settled]
    return present, invented, remaining


def _record_absence_partition(
    record: dict[str, Any], finding: Mapping[str, Any], candidate_readme: str, evidence: str
) -> None:
    """On a finding that stands, record which absence claims are already settled and which
    remain - only when both exist, so a whole finding and a dismissed one carry nothing new."""
    if not _claimed_absent(finding):
        return
    present, invented, remaining = absence_partition(finding, candidate_readme, evidence)
    if not remaining or not (present or invented):
        return
    if present:
        record["absent_refuted"] = present
    if invented:
        record["absent_invented"] = invented
    record["absent_remaining"] = remaining


def _named(claims: Sequence[str]) -> str:
    """The first few claims, quoted, so the reason names what it judged without listing all."""
    return ", ".join(repr(claim) for claim in claims[:_ABSENCE_REPORTED])


def claim_evidence(original_readme: str, facts: FactsDocument | None) -> str:
    """Everything a candidate could have drawn its text from: the original README and the facts.

    An absence claim is measured against this, never against the candidate alone: asking for text
    the original README and the facts both lack is asking for something nobody wrote.
    """
    values = [fact.value for fact in facts.facts] if facts is not None else []
    return "\n".join([original_readme, *values])


# The two criteria a reviewer uses for text it is reading, and the whole reach of item 37's
# label independence: a finding under either one is a judgment about wording the renderer may own.
_RENDERER_OWNED_CRITERIA = frozenset({"presentation", "factuality"})


def renderer_owned_defect(
    finding: Mapping[str, Any],
    by_id: Mapping[str, Fact],
    unit_texts: Sequence[str] | None = None,
) -> str | None:
    """Why a finding against content no unit wrote is the reviewer's own defect, or None.

    A deterministic section renders from facts under the contract's own checks (BC-02, BC-05,
    BC-07): its wording and its choice of command are the renderer's, so no stage the loop can
    reopen would change them. A factual error there is a finding against the fact, not against
    any unit's prose.

    The document's own shape is the same case one level up. Which sections exist, in what order,
    and under which headings is the semantic shell's, evaluated from the facts before any job
    runs, so a finding against ``structure`` or ``document`` - or one quoting a heading the
    renderer emits - names nothing a revision could write. Measured 2026-09-06: Aspose.Slides was
    held unsealed by a finding asking for a "Links" section the shell does not define, and
    Aspose.Cells by one calling the ``#### Detailed Member Reference`` block, which contract row
    14 requires, too verbose; the repair loop answered both with *section structure is
    deterministic; its blocks change only when facts change*.

    A collapsible section's own wrapper is the same case again, one level lower: the ``<details>``
    /``<summary>`` chrome around Additional Examples and the API surface is the renderer's, not a
    unit's, even though the section itself is mixed-owned and so is never wholesale exempted above
    (G4-W17 arrival item 33). Measured 2026-09-06 on Aspose.Slides for Java: a finding quoted
    ``ADDITIONAL_EXAMPLES_SUMMARY`` exactly, calling the collapsible structure "unnecessary UI";
    routed to authoring's ``additional_examples`` unit, the re-ask rewrote the unit's own prose and
    left the renderer's wrapper - and the finding - unchanged.

    A finding may also name real, verified content rather than renderer chrome and still be no
    unit's to revise: BC-04 already verifies that every identifier a unit's prose names is a real
    fact value, and loop-prompt.md rule 8 requires the complete verified surface inside the
    collapsed API reference by design. Measured 2026-09-06 on Aspose.Cells for Go: a finding quoted
    ``ExportToCSV``, a SUPPORTED ``public_symbol`` fact BC-04 had already passed, and asked for it
    to be deleted as "unsupported" because the upstream README lacked it - the reviewer judging
    against the original README as the standard of support rather than against the facts, the same
    shape as the heading and chrome cases, one level lower still (lane D PROPOSAL P16).

    A heading, a collapsible summary, and a deterministic section's body are text the renderer
    wrote from the facts: no unit wrote them and no stage the loop can reopen would rewrite them,
    so whether the finding calls that a presentation defect or a factual one changes nothing about
    who could act on it. Those three exemptions therefore read the quote and the section, never the
    finding's self-reported label - the independence ``absence_defect`` beside them already has
    (G4-W17 arrival item 37). Measured 2026-09-06 on Aspose.Cells for Java, where two of the three
    findings blocking BC-10 were exactly this shape and both were labelled ``factuality``, so
    neither reached the rule: one quoted the LLM-owned opening section's own prose while naming the
    deterministic ``identity`` row, the other quoted the renderer's own rendering of a SUPPORTED
    ``dependency:none`` fact.

    Three things the label still decides, because each rests on the criterion rather than on who
    wrote the text. ``structure``/``document`` is where a reviewer files a finding that belongs to
    no section at all, so a false claim about anything in the document arrives under it. BC-04
    verifies that an identifier a unit names is a real fact value, never that the sentence around
    it is accurate - "``ExportToCSV`` writes JSON, not CSV" is a real defect in a unit's own prose
    that merely happens to name a verified symbol. And a criterion outside the two a reviewer uses
    for text it is reading - a completeness or scope finding - reports content missing from a
    deterministic section, which is a claim about the fact set that section renders from and one
    ``S2`` can reopen.

    The BC-04 exemption's factuality gate was standing in for a question the criterion cannot
    answer: *where the quoted text lives* (G4-W17 arrival item 62, lane C PROPOSAL Z). The
    ``ExportToCSV`` case quotes a sentence a content unit wrote and can rewrite. Measured
    2026-09-11 on Aspose.Cells for Java, F05 - ``factuality``, ``api_reference`` - quoted two
    verified enums' own table rows, each a SUPPORTED ``public_symbol`` fact's name and docstring
    rendered verbatim by the renderer: ``content_units.json`` held 25 units, the section's two
    carried neither row, the repair re-asked the intro unit and got the same 157 bytes back,
    the finding re-raised, and every refutation here returned None - ``_quoted_verified_fact``
    itself already resolved the quote, and only the label stood between it and the answer. So
    when the caller supplies ``unit_texts`` (the content units' own prose) and none of them
    carries the quote, a factuality finding reaches the same exemption: text no unit wrote is
    the renderer's, whatever the finding calls it. A quote any unit carries, even partly, keeps
    its route to that unit; with no units supplied the gate stays presentation-only, because
    "no unit carries it" is a measurement, never a default.
    """
    criterion = finding.get("criterion")
    if criterion not in _RENDERER_OWNED_CRITERIA:
        return None
    presentation = criterion == "presentation"
    section = finding.get("section_id")
    if presentation and section in _STRUCTURAL_SECTIONS:
        return (
            "the semantic shell owns which sections exist, in what order, and under which "
            "headings; it is evaluated from the facts, so no stage the loop can reopen would "
            "add or remove one"
        )
    if _quoted_heading(finding):
        return (
            f"the quote is the heading {_quoted_heading(finding)!r}, which the renderer emits "
            "because the contract's shell requires it; no unit wrote it and none can change it"
        )
    if _quoted_chrome(finding):
        return (
            f"the quote is {_quoted_chrome(finding)!r}, the renderer's own collapsible-section "
            "chrome (its summary text or its <details>/</details> wrapper); no unit wrote it and "
            "none can change it"
        )
    unwritten = unit_texts is not None and not _carried_by_units(
        str(finding.get("quote", "")), unit_texts
    )
    verified = _quoted_verified_fact(finding, by_id) if presentation or unwritten else None
    if verified is not None and presentation:
        return (
            f"the quote names {verified.id}, a SUPPORTED fact BC-04 already verifies; the "
            "candidate's own fact set is the standard of support, not the upstream README, and "
            "loop-prompt.md rule 8 requires the complete verified surface - absence from the "
            "original is never itself a presentation defect for content BC-04 already verified"
        )
    if verified is not None:
        return (
            f"the quote names {verified.id}, a SUPPORTED fact BC-04 already verifies, and no "
            "content unit carries the quoted text: it is the renderer's own rendering of that "
            "verified fact, which no unit wrote and no stage the loop can reopen would rewrite"
        )
    if section not in _DETERMINISTIC_SECTIONS:
        return None
    return (
        f"section {section} renders from facts under the contract's own "
        "checks; its presentation is the renderer's, and a factual error there is a "
        "factuality finding"
    )


def _quoted_heading(finding: Mapping[str, Any]) -> str | None:
    """The heading a finding quotes and nothing else, or None."""
    quote = str(finding.get("quote", "")).strip()
    if not quote.startswith("#"):
        return None
    text = quote.lstrip("#").strip()
    return text if text in _RENDERED_HEADINGS else None


# The renderer's own collapsible-details summary text (README_CONTRACT.md rows 12 and 14, the
# "collapsible" visibility): unlike a heading it carries no leading '#', so it needs its own exact
# match rather than _quoted_heading's. The bare `<details>`/`</details>` tag lines the same call
# sites emit beside the `<summary>` text (renderer.py:519, 545, 815, 820 - item 101) are the same
# renderer-owned chrome: no content unit writes them and no repair can remove them.
_RENDERED_CHROME = frozenset(
    {ADDITIONAL_EXAMPLES_SUMMARY, API_SURFACE_SUMMARY, "<details>", "</details>"}
)


def _quoted_chrome(finding: Mapping[str, Any]) -> str | None:
    """The renderer's own collapsible chrome (summary text or bare tag) a finding quotes and
    nothing else, or None."""
    quote = str(finding.get("quote", "")).strip()
    return quote if quote in _RENDERED_CHROME else None


_VERIFIED_NAME_LENGTH = 3
_BACKTICK_SPAN = re.compile(r"`([^`\n]*)`")


def _references_symbol(quote: str, fact: Fact) -> bool:
    """Whether the finding's own raw quote actually references ``fact``, not merely contains its
    bare suffix as an ordinary English word.

    G4-W17 arrival item 45: the previous check matched a SUPPORTED ``public_symbol``'s bare
    suffix case-insensitively against the *normalized* quote, which strips backticks entirely, so
    whether the occurrence was even in a code span was never checked. Measured live on the sealed
    Aspose.Cells-FOSS-for-Rust candidate (2,084 symbols): common short identifiers that are also
    ordinary English or legitimate Rust idioms - ``new``, ``from``, ``fmt``, ``cells`` - matched
    two of that seal's seven review findings by coincidental lowercase word overlap alone,
    folding them out before BC-10 could weigh them. A real reference is backticked, spelled in
    its own qualified dotted (or ``::``) form, or spelled in its own exact non-lowercase case
    (``ExportToCSV``, not ``exporttocsv``) - none of which an ordinary English sentence does by
    coincidence, unlike a bare lowercase word.
    """
    suffix = fact.value.rsplit(".", 1)[-1].rsplit("::", 1)[-1]
    bare = re.compile(rf"\b{re.escape(suffix)}\b", re.IGNORECASE)
    for span in _BACKTICK_SPAN.finditer(quote):
        if bare.search(span.group(1)):
            return True
    if re.search(rf"\b{re.escape(fact.value)}\b", quote):
        return True
    return not suffix.islower() and bool(re.search(rf"\b{re.escape(suffix)}\b", quote))


def _quoted_verified_fact(finding: Mapping[str, Any], by_id: Mapping[str, Fact]) -> Fact | None:
    """A SUPPORTED public_symbol fact the quote actually references (see ``_references_symbol``).

    Scoped to ``public_symbol`` alone, never every fact kind: a dotted suffix is only meaningful
    for a qualified identifier value (``package.Type.Method``) - the same rsplit an ``example``'s
    multi-line code or a ``format``'s bare extension would match by coincidence, not by naming it
    (measured while landing this: an unrestricted version matched ``format:output.glb`` against
    unrelated prose that merely mentioned ``.glb`` files). A reviewer, like a unit's own prose,
    names the member by its bare name (the convention item 22's ``symbol_names`` already
    established), not the fully qualified value. Still ``public_symbol`` alone after G4-W17
    arrival item 63: a quote carrying another kind's literal value is ``cited_fact_defect``'s,
    which reads only the facts the finding itself cites, so the coincidence above stays closed.
    """
    quote = str(finding.get("quote", ""))
    if not quote.strip():
        return None
    for fact in by_id.values():
        if fact.kind != "public_symbol" or fact.polarity != "SUPPORTED":
            continue
        suffix = fact.value.rsplit(".", 1)[-1].rsplit("::", 1)[-1]
        if len(suffix) >= _VERIFIED_NAME_LENGTH and _references_symbol(quote, fact):
            return fact
    return None


# An ellipsis fragment shorter than this is too little text to place inside a unit on purpose.
_CARRIED_FRAGMENT_LENGTH = 12


def _closing_anchor_carries(quote: str, text: str) -> bool:
    """Whether one content unit's own ``text`` is carried at the CLOSE of ``quote`` - the mirror
    image of ``quote_located``'s own opening-anchor tolerance for a long quote's tail drift
    (G4-W17 arrival item 118, PROPOSAL AG).

    ``quote_located`` anchors a long quote by its first eighty normalized characters, so a
    reviewer that copies a whole block and drifts in its tail still locates real candidate text.
    The mirror-image drift is the renderer's own chrome (a rendered bullet's label and link)
    PREFIXED onto a unit's own trailing sentence in the reviewer's quote: both the whole-quote
    containment check and the opening-anchor check anchor to the quote's OPENING characters -
    exactly the renderer's prefix, absent from the unit's own text - so neither ever locates it.
    Measured on Slides-Java: the unit for ``link_target:023`` writes only "The Code of Conduct
    outlines expected behavior for participants contributing to or engaging with the
    Aspose.Slides FOSS for Java community." - the renderer composes the visible bullet as its own
    ``"- **[Code of Conduct](CODE_OF_CONDUCT.md)** - "`` prefix followed by that exact sentence,
    and the reviewer's finding quotes the whole rendered line.

    Scoped to exactly the two functions that call this, never ``quote_located`` itself, which
    ``absence_defect`` and ``review_checks`` also depend on for an unrelated question (a short
    absence claim, where this same tolerance would risk a false positive). The unit's own text
    must exceed ``_ANCHOR_LENGTH`` characters normalized - the same length gate ``quote_located``
    applies to its own opening anchor - so a short, generic sentence cannot close-anchor by
    coincidence.
    """
    haystack = _normalized(text)
    return len(haystack) > _ANCHOR_LENGTH and _normalized(quote).endswith(haystack)


def _carried_by_units(quote: str, unit_texts: Sequence[str]) -> bool:
    """Whether any content unit's own prose carries the quote, or any exact fragment of it.

    Conservative by construction (G4-W17 arrival item 62): the whole quote is looked up under
    ``quote_located``'s spelling rules against every unit's text joined, and so is each exact
    fragment around an ellipsis - a quote that is even partly a unit's sentence (the unit's
    prose beside a rendered row it disputes) counts as carried, so the finding keeps its route
    to that unit. Only a quote no unit wrote any part of is uncarried.
    """
    haystack = "\n".join(unit_texts)
    if not _normalized(quote) or not _normalized(haystack):
        return False
    if quote_located(quote, haystack):
        return True
    fragments = [part.strip() for part in _ELLIPSIS.split(quote) if part.strip()]
    if len(fragments) > 1 and any(
        len(_normalized(part)) >= _CARRIED_FRAGMENT_LENGTH and quote_located(part, haystack)
        for part in fragments
    ):
        return True
    # G4-W17 item 118: a closing anchor against each unit's own text individually - the combined
    # haystack above joins every unit, which would let one unit's tail satisfy another unit's own
    # chrome-prefixed quote by coincidence; the closing anchor is one unit's own text alone.
    return any(_closing_anchor_carries(quote, text) for text in unit_texts)


def unit_texts(units: Mapping[str, Any] | None) -> list[str] | None:
    """Every content unit's own prose from a ``content_units.json``-shaped document.

    ``None`` in, ``None`` out - and the two answers differ downstream: ``None`` means the units
    are unknown and ``renderer_owned_defect``'s BC-04 exemption stays presentation-only; a list,
    even an empty one, is a measurement of what the units carry.
    """
    if units is None:
        return None
    return [
        str(unit.get("text", "")) for unit in units.get("units", []) if isinstance(unit, Mapping)
    ]


def _reviewed_unit_fact_ids(quote: str, units: Mapping[str, Any] | None) -> tuple[str, ...]:
    """The fact IDs of the one content unit whose own text carries the quote, or an exact
    ellipsis fragment of it - the same quote-location rule ``_carried_by_units`` already applies.

    G4-W17 arrival item 83 (lane B LANE-B-W14R3-F1, 3D-TS): every refutation guard in
    ``scope_defect`` reads a finding's own self-reported ``fact_ids`` and nothing else, so a
    finding that omits a fact its own reviewed unit actually cited - here, an ``inherited_unit``
    fact stating the exact claim in the upstream repository's own words - can never be refuted by
    it, even though the unit is fully entitled to cite it as evidence. A finding that never looks
    at what the candidate actually cited cannot be a defect in the candidate.
    """
    if not units or not _normalized(quote):
        return ()
    for unit in units.get("units", []):
        if not isinstance(unit, Mapping):
            continue
        text = str(unit.get("text", ""))
        if quote_located(quote, text) or _closing_anchor_carries(quote, text):
            return tuple(str(i) for i in unit.get("fact_ids", []))
        fragments = [part.strip() for part in _ELLIPSIS.split(quote) if part.strip()]
        if len(fragments) > 1 and any(
            len(_normalized(part)) >= _CARRIED_FRAGMENT_LENGTH and quote_located(part, text)
            for part in fragments
        ):
            return tuple(str(i) for i in unit.get("fact_ids", []))
    return ()


# At a Glance is mixed-owned only in what the plan selects: the renderer owns every node, edge,
# and label (README_CONTRACT.md section 2.1), so its presentation is likewise the renderer's.
_DETERMINISTIC_SECTIONS = frozenset(
    {*(section.id for section in SEMANTIC_SHELL if section.owner == "D"), "at_a_glance"}
)
# Every heading in the document is the renderer's: the shell's own, and the subsections the
# contract names inside Dependencies and the API Reference (README_CONTRACT.md rows 9 and 14).
_RENDERED_HEADINGS = frozenset(
    {*(section.heading for section in SEMANTIC_SHELL if section.heading), *SUBSECTION_HEADINGS}
)


def review_checks(
    output: dict[str, Any], candidate_readme: str, facts: FactsDocument | None = None
) -> list[str]:
    """Why the review may not be used, beyond schema and binding; empty when it holds.

    A finding whose quote locates nothing is still unusable and is dropped - the check itself is
    unchanged - but it is folded out of the reply rather than failing the whole review, the same
    shape ``plan_checks`` folds a trimmable plan breach (``d707693``) and ``dispositions.normalize``
    folds an impossible placement. The reviewer's job puts the *upstream* README beside the
    candidate, so quoting the original where it meant the candidate is a natural slip, and it cost
    every other finding in the same reply: measured 2026-09-06 on
    ``aspose-pdf-foss/Aspose-PDF-FOSS-for-Go``, where one such quote discarded 7 usable findings of
    8 and left BC-10 unjudged (G4-W17 arrival item 28).

    Nothing is folded when no finding survives it: a reply whose every quote is invented points at
    no candidate text at all, so there is no trustworthy remainder to keep and the review is
    re-asked exactly as before. The folded finding still counts towards the repeated-ID rule, so
    dropping it never lets a duplicate through.
    """
    errors: list[str] = []
    known = set(section_ids()) | _STRUCTURAL_SECTIONS
    seen: set[str] = set()
    findings = output.get("findings", [])
    kept: list[Any] = []
    unlocated: list[str] = []
    for finding in findings:
        label = str(finding.get("id", "?"))
        if label in seen:
            errors.append(f"finding {label}: its ID repeats an earlier finding")
        seen.add(label)
        section = str(finding.get("section_id", ""))
        if section not in known:
            errors.append(
                f"finding {label}: section_id must be a shell section or 'structure'; "
                f"got {section!r}"
            )
        quote = str(finding.get("quote", ""))
        # PA-02, REC-005: scoped to the finding's own named section, the same fix AUD-002 gave
        # absence_defect - text present somewhere else in a large README does not locate a quote
        # a finding says belongs here (external audit, 2026-09-07).
        if not quote_located(quote, _section_slice(section, candidate_readme)):
            unlocated.append(
                f"finding {label}: quote is not the candidate's text: {quote.strip()[:60]!r}"
            )
            continue
        kept.append(finding)
    if unlocated and not kept:
        errors.extend(unlocated)
    elif unlocated:
        output["findings"] = kept
    return errors


def rendered_defect(finding: Mapping[str, Any], rendered: Sequence[str]) -> str | None:
    """Why a finding against a sentence the renderer wrote is the reviewer's own defect.

    A deterministic section's presentation is the renderer's (``renderer_owned_defect``); so is a
    sentence the renderer writes inside a section an LLM otherwise owns - a count from the facts,
    the suite size, the release line. The unit beside it did not write it and no revision of that
    unit can change it, so no stage the loop can reopen would act on the finding.
    """
    quote = _normalized(str(finding.get("quote", "")))
    if not quote or not rendered:
        return None
    # A reviewer may quote two of these sentences at once - the renderer prints them adjacent -
    # so the quote is measured against them joined in the order the renderer wrote them.
    if quote not in _normalized(" ".join(rendered)):
        return None
    return (
        "the quoted sentence is the renderer's own, written from the facts beside a unit that "
        "did not write it; no revision of that unit can change it"
    )


# A quote shorter than this can coincide with unrelated text; the reviewer's own anchor rule
# uses the same order of magnitude.
_EXCLUDED_QUOTE_LENGTH = 40


def excluded_evidence_defect(finding: Mapping[str, Any], by_id: Mapping[str, Fact]) -> str | None:
    """Why a finding quoting or citing evidence the facts exclude is the reviewer's own defect.

    A finding may quote candidate text or text it says should be there. When the quote is the
    value of a fact that is not ``SUPPORTED``, the second reading is the only one left - and
    rendering it would break the contract's own check 3, which admits an example only if it
    executed at this revision. There is nothing to restore and no stage would restore it.

    Measured 2026-09-06: Aspose.Slides was held unsealed by *the candidate omits the Markdown
    export example entirely*, quoting `example:015` - `CONTRADICTED`, one of fifteen examples,
    the only one the plan could not carry. This is ``absence_defect``'s "nothing to restore"
    rule, read from the quote the reviewer did fill rather than the ``absent`` list it left empty.

    An omission claim can name the same excluded evidence without quoting it at all: measured
    2026-09-06 on Aspose.3D for .NET, whose finding quoted the section's ordinary lead-in and
    named `example:003` (`CONTRADICTED`) in `fact_ids` as why the omitted example belongs -
    `absence_defect` cannot see this because the omitted heading was genuinely written by the
    maintainer, so it is not invented text, and `absence_defect` only asks whether a claim exists
    somewhere in evidence, never whether the fact backing the *claim* is itself excluded. A
    factuality finding citing a contradicted fact to disprove existing text is not this: it names
    no `absent` strings, since that is the schema's own rule for a finding that alleges no
    absence.
    """
    quote = _normalized(str(finding.get("quote", "")))
    if len(quote) >= _EXCLUDED_QUOTE_LENGTH:
        for fact in by_id.values():
            if fact.polarity != "SUPPORTED" and quote in _normalized(fact.value):
                return (
                    f"the quote is {fact.id}, which is {fact.polarity}: the contract admits it "
                    "only once the evidence supports it, so no stage the loop can reopen would "
                    "write it"
                )
    if _claimed_absent(finding):
        for fact_id in finding.get("fact_ids", []):
            cited = by_id.get(fact_id)
            if cited is not None and cited.polarity != "SUPPORTED":
                return (
                    f"the omission it names is backed by {cited.id}, which is {cited.polarity}: "
                    "the contract admits it only once the evidence supports it, so no stage the "
                    "loop can reopen would write it"
                )
    return None


def excluded_disposition_defect(
    finding: Mapping[str, Any],
    by_id: Mapping[str, Fact],
    dispositions: Mapping[str, Any] | None,
) -> str | None:
    """Why a finding demanding restoration of an inherited_unit reconciliation deliberately
    marked ``OMIT_UNSUPPORTED`` is the reviewer's own defect - the disposition-aware sibling of
    ``excluded_evidence_defect``, which reads only a fact's polarity.

    G4-W17 arrival item 86 (lane E E17, Words-Python's S10 blocker). Polarity answers "did the
    maintainer write this" (``SUPPORTED`` - a real, verbatim ``inherited_unit`` fact); disposition
    answers "may this be composed" (S4 reconciliation's own, separate judgment -
    ``OMIT_UNSUPPORTED`` when nothing beyond the maintainer's own prose backs its per-item claims).

    Measured on Words-Python: an original README table
    (``inherited_unit:038.table``, ``SUPPORTED``) that S4
    correctly refused to compose as unverified; the finding's own ``absent`` strings are literal
    substrings of that table's text, so ``absence_defect`` calls them "not invented" (they are, in
    evidence) and stands the finding, and ``excluded_evidence_defect`` never triggers either (the
    fact's polarity is ``SUPPORTED``). No stage the repair loop can reopen would restore content S4
    itself decided is unverified - a repair attempt proved this structural, not a missed retry:
    with the excluded fact uncitable, its only move was a bare filename list, and the identical
    finding re-raised.

    ``dispositions`` is ``None`` until the one call site that has it in scope
    (``repair/rounds.py``, which already threads it into ``renderer_sentences`` three lines before
    its ``review_document`` call) also threads it here - this function then never fires, matching
    today's behaviour exactly; wiring that one line is this item's own remaining step.
    """
    if not dispositions:
        return None
    excluded_ids = {
        str(entry.get("unit_id"))
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") == "OMIT_UNSUPPORTED"
    }
    if not excluded_ids:
        return None
    excluded_facts = [fact for fact in by_id.values() if fact.id in excluded_ids]
    quote = _normalized(str(finding.get("quote", "")))
    if len(quote) >= _EXCLUDED_QUOTE_LENGTH:
        for fact in excluded_facts:
            if quote in _normalized(fact.value):
                return (
                    f"the quote is {fact.id}'s own text, which reconciliation excluded "
                    "(OMIT_UNSUPPORTED, not composed): the contract admits it only once "
                    "verified, so no stage the loop can reopen would restore it"
                )
    for claim in _claimed_absent(finding):
        claimed = _normalized(claim)
        if len(claimed) < _EXCLUDED_QUOTE_LENGTH:
            continue
        for fact in excluded_facts:
            if claimed in _normalized(fact.value):
                return (
                    f"the omission it names is {fact.id}'s own text, which reconciliation "
                    "excluded (OMIT_UNSUPPORTED, not composed): the contract admits it only "
                    "once verified, so no stage the loop can reopen would restore it"
                )
    return None


def scope_defect(
    finding: Mapping[str, Any],
    candidate_readme: str,
    by_id: Mapping[str, Fact],
    evidence: str = "",
    rendered: Sequence[str] = (),
    unit_texts: Sequence[str] | None = None,
    units: Mapping[str, Any] | None = None,
    dispositions: Mapping[str, Any] | None = None,
) -> str | None:
    """Why a finding is the reviewer's own defect, or None when it may stand.

    Judged from the reviewer's raw reply every time the document is built, so the answer is a
    pure function of the finding, the facts, and the rule - never of an earlier run's verdict and
    never of a mark left in the finding's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2
    RC8). A reviewer-scope defect is recorded, never blocks (docs/README_CONTRACT.md section 6),
    and never earns a second ask.

    An absence the candidate disproves is judged first, whatever the criterion: a finding that
    names text the candidate contains is refuted by the document itself, and no reading of its
    criterion changes that. So is a quote the facts exclude by polarity, or by S4's own
    ``OMIT_UNSUPPORTED`` disposition (item 86 - polarity and disposition answer different
    questions, and a finding can be ungroundable by either), for the same reason from the other
    side - the document could not have carried it. Content the renderer owns rather than a unit
    is judged the same way, before the criterion is read at all: whether the finding calls the
    renderer's own text a presentation defect or a factual one, no stage the loop can reopen
    would rewrite it (G4-W17 arrival item 37). Only the criterion-specific refutations - a
    factuality claim measured against the facts it cites, a presentation claim contradicted by
    the finding's own citation (item 63) - come after the switch. ``unit_texts``, when the
    caller has the content units, lets the renderer-owned rule tell a rendered row no unit wrote
    from a unit's own sentence (item 62). ``units``, the same content units document unreduced,
    lets the criterion-specific refutations also read the one reviewed unit's own fact_ids, not
    only the finding's self-reported ones (item 83). ``dispositions``, the round's own
    ``dispositions.json``, is ``None`` until its one call site threads it through (item 86); the
    new disposition-aware exclusion is then inert, exactly as today.
    """
    absence = absence_defect(finding, candidate_readme, evidence)
    if absence is not None:
        return absence
    excluded = excluded_evidence_defect(finding, by_id)
    if excluded is not None:
        return excluded
    excluded_by_disposition = excluded_disposition_defect(finding, by_id, dispositions)
    if excluded_by_disposition is not None:
        return excluded_by_disposition
    written = rendered_defect(finding, rendered)
    if written is not None:
        return written
    owned = renderer_owned_defect(finding, by_id, unit_texts)
    if owned is not None:
        return owned
    quote = str(finding.get("quote", ""))
    unit_fact_ids = _reviewed_unit_fact_ids(quote, units)
    if finding.get("criterion") == "factuality":
        return factuality_defect(finding, quote, by_id, unit_fact_ids)
    if finding.get("criterion") == PROSE_JUDGMENT:
        return cited_fact_defect(finding, quote, by_id, unit_fact_ids)
    return None


def review_document(
    output: dict[str, Any],
    reviewer: LoadedManifest,
    authoring: LoadedManifest,
    readme_digest: str,
    candidate_readme: str = "",
    facts: FactsDocument | None = None,
    original_readme: str = "",
    rendered: Sequence[str] = (),
    second: Mapping[str, Any] | None = None,
    third: Mapping[str, Any] | None = None,
    units: Mapping[str, Any] | None = None,
    dispositions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """review.json: the verdict, blocking findings with their causal state, advisory findings,
    what a repair must preserve, and the two prompt identities.

    A finding that is the reviewer's own defect is recorded advisory with the reason as a field,
    the stage the reviewer named left intact: the record says why it does not block, and nothing
    downstream has to read prose to find out (section 27.5 D5).

    ``units`` is the round's own ``content_units.json`` document when the caller has it: the
    fold stack then knows which quoted text a unit wrote and which the renderer did (G4-W17
    arrival item 62); without it, that one rule keeps its narrower presentation-only reach.

    ``dispositions`` is the round's own ``dispositions.json`` document when the caller has it
    (G4-W17 arrival item 86): the fold stack then also knows which inherited_unit reconciliation
    itself, correctly, marked ``OMIT_UNSUPPORTED`` - unverified content no repair could restore
    anyway - so a finding demanding it back is the reviewer's own defect rather than a doomed
    block. Without it, that one rule stays inert, exactly as before this parameter existed.

    ``second`` is a second independent read of the same candidate under a different seed. When it
    is given (not ``None``), a prose judgment on a required row blocks only if that read raised a
    finding of the same class; otherwise it is recorded ``single_reader_advisory`` and does not
    block (the owner's two-reader rule, section 27.8).

    The accept path is symmetric (PHASE1/F6): when the first read leaves no blocking finding -
    a returned ACCEPT, or a rejection whose every finding folded to advisory, the single-read
    class 8 of the 9 pre-sprint seals belong to - the second read's own findings pass the same
    fold stack, marked ``reader: 2``. A survivor blocks with its causal state and the verdict
    becomes the second read's returned one, so the disagreement repairs through the normal
    rounds; two reads that leave nothing blocking are two independent ACCEPTs. A prose judgment
    only the second reader raised is one reader's judgment, exactly as in the other direction.
    ``second_reader.read`` records the count of completed reads (1 or 2) so check 10 can require
    a corroborated accept from the record alone.

    ``second`` must be ``None`` - never ``{}`` - when no usable second reading exists (the job
    failed, timed out, or was never attempted). A caller passing ``second={}`` for "no reading"
    was TB-04's own bug: an empty dict is not ``None``, so this function read it as a *completed*
    reading that raised zero findings, corroborating nothing and silently demoting a real blocking
    finding to advisory (REJECT_PRESENTATION -> ACCEPT, external review D4, 2026-09-08). Losing
    verification must never increase assurance; the caller (``repair/rounds.py``) is the one place
    that enforces this today, by simply never constructing ``second={}``.

    ``third`` is a third independent read, given only for a repository in
    ``MAJORITY_VOTE_REPOSITORIES`` (section 5.6) - a bounded, reversible escalation of the same
    mechanism above, never a replacement for it. When ``third`` is ``None`` (every other
    repository), behavior is unchanged from the single-confirming-read rule above, byte for byte.
    When both ``second`` and ``third`` are given and the first read left nothing blocking, a
    finding needs to be raised by BOTH extra reads (2 of the 3 total reads, the first having
    raised nothing) before it blocks - a single dissenting extra reader is recorded
    ``single_reader_advisory``, tolerated as noise rather than left to sink an otherwise-clean
    draw, exactly the class-I sampling variance this escalation exists to out-vote. ``third`` must
    equally be ``None`` - never ``{}`` - for no usable third reading, for the identical reason
    ``second={}`` is forbidden above; the caller enforces this the same way.
    """
    findings: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    corroborated = (
        {finding_class(f) for f in second.get("findings", []) if blocking(dict(f))}
        if second is not None
        else set()
    )
    if third is not None:
        # Widens corroboration from "second alone" to "either extra read": for the first read's
        # own prose-judgment demotion below, first + either one of the two extra reads already
        # is 2 of 3 - the majority the escalation asks for (section 5.6).
        corroborated |= {finding_class(f) for f in third.get("findings", []) if blocking(dict(f))}
    by_id = {fact.id: fact for fact in facts.facts} if facts is not None else {}
    evidence = claim_evidence(original_readme, facts) if original_readme else ""
    texts = unit_texts(units)
    for finding in output.get("findings", []):
        record = dict(finding)
        reason = (
            scope_defect(
                finding, candidate_readme, by_id, evidence, rendered, texts, units, dispositions
            )
            if facts is not None
            else None
        )
        if reason is not None:
            record["reviewer_scope_defect"] = reason
        else:
            _record_absence_partition(record, finding, candidate_readme, evidence)
        alone = (
            second is not None
            and prose_judgment(finding)
            and finding_class(finding) not in corroborated
        )
        if reason is None and blocking(finding) and not alone:
            record["causal_state"] = CAUSAL_STATES[str(finding["causal_stage"])]
            findings.append(record)
        else:
            record["causal_state"] = None
            if alone and reason is None:
                record["single_reader_advisory"] = True
            advisory.append(record)
    returned = str(output.get("verdict"))
    # A rejection rests on its blocking findings; one whose findings are all advisory has
    # nothing the loop can act on and, by section 6 of the contract, does not block.
    verdict = returned if findings or returned == ACCEPT else ACCEPT
    if third is not None and second is not None and not findings:
        # 2-of-3 majority vote (section 5.6): the first read left nothing blocking, so an extra
        # read's finding needs the OTHER extra read to raise the same class too before it blocks
        # - first-raised-nothing plus one extra reader is only 1 of 3, exactly the single noisy
        # reader this escalation exists to tolerate rather than let sink an otherwise-clean draw.
        # Never applied unless the caller (repair/rounds.py) actually asked for a third read, which
        # it only does for a repository named in MAJORITY_VOTE_REPOSITORIES - every other
        # repository takes the elif branch below, byte for byte as before this escalation existed.
        second_raised = {finding_class(f) for f in second.get("findings", []) if blocking(dict(f))}
        third_raised = {finding_class(f) for f in third.get("findings", []) if blocking(dict(f))}
        majority = second_raised & third_raised
        survivors: list[dict[str, Any]] = []
        for reader_num, reader_output in ((2, second), (3, third)):
            for finding in reader_output.get("findings", []):
                record = {**dict(finding), "reader": reader_num}
                reason = (
                    scope_defect(
                        finding,
                        candidate_readme,
                        by_id,
                        evidence,
                        rendered,
                        texts,
                        units,
                        dispositions,
                    )
                    if facts is not None
                    else None
                )
                if reason is not None:
                    record["reviewer_scope_defect"] = reason
                else:
                    _record_absence_partition(record, finding, candidate_readme, evidence)
                in_majority = reason is None and finding_class(finding) in majority
                if in_majority and blocking(finding):
                    record["causal_state"] = CAUSAL_STATES[str(finding["causal_stage"])]
                    survivors.append(record)
                else:
                    record["causal_state"] = None
                    if reason is None and blocking(finding):
                        record["single_reader_advisory"] = True
                    advisory.append(record)
        if survivors:
            findings.extend(survivors)
            # Mirrors the elif branch's own verdict rule below: whichever extra read's returned
            # verdict is not ACCEPT stands - a majority here means at least one of the two extra
            # reads independently disagreed with ACCEPT.
            second_returned = str(second.get("verdict"))
            third_returned = str(third.get("verdict"))
            verdict = next((v for v in (second_returned, third_returned) if v != ACCEPT), verdict)
    elif second is not None and not findings:
        # The accept path, symmetric (PHASE1/F6): no first-read finding blocks, so the second
        # read corroborates the accept - its findings go through the identical fold stack.
        first_raised = {finding_class(f) for f in output.get("findings", []) if blocking(f)}
        survivors = []
        for finding in second.get("findings", []):
            record = {**dict(finding), "reader": 2}
            reason = (
                scope_defect(
                    finding,
                    candidate_readme,
                    by_id,
                    evidence,
                    rendered,
                    texts,
                    units,
                    dispositions,
                )
                if facts is not None
                else None
            )
            if reason is not None:
                record["reviewer_scope_defect"] = reason
            else:
                _record_absence_partition(record, finding, candidate_readme, evidence)
            alone = prose_judgment(finding) and finding_class(finding) not in first_raised
            if reason is None and blocking(finding) and not alone:
                record["causal_state"] = CAUSAL_STATES[str(finding["causal_stage"])]
                survivors.append(record)
            else:
                record["causal_state"] = None
                if alone and reason is None:
                    record["single_reader_advisory"] = True
                advisory.append(record)
        if survivors:
            findings.extend(survivors)
            # The first read's own verdict rule, mirrored: a disagreement's verdict is the
            # second read's returned one (an ACCEPT that somehow carries findings keeps
            # ACCEPT, exactly as a first-read ACCEPT with findings does today).
            second_returned = str(second.get("verdict"))
            verdict = second_returned if second_returned != ACCEPT else verdict
    return {
        "schema_version": 1,
        "readme_sha256": readme_digest,
        "verdict": verdict,
        "verdict_as_returned": returned,
        "findings": findings,
        "advisory": advisory,
        "second_reader": {
            # The count of completed reads: check 10 accepts only at >= 2 (PHASE1/F6). A failed
            # second (or third) read never reaches here - the caller passes None for it (TB-04),
            # and losing verification must never increase assurance. 3 only for the escalated
            # 2-of-3 majority-vote path (section 5.6); >= 2 either way satisfies check 10 exactly
            # as before this escalation existed.
            "read": 3 if third is not None else (2 if second is not None else 1),
            "corroborated": sorted(corroborated),
        },
        "preserve": list(output.get("preserve", [])),
        "reviewer": {
            "job": reviewer.manifest.prompt_id,
            "stage": reviewer.manifest.stage,
            "prompt_sha256": reviewer.sha256,
            "model_route": reviewer.manifest.model_route,
        },
        "authoring": {
            "job": authoring.manifest.prompt_id,
            "stage": authoring.manifest.stage,
            "prompt_sha256": authoring.sha256,
        },
        "identity_separate": reviewer.manifest.prompt_id != authoring.manifest.prompt_id
        and reviewer.sha256 != authoring.sha256,
    }


def summarize_review(document: dict[str, Any]) -> str:
    return (
        f"verdict {document.get('verdict')}, findings {len(document.get('findings', []))}, "
        f"advisory {len(document.get('advisory', []))}, "
        f"preserve {len(document.get('preserve', []))}"
    )


def write_review(document: dict[str, Any], path: Path) -> str:
    """Write review.json as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
