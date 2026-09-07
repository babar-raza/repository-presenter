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
from collections.abc import Mapping, Sequence
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
    this is corroboration, never a retry: the second read can only take a finding out of the
    blocking set, never put one in.
    """
    sampling = manifest.manifest.sampling
    seed = SECOND_READER_SEED if sampling.seed is None else sampling.seed + SECOND_READER_SEED
    return replace(
        manifest,
        manifest=manifest.manifest.model_copy(
            update={"sampling": sampling.model_copy(update={"seed": seed})}
        ),
    )


REVIEWER_SCOPE_DEFECT = "reviewer-scope defect"


def factuality_defect(
    finding: Mapping[str, Any], quote: str, by_id: Mapping[str, Fact]
) -> str | None:
    """Why a factuality finding is the reviewer's own defect, or None when it may stand.

    A factuality finding cites a product fact that contradicts the quote or should have
    supported it; inherited README units are maintainer text, not evidence. A quote containing
    the literal value of a cited SUPPORTED fact is supported by definition.
    """
    cited = [by_id[i] for i in finding.get("fact_ids", []) if i in by_id]
    if not cited:
        return None  # "no fact supports this claim" cites nothing, by definition
    product = [fact for fact in cited if fact.kind != "inherited_unit"]
    if not product:
        return (
            "a factuality finding cites at least one product fact that contradicts the quote "
            "or should have supported it; inherited README units are maintainer text, not "
            "evidence"
        )
    if any(fact.polarity == "CONTRADICTED" for fact in product):
        return None
    wanted = _normalized(quote)
    for fact in product:
        value = _normalized(fact.value)
        if fact.polarity == "SUPPORTED" and len(value) >= 3 and value in wanted:
            return (
                f"the quote contains the literal value of SUPPORTED fact {fact.id} "
                f"({fact.value!r}); literal fact text is supported"
            )
    return None


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
    disproves the finding by the candidate's own bytes - scoped to that section, not the whole
    document (see ``_section_slice``), because a finding names one section and a coincidental
    match somewhere else in a large README does not disprove a real gap in that section. A string
    that occurs nowhere in the evidence the candidate draws from - the original README and the
    fact values - is text nobody wrote, so there is nothing to restore. Either way a deterministic
    check contradicts the finding (docs/README_CONTRACT.md section 6), and nothing here reads the
    finding's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC8).
    """
    claims = _claimed_absent(finding)
    section_id = str(finding.get("section_id") or "")
    haystack = _section_slice(section_id, candidate_readme)
    present = sorted({claim for claim in claims if quote_located(claim, haystack)})
    if present:
        return (
            f"the finding claims the candidate does not contain {_named(present)}, "
            "which the candidate contains"
        )
    if not evidence:
        return None
    invented = sorted({claim for claim in claims if not quote_located(claim, evidence)})
    if invented:
        return (
            f"the finding asks for {_named(invented)}, which occurs in no fact value and "
            "nowhere in the original README: there is nothing to restore"
        )
    return None


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


def renderer_owned_defect(finding: Mapping[str, Any], by_id: Mapping[str, Fact]) -> str | None:
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
            f"the quote is {_quoted_chrome(finding)!r}, the renderer's own collapsible-summary "
            "text; no unit wrote it and none can change it"
        )
    verified = _quoted_verified_fact(finding, by_id) if presentation else None
    if verified is not None:
        return (
            f"the quote names {verified.id}, a SUPPORTED fact BC-04 already verifies; the "
            "candidate's own fact set is the standard of support, not the upstream README, and "
            "loop-prompt.md rule 8 requires the complete verified surface - absence from the "
            "original is never itself a presentation defect for content BC-04 already verified"
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
# match rather than _quoted_heading's.
_RENDERED_CHROME = frozenset({ADDITIONAL_EXAMPLES_SUMMARY, API_SURFACE_SUMMARY})


def _quoted_chrome(finding: Mapping[str, Any]) -> str | None:
    """The renderer's own collapsible-summary text a finding quotes and nothing else, or None."""
    quote = str(finding.get("quote", "")).strip()
    return quote if quote in _RENDERED_CHROME else None


_VERIFIED_NAME_LENGTH = 3


def _quoted_verified_fact(finding: Mapping[str, Any], by_id: Mapping[str, Fact]) -> Fact | None:
    """A SUPPORTED public_symbol fact whose own bare name the quote contains as a whole word.

    Scoped to ``public_symbol`` alone, never every fact kind: a dotted suffix is only meaningful
    for a qualified identifier value (``package.Type.Method``) - the same rsplit an ``example``'s
    multi-line code or a ``format``'s bare extension would match by coincidence, not by naming it
    (measured while landing this: an unrestricted version matched ``format:output.glb`` against
    unrelated prose that merely mentioned ``.glb`` files). A reviewer, like a unit's own prose,
    names the member by its bare name (the convention item 22's ``symbol_names`` already
    established), not the fully qualified value.
    """
    quoted = _normalized(str(finding.get("quote", "")))
    if not quoted:
        return None
    for fact in by_id.values():
        if fact.kind != "public_symbol" or fact.polarity != "SUPPORTED":
            continue
        suffix = fact.value.rsplit(".", 1)[-1].lower()
        if len(suffix) >= _VERIFIED_NAME_LENGTH and re.search(rf"\b{re.escape(suffix)}\b", quoted):
            return fact
    return None


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
        if not quote_located(quote, candidate_readme):
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


def scope_defect(
    finding: Mapping[str, Any],
    candidate_readme: str,
    by_id: Mapping[str, Fact],
    evidence: str = "",
    rendered: Sequence[str] = (),
) -> str | None:
    """Why a finding is the reviewer's own defect, or None when it may stand.

    Judged from the reviewer's raw reply every time the document is built, so the answer is a
    pure function of the finding, the facts, and the rule - never of an earlier run's verdict and
    never of a mark left in the finding's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2
    RC8). A reviewer-scope defect is recorded, never blocks (docs/README_CONTRACT.md section 6),
    and never earns a second ask.

    An absence the candidate disproves is judged first, whatever the criterion: a finding that
    names text the candidate contains is refuted by the document itself, and no reading of its
    criterion changes that. So is a quote the facts exclude, for the same reason from the other
    side - the document could not have carried it. Content the renderer owns rather than a unit
    is judged the same way, before the criterion is read at all: whether the finding calls the
    renderer's own text a presentation defect or a factual one, no stage the loop can reopen
    would rewrite it (G4-W17 arrival item 37). Only the criterion-specific refutations - a
    factuality claim measured against the facts it cites - come after the switch.
    """
    absence = absence_defect(finding, candidate_readme, evidence)
    if absence is not None:
        return absence
    excluded = excluded_evidence_defect(finding, by_id)
    if excluded is not None:
        return excluded
    written = rendered_defect(finding, rendered)
    if written is not None:
        return written
    owned = renderer_owned_defect(finding, by_id)
    if owned is not None:
        return owned
    if finding.get("criterion") == "factuality":
        return factuality_defect(finding, str(finding.get("quote", "")), by_id)
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
) -> dict[str, Any]:
    """review.json: the verdict, blocking findings with their causal state, advisory findings,
    what a repair must preserve, and the two prompt identities.

    A finding that is the reviewer's own defect is recorded advisory with the reason as a field,
    the stage the reviewer named left intact: the record says why it does not block, and nothing
    downstream has to read prose to find out (section 27.5 D5).

    ``second`` is a second independent read of the same candidate under a different seed. When it
    is given, a prose judgment on a required row blocks only if that read raised a finding of the
    same class; otherwise it is recorded ``single_reader_advisory`` and does not block (the
    owner's two-reader rule, section 27.8). A second read that returned nothing usable
    corroborates nothing, which is the same answer as a second reader who saw no such defect.
    """
    findings: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    corroborated = (
        {finding_class(f) for f in second.get("findings", []) if blocking(dict(f))}
        if second is not None
        else set()
    )
    by_id = {fact.id: fact for fact in facts.facts} if facts is not None else {}
    evidence = claim_evidence(original_readme, facts) if original_readme else ""
    for finding in output.get("findings", []):
        record = dict(finding)
        reason = (
            scope_defect(finding, candidate_readme, by_id, evidence, rendered)
            if facts is not None
            else None
        )
        if reason is not None:
            record["reviewer_scope_defect"] = reason
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
    return {
        "schema_version": 1,
        "readme_sha256": readme_digest,
        "verdict": verdict,
        "verdict_as_returned": returned,
        "findings": findings,
        "advisory": advisory,
        "second_reader": {
            "read": second is not None,
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
