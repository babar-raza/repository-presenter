"""The closed set of correction detectors, registered by name.

A detector is a pure function ``Context -> DetectorResult`` registered with ``@detector(name)``;
``load_detectors`` imports every public module in this package so adding a detector is adding a
file and its test, never a branch in the engine (AGENTS.md: registries, not a central if/elif).
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

from repository_presenter.components.readme_correction.model import Detector

DETECTORS: dict[str, Detector] = {}


def detector(name: str) -> Callable[[Detector], Detector]:
    def register(function: Detector) -> Detector:
        if name in DETECTORS:
            raise ValueError(f"detector {name!r} is registered twice")
        DETECTORS[name] = function
        return function

    return register


def load_detectors() -> dict[str, Detector]:
    """Every registered detector, in name order, after importing the package's modules."""
    for module in pkgutil.iter_modules(__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{__name__}.{module.name}")
    return dict(sorted(DETECTORS.items()))
