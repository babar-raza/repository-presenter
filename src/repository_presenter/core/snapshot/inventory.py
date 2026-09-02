"""Case-insensitive detection of the README, license, and community files at a clone root.

Casing is deliberately ignored: the registry repositories disagree (``LICENSE``, ``License.txt``,
``License/LICENSE.txt``), and a case-insensitive filesystem would hide a mismatch until a Linux
runner saw it. Candidates are visited in name order so the result is the same on every host.
Manifest detection belongs to the platform plugins of the facts stage, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

README_FILENAMES = frozenset({"readme.md", "readme", "readme.rst", "readme.txt"})
LICENSE_FILENAMES = frozenset({"license", "license.txt", "license.md", "copying", "license.rst"})
COMMUNITY_FILENAMES: dict[str, frozenset[str]] = {
    "CONTRIBUTING": frozenset(
        {"contributing.md", "contributing", "contributing.txt", "contributing.rst"}
    ),
    "CODE_OF_CONDUCT": frozenset(
        {"code_of_conduct.md", "code_of_conduct", "code_of_conduct.txt", "code_of_conduct.rst"}
    ),
    "SECURITY": frozenset({"security.md", "security", "security.txt", "security.rst"}),
    "SUPPORT": frozenset({"support.md", "support", "support.txt", "support.rst"}),
}


@dataclass(frozen=True)
class FileInventory:
    """Where the README, license, and community files are, if anywhere."""

    readme_path: Path | None
    license_path: Path | None
    community_paths: dict[str, Path] = field(default_factory=dict)


def _find_case_insensitive(directory: Path, names: frozenset[str]) -> Path | None:
    if not directory.is_dir():
        return None
    for entry in sorted(directory.iterdir(), key=lambda p: p.name):
        if entry.is_file() and entry.name.lower() in names:
            return entry
    return None


def scan(root: Path) -> FileInventory:
    """Inventory the root of ``root``; a license may also sit in a ``License`` directory."""
    readme_path = _find_case_insensitive(root, README_FILENAMES)
    license_path = _find_case_insensitive(root, LICENSE_FILENAMES)
    if license_path is None and root.is_dir():
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            if entry.is_dir() and entry.name.lower() == "license":
                license_path = _find_case_insensitive(entry, LICENSE_FILENAMES)
                if license_path is not None:
                    break
    community_paths: dict[str, Path] = {}
    for canonical_name, names in COMMUNITY_FILENAMES.items():
        found = _find_case_insensitive(root, names)
        if found is not None:
            community_paths[canonical_name] = found
    return FileInventory(
        readme_path=readme_path, license_path=license_path, community_paths=community_paths
    )
