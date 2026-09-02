"""Gateway configuration read from the process environment, never from a file.

The owner provides ``GPT_OSS_ENDPOINT`` (the OpenAI-compatible base URL) and ``GPT_OSS_API_KEY``
as process environment variables (RESEARCH_AND_GUIDELINES.md section 18.4, owner item OWNER-02);
no ``.env`` file is read or required. ``GPT_OSS_MODEL`` is an optional override of a manifest's
default route for local experimentation only. A missing variable fails closed with a ConfigError
that names the owner item and its resume predicate. The key never appears in a repr or a message.

Extracted from the legacy ``env.py``: the single reading point and the trailing-slash
normalisation are retained; the alias chains, the hardcoded default base URL, the default model,
and the per-job routing table (routes now live in prompt manifests) are removed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from repository_presenter.core.errors import ConfigError

ENDPOINT_VARIABLE = "GPT_OSS_ENDPOINT"
API_KEY_VARIABLE = "GPT_OSS_API_KEY"
MODEL_VARIABLE = "GPT_OSS_MODEL"
OWNER_ITEM = "OWNER-02"
RESUME_PREDICATE = (
    f"{ENDPOINT_VARIABLE} and {API_KEY_VARIABLE} are present in the process environment"
)
DEFAULT_TIMEOUT_SECONDS = 360.0


@dataclass(frozen=True)
class GatewayConfig:
    """Where the gateway is and how to authenticate; the key is excluded from every repr."""

    base_url: str
    api_key: str = field(repr=False)
    model_override: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).netloc


def load_gateway_config(environment: Mapping[str, str]) -> GatewayConfig:
    """Read the gateway variables from ``environment``; absence names OWNER-02 and fails closed."""
    endpoint = (environment.get(ENDPOINT_VARIABLE) or "").strip()
    api_key = (environment.get(API_KEY_VARIABLE) or "").strip()
    missing = [
        name
        for name, value in ((ENDPOINT_VARIABLE, endpoint), (API_KEY_VARIABLE, api_key))
        if not value
    ]
    if missing:
        raise ConfigError(
            f"{OWNER_ITEM}: {' and '.join(missing)} not set in the process environment; "
            f"resume when {RESUME_PREDICATE}"
        )
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ConfigError(f"{ENDPOINT_VARIABLE} is not an absolute http(s) URL")
    override = (environment.get(MODEL_VARIABLE) or "").strip() or None
    return GatewayConfig(endpoint.rstrip("/"), api_key, override)
