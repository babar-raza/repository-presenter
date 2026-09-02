"""Typed fact records: the deterministic evidence every README claim binds to.

A fact is ``{id, kind, value, evidence[], polarity, confidence}`` per README_CONTRACT.md section 3
stage S2. IDs are stable and unique within a document (``<kind>:<slug>``), evidence names the
repository paths that support the value, and the document is written with sorted keys and
sorted records so the same revision always produces the same bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, get_args

FactKind = Literal[
    "identity",
    "package",
    "install_command",
    "import_path",
    "public_symbol",
    "example",
    "format",
    "capability",
    "dependency",
    "license",
    "third_party_notices",
    "build_test_asset",
    "link_target",
    "inherited_unit",
]
Polarity = Literal["SUPPORTED", "CONTRADICTED", "UNRESOLVED"]
FACT_KINDS: tuple[str, ...] = get_args(FactKind)
POLARITIES: tuple[str, ...] = get_args(Polarity)
FACTS_FILENAME = "facts.json"

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_UNSAFE = re.compile(r"[^a-z0-9._-]+")


def slug(text: str) -> str:
    """A lowercase identifier-safe form of ``text`` for use inside a fact ID."""
    cleaned = _UNSAFE.sub("-", text.strip().lower()).strip("._-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if not cleaned or not _SLUG_PATTERN.fullmatch(cleaned):
        raise ValueError(f"cannot derive a fact ID slug from {text!r}")
    return cleaned


def fact_id(kind: FactKind, *parts: str) -> str:
    """Compose ``<kind>:<slug>[.<slug>...]``."""
    if not parts:
        raise ValueError("a fact ID needs at least one part")
    return f"{kind}:" + ".".join(slug(part) for part in parts)


@dataclass(frozen=True)
class Evidence:
    """One repository path that supports a fact, with an optional locator or note."""

    path: str
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("evidence needs a path")


@dataclass(frozen=True)
class Fact:
    """One deterministic claim about the repository at its pinned revision."""

    id: str
    kind: FactKind
    value: str
    evidence: tuple[Evidence, ...]
    polarity: Polarity = "SUPPORTED"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in FACT_KINDS:
            raise ValueError(f"unknown fact kind {self.kind!r}")
        if not self.id.startswith(f"{self.kind}:") or not _SLUG_PATTERN.fullmatch(
            self.id[len(self.kind) + 1 :]
        ):
            raise ValueError(f"fact ID {self.id!r} must be <kind>:<slug> for kind {self.kind!r}")
        if not self.value:
            raise ValueError(f"fact {self.id} has an empty value")
        if not self.evidence:
            raise ValueError(f"fact {self.id} carries no evidence")
        if self.polarity not in POLARITIES:
            raise ValueError(f"fact {self.id} has unknown polarity {self.polarity!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"fact {self.id} confidence must be between 0 and 1")


@dataclass(frozen=True)
class FactsDocument:
    """Every fact extracted for one repository at one revision."""

    repository: str
    source_revision: str
    facts: tuple[Fact, ...]
    schema_version: int = field(default=1)

    def __post_init__(self) -> None:
        ids = [fact.id for fact in self.facts]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate fact IDs: {duplicates}")

    def by_kind(self, kind: FactKind) -> tuple[Fact, ...]:
        return tuple(fact for fact in self.facts if fact.kind == kind)

    def to_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "source_revision": self.source_revision,
            "facts": [asdict(fact) for fact in sorted(self.facts, key=lambda f: f.id)],
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


SYMBOL_MAX_DEPTH = 3
SYMBOL_CAP = 150


def bounded_records(
    document: FactsDocument,
    kinds: Iterable[str],
    polarities: Iterable[str] = ("SUPPORTED",),
    *,
    symbol_max_depth: int = SYMBOL_MAX_DEPTH,
    symbol_cap: int = SYMBOL_CAP,
) -> list[dict[str, str]]:
    """Facts of ``kinds`` and ``polarities`` as packet records, with public symbols bounded.

    Public symbols enter only to ``symbol_max_depth`` dotted parts and ``symbol_cap`` in document
    order, so a job's packet stays bounded however large the surface is.
    """
    admitted_kinds = set(kinds)
    admitted_polarities = set(polarities)
    records: list[dict[str, str]] = []
    symbols = 0
    for fact in document.facts:
        if fact.kind not in admitted_kinds or fact.polarity not in admitted_polarities:
            continue
        if fact.kind == "public_symbol":
            if fact.value.count(".") >= symbol_max_depth or symbols >= symbol_cap:
                continue
            symbols += 1
        record = {"id": fact.id, "kind": fact.kind, "value": fact.value}
        if admitted_polarities != {"SUPPORTED"}:
            record["polarity"] = fact.polarity
        records.append(record)
    return records


def write_facts(document: FactsDocument, path: Path) -> str:
    """Write ``facts.json`` and return the SHA-256 of its bytes."""
    data = document.to_json().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
