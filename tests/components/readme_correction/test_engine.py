"""The engine end to end on synthetic facts: confined, deterministic, idempotent, model-free."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from repository_presenter.components.readme_correction.detectors import load_detectors
from repository_presenter.components.readme_correction.engine import correct, is_stable
from repository_presenter.components.readme_correction.model import Context

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
        "broken_link",
        "claim_identity",
        "claim_license",
        "claim_public_types",
        "claim_publication",
        "claim_test_files",
        "claim_version",
        "missing_sections",
    ]


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
        "## Dependencies\n\nNone.\n\n## Development and Testing\n\n3 test files.\n\n"
        "## License\n\nMIT License.\n"
    )
    result = correct(make_context(clean))
    assert result.edits == [] and result.corrected == clean


def test_the_correction_path_loads_no_model_client() -> None:
    code = (
        "import sys\n"
        "import repository_presenter.components.readme_correction.engine as engine\n"
        "engine.load_detectors()\n"
        "banned = ('repository_presenter.core.llm.transport', 'openai')\n"
        "bad = [m for m in sys.modules if m.startswith(banned)]\n"
        "sys.exit(1 if bad else 0)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
