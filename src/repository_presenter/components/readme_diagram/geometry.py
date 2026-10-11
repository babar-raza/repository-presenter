"""The At a Glance label-width model: one deterministic way to decide where a label breaks.

A hosted Mermaid renderer measures a label in one font and the browser may draw it in another; a
box sized from the first clips the second. The renderer therefore never leaves a break to the
browser: every label is wrapped here, from a per-character width table, into ``<br/>`` lines whose
modelled width stays inside a budget, and the diagram is drawn with SVG text that grows its box
with the text (``build.py``). The table is the *envelope* of the widths measured in Verdana, Arial,
Trebuchet MS, Segoe UI and Tahoma at 16 px (each character takes the widest of the five), plus a
4 percent margin for fonts not measured, so a label that fits the model fits any of them.

Pure and deterministic: the same label and budget always give the same lines, which is what lets
validation, planning and the real-render check agree on a label's height before anything draws.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: The pixel size the table was measured at; Mermaid's default flowchart font size.
FONT_PX = 16
#: Margin over the measured envelope for a font nobody measured (DejaVu Sans, Liberation Sans...).
SAFETY = 1.04
#: A character outside the table (CJK, an emoji) is charged a full em, the widest a glyph gets.
FALLBACK_PX = 16.0
#: Where Mermaid wraps a label by itself when it is not told to, in its default configuration.
MERMAID_AUTO_WRAP_PX = 200

#: Generated once from ``render/measure.mjs``-style canvas measurements; see the module docstring.
WIDTHS: dict[str, float] = {
    " ": 5.7,
    "!": 6.3,
    '"': 7.4,
    "#": 13.1,
    "$": 10.2,
    "%": 17.3,
    "&": 12.8,
    "'": 4.3,
    "(": 7.3,
    ")": 7.3,
    "*": 10.2,
    "+": 13.1,
    ",": 5.9,
    "-": 7.3,
    ".": 5.9,
    "/": 8.4,
    "0": 10.2,
    "1": 10.2,
    "2": 10.2,
    "3": 10.2,
    "4": 10.2,
    "5": 10.2,
    "6": 10.2,
    "7": 10.2,
    "8": 10.2,
    "9": 10.2,
    ":": 7.3,
    ";": 7.3,
    "<": 13.1,
    "=": 13.1,
    ">": 13.1,
    "?": 8.9,
    "@": 16.3,
    "A": 11.0,
    "B": 11.0,
    "C": 11.6,
    "D": 12.4,
    "E": 10.7,
    "F": 9.8,
    "G": 12.5,
    "H": 12.1,
    "I": 6.8,
    "J": 8.0,
    "K": 11.1,
    "L": 8.9,
    "M": 14.4,
    "N": 12.0,
    "O": 12.6,
    "P": 10.7,
    "Q": 12.6,
    "R": 11.6,
    "S": 11.0,
    "T": 9.9,
    "U": 11.8,
    "V": 11.0,
    "W": 15.9,
    "X": 11.0,
    "Y": 10.7,
    "Z": 11.0,
    "[": 7.3,
    "\\": 7.3,
    "]": 7.3,
    "^": 13.1,
    "_": 10.2,
    "`": 10.2,
    "a": 9.6,
    "b": 10.0,
    "c": 8.4,
    "d": 10.0,
    "e": 9.6,
    "f": 6.0,
    "g": 10.0,
    "h": 10.2,
    "i": 4.6,
    "j": 5.9,
    "k": 9.5,
    "l": 4.8,
    "m": 15.6,
    "n": 10.2,
    "o": 9.8,
    "p": 10.0,
    "q": 10.0,
    "r": 6.9,
    "s": 8.4,
    "t": 6.4,
    "u": 10.2,
    "v": 9.5,
    "w": 13.1,
    "x": 9.5,
    "y": 9.5,
    "z": 8.4,
    "{": 10.2,
    "|": 8.4,
    "}": 10.2,
    "~": 13.1,
    "\u2014": 16.0,
    "\u2013": 10.2,
    "\u2026": 16.0,
    "\u00d7": 13.1,
    "\u2011": 6.4,
    "\u2019": 5.9,
    "\u201c": 8.4,
    "\u201d": 8.4,
    "\u00e9": 9.6,
    "\u00b0": 8.7,
    "\u00b7": 5.9,
    "\u2192": 16.0,
}

_WORD = re.compile(r"\S+")


def text_px(text: str) -> float:
    """The modelled width in pixels of ``text`` on one line at ``FONT_PX``."""
    return round(sum(WIDTHS.get(char, FALLBACK_PX) for char in text) * SAFETY, 1)


def tokens(label: str) -> list[str]:
    """The words of ``label``, the units a line break may fall between."""
    return _WORD.findall(label)


def widest_token_px(label: str) -> float:
    """The width of the widest unbroken word of ``label``; a wider word cannot be wrapped."""
    return max((text_px(word) for word in tokens(label)), default=0.0)


def _greedy(words: Sequence[str], budget_px: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}" if current else word
        if current and text_px(trial) > budget_px:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def wrap_label(label: str, budget_px: float) -> tuple[str, ...]:
    """``label`` broken between words into the fewest lines that fit ``budget_px``, then evened.

    Greedy fill decides the line count; the budget is then tightened as far as that count allows,
    so the lines come out near one width and the box stays as narrow as the text permits. A word
    wider than the budget stands alone on its line (the box grows to it; nothing is broken
    mid-word, so no text is ever lost or split).
    """
    words = tokens(label)
    if not words:
        return ()
    lines = _greedy(words, budget_px)
    count = len(lines)
    if count == 1:
        return tuple(lines)
    low = max(widest_token_px(label), text_px(label) / count)
    high = max(text_px(line) for line in lines)
    best = lines
    # Binary search on the budget in 0.5 px steps: the narrowest one that keeps the line count.
    for _ in range(24):
        if high - low < 0.5:
            break
        middle = (low + high) / 2
        trial = _greedy(words, middle)
        if len(trial) <= count:
            best, high = trial, middle
        else:
            low = middle
    return tuple(best)


def label_lines(label: str, budget_px: float) -> int:
    """How many lines ``label`` occupies once wrapped to ``budget_px``."""
    return len(wrap_label(label, budget_px))
