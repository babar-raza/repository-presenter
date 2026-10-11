"""The closed edit shape and the confinement proof: an edit that would touch an unrelated
maintainer sentence cannot be built, and a corrected text with any other change is refused."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
    order_edits,
)
from repository_presenter.components.readme_correction.model import (
    BROKEN_LINK,
    FALSE_CLAIM_FIX,
    MISSING_SECTION,
    Edit,
    InvalidEditError,
)

TEXT = "Intro line.\nInstall version 1.0.0 now.\nUnrelated maintainer sentence.\n"


def edit(**overrides: object) -> Edit:
    fields: dict[str, object] = {
        "kind": FALSE_CLAIM_FIX,
        "detector": "t",
        "start": TEXT.index("1.0.0"),
        "end": TEXT.index("1.0.0") + 5,
        "original": "1.0.0",
        "replacement": "2.0.0",
        "fact_ids": ("package:published_version",),
        "rationale": "r",
    }
    fields.update(overrides)
    return Edit(**fields)  # type: ignore[arg-type]


def test_a_correct_edit_changes_only_its_span() -> None:
    corrected, spans = apply_edits(TEXT, [edit()])
    assert corrected == TEXT.replace("1.0.0", "2.0.0")
    assert confinement_violations(TEXT, corrected, [edit()], spans) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"original": "x\ny", "end": TEXT.index("1.0.0") + 3},  # spans two lines
        {"original": "x" * 201, "end": TEXT.index("1.0.0") + 201},  # a sentence, not a token
        {"replacement": "a\nb"},  # a one-line fix stays on its line
        {"replacement": "1.0.0"},  # a no-op
        {"fact_ids": ()},  # no evidence
        {"kind": "REWRITE"},  # outside the closed set
        {"kind": BROKEN_LINK, "original": ""},  # nothing quoted
    ],
)
def test_an_edit_outside_the_closed_shape_cannot_be_built(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidEditError):
        edit(**overrides)


def test_a_section_is_only_ever_inserted() -> None:
    with pytest.raises(InvalidEditError):  # replacing text with a section
        edit(kind=MISSING_SECTION, replacement="## License\n\nMIT\n")
    with pytest.raises(InvalidEditError):  # an insertion that is not a section
        edit(kind=MISSING_SECTION, start=3, end=3, original="", replacement="loose text")
    inserted = edit(
        kind=MISSING_SECTION, start=0, end=0, original="", replacement="## License\n\nMIT\n\n"
    )
    corrected, spans = apply_edits(TEXT, [inserted])
    assert corrected == "## License\n\nMIT\n\n" + TEXT
    assert confinement_violations(TEXT, corrected, [inserted], spans) == []


def test_text_changed_outside_the_edits_is_caught() -> None:
    corrected, spans = apply_edits(TEXT, [edit()])
    tampered = corrected.replace("Unrelated maintainer sentence.", "Rewritten sentence.")
    assert confinement_violations(TEXT, tampered, [edit()], spans) == [
        "text outside the listed edits differs from the original"
    ]


def test_an_edit_quoting_text_the_original_lacks_is_caught() -> None:
    forged = edit(original="9.9.9")
    corrected, spans = apply_edits(TEXT, [forged])
    problems = confinement_violations(TEXT, corrected, [forged], spans)
    assert any("quotes text the original lacks" in problem for problem in problems)


def test_overlapping_edits_keep_one_and_drop_the_other() -> None:
    first = edit(detector="a")
    second = edit(
        detector="b", start=first.start + 2, end=first.end, original="0.0", replacement="9.9"
    )
    kept, dropped = order_edits([second, first])
    assert kept == [first] and dropped == [second]


def test_insertions_at_one_offset_are_not_an_overlap() -> None:
    one = edit(
        kind=MISSING_SECTION, start=5, end=5, original="", replacement="## A\n\nx\n\n", order=1
    )
    two = edit(
        kind=MISSING_SECTION, start=5, end=5, original="", replacement="## B\n\ny\n\n", order=2
    )
    kept, dropped = order_edits([two, one])
    assert kept == [one, two] and dropped == []
