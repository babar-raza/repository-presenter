"""``format`` facts: the extensions the product reads or writes, corroborated two ways.

A format claim lives in an example's code and the platform plugin reads it from the syntax tree;
an extension an executed example loaded or saved is SUPPORTED, and a repository file staged for an
executed example proves its extension as input. A claim no executed example makes is SUPPORTED
only when two independent static sources agree (docs/RESEARCH_AND_GUIDELINES.md sections 22.1
and 26): the product's format declarations state the extension and a registered, non-stub
importer or exporter implements that direction. One source alone, or a failed or unverified
example alone, leaves the fact UNRESOLVED; nothing is inferred from prose. Direction is part of
the ID: ``format:input.obj``, ``format:output.stl``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleOutcome,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Evidence, Fact, fact_id


def format_facts(
    candidates: Sequence[ExampleCandidate],
    receipts: Sequence[ExampleReceipt],
    claims_for: Callable[[str], Sequence[FormatClaim]],
    receipts_path: str,
    declarations: Sequence[FormatDeclaration] = (),
) -> list[Fact]:
    """One fact per (direction, extension) across the examples and the static sources."""
    by_ordinal = {receipt.ordinal: receipt for receipt in receipts}
    evidence: dict[tuple[str, str], list[Evidence]] = {}
    executed: set[tuple[str, str]] = set()
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
                executed.add(key)
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
            executed.add(key)
    # Static corroboration: a declaration states the extension for either direction; a
    # registration implements one direction. Both together support the pair.
    declared: dict[str, list[FormatDeclaration]] = {}
    registered: dict[tuple[str, str], list[FormatDeclaration]] = {}
    for declaration in declarations:
        if declaration.kind == "declaration":
            declared.setdefault(declaration.extension, []).append(declaration)
        elif declaration.direction is not None:
            registered.setdefault((declaration.direction, declaration.extension), []).append(
                declaration
            )
    corroborated: set[tuple[str, str]] = set()
    for key, registrations in sorted(registered.items()):
        direction, extension = key
        entries = evidence.setdefault(key, [])
        for statement in declared.get(extension, []):
            entries.append(
                Evidence(statement.source_path, f"line {statement.line}; {statement.detail}")
            )
        for registration in registrations:
            entries.append(
                Evidence(
                    registration.source_path, f"line {registration.line}; {registration.detail}"
                )
            )
        if extension in declared:
            corroborated.add(key)
    supported = executed | corroborated
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
