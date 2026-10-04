"""The presentation policy: ceilings and budgets the plan must respect and the renderer enforces.

These are the contract's defaults (docs/README_CONTRACT.md sections 1 and 2). A per-repository
or per-family overlay under profiles/ arrives with the family that needs it; until then the
derived defaults apply and the Enterprise Edition target is absent, so that section is omitted.

Aspose-link ceilings (plans/idea.md, "Aspose-link density must adapt to the README"): when
``link_allocation`` is configured its maxima replace the automatic allocation; otherwise
``link_budget.resolve_link_budget`` derives them per document, never above ``aspose_links_max``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from repository_presenter.components.readme.composition.link_budget import (
    AUTOMATIC_TOTAL_CAP,
    LinkAllocationPolicy,
)

POLICY_VERSION = "1"


@dataclass(frozen=True)
class PlanningPolicy:
    capabilities_min: int = 3
    capabilities_max: int = 8
    api_hubs_max: int = 12
    # The cap on the automatic Aspose-link total; the derived ceiling of any one document is at
    # most this. Replaced entirely by ``link_allocation.max_total`` when that is configured.
    aspose_links_max: int = AUTOMATIC_TOTAL_CAP
    visible_lines_budget: int = 300
    total_lines_budget: int = 600
    enterprise_target_url: str | None = None
    link_allocation: LinkAllocationPolicy | None = None


DEFAULT_POLICY = PlanningPolicy()


def policy_packet(policy: PlanningPolicy = DEFAULT_POLICY) -> dict[str, Any]:
    """The policy as the planner and the bundle see it. Unconfigured, the packet is byte-for-byte
    what it was before link allocation existed; configured, the explicit maxima appear and the
    total replaces ``aspose_links_max``."""
    packet = {"version": POLICY_VERSION, **asdict(policy)}
    configured = packet.pop("link_allocation")
    if configured is not None:
        packet["link_allocation"] = configured
        packet["aspose_links_max"] = configured["max_total"]
    return packet
