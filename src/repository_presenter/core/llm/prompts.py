"""The governed prompt registry: one manifest per LLM job under ``prompts/``, loaded fail-loud.

Prompt content lives only in those manifests, never as a string literal in code; this module
loads and validates them. Every manifest declares its packet (what deterministic code assembles
for the job), its typed output contract with the fact-ID binding the guard enforces, its
``model_route`` chosen from the catalog preflight recorded, and its sampling contract. The
manifest's content hash is a candidate dependency (README_CONTRACT.md section 7): a change to any
field reopens the candidates that consumed it.

Extracted from the legacy ``prompt_registry.py`` and ``prompt_schema.py``: fail-loud loading with
ID-equals-filename, duplicate, and schema checks is retained; the category subdirectories, the
route-to-prompt mapping (a route is a model, not a job), the deprecation lifecycle, and the
control-plane content hash are removed.
"""

from __future__ import annotations

import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from repository_presenter.core.errors import ConfigError, GatewayError
from repository_presenter.core.hashing import sha256_text

PROMPTS_DIRNAME = "prompts"
JOB_STAGES: dict[str, str] = {
    "repository_investigation": "S3",
    "source_reconciliation": "S4",
    "presentation_planning": "S5",
    "section_authoring": "S6",
    "independent_review": "S10",
    "targeted_repair": "S11",
}
JOB_IDS: tuple[str, ...] = tuple(JOB_STAGES)
Binding = Literal["fact_ids", "unit_ids", "selection_ids", "finding_ids", "revision_ids"]


class Sampling(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature: float = Field(ge=0.0, le=2.0)
    max_output_tokens: int = Field(ge=1)
    response_format: Literal["json_object", "json_schema"]
    # The gateway accepts seed for the routed model, probed in G2-W19 and recorded in
    # runs/preflight/catalog.json. It is a manifest field like the rest, so it is versioned,
    # reviewed, and tracked in every candidate's dependencies.json
    # (docs/RESEARCH_AND_GUIDELINES.md sections 18.4 and 27.5 D4).
    seed: int | None = None


class PacketField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: Literal["string", "json"]
    description: str = Field(min_length=1)


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fields: tuple[PacketField, ...] = Field(min_length=1)
    fact_kinds: tuple[str, ...] = ()

    @field_validator("fields")
    @classmethod
    def _unique_names(cls, fields: tuple[PacketField, ...]) -> tuple[PacketField, ...]:
        names = [field.name for field in fields]
        if len(set(names)) != len(names):
            raise ValueError("packet field names must be unique")
        return fields

    @property
    def names(self) -> frozenset[str]:
        return frozenset(field.name for field in self.fields)


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str = Field(pattern=r"^[A-Z][A-Za-z0-9]*V[0-9]+$")
    binding: Binding
    schema_: dict[str, Any] = Field(alias="schema")

    @field_validator("schema_")
    @classmethod
    def _object_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        if schema.get("type") != "object" or not isinstance(schema.get("required"), list):
            raise ValueError("output schema must describe an object with a required list")
        return schema


class PromptManifest(BaseModel):
    """One governed job: its route, packet, output contract, and the prompt text itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_id: str
    version: str = Field(pattern=r"^[0-9]+$")
    stage: str
    purpose: str = Field(min_length=1)
    model_route: str = Field(min_length=1)
    route_rationale: str = Field(min_length=1)
    sampling: Sampling
    schema_preface: str = Field(min_length=1)
    rejection_template: str = Field(min_length=1)
    packet: Packet
    output: Output
    system: str = Field(min_length=1)
    user_template: str = Field(min_length=1)
    notes: str | None = None

    @field_validator("prompt_id")
    @classmethod
    def _known_job(cls, prompt_id: str) -> str:
        if prompt_id not in JOB_STAGES:
            raise ValueError(f"unknown job {prompt_id!r}; jobs are {', '.join(JOB_IDS)}")
        return prompt_id

    @field_validator("rejection_template")
    @classmethod
    def _quotes_the_rejection(cls, template: str) -> str:
        if "$errors" not in template:
            raise ValueError("rejection_template must place the rejection reasons at $errors")
        return template

    def placeholders(self) -> frozenset[str]:
        pattern = string.Template.pattern
        return frozenset(
            match.group("named") or match.group("braced")
            for match in pattern.finditer(self.user_template)
            if match.group("named") or match.group("braced")
        )


@dataclass(frozen=True)
class LoadedManifest:
    manifest: PromptManifest
    path: Path
    sha256: str


@dataclass(frozen=True)
class PromptRegistry:
    """The six manifests, keyed by job, each with the content hash candidates depend on."""

    manifests: Mapping[str, LoadedManifest]

    def __getitem__(self, job: str) -> LoadedManifest:
        return self.manifests[job]

    def hashes(self) -> dict[str, str]:
        return {job: self.manifests[job].sha256 for job in sorted(self.manifests)}

    def routes(self) -> dict[str, str]:
        return {job: self.manifests[job].manifest.model_route for job in sorted(self.manifests)}


def _parse(path: Path, text: str) -> PromptManifest:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name} is not valid YAML: {exc}") from exc
    try:
        manifest = PromptManifest.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path.name} is malformed: {exc}") from exc
    if manifest.prompt_id != path.stem:
        raise ConfigError(
            f"{path.name}: declared prompt_id {manifest.prompt_id!r} must match the filename"
        )
    expected_stage = JOB_STAGES[manifest.prompt_id]
    if manifest.stage != expected_stage:
        raise ConfigError(
            f"{path.name}: job {manifest.prompt_id} runs at {expected_stage}, not {manifest.stage}"
        )
    unbound = sorted(manifest.placeholders() - manifest.packet.names)
    if unbound:
        raise ConfigError(f"{path.name}: user_template names fields outside its packet: {unbound}")
    return manifest


def load_manifests(prompts_dir: Path) -> PromptRegistry:
    """Load exactly the six job manifests from ``prompts_dir``; anything else fails closed."""
    if not prompts_dir.is_dir():
        raise ConfigError(f"prompt manifests not found: no {prompts_dir.name}/ directory")
    files = sorted(path for path in prompts_dir.iterdir() if path.is_file())
    strays = [path.name for path in files if path.suffix != ".yaml" or path.stem not in JOB_STAGES]
    if strays:
        raise ConfigError(f"{prompts_dir.name}/ holds files that are not job manifests: {strays}")
    loaded: dict[str, LoadedManifest] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        manifest = _parse(path, text)
        loaded[manifest.prompt_id] = LoadedManifest(manifest, path, sha256_text(text))
    missing = [job for job in JOB_IDS if job not in loaded]
    if missing:
        raise ConfigError(f"{prompts_dir.name}/ lacks manifests for: {', '.join(missing)}")
    return PromptRegistry(loaded)


def validate_routes(registry: PromptRegistry, catalog_ids: Sequence[str]) -> None:
    """Every manifest routes to a model the recorded catalog lists; a vanished model fails."""
    for job, route in registry.routes().items():
        if route not in catalog_ids:
            raise GatewayError(
                f"prompt manifest {job} routes to {route!r}, which the gateway catalog does not "
                f"list ({', '.join(catalog_ids)}); re-point the manifest to a listed model"
            )
