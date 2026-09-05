"""Per-ecosystem presentation knowledge the shell rows rely on, keyed by registry ecosystem.

README_CONTRACT.md section 2 names the package registries the badge row and the Installation
row present (row 2, row 8). Their display names are proper nouns a visitor reads, never
identifiers, so authored prose may spell them as written here; the renderer names the
registry a verified install came from with the same spelling; from G4-W10 the renderer takes
that spelling from the ecosystem spec (core/ecosystems.py), and this table is the prose
vocabulary alone - a candidate may name NuGet without a NuGet spec being registered.
"""

from __future__ import annotations

from collections.abc import Iterable

REGISTRY_NAMES: dict[str, str] = {
    "python": "PyPI",
    "java": "Maven Central",
    "dotnet": "NuGet",
    "node": "npm",
    "rust": "crates.io",
    "go": "pkg.go.dev",
}
# The code-hosting sites a verified link may point at. A visitor reads "the GitHub issue
# tracker" the way they read "PyPI": a proper noun, never an API name, so prose spells it as
# written here and the renderer leaves it out of a code span. A name enters the allowed set only
# when a SUPPORTED fact actually links to that host (G2-W13, where the guard rejected the word
# twice and the composition failed closed).
HOST_NAMES: dict[str, str] = {
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "bitbucket.org": "Bitbucket",
}


def host_names(values: Iterable[str]) -> frozenset[str]:
    """The display names of the hosting sites the given fact values link to."""
    return frozenset(
        name for host, name in HOST_NAMES.items() if any(host in value for value in values)
    )
