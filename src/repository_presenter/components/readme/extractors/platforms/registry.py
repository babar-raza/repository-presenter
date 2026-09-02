"""The platform plugin registry: ecosystems are added as entries, never as new call sites."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from repository_presenter.components.readme.extractors.platforms.python import PythonPlugin
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.facts import Fact


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

    def registry_facts(self, facts: Sequence[Fact]) -> list[Fact]:
        """Facts re-issued with the package registry's observation; matched by ID on merge."""

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        """Run every candidate against the repository's own package in isolation."""


_PLUGINS: dict[str, PlatformPlugin] = {plugin.ecosystem: plugin for plugin in (PythonPlugin(),)}


def known_ecosystems() -> tuple[str, ...]:
    return tuple(sorted(_PLUGINS))


def plugin_for(ecosystem: str) -> PlatformPlugin:
    """The registered plugin for ``ecosystem``; a missing plugin is a configuration failure."""
    plugin = _PLUGINS.get(ecosystem)
    if plugin is None:
        raise ConfigError(
            f"no platform plugin registered for ecosystem {ecosystem!r} "
            f"(known: {', '.join(known_ecosystems())})"
        )
    return plugin
