"""Typed registry entries: the hard allow-list of admitted repositories.

Identity is the stable provider repository ID, never the name. The clone URL is derived from
the repository coordinates rather than stored, so the file cannot carry a drifting duplicate.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from repository_presenter.core.registry.naming import validate_managed_repository_coordinates

Mode = Literal["full", "dry_run", "disabled"]
REPOSITORY_PATTERN = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"


class ProviderIdentity(BaseModel):
    """Stable provider identity for one admitted repository."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["github"] = "github"
    repository_id: StrictInt = Field(gt=0)
    node_id: str = Field(min_length=1)


class RegistryEntry(BaseModel):
    """One admitted repository. ``mode`` governs publication readiness, never read eligibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(pattern=REPOSITORY_PATTERN)
    family: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    ecosystem: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    mode: Mode
    policy_profile: str = Field(min_length=1)
    active: bool
    provider_identity: ProviderIdentity

    @model_validator(mode="after")
    def _name_matches_coordinates(self) -> RegistryEntry:
        validate_managed_repository_coordinates(self.name, self.family, self.platform)
        return self

    @property
    def owner(self) -> str:
        return self.repository.split("/")[0]

    @property
    def name(self) -> str:
        return self.repository.split("/")[1]

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.repository}.git"


class Registry(BaseModel):
    """The whole allow-list; entries are sorted by repository and identities are unique."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    entries: tuple[RegistryEntry, ...]

    @model_validator(mode="after")
    def _identities_are_unique(self) -> Registry:
        validate_stable_identities(self.entries)
        return self


def validate_stable_identities(entries: tuple[RegistryEntry, ...]) -> None:
    """Fail closed when two admitted entries claim the same repository or provider identity."""
    duplicates = _duplicates(entry.repository.casefold() for entry in entries)
    if duplicates:
        raise ValueError(f"duplicate repositories: {duplicates}")
    duplicates = _duplicates(entry.provider_identity.repository_id for entry in entries)
    if duplicates:
        raise ValueError(f"duplicate provider repository IDs: {duplicates}")
    duplicates = _duplicates(entry.provider_identity.node_id for entry in entries)
    if duplicates:
        raise ValueError(f"duplicate provider node IDs: {duplicates}")


def _duplicates(values: Iterable[Hashable]) -> list[str]:
    counts = Counter(values)
    return sorted(str(value) for value, count in counts.items() if count > 1)
