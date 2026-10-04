"""Model availability at run start: a route's own model must prove it can do the work, or stop.

A prompt manifest names its ``model_route``, and that route's model is the only model a sealed
result may come from. A substitute model would produce a different result, so there is none:
``FALLBACK_CHAINS`` is empty by owner decision, and every route's chain is the route alone.

At run start the route's model is probed with a strict json_schema request, the same request shape
a content call sends (``transport.probe_availability``), ``PROBE_CONSECUTIVE_PASSES`` times in a
row. It is available only if every probe passes: HTTP 200 with content that parses against the
probe schema. A failed probe is a failure; no retry hides it. If the route's model is not
available, the run fails closed with ``ModelChainExhaustedError`` naming the model and its probe
result, before any content call is made. The decision is a frozen value: no call in the run may
name any other model, and nothing in a run probes again.

A sealed bundle's recorded model is honoured only when it is the route's own model; any other
recorded model is named as not in the chain and ignored.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, GatewayError
from repository_presenter.core.llm.transport import AvailabilityProbe, probe_availability

# Keyed by manifest ``model_route``; values would be fallbacks tried after the route itself. Empty
# on purpose: a sealed result must come from the route's own model, never a substitute. Adding an
# entry is a change to what a sealed result is, and needs an owner decision, not a code review.
FALLBACK_CHAINS: Mapping[str, tuple[str, ...]] = {}

# How many probes in a row the route's model must pass before it counts as available. A probe that
# fails ends that run of passes, and the model is unavailable for the run.
PROBE_CONSECUTIVE_PASSES = 2


class ModelChainExhaustedError(GatewayError):
    """The route's model did not pass its availability probes at run start; the run fails closed."""


def chain_for(route: str) -> tuple[str, ...]:
    """The route alone, followed by any configured fallbacks (none today)."""
    fallbacks = FALLBACK_CHAINS.get(route, ())
    if route in fallbacks or len(set(fallbacks)) != len(fallbacks):
        raise ConfigError(f"fallback chain for {route!r} repeats a model: {fallbacks}")
    return (route, *fallbacks)


@dataclass(frozen=True)
class RouteDecision:
    """The one model a route uses for this run, and why that model rather than another."""

    route: str
    chain: tuple[str, ...]
    model: str
    recorded: str | None
    reason: str


@dataclass(frozen=True)
class ModelSelection:
    """Every route's effective model for one run, fixed when it was made."""

    probes: tuple[AvailabilityProbe, ...]
    decisions: Mapping[str, RouteDecision] = field(default_factory=dict)

    def model_for(self, route: str) -> str:
        """The model every call of ``route`` in this run names; never a different one."""
        decision = self.decisions.get(route)
        if decision is None:
            raise ConfigError(
                f"no model was selected for route {route!r} in this run; selected routes: "
                f"{', '.join(sorted(self.decisions)) or 'none'}"
            )
        return decision.model

    def models_used(self) -> dict[str, str]:
        """route -> effective model, the provenance a sealed bundle records as models_used."""
        return {route: decision.model for route, decision in sorted(self.decisions.items())}


def _probe(config: GatewayConfig, model: str, listed: Sequence[str] | None) -> AvailabilityProbe:
    """Available only after ``PROBE_CONSECUTIVE_PASSES`` passes in a row; the first failure ends it.

    No retry: a failure is recorded as the model's outcome, with how many passes came before it,
    so a model that passes once and then fails is never chosen on the strength of the pass.
    """
    required = PROBE_CONSECUTIVE_PASSES
    if required < 1:
        raise ConfigError(f"PROBE_CONSECUTIVE_PASSES must be at least 1, not {required}")
    if listed is not None and model not in listed:
        return AvailabilityProbe(model, False, "not in the recorded catalog")
    passes = 0
    for _ in range(required):
        probe = probe_availability(config, model)
        if not probe.available:
            after = f" after {passes} of {required} consecutive passes" if passes else ""
            return AvailabilityProbe(model, False, f"{probe.detail}{after}")
        passes += 1
    return AvailabilityProbe(
        model, True, f"{probe.detail}, {passes} of {required} consecutive passes"
    )


def _reason(route: str, chain: tuple[str, ...], model: str, recorded: str | None) -> str:
    if recorded is not None and model == recorded:
        return "recorded model still available"
    if recorded is not None and recorded not in chain:
        return f"recorded model {recorded} is not in the chain"
    if recorded is not None:
        return f"recorded model {recorded} unavailable"
    return "primary"


def select_models(
    config: GatewayConfig,
    routes: Iterable[str],
    *,
    listed: Sequence[str] | None = None,
    recorded: Mapping[str, str] | None = None,
) -> ModelSelection:
    """Probe each route's model in turn, then fix each route's effective model for the whole run.

    ``listed`` is the recorded catalog: a model it does not contain is unavailable without a
    request. ``recorded`` is a sealed bundle's models_used: it is honoured only if it is the
    route's own model and that model still answers. A route whose model does not pass its probes
    raises ``ModelChainExhaustedError`` naming the model and its probe outcome; no other model is
    ever selected in its place.
    """
    chains = {route: chain_for(route) for route in sorted(set(routes))}
    models = list(dict.fromkeys(model for chain in chains.values() for model in chain))
    probes = {model: _probe(config, model, listed) for model in models}
    decisions: dict[str, RouteDecision] = {}
    for route, chain in chains.items():
        sealed = (recorded or {}).get(route)
        preference = [sealed, *chain] if sealed in chain else list(chain)
        winner = next((model for model in preference if probes[model].available), None)
        if winner is None:
            outcomes = "; ".join(f"{model} {probes[model].detail}" for model in chain)
            raise ModelChainExhaustedError(
                f"route {route}: its model did not pass the availability probes ({outcomes}); "
                "no substitute model is used, and the run fails closed before any content call"
            )
        decisions[route] = RouteDecision(
            route, chain, winner, sealed, _reason(route, chain, winner, sealed)
        )
    return ModelSelection(tuple(probes.values()), decisions)


def describe(selection: ModelSelection) -> list[str]:
    """Human-readable lines: each route's probe outcome, then each route's effective model.

    Every model in a chain was probed (or refused as unlisted) by ``select_models``, so each one
    has an outcome to name.
    """
    by_model = {probe.model: probe for probe in selection.probes}
    lines: list[str] = []
    for route, decision in sorted(selection.decisions.items()):
        outcomes = " -> ".join(
            f"{model} {by_model[model].detail} "
            f"({'available' if by_model[model].available else 'unavailable'})"
            for model in decision.chain
        )
        lines.append(f"chain {route}: {outcomes}")
        lines.append(f"route {route}: will use {decision.model} ({decision.reason})")
    return lines
