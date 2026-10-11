"""What inserted text may say: no evidence narration, no manifest-key citations.

The renderer writes for a regenerated README, where a sentence may cite the manifest it came from
and say it was verified against a revision. A visitor reading the maintainers' README has no use
for either, and the independent review of the first correction bundles found both: "verified
against this revision" in an Installation section, ``python_requires`` quoted where the manifest
key is ``requires-python``, "in ``pyproject.toml``, no ``project.dependencies`` is declared".

``clean`` removes the known renderer phrasings deterministically (the facts keep the evidence; the
bundle's ``corrections.json`` cites it per edit); ``narration`` reports whatever internal-assurance
vocabulary is left, using the project's own list (``narration_patterns``, plans/idea.md "Never
present: internal assurance narration") plus this path's; an edit whose text still narrates is
dropped and reported, never applied.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme.validation.registry import narration_patterns

#: ``(pattern, replacement)`` for the renderer's evidence phrasings, applied in order.
_CLEANERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r",? verified (?:against|at|on) this revision"), ""),
    (
        re.compile(r"(No required third-party package dependencies); in `[^`]+`, [^\n]*"),
        r"\1.",
    ),
    (re.compile(r" \(`[^`\n]*` in `[^`\n]+`\)\.$", re.MULTILINE), "."),
)
_EXTRA = (
    ("this revision", re.compile(r"\bthis revision\b", re.IGNORECASE)),
    ("verified against", re.compile(r"\bverified (?:against|at|in isolation)\b", re.IGNORECASE)),
    ("evidence", re.compile(r"\bevidence\b", re.IGNORECASE)),
    ("manifest key", re.compile(r"\b(?:declared|read) (?:in|from) `[^`]+`\b")),
)


def clean(text: str) -> str:
    """``text`` without the renderer's evidence phrasings."""
    for pattern, replacement in _CLEANERS:
        text = pattern.sub(replacement, text)
    return text


def narration(text: str) -> list[str]:
    """The internal-assurance phrases ``text`` still carries (empty when it is fit to publish)."""
    found = [phrase for phrase, pattern in narration_patterns(()) if pattern.search(text)]
    found += [name for name, pattern in _EXTRA if pattern.search(text) and name not in found]
    return found
