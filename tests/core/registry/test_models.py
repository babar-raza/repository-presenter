"""Typed registry entries: closed fields, derived clone URL, unique stable identities."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from repository_presenter.core.registry.models import Registry, RegistryEntry


def entry(
    repository: str = "example/Aspose.Widget-FOSS-for-Java", **overrides: Any
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "repository": repository,
        "family": "widget",
        "platform": "java",
        "ecosystem": "java",
        "mode": "disabled",
        "policy_profile": "example-widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 10, "node_id": "R_10"},
    }
    data.update(overrides)
    return data


def test_entry_derives_coordinates_and_clone_url() -> None:
    parsed = RegistryEntry.model_validate(entry())
    assert (parsed.owner, parsed.name) == ("example", "Aspose.Widget-FOSS-for-Java")
    assert parsed.clone_url == "https://github.com/example/Aspose.Widget-FOSS-for-Java.git"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"clone_url": "https://x"}, "clone_url"),
        ({"mode": "write"}, "mode"),
        ({"ecosystem": "Java"}, "ecosystem"),
        (
            {"provider_identity": {"provider": "github", "repository_id": "10", "node_id": "R"}},
            "repository_id",
        ),
        (
            {"provider_identity": {"provider": "gitlab", "repository_id": 10, "node_id": "R"}},
            "provider",
        ),
        ({"family": "cells", "platform": "python"}, "coordinates do not match"),
    ],
)
def test_malformed_entries_are_rejected(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        RegistryEntry.model_validate(entry(**overrides))


def test_registry_rejects_duplicate_identities() -> None:
    first = entry()
    second = entry("example/Aspose-Widget-FOSS-for-Java")
    with pytest.raises(ValidationError, match="duplicate provider repository IDs"):
        Registry.model_validate({"schema_version": 1, "entries": [first, second]})

    second["provider_identity"] = {"provider": "github", "repository_id": 11, "node_id": "R_10"}
    with pytest.raises(ValidationError, match="duplicate provider node IDs"):
        Registry.model_validate({"schema_version": 1, "entries": [first, second]})

    same_name = entry(
        provider_identity={"provider": "github", "repository_id": 12, "node_id": "R_12"}
    )
    with pytest.raises(ValidationError, match="duplicate repositories"):
        Registry.model_validate({"schema_version": 1, "entries": [first, same_name]})


def test_registry_rejects_unknown_schema_versions_and_fields() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        Registry.model_validate({"schema_version": 2, "entries": []})
    with pytest.raises(ValidationError, match="extra"):
        Registry.model_validate({"schema_version": 1, "entries": [], "roadmap": []})
