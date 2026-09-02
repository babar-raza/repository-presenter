"""The gateway transport: the official ``openai`` SDK against the configured base URL.

RESEARCH_AND_GUIDELINES.md section 18.2 prefers the SDK over porting the legacy requests-based
protocol handling. ``build_client`` is the one place a client is built and the one seam tests
replace with a client over a mock transport, so nothing else ever reaches the network. Retries
are the project's own (core/retry.py), so the SDK's are off. Failures are reported by status or
by exception class only; a response body can echo a request and is never repeated.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import GatewayError


@dataclass(frozen=True)
class ModelEntry:
    id: str
    owned_by: str | None = None


@dataclass(frozen=True)
class ModelCatalog:
    """What ``GET /models`` listed, in ID order."""

    base_url: str
    models: tuple[ModelEntry, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(model.id for model in self.models)


def build_client(config: GatewayConfig) -> OpenAI:
    """One SDK client for ``config``; the key travels only in the SDK's bearer header."""
    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout_seconds,
        max_retries=0,
    )


def list_models(config: GatewayConfig) -> ModelCatalog:
    """The gateway's live model catalog; any failure is a GatewayError naming only the status."""
    client = build_client(config)
    try:
        page = client.models.list()
    except APIStatusError as exc:
        raise GatewayError(
            f"GET {config.base_url}/models answered HTTP {exc.status_code}"
        ) from None
    except APIConnectionError as exc:
        raise GatewayError(f"gateway {config.host} unreachable: {type(exc).__name__}") from None
    entries = sorted(
        (ModelEntry(model.id, getattr(model, "owned_by", None)) for model in page.data),
        key=lambda entry: entry.id,
    )
    if not entries:
        raise GatewayError(f"GET {config.base_url}/models listed no models")
    return ModelCatalog(config.base_url, tuple(entries))
