"""The platform plugin registry: ecosystems are added as entries, never as new call sites."""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from types import ModuleType
from typing import Protocol

from repository_presenter.core.errors import ConfigError
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repository_presenter.core.facts import Fact
from repository_presenter.core.probes import ProbeRecord


class PlatformPlugin(Protocol):
    """What every ecosystem plugin provides to the facts stage."""

    ecosystem: str
    manifest_globs: tuple[str, ...]
    source_suffixes: frozenset[str]

    def detect_manifest(self, root: Path) -> Path | None:
        """The manifest that governs the package at ``root``, if any."""

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Package, version, Python range, import path, and install facts from the manifest."""

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """Public symbols of the product packages, read statically from the tree."""

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Facts re-issued with the package registry's observation, matched by ID on merge, and
        the probe record of the read itself - status, timing, and the volatile reading a fact
        must not carry (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC7)."""

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        """Run every candidate against the repository's own package in isolation."""

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """The extensions one example's statements load or save, read from its syntax tree."""

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """The product's static format declarations and plugin registrations, from its tree."""


_ATTRIBUTE = "PLUGIN"
_loaded: dict[str, PlatformPlugin] = {}


def _module_for(ecosystem: str) -> ModuleType | None:
    """``platforms/<ecosystem>.py``, or None when the ecosystem names no module."""
    try:
        return import_module(f"{__package__}.{ecosystem}")
    except ImportError:
        return None


def known_ecosystems() -> tuple[str, ...]:
    """Every module beside this one that exposes ``PLUGIN``.

    Discovery is by module name, so adding an ecosystem is adding its file: this module never
    lists plugins and never grows a registration line (RESEARCH_AND_GUIDELINES.md section 29.6
    E3; docs/REPOSITORY_LAYOUT.md section 2.1). A helper module beside a plugin - python_surface,
    python_examples - exposes no PLUGIN and is not one.
    """
    found: list[str] = []
    for info in iter_modules([str(Path(__file__).parent)]):
        if info.name == Path(__file__).stem:
            continue
        module = _module_for(info.name)
        if module is not None and hasattr(module, _ATTRIBUTE):
            found.append(info.name)
    return tuple(sorted(found))


def plugin_for(ecosystem: str) -> PlatformPlugin:
    """The plugin ``platforms/<ecosystem>.py`` exposes; a missing one is a configuration failure."""
    if ecosystem not in _loaded:
        module = _module_for(ecosystem)
        plugin = getattr(module, _ATTRIBUTE, None) if module is not None else None
        if plugin is None:
            raise ConfigError(
                f"no platform plugin registered for ecosystem {ecosystem!r} "
                f"(known: {', '.join(known_ecosystems())})"
            )
        _loaded[ecosystem] = plugin
    return _loaded[ecosystem]
