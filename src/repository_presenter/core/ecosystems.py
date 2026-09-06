"""What one ecosystem declares about itself, so shared code never asks which one it is.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3 and E4: a plugin is a declarative composition, and the
fence language, the badges, the Installation block and the registry's display name read from the
spec rather than from a branch on the ecosystem name. Adding an ecosystem is a spec, a verifier,
and a negative-control test - never an edit to a shared file.

This lives in `core/` because both sides need it and neither may import the other: an extractor
imports only `core/` and its own module, and no stage after facts imports an extractor at all
(`docs/REPOSITORY_LAYOUT.md` §2.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from repository_presenter.core.errors import ConfigError


@dataclass(frozen=True)
class EcosystemSpec:
    """One ecosystem's presentation and identity vocabulary.

    ``version_badge`` is a template over ``{package}``; ``source_install`` over ``{repository}``
    and ``{name}``. A spec that needs none leaves them empty and the renderer prints nothing,
    which is what a registry-less ecosystem (C++) requires.
    """

    ecosystem: str
    language: str
    fence: str
    registry: str
    install_fact_id: str
    version_badge: str = ""
    source_install: str = ""
    # The verb phrase that completes "To work from a source checkout instead, {...}:" - carried
    # apart from the command itself only so Python's sealed wording never moves a single byte.
    source_install_lead: str = ""
    verify_command: str = ""
    # Per-ecosystem, up to core.execution's ceiling (section 29.6 E5): an interpreted example
    # returns in seconds, a compiled one pays for a restore and a build first.
    example_timeout_seconds: float = 120.0
    install_timeout_seconds: float = 300.0
    symbol_separator: str = "."
    # The fence languages a README may write an example in. Empty means the fence itself,
    # which is right for python and wrong for C#, where readers write csharp, cs and c#.
    fence_aliases: frozenset[str] = field(default_factory=frozenset)
    # The runtime floor the Dependencies row reports: which fact carries it, what to call the
    # runtime, and what the manifest calls the declaration. An ecosystem that declares no floor
    # leaves these empty and the renderer prints no requirement, which is honest.
    floor_fact_id: str = ""
    floor_label: str = ""
    floor_declaration: str = ""
    manifest_globs: tuple[str, ...] = ()
    source_suffixes: frozenset[str] = field(default_factory=frozenset)

    @property
    def example_fences(self) -> frozenset[str]:
        """Every fence language that marks an example of this ecosystem."""
        return self.fence_aliases or frozenset({self.fence})

    def badge(self, package: str) -> str:
        """The registry's version badge for this package, or an empty string when it has none."""
        return self.version_badge.format(package=package) if self.version_badge else ""

    def clone_and_build(self, repository: str, name: str) -> str:
        """The shell commands that build this ecosystem's package from a source checkout, or an
        empty string when the ecosystem declares none.

        Measured 2026-09-06: `_installation` hard-coded `pip install .` for every ecosystem with
        an executed example, so Aspose.Cells and Aspose.3D for .NET - both sealed - told a reader
        to run `pip install .` against a C# project. The command is the ecosystem's own to name;
        shared code only ever fills in the repository and its checkout directory name.
        """
        if not self.source_install:
            return ""
        return self.source_install.format(repository=repository, name=name)


PYTHON: Final = EcosystemSpec(
    ecosystem="python",
    language="Python",
    fence="python",
    registry="PyPI",
    install_fact_id="install_command:pip",
    version_badge=(
        "[![PyPI](https://img.shields.io/pypi/v/{package}.svg)]"
        "(https://pypi.org/project/{package}/)"
    ),
    source_install="git clone https://github.com/{repository}.git\ncd {name}\npip install .",
    source_install_lead="install the clone with pip",
    verify_command='python -c "import {module}"',
    fence_aliases=frozenset({"python", "py", "python3"}),
    floor_fact_id="package:python_requires",
    floor_label="Python",
    floor_declaration="python_requires",
    manifest_globs=("pyproject.toml", "setup.cfg", "setup.py"),
    source_suffixes=frozenset({".py"}),
)

NET: Final = EcosystemSpec(
    ecosystem="net",
    language="C#",
    fence="csharp",
    registry="NuGet",
    install_fact_id="install_command:dotnet",
    version_badge=(
        "[![NuGet](https://img.shields.io/nuget/v/{package}.svg)]"
        "(https://www.nuget.org/packages/{package}/)"
    ),
    # There is no single-line "install into your own project" step without knowing the
    # consumer's own setup; a build is the honest claim - it proves the source compiles, which is
    # what "work from a source checkout" can mean for .NET.
    source_install="git clone https://github.com/{repository}.git\ncd {name}\ndotnet build",
    source_install_lead="build the clone with dotnet build",
    # `dotnet list package` needs a project; `--include-transitive` is the form that reports a
    # reference added by `dotnet add package` without one.
    verify_command="dotnet list package --include-transitive | findstr {module}",
    # A restore and a build cost far more than an interpreted example: the ceiling in
    # core.execution is 300 seconds and a cold restore has been seen to use most of it.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"csharp", "cs", "c#"}),
    floor_fact_id="package:target_framework",
    floor_label=".NET",
    floor_declaration="TargetFramework",
    manifest_globs=("*.csproj", "*.fsproj", "Directory.Build.props"),
    source_suffixes=frozenset({".cs"}),
)

# Deliberately a plain, mutable dict and not Final, unlike PYTHON and NET beside it: this file
# owns only the two built-in specs above; an ecosystem outside it (a platform lane owns) registers
# its own by calling ``SPECS.setdefault(ecosystem, spec)`` from its own ``platforms/<ecosystem>.py``
# module at import time, never by adding a line here - core/ may not import an extractor (this
# file's own docstring, docs/REPOSITORY_LAYOUT.md section 2.1), so the mirror of registry.py's
# PLUGIN discovery a lane would otherwise expect is not implementable from this side of that
# boundary. `plugin_for(ecosystem)` (extractors/platforms/registry.py) already imports that module
# before any stage asks `spec_for` for the same ecosystem in every path that exists today
# (RESEARCH_AND_GUIDELINES.md section 28.12 G4-W17 arrival item 3), so registration is in place by
# the time it is needed without this file ever crossing the boundary to guarantee it itself.
SPECS: dict[str, EcosystemSpec] = {PYTHON.ecosystem: PYTHON, NET.ecosystem: NET}


def spec_for(ecosystem: str) -> EcosystemSpec:
    """The spec for ``ecosystem``; an unregistered one is a configuration failure, as it is for a
    plugin - a document rendered with guessed vocabulary would be worse than no document."""
    spec = SPECS.get(ecosystem)
    if spec is None:
        raise ConfigError(
            f"no ecosystem spec registered for {ecosystem!r} (known: {', '.join(sorted(SPECS))})"
        )
    return spec
