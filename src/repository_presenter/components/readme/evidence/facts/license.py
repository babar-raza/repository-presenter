"""License facts from the license file's own text, classified to an SPDX identifier."""

from __future__ import annotations

import re
from pathlib import Path

from repository_presenter.core.facts import Evidence, Fact, fact_id

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


KNOWN_IDENTIFIERS: frozenset[str] = frozenset(spdx_id for _, spdx_id in _CLASSIFIERS)
# The evidence a manifest-declared license carries (G4-W17 arrival item 51); the renderer reads
# the evidence path, never this text.
DECLARED_LICENSE_DETAIL = "license declared by the manifest; no license file at this revision"


def classify_license_text(text: str) -> str | None:
    """Return the SPDX identifier the license text states, or ``None`` if unrecognized."""
    for pattern, spdx_id in _CLASSIFIERS:
        if pattern.search(text):
            return spdx_id
    return None


def classify_declaration(declared: str) -> str | None:
    """The SPDX identifier a manifest's license field names, or ``None`` when it names none known.

    A manifest spells the identifier itself (`"license": "MIT"` in package.json, `license =
    "Apache-2.0"` in Cargo.toml) or the licence's name (`{text = "MIT License"}` in pyproject);
    both classify, and anything else (`SEE LICENSE IN EULA.txt`) is not a fact the contract
    can render.
    """
    stated = declared.strip()
    if stated in KNOWN_IDENTIFIERS:
        return stated
    return classify_license_text(stated) if stated else None


def license_facts(
    clone_path: Path,
    license_path: str | None,
    notices_path: str | None = None,
    declared: str | None = None,
    declared_in: str | None = None,
) -> list[Fact]:
    """The license file and its SPDX identity when the text states one, plus any notices file.

    G4-W17 arrival item 51 (DIRECTIVE 2026-09-06 20:05 rule 1): a repository that ships no license
    file may still state its license in its manifest - Aspose.3D for TypeScript declares
    `"license": "MIT"` in package.json and carries nothing else - and that declaration, passed
    here as ``declared`` with the manifest path ``declared_in``, is then the `license:spdx` fact,
    the manifest its evidence. It never adds a `license:file` fact, so the renderer links no file
    that does not exist. Where a file exists its own text stays the evidence and the declaration
    is not consulted, so no sealed bundle's facts move.
    """
    notices = (
        [
            Fact(
                fact_id("third_party_notices", "file"),
                "third_party_notices",
                notices_path,
                (Evidence(notices_path, "third-party notices file at the root"),),
            )
        ]
        if notices_path is not None
        else []
    )
    if license_path is None:
        spdx = classify_declaration(declared) if declared else None
        if spdx is None or not declared_in:
            return notices
        declared_fact = Fact(
            fact_id("license", "spdx"),
            "license",
            spdx,
            (Evidence(declared_in, DECLARED_LICENSE_DETAIL),),
        )
        return [declared_fact, *notices]
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
    return facts + notices
