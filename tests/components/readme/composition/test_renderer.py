"""The renderer owns the Markdown: sections in shell order, identifiers in code spans, verbatim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    unit_checks,
)
from repository_presenter.components.readme.composition.placement import (
    api_reference_covered_fact_ids,
)
from repository_presenter.components.readme.composition.renderer import (
    RenderContext,
    anchor,
    line_counts,
    render_patch,
    render_readme,
    renders_verbatim,
    write_text,
)
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def _fact(
    fact_id: str, kind: str, value: str, detail: str = "", polarity: str = "SUPPORTED"
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x", detail or None),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("package:name", "package", "aspose-3d-foss"),
        _fact("package:version", "package", "26.1.0"),
        _fact("package:python_requires", "package", ">=3.7"),
        _fact("package:python_versions", "package", "3.7,3.8,3.12"),
        _fact("import_path:aspose", "import_path", "aspose"),
        _fact("import_path:aspose.threed", "import_path", "aspose.threed"),
        _fact("install_command:pip", "install_command", "pip install aspose-3d-foss"),
        _fact("license:spdx", "license", "MIT"),
        _fact("license:file", "license", "LICENSE"),
        Fact(
            "public_symbol:aspose.threed.scene",
            "public_symbol",
            "aspose.threed.Scene",
            (Evidence("x", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class"},
        ),
        Fact(
            "public_symbol:aspose.threed.scene.save",
            "public_symbol",
            "aspose.threed.Scene.save",
            (Evidence("x", "line 9; method; public by name"),),
            attributes={"symbol_kind": "method"},
        ),
        _fact("format:output.glb", "format", ".glb"),
        _fact("format:input.obj", "format", ".obj"),
        _fact("example:001", "example", "from aspose.threed import Scene\nScene().save('a.glb')\n"),
        _fact("example:002", "example", "print(2)\n"),
        _fact(
            "link_target:002",
            "link_target",
            "https://docs.example.com/3d",
            "line 5; external; text 'Docs'",
        ),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
        _fact(
            "inherited_unit:009.paragraph", "inherited_unit", "Kept verbatim from the old README."
        ),
        _fact("inherited_unit:008.heading", "inherited_unit", "## Old limitations heading"),
        _fact("inherited_unit:007.code_block", "inherited_unit", "```python\nprint(2)\n```"),
    ),
)
PLAN: dict[str, Any] = {
    "sections": [
        {
            "section_id": s,
            "include": s
            not in {"banner", "dependencies", "enterprise_relationship", "third_party_notices"},
            "reason": "r",
        }
        for s in [
            "identity",
            "badges",
            "banner",
            "opening",
            "navigation",
            "at_a_glance",
            "key_capabilities",
            "installation",
            "dependencies",
            "quick_start",
            "additional_examples",
            "api_reference",
            "documentation_resources",
            "scope_limitations",
            "development_testing",
            "enterprise_relationship",
            "third_party_notices",
            "license",
        ]
    ],
    "core_capabilities": [
        {"title": "Build scenes", "fact_ids": ["public_symbol:aspose.threed.scene"]},
        {"title": "Save GLB", "fact_ids": ["format:output.glb"]},
    ],
    "at_a_glance": {
        "input_format_ids": ["format:input.obj"],
        "output_format_ids": ["format:output.glb"],
        "capability_titles": ["Build scenes", "Save GLB"],
    },
    "quick_start_example_id": "example:001",
    "additional_example_ids": ["example:002"],
    "api_hubs": [
        {"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": ["example:001"]}
    ],
    "material_limitations": [{"fact_ids": ["format:input.obj"], "unit_ids": []}],
    "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
    "deviations": [],
}


def _unit(section: str, slot: str, text: str) -> dict[str, Any]:
    return {"section": section, "slot": slot, "text": text, "fact_ids": ["identity:repository"]}


UNITS = {
    "units": [
        _unit(
            "opening",
            "opening",
            "Aspose.3D FOSS for Python builds scenes with Scene and saves them with Scene.save.",
        ),
        _unit(
            "key_capabilities", "capability:1", "Scenes are built from aspose.threed.Scene objects."
        ),
        _unit("key_capabilities", "capability:2", "A scene saves as GLB."),
        _unit("quick_start", "lead_in", "Create a scene and save it."),
        _unit("additional_examples", "preview", "One more workflow follows."),
        _unit("additional_examples", "workflow:example:002", "Print a number"),
        _unit("api_reference", "intro", "Scene is the entry point; Node hangs off it."),
        _unit(
            "api_reference", "hub:public_symbol:aspose.threed.scene", "Scene holds the scene graph."
        ),
        _unit("documentation_resources", "link:link_target:002", "The docs explain the API."),
        _unit("scope_limitations", "scope", "The package writes GLB only."),
        _unit("scope_limitations", "limitation:1", "OBJ import is unverified."),
        _unit("development_testing", "summary", "Run the tests with the standard runner."),
    ],
    "omitted": [],
}
DISPOSITIONS = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:009.paragraph",
            "disposition": "VERIFIED_MOVE",
            "destination_section": "scope_limitations",
            "fact_ids": [],
            "rationale": "r",
        },
        {
            "unit_id": "inherited_unit:008.heading",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "scope_limitations",
            "fact_ids": [],
            "rationale": "r",
        },
        {
            "unit_id": "inherited_unit:007.code_block",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "additional_examples",
            "fact_ids": ["example:002"],
            "rationale": "r",
        },
    ]
}


def test_a_literal_url_is_rejected_while_the_referential_form_renders_the_same_link() -> None:
    """G2-W20: a unit names what the reader finds; the renderer emits the link from the fact.

    Measured on the canary on 2026-09-05: three documentation units wrote the target as text
    and lost the call; under the referential form the same three rendered the same links and
    the family disappeared from the ledger (section 27.10).
    """
    task = SectionTask(
        "documentation_resources",
        {},
        frozenset({"link_target:002", "identity:repository"}),
        ("link:link_target:002",),
        slot_facts={"link:link_target:002": frozenset({"link_target:002"})},
    )

    def unit(body: str) -> dict[str, Any]:
        return {
            "units": [
                {
                    "section": "documentation_resources",
                    "slot": "link:link_target:002",
                    "text": body,
                    "fact_ids": ["link_target:002"],
                }
            ],
            "omitted": [],
        }

    literal = unit("The developer guide at https://docs.example.com/3d covers installation.")
    assert unit_checks(literal, task, FACTS, "Aspose.3D FOSS for Python") == [
        "unit link:link_target:002: text contains a URL ('https://')",
        "unit link:link_target:002: identifiers that are not accepted fact values: "
        "docs.example.com",
    ]
    referential = unit("It covers installation, walkthroughs, and feature guides.")
    assert unit_checks(referential, task, FACTS, "Aspose.3D FOSS for Python") == []
    # The command family is judged the same way, and the renderer owns the block that carries it.
    commanded = unit("Run pip install aspose-3d-foss to get the package.")
    assert unit_checks(commanded, task, FACTS, "Aspose.3D FOSS for Python") == [
        "unit link:link_target:002: text contains a command ('pip install')",
    ]
    # The renderer emits the link itself, from the fact the unit cites and nothing else.
    rendered = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert "- **[Docs](https://docs.example.com/3d)** " in rendered


def test_the_document_follows_the_shell_with_code_spans_and_placed_units() -> None:
    readme = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    lines = readme.splitlines()
    assert lines[0] == "# Aspose.3D FOSS for Python"
    repo = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert lines[2] == (
        "[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)]"
        "(https://pypi.org/project/aspose-3d-foss/) "
        "![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) "
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) "
        f"[![Contributors](https://img.shields.io/github/contributors/{repo})]"
        f"(https://github.com/{repo}/graphs/contributors)"
    )
    assert lines[4] == (
        "Aspose.3D FOSS for Python builds scenes with `Scene` and saves them with `Scene.save`."
    )
    assert lines[6] == "## Navigation"
    assert "- [At a Glance](#at-a-glance)" in lines and "- [License](#license)" in lines
    assert "- [Dependencies](#dependencies)" not in lines
    assert "- [Navigation](#navigation)" not in lines
    assert "```mermaid" in lines and '    i1["An existing OBJ file"]' in lines
    assert '    o1["GLB file"]' in lines
    assert "- **Build scenes.** Scenes are built from `aspose.threed.Scene` objects." in lines
    installation = readme.split("## Installation\n\n", 1)[1].split("\n## ", 1)[0]
    assert installation == (
        "Install the published package from PyPI (`aspose-3d-foss`, version 26.1.0):\n\n"
        "```bash\npip install aspose-3d-foss\n```\n\n"
        "To work from a source checkout instead, install the clone with pip:\n\n"
        "```bash\ngit clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git\n"
        "cd Aspose.3D-FOSS-for-Python\npip install .\n```\n\n"
        "Verify the install:\n\n"
        '```bash\npython -c "import aspose.threed"\n```\n\n'
        "The package supports Python 3.7, 3.8, and 3.12 and declares `python_requires` as "
        "`>=3.7`.\n"
    )
    quick = lines.index("## Quick Start")
    assert lines[quick + 2] == "Create a scene and save it."
    assert lines[quick + 4 : quick + 8] == [
        "```python",
        "from aspose.threed import Scene",
        "Scene().save('a.glb')",
        "```",
    ]
    assert "<summary>View Additional Examples</summary>" in lines
    assert "### Print a number" in lines and lines.count("<details>") == 2
    assert "<summary>View the Complete Public API Surface</summary>" in lines
    assert "| `Scene` | Public class. |" in lines and "### Scene" in lines
    assert "`Scene` holds the scene graph." in lines
    assert "- `save`: Public method. |" not in lines and "- `save`: Public method." in lines
    assert "- **[Docs](https://docs.example.com/3d)** — The docs explain the API." in lines
    assert (
        "- Found a bug or have a feature request? [Open an issue]"
        "(https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues)." in lines
    )
    assert "- OBJ import is unverified." in lines
    assert "Kept verbatim from the old README." in lines
    assert "## Old limitations heading" not in lines
    assert lines.count("## Scope and Limitations") == 1
    assert readme.count("print(2)") == 1
    assert "- `tests/`" not in lines  # assets are named in prose, never listed bare
    assert lines[-1] == (
        "This project is licensed under the [MIT License](LICENSE). The MIT License permits use, "
        "copying, modification, distribution, sublicensing, and commercial use, provided its "
        "copyright and permission notice are retained. The software is provided without warranty."
    )
    assert readme.endswith("\n") and "\r" not in readme and "\n\n\n" not in readme
    assert render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS) == readme


def test_headings_anchor_like_github_and_line_counts_skip_details() -> None:
    assert anchor("Documentation & Resources") == "documentation--resources"
    readme = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    visible, total = line_counts(readme)
    assert total == readme.count("\n")
    assert visible < total


def test_the_patch_is_a_unified_diff_from_the_original(tmp_path: Path) -> None:
    readme = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    patch = render_patch("# Old\n\nOld prose.\n", readme)
    assert patch.startswith("--- a/README.md\n+++ b/README.md\n@@ ")
    assert "-# Old" in patch and "+# Aspose.3D FOSS for Python" in patch
    assert render_patch(readme, readme) == ""
    digest = write_text(patch, tmp_path / "t" / "README.patch")
    assert (tmp_path / "t" / "README.patch").read_bytes() == patch.encode("utf-8")
    assert write_text(patch, tmp_path / "t" / "README.patch") == digest


def test_prose_wraps_bare_extension_fact_values_in_code_spans() -> None:
    context = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert context.prose("Export to .glb, not .obj or .xyz, via Scene.save.") == (
        "Export to `.glb`, not `.obj` or .xyz, via `Scene.save`."
    )


def test_canonical_protects_a_path_and_a_command_hyphenated_with_an_abbreviation() -> None:
    # Third external review, 2026-09-07: R3's acceptance criterion names commands, paths and API
    # identifiers alongside package names, not package names alone - verified beyond the
    # coordinate case this time.
    context = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    # A path with a hyphenated abbreviation keeps its exact spelling.
    assert context.canonical("See docs/pdf-reference.md for details.") == (
        "See docs/pdf-reference.md for details."
    )
    # So does a command-shaped identifier.
    assert context.canonical("Run the aspose-pdf-cli --export-html tool.") == (
        "Run the aspose-pdf-cli --export-html tool."
    )
    # Ambient prose mentioning the same abbreviations, not adjacent to a hyphen or colon, still
    # normalizes exactly as before - the protection is scoped to compound-identifier shapes only.
    assert context.canonical("Convert your pdf file to html today.") == (
        "Convert your PDF file to HTML today."
    )


def test_prose_wraps_a_package_coordinate_as_one_code_span_not_a_dotted_prefix() -> None:
    # External audit, 2026-09-07: measured on Aspose.PDF for Java's sealed README - the group and
    # artifact are one coordinate (`org.aspose:aspose-pdf-foss`), but only the dotted `org.aspose`
    # prefix was ever recognized as a token, so it rendered as `org.aspose`:aspose-pdf-foss - a
    # broken span with the colon and artifact id sitting outside it.
    maven = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (*FACTS.facts, _fact("package:maven_coordinate", "package", "org.aspose:aspose-pdf-foss")),
    )
    context = RenderContext(ENTRY, maven, PLAN, UNITS, DISPOSITIONS)
    # A second external review, the same day: an earlier version of this fix matched the
    # coordinate case-insensitively, papering over canonical()'s "pdf" -> "PDF" abbreviation-
    # raising corrupting the coordinate's exact spelling - a README_CONTRACT.md section 2
    # violation (package names keep their source spelling verbatim). The real fix is at
    # canonical()'s own source (_LOWER_WORD excludes a hyphen/colon neighbor); the coordinate now
    # renders with the fact's exact lowercase spelling, unaltered, wrapped as one span.
    assert context.prose("The package org.aspose:aspose-pdf-foss provides APIs.") == (
        "The package `org.aspose:aspose-pdf-foss` provides APIs."
    )
    # Ordinary prose use of the same abbreviation, well outside any coordinate, still
    # canonicalizes exactly as before - the fix is scoped to hyphen/colon-adjacent text only.
    assert context.prose("Read the pdf format documentation.") == (
        "Read the PDF format documentation."
    )


def test_prose_folds_a_trailing_call_parens_into_the_same_code_span() -> None:
    # External audit, 2026-09-07: the un-widened match left a bare "()" outside the span -
    # `Scene.save`() - measured 16+ times in one sealed candidate and once in an unrelated one.
    context = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert context.prose("Load a file using Scene.save() with default options.") == (
        "Load a file using `Scene.save()` with default options."
    )
    # The token alone, with nothing following it, is unaffected.
    assert context.prose("Scene.save is the export entry point.") == (
        "`Scene.save` is the export entry point."
    )


def test_the_hosting_site_a_verified_link_names_is_left_in_plain_text() -> None:
    # G2-W13: a code span around GitHub is a rendering defect; the site is a proper noun the
    # same way a package registry is, and it is spellable only because a fact links there.
    hosted = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact("link_target:900", "link_target", "https://github.com/org/repo/issues"),
        ),
    )
    context = RenderContext(ENTRY, hosted, PLAN, UNITS, DISPOSITIONS)
    assert context.prose("Issues live on GitHub.") == "Issues live on GitHub."
    plain = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert plain.prose("Issues live on GitHub.") == "Issues live on GitHub."


def test_renders_verbatim_follows_ownership() -> None:
    assert renders_verbatim("inherited_unit:001.paragraph", "Prose.", "python")
    assert renders_verbatim("inherited_unit:002.list", "- a\n- b", "python")
    assert not renders_verbatim("inherited_unit:003.heading", "## Old", "python")
    assert not renders_verbatim("inherited_unit:004.badge_row", "![x](y)", "python")
    assert not renders_verbatim(
        "inherited_unit:005.code_block", "```python\nprint(1)\n```", "python"
    )
    assert not renders_verbatim(
        "inherited_unit:006.code_block", "```mermaid\ngraph LR\n```", "python"
    )
    assert renders_verbatim("inherited_unit:007.code_block", "```bash\npytest\n```", "python")
    assert renders_verbatim("inherited_unit:008.code_block", "    indented\n", "python")


def test_a_placed_command_block_appears_in_its_destination() -> None:
    commands = "```bash\npip install -e .\npython -m unittest discover tests\n```"
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact(
                "inherited_unit:010.code_block",
                "inherited_unit",
                commands,
                (Evidence("README.md", "lines 20-24; code_block"),),
            ),
        ),
    )
    dispositions: dict[str, Any] = {
        "dispositions": [
            *DISPOSITIONS["dispositions"],
            {
                "unit_id": "inherited_unit:010.code_block",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "development_testing",
                "fact_ids": ["build_test_asset:tests"],
                "rationale": "r",
            },
        ]
    }
    readme = render_readme(ENTRY, facts, PLAN, UNITS, dispositions)
    section = readme.split("## Development and Testing\n", 1)[1].split("\n## ", 1)[0]
    assert section.rstrip("\n").endswith(commands)
    assert readme.count("print(2)") == 1


def test_a_placed_unit_inherits_its_sections_visibility_and_overlap_is_exclusive() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            _fact("inherited_unit:020.paragraph", "inherited_unit", "The old API note."),
            _fact("inherited_unit:021.paragraph", "inherited_unit", "OBJ import is unverified."),
        ),
    )
    dispositions: dict[str, Any] = {
        "dispositions": [
            *DISPOSITIONS["dispositions"],
            {
                "unit_id": "inherited_unit:020.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "api_reference",
                "fact_ids": [],
                "rationale": "r",
            },
            {
                "unit_id": "inherited_unit:021.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "scope_limitations",
                "fact_ids": ["format:input.obj"],
                "rationale": "r",
            },
        ]
    }
    readme = render_readme(ENTRY, facts, PLAN, UNITS, dispositions)
    api = readme.split("## API Reference\n", 1)[1].split("\n## ", 1)[0]
    assert api.index("The old API note.") < api.index("</details>")  # inside the details block
    assert api.rstrip("\n").endswith("</details>")
    # The plan's material limitation cites format:input.obj, so the overlapping preserved
    # paragraph is dropped; the planned bullet is what the reader sees.
    assert "OBJ import is unverified." in readme
    assert readme.count("OBJ import is unverified.") == 1


def test_an_unpublished_package_is_stated_plainly_and_only_verified_installs_render() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        tuple(
            Fact(
                f.id,
                f.kind,
                f.value,
                (Evidence("setup.py", "manifest"), Evidence("pypi", "distribution not found")),
                polarity="CONTRADICTED",
            )
            if f.id == "install_command:pip"
            else f
            for f in FACTS.facts
            if f.id != "package:python_versions"
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    installation = readme.split("## Installation\n\n", 1)[1].split("\n## ", 1)[0]
    assert installation.startswith(
        "The package `aspose-3d-foss` is not yet published on PyPI (distribution not found).\n\n"
        "To work from a source checkout instead"
    )
    assert "pip install aspose-3d-foss" not in installation
    assert installation.endswith("The package declares `python_requires` as `>=3.7`.\n")
    apache = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        tuple(
            Fact(f.id, f.kind, "Apache-2.0", f.evidence) if f.id == "license:spdx" else f
            for f in FACTS.facts
        ),
    )
    assert render_readme(ENTRY, apache, PLAN, UNITS, DISPOSITIONS).endswith(
        "This project is licensed under the [Apache-2.0](LICENSE).\n"
    )


def test_dependencies_render_in_four_subsections_with_verified_zero_stated() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id != "package:python_requires"),
            Fact(
                "package:python_requires",
                "package",
                ">=3.7",
                (Evidence("setup.py", "python_requires declared"),),
            ),
            Fact(
                "dependency:none",
                "dependency",
                "none",
                (Evidence("setup.py", "the `install_requires` list is empty"),),
            ),
            Fact(
                "dependency:development.dev.pytest-7.0.0",
                "dependency",
                "pytest>=7.0.0",
                (Evidence("setup.py", "extra 'dev' declared"),),
            ),
            Fact(
                "dependency:optional.viz.matplotlib",
                "dependency",
                "matplotlib",
                (Evidence("setup.py", "extra 'viz' declared"),),
            ),
        ),
    )
    plan = {
        **PLAN,
        "sections": [
            {**entry, "include": True} if entry["section_id"] == "dependencies" else entry
            for entry in PLAN["sections"]
        ],
    }
    readme = render_readme(ENTRY, facts, plan, UNITS, DISPOSITIONS)
    section = readme.split("## Dependencies\n\n", 1)[1].split("\n## ", 1)[0]
    assert section == (
        "### Required Package Dependencies\n\n"
        "No required third-party package dependencies; in `setup.py`, the `install_requires` "
        "list is empty.\n\n"
        "### Optional Dependencies\n\n- `matplotlib` (extra `viz`)\n\n"
        "### Native and System Requirements\n\n"
        '- Requires Python 3.7 or later (`python_requires=">=3.7"` in `setup.py`).\n\n'
        "### Development Dependencies\n\n- `pytest>=7.0.0` (extra `dev`)\n"
    )
    assert "- [Dependencies](#dependencies)" in readme.splitlines()


def test_the_runtime_floor_is_the_ecosystems_own_and_not_pythons() -> None:
    """Section 29.6 E4. Measured 2026-09-06: the row read `package:python_requires` by name, so
    a .NET candidate never told a reader which framework it needs - the fact is
    `package:target_framework` and no branch in shared code could see it."""
    entry = RegistryEntry.model_validate(
        {
            **ENTRY.model_dump(mode="json"),
            "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
            "platform": "net",
            "ecosystem": "net",
        }
    )
    facts = FactsDocument(
        entry.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith(("dependency:", "package:python"))),
            Fact(
                "package:target_framework",
                "package",
                "netstandard2.0",
                (Evidence("src/Aspose.Widget/Aspose.Widget.csproj", "lowest target framework"),),
            ),
            Fact(
                "dependency:skiasharp",
                "dependency",
                "SkiaSharp 2.88.8",
                (Evidence("src/Aspose.Widget/Aspose.Widget.csproj", "package reference"),),
            ),
        ),
    )
    plan = {
        **PLAN,
        "sections": [
            {**item, "include": True} if item["section_id"] == "dependencies" else item
            for item in PLAN["sections"]
        ],
    }
    readme = render_readme(entry, facts, plan, UNITS, DISPOSITIONS)
    section = readme.split("## Dependencies\n\n", 1)[1].split("\n## ", 1)[0]
    assert section == (
        "### Required Package Dependencies\n\n- `SkiaSharp 2.88.8`\n\n"
        "### Native and System Requirements\n\n"
        "- Requires .NET `netstandard2.0` (`TargetFramework` in "
        "`src/Aspose.Widget/Aspose.Widget.csproj`).\n"
    )


def test_a_floor_fact_names_its_own_declaration_when_the_ecosystems_is_too_generic() -> None:
    """G4-W17 arrival item 14. A POM may state the floor as maven.compiler.release, .target or
    .source, and one Java cohort used all three - naming any single one in the spec would cite a
    property most of the cohort's repositories do not declare. A floor fact whose own attributes
    name its precise declaration overrides the spec's generic fallback; a fact that does not
    (every ecosystem before this item, Python included) renders exactly as before."""
    entry = RegistryEntry.model_validate(
        {
            **ENTRY.model_dump(mode="json"),
            "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
            "platform": "net",
            "ecosystem": "net",
        }
    )
    facts = FactsDocument(
        entry.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith(("dependency:", "package:python"))),
            Fact(
                "package:target_framework",
                "package",
                "17",
                (Evidence("pom.xml", "maven.compiler.release declared"),),
                attributes={"floor_declaration": "maven.compiler.release"},
            ),
        ),
    )
    plan = {
        **PLAN,
        "sections": [
            {**item, "include": True} if item["section_id"] == "dependencies" else item
            for item in PLAN["sections"]
        ],
    }
    readme = render_readme(entry, facts, plan, UNITS, DISPOSITIONS)
    section = readme.split("## Dependencies\n\n", 1)[1].split("\n## ", 1)[0]
    assert "(`maven.compiler.release` in `pom.xml`)" in section
    assert "TargetFramework" not in section


def test_the_source_checkout_command_is_the_ecosystems_own_not_a_hard_coded_pip_install() -> None:
    """Measured 2026-09-06: `_installation` hard-coded `git clone ...; pip install .` for every
    ecosystem with an executed example, so Aspose.Cells and Aspose.3D for .NET - both sealed -
    told a reader to run `pip install .` against a C# project. The command and its lead-in verb
    now come from the spec; Python's own wording is unchanged, byte for byte (test_sealed_bytes.py
    holds every other sealed candidate to it)."""
    entry = RegistryEntry.model_validate(
        {
            **ENTRY.model_dump(mode="json"),
            "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-.NET",
            "family": "widget",
            "platform": "net",
            "ecosystem": "net",
        }
    )
    facts = FactsDocument(
        entry.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id != "identity:repository"),
            Fact("identity:repository", "identity", entry.repository, (Evidence("x"),)),
        ),
    )
    readme = render_readme(entry, facts, PLAN, UNITS, DISPOSITIONS)
    installation = readme.split("## Installation\n\n", 1)[1].split("\n## ", 1)[0]
    assert (
        "To work from a source checkout instead, build the clone with dotnet build:\n\n"
        "```bash\ngit clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
        "cd Aspose.Widget-FOSS-for-.NET\ndotnet build\n```"
    ) in installation
    assert "pip install" not in installation


def test_a_verified_source_build_is_the_installation_not_an_additional_suggestion() -> None:
    """G4-W17 arrival item 0. `extract.py` promotes an unpublished package's install fact to
    SUPPORTED with `install_kind: source` once an example proves the source compiles; the
    renderer states plainly that the registry does not have it yet and never also prints the
    ordinary "To work from a source checkout instead" suggestion beside it - that would repeat
    the same command as if it were a second, optional path rather than the only one."""
    entry = RegistryEntry.model_validate(
        {
            **ENTRY.model_dump(mode="json"),
            "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-.NET",
            "family": "widget",
            "platform": "net",
            "ecosystem": "net",
        }
    )
    command = (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
        "cd Aspose.Widget-FOSS-for-.NET\ndotnet build"
    )
    facts = FactsDocument(
        entry.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id not in {"identity:repository", "install_command:pip"}),
            Fact("identity:repository", "identity", entry.repository, (Evidence("x"),)),
            Fact(
                "install_command:dotnet",
                "install_command",
                command,
                (
                    Evidence("Widget.csproj", "manifest"),
                    Evidence("examples.json", "verified source build"),
                ),
                attributes={"install_kind": "source"},
            ),
        ),
    )
    readme = render_readme(entry, facts, PLAN, UNITS, DISPOSITIONS)
    installation = readme.split("## Installation\n\n", 1)[1].split("\n## ", 1)[0]
    assert installation.startswith(
        "`aspose-3d-foss` is not yet published on NuGet; build it from a source checkout "
        f"instead, verified against this revision:\n\n```bash\n{command}\n```"
    )
    assert installation.count("git clone") == 1
    assert "To work from a source checkout instead" not in installation


def test_a_verified_source_build_never_badges_a_registry_page_that_does_not_exist() -> None:
    """BC-06 regression (measured 2026-09-06 on Aspose.Slides for .NET): the version badge used
    to render whenever the install fact was SUPPORTED, which a source-kind fact now also is -
    but the package is not on the registry, so the badge linked to a NuGet page that was never
    verified and does not exist. The badge is a registry-confirmed claim; a source build is not
    one, so it stays absent instead."""
    entry = RegistryEntry.model_validate(
        {
            **ENTRY.model_dump(mode="json"),
            "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-.NET",
            "family": "widget",
            "platform": "net",
            "ecosystem": "net",
        }
    )
    facts = FactsDocument(
        entry.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id not in {"identity:repository", "install_command:pip"}),
            Fact("identity:repository", "identity", entry.repository, (Evidence("x"),)),
            Fact(
                "install_command:dotnet",
                "install_command",
                "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
                "cd Aspose.Widget-FOSS-for-.NET\ndotnet build",
                (
                    Evidence("Widget.csproj", "manifest"),
                    Evidence("examples.json", "verified source build"),
                ),
                attributes={"install_kind": "source"},
            ),
        ),
    )
    readme = render_readme(entry, facts, PLAN, UNITS, DISPOSITIONS)
    assert "nuget.org/packages" not in readme
    assert "img.shields.io/nuget" not in readme


def test_a_package_registry_name_stays_plain_in_prose() -> None:
    context = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert context.prose("Published to PyPI from Scene.") == "Published to PyPI from `Scene`."


def test_development_and_testing_states_the_suite_size_and_links_the_release_workflow() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id != "build_test_asset:tests"),
            Fact(
                "build_test_asset:tests",
                "build_test_asset",
                "tests/",
                (Evidence("tests/test_a.py"), Evidence("tests/", "34 files; test suite")),
            ),
            Fact(
                "build_test_asset:ci",
                "build_test_asset",
                ".github/workflows/",
                (
                    Evidence(".github/workflows/ci.yml"),
                    Evidence(".github/workflows/publish.yml"),
                    Evidence(".github/workflows/", "2 files; GitHub Actions workflows"),
                ),
            ),
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    section = readme.split("## Development and Testing\n\n", 1)[1].split("\n## ", 1)[0]
    assert section.startswith("Run the tests with the standard runner.\n\n")
    assert (
        "The suite covers 34 test files under `tests/`. "
        "Releases run through the [publish workflow](.github/workflows/publish.yml)."
    ) in section


def test_every_limitation_unit_renders_as_its_own_bullet() -> None:
    units = {
        "units": [
            *UNITS["units"],
            _unit("scope_limitations", "limitation:2", "FBX export is not implemented."),
        ],
        "omitted": [],
    }
    readme = render_readme(ENTRY, FACTS, PLAN, units, DISPOSITIONS)
    lines = readme.splitlines()
    assert lines.index("- OBJ import is unverified.") + 1 == lines.index(
        "- FBX export is not implemented."
    )


def test_a_second_quick_start_example_renders_with_its_own_lead_in() -> None:
    plan = {**PLAN, "second_quick_start_example_id": "example:002", "additional_example_ids": []}
    units = {
        "units": [
            *UNITS["units"],
            _unit("quick_start", "lead_in:2", "Build a scene from scratch."),
        ],
        "omitted": [],
    }
    readme = render_readme(ENTRY, FACTS, plan, units, DISPOSITIONS)
    section = readme.split("## Quick Start", 1)[1].split("## ", 1)[0]
    assert section.index("Create a scene and save it.") < section.index(
        "Build a scene from scratch."
    )
    assert section.count("```python") == 2


def test_the_api_reference_follows_row_fourteen_with_docstring_first_descriptions() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith("public_symbol:")),
            Fact(
                "public_symbol:aspose.threed.scene",
                "public_symbol",
                "aspose.threed.Scene",
                (Evidence("aspose/threed/scene.py", "line 1; class; public by name"),),
                attributes={
                    "symbol_kind": "class",
                    "signature": "class Scene(ANode)",
                    "docstring": "The root of a scene graph.",
                },
            ),
            Fact(
                "public_symbol:aspose.threed.scene.save",
                "public_symbol",
                "aspose.threed.Scene.save",
                (Evidence("aspose/threed/scene.py", "line 9; method; public by name"),),
                attributes={"symbol_kind": "method", "signature": "def save(self, path)"},
            ),
            Fact(
                "public_symbol:aspose.threed.axis",
                "public_symbol",
                "aspose.threed.Axis",
                (Evidence("aspose/threed/axis.py", "line 1; enum; public by name"),),
                attributes={"symbol_kind": "enum", "signature": "class Axis(Enum)"},
            ),
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    section = readme.split("## API Reference\n\n", 1)[1].split("\n## ", 1)[0]
    assert section.startswith(
        "`Scene` is the entry point; Node hangs off it.\n\n"
        "The verified public surface has 2 types.\n\n<details>\n"
        "<summary>View the Complete Public API Surface</summary>\n\n### Core API\n\n"
        "| Class | Description |\n| --- | --- |\n| `Scene` | The root of a scene graph. |\n\n"
        "#### Enumerations\n\n| Enumeration | Description |\n| --- | --- |\n"
        "| `Axis` | Defined as `class Axis(Enum)`. |\n\n#### Detailed Member Reference\n\n"
        "### Scene\n\n`Scene` holds the scene graph.\n\n"
        "- `save`: Defined as `def save(self, path)`.\n"
    )
    assert section.rstrip("\n").endswith("</details>")


def test_api_reference_covered_fact_ids_matches_what_this_render_actually_shows() -> None:
    """RC-02, RESEARCH_AND_GUIDELINES.md 27.2 RC2/SW2, 2026-09-08: the property test the
    taskcard itself asks for - every fact ``api_reference_covered_fact_ids`` declares covered
    must actually appear in this real render's own API Reference section, and a method excluded
    from it (not owned by any plan hub) must not appear there either. Catches drift between the
    renderer's own display logic and the coverage model automatically, rather than needing a
    human to notice (which is exactly what let RC-02's gap stand until this session)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith("public_symbol:")),
            Fact(
                "public_symbol:aspose.threed.scene",
                "public_symbol",
                "aspose.threed.Scene",
                (Evidence("x", "line 1; class; public by name"),),
                attributes={"symbol_kind": "class"},
            ),
            Fact(
                "public_symbol:aspose.threed.scene.save",
                "public_symbol",
                "aspose.threed.Scene.save",
                (Evidence("x", "line 9; method; public by name"),),
                attributes={"symbol_kind": "method"},
            ),
            Fact(
                "public_symbol:aspose.threed.node",
                "public_symbol",
                "aspose.threed.Node",
                (Evidence("x", "line 1; class; public by name"),),
                attributes={"symbol_kind": "class"},
            ),
            Fact(
                "public_symbol:aspose.threed.node.detach",
                "public_symbol",
                "aspose.threed.Node.detach",
                (Evidence("x", "line 1; method; public by name"),),
                attributes={"symbol_kind": "method"},
            ),
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    section = readme.split("## API Reference\n\n", 1)[1].split("\n## ", 1)[0]
    covered = api_reference_covered_fact_ids(PLAN, facts)
    by_id = {f.id: f for f in facts.facts}
    assert covered == {
        "public_symbol:aspose.threed.scene",  # hub class - in the table and Detailed Reference
        "public_symbol:aspose.threed.node",  # non-hub class - the table lists it regardless
        "public_symbol:aspose.threed.scene.save",  # the hub's own method
    }
    for fact_id in covered:
        display_name = by_id[fact_id].value.rsplit(".", 1)[-1]
        assert f"`{display_name}`" in section, (fact_id, section)
    # Not covered, and not shown: Node has no hub, so its own method never renders here.
    assert "detach" not in section


def test_a_synthetic_net_spec_renders_csharp_fences_a_nuget_badge_and_a_dotnet_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adding an ecosystem is a spec, not an edit to the renderer (section 29.6 E3 and E4).

    Nothing here is a .NET plugin: the spec is synthetic and the facts are the canary's, renamed.
    What it proves is that every ecosystem-specific spelling the renderer prints - the fence
    language, the registry badge, the install block and the verify command - reads from the spec.
    """
    net = EcosystemSpec(
        ecosystem="net",
        language="C#",
        fence="csharp",
        registry="NuGet",
        install_fact_id="install_command:dotnet",
        version_badge=(
            "[![NuGet](https://img.shields.io/nuget/v/{package}.svg)]"
            "(https://www.nuget.org/packages/{package}/)"
        ),
        verify_command="dotnet list package | findstr {module}",
    )
    monkeypatch.setitem(SPECS, "net", net)
    entry = ENTRY.model_copy(update={"ecosystem": "net"})
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id != "install_command:pip"),
            _fact("install_command:dotnet", "install_command", "dotnet add package Aspose.ThreeD"),
        ),
    )
    readme = render_readme(entry, facts, PLAN, UNITS, DISPOSITIONS)
    assert "[![NuGet](https://img.shields.io/nuget/v/aspose-3d-foss.svg)]" in readme
    assert "https://img.shields.io/pypi/" not in readme
    assert "Install the published package from NuGet" in readme
    assert "```bash\ndotnet add package Aspose.ThreeD\n```" in readme
    # Every fence the renderer writes takes the spec's language. The one ```python fence left is
    # an inherited code block, placed verbatim because it is the maintainer's own text.
    assert "```csharp\nfrom aspose.threed import Scene" in readme
    assert readme.count("```python") == 1


def test_import_pattern_is_the_spec_own_not_hard_coded_to_pythons_shape() -> None:
    """G4-W17 arrival items 5 and 11. TypeScript writes `import { Scene } from '@aspose/3d'` -
    the module is a quoted specifier after `from`, never matching the Python-shaped default
    (`import|from {module}` with no quotes). Measured 2026-09-06: every TypeScript and Rust
    example fails this match today, so no Verify-the-install block has ever rendered for either -
    the renderer reads the pattern from the spec so an ecosystem whose examples name a module
    differently states its own, the same as source_install (section 28.12)."""
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if f.id not in {"import_path:aspose.threed", "example:001"}),
            _fact("import_path:aspose.threed", "import_path", "@aspose/3d"),
            _fact(
                "example:001",
                "example",
                "import { Scene } from '@aspose/3d';\nnew Scene().save('a.glb');\n",
            ),
        ),
    )
    default_readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    assert "Verify the install" not in default_readme

    net = EcosystemSpec(
        ecosystem="net",
        language="TypeScript",
        fence="typescript",
        registry="npm",
        install_fact_id="install_command:pip",
        verify_command="node -e \"require('{module}')\"",
        import_pattern=r"(?m)^\s*(?:import|export)\s.*\bfrom\s+['\"]{module}['\"]",
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setitem(SPECS, "net", net)
        entry = ENTRY.model_copy(update={"ecosystem": "net"})
        readme = render_readme(entry, facts, PLAN, UNITS, DISPOSITIONS)
    installation = readme.split("## Installation\n\n", 1)[1].split("\n## ", 1)[0]
    assert "Verify the install:\n\n```bash\nnode -e \"require('@aspose/3d')\"\n```" in installation


def test_a_docstring_description_is_raised_to_the_documents_abbreviation_spelling() -> None:
    """BC-07 judges the whole document, and no repair can rewrite a docstring.

    Measured 2026-09-06: Aspose.Cells reached validation and failed on ``abbreviation 'xlsx' is
    not in its canonical form XLSX``, written by the source's own docstring - the ``glb`` defect
    of docs/RESEARCH_AND_GUIDELINES.md section 27.10, in the one prose path owner decision 2(c)
    of 2026-09-04 did not reach.
    """
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith("public_symbol:")),
            Fact(
                "public_symbol:aspose.threed.scene",
                "public_symbol",
                "aspose.threed.Scene",
                (Evidence("aspose/threed/scene.py", "line 1; class; public by name"),),
                attributes={
                    "symbol_kind": "class",
                    "docstring": "Formula evaluator for xlsx cells; see xlsx_encryptor.",
                },
            ),
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    # The abbreviation takes the spelling the rest of the document uses; a snake_case name keeps
    # its own, because it is an identifier and not a word.
    assert "| `Scene` | Formula evaluator for XLSX cells; see xlsx_encryptor. |" in readme


def test_a_type_without_a_docstring_takes_its_batch_authored_description() -> None:
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *(f for f in FACTS.facts if not f.id.startswith("public_symbol:")),
            Fact(
                "public_symbol:aspose.threed.scene",
                "public_symbol",
                "aspose.threed.Scene",
                (Evidence("aspose/threed/scene.py", "line 1; class; public by name"),),
                attributes={"symbol_kind": "class", "signature": "class Scene(ANode)"},
            ),
        ),
    )
    units = {
        "units": [
            *UNITS["units"],
            _unit(
                "api_reference", "type:public_symbol:aspose.threed.scene", "Holds a scene graph."
            ),
        ],
        "omitted": [],
    }
    readme = render_readme(ENTRY, facts, PLAN, units, DISPOSITIONS)
    assert "| `Scene` | Holds a scene graph. |" in readme.splitlines()
    without = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    assert "| `Scene` | Defined as `class Scene(ANode)`. |" in without.splitlines()


def test_the_enterprise_paragraph_closes_scope_and_limitations_from_the_live_target() -> None:
    target = Fact(
        "link_target:product.enterprise",
        "link_target",
        "https://products.aspose.com/3d/python-net/",
        (Evidence("https://products.aspose.com/3d/python-net/", "HTTP 200; enterprise target"),),
        attributes={"role": "enterprise", "level": "platform", "platform": "python"},
    )
    facts = FactsDocument(ENTRY.repository, "a" * 40, (*FACTS.facts, target))
    plan = {
        **PLAN,
        "sections": [
            {**entry, "include": True}
            if entry["section_id"] == "enterprise_relationship"
            else entry
            for entry in PLAN["sections"]
        ],
    }
    units = {
        "units": [
            *UNITS["units"],
            _unit("enterprise_relationship", "context", "It adds FBX export and rendering."),
        ],
        "omitted": [],
    }
    readme = render_readme(ENTRY, facts, plan, units, DISPOSITIONS)
    scope = readme.split("## Scope and Limitations\n\n", 1)[1].split("\n## ", 1)[0]
    assert scope.rstrip("\n").endswith(
        "These limitations don't apply to [Aspose.3D for Python \u2014 Enterprise Edition]"
        "(https://products.aspose.com/3d/python-net/). It adds FBX export and rendering."
    )
    assert readme.count("Enterprise Edition") == 1
    family = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            Fact(
                target.id,
                target.kind,
                "https://products.aspose.com/3d/",
                target.evidence,
                attributes={"role": "enterprise", "level": "family"},
            ),
        ),
    )
    assert (
        "[Aspose.3D \u2014 Enterprise Edition](https://products.aspose.com/3d/)"
        in render_readme(ENTRY, family, plan, units, DISPOSITIONS)
    )


def test_the_banner_is_a_linked_image_from_both_verified_facts_or_absent() -> None:
    image_url = "https://products.aspose.org/media/3d/python/banner-readme.png"
    homepage_url = "https://products.aspose.org/3d/python/"
    image = Fact(
        "link_target:product.banner",
        "link_target",
        image_url,
        (Evidence(image_url, "HTTP 200; banner illustration"),),
        attributes={"role": "banner illustration"},
    )
    homepage = Fact(
        "link_target:product.homepage",
        "link_target",
        homepage_url,
        (Evidence(homepage_url, "HTTP 200; product homepage"),),
        attributes={"role": "product homepage"},
    )
    plan = {
        **PLAN,
        "sections": [
            {**entry, "include": True} if entry["section_id"] == "banner" else entry
            for entry in PLAN["sections"]
        ],
    }
    facts = FactsDocument(ENTRY.repository, "a" * 40, (*FACTS.facts, image, homepage))
    readme = render_readme(ENTRY, facts, plan, UNITS, DISPOSITIONS)
    lines = readme.split(chr(10))
    banner = f"[![Aspose.3D FOSS for Python]({image_url})]({homepage_url})"
    assert banner in lines
    assert lines[lines.index(banner) - 2].startswith("[![PyPI]")  # immediately below the badges
    assert readme.count("banner-readme.png") == 1
    # One fact alone renders nothing: never an unlinked image, never a broken link.
    one = FactsDocument(ENTRY.repository, "a" * 40, (*FACTS.facts, image))
    assert "banner-readme.png" not in render_readme(ENTRY, one, plan, UNITS, DISPOSITIONS)


def test_at_a_glance_is_the_one_chain_of_section_2_1() -> None:
    lines = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS).splitlines()
    start = lines.index("## At a Glance")
    end = lines.index("## Key Capabilities")
    section = [line for line in lines[start + 1 : end] if line.strip()]
    assert section == [
        "```mermaid",
        "flowchart TD",
        '  subgraph StartingPoints["Starting Points"]',
        "    direction LR",
        '    i1["An existing OBJ file"]',
        "  end",
        '  PRODUCT["Aspose.3D FOSS for Python"]',
        '  subgraph Capabilities["Core Capabilities"]',
        "    direction TB",
        '    c1["Build scenes"]',
        '    c2["Save GLB"]',
        "  end",
        '  subgraph Outputs["Outputs"]',
        "    direction TB",
        '    o1["GLB file"]',
        "  end",
        "  StartingPoints --> PRODUCT --> Capabilities --> Outputs",
        "```",
    ]


def test_at_a_glance_drops_absent_groups_and_balances_six_or_more_capabilities() -> None:
    titles = ["Build scenes", "Save GLB", "Read OBJ", "Write STL", "Merge meshes", "Bake lights"]
    plan = {
        **PLAN,
        "at_a_glance": {
            "input_format_ids": [],
            "output_format_ids": [],
            "capability_titles": titles,
        },
    }
    readme = render_readme(ENTRY, FACTS, plan, UNITS, DISPOSITIONS)
    assert "StartingPoints" not in readme and 'subgraph Outputs["Outputs"]' not in readme
    assert "  PRODUCT --> Capabilities" + chr(10) in readme
    assert '    subgraph capl[" "]' in readme and '    subgraph capr[" "]' in readme
    assert '      c3["Read OBJ"]' in readme and '      c4["Write STL"]' in readme
    assert "~~~" not in readme


def test_the_flagship_example_stands_visible_before_the_collapsed_block() -> None:
    collapsed = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert "<details>" + chr(10) + "<summary>View Additional Examples</summary>" in collapsed
    assert collapsed.index("<details>") < collapsed.index("### Print a number")
    flagship = {**PLAN, "flagship_example_id": "example:002"}
    readme = render_readme(ENTRY, FACTS, flagship, UNITS, DISPOSITIONS)
    section = readme.split("## Additional Examples" + chr(10), 1)[1].split(chr(10) + "## ", 1)[0]
    # The one further example is the flagship, so nothing remains for a collapsed block.
    assert section.strip().splitlines() == [
        "One more workflow follows.",
        "",
        "### Print a number",
        "",
        "```python",
        "print(2)",
        "```",
    ]
    assert "View Additional Examples" not in section


def test_two_verified_types_sharing_a_name_keep_distinct_table_rows() -> None:
    # README_CONTRACT.md row 14: the complete verified surface, so both types stay, under the
    # shortest dotted suffixes that tell them apart (the canary ships two ColladaLoadOptions).
    def symbol(value: str, docstring: str) -> Fact:
        return Fact(
            f"public_symbol:{value.lower()}",
            "public_symbol",
            value,
            (Evidence("aspose/threed/formats.py", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class", "docstring": docstring},
        )

    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            *FACTS.facts,
            symbol("aspose.threed.formats.ColladaLoadOptions", "Options for COLLADA loading."),
            symbol("aspose.threed.formats.ColladaLoadOptions.ColladaLoadOptions", "Load options."),
        ),
    )
    readme = render_readme(ENTRY, facts, PLAN, UNITS, DISPOSITIONS)
    assert "| `formats.ColladaLoadOptions` | Options for COLLADA loading. |" in readme
    assert "| `ColladaLoadOptions.ColladaLoadOptions` | Load options. |" in readme
    assert readme.count("| `ColladaLoadOptions` |") == 0
    assert "| `Scene` |" in readme  # an unshared name keeps its final segment


def test_prose_raises_a_known_abbreviation_to_its_canonical_form() -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.10: the code owns the spelling, so it normalises the
    # casing instead of re-asking the model; BC-07 then judges a document already canonical. A
    # cold composition lost a whole transaction to "abbreviation 'glb' is not in its canonical
    # form GLB", which the repair loop could not route.
    context = RenderContext(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    assert context.prose("Scenes save as glb files.") == "Scenes save as GLB files."
    assert context.prose("The api returns json.") == "The API returns JSON."
    # Only a format these facts record is an abbreviation here, so another product's extension
    # stays as written and the check keeps its say over it.
    assert context.prose("Scenes save as gltf files.") == "Scenes save as gltf files."
    # A word that only looks like one is left alone, and a dotted extension is an identifier.
    assert context.prose("The scene is saved.") == "The scene is saved."
    assert "`.glb`" in context.prose("Files use the .glb extension.")
