"""Apply edits to the original text and prove nothing else changed.

The proof is the point of the path (the honest equivalent of the independent review a regenerated
candidate gets): the corrected text with every edit's output span removed equals the original text
with every edit's input span removed, and each span holds exactly what its edit says. So every
changed byte belongs to a listed, evidenced edit - and a maintainer sentence no edit names is
byte-identical in the output.
"""

from __future__ import annotations

from collections.abc import Sequence

from repository_presenter.components.readme_correction.model import Edit


def order_edits(edits: Sequence[Edit]) -> tuple[list[Edit], list[Edit]]:
    """``(kept, dropped)``: edits in document order, and those dropped because they overlap an
    earlier one. Insertions at one offset are not an overlap; two replacements of the same bytes
    are, and the earlier detector (alphabetical) wins so the result never depends on dict order."""
    ordered = sorted(edits, key=lambda e: (e.start, e.end, e.order, e.detector))
    kept: list[Edit] = []
    dropped: list[Edit] = []
    frontier = 0
    for edit in ordered:
        if edit.start < frontier:
            dropped.append(edit)
            continue
        kept.append(edit)
        frontier = max(frontier, edit.end)
    return kept, dropped


def apply_edits(text: str, edits: Sequence[Edit]) -> tuple[str, list[tuple[int, int]]]:
    """``(corrected, output spans)`` for ``edits`` already ordered and non-overlapping."""
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    cursor = 0
    produced = 0
    for edit in edits:
        before = text[cursor : edit.start]
        pieces.append(before)
        produced += len(before)
        pieces.append(edit.replacement)
        spans.append((produced, produced + len(edit.replacement)))
        produced += len(edit.replacement)
        cursor = edit.end
    pieces.append(text[cursor:])
    return "".join(pieces), spans


def _without(text: str, spans: Sequence[tuple[int, int]]) -> str:
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def confinement_violations(
    original: str,
    corrected: str,
    edits: Sequence[Edit],
    output_spans: Sequence[tuple[int, int]],
) -> list[str]:
    """Why ``corrected`` is not exactly ``original`` plus ``edits``; empty when it is."""
    problems: list[str] = []
    if len(edits) != len(output_spans):
        return [f"{len(edits)} edits but {len(output_spans)} output spans"]
    previous_end = 0
    for index, (edit, (out_start, out_end)) in enumerate(zip(edits, output_spans, strict=True)):
        if edit.start < previous_end or edit.end > len(original) or edit.start > edit.end:
            problems.append(f"edit {index} ({edit.detector}) overlaps or leaves the text")
            continue
        previous_end = edit.end
        if original[edit.start : edit.end] != edit.original:
            problems.append(f"edit {index} ({edit.detector}) quotes text the original lacks")
        if corrected[out_start:out_end] != edit.replacement:
            problems.append(f"edit {index} ({edit.detector}) is not what the corrected text holds")
    if not problems:
        residue_original = _without(original, [(e.start, e.end) for e in edits])
        residue_corrected = _without(corrected, output_spans)
        if residue_original != residue_corrected:
            problems.append("text outside the listed edits differs from the original")
    return problems
