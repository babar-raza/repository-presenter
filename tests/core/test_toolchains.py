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


def _fake_python_install(root: Path, directory: str) -> Path:
    install = root / directory
    install.mkdir(parents=True)
    executable = install / "python.exe"
    executable.write_bytes(b"")
    return executable


def _machine(
    monkeypatch: pytest.MonkeyPatch,
    launcher: list[tuple[str, Path]] | None = None,
    directories: list[tuple[str, Path]] | None = None,
    path: list[tuple[str, Path]] | None = None,
) -> None:
    """Replace every source `installed_pythons` reads, so the host's own interpreters (the CI
    runner's /usr/bin/python3.12, a developer's py launcher) never reach an assertion."""
    monkeypatch.setattr(toolchains, "_launcher_pythons", lambda: list(launcher or []))
    monkeypatch.setattr(toolchains, "_directory_pythons", lambda: list(directories or []))
    monkeypatch.setattr(toolchains, "_path_pythons", lambda: list(path or []))


def test_the_installed_pythons_are_found_by_the_launcher_and_the_install_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Words-Python in a lane worktree (2026-10-11): `requires-python >=3.10,<3.13`, a machine
    with Python 3.12 installed, and no `runs/verify` venv - every example read NOT_VERIFIED. The
    resolver now also answers from what the machine has: the `py -0p` record first, then a
    conventional install directory, then PATH, one interpreter per version, lowest first."""
    listed = _fake_python_install(tmp_path / "launcher", "Python312")
    other = _fake_python_install(tmp_path / "launcher", "Python311")
    by_directory = _fake_python_install(tmp_path / "d-root", "Python310")
    shadowed = _fake_python_install(tmp_path / "d-root", "Python3.12")
    on_path = tmp_path / "bin" / "python3.9"
    _machine(
        monkeypatch,
        launcher=[("3.12", listed), ("3.11", other)],
        directories=[("3.10", by_directory), ("3.12", shadowed)],
        path=[("3.9", on_path), ("3.11", tmp_path / "bin" / "python3.11")],
    )
    assert toolchains.installed_pythons() == [
        ("3.9", on_path),
        ("3.10", by_directory),
        ("3.11", other),
        ("3.12", listed),
    ]


def test_the_install_directory_search_reads_conventional_folder_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "d-root"
    found = {
        "3.10": _fake_python_install(root, "Python310"),
        "3.12": _fake_python_install(root, "Python3.12"),
        "3.9": _fake_python_install(root, "python-39"),
    }
    (root / "NotPython").mkdir()
    (root / "Python3").mkdir()  # no minor version: nothing to read
    (root / "Python311").mkdir()  # no interpreter inside
    monkeypatch.setattr(toolchains, "_python_roots", lambda: (root, tmp_path / "missing"))
    assert dict(toolchains._directory_pythons()) == found


def test_versioned_commands_on_path_are_a_posix_source_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    commands = {"python3.11": str(tmp_path / "python3.11"), "python3.13": str(tmp_path / "p313")}
    monkeypatch.setattr(toolchains.shutil, "which", lambda name: commands.get(name))
    monkeypatch.setattr(toolchains, "os", SimpleNamespace(name="posix"))
    assert toolchains._path_pythons() == [
        ("3.11", Path(commands["python3.11"])),
        ("3.13", Path(commands["python3.13"])),
    ]
    monkeypatch.setattr(toolchains, "os", SimpleNamespace(name="nt"))
    assert toolchains._path_pythons() == []


@pytest.mark.parametrize(
    "versions",
    [["3.11"], ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]],
    ids=["only-3.11", "many-versions"],
)
def test_the_answer_is_the_simulated_machine_whatever_the_host_has(
    versions: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hermetic: with the sources replaced, the result is exactly the simulated machine - never
    the host's own interpreters - for a one-version and a many-version machine alike."""
    installed = [(version, tmp_path / f"py{version}" / "python.exe") for version in versions]
    _machine(monkeypatch, launcher=installed[:1], directories=installed[1:])
    assert toolchains.installed_pythons() == installed


def test_a_machine_with_no_interpreter_at_all_has_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _machine(monkeypatch)
    assert toolchains.installed_pythons() == []


def test_a_launcher_listing_line_is_read_in_each_of_its_spellings() -> None:
    for line, version in (
        (r" -V:3.12 *        C:\Python312\python.exe", "3.12"),
        (r" -V:PythonCore/3.11   C:\Users\x\Python311\python.exe", "3.11"),
        (r" -3.10-64        C:\Python310\python.exe", "3.10"),
    ):
        matched = toolchains._LAUNCHER_LINE.match(line)
        assert matched is not None and matched.group("version") == version
        assert matched.group("path").endswith("python.exe")
    assert toolchains._LAUNCHER_LINE.match("Installed Pythons found by py Launcher") is None
