"""The identity component: the complete canonical product name the H1 and the prose use.

Derived deterministically from the governed repository name (``Aspose.3D-FOSS-for-Python`` becomes
``Aspose.3D FOSS for Python``): hyphens separate words, dots stay inside the family name, and
nothing is abbreviated. The authoring guard lists the name's tokens as identifiers the prose may
use; the renderer emits it as the only H1.
"""

from __future__ import annotations

from repository_presenter.core.registry.models import RegistryEntry


def product_name(entry: RegistryEntry) -> str:
    return " ".join(part for part in entry.name.split("-") if part)


def product_name_tokens(name: str) -> frozenset[str]:
    """The name's space-separated tokens, each an identifier the prose may spell as written."""
    return frozenset(token for token in name.split(" ") if token)
