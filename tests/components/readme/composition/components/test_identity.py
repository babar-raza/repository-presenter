"""The canonical product name derives from the governed repository name and nothing else."""

from __future__ import annotations

from repository_presenter.components.readme.composition.components.identity import (
    product_name,
    product_name_tokens,
)
from repository_presenter.core.registry.models import RegistryEntry


def _entry(repository: str, family: str = "3d", platform: str = "python") -> RegistryEntry:
    return RegistryEntry.model_validate(
        {
            "repository": repository,
            "family": family,
            "platform": platform,
            "ecosystem": "python",
            "mode": "dry_run",
            "policy_profile": "p",
            "active": True,
            "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
        }
    )


def test_hyphens_become_spaces_and_dots_stay() -> None:
    assert product_name(_entry("aspose-3d-foss/Aspose.3D-FOSS-for-Python")) == (
        "Aspose.3D FOSS for Python"
    )
    assert product_name(_entry("aspose-cells-foss/Aspose.Cells-FOSS-for-.NET", "cells", "net")) == (
        "Aspose.Cells FOSS for .NET"
    )
    assert product_name_tokens("Aspose.3D FOSS for Python") == {
        "Aspose.3D",
        "FOSS",
        "for",
        "Python",
    }
