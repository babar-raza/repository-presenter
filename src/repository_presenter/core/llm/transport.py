"""The gateway transport: the official ``openai`` SDK against the configured base URL.

RESEARCH_AND_GUIDELINES.md section 18.2 prefers the SDK over porting the legacy requests-based
protocol handling. ``build_client`` is the one place a client is built and the one seam tests
replace with a client over a mock transport, so nothing else ever reaches the network. Retries
are the project's own (core/retry.py), so the SDK's are off. Failures are reported by status or
by exception class only; a response body can echo a request and is never repeated.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

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


@dataclass(frozen=True)
class SeedProbe:
    """What one model does with a ``seed``, from two identical bounded calls."""

    model: str
    accepted: bool
    deterministic: bool | None
    detail: str


# Bounded enough to cost almost nothing and long enough that two replies could differ.
_PROBE_MAX_TOKENS = 24


def probe_seed(config: GatewayConfig, model: str) -> SeedProbe:
    """Two identical bounded completions carrying the same ``seed``, compared byte for byte.

    docs/RESEARCH_AND_GUIDELINES.md section 18.4's discovery pattern, with the definition section
    27.10's follow-up 3 sets: identical content is ``honoured``, differing content is ``accepted,
    non-deterministic``, and a refusal settles the question outright. Two calls, one answer, and
    no composition sampled for a kinder result. The store is not consulted: the point is what the
    gateway does, not what was cached.
    """
    client = build_client(config)
    messages = _liveness_messages()
    replies: list[str] = []
    for _ in range(2):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=_PROBE_MAX_TOKENS,
                temperature=0,
                seed=1,
            )
        except APIStatusError as exc:
            return SeedProbe(model, False, None, f"HTTP {exc.status_code}")
        except APIConnectionError as exc:
            raise GatewayError(f"gateway {config.host} unreachable: {type(exc).__name__}") from None
        choices = completion.choices or []
        if not choices:
            return SeedProbe(model, True, None, "accepted, no content returned")
        replies.append(choices[0].message.content or "")
    deterministic = replies[0] == replies[1]
    return SeedProbe(
        model,
        True,
        deterministic,
        "honoured" if deterministic else "accepted, non-deterministic",
    )


@dataclass(frozen=True)
class AvailabilityProbe:
    """Whether one model answered one tiny chat request, and how it failed when it did not."""

    model: str
    available: bool
    detail: str


def _liveness_messages() -> list[dict[str, str]]:
    """The one liveness token both probes send: a yes-or-no question the gateway answers, never
    prompt text (the single exemption tests/core/llm/test_prompt_hygiene.py allows this module)."""
    return [{"role": "user", "content": "ping"}]


# Enough output for any chat model to finish a one-word reply, far under any real budget.
_AVAILABILITY_MAX_TOKENS = 16
# A dead route must not hold a run for the whole job timeout: each probe is capped on its own.
_AVAILABILITY_TIMEOUT_SECONDS = 120.0


def probe_availability(config: GatewayConfig, model: str) -> AvailabilityProbe:
    """One tiny chat completion; a 2xx answer is available, anything else is named and not used.

    Failures are reported by status or exception class only, never a response body, and never
    raise: an unavailable model is an input to the fallback decision (core/llm/fallback.py), not
    an error of its own. Not a content call: its reply is discarded and nothing is recorded in
    the call ledger.
    """
    client = build_client(config).with_options(timeout=_AVAILABILITY_TIMEOUT_SECONDS, max_retries=0)
    try:
        client.chat.completions.create(
            model=model,
            messages=_liveness_messages(),  # type: ignore[arg-type]
            max_tokens=_AVAILABILITY_MAX_TOKENS,
            temperature=0,
        )
    except APIStatusError as exc:
        return AvailabilityProbe(model, False, f"HTTP {exc.status_code}")
    except APITimeoutError:
        return AvailabilityProbe(model, False, "timeout")
    except APIConnectionError as exc:
        return AvailabilityProbe(model, False, type(exc).__name__)
    return AvailabilityProbe(model, True, "HTTP 200")
