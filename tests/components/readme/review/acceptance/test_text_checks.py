"""Each deterministic predicate passes a conforming README and fails a violating one."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.review.acceptance.text_checks import (
    TEXT_PREDICATES,
    Outcome,
    scan,
)

PASS = Outcome.PASS
FAIL = Outcome.FAIL
NA = Outcome.NOT_APPLICABLE


def _run(name: str, readme: str) -> Outcome:
    return TEXT_PREDICATES[name](scan(readme)).outcome


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        ("# Demo\n\ntext\n", PASS),
        ("# Demo\n\n# Second\n", FAIL),
        ("## Only a subheading\n", FAIL),
        ("```\n# not a heading\n```\n# Demo\n", PASS),
    ],
)
def test_single_h1(readme: str, expected: Outcome) -> None:
    assert _run("single_h1", readme) == expected


_BADGE = "![Python](https://img.shields.io/badge/python-3.12-blue.svg)"
_BADGE2 = "![MIT](https://img.shields.io/badge/license-MIT-blue.svg)"
_BANNER = "[![Demo](https://products.aspose.org/media/banner.png)](https://products.aspose.org/demo/python/)"


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        (f"# Demo\n\n{_BADGE} {_BADGE2}\n\ntext\n", PASS),
        (f"# Demo\n\n{_BADGE}\n\n{_BADGE2}\n\ntext\n", FAIL),
        (f"# Demo\n\n{_BADGE} {_BADGE}\n\ntext\n", FAIL),
        (f"# Demo\n\n{_BADGE}\n\n{_BANNER}\n\ntext\n", PASS),
        ("# Demo\n\ntext only\n", PASS),
    ],
)
def test_single_badge_row(readme: str, expected: Outcome) -> None:
    assert _run("single_badge_row", readme) == expected


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        ("# Demo\n\nAn Enterprise Edition is linked from https://products.aspose.com/x\n", PASS),
        ("# Demo\n\nA commercial edition is also available.\n", FAIL),
        ("# Demo\n\nThe On-Premise edition runs locally.\n", FAIL),
        ("# Demo\n\nThe paid version adds features.\n", FAIL),
        ("# Demo\n\nThe full version is at https://products.aspose.com/x\n", FAIL),
        ("# Demo\n\n```\n# a commercial edition in code\n```\n", NA),
        ("# Demo\n\nNo vendor is mentioned.\n", NA),
    ],
)
def test_edition_name(readme: str, expected: Outcome) -> None:
    assert _run("edition_name", readme) == expected


def test_implementation_label_fails_on_the_named_label_and_ignores_code() -> None:
    assert _run("implementation_label", "# Demo\n\n### Preserved repository details\n") == FAIL
    assert (
        _run("implementation_label", "# Demo\n\n```\nPreserved repository details\n```\n") == PASS
    )


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("The source revision is pinned.", FAIL),
        ("Each isolated build runs offline.", FAIL),
        ("A registry receipt backs the install.", FAIL),
        ("The provider calls are logged.", FAIL),
        ("Validation status is green.", FAIL),
        ("Install it with pip and import it.", PASS),
    ],
)
def test_assurance_narration(sentence: str, expected: Outcome) -> None:
    assert _run("assurance_narration", f"# Demo\n\n{sentence}\n") == expected


def test_assurance_narration_inside_a_code_fence_is_not_visitor_text() -> None:
    assert _run("assurance_narration", "# Demo\n\n```\nprovider calls\n```\n") == PASS


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        ("# Demo\n\n## Other platforms\n\nmore\n", FAIL),
        ("# Demo\n\n## Other Platforms\n", FAIL),
        ("# Demo\n\n## Platforms\n", PASS),
    ],
)
def test_other_platforms_section(readme: str, expected: Outcome) -> None:
    assert _run("other_platforms_section", readme) == expected


_OPENING = "Demo reads and writes files in Python applications for data teams."


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        (f"# Demo\n\n{_OPENING}\n\nSee https://products.aspose.com/x\n", PASS),
        (f"# Demo\n\n{_OPENING} See https://products.aspose.com/x\n", PASS),
        ("# Demo\n\nDemo at https://products.aspose.com/x reads files.\n", FAIL),
        (f"# Demo\n\n{_BANNER}\n\n{_OPENING}\n", PASS),
        (f"# Demo\n\n[Aspose](https://www.aspose.com/)\n\n{_OPENING}\n", FAIL),
        (
            f"# Demo\n\n[![x](https://products.aspose.org/m.png)](https://products.aspose.com/d/)"
            f"\n\n{_OPENING}\n",
            FAIL,
        ),
        (f"# Demo\n\n[Docs](https://docs.aspose.org/demo/)\n\n{_OPENING}\n", FAIL),
        # Only the exact banner shape is exempt: products.aspose.org/{family}/{platform}/.
        (f"# Demo\n\n[Aspose](https://products.aspose.org/demo/)\n\n{_OPENING}\n", FAIL),
        (
            f"# Demo\n\n[![x](https://products.aspose.org/media/demo/b.png)]"
            f"(https://products.aspose.org/demo/python/extra)\n\n{_OPENING}\n",
            FAIL,
        ),
        (
            f"# Demo\n\n[![x](https://products.aspose.org/media/demo/b.png)]"
            f"(https://products.aspose.org/demo/python/)\n\n{_OPENING}\n",
            PASS,
        ),
        ("# Demo\n\n## Navigation\n\n- [A](#a)\n", NA),
        ("## No H1 here\n\n" + _OPENING + "\n", NA),
    ],
)
def test_promotion_after_product(readme: str, expected: Outcome) -> None:
    assert _run("promotion_after_product", readme) == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("This project is licensed under the [MIT](LICENSE) license. It permits reuse.", PASS),
        ("[MIT](LICENSE)", FAIL),
        ("", FAIL),
    ],
)
def test_license_prose(body: str, expected: Outcome) -> None:
    assert _run("license_prose", f"# Demo\n\n## License\n\n{body}\n") == expected


def test_license_prose_fails_without_a_license_heading() -> None:
    assert _run("license_prose", "# Demo\n\ntext\n") == FAIL


@pytest.mark.parametrize(
    ("heading_body", "expected"),
    [
        ("See [NOTICE.md](NOTICE.md) for details.", PASS),
        ("See [`NOTICE.md`](NOTICE.md) for details.", FAIL),
        ("See [notices](https://example.org/notice) for details.", FAIL),
    ],
)
def test_third_party_notices_link(heading_body: str, expected: Outcome) -> None:
    readme = f"# Demo\n\n## Third-Party Notices\n\n{heading_body}\n"
    assert _run("third_party_notices", readme) == expected


def test_third_party_notices_is_not_applicable_without_its_heading() -> None:
    assert _run("third_party_notices", "# Demo\n\ntext\n") == NA


def test_visible_core_sections_fails_when_installation_is_collapsed() -> None:
    collapsed = (
        "# Demo\n\n<details>\n\n## Installation\n\n```bash\npip install x\n```\n\n</details>\n"
    )
    assert _run("visible_core_sections", collapsed) == FAIL


def test_visible_core_sections_passes_when_only_secondary_material_is_collapsed() -> None:
    readme = (
        "# Demo\n\n## Installation\n\nx\n\n<details>\n<summary>More</summary>\n\n"
        "### Extra example\n\n</details>\n"
    )
    assert _run("visible_core_sections", readme) == PASS


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        ("# Demo\n\n## Additional Examples\n\n### Render a barcode to SVG\n", PASS),
        ("# Demo\n\n## Additional Examples\n\n### Example 2\n", FAIL),
        ("# Demo\n\n## Additional Examples\n\n### Render\n\n### Render\n", FAIL),
        ("# Demo\n\n## Additional Examples\n\n### Run it\n\nThe syntax check passed.\n", FAIL),
        ("# Demo\n\n## Additional Examples\n\n### Run it\n\nA static API check ran.\n", FAIL),
        ("# Demo\n\n## Additional Examples\n\n### Run\n\nNon-execution example.\n", FAIL),
        ("# Demo\n\n## Installation\n\nThe syntax check passed.\n", NA),
        ("# Demo\n\ntext\n", NA),
    ],
)
def test_example_headings(readme: str, expected: Outcome) -> None:
    assert _run("example_headings", readme) == expected


@pytest.mark.parametrize(
    ("readme", "expected"),
    [
        ("# Demo\n\n```python\nx = 1\n```\n", PASS),
        ("# Demo\n\n```\nx = 1\n```\n", FAIL),
        ("# Demo\n\na\n\n\nb\n", FAIL),
        ("# Demo\n\n```python\na\n\n\nb\n```\n", PASS),
        ("# Demo\n\nplain text\n", PASS),
    ],
)
def test_fences_and_spacing(readme: str, expected: Outcome) -> None:
    assert _run("fences_and_spacing", readme) == expected
