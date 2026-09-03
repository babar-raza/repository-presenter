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
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import section_ids
from repository_presenter.core.facts import FACT_KINDS, FactsDocument, bounded_records
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


def _normalized(text: str) -> str:
    """Text as a reader compares it: no code spans, plain dashes and quotes, single spaces."""
    plain = text.translate(_TYPOGRAPHY).replace("`", "")
    return re.sub(r"\s+", " ", plain).strip().lower()


def quote_located(quote: str, candidate_readme: str) -> bool:
    """A quote locates candidate text when its normalized form occurs in the candidate; a quote
    that exists nowhere in any spelling is invented and rejects the finding."""
    wanted = _normalized(quote)
    return not wanted or wanted in _normalized(candidate_readme)


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


def review_checks(output: dict[str, Any], candidate_readme: str) -> list[str]:
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
    verdict = output.get("verdict")
    if verdict != ACCEPT and not any(blocking(f) for f in findings):
        errors.append(
            f"verdict {verdict} needs at least one finding that names a section and a causal "
            "stage from S2 to S8; otherwise the candidate is accepted"
        )
    return errors


def review_document(
    output: dict[str, Any], reviewer: LoadedManifest, authoring: LoadedManifest, readme_digest: str
) -> dict[str, Any]:
    """review.json: the verdict, blocking findings with their causal state, advisory findings,
    what a repair must preserve, and the two prompt identities."""
    findings: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    for finding in output.get("findings", []):
        record = dict(finding)
        if blocking(finding):
            record["causal_state"] = CAUSAL_STATES[str(finding["causal_stage"])]
            findings.append(record)
        else:
            record["causal_state"] = None
            advisory.append(record)
    return {
        "schema_version": 1,
        "readme_sha256": readme_digest,
        "verdict": output.get("verdict"),
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
