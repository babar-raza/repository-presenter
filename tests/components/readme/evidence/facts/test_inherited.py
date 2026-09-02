"""The inherited-unit inventory: one unit per top-level block, exact source, located by lines."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts.inherited import (
    inherited_unit_facts,
    inventory_units,
)
from repository_presenter.components.readme.evidence.facts.records import FactsDocument
from support import REPO_ROOT

README = """# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An open-source 3D file format library.

## Installation

```bash
pip install aspose-3d-foss
```

## Key capabilities

- Load and save **FBX**, glTF, and STL
  - nested detail line
- Build scenes programmatically

| Format | Read | Write |
|---|---|---|
| FBX | yes | yes |

<details>
<summary>More</summary>
</details>

> A quote about the library.

### Scene graph (`aspose.threed`)

Nodes form a tree. See `Scene`.

---

## License

MIT
"""


def test_every_top_level_block_becomes_one_unit_in_order() -> None:
    units = inventory_units(README)
    assert [(u.ordinal, u.unit_type) for u in units] == [
        (1, "heading"),
        (2, "badge_row"),
        (3, "paragraph"),
        (4, "heading"),
        (5, "code_block"),
        (6, "heading"),
        (7, "list"),
        (8, "table"),
        (9, "html_block"),
        (10, "blockquote"),
        (11, "heading"),
        (12, "paragraph"),
        (13, "heading"),
        (14, "paragraph"),
    ]


def test_units_carry_exact_source_lines_and_heading_paths() -> None:
    units = {u.ordinal: u for u in inventory_units(README)}
    assert units[1].source == "# Aspose.3D FOSS for Python"
    assert (units[1].heading_level, units[1].section) == (1, "")
    assert units[2].source.startswith("[![PyPI](https://img.shields.io")
    assert units[5].source == "```bash\npip install aspose-3d-foss\n```"
    assert (units[5].start_line, units[5].end_line) == (10, 12)
    assert units[5].section == "Aspose.3D FOSS for Python > Installation"
    assert units[7].source == (
        "- Load and save **FBX**, glTF, and STL\n"
        "  - nested detail line\n"
        "- Build scenes programmatically"
    )
    assert (units[7].start_line, units[7].end_line) == (16, 18)
    assert units[8].source.startswith("| Format | Read | Write |")
    assert units[9].source == "<details>\n<summary>More</summary>\n</details>"
    assert units[10].source == "> A quote about the library."
    assert units[11].section == "Aspose.3D FOSS for Python > Key capabilities"
    assert (
        units[12].section
        == "Aspose.3D FOSS for Python > Key capabilities > Scene graph (`aspose.threed`)"
    )
    assert units[13].section == "Aspose.3D FOSS for Python"
    assert units[14].source == "MIT"


def test_a_paragraph_with_prose_and_an_image_is_not_a_badge_row() -> None:
    units = inventory_units("![logo](logo.png) The library logo above.\n")
    assert [u.unit_type for u in units] == ["paragraph"]
    units = inventory_units("![a](a.svg)\n![b](b.svg)\n")
    assert [u.unit_type for u in units] == ["badge_row"]


def test_crlf_and_empty_documents_are_handled() -> None:
    units = inventory_units("# Title\r\n\r\nText line.\r\n")
    assert [(u.unit_type, u.source) for u in units] == [
        ("heading", "# Title"),
        ("paragraph", "Text line."),
    ]
    assert inventory_units("") == []
    assert inventory_units("\n\n---\n\n") == []


def test_facts_are_stable_ordinal_ids_with_located_evidence() -> None:
    facts = inherited_unit_facts("README.md", README.encode("utf-8"))
    assert [f.id for f in facts][:3] == [
        "inherited_unit:001.heading",
        "inherited_unit:002.badge_row",
        "inherited_unit:003.paragraph",
    ]
    code = next(f for f in facts if f.id == "inherited_unit:005.code_block")
    assert code.value == "```bash\npip install aspose-3d-foss\n```"
    assert code.evidence[0].path == "README.md"
    assert code.evidence[0].detail == (
        "lines 10-12; code_block; under Aspose.3D FOSS for Python > Installation"
    )
    assert inherited_unit_facts("README.md", README.encode("utf-8")) == facts

    document = FactsDocument("o/Aspose.X-FOSS-for-Go", "a" * 40, tuple(facts))
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []
