"""An ecosystem declares its own vocabulary; shared code never branches on its name."""

from __future__ import annotations

import pytest

from repository_presenter.core.ecosystems import PYTHON, SPECS, EcosystemSpec, spec_for
from repository_presenter.core.errors import ConfigError


def test_the_python_spec_carries_what_the_renderer_used_to_hard_code() -> None:
    spec = spec_for("python")
    assert spec is PYTHON
    assert spec.fence == "python" and spec.registry == "PyPI"
    assert spec.install_fact_id == "install_command:pip"
    assert spec.badge("aspose-3d-foss") == (
        "[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)]"
        "(https://pypi.org/project/aspose-3d-foss/)"
    )
    assert spec.verify_command.format(module="aspose.threed") == 'python -c "import aspose.threed"'


def test_an_ecosystem_with_no_registry_prints_no_badge() -> None:
    """C++ has no package registry (section 29.6 E3), so its spec leaves the template empty."""
    spec = EcosystemSpec(
        ecosystem="cpp",
        language="C++",
        fence="cpp",
        registry="no package registry",
        install_fact_id="install_command:cmake",
    )
    assert spec.badge("anything") == ""


def test_an_unregistered_ecosystem_fails_closed() -> None:
    """A document rendered with guessed vocabulary is worse than no document."""
    with pytest.raises(ConfigError, match="no ecosystem spec registered for 'klingon'"):
        spec_for("klingon")


def test_a_spec_is_registered_by_name_and_nothing_else_is_needed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adding an ecosystem is one spec: section 29.6 E3's whole point."""
    added = EcosystemSpec(
        ecosystem="net",
        language="C#",
        fence="csharp",
        registry="NuGet",
        install_fact_id="install_command:dotnet",
    )
    monkeypatch.setitem(SPECS, "net", added)
    assert spec_for("net") is added
