"""Commands the README already shows, however written, are not added again; a command that needs an
install first is not added alone; an addition never lands after a closing </details>."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction.apply import apply_edits
from repository_presenter.components.readme_correction.commands import (
    commands_of,
    covered,
    equivalent,
    form_covered,
    missing_precondition,
    readme_commands,
    shown_forms,
    signature,
)
from repository_presenter.components.readme_correction.detectors.additions import (
    add_dev_commands,
    add_install_forms,
)

NL = chr(10)


def sig(command: str) -> Any:
    parsed = signature(command)
    assert parsed is not None
    return parsed


@pytest.mark.parametrize(
    ("wanted", "shown", "same"),
    [
        ("mvn package", "mvn clean package", True),
        (
            "mvn -B --no-transfer-progress clean package -DskipTests -Dgpg.skip=true",
            "mvn package",
            True,
        ),
        ("mvn test", "mvn test", True),
        ("mvn test", "./mvnw -q test", True),
        ("mvn verify", "mvn clean package", False),
        ("mvn package", "gradle package", False),
        (
            "dotnet build Aspose.Cells_FOSS.sln",
            "dotnet build src/Aspose.Cells.csproj -c Release",
            True,
        ),
        ("dotnet test", "dotnet build", False),
        ("npm test", "npm test", True),
        ("npm run build", "npm test", False),
        ("npm run build", "npm run build -- --watch", True),
        ("python -m build", "python3 -m build", True),
        ("python -m build", "python -m pytest", False),
        ("cargo test", "cargo test --all-features", True),
        ("cargo test", "cargo build", False),
        ("pytest", "pytest tests/ -q", True),
    ],
)
def test_two_commands_are_equivalent_when_they_ask_for_the_same_thing(
    wanted: str, shown: str, same: bool
) -> None:
    assert equivalent(sig(wanted), sig(shown)) is same


def test_every_command_the_readme_shows_is_found_even_inside_a_collapsed_block(
    make_context: Any,
) -> None:
    readme = NL.join(
        [
            "# P",
            "",
            "Run `mvn clean package` first.",
            "",
            "<details>",
            "<summary>More</summary>",
            "",
            "```bash",
            "$ mvn test && echo done",
            "# a comment",
            "```",
            "",
            "</details>",
            "",
        ]
    )
    shown = readme_commands(make_context(readme))
    assert sig("mvn package") in [s for s in shown if s.tool == "mvn"] or any(
        equivalent(sig("mvn package"), s) for s in shown
    )
    assert any(equivalent(sig("mvn test"), s) for s in shown)
    assert any(s.tool == "echo" for s in shown)
    assert commands_of("$ a && b; c || d") == ["a", "b", "c", "d"]


def test_a_fact_whose_every_command_is_shown_is_covered_and_a_partly_shown_one_is_not(
    make_context: Any,
) -> None:
    ctx = make_context("# P" + NL + NL + "`mvn clean package`" + NL)
    assert covered(ctx, "mvn package")
    assert not covered(ctx, "mvn package" + NL + "mvn test")
    assert not covered(ctx, "")


def test_a_module_the_toolchain_does_not_ship_needs_its_install_first() -> None:
    assert missing_precondition("python -m build") == "build"
    assert missing_precondition("python -m unittest discover") is None
    assert missing_precondition("mvn package") is None
    assert missing_precondition("python3 -m pip install -e .") is None


# ------------------------------------------------------------------------------ the detectors
DEV = NL.join(
    ["# P", "", "## Development and Testing", "", "{body}", "", "## License", "", "MIT.", ""]
)


def dev_readme(body: str) -> str:
    return DEV.replace("{body}", body)


def build_facts(make_facts: Any, make_fact: Any, build: str, test: str | None = None) -> Any:
    facts = [make_fact("build_test_asset:build-command", build, evidence=(("pom.xml", "x"),))]
    if test is not None:
        facts.append(make_fact("build_test_asset:test-command", test, evidence=(("pom.xml", "x"),)))
    return make_facts(*facts)


def test_a_build_command_the_readme_shows_in_another_form_is_not_added_again(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    body = "Build with `mvn clean package` and test with mvn test."
    ctx = make_context(
        dev_readme(body), build_facts(make_facts, make_fact, "mvn package", "mvn test")
    )
    assert add_dev_commands(ctx).edits == ()


def test_a_dotnet_sln_build_repeating_a_csproj_build_is_not_added(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    body = NL.join(["```bash", "dotnet build src/Aspose.Cells.csproj -c Release", "```"])
    ctx = make_context(
        dev_readme(body), build_facts(make_facts, make_fact, "dotnet build Aspose.Cells_FOSS.sln")
    )
    assert add_dev_commands(ctx).edits == ()


@pytest.mark.usefixtures("reenabled")
def test_a_command_the_readme_lacks_is_still_added(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        dev_readme("Run it the usual way."),
        build_facts(make_facts, make_fact, "mvn package", "mvn test"),
    )
    (edit,) = add_dev_commands(ctx).edits
    assert "mvn package" in edit.replacement and "mvn test" in edit.replacement


@pytest.mark.usefixtures("reenabled")
def test_a_command_needing_an_install_that_nothing_names_is_reported_not_added(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = build_facts(make_facts, make_fact, "python -m build")
    ctx = make_context(dev_readme("Run it the usual way."), facts)
    result = add_dev_commands(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert "pip install build" in finding.reason and "not added" in finding.reason
    stated = dev_readme("Run it the usual way. First `pip install build`.")
    (edit,) = add_dev_commands(make_context(stated, facts)).edits
    assert "python -m build" in edit.replacement


def test_an_install_command_whose_coordinates_the_readme_shows_in_a_snippet_is_not_added(
    make_context: Any,
) -> None:
    readme = NL.join(
        [
            "# Aspose.3D FOSS for Java",
            "",
            "## Installation",
            "",
            "```xml",
            "<artifactId>aspose-3d-foss</artifactId>",
            "```",
            "",
            "## License",
            "",
            "MIT.",
            "",
        ]
    )
    result = add_install_forms(make_context(readme))
    assert not any("mvn dependency:get" in e.replacement for e in result.edits)


@pytest.mark.usefixtures("reenabled")
def test_an_addition_lands_before_a_trailing_details_block_never_after_its_closing_tag(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    body = NL.join(
        [
            "Run it the usual way.",
            "",
            "<details>",
            "<summary>More</summary>",
            "",
            "Notes.",
            "",
            "</details>",
        ]
    )
    ctx = make_context(
        dev_readme(body), build_facts(make_facts, make_fact, "mvn package", "mvn test")
    )
    (edit,) = add_dev_commands(ctx).edits
    corrected, _spans = apply_edits(ctx.readme, [edit])
    assert corrected.index("mvn package") < corrected.index("<details>")
    assert corrected.index("Run it the usual way.") < corrected.index("mvn package")
    assert corrected.endswith("</details>" + NL + NL + "## License" + NL + NL + "MIT." + NL)


def test_a_section_that_is_only_a_collapsed_block_gets_no_addition(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    body = NL.join(["<details>", "<summary>All of it</summary>", "", "Text.", "", "</details>"])
    ctx = make_context(
        dev_readme(body), build_facts(make_facts, make_fact, "mvn package", "mvn test")
    )
    assert add_dev_commands(ctx).edits == ()


@pytest.mark.parametrize(
    ("wanted", "shown", "same"),
    [
        ("mvn package", "mvn verify -Dgpg.skip=true", True),  # a later phase runs the earlier ones
        ("mvn test", "mvn verify", True),
        ("mvn test", "mvn clean package", False),  # package is so often run with -DskipTests
        ("mvn verify", "mvn package", False),
        ("mvn install", "mvn verify", False),
    ],
)
def test_a_maven_phase_covers_the_phases_before_it(wanted: str, shown: str, same: bool) -> None:
    assert equivalent(sig(wanted), sig(shown)) is same


@pytest.mark.parametrize(
    ("shown", "wanted", "same"),
    [
        ("`pytest`", "python -m pytest -q", True),
        ("```bash\npip install -e .[test]\n```", "python -m pip install -e '.[test]'", True),
        ("```bash\npip install -e .\n```", "python -m pip install -e '.[test]'", False),
        ("`npm ci`", "npm install", False),
        ("`dotnet build A.sln`", "dotnet build B.csproj", True),
        ("`dotnet build A.sln`", "dotnet test A.sln", False),
        ("`cargo test`", "cargo test --all-targets", True),
        ("`go build ./...`", "go test ./...", False),
    ],
)
def test_a_command_is_shown_when_the_renderers_notion_of_the_same_command_says_so(
    make_context: Any, shown: str, wanted: str, same: bool
) -> None:
    ctx = make_context("# P" + NL + NL + shown + NL)
    assert form_covered(shown_forms(ctx), wanted) is same
