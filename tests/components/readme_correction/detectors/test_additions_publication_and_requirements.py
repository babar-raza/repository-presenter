"""Two audit findings on the additions (Lane L correction bundles, 2026-10-20).

* A published-version badge is not proposed while the README itself says the package is not
  published (PSD-.NET shipped a NuGet badge above "not published to NuGet yet").
* A requirement insertion states MSBuild target frameworks as the list they are, and a dependency
  group of one short line joins the section's list instead of taking an H3 of its own.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
)
from repository_presenter.components.readme_correction.augment import split_targets
from repository_presenter.components.readme_correction.detectors.additions import (
    add_dependency_groups,
    add_version_badge,
)
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import Context

WORDS = "aspose-words-foss/Aspose.Words-FOSS-for-Python"
CELLS_NET = "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"
UNPUBLISHED = "`aspose-words-foss` is not published to PyPI yet."


def applied(ctx: Context, edits: Any) -> str:
    ordered = sorted(edits, key=lambda e: (e.start, e.order))
    corrected, spans = apply_edits(ctx.readme, ordered)
    assert confinement_violations(ctx.readme, corrected, ordered, spans) == []
    return corrected


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


def net_facts(make_fact: Any, *, framework: str = "netstandard2.1;net10.0") -> list[Any]:
    return [
        make_fact("package:name", "Aspose.Cells.FOSS", evidence=(("src/x.csproj", None),)),
        make_fact(
            "dependency:none", "none", evidence=(("src/x.csproj", "the manifest declares none"),)
        ),
        make_fact(
            "package:target_framework",
            framework,
            evidence=(("src/x.csproj", "target frameworks the project declares"),),
        ),
    ]


# ------------------------------------------- a badge never contradicts the README's own sentence
def test_no_version_badge_while_the_readme_says_the_package_is_not_published(
    make_context: Any, make_fact: Any
) -> None:
    readme = f"# P\n\nIntro. {UNPUBLISHED}\n\n## Installation\n\nx\n"
    ctx = make_context(readme, python_facts(make_fact), repository=WORDS)
    result = add_version_badge(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.report_only_reason == "CONTRADICTS_README_PUBLICATION_CLAIM"
    assert finding.candidate.startswith("[![PyPI](https://img.shields.io/pypi/v/aspose-words-foss")
    assert finding.line == 3 and "not published" in finding.text
    outcome = correct(ctx)  # through the engine: reported under report_only, nothing applied
    assert not [e for e in outcome.edits if e.detector == "add_version_badge"]
    assert any(
        f.report_only_reason == "CONTRADICTS_README_PUBLICATION_CLAIM" for f in outcome.findings
    )


def test_the_same_readme_without_the_unpublished_sentence_still_gets_the_badge(
    make_context: Any, make_fact: Any
) -> None:
    readme = "# P\n\nIntro. It is a library.\n\n## Installation\n\nx\n"
    ctx = make_context(readme, python_facts(make_fact), repository=WORDS)
    result = add_version_badge(ctx)
    assert result.findings == ()
    (edit,) = result.edits
    assert "pypi/v/aspose-words-foss" in edit.replacement


# ------------------------------------------------- target frameworks and requirement stubs
def test_msbuild_target_frameworks_are_stated_as_the_list_they_are(
    make_context: Any, make_fact: Any
) -> None:
    readme = "# P\n\n## Requirements\n\n- .NET 10.0 SDK or later\n\n## License\n\nMIT.\n"
    ctx = make_context(readme, net_facts(make_fact), repository=CELLS_NET)
    (edit,) = add_dependency_groups(ctx).edits
    assert "netstandard2.1;net10.0" not in edit.replacement  # not the raw MSBuild value
    assert "Requires .NET" not in edit.replacement
    assert "- Targets netstandard2.1 and net10.0." in applied(ctx, [edit])


def test_target_frameworks_split_on_semicolons_and_join_with_commas_and_and() -> None:
    assert (
        split_targets("- Requires .NET `net6.0;net8.0;net10.0`.\n")
        == "- Targets net6.0, net8.0 and net10.0.\n"
    )
    # one framework, or a floor with no list, is left as the renderer wrote it
    assert split_targets("- Requires .NET 8 or later.\n") == "- Requires .NET 8 or later.\n"
    assert split_targets("- Requires .NET `net8.0`.") == "- Requires .NET `net8.0`."


def test_one_line_facts_join_the_requirements_list_instead_of_taking_an_h3_each(
    make_context: Any, make_fact: Any
) -> None:
    readme = "# P\n\n## Requirements\n\n- .NET 10.0 SDK or later\n\n## License\n\nMIT.\n"
    ctx = make_context(readme, net_facts(make_fact), repository=CELLS_NET)
    (edit,) = add_dependency_groups(ctx).edits
    corrected = applied(ctx, [edit])
    assert "###" not in corrected
    assert (
        "## Requirements\n\n- .NET 10.0 SDK or later\n"
        "- No required third-party package dependencies.\n"
        "- Targets netstandard2.1 and net10.0.\n\n## License"
    ) in corrected
    again = make_context(corrected, net_facts(make_fact), repository=CELLS_NET)
    assert add_dependency_groups(again).edits == ()  # a second run adds nothing


def test_stubs_keep_their_headings_when_there_is_no_list_to_join(
    make_context: Any, make_fact: Any
) -> None:
    prose = "# P\n\n## Requirements\n\nNeeds the SDK.\n\n## License\n\nMIT.\n"
    ctx = make_context(prose, net_facts(make_fact), repository=CELLS_NET)
    (edit,) = add_dependency_groups(ctx).edits
    corrected = applied(ctx, [edit])
    assert (
        "### Native and System Requirements\n\n- Targets netstandard2.1 and net10.0." in corrected
    )
    under_h3 = (
        "# P\n\n## Requirements\n\n### Tooling\n\n- .NET 10.0 SDK or later\n\n## License\n\nMIT.\n"
    )
    ctx3 = make_context(under_h3, net_facts(make_fact), repository=CELLS_NET)
    (edit3,) = add_dependency_groups(ctx3).edits
    assert "### Native and System Requirements" in edit3.replacement  # not folded under Tooling


def test_a_development_dependency_never_joins_a_list_of_requirements(
    make_context: Any, make_fact: Any
) -> None:
    pytest_fact = make_fact(
        "dependency:development.dev.pytest-9.0.2",
        "pytest>=9.0.2",
        evidence=(("pyproject.toml", "declared in extra 'dev'"),),
    )
    readme = "# P\n\n## Requirements\n\n- Python 3.10\n\n## License\n\nMIT.\n"
    ctx = make_context(readme, [pytest_fact], repository=WORDS)
    (edit,) = add_dependency_groups(ctx).edits
    assert "### Development Dependencies\n\n- `pytest>=9.0.2`" in edit.replacement


def test_a_context_from_before_requirements_v2_keeps_the_raw_value(
    make_context: Any, make_fact: Any
) -> None:
    """The gate re-derives a sealed bundle as written: no ``rendering`` record means no v2."""
    readme = "# P\n\n## Requirements\n\n- .NET 10.0 SDK or later\n\n## License\n\nMIT.\n"
    ctx = dataclasses.replace(
        make_context(readme, net_facts(make_fact), repository=CELLS_NET), requirements_v2=False
    )
    (edit,) = add_dependency_groups(ctx).edits
    assert "- Requires .NET `netstandard2.1;net10.0`." in edit.replacement
    assert "### Native and System Requirements" in edit.replacement
