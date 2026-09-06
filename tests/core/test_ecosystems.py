"""An ecosystem declares its own vocabulary; shared code never branches on its name."""

from __future__ import annotations

import pytest

from repository_presenter.core.ecosystems import NET, PYTHON, SPECS, EcosystemSpec, spec_for
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.execution import MAX_TIMEOUT_SECONDS


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
    # The spec owns the verifier's clock too; core.execution's ceiling still bounds it.
    assert spec.example_timeout_seconds == 120.0 and spec.install_timeout_seconds == 300.0
    assert spec.example_timeout_seconds <= MAX_TIMEOUT_SECONDS


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


def test_a_spec_names_every_fence_a_reader_may_write_its_examples_in() -> None:
    """A reader writes csharp, cs or c#; a table in shared code knew only python.

    Measured 2026-09-06: because the example extractor held that table, every C# block in the
    .NET cohort's six READMEs was invisible and each repository reached planning with zero
    example candidates (section 29.2 F6).
    """
    assert NET.example_fences == frozenset({"csharp", "cs", "c#"})
    assert PYTHON.example_fences == frozenset({"python", "py", "python3"})
    # A spec that declares no aliases still marks its own fence, so C++ needs no entry.
    minimal = EcosystemSpec(
        ecosystem="cpp",
        language="C++",
        fence="cpp",
        registry="no package registry",
        install_fact_id="install_command:cmake",
    )
    assert minimal.example_fences == frozenset({"cpp"})


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


def test_the_source_checkout_command_is_the_ecosystems_own() -> None:
    """Measured 2026-09-06: `_installation` hard-coded `pip install .` for every ecosystem with
    an executed example, so Aspose.Cells and Aspose.3D for .NET - both sealed - told a reader to
    run `pip install .` against a C# project. The command is the ecosystem's own to name."""
    assert PYTHON.clone_and_build("org/Widget-Python", "Widget-Python") == (
        "git clone https://github.com/org/Widget-Python.git\ncd Widget-Python\npip install ."
    )
    assert NET.clone_and_build("org/Widget-NET", "Widget-NET") == (
        "git clone https://github.com/org/Widget-NET.git\ncd Widget-NET\ndotnet build"
    )
    # A spec that declares no source install (C++, until it has one) renders nothing at all.
    silent = EcosystemSpec(
        ecosystem="cpp",
        language="C++",
        fence="cpp",
        registry="no package registry",
        install_fact_id="install_command:cmake",
    )
    assert silent.clone_and_build("org/Widget-CPP", "Widget-CPP") == ""
