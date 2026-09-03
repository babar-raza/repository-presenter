"""Per-ecosystem presentation knowledge the shell rows rely on, keyed by registry ecosystem.

README_CONTRACT.md section 2 names the package registries the badge row and the Installation
row present (row 2, row 8). Their display names are proper nouns a visitor reads, never
identifiers, so authored prose may spell them as written here; the renderer names the
registry a verified install came from with the same spelling. G2-W07 extends this table when
the second ecosystem arrives; nothing here imports an extractor.
"""

from __future__ import annotations

REGISTRY_NAMES: dict[str, str] = {
    "python": "PyPI",
    "java": "Maven Central",
    "dotnet": "NuGet",
    "node": "npm",
    "rust": "crates.io",
    "go": "pkg.go.dev",
}


def registry_name(ecosystem: str) -> str:
    """The registry's display name for an ecosystem, or a plain phrase when none is known."""
    return REGISTRY_NAMES.get(ecosystem, "the package registry")
