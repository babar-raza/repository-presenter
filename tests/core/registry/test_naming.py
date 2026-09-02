"""The governed repository-name contract."""

from __future__ import annotations

import pytest

from repository_presenter.core.registry.naming import (
    classify_managed_repository_name,
    required_repository_name_syntax,
    validate_managed_repository_coordinates,
)


@pytest.mark.parametrize(
    ("repo_name", "family", "platform"),
    [
        ("Aspose.PDF-FOSS-for-Go", "pdf", "go"),
        ("Aspose-PDF-FOSS-for-Go", "pdf", "go"),
        ("aspose-pdf-foss-for-go", "pdf", "go"),
        ("Aspose.Email-FOSS-for-.Net", "email", "net"),
    ],
)
def test_governed_name_forms_classify(repo_name: str, family: str, platform: str) -> None:
    assert classify_managed_repository_name(repo_name) == (family, platform)
    validate_managed_repository_coordinates(repo_name, family, platform)


@pytest.mark.parametrize("repo_name", ["CSSForge", "Aspose-PDF-FOSS-for-Go-MCP", "Aspose.PDF"])
def test_non_governed_names_do_not_classify(repo_name: str) -> None:
    assert classify_managed_repository_name(repo_name) is None
    with pytest.raises(ValueError, match="repository name must match"):
        validate_managed_repository_coordinates(repo_name, "pdf", "go")


def test_coordinates_must_match_the_name() -> None:
    with pytest.raises(ValueError, match="coordinates do not match"):
        validate_managed_repository_coordinates("Aspose.Cells-FOSS-for-Java", "cells", "python")


def test_syntax_is_stated_for_humans() -> None:
    assert "Aspose.{Family}-FOSS-for-{Platform}" in required_repository_name_syntax()
