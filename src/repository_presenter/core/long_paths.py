"""Windows extended-length paths, so a real filesystem read never trips ``MAX_PATH``.

Windows limits a plain path string to 260 characters end to end (``MAX_PATH``) unless the caller
opts a specific Win32 call out of that limit by prefixing an absolute path with ``\\\\?\\`` -
Microsoft's own documented mechanism (Win32 "Maximum Path Length Limitation"). This is independent
of the machine-wide ``LongPathsEnabled`` policy: that registry key is an unauthorized,
non-reversible-without-admin, machine-wide edit this project's own governance has already ruled
out (``docs/DECISION_LOG.md``, 2026-09-26 entry, the ``aspose-words-foss`` ``BC-02`` investigation).
The extended-length prefix needs no such setting - it opts out per call, on any machine, with
nothing to install or leave behind.

A cloned upstream repository's own directory and file names are foreign content this project does
not control (`plans/idea.md`'s standing constraint that the exact upstream revision is factual
authority): a deeply nested namespace or a long file name is a fact about the repository, not a
defect to route around by truncating, renaming, or relocating the clone. Enumerating with a
prefixed root, then reading each yielded path directly, keeps every downstream read safe without
changing what the repository is or how its tree is walked.

``core/git_safety/clone.py`` already carries this exact mechanism, privately, for its own
directory-cleanup retries; this module is the shared, public form so an extractor can use the same
proven behavior rather than a second, divergent copy of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_EXTENDED_LENGTH_PREFIX = "\\\\?\\"
_UNC_PREFIX = "\\\\?\\UNC\\"

# Win32's plain-path limit, in characters. A constant, not a query: the verdict below never
# depends on the host's LongPathsEnabled policy, so the same path gets the same answer everywhere.
MAX_PATH = 260


def exceeds_max_path(path: Path) -> bool:
    """True when ``path`` is longer than ``MAX_PATH`` as a plain string.

    A pure length check against the constant. It reads no host setting, so it is the same on a
    machine with ``LongPathsEnabled`` set as on one without. Whether an unprefixed read then
    succeeds depends on that policy; this predicate does not, and it decides when a path needs
    ``long_path``.
    """
    return len(str(path)) > MAX_PATH


def long_path(path: Path) -> Path:
    """``path``, as an absolute Windows extended-length path; unchanged on every other platform.

    Idempotent - a path that already carries the extended-length prefix (plain or ``UNC``) is
    returned as-is, so this is safe to call more than once or on a path some other layer already
    prefixed. Safe on a path that does not exist yet (``Path.resolve()`` does not require the
    target to exist) and on a path already comfortably under ``MAX_PATH`` (the prefix never makes
    a valid short path invalid; it only ever changes what happens once a path gets long).

    Apply this once, at the root passed to ``Path.rglob``/``Path.glob``: pathlib joins the
    prefixed string as-is, so every yielded child path already carries the prefix too, and a
    direct ``read_text()``/``write_text()``/``open()`` on that child then bypasses ``MAX_PATH``
    without a second call here. A caller that also compares a walked child back against the
    original, unprefixed root (``child.relative_to(root)``) must prefix that root the same way
    first, since the two path strings otherwise no longer share a common prefix.
    """
    # `platform = "linux"` in [tool.mypy] (pyproject.toml) means mypy assumes `sys.platform` is
    # never "win32" - an early `if sys.platform != "win32": return path` would then make every
    # line after it statically unreachable. Keeping the real work inside the `== "win32"` branch
    # instead (the same shape `core/git_safety/process.py`'s own platform checks already use)
    # type-checks clean under that assumption while still running for real on Windows.
    if sys.platform == "win32":
        resolved = str(path.resolve())
        if resolved.startswith(_EXTENDED_LENGTH_PREFIX):
            return path
        if resolved.startswith("\\\\"):
            return Path(f"{_UNC_PREFIX}{resolved.lstrip(chr(92))}")
        return Path(f"{_EXTENDED_LENGTH_PREFIX}{resolved}")
    return path
