"""The deterministic model of the two defects measured on the live READMEs."""

from __future__ import annotations

from collections import Counter

from repository_presenter.components.readme_diagram import (
    Glance,
    balanced_columns,
    build_body,
    lint_source,
    parse,
    rebuild_body,
)
from repository_presenter.components.readme_diagram.lint import (
    CLIP_AUTO_WRAP,
    CLIP_HTML_LABELS,
    COLUMN_ORDER,
    GROUP_LAID_AS_ROW,
    LABEL_ENTITY_RISK,
    LABEL_MARKUP_LOST,
    LABEL_TOKEN_WIDE,
    NOT_CANONICAL,
    ORDER_UNPINNED,
    ORIENTATION_VERTICAL,
    UNRECOGNIZED,
)

CAPS = tuple(f"Capability {n} of the product" for n in range(1, 7))
GLANCE = Glance(
    "Aspose.Cells FOSS for Go",
    ("An existing XLSX workbook", "CSV files"),
    balanced_columns(CAPS),
    ("XLSX workbooks", "CSV files"),
)


def test_every_live_diagram_stacks_its_blocks_and_draws_clippable_html_labels(
    live: dict[str, str],
) -> None:
    counts: Counter[str] = Counter()
    for source in live.values():
        report = lint_source(source)
        assert report.recognized and not report.conforming
        counts.update(report.codes)
    # The measured "before": 32 live diagrams, every one of them with both families of defect.
    assert counts[ORIENTATION_VERTICAL] == 32
    assert counts[CLIP_HTML_LABELS] == 32
    assert counts[GROUP_LAID_AS_ROW] == 32
    assert counts[ORDER_UNPINNED] == 32
    assert counts[CLIP_AUTO_WRAP] == 32
    assert counts[COLUMN_ORDER] == 23
    assert counts[LABEL_MARKUP_LOST] == 1  # Cells for Rust: Vec<u8> loses <u8> in the live render
    assert set(counts) == {
        ORIENTATION_VERTICAL,
        CLIP_HTML_LABELS,
        GROUP_LAID_AS_ROW,
        ORDER_UNPINNED,
        CLIP_AUTO_WRAP,
        COLUMN_ORDER,
        LABEL_MARKUP_LOST,
    }


def test_after_the_rebuild_no_live_diagram_has_a_defect(live: dict[str, str]) -> None:
    advisories: Counter[str] = Counter()
    for name, source in live.items():
        report = lint_source(rebuild_body(source))
        assert report.conforming, (name, report.defects)
        advisories.update(advisory.code for advisory in report.advisories)
    # What a rewrite must keep, the label's own text: it is reported, never changed.
    assert advisories[LABEL_ENTITY_RISK] == 1
    # With the wrapping width at 400 px no live label holds a single word wider than it.
    assert advisories[LABEL_TOKEN_WIDE] == 0


def test_a_diagram_built_by_the_builder_is_conforming() -> None:
    report = lint_source(build_body(GLANCE))
    assert report.recognized and report.conforming and report.defects == ()


def test_each_defect_is_found_by_the_one_edit_that_causes_it() -> None:
    body = build_body(GLANCE)
    assert lint_source(body.replace("flowchart LR", "flowchart TD")).codes == {ORIENTATION_VERTICAL}
    assert lint_source(
        body.replace(
            '"htmlLabels": false, "flowchart": {"htmlLabels": false',
            '"flowchart": {"htmlLabels": false',
        )
    ).codes == {CLIP_HTML_LABELS}
    assert lint_source(
        body.replace('"flowchart": {"htmlLabels": false', '"flowchart": {"htmlLabels": true')
    ).codes == {CLIP_HTML_LABELS}
    unpinned = body.replace("    c1 ~~~ c2 ~~~ c3\n", "").replace("      c1 ~~~ c2 ~~~ c3\n", "")
    assert ORDER_UNPINNED in lint_source(unpinned).codes
    assert GROUP_LAID_AS_ROW in lint_source(unpinned).codes
    natural = (
        body.replace('subgraph capr[" "]', "subgraph TMP")
        .replace('subgraph capl[" "]', 'subgraph capr[" "]')
        .replace("subgraph TMP", 'subgraph capl[" "]')
    )
    assert COLUMN_ORDER in lint_source(natural).codes or lint_source(natural).conforming is False


def test_a_label_the_renderer_would_re_wrap_is_a_defect_and_one_long_word_is_not() -> None:
    body = build_body(GLANCE)
    one_long_line = body.replace(
        'c1["Capability 1<br/>of the product"]',
        'c1["Capability 1 of the product and more words to push it past two hundred pixels"]',
    )
    assert CLIP_AUTO_WRAP in lint_source(one_long_line).codes
    word = "W" * 30
    report = lint_source(body.replace('c1["Capability 1<br/>of the product"]', f'c1["{word}"]'))
    assert CLIP_AUTO_WRAP not in report.codes
    assert LABEL_TOKEN_WIDE in {advisory.code for advisory in report.advisories}


def test_a_raw_angle_bracket_is_markup_the_renderer_drops() -> None:
    body = build_body(GLANCE).replace("Capability 1", "Vec<u8> 1")
    assert LABEL_MARKUP_LOST in lint_source(body).codes


def test_a_diagram_that_only_differs_in_spacing_is_not_canonical() -> None:
    body = build_body(GLANCE).replace('"nodeSpacing": 22', '"nodeSpacing": 99')
    report = lint_source(body)
    assert report.codes == {NOT_CANONICAL}
    assert "nodeSpacing" in report.defects[0].detail


def test_whitespace_and_blank_lines_do_not_make_a_diagram_non_canonical() -> None:
    body = build_body(GLANCE)
    padded = "\n\n".join(body.splitlines()) + "   \n\n"
    assert lint_source(padded).conforming


def test_a_mermaid_diagram_that_is_not_an_at_a_glance_chain_is_unrecognized_not_defective() -> None:
    for source in ("sequenceDiagram\n  A->>B: hi\n", "flowchart LR\n  A --> B\n", ""):
        report = lint_source(source)
        assert not report.recognized and not report.conforming
        assert report.codes == {UNRECOGNIZED}


def test_the_rebuild_of_a_diagram_changes_none_of_its_words(live: dict[str, str]) -> None:
    for name, source in live.items():
        before = parse(source).glance
        after = parse(rebuild_body(source)).glance
        assert after == before, name
        assert after.labels == before.labels and after.titles == before.titles
