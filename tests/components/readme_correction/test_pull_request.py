"""The pull request text of a correction, written from the bundle, against the reviewer's drafts.

Three drafts (a version fix, two structure fixes, a diagram redraw) are the golden shapes: a title
that names the change, a lead that says why, one bullet per edit with the quoted before and after
and the evidence fact with its status, exact counts from the validation delta, how to review and how
to decline. None of the generic composer's overclaims may appear: "every statement checked", "no
verification counts", a heading diff.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.propose.pull_request import load_pull_request_evidence
from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.components.readme_correction.settle import correct_settled

NL = chr(10)
FORBIDDEN = (
    "Every statement",
    "No verification counts",
    "reconciled",
    "Refreshes the README",
    "sections updated",
    "Rewritten sections",
)

VERSION = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0",
        "```",
        "",
        "```xml",
        "<artifactId>aspose-3d-foss</artifactId>",
        "```",
        "",
        "```groovy",
        "implementation 'org.aspose:aspose-3d-foss'",
        "```",
        "",
        "## License",
        "",
        "MIT.",
        "",
    ]
)
STRUCTURE = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
        "```",
        "",
        "```xml",
        "<artifactId>aspose-3d-foss</artifactId>",
        "```",
        "",
        "```groovy",
        "implementation 'org.aspose:aspose-3d-foss'",
        "```",
        "",
        "# Requires **Java 21+**",
        "",
        "<details>",
        "<summary>More commands</summary>",
        "",
        "```bash",
        "mvn test",
        "```",
        "",
        "## License",
        "",
        "MIT.",
        "",
    ]
)
DIAGRAM = NL.join(
    [
        "flowchart TD",
        '  subgraph StartingPoints["Starting Points"]',
        "    direction LR",
        '    i1["An existing OBJ, STL, or 3MF file"]',
        "  end",
        '  PRODUCT["Aspose.3D FOSS for Java"]',
        '  subgraph Capabilities["Core Capabilities"]',
        "    direction LR",
        '    subgraph capl[" "]',
        "      direction TB",
        '      c1["Scene-graph construction and traversal"]',
        '      c2["Mesh authoring and editing"]',
        '      c3["Parameterized primitive geometry"]',
        "    end",
        '    subgraph capr[" "]',
        "      direction TB",
        '      c4["Lambert, Phong, and PBR material assignment"]',
        '      c5["Polygon triangulation"]',
        '      c6["Keyframe animation and skeletal pose data"]',
        "    end",
        "  end",
        '  subgraph Outputs["Outputs"]',
        "    direction TB",
        '    o1["OBJ, STL, or 3MF file"]',
        "  end",
        "  StartingPoints --> PRODUCT --> Capabilities --> Outputs",
        "",
    ]
)
DIAGRAM_ONLY = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## At a Glance",
        "",
        "```mermaid",
        DIAGRAM + "```",
        "",
        "## License",
        "",
        "MIT.",
        "",
    ]
)


def complete(readme: str, *, installation: bool = False) -> str:
    """``readme`` with the other template sections present, so only the edit under test is made."""
    tail = ["## Dependencies", "", "None.", "", "## Development and Testing", "", "Run it.", ""]
    head = ["## Installation", "", "```xml", "<artifactId>aspose-3d-foss</artifactId>", "```", ""]
    head += ["```groovy", "implementation 'org.aspose:aspose-3d-foss'", "```", ""]
    head = head if installation else []
    return readme.replace("## License", NL.join([*head, *tail, "## License"]), 1)


def compose(
    tmp_path: Path, make_context: Any, readme: str, render: dict[str, Any] | None = None
) -> Any:
    readme = complete(readme, installation="## Installation" not in readme)
    ctx = make_context(readme)
    result, delta = correct_settled(ctx, readme.encode())
    directory = tmp_path / "bundle"
    files.write_bundle(ctx, readme.encode(), result, delta, directory, render=render)
    return compose_correction_pull_request(
        bundle=directory,
        repository="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        candidate_hash="c" * 64,
        source_revision="a" * 40,
        policy_version="p1",
    )


def test_a_version_fix_names_the_release_the_lines_and_the_evidence(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, VERSION)
    assert (
        content.title == "docs(readme): show the current release (26.7.0) in the install snippets"
    )
    body = content.body
    assert "The README pins `26.5.0` (README.md line 6)" in body
    assert "lists `26.7.0` as the current release" in body
    assert "- README.md line 6: `26.5.0` -> `26.7.0`" in body
    assert "evidence: `package:name` (SUPPORTED)" in body
    assert "`package:published_version` (SUPPORTED): 26.7.0" in body
    assert "0 introduced failure(s)" in body
    assert "(idempotent: yes)" in body and "(model calls: 0)" in body
    assert "### How to review" in body and "### How to decline" in body
    assert "- candidate_hash: " + "c" * 64 in body and "- kind: correction" in body
    for phrase in FORBIDDEN:
        assert phrase not in body and phrase not in content.title


def test_two_structure_fixes_are_each_a_bullet_with_their_line_and_a_title_that_says_so(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, STRUCTURE)
    assert content.title.startswith("docs(readme): ")
    assert "demote a stray second H1" in content.title
    assert "close an unclosed <details> block" in content.title
    body = content.body
    assert "no wording changes" in body
    assert (
        "- README.md line 9: `# Requires **Java 21+**` -> `## Requires **Java 21+**`" in body
        or ("second_h1" in body or "Requires **Java 21+**" in body)
    )
    assert "inserted `</details>` before line" in body
    assert body.count("  - evidence: `README.md:") >= 2
    for phrase in FORBIDDEN:
        assert phrase not in body


def test_a_diagram_redraw_says_what_is_unchanged_and_claims_no_render_without_a_record(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, DIAGRAM_ONLY)
    assert content.title == "docs(readme): lay out the At a Glance diagram left to right"
    body = content.body
    assert "is drawn top-down (`flowchart TD`)" in body
    assert "redrawn left to right so text no longer clips" in body
    assert "All 9 labels, the 3 group titles and the chain" in body
    assert "(compared by script)" in body and "`flowchart LR`" in body
    assert "headless browser" not in body  # no render record, so no claim about one
    for phrase in FORBIDDEN:
        assert phrase not in body


def test_a_recorded_render_is_reported_with_its_exact_counts(
    tmp_path: Path, make_context: Any
) -> None:
    render = {
        "status": "verified",
        "releases": ["11.17.2", "11.4.1", "11.12.0", "12.1.0"],
        "fonts": 6,
        "browser": "Chrome/154",
        "diagrams": [{"horizontal": True, "clipped_fonts": 0, "word_splits": 0, "problems": 0}],
    }
    body = compose(tmp_path, make_context, DIAGRAM_ONLY, render).body
    assert "Mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0" in body
    assert "horizontal on every release, 0 clipped labels, 0 words split across lines" in body
    unverified = {"status": "not_run", "reason": "no renderer installed"}
    assert (
        "headless browser"
        not in compose(tmp_path / "again", make_context, DIAGRAM_ONLY, unverified).body
    )


def test_the_regenerated_candidates_composer_refuses_a_correction_bundle(
    tmp_path: Path, make_context: Any
) -> None:
    compose(tmp_path, make_context, VERSION)
    with pytest.raises(ValueError, match="correction bundle"):
        load_pull_request_evidence(tmp_path / "bundle")
    document = json.loads(
        (tmp_path / "bundle" / files.CORRECTIONS_NAME).read_text(encoding="utf-8")
    )
    assert document["send"]["pr_order"] == 1  # a content correction goes first
