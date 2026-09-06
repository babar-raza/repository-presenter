"""Plugins are found through the registry; an unknown ecosystem is a configuration failure."""

from __future__ import annotations

import re
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

import pytest

from repository_presenter.components.readme.extractors import platforms as _platforms_package
from repository_presenter.components.readme.extractors.platforms.python import PythonPlugin
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
    plugin_for,
)
from repository_presenter.core.errors import ConfigError


def _package_module_names() -> list[str]:
    """Every module beside `registry.py` itself in `extractors/platforms/`, ecosystem or not."""
    directory = str(Path(_platforms_package.__file__).parent)
    return sorted(info.name for info in iter_modules([directory]) if info.name != "registry")


def test_python_is_the_first_registered_plugin() -> None:
    # G4-W17 item 6: no lane touches this file to add its own ecosystem's name - discovery finds
    # each without this module listing any, so the assertion checks a property, never a roster.
    assert "python" in known_ecosystems()
    assert known_ecosystems() == tuple(sorted(known_ecosystems()))
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
    """Adding an ecosystem is adding its file; this registry never lists plugins, and neither
    does this test (G4-W17 item 6) - every module beside `registry.py` is read from the package
    directory itself, so a lane's own helper module (python_surface, typescript_barrel,
    cpp_examples, and the rest) needs no name added here to stay proven not an ecosystem.
    """
    from repository_presenter.components.readme.extractors.platforms import python

    assert python.PLUGIN is plugin_for("python")
    assert plugin_for("python") is plugin_for("python")  # resolved once, then cached
    ecosystems = known_ecosystems()
    for name in _package_module_names():
        module = import_module(
            f"repository_presenter.components.readme.extractors.platforms.{name}"
        )
        if hasattr(module, "PLUGIN"):
            assert name in ecosystems
        else:
            assert name not in ecosystems
            with pytest.raises(ConfigError, match=re.escape(repr(name))):
                plugin_for(name)
