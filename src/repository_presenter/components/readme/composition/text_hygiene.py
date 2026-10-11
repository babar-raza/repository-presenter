"""Text hygiene for authored units: a sentence cut off, or one that slipped into another script.

Wave-3 acceptance review (reseal f69f75c7, Slides-Python): a Scope bullet of 2,254 characters
restated five limitations the section already stated, and ended "... never strips content this库" -
cut off mid-sentence, the last word a Chinese character. Every unit check passed it, BC-05 and
BC-10 accepted the README, and a maintainer would have read a broken sentence in the project's own
Scope section. A scan of the 3,719 authored units in 41 sealed bundles finds the same family
twice: that bullet, and a PDF-Cpp API description reading "used to indicate裁切 lines". Both are
model output that left the language of the document, so the rule is deterministic and cheap:

* a unit contains no letter of a non-Latin script (CJK, kana, Hangul, Cyrillic, Arabic, Hebrew,
  Thai, Devanagari) unless that exact character already appears in a verified fact or in the
  upstream README the document answers - a product that really handles Chinese text may say so;
  the whole check is skipped when the upstream README is itself written in another script;
* a sentence-bearing unit ends in terminal punctuation or a closing mark. A heading-like slot
  (``workflow:`` task headings, ``link:`` descriptions) is a phrase by design and is exempt; across
  the same 3,719 units those are the only non-terminal ones;
* a unit is not longer than ``MAX_UNIT_CHARS``. The longest well-formed unit in those bundles is
  984 characters (an opening); a unit past 1,500 is a pasted list, not a sentence.

It is called from ``authoring.unit_checks`` as one more repairable error (the same re-ask that
fixes an unaccepted identifier fixes this), so BC-04 reaches it too.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from repository_presenter.core.facts import FactsDocument

MAX_UNIT_CHARS = 1500
# Slots whose text is a phrase by design: a task heading printed as ``### Title Case`` and a
# one-line link description. Everything else the section prints is a sentence.
_PHRASE_SLOT_PREFIXES = ("workflow:", "link:")
# A final character that ends a sentence or closes a quotation, code span or bracket, in Latin
# and in the full-width forms a CJK README uses (the check is skipped for foreign-script text only
# in the script test, not here).
_TERMINAL = frozenset(
    ".!?:;)]}\"'`*"
    "\u2026\u201d\u2019"  # ellipsis, closing double and single quotation marks
    "\u3002\uff01\uff1f\uff1a\uff1b\uff09\u300d\u300f"  # full-width terminals and closers
)
_FOREIGN_SCRIPTS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
    "CYRILLIC",
    "ARABIC",
    "HEBREW",
    "THAI",
    "DEVANAGARI",
)
_SHOWN_CHARACTERS = 4
_QUOTE_TAIL = 40


def foreign_script(character: str) -> str | None:
    """The script name when ``character`` is a letter of a script an English README never uses."""
    if character.isascii() or not character.isalpha():
        return None
    name = unicodedata.name(character, "")
    return next((script for script in _FOREIGN_SCRIPTS if name.startswith(script)), None)


def _source_text(facts: FactsDocument) -> tuple[str, bool]:
    """The text the unit may legitimately echo, and whether the upstream README is Latin-script.

    The verified facts' values and the inherited README's own text are the only places a
    non-Latin character can come from; an unreadable or empty README counts as English."""
    verified = " ".join(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED")
    inherited = " ".join(fact.value for fact in facts.by_kind("inherited_unit"))
    letters = [character for character in inherited if character.isalpha()]
    foreign = sum(foreign_script(character) is not None for character in letters)
    latin = not letters or foreign * 2 < len(letters)
    return f"{verified} {inherited}", latin


def hygiene_errors(units: Iterable[Mapping[str, Any]], facts: FactsDocument) -> list[str]:
    """One error per authored unit that was cut off, left the document's language, or is a pasted
    list; each names the slot and quotes where it went wrong, so the one re-ask can act on it."""
    errors: list[str] = []
    source, latin = _source_text(facts)
    for unit in units:
        slot = str(unit.get("slot", "?"))
        text = str(unit.get("text", "")).strip()
        if not text:
            continue
        if latin:
            strangers = sorted(
                {
                    character
                    for character in text
                    if foreign_script(character) is not None and character not in source
                }
            )
            if strangers:
                scripts = sorted({foreign_script(character) or "" for character in strangers})
                errors.append(
                    f"unit {slot}: contains {''.join(strangers[:_SHOWN_CHARACTERS])!r} "
                    f"({', '.join(scripts)} script) in an English README; write the whole "
                    "sentence in English"
                )
        if not slot.startswith(_PHRASE_SLOT_PREFIXES) and text[-1] not in _TERMINAL:
            errors.append(
                f"unit {slot}: ends without terminal punctuation "
                f"(...{text[-_QUOTE_TAIL:]!r}); it reads as cut off, so finish the sentence or "
                "end it where it is complete"
            )
        if len(text) > MAX_UNIT_CHARS:
            errors.append(
                f"unit {slot}: is {len(text)} characters, past the {MAX_UNIT_CHARS} a single unit "
                "may take; say each point once, in a sentence, and leave the rest to the section's "
                "other units"
            )
    return errors
