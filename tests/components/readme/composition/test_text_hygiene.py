"""A unit that was cut off, left the document's language, or is a pasted list is refused."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.composition.text_hygiene import (
    MAX_UNIT_CHARS,
    foreign_script,
    hygiene_errors,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REPOSITORY = "org/Aspose.Widget-FOSS-for-Python"
CHINESE_LIBRARY = chr(0x5E93)  # "library", the character Slides-Python's bullet ended on
CHINESE_TITLES = chr(0x4E2D) + chr(0x6587)  # "Chinese"
HAN_SENTENCE = CHINESE_LIBRARY * 3  # a README written in Han script


def _facts(*extra: Fact, readme: str = "Widgets are saved to a file.") -> FactsDocument:
    return FactsDocument(
        REPOSITORY,
        "a" * 40,
        (
            Fact(
                "inherited_unit:001.paragraph",
                "inherited_unit",
                readme,
                (Evidence("README.md", None),),
            ),
            *extra,
        ),
    )


def _unit(slot: str, text: str) -> dict[str, Any]:
    return {"section": "scope_limitations", "slot": slot, "text": text, "fact_ids": []}


def test_a_well_formed_unit_passes() -> None:
    units = [_unit("limitation:1", "Opening and re-saving a file never strips content.")]
    assert hygiene_errors(units, _facts()) == []


def test_a_unit_cut_off_on_a_chinese_character_is_refused_twice_over() -> None:
    """Wave-3 acceptance review, Slides-Python limitation:6: '... never strips content this' plus
    a Chinese character where the sentence stopped."""
    cut = _unit("limitation:6", "so re-saving a file never strips content this" + CHINESE_LIBRARY)
    errors = hygiene_errors([cut], _facts())
    assert len(errors) == 2
    assert CHINESE_LIBRARY in errors[0] and "CJK" in errors[0] and "limitation:6" in errors[0]
    assert "ends without terminal punctuation" in errors[1]


def test_a_foreign_script_slipped_into_a_description_is_refused() -> None:
    """The same family in PDF-Cpp: an API description with Chinese words in the middle of it."""
    slip = chr(0x88C1) + chr(0x5207)
    unit = _unit(
        "type:public_symbol:x", f"A mark annotation used to indicate{slip} lines in a PDF."
    )
    errors = hygiene_errors([unit], _facts())
    assert len(errors) == 1 and all(character in errors[0] for character in slip)


def test_a_character_the_facts_or_the_readme_already_spell_is_not_a_slip() -> None:
    """A product that really handles Chinese text may say so: the character is evidence."""
    unit = _unit("capability:1", f"Reads {CHINESE_TITLES} document titles.")
    assert len(hygiene_errors([unit], _facts())) == 1
    as_fact = Fact(
        "example:001",
        "example",
        f"title = '{CHINESE_TITLES}'",
        (Evidence("README.md", None),),
    )
    assert hygiene_errors([unit], _facts(as_fact)) == []
    assert hygiene_errors([unit], _facts(readme=f"Reads {CHINESE_TITLES} titles.")) == []


def test_a_readme_written_in_another_script_is_not_judged() -> None:
    unit = _unit("opening", HAN_SENTENCE + chr(0x3002))
    chinese = _facts(readme=HAN_SENTENCE + chr(0xFF0C) + HAN_SENTENCE + chr(0x3002))
    assert hygiene_errors([unit], chinese) == []


def test_phrase_slots_need_no_terminal_punctuation_but_sentence_slots_do() -> None:
    """Across 3,719 authored units in 41 sealed bundles, the only unpunctuated ones are task
    headings and link descriptions, which are phrases by design."""
    phrases = [
        _unit("workflow:example:004", "Assign a PBR material and export to glTF"),
        _unit("link:link_target:025", "Reference for every public type"),
    ]
    assert hygiene_errors(phrases, _facts()) == []
    assert len(hygiene_errors([_unit("capability:1", "Saves a scene")], _facts())) == 1
    for closing in (".", "!", "?", ":", ")", "`", '"', chr(0x2026)):
        assert hygiene_errors([_unit("capability:1", f"Saves a scene{closing}")], _facts()) == []


def test_a_pasted_list_past_the_length_bound_is_refused() -> None:
    sentence = "Rendering is not implemented. "
    long_unit = _unit("limitation:6", sentence * (MAX_UNIT_CHARS // len(sentence) + 2))
    errors = hygiene_errors([long_unit], _facts())
    assert len(errors) == 1 and "past the" in errors[0]
    just_under = _unit("limitation:6", (sentence * 60)[: MAX_UNIT_CHARS - 1].rstrip() + ".")
    assert hygiene_errors([just_under], _facts()) == []


def test_only_letters_of_a_foreign_script_count() -> None:
    assert foreign_script(CHINESE_LIBRARY) == "CJK"
    assert foreign_script(chr(0x416)) == "CYRILLIC"
    assert foreign_script("a") is None
    assert foreign_script(chr(0xE9)) is None  # an accented Latin letter is not a foreign script
    assert foreign_script(chr(0x2014)) is None  # punctuation
    assert foreign_script(chr(0x3C0)) is None  # Greek appears in identifiers and mathematics
