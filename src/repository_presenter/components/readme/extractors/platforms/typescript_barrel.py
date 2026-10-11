"""Which TypeScript sources a package actually publishes: its entry point, and what it re-exports.

`RESEARCH_AND_GUIDELINES.md` §29.6 E3. TypeScript has no `public` keyword at module scope and no
namespace a file belongs to: a symbol is part of the package's surface only if the entry point the
manifest declares re-exports it, directly or through another barrel. Everything else is an
implementation file that happens to say `export` so a sibling can import it.

The reading itself - the manifest's entry-point fields, the build-output-to-source mapping through
`tsconfig.json`, the barrel graph and the name-and-module bindings it yields - is the same for
every npm package whatever its language, so it lives in `surface/npm_package.py` and this module
only fixes the TypeScript dialect: `.ts`/`.tsx` sources, no CommonJS. The Node.js plugin composes
the same machinery with its own dialect rather than importing this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.surface import npm_package
from repository_presenter.components.readme.extractors.surface.npm_package import (
    TYPESCRIPT_MODULES,
)


def compiler_options(package: Path) -> dict[str, Any]:
    """The package's own `tsconfig.json` compiler options, or an empty mapping."""
    return npm_package.compiler_options(package, TYPESCRIPT_MODULES.config_names)


def entry_barrel(package: Path) -> Path | None:
    """The source file that is this package's public entry point, or None when it has none."""
    return npm_package.entry_barrel(package, TYPESCRIPT_MODULES)


def reexported_bindings(barrel: Path) -> dict[str, frozenset[Path] | None]:
    """Every name the entry point re-exports, and the module each name is bound *from*."""
    return npm_package.reexported_bindings(barrel, TYPESCRIPT_MODULES)


def reexported_names(barrel: Path) -> frozenset[str]:
    """Every name the entry point re-exports, without the module each is bound from."""
    return npm_package.reexported_names(barrel, TYPESCRIPT_MODULES)
