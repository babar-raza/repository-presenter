"""License facts from the license file's own text, classified to an SPDX identifier."""

from __future__ import annotations

import re
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.records import Evidence, Fact, fact_id

_CLASSIFIERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmit license\b", re.IGNORECASE), "MIT"),
    (re.compile(r"\bapache license\b.*\bversion 2\.0\b", re.IGNORECASE | re.DOTALL), "Apache-2.0"),
    (
        re.compile(r"\bgnu general public license\b.*\bversion 3\b", re.IGNORECASE | re.DOTALL),
        "GPL-3.0",
    ),
    (re.compile(r"\bbsd 3-clause\b", re.IGNORECASE), "BSD-3-Clause"),
    (re.compile(r"\bbsd 2-clause\b", re.IGNORECASE), "BSD-2-Clause"),
    (re.compile(r"\bisc license\b", re.IGNORECASE), "ISC"),
    (re.compile(r"\bmozilla public license\b", re.IGNORECASE), "MPL-2.0"),
)


def classify_license_text(text: str) -> str | None:
    """Return the SPDX identifier the license text states, or ``None`` if unrecognized."""
    for pattern, spdx_id in _CLASSIFIERS:
        if pattern.search(text):
            return spdx_id
    return None


def license_facts(clone_path: Path, license_path: str | None) -> list[Fact]:
    """The license file as a fact, plus its SPDX identity when the text states one."""
    if license_path is None:
        return []
    facts = [Fact(fact_id("license", "file"), "license", license_path, (Evidence(license_path),))]
    text = (clone_path / license_path).read_text(encoding="utf-8", errors="replace")
    spdx = classify_license_text(text)
    if spdx is not None:
        facts.append(
            Fact(
                fact_id("license", "spdx"),
                "license",
                spdx,
                (Evidence(license_path, "license text states this license"),),
            )
        )
    else:
        facts.append(
            Fact(
                fact_id("license", "spdx"),
                "license",
                "UNCLASSIFIED",
                (Evidence(license_path, "license text matched no known classifier"),),
                polarity="UNRESOLVED",
                confidence=0.0,
            )
        )
    return facts
