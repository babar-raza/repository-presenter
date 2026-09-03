"""The renderer owns the Markdown: sections in shell order, identifiers in code spans, verbatim."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.renderer import (
    RenderContext,
    anchor,
    line_counts,
    render_patch,
    render_readme,
    renders_verbatim,
    write_text,
)
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
        _fact(
            "public_symbol:aspose.threed.scene",
            "public_symbol",
            "aspose.threed.Scene",
            "line 1; class; public by name",
        ),
        _fact(
            "public_symbol:aspose.threed.scene.scene.save",
            "public_symbol",
            "aspose.threed.Scene.Scene.save",
            "line 9; method; public by name",
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
            "include": s not in {"dependencies", "enterprise_relationship", "third_party_notices"},
            "reason": "r",
        }
        for s in [
            "identity",
            "badges",
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
        _unit(
            "api_reference", "hub:public_symbol:aspose.threed.scene", "Scene holds the scene graph."
        ),
        _unit("documentation_resources", "resources", "The docs explain the API."),
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
    assert "```mermaid" in lines and '  I1["OBJ"] --> P' in lines and '    O1["GLB"]' in lines
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
    assert "<summary>Print a number</summary>" in lines
    assert "- `aspose.threed.Scene`: `Scene` holds the scene graph." in lines
    assert "- [Docs](https://docs.example.com/3d)" in lines
    assert "- OBJ import is unverified." in lines
    assert "Kept verbatim from the old README." in lines
    assert "## Old limitations heading" not in lines
    assert lines.count("## Scope and Limitations") == 1
    assert readme.count("print(2)") == 1
    assert "- `tests/`" in lines
    assert lines[-1] == (
        "This project is licensed under the [MIT License](LICENSE). The MIT License permits use, "
        "copying, modification, distribution, sublicensing, and commercial use, provided its "
        "copyright and permission notice are retained. The software is provided without warranty."
    )
    assert readme.endswith("\n") and "\r" not in readme and "\n\n\n" not in readme
    assert render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS) == readme


def test_headings_anchor_like_github_and_line_counts_skip_details() -> None:
    assert anchor("Documentation and Resources") == "documentation-and-resources"
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
