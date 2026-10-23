"""Git LFS build inputs for a disposable build copy.

A clone made without LFS smudging holds a pointer file where a tracked binary should be: a text
stub of about 130 bytes that starts ``version https://git-lfs.github.com/spec/v1``. A build that
references such a binary (Aspose.Words for .NET references ``packages/**/*.dll``) then fails on a
file that is not an assembly - a fault of the harness's clone, not of the upstream (measured
2026-10-19). This module fetches exactly those build inputs into the build copy, and nothing else:
a repository may track thousands of LFS test assets, and none of them is a build input.

Three guards, each with its own negative control in `tests/core/test_lfs.py`. The step runs only
when the checkout's ``.gitattributes`` declares an ``lfs`` filter, only when ``git lfs`` answers,
and only when the copy holds at least one pointer file with a build-input suffix. The clone itself
is never written: LFS objects go to a storage directory and the index to a scratch copy, both in
the run workspace, so the push-disabled clone stays as it was verified.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.core.execution import error_excerpt, execute, profile_environment

POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
# What a build consumes as an input, as opposed to a test image or document the repository tracks
# in LFS: an assembly, a package, an executable, a jar or a native library.
BUILD_INPUT_SUFFIXES = (".dll", ".nupkg", ".exe", ".jar", ".so", ".dylib", ".lib", ".a")
MAX_BUILD_INPUTS = 64
_MAX_POINTER_BYTES = 1024
_MAX_TIMEOUT_SECONDS = 300.0
_PROBE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class LfsFetch:
    """What the LFS step did. ``note`` is empty when nothing was attempted, so a repository with
    no LFS build input gets exactly the receipt text it always had."""

    attempted: bool
    ok: bool
    note: str


NOT_ATTEMPTED = LfsFetch(False, True, "")


def declares_lfs(root: Path) -> bool:
    """True when the checkout's root ``.gitattributes`` assigns the ``lfs`` filter to a pattern."""
    try:
        text = (root / ".gitattributes").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any("filter=lfs" in line.split("#", 1)[0] for line in text.splitlines() if line.strip())


def pointer_files(copy: Path) -> list[str]:
    """Posix-relative paths of the LFS pointer files in ``copy`` that a build would consume."""
    found: list[str] = []
    for path in sorted(copy.rglob("*")):
        if len(found) >= MAX_BUILD_INPUTS:
            break
        if path.suffix.lower() not in BUILD_INPUT_SUFFIXES:
            continue
        try:
            if not path.is_file() or path.stat().st_size > _MAX_POINTER_BYTES:
                continue
            with path.open("rb") as handle:
                if handle.read(len(POINTER_PREFIX)) != POINTER_PREFIX:
                    continue
        except OSError:
            continue
        relative = path.relative_to(copy).as_posix()
        if "," not in relative:
            found.append(relative)
    return found


def fetch_lfs_build_inputs(
    root: Path, copy: Path, workspace: Path, timeout_seconds: float
) -> LfsFetch:
    """Replace the build-input pointer files in ``copy`` with their LFS content, when the
    checkout at ``root`` declares LFS, ``git lfs`` exists and such pointers are present."""
    git = shutil.which("git")
    index = root / ".git" / "index"
    if git is None or not declares_lfs(root) or not index.is_file():
        return NOT_ATTEMPTED
    environment = profile_environment(workspace)
    probe = execute(
        [git, "lfs", "version"],
        workspace=workspace,
        timeout_seconds=_PROBE_TIMEOUT_SECONDS,
        extra_environment=environment,
    )
    if probe.return_code != 0 or probe.timed_out:
        return NOT_ATTEMPTED
    pointers = pointer_files(copy)
    if not pointers:
        return NOT_ATTEMPTED
    scratch_index = workspace / "lfs-index"
    storage = workspace / "lfs-objects"
    try:
        shutil.copyfile(index, scratch_index)
    except OSError:
        return NOT_ATTEMPTED
    environment = {**environment, "GIT_INDEX_FILE": str(scratch_index)}
    result = execute(
        [
            git,
            "--git-dir",
            str(root / ".git"),
            "--work-tree",
            str(copy),
            "-c",
            f"lfs.storage={storage}",
            # The run's disposable HOME has no global config. Without this, git-lfs's own
            # `git ls-files` over a repository with deep paths (Aspose.Words for .NET) never
            # returns on Windows (measured 2026-10-19: no output for 90 s, 2 s with the owner's
            # real `core.longpaths=true`).
            "-c",
            "core.longpaths=true",
            "lfs",
            "pull",
            f"--include={','.join(pointers)}",
        ],
        workspace=workspace,
        timeout_seconds=min(timeout_seconds, _MAX_TIMEOUT_SECONDS),
        extra_environment=environment,
    )
    if result.return_code != 0 or result.timed_out:
        said = error_excerpt(result.stderr, result.stdout, bases=(root, copy, workspace))
        return LfsFetch(
            True, False, f"; `git lfs pull` of {len(pointers)} build input(s) failed: {said}"
        )
    left = pointer_files(copy)
    if left:
        return LfsFetch(
            True,
            False,
            f"; `git lfs pull` left {len(left)} of {len(pointers)} build input(s) as pointer files",
        )
    return LfsFetch(
        True, True, f"; {len(pointers)} Git LFS build input(s) were fetched into the build copy"
    )
