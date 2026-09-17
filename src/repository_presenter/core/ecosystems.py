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

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from repository_presenter.core.errors import ConfigError

# The checkout every source install starts from. An ecosystem's own build steps follow it, whether
# a spec's ``source_install`` template spells them or a verifier's receipt names the exact steps it
# proved for one repository (G4-W17 arrival item 50); the templates below spell this same prefix.
CLONE_PREFIX: Final = "git clone https://github.com/{repository}.git\ncd {name}\n"


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
    # A template over {repository}, {name} and {paths} for an ecosystem where a build/install
    # command can fail identically for every possible invocation (RESEARCH_LANE_E.md's
    # documented-PYTHONPATH-source-install observation, LANE-E-06/LANE-E-14/LANE-E-17):
    # `clone_and_reference` fills it with the checkout and the source directories `_source_roots`
    # already found an executed example import from, uninstalled - never a build step, since by
    # definition none succeeded. Empty means the ecosystem has no such fallback vocabulary (a
    # compiled language proves nothing by adding a directory to an interpreter's path); only
    # Python declares one today.
    source_reference: str = ""
    verify_command: str = ""
    # Whether an executed example's own source actually names a given import_path fact, so the
    # renderer knows which module to plug into verify_command - a template over {module}, matched
    # against one line of the example. The default is Python's own shape (also TypeScript's or
    # Java's plain `import x`); an ecosystem whose examples name a module differently (a quoted
    # specifier after `from`, C++'s `#include`, Rust's `use`) names its own here instead of the
    # renderer guessing a syntax that will never match. Measured 2026-09-06 on Aspose.3D for
    # TypeScript (RESEARCH_AND_GUIDELINES.md section 28.12 G4-W17 arrival items 5 and 11): every
    # TypeScript example writes `import { Scene } from '@aspose/3d'`, which the Python-shaped
    # default never matches, so no TypeScript or Rust candidate has ever rendered a Verify-the-
    # install block - the mechanism is landed here; each ecosystem's own pattern is its spec's to
    # set, the same as source_install.
    import_pattern: str = r"(?m)^\s*(?:import|from)\s+{module}\b"
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
    # The manifest field the floor sentence names, ecosystem-wide - the fallback for a repository
    # whose floor fact carries no more precise one of its own in its
    # `attributes["floor_declaration"]` (RESEARCH_AND_GUIDELINES.md section 28.12 G4-W17 arrival
    # item 14). A POM may declare
    # `maven.compiler.release`, `.target` or `.source`; three of the four repositories in one
    # cohort each used a different one, so naming any single property here would cite one three
    # of four repositories do not declare - a fabricated citation, not a generic-but-honest one.
    floor_declaration: str = ""
    manifest_globs: tuple[str, ...] = ()
    source_suffixes: frozenset[str] = field(default_factory=frozenset)

    @property
    def example_fences(self) -> frozenset[str]:
        """Every fence language that marks an example of this ecosystem."""
        return self.fence_aliases or frozenset({self.fence})

    def badge(self, package: str) -> str:
        """The registry's version badge for this package, or an empty string when it has none.

        ``{package}`` is the coordinate exactly as ``package:name`` spells it. A registry whose
        badge URL takes two path segments, not one, splits it on its own separator instead: a
        Maven Central badge is one path segment per fact ID, and shields.io's endpoint is
        ``img.shields.io/maven-central/v/{groupId}/{artifactId}`` - two segments - while Java's
        `package:name` is the colon-joined coordinate a build file actually declares
        (`org.aspose:aspose-3d-foss`), which no single `{package}` token fits (RESEARCH_AND_
        GUIDELINES.md section 28.12 G4-W17 arrival item 13). `{group}` and `{artifact}` are
        offered alongside `{package}` for a template that needs them; an ecosystem whose
        coordinate carries no colon leaves `{artifact}` equal to `{package}`, so a one-segment
        template naming only `{package}` is unaffected.
        """
        if not self.version_badge:
            return ""
        group, _, artifact = package.partition(":")
        return self.version_badge.format(package=package, group=group, artifact=artifact or group)

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

    def clone_and_run(self, repository: str, name: str, steps: str) -> str:
        """The checkout, then the ``steps`` a verifier drove and proved for this repository.

        G4-W17 arrival item 50: a receipt names the exact steps that exited 0 against one
        repository (`npm install`, or `npm install` then `npm run build`), and those outrank the
        ecosystem-wide template - which TypeScript does not even declare, because no one command
        is true for both of its repositories. The same prefix as every template, so a measured
        command and a templated one read alike to a reader and to BC-02.
        """
        if not steps:
            raise ValueError("a measured source build names at least one step")
        return CLONE_PREFIX.format(repository=repository, name=name) + steps

    def clone_and_reference(self, repository: str, name: str, roots: Sequence[str]) -> str:
        """The checkout, then adding its own source directories to the interpreter's path -
        never a build command (`RESEARCH_LANE_E.md`'s documented-PYTHONPATH-source-install
        observation).

        For a repository where every build/install attempt fails identically - a broken
        build-backend, not broken code - an example that ran via the source-tree fallback still
        proves the code imports and runs. ``roots`` are the paths `_source_roots` already found
        it running from, uninstalled: relative to the checkout, nearest first, ``"."`` meaning
        the checkout root itself. An ecosystem that declares no ``source_reference`` template (a
        build/install failure means something different for a compiled language) or a caller
        with no roots to name returns an empty string, so the fact this backs stays untouched
        rather than admitting a placeholder nobody measured.
        """
        if not self.source_reference or not roots:
            return ""
        return self.source_reference.format(repository=repository, name=name, paths=":".join(roots))


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
    # PYTHONPATH is the honest fallback when no build/install command ever succeeds
    # (RESEARCH_LANE_E.md's documented-PYTHONPATH-source-install observation): a colon-joined
    # list of the directories an executed example already imported the package from, uninstalled
    # - never a build step, since none was proven.
    source_reference=(
        "git clone https://github.com/{repository}.git\n"
        "cd {name}\n"
        'export PYTHONPATH="{paths}:$PYTHONPATH"'
    ),
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
