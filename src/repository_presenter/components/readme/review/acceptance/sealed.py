"""Score a sealed bundle under the ratified profile, with D14's portfolio inputs.

The score is a pure function of three sealed files (``README.md``, ``validation.json``,
``review.json``) plus, for disqualifier D14, ``facts.json`` and the READMEs of the OTHER current
bundles in ``candidates/`` as the template corpus. Nothing here writes, calls a provider, or reads
the network, so a status report can recompute the score instead of trusting a record sealed under
an older profile or scorer.

D14 asks whether a section is template filling, which is a comparison between repositories; one
repository's own seal has no corpus to compare against, so the repair round records D14 as
unevaluated and the portfolio funnel supplies the corpus here. A bundle with no other current
bundle, or with unreadable facts, gets no inputs and so can never score ``PASS``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.review.acceptance.scorer import score_candidate
from repository_presenter.components.readme.review.acceptance.template_check import (
    Evidence,
    ReferenceSection,
    TemplateInputs,
    sections_of,
)
from repository_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME

README_FILENAME = "README.md"
FACTS_FILENAME = "facts.json"
VALIDATION_FILENAME = "validation.json"
REVIEW_FILENAME = "review.json"
# facts.json kinds whose values are identifiers, commands, or paths of the immutable revision.
FACT_TOKEN_KINDS = frozenset(
    {"install_command", "import_path", "public_symbol", "build_test_asset", "dependency"}
)


@dataclass(frozen=True)
class SealedReadme:
    """One sealed README with the evidence D14 masks and matches by."""

    directory: str
    readme: str
    product_name: str
    version: str
    fact_tokens: frozenset[str]


def load_sealed_readme(directory: str, bundle: Path) -> SealedReadme | None:
    """The README and evidence of one sealed bundle, or None when either cannot be read."""
    try:
        readme = (bundle / README_FILENAME).read_text(encoding="utf-8")
        facts = json.loads((bundle / FACTS_FILENAME).read_text(encoding="utf-8"))
        repository = str(facts["repository"])
        rows = [row for row in facts["facts"] if isinstance(row, dict)]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    slug = repository.rsplit("/", 1)[-1]
    name = " ".join(part for part in slug.split("-") if part)
    version = next(
        (str(row.get("value", "")) for row in rows if row.get("id") == "package:version"), ""
    )
    tokens = frozenset(
        str(row["value"]).strip()
        for row in rows
        if row.get("kind") in FACT_TOKEN_KINDS
        and row.get("polarity") == "SUPPORTED"
        and isinstance(row.get("value"), str)
        and str(row["value"]).strip()
    ) | frozenset(
        str(row["value"]).strip()
        for row in rows
        if row.get("id") == "package:name" and isinstance(row.get("value"), str)
    )
    return SealedReadme(directory, readme, name, version, tokens)


def load_current_readmes(root: Path) -> list[SealedReadme]:
    """The README and evidence of every current bundle under ``root``/candidates."""
    loaded: list[SealedReadme] = []
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return loaded
    for repository in sorted(path for path in candidates.iterdir() if path.is_dir()):
        pointer = repository / CURRENT_FILENAME
        try:
            revision = pointer.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        sealed = load_sealed_readme(repository.name, repository / revision)
        if sealed is not None:
            loaded.append(sealed)
    return loaded


def reference_corpus(readmes: Sequence[SealedReadme], exclude: str) -> list[ReferenceSection]:
    """Every section of every other repository's sealed README, in directory order."""
    return [
        ReferenceSection(heading, body, other.product_name, other.version)
        for other in sorted(readmes, key=lambda item: item.directory)
        if other.directory != exclude
        for heading, body in sections_of(other.readme)
    ]


def template_inputs(
    subject: SealedReadme, readmes: Sequence[SealedReadme]
) -> TemplateInputs | None:
    """D14's inputs for ``subject``, or None when there is no other repository to compare with."""
    corpus = reference_corpus(readmes, subject.directory)
    if not corpus:
        return None
    return TemplateInputs(
        Evidence(subject.product_name, subject.version, subject.fact_tokens), corpus
    )


def _read_object(path: Path) -> Mapping[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def score_sealed_bundle(
    bundle: Path, subject: SealedReadme | None, readmes: Sequence[SealedReadme]
) -> dict[str, Any]:
    """The acceptance record of one sealed bundle. ``subject`` is that bundle's loaded README
    (None when it cannot be read, which scores as an empty README with D14 unevaluated)."""
    template = None if subject is None else template_inputs(subject, readmes)
    readme = "" if subject is None else subject.readme
    return score_candidate(
        readme,
        _read_object(bundle / VALIDATION_FILENAME),
        _read_object(bundle / REVIEW_FILENAME),
        template=template,
    )
