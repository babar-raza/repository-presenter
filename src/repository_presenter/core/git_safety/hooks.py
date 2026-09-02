"""Pre-push hook: the second, independent control that blocks any push from a clone.

Even if the neutered push URL were ever restored by mistake, this hook still hard-blocks the
push. Git for Windows runs hooks through its bundled shell by shebang, so the executable bit is
best effort there and is recorded rather than trusted by the verifier.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

BLOCK_MARKER = "REPOSITORY_PRESENTER_PUSH_BLOCKED"

HOOK_SCRIPT = f"""#!/bin/sh
echo "repository-presenter: push blocked by design ({BLOCK_MARKER})" >&2
echo "this is a disposable read-only clone; pushes are never permitted" >&2
exit 1
"""


def install_pre_push_hook(repo_path: Path) -> Path:
    """Write the blocking hook and, where the filesystem has one, set its executable bit."""
    hook_path = repo_path / ".git" / "hooks" / "pre-push"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8", newline="\n")
    try:
        current = os.stat(hook_path).st_mode
        os.chmod(hook_path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass
    return hook_path
