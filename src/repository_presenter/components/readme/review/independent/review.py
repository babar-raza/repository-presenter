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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    section_ids,
)
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
    re.compile(r"<[^>\n]+>"),  # HTML tags such as details and summary
    re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+"),  # list markers
    re.compile(r"(?m)^\s*#{1,6}\s+"),  # heading marks
    re.compile(r"\*\*|__|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)"),  # emphasis
)


def _normalized(text: str) -> str:
    """Text as a reader compares it: no code spans or Markdown syntax, plain dashes and
    quotes, single spaces. A reviewer quotes what it reads; the syntax around it is ours."""
    plain = text.translate(_TYPOGRAPHY)
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
    # An ellipsis abbreviates: every fragment around it is exact candidate text.
    fragments = [part.strip() for part in _ELLIPSIS.split(wanted) if part.strip()]
    if len(fragments) > 1 and all(part in haystack for part in fragments):
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


def presentation_defect(finding: Mapping[str, Any]) -> str | None:
    """Why a presentation finding is the reviewer's own defect, or None when it may stand.

    A deterministic section renders from facts under the contract's own checks (BC-02, BC-05,
    BC-07): its wording and its choice of command are the renderer's, so no stage the loop can
    reopen would change them. A factual error there is a factuality finding against the fact.
    """
    if finding.get("criterion") != "presentation":
        return None
    if finding.get("section_id") not in _DETERMINISTIC_SECTIONS:
        return None
    return (
        f"section {finding.get('section_id')} renders from facts under the contract's own "
        "checks; its presentation is the renderer's, and a factual error there is a "
        "factuality finding"
    )


# At a Glance is mixed-owned only in what the plan selects: the renderer owns every node, edge,
# and label (README_CONTRACT.md section 2.1), so its presentation is likewise the renderer's.
_DETERMINISTIC_SECTIONS = frozenset(
    {*(section.id for section in SEMANTIC_SHELL if section.owner == "D"), "at_a_glance"}
)


def review_checks(
    output: dict[str, Any], candidate_readme: str, facts: FactsDocument | None = None
) -> list[str]:
    """Why the review may not be used, beyond schema and binding; empty when it holds."""
    errors: list[str] = []
    known = set(section_ids()) | _STRUCTURAL_SECTIONS
    seen: set[str] = set()
    findings = output.get("findings", [])
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
            errors.append(
                f"finding {label}: quote is not the candidate's text: {quote.strip()[:60]!r}"
            )
    return errors


def scope_defect(
    finding: Mapping[str, Any], candidate_readme: str, by_id: Mapping[str, Fact]
) -> str | None:
    """Why a finding is the reviewer's own defect, or None when it may stand.

    Judged from the reviewer's raw reply every time the document is built, so the answer is a
    pure function of the finding, the facts, and the rule - never of an earlier run's verdict and
    never of a mark left in the finding's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2
    RC8). A reviewer-scope defect is recorded, never blocks (docs/README_CONTRACT.md section 6),
    and never earns a second ask.
    """
    criterion = finding.get("criterion")
    if criterion == "factuality":
        quote = str(finding.get("quote", ""))
        return factuality_defect(finding, quote, by_id)
    if criterion == "presentation":
        return presentation_defect(finding)
    return None


def review_document(
    output: dict[str, Any],
    reviewer: LoadedManifest,
    authoring: LoadedManifest,
    readme_digest: str,
    candidate_readme: str = "",
    facts: FactsDocument | None = None,
) -> dict[str, Any]:
    """review.json: the verdict, blocking findings with their causal state, advisory findings,
    what a repair must preserve, and the two prompt identities.

    A finding that is the reviewer's own defect is recorded advisory with the reason as a field,
    the stage the reviewer named left intact: the record says why it does not block, and nothing
    downstream has to read prose to find out (section 27.5 D5).
    """
    findings: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    by_id = {fact.id: fact for fact in facts.facts} if facts is not None else {}
    for finding in output.get("findings", []):
        record = dict(finding)
        reason = scope_defect(finding, candidate_readme, by_id) if facts is not None else None
        if reason is not None:
            record["reviewer_scope_defect"] = reason
        if reason is None and blocking(finding):
            record["causal_state"] = CAUSAL_STATES[str(finding["causal_stage"])]
            findings.append(record)
        else:
            record["causal_state"] = None
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
