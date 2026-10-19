"""M8: the claim sampler. Draws the claims a human auditor reads, reproducibly and blind.

A claim is one sentence of an LLM-owned content unit together with the values of the facts that unit
cites. The universe is sorted by a stable key, so ``draw(universe, seed, size)`` returns the same
claims on any machine; the committed ``SEED`` makes the C8 draw repeatable and unarguable (the
pilot, not C1, draws the sample from its own candidates). The auditor's form hides which pipeline
route wrote the candidate; the answer key (the unit label and the route) is kept apart.

Procedure (M8, claim-level blind audit; run by the C8 pilot):

1. Build the universe from the pilot's candidates: ``claim_universe(bundles)``.
2. Draw ``size`` claims (default 200) with ``draw(universe, SEED, size)``; stratify nothing else.
3. Render ``blind_form(sample)`` (claim sentence, cited fact values, no route, no bundle name) and
   give it to the human auditor; the auditor marks each claim SUPPORTED, UNSUPPORTED or
   CONTRADICTED by the cited values and the pinned source.
4. M8 passes when zero of the 200 are UNSUPPORTED or CONTRADICTED; report the exact binomial
   upper bound beside it (zero in 200 bounds the rate near 1.5 percent at 95 percent confidence).
"""

from __future__ import annotations

import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .pinned import PinnedBundle

SEED = 20261016
DEFAULT_SIZE = 200
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\"(])")


@dataclass(frozen=True)
class Claim:
    key: str  # "<bundle directory>|<section>/<slot>|<index>", the stable sort and answer key
    sentence: str
    cited_values: tuple[str, ...]


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE.split(text.strip()) if part.strip()]


def claim_universe(bundles: Iterable[PinnedBundle]) -> list[Claim]:
    """Every sentence of every LLM-owned unit of the bundles, sorted by key."""
    claims: list[Claim] = []
    for bundle in bundles:
        for unit in (bundle.content_units or {}).get("units", []):
            cited = tuple(
                f"{fact_id}={_short(bundle.facts_by_id.get(fact_id))}"
                for fact_id in unit.get("fact_ids", [])
                if bundle.facts_by_id.get(fact_id, {}).get("kind") != "identity"
            )
            label = f"{unit.get('section')}/{unit.get('slot')}"
            for index, sentence in enumerate(sentences(str(unit.get("text", "")))):
                claims.append(Claim(f"{bundle.pin.directory}|{label}|{index}", sentence, cited))
    return sorted(claims, key=lambda claim: claim.key)


def _short(fact: Any) -> str:
    if not isinstance(fact, dict):
        return "?"
    return str(fact.get("value", ""))[:120].replace("\n", " ")


def draw(universe: Sequence[Claim], seed: int = SEED, size: int = DEFAULT_SIZE) -> list[Claim]:
    """A reproducible simple random sample without replacement."""
    if size > len(universe):
        raise ValueError(f"universe has {len(universe)} claims, fewer than {size}")
    return sorted(random.Random(seed).sample(list(universe), size), key=lambda claim: claim.key)


def blind_form(sample: Sequence[Claim]) -> list[dict[str, Any]]:
    """The auditor's rows: numbered in a seeded shuffle, no route or bundle shown."""
    order = list(range(len(sample)))
    random.Random(SEED + 1).shuffle(order)
    return [
        {
            "n": number + 1,
            "claim": sample[index].sentence,
            "cited_values": list(sample[index].cited_values),
            "verdict": None,
        }
        for number, index in enumerate(order)
    ]
