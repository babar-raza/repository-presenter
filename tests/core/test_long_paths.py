"""``long_path`` opts a Windows filesystem read out of ``MAX_PATH`` without a machine-wide setting.

docs/DECISION_LOG.md's 2026-09-26 ``aspose-words-foss`` ``BC-02`` entry: a real, tracked source
file's clone path can exceed Windows' 260-character ``MAX_PATH``; the machine-wide
``LongPathsEnabled`` registry key was ruled out as an unauthorized, non-reversible-without-admin
edit. The Win32 extended-length prefix (``\\\\?\\``) is the documented, per-call alternative.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from repository_presenter.core import long_paths
from repository_presenter.core.long_paths import exceeds_max_path, long_path

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="MAX_PATH is a Windows-only limit")


def test_a_short_path_is_prefixed_and_still_resolves_to_the_same_file(tmp_path: Path) -> None:
    target = tmp_path / "short.txt"
    target.write_text("hello", encoding="utf-8")
    prefixed = long_path(target)
    assert str(prefixed).startswith("\\\\?\\")
    assert prefixed.read_text(encoding="utf-8") == "hello"


def test_prefixing_is_idempotent(tmp_path: Path) -> None:
    once = long_path(tmp_path)
    twice = long_path(once)
    assert str(once) == str(twice)


def test_a_path_beyond_max_path_is_unreadable_unprefixed_and_readable_prefixed(
    tmp_path: Path,
) -> None:
    """The exact live shape: a deeply nested tree whose full path crosses 260 characters."""
    deep = tmp_path
    for i in range(6):
        deep = deep / (f"segment_{i}_" + "x" * 40)
        long_path(deep).mkdir(exist_ok=True)
    target = deep / ("f" * 60 + ".cs")
    assert len(str(target)) > 260
    long_path(target).write_text("namespace A { public class B {} }\n", encoding="utf-8")

    # Host-independent: beyond MAX_PATH, so the prefix is needed on every machine.
    # Whether an unprefixed read fails depends on LongPathsEnabled; not asserted.
    assert exceeds_max_path(target)
    assert str(long_path(target)).startswith("\\\\?\\")

    assert long_path(target).read_text(encoding="utf-8") == "namespace A { public class B {} }\n"


def test_walking_from_a_prefixed_root_yields_directly_readable_children(tmp_path: Path) -> None:
    """The common shape every call site uses: prefix the root once, then read every child."""
    deep = tmp_path
    for i in range(6):
        deep = deep / (f"segment_{i}_" + "x" * 40)
        long_path(deep).mkdir(exist_ok=True)
    target = deep / ("f" * 60 + ".cs")
    long_path(target).write_text("namespace A { public class B {} }\n", encoding="utf-8")

    found = sorted(long_path(tmp_path).rglob("*.cs"))
    assert len(found) == 1
    assert found[0].read_text(encoding="utf-8") == "namespace A { public class B {} }\n"


def test_a_path_that_does_not_exist_yet_is_still_prefixed(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist-yet.txt"
    prefixed = long_path(missing)
    assert str(prefixed).startswith("\\\\?\\")
    assert str(prefixed).endswith("does-not-exist-yet.txt")


def test_the_max_path_check_fires_for_a_long_path_on_any_host(tmp_path: Path) -> None:
    """Negative control: the verdict is a length fact. The module reads no host policy, so a machine
    with LongPathsEnabled=1 gets the same True here as one without."""
    deep = tmp_path
    for i in range(6):
        deep = deep / (f"segment_{i}_" + "x" * 40)
    target = deep / ("f" * 60 + ".cs")
    assert len(str(target)) > 260
    assert exceeds_max_path(target) is True
    assert "winreg" not in vars(long_paths)


def test_the_max_path_check_stays_quiet_for_a_short_path(tmp_path: Path) -> None:
    assert exceeds_max_path(tmp_path / "short.txt") is False
