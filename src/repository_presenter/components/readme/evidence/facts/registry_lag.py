"""The registry's release lags the source tree: the fact behind an upstream's version-skew warning.

Wave-3 acceptance review (Slides-Python): the live README warns, twice, that the PyPI release
(26.8.0) predates the source tree - hyperlinks, strict property assignment and the six PowerPoint
save formats are in ``CHANGELOG.md`` under ``## [Unreleased]`` and not in the release - and tells
the reader to install from the repository. The candidate dropped both warnings and documented
those very members next to a ``pip install`` line, so a reader following it met a module without
``Hyperlink``. Reconciliation had omitted the warning as "contradicted by package:version and
package:published_version both being 26.8.0": the model compared two version numbers, which agree,
and not what they were claimed to bracket, which is a tree with unreleased changes.

The skew is decidable from files the extractor already reads, so it is a fact, not a judgement:

* ``manifest_newer``: the manifest's version is greater than the registry's current release (the
  source declares a version nobody can install yet);
* ``changelog_unreleased``: the root changelog's ``## [Unreleased]`` section lists entries (the
  source holds changes no release has).

Either needs the registry's own reading (``package:published_version``): without one nothing says
what a reader can install, and no skew is claimed. The fact's value is that release, so a sentence
stating it ("`pip install` gets 26.8.0") can be held to it; a unit that warns of the skew is then a
must-carry claim (``reconciliation/dispositions.py``: ``OMIT_VERSION_SKEW``).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.facts import Evidence, Fact, fact_id
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

REGISTRY_LAG_FACT_ID = fact_id("package", "registry_lag")
_CHANGELOG = re.compile(r"(?i)^(?:changelog|changes|history)(?:\.md|\.markdown|\.rst|\.txt)?$")
_UNRELEASED = re.compile(r"(?i)^#{1,3}\s*\[?\s*unreleased\s*\]?(?:\s*[-:(].*)?\s*$")
_HEADING = re.compile(r"^#{1,3}\s+\S")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+\S")
_NUMBER = re.compile(r"\d+")


def _version_key(text: str) -> tuple[int, ...] | None:
    """The dotted-number prefix of a version (``26.8.0``, ``v1.2``), or None when it has none."""
    match = re.match(r"\s*v?(\d+(?:\.\d+)*)", text)
    return tuple(int(part) for part in _NUMBER.findall(match.group(1))) if match else None


def unreleased_entries(changelog: str) -> int:
    """How many entries the changelog's ``Unreleased`` section lists (bullets, any depth)."""
    inside = False
    count = 0
    for line in changelog.splitlines():
        if _UNRELEASED.match(line):
            inside = True
            continue
        if inside and _HEADING.match(line) and not line.startswith("###"):
            break
        if inside and _BULLET.match(line):
            count += 1
    return count


def registry_lag_fact(
    facts: Sequence[Fact], clone_path: Path, tree_paths: Sequence[str]
) -> Fact | None:
    """``package:registry_lag`` when the registry's current release lags this source tree, else
    None; see the module docstring for the two bases and why a registry reading is required."""
    published = next(
        (f for f in facts if f.id == PUBLISHED_VERSION_FACT_ID and f.polarity == "SUPPORTED"), None
    )
    if published is None:
        return None
    evidence: list[Evidence] = []
    bases: list[str] = []
    manifest = next((f for f in facts if f.id == "package:version"), None)
    declared = _version_key(manifest.value) if manifest is not None else None
    current = _version_key(published.value)
    if manifest is not None and declared is not None and current is not None and declared > current:
        bases.append("manifest_newer")
        evidence.append(
            Evidence(
                manifest.evidence[0].path,
                f"manifest version {manifest.value} is newer than the registry's current "
                f"release {published.value}",
            )
        )
    changelog = next((p for p in tree_paths if "/" not in p and _CHANGELOG.match(p)), None)
    if changelog is not None:
        text = (clone_path / changelog).read_text(encoding="utf-8", errors="replace")
        entries = unreleased_entries(text)
        if entries:
            bases.append("changelog_unreleased")
            evidence.append(
                Evidence(
                    changelog,
                    f"`## [Unreleased]` lists {entries} entries; the registry's current release "
                    f"is {published.value}",
                )
            )
    if not evidence:
        return None
    return Fact(
        REGISTRY_LAG_FACT_ID,
        "package",
        published.value,
        tuple(evidence),
        attributes={"basis": ",".join(bases)},
    )
