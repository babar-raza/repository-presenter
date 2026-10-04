"""Machine toolchain resolution: the recorded registry, the install search, and PATH precedence."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from repository_presenter.core import toolchains
from repository_presenter.core.toolchains import (
    REGISTRY_VARIABLE,
    recorded_path,
    recorded_tool,
    resolve_tool,
    subprocess_path,
    toolchain_fingerprint,
)


def _tool(path: Path) -> Path:
    """An executable placeholder: POSIX needs the bit for `which`; Windows needs the suffix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


def _registry(directory: Path, lines: list[str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    registry = directory / "TOOLCHAIN_PATHS.txt"
    registry.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return registry


@pytest.fixture
def no_install_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Nothing installed anywhere this test does not place it, so the host JDK cannot leak in."""
    monkeypatch.setattr(toolchains, "_install_roots", lambda: (tmp_path / "no-install-roots",))


def test_a_recorded_path_that_exists_is_returned_as_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = _tool(tmp_path / "winlibs" / "mingw64" / "bin" / "g++.exe")
    registry = _registry(tmp_path, [f"gxx={tool}", f"ninja={tmp_path / 'absent.exe'}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    assert recorded_tool("gxx") == str(tool)
    assert recorded_tool("ninja") is None
    assert recorded_tool("nothing-recorded") is None


def test_a_record_whose_root_has_moved_is_re_rooted_under_the_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner's registry records `C:\\tools\\rp-toolchains\\...`, while the same tree lives
    under `D:\\tools\\rp-toolchains` on this machine: the registry says where its own tree is."""
    registry_dir = tmp_path / "rp-toolchains"
    moved = _tool(registry_dir / "winlibs" / "mingw64" / "bin" / "g++.exe")
    recorded = r"C:\tools\rp-toolchains\winlibs\mingw64\bin\g++.exe"
    registry = _registry(registry_dir, [f"gxx={recorded}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    assert recorded_tool("gxx") == str(moved)


def test_a_record_for_a_directory_resolves_through_recorded_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "rustup" / "rustup-home"
    home.mkdir(parents=True)
    registry = _registry(tmp_path, [f"rustup_home={home}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    assert recorded_path("rustup_home") == str(home)
    assert recorded_tool("rustup_home") is None  # a tool record must name a file


def test_javac_prefers_the_recorded_jdk_over_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_install_roots: None
) -> None:
    recorded = _tool(tmp_path / "jdk21" / "bin" / "javac.exe")
    on_path = _tool(tmp_path / "jdk17" / "bin" / "javac.exe")
    registry = _registry(tmp_path, [f"javac={recorded}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert resolve_tool("javac") == str(recorded)


def test_javac_found_by_the_install_search_when_path_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live machine's shape: no javac on PATH, a JDK under the conventional install root."""
    program_files = tmp_path / "Program Files"
    _tool(program_files / "Eclipse Adoptium" / "jdk-17.0.19.10-hotspot" / "bin" / "javac.exe")
    newest = _tool(
        program_files / "Eclipse Adoptium" / "jdk-21.0.11.10-hotspot" / "bin" / "javac.exe"
    )
    monkeypatch.setattr(toolchains, "_install_roots", lambda: (program_files,))
    monkeypatch.setenv(REGISTRY_VARIABLE, str(tmp_path / "absent-registry.txt"))
    monkeypatch.setenv("PATH", "")
    assert resolve_tool("javac") == str(newest)


def test_no_jdk_anywhere_resolves_to_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_install_roots: None
) -> None:
    monkeypatch.setenv(REGISTRY_VARIABLE, str(tmp_path / "absent-registry.txt"))
    monkeypatch.setenv("PATH", "")
    assert resolve_tool("javac") is None
    assert resolve_tool("mvn") is None


def test_tsc_keeps_the_registry_ahead_of_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_install_roots: None
) -> None:
    recorded = _tool(tmp_path / "npm" / "prefix" / "tsc.cmd")
    on_path = _tool(tmp_path / "global" / "tsc.cmd")
    registry = _registry(tmp_path, [f"tsc={recorded}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert resolve_tool("tsc") == str(recorded)


def test_cmake_keeps_path_ahead_of_the_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_install_roots: None
) -> None:
    """The documented PATH-first default: a hosted runner's CMake carries a certificate bundle."""
    # PATH-first is the contract (cmake_executable, RESEARCH 29.6 E7); the PATH fixture is named
    # as the platform's executable (`cmake.exe` on Windows, `cmake` on POSIX).
    exe = "cmake.exe" if os.name == "nt" else "cmake"
    recorded = _tool(tmp_path / "winlibs" / "cmake.exe")
    on_path = _tool(tmp_path / "system" / exe)
    registry = _registry(tmp_path, [f"cmake={recorded}"])
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    monkeypatch.setenv("PATH", str(on_path.parent))
    # Windows reports the PATHEXT spelling (`cmake.EXE`), so compare case-insensitively.
    assert os.path.normcase(resolve_tool("cmake") or "") == os.path.normcase(str(on_path))


def test_subprocess_path_prepends_tool_directories_and_never_changes_the_process_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = _tool(tmp_path / "jdk" / "bin" / "javac.exe")
    monkeypatch.setenv("PATH", "inherited-entry")
    path = subprocess_path(str(tool))
    assert path.split(os.pathsep) == [str(tool.parent), "inherited-entry"]
    assert os.environ["PATH"] == "inherited-entry"


def test_the_fingerprint_names_each_tool_by_version_or_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    present = {"javac": "/jdk/bin/javac.exe", "cmake": "/winlibs/cmake.exe"}
    monkeypatch.setattr(toolchains, "resolve_tool", lambda name: present.get(name))
    monkeypatch.setattr(
        toolchains, "probe_version", lambda name, path: "21.0.11" if name == "javac" else "4.4.1"
    )
    fingerprint = toolchain_fingerprint()
    assert fingerprint["javac"] == "21.0.11"
    assert fingerprint["cmake"] == "4.4.1"
    assert fingerprint["mvn"] == "absent"
    assert fingerprint == dict(sorted(fingerprint.items()))


def test_a_present_tool_that_reports_no_version_is_named_as_such(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        toolchains, "resolve_tool", lambda name: "/x/tool" if name == "javac" else None
    )
    monkeypatch.setattr(toolchains, "probe_version", lambda name, path: "")
    assert toolchain_fingerprint()["javac"] == "present (no version reported)"
