"""Run one governed job: render its packet, call the gateway, validate and bind the output.

A job is one manifest plus one packet. The runner renders the manifest's templates with the
packet, sends one chat completion at the manifest's route and sampling contract, parses the JSON
object it returns, validates it against the manifest's output schema, and binds every cited ID to
the facts. A rejected output earns exactly one re-ask that quotes the rejection; a second
rejection fails the job closed. Every physical attempt is recorded in the ledger. An accepted
output is stored under the hash of the request that produced it, so the same request in a later
run reuses it with zero provider calls and a ``cache_reuse`` ledger record.

Extracted from the legacy ``call_transport.py``: physical-attempt accounting and request and
response hashing are retained; the requests-based protocol handling, provider sessions, and
trusted-lane budgets are removed in favour of the openai SDK and this project's retry policies.
"""

from __future__ import annotations

import functools
import json
import string
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from openai import APIConnectionError, APIStatusError, APITimeoutError

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, JobError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm import transport
from repository_presenter.core.llm.binding import binding_errors
from repository_presenter.core.llm.ledger import CallRecord, Ledger, canonical_hash
from repository_presenter.core.llm.prompts import LoadedManifest
from repository_presenter.core.retry import RetryableOperationError, run_with_retry

CALLS_DIRNAME = "calls"
_TRANSIENT_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class JobContext:
    repository: str
    source_revision: str


@dataclass(frozen=True)
class JobResult:
    job: str
    output: dict[str, Any]
    request_sha256: str
    attempts: int
    provider_calls: int
    cache_reused: bool
    model_served: str | None
    total_tokens: int | None


@dataclass(frozen=True)
class _Reply:
    content: str
    model: str | None
    request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class CallStore:
    """Accepted outputs keyed by request hash, under the transaction directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, request_sha256: str) -> Path:
        # A short name: the full hash under a transaction directory overruns Windows' path limit.
        return self.directory / f"{request_sha256[:24]}.json"

    def get(self, request_sha256: str) -> dict[str, Any] | None:
        path = self.path(request_sha256)
        if not path.is_file():
            return None
        stored = json.loads(path.read_text(encoding="utf-8"))
        output = stored.get("output")
        return output if isinstance(output, dict) else None

    def put(
        self, request_sha256: str, job: str, model_served: str | None, output: dict[str, Any]
    ) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"job": job, "model_served": model_served, "output": output}
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        self.path(request_sha256).write_bytes(text.encode("utf-8"))


def render_messages(manifest: LoadedManifest, packet: Mapping[str, Any]) -> list[dict[str, str]]:
    """The system and user messages for ``packet``; the packet must match the manifest exactly."""
    fields = manifest.manifest.packet
    expected = fields.names
    given = frozenset(packet)
    if given != expected:
        missing = sorted(expected - given)
        extra = sorted(given - expected)
        raise ConfigError(
            f"packet for {manifest.manifest.prompt_id} does not match its manifest "
            f"(missing {missing}, unexpected {extra})"
        )
    rendered: dict[str, str] = {}
    for field in fields.fields:
        value = packet[field.name]
        if field.type == "json":
            rendered[field.name] = json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False)
        elif isinstance(value, str):
            rendered[field.name] = value
        else:
            raise ConfigError(f"packet field {field.name} must be a string")
    user = string.Template(manifest.manifest.user_template).substitute(rendered)
    schema = json.dumps(manifest.manifest.output.schema_, indent=1, sort_keys=True)
    preface = manifest.manifest.schema_preface.strip()
    system = f"{manifest.manifest.system.rstrip()}\n\n{preface}\n{schema}\n"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def request_payload(manifest: LoadedManifest, messages: list[dict[str, str]]) -> dict[str, Any]:
    """The chat-completion request; ``json_schema`` makes the gateway enforce the output shape."""
    sampling = manifest.manifest.sampling
    response_format: dict[str, Any] = {"type": sampling.response_format}
    if sampling.response_format == "json_schema":
        response_format["json_schema"] = {
            "name": manifest.manifest.prompt_id,
            "schema": manifest.manifest.output.schema_,
            "strict": True,
        }
    return {
        "model": manifest.manifest.model_route,
        "messages": messages,
        "temperature": sampling.temperature,
        "max_tokens": sampling.max_output_tokens,
        "response_format": response_format,
    }


def _complete(config: GatewayConfig, payload: dict[str, Any]) -> _Reply:
    # Looked up on the module so the test seam that swaps the client applies here too.
    client = transport.build_client(config)
    completion = client.chat.completions.create(**payload)
    usage = completion.usage
    content = completion.choices[0].message.content if completion.choices else None
    return _Reply(
        content=content or "",
        model=completion.model,
        request_id=completion.id,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class _Attempts:
    """Physical-attempt accounting for one logical call."""

    def __init__(
        self,
        manifest: LoadedManifest,
        context: JobContext,
        ledger: Ledger,
        logical_id: str,
    ) -> None:
        self.manifest = manifest
        self.context = context
        self.ledger = ledger
        self.logical_id = logical_id
        self.count = 0
        self.last_model: str | None = None
        self.last_tokens: int | None = None

    def call(self, config: GatewayConfig, payload: dict[str, Any]) -> _Reply:
        self.count += 1
        started_at = _now()
        started = time.monotonic()
        try:
            reply = _complete(config, payload)
        except APIStatusError as exc:
            self._record(
                payload, started_at, started, "http_error", exc.status_code, type(exc).__name__
            )
            if exc.status_code in _TRANSIENT_STATUSES:
                raise RetryableOperationError(f"HTTP {exc.status_code}") from None
            raise JobError(
                f"{self.manifest.manifest.prompt_id}: gateway answered HTTP {exc.status_code}"
            ) from None
        except APITimeoutError as exc:
            self._record(payload, started_at, started, "timeout", None, type(exc).__name__)
            raise RetryableOperationError("timeout") from None
        except APIConnectionError as exc:
            self._record(payload, started_at, started, "connection_error", None, type(exc).__name__)
            raise RetryableOperationError(type(exc).__name__) from None
        self.last_model = reply.model
        self.last_tokens = reply.total_tokens
        self._record(payload, started_at, started, "success", 200, None, reply)
        return reply

    def record_invalid(self, error_class: str) -> None:
        """Mark the last successful attempt's output as rejected without a new call."""
        self.ledger.append(self._base(None, _now(), 0, "response_invalid", 200, error_class))

    def _record(
        self,
        payload: dict[str, Any],
        started_at: str,
        started: float,
        outcome: str,
        status: int | None,
        error_class: str | None,
        reply: _Reply | None = None,
    ) -> None:
        latency = int((time.monotonic() - started) * 1000)
        record = self._base(payload, started_at, latency, outcome, status, error_class, reply)
        self.ledger.append(record)

    def _base(
        self,
        payload: dict[str, Any] | None,
        started_at: str,
        latency_ms: int,
        outcome: str,
        status: int | None,
        error_class: str | None,
        reply: _Reply | None = None,
    ) -> CallRecord:
        request_sha256 = canonical_hash(payload) if payload is not None else self.logical_id
        return CallRecord(
            call_id=f"{self.logical_id[:16]}-{self.count:02d}-{outcome}",
            logical_call_id=self.logical_id,
            repository=self.context.repository,
            source_revision=self.context.source_revision,
            stage=self.manifest.manifest.stage,
            job=self.manifest.manifest.prompt_id,
            prompt_sha256=self.manifest.sha256,
            model_route=self.manifest.manifest.model_route,
            model_served=reply.model if reply else self.last_model,
            attempt=self.count,
            disposition="provider_call",
            started_at=started_at,
            finished_at=_now(),
            latency_ms=latency_ms,
            outcome=outcome,  # type: ignore[arg-type]
            http_status=status,
            request_sha256=request_sha256,
            response_sha256=canonical_hash(reply.content) if reply else None,
            provider_request_id=reply.request_id if reply else None,
            prompt_tokens=reply.prompt_tokens if reply else None,
            completion_tokens=reply.completion_tokens if reply else None,
            total_tokens=reply.total_tokens if reply else None,
            error_class=error_class,
        )


def _parse(
    manifest: LoadedManifest, content: str, facts: FactsDocument
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        output = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, [f"output is not a JSON object: {exc.msg} at position {exc.pos}"]
    if not isinstance(output, dict):
        return None, ["output is not a JSON object"]
    validator = Draft202012Validator(manifest.manifest.output.schema_)
    errors = [
        f"{error.json_path}: {error.message}"
        for error in sorted(validator.iter_errors(output), key=lambda error: error.json_path)
    ]
    errors.extend(binding_errors(output, facts, manifest.manifest.output.binding))
    return (output if not errors else None), errors


def run_job(
    manifest: LoadedManifest,
    packet: Mapping[str, Any],
    *,
    config: GatewayConfig,
    facts: FactsDocument,
    ledger: Ledger,
    store: CallStore,
    context: JobContext,
) -> JobResult:
    """The accepted output of one job, from the store when the same request was accepted before."""
    job = manifest.manifest.prompt_id
    messages = render_messages(manifest, packet)
    payload = request_payload(manifest, messages)
    request_sha256 = canonical_hash({"prompt_sha256": manifest.sha256, "payload": payload})
    stored = store.get(request_sha256)
    if stored is not None:
        now = _now()
        ledger.append(
            CallRecord(
                call_id=f"{request_sha256[:16]}-00-cache_reuse",
                logical_call_id=request_sha256,
                repository=context.repository,
                source_revision=context.source_revision,
                stage=manifest.manifest.stage,
                job=job,
                prompt_sha256=manifest.sha256,
                model_route=manifest.manifest.model_route,
                model_served=None,
                attempt=0,
                disposition="cache_reuse",
                started_at=now,
                finished_at=now,
                latency_ms=0,
                outcome="cache_reuse",
                http_status=None,
                request_sha256=request_sha256,
                response_sha256=canonical_hash(stored),
                provider_request_id=None,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                error_class=None,
            )
        )
        return JobResult(job, stored, request_sha256, 0, 0, True, None, None)

    attempts = _Attempts(manifest, context, ledger, request_sha256)
    current = payload
    rejection: list[str] = []
    for ask in (1, 2):
        reply = run_with_retry("llm_call", functools.partial(attempts.call, config, current))
        output, rejection = _parse(manifest, reply.content, facts)
        if output is not None:
            store.put(request_sha256, job, reply.model, output)
            return JobResult(
                job,
                output,
                request_sha256,
                attempts.count,
                attempts.count,
                False,
                reply.model,
                attempts.last_tokens,
            )
        attempts.record_invalid("OutputRejected")
        if ask == 1:
            current = _re_ask(manifest, payload, reply.content, rejection)
    raise JobError(f"{job}: output rejected twice; last rejection: {'; '.join(rejection)}")


def _re_ask(
    manifest: LoadedManifest, payload: dict[str, Any], previous: str, errors: list[str]
) -> dict[str, Any]:
    """The same request plus the rejected output and the manifest's correction, once."""
    template = string.Template(manifest.manifest.rejection_template)
    correction = template.substitute(errors="\n- ".join(errors)).strip()
    messages = [
        *payload["messages"],
        {"role": "assistant", "content": previous},
        {"role": "user", "content": correction},
    ]
    return {**payload, "messages": messages}
