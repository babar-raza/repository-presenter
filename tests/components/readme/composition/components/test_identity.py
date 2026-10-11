"""The canonical product name derives from the governed repository name and nothing else."""

from __future__ import annotations

from repository_presenter.components.readme.composition.components.identity import (
    canonicalise_name_variants,
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


# CUT-2 (BC-12, G3-W08): the deterministic rewrite of a product-name variant in authored prose.
# The first two strings are the real ones from the 2026-10-10 baseline (3D-.NET limitation:6,
# PSD-Python's TestAsposeCompatibility row): the model shortened the name, three BC-12 repairs
# did not converge, and the rewrite is a function of the registry name alone.

NET = "Aspose.3D FOSS for .NET"


def test_a_shortened_name_becomes_the_canonical_name() -> None:
    text = "Their members do not affect licensing or usage in Aspose.3D FOSS."
    assert canonicalise_name_variants(text, NET) == (
        "Their members do not affect licensing or usage in Aspose.3D FOSS for .NET."
    )
    psd = "verifies compatibility between Aspose.PSD FOSS and the original Aspose.PSD API."
    assert canonicalise_name_variants(psd, "Aspose.PSD FOSS for Python") == (
        "verifies compatibility between Aspose.PSD FOSS for Python and the original Aspose.PSD API."
    )


def test_separator_and_case_variants_become_the_canonical_name() -> None:
    for variant in ("aspose.3d foss", "Aspose 3D FOSS", "ASPOSE.3D FOSS for .net"):
        assert canonicalise_name_variants(f"Use {variant} today.", NET) == f"Use {NET} today."


def test_the_canonical_name_is_left_as_it_is() -> None:
    text = f"{NET} reads scenes; {NET} writes them."
    assert canonicalise_name_variants(text, NET) == text


def test_a_technical_identifier_is_not_a_spelling_of_the_name() -> None:
    """Negative controls: each of these is judged by BC-12 as it was before and none is rewritten
    (a hyphen or underscore slug, a cue word, a longer dotted identifier, a path, a name a code
    span or a fence holds, a 'for <platform>' tail the name does not have)."""
    for text in (
        "The package aspose-3d-foss ships it.",
        "The Aspose.3D.FOSS namespace holds it.",
        "The Aspose.3D.FOSS.Tests project covers it.",
        "Open src/Aspose.3D.FOSS/Scene.cs next.",
        "Install `Aspose.3D FOSS` as written.",
        "```text\nAspose.3D FOSS\n```",
        "Aspose.3D FOSS for Java is another product.",
    ):
        assert canonicalise_name_variants(text, NET) == text, text


def test_a_name_without_a_foss_segment_is_not_rewritten_by_its_head() -> None:
    assert canonicalise_name_variants("Aspose.3D reads scenes.", NET) == "Aspose.3D reads scenes."


# Wave-6 acceptance review (acc-w6-pdf-python, U-NAME): two registry names use a hyphen where the
# portfolio's other names use a dot after "Aspose" (naming.py accepts both). The product is
# "Aspose.PDF", the live README's H1 says "Aspose.PDF FOSS for Python", and the candidate's H1,
# every prose mention and the Enterprise anchor said "Aspose PDF FOSS". BC-12 could not catch it:
# its canonical name is this same function, so the truncated name was canonical by construction.


def test_a_hyphen_after_aspose_is_the_dot_of_the_family_name() -> None:
    python = _entry("aspose-pdf-foss/Aspose-PDF-FOSS-for-Python", "pdf", "python")
    go = _entry("aspose-pdf-foss/Aspose-PDF-FOSS-for-Go", "pdf", "go")
    assert product_name(python) == "Aspose.PDF FOSS for Python"
    assert product_name(go) == "Aspose.PDF FOSS for Go"
    # the sibling repositories of the same family, spelled with a dot, were always right
    java = _entry("aspose-pdf-foss/Aspose.PDF-FOSS-for-Java", "pdf", "java")
    assert product_name(java) == "Aspose.PDF FOSS for Java"


def test_every_registry_name_starts_with_the_dotted_product_name() -> None:
    """The invariant behind the fix, over the whole registry: ``Aspose.<Family>`` is the first
    token of every canonical name, whichever separator the repository name uses."""
    import json

    from support import REPO_ROOT

    entries = json.loads((REPO_ROOT / "data" / "registry.json").read_text("utf-8"))["entries"]
    seen = 0
    for row in entries:
        entry = RegistryEntry.model_validate(row)
        first = product_name(entry).split(" ")[0]
        assert first.lower().startswith(f"aspose.{entry.family.lower()}"), (
            entry.repository,
            product_name(entry),
        )
        seen += 1
    assert seen, "the registry is empty"
