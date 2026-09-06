"""Plugins are found through the registry; an unknown ecosystem is a configuration failure."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.extractors.platforms.python import PythonPlugin
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.errors import ConfigError


def test_python_is_the_first_registered_plugin() -> None:
    # .NET joined at G4-W11, TypeScript at G4-W14, Go at G4-W15 and Java at G4-W12; discovery
    # finds each without this module listing it, and this assertion is the only line any had
    # to change.
    assert known_ecosystems() == ("go", "java", "net", "python", "typescript")
    plugin = plugin_for("python")
    assert isinstance(plugin, PythonPlugin)
    assert plugin.manifest_globs == ("pyproject.toml", "setup.cfg", "setup.py")
    assert plugin.source_suffixes == frozenset({".py"})
    assert [(c.direction, c.extension) for c in plugin.format_claims('s.save("a.glb")\n')] == [
        ("output", ".glb")
    ]


def test_unknown_ecosystem_fails_closed() -> None:
    with pytest.raises(ConfigError, match="no platform plugin registered for ecosystem 'cobol'"):
        plugin_for("cobol")


def test_a_plugin_is_discovered_by_module_name_and_its_plugin_attribute() -> None:
    """Adding an ecosystem is adding its file; this registry never lists plugins.

    Section 29.6 E3 and docs/REPOSITORY_LAYOUT.md section 2.1. Six helper modules sit beside
    python.py in the same package - python_surface, python_examples, python_registry,
    python_formats, python_format_declarations, python_setup_py - and none of them is an
    ecosystem, because none exposes PLUGIN.
    """
    from repository_presenter.components.readme.extractors.platforms import python

    assert python.PLUGIN is plugin_for("python")
    assert plugin_for("python") is plugin_for("python")  # resolved once, then cached
    assert known_ecosystems() == ("go", "java", "net", "python", "typescript")
    # A module that exists in the package but exposes no PLUGIN is not an ecosystem.
    with pytest.raises(ConfigError, match="'python_surface'"):
        plugin_for("python_surface")
    # The same holds for TypeScript's two helper modules, added at G4-W14.
    with pytest.raises(ConfigError, match="'typescript_barrel'"):
        plugin_for("typescript_barrel")
    # And for Go's verifier module, added at G4-W15.
    with pytest.raises(ConfigError, match="'go_examples'"):
        plugin_for("go_examples")
    # And for Java's, added at G4-W12.
    with pytest.raises(ConfigError, match="'java_examples'"):
        plugin_for("java_examples")
