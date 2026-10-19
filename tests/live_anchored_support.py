"""A small synthetic README with a verified-facts document and one operation of every kind.

Shared by ``tests/components/readme_correction/test_live_ops.py`` (the rules) and
``test_live_anchored.py`` (the bundle, the gate, the pull request text and the CLI): the README is
shaped like a live Aspose FOSS README that predates the family standard (``Features``, ``Quick
start``, ``Scope``, ``Development``, two badge lines, a link to a file the repository lacks), and
``good_ops`` brings it to the standard with the four operation kinds and nothing else.
"""

from __future__ import annotations

from repository_presenter.components.readme_correction.live_ops import (
    DELETE_LINE,
    INSERT_BEFORE,
    REFLOW,
    RETITLE,
    Op,
)
from repository_presenter.components.readme_diagram.build import build_body
from repository_presenter.components.readme_diagram.model import Glance
from repository_presenter.core.facts import Evidence, Fact

NL = "\n"
REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
BADGES = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)\n"
    "[![Maven](https://img.shields.io/badge/maven-central-blue.svg)]"
    "(https://central.sonatype.com/artifact/org.aspose/aspose-3d-foss)\n"
)
RELEASE_LINE = "- Read the [release notes](RELEASE_NOTES.md).\n"

README = (
    "# Aspose.3D FOSS for Java\n\n"
    + BADGES
    + "\nAspose.3D FOSS for Java is a free, open-source library for reading and writing OBJ and "
    "STL files.\n\n"
    "## Features\n\n"
    "- Read OBJ files into a scene\n"
    "- Write STL files from a scene\n"
    "- Convert OBJ files to STL files\n\n"
    "## Installation\n\n"
    "```bash\nmvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n\n"
    "Needs Java 17. Optional: `jackson-databind:2.17.0` for the JSON export.\n\n"
    "## Quick start\n\n"
    "Run the example.\n\n"
    "### Read a scene\n\n"
    "See the example.\n\n"
    "## Scope\n\n"
    "- Only OBJ and STL are supported.\n"
    + RELEASE_LINE
    + "- Read the [changelog](CHANGELOG.md).\n\n"
    "## Development\n\n"
    "Run `mvn test`.\n\n"
    "## License\n\n"
    "MIT.\n"
)
TREE = ("README.md", "LICENSE", "pom.xml", "CHANGELOG.md")

NAVIGATION = (
    "## Navigation\n\n"
    "- [At a Glance](#at-a-glance)\n"
    "- [Key Capabilities](#key-capabilities)\n"
    "- [Installation](#installation)\n"
    "- [Dependencies](#dependencies)\n"
    "- [Quick Start](#quick-start)\n"
    "- [Scope and Limitations](#scope-and-limitations)\n"
    "- [Development and Testing](#development-and-testing)\n"
    "- [License](#license)\n\n"
)
GLANCE = Glance(
    product="Aspose.3D FOSS for Java",
    starting_points=("OBJ files",),
    capability_columns=(
        (
            "Read OBJ files into a scene",
            "Write STL files from a scene",
            "Convert OBJ files to STL files",
        ),
    ),
    outputs=("STL files",),
)
AT_A_GLANCE = "## At a Glance\n\n```mermaid\n" + build_body(GLANCE) + "```\n\n"
DEPENDENCIES = (
    "## Dependencies\n\n"
    "### Required Package Dependencies\n\n"
    "- `com.google.guava:guava:33.0`\n\n"
    "### Optional Dependencies\n\n"
    "- `jackson-databind:2.17.0` for the JSON export.\n\n"
    "### Development Dependencies\n\n"
    "- `junit:junit:4.13.2` (extra `dev`)\n\n"
)


def line_of(needle: str, text: str = README) -> int:
    return text.count(NL, 0, text.index(needle)) + 1


def extra_facts() -> list[Fact]:
    """The facts the operations cite, beside the conftest base facts."""

    def fact(fact_id: str, value: str, polarity: str = "SUPPORTED", detail: str = "") -> Fact:
        return Fact(
            id=fact_id,
            kind=fact_id.split(":", 1)[0],  # type: ignore[arg-type]
            value=value,
            evidence=(Evidence("pom.xml", detail or None),),
            polarity=polarity,  # type: ignore[arg-type]
        )

    return [
        fact("dependency:guava", "com.google.guava:guava:33.0"),
        fact("dependency:development.junit", "junit:junit:4.13.2", detail="extra 'dev' declared"),
        fact("link_target:001", "https://img.shields.io/badge/License-MIT-blue.svg"),
        fact("link_target:002", "LICENSE"),
        fact("link_target:003", "https://img.shields.io/badge/maven-central-blue.svg"),
        fact(
            "link_target:004",
            "https://central.sonatype.com/artifact/org.aspose/aspose-3d-foss",
        ),
        fact("link_target:005", "RELEASE_NOTES.md", "CONTRADICTED"),
        fact("link_target:006", "CHANGELOG.md"),
    ]


def make(op_id: str, kind: str, anchor: str, replacement: str, *evidence: str) -> Op:
    return Op(op_id, kind, anchor, replacement, tuple(evidence))


def retitle(op_id: str, old: str, new: str, text: str = README) -> Op:
    return make(op_id, RETITLE, old + NL, new + NL, f"readme:{line_of(old + NL, text)}")


def good_ops() -> list[Op]:
    """Every kind once or more; applied to ``README`` they give ``corrected()``."""
    features = "## Features\n"
    quick = "## Quick start\n"
    return [
        make(
            "badges",
            REFLOW,
            BADGES,
            BADGES.replace(")\n[", ") ["),
            "link_target:001",
            "link_target:003",
            f"readme:{line_of('[![License')}",
        ),
        make(
            "nav",
            INSERT_BEFORE,
            features,
            NAVIGATION + AT_A_GLANCE + features,
            f"readme:{line_of(features)}",
        ),
        retitle("features", "## Features", "## Key Capabilities"),
        make(
            "deps",
            INSERT_BEFORE,
            quick,
            DEPENDENCIES + quick,
            "dependency:guava",
            "dependency:development.junit",
            f"readme:{line_of('jackson-databind')}",
        ),
        retitle("quick", "## Quick start", "## Quick Start"),
        retitle("sub", "### Read a scene", "### Read a Scene"),
        retitle("scope", "## Scope", "## Scope and Limitations"),
        make(
            "release",
            DELETE_LINE,
            RELEASE_LINE,
            "",
            "link_target:005",
            f"readme:{line_of('release notes')}",
        ),
        retitle("dev", "## Development", "## Development and Testing"),
    ]


def corrected() -> str:
    """What ``good_ops`` make of ``README``, written out by hand."""
    text = README.replace(BADGES, BADGES.replace(")\n[", ") ["))
    text = text.replace("## Features\n", NAVIGATION + AT_A_GLANCE + "## Key Capabilities\n")
    text = text.replace("## Quick start\n", DEPENDENCIES + "## Quick Start\n")
    text = text.replace("### Read a scene\n", "### Read a Scene\n")
    text = text.replace("## Scope\n", "## Scope and Limitations\n")
    text = text.replace(RELEASE_LINE, "")
    return text.replace("## Development\n", "## Development and Testing\n")
