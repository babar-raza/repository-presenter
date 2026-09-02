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
    assert known_ecosystems() == ("python",)
    plugin = plugin_for("python")
    assert isinstance(plugin, PythonPlugin)
    assert plugin.manifest_globs == ("pyproject.toml", "setup.cfg", "setup.py")
    assert plugin.source_suffixes == frozenset({".py"})


def test_unknown_ecosystem_fails_closed() -> None:
    with pytest.raises(ConfigError, match="no platform plugin registered for ecosystem 'net'"):
        plugin_for("net")
