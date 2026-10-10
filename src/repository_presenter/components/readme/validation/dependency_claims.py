"""The unscoped absolute dependency claim (docs/README_CONTRACT.md section 2, "Never present").

"Requiring no external dependencies", "dependency-free", "zero dependencies": a claim that a
product has no dependencies is either exactly true of one dependency class the sentence names
("no third-party runtime crates", "no native system libraries") and proven by the dependency
facts, or it is a claim the manifest may contradict. The contract names the rule; no check made
it blocking until Aspose.Cells FOSS for Python (2026-10-10) sealed an opening paragraph saying
"requiring no external dependencies beyond the library itself" for a library whose manifest
requires ``pycryptodome`` and ``olefile``.

Ported from aspose.org's ``check_unqualified_dependency_claims`` (the claim patterns, the
scope-qualifier words, and the clause-narrowing that stops one scoped clause rescuing a second,
unscoped one; migration/reuse-manifest.yaml has the record). Not ported: the ``self-contained``
and ``no third-party code`` patterns, which flag ordinary prose ("a self-contained example") the
dependency facts say nothing about.
"""

from __future__ import annotations

import re

CLAIM_PATTERNS = (
    r"\bno external dependenc(?:y|ies)\b",
    r"\bdependency[- ]free\b",
    r"\bno dependenc(?:y|ies) required\b",
    r"\bcompletely standalone\b",
    r"\bzero dependenc(?:y|ies)\b",
    r"\bno dependenc(?:y|ies) (?:of any kind|at all|whatsoever)\b",
    r"\bno external (?:runtime|installation|software)\b",
)
_CLAIM = re.compile("|".join(CLAIM_PATTERNS), re.IGNORECASE)
# A qualifier must name a dependency CLASS; the bare nouns "package", "library", "crate" are how a
# README names the product itself and never scope a claim (the source's own comment).
_SCOPE = re.compile(
    r"\bthird[- ]party\s+(?:runtime\s+)?crates?\b"
    r"|\bruntime\s+crates?\b"
    r"|\bthird[- ]party\s+packages?\b"
    r"|\bthird[- ]party\s+librar(?:y|ies)\b"
    r"|\bnative(?:\s+system)?\s+librar(?:y|ies)\b"
    r"|\bnative\s+binar(?:y|ies)\b"
    r"|\bsystem\s+librar(?:y|ies)\b"
    r"|\bproprietary\s+(?:aspose\s+)?(?:runtime|sdk|dll|engine)\b"
    r"|\bmicrosoft office\b"
    r"|\bcommercial\s+(?:runtime|license|sdk)\b",
    re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(r"\s+(?:or|and)\s+|[,;]\s*")


def unscoped_dependency_claims(text: str) -> list[str]:
    """Each absolute dependency-absence phrase in ``text`` whose own clause names no dependency
    class. The qualifier is searched in the clause holding the phrase, never the whole sentence."""
    found: list[str] = []
    for match in _CLAIM.finditer(text):
        sentence_start = max(text.rfind(". ", 0, match.start()), text.rfind("\n", 0, match.start()))
        window_start = sentence_start + 1 if sentence_start != -1 else 0
        ends = [pos for pos in (text.find(mark, match.end()) for mark in ".\n") if pos != -1]
        window_end = min(ends) + 1 if ends else len(text)
        sentence = text[window_start:window_end]
        relative_start = match.start() - window_start
        relative_end = match.end() - window_start
        cuts = {0, len(sentence)}
        for boundary in _CLAUSE_BOUNDARY.finditer(sentence):
            cuts.update((boundary.start(), boundary.end()))
        ordered = sorted(cuts)
        clause = sentence[
            max((cut for cut in ordered if cut <= relative_start), default=0) : min(
                (cut for cut in ordered if cut >= relative_end), default=len(sentence)
            )
        ]
        if not _SCOPE.search(clause):
            found.append(match.group(0))
    return found
