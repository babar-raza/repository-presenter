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

    ``version_badge`` and ``source_install`` are templates over ``{package}`` and ``{repository}``
    and ``{name}``; a spec that needs none leaves them empty and the renderer prints nothing,
    which is what a registry-less ecosystem (C++) requires.
    """

    ecosystem: str
    language: str
    fence: str
    registry: str
    install_fact_id: str
    version_badge: str = ""
    verify_command: str = ""
    # Per-ecosystem, up to core.execution's ceiling (section 29.6 E5): an interpreted example
    # returns in seconds, a compiled one pays for a restore and a build first.
    example_timeout_seconds: float = 120.0
    install_timeout_seconds: float = 300.0
    symbol_separator: str = "."
    manifest_globs: tuple[str, ...] = ()
    source_suffixes: frozenset[str] = field(default_factory=frozenset)

    def badge(self, package: str) -> str:
        """The registry's version badge for this package, or an empty string when it has none."""
        return self.version_badge.format(package=package) if self.version_badge else ""


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
    verify_command='python -c "import {module}"',
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
    # `dotnet list package` needs a project; `--include-transitive` is the form that reports a
    # reference added by `dotnet add package` without one.
    verify_command="dotnet list package --include-transitive | findstr {module}",
    # A restore and a build cost far more than an interpreted example: the ceiling in
    # core.execution is 300 seconds and a cold restore has been seen to use most of it.
    example_timeout_seconds=300.0,
    install_timeout_seconds=300.0,
    manifest_globs=("*.csproj", "*.fsproj", "Directory.Build.props"),
    source_suffixes=frozenset({".cs"}),
)

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
