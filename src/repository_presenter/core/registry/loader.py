"""Load the registry allow-list and gate admission; fail closed on anything malformed.

``require_listed`` is the read gate: presence in the registry is the only authorization needed
to analyze a repository. ``is_permitted`` is the deliberately stricter write gate: a
``disabled`` entry is analyzed but never proposed to. Every entry point that touches a
repository calls one of these before any network or git operation.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from repository_presenter.core.errors import ConfigError, NotAllowlistedError
from repository_presenter.core.registry.models import Registry, RegistryEntry

REGISTRY_RELATIVE_PATH = Path("data") / "registry.json"


def load_registry(path: Path) -> Registry:
    """Load and validate the registry at ``path``; raise :class:`ConfigError` if it is unfit."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"registry is not valid JSON: {path}: {exc}") from exc
    try:
        return Registry.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"registry is malformed: {path}: {exc}") from exc


def find_entry(registry: Registry, repository: str) -> RegistryEntry | None:
    """Return the entry whose ``owner/name`` matches ``repository`` exactly, if any."""
    for entry in registry.entries:
        if entry.repository == repository:
            return entry
    return None


def require_listed(registry: Registry, repository: str) -> RegistryEntry:
    """The read gate: raise :class:`NotAllowlistedError` unless ``repository`` is listed."""
    entry = find_entry(registry, repository)
    if entry is None:
        raise NotAllowlistedError(
            f"{repository} is not in the registry allow-list; refusing to touch it"
        )
    return entry


def is_permitted(registry: Registry, repository: str) -> RegistryEntry | None:
    """The write gate: the entry only if it is listed and not ``disabled``."""
    entry = find_entry(registry, repository)
    if entry is None or entry.mode == "disabled":
        return None
    return entry


def enabled_entries(registry: Registry) -> tuple[RegistryEntry, ...]:
    """Every entry whose mode is not ``disabled``."""
    return tuple(entry for entry in registry.entries if entry.mode != "disabled")
