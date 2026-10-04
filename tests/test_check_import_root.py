"""The import-root preflight: a checkout's checks must import that checkout's own src.

A worktree shares the main checkout's venv through a ``.venv`` junction, and that venv's editable
install points at the main checkout's src. Without PYTHONPATH, ``import repository_presenter`` in
the worktree then loads the main checkout's code, so every check tests the wrong tree (2026-10-04:
the version-discipline test reported a false mismatch). ``scripts/check_import_root.py`` is the loud
failure, and ``scripts/ci_check.sh`` runs it as a preflight before any check.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "check_import_root.py"
CI_CHECK = REPO_ROOT / "scripts" / "ci_check.sh"
# The preflight invocation itself; the script's name also appears in ci_check.sh's header comment.
PREFLIGHT_CALL = '"$PY" scripts/check_import_root.py .'


def _check(root: Path, pythonpath: str | None) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    if pythonpath is not None:
        env["PYTHONPATH"] = pythonpath
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_resolves_inside_this_checkout_when_pythonpath_points_at_its_src() -> None:
    # The configuration ci_check.sh establishes: PYTHONPATH is this checkout's src.
    result = _check(REPO_ROOT, pythonpath=str(REPO_ROOT / "src"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "resolves to" in result.stdout


def test_a_package_resolving_outside_the_checkout_is_refused(tmp_path: Path) -> None:
    # Negative control: a shadowing package elsewhere on PYTHONPATH (a stale checkout or a copy
    # from another worktree) must fail, and the message must name where it came from.
    shadow_dir = tmp_path / "elsewhere" / "src"
    package = shadow_dir / "repository_presenter"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    checkout = tmp_path / "checkout"
    (checkout / "src").mkdir(parents=True)

    result = _check(checkout, pythonpath=str(shadow_dir))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "resolves to" in result.stdout
    assert str(shadow_dir.resolve()) in result.stdout or "elsewhere" in result.stdout


def test_an_unrelated_install_is_refused_when_the_checkout_has_no_src(tmp_path: Path) -> None:
    # Negative control with no PYTHONPATH at all: whatever the venv imports is not under this
    # tmp checkout's src, so the check refuses it.
    result = _check(tmp_path, pythonpath=None)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "outside" in result.stdout


def test_usage_error_is_exit_two() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2


def test_ci_check_runs_the_preflight_before_any_check_step() -> None:
    # The wiring: the preflight must run, and must be before the first run_step (the checks).
    text = CI_CHECK.read_text(encoding="utf-8")
    preflight = text.find(PREFLIGHT_CALL)
    first_check = text.find('run_step "lockdrift"')
    assert preflight != -1, "ci_check.sh does not run the import-root preflight"
    assert first_check != -1
    assert preflight < first_check


def test_ci_check_exports_pythonpath_before_the_preflight() -> None:
    text = CI_CHECK.read_text(encoding="utf-8")
    assert text.find("export PYTHONPATH") < text.find(PREFLIGHT_CALL)


def _venv_bin_function() -> str:
    text = CI_CHECK.read_text(encoding="utf-8")
    start = text.index("venv_bin() {")
    return text[start : text.index("\n}\n", start) + 3]


def test_venv_bin_stays_on_path_under_an_inherited_windows_pwd(tmp_path: Path) -> None:
    # Negative control for the 2026-10-04 pre-push failure. git runs a hook with PWD in Windows form
    # (E:/...). The old venv_bin echoed that form, and the drive colon split the PATH entry, so the
    # venv's python was never found and the system Python ran the checks.
    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    tool = scripts / "venv-marker-tool"
    tool.write_text("#!/usr/bin/env bash\necho hit\n", encoding="utf-8")
    tool.chmod(0o755)
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available to run ci_check.sh's venv_bin")
    script = _venv_bin_function() + (
        'PATH="$(venv_bin .venv):$PATH"\n'
        'printf "%s\n" "$(venv_bin .venv)"\n'
        "command -v venv-marker-tool\n"
    )
    env = {**os.environ, "PWD": tmp_path.as_posix()}
    result = subprocess.run(
        [bash, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    dir_line, found = result.stdout.strip().splitlines()[-2:]
    assert ":" not in dir_line, f"venv_bin returned a PATH-splitting drive form: {dir_line}"
    assert found.endswith("venv-marker-tool")
