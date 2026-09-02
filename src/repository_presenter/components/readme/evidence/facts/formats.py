"""``format`` facts: the extensions the README's examples load or save, judged by their receipts.

A format claim lives in an example's code and the platform plugin reads it from the syntax tree;
its polarity is the example's verified outcome. An extension an executed example loaded or saved
is SUPPORTED, and a repository file staged for an executed example proves its extension as input.
An extension only a failed or unverified example names stays UNRESOLVED; nothing is inferred from
prose or from a catalog. Direction is part of the ID: ``format:input.obj``, ``format:output.stl``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleOutcome,
    ExampleReceipt,
    FormatClaim,
)
from repository_presenter.core.facts import Evidence, Fact, fact_id


def format_facts(
    candidates: Sequence[ExampleCandidate],
    receipts: Sequence[ExampleReceipt],
    claims_for: Callable[[str], Sequence[FormatClaim]],
    receipts_path: str,
) -> list[Fact]:
    """One fact per (direction, extension) across all examples, with every example as evidence."""
    by_ordinal = {receipt.ordinal: receipt for receipt in receipts}
    evidence: dict[tuple[str, str], list[Evidence]] = {}
    supported: set[tuple[str, str]] = set()
    for candidate in candidates:
        receipt = by_ordinal.get(candidate.ordinal)
        outcome: ExampleOutcome = receipt.outcome if receipt else "NOT_VERIFIED"
        detail = receipt.detail if receipt else "no verification receipt"
        for claim in claims_for(candidate.code):
            key: tuple[str, str] = (claim.direction, claim.extension)
            line = candidate.start_line + claim.line
            evidence.setdefault(key, []).extend(
                (
                    Evidence(
                        candidate.source_path,
                        f"line {line}; example {candidate.ordinal}: {claim.direction} "
                        f"{claim.extension}",
                    ),
                    Evidence(receipts_path, f"example {candidate.ordinal}: {outcome}; {detail}"),
                )
            )
            if outcome == "EXECUTED":
                supported.add(key)
        if receipt is None or outcome != "EXECUTED":
            continue
        for binding in receipt.fixtures:
            extension = Path(binding.literal).suffix.lower()
            if not extension:
                continue
            key = ("input", extension)
            evidence.setdefault(key, []).append(
                Evidence(
                    binding.source_path,
                    f"staged as {binding.literal}; example {candidate.ordinal} read it: EXECUTED",
                )
            )
            supported.add(key)
    facts: list[Fact] = []
    for key in sorted(evidence):
        direction, extension = key
        facts.append(
            Fact(
                fact_id("format", direction, extension.lstrip(".")),
                "format",
                extension,
                tuple(evidence[key]),
                polarity="SUPPORTED" if key in supported else "UNRESOLVED",
                confidence=1.0 if key in supported else 0.5,
            )
        )
    return facts
