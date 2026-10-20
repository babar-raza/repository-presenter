"""The engine end to end on synthetic facts: confined, deterministic, idempotent, model-free."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction.detectors import load_detectors
from repository_presenter.components.readme_correction.engine import correct, is_stable
from repository_presenter.components.readme_correction.model import Context

NL = chr(10)

README = """# Product

The maintainers wrote this opening and every sentence below it.

## Key Capabilities

- Reads files; see [the notes](upstream-issues.md).

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

## Scope and Limitations

The suite has 18 test files and the library is licensed under the Apache License 2.0.
Do not touch this unrelated sentence, version 26.5.0 of the spec, or this link [x](LICENSE).
"""
TREE = (
    "README.md",
    "LICENSE",
    "docs/upstream-issues.md",
    "src/test/AATests.java",
    "src/test/BBTests.java",
    "src/test/CCTests.java",
)


def build(make_context: Any, make_facts: Any, make_fact: Any) -> Context:
    broken = make_fact(
        "link_target:001",
        "upstream-issues.md",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "line 7; relative; text 'the notes'"),
            ("README.md", "MISSING: tree does not contain upstream-issues.md"),
        ),
    )
    return make_context(README, make_facts(broken), tree=TREE)


def test_every_registered_detector_is_loaded_by_name() -> None:
    assert sorted(load_detectors()) == [
        "add_dependency_groups",
        "add_dev_commands",
        "add_doc_links",
        "add_install_forms",
        "add_version_badge",
        "at_a_glance_diagram",
        "broken_link",
        "claim_identity",
        "claim_license",
        "claim_public_types",
        "claim_publication",
        "claim_test_files",
        "claim_version",
        "failing_example",
        "missing_sections",
        "report_gaps",
        "second_h1",
        "stale_phrase",
        "stray_fence",
        "unclosed_details",
        "unpublished_install_command",
    ]


@pytest.mark.usefixtures("reenabled")
def test_each_kind_of_correction_is_made_and_nothing_else_changes(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = build(make_context, make_facts, make_fact)
    result = correct(ctx)
    kinds = sorted((e.kind, e.detector) for e in result.edits)
    assert kinds == [
        ("BROKEN_LINK", "broken_link"),
        ("FALSE_CLAIM_FIX", "claim_license"),
        ("FALSE_CLAIM_FIX", "claim_test_files"),
        ("FALSE_CLAIM_FIX", "claim_version"),
        ("MISSING_INFO", "add_install_forms"),
        ("MISSING_SECTION", "missing_sections"),
        ("MISSING_SECTION", "missing_sections"),
        ("MISSING_SECTION", "missing_sections"),
        ("MISSING_SECTION", "missing_sections"),
    ]
    for old, new in (
        ("26.5.0", "26.7.0"),
        ("(upstream-issues.md)", "(docs/upstream-issues.md)"),
        ("18 test files", "3 test files"),
        ("Apache License 2.0", "MIT License"),
    ):
        assert old in README and new in result.corrected
    # The unrelated maintainer sentence, the spec's version and the working link stay as written.
    for kept in (
        "Do not touch this unrelated sentence, version 26.5.0 of the spec, or this link "
        "[x](LICENSE).",
        "The maintainers wrote this opening and every sentence below it.",
    ):
        assert kept in result.corrected
    # Every changed line of the original is a line some edit names.
    edited = {ctx.readme.count("\n", 0, e.start) + 1 for e in result.edits if e.original}
    removed = [
        number
        for number, line in enumerate(README.splitlines(), start=1)
        if line not in result.corrected.splitlines()
    ]
    assert set(removed) <= edited


def test_a_second_run_is_byte_identical_and_a_run_on_the_output_finds_nothing(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = build(make_context, make_facts, make_fact)
    result = correct(ctx)
    assert is_stable(ctx, result) == (True, True)
    again = correct(Context(ctx.entry, ctx.facts, result.corrected, ctx.tree_paths))
    assert again.edits == [] and again.corrected == result.corrected


def test_a_conformant_readme_yields_no_edit_and_no_diff(make_context: Any) -> None:
    clean = (
        "# P\n\n## Installation\n\n"
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n\n"
        "```xml\n<dependency>\n  <artifactId>aspose-3d-foss</artifactId>\n</dependency>\n```\n\n"
        "```groovy\nimplementation 'org.aspose:aspose-3d-foss:26.7.0'\n```\n\n"
        "## Dependencies\n\nNone. Requires Java 21.\n\n"
        "## Development and Testing\n\n3 test files.\n\n"
        "## License\n\nMIT License.\n"
    )
    result = correct(make_context(clean))
    assert result.edits == [] and result.corrected == clean


def test_the_correction_path_names_no_model_client_and_reaches_no_network(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Zero provider calls by construction. The shared validator's own import graph may load a
    client library, so what is held is that this package never names one and that a whole run
    (detectors, settle, validation) opens no socket - a provider call would need one."""
    import ast
    import socket
    from pathlib import Path

    import repository_presenter.components.readme_correction as package

    banned = ("openai", "anthropic", "httpx", "requests", "repository_presenter.core.llm")
    for path in Path(package.__file__).parent.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not [n for n in names if n.startswith(banned)], (path.name, names)

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the correction path opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    from repository_presenter.components.readme_correction.settle import correct_settled

    readme = "# Aspose.3D FOSS for Java" + NL + NL + "## Installation" + NL + NL + "x" + NL
    ctx = make_context(readme)
    result, delta = correct_settled(ctx, readme.encode())
    assert delta["introduced"] == [] and result.corrected
