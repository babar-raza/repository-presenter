"""A deferred unit is "stated" only when the README carries its claim-bearing tokens and prose."""

from __future__ import annotations

from repository_presenter.components.readme.validation.content_presence import unstated

README = """# Aspose.Widget for Python

## Installation

```bash
pip install "aspose-widget[pdf]"
```

Requires Python 3.10 or later.

## Quick Start

Widgets are saved with `Widget.save()`; the PDF writer needs ReportLab, a separate package
published at https://pypi.org/project/reportlab/ and installed through the pdf extra.

| Format | Direction |
| --- | --- |
| PDF | write |
"""


def test_a_unit_with_no_claim_in_it_is_stated() -> None:
    """Nothing a reader could lose: no anchor and no long sentence."""
    assert unstated("Install the library from PyPI:", README) == []


def test_every_anchor_of_a_unit_must_appear_in_the_readme() -> None:
    """Wave-3 acceptance review, Note-Python 013: the `[pdf]` extra and the ReportLab link."""
    carried = "PDF export needs ReportLab: see [ReportLab](https://pypi.org/project/reportlab/)."
    assert unstated(carried, README) == []
    lost = "PDF export needs the `pdf` extra, which pulls in [Other](https://example.org/other)."
    assert unstated(lost, README) == ["link 'https://example.org/other'"]


def test_a_dropped_code_span_is_named_even_when_the_prose_is_restated() -> None:
    """Slides-Python 018: the shared-namespace warning carried an error message no rewrite kept."""
    unit = (
        "**`aspose` is a shared namespace package.** If the commercial package is installed it "
        "takes the name over, with a bare `ModuleNotFoundError: No module named 'aspose.widget'`."
    )
    assert unstated(unit, README) == [
        "span \"modulenotfounderror: no module named 'aspose.widget'\""
    ]


def test_a_sentence_without_anchors_is_stated_by_a_restatement_not_only_by_a_quotation() -> None:
    restated = "The Python version needed is 3.10 or later for running this product."
    unit = "Requires Python 3.10 or later."
    assert unstated(unit, README) == []
    absent = "Every widget emitted by the converter keeps its original colour table intact."
    assert len(unstated(absent, README)) == 1
    # Control: the restatement above shares most content words with a README block.
    assert unstated(restated, README) == []


def test_version_numbers_and_links_are_compared_after_flattening_markup() -> None:
    assert unstated("See [the docs](https://pypi.org/project/reportlab) for 3.10.", README) == []
    assert unstated("The release 26.8.0 is not in the tree.", README) == ["number '26.8.0'"]


def test_a_code_block_is_judged_line_by_line_without_comments() -> None:
    block = '```bash\n# install\npip install "aspose-widget[pdf]"\n```'
    assert unstated(block, README, kind="code_block") == []
    other = '```bash\npip install "aspose-widget[docx]"\n```'
    assert unstated(other, README, kind="code_block") == ['pip install "aspose-widget[docx]"']


def test_a_list_is_judged_item_by_item() -> None:
    items = "- Saves to PDF.\n- Streams large documents lazily through `Widget.stream()` calls."
    assert unstated(items, README, kind="list") == ["span 'widget.stream()'"]
