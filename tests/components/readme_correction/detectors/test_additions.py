"""Additions: verified information the live README lacks, appended to a section it already has."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
)
from repository_presenter.components.readme_correction.detectors.additions import (
    add_dev_commands,
    add_doc_links,
    add_install_forms,
    add_version_badge,
)
from repository_presenter.components.readme_correction.detectors.sections import missing_sections
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import (
    MISSING_INFO,
    Context,
    Edit,
    InvalidEditError,
)

WORDS = "aspose-words-foss/Aspose.Words-FOSS-for-Python"


def applied(ctx: Context, edits: Any) -> str:
    ordered = sorted(edits, key=lambda e: (e.start, e.order))
    corrected, spans = apply_edits(ctx.readme, ordered)
    assert confinement_violations(ctx.readme, corrected, ordered, spans) == []
    return corrected


def commands(make_fact: Any) -> list[Any]:
    return [
        make_fact("build_test_asset:build-command", "mvn -B verify", evidence=(("pom.xml", "x"),)),
        make_fact("build_test_asset:test-command", "mvn test", evidence=(("pom.xml", "x"),)),
        make_fact(
            "build_test_asset:ci-matrix",
            "os=ubuntu-latest,windows-latest;java=17,21",
            evidence=((".github/workflows/ci.yml", "matrix"),),
        ),
    ]


DEV_README = "# P\n\n## Development and Testing\n\nRun it the usual way.\n\n## License\n\nMIT.\n"


# ------------------------------------------------------------------------------ dev commands
@pytest.mark.usefixtures("reenabled")
def test_the_clones_build_and_test_commands_and_ci_matrix_are_appended_to_the_section(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(DEV_README, make_facts(*commands(make_fact)))
    (edit,) = add_dev_commands(ctx).edits
    assert edit.kind == MISSING_INFO and edit.original == "" and edit.start == edit.end
    corrected = applied(ctx, [edit])
    assert corrected.startswith("# P\n\n## Development and Testing\n\nRun it the usual way.\n\n")
    assert "```bash\nmvn -B verify\nmvn test\n```" in corrected
    assert "ci.yml" in corrected and "ubuntu" in corrected.lower()
    assert corrected.index("mvn test") < corrected.index("## License")
    assert set(edit.fact_ids) == {
        "build_test_asset:build-command",
        "build_test_asset:test-command",
        "build_test_asset:ci-matrix",
    }


def test_nothing_is_added_that_the_readme_already_says(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    said = DEV_README.replace(
        "Run it the usual way.",
        "Run `mvn -B verify` then mvn test; CI is .github/workflows/ci.yml.",
    )
    ctx = make_context(said, make_facts(*commands(make_fact)))
    assert add_dev_commands(ctx).edits == ()


def test_dev_additions_are_idempotent_and_skip_a_missing_or_unsafe_section(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(DEV_README, make_facts(*commands(make_fact)))
    after = make_context(
        applied(ctx, add_dev_commands(ctx).edits), make_facts(*commands(make_fact))
    )
    assert add_dev_commands(after).edits == ()
    no_section = make_context("# P\n\n## License\n\nMIT.\n", make_facts(*commands(make_fact)))
    assert add_dev_commands(no_section).edits == ()  # missing_sections owns a whole new section
    swallowed = DEV_README.replace("Run it", "<details>\nRun it")
    assert add_dev_commands(make_context(swallowed, make_facts(*commands(make_fact)))).edits == ()


def test_a_suite_size_is_never_added_where_the_readme_states_none(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(DEV_README, make_facts())  # the base facts carry a 3-file suite
    assert add_dev_commands(ctx).edits == ()


# ----------------------------------------------------------------------------- install forms
INSTALL_README = (
    "# P\n\n## Installation\n\n```bash\nmvn dependency:get "
    "-Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n\n## License\n\nMIT.\n"
)


def test_maven_and_gradle_forms_are_added_when_only_the_command_line_is_shown(
    make_context: Any,
) -> None:
    ctx = make_context(INSTALL_README)
    (edit,) = add_install_forms(ctx).edits
    corrected = applied(ctx, [edit])
    assert (
        "Or declare it in Maven:" in corrected
        and "<artifactId>aspose-3d-foss</artifactId>" in corrected
    )
    assert "implementation 'org.aspose:aspose-3d-foss:26.7.0'" in corrected
    assert corrected.count("mvn dependency:get") == 1  # the shown command is not repeated
    assert corrected.index("implementation") < corrected.index("## License")


def test_a_form_the_readme_already_shows_in_any_spelling_is_not_added(make_context: Any) -> None:
    shown = INSTALL_README.replace(
        "## License",
        "```xml\n<dependency>\n    <artifactId>aspose-3d-foss</artifactId>\n</dependency>\n```\n\n"
        '```kotlin\nimplementation("org.aspose:aspose-3d-foss:26.7.0")\n```\n\n## License',
    )
    assert add_install_forms(make_context(shown)).edits == ()


def test_an_install_command_stated_in_plain_text_counts_as_shown(make_context: Any) -> None:
    prose = (
        "# P\n\n## Installation\n\n"
        "Run mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0 "
        "and add the xml and groovy forms yourself.\n\n## License\n\nMIT.\n"
    )
    (edit,) = add_install_forms(make_context(prose)).edits
    assert "Or declare it in Maven:" in edit.replacement  # only the alternatives, not the command
    assert "mvn dependency:get" not in edit.replacement


def test_no_install_form_is_added_for_an_unpublished_source_install(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    source = make_fact(
        "install_command:maven",
        "git clone x && mvn install",
        attributes={"install_kind": "source"},
        evidence=(("pom.xml", None),),
    )
    assert add_install_forms(make_context(INSTALL_README, make_facts(source))).edits == ()


# --------------------------------------------------------------------------------- doc links
DOCS_README = (
    "# P\n\n## Documentation & Resources\n\n- **[API](https://example.com/api)** — reference.\n\n"
    "## License\n\nMIT.\n"
)
TREE = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    ".github/SECURITY.md",
    ".github/CODE_OF_CONDUCT.md",
    "docs/guide.md",
)


@pytest.mark.usefixtures("reenabled")
def test_files_the_tree_holds_are_linked_as_bullets_continuing_the_list(make_context: Any) -> None:
    ctx = make_context(DOCS_README, tree=TREE)
    (edit,) = add_doc_links(ctx).edits
    corrected = applied(ctx, [edit])
    assert "— reference.\n- **[Changelog](CHANGELOG.md)** — release history.\n" in corrected
    assert "- **[Security policy](.github/SECURITY.md)**" in corrected
    assert "- **[Code of conduct](.github/CODE_OF_CONDUCT.md)**" in corrected
    assert "- **[Documentation](docs/)**" in corrected
    assert set(edit.locators) >= {"tree:CHANGELOG.md", "tree:CONTRIBUTING.md", "tree:docs/"}
    assert corrected.index("Documentation](docs/)") < corrected.index("## License")


@pytest.mark.usefixtures("reenabled")
def test_a_file_the_readme_names_anywhere_is_not_linked_again(make_context: Any) -> None:
    named = DOCS_README.replace("reference.", "reference. See CHANGELOG.md and docs/ too.")
    corrected = applied(
        make_context(named, tree=TREE), add_doc_links(make_context(named, tree=TREE)).edits
    )
    assert "[Changelog]" not in corrected and "[Documentation](docs/)" not in corrected
    assert "[Contributing guide](CONTRIBUTING.md)" in corrected


def test_a_file_the_tree_lacks_is_never_linked(make_context: Any) -> None:
    assert add_doc_links(make_context(DOCS_README, tree=("README.md", "LICENSE"))).edits == ()


@pytest.mark.usefixtures("reenabled")
def test_a_missing_docs_section_is_created_from_the_same_bullets(make_context: Any) -> None:
    readme = "# P\n\n## Installation\n\nx\n\n## License\n\nMIT.\n"
    result = missing_sections(make_context(readme, tree=TREE))
    docs = [e for e in result.edits if "Documentation & Resources" in e.replacement]
    (edit,) = docs
    assert edit.fact_ids == () and "tree:CHANGELOG.md" in edit.locators
    assert "- **[Changelog](CHANGELOG.md)** — release history." in edit.replacement


# --------------------------------------------------------------------------------- the badge
def python_facts(make_fact: Any) -> list[Any]:
    return [
        make_fact("package:name", "aspose-words-foss", evidence=(("pyproject.toml", None),)),
        make_fact(
            "package:published_version",
            "26.7.0",
            evidence=(("https://pypi.org/pypi/x/json", None),),
        ),
        make_fact(
            "install_command:pip",
            "pip install aspose-words-foss",
            attributes={"install_kind": "registry"},
            evidence=(("pyproject.toml", None), ("https://pypi.org/x", "package registry: found")),
        ),
    ]


def test_the_published_version_badge_leads_the_badge_row(make_context: Any, make_fact: Any) -> None:
    readme = (
        "# P\n\n[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)\n\n"
        "## Installation\n\nx\n"
    )
    ctx = make_context(readme, python_facts(make_fact), repository=WORDS)
    (edit,) = add_version_badge(ctx).edits
    corrected = applied(ctx, [edit])
    row = corrected.splitlines()[2]
    assert row.startswith("[![PyPI](https://img.shields.io/pypi/v/aspose-words-foss.svg)]")
    assert row.endswith("[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)")


def test_a_badge_is_added_under_the_title_when_there_is_no_row_and_not_when_one_exists(
    make_context: Any, make_fact: Any
) -> None:
    bare = make_context(
        "# P\n\nIntro.\n\n## Installation\n\nx\n", python_facts(make_fact), repository=WORDS
    )
    corrected = applied(bare, add_version_badge(bare).edits)
    assert corrected.startswith("# P\n\n[![PyPI]") and "Intro." in corrected
    has = make_context(
        "# P\n\n[![PyPI](https://img.shields.io/pypi/v/aspose-words-foss.svg)](x)\n\n## A\n",
        python_facts(make_fact),
        repository=WORDS,
    )
    assert add_version_badge(has).edits == ()


def test_no_badge_without_a_registry_published_version(make_context: Any, make_fact: Any) -> None:
    facts = python_facts(make_fact)[:1] + python_facts(make_fact)[2:]
    assert (
        add_version_badge(make_context("# P\n\nx\n\n## A\n", facts, repository=WORDS)).edits == ()
    )


# ------------------------------------------------------------------ the shape of an addition
@pytest.mark.parametrize(
    "overrides",
    [
        {"replacement": "\n## Sneaky\n\ntext\n"},  # a heading
        {"replacement": "x" * 4001},  # a rewrite, not an addition
        {"original": "x", "end": 1},  # replaces text
        {"fact_ids": (), "locators": ()},  # no evidence
    ],
)
def test_an_addition_that_is_not_a_short_headingless_insertion_cannot_be_built(
    overrides: dict[str, Any],
) -> None:
    fields: dict[str, Any] = {
        "kind": MISSING_INFO,
        "detector": "t",
        "start": 0,
        "end": 0,
        "original": "",
        "replacement": "\nnew line\n",
        "fact_ids": ("package:name",),
        "rationale": "r",
    }
    fields.update(overrides)
    with pytest.raises(InvalidEditError):
        Edit(**fields)


def test_a_fenced_hash_comment_is_not_a_heading() -> None:
    Edit(MISSING_INFO, "t", 0, 0, "", "```bash\n# build it\nmake\n```\n", ("package:name",), "r")


@pytest.mark.usefixtures("reenabled")
def test_an_engine_run_adds_and_a_second_run_over_the_output_adds_nothing(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(*commands(make_fact))
    ctx = make_context(
        INSTALL_README + "\n## Development and Testing\n\nRun it.\n", facts, tree=TREE
    )
    first = correct(ctx)
    assert {e.detector for e in first.edits} >= {"add_install_forms", "add_dev_commands"}
    again = correct(Context(ctx.entry, ctx.facts, first.corrected, ctx.tree_paths))
    assert again.edits == []


def test_prose_only_gaps_name_the_facts_that_would_fill_them(make_context: Any) -> None:
    result = missing_sections(make_context("# P\n\n## Installation\n\nx\n\n## License\n\nMIT.\n"))
    reasons = " ".join(f.reason for f in result.findings)
    assert "Key Capabilities is absent and needs authored prose" in reasons
    assert "would be filled from no SUPPORTED capability fact" in reasons
    assert "no SUPPORTED example fact" in reasons


# ------------------------------------------------------------------------ dependency groups
def dependency_facts(make_fact: Any) -> list[Any]:
    return [
        make_fact("dependency:fpdf2-2.7.5", "fpdf2>=2.7.5", evidence=(("pyproject.toml", None),)),
        make_fact(
            "dependency:development.dev.pytest-9.0.2",
            "pytest>=9.0.2",
            evidence=(("pyproject.toml", "declared in extra 'dev'"),),
        ),
        make_fact("package:python_requires", ">=3.10", evidence=(("pyproject.toml", None),)),
    ]


def test_dependency_groups_the_readme_never_mentions_are_added_with_only_their_missing_entries(
    make_context: Any, make_fact: Any
) -> None:
    from repository_presenter.components.readme_correction.detectors.additions import (
        add_dependency_groups,
    )

    readme = (
        "# P\n\n## Dependencies\n\n### Required Package Dependencies\n\n- `fpdf2>=2.7.5`\n\n"
        "## License\n\nMIT.\n"
    )
    ctx = make_context(readme, dependency_facts(make_fact), repository=WORDS)
    (edit,) = add_dependency_groups(ctx).edits
    corrected = applied(ctx, [edit])
    assert corrected.count("fpdf2") == 1  # the group and entry the README has are untouched
    assert "### Development Dependencies\n\n- `pytest>=9.0.2` (extra `dev`)" in corrected
    assert "### Native and System Requirements\n\n- Requires Python 3.10 or later" in corrected
    assert corrected.index("pytest") < corrected.index("## License")
    again = make_context(corrected, dependency_facts(make_fact), repository=WORDS)
    assert add_dependency_groups(again).edits == ()


def test_a_dependency_the_readme_names_anywhere_is_not_listed_again(
    make_context: Any, make_fact: Any
) -> None:
    from repository_presenter.components.readme_correction.detectors.additions import (
        add_dependency_groups,
    )

    readme = (
        "# P\n\nTests use pytest on Python 3.10.\n\n## Dependencies\n\nfpdf2 is required.\n\n"
        "## License\n\nMIT.\n"
    )
    ctx = make_context(readme, dependency_facts(make_fact), repository=WORDS)
    assert add_dependency_groups(ctx).edits == ()


def test_a_badge_of_the_registrys_family_in_any_form_counts_as_shown(
    make_context: Any, make_fact: Any
) -> None:
    other = "# P\n\n[![PyPI version](https://img.shields.io/pypi/v/aspose-words-foss)](x)\n\n## A\n"
    assert (
        add_version_badge(make_context(other, python_facts(make_fact), repository=WORDS)).edits
        == ()
    )


def test_the_cmake_minimum_joins_the_native_requirements_of_an_inserted_dependencies_section(
    make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact("package:name", "aspose_cells_foss_cpp", evidence=(("CMakeLists.txt", None),)),
        make_fact("dependency:none", "none", evidence=(("CMakeLists.txt", "links nothing"),)),
        make_fact("package:cxx_standard", "17", evidence=(("CMakeLists.txt", None),)),
        make_fact("package:cmake_minimum", "3.16", evidence=(("CMakeLists.txt", None),)),
    ]
    readme = "# P\n\n## Installation\n\nx\n\n## License\n\nMIT.\n"
    ctx = make_context(readme, facts, repository="aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp")
    (edit,) = [e for e in missing_sections(ctx).edits if "## Dependencies" in e.replacement]
    assert "- Requires CMake 3.16 or later." in edit.replacement
    assert "package:cmake_minimum" in edit.fact_ids
    stated = readme.replace("MIT.", "MIT. Needs CMake 3.16+.")
    again = missing_sections(
        make_context(stated, facts, repository="aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp")
    )
    (edit2,) = [e for e in again.edits if "## Dependencies" in e.replacement]
    assert "CMake" not in edit2.replacement  # the README already states it
