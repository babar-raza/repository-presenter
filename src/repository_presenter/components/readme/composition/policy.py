"""The presentation policy: ceilings and budgets the plan must respect and the renderer enforces.

These are the contract's defaults (docs/README_CONTRACT.md sections 1 and 2). A per-repository
or per-family overlay under profiles/ arrives with the family that needs it; until then the
derived defaults apply and the Enterprise Edition target is absent, so that section is omitted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

POLICY_VERSION = "1"


@dataclass(frozen=True)
class PlanningPolicy:
    capabilities_min: int = 3
    capabilities_max: int = 8
    api_hubs_max: int = 12
    aspose_links_max: int = 4
    visible_lines_budget: int = 300
    total_lines_budget: int = 600
    enterprise_target_url: str | None = None


DEFAULT_POLICY = PlanningPolicy()


def policy_packet(policy: PlanningPolicy = DEFAULT_POLICY) -> dict[str, Any]:
    return {"version": POLICY_VERSION, **asdict(policy)}
