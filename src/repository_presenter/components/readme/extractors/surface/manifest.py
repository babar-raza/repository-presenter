"""The typed way in to the vendored manifest reading: identity, floor, and the package root.

`RESEARCH_AND_GUIDELINES.md` §29.12 and §29.6 E2. The vendored reader parses whichever manifest an
ecosystem uses — `pyproject.toml`, a `.csproj`, `pom.xml`, `package.json`, `go.mod` — and returns a
loosely typed dictionary whose keys differ per platform. This module is where that becomes one
shape the contract can carry, with the platform's own vocabulary preserved in `floor` rather than
flattened into a lie: a Python floor is a `python_requires` string, a .NET floor is the lowest
target framework, and neither pretends to be the other.

Nothing here decides whether an identity is true; the contract's own checks do.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction import (
    package_manifest,
    package_root,
)


@dataclass(frozen=True)
class PackageIdentity:
    """What a manifest says the package is, in the vocabulary its ecosystem uses."""

    name: str
    version: str
    floor: str
    package_root: str
    manifest_path: str
    raw: dict[str, Any]


def _first(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            return str(value[0]).strip()
    return ""


def read_identity(repository_root: Path, platform: str) -> PackageIdentity:
    """The package's identity for ``platform``, or empty strings where the manifest is silent.

    An absent field is empty rather than guessed: the extractor's job is to report what the
    manifest carries, and a fact with no evidence is not written at all.
    """
    record = package_manifest.parse_manifest(repository_root, platform)
    root = package_root.detect_package_root(repository_root, platform)
    try:
        relative = root.relative_to(repository_root).as_posix()
    except ValueError:
        relative = root.as_posix()
    return PackageIdentity(
        name=_first(record, "name", "package_name", "id"),
        version=_first(record, "version"),
        # Measured 2026-09-06, one probe per platform, because the reader names the floor
        # differently in each: Python "requires_python", .NET "min_framework", Java
        # "runtime_min_version". Guessing these keys would have produced an empty floor silently.
        floor=_first(record, "requires_python", "min_framework", "runtime_min_version"),
        package_root=relative,
        manifest_path=_first(record, "manifest", "manifest_path"),
        raw=dict(record),
    )
