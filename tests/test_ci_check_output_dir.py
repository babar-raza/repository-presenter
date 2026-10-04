"""ci_check.sh's SBOM/audit output directory is private to one invocation.

The outputs used to live at a fixed path under the shared tools venv. Every session that pushes runs
the pre-push hook against that one venv, so concurrent runs overwrote and truncated each other's
``pip-audit-osv.json`` and the sbom step failed intermittently on an empty JSON file (2026-10-05).
``scripts/ci_output_dir.sh`` gives each invocation its own ``mktemp -d`` directory with an EXIT
trap; these tests drive that helper with real concurrent bash processes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from support import REPO_ROOT

LIB = REPO_ROOT / "scripts" / "ci_output_dir.sh"
CI_CHECK = REPO_ROOT / "scripts" / "ci_check.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not available to run ci_check.sh")

# Each process initialises, writes its own marker as pip-audit-osv.json, then waits at a rendezvous
# until the other has written too, so both files exist at the same moment. Each then reads back its
# own file and checks whether the other's directory is its own.
WORKER = r"""
set -u
. "$LIB"
ci_output_dir_init
mkdir -p "$SBOM_DIR"
printf '%s' "$ME" > "$SBOM_DIR/pip-audit-osv.json"
printf '%s' "$SBOM_DIR" > "$SYNC/$ME.dir"
: > "$SYNC/$ME.ready"
for _ in $(seq 1 200); do
  [ -e "$SYNC/$OTHER.ready" ] && break
  sleep 0.05
done
[ -e "$SYNC/$OTHER.ready" ] || { echo "rendezvous timed out" >&2; exit 3; }
printf 'own=%s\n' "$(cat "$SBOM_DIR/pip-audit-osv.json")"
printf 'dir=%s\n' "$SBOM_DIR"
"""


def _env(**extra: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "CI_CHECK_KEEP_OUTPUT"}
    env.update(extra)
    return env


def _run(script: str, **env: str) -> subprocess.CompletedProcess[str]:
    assert BASH is not None
    return subprocess.run(
        [BASH, "-c", script],
        env=_env(LIB=LIB.as_posix(), **env),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _spawn_worker(sync: Path, me: str, other: str) -> subprocess.Popen[str]:
    assert BASH is not None
    return subprocess.Popen(
        [BASH, "-c", WORKER],
        env=_env(LIB=LIB.as_posix(), SYNC=sync.as_posix(), ME=me, OTHER=other),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _kv(stdout: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in stdout.splitlines() if "=" in line)


def test_two_concurrent_invocations_use_different_directories_and_cannot_read_each_other(
    tmp_path: Path,
) -> None:
    sync = tmp_path / "sync"
    sync.mkdir()
    first = _spawn_worker(sync, "A", "B")
    second = _spawn_worker(sync, "B", "A")
    out_a, err_a = first.communicate(timeout=120)
    out_b, err_b = second.communicate(timeout=120)
    assert first.returncode == 0, err_a
    assert second.returncode == 0, err_b

    a, b = _kv(out_a), _kv(out_b)
    assert a["dir"] != b["dir"]
    # Each read back exactly its own content while the other's file existed: no overwrite, no
    # truncation, no cross-read.
    assert a["own"] == "A"
    assert b["own"] == "B"
    # The trap removed both directories on exit.
    assert not Path((sync / "A.dir").read_text(encoding="utf-8")).exists()
    assert not Path((sync / "B.dir").read_text(encoding="utf-8")).exists()


def test_directory_is_under_the_os_temp_dir_not_the_repository_or_tools_venv(
    tmp_path: Path,
) -> None:
    fake_tmp = tmp_path / "ostmp"
    fake_tmp.mkdir()
    marker = tmp_path / "dir.txt"
    result = _run(
        '. "$LIB"; ci_output_dir_init; printf "%s" "$SBOM_DIR" > "$MARK"',
        TMPDIR=fake_tmp.as_posix(),
        MARK=marker.as_posix(),
    )
    assert result.returncode == 0, result.stderr
    created = marker.read_text(encoding="utf-8")
    assert re.search(r"ci_check\.[A-Za-z0-9]+$", created)
    assert "ostmp" in created
    assert ".venv-ci-tools" not in created
    assert str(REPO_ROOT).replace("\\", "/") not in created.replace("\\", "/")
    assert not Path(created).exists()


def test_directory_is_removed_even_when_the_script_fails(tmp_path: Path) -> None:
    marker = tmp_path / "dir.txt"
    result = _run(
        '. "$LIB"; ci_output_dir_init; printf "%s" "$SBOM_DIR" > "$MARK"; '
        'printf x > "$SBOM_DIR/f"; exit 7',
        MARK=marker.as_posix(),
    )
    assert result.returncode == 7
    assert not Path(marker.read_text(encoding="utf-8")).exists()


def test_keep_output_retains_the_directory_and_prints_its_path(tmp_path: Path) -> None:
    marker = tmp_path / "dir.txt"
    result = _run(
        '. "$LIB"; ci_output_dir_init; printf "%s" "$SBOM_DIR" > "$MARK"; printf x > "$SBOM_DIR/f"',
        MARK=marker.as_posix(),
        CI_CHECK_KEEP_OUTPUT="1",
    )
    assert result.returncode == 0, result.stderr
    kept = Path(marker.read_text(encoding="utf-8"))
    try:
        assert kept.is_dir()
        assert (kept / "f").read_text(encoding="utf-8") == "x"
        assert "kept" in result.stdout
        assert kept.name in result.stdout
    finally:
        shutil.rmtree(kept, ignore_errors=True)


def test_two_invocations_in_sequence_never_reuse_a_directory(tmp_path: Path) -> None:
    paths = []
    for index in range(2):
        marker = tmp_path / f"dir{index}.txt"
        result = _run(
            '. "$LIB"; ci_output_dir_init; printf "%s" "$SBOM_DIR" > "$MARK"',
            MARK=marker.as_posix(),
        )
        assert result.returncode == 0, result.stderr
        paths.append(marker.read_text(encoding="utf-8"))
    assert paths[0] != paths[1]


def test_ci_check_uses_the_private_directory_and_no_other_fixed_location() -> None:
    text = CI_CHECK.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    # The old shared location is gone from the executable lines, and nothing writes into the repo's
    # committed SBOM snapshot or a fixed /tmp path.
    assert "$CI_TOOLS_VENV/sbom" not in code
    assert "evidence/sbom" not in code
    assert "/tmp/" not in code
    assert "SBOM_DIR=" not in code  # set only by ci_output_dir_init, never to a fixed path here
    # Wiring: initialised before preflight and before the first check, and every output path goes
    # through $SBOM_DIR.
    init = code.index("ci_output_dir_init")
    assert init < code.index("need ")
    assert init < code.index('run_step "lockdrift"')
    for name in ("requirements-lock.cdx.json", "pip-audit-osv.json", "pip-audit-osv.md"):
        for match in re.finditer(r'"([^"]*)' + re.escape(name) + '"', code):
            assert match.group(1) == "$SBOM_DIR/", match.group(0)


def test_ci_workflow_keeps_writing_the_snapshot_to_evidence_sbom() -> None:
    # Parity: CI (no tools venv) is unchanged; only local runs moved off the shared location.
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "evidence/sbom/requirements-lock.cdx.json" in workflow
