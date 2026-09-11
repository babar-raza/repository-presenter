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
from collections.abc import Collection, Iterable
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
_SEPARATOR_RUN = re.compile(r"[._-]{2,}")


def slug(text: str) -> str:
    """A lowercase identifier-safe form of ``text`` for use inside a fact ID."""
    cleaned = _UNSAFE.sub("-", text.strip().lower()).strip("._-")
    # A run of separators keeps its first character. Python names a symbol dict_ or class_ to
    # avoid a keyword, so a path like aspose_font.cff.dict_.PrivateDictOp arrives with "_." in
    # it; collapsing the run to "." would merge that symbol with a real dict module, while
    # keeping the first character distinguishes them (measured on Aspose.Font, 2026-09-06).
    cleaned = _SEPARATOR_RUN.sub(lambda match: match.group(0)[0], cleaned)
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
    # Structured, kind-specific attributes a consumer reads without parsing evidence text
    # (a public symbol's kind, signature, and docstring first line); None for most kinds.
    attributes: dict[str, str] | None = None

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
        if self.attributes is not None and not all(
            isinstance(k, str) and isinstance(v, str) and k and v
            for k, v in self.attributes.items()
        ):
            raise ValueError(f"fact {self.id} attributes must map non-empty strings to strings")


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

    def canonical(self) -> FactsDocument:
        """The same document with its facts in ID order: the one order a bundle stores
        (``to_json``) and the renderer reads, so a candidate renders the same bytes live and
        again from its own ``facts.json``.

        G4-W17 arrival items 48 and 61. Extractors emit facts in whatever order their source
        declares them - Cargo.toml order on Aspose.Cells for Rust, pom.xml order on Aspose.Cells
        for Java, whose two development dependencies transposed on re-render (lane C PROPOSAL Y,
        measured with zero provider calls) - and nothing stated the invariant the sealed-bytes
        control silently relied on. This is that statement. Job packets deliberately keep the
        order extraction built: ``bounded_records`` reads ``self.facts`` as given, so a sealed
        candidate's request hashes never move because of this.
        """
        return FactsDocument(
            self.repository,
            self.source_revision,
            tuple(sorted(self.facts, key=lambda fact: fact.id)),
            self.schema_version,
        )

    def to_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "source_revision": self.source_revision,
            "facts": [asdict(fact) for fact in self.canonical().facts],
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


SYMBOL_MAX_DEPTH = 3
# G4-W17 arrival item 27. `bounded_records` admits public_symbol facts in document order and
# stops at this cap - a repository whose surface exceeds it never has its later symbols in any
# job's packet at all, however alphabetically or structurally important they are. Measured
# 2026-09-06 on Aspose.PDF for Go (1,467 symbols): truncation at 150 landed mid-alphabet and
# `Document`, the product's own entry-point type, and its methods were never seen by any job.
# The reviewer's own proposal named 2000 as "well above current portfolio surfaces", but this
# session had already measured larger ones directly: Aspose.3D for Java carries 5,366
# public_symbol facts (item 12's landing, this file), Aspose.Slides for C++ 2,845 (item 19's) -
# both already over 2000. Set from the largest of at least three measured compositions, with
# headroom, per this project's own threshold rule (RESEARCH_AND_GUIDELINES.md section 27.10
# follow-up 3): the observed maximum (5,366) rounded up with margin, not the smaller number first
# proposed before this session's own larger readings were available.
SYMBOL_CAP = 6000

LINK_CAP = 100
# PHASE0/J2 (found by J1's own new structural tests, xfail(strict=True) until this landed):
# bounded_records's numeric cap was hardwired to fact.kind == "public_symbol" only - link_target
# passed through with zero limit even after link_fact_id's own enum construction started routing
# through this function for code-path consistency with the packet (Taskcard H). Measured
# 2026-09-10 across all 8 currently-sealed candidates (loop-prompt.md section 3's own "at least
# three compositions" rule): aspose-pdf-foss-Java's own 41 link_target facts is the observed
# maximum. Set with real headroom above it, mirroring SYMBOL_CAP's own "largest measured plus
# margin" precedent above, not a guess.
EXAMPLE_CAP = 30
# Same gap, same fix: the four example-ID enums fed by the same "verified" list also passed
# through uncapped. Measured 2026-09-10 across the same 8 candidates: aspose-slides-foss-Python's
# own 14 example facts is the observed maximum.


# G5-W02 (27.2 RC4). A job packet is rendered to text and hashed to key the call store, so a fact
# embedded in every packet makes that hash change whenever the fact does - identity:revision is
# exactly that: constant within one revision, but different on every new one, even when nothing a
# job would actually reason about (public symbols, formats, examples, links) changed at all. A
# fresh clone at an unchanged revision needs no exclusion (the value is the same either way), but a
# new revision could never reuse a cached call while its own coordinate rides along in every
# packet. The renderer reads identity:revision straight from FactsDocument, never through a
# packet, so no job ever needed to see it: nothing here narrows what a job may cite or claim.
_EXCLUDED_FROM_PACKETS = frozenset({"identity:revision"})

# What the vendored surface engine records each public symbol to BE
# (`extractors/surface/extractor.py::_KINDS`): a module, a class, an enum, or a free function -
# every top-level declaration - as against ``method``, the one kind that is a member of another
# symbol. ``symbol_max_depth`` is a proxy for that same distinction, and a bad one: it counts dots
# in the whole dotted path, so how much of a repository's surface a job may cite depends on how
# many segments its package root happens to have. Measured 2026-09-07 (G4-W17 arrival item 40,
# ported into PHASE0/G, 2026-09-11 - PR #29 landed the fix, never merged; independently confirmed
# by this pass's own Taskcard I investigation, same numbers) across the sealed bundles at
# ``SYMBOL_MAX_DEPTH = 3``: Aspose.PDF for Java admits 3 of 24,830 public symbols (`org`,
# `org.aspose`, `org.aspose.pdf` - not one class), Aspose.3D for Java 3 of 5,366, Aspose.Cells for
# C++ 122 of 1,943; while Aspose.Slides for Python, whose root is one segment, admits 1,702 of
# 3,180 including every method. A caller that passes this set bounds its packet by the recorded
# granularity instead, which is root-shape independent and still bounded: the same measurement
# gives 1,240 symbols for Aspose.PDF for Java, 269 for Aspose.3D for Java, 535 for Slides Python,
# 100 for Cells .NET (unchanged) - every one far inside ``SYMBOL_CAP``.
DECLARED_SYMBOL_KINDS = frozenset({"module", "class", "enum", "function"})


def _admits_symbol(fact: Fact, symbol_kinds: Collection[str] | None, symbol_max_depth: int) -> bool:
    """Whether one ``public_symbol`` fact enters a packet, before the cap is applied.

    By the kind the extractor recorded when the caller names a set and the fact records one;
    otherwise by the dotted-depth proxy. A fact whose ``symbol_kind`` is absent or ``unknown``
    keeps the old bound rather than vanishing: an ecosystem whose grammar the surface facade's
    table does not yet map records ``unknown`` for its whole surface (measured 2026-09-06 on Go
    and Rust, G4-W17 arrival item 9), and dropping all of it would be a silent, total loss.
    """
    recorded = (fact.attributes or {}).get("symbol_kind")
    if symbol_kinds is not None and recorded not in (None, "", "unknown"):
        return recorded in symbol_kinds
    return fact.value.count(".") < symbol_max_depth


def bounded_records(
    document: FactsDocument,
    kinds: Iterable[str],
    polarities: Iterable[str] = ("SUPPORTED",),
    *,
    symbol_max_depth: int = SYMBOL_MAX_DEPTH,
    symbol_cap: int = SYMBOL_CAP,
    symbol_kinds: Collection[str] | None = None,
    link_cap: int = LINK_CAP,
    example_cap: int = EXAMPLE_CAP,
) -> list[dict[str, str]]:
    """Facts of ``kinds`` and ``polarities`` as packet records, with public symbols, links, and
    examples all bounded.

    Public symbols enter only to ``symbol_max_depth`` dotted parts - or, when the caller names
    ``symbol_kinds``, only at the granularity the extractor recorded (see
    ``DECLARED_SYMBOL_KINDS``) - and ``symbol_cap`` in document order; ``link_target`` and
    ``example`` facts enter only to ``link_cap``/``example_cap`` in document order too
    (PHASE0/J2) - so a job's packet stays bounded however large the repository's own surface,
    link count, or example count is. ``identity:revision`` never enters any packet at all, so its
    own bundled call cache reuses across a revision bump that changes no fact a job would ever
    reason about.
    """
    admitted_kinds = set(kinds)
    admitted_polarities = set(polarities)
    records: list[dict[str, str]] = []
    symbols = 0
    links = 0
    examples = 0
    for fact in document.facts:
        if fact.id in _EXCLUDED_FROM_PACKETS:
            continue
        if fact.kind not in admitted_kinds or fact.polarity not in admitted_polarities:
            continue
        if fact.kind == "public_symbol":
            if symbols >= symbol_cap or not _admits_symbol(fact, symbol_kinds, symbol_max_depth):
                continue
            symbols += 1
        elif fact.kind == "link_target":
            if links >= link_cap:
                continue
            links += 1
        elif fact.kind == "example":
            if examples >= example_cap:
                continue
            examples += 1
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
