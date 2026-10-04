"""Model fallback chains: which model answers each manifest route, decided once per run.

A prompt manifest names its primary ``model_route``. ``FALLBACK_CHAINS`` is the one place a
route's fallbacks are configured; a route not listed there has a chain of its own name alone. At
run start every model in every chain is probed once with a tiny request
(``transport.probe_availability``), and each route's effective model is the first one, in chain
order, that answered - except that a sealed bundle's recorded model is preferred when it still
answers, so a rerun reproduces the bytes it was sealed with. The decision is a frozen value: no
call in the run may name any other model, and nothing in a run probes again.

Every model is probed as a chain member, so a route with no answering model fails closed with
``ModelChainExhaustedError`` before any content call is made.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, GatewayError
from repository_presenter.core.llm.transport import AvailabilityProbe, probe_availability

# Keyed by manifest ``model_route``; values are fallbacks only, tried in this order after the
# route itself. Chat-capable models only: an image or embedding model cannot answer a
# json_schema chat request, so it is never listed here.
FALLBACK_CHAINS: Mapping[str, tuple[str, ...]] = {
    "qwen3-next": ("gpt-oss", "recommended", "Qwen2.5-VL-7B"),
}


class ModelChainExhaustedError(GatewayError):
    """No model in a route's chain answered at run start; the run fails closed, names each."""


def chain_for(route: str) -> tuple[str, ...]:
    """The route followed by its configured fallbacks, in the order they are tried."""
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
    if listed is not None and model not in listed:
        return AvailabilityProbe(model, False, "not in the recorded catalog")
    return probe_availability(config, model)


def _reason(route: str, chain: tuple[str, ...], model: str, recorded: str | None) -> str:
    if recorded is not None and model == recorded:
        return "recorded model still available"
    if recorded is not None and recorded not in chain:
        return f"recorded model {recorded} is not in the chain"
    if recorded is not None:
        return f"recorded model {recorded} unavailable"
    if model == route:
        return "primary"
    return f"primary {route} unavailable"


def select_models(
    config: GatewayConfig,
    routes: Iterable[str],
    *,
    listed: Sequence[str] | None = None,
    recorded: Mapping[str, str] | None = None,
) -> ModelSelection:
    """Probe every chain model once, then fix each route's effective model for the whole run.

    ``listed`` is the recorded catalog: a chain model it does not contain is unavailable without
    a request. ``recorded`` is a sealed bundle's models_used: a route whose recorded model is in
    its chain and still answers keeps that model, so a rerun reuses what it was sealed with. A
    route with no answering model raises ``ModelChainExhaustedError`` naming every probe's outcome.
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
                f"route {route}: no model in its chain answered ({outcomes}); "
                "the run fails closed before any content call"
            )
        decisions[route] = RouteDecision(
            route, chain, winner, sealed, _reason(route, chain, winner, sealed)
        )
    return ModelSelection(tuple(probes.values()), decisions)


def describe(selection: ModelSelection) -> list[str]:
    """Human-readable lines: each chain's probe outcomes, then each route's effective model.

    Every chain member was probed (or refused as unlisted) by ``select_models``, so each one has
    an outcome to name.
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
